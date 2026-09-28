"""Store location resolution.

Two stores with different lifetimes (ADR-0007):

* **core** — versioned canonical trees plus the ``current`` pointer. Disposable:
  an uninstall may remove it and ``devteam update`` rebuilds it.
* **data** — preferences, per-project memory, credential references, plus the
  machine-local records that describe *this* machine's binds. Survives uninstall,
  and on Windows lives in the roaming profile so it is covered by profile backup.

``data/`` is split by what the content *says*, not by how it is stored (ADR-0013):
records the user authored or decided are portable and live at the top, while
records this machine observed or built live under ``data/machines/<machine-id>/``.
Nothing here synchronises anything — the split is what makes a future sync, or an
``export`` restored on a second machine, possible at all.

``$DEVTEAM_HOME`` overrides every platform convention and is the seam the test
suite uses, so no test touches a real user directory.
"""

from __future__ import annotations

import json
import os
import re
import socket
import sys
import uuid
from pathlib import Path

from .errors import EnvError

APP_NAME = "dev-team-agents"

#: Set to ``darwin``/``win32``/``linux`` to exercise another platform's layout.
PLATFORM_ENV = "DEVTEAM_PLATFORM"
HOME_ENV = "DEVTEAM_HOME"
#: Overrides the recorded machine identity. The seam that lets a test open the
#: same store "as another machine" without touching a real user directory.
MACHINE_ID_ENV = "DEVTEAM_MACHINE_ID"

MACHINE_ID_FILE = "machine-id"
MACHINES_DIR = "machines"

_MACHINE_ID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_MACHINE_ID_CACHE = {}


def platform_key():
    """``darwin``, ``win32`` or ``linux`` — overridable for tests."""
    override = os.environ.get(PLATFORM_ENV)
    raw = override if override else sys.platform
    if raw.startswith("darwin"):
        return "darwin"
    if raw.startswith("win"):
        return "win32"
    return "linux"


def devteam_home():
    """The explicit store root, or ``None`` when platform defaults apply."""
    raw = os.environ.get(HOME_ENV)
    if not raw:
        return None
    return Path(raw).expanduser()


def _home():
    return Path(os.path.expanduser("~"))


def _win_dir(env_name, fallback):
    raw = os.environ.get(env_name)
    if raw:
        return Path(raw)
    return _home() / fallback


def core_dir():
    override = devteam_home()
    if override:
        return override / "core"
    key = platform_key()
    if key == "darwin":
        return _home() / "Library" / "Application Support" / APP_NAME / "core"
    if key == "win32":
        return _win_dir("LOCALAPPDATA", Path("AppData") / "Local") / APP_NAME / "core"
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else _home() / ".local" / "share"
    return base / APP_NAME / "core"


def data_dir():
    override = devteam_home()
    if override:
        return override / "data"
    key = platform_key()
    if key == "darwin":
        return _home() / "Library" / "Application Support" / APP_NAME / "data"
    if key == "win32":
        # Roaming, deliberately: this is the tree the user must not lose.
        return _win_dir("APPDATA", Path("AppData") / "Roaming") / APP_NAME / "data"
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else _home() / ".local" / "share"
    return base / APP_NAME / "data"


def cache_dir():
    override = devteam_home()
    if override:
        return override / "cache"
    key = platform_key()
    if key == "darwin":
        return _home() / "Library" / "Caches" / APP_NAME
    if key == "win32":
        return _win_dir("LOCALAPPDATA", Path("AppData") / "Local") / APP_NAME / "cache"
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else _home() / ".cache"
    return base / APP_NAME


def versions_dir():
    return core_dir() / "versions"


def current_file():
    """Plain text file holding the active version.

    Deliberately not a symlink: a symlink here would put the Windows
    materialisation failure at the most load-bearing path in the design.
    """
    return core_dir() / "current"


def version_dir(version):
    return versions_dir() / version


# ── machine identity ──────────────────────────────────────────────────────────
# A single UUID per machine, created on first use. It exists so the store can say
# *which* machine wrote a record, which is the one thing that cannot be recovered
# retroactively: without it, two machines' registries are indistinguishable.


def machine_id_file():
    return data_dir() / MACHINE_ID_FILE


def machine_host():
    """A stable-enough name for this host, used to detect a store that travelled."""
    for key in ("DEVTEAM_HOSTNAME", "COMPUTERNAME", "HOSTNAME"):
        value = os.environ.get(key)
        if value and value.strip():
            return value.strip()
    try:
        return socket.gethostname() or "unknown"
    except OSError:
        return "unknown"


