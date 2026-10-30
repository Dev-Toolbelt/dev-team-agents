"""``devteam qa auth``: a Playwright ``storageState`` for the release QA run (ADR-0054 § 3).

The agent never handles a password. The credentials group at a JSON Pointer in
``credentials.local.json`` is turned into a browser session file, through this cascade:

1. a cached session for the group that has not expired;
2. the group's ``login`` recipe, with ``username``, ``password`` and an optional
   ``totp_secret`` resolved through ADR-0053 references (the code is computed here,
   RFC 6238);
3. ``--interactive``: a headed browser, the person signs in once, the session is captured;
4. otherwise ``details.reason: "no-credentials"``.

Values reach ``qa_login.mjs`` on its stdin only, never argv. The command prints the path of the
session file and when it expires, never its content. The cache is machine-local and holds one
``0600`` file per group (see ``paths.MACHINE_LOCAL_RECORDS``).
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import shutil
import stat
import struct
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

from . import creds, credentials_local, jsonio, paths
from .errors import DevteamError, EnvError, UsageError
from .lock import store_lock

SESSION_DIR = "qa-sessions"
LOCK_NAME = "qa-sessions"
#: A session file expires at its earliest cookie expiry, and never later than this.
SESSION_TTL = 8 * 3600
LOGIN_SCRIPT = Path(__file__).with_name("qa_login.mjs")
RECIPE_REQUIRED = ("url", "username_selector", "password_selector", "submit_selector")
RECIPE_FIELDS = RECIPE_REQUIRED + ("totp_selector", "success_url_contains")
_RECIPE_TIMEOUT = 120.0
_INTERACTIVE_TIMEOUT = 600.0
#: Names this command writes: the session file and the temp file beside it.
_SESSION_NAME = re.compile(r"^[0-9a-f]{32}\.json$")
_TEMP_NAME = re.compile(r"^[0-9a-f]{32}\.json\.[A-Za-z0-9_]+\.tmp$")


# --- TOTP (RFC 6238 over RFC 4226) ---------------------------------------------------


def hotp(key, counter, digits=6, algorithm=hashlib.sha1):
    """The RFC 4226 code for ``counter`` (an int) under raw ``key`` bytes."""
    digest = hmac.new(key, struct.pack(">Q", counter), algorithm).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)


def totp(secret, at=None, digits=6, period=30, algorithm=hashlib.sha1):
    """The RFC 6238 code for a base32 ``secret`` at time ``at`` (default: now)."""
    cleaned = re.sub(r"[\s-]", "", secret).upper()
    try:
        key = base64.b32decode(cleaned + "=" * (-len(cleaned) % 8))
    except (binascii.Error, ValueError) as exc:
        raise ValueError("the TOTP secret is not valid base32") from exc
    moment = time.time() if at is None else at
    return hotp(key, int(moment // period), digits, algorithm)


# --- the session cache ---------------------------------------------------------------


def session_dir(project_id):
    return paths.machine_project_dir(project_id) / SESSION_DIR


def session_key(pointer, node, production):
    """What a cached session is valid for: the group's pointer, its login recipe, its username
    and the way the password and TOTP secret are configured, and the production flag.

    A keyed hash (the machine-local key of ``credentials_local``) of the values as written, so
    an edited recipe or a replaced credential never reuses an old cookie jar, and a plaintext
    password never becomes a guessable digest. A reference is hashed as written; a value
    rotated behind the same reference is not seen, which is what ``qa auth clean`` is for.
    """
    login = node.get("login") if isinstance(node.get("login"), dict) else {}
    material = {
        "pointer": pointer,
        "production": bool(production),
        "recipe": {k: login.get(k) for k in RECIPE_FIELDS},
        "credentials": {k: [node.get(k), login.get(k)] for k in ("username", "password", "totp_secret")},
    }
    blob = json.dumps(material, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return credentials_local._hash(blob)[:32]


def session_path(project_id, key):
    """One ``0600`` file per key (see :func:`session_key`)."""
    return session_dir(project_id) / (key + ".json")


def _iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def _expires_at(path):
    """Epoch seconds the session in ``path`` runs out, or ``None`` when it is not a session."""
    try:
        info = os.lstat(str(path))
        if not stat.S_ISREG(info.st_mode):
            return None
        state = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(state, dict) or not isinstance(state.get("cookies"), list):
        return None
    expiries = [info.st_mtime + SESSION_TTL]
    for cookie in state["cookies"]:
        value = cookie.get("expires") if isinstance(cookie, dict) else None
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            expiries.append(float(value))
    return min(expiries)


def _cached(project_id, key, now):
    path = session_path(project_id, key)
    expires = _expires_at(path)
    if expires is None or expires <= now:
        return None
    return {"path": str(path), "expires_at": _iso(expires), "source": "cache"}


def clean(project_id):
    """Remove the session files (and stray temp files) this command wrote; nothing else."""
    base = session_dir(project_id)
    removed = 0
    with store_lock(LOCK_NAME):
        if base.is_dir():
            for entry in sorted(base.iterdir()):
                if _SESSION_NAME.match(entry.name) or _TEMP_NAME.match(entry.name):
                    if entry.is_symlink() or entry.is_file():
                        entry.unlink()
                        removed += 1
    return {"removed": removed}


# --- the sign-in -----------------------------------------------------------------------


def _stop(proc, grace=5.0):
    """SIGTERM so the script closes the browser it opened, SIGKILL if it does not exit in ``grace``."""
    proc.terminate()
    try:
        proc.communicate(timeout=grace)
    except BaseException:  # noqa: BLE001 - whatever happened, the child must not outlive us
        proc.kill()
        proc.communicate()


def _run_login(payload, interactive):
    """Run ``qa_login.mjs`` with ``payload`` on stdin; the script's one-line JSON answer."""
    node = shutil.which("node")
    if node is None:
        raise EnvError(
            "Node.js is not installed, and the QA sign-in runs on the project's Playwright",
            hint="Run /devteam:install, then retry.",
            details={"reason": "playwright-missing"},
        )
    timeout = _INTERACTIVE_TIMEOUT if interactive else _RECIPE_TIMEOUT
    proc = subprocess.Popen(
        [node, str(LOGIN_SCRIPT)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None if interactive else subprocess.DEVNULL,
    )
    try:
        stdout, _ = proc.communicate(json.dumps(payload).encode("utf-8"), timeout=timeout + 15)
    except subprocess.TimeoutExpired as exc:
        _stop(proc)
        raise EnvError("the sign-in did not finish in time", details={"reason": "login-failed"}) from exc
    except BaseException:
        _stop(proc)
        raise
    done = subprocess.CompletedProcess(proc.args, proc.returncode, stdout, None)
    lines = done.stdout.decode("utf-8", "replace").strip().splitlines()
    try:
        answer = json.loads(lines[-1]) if lines else None
    except ValueError:
        answer = None
    if not isinstance(answer, dict):
        raise EnvError("the sign-in script gave no answer", details={"reason": "login-failed"})
    return answer


def _raise_for(answer):
    if answer.get("ok") is True:
        return
    reason = answer.get("reason")
    message = answer.get("message") if isinstance(answer.get("message"), str) else "the sign-in failed"
    if reason == "invalid-login-url":
        raise UsageError(
            message,
            hint="The login page redirected somewhere the group does not describe.",
            details={"reason": "invalid-login-url"},
        )
    if reason == "playwright-missing":
        raise EnvError(
            message,
            hint="Run /devteam:install to set up Playwright in this project, then retry.",
            details={"reason": "playwright-missing"},
        )
    raise EnvError(message, details={"reason": "login-failed"})


def _field(node, login, key, pointer, project_id, root):
    """The value of ``key`` from the group (else its ``login`` recipe); references resolved."""
    where, item = pointer, node.get(key)
    if item in (None, ""):
        item = login.get(key)
        where = pointer + "/login"
    if item in (None, ""):
        return None, None
    here = "{}/{}".format(where.rstrip("/"), key)
    if credentials_local.is_ref_leaf(item):
        return credentials_local.resolve_leaf(item, project_id, "qa-auth", here, root=root), True
    if isinstance(item, str):
        return item, False
    raise UsageError("{!r} must be a string or a {} leaf".format(here, credentials_local.REF_KEY))


def _is_loopback(host):
    return host in ("localhost", "127.0.0.1", "::1") or host.endswith(".localhost")


def check_login_url(url, node, login, production):
    """ADR-0054 § 3: where a password may be typed.

    ``https:`` always; ``http:`` only for a loopback host and never under ``$production``. When
    the group has its own ``url`` field the login host must be that host, so a recipe cannot
    send the credentials somewhere the group does not describe.
    """
    def refuse(why):
        raise UsageError(
            "login.url is not acceptable: {}".format(why),
            hint="Use the https address of the app the group describes.",
            details={"reason": "invalid-login-url"},
        )

    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        port = parts.port or _DEFAULT_PORTS.get(parts.scheme)
    except ValueError:
        return refuse("it is not a URL")
    if parts.scheme not in ("http", "https") or not host:
        return refuse("it needs an http(s) address with a host")
    if parts.username is not None or parts.password is not None:
        return refuse("it must not carry credentials")
    if parts.scheme == "http" and (production or not _is_loopback(host)):
        return refuse("plain http is allowed only for localhost outside production")
    expected = node.get("url") if isinstance(node.get("url"), str) else None
    if expected:
        wanted_host, wanted_port = group_endpoint(expected)
        if wanted_host is None:
            refuse("the group's url has no host to compare with")
        if (wanted_host, wanted_port) != (host, port):
            refuse("its host or port does not match the group's url")


_DEFAULT_PORTS = {"http": 80, "https": 443}


def group_endpoint(url):
    """``(host, effective port)`` of a group's ``url`` field; ``(None, None)`` without a host."""
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        port = parts.port or _DEFAULT_PORTS.get(parts.scheme)
    except ValueError:
        return None, None
    return (host or None), (port if host else None)


def _recipe_inputs(node, production, pointer, project_id, now, root):
    """The sign-in payload for a usable recipe, else ``(None, missing_fields)``."""
    login = node.get("login") if isinstance(node.get("login"), dict) else {}
    missing = [k for k in RECIPE_REQUIRED if not isinstance(login.get(k), str) or not login[k]]
    present = {k: node.get(k) not in (None, "") or login.get(k) not in (None, "") for k in ("username", "password")}
    missing += [k for k, ok in present.items() if not ok]
    if missing:
        return None, missing
    username, _ = _field(node, login, "username", pointer, project_id, root)
    secret_fields = {}
    for key in ("password", "totp_secret"):
        item = node.get(key) if node.get(key) not in (None, "") else login.get(key)
        if production and isinstance(item, str) and item:
            raise UsageError(
                "{!r} is plaintext under $production".format(pointer + "/" + key),
                hint="Store it with `set-secret`, or point it at an op:// or bw:// reference.",
                details={"reason": "plaintext-in-production", "pointer": pointer + "/" + key},
            )
        secret_fields[key], _ = _field(node, login, key, pointer, project_id, root)
    code = None
    if secret_fields["totp_secret"] and login.get("totp_selector"):
        try:
            code = totp(secret_fields["totp_secret"], at=now)
        except ValueError as exc:
            raise EnvError("the TOTP secret is not valid base32", details={"reason": "invalid-totp-secret"}) from exc
    return {
        "recipe": {k: login[k] for k in RECIPE_FIELDS if isinstance(login.get(k), str) and login[k]},
        "username": username,
        "password": secret_fields["password"],
        "totp": code,
    }, []


def _store(project_id, key, scratch, source):
    """Validate the script's output, then move it into place atomically with mode 0600."""
    expires = _expires_at(scratch)
    if expires is None:
        raise EnvError("the sign-in produced no browser session", details={"reason": "login-failed"})
    os.chmod(str(scratch), 0o600)
    final = session_path(project_id, key)
    with store_lock(LOCK_NAME):
        os.replace(str(scratch), str(final))
    return {"path": str(final), "expires_at": _iso(_expires_at(final) or expires), "source": source}


def _scratch(project_id, key):
    base = session_dir(project_id)
    jsonio.ensure_dir(base)
    name = session_path(project_id, key).name
    fd, temp = tempfile.mkstemp(dir=str(base), prefix=name + ".", suffix=".tmp")
    os.close(fd)
    return temp


def _audit_failed(project_id, pointer, source, exc):
    creds.audit(
        project_id, "qa-auth", pointer, outcome="failed",
        detail={"layer": "local", "source": source, "reason": (getattr(exc, "details", None) or {}).get("reason")},
    )


def _sign_in_with_recipe(inputs, base, project_id, key):
    scratch = _scratch(project_id, key)
    try:
        answer = _run_login(dict(base, mode="recipe", out_path=scratch, **inputs), False)
        _raise_for(answer)
        return _store(project_id, key, scratch, "recipe")
    finally:
        if os.path.exists(scratch):
            os.unlink(scratch)


def authenticate(project_root, project_id, pointer, interactive=False, now=None):
    """The ``{path, expires_at, source}`` of a usable session for the group at ``pointer``.

    ``interactive`` skips the cache (it always captures a fresh session) and turns a failure
    of the scripted sign-in, of any kind, into an interactive capture.
    """
    now = time.time() if now is None else now
    node, production = credentials_local.group_at(project_root, pointer)
    login = node.get("login") if isinstance(node.get("login"), dict) else {}
    login_url = login.get("url") if isinstance(login.get("url"), str) and login.get("url") else None
    if login_url:
        try:
            check_login_url(login_url, node, login, production)
        except UsageError as exc:
            _audit_failed(project_id, pointer, "recipe", exc)
            raise
    key = session_key(pointer, node, production)
    if not interactive:
        cached = _cached(project_id, key, now)
        if cached:
            return cached
    group_host, group_port = group_endpoint(node["url"]) if isinstance(node.get("url"), str) else (None, None)
    base = {
        "project_root": str(project_root),
        "timeout_ms": int(_RECIPE_TIMEOUT * 1000),
        # The same rules `check_login_url` applied, for the page the browser actually lands on.
        "url_rules": {"production": bool(production), "host": group_host, "port": group_port},
    }
    inputs, missing = None, []
    try:
        inputs, missing = _recipe_inputs(node, production, pointer, project_id, now, project_root)
        if inputs is not None:
            result = _sign_in_with_recipe(inputs, base, project_id, key)
            creds.audit(project_id, "qa-auth", pointer, detail={"layer": "local", "source": "recipe"})
            return result
    except DevteamError as exc:
        _audit_failed(project_id, pointer, "recipe", exc)
        if not (interactive and login_url):
            raise
    if inputs is None and not (interactive and login_url):
        creds.audit(project_id, "qa-auth", pointer, outcome="no-credentials", detail={"layer": "local"})
        raise EnvError(
            "no usable credentials in {}".format(pointer),
            hint="Run `devteam qa auth {} --interactive` to sign in once, or store a login recipe "
            "with a username and a password.".format(pointer),
            details={"reason": "no-credentials", "missing": missing, "pointer": pointer},
        )
    scratch = _scratch(project_id, key)
    try:
        payload = dict(
            base, mode="interactive", out_path=scratch, timeout_ms=int(_INTERACTIVE_TIMEOUT * 1000),
            recipe={k: login[k] for k in RECIPE_FIELDS if isinstance(login.get(k), str) and login[k]},
        )
        _raise_for(_run_login(payload, True))
        result = _store(project_id, key, scratch, "interactive")
    except DevteamError as exc:
        _audit_failed(project_id, pointer, "interactive", exc)
        raise
    finally:
        if os.path.exists(scratch):
            os.unlink(scratch)
    creds.audit(project_id, "qa-auth", pointer, detail={"layer": "local", "source": "interactive"})
    return result
