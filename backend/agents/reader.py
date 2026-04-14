import os
import json
from services.vram_scheduler import scheduled_generate
from config import MODELS
from core.prompts import reader_prompt

WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")


async def run_reader_async(prompt: str, model_override: str | None = None):
    """
    Search and Read Files from the Project Workspace to answer context questions.
    """
    agent_cfg = MODELS.get("analyst", {"name": "llama3.1:8b"})
    model = model_override or agent_cfg["name"]

    files_info = []
    for root, _, filenames in os.walk(WORKSPACE_DIR):
        for fn in filenames:
            if fn.startswith(".") or "__pycache__" in root:
                continue
            rel = os.path.relpath(os.path.join(root, fn), WORKSPACE_DIR)
            files_info.append(rel)

    file_manifest = json.dumps(files_info, indent=2)
    system_prompt = reader_prompt().format(file_manifest=file_manifest, prompt=prompt)
    async for chunk in scheduled_generate(model, system_prompt, stream=True):
        yield chunk
