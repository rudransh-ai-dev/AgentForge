# AgentForge — v4.0 Final Architecture Plan
> **Status: APPROVED FOR IMPLEMENTATION**  
> **Version:** 4.0  
> **Hardware Target:** NVIDIA RTX 5070 Ti — 16 GB GDDR7 VRAM @ 896 GB/s  
> **Date:** 2026-04-14  

---

## Executive Summary

v4.0 is a complete architectural promotion from "working demo" to **production-grade multi-agent IDE**. The three pillars of this upgrade are:

1. **Codebase Hygiene** — Eliminate all redundant directories, dead code, and stale model references left over from prior versions
2. **7-Agent Production Roster** — Assign every agent a specific, optimized model backed by empirical benchmarks and real VRAM constraints
3. **3-Stage Critic-Feedback Pipeline** — Replace the single-pass Coder with a three-stage Write → Edit → QA loop that catches bugs before they reach the user's workspace

This is not a feature addition. It is a **system re-architecture** informed by real VRAM profiling, benchmark data, and observed failure modes from v3.1 batch testing.

---

## Table of Contents

1. [The Problem with v3.1](#1-the-problem-with-v31)
2. [The 7-Agent Final Roster](#2-the-7-agent-final-roster)
3. [VRAM Architecture & Scheduling Strategy](#3-vram-architecture--scheduling-strategy)
4. [The 3-Stage Production Pipeline](#4-the-3-stage-production-pipeline)
5. [Codebase Cleanup Specification](#5-codebase-cleanup-specification)
6. [File-by-File Change Manifest](#6-file-by-file-change-manifest)
7. [Prompt Engineering Spec](#7-prompt-engineering-spec)
8. [Persona & Chat System](#8-persona--chat-system)
9. [Execution Modes](#9-execution-modes)
10. [Failure Handling & Fallback Chains](#10-failure-handling--fallback-chains)
11. [Observability & Logging](#11-observability--logging)
12. [Implementation Order](#12-implementation-order)
13. [Verification Checklist](#13-verification-checklist)

---

## 1. The Problem with v3.1

### Observed Failure Modes from Batch Testing

During live batch testing of 6 projects (2 hard, 2 mid, 2 easy) the following issues were confirmed:

| Failure | Root Cause | Impact |
|---|---|---|
| HTML embedded in Python `main.py` | Single-pass Coder with no review stage | Unusable output |
| `WORKSPACE_DIR` path mismatch | `backend/agents/tool.py` pointing to `backend/workspace` instead of root `/workspace` | Files saved to wrong location |
| `Attempt 1 failed for model 'devstral'` | 120s HTTP timeout on long-running heavy models | Critic/README step aborted silently |
| Redundant `backend/prompts` and root `prompts` directories | Accumulated tech debt across versions | Confusing, error-prone maintenance |
| `phi3:mini` referenced as a fallback everywhere | Model was deleted from Ollama library | Runtime errors on all fallback paths |
| `deepseek-coder-v2:16b` in config as primary coder | Model deleted from library | Pipeline crashes on first run |
| Hard projects ran in `agent` mode with no planner refinement | Router lacked "complexity tiers" | Multi-file projects generated as single blobs |

### What v4.0 Fixes

- ✅ Eliminates ALL references to deleted models
- ✅ Unifies workspace to single root directory
- ✅ Unifies prompts to single source of truth
- ✅ Introduces 3-Stage pipeline that catches the "HTML in Python" class of bugs
- ✅ Raises Ollama HTTP timeout to 600s
- ✅ Pins `gemma4:e2b` as a resident model to eliminate routing cold starts
- ✅ Adds `gemma4:26b` as the "Heavy Brain" for truly complex architectural tasks

---

## 2. The 7-Agent Final Roster

This roster is derived from the `docs/modlechange.md` benchmarking analysis and constrained by the 16 GB VRAM envelope.

| # | Role | Model | VRAM | Why |
|---|---|---|---|---|
| 1 | **Manager / Router** | `qwen3.5:9b` | ~6.6 GB | Hybrid thinking mode, fast routing, fits as always-on alongside resident |
| 2 | **Coder 1 — Writer** | `gpt-oss:20b` | ~13 GB (exclusive) | MoE — only 3.6B params active per token, 96% AIME 2025, native tool calling, ~156 tok/s on RTX 5070 Ti FP4 |
| 3 | **Coder 2 — Editor** | `qwen2.5-coder:14b` | ~9 GB (exclusive) | 85–87% HumanEval, purpose-built code model, best-in-class syntax precision |
| 4 | **Tester / QA** | `deepseek-r1:8b` | ~5.2 GB | Step-by-step chain-of-thought reasoning, designed to find edge cases and break logic |
| 5 | **Researcher** | `qwen2.5:14b` | ~9 GB | 128K native context window, strong document comprehension, multilingual |
| 6 | **Heavy Brain / Fallback** | `gemma4:26b` | ~17 GB (exclusive) | Activated only when other models fail or task requires architectural reasoning beyond 9B capacity |
| 7 | **Context Manager (Resident)** | `gemma4:e2b` | ~7.2 GB | Always loaded — handles summarization, context compression, routing assist |

### Chat Persona Models (Separate from Agentic Pipeline)

| Model | Role | Notes |
|---|---|---|
| `gurubot/self-after-dark:latest` | Casual / Personality Chat | Used in SimpleChat persona mode |
| `hf.co/TrevorJS/gemma-4-E2B-it-uncensored-GGUF:Q4_K_M` | Uncensored Chat | Used in Uncensored persona mode |
| `qwen3:14b` *(downloading)* | QA Reviewer / Backup Editor | Will be promoted to QA slot when `deepseek-r1:8b` is insufficient |

### Models Removed from Project Config (Not Deleted from System)

The following models will be **removed from `config.py`** references only:

```
codestral:22b       — outperformed by gpt-oss:20b at lower VRAM
devstral:latest     — deleted from Ollama
codellama:13b       — deleted from Ollama
mistral:latest      — deleted from Ollama
phi3:mini           — deleted from Ollama (ALL fallback references must be replaced)
deepseek-coder-v2   — deleted from Ollama
llama3.1:latest     — deleted from Ollama
llama3.1:8b         — deleted from Ollama
gemma4:e4b          — superseded by e2b for residency
phi4:latest         — superseded by qwen3.5:9b for reasoning
qwen3.5:27b-q4_K_M  — overflows 16 GB VRAM (CPU offload kills throughput)
```

---

## 3. VRAM Architecture & Scheduling Strategy

### Hardware Profile

```
GPU: RTX 5070 Ti (Blackwell)
VRAM: 16 GB GDDR7
Bandwidth: 896 GB/s
VRAM OS Overhead: ~1.0 GB (reserved, non-negotiable)
VRAM GUI Overhead: ~1.2 GB (Xorg + GNOME shell)
Usable VRAM Budget: ~13.8 GB
FP4 Hardware: Yes (Blackwell architecture natively accelerates MXFP4)
```

### Three-Tier VRAM Tiering Strategy

```
TIER 1 — ALWAYS RESIDENT (pinned, never unloaded)
┌─────────────────────────────────────────────────┐
│  gemma4:e2b      ~7.2 GB                        │
│  Role: Context Manager, routing assist           │
│  keep_alive: -1 (permanent)                      │
└─────────────────────────────────────────────────┘
  Available after resident: ~6.6 GB

TIER 2 — HOT-SWAPPED SPECIALISTS (swap from ~6.6 GB headroom)
  These cannot co-run. One at a time. Fast NVMe swap (~8–15s).
┌─────────────────────────────────────────────────┐
│  qwen3.5:9b        ~6.6 GB  (fits in headroom!) │
│  qwen2.5:14b       ~9.0 GB  (needs full clear)  │
│  qwen2.5-coder:14b ~9.0 GB  (needs full clear)  │
│  deepseek-r1:8b    ~5.2 GB  (fits in headroom!) │
└─────────────────────────────────────────────────┘

TIER 3 — EXCLUSIVE HEAVY (full VRAM clear required)
┌─────────────────────────────────────────────────┐
│  gpt-oss:20b  ~13 GB                            │
│  gemma4:26b   ~17 GB  (exceeds budget → swap)  │
└─────────────────────────────────────────────────┘
  NOTE: gemma4:26b requires unloading the resident
  gemma4:e2b temporarily. This is the only case where
  residency is broken.
```

### Updated Scheduling Rules for `vram_scheduler.py`

```python
HEAVY_THRESHOLD_GB = 8.5      # 14B models treated as "heavy"
PINNED_MODELS = ["gemma4:e2b"] # Never unloaded unless loading gemma4:26b
EXCLUSIVE_MODELS = ["gpt-oss:20b", "gemma4:26b"] # Must have full VRAM
```

**Rule priority order:**
1. If model already in VRAM → reuse, skip load cycle
2. If model is PINNED → never unload it (except for gemma4:26b)
3. If model is EXCLUSIVE → unload everything else first
4. If model is HEAVY (≥8.5 GB) → unload all non-pinned models first
5. If model is LIGHT (<8.5 GB) → attempt co-run in available headroom

### Ollama System Configuration (Apply Manually)

```ini
# /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_KEEP_ALIVE=5m"
Environment="OLLAMA_GPU_OVERHEAD=536870912"
```

Apply with:
```bash
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

---

## 4. The 3-Stage Production Pipeline

This replaces the single-pass Coder in the existing `run_agent_mode()` function.

### Pipeline Diagram

```
User Request
     │
     ▼
┌─────────────────────────────────────────┐
│  MANAGER/ROUTER  (qwen3.5:9b)           │
│  • Classify task complexity             │
│  • Determine route: direct / pipeline   │
│  • Generate execution plan (steps JSON) │
└────────────────┬────────────────────────┘
                 │
                 ▼
      ┌──────────────────┐
      │   DIRECT MODE?   │  YES → analyst/qwen3.5 → response
      └──────────────────┘
                 │ NO (complex code task)
                 ▼
┌─────────────────────────────────────────┐
│  STAGE 1: WRITER  (gpt-oss:20b)         │
│  • Load exclusively (unload all)        │
│  • Generate: full implementation draft  │
│  • Output: structured JSON file list    │
│  • Unload after completion              │
└────────────────┬────────────────────────┘
                 │
                 │  draft_output
                 ▼
┌─────────────────────────────────────────┐
│  STAGE 2: EDITOR  (qwen2.5-coder:14b)  │
│  • Load exclusively                     │
│  • Input: original task + draft_output  │
│  • Task: Fix structure, split files     │
│          correctly, optimize syntax     │
│  • Output: refined JSON file list       │
│  • Unload after completion              │
└────────────────┬────────────────────────┘
                 │
                 │  refined_output
                 ▼
┌─────────────────────────────────────────┐
│  STAGE 3: TESTER  (deepseek-r1:8b)     │
│  • Can co-run with resident (5.2 GB)    │
│  • Input: task + refined_output         │
│  • Uses chain-of-thought <think> mode   │
│  • Output: JSON verdict                 │
│    {                                    │
│      "verdict": "PASS" | "FAIL",        │
│      "score": 0–10,                     │
│      "bugs": [...],                     │
│      "fix_instructions": "..."          │
│    }                                    │
└────────────┬─────────────┬──────────────┘
             │             │
           PASS           FAIL (max 3 retries)
             │             │
             │             ▼
             │     ┌──────────────────────┐
             │     │  Back to EDITOR      │
             │     │  with fix_instructions│
             │     │  (targeted fixes only)│
             │     └──────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  TOOL AGENT                             │
│  • Parse JSON file list                 │
│  • Write each file to root /workspace   │
│  • Create project.json manifest         │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  CRITIC (README GENERATION)             │
│  Uses: qwen3.5:9b (can be resident)     │
│  • Generate README.md from code output  │
│  • Include: setup, usage, architecture  │
│  • Save README.md to project dir        │
└────────────────┬────────────────────────┘
                 │
                 ▼
            Final Output to User
```

### Tester Feedback Loop Contract

The Tester agent (`deepseek-r1:8b`) MUST return structured JSON **always**:

```json
{
  "verdict": "PASS",
  "score": 8,
  "bugs": [],
  "fix_instructions": "",
  "summary": "Code is clean and follows task requirements."
}
```

Or for failures:
```json
{
  "verdict": "FAIL",
  "score": 4,
  "bugs": [
    "HTML embedded in main.py at line 24",
    "WebSocket URL hardcoded to localhost:8000"
  ],
  "fix_instructions": "1. Extract HTML to index.html. 2. Make WS URL configurable.",
  "summary": "Multi-language contamination detected."
}
```

The orchestrator passes `fix_instructions` directly back to the Editor as a prefix to the refinement prompt.

### Loop Guard

```python
MAX_QA_RETRIES = 3  # Tester can reject max 3 times before accepting best-available output
```

---

## 5. Codebase Cleanup Specification

### Redundant Directories to Eliminate

#### `backend/workspace/` → DELETE (merge first)

**Current contents:**
```
backend/workspace/
  hello_world/project.json        ← test artifact, delete
  project/main.py                 ← old bad output, delete  
  project/file_1.sh               ← old bad output, delete
  say_hello_world/App.js          ← old bad output, delete
  write_a_python_hello_world_scr/ ← old bad output, delete
```

**Action:** Delete entire `backend/workspace/`. All WORKSPACE_DIR references in code must point to root `/workspace/`.

**Files to update after deletion:**
- `backend/agents/tool.py` line 19 — WORKSPACE_DIR path (already fixed in v3.1 hotfix)
- `backend/core/orchestrator.py` line 55 — WORKSPACE_DIR path
- `backend/main.py` — any `/workspace` endpoint references

#### `backend/prompts/` → DELETE (merge first)

**Current contents:**
```
backend/prompts/
  analyst.md  (499 bytes — OLD, outdated version)
  coder.md    (462 bytes — OLD, superseded by prompts/coder.md @ 2397 bytes)
  manager.md  (590 bytes — OLD, superseded by prompts/manager.md @ 2773 bytes)
```

**Action:** Delete entire `backend/prompts/`. The canonical prompt files are in root `/prompts/`.

**Files to verify after deletion:**
- `backend/core/prompts/__init__.py` — PROMPTS_ROOT already points to root `/prompts/`, no change needed
- `prompts/__init__.py` — this file exists at root but is unused by backend; can be deleted to prevent confusion

### Prompts Directory Consolidation

**Current split (confusing):**
```
/prompts/                     ← root, used by backend via __init__.py
  analyst.md, coder.md, critic.md, manager.md, researcher.md, __init__.py

/backend/core/prompts/        ← backend loader + specialized templates
  __init__.py                 ← the REAL loader
  coder_autofix.md, coder_fix.md, coder_revision.md
  critic_file_review.md, critic_recheck.md, critic_validation.md
  readme.md, tool.md
  analyst.md, coder.md, critic.md, manager.md (DUPLICATES)
```

**After cleanup — clear split:**
```
/prompts/                     ← ALL human-readable system prompts (single source)
  manager.md                  (Pipeline + Chat sections)
  coder.md                    (Pipeline + Chat sections)
  analyst.md                  (Pipeline + Chat sections)
  critic.md                   (Pipeline + Chat sections)
  researcher.md               (Pipeline + Chat sections)
  tester.md                   [NEW] — for deepseek-r1:8b QA agent
  writer.md                   [NEW] — for gpt-oss:20b first-draft agent
  editor.md                   [NEW] — for qwen2.5-coder:14b refinement agent
  context_manager.md          [NEW] — for gemma4:e2b summarization
  readme.md                   (moved from backend/core/prompts)
  coder_autofix.md            (moved from backend/core/prompts)
  coder_fix.md                (moved from backend/core/prompts)
  coder_revision.md           (moved from backend/core/prompts)
  critic_file_review.md       (moved from backend/core/prompts)
  critic_recheck.md           (moved from backend/core/prompts)
  critic_validation.md        (moved from backend/core/prompts)
  tool.md                     (moved from backend/core/prompts)

/backend/core/prompts/        ← ONLY code (the loader)
  __init__.py                 (updated paths, new functions)
  __pycache__/
```

### Dead Code / Stale References to Purge

| Location | Stale Reference | Fix |
|---|---|---|
| `backend/core/orchestrator.py:260` | `LOCAL_FALLBACK = "phi3:mini"` | Replace with `"deepseek-r1:8b"` |
| `backend/core/orchestrator.py:551` | `LOCAL_FALLBACK = "phi3:mini"` | Replace with `"deepseek-r1:8b"` |
| `backend/core/orchestrator.py:71-77` | `MODEL_DOWNGRADES` references `phi3:mini` | Rebuild with new roster |
| `backend/core/router.py:111` | `mgr_cfg = MODELS.get("manager", {"name": "phi3:mini"})` | Update default |
| `backend/agents/critic.py:13` | `MODELS.get("critic", {"name": "llama3:8b"})` | Update default |
| `backend/agents/coder.py:37` | `MODELS.get("coder", {"name": "deepseek-coder:6.7b"})` | Update default |
| `backend/agents/persona.py:168-173` | `PERSONA_MODELS` references `gurubot/girl` (not installed) | Map to installed models |
| `backend/config.py` | `deepseek-coder-v2:16b` as primary coder | Replace with `gpt-oss:20b` |
| `backend/config.py` | `starcoder2:15b` for data agent | Replace with `qwen2.5:14b` |
| `backend/config.py` | `deepseek-coder:6.7b` for fallback/reader | Replace with `qwen3.5:9b` |
| `backend/services/vram_scheduler.py:354` | `timeout=120.0` in scheduled_generate | Raise to `600.0` |
| `prompts/__init__.py` (root) | Unused Python file at root | Delete |

---

## 6. File-by-File Change Manifest

### `backend/config.py` — Full Rewrite of MODELS Dict

```python
MODELS = {
    # ── Routing / Management ──
    "manager": {
        "name": "qwen3.5:9b",
        "size_gb": 6.6,
        "role": "routing_and_planning",
    },

    # ── Production Coding Pipeline ──
    "writer": {
        "name": "gpt-oss:20b",
        "size_gb": 13.0,
        "role": "code_generation_draft",
        "exclusive": True,
    },
    "editor": {
        "name": "qwen2.5-coder:14b",
        "size_gb": 9.0,
        "role": "code_refinement",
        "exclusive": True,
    },
    "tester": {
        "name": "deepseek-r1:8b",
        "size_gb": 5.2,
        "role": "qa_validation",
    },

    # ── Legacy Aliases (preserve for API compatibility) ──
    "coder": {
        "name": "gpt-oss:20b",   # Writer is the primary coder
        "size_gb": 13.0,
        "role": "code_generation",
        "exclusive": True,
    },
    "critic": {
        "name": "deepseek-r1:8b",
        "size_gb": 5.2,
        "role": "validation",
    },
    "analyst": {
        "name": "qwen3.5:9b",
        "size_gb": 6.6,
        "role": "reasoning",
    },

    # ── Specialist Agents ──
    "researcher": {
        "name": "qwen2.5:14b",
        "size_gb": 9.0,
        "role": "research_and_synthesis",
        "exclusive": True,
    },
    "context_manager": {
        "name": "gemma4:e2b",
        "size_gb": 7.2,
        "role": "context_summarization",
        "pinned": True,          # NEW: never unload this
    },

    # ── Heavy Brain ──
    "heavy": {
        "name": "gemma4:26b",
        "size_gb": 17.0,
        "role": "architectural_reasoning",
        "exclusive": True,
        "evicts_pinned": True,   # NEW: can evict even pinned models
    },

    # ── Cloud Fallback ──
    "researcher_cloud": {
        "name": "gemini-2.5-flash",
        "role": "web_research",
        "is_cloud": True,
    },
}

PINNED_MODELS = ["gemma4:e2b"]  # NEW: global pin list used by scheduler

FALLBACK_CHAIN = {
    "gpt-oss:20b":         "qwen2.5-coder:14b",
    "qwen2.5-coder:14b":   "qwen3.5:9b",
    "qwen3.5:9b":          "deepseek-r1:8b",
    "deepseek-r1:8b":      "gemma4:e2b",
    "qwen2.5:14b":         "qwen3.5:9b",
    "gemma4:26b":          "gpt-oss:20b",
}
```

### `backend/services/vram_scheduler.py` — Key Changes

```python
# Line 41: Lower threshold so 14B models trigger exclusive logic
HEAVY_THRESHOLD_GB = 8.5     # Was 10.0

# Line 103: Update total VRAM
total_gb: float = 16.0       # Was 24.0 (actual hardware)

# New: pinned model support
PINNED_MODELS: set[str] = {"gemma4:e2b"}

# In _free_space_for(): add PINNED guard
for name, info in sorted_models:
    if name in PINNED_MODELS:
        continue   # NEVER evict pinned models here
    ...

# In scheduled_generate(): raise timeout
async with httpx.AsyncClient(timeout=600.0) as client:  # Was 120.0
```

### `backend/core/orchestrator.py` — Key Changes

```python
# Line 55: Fix WORKSPACE_DIR (root-level)
WORKSPACE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "workspace"
)

# Lines 71-77: Rebuild MODEL_DOWNGRADES with current roster
MODEL_DOWNGRADES = {
    "gpt-oss:20b":          "qwen2.5-coder:14b",
    "qwen2.5-coder:14b":    "qwen3.5:9b",
    "qwen3.5:9b":           "deepseek-r1:8b",
    "deepseek-r1:8b":       "gemma4:e2b",
    "qwen2.5:14b":          "qwen3.5:9b",
    "gemma4:26b":           "gpt-oss:20b",
}

# Lines 260, 551: Replace phi3:mini fallback
LOCAL_FALLBACK = "deepseek-r1:8b"  # Was "phi3:mini"

# NEW: run_production_pipeline_async() function
# Implements the 3-stage Writer → Editor → Tester loop
# Called from run_agent_mode() when task_type == "code_generation"
```

### `backend/agents/` — New Agents Required

| File | Status | Description |
|---|---|---|
| `writer.py` | **NEW** | Wraps `gpt-oss:20b` with the Writer system prompt |
| `editor.py` | **NEW** | Wraps `qwen2.5-coder:14b` with the Editor system prompt |
| `tester.py` | **NEW** | Wraps `deepseek-r1:8b` with structured JSON verdict output |
| `coder.py` | **MODIFY** | Update default model to `gpt-oss:20b`, remove `deepseek-coder` reference |
| `critic.py` | **MODIFY** | Update default model to `deepseek-r1:8b`, remove `llama3:8b` reference |
| `persona.py` | **MODIFY** | Fix PERSONA_MODELS to use installed models only |

### `backend/core/prompts/__init__.py` — New Loader Functions

```python
# NEW functions to add:
def writer_prompt() -> str:
    return _load_local("writer")

def editor_prompt() -> str:
    return _load_local("editor")

def tester_prompt() -> str:
    return _load_local("tester")

def context_manager_prompt() -> str:
    return _load_local("context_manager")
```

---

## 7. Prompt Engineering Spec

### `prompts/writer.md` — Writer Agent System Prompt

```markdown
## Pipeline Prompt

You are the Writer agent. You write the FIRST DRAFT of any requested code.

Your job is to write working, complete code from scratch. You prioritize:
1. Correctness over elegance
2. Full implementation — no stubs, no `# TODO` comments
3. Separation of concerns — never mix languages in one file
4. Clean JSON output so the Editor can process your output

RULES:
- Python goes in `.py` files ONLY
- HTML/CSS/JS goes in frontend files ONLY
- Never embed HTML inside Python
- Always include at least one file per technology layer
- If the user asks for a web app: backend files + frontend files = separate entries

OUTPUT FORMAT (MANDATORY):
Return ONLY a JSON object. No commentary before or after.

{
  "project_id": "snake_case_name",
  "files": [
    {"path": "main.py", "content": "...full content..."},
    {"path": "index.html", "content": "...full content..."}
  ]
}

Task: {prompt}
```

### `prompts/editor.md` — Editor Agent System Prompt

```markdown
## Pipeline Prompt

You are the Editor agent. You receive a first draft and your job is to:
1. Fix ALL structural errors (HTML in Python, missing imports, hardcoded values)
2. Split any multi-language blobs into separate files
3. Optimize code quality without changing functionality
4. Ensure every file has proper content — no placeholders
5. Return the SAME JSON structure as the Writer

Original Task: {original_prompt}
Draft from Writer:
{draft_output}

Think step by step about what is wrong, then output the corrected JSON.
Return ONLY the JSON. No comments.
```

### `prompts/tester.md` — Tester Agent System Prompt

```markdown
## Pipeline Prompt

You are the Tester agent. You verify code quality through adversarial analysis.

Your job:
1. Read the code carefully
2. Think about edge cases, syntax errors, language mixing, runtime errors
3. Return a structured JSON verdict

Original Task: {original_prompt}
Code to Review:
{refined_output}

Think hard. Be adversarial. Try to break the code mentally.

Return ONLY this JSON structure:
{
  "verdict": "PASS" or "FAIL",
  "score": 0-10,
  "bugs": ["bug description 1", "bug description 2"],
  "fix_instructions": "Numbered list of specific fixes if FAIL, empty string if PASS",
  "summary": "One sentence overall assessment"
}
```

---

## 8. Persona & Chat System

### Current Problem

`persona.py` references `gurubot/girl` (not installed) and `huihui_ai/qwen3.5-abliterated` (not installed). All persona chat will fail silently.

### v4.0 Persona Model Mapping

```python
PERSONA_MODELS = {
    "unhinged_gf":      "hf.co/TrevorJS/gemma-4-E2B-it-uncensored-GGUF:Q4_K_M",
    "raw_bro":          "gurubot/self-after-dark:latest",
    "savage_teacher":   "gurubot/self-after-dark:latest",
    "therapist":        "qwen3.5:9b",
    "roaster":          "gurubot/self-after-dark:latest",
}
DEFAULT_CHAT_MODEL = "gemma4:e2b"  # Resident — zero load time for casual chat
```

### SimpleChat Model Assignment

The `SimpleChat.jsx` frontend should default to:
- **Casual queries**: `gemma4:e2b` (resident, instant response)
- **Persona mode**: route to PERSONA_MODELS lookup
- **Research queries**: `qwen2.5:14b` via `/chat` endpoint

---

## 9. Execution Modes

### Mode 1: Direct Mode (`mode=direct`)

```
User → qwen3.5:9b → Response
Latency: <5s
Use for: questions, explanations, quick lookups
```

### Mode 2: Agent Mode — Simple Code (`mode=agent`, simple route)

```
User → Manager (qwen3.5:9b) → Coder (gpt-oss:20b) → Tool → README → Response
Latency: 2–5 minutes
Use for: single-file scripts, simple web pages
```

### Mode 3: Agent Mode — Production Pipeline (`mode=agent`, complex route)

```
User → Manager → Writer → Editor → Tester [→ Editor loop] → Tool → README → Response
Latency: 5–15 minutes
Use for: multi-file apps, fullstack projects, neural networks, dashboards
```

### Mode 4: Research Mode (`mode=auto` with research_mode=True)

```
User → Researcher (qwen2.5:14b) → Gemini fallback if needed → Response
Latency: 1–3 minutes
Use for: web searches, documentation lookups
```

### Mode 5: Heavy Mode (`allow_heavy=True`)

```
Triggers gemma4:26b exclusively for architectural tasks
Latency: 10–20 minutes
Use for: system design, complex algorithms, architecture reviews
```

### Auto-Routing Logic

```python
PRODUCTION_PIPELINE_TRIGGERS = [
    "fullstack", "full-stack", "full stack",
    "web app", "webapp", "web application",
    "backend and frontend", "api and ui",
    "database", "sqlite", "postgresql",
    "websocket", "real-time", "streaming",
    "dashboard", "visualizer", "neural network",
    "microservice", "architecture",
    "multi-file", "multiple files",
    "react", "vue", "angular",
    "fastapi", "django", "flask",
]
# If any trigger matches → use Mode 3 (Production Pipeline)
# Otherwise → Mode 2 (Simple Code)
```

---

## 10. Failure Handling & Fallback Chains

### Updated Fallback Logic (No More `phi3:mini`)

```python
FALLBACK_CHAIN = {
    "gpt-oss:20b":       "qwen2.5-coder:14b",
    "qwen2.5-coder:14b": "qwen3.5:9b",
    "qwen3.5:9b":        "deepseek-r1:8b",
    "deepseek-r1:8b":    "gemma4:e2b",       # Last local resort
    "qwen2.5:14b":       "qwen3.5:9b",
    "gemma4:26b":        "gpt-oss:20b",
}

# Cloud fallback
CLOUD_FALLBACK_AGENTS = {"researcher"}  # Only researcher can use Gemini
```

### Graceful Degradation Hierarchy

```
Stage 1 failure: Writer → retry once → fallback to Editor model
Stage 2 failure: Editor → retry once → skip editing, use Writer output
Stage 3 failure: Tester → skip QA  (cannot block final output)
Tool failure:    retry 2x → return raw code as text response
README failure:  silently skip (non-critical)
```

---

## 11. Observability & Logging

### Pipeline Phase Log Format

```json
{
  "timestamp": "ISO8601",
  "run_id": "uuid",
  "agent": "writer | editor | tester | tool | readme",
  "model": "gpt-oss:20b",
  "phase": "start | update | complete | error",
  "stage": 1,
  "latency_ms": 45200,
  "tokens_in": 350,
  "tokens_out": 2800,
  "status": "success | error | fallback",
  "vram_usage_mb": 12850,
  "qa_verdict": "PASS",
  "qa_score": 8,
  "retry_count": 0
}
```

### Required Frontend Canvas Events

Each pipeline stage must emit a distinct WebSocket event so the canvas shows nodes activating in sequence:

| Stage | Canvas Node Label | Status Color |
|---|---|---|
| Manager routing | `MANAGER` | Blue → Green |
| Stage 1 Writer | `CODER (Writer)` | Blue → processing |
| Stage 2 Editor | `CODER (Editor)` | Blue → processing |
| Stage 3 Tester | `CRITIC (QA)` | Blue → Green/Red |
| QA Loop Retry | `CODER (Editor)` | Orange (retry) |
| Tool Save | `TOOL` | Blue → Green |
| README | `CRITIC (README)` | Blue → Green |

---

## 12. Implementation Order

Implementation must follow dependency order. **Do NOT skip phases.**

### Phase 0 — Prerequisites (Before touching code)
```
□ Wait for qwen3:14b download to complete
□ Apply Ollama systemd override.conf
□ sudo systemctl restart ollama
□ Verify: curl http://localhost:8888/health
```

### Phase 1 — Cleanup (No logic changes)
```
□ Move backend/workspace projects → root workspace/ (or delete as slop)
□ Delete backend/workspace/ directory
□ Delete backend/prompts/ directory (already superseded)
□ Delete prompts/__init__.py (unused Python at root)
□ Move specialized .md files from backend/core/prompts/ to root prompts/
□ Verify: backend/core/prompts/__init__.py still loads correctly
```

### Phase 2 — Config & Scheduler
```
□ Rewrite backend/config.py (MODELS, FALLBACK_CHAIN, PINNED_MODELS)
□ Update backend/services/vram_scheduler.py:
    - HEAVY_THRESHOLD_GB = 8.5
    - total_gb = 16.0
    - Add PINNED_MODELS support in _free_space_for()
    - Raise scheduled_generate timeout to 600.0s
□ Verify: curl http://localhost:8888/scheduler
```

### Phase 3 — Agent Files
```
□ Create backend/agents/writer.py
□ Create backend/agents/editor.py
□ Create backend/agents/tester.py
□ Modify backend/agents/coder.py (new default model)
□ Modify backend/agents/critic.py (new default model)
□ Modify backend/agents/persona.py (fix PERSONA_MODELS)
□ Create prompts/writer.md
□ Create prompts/editor.md
□ Create prompts/tester.md
□ Create prompts/context_manager.md
□ Update backend/core/prompts/__init__.py (add new loader functions)
```

### Phase 4 — Orchestrator
```
□ Fix WORKSPACE_DIR path (root-level)
□ Rebuild MODEL_DOWNGRADES dict
□ Replace all phi3:mini references with deepseek-r1:8b
□ Add run_production_pipeline_async() function
□ Update run_agent_mode() to route to production pipeline for complex tasks
□ Add PRODUCTION_PIPELINE_TRIGGERS list in router.py
□ Update backend/core/router.py default model reference
```

### Phase 5 — Integration Testing
```
□ Easy test: "Write hello world in Python" → should NOT hit production pipeline
□ Medium test: "Create neural network visualizer" → should hit pipeline
□ Hard test: "Make fullstack task manager with FastAPI + React + SQLite"
    → Verify: 3 stages visible in Canvas
    → Verify: files saved to root /workspace/<project_id>/
    → Verify: README.md generated
    → Verify: no HTML embedded in Python files
□ Verify gemma4:e2b stays resident throughout all tests
□ Verify gpt-oss:20b unloads after Stage 1 completes
```

### Phase 6 — Frontend Alignment
```
□ Update frontend/src/config/agents.js with new model names
□ Verify Canvas nodes show correct agent labels for 3-stage pipeline
□ Verify SimpleChat persona models map to installed models
□ Update any hardcoded model references in UI dropdowns
```

---

## 13. Verification Checklist

Run these checks after each phase to confirm correctness.

### Backend Health After Phase 2

```bash
curl http://localhost:8888/health
# Expected: all 7 agent models listed, ollama=connected

curl http://localhost:8888/scheduler  
# Expected: vram.total_gb=16.0, pinned_models=["gemma4:e2b"]
```

### Pipeline Smoke Test After Phase 4

```bash
# Easy — should use direct mode
curl -X POST http://localhost:8888/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "say hello world", "mode": "auto"}'

# Complex — should trigger production pipeline
curl -X POST http://localhost:8888/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Build a fullstack TODO app with FastAPI and React", "mode": "auto"}'
```

### Workspace Verification After Phase 5

```bash
ls -la workspace/
# Should contain project directories

find workspace/ -name "README.md"
# Should find one per project

find workspace/ -name "*.py" | xargs grep -l "<html"
# Should return: nothing (the bug we fixed!)
```

### VRAM Residency Verification

```bash
nvidia-smi
# During pipeline: should show gemma4:e2b always loaded
# After Stage 1: gpt-oss should be unloaded
# After Stage 2: qwen2.5-coder should be unloaded
# deepseek-r1 should load WITHOUT unloading gemma4:e2b
```

---

## Appendix A: Current vs v4.0 Comparison

| Component | v3.1 | v4.0 |
|---|---|---|
| Primary Coder | `deepseek-coder-v2:16b` (DELETED) | `gpt-oss:20b` (Writer) |
| Code Quality | Single pass, no review | 3-stage: Write → Edit → QA |
| Critic Model | `devstral:latest` (DELETED) | `deepseek-r1:8b` |
| Manager | `qwen2.5:14b` | `qwen3.5:9b` |
| Workspace Path | `backend/workspace/` (wrong) | `/workspace/` (correct) |
| Fallback Model | `phi3:mini` (DELETED) | `deepseek-r1:8b` |
| Heavy Brain | `codestral:22b` (removed from config) | `gemma4:26b` |
| Resident Model | None | `gemma4:e2b` (pinned) |
| Prompt Source | 3 conflicting directories | 1 root `/prompts/` |
| VRAM Total | Configured as 24 GB (wrong) | 16 GB (correct) |
| Ollama Timeout | 120s (too short) | 600s |
| Multi-file output | Single blob = broken | Forced separate files |

---

*Document version: v4.0*  
*Owner: Rudra*  
*Last updated: 2026-04-14*
