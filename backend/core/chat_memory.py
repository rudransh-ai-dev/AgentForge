"""
Chat Memory — Isolated conversational context for SimpleChat and AgentChat tabs.

Each chat session is fully isolated. Supports persona, agent, and direct modes.
Sessions persist across page reloads and server restarts.
"""
import sqlite3
import json
import time
import uuid

from core.memory_manager import get_connection


def init_chat_memory():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY,
            mode TEXT DEFAULT 'persona',
            selected_agent TEXT DEFAULT '',
            selected_model TEXT DEFAULT '',
            persona_key TEXT DEFAULT '',
            direct_model TEXT DEFAULT '',
            created_at REAL DEFAULT (strftime('%s', 'now')),
            updated_at REAL DEFAULT (strftime('%s', 'now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            agent_id TEXT DEFAULT '',
            model TEXT DEFAULT '',
            persona_key TEXT DEFAULT '',
            timestamp REAL DEFAULT (strftime('%s', 'now')),
            FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_summaries (
            session_id TEXT PRIMARY KEY,
            summary TEXT DEFAULT '',
            key_topics TEXT DEFAULT '[]',
            message_count INTEGER DEFAULT 0,
            updated_at REAL DEFAULT (strftime('%s', 'now')),
            FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
        )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp ON chat_messages(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated ON chat_sessions(updated_at)")

    conn.commit()


def create_session(mode="persona", selected_agent="", selected_model="", persona_key="", direct_model="") -> str:
    session_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        "INSERT INTO chat_sessions (session_id, mode, selected_agent, selected_model, persona_key, direct_model) VALUES (?,?,?,?,?,?)",
        (session_id, mode, selected_agent, selected_model, persona_key, direct_model)
    )
    conn.execute(
        "INSERT INTO chat_summaries (session_id) VALUES (?)",
        (session_id,)
    )
    conn.commit()
    return session_id


def get_session(session_id: str) -> dict:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM chat_sessions WHERE session_id = ?",
        (session_id,)
    ).fetchone()
    if not row:
        return None
    return dict(row)


def list_sessions(limit: int = 20) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT cs.session_id, cs.mode, cs.selected_agent, cs.selected_model, 
                  cs.persona_key, cs.direct_model, cs.created_at, cs.updated_at,
                  COUNT(cm.id) as message_count
           FROM chat_sessions cs
           LEFT JOIN chat_messages cm ON cs.session_id = cm.session_id
           GROUP BY cs.session_id
           ORDER BY cs.updated_at DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    return [dict(row) for row in rows]


def get_messages(session_id: str, limit: int = 100) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY timestamp ASC, id ASC LIMIT ?",
        (session_id, limit)
    ).fetchall()
    return [dict(row) for row in rows]


def add_message(session_id: str, role: str, content: str, agent_id: str = "", model: str = "", persona_key: str = ""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO chat_messages (session_id, role, content, agent_id, model, persona_key) VALUES (?,?,?,?,?,?)",
        (session_id, role, content[:10000], agent_id, model, persona_key)
    )
    conn.execute(
        "UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?",
        (time.time(), session_id)
    )
    conn.execute(
        "UPDATE chat_summaries SET message_count = message_count + 1, updated_at = ? WHERE session_id = ?",
        (time.time(), session_id)
    )
    conn.commit()


def update_session(session_id: str, **kwargs):
    conn = get_connection()
    kwargs["updated_at"] = time.time()
    set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [session_id]
    conn.execute(f"UPDATE chat_sessions SET {set_clause} WHERE session_id = ?", values)
    conn.commit()


def set_summary(session_id: str, summary: str, key_topics: list = None):
    conn = get_connection()
    conn.execute(
        "UPDATE chat_summaries SET summary = ?, key_topics = ?, updated_at = ? WHERE session_id = ?",
        (summary, json.dumps(key_topics or []), time.time(), session_id)
    )
    conn.commit()


def get_summary(session_id: str) -> dict:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM chat_summaries WHERE session_id = ?",
        (session_id,)
    ).fetchone()
    if not row:
        return {"summary": "", "key_topics": [], "message_count": 0}
    result = dict(row)
    result["key_topics"] = json.loads(result.get("key_topics", "[]"))
    return result


def get_context_for_prompt(session_id: str, max_chars: int = 2000) -> str:
    conn = get_connection()
    summary = get_summary(session_id)
    parts = []

    if summary["summary"]:
        parts.append(f"[Previous context]: {summary['summary']}")

    recent = conn.execute(
        "SELECT role, content FROM chat_messages WHERE session_id = ? ORDER BY timestamp DESC, id DESC LIMIT 3",
        (session_id,)
    ).fetchall()
    for msg in reversed(recent):
        parts.append(f"[{msg['role'].upper()}]: {msg['content'][:500]}")

    context = "\n".join(parts)
    return context[:max_chars]


def delete_session(session_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM chat_summaries WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
    conn.commit()


def clear_all_sessions():
    conn = get_connection()
    conn.execute("DELETE FROM chat_messages")
    conn.execute("DELETE FROM chat_summaries")
    conn.execute("DELETE FROM chat_sessions")
    conn.commit()
