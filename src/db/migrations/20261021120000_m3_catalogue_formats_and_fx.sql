-- migrate:up
-- M3 (F5): course formats, corporate bundles, provider types, foreign-currency prices and
-- live exchange rates from Bank Negara Malaysia (see docs/decisions.md M3-019).

ALTER TABLE courses
    ADD COLUMN format text NOT NULL DEFAULT 'self_paced'
        CHECK (format IN ('self_paced', 'live_online', 'in_person', 'hybrid', 'subscription')),
    ADD COLUMN audience text NOT NULL DEFAULT 'individual'
        CHECK (audience IN ('individual', 'corporate', 'both')),
    ADD COLUMN price_basis text NOT NULL DEFAULT 'per_course'
        CHECK (price_basis IN ('per_course', 'per_user_year', 'per_user_month', 'per_group')),
    ADD COLUMN currency text NOT NULL DEFAULT 'MYR',
    ADD COLUMN list_price numeric(10, 2),
    ADD COLUMN provider_type text NOT NULL DEFAULT 'private_provider'
        CHECK (provider_type IN ('mooc', 'university', 'industry_body', 'professional_body',
                                 'private_provider', 'government')),
    ADD COLUMN location text,      -- NULL = not stated
    ADD COLUMN price_note text;    -- how cost_myr was derived; NULL for ringgit prices

-- Daily rates from the Bank Negara Malaysia OpenAPI, used to show foreign-currency prices
-- in ringgit with the rate and its date.
CREATE TABLE fx_rates (
    currency      text NOT NULL,
    rate_date     date NOT NULL,
    selling_rate  numeric(12, 6) NOT NULL CHECK (selling_rate > 0),
    unit          integer NOT NULL DEFAULT 1 CHECK (unit > 0),
    source        text NOT NULL DEFAULT 'Bank Negara Malaysia OpenAPI',
    fetched_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (currency, rate_date)
);

-- migrate:down

DROP TABLE IF EXISTS fx_rates;
ALTER TABLE courses
    DROP COLUMN IF EXISTS format,
    DROP COLUMN IF EXISTS audience,
    DROP COLUMN IF EXISTS price_basis,
    DROP COLUMN IF EXISTS currency,
    DROP COLUMN IF EXISTS list_price,
    DROP COLUMN IF EXISTS provider_type,
    DROP COLUMN IF EXISTS location,
    DROP COLUMN IF EXISTS price_note;
