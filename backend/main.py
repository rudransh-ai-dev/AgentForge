"""
AI Agent IDE — Main API Server (v3.1 Final)
============================================

Production-grade multi-agent orchestration server.

Execution Modes:
  - Direct Mode: User → Model → Response (<2s target)
  - Agent Mode:  User → Router → Planner → Agent(s) → Manager → Output (<15s target)

All models are VRAM-scheduled through the global pipeline lock.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import time
import uuid
import json
import os
import shutil
import asyncio

from schemas.request import Query, NodeQuery
from core.orchestrator import run_direct_mode, run_agent_mode, pipeline_lock
from core.router import route_task_async
from agents.coder import run_coder_async
from agents.analyst import run_analyst_async
from agents.critic import run_critic_async
from agents.tool import run_tool_agent_async, execute_project_async, autofix_loop_async
from agents.reader import run_reader_async
from services.event_emitter import emitter
from core.memory import store_run, update_pattern, get_run_history, get_stats
from core.session import (
    create_session,
    get_session,
    add_turn,
    list_sessions,
    update_session,
)
from config import MODELS
from services.ollama_client import async_generate_stream, check_ollama_health
from services.vram_scheduler import (
    sync_model_registry,
    get_scheduler_status,
    ensure_model_loaded,
    release_model,
    scheduled_generate,
    MODEL_REGISTRY,
    vram_state,
)
from core.prompts import (
    manager_chat_prompt,
    coder_chat_prompt,
    analyst_chat_prompt,
    critic_chat_prompt,
    reader_chat_prompt,
    qa_chat_prompt,
    manager_prompt,
    coder_prompt,
    analyst_prompt,
    critic_prompt,
)

WORKSPACE_DIR = os.path.join(os.path.dirname(__file__), "workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)

# Global execution tracking for stop/cancel
active_tasks = {}  # run_id -> asyncio.Task

app = FastAPI(
    title="AI Agent IDE",
    description="VRAM-aware multi-agent inference pipeline",
    version="3.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "AI Orchestrator Running", "version": "3.1 — Full Pipeline"}


# ══════════════════════════════════════════════════════════════
# STARTUP
# ══════════════════════════════════════════════════════════════


@app.on_event("startup")
async def startup_sync_registry():
    """Sync model registry from Ollama on server boot."""
    await sync_model_registry()


# ══════════════════════════════════════════════════════════════
# HEALTH + STATUS
# ══════════════════════════════════════════════════════════════


@app.get("/health")
async def health():
    """Check Ollama connectivity, list models, and scheduler state."""
    ollama_status = await check_ollama_health()
    configured_flat = {
        k: (v["name"] if isinstance(v, dict) else v) for k, v in MODELS.items()
    }
    return {
        "backend": "running",
        "ollama": ollama_status["status"],
        "models": ollama_status.get("models", []),
        "configured": configured_flat,
        "scheduler": get_scheduler_status(),
    }


@app.get("/scheduler/status")
def scheduler_status():
    """Dedicated endpoint for real-time VRAM scheduler state."""
    return get_scheduler_status()


@app.post("/scheduler/sync")
async def scheduler_sync():
    """Force re-sync model registry from Ollama."""
    registry = await sync_model_registry()
    return {"synced": len(registry), "models": list(registry.keys())}


@app.get("/prompts")
async def get_prompts():
    """Return all agent prompts from the single source of truth."""
    return {
        "manager": {
            "pipeline": manager_prompt(),
            "chat": manager_chat_prompt(),
        },
        "coder": {
            "pipeline": coder_prompt(),
            "chat": coder_chat_prompt(),
        },
        "analyst": {
            "pipeline": analyst_prompt(),
            "chat": analyst_chat_prompt(),
        },
        "critic": {
            "pipeline": critic_prompt(),
            "chat": critic_chat_prompt(),
        },
    }


@app.put("/config/models")
def update_model_config(body: dict):
    """Update the assigned model for a specific agent role."""
    for key, val in body.items():
        if key in MODELS:
            MODELS[key] = val
    return MODELS


# ══════════════════════════════════════════════════════════════
# WEBSOCKET — Real-time event stream
# ══════════════════════════════════════════════════════════════


@app.websocket("/ws/agent-stream")
async def websocket_endpoint(websocket: WebSocket):
    await emitter.connect(websocket)
    try:
        while True:
            # Keep connection alive — client may send ping/pong or nothing
            # We just wait for disconnect. Any received text is ignored.
            await websocket.receive_text()
    except WebSocketDisconnect:
        emitter.disconnect(websocket)
    except Exception:
        emitter.disconnect(websocket)


# ══════════════════════════════════════════════════════════════
# DUAL-MODE EXECUTION — The main entry points
# ══════════════════════════════════════════════════════════════


class RunRequest(BaseModel):
    prompt: str
    mode: str = "auto"  # "direct", "agent", or "auto"
    session_id: Optional[str] = None
    model: Optional[str] = None
    allow_heavy: bool = False


@app.post("/run")
async def run(body: RunRequest):
    """
    Main execution endpoint with Dual-Mode support.

    Modes:
      - "direct": Skip pipeline, single model response (<2s)
      - "agent":  Full orchestration pipeline (<15s)
      - "auto":   Router decides based on task complexity
    """
    async with pipeline_lock:
        # Create session if not provided
        session_id = body.session_id
        if not session_id:
            session_id = create_session()

        mode = body.mode

        # AUTO mode: let the router decide
        if mode == "auto":
            is_complex = any(
                kw in body.prompt.lower()
                for kw in [
                    "build",
                    "create",
                    "project",
                    "implement",
                    "system",
                    "multi",
                    "full",
                    "complete",
                    "app",
                    "application",
                    "write a",
                    "develop",
                    "architect",
                ]
            )
            mode = "agent" if is_complex else "direct"

        if mode == "direct":
            result = await run_direct_mode(
                body.prompt,
                session_id=session_id,
                model_override=body.model,
            )
        else:
            result = await run_agent_mode(
                body.prompt,
                session_id=session_id,
                allow_heavy=body.allow_heavy,
            )

        return {
            **result.model_dump(),
            "session_id": session_id,
            "mode": mode,
        }


# Legacy endpoint — backwards compatible
@app.post("/run-legacy")
async def run_legacy(query: Query):
    """Legacy /run endpoint for backwards compatibility."""
    body = RunRequest(prompt=query.prompt, mode="auto")
    return await run(body)


# ══════════════════════════════════════════════════════════════
# DIRECT AGENT PROMPT (Node-level)
# ══════════════════════════════════════════════════════════════


@app.post("/run-node")
async def run_node(query: NodeQuery):
    run_id = str(uuid.uuid4())
    agent_id = query.agent_id

    await emitter.emit(
        run_id, agent_id, "start", input_str=f"Direct Prompt: {query.prompt}"
    )

    agent_start = time.time()
    result = ""

    try:
        if agent_id == "coder":
            async for chunk in run_coder_async(query.prompt):
                result += chunk
                await emitter.emit(run_id, agent_id, "update", output_str=result)
        elif agent_id == "critic":
            async for chunk in run_critic_async(query.prompt):
                result += chunk
                await emitter.emit(run_id, agent_id, "update", output_str=result)
        else:
            async for chunk in run_analyst_async(query.prompt):
                result += chunk
                await emitter.emit(run_id, agent_id, "update", output_str=result)

        agent_latency = int((time.time() - agent_start) * 1000)
        await emitter.emit(
            run_id,
            agent_id,
            "complete",
            output_str=result,
            metadata={
                "latency_ms": agent_latency,
                "tokens": len(result),
                "direct_prompt": True,
            },
        )

        if agent_id == "coder" and ("```" in result or "def " in result):
            await run_tool_agent_async(run_id, result)

        return {"result": result, "run_id": run_id}

    except Exception as e:
        await emitter.emit(run_id, agent_id, "error", error=str(e))
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════
# WORKSPACE API
# ══════════════════════════════════════════════════════════════


@app.get("/workspace")
def list_workspace():
    """List all projects and their files."""
    projects = []
    for item in sorted(os.listdir(WORKSPACE_DIR)):
        item_path = os.path.join(WORKSPACE_DIR, item)
        if item.startswith("."):
            continue
        if os.path.isdir(item_path):
            meta_path = os.path.join(item_path, "project.json")
            meta = {}
            if os.path.exists(meta_path):
                with open(meta_path, "r") as f:
                    meta = json.load(f)

            files = []
            SKIP_DIRS = {".venv", "__pycache__", ".git", "node_modules", ".mypy_cache"}
            for root, dirs, filenames in os.walk(item_path):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for fn in filenames:
                    rel = os.path.relpath(os.path.join(root, fn), item_path)
                    files.append(rel)

            projects.append({"project_id": item, "files": sorted(files), "meta": meta})
        else:
            projects.append({"project_id": "__root__", "files": [item], "meta": {}})

    return {"projects": projects}


@app.get("/workspace/{project_id}/{filename:path}")
def read_workspace_file(project_id: str, filename: str):
    """Read a file from a project."""
    full_path = os.path.join(WORKSPACE_DIR, project_id, filename)
    if not os.path.exists(full_path):
        return {"error": "File not found"}
    with open(full_path, "r") as f:
        return {"content": f.read(), "path": filename, "project_id": project_id}


@app.put("/workspace/{project_id}/{filename:path}")
async def update_workspace_file(project_id: str, filename: str, body: dict):
    """Edit a file in the workspace."""
    full_path = os.path.join(WORKSPACE_DIR, project_id, filename)
    if not os.path.exists(full_path):
        return {"error": "File not found"}
    content = body.get("content", "")
    with open(full_path, "w") as f:
        f.write(content)
    return {"status": "saved", "path": filename}


@app.delete("/workspace/{project_id}")
def delete_project(project_id: str):
    """Delete an entire project."""
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)
        return {"status": "deleted", "project_id": project_id}
    return {"error": "Project not found"}


@app.delete("/workspace/{project_id}/{filename:path}")
def delete_workspace_file(project_id: str, filename: str):
    """Delete a single file from a project."""
    full_path = os.path.join(WORKSPACE_DIR, project_id, filename)
    if os.path.exists(full_path):
        os.remove(full_path)
        return {"status": "deleted", "file": filename}
    return {"error": "File not found"}


# ══════════════════════════════════════════════════════════════
# EXECUTION API
# ══════════════════════════════════════════════════════════════


@app.post("/execute/{project_id}")
async def execute_project(project_id: str):
    """Run a project's entry point."""
    run_id = str(uuid.uuid4())
    result = await execute_project_async(run_id, project_id)
    return {"run_id": run_id, **result}


