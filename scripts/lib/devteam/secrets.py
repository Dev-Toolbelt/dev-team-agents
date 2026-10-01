"""Secret value storage, keyed by an opaque reference string (ADR-0010).

This module holds **values**. The non-secret reference schema — purpose, scope,
which backend a key lives in — is a different module's job; this one never reads
a reference file and never writes an audit line. Given a ``ref`` and a value, it
stores or retrieves the value and nothing else.

Backends, best first:

* ``keychain`` — macOS, via the ``security`` CLI. A value is limited to
  ``KEYCHAIN_VALUE_MAX_BYTES`` (see ``_keychain_put``).
* ``dpapi`` — Windows, via ``CryptProtectData``/``CryptUnprotectData``.
* ``insecure`` — a JSON file, chmod'ed 0600 where the filesystem has POSIX
  permission bits. Always available, so an unsupported platform is never
  blocked, but it is not a security control: anyone who can read the data store
  as this user can read every value in it.

  **On Windows that mode is not applied at all.** ``os.chmod`` there can only
  flip the read-only attribute, so neither this file's 0600 nor the data store's
  0700 directory mode is enforced by the filesystem — containment falls back to
  whatever the user profile's own ACLs give, which this code neither sets nor
  checks. The backend is therefore weaker on Windows than the name ``insecure``
  already warns, and ``dpapi`` above is the one that should be reached. That is
  now the likely outcome rather than a hope — ``dpapi`` is verified on a real
  Windows host by CI — so landing here on Windows means its probe failed, which
  ``devteam cred`` reports. Stated either way, because a 0600 claimed and not
  enforced is worse than one never claimed.

ADR-0010 also lists an ``age``/``sops`` encrypted backend. It is **not**
implemented here and does not appear in ``BACKENDS`` — it needs a passphrase
per run and this CLI has no interaction model for that yet. A backend name that
always reports itself unavailable is a surface that drifts; leaving it out
entirely is the deliberate choice.
"""

from __future__ import annotations

import base64
import ctypes
import hashlib
import re
import shutil
import subprocess

from . import jsonio, paths
from .errors import EnvError

BACKENDS = ("keychain", "dpapi", "insecure")

_PROBE_TIMEOUT = 5.0
_CMD_TIMEOUT = 10.0

#: A ref reaches a command-line argument (keychain account name) and, hashed, a
#: filename (dpapi). Printable ASCII, alnum-bounded, no whitespace or control
#: characters, bounded length — conservative on purpose, not because the shape
#: `devteam/<project_id>/<key>` is enforced here (the caller owns that contract).
_REF_MAX_LEN = 256
_REF_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._/-]*[A-Za-z0-9])?$")


class SecretError(EnvError):
    """A backend could not store, read, or remove a value."""


def _validate_ref(ref):
    if not isinstance(ref, str) or not (1 <= len(ref) <= _REF_MAX_LEN) or not _REF_RE.match(ref):
        raise SecretError(
            "invalid secret reference: {!r}".format(ref),
            hint="use an opaque identifier like devteam/<project_id>/<key>",
        )


def _validate_value(value):
    if not isinstance(value, str):
        raise SecretError("secret value must be a string")
    # The keychain backend sends the value inside one newline-terminated command
    # line on stdin (see _keychain_put); an embedded NUL or newline breaks that
    # framing. Rejecting it here keeps every backend's behavior the same
    # regardless of which one a given machine defaults to.
    if "\x00" in value or "\n" in value or "\r" in value:
        raise SecretError(
            "secret value must not contain NUL or newline characters",
            hint="store a single-line secret; split multi-line material before storing it",
        )


def _known_backend(name):
    if name not in BACKENDS:
        raise SecretError(
            "unknown secret backend {!r}".format(name),
            hint="use one of {}".format(", ".join(BACKENDS)),
        )


# ── keychain (macOS) ───────────────────────────────────────────────────────────

_KEYCHAIN_SERVICE = "dev-team-agents"

#: `security -i` reads one command line into a ~4 KiB buffer and silently cuts
#: the rest (measured: a 4100-byte value came back as 4025). 3 KiB leaves room for
#: the command, the ref and escaping, and is far above any real API token.
KEYCHAIN_VALUE_MAX_BYTES = 3072


