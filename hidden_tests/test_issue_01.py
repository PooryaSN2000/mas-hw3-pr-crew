"""Hidden evaluation tests for ISSUE-01 (Retry off-by-one bug)."""

from taskflow.hooks import AuditLogHook, HookEvent, HookManager
from taskflow.models import TaskSpec, TaskStatus, Workflow
from taskflow.runner import TaskRunner


def test_retries_exact_count_before_success():
    calls = 0

    def flaky(params, up):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ConnectionError(f"transient failure #{calls}")
        return "recovered"

    hooks = HookManager()
    audit = AuditLogHook()
    hooks.subscribe(HookEvent.ON_RETRY, audit)

    wf = Workflow(name="retry_success")
    wf.add_task(TaskSpec(name="flaky", command="flaky", max_retries=2))

    report = TaskRunner(registry={"flaky": flaky}, hooks=hooks).run(wf)
    assert report.succeeded is True
    assert report.results["flaky"].status == TaskStatus.SUCCESS
    assert report.results["flaky"].output == "recovered"
    assert report.results["flaky"].attempts == 3
    assert calls == 3
    assert len(audit.events) == 2


def test_retries_exhausted_attempts_count():
    calls = 0

    def always_fail(params, up):
        nonlocal calls
        calls += 1
        raise ValueError("permanent failure")

    wf = Workflow(name="retry_fail")
    wf.add_task(TaskSpec(name="bad", command="bad", max_retries=1))

    report = TaskRunner(registry={"bad": always_fail}).run(wf)
    assert report.succeeded is False
    assert report.results["bad"].status == TaskStatus.FAILED
    assert report.results["bad"].attempts == 2
    assert calls == 2
