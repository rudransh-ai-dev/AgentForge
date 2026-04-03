OLLAMA_URL = "http://localhost:11434/api/generate"

MODELS = {
    "manager": {"name": "qwen2.5:14b", "size_gb": 9.0, "role": "planning"},
    "coder": {
        "name": "deepseek-coder-v2:16b",
        "size_gb": 8.9,
        "role": "code_generation",
    },
    "analyst": {"name": "qwen2.5:14b", "size_gb": 9.0, "role": "reasoning"},
    "critic": {"name": "devstral:24b", "size_gb": 14, "role": "validation"},
    "heavy": {
        "name": "codestral:22b",
        "size_gb": 12,
        "role": "deep_reasoning",
        "exclusive": True,
    },
    "ultra_heavy": {
        "name": "yolo0perris/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-GGUF_Q3_K_M:latest",
        "size_gb": 13,
        "role": "ultra_deep_reasoning",
        "exclusive": True,
    },
    "fast_driver": {
        "name": "qwen2.5-coder:7b",
        "size_gb": 4.7,
        "role": "fast_code_generation",
    },
    "fallback": {
        "name": "deepseek-coder:6.7b",
        "size_gb": 3.8,
        "role": "fallback_reasoning",
    },
    "data": {
        "name": "starcoder2:15b",
        "size_gb": 9.1,
        "role": "data_analysis",
        "exclusive": True,
    },
    "reader": {
        "name": "deepseek-coder:6.7b",
        "size_gb": 3.8,
        "role": "project_analysis",
    },
}

TASK_ROUTER = {
    "code_generation": "coder",
    "debug_basic": "coder",
    "debug_complex": "heavy",
    "explanation": "analyst",
    "analysis": "analyst",
    "review": "critic",
    "data_task": "data",
    "read_code": "reader",
    "project_context": "reader",
}

AVAILABLE_MODELS = {
    "manager": "qwen2.5:14b",
    "coder": "deepseek-coder-v2:16b",
    "analyst": "qwen2.5:14b",
    "critic": "devstral:24b",
    "heavy": "codestral:22b",
    "ultra_heavy": "yolo0perris/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-GGUF_Q3_K_M:latest",
    "fast_driver": "qwen2.5-coder:7b",
    "fallback": "deepseek-coder:6.7b",
    "data": "starcoder2:15b",
    "reader": "deepseek-coder:6.7b",
}

AUTO_HEAVY_TRIGGERS = [MODELS["heavy"]["name"], MODELS["ultra_heavy"]["name"]]
