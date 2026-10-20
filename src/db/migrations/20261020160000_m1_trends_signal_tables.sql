-- migrate:up
-- F2 M1: skill signal tables for arXiv trend ingestion and scoring.
-- Never edit this file after it is merged; add a new migration instead.

-- Skill embeddings (all-MiniLM-L6-v2, 384 dims).
-- Populated by src/pipelines/trends/embed_taxonomy.py (one-off batch job).
CREATE TABLE IF NOT EXISTS skill_embeddings (
    skill_id   text PRIMARY KEY,
    embedding  vector(384) NOT NULL
);

-- Raw signal aggregates from arXiv and any other sources added later.
CREATE TABLE IF NOT EXISTS skill_signal_raw (
    id           bigserial PRIMARY KEY,
    skill_id     text NOT NULL,
    source       text NOT NULL CHECK (source IN ('arxiv', 'bls', 'mock')),
    metric       text NOT NULL,          -- e.g. 'mention_count'
    value        real NOT NULL,
    period       text NOT NULL,          -- ISO week bucket, e.g. '2026-W42'
    retrieved_at date NOT NULL,
    UNIQUE (skill_id, source, metric, period)
);

CREATE INDEX IF NOT EXISTS skill_signal_raw_skill_idx
    ON skill_signal_raw (skill_id, source, period);

-- Scored snapshots computed by src/pipelines/trends/score.py.
CREATE TABLE IF NOT EXISTS trend_snapshots (
    id                       bigserial PRIMARY KEY,
    skill_id                 text NOT NULL,
    snapshot_date            date NOT NULL,
    research_velocity        real NOT NULL,
    labor_decay              real NOT NULL,
    labor_decay_source_note  text NOT NULL,
    automation_exposure      real NOT NULL CHECK (automation_exposure BETWEEN 0 AND 1),
    velocity_moderate        real NOT NULL,
    velocity_fast            real NOT NULL,
    direction_moderate       text NOT NULL CHECK (direction_moderate IN ('rising', 'stable', 'declining')),
    direction_fast           text NOT NULL CHECK (direction_fast IN ('rising', 'stable', 'declining')),
    UNIQUE (skill_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS trend_snapshots_date_idx ON trend_snapshots (snapshot_date);

-- ArXiv cache index (raw responses are stored as JSON files in src/data/seed/arxiv_raw/).
CREATE TABLE IF NOT EXISTS arxiv_fetch_log (
    id           bigserial PRIMARY KEY,
    fetch_date   date NOT NULL UNIQUE,
    paper_count  integer NOT NULL DEFAULT 0,
    source_url   text NOT NULL,
    retrieved_at timestamptz NOT NULL DEFAULT now()
);

-- migrate:down
DROP TABLE IF EXISTS arxiv_fetch_log, trend_snapshots, skill_signal_raw, skill_embeddings;
