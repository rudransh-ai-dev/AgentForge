"""
Context Compression — Summarize conversation context to prevent overflow.

After each pipeline execution, the context manager summarizes the
previous steps and keeps only relevant state. This prevents the
context window from overflowing in multi-step workflows.
"""
from services.vram_scheduler import scheduled_generate_sync
from services.sanitizer import strip_prompt_leakage
from config import MODELS


async def compress_context(history: list[dict], max_summary_length: int = 500) -> str:
    """
    Summarize a conversation history into a compact context string.
    Uses the manager model (lightweight) for summarization.

    Args:
        history: List of conversation turns [{role, content, agent, ...}]
        max_summary_length: Maximum characters for the summary

    Returns:
        Compressed context summary string
    """
    if not history:
        return ""

    # Build a condensed version of the history
    turns_text = ""
    for turn in history[-10:]:  # Last 10 turns max
        role = turn.get("role", "unknown")
        content = turn.get("content", "")[:300]
        agent = turn.get("agent", "")
        prefix = f"[{role}" + (f"/{agent}" if agent else "") + "]"
        turns_text += f"{prefix}: {content}\n"

    if len(turns_text) < 200:
        # Too short to compress, just return as-is
        return turns_text.strip()

    prompt = f"""Summarize this conversation into a compact, informative context paragraph.
Keep key facts, decisions, code topics, and user preferences.
Remove greetings, filler, and redundant information.
Output ONLY the summary, no labels or formatting.

CONVERSATION:
{turns_text}

SUMMARY:"""

    try:
        mgr_cfg = MODELS["manager"]
        mgr_model = mgr_cfg["name"] if isinstance(mgr_cfg, dict) else mgr_cfg
        result = await scheduled_generate_sync(mgr_model, prompt)
        cleaned = strip_prompt_leakage(result)
        return cleaned[:max_summary_length].strip()
    except Exception:
        # Fallback: simple truncation
        return turns_text[:max_summary_length].strip()


def build_context_window(
    session_context: str,
    current_prompt: str,
    previous_output: str = "",
    max_total_chars: int = 4000,
) -> str:
    """
    Build the full context window for a model prompt.
    Combines session context with current task info.

    Priority order:
    1. Current prompt (always included in full)
    2. Previous step output (if multi-step pipeline)
    3. Session context (compressed history)
    """
    parts = []

    # Session context
    if session_context:
        budget = max_total_chars - len(current_prompt) - 200
        if budget > 200:
            parts.append(f"[Context from previous conversation]:\n{session_context[:budget]}")

    # Previous step output (for multi-step pipelines)
    if previous_output:
        budget = max_total_chars - len(current_prompt) - len("\n".join(parts)) - 200
        if budget > 200:
            parts.append(f"[Previous step output]:\n{previous_output[:budget]}")

    if parts:
        return "\n\n".join(parts) + f"\n\n[Current Task]:\n{current_prompt}"
    return current_prompt


AGENT_CONTEXT_BUDGETS = {
    "manager": 2600,
    "writer": 5200,
    "coder": 5200,
    "editor": 5200,
    "tester": 4400,
    "critic": 4400,
    "researcher": 5200,
    "analyst": 3600,
    "tool": 3000,
    "executor": 2200,
}


def build_agent_context_window(
    agent: str,
    current_prompt: str,
    *,
    spec_block: str = "",
    retrieval_block: str = "",
    session_context: str = "",
    previous_output: str = "",
) -> str:
    """
    Build a selective context window for one agent.

    V5 avoids sending full history to every agent. Each role gets the current
    task plus only the context it can use: specs for everyone, retrieval for
    reasoning/code roles, previous output for refinement/validation roles, and
    a small session summary for continuity.
    """
    agent = (agent or "analyst").lower()
    max_total = AGENT_CONTEXT_BUDGETS.get(agent, 3600)
    parts = []

    if spec_block:
        parts.append(spec_block[:1000])

    if retrieval_block and agent in {"manager", "writer", "coder", "editor", "researcher", "analyst", "critic", "tester"}:
        parts.append(retrieval_block[:1800])

    if previous_output and agent in {"editor", "tester", "critic", "tool", "executor"}:
        budget = 1800 if agent in {"editor", "tester", "critic"} else 1200
        parts.append(f"[Previous step output]\n{previous_output[:budget]}")

    if session_context and agent in {"manager", "analyst", "researcher", "writer", "coder"}:
        parts.append(f"[Session summary]\n{session_context[:900]}")

    header = "\n\n".join(part for part in parts if part)
    task = f"[Current Task]\n{current_prompt}"
    if not header:
        return current_prompt

    remaining = max_total - len(task) - 2
    if remaining <= 0:
        return task[:max_total]
    return f"{header[:remaining]}\n\n{task}"
