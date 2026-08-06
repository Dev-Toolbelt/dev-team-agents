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
| `reasoning` | `opus` | none — banner shows `session-default` | architecture, planning, refactoring, security analysis, onboarding decisions |
| `backend-exec` | `sonnet` | none — banner shows `session-default` | backend implementation, backend review, code review, database, devops, qa, mobile, backend tests |
| `frontend` | `sonnet` | none — banner shows `session-default` | frontend implementation, frontend review, frontend tests, ui/ux design |
| `repetitive` | `haiku` | `low` | doc generation, changelogs, release notes, boilerplate, high-volume low-judgment tasks |

> **Effort is deliberately sparse.** Claude Code supports a per-subagent `effort:` key, but it **overrides the session's level** — applying it everywhere would silently undo a user who lowered effort for cost or latency. Only `repetitive` sets it at the tier level.

**Per-agent effort overrides.** Effort tracks how much a role needs to *reason*, which does not always follow the tier that picks its model. `tiers.json` therefore carries an `agent_effort` map, keyed by agent name then provider, which wins over the tier-level `effort`. Today it puts `low` on five specialists whose work is directed enough that extra exploration does not pay for itself: `backend-test-specialist`, `frontend-test-specialist`, `database-specialist`, `devops-specialist`, `qa-specialist`.

**Codex command limitation.** The project-local Codex path is `.codex/skills/devteam-*/SKILL.md` → `$devteam-*`. Those command skills are orchestration only, not custom-agent TOML layers, so runtime `model` and `model_reasoning_effort` are still enforced by the spawned custom agents in `.codex/agents/*.toml`.

The test for adding an agent there is recorded in `tiers.json` (`_why_qa_specialist`) and is not "does this role inspect code": it is whether the agent is **handed what to check**. `qa-specialist` is — it validates observable behavior against acceptance criteria written before it ran — so `low` is safe. The reviewers and `security-specialist` are not: what they are looking for is exactly what nobody wrote down, and the exploration `low` cuts is the deliverable.

`security-specialist` is deliberately **not** in that map, and the reason is recorded in `tiers.json` so it survives the next person who notices the gap: low effort means fewer, more consolidated tool calls and less exploration before answering, and in a security audit that exploration is the product. Adding an agent there is a decision to spend less reasoning on that role — make it explicitly, not by pattern-matching on the name.

> `repetitive` is the only tier on Haiku, and Haiku's context window is 200K against 1M on the others. Keep that tier for work that is genuinely low-judgment and bounded — it currently holds `technical-writer` alone. Test authoring is **not** low-judgment: `backend-test-specialist` sits in `backend-exec`, matching `frontend-test-specialist` in `frontend`. Do not move a test agent to `repetitive`.

- Every agent must include: **Foundational Rule** (load context first) + **Immutability Warning** + a **`## Model Identity`** section carrying the `<!-- run-banner -->` block (see the Run Banner rule below)
- Stack-agnostic: no hardcoded framework, language, or tool references in agent core behavior
- No plain-text `(yes/no)` prompts in the body — `agent-lint.sh` fails on them; use `AskUserQuestion` (see the Quiz-first Rule below)
- Max ~200 lines of content per agent; move reference material to skills. `helpers/size-limits.sh` enforces 205 — the extra 5 lines are the fixed-size run-banner block every agent carries, not content budget. Do not raise that ceiling again to make a long agent fit.

**Run Banner Rule.** Every agent prints a model-identity table — agent, tier, model, effort — twice: opening its first response, and closing the summary it hands back. On every provider. The second emission is the load-bearing one: only an agent's **final** message reaches the main conversation, so a subagent running in the background would otherwise show its banner to nobody.

**The closing emission needs its own section at the very bottom of the agent body**, `## Before You Finish`, enforced by `agent-lint.sh` both for presence and for being last. This is not decoration: stating the requirement only in `## Model Identity` at the top produced 14 opening banners out of 16 and **zero** closing banners out of 6 multi-message runs. An instruction that has to survive a 22-message task has to be the last thing read before the summary is written, not the first. If you add a section to an agent, it goes *above* that one.

The rule and the table format live in `skills/shared/model-identity/SKILL.md`; each agent body carries only its own values, in a `<!-- run-banner -->` block inside `## Model Identity`:

