# Creating a singleton file when the lock itself depends on it

**Origin:** v3 M2.1 — `data/machine-id` for the portable/machine-local store split | 2026-09-27
**Tags:** O_EXCL, os.open, machine-id, circular dependency, lock, os.link, Windows, race, singleton, first use

> Every store mutation in this CLI takes a lock — except the one that creates `data/machine-id`,
> because `locks_dir()` resolves *through* the machine id. `O_EXCL` replaces the lock; the loser of
> the race reads the winner's value instead of writing its own.

---

## What it is

`paths.machine_id()` creates `data/machine-id` on first use. It cannot use `store_lock()`: the lock
file lives at `data/machines/<machine-id>/locks/`, so taking a lock requires the id that the lock
would be protecting. Reaching for the usual "wrap it in a lock" answer here deadlocks or, worse,
silently creates a second id under a different path.

## How it works

```python
try:
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
except FileExistsError:
    return _read_machine_id(path)   # another process won — adopt its value
with os.fdopen(fd, "w", encoding="utf-8") as fh:
    fh.write(value + "\n")
```

`O_CREAT | O_EXCL` is a single atomic filesystem operation: exactly one caller creates the file, and
every other caller gets `FileExistsError` and reads what the winner wrote. The result is
*convergence* rather than exclusion — nobody waits, and all callers end up with the same id.

## Gotchas

- **`os.link` is the trap answer.** The hardlink-to-a-temp-file idiom gives the same atomicity on
  POSIX, and `os.link` exists on Windows, but it needs NTFS and the right privileges and fails on
  FAT/exFAT and some network shares. `O_EXCL` on `os.open` is portable to every filesystem Python
  supports.
- **Reading before creating is not enough.** The read is only an optimisation; the create must still
  be exclusive, because two processes can both read "absent" before either writes.
- **A `FileExistsError` whose content is not a UUID is an error, not a race.** Something else wrote
  that path. Raise and name the file — do not overwrite it, and do not fall back to generating a new
  id, which would hand the caller a directory the previous records are not in.
- **The value is cached per resolved path, not globally.** `$DEVTEAM_HOME` changes per test, so a
  single module-level cache would leak one test's identity into the next.
- **Deleting the store keeps the cached id for the life of the process.** That is correct: it is still
  the same machine. Nothing re-reads the file mid-run, which is fine for a CLI and would not be for a
  daemon.

## References

- `scripts/lib/devteam/paths.py` — `machine_id()`, `_create_machine_id()`
- ADR-0013 — why the id exists at all, and why it cannot be assigned retroactively
- `tests/test_machine_layout.py` — `MachineIdentityTest`
