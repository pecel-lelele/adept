"""src/pipelines/trends/arxiv_ingest.py

PART 5 – arXiv RSS ingestion + sentence-chunked semantic matching.

Sources:
  arXiv cs.AI RSS:  https://rss.arxiv.org/rss/cs.AI
  Rate limit:       ~1 request per 3 seconds (respected via sleep).

Reads:
  src/data/seed/canonical_skills.csv         (skill taxonomy)
  src/data/seed/arxiv_raw/<date>.json        (cached raw pulls, avoids re-fetch)
  skill_embeddings table (vectors pre-computed by embed_taxonomy.py)

Writes:
  src/data/seed/arxiv_raw/<date>.json        (raw cache)
  skill_signal_raw table                     (mention counts per skill per week)
  arxiv_fetch_log table                      (audit log of each pull)

Algorithm (sentence-chunked, NOT whole-abstract cosine):
  For each paper p, split abstract into sentences on '.'.
  Embed each sentence independently with all-MiniLM-L6-v2.
  A paper counts as a mention of skill s if:
      max(cosine_similarity(sentence_vec, skill_vec)) >= THRESHOLD (0.55)
  for ANY sentence in the abstract.
  This avoids dilution by irrelevant sentences in the average.

Run (batch job, NOT called by the API):
  PYTHONPATH=src/api:src uv run --no-project python src/pipelines/trends/arxiv_ingest.py

Safety:
  * Never calls arXiv at request time; the API only reads pre-computed rows
    from skill_signal_raw.
  * Raw JSON cache keyed by fetch date lets us re-run matching without
    re-fetching the feed.
  * Rate limit is enforced before every request.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

from pipelines.trends.encoder import Encoder, get_encoder

REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_DIR = REPO_ROOT / "src" / "data" / "seed"
CANONICAL = SEED_DIR / "canonical_skills.csv"
ARXIV_CACHE_DIR = SEED_DIR / "arxiv_raw"

ARXIV_RSS_URL = "https://rss.arxiv.org/rss/cs.AI"
RATE_LIMIT_S = 3.0  # seconds between arXiv requests
SIMILARITY_THRESHOLD = 0.55  # sentence-level cosine similarity threshold
WEEK_FMT = "%G-W%V"  # ISO week format for period bucket


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _today_str() -> str:
    return date.today().isoformat()


def _iso_week(dt: date) -> str:
    return dt.strftime(WEEK_FMT)


def _strip_html(text: str) -> str:
    """Remove HTML tags and normalise whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _split_sentences(text: str) -> list[str]:
    """Split text on '.' (per spec), filter empty/very-short strings."""
    parts = text.split(".")
    return [s.strip() for s in parts if len(s.strip()) > 10]


# ---------------------------------------------------------------------------
# Load skills
# ---------------------------------------------------------------------------


def load_skills() -> list[tuple[str, str]]:
    """Return [(skill_id, skill_label), ...]."""
    with CANONICAL.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return [(row["skill_id"], row["skill_label"]) for row in reader]


# ---------------------------------------------------------------------------
# ArXiv fetch & cache
# ---------------------------------------------------------------------------


