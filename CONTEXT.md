# RaceTrace domain glossary

Terms as RaceTrace uses them. Use these words in issues, tests, and docs; avoid the synonyms noted.

**Delivery**
One handing of a message to a consumer by the queue. At-least-once queues may deliver the same message more than once. Redis Streams tracks deliveries per consumer group; the delivery count is recorded in `job_executions`.

**Message id**
The queue's identifier for a message (a Redis stream entry id such as `1700000000000-0`). It identifies a message in the stream, not the business job. Do not use it as the idempotency key.

**Job**
A unit of background work requested by a producer. In the reference app, "credit `amount_cents` to `account_id`".

**job_id**
The business identifier of a job, chosen by the producer. It is the idempotency key for the effect. Redelivery of the same job reuses the same `job_id`.

**Execution**
One attempt by a worker to process a delivery of a job, recorded as a row in `job_executions` when its transaction commits. A job can have several executions.

**Effect**
The durable business change a job is meant to cause, for example a row in `ledger_entries`. Safe systems make the effect happen once even if executions happen more than once. Do not say "exactly-once processing"; say "idempotent effect".

**Checkpoint**
A named point in application code, marked with `checkpoint(name, **metadata)` from the SDK, at which RaceTrace may observe, hold, or fault the process. Example: `job.db_committed`. Checkpoints are application-level, not infrastructure events.

**Fault**
An action RaceTrace applies when a checkpoint is reached. Planned first fault: `kill-worker` (SIGKILL). Today the only fault is the Week 1 test-only `RACETRACE_LOCAL_CRASH_AT` self-kill.

**Invariant**
A business rule that must hold after recovery, such as "exactly one ledger entry per job" or "the queue is drained". Invariants are evaluated read-only.

**Run**
One execution of a scenario from environment creation through teardown, identified by a run id and producing a report.

**Scenario**
A YAML file (planned) that declares the environment, workload, fault, recovery, and invariants for a run.

**Recovery**
What happens after a fault so the system can finish its work: for example a replacement worker reclaiming a pending message. A recovery deadline bounds how long RaceTrace waits.

**Harness error**
A failure of RaceTrace itself or its environment (Docker, controller, database unreachable, unknown outcome). It means the application's correctness is unknown, and it is never reported as a pass. Exit code 3.
