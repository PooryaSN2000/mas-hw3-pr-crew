"""Dependency graph construction, cycle detection, topological sorting, and DOT export."""

from __future__ import annotations

from collections import deque
import heapq
from typing import Dict, List, Set

from taskflow.models import CycleDetectedError, MissingDependencyError, Workflow


class WorkflowGraph:
    """Directed graph representing task dependencies in a Workflow."""

    def __init__(self, workflow: Workflow) -> None:
        self.workflow = workflow
        self.dependents: Dict[str, List[str]] = {name: [] for name in workflow.tasks}
        self.dependencies: Dict[str, List[str]] = {name: [] for name in workflow.tasks}
        self._build()

    def _build(self) -> None:
        for task_name, spec in self.workflow.tasks.items():
            for dep in spec.depends_on:
                if dep not in self.workflow.tasks:
                    raise MissingDependencyError(
                        f"Task '{task_name}' depends on unknown task '{dep}'."
                    )
                if dep not in self.dependencies[task_name]:
                    self.dependencies[task_name].append(dep)
                if task_name not in self.dependents[dep]:
                    self.dependents[dep].append(task_name)

        for name in self.workflow.tasks:
            self.dependencies[name].sort()
            self.dependents[name].sort()

    def get_upstream(self, task_name: str) -> List[str]:
        """Return direct upstream dependency names for a task."""
        return list(self.dependencies[task_name])

    def get_downstream(self, task_name: str) -> List[str]:
        """Return direct downstream dependent names for a task."""
        return list(self.dependents[task_name])

    def get_roots(self) -> List[str]:
        """Return sorted task names that have no upstream dependencies."""
        return sorted(name for name, deps in self.dependencies.items() if not deps)

    def get_leaves(self) -> List[str]:
        """Return sorted task names that have no downstream dependents."""
        return sorted(name for name, deps in self.dependents.items() if not deps)

    def ancestors(self, task_name: str) -> Set[str]:
        """Return all transitive upstream dependencies of a task."""
        seen: Set[str] = set()
        queue = deque(self.dependencies[task_name])
        while queue:
            cur = queue.popleft()
            if cur not in seen:
                seen.add(cur)
                queue.extend(self.dependencies[cur])
        return seen

    def descendants(self, task_name: str) -> Set[str]:
        """Return all transitive downstream dependents of a task."""
        seen: Set[str] = set()
        queue = deque(self.dependents[task_name])
        while queue:
            cur = queue.popleft()
            if cur not in seen:
                seen.add(cur)
                queue.extend(self.dependents[cur])
        return seen

    def detect_cycles(self) -> None:
        """Validate that the workflow graph is acyclic; raise CycleDetectedError if not."""
        globally_seen: Set[str] = set()

        def dfs(node: str, path_seen: Set[str]) -> None:
            globally_seen.add(node)
            path_seen.add(node)
            for neighbor in self.dependents[node]:
                if neighbor in path_seen:
                    raise CycleDetectedError(
                        f"Cycle detected involving task '{node}' -> '{neighbor}'."
                    )
                dfs(neighbor, path_seen)

        roots = self.get_roots()
        for root in roots:
            if root not in globally_seen:
                dfs(root, set())

        for task_name in sorted(self.workflow.tasks):
            if task_name not in globally_seen:
                dfs(task_name, set())

    def topological_sort(self) -> List[str]:
        """Return a valid deterministic execution order for all tasks."""
        self.detect_cycles()

        in_degree: Dict[str, int] = {
            name: len(deps) for name, deps in self.dependencies.items()
        }
        ready_heap: List[str] = [
            name for name, deg in in_degree.items() if deg == 0
        ]
        heapq.heapify(ready_heap)

        order: List[str] = []
        while ready_heap:
            current = heapq.heappop(ready_heap)
            order.append(current)
            for nxt in self.dependents[current]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    heapq.heappush(ready_heap, nxt)

        if len(order) != len(self.workflow.tasks):
            raise CycleDetectedError("Workflow graph contains a cycle.")
        return order

    def execution_levels(self) -> List[List[str]]:
        """Group tasks into parallelizable topological waves."""
        self.detect_cycles()
        in_degree = {name: len(deps) for name, deps in self.dependencies.items()}
        queue = deque(sorted(n for n, d in in_degree.items() if d == 0))
        levels: List[List[str]] = []

        while queue:
            current_level = sorted(queue)
            levels.append(current_level)
            next_nodes: List[str] = []
            for node in current_level:
                for nxt in self.dependents[node]:
                    in_degree[nxt] -= 1
                    if in_degree[nxt] == 0:
                        next_nodes.append(nxt)
            queue = deque(sorted(next_nodes))

        return levels

    def critical_path_depth(self) -> int:
        """Return the length (in tasks) of the longest dependency chain."""
        order = self.topological_sort()
        if not order:
            return 0
        depth: Dict[str, int] = {}
        for node in order:
            upstream = self.dependencies[node]
            depth[node] = 1 + max((depth[u] for u in upstream), default=0)
        return max(depth.values(), default=0)

    def to_dot(self) -> str:
        """Render the dependency graph in Graphviz DOT format."""
        lines = [f'digraph "{self.workflow.name}" {{', "  rankdir=LR;"]
        for name in sorted(self.workflow.tasks):
            spec = self.workflow.tasks[name]
            lines.append(f'  "{name}" [label="{name}\\n({spec.command})"];')
        for name in sorted(self.workflow.tasks):
            for nxt in self.dependents[name]:
                lines.append(f'  "{name}" -> "{nxt}";')
        lines.append("}")
        return "\n".join(lines)
