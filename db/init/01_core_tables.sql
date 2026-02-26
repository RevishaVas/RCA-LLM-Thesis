-- 01_core_tables.sql

-- Incidents created by Airflow failure callback
CREATE TABLE IF NOT EXISTS incidents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  dag_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  try_number INT NOT NULL DEFAULT 1,

  status TEXT NOT NULL DEFAULT 'PROCESSING',  -- PROCESSING / RESOLVED
  error_message TEXT,

  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Helpful query indexes (inbox view)
CREATE INDEX IF NOT EXISTS idx_incidents_ts ON incidents(ts DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_dag_task ON incidents(dag_id, task_id);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);


-- Task logs / evidence rows (store last N log lines or structured evidence)
CREATE TABLE IF NOT EXISTS task_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,

  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  source TEXT NOT NULL DEFAULT 'airflow',  -- airflow / agent / system
  message TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_task_logs_incident_ts ON task_logs(incident_id, ts DESC);


-- Optional: metrics snapshot table (if you store metrics separately)
CREATE TABLE IF NOT EXISTS incident_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  metrics JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_incident_metrics_incident_ts ON incident_metrics(incident_id, ts DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_incidents_dag_task_run_try
ON incidents(dag_id, task_id, run_id, try_number);
