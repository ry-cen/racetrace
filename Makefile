# RaceTrace developer commands. See CONTRIBUTING.md.

COMPOSE := docker compose -f examples/redis-worker/compose.yaml

# Defaults match examples/redis-worker/compose.yaml's published ports.
RACETRACE_TEST_REDIS_URL ?= redis://127.0.0.1:6379/0
RACETRACE_TEST_DATABASE_URL ?= postgresql://racetrace:racetrace@127.0.0.1:5432/racetrace
export RACETRACE_TEST_REDIS_URL RACETRACE_TEST_DATABASE_URL

.PHONY: all build test test-go test-python lint lint-go lint-python fmt sync up down clean

all: lint test build

build:
	go build -o bin/racetrace ./cmd/racetrace

sync:
	uv sync --all-packages

test: test-go test-python

test-go:
	go test ./...

# Needs Redis and PostgreSQL (`make up`, or point the RACETRACE_TEST_* URLs elsewhere).
test-python: sync
	uv run pytest

lint: lint-go lint-python

lint-go:
	@unformatted="$$(gofmt -l .)"; if [ -n "$$unformatted" ]; then echo "gofmt needed:"; echo "$$unformatted"; exit 1; fi
	go vet ./...

lint-python: sync
	uv run ruff check .
	uv run ruff format --check .

fmt:
	gofmt -w .
	uv run ruff format .
	uv run ruff check --fix .

# Start only the backing services for local tests.
up:
	$(COMPOSE) up -d --wait redis postgres

down:
	$(COMPOSE) down -v --remove-orphans

clean:
	rm -rf bin
