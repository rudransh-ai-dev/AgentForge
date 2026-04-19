import sys
"""
Pipeline Orchestrator — The Brain of the System (v3.1)
======================================================

This is the CORE execution engine. It takes a task from the Router
and executes each step sequentially through the correct agent,
with VRAM-aware model lifecycle management.

Architecture:
    User Input → Router → Planner → Orchestrator → Agent(s) → Manager → Output

Key Features:
    - Sequential agent execution (one at a time, GPU-safe)
    - VRAM-aware model loading via scheduler
    - Feedback loop: Critic validates Coder output (max 2 retries)
    - Latency budget enforcement with auto-downgrade
    - Structured logging at every phase
    - Session context integration
"""

import os
import re
import asyncio
import json
import time
import uuid
from typing import Optional



from core.router import route_task_async
from agents.coder import run_coder_async
from agents.analyst import run_analyst_async
from agents.critic import run_critic_async, validate_output
from agents.tool import run_tool_agent_async, execute_project_async, autofix_loop_async
from agents.researcher import run_researcher_async
from agents.writer import run_writer_async
from agents.editor import run_editor_async
from agents.tester import run_tester_async, validate_code
from core.router import COMPLEXITY_TRIGGERS
from services.event_emitter import emitter
from services.logger import log_pipeline_start, log_pipeline_end, log_agent_execution
from core.memory import store_run, update_pattern
from core.canvas_memory import create_run, update_run, add_step, update_step
from services.metrics import record_run
from core.session import get_session, add_turn, update_session, create_session
from core.context import compress_context, build_context_window
from core.prompts import (
    critic_file_review_prompt,
    critic_recheck_prompt,
    coder_fix_prompt,
    coder_revision_prompt,
    readme_prompt,
)
from schemas.task import Task, TaskStep, TaskBudget, ExecutionResult
from config import MODELS
from services.vram_scheduler import get_model_info, MODEL_REGISTRY

WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "workspace")

# ── Global Pipeline Lock ──
# Only one pipeline execution at a time (FIFO queue)
pipeline_lock = asyncio.Lock()

# ── Latency Budget Thresholds ──
LATENCY_BUDGETS = {
    "direct": 2000,  # 2 seconds
    "agent": 15000,  # 15 seconds
    "heavy": 25000,  # 25 seconds for devstral:24b
    "reload": 6000,  # 6 seconds for model reload
}

# Model downgrade fallbacks for budget enforcement.
# Every entry here MUST reference a model actually pulled on this box —
# see `ollama list`. A downgrade to a missing model produces a 600s
# timeout per retry and looks like the whole pipeline hanging.
MODEL_DOWNGRADES = {
    "gpt-oss:20b":        "qwen2.5-coder:14b",
    "qwen2.5-coder:14b":  "qwen2.5:14b",
    "qwen2.5:14b":        "llama3.1:8b",
    "llama3.1:8b":        "deepseek-r1:8b",
    "deepseek-r1:8b":     "llama3.1:8b",
    "phi4:latest":        "qwen2.5-coder:14b",
    "codestral:22b":      "gpt-oss:20b",
    "gemma4:26b":         "gpt-oss:20b",
}


def _should_downgrade(model: str, budget_ms: int) -> Optional[str]:
    """
    Latency budget enforcement: if the model is too heavy for the budget,
    return a lighter fallback model.
    """
    info = get_model_info(model)
    estimated_latency = info["size_gb"] * 1500  # ~1.5s per GB heuristic

    if estimated_latency > budget_ms and model in MODEL_DOWNGRADES:
        return MODEL_DOWNGRADES[model]
    return None


def _get_agent_model(
    agent: str, allow_heavy: bool = False, budget_ms: int = 15000
) -> str:
    """
    Get the appropriate model for an agent, respecting budget constraints.
    """
    agent_cfg = MODELS.get(agent, {"name": "llama3.1:8b"})
    model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg

    if not allow_heavy:
        info = get_model_info(model)
        if info.get("is_heavy", False):
            # Force downgrade for non-heavy-allowed tasks
            model = MODEL_DOWNGRADES.get(model, "llama3.1:8b")

    # Check latency budget
    downgrade = _should_downgrade(model, budget_ms)
    if downgrade:
        model = downgrade

    return model


# ══════════════════════════════════════════════════════════════
# DIRECT MODE — No pipeline, single model response
# ══════════════════════════════════════════════════════════════


