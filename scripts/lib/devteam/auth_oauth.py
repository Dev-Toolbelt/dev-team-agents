"""OAuth through the system browser: PKCE and a one-shot loopback listener (ADR-0029, SR-1..6).

The CLI never embeds a webview and never registers a URL scheme. It opens the authorize URL
in the user's own browser and waits on ``http://127.0.0.1:<port>/callback``:

* PKCE only (S256). The verifier is 32 bytes from :mod:`secrets`, base64url without padding;
  the access and refresh tokens arrive in the body of the token exchange, never in a URL.
* ``state`` is 128 bits or more, rides in the ``redirect_to`` query, and is compared in
  constant time. A callback with a missing or wrong ``state`` gets a 400 and the wait goes on.
* The listener binds ``127.0.0.1`` exactly, on an OS-assigned port (a fixed range is the
  fallback when that fails), serves ``GET /callback`` only, requires ``Host`` to be that
  address and port (DNS rebinding), and closes after the first valid callback, after the
  timeout, or on Ctrl-C, releasing the port on every path.
* The page it answers with is static, loads nothing, and carries no code or token.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import http.server
import os
import secrets
import time
import urllib.parse
import webbrowser

from . import paths
from .errors import EnvError

HOST = "127.0.0.1"
CALLBACK_PATH = "/callback"
CALLBACK_TIMEOUT = 300.0
FALLBACK_PORTS = tuple(range(53682, 53691))
_POLL_SECONDS = 0.25
_REQUEST_TIMEOUT = 5.0
_MAX_CODE_LENGTH = 2048

PROVIDERS = ("google", "github")
#: GitHub may hide the email address; this scope is what lets the server read the primary one.
PROVIDER_SCOPES = {"github": "user:email"}

_SECURITY_HEADERS = (
    ("Cache-Control", "no-store"),
    ("Referrer-Policy", "no-referrer"),
    ("Content-Security-Policy", "default-src 'none'"),
    ("X-Content-Type-Options", "nosniff"),
    ("Connection", "close"),
)

_PAGE = (
    "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
    "<title>{title}</title></head><body><main><h1>{title}</h1><p>{body}</p></main></body></html>"
)
_PAGES = {
    "ok": ("Signed in", "You can close this tab and return to your terminal."),
    "failed": ("Sign-in did not complete", "Return to your terminal and try again."),
    "bad": ("Request not recognised", "This page only answers the sign-in redirect."),
}


def _b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def new_pkce():
    """``(verifier, challenge)``: a fresh verifier per attempt and its S256 challenge (SR-1)."""
    verifier = _b64url(secrets.token_bytes(32))
    return verifier, _b64url(hashlib.sha256(verifier.encode("ascii")).digest())


def new_state():
    return _b64url(secrets.token_bytes(24))


def can_open_browser(environ=None, platform=None):
    """False on a machine with no display to open a browser on (a headless SSH session)."""
    env = os.environ if environ is None else environ
    system = platform or paths.platform_key()
    if system == "linux":
        return bool(env.get("DISPLAY") or env.get("WAYLAND_DISPLAY"))
    return True


def open_browser(url):
    """Hand ``url`` to the system browser; ``False`` when nothing could be started."""
    try:
        return bool(webbrowser.open(url, new=2))
    except webbrowser.Error:
        return False


class _Handler(http.server.BaseHTTPRequestHandler):
    timeout = _REQUEST_TIMEOUT
    server_version = "devteam"
    sys_version = ""
    protocol_version = "HTTP/1.0"

    def log_message(self, *args):
        pass

    def _reply(self, code, page):
        title, body = _PAGES[page]
        raw = _PAGE.format(title=title, body=body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        for key, value in _SECURITY_HEADERS:
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(raw)

    def _reject(self):
        self._reply(404, "bad")

    do_POST = do_PUT = do_DELETE = do_PATCH = do_HEAD = do_OPTIONS = _reject

    def do_GET(self):
        server = self.server
        parsed = urllib.parse.urlsplit(self.path)
        if self.headers.get("Host") != server.expected_host or parsed.path != CALLBACK_PATH:
            return self._reject()
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        given = (query.get("state") or [""])[0]
        if not hmac.compare_digest(given.encode("utf-8"), server.state.encode("utf-8")):
            return self._reply(400, "bad")
        code = (query.get("code") or [""])[0]
        if "error" in query or not code or len(code) > _MAX_CODE_LENGTH:
            server.outcome = {"failed": True}
            return self._reply(400, "failed")
        server.outcome = {"code": code}
        self._reply(200, "ok")


class _Server(http.server.HTTPServer):
    allow_reuse_address = False

    def handle_error(self, request, client_address):
        pass


class Listener:
    """The loopback listener for one sign-in attempt."""

    def __init__(self, state):
        self.state = state
        self.server = self._bind()
        self.port = self.server.server_address[1]
        self.server.expected_host = "{}:{}".format(HOST, self.port)
        self.server.state = state
        self.server.outcome = None
        self.server.timeout = _POLL_SECONDS

    @staticmethod
    def _bind():
        for port in (0,) + FALLBACK_PORTS:
            try:
                return _Server((HOST, port), _Handler)
            except OSError:
                continue
        raise EnvError(
            "cannot open a local port for the sign-in redirect",
            hint="Free a port in 53682-53690, or sign in with `devteam auth login --email`.",
            details={"reason": "no_port"},
        )

    @property
    def redirect_to(self):
        return "http://{}:{}{}?{}".format(
            HOST, self.port, CALLBACK_PATH, urllib.parse.urlencode({"state": self.state})
        )

    def wait(self, timeout=None):
        """The callback's outcome: ``{"code": ...}`` or ``{"failed": True}``.

        Raises :class:`EnvError` on timeout. Ctrl-C propagates; either way the caller closes.
        """
        deadline = time.monotonic() + (CALLBACK_TIMEOUT if timeout is None else timeout)
        while self.server.outcome is None:
            if time.monotonic() >= deadline:
                raise EnvError(
                    "timed out waiting for the browser sign-in",
                    hint="Run the command again, or sign in with `devteam auth login --email`.",
                    details={"reason": "timeout"},
                )
            self.server.handle_request()
        return self.server.outcome

    def close(self):
        self.server.server_close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def authorize_url(base, provider, redirect_to, challenge):
    query = {
        "provider": provider,
        "redirect_to": redirect_to,
        "code_challenge": challenge,
        "code_challenge_method": "s256",
    }
    if provider in PROVIDER_SCOPES:
        query["scopes"] = PROVIDER_SCOPES[provider]
    return "{}/auth/v1/authorize?{}".format(base, urllib.parse.urlencode(query))
