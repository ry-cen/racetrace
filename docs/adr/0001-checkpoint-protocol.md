# 0001. Checkpoint protocol: HTTP/JSON long-poll

## Status

Accepted (implementation planned for Week 2). Nothing in this ADR is implemented today. The Python SDK currently raises `ControllerUnavailableError` when `RACETRACE_CONTROLLER_URL` is set.

## Context

RaceTrace injects faults at application-level checkpoints. The SDK running inside the system under test must tell the controller (which runs on the host, outside application containers) that a worker reached a named point, and must wait while the controller decides whether to hold, release, or crash it.

Requirements:

- Work across a container boundary without mounting host sockets into application containers.
- Add no third-party dependencies to the SDK (it stays stdlib-only).
- Be easy to debug with `curl` and to implement in other languages later.
- Never silently proceed when the controller cannot be reached, because a missed checkpoint would make a run look like it tested something it did not.

## Decision

Transport is HTTP/1.1 with JSON bodies, using the standard library on both sides (Go `net/http`; Python `urllib` or `http.client`).

Request: `POST /v1/checkpoints` with body:

```json
{
  "protocol": 1,
  "run_id": "...",
  "worker_id": "...",
  "checkpoint": "job.db_committed",
  "seq": 7,
  "metadata": {},
  "pid": 123,
  "sent_at": "..."
}
```

`seq` is monotonic per worker. Correlation key is `run_id` + `worker_id` + `seq`. The controller records every checkpoint event in the run timeline.

Response (long-poll): the controller holds the request open while it decides or holds, then replies `{"action":"continue"}` or `{"action":"crash"}`. On `crash` the SDK sends itself SIGKILL; this is the fallback for when the controller cannot kill the container. For the `kill-worker` fault under Docker, the controller normally kills the container while the request is held, so no response arrives at all.

Release: an internal controller API (`/v1/holds/{id}/release`) is used by the controller itself and by tests. It is not part of the SDK surface.

Timeouts: the SDK has a total deadline, `RACETRACE_CHECKPOINT_TIMEOUT_MS` (default 30000). The controller hold deadline must be shorter than the SDK deadline. On timeout, connection refused, non-2xx status, or a malformed response, the SDK raises `ControllerUnavailableError` (default) or exits the process when `RACETRACE_ON_CONTROLLER_ERROR=exit`. It never silently continues.

Security: the controller binds to loopback or the Compose network gateway address only. A per-run random token is sent in `RACETRACE_CONTROLLER_TOKEN` as an `Authorization: Bearer` header. RaceTrace is a test-only tool and is not intended for production.

When the SDK is inactive (no controller configured), `checkpoint()` remains a no-op with no I/O.

## Consequences

- The protocol is simple to inspect and to implement in other languages, and needs no code generation.
- A blocking HTTP call inside an async framework will block the event loop; this is a known risk (see ROADMAP.md) and needs an explicit design in Week 2.
- Long-poll holds consume a connection and a controller goroutine per held checkpoint; hold deadlines must stay below SDK deadlines or the SDK will report a controller error instead of a hold.
- Reaching the controller from a container differs between Linux and macOS/Docker Desktop (`host.docker.internal`); the bind-address rule above needs per-platform handling.
- The Week 1 `RACETRACE_LOCAL_CRASH_AT` trigger is a development aid that this protocol supersedes.

## Alternatives considered

- gRPC: adds dependencies and code generation to the SDK.
- WebSockets: more connection-state complexity than a per-checkpoint request needs.
- Unix sockets: do not cross the container boundary easily.
- Shared files or Redis as the channel: couples the harness to the system under test, so a fault in that system could corrupt the control path.
