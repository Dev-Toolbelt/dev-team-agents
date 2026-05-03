---
name: conventional-commits
description: Conventional Commits 1.0.0 standard for commit messages and changelogs. Use when writing, reviewing, or generating git commit messages. Covers types, scopes, breaking changes, and multi-line body format.
---

# Conventional Commits

Follow the [Conventional Commits 1.0.0](https://www.conventionalcommits.org/) specification.

## Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
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

- **Description**: imperative, lowercase, no period at end — `add login endpoint`, not `Added login endpoint.`
- **Scope**: noun in parentheses describing the affected section — `feat(auth): add JWT refresh`
- **Breaking change**: append `!` after type/scope OR add `BREAKING CHANGE:` footer
- **Body**: use when the WHY is not obvious; wrap at 72 characters
- **Footer**: `BREAKING CHANGE: <description>`, `Fixes #123`, `Co-authored-by: Name <email>`

## Examples

```
feat(auth): add JWT refresh token rotation

Tokens now rotate on each use to reduce the window for token theft.
Previous tokens are invalidated immediately after rotation.

Fixes #42
```

```
fix!: remove deprecated payment endpoint

BREAKING CHANGE: /api/v1/pay is removed. Use /api/v2/payments instead.
```

```
chore(deps): upgrade Laravel to 11.x
```

## Changelog Generation

Group commits by type for changelog:
- **Breaking Changes** — `!` or `BREAKING CHANGE` footer
- **Features** — `feat`
- **Bug Fixes** — `fix`
- **Performance** — `perf`
- Other types are typically omitted from user-facing changelogs
