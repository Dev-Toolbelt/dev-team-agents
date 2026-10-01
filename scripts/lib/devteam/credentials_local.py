"""The local credentials file at ``.dev-team-agents/credentials.local.json`` (ADR-0024).

One location on every layout, edited by hand or through ``devteam cred local``. This
module owns the file's whole life: relocating a legacy copy byte-for-byte, reading it
with secrets redacted, creating it from the canonical template, and patching it.

Nothing here creates the file implicitly. :func:`init` is the only creator, and it is
reached by an explicit command.
"""

from __future__ import annotations

import copy
import errno
import hashlib
import hmac
import json
import math
import os
import re
import secrets
import stat
import tempfile
from pathlib import Path

from . import gitignore, jsonio, paths, project, quarantine, registry
from .errors import ConflictError, EnvError, UsageError
from .lock import store_lock

FILE_NAME = "credentials.local.json"
FILE_MODE = 0o600
TEMPLATE_FILE = Path(__file__).resolve().parent.parent / "credentials-local-template.json"
QUARANTINE_GROUP = "credentials-relocate"
LOCK_NAME = "credentials-local"
#: Machine-local key for the ``hash`` token (dot-prefixed, so machine-local by rule).
TOKEN_KEY_FILE = ".credentials-local-token-key"
#: Ignore lines the file and its temp files need, relative to the project root.
IGNORE_ENTRIES = (".dev-team-agents/" + FILE_NAME, ".dev-team-agents/" + FILE_NAME + ".*")

#: Substrings that mark a key as secret-ish, compared case-insensitively. ``privateKeyPath``
#: is a path, not a secret: ``privatekey`` only counts when it is not followed by ``path``.
SECRET_SUBSTRINGS = (
    "pass", "secret", "token", "credential", "auth", "dsn", "apikey", "api_key", "api-key",
)
#: The flat top-level settings that are not credentials, with the types they may hold.
PLAIN_TOP_LEVEL = {"work_feedback_active": (bool,), "work_feedback_interval_minutes": (int,)}
#: Nested leaf names whose value ``show`` returns (lower-cased). Explicit on purpose: a
#: leaf added to the template stays hidden until it is added here, and a test pins this
#: set against the template so the two cannot drift.
SAFE_LEAF_NAMES = frozenset(
    {"user", "host", "privatekeypath", "path", "type", "port", "database", "username", "appurl"}
)
#: URL userinfo (``scheme://user:pw@host``) or bare ``user:pw@host``.
_USERINFO = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://[^/?#]*@|^[^/@\s:]+:[^/@\s]*@")
#: A URL carrying a query or fragment (``?token=``, ``#access_token=``).
_URL_QUERY = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://[^?#]*[?#]")
#: Pasted key material (PEM, OpenSSH).
_KEY_MATERIAL = "-----BEGIN"

OPS = ("set", "unset")


# --- locations ---------------------------------------------------------------------


def main_root(project_root):
    """The project as seen from the main checkout; every linked worktree shares its file."""
    return project.main_checkout(project_root)


def file_path(project_root):
    """The one canonical location, on layout 1 and layout 2, shared by linked worktrees."""
    return main_root(project_root) / project.PROJECT_DIR / FILE_NAME


def _resolve_project_id(project_root, project_id):
    if project_id:
        return project_id
    data = project.load(project_root)
    return data["project_id"] if data else None


def _store_copy_belongs_here(pid, base):
    """The store copy is this project's only when the registry binds ``pid`` to ``base``.

    ``project_id`` comes from the committed ``project.json``, so a second clone, or a
    repository that copied another project's id, must not pull that project's file in.
    """
    entry = registry.get(pid)
    if not entry or not entry.get("path"):
        return False
    try:
        return Path(os.path.realpath(entry["path"])) == Path(os.path.realpath(str(base)))
    except OSError:
        return False


