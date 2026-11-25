# A junction is a directory to Python, and removing it the wrong way deletes the store

**Origin:** link mode on Windows without Developer Mode, implemented with NTFS junctions | 2026-11-25
**Tags:** Windows, junction, symlink, is_symlink, is_link, remove_link, rmtree, quarantine, bind, link mode

> `Path.is_symlink()` is False for a junction. Code that asks it treats the junction as real content and acts on the files it points to.

---

## What it is

Link mode falls back to an NTFS junction where `os.symlink` is refused (ADR-0069). A junction behaves like a
directory symlink for every tool that reads through it, but Python's link checks only know symlinks:
`is_symlink()` and `os.path.islink()` return False, `is_dir()` returns True, `os.walk` descends into it.

## How it works

- `paths.is_link` is True for a symlink or a junction. It reads `st_file_attributes` and `st_reparse_tag`
  from `os.lstat`, because `Path.is_junction` needs Python 3.12 and the CLI floor is 3.9.
- `paths.remove_link` deletes the link only: `os.unlink` for a symlink, `os.rmdir` for a junction
  (RemoveDirectoryW removes the reparse point, not the target's files).
- `os.readlink` reads a junction's target on Windows, with the `\\?\` prefix `paths.realpath_normalized`
  already strips.

## Gotchas

- `quarantine.move` refuses a junction. On one volume `shutil.move` renames the junction, but across
  volumes it copies the target's files into quarantine and then deletes them, emptying the store.
- `shutil.rmtree` and `Path.unlink` on a bind artifact are wrong for the same reason; go through
  `_retire_artifact`, which asks `paths.is_link` first.
- macOS and Linux CI cannot create a junction. `tests/test_windows_junctions.py` runs on the windows-latest
  job and patches `os.symlink` to fail, since the runner holds the symlink privilege.
