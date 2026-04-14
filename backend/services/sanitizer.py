"""
Output Sanitizer: Production-grade post-processing for LLM outputs.

Handles:
- Prompt leakage removal (small models re-echo instructions)
- JSON extraction from noisy text
- Code block extraction and cleanup
- Schema validation
- Markdown/formatting noise stripping
"""

import re
import json


# ── Patterns that indicate prompt leakage ──

LEAKAGE_PATTERNS = [
    r"(?:^|\n)\s*(?:GENERATE|TASK|ROLE|OUTPUT FORMAT|RULES|SCHEMA|CRITICAL RULES|SELF-CHECK|FORMAT ENFORCEMENT):.*",
    r"(?:^|\n)\s*(?:You are a|As an AI|I am a|I'm an AI|As a language model).*",
    r"(?:^|\n)\s*(?:Here (?:is|are) (?:the|a|your)|Below (?:is|are)|Following (?:is|are) the).*?:\s*$",
    r"(?:^|\n)\s*\d+\.\s*Prompt Engineering Agent inside.*",
    r"(?:^|\n)\s*OUTPUT FORMAT \(STRICT JSON ARRAY\):.*",
]


def strip_prompt_leakage(text: str) -> str:
    """Remove lines where the model re-echoed its own instructions."""
    for pattern in LEAKAGE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.MULTILINE | re.IGNORECASE)
    # Remove multiple blank lines left behind
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_json_object(text: str) -> dict | None:
    """Extract the first valid JSON object {} from noisy text."""
    # Try the full text first
    text = strip_prompt_leakage(text)
    
    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: Find {...} block
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def extract_json_array(text: str) -> list | None:
    """Extract the first valid JSON array [] from noisy text."""
    text = strip_prompt_leakage(text)

    # Strategy 1: Direct parse
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: Find [...] block
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(0))
            if isinstance(result, list):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def extract_code_blocks(text: str) -> list[dict]:
    """
    Extract all code blocks from markdown-formatted text.
    Returns list of {"language": str, "code": str, "filename": str|None}
    """
    blocks = []
    
    # Pattern: ```language\n...code...\n```
    pattern = r'```(\w*)\n(.*?)```'
    matches = re.finditer(pattern, text, re.DOTALL)
    
    for match in matches:
        lang = match.group(1).strip() or "text"
        code = match.group(2).strip()
        
        # Try to detect filename from comment or context before the block
        filename = None
        pre_text = text[:match.start()].strip().split('\n')
        if pre_text:
            last_line = pre_text[-1].strip()
            # Look for patterns like "# filename.py" or "File: main.py"
            fn_match = re.search(r'(?:file[:\s]*|#\s*)([\w./-]+\.\w+)', last_line, re.IGNORECASE)
            if fn_match:
                filename = fn_match.group(1)
        
        # Infer filename from language if not found
        if not filename:
            ext_map = {"python": ".py", "javascript": ".js", "java": ".java",
                       "html": ".html", "css": ".css", "typescript": ".ts",
                       "bash": ".sh", "shell": ".sh", "sql": ".sql",
                       "json": ".json", "yaml": ".yml", "toml": ".toml"}
            ext = ext_map.get(lang.lower(), "")
            if ext:
                filename = f"file_{len(blocks) + 1}{ext}"
        
        blocks.append({"language": lang, "code": code, "filename": filename})
    
    return blocks


def clean_agent_output(text: str, expect_json: bool = False) -> str:
    """
    Master cleaner: strips leakage, normalizes whitespace.
    If expect_json=True, attempts to extract and return clean JSON string.
    """
    cleaned = strip_prompt_leakage(text)
    
    if expect_json:
        # Try object first, then array
        obj = extract_json_object(cleaned)
        if obj:
            return json.dumps(obj, indent=2)
        arr = extract_json_array(cleaned)
        if arr:
            return json.dumps(arr, indent=2)
    
    return cleaned


def validate_schema(data: dict, required_keys: list[str]) -> tuple[bool, list[str]]:
    """
    Validate that a dict has all required keys.
    Returns (is_valid, list_of_missing_keys).
    """
    missing = [k for k in required_keys if k not in data]
    return (len(missing) == 0, missing)


def sanitize_file_content(content: str) -> str:
    """
    Clean file content that came from LLM output.
    Removes markdown artifacts, trailing commentary, etc.
    """
    # Remove markdown code block wrappers if the entire content is wrapped
    content = re.sub(r'^```\w*\n', '', content)
    content = re.sub(r'\n```\s*$', '', content)
    
    # Remove trailing LLM commentary after code
    lines = content.split('\n')
    clean_lines = []
    trailing_comment = False
    for line in reversed(lines):
        stripped = line.strip()
        # If we're scanning from the bottom and hit pure commentary, skip it
        if not trailing_comment and stripped and not stripped.startswith('#') and not stripped.startswith('//'):
            trailing_comment = True
        if trailing_comment:
            clean_lines.insert(0, line)
        elif stripped.startswith('#') or stripped.startswith('//') or not stripped:
            clean_lines.insert(0, line)
            trailing_comment = True
        # Skip lines that look like LLM commentary (no code characteristics)
    
    return '\n'.join(clean_lines).strip() + '\n'

async def auto_fix_json(broken_text: str, error_msg: str = "") -> dict | list | None:
    """
    Critic Auto-validator: Uses the Critic agent to fix severely broken JSON 
    that regex and heuristics couldn't extract.
    """
    from services.ollama_client import async_generate
    from config import MODELS
    
    prompt = f"""You are a JSON repair agent.
Your ONLY job is to take broken text that was supposed to be JSON, and output valid JSON.
DO NOT output any explanations, markdown, or chat. Output ONLY the raw JSON.

Error encountered: {error_msg}

BROKEN TEXT:
{broken_text}
"""
    try:
        critic_cfg = MODELS.get("critic", {"name": "llama3.1:8b"})
        critic_model = critic_cfg["name"] if isinstance(critic_cfg, dict) else critic_cfg
        response = await async_generate(critic_model, prompt)
        cleaned = strip_prompt_leakage(response)
        
        # Try object
        obj = extract_json_object(cleaned)
        if obj: return obj
        
        # Try array
        arr = extract_json_array(cleaned)
        if arr: return arr
        
        return None
    except Exception:
        return None
