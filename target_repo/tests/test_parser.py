"""Public unit tests for .tfw/.json parsing and serialization."""

import pytest

from taskflow.models import WorkflowParseError
from taskflow.parser import parse_workflow, parse_workflow_file
from taskflow.serializers import workflow_to_dict, workflow_to_tfw


def test_parse_valid_tfw():
    text = '''
    # Sample workflow
    workflow: etl
    meta owner=data-eng

    task extract:
      command: fetch
      retries: 2
      cacheable: false
      tags: io, critical
      timeout: 30.5
      param source=s3
      param limit=100

    task load:
      command: store
      depends_on: extract
    '''
    wf = parse_workflow(text)
    assert wf.name == "etl"
    assert wf.metadata == {"owner": "data-eng"}
    assert set(wf.tasks.keys()) == {"extract", "load"}
    assert wf.tasks["extract"].max_retries == 2
    assert wf.tasks["extract"].cacheable is False
    assert wf.tasks["extract"].tags == ["io", "critical"]
    assert wf.tasks["extract"].timeout_s == 30.5
    assert wf.tasks["extract"].params == {"source": "s3", "limit": 100}
    assert wf.tasks["load"].depends_on == ["extract"]

    # Round-trip serialization check
    serialized = workflow_to_tfw(wf)
    reparsed = parse_workflow(serialized)
    assert reparsed.name == wf.name
    assert reparsed.tasks["extract"].params == wf.tasks["extract"].params
    assert workflow_to_dict(wf)["name"] == "etl"


def test_parse_missing_workflow_header():
    with pytest.raises(WorkflowParseError):
        parse_workflow("task a:\n  command: echo\n")


def test_parse_missing_command():
    with pytest.raises(WorkflowParseError):
        parse_workflow("workflow: bad\ntask a:\n  retries: 1\n")


def test_parse_demo_file(tmp_path):
    p = tmp_path / "simple.json"
    p.write_text(
        '{"name": "jflow", "tasks": [{"name": "a", "command": "echo", "params": {"message": "hi"}}]}',
        encoding="utf-8",
    )
    wf = parse_workflow_file(p)
    assert wf.name == "jflow"
    assert wf.tasks["a"].params["message"] == "hi"
