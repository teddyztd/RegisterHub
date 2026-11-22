"""Offline tests for the APIrf HTTP protocol and mailbox route."""
from typing import Any, Dict, List
from unittest.mock import Mock

import pytest
import requests

from core.mail_client import MailboxError, NoProviderAvailable
from core.apirf_mail import ApirfMailRouter, Im215Mailbox, extract_apirf_confirmation_link
from sites import discover_adapters
from sites.apirf import ApirfAdapter, ApirfBlockedError


CONFIRM_URL = "https://apirf.ru/api/auth/email/confirm/test-token"


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
    def __init__(self, responses: List[FakeResponse]):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.responses.pop(0)

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.responses.pop(0)


class FakeMailRouter:
    def __init__(self, confirmation_url=CONFIRM_URL):
        self.confirmation_url = confirmation_url
        self.address = "mailbox@mail.example"
        self.submitted = False
        self.create_calls = 0
        self.poll_calls = 0

    def create_mailbox(self):
        self.create_calls += 1
        return self.address

    def mark_submitted(self):
        self.submitted = True

    def poll_for_confirmation(self, **kwargs):
        self.poll_calls += 1
        return self.confirmation_url

    def recovery_data(self):
        return {"provider": "mail.tm", "address": self.address}


class FakeMailbox:
    def __init__(self, address="mailbox@mail.example", messages=None, error=None):
        self.address = address
        self.messages = messages or []
        self.error = error
        self.create_calls = 0
        self.read_ids = []

    def create_mailbox(self):
        self.create_calls += 1
        if self.error:
            raise self.error
        return self.address

    def check_messages(self):
        return self.messages

    def read_message(self, message_id):
        self.read_ids.append(message_id)
        for message in self.messages:
            if message["id"] == message_id:
                return message.get("full_body", message.get("body", ""))
        return ""

    def recovery_data(self):
        return {"address": self.address}


def identity_fixture():
    return {
        "username": "apirf_login",
        "email": "placeholder@local.dev",
        "password": "not-a-real-password!A1",
        "first_name": "Test",
        "last_name": "User",
    }


def make_adapter(session, router):
    return ApirfAdapter(
        config={"apirf": {"confirmation_timeout_secs": 0}},
        session=session,
        mail_router=router,
    )


def test_apirf_adapter_is_discoverable_and_does_not_require_a_browser():
    adapter_cls = discover_adapters()["apirf"]

    assert adapter_cls is ApirfAdapter
    assert adapter_cls.requires_browser is False


def test_full_protocol_uses_one_session_in_the_recorded_order(monkeypatch):
    session = FakeSession([
        FakeResponse({"id": "guest"}),
        FakeResponse({"email": "mailbox@mail.example"}),
        FakeResponse({"confirmed": True}),
        FakeResponse({"ok": True, "user": {"email_verified": True, "is_guest": False}}),
        FakeResponse({"ok": True, "user": {"email_verified": True, "is_guest": False}}),
    ])
    router = FakeMailRouter()
    monkeypatch.setattr("sites.apirf.generate_identity", identity_fixture)
    adapter = make_adapter(session, router)

    assert adapter.run() is True

    assert [(method, url) for method, url, _ in session.calls] == [
        ("POST", "https://apirf.ru/api/auth/guest"),
        ("POST", "https://apirf.ru/api/auth/guest/upgrade"),
        ("GET", CONFIRM_URL),
        ("POST", "https://apirf.ru/api/auth/login"),
        ("GET", "https://apirf.ru/api/auth/me"),
    ]
    assert "json" not in session.calls[0][2]
    assert session.calls[1][2]["json"] == {
        "login": "apirf_login",
        "password": "not-a-real-password!A1",
        "email": "mailbox@mail.example",
    }
    assert session.calls[3][2]["json"] == {
        "login": "apirf_login",
        "password": "not-a-real-password!A1",
    }
    assert router.submitted is True
    assert router.create_calls == 1
    assert adapter.account_data["email"] == "mailbox@mail.example"
    assert adapter.account_data["email"].split("@")[1] != "local.dev"


@pytest.mark.parametrize(
    "payload",
    [
        {"ok": True, "user": {"email_verified": False, "is_guest": False}},
        {"ok": True, "user": {"email_verified": True, "is_guest": True}},
        {"ok": True, "user": {"email_verified": 1, "is_guest": 0}},
        {"ok": True, "user": {}},
        {"ok": True, "email_verified": True, "is_guest": False},
        {},
    ],
)
def test_only_exact_verified_non_guest_identity_succeeds(monkeypatch, payload):
    session = FakeSession([
        FakeResponse(),
        FakeResponse(),
        FakeResponse(),
        FakeResponse({"ok": True, "user": {"email_verified": True, "is_guest": False}}),
        FakeResponse(payload),
    ])
    monkeypatch.setattr("sites.apirf.generate_identity", identity_fixture)
    adapter = make_adapter(session, FakeMailRouter())

    assert adapter.run() is False
    assert adapter.pending_activation["stage"] == "identity"
    assert adapter.account_data["email"] == "mailbox@mail.example"


