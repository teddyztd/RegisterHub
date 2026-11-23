"""
APIrf pure-HTTP registration adapter (feature: apirf-http-registration).

Implements docs/adr/0002: a single requests.Session drives the recorded
protocol against https://apirf.ru -- no browser, no Playwright:

    POST /api/auth/guest
    POST /api/auth/guest/upgrade      {login, password, email}
    GET  /api/auth/email/confirm/<token>   (link read from the mailbox)
    POST /api/auth/login              {login, password}
    GET  /api/auth/me                 success iff user.email_verified is
                                      exactly True AND user.is_guest is
                                      exactly False

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
from core.mail_client import MailboxError
from core.apirf_mail import (
    APIRF_MAIL_PROVIDER_ORDER,
    ApirfMailRouter,
    Im215Mailbox,
    extract_apirf_confirmation_link,
)

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
        http_cfg = apirf_cfg.get("http", {})
        # APIrf has a single fixed target origin; config cannot redirect the
        # registration protocol to another host.
        self.base_url = APIRF_BASE_URL
        self.timeout = mail_cfg.get("http_timeout_secs", 20)
        self.confirmation_timeout = mail_cfg.get("confirmation_timeout_secs", 300)
        # Direct connection by default: apirf.http.trust_env=False makes the
        # session ignore Windows system / environment proxies (a broken local
        # proxy aborts the TLS handshake). An injected session is left as-is.
        self.trust_env = http_cfg.get("trust_env", False)
        self.session = session or self._new_session(self.trust_env)
        self.mail_router = mail_router or self._build_default_router(mail_cfg, self.trust_env)
        self.pending_activation: Optional[Dict[str, Any]] = None

    @staticmethod
    def _new_session(trust_env: bool) -> requests.Session:
        session = requests.Session()
        session.trust_env = trust_env
        return session

    @staticmethod
    def _build_default_router(mail_cfg: Dict[str, Any], trust_env: bool = False) -> ApirfMailRouter:
        """Build the production mailbox route from local config / environment.

        The 215.im API key is read from config or APIRF_215_API_KEY and passed
        only into the Im215Mailbox header path -- never logged or submitted to
        APIrf.

        APIrf sends confirmation mail only to 215.im's own domains, so the
        public disposable providers cannot serve as fallbacks: a missing key
        fails here, before any HTTP request, instead of burning the whole
        confirmation timeout on a mailbox that will never receive anything.
        """
        api_key = mail_cfg.get("im215_api_key") or os.environ.get("APIRF_215_API_KEY", "")
        if not api_key:
            raise MailboxError(
                "APIrf requires the 215.im mailbox: set APIRF_215_API_KEY "
                "(or apirf.mail.im215_api_key in config.json). Public providers "
                "(mail.tm / tempmail.io / guerrillamail) never receive APIrf "
                "confirmation mail, so the run stops before contacting APIrf."
            )
        timeout = mail_cfg.get("http_timeout_secs", 20)
        factories = {
            "215.im": lambda: Im215Mailbox(api_key=api_key, timeout=timeout, trust_env=trust_env),
        }
        return ApirfMailRouter(
            factories=factories,
            timeout=timeout,
            trust_env=trust_env,
            provider_order=list(APIRF_MAIL_PROVIDER_ORDER),
        )

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
        self._set_pending("confirmation")

        # 4. Poll the pinned mailbox and follow only a strictly validated link.
        link = self.mail_router.poll_for_confirmation(timeout_secs=self.confirmation_timeout)
        if not link:
            # Persist the sanitized rejection diagnostics so a received-but-
            # unsupported confirmation email is reported immediately in the
            # pending-activation record (provider, safe message metadata and
            # rejection reasons; never tokens, credentials or bodies).
            diagnostics = self.mail_router.rejection_diagnostics
            if diagnostics:
                self._set_pending("confirmation")
                self.pending_activation["diagnostics"] = list(diagnostics)
            return False
        if not extract_apirf_confirmation_link(f'href="{link}"'):
            return False
        self._get(link)
        self._set_pending("identity")

        # 5. Establish an authenticated session after email confirmation. The
        # upgraded guest cookie is not sufficient for the final identity gate.
        self._post("/api/auth/login", json={
            "login": identity["username"],
            "password": identity["password"],
        })

        # 6. Activation gate: exact booleans only, read from the user object
        # in /api/auth/me on the same session. The login response body is not
        # trusted for this decision.
        payload = self._get(self.base_url + "/api/auth/me").json() or {}
        me = payload.get("user") if isinstance(payload, dict) else None
        if not isinstance(me, dict):
            me = {}
        if me.get("email_verified") is True and me.get("is_guest") is False:
            self.pending_activation = None
            return True
        self._set_pending("identity")
        return False
