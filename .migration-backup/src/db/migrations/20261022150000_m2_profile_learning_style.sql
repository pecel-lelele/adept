-- migrate:up
-- Learning style from the intake questionnaire (handbook must-have 1: "interests, hours per
-- week and learning style"). Previously accepted by the API but not stored.

ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS learning_style text NOT NULL DEFAULT 'mixed'
        CHECK (learning_style IN ('video', 'reading', 'hands-on', 'classroom', 'mixed'));

-- migrate:down

ALTER TABLE profiles DROP COLUMN IF EXISTS learning_style;
