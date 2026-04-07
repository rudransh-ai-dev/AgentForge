"""
Migration Runner — Versioned database schema migrations.

Ensures backward compatibility and safe schema evolution.
"""
import sqlite3
import os
import importlib

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory.db")
MIGRATIONS_DIR = os.path.dirname(__file__)

MIGRATIONS = [
    "001_initial",
    "002_metrics_enable",
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def ensure_migrations_table():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def get_applied_migrations():
    conn = get_connection()
    rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version ASC").fetchall()
    conn.close()
    return [r["version"] for r in rows]


def run_migrations():
    ensure_migrations_table()
    applied = get_applied_migrations()

    for migration_name in MIGRATIONS:
        if migration_name in applied:
            continue

        print(f"Applying migration: {migration_name}")
        try:
            mod = importlib.import_module(f"migrations.{migration_name}")
            mod.migrate()

            conn = get_connection()
            conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (migration_name,))
            conn.commit()
            conn.close()
            print(f"  ✓ {migration_name} applied successfully")
        except Exception as e:
            print(f"  ✗ {migration_name} failed: {e}")
            raise