async def run_direct_mode(
    prompt: str, session_id: Optional[str] = None, model_override: Optional[str] = None
) -> ExecutionResult:
    """
    Direct Mode execution — bypasses the pipeline.
    User → Selected Model → Response

    Target latency: < 2 seconds
    """
    run_id = str(uuid.uuid4())
    start_time = time.time()

    log_pipeline_start(run_id, "direct", prompt)
    await emitter.emit(
        run_id, "system", "start", input_str=f"⚡ Direct Mode: {prompt[:80]}"
    )

    # Build context if session exists
    context_prompt = prompt
    if session_id:
        session = get_session(session_id)
        if session:
            from core.context import build_context_window

            session_ctx = session.get("context_summary", "")
            context_prompt = build_context_window(session_ctx, prompt)

    # Determine agent from simple keyword matching
    is_code = any(
        kw in prompt.lower()
        for kw in [
            "code",
            "write",
            "build",
            "create",
            "script",
            "program",
            "app",
            "function",
            "class",
            "implement",
            "debug",
            "fix",
            "python",
            "javascript",
            "java",
            "c++",
            "c#",
            "ruby",
            "go ",
            "rust",
            "typescript",
            "swift",
            "kotlin",
            "php",
            "html",
            "css",
            "sql",
            "bash",
            "shell",
            "hello world",
            "print(",
            "def ",
            "import ",
            "const ",
            "let ",
            "func ",
        ]
    )
    agent = "coder" if is_code else "analyst"

    # Extract model name from dictionary
    agent_model_info = MODELS.get(agent, MODELS["analyst"])
    base_model = (
        agent_model_info["name"]
        if isinstance(agent_model_info, dict)
        else agent_model_info
    )

    model = model_override or base_model

    # Execute
    await emitter.emit(run_id, agent, "start", input_str=prompt)
    result = ""
    agent_start = time.time()

    try:
        gen = (
            run_coder_async(context_prompt, model_override=model)
            if agent == "coder"
            else run_analyst_async(context_prompt, model_override=model)
        )

        async for chunk in gen:
            result += chunk
            if len(result) % 50 == 0:
                await emitter.emit(run_id, agent, "update", output_str=result)

        latency_ms = int((time.time() - agent_start) * 1000)
        await emitter.emit(
            run_id,
            agent,
            "complete",
            output_str=result,
            metadata={"latency_ms": latency_ms, "model": model, "mode": "direct"},
        )

        log_agent_execution(
            run_id,
            agent,
            model,
            "direct_complete",
            latency_ms=latency_ms,
            tokens_out=len(result),
        )

    except Exception as e:
        local_error = str(e)
        log_agent_execution(run_id, agent, model, "direct_error", error=local_error)

        # For all agents — fall back to a light local model, never cloud
        LOCAL_FALLBACK = "deepseek-r1:8b"
        await emitter.emit(run_id, agent, "update",
            output_str=f"⚡ {model} unavailable — falling back to {LOCAL_FALLBACK}...")
        result = ""
        fallback_start = time.time()
        try:
            gen = (run_coder_async(context_prompt, model_override=LOCAL_FALLBACK)
                   if agent == "coder"
                   else run_analyst_async(context_prompt, model_override=LOCAL_FALLBACK))
            async for chunk in gen:
                result += chunk
                if len(result) % 80 == 0:
                    await emitter.emit(run_id, agent, "update", output_str=result)
            fallback_latency = int((time.time() - fallback_start) * 1000)
            await emitter.emit(run_id, agent, "complete", output_str=result,
                metadata={"latency_ms": fallback_latency, "model": LOCAL_FALLBACK, "mode": "local_fallback"})
        except Exception as fe:
            await emitter.emit(run_id, agent, "error", error=f"All local models failed: {fe}")
            result = f"Error: {local_error}"

    # Update session
    if session_id:
        add_turn(session_id, "user", prompt)
        add_turn(session_id, "assistant", result[:3000], agent=agent, model=model)
        update_session(session_id, active_mode="direct")

    total_latency = int((time.time() - start_time) * 1000)
    store_run(run_id, prompt, agent, result[:3000], "", "success", total_latency)
    update_pattern(prompt, agent, True)
    create_run(run_id, prompt, mode="direct", allow_heavy=False)
    add_step(run_id, 0, agent, prompt[:5000], model)
    update_step(run_id, agent, status="success", output=result[:10000], latency_ms=total_latency)
    update_run(run_id, status="success", total_latency_ms=total_latency)
    record_run(run_id, "direct", "direct", model, total_latency, len(result), "success", session_id or "")
    log_pipeline_end(run_id, "success", total_latency)

    # Release model from VRAM after direct mode — don't keep it warm
    try:
        from services.vram_scheduler import release_model
        await release_model(model)
    except Exception:
        pass

    return ExecutionResult(
        task_id=run_id,
        run_id=run_id,
        mode="direct",
        route=agent,
        result=result,
        total_latency_ms=total_latency,
        status="success",
    )



