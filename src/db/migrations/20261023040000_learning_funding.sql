-- migrate:up
-- One ledger per organisation, including every budget year. Row locks serialize budget reservations and claims.
CREATE TABLE learning_funding (
    org_id text PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    state jsonb NOT NULL DEFAULT '{"budgets":{},"claims":[],"budget_events":[]}'::jsonb
);
REVOKE ALL ON learning_funding FROM PUBLIC;
ALTER TABLE learning_funding ENABLE ROW LEVEL SECURITY;

-- migrate:down
DROP TABLE learning_funding;
