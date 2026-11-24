"""Parser for TaskFlow (.tfw) and (.json) workflow definition files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from taskflow.models import TaskSpec, Workflow, WorkflowParseError


def _coerce_value(raw: str) -> Any:
    """Convert simple scalar strings into bool, int, float, or str."""
    val = raw.strip()
    lower = val.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


def parse_workflow(text: str) -> Workflow:
    """Parse a .tfw DSL string into a Workflow object."""
    workflow_name: Optional[str] = None
    tasks: Dict[str, TaskSpec] = {}
    metadata: Dict[str, Any] = {}

    current_task_name: Optional[str] = None
    current_fields: Dict[str, Any] = {}

    def flush_task() -> None:
        nonlocal current_task_name, current_fields
        if current_task_name is None:
            return
        if "command" not in current_fields:
            raise WorkflowParseError(
                f"Task '{current_task_name}' is missing required field 'command'."
            )
        spec = TaskSpec(
            name=current_task_name,
            command=str(current_fields["command"]),
            depends_on=list(current_fields.get("depends_on", [])),
            params=dict(current_fields.get("params", {})),
            max_retries=int(current_fields.get("retries", 0)),
            cacheable=bool(current_fields.get("cacheable", True)),
            tags=list(current_fields.get("tags", [])),
            timeout_s=current_fields.get("timeout_s"),
            description=str(current_fields.get("description", "")),
        )
        tasks[current_task_name] = spec
        current_task_name = None
        current_fields = {}

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("workflow:"):
            flush_task()
            workflow_name = stripped.split(":", 1)[1].strip()
            if not workflow_name:
                raise WorkflowParseError(f"Line {line_no}: workflow name cannot be empty.")
            continue

        if stripped.startswith("meta ") and current_task_name is None:
            assignment = stripped[len("meta ") :].strip()
            if "=" not in assignment:
                raise WorkflowParseError(
                    f"Line {line_no}: invalid meta syntax '{stripped}', expected 'meta key=value'."
                )
            key, val = assignment.split("=", 1)
            metadata[key.strip()] = _coerce_value(val)
            continue

        if stripped.startswith("task ") and stripped.endswith(":"):
            flush_task()
            name = stripped[len("task ") : -1].strip()
            if not name:
                raise WorkflowParseError(f"Line {line_no}: task name cannot be empty.")
            current_task_name = name
            current_fields = {"params": {}, "depends_on": [], "tags": []}
            continue

        if current_task_name is None:
            raise WorkflowParseError(
                f"Line {line_no}: unexpected directive outside task block: '{stripped}'"
            )

        if stripped.startswith("param "):
            assignment = stripped[len("param ") :].strip()
            if "=" not in assignment:
                raise WorkflowParseError(
                    f"Line {line_no}: invalid param syntax '{stripped}', expected 'param key=value'."
                )
            key, val = assignment.split("=", 1)
            current_fields["params"][key.strip()] = _coerce_value(val)
            continue

        if ":" not in stripped:
            raise WorkflowParseError(f"Line {line_no}: invalid field line '{stripped}'.")

        field_name, field_val = stripped.split(":", 1)
        field_name = field_name.strip()
        field_val = field_val.strip()

        if field_name == "command":
            current_fields["command"] = field_val
        elif field_name == "depends_on":
            deps: List[str] = [d.strip() for d in field_val.split(",") if d.strip()]
            current_fields["depends_on"].extend(deps)
        elif field_name == "tags":
            tags: List[str] = [t.strip() for t in field_val.split(",") if t.strip()]
            current_fields["tags"].extend(tags)
        elif field_name == "retries":
            try:
                current_fields["retries"] = int(field_val)
            except ValueError as exc:
                raise WorkflowParseError(
                    f"Line {line_no}: retries must be an integer, got '{field_val}'."
                ) from exc
        elif field_name == "timeout":
            try:
                current_fields["timeout_s"] = float(field_val)
            except ValueError as exc:
                raise WorkflowParseError(
                    f"Line {line_no}: timeout must be a number, got '{field_val}'."
                ) from exc
        elif field_name == "cacheable":
            current_fields["cacheable"] = bool(_coerce_value(field_val))
        elif field_name == "description":
            current_fields["description"] = field_val
        else:
            raise WorkflowParseError(
                f"Line {line_no}: unknown task attribute '{field_name}'."
            )

    flush_task()

    if not workflow_name:
        raise WorkflowParseError("Workflow definition must include a 'workflow:' header.")

    return Workflow(name=workflow_name, tasks=tasks, metadata=metadata)


def parse_workflow_file(path: Path | str) -> Workflow:
    """Load a workflow from a .tfw or .json file."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Workflow file not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    if file_path.suffix.lower() == ".json":
        data = json.loads(content)
        wf = Workflow(name=data["name"], metadata=data.get("metadata", {}))
        seen_names: set[str] = set()
        for item in data.get("tasks", []):
            name = item["name"]
            if name in seen_names:
                raise WorkflowParseError(f"Duplicate task name in JSON workflow: '{name}'.")
            seen_names.add(name)
            wf.add_task(
                TaskSpec(
                    name=name,
                    command=item["command"],
                    depends_on=item.get("depends_on", []),
                    params=item.get("params", {}),
                    max_retries=item.get("max_retries", 0),
                    cacheable=item.get("cacheable", True),
                    tags=item.get("tags", []),
                    timeout_s=item.get("timeout_s"),
                    description=item.get("description", ""),
                )
            )
        return wf

    return parse_workflow(content)
