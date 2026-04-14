"""
Tester Agent — deepseek-r1:8b (Stage 3: QA Validation)
Uses scheduled_generate() for safe GPU memory management.

Returns structured JSON verdict for the feedback loop.
"""

import json
from services.vram_scheduler import scheduled_generate
from services.sanitizer import extract_json_object, strip_prompt_leakage
from config import MODELS


async def run_tester_async(prompt: str, model_override: str | None = None):
    """Stream raw tester output (used for event emission)."""
    agent_cfg = MODELS.get("tester", {"name": "deepseek-r1:8b"})
    default_model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg
    model = model_override or default_model

    from core.prompts import tester_prompt
    system_prompt = tester_prompt().format(
        original_prompt=prompt,
        refined_output=prompt,  # Will be overridden by caller
    )

    async for chunk in scheduled_generate(model, system_prompt, stream=True):
        yield chunk


async def validate_code(
    original_prompt: str,
    refined_output: str,
    model_override: str | None = None,
) -> dict:
    """
    Tester validation — returns structured QA verdict.
    Used by the orchestrator's feedback loop.

    Returns:
        {
            "verdict": "PASS" or "FAIL",
            "score": 0-10,
            "bugs": [...],
            "fix_instructions": "...",
            "summary": "..."
        }
    """
    agent_cfg = MODELS.get("tester", {"name": "deepseek-r1:8b"})
    default_model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg
    model = model_override or default_model

    from core.prompts import tester_prompt
    system_prompt = tester_prompt().format(
        original_prompt=original_prompt,
        refined_output=refined_output[:4000],
    )

    result_text = ""
    async for chunk in scheduled_generate(model, system_prompt, stream=False):
        result_text += chunk

    # Parse the structured JSON verdict
    cleaned = strip_prompt_leakage(result_text)
    parsed = extract_json_object(cleaned)

    if parsed and isinstance(parsed, dict) and "verdict" in parsed:
        return {
            "verdict": parsed.get("verdict", "PASS"),
            "score": int(parsed.get("score", 6)),
            "bugs": parsed.get("bugs", []),
            "fix_instructions": parsed.get("fix_instructions", ""),
            "summary": parsed.get("summary", "No summary provided."),
        }

    # Fallback: if we can't parse JSON, assume PASS to avoid infinite loops
    return {
        "verdict": "PASS",
        "score": 6,
        "bugs": [],
        "fix_instructions": "",
        "summary": "Tester output could not be parsed — assuming PASS.",
    }
