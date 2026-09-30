# Machine-local records match by basename at any depth

**Origin:** task-board implementation chose `task-board/` over `tasks/` to avoid routing a user's `wiki/tasks/` to the machine subtree | 2026-09-30
**Tags:** machine-local, basename, MACHINE_LOCAL_RECORDS, paths.is_machine_local_record, task-board, portable, export, gitignore

> A machine-local record is matched by basename at any depth, so a generic name like `tasks` routes *any* directory with that name to machine-local storage.

---

## What it is

The store splits records into portable and machine-local (ADR-0013). The classifier `paths.is_machine_local_record(name)` checks whether a path belongs in the machine subtree by matching the **basename** against the tuple `MACHINE_LOCAL_RECORDS` in `scripts/lib/devteam/paths.py`. The match is by name alone, not by depth or path context.

## How it works

```python
# Single source of truth: scripts/lib/devteam/paths.py
MACHINE_LOCAL_RECORDS = (
    "state.json",
    "bind-manifest.json",
    "telemetry-queue.json",
    "credentials.local.json",  # values, not references
    "audit.log",
    "notifications.jsonl", "notifications-seen.json",
    "task-board",  # directory
    # plus all dot-prefixed names (.*) — cache, ETag, marker files
)

def is_machine_local_record(name: str) -> bool:
    # Strips leading path components, matches basename only
    return basename.lower() in MACHINE_LOCAL_RECORDS or basename.startswith(".")
```

Example matching:
- `audit.log` → machine-local
- `data/machines/…/audit.log` → machine-local (basename match)
- `task-board/` → machine-local
- `projects/board/task-board/` → machine-local (basename match) — **a user's directory named this would be routed away**
- `wiki/tasks/` → portable (basename `tasks` is not in the tuple; it would be if it were called `task-board`)

## Gotchas

- **Generic names route away from portable storage.** The task-board directory is named `task-board`, not `tasks`, specifically to avoid routing user content. When adding a new machine-local record, pick a distinctive name unlikely to collide with project directories.
- **The match ignores depth.** A file under many subdirectories is still machine-local if its basename matches. This is intentional — `scripts/lib/devteam/paths.py` is the single source of truth, and it is called on every write to decide which store side gets the record.
- **Dot-prefixed names are always machine-local.** The rule `startswith(".")` means `.gitignore`, `.my-cache`, `.session-lock` are all machine-local without explicit entry. This keeps transient and implementation details out of exports.

## References

- ADR-0013: Store layout and portable vs. machine-local records
- Single source of truth: `scripts/lib/devteam/paths.py::MACHINE_LOCAL_RECORDS`
- Documentation mirrors: `CLAUDE-md/user-data.md` § Under v3 layout 2; `CLAUDE-md/cli.md` § Store layout