def machine_id(create=True):
    """This machine's id, creating it on first use unless ``create`` is false.

    The id is recorded **with the host that created it**, and a mismatch re-issues a
    new one. Without that, the id identifies the *store* rather than the machine, and
    the store is reachable from two machines in cases this design actively invites:
    ADR-0007 deliberately places ``data/`` in the Windows **roaming** profile, which
    is replicated between machines by policy — so the documented Windows layout would
    otherwise guarantee that two machines answer with one id. A restored disk image, a
    VM clone and a shared ``$DEVTEAM_HOME`` on a network mount are the same failure.

    Concurrent first uses converge on one value: the file is created with ``O_EXCL``,
    and the process that loses the race reads the winner's id rather than overwriting
    it. No lock is taken here on purpose — ``locks_dir()`` resolves through this
    function, so locking would be circular.
    """
    override = os.environ.get(MACHINE_ID_ENV)
    if override:
        value = override.strip()
        if not _MACHINE_ID_RE.fullmatch(value):
            raise EnvError(
                "{} must be a lowercase UUID, got {!r}".format(MACHINE_ID_ENV, override),
                hint="Unset it to use this machine's recorded id.",
            )
        return value

    path = machine_id_file()
    key = str(path)
    cached = _MACHINE_ID_CACHE.get(key)
    if cached:
        return cached
    recorded, host = _read_machine_id(path)
    if recorded and host is None:
        # A bare-UUID record from before the host was tracked. It cannot be judged to
        # have travelled, so it is adopted, not re-issued — re-issuing would orphan the
        # records this id already names. The host is filled in so the next open can
        # judge it.
        if create:
            try:
                _write_machine_record(path, recorded, exclusive=False)
            except OSError:
                pass
        _MACHINE_ID_CACHE[key] = recorded
        return recorded
    if recorded and host == machine_host():
        _MACHINE_ID_CACHE[key] = recorded
        return recorded
    if not create:
        # A read-only caller gets the recorded id even when the host does not match;
        # it must not mint one as a side effect of being asked a question.
        return recorded
    value = _reissue_machine_id(path, previous=recorded, previous_host=host)
    _MACHINE_ID_CACHE[key] = value
    return value


def reset_machine_id_cache():
    """Forget the resolved id. Called after anything replaces the data store."""
    _MACHINE_ID_CACHE.clear()


def _read_machine_id(path):
    """``(id, host)`` from the record, or ``(None, None)``.

    Reads both the current object form and the bare-UUID form the first
    implementation wrote, so a store created by it keeps its id.
    """
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None, None
    if not raw:
        return None, None
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
        except ValueError:
            return None, None
        if not isinstance(data, dict):
            return None, None
        value = str(data.get("id", "")).strip()
        host = data.get("created_on")
        return (value if _MACHINE_ID_RE.fullmatch(value) else None), host
    # Bare UUID: no host was recorded, so it cannot be judged to have travelled.
    return (raw if _MACHINE_ID_RE.fullmatch(raw) else None), None


def _write_machine_record(path, value, exclusive):
    payload = json.dumps(
        {"id": value, "created_on": machine_host()}, indent=2, sort_keys=True
    ) + "\n"
    flags = os.O_CREAT | os.O_WRONLY | (os.O_EXCL if exclusive else os.O_TRUNC)
    handle = os.open(str(path), flags, 0o600)
    with os.fdopen(handle, "w", encoding="utf-8") as fh:
        fh.write(payload)
    try:
        # os.open's mode is masked by umask; the store's files are owner-only by
        # contract (jsonio.STORE_FILE_MODE), not by whatever the shell was set to.
        os.chmod(str(path), 0o600)
    except OSError:
        pass


def _reissue_machine_id(path, previous=None, previous_host=None):
    _mkdir_owner_only(path.parent)
    if previous is None and path.exists():
        raise EnvError(
            "{} exists but does not hold a machine record".format(path),
            hint=(
                "Fix or move the file by hand. dev-team-agents will not replace it: a "
                "new id would point at a machine subtree your existing records are not in."
            ),
        )
    value = str(uuid.uuid4())
    if previous is None:
        try:
            _write_machine_record(path, value, exclusive=True)
        except FileExistsError:
            existing, _ = _read_machine_id(path)
            if existing:
                return existing
            raise EnvError(
                "{} exists but does not hold a machine record".format(path),
                hint="Fix or move the file by hand.",
            )
        return value
    # The record came from another host: this machine takes a new identity rather
    # than adopting records that describe a different one. Nothing is deleted — the
    # other host's subtree stays where it is, inert.
    _write_machine_record(path, value, exclusive=False)
    return value


def _mkdir_owner_only(path):
    """``mkdir -p`` with owner-only permissions on each directory it creates.

    Duplicates the narrow part of ``jsonio.ensure_dir`` deliberately: importing
    jsonio here would put a module that writes files underneath the module that
    tells it where to write.
    """
    missing = []
    current = Path(path)
    while not current.exists():
        missing.append(current)
        if current.parent == current:
            break
        current = current.parent
    Path(path).mkdir(parents=True, exist_ok=True)
    for created in missing:
        try:
            os.chmod(str(created), 0o700)
        except OSError:
            pass
    return Path(path)


def machines_dir():
    return data_dir() / MACHINES_DIR


def machine_dir(machine=None):
    """The subtree holding records that describe one machine."""
    return machines_dir() / (machine or machine_id())


# ── machine-local records ─────────────────────────────────────────────────────


def registry_file(machine=None):
    """Bound projects. Machine-local: every entry is an absolute path."""
    return machine_dir(machine) / "registry.json"


def machine_projects_dir(machine=None):
    return machine_dir(machine) / "projects"


