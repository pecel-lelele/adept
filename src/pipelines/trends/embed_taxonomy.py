"""src/pipelines/trends/embed_taxonomy.py

PART 4 – One-off embedding batch job (zero-shot, no training).

Reads:
  src/data/seed/canonical_skills.csv

Writes:
  PostgreSQL: skill_embeddings(skill_id, embedding vector(384))
  (migration: src/db/migrations/20261020160000_m1_trends_signal_tables.sql)

Model: sentence-transformers/all-MiniLM-L6-v2
  (384 dimensions; RunPod worker, or explicit local CPU development)
  * Weights are packaged once in the RunPod worker image.
  * No fine-tuning or gradient computation. The API never invokes the encoder.
  * License: Apache 2.0 (Hugging Face).

Run (one-off, after `make db-migrate`):
  PYTHONPATH=src/api:src uv run --no-project python src/pipelines/trends/embed_taxonomy.py

Design notes:
  * Embeddings are NOT re-computed per request; the API reads them from Postgres.
  * Re-run whenever canonical_skills.csv changes (it UPSERTS, so safe to re-run).
  * Local development uses sentence_transformers, installed separately:
      pip install sentence-transformers  (NOT in requirements.txt – pipeline-only dep)
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from pipelines.trends.encoder import get_encoder

REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_DIR = REPO_ROOT / "src" / "data" / "seed"
CANONICAL = SEED_DIR / "canonical_skills.csv"


def load_skills() -> list[tuple[str, str]]:
    """Return [(skill_id, skill_label), ...]."""
    with CANONICAL.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return [(row["skill_id"], row["skill_label"]) for row in reader]


def embed_and_store(skills: list[tuple[str, str]]) -> None:
    """Embed skill labels and upsert into the skill_embeddings table."""
    try:
        import psycopg  # type: ignore[import]
    except ImportError:
        print("ERROR: psycopg is not installed (should be in requirements.txt).", file=sys.stderr)
        sys.exit(1)

    # Load the API's database URL
    sys.path.insert(0, str(REPO_ROOT / "src" / "api"))
    from app.core.config import get_settings  # noqa: E402

    db_url = get_settings().database_url

    print("Loading configured MiniLM encoder ...")
    model = get_encoder()

    skill_ids = [s[0] for s in skills]
    labels = [s[1] for s in skills]

    print(f"Embedding {len(labels)} skill labels ...")
    vectors = model.encode(labels, batch_size=32, show_progress_bar=True)

    print(f"Upserting {len(skill_ids)} vectors into skill_embeddings ...")
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            for skill_id, vec in zip(skill_ids, vectors, strict=True):
                # pgvector accepts a Python list as the embedding literal.
                vec_list = vec
                cur.execute(
                    """
                    INSERT INTO skill_embeddings (skill_id, embedding)
                    VALUES (%s, %s::vector)
                    ON CONFLICT (skill_id) DO UPDATE SET embedding = EXCLUDED.embedding
                    """,
                    (skill_id, vec_list),
                )
        conn.commit()
    print(f"Done. {len(skill_ids)} embeddings stored in skill_embeddings.")


def main() -> None:
    if not CANONICAL.exists():
        print(f"ERROR: {CANONICAL} not found", file=sys.stderr)
        sys.exit(1)

    skills = load_skills()
    print(f"Loaded {len(skills)} skills from {CANONICAL.name}")
    embed_and_store(skills)


if __name__ == "__main__":
    main()
