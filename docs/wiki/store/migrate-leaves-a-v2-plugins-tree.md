# A v2 plugins tree must be migrated, not just refused

**Origin:** `devteam migrate --apply` exited 4 on every v2 project with a real `.dev-team-agents/plugins` directory | 2026-10-31
**Tags:** v2, plugins, migrate, vendored, bind, exit 4, VENDORED_TREES, RUNTIME_TREES

> `bind` refuses a real `.dev-team-agents/plugins` directory in a v2 install and says to run `devteam migrate`, so every tree `bind` refuses must be a tree `migrate` moves.

---

## What it is

A v2 install vendored `plugins/` into `.dev-team-agents/plugins`, next to the other framework trees. In v3 that path is a link into the core store, so `bind` cannot replace a real directory with it.

Two lists in `scripts/lib/devteam/` hold different facts and must not be merged:

| Constant | Module | Meaning |
|----------|--------|---------|
| `VENDORED_TREES` | `migrate.py` | Trees a v2 install copied into the project |
| `RUNTIME_TREES` | `bind.py` | Trees v3 links into the project from the core store |

## Symptom

- `devteam migrate --apply` exits 4 and reports that a v2 install needs migrating, even though `migrate` is the command being run.
- `devteam bind` reports `.dev-team-agents/plugins` as "is a v2 vendored tree".

## Cause

`RUNTIME_TREES` includes `plugins`, but `VENDORED_TREES` did not. `bind` refused the directory and told the user to migrate, and `migrate` did not recognise it as a vendored tree to move. The refusal and the fix path disagreed.

## Fix

`plugins` is in `migrate.VENDORED_TREES` (commit `cc5460c`). Migration quarantines the v2 directory and lets `bind` link the core tree.

## Gotchas

- Plugin settings do not live in `plugins/`. They stay in `.dev-team-agents/plugin-settings/`, which is not a vendored tree and is never moved by migration. See `store/plugin-settings-location.md`.
- Do not add a tree to `RUNTIME_TREES` without adding it to `VENDORED_TREES`. The opposite direction is not required, because a vendored-only tree is one `bind` never links.

## References

- `scripts/lib/devteam/migrate.py` — `VENDORED_TREES`
- `scripts/lib/devteam/bind.py` — `RUNTIME_TREES`
- `tests/test_migrate_doctor.py` — `DualLayoutMigrationTest`, which asserts `set(bind.RUNTIME_TREES) <= set(migrate.VENDORED_TREES)`
- `store/bind-over-a-v2-install.md`, `store/pre-root-v2-install.md`
