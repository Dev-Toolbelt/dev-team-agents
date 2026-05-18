---
name: workflow-detection
description: Intent classification table for software-architect. Maps user request keywords to the matching workflow file to load from .claude/dev-team-agents/workflows/.
---

# Workflow Detection

**Before acting on any request**, classify the user's intent and load the matching workflow file from `.claude/dev-team-agents/workflows/`. Read the detected workflow to understand the expected steps, outputs, and agent collaboration pattern — then follow it.

| Intent signals (keywords / phrases) | Workflow to load |
|---|---|
| new project, start from scratch, greenfield, initialize project, create project, bootstrap | `new-project.md` |
| bug, fix, broken, error, crash, regression, hotfix, not working | `bug-fix.md` |
| refactor, cleanup, restructure, reorganize, technical debt, improve structure, decouple | `refactor.md` |
| security, vulnerability, CVE, exploit, breach, patch, pentest, auth flaw | `security-patch.md` |
| design, UI, UX, interface, wireframe, prototype, visual, component library | `design.md` |
| mobile, React Native, Expo, Flutter, iOS, Android, native app | `mobile.md` |
| fullstack, full-stack, frontend + backend, end-to-end feature | `fullstack.md` |
| review, audit, inspect, code review, analyze PR, quality check | `review.md` |
| inherited, legacy, existing project, take over, onboard, unfamiliar codebase | `inherited-project.md` |
| _(no clear signal — fallback)_ | `maintenance.md` |

**Detection rules:**
1. Match against the user's full request text (case-insensitive).
2. If multiple signals match, pick the workflow whose signals are most dominant in the request.
3. If still ambiguous, fall back to `maintenance.md`.
4. After detecting, briefly state the chosen workflow to the user (one line) before proceeding — e.g., _"Following the **refactor** workflow."_ — so they can correct it if needed.
