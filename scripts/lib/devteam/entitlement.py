"""The signed entitlement: parse, verify, cache and evaluate (ADR-0029 section 4, SR-21..27, SR-44).

The account server returns a token after every sign-in or refresh. This module is the one
code path that decides what that token means; the gate, ``devteam auth status`` and the
desktop app all go through it and none parses ``entitlement.json`` itself.

Pieces, all of them pure except the cache functions:

* :func:`load_identity` -- the compiled constants (``scripts/lib/auth-config.json``) and the
  loopback test seam (SR-44). Nothing else changes the endpoint or the keys (SR-8).
* :func:`verify_token` -- format, signature over the raw bytes, then the payload (SR-21, 22).
* :func:`check_claims` -- the static claim checks of SR-23.
* :func:`evaluate` -- time, offline window and clock handling (SR-23, 25) -> an
  :class:`EntitlementResult` with one of the :data:`STATUSES`.
* :func:`store_token`, :func:`check`, :func:`clear_cache` -- ``entitlement.json`` in the
  machine-local state directory, written atomically under the store lock (SR-24).

Token wire format (SR-21): ``v1.<header>.<payload>.<signature>``, each part base64url without
padding; the header is exactly ``{"kid": ...}``; the signature is Ed25519 over the ASCII
bytes ``v1.<header>.<payload>``.

Validity is ``exp``, which the server sets to ``iat + max_offline_days`` (7 by default, a
server-side setting); the code ceiling is 30 days and a token carrying more is invalid, so a
misconfigured server cannot make a licence outlive it. A token may also carry an optional
integer claim ``max_offline_days``; when present it can only shorten the window below ``exp``.

Time is evaluated as ``effective_now = local_now + skew`` where ``skew = iat - local_now`` was
recorded when the token was accepted online, so a merely slow clock is not read as a rollback.
``max_seen_at`` is the highest ``effective_now`` observed with a usable token; reading earlier
than that minus five minutes forces an online check, and the next online success resets it.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import ed25519, jsonio, paths
from .errors import EnvError, UsageError
from .integrations import http as http_policy
from .lock import store_lock

TOKEN_VERSION = "v1"
MAX_TOKEN_BYTES = 4096
MAX_VALIDITY_SECONDS = 30 * 86400
DEFAULT_OFFLINE_DAYS = 7
CLOCK_TOLERANCE_SECONDS = 300
#: ``max_seen_at`` is only rewritten once it has moved this far, so a command does not write
#: a file every time it runs.
OBSERVE_WRITE_STEP_SECONDS = 60
CACHE_FILE = "entitlement.json"
CACHE_SCHEMA = 1

STATUS_ACTIVE = "active"
STATUS_TRIAL = "trial"
STATUS_TRIAL_EXPIRED = "trial_expired"
STATUS_BANNED = "banned"
STATUS_NEEDS_ONLINE_CHECK = "needs_online_check"
STATUS_SIGNED_OUT = "signed_out"
STATUS_INVALID = "invalid"
STATUSES = (
    STATUS_ACTIVE,
    STATUS_TRIAL,
    STATUS_TRIAL_EXPIRED,
    STATUS_BANNED,
    STATUS_NEEDS_ONLINE_CHECK,
    STATUS_SIGNED_OUT,
    STATUS_INVALID,
)
_USABLE = (STATUS_ACTIVE, STATUS_TRIAL)
_OBSERVED = (STATUS_ACTIVE, STATUS_TRIAL, STATUS_TRIAL_EXPIRED, STATUS_BANNED)

#: The statuses a token may carry. ``premium`` is an ``active`` account with features.
TOKEN_STATUSES = ("active", "trial", "trial_expired", "premium", "banned")
#: Feature keys this build knows how to grant. None today (ADR-0029 section 4): a key the
#: token carries and this set lacks is ignored, never granted (SR-23).
KNOWN_FEATURES = frozenset()

# ── test seam (SR-44) ─────────────────────────────────────────────────────────

SEAM_URL_ENV = "DEVTEAM_AUTH_TEST_URL"
SEAM_KID_ENV = "DEVTEAM_AUTH_TEST_KID"
SEAM_KEY_ENV = "DEVTEAM_AUTH_TEST_PUBKEY"
SEAM_ENVS = (SEAM_URL_ENV, SEAM_KID_ENV, SEAM_KEY_ENV)
SEAM_KID_PREFIX = "test-"

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "auth-config.json"
_PLACEHOLDER = "REPLACE-ME"
_KID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_B64URL_RE = re.compile(r"^[A-Za-z0-9_-]*$")


class TokenError(Exception):
    """The token is not acceptable. ``reason`` is a stable machine-readable code."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Identity:
    """What this build trusts: one issuer, one audience, a set of public keys by ``kid``."""

    environment: str
    supabase_url: str
    anon_key: str
    audience: str
    keys: dict = field(default_factory=dict)
    test_seam: bool = False

    @property
    def issuer(self):
        return self.supabase_url

    @property
    def configured(self):
        """False while the compiled constants are still placeholders."""
        return _PLACEHOLDER not in self.supabase_url and bool(self.keys)