def fetch_or_load_rss(fetch_date: str) -> list[dict[str, str]]:
    """
    Return a list of {title, abstract, arxiv_id} dicts.
    Uses the cached file if it exists; otherwise fetches and caches.
    """
    ARXIV_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = ARXIV_CACHE_DIR / f"{fetch_date}.json"

    if cache_file.exists():
        print(f"[arxiv] Loading cached feed from {cache_file}")
        with cache_file.open(encoding="utf-8") as fh:
            return json.load(fh)

    print(f"[arxiv] Fetching {ARXIV_RSS_URL} ...")
    time.sleep(RATE_LIMIT_S)  # respect rate limit before every request
    req = urllib.request.Request(
        ARXIV_RSS_URL,
        headers={"User-Agent": "adept-trends-pipeline/1.0 (adept-hackathon; no-commercial)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw_xml = resp.read().decode("utf-8", errors="replace")

    papers = _parse_rss(raw_xml)
    with cache_file.open("w", encoding="utf-8") as fh:
        json.dump(papers, fh, ensure_ascii=False, indent=2)
    print(f"[arxiv] Cached {len(papers)} papers -> {cache_file}")
    return papers


def _parse_rss(xml_text: str) -> list[dict[str, str]]:
    """Parse arXiv RSS XML and return list of {arxiv_id, title, abstract}."""
    papers: list[dict[str, str]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        print(f"[arxiv] XML parse error: {exc}", file=sys.stderr)
        return papers

    channel = root.find("channel")
    if channel is None:
        return papers

    for item in root.iter("item"):
        title_el = item.find("title")
        desc_el = item.find("description")
        link_el = item.find("link")

        title = _strip_html(title_el.text or "") if title_el is not None else ""
        abstract = _strip_html(desc_el.text or "") if desc_el is not None else ""
        arxiv_id = (link_el.text or "").strip() if link_el is not None else ""

        if title or abstract:
            papers.append({"arxiv_id": arxiv_id, "title": title, "abstract": abstract})
    return papers


# ---------------------------------------------------------------------------
# Embedding + matching
# ---------------------------------------------------------------------------


def load_skill_vectors(
    skill_ids: list[str],
    db_url: str,
) -> dict[str, list[float]]:
    """
    Load skill embeddings from Postgres.
    Returns {skill_id: vector_list}.
    Falls back to encoding with the model if no DB rows found.
    """
    import psycopg  # type: ignore[import]

    vectors: dict[str, list[float]] = {}
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT skill_id, embedding::text FROM skill_embeddings "
                    "WHERE skill_id = ANY(%s)",
                    (skill_ids,),
                )
                for row in cur.fetchall():
                    sid = row[0]
                    # pgvector returns a string like "[0.1, 0.2, ...]"
                    vec_str = row[1].strip("[]")
                    vectors[sid] = [float(x) for x in vec_str.split(",")]
    except Exception as exc:
        print(f"[embed] DB unavailable ({exc}), will encode from model.", file=sys.stderr)
    return vectors


def encode_skills_from_model(
    skills: list[tuple[str, str]],
) -> dict[str, list[float]]:
    """Encode skill labels with the model (fallback when DB not ready)."""
    model = get_encoder()
    ids = [s[0] for s in skills]
    labels = [s[1] for s in skills]
    vecs = model.encode(labels, batch_size=32, show_progress_bar=True)
    return dict(zip(ids, vecs, strict=True))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def count_mentions(
    papers: list[dict[str, str]],
    skill_ids: list[str],
    skill_vectors: dict[str, list[float]],
    model: Encoder | None,
) -> dict[str, int]:
    """
    Count papers that mention each skill via sentence-level cosine similarity.
    Returns {skill_id: count}.
    """
    counts: dict[str, int] = {sid: 0 for sid in skill_ids}

    for paper in papers:
        text = f"{paper['title']}. {paper['abstract']}"
        sentences = _split_sentences(text)
        if not sentences:
            continue

        # Embed sentences
        if model is not None:
            sent_vecs = model.encode(sentences, batch_size=64, show_progress_bar=False)
        else:
            # Cannot embed; skip
            continue

        # Check each skill
        for sid in skill_ids:
            if sid not in skill_vectors:
                continue
            sv = skill_vectors[sid]
            max_sim = max(cosine_similarity(sv, sent_vec) for sent_vec in sent_vecs)
            if max_sim >= SIMILARITY_THRESHOLD:
                counts[sid] += 1

    return counts


# ---------------------------------------------------------------------------
# Write to DB
# ---------------------------------------------------------------------------


def write_signal_rows(
    counts: dict[str, int],
    total_papers: int,
    fetch_date: date,
    db_url: str,
) -> None:
    """Upsert skill_signal_raw rows and log the fetch."""
    import psycopg  # type: ignore[import]

    period = _iso_week(fetch_date)
    retrieved_at = fetch_date

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            for skill_id, count in counts.items():
                cur.execute(
                    """
                    INSERT INTO skill_signal_raw
                        (skill_id, source, metric, value, total_papers, period, retrieved_at)
                    VALUES (%s, 'arxiv', 'mention_count', %s, %s, %s, %s)
                    ON CONFLICT (skill_id, source, metric, period, retrieved_at)
                    DO UPDATE SET value = EXCLUDED.value,
                                  total_papers = EXCLUDED.total_papers
                    """,
                    (skill_id, float(count), total_papers, period, retrieved_at),
                )
            # Log the fetch
            cur.execute(
                """
                INSERT INTO arxiv_fetch_log (fetch_date, paper_count, source_url, retrieved_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (fetch_date) DO UPDATE
                    SET paper_count = EXCLUDED.paper_count,
                        retrieved_at = now()
                """,
                (fetch_date, total_papers, ARXIV_RSS_URL),
            )
        conn.commit()
    print(f"[db] Wrote {len(counts)} signal rows for period {period}.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    sys.path.insert(0, str(REPO_ROOT / "src" / "api"))
    from app.core.config import get_settings  # noqa: E402

    db_url = get_settings().database_url
    fetch_date_str = _today_str()
    fetch_date = date.fromisoformat(fetch_date_str)

    skills = load_skills()
    skill_ids = [s[0] for s in skills]
    print(f"Loaded {len(skills)} skills.")

    # Fetch or load cached papers
    papers = fetch_or_load_rss(fetch_date_str)
    print(f"Total papers: {len(papers)}")
    if not papers:
        print("No papers found; exiting.")
        return

    # Load embeddings from DB (preferred) or encode from model
    skill_vectors = load_skill_vectors(skill_ids, db_url)
    missing_ids = [sid for sid in skill_ids if sid not in skill_vectors]

    model = get_encoder()

    if missing_ids:
        print(f"[embed] Encoding {len(missing_ids)} missing skills from model ...")
        missing_skills = [(s[0], s[1]) for s in skills if s[0] in missing_ids]
        missing_vecs = encode_skills_from_model(missing_skills)
        skill_vectors.update(missing_vecs)

    # Count mentions via sentence-level cosine similarity
    print("Counting mentions (sentence-level cosine similarity) ...")
    counts = count_mentions(papers, skill_ids, skill_vectors, model)

    mentioned = sum(1 for c in counts.values() if c > 0)
    print(f"Skills with at least one mention: {mentioned}/{len(skill_ids)}")

    # Write to DB
    write_signal_rows(counts, len(papers), fetch_date, db_url)
    print("Done.")


if __name__ == "__main__":
    main()
