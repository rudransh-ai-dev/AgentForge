"""
Session Memory — Persistent state across conversation turns.

Tracks conversation history, last active agent/model, and context summaries.
Sessions are stored in SQLite alongside the existing memory.db.
"""
import sqlite3
import json
import os
import time
import uuid

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_sessions():
    """Initialize session tables."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            history TEXT DEFAULT '[]',
            last_agent TEXT DEFAULT '',
            last_model TEXT DEFAULT '',
            context_summary TEXT DEFAULT '',
            task_queue TEXT DEFAULT '[]',
            active_mode TEXT DEFAULT 'direct',
            created_at REAL DEFAULT (strftime('%s', 'now')),
            updated_at REAL DEFAULT (strftime('%s', 'now'))
        )
    """)
    conn.commit()
    conn.close()


def create_session() -> str:
    """Create a new session and return its ID."""
    session_id = str(uuid.uuid4())
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO sessions (session_id) VALUES (?)",
            (session_id,)
        )
        conn.commit()
    finally:
        conn.close()
    return session_id


def get_session(session_id: str) -> dict:
    """Retrieve a session by ID."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "session_id": row["session_id"],
            "history": json.loads(row["history"]),
            "last_agent": row["last_agent"],
            "last_model": row["last_model"],
            "context_summary": row["context_summary"],
            "task_queue": json.loads(row["task_queue"]),
            "active_mode": row["active_mode"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    finally:
        conn.close()


def update_session(session_id: str, **kwargs):
    """Update session fields."""
    conn = _get_conn()
    try:
        session = get_session(session_id)
        if not session:
            return

        # Handle JSON fields
        if "history" in kwargs:
            kwargs["history"] = json.dumps(kwargs["history"])
        if "task_queue" in kwargs:
            kwargs["task_queue"] = json.dumps(kwargs["task_queue"])

        kwargs["updated_at"] = time.time()

        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [session_id]

        conn.execute(
            f"UPDATE sessions SET {set_clause} WHERE session_id = ?",
            values
        )
        conn.commit()
    finally:
        conn.close()


def add_turn(session_id: str, role: str, content: str, agent: str = "", model: str = ""):
    """Add a conversation turn to the session history."""
    session = get_session(session_id)
    if not session:
        return

    history = session["history"]
    history.append({
        "role": role,  # "user" or "assistant"
        "content": content[:5000],
        "agent": agent,
        "model": model,
        "timestamp": time.time(),
    })

    # Keep last 20 turns in active history
    if len(history) > 20:
        history = history[-20:]

    update_session(
        session_id,
        history=history,
        last_agent=agent or session["last_agent"],
        last_model=model or session["last_model"],
    )


def get_context_for_prompt(session_id: str, max_chars: int = 2000) -> str:
    """
    Build context string from session for injection into prompts.
    Uses compressed summary + recent turns.
    """
    session = get_session(session_id)
    if not session:
        return ""

    parts = []

    # Add compressed summary if available
    if session["context_summary"]:
        parts.append(f"[Previous context]: {session['context_summary']}")

    # Add last 3 recent turns
    recent = session["history"][-3:]
    for turn in recent:
        role = turn["role"].upper()
        content = turn["content"][:500]
        parts.append(f"[{role}]: {content}")

    context = "\n".join(parts)
    return context[:max_chars]


def list_sessions(limit: int = 20) -> list:
    """List recent sessions."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT session_id, last_agent, active_mode, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# Initialize on import
init_sessions()
