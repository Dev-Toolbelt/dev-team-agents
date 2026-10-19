# ADR-0039: ADRs declare the paths they govern and a Stop hook names them when those paths change

**Date:** 2026-10-19  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/hooks/stop/03h-adr-scope-check.sh`, `templates/adr-template.md`, `skills/shared/adr/SKILL.md`  
**Relates to:** [ADR-0038](0038-retrieval-indexes-for-the-wiki-and-adrs-are-checked-mechanically.md) (ADR index), [ADR-0036](0036-path-scoped-and-severity-graded-rules-in-the-reuse-registry-enforced-at-stop-by-exit-2.md) (path-scoped rules, exit 2 at Stop)

## Context

The harness has a mechanical check for one ADR gap: `03e-adr-gap-check.sh` warns when a session touched a dependency manifest, a migration or a provider config and added no ADR. Nothing covered the opposite gap — code changing under a decision that already exists. The ADR index (ADR-0038) makes an ADR findable when an agent looks for it, but an agent editing `scripts/install-codex.sh` has no reason to search for "provider ownership" and so never reads ADR-0022, which governs exactly that file. ADR-0022 itself was written after a delegated installer skipped a guarantee nobody had re-read.

The pattern comes from CompozyOS's standing directives, where each directive names the files whose change "triggers re-evaluation".

## Decision

1. An ADR may carry an optional header line, `**Applies to:**`, listing the paths it governs as backticked globs. `*` also crosses `/`. The line is part of `templates/adr-template.md` as an optional placeholder with no code span, so an unedited placeholder matches nothing.
2. `scripts/hooks/stop/03h-adr-scope-check.sh` reads the line from every `Accepted` ADR in the directory `new-adr.sh --dir` resolves. When a touched path matches and the ADR file itself was not touched, it exits 2 with the ADR and the matching paths, once per distinct set of matches (`lib/warn-once.sh`, marker `.adr-scope-warned`).
3. It is a reminder, not a gate: the agent re-reads the ADR and amends or supersedes it if the change departs from it. Nothing blocks the session past that one continuation.
4. The field lives in each ADR's header, not as a fifth column of the ADR index.

## Consequences

### Positive
- A change under an existing decision surfaces that decision at the moment it matters, without the agent having to know it exists.
- Patterns are globs (`*`, `?`) converted to anchored regular expressions and matched by `grep -E` — never evaluated, expanded against the disk, or handed to bash's glob matcher, which backtracks exponentially on patterns like `*a*a*a*a*b` (bash 3.2) or nested `+(…)` groups (bash 4.1+). A cloned repository's ADR text can neither run anything nor stall a Stop. Filenames that are not printable ASCII are skipped, so nothing printed to the agent can carry control or bidi characters.

### Negative
- Coverage depends on authors filling the line; an ADR without it is invisible to the check. Six ADRs in this repository were backfilled; the rest stay unscoped until someone touches them.
- A broad pattern (`scripts/*`) will fire on most sessions. The warn-once signature limits that to one continuation per distinct set.

### Neutral
- opencode only logs a Stop hook's stderr, the same accepted gap as `03e` (see that script's header).
- Superseded, Deprecated and Proposed ADRs are ignored; only a decision in force constrains code.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| A fifth `Applies to` column in the ADR index | Breaks `index-lint` and every index already generated in bound projects; the index is a retrieval aid, not a policy file |
| Blocking until the ADR is touched | A change that follows the ADR is the normal case; forcing an edit to clear the check would produce noise edits |
| Inferring governed paths from paths mentioned in the ADR body | ADR bodies cite files as examples and history; the hit rate would make the warning ignorable |
