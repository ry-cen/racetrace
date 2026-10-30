<img src="assets/icon.svg" width="64" height="64" alt="">

# RaceTrace

Crash the worker. Break the ordering. Find the bug.

RaceTrace is a local-first developer tool for asynchronous backend systems. It injects faults at application-level checkpoints, lets the system recover, evaluates business invariants, and saves an execution history. The initial target is background job processing.

> **Status: early development.** Only the foundation (Week 1) exists. The CLI cannot run scenarios yet, and the checkpoint protocol, fault injection, and invariant engine are planned. See [Status](#status) and [ROADMAP.md](ROADMAP.md).

## Problem

Asynchronous systems fail in the gaps between steps: a worker commits to the database and dies before acknowledging the message; a job is redelivered; two workers race. These bugs are hard to reproduce with unit tests, and generic infrastructure chaos (killing random pods, network chaos) does not target the step that matters or say whether the business result is wrong.

## Core concept

- **Checkpoints**: named points in application code (`job.received`, `job.db_committed`, ...) marked with a one-line SDK call.
- **Faults**: actions applied when a checkpoint is reached, such as killing the worker process.
- **Invariants**: business rules checked after recovery, such as "exactly one ledger entry per job".
- **Execution history**: a saved record of what happened in each run.

The differentiator is application checkpoints plus business invariants, not random infrastructure failure. RaceTrace is a test-only tool. It does not provide deterministic scheduling, exact replay, or exactly-once guarantees, and it makes no performance claims.

## Architecture overview

Target design (planned except where noted in [Status](#status)); details in [ARCHITECTURE.md](ARCHITECTURE.md).

```
 host                                       disposable Compose project rt-<run-id>
+-------------------------+                +--------------------------------------+
| racetrace (Go)          |                |  worker (Python + racetrace SDK)     |
|  - scenario parser      | <-- HTTP/JSON  |   checkpoint("job.db_committed")     |
|  - checkpoint endpoint  |    long-poll   |        |                |            |
|  - fault engine         |                |        v                v            |
|  - invariants, reports  | -- docker  --> |     Redis Streams    PostgreSQL      |
+-------------------------+    kill        +--------------------------------------+
```

## Developer workflow (planned)

1. Mark checkpoints in your worker with the Python SDK.
2. Write a YAML scenario: workload, fault location, recovery deadline, invariants.
3. `racetrace run scenario.yaml` creates a disposable Compose project, applies the fault, lets the system recover, evaluates invariants, writes a report under `.racetrace/runs/<run-id>/`, tears down, and exits with a code that classifies the result.
4. Later: `racetrace explore` crashes at every discovered checkpoint.

## Status

| Area | State | Notes |
| --- | --- | --- |
| CLI skeleton (`racetrace version`, `racetrace help`) | Implemented | `run`, `explore`, `report` print "not implemented yet" and exit 2 |
| Outcome categories and exit codes (`internal/outcome`) | Implemented | Unknown outcome maps to 3, never a pass |
| Python SDK `checkpoint()` | Implemented (local only) | No-op when disabled; Week 1 test-only trigger `RACETRACE_LOCAL_CRASH_AT`; with `RACETRACE_CONTROLLER_URL` set it raises `ControllerUnavailableError` |
| Reference app `examples/redis-worker` (unsafe and safe variants) | Implemented | Redis Streams worker, PostgreSQL effects, pytest integration tests |
| `Makefile`, uv workspace, ruff, CI workflow | Implemented | CI workflow has not yet run on GitHub |
| Reference app Docker image and `compose.yaml` | Written, not verified locally | No Docker in the dev sandbox; CI is expected to validate |
| Checkpoint HTTP protocol, SDK-to-controller calls | Planned (Week 2) | [ADR 0001](docs/adr/0001-checkpoint-protocol.md) |
| Controller, Compose orchestration, `kill-worker` fault | Planned (Week 3) | [ADR 0002](docs/adr/0002-local-first-docker-compose.md) |
| YAML scenarios, invariants, reports, `racetrace run` and `report` | Planned (Week 4) | v0.1 target |
| Automatic exploration (`racetrace explore`) | Planned (Week 5) | |
| Reliability, DX, public release | Planned (Weeks 6 to 8) | OpenTelemetry and a React/TypeScript visualization are later |

## Quick start: the Week 1 crash demo

This demonstrates the reference app's failure window using the local test-only crash trigger. It does not use the RaceTrace controller.

Prerequisites: Go 1.24+, Python 3.11+, [uv](https://docs.astral.sh/uv/), Docker with Compose, plus `psql` and `redis-cli` on the host.

```sh
make sync   # uv sync --all-packages
make up     # start Redis and PostgreSQL (docker compose)

export REDIS_URL=redis://127.0.0.1:6379/0
export DATABASE_URL=postgresql://racetrace:racetrace@127.0.0.1:5432/racetrace
export REFWORKER_VARIANT=unsafe     # use a fresh database (make down; make up) before trying safe

uv run python -m refworker migrate
uv run python -m refworker produce --count 1 --account-id demo --amount-cents 100

# Worker A commits the effect, then is SIGKILLed before XACK.
RACETRACE_LOCAL_CRASH_AT=job.db_committed REFWORKER_WORKER_ID=A \
  uv run python -m refworker work --max-jobs 1

# The message is still pending. Wait longer than the min-idle threshold, then recover with worker B.
sleep 1
REFWORKER_WORKER_ID=B uv run python -m refworker work \
  --min-idle-ms 200 --block-ms 100 --max-jobs 1 --idle-exit-ms 2000

psql "$DATABASE_URL" -c "SELECT * FROM job_executions"
psql "$DATABASE_URL" -c "SELECT * FROM ledger_entries"
make down
```

Expected for `unsafe`: two executions and two ledger entries for one job (the invariant violation RaceTrace is designed to find). For `safe` (set `REFWORKER_VARIANT=safe` and start from a fresh database): two executions and one ledger entry. See [examples/redis-worker/README.md](examples/redis-worker/README.md) for flags, an isolated-schema variant of this demo, and details.

## Local development

```sh
make sync         # install Python workspace
make lint         # gofmt, go vet, ruff check, ruff format --check
make test         # go test ./... and pytest
make build        # builds bin/racetrace
make fmt          # gofmt and ruff
bin/racetrace help
```

Python integration tests need `RACETRACE_TEST_REDIS_URL` and `RACETRACE_TEST_DATABASE_URL`; the Makefile defaults match `make up`. Running `uv run pytest` directly without them skips the integration tests. See [CONTRIBUTING.md](CONTRIBUTING.md).

Exit codes: 0 passed, 1 invariant violated, 2 usage error, 3 harness error, 4 recovery timeout, 5 application failure.

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md), [ROADMAP.md](ROADMAP.md), [CONTRIBUTING.md](CONTRIBUTING.md), [CONTEXT.md](CONTEXT.md) (glossary), [AGENTS.md](AGENTS.md)
- Decisions: [docs/adr/](docs/adr/)

## License

Apache License 2.0. See [LICENSE](LICENSE). Copyright 2026 RaceTrace contributors.
