"""Sanitized mailbox polling diagnostics (ticket #11).

A confirmation email that is *received but unsupported* must produce
actionable, sanitized rejection diagnostics: provider, safe message
metadata and the rejected scheme / host / path.  Confirmation tokens,
passwords, cookie values and message bodies must never appear.

These tests drive the public seams only:

* ``analyze_apirf_confirmation_links`` -- the pure classifier.
* ``ApirfMailRouter.poll_for_confirmation`` -- the polling boundary that
  collects ``rejection_diagnostics`` and emits them immediately.
* ``ApirfAdapter.run`` -- the adapter that persists diagnostics into its
  pending-activation recovery record.
"""
import json
from unittest.mock import Mock

import pytest
import requests

from core.apirf_mail import (
    ApirfMailRouter,
    analyze_apirf_confirmation_links,
    format_rejection_diagnostic,
)

# A distinctly recognizable token: if it ever leaks into a diagnostic the
# assertions below fail loudly.
TOKEN = "tok_SUPERSECRET_9f8e7d6c5b4a3210"
CONFIRM_URL = "https://apirf.ru/api/auth/email/confirm/good-token"


# ---------------------------------------------------------------------------
# Pure classifier
# ---------------------------------------------------------------------------

def test_analyze_reports_safe_scheme_host_and_path_rejections():
    body = f"""
        <a href="http://apirf.ru/api/auth/email/confirm/{TOKEN}">insecure</a>
        <a href="https://evil.example/api/auth/email/confirm/{TOKEN}">wrong host</a>
        <a href="https://apirf.ru/api/auth/email/verify/{TOKEN}">wrong path</a>
    """

    link, rejections = analyze_apirf_confirmation_links(body)

    assert link is None
    assert {r["reason"] for r in rejections} == {
        "scheme_not_https",
        "host_not_allowed",
        "unexpected_path",
    }

    dumped = json.dumps(rejections)
    # The token never appears, but the actionable scheme/host/path do.
    assert TOKEN not in dumped
    assert "http" in dumped
    assert "evil.example" in dumped
    assert "/api/auth/email/verify" in dumped


def test_analyze_returns_valid_link_without_rejections():
    link, rejections = analyze_apirf_confirmation_links(
        f'<a href="{CONFIRM_URL}">Confirm</a>'
    )

    assert link == CONFIRM_URL
    assert rejections == []


def test_analyze_rejects_credentials_in_url_without_leaking_them():
    body = f'<a href="https://alice:hunter2@apirf.ru/api/auth/email/confirm/{TOKEN}">x</a>'

    link, rejections = analyze_apirf_confirmation_links(body)

    assert link is None
    assert rejections[0]["reason"] == "credentials_in_url"
    dumped = json.dumps(rejections)
    assert "alice" not in dumped
    assert "hunter2" not in dumped
    assert TOKEN not in dumped


def test_analyze_reports_missing_and_malformed_tokens():
    missing, rejections = analyze_apirf_confirmation_links(
        '<a href="https://apirf.ru/api/auth/email/confirm/">x</a>'
    )
    assert missing is None
    assert [r["reason"] for r in rejections] == ["missing_token"]

    malformed, rejections = analyze_apirf_confirmation_links(
        f'<a href="https://apirf.ru/api/auth/email/confirm/{TOKEN}/extra">x</a>'
    )
    assert malformed is None
    assert [r["reason"] for r in rejections] == ["malformed_token"]
    assert TOKEN not in json.dumps(rejections)


def test_analyze_deduplicates_repeated_candidates():
    # The same URL appears as a plain-text match and as an href; it must be
    # reported once, not twice.
    body = (
        f'Confirm https://evil.example/confirm/{TOKEN} '
        f'<a href="https://evil.example/confirm/{TOKEN}">again</a>'
    )

    link, rejections = analyze_apirf_confirmation_links(body)

    assert link is None
    assert len(rejections) == 1
    assert rejections[0]["reason"] == "host_not_allowed"


# ---------------------------------------------------------------------------
# Polling boundary
# ---------------------------------------------------------------------------

class FakeMailbox:
    def __init__(self, address="box@mail.example", messages=None):
        self.address = address
        self.messages = messages or []

    def create_mailbox(self):
        return self.address

    def check_messages(self):
        return self.messages

    def read_message(self, message_id):
        for message in self.messages:
            if message["id"] == message_id:
                return message.get("body", message.get("full_body", ""))
        return ""

    def recovery_data(self):
        return {"provider": "215.im", "address": self.address}


def _router(mailbox, reporter=None):
    return ApirfMailRouter(
        factories={"215.im": Mock(return_value=mailbox)},
        sleeper=lambda _: None,
        reporter=reporter,
    )


def test_poll_collects_sanitized_rejection_diagnostics_and_emits_them():
    emitted = []
    mailbox = FakeMailbox(messages=[{
        "id": "msg-1",
        "subject": "Подтвердите email",
        "from": "no-reply@apirf.ru",
        "body": f"Please confirm here: https://evil.example/confirm/{TOKEN}",
    }])
    router = _router(mailbox, reporter=emitted.append)
    router.create_mailbox()
    router.mark_submitted()

    assert router.poll_for_confirmation(timeout_secs=0.2, first_interval=0) is None

    diagnostics = router.rejection_diagnostics
    assert len(diagnostics) == 1
    diag = diagnostics[0]
    assert diag["provider"] == "215.im"
    assert diag["message_id"] == "msg-1"
    assert diag["metadata"] == {
        "subject": "Подтвердите email",
        "from": "no-reply@apirf.ru",
    }
    assert diag["rejections"][0]["reason"] == "host_not_allowed"
    assert diag["rejections"][0]["host"] == "evil.example"

    dumped = json.dumps(diagnostics, ensure_ascii=False)
    assert TOKEN not in dumped
    # The message body never appears in the diagnostic.
    assert "Please confirm here" not in dumped

    assert len(emitted) == 1
    assert TOKEN not in emitted[0]
    assert "evil.example" in emitted[0]


