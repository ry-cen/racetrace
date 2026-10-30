# Prioritized backlog

Priorities: P0 blocks the week's goal; P1 needed for the milestone; P2 improves it. Each task is small and testable. Implemented-vs-planned status is in [README.md](../README.md); the schedule is in [ROADMAP.md](../ROADMAP.md). Tick or remove tasks only when verified.

## Week 1 (in progress)

- [x] P0: Verify `make lint` and `make test` pass against live Redis and PostgreSQL. Test: both exit 0 with `RACETRACE_REQUIRE_INTEGRATION=1`. (verified locally with RACETRACE_REQUIRE_INTEGRATION=1: 27 passed.)
- [x] P0: Confirm the CI workflow passes on GitHub. Test: green run on the PR. ([PR #2 run](https://github.com/ry-cen/racetrace/actions/runs/40989121412))
- [ ] P1: Verify `examples/redis-worker/compose.yaml` and Dockerfile build and the demo works in Compose. Test: `make up` then the README demo yields the documented counts.
- [ ] P1: Reconcile docs commands with the Makefile and CLI. Test: each documented command runs.

## Week 2

- [ ] P0: Define protocol v1 Go types and JSON round-trip tests.
- [ ] P0: Implement `POST /v1/checkpoints` with hold and release. Test: held request blocks until release.
- [ ] P0: SDK active mode with bounded timeout. Test: each failure mode raises `ControllerUnavailableError`.
- [ ] P1: Per-run bearer token. Test: missing or wrong token gives 401.
- [ ] P1: `RACETRACE_ON_CONTROLLER_ERROR=exit` behavior. Test: process exits non-zero.
- [ ] P1: Record every checkpoint event in the timeline. Test: `seq` is monotonic per worker.
- [ ] P2: Decide and document the async-framework story for the blocking SDK call.

## Week 3

- [ ] P0: Compose project create/teardown wrapper using `-p rt-<run-id>`. Test: project created and removed.
- [ ] P0: `kill-worker` via `docker kill --signal SIGKILL`, scoped by project label. Test: unrelated container survives.
- [ ] P0: Container-to-host controller reachability on Linux. Test: worker in Compose reaches the controller.
- [ ] P1: Start replacement worker after the fault.
- [ ] P1: Teardown on error path and `--keep`. Test: induced failure still tears down.
- [ ] P2: Document the macOS (`host.docker.internal`) path.

## Week 4

- [ ] P0: Scenario YAML parser and validation. Test: invalid files give exit 2 with a clear message.
- [ ] P0: Read-only Postgres assertion runner. Test: write attempt fails.
- [ ] P0: Outcome classification with precedence. Test: table-driven over combined conditions.
- [ ] P0: `racetrace run` E2E on unsafe (exit 1) and safe (exit 0).
- [ ] P1: Redis stream-pending assertion.
- [ ] P1: `report.json` and `events.jsonl`; `racetrace report <run-id>`.
- [ ] P1: Terminal summary.
- [ ] P2: v0.1 release notes.

## Week 5

- [ ] P0: Checkpoint discovery run.
- [ ] P0: Failure matrix: one run per discovered checkpoint.
- [ ] P1: Matrix report. Test: unsafe violates only at `job.db_committed`.
- [ ] P2: Project reuse and state reset between attempts.

## Week 6

- [ ] P0: Orphaned `rt-*` project sweep. Test: leftover project removed.
- [ ] P0: Replace fixed sleeps with readiness waits.
- [ ] P0: 30 consecutive runs script and CI job. Test: every run classified correctly, no leftovers.
- [ ] P1: Flake log: record failed runs' artifacts in CI.

## Week 7

- [ ] P1: `--help` for every command.
- [ ] P1: Scenario error messages with line numbers.
- [ ] P1: Guide for instrumenting your own worker.
- [ ] P2: OpenTelemetry design note.

## Week 8

- [ ] P0: Release pipeline for binaries and the Python package.
- [ ] P0: Final docs pass for implemented versus planned accuracy.
- [ ] P1: Known limitations section.
