from services.ollama_client import async_generate_stream
from config import MODELS

async def run_critic_async(prompt: str):
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
    async for chunk in async_generate_stream(MODELS["critic"], system_prompt):
        yield chunk
