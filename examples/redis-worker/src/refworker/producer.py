from uuid import uuid4


def enqueue_job(redis, stream, job_id=None, account_id="demo", amount_cents=100):
    """Reuse a job_id only with the same payload (a redelivery)."""
    job_id = job_id or str(uuid4())
    message_id = redis.xadd(
        stream,
        {"job_id": job_id, "account_id": account_id, "amount_cents": amount_cents},
    )
    return job_id, message_id
