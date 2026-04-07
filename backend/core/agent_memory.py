"""
Agent Memory — Per-agent knowledge, patterns, and error fixes.

Each agent has its own isolated memory. Coder's fixes don't pollute Analyst's patterns.
"""
import hashlib
import time


def init_agent_memory():
    from core.memory_manager import get_connection
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS agent_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            fact TEXT NOT NULL,
            context TEXT DEFAULT '',
            source_run_id TEXT DEFAULT '',
            confidence REAL DEFAULT 0.5,
            created_at REAL DEFAULT (strftime('%s', 'now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS agent_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            prompt_hash TEXT NOT NULL,
            prompt TEXT DEFAULT '',
            success_count INTEGER DEFAULT 0,
            fail_count INTEGER DEFAULT 0,
            last_used REAL DEFAULT (strftime('%s', 'now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS agent_fixes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            error_snippet TEXT NOT NULL,
            fix_code TEXT NOT NULL,
            success INTEGER DEFAULT 0,
            attempt_count INTEGER DEFAULT 1,
            created_at REAL DEFAULT (strftime('%s', 'now'))
        )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_agent_knowledge_agent ON agent_knowledge(agent_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_agent_patterns_agent_hash ON agent_patterns(agent_id, prompt_hash)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_agent_fixes_agent ON agent_fixes(agent_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_agent_fixes_success ON agent_fixes(agent_id, success)")

    conn.commit()


def store_knowledge(agent_id: str, fact: str, context: str = "", source_run_id: str = "", confidence: float = 0.5):
    conn = get_connection()
    conn.execute(
        "INSERT INTO agent_knowledge (agent_id, fact, context, source_run_id, confidence) VALUES (?,?,?,?,?)",
        (agent_id, fact[:5000], context[:2000], source_run_id, confidence)
    )
    conn.commit()


def get_knowledge(agent_id: str, limit: int = 20) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM agent_knowledge WHERE agent_id = ? ORDER BY confidence DESC, created_at DESC LIMIT ?",
        (agent_id, limit)
    ).fetchall()
    return [dict(row) for row in rows]


def delete_knowledge(agent_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM agent_knowledge WHERE agent_id = ?", (agent_id,))
    conn.commit()


def update_pattern(agent_id: str, prompt: str, success: bool):
    prompt_hash = hashlib.md5(prompt.lower().strip().encode()).hexdigest()
    conn = get_connection()

    existing = conn.execute(
        "SELECT * FROM agent_patterns WHERE agent_id = ? AND prompt_hash = ?",
        (agent_id, prompt_hash)
    ).fetchone()

    if existing:
        if success:
            conn.execute(
                "UPDATE agent_patterns SET success_count = success_count + 1, last_used = ? WHERE agent_id = ? AND prompt_hash = ?",
                (time.time(), agent_id, prompt_hash)
            )
        else:
            conn.execute(
                "UPDATE agent_patterns SET fail_count = fail_count + 1, last_used = ? WHERE agent_id = ? AND prompt_hash = ?",
                (time.time(), agent_id, prompt_hash)
            )
    else:
        conn.execute(
            "INSERT INTO agent_patterns (agent_id, prompt_hash, prompt, success_count, fail_count) VALUES (?,?,?,?,?)",
            (agent_id, prompt_hash, prompt[:500], int(success), int(not success))
        )
    conn.commit()


def get_patterns(agent_id: str) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM agent_patterns WHERE agent_id = ? ORDER BY last_used DESC",
        (agent_id,)
    ).fetchall()
    return [dict(row) for row in rows]


def store_fix(agent_id: str, error_snippet: str, fix_code: str, success: bool):
    conn = get_connection()

    existing = conn.execute(
        "SELECT id, attempt_count FROM agent_fixes WHERE agent_id = ? AND error_snippet LIKE ? AND success = 1",
        (agent_id, f"%{error_snippet[:100]}%")
    ).fetchone()

    if existing and not success:
        conn.execute(
            "UPDATE agent_fixes SET attempt_count = attempt_count + 1 WHERE id = ?",
            (existing["id"],)
        )
    else:
        conn.execute(
            "INSERT INTO agent_fixes (agent_id, error_snippet, fix_code, success, attempt_count) VALUES (?,?,?,?,?)",
            (agent_id, error_snippet[:2000], fix_code[:5000], int(success), 1)
        )
    conn.commit()


def get_similar_fixes(agent_id: str, error_snippet: str, limit: int = 3) -> list:
    keywords = [w for w in error_snippet.split() if len(w) > 4][:5]
    if not keywords:
        return []

    conditions = " OR ".join(["error_snippet LIKE ?" for _ in keywords])
    params = [f"%{kw}%" for kw in keywords]

    conn = get_connection()
    rows = conn.execute(
        f"SELECT error_snippet, fix_code FROM agent_fixes WHERE agent_id = ? AND success = 1 AND ({conditions}) ORDER BY created_at DESC LIMIT ?",
        [agent_id] + params + [limit]
    ).fetchall()

    return [{"error": row["error_snippet"], "fix": row["fix_code"][:1000]} for row in rows]


def get_fixes(agent_id: str, limit: int = 20) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM agent_fixes WHERE agent_id = ? ORDER BY created_at DESC LIMIT ?",
        (agent_id, limit)
    ).fetchall()
    return [dict(row) for row in rows]


def delete_fixes(agent_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM agent_fixes WHERE agent_id = ?", (agent_id,))
    conn.commit()


def reset_agent_memory(agent_id: str):
    """Wipe all memory for a specific agent."""
    conn = get_connection()
    conn.execute("DELETE FROM agent_knowledge WHERE agent_id = ?", (agent_id,))
    conn.execute("DELETE FROM agent_patterns WHERE agent_id = ?", (agent_id,))
    conn.execute("DELETE FROM agent_fixes WHERE agent_id = ?", (agent_id,))
    conn.commit()
