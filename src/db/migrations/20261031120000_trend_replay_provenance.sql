-- migrate:up
-- Replay provenance fix: storage origin and slot dates are not observation evidence.
-- NULL classification means unknown legacy provenance, never verified live ingestion.
ALTER TABLE skill_signal_raw
    ADD COLUMN is_replay boolean,
    ADD COLUMN observation_window_start date,
    ADD COLUMN observation_window_end date,
    ADD COLUMN retrieved_at_basis text NOT NULL DEFAULT 'unknown',
    ADD COLUMN retrieval_evidence text;
ALTER TABLE skill_signal_raw DROP CONSTRAINT skill_signal_raw_unique_fetch;
-- Portable (PostgreSQL < 15) equivalent of UNIQUE NULLS NOT DISTINCT on is_replay:
-- classified rows are unique per origin (the ON CONFLICT arbiter for writers, which
-- always set is_replay), and unclassified legacy rows keep the old per-fetch key.
ALTER TABLE skill_signal_raw ADD CONSTRAINT skill_signal_raw_unique_fetch
    UNIQUE (skill_id, source, metric, period, retrieved_at, is_replay);
CREATE UNIQUE INDEX skill_signal_raw_unique_legacy_fetch
    ON skill_signal_raw (skill_id, source, metric, period, retrieved_at)
    WHERE is_replay IS NULL;

ALTER TABLE trend_snapshots
    ADD COLUMN is_replay boolean,
    ADD COLUMN observation_window_start date,
    ADD COLUMN observation_window_end date,
    ADD COLUMN retrieved_at date,
    ADD COLUMN retrieved_at_basis text NOT NULL DEFAULT 'unknown',
    ADD COLUMN retrieval_evidence text;

ALTER TABLE trend_snapshot_meta
    ADD COLUMN is_replay boolean,
    ADD COLUMN observation_window_start date,
    ADD COLUMN observation_window_end date,
    ADD COLUMN retrieved_at date,
    ADD COLUMN retrieved_at_basis text NOT NULL DEFAULT 'unknown',
    ADD COLUMN retrieval_evidence text;

-- Repair only the identifiable committed historical exports. 2026-10-20 is the UTC
-- commit date of the last data change to their source fixtures,
-- 8005c5f4974df5953b9209475e88abcf9a32e7f9 (later commits only moved the files or added
-- metadata). The static BLS baseline is dated by its own last content change,
-- 750fa30225a8012e2dec52ccd6a7932d896c49a4 (2026-10-20). These are disclosed
-- artifact-date fallbacks, NOT evidence of a fetch on that day.
UPDATE trend_snapshot_meta
SET is_replay = true,
    observation_window_start = CASE snapshot_date
        WHEN DATE '2026-10-13' THEN DATE '2024-10-06' ELSE DATE '2024-10-13' END,
    observation_window_end = CASE snapshot_date
        WHEN DATE '2026-10-13' THEN DATE '2024-10-12' ELSE DATE '2024-10-19' END,
    retrieved_at = DATE '2026-10-20',
    retrieved_at_basis = 'git_commit_date',
    retrieval_evidence = 'git:8005c5f4974df5953b9209475e88abcf9a32e7f9 (source fixture data commit date; fetch time unverified)',
    sources = (SELECT jsonb_agg(s || jsonb_build_object(
        'retrieved_at', '2026-10-20', 'retrieved_at_basis', 'git_commit_date',
        'retrieval_evidence', CASE WHEN s->>'name' LIKE 'BLS%'
            THEN 'git:750fa30225a8012e2dec52ccd6a7932d896c49a4:src/data/seed/labor_decay.csv (UTC commit date of the last content change; fetch time unverified)'
            ELSE 'git:8005c5f4974df5953b9209475e88abcf9a32e7f9 (source fixture data commit date; fetch time unverified)' END))
        FROM jsonb_array_elements(sources) AS s)
WHERE snapshot_date IN (DATE '2026-10-13', DATE '2026-10-20')
  AND provenance_note LIKE '%2024-10-%'
  AND provenance_note LIKE '%calibrated%';

UPDATE trend_snapshots s
SET is_replay = m.is_replay,
    observation_window_start = m.observation_window_start,
    observation_window_end = m.observation_window_end,
    retrieved_at = m.retrieved_at, retrieved_at_basis = m.retrieved_at_basis,
    retrieval_evidence = m.retrieval_evidence
