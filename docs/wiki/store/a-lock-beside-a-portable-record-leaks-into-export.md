# A lock beside a portable record leaks into an export

**Origin:** /devteam:learn consolidation, insights decisions locks | 2026-10-19
**Tags:** lock, export, machine-local, locks directory, lock.store_lock, portable record, store root, insights, dismiss, devteam export

> A lock file placed next to a portable record, under the store root and outside `locks/`, is not machine-local. An export carries it to another machine.

---

## What it is

The store separates portable records (shared, exported) from machine-local ones. A lock follows the same split. A lock is machine-local only when it sits under the machine's `locks/` directory.

## How it works

1. Call `lock.store_lock(name)`. It places the lock under the machine's `locks/` directory.
2. Never build a lock path by hand under the store root. That path is classified as portable.

## Gotchas

- A lock beside a portable record looks harmless on one machine. Export is where it leaks.
- `insights.py` `dismiss` takes its lock through `store_lock("insights-decisions")`. Copy that call, not a hand-built path.

## References

- `scripts/lib/devteam/insights.py` — `dismiss`
- `scripts/lib/devteam/lock.py` — `store_lock`
- `scripts/lib/devteam/paths.py` — `MACHINE_LOCAL_RECORDS`
