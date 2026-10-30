-- migrate:up
ALTER TABLE users ADD COLUMN session_version bigint NOT NULL DEFAULT 0 CHECK (session_version >= 0);

-- migrate:down
ALTER TABLE users DROP COLUMN session_version;
