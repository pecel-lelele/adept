-- migrate:up
-- M3 (F5/F8): a reachable certificate link is "submitted", not verified. It proves neither
-- the learner's identity nor the course, so only a reviewer's confirmation earns credit
-- (issue #83, see docs/decisions.md). Allow the new status alongside the legacy ones.

ALTER TABLE course_evidence DROP CONSTRAINT IF EXISTS course_evidence_link_status_check;
ALTER TABLE course_evidence ADD CONSTRAINT course_evidence_link_status_check
    CHECK (link_status IN ('not_submitted', 'submitted', 'provider_verified', 'unreachable',
                           'not_provider_page'));

-- migrate:down

-- Before this change a reachable provider link was stored as provider_verified.
UPDATE course_evidence SET link_status = 'provider_verified' WHERE link_status = 'submitted';
ALTER TABLE course_evidence DROP CONSTRAINT IF EXISTS course_evidence_link_status_check;
ALTER TABLE course_evidence ADD CONSTRAINT course_evidence_link_status_check
    CHECK (link_status IN ('not_submitted', 'provider_verified', 'unreachable',
                           'not_provider_page'));
