"""The signed-in session: what is stored, where, and how a refresh stays safe (ADR-0029).

Two records and one in-memory value:

* the **refresh token** goes through :mod:`secrets` under the global reference
  :data:`REF` (SR-16), on the default backend. When that backend is ``insecure`` the file
  stays mode 0600 and every report says so in plain words and in ``secret_backend``;
* ``account-session.json`` in the machine-local state directory holds the non-secret
  facts: the account id the entitlement's ``sub`` is checked against, the email, which
  backend holds the token, and when the entitlement was last fetched. It lets an offline
  ``status`` answer without touching the keychain;
* the **access token** lives in this process's memory only and is never written anywhere.

A refresh runs under the store lock (SR-17). A second process that waited on the lock
re-reads the stored token instead of presenting the one it read earlier, so the rotated
token is never presented twice and reuse detection never fires. Threads of one process
share the in-memory access token, so only the first of them exchanges a token.

No function here puts a token in an exception, a log line or a return value that a caller
prints: the callers receive plain dicts and are written not to render them.
"""

from __future__ import annotations

import threading
import time

from . import entitlement, jsonio, paths
from . import secrets as secrets_module
from .auth_gotrue import REASON_SESSION_EXPIRED, Rejected
from .errors import EnvError
from .lock import store_lock

REF = "account.session.refresh_token"
META_FILE = "account-session.json"
META_SCHEMA = 1
LOCK_NAME = "auth-session"
LOCK_TIMEOUT = 45.0
#: An access token this close to its expiry is treated as expired.
ACCESS_SKEW_SECONDS = 60
#: A token fetched this long ago is stale; a usable one is then refreshed when online.
REFRESH_AFTER_SECONDS = 24 * 3600
#: A ``trial_expired`` or ``banned`` answer is rechecked sooner: the user may have been
#: cleared, and nothing else tells this machine.
BLOCKED_RECHECK_SECONDS = 3600
#: After a failed online attempt a usable cached token is trusted for this long before the
#: next attempt, so an offline machine does not pay a network timeout on every command.
RETRY_AFTER_FAILURE_SECONDS = 900

_memory = {}
_memory_lock = threading.Lock()
#: Serialises refreshes among the threads of one process; the store lock does it across
#: processes. Taken first, so a thread never holds the store lock while waiting on another.
_refresh_gate = threading.Lock()


def meta_path():
    return paths.machine_dir() / META_FILE


def read_meta():
    """The session record, or ``None`` when signed out. Regenerable, so a bad one is ignored."""
    base = paths.known_machine_dir()
    if base is None:
        return None
    try:
        data = jsonio.read_json(base / META_FILE)
    except EnvError:
        return None
    if not isinstance(data, dict) or data.get("schema") != META_SCHEMA:
        return None
    if not isinstance(data.get("account_id"), str) or not data["account_id"]:
        return None
    return data


def update_meta(**fields):
    """Merge ``fields`` into the record under the session lock; a no-op when signed out."""
    with store_lock(LOCK_NAME, timeout=LOCK_TIMEOUT):
        meta = read_meta()
        if meta is None:
            return None
        meta.update(fields)
        jsonio.write_json_atomic(meta_path(), meta)
        return meta


def _forget_memory():
    with _memory_lock:
        _memory.clear()


def _remember(access_token, expires_in, account_id):
    with _memory_lock:
        _memory.update(
            access_token=access_token,
            expires_at=time.time() + expires_in,
            account_id=account_id,
        )


def _remembered(account_id):
    with _memory_lock:
        if (
            _memory.get("account_id") == account_id
            and _memory.get("access_token")
            and _memory.get("expires_at", 0) - ACCESS_SKEW_SECONDS > time.time()
        ):
            return _memory["access_token"]
    return None


def backend_view(meta):
    """``(backend_name, insecure)`` for reports; ``(None, False)`` when signed out."""
    backend = (meta or {}).get("backend")
    return backend, backend == "insecure"


def insecure_warning():
    return (
        "the session is stored in a plain file (mode 0600) because no OS keychain is "
        "available on this machine"
    )


def _display_name(user):
    meta = user.get("user_metadata") if isinstance(user, dict) else None
    value = meta.get("display_name") if isinstance(meta, dict) else None
    return value if isinstance(value, str) and value else None


def _provider(user, default):
    app = user.get("app_metadata") if isinstance(user, dict) else None
    value = app.get("provider") if isinstance(app, dict) else None
    return value if isinstance(value, str) and value else default


def save_session(session, provider, now=None):
    """Persist a fresh session: the token in the secret store, the facts in the record.

    Returns the record. A different account than the one stored before clears that
    account's cached entitlement, so a token for the old one is never evaluated for the new.
    """
    user = session["user"]
    now = int(time.time() if now is None else now)
    with store_lock(LOCK_NAME, timeout=LOCK_TIMEOUT):
        previous = read_meta()
        backend = secrets_module.default_backend()
        secrets_module.put(REF, session["refresh_token"], backend)
        if previous and previous.get("backend") not in (None, backend):
            _delete_quietly(previous["backend"])
        same_account = bool(previous) and previous["account_id"] == user["id"]
        meta = {
            "schema": META_SCHEMA,
            "account_id": user["id"],
            "email": user.get("email") if isinstance(user.get("email"), str) else None,
            "display_name": _display_name(user) or (previous.get("display_name") if same_account else None),
            "provider": _provider(user, provider),
            "backend": backend,
            "signed_in_at": previous["signed_in_at"] if same_account and previous.get("signed_in_at") else now,
            "last_online_check": previous.get("last_online_check") if same_account else None,
            "last_online_attempt": None,
        }
        jsonio.write_json_atomic(meta_path(), meta)
        if previous and not same_account:
            entitlement.clear_cache()
    _remember(session["access_token"], session["expires_in"], user["id"])
    return meta


