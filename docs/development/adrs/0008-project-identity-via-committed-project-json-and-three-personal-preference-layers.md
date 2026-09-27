# ADR-0008: Project identity via committed project.json and three personal preference layers

**Date:** 2026-09-27
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

> **Status of the memory claims below: PENDING, not delivered.** Milestone M1 implements the
> identity and the preference layers; `user-data/` is still in the project and still gitignored,
> so the v2 behaviour of losing it on a fresh clone is unchanged for now. The paragraphs about
> memory describe what the identity is *for* and what the relocation milestone will do with it.
> `docs/specs/v3-global-install.md` § Out of Scope is authoritative on what M1 shipped.

## Context

ADR-0007 moves per-project memory (`session-summary.md`, `state.json`, audit log) out of the
project and into `data/projects/<project_id>/`. That store needs a key, and the key determines
whether memory survives the three events that actually happen: the project directory being
moved or renamed, the repository being cloned again, and the developer switching machines.

Keying by absolute path fails all three. Deriving the key from the first commit SHA survives
clones but produces nothing in a repository with no commits, and gives two identities to a
fork of the same code.

Separately, v2 had a single `preferences.json` per project. v3 has a global layer plus a
per-project layer, and the question is which settings belong to the person and which belong to
the repository.

## Decision

**Identity.** Each project carries `.dev-team-agents/project.json`, **committed**:

```json
{
  "schema": 1,
  "project_id": "8f14e45f-ea0c-4c2b-9c1f-2b1f9a7d3e10",
  "context_paths": ["docs"]
}
```

The file is tiny, contains no secret, and is versioned. The identity therefore survives a
re-clone, a directory move and a machine change, and `data/projects/<project_id>/` is reachable
from any of them. `devteam doctor` reconciles `registry.json` when a bound path no longer
exists but the `project_id` is found elsewhere, and reports the same `project_id` appearing at
two paths (the fork case) instead of silently merging two projects' memory.

**Preferences: three layers, all personal.**

| Layer | Location | Example keys |
|-------|----------|--------------|
| Defaults | `core/versions/<v>/scripts/lib/preferences-defaults.json` | every key, canonical schema |
| Global user | `data/preferences.json` | `language`, `auto_update`, `telemetry` |
| Project | `data/projects/<id>/preferences.json` | `worktree_active`, `qa_browser` for this project |

Nothing about a **preference** is committed. The cascade is resolved **on write**, not on read:
`devteam sync` materialises the merged result at `<project>/.dev-team-agents/resolved/preferences.json`
(gitignored). Agents keep performing a single file read — no merge logic enters any of the 18
agent bodies, and `skills/shared/user-preferences/SKILL.md` changes a path, not a contract.

**`context_paths` is committed, and is not a preference.** It declares where the project's
knowledge lives (`docs/` by default, plus any additional read-only folders). Two developers
disagreeing about it is not a matter of taste — one of them is simply reading the wrong
universe, silently, with no error and no lint to catch it. The failure is concrete: a plan
produced against `docs/` + `rfcs/` respects a constraint recorded in an RFC, and the same
command on a colleague's machine produces a plan that violates it. Topology of the repository
belongs with the repository.

The `CONSENT_KEYS` rule from v2 carries over unchanged: `telemetry` and `auto_update` default
to `true` only in a file that does not exist yet, and are backfilled as `false` into a
pre-existing one, because that file's owner never saw a prompt for a key added later.

## Consequences

### Positive
- Memory will survive move, rename, re-clone and machine change — which it did not in v2, where
  `session-summary.md` was gitignored and lost on every fresh clone. The identity that makes this
  possible ships in M1; the relocation itself does not (see the status note above).
- Linked worktrees resolve to the same `project_id` as the main checkout, matching what
  `scripts/hooks/lib/session-summary-detect.sh` already does with `--git-common-dir`.
- Agents read one resolved file; the cascade cannot drift into 18 divergent implementations.
- Every developer on a project reads the same knowledge folders.

### Negative
- One framework file is committed into the product repository. It is 4 lines and carries no
  secret, but it is a departure from "nothing of the framework in git".
- A fork of a repository inherits the parent's `project_id` until `doctor` reassigns it.
- The resolved projection is a derived file: a stale `resolved/preferences.json` is possible if
  someone edits the source layers without running `sync`. `doctor` checks for it.

### Neutral
- `schema` is present from the first version so a future layout change has a migration hook.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Key memory by absolute project path | Moving or renaming the folder orphans all memory — the exact problem the store was meant to solve. |
| Derive identity from the first commit SHA | No identity in a repository without commits, and a fork or a fresh `git init` of the same code yields a different one. |
| Resolve the preference cascade at read time, inside each agent | Puts merge logic in 18 agent bodies, which is precisely the duplication the Canonical Rule Homes policy exists to prevent. |
| Make `context_paths` a personal preference | Produces silent divergence between developers running the same command on the same branch. No error, no lint, different results. |
| A fourth, committed "team preferences" layer | Rejected with D8: preferences stay personal. `context_paths` is topology, not preference, and rides with identity instead. |
