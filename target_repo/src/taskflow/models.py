"""Core data models and exception hierarchy for TaskFlow."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class TaskFlowError(Exception):
    """Base exception for all TaskFlow errors."""


class CycleDetectedError(TaskFlowError):
    """Raised when a circular dependency is detected in a workflow graph."""


class MissingDependencyError(TaskFlowError):
    """Raised when a task references an unknown upstream dependency."""


class WorkflowParseError(TaskFlowError):
    """Raised when a workflow definition cannot be parsed."""


class ValidationError(TaskFlowError):
    """Raised when strict workflow validation fails."""


class ConfigError(TaskFlowError):
    """Raised when a WorkflowConfig contains invalid settings."""


class SerializationError(TaskFlowError):
    """Raised when a workflow or report cannot be serialized."""


class HookError(TaskFlowError):
    """Raised when a lifecycle hook fails in strict hook mode."""


class TaskStatus(str, Enum):
    """Lifecycle status of an individual task execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CACHED = "cached"


@dataclass
class TaskSpec:
    """Declarative specification of a single task node in a workflow."""

    name: str
    command: str
    depends_on: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    max_retries: int = 0
    cacheable: bool = True
    tags: list[str] = field(default_factory=list)
    timeout_s: Optional[float] = None
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Task name must be a non-empty string.")
        if not self.command or not self.command.strip():
            raise ValueError(f"Task '{self.name}' must define a non-empty command.")
        if self.max_retries < 0:
            raise ValueError(f"Task '{self.name}' max_retries cannot be negative.")
        if self.timeout_s is not None and self.timeout_s <= 0:
            raise ValueError(f"Task '{self.name}' timeout_s must be positive.")


@dataclass
class TaskResult:
    """Outcome recorded after executing (or skipping/caching) a task."""

    task_name: str
    status: TaskStatus
    output: Any = None
    error: Optional[str] = None
    attempts: int = 0
    duration_ms: float = 0.0
    from_cache: bool = False


@dataclass
class Workflow:
    """Container for a named collection of interdependent tasks."""

    name: str
    tasks: dict[str, TaskSpec] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_task(self, task: TaskSpec) -> None:
        """Register a task specification into the workflow."""
        self.tasks[task.name] = task

    def get_task(self, name: str) -> TaskSpec:
        """Retrieve a task by name or raise KeyError."""
        return self.tasks[name]

    def task_names(self) -> list[str]:
        """Return sorted task names registered in this workflow."""
        return sorted(self.tasks.keys())

    def tasks_by_tag(self, tag: str) -> list[TaskSpec]:
        """Return all tasks carrying a specific tag."""
        return [spec for spec in self.tasks.values() if tag in spec.tags]


@dataclass
class WorkflowConfig:
    """Runtime configuration controlling execution behavior."""

    max_workers: int = 1
    fail_fast: bool = False
    default_retries: int = 0
    enable_cache: bool = True
    cache_dir: Optional[Path] = None
    strict_hooks: bool = False
    report_format: str = "text"

    def __post_init__(self) -> None:
        if self.max_workers < 1:
            raise ConfigError("max_workers must be >= 1.")
        if self.default_retries < 0:
            raise ConfigError("default_retries cannot be negative.")
        if self.cache_dir is not None and not isinstance(self.cache_dir, Path):
            self.cache_dir = Path(self.cache_dir)


@dataclass
class ValidationIssue:
    """Single finding emitted by WorkflowValidator."""

    severity: str  # "error" or "warning"
    code: str
    message: str
    task_name: Optional[str] = None


@dataclass
class ValidationReport:
    """Collection of validation issues for a workflow."""

    workflow_name: str
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


@dataclass
class ExecutionReport:
    """Structured summary of a full workflow execution."""

    workflow_name: str
    results: dict[str, TaskResult]
    execution_order: list[str]
    total_duration_ms: float
    dry_run: bool = False
    metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        """Return True if no task failed."""
        return all(r.status != TaskStatus.FAILED for r in self.results.values())
