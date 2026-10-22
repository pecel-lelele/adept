-- migrate:up
ALTER TABLE roles ADD COLUMN is_target boolean NOT NULL DEFAULT true;
UPDATE roles SET is_target = false WHERE id IN (
    'bank-operations-executive', 'data-entry-clerk', 'logistics-supervisor'
);

-- migrate:down
ALTER TABLE roles DROP COLUMN is_target;
