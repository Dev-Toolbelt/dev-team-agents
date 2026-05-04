---
name: conventional-commits
description: Conventional Commits 1.0.0 standard for commit messages and changelogs. Use when writing, reviewing, or generating git commit messages. Covers types, scopes, breaking changes, layered commits, and multi-line body format.
---

# Conventional Commits

Follow the [Conventional Commits 1.0.0](https://www.conventionalcommits.org/) specification.

## Format

```
<type>[optional scope][!]: <description>

[optional body]
```

## Types

| Type | When to use |
|------|-------------|
| `feat` | New feature for the user |
| `fix` | Bug fix for the user |
| `docs` | Documentation only |
| `style` | Formatting, missing semicolons — no logic change |
| `refactor` | Code change that is neither fix nor feature |
| `perf` | Performance improvement |
| `test` | Adding or correcting tests |
| `build` | Build system or dependency changes |
| `ci` | CI/CD configuration changes |
| `chore` | Other changes that don't modify src or test files |
| `revert` | Reverts a previous commit |

## Rules

- **Description**: imperative, lowercase, ≤72 characters, no trailing period — `add login endpoint`, not `Added login endpoint.`
- **Scope**: noun in parentheses describing the affected section. **Derive scope from this repository's history** — use folder names under `src/`, `app/`, `packages/`, or whatever the recent `git log` already uses. Do not invent scopes that don't match the repo.
- **Breaking change**: append `!` after type/scope (`refactor(api)!:`). When `!` is used, the body **must** start with `BREAKING CHANGE:` followed by what breaks and migration notes.
- **Body**: use when the WHY is not obvious; wrap at 72 characters. Explain motivation and context — the diff already shows what changed.
- **Footers**: omit unless explicitly requested. Do not add `Co-Authored-By:`, `Reviewed-by:`, `Signed-off-by:`, `Fixes:`, `Closes:`, or similar footers unless the user asks for them. **Never add Claude as co-author** (`Co-Authored-By: Claude` or any variant) — commits must only carry the authenticated git user's authorship.

## Layered Commits

When a single logical change spans multiple architectural layers (e.g., a new endpoint with migration + model + service + controller + tests), **produce one commit per layer** ordered from the lowest-level dependency to the highest. This keeps each commit coherent and makes history readable as a dependency chain.

Generic ordering (adapt to the project's stack):

| Order | Layer | Examples |
|-------|-------|---------|
| 1 | Data / schema | migrations, seed data, fixtures |
| 2 | Domain | entities, value objects, domain models |
| 3 | Persistence | ORM models, repository interfaces |
| 4 | Infrastructure | repository implementations, adapters, queries |
| 5 | Application | services, use cases, handlers, DTOs |
| 6 | Interface | controllers, routes, CLI commands, views |
| 7 | Tests | unit, integration, E2E (bundle or split by suite) |

Rules:
- Skip layers with no change
- Each commit must leave the codebase in a compilable/runnable state
- If two unrelated features are mixed, run the sequence per feature
- Never bundle unrelated changes into one commit

Example sequence for a full CRUD:
```
feat(<module>): add <Entity> schema migration
feat(<module>): add <Entity> domain entity
feat(<module>): expose <Entity> persistence model
feat(<module>): add <Entity> CRUD services
feat(<module>): expose <Entity> CRUD endpoints
test(<module>): cover <Entity> CRUD with integration and e2e tests
```

## Examples

```
feat(auth): add JWT refresh token rotation

Tokens now rotate on each use to reduce the window for token theft.
Previous tokens are invalidated immediately after rotation.
```

```
refactor(api)!: remove deprecated payment endpoint

BREAKING CHANGE: /api/v1/pay is removed. Use /api/v2/payments instead.
All clients must update to the new endpoint before this version is deployed.
```

```
fix(scheduler): prevent double firing when cron runs twice in the same minute

Guard with a status = PENDING check inside the update query to make the
operation idempotent under clock drift.
```

```
chore(deps): upgrade Laravel to 11.x
```

## Changelog Generation

Group commits by type for changelog:
- **Breaking Changes** — `!` or `BREAKING CHANGE` in body
- **Features** — `feat`
- **Bug Fixes** — `fix`
- **Performance** — `perf`
- Other types are typically omitted from user-facing changelogs
