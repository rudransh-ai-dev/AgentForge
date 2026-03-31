# 🧠 LocalAI — VRAM-Aware Multi-Agent Orchestration Platform

> A production-grade, fully local AI Agent IDE built on top of Ollama with a layered intelligence architecture. No cloud. No API keys. Complete control.

---

## 🏗️ Architecture Overview

```
User Prompt
    │
    ▼
┌─────────────────────────────────────────────┐
│            COMMAND CENTER (UI)              │
│  Mode: AUTO / DIRECT / AGENT  ·  DeepThink │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│           MANAGER — phi3:mini               │
│   Task Classification · Plan Generation    │
│   Confidence Scoring · Agent Selection     │
└─────────────────────┬───────────────────────┘
                      │
          ┌───────────▼───────────┐
          │       TASK ROUTER     │
          │  task_type → agent    │
          └───────────┬───────────┘
                      │
     ┌────────────────┼──────────────────┐
     ▼                ▼                  ▼
┌──────────┐   ┌──────────────┐   ┌──────────┐
│  CODER   │   │   ANALYST    │   │  CRITIC  │
│ deepseek │   │   llama3:8b  │   │ llama3:8b│
│  6.7b    │   │              │   │          │
└────┬─────┘   └──────────────┘   └─────┬────┘
     │                                   │
     │         Critic rejects?           │
     └───────────────────────────────────┘
                      │
             ≥2 fails / low confidence?
                      │
                      ▼
         ┌────────────────────────┐
         │   HEAVY — qwen 35B     │
         │  Exclusive VRAM Mode   │
         │  Deep Reasoning / Fix  │
         └────────────────────────┘
```

---

## 🤖 Model Stack & Role Assignment

| Role | Model | VRAM | Trigger |
|---|---|---|---|
| **Manager** (Planner) | `phi3:mini` | 2.2 GB | Every request, always-on |
| **Coder** (Execution) | `deepseek-coder:6.7b` | 3.8 GB | Code tasks |
| **Analyst** (Reasoning) | `llama3:8b` | 4.7 GB | Explanation / Analysis |
| **Critic** (Validator) | `llama3:8b` | 4.7 GB | Automatic after Coder |
| **Heavy** (Expert) | `qwen3.5:35b-a3b` | 23 GB | Auto-escalation only |
| **Fallback** | Qwen 27B Distilled | 13 GB | If heavy fails |
| **Data** | `mixtral:latest` | 26 GB | Large-context data tasks |

### Execution Rules
- Models **< 10 GB** can co-run in VRAM (Phi-3, DeepSeek, Llama-3 warm pool)
- Models **≥ 10 GB** require **exclusive VRAM** — all others are unloaded first
- Qwen/Mixtral are **auto-released** from VRAM immediately after task completion

---

## 🔁 Task → Agent Mapping

```python
TASK_ROUTER = {
    "code_generation" → coder       # DeepSeek 6.7B
    "debug_basic"     → coder       # DeepSeek 6.7B
    "debug_complex"   → heavy       # Qwen 35B (auto-escalation)
    "explanation"     → analyst     # Llama-3 8B
    "analysis"        → analyst     # Llama-3 8B
    "review"          → critic      # Llama-3 8B
    "data_task"       → data        # Mixtral
}
```

### Auto Heavy Escalation Triggers
```
retries >= 2  →  Escalate to Qwen 35B
confidence < 0.5  →  Escalate to Qwen 35B
task_type == "debug_complex"  →  Escalate to Qwen 35B
```

---

## 🎛️ Dual-Mode Execution

| Mode | Behavior | Target Latency |
|---|---|---|
| **DIRECT** | Bypass pipeline, single model | < 2 seconds |
| **AGENT** | Full pipeline: Plan → Execute → Review | 8–15 seconds |
| **AUTO** | Manager decides based on complexity | Adaptive |

---

## 📁 Project Structure

