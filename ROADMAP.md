# Roadmap

Eight-week plan. Effort figures are planning estimates in person-days for one developer, not measurements, and will be revised. A checkbox is ticked only after its acceptance criterion has been verified. Week 1 items verified locally on 2026-10-30 are ticked; the Compose files and CI remain unverified because the dev sandbox has no Docker and CI has not run yet.

The detailed task list is in [docs/backlog.md](docs/backlog.md). Architecture is in [ARCHITECTURE.md](ARCHITECTURE.md).

Non-goals throughout: deterministic scheduling, exact replay, exactly-once claims, performance claims, Kubernetes, and microservice frameworks in the MVP.

## Week 1: Foundation and reference system

Status: core acceptance verified locally; Compose and CI verification pending. Effort estimate: 5 person-days.

Deliverables:

- [x] Repo scaffolding: Go module, uv workspace, Makefile, lint/test tooling
- [x] CLI skeleton (`version`, `help`; `run`, `explore`, `report` exit 2 as not implemented)
- [x] `internal/outcome`: outcome categories and exit codes; unknown maps to 3
- [x] Python SDK `checkpoint()`: no-op when disabled; local test-only crash trigger; explicit `ControllerUnavailableError`
- [x] Reference app `examples/redis-worker`: unsafe and safe variants, migrations, producer, worker
- [x] Integration tests for crash at `job.received`, `job.effect_written`, `job.db_committed`, `job.acknowledged`
- [ ] Dockerfile and `compose.yaml` for the reference app
- [ ] GitHub Actions CI (Go, Python with service containers, Compose validate and build)
- [x] Documentation set: README, ARCHITECTURE, CONTRIBUTING, AGENTS, CONTEXT, ADRs, LICENSE

Dependencies: none.

Acceptance criteria:

- [x] `make lint` and `make test` pass with Redis and PostgreSQL available (verified with locally built Redis 7.4 and PostgreSQL 17 via the `RACETRACE_TEST_*` URLs)
- [x] `racetrace run x.yaml` exits 2 with a "not implemented yet" message
- [x] Unsafe variant: crash at `job.db_committed` then recovery yields 2 ledger entries for one job; safe yields 2 executions and 1 ledger entry
- [x] Crash at `job.received` or `job.effect_written` yields 1 effect after recovery in both variants
- [ ] CI is green on GitHub, including Compose build (not verified locally; no Docker in the dev sandbox)

Risks: XAUTOCLAIM timing flakiness in tests; Compose files unverified until CI runs.

## Week 2: Checkpoint protocol and SDK

Estimate: 5 person-days. ([ADR 0001](docs/adr/0001-checkpoint-protocol.md))

Deliverables:

- [ ] `internal/checkpoints`: request/response types, protocol version 1
- [ ] Minimal controller HTTP server with `POST /v1/checkpoints` and internal hold/release
- [ ] SDK active mode: bounded blocking HTTP call, `RACETRACE_CHECKPOINT_TIMEOUT_MS`, `RACETRACE_ON_CONTROLLER_ERROR`
- [ ] Per-run bearer token
- [ ] Reference app talks to a local controller

Dependencies: Week 1.

Acceptance criteria:

- [ ] Go tests: hold, release, and `crash` response over HTTP
- [ ] SDK tests: timeout, connection refused, non-2xx, and malformed response each raise `ControllerUnavailableError` (or exit when configured)
- [ ] Every checkpoint event is recorded with `run_id`, `worker_id`, `seq`
- [ ] Inactive SDK performs no I/O (test)

Risks: blocking SDK call inside async frameworks; hold deadline versus SDK deadline mismatch.

## Week 3: Fault injection and Docker orchestration

Estimate: 6 person-days. ([ADR 0002](docs/adr/0002-local-first-docker-compose.md))

Deliverables:

- [ ] `internal/docker`: Compose project create/teardown via the `docker` CLI, scoped by project label
- [ ] `internal/faults`: `Fault` interface and `kill-worker` (`docker kill --signal SIGKILL`)
- [ ] Controller reachable from containers on Linux (and a documented macOS path)
- [ ] Recovery worker start
- [ ] Teardown always attempted; `--keep` flag

Dependencies: Week 2.

Acceptance criteria:

- [ ] A hard-coded run kills the worker at `job.db_committed` and a replacement worker finishes the job
- [ ] Only containers in the `rt-<run-id>` project are affected (test with an unrelated container present)
- [ ] Teardown removes the project after success and after induced error

