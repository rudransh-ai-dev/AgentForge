from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from schemas.request import Query, NodeQuery
from core.router import route_task_async
from agents.coder import run_coder_async
from agents.analyst import run_analyst_async
from agents.critic import run_critic_async
from agents.tool import run_tool_agent_async, execute_project_async, autofix_loop_async
from services.event_emitter import emitter
from core.memory import store_run, update_pattern, get_run_history, get_stats
from config import MODELS
from services.ollama_client import async_generate_stream
import time
import uuid
import json
import os
import shutil
import asyncio

WORKSPACE_DIR = os.path.join(os.path.dirname(__file__), "workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)

# Global execution tracking for stop/cancel
active_tasks = {}  # run_id -> asyncio.Task

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "AI Orchestrator Running", "version": "3.0 — Planning + Memory + Sandbox"}

# ── WebSocket ──────────────────────────────────────────────

@app.websocket("/ws/agent-stream")
async def websocket_endpoint(websocket: WebSocket):
    await emitter.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        emitter.disconnect(websocket)
    except Exception:
        emitter.disconnect(websocket)

# ── Main Orchestrated Run ──────────────────────────────────

@app.post("/run")
async def run(query: Query):
    run_id = str(uuid.uuid4())
    start_time = time.time()

    # 1. MANAGER
    await emitter.emit(run_id, "manager", "start", input_str=query.prompt)

    try:
        decision = await route_task_async(query.prompt)
        route = decision.get("selected_agent", "analyst")
        confidence = decision.get("confidence", 1.0)
    except Exception as e:
        await emitter.emit(run_id, "manager", "error", error=str(e))
        return {"error": str(e)}

    latency_ms = int((time.time() - start_time) * 1000)
    await emitter.emit(
        run_id, "manager", "complete", input_str=query.prompt,
        output_str=json.dumps(decision, indent=2),
        metadata={"latency_ms": latency_ms, "tokens": len(query.prompt), "confidence": confidence}
    )

    # 2. AGENT EXECUTION
    agent_id = route
    await emitter.emit(run_id, agent_id, "start", input_str=f"Execute task: {query.prompt}")

    agent_start = time.time()
    result = ""

    try:
        if route == "coder":
            async for chunk in run_coder_async(query.prompt):
                result += chunk
                await emitter.emit(run_id, agent_id, "update", output_str=result)
        elif route == "critic":
            async for chunk in run_critic_async(query.prompt):
                result += chunk
                await emitter.emit(run_id, agent_id, "update", output_str=result)
        else:
            async for chunk in run_analyst_async(query.prompt):
                result += chunk
                await emitter.emit(run_id, agent_id, "update", output_str=result)

        agent_latency = int((time.time() - agent_start) * 1000)
        await emitter.emit(
            run_id, agent_id, "complete", output_str=result,
            metadata={"latency_ms": agent_latency, "tokens": len(result)}
        )

        # 3. AUTO-TOOL: If coder produced code blocks or JSON format, auto-save to workspace
        project_id = decision.get("project_id")
        if agent_id == "coder" and ("```" in result or "def " in result or "---JSON---" in result):
            tool_result = await run_tool_agent_async(run_id, result, project_id=project_id)

            # 4. AUTO-EXECUTE: If files were created successfully, try running
            if tool_result.get("status") == "success" and tool_result.get("project_id"):
                pid = tool_result["project_id"]
                exec_result = await autofix_loop_async(run_id, pid, max_retries=2)
                total_latency = int((time.time() - start_time) * 1000)
                store_run(run_id, query.prompt, route, result[:3000], pid,
                         exec_result.get("status", "error"), total_latency)
                update_pattern(query.prompt, route, exec_result.get("status") == "success")
                return {"route": route, "result": result, "run_id": run_id,
                        "project_id": pid, "execution": exec_result}

        total_latency = int((time.time() - start_time) * 1000)
        store_run(run_id, query.prompt, route, result[:3000], None, "success", total_latency)
        update_pattern(query.prompt, route, True)
        return {"route": route, "result": result, "run_id": run_id}

    except Exception as e:
        await emitter.emit(run_id, agent_id, "error", error=str(e))
        return {"error": str(e)}

