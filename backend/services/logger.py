"""
Structured Logger — JSON-formatted observability for the pipeline.

Every agent execution, model load/unload, and pipeline step is logged
as a structured JSON event. This enables dashboarding and debugging.
"""
import json
import time
import logging
from typing import Optional

# Create a separate logger that outputs structured JSON
logger = logging.getLogger("pipeline")
logger.setLevel(logging.INFO)

# Prevent duplicate handlers
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)


def log_event(
    run_id: str,
    agent: str,
    model: str,
    phase: str,
    status: str = "running",
    latency_ms: int = 0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    vram_usage_mb: int = 0,
    error: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """
    Emit a structured log event matching the observability schema
    defined in system-design.md.
    """
    event = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_id": run_id,
        "agent": agent,
        "model": model,
        "phase": phase,
        "latency_ms": latency_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "status": status,
        "vram_usage_mb": vram_usage_mb,
    }
    if error:
        event["error"] = error
    if metadata:
        event["metadata"] = metadata

    logger.info(json.dumps(event))
    return event


def log_pipeline_start(run_id: str, mode: str, prompt: str):
    """Log the beginning of a pipeline execution."""
    return log_event(
        run_id=run_id,
        agent="pipeline",
        model="",
        phase="pipeline_start",
        status="running",
        tokens_in=len(prompt.split()),
        metadata={"mode": mode, "prompt_preview": prompt[:100]},
    )


def log_pipeline_end(run_id: str, status: str, total_latency_ms: int, steps_completed: int = 0):
    """Log the completion of a pipeline execution."""
    return log_event(
        run_id=run_id,
        agent="pipeline",
        model="",
        phase="pipeline_end",
        status=status,
        latency_ms=total_latency_ms,
        metadata={"steps_completed": steps_completed},
    )


def log_agent_execution(
    run_id: str,
    agent: str,
    model: str,
    phase: str,
    latency_ms: int = 0,
    tokens_out: int = 0,
    status: str = "success",
    error: Optional[str] = None,
):
    """Log an individual agent execution step."""
    from services.vram_scheduler import vram_state
    vram_mb = int(vram_state.used_gb * 1024)
    return log_event(
        run_id=run_id,
        agent=agent,
        model=model,
        phase=phase,
        latency_ms=latency_ms,
        tokens_out=tokens_out,
        status=status,
        vram_usage_mb=vram_mb,
        error=error,
    )


def log_model_lifecycle(run_id: str, model: str, action: str, latency_ms: int = 0):
    """Log model load/unload events."""
    return log_event(
        run_id=run_id,
        agent="vram_scheduler",
        model=model,
        phase=f"model_{action}",
        latency_ms=latency_ms,
        status="success",
    )
