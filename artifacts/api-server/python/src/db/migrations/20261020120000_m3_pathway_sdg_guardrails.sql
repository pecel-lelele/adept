-- migrate:up
-- M3 (F5 pathway, F6 SDG, F8 guardrails). Additive only; see docs/decisions.md M3 entries.

-- F6: all 17 goals (UN SDG API) and provenance on targets -----------------------

CREATE TABLE sdg_goals (
    id            smallint PRIMARY KEY CHECK (id BETWEEN 1 AND 17),
    title         text NOT NULL,
    short_title   text NOT NULL,
    source_url    text NOT NULL DEFAULT '',
    retrieved_at  date
);

ALTER TABLE sdg_targets
    ADD COLUMN retrieved_at date;

-- direct: the work itself advances the target; enabling: it builds capacity the target needs.
ALTER TABLE role_sdg_map
    ADD COLUMN strength text NOT NULL DEFAULT 'enabling'
        CHECK (strength IN ('direct', 'enabling'));

ALTER TABLE skill_sdg_map
    ADD COLUMN strength text NOT NULL DEFAULT 'enabling'
        CHECK (strength IN ('direct', 'enabling'));

-- Synthetic demo organisations → Malaysian state, for the region SDG view.
CREATE TABLE org_regions (
    org_id  text PRIMARY KEY REFERENCES organizations (id) ON DELETE CASCADE,
    state   text NOT NULL
);

-- F5: catalogue provenance, prerequisite graph, saved plans, progress, badges ----

ALTER TABLE courses
    ADD COLUMN level smallint NOT NULL DEFAULT 2 CHECK (level BETWEEN 1 AND 5),
    ADD COLUMN source_name text NOT NULL DEFAULT '',
    ADD COLUMN source_url text NOT NULL DEFAULT '',
    ADD COLUMN hrd_note text NOT NULL DEFAULT '',
    ADD COLUMN language text NOT NULL DEFAULT 'en',
    ADD COLUMN duration_note text NOT NULL DEFAULT '';

CREATE TABLE skill_prerequisites (
    skill_id         text NOT NULL REFERENCES skills (id) ON DELETE CASCADE,
    prerequisite_id  text NOT NULL REFERENCES skills (id) ON DELETE CASCADE,
    reason           text NOT NULL,
    PRIMARY KEY (skill_id, prerequisite_id),
    CHECK (skill_id <> prerequisite_id)
);

-- One saved (human-chosen) plan per learner; snapshot_version drives re-planning.
CREATE TABLE pathway_plans (
    user_id           text PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    role_id           text NOT NULL REFERENCES roles (id),
    scenario          text NOT NULL CHECK (scenario IN ('moderate', 'fast')),
    snapshot_version  text NOT NULL,
    steps             jsonb NOT NULL,
    saved_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE course_progress (
    user_id     text NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    course_id   text NOT NULL REFERENCES courses (id) ON DELETE CASCADE,
    status      text NOT NULL CHECK (status IN ('in_progress', 'completed')),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, course_id)
);

CREATE TABLE user_badges (
    user_id    text NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    badge_id   text NOT NULL,
    earned_at  timestamptz NOT NULL DEFAULT now(),
    evidence   text NOT NULL DEFAULT 'self_reported',
    PRIMARY KEY (user_id, badge_id)
);

-- F8: audit log of LLM calls (provider and model are disclosed on /about) ---------

CREATE TABLE llm_calls (
    id            bigserial PRIMARY KEY,
    called_at     timestamptz NOT NULL DEFAULT now(),
    provider      text NOT NULL,
    model         text NOT NULL DEFAULT '',
    task          text NOT NULL,
    n_candidates  integer NOT NULL DEFAULT 0,
    selected      text[] NOT NULL DEFAULT '{}',
    rejected      text[] NOT NULL DEFAULT '{}',
    outcome       text NOT NULL
        CHECK (outcome IN ('ok', 'rejected_unknown_ids', 'unavailable', 'breaker_open'))
);

-- migrate:down

DROP TABLE IF EXISTS llm_calls, user_badges, course_progress, pathway_plans,
    skill_prerequisites, org_regions, sdg_goals;
ALTER TABLE courses
    DROP COLUMN IF EXISTS level,
    DROP COLUMN IF EXISTS source_name,
    DROP COLUMN IF EXISTS source_url,
    DROP COLUMN IF EXISTS hrd_note,
    DROP COLUMN IF EXISTS language,
    DROP COLUMN IF EXISTS duration_note;
ALTER TABLE skill_sdg_map DROP COLUMN IF EXISTS strength;
ALTER TABLE role_sdg_map DROP COLUMN IF EXISTS strength;
ALTER TABLE sdg_targets DROP COLUMN IF EXISTS retrieved_at;
