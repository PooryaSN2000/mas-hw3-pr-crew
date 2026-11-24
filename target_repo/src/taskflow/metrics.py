"""Execution telemetry and summary metrics collection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from taskflow.models import TaskResult, TaskStatus


@dataclass
class RunMetrics:
    """Snapshot of performance and outcome metrics for a workflow run."""

    workflow_name: str
    total_tasks: int = 0
    succeeded_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    cached_tasks: int = 0
    total_attempts: int = 0
    total_retries: int = 0
    total_duration_ms: float = 0.0
    per_task_duration_ms: Dict[str, float] = field(default_factory=dict)

    def slowest_task(self) -> Optional[str]:
        """Return the name of the task with the largest recorded duration."""
        if not self.per_task_duration_ms:
            return None
        return max(self.per_task_duration_ms, key=self.per_task_duration_ms.get)  # type: ignore[arg-type]

    def cache_hit_ratio(self) -> float:
        """Return fraction of tasks served directly from cache."""
        if self.total_tasks == 0:
            return 0.0
        return round(self.cached_tasks / self.total_tasks, 4)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics snapshot into a JSON-friendly dictionary."""
        return {
            "workflow_name": self.workflow_name,
            "total_tasks": self.total_tasks,
            "succeeded_tasks": self.succeeded_tasks,
            "failed_tasks": self.failed_tasks,
            "skipped_tasks": self.skipped_tasks,
            "cached_tasks": self.cached_tasks,
            "total_attempts": self.total_attempts,
            "total_retries": self.total_retries,
            "total_duration_ms": round(self.total_duration_ms, 3),
            "cache_hit_ratio": self.cache_hit_ratio(),
            "slowest_task": self.slowest_task(),
        }


class MetricsCollector:
    """Aggregates TaskResult records into a RunMetrics summary."""

    def __init__(self, workflow_name: str) -> None:
        self.workflow_name = workflow_name
        self._records: List[TaskResult] = []

    def record(self, result: TaskResult) -> None:
        """Record a completed, cached, failed, or skipped task result."""
        self._records.append(result)

    def finalize(self, total_duration_ms: float) -> RunMetrics:
        """Compute final RunMetrics across all recorded results."""
        metrics = RunMetrics(
            workflow_name=self.workflow_name,
            total_tasks=len(self._records),
            total_duration_ms=total_duration_ms,
        )
        for res in self._records:
            metrics.total_attempts += res.attempts
            if res.attempts > 1:
                metrics.total_retries += res.attempts - 1
            metrics.per_task_duration_ms[res.task_name] = round(res.duration_ms, 3)
            if res.status == TaskStatus.SUCCESS:
                metrics.succeeded_tasks += 1
            elif res.status == TaskStatus.FAILED:
                metrics.failed_tasks += 1
            elif res.status == TaskStatus.SKIPPED:
                metrics.skipped_tasks += 1
            elif res.status == TaskStatus.CACHED:
                metrics.cached_tasks += 1
        return metrics
