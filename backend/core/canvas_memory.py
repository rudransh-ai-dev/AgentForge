"""
Canvas Memory — Pipeline run and step-by-step execution tracking.

Each pipeline run is tracked with individual step details for debugging and replay.
"""
import time
from core.memory_manager import get_connection


def init_canvas_memory():
    from core.memory_manager import get_connection
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id TEXT PRIMARY KEY,
            prompt TEXT NOT NULL,
            mode TEXT DEFAULT 'auto',
            allow_heavy INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            total_latency_ms INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            created_at REAL DEFAULT (strftime('%s', 'now')),
            completed_at REAL DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            step_order INTEGER NOT NULL,
            node_id TEXT NOT NULL,
            input TEXT DEFAULT '',
            output TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            latency_ms INTEGER DEFAULT 0,
            tokens INTEGER DEFAULT 0,
            model_used TEXT DEFAULT '',
            error TEXT DEFAULT '',
            created_at REAL DEFAULT (strftime('%s', 'now')),
            FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_hash TEXT UNIQUE NOT NULL,
            prompt TEXT DEFAULT '',
            route TEXT DEFAULT '',
            success_count INTEGER DEFAULT 0,
            fail_count INTEGER DEFAULT 0,
            last_used REAL DEFAULT (strftime('%s', 'now'))
        )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_steps_run ON pipeline_steps(run_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_steps_order ON pipeline_steps(run_id, step_order)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_runs_created ON pipeline_runs(created_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status)")

    conn.commit()


def create_run(run_id: str, prompt: str, mode: str = "auto", allow_heavy: bool = False):
    conn = get_connection()
    conn.execute(
        "INSERT INTO pipeline_runs (run_id, prompt, mode, allow_heavy) VALUES (?,?,?,?)",
        (run_id, prompt[:5000], mode, int(allow_heavy))
    )
    conn.commit()


def update_run(run_id: str, status: str = None, total_latency_ms: int = None, total_tokens: int = None):
    conn = get_connection()
    updates = []
    values = []

    if status is not None:
        updates.append("status = ?")
        values.append(status)
    if total_latency_ms is not None:
        updates.append("total_latency_ms = ?")
        values.append(total_latency_ms)
    if total_tokens is not None:
        updates.append("total_tokens = ?")
        values.append(total_tokens)

    if status in ("success", "error", "stopped"):
        updates.append("completed_at = ?")
        values.append(time.time())

    if updates:
        values.append(run_id)
        conn.execute(f"UPDATE pipeline_runs SET {', '.join(updates)} WHERE run_id = ?", values)
        conn.commit()


def add_step(run_id: str, step_order: int, node_id: str, input_text: str = "", model_used: str = ""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO pipeline_steps (run_id, step_order, node_id, input, status, model_used) VALUES (?,?,?,?,?,?)",
        (run_id, step_order, node_id, input_text[:5000], "running", model_used)
    )
    conn.commit()


def update_step(run_id: str, node_id: str, status: str = None, output: str = None,
                latency_ms: int = None, tokens: int = None, error: str = None):
    conn = get_connection()
    updates = []
    values = []

    if status is not None:
        updates.append("status = ?")
        values.append(status)
    if output is not None:
        updates.append("output = ?")
        values.append(output[:10000])
    if latency_ms is not None:
        updates.append("latency_ms = ?")
        values.append(latency_ms)
    if tokens is not None:
        updates.append("tokens = ?")
        values.append(tokens)
    if error is not None:
        updates.append("error = ?")
        values.append(error[:5000])

    if updates:
        values.append(run_id)
        values.append(node_id)
        conn.execute(f"UPDATE pipeline_steps SET {', '.join(updates)} WHERE run_id = ? AND node_id = ?", values)
        conn.commit()


def get_run(run_id: str) -> dict:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM pipeline_runs WHERE run_id = ?",
        (run_id,)
    ).fetchone()
    return dict(row) if row else None


def get_run_steps(run_id: str) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM pipeline_steps WHERE run_id = ? ORDER BY step_order ASC",
        (run_id,)
    ).fetchall()
    return [dict(row) for row in rows]


def get_recent_runs(limit: int = 20) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM pipeline_runs ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    return [dict(row) for row in rows]


def get_active_run() -> dict:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM pipeline_runs WHERE status = 'running' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    return dict(row) if row else None


def update_pattern(prompt: str, route: str, success: bool):
    import hashlib
    prompt_hash = hashlib.md5(prompt.lower().strip().encode()).hexdigest()
    conn = get_connection()

    existing = conn.execute(
        "SELECT * FROM pipeline_patterns WHERE prompt_hash = ?",
        (prompt_hash,)
    ).fetchone()

    if existing:
        if success:
            conn.execute(
                "UPDATE pipeline_patterns SET success_count = success_count + 1, last_used = ?, route = ? WHERE prompt_hash = ?",
                (time.time(), route, prompt_hash)
            )
        else:
            conn.execute(
                "UPDATE pipeline_patterns SET fail_count = fail_count + 1, last_used = ? WHERE prompt_hash = ?",
                (time.time(), prompt_hash)
            )
    else:
        conn.execute(
            "INSERT INTO pipeline_patterns (prompt_hash, prompt, route, success_count, fail_count) VALUES (?,?,?,?,?)",
            (prompt_hash, prompt[:500], route, int(success), int(not success))
        )
    conn.commit()


def delete_run(run_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM pipeline_steps WHERE run_id = ?", (run_id,))
    conn.execute("DELETE FROM pipeline_runs WHERE run_id = ?", (run_id,))
    conn.commit()


def clear_all_runs():
    conn = get_connection()
    conn.execute("DELETE FROM pipeline_steps")
    conn.execute("DELETE FROM pipeline_runs")
    conn.execute("DELETE FROM pipeline_patterns")
    conn.commit()
