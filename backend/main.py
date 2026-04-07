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
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import time
import uuid
import json
import os
import shutil
import asyncio
import zipfile
import io

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
from core.memory_manager import get_db_health, cleanup_old_data
from core.chat_memory import (
    create_session as create_chat_session,
    get_session as get_chat_session,
    list_sessions as list_chat_sessions,
    get_messages,
    add_message,
    delete_session as delete_chat_session,
    clear_all_sessions,
    get_summary,
    set_summary,
)
from core.agent_memory import (
    get_knowledge, delete_knowledge, get_patterns, get_fixes,
    delete_fixes, reset_agent_memory, store_fix, store_knowledge,
    update_pattern as update_agent_pattern,
)
from core.canvas_memory import (
    get_run, get_run_steps, get_recent_runs, get_active_run,
    delete_run, clear_all_runs,
)
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
    """Seed DB schemas and sync model registry from Ollama on server boot."""
    from core.memory_manager import init_all
    from services.mcp_client import mcp_manager
    init_all()
    await sync_model_registry()
    await mcp_manager.initialize_all()

@app.on_event("shutdown")
async def shutdown_event():
    from services.mcp_client import mcp_manager
    await mcp_manager.close()


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


class ChatMessage(BaseModel):
    message: str
    model: Optional[str] = None
    session_id: Optional[str] = None


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


@app.get("/workspace/export/{project_id}")
def export_project(project_id: str):
    """Export a project as a zip file."""
    project_dir = os.path.join(WORKSPACE_DIR, project_id)
    if not os.path.exists(project_dir):
        return {"error": "Project not found"}

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        SKIP_DIRS = {".venv", "__pycache__", ".git", "node_modules", ".mypy_cache"}
        for root, dirs, filenames in os.walk(project_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fn in filenames:
                full_path = os.path.join(root, fn)
                arcname = os.path.relpath(full_path, project_dir)
                zf.write(full_path, arcname)

    zip_buffer.seek(0)
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={project_id}.zip"},
    )