def machine_project_dir(project_id, machine=None):
    """Per-project machine-local records: ``bind-manifest.json``, ``state.json``."""
    return machine_projects_dir(machine) / project_id


def locks_dir():
    """Lock files. Machine-local: a lock carries the pid that holds it."""
    return machine_dir() / "locks"


#: Per-project record names that describe this machine rather than the user's work.
#: Everything else in a project's memory is portable.
#:
#: `credentials.local.json` is here on purpose: its **values** are secrets, and a
#: secret that travels with a portable export is a secret in one more place. ADR-0010
#: replaces the file with non-secret references in `data/credentials/`, which are
#: portable precisely because they hold no value.
MACHINE_LOCAL_RECORDS = (
    "state.json",
    "bind-manifest.json",
    "telemetry-queue.json",
    "credentials.local.json",
    # Records credential reads that happened on THIS machine (ADR-0010). Two machines
    # appending to one portable log would need merge semantics nothing here has, and an
    # audit trail that silently interleaves two hosts is worse than two separate ones.
    "audit.log",
)

#: Records that belong to the **project**, not to the user's personal memory:
#: committed, shared by every developer on the repository, and therefore not moved
#: into a per-user store at all. `graphify.json` carries its own gitignore exception
#: (`!.dev-team-agents/user-data/graphify.json`) precisely so the team shares one.
PROJECT_OWNED_RECORDS = ("graphify.json",)

#: Top-level entries of ``data/`` that never leave this machine.
MACHINE_LOCAL_STORE_ENTRIES = (MACHINE_ID_FILE, MACHINES_DIR, "locks")

#: Portable by content, but not part of a portable export: an unbounded recovery bin
#: that is also where both the upgrade and the relocation deposit retired
#: machine-local records — secrets included. `--all` takes it; the default does not.
LOCAL_ONLY_STORE_ENTRIES = ("quarantine",)


def is_machine_local_record(name):
    """True for a record that belongs in the machine subtree.

    Dot-prefixed names are machine-local as a class: every one of them is a cache,
    an ETag, a once-per-day stamp or a session marker — state this machine observed.

    Takes the **basename**, case-folded, so the answer cannot depend on where the
    caller found the file or on how the user typed it. Both mattered: a review found
    that `Credentials.local.json` classified as portable while macOS APFS and Windows
    hand the very same file to anything opening `credentials.local.json`, and that a
    record nested one directory deeper escaped the check entirely.
    """
    base = os.path.basename(str(name)).lower()
    return base.startswith(".") or base in MACHINE_LOCAL_RECORDS


def path_is_machine_local(relative):
    """True when **any** component of a relative path is a machine-local record.

    The single answer for a path rather than a name: a machine-local directory makes
    everything under it machine-local, which is what keeps `.cache/state.json` and
    `env/credentials.local.json` on the right side.
    """
    return any(is_machine_local_record(part) for part in Path(relative).parts)


# ── portable records ─────────────────────────────────────────────────────────


def global_preferences_file():
    return data_dir() / "preferences.json"


def credentials_dir():
    """Credential **references** (ADR-0010). Portable: no entry holds a value."""
    return data_dir() / "credentials"


def credentials_file(project_id=None):
    """``global.json``, or a project's own reference layer when given an id."""
    if project_id is None:
        return credentials_dir() / "global.json"
    return credentials_dir() / "{}.json".format(project_id)


def secrets_dir():
    """Where a backend that must keep a value on disk keeps it.

    Machine-local, and separate from ``credentials/`` on purpose: the reference layer
    is portable precisely because it holds no value, and a value store must never end
    up in an archive that the reference layer's portability makes routine.
    """
    return machine_dir() / "secrets"


def audit_log(project_id):
    """Append-only credential audit for this project, on this machine."""
    return machine_project_dir(project_id) / "audit.log"


def projects_dir():
    return data_dir() / "projects"


def project_data_dir(project_id):
    """Per-project portable records: preferences, session summary."""
    return projects_dir() / project_id


def quarantine_dir(stamp):
    return data_dir() / "quarantine" / stamp


def render_cache_dir(version, provider):
    return cache_dir() / "render" / version / provider


def describe():
    """Everything ``devteam path`` reports, as plain strings. Creates nothing."""
    _reported = machine_id(create=False) or "<unassigned>"
    return {
        "platform": platform_key(),
        "devteam_home": str(devteam_home()) if devteam_home() else None,
        "core": str(core_dir()),
        "data": str(data_dir()),
        "cache": str(cache_dir()),
        "versions": str(versions_dir()),
        "current_file": str(current_file()),
        # `create=False`, and the resolved id is threaded into every machine-local
        # path below: `devteam path` and `devteam doctor` are questions, and a
        # diagnostic that mutates what it diagnoses reports on a world it just made.
        # `registry_file()` with no argument would mint one through `machine_dir()`.
        "machine_id": _reported,
        "machine": str(machine_dir(_reported)),
        "registry": str(registry_file(_reported)),
        "global_preferences": str(global_preferences_file()),
        "credentials": str(credentials_dir()),
        "secrets": str(machine_dir(_reported) / "secrets"),
        "projects": str(projects_dir()),
    }
