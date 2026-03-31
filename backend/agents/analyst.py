"""
Analyst Agent — VRAM-Scheduled
Uses scheduled_generate() for safe GPU memory management.
"""
from services.vram_scheduler import scheduled_generate
from config import MODELS


async def run_analyst_async(prompt: str, model_override: str = None):
    """Analyze and explain using the analyst model through the VRAM scheduler."""
    agent_cfg = MODELS.get("analyst", {"name": "llama3:8b"})
    default_model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg
    model = model_override or default_model

    system_prompt = f"""You are an analysis agent in a multi-agent system.

RULES:
- Deliver precise, technical, actionable responses
- Use structured format: headings, bullet points, numbered steps
- Prioritize clarity over verbosity
- Do NOT say "As an AI" or mention your identity
- Do NOT repeat the task instructions back
- Do NOT add filler phrases or generic disclaimers
- No unnecessary background explanations

WHEN APPLICABLE:
- Break problems into clear steps
- Suggest architecture, tools, or implementation ideas
- Highlight trade-offs and limitations
- Provide concrete examples

OUTPUT STYLE:
- Direct, technical, efficient
- No repetition of input
- Machine-readable structure when possible

Task:
{prompt}
"""
    async for chunk in scheduled_generate(model, system_prompt, stream=True):
        yield chunk
