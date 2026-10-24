-- migrate:up
-- Core (M4): real sign-up / login for the live demo. Passwords are stored as scrypt hashes
-- (never plain text); organisations get a join code members enter to join.

ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash text;

ALTER TABLE organizations ADD COLUMN IF NOT EXISTS join_code text;
UPDATE organizations SET join_code = upper(substr(md5(id || clock_timestamp()::text), 1, 8))
WHERE join_code IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS organizations_join_code_idx ON organizations (join_code);

CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_idx ON users (lower(email));

-- migrate:down

DROP INDEX IF EXISTS users_email_lower_idx;
DROP INDEX IF EXISTS organizations_join_code_idx;
ALTER TABLE organizations DROP COLUMN IF EXISTS join_code;
ALTER TABLE users DROP COLUMN IF EXISTS password_hash;
