"""
Memory Manager — Central orchestrator for all 4 memory domains.

Manages initialization, connection pooling, WAL mode, foreign keys,
and provides a unified interface to chat, agent, canvas, and metrics memory.
"""
import sqlite3
import os
import threading

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory.db")

_local = threading.local()


def get_connection():
    """Thread-safe connection with WAL mode and foreign keys enabled."""
    if not hasattr(_local, 'conn') or _local.conn is None:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        _local.conn = conn
    return _local.conn


def close_connection():
    """Close the thread-local connection."""
    if hasattr(_local, 'conn') and _local.conn is not None:
        _local.conn.close()
        _local.conn = None


def init_all():
    """Initialize all memory domain schemas."""
    from core.chat_memory import init_chat_memory
    from core.agent_memory import init_agent_memory
    from core.canvas_memory import init_canvas_memory
    from services.metrics import init_metrics
    from core.prompt_versions import init_prompt_versions

    conn = get_connection()

    init_chat_memory()
    init_agent_memory()
    init_canvas_memory()
    init_metrics()
    init_prompt_versions()

    conn.commit()


def get_db_health():
    """Return database health metrics."""
    conn = get_connection()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()

    health = {
        "db_path": DB_PATH,
        "tables": {},
        "total_size_bytes": 0,
    }

    try:
        stat = os.stat(DB_PATH)
        health["total_size_bytes"] = stat.st_size
        health["total_size_mb"] = round(stat.st_size / (1024 * 1024), 2)
    except OSError:
        health["total_size_bytes"] = 0
        health["total_size_mb"] = 0

    for table in tables:
        name = table["name"]
        count = conn.execute(f"SELECT COUNT(*) as c FROM {name}").fetchone()["c"]
        health["tables"][name] = count

    return health


def cleanup_old_data(chat_ttl_days=7, metrics_ttl_days=30, canvas_ttl_days=30):
    """Remove data older than TTL thresholds. Returns counts of deleted rows."""
    conn = get_connection()
    deleted = {}

    deleted["chat_messages"] = conn.execute(
        f"DELETE FROM chat_messages WHERE timestamp < strftime('%s', 'now', '-{chat_ttl_days} days')"
    ).rowcount

    deleted["chat_sessions"] = conn.execute(
        f"DELETE FROM chat_sessions WHERE updated_at < strftime('%s', 'now', '-{chat_ttl_days} days') AND session_id NOT IN (SELECT DISTINCT session_id FROM chat_messages)"
    ).rowcount

    deleted["metric_runs"] = conn.execute(
        f"DELETE FROM metric_runs WHERE timestamp < datetime('now', '-{metrics_ttl_days} days')"
    ).rowcount

    deleted["metric_vram_samples"] = conn.execute(
        f"DELETE FROM metric_vram_samples WHERE timestamp < datetime('now', '-{metrics_ttl_days} days')"
    ).rowcount

    deleted["pipeline_runs"] = conn.execute(
        f"DELETE FROM pipeline_runs WHERE created_at < strftime('%s', 'now', '-{canvas_ttl_days} days')"
    ).rowcount

    deleted["pipeline_steps"] = conn.execute(
        f"DELETE FROM pipeline_steps WHERE run_id NOT IN (SELECT run_id FROM pipeline_runs)"
    ).rowcount

    conn.execute("VACUUM")
    conn.commit()

    return deleted
