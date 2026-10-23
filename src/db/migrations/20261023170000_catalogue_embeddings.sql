-- migrate:up
-- Embeddings of catalogue entries (skills today) for cosine-similarity matching with pgvector.
-- One row per entry per embedding model; `text_hash` detects a changed label or alias list so
-- only those rows are re-embedded. Reference data: catalogue text only, never personal data.
-- Never edit this file after it is merged; add a new migration instead.

CREATE TABLE catalogue_embeddings (
    kind        text NOT NULL CHECK (kind IN ('skill')),
    item_id     text NOT NULL,
    model       text NOT NULL,               -- e.g. gemini-embedding-001@768
    text_hash   text NOT NULL,               -- sha256 of the embedded text
    embedding   vector(768) NOT NULL,        -- unit length, so <=> is cosine distance
    updated_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (kind, item_id, model)
);

CREATE INDEX catalogue_embeddings_hnsw
    ON catalogue_embeddings USING hnsw (embedding vector_cosine_ops);

-- migrate:down
DROP TABLE IF EXISTS catalogue_embeddings;
