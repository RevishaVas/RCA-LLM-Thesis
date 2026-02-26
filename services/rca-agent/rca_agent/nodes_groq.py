import os
import time
import json

from groq import Groq

from .validate import RCAResult
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .nodes import _extract_json, _coerce_rca_fields


def run_groq(bundle: dict, model_name: str):
    """
    Backwards-compatible function name.
    Uses Groq instead of Hugging Face.
    """

    groq_key = os.getenv("GROQ_API_KEY")
    groq_model = os.getenv("GROQ_MODEL", model_name)

    if not groq_key:
        raise RuntimeError("GROQ_API_KEY not set")
    if not groq_model:
        raise RuntimeError("GROQ_MODEL not set")

    client = Groq(api_key=groq_key)

    prompt = SYSTEM_PROMPT.strip() + "\n\n" + build_user_prompt(bundle).strip()

    start = time.time()

    resp = client.chat.completions.create(
        model=groq_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": build_user_prompt(bundle).strip()},
        ],
        temperature=0.2,
        max_tokens=700,
    )

    latency_ms = int((time.time() - start) * 1000)

    text = resp.choices[0].message.content

    json_text = _extract_json(text)
    if not json_text:
        raise ValueError(f"No JSON returned from Groq. Raw: {text[:300]}")

    parsed = json.loads(json_text)
    parsed = _coerce_rca_fields(parsed)

    validated = RCAResult(**parsed)
    return validated.model_dump(), latency_ms
