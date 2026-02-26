import os
import time
import traceback

from .config import init_gemini
from .db import conn, claim_next_job
from .graph import run_trca

POLL_SECONDS = int(os.getenv("RCA_POLL_SECONDS", "2"))

def set_incident_status(c, incident_id: str, status: str):
    with c.cursor() as cur:
        cur.execute("UPDATE incidents SET status=%s, updated_at=now() WHERE id=%s;", (status, incident_id))
    c.commit()

def finish_job(c, job_id: str, status: str, last_error: str | None = None):
    with c.cursor() as cur:
        cur.execute("""
            UPDATE rca_jobs
            SET status=%s,
                last_error=%s,
                updated_at=now()
            WHERE id=%s;
        """, (status, last_error, job_id))
    c.commit()

def bump_attempts(c, job_id: str):
    with c.cursor() as cur:
        cur.execute("UPDATE rca_jobs SET attempts = attempts + 1, updated_at=now() WHERE id=%s;", (job_id,))
    c.commit()

if __name__ == "__main__":
    init_gemini()
    print("[RCA] Agent started (clean queue mode)")

    while True:
        with conn() as c:
            job = claim_next_job(c)

        if not job:
            time.sleep(POLL_SECONDS)
            continue

        job_id, incident_id, attempts = job
        job_id, incident_id = str(job_id), str(incident_id)

        print(f"[RCA] Claimed job={job_id} incident={incident_id} attempts={attempts}")

        try:
            with conn() as c:
                bump_attempts(c, job_id)
                set_incident_status(c, incident_id, "PROCESSING")

            with conn() as c:
                run_trca(c, incident_id)

            with conn() as c:
                set_incident_status(c, incident_id, "RESOLVED")
                finish_job(c, job_id, "DONE", None)

            print(f"[RCA] Job {job_id} DONE")

        except Exception as e:
            err = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            print("[RCA] ERROR:", err[:400])
            with conn() as c:
                set_incident_status(c, incident_id, "FAILED")
                finish_job(c, job_id, "FAILED", err[:1200])



            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                time.sleep(60)
            else:
                time.sleep(2)
