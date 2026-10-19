# ADR-0036: Path-scoped and severity-graded rules in the reuse registry, enforced at Stop by exit 2

**Date:** 2026-10-17  
**Status:** Accepted  
**Deciders:** Maintainers  
**Applies to:** `scripts/reuse-lint.sh`, `scripts/hooks/stop/03c-reuse-lint.sh`, `skills/shared/reuse-guidelines/SKILL.md`  

## Context

A bound project's rules live in its instruction files, ADRs, specs and `docs/development/`. Only one of those is machine-checked: `docs/development/reuse-guidelines.md`, through `scripts/reuse-lint.sh` and the Stop hook `03c-reuse-lint.sh`. An audit found that this gate did not work in the cases that matter:

- Without `origin/HEAD`, which is common in a repository wired with `git remote add`, the lint aborted with exit 128 under `set -o pipefail`.
- It checked only `<base>...HEAD`. Staged, unstaged and untracked changes were invisible, and that is the state the tree is in when Stop runs.
- A regex alternation written `\|` in a table cell was split across columns. The skill's own example regex failed this way.
- An invalid regex was treated as "no match".
- The hook ran the lint `--quiet` and passed its exit 1 through. No provider shows a Stop exit 1 to the agent, so violations reached nobody.

There was also no way to limit a rule to part of the codebase, and no way to register a rule as a recommendation rather than a hard stop.

## Decision

1. **The registry gains three optional columns, appended at the end of the row:**
   - `scope`: comma-separated globs where `*` crosses directories;
   - `severity`: `blocking` (the default) or `advisory`;
   - `added`: `YYYY-MM-DD`.

   It also gains a fourth type, `review-rule`, for non-visual conventions that only a reviewer can judge. Rows are parsed positionally, so a five-column registry stays valid as written.
2. **Scoped rules are agent behavior plus the shell lint, not a provider-native rules directory** (Claude Code's `.claude/rules/`). They therefore work identically on every provider in `ALL_PROVIDERS`. Reviewers and coding agents load only the rows whose `scope` matches the files involved.
3. **The lint checks everything the branch adds:** commits against the base branch (with a fallback when `origin/HEAD` is absent), plus staged, unstaged and untracked changes. It unescapes `\|`, reports an invalid regex as a blocking finding, and gains `--validate` for the registry itself. Advisory findings print and exit 0.
4. **The Stop hook exits 2 with the findings on stderr, once per distinct set of blocking findings.** The once-per-signature gate is extracted to `scripts/hooks/lib/warn-once.sh`, shared with `03e-adr-gap-check.sh`. Per provider:
   - Claude Code and Codex continue the turn;
   - the opencode plugin logs the findings.

   `stop.sh` already downgrades an exit 2 to 0 while `stop_hook_active` is set.
5. **Precedence among project sources:**
   - Within one source, a scoped rule narrows a global one inside its scope.
   - Across sources there is no fixed ranking: a conflict goes through the Contradiction Guard, which now also reads the registry and `docs/specs/`. The losing source is then updated through its own change process (superseding ADR, spec amendment, edit).

## Consequences

### Positive
- The only machine-checked rule source now catches what an agent changes in the session, and the agent sees the finding.
- A project can write a rule for one area (`src/api/*`) without loading it into every task. Out-of-scope rows stay out of the review.
- A broken row (bad regex, moved `canonical_ref`) surfaces through `--validate` in the health check and in CI instead of silently matching nothing.

### Negative
- A violation the turn cannot fix still costs one continuation before the signature silences it.
- On opencode the agent never sees the finding: the plugin can only log it.
- CI enforcement needs a committed copy of the script (`skills/devops/cicd-base/SKILL.md` § Project Rule Lint), because `.dev-team-agents/scripts/` is a bind artifact. That copy can drift from the shipped version; the health check warns when it differs.

### Neutral
- Prose in `code-standards.md` stays unchecked. A rule that matters enough to enforce moves into the registry as a `review-rule` or `code-pattern` row.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| A separate `docs/development/rules/*.md` tree with `paths:` frontmatter and an index | A second artifact holding the same kind of fact as the registry; the lint, reviewers and `/devteam:rule` would need two readers. Kept as an option if rules ever need long-form bodies — `canonical_ref` to a doc anchor covers that today |
| Render scoped rules to `.claude/rules/` | Claude-only; breaks provider parity, and the registry would still be needed for the lint |
| Keep exit 1 and print to stdout | No provider surfaces either to the agent at Stop; the finding would stay invisible |
| Exit 2 on every Stop while a violation exists | A violation the turn cannot clear would re-block after every reply — the failure `03e-adr-gap-check.sh` already hit |
