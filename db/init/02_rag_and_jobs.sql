-- 02_rag_and_jobs.sql

-- Past cases / knowledge base chunks (for RAG)
-- NOTE: set dimension to what you actually use (e.g., 768, 1024, 1536).
-- If you are unsure, pick 768 and keep it consistent everywhere.
CREATE TABLE IF NOT EXISTS rca_knowledge (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),

  source TEXT NOT NULL,           -- e.g., "airflow_log", "doc", "manual_case"
  doc_id TEXT,                    -- optional external id
  chunk_id TEXT,                  -- optional chunk id

  content TEXT NOT NULL,
  embedding VECTOR(768)           -- pgvector
);

CREATE INDEX IF NOT EXISTS idx_rca_knowledge_ts ON rca_knowledge(ts DESC);

-- Vector index (you can drop/recreate later after data grows)
-- If you use cosine similarity, use vector_cosine_ops.
-- For L2 distance use vector_l2_ops.
CREATE INDEX IF NOT EXISTS idx_rca_knowledge_embedding
ON rca_knowledge USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);


-- RCA job queue (agent picks up jobs from here)
CREATE TABLE IF NOT EXISTS rca_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,

  status TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING / PROCESSING / DONE / FAILED
  attempts INT NOT NULL DEFAULT 0,

  last_error TEXT
);

-- One incident should have at most one active job row (simple queue model)
CREATE UNIQUE INDEX IF NOT EXISTS uq_rca_jobs_incident ON rca_jobs(incident_id);
CREATE INDEX IF NOT EXISTS idx_rca_jobs_status_ts ON rca_jobs(status, ts);
