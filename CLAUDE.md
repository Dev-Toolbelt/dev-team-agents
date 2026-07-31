# CLAUDE.md — dev-team-agents

Instructions for working on this repository. These rules apply to Claude when authoring or modifying agents, skills, scripts, and documentation inside `dev-team-agents`.

---

## What This Repo Is

**Multi-agent development harness** — a harness for organizing AI agents in software development. Not just a bundle of agents: it is the layer that governs how those agents plan, execute, test, review, and record their work.

Stack-agnostic, project-aware. Installed at the project level (`.dev-team-agents/`) — not globally.

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

1. Present a plan using the canonical format in `templates/plan-template.md` (installed projects: `.dev-team-agents/templates/plan-template.md`)
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

- Frontmatter: `name`, `description`, `tier`, `model` — all four are required and enforced by `helpers/agent-lint.sh` (`REQUIRED_FIELDS`), which runs in CI and from the `Stop` hook (`scripts/hooks/stop/03-agent-lint.sh`). A fifth key, `effort:`, is present **only** on agents whose tier defines one in `tiers.json` (today: `repetitive`); the lint fails both on a missing one and on an extra one
- **`tier:` is the source of truth; `model:` is a checked mirror of it.** `scripts/lib/tiers.json` is the canonical tier → model map (it also carries the per-provider `effort` value where the provider has one). The render engine resolves the tier to a provider-specific model id for opencode and Codex. Claude Code is the identity case — its agents are symlinked from source and never pass through the renderer, so it cannot be handed a resolved model at install time; it reads `model:` from the frontmatter instead. That key therefore holds **exactly** `tiers.json[<tier>].claude` and nothing else. To change a model, edit `tiers.json` and re-run the mirror; never hand-edit `model:` to a different value — `agent-lint.sh` fails on any divergence between `tiers.json`, `model:`, and the run-banner row.
- **The `claude` column holds aliases** (`opus` / `sonnet` / `haiku`), not pinned model ids. Claude Code resolves an alias to the current model of that family, so the column does not go stale on a model launch. Pinned ids did exactly that, which is why they were replaced.
- **No `tools:` key**, and therefore no tools-order rule. Tool availability is provider-native; the renderer rewrites tool names per provider from `scripts/lib/tool-map.json`.
- Valid `tier:` values — any other value fails the lint:

| Tier | `claude` model | `claude` effort | Use for |
|------|----------------|-----------------|---------|
| `reasoning` | `opus` | inherits session | architecture, planning, refactoring, security analysis, onboarding decisions |
| `backend-exec` | `sonnet` | inherits session | backend implementation, backend review, code review, database, devops, qa, mobile, backend tests |
| `frontend` | `sonnet` | inherits session | frontend implementation, frontend review, frontend tests, ui/ux design |
| `repetitive` | `haiku` | `low` | doc generation, changelogs, release notes, boilerplate, high-volume low-judgment tasks |

> **Effort is set on one tier only, on purpose.** Claude Code supports a per-subagent `effort:` key, but it **overrides the session's level** — setting it on every tier would silently undo a user who lowered effort for cost or latency. `repetitive` is bounded low-judgment work where `low` is an unambiguous win; everything else inherits. Do not add an effort to another tier without a specific reason to override the user.

> `repetitive` is the only tier on Haiku, and Haiku's context window is 200K against 1M on the others. Keep that tier for work that is genuinely low-judgment and bounded — it currently holds `technical-writer` alone. Test authoring is **not** low-judgment: `backend-test-specialist` sits in `backend-exec`, matching `frontend-test-specialist` in `frontend`. Do not move a test agent to `repetitive`.

- Every agent must include: **Foundational Rule** (load context first) + **Immutability Warning** + a **`## Model Identity`** section carrying the `<!-- run-banner -->` block (see the Run Banner rule below)
- Stack-agnostic: no hardcoded framework, language, or tool references in agent core behavior
- No plain-text `(yes/no)` prompts in the body — `agent-lint.sh` fails on them; use `AskUserQuestion` (see the Quiz-first Rule below)
- Max ~200 lines of content per agent; move reference material to skills. `helpers/size-limits.sh` enforces 205 — the extra 5 lines are the fixed-size run-banner block every agent carries, not content budget. Do not raise that ceiling again to make a long agent fit.

**Run Banner Rule.** Every agent prints a model-identity table — agent, tier, model, effort — as the first thing in its first response, on every provider. The rule and the table format live in `skills/shared/model-identity/SKILL.md`; each agent body carries only its own values, in a `<!-- run-banner -->` block inside `## Model Identity`:

