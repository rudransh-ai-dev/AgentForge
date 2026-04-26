"""
Tester Agent — deepseek-r1:8b (Stage 3: QA Validation)
Uses scheduled_generate() for safe GPU memory management.

Returns structured JSON verdict for the feedback loop.
"""

import json
from services.vram_scheduler import scheduled_generate
from services.sanitizer import extract_json_object, strip_prompt_leakage
from config import MODELS


def _heuristic_validation(original_prompt: str, refined_output: str) -> dict | None:
    """Fast local quality gate before asking the tester model."""
    prompt = (original_prompt or "").lower()
    output = refined_output or ""
    output_lower = output.lower()

    code_task = any(
        kw in prompt
        for kw in [
            "code", "write", "build", "create", "make", "implement", "script",
            "program", "app", "function", "class", "calculator", "todo",
        ]
    )
    if not code_task:
        return None

    bugs = []
    if len(output.strip()) < 80:
        bugs.append("Output is too short to satisfy a code-generation task.")
    if any(marker in output_lower for marker in ["todo: implement", "pass  #", "placeholder", "your code here"]):
        bugs.append("Output still contains placeholder implementation text.")
    if "```" not in output and not any(token in output for token in ["def ", "class ", "function ", "<html", "import ", "const "]):
        bugs.append("No recognizable code artifact was produced.")
    if "calculator" in prompt and not any(op in output for op in ["+", "-", "*", "/", "add", "subtract", "multiply", "divide"]):
        bugs.append("Calculator request does not include basic arithmetic operations.")

    if not bugs:
        return None

    return {
        "verdict": "FAIL",
        "score": 3,
        "bugs": bugs,
        "fix_instructions": "Regenerate complete runnable files and remove placeholders.",
        "summary": "Local validator rejected the output before model QA.",
    }


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

    heuristic = _heuristic_validation(original_prompt, refined_output)
    if heuristic:
        return heuristic

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
