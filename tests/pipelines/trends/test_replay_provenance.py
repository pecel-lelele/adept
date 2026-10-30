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


def test_commit_fallback_is_evidenced_day_precision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args, 0, "8a5a4608c0a5907d85e5acf1b8fc246661bbfd2a\n2026-10-24T18:44:48+08:00\n"
        ),
    )
    result = provenance.git_commit_retrieval(provenance.ROOT / "src/data/seed/mock_trends.json")
    assert result["retrieved_at"] == "2026-10-24"
    assert result["retrieved_at_basis"] == "git_commit_date"
    assert "8a5a4608" in result["retrieval_evidence"]
    assert "fetch time unverified" in result["retrieval_evidence"]


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


def test_replay_generator_marks_both_raw_and_published_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = {
        "retrieved_at": "2026-10-24",
        "retrieved_at_basis": "git_commit_date",
        "retrieval_evidence": "synthetic fixture commit evidence",
    }
    monkeypatch.setattr(
        replay, "fetch_window_papers", lambda *args, **kwargs: [{"title": "Synthetic paper"}]
    )
    monkeypatch.setattr(replay, "load_skills", lambda: [("python", "Python")])
    monkeypatch.setattr(replay, "load_skill_vectors", lambda *args: {})
    monkeypatch.setattr(replay, "get_encoder", object)
    monkeypatch.setattr(replay, "count_mentions", lambda *args: {"python": 1})
    monkeypatch.setattr(replay, "cached_retrieval", lambda *args: evidence)
    monkeypatch.setattr(replay, "git_commit_retrieval", lambda *args: evidence)
    monkeypatch.setattr(replay.score, "load_skill_ids", lambda *args: {"python"})
    written: list[dict[str, object]] = []
    monkeypatch.setattr(
        replay, "write_signal_rows", lambda *args, **kwargs: written.append(kwargs["provenance"])
    )
    monkeypatch.setattr(
        replay, "publish", lambda *args, **kwargs: written.append(kwargs["provenance"])
    )
    replay.run()
    assert len(written) == 4
    assert [str(row["observation_window_start"]) for row in written] == [
        "2024-10-06",
        "2024-10-06",
        "2024-10-13",
        "2024-10-13",
    ]
    for row in written:
        parsed = TrendProvenance.model_validate(row)
        assert parsed.is_replay is True
        assert parsed.retrieved_at is not None and parsed.retrieved_at.isoformat() == "2026-10-24"


def test_committed_fixtures_freeze_retrieval_evidence_independently_of_slot() -> None:
    for path in (provenance.ROOT / "src/data/seed").glob("mock_trends*.json"):
        raw = json.loads(path.read_text(encoding="utf-8"))
        meta = TrendProvenance.model_validate(raw["meta"])
        assert meta.is_replay is True
        assert meta.observation_window_start.year == 2024
        assert meta.retrieved_at.isoformat() != raw["meta"]["snapshot_date"]
        assert meta.retrieved_at_basis == "git_commit_date"
        for source in raw["meta"]["sources"]:
            assert source["retrieved_at_basis"] == "git_commit_date"


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
