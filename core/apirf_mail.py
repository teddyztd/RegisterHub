"""
APIrf temporary-mail routing policy (feature: apirf-http-registration).

Implements the Mailbox Route required by docs/adr/0002:

* Provider order is fixed: 215.im (X-API-Key), mail.tm, tempmail.io, guerrillamail.
* Failover happens at mailbox CREATION time only. Once an address has been
  submitted to APIrf (`mark_submitted()`), polling stays bound to that mailbox
  and creating a replacement is a hard error -- silently switching mailboxes
  would strand the confirmation mail.
* Every provider must return a REAL address issued by its API. No provider may
  fabricate a local placeholder address; if all providers fail the router
  raises NoProviderAvailable so callers stop instead of writing a dead mailbox
  into a signup form.

215.im backend follows https://vip.215.im/docs: base https://maliapi.215.im/v1,
account creation via POST /v1/accounts with the API key sent only in the
X-API-Key header (the key never appears in payloads or logs).
"""
import html as html_module
import re
import sys
import time
import urllib.parse
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

from core.mail_client import (
    DisposableMailClient,
    MailboxError,
    NoProviderAvailable,
)

# ---------------------------------------------------------------------------
# Strict confirmation-link extraction + sanitized rejection diagnostics
# ---------------------------------------------------------------------------

APIRF_CONFIRM_HOSTS = ("apirf.ru",)
APIRF_CONFIRM_PATH = "/api/auth/email/confirm/"
APIRF_CONFIRM_WEB_PATH = "/podtverdit"

# Only http/https candidates count as confirmation-link attempts. Relative
# hrefs, mailto:, tel:, javascript: and bare fragments are ordinary page
# furniture, not the emailed confirmation link, so they are ignored rather than
# reported as rejections.
_LINK_SCHEMES = frozenset(("http", "https"))

_LINK_HREF_RE = re.compile(
    r"""href\s*=\s*(?:
        "(?P<dq>[^"]*)"          |   # double-quoted
        '(?P<sq>[^']*)'          |   # single-quoted
        (?P<bare>[^\s>]+)            # unquoted
    )""",
    re.VERBOSE | re.IGNORECASE,
)
_PLAIN_URL_RE = re.compile(r"(?<![\w=?&])https://[^\s<>\"']+", re.IGNORECASE)

# A long unbroken run of URL-safe characters is treated as an opaque secret
# (confirmation token, API key...) and redacted wherever it could otherwise
# surface: rejected path tails and safe message metadata. Secret-shaped query
# parameters are redacted at any length via _SECRET_PARAM_RE.
_TOKEN_RUN_RE = re.compile(r"[A-Za-z0-9_\-]{16,}")
# Secret-bearing query parameters are redacted regardless of value length, so
# a short token in ``?token=abc123`` cannot leak through safe metadata.
_SECRET_PARAM_RE = re.compile(
    r"(?i)\b(token|key|secret|code|password|pass|pwd)=([^&\s\"']+)"
)
_REDACTED = "<redacted>"

# Envelope fields that are safe to report: they never carry the confirmation
# token, the account password, a cookie value, or the message body.
MESSAGE_METADATA_KEYS = ("subject", "from", "to", "date", "created_at", "received_at")


def _iter_unescaped_candidates(text: str) -> List[str]:
    """Return unique HTML-unescaped link candidates, in extractor order."""
    if not text:
        return []
    raw_candidates: List[str] = [m.group(0) for m in _PLAIN_URL_RE.finditer(text)]
    for match in _LINK_HREF_RE.finditer(text):
        raw = (match.group("dq") or match.group("sq") or match.group("bare") or "").strip()
        if raw:
            raw_candidates.append(raw)
    seen = set()
    ordered: List[str] = []
    for raw in raw_candidates:
        candidate = html_module.unescape(raw)
        if candidate in seen:
            continue
        seen.add(candidate)
        ordered.append(candidate)
    return ordered


