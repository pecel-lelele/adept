-- migrate:up
-- Live job openings from public employer and job-board feeds (src/pipelines/jobs), and paid
-- certification exams with dated fees. Reference data: no personal data, no ad text stored.
-- Never edit this file after it is merged; add a new migration instead.

CREATE TABLE job_postings (
    id               text PRIMARY KEY,           -- <source>:<board>:<posting id>
    source           text NOT NULL,              -- connector, e.g. greenhouse, workday, himalayas
    board            text NOT NULL,              -- employer or feed on that platform
    source_name      text NOT NULL,              -- how the source is credited in the UI
    employer         text NOT NULL,
    title            text NOT NULL,
    location         text NOT NULL DEFAULT '',
    work_mode        text NOT NULL DEFAULT 'onsite' CHECK (work_mode IN ('onsite', 'hybrid', 'remote')),
    remote_scope     text,                       -- remote only: who may apply (Malaysia, APAC, Worldwide)
    employment_type  text,
    seniority        text NOT NULL DEFAULT 'unknown'
        CHECK (seniority IN ('intern', 'entry', 'mid', 'senior', 'lead', 'unknown')),
    url              text NOT NULL,              -- the employer's or board's own ad (apply there)
    api_url          text NOT NULL,              -- the feed it was read from
    posted_at        date,
    expires_at       date,
    salary_min       numeric(12, 2),
    salary_max       numeric(12, 2),
    salary_currency  text,
    salary_period    text,
    role_id          text REFERENCES roles(id) ON DELETE SET NULL,
    role_method      text CHECK (role_method IN ('title', 'skills')),
    skill_ids        text[] NOT NULL DEFAULT '{}',   -- catalogue skills the ad names
    cert_ids         text[] NOT NULL DEFAULT '{}',   -- certifications the ad names
    first_seen       date NOT NULL,
    last_seen        date NOT NULL,
    active           boolean NOT NULL DEFAULT true
);

CREATE INDEX job_postings_role_active_idx ON job_postings (role_id) WHERE active;
CREATE INDEX job_postings_skills_idx ON job_postings USING gin (skill_ids);

-- One row per board per pipeline run: what was read, skipped (no key) or blocked (robots.txt).
CREATE TABLE job_fetch_log (
    source      text NOT NULL,
    board       text NOT NULL,
    fetched_on  date NOT NULL,
    status      text NOT NULL CHECK (status IN ('ok', 'skipped', 'blocked', 'error')),
    kept        integer NOT NULL DEFAULT 0,
    detail      text NOT NULL DEFAULT '',
    PRIMARY KEY (source, board, fetched_on)
);

-- Paid certification exams that follow catalogue courses (src/pipelines/jobs/certifications.py).
CREATE TABLE certifications (
    id              text PRIMARY KEY,
    name            text NOT NULL,
    issuer          text NOT NULL,
    exam_code       text NOT NULL,
    url             text NOT NULL,
    fee_amount      numeric(10, 2) NOT NULL CHECK (fee_amount >= 0),
    fee_currency    text NOT NULL,
    fee_myr         numeric(10, 2) NOT NULL CHECK (fee_myr >= 0),
    fee_note        text NOT NULL,
    fee_source_url  text NOT NULL,
    level           text NOT NULL CHECK (level IN ('foundational', 'associate', 'professional')),
    skill_ids       text[] NOT NULL,
    validity_note   text,
    verified_at     date NOT NULL
);

-- migrate:down
DROP TABLE IF EXISTS certifications;
DROP TABLE IF EXISTS job_fetch_log;
DROP TABLE IF EXISTS job_postings;
