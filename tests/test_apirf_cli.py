"""Real CLI/discovery seam for the APIrf adapter, with execution faked."""
import sys
from unittest.mock import patch

from sites import discover_adapters
from sites.apirf import ApirfAdapter


def test_apirf_is_auto_discovered_without_registration_changes():
    adapters = discover_adapters()
    assert adapters["apirf"] is ApirfAdapter
    assert adapters["apirf"].requires_browser is False


def test_main_run_apirf_uses_discovered_adapter_and_count_without_network(monkeypatch, tmp_path):
    import main

    monkeypatch.setattr(sys, "argv", ["main.py", "--run", "apirf", "--count", "2"])
    monkeypatch.setattr(main, "load_config", lambda: {"output_dir": str(tmp_path)})

    with patch("core.runner.StandardRunner.execute_adapter", return_value=0) as execute:
        main.main()

    execute.assert_called_once_with(ApirfAdapter, count=2)
