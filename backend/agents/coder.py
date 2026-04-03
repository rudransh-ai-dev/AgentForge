"""
Coder Agent — VRAM-Scheduled
Uses scheduled_generate() for safe GPU memory management.
"""

from services.vram_scheduler import scheduled_generate
from config import MODELS
from core.prompts import coder_prompt, coder_simple_prompt


_SIMPLE_TASKS = [
    "hello",
    "print",
    "fibonacci",
    "factorial",
    "prime",
    "reverse",
    "sort",
    "sum",
    "average",
    "count",
    "first 10",
    "first 20",
    "first 50",
    "first 100",
]


def _is_simple_task(prompt: str) -> bool:
    """Check if the task is simple enough to skip JSON output."""
    lower = prompt.lower()
    return any(kw in lower for kw in _SIMPLE_TASKS) and len(lower.split()) < 15


async def run_coder_async(prompt: str, model_override: str | None = None):
    """Generate code using the coder model through the VRAM scheduler."""
    agent_cfg = MODELS.get("coder", {"name": "deepseek-coder:6.7b"})
    default_model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg
    model = model_override or default_model

    is_simple = _is_simple_task(prompt)

    if is_simple:
        system_prompt = coder_simple_prompt().format(prompt=prompt)
    else:
        system_prompt = coder_prompt().format(prompt=prompt)
    async for chunk in scheduled_generate(model, system_prompt, stream=True):
        yield chunk