def _redacted_path(parsed: "urllib.parse.SplitResult") -> str:
    """Return a token-free view of a URL path.

    The confirmation token lives either in the suffix after the confirm path or
    in the web-form query string. The suffix is always redacted and the query is
    never included; for any other multi-segment path the last segment is
    redacted so a foreign ``/verify/<token>`` style link cannot leak a secret.
    """
    path = urllib.parse.unquote(parsed.path or "") or "/"
    if path.startswith(APIRF_CONFIRM_PATH):
        return APIRF_CONFIRM_PATH + _REDACTED
    if path == APIRF_CONFIRM_WEB_PATH:
        return path
    segments = path.split("/")
    if len(segments) > 2:
        segments[-1] = _REDACTED
        return "/".join(segments)
    return path


def _rejection(parsed: "urllib.parse.SplitResult", reason: str) -> Dict[str, str]:
    """Build a safe rejection record: scheme, host and token-free path only."""
    try:
        host = parsed.hostname or ""
    except ValueError:  # malformed authority in an untrusted email
        host = ""
    return {
        "scheme": parsed.scheme or "",
        "host": host,
        "path": _redacted_path(parsed),
        "reason": reason,
    }


def _classify_candidate(candidate: str) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """Classify one candidate: (accepted_url, None) or (None, safe rejection)."""
    parsed = urllib.parse.urlsplit(candidate)
    if parsed.scheme != "https":
        return None, _rejection(parsed, "scheme_not_https")
    if parsed.hostname not in APIRF_CONFIRM_HOSTS:
        return None, _rejection(parsed, "host_not_allowed")
    if parsed.username or parsed.password:
        return None, _rejection(parsed, "credentials_in_url")
    try:
        port = parsed.port
    except ValueError:  # malformed port in an untrusted email
        return None, _rejection(parsed, "malformed_port")
    if port is not None and port != 443:
        return None, _rejection(parsed, "unexpected_port")

    path = urllib.parse.unquote(parsed.path or "")
    if path.startswith(APIRF_CONFIRM_PATH):
        token = path[len(APIRF_CONFIRM_PATH):]
        if not token:
            return None, _rejection(parsed, "missing_token")
        if "/" in token:
            return None, _rejection(parsed, "malformed_token")
        return candidate, None

    # The live email links to the web form /podtverdit?token=... rather than the
    # API path. Normalize it to the canonical API confirmation URL so the
    # adapter's GET performs the actual confirmation, and reject a missing token
    # or a token containing path separators.
    if path == APIRF_CONFIRM_WEB_PATH:
        query = urllib.parse.parse_qs(parsed.query or "")
        token = (query.get("token") or [""])[0]
        if not token:
            return None, _rejection(parsed, "missing_token")
        if "/" in token:
            return None, _rejection(parsed, "malformed_token")
        return (
            f"https://{parsed.hostname}{APIRF_CONFIRM_PATH}"
            f"{urllib.parse.quote(token, safe='')}"
        ), None

    return None, _rejection(parsed, "unexpected_path")


def analyze_apirf_confirmation_links(text: str) -> Tuple[Optional[str], List[Dict[str, str]]]:
    """Return ``(confirmation_url, rejections)`` for one email body.

    ``confirmation_url`` is the first accepted APIrf confirmation link, or None.
    When no link is accepted, ``rejections`` holds one safe record per
    unsupported http(s) candidate, naming the rejected scheme, host and
    token-free path plus a machine-readable reason. Tokens, credentials, query
    values and the message body are never included.
    """
    rejections: List[Dict[str, str]] = []
    for candidate in _iter_unescaped_candidates(text):
        link, rejection = _classify_candidate(candidate)
        if link is not None:
            return link, []
        if rejection is not None:
            rejections.append(rejection)
    return None, rejections


def extract_apirf_confirmation_link(text: str) -> Optional[str]:
    """Return the single APIrf email-confirmation URL, or None.

    A URL is accepted only when, after HTML-entity decoding, its parsed form is
    an https URL on the official APIrf host with the exact confirmation path
    prefix and a non-empty token. Redirectors, trackers, www variants, other
    ports/paths, credentials-in-URL and unrelated links are all rejected.
    """
    return analyze_apirf_confirmation_links(text)[0]