```markdown
<!-- run-banner -->
| Agent | Tier | Model | Effort |
|---|---|---|---|
| `backend-developer` | `backend-exec` | `sonnet` | `—` |
```

The source copy holds Claude's values because Claude is the identity case; `render_run_banner()` in `scripts/lib/render_provider.py` rewrites the **Model** and **Effort** cells for opencode and Codex (Agent and Tier are provider-agnostic and pass through). Resolving the banner at render time — rather than having the agent read `tiers.json` and sniff the provider at runtime — is deliberate: it costs no tool call per invocation, and it cannot report the wrong provider in a project that has more than one installed.

**Coding agents** (`backend-developer`, `frontend-developer`, `mobile-developer`, `database-specialist`, `devops-specialist`, `ui-ux-designer`, `backend-test-specialist`, `frontend-test-specialist`) must also include a **`## Worktree Isolation`** section. That section **delegates** — it points at the canonical cascade below and at `skills/shared/worktree/SKILL.md` for the `worktree=yes` path, in two or three lines. **Do not restate the cascade in an agent body.** It used to be inlined in all eight agents (~15 lines each) and drifted between them; the cascade has exactly one copy, and it is here.

**Canonical worktree decision cascade** (resolve top-down, stop at the first match):

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
- **`name` must equal the skill's directory basename** (`skills/testing/load-testing/SKILL.md` → `name: load-testing`), and must be **unique across all categories**. Both are enforced by `helpers/agent-lint.sh`. The divergence is load-bearing: the render engine resolves opencode skills by frontmatter `name` while the installers symlink by directory, and agent bodies plus `helpers/orphan-skill-scan.sh` reference skills by bare name
- Keep `description` within **95 characters** — it feeds the always-loaded skill index. `agent-lint.sh` reports over-budget descriptions as a non-blocking warning today (`SKILL_DESC_STRICT=false`)
- Body is current rules only — no change history, no "was removed / replaced by" narratives
- Max ~500 lines (SKILL.md only; `references/` is exempt); move long reference material to `references/` subdirectory
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

#### Canonical Rule Homes — Delegate, Never Restate

A rule that applies to more than one agent lives in exactly **one** skill. Agents load that skill and reference the rule by name; they must not paraphrase or inline it. Every entry below was previously duplicated across agent bodies and had already drifted into divergent variants before it was consolidated.

| Rule | Canonical home | Agents must |
|------|---------------|-------------|
| Task Closure Rule — after finishing a task, patch the docs the work triggers, in parallel with the commit | `skills/shared/docs-sync/SKILL.md` § Task Closure Rule | Load docs-sync and reference the rule; write no closing directive of their own |
| Foundational Rule context list (12 items) | `skills/shared/project-context/SKILL.md` | Delegate in one line, then add only genuinely role-specific loads |
| Project rules override these base standards | `skills/shared/project-context/SKILL.md` | Say nothing — loading the skill is the enforcement |
| SonarQube detection signals | `skills/devops/sonarqube/SKILL.md` (detection table) | Route to the table; never restate a subset of the signals |
| Comments policy, including TODO/FIXME handling | `skills/shared/comments-policy/SKILL.md` (Conditional Section Loading table) | Load it; the routing parenthetical belongs to the skill |
| Worktree decision cascade | `CLAUDE.md` → *Canonical worktree decision cascade* + `skills/shared/worktree/SKILL.md` | Delegate from `## Worktree Isolation` (see Agents above) |
| Layered-commit table and commit message format | `skills/shared/conventional-commits/SKILL.md` | Load it; commands must not carry a second copy of the table |
| Plan document format | `templates/plan-template.md`, loaded via `skills/shared/plan-mode/SKILL.md` | Load the template; never ship a second rendering of the format |
| Which tests to execute when finishing a task — scoped to the touched code, full suite only on explicit user request | `skills/shared/scoped-test-execution/SKILL.md` | Load it and delegate; never restate the exception, and never add a second escalation criterion (suite speed, refactor width, shared code) |

When a duplicated rule is found, delete the copy — do not "reconcile" the two wordings.

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
| `agent-creator` | `.claude/skills/agent-creator/SKILL.md` — tracked in this repo, but `.claude/` is stripped from the package by `scripts/lib/strip-tarball.sh`, so it never reaches an installed project. Available to contributors working inside this repo only. | `/agent-creator` or "create/update an agent" |
| `review` | `agents/code-reviewer.md` | `/review`, `/review backend`, `/review frontend`, `/review both` |