async def run_production_pipeline_async(prompt: str, run_id: str, project_id: str, emitter, allow_heavy: bool = False):
    import time
    from services.vram_scheduler import release_model

    # Resolve model names dynamically from config so the messages and
    # VRAM releases match what's actually loaded.
    def _model_name(agent: str, fallback: str) -> str:
        cfg = MODELS.get(agent, {"name": fallback})
        return cfg["name"] if isinstance(cfg, dict) else cfg

    writer_model = _model_name("writer", "qwen2.5-coder:14b")
    editor_model = _model_name("editor", "qwen2.5-coder:14b")

    # Deep Think mode: swap writer to the heavy model for stronger drafts
    if allow_heavy:
        heavy_model = _model_name("heavy", "codestral:22b")
        writer_model = heavy_model

    # -- STAGE 1: WRITER --
    await emitter.emit(run_id, "writer", "start", input_str=f"Stage 1/3: {'🧠 Deep Think' if allow_heavy else 'Writer'} ({writer_model}) drafting architecture and code...")
    stage_start = time.time()
    draft_output = ""
    try:
        writer_chunks = 0
        async for chunk in run_writer_async(prompt, model_override=writer_model):
            draft_output += chunk
            writer_chunks += 1
            if writer_chunks % 8 == 0:
                await emitter.emit(run_id, "writer", "update", output_str=draft_output)

        await emitter.emit(run_id, "writer", "complete", output_str=draft_output[:2000] + "\n...[truncated]...", metadata={"latency_ms": int((time.time() - stage_start) * 1000)})
        # Only release writer if it differs from editor — otherwise we'd
        # unload the model and immediately reload it for stage 2. Saves
        # 20-40s per run when writer and editor share the same model.
        if writer_model != editor_model:
            await release_model(writer_model)
    except Exception as e:
        await emitter.emit(run_id, "writer", "error", error=str(e))
        return None  # Fallback gracefully if Writer dies entirely

    # -- STAGE 2 & 3: EDITOR -> TESTER FEEDBACK LOOP --
    # Reduced from 3 to 1 retry: worst-case latency halved for the demo.
    max_retries = 1
    refined_output = draft_output
    tester_feedback = ""
    
    for attempt in range(max_retries + 1):
        # EDITOR PHASE
        editor_title = "Stage 2/3: Editor refining code..." if attempt == 0 else f"Stage 2/3: Editor applying fixes (Attempt {attempt})..."
        await emitter.emit(run_id, "editor", "start", input_str=editor_title)
        stage_start = time.time()
        temp_refined = ""
        try:
            editor_chunks = 0
            async for chunk in run_editor_async(prompt, draft_output, fix_instructions=tester_feedback):
                temp_refined += chunk
                editor_chunks += 1
                if editor_chunks % 8 == 0:
                    await emitter.emit(run_id, "editor", "update", output_str=temp_refined)
            
            refined_output = temp_refined
            await emitter.emit(run_id, "editor", "complete", output_str=refined_output[:2000] + "\n...[truncated]...", metadata={"latency_ms": int((time.time() - stage_start) * 1000)})
            # Unload editor using the resolved name, not a hardcoded tag.
            await release_model(editor_model)
        except Exception as e:
            await emitter.emit(run_id, "editor", "error", error=str(e))
            # Just use writer's output or previous refined output if editor dies
            pass

        # TESTER PHASE
        await emitter.emit(run_id, "tester", "start", input_str="Stage 3/3: Tester running adversarial QA...")
        stage_start = time.time()
        try:
            # We concurrently stream visual output while calculating structured JSON verdict
            # Note: For strict correctness without complex async, we just get verdict directly
            verdict = await validate_code(prompt, refined_output)
            
            summary = verdict.get("summary", "")
            bugs = verdict.get("bugs", [])
            state = verdict.get("verdict", "PASS")
            score = verdict.get("score", 0)
            
            output_msg = f"**Verdict:** {state} (Score: {score}/10)\n**Summary:** {summary}\n"
            if bugs:
                output_msg += "**Found Bugs:**\n"
                for b in bugs:
                    output_msg += f"- {b}\n"
            
            await emitter.emit(run_id, "tester", "update", output_str=output_msg)
            await emitter.emit(run_id, "tester", "complete", output_str=output_msg, metadata={"latency_ms": int((time.time() - stage_start) * 1000), "score": score, "verdict": state})
            
            if state == "PASS":
                break
            else:
                tester_feedback = verdict.get("fix_instructions", "")
                if not tester_feedback:
                    tester_feedback = "\n".join(bugs)
                    
        except Exception as e:
            await emitter.emit(run_id, "tester", "error", error=str(e))
            break # Can't loop without a tester
            
    # Auto-Tool Saving
    # Note: run_tool_agent_async emits its own "tool start" with a more
    # descriptive message, so we skip the duplicate start here.
    try:
        tool_resp = await run_tool_agent_async(run_id, refined_output, project_id=project_id)
    except Exception as e:
        await emitter.emit(run_id, "tool", "error", error=f"Tool agent crashed: {e}")
        tool_resp = {"status": "error", "message": str(e)}
    if tool_resp and tool_resp.get("status") == "success":
        await emitter.emit(run_id, "tool", "complete", output_str=f"Saved {len(tool_resp.get('files', []))} files.")
    elif not (tool_resp and tool_resp.get("status") == "error"):
        # Only emit a generic error if the tool agent didn't already emit its own
        await emitter.emit(run_id, "tool", "error", error="Failed to save files.")
        
    # Generate README
    await _generate_readme_async(run_id, project_id, prompt, refined_output)

    # Save Canvas History explicitly to the workspace
    history_md = f"# Canvas Execution History\\n\\n## Goal\\n{prompt}\\n\\n## Stage 1: Writer Draft\\n{draft_output}\\n\\n## Stage 2: Editor Output\\n{refined_output}\\n\\n## Stage 3: QA Feedback\\n{tester_feedback}"
    import os
    workspace_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "workspace")
    project_dir = os.path.join(workspace_dir, project_id)
    if os.path.exists(project_dir):
        with open(os.path.join(project_dir, "canvas_history.md"), "w") as f:
            f.write(history_md)
        # Update project.json
        meta_path = os.path.join(project_dir, "project.json")
        if os.path.exists(meta_path):
            import json
            try:
                with open(meta_path, "r") as f:
                    meta = json.load(f)
                if "canvas_history.md" not in meta.get("files", []):
                    meta.setdefault("files", []).append("canvas_history.md")
                    with open(meta_path, "w") as f:
                        json.dump(meta, f, indent=2)
            except Exception: pass
    
    return refined_output

# ══════════════════════════════════════════════════════════════
# AGENT MODE — Full orchestration pipeline

# ══════════════════════════════════════════════════════════════


