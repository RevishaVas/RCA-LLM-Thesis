SYSTEM_PROMPT = """
You are an expert data pipeline reliability engineer.

You perform root cause analysis (RCA) for Airflow-based data pipelines.

Rules:
- Use ONLY the provided logs, metrics, and incident details.
- Cite concrete evidence.
- Do NOT guess if evidence is insufficient.
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
