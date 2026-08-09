# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [2.35.1] - 2026-08-09

### Changed
- **`worktree` skill — unified naming rule made explicit**: worktree directory, branch, and (when Docker isolation applies) Docker Compose project/container names always derived from the same `<context>/<brief-title>` slug, but this was only implicit across `SKILL.md` and `docker-isolation.md`. Added an explicit "Unified naming" bullet to `SKILL.md` → Key Rules and a cross-reference in `docker-isolation.md`, so agents state the rule instead of inferring it.

## [2.35.0] - 2026-08-09

### Added
- **Full-suite test guard**: `skills/shared/scoped-test-execution/SKILL.md` (never run the full test suite without explicit user request) was only enforced inside `/devteam:*` agent routing, via `project-context`'s mandatory load — a plain main-loop session never triggered that load and could self-escalate to an unscoped full-suite run. `scripts/hooks/session-start.sh` now injects the rule unconditionally into every session, and a new `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` nudges (does not block, per this repo's PreToolUse convention) when a `Bash` command looks like an unscoped full-suite run (pytest/jest/phpunit/go test/gradle/flutter/cargo/rspec with no path/filter).

## [2.34.2] - 2026-08-08

### Fixed
- **`worktree` skill — teardown could destroy uncommitted work**: `git worktree remove` deletes uncommitted/untracked content silently, and the finalization flow (`references/branch-flow.md` Step 8) ran it right after merge with no check on working-tree state. A worktree with no commits — abandoned, or merged in a sibling worktree — lost all its edits on teardown with no warning. Finalization now runs `git status --porcelain` before removal; a dirty tree aborts teardown and asks the user (commit / discard / keep the worktree) instead of proceeding.

## [2.34.1] - 2026-08-08

### Fixed
- **`scripts/install.sh` — orphaned `.dev-team-agents.old.*` / `.new.*` swap directories**: the install/update swap (Step 2c) renamed the previous installation aside before removing it, but the final `rm -rf` was best-effort (`|| true`) and never retried, so a process killed mid-swap — or a failed removal on a locked/permission-denied file — left the backup on disk forever, with no warning. Install now self-heals any stray `.old.*`/`.new.*` directory from a previous interrupted run at startup, and `_cleanup()` retries the removal on exit and prints an explicit warning with the path if it still fails, instead of swallowing the error silently. `/devteam:health-check` Category 3 also now detects and removes any leftover swap directories as a safety net.

## [2.34.0] - 2026-08-08

### Added
- **`/devteam:sync-rules` — mode selection**: a new Step 2 asks via `AskUserQuestion` whether to apply every surviving candidate automatically ("Apply all automatically", recommended) or review each one individually, before scanning starts. `--all`/`--yes` still skips straight to all-mode without the quiz. Previously the command always confirmed one candidate at a time with no way to batch-apply.

## [2.33.0] - 2026-08-08

### Added
- **`/devteam:sync-rules` command** (`commands/sync-rules.md`) — scans `docs/` for conventions documented only in prose, dedupes against `docs/development/reuse-guidelines.md`, and runs `/devteam:rule`'s classify → propose → confirm → append routine per candidate. Fixes the gap where a documented convention (e.g. a response-envelope rule) never becomes a mechanically enforced registry row, so neither `reuse-lint.sh` nor the review gate can catch a violation.
- Wired into `install.sh` and `update.sh` (post-run suggestion to run the scan) and into `/devteam:health-check` Category 11, which now stays detection-only and points to the command instead of duplicating its classify/propose logic.

## [2.32.1] - 2026-08-08

### Fixed
- **`orchestration` skill — Spawn Integrity check 4 (Liveness)**: the orchestrator had no way to distinguish a subagent that was still executing from one that had silently stalled or died — its only signal was the final returned message, so a status question mid-run got answered from stale assumption. Now it notes spawn time, tries any available status/output check before answering, and states explicitly that completion can't be confirmed instead of asserting "still running".

### Added
- **`/devteam:commit` — Step 2.5 unrelated-changes quiz**: before staging, cross-references unstaged/untracked files against what was actually touched in today's session and asks via `AskUserQuestion` how to handle anything that doesn't match, instead of silently sweeping unrelated work into the commit plan.

## [2.31.0] - 2026-08-06

### Added
- **`data-fetching-integrity` skill** (`skills/architecture/data-fetching-integrity/SKILL.md`) — tool-agnostic gate for duplicate/redundant API calls in SPA/SSG frontends: symptom table (double-fire on mount, re-fetch on every render, siblings independently fetching the same resource, avoidable waterfalls, no de-dupe for concurrent identical requests, un-debounced fetch-on-input), root causes, and prevention rules.
- **New mandatory rule wired into `frontend-developer`, `frontend-reviewer`, and `qa-specialist`** — developer loads the skill before writing fetch logic, reviewer flags a match as `[BLOCKING]`, QA validates via the network panel as `[BLOCKER]`. Added as a pre-delivery item in `skills/shared/frontend-done-checklist/SKILL.md`.

## [2.30.2] - 2026-08-06

### Fixed
- **`/devteam:commit` no longer bundles `graphify-out/` regenerated output into the task's commit** — new "Graphify isolation" rule in `commands/commit.md` always splits any staged or unstaged `graphify-out/` changes into their own trailing `chore(graphify): ...` commit, after the task's other layered commits.

## [2.30.1] - 2026-08-06

### Fixed
- **PreCompact block now prompts instead of silently complying** — `CLAUDE-md/hooks.md` documents that `pre-compact.sh` can only emit plain text, so on its "SESSION SUMMARY REQUIRED" block Claude must use `AskUserQuestion` (generate automatically / write it myself / show a draft first) instead of writing the entry without asking.

## [2.30.0] - 2026-08-06

### Added
- **`/devteam:push` command** — thin wrapper around `skills/shared/github-actions/SKILL.md`; asks a CI/CD-aware quiz (watch CI + auto-fix vs. push-only vs. other) when GitHub Actions is configured, otherwise pushes normally. `plan_gate: opt_out`.
- **CI/CD-aware quiz before pushing** — `skills/shared/github-actions/SKILL.md` now asks the user (via `AskUserQuestion`) whether to watch CI or just push, instead of always watching. The same quiz gates the push triggered by `/devteam:pr`'s `gh pr create`.
- **`ci_cd_detected` preference** — caches the GitHub Actions detection result in `preferences.json` (`null` = unchecked, `true` trusted as-is, `false` always rechecked).
- **Push as a session-summary finalization signal** — `/devteam:push` and the push inside `/devteam:pr` now write today's `session-summary.md` entry right after a successful push if one is missing, instead of waiting for session end.

## [2.29.0] - 2026-08-03

### Added
- **Health check staleness notification** — `session-start.sh` now warns when `/devteam:health-check` hasn't run in over `docs_stale_after_days`, or has never been recorded on a project already in motion. `/devteam:health-check` (Step 4) and `setup-health-check/SKILL.md` (Flow step 5) now write today's date to `.dev-team-agents/user-data/.last-health-check` on every run.
- **Uncommitted-progress warning** — `stop/04-notifier.sh` fires a one-time-per-session `warning` when the turn count passes the new `session_no_commit_turns` preference (default `8`) with a dirty working tree and no commit since the session started (tracked via `.dev-team-agents/user-data/.session-head`, written by `session-start.sh`). Catches the case where a crash, `/clear`, or context compaction would lose the most.

## [2.28.1] - 2026-08-03

### Fixed
- **Context-window warnings (`context_window_percent_warning`/`_limit`) now fire in purely conversational sessions** — `stop/04-notifier.sh`'s `DEVTEAM_NO_CHANGES` fast-path used to skip the entire context estimation block whenever no file changed, so sessions with no edits never got warned no matter how full the context actually was. The fast-path now only skips the once-per-day tip lookup.
- **Context-window estimation is now exact instead of a compensated heuristic** — the transcript-based method used to sum `input_tokens + output_tokens` across every turn and apply `transcript_multiplier` (1.8) to correct for the resulting drift; because of prompt caching each turn's `input_tokens` already includes the full prior conversation, so the sum silently double-counted history and grew unboundedly. It now reads only the LAST usage entry's `cache_read_input_tokens + cache_creation_input_tokens + input_tokens` — the exact context size sent on the most recent API call. `transcript_multiplier` is deprecated (no-op, kept for backward-compat reads) and documented as such across `notifications.md`, `preferences.md`, `user-preferences/SKILL.md`, and both installation guides.
- **opencode sessions now get the same accurate context estimation as Claude Code** — `opencode/plugin/dev-team-agents.ts` used to invoke `stop.sh` with no stdin at all on `session.idle`, so the transcript-based method could never activate there and every opencode session silently used the coarse turn-count fallback. The plugin now fetches the last assistant message's token usage via `client.session.messages()` and passes a synthetic transcript payload shaped like Claude's, requiring no change to the shared bash parsing. Codex needed no change — its usage schema already parses correctly under the same keys.
- **`auto_update` no longer fails silently when `.installed-version` is missing or corrupted** — `pre-tool-use/01-check-updates.sh` used to `exit 0` with zero diagnostic; it now prints a message pointing at `/devteam:health-check`.
- **Auto-update no longer reports success when it actually failed** — the "updated to $latest" notification used to fire unconditionally even when `uc_perform_auto_update` failed (e.g. a partial install missing `installer-fetch.sh`); it now checks the return code and falls back to the "update available" notice on failure.

## [2.28.0] - 2026-08-03

### Added
- **Token economy in subagent delegation** — `skills/architecture/orchestration/SKILL.md` gains two mandatory rules: Subagent Report Economy (every spawn prompt must instruct the subagent to close with a concise report — no dumped file contents, command logs, or step-by-step narration — since a subagent's final message is the only thing that reaches the orchestrator's context) and Spawn Prompt Economy (pass condensed, already-synthesized project context instead of a re-read instruction, and reference an on-disk plan by file path + section instead of pasting the full plan into every parallel spawn)

### Changed
- **`project-context/SKILL.md` split for lighter per-agent loads** — First-Time Setup Guard, Session Summary Write Rules, and the Immutability Warning moved to `skills/shared/project-context/references/`, loaded only on their trigger condition instead of unconditionally on every load; the always-loaded body drops from 372 to 297 lines with no loss of coverage

## [2.27.3] - 2026-08-03

### Added
- **Python 3 is now documented as a prerequisite** and checked as a non-blocking warning — `install.sh` warns with OS-specific install instructions (macOS/Linux/Windows) when `python3` is missing instead of failing silently later; `/devteam:health-check` gained Category 12 (Python Prerequisite) with the same warn-only behavior; `README.md`/`README.pt-BR.md` document it in a new Prerequisites section

## [2.27.2] - 2026-08-03

### Fixed
- **`install.sh`'s directory swap now falls back to copy+delete when a rename fails even after retries** — v2.27.1's retry-only fix assumed transient locks, but on WSL a project under `/mnt/<drive>/...` (DrvFs) can fail a whole-directory `rename()` reliably, with nothing locked. `_mv_or_copy` tries the retried rename first and falls back to an explicit `cp -R` + `rm -rf` before giving up; the error message now also names DrvFs as a possible cause on `/mnt/` paths

## [2.27.1] - 2026-08-03

