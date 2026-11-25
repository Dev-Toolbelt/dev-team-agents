# ADR-0068: A committed link into any machine's core store is a bind artifact

**Date:** 2026-11-25  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Amends:** [ADR-0022](0022-delegated-provider-installers-own-files-not-directories.md), Decision 2 (the ownership rule)  
**Applies to:** `scripts/lib/devteam/bind.py`

## Context

A v3 bind in link mode writes absolute links into this machine's core store
(`…/dev-team-agents/core/versions/<v>/agents`, one per skill, `.dev-team-agents/scripts`, the opencode
and Codex skills link). They go into `.git/info/exclude`, which has no effect on a tracked path. A project
that committed them, by a `git add -A` or because a v2 install had tracked links a bind rewrote, hands
every clone a link into a store that only the committing machine has. On Windows without symlink
support, git writes each one as a plain file holding the Mac path.

Ownership (ADR-0022, Decision 2) was proven by the manifest, by the installer's ledger, or by a link
resolving into this machine's core or the project's own install directory. A link that resolves nowhere
matched none of these. `bind`, `start` and `migrate` refused it as "not created by dev-team-agents", with
no `reason`, so the desktop app offered no repair and a first-run project could not be set up.

## Decision

1. **The target's shape is a fourth proof of ownership.** A symlink, or a link stub that a checkout wrote
   as a file (`providers.read_link_stub`, inside the project), is framework-owned when its target is an
   absolute path of the form `…/core/versions/<x.y.z…>/<tree>`, where `<tree>` is `agents`, `commands`,
   `scripts`, `templates`, `plugins`, `skills`, or up to two levels below `skills`. A target with a `.` or
   `..` component never qualifies.
2. **Retiring follows the existing rule.** A symlink is unlinked and recreated; a stub file is moved to
   quarantine, never deleted. At an opencode or Codex target, `bind` retires it before the installer runs,
   because the installer would `rm -rf` an owned path.
3. **Owned symlinks are unlinked before a delegated installer runs.** The installers rewrite their files
   with `cp -f`, which writes through a symlink at the destination. Without this, Decision 1 would let a
   committed link shaped like a core path make an installer write outside the project.
4. **`bind` reports the tracked state.** Its result carries `tracked_artifacts` (additive under ADR-0014)
   and it warns with the `git rm -r --cached` command `doctor` already prints. Untracking is the user's
   one-time fix; `bind` never edits the index.

## Consequences

### Positive
- A project committed with bind links from one machine binds on any other, Windows included, without
  manual cleanup, and the user learns from `bind` itself which paths to untrack.
- The same rule holds for Claude, opencode and Codex, with tests iterating `ALL_PROVIDERS`.

### Negative
- Ownership is proven by text that does not resolve on this machine. A project file whose whole content
  is one line naming such a path would be moved to quarantine. Quarantine keeps it, and the shape is narrow
  enough that a real project file matching it is unlikely.

### Neutral
- The committed links stay a repository problem until someone untracks them; this decision makes them
  harmless to `bind`, not absent from git.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Accept only links into this machine's store | That is the old rule, and it is what stranded the Windows first run |
| Refuse with `reason: v2-install` and route to `migrate` | These are v3 artifacts, not a v2 install, and `migrate` would refuse them for the same reason |
| Have `bind` untrack the paths itself | Editing the index is a repository change the user did not ask for, and it would show up in their next commit |
| Make bind links relative so they survive a commit | The core store lives outside the project, so no relative path is portable across machines either |
