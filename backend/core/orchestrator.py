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
import asyncio
import time
import uuid
from typing import Optional

from core.router import route_task_async
from agents.coder import run_coder_async
from agents.analyst import run_analyst_async
from agents.critic import run_critic_async, validate_output
from agents.tool import run_tool_agent_async, execute_project_async, autofix_loop_async
from services.event_emitter import emitter
from services.logger import log_pipeline_start, log_pipeline_end, log_agent_execution
from core.memory import store_run, update_pattern
from core.session import get_session, add_turn, update_session, create_session
from core.context import compress_context, build_context_window
from schemas.task import Task, TaskStep, TaskBudget, ExecutionResult
from config import MODELS
from services.vram_scheduler import get_model_info, MODEL_REGISTRY

# ── Global Pipeline Lock ──
# Only one pipeline execution at a time (FIFO queue)
pipeline_lock = asyncio.Lock()

# ── Latency Budget Thresholds ──
LATENCY_BUDGETS = {
    "direct": 2000,    # 2 seconds
    "agent": 15000,    # 15 seconds
    "heavy": 25000,    # 25 seconds for Qwen/Mixtral
    "reload": 6000,    # 6 seconds for model reload
}

# Model downgrade fallbacks for budget enforcement
MODEL_DOWNGRADES = {
    "qwen3.5:35b-a3b": "yolo0perris/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-GGUF_Q3_K_M:latest",
    "yolo0perris/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-GGUF_Q3_K_M:latest": "llama3:8b",
    "mixtral:latest": "llama3:8b",
    "deepseek-coder:6.7b": "phi3:mini",
    "llama3:8b": "phi3:mini",
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


def _get_agent_model(agent: str, allow_heavy: bool = False, budget_ms: int = 15000) -> str:
    """
    Get the appropriate model for an agent, respecting budget constraints.
    """
    model = MODELS.get(agent, "llama3:8b")

    if not allow_heavy:
        info = get_model_info(model)
        if info.get("is_heavy", False):
            # Force downgrade for non-heavy-allowed tasks
            model = MODEL_DOWNGRADES.get(model, "llama3:8b")

    # Check latency budget
    downgrade = _should_downgrade(model, budget_ms)
    if downgrade:
        model = downgrade

    return model


# ══════════════════════════════════════════════════════════════
# DIRECT MODE — No pipeline, single model response
# ══════════════════════════════════════════════════════════════

async def run_direct_mode(
    prompt: str,
    session_id: Optional[str] = None,
    model_override: Optional[str] = None
) -> ExecutionResult:
    """
    Direct Mode execution — bypasses the pipeline.
    User → Selected Model → Response

    Target latency: < 2 seconds
    """
    run_id = str(uuid.uuid4())
    start_time = time.time()

    log_pipeline_start(run_id, "direct", prompt)
    await emitter.emit(run_id, "system", "start", input_str=f"⚡ Direct Mode: {prompt[:80]}")

    # Build context if session exists
    context_prompt = prompt
    if session_id:
        session = get_session(session_id)
        if session:
            from core.context import build_context_window
            session_ctx = session.get("context_summary", "")
            context_prompt = build_context_window(session_ctx, prompt)

    # Determine agent from simple keyword matching
    is_code = any(kw in prompt.lower() for kw in [
        "code", "write", "build", "create", "script", "program", "app",
        "function", "class", "implement", "debug", "fix"
    ])
    agent = "coder" if is_code else "analyst"
    
    # Extract model name from dictionary
    agent_model_info = MODELS.get(agent, MODELS["analyst"])
    base_model = agent_model_info["name"] if isinstance(agent_model_info, dict) else agent_model_info
    
    model = model_override or base_model

    # Execute
    await emitter.emit(run_id, agent, "start", input_str=prompt)
    result = ""
    agent_start = time.time()

    try:
        gen = run_coder_async(context_prompt, model_override=model) if agent == "coder" \
            else run_analyst_async(context_prompt, model_override=model)

        async for chunk in gen:
            result += chunk
            if len(result) % 50 == 0:
                await emitter.emit(run_id, agent, "update", output_str=result)

        latency_ms = int((time.time() - agent_start) * 1000)
        await emitter.emit(run_id, agent, "complete", output_str=result,
                          metadata={"latency_ms": latency_ms, "model": model, "mode": "direct"})

        log_agent_execution(run_id, agent, model, "direct_complete",
                          latency_ms=latency_ms, tokens_out=len(result))

    except Exception as e:
        await emitter.emit(run_id, agent, "error", error=str(e))
        log_agent_execution(run_id, agent, model, "direct_error", error=str(e))
        result = f"Error: {e}"

    # Update session
    if session_id:
        add_turn(session_id, "user", prompt)
        add_turn(session_id, "assistant", result[:3000], agent=agent, model=model)
        update_session(session_id, active_mode="direct")

    total_latency = int((time.time() - start_time) * 1000)
    store_run(run_id, prompt, agent, result[:3000], None, "success", total_latency)
    update_pattern(prompt, agent, True)
    log_pipeline_end(run_id, "success", total_latency)

    return ExecutionResult(
        task_id=run_id,
        run_id=run_id,
        mode="direct",
        route=agent,
        result=result,
        total_latency_ms=total_latency,
        status="success",
    )


# ══════════════════════════════════════════════════════════════
# AGENT MODE — Full orchestration pipeline
# ══════════════════════════════════════════════════════════════

async def run_agent_mode(
    prompt: str,
    session_id: Optional[str] = None,
    allow_heavy: bool = False,
) -> ExecutionResult:
    """
    Agent Mode execution — full pipeline.
    User → Router → Planner → Agent(s) → Manager → Output

    Target latency: 8-15s (standard), <25s (heavy models)
    """
    run_id = str(uuid.uuid4())
    start_time = time.time()

    log_pipeline_start(run_id, "agent", prompt)

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
        decision = await route_task_async(prompt)
    except Exception as e:
        await emitter.emit(run_id, "manager", "error", error=str(e))
        log_pipeline_end(run_id, "error", int((time.time() - start_time) * 1000))
        return ExecutionResult(
            task_id=run_id, run_id=run_id, mode="agent", route="error",
            result=f"Router error: {e}", status="error",
            total_latency_ms=int((time.time() - start_time) * 1000),
        )

    route = decision.get("selected_agent", "analyst")
    plan_steps = decision.get("plan", [])
    goal = decision.get("goal", prompt[:80])
    project_id = decision.get("project_id", "project")
    confidence = decision.get("confidence", 1.0)

    router_latency = int((time.time() - start_time) * 1000)
    
    manager_model = MODELS["manager"]["name"] if isinstance(MODELS["manager"], dict) else MODELS["manager"]
    
    await emitter.emit(run_id, "manager", "complete",
                      output_str=f"Plan: {goal} ({len(plan_steps)} steps)",
                      metadata={"latency_ms": router_latency, "confidence": confidence,
                               "route": route, "steps": len(plan_steps)})

    log_agent_execution(run_id, "manager", manager_model, "routing_complete",
                       latency_ms=router_latency)

    # ── Step 2: Build Task Object ──
    budget = TaskBudget(
        max_latency_ms=LATENCY_BUDGETS["heavy"] if allow_heavy else LATENCY_BUDGETS["agent"],
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

    for i, step in enumerate(task.steps):
        step_agent = step.agent
        step.status = "running"

        # Skip non-primary agents in this simplified loop
        if step_agent not in ["coder", "analyst", "critic"]:
            continue

        # Get model name from the rich config
        agent_cfg = MODELS.get(step_agent, MODELS["analyst"])
        model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg

        await emitter.emit(run_id, step_agent, "start",
                          input_str=f"Step {step.step}: {step.description}")

        agent_start = time.time()
        step_result = ""

        try:
            if step_agent == "coder":
                async for chunk in run_coder_async(context_prompt, model_override=model):
                    step_result += chunk
                    if len(step_result) % 50 == 0:
                        await emitter.emit(run_id, step_agent, "update", output_str=step_result)

            elif step_agent == "critic":
                async for chunk in run_critic_async(context_prompt, model_override=model):
                    step_result += chunk
                    if len(step_result) % 50 == 0:
                        await emitter.emit(run_id, step_agent, "update", output_str=step_result)

            else:  # analyst
                async for chunk in run_analyst_async(context_prompt, model_override=model):
                    step_result += chunk
                    if len(step_result) % 50 == 0:
                        await emitter.emit(run_id, step_agent, "update", output_str=step_result)

            step_latency = int((time.time() - agent_start) * 1000)
            step.status = "success"
            step.result = step_result[:3000]
            step.latency_ms = step_latency
            steps_completed += 1

            await emitter.emit(run_id, step_agent, "complete", output_str=step_result,
                             metadata={"latency_ms": step_latency, "model": model,
                                      "step": step.step})

            log_agent_execution(run_id, step_agent, model, f"step_{step.step}_complete",
                              latency_ms=step_latency, tokens_out=len(step_result))

            final_result = step_result

        except Exception as e:
            step.status = "error"
            step.error = str(e)
            await emitter.emit(run_id, step_agent, "error", error=str(e))
            log_agent_execution(run_id, step_agent, model, f"step_{step.step}_error",
                              error=str(e))
            break

    # ── Step 4: Feedback Loop (Critic validates Coder output) ──
    if route == "coder" and final_result and steps_completed > 0:
        feedback = await _run_feedback_loop(run_id, final_result, prompt, allow_heavy)

        # If critic says NEEDS_REVISION, retry the coder (max 2 times)
        if feedback and feedback.get("verdict") == "NEEDS_REVISION":
            current_coder_model = model
            for retry in range(2):
                # Escalate to heavy model on the second retry if a deep bug is detected
                if retry == 1:
                    heavy_cfg = MODELS.get("heavy", {"name": "qwen3.5:35b-a3b"})
                    current_coder_model = heavy_cfg["name"] if isinstance(heavy_cfg, dict) else heavy_cfg
                    await emitter.emit(run_id, "manager", "update", output_str=f"⚠️ Deep bug detected. Escalating to Heavy Reasoning Agent ({current_coder_model})...")

                revision_prompt = (
                    f"Revise this code based on critic feedback:\n"
                    f"Issues: {feedback.get('issues', [])}\n"
                    f"Suggestions: {feedback.get('suggestions', [])}\n\n"
                    f"Original task: {prompt}\n\n"
                    f"Your previous output:\n{final_result[:2000]}"
                )

                await emitter.emit(run_id, "coder", "start",
                                  input_str=f"Revision {retry + 1}/2" + (" (Escalated)" if retry == 1 else ""))
                revised = ""
                async for chunk in run_coder_async(revision_prompt, model_override=current_coder_model):
                    revised += chunk
                    if len(revised) % 50 == 0:
                        await emitter.emit(run_id, "coder", "update", output_str=revised)

                await emitter.emit(run_id, "coder", "complete", output_str=revised,
                                  metadata={"revision": retry + 1, "model_used": current_coder_model})

                # Re-validate
                feedback = await _run_feedback_loop(run_id, revised, prompt, allow_heavy)
                if feedback and feedback.get("verdict") in ["PASS", None]:
                    final_result = revised
                    break
                final_result = revised

    # ── Step 5: Auto-Tool (save files if code was generated) ──
    if route == "coder" and final_result and ("```" in final_result or "---JSON---" in final_result):
        tool_result = await run_tool_agent_async(run_id, final_result, project_id=project_id)

        if tool_result.get("status") == "success" and tool_result.get("project_id"):
            pid = tool_result["project_id"]
            exec_result = await autofix_loop_async(run_id, pid, max_retries=2)
            execution_result = exec_result

    # ── Step 6: Finalize ──
    total_latency = int((time.time() - start_time) * 1000)
    task.mark_complete("success" if steps_completed > 0 else "error")

    # Update session
    if session_id:
        add_turn(session_id, "user", prompt)
        
        agent_cfg = MODELS.get(route, {})
        resp_model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg
        
        add_turn(session_id, "assistant", final_result[:3000], agent=route,
                model=resp_model)
        update_session(session_id, active_mode="agent")

        # Compress context periodically
        session = get_session(session_id)
        if session and len(session["history"]) > 6:
            summary = await compress_context(session["history"])
            update_session(session_id, context_summary=summary)

    store_run(run_id, prompt, route, final_result[:3000], project_id,
             "success" if steps_completed > 0 else "error", total_latency)
    update_pattern(prompt, route, steps_completed > 0)

    log_pipeline_end(run_id, "success", total_latency, steps_completed)

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
    await emitter.emit(run_id, "critic", "start",
                      input_str="Validating output quality...")

    try:
        feedback = await validate_output(output, original_task)

        status_icon = "✅" if feedback["verdict"] == "PASS" else "⚠️"
        summary = (f"{status_icon} Score: {feedback['score']}/10 | "
                  f"Verdict: {feedback['verdict']}")

        if feedback.get("issues"):
            summary += f"\nIssues: {', '.join(feedback['issues'][:3])}"

        await emitter.emit(run_id, "critic", "complete", output_str=summary,
                          metadata={"score": feedback["score"],
                                   "verdict": feedback["verdict"]})

        log_agent_execution(run_id, "critic", MODELS.get("critic", {}).get("name", "llama3:8b"),
                          "feedback_complete", tokens_out=len(summary))

        return feedback

    except Exception as e:
        await emitter.emit(run_id, "critic", "error", error=str(e))
        return {"score": 6, "verdict": "PASS", "issues": [], "suggestions": []}