FROM trend_snapshot_meta m
WHERE s.snapshot_date = m.snapshot_date AND m.is_replay IS TRUE;

-- Old raw rows have no trustworthy origin discriminator. Leave them unknown and
-- exclude them from live refreshes. Relabel only rows tied to a documented replay.
UPDATE skill_signal_raw r
SET is_replay = true,
    observation_window_start = m.observation_window_start,
    observation_window_end = m.observation_window_end,
    retrieved_at = m.retrieved_at, retrieved_at_basis = m.retrieved_at_basis,
    retrieval_evidence = m.retrieval_evidence
FROM trend_snapshot_meta m
WHERE m.is_replay IS TRUE AND r.source = 'arxiv'
  AND r.retrieved_at = m.snapshot_date
  AND r.period = to_char(m.snapshot_date, 'IYYY-"W"IW');

ALTER TABLE skill_signal_raw ADD CONSTRAINT raw_signal_provenance_check CHECK (
    is_replay IS NULL OR (observation_window_start IS NOT NULL
        AND observation_window_end IS NOT NULL AND observation_window_end >= observation_window_start
        AND retrieved_at_basis IN ('pipeline_fetch', 'fetch_log', 'git_commit_date')
        AND (is_replay IS TRUE OR retrieved_at_basis IN ('pipeline_fetch', 'fetch_log'))
        AND retrieval_evidence IS NOT NULL AND length(retrieval_evidence) > 0));
ALTER TABLE trend_snapshots ADD CONSTRAINT snapshot_provenance_check CHECK (
    is_replay IS NULL OR (observation_window_start IS NOT NULL
        AND observation_window_end IS NOT NULL AND observation_window_end >= observation_window_start AND retrieved_at IS NOT NULL
        AND retrieved_at_basis IN ('pipeline_fetch', 'fetch_log', 'git_commit_date')
        AND (is_replay IS TRUE OR retrieved_at_basis IN ('pipeline_fetch', 'fetch_log'))
        AND retrieval_evidence IS NOT NULL AND length(retrieval_evidence) > 0));
ALTER TABLE trend_snapshot_meta ADD CONSTRAINT snapshot_meta_provenance_check CHECK (
    is_replay IS NULL OR (observation_window_start IS NOT NULL
        AND observation_window_end IS NOT NULL AND observation_window_end >= observation_window_start AND retrieved_at IS NOT NULL
        AND retrieved_at_basis IN ('pipeline_fetch', 'fetch_log', 'git_commit_date')
        AND (is_replay IS TRUE OR retrieved_at_basis IN ('pipeline_fetch', 'fetch_log'))
        AND retrieval_evidence IS NOT NULL AND length(retrieval_evidence) > 0));

-- migrate:down
-- This rollback removes provenance, not trend observations or scores.
-- Restoring the old uniqueness rule deliberately fails if origins would collide;
-- never delete observations to make a rollback fit an older schema.
DROP INDEX skill_signal_raw_unique_legacy_fetch;
ALTER TABLE skill_signal_raw DROP CONSTRAINT skill_signal_raw_unique_fetch;
ALTER TABLE skill_signal_raw ADD CONSTRAINT skill_signal_raw_unique_fetch
    UNIQUE (skill_id, source, metric, period, retrieved_at);
ALTER TABLE skill_signal_raw DROP CONSTRAINT raw_signal_provenance_check,
    DROP COLUMN is_replay, DROP COLUMN observation_window_start,
    DROP COLUMN observation_window_end, DROP COLUMN retrieved_at_basis,
    DROP COLUMN retrieval_evidence;
ALTER TABLE trend_snapshots DROP CONSTRAINT snapshot_provenance_check,
    DROP COLUMN is_replay, DROP COLUMN observation_window_start,
    DROP COLUMN observation_window_end, DROP COLUMN retrieved_at,
    DROP COLUMN retrieved_at_basis, DROP COLUMN retrieval_evidence;
ALTER TABLE trend_snapshot_meta DROP CONSTRAINT snapshot_meta_provenance_check,
    DROP COLUMN is_replay, DROP COLUMN observation_window_start,
    DROP COLUMN observation_window_end, DROP COLUMN retrieved_at,
    DROP COLUMN retrieved_at_basis, DROP COLUMN retrieval_evidence;