Risks: Docker kill latency versus checkpoint hold; host networking differences; cleanup after controller crash.

## Week 4: Invariants, scenarios, E2E; release v0.1

Estimate: 6 person-days.

Deliverables:

- [ ] YAML scenario parser and validation (`version: 1`)
- [ ] `internal/assertions`: read-only Postgres assertions, stream-pending assertion
- [ ] `internal/report`: `report.json`, `events.jsonl`, terminal summary
- [ ] `racetrace run` and `racetrace report` implemented; outcome classification with documented precedence
- [ ] E2E scenarios on the reference app: unsafe fails (exit 1), safe passes (exit 0)
- [ ] Release v0.1 notes

Dependencies: Week 3.

Acceptance criteria:

- [ ] `racetrace run` on the unsafe scenario exits 1 and the report names the violated invariant
- [ ] Same on the safe variant exits 0
- [ ] Harness error, recovery timeout, and application failure each have a test producing the right exit code
- [ ] Assertions cannot write (read-only transaction test)

Risks: invariant queries coupling to the schema; recovery deadline flakiness.

## Week 5: Automatic exploration

Estimate: 5 person-days.

Deliverables:

- [ ] Checkpoint discovery run
- [ ] `internal/explorer`: crash at each discovered checkpoint (failure matrix)
- [ ] `racetrace explore` with a matrix report

Dependencies: Week 4.

Acceptance criteria:

- [ ] On the reference app, the matrix shows violation only at `job.db_committed` for unsafe, and none for safe
- [ ] Each cell is an independent run with its own report

Risks: per-run startup cost; project reuse and state reset correctness.

## Week 6: Reliability and CI

Estimate: 5 person-days.

Deliverables:

- [ ] Cleanup of orphaned `rt-*` projects
- [ ] Timing hardening (readiness waits instead of sleeps)
- [ ] CI runs RaceTrace end to end on the reference app

Dependencies: Week 4 (Week 5 optional).

Acceptance criteria:

- [ ] 30 consecutive runs: the unsafe scenario is detected (exit 1) and the safe scenario passes (exit 0) every time. Any failure is investigated, not retried away.
- [ ] No leftover containers or networks after the 30 runs

Risks: XAUTOCLAIM and Docker timing flakiness.

## Week 7: Developer experience

Estimate: 4 person-days.

Deliverables:

- [ ] Clear error messages and `--help` for every command
- [ ] Scenario validation errors with line information
- [ ] Documented guide for instrumenting your own worker
- [ ] Optional: OpenTelemetry export design note

Dependencies: Week 4.

Acceptance criteria:

- [ ] A new developer can follow the docs to run the demo scenario without help (checked by a person other than the author)

Risks: scope creep into visualization.

## Week 8: Public release

Estimate: 4 person-days.

Deliverables:

- [ ] Versioned binaries and Python package publishing
- [ ] Release notes and known limitations
- [ ] Final documentation pass

Dependencies: Weeks 6 and 7.

Acceptance criteria:

- [ ] Tagged release from `main` with CI green
- [ ] Docs accurately mark any still-planned features

Risks: packaging across platforms.

## Later (unscheduled)

OpenTelemetry integration, React/TypeScript visualization, additional faults (pause/resume, delay, duplicate delivery, network faults), competing-schedule exploration.

## Technical risks

| Risk | Mitigation direction |
| --- | --- |
| XAUTOCLAIM timing flakiness (min-idle versus test timing) | Poll idle time and pending ownership before recovery; avoid fixed sleeps; set min-idle above processing time |
| Docker kill latency versus checkpoint hold | Hold deadline shorter than SDK deadline; confirm kill before release; `crash` response as fallback |
| Container networking to a host controller: Linux versus macOS (`host.docker.internal`) | Per-platform bind and address strategy; document both |
| Cleanup when the controller crashes | Label-scoped orphan sweep for `rt-*` projects |
| SDK blocking inside async frameworks | Decide in Week 2: document, or provide an async-safe path |
| Python SIGKILL versus container kill semantics | Prefer container kill; self-kill only as fallback; test both |
| Startup cost per run during exploration | Reuse project and reset state (not designed yet) |
| Compose files unverified locally | CI validates and builds; treat as unverified until CI is green |
