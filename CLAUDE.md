# CLAUDE.md — dev-team-agents

Instructions for working on this repository. These rules apply to Claude when authoring or modifying agents, skills, scripts, and documentation inside `dev-team-agents`.

---

## What This Repo Is

A global team of specialized Claude Code agents and skills for software development. Stack-agnostic, project-aware. Installed at the project level (`.dev-team-agents/`) — not globally.

The canonical source (`agents/`, `commands/`, `skills/`, `scripts/hooks/`) is **provider-agnostic**. Claude Code is the default provider; opencode and OpenAI Codex CLI are supported via a render engine (`scripts/render-provider.sh`) that emits the provider-specific file tree per target project. See `docs/providers.md` for the tier → model id map and the per-provider install scripts.

---

## Language

**All content in this repository must be written in English** — agents, skills, templates, comments, commit messages, and documentation — unless a specific piece of content is explicitly marked as an exception (e.g., a locale-specific example).

This applies to:
- Agent instructions and behavior descriptions
- Skill bodies and reference material
- Prompt and command templates
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
- Model assignment: `claude-opus-4-7` (decision-making, complex reasoning), `claude-sonnet-4-6` (execution, coding, structured output)
  > Note: Haiku is available for future micro-agents with strict latency/cost requirements; add it back when a concrete candidate emerges.
- Tools order: `Read, Write, Edit, Glob, Grep, Bash, WebSearch, WebFetch` (write-capable agents); `Read, Glob, Grep, Bash` (read-only reviewers). Append optional tools (WebSearch, WebFetch) in that order.
- Every agent must include: **Foundational Rule** (load context first) + **Immutability Warning**
- Stack-agnostic: no hardcoded framework, language, or tool references in agent core behavior
- Max ~200 lines per agent; move reference material to skills

**Coding agents** (`backend-developer`, `frontend-developer`, `mobile-developer`, `database-specialist`, `devops-specialist`, `ui-ux-designer`, `backend-test-specialist`, `frontend-test-specialist`) must also include a **`## Worktree Isolation`** section using the canonical **decision cascade** (resolve top-down, stop at the first match):

1. `.dev-team-agents/.worktree-session` present → follow the stored decision silently:
   - `worktree=no branch=<b>` → operate on branch `<b>`; do not load the worktree skill
   - `worktree=yes branch=<b>` → load `skills/shared/worktree/SKILL.md` using base branch `<b>`
2. Session file absent → read `worktree_active` from `.dev-team-agents/user-data/preferences.json`:
   - `true` → set up a worktree **without asking**: resolve base branch (`worktree_base_branch` → project config → auto-detected default branch), write `worktree=yes branch=<base>`, load the skill
   - `false` → do **not** show the worktree yes/no prompt; ask only for a new branch name (suggest `<context>/<brief-title>`), `git checkout -b <name>`, write `worktree=no branch=<name>`
3. Key absent (legacy install) → ask the user once with `AskUserQuestion` (Yes/No), then follow the matching path from step 2.

`preferences.json` is the persistent default; the session file is the per-session override. The base branch is **never** hardcoded (no `main`/`master`/`beta`) — it is auto-detected. On finalization (merge), the worktree skill enforces **rebase-onto-base → merge → teardown** of the worktree and its **isolated Docker stack only** (see `skills/shared/worktree/references/docker-isolation.md`). This ensures multi-agent workflows resolve the worktree decision exactly once.

### Skills (`skills/**/*.md`)

