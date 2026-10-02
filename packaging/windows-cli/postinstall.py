"""Install-time steps of the Windows CLI installer (ADR-0028), run by the embedded Python.

The NSIS script copies files; everything that needs logic happens here, in the interpreter
the installer has just placed, because NSIS string handling is the wrong tool for it — its
default 1024-character string limit would silently truncate a long user PATH on write.

    python.exe postinstall.py install   --instdir <dir>
    python.exe postinstall.py uninstall --instdir <dir>
    python.exe postinstall.py check-git

Standard library only: the embeddable distribution has no pip and needs none.
"""

import argparse
import io
import json
import ntpath
import os
import subprocess
import sys
import zipfile

#: `devteam`'s own exit code for "already installed" (errors.EXIT_CONFLICT).
EXIT_CONFLICT = 4
#: What `check-git` returns when no Git Bash is found. Not 1: a crash must not read as "missing".
GIT_MISSING = 10


def paths(instdir):
    return {
        "python": ntpath.join(instdir, "python", "python.exe"),
        "cli": ntpath.join(instdir, "cli", "scripts", "cli", "devteam"),
        "lib": ntpath.join(instdir, "cli", "scripts", "lib"),
        "launcher": ntpath.join(instdir, "launcher", "launcher.exe"),
        "bin": ntpath.join(instdir, "bin"),
        "exe": ntpath.join(instdir, "bin", "devteam.exe"),
        "payload": ntpath.join(instdir, "payload"),
    }


def launcher_bytes(stub, python, cli):
    """distlib's launcher format: the stub, a shebang naming the interpreter, then a zip.

    The stub reads the shebang off its own file and runs `"<python>" "<this exe>" args`;
    Python executes the exe as a zip application, whose `__main__` runs the CLI script.
    The interpreter path is absolute because it is written here, at install time.
    """
    shebang = '#!"{}"\r\n'.format(python).encode("utf-8")
    main = (
        "import runpy\n"
        "runpy.run_path({!r}, run_name='__main__')\n".format(cli)
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("__main__.py", main)
    return stub + shebang + buffer.getvalue()


def _same_dir(left, right):
    norm = lambda value: ntpath.normcase(os.path.expandvars(value)).rstrip("\\/")
    return norm(left) == norm(right)


def path_with(current, entry):
    """`current` with `entry` appended, or unchanged when it is already there."""
    segments = current.split(";") if current else []
    if any(_same_dir(segment, entry) for segment in segments if segment):
        return current
    return entry if not current else current.rstrip(";") + ";" + entry


def path_without(current, entry):
    """`current` with every segment naming `entry` removed; other segments kept as written."""
    segments = current.split(";") if current else []
    return ";".join(segment for segment in segments if not (segment and _same_dir(segment, entry)))


def _edit_user_path(transform):
    import winreg  # Windows only; imported here so the pure helpers above test anywhere.

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
        try:
            current, kind = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current, kind = "", winreg.REG_EXPAND_SZ
        if kind not in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
            kind = winreg.REG_EXPAND_SZ
        updated = transform(current)
        if updated == current:
            return False
        winreg.SetValueEx(key, "Path", 0, kind, updated)
    _broadcast_environment_change()
    return True


def _broadcast_environment_change():
    """Tell running programs (Explorer, new terminals) that the user environment changed."""
    import ctypes
    from ctypes import wintypes

    result = wintypes.DWORD()
    ctypes.windll.user32.SendMessageTimeoutW(
        0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, ctypes.byref(result)
    )


def write_launcher(path, data):
    """Replace `path` even while it runs: Windows lets a running .exe be renamed, not rewritten."""
    old = path + ".old"
    try:
        os.remove(old)
    except OSError:
        pass  # absent, or still running from the previous upgrade
    if os.path.exists(path):
        try:
            os.replace(path, old)
        except OSError:
            pass  # not in use after all; the open below overwrites it
    with open(path, "wb") as handle:
        handle.write(data)


def hint_current(where):
    """An install never moves `current`; say how when the store's current is another version."""
    sys.path.insert(0, where["lib"])
    try:
        from devteam.versions import version_from_tree

        bundled = version_from_tree(where["payload"])
        listed = subprocess.run(
            [where["python"], where["cli"], "store", "list", "--json"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True,
        )
        current = json.loads(listed.stdout or "{}").get("current")
    except (ImportError, ValueError, OSError):
        return
    if bundled and current and bundled != current:
        print("The store's current framework is {}. To use {}: devteam store use {} && devteam sync --all".format(
            current, bundled, bundled))


def store_install(where):
    """Install the bundled framework version; an installed version or a set `current` stays."""
    result = subprocess.run(
        [where["python"], where["cli"], "store", "install", "--from", where["payload"]],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    output = (result.stdout or "").strip()
    if result.returncode == 0:
        print(output or "framework installed into the store")
        return 0
    if result.returncode == EXIT_CONFLICT:
        print("framework version already in the store; left as it is")
        return 0
    print("devteam store install failed ({}): {}".format(result.returncode, output))
    return result.returncode


def cmd_install(instdir):
    where = paths(instdir)
    with open(where["launcher"], "rb") as handle:
        stub = handle.read()
    os.makedirs(where["bin"], exist_ok=True)
    write_launcher(where["exe"], launcher_bytes(stub, where["python"], where["cli"]))
    print("wrote {}".format(where["exe"]))
    if _edit_user_path(lambda current: path_with(current, where["bin"])):
        print("added {} to the user PATH".format(where["bin"]))
    status = store_install(where)
    if status == 0:
        hint_current(where)
    return status


def cmd_uninstall(instdir):
    where = paths(instdir)
    if _edit_user_path(lambda current: path_without(current, where["bin"])):
        print("removed {} from the user PATH".format(where["bin"]))
    return 0


def cmd_check_git(instdir):
    """The CLI's own Git Bash lookup (ADR-0026), so the installer and the CLI cannot disagree."""
    sys.path.insert(0, paths(instdir)["lib"])
    from devteam.shells import find_git_bash

    found = find_git_bash()
    print(found or "no Git Bash found")
    return 0 if found else GIT_MISSING


def main(argv=None):
    parser = argparse.ArgumentParser(prog="postinstall")
    parser.add_argument("command", choices=("install", "uninstall", "check-git"))
    parser.add_argument("--instdir", default=ntpath.dirname(ntpath.abspath(__file__)))
    args = parser.parse_args(argv)
    handler = {"install": cmd_install, "uninstall": cmd_uninstall, "check-git": cmd_check_git}[args.command]
    return handler(args.instdir)


if __name__ == "__main__":
    sys.exit(main())
