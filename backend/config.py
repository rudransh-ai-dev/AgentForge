OLLAMA_URL = "http://localhost:11434/api/generate"

MODELS = {
    "manager": {
        "name": "phi3:mini",
        "size_gb": 2.2,
        "role": "planning"
    },
    "coder": {
        "name": "deepseek-coder:6.7b",
        "size_gb": 3.8,
        "role": "code_generation"
    },
    "analyst": {
        "name": "llama3:8b",
        "size_gb": 4.7,
        "role": "reasoning"
    },
    "critic": {
        "name": "llama3:8b",
        "size_gb": 4.7,
        "role": "validation"
    },
    "heavy": {
        "name": "qwen3.5:35b-a3b",
        "size_gb": 23,
        "role": "deep_reasoning",
        "exclusive": True
    },
    "fallback": {
        "name": "yolo0perris/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-GGUF_Q3_K_M:latest",
        "size_gb": 13,
        "role": "fallback_reasoning",
        "exclusive": True
    },
    "data": {
        "name": "mixtral:latest",
        "size_gb": 26,
        "role": "data_analysis",
        "exclusive": True
    }
}

TASK_ROUTER = {
    "code_generation": "coder",
    "debug_basic": "coder",
    "debug_complex": "heavy",
    "explanation": "analyst",
    "analysis": "analyst",
    "review": "critic",
    "data_task": "data"
}