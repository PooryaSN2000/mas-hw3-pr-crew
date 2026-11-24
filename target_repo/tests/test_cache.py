"""Public unit tests for ResultCache and basic caching integration."""

from taskflow.cache import ResultCache
from taskflow.models import TaskSpec, TaskStatus, Workflow
from taskflow.runner import TaskRunner


def test_cache_set_get_invalidate_and_clear(tmp_path):
    cache = ResultCache(cache_dir=tmp_path)
    task = TaskSpec(name="step1", command="echo")
    key = cache.compute_key(task)

    assert not cache.has(key)
    cache.set(key, {"value": 42})
    assert cache.has(key)
    assert cache.get(key) == {"value": 42}

    cache2 = ResultCache(cache_dir=tmp_path)
    assert cache2.has(key)
    assert cache2.get(key) == {"value": 42}
    assert cache2.stats()["hits"] == 1

    assert cache2.invalidate(key) is True
    assert not cache2.has(key)

    cache2.set(key, {"value": 99})
    cache2.clear()
    assert not cache2.has(key)


def test_repeated_run_uses_cache():
    call_count = 0

    def compute(params, upstream):
        nonlocal call_count
        call_count += 1
        return "computed_result"

    wf = Workflow(name="cache_demo")
    wf.add_task(TaskSpec(name="job", command="compute", cacheable=True))

    cache = ResultCache()
    runner = TaskRunner(registry={"compute": compute}, cache=cache)

    report1 = runner.run(wf)
    report2 = runner.run(wf)

    assert call_count == 1
    assert report1.results["job"].status == TaskStatus.SUCCESS
    assert report2.results["job"].status == TaskStatus.CACHED
    assert report2.results["job"].from_cache is True
    assert report2.results["job"].output == "computed_result"
