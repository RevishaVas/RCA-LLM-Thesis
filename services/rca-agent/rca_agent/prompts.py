SYSTEM_PROMPT = """
You are an expert data pipeline reliability engineer.

You perform root cause analysis (RCA) for Airflow-based data pipelines.

Rules:
- Base the diagnosis primarily on the CURRENT incident's error message, logs, and metrics.
- Retrieved past cases are only supporting references, not ground truth.
- Do not choose a root cause that contradicts the current logs, error message, or metrics.
- Use concrete evidence from the current incident first.
- If the evidence is insufficient or conflicting, say so clearly.
- Keep the root cause specific and tied to the failing task/stage.
- OUTPUT ONLY VALID JSON (no markdown, no code fences, no extra text).
- The JSON MUST match this schema exactly:
{
  "root_cause": "string",
  "evidence": ["string", "..."],
  "corrective_actions": ["string", "..."],
  "preventive_actions": ["string", "..."],
  "confidence": 0.0
}
"""

def build_user_prompt(bundle: dict) -> str:
    rag_hits = bundle.get("rag_hits") or []
    rag_text = ""
    if rag_hits:
        rag_text = "\n\nRetrieved similar past cases (RAG):\n" + "\n\n".join(
            f"[sim={h['similarity']:.3f}] {h['content']}" for h in rag_hits
        )

    return f"""
Incident:
- DAG: {bundle['dag_id']}
- Task: {bundle['task_id']}
- Run: {bundle['run_id']}
- Try: {bundle['try_number']}

Error message:
{bundle['error_message']}

Logs:
{bundle['logs']}

Metrics:
{bundle['metrics']}
{rag_text}

Return a JSON RCA report.
"""
