# CLAUDE.md — dev-team-agents
Instructions for working on this repository. These rules apply to Claude when authoring or modifying agents, skills, scripts, and documentation inside `dev-team-agents`.

---

## What This Repo Is

**Multi-agent development harness** — a harness for organizing AI agents in software development. Not just a bundle of agents: it is the layer that governs how those agents plan, execute, test, review, and record their work.

Stack-agnostic, project-aware. Installed at the project level (`.dev-team-agents/`) — not globally.

The canonical source (`agents/`, `commands/`, `skills/`, `scripts/hooks/`) is **provider-agnostic**. Claude Code is the default provider; opencode and OpenAI Codex CLI are supported via a render engine (`scripts/render-provider.sh`) that emits the provider-specific file tree per target project. See `docs/providers.md` for the tier → model id map and the per-provider install scripts.

This file is the single home of the contributor rules. `AGENTS.md` only points Codex and opencode contributors here: Codex never reads `CLAUDE.md`, and opencode reads it only when no `AGENTS.md` exists — and one always does, because `install-codex.sh` writes it. Never put a rule there.

### Provider Parity Rule

**Any change to provider-facing behavior is implemented and tested for every supported provider, never for Claude Code alone.** The supported set is `scripts/lib/devteam/providers.py:ALL_PROVIDERS` (today: `claude`, `opencode`, `codex`) — read it, do not restate it.

Provider-facing means anything a provider's install observes: `bind` / `sync` / `unbind` / `doctor` / `migrate`, the installers (`install-opencode.sh`, `install-codex.sh`, `install-provider.sh`, `update.sh`), the render engine, hook wiring, and the agents, commands and skills a provider receives.

- A plan for such a change lists each provider in scope. Excluding one is a decision: the plan names it and says why, and the PR template's parity checkbox records it.
- Tests iterate `ALL_PROVIDERS` rather than naming providers, and keep a per-provider fixture map that fails when a provider is added without a case — `tests/test_provider_ownership.py` is the pattern.
- A guarantee that `bind.py` enforces for Claude natively must be enforced for the delegated providers through their installers too. Claude being the identity case is not a reason for the others to skip a check (ADR-0022 is what that gap cost).

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

### Mandatory Scoped Review Before Done

Every task that changes functionality in this repository ends with a review-and-fix pass, **run automatically, without asking**. It is skipped only for one-liner fixes (typo, single-line change, rename in one file) and for changes that touch no functionality (`docs/`, README, CHANGELOG, code comments, formatting). Edits to `agents/`, `commands/`, `skills/`, `templates/` and `CLAUDE.md` rules are functionality and are never exempt. This is a project-level rule, so it wins over the shipped Review Next-Step Gate per the Coexistence Rule — and the gate is never reached anyway: this pass satisfies its "a review already ran this session" skip condition. The Visual Check Gate and the commit/PR hand-off still follow.

| Point | Rule |
|---|---|
| **Owner** | The main conversation (or outermost orchestrator). A sub-agent reports its touched paths and never starts the pass itself |
| **Plan** | Every plan for such a task ends with a `Scoped review` step, so approving the plan covers the in-scope fixes |
| **Scope** | When the plan is approved, save `git status --porcelain` and `git diff` to the scratchpad as the baseline; the scope is the current diff minus that baseline. Reviewer prompts name the touched files and hunks and say everything else is out of scope |
| **Reviewers** | This repo's own map, not the shipped classifier: `code-reviewer` always — when it classifies the diff as `BOTH`, spawn `backend-reviewer` and `frontend-reviewer` instead; `security-specialist` when `scripts/`, hooks, the CLI, credentials or installers are touched; `software-architect` when a canonical rule, provider-facing behavior or an ADR Trigger Rule case is touched; `qa-specialist` when a spec or acceptance criteria exist. Spawned in parallel under `skills/architecture/orchestration/SKILL.md` § Spawn Integrity — a reviewer that did not run means the task is not done |
| **Fix** | Apply in-scope BLOCKING and SUGGESTION findings without asking. A fix beyond the approved plan (new file, behavior change, anything provider-facing) goes through `AskUserQuestion`; NITs and out-of-scope items are listed |
| **Re-verify** | `helpers/agent-lint.sh`, `helpers/size-limits.sh`, `helpers/plugin-lint.sh` when `plugins/` changed, `helpers/orphan-skill-scan.sh` when `agents/` or `skills/` changed, and tests per `skills/shared/scoped-test-execution/SKILL.md`. At most **one** re-review, limited to the fixed hunks; BLOCKING items it still finds are reported as open and asked about. This cap wins over the shipped Review Loop (`skills/shared/review-result/SKILL.md`) for this pass |
| **Done** | Only after the review returned and its fixes landed — wrap-up and the session-summary entry come after it. The close carries a table built from returned run banners and `review-result` markers: reviewer · findings · applied · left open. Zero findings is a valid result |