# ── Direct Agent Prompt ────────────────────────────────────

@app.post("/run-node")
async def run_node(query: NodeQuery):
    run_id = str(uuid.uuid4())
    agent_id = query.agent_id

    await emitter.emit(run_id, agent_id, "start", input_str=f"Direct Prompt: {query.prompt}")

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
            run_id, agent_id, "complete", output_str=result,
            metadata={"latency_ms": agent_latency, "tokens": len(result), "direct_prompt": True}
        )

        if agent_id == "coder" and ("```" in result or "def " in result):
            await run_tool_agent_async(run_id, result)

        return {"result": result, "run_id": run_id}

    except Exception as e:
        await emitter.emit(run_id, agent_id, "error", error=str(e))
        return {"error": str(e)}

# ── Workspace API ──────────────────────────────────────────

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
            SKIP_DIRS = {'.venv', '__pycache__', '.git', 'node_modules', '.mypy_cache'}
            for root, dirs, filenames in os.walk(item_path):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for fn in filenames:
                    rel = os.path.relpath(os.path.join(root, fn), item_path)
                    files.append(rel)
            
            projects.append({
                "project_id": item,
                "files": sorted(files),
                "meta": meta
            })
        else:
            # Loose file
            projects.append({
                "project_id": "__root__",
                "files": [item],
                "meta": {}
            })

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

# ── Execution API ──────────────────────────────────────────

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

# ── Memory API ─────────────────────────────────────────────

@app.get("/memory/history")
def memory_history():
    """Get recent run history from persistent memory."""
    return {"history": get_run_history(limit=50)}

@app.get("/memory/stats")
def memory_stats():
    """Get aggregate system intelligence stats."""
    return get_stats()

# ── Agent Chat (Streaming) ─────────────────────────────────

from fastapi.responses import StreamingResponse as SR
from pydantic import BaseModel

class ChatMessage(BaseModel):
    message: str

@app.post("/agent/{agent_id}/chat")
async def agent_chat(agent_id: str, body: ChatMessage):
    """Direct streaming chat with any agent. Returns SSE stream."""
    agent_map = {
        "manager": ("manager", "You are a senior AI system planner. Answer the user's question with structured reasoning."),
        "coder": ("coder", "You are an expert software engineer. Write clean, production-ready code."),
        "analyst": ("analyst", "You are a senior analyst. Provide clear explanations and reasoning."),
        "critic": ("critic", "You are an expert reviewer and critic. Evaluate critically and honestly."),
    }

    if agent_id not in agent_map:
        return {"error": f"Unknown agent: {agent_id}"}

    model_key, system_instruction = agent_map[agent_id]
    model = MODELS.get(model_key, "llama3:8b")
    full_prompt = f"{system_instruction}\n\nUser: {body.message}"

    async def stream_gen():
        async for chunk in async_generate_stream(model, full_prompt):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return SR(stream_gen(), media_type="text/event-stream")

# ── Stop / Cancel ──────────────────────────────────────────

@app.post("/stop")
async def stop_all():
    """Cancel all active tasks."""
    cancelled = 0
    for run_id, task in list(active_tasks.items()):
        if not task.done():
            task.cancel()
            cancelled += 1
        del active_tasks[run_id]
    
    # Also emit stop event to canvas
    await emitter.emit("system", "system", "error", error=f"Execution terminated by user ({cancelled} tasks cancelled)")
    return {"status": "stopped", "cancelled": cancelled}

# ── Voice Agent (100% Local) ───────────────────────────────
import urllib.parse
import subprocess
import tempfile

# Lazy-loaded whisper model
_whisper_model = None
VOICE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "voice", "voice.onnx")

def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        print("⚡ Loading Whisper tiny (CPU int8)...")
        _whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _whisper_model

