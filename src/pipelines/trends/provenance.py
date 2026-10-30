"""Fetch evidence for trend tooling; a replay slot is never a retrieval timestamp."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def git_commit_retrieval(path: Path) -> dict[str, str]:
    """Disclosed day-precision fallback from the last committed source artifact.

    A missing history is an error, never permission to use today/the slot date.
    The evidence is frozen in exported JSON, so later commits cannot move its date.
    """
    relative = path.resolve().relative_to(ROOT).as_posix()
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H%n%cI", "--", relative],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    lines = result.stdout.strip().splitlines()
    if len(lines) != 2:
        raise ValueError(f"No fetch evidence or committed source history for {relative}")
    commit, timestamp = lines
    day = datetime.fromisoformat(timestamp).astimezone(UTC).date().isoformat()
    return {
        "retrieved_at": day,
        "retrieved_at_basis": "git_commit_date",
        "retrieval_evidence": f"git:{commit}:{relative} (UTC commit date; fetch time unverified)",
    }


def record_fetch(path: Path, url: str) -> None:
    """Call only after a successful upstream fetch has been written to its cache."""
    instant = datetime.now(UTC)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    evidence = {
        "retrieved_at": instant.date().isoformat(),
        "fetched_at": instant.isoformat(),
        "retrieved_at_basis": "pipeline_fetch",
        "retrieval_evidence": f"{url}; fetched_at={instant.isoformat()}; sha256={digest}",
        "sha256": digest,
    }
    path.with_suffix(".provenance.json").write_text(json.dumps(evidence), encoding="utf-8")


def cached_retrieval(path: Path, fallback: Path | None = None) -> dict[str, str]:
    sidecar = path.with_suffix(".provenance.json")
    if sidecar.is_file():
        evidence = json.loads(sidecar.read_text(encoding="utf-8"))
        if evidence.get("sha256") != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError("Fetch evidence does not match cached research")
        return evidence
    try:
        return git_commit_retrieval(path)
    except ValueError:
        if fallback is None:
            raise
        return git_commit_retrieval(fallback)
