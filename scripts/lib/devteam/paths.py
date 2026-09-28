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

import os
import re
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


def machine_id():
    """This machine's id, creating it on first use.

    Concurrent first uses converge on one value: the file is created with
    ``O_EXCL``, and the process that loses the race reads the winner's id rather
    than overwriting it. No lock is taken here on purpose — ``locks_dir()``
    resolves through this function, so locking would be circular.
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
    value = _read_machine_id(path) or _create_machine_id(path)
    _MACHINE_ID_CACHE[key] = value
    return value


def _read_machine_id(path):
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return raw if _MACHINE_ID_RE.fullmatch(raw) else None


def _create_machine_id(path):
    _mkdir_owner_only(path.parent)
    value = str(uuid.uuid4())
    try:
        handle = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        # Another process got there first, or the file holds something unparseable.
        existing = _read_machine_id(path)
        if existing:
            return existing
        raise EnvError(
            "{} exists but does not hold a UUID".format(path),
            hint=(
                "Fix or move the file by hand. dev-team-agents will not replace it: a new id "
                "would point at a machine subtree your existing records are not in."
            ),
        )
    with os.fdopen(handle, "w", encoding="utf-8") as fh:
        fh.write(value + "\n")
    try:
        # os.open's mode is masked by umask; the store's files are owner-only by
        # contract (jsonio.STORE_FILE_MODE), not by whatever the shell was set to.
        os.chmod(str(path), 0o600)
    except OSError:
        pass
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
)

#: Top-level entries of ``data/`` that never leave this machine.
MACHINE_LOCAL_STORE_ENTRIES = (MACHINE_ID_FILE, MACHINES_DIR, "locks")


def is_machine_local_record(name):
    """True for a per-project record that belongs in the machine subtree.

    Dot-prefixed names are machine-local as a class: every one of them is a cache,
    an ETag, a once-per-day stamp or a session marker — state this machine observed.
    """
    base = str(name)
    return base.startswith(".") or base in MACHINE_LOCAL_RECORDS


# ── portable records ─────────────────────────────────────────────────────────


def global_preferences_file():
    return data_dir() / "preferences.json"


def credentials_dir():
    return data_dir() / "credentials"


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
    """Everything ``devteam path`` reports, as plain strings."""
    return {
        "platform": platform_key(),
        "devteam_home": str(devteam_home()) if devteam_home() else None,
        "core": str(core_dir()),
        "data": str(data_dir()),
        "cache": str(cache_dir()),
        "versions": str(versions_dir()),
        "current_file": str(current_file()),
        "machine_id": machine_id(),
        "machine": str(machine_dir()),
        "registry": str(registry_file()),
        "global_preferences": str(global_preferences_file()),
        "credentials": str(credentials_dir()),
        "projects": str(projects_dir()),
    }
