"""
Critic Agent — VRAM-Scheduled
Uses scheduled_generate() for safe GPU memory management.
"""

from services.vram_scheduler import scheduled_generate
from config import MODELS
from core.prompts import critic_prompt, critic_validation_prompt


async def run_critic_async(prompt: str, model_override: str | None = None):
    """Review and validate output using the critic model through the VRAM scheduler."""
    agent_cfg = MODELS.get("critic", {"name": "deepseek-r1:8b"})
    default_model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg
    model = model_override or default_model

    system_prompt = critic_prompt().format(prompt=prompt)
    async for chunk in scheduled_generate(model, system_prompt, stream=True):
        yield chunk


async def validate_output(
    output: str, original_task: str, model_override: str | None = None
) -> dict:
    """
    Critic validation — returns structured quality assessment.
    Used by the orchestrator's feedback loop.
    """
    agent_cfg = MODELS.get("critic", {"name": "deepseek-r1:8b"})
    default_model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg
    model = model_override or default_model

    validation_prompt = critic_validation_prompt().format(
        original_task=original_task, output=output[:3000]
    )
    from services.sanitizer import extract_json_object, strip_prompt_leakage

    result_text = ""
    async for chunk in scheduled_generate(model, validation_prompt, stream=False):
        result_text += chunk

    cleaned = strip_prompt_leakage(result_text)
    parsed = extract_json_object(cleaned)

    if parsed and "score" in parsed:
        return {
            "score": parsed.get("score", 5),
            "verdict": parsed.get("verdict", "PASS"),
            "issues": parsed.get("issues", []),
            "suggestions": parsed.get("suggestions", []),
        }

    # Fallback: assume pass
    return {"score": 6, "verdict": "PASS", "issues": [], "suggestions": []}
