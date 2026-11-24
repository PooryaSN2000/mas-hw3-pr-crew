"""Workflow execution engine with retries, caching, hooks, metrics, and parallel waves."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from typing import Any, Callable, Dict, List, Optional

from taskflow.cache import ResultCache
from taskflow.hooks import HookEvent, HookManager
from taskflow.metrics import MetricsCollector
from taskflow.models import (
    ExecutionReport,
    TaskResult,
    TaskSpec,
    TaskStatus,
    Workflow,
    WorkflowConfig,
)
from taskflow.scheduler import ExecutionScheduler

TaskHandler = Callable[[Dict[str, Any], Dict[str, Any]], Any]


class TaskRunner:
    """Executes all tasks in a Workflow according to topological dependencies."""

    def __init__(
        self,
        registry: Dict[str, TaskHandler],
        cache: Optional[ResultCache] = None,
        config: Optional[WorkflowConfig] = None,
        hooks: Optional[HookManager] = None,
    ) -> None:
        self.registry = dict(registry)
        self.config = config if config is not None else WorkflowConfig()
        self.cache = cache
        self.hooks = hooks if hooks is not None else HookManager(strict=self.config.strict_hooks)

    def register(self, command_name: str, handler: TaskHandler) -> None:
        """Register a callable handler for a command name."""
        self.registry[command_name] = handler

    def _execute_with_retries(
        self,
        task: TaskSpec,
        upstream_outputs: Dict[str, Any],
    ) -> TaskResult:
        """Invoke a task handler with configured retry behavior."""
        handler = self.registry.get(task.command)
        if handler is None:
            return TaskResult(
                task_name=task.name,
                status=TaskStatus.FAILED,
                error=f"No registered handler for command '{task.command}'.",
                attempts=0,
            )

        start = time.perf_counter()
        last_error: Optional[str] = None
        retries = task.max_retries if task.max_retries > 0 else self.config.default_retries
        max_attempts = max(1, retries)

        for attempt in range(1, max_attempts + 1):
            try:
                output = handler(dict(task.params), dict(upstream_outputs))
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                return TaskResult(
                    task_name=task.name,
                    status=TaskStatus.SUCCESS,
                    output=output,
                    attempts=attempt,
                    duration_ms=elapsed_ms,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt < max_attempts:
                    self.hooks.emit(
                        HookEvent.ON_RETRY,
                        {
                            "task_name": task.name,
                            "attempt": attempt,
                            "error": last_error,
                        },
                    )

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.hooks.emit(
            HookEvent.ON_ERROR,
            {"task_name": task.name, "error": last_error, "attempts": max_attempts},
        )
        return TaskResult(
            task_name=task.name,
            status=TaskStatus.FAILED,
            error=last_error,
            attempts=max_attempts,
            duration_ms=elapsed_ms,
        )

    def _run_single_task(
        self,
        task: TaskSpec,
        upstream_names: List[str],
        results: Dict[str, TaskResult],
    ) -> TaskResult:
        """Execute, cache-hit, or skip a single task node."""
        failed_deps = [
            dep
            for dep in upstream_names
            if results[dep].status not in (TaskStatus.SUCCESS, TaskStatus.CACHED)
        ]
        if failed_deps:
            return TaskResult(
                task_name=task.name,
                status=TaskStatus.SKIPPED,
                error=f"Skipped due to upstream failure: {', '.join(failed_deps)}",
                attempts=0,
            )

        upstream_outputs = {dep: results[dep].output for dep in upstream_names}

        self.hooks.emit(
            HookEvent.BEFORE_TASK,
            {"task_name": task.name, "command": task.command},
        )

        cache_key: Optional[str] = None
        if self.cache is not None and self.config.enable_cache and task.cacheable:
            cache_key = self.cache.compute_key(task)
            if self.cache.has(cache_key):
                cached_val = self.cache.get(cache_key)
                self.hooks.emit(
                    HookEvent.ON_CACHE_HIT,
                    {"task_name": task.name, "cache_key": cache_key},
                )
                result = TaskResult(
                    task_name=task.name,
                    status=TaskStatus.CACHED,
                    output=cached_val,
                    attempts=0,
                    duration_ms=0.0,
                    from_cache=True,
                )
                self.hooks.emit(
                    HookEvent.AFTER_TASK,
                    {"task_name": task.name, "status": result.status.value},
                )
                return result

        result = self._execute_with_retries(task, upstream_outputs)

        if (
            result.status == TaskStatus.SUCCESS
            and self.cache is not None
            and self.config.enable_cache
            and task.cacheable
            and cache_key is not None
        ):
            self.cache.set(cache_key, result.output)

        self.hooks.emit(
            HookEvent.AFTER_TASK,
            {"task_name": task.name, "status": result.status.value},
        )
        return result

    def run(self, workflow: Workflow) -> ExecutionReport:
        """Validate and execute a workflow end-to-end."""
        workflow_start = time.perf_counter()
        scheduler = ExecutionScheduler(workflow)
        plan = scheduler.build_plan()
        graph = scheduler.graph
        collector = MetricsCollector(workflow.name)

        self.hooks.emit(
            HookEvent.BEFORE_WORKFLOW,
            {"workflow_name": workflow.name, "task_count": len(plan.topological_order)},
        )

        results: Dict[str, TaskResult] = {}
        recorded_order: List[str] = []

        if self.config.max_workers > 1:
            for wave in plan.waves:
                with ThreadPoolExecutor(max_workers=self.config.max_workers) as pool:
                    future_map = {
                        pool.submit(
                            self._run_single_task,
                            workflow.get_task(name),
                            graph.get_upstream(name),
                            results,
                        ): name
                        for name in wave
                    }
                    for fut in as_completed(future_map):
                        name = future_map[fut]
                        res = fut.result()
                        results[name] = res
                        recorded_order.append(name)
                        collector.record(res)
        else:
            for task_name in plan.topological_order:
                if self.config.fail_fast and scheduler.has_any_failure(results):
                    res = TaskResult(
                        task_name=task_name,
                        status=TaskStatus.SKIPPED,
                        error="Skipped due to fail_fast after earlier failure.",
                        attempts=0,
                    )
                else:
                    task = workflow.get_task(task_name)
                    res = self._run_single_task(task, graph.get_upstream(task_name), results)
                results[task_name] = res
                recorded_order.append(task_name)
                collector.record(res)

        total_ms = (time.perf_counter() - workflow_start) * 1000.0
        run_metrics = collector.finalize(total_ms)

        self.hooks.emit(
            HookEvent.AFTER_WORKFLOW,
            {
                "workflow_name": workflow.name,
                "succeeded": run_metrics.failed_tasks == 0,
                "duration_ms": round(total_ms, 3),
            },
        )

        return ExecutionReport(
            workflow_name=workflow.name,
            results=results,
            execution_order=recorded_order,
            total_duration_ms=total_ms,
            dry_run=False,
            metrics=run_metrics.to_dict(),
        )
