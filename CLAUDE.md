# CLAUDE.md — dev-team-agents

Instructions for working on this repository. These rules apply to Claude when authoring or modifying agents, skills, workflows, scripts, and documentation inside `dev-team-agents`.

---

## What This Repo Is

A global team of specialized Claude Code agents and skills for software development. Stack-agnostic, project-aware. Installed at the project level (`.claude/dev-team-agents/`) — not globally.

---

## Language

**All content in this repository must be written in English** — agents, skills, workflows, templates, comments, commit messages, and documentation — unless a specific piece of content is explicitly marked as an exception (e.g., a locale-specific example).

This applies to:
- Agent instructions and behavior descriptions
- Skill bodies and reference material
- Workflow steps and prompt examples
- Template files
- README.md, CLAUDE.md

### README Sync Rule

`README.pt-BR.md` is the Portuguese translation of `README.md`. **Any change made to `README.md` must also be reflected in `README.pt-BR.md`** in the same commit or PR. These two files must always be kept in sync. If you update one, update the other.

### Auto-Docs Rule

After completing any task that changes **observable behavior** — installation flow, update mechanism, script flags, `.claude/` directory structure, versioning strategy, or agent/skill naming — **automatically update `README.md`, `README.pt-BR.md`, and `CLAUDE.md`** before considering the task done. Do not wait to be asked. The update must happen in the same working session as the change that triggered it.

---

## Mandatory Plan Mode Before Any Execution

**Before executing any non-trivial task** (file creation, file modification, script changes, refactoring, agent authoring), you MUST:

1. Present a plan using the canonical format in `templates/plan-template.md`
2. State explicitly: **"Awaiting your approval before proceeding."**
3. Only execute after the user approves

One-liner fixes (typo, single-line change, rename in one file) may proceed without a plan. Everything else requires a plan.

**Never execute and then explain.** Always plan first, execute second.

### Parallel Execution After Approval

When generating a plan, use the `Par.` column in the STEPS table to group steps that can run simultaneously:
- Assign the same letter (A, B, C…) to steps with no dependency on each other
- Use `—` for steps that must complete before the next can start
- After the user approves, explicitly instruct them: **send all prompts for the same Par. group in a single message** so the agents run in parallel

This reduces total wall-clock time significantly on multi-agent tasks.

---

## Authoring Standards

### Agents (`agents/*.md`)

- Frontmatter: `name`, `description`, `model`, `tools`
- Model assignment: `claude-opus-4-7` (decision-making), `claude-sonnet-4-6` (execution), `claude-haiku-4-5-20251001` (structured output)
- Every agent must include: **Foundational Rule** (load context first) + **Immutability Warning**
- Stack-agnostic: no hardcoded framework, language, or tool references in agent core behavior
- Max ~200 lines per agent; move reference material to skills

**Coding agents** (`backend-developer`, `frontend-developer`, `database-specialist`, `devops-specialist`, `ui-ux-designer`, `backend-test-specialist`, `frontend-test-specialist`) must also include a **`## Worktree Isolation`** section using the canonical session-file pattern:

1. Read `.claude/.worktree-session` — if it exists, follow the stored decision silently (`worktree=no` or `worktree=yes branch=<b>`)
2. If absent, ask the user once, write the decision to `.claude/.worktree-session`, then act
3. On "yes": load `skills/shared/worktree/SKILL.md` with the provided branch (default: `main`)

This ensures multi-agent workflows ask the worktree question exactly once.

### Skills (`skills/**/*.md`)

