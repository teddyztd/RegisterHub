"""Safe worktree cleanup: protect ignored live artifacts before removal.

Live artifacts are the local credentials and recovery data that Git ignores
(``results/``) but an operator must never silently lose when removing a
linked worktree:

* account ledger rows   -- ``results/**/accounts.txt`` rows whose email is
  not on the built-in offline Demo domain
* cookie sidecars       -- ``results/**/cookies/*.json``
* pending activations   -- ``results/**/pending_activation/*.json``

The built-in offline Demo adapter writes only ``@demo-community.org`` ledger
rows and never writes cookie sidecars or pending-activation records, so demo
output alone is not a live artifact and does not trigger the guard.

Standard-library only; no new application framework.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

DEMO_EMAIL_DOMAIN = "demo-community.org"
RESULTS_DIR = "results"
LEDGER_NAME = "accounts.txt"
COOKIE_DIR = "cookies"
PENDING_DIR = "pending_activation"

KIND_LEDGER = "accounts"
KIND_COOKIE = "cookie"
KIND_PENDING = "pending_activation"
KIND_DEMO = "demo"


@dataclass
class Artifact:
    """One protected item found under a worktree's results directory."""

    kind: str
    path: Path
    detail: str = ""


@dataclass
class ScanResult:
    """Inventory of protected artifacts found in one worktree."""

    worktree: Path
    artifacts: List[Artifact] = field(default_factory=list)

    @property
    def live(self) -> bool:
        """True when at least one unarchived live artifact remains."""
        return any(a.kind != KIND_DEMO for a in self.artifacts)

    @property
    def live_artifacts(self) -> List[Artifact]:
        return [a for a in self.artifacts if a.kind != KIND_DEMO]


def _ledger_row_kind(line: str):
    """Classify one ledger line.

    Returns ``KIND_DEMO`` for validated offline demo credentials,
    ``KIND_LEDGER`` for anything else that looks like a credential row, and
    ``None`` for blank/unrelated lines. A row containing ``----`` but failing
    validation is still treated as live: fail-safe beats silently discarding a
    malformed real credential.
    """
    line = line.strip()
    if not line or "----" not in line:
        return None
    parts = [part.strip() for part in line.split("----")]
    if len(parts) < 3 or not all(parts[:3]):
        return KIND_LEDGER
    if parts[0].endswith("@" + DEMO_EMAIL_DOMAIN):
        return KIND_DEMO
    return KIND_LEDGER


def _json_under_dir(results: Path, dirname: str) -> List[Path]:
    """Every ``*.json`` whose path has a ``dirname`` directory component."""
    if not results.is_dir():
        return []
    found = []
    for path in sorted(results.rglob("*.json")):
        rel = path.relative_to(results)
        if dirname in rel.parts[:-1]:
            found.append(path)
    return found


def scan_artifacts(worktree: Path) -> ScanResult:
    """Inventory the protected artifacts under ``<worktree>/results``.

    Non-mutating: only reads. Ledger files with live rows, every cookie
    sidecar, and every pending-activation record are live artifacts; demo
    ledger rows are reported as ``demo`` and never trigger the guard.
    """
    worktree = Path(worktree)
    results = worktree / RESULTS_DIR
    scan = ScanResult(worktree=worktree)

    if results.is_dir():
        for ledger in sorted(results.rglob(LEDGER_NAME)):
            try:
                content = ledger.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line in content.splitlines():
                kind = _ledger_row_kind(line)
                if kind is not None:
                    scan.artifacts.append(
                        Artifact(kind, ledger, detail=line.strip())
                    )

    for path in _json_under_dir(results, COOKIE_DIR):
        scan.artifacts.append(Artifact(KIND_COOKIE, path))

    for path in _json_under_dir(results, PENDING_DIR):
        scan.artifacts.append(Artifact(KIND_PENDING, path))

    return scan


def archive_live_artifacts(scan: ScanResult, dest: Path) -> List[Path]:
    """Move every live artifact into ``dest``, preserving paths from the worktree.

    The destination must sit outside the worktree, otherwise the artifacts
    would still be "in" the worktree being removed. One ledger file is moved
    once even when it holds several live rows. Returns the archived paths.
    """
    worktree = scan.worktree
    dest = Path(dest)
    worktree_resolved = worktree.resolve()
    dest_resolved = dest.resolve()
    if dest_resolved == worktree_resolved or dest_resolved.is_relative_to(
        worktree_resolved
    ):
        raise ValueError("archive destination must be outside the worktree")

    moved: List[Path] = []
    seen = set()
    for artifact in scan.live_artifacts:
        if artifact.path in seen:
            continue
        seen.add(artifact.path)
        rel = artifact.path.relative_to(worktree)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(f"archive target already exists: {target}")
        shutil.move(str(artifact.path), str(target))
        moved.append(target)
    return moved


def git_status_porcelain(worktree: Path) -> subprocess.CompletedProcess:
    """Return ``git status --porcelain`` for a worktree.

    Ignored files are excluded by default, so protected ``results/`` artifacts
    do not make a worktree look dirty. Any output means tracked changes or
    untracked non-ignored files exist and must be reviewed before ``--force``
    removal.
    """
    return subprocess.run(
        ["git", "-C", str(worktree), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )


def git_remove_worktree(worktree: Path) -> subprocess.CompletedProcess:
    """Remove a linked worktree via Git, from its main checkout.

    ``--force`` is required because Git refuses to remove a worktree holding
    ignored files (e.g. leftover offline demo output) and this CLI has already
    guarded the only data class Git would silently lose: ignored live
    artifacts. The command runs from the main checkout so the target worktree
    is never the process working directory.
    """
    worktree = Path(worktree).resolve()
    common = subprocess.run(
        [
            "git",
            "-C",
            str(worktree),
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        ],
        capture_output=True,
        text=True,
    )
    if common.returncode != 0:
        return common
    main_root = Path(common.stdout.strip()).parent
    return subprocess.run(
        ["git", "-C", str(main_root), "worktree", "remove", str(worktree), "--force"],
        cwd=str(main_root),
        capture_output=True,
        text=True,
    )