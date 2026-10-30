import os
import subprocess
import sys
from pathlib import Path

import pytest
from refworker.config import parse_args


@pytest.mark.parametrize("required", [False, True])
def test_missing_integration_urls(required):
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("RACETRACE_")
    }
    if required:
        env["RACETRACE_REQUIRE_INTEGRATION"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            str(Path(__file__).with_name("test_integration.py")),
            "-k",
            "test_safe_requires_constraint",
        ],
        check=False,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == (1 if required else 0), result.stdout + result.stderr
    assert ("1 error" if required else "1 skipped") in result.stdout


@pytest.mark.parametrize("flag", ["--idle-exit-ms", "--deadline-ms"])
def test_optional_limits_accept_zero_reject_negative(monkeypatch, flag):
    monkeypatch.setattr(sys, "argv", ["refworker", "work", flag, "0"])
    assert getattr(parse_args(), flag[2:].replace("-", "_")) == 0
    monkeypatch.setattr(sys, "argv", ["refworker", "work", flag, "-1"])
    with pytest.raises(SystemExit) as error:
        parse_args()
    assert error.value.code == 2