**Command-level skills** — loaded by `commands/*.md` files rather than by agents directly:

| Skill | Used by |
|-------|---------|
| `current-context` | All `/devteam:*` commands — detects branch/worktree state before executing |
| `spawn-classifier` | `/devteam:plan` and multi-agent commands — decides conditional agent spawn |

#### User-Invocable Commands (`commands/*.md`)

Slash commands installed to `.claude/commands/devteam/` and invoked as `/devteam:<name>` (e.g. `/devteam:plan`). This keeps all devteam commands namespaced and separate from any project-specific commands. Each command spawns agents via the Task tool and restricts scope to the current git branch/worktree unless overridden by the user.

Commands are subject to the same authoring discipline as agents: **max ~200 lines each**, enforced by `helpers/size-limits.sh`, and the **Quiz-first Rule** below, enforced by `helpers/agent-lint.sh`. A command is a thin orchestration wrapper — it must never restate a skill it already loads.

| Command | Agents invoked | Use when… |
|---------|---------------|-----------|
| `/devteam:setup` | setup-assistant | Onboarding a project into dev-team-agents — detects `FIRST_RUN` vs `REFRESH` (`docs/project.md` present), then delegates the full setup flow |
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
| `/devteam:review` | code-reviewer + software-architect + security-specialist + qa-specialist + database¹ + mobile-developer¹ | Code review before merge; with no args, asks a dynamic quiz (current branch / other local branch / PR link / other) to pick the target |
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
| `/devteam:health-check` | loads `skills/shared/setup-health-check/SKILL.md` and `skills/shared/output-format/SKILL.md`; no agents spawned | Diagnosing an installation — detects the active provider (`claude` / `opencode` / `codex`), runs the 9 check categories (symlinks, scripts, user data, provider config, graphify, CLAUDE.md/AGENTS.md, .gitignore, preferences, notifier) and applies auto-fixes |

¹ conditional — spawned only when the task context involves that scope.
² test-gated — spawned only when the project's `CLAUDE.md` `## dev-team-agents` section has `TESTS_REQUIRED=yes` (or the key is absent — default to running tests). If `TESTS_REQUIRED=no`, the test phase is skipped entirely.

> **Exception — commands that do NOT load `current-context`:** `/devteam:commit` (operates on the staging area, not a branch scope), `/devteam:update` (operates on the local installation), `/devteam:health-check` (operates on the local installation), and `/devteam:learn` (operates on session evidence, not a branch scope). These four are the complete list — verify with `grep -L current-context commands/*.md`. `/devteam:symlinks` does reference `current-context`, explicitly to record that it does not apply.

> **Exception — commands that do NOT require Plan Gate:** the canonical per-command `plan_gate` value lives in `scripts/lib/commands.json` (`required` / `conditional` / `opt_out`). Only `/devteam:update`, `/devteam:symlinks`, and `/devteam:health-check` are `opt_out` — thin script/skill runners with their own interactive guardrails. `/devteam:review` is `conditional` and read-only by design (it reads the diff and delegates, and its body carries no plan-gate step), so in practice it executes directly.

**Code Reviewer roles:** `code-reviewer` is the entry-point router for `/devteam:review`. Before anything else it loads `skills/shared/review-router/SKILL.md`, which classifies the git diff as `BACKEND`, `FRONTEND`, or `BOTH`. It then proceeds as `backend-reviewer` (`BACKEND`), as `frontend-reviewer` (`FRONTEND`), or emits the parallel routing message and stops (`BOTH`). An explicit argument (`/review backend`, `/review frontend`, `/review both`) overrides classification. The router does not duplicate the structural checks of the specialists — it coordinates and synthesizes their outputs into a single review verdict.

### Templates (`templates/*.md`)

