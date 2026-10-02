"""The identity server's wire protocol, and the input rules that sit in front of it (ADR-0029).

Everything that talks to GoTrue or to the two Edge Functions goes through :class:`Client`,
which sits on :mod:`integrations.http` (https only, one origin, deadlines, body cap, no
redirect on a request that carries a body). Three rules shape this module:

* **No response body ever reaches a message** (SR-18). A failure is translated to one of a
  few fixed messages from the HTTP status alone; the parsed error body is read only to tell
  a rate limit from a rejection, never echoed.
* **No enumeration** (SR-10). Every rejection of a credential or a code is the same fixed
  text, whether the address is unknown, unconfirmed, banned or the secret is wrong.
* **The identity endpoint is a constant** (SR-8): the base URL, the project key and the
  seam flag come from :class:`entitlement.Identity` and nothing here reads anything else.

Nothing in this module imports telemetry, and no request carries a telemetry id (SR-41):
the only header besides the standard ones is the project's public ``apikey``.
"""

from __future__ import annotations

import re
import unicodedata

from .errors import EXIT_ENVIRONMENT, DevteamError, EnvError, UsageError
from .integrations import http as http_policy

#: GoTrue's configured code length (``otp_length`` in ``infra/supabase/config.toml``, SR-12).
CODE_LENGTH = 8
PASSWORD_MIN_CHARS = 10
PASSWORD_MAX_CHARS = 64
#: bcrypt, which GoTrue hashes with, ignores everything past byte 72 (SR-15).
PASSWORD_MAX_BYTES = 72
DISPLAY_NAME_MAX = 80

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_CODE_RE = re.compile(r"^[0-9]{%d}$" % CODE_LENGTH)
_UUID_RE = re.compile(r"^[0-9A-Za-z-]{8,64}$")

REASON_INVALID_CREDENTIALS = "invalid_credentials"
REASON_INVALID_CODE = "invalid_code"
REASON_SESSION_EXPIRED = "session_expired"
REASON_REJECTED = "rejected"
REASON_NOT_SIGNED_IN = "not_signed_in"
REASON_RATE_LIMITED = "rate_limited"
REASON_UNREACHABLE = "unreachable"
REASON_NOT_CONFIGURED = "not_configured"

#: One fixed sentence per reason. Nothing from a response is ever added to these.
MESSAGES = {
    REASON_INVALID_CREDENTIALS: "invalid credentials",
    REASON_INVALID_CODE: "the code is invalid or has expired",
    REASON_SESSION_EXPIRED: "the session is no longer valid",
    REASON_REJECTED: "the account server rejected the request",
    REASON_NOT_SIGNED_IN: "you are not signed in",
}


class Rejected(DevteamError):
    """The server answered no: a wrong credential or code, a dead session, a refused call.

    Exit ``1``: the command ran and reported a problem it could not fix, the same meaning
    exit ``1`` has everywhere else in the CLI. ``reason`` is the stable machine-readable code.
    """

    def __init__(self, reason, message=None, hint=None, details=None):
        merged = dict(details or {})
        merged["reason"] = reason
        super().__init__(message or MESSAGES.get(reason, MESSAGES[REASON_REJECTED]), hint, merged)
        self.reason = reason


class RateLimited(DevteamError):
    """The server asked the caller to slow down. Never retried automatically (SR-11)."""

    exit_code = EXIT_ENVIRONMENT

    def __init__(self, retry_after=None):
        details = {"reason": REASON_RATE_LIMITED}
        if retry_after is not None:
            details["retry_after"] = retry_after
            message = "too many requests; try again in {} seconds".format(retry_after)
        else:
            message = "too many requests; try again later"
        super().__init__(message, "Wait before trying again; the CLI does not retry on its own.", details)
        self.retry_after = retry_after


def unreachable():
    return EnvError(
        "cannot reach the account server",
        hint="Check your connection and try again.",
        details={"reason": REASON_UNREACHABLE},
    )


# ── input rules ───────────────────────────────────────────────────────────────


def normalize_email(value):
    text = unicodedata.normalize("NFC", str(value or "")).strip().lower()
    if not text or len(text) > 254 or not _EMAIL_RE.match(text) or any(ord(c) < 32 for c in text):
        raise UsageError("that does not look like an email address")
    return text


