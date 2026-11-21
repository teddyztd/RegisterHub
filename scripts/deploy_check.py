"""
RegisterHub Deployment Checker.

One-command local CLI deployment verification: prepares or reuses the local
.venv, installs dependencies and the Playwright Chromium fallback browser,
preserves operator configuration, runs diagnostics and the test suite, and
executes the built-in offline demo in an isolated temporary working directory.
The checker succeeds only when every stage succeeds and the isolated demo
produces a non-empty account ledger.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

STAGE_INSTALL = "install"
STAGE_CONFIG = "config"
STAGE_DOCTOR = "doctor"
STAGE_TESTS = "pytest"
STAGE_DEMO = "demo"


class StageFailure(Exception):
    """Raised when a blocking stage fails; carries the failing stage name."""

    def __init__(self, stage: str, returncode: int, detail: str = ""):
        super().__init__(f"stage '{stage}' failed with exit code {returncode}")
        self.stage = stage
        self.returncode = returncode
        self.detail = detail


def log(message: str) -> None:
    print(message, flush=True)


def in_venv() -> bool:
    return sys.prefix != sys.base_prefix


def ensure_venv() -> Path:
    """Create .venv when missing and return the interpreter inside it."""
    if in_venv():
        return Path(sys.executable)
    venv_dir = REPO_ROOT / ".venv"
    if os.name == "nt":
        interpreter = venv_dir / "Scripts" / "python.exe"
    else:
        interpreter = venv_dir / "bin" / "python"
    if not interpreter.exists():
        log("[*] .venv not found; creating virtual environment...")
        venv.create(str(venv_dir), with_pip=True)
    return interpreter


def reexec_in_venv(interpreter: Path, argv) -> "NoReturn":  # noqa: F821
    script = Path(__file__).resolve()
    result = subprocess.run([str(interpreter), str(script)] + list(argv), cwd=REPO_ROOT)
    raise SystemExit(result.returncode)


def run_stage(stage: str, command, cwd: Path) -> None:
    log(f"==> [{stage}] {' '.join(str(part) for part in command)} (cwd: {cwd})")
    result = subprocess.run(
        [str(part) for part in command], cwd=cwd, check=False
    )
    if result.returncode != 0:
        raise StageFailure(stage, result.returncode)


def derive_config() -> None:
    """Create root config.json from the example, forcing headless, only if missing.

    An existing operator configuration is never read or overwritten; the
    checker only preserves it.
    """
    config_path = REPO_ROOT / "config.json"
    example_path = REPO_ROOT / "config.example.json"
    if config_path.exists():
        log("[i] Existing config.json preserved.")
        return
    if not example_path.exists():
        raise StageFailure(STAGE_CONFIG, 1, "config.example.json is missing")
    try:
        config = json.loads(example_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StageFailure(STAGE_CONFIG, 1, f"cannot parse config.example.json: {exc}")
    config.setdefault("browser", {})["headless"] = True
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    log("[+] Created config.json from config.example.json with browser.headless=true.")


def run_demo(interpreter: Path) -> None:
    """Run the offline demo in an isolated temporary working directory.

    The demo configuration forces headless mode and a temporary output_dir so
    verification credentials never reach the normal account ledger.
    """
    with tempfile.TemporaryDirectory(prefix="registerhub-deploy-demo-") as tmp:
        workdir = Path(tmp)
        demo_config = {
            "browser": {"headless": True, "enable_stealth": True},
            "output_dir": str(workdir / "results"),
        }
        (workdir / "config.json").write_text(
            json.dumps(demo_config, indent=2), encoding="utf-8"
        )
        log("==> [demo] main.py --run demo (isolated temporary working directory)")
        result = subprocess.run(
            [str(interpreter), str(REPO_ROOT / "main.py"), "--run", "demo"],
            cwd=str(workdir),
            check=False,
        )
        if result.returncode != 0:
            raise StageFailure(STAGE_DEMO, result.returncode)
        ledger = workdir / "results" / "accounts.txt"
        content = ledger.read_text(encoding="utf-8") if ledger.exists() else ""
        if not content.strip():
            raise StageFailure(
                STAGE_DEMO, 1, "demo account ledger is empty (accounts.txt has no credentials)"
            )
        log("[+] Isolated demo ledger contains credential data (temporary, will be cleaned).")
    log("[+] Temporary demo directory cleaned.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="RegisterHub one-command local CLI deployment checker"
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip dependency and browser installation (prepared machines only)",
    )
    raw_argv = sys.argv[1:] if argv is None else list(argv)
    args = parser.parse_args(raw_argv)

    if not in_venv():
        reexec_in_venv(ensure_venv(), raw_argv)

    interpreter = Path(sys.executable)
    failed_stage = None
    failure_code = 0
    try:
        if not args.skip_install:
            run_stage(
                STAGE_INSTALL,
                [interpreter, "-m", "pip", "install", "-r", "requirements.txt"],
                REPO_ROOT,
            )
            run_stage(
                STAGE_INSTALL,
                [interpreter, "-m", "playwright", "install", "chromium"],
                REPO_ROOT,
            )
        derive_config()
        run_stage(STAGE_DOCTOR, [interpreter, str(REPO_ROOT / "main.py"), "doctor"], REPO_ROOT)
        run_stage(STAGE_TESTS, [interpreter, "-m", "pytest", "tests/"], REPO_ROOT)
        run_demo(interpreter)
    except StageFailure as exc:
        failed_stage = exc.stage
        failure_code = exc.returncode or 1
        log(f"[failed] {failed_stage}: {exc.detail}".rstrip(": "))
    except KeyboardInterrupt:
        failed_stage = "interrupted"
        failure_code = 130
        log("[failed] interrupted by user")

    if failed_stage:
        log(f"Deployment verification FAILED at stage '{failed_stage}'.")
        return failure_code

    log("=" * 60)
    log("Deployment verification PASSED:")
    if args.skip_install:
        log("  - dependencies & browser install: skipped (--skip-install)")
    else:
        log("  - dependencies & Playwright Chromium installed")
    log("  - config.json preserved or derived headless from example")
    log("  - doctor diagnostics passed")
    log("  - test suite passed")
    log("  - isolated offline demo produced a non-empty account ledger")
    log("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
