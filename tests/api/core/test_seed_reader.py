"""Seed reads follow file changes (review: new trends must reach saved plans)."""

import os
from pathlib import Path

import pytest

from app.core import seed


def _write(path: Path, text: str, mtime_ns: int) -> None:
    path.write_text(text, encoding="utf-8")
    os.utime(path, ns=(mtime_ns, mtime_ns))


def test_replaced_file_is_read_again(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(seed, "SEED_DIR", tmp_path)
    (tmp_path / "trends").mkdir()
    target = tmp_path / "trends" / "snapshots.csv"
    _write(target, "id,version\n1,mock-0\n", 1_000_000_000)
    assert [r["version"] for r in seed.rows("trends", "snapshots")] == ["mock-0"]
    _write(target, "id,version\n1,mock-0\n2,live-1\n", 2_000_000_000)
    assert [r["version"] for r in seed.rows("trends", "snapshots")] == ["mock-0", "live-1"]


def test_missing_file_is_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(seed, "SEED_DIR", tmp_path)
    assert seed.rows("nowhere", "nothing") == ()
