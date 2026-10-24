-- migrate:up
-- Preserve course facts with progress so accepted learning survives target changes,
-- catalogue edits and retirement. Evidence remains separate and can still be revoked.
ALTER TABLE course_progress ADD COLUMN course_snapshot jsonb;

-- Prefer the original saved plan for existing progress. If that plan was already replaced,
-- its original course facts are unavailable: backfill the surviving catalogue record.
UPDATE course_progress p
SET course_snapshot = COALESCE(
    (
        SELECT course.value
        FROM pathway_plans plan
        CROSS JOIN LATERAL jsonb_array_elements(plan.steps->'steps') step
        CROSS JOIN LATERAL jsonb_array_elements(step.value->'courses') course
        WHERE plan.user_id = p.user_id AND plan.role_id = p.role_id
          AND course.value->>'id' = p.course_id
        LIMIT 1
    ),
    (
        SELECT jsonb_strip_nulls(to_jsonb(c)) || jsonb_build_object(
            'source', jsonb_build_object(
                'name', COALESCE(NULLIF(c.source_name, ''), c.provider),
                'url', COALESCE(NULLIF(c.source_url, ''), c.url),
                'retrieved_at', c.verified_at
            )
        )
        FROM courses c WHERE c.id = p.course_id
    )
);

-- migrate:down
ALTER TABLE course_progress DROP COLUMN course_snapshot;
