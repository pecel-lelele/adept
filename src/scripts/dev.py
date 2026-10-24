"""Compatibility entry point for the relocated quality gate."""

import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
runpy.run_path(str(ROOT / "artifacts/api-server/python/src/scripts/dev.py"), run_name="__main__")
