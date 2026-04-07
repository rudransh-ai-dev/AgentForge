"""
Centralized Prompt Loader
=========================
Loads system prompts from the shared /prompts/ directory at the project root.
Each agent has ONE file with both pipeline and chat sections.
"""

from functools import lru_cache
from pathlib import Path

PROMPTS_ROOT = Path(__file__).resolve().parents[3] / "prompts"


@lru_cache(maxsize=None)
def _load(agent: str, section: str) -> str:
    """Load a prompt section from the shared prompts directory."""
    path = PROMPTS_ROOT / f"{agent}.md"
    raw = path.read_text(encoding="utf-8")
    marker = f"## {section} Prompt"
    parts = raw.split(marker, 1)
    if len(parts) < 2:
        raise FileNotFoundError(f"Section '{section}' not found in {path}")
    content = parts[1].strip()
    # Stop at the next ## heading to avoid leaking other sections
    next_section = content.find("\n## ")
    if next_section != -1:
        content = content[:next_section].strip()
    return content


# ── Manager ──


def manager_prompt() -> str:
    return _load("manager", "Pipeline")


def manager_prompt_md() -> str:
    return _load("manager", "Pipeline")


def planner_prompt() -> str:
    return _load("manager", "Pipeline")


def manager_chat_prompt() -> str:
    return _load("manager", "Chat")


# ── Coder ──


def coder_prompt() -> str:
    return _load("coder", "Pipeline")


def coder_simple_prompt() -> str:
    return _load("coder", "Pipeline")


def coder_chat_prompt() -> str:
    return _load("coder", "Chat")


def coder_fix_prompt() -> str:
    return _load("coder", "Pipeline")


def coder_revision_prompt() -> str:
    return _load("coder", "Pipeline")


def coder_autofix_prompt() -> str:
    return _load("coder", "Pipeline")


# ── Analyst ──


def analyst_prompt() -> str:
    return _load("analyst", "Pipeline")


def analyst_chat_prompt() -> str:
    return _load("analyst", "Chat")


# ── Critic ──


def critic_prompt() -> str:
    return _load("critic", "Pipeline")


def critic_chat_prompt() -> str:
    return _load("critic", "Chat")


def critic_validation_prompt() -> str:
    return _load("critic", "Pipeline")


def critic_file_review_prompt() -> str:
    return _load("critic", "Pipeline")


def critic_recheck_prompt() -> str:
    return _load("critic", "Pipeline")


# ── Reader / Tool ──


def reader_prompt() -> str:
    return _load("analyst", "Pipeline")


def reader_chat_prompt() -> str:
    return _load("analyst", "Chat")


def tool_prompt() -> str:
    return ""


def qa_chat_prompt() -> str:
    return _load("analyst", "Chat")


def readme_prompt() -> str:
    return ""
