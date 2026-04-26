import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = "http://localhost:11434/api/generate"


# ══════════════════════════════════════════════════════════════
# v4.0 — 7-Agent Production Roster
# Hardware: RTX 5070 Ti — 16 GB GDDR7 VRAM
# ══════════════════════════════════════════════════════════════

MODELS = {
    # ── Routing / Management ──
    "manager": {
        "name": "llama3.1:8b",
        "size_gb": 6.6,
        "role": "routing_and_planning",
    },
    "specifier": {
        "name": "llama3.1:8b",
        "size_gb": 6.6,
        "role": "requirements_specification",
    },

    # ── Production Coding Pipeline (3-Stage) ──
    # Demo config: writer and editor share the same model so the pipeline
    # loads qwen2.5-coder:14b exactly once instead of swapping 20B→14B.
    # Saves ~30-60s per run. Deep Think mode still swaps to codestral:22b.
    "writer": {
        "name": "qwen2.5-coder:14b",
        "size_gb": 9.0,
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
        "name": "llama3.1:8b",
        "size_gb": 4.9,
        "role": "qa_validation",
    },

    # ── Legacy Aliases (API compatibility with existing canvas/frontend) ──
    "coder": {
        "name": "qwen2.5-coder:14b",
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
        "name": "llama3.1:8b",
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
        "name": "llama3.1:8b",
        "size_gb": 7.2,
        "role": "selective_context_and_retrieval",
        "pinned": True,
    },

    # ── Heavy Brain (architecture-level fallback) ──
    "heavy": {
        "name": "codestral:22b",
        "size_gb": 12.0,
        "role": "architectural_reasoning",
        "exclusive": True,
        "evicts_pinned": True,
    },

    # ── Specialist Agents ──

    # ── Reader (uses resident model) ──
    "reader": {
        "name": "llama3.1:8b",
        "size_gb": 7.2,
        "role": "project_analysis",
        "pinned": True,
    },
}

# Models that should never be unloaded from VRAM
PINNED_MODELS = ["llama3.1:8b"]

# Fallback chain: if primary fails, try next
FALLBACK_CHAIN = {
    "qwen2.5-coder:14b":  "qwen2.5:14b",
    "qwen2.5:14b":        "llama3.1:8b",
    "llama3.1:8b":        "deepseek-r1:8b",
    "deepseek-r1:8b":     "llama3.1:8b",
    "qwen3.5:9b":         "llama3.1:8b",
    "gpt-oss:20b":        "qwen2.5-coder:14b",
    "phi4:latest":        "qwen2.5-coder:14b",
    "gemma4:26b":         "gpt-oss:20b",
}

TASK_ROUTER = {
    "code_generation": "writer",
    "code_refinement": "editor",
    "debug_basic": "editor",
    "debug_complex": "heavy",
    "explanation": "analyst",
    "analysis": "analyst",
    "review": "tester",
    "qa_validation": "tester",
    "research": "researcher",
    "web_search": "researcher",
    "read_code": "reader",
    "project_context": "reader",
    "specification": "specifier",
}

AVAILABLE_MODELS = {
    "manager": "llama3.1:8b",
    "specifier": "llama3.1:8b",
    "writer": "qwen2.5-coder:14b",
    "editor": "qwen2.5-coder:14b",
    "tester": "llama3.1:8b",
    "coder": "qwen2.5-coder:14b",
    "critic": "deepseek-r1:8b",
    "analyst": "llama3.1:8b",
    "researcher": "qwen2.5:14b",
    "context_manager": "llama3.1:8b",
    "reader": "llama3.1:8b",
    "heavy": "phi4:latest",
}

AUTO_HEAVY_TRIGGERS = [MODELS["heavy"]["name"]]
