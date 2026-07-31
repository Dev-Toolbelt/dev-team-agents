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
   - Detect SonarQube using the `## Detection Signals` table in `skills/devops/sonarqube/SKILL.md` — if **any** signal in that table matches, load the skill. That table is the single source of truth; do not maintain or infer a signal list here, and do not treat the config files as the only trigger (a CI scanner step or a `sonarqube` service in `docker-compose.yml` counts too).

Apply `skills/shared/token-efficiency/SKILL.md` — prefer `grep`/`head` over full-file reads; use `git diff` output directly rather than re-reading changed files.

After loading this skill, apply `skills/shared/reviewer-mindset/SKILL.md` for the review mindset questions.