```markdown
<!-- run-banner -->
| Agent | Tier | Model | Effort |
|---|---|---|---|
| `backend-developer` | `backend-exec` | `sonnet` | `session-default` |
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
| Spawn integrity — no Task tool means stop and say so; `subagent_type` must come from the roster; a returned run banner is the only proof an agent ran | `skills/architecture/orchestration/SKILL.md` § Spawn Integrity | Load it and delegate. Never write a second "verify the spawn" rule, and never let a summary template ask for a list of agents from memory — the table is filled from returned banners |
| Which tests to execute when finishing a task — scoped to the touched code, full suite only on explicit user request | `skills/shared/scoped-test-execution/SKILL.md`, made mandatory for every agent by `skills/shared/project-context/SKILL.md` § Test Execution | Nothing — loading project-context is the enforcement. Add a per-agent load line only where the agent runs tests and its role changes the scope derivation; never restate the exception, and never add a second escalation criterion (suite speed, refactor width, shared code) |
| Memory layers — which artifact holds what, and the three-question routing that picks one | `skills/shared/project-context/SKILL.md` § Memory Layers | Nothing — loading project-context is the enforcement. Never add a sixth layer or a per-agent memory file: one finding lands in one layer, referenced from others, never copied |
| Wiki specification — entry format, `Tags` retrieval key, dynamic domain folders, index rows, never-delete. Every project gets one at `docs/wiki/`; `setup-assistant` creates `wiki/README.md` on FIRST_RUN as a **retrieval index** (one row per entry: `path \| keywords \| read-it-when`), the only part loaded unconditionally, greppable so context cost stays flat as it grows | `skills/shared/docs-sync/references/wiki-format.md` | Load it before writing an entry — one without its index row is unreachable, so that is an incomplete write. The **read** path (keyword lookup against the index) belongs to project-context § Context Loading Order and is the only part that lives elsewhere |
| No-Destruction Rule — a health check creates, moves, or adapts; it never deletes | `skills/shared/setup-health-check/SKILL.md` § No-Destruction Rule | Load it and delegate. Never write a per-check exemption: the rule holds for zero-byte markers too, because a rule with a judgment call in it eventually gets the judgment wrong |
| Reuse guidelines registry — mandatory reuse/standardization rules as `docs/development/reuse-guidelines.md` (Structural layer, see Memory Layers below), plus the review/lint gates | `skills/shared/reuse-guidelines/SKILL.md` | Load it and run the gate; never restate the table format or copy rows into review output — reference the row's `name` |
| Spec layer — per-feature `docs/specs/<feature>.md` (Given/When/Then, `touches`/`depends_on`), auto-contract gate, execution scope-lock, living-spec Amendment Log, and the end-of-work Spec Sync Gate (`[SPEC-DRIFT]` blocks deploy) | `skills/shared/spec-gate/SKILL.md`, `templates/spec-template.md` | Load it wherever the table applies — product-analyst (Step 5b), software-architect (contract/amendment), coding agents (scope-lock, business amendments), qa-specialist (sync gate). Never restate the format, gate condition, or amendment rules |

When a duplicated rule is found, delete the copy — do not "reconcile" the two wordings.

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
| `/devteam:seo` | seo-specialist | SEO quality gate — technical, on-page, Core Web Vitals, structured data, GEO/LLM readiness; auto-spawned by `/devteam:frontend` and `/devteam:fullstack` when the project matches a public-site/landing/e-commerce/blog Detection Signal |
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
| `/devteam:pr` | technical-writer (+ code-reviewer if `review` in args) | Drafting and creating a pull request; before creating (which pushes), loads `skills/shared/github-actions/SKILL.md`, which asks a CI/CD-aware quiz when GitHub Actions is configured, then watches Actions and auto-fixes failures if the user opted in |
| `/devteam:push` | none — thin wrapper around `skills/shared/github-actions/SKILL.md` | Pushing the current branch; asks a CI/CD-aware quiz (watch CI vs. push-only vs. other) when GitHub Actions is configured, otherwise pushes normally |
| `/devteam:commit` | reads staged changes, groups by layer, writes and runs commits | Committing changes with the project's or Conventional Commits pattern |
| `/devteam:learn` | technical-writer + software-architect¹ | Consolidating session decisions, patterns, and discoveries into docs, wiki, and ADRs |
| `/devteam:rule` | technical-writer | Cataloging a mandatory reuse/standardization rule (`/devteam:rule use o componente XPTO em todo o projeto`) into `docs/development/reuse-guidelines.md`, classified as `code-pattern` / `path-convention` / `design-rule` |
| `/devteam:explain` | none — answers in the main context | Explaining a term, acronym or piece of jargon seen in the session (`/devteam:explain SPA` or `/devteam:explain SPA, SSR, tenant`); short by design — expands every acronym, states the problem the term solves, gives one example, draws a `mermaid` diagram only when the term is a shape (flow, exchange, hierarchy, lifecycle), and always closes by offering an interactive quiz |
| `/devteam:update` | runs `update.sh` (which delegates freshness check to `hooks/pre-tool-use/01-check-updates.sh`) | Checking for and applying dev-team-agents updates |
| `/devteam:symlinks` | runs `fix-symlinks.sh` (detects OS, repairs materialized `.claude/` links, guides the OS fix on exit 3) | Diagnosing and repairing broken dev-team-agents symlinks (Windows without native symlink support) |
| `/devteam:health-check` | loads `skills/shared/setup-health-check/SKILL.md` and `skills/shared/output-format/SKILL.md`; no agents spawned | Diagnosing an installation — detects the active provider (`claude` / `opencode` / `codex`), runs the 12 check categories (symlinks, scripts, user data, provider config, graphify, CLAUDE.md/AGENTS.md, .gitignore, preferences, notifier, credentials, memory artifacts, python prerequisite) and applies auto-fixes — never deletions, per its No-Destruction Rule |

¹ conditional — spawned only when the task context involves that scope. ² test-gated — spawned only when the project's `CLAUDE.md` `## dev-team-agents` section has `TESTS_REQUIRED=yes` (or the key is absent — default to running tests). If `TESTS_REQUIRED=no`, the test phase is skipped entirely.

