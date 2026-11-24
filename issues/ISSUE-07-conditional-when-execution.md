# ISSUE-07: Add conditional task execution (`when:` directive)

- **Type:** Feature Request (Multi-Module Feature)
- **Difficulty:** Hard
- **Labels:** `enhancement`, `architecture`, `models`, `parser`, `runner`

## Description

Production pipelines often need conditional steps—for example, running an alert **only on failure**, running cleanup **always**, or running deploy **only when an upstream task returns a specific value**.

Implement a `when:` directive across **3 core modules** (`models.py`, `parser.py`, `runner.py`).

## Specification (3 Files Involved)

### 1. Data Model (`src/taskflow/models.py`)
- Add `when: Optional[str] = None` to `TaskSpec`.

### 2. Parser (`src/taskflow/parser.py`)
- In `parse_workflow()`, accept `when: <expression>` inside any `task <name>:` block and pass `when=current_fields.get("when")` into `TaskSpec(...)`.
- In `parse_workflow_file()` (`.json` branch), load `when=item.get("when")`.

### 3. Execution Semantics (`src/taskflow/runner.py` — `TaskRunner._run_single_task`)
Support these 3 `when` forms (in addition to default `when is None`):
- **`when is None` (default):** Existing behavior—skip if any direct upstream dependency did not succeed/cache.
- **`when == "always"`:** Run the task even if one or more upstream dependencies failed or were skipped (pass their `output`—`None` if failed/skipped—in `upstream_outputs`).
- **`when == "on_failure"`:** Run **only** if at least one direct upstream dependency has status `TaskStatus.FAILED`. Otherwise mark the task `TaskStatus.SKIPPED`.
- **`when == "upstream.<dep_name> == <value>"`:**
  - If any direct upstream dependency failed or was skipped, mark `TaskStatus.SKIPPED`.
  - Otherwise compare `results[<dep_name>].output` with `_coerce_value(<value>)`. Run only if equal; otherwise mark `TaskStatus.SKIPPED`.
- Note: A `SKIPPED` task does **not** make `ExecutionReport.succeeded` False.

## Example `.tfw`

```text
workflow: cond_run

task step_a:
  command: maybe_fail

task deploy:
  command: tag
  depends_on: step_a
  when: upstream.step_a == green
  param val=matched

task alert:
  command: tag
  depends_on: step_a
  when: on_failure
  param val=handled_fail

task cleanup:
  command: tag
  depends_on: step_a
  when: always
  param val=cleaned
```
