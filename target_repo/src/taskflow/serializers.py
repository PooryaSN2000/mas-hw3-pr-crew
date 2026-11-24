"""Serialization helpers for exporting workflows and execution reports."""

from __future__ import annotations

import csv
import io
from typing import Any, Dict, List

from taskflow.models import ExecutionReport, SerializationError, Workflow


def workflow_to_dict(workflow: Workflow) -> Dict[str, Any]:
    """Convert a Workflow into a plain JSON-serializable dictionary."""
    if not workflow.name:
        raise SerializationError("Cannot serialize a workflow with an empty name.")
    tasks_list: List[Dict[str, Any]] = []
    for name in sorted(workflow.tasks):
        spec = workflow.tasks[name]
        entry: Dict[str, Any] = {
            "name": spec.name,
            "command": spec.command,
            "depends_on": list(spec.depends_on),
            "params": dict(spec.params),
            "max_retries": spec.max_retries,
            "cacheable": spec.cacheable,
            "tags": list(spec.tags),
        }
        if spec.timeout_s is not None:
            entry["timeout_s"] = spec.timeout_s
        if spec.description:
            entry["description"] = spec.description
        tasks_list.append(entry)

    return {
        "name": workflow.name,
        "metadata": dict(workflow.metadata),
        "tasks": tasks_list,
    }


def workflow_to_tfw(workflow: Workflow) -> str:
    """Render a Workflow back into valid .tfw DSL text."""
    if not workflow.name:
        raise SerializationError("Cannot serialize a workflow with an empty name.")

    lines: List[str] = [f"workflow: {workflow.name}"]
    for key in sorted(workflow.metadata):
        lines.append(f"meta {key}={workflow.metadata[key]}")

    for name in sorted(workflow.tasks):
        spec = workflow.tasks[name]
        lines.append("")
        lines.append(f"task {spec.name}:")
        lines.append(f"  command: {spec.command}")
        if spec.depends_on:
            lines.append(f"  depends_on: {', '.join(spec.depends_on)}")
        if spec.max_retries:
            lines.append(f"  retries: {spec.max_retries}")
        if not spec.cacheable:
            lines.append("  cacheable: false")
        if spec.tags:
            lines.append(f"  tags: {', '.join(spec.tags)}")
        if spec.timeout_s is not None:
            lines.append(f"  timeout: {spec.timeout_s}")
        if spec.description:
            lines.append(f"  description: {spec.description}")
        for p_key in sorted(spec.params):
            val = spec.params[p_key]
            if isinstance(val, bool):
                val_str = "true" if val else "false"
            else:
                val_str = str(val)
            lines.append(f"  param {p_key}={val_str}")

    return "\n".join(lines) + "\n"


def report_to_csv(report: ExecutionReport) -> str:
    """Render an ExecutionReport as CSV rows."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["task_name", "status", "attempts", "from_cache", "duration_ms", "error"])
    for task_name in report.execution_order:
        res = report.results[task_name]
        writer.writerow(
            [
                task_name,
                res.status.value,
                res.attempts,
                str(res.from_cache).lower(),
                f"{res.duration_ms:.2f}",
                res.error or "",
            ]
        )
    return buf.getvalue()
