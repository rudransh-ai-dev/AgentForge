# AgentForge — System Architecture (v3.1 Final)

> **Architecture Grade: 9.5/10 — Production-Ready**
> **Identity: Deterministic, resource-aware multi-agent inference system**

---

## Core Invariants (Hard Rules — NEVER Break)

| Rule                           | Status       |
| ------------------------------ | ------------ |
| Size-aware concurrency (below) | ✅ Mandatory  |
| Manager + Heavy (≥10GB) together | ❌ Forbidden  |
| Manager + Light (<10GB) together | ✅ Allowed    |
| Precompute before Heavy model  | ✅ Required   |
| Heavy models only on demand    | ✅ Critical   |
| Minimize reload cycles         | ✅ Important  |
| No group chat agents           | ❌ Forbidden  |
| Sequential orchestration       | ✅ Mandatory  |
| Global pipeline lock           | ✅ Mandatory  |

---

## Execution Modes (Dual-Mode UI)

### Mode 1: ⚡ Direct Model Mode
- No manager, no pipeline
- `User → Selected Model → Response`
- Target latency: **< 2 seconds**
- Best for: daily questions, quick lookups

### Mode 2: 🧠 Agent Mode
- Full orchestration pipeline
- `User → Router → Planner → Agent(s) → Manager → Output`
- Target latency: **< 8–15 seconds** (standard), **< 25 seconds** (Qwen)
- Best for: complex tasks, code generation, multi-step reasoning

---

## Pipeline Architecture

### Router → Planner → Executor (Logical Split)

```text
User Input
   ↓
Router (rule-based + light LLM fallback)
   ↓
IF simple → Direct Mode (single model)
IF complex → Planner
   ↓
Planner (break into steps, estimate complexity)
   ↓
Executor Agents (sequential, one at a time)
   ↓
Manager (validate / finalize)
```

---

## VRAM-Aware Model Lifecycle

### Size-Based Concurrency Policy (Based on Actual Hardware)
```text
╔════════════════════════════════════════════════════════════════════╗
║  MODEL INVENTORY & CONCURRENCY RULES                              ║
╠════════════════════════════════════════════════════════════════════╣
║  phi3:mini              2.2 GB  → ✅ Can co-run with Manager      ║
║  deepseek-coder:6.7b    3.8 GB  → ✅ Can co-run with Manager      ║
║  llama3:8b              4.7 GB  → ✅ Can co-run with Manager      ║
║  llama3:latest          4.7 GB  → ✅ Can co-run with Manager      ║
║  ─────────────────── 10 GB THRESHOLD ──────────────────────────── ║
║  yolo0perris/Qwen...   13 GB   → ❌ EXCLUSIVE (unload all first)  ║
║  qwen3.5:35b-a3b       23 GB   → ❌ EXCLUSIVE (unload all first)  ║
║  mixtral:latest         26 GB   → ❌ EXCLUSIVE (unload all first)  ║
╚════════════════════════════════════════════════════════════════════╝
```

### Concurrency Rule (Code)
```python
HEAVY_THRESHOLD_GB = 10

def is_heavy_model(model_name: str, model_sizes: dict) -> bool:
    return model_sizes.get(model_name, 0) >= HEAVY_THRESHOLD_GB

# Light models (<10GB): Manager can stay loaded alongside
# Heavy models (≥10GB): EXCLUSIVE — unload everything first
```

### Standard Flow (Light Model — No Unload Needed)
```text
1. Manager (Phi-3, 2.2GB) → Analyze → stays in VRAM
2. Coder (DeepSeek, 3.8GB) → Loads alongside Manager → Execute
3. Coder → UNLOAD (optional, can stay warm)
4. Manager → still loaded → Validate / finalize
```
👉 **No reload penalty! Fast pipeline.**

### Heavy Model Flow (≥10GB — Exclusive Phase)
```text
1. Manager (Phi-3) → Precompute FULL instruction
   → clear task, constraints, expected format, minimal context
2. Manager → GUARANTEED UNLOAD
3. ALL other models → GUARANTEED UNLOAD
4. Qwen/Mixtral → EXCLUSIVE LOAD → Execute
5. Qwen/Mixtral → UNLOAD
6. Manager → RELOAD → Interpret + finalize
```

### ⚠️ Anti-Patterns
```text
Manager + Qwen simultaneously            ❌ (VRAM overflow)
Manager → Qwen → Manager → Qwen          ❌ (reload hell)
Two heavy models simultaneously           ❌ (instant crash)
```

---

## Global Pipeline Lock (Race Condition Prevention)

```python
import asyncio

# FIFO task queue — prevents model conflicts from rapid requests
pipeline_lock = asyncio.Lock()

async def run_pipeline(task):
    async with pipeline_lock:
        # Only one pipeline execution at a time
        # Queued requests wait in FIFO order
        result = await execute_task(task)
        return result
```

---

## Model Tiering & Warm Pool

| Model Type           | Size     | Strategy              | Examples               |
| -------------------- | -------- | --------------------- | ---------------------- |
| Small (≤3B)          | <3 GB    | Keep warm (co-run OK) | Phi-3 (2.2GB)          |
| Medium (3B–10B)      | 3–10 GB  | Warm pool (co-run OK) | DeepSeek (3.8GB), LLaMA 3 (4.7GB) |
| Large (10B+)         | ≥10 GB   | Exclusive, on-demand  | Mixtral (26GB), Qwen (13–23GB) |

