# Commands still reading the v2 user-data path after bind

**Origin:** /devteam:version reported `vunknown` and default preferences in a bound project | 2026-09-29
**Tags:** v3, bind, state.json, preferences.json, data-dirs, bound project, user-data, version, health-check, update, git-common-dir

> A bound project has no `state.json` or `preferences.json` under `.dev-team-agents/user-data/`. A command that reads them there gets nothing and falls back to defaults — no error, just wrong output.

---

## What it is

v2 kept all per-project state in `.dev-team-agents/user-data/`. A bound project keeps it elsewhere:

| Record | Where a bound project keeps it | How to find it |
|--------|--------------------------------|----------------|
| `state.json` (incl. `installed_version`, stamped by `bind`) | machine-local store dir | `.dev-team-agents/state-dir` pointer |
| preferences | `.dev-team-agents/resolved/preferences.json` (the cascade's projection) | fixed path |

`grep … 2>/dev/null` on a missing file prints nothing, so `/devteam:version` showed `vunknown`, `Language: en`, and `No` for every switch.

## How it works

Resolve both through `scripts/hooks/lib/data-dirs.sh`, the helper `session-start.sh` uses, passing the **main checkout root**:

```bash
ROOT=""
GIT_COMMON_DIR="$(git rev-parse --git-common-dir 2>/dev/null)"
[ -n "$GIT_COMMON_DIR" ] && ROOT="$(cd "$GIT_COMMON_DIR/.." 2>/dev/null && pwd)"
[ -n "$ROOT" ] || ROOT="$PWD"

unset STATE_FILE USER_DATA_DIR   # devteam_state_dir treats these as caller overrides
for LIB in "$ROOT/.dev-team-agents/scripts/hooks/lib/data-dirs.sh" "$ROOT/scripts/hooks/lib/data-dirs.sh"; do
  [ -f "$LIB" ] && . "$LIB" && break
done
STATE_FILE="$(devteam_state_dir "$ROOT")/state.json"
PREFS_FILE="$(devteam_prefs_file "$ROOT")"
```

The helper falls back to `user-data/` itself when no pointer or projection exists, so the same code works on a never-bound (layout 1) project. The second `LIB` path covers this repository, which runs its own tree unbound.

`commands/health-check.md` and `setup-health-check/references/checks-list.md` (§ Before Category 1) use the same pattern. The checks-list section also prints `IN_STORE` — whether the state directory is outside the project — because "bound" alone does not say where the files are: a bound project keeps them in `user-data/` until `devteam upgrade` runs.

`skills/shared/work-feedback/SKILL.md` reads its gate keys from the same state directory, then from the credential reference files (`devteam cred import` moves them there), with the Read tool — the credential guard hook blocks a shell read of the local credentials file.

Still reading `user-data/` directly as of 2026-09-30:
- the v2 section of `commands/update.md` — unreachable in a bound project, because its Step 0 hands off to `devteam update` when `project.json` exists
- the category bodies of `setup-health-check/references/checks-list.md` — deliberately, since a v2 project runs them as written; a bound project applies § Before Category 1's routing table, which overrides them

## Gotchas

- **Machine-local is not the same as shared across checkouts.** The state *directory* belongs to the main checkout, but a value that describes one checkout must not live there. `graphify-refresh.sh` was moved to the main checkout's `state.json` and started letting a linked worktree's build stand in for the main checkout's graph; its marker now lives in `graphify-out/.build-commit`, next to the graph. Ask what the value describes before choosing the directory.

- **`--git-common-dir` outside a git repository.** Written inline as `cd "$(git rev-parse --git-common-dir)/.."`, the empty output makes it `cd "/.."`, which **succeeds** — `ROOT` becomes `/`, and a `[ -n "$ROOT" ] || ROOT="$PWD"` fallback never fires. Capture the output first and `cd` only when it is non-empty.
- **Use `--git-common-dir`, not `--show-toplevel`.** From a linked worktree, `--show-toplevel` gives the worktree's root; the pointer files live only in the main checkout, which `data-dirs.sh` requires as its argument.
- **`unset STATE_FILE USER_DATA_DIR` before calling.** `devteam_state_dir` returns an inherited `$STATE_FILE`'s directory or `$USER_DATA_DIR` ahead of the pointer.

## References

- `scripts/hooks/lib/data-dirs.sh` — the resolver
- `commands/version.md` — the fixed command (commit 7d88b41)
- ADR-0013 — the portable / machine-local split of the data store
