"""Command-line interface for running, validating, and inspecting TaskFlow workflows."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import List, Optional

from taskflow.cache import ResultCache
from taskflow.graph import WorkflowGraph
from taskflow.inspector import explain_workflow
from taskflow.models import WorkflowConfig
from taskflow.parser import parse_workflow_file
from taskflow.registry import build_default_registry
from taskflow.reporter import format_report
from taskflow.runner import TaskRunner
from taskflow.validators import WorkflowValidator


def _handle_run(args: argparse.Namespace) -> int:
    workflow = parse_workflow_file(args.workflow_file)
    cache = ResultCache(cache_dir=args.cache_dir) if args.cache_dir else ResultCache()
    config = WorkflowConfig(
        max_workers=args.workers,
        fail_fast=args.fail_fast,
        cache_dir=args.cache_dir,
    )
    runner = TaskRunner(
        registry=build_default_registry(),
        cache=cache,
        config=config,
    )
    report = runner.run(workflow)
    print(format_report(report, fmt=args.format))
    return 0 if report.succeeded else 1


def _handle_validate(args: argparse.Namespace) -> int:
    workflow = parse_workflow_file(args.workflow_file)
    registry = build_default_registry()
    validator = WorkflowValidator(known_commands=registry.keys())
    v_report = validator.validate(workflow)
    if v_report.is_valid:
        print(f"Workflow '{workflow.name}' is VALID ({len(workflow.tasks)} tasks).")
        for warn in v_report.warnings:
            print(f"  [WARN] {warn.code}: {warn.message}")
        return 0
    print(f"Workflow '{workflow.name}' is INVALID:")
    for err in v_report.errors:
        print(f"  [ERROR] {err.code}: {err.message}")
    return 1


def _handle_inspect(args: argparse.Namespace) -> int:
    workflow = parse_workflow_file(args.workflow_file)
    info = explain_workflow(workflow)
    print(f"Workflow: {info['workflow']} ({info['task_count']} tasks)")
    print(f"Roots:    {', '.join(info['roots'])}")
    print(f"Leaves:   {', '.join(info['leaves'])}")
    print(f"Depth:    {info['critical_path_depth']}")
    print("Waves:")
    for idx, wave in enumerate(info["waves"], start=1):
        print(f"  Wave {idx}: {', '.join(wave)}")
    return 0


def _handle_graph(args: argparse.Namespace) -> int:
    workflow = parse_workflow_file(args.workflow_file)
    graph = WorkflowGraph(workflow)
    print(graph.to_dot())
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint for TaskFlow."""
    parser = argparse.ArgumentParser(prog="taskflow", description="TaskFlow workflow engine CLI.")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    run_parser = subparsers.add_parser("run", help="Execute a workflow file.")
    run_parser.add_argument("workflow_file", type=Path, help="Path to a .tfw or .json workflow.")
    run_parser.add_argument(
        "--format",
        choices=["text", "markdown"],
        default="text",
        help="Output format for the execution report.",
    )
    run_parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Optional directory to persist cached task outputs.",
    )
    run_parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of concurrent worker threads per execution wave.",
    )
    run_parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop executing subsequent tasks after the first task failure.",
    )

    val_parser = subparsers.add_parser("validate", help="Validate a workflow file.")
    val_parser.add_argument("workflow_file", type=Path, help="Path to a .tfw or .json workflow.")

    insp_parser = subparsers.add_parser("inspect", help="Inspect workflow topology and waves.")
    insp_parser.add_argument("workflow_file", type=Path, help="Path to a .tfw or .json workflow.")

    graph_parser = subparsers.add_parser("graph", help="Export workflow DAG as Graphviz DOT.")
    graph_parser.add_argument("workflow_file", type=Path, help="Path to a .tfw or .json workflow.")

    args = parser.parse_args(argv)

    if args.subcommand == "run":
        return _handle_run(args)
    if args.subcommand == "validate":
        return _handle_validate(args)
    if args.subcommand == "inspect":
        return _handle_inspect(args)
    if args.subcommand == "graph":
        return _handle_graph(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
