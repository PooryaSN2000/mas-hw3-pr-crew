"""Hidden evaluation tests for ISSUE-04 (Converging / Diamond DAG false cycle detection)."""

from pathlib import Path
import pytest

from taskflow.cli import main
from taskflow.graph import WorkflowGraph
from taskflow.models import CycleDetectedError, TaskSpec, Workflow
from taskflow.parser import parse_workflow_file
from taskflow.runner import TaskRunner

TARGET_ROOT = Path(__file__).resolve().parents[1] / "target_repo"


def test_release_audit_workflow_validates_and_runs(capsys):
    audit_path = TARGET_ROOT / "workflows" / "release_audit.tfw"
    assert main(["validate", str(audit_path)]) == 0
    assert "VALID" in capsys.readouterr().out

    assert main(["run", str(audit_path)]) == 0
    out = capsys.readouterr().out
    assert "Workflow: release_audit" in out
    assert "PASSED" in out


def test_nested_diamonds_succeed():
    wf = Workflow(name="double_diamond")
    wf.add_task(TaskSpec(name="n0", command="echo"))
    wf.add_task(TaskSpec(name="n1", command="echo", depends_on=["n0"]))
    wf.add_task(TaskSpec(name="n2", command="echo", depends_on=["n0"]))
    wf.add_task(TaskSpec(name="n3", command="echo", depends_on=["n1", "n2"]))
    wf.add_task(TaskSpec(name="n4", command="echo", depends_on=["n3"]))
    wf.add_task(TaskSpec(name="n5", command="echo", depends_on=["n3"]))
    wf.add_task(TaskSpec(name="n6", command="echo", depends_on=["n4", "n5"]))

    order = WorkflowGraph(wf).topological_sort()
    assert order[0] == "n0"
    assert order[-1] == "n6"
    assert order.index("n3") < order.index("n4")
    assert order.index("n3") < order.index("n5")


def test_cycle_off_valid_branch_still_detected():
    wf = Workflow(name="branch_with_cycle")
    wf.add_task(TaskSpec(name="start", command="echo"))
    wf.add_task(TaskSpec(name="x", command="echo", depends_on=["start", "y"]))
    wf.add_task(TaskSpec(name="y", command="echo", depends_on=["x"]))

    with pytest.raises(CycleDetectedError):
        WorkflowGraph(wf).topological_sort()
