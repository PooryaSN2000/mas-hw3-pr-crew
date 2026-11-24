"""Wave-based execution planner for sequential and concurrent workflow runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from taskflow.graph import WorkflowGraph
from taskflow.models import TaskResult, TaskStatus, Workflow


@dataclass
class ExecutionPlan:
    """Immutable execution plan produced before running a workflow."""

    workflow_name: str
    topological_order: List[str]
    waves: List[List[str]]
    max_parallelism: int


class ExecutionScheduler:
    """Computes deterministic execution waves and evaluates dependency readiness."""

    def __init__(self, workflow: Workflow) -> None:
        self.workflow = workflow
        self.graph = WorkflowGraph(workflow)

    def build_plan(self) -> ExecutionPlan:
        """Validate the graph and construct a wave-by-wave execution plan."""
        order = self.graph.topological_sort()
        waves = self.graph.execution_levels()
        max_width = max((len(wave) for wave in waves), default=0)
        return ExecutionPlan(
            workflow_name=self.workflow.name,
            topological_order=order,
            waves=waves,
            max_parallelism=max_width,
        )

    def failed_upstream_deps(
        self,
        task_name: str,
        results: Dict[str, TaskResult],
    ) -> List[str]:
        """Return upstream task names whose status blocks default downstream execution."""
        upstream_names = self.graph.get_upstream(task_name)
        return [
            dep
            for dep in upstream_names
            if dep in results
            and results[dep].status not in (TaskStatus.SUCCESS, TaskStatus.CACHED)
        ]

    def has_any_failure(self, results: Dict[str, TaskResult]) -> bool:
        """Return True if any completed task in `results` has failed."""
        return any(r.status == TaskStatus.FAILED for r in results.values())
