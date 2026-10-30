# Contributing

RaceTrace is in early development. Read [README.md](README.md) for what exists and [ROADMAP.md](ROADMAP.md) for what is planned.

## Setup

- Go 1.24+
- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Docker with Compose (for the easy path to Redis and PostgreSQL)

```sh
make sync    # uv sync --all-packages
```

## Running checks

```sh
make lint    # gofmt -l, go vet, ruff check, ruff format --check
make test    # go test ./... and uv run pytest
make build   # bin/racetrace
make fmt     # gofmt -w and ruff format/--fix
```

Run `make lint test` before opening a PR.

### Integration tests and backing services

Python integration tests need Redis and PostgreSQL:

```sh
make up      # docker compose up -d --wait redis postgres
make test
make down    # docker compose down -v --remove-orphans
```

Environment variables:

| Variable | Default (Makefile) |
| --- | --- |
| `RACETRACE_TEST_REDIS_URL` | `redis://127.0.0.1:6379/0` |
| `RACETRACE_TEST_DATABASE_URL` | `postgresql://racetrace:racetrace@127.0.0.1:5432/racetrace` |

If either is unset, integration tests skip with an explicit reason. CI sets `RACETRACE_REQUIRE_INTEGRATION=1` so they fail instead of skipping; set it locally to get the same behavior.

To run without Docker, point both variables at any Redis 7+ and PostgreSQL 14+ you control. Tests create and drop isolated schemas and streams, but use a non-production instance anyway. The reference app is developed against Redis 7.4 and PostgreSQL 17; older versions are not verified here.

## Conventions

- Go: `gofmt` and `go vet` clean. Prefer the standard library.
- Python: `ruff check` and `ruff format`. The SDK (`sdk/python`) stays stdlib-only.
- Keep PRs small and focused, with tests for behavior changes.
- Keep implemented and planned behavior clearly separated in docs. Do not claim deterministic replay, exactly-once processing, or performance numbers.
- Update [ROADMAP.md](ROADMAP.md) checkboxes only for items you have verified.
- Record significant design decisions as ADRs in `docs/adr/` (Status, Context, Decision, Consequences, Alternatives considered).
- Use the terms in [CONTEXT.md](CONTEXT.md).
- The reference app's `unsafe` variant is deliberately vulnerable. Do not fix it.

## Git workflow

- `dev` is the long-lived integration branch. Never commit to it directly.
- Create a feature or fix branch from `dev`; open a PR into `dev`.
- `main` is for releases only: `dev` is merged into `main` when cutting a release. Do not open feature PRs against `main`.

## Issues

Issues are tracked in GitHub Issues. Triage labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`.

## License

By contributing you agree that your contributions are licensed under the Apache License 2.0 (see [LICENSE](LICENSE)).
