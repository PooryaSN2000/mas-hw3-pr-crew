"""Public unit tests for TaskRunner, hooks, and metrics."""

from taskflow.hooks import AuditLogHook, HookManager, TimingHook
from taskflow.models import TaskSpec, TaskStatus, Workflow, WorkflowConfig
from taskflow.runner import TaskRunner


def test_runner_executes_pipeline_and_passes_upstream():
    registry = {
        "produce": lambda params, up: params["n"] * 2,
        "add_ten": lambda params, up: up["step1"] + 10,
    }
    wf = Workflow(name="math")
    wf.add_task(TaskSpec(name="step1", command="produce", params={"n": 5}))
    wf.add_task(TaskSpec(name="step2", command="add_ten", depends_on=["step1"]))

    hooks = HookManager()
    audit = AuditLogHook()
    timing = TimingHook()
    hooks.subscribe_all(audit)
    hooks.subscribe_all(timing)

    report = TaskRunner(registry=registry, hooks=hooks).run(wf)

    assert report.succeeded is True
    assert report.results["step1"].output == 10
    assert report.results["step2"].output == 20
    assert report.metrics["succeeded_tasks"] == 2
    assert len(audit.events_for_task("step1")) >= 2
    assert "step1" in timing.durations_ms


def test_runner_skips_downstream_when_upstream_fails():
    def boom(params, up):
        raise RuntimeError("database offline")

    registry = {
        "boom": boom,
        "after": lambda params, up: "should not run",
    }
    wf = Workflow(name="fail_chain")
    wf.add_task(TaskSpec(name="step1", command="boom", max_retries=0))
    wf.add_task(TaskSpec(name="step2", command="after", depends_on=["step1"]))

    report = TaskRunner(registry=registry).run(wf)

    assert report.succeeded is False
    assert report.results["step1"].status == TaskStatus.FAILED
    assert report.results["step1"].attempts == 1
    assert report.results["step2"].status == TaskStatus.SKIPPED


def test_runner_succeeds_first_attempt_with_retries_configured():
    registry = {"ok": lambda params, up: "done"}
    wf = Workflow(name="ok_retry")
    wf.add_task(TaskSpec(name="step1", command="ok", max_retries=2))

    report = TaskRunner(registry=registry).run(wf)
    assert report.succeeded is True
    assert report.results["step1"].attempts == 1


def test_sequential_fail_fast_stops_subsequent_tasks():
    ran = []

    def fail_op(params, up):
        ran.append("a")
        raise RuntimeError("boom")

    def ok_op(params, up):
        ran.append("b")
        return "ok"

    wf = Workflow(name="ff_seq")
    wf.add_task(TaskSpec(name="a_first", command="fail"))
    wf.add_task(TaskSpec(name="b_second", command="ok"))

    cfg = WorkflowConfig(max_workers=1, fail_fast=True)
    report = TaskRunner(registry={"fail": fail_op, "ok": ok_op}, config=cfg).run(wf)

    assert ran == ["a"]
    assert report.results["a_first"].status == TaskStatus.FAILED
    assert report.results["b_second"].status == TaskStatus.SKIPPED