def legacy_paths(project_root, project_id=None):
    """Where a pre-ADR-0024 copy may live, most authoritative first.

    Layout 1 kept it in ``user-data/``; layout 2 in the store's machine-local project
    folder. The layout the project records decides which is tried first; both are
    candidates, because a half-finished upgrade can leave either behind. A file at the
    project's own root is never a candidate: nothing scans for it (v3-credentials spec).
    """
    root = Path(project_root)
    base = main_root(root)
    bases = [base] if base == root else [base, root]
    pid = _resolve_project_id(root, project_id)
    in_projects = [project.legacy_memory_dir(b) / FILE_NAME for b in bases]
    if not pid or not _store_copy_belongs_here(pid, base):
        return in_projects
    in_store = paths.machine_project_dir(pid) / FILE_NAME
    if project.layout(root) >= project.LAYOUT_MEMORY_IN_STORE:
        return [in_store] + in_projects
    return in_projects + [in_store]


# --- template ----------------------------------------------------------------------


def load_template():
    """The canonical template, parsed. A fresh copy on every call."""
    return json.loads(TEMPLATE_FILE.read_text(encoding="utf-8"))


def is_blank_template(raw):
    """True when ``raw`` parses to exactly the canonical template."""
    try:
        return json.loads(raw.decode("utf-8")) == load_template()
    except (ValueError, UnicodeDecodeError, RecursionError):
        return False


# --- relocation --------------------------------------------------------------------


def _read_bytes(path):
    return Path(path).read_bytes()


def _copy_exclusive(src, dst):
    """Copy ``src`` to a brand-new ``dst`` (``O_EXCL``). False when ``dst`` already exists."""
    payload = src.read_bytes()
    try:
        fd = os.open(str(dst), os.O_WRONLY | os.O_CREAT | os.O_EXCL, FILE_MODE)
    except FileExistsError:
        return False
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if dst.read_bytes() != payload:
            raise EnvError("verification failed copying {} to {}".format(src, dst))
    except BaseException:
        try:
            os.unlink(str(dst))
        except OSError:
            pass
        raise
    return True


def _move_file(source, destination):
    """Move byte-for-byte, never overwriting ``destination``.

    Returns False when ``destination`` already exists (the caller re-evaluates). A hard
    link is the atomic no-clobber primitive; a copy + verify is used only across
    filesystems (EXDEV) or where links are unsupported. Any other OSError propagates.
    """
    src, dst = Path(source), Path(destination)
    jsonio.ensure_dir(dst.parent, mode=None)
    try:
        os.link(str(src), str(dst), follow_symlinks=False)
    except FileExistsError:
        return False
    except (PermissionError, NotImplementedError, AttributeError):
        if not _copy_exclusive(src, dst):
            return False
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise
        if not _copy_exclusive(src, dst):
            return False
    # The destination is in place and verified, so removing the source completes the move.
    os.unlink(str(src))
    try:
        os.chmod(str(dst), FILE_MODE)
    except OSError:
        pass
    return True


def _is_regular(path):
    """A regular file that is not a symlink (``lstat``): never read or move through a link."""
    try:
        return stat.S_ISREG(os.lstat(str(path)).st_mode)
    except OSError:
        return False


def _require_contained(path, base):
    """Refuse a ``.dev-team-agents`` that is a symlink or resolves outside the project.

    A repository can commit that directory as a symlink; following it would put the
    credentials file anywhere the link points (reuse rule ``devteam_containment``).
    """
    parent = Path(path).parent
    if parent.is_symlink():
        raise EnvError(
            "{} is a symlink; refusing to place credentials through it".format(parent),
            hint="Replace the symlink with a real directory.",
            details={"path": str(parent)},
        )
    try:
        Path(os.path.realpath(str(parent))).relative_to(Path(os.path.realpath(str(base))))
    except ValueError:
        raise EnvError(
            "{} resolves outside the project".format(parent),
            details={"path": str(parent)},
        )


