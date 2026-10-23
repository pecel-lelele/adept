-- migrate:up
-- Fix weekly signal aggregation: key skill_signal_raw by (skill_id, source, metric, period, retrieved_at)
-- and store total_papers per run so multiple runs within a period aggregate both count and total_papers.

ALTER TABLE skill_signal_raw DROP CONSTRAINT IF EXISTS skill_signal_raw_skill_id_source_metric_period_key;

ALTER TABLE skill_signal_raw ADD COLUMN IF NOT EXISTS total_papers integer NOT NULL DEFAULT 0;

ALTER TABLE skill_signal_raw ADD CONSTRAINT skill_signal_raw_unique_fetch
    UNIQUE (skill_id, source, metric, period, retrieved_at);

-- migrate:down
ALTER TABLE skill_signal_raw DROP CONSTRAINT IF EXISTS skill_signal_raw_unique_fetch;
ALTER TABLE skill_signal_raw DROP COLUMN IF EXISTS total_papers;
ALTER TABLE skill_signal_raw ADD CONSTRAINT skill_signal_raw_skill_id_source_metric_period_key
    UNIQUE (skill_id, source, metric, period);
