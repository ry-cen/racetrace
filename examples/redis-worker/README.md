# Reference app: Redis Streams credit worker

A small background-job system that is deliberately vulnerable in one variant.
It is the target RaceTrace is being built against.

A producer enqueues "credit account" jobs on a Redis stream. Workers in a
consumer group claim each job, write to PostgreSQL, and then acknowledge the
message. Three identities are kept separate:

| Concept | Where it lives |
| --- | --- |
| Delivery | Redis message id; one job can be delivered more than once |
| Execution | a `job_executions` row: one per committed processing attempt, with its delivery count |
| Business effect | a `ledger_entries` row: the credit itself, keyed by the business `job_id` |

Each attempt writes its execution row and its effect in one transaction.

## Variants

- **unsafe**: schema `001_init.sql` only, plain `INSERT` of the effect.
- **safe**: adds `002_idempotency.sql` (`UNIQUE (job_id)`) and inserts with
  `ON CONFLICT (job_id) DO NOTHING`. The job may run twice; the credit lands once.
  Running safe without the constraint fails loudly instead of silently succeeding.

Running `migrate --variant unsafe` never removes an existing constraint, so use
a fresh database or schema when switching back to unsafe.

## Worker loop and checkpoints

1. Recovery first: `XAUTOCLAIM` messages pending longer than `--min-idle-ms`.
   The scan runs to completion (cursor `0-0`) before the worker blocks on new work.
2. Then `XREADGROUP ... >` with a bounded `BLOCK`.
3. Per message:

```
job.received -> BEGIN -> insert execution + effect -> job.effect_written
             -> COMMIT -> job.db_committed -> XACK -> job.acknowledged
```

`XAUTOCLAIM` reclaims *idle* messages, not provably dead consumers. It can take
work from a slow live worker, so `--min-idle-ms` must exceed worst-case processing time.

## Crash demo (manual)

Run from the repository root with Redis and PostgreSQL running (`make up` starts
them via `compose.yaml`; any Redis 7+ and PostgreSQL work if you adjust the URLs).

```sh
make sync
export REDIS_URL=redis://127.0.0.1:6379/0
export DATABASE_URL=postgresql://racetrace:racetrace@127.0.0.1:5432/racetrace
export REFWORKER_DB_SCHEMA=rt_demo_$(date +%s)     # fresh, isolated schema
export REFWORKER_STREAM=$REFWORKER_DB_SCHEMA:jobs
export REFWORKER_GROUP=$REFWORKER_DB_SCHEMA
export REFWORKER_VARIANT=unsafe                    # repeat with safe in a new schema

psql "$DATABASE_URL" -c "CREATE SCHEMA $REFWORKER_DB_SCHEMA"
uv run python -m refworker migrate
uv run python -m refworker produce --count 1

# Worker A commits the effect and is SIGKILLed before XACK.
RACETRACE_LOCAL_CRASH_AT=job.db_committed REFWORKER_WORKER_ID=A \
  uv run python -m refworker work --max-jobs 1
redis-cli -u "$REDIS_URL" XPENDING "$REFWORKER_STREAM" "$REFWORKER_GROUP" - + 10

# Wait past the idle threshold, then worker B reclaims and reprocesses the job.
sleep 1
REFWORKER_WORKER_ID=B uv run python -m refworker work \
  --min-idle-ms 200 --block-ms 100 --max-jobs 1 --idle-exit-ms 2000

psql "$DATABASE_URL" -c "SELECT job_id, worker_id, delivery_count FROM $REFWORKER_DB_SCHEMA.job_executions"
psql "$DATABASE_URL" -c "SELECT job_id, amount_cents FROM $REFWORKER_DB_SCHEMA.ledger_entries"

# Clean up only this demo's resources.
redis-cli -u "$REDIS_URL" DEL "$REFWORKER_STREAM"
psql "$DATABASE_URL" -c "DROP SCHEMA $REFWORKER_DB_SCHEMA CASCADE"
```