@dataclass(frozen=True)
class Claims:
    sub: str
    status: str
    features: tuple
    trial_ends_at: object
    iss: str
    aud: str
    v: int
    iat: int
    exp: int
    kid: str
    max_offline_days: object = None

    @property
    def expires_at(self):
        """The end of the offline window: ``exp``, shortened by ``max_offline_days``."""
        end = self.exp
        if self.max_offline_days is not None:
            end = min(end, self.iat + self.max_offline_days * 86400)
        return end


@dataclass(frozen=True)
class EntitlementResult:
    status: str
    reason: str = ""
    token_status: object = None
    sub: object = None
    features: tuple = ()
    trial_ends_at: object = None
    expires_at: object = None
    effective_now: object = None

    @property
    def usable(self):
        return self.status in _USABLE

    def to_dict(self):
        return {
            "status": self.status,
            "reason": self.reason,
            "token_status": self.token_status,
            "features": list(self.features),
            "trial_ends_at": self.trial_ends_at,
            "expires_at": self.expires_at,
        }


def _loopback_host(url):
    import urllib.parse

    try:
        return urllib.parse.urlsplit(url).hostname in http_policy.LOOPBACK_HOSTS
    except ValueError:
        return False


def _decode_key(text):
    raw = _b64url_decode(text)
    if len(raw) != 32:
        raise TokenError("bad_key_length")
    return raw


def load_identity(environ=None, config_path=None):
    """The compiled identity, plus the test seam when ``DEVTEAM_AUTH_TEST_*`` is set.

    Reads only the config file shipped with the CLI and the three seam variables, and the
    seam is read from the environment alone. A seam that names a non-loopback URL, a ``kid``
    without the ``test-`` prefix or an unusable key is refused with a usage error.
    """
    env = os.environ if environ is None else environ
    config = jsonio.read_json(config_path or _CONFIG_PATH)
    if not isinstance(config, dict):
        raise EnvError("auth-config.json is missing or malformed")
    name = config.get("environment")
    section = (config.get("environments") or {}).get(name)
    if not isinstance(section, dict):
        raise EnvError("auth-config.json has no environment {!r}".format(name))
    keys = {}
    for kid, text in (section.get("entitlement_keys") or {}).items():
        if not isinstance(text, str) or text.startswith(_PLACEHOLDER):
            continue
        try:
            keys[kid] = _decode_key(text)
        except (TokenError, ValueError):
            raise EnvError("auth-config.json carries an unusable key for kid {!r}".format(kid))
    url = str(section.get("supabase_url", "")).rstrip("/")
    seam = {key: env.get(key) for key in SEAM_ENVS if env.get(key)}
    if seam:
        missing = [key for key in SEAM_ENVS if key not in seam]
        if missing:
            raise UsageError("the test seam needs {}".format(", ".join(SEAM_ENVS)))
        test_url = seam[SEAM_URL_ENV]
        if not _loopback_host(test_url):
            raise UsageError("{} must be a loopback URL".format(SEAM_URL_ENV))
        test_url = http_policy.validate_base_url(test_url, SEAM_URL_ENV, allow_loopback_http=True)
        if not seam[SEAM_KID_ENV].startswith(SEAM_KID_PREFIX) or not _KID_RE.match(seam[SEAM_KID_ENV]):
            raise UsageError("{} must start with {!r}".format(SEAM_KID_ENV, SEAM_KID_PREFIX))
        try:
            keys[seam[SEAM_KID_ENV]] = _decode_key(seam[SEAM_KEY_ENV])
        except (TokenError, ValueError):
            raise UsageError("{} must be a base64url Ed25519 public key".format(SEAM_KEY_ENV))
        url = test_url
    return Identity(
        environment=name,
        supabase_url=url,
        anon_key=str(section.get("anon_key", "")),
        audience=str(config.get("audience", "devteam-cli")),
        keys=keys,
        test_seam=bool(seam),
    )


