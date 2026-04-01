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
