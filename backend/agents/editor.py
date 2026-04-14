"""
Editor Agent — qwen2.5-coder:14b (Stage 2: Refinement)
Uses scheduled_generate() for safe GPU memory management.
"""

from services.vram_scheduler import scheduled_generate
from config import MODELS


async def run_editor_async(
    original_prompt: str,
    draft_output: str,
    fix_instructions: str = "",
    model_override: str | None = None,
):
    """
    Refine/fix code from the Writer using the Editor model (qwen2.5-coder:14b).
    
    If fix_instructions are provided (from Tester feedback loop), the Editor
    focuses specifically on those fixes rather than a general review.
    """
    agent_cfg = MODELS.get("editor", {"name": "qwen2.5-coder:14b"})
    default_model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg
    model = model_override or default_model

    from core.prompts import editor_prompt
    system_prompt = editor_prompt().format(
        original_prompt=original_prompt,
        draft_output=draft_output,
    )

    # If we have fix instructions from the Tester, prepend them
    if fix_instructions:
        system_prompt = (
            f"CRITICAL FIX INSTRUCTIONS FROM QA TESTER:\n{fix_instructions}\n\n"
            f"Apply these fixes to the code below.\n\n{system_prompt}"
        )

    async for chunk in scheduled_generate(model, system_prompt, stream=True):
        yield chunk
