# 0003. At-least-once delivery with idempotent effects in the reference application

## Status

Accepted. Implemented in `examples/redis-worker` (Week 1).

## Context

The reference application (`examples/redis-worker`) consumes jobs from a Redis Streams consumer group and writes a business effect to PostgreSQL: it credits `amount_cents` to `account_id` for a `job_id` in `ledger_entries`. RaceTrace needs a system with a real, reproducible failure window to demonstrate on.

Per job, the worker acknowledges after the database commit: checkpoints `job.received`, BEGIN, insert execution and effect, `job.effect_written` (inside the transaction), COMMIT, `job.db_committed`, XACK, `job.acknowledged`. A crash between COMMIT and XACK leaves the message pending, and it is delivered again.

## Decision

- Redis Streams consumer groups provide at-least-once delivery. We do not claim exactly-once processing.
- Safety comes from an idempotent effect keyed by the business `job_id`: a `UNIQUE(job_id)` constraint on `ledger_entries` (migration 002) plus `INSERT ... ON CONFLICT (job_id) DO NOTHING`. An execution may happen twice (visible in `job_executions`); the effect happens once.
- The reference app has two variants. `unsafe` applies migration 001 only (no uniqueness). `safe` applies 001 and 002. The unsafe variant is deliberately vulnerable and must not be fixed; it is what RaceTrace is meant to catch.
- Recovery uses XAUTOCLAIM with a minimum idle threshold. It reclaims idle messages, not provably dead consumers, so it can take a message from a slow but live worker. The threshold (`REFWORKER_MIN_IDLE_MS`, default 5000) must exceed worst-case processing time.
- `job_executions` and `ledger_entries` are written in one transaction.

Observed behavior is characterized by the integration tests for these crash points only: after `job.db_committed`, unsafe yields two ledger entries for one job and safe yields two executions with one ledger entry; crashes at `job.received` or `job.effect_written` yield one effect in both variants because nothing was committed; a crash at `job.acknowledged` causes no redelivery.

## Consequences

- The demonstration is meaningful: the same crash is a violation in one variant and harmless in the other.
- Tests depending on idle times are timing-sensitive (XAUTOCLAIM flakiness is a tracked risk).
- Correctness depends on the application choosing a stable `job_id`; reuse of a `job_id` with a different payload is out of scope.
- The tests characterize these crash windows for this worker, not all failure modes.

## Alternatives considered

- Outbox or transactional acknowledgement: Redis is not transactional with PostgreSQL, so an ack cannot be made atomic with the commit.
- Storing stream offsets in PostgreSQL: moves delivery tracking out of Redis consumer groups, which would no longer exercise the semantics we want to test.
