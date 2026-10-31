-- migrate:up
-- M1-018: accumulated, per-paper trend evidence. Each arXiv paper is matched to skills once;
-- any rolling window is then a count over stored rows (no repeated model calls).
CREATE TABLE trend_fetched_days (
    day date PRIMARY KEY,
    papers integer NOT NULL CHECK (papers >= 0),
    fetched_on date NOT NULL
);

CREATE TABLE trend_paper_mentions (
    arxiv_id text PRIMARY KEY,
    published_on date NOT NULL REFERENCES trend_fetched_days(day) ON DELETE CASCADE,
    method text NOT NULL CHECK (method IN ('M1-014', 'M1-017')),
    model text NOT NULL,
    skills text[] NOT NULL DEFAULT '{}'
);

CREATE INDEX trend_paper_mentions_day_idx ON trend_paper_mentions (published_on);

-- One Gemini threshold per model, calibrated once against stored MiniLM evidence.
CREATE TABLE trend_fallback_calibration (
    model text PRIMARY KEY,
    threshold double precision NOT NULL,
    reference_rate double precision NOT NULL CHECK (reference_rate >= 0),
    calibrated_on date NOT NULL
);

-- migrate:down
DROP TABLE trend_fallback_calibration;
DROP TABLE trend_paper_mentions;
DROP TABLE trend_fetched_days;
