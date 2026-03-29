from services.ollama_client import async_generate
from config import MODELS
from pydantic import BaseModel, ConfigDict
from services.sanitizer import extract_json_object, strip_prompt_leakage, auto_fix_json
import json
import re
import random


class PlanStep(BaseModel):
    step: int
    action: str  # "code", "analyze", "review", "execute", "install_deps"
    description: str
    agent: str  # "coder", "analyst", "critic", "tool", "executor"
    model_config = ConfigDict(extra='ignore')


class ExecutionPlan(BaseModel):
    goal: str
    project_id: str
    steps: list[PlanStep]
    model_config = ConfigDict(extra='ignore')


class RouteDecision(BaseModel):
    selected_agent: str
    reason: str
    confidence: float
    plan: list[dict] | None = None
    model_config = ConfigDict(extra='ignore')


async def plan_task_async(prompt: str) -> dict:
    """
    Planning Agent: Generates a multi-step execution plan for complex tasks.
    For simple tasks, returns a single-step plan.
    """
    plan_prompt = f"""You are an AI System Planner. Analyze the task and create an execution plan.

For SIMPLE tasks (questions, explanations, short code), create a 1-step plan.
For COMPLEX tasks (projects, multi-file apps, systems), create a multi-step plan.

Available agents and their actions:
- "coder" (action: "code") → Write code, create files, build features
- "analyst" (action: "analyze") → Explain concepts, reason about problems
- "critic" (action: "review") → Review code, evaluate quality
- "tool" (action: "save_files") → Save generated code to filesystem
- "executor" (action: "execute") → Run the project code

Respond with ONLY a JSON object:
{{
  "goal": "one-line summary of what we're building",
  "project_id": "short_snake_case_name",
  "complexity": "simple" or "complex",
  "steps": [
    {{"step": 1, "action": "code", "description": "what this step does", "agent": "coder"}},
    {{"step": 2, "action": "save_files", "description": "save to workspace", "agent": "tool"}},
    {{"step": 3, "action": "execute", "description": "run and test", "agent": "executor"}}
  ]
}}

Task: {prompt}
"""
    response_text = await async_generate(MODELS["manager"], plan_prompt)

    try:
        # Sanitize and extract JSON reliably
        cleaned = strip_prompt_leakage(response_text)
        parsed = extract_json_object(cleaned)
        
        if not parsed:
            # Critic auto-validator fallback
            parsed = await auto_fix_json(cleaned, "JSON structure could not be extracted.")
            if not parsed:
                raise ValueError("No valid JSON found in router output")

        # Validate steps
        steps = []
        for s in parsed.get("steps", []):
            try:
                steps.append(PlanStep(**s).model_dump())
            except Exception:
                continue

        if not steps:
            raise ValueError("No valid steps parsed")

        return {
            "goal": parsed.get("goal", prompt[:80]),
            "project_id": parsed.get("project_id", "project"),
            "complexity": parsed.get("complexity", "simple"),
            "steps": steps
        }
    except Exception as e:
        # Fallback: single-step simple plan
        is_code = any(kw in prompt.lower() for kw in ["code", "write", "build", "create", "script", "program", "app", "function"])
        agent = "coder" if is_code else "analyst"

        steps = [{"step": 1, "action": "code" if is_code else "analyze", "description": prompt[:100], "agent": agent}]
        if is_code:
            steps.append({"step": 2, "action": "save_files", "description": "Save generated code", "agent": "tool"})
            steps.append({"step": 3, "action": "execute", "description": "Run and validate", "agent": "executor"})

        return {
            "goal": prompt[:80],
            "project_id": "project",
            "complexity": "simple",
            "steps": steps
        }


async def route_task_async(prompt: str) -> dict:
    """
    Enhanced Router: Now includes planning context.
    Returns routing decision + execution plan for complex tasks.
    """
    # First, generate a plan
    plan = await plan_task_async(prompt)

    # The first agent in the plan is the route target
    first_step = plan["steps"][0] if plan["steps"] else None
    agent = first_step["agent"] if first_step else "analyst"

    if agent not in ["coder", "analyst", "critic"]:
        agent = "analyst"

    decision = RouteDecision(
        selected_agent=agent,
        reason=f"Plan: {plan['goal']} ({len(plan['steps'])} steps, {plan['complexity']})",
        confidence=0.9 if plan["complexity"] == "simple" else 0.85,
        plan=plan["steps"]
    )

    return {**decision.model_dump(), "project_id": plan["project_id"], "goal": plan["goal"]}
