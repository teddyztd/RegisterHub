"""Safe worktree cleanup CLI (ticket #10).

Guards the ignored live artifacts — account ledger rows, cookie sidecars,
pending-activation records — that ``git worktree remove`` would silently
discard. Offline demo output alone never triggers the guard.

Modes:
  check   <worktree>                 report protected artifacts, never modify
  archive <worktree> --dest DIR     move live artifacts to an explicit archive
  remove  <worktree> [--dest DIR]   refuse while unarchived live artifacts
                                     remain; with --dest, archive first, then
                                     remove the worktree via Git

Exit codes: 0 = success/safe; 1 = check found live artifacts; 2 = refused
or invalid request; other non-zero = the underlying Git failure.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.worktree_cleanup import (  # noqa: E402
    KIND_DEMO,
    ScanResult,
    archive_live_artifacts,
    git_remove_worktree,
    git_status_porcelain,
    scan_artifacts,
)

EXIT_OK = 0
EXIT_LIVE = 1
EXIT_REFUSED = 2


def _print_inventory(scan: ScanResult) -> None:
    live = scan.live_artifacts
    if not live:
        print("no live artifacts found")
    else:
        print(f"live artifacts: {len(live)}")
        for artifact in live:
            print(f"  [{artifact.kind}] {artifact.path}")
    demo_rows = [a for a in scan.artifacts if a.kind == KIND_DEMO]
    if demo_rows:
        print(f"offline demo rows (not live): {len(demo_rows)}")


def _refuse(message: str) -> int:
    print(message, file=sys.stderr)
    return EXIT_REFUSED


def _do_check(worktree: Path) -> int:
    scan = scan_artifacts(worktree)
    _print_inventory(scan)
    return EXIT_LIVE if scan.live else EXIT_OK


def _do_archive(worktree: Path, dest: Path) -> int:
    scan = scan_artifacts(worktree)
    if not scan.live:
        print("no live artifacts to archive")
        return EXIT_OK
    try:
        moved = archive_live_artifacts(scan, dest)
    except (ValueError, FileExistsError, OSError) as exc:
        return _refuse(f"archive refused: {exc}")
    print(f"archived {len(moved)} live artifact(s) to {dest}")
    for target in moved:
        print(f"  -> {target}")
    return EXIT_OK


def _do_remove(worktree: Path, dest: Path | None) -> int:
    scan = scan_artifacts(worktree)
    if scan.live:
        if dest is None:
            _print_inventory(scan)
            return _refuse(
                "refusing to remove worktree with unarchived live artifacts; "
                "pass --dest DIR to archive them first"
            )
        try:
            moved = archive_live_artifacts(scan, dest)
        except (ValueError, FileExistsError, OSError) as exc:
            return _refuse(f"archive refused: {exc}")
        print(f"archived {len(moved)} live artifact(s) to {dest}")
        for target in moved:
            print(f"  -> {target}")
    else:
        print("no live artifacts found")

    # Guard against tracked changes and untracked non-ignored files that
    # `git worktree remove --force` would silently discard.
    status = git_status_porcelain(worktree)
    if status.returncode != 0:
        return _refuse(f"git status failed: {status.stderr.strip()}")
    if status.stdout.strip():
        return _refuse(
            "refusing to remove worktree with uncommitted or untracked "
            "non-ignored changes; commit or discard them first"
        )

    # Re-scan immediately before removal: a concurrent writer may have
    # produced a new live artifact after the archive step.
    if scan_artifacts(worktree).live:
        return _refuse(
            "refusing to remove worktree: live artifacts appeared after "
            "archiving; run check and archive again"
        )

    result = git_remove_worktree(worktree)
    if result.returncode != 0:
        print(
            f"git worktree remove failed: {result.stderr.strip()}",
            file=sys.stderr,
        )
        return result.returncode or EXIT_REFUSED
    print(f"removed worktree: {worktree}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        prog="worktree_cleanup.py",
        description="Remove a Git worktree without losing ignored live artifacts",
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    check = sub.add_parser("check", help="report protected artifacts without modifying")
    check.add_argument("worktree")

    archive = sub.add_parser("archive", help="move live artifacts to an explicit archive")
    archive.add_argument("worktree")
    archive.add_argument("--dest", required=True, help="archive destination directory")

    remove = sub.add_parser("remove", help="guard, optionally archive, then remove")
    remove.add_argument("worktree")
    remove.add_argument("--dest", default=None, help="archive destination directory")

    args = parser.parse_args(argv)
    worktree = Path(args.worktree)

    if args.mode == "check":
        return _do_check(worktree)
    if args.mode == "archive":
        return _do_archive(worktree, Path(args.dest))
    return _do_remove(worktree, Path(args.dest) if args.dest else None)


if __name__ == "__main__":
    raise SystemExit(main())