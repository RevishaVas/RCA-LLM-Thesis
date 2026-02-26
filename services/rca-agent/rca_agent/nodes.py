import os
import time
import json
from google import genai
from .validate import RCAResult
from .prompts import SYSTEM_PROMPT, build_user_prompt

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

def _extract_json(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```JSON", "").replace("```", "").strip()
    start_i = text.find("{")
    end_i = text.rfind("}")
    if start_i != -1 and end_i != -1 and end_i > start_i:
        return text[start_i:end_i + 1]
    return ""

def _coerce_rca_fields(parsed: dict) -> dict:
    ev = parsed.get("evidence")
    if ev is None:
        parsed["evidence"] = []
    elif isinstance(ev, list):
        parsed["evidence"] = [str(x) for x in ev]
    else:
        parsed["evidence"] = [str(ev)]

    ca = parsed.get("corrective_actions")
    if ca is None:
        parsed["corrective_actions"] = []
    elif isinstance(ca, list):
        parsed["corrective_actions"] = [str(x) for x in ca]
    else:
        parsed["corrective_actions"] = [str(ca)]

    pa = parsed.get("preventive_actions")
    if pa is None:
        parsed["preventive_actions"] = []
    elif isinstance(pa, list):
        parsed["preventive_actions"] = [str(x) for x in pa]
    else:
        parsed["preventive_actions"] = [str(pa)]

    conf = parsed.get("confidence")
    if isinstance(conf, str):
        m = {"LOW": 0.3, "MEDIUM": 0.6, "HIGH": 0.9}
        parsed["confidence"] = m.get(conf.strip().upper(), 0.5)

    return parsed

def run_gemini(bundle: dict, model_name: str | None = None):
    start = time.time()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)
    model = model_name or DEFAULT_MODEL

    resp = client.models.generate_content(
        model=model,
        contents=[SYSTEM_PROMPT, build_user_prompt(bundle)],
    )

    latency_ms = int((time.time() - start) * 1000)

    raw_text = (resp.text or "").strip()
    json_text = _extract_json(raw_text)
    if not json_text:
        raise ValueError(f"No JSON returned from Gemini. Raw response: {raw_text[:300]}")

    parsed = json.loads(json_text)
    parsed = _coerce_rca_fields(parsed)

    validated = RCAResult(**parsed)
    return validated.model_dump(), latency_ms
