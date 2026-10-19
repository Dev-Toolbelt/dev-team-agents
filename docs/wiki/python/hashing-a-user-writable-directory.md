# Hashing a directory that users or tools can write

**Origin:** provenance and content hash for installed skills (ADR-0040) | 2026-10-19
**Tags:** os.walk, symlink, O_NOFOLLOW, dir_fd, scandir, RecursionError, FIFO, sha256, UnicodeDecodeError, jsonio

> `os.walk` skips symlinked directories without a warning, so a hash over it quietly omits them. Walk the tree with directory file descriptors, open every file with `O_NOFOLLOW|O_NONBLOCK`, and check the type on the open handle, not on the path.

---

## What it is

Installed skills live in directories a user, or another tool, can write. A content hash over such a tree must reflect what is really there, must not follow links out of the tree, and must not block or exhaust memory.

## How it works

| Hazard | Effect | Fix used in `scripts/lib/devteam/global_skills.py` |
|--------|--------|-----------------------------------------------------|
| `os.walk` does not descend into symlinked dirs | They add nothing to the hash | Record symlinks by target string |
| `islink` check, then listing by path | A swap between check and read (race) | Open each directory with `O_RDONLY\|O_DIRECTORY\|O_NOFOLLOW`, relative to the base (`dir_fd=`), list with `os.scandir(fd)` (`_entries_by_fd`, `_open_dir_at`) |
| Reading a FIFO | Blocks forever | Open files `O_NOFOLLOW\|O_NONBLOCK`, then `fstat` the handle and require `S_ISREG` (`_file_digest`) |
| `read_bytes()` | Holds a whole file in memory | Stream into sha256 in chunks |
| Recursive walk | `RecursionError` near 1000 levels | Iterate with a stack of relative paths, reopening one component at a time |
| One fd per level | Hits the open-file limit instead | Same stack; no fd is kept across levels |
| Empty directories | Invisible to the hash | Mark them explicitly |

Where `os.supports_fd` or `os.supports_dir_fd` lack the calls (Windows), use a path-based fallback.

## Gotchas

- `UnicodeDecodeError` is a `ValueError`, not an `OSError`, and `jsonio.read_json` does not convert it. A non-UTF-8 JSON record escaped `except EnvError` until the handler also caught `ValueError`. Catch both.
- To prove the walk does not recurse, lower `sys.setrecursionlimit` below the tree depth. Do not build a 1000-level tree: O(n·depth) reopens took 94 s.

## References

- `scripts/lib/devteam/global_skills.py` (`_entries_by_fd`, `_open_dir_at`, `_file_digest`, `_load_lock_file`)
- ADR-0040 (`docs/development/adrs/0040-*.md`)
