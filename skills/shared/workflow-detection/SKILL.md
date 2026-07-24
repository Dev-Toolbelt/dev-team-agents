---
name: workflow-detection
description: Intent classification table for software-architect. Maps a user request to a scope-specific workflow file when one exists; otherwise the architect handles the request with its own built-in behavior.
---

# Workflow Detection

**Before acting on any request**, classify the user's intent. If it matches one of the scope-specific workflows below, load that file from `.claude/dev-team-agents/workflows/` and follow it. Otherwise, **handle the request with your own built-in behavior** — there is no workflow file to load.

| Intent signals (keywords / phrases) | Workflow to load |
|---|---|
| refactor, cleanup, restructure, reorganize, technical debt, improve structure, decouple | `refactor.md` |
| design, UI, UX, interface, wireframe, prototype, visual, component library | `design.md` |
| mobile, React Native, Expo, Flutter, iOS, Android, native app | `mobile.md` |
| fullstack, full-stack, frontend + backend, end-to-end feature | `fullstack.md` |
| review, audit, inspect, code review, analyze PR, quality check | `review.md` |
| _(anything else — new project, bug fix, security patch, inherited/legacy code, general maintenance, or no clear signal)_ | **No file — use built-in behavior** (see below) |

**Built-in behavior (default):** for requests that don't match a scope-specific workflow — greenfield projects, bug fixes, security patches, inherited/legacy codebases, or routine maintenance — do not load a workflow file. Apply your own analysis-first process: understand the context, identify the change, plan it, and present the plan for approval. These lifecycle concerns are now encapsulated in the agent, not in separate workflow documents.

**Detection rules:**
1. Match against the user's full request text (case-insensitive).
2. If multiple signals match, pick the workflow whose signals are most dominant in the request.
3. If no signal matches a scope-specific workflow, use built-in behavior — do not force a match.
4. After detecting, state the chosen path in one line before proceeding — e.g., _"Following the **refactor** workflow."_ or _"Handling this directly (no scope-specific workflow)."_ — so the user can correct it if needed.