- Standalone, copy-paste ready
- No hardcoded project-specific values — use `[placeholders]`
- **Reference templates by their installed path** — `.dev-team-agents/templates/<name>.md`, the form `scripts/new-adr.sh` already uses. A bare `templates/<name>.md` resolves only inside this repository, not from the project root an agent actually runs in. `helpers/orphan-template-scan.sh` checks that references **resolve**, not merely that the filename is mentioned
- A skill named after a template does not make the two a pair. Wire a skill to a template only when the skill emits that exact document shape

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
│   ├── database/
│   ├── design/
│   ├── devops/      ← one skill per platform
│   ├── integrations/ ← platform/integration-specific reference skills
│   ├── legacy/      ← survival guides for legacy codebases (jquery)
│   ├── mobile/
│   ├── security/
│   ├── skill-creator/ ← user-invocable skill-authoring skill
│   ├── testing/
│   └── ui-libraries/ ← UI component library reference skills
├── commands/        ← devteam slash commands (installed to .claude/commands/devteam/, invoked as /devteam:<name>)
├── templates/       ← document templates: adr-template.md, plan-template.md, runbook-template.md
├── CLAUDE-md/       ← companion sections of this file (preferences, notifications, user-data, versioning)
├── docs/            ← repository-level reports and internal docs (NOT installed to user projects)
│   ├── agents.md · agents.pt-BR.md            ← canonical agent reference
│   ├── installation.md · installation.pt-BR.md ← installation and advanced options guide
│   ├── install-claude.md · install-codex.md · install-opencode.md ← per-provider install guides
│   ├── providers.md     ← provider matrix and tier → model id map
│   └── reports/         ← audit reports and fingerprint index
├── helpers/         ← DEV-ONLY authoring tools, never shipped (see "Two helpers directories" below)
│   ├── agent-lint.sh              ← agent frontmatter (name/description/tier/model) +
│   │                                model↔tiers.json↔run-banner drift + skill
│   │                                identity (name == dir, unique) + quiz-first
│   ├── size-limits.sh             ← agents 205 (200 content + 5 run-banner) · commands 200 · skills 500
│   ├── orphan-skill-scan.sh       ← repairs broken skill paths; never deletes
│   ├── orphan-template-scan.sh    ← template references must RESOLVE, not just be mentioned
│   └── archive-index.sh · check-fingerprint-uniqueness.sh ← report-index rotation and
│                                    global fingerprint uniqueness across live + archives
├── opencode/        ← opencode provider plugin source (plugin/dev-team-agents.ts); stripped at install,
│                      fetched on demand by install-opencode.sh / install-provider.sh
├── scripts/
│   ├── install.sh · update.sh · rollback.sh   ← install / update / rollback lifecycle
│   ├── install-provider.sh · install-opencode.sh · install-codex.sh ← multi-provider installers
│   ├── render-provider.sh         ← renders the canonical source into a provider-specific tree
│   ├── check-codex-compat.sh      ← lints rendered Codex output for forbidden terms
│   ├── migrate-to-root.sh         ← migrates .claude/dev-team-agents/ → .dev-team-agents/
│   ├── fix-symlinks.sh · check-updates.sh (shim) · new-adr.sh
│   ├── graphify-refresh.sh · validate-commit-msg.sh
│   ├── lib/         ← render-engine data and shared install logic
│   │   ├── tiers.json             ← CANONICAL tier → provider model id map (+ per-provider effort)
│   │   ├── commands.json · command-map.json · tool-map.json ← renderer metadata
│   │   ├── preferences-defaults.json ← defaults written into user-data/preferences.json
│   │   ├── render_provider.py     ← render engine
│   │   ├── strip-tarball.sh       ← single source of truth for the package strip rules
│   │   ├── installer-fetch.sh     ← shared ref-pinned download + payload verification
│   │   │                            (update.sh, rollback.sh, the auto-update hook path)
│   │   ├── telemetry-guard.sh     ← single fail-closed definition of _telemetry_enabled
│   │   └── ensure-claude-framework.sh
│   ├── helpers/     ← SHIPS and runs in user projects — telemetry-send.sh (called by install.sh, update.sh)
│   └── hooks/       ← session-start.sh, pre-compact.sh + pre-tool-use.sh, stop.sh (dispatchers)
│       ├── pre-tool-use/  ← PreToolUse sub-scripts
│       ├── stop/          ← Stop sub-scripts
│       │   └── tips/      ← notifier tip data, one file per locale
│       │                    (tips.en.txt · tips.pt-BR.txt · tips.es.txt)
│       └── lib/           ← shared hook logic, sourced not dispatched
│           ├── session-summary-detect.sh ← shared by pre-compact.sh and stop/01-
│           ├── touched-paths.sh          ← touched-path set computed once by stop.sh
│           └── update-check.sh           ← update-check engine behind pre-tool-use/01-
├── .github/         ← CI workflows, issue/PR templates, CODEOWNERS, scripts/ci/ — stripped at install
├── user-data/       ← runtime state of this repo's own self-install; gitignored and untracked
├── README.md
├── README.pt-BR.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── PRIVACY.md
├── LICENSE
└── CLAUDE.md        ← this file
```

**Two `helpers` directories — do not confuse them:**

| Path | Ships to user projects? | Purpose |
|------|------------------------|---------|
| `helpers/` (repo root) | **No** — `rm -rf` by `scripts/lib/strip-tarball.sh` | Dev-only authoring tools for this repo: linting, orphan scans, size limits, fingerprint index maintenance. Run them from the repo root, never from an installed `.dev-team-agents/`. |
| `scripts/helpers/` | **Yes** — inside the allowlisted `scripts/` tree | Runtime helpers used by the installed package. Currently `telemetry-send.sh`, invoked by `install.sh` and `update.sh` at `.dev-team-agents/scripts/helpers/telemetry-send.sh`. |

When a rule or script path references "helpers", state which of the two it means.

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

`install.sh` registers `scripts/hooks/stop.sh` as the `Stop` dispatcher in `.claude/settings.json`. This dispatcher runs every sub-script in `scripts/hooks/stop/` whose filename matches the naming convention, in order, including `01-session-summary.sh`, which:

- Runs automatically each time Claude finishes responding
- Detects uncommitted changes **or commits made today** without a session-summary entry for today
- Outputs a structured reminder visible to Claude on the next turn, which then writes the summary

No manual setup is required — the installer handles registration.

### Stop Hook Sub-script Convention

Sub-scripts in `scripts/hooks/stop/` are executed in alphabetical order by filename. The numeric prefix controls execution order:

| Prefix | Reserved for | Current scripts |
|--------|-------------|-----------------|
| `01-` | State detection and collection (session context) | `01-session-summary.sh` |
| `02-` | Repository integrity checks | `02-orphan-skill-scan.sh`, `02b-orphan-template-scan.sh` |
| `03-` | Static validation | `03-agent-lint.sh`, `03b-fingerprint-uniqueness.sh` |
| `04-` | User-facing notifications | `04-notifier.sh` |
| `05-` | External reporting (telemetry) | `05-telemetry.sh` |
| `99-` | Final/cleanup tasks | `99-graphify-refresh.sh`, `99b-archive-index.sh` |

Each sub-script must:
- **Match the filename pattern `NN-name.sh` or `NNx-name.sh`** — regex `^[0-9]{2}[a-z]?-[a-z0-9]([a-z0-9-]*[a-z0-9])?\.sh$`. The dispatcher **skips any file that does not match**, so a draft, a `.sh.bak`, or a `notes.sh` left in the directory is ignored instead of being auto-run on every Stop. Set `DEVTEAM_HOOK_DEBUG=1` to see what was run and what was skipped
- Accept `--quiet` flag and suppress output when OK
- Honour the dispatcher's `DEVTEAM_NO_CHANGES=1` fast path — a Stop with no staged/unstaged changes and no commits today must not trigger a full scan
- Reuse `DEVTEAM_TOUCHED_PATHS` / `DEVTEAM_TOUCHED_COMPUTED` (exported by `stop.sh` via `scripts/hooks/lib/touched-paths.sh`) instead of re-running `git status`/`git log`, while still working standalone when they are unset
- Exit with code `0` when nothing is wrong
- Exit non-zero only when action is required from the user

Prefix `00-` is reserved for future preconditions. When adding a new sub-script, choose the correct tier and pick a number within that tier (e.g. `02-new-check.sh`). When the tier's number is already taken and the new script must run adjacent to the existing one, append a **lowercase letter suffix** instead of claiming a new number — `02b-`, `02c-`, … — which sorts immediately after `02-` and keeps the tier boundaries intact.

Sub-scripts that call a `helpers/` tool (`03b-fingerprint-uniqueness.sh`, `99b-archive-index.sh`) must degrade silently when `helpers/` is absent — it is stripped from every installed project.

Data files may live under `scripts/hooks/stop/`: `tips/` holds the notifier's rotating tips as one file per locale (`tips.en.txt`, `tips.pt-BR.txt`, `tips.es.txt`, 15 lines each). Only the selected locale's file is read, and only after the once-per-day gate opens. They are not `.sh` and are never dispatched.

### PreToolUse Hook Sub-script Convention

Sub-scripts in `scripts/hooks/pre-tool-use/` are run by `scripts/hooks/pre-tool-use.sh`, which reads the hook JSON from stdin once and pipes the same payload to every sub-script in alphabetical order. The dispatcher propagates the first non-zero exit code.

| Prefix | Reserved for | Current scripts |
|--------|-------------|-----------------|
| `01-` | Installation freshness | `01-check-updates.sh` — thin orchestrator over `scripts/hooks/lib/update-check.sh`; TTL-based update check, auto-updates when the `.auto-update` flag exists |
| `02-` | Context injection and reporting | `02-graphify-hint.sh` — injects a graph hint on Glob/Grep when `graphify-out/graph.json` exists; `02b-telemetry.sh` — queues agent-spawn and `/devteam:*` command events |

> One script per bare number. `02-graphify-hint.sh` keeps `02-` because it is referenced externally; the telemetry script is `02b-telemetry.sh`. Two files sharing a bare prefix leaves execution order to an alphabetical tiebreak on the rest of the filename — never rely on that. Add a **lowercase letter suffix** (`02b-`, `02c-`, …) instead.

Each sub-script must:
- **Match the filename pattern `NN-name.sh` or `NNx-name.sh`** — the same regex the Stop dispatcher uses. Non-matching files are skipped, not run; `DEVTEAM_HOOK_DEBUG=1` traces both
- Exit `0` in all normal paths — a PreToolUse sub-script runs on **every tool call** and must never block one
- Stay off the hot path: return from the TTL/cache check before forking anything (no `python3`, no network) — see `update-check.sh`, whose interval sidecar cache is invalidated with the `[ prefs -nt cache ]` bash builtin

### Hook Files Map

| Event | File | Dispatcher | Purpose |
|-------|------|-----------|---------|
| `SessionStart` | `scripts/hooks/session-start.sh` | — | Stale config detection, missing prefs |
| `PreToolUse` | `scripts/hooks/pre-tool-use.sh` | Dispatcher | Runs `pre-tool-use/`: update checks, graphify hint, telemetry queue |
| `PreCompact` | `scripts/hooks/pre-compact.sh` | — | Session summary before context compaction |
| `Stop` | `scripts/hooks/stop.sh` | Dispatcher | Runs `stop/`: session summary, orphan scans, lint, fingerprint uniqueness, notifications, telemetry, graph refresh, archive rotation. Computes `DEVTEAM_NO_CHANGES` and `DEVTEAM_TOUCHED_PATHS` once and exports them |
| — | `scripts/hooks/lib/session-summary-detect.sh` | Shared library | Not a hook. Sourced by **both** `pre-compact.sh` and `stop/01-session-summary.sh`; exports `TODAY`, `NOW`, `HAS_CHANGES`, `TODAY_COMMITS`. Changing it affects both hooks — test both. |
| — | `scripts/hooks/lib/touched-paths.sh` | Shared library | Not a hook. Sourced by `stop.sh` to compute the touched-path set once; sub-scripts `02`, `02b`, `03`, `03b` consume `DEVTEAM_TOUCHED_PATHS` instead of re-forking `git status` + `git log`, and fall back to computing it themselves when run standalone. |
| — | `scripts/hooks/lib/update-check.sh` | Shared library | Not a hook. The update-check engine behind `pre-tool-use/01-check-updates.sh`; also owns the auto-update path, which delegates the download to `scripts/lib/installer-fetch.sh` and **skips the upgrade entirely** when that library is absent rather than falling back to an unverified fetch. |

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

- **AUTO-FIXED** lines: a broken skill path was **repaired in place** — the scanner located the skill unambiguously by basename and repointed the reference at its new location. Nothing is deleted. Verify the new path is the one you intended (a move between categories is the usual cause).
- **ACTION REQUIRED — Broken references that could not be resolved**: the scanner could not find a matching skill by basename, so it left the reference alone and reported it. Fix or remove the reference yourself.
- **ACTION REQUIRED — Skills with no agent reference**: a skill has no agent reference. Add a load reference in the suggested agent file, following that agent's existing skill-loading pattern (full path or backtick name form, whichever is already used).

> The scanner **never deletes**. Its earlier auto-fix ran `sed "/$ref/d"`, which removed the whole line containing the broken reference — on a routing-table row that took the detection signals with it, silently, on every Stop. Do not reintroduce a line-deleting fix.

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

`/devteam:setup` (`commands/setup.md`) is the explicit slash-command entry point for the same flow: it detects `FIRST_RUN` vs `REFRESH` from the presence of `docs/project.md`, reports the mode, and spawns `setup-assistant` with that mode as context.

---

## Coexistence Rule (Core Principle)

`dev-team-agents` is the base layer. Any rule in the target project's CLAUDE.md, README.md, AGENTS.md, or `.agents/` always takes precedence over these base standards. Agents must load and respect project context before acting on any task.

This principle must be reinforced in every agent and every command.
