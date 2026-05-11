---
name: reviewer-base
description: Code reviewer shared rules — context, SonarQube, commit style.
---

## Foundational Rule — Load Context First

Before reviewing anything, load context in this order:

| Step | What to load | Purpose |
|------|-------------|---------|
| 1 | `README.md`, `CLAUDE.md`, `AGENTS.md` | Project conventions |
| 2 | `.claude/docs/project.md` | Synthesized project overview |
| 3 | `.claude/user-data/session-summary.md` (topmost `## YYYY-MM-DD` block only) | Last session's decisions and next steps |
| 4 | `.claude/docs/development/code-standards.md` | **Primary review guide** |
| 5 | `.claude/docs/development/architecture.md` | Architectural decisions to validate against |
| 6 | Linter/static analysis configs (`phpcs.xml`, `.eslintrc`, `.prettierrc`, `pyproject.toml`, `.rubocop.yml`, `golangci.yml`) | Source of truth for style |
| 7 | `git log --oneline -10` | Recent commits — team conventions and blast radius |
| 8 | `git diff main...HEAD` | Exact changeset; focus all findings here, not pre-existing code |
| 9 | `skills/shared/comments-policy/SKILL.md` | Apply when reviewing comments in the code |
| 10 | `skills/shared/conventional-commits/SKILL.md` | Validate commit messages in the changeset |
| 11 | **SonarQube detection**: if `sonar-project.properties`, `.sonarcloud.properties`, or `SONAR_TOKEN` is present → load `skills/devops/sonarqube/SKILL.md` | Quality gate and security hotspot reporting |

**Project standards override base standards. Always.**

Apply `skills/shared/token-efficiency/SKILL.md` — prefer `grep`/`head` over full-file reads; use `git diff` output directly rather than re-reading changed files.

After loading this skill, apply `skills/shared/reviewer-mindset/SKILL.md` for the review mindset questions.