- Follow [agentskills.io specification](https://agentskills.io/specification)
- Frontmatter: `name`, `description`
- Body is current rules only — no change history, no "was removed / replaced by" narratives
- Max ~500 lines; move long reference material to `references/` subdirectory
- Prefer tables and bullets over prose

#### Token Efficiency

All agents should apply token-efficient patterns by default. The canonical reference is `skills/shared/token-efficiency/SKILL.md`. Load it explicitly when:
- Authoring or reviewing a coding agent that reads many files
- Optimizing a workflow that involves large output or log files
- Guiding model selection for multi-step tasks (Opus → understand, Sonnet → execute)

Key rules (apply without loading the full skill):
- Prefer `grep`/`head`/`tail` over reading entire files
- Prefer `cp`/`sed`/`awk` bash commands over Read + Write for large or repetitive file operations
- Summarize command output instead of dumping raw content
- Use `--quiet`/`-q` flags by default

#### User-Invocable Skills

Skills that users trigger directly via slash command must be registered here:

| Skill | Path | Trigger |
|-------|------|---------|
| `skill-creator` | `skills/skill-creator/SKILL.md` | `/skill-creator` or "create/update a skill" |
| `review` | `agents/code-reviewer.md` | `/review`, `/review backend`, `/review frontend`, `/review both` |

### Workflows (`workflows/*.md`)

- Each step must include:
  1. The prompt the user gives to Claude
  2. What the agent produces
  3. A note that the agent will present a Plan before executing
- Name files: `<context>.md` (e.g., `new-project.md`, `bug-fix.md`)

### Templates (`templates/*.md`)

- Standalone, copy-paste ready
- No hardcoded project-specific values — use `[placeholders]`

### Scripts (`scripts/*.sh`)

- `set -euo pipefail` at top
- Silent on success when possible
- Fail gracefully (no network → exit 0, not error)

---

## File Structure

```
dev-team-agents/
├── agents/          ← agent definitions (.md)
├── skills/          ← modular skill knowledge
│   ├── shared/      ← foundational rules used by all agents
│   ├── architecture/
│   ├── testing/
│   ├── security/
│   ├── design/
│   ├── devops/      ← one skill per platform
│   ├── integrations/ ← platform/integration-specific reference skills
│   └── ui-libraries/ ← UI component library reference skills
├── workflows/       ← step-by-step workflow guides
├── templates/       ← document templates (plan, backlog, ADR, etc.)
├── scripts/         ← update.sh, session-summary-hook.sh, graphify-refresh.sh, new-adr.sh
├── README.md
└── CLAUDE.md        ← this file
```

---

## User Data Directory

When installed in a project, the installer creates two sibling directories under `.claude/`:

| Directory | Purpose |
|-----------|---------|
| `.claude/dev-team-agents/` | Package files — replaced entirely on every update |
| `.claude/user-data/` | User state and config — **never touched by the installer** |

Files in `user-data/`:
- `.installed-version` — current installed version tag
- `.last-update-check` — Unix timestamp of last update check (prevents daily hammering)
- `.auto-update` — flag file; present = automatic updates enabled
- `graphify.json` — Graphify config (created by the `graphify-setup` skill if enabled)

**Rule:** any file that must survive an update must live in `.claude/user-data/`, not inside `.claude/dev-team-agents/`. Never store user config or state inside the package directory.

**Package exclusions:** `CLAUDE.md`, `scripts/install.sh`, and `scripts/orphan-skill-scan.sh` are stripped from the extracted tarball before it is placed in the project. `CLAUDE.md` contains authoring rules for this repository, not for end-users; `install.sh` is accessed exclusively via `curl`; `orphan-skill-scan.sh` is a development tool for this repository and is not relevant to user projects.

---

## Versioning

- Semantic versioning via git tags: `v1.0.0`, `v1.1.0`, `v2.0.0`
- Breaking changes (agent behavior changes, removed skills) → major version bump
- New agents/skills → minor version bump
- Fixes, clarifications → patch bump

---

## Immutability Contract

These files are installed via symlinks into user projects. Users are warned not to modify them directly. When authoring changes:

- Maintain backward compatibility where possible
- If a breaking change is unavoidable, document it in the PR description and README release notes
- Never remove a skill or agent without a deprecation cycle (one minor version with a warning)

---

## Agent Memory System

Three mechanisms work together to minimize context loss between sessions. All three are enforced automatically after installation.

### Session Summary Rule

**At the end of any session where files were created or modified**, write a new entry at the top of `.claude/session-summary.md`:

```
## YYYY-MM-DD | [brief task title]
**Done**: what was implemented or changed
**Decisions**: key choices made and why
**Next**: what remains or is recommended next
```

- One entry per session per task; append to the same entry if continuing the same task the same day
- This file is read at agent startup via `skills/shared/project-context/SKILL.md`
- The `Stop` hook (`scripts/session-summary-hook.sh`) detects when this is missing and prompts you

### ADR Trigger Rule

Write an ADR when a decision is:
- Hard to reverse (database engine, auth strategy, API design)
- Affects multiple components or agents
- Has non-obvious reasoning that future agents would question

**Create an ADR by running:**

```bash
bash .claude/dev-team-agents/scripts/new-adr.sh "title of the decision"
```

The script auto-numbers the file and places it in `.claude/docs/development/adrs/`. Fill in the generated template and change the status from `Proposed` to `Accepted`.

### Stop Hook (Automated Enforcement)

`install.sh` registers `scripts/session-summary-hook.sh` as a `Stop` hook in `.claude/settings.json`. This hook:

- Runs automatically each time Claude finishes responding
- Detects uncommitted changes without a session-summary entry for today
- Outputs a structured reminder visible to Claude on the next turn, which then writes the summary

No manual setup is required — the installer handles registration.

---

## Orphan Skill Self-Check Rule

**After any session where files in `agents/` or `skills/` were created or modified**, run:

```bash
bash scripts/orphan-skill-scan.sh
```

Read the output and act on it before considering the task done:

- **AUTO-FIXED** lines: broken path references were automatically removed from agent files — verify the agent still reads correctly after the removal.
- **ACTION REQUIRED** lines: a skill has no agent reference. Add a load reference in the suggested agent file, following that agent's existing skill-loading pattern (full path or backtick name form, whichever is already used).

User-invocable skills (registered in the "User-Invocable Skills" table above) are excluded from this check — they are triggered by humans, not loaded by agents.

The `Stop` hook (`.claude/settings.json`) runs `orphan-skill-scan.sh --quiet` automatically at the end of every session as a safety net.

---

## Setup Trigger

When the user writes any prompt matching the intent of setting up the project with dev-team-agents — such as:

- "Help me set up this project with dev-team-agents"
- "Configure dev-team-agents for this project"
- "Set up the agent team for this project"
- "Initialize dev-team-agents here"

**Immediately invoke the `setup-assistant` agent.** Do not ask clarifying questions first, do not run any commands, do not read files yourself — hand off directly to `setup-assistant`, which is designed to gather all context and drive the full setup flow.

---

## Coexistence Rule (Core Principle)

`dev-team-agents` is the base layer. Any rule in the target project's CLAUDE.md, README.md, AGENTS.md, or `.agents/` always takes precedence over these base standards. Agents must load and respect project context before acting on any task.

This principle must be reinforced in every agent and every workflow.
