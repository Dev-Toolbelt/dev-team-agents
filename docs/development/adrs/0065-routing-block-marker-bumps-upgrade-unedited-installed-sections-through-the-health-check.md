# ADR-0065: Routing block marker bumps upgrade unedited installed sections through the health check

**Date:** 2026-11-10  
**Status:** Accepted  
**Deciders:** maintainer, software-architect review  
**Applies to:** `skills/shared/auto-routing/SKILL.md`, `skills/shared/setup-health-check/references/legacy-routing-*.md`

## Context

Setup copies the `## dev-team-agents` block from `skills/shared/auto-routing/SKILL.md` into a project's `CLAUDE.md` and `AGENTS.md`. Every provider loads that block on every turn, and it is the only harness text the main conversation always reads. After setup the copy belongs to the project, so a later change to the template does not reach it on its own.

Until now the template changed without a marker bump (the `mobile-developer`, `seo-specialist` and `security-specialist` row changes under `devteam:routing v3`), and nothing rewrote a v3 section. ADR-0047 recorded that projects bound earlier get such a change only through a merge by hand.

The Delivery Confirmation Heading (`skills/shared/output-format/SKILL.md`) is a rule for the main conversation's own replies, so it has to be in that block. A pointer that only new projects receive would leave every existing install without it.

## Decision

A template change that installed projects must receive bumps the marker (`devteam:routing v3` → `v4`). Each bump ships:

1. `legacy-routing-vN.md` beside `fix-patterns.md`, holding every line the block carried under the old marker, including wording that changed without a bump.
2. A `STALE: routing vN in <file>` check in `checks-list.md`, run against both `CLAUDE.md` and `AGENTS.md`.
3. An auto-fix in `fix-patterns.md`. It rewrites a section only when it is unedited, meaning every line outside the config `KEY: value` lines and blank lines appears verbatim in the legacy file. The old section goes to quarantine first and config values carry over. An edited section gets a WARN and the current block to merge by hand.

A wording change that installed projects can do without stays unbumped, as before.

The block's 50-line budget, fences included, still holds, and the block now has no spare lines. It carries routing plus the few conventions every reply follows (the English-documents line and the delivery heading). Anything else stays in a skill.

## Consequences

### Positive
- Existing installs on all three providers receive a block change through the next health check, with no hand merge when the user never edited the section.
- A v3 upgrade also brings in the `security-specialist` audit row that ADR-0047 left to a hand merge.

### Negative
- Each bump adds a legacy file, a check line and a fix section. If bumps become frequent, generalize to one check ("marker lower than the template's") and one fix section that picks the legacy file by the section's marker.
- The unedited test checks that each line is in the legacy file, not that each legacy line is still in the section. A section whose rows the user deleted counts as unedited and gets those rows back. Quarantine keeps the original.

### Neutral
- Projects with an edited section keep v3 until the user merges by hand. A per-delivery hint on the ADR-0048 channel could cover them later if that gap turns out to matter.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Per-prompt hook line, like `04-language.sh` | Runs before the reply, so it cannot know whether the reply reports a delivery. It would spend tokens on every prompt for a rule that applies to a few replies |
| Session-start banner line | Said once per session and lost in long sessions, which is the drift the per-prompt language line was added to fix |
| Change the template without a bump, as ADR-0047 did | Only newly set-up projects would receive the rule |
