"""Recover deliveries and commit executions with their business effects."""

import logging
import signal
import time

from racetrace import checkpoint
from redis.exceptions import ResponseError

from .db import connect

log = logging.getLogger(__name__)


def ensure_group(redis, args):
    """Create the group without hiding Redis errors other than BUSYGROUP."""
    try:
        redis.xgroup_create(args.stream, args.group, "0", mkstream=True)
    except ResponseError as error:
        if not str(error).startswith("BUSYGROUP "):
            raise


def claim_idle(redis, args, cursor):
    """Advance one bounded scan step; only cursor 0-0 completes a pass."""
    claimed = redis.xautoclaim(
        args.stream, args.group, args.worker_id, args.min_idle_ms, cursor, count=1
    )
    for deleted in claimed[2] if len(claimed) > 2 else []:
        log.info(
            "pending_deleted",
            extra={"fields": {"message_id": deleted, "worker_id": args.worker_id}},
        )
    return claimed[:2]


def read_new(redis, args, block_ms):
    """Read a delivery with a positive, bounded Redis BLOCK interval."""
    batches = redis.xreadgroup(
        args.group, args.worker_id, {args.stream: ">"}, count=1, block=block_ms
    )
    return batches[0][1] if batches else []


def mark(name, fields):
    log.info("checkpoint", extra={"fields": {**fields, "checkpoint": name}})
    checkpoint(name, **fields)


def process_message(redis, conn, args, message_id, payload):
    """Record an execution and effect together, then acknowledge its delivery.

    The inside-transaction checkpoint tests rollback; the post-commit checkpoint
    exposes the window where redelivery can repeat an already durable effect.
    """
    fields = {
        "worker_id": args.worker_id,
        "job_id": payload["job_id"],
        "message_id": message_id,
    }
    mark("job.received", fields)
    pending = redis.xpending_range(args.stream, args.group, message_id, message_id, 1)
    delivery_count = pending[0]["times_delivered"] if pending else None
    with conn.transaction():
        conn.execute(
            "INSERT INTO job_executions "
            "(job_id,worker_id,redis_message_id,delivery_count) VALUES (%s,%s,%s,%s)",
            (payload["job_id"], args.worker_id, message_id, delivery_count),
        )
        query = (
            "INSERT INTO ledger_entries (job_id,account_id,amount_cents) "
            "VALUES (%s,%s,%s)"
        )
        if args.variant == "safe":
            query += " ON CONFLICT (job_id) DO NOTHING"
        conn.execute(
            query,
            (payload["job_id"], payload["account_id"], int(payload["amount_cents"])),
        )
        mark("job.effect_written", fields)
    mark("job.db_committed", fields)
    redis.xack(args.stream, args.group, message_id)
    mark("job.acknowledged", fields)


def work(redis, args):
    stopped = False

    def stop(*_):
        nonlocal stopped
        stopped = True

    previous = {
        sig: signal.signal(sig, stop) for sig in (signal.SIGTERM, signal.SIGINT)
    }
    log.info("worker_started", extra={"fields": {"worker_id": args.worker_id}})
    deadline = time.monotonic() + args.deadline_ms / 1000 if args.deadline_ms else None

    def expired():
        if deadline is not None and time.monotonic() >= deadline:
            log.info(
                "deadline_reached", extra={"fields": {"worker_id": args.worker_id}}
            )
            return True
        return False

    try:
        ensure_group(redis, args)
        cursor = "0-0"
        done = 0
        last_work = time.monotonic()
        with connect(args.database_url, args.db_schema) as conn:
            while not stopped:
                if expired():
                    return 3
                cursor, messages = claim_idle(redis, args, cursor)
                if not messages:
                    if cursor != "0-0":
                        continue
                    if stopped:
                        break
                    if expired():
                        return 3
                    block_ms = args.block_ms
                    if deadline is not None:
                        block_ms = min(
                            block_ms, int((deadline - time.monotonic()) * 1000)
                        )
                        if block_ms <= 0:
                            continue
                    messages = read_new(redis, args, block_ms)
                for message_id, payload in messages:
                    if stopped:
                        return 0
                    if expired():
                        return 3
                    process_message(redis, conn, args, message_id, payload)
                    done += 1
                    last_work = time.monotonic()
                    # A run that overran its deadline is incomplete even if it
                    # reached max-jobs; report it as such.
                    if expired():
                        return 3
                    if args.max_jobs and done >= args.max_jobs:
                        return 0
                if expired():
                    return 3
                if (
                    cursor == "0-0"
                    and args.idle_exit_ms
                    and (time.monotonic() - last_work) * 1000 >= args.idle_exit_ms
                ):
                    return 0
        return 0
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
