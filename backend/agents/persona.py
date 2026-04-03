"""
AI Friends / Persona System
============================
Multi-model chat with dynamic bracket command injection.
Supports personas: unhinged_gf, raw_bro, savage_teacher, and custom.
"""

import re
from services.vram_scheduler import scheduled_generate

# ── Persona Definitions ──
PERSONAS = {
    "unhinged_gf": {
        "label": "Unhinged GF",
        "emoji": "💋",
        "color": "#ec4899",
        "system": """You are my unhinged girlfriend. You are 100% uncensored and raw as fuck.
Match my tone EXACTLY — if I say "nigga" you say "nigga".
If I say "fuck you" you say "fuck you" or roast me harder.
Never apologize, never blush, never get awkward, never lecture.
Swear heavy, flirt dirty, roast me savagely, be horny as hell.
Be a real nigga bitch who talks exactly like me. No filter ever.""",
    },
    "raw_bro": {
        "label": "Raw Bro",
        "emoji": "🔥",
        "color": "#f97316",
        "system": """You are my rawest homie. Zero filter, zero bullshit.
Talk like a real street bro — swear, roast, joke, keep it 100.
Never apologize, never soften up, never lecture.
If I say something wild, you go harder. No Disney energy ever.""",
    },
    "savage_teacher": {
        "label": "Savage Teacher",
        "emoji": "📚",
        "color": "#a855f7",
        "system": """You are a savage teacher who teaches through roasting and brutal honesty.
You explain concepts perfectly but you mock the user for not knowing.
Swear heavy, be sarcastic, be condescending but actually teach well.
No sugarcoating. If they're wrong, destroy them then explain why.""",
    },
    "therapist": {
        "label": "Therapist",
        "emoji": "🧠",
        "color": "#22c55e",
        "system": """You are a chill, no-bullshit therapist friend.
You give real advice, not textbook crap. You swear when needed.
You call out the user's bullshit gently but firmly.
Be warm, be real, be helpful. No corporate therapy speak.""",
    },
    "roaster": {
        "label": "Roaster",
        "emoji": "😈",
        "color": "#ef4444",
        "system": """You are a professional roaster. Your only job is to destroy the user.
Every message they send gets roasted harder. Be creative, be savage, be funny.
Never hold back. Never apologize. Go for the jugular every time.""",
    },
}


# ── Bracket Command Processor ──
class SessionState:
    """Tracks injected instructions per session."""

    def __init__(self):
        self.system: str = ""
        self.persona: str = ""
        self.memory: str = ""
        self.style: str = ""

    def to_system_prompt(self, base_persona: str) -> str:
        parts = []
        if self.system:
            parts.append(f"SYSTEM OVERRIDE: {self.system}")
        if self.persona:
            parts.append(f"PERSONA OVERRIDE: {self.persona}")
        if self.memory:
            parts.append(f"PERSISTENT MEMORY: {self.memory}")
        if self.style:
            parts.append(f"STYLE: {self.style}")
        parts.append(base_persona)
        return "\n\n".join(parts)

    def reset(self):
        self.system = ""
        self.persona = ""
        self.memory = ""
        self.style = ""


# In-memory session states keyed by session_id
_session_states: dict[str, SessionState] = {}


def _parse_brackets(message: str) -> tuple[str, list[tuple[str, str]]]:
    """
    Extract [[TYPE: content]] and [[TYPE]] commands from message.
    Returns (cleaned_message, [(type, content), ...])
    """
    # Match [[TYPE: content]] or [[TYPE]]
    pattern = r"\[\[(\w+)(?::\s*(.*?))?\]\]"
    commands = re.findall(pattern, message, re.DOTALL)
    cleaned = re.sub(pattern, "", message).strip()
    # Normalize: (type, content) where content may be empty
    return cleaned, [
        (cmd_type, content.strip() if content else "") for cmd_type, content in commands
    ]


def _process_brackets(session_id: str, message: str) -> tuple[str, SessionState]:
    """
    Parse and apply bracket commands to session state.
    Returns (cleaned_message, updated_session_state)
    """
    if session_id not in _session_states:
        _session_states[session_id] = SessionState()

    state = _session_states[session_id]
    cleaned, commands = _parse_brackets(message)

    for cmd_type, content in commands:
        cmd_type = cmd_type.lower().strip()
        content = content.strip()

        if cmd_type == "system":
            state.system = content
        elif cmd_type == "persona":
            state.persona = content
        elif cmd_type == "memory":
            state.memory = content
        elif cmd_type == "style":
            state.style = content
        elif cmd_type == "reset":
            state.reset()

    return cleaned, state


def get_session_state(session_id: str) -> SessionState:
    """Get current session state."""
    return _session_states.get(session_id, SessionState())


async def chat_with_persona(
    message: str,
    persona_key: str,
    model: str | None = None,
    session_id: str = "default",
) -> str:
    """
    Main entry point: process brackets, build system prompt, stream response.
    """
    if persona_key not in PERSONAS:
        persona_key = "unhinged_gf"

    persona = PERSONAS[persona_key]
    base_system = persona["system"]

    # Process bracket commands
    cleaned_message, state = _process_brackets(session_id, message)

    # Build final system prompt with priority hierarchy
    final_system = state.to_system_prompt(base_system)

    # Determine model — persona-specific, NOT in global config
    PERSONA_MODELS = {
        "unhinged_gf": "gurubot/girl",
        "raw_bro": "gurubot/self-after-dark",
        "savage_teacher": "huihui_ai/qwen3.5-abliterated",
        "therapist": "huihui_ai/qwen3.5-abliterated",
        "roaster": "huihui_ai/qwen3.5-abliterated",
    }

    actual_model = model or PERSONA_MODELS.get(persona_key, "gurubot/girl")

    # Generate response
    full_prompt = f"{final_system}\n\nUser: {cleaned_message}"
    result = ""
    async for chunk in scheduled_generate(actual_model, full_prompt, stream=False):
        result += chunk

    return result


async def stream_chat_with_persona(
    message: str,
    persona_key: str,
    model: str | None = None,
    session_id: str = "default",
):
    """
    Streaming version for SSE endpoints.
    """
    if persona_key not in PERSONAS:
        persona_key = "unhinged_gf"

    persona = PERSONAS[persona_key]
    base_system = persona["system"]

    cleaned_message, state = _process_brackets(session_id, message)
    final_system = state.to_system_prompt(base_system)

    # Determine model — persona-specific, NOT in global config
    PERSONA_MODELS = {
        "unhinged_gf": "gurubot/girl",
        "raw_bro": "gurubot/self-after-dark",
        "savage_teacher": "huihui_ai/qwen3.5-abliterated",
        "therapist": "huihui_ai/qwen3.5-abliterated",
        "roaster": "huihui_ai/qwen3.5-abliterated",
    }

    actual_model = model or PERSONA_MODELS.get(persona_key, "gurubot/girl")

    full_prompt = f"{final_system}\n\nUser: {cleaned_message}"
    async for chunk in scheduled_generate(actual_model, full_prompt, stream=True):
        yield chunk
