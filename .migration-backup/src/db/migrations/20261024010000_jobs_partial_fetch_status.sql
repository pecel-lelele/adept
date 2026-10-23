-- migrate:up
-- An interrupted board read can keep valid results without closing unseen openings.
ALTER TABLE job_fetch_log DROP CONSTRAINT job_fetch_log_status_check;
ALTER TABLE job_fetch_log ADD CONSTRAINT job_fetch_log_status_check
    CHECK (status IN ('ok', 'partial', 'skipped', 'blocked', 'error'));

-- migrate:down
-- Preserve the audit history when returning to the older set of status values.
UPDATE job_fetch_log SET status = 'error', detail = 'Partial read: ' || detail
    WHERE status = 'partial';
ALTER TABLE job_fetch_log DROP CONSTRAINT job_fetch_log_status_check;
ALTER TABLE job_fetch_log ADD CONSTRAINT job_fetch_log_status_check
    CHECK (status IN ('ok', 'skipped', 'blocked', 'error'));
