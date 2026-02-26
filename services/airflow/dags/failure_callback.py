import traceback
import json
import os
from datetime import datetime, timezone
from utils.pg import pg_conn

def log_incident(context):
    try:
        ti = context["task_instance"]
        dag_id, task_id, run_id = ti.dag_id, ti.task_id, ti.run_id
        try_number = int(getattr(ti, "try_number", 1))

        exc = context.get("exception")
        error_message = str(exc) if exc else "Task failed"
        tb = traceback.format_exc()

        log_text = (
            f"[airflow_failure_callback] {datetime.now(timezone.utc).isoformat()}\n"
            f"dag_id={dag_id}\n"
            f"task_id={task_id}\n"
            f"run_id={run_id}\n"
            f"try_number={try_number}\n"
            f"error_message={error_message}\n\n"
            f"traceback:\n{tb}"
        )

        with pg_conn() as conn:
            with conn.cursor() as cur:
                # 1) Insert/update incident
                cur.execute(
                    """
                    INSERT INTO incidents (dag_id, task_id, run_id, try_number, status, error_message, ts, updated_at)
                    VALUES (%s, %s, %s, %s, 'NEW', %s, now(), now())
                    ON CONFLICT (dag_id, task_id, run_id, try_number)
                    DO UPDATE SET
                    status = CASE
                        WHEN incidents.status = 'RESOLVED' THEN 'NEW'  -- if a new failure happens, reopen
                        ELSE incidents.status
                    END,
                    error_message=EXCLUDED.error_message,
                    updated_at=now()

                    RETURNING id;
                    """,
                    (dag_id, task_id, run_id, try_number, error_message),
                )
                incident_id = cur.fetchone()[0]

                # 2) Store metrics snapshot (for Streamlit Metrics tab)
                metrics_payload = {
                    "failure_mode": os.getenv("FAILURE_MODE"),
                    "dag_id": dag_id,
                    "task_id": task_id,
                    "run_id": run_id,
                    "try_number": try_number,
                    "error_type": type(exc).__name__ if exc else None,
                }

                cur.execute(
                    """
                    INSERT INTO incident_metrics (incident_id, metrics)
                    VALUES (%s, %s::jsonb);
                    """,
                    (incident_id, json.dumps(metrics_payload)),
                )

                # 3) Store evidence
                cur.execute(
                    """
                    INSERT INTO task_logs (incident_id, ts, source, message)
                    VALUES (%s, now(), 'airflow', %s);
                    """,
                    (incident_id, log_text),
                )

                # 4) Enqueue RCA job (idempotent per incident)
                cur.execute(
                    """
                    INSERT INTO rca_jobs (incident_id, status, attempts, last_error, ts, updated_at)
                    VALUES (%s, 'PENDING', 0, NULL, now(), now())
                    ON CONFLICT (incident_id) DO NOTHING;
                    """,
                    (incident_id,),
                )

            conn.commit()

        print(f"[failure_callback] incident={incident_id} queued RCA job")

    except Exception as e:
        print("[failure_callback] ERROR:", repr(e))
        traceback.print_exc()
