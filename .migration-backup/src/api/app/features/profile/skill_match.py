"""Suggest catalogue skills for CV phrases that match no approved label or alias.

Exact alias matching (`cv_parser`) stays the source of truth. For the short entries of a CV's
skills list that it could not place ("workflow validation"), this module embeds the phrase,
finds the nearest catalogue skills by cosine similarity (pgvector `<=>` when the database is
in use, in memory otherwise) and proposes the best one only when it is close enough and
clearly ahead of the runner-up. A suggestion is never saved by itself: the person adds it.

Catalogue vectors live in `catalogue_embeddings`, one row per skill per model, re-embedded
only when the skill's label, aliases or description change (`text_hash`).
"""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Sequence
from dataclasses import dataclass

import psycopg

from app.core import embeddings, refdata
from app.core.db import connection
from app.core.logging import get_logger
from app.features.profile import cv_parser

log = get_logger("app.profile.skill_match")

# Calibrated on 18 skills-list entries from five synthetic CVs (2026-10-23): with Gemini, related
# skills score about 0.82-0.89 and unrelated ones 0.76-0.81 ("Kuala Lumpur" 0.775), so a
# suggestion also needs a clear lead over the runner-up.
MIN_SIMILARITY = 0.80
MIN_MARGIN = 0.015
MAX_TERMS = 30

_lock = threading.Lock()
_index: dict[str, list[float]] = {}
_index_model = ""
_index_hashes: dict[str, str] = {}


@dataclass(frozen=True)
class Suggestion:
    term: str
    skill_id: str
    label: str
    similarity: float
    runner_up: str = ""


def _skill_text(skill: cv_parser.TaxonomySkill, description: str) -> str:
    aliases = [a for a in skill.aliases if a.isascii() and a != skill.normalised_label][:10]
    text = skill.label
    if aliases:
        text += ". Also called: " + ", ".join(aliases)
    if description and description != "Core workplace skill":
        text += f". {description}"
    return text


def catalogue_texts() -> dict[str, str]:
    """skill_id -> the text embedded for it (canonical skills only)."""
    taxonomy = cv_parser._load_taxonomy()  # noqa: SLF001 - same canonical catalogue
    descriptions = {r["id"]: r.get("description", "") for r in refdata.rows("taxonomy", "skills")}
    return {sid: _skill_text(s, descriptions.get(sid, "")) for sid, s in taxonomy.items()}


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _vector_literal(v: Sequence[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in v) + "]"


def _load_db(model: str) -> dict[str, tuple[str, list[float]]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT item_id, text_hash, embedding::text AS v FROM catalogue_embeddings "
            "WHERE kind = 'skill' AND model = %s",
            (model,),
        ).fetchall()
    return {
        str(r["item_id"]): (
            str(r["text_hash"]),
            [float(x) for x in str(r["v"]).strip("[]").split(",")],
        )
        for r in rows
    }


def _save_db(model: str, rows: list[tuple[str, str, list[float]]]) -> None:
    with connection() as conn, conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO catalogue_embeddings (kind, item_id, model, text_hash, embedding) "
            "VALUES ('skill', %s, %s, %s, %s::vector) ON CONFLICT (kind, item_id, model) DO "
            "UPDATE SET text_hash = EXCLUDED.text_hash, embedding = EXCLUDED.embedding, "
            "updated_at = now()",
            [(sid, model, h, _vector_literal(v)) for sid, h, v in rows],
        )


