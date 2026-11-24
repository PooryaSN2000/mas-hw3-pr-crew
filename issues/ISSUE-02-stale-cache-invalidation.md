# ISSUE-02: Cache returns stale outputs when task params or upstream results change

- **Type:** Bug (Multi-File)
- **Difficulty:** Easy-Medium
- **Labels:** `bug`, `cache`, `runner`

## Description

When reusing a `ResultCache` across multiple runs of a workflow, `TaskRunner` returns **stale cached outputs** even when:
1. The task's `params` dictionary changed (e.g., `{"x": 2}` vs `{"x": 5}`), OR
2. An upstream dependency produced a different output than in the previous run.

## Requirements (2 Files Involved)

1. **`src/taskflow/cache.py` (`ResultCache.compute_key`):**
   - Include both `task.params` and `upstream_outputs` (serialized deterministically with `json.dumps(..., sort_keys=True, default=str)`) in the hashed payload.
   - Preserve key-order independence: `{"a": 1, "b": 2}` and `{"b": 2, "a": 1}` MUST yield the **same** cache key.
2. **`src/taskflow/runner.py` (`TaskRunner._run_single_task`):**
   - Pass `upstream_outputs` into `self.cache.compute_key(task, upstream_outputs=upstream_outputs)` instead of calling `compute_key(task)` alone.
- Keep existing caching working when neither `params` nor upstream outputs change.

## Minimal Reproduction

```python
from taskflow.cache import ResultCache
from taskflow.models import TaskSpec

cache = ResultCache()
t1 = TaskSpec(name="op", command="calc", params={"a": 1, "b": 2})
t2 = TaskSpec(name="op", command="calc", params={"b": 2, "a": 1})
t3 = TaskSpec(name="op", command="calc", params={"a": 1, "b": 99})
assert cache.compute_key(t1) == cache.compute_key(t2)
assert cache.compute_key(t1) != cache.compute_key(t3)  # Currently FAILS!
```
