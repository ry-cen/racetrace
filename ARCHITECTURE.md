# Architecture

Each section is labeled **Implemented** (exists in the repository today) or **Planned**. Today only the CLI skeleton, `internal/outcome`, the Python SDK's local behavior, and the reference app exist. See [ROADMAP.md](ROADMAP.md) for schedule and [docs/adr/](docs/adr/) for decisions.

RaceTrace makes no claim of deterministic scheduling, exact replay, exactly-once processing, or performance. It exercises specific crash points and checks stated invariants; passing means the checked invariants held in the runs performed.

## Components

### Go controller (Planned: Weeks 3 and 4)

Runs on the host, outside application containers. It:

- parses and validates the YAML scenario;
- manages a disposable Compose project per run (`docker compose -p rt-<run-id>`);
- serves the checkpoint HTTP endpoint;
- holds and releases checkpoints;
- selects and executes faults;
- tracks the run state machine;
- evaluates assertions;
- writes reports and returns the exit code.

Implemented today: only the `racetrace` CLI skeleton (`cmd/racetrace`). `version` and `help` work; `run`, `explore`, and `report` print "not implemented yet (planned for Week N)" and exit 2.

### Python SDK (Implemented locally; protocol Planned for Week 2)

Package `racetrace` in `sdk/python`. Stays stdlib-only.

Implemented:

- `checkpoint(name, **metadata)`. When disabled it is a no-op: no I/O and no metadata processing.
- `RACETRACE_LOCAL_CRASH_AT=<checkpoint>` (optionally `RACETRACE_LOCAL_CRASH_JOB_ID`): a Week 1 test-only trigger that SIGKILLs the process at that checkpoint. It is superseded by the controller.
- If `RACETRACE_CONTROLLER_URL` is set, `checkpoint()` raises `ControllerUnavailableError`. This is deliberate: the protocol does not exist yet, and the SDK must not silently proceed.
- Identity from `RACETRACE_RUN_ID` and `RACETRACE_WORKER_ID`.

Planned (Week 2): when active, a blocking HTTP call to the controller with a bounded timeout, and an explicit error on controller unavailability. See the protocol below.

### Fault engine (Planned: Week 3)

A small interface, for example `Fault` with `Apply(ctx, target) error`. Only `kill-worker` is planned initially, implemented as `docker kill --signal SIGKILL` on the container of the worker that hit the checkpoint, scoped to the run's Compose project by label. Later candidates: pause/resume, delay, duplicate delivery, network faults, competing-schedule exploration.

### Invariants and reporting (Planned: Week 4)

- Read-only PostgreSQL query assertions, run in a `READ ONLY` transaction.
- Job completion expectations, for example stream pending count 0.
- Recovery deadlines.
- A JSON report per run under `.racetrace/runs/<run-id>/` (`report.json`, `events.jsonl`) and a human terminal summary.

### Reference application (Implemented)

`examples/redis-worker` (package `refworker`) is a Redis Streams consumer-group worker, producer, and migrations, with `unsafe` and `safe` variants. It exists to give RaceTrace a real failure window; the unsafe variant is intentionally vulnerable. See [ADR 0003](docs/adr/0003-at-least-once-idempotent-effects.md) and [examples/redis-worker/README.md](examples/redis-worker/README.md).

Tables: `job_executions` (one row per committed execution attempt, including Redis message id and delivery count) and `ledger_entries` (credit `amount_cents` to `account_id` for `job_id`), written in one transaction. Migration 001 creates the tables without uniqueness; 002 adds `UNIQUE(job_id)` on `ledger_entries`. Safe uses `INSERT ... ON CONFLICT (job_id) DO NOTHING`.

Worker loop: XAUTOCLAIM idle pending messages first (minimum idle `REFWORKER_MIN_IDLE_MS`, default 5000), then XREADGROUP `>` with a bounded BLOCK. Per job:

```
job.received -> BEGIN -> insert execution + effect
  -> job.effect_written (inside transaction) -> COMMIT
  -> job.db_committed -> XACK -> job.acknowledged
```

Characterized by the integration tests:

| Crash at | Result after recovery |
| --- | --- |
| `job.received` | 1 effect, both variants (nothing committed) |
| `job.effect_written` | 1 effect, both variants (transaction rolled back) |
| `job.db_committed` | message stays pending, then is reclaimed. Unsafe: 2 ledger entries for one job (violation). Safe: 2 executions, 1 ledger entry |
| `job.acknowledged` | no redelivery |

## Planned run lifecycle

