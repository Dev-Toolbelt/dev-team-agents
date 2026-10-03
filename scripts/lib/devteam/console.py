"""Terminal detection shared by the CLI dispatcher and the commands that prompt."""

from __future__ import annotations

import os
import sys


def stdin_is_console():
    """Whether stdin is an interactive console a prompt can wait on.

    ``isatty()`` alone is not enough on Windows: the ``NUL`` device is a character device, so a
    command run with stdin from ``NUL`` (a hook, a script, ``subprocess.DEVNULL``) reports a tty
    and ``getpass`` then waits on a console that does not exist. Only a handle the console API
    accepts is one.
    """
    stream = sys.stdin
    if stream is None or not stream.isatty():
        return False
    if os.name != "nt":
        return True
    try:
        import ctypes
        import msvcrt

        mode = ctypes.c_uint32()
        handle = msvcrt.get_osfhandle(stream.fileno())
        return bool(ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(mode)))
    except (OSError, ValueError, AttributeError):
        return False