# ---------------------------------------------------------------------------
# Sanitized polling diagnostics
# ---------------------------------------------------------------------------

def _redact_token_runs(value: Any) -> Any:
    if isinstance(value, str):
        value = _SECRET_PARAM_RE.sub(
            lambda match: match.group(1) + "=" + _REDACTED, value
        )
        return _TOKEN_RUN_RE.sub(_REDACTED, value)
    return value


def _safe_message_metadata(message: Dict[str, Any]) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {}
    for key in MESSAGE_METADATA_KEYS:
        value = message.get(key)
        if value:
            metadata[key] = _redact_token_runs(str(value))
    return metadata


def format_rejection_diagnostic(diagnostic: Dict[str, Any]) -> str:
    """Render one sanitized rejection diagnostic as a printable report block."""
    provider = diagnostic.get("provider") or "unknown"
    message_id = diagnostic.get("message_id")
    metadata = diagnostic.get("metadata") or {}

    header = f"[mailbox] {provider}: received message"
    if message_id:
        header += f" {message_id}"
    header += " but no supported confirmation link"

    details: List[str] = []
    for key in MESSAGE_METADATA_KEYS:
        value = metadata.get(key)
        if value:
            details.append(f"{key}={value!r}")
    if details:
        header += " (" + ", ".join(details) + ")"

    lines = [header]
    for rejection in diagnostic.get("rejections") or []:
        scheme = rejection.get("scheme") or ""
        host = rejection.get("host") or ""
        path = rejection.get("path") or ""
        if scheme or host:
            target = f"{scheme}://{host}{path}"
        else:
            target = path
        lines.append(f"  rejected {rejection.get('reason', 'unknown')}: {target}")
    return "\n".join(lines)


def _default_reporter(line: str) -> None:
    print(line, file=sys.stderr)


# ---------------------------------------------------------------------------
# 215.im primary provider
# ---------------------------------------------------------------------------

DEFAULT_215_BASE_URL = "https://maliapi.215.im/v1"


class Im215Mailbox:
    """Temporary inbox backed by the YYDS Mail (215.im) REST API.

    Args:
        api_key:       X-API-Key value; resolved from local config or the
                       environment by the caller, never committed or logged.
        session:       Optional requests.Session (dependency injection).
        base_url:      Override for tests / alternate deployments.
        timeout:       Per-request timeout in seconds.
    """

    name = "215.im"

    def __init__(self, api_key: str, session: Optional[requests.Session] = None,
                 base_url: str = DEFAULT_215_BASE_URL, timeout: int = 20,
                 trust_env: bool = True):
        if not api_key:
            raise MailboxError("215.im API key is missing (configure apirf.mail.im215_api_key or APIRF_215_API_KEY)")
        self._session = session or requests.Session()
        if session is None:
            self._session.trust_env = trust_env
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._api_key = api_key
        self._token: Optional[str] = None
        self.active_address: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        headers = {"X-API-Key": self._api_key}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def create_mailbox(self) -> str:
        response = self._session.post(
            f"{self._base}/accounts",
            json={},
            headers=self._headers(),
            timeout=self._timeout,
        )
        if response.status_code >= 400:
            raise MailboxError(f"215.im create failed: HTTP {response.status_code} {response.text[:120]}")
        try:
            data = (response.json() or {}).get("data") or {}
        except ValueError as exc:
            raise MailboxError(f"215.im returned a non-JSON create response: {exc}") from exc

        address = data.get("address")
        token = data.get("token")
        if not address or "@" not in address:
            raise MailboxError("215.im returned no usable address")
        if not token:
            raise MailboxError("215.im returned no inbox token")
        self.active_address = address
        self._token = token
        return address

    def check_messages(self) -> List[Dict[str, Any]]:
        if not self.active_address:
            return []
        response = self._session.get(
            f"{self._base}/messages",
            params={"address": self.active_address},
            headers=self._headers(),
            timeout=self._timeout,
        )
        if response.status_code >= 400:
            return []
        try:
            payload = response.json() or {}
        except ValueError:
            return []
        messages = payload.get("data") or {}
        if isinstance(messages, dict):
            messages = messages.get("list") or messages.get("messages") or []
        return list(messages or [])

    def read_message(self, message_id: Any) -> str:
        response = self._session.get(
            f"{self._base}/messages/{message_id}",
            params={"address": self.active_address},
            headers=self._headers(),
            timeout=self._timeout,
        )
        if response.status_code >= 400:
            return ""
        try:
            data = (response.json() or {}).get("data") or {}
        except ValueError:
            return ""
        html = data.get("html", "")
        if isinstance(html, list):
            html = "\n".join(str(part) for part in html)
        return "\n".join(str(part) for part in [data.get("subject", ""), data.get("text", ""), html] if part)

    def recovery_data(self) -> Dict[str, Any]:
        return {"provider": self.name, "address": self.active_address}


