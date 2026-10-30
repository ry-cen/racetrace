import os
import subprocess
import sys
import time
from contextlib import contextmanager
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from redis import Redis
from refworker.db import connect
from refworker.producer import enqueue_job


@pytest.fixture
def demo(tmp_path):
    redis_url = os.getenv("RACETRACE_TEST_REDIS_URL")
    database_url = os.getenv("RACETRACE_TEST_DATABASE_URL")
    if not redis_url or not database_url:
        unavailable = (
            pytest.fail
            if os.getenv("RACETRACE_REQUIRE_INTEGRATION") == "1"
            else pytest.skip
        )
        unavailable(
            "integration requires RACETRACE_TEST_REDIS_URL and RACETRACE_TEST_DATABASE_URL"
        )
    schema = "rt_" + uuid4().hex
    stream = schema + ":jobs"
    group = schema
    processes = []
    logs = []
    redis = Redis.from_url(
        redis_url, decode_responses=True, socket_timeout=3, socket_connect_timeout=3
    )
    admin = psycopg.connect(
        database_url,
        autocommit=True,
        connect_timeout=5,
        options="-cstatement_timeout=5000",
    )
    admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("RACETRACE_") and not k.startswith("REFWORKER_")
    }
    env.update(
        REDIS_URL=redis_url,
        DATABASE_URL=database_url,
        REFWORKER_DB_SCHEMA=schema,
        REFWORKER_STREAM=stream,
        REFWORKER_GROUP=group,
    )

    class Demo:
        client = redis
        stream_name = stream
        group_name = group

        def run(self, command, *flags, crash=None, worker="A"):
            child_env = {**env, "REFWORKER_WORKER_ID": worker}
            if crash:
                child_env["RACETRACE_LOCAL_CRASH_AT"] = crash
            path = tmp_path / f"process-{len(processes)}.log"
            handle = path.open("w+")
            logs.append(handle)
            process = subprocess.Popen(
                [sys.executable, "-m", "refworker", command, *flags],
                env=child_env,
                stdout=handle,
                stderr=handle,
            )
            processes.append(process)
            return process

        def output(self):
            for handle in logs:
                handle.flush()
            return "\n".join(p.read_text() for p in sorted(tmp_path.glob("*.log")))

        def wait(self, process, code=0):
            try:
                actual = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pytest.fail("worker deadline exceeded\n" + self.output())
            assert actual == code, self.output()

        def migrate(self, variant):
            self.wait(self.run("migrate", "--variant", variant))

        def enqueue(self):
            return enqueue_job(redis, stream)

        def worker(self, variant, crash=None, worker="A", max_jobs="1"):
            return self.run(
                "work",
                "--variant",
                variant,
                "--min-idle-ms",
                "100",
                "--block-ms",
                "20",
                "--max-jobs",
                max_jobs,
                "--idle-exit-ms",
                "500",
                "--deadline-ms",
                "3000",
                crash=crash,
                worker=worker,
            )

        def pending(self):
            return redis.xpending_range(stream, group, "-", "+", 10)

        def state(self, effects, deliveries, job):
            with connect(database_url, schema) as conn:
                rows = conn.execute(
                    "SELECT job_id, delivery_count FROM job_executions ORDER BY id"
                ).fetchall()
                entries = conn.execute("SELECT job_id FROM ledger_entries").fetchall()
            assert rows == [(job, n) for n in deliveries], self.output()
            assert entries == [(job,)] * effects, self.output()

        @contextmanager
        def effects_locked(self):
            """Block ledger inserts from other sessions while the block is open."""
            with connect(database_url, schema) as conn, conn.transaction():
                conn.execute("LOCK TABLE ledger_entries IN EXCLUSIVE MODE")
                yield

        def wait_for(self, text):
            deadline = time.monotonic() + 5
            while text not in self.output():
                assert time.monotonic() < deadline, self.output()
                time.sleep(0.01)

        def idle(self):
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                pending = self.pending()
                if pending and pending[0]["time_since_delivered"] >= 140:
                    return
                time.sleep(0.01)
            pytest.fail("pending message did not become idle\n" + self.output())

    try:
        yield Demo()
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
        for handle in logs:
            handle.close()
        redis.delete(stream)
        redis.close()
        admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        admin.close()


@pytest.mark.parametrize("variant", ["unsafe", "safe"])
def test_happy_path(demo, variant):
    demo.migrate(variant)
    job, _ = demo.enqueue()
    demo.wait(demo.worker(variant))
    demo.state(1, [1], job)
    assert demo.pending() == []


@pytest.mark.parametrize("variant", ["unsafe", "safe"])
def test_worker_effect_after_crash_post_commit(demo, variant):
    demo.migrate(variant)
    job, message = demo.enqueue()
    demo.wait(demo.worker(variant, "job.db_committed"), -9)
    demo.state(1, [1], job)
    pending = demo.pending()
    assert len(pending) == 1 and pending[0]["consumer"] == "A"
    assert pending[0]["message_id"] == message
    demo.idle()
    demo.wait(demo.worker(variant, worker="B"))
    demo.state(2 if variant == "unsafe" else 1, [1, 2], job)
    assert demo.pending() == []