```
ai-agent-ide/
├── backend/
│   ├── main.py                    # FastAPI server + WebSocket stream
│   ├── config.py                  # Model registry + TASK_ROUTER
│   ├── requirements.txt
│   ├── agents/
│   │   ├── coder.py               # DeepSeek code generation agent
│   │   ├── analyst.py             # Llama-3 reasoning agent
│   │   └── critic.py              # Llama-3 validation + feedback loop
│   ├── core/
│   │   ├── orchestrator.py        # Pipeline execution engine (v3.1)
│   │   ├── router.py              # Task classifier + planner (phi3)
│   │   ├── memory.py              # SQLite run history
│   │   ├── session.py             # Per-session context management
│   │   └── context.py             # Context compression
│   ├── services/
│   │   ├── vram_scheduler.py      # VRAM allocation + FIFO lock
│   │   ├── ollama_client.py       # Async Ollama API wrapper
│   │   ├── event_emitter.py       # WebSocket event bus
│   │   ├── sanitizer.py           # JSON extraction + auto-fix
│   │   └── logger.py              # Structured JSON logging
│   ├── schemas/
│   │   └── task.py                # Task, Step, Budget, Result models
│   └── workspace/                 # Generated project outputs
│
├── frontend/
│   └── src/
│       ├── Dashboard.jsx          # Main layout + Command Center
│       ├── store/
│       │   └── useAgentStore.js   # Zustand global state
│       └── components/
│           ├── AgentChat.jsx      # Streaming chat per-agent
│           ├── AgentCanvas.jsx    # XYFlow pipeline visualizer
│           ├── WorkspaceExplorer.jsx  # File manager for generated code
│           ├── CustomNode.jsx     # Pipeline node rendering
│           └── NodeInspectorPanel.jsx # Node detail drawer
│
├── docs/
│   └── system-design.md          # Full architecture specification
├── start.sh                       # Quick start script
└── README.md
```

---

## 🚀 Setup & Running

### Prerequisites
- **WSL2 (Ubuntu)** with Ollama installed
- **Node.js 18+** for the frontend
- **Python 3.10+** for the backend

### 1. Pull Models
```bash
ollama pull phi3:mini
ollama pull deepseek-coder:6.7b
ollama pull llama3:8b
# Optional heavy models (need 24GB+ VRAM)
ollama pull qwen3.5:35b-a3b
ollama pull mixtral:latest
```

### 2. Start Backend
```bash
cd backend
pip install -r requirements.txt
python3 -m uvicorn main:app --reload --port 8888
```

### 3. Start Frontend
```bash
cd frontend
npm install
npm run dev -- --port 5173
```

Open **http://localhost:5173**

---

## ⚡ API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Check Ollama + available models |
| `POST` | `/run` | Run agent pipeline (mode, prompt, allow_heavy) |
| `POST` | `/stop` | Abort running pipeline |
| `GET` | `/ws/events` | WebSocket real-time event stream |
| `GET` | `/memory/stats` | Session run history stats |
| `GET/POST` | `/workspace/*` | File system API for generated projects |

---

## 🔒 Key Engineering Decisions

- **Global Pipeline Lock** — Single `asyncio.Lock` ensures strictly sequential VRAM usage. No race conditions.
- **FIFO Task Queue** — Requests queue up; no parallel model loads. Memory is never fragmented.
- **Critic Feedback Loop** — Coder output is always reviewed. Two failed reviews auto-trigger Qwen escalation.
- **Stateless Agents** — Every agent is a pure function. State lives only in the Orchestrator and Session.
- **Zero Cloud Dependencies** — 100% local. Ollama handles all model serving.

---

## 📊 Expected Performance (RTX 3090 / 24GB VRAM)

| Model Combo | Speed |
|---|---|
| Phi-3 alone | ~40 tok/s |
| Phi-3 + DeepSeek co-running | ~20 tok/s |
| Llama-3 8B | ~18 tok/s |
| Qwen 35B (exclusive) | ~6 tok/s |
| Model switch delay | 2–5 sec |

---

## 🧱 Built With

- **FastAPI** — Async Python backend
- **Ollama** — Local model serving
- **React + Vite** — Frontend
- **XYFlow** — Agent pipeline canvas
- **Zustand** — Global state management
- **Framer Motion** — UI animations
- **SQLite** — Persistent memory

---

*Built by Rudransh — Local-first AI, production-grade architecture.*
