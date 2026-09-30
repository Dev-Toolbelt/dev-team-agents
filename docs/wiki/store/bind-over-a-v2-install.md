# Binding over a v2 install leaves it behind, tracked, and invisible

**Origin:** a real project bound from the desktop app reported `status: ok` with the v2 tree still in git | 2026-09-29
**Tags:** v2, vendored, bind, migrate, doctor, git, tracked, info/exclude, symlink, leftover

> `.git/info/exclude` only ignores untracked files. Anything a v2 install committed stays tracked after a bind replaces it — including links the bind rewrote to point into one machine's store.

---

## What it is

A v2 `install.sh` vendored the framework into `.dev-team-agents/{agents,commands,skills,scripts,templates}`
and committed relative links to it under `.claude/`. Running `devteam bind` over that (instead of
`devteam migrate`) replaced the links — `_is_managed_path` counts a link into the project's own
`.dev-team-agents/` as a bind artifact — but did nothing about the vendored tree.

## How it works

- The new links point at `~/Library/Application Support/dev-team-agents/core/versions/<v>/…`. They are
  listed in `.git/info/exclude`, which has **no effect on a tracked path**, so `git status` shows ~150 of
  them modified and the next `git add -A` commits links into a directory no teammate has.
- `doctor` only checked for a v2 shape when `project.json` was absent. After the bind it existed, so the
  report was `status: ok`.
- Nothing reads the vendored tree any more (hooks pointed at `.dev-team-agents/core/…`), so it is dead
  weight that still ships with every clone. Since the runtime root became two links at
  `.dev-team-agents/scripts` and `/templates`, the vendored `scripts/` sits exactly where a link must
  go: `bind` and `sync` refuse such a project with exit 4 until `devteam migrate` has run.

Since 2026-09-29 the `bind` command refuses a v2 install (exit 4, pointing at `migrate`), and `doctor` and
`migrate` report both the leftover tree and the tracked artifacts with the exact untrack command.

## Gotchas

- The untrack list must name each artifact, not a parent directory: `git rm -r --cached .claude/skills`
  would also untrack the project's own skills sitting beside the framework's.
- `.claude/settings.json` is in the manifest (kind `settings`), but it is the project's file — never tell
  a user to untrack it. Until 2026-09-29 it was also written into the exclude block, which on a project
  that had not committed it yet made `git add -A` skip the file carrying the hooks; the exclude block and
  the "must not be tracked" check now share one allowlist, `bind.MACHINE_LOCAL_KINDS`.
- A project already in this state still syncs: the refusal is in the command, not in `bind()`.
