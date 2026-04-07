"""Migration 002: Enable metrics recording — fix dead code."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "memory.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def migrate():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS metric_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            mode TEXT,
            task_type TEXT,
            model TEXT,
            latency_ms INTEGER,
            tokens INTEGER,
            status TEXT,
            session_id TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS metric_vram_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_gb REAL,
            used_gb REAL,
            active_models TEXT
        )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_metric_runs_timestamp ON metric_runs(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_metric_runs_model ON metric_runs(model)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_metric_runs_status ON metric_runs(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_metric_vram_timestamp ON metric_vram_samples(timestamp)")

    conn.commit()
    conn.close()
