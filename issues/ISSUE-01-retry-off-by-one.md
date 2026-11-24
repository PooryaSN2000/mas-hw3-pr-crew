# ISSUE-01: `max_retries` runs one fewer attempt than configured

- **Type:** Bug (Straightforward)
- **Difficulty:** Easy (Ideal for validating your Base Camp setup)
- **Labels:** `bug`, `good-first-issue`, `runner`

## Description

When a task is configured with `max_retries=N`, the semantic contract of `max_retries` is:
- 1 initial attempt, **plus** up to `N` retries upon failure (i.e., `N + 1` total attempts).

Currently, in `src/taskflow/runner.py` inside `TaskRunner._execute_with_retries`:
- Setting `max_retries=1` only executes **1 attempt total** (never retries!).
- Setting `max_retries=2` only executes **2 attempts total** instead of 3.

## Steps to Reproduce

Create a task handler that fails on its first 2 calls and succeeds on its 3rd call, and configure `TaskSpec(name="flaky", command="flaky", max_retries=2)`.
Running the workflow currently fails after 2 attempts instead of succeeding on attempt 3.

## Expected Behavior

- `max_retries=0` -> 1 total attempt
- `max_retries=1` -> up to 2 total attempts
- `max_retries=2` -> up to 3 total attempts
- `TaskResult.attempts` accurately reflects the number of attempts performed, and `HookEvent.ON_RETRY` is emitted before each retry attempt.
