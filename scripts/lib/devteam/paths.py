"""Store location resolution.

Two stores with different lifetimes (ADR-0007):

* **core** — versioned canonical trees plus the ``current`` pointer. Disposable:
  an uninstall may remove it and ``devteam update`` rebuilds it.
* **data** — registry, preferences, per-project memory, credential references.
  Survives uninstall, and on Windows lives in the roaming profile so it is
  covered by profile backup.

``$DEVTEAM_HOME`` overrides every platform convention and is the seam the test
suite uses, so no test touches a real user directory.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "dev-team-agents"

#: Set to ``darwin``/``win32``/``linux`` to exercise another platform's layout.
PLATFORM_ENV = "DEVTEAM_PLATFORM"
HOME_ENV = "DEVTEAM_HOME"


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


def registry_file():
    return data_dir() / "registry.json"


def global_preferences_file():
    return data_dir() / "preferences.json"


def credentials_dir():
    return data_dir() / "credentials"


def projects_dir():
    return data_dir() / "projects"


def project_data_dir(project_id):
    return projects_dir() / project_id


def quarantine_dir(stamp):
    return data_dir() / "quarantine" / stamp


def render_cache_dir(version, provider):
    return cache_dir() / "render" / version / provider


def locks_dir():
    return data_dir() / "locks"


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
        "registry": str(registry_file()),
        "global_preferences": str(global_preferences_file()),
        "credentials": str(credentials_dir()),
        "projects": str(projects_dir()),
    }
