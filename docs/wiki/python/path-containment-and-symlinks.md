# Checking that a path stays inside a directory

**Origin:** three data-loss defects in the v3 bind, all one missing call | 2026-09-27
**Tags:** realpath, symlink, containment, relative_to, startswith, /private/var, path traversal

> Resolving the path you are checking follows it. For an artifact that is *supposed* to be a symlink out of the tree, resolve the **parent** and re-attach the leaf — and compare with `relative_to`, never `startswith`.

---

## What it is

"Is this path inside that directory?" has two wrong answers that both look right, and a project can
ship both at once: one that rejects its own legitimate artifacts, and one that accepts a sibling
directory whose name merely starts the same way.

## How it works

```python
def _resolved_location(path):
    """Where the path lives, with parents resolved but the leaf not followed."""
    return Path(os.path.realpath(str(path.parent))) / path.name

located = _resolved_location(candidate)
Path(os.path.realpath(str(root)))          # resolve BOTH sides
located.relative_to(resolved_root)         # raises ValueError when outside
```

Resolving the parent still catches the attack that matters — a symlinked `.claude` or
`.dev-team-agents` relocating the write out of the tree — while leaving a symlink artifact, whose
whole purpose is to point at the store, alone.

## Gotchas

- **`startswith` compares characters, not components.** `/store/core-backup/x` starts with
  `/store/core`, so a sibling directory reads as "inside". `relative_to` cannot make that mistake.
- **Resolve both sides.** On macOS `/var` is a symlink to `/private/var`, so comparing a resolved
  root against an unresolved candidate reports a path as foreign — which in this codebase made the
  containment check refuse the very artifacts the tool had just created. Temp directories live
  under `/var`, so tests hit it before users do.
- **Having the helper is not having the check.** `_is_inside` was correct and complete the whole
  time; three separate data-loss defects existed because no write path called it. A test per rule
  beats a correct helper nobody invokes.
- A containment check must run before `mkdir(parents=True)` too — that call traverses symlinks
  happily, so an ancestor is enough to relocate everything below it.

## References

- `scripts/lib/devteam/bind.py` — `require_inside`, `_resolved_location`, `_is_inside`, `_mkdir_within`
