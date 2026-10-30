"""Fetch evidence for trend tooling; a replay slot is never a retrieval timestamp."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def last_content_commit(relative: str) -> tuple[str, str]:
    """(commit, ISO committer timestamp) of the newest commit that changed the file's bytes.

    Follows renames and skips pure moves (same blob before and after), so a repository
    re-layout never makes a static artifact look newer than its real acquisition.
    """
    result = subprocess.run(
        ["git", "log", "--follow", "--no-abbrev", "--raw", "--format=@%H %cI", "--", relative],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    current: tuple[str, str] | None = None
    for line in result.stdout.splitlines():
        if line.startswith("@"):
            commit, _, timestamp = line[1:].partition(" ")
            current = (commit, timestamp)
        elif line.startswith(":") and current is not None:
            fields = line[1:].split("\t", 1)[0].split()
            if len(fields) >= 4 and fields[2] != fields[3]:
                return current
    raise ValueError(f"No fetch evidence or committed source history for {relative}")


def git_commit_retrieval(path: Path) -> dict[str, str]:
    """Disclosed day-precision fallback from the last commit that changed the artifact.

    A missing history is an error, never permission to use today/the slot date. Pure moves
    do not count (see ``last_content_commit``). The evidence is frozen in exported JSON, so
    later commits cannot move its date.
    """
    relative = path.resolve().relative_to(ROOT).as_posix()
    commit, timestamp = last_content_commit(relative)
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
    """Read frozen, byte-bound evidence at runtime; never require repository history.

    Generate committed sidecars with the dev-time ``git_commit_retrieval`` helper.
    A missing sidecar is unverified data, including in images without Git installed.
    """
    sidecar = path.with_suffix(".provenance.json")
    if sidecar.is_file():
        evidence = json.loads(sidecar.read_text(encoding="utf-8"))
        if evidence.get("sha256") != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError("Fetch evidence does not match cached research")
        return evidence
    if fallback is not None:
        return cached_retrieval(fallback)
    raise ValueError(f"Missing committed or fetched provenance for {path.name}")
