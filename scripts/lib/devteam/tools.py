"""Provision the pinned helper tools on this machine (ADR-0060).

``devteam tools install`` is the one place that installs the tools agents lean on —
code search, JSON extraction, diff review, secret scanning, static analysis. The CLI
installer, every ``devteam bind``, the health check and ``/devteam:install`` all call
it, so the install rules live here and nowhere else.

What it does, and what it refuses to do:

* A tool already on ``PATH`` (or already in the bin directory) is reported as present
  and nothing is downloaded. A bind on a machine that has everything costs a few
  ``which`` lookups.
* A binary tool comes from the release asset pinned in ``tool-pins.json``. The bytes
  are hashed before anything is written; a digest that does not match installs
  nothing. Only the one named executable is read out of an archive — nothing is
  extracted, so an archive cannot write outside the bin directory.
* A Python tool gets a virtualenv of its own under the tools home, created with an
  interpreter that meets the tool's floor, and ``pip install <package>==<version>``.
  The top-level version is pinned; transitive hashes are not (ADR-0060 says why).
* No ``sudo`` and no system package manager. Homebrew is used only as a fallback for a
  tool that has no pinned build for this platform, because it installs into the
  user's own prefix.
* Nothing here raises past ``install``: a tool that cannot be installed is reported as
  ``skipped`` or ``failed`` with a reason, and the caller carries on.

``DEVTEAM_SKIP_TOOLS=1`` turns every install off — for CI images and managed machines.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path

from . import paths
from .errors import ConflictError, UsageError
from .lock import Lock

PINS_FILE = Path(__file__).with_name("tool-pins.json")

SKIP_ENV = "DEVTEAM_SKIP_TOOLS"
BIN_DIR_ENV = "DEVTEAM_BIN_DIR"
TOOLS_HOME_ENV = "DEVTEAM_TOOLS_HOME"

DOWNLOAD_TIMEOUT = 60
MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024
PIP_TIMEOUT = 1800
BREW_TIMEOUT = 1800
LOCK_TIMEOUT = 2.0
LOCK_STALE_AFTER = 3600.0

PRESENT = "present"
INSTALLED = "installed"
SKIPPED = "skipped"
FAILED = "failed"
MISSING = "missing"

#: Alternate names a distribution installs a tool under (Debian ships fd as `fdfind`).
ALIASES = {"fd": ("fdfind",)}

_ARCHES = {"x86_64": "x64", "amd64": "x64", "arm64": "arm64", "aarch64": "arm64"}


def load_pins():
    with PINS_FILE.open(encoding="utf-8") as handle:
        doc = json.load(handle)
    return doc["tools"]


def skip_requested():
    return os.environ.get(SKIP_ENV, "").strip().lower() not in ("", "0", "false", "no")


def host_os():
    return {"win32": "windows"}.get(paths.platform_key(), paths.platform_key())


def host_platform():
    """``<os>-<arch>``, the key `tool-pins.json` indexes assets by; arch ``None`` if unknown."""
    arch = _ARCHES.get(platform.machine().lower())
    return "{}-{}".format(host_os(), arch) if arch else None


def _exe(name):
    return name + ".exe" if host_os() == "windows" else name


def bin_dir():
    override = os.environ.get(BIN_DIR_ENV)
    if override:
        return Path(override).expanduser()
    if host_os() == "windows":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        # The Windows CLI installer puts this directory on the user PATH.
        return Path(base) / "Programs" / "devteam" / "bin"
    return Path.home() / ".local" / "bin"


def tools_home():
    override = os.environ.get(TOOLS_HOME_ENV)
    if override:
        return Path(override).expanduser()
    if host_os() == "windows":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "devteam" / "tools"
    cli_home = os.environ.get("DEVTEAM_CLI_HOME")
    base = Path(cli_home).expanduser() if cli_home else Path.home() / ".local" / "share" / "devteam"
    return base / "tools"


def find_existing(tool):
    """The path of an installed copy of ``tool`` — on PATH or in the bin directory — or ``None``."""
    for name in (tool["binary"],) + ALIASES.get(tool["name"], ()):
        found = shutil.which(name)
        if found:
            return found
        for candidate in (bin_dir() / _exe(name), bin_dir() / (name + ".cmd")):
            if candidate.is_file():
                return str(candidate)
    return None


def _select(names):
    pins = load_pins()
    if not names:
        return pins
    known = {tool["name"]: tool for tool in pins}
    unknown = [name for name in names if name not in known]
    if unknown:
        raise UsageError(
            "unknown tool(s): {}".format(", ".join(unknown)),
            hint="Known tools: {}".format(", ".join(sorted(known))),
        )
    return [tool for tool in pins if tool["name"] in names]


def _entry(tool, status, **extra):
    entry = {
        "name": tool["name"],
        "version": tool["version"],
        "purpose": tool["purpose"],
        "status": status,
        "method": None,
        "path": None,
        "reason": None,
    }
    entry.update(extra)
    return entry


def list_tools():
    rows = []
    for tool in load_pins():
        found = find_existing(tool)
        rows.append(_entry(tool, PRESENT if found else MISSING, path=found))
    return {"bin_dir": str(bin_dir()), "platform": host_platform(), "tools": rows}


# ── downloads ────────────────────────────────────────────────────────────────


def _download(url):
    if not url.startswith("https://"):
        raise ValueError("refusing a non-HTTPS URL")
    request = urllib.request.Request(url, headers={"User-Agent": "devteam-tools"})
    chunks, total = [], 0
    with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:  # nosec - HTTPS only, digest-checked
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_DOWNLOAD_BYTES:
                raise ValueError("download exceeds {} bytes".format(MAX_DOWNLOAD_BYTES))
            chunks.append(chunk)
    return b"".join(chunks)


def _member(data, fmt, exe_name):
    """The bytes of the one executable named ``exe_name`` inside the asset."""
    if fmt == "raw":
        return data
    if fmt == "tar.gz":
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            for member in archive.getmembers():
                if member.isfile() and Path(member.name).name == exe_name:
                    return archive.extractfile(member).read()
    elif fmt == "zip":
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for name in archive.namelist():
                if not name.endswith("/") and Path(name).name == exe_name:
                    return archive.read(name)
    raise ValueError("{} not found in the {} asset".format(exe_name, fmt))


def _write_executable(target, payload):
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(".{}.tmp-{}".format(target.name, os.getpid()))
    # O_EXCL and O_NOFOLLOW: a file or link already sitting at the temp name is never written through.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    fd = os.open(str(tmp), flags, 0o755)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
        os.chmod(str(tmp), 0o755)
        os.replace(str(tmp), str(target))
    finally:
        if os.path.lexists(str(tmp)):
            os.unlink(str(tmp))


def _install_binary(tool, asset):
    data = _download(asset["url"])
    digest = hashlib.sha256(data).hexdigest()
    if digest != asset["sha256"].lower():
        return _entry(
            tool, FAILED, method="download",
            reason="sha256 mismatch (expected {}…, got {}…) — nothing installed".format(
                asset["sha256"][:12], digest[:12]
            ),
        )
    exe_name = _exe(tool["binary"])
    target = bin_dir() / exe_name
    _write_executable(target, _member(data, asset["format"], exe_name))
    return _entry(tool, INSTALLED, method="download", path=str(target))


# ── python tools ─────────────────────────────────────────────────────────────


def _python_version(executable):
    try:
        out = subprocess.run(
            # `venv` and `ensurepip` too: an embeddable Python (the Windows CLI bundles one)
            # has neither, and could not create the virtualenv a Python tool needs.
            [executable, "-I", "-c", "import sys, venv, ensurepip; print('%d %d' % sys.version_info[:2])"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True, timeout=20,
        ).stdout.split()
        return int(out[0]), int(out[1])
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None


#: Tried first, newest to oldest: a release this recent has wheels for every dependency, and the
#: install refuses source builds. A newer interpreter is tried only after these.
SETTLED_MINORS = (13, 12, 11, 10)


def find_python(minimum):
    """An interpreter at or above ``minimum`` (a ``(major, minor)`` pair), or ``None``."""
    minors = [m for m in SETTLED_MINORS if m >= minimum[1]] + list(range(max(SETTLED_MINORS) + 1, 21))
    candidates = [shutil.which("python3.{}".format(minor)) for minor in minors]
    candidates += [sys.executable, shutil.which("python3"), shutil.which("python")]
    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        version = _python_version(candidate)
        if version and version >= tuple(minimum):
            return candidate
    return None


def _venv_bin(venv):
    return venv / ("Scripts" if host_os() == "windows" else "bin")


def _link_into_bin(tool, executable):
    """Expose ``executable`` in the bin directory: a symlink on POSIX, a ``.cmd`` shim on Windows."""
    if host_os() == "windows":
        shim = bin_dir() / (tool["binary"] + ".cmd")
        _write_executable(shim, '@"{}" %*\r\n'.format(executable).encode("utf-8"))
        return shim
    link = bin_dir() / tool["binary"]
    link.parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(link):
        # Only a dangling link back into our own tools home is ours to replace.
        home = os.path.join(str(tools_home()), "")
        if not (link.is_symlink() and os.path.join(os.readlink(str(link)), "").startswith(home)):
            raise ValueError("{} exists and is not a link this command made".format(link))
        link.unlink()
    os.symlink(str(executable), str(link))
    return link


def _install_python(tool, interpreter):
    venv = tools_home() / tool["name"]
    if venv.exists():
        # A venv left by an earlier, broken attempt is moved aside, never deleted: the health
        # check runs this, and a health check never deletes.
        aside = "{}.broken-{}-{}".format(venv.name, int(time.time()), os.getpid())
        os.replace(str(venv), str(venv.with_name(aside)))
    venv.parent.mkdir(parents=True, exist_ok=True)
    # `-I` and a cwd of our own: `-m` puts the current directory first on sys.path, and the
    # current directory is the project being bound — a planted `venv.py` or `pip/` would run.
    subprocess.run(
        [interpreter, "-I", "-m", "venv", str(venv)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, timeout=300, cwd=str(tools_home()),
    )
    venv_python = _venv_bin(venv) / _exe("python")
    subprocess.run(
        # Wheels only: an sdist would run its own build code during an unattended install.
        [str(venv_python), "-I", "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "--quiet",
         "--only-binary=:all:", "{}=={}".format(tool["package"], tool["version"])],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, timeout=PIP_TIMEOUT, cwd=str(tools_home()),
    )
    executable = _venv_bin(venv) / _exe(tool["binary"])
    if not executable.exists():
        return _entry(tool, FAILED, method="pip", reason="{} did not install a {} executable".format(
            tool["package"], tool["binary"]))
    return _entry(tool, INSTALLED, method="pip", path=str(_link_into_bin(tool, executable)))


# ── fallback ─────────────────────────────────────────────────────────────────


def _install_brew(tool):
    brew = shutil.which("brew")
    # Install this one formula only: no auto-update, and no upgrade of the user's other formulae.
    env = dict(
        os.environ, HOMEBREW_NO_AUTO_UPDATE="1", HOMEBREW_NO_ENV_HINTS="1",
        HOMEBREW_NO_INSTALL_UPGRADE="1", HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK="1",
    )
    subprocess.run(
        [brew, "install", "--quiet", tool["brew"]],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, timeout=BREW_TIMEOUT, env=env,
        cwd=str(tools_home()),
    )
    return _entry(tool, INSTALLED, method="brew", path=shutil.which(tool["binary"]))


def _brew_usable(tool):
    return bool(tool.get("brew")) and host_os() != "windows" and shutil.which("brew") is not None


# ── install ──────────────────────────────────────────────────────────────────


def _install_one(tool, done):
    found = find_existing(tool)
    if found:
        return _entry(tool, PRESENT, path=found)
    # A requirement installed earlier in this run, or already on the machine when it was not selected.
    pins = {pin["name"]: pin for pin in load_pins()}
    missing = [
        name for name in tool.get("requires", ())
        if done.get(name) not in (PRESENT, INSTALLED)
        and not (name not in done and name in pins and find_existing(pins[name]))
    ]
    if missing:
        return _entry(tool, SKIPPED, reason="needs {}".format(", ".join(missing)))
    if host_os() not in tool.get("platforms", (host_os(),)):
        return _entry(tool, SKIPPED, reason="no supported build for {} — use WSL or Docker".format(host_os()))

    if tool["kind"] == "binary":
        asset = tool["assets"].get(host_platform() or "")
        if asset:
            return _install_binary(tool, asset)
        if _brew_usable(tool):
            return _install_brew(tool)
        return _entry(tool, SKIPPED, reason="no pinned build for {}".format(host_platform() or "this CPU"))

    interpreter = find_python(tool["python_min"])
    if interpreter:
        try:
            return _install_python(tool, interpreter)
        except subprocess.CalledProcessError:
            # Usually a dependency with no wheel for this interpreter yet; Homebrew ships its own.
            if not _brew_usable(tool):
                raise
            return _install_brew(tool)
    if _brew_usable(tool):
        return _install_brew(tool)
    return _entry(tool, SKIPPED, reason="needs Python {}.{}+".format(*tool["python_min"]))


def _failure(tool, exc):
    if isinstance(exc, subprocess.CalledProcessError):
        detail = (exc.stderr or b"")
        detail = detail.decode("utf-8", "replace") if isinstance(detail, bytes) else detail
        lines = [line for line in detail.strip().splitlines() if line.strip()]
        reason = lines[-1][:200] if lines else "exit {}".format(exc.returncode)
    else:
        reason = "{}: {}".format(type(exc).__name__, exc)[:200]
    return _entry(tool, FAILED, reason=reason)


def format_entry(entry):
    """One human line: ``  gitleaks 8.30.1  — blocks commits…  ✓ installed``."""
    marks = {PRESENT: "✓ already present", INSTALLED: "✓ installed", MISSING: "· missing"}
    status = marks.get(entry["status"]) or "✗ {} ({})".format(entry["status"], entry["reason"])
    if entry["status"] == INSTALLED and entry["method"] == "brew":
        status += " via Homebrew (its version, not the pin)"
    # A copy found on PATH is whatever version the user has, not necessarily the pin.
    label = entry["name"] if entry["status"] == PRESENT else "{} {}".format(entry["name"], entry["version"])
    return "  {:<18} — {:<48} {}".format(label, entry["purpose"], status)


def install(names=None, progress=None):
    """Install every missing pinned tool (or only ``names``); never raises for a tool that fails.

    ``progress`` is called with each finished entry, so a caller can show the list as
    it fills instead of after a multi-minute silence.
    """
    selected = _select(names)
    payload = {
        "bin_dir": str(bin_dir()),
        "platform": host_platform(),
        "skipped_all": None,
        "on_path": _on_path(bin_dir()),
        "tools": [],
    }
    if skip_requested():
        payload["skipped_all"] = "{}=1".format(SKIP_ENV)
        payload["tools"] = [_entry(tool, SKIPPED, reason=payload["skipped_all"]) for tool in selected]
        return payload

    with contextlib.ExitStack() as stack:
        try:
            tools_home().mkdir(parents=True, exist_ok=True)
            stack.enter_context(
                Lock(tools_home() / ".install.lock", timeout=LOCK_TIMEOUT, stale_after=LOCK_STALE_AFTER)
            )
        except (ConflictError, OSError) as exc:
            reason = "another tools install is running" if isinstance(exc, ConflictError) else str(exc)
            payload["skipped_all"] = reason
            payload["tools"] = [_entry(tool, SKIPPED, reason=reason) for tool in selected]
            return payload
        done = {}
        for tool in selected:
            try:
                entry = _install_one(tool, done)
            except Exception as exc:  # noqa: BLE001 - one tool never stops the others, nor the caller
                entry = _failure(tool, exc)
            done[tool["name"]] = entry["status"]
            payload["tools"].append(entry)
            if progress:
                progress(entry)
    return payload


def _on_path(directory):
    entries = os.environ.get("PATH", "").split(os.pathsep)
    target = os.path.normcase(os.path.abspath(str(directory)))
    return any(os.path.normcase(os.path.abspath(entry)) == target for entry in entries if entry)


def header():
    return "Installing tools (set {}=1 to skip):".format(SKIP_ENV)


def summary_lines(payload):
    """The human block every caller prints: header, one line per tool, PATH note."""
    if payload.get("skipped_all"):
        return ["Tools: not installed ({})".format(payload["skipped_all"])]
    lines = [header()]
    lines += [format_entry(entry) for entry in payload["tools"]]
    if any(e["status"] == INSTALLED and e["method"] != "brew" for e in payload["tools"]) and not payload["on_path"]:
        lines.append("  add {} to your PATH so these tools can be found".format(payload["bin_dir"]))
    return lines
