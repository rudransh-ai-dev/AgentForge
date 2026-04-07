import time
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_metrics():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metric_vram_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_gb REAL,
            used_gb REAL,
            active_models TEXT
        )
    """)
    conn.commit()
    conn.close()


def record_run(run_id, mode, task_type, model, latency_ms, tokens, status, session_id=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO metric_runs (run_id, mode, task_type, model, latency_ms, tokens, status, session_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, mode, task_type, model, latency_ms, tokens, status, session_id),
    )
    conn.commit()
    conn.close()


def record_vram_sample(total_gb, used_gb, active_models):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO metric_vram_samples (total_gb, used_gb, active_models)
           VALUES (?, ?, ?)""",
        (total_gb, used_gb, ",".join(active_models) if isinstance(active_models, list) else active_models),
    )
    conn.commit()
    conn.close()


def get_overview():
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM metric_runs WHERE date(timestamp) = date(?)", (today,))
    total_today = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM metric_runs WHERE status = 'success'")
    total_success = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM metric_runs")
    total_all = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(latency_ms) FROM metric_runs WHERE latency_ms > 0")
    row = cursor.fetchone()
    avg_latency = round(row[0], 0) if row[0] else 0

    cursor.execute("SELECT AVG(latency_ms) FROM metric_runs WHERE latency_ms > 0 AND date(timestamp) = date(?)", (today,))
    row = cursor.fetchone()
    avg_latency_today = round(row[0], 0) if row[0] else 0

    success_rate = round((total_success / total_all * 100), 1) if total_all > 0 else 0

    conn.close()
    return {
        "total_runs_today": total_today,
        "total_runs": total_all,
        "success_rate": success_rate,
        "avg_latency_ms": int(avg_latency),
        "avg_latency_today_ms": int(avg_latency_today),
    }


def get_latency_timeseries(hours=24):
    conn = get_connection()
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    cursor.execute(
        """SELECT timestamp, latency_ms, model, status FROM metric_runs
           WHERE timestamp > ? AND latency_ms > 0
           ORDER BY timestamp ASC""",
        (cutoff,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "timestamp": r["timestamp"],
            "latency_ms": r["latency_ms"],
            "model": r["model"],
            "status": r["status"],
        }
        for r in rows
    ]


def get_vram_timeseries(hours=24):
    conn = get_connection()
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    cursor.execute(
        """SELECT timestamp, total_gb, used_gb, active_models FROM metric_vram_samples
           WHERE timestamp > ?
           ORDER BY timestamp ASC""",
        (cutoff,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "timestamp": r["timestamp"],
            "total_gb": r["total_gb"],
            "used_gb": r["used_gb"],
            "active_models": r["active_models"],
        }
        for r in rows
    ]


def get_model_breakdown():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT model, COUNT(*) as runs,
                  AVG(latency_ms) as avg_latency,
                  SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
           FROM metric_runs
           WHERE model IS NOT NULL AND model != ''
           GROUP BY model
           ORDER BY runs DESC"""
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "model": r["model"],
            "runs": r["runs"],
            "avg_latency_ms": round(r["avg_latency"], 0) if r["avg_latency"] else 0,
            "success_rate": round(r["success_rate"], 1),
        }
        for r in rows
    ]


def get_task_distribution():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT task_type, COUNT(*) as count
           FROM metric_runs
           WHERE task_type IS NOT NULL AND task_type != ''
           GROUP BY task_type
           ORDER BY count DESC"""
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"task_type": r["task_type"], "count": r["count"]} for r in rows]


def get_recent_runs(limit=50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT run_id, timestamp, mode, task_type, model, latency_ms, tokens, status
           FROM metric_runs
           ORDER BY timestamp DESC
           LIMIT ?""",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "run_id": r["run_id"],
            "timestamp": r["timestamp"],
            "mode": r["mode"],
            "task_type": r["task_type"],
            "model": r["model"],
            "latency_ms": r["latency_ms"],
            "tokens": r["tokens"],
            "status": r["status"],
        }
        for r in rows
    ]


init_metrics()