def ensure_index() -> dict[str, list[float]]:
    """Catalogue vectors for the current model, embedding only new or changed skills."""
    global _index, _index_model, _index_hashes  # noqa: PLW0603
    model = embeddings.model_name()
    texts = catalogue_texts()
    hashes = {sid: _hash(text) for sid, text in texts.items()}
    with _lock:
        if _index_model == model and _index_hashes == hashes:
            return _index
        stored: dict[str, tuple[str, list[float]]] = {}
        use_db = refdata.use_postgres()
        if use_db:
            try:
                stored = _load_db(model)
            except psycopg.Error as exc:
                log.warning("catalogue embeddings unreadable, embedding in memory: %s", exc)
                use_db = False
        stale = [sid for sid, t in texts.items() if stored.get(sid, ("",))[0] != _hash(t)]
        fresh: list[tuple[str, str, list[float]]] = []
        if stale:
            vectors = embeddings.embed([texts[sid] for sid in stale], patient=True)
            fresh = [(sid, _hash(texts[sid]), v) for sid, v in zip(stale, vectors, strict=True)]
            if use_db:
                try:
                    _save_db(model, fresh)
                except psycopg.Error as exc:
                    log.warning("could not store catalogue embeddings: %s", exc)
            log.info("embedded %d catalogue skill(s) with %s", len(fresh), model)
        index = {sid: v for sid, (_, v) in stored.items() if sid in texts}
        index.update({sid: v for sid, _, v in fresh})
        _index, _index_model, _index_hashes = index, model, hashes
        return _index


def _nearest_db(vector: list[float], model: str, k: int = 3) -> list[tuple[str, float]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT item_id, 1 - (embedding <=> %s::vector) AS sim FROM catalogue_embeddings "
            "WHERE kind = 'skill' AND model = %s ORDER BY embedding <=> %s::vector LIMIT %s",
            (_vector_literal(vector), model, _vector_literal(vector), k),
        ).fetchall()
    return [(str(r["item_id"]), float(r["sim"])) for r in rows]


def ready_index() -> dict[str, list[float]]:
    """Read an existing catalogue index; requests never build or wait for one."""
    model = embeddings.model_name()
    texts = catalogue_texts()
    hashes = {sid: _hash(text) for sid, text in texts.items()}
    if not _lock.acquire(blocking=False):
        return {}
    try:
        if _index_model == model and _index_hashes == hashes and set(_index) == set(texts):
            return dict(_index)
        if not refdata.use_postgres():
            return {}
        try:
            stored = _load_db(model)
        except psycopg.Error:
            return {}
        index = {
            sid: vector
            for sid, (text_hash, vector) in stored.items()
            if sid in texts and text_hash == _hash(texts[sid])
        }
        return index if set(index) == set(texts) else {}
    finally:
        _lock.release()


def _nearest_memory(
    vector: list[float], index: dict[str, list[float]], k: int = 3
) -> list[tuple[str, float]]:
    scored = [(sid, embeddings.cosine(vector, v)) for sid, v in index.items()]
    return sorted(scored, key=lambda kv: (-kv[1], kv[0]))[:k]


def decide(
    term: str, ranked: list[tuple[str, float]], labels: dict[str, str], exclude: set[str]
) -> Suggestion | None:
    """The best match if it is similar enough and clearly ahead of the next one (pure).

    When the closest skill is one the CV already has, the term is most likely that skill in
    other words, so nothing is suggested (not the second-closest instead)."""
    if not ranked or ranked[0][0] in exclude:
        return None
    best, sim = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else ("", 0.0)
    if sim < MIN_SIMILARITY or sim - runner[1] < MIN_MARGIN:
        return None
    return Suggestion(term, best, labels.get(best, best), round(sim, 3), labels.get(runner[0], ""))


def suggest(terms: Sequence[str], exclude: set[str] | None = None) -> list[Suggestion]:
    """Catalogue suggestions for unmatched skills-list entries; [] when embeddings are off."""
    terms = [t for t in terms if t.strip()][:MAX_TERMS]
    if not terms or not embeddings.enabled():
        return []
    try:
        index = ready_index()
        if not index:
            return []
        vectors = embeddings.embed(terms)
    except embeddings.EmbeddingsUnavailable:
        return []
    labels = {sid: s.label for sid, s in cv_parser._load_taxonomy().items()}  # noqa: SLF001
    out: list[Suggestion] = []
    for term, vector in zip(terms, vectors, strict=True):
        ranked = _nearest_memory(vector, index, 3)
        found = decide(term, ranked, labels, exclude or set())
        if found:
            out.append(found)
    return out


if __name__ == "__main__":  # python -m app.features.profile.skill_match  (pre-builds the index)
    print(f"{len(ensure_index())} catalogue skills embedded with {embeddings.model_name()}")
