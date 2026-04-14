# 🎯 Top 10 Viva Questions — LocalAI Multi-Agent IDE

> **Quick-prep cheat sheet for academic viva / project presentation**

---

## ⭐ Important Points to Remember First

| Point | Detail |
|---|---|
| **Project Type** | Local-first, offline AI IDE — no cloud, no API keys |
| **Hardware** | RTX 5070 Ti, 16 GB GDDR7 VRAM |
| **Backend** | FastAPI + Python 3.11 + SQLite (memory.db) |
| **Frontend** | React 18 + Vite + Zustand + ReactFlow + Framer Motion |
| **AI Runtime** | Ollama on `localhost:11434` |
| **Communication** | WebSocket for pipeline events, SSE for chat streaming |
| **Agents** | 10 agents: Manager, Writer, Editor, Tester, Coder, Critic, Analyst, Researcher, Reader, Tool |
| **Pipeline** | Writer (draft) → Editor (refine) → Tester (QA) → loop max 3x |
| **Execution** | Direct mode < 2s, Agent mode 8–15s, Heavy mode ~25s |
| **Storage** | SQLite: `runs`, `fixes`, `patterns`, `chat_sessions`, `canvas_runs`, `metrics` |

---

## 🔟 Top 10 Questions & Model Answers

---

### ❓ Q1. What is the core idea of this project? Explain in 2–3 sentences.

**Answer:**  
This project is a **fully local AI-powered IDE** where multiple specialized LLMs (large language models) running on your own GPU collaborate to plan, write, refine, test, and execute code automatically. It uses a **multi-agent pipeline** — a Writer drafts the code, an Editor refines it, and a Tester validates it in a feedback loop — all without any cloud dependency. The entire system is orchestrated through a FastAPI backend with a React-based visual canvas frontend.

---

### ❓ Q2. What is the multi-agent pipeline and how does each stage work?

**Answer:**  
The pipeline is a **3-stage Writer → Editor → Tester** loop:

- **Stage 1 — Writer** (`gpt-oss:20b`): Generates the initial code draft. Uses the largest model for breadth and creativity.
- **Stage 2 — Editor** (`qwen2.5-coder:14b`): Reviews and improves the draft — fixes logic errors, edge cases, code style.
- **Stage 3 — Tester** (`deepseek-r1:8b`): Acts as an adversarial QA engineer. Returns a JSON verdict `{verdict: "PASS"/"FAIL", bugs: [...], fix_instructions: "..."}`.  
- If Tester says **FAIL**, the fix instructions go back to the Editor. This loop runs up to **3 times**.  
- After PASS: the Tool agent saves files to `/workspace`, and the Executor runs the code.

---

### ❓ Q3. How does the VRAM Scheduler work? Why is it needed?

**Answer:**  
A GPU with 16 GB VRAM cannot load multiple large models simultaneously. The **VRAM Scheduler** (`services/vram_scheduler.py`) tracks the state of all loaded models in a `VRAMState` dataclass and enforces these rules:

1. **Heavy models** (≥ 8.5 GB, like `codestral:22b`) need the entire VRAM exclusively — everything else is unloaded first.
2. **Light models** (< 8.5 GB) can co-run if the combined usage fits.
3. **Pinned models** (e.g., `llama3.1:8b`) stay resident unless a heavy model forces eviction.

Every inference call passes through `scheduled_generate()` which loads the model, runs inference, and for heavy models, immediately unloads them after use. The global `pipeline_lock` (an `asyncio.Lock`) ensures only one pipeline uses the GPU at a time.

---

### ❓ Q4. What is the difference between WebSocket and SSE? Where does this project use each?

**Answer:**  

| Feature | WebSocket | SSE (Server-Sent Events) |
|---|---|---|
| Direction | Full-duplex (both ways) | Server → Client only |
| Protocol | Upgraded HTTP | Regular HTTP |
| Use here | Agent pipeline events (canvas) | Chat streaming responses |