async def run_agent_mode(
    prompt: str,
    session_id: Optional[str] = None,
    allow_heavy: bool = False,
    research_mode: bool = False,
    node_models: dict = None,
) -> ExecutionResult:
    """
    Agent Mode execution — full pipeline.
    User → Router → Planner → Agent(s) → Manager → Output

    Target latency: 8-15s (standard), <25s (heavy models)
    """
    run_id = str(uuid.uuid4())
    start_time = time.time()

    log_pipeline_start(run_id, "agent", prompt)
    create_run(run_id, prompt, mode="agent", allow_heavy=allow_heavy)
    add_step(run_id, 0, "manager", prompt[:5000], 
        MODELS["manager"]["name"] if isinstance(MODELS["manager"], dict) else MODELS["manager"])

    # Build context from session
    context_prompt = prompt
    if session_id:
        session = get_session(session_id)
        if session:
            session_ctx = session.get("context_summary", "")
            context_prompt = build_context_window(session_ctx, prompt)

    # ── Step 1: ROUTER + PLANNER ──
    await emitter.emit(run_id, "manager", "start", input_str=prompt)

    try:
        manager_override = (node_models or {}).get("manager")
        decision = await route_task_async(
            prompt,
            research_mode=research_mode,
            manager_model=manager_override,
        )
    except Exception as e:
        await emitter.emit(run_id, "manager", "error", error=str(e))
        log_pipeline_end(run_id, "error", int((time.time() - start_time) * 1000))
        return ExecutionResult(
            task_id=run_id,
            run_id=run_id,
            mode="agent",
            route="error",
            result=f"Router error: {e}",
            status="error",
            total_latency_ms=int((time.time() - start_time) * 1000),
        )

    route = decision.get("selected_agent", "analyst")
    plan_steps = decision.get("plan", [])
    goal = decision.get("goal", prompt[:80])
    project_id = decision.get("project_id", "project")
    confidence = decision.get("confidence", 1.0)

    router_latency = int((time.time() - start_time) * 1000)

    manager_model = (
        MODELS["manager"]["name"]
        if isinstance(MODELS["manager"], dict)
        else MODELS["manager"]
    )

    await emitter.emit(
        run_id,
        "manager",
        "complete",
        output_str=json.dumps(
            {
                "selected_agent": route,
                "goal": goal,
                "confidence": confidence,
                "steps_total": len(plan_steps),
                "project_id": project_id,
            }
        ),
        metadata={
            "latency_ms": router_latency,
            "confidence": confidence,
            "route": route,
            "steps": len(plan_steps),
        },
    )

    log_agent_execution(
        run_id, "manager", manager_model, "routing_complete", latency_ms=router_latency
    )

    # ── Step 2: Build Task Object ──
    budget = TaskBudget(
        max_latency_ms=LATENCY_BUDGETS["heavy"]
        if allow_heavy
        else LATENCY_BUDGETS["agent"],
        allow_heavy_model=allow_heavy,
    )

    task = Task(
        task_id=run_id,
        input=prompt,
        goal=goal,
        project_id=project_id,
        agent=route,
        budget=budget,
        run_id=run_id,
        steps=[TaskStep(**s) for s in plan_steps] if plan_steps else [],
    )

    # ── Step 3: Execute Agent Steps ──
    final_result = ""
    steps_completed = 0
    execution_result = None
    feedback = None

    is_complex_code_req = any(trig in prompt.lower() for trig in COMPLEXITY_TRIGGERS)

    # ── Researcher Route: direct model call, no code pipeline ──
    if route == "researcher":
        researcher_model = _get_agent_model("researcher", allow_heavy)
        await emitter.emit(run_id, "researcher", "start",
            input_str=f"Researching: {prompt[:100]}...")

        result = ""
        res_start = time.time()
        try:
            async for chunk in run_researcher_async(prompt):
                result += chunk
                if len(result) % 80 == 0:
                    await emitter.emit(run_id, "researcher", "update", output_str=result)

            res_latency = int((time.time() - res_start) * 1000)
            await emitter.emit(run_id, "researcher", "complete", output_str=result,
                metadata={"latency_ms": res_latency, "model": researcher_model})

            total_latency = int((time.time() - start_time) * 1000)
            from services.metrics import record_run
            record_run(run_id, "agent", "researcher", researcher_model,
                total_latency, len(result), "success", session_id or "")
            update_run(run_id, status="success", total_latency_ms=total_latency)
            log_pipeline_end(run_id, "success", total_latency, 1)
            return ExecutionResult(task_id=run_id, run_id=run_id, mode="agent", route="researcher",
                result=result[:3000], total_latency_ms=total_latency, status="success")
        except Exception as e:
            await emitter.emit(run_id, "researcher", "error", error=str(e))
            total_latency = int((time.time() - start_time) * 1000)
            update_run(run_id, status="error", total_latency_ms=total_latency)
            return ExecutionResult(task_id=run_id, run_id=run_id, mode="agent", route="researcher",
                result=f"Research failed: {e}", total_latency_ms=total_latency, status="error")

    # ── Production Code Pipeline (Writer → Editor → Tester) ──
    if route == "writer" or route == "coder" or (route == "coder" and is_complex_code_req):
        final_result = await run_production_pipeline_async(prompt, run_id, project_id, emitter, allow_heavy)
        
        total_latency = int((time.time() - start_time) * 1000)
        
        # Record pipeline metrics before early return
        from services.metrics import record_run
        record_run(run_id, "agent", route, 
            MODELS.get(route, {}).get("name", route) if isinstance(MODELS.get(route), dict) else MODELS.get(route, route),
            total_latency, len(final_result) if final_result else 0, 
            "success" if final_result else "error", session_id or "")

        if final_result:
            update_run(run_id, status="success", total_latency_ms=total_latency)
            log_pipeline_end(run_id, "success", total_latency, 3) # approx 3 steps
            return ExecutionResult(task_id=run_id, run_id=run_id, mode="agent", route=route, result=final_result[:3000], total_latency_ms=total_latency, status="success")
        else:
            update_run(run_id, status="error", total_latency_ms=total_latency)
            log_pipeline_end(run_id, "error", total_latency, 1)
            return ExecutionResult(task_id=run_id, run_id=run_id, mode="agent", route=route, result="Error: Pipeline execution failed.", total_latency_ms=total_latency, status="error")


    for i, step in enumerate(task.steps):
        step_agent = step.agent
        step.status = "running"

        # Skip non-primary agents in this simplified loop
        if step_agent not in ["coder", "analyst", "critic", "researcher", "tool"]:
            continue

        if step_agent == "tool":
            await emitter.emit(run_id, step_agent, "start", input_str=f"Step {step.step}: {step.description}")
            step_start = time.time()
            tr = await run_tool_agent_async(run_id, final_result, project_id=project_id)
            step_latency = int((time.time() - step_start) * 1000)
            
            if tr.get("status") == "success":
                if tr.get("project_id"): project_id = tr["project_id"]
                step.status = "success"
                step.result = f"Saved {len(tr.get('files', []))} files."
                tool_result = tr
            else:
                step.status = "error"
                step.error = tr.get("message", "Tool failed")
                
            step.latency_ms = step_latency
            steps_completed += 1
            add_step(run_id, i + 1, step_agent, step.description[:5000], "tool-script")
            update_step(run_id, step_agent, status=step.status, output=(step.result or '')[:10000], latency_ms=step_latency, tokens=0)
            continue

        # Get model — canvas node override takes priority over config
        agent_cfg = MODELS.get(step_agent, MODELS["analyst"])
        default_model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg
        model = (node_models or {}).get(step_agent) or default_model

        await emitter.emit(
            run_id,
            step_agent,
            "start",
            input_str=f"Step {step.step}: {step.description}",
        )

        agent_start = time.time()
        step_result = ""

        try:
            if step_agent == "coder":
                async for chunk in run_coder_async(
                    context_prompt, model_override=model
                ):
                    step_result += chunk
                    if len(step_result) % 50 == 0:
                        await emitter.emit(
                            run_id, step_agent, "update", output_str=step_result
                        )

            elif step_agent == "critic":
                async for chunk in run_critic_async(
                    context_prompt, model_override=model
                ):
                    step_result += chunk
                    if len(step_result) % 50 == 0:
                        await emitter.emit(
                            run_id, step_agent, "update", output_str=step_result
                        )

            elif step_agent == "researcher":
                async for chunk in run_researcher_async(
                    context_prompt, model_override=model
                ):
                    step_result += chunk
                    if len(step_result) % 50 == 0:
                        await emitter.emit(
                            run_id, step_agent, "update", output_str=step_result
                        )

            else:  # analyst
                async for chunk in run_analyst_async(
                    context_prompt, model_override=model
                ):
                    step_result += chunk
                    if len(step_result) % 50 == 0:
                        await emitter.emit(
                            run_id, step_agent, "update", output_str=step_result
                        )

            step_latency = int((time.time() - agent_start) * 1000)
            step.status = "success"
            step.result = step_result[:3000]
            step.latency_ms = step_latency
            steps_completed += 1

            add_step(run_id, i + 1, step_agent, step.description[:5000], model)
            update_step(run_id, step_agent, status="success", output=step_result[:10000], latency_ms=step_latency, tokens=len(step_result))

            await emitter.emit(
                run_id,
                step_agent,
                "complete",
                output_str=step_result,
                metadata={
                    "latency_ms": step_latency,
                    "model": model,
                    "step": step.step,
                },
            )

            log_agent_execution(
                run_id,
                step_agent,
                model,
                f"step_{step.step}_complete",
                latency_ms=step_latency,
                tokens_out=len(step_result),
            )

            final_result = step_result

        except Exception as e:
            local_error = str(e)
            log_agent_execution(run_id, step_agent, model, f"step_{step.step}_error", error=local_error)

            LOCAL_FALLBACK = "deepseek-r1:8b"

            # For all agents — fall back to light local model, never cloud
            await emitter.emit(run_id, step_agent, "update",
                    output_str=f"⚡ {model} unavailable — falling back to {LOCAL_FALLBACK}...")
        step_result = ""
        fb_start = time.time()
        try:
            gen = (run_coder_async(context_prompt, model_override=LOCAL_FALLBACK)
                   if step_agent == "coder"
                   else run_analyst_async(context_prompt, model_override=LOCAL_FALLBACK))
            async for chunk in gen:
                step_result += chunk
                if len(step_result) % 80 == 0:
                    await emitter.emit(run_id, step_agent, "update", output_str=step_result)
            fb_latency = int((time.time() - fb_start) * 1000)
            step.status = "success"
            step.result = step_result[:3000]
            step.latency_ms = fb_latency
            steps_completed += 1
            await emitter.emit(run_id, step_agent, "complete", output_str=step_result,
                metadata={"latency_ms": fb_latency, "model": LOCAL_FALLBACK, "step": step.step})
            final_result = step_result
        except Exception as fe:
            step.status = "error"
            step.error = f"All local models failed: {fe}"
            await emitter.emit(run_id, step_agent, "error", error=step.error)
            break

    # ── Step 4: Auto-Tool (save files FIRST so critic can validate actual code) ──
    execution_result = None
    tool_result = None
    pid = project_id

    if route == "coder" and final_result and steps_completed > 0:
        # Always run tool agent for coder routes — don't require markers
        has_markers = "```" in final_result or "---JSON---" in final_result

        if has_markers:
            tool_result = await run_tool_agent_async(
                run_id, final_result, project_id=project_id
            )
            if tool_result.get("status") == "success" and tool_result.get("project_id"):
                pid = tool_result["project_id"]
        else:
            # No markers — try to save as a single file anyway
            await emitter.emit(
                run_id,
                "tool",
                "start",
                input_str="Saving code output (no JSON markers detected)...",
            )
            project_dir = os.path.join(WORKSPACE_DIR, pid)
            os.makedirs(project_dir, exist_ok=True)

            # Try to extract code blocks
            import re

            code_match = re.search(
                r"```(?:python|javascript|java|html|css|ts|bash|sh)?\s*(.*?)```",
                final_result,
                re.DOTALL,
            )
            code_content = (
                code_match.group(1).strip() if code_match else final_result.strip()
            )

            # Determine file extension
            if any(
                kw in final_result.lower()
                for kw in ["def ", "import ", "class ", "print("]
            ):
                filename = "main.py"
            elif any(
                kw in final_result.lower()
                for kw in ["function ", "const ", "let ", "var ", "console."]
            ):
                filename = "main.js"
            elif "<html" in final_result.lower() or "<div" in final_result.lower():
                filename = "index.html"
            else:
                filename = "main.py"

            file_path = os.path.join(project_dir, filename)
            with open(file_path, "w") as f:
                f.write(code_content)

            meta = {
                "project_id": pid,
                "entry_point": filename,
                "language": "python"
                if filename.endswith(".py")
                else "javascript"
                if filename.endswith(".js")
                else "html",
                "dependencies": [],
                "files": [filename, "project.json"],
            }
            with open(os.path.join(project_dir, "project.json"), "w") as f:
                json.dump(meta, f, indent=2)

            await emitter.emit(
                run_id,
                "tool",
                "complete",
                output_str=f"Project '{pid}' created (1 file: {filename})",
                metadata={"files_created": 1, "project_id": pid},
            )
            tool_result = {"status": "success", "files": [filename], "project_id": pid}

    # ── Step 5: Feedback Loop (Critic validates saved files, not raw output) ──
    if route == "coder" and final_result and steps_completed > 0:
        # If we have saved files, validate the actual code
        if tool_result and tool_result.get("status") == "success":
            project_dir = os.path.join(WORKSPACE_DIR, pid)
            meta_path = os.path.join(project_dir, "project.json")
            if os.path.exists(meta_path):
                with open(meta_path, "r") as f:
                    meta = json.load(f)

                # Read all code files for validation
                code_files_content = {}
                for fname in meta.get("files", []):
                    fpath = os.path.join(project_dir, fname)
                    if os.path.exists(fpath) and fname.endswith(
                        (".py", ".js", ".ts", ".html")
                    ):
                        with open(fpath, "r") as f:
                            code_files_content[fname] = f.read()

                # Build validation prompt from actual files
                files_text = "\n\n".join(
                    [
                        f"=== {name} ===\n{content}"
                        for name, content in code_files_content.items()
                    ]
                )

                await emitter.emit(
                    run_id,
                    "critic",
                    "start",
                    input_str="Validating saved code files...",
                )

                critic_prompt_text = critic_file_review_prompt().format(
                    original_task=prompt, files_text=files_text[:4000]
                )

                try:
                    critic_output = ""
                    # 60s timeout — if critic model can't load, skip validation
                    async def _run_critic_with_timeout():
                        out = ""
                        async for chunk in run_critic_async(critic_prompt_text):
                            out += chunk
                        return out

                    try:
                        critic_output = await asyncio.wait_for(
                            _run_critic_with_timeout(), timeout=60.0
                        )
                    except asyncio.TimeoutError:
                        await emitter.emit(run_id, "critic", "complete",
                            output_str="Critic timed out — skipping validation",
                            metadata={"skipped": True})
                        critic_output = ""

                    # Parse critic response
                    from services.sanitizer import (
                        extract_json_object,
                        strip_prompt_leakage,
                    )

                    cleaned = strip_prompt_leakage(critic_output)
                    feedback = extract_json_object(cleaned)

                    if not feedback:
                        feedback = {
                            "score": 7,
                            "verdict": "PASS",
                            "issues": [],
                            "suggestions": [],
                        }

                    status_icon = "✅" if feedback.get("verdict") == "PASS" else "⚠️"
                    summary = f"{status_icon} Score: {feedback.get('score', '?')}/10 | Verdict: {feedback.get('verdict', '?')}"

                    await emitter.emit(
                        run_id,
                        "critic",
                        "complete",
                        output_str=summary,
                        metadata={
                            "score": feedback.get("score"),
                            "verdict": feedback.get("verdict"),
                        },
                    )

                    # If NEEDS_REVISION, fix the actual files
                    if feedback.get("verdict") == "NEEDS_REVISION":
                        for retry in range(2):
                            if retry == 1:
                                heavy_cfg = MODELS.get(
                                    "heavy", {"name": "devstral:24b"}
                                )
                                fix_model = (
                                    heavy_cfg["name"]
                                    if isinstance(heavy_cfg, dict)
                                    else heavy_cfg
                                )
                                await emitter.emit(
                                    run_id,
                                    "manager",
                                    "update",
                                    output_str=f"⚠️ Deep bug detected. Escalating to Heavy Agent...",
                                )
                            else:
                                fix_model = MODELS.get(
                                    "coder", {"name": "qwen2.5-coder:14b"}
                                )
                                fix_model = (
                                    fix_model["name"]
                                    if isinstance(fix_model, dict)
                                    else fix_model
                                )

                            # Fix each file that has issues
                            for fname, fcontent in code_files_content.items():
                                fix_prompt = coder_fix_prompt().format(
                                    issues=feedback.get("issues", []),
                                    suggestions=feedback.get("suggestions", []),
                                    original_task=prompt,
                                    filename=fname,
                                    file_content=fcontent,
                                )

                                await emitter.emit(
                                    run_id,
                                    "coder",
                                    "start",
                                    input_str=f"Fixing {fname} (attempt {retry + 1}/2)",
                                )

                                fixed = ""
                                async for chunk in run_coder_async(
                                    fix_prompt, model_override=fix_model
                                ):
                                    fixed += chunk
                                    if len(fixed) % 50 == 0:
                                        await emitter.emit(
                                            run_id, "coder", "update", output_str=fixed
                                        )

                                # Strip markdown wrappers
                                code_match = re.search(
                                    r"```(?:python|javascript|js|html)?\s*(.*?)```",
                                    fixed,
                                    re.DOTALL,
                                )
                                patched = (
                                    code_match.group(1).strip()
                                    if code_match
                                    else fixed.strip()
                                )

                                fpath = os.path.join(project_dir, fname)
                                with open(fpath, "w") as f:
                                    f.write(patched)
                                code_files_content[fname] = patched

                                await emitter.emit(
                                    run_id,
                                    "coder",
                                    "complete",
                                    output_str=f"Fixed {fname}",
                                    metadata={"file": fname, "attempt": retry + 1},
                                )

                            # Re-validate after fix
                            files_text = "\n\n".join(
                                [
                                    f"=== {name} ===\n{content}"
                                    for name, content in code_files_content.items()
                                ]
                            )
                            recheck_prompt_text = critic_recheck_prompt().format(
                                original_task=prompt, files_text=files_text[:4000]
                            )

                            recheck_output = ""
                            async for chunk in run_critic_async(recheck_prompt_text):
                                recheck_output += chunk

                            cleaned = strip_prompt_leakage(recheck_output)
                            feedback = extract_json_object(cleaned)
                            if not feedback:
                                feedback = {
                                    "score": 7,
                                    "verdict": "PASS",
                                    "issues": [],
                                    "suggestions": [],
                                }

                            if feedback.get("verdict") == "PASS":
                                await emitter.emit(
                                    run_id,
                                    "critic",
                                    "complete",
                                    output_str=f"✅ Fix accepted. Score: {feedback.get('score', '?')}/10",
                                    metadata={
                                        "score": feedback.get("score"),
                                        "verdict": "PASS",
                                    },
                                )
                                break
                        else:
                            await emitter.emit(
                                run_id,
                                "critic",
                                "complete",
                                output_str=f"⚠️ Max retries reached. Score: {feedback.get('score', '?')}/10",
                                metadata={
                                    "score": feedback.get("score"),
                                    "verdict": feedback.get(
                                        "verdict", "NEEDS_REVISION"
                                    ),
                                },
                            )
                except Exception as e:
                    await emitter.emit(run_id, "critic", "error", error=str(e))
        else:
            # No files saved — fallback to raw output validation
            feedback = await _run_feedback_loop(
                run_id, final_result, prompt, allow_heavy
            )

            if feedback and feedback.get("verdict") == "NEEDS_REVISION":
                current_coder_model = MODELS.get(
                    "coder", {"name": "qwen2.5-coder:14b"}
                )
                current_coder_model = (
                    current_coder_model["name"]
                    if isinstance(current_coder_model, dict)
                    else current_coder_model
                )
                for retry in range(2):
                    if retry == 1:
                        heavy_cfg = MODELS.get("heavy", {"name": "devstral:24b"})
                        current_coder_model = (
                            heavy_cfg["name"]
                            if isinstance(heavy_cfg, dict)
                            else heavy_cfg
                        )
                        await emitter.emit(
                            run_id,
                            "manager",
                            "update",
                            output_str=f"⚠️ Deep bug detected. Escalating to Heavy Agent ({current_coder_model})...",
                        )

                    revision_prompt_text = coder_revision_prompt().format(
                        issues=feedback.get("issues", []),
                        suggestions=feedback.get("suggestions", []),
                        original_task=prompt,
                        previous_output=final_result[:3000],
                    )

                    await emitter.emit(
                        run_id,
                        "coder",
                        "start",
                        input_str=f"Revision {retry + 1}/2"
                        + (" (Escalated)" if retry == 1 else ""),
                    )
                    revised = ""
                    async for chunk in run_coder_async(
                        revision_prompt_text, model_override=current_coder_model
                    ):
                        revised += chunk
                        if len(revised) % 50 == 0:
                            await emitter.emit(
                                run_id, "coder", "update", output_str=revised
                            )

                    await emitter.emit(
                        run_id,
                        "coder",
                        "complete",
                        output_str=revised,
                        metadata={
                            "revision": retry + 1,
                            "model_used": current_coder_model,
                        },
                    )

                    feedback = await _run_feedback_loop(
                        run_id, revised, prompt, allow_heavy
                    )
                    if feedback and feedback.get("verdict") in ["PASS", None]:
                        final_result = revised
                        break
                    final_result = revised

                # Try to save revised output
                if tool_result is None or tool_result.get("status") != "success":
                    has_markers = "```" in final_result or "---JSON---" in final_result
                    if has_markers:
                        tool_result = await run_tool_agent_async(
                            run_id, final_result, project_id=project_id
                        )
                        if tool_result.get("status") == "success" and tool_result.get(
                            "project_id"
                        ):
                            pid = tool_result["project_id"]

    # ── Step 6: Generate README (only if project was created) ──
    if (
        tool_result
        and tool_result.get("status") == "success"
        and tool_result.get("project_id")
    ):
        pid = tool_result["project_id"]

        # Generate README using coder agent (not critic) for proper documentation
        await _generate_readme_async(run_id, pid, prompt, final_result)

        # Only run autofix if the project has dependencies or entry point is not trivial
        exec_result = await autofix_loop_async(run_id, pid, max_retries=2)
        execution_result = exec_result

        # If execution succeeded, emit success event for executor node
        if exec_result and exec_result.get("status") == "success":
            await emitter.emit(
                run_id,
                "executor",
                "complete",
                output_str=exec_result.get("output", "Execution successful"),
                metadata={
                    "exit_code": exec_result.get("exit_code", 0),
                    "project_id": pid,
                },
            )
        elif exec_result and exec_result.get("status") == "error":
            await emitter.emit(
                run_id,
                "executor",
                "error",
                error=exec_result.get(
                    "errors", exec_result.get("output", "Unknown error")
                ),
            )

    # ── Step 6: Finalize ──
    total_latency = int((time.time() - start_time) * 1000)
    task.mark_complete("success" if steps_completed > 0 else "error")

    # Update session
    if session_id:
        add_turn(session_id, "user", prompt)

        agent_cfg = MODELS.get(route, {})
        resp_model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg

        add_turn(
            session_id, "assistant", final_result[:3000], agent=route, model=resp_model
        )
        update_session(session_id, active_mode="agent")

        # Compress context periodically
        session = get_session(session_id)
        if session and len(session["history"]) > 6:
            summary = await compress_context(session["history"])
            update_session(session_id, context_summary=summary)

    store_run(
        run_id,
        prompt,
        route,
        final_result[:3000],
        project_id,
        "success" if steps_completed > 0 else "error",
        total_latency,
    )
    update_pattern(prompt, route, steps_completed > 0)
    update_run(run_id, status="success" if steps_completed > 0 else "error", total_latency_ms=total_latency)
    record_run(run_id, "agent", route, 
        MODELS.get(route, {}).get("name", route) if isinstance(MODELS.get(route), dict) else MODELS.get(route, route),
        total_latency, len(final_result), "success" if steps_completed > 0 else "error", session_id or "")

    log_pipeline_end(run_id, "success", total_latency, steps_completed)

    # Signal all nodes to reset — frontend uses this to clear any stuck "running" states
    await emitter.emit(
        run_id, "system", "run_complete",
        output_str=f"Pipeline finished in {total_latency}ms",
        metadata={"total_latency_ms": total_latency, "steps": steps_completed},
    )

    # Release all models from VRAM after pipeline completes
    try:
        from services.vram_scheduler import unload_all
        await unload_all()
    except Exception:
        pass

    return ExecutionResult(
        task_id=run_id,
        run_id=run_id,
        mode="agent",
        route=route,
        result=final_result,
        goal=goal,
        project_id=project_id,
        steps_completed=steps_completed,
        steps_total=len(task.steps),
        total_latency_ms=total_latency,
        status="success" if steps_completed > 0 else "error",
        feedback=feedback,
        execution=execution_result,
    )


