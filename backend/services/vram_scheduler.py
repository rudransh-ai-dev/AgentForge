"""
VRAM-Aware Model Scheduler (Core Engine)
=========================================
This is the foundation layer that ALL other components depend on.

Key Responsibilities:
1. Model Registry — knows every model's size and type
2. VRAM State Tracker — tracks what's loaded in GPU memory
3. Allocation Logic — decides if a model can co-run or needs exclusive access
4. Load/Unload Controller — talks to Ollama API to manage GPU memory
5. Global Pipeline Lock — prevents race conditions from concurrent requests

Architecture Rules Enforced:
- Models < 10GB can co-run with Manager (no unload needed)
- Models >= 10GB require exclusive VRAM (unload everything first)
- FIFO task queue prevents model conflicts from rapid requests
- Automatic fallback if a model fails to load
"""

import asyncio
import httpx
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("vram_scheduler")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"
    ))
    logger.addHandler(handler)

# ────────────────────────────────────────────────────────────────
# 1. MODEL REGISTRY
# ────────────────────────────────────────────────────────────────

OLLAMA_BASE = "http://localhost:11434"
HEAVY_THRESHOLD_GB = 8.5

# Static registry — updated dynamically on health check
MODEL_REGISTRY: dict[str, dict] = {}

# v4.0: Models that should never be unloaded from VRAM
PINNED_MODELS: set[str] = {"llama3.1:8b"}


def _parse_size_gb(size_bytes: int) -> float:
    """Convert bytes to GB."""
    return round(size_bytes / (1024 ** 3), 1)


async def sync_model_registry():
    """
    Fetch all installed models from Ollama and build the registry
    with accurate sizes. Called on startup and periodically.
    """
    global MODEL_REGISTRY
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{OLLAMA_BASE}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                registry = {}
                for m in data.get("models", []):
                    name = m["name"]
                    size_gb = _parse_size_gb(m.get("size", 0))
                    model_type = (
                        "large" if size_gb >= HEAVY_THRESHOLD_GB
                        else "small" if size_gb < 3.0
                        else "medium"
                    )
                    registry[name] = {
                        "size_gb": size_gb,
                        "type": model_type,
                        "is_heavy": size_gb >= HEAVY_THRESHOLD_GB,
                    }
                MODEL_REGISTRY = registry
                logger.info(f"📦 Model registry synced: {len(registry)} models")
                for name, info in registry.items():
                    icon = "🔴" if info["is_heavy"] else "🟢"
                    logger.info(f"   {icon} {name}: {info['size_gb']}GB ({info['type']})")
                return registry
    except Exception as e:
        logger.error(f"❌ Failed to sync model registry: {e}")
    return MODEL_REGISTRY


def get_model_info(model_name: str) -> dict:
    """Get model info from registry, with sensible defaults if unknown."""
    if model_name in MODEL_REGISTRY:
        return MODEL_REGISTRY[model_name]
    # Unknown model — assume medium to be safe
    return {"size_gb": 5.0, "type": "medium", "is_heavy": False}


# ────────────────────────────────────────────────────────────────
# 2. VRAM STATE TRACKER
# ────────────────────────────────────────────────────────────────

@dataclass
class VRAMState:
    """Tracks current GPU memory usage and loaded models."""
    total_gb: float = 48.0  # 16GB VRAM + System RAM spillover
    used_gb: float = 0.0
    active_models: dict = field(default_factory=dict)  # name -> {size_gb, loaded_at}

    @property
    def free_gb(self) -> float:
        return self.total_gb - self.used_gb

    @property
    def has_heavy_model(self) -> bool:
        return any(
            info.get("size_gb", 0) >= HEAVY_THRESHOLD_GB
            for info in self.active_models.values()
        )

    def __repr__(self):
        models = ", ".join(
            f"{name}({info['size_gb']}GB)"
            for name, info in self.active_models.items()
        )
        return f"VRAM[{self.used_gb:.1f}/{self.total_gb}GB | {models or 'empty'}]"


# Global singleton
vram_state = VRAMState()


# ────────────────────────────────────────────────────────────────
# 3. ALLOCATION LOGIC (Critical Decision Engine)
# ────────────────────────────────────────────────────────────────

