"""Public unit tests for config, validators, inspector, and registry."""

import json
import pytest

from taskflow.config import load_config, load_config_from_env
from taskflow.inspector import diff_workflows, explain_workflow, find_impacted_tasks
from taskflow.models import ConfigError, TaskSpec, Workflow
from taskflow.registry import CommandRegistry, build_default_registry
from taskflow.validators import WorkflowValidator


def test_config_loading_and_env(tmp_path):
    cfg_file = tmp_path / "cfg.json"
    cfg_file.write_text(json.dumps({"max_workers": 2, "fail_fast": True}), encoding="utf-8")

    cfg = load_config(config_file=cfg_file, overrides={"default_retries": 1})
    assert cfg.max_workers == 2
    assert cfg.fail_fast is True
    assert cfg.default_retries == 1

    env_cfg = load_config_from_env({"TASKFLOW_MAX_WORKERS": "4", "TASKFLOW_ENABLE_CACHE": "false"})
    assert env_cfg.max_workers == 4
    assert env_cfg.enable_cache is False

    with pytest.raises(ConfigError):
        load_config(overrides={"unknown_setting": 123})


def test_validator_and_inspector():
    wf = Workflow(name="sample")
    wf.add_task(TaskSpec(name="ingest", command="echo"))
    wf.add_task(TaskSpec(name="clean", command="upper", depends_on=["ingest"]))
    wf.add_task(TaskSpec(name="count", command="word_count", depends_on=["clean"]))

    validator = WorkflowValidator(known_commands=build_default_registry().keys())
    v_report = validator.validate(wf)
    assert v_report.is_valid is True

    info = explain_workflow(wf)
    assert info["roots"] == ["ingest"]
    assert info["leaves"] == ["count"]
    assert find_impacted_tasks(wf, "clean") == ["clean", "count"]

    wf2 = Workflow(name="sample")
    wf2.add_task(TaskSpec(name="ingest", command="echo"))
    wf2.add_task(TaskSpec(name="clean", command="lower", depends_on=["ingest"]))
    diff = diff_workflows(wf, wf2)
    assert diff["modified"] == ["clean"]
    assert diff["removed"] == ["count"]


def test_command_registry_aliases():
    reg = CommandRegistry()
    reg.register("greet", lambda p, u: "hi", description="Greet user", aliases=["hello"])
    assert reg.has("greet")
    assert reg.has("hello")
    assert reg.resolve_name("hello") == "greet"
    assert reg.describe("hello") == "Greet user"
