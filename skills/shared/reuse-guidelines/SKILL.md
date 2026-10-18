---
name: reuse-guidelines
description: Registry of mandatory reuse/standardization rules and the review/lint gates that enforce them.
---

# Reuse Guidelines

Structural-layer registry (see `skills/shared/project-context/SKILL.md` § Memory Layers — this is "current state: standards") that catalogs project-wide rules the team has explicitly decided to standardize on. Its job: stop the next task from re-deciding, ignoring, or drifting from something already settled.

A rule belongs here only when it is **not derivable from the code** and **will still be true after this sprint**. One-off preferences go in `docs/development/code-standards.md` instead.

## Registry File

`docs/development/reuse-guidelines.md` — one Markdown table, one row per rule:

```markdown
| name | type | rule | detection | canonical_ref | scope | severity | added |
|------|------|------|-----------|---------------|-------|----------|-------|
| modal | code-pattern | Always use the shared Modal, never a new modal implementation | `\b(new Modal\(\|<div[^>]*className=["'][^"']*\bmodal\b)` | src/components/Modal.tsx | src/* | blocking | 2026-10-17 |
| upload_location | path-convention | Upload-handling files must live under xpto/pasta | `path:*Upload*=>xpto/pasta/` | xpto/pasta/ | | | |
| buttons_left | design-rule | Buttons in section X are always left-aligned | (review-only — no regex; verify visually against canonical_ref) | docs/design/design-system.md#section-x | | advisory | |
| api_no_db | review-rule | Controllers never query the database directly; go through a service | (review-only) | docs/development/architecture.md#layers | src/api/* | | 2026-10-17 |
```

Not code-fenced in the real file — this is a live Markdown table in `docs/development/reuse-guidelines.md`, readable as a normal doc and parseable by splitting on unescaped `|` (skip the header and the `---` separator row).

| Column | Meaning |
|--------|---------|
| `name` | Short identifier, used in violation messages and cross-references |
| `type` | `code-pattern` \| `path-convention` \| `design-rule` \| `review-rule` — decides which enforcement below applies |
| `rule` | One sentence, human-readable — what must always/never happen |
| `detection` | For `code-pattern`: a POSIX extended regex (`grep -E`) matched against **added** lines — avoid `\d`/`\s`, which GNU and BSD grep read differently. For `path-convention`: `path:<name-glob>=><required-dir>` — any added/modified file whose basename matches `<name-glob>` must live under `<required-dir>`. For `design-rule` / `review-rule`: literal `(review-only — ...)`, never a regex — nothing here is machine-checked |
| `canonical_ref` | The file, doc anchor, or path that IS the correct implementation/location |
| `scope` | *Optional.* Comma-separated globs matched against the repo-relative path; `*` crosses directories (`src/api/*` covers nested files). Empty or `*` = whole repository. A row only applies to files inside its scope — for the lint and for the review gate |
| `severity` | *Optional.* `blocking` (default when empty) or `advisory`. Advisory findings are reported but never fail the lint, never block the Stop hook, and are reported as `[SUGGESTION]` in review |
| `added` | *Optional.* `YYYY-MM-DD` the rule was registered — what the health check uses to surface rules worth re-confirming |

The last three columns are optional and positional at the end of the row, so a five-column registry stays valid as written. A literal `|` inside a cell (a regex alternation) is written `\|`, the Markdown table escape; the lint unescapes it before compiling the regex.

The file does not exist until a project creates one. Its absence means no rule is registered — never treat that as a lint failure.

## Three Enforcement Behaviors, by `type`

| `type` | Mechanism | Who enforces |
|--------|-----------|--------------|
| `code-pattern` | `detection` regex run against added diff lines | `scripts/reuse-lint.sh` (hard, CI/Stop hook) **and** the review gate below |
| `path-convention` | Touched/added file's path checked against the `path:` glob in `detection` | `scripts/reuse-lint.sh` (hard, CI/Stop hook) **and** the review gate below |
| `design-rule` | Not mechanizable — no script can judge alignment, layout, or "follows pattern X/Y/Z" | **Review gate only** — see below. The hard part here is never skipping the row, not detecting it automatically |
| `review-rule` | Same as `design-rule`, for non-visual conventions (layering, error handling, naming inside an area). Combined with `scope`, this is how a project writes a rule that applies to one part of the codebase only | **Review gate only** |

Scoping and the review gate are agent behavior, so they work identically on every provider — no provider-native rules directory is involved. The Stop-hook surfacing differs per provider; see Hard Lint below.

## Review Gate (agents)

`code-reviewer`, `backend-reviewer`, and `frontend-reviewer` load this skill as part of their Foundational Rule additions. When `docs/development/reuse-guidelines.md` exists:

1. Keep only the rows whose `scope` matches at least one file in the diff — filter on the `scope` column rather than reading the whole table into the review once the registry grows. Out-of-scope rows are not carried into the review.
2. For `code-pattern` / `path-convention` rows: same check the lint script runs — report a match citing `name` and `canonical_ref`.
3. For `design-rule` / `review-rule` rows: **iterate every remaining row explicitly against the diff** — this cannot be delegated to a script, so skipping it silently is the one failure mode that matters here. If the changeset touches the area the `rule` describes and does not conform, report it citing `name`, `rule`, and `canonical_ref`. If the row's area is untouched by the diff, say nothing about it.
4. Severity: a `blocking` (or empty) row is reported `[BLOCKING]`; an `advisory` row is reported `[SUGGESTION]`.

Coding agents apply the same filter before writing: the rows whose `scope` matches the files they are about to touch are rules for that task.

Never copy the registry's rows into the review output — reference the row's `name` and let the file be the source of truth.

## Auto-detection During Review

The Review Gate above catches deviations from rows that already exist. This is the earlier step: catching a deviation that has **no row yet**. When `code-reviewer`/`backend-reviewer`/`frontend-reviewer` finds the same pattern deviation (same underlying rule being broken, not merely the same file) appearing **2 or more times** in the changeset under review, treat it as a standardization candidate, not just a repeated finding:

1. Report each occurrence normally in the review (`[SUGGESTION]` or `[BLOCKING]` per its own severity).
2. In the review summary, add one line proposing the row: `name`, `type`, `rule`, and a draft `detection`/`canonical_ref` per the classify step in "Growing the Registry" below.
3. Do not append the row yourself mid-review — hand the proposal to the user the same way `/devteam:rule` would, and let them confirm before it is written.

A single occurrence is just a finding. Two or more in the same diff is a pattern the registry exists to stop from recurring next sprint.

## Hard Lint (CI / Stop hook)

`scripts/reuse-lint.sh` (installed at `.dev-team-agents/scripts/reuse-lint.sh`) runs the `code-pattern` and `path-convention` rows non-interactively against everything the branch adds: its commits against the base branch plus staged, unstaged, and untracked changes. It never scans `.dev-team-agents/` (the installed framework, not project code) and never follows an untracked symlink. It exits 1 on any blocking match and 0 when only advisory findings remain. `design-rule` / `review-rule` rows are parsed but never checked mechanically. Degrades to exit 0 silently when the registry file is absent.

| Where it runs | Behavior |
|---------------|----------|
| Stop hook (`03c-reuse-lint.sh`) | Blocking findings exit 2 with the findings on stderr, once per distinct set of findings — Claude Code and Codex continue the turn so the agent fixes them; the opencode plugin logs them |
| CI | The step in `skills/devops/cicd-base/SKILL.md` § Project Rule Lint |
| Health check | `reuse-lint.sh --validate` checks the registry itself: every `detection` regex compiles, every `canonical_ref` exists, `type`/`severity`/`added` are well-formed. An invalid regex is also reported as a blocking finding by the normal lint run, never treated as "no match" |

## Growing the Registry — Standardization Trigger and `/devteam:rule`

The registry is meant to grow without the user re-explaining a decision. Two paths write to it, sharing the same classify → propose → confirm → append routine — neither writes silently:

- **Passive capture**: the Convention / Standardization Signals already recognized by `skills/shared/docs-sync/references/update-triggers.md` — when one of those signals names a specific reusable component, path, or design rule (its "Where to write user-triggered entries" step 0), it routes here instead of to the wiki/code-standards.md. This skill does not restate that trigger table.
- **Explicit capture**: `/devteam:rule <description>` (see `commands/rule.md`), for when the user wants to catalog something outside the flow of another task.

Both resolve to the same steps:

1. Classify `type` from the description — `code-pattern` if it names a component/class/helper to reuse, `path-convention` if it's about file location, `design-rule` for a visual/layout rule, `review-rule` for any other convention.
2. Derive `canonical_ref` from context (grep the repo for the named component/file; ask the user if it can't be resolved unambiguously).
3. For `code-pattern`, draft a `detection` regex from the canonical implementation's own markup/API — never a placeholder that would never match.
4. Derive `scope` when the description names an area ("in the API", "under `src/admin`"); leave it empty for a repository-wide rule. Propose `severity` — `blocking` unless the user framed it as a preference — and set `added` to today.
5. Show the proposed row to the user before writing it.
6. Append the confirmed row to `docs/development/reuse-guidelines.md`, then run `reuse-lint.sh --validate`.

## Updating the Registry

Adding, editing, or retiring a row is a `docs/development/*.md`-class change. A five-column registry stays five columns until a row needs `scope`, `severity`, or `added`; then widen the header and separator to all eight columns in the same edit — existing five-cell rows remain valid. It sits in the same Structural layer as `code-standards.md`. Retiring a rule: delete the row, do not comment it out — a disabled rule that still parses as active is a false negative waiting to happen.

**When the canonical implementation's dependency changes, update `detection` in the same change.** A `code-pattern` row's regex is often written against a specific import path or library name (e.g. `from '[r]eact-hot-toast'`). If a later task swaps that library (e.g. to `sonner`) without touching the registry row, the regex keeps parsing and `reuse-lint.sh` keeps exiting 0 — but it can no longer match the thing it exists to catch. This is a silent false negative, not a missing rule, so it will not surface on its own. Whenever you change what a `canonical_ref` file imports or depends on, grep the registry for rows whose `detection` references the old dependency and update them in the same commit.