> **Exception — commands that do NOT load `current-context`:** `/devteam:commit` (operates on the staging area, not a branch scope), `/devteam:update` (operates on the local installation), `/devteam:health-check` (operates on the local installation), `/devteam:learn` (operates on session evidence, not a branch scope), and `/devteam:rule` (catalogs a user-stated rule into `docs/development/reuse-guidelines.md`, not scoped to a branch or diff). These five are the complete list — verify with `grep -L current-context commands/*.md`. `/devteam:symlinks` and `/devteam:explain` also do not load it, but both name it in prose to record that it does not apply, so neither appears in that grep.

> **Exception — commands that do NOT require Plan Gate:** the canonical per-command `plan_gate` value lives in `scripts/lib/commands.json` (`required` / `conditional` / `opt_out`). Only `/devteam:update`, `/devteam:symlinks`, `/devteam:health-check`, and `/devteam:push` are `opt_out` — thin script/skill runners with their own interactive guardrails. `/devteam:review` and `/devteam:explain` are `conditional` and read-only by design (neither body carries a plan-gate step — review reads the diff and delegates; explain answers a question and writes nothing), so in practice both execute directly.

**Command tier mirrors its lead agent's tier.** Each row in `scripts/lib/commands.json` carries a `tier` and an `agent`, and the two are **not** independent knobs: on opencode the snippet's `agent` makes the command run *as* that agent while `model` is resolved from the **command's** tier, so a divergence runs an agent on a model that is not its own. `helpers/agent-lint.sh` (`check_command_roster`) fails on any mismatch, and on an `agent` with no file in `agents/`. The CI contract checker validates rendered output and only catches a dangling ref — the source-side rule is the lint's.

`/devteam:update`, `/devteam:symlinks`, `/devteam:health-check` and `/devteam:explain` spawn **no** agent; their `agent` field is filler the renderer still requires. The first three are thin script/skill runners; `explain` answers in the main context on purpose, because the terms it explains come from the live session and a subagent receives only the prompt. All four name `technical-writer`, which keeps the filler consistent and resolves the rule above to `repetitive` — what that class of work actually is. Do not read those four rows as a delegation target.

**Command frontmatter — `model:` pins the body's model on Claude Code, and only there.** `commands/<name>.md` may open with a YAML block; Claude Code reads it, and it is the **only** route by which a command's tier reaches Claude, which symlinks the body and never passes it through the renderer. `render_provider.py` strips the block before emitting the opencode `template` and the Codex prompt (both resolve the model from `commands.json` `tier`), and `render_command_claude` re-reads the source file so Claude still receives it byte-identical — the CI contract checker enforces that. The key is permitted on the **`repetitive` tier alone**, with exactly the argument that keeps `effort:` sparse: it **overrides the session's model**, so pinning a `reasoning` command to `opus` would silently undo someone who lowered the session for cost, while a `haiku` pin can never raise what the user chose. `check_command_roster` in `helpers/agent-lint.sh` fails on a pin outside `repetitive` and on a value that is not `tiers.json.repetitive.claude`. Presence is **permitted, not required**: `/devteam:explain` is `repetitive` and deliberately carries no pin, because its output is a teaching explanation grounded in the user's own code and the session model is the one they picked for that.

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
│   │                                identity (name == dir, unique) + quiz-first +
│   │                                orchestration roster ↔ agents/ (name + tier, both ways)
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
│   ├── graphify-refresh.sh · validate-commit-msg.sh · reuse-lint.sh · design-token-lint.sh
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

