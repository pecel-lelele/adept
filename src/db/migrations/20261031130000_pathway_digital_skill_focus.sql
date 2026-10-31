-- Issue #84: remove only the dated target-profile edges removed from the seed.
-- No learner skills, course history or current-role requirements are deleted.
-- migrate:up
DELETE FROM role_skills AS existing
USING (VALUES
    ('cloud-solutions-architect', 'stakeholder-management', 3, 0.6),
    ('cybersecurity-analyst', 'critical-thinking', 3, 0.5),
    ('ai-product-manager', 'stakeholder-management', 3, 0.8),
    ('ux-designer', 'stakeholder-management', 2, 0.4),
    ('energy-manager', 'stakeholder-management', 3, 0.5),
    ('esg-sustainability-analyst', 'stakeholder-management', 3, 0.5),
    ('learning-experience-designer', 'coaching-mentoring', 2, 0.4),
    ('tvet-digital-skills-trainer', 'coaching-mentoring', 3, 0.5),
    ('tvet-digital-skills-trainer', 'public-speaking', 3, 0.4),
    ('customer-success-specialist', 'stakeholder-management', 2, 0.5),
    ('people-analytics-specialist', 'change-management', 2, 0.5),
    ('hospitality-experience-manager', 'cross-cultural-communication', 3, 0.6)
) AS removed(role_id, skill_id, required_level, importance)
WHERE existing.role_id = removed.role_id AND existing.skill_id = removed.skill_id;

-- migrate:down
-- Restore the prior estimated requirement edges without overwriting later edits.
INSERT INTO role_skills (role_id, skill_id, required_level, importance)
VALUES
    ('cloud-solutions-architect', 'stakeholder-management', 3, 0.6),
    ('cybersecurity-analyst', 'critical-thinking', 3, 0.5),
    ('ai-product-manager', 'stakeholder-management', 3, 0.8),
    ('ux-designer', 'stakeholder-management', 2, 0.4),
    ('energy-manager', 'stakeholder-management', 3, 0.5),
    ('esg-sustainability-analyst', 'stakeholder-management', 3, 0.5),
    ('learning-experience-designer', 'coaching-mentoring', 2, 0.4),
    ('tvet-digital-skills-trainer', 'coaching-mentoring', 3, 0.5),
    ('tvet-digital-skills-trainer', 'public-speaking', 3, 0.4),
    ('customer-success-specialist', 'stakeholder-management', 2, 0.5),
    ('people-analytics-specialist', 'change-management', 2, 0.5),
    ('hospitality-experience-manager', 'cross-cultural-communication', 3, 0.6)
ON CONFLICT (role_id, skill_id) DO NOTHING;
