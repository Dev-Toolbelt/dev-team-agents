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

**Coding agents** (`backend-developer`, `frontend-developer`, `mobile-developer`, `database-specialist`, `devops-specialist`, `ui-ux-designer`, `backend-test-specialist`, `frontend-test-specialist`) must also include a **`## Worktree Isolation`** section using the canonical session-file pattern:

1. Read `.claude/.worktree-session` — if it exists, follow the stored decision silently:
   - `worktree=no branch=<b>` → operate on branch `<b>`; do not load the worktree skill
   - `worktree=yes branch=<b>` → load `skills/shared/worktree/SKILL.md` using branch `<b>`
2. If absent, ask the user once:
   - **yes** → ask for the base branch (default: current branch), write `worktree=yes branch=<base>`, load `skills/shared/worktree/SKILL.md`
   - **no** → get current branch, ask for a new branch name (suggest `<context>/<brief-title>`), run `git checkout -b <branch-name>`, write `worktree=no branch=<branch-name>`

This ensures multi-agent workflows ask the worktree question exactly once.

### Skills (`skills/**/*.md`)

- Follow [agentskills.io specification](https://agentskills.io/specification)
- Frontmatter: `name`, `description`
  > Note: `allowed-tools:` is **not** a standard frontmatter key for skills in this repo. Use only `name` and `description`. The `allowed-tools:` key in `skills/shared/worktree/SKILL.md` was an experiment and has been removed.
- Body is current rules only — no change history, no "was removed / replaced by" narratives
- Max ~500 lines; move long reference material to `references/` subdirectory
- Prefer tables and bullets over prose

#### Contradiction Guard

All agents automatically enforce the Contradiction Guard defined in `skills/shared/project-context/SKILL.md`. When a user request conflicts with an established rule (in `CLAUDE.md`, ADRs, architecture docs, or sprint scope), the agent must flag the conflict, cite the source, and ask for explicit confirmation before proceeding.

#### Wiki Knowledge Base

Every project gets a wiki at `.claude/docs/wiki/`. Agents write entries after completing tasks that reveal non-obvious domain knowledge — gotchas, multi-layer flows, behavioral quirks that aren't derivable from reading code. The `setup-assistant` creates `wiki/README.md` on FIRST_RUN. See `skills/shared/docs-sync/SKILL.md` for the wiki entry format, domain folder rules, and update protocol.

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
| `agent-creator` | `.claude/skills/agent-creator/SKILL.md` | `/agent-creator` or "create/update an agent" |
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
| `/devteam:plan` | software-architect + product-analyst + database-specialist + backend¹ + frontend¹ + devops¹ | Planning a feature, system, or change |
| `/devteam:backend` | backend-developer + database-specialist¹ → backend-test-specialist | Implementing backend changes |
| `/devteam:frontend` | frontend-developer + ui-ux-designer¹ → frontend-test-specialist | Implementing frontend changes |
| `/devteam:fullstack` | backend + frontend + database¹ + ui-ux¹ → both test-specialists | Implementing full-stack changes |
| `/devteam:mobile` | mobile-developer + ui-ux-designer¹ | Implementing mobile features (React Native, Expo, Flutter, native iOS/Android) |
| `/devteam:design` | ui-ux-designer | Design system, UX flows, visual decisions |
| `/devteam:fix` | backend-developer¹ + frontend-developer¹ + mobile-developer¹ → test-specialist¹ | Fixing a bug |
| `/devteam:refactor` | software-architect → backend/frontend-test-specialist + database-specialist¹ + security-specialist → backend-developer¹ + frontend-developer¹ → code-reviewer + qa-specialist | Structured refactoring with test-first coverage, dependency mapping, consolidated plan, and ordered commit blocks (tests → refactoring) |
| `/devteam:architect` | software-architect | Architecture decisions, ADRs, trade-offs |
| `/devteam:adr` | runs `scripts/new-adr.sh` → software-architect fills template | Creating a new Architecture Decision Record |
| `/devteam:review` | code-reviewer + software-architect + security-specialist + database¹ + mobile-developer¹ | Code review before merge |
| `/devteam:qa` | qa-specialist | Validating feature behavior and acceptance criteria |
| `/devteam:security` | security-specialist + software-architect | Security audit or vulnerability analysis |
| `/devteam:dba` | database-specialist + software-architect | Schema design, query optimization, migrations |
| `/devteam:devops` | devops-specialist | CI/CD, Docker, infra, deploy scripts |
| `/devteam:tester` | backend-test-specialist + frontend-test-specialist¹ + mobile-developer¹ | Writing or updating tests only |
| `/devteam:docs` | technical-writer | Docs, changelogs, runbooks, release notes |
| `/devteam:pr` | technical-writer (+ code-reviewer if `review` in args) | Drafting and creating a pull request |
| `/devteam:workflow-new` | follows `workflows/new-project.md` | Starting a new project |
| `/devteam:workflow-maintenance` | follows `workflows/maintenance.md` | Maintenance / feature evolution |
| `/devteam:workflow-bugfix` | follows `workflows/bug-fix.md` | Full bug-fix workflow |
| `/devteam:workflow-inherited` | follows `workflows/inherited-project.md` | Taking over an existing project |
| `/devteam:workflow-security-patch` | follows `workflows/security-patch.md` | Applying a security patch |
| `/devteam:commit` | reads staged changes, groups by layer, writes and runs commits | Committing changes with the project's or Conventional Commits pattern |
| `/devteam:update` | runs `check-updates.sh` + `update.sh` | Checking for and applying dev-team-agents updates |

¹ conditional — spawned only when the task context involves that scope.

> **Exception — commands that do NOT load `current-context`:** `/devteam:commit` (operates on the staging area, not a branch scope) and `/devteam:update` (operates on the local installation). Both omit `current-context` by design.

**Code Reviewer roles:** `code-reviewer` is the entry-point router for `/devteam:review`. It reads the diff, classifies the change scope, and delegates to `backend-test-specialist` or `frontend-test-specialist` as needed. The router does not duplicate the structural checks of the specialists — it coordinates and synthesizes their outputs into a single review verdict.

### Workflows (`workflows/*.md`)

- Each step must include:
  1. The prompt the user gives to Claude
  2. What the agent produces
  3. A note that the agent will present a Plan before executing
- Name files: `<context>.md` (e.g., `new-project.md`, `bug-fix.md`)
- Existing workflows: `new-project.md`, `bug-fix.md`, `maintenance.md`, `inherited-project.md`, `security-patch.md`, `fullstack.md`, `refactor.md`, `review.md`

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
├── workflows/       ← step-by-step workflow guides
├── templates/       ← document templates (plan, backlog, ADR, etc.)
├── docs/            ← repository-level reports and internal docs (NOT installed to user projects)
├── scripts/         ← install.sh, update.sh, new-adr.sh, graphify-refresh.sh
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

All user-level preferences are stored in `.claude/user-data/preferences.json` (gitignored). The file is created by `install.sh` on first install and validated/migrated by the health check.

### Schema

```json
{
  "language": "en",
  "context_window_percent_warning": 55,
  "context_window_percent_limit": 60,
  "suppress_notifications": false,
  "session_summary_max_days": 30,
  "session_summary_max_entries": 30,
  "docs_stale_after_days": 30,
  "auto_update": false,
  "update_check_interval_hours": 24,
  "transcript_multiplier": 1.8,
  "model_max_tokens": 200000
}
```

| Field | Default | Purpose |
|-------|---------|---------|
| `language` | `"en"` | BCP 47 language tag for agent conversation with the user |
| `context_window_percent_warning` | `55` | % at which agents emit a `warning` notification |
| `context_window_percent_limit` | `60` | % at which agents emit a `critical` notification |
| `suppress_notifications` | `false` | `false` / `true` / `["info"]` — suppress notification types |
| `session_summary_max_days` | `30` | Days before session-summary entries are trimmed |
| `session_summary_max_entries` | `30` | Maximum number of session-summary entries |
| `docs_stale_after_days` | `30` | Days before `project.md` and `session-summary.md` are flagged as stale |
| `auto_update` | `false` | Auto-update when a new version is detected |
| `update_check_interval_hours` | `24` | Hours between update checks |
| `transcript_multiplier` | `1.8` | Multiplier applied to transcript token count to estimate full context (compensates for system prompt + tools not stored in transcript) |
| `model_max_tokens` | `200000` | Maximum context window for the active model; used to compute context percentage from transcript tokens |

> **Fallback safety**: all scripts that read `preferences.json` use hardcoded defaults for every key. If the file is missing, malformed, or a key is removed, scripts fall back to the defaults above without error. Never leave a key out — the schema above is the authoritative default set.

### Language Rule

| Output | Language |
|--------|---------|
| Documents (ADRs, session-summary, changelogs, code comments) | **Always English** |
| Plans presented for user approval | **`language` field from `preferences.json`** — plans are conversation items, not documents |
| Conversation with the user (responses, questions, notifications) | **`language` field from `preferences.json`** — fallback to English |

### Migration

The legacy `.auto-update` flag file is automatically migrated to `preferences.json → auto_update` by `install.sh` and the health check.

---

## Notification System

Agents and shell hooks emit structured notifications using the DEV TEAM AGENTS format.

### Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 {icon}  DEV TEAM AGENTS  {icon}
 {message in the user's language}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Types

| Type | Icon | When to use |
|------|------|-------------|
| `info` | ℹ️ | Tips, suggestions, best practices |
| `warning` | ⚠️ | Context approaching limit, stale config, missing prefs |
| `critical` | 🚨 | Context at or beyond limit, broken installation |

### Channels

| Hook | Notifications |
|------|--------------|
| `session-start.sh` | Persistent state: missing `preferences.json`, stale docs |
| `stop/04-notifier.sh` | Session progress: context window warnings, tip of session |

### Suppression

Set `suppress_notifications` in `preferences.json`:
- `false` — show all
- `true` — suppress all
- `["info"]` — suppress only the listed types

### Context Window Estimation

`stop/04-notifier.sh` estimates context usage using two strategies (in order of preference):

1. **Transcript-based** (primary): reads `transcript_path` from the Stop hook payload, sums `input_tokens + output_tokens` across all turns, then applies `transcript_multiplier` (default `1.8`) to compensate for system prompt, tools, and memory not stored in the transcript. Result is compared to `model_max_tokens`.
2. **Turn-count heuristic** (fallback): fires when the transcript path is unavailable. Calibrates `100% ≈ 45 turns` and scales linearly. Less accurate for content-heavy sessions.

> **Limitation**: the actual context percentage (as shown by `/context`) is not accessible from bash hooks. The transcript-based estimate covers the conversation messages portion (~55% of total) and approximates the rest via the multiplier. Adjust `transcript_multiplier` in `preferences.json` if notifications fire too early or too late for your typical session profile.

### Tip of Session

`stop/04-notifier.sh` emits one `ℹ️ info` tip per session, indexed by `(day_of_month - 1) % 15`. 15 tips are defined inline in the script. Translations are provided for `pt-BR` and `es`; all other languages fall back to English.

### Stop Sub-script Convention (updated)

| Prefix | Reserved for | Current scripts |
|--------|-------------|-----------------|
| `01-` | State detection and collection | `01-session-summary.sh` |
| `02-` | Repository integrity checks | `02-orphan-skill-scan.sh` |
| `03-` | Static validation | `03-agent-lint.sh` |
| `04-` | User-facing notifications | `04-notifier.sh` |
| `99-` | Final/cleanup tasks | _(reserved, unused)_ |

---

## User Data Directory

When installed in a project, the installer creates two sibling directories under `.claude/`:

| Directory | Purpose |
|-----------|---------|
| `.claude/dev-team-agents/` | Package files — replaced entirely on every update |
| `.claude/user-data/` | User state and config — **never touched by the installer** |

Files in `user-data/`:
- `preferences.json` — user preferences (language, thresholds, notifications) (**gitignored** by installer)
- `session-summary.md` — per-session notes written by agents (**gitignored** by installer)
- `.installed-version` — current installed version tag (**gitignored** by installer)
- `.last-update-check` — Unix timestamp of last update check (**gitignored** by installer)
- `.session-id` — current session ID written by session-start hook (**gitignored** by installer)
- `.notifier-state` — notifier turn counter and tip-shown flag (**gitignored** by installer)
- `graphify.json` — Graphify config (created by `graphify-setup`; should be committed)

Other directories under `.claude/` created by agents:
- `.claude/docs/audit/` — project audit reports generated by `setup-assistant` on first run and on health checks. Versioned by default; add to `.gitignore` only if the team prefers not to track audit snapshots.

`install.sh` adds `.claude/user-data/` (entire directory) and `!.claude/user-data/graphify.json` (exception) to `.gitignore` — this ignores all user-data files except `graphify.json`. It also adds `.claude/.worktree-session` to `.gitignore`. Projects with the old per-file entries will be migrated automatically by the health check or next installer run.

**Rule:** any file that must survive an update must live in `.claude/user-data/`, not inside `.claude/dev-team-agents/`. Never store user config or state inside the package directory.

**Package exclusions:** The following are stripped from the extracted tarball before it is placed in the project:

| Stripped path | Mechanism | Reason |
|---------------|-----------|--------|
| `CLAUDE.md` | allowlist (not in `KEEP_ROOT`) | Authoring rules for this repo — not for end-users |
| `README.md` | allowlist (not in `KEEP_ROOT`) | Replaced by the installed package's own README if present |
| `README.pt-BR.md` | allowlist (not in `KEEP_ROOT`) | Same as README.md |
| `CHANGELOG.md` | allowlist (not in `KEEP_ROOT`) | Release history for this repo — not for user projects |
| `CONTRIBUTING.md` | allowlist (not in `KEEP_ROOT`) | Contribution guide for this repo — not for user projects |
| `LICENSE` | allowlist (not in `KEEP_ROOT`) | Repo license file — not for user projects |
| `SECURITY.md` | allowlist (not in `KEEP_ROOT`) | Vulnerability disclosure policy — not for user projects |
| `docs/` | allowlist (not in `KEEP_ROOT`) | Repository-level reports and internal docs irrelevant to users |
| `.gitignore` | explicit `rm -f` (dotfile strip) | Repo-level gitignore — not for user projects |
| `.claude/` | explicit `rm -rf` (dotfile strip) | Repo-level Claude config — not for user projects |
| `.github/` | explicit `rm -rf` (dotfile strip) | Repo-level GitHub config (templates, CODEOWNERS) — not for user projects |
| `scripts/install.sh` | explicit `rm -f` | Accessed exclusively via `curl` — never bundled |
| `scripts/orphan-skill-scan.sh` | explicit `rm -f` | Development tool for this repo — not relevant to user projects |
| `scripts/agent-lint.sh` | explicit `rm -f` | Development tool for this repo — not relevant to user projects |

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

**At the end of any session where files were created or modified**, write a new entry at the top of `.claude/user-data/session-summary.md`:

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
bash .claude/dev-team-agents/scripts/new-adr.sh "title of the decision"
```

The script auto-numbers the file and places it in `.claude/docs/development/adrs/`. Fill in the generated template and change the status from `Proposed` to `Accepted`.

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
| `99-` | Final/cleanup tasks | _(reserved, unused)_ |

Each sub-script must:
- Accept `--quiet` flag and suppress output when OK
- Exit with code `0` when nothing is wrong
- Exit non-zero only when action is required from the user

Prefix `00-` is reserved for future preconditions. When adding a new sub-script, choose the correct tier and pick a number within that tier (e.g., `02-new-check.sh`).

---

## Commit Rule

When making a git commit for any task:

1. **Load `skills/shared/conventional-commits/SKILL.md`** before writing the commit message
2. **Defer to the project's own pattern first**: run `git log --oneline -10` and check whether the existing history follows Conventional Commits or a different format (e.g., GitHub-style `[feature]`, plain imperative, Jira ticket prefix). If a project-specific pattern is clearly in use, follow it instead.
3. **Never include Claude attribution**: no `Co-Authored-By: Claude`, no `🤖 Generated with Claude Code`, no AI tooling references in commit messages, PR titles, or PR bodies.

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
