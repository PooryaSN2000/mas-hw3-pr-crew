# ISSUE-06: Parallel execution (`max_workers > 1`) breaks state isolation, `fail_fast`, and deterministic ordering

- **Type:** Bug (Concurrency & State Isolation)
- **Difficulty:** Medium-Hard
- **Labels:** `bug`, `concurrency`, `runner`, `cache`

## Description

When running workflows with `WorkflowConfig(max_workers > 1)` or with tasks that return nested dicts/lists, three reliability bugs occur across `src/taskflow/runner.py` and `src/taskflow/cache.py`:

1. **Nested state mutation leaks across tasks and cache:**
   - Currently `runner.py` uses shallow copies (`dict(task.params)`, `dict(upstream_outputs)`) and `cache.py` stores/returns direct object references.
   - If a task handler mutates a nested `dict` or `list` inside `params` or `upstream_outputs` (e.g., `upstream["src"]["items"].append(999)`), that mutation corrupts `TaskResult.output`, the cache entry, and sibling tasks.
2. **`fail_fast=True` is ignored across waves in parallel mode:**
   - In `TaskRunner.run()`, when `self.config.max_workers > 1` and `self.config.fail_fast` is True, if a failure occurred in wave 1, tasks in wave 2 still execute instead of being marked `TaskStatus.SKIPPED`.
3. **Non-deterministic `ExecutionReport.execution_order`:**
   - In parallel mode, `recorded_order` currently appends task names in random `as_completed` thread-finish order. It MUST preserve deterministic topological order (`plan.topological_order`).

## Acceptance Criteria (2 Files Involved)

- **`src/taskflow/runner.py`:**
  - Use `copy.deepcopy` for `task.params` and `upstream_outputs` passed into task handlers.
  - Before submitting each wave in parallel mode (`max_workers > 1`), if `self.config.fail_fast and scheduler.has_any_failure(results)`, mark all tasks in that wave as `TaskStatus.SKIPPED` without running them.
  - Set `execution_order` to deterministic topological order (`[n for n in plan.topological_order if n in results]`).
- **`src/taskflow/cache.py`:**
  - Guard `ResultCache` (`has`, `get`, `set`, `invalidate`, `clear`) with `threading.RLock` and use `copy.deepcopy` on `get`/`set` so cached nested objects cannot be mutated externally.
