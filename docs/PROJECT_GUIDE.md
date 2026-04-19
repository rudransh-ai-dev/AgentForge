# AgentForge — Multi-Agent IDE: Comprehensive Project Guide
> **Version:** v3.1 / v4.0 Production  
> **Hardware Target:** RTX 5070 Ti — 16 GB GDDR7 VRAM  
> **Stack:** FastAPI (Python) + React (Vite) + Ollama + SQLite  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Directory Structure](#3-directory-structure)
4. [Backend — Deep Dive](#4-backend--deep-dive)
   - [main.py](#41-mainpy--the-api-gateway)
   - [config.py](#42-configpy--model-registry-and-routing-config)
   - [core/orchestrator.py](#43-coreorchestratorpy--the-brain)
   - [core/router.py](#44-corerouterpy--task-routing-and-planning)
   - [core/memory.py](#45-corememorypy--persistent-memory)
   - [core/chat_memory.py](#46-corechat_memorypy)
   - [core/canvas_memory.py](#47-corecanvas_memorypy)
   - [core/session.py](#48-coresessionpy)
   - [core/context.py](#49-corecontextpy)
   - [core/memory_manager.py](#410-corememory_managerpy)
   - [core/prompt_versions.py](#411-coreprompt_versionspy)
   - [services/vram_scheduler.py](#412-servicesvram_schedulerpy--vram-scheduler)
   - [services/event_emitter.py](#413-servicesevent_emitterpy--websocket-broadcaster)
   - [services/executor.py](#414-servicesexecutorpy--sandboxed-code-runner)
   - [services/ollama_client.py](#415-servicesollamaclientpy)
   - [services/sanitizer.py](#416-servicessanitizerpy)
   - [services/metrics.py](#417-servicesmetricspy)
   - [services/diff.py](#418-servicesdiffpy)
   - [services/whisper_stt.py](#419-serviceswhisper_sttpy)
   - [agents/](#420-agents-directory)
   - [chat_server.py](#421-chat_serverpy--persona-sub-app)
   - [schemas/](#422-schemas)
5. [Frontend — Deep Dive](#5-frontend--deep-dive)
   - [App.jsx and main.jsx](#51-appjsx-and-mainjsx)
   - [pages/LandingPage.jsx](#52-pageslandingpagejsx)
   - [pages/Dashboard.jsx](#53-pagesdashboardjsx--the-main-ui)
   - [components/AgentCanvas.jsx](#54-componentsagentcanvasjsx)
   - [components/CustomNode.jsx](#55-componentscustomnodejsx)
   - [components/NodeInspectorPanel.jsx](#56-componentsnodeinspectorpaneljsx)
   - [components/NodeSidebar.jsx](#57-componentsnodesidebarjsx)
   - [components/SimpleChat.jsx](#58-componentssimplechatjsx)
   - [components/AgentChat.jsx](#59-componentsagentchatjsx)
   - [components/WorkspaceExplorer.jsx](#510-componentsworkspaceexplorerjsx)
   - [components/TimelinePanel.jsx](#511-componentstimelinepaneljsx)
   - [components/PerformanceDashboard.jsx](#512-componentsperformancedashboardjsx)
   - [components/CustomAgentManager.jsx](#513-componentscustomagentmanagerjsx)
   - [components/VoiceButton.jsx](#514-componentsvoicebuttonjsx)
   - [components/StatusBar.jsx](#515-componentsstatusbarisx)
   - [components/ChatHistoryPanel.jsx](#516-componentschathistorypaneljsx)
   - [components/CodeDiffViewer.jsx](#517-componentscodediffviewerjsx)
   - [store/useAgentStore.js](#518-storeuseagentstorejs)
   - [store/useSimpleChatHistoryStore.js](#519-storeusesimplechathistorystorejs)
   - [store/useAgentChatHistoryStore.js](#520-storeuseagentchathistorystorejs)
   - [config/agents.js](#521-configagentsjs)
   - [index.css](#522-indexcss)
6. [Prompts Directory](#6-prompts-directory)
7. [End-to-End Data Flow](#7-end-to-end-data-flow)
8. [Key Design Patterns](#8-key-design-patterns)
9. [Scripts and Start Files](#9-scripts-and-start-files)
10. [100+ Viva Questions and Answers](#10-100-viva-questions-and-answers)

---

## 1. Project Overview

**AgentForge Multi-Agent IDE** is a fully local, offline-first AI-powered Integrated Development Environment (IDE). It orchestrates multiple AI language models (LLMs) running on-device via [Ollama](https://ollama.com/) to collaboratively plan, write, review, test, and execute code — all without sending data to any cloud service.

### Core Capabilities
| Feature | Description |
|---|---|
| **Multi-Agent Pipeline** | Writer → Editor → Tester feedback loop produces production-grade code |
| **VRAM-Aware Scheduling** | One GPU, many models — scheduler loads/unloads automatically |
| **Visual Agent Canvas** | ReactFlow graph showing live agent execution as animated nodes |
| **Dual-Mode Execution** | "Direct" (<2s) for simple questions, "Agent" (<15s) for coding tasks |
| **Persona Chat** | AI friends with uncensored personalities (Persona mode) |
| **Workspace Explorer** | Code files saved to `/workspace`, viewable + editable in the UI |
| **Self-Correcting Code** | Autofix loop: execute → catch errors → regenerate → re-execute |
| **Voice Input** | Whisper STT converts microphone audio to text |
| **Streaming Responses** | SSE + WebSocket for real-time character-by-character output |

### Tech Stack
| Layer | Technology |
|---|---|
| **Backend** | Python 3.11+, FastAPI, Uvicorn, SQLite, asyncio |
| **AI Inference** | Ollama (local LLM runner), Whisper (STT) |
| **Frontend** | React 18, Vite, Zustand, ReactFlow, Framer Motion, TailwindCSS |
| **Realtime** | WebSocket (agent events), SSE (chat streaming) |
| **Storage** | SQLite (`memory.db`) for all persistent state |

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         BROWSER (React/Vite)                         │
│  ┌──────────┐  ┌────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │Dashboard │  │SimpleChat  │  │AgentCanvas   │  │WorkspaceExpl. │  │
│  └────┬─────┘  └─────┬──────┘  └──────┬───────┘  └───────────────┘  │
│       │ fetch/POST   │  SSE stream     │ WebSocket                   │
└───────┼──────────────┼─────────────────┼────────────────────────────-┘
        │              │                 │
        ▼              ▼                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    FASTAPI SERVER (main.py :8000)                     │
│  /run  /run-node  /agent/{id}/chat  /workspace  /ws/agent-stream     │
│                                                                        │
│  ┌──────────────────────────────────────────────────┐                 │
│  │           DUAL-MODE EXECUTION ENGINE              │                 │
│  │  ┌───────────┐         ┌────────────────────┐    │                 │
│  │  │Direct Mode│         │   Agent Mode        │    │                 │
│  │  │ (< 2s)    │         │ Router → Planner    │    │                 │
│  │  └───────────┘         │    ↓                │    │                 │
│  │               Pipeline Lock (asyncio.Lock)   │    │                 │
│  │               ┌──────────────────────────┐   │    │                 │
│  │               │  ORCHESTRATOR            │   │    │                 │
│  │               │  Writer → Editor →Tester │   │    │                 │
│  │               │  researcher / analyst    │   │    │                 │
│  │               └──────────────────────────┘   │    │                 │
│  └──────────────────────────────────────────────┘                 │
│                                                                        │
│  ┌─────────────────────┐   ┌──────────────────────────────────────┐  │
│  │   VRAM Scheduler    │   │  EventEmitter (WebSocket Broadcaster) │  │
│  │  Model Registry     │   │  Broadcasts agent events to UI         │  │
│  │  Load/Unload via    │   └──────────────────────────────────────┘  │
│  │  Ollama API         │                                               │
│  └─────────────────────┘                                               │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │           SQLite memory.db (4 domains)                           │  │
│  │  runs | fixes | patterns | chat_sessions | canvas_runs | metrics │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────┐
│   OLLAMA  :11434     │
│  llama3.1:8b         │
│  qwen2.5-coder:14b   │
│  deepseek-r1:8b      │
│  gpt-oss:20b         │
│  codestral:22b       │
└──────────────────────┘
        │
        ▼
   GPU VRAM (16GB)
```

---

## 3. Directory Structure

```
ai-agent-ide-type-project/
│
├── backend/                   ← Python FastAPI server
│   ├── main.py                ← API Gateway (1153 lines) — all HTTP + WS routes
│   ├── chat_server.py         ← Persona chat sub-app (mounted at /persona)
│   ├── config.py              ← Model registry, TASK_ROUTER, fallback chains
│   ├── requirements.txt       ← Python dependencies
│   ├── memory.db              ← SQLite persistent storage
│   ├── custom_agents.json     ← User-created custom agent definitions
│   │
│   ├── core/                  ← Core business logic
│   │   ├── orchestrator.py    ← run_direct_mode, run_agent_mode (1373 lines)
│   │   ├── router.py          ← route_task_async, plan_task_async
│   │   ├── memory.py          ← runs/fixes/patterns tables
│   │   ├── chat_memory.py     ← chat sessions and messages
│   │   ├── canvas_memory.py   ← canvas runs and agent steps
│   │   ├── agent_memory.py    ← per-agent knowledge and fix patterns
│   │   ├── session.py         ← session management
│   │   ├── context.py         ← context window compression
│   │   ├── memory_manager.py  ← DB health, TTL cleanup, init_all()
│   │   ├── prompt_versions.py ← versioned prompt history in DB
│   │   └── prompts/           ← prompt loader from /prompts/*.md files
│   │
│   ├── agents/                ← Individual agent implementations
│   │   ├── coder.py           ← run_coder_async (streaming)
│   │   ├── analyst.py         ← run_analyst_async
│   │   ├── critic.py          ← run_critic_async, validate_output
│   │   ├── writer.py          ← run_writer_async (Stage 1)
│   │   ├── editor.py          ← run_editor_async (Stage 2)
│   │   ├── tester.py          ← run_tester_async, validate_code (Stage 3)
│   │   ├── researcher.py      ← run_researcher_async
│   │   ├── reader.py          ← run_reader_async
│   │   ├── tool.py            ← run_tool_agent_async, execute_project_async
│   │   └── persona.py         ← AI persona chat agent
│   │
│   ├── services/              ← Infrastructure services
│   │   ├── vram_scheduler.py  ← VRAM state tracking + model load/unload
│   │   ├── event_emitter.py   ← WebSocket broadcaster (singleton)
│   │   ├── executor.py        ← Multi-language code runner (Python/Node/Go/Rust/Bash)
│   │   ├── ollama_client.py   ← Ollama API wrapper (streaming + sync)
│   │   ├── sanitizer.py       ← JSON/code output cleaning utilities
│   │   ├── metrics.py         ← Performance metrics recording + queries
│   │   ├── diff.py            ← Code diff recording for autofix loop
│   │   ├── logger.py          ← Structured pipeline logging
│   │   ├── whisper_stt.py     ← Local Whisper speech-to-text
│   │   └── stream.py          ← SSE helpers
│   │
│   ├── schemas/               ← Pydantic data models
│   │   ├── request.py         ← Query, NodeQuery input models
│   │   ├── response.py        ← Response model
│   │   └── task.py            ← Task, TaskStep, TaskBudget, ExecutionResult
│   │
│   └── migrations/            ← DB migration scripts
│
├── frontend/                  ← React/Vite application
│   ├── index.html             ← HTML entry point
│   ├── vite.config.js         ← Vite + proxy config (→ :8000)
│   ├── tailwind.config.js     ← TailwindCSS design tokens
│   ├── package.json           ← Dependencies
│   │
│   └── src/
│       ├── main.jsx           ← React root mount
│       ├── App.jsx            ← Router + route definitions
│       ├── index.css          ← Global CSS + design system
│       │
│       ├── pages/
│       │   ├── LandingPage.jsx ← Home/landing page
│       │   └── Dashboard.jsx   ← Main application shell
│       │
│       ├── components/        ← UI components
│       │   ├── AgentCanvas.jsx        ← ReactFlow visual pipeline
│       │   ├── CustomNode.jsx         ← Individual agent node UI
│       │   ├── NodeInspectorPanel.jsx ← Node detail panel
│       │   ├── NodeSidebar.jsx        ← Drag-and-drop node palette
│       │   ├── SimpleChat.jsx         ← Persona/Agent/Direct chat UI
│       │   ├── AgentChat.jsx          ← Full-featured agent chat
│       │   ├── WorkspaceExplorer.jsx  ← File browser + code viewer
│       │   ├── TimelinePanel.jsx      ← Real-time event log
│       │   ├── PerformanceDashboard.jsx ← Metrics charts
│       │   ├── CustomAgentManager.jsx ← Create/edit custom agents
│       │   ├── VoiceButton.jsx        ← Microphone → Whisper STT
│       │   ├── StatusBar.jsx          ← Bottom status bar
│       │   ├── ChatHistoryPanel.jsx   ← Chat session list sidebar
│       │   ├── CodeDiffViewer.jsx     ← Side-by-side diff viewer
│       │   └── TopClock.jsx           ← Real-time clock in header
│       │
│       ├── store/
│       │   ├── useAgentStore.js            ← Zustand global state (canvas)
│       │   ├── useSimpleChatHistoryStore.js ← Chat session history
│       │   └── useAgentChatHistoryStore.js  ← Agent chat history
│       │
│       └── config/
│           └── agents.js      ← Agent definitions + API base URLs
│
├── prompts/                   ← Markdown prompt files (single source of truth)
│   ├── manager.md             ← Orchestrator / planner prompt
│   ├── coder.md               ← Code generation prompt
│   ├── coder_autofix.md       ← Autofix loop prompt template
│   ├── coder_fix.md           ← Single-pass fix prompt
│   ├── coder_revision.md      ← Revision prompt
│   ├── analyst.md             ← Analysis / explanation prompt
│   ├── critic.md              ← Code review / validation prompt
│   ├── critic_file_review.md  ← File-level review prompt
│   ├── critic_recheck.md      ← Re-validation prompt
│   ├── critic_validation.md   ← Output quality check
│   ├── editor.md              ← Code refinement prompt
│   ├── writer.md              ← Initial code drafting prompt
│   ├── tester.md              ← QA adversarial testing prompt
│   ├── researcher.md          ← Research / explanation prompt
│   ├── reader.md              ← Project analysis prompt
│   ├── tool.md                ← File extraction prompt
│   └── readme.md              ← README auto-generation prompt
│
├── workspace/                 ← Agent-generated project files live here
│   └── <project_id>/
│       ├── main.py            ← Generated code
│       ├── project.json       ← Project metadata
│       └── canvas_history.md  ← Execution history
│
├── docs/                      ← Documentation
├── scripts/                   ← Helper scripts (Ollama model downloads, etc.)
├── start.sh                   ← Launch script (starts backend + frontend)
└── .env                       ← Environment variables
```

---

## 4. Backend — Deep Dive

### 4.1 `main.py` — The API Gateway

**File size:** 1153 lines  
**Purpose:** The single entry point for all HTTP and WebSocket traffic. Acts as a thin routing layer that delegates work to the orchestrator, agents, and services.

#### Key Sections

**FastAPI App Initialization (lines 110–122)**
```python
app = FastAPI(title="AgentForge", description="VRAM-aware multi-agent inference pipeline", version="3.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
```
- The `CORSMiddleware` allows the React frontend (served on a different port) to call the API without CORS errors.

**Startup Event (lines 135–161)**
```python
@app.on_event("startup")
async def startup_sync_registry():
    init_all()           # Initialize all 4 DB domains
    await sync_model_registry()  # Fetch models from Ollama
    # Warm the manager model (llama3.1:8b) so first request is fast
    await client.post("http://localhost:11434/api/generate", json={...keep_alive: "30m"...})
```
On startup: DB tables are created, the Ollama model list is fetched, and the manager model is pre-loaded into VRAM so the first canvas run doesn't pay the cold-start penalty.

**`pipeline_lock` Usage in `/run`**
```python
@app.post("/run")
async def run(body: RunRequest):
    async with pipeline_lock:  # Only ONE pipeline at a time
        ...
```
The global `asyncio.Lock` from `core/orchestrator.py` ensures that only one full pipeline executes at a time — critical for GPU safety.

**Auto-Mode Routing Logic (lines 299–336)**
```python
is_research = any(kw in p for kw in ["explain", "what is", "how does", ...])
is_complex  = any(kw in p for kw in ["build", "create", "implement", "write a", ...])
if is_research and not is_complex:
    mode = "agent"; body.research_mode = True
else:
    mode = "agent" if is_complex else "direct"
```
The "auto" mode inspects the prompt text to decide whether to use the fast direct path or the full agent pipeline.

**`/run-node` Endpoint (lines 402–460)**  
Called by the canvas when a user clicks a single node. Streams the agent's response via WebSocket events and saves code files if the output contains code.

**WebSocket `/ws/agent-stream` (lines 244–255)**  
A persistent WebSocket connection. Clients connect, and the server sends pipeline events (start/update/complete/error) via the `EventEmitter` singleton as they happen during any `/run` call.

**Workspace API (lines 468–607)**  
Full CRUD for files in `/workspace`:
- `GET /workspace` — list all projects + files
- `GET /workspace/{project_id}/{filename}` — read file
- `PUT /workspace/{project_id}/{filename}` — edit/save file
- `DELETE /workspace/{project_id}` — delete project
- `GET /workspace/export/{project_id}` — download as `.zip`
- `POST /workspace/import` — upload a `.zip` to import a project

**Chat API `/agent/{agent_id}/chat` (lines 1026–1070)**  
SSE streaming endpoint. Constructs a prompt by combining the agent's system instruction with the user message, then pipes it through `scheduled_generate()` which handles VRAM allocation.

**Stop API `/stop` (lines 1123–1143)**  
Cancels all active asyncio Tasks and emits `error` WebSocket events to reset the UI.

**Persona Sub-App Mount (line 1150–1152)**
```python
from chat_server import app as chat_app
app.mount("/persona", chat_app)
```
The persona chat server is a completely separate FastAPI app mounted at `/persona`. This isolates its uncensored model choices from the main orchestration pipeline.

---

### 4.2 `config.py` — Model Registry and Routing Config

**Purpose:** Single source of truth for all model assignments, VRAM sizes, fallback chains, and task routing.

```python
MODELS = {
    "manager":  {"name": "llama3.1:8b",       "size_gb": 6.6,  "role": "routing_and_planning"},
    "writer":   {"name": "gpt-oss:20b",        "size_gb": 13.0, "role": "code_generation_draft", "exclusive": True},
    "editor":   {"name": "qwen2.5-coder:14b",  "size_gb": 9.0,  "role": "code_refinement",       "exclusive": True},
    "tester":   {"name": "deepseek-r1:8b",     "size_gb": 5.2,  "role": "qa_validation"},
    "coder":    {"name": "qwen2.5-coder:14b",  "size_gb": 13.0, "role": "code_generation",        "exclusive": True},
    "critic":   {"name": "deepseek-r1:8b",     "size_gb": 5.2,  "role": "validation"},
    "analyst":  {"name": "llama3.1:8b",        "size_gb": 6.6,  "role": "reasoning"},
    "researcher":{"name": "qwen2.5:14b",       "size_gb": 9.0,  "role": "research_and_synthesis", "exclusive": True},
    "heavy":    {"name": "codestral:22b",       "size_gb": 12.0, "role": "architectural_reasoning","exclusive": True, "evicts_pinned": True},
    "reader":   {"name": "llama3.1:8b",        "size_gb": 7.2,  "role": "project_analysis",       "pinned": True},
}

PINNED_MODELS = ["llama3.1:8b"]   # Never unloaded from VRAM

FALLBACK_CHAIN = {
    "qwen2.5-coder:14b": "qwen2.5:14b",
    "gpt-oss:20b":       "qwen2.5-coder:14b",
    "llama3.1:8b":       "deepseek-r1:8b",
    ...
}

TASK_ROUTER = {
    "code_generation": "writer",
    "code_refinement": "editor",
    "debug_complex":   "heavy",
    "research":        "researcher",
    ...
}
```

**Key Concepts:**
- `"exclusive": True` → model needs the entire 16GB VRAM, nothing else can co-run
- `"pinned": True` → model should stay resident in VRAM between requests
- `"evicts_pinned": True` → even pinned models get evicted for this model (e.g., heavy/codestral)
- `FALLBACK_CHAIN` — if a model fails and needs downgrading, follow this chain

---

### 4.3 `core/orchestrator.py` — The Brain

**File size:** 1373 lines  
**Purpose:** The central execution engine. Implements both `run_direct_mode()` and `run_agent_mode()`, plus the 3-stage production pipeline.

#### `run_direct_mode(prompt, session_id, model_override)`
**Target:** < 2 seconds  
**Flow:**
1. Build context from session history
2. Keyword-match prompt → choose `coder` or `analyst` agent
3. Call `run_coder_async()` or `run_analyst_async()` (streaming)
4. Stream chunks to WebSocket via `emitter.emit()`
5. On error, fall back to `deepseek-r1:8b`
6. Store run in SQLite (memory + canvas + metrics)
7. Release model from VRAM

#### `run_agent_mode(prompt, session_id, allow_heavy, research_mode, node_models)`
**Target:** 8–15 seconds  
**Flow:**
1. Call `route_task_async()` → get routing decision + plan
2. Build `Task` Pydantic object with steps
3. **If research route:** Call `run_researcher_async()` directly
4. **If code route:** Call `run_production_pipeline_async()` (3-stage)
5. **Otherwise:** Execute plan steps sequentially for analyst/critic
6. Run `run_tool_agent_async()` to save files to `/workspace`
7. Store metrics, emit completion events

#### `run_production_pipeline_async(prompt, run_id, project_id, emitter, allow_heavy)`
**The 3-Stage Code Pipeline:**

**Stage 1 — WRITER** (`gpt-oss:20b` or `codestral:22b` with Deep Think)
- Produces the initial code draft
- Emits streaming `update` events to WebSocket
- Immediately releases from VRAM after completion

**Stage 2 — EDITOR** (`qwen2.5-coder:14b`)
- Receives the writer's draft + any tester feedback
- Refines/fixes the code
- Max 3 retry attempts if tester rejects

**Stage 3 — TESTER** (`deepseek-r1:8b`)
- Calls `validate_code()` which returns a structured verdict: `{verdict: "PASS"/"FAIL", score: 0-10, bugs: [...], fix_instructions: "..."}`
- If PASS → break the loop
- If FAIL → send `fix_instructions` back to EDITOR

**After pipeline:**
- `run_tool_agent_async()` extracts files from code blocks and saves to `/workspace`
- `_generate_readme_async()` auto-generates a README.md
- Saves `canvas_history.md` to the project directory

#### LATENCY_BUDGETS
```python
LATENCY_BUDGETS = {
    "direct":  2000,   # 2 seconds
    "agent":   15000,  # 15 seconds
    "heavy":   25000,  # 25 seconds for codestral:22b
    "reload":  6000,   # 6 seconds for model reload
}
```

#### `_should_downgrade(model, budget_ms)`
Heuristic: `estimated_latency = size_gb × 1500ms`  
If the model is too large for the budget, return a lighter fallback.

---

### 4.4 `core/router.py` — Task Routing and Planning

**Purpose:** Decides which agent handles a task and creates a multi-step execution plan.

#### `_is_code_task(prompt)` — Fast Path Check
Checks if prompt matches CODE_TRIGGERS (e.g., "hello world", "write a function", "in python"). Short simple code prompts skip the LLM planner entirely.

#### `_deterministic_code_plan(prompt)` — No-LLM Planning
For simple code tasks (< 150 chars, no complexity triggers):
```python
return {
    "goal": prompt[:80],
    "project_id": slug,   # e.g., "hello_world_in_python"
    "steps": [
        {"step": 1, "action": "code",       "agent": "coder"},
        {"step": 2, "action": "save_files", "agent": "tool"},
        {"step": 3, "action": "execute",    "agent": "executor"},
    ]
}
```
This avoids a 6-second LLM planning step for trivial tasks.

#### `plan_task_async(prompt)` — LLM Planner
For complex tasks, calls the manager model (`llama3.1:8b`) with a planner prompt that asks it to output structured JSON:
```json
{
  "goal": "Build a web calculator",
  "project_id": "web_calculator",
  "task_type": "code_generation",
  "confidence": 0.95,
  "steps": [...]
}
```
Uses `extract_json_object()` + `auto_fix_json()` (critic model) to handle malformed JSON.

#### `route_task_async(prompt, research_mode)`
1. Gets a plan from `plan_task_async()`
2. Maps `task_type` → agent name via `TASK_ROUTER`
3. Returns `RouteDecision` + plan steps + project_id

---

### 4.5 `core/memory.py` — Persistent Memory

**Database:** `backend/memory.db` (SQLite)  
**Tables:**
- `runs` — every pipeline run (prompt, route, result, status, latency_ms)
- `fixes` — every autofix attempt (error text, fix code, success flag)
- `patterns` — prompt hash → routing pattern (success/fail counts)

**Key Functions:**
- `store_run()` — saves completed run
- `store_fix()` — saves fix attempt for learning
- `update_pattern()` — increments success/fail counts for routing
- `get_similar_fixes(error)` — keyword search for past fixes (used by autofix loop)
- `get_stats()` — `{total_runs, success_rate, fix_rate}` for dashboard

---

### 4.6 `core/chat_memory.py`

Manages persistent chat sessions for the SimpleChat/AgentChat components.

**Tables:** `chat_sessions`, `chat_messages`  
**Functions:** `create_session()`, `get_session()`, `add_message()`, `get_messages()`, `get_summary()`, `set_summary()`, `delete_session()`

Each session tracks: mode (persona/agent/direct), selected_agent, selected_model, timestamp.

---

### 4.7 `core/canvas_memory.py`

Stores canvas pipeline run history — each run and its per-agent steps.

**Tables:** `canvas_runs`, `canvas_steps`  
**Functions:** `create_run()`, `update_run()`, `add_step()`, `update_step()`, `get_run()`, `get_run_steps()`, `get_recent_runs()`, `get_active_run()`

---

### 4.8 `core/session.py`

Lightweight session state for the `/run` orchestration pipeline.

**Storage:** Dictionary in memory (+ SQLite persistence)  
**Fields:** session_id, context_summary, turn_count, active_mode, created_at  
**Functions:** `create_session()`, `get_session()`, `add_turn()`, `update_session()`, `list_sessions()`

---

### 4.9 `core/context.py`

**`compress_context(text)`** — Summarize long conversation history.  
**`build_context_window(session_ctx, new_prompt)`** — Prepend session summary to new prompt:
```
[Previous context: ...summary...] 

Current task: <user prompt>
```

---

### 4.10 `core/memory_manager.py`

Coordinates initialization and maintenance across all 4 DB domains.

**`init_all()`** — Called on startup; initializes memory, chat_memory, canvas_memory, agent_memory, and metrics tables.

**`get_db_health()`** — Returns DB file size and row counts per table.

**`cleanup_old_data(chat_ttl, metrics_ttl, canvas_ttl)`** — Deletes old records to prevent DB bloat. Called via `POST /memory/cleanup`.

---

### 4.11 `core/prompt_versions.py`

Versioned prompt history stored in SQLite. Allows users to:
- Save new prompt versions via `POST /prompts/{agent_id}/versions`
- Roll back to previous versions via `PUT /prompts/{agent_id}/rollback/{version}`
- View version diffs via `GET /prompts/{agent_id}/diff?from_version=1&to_version=2`

---

### 4.12 `services/vram_scheduler.py` — VRAM Scheduler

**The most architecturally complex service in the project.**

#### Architecture Rules
```
Models < 10GB  →  can co-run with manager (light models)
Models >= 10GB →  need exclusive VRAM (unload everything first)
Pinned models  →  never unloaded unless evicts_pinned model requested
FIFO Lock      →  only one request uses the GPU at a time
```

#### VRAMState Dataclass
```python
@dataclass
class VRAMState:
    total_gb: float = 48.0  # 16GB VRAM + spillover RAM
    used_gb: float = 0.0
    active_models: dict = {}  # name → {size_gb, loaded_at}
```

#### `can_load(model_name)` — The Decision Engine
Returns `(bool, reason_string)`:
1. If already loaded → `True, "already_loaded"` (reuse)
2. If heavy model requested and VRAM not empty → `False, "heavy_model_needs_exclusive_vram"`
3. If a heavy model is loaded → `False, "heavy_model_blocking_vram"`
4. If enough free space → `True, "co-run_ok"`

#### `ensure_model_loaded(model_name)`
Main entry point. Handles:
- Reuse if already loaded
- Call `unload_all()` if heavy model needed
- Call `_free_space_for()` if light model can't fit
- Call `_ollama_load()` to actually load
- Update `vram_state.active_models`

#### `scheduled_generate(model, prompt, stream=True)` — The Safe Inference Gate
```python
async def scheduled_generate(model, prompt, stream=True):
    async with pipeline_lock:
        await ensure_model_loaded(model)    # Step 1: Load
        # Stream response...                # Step 2: Inference
        if info["is_heavy"]:
            await release_model(model)      # Step 3: Auto-release heavy
        record_vram_sample(...)             # Step 4: Log metrics
```
Every agent call goes through this. It is the single choke-point that prevents GPU OOM errors.

#### Ollama API for Load/Unload
- **Load:** `POST /api/generate` with `keep_alive: "5m"` and empty prompt → forces model into VRAM
- **Unload:** `POST /api/generate` with `keep_alive: "0"` → releases from VRAM immediately

---

### 4.13 `services/event_emitter.py` — WebSocket Broadcaster

**20 lines of code, but architecturally critical.**

```python
class EventEmitter:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def emit(self, run_id, node_id, type_str, input_str="", output_str="", metadata=None, error=""):
        event = {
            "event_id": uuid4(), "run_id": run_id, "node_id": node_id,
            "type": type_str,    # "start" | "update" | "complete" | "error"
            "input": input_str,  "output": output_str,
            "error": error,      "metadata": metadata,
            "timestamp": int(time.time() * 1000),
        }
        for ws in self.connections.copy():
            await ws.send_text(json.dumps(event))

emitter = EventEmitter()  # Global singleton
```

Every agent in the pipeline calls `emitter.emit()`. The frontend WebSocket connection receives these events and updates the visual canvas in real-time.

**Event Types:**
- `start` — agent started working
- `update` — streaming output (partial result)
- `complete` — agent finished successfully
- `error` — agent encountered an error

---

### 4.14 `services/executor.py` — Sandboxed Code Runner

**Purpose:** Executes generated code files in an isolated environment.

#### Runner Abstract Class
```python
class Runner(ABC):
    @property
    @abstractmethod
    def language(self) -> str: ...
    
    async def setup(self, project_dir, emit) -> bool: ...
    async def install_deps(self, project_dir, deps, emit) -> None: ...
    async def run(self, project_dir, entry, emit, timeout=60) -> dict: ...
    def detect(self, project_dir, files) -> bool: ...
```

#### Concrete Runners
| Runner | Language | Detection | Run Command |
|---|---|---|---|
| `PythonRunner` | Python | `.py` files | `python3 main.py` in venv |
| `NodeRunner` | JavaScript | `.js/.jsx/.ts` | `node index.js` |
| `GoRunner` | Go | `.go` files | `go run main.go` |
| `RustRunner` | Rust | `.rs` files | `cargo run` |
| `BashRunner` | Bash | `.sh` files | `bash script.sh` |

**PythonRunner details:**
- Creates `.venv` in project directory using `python -m venv`
- Filters standard library modules from `install_deps()` to avoid unnecessary pip calls
- Uses `asyncio.create_subprocess_exec` for non-blocking execution
- Has a `timeout` parameter (default 60s) enforced via `asyncio.wait_for()`

---

### 4.15 `services/ollama_client.py`

Thin wrapper around the Ollama HTTP API.

**`async_generate_stream(model, prompt)`** — yields string chunks (async generator)  
**`async_generate(model, prompt)`** — returns full string response  
**`check_ollama_health()`** — GET `/api/tags`, returns available model list

---

### 4.16 `services/sanitizer.py`

Critical utility for cleaning LLM outputs.

**Functions:**
- `strip_prompt_leakage(text)` — removes repeated prompt text that LLMs sometimes echo back
- `extract_json_object(text)` — finds and parses the first valid JSON object in a string, even with surrounding prose
- `auto_fix_json(raw, error_msg)` — calls the critic model to repair malformed JSON
- `sanitize_file_content(content)` — strips markdown fences, removes preamble lines like "Here is the code..."

---

### 4.17 `services/metrics.py`

Stores and queries performance metrics in SQLite.

**Tables:** `metrics_runs` (per-run data), `metrics_vram` (VRAM snapshots)

**Functions:**
- `record_run(run_id, mode, route, model, latency_ms, tokens, status, session_id)`
- `record_vram_sample(total_gb, used_gb, active_models)`
- `get_overview()` — aggregate stats: total runs, avg latency, success rate
- `get_latency_timeseries()` — recent run latencies for time chart
- `get_vram_timeseries()` — VRAM usage over time
- `get_model_breakdown()` — per-model performance stats
- `get_task_distribution()` — count by task type

---

### 4.18 `services/diff.py`

Records code changes made during the autofix loop.

**`save_diff(project_id, filename, original, patched, attempt)`** — generates unified diff, saves to `backend/diffs/`  
**`get_diffs_for_project(project_id)`** — list all diffs  
**`get_diff(project_id, diff_id)`** — get specific diff content

---

### 4.19 `services/whisper_stt.py`

Local speech-to-text using OpenAI Whisper.

**`transcribe_audio(audio_bytes, content_type)`** — converts audio blob to text  
**`is_whisper_available()`** — checks if whisper package + model is available

The frontend's `VoiceButton` component sends a MediaRecorder audio blob to `POST /transcribe`, which returns `{"text": "...", "model": "whisper-tiny"}`.

---

### 4.20 Agents Directory

Each agent file follows the same pattern:

```python
# Example: agents/coder.py
async def run_coder_async(prompt: str, model_override: str = None):
    model = model_override or MODELS["coder"]["name"]
    system_prompt = coder_prompt()  # Load from /prompts/coder.md
    full_prompt = f"{system_prompt}\n\nTask: {prompt}"
    async for chunk in scheduled_generate(model, full_prompt):
        yield chunk
```

All agents are **async generators** that stream output chunks. This enables real-time UI updates.

| Agent File | Agent Type | Primary Model |
|---|---|---|
| `coder.py` | Code generation | `qwen2.5-coder:14b` |
| `writer.py` | Draft code (Stage 1) | `gpt-oss:20b` |
| `editor.py` | Refine code (Stage 2) | `qwen2.5-coder:14b` |
| `tester.py` | QA validate (Stage 3) | `deepseek-r1:8b` |
| `critic.py` | Review output, validate JSON | `deepseek-r1:8b` |
| `analyst.py` | Explanation + reasoning | `llama3.1:8b` |
| `researcher.py` | Deep research synthesis | `qwen2.5:14b` |
| `reader.py` | Read + analyze project files | `llama3.1:8b` |
| `tool.py` | Extract files, save to workspace | tool-script |
| `persona.py` | Persona chat AI | persona-specific |

---

### 4.21 `chat_server.py` — Persona Sub-App

A completely separate FastAPI application mounted at `/persona`.

**5 Personas:**
| Key | Label | Color | Model |
|---|---|---|---|
| `unhinged_gf` | Unhinged GF 💋 | #ec4899 | `gurubot/girl` |
| `raw_bro` | Raw Bro 🔥 | #f97316 | `gurubot/self-after-dark` |
| `savage_teacher` | Savage Teacher 📚 | #a855f7 | `huihui_ai/qwen3.5-abliterated` |
| `therapist` | Therapist 🧠 | #22c55e | `huihui_ai/qwen3.5-abliterated` |
| `roaster` | Roaster 😈 | #ef4444 | `huihui_ai/qwen3.5-abliterated` |

**Bracket Command System:**  
Users can inject inline commands like `[[system: Be extra formal]] [[memory: User is a student]]`  
Parsed by `_parse_brackets()` regex and applied to the system prompt via `SessionState`.

**`POST /persona/chat`** — Streaming SSE response  
The persona's system prompt + user message → Ollama → SSE chunks → browser

---

### 4.22 Schemas

**`schemas/request.py`:**
```python
class Query(BaseModel):
    prompt: str

class NodeQuery(BaseModel):
    agent_id: str
    prompt: str
    model: Optional[str] = None
```

**`schemas/task.py`:**
```python
class TaskStep(BaseModel):
    step: int
    action: str
    description: str
    agent: str
    status: str = "pending"
    result: Optional[str] = None
    latency_ms: Optional[int] = None

class TaskBudget(BaseModel):
    max_latency_ms: int = 15000
    allow_heavy_model: bool = False

class Task(BaseModel):
    task_id: str
    input: str
    goal: str
    agent: str
    project_id: str = "project"
    budget: TaskBudget
    run_id: str
    steps: List[TaskStep] = []

class ExecutionResult(BaseModel):
    task_id: str
    run_id: str
    mode: str
    route: str
    result: str
    total_latency_ms: int = 0
    status: str = "success"
```

---

## 5. Frontend — Deep Dive

### 5.1 `App.jsx` and `main.jsx`

**`main.jsx`:** Root React mount point.
```jsx
ReactDOM.createRoot(document.getElementById('root')).render(<App />)
```

**`App.jsx`:** Sets up client-side routing using `react-router-dom`:
```jsx
<Routes>
  <Route path="/"         element={<LandingPage />} />
  <Route path="/dashboard" element={<Dashboard />} />
</Routes>
```

---

### 5.2 `pages/LandingPage.jsx`

The home/intro page. Showcases the key features with animated cards and a "Launch IDE" button that navigates to `/dashboard`.

---

### 5.3 `pages/Dashboard.jsx` — The Main UI

**The most complex frontend file (687 lines)**

**Key State:**
```javascript
const [activeTab, setActiveTab] = useState('chat');      // Which panel is showing
const [execMode, setExecMode] = useState('auto');        // auto/direct/agent
const [allowHeavy, setAllowHeavy] = useState(false);    // Deep Think toggle
const [wsStatus, setWsStatus] = useState('disconnected'); // WebSocket state
const [health, setHealth] = useState({...});            // Ollama health
```

**WebSocket Management (lines 148–221):**
- Connects to `ws://localhost/ws/agent-stream`
- Auto-reconnects every 2 seconds on disconnect
- Sends pings every 15 seconds to keep alive
- On message: calls `updateNode()` + `addTimelineEvent()` from Zustand store

```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  storeRef.current.addTimelineEvent(data);
  if (type === 'start')    updateNode(run_id, node_id, { status: 'running', ... });
  if (type === 'update')   updateNode(run_id, node_id, { output });
  if (type === 'complete') updateNode(run_id, node_id, { status: 'success', ... });
  if (type === 'error')    updateNode(run_id, node_id, { status: 'error', error });
};
```

**Health Polling:** Every 15 seconds, fetches `/health` and updates `useAgentStore` with available/configured models.

**`handleQuery(e)`** — Main execution trigger (runs when Enter pressed in top search bar):
```javascript
await fetch('/run', {
  method: 'POST',
  body: JSON.stringify({
    prompt, mode: execMode, allow_heavy: allowHeavy, node_models: nodeModels
  })
})
```

**Sidebar Navigation:** Animated collapsible sidebar with 6 tabs:
| Tab | Component | Icon |
|---|---|---|
| Agent Chat | `AgentChat` | MessageSquare |
| Chat | `SimpleChat` | MessageCircle |
| Canvas | `AgentCanvas` | Network |
| Files | `WorkspaceExplorer` | FolderTree |
| Metrics | `PerformanceDashboard` | BarChart3 |
| Agents | `CustomAgentManager` | Users |

**Timeline Panel:** Resizable (drag handle) showing `TimelinePanel` on the right of the canvas.

---

### 5.4 `components/AgentCanvas.jsx`

**Purpose:** Visual representation of the agent pipeline as a directed graph.

**Technology:** `@xyflow/react` (ReactFlow v12)

**INITIAL_NODES (9 nodes):**
| Node ID | Label | Position |
|---|---|---|
| `input` | User Input | (50, 300) |
| `manager` | Orchestrator | (300, 300) |
| `writer` | Senior Coder | (650, 100) |
| `editor` | Code Editor | (650, 250) |
| `tester` | QA Tester | (650, 400) |
| `researcher` | Researcher | (650, 550) |
| `heavy` | System Architect | (950, 600) |
| `tool` | Tool Mgr | (1000, 250) |
| `executor` | Executor | (1250, 250) |

**INITIAL_EDGES:** Connect nodes showing the pipeline flow. The `e-t-e` edge (tester → editor) has `animated: true` to show the feedback loop.

**Key Behaviors:**
- **Node State Sync:** `useEffect` watches `nodesState` from Zustand store, updates ReactFlow node `stateData` whenever agent events arrive via WebSocket
- **Edge Animation:** Active edges glow with color-coded drop-shadows (blue for manager, purple for writer, pink for editor, yellow for tester, green for researcher)
- **Drag-and-Drop:** New nodes can be dragged from `NodeSidebar` and dropped onto the canvas
- **Delete Key:** Selected node deleted with Backspace/Delete
- **Fullscreen:** Toggle button in top-right corner

---

### 5.5 `components/CustomNode.jsx`

**Purpose:** The visual representation of each agent in the canvas (14429 bytes — complex component).

Each node shows:
- Agent icon and label
- Model name badge
- Status indicator (idle/running/success/error) with color coding
- Output preview (last 200 chars of agent output)
- metadata (latency_ms, tokens)
- "Run" button for direct single-node execution

**Status Colors:**
- `idle` → grey border
- `running` → blue glow + pulsing animation
- `success` → green border
- `error` → red border

---

### 5.6 `components/NodeInspectorPanel.jsx`

A panel that appears when a node is selected on the canvas. Shows:
- Full agent output with syntax highlighting
- Editable prompt field for direct node execution
- Model override selector (overrides the default for this node in the next run)
- Latency + token count metadata

---

### 5.7 `components/NodeSidebar.jsx`

A drag-and-drop palette of available agent node types. Users drag nodes onto the canvas to build custom pipelines. Shows both built-in agents and custom agents from the store.

---

### 5.8 `components/SimpleChat.jsx`

**Purpose:** Versatile chat interface with 3 modes (878 lines — largest component).

**Chat Modes:**
| Mode | Endpoint | Description |
|---|---|---|
| `persona` | `POST /persona/chat` | Persona characters (Unhinged GF, Raw Bro, etc.) |
| `agent` | `POST /agent/{id}/chat` | Direct chat with a specific AI agent |
| `direct` | `POST /agent/manager/chat` | Bare LLM without agent persona |

**Key State:**
- `chatMode` — "persona" / "agent" / "direct"
- `selectedPersona` — active persona (with color, icon)
- `selectedAgent` — active agent (from agents config)
- `selectedModel` / `directModel` — active Ollama model
- `isStreaming` — whether response is actively streaming
- `sessionId` — backend session ID for persistence

**Streaming Logic (SSE):**
```javascript
const reader = res.body.getReader();
while (true) {
  const { done, value } = await reader.read();
  const lines = text.split('\n').filter(l => l.startsWith('data: '));
  for (const line of lines) {
    const data = JSON.parse(line.slice(6));
    if (data.chunk) {
      fullText += data.chunk;
      updateLastMessage(msg => ({ ...msg, content: fullText }));
    }
  }
}
```

**Prompt Editor:** Inline modal to customize any agent's or persona's system prompt. Changes are stored locally and sent as `custom_prompt` in the API call.

**Markdown Rendering:** Uses `react-markdown` + `react-syntax-highlighter` with VSCode Dark+ theme for code blocks.

---

### 5.9 `components/AgentChat.jsx`

A more feature-rich chat interface focused on development tasks. Supports:
- Session history
- Model selection per message
- Canvas run history viewing
- Code diff viewing
- Project file browsing inline

---

### 5.10 `components/WorkspaceExplorer.jsx`

**Purpose:** File manager for the `/workspace` directory.

Features:
- Tree view of all projects and files
- Click file to view content with syntax highlighting
- Inline editor (PUT `/workspace/{project}/{file}`)
- Delete project/file
- Download as ZIP (GET `/workspace/export/{project_id}`)
- Upload ZIP (POST `/workspace/import`)
- Run project (POST `/execute/{project_id}`)
- Autofix run (POST `/execute/{project_id}/autofix`)

---

### 5.11 `components/TimelinePanel.jsx`

A real-time event log showing each WebSocket event as a timeline entry. Events are color-coded by type (blue=start, yellow=update, green=complete, red=error). Supports filtering and clearing.

---

### 5.12 `components/PerformanceDashboard.jsx`

Fetches from metrics endpoints and renders charts using `recharts` or CSS bars:
- `/metrics/overview` — KPI cards (total runs, avg latency, success rate)
- `/metrics/latency` — Latency over time line chart
- `/metrics/vram` — VRAM usage area chart
- `/metrics/models` — Per-model bar chart
- `/metrics/tasks` — Task type pie/donut chart

---

### 5.13 `components/CustomAgentManager.jsx`

CRUD UI for custom agents stored in `backend/custom_agents.json`.

Form fields: Name, Model, System Prompt (textarea), Color, Icon  
After creation, agents appear in the NodeSidebar for dragging onto the canvas, and in SimpleChat's agent list.

---

### 5.14 `components/VoiceButton.jsx`

Uses the browser's `MediaRecorder` API to capture microphone audio.

```javascript
const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
mediaRecorder.onstop = async () => {
  const blob = new Blob(audioChunks, { type: 'audio/webm' });
  const formData = new FormData();
  formData.append('file', blob, 'audio.webm');
  const res = await fetch('/transcribe', { method: 'POST', body: formData });
  const { text } = await res.json();
  onTranscript(text);  // Callback to set input field
};
```

---

### 5.15 `components/StatusBar.jsx`

Fixed bottom bar showing:
- Ollama connection status
- WebSocket status
- Total runs, success rate, fix rate (from `/memory/stats`)
- Whether system is actively processing

---

### 5.16 `components/ChatHistoryPanel.jsx`

A collapsible sidebar showing previous chat sessions from Zustand store. Supports switching sessions and creating new ones.

---

### 5.17 `components/CodeDiffViewer.jsx`

Side-by-side diff viewer for showing code changes made during the autofix loop. Fetches from `/workspace/{project_id}/diffs/{diff_id}`.

---

### 5.18 `store/useAgentStore.js`

**Zustand global store — the shared state between Dashboard, Canvas, and Timeline.**

Key state slices:
```javascript
{
  nodesState: {},      // {nodeId: {status, input, output, error, metadata}}
  executionLog: [],    // Array of WebSocket events for TimelinePanel
  projects: [],        // Workspace project list
  canvasRuns: [],      // Recent canvas run history
  chatSessions: [],    // Recent chat sessions
  availableModels: [], // Models from /health
  configuredModels: {}, // Agent→model mapping
  customAgents: [],    // From custom_agents.json
  canvasNodeModels: {}, // Per-node model overrides from NodeInspector
  selectedNodeId: null, // Currently selected canvas node
  activeRunId: null,   // Current pipeline run ID
}
```

Key actions:
- `updateNode(run_id, node_id, patch)` — merge patch into `nodesState[node_id]`
- `addTimelineEvent(event)` — prepend to `executionLog`
- `setSelectedNode(id)` — update selected node
- `resetAll()` — reset all node states to idle

---

### 5.19 `store/useSimpleChatHistoryStore.js`

Zustand store for SimpleChat sessions. Persists to `localStorage`.

```javascript
{
  sessions: [],        // Array of {id, mode, persona, agent, model, messages}
  activeSessionId: null,
  createSession(mode, persona, agent, model, directModel),
  setActiveSession(id),
  addMessage(msg),
  updateLastMessage(updater),
  deleteSession(id),
  setSessionMessages(msgs),
  updateSessionMeta(patch),
}
```

---

### 5.20 `store/useAgentChatHistoryStore.js`

Similar to SimpleChat history but for the AgentChat component. Stores agent-specific conversation sessions.

---

### 5.21 `config/agents.js`

Central agent configuration for the frontend.

```javascript
const AGENTS = [
  { id: "manager",    label: "Orchestrator",   color: "#58a6ff", icon: BrainCircuit, model: "llama3.1:8b" },
  { id: "coder",      label: "Coder",           color: "#a371f7", icon: Code,        model: "qwen2.5-coder:14b" },
  { id: "analyst",    label: "Analyst",         color: "#3fb950", icon: BarChart3,   model: "llama3.1:8b" },
  { id: "critic",     label: "Critic",          color: "#d29922", icon: Shield,       model: "deepseek-r1:8b" },
  { id: "researcher", label: "Researcher",      color: "#58a6ff", icon: Globe,        model: "qwen2.5:14b" },
  { id: "reader",     label: "Reader",          color: "#79c0ff", icon: BookOpen,     model: "llama3.1:8b" },
  { id: "qa",         label: "QA Engineer",     color: "#ffa657", icon: TestTube,     model: "deepseek-r1:8b" },
];

export const API      = "";          // Empty → uses Vite proxy to :8000
export const CHAT_API = "/persona";  // Persona sub-app
```

The `loadAgentPrompts()` function fetches `GET /prompts` and populates frontend prompt state.

---

### 5.22 `index.css`

**18,980 bytes** of carefully crafted styling.

**CSS Custom Properties (Design Tokens):**
```css
:root {
  --canvas: #0d1117;
  --canvas-subtle: #161b22;
  --fg-default: #c9d1d9;
  --fg-muted: #8b949e;
  --fg-subtle: #6e7681;
  --accent: #58a6ff;
  --success: #3fb950;
  --danger: #f85149;
  --attention: #d29922;
  --stroke-1: #30363d;
  --stroke-2: #21262d;
}
```

**Custom Animations:**
- `animate-float` — gentle floating animation for idle state icons
- `gradient-bg-animated` — slowly shifting background gradient
- `aurora-line` — a glowing aurora line under the top header
- `ambient-orb-*` — 3 large blurred colored orbs behind content
- `glass-strong` — glassmorphism effect with backdrop-blur
- `glow-accent` — blue glow box-shadow on active elements

---

## 6. Prompts Directory

All prompts are `.md` files loaded at runtime via `core/prompts/__init__.py`.

| File | Used By | Purpose |
|---|---|---|
| `manager.md` | Router planner | Asks model to output structured JSON execution plan |
| `coder.md` | Coder agent | Code generation with Hybrid JSON output format |
| `coder_autofix.md` | Autofix loop | Fix code given error output and memory hints |
| `coder_fix.md` | Single-pass fix | Fix specific bug in code |
| `coder_revision.md` | Revision cycle | Improve code based on feedback |
| `writer.md` | Writer agent (Stage 1) | Produce comprehensive initial code draft |
| `editor.md` | Editor agent (Stage 2) | Refine and improve the writer's draft |
| `tester.md` | Tester agent (Stage 3) | Adversarial QA — find bugs, output JSON verdict |
| `critic.md` | Critic agent | Code review and quality validation |
| `critic_file_review.md` | Critic (file review) | Review existing project files |
| `critic_recheck.md` | Critic (recheck) | Re-validate after fixes |
| `critic_validation.md` | Critic (output check) | Validate output quality |
| `analyst.md` | Analyst agent | Explain concepts and analyze code |
| `researcher.md` | Researcher agent | Deep research and synthesis |
| `reader.md` | Reader agent | Read and understand project files |
| `tool.md` | Tool agent | Extract file structure as JSON |
| `readme.md` | Auto-README | Generate README.md for projects |

---

## 7. End-to-End Data Flow

### Flow 1: User types "write hello world in python" → Canvas

```
1. User types in Dashboard top search bar + hits Enter
2. Dashboard.handleQuery() → POST /run {prompt, mode: "auto", allow_heavy: false}
3. main.py route_task() → AUTO mode: detects "hello world" as complex code task
4. Task enters pipeline_lock (asyncio.Lock)
5. orchestrator.run_agent_mode() called
6. router.route_task_async() → _is_code_task() → True (short, matches CODE_TRIGGERS)
   → returns _deterministic_code_plan() (no LLM needed for planning)
   → route = "coder", project_id = "hello_world_in_python"
7. emitter.emit(run_id, "manager", "start") → WebSocket → Canvas "manager" node turns blue
8. route == "coder" → run_production_pipeline_async()
9. STAGE 1: emitter.emit(run_id, "writer", "start") → Canvas "writer" node turns blue  
   → run_writer_async(prompt, model="gpt-oss:20b")
   → vram_scheduler.scheduled_generate() → ensure_model_loaded("gpt-oss:20b")
   → Ollama loads model → streams response chunks
   → Each chunk: emitter.emit("writer", "update", output_str=partial_code)
   → Canvas "writer" node shows streaming output
   → Writer done: emitter.emit("writer", "complete")
   → release_model("gpt-oss:20b")
10. STAGE 2: emitter.emit("editor", "start") → Canvas "editor" node turns blue
    → run_editor_async(prompt, draft_output)
    → Streams refinements
11. STAGE 3: emitter.emit("tester", "start") → Canvas "tester" node turns blue
    → validate_code(prompt, refined_output) → {verdict: "PASS", score: 9}
    → PASS → break loop
12. run_tool_agent_async() → parse code blocks from refined_output
    → extract main.py, requirements.txt → write to /workspace/hello_world_in_python/
    → emitter.emit("tool", "complete", files_created: 2)
13. execute_project_async() → PythonRunner.setup() → create .venv
    → install_deps() → run() → stdout: "Hello, World!\n"
    → emitter.emit("executor", "complete", "Success: Hello, World!")
14. run_id stored in: memory.db (runs table), canvas_memory (canvas_runs + canvas_steps)
    → metrics recorded
15. POST /run returns ExecutionResult {status:"success", result:...}
16. Timeline panel shows all events in sequence
```

### Flow 2: User sends message in SimpleChat (Persona mode)

```
1. User types in SimpleChat textarea + hits Enter
2. sendMessage() → POST /persona/chat {message, persona: "raw_bro", session_id}
3. chat_server.py chat() handler:
   → _process_brackets() strips [[system:...]] commands
   → Builds full_prompt = persona_system + "User: " + message
   → ollama_stream("gurubot/self-after-dark", full_prompt)
4. SSE chunks streamed back to browser
5. SimpleChat reader loop: reads chunks, calls updateLastMessage()
6. Cursor blink animation shows streaming state
7. When done: updateLastMessage(msg => ({...msg, streaming: false}))
```

### Flow 3: Voice Input

```
1. VoiceButton: User clicks mic → navigator.mediaDevices.getUserMedia({audio: true})
2. MediaRecorder starts, collects audio chunks
3. User clicks again to stop
4. blob = new Blob(audioChunks, {type: "audio/webm"})
5. FormData → POST /transcribe
6. whisper_stt.transcribe_audio(audio_bytes) → Whisper model processes
7. Returns {"text": "write a calculator in python"}
8. onTranscript callback → setInput(text) in Dashboard or SimpleChat
```

---

## 8. Key Design Patterns

### Pattern 1: Async Generator Streaming
Every agent uses `async def run_X_async() → AsyncGenerator[str, None]`:
```python
async for chunk in run_coder_async(prompt):
    result += chunk
    await emitter.emit(run_id, "coder", "update", output_str=result)
```

### Pattern 2: FIFO Pipeline Lock
```python
# Only one pipeline at a time — prevents GPU memory conflicts
pipeline_lock = asyncio.Lock()  # In orchestrator.py
async with pipeline_lock:
    ...execute pipeline...
```

### Pattern 3: Event-Driven UI (WebSocket → Zustand → React)
```
Backend emitter.emit() 
  → WebSocket broadcast 
  → Dashboard ws.onmessage() 
  → useAgentStore.updateNode() 
  → AgentCanvas and CustomNode re-render
```

### Pattern 4: SSE Streaming for Chat
```
Backend StreamingResponse(stream_gen(), media_type="text/event-stream")
  → SSE chunks: "data: {\"chunk\": \"Hello\"}\n\n"
  → Frontend ReadableStream reader
  → updateLastMessage() for live typing effect
```

### Pattern 5: Multi-Layer JSON Fallback (Tool Agent)
```
1. ---JSON--- markers (fastest)
2. Raw JSON parse entire prompt
3. JSON wrapped in ```json...``` markdown block
4. Regex extract all ```lang...``` code blocks → map to files
5. LLM AI parser (slowest, most reliable)
```

### Pattern 6: Self-Correcting Autofix Loop
```
execute_project_async() 
  → error detected 
  → get_similar_fixes(error) from SQLite 
  → build fix_prompt with past fixes as hints
  → run_coder_async(fix_prompt) 
  → save patched file 
  → execute_project_async() again (max 2 retries)
```

### Pattern 7: VRAM Exclusive Access Gate
```
Heavy model (>= 8.5GB):
  can_load() returns False if anything is loaded
  → unload_all()
  → load heavy model exclusively
  → after use: release_model()

Light model (< 8.5GB):
  can co-run with other light models
  → check free_gb >= model_size
  → load if fits
```

---

## 9. Scripts and Start Files

### `start.sh`
```bash
#!/bin/bash
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
cd frontend && npm run dev
```

Starts both backend (port 8000) and frontend (Vite dev server, port 5173).

### `vite.config.js` Proxy
```javascript
server: {
  proxy: {
    '/api': 'http://localhost:8000',
    '/ws':  { target: 'ws://localhost:8000', ws: true },
    '/run': 'http://localhost:8000',
    '/health': 'http://localhost:8000',
    ...
  }
}
```
Proxies all backend API calls through Vite so the frontend can use relative URLs (no CORS issues in development).

### `scripts/` Directory
Contains Ollama model download automation scripts — useful for setting up the project on a new machine.

---

## 10. 100+ Viva Questions and Answers

---

### 🔷 SECTION A — Project Overview & Architecture

**Q1. What is AgentForge Multi-Agent IDE?**  
A: It is a fully offline, local-first AI-powered IDE that uses multiple LLMs running via Ollama to collaboratively plan, write, review, test, and execute code without any cloud dependency.

**Q2. What is the technology stack?**  
A: Backend: Python + FastAPI + SQLite. Frontend: React + Vite + Zustand + ReactFlow. AI runtime: Ollama. Communication: WebSocket (events) + SSE (chat streaming).

**Q3. What is Ollama and why is it used?**  
A: Ollama is a local LLM server that manages downloading, managing, and running open-source models like Llama, Qwen, and DeepSeek on consumer hardware. It exposes a REST API on port 11434. The project uses it so no API key or internet is needed.

**Q4. What are the two execution modes?**  
A: Direct Mode (<2s): single model response, skips pipeline. Agent Mode (<15s): full multi-agent pipeline with Writer→Editor→Tester stages.

**Q5. What does VRAM-aware mean in this context?**  
A: The system tracks GPU memory (VRAM) usage and ensures models are loaded/unloaded to prevent Out-of-Memory errors. Large models get exclusive access; smaller ones can co-run.

**Q6. What is the role of the pipeline lock?**  
A: `asyncio.Lock()` ensures only one pipeline executes at a time on the GPU. This prevents race conditions where two pipelines simultaneously try to load competing models into limited VRAM.

**Q7. How many agents are in the system?**  
A: 10 agents: Manager/Router, Writer, Editor, Tester, Coder, Critic, Analyst, Researcher, Reader, Tool.

**Q8. What is the workspace directory?**  
A: `/workspace` at the project root is where agent-generated code files are saved. Each task creates a subdirectory named after the `project_id` (slugified from the prompt).

---

### 🔷 SECTION B — Backend Concepts

**Q9. What is FastAPI and why was it chosen?**  
A: FastAPI is a modern Python web framework that automatically generates OpenAPI docs, natively supports async/await, and handles Pydantic model validation. It was chosen for high performance, native async support needed for LLM streaming, and WebSocket support.

**Q10. What is the difference between `async def` and `def` in FastAPI endpoints?**  
A: `async def` allows the endpoint to `await` coroutines without blocking the event loop. Regular `def` runs in a thread pool. For LLM calls that can take 10-30 seconds, `async def` is essential to serve concurrent requests.

**Q11. What is an async generator in Python?**  
A: A function with `async def` and `yield` statements. Example: `async def stream(): async for chunk in ollama: yield chunk`. All agents use this pattern to stream text chunks as they arrive from Ollama.

**Q12. What is SSE (Server-Sent Events)?**  
A: A standard HTTP-based protocol where the server sends a stream of `data: ...\n\n` lines to the client over a single long-lived connection. Used for chat streaming in this project. Unlike WebSocket, SSE is unidirectional (server→client only).

**Q13. What is a WebSocket and how is it different from HTTP?**  
A: WebSocket is a full-duplex persistent connection established by HTTP upgrade. Unlike HTTP which is request-response, WebSocket allows both sides to send messages at any time. Used here to broadcast live pipeline events to the canvas.

**Q14. Explain the EventEmitter and how it broadcasts updates.**  
A: The `EventEmitter` class maintains a list of connected WebSockets. When `emitter.emit()` is called by any agent, it serializes a JSON event and calls `ws.send_text()` for every connected client. It's a global singleton imported everywhere.

**Q15. What is Pydantic and how is it used?**  
A: Pydantic is a Python library for data validation using type annotations. FastAPI uses it for request/response models. Models like `RunRequest`, `Task`, `ExecutionResult` are Pydantic BaseModels that auto-validate incoming JSON.

**Q16. How does the SQLite database work in this project?**  
A: `memory.db` is a single SQLite file with multiple tables across 4 domains. The `_get_conn()` function creates a connection with `row_factory = sqlite3.Row` (enables dict-like access). All functions use try/finally to ensure connection closure.

**Q17. What are the 4 memory domains?**  
A: (1) Core memory: runs/fixes/patterns. (2) Chat memory: sessions/messages/summaries. (3) Canvas memory: canvas_runs/canvas_steps. (4) Agent memory: per-agent knowledge/patterns/fixes. Plus metrics tables.

**Q18. How does the autofix loop work?**  
A: `autofix_loop_async()` runs up to `max_retries` times. Each iteration: execute project → capture error → query SQLite for similar past fixes → build fix prompt with memory hints → call coder → patch the file → loop. Saves each fix attempt to SQLite for learning.

**Q19. What is the CORS middleware and why is it needed?**  
A: Cross-Origin Resource Sharing. Browsers block requests from `http://localhost:5173` (Vite) to `http://localhost:8000` (FastAPI) by default. The `CORSMiddleware` with `allow_origins=["*"]` adds headers that tell browsers these cross-origin requests are allowed.

**Q20. What is `keep_alive` in Ollama API calls?**  
A: A parameter that tells Ollama how long to keep a model loaded in VRAM after a request. `keep_alive: "5m"` keeps it warm for 5 minutes. `keep_alive: "0"` immediately unloads. Used by the VRAM scheduler to control memory.

**Q21. Explain the fallback chain in config.py.**  
A: If a primary model fails or is too large for the latency budget, the system downgrades to a lighter model. Example: `gpt-oss:20b → qwen2.5-coder:14b → qwen2.5:14b → llama3.1:8b`. This ensures the pipeline never completely fails.

**Q22. What is `asyncio.gather()` and where is it used?**  
A: `asyncio.gather()` runs multiple coroutines concurrently. In `vram_scheduler.unload_all()`, it calls `_ollama_unload()` for all loaded models simultaneously instead of sequentially, saving time.

**Q23. What is the `pipeline_lock` and how does it prevent GPU conflicts?**  
A: It is an `asyncio.Lock()` object. `async with pipeline_lock:` blocks any other coroutine from entering until the current one exits. Since only one block of code can hold the lock at a time, the GPU is never shared between two inference calls.

**Q24. What does `zipfile.ZipFile` do and where is it used?**  
A: Python's builtin library for creating/extracting zip archives. Used in `export_project()` endpoint to pack all project files into a downloadable `.zip`, and in `import_project()` to extract an uploaded `.zip` into the workspace.

**Q25. How does the autofix loop use memory to improve over time?**  
A: `get_similar_fixes(error_snippet)` does a keyword search in the `fixes` table for past successful fixes with similar error messages. These are prepended to the fix prompt so the coder knows what worked before. MD5 hashing of prompt patterns also tracks routing success.

---

### 🔷 SECTION C — VRAM Scheduler

**Q26. What is VRAM?**  
A: Video RAM — the dedicated memory on a GPU. LLM inference loads model weights into VRAM. Running a 14B parameter model requires approximately 9GB of VRAM. The project targets an RTX 5070 Ti with 16GB VRAM.

**Q27. What is the HEAVY_THRESHOLD_GB?**  
A: 8.5GB. Models at or above this size are classified as "heavy" and require exclusive VRAM access. Models below can potentially co-run with others.

**Q28. Explain the `VRAMState` dataclass.**  
A: Tracks: `total_gb` (16GB), `used_gb` (sum of loaded models), and `active_models` dict (name → {size_gb, loaded_at}). Has computed properties `free_gb` and `has_heavy_model`. Single global instance `vram_state`.

**Q29. What are the 3 rules in `can_load()`?**  
A: Rule 1: Heavy models need completely empty VRAM. Rule 2: If any heavy model is loaded, nothing else can load. Rule 3: Light models can load if `used_gb + model_size <= total_gb`.

**Q30. How does `_free_space_for()` decide which model to evict?**  
A: Sorts loaded models by `loaded_at` (oldest first) and unloads them until there's enough space. Pinned models (llama3.1:8b) are skipped unless an `evicts_pinned` model is requested.

**Q31. What is model warm-up and why is it done at startup?**  
A: Sending a minimal `prompt: ""` request to Ollama loads the model weights from disk into VRAM. Warming the manager model (`llama3.1:8b`) at startup means the first canvas run doesn't pay the 30-60 second cold-load penalty.

**Q32. How is `release_model()` different from unloading?**  
A: `release_model()` is explicit post-use cleanup: it updates `vram_state` (removes from dict, subtracts GB) and calls `_ollama_unload()`. Normal Ollama unload just releases kernel-side; the VRAMState tracker needs the explicit update to keep consistent.

**Q33. What happens when a heavy model is requested during an active run?**  
A: The pipeline lock ensures another pipeline can't start while one is running. When the orchestrator requests a heavy model, `ensure_model_loaded()` calls `unload_all()` first (even evicting pinned models), then loads the heavy model exclusively.

---

### 🔷 SECTION D — Frontend Concepts

**Q34. What is React and what is JSX?**  
A: React is a JavaScript library for building component-based UIs. JSX is a syntax extension that lets you write HTML-like code inside JavaScript. Vite compiles JSX to regular `React.createElement()` calls.

**Q35. What is Vite?**  
A: A frontend build tool. In dev mode, it serves files with HMR (Hot Module Replacement) — changes reflect instantly without page reload. It also proxies API calls to the backend on port 8000.

**Q36. What is Zustand and why was it chosen over Redux?**  
A: Zustand is a minimalist state management library. Unlike Redux, it requires no boilerplate (no actions/reducers/dispatch). Store state is accessed directly: `useAgentStore.getState().updateNode(...)`. Chosen for simplicity in a fast-moving project.

**Q37. What is ReactFlow?**  
A: A React library for building node-based editors (flowcharts, diagrams). Provides draggable nodes, animated edges, zoom/pan, and hooks for programmatic control. Used for the visual agent canvas.

**Q38. Explain the `useEffect` used for WebSocket connection in Dashboard.**  
A: On mount (empty dependency array `[]`), establishes a WebSocket connection. On each message, parses JSON and calls `updateNode()` / `addTimelineEvent()`. On disconnect, schedules a reconnect after 2 seconds. On unmount (cleanup function), closes the socket.

**Q39. What is Framer Motion and where is it used?**  
A: An animation library for React. Used throughout Dashboard for `<AnimatePresence>` (fade transitions between tabs), `<motion.div>` for sidebar slide animation, and `<motion.button>` for scale + whileHover effects.

**Q40. What is TailwindCSS?**  
A: A utility-first CSS framework where styles are applied as class names (e.g., `flex items-center gap-2 text-sm`). The project uses it for layout and spacing, but relies on `index.css` custom properties for the color theme.

**Q41. What is the Vite proxy and how does it help?**  
A: In `vite.config.js`, paths like `/run`, `/health`, `/ws` are proxied to `http://localhost:8000`. This means the frontend can use `fetch('/run', ...)` without specifying host/port, avoiding CORS issues during development.

**Q42. What is `useRef` and how is it used in Dashboard?**  
A: `useRef` creates a mutable object that persists across renders without causing re-renders. Used for: `wsRef` (WebSocket connection), `searchInputRef` (focus input programmatically), `storeRef` (stable reference to store functions avoiding stale closure).

**Q43. Explain Server-Sent Events (SSE) flow in SimpleChat.**  
A: `fetch()` returns a response with a readable stream body. A `ReadableStreamDefaultReader` reads chunks. Each chunk contains SSE lines like `data: {"chunk": "Hello"}\n\n`. The code splits by newlines, filters for `data:` prefix, parses JSON, and appends `data.chunk` to the message content.

**Q44. What is `react-markdown` and `react-syntax-highlighter`?**  
A: `react-markdown` renders Markdown text as React elements (headings, lists, code blocks). `react-syntax-highlighter` applies language-specific syntax coloring to code blocks using the VSCode Dark+ theme (`vscDarkPlus`).

**Q45. How does the canvas node color animation work?**  
A: In `AgentCanvas.jsx`, `useEffect` watches `nodesState`. Based on each node's status, edge styles are updated: `animated: true` for running edges, colored `stroke` with CSS `filter: drop-shadow()` for active edges, and dim grey for inactive ones.

**Q46. What is `localStorage` and how is it used?**  
A: Browser storage that persists across page reloads. Zustand's `persist` middleware (in `useSimpleChatHistoryStore`) serializes the store to `localStorage` so chat history survives page refreshes.

---

### 🔷 SECTION E — Agent Pipeline Theory

**Q47. What is an LLM (Large Language Model)?**  
A: A neural network trained on massive text datasets that can generate human-quality text. It predicts the next token given previous context. Models like Llama, Qwen, and DeepSeek are local LLMs that run on consumer GPUs.

**Q48. Why use multiple agents instead of one large model?**  
A: Specialization — each model is tuned for its role. Writer uses a creative large model; Editor uses a code-focused model; Tester uses a reasoning model. This produces better results than one model doing everything. Also, smaller specialized models fit in VRAM simultaneously.

**Q49. What is prompt engineering?**  
A: The practice of crafting system prompts that guide LLM behavior. The `.md` files in `/prompts/` are carefully written instructions that define each agent's persona, output format, constraints, and examples.

**Q50. What is a system prompt?**  
A: An instruction prepended to a conversation that sets the LLM's behavior and persona. E.g., the tester's system prompt says "You are an adversarial QA engineer. Output a JSON verdict with bugs found."

**Q51. What is token streaming and why does it matter for UX?**  
A: LLMs generate text token-by-token. Rather than waiting for the full response (10-30 seconds), streaming sends each token as it's generated, creating a "typing" effect. This dramatically improves perceived responsiveness.

**Q52. Explain the 3-stage production pipeline.**  
A: Stage 1 (Writer): creates comprehensive initial draft using largest model. Stage 2 (Editor): refines for correctness, style, edge cases. Stage 3 (Tester): adversarial QA — returns PASS/FAIL verdict. If FAIL, instructions sent back to Editor (max 3 retries).

**Q53. What is the "Deep Think" mode?**  
A: When `allow_heavy: true` is sent, the Writer stage swaps to `codestral:22b` (22B params, 12GB VRAM) for more sophisticated architectural reasoning. Adds ~10 seconds to pipeline but produces better results for complex tasks.

**Q54. Why does the tool agent have multiple fast-path strategies?**  
A: LLM output parsing is unreliable. Some models output clean JSON, others wrap it in markdown, others put it inside `---JSON---` markers. The multi-tier parsing strategy (4 fast paths before LLM fallback) ensures the system handles all these cases without unnecessary LLM calls.

**Q55. What is the critic/auto-fix JSON feature?**  
A: If `extract_json_object()` fails (malformed JSON), `auto_fix_json()` calls the critic model (`deepseek-r1:8b`) with the broken JSON and asks it to repair it. This adds resilience to the parsing pipeline.

**Q56. What is RAG (Retrieval Augmented Generation)?**  
A: A technique that retrieves relevant documents/data and injects them into the LLM prompt. This project uses a simplified version: `get_similar_fixes()` retrieves past error fixes from SQLite and adds them to the repair prompt. A full RAG system would use embeddings + vector database.

**Q57. What is a system routing decision based on keyword matching?**  
A: The auto-mode in `/run` checks the prompt for keywords manually. `is_research = "explain" in p or "what is" in p`. This deterministic approach is faster than asking an LLM to decide, and more reliable for well-defined inputs.

**Q58. What is the model fallback chain purpose?**  
A: When a model fails (network error, timeout, OOM), the system tries the next lighter model in `FALLBACK_CHAIN` / `MODEL_DOWNGRADES`. This ensures the pipeline always produces output even when primary models are unavailable.

**Q59. Why are writer and editor DIFFERENT models?**  
A: Using the same model for drafting and editing creates "self-review bias" — the model tends to approve its own output without finding flaws. Different models have different training, so the editor can genuinely critique the writer's code.

---

### 🔷 SECTION F — Code Execution / Workspace

**Q60. How is Python code executed safely?**  
A: `PythonRunner` creates a virtual environment (`.venv`) inside the project directory, installs dependencies with `pip install`, and runs the entry point using `asyncio.create_subprocess_exec()` with a timeout. stdin is set to DEVNULL to prevent hanging on input prompts.

**Q61. What is `asyncio.create_subprocess_exec()`?**  
A: An async version of subprocess creation. Returns a `Process` object. `await proc.communicate()` returns stdout and stderr. `asyncio.wait_for(communicate(), timeout=60)` terminates if it takes too long.

**Q62. How does the system detect which programming language to use?**  
A: `detect_language(project_dir, files)` loops through `RUNNERS` in order (Python first) and calls `runner.detect()` which checks file extensions. First match wins.

**Q63. What is a virtual environment and why is it created per-project?**  
A: A Python venv is an isolated Python installation with its own packages. Creating one per project ensures dependencies from one generated project don't interfere with others. The system uses `python -m venv` to create it.

**Q64. What is `project.json` and what does it store?**  
A: Metadata file created in each project directory by the tool agent:
```json
{
  "project_id": "hello_world",
  "entry_point": "main.py",
  "language": "python",
  "dependencies": ["requests", "numpy"],
  "files": ["main.py", "utils.py"]
}
```
Used by the executor to know which file to run and which packages to install.

**Q65. How does the workspace API handle file paths safely?**  
A: `full_path = os.path.join(WORKSPACE_DIR, project_id, filename)`. The `WORKSPACE_DIR` is computed with `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` — always relative to the actual source file, not the working directory. Hidden dirs (`.git`, `__pycache__`) are filtered from listings.

---

### 🔷 SECTION G — Chat and Persona System

**Q66. What are the 5 AI personas?**  
A: Unhinged GF (💋), Raw Bro (🔥), Savage Teacher (📚), Therapist (🧠), Roaster (😈). Each has a unique system prompt, emoji, color, and assigned Ollama model.

**Q67. How does the bracket command system work?**  
A: The regex `\[\[(\w+)(?:: (.*?))?\]\]` extracts commands like `[[system: Be formal]]`. These are stripped from the user message and applied to a `SessionState` object that modifies the system prompt on a per-session basis.

**Q68. Why is the chat server mounted as a sub-app?**  
A: `app.mount("/persona", chat_app)` isolates persona chat from the main orchestration server. Different CORS rules, different model assignments (uncensored models), completely independent routing. Mounting allows code reuse of the FastAPI infrastructure without coupling the logic.

**Q69. What chat modes exist in SimpleChat?**  
A: (1) Persona mode → calls `/persona/chat`, uses character personalities. (2) Agent mode → calls `/agent/{id}/chat`, uses AI agent system prompts for technical tasks. (3) Direct mode → calls `/agent/manager/chat` with no system prompt, raw model output.

**Q70. How is session state maintained across messages?**  
A: Session IDs are created via `POST /chat/sessions`. Subsequent messages include `session_id`. The backend `chat_memory.py` stores each message with its role and model. The frontend stores sessions in Zustand with localStorage persistence.

---

### 🔷 SECTION H — Real-time Communication

**Q71. How does the WebSocket connection auto-reconnect?**  
A: In `ws.onclose`, a `setTimeout(connect, 2000)` is scheduled. On reconnect, a new WebSocket is created and the cycle is re-established. A `clearTimeout(reconnectTimer)` in the cleanup function (useEffect return) prevents reconnect attempts after the component unmounts.

**Q72. What is ping/pong and why is it needed for WebSockets?**  
A: Some browsers/proxies close idle WebSocket connections after 30-60 seconds. The dashboard sends `ws.send(JSON.stringify({type: 'ping'}))` every 15 seconds to keep the connection alive. The backend ignores this (just `await websocket.receive_text()`).

**Q73. How are WebSocket events structured?**  
A: Each event has: `{event_id, run_id, node_id, type, input, output, error, metadata, timestamp}`. The `type` field drives the canvas update logic: "start"→running, "update"→streaming output, "complete"→success, "error"→error state.

**Q74. What is the difference between WebSocket and SSE in this project?**  
A: WebSocket (`/ws/agent-stream`) is used for canvas pipeline events — bidirectional, persistent, broadcasts to all connected clients. SSE is used for individual chat responses — unidirectional streaming per request, handled by `StreamingResponse`.

**Q75. What happens if the WebSocket connection drops during a pipeline run?**  
A: The pipeline continues running on the backend (the lock is held, Ollama is generating). When the client reconnects (2-second auto-reconnect), it won't receive the events that already fired, but will receive any future events. The canvas shows the final state when the `complete` event arrives.

---

### 🔷 SECTION I — Voice and STT

**Q76. What is Whisper?**  
A: OpenAI's speech recognition model, available as a local Python library. The project uses `whisper-tiny` (fastest, least accurate) or the available model. Runs entirely offline.

**Q77. What audio format does the VoiceButton use?**  
A: `audio/webm` captured by `MediaRecorder`. The browser's MediaRecorder API captures in the best format it supports. The backend accepts any format and passes it through to Whisper which handles format detection.

**Q78. What is `navigator.mediaDevices.getUserMedia()`?**  
A: Browser Web API that requests permission for microphone (or camera) access. Returns a `MediaStream`. If permission is denied, it throws an error which the VoiceButton catches to show an appropriate state.

---

### 🔷 SECTION J — Performance and Metrics

**Q79. What metrics does the system track?**  
A: Run counts, success/fail rates, per-model latency, VRAM usage over time, task type distribution, token counts. All stored in SQLite `metrics_runs` and `metrics_vram` tables.

**Q80. How is latency measured?**  
A: `start_time = time.time()` before pipeline, `total_latency = int((time.time() - start_time) * 1000)` after. Stored in `latency_ms` column. Per-agent latency is measured separately for the timeline.

**Q81. What is the PerformanceDashboard built with?**  
A: Fetches metric JSON from multiple endpoints and renders with CSS progress bars and/or `recharts` (if installed) for line/bar/pie charts. Data refreshes on component mount.

**Q82. What is `db_size_mb` in memory stats?**  
A: `os.path.getsize("memory.db") / (1024*1024)` — the SQLite file size in megabytes. Exposed via `/memory/stats` so users can monitor database growth.

---

### 🔷 SECTION K — Prompt Engineering and Versioning

**Q83. How are prompts loaded from `.md` files?**  
A: `core/prompts/__init__.py` reads each `.md` file from the `prompts/` directory and exposes them as functions: `coder_prompt()`, `analyst_prompt()`, etc. This makes prompts easy to edit without touching Python code.

**Q84. What is the prompt versioning system?**  
A: A SQLite table stores each prompt save with: agent_id, version_number, prompt_text, prompt_type (chat/pipeline), note, created_at. The API allows saving new versions, viewing history, rolling back, and comparing diffs.

**Q85. What is a planner prompt and what output format does it expect?**  
A: The planner prompt in `manager.md` instructs the LLM to analyze a task and output structured JSON with `{goal, project_id, complexity, task_type, confidence, steps: [...]}`. The steps tell the orchestrator which agents to run in what order.

**Q86. Why do some prompts have a "Hybrid JSON output format"?**  
A: The coder agent outputs both human-readable code with markdown fences AND a machine-parseable JSON section separated by `---JSON---`. This allows the tool agent to use the fast JSON parsing path while still showing readable output to users.

---

### 🔷 SECTION L — Code-Change / Tricky Questions

**Q87. What would happen if you removed the `pipeline_lock`?**  
A: Multiple requests would reach `ensure_model_loaded()` simultaneously. Two pipelines might both try to load a heavy model, causing VRAM OOM errors. The GPU inference would also interfere, producing garbled outputs from token-level conflicts.

**Q88. What change would you make to support GPT-4 as a backend model?**  
A: Add an `openai_client.py` in services that calls `openai.ChatCompletion.create(model="gpt-4", stream=True)`. Add `"openai-gpt4"` to the `MODELS` dict with `"size_gb": 0` (cloud model). Modify `scheduled_generate()` in the VRAM scheduler to skip VRAM allocation for cloud models (check if model starts with "openai-").

**Q89. How would you add a new agent, e.g., a "Security Auditor"?**  
A: 1) Create `prompts/security.md` with the audit prompt. 2) Create `agents/security.py` with `run_security_async()`. 3) Add `"security": {"name": "deepseek-r1:8b", "size_gb": 5.2, "role": "security_audit"}` to `config.py MODELS`. 4) Import in `main.py` and add to `_resolve_node_handler()`. 5) Add to `TASK_ROUTER` in `router.py`. 6) Add to frontend `config/agents.js`.

**Q90. Why is `result_json = ""` reset in tool.py when each fast-path fails?**  
A: Each fast-path sets `result_json` only if it succeeds. The `if not result_json:` guard before each path checks if a previous path already succeeded. If `result_json` is non-empty, all subsequent paths are skipped. This creates a waterfall of increasingly expensive fallbacks.

**Q91. What happens to the `active_tasks` dict in main.py?**  
A: It's designed to store `run_id → asyncio.Task` references. The `/stop` endpoint cancels all tasks in this dict. However, currently the pipelines don't explicitly add themselves to `active_tasks` (it's an architectural stub for future implementation).

**Q92. What would break if `WORKSPACE_DIR` pointed to `backend/workspace` instead of the project root `/workspace`?**  
A: The backend agents (tool.py) save to the project-root `/workspace`, but the `/workspace` API would list a different (empty) directory. This was a bug that was explicitly fixed — the comment in `main.py` around line 97-104 explains this fix.

**Q93. Why does `PythonRunner.install_deps()` have a STDLIB set?**  
A: To avoid calling `pip install os`, `pip install json`, etc. — standard library modules can't be pip-installed and trying to would fail. The set has 80+ stdlib module names; only modules NOT in this set are passed to pip.

**Q94. How would you add authentication to the API?**  
A: Add `from fastapi.security import OAuth2PasswordBearer` and create a `get_current_user` dependency. Inject it into each route: `async def run(body: RunRequest, user: User = Depends(get_current_user))`. Add token generation endpoint.

**Q95. What is the `shutil.rmtree()` call in delete_project and what risk does it carry?**  
A: `shutil.rmtree(project_dir)` recursively deletes the entire project directory and all its contents. The risk is that if `project_dir` is constructed incorrectly (e.g., path traversal attack `/workspace/../../etc`), it could delete critical system files. The current implementation should add path safety checks.

**Q96. How does ReactFlow detect that a node was dropped onto the canvas?**  
A: The canvas `<div>` has `onDrop` and `onDragOver` handlers. The `NodeSidebar` sets `event.dataTransfer.setData('application/reactflow', 'custom')` when dragging starts. The canvas reads this data in `onDrop`, calls `rfInstance.screenToFlowPosition()` to convert screen coordinates to canvas coordinates, and adds the new node.

**Q97. What is `rfInstance.screenToFlowPosition()` and why is it needed?**  
A: ReactFlow's internal coordinate system (the "flow") can be panned and zoomed independently of the screen. `screenToFlowPosition({x, y})` converts mouse position (screen pixels) to flow coordinates, accounting for current pan and zoom level. Without it, dropped nodes would appear in wrong positions.

**Q98. Why does `compile(content, path, "exec")` validate Python code before saving?**  
A: `compile()` syntax-checks Python code without executing it. If it raises `SyntaxError`, the file would cause a runtime error when executed. The tool agent uses this to detect and attempt cleanup of LLM-generated code that has syntax errors before saving.

**Q99. How does the system handle a user switching personas in the middle of a conversation?**  
A: `handlePersonaChange()` calls `addMessage()` with `role: "system"` to inject a visual separator like "Persona changed: Therapist → Roaster". The `updateSessionMeta()` updates the Zustand session. On the next `sendMessage()`, the new persona's system prompt is used. Past messages are not regenerated.

**Q100. Explain why `strip_prompt_leakage()` is necessary.**  
A: Some LLMs echo back portions of the system prompt in their responses before giving the actual answer. If `result_json` contains "You are a helpful assistant..." followed by the actual JSON, `extract_json_object()` would still find the JSON, but the text confuses earlier parsing steps. `strip_prompt_leakage()` removes known prompt preambles.

---

### 🔷 SECTION M — Additional Deep-Dive Questions

**Q101. What is the `storeRef` pattern in Dashboard.jsx?**  
A: `storeRef.current = { updateNode: useAgentStore.getState().updateNode }` uses `useRef` to hold stable function references. When the WebSocket `onmessage` handler (defined in useEffect) calls `storeRef.current.updateNode()`, it always gets the latest store function, avoiding stale closure issues that would occur with a direct `useCallback` reference.

**Q102. What is `AnimatePresence` in Framer Motion?**  
A: A component that enables exit animations for React components being unmounted. Normally React unmounts components immediately (no time for exit animations). `<AnimatePresence>` delays unmounting until the `exit` animation completes.

**Q103. What is the purpose of `custom_agents.json`?**  
A: Persists user-created custom agents. When the server restarts, `load_custom_agents()` reads this file. Without it, all custom agents would be lost on restart. A database could be used instead, but a JSON file is simpler for a small number of agents.

**Q104. What would you change to support concurrent pipeline executions?**  
A: The fundamental challenge is VRAM — with 16GB, you can't run two 9GB models simultaneously. Solutions: (1) Queue-based scheduling (FIFO queue instead of a simple lock), (2) Use lighter models for concurrent requests (4GB each, 4 simultaneous), (3) Implement a job priority system where direct mode queries interrupt queued agent runs.

**Q105. How does `PINNED_MODELS` work differently from `exclusive`?**  
A: `exclusive: True` in config means the model needs the entire VRAM for itself. `PINNED_MODELS` in the scheduler means the model should stay resident between requests (never proactively unloaded). A pinned model can be evicted only if a model with `evicts_pinned: True` (like heavy/codestral) is requested.

**Q106. What is the `@dataclass` decorator in Python?**  
A: Automatically generates `__init__`, `__repr__`, and other special methods based on class-level annotations. `@dataclass class VRAMState: total_gb: float = 48.0` means `VRAMState()` works without writing an `__init__`. `field(default_factory=dict)` creates a new dict for each instance.

**Q107. Explain the `model_config = ConfigDict(extra="ignore")` in Pydantic models.**  
A: By default, Pydantic BaseModel raises an error if the JSON has extra fields not defined in the model. `extra="ignore"` silently drops unknown fields. This is used in `PlanStep` and `RouteDecision` so the planner's JSON output can have extra informational fields without breaking parsing.

**Q108. What is `row_factory = sqlite3.Row`?**  
A: Setting this on a SQLite connection makes `cursor.fetchone()` return a `Row` object instead of a plain tuple. `Row` supports both index access (`row[0]`) and key access (`row["name"]`), making database code more readable.

**Q109. How would you implement real-time collaboration (multiple users)?**  
A: The EventEmitter already broadcasts to ALL connected WebSocket clients. Multiple users see each other's pipeline runs in real-time. To isolate: add `user_id` to events and filter in the frontend. For collision-free workspace editing, implement file locking via a `locks` table in SQLite.

**Q110. What is the significance of `os.path.abspath(__file__)`?**  
A: `__file__` is the current Python file's path. `os.path.abspath()` makes it absolute. `os.path.dirname(os.path.abspath(__file__))` gives the directory containing the script. Used extensively to compute the workspace path relative to source files rather than the current working directory, which varies depending on where `uvicorn` is launched from.

---

## Quick Reference — Endpoint Cheat Sheet

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Backend + Ollama + model status |
| POST | `/run` | Main dual-mode execution |
| POST | `/run-node` | Single agent node execution |
| GET | `/workspace` | List all projects |
| GET | `/workspace/{pid}/{file}` | Read file |
| PUT | `/workspace/{pid}/{file}` | Update file |
| DELETE | `/workspace/{pid}` | Delete project |
| GET | `/workspace/export/{pid}` | Download ZIP |
| POST | `/execute/{pid}` | Run project code |
| POST | `/execute/{pid}/autofix` | Run with autofix loop |
| GET | `/metrics/overview` | Performance stats |
| GET | `/memory/stats` | DB stats |
| POST | `/memory/cleanup` | TTL cleanup |
| POST | `/chat/sessions` | Create chat session |
| GET | `/chat/sessions/{sid}` | Get session + messages |
| POST | `/agent/{id}/chat` | Streaming agent chat (SSE) |
| POST | `/transcribe` | Audio → text (Whisper) |
| GET | `/custom-agents` | List custom agents |
| POST | `/custom-agents` | Create custom agent |
| POST | `/stop` | Cancel all runs |
| GET | `/scheduler/status` | VRAM scheduler state |
| WS | `/ws/agent-stream` | Real-time event stream |
| POST | `/persona/chat` | Persona chat (SSE) |

---

*Guide generated from full codebase analysis of AgentForge v3.1/v4.0*  
*Total files analyzed: 40+ across backend, frontend, and prompts directories*
