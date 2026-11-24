# ISSUE-04: `workflows/release_audit.tfw` crashes immediately on `validate` and `run`

- **Type:** Bug (User Report — Investigation Required)
- **Difficulty:** Medium
- **Labels:** `bug`, `user-report`, `graph`

## User Report

Hi team,

I put together a release readiness pipeline in `workflows/release_audit.tfw` where multiple checks branch off `fetch_code` and later merge into `merge_checks`, `compliance_report`, and `release_gate`.

Every task only depends on earlier stages—there is **no circular dependency** anywhere. Yet running:

```bash
PYTHONPATH=src python -m taskflow.cli validate workflows/release_audit.tfw
PYTHONPATH=src python -m taskflow.cli run workflows/release_audit.tfw
```

immediately fails with:

```text
[ERROR] CYCLE_DETECTED: Cycle detected involving task 'run_unit_tests' -> 'compliance_report'.
```
(or `CycleDetectedError` when running `WorkflowGraph(wf).topological_sort()`).

## Expected Behavior

- Converging / diamond DAGs (including `workflows/release_audit.tfw` and nested diamonds) MUST validate and run without false cycle errors.
- Genuine circular dependencies (2-node cycles, 3-node cycles, or cycles attached to a valid branch) MUST still raise `CycleDetectedError`.