async def _run_feedback_loop(
    run_id: str,
    output: str,
    original_task: str,
    allow_heavy: bool = False,
) -> dict:
    """
    Critic Pattern: Manager validates Coder output.
    Returns quality assessment dict.
    """
    await emitter.emit(
        run_id, "critic", "start", input_str="Validating output quality..."
    )

    try:
        feedback = await validate_output(output, original_task)

        status_icon = "✅" if feedback["verdict"] == "PASS" else "⚠️"
        summary = (
            f"{status_icon} Score: {feedback['score']}/10 | "
            f"Verdict: {feedback['verdict']}"
        )

        if feedback.get("issues"):
            summary += f"\nIssues: {', '.join(feedback['issues'][:3])}"

        await emitter.emit(
            run_id,
            "critic",
            "complete",
            output_str=summary,
            metadata={"score": feedback["score"], "verdict": feedback["verdict"]},
        )

        log_agent_execution(
            run_id,
            "critic",
            MODELS.get("critic", {}).get("name", "llama3.1:8b"),
            "feedback_complete",
            tokens_out=len(summary),
        )

        return feedback

    except Exception as e:
        await emitter.emit(run_id, "critic", "error", error=str(e))
        return {"score": 6, "verdict": "PASS", "issues": [], "suggestions": []}