def test_confirmation_timeout_does_not_call_confirmation_or_identity(monkeypatch):
    session = FakeSession([FakeResponse(), FakeResponse()])
    monkeypatch.setattr("sites.apirf.generate_identity", identity_fixture)
    adapter = make_adapter(session, FakeMailRouter(confirmation_url=None))

    assert adapter.run() is False

    assert len(session.calls) == 2
    assert adapter.pending_activation["stage"] == "confirmation"
    assert adapter.pending_activation["mailbox"]["address"] == "mailbox@mail.example"


@pytest.mark.parametrize(
    "url",
    [
        "http://apirf.ru/api/auth/email/confirm/token",
        "https://evil.example/api/auth/email/confirm/token",
        "https://www.apirf.ru/api/auth/email/confirm/token",
        "https://apirf.ru.evil.example/api/auth/email/confirm/token",
        "https://apirf.ru@evil.example/api/auth/email/confirm/token",
        "https://user@apirf.ru/api/auth/email/confirm/token",
        "https://apirf.ru:444/api/auth/email/confirm/token",
        "https://apirf.ru:bad/api/auth/email/confirm/token",
        "https://apirf.ru/api/auth/email/confirm/",
        "https://apirf.ru/api/auth/email/confirm/token/extra",
        "https://apirf.ru/api/auth/email/verify/token",
    ],
)
def test_confirmation_link_filter_rejects_unsafe_or_unintended_urls(url):
    assert extract_apirf_confirmation_link(f'<a href="{url}">confirm</a>') is None


def test_confirmation_link_filter_ignores_other_links_and_decodes_html():
    body = """
        <a href="https://apirf.ru/">welcome</a>
        <a href="https://tracker.example/click?url=https://apirf.ru/api/auth/email/confirm/fake">track</a>
        <a href="https://apirf.ru/api/auth/email/confirm/real-token?source=email&amp;lang=en">Confirm</a>
        <a href="https://apirf.ru/privacy">footer</a>
    """

    assert extract_apirf_confirmation_link(body) == (
        "https://apirf.ru/api/auth/email/confirm/real-token?source=email&lang=en"
    )


def test_confirmation_link_filter_accepts_the_real_web_form_link():
    """The live email links to /podtverdit?token=..., not the API path.

    The extractor normalizes it to the canonical API confirmation URL so the
    adapter can perform the actual confirmation action with a GET.
    """
    body = """
        <a href="https://apirf.ru/podtverdit?token=9wTjAjq2dDMskuv3Xm3BbzuPVrYrLEZf"
           style="background:#c9ec4d">Подтвердить email</a>
    """

    assert extract_apirf_confirmation_link(body) == (
        "https://apirf.ru/api/auth/email/confirm/9wTjAjq2dDMskuv3Xm3BbzuPVrYrLEZf"
    )


def test_confirmation_link_filter_accepts_the_real_web_form_plain_text_link():
    body = "Подтвердите email: https://apirf.ru/podtverdit?token=9wTjAjq2dDMskuv3Xm3BbzuPVrYrLEZf\n"

    assert extract_apirf_confirmation_link(body) == (
        "https://apirf.ru/api/auth/email/confirm/9wTjAjq2dDMskuv3Xm3BbzuPVrYrLEZf"
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://apirf.ru/podtverdit",
        "https://apirf.ru/podtverdit?token=",
        "https://apirf.ru/podtverdit?other=1",
        "https://apirf.ru/podtverdit?token=a/b",
        "https://evil.example/podtverdit?token=abc",
        "http://apirf.ru/podtverdit?token=abc",
        "https://www.apirf.ru/podtverdit?token=abc",
        "https://apirf.ru:444/podtverdit?token=abc",
        "https://user@apirf.ru/podtverdit?token=abc",
    ],
)
def test_confirmation_link_filter_rejects_unsafe_web_form_links(url):
    assert extract_apirf_confirmation_link(f'<a href="{url}">confirm</a>') is None


def test_mailbox_creation_falls_back_in_the_required_order():
    primary = FakeMailbox(error=MailboxError("missing key"))
    secondary = FakeMailbox(address="second@mail.example")
    unused = FakeMailbox(address="unused@mail.example")
    factories = {
        "215.im": Mock(return_value=primary),
        "mail.tm": Mock(return_value=secondary),
        "tempmail.io": Mock(return_value=unused),
        "guerrillamail": Mock(return_value=unused),
    }
    router = ApirfMailRouter(factories=factories)

    assert router.create_mailbox() == "second@mail.example"
    assert router.provider == "mail.tm"
    assert [name for name, factory in factories.items() if factory.called] == ["215.im", "mail.tm"]
    assert unused.create_calls == 0