# ---------------------------------------------------------------------------
# Ordered Mailbox Route
# ---------------------------------------------------------------------------

PROVIDER_ORDER = ("215.im", "mail.tm", "tempmail.io", "guerrillamail")

# APIrf only delivers confirmation mail to mailboxes on 215.im's own domains.
# The public disposable providers (mail.tm / tempmail.io / guerrillamail) never
# receive it, so the APIrf route must not treat them as usable fallbacks: a
# run that lands there burns the whole confirmation timeout before failing.
APIRF_MAIL_PROVIDER_ORDER = ("215.im",)


class ApirfMailRouter:
    """Creation-time failover mailbox route for the APIrf adapter.

    Args:
        factories:  Optional provider-name -> zero-arg factory returning a
                    mailbox object exposing create_mailbox()/check_messages()/
                    read_message()/recovery_data(). Defaults to the built-in
                    backends; test code injects fakes here.
        sleeper:    Poll sleep hook (dependency injection for tests).
        provider_order: Optional ordered provider names subset of PROVIDER_ORDER.
    """

    def __init__(self, factories: Optional[Dict[str, Callable[[], Any]]] = None,
                 sleeper: Callable[[float], None] = time.sleep,
                 provider_order: Optional[List[str]] = None,
                 proxies: Optional[Dict[str, str]] = None,
                 timeout: int = 20, trust_env: bool = True,
                 reporter: Optional[Callable[[str], None]] = None):
        self._factories = {
            **self.default_factories(proxies, timeout, trust_env),
            **(factories or {}),
        }
        names = provider_order or list(PROVIDER_ORDER)
        unknown = [name for name in names if name not in PROVIDER_ORDER]
        if unknown:
            raise MailboxError(f"Unknown mailbox providers: {unknown}; allowed: {PROVIDER_ORDER}")
        self._order = names
        self._sleeper = sleeper
        self._reporter = reporter if reporter is not None else _default_reporter
        self._mailbox: Optional[Any] = None
        self._submitted = False
        self.provider: Optional[str] = None
        self.active_address: Optional[str] = None
        # Sanitized diagnostics for messages received but rejected during the
        # most recent poll. Reset at the start of every poll; tokens, bodies
        # and credentials never enter these records.
        self.rejection_diagnostics: List[Dict[str, Any]] = []

    @staticmethod
    def default_factories(proxies: Optional[Dict[str, str]], timeout: int,
                           trust_env: bool = True) -> Dict[str, Callable[[], Any]]:
        """Built-in provider factories. Failures surface as exceptions -- no
        local placeholder address is ever fabricated."""

        def _make_215() -> Any:
            return Im215Mailbox(api_key="", timeout=timeout)  # guarded by explicit factory in adapter

        return {
            "215.im": _make_215,
            "mail.tm": lambda: _PublicBackend("mail.tm", proxies, timeout, trust_env),
            "tempmail.io": lambda: _PublicBackend("tempmail.io", proxies, timeout, trust_env),
            "guerrillamail": lambda: _PublicBackend("guerrillamail", proxies, timeout, trust_env),
        }

    # -- creation -----------------------------------------------------------

    def create_mailbox(self) -> str:
        """Acquire a mailbox, failing over in order BEFORE APIrf submission.

        After mark_submitted() this method refuses to run: the confirmed
        address is pinned and polling must stay on that mailbox.
        """
        if self._submitted:
            raise MailboxError(
                "Mailbox route is pinned: the address was already submitted to APIrf and may not be replaced"
            )

        errors: List[str] = []
        for name in self._order:
            try:
                mailbox = self._factories[name]()
                address = mailbox.create_mailbox()
                if not address or "@" not in address:
                    raise MailboxError(f"{name} returned a malformed address: {address!r}")
            except KeyError:
                errors.append(f"{name}: no factory registered")
                continue
            except Exception as exc:  # noqa: BLE001 - provider-level failure must not abort the route
                errors.append(f"{name}: {type(exc).__name__}: {str(exc)[:110]}")
                continue

            self._mailbox = mailbox
            self.active_address = address
            self.provider = name
            return address

        detail = "\n  ".join(errors) or "no provider attempted"
        raise NoProviderAvailable("All temporary-mail providers failed. Tried:\n  " + detail)

    def mark_submitted(self) -> None:
        """Pin the route once the address has been sent to APIrf."""
        if not self.active_address:
            raise MailboxError("mark_submitted() requires a created mailbox")
        self._submitted = True

    # -- polling ------------------------------------------------------------

    def poll_for_confirmation(self, timeout_secs: int = 300,
                              first_interval: float = 3.0,
                              max_interval: float = 10.0) -> Optional[str]:
        """Poll the pinned mailbox for the APIrf confirmation link.

        Returns the confirmed URL, or None when the mailbox stays silent until
        the deadline. Never calls any provider other than the pinned mailbox.
        """
        if not self._submitted:
            raise MailboxError("poll_for_confirmation() must run after mark_submitted()")

        deadline = time.time() + timeout_secs
        interval = first_interval
        processed_message_ids = set()
        self.rejection_diagnostics = []

        while time.time() < deadline:
            try:
                messages = self._mailbox.check_messages()
            except Exception:  # noqa: BLE001 - transient read errors are retried on the next tick
                messages = []
            for message in messages:
                message_id = message.get("id")
                if message_id in processed_message_ids:
                    continue
                body = message.get("body")
                if not body:
                    try:
                        body = self._mailbox.read_message(message_id)
                    except Exception:  # retry this message on the next poll
                        body = ""
                if not body:
                    continue
                processed_message_ids.add(message_id)
                link, rejections = analyze_apirf_confirmation_links(body)
                if link:
                    return link
                if rejections:
                    diagnostic = {
                        "provider": self.provider,
                        "message_id": message_id,
                        "metadata": _safe_message_metadata(message),
                        "rejections": rejections,
                    }
                    self.rejection_diagnostics.append(diagnostic)
                    self._reporter(format_rejection_diagnostic(diagnostic))
            self._sleeper(interval)
            interval = min(interval * 1.3, max_interval)

        return None

    def recovery_data(self) -> Dict[str, Any]:
        if self._mailbox is not None:
            try:
                return self._mailbox.recovery_data()
            except Exception:  # noqa: BLE001
                pass
        return {"provider": self.provider, "address": self.active_address}


class _PublicBackend:
    """Thin adapter over the existing DisposableMailClient public providers.

    Guarantees a provider-issued address: DisposableMailClient raises
    NoProviderAvailable instead of fabricating a local placeholder, which is
    exactly the behaviour the ADR requires.
    """

    def __init__(self, provider: str, proxies: Optional[Dict[str, str]], timeout: int,
                 trust_env: bool = True):
        self.name = provider
        self._client = DisposableMailClient(timeout=timeout, providers=[provider])
        if proxies is not None:
            self._client.proxies = proxies
        elif not trust_env:
            # Explicit per-scheme None makes requests bypass system/env proxies.
            self._client.proxies = {"http": None, "https": None}

    def create_mailbox(self) -> str:
        return self._client.create_mailbox()

    def check_messages(self) -> List[Dict[str, Any]]:
        return self._client.check_messages()

    def read_message(self, message_id: Any) -> str:
        return self._client.read_message(message_id)

    def recovery_data(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "address": self._client.active_address,
        }
