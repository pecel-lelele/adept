"""Evidence/classification regressions for historical trend tooling; no live I/O."""

import json
import subprocess
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.contracts.common import TrendProvenance
from pipelines.trends import populate_dual_snapshot as replay
from pipelines.trends import provenance
from pipelines.trends.export_fixtures_from_db import export_snapshot

_MOVE = "a" * 40
_EDIT = "b" * 40
_BLOB_OLD = "1" * 40
_BLOB_NEW = "2" * 40
_PATH = "src/data/seed/mock_trends.json"
# Synthetic `git log --follow --raw` output: newest commit is a pure move (same blob).
_HISTORY = (
    f"@{_MOVE} 2026-10-24T18:44:48+08:00\n\n"
    f":100644 100644 {_BLOB_NEW} {_BLOB_NEW} R100\told/{_PATH}\t{_PATH}\n"
    f"@{_EDIT} 2026-10-20T19:05:33+08:00\n\n"
    f":100644 100644 {_BLOB_OLD} {_BLOB_NEW} M\told/{_PATH}\n"
)


def test_commit_fallback_is_evidenced_day_precision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, _HISTORY),
    )
    result = provenance.git_commit_retrieval(provenance.ROOT / "src/data/seed/mock_trends.json")
    # A pure move/re-layout never makes a static artifact look newer than its content.
    assert result["retrieved_at"] == "2026-10-20"
    assert result["retrieved_at_basis"] == "git_commit_date"
    assert _EDIT in result["retrieval_evidence"]
    assert _MOVE not in result["retrieval_evidence"]
    assert "fetch time unverified" in result["retrieval_evidence"]


def test_bls_baseline_sidecar_dates_the_content_commit_not_the_move() -> None:
    evidence = json.loads(
        (provenance.ROOT / "src/data/seed/labor_decay.provenance.json").read_text("utf-8")
    )
    assert evidence["retrieved_at"] == "2026-10-20"
    assert "750fa30225a8012e2dec52ccd6a7932d896c49a4" in evidence["retrieval_evidence"]
    assert "8a5a460" not in evidence["retrieval_evidence"]
    assert (
        provenance.cached_retrieval(provenance.ROOT / "src/data/seed/labor_decay.csv") == evidence
    )


def test_missing_commit_and_fetch_evidence_cannot_invent_a_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "")
    )
    with pytest.raises(ValueError, match="No fetch evidence"):
        provenance.git_commit_retrieval(provenance.ROOT / "src/data/seed/mock_trends.json")


def test_fetch_evidence_is_bound_to_the_cached_bytes(tmp_path: Path) -> None:
    cache = tmp_path / "synthetic-research.json"
    cache.write_text("[]", encoding="utf-8")
    provenance.record_fetch(cache, "https://example.test/synthetic-research")
    evidence = provenance.cached_retrieval(cache)
    assert evidence["retrieved_at_basis"] == "pipeline_fetch"
    assert evidence["fetched_at"].startswith(evidence["retrieved_at"])
    assert "sha256=" in evidence["retrieval_evidence"]
    cache.write_text('["changed"]', encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        provenance.cached_retrieval(cache)


@pytest.mark.parametrize(
    "missing", ["observation_window_start", "retrieved_at", "retrieval_evidence"]
)
def test_replay_classification_requires_its_evidence(missing: str) -> None:
    values = {
        "is_replay": True,
        "observation_window_start": "2024-10-13",
        "observation_window_end": "2024-10-19",
        "retrieved_at": "2026-10-24",
        "retrieved_at_basis": "git_commit_date",
        "retrieval_evidence": "synthetic commit evidence",
    }
    values.pop(missing)
    with pytest.raises(ValidationError):
        TrendProvenance.model_validate(values)


def test_retired_replay_generator_exits_without_writing() -> None:
    # The bootstrap relabelled October 2024 windows as 2026 signals; it is retired (M1-015).
    with pytest.raises(SystemExit, match="Retired"):
        replay.run()


def test_committed_fixtures_freeze_retrieval_evidence_independently_of_slot() -> None:
    for path in (provenance.ROOT / "src/data/seed").glob("mock_trends*.json"):
        raw = json.loads(path.read_text(encoding="utf-8"))
        meta = TrendProvenance.model_validate(raw["meta"])
        assert meta.is_replay is True
        assert meta.observation_window_start.year == 2024
        # Retrieval is evidenced by the commit that last changed the fixture's data (it can
        # coincide with a slot label, as for 2026-10-20, but is never derived from it), and
        # never by a later move/metadata commit.
        assert "git:8005c5f4974df5953b9209475e88abcf9a32e7f9" in meta.retrieval_evidence
        assert meta.retrieved_at.isoformat() == "2026-10-20"
        assert meta.retrieved_at_basis == "git_commit_date"
        for source in raw["meta"]["sources"]:
            assert source["retrieved_at_basis"] == "git_commit_date"
            assert source["retrieved_at"] <= "2026-10-20"
            assert "8a5a4608" not in source["retrieval_evidence"]


def test_exporter_rejects_live_metadata_over_replay_rows() -> None:
    frozen = json.loads(
        (provenance.ROOT / "src/data/seed/mock_trends.json").read_text(encoding="utf-8")
    )
    meta = frozen["meta"]
    row = {
        **frozen["items"][0],
        **{
            key: meta[key]
            for key in (
                "is_replay",
                "observation_window_start",
                "observation_window_end",
                "retrieved_at",
                "retrieved_at_basis",
                "retrieval_evidence",
            )
        },
    }
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = [row]
    cursor.fetchone.return_value = {
        **meta,
        "is_replay": False,
        "retrieved_at_basis": "fetch_log",
        "provenance_note": "Synthetic conflicting metadata",
    }
    with pytest.raises(ValueError, match="Conflicting stored"):
        export_snapshot(connection, "2026-10-20", {})


def test_exporter_cannot_infer_observations_from_a_known_slot_alone() -> None:
    frozen = json.loads(
        (provenance.ROOT / "src/data/seed/mock_trends.json").read_text(encoding="utf-8")
    )
    rows = frozen["items"]
    rows[0]["research_velocity"] += 1
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = rows
    cursor.fetchone.return_value = {}
    with pytest.raises(ValueError, match="does not match its cited replay fixture"):
        export_snapshot(connection, "2026-10-20", {})


def test_commit_fallback_cannot_be_classified_as_live_ingestion() -> None:
    with pytest.raises(ValidationError, match="cannot verify live"):
        TrendProvenance(
            is_replay=False,
            observation_window_start=date(2024, 10, 13),
            observation_window_end=date(2024, 10, 19),
            retrieved_at=date(2026, 10, 24),
            retrieved_at_basis="git_commit_date",
            retrieval_evidence="synthetic commit evidence",
        )