def normalize_code(value):
    text = str(value or "").strip().replace(" ", "")
    if not _CODE_RE.match(text):
        raise UsageError("the code is {} digits".format(CODE_LENGTH))
    return text


def normalize_password(value):
    """NFC, so the same password typed on two systems is the same bytes (SR-15)."""
    return unicodedata.normalize("NFC", str(value or ""))


def validate_new_password(value):
    """The policy of SR-15 for a password being **set**; returns the NFC form.

    Never applied to a sign-in: a password accepted earlier must still work. The message
    carries the limits and nothing about the candidate.
    """
    text = normalize_password(value)
    if (
        not PASSWORD_MIN_CHARS <= len(text) <= PASSWORD_MAX_CHARS
        or len(text.encode("utf-8")) > PASSWORD_MAX_BYTES
    ):
        raise UsageError(
            "the password must be {} to {} characters and at most {} bytes in UTF-8".format(
                PASSWORD_MIN_CHARS, PASSWORD_MAX_CHARS, PASSWORD_MAX_BYTES
            )
        )
    return text


def normalize_display_name(value):
    text = unicodedata.normalize("NFC", str(value or "")).strip()
    if not text or len(text) > DISPLAY_NAME_MAX or any(ord(c) < 32 for c in text):
        raise UsageError("the display name must be 1 to {} characters".format(DISPLAY_NAME_MAX))
    return text


# ── the client ────────────────────────────────────────────────────────────────


def _session_from(response):
    """A GoTrue token response as a plain dict, or ``None`` when it is not a session."""
    if not isinstance(response, dict):
        return None
    user = response.get("user")
    access, refresh = response.get("access_token"), response.get("refresh_token")
    if not (
        isinstance(user, dict)
        and isinstance(user.get("id"), str)
        and isinstance(access, str)
        and access
        and isinstance(refresh, str)
        and refresh
    ):
        return None
    expires_in = response.get("expires_in")
    if not isinstance(expires_in, int) or isinstance(expires_in, bool) or expires_in <= 0:
        expires_in = 3600
    return {"access_token": access, "refresh_token": refresh, "expires_in": expires_in, "user": user}


