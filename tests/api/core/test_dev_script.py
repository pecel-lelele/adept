"""`make dev` must fail when one of its servers dies (review finding P2)."""

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

DEV_PY = Path(__file__).resolve().parents[3] / "src" / "scripts" / "dev.py"


def _load_dev() -> ModuleType:
    spec = importlib.util.spec_from_file_location("adept_dev_script", DEV_PY)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _child(code: str) -> subprocess.Popen[bytes]:
    return subprocess.Popen([sys.executable, "-c", code])


def test_supervise_raises_with_the_failed_childs_exit_code() -> None:
    dev = _load_dev()
    procs = {
        "API": _child("import time; time.sleep(30)"),
        "web": _child("import sys; sys.exit(3)"),
    }
    with pytest.raises(dev.TaskError, match=r"web server exited unexpectedly \(exit code 3\)"):
        dev.supervise(procs, poll_s=0.05)
    assert procs["API"].poll() is not None, "the surviving server must be stopped"


def test_supervise_treats_a_clean_exit_as_unexpected_too() -> None:
    dev = _load_dev()
    procs = {"API": _child("pass"), "web": _child("import time; time.sleep(30)")}
    with pytest.raises(dev.TaskError, match="API server exited unexpectedly"):
        dev.supervise(procs, poll_s=0.05)
