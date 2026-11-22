"""
APIrf pure-HTTP registration adapter (feature: apirf-http-registration).

Implements docs/adr/0002: a single requests.Session drives the recorded
protocol against https://apirf.ru -- no browser, no Playwright:

    POST /api/auth/guest
    POST /api/auth/guest/upgrade      {login, password, email}
    GET  /api/auth/email/confirm/<token>   (link read from the mailbox)
    GET  /api/auth/me                 success iff email_verified is exactly
                                      True AND is_guest is exactly False

Safety properties:
* requires_browser = False -> Runner uses the protocol path, never launches
  a browser for this adapter.
* The mailbox address always comes from a real provider via ApirfMailRouter
  (215.im -> mail.tm -> tempmail.io -> guerrillamail, creation-time failover,
  pinned after submission). The identity generator's local.dev placeholder is
  never submitted.
* The emailed confirmation link is validated by the strict extractor
  (https + official apirf.ru host + exact confirm path) before any GET.
* Captcha / access-denied / rate-limit responses raise ApirfBlockedError
  (stop_run=True) so the Runner halts instead of retrying.
* Incomplete activations are reported through pending_activation (stage +
  mailbox recovery data) for later resumption; they are not successes.
"""
import os
from typing import Any, Dict, Optional

import requests

from core.adapter import BaseSiteAdapter
from core.identity import generate_identity
from core.apirf_mail import ApirfMailRouter, Im215Mailbox, extract_apirf_confirmation_link

APIRF_BASE_URL = "https://apirf.ru"

_BLOCKED_MARKERS = ("captcha", "access denied", "too many requests", "rate limit")


class ApirfBlockedError(RuntimeError):
    """Raised on captcha / access-denied / rate-limit responses.

    stop_run tells the Runner to halt the whole batch immediately rather than
    retrying into a WAF.
    """

    stop_run = True


class ApirfAdapter(BaseSiteAdapter):
    """Single-account APIrf protocol adapter (no browser)."""

    requires_browser = False

    def __init__(self, page=None, context=None, config: Optional[Dict[str, Any]] = None,
                 session: Optional[requests.Session] = None,
                 mail_router: Optional[ApirfMailRouter] = None):
        super().__init__(page, context, config)
        apirf_cfg = (config or {}).get("apirf", {})
        mail_cfg = apirf_cfg.get("mail", {})
        self.base_url = apirf_cfg.get("base_url", APIRF_BASE_URL).rstrip("/")
        self.timeout = mail_cfg.get("http_timeout_secs", 20)
        self.confirmation_timeout = mail_cfg.get("confirmation_timeout_secs", 300)
        self.session = session or requests.Session()
        self.mail_router = mail_router or self._build_default_router(mail_cfg)
        self.pending_activation: Optional[Dict[str, Any]] = None

    @staticmethod
    def _build_default_router(mail_cfg: Dict[str, Any]) -> ApirfMailRouter:
        """Build the production mailbox route from local config / environment.

        The 215.im API key is read from config or APIRF_215_API_KEY and passed
        only into the Im215Mailbox header path -- never logged or submitted to
        APIrf. A missing key makes 215.im fail at creation time and the route
        fails over to the public providers, exactly as the ADR requires.
        """
        api_key = mail_cfg.get("im215_api_key") or os.environ.get("APIRF_215_API_KEY", "")
        timeout = mail_cfg.get("http_timeout_secs", 20)
        factories = {
            "215.im": lambda: Im215Mailbox(api_key=api_key, timeout=timeout),
            # remaining providers use ApirfMailRouter's built-in public backends
        }
        router = ApirfMailRouter(timeout=timeout)
        router._factories = {**router._factories, **factories}
        order = mail_cfg.get("provider_order")
        if order:
            unknown = [name for name in order if name not in router._factories]
            if unknown:
                raise ValueError(f"Unknown apirf.mail.provider_order entries: {unknown}")
            router._order = list(order)
        return router

    # -- BaseSiteAdapter interface -----------------------------------------

    def target_url(self) -> str:
        return self.base_url + "/"

    def prepare_identity(self) -> Dict[str, Any]:
        """Generate synthetic credentials; email is replaced by the real
        provider-issued mailbox address inside run()."""
        self.account_data = generate_identity()
        return self.account_data

    def fill_form(self, identity: Dict[str, Any]) -> bool:  # protocol path has no form
        return True

    def submit_and_confirm(self) -> bool:  # protocol path has no form
        return True

    # -- protocol -----------------------------------------------------------

    def _check_blocked(self, response) -> None:
        text = (response.text or "").lower()
        if response.status_code in (403, 429) or any(marker in text for marker in _BLOCKED_MARKERS):
            raise ApirfBlockedError(
                f"APIrf blocked the request (HTTP {response.status_code}); stopping without retries"
            )

    def _post(self, path: str, **kwargs):
        response = self.session.post(self.base_url + path, timeout=self.timeout, **kwargs)
        self._check_blocked(response)
        response.raise_for_status()
        return response

    def _get(self, url: str):
        response = self.session.get(url, timeout=self.timeout)
        self._check_blocked(response)
        response.raise_for_status()
        return response

    def _set_pending(self, stage: str) -> None:
        self.pending_activation = {
            "stage": stage,
            "account": dict(self.account_data),
            "mailbox": self.mail_router.recovery_data(),
        }

    def run(self) -> bool:
        # 1. Guest session (mailbox is created only after this succeeds, so a
        #    blocked guest request never burns a mailbox).
        self._post("/api/auth/guest")

        # 2. Real provider-issued mailbox; local.dev placeholder is discarded.
        address = self.mail_router.create_mailbox()
        identity = self.prepare_identity()
        identity["email"] = address
        self.account_data["email"] = address

        # 3. Bind credentials to the guest session, then pin the mailbox route.
        self._post("/api/auth/guest/upgrade", json={
            "login": identity["username"],
            "password": identity["password"],
            "email": address,
        })
        self.mail_router.mark_submitted()

        # 4. Poll the pinned mailbox and follow only a strictly validated link.
        link = self.mail_router.poll_for_confirmation(timeout_secs=self.confirmation_timeout)
        if not link:
            self._set_pending("confirmation")
            return False
        if not extract_apirf_confirmation_link(f'href="{link}"'):
            self._set_pending("confirmation")
            return False
        self._get(link)

        # 5. Activation gate: exact booleans only.
        me = self._get(self.base_url + "/api/auth/me").json() or {}
        if me.get("email_verified") is True and me.get("is_guest") is False:
            return True
        self._set_pending("identity")
        return False
