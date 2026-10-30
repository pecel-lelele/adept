-- migrate:up
CREATE TABLE malaysia_labour_context (
    observed_month date PRIMARY KEY,
    payload jsonb NOT NULL
);
REVOKE ALL ON malaysia_labour_context FROM PUBLIC;

-- migrate:down
-- Removes only the public national-context cache; no personal/organisation learning data.
DROP TABLE malaysia_labour_context;
