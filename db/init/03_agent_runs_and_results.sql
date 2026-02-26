-- 03_agent_runs_and_results.sql

-- Each execution of the agent for an incident/model
CREATE TABLE IF NOT EXISTS agent_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  model_name TEXT NOT NULL,

  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  status TEXT NOT NULL DEFAULT 'FAILED',  -- FAILED / PROCESSING / RESOLVED
  attempt INT NOT NULL DEFAULT 1,
  error TEXT
);

-- Needed for ON CONFLICT upserts (this fixes your earlier error)
CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_runs_incident_model_attempt
ON agent_runs(incident_id, model_name, attempt);

CREATE INDEX IF NOT EXISTS idx_agent_runs_incident_ts ON agent_runs(incident_id, ts DESC);


-- Final RCA result per incident/model (latest or canonical output)
CREATE TABLE IF NOT EXISTS rca_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  model_name TEXT NOT NULL,

  ts TIMESTAMPTZ NOT NULL DEFAULT now(),

  root_cause TEXT NOT NULL,
  confidence NUMERIC(4,3) NOT NULL DEFAULT 0.0,
  recommendation TEXT NOT NULL,

  evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
  retrieved_cases JSONB NOT NULL DEFAULT '[]'::jsonb,
  raw_response JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Ensures "one result per incident per model" (enables ON CONFLICT)
CREATE UNIQUE INDEX IF NOT EXISTS uq_rca_results_incident_model
ON rca_results(incident_id, model_name);

CREATE INDEX IF NOT EXISTS idx_rca_results_incident_ts ON rca_results(incident_id, ts DESC);
