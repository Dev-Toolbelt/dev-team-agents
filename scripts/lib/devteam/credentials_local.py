"""The local credentials file at ``.dev-team-agents/credentials.local.json`` (ADR-0024).

One location on every layout, edited by hand or through ``devteam cred local``. This
module owns the file's whole life: relocating a legacy copy byte-for-byte, reading it
with secrets redacted, creating it from the canonical template, and patching it.

Nothing here creates the file implicitly. :func:`init` is the only creator, and it is
reached by an explicit command.
"""

from __future__ import annotations

import contextlib
import copy
import errno
import hashlib
import hmac
import json
import math
import os
import re
import secrets
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

from . import creds, gitignore, jsonio, paths, project, quarantine, registry
from . import secrets as secret_store
from .errors import ConflictError, EnvError, UsageError
from .lock import store_lock

FILE_NAME = "credentials.local.json"
FILE_MODE = 0o600
TEMPLATE_FILE = Path(__file__).resolve().parent.parent / "credentials-local-template.json"
LEGACY_BLANKS_FILE = Path(__file__).resolve().parent.parent / "credentials-local-legacy-blanks.json"
QUARANTINE_GROUP = "credentials-relocate"
LOCK_NAME = "credentials-local"
#: Machine-local key for the ``hash`` token (dot-prefixed, so machine-local by rule).
TOKEN_KEY_FILE = ".credentials-local-token-key"
#: Ignore lines the file and its temp files need, relative to the project root.
IGNORE_ENTRIES = (".dev-team-agents/" + FILE_NAME, ".dev-team-agents/" + FILE_NAME + ".*")

#: Reserved keys, valid in any object. Everything else in the file is the user's own.
#: ``$secrets`` lists which sibling keys hold a secret; ``$production`` marks the object
#: and everything below it as production.
SECRETS_KEY = "$secrets"
PRODUCTION_KEY = "$production"
#: Substrings that make a key look secret even when it is not listed in ``$secrets``,
#: compared case-insensitively. A safety net only: it hides, it never reveals.
#: ``privateKeyPath`` is a path: ``privatekey`` counts only when not followed by ``path``.
SECRET_SUBSTRINGS = (
    "pass", "secret", "token", "credential", "auth", "dsn", "apikey", "api_key", "api-key",
)
#: Longest key name ``$secrets`` may list before the list is treated as ordinary data.
MAX_SECRET_NAME = 200
#: URL userinfo (``scheme://user:pw@host``) or bare ``user:pw@host``.
_USERINFO = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://[^/?#]*@|^[^/@\s:]+:[^/@\s]*@")
#: A URL carrying a query or fragment (``?token=``, ``#access_token=``).
_URL_QUERY = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://[^?#]*[?#]")
#: Pasted key material (PEM, OpenSSH).
_KEY_MATERIAL = "-----BEGIN"

OPS = ("set", "unset", "move", "set-secret")

#: ADR-0053 § 1: a value may be the reserved leaf ``{"$ref": <ref>, "$backend": <name>}``.
#: ``$backend`` is recorded only for a ``devteam/`` ref; ``op://`` and ``bw://`` refs are
#: resolved by the vendor CLI and carry no backend.
REF_KEY = "$ref"
BACKEND_KEY = "$backend"
_LOCAL_REF = re.compile(r"^devteam/([A-Za-z0-9._-]+)/local/([A-Za-z0-9]{16,64})$")
_OP_REF = re.compile(r"^op://[^\s\x00-\x1f]+$")
_BW_REF = re.compile(
    r"^bw://([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})"
    r"/([^\s/\x00-\x1f][^/\x00-\x1f]{0,127})$"
)
#: ``stored`` value the redactor reports for a malformed reference leaf.
STORED_INVALID = "invalid"
_VENDOR_TIMEOUT = 30.0


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


def _blank_templates():
    blanks = [load_template()]
    try:
        blanks.extend(json.loads(LEGACY_BLANKS_FILE.read_text(encoding="utf-8"))["templates"])
    except (OSError, ValueError, KeyError):
        pass
    return blanks


def is_blank_template(raw):
    """True when ``raw`` parses to the canonical template or to one an earlier release wrote."""
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, RecursionError):
        return False
    return any(parsed == blank for blank in _blank_templates())


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


def _hidden_string(value):
    """A value that reads as a secret whatever key holds it."""
    if not isinstance(value, str):
        return False
    return (
        bool(_USERINFO.search(value))
        or bool(_URL_QUERY.search(value))
        or _KEY_MATERIAL in value
    )


def _marked(node):
    """The key names a well-formed ``$secrets`` list marks in ``node``, else ``None``."""
    listed = node.get(SECRETS_KEY)
    if not isinstance(listed, list):
        return None
    if not all(isinstance(n, str) and 0 < len(n) <= MAX_SECRET_NAME and not _hidden_string(n) for n in listed):
        return None
    return frozenset(listed)


# --- references (ADR-0053) ---------------------------------------------------------


def is_ref_leaf(value):
    """A dict that claims to be a reference leaf (it carries ``$ref``), well formed or not."""
    return isinstance(value, dict) and REF_KEY in value