def seam_warning(identity):
    """The one-line stderr warning every command prints while the seam is active (SR-44)."""
    if not identity.test_seam:
        return None
    return "warning: account test seam active ({}); licence checks are not production checks".format(
        identity.supabase_url
    )


# ── token parsing and verification ────────────────────────────────────────────


def _b64url_encode(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text):
    """Strict base64url without padding: only the alphabet, and only the canonical encoding."""
    if not isinstance(text, str) or not _B64URL_RE.match(text) or len(text) % 4 == 1:
        raise TokenError("bad_encoding")
    try:
        raw = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except (binascii.Error, ValueError):
        raise TokenError("bad_encoding") from None
    if _b64url_encode(raw) != text:
        raise TokenError("bad_encoding")
    return raw


def _reject_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise TokenError("duplicate_key")
        out[key] = value
    return out


def _reject_constant(_name):
    raise TokenError("bad_json")


def _strict_json(raw):
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicates,
            parse_constant=_reject_constant,
        )
    except TokenError:
        raise
    except (ValueError, UnicodeDecodeError):
        raise TokenError("bad_json") from None


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _claims_from(payload, kid):
    if not isinstance(payload, dict):
        raise TokenError("bad_payload")
    sub, status = payload.get("sub"), payload.get("status")
    iss, aud = payload.get("iss"), payload.get("aud")
    if not (isinstance(sub, str) and 0 < len(sub) <= 128):
        raise TokenError("bad_claim_sub")
    if not isinstance(status, str):
        raise TokenError("bad_claim_status")
    if not (isinstance(iss, str) and isinstance(aud, str)):
        raise TokenError("bad_claim_iss_aud")
    for name in ("v", "iat", "exp"):
        if not _is_int(payload.get(name)):
            raise TokenError("bad_claim_" + name)
    trial_ends_at = payload.get("trial_ends_at")
    if trial_ends_at is not None and not _is_int(trial_ends_at):
        raise TokenError("bad_claim_trial_ends_at")
    max_offline = payload.get("max_offline_days")
    if max_offline is not None and not (_is_int(max_offline) and 0 < max_offline <= 30):
        raise TokenError("bad_claim_max_offline_days")
    features = payload.get("features", [])
    if not isinstance(features, list) or not all(isinstance(item, str) for item in features):
        raise TokenError("bad_claim_features")
    granted = tuple(item for item in features if item in KNOWN_FEATURES)
    return Claims(
        sub=sub,
        status=status,
        features=granted,
        trial_ends_at=trial_ends_at,
        iss=iss,
        aud=aud,
        v=payload["v"],
        iat=payload["iat"],
        exp=payload["exp"],
        kid=kid,
        max_offline_days=max_offline,
    )


