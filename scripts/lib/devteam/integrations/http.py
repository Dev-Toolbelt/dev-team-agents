"""The one HTTP policy every integration adapter goes through.

* https only. The single exception is for tests: ``http://127.0.0.1`` or
  ``http://localhost`` when ``DEVTEAM_INTEGRATIONS_TEST_ALLOW_LOOPBACK_HTTP=1``.
* The credential is sent only to the exact scheme, host and port of the configured base
  URL. A redirect is followed only to that same origin; anything else is refused.
* 10 second socket timeout, a 20 second total deadline, 2 MB response cap, JSON only.
* :func:`request_json` (and :func:`post_json`, its POST form) follows no redirect at all: a
  request that moved is refused, never replayed as a GET. A caller may widen the loopback exception for its own test seam by passing
  ``allow_loopback_http=True`` (the account flow does so only when its seam is active,
  ADR-0029 SR-44); the integrations environment variable above stays the integrations seam.
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

    def __init__(self, state, summary, http_status=None, body=None, retry_after=None):
        super().__init__(summary)
        self.state = state
        self.summary = summary
        #: Seconds the server asked the caller to wait (``Retry-After``), when it sent a
        #: usable integer, else ``None``.
        self.retry_after = retry_after
        #: The HTTP status when the server answered, else ``None``.
        self.http_status = http_status
        #: The parsed JSON error body (a dict) when :func:`post_json` got one, else ``None``.
        self.body = body


def _loopback_allowed():
    return os.environ.get(LOOPBACK_ENV) == "1"


def validate_base_url(url, label="URL", allow_loopback_http=False):
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
        parsed.scheme == "http"
        and (allow_loopback_http or _loopback_allowed())
        and host in LOOPBACK_HOSTS
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


def _opener(base_origin, follow_redirects=True):
    def check(newurl):
        if not follow_redirects:
            raise FetchError("unreachable", "Refused a redirect on a POST request")
        try:
            target = origin(newurl)
        except ValueError:
            # A malformed redirect target (a bad port, say) is the server's fault, not
            # the token's: report it as such rather than letting it reach the header
            # handler below.
            raise FetchError("unreachable", "Refused a malformed redirect target") from None
        if target != base_origin:
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


def _retry_after(headers):
    try:
        value = int(str(headers.get("Retry-After", "")).strip())
    except ValueError:
        return None
    return value if 0 <= value <= 86400 else None


def _classify(exc):
    code = exc.code
    if code == 401:
        return FetchError("invalid_token", "The server rejected the token (HTTP 401)", code)
    if code in (403, 429):
        if _rate_limited(code, exc.headers):
            return FetchError(
                "rate_limited",
                "The API rate limit was reached (HTTP {})".format(code),
                code,
                retry_after=_retry_after(exc.headers),
            )
        return FetchError(
            "invalid_token",
            "Access denied (HTTP 403): the token lacks the needed permission",
            code,
        )
    return FetchError("unreachable", "The server answered HTTP {}".format(code), code)


def _error_body(exc):
    """The JSON object an error response carried, or ``None``. Capped like any body."""
    try:
        raw = exc.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            return None
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError, http.client.HTTPException):
        return None
    finally:
        exc.close()
    return parsed if isinstance(parsed, dict) else None


def _shrink_timeout(response, remaining):
    """Cap the socket's timeout at what is left of the deadline, so one blocking read
    cannot run past it. Best effort: the attribute path is an implementation detail."""
    sock = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
    if sock is not None:
        try:
            sock.settimeout(max(0.01, min(TIMEOUT, remaining)))
        except OSError:
            pass


def _read_capped(response, deadline):
    """The body, read in chunks so a drip-fed answer cannot outlive ``deadline``."""
    chunks, total = [], 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FetchError("unreachable", "The server did not answer in time")
        _shrink_timeout(response, remaining)
        chunk = response.read(min(CHUNK, MAX_RESPONSE_BYTES + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            break
    return b"".join(chunks)


def _send(request, base, deadline, follow_redirects, want_error_body, allow_empty=False):
    """Run ``request`` under the shared policy; returns ``(parsed_json, headers)``."""
    try:
        with _opener(origin(base), follow_redirects).open(request, timeout=TIMEOUT) as response:
            payload = _read_capped(response, deadline)
            response_headers = response.headers
    except urllib.error.HTTPError as exc:
        error = _classify(exc)
        if want_error_body:
            error.body = _error_body(exc)
        raise error from None
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
    if allow_empty and not payload.strip():
        return {}, response_headers
    try:
        data = json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise FetchError("unreachable", "The server answered with something that is not JSON") from None
    return data, response_headers


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
    return _send(request, base, deadline, True, False)


def request_json(
    method, base_url, path, headers, body=None, query=None, allow_loopback_http=False
):
    """One JSON request with any method; returns ``(parsed_json, headers)``.

    The account flow's general entry point (ADR-0029): same policy as :func:`get_json`
    (https only, one origin, 10 s socket timeout, 20 s deadline, 2 MB cap), **no redirect is
    followed**, an empty success body reads as ``{}``, and an HTTP error carries
    ``http_status``, ``retry_after`` and the parsed JSON error object in ``body`` so a caller
    can tell a wrong code from a rate limit without this module ever echoing the request
    into a message.
    """
    base = validate_base_url(base_url, "API URL", allow_loopback_http=allow_loopback_http)
    sent = {"Accept": "application/json", "User-Agent": USER_AGENT}
    data = None
    if body is not None:
        sent["Content-Type"] = "application/json"
        data = json.dumps(body, separators=(",", ":")).encode("utf-8")
    sent.update(headers)
    url = base + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(url, data=data, headers=sent, method=method)
    deadline = time.monotonic() + TOTAL_DEADLINE
    return _send(request, base, deadline, False, True, allow_empty=True)


def post_json(base_url, path, headers, body, allow_loopback_http=False):
    """``POST base_url + path`` with ``body`` as JSON; returns ``(parsed_json, headers)``.

    :func:`request_json` with the ``POST`` method. A body is always sent, so a caller that
    has nothing to say passes ``{}``.
    """
    return request_json(
        "POST", base_url, path, headers, body=body, allow_loopback_http=allow_loopback_http
    )
