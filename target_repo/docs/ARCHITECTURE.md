# TaskFlow Architecture

TaskFlow is organized into small, focused modules under `src/taskflow/`:

| Module | Responsibility |
| :--- | :--- |
| `models.py` | Core dataclasses (`TaskSpec`, `TaskResult`, `Workflow`, `ExecutionReport`, `WorkflowConfig`, `ValidationIssue`) and exceptions. |
| `config.py` | Loading and merging `WorkflowConfig` from defaults, dictionaries, JSON files, or environment variables. |
| `parser.py` | Parsing `.tfw` DSL files and `.json` workflow definitions into `Workflow` instances. |
| `serializers.py` | Exporting `Workflow` and `ExecutionReport` objects to `.tfw`, dict, CSV, and Markdown formats. |
| `graph.py` | Directed dependency graph (`WorkflowGraph`), cycle detection, topological sorting, wave grouping, and DOT export. |
| `validators.py` | Static structural and semantic checks (`WorkflowValidator`) before execution. |
| `registry.py` | Command handler registry (`CommandRegistry`), aliases, and built-in demo commands. |
| `cache.py` | In-memory and disk-backed result caching (`ResultCache`) with hit/miss tracking. |
| `hooks.py` | Lifecycle event hooks (`HookManager`, `AuditLogHook`, `TimingHook`). |
| `metrics.py` | Execution telemetry aggregation (`MetricsCollector`, `RunMetrics`). |
| `scheduler.py` | Wave-based execution planning (`ExecutionScheduler`) and failure propagation policies. |
| `runner.py` | End-to-end execution engine (`TaskRunner`) supporting sequential and parallel wave execution, retries, and caching. |
| `reporter.py` | Human-readable report formatting (`format_text`, `format_markdown`, `format_report`). |
| `inspector.py` | Static analysis helpers (`explain_workflow`, `diff_workflows`, `find_impacted_tasks`). |
| `cli.py` | Command-line interface (`run`, `validate`, `inspect`, `graph`). |
