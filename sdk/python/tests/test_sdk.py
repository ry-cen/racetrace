import json
import os
import subprocess
import sys

import pytest
import racetrace


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in os.environ:
        if key.startswith("RACETRACE_"):
            monkeypatch.delenv(key)
    racetrace._reset_for_tests()
    yield
    racetrace._reset_for_tests()


def test_disabled_no_io_or_metadata(monkeypatch, capsys):
    class Poison:
        def __str__(self):
            raise AssertionError("metadata inspected")

    monkeypatch.setattr(os, "kill", lambda *_: pytest.fail("kill called"))
    racetrace.checkpoint("x", value=Poison())
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    "restriction,job,code", [(None, "a", -9), ("a", "a", -9), ("a", "b", 0)]
)
def test_crash_subprocess(restriction, job, code):
    env = {**os.environ, "RACETRACE_LOCAL_CRASH_AT": "match"}
    if restriction:
        env["RACETRACE_LOCAL_CRASH_JOB_ID"] = restriction
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            f'import racetrace; racetrace.checkpoint("other", job_id={job!r}); racetrace.checkpoint("match", job_id={job!r})',
        ],
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == code, result.stderr
    if code == -9:
        assert json.loads(result.stderr)["checkpoint"] == "match"


def test_controller_precedence(monkeypatch):
    monkeypatch.setenv("RACETRACE_CONTROLLER_URL", "http://localhost:1")
    monkeypatch.setenv("RACETRACE_LOCAL_CRASH_AT", "match")
    with pytest.raises(racetrace.ControllerUnavailableError):
        racetrace.checkpoint("match")


def test_context_cached(monkeypatch):
    monkeypatch.setenv("RACETRACE_RUN_ID", "run")
    monkeypatch.setenv("RACETRACE_WORKER_ID", "worker")
    assert racetrace.context() == {"run_id": "run", "worker_id": "worker"}
    monkeypatch.setenv("RACETRACE_RUN_ID", "changed")
    assert racetrace.context()["run_id"] == "run"


def test_crash_preserves_caller_identity(monkeypatch, capsys):
    monkeypatch.setenv("RACETRACE_LOCAL_CRASH_AT", "match")
    monkeypatch.setattr(os, "kill", lambda *_: None)
    racetrace.checkpoint("match", worker_id="caller")
    assert json.loads(capsys.readouterr().err)["worker_id"] == "caller"
