from typing import AsyncGenerator
from services.ollama_client import async_generate
from config import MODELS

async def run_researcher_async(prompt: str, model_override: str = None) -> AsyncGenerator[str, None]:
    """
    Researcher Specialist — Handles data-gathering and broader context analysis natively using internal local weights.
    """
    agent_cfg = MODELS.get("researcher", {"name": "qwen2.5:14b"})
    default_model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg
    model = model_override or default_model

    async for chunk in async_generate(prompt, model_name=model):
        yield chunk