def can_load(model_name: str) -> tuple[bool, str]:
    """
    Decide if a model can be loaded into VRAM right now.

    Returns (can_load: bool, reason: str)

    Rules:
    - If model is already loaded → yes (reuse)
    - If model is heavy (>=10GB) → only if VRAM is completely empty
    - If any heavy model is currently loaded → nothing else can load
    - If model is light (<10GB) → load if there's enough free space
    """
    if model_name in vram_state.active_models:
        return True, "already_loaded"

    info = get_model_info(model_name)
    size = info["size_gb"]

    # RULE 1: Heavy model needs exclusive access
    if info["is_heavy"]:
        if vram_state.used_gb == 0:
            return True, "exclusive_slot_available"
        else:
            return False, f"heavy_model_needs_exclusive_vram (current: {vram_state.used_gb:.1f}GB used)"

    # RULE 2: If a heavy model is already loaded, nothing else can co-run
    if vram_state.has_heavy_model:
        return False, "heavy_model_blocking_vram"

    # RULE 3: Light model — check if there's enough space
    if (vram_state.used_gb + size) <= vram_state.total_gb:
        return True, f"co-run_ok ({vram_state.used_gb + size:.1f}/{vram_state.total_gb}GB)"
    else:
        return False, f"insufficient_vram ({vram_state.free_gb:.1f}GB free, need {size}GB)"


# ────────────────────────────────────────────────────────────────
# 4. LOAD / UNLOAD CONTROLLER (Ollama API)
# ────────────────────────────────────────────────────────────────

async def _ollama_load(model_name: str) -> bool:
    """
    Tell Ollama to load a model into VRAM.
    Uses a minimal generate request with keep_alive to warm the model.
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Sending a minimal request loads the model into memory
            resp = await client.post(
                f"{OLLAMA_BASE}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "",
                    "keep_alive": "5m",  # Keep warm for 5 minutes
                    "stream": False,
                },
            )
            if resp.status_code == 200:
                logger.info(f"✅ Loaded '{model_name}' into VRAM")
                return True
            else:
                logger.error(f"❌ Failed to load '{model_name}': HTTP {resp.status_code}")
                return False
    except Exception as e:
        logger.error(f"❌ Failed to load '{model_name}': {e}")
        return False


async def _ollama_unload(model_name: str) -> bool:
    """
    Tell Ollama to unload a model from VRAM.
    Uses keep_alive=0 to immediately release memory.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{OLLAMA_BASE}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "",
                    "keep_alive": "0",  # Unload immediately
                    "stream": False,
                },
            )
            if resp.status_code == 200:
                logger.info(f"🗑️  Unloaded '{model_name}' from VRAM")
                return True
            else:
                logger.warning(f"⚠️  Unload '{model_name}' returned HTTP {resp.status_code}")
                return False
    except Exception as e:
        logger.warning(f"⚠️  Failed to unload '{model_name}': {e}")
        return False


async def unload_all():
    """Unload ALL models from VRAM. Used before loading a heavy model."""
    logger.info(f"🧹 Unloading all models from VRAM: {list(vram_state.active_models.keys())}")
    tasks = [_ollama_unload(name) for name in list(vram_state.active_models.keys())]
    if tasks:
        await asyncio.gather(*tasks)
    vram_state.active_models.clear()
    vram_state.used_gb = 0.0
    logger.info("🧹 VRAM cleared")


async def ensure_model_loaded(model_name: str) -> bool:
    """
    The main entry point for the scheduler.

    Ensures a model is loaded and ready in VRAM.
    Handles all allocation logic, unloading, and loading automatically.

    Returns True if the model is ready, False if loading failed.
    """
    loadable, reason = can_load(model_name)

    if loadable and reason == "already_loaded":
        logger.info(f"♻️  '{model_name}' already in VRAM — reusing")
        return True

    if not loadable:
        info = get_model_info(model_name)
        if info["is_heavy"]:
            # Heavy model needs exclusive access — unload everything
            logger.info(f"⚡ Heavy model '{model_name}' requested — clearing VRAM")
            await unload_all()
        else:
            # Not enough space — unload the oldest non-essential model
            logger.info(f"📦 Need space for '{model_name}' — freeing VRAM")
            await _free_space_for(model_name)

    # Now load the model
    info = get_model_info(model_name)
    start = time.time()
    success = await _ollama_load(model_name)

    if success:
        vram_state.active_models[model_name] = {
            "size_gb": info["size_gb"],
            "loaded_at": time.time(),
        }
        vram_state.used_gb += info["size_gb"]
        load_time = (time.time() - start) * 1000
        logger.info(f"📊 {vram_state} (load took {load_time:.0f}ms)")
        return True
    else:
        logger.error(f"❌ Failed to load '{model_name}' — pipeline cannot continue")
        return False