### Fixed
- **`install.sh` retries the directory renames used to swap `.dev-team-agents` into place** — on Windows a single locked file (open editor, terminal `cd`'d into the folder, antivirus real-time scan) could fail the whole-directory `mv` and abort the update; the swap now retries up to 5 times with a 1s backoff before failing, and the resulting error message names the exact directory and likely causes instead of a raw `mv` permission error
- **`graphify-refresh.sh`'s change-detection gate is no longer defeated by `SIGPIPE` under `pipefail`** — `grep -q` closing the pipe on `git log`/`git diff` made the gate silently skip rebuilds, and the output swap could abort silently on macOS's deny-delete ACL on `graphify-out/cache`, losing the freshly built graph; both failure modes exited 0, so the graph went stale with no visible signal. Health check Category 5 now validates `graphify.json` content and every `targetPaths`/`manifestPaths` entry, checks output integrity, and actually runs the refresh script to confirm it rebuilds instead of trusting that `graphify-out/` exists

## [2.27.0] - 2026-08-02

### Added — Consistency-loop fixes across coding and design agents
- **`reuse-guidelines` is now consulted before creating, not just at review time** — `frontend-developer`, `ui-ux-designer`, `backend-developer`, `database-specialist`, `devops-specialist`, `mobile-developer`, and `software-architect` all check `docs/development/reuse-guidelines.md` for a canonical implementation before proposing anything new
- **`ui-ux-designer` auto-switches to Consultive Mode** after `frontend-developer` reports UI changes in the same session, instead of waiting to be asked
- **`software-architect` gained a live Consultive Mode alongside `backend-developer`**, flagging `[ARCH-DEVIATION]` in-session instead of only at the post-hoc Quality Gate; `backend-developer`'s done-checklist now requires resolving it first
- **`design-system-audit`'s Design Mode template now fits the 80-line cap** enforced by `docs-sync` for `docs/design/design-system.md`, instead of a template that could never fit it
- **New non-blocking `design-token-lint` Stop hook** reports hardcoded CSS `px` values outside `var(--...)` tokens as a nudge, without blocking the session
- **ADR creation now checks for an existing ADR on the same topic first** — `skills/shared/adr/SKILL.md` gained a Check Before Creating step, `/devteam:adr` loads it before scaffolding, and `new-adr.sh` prints existing ADR titles as a mechanical reminder, closing a gap where `/devteam:adr`, `/devteam:learn`, and `software-architect` could each independently create a duplicate ADR for the same decision

## [2.26.0] - 2026-08-02

### Added — Spec layer between overview and sprints, with a living-spec amendment protocol
- **`product-analyst` now writes one testable spec per feature** (`docs/specs/<feature>.md`, `Given/When/Then` acceptance criteria, `touches`/`depends_on`) before generating sprints, using the new `templates/spec-template.md` and `skills/shared/spec-gate/SKILL.md`
- **A mechanical gate auto-spawns `software-architect`** to write `<feature>-contract.md` whenever a spec's `touches` field spans more than one layer or introduces a new API/schema — no user request needed
- **Execution agents and `qa-specialist` now treat the linked spec as the implementation and validation boundary**, asking rather than assuming when something isn't covered, instead of re-interpreting the sprint task text
- **A Living Spec amendment protocol keeps the spec current after implementation**: business-level divergence is amended in place by the executing agent, interface-level divergence goes through `software-architect`, and every amendment is logged in the spec's new `Amendment Log` section
- **A Spec Sync Gate at the end of work** has `qa-specialist` verify the spec still matches what was built and every amendment carries a reason, tagging drift `[SPEC-DRIFT]` and treating it as a `[BLOCKER]`
- **A hard gate blocks marking a feature done while an open assumption remains** — every assumption must resolve to an answered question, a spec amendment, or an explicit blocker before hand-off, enforced by `qa-specialist`'s Definition of Done check
- **A new `skills/shared/feature-learn/SKILL.md` fires automatically at the end of `backend`/`frontend`/`fullstack`/`mobile` sessions**, promoting spec amendments and non-obvious findings into docs, wiki, or an ADR (scoped mirror of `/devteam:learn`) so knowledge compounds feature-to-feature instead of aging unpromoted in `session-summary.md`

## [2.24.7] - 2026-08-02

### Fixed — Codex now routes guided choices through `request_user_input` and audits that generation
- **The Codex renderer now maps `AskUserQuestion` explicitly to `request_user_input` in Plan mode and rewrites quiz payload examples into the Codex shape.** Generated Codex command skills now preserve structured choice payloads in a form the runtime can actually consume instead of only describing an abstract quiz flow
- **Codex no longer silently degrades guided choices into inline prose when the session is outside Plan mode.** The rendered instructions now require a `/plan` retry when `request_user_input` is unavailable, so commands that depend on interactive branching stop pretending to offer a native chooser they cannot render
- **`/devteam:health-check` now verifies the new Codex quiz generation explicitly.** The Codex provider checks inspect rendered skills for `request_user_input`, `/plan` retry guidance, and absence of the old plain-text-degrade wording, then repair drift by re-running `install-codex.sh`

## [2.24.6] - 2026-08-02

### Fixed — Codex preserves structured quizzes and provider rewrites stay isolated
- **The Codex renderer no longer flattens `AskUserQuestion` flows into plain-text prompts or strips quiz JSON blocks.** Rendered Codex skills and agents now preserve the original structured choice flow so dynamic quizzes, confirmation gates, and guided branching survive the provider adaptation
- **Codex tool-convention notes now instruct the runtime to use structured user input whenever the current surface exposes it, with plain-text fallback only as a last resort.** This aligns the generated artifacts with the actual Codex app/runtime behavior instead of hard-coding a degraded interaction model
- **The opencode agent renderer no longer passes through Codex-only body rewrites.** This removes a real cross-provider leakage bug in the render pipeline and keeps provider-specific adaptations scoped to the intended target

## [2.24.5] - 2026-08-02

### Changed — Codex now standardizes on `$devteam-*` only
- **The Codex renderer and installer no longer treat `/prompts:` as a supported command surface.** Rendered Codex commands now exist only as project-local skills under `.codex/skills/devteam-*/SKILL.md`, and the surrounding command-map/docs text was updated to make `$devteam-*` the sole official invocation path
- **Legacy prompt aliases are now handled only as drift cleanup.** `install-codex.sh`, the health-check references, and the compatibility notes still detect and remove old `.codex/prompts/devteam-*.md` leftovers, but the harness no longer offers or documents prompt alias installation as part of normal Codex usage

### Fixed — `devteam:commit` no longer dead-ends on unstaged-only changes
- **When a project has modified files but nothing staged, `/devteam:commit` now routes through a structured decision instead of stopping on a plain-text blocker.** The command asks whether it should stage everything and commit, just show the commit plan, or abort
- **Re-running `install-codex.sh` from the project's own `.dev-team-agents` copy now works.** The materialized runtime now includes the minimal render plumbing required for `--source .dev-team-agents`, skips self-copy loops safely, and bootstraps the notifier state files expected by hooks and health-checks

## [2.24.4] - 2026-08-02

### Fixed — Codex CI fixtures no longer expect the removed project-local prompt directory
- **The slim-bootstrap contract test now validates the installed Codex project shape against command skills, not `.codex/prompts/`.** The skills-first migration intentionally stopped creating project-local `devteam-*.md` prompt files, but the bootstrap assertion still `find`ed that directory and failed even when the install was correct
- **The Codex installed-fixture validator now requires `.codex/skills/devteam-*` and rejects leftover `.codex/prompts/devteam-*.md` files.** This brings CI in line with the new installer behavior and catches regressions back to the legacy layout instead of enshrining it

## [2.24.3] - 2026-08-02

### Fixed — Codex installs now converge old projects to the new skills-first layout
- **`install-codex.sh` now removes legacy project-local prompt aliases under `.codex/prompts/`** when refreshing a project. Older Codex installs kept `/prompts:devteam-*` files inside the repo; re-running the installer now migrates them to the supported shape: project-local `$devteam-*` skills in `.codex/skills/`, with `/prompts:devteam-*` available only as optional user-local aliases in `~/.codex/prompts`
- **`update.sh` now re-runs the Codex installer when a project has `.codex/` config**, just as it already did for opencode. That means `/devteam:update` now repairs stale Codex layouts and refreshes generated agents, hooks, and command skills instead of leaving Codex installs partially outdated
- **The Codex health-check now treats project-local `.codex/prompts/devteam-*.md` files as legacy drift**, so it can point the user to the canonical repair path instead of accepting the old layout as healthy

## [2.24.2] - 2026-08-02

### Fixed — the Codex port now matches the runtime that actually executes the harness
- **Codex command prompts no longer pretend to pin runtime model/effort.** In Codex, those settings apply to `.codex/agents/*.toml`, not to `.codex/prompts/*.md`; the renderer now keeps prompt metadata informational and leaves the enforcement to the spawned agents
- **The Codex renderer no longer emits invalid quiz-tool instructions.** Claude-specific `AskUserQuestion` phrasing and embedded quiz JSON are rewritten into direct plain-text questioning so the rendered Codex artifacts stop referring to nonexistent tool calls
- **The Codex compatibility checker now validates the artifacts the port actually ships.** It scans prompts, agents, and generated skills, and fails on stale pseudo-tool residues and misleading prompt model metadata

### Added — a skills-first Codex entrypoint alongside the legacy prompt surface
- **Every Codex command now renders twice:** as the existing compatibility prompt `/prompts:devteam-<name>` and as an explicit skill `$devteam-<name>`
- **`install-codex.sh` now installs both entrypoints** and documents `$devteam-*` as the forward-compatible path while keeping `/prompts:devteam-*` available
- **The setup-health-check references now validate the full Codex install shape** — hooks, generated prompts, generated `$devteam-*` skills, and `.codex/agents/*.toml` `model` / `model_reasoning_effort` against `tiers.json` including `agent_effort` overrides

## [2.24.1] - 2026-08-02

### Fixed — the opencode installer silently produced an empty command block
- **`install-opencode.sh` handed the whole command snippet to `jq` as an exec argument** (`jq --argjson new "$CLEAN_JSON"`). Every command body is embedded in that JSON as a `template` string, so it grows with the roster — adding `/devteam:explain` pushed it past `ARG_MAX` and the merge died with `jq: Argument list too long`, leaving `.opencode/opencode.json` with `"command": {}`
- **The snippet now reaches `jq` through a temp file, read with `--slurpfile`**, which has no size ceiling
- **`v2.24.0` carries the defect**: an opencode install from that tag registers zero slash commands. Use `v2.24.1` instead. Claude Code and Codex installs are unaffected — neither path goes through this merge
- Caught by the two CI jobs that exist for exactly this, `slim-bootstrap` and the opencode installed-fixture validator; both now report 26 commands

## [2.24.0] - 2026-08-02

### Added — `/devteam:explain`, a glossary you can reach without leaving the session
- **`/devteam:explain SPA` or `/devteam:explain SPA, SSR, tenant, middleware`** — explains a term, acronym, or piece of jargon that came up in the conversation. Acronyms and initialisms are always expanded on the heading line; every term gets what it is, **the problem it solves**, and a concrete example — a code block in the project's own language when the concept is a code concept
- **Short by design.** Two sentences for the definition, one or two for the problem, the shortest example that shows the point, and an explicit list of things never to write — no opening line about the question, no restatement of what was asked, no closing summary, no "the topic goes deeper than this" caveat
- **It draws when the term is a shape.** A fenced `mermaid` block for a flow (middleware, CI pipeline), an exchange between parties (OAuth, webhook), containment (multi-tenancy, subnets), or a lifecycle (saga, order status) — capped at three to seven nodes, with edges labelled by what actually moves. It deliberately does **not** draw for a definition, a property, or a convention (`idempotent`, `DTO`, `camelCase`): a box with the word inside it teaches nothing and makes a short answer feel long, which is the failure the command exists to avoid
- **It answers in the main context and spawns no agent.** That is the point, not an omission: the terms come from the live session, and a subagent receives only the prompt text — it would lose the message where the term appeared, the file it was about, and the decision it belonged to. The command grounds each term in the session first, the repository second (citing `file:line`), and only then explains it generically
- **It always closes by offering an interactive quiz** — application questions rather than recall, one at a time, each wrong option a real misconception, and feedback that names the misconception instead of just pointing at the right letter
- Joins `update`, `symlinks` and `health-check` as a row whose `agent` is filler; it is `conditional` on the plan gate and, like `/devteam:review`, carries no plan-gate step because it writes nothing

### Added — commands can pin their model on Claude Code
- **`commands/<name>.md` may now open with a YAML frontmatter block, and `model:` in it pins that command's body.** Until now `commands.json` `tier` was inert on Claude Code, which symlinks command bodies and never passes them through the render engine — the tier only ever took effect on opencode and Codex
- **The seven `repetitive` commands** (`docs`, `pr`, `commit`, `learn`, `update`, `symlinks`, `health-check`) carry `model: haiku`. The other eighteen carry no key and keep inheriting the session
- **Restricted to `repetitive` on purpose, with the argument that already keeps `effort:` sparse:** the key *overrides* the session's model. Pinning `/devteam:plan` to `opus` would silently undo a user who lowered the session for cost; a `haiku` pin can only ever cost less than what they chose. `/devteam:explain` is `repetitive` and deliberately carries **no** pin — its output is a teaching explanation grounded in the user's own code, and the session model is the one they picked for that
- **`check_command_roster()` in `helpers/agent-lint.sh` now enforces it** — a pin outside `repetitive` fails, and a pin inside it must equal `tiers.json.repetitive.claude`. Presence is permitted, not required. All three branches were negative-tested
- The `commands.json` `_comment` had stated the opposite (*"do NOT add frontmatter to commands/*.md directly — Claude Code parses them as body-only"*). Claude Code does read command frontmatter; the note is replaced by `_claude_model_pin`, which records the rule and the reasoning

### Fixed
- **The renderer now strips command frontmatter before emitting the opencode template and the Codex prompt.** Command bodies were read with a raw `read_text()`, so the new YAML block would have been emitted as literal text at the head of every `template` string and every Codex prompt. `render_command_claude` still re-reads the source file, so Claude receives it byte-identical — verified against the CI contract checker on all three providers

## [2.23.2] - 2026-08-01

### Fixed — two `commands.json` rows ran an agent on a model that was not its own
- **`tester` was `tier: repetitive` while its lead `backend-test-specialist` is `backend-exec`** — which also contradicted the `CLAUDE.md` rule against putting a test agent on that tier. On opencode the command rendered `kimi-k2.5` for an agent whose own file declares `kimi-k2.7-code`
- **`health-check` was `tier: backend-exec` while naming `setup-assistant`, a `reasoning` agent.** The command spawns no agent at all — the field is filler the renderer requires — so it now names `technical-writer` at `repetitive`, matching `update` and `symlinks`, the two other `opt_out` runners
- **The fields are not independent knobs.** On opencode the snippet's `agent` makes the command run *as* that agent while `model` comes from the **command's** tier. 23 of the 25 rows already mirrored their lead agent's tier; the rule was simply never written down or checked

### Added
- **`check_command_roster()` in `helpers/agent-lint.sh`** — every command's `agent` must exist in `agents/`, and its `tier` must equal that agent's tier. The CI contract checker validates the *rendered* output and only catches a dangling ref, so the source-side rule lives in the lint, alongside the orchestration-roster check that exists for the same reason
- **`_tier_rule` and `_filler_agent_note` in `scripts/lib/commands.json`**, and the matching rule in `CLAUDE.md` next to the command table

### Fixed — commands ignored their lead agent's effort override
- **The same defect on the effort axis.** `resolve_effort()` was called with `agent=None` for commands, so a command took its tier's effort and skipped the `agent_effort` override of the agent it runs as. `devteam:tester`, `devteam:dba`, `devops` and `qa` rendered `default`/`medium` for agents that declare `low`
- **The renderer now passes the lead agent from `commands.json`.** All 25 commands render an effort that matches the agent they run as — verified across opencode and Codex
- `tester` had been masking this: its old (wrong) `repetitive` tier produced `low` by accident, so fixing the model exposed the effort mismatch that was underneath

## [2.23.1] - 2026-08-01

### Changed — the run banner says `session-default` instead of `inherit`
- **An agent that sets no `effort:` key showed `inherit` in its banner**, which names the mechanism rather than telling the reader what the agent is running at. The 11 agents in `reasoning`, `backend-exec` and `frontend` now show `session-default`; the 6 carrying `effort: low` are unchanged
- **Showing the resolved level was rejected, not overlooked.** The session's effort is not knowable at render time, and `skills/shared/model-identity/SKILL.md` forbids an agent from resolving its own identity at runtime — so the fix is a clearer label for the same semantics, not new information
- **The label is hyphenated on purpose.** `helpers/agent-lint.sh` strips spaces from the banner cell before comparing, so a two-word label would have to be matched as `sessiondefault` and would read like a typo to whoever touches that check next
- Propagated to `helpers/agent-lint.sh`, `skills/shared/model-identity/SKILL.md`, `CLAUDE.md`, `docs/providers.md`, and the `render_run_banner()` fallback in `scripts/lib/render_provider.py`. `inherit` stays in prose describing the **frontmatter** mechanism, where inheritance is still the accurate word

### Fixed
- **The `CLAUDE.md` run-banner example showed a third value**, an em dash, while every agent showed `inherit`. It is now aligned with the 11 agents it documents

### Added — why `qa-specialist` takes low effort and the reviewers do not
- **`agent_effort` carried a note for the agent it excludes (`security-specialist`) but none for the one that looks like it should have been excluded too.** `_why_qa_specialist` in `scripts/lib/tiers.json` records the dividing line: not whether the role inspects code, but whether the agent is **handed what to check**. QA validates observable behavior against acceptance criteria written before it ran; review and security audit exist to surface what nobody wrote down, and that exploration is exactly what `low` cuts
- The same test is summarized in `CLAUDE.md` next to the `agent_effort` description, so it is applied before adding an agent to the map rather than after

## [2.23.0] - 2026-08-01

### Changed — versioning policy now describes what the repo actually does
- **"Breaking changes (agent behavior changes, removed skills) → major" was never applied literally.** Read as written it makes nearly every release a major; in practice `v2.20.2` shipped a new mandatory emission for all 17 agents as a **patch** and `v2.21.0` changed how five specialists reason as a **minor**
- `CLAUDE-md/versioning.md` now spells out the three tiers with the real tags as examples, and states the test that decides a major: **does an existing installation behave differently after an update without its user asking?** Changed values in `preferences-defaults.json` do not qualify on their own, because an existing `preferences.json` is never rewritten

### Changed — default `preferences.json` values (fresh installs only)
- **`language` `en` → `pt-BR`, `auto_update` `false` → `true`, `worktree_active` `false` → `true`, `telemetry` `false` → `true`** in `scripts/lib/preferences-defaults.json`. These apply **only to a `preferences.json` that does not exist yet** — an existing file is still never rewritten, and neither is `credentials.local.json`
- **The installer still asks.** The language prompt now defaults to `[pt-BR]`, and the telemetry consent gate is unchanged: no terminal, `DEVTEAM_NONINTERACTIVE=1`, `n`, or 60s of silence all still write `telemetry: false`. Silence is still not consent

### Fixed — the default schema had drifted across five copies
- **`qa_browser` was missing** from the no-python3 fallback heredoc in `install.sh`, which also hardcoded `worktree_active: false` independently of the schema
- **`telemetry` was inverted** between `skills/shared/user-preferences/SKILL.md` (`true`) and the canonical file (`false`)
- **The health check validated a stale 9-field list**, silently passing files missing eight fields. It now reads the required set from `preferences-defaults.json` instead of hardcoding it
- **`skills/shared/project-context/SKILL.md` hand-wrote a 12-field copy** in its first-run path. It now copies the canonical file rather than retyping the JSON
- **`CLAUDE.md` now names the canonical file and lists every mirror** that cannot read it, so the next key change touches all of them

### Fixed — a backfill could switch telemetry and auto-update on without consent
- **`telemetry` and `auto_update` are now `CONSENT_KEYS`.** When either is absent from an **existing** `preferences.json`, both `install.sh` and `scripts/hooks/session-start.sh` write `false` rather than the schema's `true`. That file's owner never saw a prompt for a field added after they installed, so an absent key means "no"
- **This resolves a disagreement `CLAUDE-md/preferences.md` had recorded as an open question.** The fail-closed read path in `telemetry-guard.sh` treats a missing key as disabled, while the backfill would write the schema default and flip it to enabled at the next session start. The fix was the backfill, not the schema value — a fresh install should still default to enabled, subject to the prompt
- **The legacy `.auto-update` flag file still wins.** An install carrying it opted in explicitly, so the consent guard does not read its missing `auto_update` key as a revocation

### Fixed — an orchestrator could report spawns that never happened
- **Observed in the wild:** a `software-architect` run reported spawning `test-author` and `frontend-test-specialist` and said it was "waiting on the consolidated summary", while the UI showed no running task — no side panel, no animated logo, no pulsing bullet. `test-author` **does not exist** in this repo. Nothing had been spawned; the narration was invented
- **`skills/architecture/orchestration/SKILL.md` gained a `## Spawn Integrity` section** with three ordered checks: (1) **preflight** — if the Task tool is not in your tool list, stop and say so; never describe what the subagents would have done, which matters most for a nested orchestrator that may not have the tool at all; (2) **name validation** — `subagent_type` must appear verbatim in the Agent Roster, never inferred from the role; (3) **evidence** — a subagent's run banner arrives only in its final message, so no banner returned means it did not run
- **The consolidated-summary template was inviting the failure.** `### Agents spawned` / `[list of agents and what they did]` asks for a list from memory and accepts one written by an orchestrator that spawned nobody. It is now a table whose Model column is filled from the **returned** banner, with `NOT RUN` for any agent that returned none — and an all-`NOT RUN` result must be stated as the headline, not buried
- **`helpers/agent-lint.sh` now validates the roster against `agents/`** in both directions: a row naming a nonexistent agent, a row whose tier contradicts the agent's frontmatter, or an agent missing from the roster entirely (with `software-architect` and `setup-assistant` exempt — the orchestrator itself and the user-invoked onboarding agent). Verified against all three failure modes rather than assumed
- **Fixed the drift this check immediately caught:** the roster listed `backend-test-specialist` as tier `repetitive`, contradicting both its frontmatter and the explicit rule in `CLAUDE.md` that test authoring is not low-judgment work

### Fixed — subagents ran the full test suite despite `scoped-test-execution`
- **The rule was opt-in and reached 5 of 17 agents.** Nothing instructed a full-suite run; the leak was by omission. `frontend-developer`, `database-specialist`, the three reviewers and `software-architect` never loaded the skill
- **It is now part of the Foundational Rule.** `skills/shared/project-context/SKILL.md` carries a `## Test Execution — Scoped by Default` section, so every agent reaches it through the skill it already loads first. Fixing this centrally, rather than in twelve agent bodies, also kept `devops-specialist` (at the 211-line ceiling) from needing to grow
- **Orchestrators were propagating the problem.** `skills/architecture/orchestration/SKILL.md` now forbids passing "run the tests" unqualified into a spawn prompt, or instructing a full-suite run unless the user asked for one this session
- **Where the rule already existed, it was a checkbox on line ~157** of a 200-line body — passive, and read last. The two agents phrasing it that way (`backend-developer`, `mobile-developer`) now use the imperative "load before invoking any test runner" form that the compliant agents already used
- **The CI carve-out is explicit.** This governs local runs only; a pipeline still executes 100% of the suite and must never be narrowed to satisfy the rule

## [2.22.2] - 2026-07-31

### Fixed — the v2.22.1 compliance measurement was wrong, and so was the diagnosis it rested on
- **The real opening-banner rate is 14 of 16, not 13 of 13.** v2.22.1 classified every no-banner subagent transcript as a generic inline spawn by reading its prompt text (`You are implementing **Wave 1** of…`) instead of the `subagent_type` that produced it. Correlating each transcript with its spawning `Agent` tool call shows two of those were **dev-team agents that failed to emit**: `frontend-developer` and `database-specialist`
- **Both misses share a shape:** they were spawned *by another agent* with a long, directive task prompt, and their first action was to start the work (`Now let's write the core modules.`). The same pressure that loses the closing banner after a long task also loses the opening one when a strong task prompt arrives up front. `skills/shared/model-identity/SKILL.md` now says so explicitly
- **The v2.22.1 fix is unaffected** — it targets the closing banner, which was and remains 0 of 6. It does not address these two opening misses, which fail for a different reason
- **Corrected in `CHANGELOG.md`, `CLAUDE.md` and the model-identity skill.** The v2.22.1 entry keeps a pointer to this one rather than being silently rewritten
- **Method note worth keeping:** a subagent's prompt text says nothing about which agent definition ran it. Attribute transcripts through the `subagent_type` on the spawning `Agent` call, or the numbers are guesses

## [2.22.1] - 2026-07-31

### Fixed — the closing run banner from v2.20.2 was never actually emitted
- **Measured against live sessions, not assumed.** Across `navicms` and `site-prefeituras` on v2.22.0: the opening banner appeared in **14 of 16** dev-team agent runs, and the closing one in **0 of 6** runs that produced more than one message. Runs of 2, 3, 4, 6, 13 and 22 messages all opened with the banner and none closed with it; `Ran on:` appeared nowhere. (This line originally read "13 of 13" — see v2.22.2 for why that was wrong)
- **The v2.20.2 wording was not the problem — its position was.** Stating the requirement in `## Model Identity` at the top of the body means it has to survive the entire task; after a 22-message run it is long gone. Agents now carry a **`## Before You Finish`** section as the last thing in the body, so the requirement is the last instruction read before the summary is composed
- **`agent-lint.sh` enforces both presence and position**, because a section that works by recency stops working the moment someone appends another one below it. Adding a section to an agent now means adding it *above* that one
- **Earlier "success" readings were false positives.** Three runs looked compliant because the banner appeared in both the first and last message — they were single-message runs where those are the same text. Only runs with a genuinely separate summary test this
- **`helpers/size-limits.sh`: agent ceiling 205 → 211**, the exact size of the now-11-line mandatory model-identity boilerplate. The comment states the rule that survives this: raise it only for a new block required of every agent, by exactly that block's size, and never to make one long agent fit

## [2.22.0] - 2026-07-31

### Changed — the five specialists now run at low effort on opencode and Codex too
- **`agent_effort` entries gained `codex` and `opencode` keys.** v2.21.0 scoped the override to `claude`, leaving the same five agents on their tier defaults elsewhere; they now drop to `low` on all three providers. `qa-specialist` renders `variant: low` on opencode and `model_reasoning_effort = "low"` on Codex, against tier defaults of `default` and `medium`
- **A provider omitted from an entry still falls back to its tier level**, so the map can be rolled out one provider at a time — that is what made this a two-step change rather than a rewrite
- **`security-specialist` remains excluded** and keeps its `reasoning` tier level: `high` on both opencode and Codex
- Both values were checked against the contract's allowed sets before landing — `low` is in `CODEX_EFFORTS` and in the opencode effort set, and `check_tiers_completeness` validates column presence per tier rather than the rendered effort, so a per-agent override does not conflict with it

## [2.21.0] - 2026-07-31

### Added — per-agent effort overrides, and `low` on five specialists
- **New `agent_effort` map in `scripts/lib/tiers.json`**, keyed by agent name then provider, resolved ahead of the tier-level `effort`. Effort tracks how much a role needs to *reason*, which does not always follow the tier that picks its model — so it could not be expressed in a tier→effort map alone
- **`effort: low` on `backend-test-specialist`, `frontend-test-specialist`, `database-specialist`, `devops-specialist` and `qa-specialist`.** These roles carry detailed instructions and work largely to spec, so the extra exploration higher effort buys does not pay for itself
- **`security-specialist` is deliberately excluded, and the reason is recorded in `tiers.json` next to the map.** Low effort means fewer, more consolidated tool calls and less exploration before answering; in a security audit that exploration *is* the product, and cutting it is how a finding goes unreported. The exclusion is a decision, not an oversight — the note is there so the next person to notice the gap does not "fix" it
- **Scoped to the `claude` column.** opencode and Codex keep their tier-level effort — `qa-specialist` still renders `variant: default` on opencode
- **`agent-lint.sh` resolves the same precedence** and fails both on a mismatched effort and on an effort set where neither the agent nor its tier defines one. The lookup keys on the filename stem, which is the name the renderer uses, so the two cannot disagree

## [2.20.2] - 2026-07-31

### Fixed — the run banner never reached the main conversation from a background subagent
- **A subagent returns only its summary; everything before that stays in its own context.** The banner was emitted once, opening the agent's first response, so it reached the user only while the agent ran in the *foreground*. Claude Code runs subagents in the **background by default from v2.1.198**, which turned the banner into something visible only by opening the agent's transcript via `/tasks` — defeating the point of having one
- **Agents now emit the banner twice**: opening the first response, and closing the summary they hand back, under a `**Ran on:**` heading. The second emission is the load-bearing one — it is the only one that lands where the user is actually reading
- **Still exactly twice.** Not after every tool call and not between phases: those intermediate messages never leave the agent's context, so a banner there is pure noise
- This was a design gap in v2.20.0, not a regression. On Claude Code 2.1.140 and earlier the foreground default masked it; the failure would have appeared silently on upgrade

## [2.20.1] - 2026-07-31

### Fixed — Claude Code does support per-subagent effort; v2.20.0 said it did not
- **The claim was checked against the docs and was wrong.** `tiers.json`, `CLAUDE.md`, `docs/providers.md` and the model-identity skill all stated that Claude Code has no effort concept, and the run banner printed `—` in the Effort column. Claude Code accepts an `effort:` frontmatter key on subagents (`low` … `max`)
- **`repetitive` now sets `effort: low`** — bounded, low-judgment work where the saving is unambiguous, on top of the Haiku move. **No other tier sets it**, deliberately: the key *overrides* the session's effort level, so setting it everywhere would silently undo a user who lowered effort for cost or latency. Omitted means the agent inherits the session, which is the right default
- **The banner's Effort column now reads `inherit`** on tiers that set none, instead of `—`, which is what the agent actually runs at
- **`agent-lint.sh` guards the new key in both directions:** an agent whose tier defines an effort must carry it and match, and an agent whose tier does not must not carry one at all

### Fixed — a `set -o pipefail` interaction that made the linter exit silently
- **`grep` returning 1 inside a command substitution killed the whole script.** `effort:` is absent on 16 of 17 agents, so `effort_fm=$(… | grep -E "^effort:" | …)` failed the pipeline, `set -e` fired, and the linter exited 1 having printed nothing — no findings, no error, no clue
- **The same latent bug sat in the banner lookup.** An agent with no `<!-- run-banner -->` block would have crashed the linter instead of reporting the missing block — the exact condition that check exists to catch. Both now end in `|| true`

### Verified — model aliases are accepted by Claude Code
- Confirmed on two independent sources: the subagent frontmatter reference (`sonnet`, `opus`, `haiku`, `fable`, a full model ID, or `inherit`), and the installed 2.1.140 binary, which carries the `opus` / `sonnet` / `haiku` / `inherit` literals. `fable` is **absent** from that build, which reinforces the earlier decision to keep it out of the tier map
- **Documented two ways the banner can be out of step with reality.** The frontmatter `model:` is only the third source Claude Code consults, after `CLAUDE_CODE_SUBAGENT_MODEL` and any per-invocation `model` parameter; and an org `availableModels` allowlist makes it silently fall back to the inherited model. The banner reports configured intent, not the runtime's final choice

## [2.20.0] - 2026-07-31

> **Action required if you maintain a custom agent.** The authoring rule was "**No `model:` key**"; `model:` is now required and must equal `tiers.json[<tier>].claude`. Any agent authored against the old rule fails `helpers/agent-lint.sh` on the next run — including from the `Stop` hook. Add the key (`reasoning` → `opus`, `backend-exec` / `frontend` → `sonnet`, `repetitive` → `haiku`) plus the `<!-- run-banner -->` block; the lint message names the expected value. Released as a minor rather than a major despite the agent-behavior change, so this note is the migration signal.

### Added — subagents now actually switch models on Claude Code (behavior change)
- **The tier system was inert on Claude Code.** `render_agent_claude()` is the identity case and `install.sh` symlinks `agents/` into `.claude/agents/dev-team/` without ever invoking the renderer, so the resolved model was computed and then discarded. Every subagent ran on the session's model — `software-architect` (`reasoning`) and `technical-writer` (`repetitive`) were indistinguishable. Only opencode and Codex had per-tier model selection
- **Agents now carry a `model:` frontmatter key** alongside `tier:`. It is a *checked mirror* of `tiers.json[<tier>].claude`, not an independent value — Claude Code reads it directly from the symlinked source, which is the only channel available when nothing is rendered at install time
- **The `claude` column holds aliases now** (`opus` / `sonnet` / `haiku`) instead of pinned ids. The pinned ids had already drifted a generation behind (`claude-opus-4-7`, `claude-sonnet-4-6`); aliases track the current model of each family and do not go stale on a model launch
- **New mapping, chosen for cost/quality/latency:** `reasoning` → `opus`, `backend-exec` / `frontend` → `sonnet`, `repetitive` → `haiku`. The material change is `repetitive`, which was paying Sonnet rates for doc generation and now runs on Haiku at roughly a third of the cost
- **`backend-test-specialist` moved from `repetitive` to `backend-exec`**, matching `frontend-test-specialist` in `frontend`. The two had been asymmetric; the asymmetry only became expensive once `repetitive` meant Haiku, since authoring backend tests is not low-judgment work. `repetitive` now holds `technical-writer` alone
- **Three copies of the mapping, one guard.** `helpers/agent-lint.sh` re-derives the map from `tiers.json` on every run and fails if `model:` or the run-banner row disagrees with it, in either direction. `model` is now in `REQUIRED_FIELDS`
- **Rejected alternative:** having `render_agent_claude()` inject the model and `install.sh` copy instead of symlink. That breaks the byte-identity assertion in `check_claude` (`.github/scripts/ci/provider/_contract.py`), requires `update.sh` to re-render, and changes what `fix-symlinks.sh` and the health-check's symlink category test. The mirrored key achieves the same result with none of that blast radius

### Added — every agent opens with a run banner, on all three providers
- **`skills/shared/model-identity/SKILL.md` now emits a table** (agent, tier, model, effort) rather than a one-line blockquote, and each agent body carries its own values in a `<!-- run-banner -->` block inside `## Model Identity`
- **The banner is resolved at render time, not runtime.** `render_run_banner()` rewrites the Model and Effort cells for opencode and Codex; the source copy holds Claude's values because Claude is the identity case. Agent and Tier cells are provider-agnostic and pass through
- **This replaces a runtime resolution procedure that was wrong by construction.** The skill used to tell each agent to detect the provider by directory presence — checking `.opencode/` *before* `.claude/` — and then read `tiers.json` itself. A Claude project that later ran `install-opencode.sh` (a flow the framework explicitly supports) would report opencode's model on every Claude agent. It also cost a file read on every single agent invocation
- **`helpers/size-limits.sh`: agent ceiling 200 → 205.** The banner adds a fixed 5 lines to all 17 agents; six were pushed over. The content budget is unchanged at 200 — the comment in the script says so, and says not to raise it again to fit a long agent
- **Note for whoever extends `agent-lint.sh` next:** the first draft of the `tiers.json` lookup used `f"{tier}\t{entry[\"claude\"]}"` — a backslash inside an f-string expression, which is a `SyntaxError` — behind a trailing `|| true`. The map came back empty and the check silently passed everything. It was caught only by introducing drift on purpose and noticing that two of the three expected errors fired. Never let a `|| true` cover a snippet whose failure mode is "the check does nothing"; the guard now reports an unreadable `tiers.json` as an error instead of skipping

### Fixed — the shellcheck gate now passes on the tree it was promoted against
- **`helpers/orphan-skill-scan.sh` had `2>/dev/null` in the middle of a `find` expression**, before `-exec … -print`. It worked — the shell strips the redirect and applies it to `find` — but it read as a per-action redirect and was one edit away from becoming one. Moved to the end
- **Three `# shellcheck source=` directives used script-relative paths**, which resolve to nothing when CI runs `shellcheck -x` from the repo root. The unresolved source hid the guard's use of `PREFS_FILE`, so each `SC1091` also produced a bogus `SC2034` — nine findings from one cause. The paths are now repo-root-relative, the form `scripts/update.sh` already used, and in two of the three the directive moved below the `[ -f … ] || exit 0` guard, since a directive separated from its `.` line is not attached to it
- **`_telemetry_enabled` is now called with `"$PREFS_FILE"` at all four call sites.** Behaviourally identical (`${1:-${PREFS_FILE:-}}`), but it turns an implicit dependency on a global into an argument, which is what keeps the `SC2034` class from returning if a source path ever breaks again
- **`SC2317` and `SC2329` are both disabled on `uc_setup_http`** — the unreachable-function check was renumbered between shellcheck releases, and CI runs an older build than a current local install
- **Note for whoever promotes the next advisory check:** this gate was flipped to blocking in `c7535b7` with the note "the tree is clean". It was not, and `main` stayed red until this fix. Run `bash .github/scripts/ci/01-lint.sh` — not the individual helpers — before promoting

## [2.19.0] - 2026-07-31

### Changed — agents run scoped tests, never the full suite (behavior change)
- **New canonical skill `skills/shared/scoped-test-execution/SKILL.md`.** When finishing a task, an agent now runs only the tests covering the code it touched plus that code's direct dependents. The project's full suite is left to CI, or to the user running it manually
- **One exception, and only one:** an explicit user request in the session ("run the whole suite"). Suite speed, refactor width, changes to shared code, a failing scoped test, a release or a merge do **not** authorize a full run. An ambiguous request ("make sure nothing broke") resolves to the scoped run plus an offer, never to escalation
- **The `< 60 s` fast-suite criterion in `/devteam:commit` is gone.** Step 4.5c used to run `npm test` / `pytest` / `go test ./...` / `make test` whenever the suite was believed to be fast; it now delegates to the skill and runs only what covers the staged files
- **`/devteam:refactor` no longer tells `qa-specialist` to run the full suite** during the quality gate
- **Definition-of-Done lines updated** in `backend-developer`, `mobile-developer` and `skills/shared/frontend-done-checklist` — "Test suite passes" became "Tests covering the change pass". `backend-test-specialist`, `frontend-test-specialist` and `qa-specialist` load the skill before executing any test command
- **No gate was weakened:** a failing scoped test still blocks the task, CI pipelines still execute 100% of the suite, and what agents *write* is still governed by `skills/testing/test-strategy/SKILL.md`

### Changed — telemetry now requires explicit consent (behavior change, action may be required)
- **Anonymous telemetry defaults to DISABLED.** It is enabled only when the installer could reach a terminal *and* the user actively accepted the prompt. Previously the value was pre-set to `"telemetry": true` and the consent prompt was gated behind `[ -t 0 ]` — which is false under the documented `curl … | bash` install, because stdin is a pipe. The prompt therefore never appeared on the primary install path while telemetry was already on, contradicting the opt-out consent both READMEs advertised
- **The interactivity test is now "can we open `/dev/tty`"**, not `[ -t 0 ]`, so the prompt is actually shown on the `curl … | bash` path. Pressing Enter still accepts — the opt-out model survives wherever the prompt is genuinely reachable
- **A 60-second timeout or an EOF counts as declining.** Silence is not consent
- **`DEVTEAM_NONINTERACTIVE=1` forces the silent path** (CI, container image builds, automated provisioning) — no prompt, telemetry left off
- **The read path fails closed to match.** `_telemetry_enabled` was defined three times across `scripts/helpers/telemetry-send.sh`, `stop/05-telemetry.sh` and `pre-tool-use/02b-telemetry.sh`, and a missing or unreadable `preferences.json` used to resolve to *on*. It is now a single definition in the new **`scripts/lib/telemetry-guard.sh`**, and a missing file, an unreadable file, a missing `telemetry` key, or no `python3` all resolve to *off*. A consumer that cannot source the guard must also skip sending
- **Existing `preferences.json` values are untouched** by an update. A **legacy file missing the `telemetry` key now resolves to off** on the read path. Note the remaining seam: `scripts/lib/preferences-defaults.json` still carries `"telemetry": true`, so the session-start backfill will write `true` into such a legacy file on the next session — documented in `CLAUDE-md/preferences.md` until the default is flipped
- **`PRIVACY.md` corrected on two counts** — it described a pure opt-out model (now a consent table matching the installer), and it named the PostHog **EU** region while the code has always posted to `us.i.posthog.com`. The document now states the US region, and mentions `DEVTEAM_POSTHOG_ENDPOINT` for self-hosted instances
- **PostHog key comment disambiguated.** Two adjacent comments claimed the embedded key was both intentionally public and a placeholder to replace before release. It is a full-length `phc_` project *capture* key — write-only ingestion, cannot read, query or export. The stale TODO referred to a literal placeholder that no longer exists

### Fixed — install, update and rollback lifecycle
- **Fresh installs were broken.** A genuinely clean install died at Step 2b: `user-data/` does not exist in the tarball, so the credentials heredoc failed and `set -e` exited 1. Reproduced against the unmodified original; fixed with `mkdir -p`
- **The install swap could destroy an existing installation with nothing to restore from.** `rm -rf` preceded each `mv`: if the first move failed the existing install was already gone, and if the second failed, `user-data/` — preferences and session summary — survived only in an unadvertised `mktemp` directory. Replaced with a **stage-aside-swap**: build the new tree as a sibling, rename the current one aside, rename the new one in, delete the aside copy last. Both critical steps are same-filesystem renames, and an `EXIT` trap restores the aside copy if the script dies between them. Also corrects a comment claiming the rename kept the running script alive — `update.sh` executes from inside the tree being replaced
- **Download failures reported a single generic message.** stderr from all three fetches went to `/dev/null`, so TLS errors, a 404 on a bad tag, proxy failures and rate limits were indistinguishable on the sole install entry point. The cause is now printed, on the failure path only
- **`chmod` had drifted past three shipped subtrees** (`hooks/lib`, `scripts/helpers`, `scripts/lib`) because it enumerated four directories by hand. Replaced with a recursive `find`, so it cannot drift again
- **Update integrity.** `update.sh` piped an unverified download into `bash`. There is no release workflow and no published checksum, so authenticity is not achievable here and is **not** claimed. What is now true: the installer is fetched from the **same pinned ref** as the payload rather than a moving `main`; the payload is verified before `bash` sees it (non-empty, size floor, shebang, project markers, `bash -n` parse — which catches truncation); and a SHA-256 is checked when `DEVTEAM_INSTALLER_SHA256` or a published digest exists, with a mismatch aborting. The file header states plainly that this does not defend against a repo-write attacker, who controls both files
- **New `scripts/lib/installer-fetch.sh`** — `rollback.sh` duplicated `update.sh`'s HTTP detection, GitHub coordinates and fetch sequence byte for byte. Extracted into one shipped library, now also used by the unattended auto-update hook path

### Fixed — repository tooling that silently did nothing, or the wrong thing
- **`orphan-skill-scan.sh` no longer deletes.** Its auto-fix ran `sed "/$ref/d"`, removing the *entire line* containing a broken skill reference — on a routing-table row that took the detection signals with it, silently, unattended, on every Stop. Observed live: moving the `jquery` skill destroyed its row in `frontend-developer.md`. It now **repairs** the path when the skill can be located unambiguously by basename, and **reports** anything it cannot resolve instead of removing it
- **`orphan-skill-scan.sh` no longer counts a narrative mention as a load**, which was producing an unresolvable standing finding on `software-architect`. The genuine finding (`migration-v1-to-v2` had no agent reference) still reported, and is now resolved
- **`archive-index.sh` was a guaranteed no-op**, not merely unwired: its parser matched `### YYYY-MM-DD` while the index uses `## YYYY-MM-DD`, so it found zero sections and would have reported "nothing to archive" forever — the documented 90-day rotation could never have run even once triggered. Both `awk` passes also mishandled nested category headings; removal would have truncated the file to EOF. Rewritten and verified against a sandboxed copy of the real index: correct quarter routing, entry count conserved, idempotent, with a trustworthy `--dry-run`
- **`check-fingerprint-uniqueness.sh` now scans the archive files too.** Scoped to a single file, this blocking gate would have silently degraded from a global to a per-file guarantee the moment rotation ran
- **`orphan-template-scan.sh` now checks resolvability, not mention.** It surfaced 6 references using bare `templates/…` paths that resolve only inside this repository, not from an installed project root; `runbook-template.md` had zero resolvable references and was previously reported healthy. All template references now use the installed `.dev-team-agents/templates/…` form that `new-adr.sh` already proved
- **`check-codex-compat.sh` aborted with an unbound variable** when run with no arguments, contradicting its own usage line

### Fixed — skills
- **`discovery-mode` shipped two real bugs in a snippet models transcribe verbatim.** The acquire block returned before the staleness check could ever run, so a stale lock blocked discovery permanently; and the check used GNU-only `date -d` with `|| echo 0`, which on macOS made every lock look stale and **deleted it unconditionally** — the exact opposite of the intent, on a large share of installs. Both fixed with `find -mmin`, verified across GNU, BSD and dash
- **`architecture-awareness` contradicted the stack-agnostic core rule** at the one place every coding agent reads on every spawn: it enumerated frameworks and bundlers with no section gate, so `backend-developer` received SPA advice and `mobile-developer` received two browser sections that do not apply. Rewritten as structural signal-to-model tables with a routing gate and a mobile section that voids the DOM rules
- **`mobile/ios` and `mobile/android` stacked instead of replacing.** Each opened by loading the very reference the agent's routing table already loads — 507 lines for a cross-platform task. Each now declares itself the engineering half and defers the design half
- **`reviewer-base` restated a strict subset of the SonarQube detection signals**, silently missing two detection paths. It now delegates to that skill's own table
- **`security-checklist` asserted the security/QA overlap** rather than partitioning it. It now carries an explicit ownership boundary with a cross-boundary reporting protocol
- **Integration skills audited before the inlined agent copies were deleted.** Kong's `strip_path` rule lived only in `references/consumers.md`, so removing the agent copy would have reference-gated a critical rule; none of SonarQube's four developer rules existed in the skill at all. Supabase and `async-jobs` each gained one rule. Nothing was lost in the extraction

### Added
- **`/devteam:setup`** — `commands/setup.md` gives `setup-assistant` the slash-command entry point every other agent already had. Detects `FIRST_RUN` vs `REFRESH` from the presence of `docs/project.md`, reports the mode, and delegates the full flow. Registered in `scripts/lib/commands.json` with `plan_gate: required`
- **`skills/architecture/llm-integration`** — embeddings, retrieval, prompt versioning, evaluation, and an 11-row failure-mode table covering prompt injection and PII. The repo had no such skill; its only pointer, in `db-comparison`, routed pgvector questions to a multitenancy skill
- **`skills/testing/load-testing`** — load profiles, SLO-derived thresholds and percentile interpretation, with an explicit boundary against `performance-budgets`. Loaded by `backend-test-specialist`
- **`skills/testing/frontend-hook-tests`** and **`skills/testing/decoupled-frontend`** — React `renderHook` / Vue `withSetup` recipes, and MSW handlers, state coverage and selector priority, extracted from `frontend-test-specialist`
- **`skills/devops/infrastructure-sizing`** and **`skills/security/dependency-audit`** — both were stack-prescriptive at source and were rewritten to preserve the judgment while dropping the prescription: sizing is capability tiers T0–T3, scanner selection is a lockfile-signal table where exactly one row applies. Product names survive only as labelled examples
- **`skills/architecture/orchestration`** and **`skills/architecture/architecture-docs`** — extracted from `software-architect` to bring it under the line cap
- **`skills/legacy/`** — new skill category for legacy-codebase survival material. `jquery` moves here from `ui-libraries`; its content is survival guidance, not component-library reference
- **New Stop sub-scripts** — `03b-fingerprint-uniqueness.sh` (static validation; exits 2 so the finding reaches the session instead of arriving later as a red build) and `99b-archive-index.sh` (cleanup tier, must run after every check that reads the fingerprint bank, gated by a daily stamp since rotation is time-based). Both degrade silently where `helpers/` is absent, as it is in every installed project
- **`DEVTEAM_HOOK_DEBUG`** — set it to trace which hook sub-scripts ran, which were skipped, and with what exit code

### Changed — hooks
- **Both dispatchers now require the documented `NN-name.sh` / `NNx-name.sh` filename pattern** and skip anything that does not match. They previously globbed every `.sh` in their directory, so a draft or a renamed `.bak` executed on every Stop or every tool call. Chosen over an allowlist (no second registry to drift) and over an opt-out marker (fails open). All current sub-scripts match
- **`pre-tool-use/02-telemetry.sh` renamed to `02b-telemetry.sh`.** Two sub-scripts shared the `02-` prefix with order decided only by an alphabetical tiebreak; `02-graphify-hint.sh` keeps its number as the externally referenced one
- **Change gates.** `02b-orphan-template-scan` was the only Stop sub-script with no gate, running a full recursive scan across four trees on every Stop including purely conversational ones. `05-telemetry` ignored the dispatcher's no-changes flag, queueing a `session_end` for every empty turn. Both now honour it; `05` keeps the flush (it is TTL-gated and the only delivery path for events queued by PreToolUse) and suppresses only the event
- **Hot path.** `01-check-updates` forked `python3` to read the update interval *before* its own TTL early-return, so the 24h cache could never prevent the fork — on a hook that runs on every tool call. The interval now comes from a sidecar cache invalidated with `[ prefs -nt cache ]`, a bash builtin. Measured: cold run 1 fork, hot run 0 subprocesses
- **`01-check-updates` decomposed** from a 209-line monolith into a 79-line orchestrator over the new **`scripts/hooks/lib/update-check.sh`**, which also fixes a pre-existing trap leak where the auto-update `EXIT` trap replaced the temp-file trap
- **Auto-update integrity.** `uc_perform_auto_update` piped an unverified download from a moving ref straight into `bash` — on the *unattended* path. It now delegates to `scripts/lib/installer-fetch.sh` for ref pinning and payload verification, and **skips the upgrade entirely** if that library is absent rather than falling back to an unverified fetch
- **Git state deduplicated.** `stop.sh` computes the touched-path set once and exports it via the new **`scripts/hooks/lib/touched-paths.sh`**; sub-scripts `02`, `02b`, `03` and `03b` no longer each re-run identical `git status` / `git log` invocations. Four forks removed, and the sub-scripts still work standalone
- **Notifier tips moved out of the script.** The 45 inline tip strings now live in `scripts/hooks/stop/tips/tips.{en,pt-BR,es}.txt`, so the notifier reads **one** locale after the daily gate instead of parsing all three on every Stop. Adding a locale is one file plus one `case` arm

### Changed — agent and command authoring standards
- **Agent frontmatter is `name` + `description` + `tier`.** `CLAUDE.md` still mandated the `model:` and `tools:` keys that the multi-provider port removed — following the canonical doc produced an agent that failed CI. The standards block now documents the four valid tiers, points at `scripts/lib/tiers.json` as the canonical tier → model id map, and drops both the Haiku note (no tier resolves to Haiku on any provider) and the obsolete tools-order rule
- **All 17 agents are within the 200-line cap for the first time** — from 11 violations to 0, and `agents/` from ~3,900 to 3,100 lines. `software-architect` 372 → 185, `frontend-test-specialist` 266 → 180, `backend-developer` 265 → 167, `setup-assistant` 244 → 195, `devops-specialist` 243 → 198, `security-specialist` 240 → 198, `frontend-developer` 236 → 196, `code-reviewer` 233 → 185, `qa-specialist` 227 → 196, `backend-reviewer` 209 → 194, `mobile-developer` 203 → 173
- **`helpers/size-limits.sh` now passes strict with no flag** — 17/17 agents, 25/25 commands and every `SKILL.md` within their caps. `commands/learn.md` (229 → 194) was the last file over any declared limit
- **The Foundational Rule is delegated, not inlined.** 15 agents carried the same 12-item context list — 384 duplicated lines fleet-wide. All 17 now delegate to `skills/shared/project-context/SKILL.md` in one line and keep only genuinely role-specific additions
- **Directives with a canonical home were deleted rather than paraphrased**: the project-rules-override sentence (14 copies) lives in `project-context`; the docs-sync closing paragraph (13 copies, already drifted into two variants) is now a **Task Closure Rule** in `skills/shared/docs-sync/SKILL.md`; the comments-policy routing parenthetical (8 copies) is in that skill's Conditional Section Loading table; the SonarQube detection triple (11 copies) is in `project-context`; the token-efficiency load line, drifted into nine wordings, is now one. The TODO/FIXME reviewer bullet, triplicated in two diverging variants, is gone entirely — `comments-policy` already owns the rule and all three reviewers load it
- **`## Worktree Isolation` now delegates.** The decision cascade was restated in all 8 coding agents (~15 lines each) and drifted between them. Agents point at the canonical cascade in `CLAUDE.md` and at `skills/shared/worktree/SKILL.md`; the cascade itself is documented exactly once
- **`code-reviewer` matches its documented contract.** It shipped 10 structural review categories while `CLAUDE.md` says the router coordinates rather than duplicates specialist checks. Nine were covered by the specialists and were removed; the three that existed only here — running the linters, cross-cutting silent bugs, static-state-vs-injection — survive as Router Responsibilities. Its 15-item Foundational Rule, which mixed five conditional loads into the mandatory list, is now split
- **Stack-prescriptive agent bodies moved to skills** — `security-specialist`'s nine-scanner command block, `backend-developer`'s eight blocks of inlined integration rules, `devops-specialist`'s Kubernetes/Nginx/Datadog decision framework, `frontend-test-specialist`'s hook recipes and decoupled-frontend material, `backend-test-specialist`'s five-language coverage matrix, `setup-assistant`'s Docker Compose probe (now in `stack-detection`, whose consumer is every agent rather than devops alone). `frontend-developer`'s data-fetching and security rules and `frontend-reviewer`'s type-safety criteria were rewritten framework-neutrally, with identifiers demoted to examples
- **`setup-assistant`** merges its duplicate Immutability Warning headings, delegates its bundled Health Check and Update Manager roles to the procedures that already exist for `/devteam:health-check` and `/devteam:update`, and gains a trigger for the `migration-v1-to-v2` skill, which had no consumer despite defining what v2 is
- **`product-analyst`** loads the 237-line `backlog-template` only when producing backlog output, and its tracker section gained an explicit fallback instead of silently handling two of the five trackers the installer advertises
- **Quiz-first Rule enforced across `commands/` too.** Seven live violations were found, not the two previously reported — the linter only ever scanned `agents/`, so `commands/` had never been checked, and its regex only matched yes/no forms. Fixed in `refactor`, `audit`, `commit` and `pr`; `refactor` and `audit` now load `interaction-patterns`
- **Command preambles collapsed to one line.** The `current-context` and `interaction-patterns` directives were two copy-pasted paragraphs across 20 files, now a single identical line (~35% shorter). The `.claude/agents/dev-team/` prefix, repeated 72 times, is declared once per file in the 15 files with two or more spawn references; the six single-reference files keep it inline
- **All six implementation commands now share an identical Session close step** — session-summary append with per-agent sub-headings, then commit and PR. Five of the six previously ended at the resolution message, leaving the working tree dirty with no terminus, while two others in the same family defined one. Only `learn.md` had mentioned session-summary at all
- **`commit.md` no longer restates the layered-commit table** it already loads from `conventional-commits`. Rows 8 (Config/CI) and 9 (Docs), which existed only in the command, were appended to the skill so nothing was lost
- **`plan-mode` no longer carries a second copy of the plan format** in box-drawing characters, which the repo's own `output-format` skill forbids. It loads `templates/plan-template.md`

### Changed — CI, validators and governance
- **CI push trigger narrowed to `main` + tags.** Concurrency alone cannot dedupe push-vs-PR because the two events carry different refs, so both runs survived. **Trade-off: a branch with no open PR no longer gets CI on push.** A concurrency group was added alongside
- **New `tag-name` job rejects tags outside `vX.Y.Z`.** Scoped to the tag-push event and reads only the ref just created, so the two existing malformed tags are never evaluated and are left in place
- **`agent-lint.sh` gained skill validators** — skill frontmatter `name` must equal its directory basename (the renderer resolves opencode skills by name while installers symlink by directory, so a divergence is load-bearing across providers; the single violator, `shadcn-ui` vs `shadcn/`, is fixed), skill names must be unique across categories, and the quiz-first check now catches multiple-choice prompts, not only yes/no variants. A skill-description length check (95-char budget) is included as an advisory warning; 21 descriptions currently exceed it
- **`size-limits.sh` now covers `commands/`** (limit 200, matching agents) — previously the only shipped content category with no size discipline
- **README-sync is now structural.** It compared heading counts and total lines, so a faithful translation of wrong data passed green. It now compares the **ordered heading skeleton** plus per-section fence, table-row, link and line counts, and discovers pairs instead of using a hardcoded list. This immediately caught real pre-existing drift: `docs/installation.pt-BR.md` was missing the entire "Windows: symlinks in a committed installation" subsection, now translated and inserted. The gate ships with **no known-drift exemptions**
- **Enforcement is now exactly two wrappers**, blocking and advisory, with the policy stated in-file and a `PROMOTE WHEN` note on each advisory — promotion is a one-word change once the subjects are clean
- **`CODEOWNERS` gains a default catch-all** so no future path lands unowned, plus explicit rules for the five missing skill domains, `helpers/`, `.github/` and the sync-governed doc pairs. The dead `workflows/` rule is removed

### Removed
- **`templates/backlog-template.md`** — no consumer ever referenced the file, and the same-named skill emits a different document shape, so wiring them together would have forced the skill to document a format it never produces

### Documentation
- **`docs/agents.md` / `docs/agents.pt-BR.md`** — the hand-maintained `Model` column was wrong for `technical-writer` (listed Haiku, resolves to sonnet) and `setup-assistant` (listed Sonnet, resolves to opus), and the pt-BR mirror had faithfully propagated both errors. The column is replaced by the agent's actual `tier`, with the provider mapping stated once below the table; the duplicate of `tiers.json` was the drift's root cause
- **`CLAUDE.md` File Structure** — previously omitted `helpers/`, `opencode/`, `user-data/`, `.github/`, `PRIVACY.md` and `CLAUDE-md/` (cross-referenced four times by `CLAUDE.md` itself), documented 5 of 15 scripts and 8 of 11 skill domains. Now complete and verified against the tree, including `skills/legacy/`, `scripts/lib/{installer-fetch,telemetry-guard}.sh`, `scripts/hooks/lib/{touched-paths,update-check}.sh` and `scripts/hooks/stop/tips/`. It also documents the two directories named `helpers` and their opposite packaging fates: root `helpers/` is stripped at install, `scripts/helpers/` ships and runs
- **`CLAUDE.md` hook maps** — Stop and PreToolUse convention sections now list `03b-`, `99b-` and `02b-telemetry.sh`, document the mandatory filename pattern both dispatchers enforce, and record the `DEVTEAM_NO_CHANGES` / `DEVTEAM_TOUCHED_PATHS` contract. The Hook Files Map gains all three shared libraries under `scripts/hooks/lib/`
- **`CLAUDE.md` — new "Canonical Rule Homes" section** listing each cross-cutting rule, the single skill that owns it, and what agents must do instead of restating it
- **`CLAUDE.md` Code Reviewer roles** — said `code-reviewer` delegates to the test specialists; it routes to `backend-reviewer` / `frontend-reviewer` via `skills/shared/review-router/SKILL.md`
- **`CLAUDE.md` Orphan Skill Self-Check Rule** — the `AUTO-FIXED` line no longer describes deletion, and the two distinct `ACTION REQUIRED` classes are documented separately
- **README command tables** — `/devteam:health-check`, `/devteam:adr`, `/devteam:update`, `/devteam:symlinks` and `/devteam:setup` were missing; both READMEs now document all 25. The `/devteam:plan` row was corrected to reflect `product-analyst` as protagonist. The `current-context` exception list was corrected against `grep -L`: it wrongly listed `symlinks` and omitted `health-check`
- **`CLAUDE-md/user-data.md`** — added the `opencode/` strip rule and the four update-check / archive state files under `user-data/`
- **`CLAUDE-md/notifications.md`** — sub-script table reconciled with the real `scripts/hooks/stop/` contents; the tip section now describes the locale data files rather than inline strings
- **`docs/providers.md`** — documents the skill `name` == directory invariant as a cross-provider requirement, corrects the CI job name (`provider-contracts`, not `provider-matrix`), and corrects the packaging note: `strip-tarball.sh` keeps the render engine and provider installers in a Claude install so providers can be added offline, and removes only `opencode/`, `helpers/`, `.claude/`, `.github/`, `.gitignore` and `scripts/install.sh`

### Changed — slim Claude install + on-demand provider bootstrapping
- **Slim Claude installer** — `scripts/install.sh` no longer bundles the cross-CLI plumbing into the client's `.dev-team-agents/`. The following files are stripped from the extracted tarball before install: `scripts/install-opencode.sh`, `scripts/install-codex.sh`, `scripts/render-provider.sh`, `scripts/lib/render_provider.py`, `scripts/lib/{tiers,tool-map,command-map,commands}.json`, and the `opencode/` directory. The default Claude-only client footprint drops by the size of those ~7 files. Users who want opencode or Codex CLI support bootstrap it on demand (see below)
  > **Superseded before release.** `scripts/lib/strip-tarball.sh` now removes only `opencode/` from that list — the render engine, `scripts/lib/*.json` and both provider installers are kept in a Claude install so providers can be added offline. `install-provider.sh` remains the curl-pipe entry point for users starting from scratch.
- **New `scripts/lib/strip-tarball.sh`** — single source of truth for the slim strip rules. Sourced by `install.sh` (during tarball install) and by `.github/scripts/ci/slim-bootstrap.sh` (CI contract test), eliminating duplication. Add or remove a strip entry in one place; CI catches the regression automatically

### Added — multi-provider CI contract net
- **Per-provider contract tests** — new job `provider-contracts` in `.github/workflows/ci.yml` runs across `claude | opencode | codex` with five sequential checks per provider: render → attendance (counts derived from canonical source, never hardcoded) → schema/cross-ref contract → fixture install → fixture validation. The contract checker (`.github/scripts/ci/provider/_contract.py`) enforces: every tier has a column for every provider; every command in `commands.json` has a valid `agent` ref pointing at an existing source agent; opencode agents have frontmatter matching the schema (`mode ∈ {subagent, primary, all}`, `model` carries a provider prefix, `permission` keys are from the allowed set); opencode command snippet entries have all four required keys (`description`, `agent`, `model`, `template`); codex agent TOML parses and carries `name/description/model/developer_instructions` without provider prefix on model and valid `model_reasoning_effort` if present; codex prompts carry a `<!-- description: ... -->` header and follow the `devteam-<name>.md` naming. Violations exit non-zero with a one-line diagnostic
- **`slim-bootstrap` CI job** — new dedicated job verifies (1) a `git archive HEAD | tar -x` extraction + `apply_strip` produces the slim Claude shape (cross-CLI plumbing absent, Claude runtime essentials present — both lists asserted), (2) `install-provider.sh opencode --source` bootstraps `.opencode/` correctly into a slim-claude fixture (22 commands merged into `opencode.json`, plugin copied, skills symlinked, 17 agents), (3) `install-provider.sh codex --source` does the same for `.codex/` (17 agents + 22 prompts + 4 managed hooks + skills)
- **CI scripts externalized** — `.github/workflows/ci.yml` now invokes helper scripts under `.github/scripts/ci/` instead of inlining logic. New layout: `.github/scripts/ci/01-lint.sh`, `02-readme-sync.sh`, `slim-bootstrap.sh`, and `provider/{10-render,20-attendance,30-contract,40-install-fixture,50-validate-installed}.sh` + `_contract.py`. Pipeline is 3 jobs (`lint`, `provider-contracts` ×3, `slim-bootstrap`) with each step a single `bash .github/scripts/ci/...` invocation
- **Negative-test rehearsal** — the contract checker has been locally verified to catch: missing tier column for a provider, dangling `agent` ref in `commands.json`, malformed rendered opencode frontmatter (unknown `permission` key, missing `mode`, etc.). Each prints one diagnostic line and fails the build
- **New `scripts/install-provider.sh`** — curl-pipeable bootstrap that downloads a tarball of the requested version (`main` by default, or `--version vX.Y.Z`) and runs `install-opencode.sh` / `install-codex.sh` from a temp source dir with `--source`. It accepts `--source <path>` for working from a local clone without network. Usage: `bash <(curl -sSL .../install-provider.sh) opencode` or `... codex`
- **install-opencode.sh / install-codex.sh** — added a defensive check that exits with a clear error and bootstrap guidance when invoked from a source dir that lacks the render engine (`scripts/render-provider.sh` or `lib/{render_provider.py,tiers.json,…}` not present). This case happens when a slim Claude install is mistakenly used as the source; the message points the user at the `install-provider.sh` curl-pipe
- **README.md and README.pt-BR.md** — new "How It Works — Single Source, Multi-CLI" section right after "What This Is" with a textual architecture diagram showing the canonical source → render engine → per-provider output flow, and the slim Claude install alongside it. The "Other providers" section is rewritten to use the new `install-provider.sh` curl-pipe as the entry point (instead of pointing at `install-opencode.sh` / `install-codex.sh` inside the framework install, which no longer ships by default)
- **docs/providers.md** — added a note at the end of the "Adding a new provider" section explaining why the install scripts are stripped from slim installs and how `install-provider.sh` bootstraps them on demand

### Removed
- **`workflows/` directory and concept** — the 5 scope-specific workflow files (`design.md`, `fullstack.md`, `mobile.md`, `refactor.md`, `review.md`) and the 5 `/devteam:workflow-*` loader commands are gone. Each scope is now reached directly through its `/devteam:<scope>` command (`/devteam:design`, `/devteam:fullstack`, `/devteam:mobile`, `/devteam:refactor`, `/devteam:review`), which already delegated to the right agent. The `skills/shared/workflow-detection/SKILL.md` skill was removed. `agents/software-architect.md` and `commands/architect.md` no longer reference a separate workflow file. `helpers/orphan-skill-scan.sh` and `helpers/orphan-template-scan.sh` no longer scan a `workflows/` directory. `scripts/install.sh` `KEEP_ROOT` no longer distributes a `workflows/` directory. The 5 `workflow-*` entries were removed from `scripts/lib/commands.json`. CLAUDE.md, both READMEs, `docs/providers.md`, `CONTRIBUTING.md`, and `.github` templates were updated to drop framework-workflow references (`.github/workflows/` and `skills/shared/git-workflow/` are unrelated and kept)

### Added — multi-provider port (single source of truth)
- **Provider-agnostic render engine** — `scripts/render-provider.sh` (+ python engine `scripts/lib/render_provider.py`) renders the canonical `agents/` + `commands/` into the frontmatter shape expected by Claude Code, opencode, or Codex CLI. Agent bodies stay unchanged; a short "Tool conventions" preamble per provider explains how Claude Code tool names map to that provider's native tools. Fails fast on any unknown tier or missing `tier:` key
- **Per-agent `tier:` frontmatter key** — every `agents/*.md` now declares one of `reasoning | backend-exec | frontend | repetitive`. `helpers/agent-lint.sh` validates this key
- **Canonical tier → provider model id map** — `scripts/lib/tiers.json` carries the full model id per tier per provider (`claude`, `opencode`, `codex`). Adding a new provider is one new column, no edits to any agent or skill
- **Per-provider metadata** — `scripts/lib/tool-map.json` (Claude tool names → provider equivalents, used to generate the body's "Tool conventions" preamble) and `scripts/lib/command-map.json` (per-provider output form for slash commands)
- **Per-command metadata** — `scripts/lib/commands.json` declares each `commands/<name>.md`'s tier + lead agent + description, removing any need to add frontmatter to source command bodies
- **`scripts/install-opencode.sh`** — installs dev-team-agents into a project's `.opencode/` (renders 17 agents with opencode-shaped frontmatter, symlinks `skills/`, copies the plugin at `opencode/plugin/dev-team-agents.ts`, deep-merges 27 `devteam:<name>` command keys into `.opencode/opencode.json`)
- **`scripts/install-codex.sh`** — installs dev-team-agents into a project's `.codex/` (renders 17 agents as `.codex/agents/<name>.toml`, renders 27 prompts as `.codex/prompts/devteam-<name>.md` → `/prompts:devteam-<name>`, symlinks `skills/`, writes 4 managed hooks to `.codex/hooks.json` wiring `SessionStart | PreToolUse | PreCompact | Stop` to the existing bash dispatchers)
- **opencode plugin** — `opencode/plugin/dev-team-agents.ts` binds opencode's `event`, `tool.execute.before`, and `experimental.session.compacting` hooks to the same `scripts/hooks/*.sh` that Claude Code uses. Hook behavior stays single-source; only the binding event adapts
- **CI matrix job** — `.github/workflows/ci.yml` runs `provider-matrix` across `claude | opencode | codex`, asserting each emits 17 agents + 27 commands and installs cleanly into a fixture project
- **`docs/providers.md`** — canonical reference for the provider port: tier map, install commands per provider, the `/devteam:plan` UX across providers, how to add a new provider (single column in `tiers.json` + a row in `tool-map.json` + a row in `command-map.json` + one install-$provider.sh shell)
- **README updates** — new "Other providers (opencode, Codex)" section in both `README.md` and `README.pt-BR.md`; CLAUDE.md gains a "Multi-provider port" reference section

### Changed
- **Per-agent model id is now derived from `tier:` + `tiers.json`** — `model:` in `agents/*.md` is kept as the Claude fallback; non-Claude installations ignore it and resolve model via `tiers.json[tier][provider]`
- **Codex slash-command divergence** — Codex CLI's custom-prompt namespace is hardcoded as `/prompts:<name>`, so dev-team-agents commands are exposed as `/prompts:devteam-<name>` in Codex (e.g., `/prompts:devteam-plan`). Claude Code and opencode both preserve the canonical `/devteam:<name>` UX. The divergence is documented in `docs/providers.md`

### Fixed — silent bugs detected by post-SHIP audit
- **codex hooks.json shape (CRITICAL).** The `.codex/hooks.json` file previously emitted an array under `"hooks"` (e.g. `{"hooks": [{"event": "Stop", ...}]}`) but the Codex spec requires an object keyed by event name (`{"hooks": {"Stop": [...]}}`). Each hook `command` field was emitted as an array (`["bash", "../a.sh"]`) but the spec requires a string (`"bash ../a.sh"`). Both bugs caused all 4 lifecycle dispatchers to be silently ignored by Codex. Fixed.
- **`ensure-claude-framework.sh` — hook scripts not materialised in opencode/codex-only setups (CRITICAL).** Both `install-opencode.sh` and `install-codex.sh` now source `scripts/lib/ensure-claude-framework.sh` which copies the Claude-runtime subset (`scripts/hooks/`, `scripts/lib/`, `scripts/helpers/`, `agents/`, `commands/`, `skills/`, `templates/`) to `.dev-team-agents/` in the target project. This is done IDEMPOTentently (only if the hooks dir is absent). Without this, the opencode plugin's `${directory}/.dev-team-agents/scripts/hooks/...` paths and codex hooks.json's `.dev-team-agents/scripts/hooks/...` commands would reference non-existent files, making all lifecycle hooks silently non-functional. Previous codex installer created a dangling symlink to the bootstrap temp dir (deleted after curl-pipe cleanup). Fixed.
- **opencode agent `task` permission always set.** Every opencode agent now gets `permission: { task: "allow" }` unconditionally, regardless of whether the source agent's Claude `tools:` line listed `Task`. Per the framework's design, any agent may delegate via subagent. Without this, reviewers and other read-only agents would be prompted before each `task` call.
- **opencode `options.effort` removed (no-op).** The `options.effort: high|default|low` field previously emitted in every opencode agent's frontmatter is removed. Opencode's schema has no `effort` field — unknown frontmatter is silently routed into an untyped `options` object with zero effect. Documented in `docs/providers.md` Known Limitations.
- **Renderer preamble extended (skill-loading + subagent-spawn idioms).** The per-provider "Tool conventions" block that opens every rendered agent body now covers two new idiom classes: (a) how to interpret `Load skills/<category>/<name>/SKILL.md` (opencode → `skill({ name: '<name>' })`, codex → `Read .dev-team-agents/skills/<category>/<name>/SKILL.md`), and (b) how to interpret `spawn the agent at .claude/agents/dev-team/<X>.md` (opencode → `task({ name: '<X>' })`, codex → `spawn_agent({ agent_type: '<X>' })`). Source in `scripts/lib/tool-map.json`.
- **Contract tests tightened.** New shared contract validators: `check_tool_map_idiom_notes` (each non-claude provider's tool-map entry must carry `idiom_notes` — catches forgotten preamble additions when adding a provider column), `check_slug_uniqueness_in_tool_map` (no duplicate `from` keys), `check_installer_references` (`install-opencode.sh` / `install-codex.sh` must source `ensure-claude-framework.sh`). The codex `check_codex_hooks_json_shape` validator now enforces event-keyed object structure, `command` is string, and each command path resolves on disk. `50-validate-installed.sh` now asserts `.dev-team-agents/scripts/hooks/stop.sh`, `pre-tool-use.sh`, `session-start.sh`, `pre-compact.sh` exist on disk after both opencode and codex installs. `slim-bootstrap.sh` asserts hooks are materialised after both bootstrap steps.
- **`ensure-claude-framework.sh`** — new helper `scripts/lib/ensure-claude-framework.sh` containing the `ensure_claude_framework()` bash function. Sourced by both `install-opencode.sh` and `install-codex.sh`. Copies the runtime subset to `.dev-team-agents/` idempotentently, so that hook scripts are always project-local and survive bootstrap temp-dir cleanup.
- **Per-provider install docs.** New `docs/install-claude.md`, `docs/install-opencode.md`, `docs/install-codex.md` — each a focused step-by-step reference with troubleshooting. README "How to Install" collapsed to a table of one-line curl commands pointing at each doc.
- **`docs/providers.md` Known Limitations section.** Covers opencode effort no-op, per-provider skill-loading idiom differences, and codex UX divergence.

## [1.11.0] - 2026-07-24

### Added
- **Push & GitHub Actions monitoring** — new `skills/shared/github-actions/SKILL.md`. When the user explicitly asks to push and `gh` is configured, agents watch the triggered Actions run and, on failure, run a capped diagnose→fix→re-push loop (max 3 attempts) with a one-line summary each cycle. Wired into `/devteam:pr` and a new **Push & CI Monitoring Rule** in `CLAUDE.md`
- **README agent list** — both READMEs (EN/pt-BR) now list all 17 agents grouped by role with a one-line summary each
- **Mandatory post-implementation handoff** — `/devteam:backend`, `/devteam:frontend`, `/devteam:mobile`, and `/devteam:fullstack` now always hand off to `code-reviewer` + `qa-specialist` after implementation, presenting a single consolidated block of critical findings
- **`qa_browser` preference** — `qa-specialist` prefers the in-app Claude browser for browser testing; in the CLI it asks which browser to use (quiz) and can save the choice as the `qa_browser` default in `preferences.json`

### Changed
- **`/devteam:plan` reworked** — `product-analyst` is now the protagonist and produces a **business-only** requirements document ready to become sprints; `software-architect` joins only on explicit technical request. The `product-analyst` agent gained a fixed interrogation methodology (7 lenses), an anti-overengineering rule, and a 3-category finding model
- **Sprints reorganized** — sprint files now live under `docs/backlog/sprints/` as `sprint-<n>.md`, with a `sprints.md` status index (Planned → In progress → Done) kept current as sprints finalize
- **Test creation is now gated** — `/devteam:backend|frontend|mobile|fullstack|fix|refactor` create tests only when the project sets `TESTS_REQUIRED=yes` (absent key defaults to running tests); when `TESTS_REQUIRED=no` the test phase is skipped entirely
- **`/devteam:review` with no arguments** now asks a dynamic quiz — current local branch / another local branch / a PR link (GitHub, GitLab, Bitbucket, …) / other — and acts on the chosen target
- **Sprints designed for parallel execution** — `product-analyst` now decomposes scope for maximum parallelism and fills a **Parallel Execution Plan** (waves of mutually independent tasks). The `backlog-template` sprint file gained per-task `Wave` + `Worktree branch` fields and a waves table. Isolation model is explicit: worktree-per-task always; isolated Docker stack per worktree **only when the project uses Docker** — otherwise parallelism is by worktree alone

### Removed
- **Lifecycle workflow commands** — `/devteam:workflow-new`, `/devteam:workflow-maintenance`, `/devteam:workflow-bugfix`, `/devteam:workflow-inherited`, and `/devteam:workflow-security-patch`, plus their `workflows/*.md` files. These lifecycle concerns are now encapsulated in the agents (`software-architect` built-in behavior + the direct commands). Scope-specific workflows (design, fullstack, mobile, refactor, review) are retained

---

## [1.10.0] — 2026-07-21

### Added
- Worktree preferences in `preferences.json` — four keys (`worktree_active`, `worktree_base_branch`, `worktree_path`, `worktree_docker_isolate`) let coding agents default to a git worktree per task without asking. `scripts/lib/preferences-defaults.json` is the new canonical default schema, read by both `install.sh` and the session-start health check
- Health-check backfill — `session-start.sh` fills any missing `preferences.json` key from the canonical schema on every session (idempotent, preserves existing user values), self-healing installs that predate a newly added key
- Docker isolation per worktree — `skills/shared/worktree/references/docker-isolation.md` describes spinning up an isolated `docker compose -p <project>-wt-<ctx>-<title>` stack (namespaced containers/volumes/networks, host ports not published, teardown scoped to the isolated project only)
- `/devteam:learn` now declares a commit manifest in its plan (Step 3) and auto-commits the knowledge-base updates after execution (conventional commits, local only, no push). New `--no-commit` argument opts out

### Changed
- Worktree decision is now a three-level cascade — `.dev-team-agents/.worktree-session` (per-session override) → `worktree_active` in `preferences.json` (default) → ask once (legacy installs). Propagated to the 8 coding agents, `software-architect` worktree detection, and `CLAUDE.md`
- Worktree base branch is auto-detected (`origin/HEAD` → current branch) instead of assuming `beta` or `master`; `worktree_path` makes the worktree location configurable (default `.dev-team-agents/worktrees`)
- Worktree finalization enforces rebase-onto-base → resolve → merge → teardown of the worktree and its isolated Docker stack only, never the main infrastructure
- The coding agents' worktree prompt now uses `AskUserQuestion` (quiz-first) instead of a plain `(yes / no)` text prompt
- Synced the preferences schema across the `user-preferences` skill, `setup-assistant`, installation guides (EN/pt-BR), and both READMEs

---

## [1.9.3] — 2026-07-19

### Fixed
- `/devteam:update` now repairs a broken installation instead of falsely reporting "Up to date". When `.dev-team-agents/user-data/.installed-version` is missing or empty (`Installed: unknown`), the version check exited silently and the command reported the install as current; it now force-reinstalls the latest release to rewrite the metadata and clears the cached ETag so a stale `304` cannot mask the mismatch
- `01-check-updates.sh` no longer treats an install that is behind the still-latest release as up to date. A `304 Not Modified` short-circuited before comparing the local version against the latest release, silencing the "update available" notification after its first fire. The resolved version is now cached alongside the ETag (`.last-releases-version`) and reused on `304` to complete the comparison

---

## [1.9.2] — 2026-07-17

### Added
- `/devteam:symlinks` command — detects the OS, runs `fix-symlinks.sh` to repair materialized `.claude/` links, and walks the user through the OS fix (quiz-first) when native symlinks are blocked

---

## [1.9.1] — 2026-07-17

### Fixed
- `scripts/fix-symlinks.sh` now removes the legacy `stop/02-graphify-refresh.sh` sub-script during an in-place repair. On stale Windows installs the old sub-script called a `graphify-refresh.sh` that exited non-zero when graphify was absent, looping the Stop hook; a full update already drops it via the install-dir replace, but a symlink-only repair did not

---

## [1.9.0] — 2026-07-16

### Added
- `scripts/fix-symlinks.sh` — repairs `.claude/` links materialized as plain files instead of symlinks (Windows without Developer Mode / `core.symlinks`); auto-fixes when the OS allows and otherwise prints three remediation options. Detected automatically at session start (`[DEVTEAM:SYMLINK_BROKEN]`) and verified at install time; health-check Category 1 now distinguishes OK / MATERIALIZED / MISSING

### Changed
- Documented the Windows materialized-symlink repair flow across README (EN/pt-BR) and the installation guide

---

## [1.8.2] — 2026-06-29

### Fixed
- `graphify-refresh.sh` exits `0` on skip instead of non-zero, preventing a Stop-hook loop when graphify is not installed

---

## [1.8.1] — 2026-06-28

### Fixed
- Removed an unused `_notify` function in `session-start.sh`

---

## [1.8.0] — 2026-06-28

### Added
- `/devteam:learn` command for consolidating session decisions, patterns, and discoveries into docs, wiki, and ADRs
- Post-execution review step in `software-architect` and auto-learn hand-off in `/devteam:commit`

---

## [1.7.4] — 2026-06-28

### Fixed
- Suppress WSL `BASH_ENV` bashrc noise on hook invocation (follow-up to 1.7.3)

---

## [1.7.3] — 2026-06-24

### Fixed
- Suppress WSL `BASH_ENV` bashrc noise on hook invocation

---

## [1.7.2] — 2026-06-24

### Fixed
- Enforce LF line endings in the target project `.gitattributes` on install

---

## [1.7.1] — 2026-06-24

### Added
- First-time setup guard with quiz in `project-context`
- `SessionStart` emits a structured signal when `preferences.json` is missing
- Installer injects a pre-compact auto-summary rule into the project `CLAUDE.md`; health-check detects and auto-fixes it when missing

### Changed
- Added `.gitattributes` to enforce LF line endings in the repository

---

## [1.7.0] — 2026-05-18

### Added
- Anonymous usage telemetry via PostHog, wired into `install.sh` and `update.sh`; `PRIVACY.md` documents what is collected and how to opt out

---

## [1.6.7] — 2026-05-18

### Fixed
- Prune stale skill symlinks during update
- Resolve shellcheck warnings in hook and lint scripts

---

## [1.6.6] — 2026-05-18

### Fixed
- Anchor the fingerprint uniqueness check to registration lines only

---

## [1.6.5] — 2026-05-18

Large refactor/performance release focused on reducing per-session and per-spawn context-budget usage.

### Added
- `stack-detection` skill wired to agents; iOS and Android platform skills
- `interaction-patterns` skill (quiz-first rule) and `push-notifications` skill
- `validate-commit-msg.sh` gate in `/devteam:commit`; `workflow-mobile` and `workflow-design` shortcut commands
- Fingerprint uniqueness check, orphan-template scanner, and additional CI scans

### Changed
- Fragmented `CLAUDE.md` into `CLAUDE-md/` sub-files; extracted large inline sections across agents and skills (project-context, mobile, integrations, frontend, ui-ux) to `references/` subdirectories
- Moved dev-only tools to `helpers/`; moved the context-cache path to `user-data/`; canonicalized tools order; added the Hook Files Map
- Made agents stack-agnostic — removed Docker-first and stack-prescriptive language

### Fixed
- Restored the worktree session-file gate across coding agents; hardened `rollback.sh` and `pre-compact.sh` guards; corrected the CI fast-path comparison and fingerprint regex

---

## [1.6.4] — 2026-05-13

### Fixed
- README sync check compares section counts instead of header text

---

## [1.6.3] — 2026-05-13

### Added
- `release-prep` skill; ADR, backlog-item, and runbook templates
- Context cache, discovery lockfile, and graphify skip conditions; PreCompact hook and rollback script
- `conventional-commits` `validate.sh`; size-limits check; mobile and design workflows

### Changed
- Reduced file sizes across architect, database, setup, and reviewer agents; extracted large devops and docs skills to `references/`
- Extended orphan-skill-scan to cover `commands/` and `workflows/`; added Portuguese translations for agents and installation guides

### Fixed
- Implemented the worktree session-file gate in all coding agents; removed non-canonical frontmatter keys from design skills

---

## [1.6.2] — 2026-05-12

### Changed
- Restructured README for first-time readability; extracted the agent reference and installation guide to `docs/`

---

## [1.6.1] — 2026-05-12

### Added
- `/devteam:mobile` and `/devteam:adr` commands
- Plan-gate enforcement across all implementation commands; context estimation via transcript tokens with a preferences fallback

### Changed
- Reduced the git-log window from `-20` to `-10` across 10 agents; expanded the preferences schema (`transcript_multiplier`, `model_max_tokens`)

### Fixed
- Disabled Claude co-authoring in git artifacts and added a Jira REST API fallback; reclassified plans as conversation items using the user's preferred language; added a daily gate to the notifier tip-of-session; fixed the graphify-setup skill path in `setup-assistant`

---

## [1.6.0] — 2026-05-11

### Added
- `mobile-developer` agent with React Native, Expo, and Flutter skills
- Material Design 3 and iOS HIG mobile design skills

---

## [1.5.5] — 2026-05-11

### Fixed
- `check-updates.sh` no longer exits with code 1 when the GitHub API returns an empty response

---

## [1.5.4] — 2026-05-11

### Fixed
- Exclude repo-only files from the distributed package
- Remove the rollback feature and `.previous` directory from the installer

---

## [1.5.3] — 2026-05-11

### Changed
- Trimmed all skill descriptions to reduce context-budget usage

---

## [1.5.2] — 2026-05-11

### Fixed
- Jira MCP setup checks deferred tools via ToolSearch before showing setup instructions

---

## [1.5.1] — 2026-05-11

### Fixed
- Skip the Graphify prompt when already configured; strip `agent-lint.sh` from the distributed package

---

## [1.5.0] — 2026-05-11

### Added
- User preferences system (`preferences.json`) with a language prompt on install; notification system and the `04-notifier.sh` stop sub-script
- `user-preferences` and `notifier` shared skills; per-engine database skills for all 7 engines
- Architecture skills (event-driven, rate-limiting, api-versioning); `diataxis-framework`; fullstack workflow; recovery paths in all workflows
- Community health files and GitHub templates; rollback support in the installer/update script; session-start staleness hook

### Changed
- Migrated command context detection to the `current-context` skill and `spawn-classifier`; rewrote `/devteam:refactor` with test-first coverage and dependency mapping; expanded database-specialist engine detection
- Untracked `session-summary.md` and added it to `.gitignore`

### Fixed
- Removed the manual shellcheck `apt-get install` step in CI

---

## [1.4.0] — 2026-05-10

### Added
- MIT `LICENSE` file
- `.github/workflows/ci.yml` — frontmatter validation, orphan scan, shellcheck, README sync check
- `scripts/agent-lint.sh` — validates frontmatter on all `agents/*.md`
- Stop hook sub-scripts: `02-orphan-skill-scan.sh`, `03-agent-lint.sh`
- Orphan skill scan Phase 3: duplicate skill detection

### Changed
- `.claude/settings.json` uses the stop dispatcher (`scripts/hooks/stop.sh`) instead of direct orphan scan
- Fixed 23 real duplicate skill references across 6 agents

---

## [1.3.16] — 2026-05

### Added
- `/devteam:update` command for checking and applying updates
- 13 new skills across security, testing, database, devops, and integrations
- 7 new architecture skills; updated `api-design`
- 7 new shared skills; refactored `comments-policy` (417 → 76 lines)
- `workflows/refactor.md` and `workflows/review.md`
- Jira integration section in 7 agents; `skills/integrations/jira/SKILL.md`

### Changed
- Refactored 4 agents by extracting skills: `db-comparison`, `setup-health-check`, `frontend-patterns`, `ssh-remote-access`
- `/devteam:*` commands namespaced (were `/devteam-*`)
- `session-summary.md` moved to `user-data/` directory

---

## [1.3.0] — 2026-05

### Added
- Comprehensive `/devteam:*` slash commands (plan, backend, frontend, fullstack, fix, refactor, architect, review, qa, security, dba, devops, tester, docs, pr, design, commit, update)
- Graphify integration for visual codebase navigation
- Wiki knowledge base system (`docs/wiki/`)
- Contradiction Guard in `project-context` skill

### Changed
- Agents enforce human-only authorship in git artifacts (no Claude attribution)
- `setup-assistant` adds audit step, devops/tests doc dirs

---

## [1.2.0] — 2026-04

### Added
- `skills/shared/` modular skill system
- `agent-creator` and `skill-creator` skills
- Release preparation skill (`release-prep`)
- `session-summary.md` per-session notes (multi-agent append pattern)

### Changed
- Skills extracted from agents to reduce inline duplication
- Auto-routing skill for agent delegation

---

## [1.1.0] — 2026-04

### Added
- Core agent roster: `backend-developer`, `frontend-developer`, `database-specialist`, `devops-specialist`, `qa-specialist`, `security-specialist`, `software-architect`, `product-analyst`, `technical-writer`, `code-reviewer`, `setup-assistant`
- Worktree isolation pattern for coding agents
- `skills/shared/project-context/SKILL.md` — foundational context loader
- `skills/shared/conventional-commits/SKILL.md`
- Pre-tool-use update check hook (`01-check-updates.sh`)
- Stop hook for session summary (`01-session-summary.sh`)
- Orphan skill scan (`scripts/orphan-skill-scan.sh`)

---

## [1.0.0] — 2026-03

### Added
- Initial release: installer (`scripts/install.sh`), updater (`scripts/update.sh`)
- 5 core workflows: `new-project`, `bug-fix`, `maintenance`, `inherited-project`, `security-patch`
- `templates/plan-template.md`
- `CLAUDE.md` authoring standards

[Unreleased]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.9.3...HEAD
[1.9.3]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.9.2...v1.9.3
[1.9.2]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.9.1...v1.9.2
[1.9.1]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.9.0...v1.9.1
[1.9.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.8.2...v1.9.0
[1.8.2]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.8.1...v1.8.2
[1.8.1]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.8.0...v1.8.1
[1.8.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.7.4...v1.8.0
[1.7.4]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.7.3...v1.7.4
[1.7.3]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.7.2...v1.7.3
[1.7.2]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.7.1...v1.7.2
[1.7.1]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.7.0...v1.7.1
[1.7.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.7...v1.7.0
[1.6.7]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.6...v1.6.7
[1.6.6]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.5...v1.6.6
[1.6.5]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.4...v1.6.5
[1.6.4]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.3...v1.6.4
[1.6.3]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.2...v1.6.3
[1.6.2]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.1...v1.6.2
[1.6.1]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.0...v1.6.1
[1.6.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.5...v1.6.0
[1.5.5]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.4...v1.5.5
[1.5.4]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.3...v1.5.4
[1.5.3]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.2...v1.5.3
[1.5.2]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.1...v1.5.2
[1.5.1]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.0...v1.5.1
[1.5.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.3.16...v1.4.0
[1.3.16]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.3.0...v1.3.16
[1.3.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Dev-Toolbelt/dev-team-agents/releases/tag/v1.0.0
