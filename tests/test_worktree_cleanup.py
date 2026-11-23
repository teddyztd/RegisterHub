"""Behavior tests for safe worktree cleanup (ticket #10).

External seams under test:
* ``core.worktree_cleanup.scan_artifacts`` — the protected-artifact detector.
* ``scripts/worktree_cleanup.py`` — the real CLI, driven through a subprocess
  against temporary Git repositories and worktrees. No real ``results/`` data
  is ever touched; every fixture lives under pytest's tmp_path.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from core.worktree_cleanup import scan_artifacts

REPO_ROOT = Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "scripts" / "worktree_cleanup.py"

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None,
    reason="git CLI is required for worktree cleanup behavior tests",
)


# --- helpers --------------------------------------------------------------


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git("init", "-q", cwd=repo).returncode == 0
    assert _git("config", "user.email", "test@example.com", cwd=repo).returncode == 0
    assert _git("config", "user.name", "Test", cwd=repo).returncode == 0
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    (repo / ".gitignore").write_text("results/\n", encoding="utf-8")
    assert _git("add", "README.md", ".gitignore", cwd=repo).returncode == 0
    assert _git("commit", "-q", "-m", "init", cwd=repo).returncode == 0
    return repo


def _add_worktree(repo: Path, worktree: Path, branch: str) -> None:
    result = _git("worktree", "add", str(worktree), "-b", branch, cwd=repo)
    assert result.returncode == 0, result.stderr


def _run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *args], cwd=cwd, capture_output=True, text=True
    )


def _seed_live_artifacts(worktree: Path) -> None:
    results = worktree / "results"
    (results / "cookies").mkdir(parents=True)
    (results / "pending_activation").mkdir()
    (results / "accounts.txt").write_text(
        "alice@example.com----S3cretPass!----alice\n", encoding="utf-8"
    )
    (results / "cookies" / "alice.json").write_text(
        json.dumps([{"name": "session", "value": "TOKEN", "domain": "example.com"}]),
        encoding="utf-8",
    )
    (results / "pending_activation" / "bob.json").write_text(
        json.dumps({"stage": "confirmation", "account": {"email": "bob@example.com"}}),
        encoding="utf-8",
    )


# --- core scan seam -------------------------------------------------------


def test_scan_protects_live_accounts_cookies_and_pending_activation(tmp_path: Path) -> None:
    wt = tmp_path / "wt"
    _seed_live_artifacts(wt)

    scan = scan_artifacts(wt)

    assert scan.live is True
    kinds = {a.kind for a in scan.artifacts}
    assert {"accounts", "cookie", "pending_activation"} <= kinds
    assert scan.artifacts  # non-empty inventory


def test_scan_offline_demo_output_alone_is_not_live(tmp_path: Path) -> None:
    wt = tmp_path / "wt"
    (wt / "results").mkdir(parents=True)
    (wt / "results" / "accounts.txt").write_text(
        "cool_dev42@demo-community.org----Passw0rd!----cool_dev42\n", encoding="utf-8"
    )

    scan = scan_artifacts(wt)

    assert scan.live is False
    assert all(a.kind == "demo" for a in scan.artifacts)


def test_scan_malformed_credential_row_is_live_fail_safe(tmp_path: Path) -> None:
    wt = tmp_path / "wt"
    (wt / "results").mkdir(parents=True)
    (wt / "results" / "accounts.txt").write_text(
        "truncated@example.com----only-two-fields\n", encoding="utf-8"
    )

    scan = scan_artifacts(wt)

    assert scan.live is True
    assert scan.artifacts[0].kind == "accounts"


def test_scan_recurses_into_nested_run_output(tmp_path: Path) -> None:
    wt = tmp_path / "wt"
    nested = wt / "results" / "stress-10"
    (nested / "cookies").mkdir(parents=True)
    (nested / "accounts.txt").write_text(
        "carol@example.com----pw----carol\n", encoding="utf-8"
    )
    (nested / "cookies" / "carol.json").write_text("[]", encoding="utf-8")

    scan = scan_artifacts(wt)

    assert scan.live is True
    assert {a.kind for a in scan.artifacts} == {"accounts", "cookie"}


# --- real CLI: check mode -------------------------------------------------


def test_cli_check_reports_live_artifacts_without_modifying(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = tmp_path / "wt"
    _add_worktree(repo, wt, "wt-check")
    _seed_live_artifacts(wt)
    before = sorted(p for p in (wt / "results").rglob("*") if p.is_file())

    result = _run_cli("check", str(wt), cwd=tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    out = result.stdout.lower()
    assert "accounts" in out and "cookie" in out and "pending_activation" in out
    # Non-mutating: every protected file is still present.
    after = sorted(p for p in (wt / "results").rglob("*") if p.is_file())
    assert after == before
    # Credentials must never leak into diagnostics.
    assert "S3cretPass!" not in result.stdout


def test_cli_check_offline_demo_only_exits_zero(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = tmp_path / "wt"
    _add_worktree(repo, wt, "wt-demo")
    (wt / "results").mkdir()
    (wt / "results" / "accounts.txt").write_text(
        "cool_dev42@demo-community.org----Passw0rd!----cool_dev42\n", encoding="utf-8"
    )

    result = _run_cli("check", str(wt), cwd=tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (wt / "results" / "accounts.txt").exists()


# --- real CLI: remove refusal --------------------------------------------


def test_cli_remove_refuses_while_unarchived_live_artifacts_remain(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = tmp_path / "wt"
    _add_worktree(repo, wt, "wt-refuse")
    _seed_live_artifacts(wt)

    result = _run_cli("remove", str(wt), cwd=tmp_path)

    assert result.returncode == 2, result.stdout + result.stderr
    assert wt.exists(), "worktree must survive a refusal"
    assert (wt / "results" / "accounts.txt").exists()
    assert (wt / "results" / "cookies" / "alice.json").exists()
    assert (wt / "results" / "pending_activation" / "bob.json").exists()


def test_cli_remove_refuses_uncommitted_untracked_changes(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = tmp_path / "wt"
    _add_worktree(repo, wt, "wt-dirty")
    (wt / "notes.txt").write_text("uncommitted work\n", encoding="utf-8")

    result = _run_cli("remove", str(wt), cwd=tmp_path)

    assert result.returncode == 2, result.stdout + result.stderr
    assert wt.exists()
    assert (wt / "notes.txt").exists()


# --- real CLI: explicit archive ------------------------------------------


def test_cli_archive_moves_live_artifacts_to_explicit_destination(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = tmp_path / "wt"
    _add_worktree(repo, wt, "wt-archive")
    _seed_live_artifacts(wt)
    dest = tmp_path / "archive"

    result = _run_cli("archive", str(wt), "--dest", str(dest), cwd=tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    archived = dest / "results"
    assert (archived / "accounts.txt").read_text(encoding="utf-8").strip()
    assert (archived / "cookies" / "alice.json").is_file()
    assert (archived / "pending_activation" / "bob.json").is_file()
    # Preserved, not lost: the worktree no longer holds them.
    assert not (wt / "results" / "accounts.txt").exists()
    assert not (wt / "results" / "cookies" / "alice.json").exists()
    # Archive is not removal: the worktree still exists.
    assert wt.exists()


def test_cli_archive_refuses_destination_inside_worktree(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = tmp_path / "wt"
    _add_worktree(repo, wt, "wt-dest-guard")
    _seed_live_artifacts(wt)

    result = _run_cli("archive", str(wt), "--dest", str(wt / "keep"), cwd=tmp_path)

    assert result.returncode == 2, result.stdout + result.stderr
    assert (wt / "results" / "accounts.txt").exists()


# --- real CLI: guarded removal -------------------------------------------


def test_cli_remove_with_dest_archives_then_removes(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = tmp_path / "wt"
    _add_worktree(repo, wt, "wt-remove-dest")
    _seed_live_artifacts(wt)
    dest = tmp_path / "archive"

    result = _run_cli("remove", str(wt), "--dest", str(dest), cwd=tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert not wt.exists(), "worktree must be removed after archiving"
    assert (dest / "results" / "cookies" / "alice.json").is_file()


def test_cli_remove_offline_demo_output_proceeds_without_archive(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = tmp_path / "wt"
    _add_worktree(repo, wt, "wt-demo-remove")
    (wt / "results").mkdir()
    (wt / "results" / "accounts.txt").write_text(
        "cool_dev42@demo-community.org----Passw0rd!----cool_dev42\n", encoding="utf-8"
    )

    result = _run_cli("remove", str(wt), cwd=tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert not wt.exists(), "offline demo output alone must not block removal"