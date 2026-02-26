import os
import time
import json
from google import genai
from pydantic import BaseModel, Field
from typing import List, Optional, Tuple


# ----- Pydantic schema (same as your validate.py) -----
class RCAResult(BaseModel):
    root_cause: str = Field(..., description="Most likely root cause")
    evidence: List[str] = Field(..., description="Log lines / metrics used as evidence")
    corrective_actions: List[str]
    preventive_actions: List[str]
    confidence: float = Field(..., ge=0.0, le=1.0)


SYSTEM_PROMPT = """
You are an expert data pipeline reliability engineer.

You perform root cause analysis (RCA) for Airflow-based data pipelines.

Rules:
- Use ONLY the provided logs, metrics, and context.
- Cite concrete evidence.
- Do NOT guess if evidence is insufficient.
- Output STRICT JSON that matches the provided schema.
- The field "confidence" MUST be a floating point number between 0.0 and 1.0.
- DO NOT use words like HIGH, MEDIUM, or LOW.
"""


def build_user_prompt(bundle: dict) -> str:
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

Task context:
{bundle['context']}

Return ONLY a JSON object with keys:
root_cause, evidence, corrective_actions, preventive_actions, confidence
"""


def run_gemini_once(bundle: dict, model_name: Optional[str] = None) -> Tuple[dict, int]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in Streamlit container")

    model = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    start = time.time()
    client = genai.Client(api_key=api_key)

    resp = client.models.generate_content(
        model=model,
        contents=[SYSTEM_PROMPT, build_user_prompt(bundle)],
    )

    latency_ms = int((time.time() - start) * 1000)

    raw_text = (resp.text or "").strip()

    # If Gemini returns extra text, try to extract JSON block
    if not raw_text.startswith("{"):
        first = raw_text.find("{")
        last = raw_text.rfind("}")
        if first != -1 and last != -1 and last > first:
            raw_text = raw_text[first:last + 1]

    parsed = json.loads(raw_text)

    # --- SAFETY COERCION ---
    conf = parsed.get("confidence")
    if isinstance(conf, str):
        conf_map = {"LOW": 0.3, "MEDIUM": 0.6, "HIGH": 0.9}
        parsed["confidence"] = conf_map.get(conf.upper(), 0.5)

    validated = RCAResult(**parsed)
    return validated.model_dump(), latency_ms
