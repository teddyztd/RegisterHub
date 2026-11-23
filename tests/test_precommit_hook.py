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


# Git exports its repository plumbing to hooks: GIT_DIR and friends relocate the
# repository, GIT_INDEX_FILE relocates the index, GIT_CONFIG_* carries ``-c``
# overrides such as core.hooksPath, and GIT_AUTHOR_*/GIT_COMMITTER_* carry the
# identity. This module runs inside the pre-commit hook itself, so inheriting
# any of it makes the temp repo below act on the developer's real repository
# (``git init`` there flips core.bare, temp commits land on the live branch) or
# silently skip the temp repo's own hook. Each command must start from a clean
# Git environment and discover everything from its own ``cwd``.
def _clean_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.lower().startswith("git_")}


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        env=_clean_env(),
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


def test_temp_repo_helpers_ignore_inherited_git_plumbing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The suite runs inside the hook, so Git's plumbing leaks into it.

    With GIT_DIR pointing at another repository, the temp-repo helpers must
    still act on their own repo and leave the leaked one byte-for-byte alone
    (no re-init, no core.bare flip, no stray commit on its branch).
    """
    victim = tmp_path / "victim"
    victim.mkdir()
    assert _git(victim, "init").returncode == 0
    assert _git(victim, "config", "user.email", "victim@example.com").returncode == 0
    assert _git(victim, "config", "user.name", "Victim").returncode == 0
    (victim / "keep.txt").write_text("keep\n", encoding="utf-8")
    assert _git(victim, "add", "keep.txt").returncode == 0
    assert _commit(victim, "victim baseline").returncode == 0
    baseline = _git(victim, "rev-parse", "HEAD").stdout.strip()
    assert baseline

    monkeypatch.setenv("GIT_DIR", str(victim / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(victim))
    monkeypatch.setenv("GIT_INDEX_FILE", str(victim / ".git" / "index"))
    # The identity and -c overrides a live hook run also exports.
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "leaked@example.com")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "leaked@example.com")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.hookspath")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", ".githooks")

    repo = _make_repo(tmp_path)
    _install_hook(repo)
    test_file = _write_test(repo, passing=True)
    _git(repo, "add", test_file.name)
    result = _commit(repo, "passing change")

    assert result.returncode == 0, result.stderr + result.stdout
    assert "passing change" in _git(repo, "log", "--oneline").stdout
    # The commit belongs to the temp repo, under the identity it configured.
    assert _git(repo, "log", "-1", "--format=%ae").stdout.strip() == "test@example.com"
    # The leaked repository is untouched.
    assert _git(victim, "rev-parse", "HEAD").stdout.strip() == baseline
    assert "passing change" not in _git(victim, "log", "--oneline").stdout
    assert _git(victim, "config", "--local", "core.bare").stdout.strip() != "true"
