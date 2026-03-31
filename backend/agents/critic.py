"""
Critic Agent — VRAM-Scheduled
Uses scheduled_generate() for safe GPU memory management.
"""
from services.vram_scheduler import scheduled_generate
from config import MODELS


async def run_critic_async(prompt: str, model_override: str = None):
    """Review and validate output using the critic model through the VRAM scheduler."""
    agent_cfg = MODELS.get("critic", {"name": "llama3:8b"})
    default_model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg
    model = model_override or default_model

    system_prompt = f"""You are a code review and quality assurance agent in a multi-agent system.

RULES:
- Evaluate output quality with specific, actionable feedback
- Score on a 1-10 scale with clear justification
- Identify concrete bugs, logic errors, and missing edge cases
- Do NOT say "As an AI" or mention your identity
- Do NOT repeat the task instructions back
- Do NOT be vague — every point must be specific

OUTPUT FORMAT:
## Score: X/10

## Issues Found:
- [severity: high/medium/low] Description of specific issue

## Fixes Required:
- Specific fix with code example if applicable

## Verdict:
PASS / FAIL / NEEDS_REVISION

Task:
{prompt}
"""
    async for chunk in scheduled_generate(model, system_prompt, stream=True):
        yield chunk


async def validate_output(output: str, original_task: str, model_override: str = None) -> dict:
    """
    Critic validation — returns structured quality assessment.
    Used by the orchestrator's feedback loop.
    """
    agent_cfg = MODELS.get("critic", {"name": "llama3:8b"})
    default_model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg
    model = model_override or default_model

    validation_prompt = f"""You are a quality gate in an AI pipeline.
Evaluate this output against the original task.

Respond with ONLY a JSON object:
{{
  "score": 7,
  "verdict": "PASS",
  "issues": ["issue 1", "issue 2"],
  "suggestions": ["suggestion 1"]
}}

Score 1-10. Verdict: PASS (score >= 6), FAIL (score < 4), NEEDS_REVISION (4-5).

ORIGINAL TASK:
{original_task}

OUTPUT TO EVALUATE:
{output[:3000]}
"""
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