def _delete_quietly(backend):
    try:
        secrets_module.delete(REF, backend)
    except EnvError:
        pass


def _stored_refresh_token(meta):
    try:
        return secrets_module.get(REF, meta.get("backend") or secrets_module.default_backend())
    except EnvError:
        raise EnvError(
            "cannot read the stored session from the secret store",
            hint="Unlock your keychain and try again, or sign in again with `devteam auth login`.",
            details={"reason": "secret_store"},
        ) from None


def access_token(client):
    """A valid access token for the signed-in account, refreshing under the lock if needed.

    Raises :class:`Rejected` (``session_expired``) when there is no session or the server
    refuses the refresh token for good; network trouble raises the client's own errors and
    leaves the session alone.
    """
    meta = read_meta()
    if meta is None:
        raise Rejected("not_signed_in", hint="Run `devteam auth login`.")
    token = _remembered(meta["account_id"])
    if token:
        return token
    with _refresh_gate:
        meta = read_meta()
        if meta is None:
            raise Rejected("not_signed_in", hint="Run `devteam auth login`.")
        token = _remembered(meta["account_id"])
        if token:
            return token
        with store_lock(LOCK_NAME, timeout=LOCK_TIMEOUT):
            meta = read_meta()
            if meta is None:
                raise Rejected("not_signed_in", hint="Run `devteam auth login`.")
            token = _remembered(meta["account_id"])
            if token:
                return token
            stored = _stored_refresh_token(meta)
            if not stored:
                raise Rejected(
                    REASON_SESSION_EXPIRED, hint="Sign in again with `devteam auth login`."
                )
            session = client.refresh(stored)
            if session["user"]["id"] != meta["account_id"]:
                raise Rejected(
                    REASON_SESSION_EXPIRED, hint="Sign in again with `devteam auth login`."
                )
            secrets_module.put(REF, session["refresh_token"], meta["backend"])
            _remember(session["access_token"], session["expires_in"], meta["account_id"])
            return session["access_token"]


def fetch_entitlement(client, identity, access):
    """Ask the server for a token, cache it, and stamp the fetch time. Returns the result."""
    meta = read_meta()
    token = client.entitlement(access)
    result = entitlement.store_token(token, identity, meta["account_id"] if meta else None)
    now = int(time.time())
    if result.status != entitlement.STATUS_INVALID:
        update_meta(last_online_check=now, last_online_attempt=now)
    return result


def sync_entitlement(client, identity):
    """Refresh the access token if needed, then fetch and cache the entitlement."""
    return fetch_entitlement(client, identity, access_token(client))


def should_refresh(result, meta, now=None):
    """Whether an online check is due, given what the cache says and when it last ran."""
    now = time.time() if now is None else now
    if meta is None:
        return False
    if result.status in (entitlement.STATUS_NEEDS_ONLINE_CHECK, entitlement.STATUS_INVALID):
        return True
    last = meta.get("last_online_check")
    attempt = meta.get("last_online_attempt")
    window = (
        BLOCKED_RECHECK_SECONDS
        if result.status in (entitlement.STATUS_TRIAL_EXPIRED, entitlement.STATUS_BANNED)
        else REFRESH_AFTER_SECONDS
    )
    stale = not isinstance(last, int) or now < last or now - last >= window
    if not stale:
        return False
    if isinstance(attempt, int) and 0 <= now - attempt < RETRY_AFTER_FAILURE_SECONDS and (
        not isinstance(last, int) or attempt > last
    ):
        return False
    return True


def note_failed_attempt():
    update_meta(last_online_attempt=int(time.time()))


def clear_local():
    """Remove every local trace of the session; returns what was removed.

    Each step runs even when an earlier one fails (SR-20), and the report says which
    parts succeeded. The in-memory access token is dropped first.
    """
    _forget_memory()
    report = {"refresh_token_removed": True, "entitlement_removed": True, "session_record_removed": True}
    meta = read_meta()
    backends = []
    if meta and meta.get("backend"):
        backends.append(meta["backend"])
    for name in secrets_module.available_backends():
        if name not in backends:
            backends.append(name)
    for name in backends:
        try:
            secrets_module.delete(REF, name)
        except EnvError:
            report["refresh_token_removed"] = False
    try:
        entitlement.clear_cache()
    except EnvError:
        report["entitlement_removed"] = False
    try:
        with store_lock(LOCK_NAME, timeout=LOCK_TIMEOUT):
            try:
                meta_path().unlink()
            except FileNotFoundError:
                pass
    except (EnvError, OSError):
        report["session_record_removed"] = False
    return report
