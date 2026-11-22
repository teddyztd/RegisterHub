"""Runner integration tests for the APIrf no-browser protocol path."""
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from core.runner import StandardRunner
from sites.apirf import ApirfBlockedError


def make_runner(tmp_path):
    return StandardRunner(config={"output_dir": str(tmp_path), "browser": {"headless": True}})


def attach_cookie(session):
    cookie = requests.cookies.create_cookie(
        name="session",
        value="cookie-value",
        domain="apirf.ru",
        path="/",
        expires=1893456000,
        secure=True,
        rest={"HttpOnly": True, "SameSite": "Lax"},
    )
    session.cookies.set_cookie(cookie)


class SuccessAdapter:
    requires_browser = False
    instantiations = 0

    def __init__(self, page, context, config):
        type(self).instantiations += 1
        self.account_data = {
            "email": "real@mail.example",
            "password": "pw",
            "username": "apirf_login",
        }
        self.session = requests.Session()
        attach_cookie(self.session)
        self.pending_activation = None

    def run(self):
        return True


class PendingAdapter(SuccessAdapter):
    def run(self):
        self.pending_activation = {
            "stage": "confirmation",
            "account": dict(self.account_data),
            "mailbox": {"provider": "mail.tm", "address": "real@mail.example"},
        }
        return False


class BlockedAdapter(SuccessAdapter):
    runs = 0

    def run(self):
        type(self).runs += 1
        raise ApirfBlockedError("captcha")


class CrashingAdapter(SuccessAdapter):
    """Adapter whose post-binding phase raises a generic exception.

    pending_activation is set in the constructor, mirroring an adapter that
    reached confirmation/identity before the crash, so the runner's exception
    path must preserve the recovery record.
    """

    def __init__(self, page, context, config):
        super().__init__(page, context, config)
        self.pending_activation = {
            "stage": "identity",
            "account": dict(self.account_data),
            "mailbox": {"provider": "215.im", "address": "real@mail.example"},
        }

    def run(self):
        raise RuntimeError("identity verification exploded")


def test_protocol_success_never_starts_browser_and_exports_ledger_and_cookies(tmp_path):
    SuccessAdapter.instantiations = 0
    runner = make_runner(tmp_path)

    with patch("core.runner.sync_playwright", side_effect=AssertionError("browser must not start")):
        assert runner.execute_adapter(SuccessAdapter, count=1) == 1

    ledger = (tmp_path / "accounts.txt").read_text(encoding="utf-8")
    assert ledger == "real@mail.example----pw----apirf_login\n"

    cookie_file = tmp_path / "cookies" / "apirf_login.json"
    cookies = json.loads(cookie_file.read_text(encoding="utf-8"))
    assert cookies == [{
        "name": "session",
        "value": "cookie-value",
        "domain": "apirf.ru",
        "path": "/",
        "expires": 1893456000,
        "httpOnly": True,
        "secure": True,
        "sameSite": "Lax",
    }]
    assert not (tmp_path / "pending_activation").exists()


def test_protocol_success_without_cookies_does_not_write_success_ledger(tmp_path):
    class EmptyCookieAdapter(SuccessAdapter):
        def __init__(self, page, context, config):
            super().__init__(page, context, config)
            self.session = requests.Session()

    runner = make_runner(tmp_path)
    with patch("core.runner.sync_playwright", side_effect=AssertionError("browser must not start")):
        assert runner.execute_adapter(EmptyCookieAdapter, count=1) == 0

    assert not (tmp_path / "accounts.txt").exists()
    assert not (tmp_path / "cookies").exists()
    assert "no session cookies" in (tmp_path / "failed.txt").read_text(encoding="utf-8")


def test_pending_activation_writes_recovery_record_without_success_or_cookies(tmp_path):
    runner = make_runner(tmp_path)

    with patch("core.runner.sync_playwright", side_effect=AssertionError("browser must not start")):
        assert runner.execute_adapter(PendingAdapter, count=1) == 0

    assert not (tmp_path / "accounts.txt").exists()
    assert not (tmp_path / "cookies").exists()
    record_file = tmp_path / "pending_activation" / "apirf_login.json"
    record = json.loads(record_file.read_text(encoding="utf-8"))
    assert record["stage"] == "confirmation"
    assert record["account"]["email"] == "real@mail.example"
    assert record["mailbox"] == {"provider": "mail.tm", "address": "real@mail.example"}
    assert record["recorded_at"]


def test_protocol_exception_preserves_pending_recovery_record(tmp_path):
    runner = make_runner(tmp_path)

    with patch("core.runner.sync_playwright", side_effect=AssertionError("browser must not start")):
        assert runner.execute_adapter(CrashingAdapter, count=1) == 0

    assert not (tmp_path / "accounts.txt").exists()
    assert not (tmp_path / "cookies").exists()
    record_file = tmp_path / "pending_activation" / "apirf_login.json"
    record = json.loads(record_file.read_text(encoding="utf-8"))
    assert record["stage"] == "identity"
    assert record["mailbox"] == {"provider": "215.im", "address": "real@mail.example"}
    assert "identity verification exploded" in (tmp_path / "failed.txt").read_text(encoding="utf-8")


def test_protocol_rejects_bulk_count_before_creating_accounts(tmp_path):
    SuccessAdapter.instantiations = 0
    runner = make_runner(tmp_path)

    with pytest.raises(ValueError, match="one account per run"):
        runner.execute_adapter(SuccessAdapter, count=2)

    assert SuccessAdapter.instantiations == 0
    assert not (tmp_path / "accounts.txt").exists()


def test_blocked_protocol_stops_without_retrying(tmp_path):
    BlockedAdapter.runs = 0
    BlockedAdapter.instantiations = 0
    runner = make_runner(tmp_path)

    with patch("core.runner.sync_playwright", side_effect=AssertionError("browser must not start")):
        assert runner.execute_adapter(BlockedAdapter, count=1) == 0

    assert BlockedAdapter.runs == 1
    assert BlockedAdapter.instantiations == 1
    assert not (tmp_path / "accounts.txt").exists()
    assert "captcha" in (tmp_path / "failed.txt").read_text(encoding="utf-8")


def test_adapter_without_protocol_marker_still_uses_browser_path(tmp_path):
    class BrowserAdapter:
        pass

    runner = make_runner(tmp_path)
    with patch.object(StandardRunner, "_execute_browser_adapter", return_value=7) as browser_path:
        assert runner.execute_adapter(BrowserAdapter, count=2) == 7

    browser_path.assert_called_once_with(BrowserAdapter, 2)

def test_cookie_and_pending_filenames_are_sanitized(tmp_path):
    from core.runner import StandardRunner

    assert StandardRunner._safe_filename("apirf_login") == "apirf_login"
    assert StandardRunner._safe_filename("user/..\\bad*name") == "user_.._bad_name"
    assert StandardRunner._safe_filename("") == "account"
