"""Read-only live-run preflight for the APIrf adapter (ticket #12).

Answers one question before a real run: is this machine ready? It checks the
console encoding, the 215.im credential through a read-only API call, and the
APIrf network path through a read-only endpoint. It never creates a guest,
never upgrades one and never registers anything: every third-party request is
a GET, enforced structurally by ReadOnlySession rather than by convention.

Import policy mirrors main.py: stdlib + requests only. Nothing here may pull
in Playwright or the adapter layer, because the preflight has to work on a
machine where the browser stack is not installed yet.
"""
from dataclasses import dataclass

import requests

from core.apirf_mail import DEFAULT_215_BASE_URL

APIRF_BASE_URL = "https://apirf.ru"

# Read-only probes. GET /v1/messages is the 215.im inbox listing: any answer
# that got past authentication proves the key is live, without creating a
# mailbox. GET /api/auth/me answers 401 without a session -- that 401 is the
# proof the APIrf network path works, so no login is needed either.
DEFAULT_IM215_PROBE_PATH = "/messages"
DEFAULT_APIRF_PROBE_PATH = "/api/auth/me"

# Statuses that mean "the request was authenticated and handled" for the
# mailbox probe. 400/422 are validation complaints about probe parameters,
# which still prove the credential itself was accepted.
_MAILBOX_ACCEPTED = {200, 204, 400, 422}
# Any answered request proves reachability; redirects are not followed.
_NETWORK_REACHABLE = {200, 302, 401, 403}


class ReadOnlyViolation(RuntimeError):
    """Raised when code tries to send a mutating request through the guard."""


class ReadOnlySession:
    """A session facade that exposes GET and refuses every mutating verb.

    Account creation on both APIrf and 215.im is a POST; blocking the verb at
    the session boundary makes "preflight never creates an account" a
    structural property, not a promise in a comment.
    """

    def __init__(self, session):
        self._session = session

    def get(self, url, **kwargs):
        return self._session.get(url, **kwargs)

    def _refuse(self, verb):
        def refused(*args, **kwargs):
            raise ReadOnlyViolation(
                f"preflight is read-only: HTTP {verb.upper()} is not allowed"
            )
        return refused

    post = property(lambda self: self._refuse("post"))
    put = property(lambda self: self._refuse("put"))
    patch = property(lambda self: self._refuse("patch"))
    delete = property(lambda self: self._refuse("delete"))


@dataclass
class PreflightSettings:
    api_key: str
    im215_base_url: str = DEFAULT_215_BASE_URL
    im215_probe_path: str = DEFAULT_IM215_PROBE_PATH
    apirf_base_url: str = APIRF_BASE_URL
    apirf_probe_path: str = DEFAULT_APIRF_PROBE_PATH
    timeout_secs: float = 20
    trust_env: bool = False


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    hint: str = ""
    blocking: bool = True


def _is_utf8(encoding) -> bool:
    if not encoding:
        return False
    normalized = str(encoding).lower().replace("-", "").replace("_", "")
    return normalized in {"utf8", "cp65001", "65001"}


def check_console_encoding(stdout=None, stderr=None) -> CheckResult:
    """Verify both console streams emit UTF-8, repairing them when possible.

    A legacy Windows codepage (GBK, cp1252, ...) mangles Chinese diagnostics
    and can crash prints outright. TextIOWrapper streams can be reconfigured
    in place; anything else must be fixed by the operator before a live run.
    """
    import sys

    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr

    bad = []
    repaired = []
    for label, stream in (("stdout", stdout), ("stderr", stderr)):
        encoding = getattr(stream, "encoding", None)
        if _is_utf8(encoding):
            continue
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            bad.append(f"{label}={encoding}")
            continue
        if _is_utf8(getattr(stream, "encoding", None)):
            repaired.append(label)
        else:
            bad.append(f"{label}={encoding}")

    if bad:
        return CheckResult(
            name="Console encoding",
            ok=False,
            detail="non-UTF-8 console streams: " + ", ".join(bad),
            hint="run 'chcp 65001' or set PYTHONIOENCODING=utf-8 / PYTHONUTF8=1 "
                 "before the live run",
        )
    detail = "stdout/stderr are UTF-8"
    if repaired:
        detail += f" ({', '.join(repaired)} reconfigured from a legacy codepage)"
    return CheckResult(name="Console encoding", ok=True, detail=detail)