- Follow [agentskills.io specification](https://agentskills.io/specification)
- Frontmatter: `name`, `description`
  > Note: `allowed-tools:` is **not** a standard frontmatter key for skills in this repo. Use only `name` and `description`. The `allowed-tools:` key in `skills/shared/worktree/SKILL.md` was an experiment and has been removed.
- Body is current rules only — no change history, no "was removed / replaced by" narratives
- Max ~500 lines; move long reference material to `references/` subdirectory
- Prefer tables and bullets over prose

#### Interaction Patterns — Quiz-first Rule

All agents and commands must use the `AskUserQuestion` tool whenever asking the user a question with a finite set of reasonable answers. Plain text prompts like `(yes / no)` or `(a / b / c)` are not allowed.

Rules:
- **Yes / No questions** → always use `AskUserQuestion` with two options
- **Multiple-choice** → use `AskUserQuestion` with 2–4 options
- **Open-ended with common defaults** → add an `"Other"` option so the user can type freely
- **Strict free-form input** (branch name, ADR title, custom text) → plain text is acceptable
- Use the user's language from `preferences.json` for all option labels and descriptions

The canonical reference is `skills/shared/interaction-patterns/SKILL.md`. Load it before writing any agent or command that asks user questions.

#### Contradiction Guard

All agents automatically enforce the Contradiction Guard defined in `skills/shared/project-context/SKILL.md`. When a user request conflicts with an established rule (in `CLAUDE.md`, ADRs, architecture docs, or sprint scope), the agent must flag the conflict, cite the source, and ask for explicit confirmation before proceeding.

#### Wiki Knowledge Base

Every project gets a wiki at `docs/wiki/`. Agents write entries after completing tasks that reveal non-obvious domain knowledge — gotchas, multi-layer flows, behavioral quirks that aren't derivable from reading code. The `setup-assistant` creates `wiki/README.md` on FIRST_RUN. See `skills/shared/docs-sync/SKILL.md` for the wiki entry format, domain folder rules, and update protocol.

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
| `agent-creator` | `.claude/skills/agent-creator/SKILL.md` (global Claude skill — not in this repo) | `/agent-creator` or "create/update an agent" |
| `review` | `agents/code-reviewer.md` | `/review`, `/review backend`, `/review frontend`, `/review both` |

**Command-level skills** — loaded by `commands/*.md` files rather than by agents directly:

| Skill | Used by |
|-------|---------|
| `current-context` | All `/devteam:*` commands — detects branch/worktree state before executing |
| `spawn-classifier` | `/devteam:plan` and multi-agent commands — decides conditional agent spawn |

#### User-Invocable Commands (`commands/*.md`)

Slash commands installed to `.claude/commands/devteam/` and invoked as `/devteam:<name>` (e.g. `/devteam:plan`). This keeps all devteam commands namespaced and separate from any project-specific commands. Each command spawns agents via the Task tool and restricts scope to the current git branch/worktree unless overridden by the user.

| Command | Agents invoked | Use when… |
|---------|---------------|-----------|
| `/devteam:plan` | **product-analyst (protagonist)** + software-architect¹ | Planning a feature — product-analyst leads, produces a business-only requirements doc ready for sprints; software-architect joins only on explicit technical request |
| `/devteam:backend` | backend-developer + database-specialist¹ → backend-test-specialist² → code-reviewer + qa-specialist | Implementing backend changes (tests only if `TESTS_REQUIRED=yes`; mandatory code-review + qa handoff, consolidated summary) |
| `/devteam:frontend` | frontend-developer + ui-ux-designer¹ → frontend-test-specialist² → code-reviewer + qa-specialist | Implementing frontend changes (tests only if `TESTS_REQUIRED=yes`; mandatory code-review + qa handoff, consolidated summary) |
| `/devteam:fullstack` | backend + frontend + database¹ + ui-ux¹ → both test-specialists² → code-reviewer + qa-specialist | Implementing full-stack changes (tests only if `TESTS_REQUIRED=yes`; mandatory code-review + qa handoff, consolidated summary) |
| `/devteam:mobile` | mobile-developer + ui-ux-designer¹ → tests² → code-reviewer + qa-specialist | Implementing mobile features (tests only if `TESTS_REQUIRED=yes`; mandatory code-review + qa handoff, consolidated summary) |
| `/devteam:design` | ui-ux-designer | Design system, UX flows, visual decisions |
| `/devteam:fix` | backend-developer¹ + frontend-developer¹ + mobile-developer¹ → test-specialist² | Fixing a bug (tests only if `TESTS_REQUIRED=yes`) |
| `/devteam:refactor` | software-architect → backend/frontend-test-specialist² + database-specialist¹ + security-specialist → backend-developer¹ + frontend-developer¹ → code-reviewer + qa-specialist | Structured refactoring; test-first coverage only if `TESTS_REQUIRED=yes` (else refactor without a test net), dependency mapping, consolidated plan, ordered commit blocks |
| `/devteam:architect` | software-architect | Architecture decisions, ADRs, trade-offs; specialized handling for refactor/design/mobile/fullstack/review scope requests routes through the matching `/devteam:<scope>` command, otherwise built-in behavior (new project, bug fix, security, inherited, maintenance) |
| `/devteam:adr` | runs `scripts/new-adr.sh` → software-architect fills template | Creating a new Architecture Decision Record |
| `/devteam:audit` | explore → backend-developer + frontend-developer + security-specialist + devops-specialist → backend-test-specialist² + frontend-test-specialist² | Deep analysis of a module/area — silent bugs, test gaps, edge cases, security, infra, and improvement plan; saves report to `docs/audit/` |
| `/devteam:review` | code-reviewer + software-architect + security-specialist + database¹ + mobile-developer¹ | Code review before merge; with no args, asks a dynamic quiz (current branch / other local branch / PR link / other) to pick the target |
| `/devteam:qa` | qa-specialist | Validating feature behavior and acceptance criteria |
| `/devteam:security` | security-specialist + software-architect | Security audit or vulnerability analysis |
| `/devteam:dba` | database-specialist + software-architect | Schema design, query optimization, migrations |
| `/devteam:devops` | devops-specialist | CI/CD, Docker, infra, deploy scripts |
| `/devteam:tester` | backend-test-specialist + frontend-test-specialist¹ + mobile-developer¹ | Writing or updating tests only |
| `/devteam:docs` | technical-writer | Docs, changelogs, runbooks, release notes |
| `/devteam:pr` | technical-writer (+ code-reviewer if `review` in args) | Drafting and creating a pull request; after creating (which pushes), loads `skills/shared/github-actions/SKILL.md` to watch Actions and auto-fix failures |
| `/devteam:commit` | reads staged changes, groups by layer, writes and runs commits | Committing changes with the project's or Conventional Commits pattern |
| `/devteam:learn` | technical-writer + software-architect¹ | Consolidating session decisions, patterns, and discoveries into docs, wiki, and ADRs |
| `/devteam:update` | runs `update.sh` (which delegates freshness check to `hooks/pre-tool-use/01-check-updates.sh`) | Checking for and applying dev-team-agents updates |
| `/devteam:symlinks` | runs `fix-symlinks.sh` (detects OS, repairs materialized `.claude/` links, guides the OS fix on exit 3) | Diagnosing and repairing broken dev-team-agents symlinks (Windows without native symlink support) |

¹ conditional — spawned only when the task context involves that scope.
² test-gated — spawned only when the project's `CLAUDE.md` `## dev-team-agents` section has `TESTS_REQUIRED=yes` (or the key is absent — default to running tests). If `TESTS_REQUIRED=no`, the test phase is skipped entirely.

> **Exception — commands that do NOT load `current-context`:** `/devteam:commit` (operates on the staging area, not a branch scope), `/devteam:update` (operates on the local installation), `/devteam:symlinks` (operates on the local installation), and `/devteam:learn` (operates on session evidence, not a branch scope). All omit `current-context` by design.

> **Exception — commands that do NOT require Plan Gate:** `/devteam:review` (read-only by design — reads the diff and delegates, does not modify files). `/devteam:update` and `/devteam:symlinks` are thin script-runners over `update.sh` / `fix-symlinks.sh` (both with their own interactive guardrails) and likewise run without a Plan Gate.

**Code Reviewer roles:** `code-reviewer` is the entry-point router for `/devteam:review`. It reads the diff, classifies the change scope, and delegates to `backend-test-specialist` or `frontend-test-specialist` as needed. The router does not duplicate the structural checks of the specialists — it coordinates and synthesizes their outputs into a single review verdict.

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
├── commands/        ← devteam slash commands (installed to .claude/commands/devteam/, invoked as /devteam:<name>)
├── templates/       ← document templates (plan, backlog, ADR, etc.)
├── docs/            ← repository-level reports and internal docs (NOT installed to user projects)
│   ├── agents.md        ← canonical agent reference
│   ├── installation.md  ← installation and advanced options guide
│   └── reports/         ← audit reports and fingerprint index
├── scripts/         ← install.sh, update.sh, new-adr.sh, graphify-refresh.sh, fix-symlinks.sh
│   └── hooks/       ← pre-tool-use.sh, stop.sh (dispatchers) + pre-tool-use/, stop/ (sub-scripts)
├── README.md
├── README.pt-BR.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── LICENSE
└── CLAUDE.md        ← this file
```

---

## User Preferences

→ See [`CLAUDE-md/preferences.md`](CLAUDE-md/preferences.md) for the preferences.json schema, language rules, and migration notes.

---

## Notification System

→ See [`CLAUDE-md/notifications.md`](CLAUDE-md/notifications.md) for format, types, channels, suppression, and context window estimation.

---

## User Data Directory

→ See [`CLAUDE-md/user-data.md`](CLAUDE-md/user-data.md) for directory structure, file purposes, gitignore rules, and package exclusions.

---

## Versioning

→ See [`CLAUDE-md/versioning.md`](CLAUDE-md/versioning.md) for the semantic versioning policy.

---

## Immutability Contract

These files are installed at a fixed path (`.dev-team-agents/`) and replaced entirely on every update. Users are warned not to modify them directly. When authoring changes:

- Maintain backward compatibility where possible
- If a breaking change is unavoidable, document it in the PR description and README release notes
- Never remove a skill or agent without a deprecation cycle (one minor version with a warning)

---

## Agent Memory System

Three mechanisms work together to minimize context loss between sessions. All three are enforced automatically after installation.

### Session Summary Rule

**At the end of any session where files were created or modified**, write a new entry at the top of `.dev-team-agents/user-data/session-summary.md`:

```
## YYYY-MM-DD HH:MM:SS | [brief task title]
**Done**: what was implemented or changed

**Decisions**: key choices made and why

**Next**: what remains or is recommended next

---
```

- One entry per session per task; append to the same entry if continuing the same task the same day
- **Always write in English** — even if the conversation with the user is in another language
- This file is read at agent startup via `skills/shared/project-context/SKILL.md`
- The `Stop` dispatcher (`scripts/hooks/stop.sh`) runs `scripts/hooks/stop/01-session-summary.sh`, which detects when this is missing and prompts you

**Multi-agent sessions**: when multiple agents work in the same session, each agent **appends** its contribution to today's entry — never overwrites. Use the agent name as a sub-heading:

```
## YYYY-MM-DD HH:MM:SS | [task title]
### backend-developer
**Done**: ...

**Decisions**: ...

**Next**: ...

### frontend-developer
**Done**: ...

**Decisions**: ...

**Next**: ...

---
```

If no entry exists for today yet, create one with the agent name as the first sub-heading.

**Rotation**: after writing a new entry, trim entries older than 30 days from the file. Keep the file under 30 entries total.

### ADR Trigger Rule

Write an ADR when a decision is:
- Hard to reverse (database engine, auth strategy, API design)
- Affects multiple components or agents
- Has non-obvious reasoning that future agents would question

**Create an ADR by running:**

```bash
bash .dev-team-agents/scripts/new-adr.sh "title of the decision"
```

The script auto-numbers the file and places it in `docs/development/adrs/`. Fill in the generated template and change the status from `Proposed` to `Accepted`.

### Stop Hook (Automated Enforcement)

`install.sh` registers `scripts/hooks/stop.sh` as the `Stop` dispatcher in `.claude/settings.json`. This dispatcher runs all sub-scripts in `scripts/hooks/stop/` in order, including `01-session-summary.sh`, which:

- Runs automatically each time Claude finishes responding
- Detects uncommitted changes **or commits made today** without a session-summary entry for today
- Outputs a structured reminder visible to Claude on the next turn, which then writes the summary

No manual setup is required — the installer handles registration.

### Stop Hook Sub-script Convention

Sub-scripts in `scripts/hooks/stop/` are executed in alphabetical order by filename. The numeric prefix controls execution order:

| Prefix | Reserved for | Current scripts |
|--------|-------------|-----------------|
| `01-` | State detection and collection (session context) | `01-session-summary.sh` |
| `02-` | Repository integrity checks | `02-orphan-skill-scan.sh` |
| `03-` | Static validation | `03-agent-lint.sh` |
| `04-` | User-facing notifications | `04-notifier.sh` |
| `05-` | External reporting (telemetry) | `05-telemetry.sh` |
| `99-` | Final/cleanup tasks | _(reserved, unused)_ |

Each sub-script must:
- Accept `--quiet` flag and suppress output when OK
- Exit with code `0` when nothing is wrong
- Exit non-zero only when action is required from the user

Prefix `00-` is reserved for future preconditions. When adding a new sub-script, choose the correct tier and pick a number within that tier (e.g., `02-new-check.sh`).

### Hook Files Map

| Event | File | Dispatcher | Purpose |
|-------|------|-----------|---------|
| `SessionStart` | `scripts/hooks/session-start.sh` | — | Stale config detection, missing prefs |
| `PreToolUse` | `scripts/hooks/pre-tool-use.sh` | Dispatcher | Update checks, context cache |
| `PreCompact` | `scripts/hooks/pre-compact.sh` | — | Session summary before context compaction |
| `Stop` | `scripts/hooks/stop.sh` | Dispatcher | Session summary, orphan scans, notifications |

---

## Commit Rule

When making a git commit for any task:

1. **Load `skills/shared/conventional-commits/SKILL.md`** before writing the commit message
2. **Defer to the project's own pattern first**: run `git log --oneline -10` and check whether the existing history follows Conventional Commits or a different format (e.g., GitHub-style `[feature]`, plain imperative, Jira ticket prefix). If a project-specific pattern is clearly in use, follow it instead.
3. **Never include Claude attribution**: no `Co-Authored-By: Claude`, no `🤖 Generated with Claude Code`, no AI tooling references in commit messages, PR titles, or PR bodies.

---

## Push & CI Monitoring Rule

When the user **explicitly asks to push** (a commit alone does not count) and the GitHub CLI is configured (`gh auth status` succeeds):

1. **Load `skills/shared/github-actions/SKILL.md`** and follow it.
2. If the repo has workflow files (`.github/workflows/*`), watch the triggered run and, on failure, run the capped **diagnose → fix → re-push** loop (max 3 attempts), reporting a **one-line summary** to the user each cycle.
3. Stop and hand back to the user when the run is green, the 3-attempt cap is reached, or the failure is not auto-fixable (missing secret, infra, required approval). Never disable/skip a workflow or weaken a test to force green.

If `gh` is not configured or there are no workflow files, push normally and skip the monitoring loop.

---

## Orphan Skill Self-Check Rule

**After any session where files in `agents/` or `skills/` were created or modified**, run:

```bash
bash helpers/orphan-skill-scan.sh
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

This principle must be reinforced in every agent and every command.