- **WebSocket** (`/ws/agent-stream`): Persistent connection. The backend broadcasts `{type: start/update/complete/error, node_id, output}` events to ALL connected clients. The frontend canvas updates in real-time.
- **SSE** (`/agent/{id}/chat`, `/persona/chat`): Per-request stream. The backend uses `StreamingResponse` with `text/event-stream` MIME type. The frontend reads it with `ReadableStream` API.

---

### ❓ Q5. Explain the self-correcting autofix loop. How does memory improve it over time?

**Answer:**  
When generated code fails to execute, `autofix_loop_async()` kicks in (max 2 retries):

1. `execute_project_async()` runs the code and captures the error output.
2. `get_similar_fixes(error)` searches SQLite's `fixes` table for **past successful fixes** with similar error keywords.
3. These past fixes are prepended as **memory hints** in the repair prompt:  
   `"PAST SUCCESSFUL FIXES FOR SIMILAR ERRORS: error was X, fix was Y..."`
4. The Coder agent generates a patch; the file is overwritten.
5. The project is executed again.

Each fix attempt is stored in SQLite with `store_fix(error, fix_code, success)`. Over time, the system accumulates a fix knowledge base — making it progressively better at self-correcting similar bugs.

---

### ❓ Q6. What is Zustand? How is it used for state management?

**Answer:**  
Zustand is a minimal, boilerplate-free React state management library. Unlike Redux (which requires actions, reducers, dispatch), Zustand stores are plain JavaScript objects with methods:

```javascript
// Reading state: hook inside component
const { nodesState } = useAgentStore();

// Updating state: from anywhere (even outside React)
useAgentStore.getState().updateNode(run_id, node_id, { status: 'running' });
```

**In this project**, `useAgentStore` holds:
- `nodesState` — which canvas node is running/idle/successful
- `executionLog` — the timeline of all WebSocket events
- `projects`, `canvasRuns`, `chatSessions` — history
- `customAgents`, `availableModels` — configuration

The WebSocket `onmessage` handler in `Dashboard.jsx` calls `useAgentStore.getState().updateNode()`, which triggers React re-renders only in components that subscribe to that slice of state.

---

### ❓ Q7. What is the dual-mode execution system and how does Auto mode decide?

**Answer:**  
Two modes exist:

| Mode | Target Latency | How it works |
|---|---|---|
| **Direct** | < 2 seconds | Single model response, no pipeline, no tool agent |
| **Agent** | 8–15 seconds | Full Writer→Editor→Tester pipeline |
| **Heavy** | ~25 seconds | Agent mode but with `codestral:22b` for Stage 1 |

**Auto mode** inspects the prompt using keyword lists:
```python
is_research = "explain" in prompt or "what is" in prompt  # → agent + research_mode
is_complex  = "build" in prompt or "create a" in prompt   # → agent mode
# else → direct mode
```
This avoids expensive LLM planning calls for obvious cases. For complex routing, `plan_task_async()` calls the manager LLM to generate a structured JSON execution plan.

---

### ❓ Q8. Explain the Tool Agent's multi-tier JSON parsing strategy.

**Answer:**  
LLMs produce inconsistent output formats. The Tool Agent (`agents/tool.py`) handles this with 5 fallback tiers — from fastest to slowest:

1. **`---JSON---` marker** — The coder wraps JSON in `---JSON---...---OUTPUT---`. Direct string split + parse. Fastest.
2. **Raw JSON parse** — Try `json.loads(entire_prompt)`. Works if the model output IS pure JSON.
3. **JSON in markdown block** — Regex extract from ` ```json...``` `. Works for wrapped JSON.
4. **Markdown code blocks** — Regex all ` ```lang...``` ` blocks, map to files by extension. No JSON needed.
5. **AI parser (LLM fallback)** — Call the manager model to extract structure. Slowest but most reliable.

This layered approach means trivial tasks ("hello world") parse in milliseconds, while edge cases still resolve correctly.

---

### ❓ Q9. How does React Flow show live agent status on the canvas?

**Answer:**  
The data flow is completely event-driven:

