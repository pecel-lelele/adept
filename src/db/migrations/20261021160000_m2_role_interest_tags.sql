-- migrate:up
-- F4 role-interest tags are part of the synthetic role catalogue.
ALTER TABLE roles
    ADD COLUMN interest_tags text;

-- The upgrade test seeds roles before applying this migration. Preserve those
-- rows and fill their catalogue tags because the seed loader skips conflicts.
UPDATE roles
SET interest_tags = CASE id
    WHEN 'data-analyst' THEN 'data|analytics|software'
    WHEN 'ai-operations-specialist' THEN 'software|AI|automation'
    WHEN 'process-automation-analyst' THEN 'process improvement|operations|automation|finance'
    WHEN 'compliance-analytics-officer' THEN 'finance|risk|data|compliance'
    ELSE interest_tags
END
WHERE interest_tags IS NULL
  AND id IN (
      'data-analyst',
      'ai-operations-specialist',
      'process-automation-analyst',
      'compliance-analytics-officer'
  );

-- migrate:down
ALTER TABLE roles
    DROP COLUMN interest_tags;
