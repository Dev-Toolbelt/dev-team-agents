# `os.kill(pid, 0)`, deleting an open file and `select()` on a pipe all mean something else on Windows

**Origin:** Windows CI hang in `test_integrations` and the store lock | 2026-10-02
**Tags:** windows, os.kill, signal 0, TerminateProcess, liveness probe, lock, unlink, PermissionError, sharing violation, select, pipe, stdin, hook, timeout

> Three POSIX idioms that probe or clean up compile and run on Windows, and each one does something else there. All three were in the store lock or the hook stdin reader, and each cost a hang or worse.

---

## `os.kill(pid, 0)` kills the process

On POSIX, signal 0 only checks that the pid exists. On Windows, `os.kill` with anything other than `CTRL_C_EVENT` / `CTRL_BREAK_EVENT` calls `TerminateProcess`. The stale-lock check (`Lock._holder_is_alive`) would have terminated the process holding the lock. On Windows the probe is `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)` followed by `GetExitCodeProcess == STILL_ACTIVE`. `ERROR_ACCESS_DENIED` from `OpenProcess` means the process exists. See `lock._windows_pid_alive`.

## A file another process has open cannot be deleted

POSIX unlinks an open file; Windows refuses with a sharing violation (`PermissionError`). `Lock.release` deleted `owner.json` while a waiter happened to be reading it to age the lock. The error was swallowed, the lock directory stayed, and every waiter timed out after 15 s. `Lock._remove` now retries `PermissionError` for about 2 s. A bare `except OSError: pass` around a delete is the pattern to look for.

## `select()` does not take pipes

`select.select` on Windows accepts sockets only. A hook command that reads stdin with a deadline cannot use it, and a plain `read()` blocks for good when the provider leaves stdin open and silent. `cli._read_hook_stdin` reads on a daemon thread and stops waiting at the same deadline the POSIX path uses, keeping whatever arrived.

## References

- `scripts/lib/devteam/lock.py`: `_windows_pid_alive`, `Lock._remove`
- `scripts/lib/devteam/cli.py`: `_read_hook_stdin`
- `tests/test_store_primitives.py`: `LockTest`, covering the release retry and the Windows liveness probe
- `docs/wiki/windows/nul-is-a-tty.md`: the other stdin trap
