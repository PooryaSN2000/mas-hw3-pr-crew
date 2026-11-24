# ISSUE-03: Add `--dry-run` mode and JSON report output (`--format json`)

- **Type:** Feature Request
- **Difficulty:** Medium
- **Labels:** `enhancement`, `cli`, `reporter`, `runner`

## Description

Before running expensive workflows in CI, users want to preview the execution plan without running handlers (`--dry-run`) and export structured JSON reports (`--format json`).

## Acceptance Criteria (3 Files Involved)

1. **`src/taskflow/runner.py` (`TaskRunner.run`):**
   - Update signature to `def run(self, workflow: Workflow, dry_run: bool = False) -> ExecutionReport:`.
   - When `dry_run=True`:
     - Build the execution plan normally (so cycles/missing dependencies still raise errors).
     - Do **NOT** invoke any task handler callables.
     - Record each task in `plan.topological_order` with `TaskStatus.PENDING`, `output=None`, `attempts=0`, `from_cache=False`.
     - Return `ExecutionReport(..., execution_order=list(plan.topological_order), dry_run=True)`.
2. **`src/taskflow/reporter.py` (`format_json` & `format_report`):**
   - Add `format_json(report: ExecutionReport) -> str` and support `fmt="json"` in `format_report(report, fmt=...)`.
   - Return valid JSON with keys:
     ```json
     {
       "workflow_name": "...",
       "dry_run": false,
       "succeeded": true,
       "execution_order": ["a"],
       "summary": {},
       "tasks": {
         "a": {"status": "success", "attempts": 1, "from_cache": false, "output": 42, "error": null}
       }
     }
     ```
     where `"summary"` is `compute_stats(report)`.
3. **`src/taskflow/cli.py` (`main` & `_handle_run`):**
   - Add `--dry-run` (`action="store_true"`) to `taskflow run` and pass `dry_run=args.dry_run` to `runner.run(...)`.
   - Extend `--format` choices to `["text", "markdown", "json"]`.
