"""Behavior tests for the repository-provided opt-in pre-commit hook.

These exercise the real external seam: a temporary Git repository with the
hook installed, driven through the actual ``git commit`` CLI. The hook must
run the pytest gate and block a commit when the suite fails, while allowing
it when the suite passes. No global Git configuration is touched — the hook
is installed directly into the temp repo's ``.git/hooks`` directory.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_SOURCE = REPO_ROOT / ".githooks" / "pre-commit"

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None, reason="git CLI is required for hook behavior tests"
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def _commit(repo: Path, message: str) -> subprocess.CompletedProcess:
    return _git(repo, "commit", "-m", message)


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    result = _git(repo, "init")
    assert result.returncode == 0, result.stderr
    # Local-only identity; never touches global config.
    assert _git(repo, "config", "user.email", "test@example.com").returncode == 0
    assert _git(repo, "config", "user.name", "Test").returncode == 0
    # Isolate the gate: this temp repo defines its own quick suite.
    (repo / "pytest.ini").write_text("[pytest]\ntestpaths = .\n", encoding="utf-8")
    return repo


def _install_hook(repo: Path) -> None:
    hooks_dir = repo / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    target = hooks_dir / "pre-commit"
    shutil.copyfile(HOOK_SOURCE, target)
    # Ensure the executable bit is set on POSIX checkouts.
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _write_test(repo: Path, passing: bool) -> Path:
    body = "def test_gate():\n    assert True\n" if passing else "def test_gate():\n    assert False\n"
    test_file = repo / "test_gate.py"
    test_file.write_text(body, encoding="utf-8")
    return test_file


def test_hook_allows_commit_when_tests_pass(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _install_hook(repo)
    test_file = _write_test(repo, passing=True)
    _git(repo, "add", test_file.name)

    result = _commit(repo, "passing change")

    assert result.returncode == 0, result.stderr + result.stdout
    log = _git(repo, "log", "--oneline")
    assert "passing change" in log.stdout


def test_hook_blocks_commit_when_tests_fail(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    _install_hook(repo)
    test_file = _write_test(repo, passing=False)
    _git(repo, "add", test_file.name)

    result = _commit(repo, "failing change")

    assert result.returncode != 0, "a failing test must block the commit"
    log = _git(repo, "log", "--oneline")
    assert "failing change" not in log.stdout, "no commit may be created on failure"