def check_mailbox_probe(settings: PreflightSettings, session) -> CheckResult:
    """Validate the 215.im credential with a read-only inbox listing.

    The key travels only in the X-API-Key header (ADR 0002); it never appears
    in the URL, the payload or the diagnostics.
    """
    name = "215.im credentials"
    if not settings.api_key:
        return CheckResult(
            name=name,
            ok=False,
            detail="215.im API key is missing",
            hint="configure apirf.mail.im215_api_key in config.json or set the "
                 "APIRF_215_API_KEY environment variable",
        )

    url = settings.im215_base_url.rstrip("/") + settings.im215_probe_path
    try:
        response = session.get(
            url,
            headers={"X-API-Key": settings.api_key},
            timeout=settings.timeout_secs,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        return CheckResult(
            name=name,
            ok=False,
            detail=f"215.im unreachable: {exc.__class__.__name__}",
            hint="check the network/proxy path to maliapi.215.im",
        )

    status = response.status_code
    if status in _MAILBOX_ACCEPTED:
        return CheckResult(
            name=name,
            ok=True,
            detail=f"read-only probe answered HTTP {status}; credential accepted",
        )
    if status in (401, 403):
        return CheckResult(
            name=name,
            ok=False,
            detail=f"credential rejected by 215.im (HTTP {status})",
            hint="verify apirf.mail.im215_api_key / APIRF_215_API_KEY is a "
                 "current, valid key",
        )
    return CheckResult(
        name=name,
        ok=False,
        detail=f"read-only probe unusable (HTTP {status})",
        hint="check apirf.preflight.im215_base_url and the probe path; "
             "429 means rate-limited, 5xx means the provider is degraded",
    )


def check_network_path(settings: PreflightSettings, session) -> CheckResult:
    """Prove the APIrf network path with an unauthenticated read-only GET.

    /api/auth/me answers 401 without a session; receiving that answer is the
    success signal. Redirects are never followed, so the probe cannot wander
    into a state-changing flow.
    """
    name = "APIrf network path"
    url = settings.apirf_base_url.rstrip("/") + settings.apirf_probe_path
    try:
        response = session.get(
            url,
            timeout=settings.timeout_secs,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        return CheckResult(
            name=name,
            ok=False,
            detail=f"APIrf unreachable: {exc.__class__.__name__}",
            hint="check DNS/proxy/firewall for apirf.ru; the live run needs "
                 "this exact path",
        )

    status = response.status_code
    if status in _NETWORK_REACHABLE:
        return CheckResult(
            name=name,
            ok=True,
            detail=f"read-only probe answered HTTP {status}; path reachable",
        )
    return CheckResult(
        name=name,
        ok=False,
        detail=f"read-only probe unusable (HTTP {status})",
        hint="check apirf.preflight.apirf_base_url and the probe path; "
             "429 means rate-limited, 5xx means the site is degraded",
    )


def load_settings(config: dict) -> PreflightSettings:
    import os

    apirf = (config or {}).get("apirf", {}) or {}
    mail = apirf.get("mail", {}) or {}
    http = apirf.get("http", {}) or {}
    preflight = apirf.get("preflight", {}) or {}
    return PreflightSettings(
        api_key=(mail.get("im215_api_key") or os.environ.get("APIRF_215_API_KEY") or "").strip(),
        im215_base_url=preflight.get("im215_base_url", DEFAULT_215_BASE_URL),
        im215_probe_path=preflight.get("im215_probe_path", DEFAULT_IM215_PROBE_PATH),
        apirf_base_url=preflight.get("apirf_base_url", APIRF_BASE_URL),
        apirf_probe_path=preflight.get("apirf_probe_path", DEFAULT_APIRF_PROBE_PATH),
        timeout_secs=preflight.get("timeout_secs", mail.get("http_timeout_secs", 20)),
        trust_env=bool(http.get("trust_env", False)),
    )


def run_preflight(config: dict) -> bool:
    """Run all preflight checks, print a doctor-style report, return readiness.

    True means every check passed; False means at least one blocking failure.
    Only GET requests are ever issued, through a ReadOnlySession guard.
    """
    settings = load_settings(config)

    session = requests.Session()
    session.trust_env = settings.trust_env
    guarded = ReadOnlySession(session)

    results = [
        check_console_encoding(),
        check_mailbox_probe(settings, guarded),
        check_network_path(settings, guarded),
    ]

    print("=" * 65)
    print("  RegisterHub - APIrf Live-Run Preflight (read-only)")
    print("=" * 65)
    for result in results:
        label = "PASS" if result.ok else "FAIL"
        print(f"[{label}] {result.name}")
        print(f"       {result.detail}")

    failures = [r for r in results if not r.ok and r.blocking]
    print("-" * 65)
    if failures:
        print("Blocking issues:")
        for result in failures:
            print(f"  x {result.name}: {result.detail}")
            if result.hint:
                print(f"    -> {result.hint}")
        plural = "s" if len(failures) != 1 else ""
        print(f"RESULT: {len(failures)} blocking failure{plural} - NOT ready for a live run")
        return False

    print("RESULT: Preflight passed - configuration is ready (no account was created)")
    return True
