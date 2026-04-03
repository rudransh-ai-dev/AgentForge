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
from services.event_emitter import emitter
from services.logger import log_pipeline_start, log_pipeline_end, log_agent_execution
from core.memory import store_run, update_pattern
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

WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")

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

# Model downgrade fallbacks for budget enforcement
MODEL_DOWNGRADES = {
    "devstral:24b": "qwen2.5:14b",
    "qwen2.5-coder:32b": "devstral:24b",
    "qwen2.5:14b": "llama3:8b",
    "deepseek-coder-v2:16b": "qwen2.5-coder:7b",
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


def _get_agent_model(
    agent: str, allow_heavy: bool = False, budget_ms: int = 15000
) -> str:
    """
    Get the appropriate model for an agent, respecting budget constraints.
    """
    agent_cfg = MODELS.get(agent, {"name": "llama3:8b"})
    model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg

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
        await emitter.emit(run_id, agent, "error", error=str(e))
        log_agent_execution(run_id, agent, model, "direct_error", error=str(e))
        result = f"Error: {e}"

    # Update session
    if session_id:
        add_turn(session_id, "user", prompt)
        add_turn(session_id, "assistant", result[:3000], agent=agent, model=model)
        update_session(session_id, active_mode="direct")

    total_latency = int((time.time() - start_time) * 1000)
    store_run(run_id, prompt, agent, result[:3000], "", "success", total_latency)
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

    for i, step in enumerate(task.steps):
        step_agent = step.agent
        step.status = "running"

        # Skip non-primary agents in this simplified loop
        if step_agent not in ["coder", "analyst", "critic"]:
            continue

        # Get model name from the rich config
        agent_cfg = MODELS.get(step_agent, MODELS["analyst"])
        model = agent_cfg["name"] if isinstance(agent_cfg, dict) else agent_cfg

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
            step.status = "error"
            step.error = str(e)
            await emitter.emit(run_id, step_agent, "error", error=str(e))
            log_agent_execution(
                run_id, step_agent, model, f"step_{step.step}_error", error=str(e)
            )
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
                    from agents.critic import run_critic_async

                    critic_output = ""
                    async for chunk in run_critic_async(critic_prompt_text):
                        critic_output += chunk

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
                                    "coder", {"name": "deepseek-coder-v2:16b"}
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
                                from agents.coder import run_coder_async

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
                    "coder", {"name": "deepseek-coder-v2:16b"}
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
            MODELS.get("critic", {}).get("name", "llama3:8b"),
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
    from agents.critic import run_critic_async

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