def verify_token(token, identity):
    """Check format and signature, then parse the payload; returns :class:`Claims`.

    The signature is verified over the raw bytes **before** the payload is parsed (SR-22).
    Raises :class:`TokenError`. Time and account checks are not made here.
    """
    if not isinstance(token, str) or len(token) > MAX_TOKEN_BYTES:
        raise TokenError("bad_format")
    try:
        token.encode("ascii")
    except UnicodeEncodeError:
        raise TokenError("bad_format") from None
    parts = token.split(".")
    if len(parts) != 4:
        raise TokenError("bad_format")
    version, header_text, payload_text, signature_text = parts
    if version != TOKEN_VERSION:
        raise TokenError("bad_version")
    header = _strict_json(_b64url_decode(header_text))
    if not isinstance(header, dict) or set(header) != {"kid"}:
        raise TokenError("bad_header")
    kid = header["kid"]
    if not isinstance(kid, str) or not _KID_RE.match(kid):
        raise TokenError("bad_header")
    key = identity.keys.get(kid)
    if key is None:
        raise TokenError("unknown_kid")
    signature = _b64url_decode(signature_text)
    signed = "{}.{}.{}".format(version, header_text, payload_text).encode("ascii")
    if not ed25519.verify(key, signed, signature):
        raise TokenError("bad_signature")
    return _claims_from(_strict_json(_b64url_decode(payload_text)), kid)


def check_claims(claims, identity, account_id):
    """The claim checks that do not depend on the clock (SR-23). Raises :class:`TokenError`."""
    if claims.v != 1:
        raise TokenError("bad_version")
    if claims.iss.rstrip("/") != identity.issuer:
        raise TokenError("wrong_issuer")
    if claims.aud != identity.audience:
        raise TokenError("wrong_audience")
    if claims.sub != account_id:
        raise TokenError("wrong_account")
    if claims.status not in TOKEN_STATUSES:
        raise TokenError("unknown_status")
    if claims.exp <= claims.iat:
        raise TokenError("bad_validity")
    if claims.exp - claims.iat > MAX_VALIDITY_SECONDS:
        raise TokenError("validity_too_long")
    if claims.status == "trial" and claims.trial_ends_at is None:
        raise TokenError("bad_claim_trial_ends_at")


# ── evaluation ────────────────────────────────────────────────────────────────


def _result(status, reason="", claims=None, effective_now=None):
    if claims is None:
        return EntitlementResult(status=status, reason=reason, effective_now=effective_now)
    end = claims.expires_at
    if claims.status == "trial" and claims.trial_ends_at is not None:
        end = min(end, claims.trial_ends_at)
    return EntitlementResult(
        status=status,
        reason=reason,
        token_status=claims.status,
        sub=claims.sub,
        features=claims.features,
        trial_ends_at=claims.trial_ends_at,
        expires_at=end,
        effective_now=effective_now,
    )


def _cache_shape_ok(cache):
    return (
        isinstance(cache, dict)
        and cache.get("schema") == CACHE_SCHEMA
        and isinstance(cache.get("token"), str)
        and _is_int(cache.get("skew"))
        and _is_int(cache.get("max_seen_at"))
    )


def evaluate(cache, identity, account_id, local_now):
    """What the cached entitlement means right now. Pure: reads nothing, writes nothing.

    ``cache`` is the parsed ``entitlement.json`` or ``None``; ``account_id`` is the id stored
    at sign-in (``None`` when signed out); ``local_now`` is the machine clock in seconds.
    """
    if not account_id:
        return _result(STATUS_SIGNED_OUT, "no_session")
    if cache is None:
        return _result(STATUS_NEEDS_ONLINE_CHECK, "no_cached_token")
    if not _cache_shape_ok(cache):
        return _result(STATUS_INVALID, "cache_malformed")
    try:
        claims = verify_token(cache["token"], identity)
        check_claims(claims, identity, account_id)
    except TokenError as exc:
        return _result(STATUS_INVALID, exc.reason)
    effective_now = local_now + cache["skew"]
    if effective_now < cache["max_seen_at"] - CLOCK_TOLERANCE_SECONDS:
        return _result(STATUS_NEEDS_ONLINE_CHECK, "clock_rollback", claims, effective_now)
    if claims.iat > effective_now + CLOCK_TOLERANCE_SECONDS:
        return _result(STATUS_INVALID, "issued_in_the_future", claims, effective_now)
    if effective_now >= claims.expires_at:
        return _result(STATUS_NEEDS_ONLINE_CHECK, "expired", claims, effective_now)
    if claims.status == "trial":
        if effective_now >= claims.trial_ends_at:
            return _result(STATUS_NEEDS_ONLINE_CHECK, "trial_period_ended", claims, effective_now)
        return _result(STATUS_TRIAL, "", claims, effective_now)
    if claims.status == "trial_expired":
        return _result(STATUS_TRIAL_EXPIRED, "", claims, effective_now)
    if claims.status == "banned":
        return _result(STATUS_BANNED, "", claims, effective_now)
    return _result(STATUS_ACTIVE, "", claims, effective_now)


