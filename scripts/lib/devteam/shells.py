"""Which ``bash`` to run a shell script with.

On POSIX it is whatever ``bash`` is on PATH. On Windows a bare ``bash`` is a trap: Windows
ships ``System32\\bash.exe``, the WSL launcher, which runs the script inside a Linux
distribution (or prints that none is installed) rather than in Git Bash, and whose children a
``taskkill /T`` of the launcher does not reach. The Microsoft Store alias under
``WindowsApps`` is the same kind of stub. So on Windows only an absolute Git Bash is used.
"""

from __future__ import annotations

import ntpath
import os
import shutil
import sys

_WSL_STUBS = ("\\windows\\system32\\", "\\windowsapps\\")
_GIT_BASH_DEFAULTS = (
    ("ProgramFiles", "Git", "bin", "bash.exe"),
    ("ProgramFiles(x86)", "Git", "bin", "bash.exe"),
    # The 64-bit Program Files as seen from a 32-bit process, whose ProgramFiles is the x86 one.
    ("ProgramW6432", "Git", "bin", "bash.exe"),
    ("LOCALAPPDATA", "Programs", "Git", "bin", "bash.exe"),
)


def is_windows():
    return sys.platform.startswith(("win", "msys", "cygwin"))


def _is_absolute(path):
    """A drive, UNC or extended path, or an MSYS/Cygwin ``/…`` one; never relative to the cwd."""
    return ntpath.isabs(path) or path.startswith("/")


def _is_wsl_stub(path):
    norm = path.replace("/", "\\").lower()
    return any(stub in norm for stub in _WSL_STUBS)


#: Folders Git for Windows puts ``git.exe`` in, relative to its install root. Its installer adds
#: ``cmd`` to PATH, never ``bin``, so ``bash`` is usually not on PATH while ``git`` is.
_GIT_EXE_DIRS = (("cmd",), ("bin",), ("mingw64", "bin"), ("mingw32", "bin"))


def _bash_beside_git(which, isfile):
    """``<root>\\bin\\bash.exe`` for the Git for Windows whose ``git.exe`` is on PATH, or None.

    Any ``git.exe`` in one of these layouts qualifies, so a ``bash.exe`` beside a Cygwin or MSYS2
    ``git`` in a ``bin`` folder is taken too; both run the installers as Git Bash does.
    """
    git = which("git")
    if not git or not _is_absolute(git) or _is_wsl_stub(git):
        return None
    folder = ntpath.dirname(git)
    for parts in _GIT_EXE_DIRS:
        root = folder
        matched = True
        for part in reversed(parts):
            if ntpath.basename(root).lower() != part:
                matched = False
                break
            root = ntpath.dirname(root)
        if matched and root:
            candidate = ntpath.join(root, "bin", "bash.exe")
            if isfile(candidate) and not _is_wsl_stub(candidate):
                return candidate
    return None


#: Where `find_git_bash` looks, for an error message that says so.
GIT_BASH_SEARCH = (
    "bash on PATH (not WSL's launcher), bin\\bash.exe beside the git.exe on PATH, and "
    "Git\\bin\\bash.exe under %ProgramFiles%, %ProgramFiles(x86)%, %ProgramW6432% and %LOCALAPPDATA%\\Programs"
)


def find_git_bash(which=None, environ=None, isfile=os.path.isfile):
    """An absolute Git Bash, or None. Never WSL's launcher or the Store alias."""
    which = shutil.which if which is None else which
    environ = os.environ if environ is None else environ
    # Absolute only, at every step: `shutil.which` on Windows also searches the current
    # folder, and a relative result would run a `bash.exe` a cloned project ships.
    found = which("bash")
    if found and _is_absolute(found) and not _is_wsl_stub(found):
        return found
    beside_git = _bash_beside_git(which, isfile)
    if beside_git:
        return beside_git
    for parts in _GIT_BASH_DEFAULTS:
        base = environ.get(parts[0])
        if base:
            candidate = ntpath.join(base, *parts[1:])  # always a Windows path
            if _is_absolute(candidate) and isfile(candidate):
                return candidate
    return None


def bash_path(windows=None, which=None, environ=None, isfile=os.path.isfile):
    """The ``bash`` to run a script with, or None when there is none to use."""
    which = shutil.which if which is None else which
    windows = is_windows() if windows is None else windows
    if not windows:
        return which("bash")
    return find_git_bash(which=which, environ=environ, isfile=isfile)
