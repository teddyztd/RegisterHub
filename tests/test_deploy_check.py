import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest


def _load_deploy_check():
    script = Path(__file__).resolve().parent.parent / "scripts" / "deploy_check.py"
    spec = importlib.util.spec_from_file_location("deploy_check", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules["deploy_check"] = module
    spec.loader.exec_module(module)
    return module


deploy_check = _load_deploy_check()


def prepare_project(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    (root / "config.example.json").write_text(
        json.dumps(
            {
                "browser": {"headless": False, "slow_mo": 50},
                "output_dir": "./results",
                "defaults": {"country": "US"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(deploy_check, "REPO_ROOT", root)
    venv = root / ".venv"
    executable = venv / ("Scripts/python.exe" if deploy_check.os.name == "nt" else "bin/python")
    monkeypatch.setattr(deploy_check.sys, "prefix", str(venv))
    monkeypatch.setattr(deploy_check.sys, "executable", str(executable))
    return root, executable


def test_failed_doctor_derives_headless_config_and_stops(tmp_path, monkeypatch, capsys):
    root, executable = prepare_project(tmp_path, monkeypatch)
    run = Mock(return_value=subprocess.CompletedProcess(args=[], returncode=7))
    monkeypatch.setattr(deploy_check.subprocess, "run", run)

    result = deploy_check.main(["--skip-install"])

    assert result == 7
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    assert config == {
        "browser": {"headless": True, "slow_mo": 50},
        "output_dir": "./results",
        "defaults": {"country": "US"},
    }
    assert run.call_count == 1
    assert run.call_args.args[0] == [str(executable), str(root / "main.py"), "doctor"]
    assert run.call_args.kwargs == {"cwd": root, "check": False}
    assert "[failed] doctor" in capsys.readouterr().out


def fake_demo_run(command, **kwargs):
    """Simulate the demo's observable side effect: a non-empty ledger in its cwd."""
    if "--run" in command:
        results = Path(kwargs["cwd"]) / "results"
        results.mkdir(parents=True, exist_ok=True)
        (results / "accounts.txt").write_text(
            "demo@example.test----Secret123!----demouser\n", encoding="utf-8"
        )
    return subprocess.CompletedProcess(args=command, returncode=0)


def test_existing_config_is_preserved_untouched(tmp_path, monkeypatch, capsys):
    root, _ = prepare_project(tmp_path, monkeypatch)
    existing = {
        "browser": {"headless": False, "proxy": "http://127.0.0.1:7890"},
        "output_dir": "./results",
    }
    (root / "config.json").write_text(json.dumps(existing), encoding="utf-8")
    monkeypatch.setattr(deploy_check.subprocess, "run", Mock(side_effect=fake_demo_run))

    result = deploy_check.main(["--skip-install"])

    assert result == 0
    assert json.loads((root / "config.json").read_text(encoding="utf-8")) == existing
    assert "preserved" in capsys.readouterr().out


def test_full_success_runs_stages_in_order_and_isolates_demo(tmp_path, monkeypatch, capsys):
    root, executable = prepare_project(tmp_path, monkeypatch)
    calls = []
    captured = {}

    def record(command, **kwargs):
        calls.append((command, kwargs["cwd"]))
        if "--run" in command:
            captured["config"] = json.loads(
                (Path(kwargs["cwd"]) / "config.json").read_text(encoding="utf-8")
            )
        return fake_demo_run(command, **kwargs)

    monkeypatch.setattr(deploy_check.subprocess, "run", Mock(side_effect=record))

    result = deploy_check.main([])

    assert result == 0

    def stage_of(command):
        if "--run" in command:
            return "demo"
        if "-m" in command:
            return command[command.index("-m") + 1]
        if "doctor" in command:
            return "main.py"
        raise AssertionError(f"unexpected command: {command}")

    assert [stage_of(cmd) for cmd, _ in calls] == ["pip", "playwright", "main.py", "pytest", "demo"]
    demo_cwd = Path(calls[-1][1])
    assert demo_cwd != root
    assert demo_cwd.name.startswith("registerhub-deploy-demo-")
    assert not demo_cwd.exists(), "temporary demo directory must be cleaned up"
    assert captured["config"]["browser"]["headless"] is True
    assert Path(captured["config"]["output_dir"]) == demo_cwd / "results"
    assert not (root / "results" / "accounts.txt").exists()
    out = capsys.readouterr().out
    assert "[failed]" not in out
    assert "Deployment verification PASSED" in out


def test_empty_demo_ledger_is_failure(tmp_path, monkeypatch, capsys):
    root, _ = prepare_project(tmp_path, monkeypatch)

    def empty_demo(command, **kwargs):
        if "--run" in command:
            results = Path(kwargs["cwd"]) / "results"
            results.mkdir(parents=True, exist_ok=True)
            (results / "accounts.txt").write_text("", encoding="utf-8")
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(deploy_check.subprocess, "run", Mock(side_effect=empty_demo))

    assert deploy_check.main(["--skip-install"]) == 1
    assert "[failed] demo" in capsys.readouterr().out


def test_unknown_option_exits_2_with_usage():
    script = Path(__file__).resolve().parent.parent / "scripts" / "deploy_check.py"
    result = subprocess.run(
        [sys.executable, str(script), "--unknown-option"],
        cwd=script.parent.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "unrecognized arguments" in result.stderr


def test_outside_venv_creates_environment_then_reexecs(tmp_path, monkeypatch):
    root, executable = prepare_project(tmp_path, monkeypatch)
    monkeypatch.setattr(deploy_check.sys, "prefix", "C:/Python314")
    monkeypatch.setattr(deploy_check.sys, "base_prefix", "C:/Python314")
    created = []
    calls = []

    def fake_venv_create(directory, **kwargs):
        created.append(directory)
        path = Path(directory) / ("Scripts/python.exe" if deploy_check.os.name == "nt" else "bin/python")
        path.parent.mkdir(parents=True)
        path.write_text("", encoding="utf-8")

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(args=command, returncode=23)

    monkeypatch.setattr(deploy_check.venv, "create", fake_venv_create)
    monkeypatch.setattr(deploy_check.subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as exc_info:
        deploy_check.main(["--skip-install"])
    assert exc_info.value.code == 23
    assert created == [str(root / ".venv")]
    assert calls[0][0] == str(executable)
    assert calls[0][1].endswith("deploy_check.py")
    assert calls[0][-1] == "--skip-install"
    assert len(calls) == 1, "must re-exec once, not loop"
