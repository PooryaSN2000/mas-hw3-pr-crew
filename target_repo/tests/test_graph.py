"""Public unit tests for WorkflowGraph."""

import pytest

from taskflow.graph import WorkflowGraph
from taskflow.models import (
    CycleDetectedError,
    MissingDependencyError,
    TaskSpec,
    Workflow,
)


def test_linear_topological_order():
    wf = Workflow(name="linear")
    wf.add_task(TaskSpec(name="extract", command="echo"))
    wf.add_task(TaskSpec(name="transform", command="echo", depends_on=["extract"]))
    wf.add_task(TaskSpec(name="load", command="echo", depends_on=["transform"]))

    graph = WorkflowGraph(wf)
    assert graph.topological_sort() == ["extract", "transform", "load"]
    assert graph.critical_path_depth() == 3


def test_tree_branching_order_and_dot():
    wf = Workflow(name="tree")
    wf.add_task(TaskSpec(name="root", command="echo"))
    wf.add_task(TaskSpec(name="branch_b", command="echo", depends_on=["root"]))
    wf.add_task(TaskSpec(name="branch_a", command="echo", depends_on=["root"]))

    graph = WorkflowGraph(wf)
    assert graph.topological_sort() == ["root", "branch_a", "branch_b"]
    assert graph.execution_levels() == [["root"], ["branch_a", "branch_b"]]
    dot = graph.to_dot()
    assert '"root" -> "branch_a";' in dot
    assert '"root" -> "branch_b";' in dot


def test_detects_direct_cycle():
    wf = Workflow(name="cycle2")
    wf.add_task(TaskSpec(name="a", command="echo", depends_on=["b"]))
    wf.add_task(TaskSpec(name="b", command="echo", depends_on=["a"]))

    graph = WorkflowGraph(wf)
    with pytest.raises(CycleDetectedError):
        graph.topological_sort()


def test_detects_three_node_cycle():
    wf = Workflow(name="cycle3")
    wf.add_task(TaskSpec(name="a", command="echo", depends_on=["c"]))
    wf.add_task(TaskSpec(name="b", command="echo", depends_on=["a"]))
    wf.add_task(TaskSpec(name="c", command="echo", depends_on=["b"]))

    graph = WorkflowGraph(wf)
    with pytest.raises(CycleDetectedError):
        graph.detect_cycles()


def test_missing_dependency_raises():
    wf = Workflow(name="broken")
    wf.add_task(TaskSpec(name="a", command="echo", depends_on=["nonexistent"]))

    with pytest.raises(MissingDependencyError):
        WorkflowGraph(wf)
