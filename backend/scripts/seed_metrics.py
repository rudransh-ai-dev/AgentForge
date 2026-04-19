"""Seed metric_runs and metric_vram_samples with realistic historical data.

Generates:
  - ~350 runs over the past 10 days
  - ~55 runs for today
  - VRAM samples every ~15 min over the same window

Safe to run multiple times — uses a marker run_id prefix 'seed-' so you can
delete them with: DELETE FROM metric_runs WHERE run_id LIKE 'seed-%';
"""
import os
import sys
import random
import sqlite3
from datetime import datetime, timedelta, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory.db")

# Model profiles: (name, base_latency_ms, jitter_pct, success_rate)
MODEL_PROFILES = [
    ("llama3.1:8b",         4200,  0.35, 0.97),
    ("qwen2.5-coder:14b",   9800,  0.30, 0.95),
    ("qwen2.5:14b",         8600,  0.30, 0.96),
    ("gpt-oss:20b",        14200,  0.25, 0.93),
    ("deepseek-r1:8b",     18500,  0.40, 0.91),
    ("phi3:mini",           2100,  0.45, 0.94),
]

TASKS = [
    ("code_generation", "agent"),
    ("code_refinement", "agent"),
    ("qa_validation",   "agent"),
    ("research",        "agent"),
    ("analysis",        "agent"),
    ("direct",          "direct"),
    ("web_search",      "agent"),
    ("explanation",     "direct"),
]

# Agent-role → model mapping (matches config.py MODELS)
ROLE_MODEL = {
    "code_generation": "gpt-oss:20b",
    "code_refinement": "qwen2.5-coder:14b",
    "qa_validation":   "llama3.1:8b",
    "research":        "qwen2.5:14b",
    "analysis":        "llama3.1:8b",
    "direct":          "llama3.1:8b",
    "web_search":      "qwen2.5:14b",
    "explanation":     "llama3.1:8b",
}


def fmt_ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def pick_latency(base: int, jitter: float) -> int:
    delta = random.uniform(-jitter, jitter)
    return max(300, int(base * (1 + delta)))


def pick_tokens(latency_ms: int) -> int:
    # rough: ~35 tok/s local throughput
    return int((latency_ms / 1000) * random.uniform(25, 50))


def make_run(ts: datetime, idx: int):
    task_type, mode = random.choice(TASKS)
    model = ROLE_MODEL[task_type]
    profile = next(p for p in MODEL_PROFILES if p[0] == model)
    _, base, jitter, success_rate = profile
    latency = pick_latency(base, jitter)
    status = "success" if random.random() < success_rate else "error"
    tokens = pick_tokens(latency) if status == "success" else 0
    return (
        f"seed-{ts.strftime('%Y%m%d%H%M%S')}-{idx}",
        fmt_ts(ts),
        mode,
        task_type,
        model,
        latency,
        tokens,
        status,
        f"session-{ts.strftime('%Y%m%d')}-{idx % 7}",
    )


def main():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: {DB_PATH} not found. Start the backend once to init the schema.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    runs = []

    # Past 10 days: ~35 runs/day on average, concentrated in work hours
    for day_offset in range(10, 0, -1):
        day_base = now_utc - timedelta(days=day_offset)
        n_runs = random.randint(28, 48)
        for i in range(n_runs):
            hour = min(23, max(0, int(random.gauss(15, 3))))
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            ts = day_base.replace(hour=hour, minute=minute, second=second, microsecond=0)
            runs.append(make_run(ts, i))

    # Today: ~55 runs, spread from morning till now
    today_start = now_utc.replace(hour=8, minute=30, second=0, microsecond=0)
    total_seconds = max(60, int((now_utc - today_start).total_seconds()))
    n_today = random.randint(48, 62)
    for i in range(n_today):
        ts = today_start + timedelta(seconds=random.randint(0, total_seconds))
        runs.append(make_run(ts, i))

    cur.executemany(
        """INSERT INTO metric_runs
           (run_id, timestamp, mode, task_type, model, latency_ms, tokens, status, session_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        runs,
    )

    # VRAM samples: every 15 min over last 10 days
    vram_rows = []
    cursor_ts = now_utc - timedelta(days=10)
    total_gb = 12.0
    while cursor_ts <= now_utc:
        used = round(random.uniform(3.8, 10.6), 2)
        active = random.choice([
            "llama3.1:8b",
            "qwen2.5-coder:14b",
            "qwen2.5:14b",
            "gpt-oss:20b",
            "qwen2.5-coder:14b,llama3.1:8b",
            "",
        ])
        vram_rows.append((fmt_ts(cursor_ts), total_gb, used, active))
        cursor_ts += timedelta(minutes=15)

    cur.executemany(
        """INSERT INTO metric_vram_samples (timestamp, total_gb, used_gb, active_models)
           VALUES (?, ?, ?, ?)""",
        vram_rows,
    )

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM metric_runs")
    total_runs = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM metric_runs WHERE date(timestamp) = date('now')")
    today_runs = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM metric_vram_samples")
    vram_count = cur.fetchone()[0]

    print(f"Inserted {len(runs)} runs ({n_today} for today) + {len(vram_rows)} VRAM samples")
    print(f"DB now holds: {total_runs} runs total, {today_runs} today, {vram_count} VRAM samples")
    conn.close()


if __name__ == "__main__":
    random.seed()
    main()
