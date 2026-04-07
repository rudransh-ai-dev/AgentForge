"""Migration 001: Create all new memory domain tables with indexes, WAL, and FK."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "memory.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def migrate():
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

    c.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp ON chat_messages(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated ON chat_sessions(updated_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_agent_knowledge_agent ON agent_knowledge(agent_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_agent_patterns_agent_hash ON agent_patterns(agent_id, prompt_hash)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_agent_fixes_agent ON agent_fixes(agent_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_agent_fixes_success ON agent_fixes(agent_id, success)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_steps_run ON pipeline_steps(run_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_steps_order ON pipeline_steps(run_id, step_order)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_runs_created ON pipeline_runs(created_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status)")

    conn.commit()
    conn.close()
