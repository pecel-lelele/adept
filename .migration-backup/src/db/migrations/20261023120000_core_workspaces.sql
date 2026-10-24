-- migrate:up
-- Workspaces (Core M4, decisions M4-033). One account works in a personal workspace and in
-- each organisation it belongs to. Learning progress and completion evidence belong to the
-- workspace they were recorded in: 'personal' or 'org:<organisation id>'. HR sees only its
-- own organisation's scope, plus skill levels a member explicitly shares.

ALTER TABLE memberships
    ADD COLUMN share_skills boolean NOT NULL DEFAULT false,
    ADD COLUMN skills_shared_at timestamptz;

ALTER TABLE course_progress
    ADD COLUMN scope text NOT NULL DEFAULT 'personal'
        CHECK (scope = 'personal' OR scope LIKE 'org:%');
ALTER TABLE course_evidence
    ADD COLUMN scope text NOT NULL DEFAULT 'personal'
        CHECK (scope = 'personal' OR scope LIKE 'org:%'),
    -- Provenance of evidence a member copied from their personal workspace into a programme.
    ADD COLUMN shared_from text CHECK (shared_from IN ('personal'));

-- Existing work learning: completions an organisation's manager reviewed, and completions
-- behind that organisation's funding claims, move to the organisation's scope.
UPDATE course_progress p SET scope = 'org:' || m.org_id
FROM course_evidence e
JOIN memberships m ON m.user_id = e.reviewed_by AND m.role IN ('manager', 'advisor')
WHERE e.user_id = p.user_id AND e.role_id = p.role_id AND e.course_id = p.course_id
  AND EXISTS (SELECT 1 FROM memberships l WHERE l.user_id = e.user_id AND l.org_id = m.org_id);
UPDATE course_progress p SET scope = 'org:' || f.org_id
FROM learning_funding f
CROSS JOIN LATERAL jsonb_array_elements(f.state->'claims') c
WHERE p.scope = 'personal' AND c->>'user_id' = p.user_id AND c->>'role_id' = p.role_id
  AND c->'course'->>'id' = p.course_id;
UPDATE course_evidence e SET scope = p.scope
FROM course_progress p
WHERE p.user_id = e.user_id AND p.role_id = e.role_id AND p.course_id = e.course_id
  AND p.scope <> 'personal';

ALTER TABLE course_progress DROP CONSTRAINT course_progress_pkey;
ALTER TABLE course_progress ADD PRIMARY KEY (user_id, scope, role_id, course_id);
ALTER TABLE course_evidence DROP CONSTRAINT course_evidence_pkey;
ALTER TABLE course_evidence ADD PRIMARY KEY (user_id, scope, role_id, course_id);

-- migrate:down
DELETE FROM course_evidence a USING course_evidence b
    WHERE (a.user_id, a.role_id, a.course_id) = (b.user_id, b.role_id, b.course_id)
      AND a.scope <> 'personal' AND b.scope = 'personal';
DELETE FROM course_progress a USING course_progress b
    WHERE (a.user_id, a.role_id, a.course_id) = (b.user_id, b.role_id, b.course_id)
      AND a.scope <> 'personal' AND b.scope = 'personal';
ALTER TABLE course_evidence DROP CONSTRAINT course_evidence_pkey;
ALTER TABLE course_evidence ADD PRIMARY KEY (user_id, role_id, course_id);
ALTER TABLE course_evidence DROP COLUMN shared_from, DROP COLUMN scope;
ALTER TABLE course_progress DROP CONSTRAINT course_progress_pkey;
ALTER TABLE course_progress ADD PRIMARY KEY (user_id, role_id, course_id);
ALTER TABLE course_progress DROP COLUMN scope;
ALTER TABLE memberships DROP COLUMN skills_shared_at, DROP COLUMN share_skills;
