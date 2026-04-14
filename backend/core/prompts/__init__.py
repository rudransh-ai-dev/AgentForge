"""
Centralized Prompt Loader (v4.1)
=================================
All prompt templates live in the root /prompts/ directory.
This module is the ONLY loader. No other directory contains prompts.

v4.1: Supports both sectioned prompts (## Pipeline Prompt / ## Chat Prompt)
      and flat prompts (entire file = one prompt). Falls back gracefully.
"""

from functools import lru_cache
from pathlib import Path

PROMPTS_ROOT = Path(__file__).resolve().parents[3] / "prompts"


class SafePromptTemplate(str):
    """
    str subclass whose .format() treats literal `{`/`}` as data, not field
    delimiters. Only the explicit kwargs passed in are substituted, so JSON
    examples embedded in prompt markdown don't blow up with KeyError.
    """
    def format(self, *args, **kwargs):  # type: ignore[override]
        escaped = str.replace(self, "{", "{{").replace("}", "}}")
        for key in kwargs:
            escaped = escaped.replace("{{" + key + "}}", "{" + key + "}")
        return str.format(escaped, **kwargs)


@lru_cache(maxsize=None)
def _load(agent: str, section: str) -> SafePromptTemplate:
    """Load a prompt section from the shared prompts directory.
    
    If the file contains a `## {section} Prompt` marker, extract that section.
    Otherwise, return the entire file content (supports flat prompt format).
    """
    path = PROMPTS_ROOT / f"{agent}.md"
    raw = path.read_text(encoding="utf-8")
    marker = f"## {section} Prompt"
    
    # Try sectioned format first
    if marker in raw:
        parts = raw.split(marker, 1)
        content = parts[1].strip()
        # Stop at the next ## heading to avoid leaking other sections
        next_section = content.find("\n## ")
        if next_section != -1:
            content = content[:next_section].strip()
        return SafePromptTemplate(content)
    
    # Flat format: return the whole file, skipping the # ROLE header line
    lines = raw.strip().split("\n")
    # Skip the first line if it's a markdown heading (# ROLE: ...)
    start = 0
    if lines and lines[0].startswith("# "):
        start = 1
    content = "\n".join(lines[start:]).strip()
    return SafePromptTemplate(content)


@lru_cache(maxsize=None)
def _load_raw(name: str) -> str:
    """Load a raw prompt template from root /prompts/ directory."""
    return (PROMPTS_ROOT / f"{name}.md").read_text(encoding="utf-8")


# ── Manager ──

def manager_prompt() -> str:
    return _load("manager", "Pipeline")

def manager_prompt_md() -> str:
    return _load("manager", "Pipeline")

def planner_prompt() -> str:
    return _load("manager", "Pipeline")

def manager_chat_prompt() -> str:
    return _load("manager", "Chat")


# ── Writer (Stage 1: First Draft) ──

def writer_prompt() -> str:
    return _load("writer", "Pipeline")


# ── Editor (Stage 2: Refinement) ──

def editor_prompt() -> str:
    return _load("editor", "Pipeline")


# ── Tester (Stage 3: QA Validation) ──

def tester_prompt() -> str:
    return _load("tester", "Pipeline")


# ── Coder (legacy alias — same pipeline as Writer) ──

def coder_prompt() -> str:
    return _load("coder", "Pipeline")

def coder_chat_prompt() -> str:
    return _load("coder", "Chat")

def coder_simple_prompt() -> str:
    """Simple tasks use the same coder prompt — the model scales complexity."""
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

def critic_file_review_prompt() -> str:
    return _load_raw("critic_file_review")

def critic_recheck_prompt() -> str:
    return _load_raw("critic_recheck")


# ── Researcher ──

def researcher_prompt() -> str:
    return _load("researcher", "Pipeline")

def researcher_chat_prompt() -> str:
    return _load("researcher", "Chat")


# ── QA (alias for tester chat) ──

def qa_chat_prompt() -> str:
    return _load("tester", "Pipeline")


# ── Reader ──

def reader_prompt() -> str:
    """Reader uses analyst prompt as its base."""
    return _load("analyst", "Pipeline")

def reader_chat_prompt() -> str:
    try:
        return _load("analyst", "Chat")
    except FileNotFoundError:
        return "You are a code reader. Analyze the codebase and answer questions about it."


# ── Tool ──

def tool_prompt() -> str:
    return _load_raw("tool")


# ── Coder Fix / Revision / Autofix ──

def coder_fix_prompt() -> str:
    return _load_raw("coder_fix")

def coder_revision_prompt() -> str:
    return _load_raw("coder_revision")

def coder_autofix_prompt() -> str:
    return _load_raw("coder_autofix")


# ── Critic Validation ──

def critic_validation_prompt() -> str:
    return _load_raw("critic_validation")


# ── README ──

def readme_prompt() -> str:
    return _load_raw("readme")