```
Backend (any agent) 
  → emitter.emit(run_id, "writer", "start") 
  → EventEmitter broadcasts JSON over WebSocket
  → Dashboard.jsx ws.onmessage() receives it
  → useAgentStore.getState().updateNode("writer", {status: "running"})
  → Zustand state updates
  → AgentCanvas.jsx useEffect detects nodesState change
  → Updates ReactFlow node's `data.stateData` 
  → CustomNode.jsx re-renders with blue glow + "running" badge
```

The `EventEmitter` is a singleton (`emitter`) imported by every agent. It serializes events as `{run_id, node_id, type, output, timestamp}` and sends to all WebSocket connections. No polling — all push-based.

---

### ❓ Q10. What would you improve or add next? (Future scope)

**Answer:**  
Several improvements are architecturally planned or easily achievable:

1. **Vector DB for memory** — Replace SQLite keyword search in `get_similar_fixes()` with embedding-based semantic search (ChromaDB/FAISS) for smarter fix retrieval.
2. **Multi-user support** — The WebSocket already broadcasts to all clients; adding `user_id` filtering makes it multi-tenant.
3. **Cloud model support** — Add an `openai_client.py` service; VRAM scheduler skips VRAM allocation for cloud models (`size_gb: 0`).
4. **Code diff visualization** — The `services/diff.py` already saves diffs; `CodeDiffViewer.jsx` just needs connecting to the workspace UI.
5. **Parallel agent execution** — Currently strictly sequential. Independent analysis + research tasks could run in parallel with `asyncio.gather()`.
6. **Voice output (TTS)** — Add a text-to-speech route; agent responses could be spoken aloud.
7. **Plugin system** — Allow users to write their own agent scripts that plug into the pipeline.

---

## 📌 Key Technical Terms — Quick Definitions

| Term | Definition |
|---|---|
| **Ollama** | Local LLM server exposing REST API on port 11434 |
| **VRAM** | GPU memory — models are loaded here for fast inference |
| **Asyncio** | Python's built-in async I/O framework — used for non-blocking LLM calls |
| **Pipeline Lock** | `asyncio.Lock()` — ensures only one pipeline runs at a time |
| **Token Streaming** | LLM output sent token-by-token, not waiting for full response |
| **SSE** | Server-Sent Events — HTTP-based unidirectional streaming |
| **Zustand** | Minimal React state manager — no boilerplate, direct store access |
| **ReactFlow** | Library for interactive node/edge graph UIs |
| **Pydantic** | Python data validation with type annotations (used for API models) |
| **SQLite** | Embedded, file-based SQL database (`memory.db`) |
| **Autofix Loop** | Execute → error → patch code → re-execute (max 2 retries) |
| **Pinned Model** | A model that stays in VRAM between requests (`llama3.1:8b`) |
| **Heavy Model** | A model that needs exclusive VRAM access (`codestral:22b`) |
| **Framer Motion** | React animation library — used for transitions and micro-animations |
| **Vite Proxy** | Dev server forwards `/run`, `/ws`, etc. to FastAPI on :8000 |

---

## 🔑 Numbers to Remember

| Metric | Value |
|---|---|
| Total Agents | 10 |
| Pipeline Stages | 3 (Writer → Editor → Tester) |
| Max Autofix Retries | 2 |
| Max Editor Retries (tester rejection) | 3 |
| Direct Mode Target | < 2 seconds |
| Agent Mode Target | 8–15 seconds |
| Heavy Mode Target | ~25 seconds |
| VRAM Budget | 16 GB |
| Heavy Model Threshold | 8.5 GB |
| WS Ping Interval | 15 seconds |
| WS Reconnect Delay | 2 seconds |
| Health Check Interval | 15 seconds |
| Backend Port | 8000 |
| Frontend Port | 5173 (Vite dev) |
| Ollama Port | 11434 |
| Persona Server Mount | `/persona` |
| DB Tables | 9+ (runs, fixes, patterns, chat_sessions, messages, canvas_runs, canvas_steps, metrics_runs, metrics_vram) |

---

*Generated for BCA 6th Semester Project Viva — LocalAI Multi-Agent IDE*