def _run_security(args, input_bytes=None):
    # A new session detaches `security` from any controlling terminal. With one,
    # `add-generic-password -w` reads the value from /dev/tty instead of stdin and
    # waits there until the timeout -- which is what happens to every child of a
    # desktop app started from a terminal, and to `devteam cred set` run in one.
    try:
        return subprocess.run(
            ["security"] + list(args),
            input=input_bytes,
            capture_output=True,
            timeout=_CMD_TIMEOUT,
            start_new_session=True,
        )
    except FileNotFoundError as exc:
        raise SecretError(
            "'security' binary not found",
            hint="install the Xcode Command Line Tools, or choose a different backend",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise SecretError(
            "'security' did not respond within {:.0f}s".format(_CMD_TIMEOUT),
            hint=(
                "the keychain may be locked or waiting on a GUI prompt; unlock it "
                "(or run this once from an interactive terminal) and retry"
            ),
        ) from exc


def _quote_for_security(value):
    """A double-quoted word in `security -i`'s own command syntax.

    Inside double quotes it honours backslash escapes, so a backslash and a double
    quote are the only characters that need one -- verified against a real keychain with
    spaces, quotes, backslashes, ``$`` and backticks round-tripping unchanged.
    """
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _safe_stderr(raw, value=None):
    # `security`'s stderr carries only OS diagnostic text — confirmed against a
    # real keychain for both the not-found and locked-keychain paths — never the
    # password, which only ever appears on stdout of a successful `find`. Safe
    # to surface here.
    text = (raw or b"").decode("utf-8", errors="replace").strip()
    if value:
        # `security -i` was not seen echoing a failed command line, but the value
        # is on its stdin; never let it reach an error message if it ever does.
        text = text.replace(value, "<redacted>")
    return text[:300] if text else "no diagnostic output"


def _probe_keychain():
    if paths.platform_key() != "darwin":
        return "requires macOS"
    binary = shutil.which("security")
    if not binary:
        return "'security' binary not found on PATH"
    try:
        completed = subprocess.run(
            [binary, "list-keychains"], capture_output=True, timeout=_PROBE_TIMEOUT
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "'security' did not respond: {}".format(exc)
    if completed.returncode != 0:
        return "'security list-keychains' exited {}".format(completed.returncode)
    return None


def _keychain_put(ref, value):
    if paths.platform_key() != "darwin":
        raise SecretError("keychain backend requires macOS", hint="ref={}".format(ref))
    # The value never goes on argv: `-w <value>` there would put it in the process
    # table, readable via `ps` by anyone else on the box. A bare trailing `-w`
    # prompts instead, but through readpassphrase, which cuts the value at 128
    # characters (an Atlassian API token is ~190). So the whole command goes to
    # `security -i` on stdin, the value quoted in its own syntax. The item is
    # still created by /usr/bin/security, so its access list -- and every item
    # stored before this -- keeps trusting the same binary.
    size = len(value.encode("utf-8"))
    if size > KEYCHAIN_VALUE_MAX_BYTES:
        raise SecretError(
            "secret value for {} is {} bytes; the keychain backend stores at most {}".format(
                ref, size, KEYCHAIN_VALUE_MAX_BYTES
            ),
            hint="store it with --backend insecure, or split it",
        )
    line = "add-generic-password -a {} -s {} -U -w {}\n".format(
        ref, _KEYCHAIN_SERVICE, _quote_for_security(value)
    )
    completed = _run_security(["-i"], input_bytes=line.encode("utf-8"))
    if completed.returncode != 0:
        raise SecretError(
            "keychain write failed for {}: {}".format(ref, _safe_stderr(completed.stderr, value)),
            hint="check `security`'s diagnostic output; the keychain may be locked",
        )
    # A cut or mangled value can still exit 0; read it back rather than trusting
    # the exit code alone.
    stored = _keychain_get(ref)
    if stored != value:
        _keychain_delete(ref)
        raise SecretError(
            "keychain write for {} did not verify after writing".format(ref),
            hint="retry; if this repeats, inspect the item in Keychain Access",
        )


def _keychain_get(ref):
    if paths.platform_key() != "darwin":
        raise SecretError("keychain backend requires macOS", hint="ref={}".format(ref))
    completed = _run_security(["find-generic-password", "-a", ref, "-s", _KEYCHAIN_SERVICE, "-w"])
    if completed.returncode == 44:
        return None
    if completed.returncode != 0:
        raise SecretError(
            "keychain read failed for {}: {}".format(ref, _safe_stderr(completed.stderr)),
            hint="check `security`'s diagnostic output; the keychain may be locked",
        )
    return completed.stdout.decode("utf-8").rstrip("\n")


def _keychain_delete(ref):
    if paths.platform_key() != "darwin":
        raise SecretError("keychain backend requires macOS", hint="ref={}".format(ref))
    completed = _run_security(["delete-generic-password", "-a", ref, "-s", _KEYCHAIN_SERVICE])
    if completed.returncode == 44:
        return False
    if completed.returncode != 0:
        raise SecretError(
            "keychain delete failed for {}: {}".format(ref, _safe_stderr(completed.stderr)),
            hint="check `security`'s diagnostic output",
        )
    return True


# ── dpapi (Windows) ────────────────────────────────────────────────────────────
# VERIFIED on a real Windows host, by CI. This block carried an UNVERIFIED label
# for as long as it had never executed: it was written against the documented
# Win32 DPAPI/ctypes pattern on a macOS development machine, and the only test
# covering it faked `crypt32`, which is to say it tested the base64 envelope and
# nothing about DPAPI.
#
# `tests/test_credentials.py::SecretsDpapiRealRoundTripTest` now drives the real
# `CryptProtectData`/`CryptUnprotectData` on the `windows-latest` runner. What
# that establishes, beyond "it does not crash": the stored blob is genuinely
# ciphertext and does not contain the plaintext; `_dpapi_bytes_from_blob` copies
# out of the returned buffer before `LocalFree` releases it, which no fake can
# check because no fake allocates through `LocalAlloc`; and a tampered blob is
# refused by DPAPI's own integrity protection rather than decrypting to
# something else.
#
# Still not verified, and deliberately named rather than left to be assumed
# covered: the failure branches of `_probe_dpapi()` (a build whose `crypt32`
# entry points do not resolve), and behaviour under a roaming profile or a
# non-interactive service account, where the user's master key may not be
# available. A GitHub runner is an ordinary interactive-style local profile.
#
# Every Windows-only symbol (`ctypes.windll`) is still reached only behind a
# `platform_key() == "win32"` guard, so importing this module on macOS or Linux
# never touches it and cannot fail because of it.


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _probe_dpapi():
    if paths.platform_key() != "win32":
        return "requires Windows"
    if not hasattr(ctypes, "windll"):
        return "ctypes.windll is not available on this Python build"
    try:
        ctypes.windll.crypt32.CryptProtectData
        ctypes.windll.crypt32.CryptUnprotectData
    except (AttributeError, OSError) as exc:
        return "crypt32 entry points not available: {}".format(exc)
    return None


def _dpapi_blob_from_bytes(raw):
    buf = ctypes.create_string_buffer(raw, len(raw))
    return _DataBlob(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))


def _dpapi_bytes_from_blob(blob):
    return ctypes.string_at(blob.pbData, blob.cbData)


def _dpapi_protect(raw):
    in_blob = _dpapi_blob_from_bytes(raw)
    out_blob = _DataBlob()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
    )
    if not ok:
        raise SecretError(
            "CryptProtectData failed", hint="check DPAPI availability for this user profile"
        )
    try:
        return _dpapi_bytes_from_blob(out_blob)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def _dpapi_unprotect(blob_bytes):
    in_blob = _dpapi_blob_from_bytes(blob_bytes)
    out_blob = _DataBlob()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
    )
    if not ok:
        raise SecretError(
            "CryptUnprotectData failed",
            hint="the blob may belong to a different user profile or machine",
        )
    try:
        return _dpapi_bytes_from_blob(out_blob)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def _dpapi_path(ref):
    digest = hashlib.sha256(ref.encode("utf-8")).hexdigest()
    return paths.secrets_dir() / "{}.bin".format(digest)