**`scripts/lib/preferences-defaults.json` is the single source of truth for the default schema.** Everything else is a mirror, and the set had already drifted five ways before it was reconciled (`qa_browser` missing from one, `telemetry` inverted in another, eight fields missing from a third). When you change a key, change every mirror in the same commit:

| Mirror | Why it cannot just read the JSON |
|--------|----------------------------------|
| `scripts/install.sh` — no-python3 fallback heredoc | No JSON parser available on that path |
| `CLAUDE-md/preferences.md` — schema block + field table | Documentation |
| `skills/shared/user-preferences/SKILL.md` — schema block + field table | Documentation read by agents |
| `README.md` / `README.pt-BR.md` — worktree preference table | Documentation |

`skills/shared/project-context/SKILL.md` and `skills/shared/setup-health-check/references/checks-list.md` **read the canonical file** instead of mirroring it — keep them that way.

**Defaults apply only to a file that does not exist.** `preferences.json` and `credentials.local.json` are both created when absent and never rewritten: install merges with existing values winning, and the session-start backfill only adds missing keys. **`telemetry` and `auto_update` are `CONSENT_KEYS`** — both default to `true` in a fresh file, but are backfilled as `false` into a pre-existing one, because that file's owner never saw a prompt for a field added after they installed. The lists live in `scripts/install.sh` and `scripts/hooks/session-start.sh`; keep them in sync.

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
- **A push is also a finalization signal, not only session end.** `/devteam:push`, and the push that `/devteam:pr` triggers via `gh pr create`, run the same detection the `Stop` hook uses (dirty working tree, staged changes, or a commit made today — see `scripts/hooks/lib/session-summary-detect.sh`) right after the push succeeds, and write today's entry then if it is missing, instead of waiting for the session to end.

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

The script prints existing ADR titles and auto-numbers the file — see `skills/shared/adr/SKILL.md` § Check Before Creating before running it, so a decision doesn't get a second, duplicate ADR. Fill in the generated template and change the status from `Proposed` to `Accepted`.

### Stop Hook (Automated Enforcement)

`install.sh` registers `scripts/hooks/stop.sh` as the `Stop` dispatcher in `.claude/settings.json`, running every sub-script in `scripts/hooks/stop/` in order — including `01-session-summary.sh`, which detects missing session-summary entries and prompts for one. No manual setup is required.

→ See [`CLAUDE-md/hooks.md`](CLAUDE-md/hooks.md) for the Stop and PreToolUse sub-script conventions and the full hook files map.

---

## Commit Rule

When making a git commit for any task:

1. **Load `skills/shared/conventional-commits/SKILL.md`** before writing the commit message
2. **Defer to the project's own pattern first**: run `git log --oneline -10` and check whether the existing history follows Conventional Commits or a different format (e.g., GitHub-style `[feature]`, plain imperative, Jira ticket prefix). If a project-specific pattern is clearly in use, follow it instead.
3. **Never include Claude attribution**: no `Co-Authored-By: Claude`, no `🤖 Generated with Claude Code`, no AI tooling references in commit messages, PR titles, or PR bodies.

---

## Push & CI Monitoring Rule

When the user **explicitly asks to push** (a commit alone does not count) — including via `/devteam:push` — and the GitHub CLI is configured (`gh auth status` succeeds):

1. **Load `skills/shared/github-actions/SKILL.md`** and follow it.
2. If the repo has workflow files (`.github/workflows/*`, cached in `preferences.json` as `ci_cd_detected`), **ask the user first** with a dynamic quiz (`AskUserQuestion`): watch CI and auto-fix (recommended), push only, or other. Only proceed to watching if they opt in.
3. If watching, watch the triggered run and, on failure, run the capped **diagnose → fix → re-push** loop (max 3 attempts), reporting a **one-line summary** to the user each cycle.
4. Stop and hand back to the user when the run is green, the 3-attempt cap is reached, or the failure is not auto-fixable (missing secret, infra, required approval). Never disable/skip a workflow or weaken a test to force green.

If `gh` is not configured or there are no workflow files, push normally and skip both the quiz and the monitoring loop. The same quiz gates the push that happens when opening a PR via `/devteam:pr`.

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

`dev-team-agents` is the base layer. Any rule in the target project's CLAUDE.md, README.md, AGENTS.md, or `.agents/` always takes precedence over these base standards. Agents must load and respect project context before acting on any task. This principle must be reinforced in every agent and command.
