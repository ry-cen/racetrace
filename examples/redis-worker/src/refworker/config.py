import argparse
import os
import socket


def database_flags(parser):
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", "postgresql://localhost/postgres"),
    )
    parser.add_argument("--db-schema", default=os.getenv("REFWORKER_DB_SCHEMA"))
    parser.add_argument(
        "--variant",
        choices=("unsafe", "safe"),
        default=os.getenv("REFWORKER_VARIANT", "unsafe"),
    )


def redis_flags(parser):
    parser.add_argument(
        "--redis-url", default=os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
    parser.add_argument(
        "--stream", default=os.getenv("REFWORKER_STREAM", "racetrace:jobs")
    )


def parse_args():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    migrate = sub.add_parser("migrate")
    database_flags(migrate)
    produce = sub.add_parser("produce")
    redis_flags(produce)
    produce.add_argument("--count", type=int, default=1)
    produce.add_argument("--account-id", default="demo")
    produce.add_argument("--amount-cents", type=int, default=100)
    work = sub.add_parser("work")
    database_flags(work)
    redis_flags(work)
    work.add_argument("--group", default=os.getenv("REFWORKER_GROUP", "refworker"))
    work.add_argument(
        "--worker-id",
        default=os.getenv(
            "REFWORKER_WORKER_ID", f"{socket.gethostname()}-{os.getpid()}"
        ),
    )
    work.add_argument(
        "--min-idle-ms", type=int, default=os.getenv("REFWORKER_MIN_IDLE_MS", "5000")
    )
    work.add_argument(
        "--block-ms", type=int, default=os.getenv("REFWORKER_BLOCK_MS", "1000")
    )
    work.add_argument("--max-jobs", type=int, default=0)
    work.add_argument(
        "--idle-exit-ms", type=int, default=os.getenv("REFWORKER_IDLE_EXIT_MS", "0")
    )
    work.add_argument(
        "--deadline-ms", type=int, default=os.getenv("REFWORKER_DEADLINE_MS", "0")
    )
    args = parser.parse_args()
    if hasattr(args, "variant") and args.variant not in ("unsafe", "safe"):
        parser.error("variant must be unsafe or safe")
    for name in ("min_idle_ms", "max_jobs", "idle_exit_ms", "deadline_ms", "count"):
        if getattr(args, name, 0) < 0:
            parser.error(name.replace("_", "-") + " must be nonnegative")
    if args.command == "work" and args.block_ms <= 0:
        parser.error("block-ms must be positive")
    return args
