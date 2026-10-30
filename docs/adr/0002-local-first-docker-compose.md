# 0002. Local-first execution with a disposable Docker Compose project per run

## Status

Accepted. The reference application's Compose file exists today; the controller that drives per-run projects is planned (Weeks 3 and 4).

## Context

RaceTrace must kill real worker processes against real Redis and PostgreSQL, then inspect the resulting state. Results are only meaningful if each run starts from clean state and cleanup cannot affect unrelated containers on the developer's machine.

## Decision

- Each run uses a unique Compose project named `rt-<run-id>`, where the run id is a short random lowercase string. Resources carry the `com.docker.compose.project` label.
- The controller kills only target containers resolved through that project. It never selects containers by image name or global filters.
- Teardown is `docker compose -p rt-<run-id> down -v --remove-orphans` with a deadline. It is always attempted, including after errors. A `--keep` flag will keep the project for debugging.
- The controller runs on the host and shells out to the `docker` CLI. There is no Docker SDK dependency initially.
- The Docker socket is never mounted into application containers.

## Consequences

- Docker is required locally.
- Each run pays a startup cost, which matters for exploration (Week 5). A later mitigation is to reuse a project and reset state between attempts; this is not designed yet.
- If the controller crashes, its project may be left behind. Cleanup of orphaned `rt-*` projects is a tracked risk.
- Container networking to a host-side controller differs on Linux and macOS.
- The Compose setup in `examples/redis-worker/compose.yaml` has not been verified locally in the development sandbox (no Docker there); CI is expected to validate and build it.

## Alternatives considered

- Kubernetes: heavy and slow for a local developer loop.
- testcontainers: ties the tool to each language's library.
- In-process fakes: miss the semantics of real Redis and PostgreSQL that the faults are meant to exercise.
