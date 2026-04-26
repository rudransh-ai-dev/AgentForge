# AgentForge - VRAM-Aware Multi-Agent Code IDE

> Production-grade, fully local multi-agent code IDE built on Ollama. V5 adds a specification agent, selective context passing, local retrieval, validator guardrails, VRAM-aware scheduling, and a real-time canvas. No cloud. No API keys.

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
│ SPECIFIER - llama3.1:8b      │
│ Normalize requirements       │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ CONTEXT MANAGER              │
│ Selective context + retrieval│
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   MANAGER - llama3.1:8b      │
│   Classify · Plan · Route    │
└──────────────┬───────────────┘
               │
    ┌──────────┴───────────┐
    ▼                      ▼
Production Pipeline    Specialist
    │                      │
    ▼                      ▼
WRITER → EDITOR → TESTER   RESEARCHER / READER / HEAVY
qwen2.5  qwen2.5  llama3.1 qwen2.5 / llama3.1 / codestral
coder14b coder14b  8b
    │
    ▼
  TOOL ──► EXECUTOR ──► workspace/
 (save)   (sandbox run)
```

Every pipeline run ends in a real, runnable multi-file project dropped into `workspace/<project_id>/`.

---

## V5 Upgrade Status

Implemented:
- Specification Agent: converts vague prompts into a compact execution contract before routing.
- Selective context passing: agents get only the spec, retrieval hits, session summary, or previous output they actually need.
- Local retrieval/RAG: dependency-free retrieval over `docs/`, `workspace/`, and recent run history.
- Validator gate: rejects empty code, placeholders, and missing runnable artifacts before model QA.
- Canvas update: V5 flow now includes the Spec Agent and Context Manager events.
- V5 status endpoints: `/health` and `/v5/status`.

Not installed yet:
- Chroma/vector embeddings. The current retrieval layer works now without extra dependencies, but it is keyword/local-text retrieval rather than embedding search.

---

## Model Roster (v5.0)

| Role       | Model              | VRAM    | Trigger                       |
|------------|--------------------|---------|-------------------------------|
| Manager    | `llama3.1:8b`      | 6.6 GB  | Every request                 |
| Specifier  | `llama3.1:8b`      | 6.6 GB  | Requirements normalization    |
| Writer     | `qwen2.5-coder:14b`| 9 GB    | Code-gen draft (exclusive)    |
| Editor     | `qwen2.5-coder:14b`| 9 GB    | Refinement (exclusive)        |
| Tester     | `llama3.1:8b`      | 4.9 GB  | QA validation                 |
| Critic     | `deepseek-r1:8b`   | 5.2 GB  | Secondary validation          |
| Researcher | `qwen2.5:14b`      | 9 GB    | Web/context research          |
| Reader     | `llama3.1:8b`      | pinned  | Codebase Q&A                  |
| Heavy      | `codestral:22b`    | 12 GB   | Architecture fallback         |

### Scheduling rules
- Models under 10 GB can co-reside in VRAM (Manager + Tester warm pool).
- Exclusive models (Writer, Editor, Heavy, Researcher) evict others before loading.
- `keep_alive=15m` on every call - no cold-load tax on agent hops.
- Manager model is warmed on backend startup for fast first-click.
- Writer and Editor share `qwen2.5-coder:14b` in demo mode to avoid unnecessary model swaps.

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
    "specification":   "specifier",
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
│   │   ├── specification.py       V5 deterministic spec agent
│   │   ├── retrieval.py           V5 local retrieval/RAG layer
│   │   ├── context.py             Selective per-agent context windows
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
ollama pull qwen2.5-coder:14b
ollama pull deepseek-r1:8b
ollama pull qwen2.5:14b
# Optional heavy fallback
ollama pull codestral:22b
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
| GET    | `/v5/status`        | V5 feature status + retrieval probe  |
| POST   | `/run`              | Run full pipeline                    |
| POST   | `/run-node`         | Run a single canvas node             |
| POST   | `/stop`             | Abort pipeline                       |
| WS     | `/ws/agent-stream`  | Real-time pipeline event stream      |
| GET    | `/metrics/overview` | Run counts, success rate, latency    |
| GET    | `/metrics/latency`  | Latency history                      |
| GET    | `/metrics/vram`     | VRAM history                         |
| GET/POST | `/workspace/*`    | File system API for generated code   |

---

## Key Engineering Decisions

- **Global pipeline lock**: single `asyncio.Lock` ensures sequential VRAM usage. No race conditions.
- **Specifier before Manager**: ambiguous requests are normalized before planning, which improves routing and output quality.
- **Selective context**: the Manager, Writer, Editor, Tester, Researcher, and Tool nodes receive different compact prompt windows instead of one bloated conversation.
- **Local retrieval first**: V5 uses dependency-free retrieval over local docs, generated projects, and run history so it works immediately.
- **Writer + Editor demo model sharing**: both use `qwen2.5-coder:14b` to reduce cold swaps during demos.
- **SafePromptTemplate**: prompts can embed literal JSON braces without crashing Python's `.format()`.
- **Stateless agents**: each agent is a pure async function. State lives in orchestrator + session only.
- **Zero cloud**: 100% local inference via Ollama.

See [`docs/v5_upgrade.md`](docs/v5_upgrade.md) for the V5 roadmap and [`docs/v4_upgrades.md`](docs/v4_upgrades.md) for the v4.0 changelog.

---

## Making The Canvas Faster

Fastest wins already applied:
- Manager warmup on backend startup.
- Writer and Editor share `qwen2.5-coder:14b` to avoid a model unload/load between stages.
- Selective context reduces prompt size per agent.
- Local retrieval is dependency-free and avoids vector DB startup cost.

Next speedups to implement:
- Render only active node output previews; keep full logs in the Timeline panel.
- Throttle WebSocket node update events to 100-200ms instead of updating ReactFlow on every chunk.
- Virtualize long timeline/history lists.
- Memoize `CustomNode` and avoid re-rendering every node when one node streams.
- Keep a small model warm for Manager/Specifier/Tester and unload only exclusive code models.
- Add a "Fast Draft" mode that runs Writer -> Tool -> Executor and skips Editor/Tester for tiny tasks.

---

## Full Chroma Vector RAG Upgrade

Current status: V5 local retrieval is done, but full embedding/vector search is not installed yet.

To add Chroma:

1. Install dependencies:
```bash
cd backend
../.venv/bin/pip install chromadb sentence-transformers
```

2. Add them to [backend/requirements.txt](backend/requirements.txt):
```text
chromadb
sentence-transformers
```

3. Create an indexer that embeds files from `docs/`, `workspace/`, and recent run history.

4. Replace or extend [backend/core/retrieval.py](backend/core/retrieval.py) so `retrieve_context()` first queries Chroma and falls back to the current keyword retriever if Chroma is unavailable.

5. Re-index after generated projects change, either after Tool saves files or through a manual `/rag/reindex` endpoint.

Recommended local embedding model:
```text
sentence-transformers/all-MiniLM-L6-v2
```

For your interview/demo, you can honestly say: "V5 has a local retrieval layer now. Full Chroma vector RAG is the next upgrade; the interface is already isolated in `core/retrieval.py`, so swapping it in is straightforward."

---

## Built With

FastAPI · Ollama · React + Vite · ReactFlow · Zustand · Framer Motion · SQLite

---

*Built by Rudransh — local-first AI, production-grade architecture.*