def _dpapi_put(ref, value):
    if paths.platform_key() != "win32":
        raise SecretError("dpapi backend requires Windows", hint="ref={}".format(ref))
    protected = _dpapi_protect(value.encode("utf-8"))
    # A JSON envelope rather than a raw byte dump so the write goes through the
    # shared `jsonio.write_json_atomic` (atomic replace, 0600 mode) instead of a
    # second, module-local atomic-write implementation.
    jsonio.write_json_atomic(
        _dpapi_path(ref), {"blob_b64": base64.b64encode(protected).decode("ascii")}
    )


def _dpapi_get(ref):
    if paths.platform_key() != "win32":
        raise SecretError("dpapi backend requires Windows", hint="ref={}".format(ref))
    data = jsonio.read_json(_dpapi_path(ref))
    if data is None:
        return None
    blob = base64.b64decode(data["blob_b64"])
    return _dpapi_unprotect(blob).decode("utf-8")


def _dpapi_delete(ref):
    if paths.platform_key() != "win32":
        raise SecretError("dpapi backend requires Windows", hint="ref={}".format(ref))
    path = _dpapi_path(ref)
    if not path.exists():
        return False
    try:
        path.unlink()
    except OSError as exc:
        raise SecretError("cannot remove {}: {}".format(path, exc)) from exc
    return True