@app.post("/api/voice-chat")
async def voice_chat(audio: UploadFile = File(...), prompt: str = Form("You are a helpful voice assistant. Keep responses under 2 sentences.")):
    from fastapi import HTTPException

    # 1. Save browser audio blob
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        f.write(await audio.read())
        input_path = f.name

    # 2. Transcribe with Whisper (local, CPU)
    try:
        whisper = _get_whisper()
        segments, _ = whisper.transcribe(input_path)
        user_text = " ".join(s.text for s in segments).strip()
        if not user_text:
            user_text = "[No speech detected]"
        print(f"🎤 Heard: {user_text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {e}")

    # 3. Generate AI response (connect to your Ollama brain)
    try:
        from services.ollama_client import async_generate
        agent_text = await async_generate(
            MODELS.get("analyst", "phi3:mini"),
            f"{prompt} User said: {user_text}"
        )
        if not agent_text or len(agent_text.strip()) < 2:
            agent_text = f"You said: {user_text}"

        print(f"🧠 Reply: {agent_text}")
    except Exception:
        agent_text = f"You said: {user_text}"

    # 4. Text-to-Speech with Piper (local, ~50ms)
    output_path = input_path.replace(".webm", ".wav")
    try:
        proc = subprocess.run(
            f'echo {repr(agent_text)} | python3 -m piper --model "{VOICE_MODEL_PATH}" --output_file "{output_path}"',
            shell=True, capture_output=True, text=True
        )
        if proc.returncode != 0:
            raise Exception(proc.stderr)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {e}")

    # 5. Return audio + transcript headers
    headers = {
        "X-User-Transcript": urllib.parse.quote(user_text),
        "X-Agent-Transcript": urllib.parse.quote(agent_text),
        "Access-Control-Expose-Headers": "X-User-Transcript, X-Agent-Transcript"
    }
    return FileResponse(output_path, media_type="audio/wav", headers=headers)


# ── Image Enhancement (100% Local with Pillow) ────────────

@app.post("/api/restore-image")
async def restore_image(image: UploadFile = File(...), prompt: str = Form(...)):
    """Local image enhancement using Pillow filters."""
    from fastapi import HTTPException
    from PIL import Image, ImageFilter, ImageEnhance
    import io

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_in:
        content = await image.read()
        temp_in.write(content)
        input_path = temp_in.name

    output_path = input_path.replace(".png", "_restored.png")
    prompt_lower = prompt.lower()

    try:
        img = Image.open(input_path)

        # Apply filters based on prompt keywords
        if "deblur" in prompt_lower or "sharp" in prompt_lower:
            img = img.filter(ImageFilter.SHARPEN)
            img = ImageEnhance.Sharpness(img).enhance(2.0)
            img = ImageEnhance.Contrast(img).enhance(1.2)
        elif "denoise" in prompt_lower or "noise" in prompt_lower:
            img = img.filter(ImageFilter.SMOOTH_MORE)
            img = img.filter(ImageFilter.SMOOTH)
        elif "dehaze" in prompt_lower or "haze" in prompt_lower:
            img = ImageEnhance.Contrast(img).enhance(1.5)
            img = ImageEnhance.Color(img).enhance(1.3)
        elif "low-light" in prompt_lower or "bright" in prompt_lower or "dark" in prompt_lower:
            img = ImageEnhance.Brightness(img).enhance(1.6)
            img = ImageEnhance.Contrast(img).enhance(1.3)
            img = ImageEnhance.Color(img).enhance(1.1)
        else:
            # General enhance
            img = img.filter(ImageFilter.SHARPEN)
            img = ImageEnhance.Contrast(img).enhance(1.2)
            img = ImageEnhance.Color(img).enhance(1.1)

        img.save(output_path, quality=95)
        print(f"✅ Image processed: {prompt}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image processing error: {e}")

    if not os.path.exists(output_path):
        raise HTTPException(status_code=500, detail="Processing finished but no output file was generated.")

    return FileResponse(output_path, media_type="image/png")


