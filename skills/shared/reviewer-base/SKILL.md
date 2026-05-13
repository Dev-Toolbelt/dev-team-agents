---
name: reviewer-base
description: Code reviewer shared rules — context, SonarQube, commit style.
---

## Foundational Rule

1. Load `skills/shared/project-context/SKILL.md` — covers README, CLAUDE.md, AGENTS.md, project.md, session-summary, code-standards, architecture, and recent git log.

2. Additionally for review sessions:
   - Read linter configs (`.eslintrc*`, `pyproject.toml`, `.rubocop.yml`, `phpcs.xml`, `golangci.yml`) — source of truth for style
   - Run `git diff main...HEAD` to scope the review to what changed; focus all findings here, not pre-existing code
   - Load `skills/shared/comments-policy/SKILL.md`
   - Load `skills/shared/conventional-commits/SKILL.md`
   - Detect SonarQube: if `sonar-project.properties`, `.sonarcloud.properties`, or `SONAR_TOKEN` is present → load `skills/devops/sonarqube/SKILL.md`

Apply `skills/shared/token-efficiency/SKILL.md` — prefer `grep`/`head` over full-file reads; use `git diff` output directly rather than re-reading changed files.

After loading this skill, apply `skills/shared/reviewer-mindset/SKILL.md` for the review mindset questions.
