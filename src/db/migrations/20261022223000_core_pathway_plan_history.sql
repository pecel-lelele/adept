-- migrate:up
-- A replacement plan must not remove the context for completed learning and badges.
CREATE TABLE pathway_plan_history (
    user_id text NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    plan_key text NOT NULL,
    role_id text NOT NULL REFERENCES roles (id),
    scenario text NOT NULL CHECK (scenario IN ('moderate', 'fast')),
    snapshot_version text NOT NULL,
    steps jsonb NOT NULL,
    saved_at timestamptz NOT NULL,
    PRIMARY KEY (user_id, plan_key)
);

-- Only the surviving saved plan is available when upgrading. Older replaced plans cannot
-- be reconstructed; their completed courses remain in course_progress.course_snapshot.
INSERT INTO pathway_plan_history
    (user_id, plan_key, role_id, scenario, snapshot_version, steps, saved_at)
SELECT user_id, 'legacy:' || md5(steps::text), role_id, scenario, snapshot_version, steps, saved_at
FROM pathway_plans;

-- migrate:down
DROP TABLE pathway_plan_history;
