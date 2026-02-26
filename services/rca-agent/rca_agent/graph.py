import json
import os
import traceback


from .db import load_incident_bundle
from .nodes import run_gemini
from .rag import retrieve_rag_hits
from .nodes_groq import run_groq

DEFAULT_MODEL = [
    ("gemini", os.getenv("GEMINI_MODEL", "gemini-2.5-flash")),
    ("groq", os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")),
]

def _set_incident_status(c, incident_id: str, status: str):
    with c.cursor() as cur:
        cur.execute("UPDATE incidents SET status=%s, updated_at=now() WHERE id=%s;", (status, incident_id))
    c.commit()

def upsert_rca_result(c, incident_id: str, model_name: str, r: dict, latency_ms: int | None = None,retrieved_cases: list | None = None,rag_query: str | None = None,):
    
    root_cause = (r.get("root_cause") or "Unknown").strip()
    confidence = float(r.get("confidence") or 0.0)

    corrective = r.get("corrective_actions") or []
    preventive = r.get("preventive_actions") or []

    recommendation = "Corrective actions:\n- " + "\n- ".join(map(str, corrective)) if corrective else "Corrective actions: N/A"
    recommendation += "\n\nPreventive actions:\n- " + "\n- ".join(map(str, preventive)) if preventive else "\n\nPreventive actions: N/A"

    evidence = r.get("evidence") if isinstance(r.get("evidence"), list) else []
    retrieved_cases = retrieved_cases or []  

    raw_response = {
        "model_output": r,
        "latency_ms": latency_ms,
        "rag_query": rag_query,
    }

    with c.cursor() as cur:
        cur.execute("""
            INSERT INTO rca_results
              (incident_id, model_name, ts, root_cause, confidence, recommendation, evidence, retrieved_cases, raw_response)
            VALUES (%s, %s, now(), %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
            ON CONFLICT (incident_id, model_name)
            DO UPDATE SET
              ts = now(),
              root_cause = EXCLUDED.root_cause,
              confidence = EXCLUDED.confidence,
              recommendation = EXCLUDED.recommendation,
              evidence = EXCLUDED.evidence,
              retrieved_cases = EXCLUDED.retrieved_cases,
              raw_response = EXCLUDED.raw_response;
        """, (
            incident_id, model_name,
            root_cause, confidence, recommendation,
            json.dumps(evidence), json.dumps(retrieved_cases), json.dumps(raw_response)
        ))
    c.commit()

def run_trca(c, incident_id: str, model_name: str | None = None, job_id: str | None = None):
    """
    Runs RCA with:
    - RAG retrieval (pgvector) -> injected into prompt via bundle["rag_hits"]
    - Two comparative models: Gemini + HuggingFace Inference API
    - HITL: mark NEEDS_REVIEW if any model low-confidence or has no evidence
    - Stores one row per (incident_id, model_name) in rca_results
    """

    _set_incident_status(c, incident_id, "PROCESSING")

    
    models = DEFAULT_MODEL
    if model_name:
        models = [("gemini", model_name), ("groq", os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"))]

    try:
        bundle = load_incident_bundle(c, incident_id)

        
        incident_text = f"""DAG={bundle['dag_id']}
TASK={bundle['task_id']}
ERROR={bundle['error_message']}
LOGS={bundle['logs'][-2000:]}
METRICS={json.dumps(bundle['metrics'], default=str)}
""".strip()

        
        rag_hits, _ = retrieve_rag_hits(c, incident_text, top_k=4)
        bundle["rag_hits"] = rag_hits

        
        # -------------------------
        outputs = {}  # model_name -> result_json

        for provider, mname in models:
            if provider == "gemini":
                result_json, latency_ms = run_gemini(bundle, mname)
            elif provider == "groq":
                result_json, latency_ms = run_groq(bundle, mname)
            else:
                raise ValueError(f"Unknown provider: {provider}")

            upsert_rca_result(
                c,
                incident_id,
                mname,  # stored under this model name in rca_results
                result_json,
                latency_ms=latency_ms,
                retrieved_cases=bundle.get("rag_hits"),
                rag_query=incident_text,
            )

            outputs[mname] = result_json

        
        confs = []
        MIN_EVIDENCE = int(os.getenv("HITL_MIN_EVIDENCE", "3")) 
        evidence_ok = True
        for out in outputs.values():
            confs.append(float(out.get("confidence") or 0.0))
            evidence = out.get("evidence") or []
            if len(evidence) < MIN_EVIDENCE: 
            # if len(out.get("evidence") or []) == 0:
                evidence_ok = False

        # If any model is low-confidence OR evidence missing => NEEDS_REVIEW
        
        needs_review = (min(confs) < 0.6) or (not evidence_ok) 

        _set_incident_status(c, incident_id, "NEEDS_REVIEW" if needs_review else "RESOLVED")

        
        return outputs

    except Exception:
        try:
            c.rollback()
        except Exception:
            pass
        _set_incident_status(c, incident_id, "FAILED")
        raise
