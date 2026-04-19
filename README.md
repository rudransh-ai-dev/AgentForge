# AgentForge — VRAM-Aware Multi-Agent Code IDE

> Production-grade, fully local multi-agent code IDE built on Ollama. Seven specialized agents, 3-stage code pipeline, VRAM-aware scheduling, real-time canvas. No cloud. No API keys.

Built and tuned for **RTX 5070 Ti (16 GB GDDR7)**.

---

## Architecture

```
User Prompt
    │
    ▼
┌──────────────────────────────┐
│     Canvas / Chat UI         │
│  Mode: AUTO / DIRECT / AGENT │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   MANAGER — llama3.1:8b      │
│   Classify · Plan · Route    │
└──────────────┬───────────────┘
               │
    ┌──────────┴───────────┐
    ▼                      ▼
Production Pipeline    Specialist
    │                      │
    ▼                      ▼
WRITER → EDITOR → TESTER   RESEARCHER / READER / HEAVY
gpt-oss  qwen2.5  deepseek qwen2.5 / llama3.1 / phi4
 20b     coder14b   r1 8b
    │
    ▼
  TOOL ──► EXECUTOR ──► workspace/
 (save)   (sandbox run)
```

Every pipeline run ends in a real, runnable multi-file project dropped into `workspace/<project_id>/`.

---

## Model Roster (v4.0)

| Role       | Model              | VRAM    | Trigger                       |
|------------|--------------------|---------|-------------------------------|
| Manager    | `llama3.1:8b`      | 6.6 GB  | Every request                 |
| Writer     | `gpt-oss:20b`      | 13 GB   | Code-gen draft (exclusive)    |
| Editor     | `qwen2.5-coder:14b`| 9 GB    | Refinement (exclusive)        |
| Tester     | `deepseek-r1:8b`   | 5.2 GB  | QA validation                 |
| Researcher | `qwen2.5:14b`      | 9 GB    | Web/context research          |
| Reader     | `llama3.1:8b`      | pinned  | Codebase Q&A                  |
| Heavy      | `phi4:latest`      | 17 GB   | Architecture fallback         |

### Scheduling rules
- Models under 10 GB can co-reside in VRAM (Manager + Tester warm pool).
- Exclusive models (Writer, Editor, Heavy, Researcher) evict others before loading.
- `keep_alive=15m` on every call — no cold-load tax on agent hops.
- Manager model is warmed on backend startup for fast first-click.

---

## Task Routing

```python
TASK_ROUTER = {
    "code_generation": "writer",
    "code_refinement": "editor",
    "debug_basic":     "editor",
    "debug_complex":   "heavy",
    "explanation":     "analyst",
    "analysis":        "analyst",
    "review":          "tester",
    "research":        "researcher",
    "read_code":       "reader",
}
```

---

## Project Structure

```
ai-agent-ide/
├── backend/
│   ├── main.py                    FastAPI + WebSocket event bus
│   ├── config.py                  Model registry + TASK_ROUTER
│   ├── agents/                    Per-agent handlers (writer, editor, tester, …)
│   ├── core/
│   │   ├── orchestrator.py        3-stage pipeline engine
│   │   ├── router.py              Task classifier + planner
│   │   └── prompts/               SafePromptTemplate loader (v4.1)
│   ├── services/
│   │   ├── vram_scheduler.py      FIFO VRAM allocation
│   │   ├── ollama_client.py       Async Ollama + fallback chain
│   │   ├── metrics.py             Run history + timeseries
│   │   └── executor.py            Sandboxed project runner
│   └── schemas/                   Pydantic models
│
├── frontend/
│   └── src/
│       ├── pages/Dashboard.jsx
│       ├── store/useAgentStore.js ReactFlow + Zustand
│       └── components/
│           ├── AgentCanvas.jsx      Pipeline visualizer
│           ├── CustomNode.jsx       Node rendering + Input/Run
│           ├── WorkspaceExplorer.jsx
│           └── TimelinePanel.jsx    Metrics dashboard
│
├── prompts/                       All agent prompts (single source of truth)
├── docs/
│   ├── system-design.md
│   ├── v4_upgrades.md             v4.0 changelog
│   └── canvas-guide.md
├── scripts/                       Startup + deployment scripts
│   ├── start.sh                   Unified: backend + frontend
│   ├── start-backend.sh
│   ├── start-frontend.sh
│   ├── start-chat.sh
│   └── deploy-ngrok.sh            Expose via ngrok tunnels
├── workspace/                     Generated projects land here
└── start.sh                       Thin wrapper → scripts/start.sh
```

---

## Setup

### Prerequisites
- Linux / WSL2 with **Ollama**
- **Python 3.10+**, **Node.js 18+**

### 1. Pull models
```bash
ollama pull llama3.1:8b
ollama pull gpt-oss:20b
ollama pull qwen2.5-coder:14b
ollama pull deepseek-r1:8b
ollama pull qwen2.5:14b
# Optional heavy fallback
ollama pull phi4:latest
```

### 2. One-command start

```bash
./start.sh             # backend + frontend together
./start.sh backend     # backend only
./start.sh frontend    # frontend only
./start.sh stop        # kill everything
```

The root `start.sh` is a thin wrapper — the real scripts live in [`scripts/`](scripts/).

### 3. Manual start (if you prefer)
```bash
cd backend && pip install -r requirements.txt && python -m uvicorn main:app --reload --port 8888
# in another terminal
cd frontend && npm install && npm run dev -- --port 5173
```

### 4. Public tunnel (optional)
```bash
./scripts/deploy-ngrok.sh [ngrok-authtoken]
```

Open **http://localhost:5173**. Drop a prompt into the Input node on the canvas, hit **▶ Run Pipeline**, watch the nodes light up.

---

## API

| Method | Endpoint            | Description                          |
|--------|---------------------|--------------------------------------|
| GET    | `/health`           | Ollama status + available models     |
| POST   | `/run`              | Run full pipeline                    |
| POST   | `/run-node`         | Run a single canvas node             |
| POST   | `/stop`             | Abort pipeline                       |
| WS     | `/ws/events`        | Real-time pipeline event stream      |
| GET    | `/metrics/overview` | Run counts, success rate, latency    |
| GET    | `/metrics/timeseries` | 24h latency + VRAM history        |
| GET/POST | `/workspace/*`    | File system API for generated code   |

---

## Key Engineering Decisions

- **Global pipeline lock**: single `asyncio.Lock` ensures sequential VRAM usage. No race conditions.
- **Writer ≠ Editor**: different models on the two code stages — enforced in `config.py`. Same model collapses the pipeline into pointless self-review.
- **SafePromptTemplate**: prompts can embed literal JSON braces without crashing Python's `.format()`.
- **Stateless agents**: each agent is a pure async function. State lives in orchestrator + session only.
- **Zero cloud**: 100% local inference via Ollama.

See [`docs/v4_upgrades.md`](docs/v4_upgrades.md) for the full v4.0 changelog (dead fallback-chain bug, cold-load tax, metrics UTC bug, canvas input node, workspace routing, prompt template trap, and more).

---

## Built With

FastAPI · Ollama · React + Vite · ReactFlow · Zustand · Framer Motion · SQLite

---

*Built by Rudransh — local-first AI, production-grade architecture.*
