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

### Skills (`skills/**/*.md`)

- Follow [agentskills.io specification](https://agentskills.io/specification)
- Frontmatter: `name`, `description`
- Body is current rules only — no change history, no "was removed / replaced by" narratives
- Max ~500 lines; move long reference material to `references/` subdirectory
- Prefer tables and bullets over prose

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
├── scripts/         ← install.sh, check-updates.sh
├── README.md
└── CLAUDE.md        ← this file
```

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

## Coexistence Rule (Core Principle)

`dev-team-agents` is the base layer. Any rule in the target project's CLAUDE.md, README.md, AGENTS.md, or `.agents/` always takes precedence over these base standards. Agents must load and respect project context before acting on any task.

This principle must be reinforced in every agent and every workflow.
