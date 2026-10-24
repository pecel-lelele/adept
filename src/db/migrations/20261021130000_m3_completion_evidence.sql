-- migrate:up
-- M3 (F5): evidence behind a completed course, and HR / career-advisor review of it
-- (see docs/decisions.md M3-020). Kinds, weakest first: self_reported, certificate_link,
-- org_confirmed; org_rejected means a reviewer did not accept the completion.

CREATE TABLE course_evidence (
    user_id          text NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    role_id          text NOT NULL,
    course_id        text NOT NULL REFERENCES courses (id) ON DELETE CASCADE,
    kind             text NOT NULL
        CHECK (kind IN ('self_reported', 'certificate_link', 'org_confirmed', 'org_rejected')),
    url              text,
    link_status      text NOT NULL DEFAULT 'not_submitted'
        CHECK (link_status IN ('not_submitted', 'provider_verified', 'unreachable',
                               'not_provider_page')),
    link_checked_at  timestamptz,
    submitted_at     timestamptz NOT NULL DEFAULT now(),
    reviewed_by      text REFERENCES users (id) ON DELETE SET NULL,
    reviewed_at      timestamptz,
    review_note      text NOT NULL DEFAULT '',
    PRIMARY KEY (user_id, role_id, course_id)
);

-- migrate:down

DROP TABLE IF EXISTS course_evidence;
