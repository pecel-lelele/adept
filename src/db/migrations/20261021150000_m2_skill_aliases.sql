-- migrate:up
-- F1 CV parsing uses aliases from the skills taxonomy seed.
ALTER TABLE skills
    ADD COLUMN aliases text NOT NULL DEFAULT '';

-- migrate:down
ALTER TABLE skills
    DROP COLUMN aliases;
