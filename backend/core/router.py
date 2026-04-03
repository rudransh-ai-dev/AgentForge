from services.ollama_client import async_generate
from config import MODELS
from pydantic import BaseModel, ConfigDict
from services.sanitizer import extract_json_object, strip_prompt_leakage, auto_fix_json
from core.prompts import planner_prompt
import json
import re
import random


class PlanStep(BaseModel):
    step: int
    action: str  # "code", "analyze", "review", "execute", "install_deps"
    description: str
    agent: str  # "coder", "analyst", "critic", "tool", "executor"
    model_config = ConfigDict(extra="ignore")


class ExecutionPlan(BaseModel):
    goal: str
    project_id: str
    steps: list[PlanStep]
    model_config = ConfigDict(extra="ignore")


class RouteDecision(BaseModel):
    selected_agent: str
    reason: str
    confidence: float
    plan: list[dict] | None = None
    model_config = ConfigDict(extra="ignore")


TASK_ROUTER = {
    "code_generation": "coder",
    "debug_basic": "coder",
    "debug_complex": "heavy",
    "explanation": "analyst",
    "analysis": "analyst",
    "review": "critic",
    "data_task": "data",
}


def should_use_heavy(task_type: str, retries: int, confidence: float) -> bool:
    return retries >= 2 or confidence < 0.5 or task_type == "debug_complex"


def resolve_agent(task_type: str, confidence: float, retries: int = 0) -> str:
    base_agent = TASK_ROUTER.get(task_type, "analyst")
    if should_use_heavy(task_type, retries, confidence):
        return "heavy"
    return base_agent


async def plan_task_async(prompt: str) -> dict:
    """
    Planning Agent: Generates a multi-step execution plan and assigns task properties.
    """
    plan_prompt = planner_prompt().format(prompt=prompt)
    # Extract manager model name
    mgr_cfg = MODELS.get("manager", {"name": "phi3:mini"})
    mgr_model = mgr_cfg["name"] if isinstance(mgr_cfg, dict) else mgr_cfg

    response_text = await async_generate(mgr_model, plan_prompt)

    try:
        # Sanitize and extract JSON reliably
        cleaned = strip_prompt_leakage(response_text)
        parsed = extract_json_object(cleaned)

        if not parsed:
            # Critic auto-validator fallback
            parsed = await auto_fix_json(
                cleaned, "JSON structure could not be extracted."
            )
            if not parsed or not isinstance(parsed, dict):
                raise ValueError("No valid JSON found in router output")

        # Ensure parsed is a dict (type narrowing for static analysis)
        if not isinstance(parsed, dict):
            raise ValueError("Parsed result is not a JSON object")

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
            "task_type": parsed.get("task_type", "analysis"),
            "confidence": float(parsed.get("confidence", 0.9)),
            "steps": steps,
        }
    except Exception as e:
        # Fallback: single-step simple plan
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
            ]
        )
        task_type = "code_generation" if is_code else "explanation"
        agent = resolve_agent(task_type, 0.9)

        steps = [
            {
                "step": 1,
                "action": "code" if is_code else "analyze",
                "description": prompt[:100],
                "agent": agent,
            }
        ]
        if is_code:
            steps.append(
                {
                    "step": 2,
                    "action": "save_files",
                    "description": "Save generated code",
                    "agent": "tool",
                }
            )
            steps.append(
                {
                    "step": 3,
                    "action": "execute",
                    "description": "Run and validate",
                    "agent": "executor",
                }
            )

        return {
            "goal": prompt[:80],
            "project_id": "project",
            "complexity": "simple",
            "task_type": task_type,
            "confidence": 0.9,
            "steps": steps,
        }


async def route_task_async(prompt: str) -> dict:
    """
    Enhanced Router: Now includes planning context.
    Returns routing decision + execution plan for complex tasks.
    """
    # First, generate a plan
    plan = await plan_task_async(prompt)

    # The first agent in the plan tells us what the primary task is, but we use strict mapping logic
    task_type = plan.get("task_type", "analysis")
    confidence = plan.get("confidence", 0.9)
    agent = resolve_agent(task_type, confidence)

    decision = RouteDecision(
        selected_agent=agent,
        reason=f"Plan: {plan['goal']} ({len(plan['steps'])} steps). Mapped '{task_type}' to '{agent}' (Conf: {confidence})",
        confidence=confidence,
        plan=plan["steps"],
    )

    return {
        **decision.model_dump(),
        "project_id": plan["project_id"],
        "goal": plan["goal"],
    }
