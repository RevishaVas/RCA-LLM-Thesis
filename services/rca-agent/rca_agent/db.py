import os
import psycopg2
from pgvector.psycopg2 import register_vector

def conn():
    c = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        dbname=os.getenv("POSTGRES_DB", "llmrca"),
        user=os.getenv("POSTGRES_USER", "llmrca"),
        password=os.getenv("POSTGRES_PASSWORD", "llmrca"),
        port=int(os.getenv("POSTGRES_PORT") or "5432"),
    )
    register_vector(c)  
    return c

def load_incident_bundle(c, incident_id: str):
    with c.cursor() as cur:
        cur.execute("""
            SELECT id, dag_id, task_id, run_id, try_number, status, error_message, ts
            FROM incidents
            WHERE id = %s
        """, (incident_id,))
        inc = cur.fetchone()
        if not inc:
            raise ValueError("Incident not found")

        cur.execute("""
            SELECT source, message, ts
            FROM task_logs
            WHERE incident_id = %s
            ORDER BY ts DESC
            LIMIT 20
        """, (incident_id,))
        rows = cur.fetchall()
        logs_text = "\n\n".join(f"[{ts}][{source}] {msg}" for source, msg, ts in rows)

        cur.execute("""
            SELECT metrics
            FROM incident_metrics
            WHERE incident_id = %s
            ORDER BY ts DESC
            LIMIT 1
        """, (incident_id,))
        m = cur.fetchone()
        metrics = m[0] if m else {}

    return {
        "incident_id": str(inc[0]),
        "dag_id": inc[1],
        "task_id": inc[2],
        "run_id": inc[3],
        "try_number": inc[4],
        "status": inc[5],
        "error_message": inc[6],
        "ts": inc[7].isoformat() if inc[7] else None,
        "logs": logs_text[-8000:],
        "metrics": metrics,
    }

def claim_next_job(c):
    """
    Atomically claim one pending job.
    status: PENDING -> PROCESSING
    """
    with c.cursor() as cur:
        cur.execute("""
            UPDATE rca_jobs
            SET status='PROCESSING',
                updated_at=now()
            WHERE id = (
                SELECT id
                FROM rca_jobs
                WHERE status='PENDING'
                ORDER BY ts ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id, incident_id, attempts;
        """)
        row = cur.fetchone()
    c.commit()
    return row  # (job_id, incident_id, attempts) or None
