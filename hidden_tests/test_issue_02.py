"""Hidden evaluation tests for ISSUE-02 (Cache invalidation on params & upstream outputs)."""

from taskflow.cache import ResultCache
from taskflow.models import TaskSpec, TaskStatus, Workflow
from taskflow.runner import TaskRunner


def test_cache_key_sensitive_to_params_but_order_independent():
    cache = ResultCache()
    t1 = TaskSpec(name="op", command="calc", params={"a": 1, "b": 2})
    t2 = TaskSpec(name="op", command="calc", params={"b": 2, "a": 1})
    t3 = TaskSpec(name="op", command="calc", params={"a": 1, "b": 99})

    assert cache.compute_key(t1) == cache.compute_key(t2)
    assert cache.compute_key(t1) != cache.compute_key(t3)


def test_runner_invalidates_cache_when_params_change():
    calls = 0

    def scale(params, up):
        nonlocal calls
        calls += 1
        return params["x"] * 10

    cache = ResultCache()
    runner = TaskRunner(registry={"scale": scale}, cache=cache)

    wf1 = Workflow(name="p1")
    wf1.add_task(TaskSpec(name="job", command="scale", params={"x": 2}, cacheable=True))
    r1 = runner.run(wf1)

    wf2 = Workflow(name="p2")
    wf2.add_task(TaskSpec(name="job", command="scale", params={"x": 5}, cacheable=True))
    r2 = runner.run(wf2)

    assert r1.results["job"].output == 20
    assert r2.results["job"].output == 50
    assert r2.results["job"].status == TaskStatus.SUCCESS
    assert calls == 2


def test_runner_invalidates_downstream_when_upstream_output_changes():
    upstream_val = {"v": 100}
    downstream_calls = 0

    def src(params, up):
        return upstream_val["v"]

    def sink(params, up):
        nonlocal downstream_calls
        downstream_calls += 1
        return up["src"] + 1

    cache = ResultCache()
    runner = TaskRunner(registry={"src": src, "sink": sink}, cache=cache)

    wf = Workflow(name="upstream_invalidation")
    wf.add_task(TaskSpec(name="src", command="src", cacheable=False))
    wf.add_task(TaskSpec(name="sink", command="sink", depends_on=["src"], cacheable=True))

    r1 = runner.run(wf)
    assert r1.results["sink"].output == 101
    assert downstream_calls == 1

    r2 = runner.run(wf)
    assert r2.results["sink"].status == TaskStatus.CACHED
    assert r2.results["sink"].output == 101
    assert downstream_calls == 1

    upstream_val["v"] = 200
    r3 = runner.run(wf)
    assert r3.results["sink"].status == TaskStatus.SUCCESS
    assert r3.results["sink"].output == 201
    assert downstream_calls == 2
