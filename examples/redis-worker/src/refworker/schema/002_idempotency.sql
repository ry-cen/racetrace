DO $$ BEGIN
 IF NOT EXISTS (
  SELECT 1 FROM pg_constraint
  WHERE conrelid = 'ledger_entries'::regclass AND conname = 'ledger_entries_job_id_key'
 ) THEN
  ALTER TABLE ledger_entries ADD CONSTRAINT ledger_entries_job_id_key UNIQUE (job_id);
 END IF;
END $$;
