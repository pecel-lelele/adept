-- migrate:up
-- M3 (F5/F6/F8): live data sync, SDG evidence, per-role progress, shared rate limits, and an
-- upgrade path for databases seeded from the skeleton (see docs/decisions.md M3-014..).

-- 1. Upgrade databases seeded from the skeleton ------------------------------------------
-- The seed loader uses ON CONFLICT DO NOTHING, so stale reference rows would never be
-- replaced. Remove the skeleton's placeholder rows; `make seed` (or the M3 sync) reloads
-- the real ones. No user data is touched: these are reference tables.

DELETE FROM courses WHERE url LIKE 'https://example.org/%';
DELETE FROM role_sdg_map WHERE reason ILIKE '%mock%';
DELETE FROM skill_sdg_map WHERE reason ILIKE '%mock%';

-- 2. SDG mapping evidence ----------------------------------------------------------------
-- Every link must cite the source that justifies it (UN indicator metadata, ILO, UNESCO).

ALTER TABLE role_sdg_map
    ADD COLUMN evidence_source text NOT NULL DEFAULT '',
    ADD COLUMN evidence_url text NOT NULL DEFAULT '',
    ADD COLUMN evidence_note text NOT NULL DEFAULT '';

ALTER TABLE skill_sdg_map
    ADD COLUMN evidence_source text NOT NULL DEFAULT '',
    ADD COLUMN evidence_url text NOT NULL DEFAULT '',
    ADD COLUMN evidence_note text NOT NULL DEFAULT '';

-- Links loaded before evidence existed are replaced by the evidence-backed seed rows.
DELETE FROM role_sdg_map WHERE evidence_url = '';
DELETE FROM skill_sdg_map WHERE evidence_url = '';

-- Skeleton targets carried shortened labels and no retrieval date; drop those no longer
-- referenced so the official wording from the UN API is loaded instead.
DELETE FROM sdg_targets t
WHERE t.retrieved_at IS NULL
  AND NOT EXISTS (SELECT 1 FROM role_sdg_map m WHERE m.sdg_target_id = t.id)
  AND NOT EXISTS (SELECT 1 FROM skill_sdg_map m WHERE m.sdg_target_id = t.id);

-- 3. Live course catalogue sync --------------------------------------------------------------

ALTER TABLE courses
    ADD COLUMN provider_ref text NOT NULL DEFAULT '',
    ADD COLUMN last_synced_at timestamptz,
    ADD COLUMN retired_at timestamptz;

CREATE TABLE data_syncs (
    id           bigserial PRIMARY KEY,
    source       text NOT NULL,
    started_at   timestamptz NOT NULL DEFAULT now(),
    finished_at  timestamptz,
    status       text NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'ok', 'failed')),
    records      integer NOT NULL DEFAULT 0,
    retired      integer NOT NULL DEFAULT 0,
    detail       text NOT NULL DEFAULT ''
);

CREATE INDEX data_syncs_source_idx ON data_syncs (source, started_at DESC);

-- 4. Progress is tracked per target role ---------------------------------------------------

ALTER TABLE course_progress ADD COLUMN role_id text NOT NULL DEFAULT '';
ALTER TABLE course_progress DROP CONSTRAINT course_progress_pkey;
ALTER TABLE course_progress ADD PRIMARY KEY (user_id, role_id, course_id);

-- 5. Rate-limit counters shared by every API instance ---------------------------------------
-- UNLOGGED: fast, and losing counters on a crash only resets throttles.

CREATE UNLOGGED TABLE rate_limit_counters (
    client        text NOT NULL,
    bucket        text NOT NULL,
    window_start  bigint NOT NULL,
    hits          integer NOT NULL,
    PRIMARY KEY (client, bucket, window_start)
);

-- migrate:down

DROP TABLE IF EXISTS rate_limit_counters, data_syncs;
ALTER TABLE course_progress DROP CONSTRAINT course_progress_pkey;
DELETE FROM course_progress a USING course_progress b
    WHERE a.user_id = b.user_id AND a.course_id = b.course_id AND a.ctid < b.ctid;
ALTER TABLE course_progress ADD PRIMARY KEY (user_id, course_id);
ALTER TABLE course_progress DROP COLUMN IF EXISTS role_id;
ALTER TABLE courses
    DROP COLUMN IF EXISTS provider_ref,
    DROP COLUMN IF EXISTS last_synced_at,
    DROP COLUMN IF EXISTS retired_at;
ALTER TABLE skill_sdg_map
    DROP COLUMN IF EXISTS evidence_source,
    DROP COLUMN IF EXISTS evidence_url,
    DROP COLUMN IF EXISTS evidence_note;
ALTER TABLE role_sdg_map
    DROP COLUMN IF EXISTS evidence_source,
    DROP COLUMN IF EXISTS evidence_url,
    DROP COLUMN IF EXISTS evidence_note;
