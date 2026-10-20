# A pre-v2.1.0 install hides one directory deeper, and a refused bind used to wall it in

**Origin:** binding `gulosao-site` from the desktop app failed on `.claude/agents/dev-team` | 2026-09-30
**Tags:** v2, pre-root, .claude/dev-team-agents, migrate, migrate-to-root, bind, project.json, layout 1, dual layout, secondary

> Before v2.1.0 the framework lived at `.claude/dev-team-agents/`, memory at `.claude/user-data/`, docs at `.claude/docs/`. Every check that looks only at `.dev-team-agents/` misses it.

---

## What it is

The v2 refusal in `bind` (`migrate.leftover_trees`) looked at the project root only, so this shape
passed it, and the bind collided on the relative link the old installer committed
(`.claude/agents/dev-team -> ../dev-team-agents/agents`) — after writing `project.json`, and after the
symlink probe had created `.dev-team-agents/`. `migrate-to-root.sh` refuses to move onto an existing
`.dev-team-agents/`, so the failed bind blocked the one tool for the shape.

## How it works now

- `migrate.pre_root_install()` is the single detector for `bind`, `migrate` and `doctor`.
- `bind` checks every collision before its first write, and the probe removes the directory it made.
- `migrate` converts the shape itself: tree to quarantine, `.claude/user-data/` moved to
  `.dev-team-agents/user-data/` (layout 1), `.claude/docs/` added to `context_paths`, the old hook
  entries (`hooks.PRE_ROOT_HOOK_DIR`) rewritten in place, leftover links into the quarantined tree
  unlinked.
- A project can hold both shapes: an update vendors the root tree at `.dev-team-agents/` and leaves
  `.claude/dev-team-agents/` in place. `detect()` reports the root tree as `secondary`, and
  `vendored_paths()` feeds the bind's `vacated` set, the moves and `git_tracked`. Without it the bind
  preflight refuses the root tree before anything moves, so every `migrate` retry failed with the same
  exit 4 and a hint to run `migrate`.
- `doctor` reads `leftover_installs()`, which names each install with its own directory. A pre-root
  install is checked before the generic v2 message, which would place its trees under `.dev-team-agents/`.
- An unregistered `project.json` is adopted; if it says layout 2 and memory moves in, it is set to 1 —
  otherwise the moved memory is invisible and `upgrade` never offers to take it.

## Gotchas

- `.claude/user-data/` may be committed: it goes into `git_tracked`, so `--untrack` takes it out of
  the index with the framework tree.
- Two memory directories (`.claude/user-data/` and `.claude/dev-team-agents/user-data/`) are refused
  in the plan: merging them is a judgement `migrate` does not make.
- A committed `.dev-team-agents` or `.claude/dev-team-agents` symlink to a directory outside the project
  must be refused by `require_inside` before any move, memory write or `project.json` write, not only before
  the vendored moves.
- Test fixtures need a real commit: `git_tracked` and the committed links are read from git, not disk.
