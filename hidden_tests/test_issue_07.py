"""Hidden evaluation tests for ISSUE-07 (Conditional `when:` execution across models, parser, runner)."""

import json

from taskflow.models import TaskStatus
from taskflow.parser import parse_workflow, parse_workflow_file
from taskflow.runner import TaskRunner


def test_when_parsing_tfw_and_json(tmp_path):
    dsl = '''
workflow: deploy_flow

task check:
  command: echo
  param message=ready

task deploy:
  command: echo
  depends_on: check
  when: upstream.check == ready
  param message=deployed

task alert:
  command: echo
  depends_on: check
  when: on_failure
  param message=alerted

task cleanup:
  command: echo
  depends_on: deploy
  when: always
  param message=cleaned
'''
    wf = parse_workflow(dsl)
    assert wf.tasks["check"].when is None
    assert wf.tasks["deploy"].when == "upstream.check == ready"
    assert wf.tasks["alert"].when == "on_failure"
    assert wf.tasks["cleanup"].when == "always"

    jpath = tmp_path / "cond.json"
    jpath.write_text(
        json.dumps(
            {
                "name": "jcond",
                "tasks": [
                    {"name": "a", "command": "echo"},
                    {"name": "b", "command": "echo", "depends_on": ["a"], "when": "always"},
                ],
            }
        ),
        encoding="utf-8",
    )
    jwf = parse_workflow_file(jpath)
    assert jwf.tasks["b"].when == "always"


def test_when_runtime_on_upstream_success():
    dsl = '''
workflow: cond_ok

task step_a:
  command: produce

task on_match:
  command: tag
  depends_on: step_a
  when: upstream.step_a == green
  param val=matched

task on_mismatch:
  command: tag
  depends_on: step_a
  when: upstream.step_a == red
  param val=mismatched

task on_fail:
  command: tag
  depends_on: step_a
  when: on_failure
  param val=handled_fail

task final_cleanup:
  command: tag
  depends_on: step_a
  when: always
  param val=cleaned
'''
    wf = parse_workflow(dsl)
    reg = {"produce": lambda p, u: "green", "tag": lambda p, u: p["val"]}
    report = TaskRunner(registry=reg).run(wf)

    assert report.succeeded is True
    assert report.results["on_match"].status == TaskStatus.SUCCESS
    assert report.results["on_match"].output == "matched"
    assert report.results["on_mismatch"].status == TaskStatus.SKIPPED
    assert report.results["on_fail"].status == TaskStatus.SKIPPED
    assert report.results["final_cleanup"].status == TaskStatus.SUCCESS
    assert report.results["final_cleanup"].output == "cleaned"


def test_when_runtime_on_upstream_failure():
    dsl = '''
workflow: cond_fail

task step_a:
  command: boom

task on_match:
  command: tag
  depends_on: step_a
  when: upstream.step_a == green
  param val=matched

task on_fail:
  command: tag
  depends_on: step_a
  when: on_failure
  param val=handled_fail

task final_cleanup:
  command: tag
  depends_on: step_a
  when: always
  param val=cleaned
'''
    wf = parse_workflow(dsl)

    def boom(p, u):
        raise RuntimeError("step_a failed")

    reg = {"boom": boom, "tag": lambda p, u: p["val"]}
    report = TaskRunner(registry=reg).run(wf)

    assert report.succeeded is False
    assert report.results["step_a"].status == TaskStatus.FAILED
    assert report.results["on_match"].status == TaskStatus.SKIPPED
    assert report.results["on_fail"].status == TaskStatus.SUCCESS
    assert report.results["on_fail"].output == "handled_fail"
    assert report.results["final_cleanup"].status == TaskStatus.SUCCESS
    assert report.results["final_cleanup"].output == "cleaned"