def ensure_ignored(project_root):
    """Make sure git ignores the root file before anything is placed there.

    The bind-managed ``.gitignore`` block carries the entries, but a project bound by an
    older CLI, or pinned, does not have them yet — and ``doctor`` and ``upgrade`` do not
    rewrite that block. The entries are unioned into the machine-local
    ``$GIT_COMMON_DIR/info/exclude`` managed block instead. Returns True when the file is
    ignored afterwards, or when the project is not in a git repository.
    """
    base = main_root(project_root)
    target = file_path(project_root)
    top = project.git_lines(base, "rev-parse", "--show-toplevel")
    if not top:
        return True
    lines = project.git_lines(base, "rev-parse", "--git-path", "info/exclude")
    if lines and lines[0].strip():
        exclude = Path(os.path.join(str(base), lines[0].strip()))
        try:
            offset = Path(os.path.realpath(str(base))).relative_to(
                Path(os.path.realpath(top[0].strip()))
            )
        except ValueError:
            offset = Path(".")
        prefix = "" if str(offset) == "." else offset.as_posix() + "/"
        wanted = ["/" + prefix + entry for entry in IGNORE_ENTRIES]
        existing = gitignore.read_managed_entries(exclude)
        if not set(wanted) <= set(existing):
            jsonio.ensure_dir(exclude.parent, mode=None)
            gitignore.apply_managed_block(exclude, sorted(set(existing) | set(wanted)))
    return project.git_lines(base, "check-ignore", "-q", "--no-index", str(target)) is not None


def relocate(project_root, project_id=None):
    """Bring every legacy copy to the root per ADR-0024 § 2. Idempotent, never destructive.

    The root is the main checkout's ``.dev-team-agents/``, never a linked worktree.

    Returns ``{"path", "changed", "moved", "quarantined", "conflicts"}``:

    * ``moved``       — ``[{"from", "to"}]`` legacy copy became the root file
    * ``quarantined`` — ``[{"path", "to", "reason"}]`` reason is ``duplicate``,
      ``blank-legacy`` or ``blank-root``
    * ``conflicts``   — ``[{"legacy", "root", "reason"}]`` left untouched for ``doctor`` to
      report; reason is ``different-content`` or ``symlink`` (never read through a link)
    """
    root_file = file_path(project_root)
    pid = _resolve_project_id(project_root, project_id)
    report = {
        "path": str(root_file),
        "changed": False,
        "moved": [],
        "quarantined": [],
        "conflicts": [],
    }
    candidates = [p for p in legacy_paths(project_root, pid) if p != root_file]
    legacy = []
    for candidate in candidates:
        if os.path.islink(str(candidate)):
            report["conflicts"].append(
                {"legacy": str(candidate), "root": str(root_file), "reason": "symlink"}
            )
        elif _is_regular(candidate):
            legacy.append(candidate)
    if not legacy:
        return report
    _require_contained(root_file, main_root(project_root))
    if os.path.islink(str(root_file)):
        for source in legacy:
            report["conflicts"].append(
                {"legacy": str(source), "root": str(root_file), "reason": "symlink"}
            )
        return report
    if not ensure_ignored(project_root):
        raise EnvError(
            "{} would not be ignored by git; refusing to move credentials there".format(root_file),
            hint="Run `devteam sync` to write the managed .gitignore block, then retry.",
            details={"path": str(root_file)},
        )

    def quarantine_file(path, reason):
        destination = quarantine.move(path, pid, group=QUARANTINE_GROUP)
        report["quarantined"].append(
            {"path": str(path), "to": str(destination) if destination else None, "reason": reason}
        )
        report["changed"] = True

    with store_lock(LOCK_NAME):
        for source in legacy:
            if not _is_regular(source):
                continue
            content = _read_bytes(source)
            for _attempt in range(4):
                if not root_file.is_file():
                    if _move_file(source, root_file):
                        report["moved"].append({"from": str(source), "to": str(root_file)})
                        report["changed"] = True
                        break
                    continue  # the root appeared meanwhile: evaluate it as present
                root_content = _read_bytes(root_file)
                if content == root_content:
                    quarantine_file(source, "duplicate")
                    break
                if is_blank_template(content):
                    quarantine_file(source, "blank-legacy")
                    break
                if is_blank_template(root_content):
                    quarantine_file(root_file, "blank-root")
                    continue  # root is gone now: the next pass moves the legacy copy in
                report["conflicts"].append(
                    {"legacy": str(source), "root": str(root_file), "reason": "different-content"}
                )
                break
            else:
                raise EnvError("cannot place {}: it keeps changing".format(root_file))
    return report


