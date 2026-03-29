import sqlite3
import json
import os
import time

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_memory():
    """Initialize the memory database schema."""
    conn = _get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            prompt TEXT,
            route TEXT,
            result TEXT,
            project_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at REAL DEFAULT (strftime('%s', 'now')),
            latency_ms INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS fixes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            project_id TEXT,
            error TEXT,
            fix_code TEXT,
            attempt INTEGER,
            success INTEGER DEFAULT 0,
            created_at REAL DEFAULT (strftime('%s', 'now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_hash TEXT UNIQUE,
            prompt TEXT,
            route TEXT,
            success_count INTEGER DEFAULT 0,
            fail_count INTEGER DEFAULT 0,
            last_used REAL DEFAULT (strftime('%s', 'now'))
        )
    """)

    conn.commit()
    conn.close()


def store_run(run_id: str, prompt: str, route: str, result: str,
              project_id: str = None, status: str = "success", latency_ms: int = 0):
    """Store a completed run in memory."""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO runs (run_id, prompt, route, result, project_id, status, latency_ms) VALUES (?,?,?,?,?,?,?)",
            (run_id, prompt, route, result[:5000], project_id, status, latency_ms)
        )
        conn.commit()
    finally:
        conn.close()


def store_fix(run_id: str, project_id: str, error: str, fix_code: str,
              attempt: int, success: bool):
    """Store a fix attempt for learning."""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO fixes (run_id, project_id, error, fix_code, attempt, success) VALUES (?,?,?,?,?,?)",
            (run_id, project_id, error[:2000], fix_code[:5000], attempt, int(success))
        )
        conn.commit()
    finally:
        conn.close()


def update_pattern(prompt: str, route: str, success: bool):
    """Track routing patterns for learning."""
    import hashlib
    prompt_hash = hashlib.md5(prompt.lower().strip().encode()).hexdigest()
    conn = _get_conn()
    try:
        existing = conn.execute(
            "SELECT * FROM patterns WHERE prompt_hash = ?", (prompt_hash,)
        ).fetchone()

        if existing:
            if success:
                conn.execute(
                    "UPDATE patterns SET success_count = success_count + 1, last_used = ? WHERE prompt_hash = ?",
                    (time.time(), prompt_hash)
                )
            else:
                conn.execute(
                    "UPDATE patterns SET fail_count = fail_count + 1, last_used = ? WHERE prompt_hash = ?",
                    (time.time(), prompt_hash)
                )
        else:
            conn.execute(
                "INSERT INTO patterns (prompt_hash, prompt, route, success_count, fail_count) VALUES (?,?,?,?,?)",
                (prompt_hash, prompt[:500], route, int(success), int(not success))
            )
        conn.commit()
    finally:
        conn.close()


def get_similar_fixes(error_snippet: str, limit: int = 3):
    """Find past fixes for similar errors to guide the coder."""
    conn = _get_conn()
    try:
        # Simple keyword search — a real system would use embeddings
        keywords = [w for w in error_snippet.split() if len(w) > 4][:5]
        if not keywords:
            return []

        conditions = " OR ".join(["error LIKE ?" for _ in keywords])
        params = [f"%{kw}%" for kw in keywords]

        rows = conn.execute(
            f"SELECT error, fix_code FROM fixes WHERE success = 1 AND ({conditions}) ORDER BY created_at DESC LIMIT ?",
            params + [limit]
        ).fetchall()

        return [{"error": row["error"], "fix": row["fix_code"][:1000]} for row in rows]
    finally:
        conn.close()


def get_run_history(limit: int = 20):
    """Get recent run history."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT run_id, prompt, route, status, project_id, latency_ms, created_at FROM runs ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_stats():
    """Get aggregate system stats."""
    conn = _get_conn()
    try:
        total_runs = conn.execute("SELECT COUNT(*) as c FROM runs").fetchone()["c"]
        successful = conn.execute("SELECT COUNT(*) as c FROM runs WHERE status='success'").fetchone()["c"]
        total_fixes = conn.execute("SELECT COUNT(*) as c FROM fixes").fetchone()["c"]
        successful_fixes = conn.execute("SELECT COUNT(*) as c FROM fixes WHERE success=1").fetchone()["c"]
        return {
            "total_runs": total_runs,
            "successful_runs": successful,
            "success_rate": round(successful / max(total_runs, 1) * 100, 1),
            "total_fix_attempts": total_fixes,
            "successful_fixes": successful_fixes,
            "fix_rate": round(successful_fixes / max(total_fixes, 1) * 100, 1),
        }
    finally:
        conn.close()


# Initialize on import
init_memory()
