"""Static structural and semantic validator for TaskFlow workflows."""

from __future__ import annotations

import re
from typing import Iterable, Optional, Set

from taskflow.graph import WorkflowGraph
from taskflow.models import (
    CycleDetectedError,
    MissingDependencyError,
    ValidationError,
    ValidationIssue,
    ValidationReport,
    Workflow,
)

TASK_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
MAX_RECOMMENDED_RETRIES = 10


class WorkflowValidator:
    """Performs pre-flight structural and semantic validation on a Workflow."""

    def __init__(self, known_commands: Optional[Iterable[str]] = None) -> None:
        self.known_commands: Optional[Set[str]] = (
            set(known_commands) if known_commands is not None else None
        )

    def validate(self, workflow: Workflow, raise_on_error: bool = False) -> ValidationReport:
        """Validate `workflow` and return a ValidationReport."""
        report = ValidationReport(workflow_name=workflow.name)

        if not workflow.name or not workflow.name.strip():
            report.issues.append(
                ValidationIssue(
                    severity="error",
                    code="EMPTY_WORKFLOW_NAME",
                    message="Workflow name must not be empty.",
                )
            )

        if not workflow.tasks:
            report.issues.append(
                ValidationIssue(
                    severity="warning",
                    code="EMPTY_WORKFLOW",
                    message="Workflow contains no tasks.",
                )
            )
            return report

        for task_name, spec in sorted(workflow.tasks.items()):
            if not TASK_NAME_RE.match(task_name):
                report.issues.append(
                    ValidationIssue(
                        severity="error",
                        code="INVALID_TASK_NAME",
                        message=(
                            f"Task name '{task_name}' must start with a letter and "
                            "contain only alphanumeric characters, '_' or '-'."
                        ),
                        task_name=task_name,
                    )
                )

            if task_name in spec.depends_on:
                report.issues.append(
                    ValidationIssue(
                        severity="error",
                        code="SELF_DEPENDENCY",
                        message=f"Task '{task_name}' cannot depend on itself.",
                        task_name=task_name,
                    )
                )

            if self.known_commands is not None and spec.command not in self.known_commands:
                report.issues.append(
                    ValidationIssue(
                        severity="error",
                        code="UNKNOWN_COMMAND",
                        message=f"Task '{task_name}' uses unregistered command '{spec.command}'.",
                        task_name=task_name,
                    )
                )

            if spec.max_retries > MAX_RECOMMENDED_RETRIES:
                report.issues.append(
                    ValidationIssue(
                        severity="warning",
                        code="EXCESSIVE_RETRIES",
                        message=(
                            f"Task '{task_name}' configures {spec.max_retries} retries "
                            f"(recommended <= {MAX_RECOMMENDED_RETRIES})."
                        ),
                        task_name=task_name,
                    )
                )

        try:
            graph = WorkflowGraph(workflow)
            graph.topological_sort()
        except MissingDependencyError as exc:
            report.issues.append(
                ValidationIssue(
                    severity="error",
                    code="MISSING_DEPENDENCY",
                    message=str(exc),
                )
            )
        except CycleDetectedError as exc:
            report.issues.append(
                ValidationIssue(
                    severity="error",
                    code="CYCLE_DETECTED",
                    message=str(exc),
                )
            )

        if raise_on_error and not report.is_valid:
            summary = "; ".join(f"[{e.code}] {e.message}" for e in report.errors)
            raise ValidationError(f"Workflow '{workflow.name}' failed validation: {summary}")

        return report
