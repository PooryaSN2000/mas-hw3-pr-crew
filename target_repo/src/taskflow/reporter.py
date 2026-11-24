"""Formatting and summary utilities for ExecutionReport objects."""

from __future__ import annotations

from typing import Any, Dict, List

from taskflow.models import ExecutionReport, TaskStatus


def compute_stats(report: ExecutionReport) -> Dict[str, Any]:
    """Compute aggregate execution counts and overall status."""
    counts: Dict[str, int] = {status.value: 0 for status in TaskStatus}
    for result in report.results.values():
        counts[result.status.value] = counts.get(result.status.value, 0) + 1

    return {
        "workflow": report.workflow_name,
        "total_tasks": len(report.execution_order),
        "succeeded": report.succeeded,
        "dry_run": report.dry_run,
        "counts": counts,
        "total_duration_ms": round(report.total_duration_ms, 2),
    }


def format_text(report: ExecutionReport) -> str:
    """Render an ExecutionReport as a clean human-readable table."""
    stats = compute_stats(report)
    mode = " [DRY RUN]" if report.dry_run else ""
    lines: List[str] = [
        f"Workflow: {report.workflow_name}{mode}",
        f"Status: {'PASSED' if report.succeeded else 'FAILED'} "
        f"({stats['total_tasks']} tasks, {stats['total_duration_ms']:.2f} ms)",
        "-" * 68,
        f"{'TASK':<20} {'STATUS':<10} {'ATTEMPTS':<10} {'DETAILS'}",
        "-" * 68,
    ]

    for task_name in report.execution_order:
        res = report.results[task_name]
        detail = res.error if res.error else repr(res.output)
        lines.append(
            f"{task_name:<20} {res.status.value:<10} {res.attempts:<10} {detail}"
        )

    lines.append("-" * 68)
    return "\n".join(lines)


def format_markdown(report: ExecutionReport) -> str:
    """Render an ExecutionReport as a Markdown table."""
    stats = compute_stats(report)
    mode = " (DRY RUN)" if report.dry_run else ""
    lines: List[str] = [
        f"### Workflow: `{report.workflow_name}`{mode}",
        "",
        f"- **Status:** {'PASSED' if report.succeeded else 'FAILED'}",
        f"- **Tasks:** {stats['total_tasks']} | **Duration:** {stats['total_duration_ms']:.2f} ms",
        "",
        "| Task | Status | Attempts | From Cache | Details |",
        "| :--- | :--- | ---: | :--- | :--- |",
    ]
    for task_name in report.execution_order:
        res = report.results[task_name]
        detail = (res.error if res.error else repr(res.output)).replace("|", "\\|")
        lines.append(
            f"| `{task_name}` | `{res.status.value}` | {res.attempts} | {res.from_cache} | {detail} |"
        )
    return "\n".join(lines)


def format_report(report: ExecutionReport, fmt: str = "text") -> str:
    """Format an ExecutionReport in the requested output format."""
    if fmt == "text":
        return format_text(report)
    if fmt == "markdown":
        return format_markdown(report)
    raise ValueError(
        f"Unsupported report format: '{fmt}'. Supported: 'text', 'markdown'."
    )