def ref_kind(leaf):
    """``"devteam"``, ``"op"`` or ``"bw"`` for a well-formed reference leaf, else ``None``."""
    if not is_ref_leaf(leaf) or not set(leaf) <= {REF_KEY, BACKEND_KEY}:
        return None
    ref, backend = leaf[REF_KEY], leaf.get(BACKEND_KEY)
    if not isinstance(ref, str):
        return None
    if _LOCAL_REF.fullmatch(ref):
        return "devteam" if backend in secret_store.BACKENDS else None
    if backend is not None:
        return None
    if _OP_REF.fullmatch(ref):
        return "op"
    if _BW_REF.fullmatch(ref):
        return "bw"
    return None


def stored_kind(value):
    """The additive ``stored`` field of a hidden value: a backend name, ``op``, ``bw``,
    ``"invalid"`` for a malformed reference leaf, or ``None`` for a plaintext secret."""
    if not is_ref_leaf(value):
        return None
    kind = ref_kind(value)
    if kind is None:
        return STORED_INVALID
    return value[BACKEND_KEY] if kind == "devteam" else kind


def _ref_owner(leaf):
    """The project id inside a ``devteam/`` reference, else ``None``."""
    match = _LOCAL_REF.fullmatch(leaf[REF_KEY]) if isinstance(leaf.get(REF_KEY), str) else None
    return match.group(1) if match else None


def _new_ref(project_id):
    return "devteam/{}/local/{}".format(project_id, secrets.token_hex(16))