@pytest.mark.parametrize("variant", ["unsafe", "safe"])
@pytest.mark.parametrize("checkpoint", ["job.received", "job.effect_written"])
def test_crash_before_commit(demo, variant, checkpoint):
    demo.migrate(variant)
    job, _ = demo.enqueue()
    demo.wait(demo.worker(variant, checkpoint), -9)
    demo.state(0, [], job)
    assert len(demo.pending()) == 1 and demo.pending()[0]["consumer"] == "A"
    demo.idle()
    demo.wait(demo.worker(variant, worker="B"))
    demo.state(1, [2], job)
    assert demo.pending() == []


@pytest.mark.parametrize("variant", ["unsafe", "safe"])
def test_crash_after_ack(demo, variant):
    demo.migrate(variant)
    job, _ = demo.enqueue()
    demo.wait(demo.worker(variant, "job.acknowledged"), -9)
    demo.state(1, [1], job)
    assert demo.pending() == []
    demo.wait(demo.worker(variant, worker="B"))
    demo.state(1, [1], job)


def test_safe_requires_constraint(demo):
    demo.migrate("unsafe")
    job, _ = demo.enqueue()
    demo.wait(demo.worker("safe"), 1)
    demo.state(0, [], job)
    assert len(demo.pending()) == 1
    assert "no unique or exclusion constraint" in demo.output()


def test_cli_produce_and_idempotent_migrations(demo):
    demo.migrate("safe")
    demo.migrate("safe")
    demo.wait(
        demo.run(
            "produce", "--count", "1", "--account-id", "cli", "--amount-cents", "25"
        )
    )
    demo.wait(demo.worker("safe"))
    assert demo.pending() == []


def test_service_accepts_work_after_idle_and_stops(demo):
    demo.migrate("safe")
    process = demo.run("work", "--variant", "safe", "--block-ms", "100")
    deadline = time.monotonic() + 3
    while not demo.client.exists(demo.stream_name):
        assert time.monotonic() < deadline, demo.output()
        time.sleep(0.01)
    time.sleep(0.3)
    assert process.poll() is None, demo.output()
    job, _ = demo.enqueue()
    deadline = time.monotonic() + 3
    while "job.acknowledged" not in demo.output():
        assert time.monotonic() < deadline, demo.output()
        time.sleep(0.01)
    process.terminate()
    assert process.wait(timeout=1) == 0, demo.output()
    demo.state(1, [1], job)
    assert demo.pending() == []


def test_deadline_caps_block_and_reports_incomplete(demo):
    demo.migrate("safe")
    process = demo.run("work", "--deadline-ms", "300", "--block-ms", "2000")
    startup_deadline = time.monotonic() + 5
    while "worker_started" not in demo.output():
        assert time.monotonic() < startup_deadline, demo.output()
        time.sleep(0.01)
    start = time.monotonic()
    assert process.wait(timeout=1) == 3, demo.output()
    assert time.monotonic() - start < 1
    assert "deadline_reached" in demo.output()


def test_recovery_scans_empty_batches_before_idle_exit(demo):
    demo.migrate("safe")
    client = demo.client
    stream, group = demo.stream_name, demo.group_name
    client.xgroup_create(stream, group, "0", mkstream=True)
    jobs = [demo.enqueue() for _ in range(31)]
    client.xreadgroup(group, "A", {stream: ">"}, count=31)
    # COUNT=1 scans at most ten pending entries per XAUTOCLAIM. Only the
    # final entry is eligible, forcing three empty batches with nonzero cursors.
    for _, message in jobs[:-1]:
        client.xclaim(stream, group, "A", 0, [message], idle=0)
    job, tail = jobs[-1]
    client.xclaim(stream, group, "A", 0, [tail], idle=200000)
    process = demo.run(
        "work",
        "--variant",
        "safe",
        "--worker-id",
        "B",
        "--min-idle-ms",
        "100000",
        "--block-ms",
        "2000",
        "--idle-exit-ms",
        "1",
        "--deadline-ms",
        "3000",
        "--max-jobs",
        "1",
    )
    demo.wait(process)
    demo.state(1, [3], job)
    assert client.xpending(stream, group)["pending"] == 30


def test_deadline_takes_precedence_over_max_jobs(demo):
    demo.migrate("safe")
    job, _ = demo.enqueue()
    with demo.effects_locked():
        process = demo.run(
            "work", "--deadline-ms", "300", "--max-jobs", "1", "--block-ms", "20"
        )
        demo.wait_for('"checkpoint": "job.received"')
        time.sleep(0.6)
    assert process.wait(timeout=5) == 3, demo.output()
    assert "deadline_reached" in demo.output()
    demo.state(1, [1], job)