def test_poll_success_emits_no_diagnostics():
    emitted = []
    mailbox = FakeMailbox(messages=[{
        "id": "confirm",
        "subject": "Confirm email",
        "body": f"Click {CONFIRM_URL}",
    }])
    router = _router(mailbox, reporter=emitted.append)
    router.create_mailbox()
    router.mark_submitted()

    assert router.poll_for_confirmation(timeout_secs=0.2, first_interval=0) == CONFIRM_URL
    assert router.rejection_diagnostics == []
    assert emitted == []


def test_message_without_links_produces_no_diagnostic():
    emitted = []
    mailbox = FakeMailbox(messages=[{"id": "hello", "body": "Welcome, no links here."}])
    router = _router(mailbox, reporter=emitted.append)
    router.create_mailbox()
    router.mark_submitted()

    assert router.poll_for_confirmation(timeout_secs=0.2, first_interval=0) is None
    assert router.rejection_diagnostics == []
    assert emitted == []


def test_rejection_diagnostics_reset_between_polls():
    emitted = []
    mailbox = FakeMailbox(messages=[{"id": "m1", "body": "https://evil.example/a/b"}])
    router = _router(mailbox, reporter=emitted.append)
    router.create_mailbox()
    router.mark_submitted()

    router.poll_for_confirmation(timeout_secs=0.1, first_interval=0)
    router.poll_for_confirmation(timeout_secs=0.1, first_interval=0)

    # Each poll starts fresh; the same rejected message is not re-reported.
    assert len(router.rejection_diagnostics) == 1


def test_format_rejection_diagnostic_names_reason_and_target():
    diag = {
        "provider": "215.im",
        "message_id": "m1",
        "metadata": {"subject": "hi"},
        "rejections": [{
            "scheme": "https",
            "host": "evil.example",
            "path": "/api/auth/email/confirm/<redacted>",
            "reason": "host_not_allowed",
        }],
    }

    text = format_rejection_diagnostic(diag)

    assert "215.im" in text
    assert "host_not_allowed" in text
    assert "evil.example" in text
    assert "<redacted>" in text


# ---------------------------------------------------------------------------
# Adapter persistence seam
# ---------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, payload=None, status_code=200, text=""):
        self._payload = payload if payload is not None else {}
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.responses.pop(0)

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.responses.pop(0)


class RejectionRouter:
    """Router stub whose poll fails with pre-built sanitized diagnostics."""

    def __init__(self, diagnostics):
        self.create_calls = 0
        self.submitted = False
        self.rejection_diagnostics = diagnostics

    def create_mailbox(self):
        self.create_calls += 1
        return "box@mail.example"

    def mark_submitted(self):
        self.submitted = True

    def poll_for_confirmation(self, **kwargs):
        return None

    def recovery_data(self):
        return {"provider": "215.im", "address": "box@mail.example"}


def test_adapter_persists_sanitized_diagnostics_on_incomplete_confirmation(monkeypatch):
    from sites.apirf import ApirfAdapter

    monkeypatch.setattr("sites.apirf.generate_identity", lambda: {
        "username": "apirf_login",
        "email": "placeholder@local.dev",
        "password": "not-a-real-password!A1",
        "first_name": "Test",
        "last_name": "User",
    })
    diagnostics = [{
        "provider": "215.im",
        "message_id": "m1",
        "metadata": {"subject": "Подтвердите email"},
        "rejections": [{
            "scheme": "https",
            "host": "evil.example",
            "path": "/confirm/<redacted>",
            "reason": "host_not_allowed",
        }],
    }]
    router = RejectionRouter(diagnostics)
    adapter = ApirfAdapter(
        config={"apirf": {"confirmation_timeout_secs": 0}},
        session=FakeSession([FakeResponse(), FakeResponse()]),
        mail_router=router,
    )

    assert adapter.run() is False

    pending = adapter.pending_activation
    assert pending["stage"] == "confirmation"
    assert pending["diagnostics"] == diagnostics
    assert TOKEN not in json.dumps(pending, ensure_ascii=False)


def test_adapter_success_has_no_diagnostics(monkeypatch):
    from sites.apirf import ApirfAdapter

    monkeypatch.setattr("sites.apirf.generate_identity", lambda: {
        "username": "apirf_login",
        "email": "placeholder@local.dev",
        "password": "not-a-real-password!A1",
        "first_name": "Test",
        "last_name": "User",
    })

    class SuccessRouter(RejectionRouter):
        def poll_for_confirmation(self, **kwargs):
            return CONFIRM_URL

    router = SuccessRouter([])
    adapter = ApirfAdapter(
        config={"apirf": {"confirmation_timeout_secs": 0}},
        session=FakeSession([
            FakeResponse(),
            FakeResponse(),
            FakeResponse(),
            FakeResponse({"ok": True, "user": {"email_verified": True, "is_guest": False}}),
            FakeResponse({"ok": True, "user": {"email_verified": True, "is_guest": False}}),
        ]),
        mail_router=router,
    )

    assert adapter.run() is True
    assert adapter.pending_activation is None
