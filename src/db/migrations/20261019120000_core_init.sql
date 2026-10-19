-- migrate:up
-- Initial schema. Never edit this file after it is merged: add a new migration instead.
-- Format is dbmate-compatible (up and down marker lines).

CREATE EXTENSION IF NOT EXISTS vector;

-- Accounts --------------------------------------------------------------------

CREATE TABLE users (
    id            text PRIMARY KEY,
    display_name  text NOT NULL,
    email         text UNIQUE,
    kind          text NOT NULL DEFAULT 'learner' CHECK (kind IN ('learner', 'org_admin', 'admin')),
    is_synthetic  boolean NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE organizations (
    id          text PRIMARY KEY,
    type        text NOT NULL CHECK (type IN ('company', 'institution')),
    name        text NOT NULL,
    industry    text NOT NULL DEFAULT '',
    size        integer NOT NULL DEFAULT 0 CHECK (size >= 0),
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE memberships (
    user_id        text NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    org_id         text NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    role           text NOT NULL DEFAULT 'member' CHECK (role IN ('member', 'manager', 'advisor')),
    intake_status  text NOT NULL DEFAULT 'invited'
                   CHECK (intake_status IN ('invited', 'in_progress', 'complete')),
    joined_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, org_id)
);

-- Taxonomy (F4) -----------------------------------------------------------------
-- embedding has no fixed dimension yet; the matching owner picks the model.

CREATE TABLE skills (
    id            text PRIMARY KEY,
    label         text NOT NULL,
    description   text NOT NULL DEFAULT '',
    taxonomy      text NOT NULL DEFAULT 'custom',
    taxonomy_uri  text,
    embedding     vector
);

CREATE TABLE roles (
    id            text PRIMARY KEY,
    label         text NOT NULL,
    description   text NOT NULL DEFAULT '',
    taxonomy      text NOT NULL DEFAULT 'custom',
    taxonomy_uri  text,
    embedding     vector
);

CREATE TABLE role_skills (
    role_id         text NOT NULL REFERENCES roles (id) ON DELETE CASCADE,
    skill_id        text NOT NULL REFERENCES skills (id) ON DELETE CASCADE,
    required_level  smallint NOT NULL DEFAULT 3 CHECK (required_level BETWEEN 1 AND 5),
    importance      real NOT NULL DEFAULT 1.0,
    PRIMARY KEY (role_id, skill_id)
);

-- Profiles (F1) -----------------------------------------------------------------
-- No age, gender or background columns: they must not influence matching.

CREATE TABLE profiles (
    user_id          text PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    segment          text NOT NULL CHECK (segment IN ('working', 'graduate', 'switcher')),
    interests        text[] NOT NULL DEFAULT '{}',
    hours_per_week   integer NOT NULL DEFAULT 0 CHECK (hours_per_week BETWEEN 0 AND 80),
    budget_myr       numeric(10, 2) NOT NULL DEFAULT 0,
    hrd_eligible     boolean NOT NULL DEFAULT false,
    current_role_id  text REFERENCES roles (id),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE user_skills (
    user_id     text NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    skill_id    text NOT NULL REFERENCES skills (id) ON DELETE CASCADE,
    level       smallint NOT NULL CHECK (level BETWEEN 1 AND 5),
    source      text NOT NULL CHECK (source IN ('cv', 'form', 'confirmed')),
    confidence  real CHECK (confidence BETWEEN 0 AND 1),
    PRIMARY KEY (user_id, skill_id)
);

-- Trends (F2) -------------------------------------------------------------------

CREATE TABLE snapshots (
    id          bigserial PRIMARY KEY,
    source      text NOT NULL,
    url         text NOT NULL DEFAULT '',
    fetched_at  timestamptz NOT NULL,
    version     text NOT NULL,
    notes       text NOT NULL DEFAULT '',
    UNIQUE (source, version)
);

CREATE TABLE trend_signals (
    id                  bigserial PRIMARY KEY,
    snapshot_id         bigint NOT NULL REFERENCES snapshots (id) ON DELETE CASCADE,
    entity_type         text NOT NULL CHECK (entity_type IN ('role', 'skill')),
    entity_id           text NOT NULL,
    direction           text NOT NULL CHECK (direction IN ('rising', 'stable', 'declining')),
    growth_rate         real NOT NULL,
    ai_exposure         real NOT NULL CHECK (ai_exposure BETWEEN 0 AND 1),
    automation_share    real NOT NULL CHECK (automation_share BETWEEN 0 AND 1),
    augmentation_share  real NOT NULL CHECK (augmentation_share BETWEEN 0 AND 1),
    UNIQUE (snapshot_id, entity_type, entity_id)
);

CREATE INDEX trend_signals_entity_idx ON trend_signals (entity_type, entity_id);

-- Courses (F5) ------------------------------------------------------------------

CREATE TABLE courses (
    id             text PRIMARY KEY,
    title          text NOT NULL,
    provider       text NOT NULL,
    url            text NOT NULL,
    hours          numeric(6, 1) NOT NULL CHECK (hours >= 0),
    cost_myr       numeric(10, 2) NOT NULL DEFAULT 0 CHECK (cost_myr >= 0),
    hrd_claimable  boolean NOT NULL DEFAULT false,
    verified_at    date NOT NULL,
    skill_ids      text[] NOT NULL DEFAULT '{}'
);

-- SDGs (F6) ---------------------------------------------------------------------

CREATE TABLE sdg_targets (
    id          text PRIMARY KEY,          -- e.g. '4.4'
    goal        smallint NOT NULL CHECK (goal BETWEEN 1 AND 17),
    label       text NOT NULL,
    source_url  text NOT NULL DEFAULT ''
);

CREATE TABLE role_sdg_map (
    role_id        text NOT NULL REFERENCES roles (id) ON DELETE CASCADE,
    sdg_target_id  text NOT NULL REFERENCES sdg_targets (id),
    reason         text NOT NULL,
    reviewed_by    text,
    reviewed_at    date,
    PRIMARY KEY (role_id, sdg_target_id)
);

CREATE TABLE skill_sdg_map (
    skill_id       text NOT NULL REFERENCES skills (id) ON DELETE CASCADE,
    sdg_target_id  text NOT NULL REFERENCES sdg_targets (id),
    reason         text NOT NULL,
    reviewed_by    text,
    reviewed_at    date,
    PRIMARY KEY (skill_id, sdg_target_id)
);

-- migrate:down

DROP TABLE IF EXISTS skill_sdg_map, role_sdg_map, sdg_targets, courses, trend_signals,
    snapshots, user_skills, profiles, role_skills, roles, skills, memberships,
    organizations, users;
