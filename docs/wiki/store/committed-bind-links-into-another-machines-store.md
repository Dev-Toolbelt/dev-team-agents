# Committed bind links point into another machine's store

**Origin:** `devteam start` from the desktop app on Windows, exit 4 on `.claude/agents/dev-team` in a project bound and committed on a Mac | 2026-11-25
**Tags:** bind, start, symlink, stub, core store, tracked, Windows, core.symlinks=false, foreign, cross-machine

> A v3 bind link is absolute and machine-specific. Once committed, every other machine gets a link into a store it does not have, and on Windows a plain file holding a Mac path.

---

## What it is

`bind` in link mode writes `.claude/agents/dev-team`, `.claude/commands/devteam`, one link per framework
skill and the runtime links `.dev-team-agents/{scripts,templates,plugins}` as **absolute** symlinks into
this machine's core store (`…/dev-team-agents/core/versions/<v>/<tree>`). They are listed in
`.git/info/exclude`, but that has no effect on a path already tracked: a project that committed them
(an earlier `git add -A`, or a v2 install whose tracked links a bind rewrote) carries one machine's paths.

A Windows checkout without symlink support writes each such link as a regular file holding the target
text, for example `/Users/<name>/Library/Application Support/dev-team-agents/core/versions/2.49.1/agents`
(git mode `120000` in the index, an 89-byte file on disk).

## How it works

- `_is_managed_path` used to vouch only for symlinks into *this* machine's core or the project's own
  `.dev-team-agents/`. The foreign link, or its stub, fell through to "already exists and was not created
  by dev-team-agents", with no `reason`, so the app offered no repair and `migrate` did not list it.
- `bind._is_core_link_text` now recognises an absolute target shaped `…/core/versions/<x.y.z…>/<tree>`
  (tree is `agents`, `commands`, `scripts`, `templates`, `plugins`, `skills` for the opencode and Codex
  skills link, or `skills/<category>/<name>`) on any machine, with `/` or `\` separators. A symlink with
  that target is unlinked and recreated. A stub file (`providers.read_link_stub`, all three formats,
  inside the project only) is quarantined, never deleted. At an opencode or Codex skills link `bind`
  quarantines it before the provider's installer runs, because the installer would `rm -rf` an owned path.
- Before the opencode and Codex installers run, `bind` unlinks every symlink at a path they own. They
  rewrite those paths with `cp -f`, which writes through a symlink at the destination: a committed link
  shaped like a core path at `.codex/agents/<name>.toml` would otherwise have the installer write
  outside the project.
- `bind` and `doctor` report tracked bind artifacts with the exact `git rm -r --cached` command
  (`tracked_artifacts` in `bind --json`). The tracked links stay a repository problem until someone
  untracks them once. The ownership rule itself is ADR-0068.

## Gotchas

- The link text alone identifies a bind artifact, because the target never exists on the machine that
  reads it. A relative target is never accepted, since a bind only writes absolute links. A project file at the same path whose text merely mentions `core/versions/…` stays foreign, because the
  stub must be a single line naming exactly one linked tree.
- After the bind replaces the stub, git shows the tracked path as modified (a type change on Windows,
  where auto mode falls back to copies). Untracking is the fix, not committing the new link.
