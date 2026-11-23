"""Conformance test for the GitHub Actions test workflow.

Guards the wiring that makes CI a real gate: the workflow must trigger on
push and pull_request, exercise the existing pytest suite, and cover the
supported Python 3.10+ line. This is a config-conformance check over the
workflow file rather than a re-derivation of its contents.
"""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "tests.yml"


def _load() -> str:
    assert WORKFLOW.is_file(), f"CI workflow is missing: {WORKFLOW}"
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_triggers_on_push_and_pull_request() -> None:
    text = _load()
    assert re.search(r"^\s*push\s*:", text, re.MULTILINE), "workflow must run on push"
    assert re.search(r"^\s*pull_request\s*:", text, re.MULTILINE), "workflow must run on pull_request"


def test_workflow_covers_python_310_plus() -> None:
    text = _load()
    assert "3.10" in text, "workflow must include Python 3.10 in its matrix"
    assert re.search(r"python-version", text), "workflow must select a Python version"


def test_workflow_runs_existing_pytest_suite() -> None:
    text = _load()
    assert re.search(r"python -m pytest|pytest tests", text), "workflow must invoke the existing pytest suite"
    assert re.search(r"pip install", text), "workflow must install project dependencies"
