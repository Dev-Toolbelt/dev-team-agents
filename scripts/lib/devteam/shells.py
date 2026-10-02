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
    ("LOCALAPPDATA", "Programs", "Git", "bin", "bash.exe"),
)


def is_windows():
    return sys.platform.startswith(("win", "msys", "cygwin"))


def _is_wsl_stub(path):
    norm = path.replace("/", "\\").lower()
    return any(stub in norm for stub in _WSL_STUBS)


def find_git_bash(which=None, environ=None, isfile=os.path.isfile):
    """An absolute Git Bash, or None. Never WSL's launcher or the Store alias."""
    which = shutil.which if which is None else which
    environ = os.environ if environ is None else environ
    found = which("bash")
    if found and not _is_wsl_stub(found):
        return found
    for parts in _GIT_BASH_DEFAULTS:
        base = environ.get(parts[0])
        if base:
            candidate = ntpath.join(base, *parts[1:])  # always a Windows path
            if isfile(candidate):
                return candidate
    return None


def bash_path(windows=None, which=None, environ=None, isfile=os.path.isfile):
    """The ``bash`` to run a script with, or None when there is none to use."""
    which = shutil.which if which is None else which
    windows = is_windows() if windows is None else windows
    if not windows:
        return which("bash")
    return find_git_bash(which=which, environ=environ, isfile=isfile)