def _vendor(argv):
    """Run a password-manager CLI; stdout on success, a loud ``EnvError`` otherwise.

    The command line carries a reference, never a value. stderr is truncated to one line.
    """
    if shutil.which(argv[0]) is None:
        raise EnvError(
            "the {} CLI is not installed".format(argv[0]),
            hint="Install it and unlock it, or store the value in the OS secret store instead.",
            details={"reason": "cli-missing", "cli": argv[0]},
        )
    try:
        done = subprocess.run(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=_VENDOR_TIMEOUT, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise EnvError(
            "{} did not answer in {:.0f}s".format(argv[0], _VENDOR_TIMEOUT),
            details={"reason": "cli-failed", "cli": argv[0]},
        ) from exc
    if done.returncode != 0:
        line = (done.stderr.decode("utf-8", "replace").strip().splitlines() or [""])[0][:200]
        raise EnvError(
            "{} failed (exit {}){}".format(argv[0], done.returncode, ": " + line if line else ""),
            hint="Is the vault unlocked?",
            details={"reason": "cli-failed", "cli": argv[0], "exit": done.returncode},
        )
    return done.stdout.decode("utf-8", "replace")


def _bw_field(item, field):
    login = item.get("login") if isinstance(item.get("login"), dict) else {}
    if field in ("username", "password", "totp"):
        value = login.get(field)
    elif field == "notes":
        value = item.get("notes")
    else:
        value = next(
            (f.get("value") for f in item.get("fields") or [] if isinstance(f, dict) and f.get("name") == field),
            None,
        )
    if not isinstance(value, str) or not value:
        raise EnvError(
            "the Bitwarden item has no value for that field",
            details={"reason": "field-missing"},
        )
    return value


def _resolve(leaf, kind, project_id):
    if kind == "devteam":
        if _ref_owner(leaf) != project_id:
            raise EnvError(
                "the reference belongs to another project",
                details={"reason": "foreign-ref"},
            )
        value = secret_store.get(leaf[REF_KEY], leaf[BACKEND_KEY])
        if value is None:
            raise EnvError(
                "the secret store holds no value for this reference",
                hint="Store it again with `set-secret`.",
                details={"reason": "value-missing"},
            )
        return value
    if kind == "op":
        return _vendor(["op", "read", leaf[REF_KEY]]).rstrip("\r\n")
    item_id, field = _BW_REF.fullmatch(leaf[REF_KEY]).groups()
    try:
        item = json.loads(_vendor(["bw", "get", "item", item_id]))
    except ValueError as exc:
        raise EnvError("bw returned something that is not JSON", details={"reason": "cli-failed", "cli": "bw"}) from exc
    if not isinstance(item, dict):
        raise EnvError("bw returned an unexpected item", details={"reason": "cli-failed", "cli": "bw"})
    return _bw_field(item, field)


_GIT_TIMEOUT = 10


def _clean_git_env():
    """The environment git runs in: nothing that can point it at another repository, widen the
    search upward, change how a path is read, or inject configuration."""
    overrides = ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_CEILING_DIRECTORIES")
    return {
        k: v for k, v in os.environ.items()
        if k not in overrides and not k.startswith("GIT_CONFIG") and not (k.startswith("GIT_") and k.endswith("_PATHSPECS"))
    }


def _git_rc(base, *args):
    """``(returncode, stdout)`` of ``git --literal-pathspecs -C base <args>``; ``(None, '')``
    when git could not be run (timeout, I/O error); ``(-1, '')`` when git is not installed."""
    try:
        done = subprocess.run(
            ["git", "--literal-pathspecs", "-C", str(base)] + list(args),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env=_clean_git_env(), timeout=_GIT_TIMEOUT, check=False,
        )
    except FileNotFoundError:
        return -1, ""
    except (OSError, subprocess.SubprocessError):
        return None, ""
    return done.returncode, done.stdout.decode("utf-8", "replace").strip()


def tracked_state(project_root):
    """``"tracked"``, ``"untracked"``, ``"not-a-repo"`` or ``"unknown"`` for the credentials file.

    Fails closed inside a repository: only a clean "exit 1: not in the index" answer is
    ``untracked``; any other error or a timeout is ``unknown``.
    """
    base = main_root(project_root)
    code, out = _git_rc(base, "rev-parse", "--is-inside-work-tree")
    if code is None:
        return "unknown"
    if code == 0 and out != "true":
        return "not-a-repo"  # a bare repository or the inside of .git: no work tree to track in
    if code not in (0, 128, -1):
        return "unknown"  # git itself is unusable (a broken install, a license prompt): fail closed
    if code != 0:
        return "not-a-repo"  # 128: not a git repository; -1: git is not installed
    code, _out = _git_rc(base, "ls-files", "--error-unmatch", "--", str(file_path(project_root)))
    if code == 0:
        return "tracked"
    return "untracked" if code == 1 else "unknown"


def is_tracked(project_root):
    """True when git tracks ``credentials.local.json`` (ADR-0053: it then holds no resolvable ref)."""
    return tracked_state(project_root) == "tracked"


def resolve_leaf(leaf, project_id, action, key, audit=True, *, root):
    """The value behind a reference leaf (ADR-0053 § 3).

    Every resolution is appended to the machine-local audit log through the ADR-0010
    writer: the action, ``key`` (a pointer) and the backend kind, never the value or
    anything derived from it. A refused or failed resolution is audited too.
    """
    kind = ref_kind(leaf)
    if kind is None:
        raise UsageError(
            "{!r} holds a malformed reference".format(key),
            details={"reason": "invalid-ref", "pointer": key},
        )
    detail = {"layer": "local", "stored": leaf[BACKEND_KEY] if kind == "devteam" else kind}
    state = tracked_state(root)
    if state in ("tracked", "unknown"):
        reason = "tracked-file" if state == "tracked" else "tracked-file-unknown"
        if audit:
            creds.audit(project_id, action, key, outcome="refused", detail=dict(detail, reason=reason))
        raise EnvError(
            "credentials.local.json is tracked by git; references are not resolved from a committed file"
            if state == "tracked"
            else "git could not say whether credentials.local.json is tracked; references are not resolved",
            hint="Run `git rm --cached .dev-team-agents/credentials.local.json`, keep it ignored, then retry."
            if state == "tracked" else "Check that `git status` works in this project, then retry.",
            details={"reason": reason, "path": str(file_path(root))},
        )
    try:
        value = _resolve(leaf, kind, project_id)
    except Exception:
        if audit:
            creds.audit(project_id, action, key, outcome="failed", detail=detail)
        raise
    if audit:
        creds.audit(project_id, action, key, detail=detail)
    return value


class _Redactor:
    """What the user marked in ``$secrets`` is hidden; what looks secret is hidden too.

    A marked key hides its whole value, scalar or container. An unmarked key is hidden
    only when its name or its value looks secret; containers under it are walked.
    """

    @staticmethod
    def _hide(value, marked):
        return {"secret": True, "set": _is_set(value), "marked": marked, "stored": stored_kind(value)}

    def walk(self, value):
        if isinstance(value, dict):
            marked = _marked(value)
            out = {}
            for key, item in value.items():
                if key == SECRETS_KEY and marked is not None:
                    out[key] = list(item)
                elif key == PRODUCTION_KEY and isinstance(item, bool):
                    out[key] = item
                elif marked is not None and key in marked:
                    out[key] = self._hide(item, True)
                elif is_ref_leaf(item):
                    out[key] = self._hide(item, False)
                elif isinstance(item, (dict, list)):
                    out[key] = self.walk(item)
                elif _secret_ish(key) or _hidden_string(item):
                    out[key] = self._hide(item, False)
                else:
                    out[key] = item
            return out
        if isinstance(value, list):
            return [
                self._hide(item, False) if is_ref_leaf(item)
                else self.walk(item) if isinstance(item, (dict, list))
                else self._hide(item, False) if _hidden_string(item)
                else item
                for item in value
            ]
        return self._hide(value, False) if _hidden_string(value) else value


def _redact(value):
    return _Redactor().walk(value)


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


def _state(path, raw):
    """The ``show`` payload for the bytes read from ``path`` (``None`` = file missing)."""
    base = {
        "path": str(path),
        "exists": raw is not None,
        "valid": False,
        "error": None,
        "hash": None,
        "data": None,
    }
    if raw is None:
        return base
    base["hash"] = _hash(raw)
    try:
        parsed = _loads(raw)
        redacted = _redact(parsed)
    except _Invalid as exc:
        base["error"] = {"message": exc.message, "line": exc.line, "column": exc.column}
        return base
    except RecursionError:
        base["error"] = {"message": "the document is nested too deeply", "line": 1, "column": 1}
        return base
    base["valid"] = True
    base["data"] = redacted
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


def copy_value(project_root, pointer, expect_hash):
    """The raw value of one hidden field, for the desktop app's copy button (ADR-0046).

    Only a value ``show`` hides and that is set is returned; everything else is refused, so
    this can never become a way to read the file around ``show``. ``expect_hash`` ties the
    copy to the version the caller was shown. A non-string value — a group or list marked
    secret as a whole — is returned as JSON text.
    """
    tokens = _tokens(pointer)
    path = file_path(project_root)
    _require_contained(path, main_root(project_root))
    if os.path.islink(str(path)):
        raise EnvError("{} is a symlink; it is never read through a link".format(path), details={"path": str(path)})
    raw = _read_raw(path)
    if raw is None:
        raise EnvError("{} does not exist".format(path), details={"path": str(path)})
    actual = _hash(raw)
    if expect_hash != actual:
        raise ConflictError(
            "credentials.local.json changed since it was read",
            hint="Re-read it with `devteam cred local show` and copy again.",
            details={"path": str(path), "reason": "hash-conflict"},
        )
    current = _state(path, raw)
    if not current["valid"]:
        raise EnvError("{} is not valid JSON".format(path), details={"path": str(path)})
    shown = _lookup(current["data"], tokens, pointer)
    value = _lookup(_loads(raw), tokens, pointer)
    is_marker = (
        isinstance(shown, dict)
        and set(shown) in ({"secret", "set", "marked"}, {"secret", "set", "marked", "stored"})
        and shown["secret"] is True
        and isinstance(shown["set"], bool)
        and isinstance(shown["marked"], bool)
    )
    if not is_marker:
        raise UsageError("{!r} is not a hidden value".format(pointer), hint="Only a secret field can be copied.")
    if not shown["set"]:
        raise UsageError("{!r} has no value to copy".format(pointer))
    if is_ref_leaf(value):
        # The caller (`cred local copy-value`) audits this read as a whole; the leaf is
        # resolved without a second line.
        text = resolve_leaf(
            value, _resolve_project_id(project_root, None), "local-copy", pointer, audit=False, root=project_root
        )
    else:
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return {"pointer": pointer, "value": text}


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
        if value.get("secret") is True and set(value) in (
            {"secret", "set"}, {"secret", "set", "marked"}, {"secret", "set", "marked", "stored"},
        ):
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


def _lookup(doc, tokens, pointer):
    """The value at ``tokens``; ``UsageError`` when any step is missing."""
    node = doc
    for token in tokens:
        if isinstance(node, dict) and token in node:
            node = node[token]
        elif isinstance(node, list):
            idx = _index(token, pointer)
            if idx >= len(node):
                raise UsageError("{!r} does not exist".format(pointer))
            node = node[idx]
        else:
            raise UsageError("{!r} does not exist".format(pointer))
    return node


def _exists(doc, tokens, pointer):
    try:
        _lookup(doc, tokens, pointer)
        return True
    except UsageError:
        return False


def _apply_move(doc, source, target, op):
    """Move the value at ``from`` to ``pointer`` without it ever leaving this process.

    Renaming a key whose value ``show`` hides is only possible here: the app never holds
    that value. Refuses a missing source, an existing destination (it would overwrite a
    value the caller may not be able to see), and a move into the value's own subtree. A value
    hidden by its key stays hidden where it lands.
    """
    if not source or not target:
        raise UsageError("a move takes a key, not the whole document")
    if target[: len(source)] == source:
        raise UsageError("{!r} cannot move inside itself".format(op["from"]))
    value = _lookup(doc, source, op["from"])
    if target[-1] != "-" and _exists(doc, target, op["pointer"]):
        raise UsageError(
            "{!r} already exists".format(op["pointer"]),
            hint="Remove it first, or move to another name.",
        )
    hidden = _hidden_by_key(doc, source, value)
    keep_hidden = hidden and not _hidden_by_name(target[-1], value)
    if hidden and target[-1] in (SECRETS_KEY, PRODUCTION_KEY):
        raise UsageError("{!r}: a hidden value cannot become a reserved key".format(op["pointer"]))
    _apply_unset(doc, source, op["from"])
    _apply_set(doc, target, value, op["pointer"])
    if keep_hidden:
        _mark_moved(doc, target, op["pointer"])


def _hidden_by_name(key, value):
    return not isinstance(value, (dict, list)) and _secret_ish(key)


def _hidden_by_key(doc, tokens, value):
    """Whether ``show`` hides ``value`` at ``tokens`` because of a key on its path, not the value itself.

    A mark anywhere above hides the whole subtree, so every object on the way is checked.
    """
    node = doc
    for token in tokens:
        if isinstance(node, dict):
            marked = _marked(node)
            if marked is not None and token in marked:
                return True
            node = node.get(token)
        elif isinstance(node, list):
            node = node[int(token)]
    parent_is_object = isinstance(_lookup(doc, tokens[:-1], ""), dict)
    return parent_is_object and _hidden_by_name(tokens[-1], value)


def _mark_moved(doc, target, pointer):
    """Mark the moved key in its new ``$secrets``, so a move never makes ``show`` reveal it."""
    parent = _lookup(doc, target[:-1], pointer)
    if not isinstance(parent, dict):
        raise UsageError("{!r}: a hidden value cannot move into a list".format(pointer))
    if SECRETS_KEY in parent and _marked(parent) is None:
        raise UsageError(
            "{!r}: the destination's {} list is malformed".format(pointer, SECRETS_KEY),
            hint="Fix that list first, then move the value.",
        )
    names = set(parent.get(SECRETS_KEY, []))
    names.add(target[-1])
    if _marked({SECRETS_KEY: sorted(names)}) is None:
        raise UsageError("{!r}: that name cannot be marked as a secret".format(pointer))
    parent[SECRETS_KEY] = sorted(names)


def _check_ref_shapes(value, position):
    """Every ``$ref`` leaf inside a value an op writes must be well formed."""
    if isinstance(value, dict):
        if is_ref_leaf(value):
            if ref_kind(value) is None:
                raise UsageError(
                    "operation {} carries a malformed {} leaf".format(position, REF_KEY),
                    hint='Use {"$ref": "op://vault/item/field"}, {"$ref": "bw://item-id/field"}, '
                    "or `set-secret` for a value to store.",
                    details={"reason": "invalid-ref"},
                )
            return
        for item in value.values():
            _check_ref_shapes(item, position)
    elif isinstance(value, list):
        for item in value:
            _check_ref_shapes(item, position)


def _validate_ops(ops):
    if not isinstance(ops, list):
        raise UsageError("the operations must be a JSON array")
    for position, op in enumerate(ops):
        if not isinstance(op, dict) or op.get("op") not in OPS:
            raise UsageError(
                "operation {} must be an object with op 'set', 'unset', 'move' or 'set-secret'".format(position)
            )
        _tokens(op.get("pointer"))
        if op["op"] == "move":
            _tokens(op.get("from"))
        if op["op"] == "set":
            if "value" not in op:
                raise UsageError("operation {} ('set') carries no value".format(position))
            if _is_placeholder(op["value"]):
                raise UsageError(
                    "operation {} carries a redaction placeholder, not a value".format(position),
                    hint="`show` replaces secrets with {\"secret\": true, \"set\": ...}; send the "
                    "real value, or leave the field out of the patch to keep it.",
                )
            _check_ref_shapes(op["value"], position)
        if op["op"] == "set-secret":
            value = op.get("value")
            if not isinstance(value, str) or not value:
                raise UsageError("operation {} ('set-secret') needs a non-empty string value".format(position))
            _check_secret_value(value, position)
            if not _tokens(op["pointer"]) or _tokens(op["pointer"])[-1] in (SECRETS_KEY, PRODUCTION_KEY, REF_KEY, BACKEND_KEY):
                raise UsageError("operation {} ('set-secret') needs a key to write to".format(position))


def _check_secret_value(value, position=None):
    where = "" if position is None else "operation {}: ".format(position)
    if "\x00" in value or "\n" in value or "\r" in value:
        raise UsageError(
            where + "a stored secret must be a single line without NUL",
            details={"reason": "invalid-secret-value"},
        )
    if len(value.encode("utf-8")) > secret_store.KEYCHAIN_VALUE_MAX_BYTES:
        raise UsageError(
            where + "the value is larger than {} bytes, the most the secret store holds".format(
                secret_store.KEYCHAIN_VALUE_MAX_BYTES
            ),
            details={"reason": "value-too-large"},
        )


# --- secrets by reference (ADR-0053) ------------------------------------------------


@contextlib.contextmanager
def _both_locks():
    """``credentials-local`` first, then ``credentials``: secret-store writes (the insecure
    backend's read-modify-write) cannot race `cred set` / `cred import`."""
    with store_lock(LOCK_NAME):
        with store_lock("credentials"):
            yield


def _pointer(tokens):
    return "/" + "/".join(_pointer_escape(t) for t in tokens)


def _quiet(doc, tokens):
    """The value at ``tokens`` or ``None`` when any step is missing."""
    node = doc
    for token in tokens:
        if isinstance(node, dict) and token in node:
            node = node[token]
        elif isinstance(node, list) and token.isascii() and token.isdigit() and int(token) < len(node):
            node = node[int(token)]
        else:
            return None
    return node


def _production_along(doc, tokens):
    """Whether ``$production: true`` is on the object at ``tokens`` or any ancestor."""
    node = doc
    if isinstance(node, dict) and node.get(PRODUCTION_KEY) is True:
        return True
    for token in tokens:
        node = _quiet(node, [token])
        if node is None:
            return False
        if isinstance(node, dict) and node.get(PRODUCTION_KEY) is True:
            return True
    return False


def _plaintext_in(node, tokens, production, out):
    """Collect ``(tokens, production)`` of every plaintext secret string under ``node``.

    Mirrors the redactor: a key listed in ``$secrets``, a secret-looking key, or a value
    that reads as a secret. A reference leaf is not plaintext. An empty string is not a
    secret value yet.
    """
    if isinstance(node, dict):
        production = production or node.get(PRODUCTION_KEY) is True
        marked = _marked(node)
        for key, item in node.items():
            if key in (SECRETS_KEY, PRODUCTION_KEY) or is_ref_leaf(item):
                continue
            here = tokens + [key]
            if marked is not None and key in marked:
                if isinstance(item, str) and item:
                    out.append((here, production))
            elif isinstance(item, (dict, list)):
                _plaintext_in(item, here, production, out)
            elif isinstance(item, str) and item and (_secret_ish(key) or _hidden_string(item)):
                out.append((here, production))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            here = tokens + [str(index)]
            if isinstance(item, (dict, list)) and not is_ref_leaf(item):
                _plaintext_in(item, here, production, out)
            elif isinstance(item, str) and item and _hidden_string(item):
                out.append((here, production))


def plaintext_secrets(doc):
    """``[{"pointer", "production"}]`` for every plaintext secret in ``doc``."""
    found = []
    _plaintext_in(doc, [], False, found)
    return [{"pointer": _pointer(tokens), "production": prod} for tokens, prod in found]


def _production_plaintext(doc):
    found = []
    _plaintext_in(doc, [], False, found)
    return {_pointer(tokens): _quiet(doc, tokens) for tokens, prod in found if prod}


def _local_refs(node, out):
    """``{ref: backend}`` of every well-formed ``devteam/`` reference leaf under ``node``."""
    if is_ref_leaf(node):
        if ref_kind(node) == "devteam":
            out[node[REF_KEY]] = node[BACKEND_KEY]
    elif isinstance(node, dict):
        for item in node.values():
            _local_refs(item, out)
    elif isinstance(node, list):
        for item in node:
            _local_refs(item, out)
    return out


def _store_secret(value, project_id, production, reuse, created):
    """Push ``value`` into the secret store, read it back, and return the reference leaf.

    ``reuse`` is an existing leaf at the pointer: its ``devteam/`` ref (of this project)
    and recorded backend are kept. The value previously under a reused ref is remembered
    so :func:`_rollback` can restore it; a new ref is deleted instead.
    """
    if project_id is None:
        raise EnvError("secrets can only be stored for a bound project", details={"reason": "not-bound"})
    _check_secret_value(value)
    previous = None
    if reuse is not None and ref_kind(reuse) == "devteam" and _ref_owner(reuse) == project_id:
        ref, backend, reused = reuse[REF_KEY], reuse[BACKEND_KEY], True
    else:
        ref, backend, reused = _new_ref(project_id), secret_store.default_backend(), False
    if production and backend == "insecure":
        raise EnvError(
            "this machine has no OS secret store, and production values are not kept in a plain file",
            hint="Use `op://` or `bw://` references, or run this on a machine with a keychain.",
            details={"reason": "insecure-backend-in-production"},
        )
    if reused:
        previous = secret_store.get(ref, backend)
    created.append((ref, backend, previous))
    secret_store.put(ref, value, backend)
    if secret_store.get(ref, backend) != value:
        raise EnvError(
            "verification failed writing a secret to {}".format(backend),
            details={"reason": "verify-failed"},
        )
    return {REF_KEY: ref, BACKEND_KEY: backend}


def _rollback(created, project_id):
    """Undo what ``created`` pushed into the store. A failure is audited with the ref (not a
    secret), never swallowed: a value left behind is something the user may need to remove."""
    for ref, backend, previous in reversed(created):
        try:
            if previous is None:
                secret_store.delete(ref, backend)
            else:
                secret_store.put(ref, previous, backend)
        except Exception:  # noqa: BLE001 - the original failure is what the caller raises
            creds.audit(project_id, "local-rollback", "-", outcome="rollback-failed",
                        detail={"layer": "local", "ref": ref, "backend": backend})


def _apply_set_secret(working, tokens, op, project_id, created):
    parent = _quiet(working, tokens[:-1])
    if parent is not None and not isinstance(parent, dict):
        raise UsageError("{!r}: 'set-secret' writes an object key, not a list item".format(op["pointer"]))
    existing = _quiet(working, tokens)
    production = _production_along(working, tokens[:-1])
    leaf = _store_secret(op["value"], project_id, production, existing, created)
    _apply_set(working, tokens, leaf, op["pointer"])
    _mark_moved(working, tokens, op["pointer"])


def _refs_in(node, tokens, production, out):
    """Collect ``(pointer, leaf, production)`` for every well-formed ``devteam/`` reference leaf."""
    if is_ref_leaf(node):
        if ref_kind(node) == "devteam":
            out.append((_pointer(tokens), node, production))
    elif isinstance(node, dict):
        production = production or node.get(PRODUCTION_KEY) is True
        for key, item in node.items():
            _refs_in(item, tokens + [key], production, out)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _refs_in(item, tokens + [str(index)], production, out)


def insecure_refs_in_production(doc):
    """Pointers of insecure-backend references that sit under ``$production``."""
    found = []
    _refs_in(doc, [], False, found)
    return {ptr: leaf[REF_KEY] for ptr, leaf, prod in found if prod and leaf[BACKEND_KEY] == "insecure"}


def _refuse_new_insecure_in_production(before, after):
    old = insecure_refs_in_production(before)
    fresh = sorted(ptr for ptr, ref in insecure_refs_in_production(after).items() if old.get(ptr) != ref)
    if fresh:
        raise EnvError(
            "a value kept in the plain-file backend would end up under $production: {}".format(", ".join(fresh)),
            hint="Production values belong in the OS secret store, `op://` or `bw://`.",
            details={"reason": "insecure-backend-in-production", "pointers": fresh},
        )


def _refuse_new_production_plaintext(before, after):
    old = _production_plaintext(before)
    fresh = sorted(ptr for ptr, value in _production_plaintext(after).items() if old.get(ptr) != value)
    if fresh:
        raise UsageError(
            "plaintext secrets are not accepted under $production: {}".format(", ".join(fresh)),
            hint="Send `set-secret` for these values; they are kept in the OS secret store.",
            details={"reason": "plaintext-in-production", "pointers": fresh},
        )


def apply_patch(project_root, ops, expect_hash):
    """Apply ``ops`` atomically; refuse on a stale hash or a file that is not valid JSON.

    Order of refusals: missing file (``EnvError``), hash mismatch (``ConflictError``),
    invalid JSON on disk (``EnvError`` with the line and column), bad operation
    (``UsageError``). Any failure leaves the file untouched, and values a ``set-secret``
    already pushed into the secret store are put back.

    A ``devteam/`` reference that no longer appears after the patch has its stored value
    deleted once the file is written (ADR-0053 § 2); the deletion is limited to
    references that carry this project's id.
    """
    try:
        _validate_ops(ops)
    except RecursionError as exc:
        raise UsageError("the operations are nested too deeply") from exc
    path = file_path(project_root)
    _require_contained(path, main_root(project_root))
    project_id = _resolve_project_id(project_root, None)
    with _both_locks():
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
        original = _loads(raw)
        working = copy.deepcopy(original)
        created = []
        try:
            for op in ops:
                tokens = _tokens(op["pointer"])
                if op["op"] == "set":
                    _apply_set(working, tokens, copy.deepcopy(op["value"]), op["pointer"])
                elif op["op"] == "set-secret":
                    _apply_set_secret(working, tokens, op, project_id, created)
                elif op["op"] == "move":
                    _apply_move(working, _tokens(op["from"]), tokens, op)
                else:
                    _apply_unset(working, tokens, op["pointer"])
            _refuse_new_production_plaintext(original, working)
            _refuse_new_insecure_in_production(original, working)
            _refuse_foreign_refs(working, original, project_id)
            payload = _serialise(working)
            _write_bytes(path, payload)
        except RecursionError as exc:
            _rollback(created, project_id)
            raise UsageError("the operations are nested too deeply") from exc
        except UnicodeEncodeError as exc:
            _rollback(created, project_id)
            raise UsageError("a value holds a character that is not valid Unicode") from exc
        except ValueError as exc:
            _rollback(created, project_id)
            if "Out of range float" in str(exc):
                raise UsageError("NaN and Infinity cannot be stored in JSON") from exc
            raise
        except BaseException:
            _rollback(created, project_id)
            raise
        _drop_unreferenced(original, working, created, project_id)
    return _state(path, payload)


def _refuse_foreign_refs(working, original, project_id):
    """A hand-written ``devteam/`` ref must carry this project's id: it is how a value is found."""
    fresh = set(_local_refs(working, {})) - set(_local_refs(original, {}))
    for ref in fresh:
        match = _LOCAL_REF.fullmatch(ref)
        if not match or match.group(1) != project_id:
            raise UsageError(
                "a {} refers to another project".format(REF_KEY),
                details={"reason": "invalid-ref"},
            )


def _drop_unreferenced(original, working, created, project_id):
    """Delete the stored value of every ``devteam/`` ref the file no longer holds."""
    before = _local_refs(original, {})
    before.update({ref: backend for ref, backend, _prev in created})
    after = _local_refs(working, {})
    for ref, backend in before.items():
        if ref in after or not (_LOCAL_REF.fullmatch(ref) and _LOCAL_REF.fullmatch(ref).group(1) == project_id):
            continue
        try:
            secret_store.delete(ref, backend)
        except Exception:  # noqa: BLE001 - the file is already written; leave a trace, not a failure
            creds.audit(project_id, "local-unset", "-", outcome="delete-failed",
                        detail={"layer": "local", "ref": ref, "backend": backend})


# --- reading a group for exec and the QA sign-in -------------------------------------


def _read_contained(project_root):
    """``(path, raw bytes)`` of the file; never through a link, ``EnvError`` when absent."""
    path = file_path(project_root)
    _require_contained(path, main_root(project_root))
    if os.path.islink(str(path)):
        raise EnvError("{} is a symlink; it is never read through a link".format(path), details={"path": str(path)})
    raw = _read_raw(path)
    if raw is None:
        raise EnvError(
            "{} does not exist".format(path),
            hint="Create it with `devteam cred local init`.",
            details={"path": str(path)},
        )
    return path, raw


def load_document(project_root):
    """The parsed file, for the commands that resolve values; never through a link."""
    path, raw = _read_contained(project_root)
    return _parse(path, raw)


def _parse(path, raw):
    try:
        return _loads(raw)
    except _Invalid as exc:
        raise EnvError(
            "{} is not valid JSON: {}".format(path, exc.message),
            details={"path": str(path), "line": exc.line, "column": exc.column},
        ) from exc
    except RecursionError as exc:
        raise EnvError("{} is nested too deeply".format(path)) from exc


def group_at(project_root, pointer):
    """``(object, production)`` for the group at ``pointer``; ``UsageError`` unless it is an object."""
    doc = load_document(project_root)
    tokens = _tokens(pointer)
    node = _lookup(doc, tokens, pointer)
    if not isinstance(node, dict):
        raise UsageError("{!r} is not a group of fields".format(pointer))
    return node, _production_along(doc, tokens)


def env_name(key):
    """``appUrl`` -> ``APP_URL``; ``None`` for a key with nothing usable in it."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
    name = re.sub(r"[^A-Za-z0-9]+", "_", spaced).strip("_").upper()
    return name or None


def group_environment(project_root, pointer, project_id, allow_production=False):
    """``{DEVTEAM_<KEY>: value}`` for the scalar fields of the group, references resolved.

    A group under ``$production`` is refused unless ``allow_production`` (the CLI's
    ``--production`` flag), before anything is resolved.
    """
    node, production = group_at(project_root, pointer)
    if production and not allow_production:
        raise UsageError(
            "{!r} is under $production".format(pointer),
            hint="Pass --production to run a command with production values.",
            details={"reason": "production-flag-required", "pointer": pointer},
        )
    tokens = _tokens(pointer)
    out, origin = {}, {}
    for key, item in node.items():
        if key in (SECRETS_KEY, PRODUCTION_KEY):
            continue
        name = env_name(key)
        if name is None:
            continue
        here = _pointer(tokens + [key])
        if is_ref_leaf(item):
            value = resolve_leaf(item, project_id, "local-exec", here, root=project_root)
        elif isinstance(item, bool):
            value = "true" if item else "false"
        elif isinstance(item, (str, int, float)):
            value = str(item)
        else:
            continue
        name = "DEVTEAM_" + name
        if name in out:
            raise UsageError(
                "{} and {} both map to {}".format(origin[name], here, name),
                details={"reason": "env-collision"},
            )
        out[name], origin[name] = value, here
    return out


# --- moving existing plaintext (ADR-0053 § 5) ----------------------------------------


def secure(project_root, apply=False, pointers=None):
    """List the plaintext secrets; with ``apply`` move them into the secret store.

    Returns ``{"path", "secrets": [{pointer, production}], "hash"}`` (the desktop app's
    contract): ``secrets`` is what is still plaintext, so after ``apply`` it lists what remains. Applying is
    all or nothing: values are stored and read back first, then the file is rewritten under
    the lock; a failure puts back what was stored and leaves the file as it was.
    """
    path = file_path(project_root)
    _require_contained(path, main_root(project_root))
    if not apply:
        if pointers:
            raise UsageError("--pointer needs --apply")
        _path, raw = _read_contained(project_root)
        doc = _parse(path, raw)
        return {"path": str(path), "secrets": plaintext_secrets(doc), "hash": _hash(raw)}
    project_id = _resolve_project_id(project_root, None)
    with _both_locks():
        _path, raw = _read_contained(project_root)
        doc = _parse(path, raw)
        found = []
        _plaintext_in(doc, [], False, found)
        chosen = found
        if pointers:
            by_pointer = {_pointer(tokens): (tokens, prod) for tokens, prod in found}
            for wanted in pointers:
                if wanted not in by_pointer:
                    raise UsageError("{!r} is not a plaintext secret".format(wanted))
            chosen = [by_pointer[w] for w in dict.fromkeys(pointers)]
        working = copy.deepcopy(doc)
        created, applied = [], []
        try:
            for tokens, production in chosen:
                value = _quiet(working, tokens)
                try:
                    leaf = _store_secret(value, project_id, production, None, created)
                except (UsageError, EnvError) as exc:
                    exc.details = dict(exc.details, pointer=_pointer(tokens))
                    raise
                _apply_set(working, tokens, leaf, _pointer(tokens))
                parent = _quiet(working, tokens[:-1])
                if isinstance(parent, dict):
                    try:
                        _mark_moved(working, tokens, _pointer(tokens))
                    except UsageError:
                        pass  # a malformed $secrets list: the reference leaf is hidden anyway
                applied.append(_pointer(tokens))
            payload = _serialise(working)
            if applied:
                _write_bytes(path, payload)
        except BaseException:
            _rollback(created, project_id)
            raise
    final = payload if applied else raw
    return {
        "path": str(path),
        "secrets": plaintext_secrets(working),
        "hash": _hash(final),
    }