Commits and pushes still happen only when the user asks.

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
- Max ~200 lines of content per agent; move reference material to skills. `helpers/size-limits.sh` enforces 211 — the extra lines are the fixed-size run-banner block and the `## Before You Finish` section every agent carries, not content budget. Do not raise that ceiling again to make a long agent fit.

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

**Coding agents** (`backend-developer`, `frontend-developer`, `mobile-developer`, `database-specialist`, `devops-specialist`, `ui-ux-designer`, `backend-test-specialist`, `frontend-test-specialist`) must also include a **`## Worktree Isolation`** section. That section **delegates** — in two or three lines it points at `skills/shared/worktree/SKILL.md` § Decision Cascade, the canonical home that ships to installed projects (this `CLAUDE.md` does not — `install.sh`'s KEEP_ROOT drops it). **Do not restate the cascade in an agent body.** It used to be inlined in all eight agents (~15 lines each) and drifted between them. The block below is contributor documentation of the same rule; when the two disagree, the skill wins and this block is patched to match.

**Canonical worktree decision cascade** (resolve top-down, stop at the first match):

0. Spawn prompt carries `WORKTREE_PATH` and `BRANCH` → work only there; no setup, no session file, no finalization — the orchestrator owns merge and teardown
1. `.dev-team-agents/.worktree-session` present → follow the stored decision silently:
   - `worktree=no branch=<b>` → operate on branch `<b>`; do not load the worktree skill
   - `worktree=yes branch=<b>` → load `skills/shared/worktree/SKILL.md` using base branch `<b>`
2. Session file absent → read `worktree_active` from `.dev-team-agents/resolved/preferences.json`:
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
| Worktree decision cascade | `skills/shared/worktree/SKILL.md` § Decision Cascade (shipped); `CLAUDE.md` → *Canonical worktree decision cascade* is the contributor-facing summary | Delegate from `## Worktree Isolation` (see Agents above) |
| Layered-commit table and commit message format | `skills/shared/conventional-commits/SKILL.md` | Load it; commands must not carry a second copy of the table |
| Plan document format | `templates/plan-template.md`, loaded via `skills/shared/plan-mode/SKILL.md` | Load the template; never ship a second rendering of the format |
| Spawn integrity — no Task tool means stop and say so; `subagent_type` must come from the roster; a returned run banner is the only proof an agent ran | `skills/architecture/orchestration/SKILL.md` § Spawn Integrity | Load it and delegate. Never write a second "verify the spawn" rule, and never let a summary template ask for a list of agents from memory — the table is filled from returned banners |
| Which tests to execute when finishing a task — scoped to the touched code, full suite only on explicit user request | `skills/shared/scoped-test-execution/SKILL.md`, made mandatory for every agent by `skills/shared/project-context/SKILL.md` § Test Execution | Nothing — loading project-context is the enforcement. Add a per-agent load line only where the agent runs tests and its role changes the scope derivation; never restate the exception, and never add a second escalation criterion (suite speed, refactor width, shared code) |
| Memory layers — which artifact holds what, and the three-question routing that picks one | `skills/shared/project-context/SKILL.md` § Memory Layers | Nothing — loading project-context is the enforcement. Never add a sixth layer or a per-agent memory file: one finding lands in one layer, referenced from others, never copied |
| Wiki specification — entry format, `Tags` retrieval key (4–10 terms, checked by `scripts/index-lint.sh` from the `03g` Stop hook), dynamic domain folders, index rows, never-delete. Every project gets one at `docs/wiki/`; `setup-assistant` creates `wiki/README.md` on FIRST_RUN as a **retrieval index** (one row per entry: `path \| keywords \| read-it-when`), the only part loaded unconditionally, greppable so context cost stays flat as it grows | `skills/shared/docs-sync/references/wiki-format.md` | Load it before writing an entry — one without its index row is unreachable, so that is an incomplete write. The **read** path (keyword lookup against the index) belongs to project-context § Context Loading Order and is the only part that lives elsewhere |
| ADR directory and ADR index — the directory is whatever `new-adr.sh --dir` resolves (`docs/development/adrs/`, else an existing `docs/adr/`), and `<adr-dir>/README.md` is the ADRs' retrieval index, one `ADR · Status · Keywords · Read it when` row per ADR; an ADR's optional `**Applies to:**` globs name the paths it governs | `skills/shared/adr/SKILL.md` § File Location, § ADR Index, § Applies To | Read the directory from `--dir`, never hardcode it; add or update the row in the same edit as the ADR; never restate the `Applies to` matching rules |
| Document Lifecycle — plans carry a `**Status:**` line with evidence; superseded documents and point-in-time snapshots carry a historical banner; nothing is deleted | `skills/shared/docs-sync/SKILL.md` § Document Lifecycle | Reference it; never write a second marker format |
| No-Destruction Rule — a health check creates, moves, or adapts; it never deletes | `skills/shared/setup-health-check/SKILL.md` § No-Destruction Rule | Load it and delegate. Never write a per-check exemption: the rule holds for zero-byte markers too, because a rule with a judgment call in it eventually gets the judgment wrong |
| Reuse guidelines registry — reuse/standardization rules as `docs/development/reuse-guidelines.md` (Structural layer, see Memory Layers below), optionally path-`scope`d and `advisory`, plus the review/lint gates (ADR-0036) | `skills/shared/reuse-guidelines/SKILL.md` | Load it and run the gate; never restate the table format or copy rows into review output — reference the row's `name` |
| Spec layer — per-feature `docs/specs/<feature>.md` (`status`, Given/When/Then with stable `S<n>` IDs, `touches`/`depends_on`), sprint-task resolution (`TASK-NNN` → spec + `Covers`), retroactive specs for built features (`/devteam:spec`), `[spec:<feature>#S<n>]` test traceability, `scripts/spec-lint.sh` (ADR-0037), auto-contract gate (`templates/contract-template.md`), execution scope-lock, living-spec Amendment Log, and the end-of-work Spec Sync Gate (`[SPEC-DRIFT]` blocks deploy) | `skills/shared/spec-gate/SKILL.md`, `templates/spec-template.md` | Load it wherever the table applies — product-analyst (Step 5b), software-architect (contract/amendment), coding agents (scope-lock, business amendments), qa-specialist (sync gate). Never restate the format, gate condition, or amendment rules |
| Task List Mirroring — an approved plan's Steps become each provider's native task list, moved in step with Progress Reporting; the only way a plan reaches the task board | `skills/shared/plan-mode/SKILL.md` § Task List Mirroring | Nothing — loading plan-mode is the enforcement; `agent-lint.sh` (`PLAN_MODE_LOADERS`, `PLAN_MODE_COMMAND_EXEMPT`) fails when the section, an agent's plan-mode load or a plan-gated command's pointer disappears |
| Review result marker — every review or QA pass ends with `<!-- review-result: findings=N -->`, the only way the task board learns a review's outcome; findings go in its Findings Table, a clean verdict carries a `**Verified:**` line, and the fix-and-re-review loop is its § Review Loop | `skills/shared/review-result/SKILL.md` | Name it from `## Before You Finish` in one sentence; commands that apply findings point at § Review Loop and never restate its cap or terminal states; `agent-lint.sh` (`REVIEW_RESULT_AGENTS`) fails a reviewer or QA agent that omits it |
| Periodic status-table check-in while background sub-agents work — table format, `ScheduleWakeup` cadence, and the `credentials.local.json` gate (`work_feedback_active`, `work_feedback_interval_minutes`) | `skills/shared/work-feedback/SKILL.md` | Orchestrators load it from `skills/architecture/orchestration/SKILL.md` § Spawn Integrity, check 6. Never restate the gate check, loop mechanics, or table format |
| Sub-agent Question Relay — a sub-agent cannot ask the user; it ends its report with an `## Open Decisions` block and the orchestrator asks, then continues the same sub-agent with the answers | `skills/shared/interaction-patterns/SKILL.md` § Sub-agent Question Relay | Reference it wherever a spawned agent's workflow needs a user decision or approval; never write a per-command relay loop |
| Test Gate — how `TESTS_REQUIRED` is resolved: whichever of `CLAUDE.md` / `AGENTS.md` carries the key; two different values go to the Contradiction Guard; absent means `yes` | `skills/shared/auto-routing/SKILL.md` § Test Gate | Point to it in one line; a spawned agent uses the value its command resolved and never re-derives it |
| Review Next-Step Gate — a flow whose next step is a review closes with a dynamic `AskUserQuestion` (review recommended, `Don't review`, options built from the diff and specs), never a plain-text pointer | `skills/shared/interaction-patterns/SKILL.md` § Review Next-Step Gate | Reference it at the flow's close; never restate the options or skip conditions |
| Visual Check Gate — a flow that changed or reviewed web UI closes with a dynamic `AskUserQuestion` offering to open the changed screen, loopback only, reusing or starting the environment through the local-environment skill; never a plain-text "check it in the browser" line. Its § Browser Choice is also the single browser-selection rule (`qa-specialist` follows it) | `skills/shared/interaction-patterns/SKILL.md` § Visual Check Gate | Reference it at the flow's close, after the Review Next-Step Gate; sub-agents end with a **Screens to check** list instead of asking. Never restate the options or the browser choice; the reuse order belongs to the Local environment row |
| Scoped review before done — contributor-only; no provider auto-loads the core-store copy (`versions.py` copies it so the `CLAUDE-md/` links resolve) | `CLAUDE.md` § Mandatory Scoped Review Before Done | Nothing — it does not apply to installed projects. Never copy it into `agents/`, `commands/` or `skills/` |
| Local environment — discovery order (docs before manifests), reuse before starting, start/health-check/report, and stop without destroying data; used by `/devteam:up`, `/devteam:down` and the Visual Check Gate | `skills/devops/local-environment/SKILL.md` | Load it and point at its sections; never carry a second discovery order, reuse list or stop rule |
| Fixed-message wording — in a command, `output exactly` is a fixed message said in the user's language, `output verbatim` is passed through byte-for-byte (script output, lines a later step parses) | `skills/shared/project-context/SKILL.md` § Language Policy | Commands use the two wordings and never restate them; the per-prompt `[DEVTEAM:LANGUAGE]` hook line is the delivery to the main conversation, not a copy; `agent-lint.sh` (`check_verbatim_wording`) fails a script passthrough worded `exactly` |
| Dirty-Tree Pre-flight — `/devteam:push`, `/devteam:merge`, `/devteam:pr` (and a push/merge asked in plain language) run the `/devteam:commit` flow automatically on uncommitted changes, then continue | `skills/shared/git-workflow/SKILL.md` § Dirty-Tree Pre-flight | Load it as the first step; never carry a copy of the commit routine |
| PR Comment Gate — reviewing a PR/MR drafts one comment mentioning the assignees (fallback: author), rule-violating BLOCKING/SUGGESTION items with `path:line` + code excerpts; with no BLOCKING it approves instead (never self-approval); posted only after an `AskUserQuestion` confirmation | `skills/shared/pr-review/SKILL.md` § PR Comment Gate | Point to it from the review close; never restate the format, mention rule, or platform commands |

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
| `repo-release-prep` | `.claude/skills/repo-release-prep/SKILL.md` — contributor-only, same fate as `agent-creator`: tracked here, stripped from the package. **Named apart from the shipped `release-prep` on purpose.** The two are different documents — this one is the 10-step runbook for tagging *this* repository (orphan scan, agent compliance, README sync, package exclusions, this very table), while `skills/shared/release-prep/SKILL.md` is the generic checklist a bound project gets. They shared the name `release-prep` until the collision blocked `devteam bind` on this repository, because bind will not write a framework skill's symlink over a real directory. | `/repo-release-prep` |
| `review` | `agents/code-reviewer.md` | `/review`, `/review backend`, `/review frontend`, `/review both` |

**Command-level skills** — loaded by `commands/*.md` files rather than by agents directly:

| Skill | Used by |
|-------|---------|
| `current-context` | All `/devteam:*` commands — detects branch/worktree state before executing |
| `spawn-classifier` | `/devteam:plan` and multi-agent commands — decides conditional agent spawn |

#### User-Invocable Commands (`commands/*.md`)

Slash commands installed to `.claude/commands/devteam/` and invoked as `/devteam:<name>` (e.g. `/devteam:plan`). This keeps all devteam commands namespaced and separate from any project-specific commands. Each command spawns agents via the Task tool and restricts scope to the current git branch/worktree unless overridden by the user.

Commands are subject to the same authoring discipline as agents: **max ~200 lines each**, enforced by `helpers/size-limits.sh`, and the **Quiz-first Rule** below, enforced by `helpers/agent-lint.sh`. A command is a thin orchestration wrapper — it must never restate a skill it already loads.

→ See [`CLAUDE-md/commands.md`](CLAUDE-md/commands.md) for the full command → agents table, the conditional/test-gated spawn markers, the `current-context` and Plan-Gate exception lists, the command-tier mirror rule, the Claude-only frontmatter keys (`model:`, `argument-hint`, `description`), and the Code Reviewer router roles.

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

→ See [`CLAUDE-md/file-structure.md`](CLAUDE-md/file-structure.md) for the repository tree and the two `helpers` directories: root `helpers/` is dev-only and stripped from the package, `scripts/helpers/` ships. When a rule or script path references "helpers", state which of the two it means.

---

## User Preferences

→ See [`CLAUDE-md/preferences.md`](CLAUDE-md/preferences.md) for the preferences.json schema, language rules, and migration notes.

**`scripts/lib/preferences-defaults.json` is the single source of truth for the default schema.** Everything else is a mirror, and the set had already drifted five ways before it was reconciled (`qa_browser` missing from one, `telemetry` inverted in another, eight fields missing from a third). When you change a key, change every mirror in the same commit:

| Mirror | Why it cannot just read the JSON |
|--------|----------------------------------|
| `scripts/install.sh` — no-python3 fallback heredoc | No JSON parser available on that path |
| `CLAUDE-md/preferences.md` — schema block + field table | Documentation |
| `skills/shared/user-preferences/SKILL.md` — schema block + field table | Documentation read by agents |
| `docs/user-preferences.md` / `docs/user-preferences.pt-BR.md` — schema block, key table and effects table | Documentation |

`skills/shared/project-context/SKILL.md` and `skills/shared/setup-health-check/references/checks-list.md` **read the canonical file** instead of mirroring it — keep them that way.

**Defaults apply only to a file that does not exist.** `preferences.json` is created when absent and never rewritten: install merges with existing values winning, and the session-start backfill only adds missing keys. `credentials.local.json` is not created implicitly; see [Credentials Reference](docs/credentials.local.md) for creation methods. **`telemetry` and `auto_update` are `CONSENT_KEYS`** — both default to `true` in a fresh file, but are backfilled as `false` into a pre-existing one, because that file's owner never saw a prompt for a field added after they installed. The lists live in `scripts/install.sh` and `scripts/hooks/session-start.sh`; keep them in sync.

### Machine-Local Records

**`scripts/lib/devteam/paths.py:MACHINE_LOCAL_RECORDS` is the single source of truth** for what a project's state belongs in the machine-local subtree. When adding a machine-local record, add its **basename** (case-insensitive) to that tuple and mirror it in every place it is mentioned:

| Mirror | Purpose |
|--------|---------|
| `scripts/lib/devteam/paths.py` — `MACHINE_LOCAL_RECORDS` | Canonical classifier, read by `is_machine_local_record(name)` |
| `CLAUDE-md/cli.md` — `data/machines/<machine-id>/projects/<id>/…` section | Documentation; enumerate what lives in the machine subtree |
| `CLAUDE-md/user-data.md` — § Under v3 layout 2 | Documentation; explain the migration and the rule for new files |
| `scripts/lib/devteam/paths.py` — docstring of `MACHINE_LOCAL_RECORDS` | Rationale for the list |

The set today: **`state.json`, `bind-manifest.json`, `telemetry-queue.json`** (all in the store's machine-local folder), **`audit.log`, `notifications.jsonl`, `notifications-seen.json`** (ADR-0017), the **`task-board/`** directory of per-session task records (ADR-0018), **`integrations-status.json`** (the last integration connection test), **`entitlement.json`** (the signed account entitlement, ADR-0029), **`account-session.json`** (the non-secret half of the signed-in session, ADR-0029), **`command-usage.json`** (how often each devteam command was run on this machine, ADR-0030), **`global-skills-lock.json`** (source and content hash of each skill `devteam skills install` placed, ADR-0040), **`backlog-claims.json`** (which orchestrator on this machine holds which sprint task, until when, ADR-0044), plus every dot-prefixed name (cache, ETag, marker file). **`credentials.local.json`** is a special case: machine-local by classification (ADR-0024) but lives in the project tree at `.dev-team-agents/credentials.local.json`, never in the store, and is ignored by the bind-managed `.gitignore` block. When a review or ADR discussion finds a record that should be machine-local but is not listed, add it to the tuple and update the mirrors in the same commit.

---

## Notification System

→ See [`CLAUDE-md/notifications.md`](CLAUDE-md/notifications.md) for format, types, channels, suppression, and context window estimation.

---

## User Data Directory

→ See [`CLAUDE-md/user-data.md`](CLAUDE-md/user-data.md) for directory structure, file purposes, gitignore rules, and package exclusions.

---

## Versioning

→ See [`CLAUDE-md/versioning.md`](CLAUDE-md/versioning.md) for the semantic versioning policy, including pre-release names for builds ahead of a release (`2.49.0-dev.1`, never an invented patch) and the desktop app's own version line in `app/package.json`.

---

## Plugins

A plugin is an optional, per-project integration declared by a manifest in `plugins/<name>/plugin.json`. See `plugins/README.md` for the authoring guide and `docs/development/adrs/0019-plugins-as-manifest-declared-per-project-integrations.md` for the design.

The CLI surface is `devteam plugin {list,show,enable,disable,config,run}`, with `--path` and `--json` flags. Settings live per-project in `.dev-team-agents/plugin-settings/<name>.json` (committed). Hooks are dispatched by `scripts/hooks/pre-tool-use/02d-plugins.sh` and `scripts/hooks/stop/99a-plugins.sh`.

---

## v3 — Global Store, Project Bind and the `devteam` CLI

One installation per machine, many bound projects: the canonical tree lives in a versioned **core**
store, durable state lives in a separate **data** store, and each project carries only a committed
`project.json` (identity, `layout`, `context_paths`) plus excluded, regenerable bind artifacts. An
update writes one version and `devteam sync --all` re-points every project that is not pinned.

**`data/` is split by what a record says** (ADR-0013): what the user authored or decided is portable
and stays at the top of the store; what this machine observed or built — the registry, the bind
manifests, `state.json`, locks, caches and credential *values* — lives under
`data/machines/<machine-id>/`. `paths.is_machine_local_record()` is the single answer to which side a
record belongs on; never re-derive that rule at a call site. No synchronisation exists or is implied.

**Credential references are portable; values are machine-local** (ADR-0010): `data/credentials/` holds the
**references** (purpose, scope, which backend holds the value — no secret data), reviewed and diffed in git;
`data/machines/<machine-id>/secrets/` or the OS keychain holds the **values** themselves, never exported or
shared. This split keeps the references reviewable while values stay on the machine that set them. Reading a
value is audited (who, when, which key) in a machine-local append-only log.

A project's memory moves into the store only when the user runs **`devteam upgrade`** — `bind`,
`sync`, `update` and `migrate` report a stale `layout` and change nothing. Preferences cascade in
three personal layers and are resolved on write into `.dev-team-agents/resolved/preferences.json`,
which is the one file agents read; `context_paths` is committed topology, not a preference.

The CLI is python3 (`scripts/cli/devteam`, implementation in `scripts/lib/devteam/`); hooks stay
bash. Contributors working in that tree are bound by the **No-Destruction Rule** — canonical home
and its one named CLI exception in `skills/shared/setup-health-check/SKILL.md` — and by the rule
that **every store mutation is locked and written atomically**.

The CLI's `--json` output is the desktop app's public API (ADR-0011); an output shape change is a
breaking change. The contract is swept across every subcommand by `tests/test_json_contract.py`,
discovering commands from the real parser rather than a hardcoded list.

→ See [`CLAUDE-md/cli.md`](CLAUDE-md/cli.md) for the store layout, bind modes, the command table,
the `--json` contract and exit codes, and the contributor rules.
**Accounts** ([ADR-0029](docs/development/adrs/0029-mandatory-accounts-owned-by-the-cli-licensed-through-a-signed-offline-entitlement.md)): a signed-in account gates the CLI, `warn` then `enforce`; see [`CLAUDE-md/cli.md`](CLAUDE-md/cli.md) § Account.

---

## Immutability Contract

These files are installed at a fixed path (`.dev-team-agents/`) and replaced entirely on every update. Users are warned not to modify them directly. When authoring changes:

- Maintain backward compatibility where possible
- If a breaking change is unavoidable, document it in the PR description and README release notes
- Never remove a skill or agent without a deprecation cycle (one minor version with a warning)

**Compatibility regime per surface.** Each surface has one rule for how it may change, and the rule lives in one place — this table only points at it:

| Surface | Regime | Canonical home |
|---------|--------|----------------|
| User state — `preferences.json`, project memory, files in a bound project | Never destroyed; defaults fill only what is absent; a structure move needs consent | `skills/shared/setup-health-check/SKILL.md` § No-Destruction Rule · § User Preferences above · ADR-0012 |
| CLI `--json` output and store schemas | Additive freely; a removal ships a `deprecated` list one release first | ADR-0014 |
| Shipped agents, skills and commands | One minor version with a warning before removal | This section |

---

## Agent Memory System

Three mechanisms work together to minimize context loss between sessions. All three are enforced automatically after installation.

### Session Summary Rule

**At the end of any session where files were created or modified**, write a new entry at the top of the session summary file. Read `.dev-team-agents/memory-dir` (a one-line pointer) to find the absolute path; on layout 1 it resolves to `.dev-team-agents/user-data/session-summary.md`, and on layout 2 to `data/projects/<project_id>/session-summary.md` in the global store. Write the entry in the format:

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

**Automated gap detection.** `scripts/hooks/stop/03e-adr-gap-check.sh` is a heuristic, non-blocking safety net for this rule: it warns when a session touched a dependency manifest, a schema migration, or a provider config file but added no new file under `docs/development/adrs/`. It never decides whether an ADR is actually warranted — that judgment stays with the triggers above — it only prevents the signal from being silently missed. It warns **once per distinct set of signals** (signature kept as `.adr-gap-warned` in the machine-local state dir): a Stop exit 2 makes Claude Code continue the turn, so a warning nothing in the turn can clear would otherwise repeat after every reply.

**Governed-path reminder.** `scripts/hooks/stop/03h-adr-scope-check.sh` covers the opposite gap: an Accepted ADR may list the paths it governs in an `**Applies to:**` header line (`skills/shared/adr/SKILL.md` § Applies To), and a session that touches one of them without touching the ADR is told once to re-read it (ADR-0039). Add the line when you write an ADR that constrains specific files.

### Learn Trigger Rule

`/devteam:learn` should not be treated as an end-of-session-only command — any point where work is about to leave the current session's context is a finalization signal worth checking. The canonical nudge implementation is `commands/merge.md` § Step 4 (checks `.dev-team-agents/.learn-last-run` against current `HEAD`, asks via `AskUserQuestion`; on Yes it runs the learn flow inline — see that step). The following commands carry the same check at their own closing point — patch all of them together if the mechanism ever changes:

| Command | Finalization point |
|---------|--------------------|
| `/devteam:merge` | Just before merging the working branch into the target, so learn commits ride into it (canonical implementation) |
| `/devteam:pr` | After `gh pr create` succeeds |
| `/devteam:refactor` | Session close, alongside the session-summary step |
| `/devteam:audit` | After the report is written, even on **Report only** |

Not every finalization point has a mechanical nudge — some triggers (recurring findings across sessions, a bug that took many iterations to isolate, a first-time integration with an external service) are real signals but have no persistent cross-session store to detect them from today. Do not invent one ad hoc inside a single command; that is a harness-level feature, not a per-command patch.

### Correction Pattern Rule

When the user corrects the same agent behavior **2 or more times in the same session** — pushing back on the same workflow choice, format, or default — that is a standing preference, not a one-off note for that task. Do not just comply silently a second time. Before continuing:

1. State the pattern you noticed in one sentence ("You've asked twice this session not to spawn a worktree — want this to be the default going forward?").
2. Check whether it maps to an existing field in `preferences.json` (see `skills/shared/user-preferences/SKILL.md` § Schema and Defaults) — most behavioral preferences already have one (`worktree_active`, `worktree_commit_action`, `qa_browser`, `language`, etc.).
3. Ask via `AskUserQuestion` whether to persist it. **Never write to `preferences.json` without this confirmation** — a correction scoped to the current task is not consent to change a standing default.
4. If confirmed, update the field and confirm the new value back to the user.

If the correction does not map to any existing field, do not invent a new preferences.json key on the spot — say so, and suggest the user phrase it as an explicit instruction for this session instead.

This rule does not replace the Session Summary Rule above — a corrected preference is still worth a line in **Decisions** if it shaped the session's work, even after being persisted to `preferences.json`.

### Stop Hook (Automated Enforcement)

`install.sh` registers `scripts/hooks/stop.sh` as the `Stop` dispatcher in `.claude/settings.json`, running every sub-script in `scripts/hooks/stop/` in order — including `01-session-summary.sh`, which detects missing session-summary entries and prompts for one. No manual setup is required.

→ See [`CLAUDE-md/hooks.md`](CLAUDE-md/hooks.md) for the Stop and PreToolUse sub-script conventions, the Session Start Banner echo rule, and the full hook files map.

---

<!-- dev-team-agents: commit-rule -->
## Commit Rule

When making a git commit for any task:

1. **Load `skills/shared/conventional-commits/SKILL.md`** before writing the commit message
2. **Defer to the project's own pattern first**: run `git log --oneline -10` and check whether the existing history follows Conventional Commits or a different format (e.g., GitHub-style `[feature]`, plain imperative, Jira ticket prefix). If a project-specific pattern is clearly in use, follow it instead.
3. **Never include Claude attribution**: no `Co-Authored-By: Claude`, no `🤖 Generated with Claude Code`, no AI tooling references in commit messages, PR titles, or PR bodies.
4. **Show the Work Summary Table** from the loaded skill's § Work Summary Table before presenting the commit plan — whether the commit is planned or executed directly.

---

## Push & CI Monitoring Rule

Before any push or merge the user asks for — by command or in plain language — run the **Dirty-Tree Pre-flight** (`skills/shared/git-workflow/SKILL.md`): uncommitted changes go through the `/devteam:commit` flow automatically, then the push or merge runs.

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

<!-- dev-team-agents: pre-compact-auto-summary -->
# Pre-compact Hook — Auto Session Summary
When `/compact` is blocked by the `pre-compact.sh` hook with the message "SESSION SUMMARY REQUIRED (pre-compact)", do the following **automatically, without asking the user**:

1. Read `.dev-team-agents/memory-dir` to find the session summary path (resolves to `.dev-team-agents/user-data/session-summary.md` on layout 1, `data/projects/<project_id>/session-summary.md` on layout 2). Write a new entry at the top using this format:
   ```
   ## YYYY-MM-DD HH:MM:SS | [brief task title]
   **Done**: what was implemented or changed

   **Decisions**: key choices made and why

   **Next**: what remains or is recommended next

   ---
   ```
   - Use today's date and current time
   - Base the content on the current conversation context
   - Always write in English
2. After writing, tell the user, in their configured language, that the session summary was written and to run `/compact` again to proceed.
