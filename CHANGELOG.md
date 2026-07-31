# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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
