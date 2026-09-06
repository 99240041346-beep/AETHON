-- AETHON semantic memory migration.
-- Requires a PostgreSQL installation with the pgvector extension available.

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE memories
    ADD COLUMN IF NOT EXISTS embedding vector(1536);

CREATE INDEX IF NOT EXISTS idx_memories_embedding_hnsw
    ON memories USING hnsw (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;