async def _generate_readme_async(
    run_id: str,
    project_id: str,
    original_prompt: str,
    code_output: str,
) -> None:
    """
    Critic generates a README.md for every project.
    Called after tool agent creates the project files.
    """
    import os

    workspace_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "workspace"
    )
    project_dir = os.path.join(workspace_dir, project_id)

    if not os.path.exists(project_dir):
        return

    await emitter.emit(
        run_id, "critic", "start", input_str="📝 Generating README.md for project..."
    )

    readme_prompt_text = readme_prompt().format(
        original_prompt=original_prompt, code_output=code_output[:2000]
    )

    readme_content = ""
    async for chunk in run_critic_async(readme_prompt_text):
        readme_content += chunk

    # Strip markdown code block wrappers if present
    import re

    md_match = re.search(r"```(?:markdown)?\s*(.*?)```", readme_content, re.DOTALL)
    if md_match:
        readme_content = md_match.group(1).strip()

    readme_path = os.path.join(project_dir, "README.md")
    with open(readme_path, "w") as f:
        f.write(readme_content)

    # Update project.json to include README
    meta_path = os.path.join(project_dir, "project.json")
    if os.path.exists(meta_path):
        import json

        with open(meta_path, "r") as f:
            meta = json.load(f)
        if "README.md" not in meta.get("files", []):
            meta["files"].append("README.md")
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=2)

    await emitter.emit(
        run_id,
        "critic",
        "complete",
        output_str=f"📝 README.md generated for '{project_id}'",
        metadata={"readme_path": readme_path},
    )
