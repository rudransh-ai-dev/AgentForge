"""
Task Schema — Standardized task objects with execution budgets.

Every task flowing through the pipeline uses this schema.
The Router creates tasks, the Orchestrator executes them.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from enum import Enum
import uuid
import time


class TaskType(str, Enum):
    CODE_GENERATION = "code_generation"
    ANALYSIS = "analysis"
    REVIEW = "review"
    DEBUG = "debug"
    SAVE_FILES = "save_files"
    EXECUTE = "execute"
    INSTALL_DEPS = "install_deps"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskBudget(BaseModel):
    """Resource constraints for a single task."""
    max_latency_ms: int = 15000
    max_model_size_gb: float = 10.0
    allow_heavy_model: bool = False
    max_tokens: int = 2048

    model_config = ConfigDict(extra='ignore')


class TaskStep(BaseModel):
    """A single step in an execution plan."""
    step: int
    action: str  # "code", "analyze", "review", "execute", "save_files", "install_deps"
    description: str
    agent: str  # "coder", "analyst", "critic", "tool", "executor"
    model: Optional[str] = None  # Override the default model for this agent
    status: str = "pending"  # pending, running, success, error, skipped
    result: Optional[str] = None
    latency_ms: int = 0
    error: Optional[str] = None

    model_config = ConfigDict(extra='ignore')


class Task(BaseModel):
    """
    Standardized task object that flows through the entire pipeline.
    Created by the Router, executed by the Orchestrator.
    """
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "analysis"
    agent: str = "analyst"
    model: Optional[str] = None
    input: str = ""
    constraints: list[str] = Field(default_factory=list)
    expected_output: str = "text"  # "code", "text", "json"
    priority: TaskPriority = TaskPriority.MEDIUM
    budget: TaskBudget = Field(default_factory=TaskBudget)

    # Execution plan (for Agent Mode)
    goal: str = ""
    project_id: str = "project"
    complexity: str = "simple"  # "simple" or "complex"
    steps: list[TaskStep] = Field(default_factory=list)

    # Execution state
    status: str = "pending"
    run_id: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None
    total_latency_ms: int = 0

    model_config = ConfigDict(extra='ignore')

    def mark_complete(self, status: str = "success"):
        self.status = status
        self.completed_at = time.time()
        self.total_latency_ms = int((self.completed_at - self.created_at) * 1000)


class ExecutionResult(BaseModel):
    """Result of a complete pipeline execution."""
    task_id: str
    run_id: str
    mode: str  # "direct" or "agent"
    route: str
    result: str = ""
    goal: str = ""
    project_id: Optional[str] = None
    steps_completed: int = 0
    steps_total: int = 0
    total_latency_ms: int = 0
    status: str = "success"
    feedback: Optional[dict] = None  # Critic feedback if applicable
    execution: Optional[dict] = None  # Project execution result if applicable

    model_config = ConfigDict(extra='ignore')