def relocate_safely(project_root, project_id=None):
    """:func:`relocate` for callers that must never fail on it (sync, migrate)."""
    try:
        return relocate(project_root, project_id)
    except (EnvError, ConflictError, OSError) as exc:
        return {
            "path": str(file_path(project_root)),
            "changed": False,
            "moved": [],
            "quarantined": [],
            "conflicts": [],
            "error": str(exc),
        }


# --- reading -----------------------------------------------------------------------


def _token_key():
    """The machine-local key the ``hash`` token is keyed with, created on first use.

    A plain SHA-256 of the file would let anyone holding a ``show`` output rebuild every
    byte but the secrets and test guesses offline; an HMAC with a key that never leaves
    this machine does not.
    """
    path = paths.machine_dir() / TOKEN_KEY_FILE
    try:
        key = path.read_bytes()
        if len(key) >= 32:
            return key
    except OSError:
        pass
    jsonio.ensure_dir(path.parent)
    key = secrets.token_bytes(32)
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, FILE_MODE)
    except FileExistsError:
        return path.read_bytes()
    with os.fdopen(fd, "wb") as handle:
        handle.write(key)
    return key


def _hash(raw):
    return hmac.new(_token_key(), raw, hashlib.sha256).hexdigest()


def _pointer_escape(token):
    return token.replace("~", "~0").replace("/", "~1")


def _is_set(value):
    return value not in (None, "", [], {})


def _secret_ish(key):
    low = key.lower()
    if any(part in low for part in SECRET_SUBSTRINGS):
        return True
    return "privatekey" in low and not low.endswith("path")


def _has_userinfo(value):
    return isinstance(value, str) and bool(_USERINFO.search(value))


def _hidden_string(value):
    """A value that reads as a secret whatever key holds it."""
    if not isinstance(value, str):
        return False
    return (
        bool(_USERINFO.search(value))
        or bool(_URL_QUERY.search(value))
        or _KEY_MATERIAL in value
    )


class _Redactor:
    """Default-deny: only known non-secret shapes keep their value."""

    @staticmethod
    def _hide(value):
        return {"secret": True, "set": _is_set(value)}

    @staticmethod
    def _scalar_ok(key, value, top):
        if not isinstance(key, str) or isinstance(value, (dict, list)):
            return False
        if top and key in PLAIN_TOP_LEVEL:
            allowed = PLAIN_TOP_LEVEL[key]
            return isinstance(value, allowed) and not (int in allowed and isinstance(value, bool))
        if key.lower() not in SAFE_LEAF_NAMES or _secret_ish(key):
            return False
        return not _hidden_string(value)

    def walk(self, value, top=False):
        if isinstance(value, dict):
            out = {}
            for key, item in value.items():
                if (
                    key == "agents"
                    and isinstance(item, list)
                    and all(isinstance(i, str) and not _hidden_string(i) for i in item)
                ):
                    out[key] = list(item)
                elif isinstance(item, (dict, list)):
                    out[key] = self.walk(item)
                elif self._scalar_ok(key, item, top):
                    out[key] = item
                else:
                    out[key] = self._hide(item)
            return out
        if isinstance(value, list):
            return [self.walk(item) if isinstance(item, (dict, list)) else self._hide(item) for item in value]
        return self._hide(value)


