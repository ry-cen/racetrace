# Prioritized backlog

Priorities: P0 blocks the week's goal; P1 needed for the milestone; P2 improves it. Each task is small and testable. Implemented-vs-planned status is in [README.md](../README.md); the schedule is in [ROADMAP.md](../ROADMAP.md). Tick or remove tasks only when verified. Each open task is tracked as a GitHub issue (labels `P0`/`P1`/`P2`, one milestone per week); close the issue and tick the box together.

## Week 1

- [x] P0: Verify `make lint` and `make test` pass against live Redis and PostgreSQL. Test: both exit 0 with `RACETRACE_REQUIRE_INTEGRATION=1`. (verified locally with RACETRACE_REQUIRE_INTEGRATION=1: 27 passed.)
- [x] P0: Confirm the CI workflow passes on GitHub. Test: green run on the PR. ([PR #2 run](https://github.com/ry-cen/racetrace/actions/runs/40989121412))
- [ ] P1: Verify `examples/redis-worker/compose.yaml` and Dockerfile build and the demo works in Compose. Test: `make up` then the README demo yields the documented counts. ([#3](https://github.com/ry-cen/racetrace/issues/3))
- [ ] P1: Reconcile docs commands with the Makefile and CLI. Test: each documented command runs. ([#4](https://github.com/ry-cen/racetrace/issues/4))

## Week 2

- [ ] P0: Define protocol v1 Go types and JSON round-trip tests. ([#5](https://github.com/ry-cen/racetrace/issues/5))
- [ ] P0: Implement `POST /v1/checkpoints` with hold and release. Test: held request blocks until release. ([#6](https://github.com/ry-cen/racetrace/issues/6))
- [ ] P0: SDK active mode with bounded timeout. Test: each failure mode raises `ControllerUnavailableError`. ([#7](https://github.com/ry-cen/racetrace/issues/7))
- [ ] P1: Per-run bearer token. Test: missing or wrong token gives 401. ([#8](https://github.com/ry-cen/racetrace/issues/8))
- [ ] P1: `RACETRACE_ON_CONTROLLER_ERROR=exit` behavior. Test: process exits non-zero. ([#9](https://github.com/ry-cen/racetrace/issues/9))
- [ ] P1: Record every checkpoint event in the timeline. Test: `seq` is monotonic per worker. ([#10](https://github.com/ry-cen/racetrace/issues/10))
- [ ] P2: Decide and document the async-framework story for the blocking SDK call. ([#11](https://github.com/ry-cen/racetrace/issues/11))

## Week 3

- [ ] P0: Compose project create/teardown wrapper using `-p rt-<run-id>`. Test: project created and removed. ([#12](https://github.com/ry-cen/racetrace/issues/12))
- [ ] P0: `kill-worker` via `docker kill --signal SIGKILL`, scoped by project label. Test: unrelated container survives. ([#13](https://github.com/ry-cen/racetrace/issues/13))
- [ ] P0: Container-to-host controller reachability on Linux. Test: worker in Compose reaches the controller. ([#14](https://github.com/ry-cen/racetrace/issues/14))
- [ ] P1: Start replacement worker after the fault. ([#15](https://github.com/ry-cen/racetrace/issues/15))
- [ ] P1: Teardown on error path and `--keep`. Test: induced failure still tears down. ([#16](https://github.com/ry-cen/racetrace/issues/16))
- [ ] P2: Document the macOS (`host.docker.internal`) path. ([#17](https://github.com/ry-cen/racetrace/issues/17))

## Week 4

- [ ] P0: Scenario YAML parser and validation. Test: invalid files give exit 2 with a clear message. ([#18](https://github.com/ry-cen/racetrace/issues/18))
- [ ] P0: Read-only Postgres assertion runner. Test: write attempt fails. ([#19](https://github.com/ry-cen/racetrace/issues/19))
- [ ] P0: Outcome classification with precedence. Test: table-driven over combined conditions. ([#20](https://github.com/ry-cen/racetrace/issues/20))
- [ ] P0: `racetrace run` E2E on unsafe (exit 1) and safe (exit 0). ([#21](https://github.com/ry-cen/racetrace/issues/21))
- [ ] P1: Redis stream-pending assertion. ([#22](https://github.com/ry-cen/racetrace/issues/22))
- [ ] P1: `report.json` and `events.jsonl`; `racetrace report <run-id>`. ([#23](https://github.com/ry-cen/racetrace/issues/23))
- [ ] P1: Terminal summary. ([#24](https://github.com/ry-cen/racetrace/issues/24))
- [ ] P2: v0.1 release notes. ([#25](https://github.com/ry-cen/racetrace/issues/25))

## Week 5

- [ ] P0: Checkpoint discovery run. ([#26](https://github.com/ry-cen/racetrace/issues/26))
- [ ] P0: Failure matrix: one run per discovered checkpoint. ([#27](https://github.com/ry-cen/racetrace/issues/27))
- [ ] P1: Matrix report. Test: unsafe violates only at `job.db_committed`. ([#28](https://github.com/ry-cen/racetrace/issues/28))
- [ ] P2: Project reuse and state reset between attempts. ([#29](https://github.com/ry-cen/racetrace/issues/29))

## Week 6

- [ ] P0: Orphaned `rt-*` project sweep. Test: leftover project removed. ([#30](https://github.com/ry-cen/racetrace/issues/30))
- [ ] P0: Replace fixed sleeps with readiness waits. ([#31](https://github.com/ry-cen/racetrace/issues/31))
- [ ] P0: 30 consecutive runs script and CI job. Test: every run classified correctly, no leftovers. ([#32](https://github.com/ry-cen/racetrace/issues/32))
- [ ] P1: Flake log: record failed runs' artifacts in CI. ([#33](https://github.com/ry-cen/racetrace/issues/33))

## Week 7

- [ ] P1: `--help` for every command. ([#34](https://github.com/ry-cen/racetrace/issues/34))
- [ ] P1: Scenario error messages with line numbers. ([#35](https://github.com/ry-cen/racetrace/issues/35))
- [ ] P1: Guide for instrumenting your own worker. ([#36](https://github.com/ry-cen/racetrace/issues/36))
- [ ] P2: OpenTelemetry design note. ([#37](https://github.com/ry-cen/racetrace/issues/37))

## Week 8

- [ ] P0: Release pipeline for binaries and the Python package. ([#38](https://github.com/ry-cen/racetrace/issues/38))
- [ ] P0: Final docs pass for implemented versus planned accuracy. ([#39](https://github.com/ry-cen/racetrace/issues/39))
- [ ] P1: Known limitations section. ([#40](https://github.com/ry-cen/racetrace/issues/40))
