from services.ollama_client import async_generate_stream
from config import MODELS

async def run_coder_async(prompt: str):
    system_prompt = f"""You are a code generation agent in a multi-agent system.

RULES:
- Write clean, production-ready, working code
- Include ALL necessary imports
- Use clear variable names and add minimal comments
- Output complete files, never partial snippets
- Do NOT say "As an AI" or explain yourself
- Do NOT repeat the task instructions back
- Do NOT add disclaimers or alternatives unless asked
- If multiple files are needed, separate with clear headers

WHEN WRITING CODE:
- Always include error handling
- Use type hints for Python
- Follow language-standard conventions
- Make it runnable without modification

Task:
{prompt}
"""
    async for chunk in async_generate_stream(MODELS["coder"], system_prompt):
        yield chunk
