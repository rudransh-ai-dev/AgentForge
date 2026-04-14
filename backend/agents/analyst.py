"""
Analyst Agent — VRAM-Scheduled
Uses scheduled_generate() for safe GPU memory management.
"""

from services.vram_scheduler import scheduled_generate
from config import MODELS
from core.prompts import analyst_prompt


async def run_analyst_async(prompt: str, model_override: str | None = None):
    """Analyze and explain using the analyst model through the VRAM scheduler."""
    agent_cfg = MODELS.get("analyst", {"name": "llama3.1:8b"})
    default_model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg
    model = model_override or default_model

    system_prompt = analyst_prompt().format(prompt=prompt)
    async for chunk in scheduled_generate(model, system_prompt, stream=True):
        yield chunk