Expected: unsafe shows two executions (delivery counts 1 and 2) and **two ledger
entries for one job**. Safe shows two executions and **one** ledger entry.

`RACETRACE_LOCAL_CRASH_AT` is a Week 1 development aid in the SDK. It is
replaced by the RaceTrace controller in Week 2. Do not leave it set for the
recovery worker.

## Configuration

| Flag | Env fallback | Default | Commands |
| --- | --- | --- | --- |
| `--redis-url` | `REDIS_URL` | `redis://localhost:6379/0` | produce, work |
| `--database-url` | `DATABASE_URL` | `postgresql://localhost/postgres` | migrate, work |
| `--db-schema` | `REFWORKER_DB_SCHEMA` | `public` | migrate, work |
| `--variant` | `REFWORKER_VARIANT` | `unsafe` | migrate, work |
| `--stream` | `REFWORKER_STREAM` | `racetrace:jobs` | produce, work |
| `--group` | `REFWORKER_GROUP` | `refworker` | work |
| `--worker-id` | `REFWORKER_WORKER_ID` | `<hostname>-<pid>` | work |
| `--min-idle-ms` | `REFWORKER_MIN_IDLE_MS` | 5000 | work |
| `--block-ms` | `REFWORKER_BLOCK_MS` | 1000 | work |
| `--idle-exit-ms` | `REFWORKER_IDLE_EXIT_MS` | 0 (disabled) | work |
| `--deadline-ms` | `REFWORKER_DEADLINE_MS` | 0 (disabled) | work |
| `--max-jobs` | | 0 (no limit) | work |
| `--count`, `--account-id`, `--amount-cents` | | 1, `demo`, 100 | produce |

The schema name must match `^[a-z_][a-z0-9_]{0,62}$`; the connection's
`search_path` is exactly that schema. SQL migrations ship inside the package.

Plain `work` runs as a service until SIGTERM or SIGINT, which stop it after the
current bounded operation. Exit codes: 0 for normal stop, idle exit, or
`--max-jobs` reached; 3 when `--deadline-ms` expires (logged as `deadline_reached`),
including when the last job finished after the deadline; 1 on errors. Logs are
JSON lines on stderr.

## Tests

```sh
export RACETRACE_TEST_REDIS_URL=redis://127.0.0.1:6379/0
export RACETRACE_TEST_DATABASE_URL=postgresql://racetrace:racetrace@127.0.0.1:5432/racetrace
uv run pytest -q
```

The integration tests start real worker subprocesses. Each test uses its own
PostgreSQL schema and Redis stream and removes them afterwards. Without the URLs
the integration tests are skipped, unless `RACETRACE_REQUIRE_INTEGRATION=1` is set,
in which case they fail.

| Crash at | unsafe after recovery | safe after recovery |
| --- | --- | --- |
| none | 1 execution, 1 effect | 1 execution, 1 effect |
| `job.received` (before BEGIN) | 1 execution, 1 effect | 1 execution, 1 effect |
| `job.effect_written` (inside the transaction, rolled back) | 1 execution, 1 effect | 1 execution, 1 effect |
| `job.db_committed` (after COMMIT, before XACK) | 2 executions, **2 effects** | 2 executions, 1 effect |
| `job.acknowledged` | 1 execution, 1 effect, no redelivery | same |

These results describe these crash windows for this worker, not every possible
failure mode.

### Observed results

On 2026-10-30 the suite ran against Redis 7.4 and PostgreSQL 17 on Linux with
Python 3.12. Every run passed, and the table above matches what was observed:

- the initial suite: five consecutive runs;
- after the review fixes: three consecutive runs;
- the final 27-test suite: three runs, one with `RACETRACE_REQUIRE_INTEGRATION=1`.

CI validates `compose.yaml` and builds the image. The crash demo has not yet been
run end to end under Compose.