def test_mailbox_creation_never_returns_a_local_placeholder_when_all_providers_fail():
    factories = {
        name: Mock(return_value=FakeMailbox(error=MailboxError("offline")))
        for name in ("215.im", "mail.tm", "tempmail.io", "guerrillamail")
    }
    router = ApirfMailRouter(factories=factories)

    with pytest.raises(NoProviderAvailable):
        router.create_mailbox()

    assert router.active_address is None


def test_submitted_mailbox_is_pinned_for_polling_and_cannot_be_replaced():
    mailbox = FakeMailbox(messages=[
        {"id": "welcome", "body": "https://apirf.ru/"},
        {"id": "confirm", "full_body": f"Click {CONFIRM_URL}"},
    ])
    factories = {
        "215.im": Mock(return_value=mailbox),
        "mail.tm": Mock(side_effect=AssertionError("must not switch provider")),
    }
    router = ApirfMailRouter(factories=factories, sleeper=lambda _: None)
    assert router.create_mailbox() == mailbox.address
    router.mark_submitted()

    with pytest.raises(MailboxError, match="already submitted"):
        router.create_mailbox()

    assert router.poll_for_confirmation(timeout_secs=1, first_interval=0) == CONFIRM_URL
    assert mailbox.read_ids == ["confirm"]
    assert factories["mail.tm"].call_count == 0


def test_215_mailbox_uses_api_key_only_in_header_and_returns_real_address():
    session = FakeSession([
        FakeResponse({"success": True, "data": {"address": "real@mail.example", "token": "temp-token"}}),
        FakeResponse({"success": True, "data": [{"id": "msg-1"}]}),
        FakeResponse({"success": True, "data": {"subject": "Confirm", "text": "body", "html": ["<p>html</p>", "<a href='https://apirf.ru/api/auth/email/confirm/token'>confirm</a>"]}}),
    ])
    mailbox = Im215Mailbox(api_key="AC-test-secret", session=session)

    assert mailbox.create_mailbox() == "real@mail.example"
    assert mailbox.check_messages() == [{"id": "msg-1"}]
    assert mailbox.read_message("msg-1") == "Confirm\nbody\n<p>html</p>\n<a href='https://apirf.ru/api/auth/email/confirm/token'>confirm</a>"

    method, url, kwargs = session.calls[0]
    assert (method, url) == ("POST", "https://maliapi.215.im/v1/accounts")
    assert kwargs["headers"]["X-API-Key"] == "AC-test-secret"
    assert "AC-test-secret" not in str(kwargs["json"])
    assert "domain" not in kwargs["json"] or kwargs["json"]["domain"] != "local.dev"
    for _, _, read_kwargs in session.calls[1:]:
        assert read_kwargs["headers"]["X-API-Key"] == "AC-test-secret"
        assert read_kwargs["headers"]["Authorization"] == "Bearer temp-token"


@pytest.mark.parametrize("status_code,text", [(403, "Access denied"), (429, "Too many requests"), (200, "Captcha required")])
def test_captcha_access_denial_and_rate_limit_stop_without_retries(monkeypatch, status_code, text):
    session = FakeSession([FakeResponse(status_code=status_code, text=text)])
    monkeypatch.setattr("sites.apirf.generate_identity", identity_fixture)
    adapter = make_adapter(session, FakeMailRouter())

    with pytest.raises(ApirfBlockedError) as exc_info:
        adapter.run()

    assert exc_info.value.stop_run is True
    assert len(session.calls) == 1
    assert router_not_created(adapter)


def router_not_created(adapter):
    return adapter.mail_router.create_calls == 0


def test_adapter_default_session_bypasses_system_proxy():
    adapter = ApirfAdapter(config={"apirf": {}})

    assert adapter.session.trust_env is False


def test_adapter_trust_env_true_keeps_system_proxy():
    adapter = ApirfAdapter(config={"apirf": {"http": {"trust_env": True}}})

    assert adapter.session.trust_env is True


def test_adapter_does_not_reconfigure_an_injected_session():
    session = FakeSession([])
    adapter = make_adapter(session, FakeMailRouter())

    assert adapter.session is session
    assert not hasattr(session, "trust_env")


def test_215_mailbox_session_honors_trust_env_flag():
    assert Im215Mailbox(api_key="k")._session.trust_env is True
    assert Im215Mailbox(api_key="k", trust_env=False)._session.trust_env is False


def test_public_mail_backend_can_force_direct_connection():
    router = ApirfMailRouter(trust_env=False)
    backend = router._factories["mail.tm"]()

    assert backend._client.proxies == {"http": None, "https": None}