async def _free_space_for(model_name: str):
    """
    Intelligently free VRAM space for a new model.
    Unloads the oldest, least-needed model first.
    Never unloads a model that's actively generating.
    """
    needed = get_model_info(model_name)["size_gb"]

    # Sort loaded models by load time (oldest first)
    sorted_models = sorted(
        vram_state.active_models.items(),
        key=lambda x: x[1]["loaded_at"]
    )

    for name, info in sorted_models:
        if vram_state.free_gb >= needed:
            break
        # v4.0: Never evict pinned models (unless the requestor is an evicts_pinned model)
        if name in PINNED_MODELS:
            continue
        await _ollama_unload(name)
        vram_state.used_gb -= info["size_gb"]
        del vram_state.active_models[name]


async def release_model(model_name: str):
    """
    Explicitly release a model from VRAM after use.
    Called after a heavy model finishes execution.
    """
    if model_name in vram_state.active_models:
        info = vram_state.active_models[model_name]
        await _ollama_unload(model_name)
        vram_state.used_gb -= info["size_gb"]
        del vram_state.active_models[model_name]
        logger.info(f"📊 Released '{model_name}' — {vram_state}")


# ────────────────────────────────────────────────────────────────
# 5. GLOBAL PIPELINE LOCK + TASK QUEUE
# ────────────────────────────────────────────────────────────────

# FIFO lock — one pipeline execution at a time
pipeline_lock = asyncio.Lock()


async def scheduled_generate(model: str, prompt: str, stream: bool = True):
    """
    The SAFE way to call any model. Wraps every request with:
    1. Pipeline lock (prevents race conditions)
    2. VRAM allocation (ensures model fits)
    3. Automatic cleanup for heavy models

    Usage:
        async for chunk in scheduled_generate("mixtral:latest", "Write a poem"):
            print(chunk)
    """
    async with pipeline_lock:
        info = get_model_info(model)

        # Step 1: Ensure model is loaded
        loaded = await ensure_model_loaded(model)
        if not loaded:
            if stream:
                yield f"\n\n⚠️ Error: Failed to load model '{model}' into VRAM"
                return
            else:
                raise RuntimeError(f"Failed to load model '{model}'")

        # Step 2: Execute the request
        try:
            if stream:
                async with httpx.AsyncClient(timeout=600.0) as client:
                    async with client.stream(
                        "POST",
                        f"{OLLAMA_BASE}/api/generate",
                        json={"model": model, "prompt": prompt, "stream": True},
                    ) as response:
                        import json as _json
                        async for line in response.aiter_lines():
                            if line:
                                try:
                                    data = _json.loads(line)
                                    text = data.get("response", "")
                                    if text:
                                        yield text
                                except Exception:
                                    pass
            else:
                async with httpx.AsyncClient(timeout=600.0) as client:
                    resp = await client.post(
                        f"{OLLAMA_BASE}/api/generate",
                        json={"model": model, "prompt": prompt, "stream": False},
                    )
                    data = resp.json()
                    yield data.get("response", "")

        finally:
            # Step 3: Auto-release heavy models after use
            if info["is_heavy"]:
                logger.info(f"🔒 Auto-releasing heavy model '{model}' after execution")
                await release_model(model)
            # Step 4: Sample VRAM state for metrics
            try:
                from services.metrics import record_vram_sample
                state = vram_state
                record_vram_sample(
                    total_gb=state.total_gb,
                    used_gb=state.used_gb,
                    active_models=list(state.active_models.keys())
                )
            except Exception:
                pass


async def scheduled_generate_sync(model: str, prompt: str) -> str:
    """
    Non-streaming version of scheduled_generate.
    Returns the full response as a string.
    """
    result = ""
    async for chunk in scheduled_generate(model, prompt, stream=False):
        result += chunk
    return result


# ────────────────────────────────────────────────────────────────
# 6. SCHEDULER STATUS API (For Frontend/Dashboard)
# ────────────────────────────────────────────────────────────────

def get_scheduler_status() -> dict:
    """Returns current scheduler state for the frontend dashboard."""
    return {
        "vram": {
            "total_gb": vram_state.total_gb,
            "used_gb": round(vram_state.used_gb, 1),
            "free_gb": round(vram_state.free_gb, 1),
            "utilization_pct": round(
                (vram_state.used_gb / vram_state.total_gb) * 100, 1
            ) if vram_state.total_gb > 0 else 0,
        },
        "active_models": {
            name: {
                "size_gb": info["size_gb"],
                "loaded_seconds_ago": round(time.time() - info["loaded_at"]),
            }
            for name, info in vram_state.active_models.items()
        },
        "model_count": len(vram_state.active_models),
        "pipeline_locked": pipeline_lock.locked(),
        "registry_size": len(MODEL_REGISTRY),
        "heavy_threshold_gb": HEAVY_THRESHOLD_GB,
    }
