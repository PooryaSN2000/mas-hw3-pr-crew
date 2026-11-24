"""Hidden evaluation tests for ISSUE-06 (Parallel execution, state isolation & fail_fast)."""

import time

from taskflow.cache import ResultCache
from taskflow.hooks import AuditLogHook, HookManager
from taskflow.models import TaskSpec, TaskStatus, Workflow, WorkflowConfig
from taskflow.runner import TaskRunner


def test_nested_upstream_and_param_mutation_is_isolated():
    def produce(params, up):
        return {"items": [1, 2], "meta": {"ok": True}}

    def mutator(params, up):
        up["src"]["items"].append(999)
        up["src"]["meta"]["ok"] = False
        params["cfg"]["nested"].append("dirty")
        return len(up["src"]["items"])

    def reader(params, up):
        return (list(up["src"]["items"]), up["src"]["meta"]["ok"])

    shared_param_cfg = {"nested": ["clean"]}
    wf = Workflow(name="iso_test")
    wf.add_task(TaskSpec(name="src", command="produce", cacheable=True))
    wf.add_task(
        TaskSpec(
            name="a_mutator",
            command="mutator",
            depends_on=["src"],
            params={"cfg": shared_param_cfg},
        )
    )
    wf.add_task(TaskSpec(name="b_reader", command="reader", depends_on=["src"]))

    cache = ResultCache()
    runner = TaskRunner(
        registry={"produce": produce, "mutator": mutator, "reader": reader},
        cache=cache,
        config=WorkflowConfig(max_workers=1),
    )
    report = runner.run(wf)

    assert report.succeeded is True
    assert report.results["src"].output == {"items": [1, 2], "meta": {"ok": True}}
    assert report.results["b_reader"].output == ([1, 2], True)
    assert shared_param_cfg == {"nested": ["clean"]}


def test_parallel_execution_preserves_deterministic_order_and_hooks():
    def slow_first(params, up):
        time.sleep(0.06)
        return "slow"

    def fast_second(params, up):
        return "fast"

    wf = Workflow(name="par_order")
    wf.add_task(TaskSpec(name="a_slow", command="slow"))
    wf.add_task(TaskSpec(name="b_fast", command="fast"))
    wf.add_task(TaskSpec(name="c_fast", command="fast"))

    hooks = HookManager()
    audit = AuditLogHook()
    hooks.subscribe_all(audit)

    cfg = WorkflowConfig(max_workers=3)
    report = TaskRunner(
        registry={"slow": slow_first, "fast": fast_second},
        cache=ResultCache(),
        config=cfg,
        hooks=hooks,
    ).run(wf)

    assert report.succeeded is True
    # Even though b_fast and c_fast finish before a_slow, execution_order must stay topological!
    assert report.execution_order == ["a_slow", "b_fast", "c_fast"]
    assert len(audit.events_for_task("a_slow")) >= 2
    assert len(audit.events_for_task("b_fast")) >= 2


def test_parallel_fail_fast_skips_subsequent_waves():
    ran = []

    def fail_wave1(params, up):
        ran.append("fail1")
        raise RuntimeError("boom")

    def ok_wave1(params, up):
        ran.append("ok1")
        return "ok"

    def wave2_independent(params, up):
        ran.append("wave2_independent")
        return "should_not_run"

    wf = Workflow(name="par_fail_fast")
    wf.add_task(TaskSpec(name="t1_fail", command="fail1"))
    wf.add_task(TaskSpec(name="t2_ok", command="ok1"))
    # Depends only on t2_ok (which succeeded!), so without fail_fast it WOULD run in wave 2
    wf.add_task(TaskSpec(name="t3_wave2", command="wave2", depends_on=["t2_ok"]))

    cfg = WorkflowConfig(max_workers=2, fail_fast=True)
    report = TaskRunner(
        registry={"fail1": fail_wave1, "ok1": ok_wave1, "wave2": wave2_independent},
        config=cfg,
    ).run(wf)

    assert report.succeeded is False
    assert report.results["t1_fail"].status == TaskStatus.FAILED
    assert report.results["t3_wave2"].status == TaskStatus.SKIPPED
    assert "wave2_independent" not in ran
