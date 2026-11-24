"""Hidden evaluation tests for ISSUE-03 (Dry-run mode & JSON output format)."""

import json
from pathlib import Path

from taskflow.cache import ResultCache
from taskflow.cli import main
from taskflow.models import TaskSpec, TaskStatus, Workflow
from taskflow.reporter import format_report
from taskflow.runner import TaskRunner


def test_runner_dry_run_does_not_execute_handlers():
    executed = []

    def side_effect(params, up):
        executed.append(params.get("id"))
        return "ran"

    wf = Workflow(name="dry_test")
    wf.add_task(TaskSpec(name="a", command="run_it", params={"id": 1}))
    wf.add_task(TaskSpec(name="b", command="run_it", depends_on=["a"], params={"id": 2}))

    runner = TaskRunner(registry={"run_it": side_effect}, cache=ResultCache())
    report = runner.run(wf, dry_run=True)

    assert executed == []
    assert report.dry_run is True
    assert report.execution_order == ["a", "b"]
    assert report.results["a"].status == TaskStatus.PENDING
    assert report.results["b"].status == TaskStatus.PENDING


def test_format_report_json():
    wf = Workflow(name="json_test")
    wf.add_task(TaskSpec(name="a", command="ok"))
    runner = TaskRunner(registry={"ok": lambda p, u: 42})
    report = runner.run(wf)

    raw = format_report(report, fmt="json")
    data = json.loads(raw)

    assert data["workflow_name"] == "json_test"
    assert data["dry_run"] is False
    assert data["succeeded"] is True
    assert data["execution_order"] == ["a"]
    assert "summary" in data
    assert "a" in data["tasks"]
    assert data["tasks"]["a"]["status"] == "success"


def test_cli_dry_run_and_json_flag(capsys):
    demo_path = Path(__file__).resolve().parents[1] / "target_repo" / "workflows" / "demo.tfw"
    exit_code = main(["run", str(demo_path), "--dry-run", "--format", "json"])
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert exit_code == 0
    assert payload["workflow_name"] == "greeting_pipeline"
    assert payload["dry_run"] is True
    assert payload["execution_order"] == ["greet", "shout", "count"]
