"""Public unit tests for reporter, serializers, and CLI subcommands."""

from pathlib import Path

from taskflow.cli import main
from taskflow.models import ExecutionReport, TaskResult, TaskStatus
from taskflow.reporter import compute_stats, format_report
from taskflow.serializers import report_to_csv


def test_format_text_markdown_and_csv():
    report = ExecutionReport(
        workflow_name="demo",
        results={
            "a": TaskResult(task_name="a", status=TaskStatus.SUCCESS, output="hi", attempts=1)
        },
        execution_order=["a"],
        total_duration_ms=12.5,
    )
    text = format_report(report, fmt="text")
    assert "Workflow: demo" in text
    assert "PASSED" in text

    md = format_report(report, fmt="markdown")
    assert "| `a` | `success` |" in md

    csv_out = report_to_csv(report)
    assert "task_name,status,attempts" in csv_out
    assert "a,success,1,false" in csv_out

    stats = compute_stats(report)
    assert stats["total_tasks"] == 1
    assert stats["counts"]["success"] == 1


def test_cli_subcommands(capsys):
    demo_path = Path(__file__).resolve().parents[1] / "workflows" / "demo.tfw"
    etl_path = Path(__file__).resolve().parents[1] / "workflows" / "etl_pipeline.tfw"

    assert main(["run", str(demo_path)]) == 0
    out_run = capsys.readouterr().out
    assert "Workflow: greeting_pipeline" in out_run
    assert "PASSED" in out_run

    assert main(["validate", str(etl_path)]) == 0
    assert "VALID" in capsys.readouterr().out

    assert main(["inspect", str(etl_path)]) == 0
    assert "Waves:" in capsys.readouterr().out

    assert main(["graph", str(etl_path)]) == 0
    assert "digraph" in capsys.readouterr().out