class Client:
    """Calls the account server. One instance per command; holds no token."""

    def __init__(self, identity):
        self.identity = identity
        self.base = identity.supabase_url

    # -- plumbing -------------------------------------------------------------

    def _headers(self, token=None):
        headers = {"apikey": self.identity.anon_key}
        if token:
            headers["Authorization"] = "Bearer " + token
        return headers

    def _call(self, method, path, rejected, *, body=None, query=None, token=None):
        try:
            data, _headers = http_policy.request_json(
                method,
                self.base,
                path,
                self._headers(token),
                body=body,
                query=query,
                allow_loopback_http=self.identity.test_seam,
            )
        except http_policy.FetchError as exc:
            raise self._translate(exc, rejected) from None
        return data

    @staticmethod
    def _translate(exc, rejected):
        status = exc.http_status
        if exc.state == "rate_limited" or status == 429:
            return RateLimited(exc.retry_after)
        if status is None or status >= 500:
            return unreachable()
        return Rejected(rejected)

    def _session(self, data):
        session = _session_from(data)
        if session is None:
            raise EnvError(
                "the account server answered with something unexpected",
                details={"reason": "bad_response"},
            )
        return session

    # -- sign-in --------------------------------------------------------------

    def otp_start(self, email, create_user=True, display_name=None):
        body = {"email": email, "create_user": create_user}
        if display_name:
            body["data"] = {"display_name": display_name}
        self._call("POST", "/auth/v1/otp", REASON_REJECTED, body=body)

    def verify(self, email, code, kind="email"):
        data = self._call(
            "POST",
            "/auth/v1/verify",
            REASON_INVALID_CODE,
            body={"type": kind, "email": email, "token": code},
        )
        return self._session(data)

    def verify_pending(self, email, code, kind):
        """A confirmation step that may complete without a session (a double-confirmed change)."""
        data = self._call(
            "POST",
            "/auth/v1/verify",
            REASON_INVALID_CODE,
            body={"type": kind, "email": email, "token": code},
        )
        return _session_from(data)

    def sign_up(self, email, password, display_name=None):
        body = {"email": email, "password": password}
        if display_name:
            body["data"] = {"display_name": display_name}
        self._call("POST", "/auth/v1/signup", REASON_REJECTED, body=body)

    def sign_in_password(self, email, password):
        data = self._call(
            "POST",
            "/auth/v1/token",
            REASON_INVALID_CREDENTIALS,
            body={"email": email, "password": password},
            query={"grant_type": "password"},
        )
        return self._session(data)

    def refresh(self, refresh_token):
        data = self._call(
            "POST",
            "/auth/v1/token",
            REASON_SESSION_EXPIRED,
            body={"refresh_token": refresh_token},
            query={"grant_type": "refresh_token"},
        )
        return self._session(data)

    def pkce_exchange(self, auth_code, verifier):
        data = self._call(
            "POST",
            "/auth/v1/token",
            REASON_REJECTED,
            body={"auth_code": auth_code, "code_verifier": verifier},
            query={"grant_type": "pkce"},
        )
        return self._session(data)

    def recover(self, email):
        self._call("POST", "/auth/v1/recover", REASON_REJECTED, body={"email": email})

    def logout(self, access_token, scope):
        self._call(
            "POST",
            "/auth/v1/logout",
            REASON_REJECTED,
            body={},
            query={"scope": scope},
            token=access_token,
        )

    # -- the signed-in account ------------------------------------------------

    def get_user(self, access_token):
        data = self._call("GET", "/auth/v1/user", REASON_SESSION_EXPIRED, token=access_token)
        if not isinstance(data, dict) or not isinstance(data.get("id"), str):
            raise EnvError(
                "the account server answered with something unexpected",
                details={"reason": "bad_response"},
            )
        return data

    def update_user(self, access_token, body):
        data = self._call("PUT", "/auth/v1/user", REASON_REJECTED, body=body, token=access_token)
        return data if isinstance(data, dict) else {}

    def link_identity_url(self, access_token, provider, redirect_to, challenge, scopes=None):
        query = {
            "provider": provider,
            "redirect_to": redirect_to,
            "code_challenge": challenge,
            "code_challenge_method": "s256",
            "skip_http_redirect": "true",
        }
        if scopes:
            query["scopes"] = scopes
        data = self._call(
            "GET", "/auth/v1/user/identities/authorize", REASON_REJECTED, query=query, token=access_token
        )
        url = data.get("url") if isinstance(data, dict) else None
        if not isinstance(url, str) or not url.startswith(self.base + "/"):
            raise EnvError(
                "the account server answered with something unexpected",
                details={"reason": "bad_response"},
            )
        return url

    def unlink_identity(self, access_token, identity_id):
        if not _UUID_RE.match(str(identity_id)):
            raise UsageError("that is not an identity id")
        self._call(
            "DELETE",
            "/auth/v1/user/identities/{}".format(identity_id),
            REASON_REJECTED,
            token=access_token,
        )

    def profile_get(self, access_token, user_id):
        rows = self._call(
            "GET",
            "/rest/v1/profiles",
            REASON_REJECTED,
            query={"select": "display_name,signup_method,created_at", "id": "eq." + user_id},
            token=access_token,
        )
        return rows[0] if isinstance(rows, list) and rows and isinstance(rows[0], dict) else {}

    def profile_set_name(self, access_token, user_id, display_name):
        rows = self._call(
            "PATCH",
            "/rest/v1/profiles?id=eq." + user_id,
            REASON_REJECTED,
            body={"display_name": display_name},
            token=access_token,
        )
        return rows

    # -- Edge Functions -------------------------------------------------------

    def entitlement(self, access_token):
        data = self._call(
            "POST", "/functions/v1/entitlement", REASON_SESSION_EXPIRED, body={}, token=access_token
        )
        token = data.get("token") if isinstance(data, dict) else None
        if not isinstance(token, str) or not token:
            raise EnvError(
                "the account server answered with something unexpected",
                details={"reason": "bad_response"},
            )
        return token

    def delete_account(self, access_token):
        self._call("POST", "/functions/v1/account-delete", REASON_REJECTED, body={}, token=access_token)