def _redact(value):
    return _Redactor().walk(value, top=True)


class _Invalid(Exception):
    def __init__(self, message, line=1, column=1):
        super().__init__(message)
        self.message, self.line, self.column = message, line, column


class _NonFinite(Exception):
    def __init__(self, token):
        super().__init__(token)
        self.token = token


def _locate(text, token):
    """Line and column of the first ``token`` outside a JSON string; 1, 1 when not found."""
    in_string = escaped = False
    index = 0
    while index < len(text):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif text.startswith(token, index):
            line = text.count("\n", 0, index) + 1
            return line, index - (text.rfind("\n", 0, index) + 1) + 1
        index += 1
    return 1, 1


def _reject_constant(name):
    raise _NonFinite(name)


def _parse_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise _NonFinite(text)
    return value


def _loads(raw):
    """Parse ``raw`` bytes; raises :class:`_Invalid` (never echoing a value) when unusable."""
    try:
        text = raw.decode("utf-8")
        parsed = json.loads(text, parse_constant=_reject_constant, parse_float=_parse_float)
    except json.JSONDecodeError as exc:
        raise _Invalid(exc.msg, exc.lineno, exc.colno) from exc
    except _NonFinite as exc:
        line, column = _locate(text, exc.token)
        raise _Invalid("NaN and Infinity are not valid JSON", line, column) from exc
    except UnicodeDecodeError as exc:
        raise _Invalid("the file is not valid UTF-8") from exc
    except RecursionError as exc:
        raise _Invalid("the document is nested too deeply") from exc
    if not isinstance(parsed, dict):
        raise _Invalid("the top-level value must be a JSON object")
    try:
        json.dumps(parsed, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except UnicodeEncodeError as exc:
        raise _Invalid("the document holds a character that is not valid Unicode") from exc
    except RecursionError as exc:
        raise _Invalid("the document is nested too deeply") from exc
    return parsed


def _unknown_paths(data, template):
    """JSON pointers in ``data`` outside the template's known shape, in document order."""
    found = []

    def walk(node, shape, pointer):
        if isinstance(shape, dict):
            if not isinstance(node, dict):
                found.append(pointer or "/")
                return
            if not shape:  # `{}` in the template: free-form (e.g. `docker`)
                return
            for key, item in node.items():
                child = "{}/{}".format(pointer, _pointer_escape(key))
                if key not in shape:
                    found.append(child)
                else:
                    walk(item, shape[key], child)
        elif isinstance(shape, list):
            if not isinstance(node, list):
                found.append(pointer or "/")
                return
            exemplar = shape[0] if shape else None
            for index, item in enumerate(node):
                child = "{}/{}".format(pointer, index)
                if isinstance(exemplar, (dict, list)):
                    walk(item, exemplar, child)
                elif isinstance(item, (dict, list)):
                    found.append(child)
        elif isinstance(node, (dict, list)):
            found.append(pointer or "/")

    walk(data, template, "")
    return found


def _state(path, raw):
    """The ``show`` payload for the bytes read from ``path`` (``None`` = file missing)."""
    base = {
        "path": str(path),
        "exists": raw is not None,
        "valid": False,
        "error": None,
        "hash": None,
        "data": None,
        "unknown_paths": [],
    }
    if raw is None:
        return base
    base["hash"] = _hash(raw)
    try:
        parsed = _loads(raw)
        redacted = _redact(parsed)
        unknown = _unknown_paths(parsed, load_template())
    except _Invalid as exc:
        base["error"] = {"message": exc.message, "line": exc.line, "column": exc.column}
        return base
    except RecursionError:
        base["error"] = {"message": "the document is nested too deeply", "line": 1, "column": 1}
        return base
    base["valid"] = True
    base["data"] = redacted
    base["unknown_paths"] = unknown
    return base


def _read_raw(path):
    try:
        return Path(path).read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise EnvError("cannot read {}: {}".format(path, exc)) from exc


def show(project_root):
    """Read the file; secret values are replaced, never returned."""
    path = file_path(project_root)
    return _state(path, _read_raw(path))


# --- init --------------------------------------------------------------------------


def init(project_root):
    """Write the canonical template. Refuses when the file already exists."""
    path = file_path(project_root)
    template = TEMPLATE_FILE.read_bytes()
    exists = ConflictError(
        "{} already exists".format(path),
        hint="Edit it with `devteam cred local patch`, or by hand.",
        details={"path": str(path), "reason": "exists"},
    )
    _require_contained(path, main_root(project_root))
    with store_lock(LOCK_NAME):
        if os.path.lexists(str(path)):
            raise exists
        if not ensure_ignored(project_root):
            raise EnvError(
                "{} would not be ignored by git; refusing to create it".format(path),
                hint="Run `devteam sync` to write the managed .gitignore block, then retry.",
                details={"path": str(path)},
            )
        if not _write_bytes(path, template, exclusive=True):
            raise exists
    return show(project_root)


# --- patch -------------------------------------------------------------------------


def _write_bytes(path, payload, exclusive=False):
    """Atomic, owner-only write of already-serialised bytes.

    Temp files are named ``credentials.local.json.<random>.tmp`` so the gitignore entry
    ``credentials.local.json.*`` covers them, and are removed on any failure. With
    ``exclusive`` the temp file is hard-linked into place, so a file that appeared in the
    meantime (a hand edit) is never overwritten; returns False in that case.
    """
    p = Path(path)
    jsonio.ensure_dir(p.parent, mode=None)
    handle = tempfile.NamedTemporaryFile(
        "wb", dir=str(p.parent), prefix=p.name + ".", suffix=".tmp", delete=False
    )
    tmp_name = handle.name
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, FILE_MODE)
        if exclusive:
            try:
                os.link(tmp_name, str(p), follow_symlinks=False)
            except FileExistsError:
                os.unlink(tmp_name)
                return False
            os.unlink(tmp_name)
            return True
        os.replace(tmp_name, str(p))
        return True
    except BaseException as exc:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        if isinstance(exc, OSError):
            raise EnvError("cannot write {}: {}".format(p, exc)) from exc
        raise


