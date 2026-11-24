"""Static analysis and diff utilities for inspecting TaskFlow workflows."""

from __future__ import annotations

from typing import Any, Dict, List

from taskflow.graph import WorkflowGraph
from taskflow.models import Workflow


def explain_workflow(workflow: Workflow) -> Dict[str, Any]:
    """Produce a structural summary of a workflow (roots, leaves, waves, depth)."""
    graph = WorkflowGraph(workflow)
    order = graph.topological_sort()
    waves = graph.execution_levels()
    return {
        "workflow": workflow.name,
        "task_count": len(order),
        "roots": graph.get_roots(),
        "leaves": graph.get_leaves(),
        "waves": waves,
        "critical_path_depth": graph.critical_path_depth(),
        "topological_order": order,
    }


def find_impacted_tasks(workflow: Workflow, changed_task: str) -> List[str]:
    """Return sorted task names affected if `changed_task` changes (including itself)."""
    if changed_task not in workflow.tasks:
        raise KeyError(f"Unknown task: '{changed_task}'")
    graph = WorkflowGraph(workflow)
    impacted = graph.descendants(changed_task)
    impacted.add(changed_task)
    return sorted(impacted)


def diff_workflows(old: Workflow, new: Workflow) -> Dict[str, List[str]]:
    """Compare two versions of a workflow and categorize added, removed, and modified tasks."""
    old_names = set(old.tasks.keys())
    new_names = set(new.tasks.keys())

    added = sorted(new_names - old_names)
    removed = sorted(old_names - new_names)
    modified: List[str] = []

    for name in sorted(old_names & new_names):
        if old.tasks[name] != new.tasks[name]:
            modified.append(name)

    return {
        "added": added,
        "removed": removed,
        "modified": modified,
    }