1. Validate the scenario.
2. Create the Compose project `rt-<run-id>`.
3. Wait until services are healthy.
4. Migrate and seed.
5. Start workers with `RACETRACE_CONTROLLER_URL`, `RACETRACE_RUN_ID`, `RACETRACE_WORKER_ID`.
6. Run the workload.
7. When the target checkpoint is reached, apply the fault.
8. Start or allow the recovery worker.
9. Wait for quiescence or the recovery deadline.
10. Evaluate invariants (read-only).
11. Write the report.
12. Tear down the project. This is always attempted, including on error; `--keep` keeps it for debugging.
13. Exit with the outcome's code.

## Planned checkpoint protocol

Summary of [ADR 0001](docs/adr/0001-checkpoint-protocol.md) (Week 2):

- HTTP/1.1 and JSON, stdlib on both sides.
- Request `POST /v1/checkpoints` with `protocol`, `run_id`, `worker_id`, `checkpoint`, `seq` (per-worker monotonic), `metadata`, `pid`, `sent_at`.
- Long-poll response `{"action":"continue"}` or `{"action":"crash"}`; with `kill-worker` under Docker the container is usually killed while the request is held, so no response arrives.
- SDK deadline `RACETRACE_CHECKPOINT_TIMEOUT_MS` (default 30000); the controller hold deadline is shorter.
- On timeout, refused connection, non-2xx, or malformed response the SDK raises `ControllerUnavailableError` (or exits with `RACETRACE_ON_CONTROLLER_ERROR=exit`). It never silently continues.
- Per-run bearer token; controller bound to loopback or the Compose gateway address.

## Failure semantics

Outcome categories (Implemented in `internal/outcome`; stable names appear in JSON reports):

| Outcome | Name | Exit code |
| --- | --- | --- |
| Passed | `passed` | 0 |
| Invariant violated | `invariant_violated` | 1 |
| Usage error | (CLI only) | 2 |
| Harness error | `harness_error` | 3 |
| Recovery timeout | `recovery_timeout` | 4 |
| Application failure | `application_failure` | 5 |

Rules:

- Classification precedence (Planned, not yet implemented): harness error > application failure > recovery timeout > invariant violated > passed. A harness error anywhere means correctness is unknown.
- An unknown outcome maps to exit code 3 (Implemented), so a classification bug can never look like a pass.
- Infrastructure errors are never a pass.
- Every wait has a deadline: checkpoint hold, SDK call, recovery, teardown. There are no unbounded retries.
- Application failure means the application failed in a way not caused by the injected fault (for example a worker crashing on its own).

## Planned scenario format

Planned shape (Week 4); not parsed by anything today.

```yaml
version: 1
name: crash-after-commit
environment:
  compose_file: examples/redis-worker/compose.yaml
  services: { worker: worker }
workload:
  command: ["python", "-m", "refworker", "produce", "--count", "1"]
fault:
  type: kill-worker
  at: job.db_committed
  occurrence: 1
recovery:
  start_replacement_worker: true
  deadline: 30s
invariants:
  - name: exactly-one-ledger-entry-per-job
    postgres: |
      SELECT job_id, count(*) FROM ledger_entries GROUP BY job_id HAVING count(*) <> 1
    expect: no_rows
  - name: queue-drained
    redis_stream_pending: { stream: racetrace:jobs, group: refworker, expect: 0 }
```

## Tradeoffs

- Docker required locally, with per-run startup cost (seconds). Matters for exploration in Week 5; mitigation (reuse project, reset state) is not designed.
- Shelling out to the `docker` CLI avoids an SDK dependency at the cost of parsing CLI behavior.
- HTTP long-poll is simple and portable but blocks the caller, which is an issue for async frameworks.
- Scoping kills by Compose project label is safe but depends on correct project/label handling.
- XAUTOCLAIM reclaims idle, not dead, consumers; tests must set min-idle above processing time.
- The Docker socket is never mounted into application containers, so the controller must live on the host.

Rejected for the MVP: Kubernetes, testcontainers, in-process fakes, gRPC, WebSockets, Unix sockets. See the ADRs.

## Repository layout

Current:

```
cmd/racetrace/            CLI skeleton (version, help; run/explore/report not implemented)
internal/outcome/         outcome categories and exit codes
sdk/python/               racetrace Python SDK
examples/redis-worker/    reference app (refworker), Dockerfile, compose.yaml
docs/adr/                 architecture decision records
docs/agents/              agent tooling conventions
.github/workflows/ci.yml  CI (not yet run on GitHub)
Makefile                  developer commands
```

Planned packages (none exist yet; only `internal/outcome` does):

```
internal/controller/      run state machine, HTTP server
internal/checkpoints/     protocol types, holds
internal/docker/          docker CLI wrapper, Compose project handling
internal/faults/          Fault interface, kill-worker
internal/assertions/      Postgres and Redis invariants
internal/explorer/        checkpoint failure matrix (Week 5)
internal/report/          report.json, events.jsonl, terminal summary
```