@app.post("/execute/{project_id}/autofix")
async def execute_with_autofix(project_id: str):
    """Run a project with auto-fix loop on failure."""
    run_id = str(uuid.uuid4())
    result = await autofix_loop_async(run_id, project_id, max_retries=2)
    return {"run_id": run_id, **result}


# ══════════════════════════════════════════════════════════════
# MEMORY API
# ══════════════════════════════════════════════════════════════


@app.get("/memory/history")
def memory_history():
    """Get recent run history from persistent memory."""
    return {"history": get_run_history(limit=50)}


@app.get("/memory/stats")
def memory_stats():
    """Get aggregate system intelligence stats."""
    return get_stats()


# ══════════════════════════════════════════════════════════════
# SESSION API
# ══════════════════════════════════════════════════════════════


@app.post("/session")
def create_new_session():
    """Create a new conversation session."""
    sid = create_session()
    return {"session_id": sid}


@app.get("/session/{session_id}")
def get_session_endpoint(session_id: str):
    """Get session state."""
    session = get_session(session_id)
    if not session:
        return {"error": "Session not found"}
    return session


@app.get("/sessions")
def list_all_sessions():
    """List recent sessions."""
    return {"sessions": list_sessions()}


# ══════════════════════════════════════════════════════════════
# AGENT CHAT (Streaming SSE)
# ══════════════════════════════════════════════════════════════


