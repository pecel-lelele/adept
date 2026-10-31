-- migrate:up
-- M1-024: one matcher per trend series. A paper may hold one row per method, so MiniLM evidence
-- stays intact while Gemini rows are added; every read names a single method, so no window can
-- mix them. Each stored day is also per method (a day is only complete for the method that
-- fetched and matched it).
ALTER TABLE trend_paper_mentions DROP CONSTRAINT trend_paper_mentions_published_on_fkey;
ALTER TABLE trend_paper_mentions DROP CONSTRAINT trend_paper_mentions_pkey;
ALTER TABLE trend_paper_mentions DROP CONSTRAINT trend_paper_mentions_method_check;
ALTER TABLE trend_fetched_days DROP CONSTRAINT trend_fetched_days_pkey;

ALTER TABLE trend_fetched_days ADD COLUMN method text;
-- A day's papers were saved in one batch, so they share a method. Empty days have no papers to
-- say otherwise and take MiniLM, the only method that was ever primary.
UPDATE trend_fetched_days d SET method = COALESCE(
    (SELECT min(m.method) FROM trend_paper_mentions m WHERE m.published_on = d.day), 'M1-014');
-- Defensive: if a day ever did hold two methods, give the other method its own day row.
INSERT INTO trend_fetched_days (day, papers, fetched_on, method)
SELECT m.published_on, count(*), d.fetched_on, m.method
FROM trend_paper_mentions m JOIN trend_fetched_days d ON d.day = m.published_on
WHERE m.method <> d.method
GROUP BY m.published_on, d.fetched_on, m.method;
UPDATE trend_fetched_days d SET papers = (
    SELECT count(*) FROM trend_paper_mentions m WHERE m.published_on = d.day AND m.method = d.method)
WHERE EXISTS (
    SELECT 1 FROM trend_paper_mentions m WHERE m.published_on = d.day AND m.method <> d.method);

ALTER TABLE trend_fetched_days ALTER COLUMN method SET NOT NULL;
ALTER TABLE trend_fetched_days ADD PRIMARY KEY (day, method);
ALTER TABLE trend_fetched_days ADD CONSTRAINT trend_fetched_days_method_check
    CHECK (method IN ('M1-014', 'M1-017', 'M1-024'));
ALTER TABLE trend_paper_mentions ADD PRIMARY KEY (arxiv_id, method);
ALTER TABLE trend_paper_mentions ADD CONSTRAINT trend_paper_mentions_method_check
    CHECK (method IN ('M1-014', 'M1-017', 'M1-024'));
ALTER TABLE trend_paper_mentions ADD CONSTRAINT trend_paper_mentions_day_method_fkey
    FOREIGN KEY (published_on, method) REFERENCES trend_fetched_days(day, method) ON DELETE CASCADE;

DROP INDEX trend_paper_mentions_day_idx;
CREATE INDEX trend_paper_mentions_method_day_idx ON trend_paper_mentions (method, published_on);

-- One stored threshold per primary model, chosen by the rule named in `rule`.
CREATE TABLE trend_matcher_calibration (
    model text PRIMARY KEY,
    threshold double precision NOT NULL,
    rule text NOT NULL CHECK (rule IN ('minilm_mentions_per_paper', 'documented_minilm_rate')),
    reference_rate double precision NOT NULL CHECK (reference_rate >= 0),
    reference_papers integer NOT NULL CHECK (reference_papers >= 0),
    calibrated_on date NOT NULL
);

-- migrate:down
-- Data loss: removes Gemini-primary rows and the per-model thresholds. MiniLM rows are kept.
DROP TABLE trend_matcher_calibration;

DROP INDEX trend_paper_mentions_method_day_idx;
ALTER TABLE trend_paper_mentions DROP CONSTRAINT trend_paper_mentions_day_method_fkey;
ALTER TABLE trend_paper_mentions DROP CONSTRAINT trend_paper_mentions_method_check;
ALTER TABLE trend_paper_mentions DROP CONSTRAINT trend_paper_mentions_pkey;
ALTER TABLE trend_fetched_days DROP CONSTRAINT trend_fetched_days_method_check;
ALTER TABLE trend_fetched_days DROP CONSTRAINT trend_fetched_days_pkey;

DELETE FROM trend_paper_mentions WHERE method = 'M1-024';
DELETE FROM trend_fetched_days WHERE method = 'M1-024';
-- Keep one method per day and paper, preferring MiniLM ('M1-014' sorts first).
DELETE FROM trend_paper_mentions m USING trend_paper_mentions o
    WHERE m.arxiv_id = o.arxiv_id AND m.method > o.method;
DELETE FROM trend_fetched_days d USING trend_fetched_days o
    WHERE d.day = o.day AND d.method > o.method;
DELETE FROM trend_paper_mentions m WHERE NOT EXISTS (
    SELECT 1 FROM trend_fetched_days d WHERE d.day = m.published_on AND d.method = m.method);
ALTER TABLE trend_fetched_days DROP COLUMN method;

ALTER TABLE trend_fetched_days ADD PRIMARY KEY (day);
ALTER TABLE trend_paper_mentions ADD PRIMARY KEY (arxiv_id);
ALTER TABLE trend_paper_mentions ADD CONSTRAINT trend_paper_mentions_method_check
    CHECK (method IN ('M1-014', 'M1-017'));
ALTER TABLE trend_paper_mentions ADD CONSTRAINT trend_paper_mentions_published_on_fkey
    FOREIGN KEY (published_on) REFERENCES trend_fetched_days(day) ON DELETE CASCADE;
CREATE INDEX trend_paper_mentions_day_idx ON trend_paper_mentions (published_on);
