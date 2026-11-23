"""Ticket #12: the read-only live-run preflight, exercised through the real CLI.

Every third-party call is answered by a local fake HTTP server, so the tests
are deterministic and never touch the network. The server records the verb and
headers of every request it receives: that is how "preflight never creates an
account" is enforced here -- a POST would fail the assertion, because guest
creation, upgrade and registration are all POSTs.
"""
import json
import os
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_PY = REPO_ROOT / "main.py"

MAILBOX_PROBE_PATH = "/v1/messages"
APIRF_PROBE_PATH = "/api/auth/me"
API_KEY = "preflight-fake-215-key-2f4c"

# Variables that would silently change the outcome of a CLI subprocess.
_SCRUBBED_ENV = (
    "APIRF_215_API_KEY",
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
    "PYTHONIOENCODING",
)


class FakeThirdParty:
    """Local HTTP server standing in for 215.im and APIrf.

    ``routes`` maps (method, path) to (status, json-body). Unrouted requests
    answer 404, which is exactly what a typo'd probe path should look like.
    """

    def __init__(self, routes):
        self.routes = dict(routes)
        self.log = []  # (method, path, headers, body)
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def _handle(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                outer.log.append((self.command, self.path, self.headers, body))
                status, payload = outer.routes.get(
                    (self.command, self.path.split("?")[0]),
                    (404, {"error": "not routed"}),
                )
                raw = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            do_GET = _handle
            do_POST = _handle
            do_PUT = _handle
            do_PATCH = _handle
            do_DELETE = _handle

            def log_message(self, *args):  # keep pytest output clean
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def __enter__(self):
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc_info):
        self._server.shutdown()
        self._server.server_close()

    def methods(self):
        return {entry[0] for entry in self.log}

    def paths(self):
        return [entry[1].split("?")[0] for entry in self.log]

    def header_for(self, path, name):
        for _method, requested, headers, _body in self.log:
            if requested.split("?")[0] == path:
                return headers.get(name)
        raise AssertionError(f"no request recorded for {path}")


def _write_config(directory: Path, base_url: str, *, api_key=API_KEY) -> Path:
    config = {
        "output_dir": str(directory / "results"),
        "apirf": {
            "http": {"trust_env": False},
            "mail": {"im215_api_key": api_key, "http_timeout_secs": 5},
            "preflight": {
                "im215_base_url": f"{base_url}/v1",
                "apirf_base_url": base_url,
                "timeout_secs": 5,
            },
        },
    }
    path = directory / "config.json"
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path


def _run_cli(workdir: Path, extra_env=None):
    env = {key: value for key, value in os.environ.items() if key not in _SCRUBBED_ENV}
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(REPO_ROOT) + (os.pathsep + existing if existing else "")
    env.update(extra_env or {})
    completed = subprocess.run(
        [sys.executable, str(MAIN_PY), "preflight"],
        cwd=str(workdir),
        env=env,
        capture_output=True,
        timeout=180,
    )
    output = (completed.stdout + completed.stderr).decode("utf-8", "replace")
    return completed.returncode, output


def _closed_port() -> int:
    """A port nothing is listening on: the 'network path unavailable' case."""
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


HEALTHY_ROUTES = {
    ("GET", MAILBOX_PROBE_PATH): (200, {"code": 200, "data": {"list": []}}),
    ("GET", APIRF_PROBE_PATH): (401, {"detail": "Unauthorized"}),
}


# ---------------------------------------------------------------------------
# Passing configuration, local and read-only
# ---------------------------------------------------------------------------

def test_passing_configuration_exits_zero_without_creating_an_account(tmp_path):
    with FakeThirdParty(HEALTHY_ROUTES) as fake:
        _write_config(tmp_path, fake.base_url)
        code, output = _run_cli(tmp_path)

        assert code == 0, output
        assert "Console encoding" in output
        assert "215.im credentials" in output
        assert "APIrf network path" in output
        assert "RESULT: Preflight passed" in output

        # Read-only by construction: only GETs ever left the process.
        assert fake.methods() == {"GET"}
        assert fake.paths() == [MAILBOX_PROBE_PATH, APIRF_PROBE_PATH]

        # ADR 0002: the key travels in the header only, never in the URL.
        assert fake.header_for(MAILBOX_PROBE_PATH, "X-API-Key") == API_KEY
        assert API_KEY not in "".join(fake.paths())

    # Diagnostics are secret-free.
    assert API_KEY not in output


def test_missing_mailbox_key_blocks_without_any_mailbox_request(tmp_path):
    with FakeThirdParty(HEALTHY_ROUTES) as fake:
        _write_config(tmp_path, fake.base_url, api_key="")
        code, output = _run_cli(tmp_path)

        assert code == 1, output
        assert "RESULT: 1 blocking failure" in output
        assert "im215_api_key" in output
        assert "APIRF_215_API_KEY" in output
        # Fail fast without spending a mailbox request (#7 behaviour).
        assert MAILBOX_PROBE_PATH not in fake.paths()


def test_rejected_mailbox_key_is_a_blocking_failure(tmp_path):
    routes = dict(HEALTHY_ROUTES)
    routes[("GET", MAILBOX_PROBE_PATH)] = (401, {"error": "invalid api key"})
    with FakeThirdParty(routes) as fake:
        _write_config(tmp_path, fake.base_url)
        code, output = _run_cli(tmp_path)

        assert code == 1, output
        assert "rejected" in output.lower()
        assert "401" in output
        assert API_KEY not in output