class ChatMessage(BaseModel):
    message: str
    model: Optional[str] = None
    session_id: Optional[str] = None


@app.post("/agent/{agent_id}/chat")
async def agent_chat(agent_id: str, body: ChatMessage):
    """Direct streaming chat with any agent. Returns SSE stream."""
    chat_prompts = {
        "manager": ("manager", manager_chat_prompt()),
        "coder": ("coder", coder_chat_prompt()),
        "analyst": ("analyst", analyst_chat_prompt()),
        "critic": ("critic", critic_chat_prompt()),
        "reader": ("reader", reader_chat_prompt()),
        "qa": ("qa", qa_chat_prompt()),
    }

    if agent_id not in chat_prompts:
        return {"error": f"Unknown agent: {agent_id}"}

    model_key, system_instruction = chat_prompts[agent_id]
    model_cfg = MODELS.get(model_key, "llama3:8b")
    model = body.model or (
        model_cfg["name"] if isinstance(model_cfg, dict) else model_cfg
    )
    full_prompt = f"{system_instruction}\n\nUser: {body.message}"

    async def stream_gen():
        async for chunk in scheduled_generate(model, full_prompt):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(stream_gen(), media_type="text/event-stream")


# ══════════════════════════════════════════════════════════════
# STOP / CANCEL
# ══════════════════════════════════════════════════════════════


@app.post("/stop")
async def stop_all():
    """Cancel all active tasks."""
    cancelled = 0
    for run_id, task in list(active_tasks.items()):
        if not task.done():
            task.cancel()
            cancelled += 1
        del active_tasks[run_id]

    # Emit stop events for all active nodes so UI resets
    for node_id in ["manager", "coder", "analyst", "critic", "tool", "executor"]:
        await emitter.emit(node_id, node_id, "error", error="Execution stopped by user")

    await emitter.emit(
        "system",
        "system",
        "error",
        error=f"Execution terminated by user ({cancelled} tasks cancelled)",
    )
    return {"status": "stopped", "cancelled": cancelled}
