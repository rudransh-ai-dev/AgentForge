import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_prompt_versions():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompt_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            prompt_text TEXT NOT NULL,
            prompt_type TEXT DEFAULT 'chat',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            note TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()


def save_version(agent_id, prompt_text, prompt_type="chat", note=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COALESCE(MAX(version), 0) + 1 FROM prompt_versions WHERE agent_id = ? AND prompt_type = ?",
        (agent_id, prompt_type),
    )
    next_version = cursor.fetchone()[0]
    cursor.execute(
        "INSERT INTO prompt_versions (agent_id, version, prompt_text, prompt_type, note) VALUES (?, ?, ?, ?, ?)",
        (agent_id, next_version, prompt_text, prompt_type, note),
    )
    conn.commit()
    conn.close()
    return next_version


def get_versions(agent_id, prompt_type="chat"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT version, prompt_text, created_at, note
           FROM prompt_versions
           WHERE agent_id = ? AND prompt_type = ?
           ORDER BY version ASC""",
        (agent_id, prompt_type),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "version": r["version"],
            "prompt_text": r["prompt_text"],
            "created_at": r["created_at"],
            "note": r["note"],
        }
        for r in rows
    ]


def get_version(agent_id, version, prompt_type="chat"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT version, prompt_text, created_at, note
           FROM prompt_versions
           WHERE agent_id = ? AND version = ? AND prompt_type = ?""",
        (agent_id, version, prompt_type),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "version": row["version"],
            "prompt_text": row["prompt_text"],
            "created_at": row["created_at"],
            "note": row["note"],
        }
    return None


def get_diff(agent_id, from_version, to_version, prompt_type="chat"):
    import difflib
    v1 = get_version(agent_id, from_version, prompt_type)
    v2 = get_version(agent_id, to_version, prompt_type)
    if not v1 or not v2:
        return None

    v1_lines = v1["prompt_text"].splitlines(keepends=True)
    v2_lines = v2["prompt_text"].splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        v1_lines, v2_lines,
        fromfile=f"v{from_version}",
        tofile=f"v{to_version}",
        lineterm="",
    ))

    return {
        "from_version": from_version,
        "to_version": to_version,
        "diff": "".join(diff),
    }


def rollback_to(agent_id, version, prompt_type="chat"):
    target = get_version(agent_id, version, prompt_type)
    if not target:
        return None
    new_version = save_version(
        agent_id,
        target["prompt_text"],
        prompt_type,
        f"Rollback to v{version}",
    )
    return new_version


init_prompt_versions()
