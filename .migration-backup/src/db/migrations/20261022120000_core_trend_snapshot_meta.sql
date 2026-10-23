-- migrate:up
-- Provenance per trend snapshot date: which sources produced it and how. Lets the API cite the
-- real source of each stored snapshot instead of a fixed label.

CREATE TABLE IF NOT EXISTS trend_snapshot_meta (
    snapshot_date    date PRIMARY KEY,
    sources          jsonb NOT NULL,
    provenance_note  text NOT NULL DEFAULT '',
    loaded_at        timestamptz NOT NULL DEFAULT now()
);

-- migrate:down

DROP TABLE IF EXISTS trend_snapshot_meta;
