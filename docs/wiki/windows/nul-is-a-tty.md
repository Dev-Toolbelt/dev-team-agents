# `NUL` is a tty on Windows: an `isatty()` check is not "a human is there"

**Origin:** `test_integrations` hanging the Windows CI job | 2026-10-02
**Tags:** windows, NUL, isatty, tty, getpass, stdin, DEVNULL, GetConsoleMode, console, prompt, hang, integration connect, cred set

> On Windows the `NUL` device is a character device, so `sys.stdin.isatty()` is `True` when stdin is `NUL`. Code that prompts "when interactive" then calls `getpass`, which waits forever on a console that does not exist.

---

## Where it bites

`devteam integration connect` and `devteam cred set` read the secret from stdin, and prompt with `getpass` only when stdin is interactive. Run with stdin from `NUL`, which is what `subprocess.DEVNULL`, a hook or a scheduled script gives you, the command hung for good. It did not time out or fail, and the CI job sat until it was cancelled.

## The check that works

Ask the console API: `GetConsoleMode` succeeds only on a real console handle. `cli._stdin_is_console()` uses `isatty()` first (cheap, and enough on POSIX), and on Windows also needs `kernel32.GetConsoleMode(msvcrt.get_osfhandle(fd))` to succeed. When it is `False`, stdin is read as data. `NUL` reads empty, so the command reports "no value" instead of waiting.

## Gotchas

- The same `isatty()` test guarding "do not read stdin, it is a terminal" (`_hook_payload`, `cred local patch`) is harmless with `NUL`, because both branches end without blocking. Only a branch that **waits for a person** needs the console check.
- `os.isatty(fd)` and `msvcrt`-level checks agree with `sys.stdin.isatty()`, so none of them is a substitute for the console API.

## References

- `scripts/lib/devteam/cli.py`: `_stdin_is_console`, `_read_token_from_stdin`, `_read_secret_from_stdin`
- `docs/wiki/windows/os-kill-and-unlink-differ.md`: the other stdin trap (`select()` on pipes)
