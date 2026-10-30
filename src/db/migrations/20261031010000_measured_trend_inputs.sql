-- migrate:up
-- Exact dated inputs used by the scorer, without paper authors or abstract text.
CREATE TABLE measured_trend_inputs (
    measured_date date PRIMARY KEY,
    retrieved_at date NOT NULL CHECK (retrieved_at >= measured_date),
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object')
);
REVOKE ALL ON measured_trend_inputs FROM PUBLIC;

-- migrate:down
-- Removes reproducibility inputs only; published snapshots and their provenance stay intact.
DROP TABLE measured_trend_inputs;
