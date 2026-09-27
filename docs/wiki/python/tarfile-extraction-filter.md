# tarfile extraction is only safe if you say so

**Origin:** CRITICAL archive-escape finding in `devteam update` | 2026-09-27
**Tags:** tarfile, extractall, filter, data, tarslip, linkname, symlink, CVE, python 3.14

> A member-name check is not enough: the escape hides in `linkname`. And `extractall`'s default filter changed in 3.14, so testing only the newest interpreter hides the bug on every version users actually run.

---

## What it is

The familiar guard — reject absolute paths and `..` in `member.name` — leaves the whole link class
open. A `SYMTYPE`/`LNKTYPE` member whose **`linkname`** escapes creates a link inside the
extraction directory, and then any later member whose own name is perfectly clean is written
*through* that link, outside the tree.

## How it works

```python
tar.extractall(dest, members=members, filter="data")   # 3.12+; rejects links, devices, setuid
```

plus an explicit floor, because `filter=` does not exist before 3.12 and the default below 3.14 is
`fully_trusted`:

```python
if member.issym() or member.islnk():
    resolved = os.path.normpath(os.path.join(str(Path(member.name).parent), member.linkname))
    if os.path.isabs(resolved) or resolved == ".." or resolved.startswith(".." + os.sep):
        raise ...
if member.isdev() or member.isfifo():
    raise ...
```

## Gotchas

- **CI on `python-version: "3.x"` masks this**, because `3.x` resolves to the newest release, where
  `data` is already the default. Pin the floor as its own matrix leg — the defect is only reachable
  on the interpreters you are not testing.
- Both creating a new file and overwriting an existing one outside the tree are reachable; the write
  runs as the invoking user, and a dropped shim in a user-writable `PATH` directory (for example
  Homebrew's `bin` on Apple Silicon) turns file write into code execution.
- Validating after extraction is not validating. A version string checked once the archive is
  already on disk protects nothing.
- Copy extracted trees with `symlinks=False` if anything will later execute from them; otherwise an
  archive symlink survives into the destination.

## References

- `scripts/lib/devteam/update.py` — `_safe_members`, `verify_digest`
- `tests/test_update_and_contract.py` — one test per rejected member class