# ── insecure (last resort) ──────────────────────────────────────────────────────
# Not a security control: a mode-0600 JSON file readable by anything running as
# this user. It exists so a platform with no working keychain/dpapi backend is
# never blocked from working at all; `put()` marks every write it makes
# `"insecure": True` so the caller reports it loudly rather than treating it as
# equivalent to the other two.


def _insecure_path():
    return paths.secrets_dir() / "insecure.json"


def _insecure_load():
    return jsonio.read_json(_insecure_path(), default={})


def _probe_insecure():
    return None


def _insecure_put(ref, value):
    data = _insecure_load()
    data[ref] = value
    jsonio.write_json_atomic(_insecure_path(), data)


def _insecure_get(ref):
    return _insecure_load().get(ref)


def _insecure_delete(ref):
    data = _insecure_load()
    if ref not in data:
        return False
    del data[ref]
    jsonio.write_json_atomic(_insecure_path(), data)
    return True


_PROBES = {"keychain": _probe_keychain, "dpapi": _probe_dpapi, "insecure": _probe_insecure}
_PUT = {"keychain": _keychain_put, "dpapi": _dpapi_put, "insecure": _insecure_put}
_GET = {"keychain": _keychain_get, "dpapi": _dpapi_get, "insecure": _insecure_get}
_DELETE = {"keychain": _keychain_delete, "dpapi": _dpapi_delete, "insecure": _insecure_delete}


def _probe_all():
    return {name: _PROBES[name]() for name in BACKENDS}


def available_backends():
    """Backends this machine can actually use, best first. Probed, not guessed."""
    probed = _probe_all()
    return [name for name in BACKENDS if probed[name] is None]


def default_backend():
    """The first available backend. Never ``insecure`` unless it is the only one."""
    avail = available_backends()
    if not avail:
        # Unreachable in practice — `insecure` always probes available — but a
        # missing default must never be mistaken for permission to guess one.
        raise SecretError("no secret backend is available on this machine")
    return avail[0]


def describe():
    """``{"available": [...], "default": ..., "probed": {name: reason-or-None}}``."""
    probed = _probe_all()
    available = [name for name in BACKENDS if probed[name] is None]
    return {
        "available": available,
        "default": available[0] if available else None,
        "probed": probed,
    }


def put(ref, value, backend=None):
    """Store ``value`` under ``ref``, choosing ``default_backend()`` if unset.

    Returns ``{"backend": <name>, "ref": ref, "insecure": bool}``. Raises
    ``SecretError`` naming ``ref`` and the backend, never the value, on failure.
    """
    _validate_ref(ref)
    _validate_value(value)
    chosen = backend if backend is not None else default_backend()
    _known_backend(chosen)
    _PUT[chosen](ref, value)
    return {"backend": chosen, "ref": ref, "insecure": chosen == "insecure"}


def get(ref, backend):
    """The value stored under ``ref`` in ``backend``, or ``None`` if absent."""
    _validate_ref(ref)
    _known_backend(backend)
    return _GET[backend](ref)


def delete(ref, backend):
    """Remove ``ref`` from ``backend``. Returns ``True`` if something was removed."""
    _validate_ref(ref)
    _known_backend(backend)
    return _DELETE[backend](ref)
