"""
Writer Agent — qwen2.5-coder:14b (Stage 1: First Draft)
Uses scheduled_generate() for safe GPU memory management.
"""

from services.vram_scheduler import scheduled_generate
from config import MODELS


async def run_writer_async(prompt: str, model_override: str | None = None):
    """Generate first-draft code using the Writer model (qwen2.5-coder:14b)."""
    agent_cfg = MODELS.get("writer", {"name": "qwen2.5-coder:14b"})
    default_model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg
    model = model_override or default_model

    from core.prompts import writer_prompt
    system_prompt = writer_prompt().format(prompt=prompt)

    async for chunk in scheduled_generate(model, system_prompt, stream=True):
        yield chunk
