CREATE TABLE IF NOT EXISTS job_executions (
 id bigserial PRIMARY KEY, job_id text, worker_id text, redis_message_id text,
 delivery_count int NULL, executed_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS ledger_entries (
 id bigserial PRIMARY KEY, job_id text NOT NULL, account_id text NOT NULL,
 amount_cents bigint NOT NULL, created_at timestamptz DEFAULT now()
);
