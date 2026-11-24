"""Example 3: Build a lightweight code knowledge graph with Python's `ast` + `networkx`.

This is a starting point for Context Management and the `Cartographer` badge.
Run:
    python examples/03_code_graph.py
"""

from __future__ import annotations

import ast
from pathlib import Path
import networkx as nx

SRC_DIR = Path(__file__).resolve().parents[1] / "target_repo" / "src" / "taskflow"


def build_code_graph(src_dir: Path) -> nx.DiGraph:
    """Parse Python modules into a directed graph of modules, classes, functions, and calls."""
    graph = nx.DiGraph()

    for py_file in sorted(src_dir.glob("*.py")):
        module_name = f"taskflow.{py_file.stem}"
        graph.add_node(module_name, kind="module", file=str(py_file.name))

        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("taskflow"):
                graph.add_edge(module_name, node.module, relation="imports")

        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                fn_id = f"{module_name}.{node.name}"
                graph.add_node(fn_id, kind="function", lineno=node.lineno)
                graph.add_edge(module_name, fn_id, relation="defines")
                _add_call_edges(graph, fn_id, node)
            elif isinstance(node, ast.ClassDef):
                cls_id = f"{module_name}.{node.name}"
                graph.add_node(cls_id, kind="class", lineno=node.lineno)
                graph.add_edge(module_name, cls_id, relation="defines")
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        m_id = f"{cls_id}.{item.name}"
                        graph.add_node(m_id, kind="method", lineno=item.lineno)
                        graph.add_edge(cls_id, m_id, relation="has_method")
                        _add_call_edges(graph, m_id, item)

    return graph


def _add_call_edges(graph: nx.DiGraph, caller_id: str, func_node: ast.AST) -> None:
    for child in ast.walk(func_node):
        if isinstance(child, ast.Call):
            callee = None
            if isinstance(child.func, ast.Name):
                callee = child.func.id
            elif isinstance(child.func, ast.Attribute):
                callee = child.func.attr
            if callee:
                graph.add_edge(caller_id, f"call:{callee}", relation="calls")


def main() -> None:
    graph = build_code_graph(SRC_DIR)
    modules = [n for n, d in graph.nodes(data=True) if d.get("kind") == "module"]
    classes = [n for n, d in graph.nodes(data=True) if d.get("kind") == "class"]
    funcs = [n for n, d in graph.nodes(data=True) if d.get("kind") in ("function", "method")]

    print(f"Code Graph built from {SRC_DIR.name}/:")
    print(f"  Modules: {len(modules)} | Classes: {len(classes)} | Functions/Methods: {len(funcs)}")
    print(f"  Total Nodes: {graph.number_of_nodes()} | Total Edges: {graph.number_of_edges()}")

    print("\nModule import dependencies (excluding __init__):")
    for u, v, data in sorted(graph.edges(data=True)):
        if data.get("relation") == "imports" and u != "taskflow.__init__":
            print(f"  {u}  -->  {v}")

    target_method = "taskflow.runner.TaskRunner._run_single_task"
    if target_method in graph:
        callees = [
            v.replace("call:", "")
            for _, v, d in graph.edges(target_method, data=True)
            if d.get("relation") == "calls"
        ]
        print(f"\nDirect calls inside `{target_method}`:")
        print(" ", ", ".join(sorted(set(callees))))


if __name__ == "__main__":
    main()