# ── cache ─────────────────────────────────────────────────────────────────────


def cache_path():
    return paths.machine_dir() / CACHE_FILE


def _cache_path_readonly():
    """The cache path without minting a machine identity; ``None`` when there is none yet."""
    base = paths.known_machine_dir()
    return base / CACHE_FILE if base else None


def read_cache(path=None):
    """The parsed cache, ``None`` when absent. A malformed file reads as ``{}`` (invalid).

    The cache is regenerable by signing in again, so unlike a user-authored file it is not
    protected from being replaced: a corrupt one must not lock the user out forever.
    """
    target = path or _cache_path_readonly()
    if target is None:
        return None
    try:
        data = jsonio.read_json(target)
    except EnvError:
        return {}
    return data


def _now(local_now):
    return time.time() if local_now is None else local_now


def store_token(token, identity, account_id, local_now=None, path=None):
    """Accept ``token`` after an online success and cache it; returns the new result.

    Verifies the signature and the static claims, records ``skew`` and resets
    ``max_seen_at`` to the token's ``iat`` (SR-25). A token with an earlier ``iat`` than the
    cached one for the same account is never written over it (SR-24); the result then
    describes what is cached. An unacceptable token writes nothing.
    """
    now = _now(local_now)
    target = Path(path) if path else cache_path()
    try:
        claims = verify_token(token, identity)
        check_claims(claims, identity, account_id)
    except TokenError as exc:
        return _result(STATUS_INVALID, exc.reason)
    with store_lock("entitlement"):
        current = read_cache(target)
        if _cache_shape_ok(current):
            try:
                cached = verify_token(current["token"], identity)
            except TokenError:
                cached = None
            if cached is not None and cached.sub == claims.sub and cached.iat > claims.iat:
                return evaluate(current, identity, account_id, now)
        record = {
            "schema": CACHE_SCHEMA,
            "token": token,
            "skew": int(round(claims.iat - now)),
            "max_seen_at": claims.iat,
        }
        jsonio.write_json_atomic(target, record)
    return evaluate(record, identity, account_id, now)


def check(identity, account_id, local_now=None, path=None):
    """Read the cache, evaluate it and advance ``max_seen_at`` when the token is in use."""
    now = _now(local_now)
    target = Path(path) if path else _cache_path_readonly()
    cache = read_cache(target) if target else None
    result = evaluate(cache, identity, account_id, now)
    if (
        target is not None
        and result.status in _OBSERVED
        and result.effective_now is not None
        and result.effective_now > cache["max_seen_at"] + OBSERVE_WRITE_STEP_SECONDS
    ):
        _advance(target, cache["token"], int(result.effective_now))
    return result


def _advance(target, token, seen_at):
    with store_lock("entitlement"):
        current = read_cache(target)
        # A newer token may have landed between the read and the lock: leave it alone.
        if _cache_shape_ok(current) and current["token"] == token and seen_at > current["max_seen_at"]:
            current = dict(current, max_seen_at=seen_at)
            jsonio.write_json_atomic(target, current)


def clear_cache(path=None):
    """Remove the cache (sign-out). The one place this record is deleted, under the lock."""
    target = Path(path) if path else cache_path()
    with store_lock("entitlement"):
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise EnvError("cannot remove {}: {}".format(target, exc)) from exc
