# AGENTS.md

Instructions for coding agents working on RaceTrace. Also read `CLAUDE.md` (git workflow and skill config), `docs/agents/*` (issue tracker is GitHub Issues via `gh`; triage labels `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`), [CONTEXT.md](CONTEXT.md) (glossary), and the ADRs in `docs/adr/`.

## Architecture boundaries

- The controller (Go) runs on the host, outside application containers.
- Never mount the Docker socket into application containers.
- Kill only containers resolved through the run's Compose project (`rt-<run-id>`). Never select by image name or global filters.
- The Python SDK (`sdk/python`) stays stdlib-only. Inactive `checkpoint()` must stay a no-op with no I/O.
- Never silently proceed when the controller is unreachable: raise or exit explicitly.
- A harness or infrastructure error is never a pass. Unknown outcomes map to exit code 3.
- Every wait needs a deadline. No unbounded retries.
- The reference app's `unsafe` variant is deliberately vulnerable. Do not fix it. Do not remove the safe variant's idempotency.
- Contradicting an ADR requires saying so explicitly.

## Implemented vs planned

Keep them separate in all docs and CLI messages. Today only the CLI skeleton, `internal/outcome`, the SDK's local behavior, and `examples/redis-worker` are implemented. Do not claim deterministic scheduling, exact replay, exactly-once processing, or performance numbers.

## Coding standards

- Go 1.24+: `gofmt`, `go vet`, standard library first.
- Python 3.11+: ruff check and format.
- Small PRs, tests with behavior changes.

## Tests to run

```sh
make lint
make test        # needs Redis and PostgreSQL: make up first, or set RACETRACE_TEST_REDIS_URL / RACETRACE_TEST_DATABASE_URL
```

Set `RACETRACE_REQUIRE_INTEGRATION=1` so missing services fail instead of skipping. If Docker is unavailable, say so in your report; do not claim Compose files are verified.

## Priorities

- Build vertical slices first (end to end, thin) before breadth.
- No speculative abstraction. Add an interface when a second implementation exists or is scheduled in ROADMAP.md.
- Follow the order in [ROADMAP.md](ROADMAP.md).

## Keep the roadmap current

Update [ROADMAP.md](ROADMAP.md) checkboxes as part of your change. Tick only items you have verified (by running the stated acceptance check). Do not tick on intent.

## Git workflow

Branch from `dev`, open a PR into `dev`. Never commit to `dev` or `main` directly. `main` is for releases only. Do not push or merge without approval from the human owner.