### Warm Pool Strategy
```text
Always Ready : Phi-3 (routing + lightweight tasks)
Short Cache  : DeepSeek + LLaMA 3 (stay warm 60s, can co-exist)
On-Demand    : Qwen/Mixtral (exclusive load, unload immediately after)
```

---

## Task Schema (Standardized — With Execution Budget)

```json
{
  "task_id": "uuid",
  "type": "code_generation | analysis | review | debug",
  "agent": "coder | analyst | critic",
  "model": "deepseek-coder:6.7b",
  "input": "user prompt or manager instruction",
  "constraints": ["no external APIs", "Python only"],
  "expected_output": "code | text | json",
  "priority": "low | medium | high",
  "max_tokens": 2048,
  "budget": {
    "max_latency_ms": 15000,
    "max_model_size_gb": 10,
    "allow_heavy_model": false
  }
}
```

### Cost-Aware Routing
```text
IF task is simple AND latency_critical:
   → force small model (Phi-3 / DeepSeek)
IF task is medium:
   → avoid Qwen even if complex enough
IF task is complex AND user explicitly allows:
   → trigger Qwen (exclusive phase)
```

### Budget Enforcement
```text
IF predicted_cost > budget.max_latency_ms:
   → downgrade model OR simplify plan
IF model_size > budget.max_model_size_gb AND NOT budget.allow_heavy_model:
   → use fallback model
```
```

---

## Feedback Loop (Critic Pattern)

```text
Coder → Output
   ↓
Manager (reload)
   ↓
IF quality < threshold → send back to coder with corrections (max 2 retries)
ELSE → final output to user
```

### Event-Driven Triggers
```text
IF runtime_error OR syntax_error OR user_dissatisfaction:
   → trigger critic / debugger agent
```

---

## Failure Handling

```text
IF agent fails:
   → retry (max 2 attempts)
IF still fails:
   → fallback model (DeepSeek → LLaMA 3)
IF still fails:
   → return structured error to user
```

---

## State Persistence (Session Memory)

```python
session = {
    "session_id": "uuid",
    "history": [],           # conversation turns
    "last_agent": "coder",   # last active agent
    "last_model": "deepseek-coder:6.7b",
    "context_summary": "...", # compressed context
    "task_queue": [],         # pending tasks
    "active_mode": "direct",  # direct | agent
}
```

---

## Context Compression Layer

```text
Context Manager:
- Summarize previous steps after each turn
- Keep only relevant state (discard verbose outputs)
- Essential for multi-step workflows
- Prevents context window overflow
```

---

## Observability (Structured Logging)

```json
{
  "timestamp": "2026-03-31T13:00:00Z",
  "run_id": "uuid",
  "agent": "coder",
  "model": "deepseek-coder:6.7b",
  "phase": "execution",
  "latency_ms": 3200,
  "tokens_in": 150,
  "tokens_out": 850,
  "status": "success",
  "vram_usage_mb": 4200
}
```

---

## Latency Budgets

| Mode          | Target     | Action if Exceeded        |
| ------------- | ---------- | ------------------------- |
| Direct Mode   | < 2s       | Warn user                 |
| Agent Mode    | < 8–15s    | Show progress indicators  |
| Qwen Phase    | < 25s      | Downgrade model or warn   |
| Model Reload  | < 2–6s     | Use warm pool             |

---

## Missing Components (Implementation TODO)

### Priority 1 (Build First)
1. ⚡ **Dual-Mode UI** — Toggle Direct/Agent in chat
2. ⚙️ **VRAM Scheduler** — Ollama load/unload management
3. 🔄 **Router Logic** — Rule-based + LLM fallback

### Priority 2 (Build Second)
4. 🧠 **Feedback Loop** — Manager validates Coder output
5. 🛠️ **Tool Agent** — Python executor, file ops, API calls
6. 📋 **Task Schema** — Structured task objects

### Priority 3 (Polish)
7. 💾 **Session Memory** — State persistence across turns
8. 📊 **Structured Logging** — Full observability
9. 🗜️ **Context Compression** — Summarize long conversations
10. ⚡ **Latency Budgets** — Auto-downgrade if too slow

---

## Architecture Decision Records

| Decision            | Choice                  | Reason                          |
| ------------------- | ----------------------- | ------------------------------- |
| Execution model     | Sequential              | GPU constraint, deterministic   |
| Agent communication | No group chat           | Chaos prevention, VRAM safety   |
| Heavy models        | Exclusive phase         | Full VRAM allocation            |
| Router              | Rule-based + LLM        | Fast path for simple, smart for complex |
| State               | Session-scoped          | Multi-step workflows            |
| Failures            | Retry → Fallback → Error| Graceful degradation            |

---

## System Identity

> **Not a chatbot → a controlled inference pipeline**
> **Agents = stateless workers, Manager = brain**
> **Treat models like GPU processes, not permanent services**
> **Treat Qwen 35B as an exclusive execution phase**
> **The system should be deterministic, observable, and resource-aware**
