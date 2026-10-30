import logging

from redis import Redis

from .config import parse_args
from .db import migrate
from .logging import configure
from .producer import enqueue_job
from .worker import work


def main():
    configure()
    args = parse_args()
    try:
        if args.command == "migrate":
            migrate(args.database_url, args.variant, args.db_schema)
        else:
            with Redis.from_url(
                args.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=getattr(args, "block_ms", 1000) / 1000 + 5,
            ) as redis:
                if args.command == "produce":
                    for _ in range(args.count):
                        print(
                            enqueue_job(
                                redis,
                                args.stream,
                                account_id=args.account_id,
                                amount_cents=args.amount_cents,
                            )[0],
                            flush=True,
                        )
                else:
                    raise SystemExit(work(redis, args))
    except Exception:
        logging.getLogger(__name__).exception(
            "command_failed",
            extra={"fields": {"worker_id": getattr(args, "worker_id", None)}},
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
