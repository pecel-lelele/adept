-- migrate:up
-- Enforce new writes without deleting historical learning records. Existing orphan counts
-- must be audited before VALIDATE CONSTRAINT; NOT VALID still checks every new/changed key.
CREATE INDEX memberships_org_id_idx ON memberships (org_id);

ALTER TABLE course_progress
    ADD COLUMN workspace_org_id text GENERATED ALWAYS AS
        (CASE WHEN scope = 'personal' THEN NULL ELSE substring(scope FROM 5) END) STORED,
    ADD CONSTRAINT course_progress_workspace_fk FOREIGN KEY (workspace_org_id)
        REFERENCES organizations(id) ON DELETE CASCADE NOT VALID,
    ADD CONSTRAINT course_progress_role_fk FOREIGN KEY (role_id)
        REFERENCES roles(id) NOT VALID;
ALTER TABLE course_evidence
    ADD COLUMN workspace_org_id text GENERATED ALWAYS AS
        (CASE WHEN scope = 'personal' THEN NULL ELSE substring(scope FROM 5) END) STORED,
    ADD CONSTRAINT course_evidence_workspace_fk FOREIGN KEY (workspace_org_id)
        REFERENCES organizations(id) ON DELETE CASCADE NOT VALID,
    ADD CONSTRAINT course_evidence_role_fk FOREIGN KEY (role_id)
        REFERENCES roles(id) NOT VALID;

-- The app sets exactly one organisation for a ledger operation, transaction-locally.
-- FORCE covers non-superuser table owners too; production must not use BYPASSRLS/superuser.
CREATE POLICY funding_workspace ON learning_funding
    USING (org_id = current_setting('app.funding_org', true))
    WITH CHECK (org_id = current_setting('app.funding_org', true));
ALTER TABLE learning_funding FORCE ROW LEVEL SECURITY;

-- migrate:down
-- No application records are deleted by this rollback. Removing constraints weakens checks.
ALTER TABLE learning_funding NO FORCE ROW LEVEL SECURITY;
DROP POLICY funding_workspace ON learning_funding;
ALTER TABLE course_evidence
    DROP CONSTRAINT course_evidence_role_fk,
    DROP CONSTRAINT course_evidence_workspace_fk,
    DROP COLUMN workspace_org_id;
ALTER TABLE course_progress
    DROP CONSTRAINT course_progress_role_fk,
    DROP CONSTRAINT course_progress_workspace_fk,
    DROP COLUMN workspace_org_id;
DROP INDEX memberships_org_id_idx;