def _serialise(data):
    return (json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _tokens(pointer):
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise UsageError(
            "invalid JSON pointer {!r}: it must start with '/'".format(pointer),
            hint="RFC 6901, e.g. /app/staging/appUrl",
        )
    out = []
    for raw in pointer[1:].split("/"):
        if "~" in raw.replace("~0", "").replace("~1", ""):
            raise UsageError("invalid escape in JSON pointer {!r}".format(pointer))
        out.append(raw.replace("~1", "/").replace("~0", "~"))
    return out


def _index(token, pointer):
    if not (token.isascii() and token.isdigit()) or (len(token) > 1 and token[0] == "0"):
        raise UsageError(
            "{!r} is not an array index in {!r}".format(token, pointer)
        )
    return int(token)


def _is_placeholder(value):
    if isinstance(value, dict):
        if value.get("secret") is True and set(value) == {"secret", "set"}:
            return True
        return any(_is_placeholder(item) for item in value.values())
    if isinstance(value, list):
        return any(_is_placeholder(item) for item in value)
    return False


def _apply_set(doc, tokens, value, pointer):
    node = doc
    for token in tokens[:-1]:
        if isinstance(node, dict):
            if token not in node:
                node[token] = {}
            node = node[token]
        elif isinstance(node, list):
            idx = _index(token, pointer)
            if idx >= len(node):
                raise UsageError("{!r}: index {} is out of range".format(pointer, idx))
            node = node[idx]
        else:
            raise UsageError("{!r}: cannot descend into a non-container value".format(pointer))
        if not isinstance(node, (dict, list)):
            raise UsageError("{!r}: cannot descend into a non-container value".format(pointer))
    last = tokens[-1]
    if isinstance(node, dict):
        node[last] = value
    else:
        if last == "-":
            node.append(value)
            return
        idx = _index(last, pointer)
        if idx < len(node):
            node[idx] = value
        elif idx == len(node):
            node.append(value)
        else:
            raise UsageError("{!r}: index {} is out of range".format(pointer, idx))


def _apply_unset(doc, tokens, pointer):
    node = doc
    for token in tokens[:-1]:
        if isinstance(node, dict):
            if token not in node:
                return
            node = node[token]
        elif isinstance(node, list):
            idx = _index(token, pointer)
            if idx >= len(node):
                return
            node = node[idx]
        else:
            return
    last = tokens[-1]
    if isinstance(node, dict):
        node.pop(last, None)
    elif isinstance(node, list):
        idx = _index(last, pointer)
        if idx < len(node):
            node.pop(idx)


def _validate_ops(ops):
    if not isinstance(ops, list):
        raise UsageError("the operations must be a JSON array")
    for position, op in enumerate(ops):
        if not isinstance(op, dict) or op.get("op") not in OPS:
            raise UsageError(
                "operation {} must be an object with op 'set' or 'unset'".format(position)
            )
        _tokens(op.get("pointer"))
        if op["op"] == "set":
            if "value" not in op:
                raise UsageError("operation {} ('set') carries no value".format(position))
            if _is_placeholder(op["value"]):
                raise UsageError(
                    "operation {} carries a redaction placeholder, not a value".format(position),
                    hint="`show` replaces secrets with {\"secret\": true, \"set\": ...}; send the "
                    "real value, or leave the field out of the patch to keep it.",
                )


def apply_patch(project_root, ops, expect_hash):
    """Apply ``ops`` atomically; refuse on a stale hash or a file that is not valid JSON.

    Order of refusals: missing file (``EnvError``), hash mismatch (``ConflictError``),
    invalid JSON on disk (``EnvError`` with the line and column), bad operation
    (``UsageError``). Any failure leaves the file untouched.
    """
    try:
        _validate_ops(ops)
    except RecursionError as exc:
        raise UsageError("the operations are nested too deeply") from exc
    path = file_path(project_root)
    _require_contained(path, main_root(project_root))
    with store_lock(LOCK_NAME):
        raw = None if os.path.islink(str(path)) else _read_raw(path)
        if raw is None:
            raise EnvError(
                "{} does not exist".format(path),
                hint="Create it first with `devteam cred local init`.",
                details={"path": str(path)},
            )
        actual = _hash(raw)
        if expect_hash != actual:
            raise ConflictError(
                "credentials.local.json changed since it was read",
                hint="Re-read it with `devteam cred local show` and apply the edit again.",
                details={
                    "path": str(path),
                    "reason": "hash-conflict",
                    "expected_hash": expect_hash,
                    "actual_hash": actual,
                },
            )
        current = _state(path, raw)
        if not current["valid"]:
            raise EnvError(
                "{} is not valid JSON: {}".format(path, current["error"]["message"]),
                hint="Fix the file by hand. dev-team-agents never rewrites a malformed file.",
                details={"path": str(path), "error": current["error"]},
            )
        working = _loads(raw)
        try:
            for op in ops:
                tokens = _tokens(op["pointer"])
                if op["op"] == "set":
                    _apply_set(working, tokens, copy.deepcopy(op["value"]), op["pointer"])
                else:
                    _apply_unset(working, tokens, op["pointer"])
            payload = _serialise(working)
        except RecursionError as exc:
            raise UsageError("the operations are nested too deeply") from exc
        except UnicodeEncodeError as exc:
            raise UsageError("a value holds a character that is not valid Unicode") from exc
        except ValueError as exc:
            if "Out of range float" in str(exc):
                raise UsageError("NaN and Infinity cannot be stored in JSON") from exc
            raise
        _write_bytes(path, payload)
    return _state(path, payload)
