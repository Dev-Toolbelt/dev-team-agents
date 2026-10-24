---
name: adr
description: Architecture Decision Records — MADR format, index, and the paths each decision governs.
---

# Architecture Decision Records (ADR)

ADRs document significant architectural decisions — the context, what was decided, why, and what was considered and rejected.

## File Location

```
docs/development/adrs/
  README.md                      ← retrieval index (see § ADR Index)
  0001-database-choice.md
  0002-api-design-approach.md
  0003-authentication-strategy.md
```

**The ADR directory is whatever `bash .dev-team-agents/scripts/new-adr.sh --dir` prints**, under the project's docs write root — the first `context_paths` entry, `docs` by default (`skills/shared/project-context/SKILL.md` § Context Loading Order). The default follows the project's doc layout (the `adr` key in `scripts/lib/doc-layouts.json`, `skills/shared/doc-flow/SKILL.md` § Doc Layout): in the **gated** layout it is `<root>/adr/` with files named `ADR-NNNN-slug.md`; in the **development** layout (the default) it is `<root>/development/adrs/` when it exists, otherwise an existing `<root>/adr/`, otherwise `<root>/development/adrs/` (created with the first ADR). A directory whose ADRs are named `ADR-NNNN-slug.md` keeps that scheme. Every mention of `docs/development/adrs/` in any skill, agent or command means that resolved directory. A symlinked ADR directory is refused, never followed.

## MADR Format

```markdown
# [Short title of the decision]

**Status**: [Proposed | Accepted | Deprecated | Superseded by ADR-XXX]
**Date**: YYYY-MM-DD
**Deciders**: [names or roles involved]
**Applies to**: [optional — path globs in backticks, see § Applies To]

## Context

[Describe the issue motivating this decision, including forces at play: technical, political, social, project constraints. Be factual — no judgment yet.]

## Decision

[State the decision in active voice: "We will use X because..."]

## Rationale

[Explain why this option was chosen over the alternatives. Link to evidence, benchmarks, or constraints that drove the decision.]

## Alternatives Considered

### Option A — [Name]
- **Pros**: ...
- **Cons**: ...
- **Why rejected**: ...

### Option B — [Name]
- **Pros**: ...
- **Cons**: ...
- **Why rejected**: ...

## Consequences

**Positive**: [What becomes easier or possible]
**Negative**: [What becomes harder, what debt is accepted]
**Risks**: [What could go wrong, and how to mitigate]
```

## Check Before Creating

**Before creating anything**, list the existing ADR titles and check whether the decision is already covered:

```bash
bash .dev-team-agents/scripts/new-adr.sh --list
```

`--list` prints the titles and creates nothing. Use it rather than a glob of your own: ADR filenames exist under two schemes (the historical `adr-NNN-slug.md` and the current `NNNN-slug.md`), the script is the single place that knows both, and a hand-written glob that matched only the historical one is exactly why this check silently returned an empty list for every ADR that existed.

- **Same decision, not yet decided** (still `Proposed`, or genuinely still open) → edit that file, do not create a new one.
- **Same decision, already `Accepted`, and this is a reversal** → create a new ADR, then set the old one's status to `Superseded by ADR-XXX` and link forward.
- **Related but distinct decision** (e.g. this one narrows or extends an existing ADR without reversing it) → create a new ADR and cross-reference the related one in `## Context`.
- **Genuinely new topic** → create a new ADR.

This check applies regardless of which command or agent triggers ADR creation (`/devteam:adr`, `/devteam:learn`, `software-architect` acting on the CLAUDE.md trigger) — each is a separate entry point into the same registry, and none of them can see what another already wrote without this step.

## Creating an ADR

Use the script to auto-number and scaffold the file — it also prints existing ADR titles as a mechanical reminder of the check above:

```bash
bash .dev-team-agents/scripts/new-adr.sh "title of the decision"
```

This creates `<adr-dir>/NNNN-title-slug.md` — four digits, no prefix, or `ADR-NNNN-title-slug.md` in the gated layout or in a directory that already uses that scheme — with the MADR template pre-filled, and appends its row to the ADR index. Fill in the generated file and its index row, and change the status from `Proposed` to `Accepted` in both.

## ADR Index

`README.md` inside the ADR directory is the ADRs' retrieval index — the same idea as the wiki index (`skills/shared/docs-sync/references/wiki-format.md`): an agent greps it for the task's keywords instead of listing and opening ADRs.

```markdown
# Architecture Decision Records

## Index

| ADR | Status | Keywords | Read it when |
|-----|--------|----------|--------------|
| `0001-database-choice.md` | Accepted | postgres, database engine, jsonb, banco de dados | Choosing or replacing the primary datastore |
| `0002-api-design-approach.md` | Superseded by ADR-0007 | rest, graphql, api style, versioning | Adding an endpoint style the API does not use yet |
```

| Column | Content |
|--------|---------|
| **ADR** | Filename, in backticks |
| **Status** | The ADR's current status — update it in the same edit that supersedes or deprecates the ADR |
| **Keywords** | 4–10 comma-separated lowercase search terms, with synonyms — the wiki `Tags` rules apply |
| **Read it when** | One clause naming the situation in which the decision constrains the work — not the title |

- `new-adr.sh` appends the row with `Proposed` and two placeholders; filling them is part of writing the ADR. A placeholder left behind is an ADR nothing will find.
- The index is created on demand: the first `new-adr.sh` run that finds it missing writes the header and a placeholder row (`[status]`, `[keywords]`, `[read it when]`) for every existing ADR, so the series stays reachable while the cells are filled. An existing index is never regenerated; a `README.md` with no `## Index` table is left untouched and the row is printed for a manual add.
- `scripts/index-lint.sh` (run by the `Stop` hook when a session touches the ADR directory) reports an ADR with no row, a row pointing at a missing file, unfilled placeholders, and Keywords below four terms.

## Applies To

An optional header line naming the paths a decision governs, so a later change to them is not made blind to it:

```markdown
**Applies to:** `scripts/lib/devteam/bind.py`, `scripts/install-*.sh`
```

- Patterns are globs matched against repo-relative paths: `*` matches any run of characters, including `/`, and `?` one character; every other character is literal (no `[ab]` classes). Only the backticked code spans on the line count.
- Add it when the decision constrains specific code — a module, an installer, a schema. Leave it out for decisions about process or tooling choices with no fixed location.
- `scripts/hooks/stop/03h-adr-scope-check.sh` reads it: when a session touches a matching path of an `Accepted` ADR and not the ADR itself, the agent is told once to re-read the ADR, then amend or supersede it if the change departs from it. Superseded and Proposed ADRs are ignored.

## When to Write an ADR

Write an ADR when the decision:
- Is hard to reverse (database engine, auth strategy, monolith vs microservices)
- Affects multiple components or teams
- Has non-obvious reasoning that future developers will question
- Involves a significant tradeoff

Skip ADRs for: library versions, code style rules, trivial configuration.

## Status Lifecycle

`Proposed` → `Accepted` → (if superseded) `Deprecated` / `Superseded by ADR-XXX`

When superseding an ADR, update the old one's status and link to the new one.

## Tips

- Keep it short — 1-2 pages max
- Write it at decision time, not after implementation
- "We will" not "We should" — ADRs record decisions, not recommendations
- The ADR index is what makes an ADR discoverable; link the load-bearing ones from `CLAUDE.md` or `development/architecture.md` as well
