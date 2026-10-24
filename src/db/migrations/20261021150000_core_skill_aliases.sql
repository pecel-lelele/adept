-- migrate:up
-- The F1 taxonomy seed includes pipe-separated aliases for CV extraction.
ALTER TABLE skills ADD COLUMN IF NOT EXISTS aliases text NOT NULL DEFAULT '';

-- migrate:down
ALTER TABLE skills DROP COLUMN IF EXISTS aliases;
