"""The immutable alias collision is accepted only while its SQL is equivalent."""

from pathlib import Path

import pytest

from db import migrate


def test_the_known_alias_collision_is_applied_once() -> None:
    versions = [migrate.version_of(path) for path in migrate.pending(set())]
    assert len(versions) == len(set(versions))
    assert versions.count("20261021150000") == 1


def test_new_collisions_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ["a", "b"]:
        (tmp_path / f"20261030150000_{name}.sql").write_text(
            "-- migrate:up\nSELECT 1;\n-- migrate:down\nSELECT 1;", encoding="utf-8"
        )
    monkeypatch.setattr(migrate, "MIGRATIONS", tmp_path)
    with pytest.raises(ValueError, match="Conflicting migration"):
        migrate.pending(set())
