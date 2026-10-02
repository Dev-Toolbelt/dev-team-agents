# A v2 install's `.claude/` links can arrive as real copies, and a late refusal stranded the migration

**Origin:** binding `the-valle-route-tours-site` from the desktop app failed on `.claude/agents/dev-team` after an earlier migrate | 2026-10-01
**Tags:** v2, migrate, bind, symlink, copy, materialized, dereference, windows, link file, quarantine, interrupted migration, preflight, project.json

> v2 committed `.claude/agents/dev-team`, `.claude/commands/devteam` and one link per skill as relative symlinks into `.dev-team-agents/`. Nothing guarantees they are still symlinks when a project reaches `migrate`.

---

## What it is

A scaffolding tool that copied a template project with links dereferenced committed those paths as
real directories (265 regular files in the case found); a Windows checkout without symlink support
writes each link as a text file holding its target. `_is_managed_path` only vouches for symlinks, so
the bind saw "foreign" content.

`migrate.apply` used to quarantine `.dev-team-agents/{agents,…}` and write `project.json` **before**
the bind ran its preflight. The refusal then left a project where `migrate` found no vendored tree
("no v2 install") and `bind` kept refusing the copies: no command could move it forward.

## How it works now

- `bind.v2_copy(rel, dest, version_dir)` is the single detector. Content decides, not the path: the
  agents/commands folder must hold only `.md` files with at least one framework name; a skill's
  `SKILL.md` frontmatter `name` must match; a plain file must hold a path through `.dev-team-agents`.
  A project's own directory at the same path stays foreign.
- `bind` refuses a copy with `details.reason: "v2-install"`, the reason the app turns into Migrate.
- `migrate` accepts a project with copies even when the tree is gone (an interrupted migration),
  adopts the unregistered `project.json`, and quarantines the copies under `v2-install/claude/<folder>`.
- `migrate.apply` calls `bind.check(..., vacated=…)` before its first move: every provider's preflight,
  with the paths about to be quarantined treated as absent. A refusal changes nothing.

## Gotchas

- The copies are usually stale relative to the vendored tree (they were frozen when copied), so
  comparing their content with the tree is not a usable detector.
- They are commonly tracked by git: they go into `git_tracked`, and `--untrack` takes them out.
