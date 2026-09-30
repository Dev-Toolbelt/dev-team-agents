"""The one HTTP policy every integration adapter goes through.

* https only. The single exception is for tests: ``http://127.0.0.1`` or
  ``http://localhost`` when ``DEVTEAM_INTEGRATIONS_TEST_ALLOW_LOOPBACK_HTTP=1``.
* The credential is sent only to the exact scheme, host and port of the configured base
  URL. A redirect is followed only to that same origin; anything else is refused.
* 10 second socket timeout, a 20 second total deadline, 2 MB response cap, JSON only.
* A failure is a :class:`FetchError` carrying a *state* (``invalid_token``,
  ``rate_limited``, ``unreachable``) and a summary built here, never from the request:
  neither the token nor the Authorization header can appear in it.

The redirect guard itself lives in :mod:`..redirects`; this module hands it a same-origin
check.
"""

from __future__ import annotations

import http.client
import json
import os
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from ..errors import UsageError
from ..redirects import RestrictedRedirects

TIMEOUT = 10
TOTAL_DEADLINE = 20
CHUNK = 64 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
USER_AGENT = "devteam-cli"
LOOPBACK_ENV = "DEVTEAM_INTEGRATIONS_TEST_ALLOW_LOOPBACK_HTTP"
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
_DEFAULT_PORTS = {"https": 443, "http": 80}


class FetchError(Exception):
    """A request that did not produce a usable answer.

    ``state`` is one of ``invalid_token``, ``rate_limited``, ``unreachable``.
    """

    def __init__(self, state, summary):
        super().__init__(summary)
        self.state = state
        self.summary = summary


def _loopback_allowed():
    return os.environ.get(LOOPBACK_ENV) == "1"


def validate_base_url(url, label="URL"):
    """The normalised base URL (no trailing slash), or ``UsageError``."""
    if not isinstance(url, str) or not url.strip():
        raise UsageError("{} must not be empty".format(label))
    text = url.strip()
    try:
        parsed = urllib.parse.urlsplit(text)
        host = parsed.hostname
        parsed.port  # noqa: B018 - raises ValueError on a malformed port
    except ValueError:
        raise UsageError("{} is not a valid URL".format(label))
    scheme_ok = parsed.scheme == "https" or (
        parsed.scheme == "http" and _loopback_allowed() and host in LOOPBACK_HOSTS
    )
    if not scheme_ok:
        raise UsageError(
            "{} must be an https:// URL".format(label),
            hint="The token is only ever sent over https.",
        )
    if not host or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise UsageError(
            "{} must be a plain base URL (host and optional path only)".format(label)
        )
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def origin(url):
    """``(scheme, host, port)`` — what "the same origin" means here."""
    parsed = urllib.parse.urlsplit(url)
    scheme = parsed.scheme.lower()
    return (scheme, (parsed.hostname or "").lower(), parsed.port or _DEFAULT_PORTS.get(scheme))


def _opener(base_origin):
    def check(newurl):
        if origin(newurl) != base_origin:
            raise FetchError(
                "unreachable", "Refused a redirect to a different origin than the configured URL"
            )

    handlers = [RestrictedRedirects(check)]
    if base_origin[0] == "https":
        handlers.append(urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    else:
        # Loopback test server: never through an ambient proxy.
        handlers.append(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener(*handlers)


def _rate_limited(code, headers):
    if code == 429:
        return True
    if headers.get("Retry-After") is not None:
        return True
    return (headers.get("X-RateLimit-Remaining") or "").strip() == "0"


def _classify(exc):
    code = exc.code
    if code == 401:
        return FetchError("invalid_token", "The server rejected the token (HTTP 401)")
    if code in (403, 429):
        if _rate_limited(code, exc.headers):
            return FetchError("rate_limited", "The API rate limit was reached (HTTP {})".format(code))
        return FetchError(
            "invalid_token", "Access denied (HTTP 403): the token lacks the needed permission"
        )
    return FetchError("unreachable", "The server answered HTTP {}".format(code))


def _read_capped(response, deadline):
    """The body, read in chunks so a drip-fed answer cannot outlive ``deadline``."""
    chunks, total = [], 0
    while True:
        if time.monotonic() > deadline:
            raise FetchError("unreachable", "The server did not answer in time")
        chunk = response.read(min(CHUNK, MAX_RESPONSE_BYTES + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            break
    return b"".join(chunks)


def get_json(base_url, path, headers, query=None):
    """``GET base_url + path``; returns ``(parsed_json, response_headers)``."""
    base = validate_base_url(base_url, "API URL")
    url = base + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    sent = {"Accept": "application/json", "User-Agent": USER_AGENT}
    sent.update(headers)
    request = urllib.request.Request(url, headers=sent, method="GET")
    deadline = time.monotonic() + TOTAL_DEADLINE
    try:
        with _opener(origin(base)).open(request, timeout=TIMEOUT) as response:
            payload = _read_capped(response, deadline)
            response_headers = response.headers
    except urllib.error.HTTPError as exc:
        raise _classify(exc) from None
    except FetchError:
        raise
    except ValueError:
        # http.client refuses a header value with a control character or one that
        # cannot be latin-1 encoded; UnicodeError is a ValueError.
        raise FetchError(
            "invalid_token", "The stored token contains characters that cannot be sent in a header"
        ) from None
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, ssl.SSLError):
            raise FetchError("unreachable", "TLS error talking to the server") from None
        if isinstance(reason, socket.timeout):
            raise FetchError("unreachable", "The server did not answer in time") from None
        raise FetchError("unreachable", "Cannot reach the server") from None
    except (socket.timeout, TimeoutError):
        raise FetchError("unreachable", "The server did not answer in time") from None
    except ssl.SSLError:
        raise FetchError("unreachable", "TLS error talking to the server") from None
    except (OSError, http.client.HTTPException):
        raise FetchError("unreachable", "Cannot reach the server") from None
    if len(payload) > MAX_RESPONSE_BYTES:
        raise FetchError("unreachable", "The response is larger than the 2 MB cap")
    try:
        data = json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise FetchError("unreachable", "The server answered with something that is not JSON") from None
    return data, response_headers
