from typing import AsyncGenerator
from services.vram_scheduler import scheduled_generate
from config import MODELS

async def run_researcher_async(prompt: str, model_override: str = None) -> AsyncGenerator[str, None]:
    """
    Researcher Specialist — Handles data-gathering and broader context analysis natively using internal local weights.
    """
    agent_cfg = MODELS.get("researcher", {"name": "qwen2.5:14b"})
    default_model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg
    model = model_override or default_model

    from core.prompts import researcher_prompt
    system_prompt = researcher_prompt().format(prompt=prompt)

    async for chunk in scheduled_generate(model, system_prompt, stream=True):
        yield chunk