@app.get("/workspace/export-all")
def export_all_projects():
    """Export all projects as a single zip file."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        SKIP_DIRS = {".venv", "__pycache__", ".git", "node_modules", ".mypy_cache"}
        for item in sorted(os.listdir(WORKSPACE_DIR)):
            item_path = os.path.join(WORKSPACE_DIR, item)
            if item.startswith(".") or not os.path.isdir(item_path):
                continue
            for root, dirs, filenames in os.walk(item_path):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for fn in filenames:
                    full_path = os.path.join(root, fn)
                    arcname = os.path.relpath(full_path, WORKSPACE_DIR)
                    zf.write(full_path, arcname)

    zip_buffer.seek(0)
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=workspace.zip"},
    )


@app.post("/workspace/import")
async def import_project(file: UploadFile = File(...)):
    """Import a project from a zip file."""
    if not file.filename.endswith(".zip"):
        return {"error": "Only zip files are supported"}

    try:
        contents = await file.read()
        zip_buffer = io.BytesIO(contents)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            project_name = os.path.splitext(file.filename)[0]
            project_dir = os.path.join(WORKSPACE_DIR, project_name)
            os.makedirs(project_dir, exist_ok=True)
            zf.extractall(project_dir)
        return {"status": "imported", "project_id": project_name}
    except Exception as e:
        return {"error": f"Failed to import: {str(e)}"}


@app.get("/executors")
def list_executors():
    """List supported execution languages."""
    from services.executor import RUNNERS
    runners = []
    for runner in RUNNERS:
        runners.append({
            "language": runner.language,
            "available": os.system(f"which {runner.language} > /dev/null 2>&1") == 0 if runner.language != "python" else True,
        })
    return {"runners": runners}


# ══════════════════════════════════════════════════════════════
# METRICS API
# ══════════════════════════════════════════════════════════════


@app.get("/metrics/overview")
def metrics_overview():
    """Summary stats."""
    from services.metrics import get_overview
    return get_overview()


@app.get("/metrics/latency")
def metrics_latency():
    """Latency timeseries data."""
    from services.metrics import get_latency_timeseries
    return get_latency_timeseries()


@app.get("/metrics/vram")
def metrics_vram():
    """VRAM usage timeseries."""
    from services.metrics import get_vram_timeseries
    return get_vram_timeseries()


@app.get("/metrics/models")
def metrics_models():
    """Per-model performance breakdown."""
    from services.metrics import get_model_breakdown
    return get_model_breakdown()


@app.get("/metrics/tasks")
def metrics_tasks():
    """Task type distribution."""
    from services.metrics import get_task_distribution
    return get_task_distribution()


@app.get("/metrics/recent")
def metrics_recent():
    """Recent runs."""
    from services.metrics import get_recent_runs
    return get_recent_runs()


# ══════════════════════════════════════════════════════════════
# CUSTOM AGENTS API
# ══════════════════════════════════════════════════════════════


CUSTOM_AGENTS_FILE = os.path.join(os.path.dirname(__file__), "custom_agents.json")


def load_custom_agents():
    if os.path.exists(CUSTOM_AGENTS_FILE):
        with open(CUSTOM_AGENTS_FILE, "r") as f:
            return json.load(f)
    return []


def save_custom_agents(agents):
    with open(CUSTOM_AGENTS_FILE, "w") as f:
        json.dump(agents, f, indent=2)


@app.get("/custom-agents")
def list_custom_agents():
    agents = load_custom_agents()
    return {"agents": agents}


@app.post("/custom-agents")
def create_custom_agent(body: dict):
    agents = load_custom_agents()
    agent_id = body.get("name", "agent").lower().replace(" ", "_")
    agent = {
        "id": agent_id,
        "name": body.get("name", "Custom Agent"),
        "model": body.get("model", "qwen2.5:14b"),
        "system_prompt": body.get("system_prompt", ""),
        "color": body.get("color", "#58a6ff"),
        "icon": body.get("icon", "Cpu"),
        "created_at": time.time(),
    }
    agents.append(agent)
    save_custom_agents(agents)
    return {"status": "created", "agent": agent}


@app.put("/custom-agents/{agent_id}")
def update_custom_agent(agent_id: str, body: dict):
    agents = load_custom_agents()
    for i, agent in enumerate(agents):
        if agent["id"] == agent_id:
            agents[i].update({
                "name": body.get("name", agent["name"]),
                "model": body.get("model", agent["model"]),
                "system_prompt": body.get("system_prompt", agent["system_prompt"]),
                "color": body.get("color", agent["color"]),
                "icon": body.get("icon", agent["icon"]),
            })
            save_custom_agents(agents)
            return {"status": "updated", "agent": agents[i]}
    return {"error": "Agent not found"}


@app.delete("/custom-agents/{agent_id}")
def delete_custom_agent(agent_id: str):
    agents = load_custom_agents()
    agents = [a for a in agents if a["id"] != agent_id]
    save_custom_agents(agents)
    return {"status": "deleted"}


# ══════════════════════════════════════════════════════════════
# DIFF API
# ══════════════════════════════════════════════════════════════


@app.get("/workspace/{project_id}/diffs")
def list_project_diffs(project_id: str):
    """List all diffs for a project."""
    from services.diff import get_diffs_for_project
    return {"diffs": get_diffs_for_project(project_id)}


@app.get("/workspace/{project_id}/diffs/{diff_id}")
def get_project_diff(project_id: str, diff_id: str):
    """Get a specific diff."""
    from services.diff import get_diff
    diff = get_diff(project_id, diff_id)
    if not diff:
        return {"error": "Diff not found"}
    return diff


# ══════════════════════════════════════════════════════════════
# PROMPT VERSIONING API
# ══════════════════════════════════════════════════════════════


@app.get("/prompts/{agent_id}/versions")
def get_prompt_versions(agent_id: str, prompt_type: str = "chat"):
    from core.prompt_versions import get_versions
    return {"versions": get_versions(agent_id, prompt_type)}


@app.get("/prompts/{agent_id}/versions/{version}")
def get_prompt_version(agent_id: str, version: int, prompt_type: str = "chat"):
    from core.prompt_versions import get_version
    v = get_version(agent_id, version, prompt_type)
    if not v:
        return {"error": "Version not found"}
    return v


@app.post("/prompts/{agent_id}/versions")
def save_prompt_version(agent_id: str, body: dict):
    from core.prompt_versions import save_version
    note = body.get("note", "")
    prompt_text = body.get("prompt_text", "")
    prompt_type = body.get("prompt_type", "chat")
    if not prompt_text:
        return {"error": "prompt_text is required"}
    new_version = save_version(agent_id, prompt_text, prompt_type, note)
    return {"status": "saved", "version": new_version}


@app.get("/prompts/{agent_id}/diff")
def get_prompt_diff(agent_id: str, from_version: int, to_version: int, prompt_type: str = "chat"):
    from core.prompt_versions import get_diff
    d = get_diff(agent_id, from_version, to_version, prompt_type)
    if not d:
        return {"error": "Version not found"}
    return d


@app.put("/prompts/{agent_id}/rollback/{version}")
def rollback_prompt(agent_id: str, version: int, prompt_type: str = "chat"):
    from core.prompt_versions import rollback_to
    new_version = rollback_to(agent_id, version, prompt_type)
    if new_version is None:
        return {"error": "Version not found"}
    return {"status": "rolled_back", "new_version": new_version}


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
    """Get aggregate system intelligence stats from all 4 memory domains."""
    base = get_stats()
    health = get_db_health()
    active = get_active_run()
    return {
        **base,
        "db_size_mb": health.get("total_size_mb", 0),
        "table_counts": health.get("tables", {}),
        "active_run": active["run_id"] if active else None,
    }


@app.get("/memory/health")
def memory_health():
    """Get database health metrics."""
    return get_db_health()


@app.post("/memory/cleanup")
def memory_cleanup(chat_ttl: int = 7, metrics_ttl: int = 30, canvas_ttl: int = 30):
    """Run TTL cleanup job."""
    deleted = cleanup_old_data(chat_ttl, metrics_ttl, canvas_ttl)
    return {"status": "cleaned", "deleted": deleted}


@app.post("/memory/backup")
def memory_backup():
    """Export database as downloadable file."""
    db_path = os.path.join(os.path.dirname(__file__), "memory.db")
    if not os.path.exists(db_path):
        return {"error": "Database not found"}
    return FileResponse(db_path, filename="memory_backup.db", media_type="application/octet-stream")


# ══════════════════════════════════════════════════════════════
# CHAT MEMORY API
# ══════════════════════════════════════════════════════════════


class CreateChatSession(BaseModel):
    mode: Optional[str] = "persona"
    selected_agent: Optional[str] = ""
    selected_model: Optional[str] = ""
    persona_key: Optional[str] = ""
    direct_model: Optional[str] = ""


@app.post("/chat/sessions")
def new_chat_session(body: CreateChatSession):
    sid = create_chat_session(
        mode=body.mode,
        selected_agent=body.selected_agent,
        selected_model=body.selected_model,
        persona_key=body.persona_key,
        direct_model=body.direct_model,
    )
    return {"session_id": sid}


@app.get("/chat/sessions")
def list_chat_sessions_endpoint(limit: int = 20):
    return {"sessions": list_chat_sessions(limit)}


# ══════════════════════════════════════════════════════════════
# MCP API
# ══════════════════════════════════════════════════════════════


@app.get("/mcp/tools")
async def list_mcp_tools():
    """List all tools available across configured MCP servers."""
    from services.mcp_client import mcp_manager
    tools = await mcp_manager.get_all_tools()
    return {"tools": tools}


@app.post("/mcp/call/{server_name}/{tool_name}")
async def call_mcp_tool(server_name: str, tool_name: str, body: dict):
    """Call a specific MCP tool."""
    from services.mcp_client import mcp_manager
    try:
        result = await mcp_manager.call_tool(server_name, tool_name, body)
        # Assuming the result is serializable, otherwise just return string
        return {"status": "success", "result": str(result)}
    except Exception as e:
        return {"error": str(e)}

@app.get("/chat/sessions/{session_id}")
def get_chat_session_endpoint(session_id: str):
    session = get_chat_session(session_id)
    if not session:
        return {"error": "Session not found"}
    messages = get_messages(session_id, limit=200)
    summary = get_summary(session_id)
    return {**session, "messages": messages, "summary": summary}


@app.delete("/chat/sessions/{session_id}")
def delete_chat_session_endpoint(session_id: str):
    delete_chat_session(session_id)
    return {"status": "deleted"}


# ══════════════════════════════════════════════════════════════
# AGENT MEMORY API
# ══════════════════════════════════════════════════════════════


@app.get("/agents/{agent_id}/knowledge")
def get_agent_knowledge(agent_id: str, limit: int = 20):
    return {"knowledge": get_knowledge(agent_id, limit)}


@app.delete("/agents/{agent_id}/knowledge")
def delete_agent_knowledge(agent_id: str):
    delete_knowledge(agent_id)
    return {"status": "deleted"}


@app.get("/agents/{agent_id}/patterns")
def get_agent_patterns(agent_id: str):
    return {"patterns": get_patterns(agent_id)}


@app.get("/agents/{agent_id}/fixes")
def get_agent_fixes(agent_id: str, limit: int = 20):
    return {"fixes": get_fixes(agent_id, limit)}


@app.delete("/agents/{agent_id}/memory")
def reset_agent_memory_endpoint(agent_id: str):
    reset_agent_memory(agent_id)
    return {"status": "reset"}


# ══════════════════════════════════════════════════════════════
# CANVAS MEMORY API
# ══════════════════════════════════════════════════════════════


@app.get("/canvas/runs")
def list_canvas_runs(limit: int = 20):
    return {"runs": get_recent_runs(limit)}


@app.get("/canvas/runs/{run_id}")
def get_canvas_run(run_id: str):
    run = get_run(run_id)
    if not run:
        return {"error": "Run not found"}
    steps = get_run_steps(run_id)
    return {**run, "steps": steps}


@app.get("/canvas/runs/{run_id}/steps")
def get_canvas_run_steps(run_id: str):
    return {"steps": get_run_steps(run_id)}


@app.delete("/canvas/runs/{run_id}")
def delete_canvas_run(run_id: str):
    delete_run(run_id)
    return {"status": "deleted"}


@app.delete("/canvas/runs")
def clear_canvas_runs():
    clear_all_runs()
    return {"status": "cleared"}


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
        full_response = ""
        async for chunk in scheduled_generate(model, full_prompt):
            full_response += chunk
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

        if body.session_id:
            add_message(body.session_id, role="user", content=body.message, agent_id=agent_id, model=model)
            add_message(body.session_id, role="assistant", content=full_response, agent_id=agent_id, model=model)

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
        await emitter.emit("system", node_id, "error", error="Execution stopped by user")

    await emitter.emit(
        "system",
        "system",
        "error",
        error=f"Execution terminated by user ({cancelled} tasks cancelled)",
    )
    return {"status": "stopped", "cancelled": cancelled}


# ══════════════════════════════════════════════════════════════
# CHAT SERVER — Mounted as sub-app (Persona / AI Friends)
# ══════════════════════════════════════════════════════════════

from chat_server import app as chat_app

app.mount("/persona", chat_app)