def test_unavailable_apirf_path_is_a_blocking_failure(tmp_path):
    port = _closed_port()
    _write_config(tmp_path, f"http://127.0.0.1:{port}")
    code, output = _run_cli(tmp_path)

    assert code == 1, output
    assert "APIrf network path" in output
    assert "unreachable" in output.lower()
    assert "Traceback" not in output


def test_legacy_console_encoding_blocks_the_cli(tmp_path):
    with FakeThirdParty(HEALTHY_ROUTES) as fake:
        _write_config(tmp_path, fake.base_url)
        code, output = _run_cli(tmp_path, {"PYTHONIOENCODING": "gbk"})

        assert code != 0, output
        assert "Console encoding" in output
        assert "started without UTF-8" in output
        assert "Traceback" not in output


# ---------------------------------------------------------------------------
# Console-encoding check: unit level, where a legacy codepage is reproducible
# ---------------------------------------------------------------------------

class _Stream:
    """Minimal stdout/stderr stand-in with a controllable encoding."""

    def __init__(self, encoding, repairable=False):
        self.encoding = encoding
        self._repairable = repairable
        self.reconfigured = []

    def reconfigure(self, **kwargs):
        if not self._repairable:
            raise AttributeError("reconfigure not supported")
        self.reconfigured.append(kwargs)
        self.encoding = kwargs.get("encoding", self.encoding)


def test_console_check_flags_a_codepage_it_cannot_repair():
    from core.preflight import check_console_encoding

    result = check_console_encoding(stdout=_Stream("cp1252"), stderr=_Stream("cp1252"))

    assert result.ok is False
    assert result.blocking is True
    assert "cp1252" in result.detail
    assert result.hint


def test_console_check_repairs_for_printing_but_still_blocks():
    from core.preflight import check_console_encoding

    stdout, stderr = _Stream("gbk", repairable=True), _Stream("gbk", repairable=True)
    result = check_console_encoding(stdout=stdout, stderr=stderr)

    assert result.ok is False
    assert "reconfigured for this process only" in result.detail
    assert stdout.encoding == "utf-8"
    assert stderr.encoding == "utf-8"
    assert "reconfigured" in result.detail.lower()
    assert stdout.reconfigured and stderr.reconfigured


@pytest.mark.parametrize("encoding", ["utf-8", "UTF8", "utf_8", "cp65001"])
def test_console_check_accepts_utf8_aliases(encoding):
    from core.preflight import check_console_encoding

    result = check_console_encoding(stdout=_Stream(encoding), stderr=_Stream(encoding))

    assert result.ok is True


# ---------------------------------------------------------------------------
# Probe semantics: which HTTP answers count as a pass
# ---------------------------------------------------------------------------

class _Response:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = ""


class _Session:
    def __init__(self, status_code):
        self.status_code = status_code
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _Response(self.status_code)


def _settings(**overrides):
    from core.preflight import PreflightSettings

    values = dict(
        api_key=API_KEY,
        im215_base_url="https://maliapi.215.im/v1",
        im215_probe_path=MAILBOX_PROBE_PATH,
        apirf_base_url="https://apirf.ru",
        apirf_probe_path=APIRF_PROBE_PATH,
        timeout_secs=5,
        trust_env=False,
    )
    values.update(overrides)
    return PreflightSettings(**values)


@pytest.mark.parametrize("status", [200, 204])
def test_mailbox_probe_accepts_only_explicit_success(status):
    from core.preflight import check_mailbox_probe

    result = check_mailbox_probe(_settings(), _Session(status))

    assert result.ok is True, result.detail


@pytest.mark.parametrize("status", [400, 422, 401, 403, 429, 404, 405, 500])
def test_mailbox_probe_treats_rejection_and_unusable_probes_as_blocking(status):
    from core.preflight import check_mailbox_probe

    result = check_mailbox_probe(_settings(), _Session(status))

    assert result.ok is False
    assert result.blocking is True
    assert str(status) in result.detail


@pytest.mark.parametrize("status", [200, 302, 401, 403])
def test_apirf_probe_accepts_any_answered_request(status):
    from core.preflight import check_network_path

    session = _Session(status)
    result = check_network_path(_settings(), session)

    assert result.ok is True, result.detail
    # A reachability probe must never chase a redirect into a state change.
    assert session.calls[0][1].get("allow_redirects") is False


@pytest.mark.parametrize("status", [404, 429, 500, 503])
def test_apirf_probe_blocks_on_unusable_answers(status):
    from core.preflight import check_network_path

    result = check_network_path(_settings(), _Session(status))

    assert result.ok is False
    assert result.blocking is True


# ---------------------------------------------------------------------------
# Structural guarantee: nothing but GET can leave the process
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("verb", ["request", "post", "put", "patch", "delete"])
def test_read_only_session_refuses_mutating_verbs(verb):
    from core.preflight import ReadOnlySession, ReadOnlyViolation

    guarded = ReadOnlySession(_Session(200))
    with pytest.raises(ReadOnlyViolation):
        getattr(guarded, verb)("https://apirf.ru/api/auth/guest")


def test_read_only_session_forwards_get():
    from core.preflight import ReadOnlySession

    inner = _Session(401)
    guarded = ReadOnlySession(inner)

    assert guarded.get("https://apirf.ru/api/auth/me").status_code == 401
    assert inner.calls[0][0] == "https://apirf.ru/api/auth/me"
