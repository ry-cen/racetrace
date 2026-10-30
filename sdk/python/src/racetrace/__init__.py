"""Week 1 checkpoint SDK; local SIGKILL is a pre-controller development aid.

The Week 2 controller will supersede the local crash trigger. Configuration is
cached on first use. Disabled checkpoints perform no I/O or metadata processing.
"""

import json
import os
import signal
import sys
from functools import lru_cache


class ControllerUnavailableError(RuntimeError):
    """The configured controller protocol is not implemented in Week 1."""


@lru_cache(maxsize=1)
def _config():
    return tuple(
        os.environ.get(k)
        for k in (
            "RACETRACE_CONTROLLER_URL",
            "RACETRACE_LOCAL_CRASH_AT",
            "RACETRACE_LOCAL_CRASH_JOB_ID",
            "RACETRACE_RUN_ID",
            "RACETRACE_WORKER_ID",
        )
    )


def context():
    config = _config()
    return {"run_id": config[3], "worker_id": config[4]}


def _reset_for_tests():
    _config.cache_clear()


def checkpoint(name: str, **metadata) -> None:
    controller, crash_at, job_id, _, _ = _config()
    if controller:
        raise ControllerUnavailableError(
            "Week 2 controller protocol is not implemented"
        )
    if not crash_at:
        return
    if name == crash_at and (job_id is None or metadata.get("job_id") == job_id):
        print(
            json.dumps(
                {
                    **metadata,
                    **{k: v for k, v in context().items() if v is not None},
                    "checkpoint": name,
                    "event": "local_crash",
                }
            ),
            file=sys.stderr,
            flush=True,
        )
        os.kill(os.getpid(), signal.SIGKILL)
