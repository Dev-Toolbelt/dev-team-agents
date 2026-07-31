# Token Economy — v2 Carry-Over

**Axis:** `token-*` · **Verified against:** `HEAD` = `7f85ed7`

The largest axis by volume (86 candidates, 45 survivors). Its defining pattern: **the repo consistently identifies the right lazy-loading mechanism, applies it in one place, and never propagates it.** Detection gates, `references/` splits and one-line skill delegation all exist and all work — they were simply never rolled out past the first adopter.

Several survivors have measurably **worsened** since the v1 window:

| Item | v1 measurement | HEAD |
|---|---|---|
| `docs/reports/_index.md` | 647 lines | **850** |
| `scripts/install.sh` | 503 lines | **803** |
| `CHANGELOG.md` | ~130 lines | **441** |
| `skills/shared/project-context/SKILL.md` | 266 lines | **321** |
| `backend-developer` integrations inlined | 7 | **8** |
| Skill descriptions over 95 chars | 16 | **20** |
| `skills/shared/plan-mode/SKILL.md` | 131 lines | **199** |
| `.claude/agents/dev-team/` path repetitions | ~40 | **72** |

---

## MEDIUM-HIGH

### `CLAUDE.md` is still monolithic at 425 lines while `CLAUDE-md/` fragmentation is already live

- **Fingerprint:** `token-claude-md-426-lines-still-monolithic-three-extractable-blocks-commands-table-40-stop-sub-script-convention-24-hook-files-map-8-total-72-lines-while-claude-md-folder-already-exists-with-preferences-notifications-user-data-versioning`
- **Evidence:** `CLAUDE.md:143` — "#### User-Invocable Commands" with a table spanning 143-181 (39 lines); `:336` "### Stop Hook Sub-script Convention" and `:356` "### Hook Files Map" spanning 336-366 (31 lines). `CLAUDE-md/` already contains `preferences.md`, `notifications.md`, `user-data.md`, `versioning.md`.
- **Problem:** Phase 1 of the fragmentation shipped and was accepted, but the three largest remaining blocks are still inline. Roughly 105 lines (262-366, the whole Agent Memory System) are extractable.
- **Why it matters at HEAD:** `CLAUDE.md` is read at session start **and** by every agent's Foundational Rule step 2, so the extractable lines are re-paid on every spawn in multi-agent commands. The barrier is not architectural — the destination directory exists.

### The Foundational Rule block is duplicated inline across 17 agents (384 lines total)

- **Fingerprint:** `token-foundational-rule-424-lines-across-17-agents`
- **Evidence:** `agents/backend-developer.md:13-39` (27 lines) — "1. `README.md` … 12. Run `git log --oneline -10`"; the same 12-item list recurs at `frontend-developer.md:13-36`, `mobile-developer.md:13-35`, `devops-specialist.md:13-37`, `code-reviewer.md:32-59` and 12 more. Measured total: **384 lines**.
- **Problem:** Items 1-4 plus the closing "Project rules override base standards" / token-efficiency / plan-mode lines are near-verbatim identical fleet-wide, even though `skills/shared/project-context/SKILL.md` is the documented canonical source.
- **Why it matters at HEAD:** **Two agents already prove the fix works** — `database-specialist:15` and `software-architect:15` delegate with a single line. The other 15 still carry the expanded copy.

---

## MEDIUM

### The `token-efficiency` skill (154 lines) is eager-loaded by 16 agents, against `CLAUDE.md`'s own instruction

- **Fingerprint:** `token-token-efficiency-skill-itself-154-lines-eager-loaded-by-all-17-agents-meta-irony-multiplied-in-multi-agent-flows`
- **Evidence:** The load appears in the Foundational Rule of 16 agents (`backend-developer:32`, `backend-reviewer:38`, `backend-test-specialist:62`, `code-reviewer:54`, `database-specialist:24`, `devops-specialist:32`, `frontend-developer:31`, `frontend-reviewer:37`, `frontend-test-specialist:63`, `mobile-developer:30`, `qa-specialist:41`, `security-specialist:38`, `setup-assistant:19`, `software-architect:24`, `technical-writer:26`, `ui-ux-designer:25`). Against `CLAUDE.md:120` — "Key rules (apply without loading the full skill):" followed by the four rules, with the full load scoped to three narrow authoring cases.
- **Problem:** `CLAUDE.md` explicitly says the key rules apply *without* loading the skill; every agent loads it unconditionally anyway.
- **Why it matters at HEAD:** ~2k tokens × 16 agents. A `/devteam:fullstack` or `/devteam:review` fan-out pays it 4-6 times in one command.

### `project-context` inlines an eager Docker section while gating SonarQube in the same file

- **Fingerprint:** `token-project-context-docker-development-environment-section-22-lines-inlined-eager-loaded-by-14-agents-while-sonarqube-same-file-is-detection-gated`
- **Evidence:** `skills/shared/project-context/SKILL.md:272-296` — "## Docker Development Environment" (25 lines of inline command tables). Contrast `:260-268` — "## Quality / Security Scanners … | Detection | Skill to load | … `sonar-project.properties` … → `skills/devops/sonarqube/SKILL.md`".
- **Problem:** Two equally detection-conditional topics, eight lines apart, treated in opposite ways: SonarQube is a two-line detection row pointing at an external skill; Docker is 25 inline lines.
- **Why it matters at HEAD:** Loaded by all 14 context-loading agents; on non-Docker projects it is pure dead weight. The file has grown to 321 lines.

### `qa-specialist` eager-loads `security-checklist` (123 lines) while gating SonarQube eight lines below

- **Fingerprint:** `token-qa-specialist-eager-loads-security-checklist-123-lines-every-spawn-though-behavioral-qa-often-no-security-scope-sonarqube-gated-in-same-file`
- **Evidence:** `agents/qa-specialist.md:35` — "Load `security-checklist` skill…" (unconditional) vs `:43` — "**SonarQube / SonarCloud** — **if** `sonar-project.properties` … is present, load…".
- **Problem:** The same internal contrast as `project-context` above: one skill detection-gated, the adjacent 123-line one not, even though behavioral QA frequently has no security scope.
- **Why it matters at HEAD:** Five commands spawn `qa-specialist`. See also the [ownership-boundary dimension in 03](03-agentes-e-skills.md).

### `conventional-commits` (138 lines) is a mandatory Foundational Rule step in all three reviewers

- **Fingerprint:** `token-conventional-commits-138-lines-eager-loaded-by-code-reviewer-and-backend-reviewer-and-frontend-reviewer-agents-commit-validation-not-in-scope-every-review`
- **Evidence:** `agents/code-reviewer.md:45` — "10. Load `skills/shared/conventional-commits/SKILL.md` — validate that commit messages in the changeset follow the project's convention"; same numbered item at `backend-reviewer.md:32` and `frontend-reviewer.md:31`.
- **Problem:** Unconditional even for working-tree or single-file reviews where there are no commits, and even when the project uses a non-Conventional pattern.
- **Why it matters at HEAD:** `/devteam:review` spawns `code-reviewer`, which routes to `backend-reviewer`/`frontend-reviewer` → 2-3 loads of the same 138 lines per review.

### `code-reviewer` still eager-loads `comments-policy` as a Foundational Rule step

- **Fingerprint:** `token-code-reviewer-still-eager-loads-comments-policy-after-lazy-load-fix-applied`
- **Evidence:** `agents/code-reviewer.md:44` — "9. Load `skills/shared/comments-policy/SKILL.md`…" — item 9 of the numbered rule, i.e. unconditional at startup.
- **Problem:** The lazy-load fix that landed for other agents never reached the most frequently spawned reviewer.
- **Why it matters at HEAD:** `code-reviewer` is invoked by seven `/devteam:*` commands.

### `/devteam:review` fan-out reloads the same shared skill package in every isolated spawn

- **Fingerprint:** `token-review-shared-skills-reloaded-by-router-then-each-specialist-2-3x-fanout-per-devteam-review-no-shared-loaded-context`
- **Evidence:** `commands/review.md` spawns `code-reviewer`, `software-architect`, `security-specialist`, `qa-specialist` in parallel plus conditional `database-specialist` / `mobile-developer`, and `code-reviewer` routes internally to the two reviewers. Each spawn independently re-executes its Foundational Rule: `project-context` (**321** lines), `token-efficiency` (154), `conventional-commits` (138), `comments-policy`, `reviewer-base`/`reviewer-mindset`.
- **Problem:** No mechanism passes a factual summary between spawns.
- **Why it matters at HEAD:** The fan-out widened (4 unconditional + 2 conditional + 2 internal routes) and `project-context` grew 266 → 321, so the per-review multiplier is larger than when reported.

### `product-analyst` loads the 237-line `backlog-template` skill unconditionally

- **Fingerprint:** `token-backlog-template-skill-171-lines-unconditionally-loaded-every-product-analyst-spawn-diverged-from-physical-template-same-name`
- **Evidence:** `agents/product-analyst.md:22` — "6. Load `skills/shared/backlog-template/SKILL.md`" as a numbered Foundational Rule step. The skill is now **237** lines (was 171); the same-named `templates/backlog-template.md` is 35.
- **Problem:** Loaded at startup even in pure discovery turns that produce no backlog.
- **Why it matters at HEAD:** `/devteam:plan` makes `product-analyst` the protagonist of every planning command, and the skill grew 39% since the finding. See the [orphan-template dimension in 01](01-referencias-e-consistencia.md).

### `plan-mode` (199 lines) is loaded by 7 agents *and* 16 commands — duplicated, not moved

- **Fingerprint:** `token-plan-mode-skill-131-lines-loaded-by-7-agents-unconditionally`
- **Evidence:** "Follow `skills/shared/plan-mode/SKILL.md`" appears in the Foundational Rule of `backend-developer:34`, `code-reviewer:56`, `database-specialist:26`, `devops-specialist:34`, `frontend-developer:33`, `mobile-developer:32`, `software-architect:22`; 16 command files also load it in their PLAN GATE.
- **Problem:** The intended fix was to **move** the load to the command layer. Instead the command load was added and the seven agent loads stayed, so `/devteam:backend` now pays it at both layers.
- **Why it matters at HEAD:** The skill is 52% larger than when reported (131 → 199) and now double-loaded per command.

### `frontend-code-quality` has a 288-character description — 3× the budget, with a 67-char meta-narrative tail

- **Fingerprint:** `token-frontend-code-quality-description-288-chars-cauda-loaded-by-frontend-developer-as-authoritative-redundant-trim-target-70-chars-pior-offender-confirmado-na-relista-de-2026-05-26`
- **Evidence:** `skills/architecture/frontend-code-quality/SKILL.md:3` — the description ends "…**Loaded by frontend-developer as the authoritative quality baseline.**" (67 of the 288 chars).
- **Problem:** The tail describes internal wiring rather than what the skill is for. Comparison: `skills/architecture/graphql/SKILL.md` describes a 235-line skill in 59 chars.
- **Why it matters at HEAD:** Still the single worst offender. The file itself is only 35 lines, so the description is ~10% of the skill's total weight.

### `scripts/install.sh` grew to 803 lines with three functions and no decomposition

- **Fingerprint:** `token-install-sh-503-lines-largest-single-script-not-fragmented-vs-stop-dispatcher-pattern-13-functions-extractable-each-100-tokens`
- **Evidence:** **803** lines (was 503). Only three function definitions: `_is_materialized()` at `:315`, `_add_gitignore()` at `:563`, `_add_gitattributes()` at `:586`. Everything else is linear top-level script.
- **Problem:** The Stop-dispatcher decomposition pattern was never applied to the installer, which remains the largest single script in the repo by a wide margin.
- **Why it matters at HEAD:** It grew **60%** since the finding, and `scripts/lib/` now exists (`strip-tarball.sh`, `ensure-claude-framework.sh`), so the extraction target is available — the barrier is no longer structural.

### `_telemetry_enabled()` is defined three times across the telemetry scripts

- **Fingerprint:** `token-telemetry-helper-289-lines-loaded-by-2-sub-scripts-plus-install-update-shell-fork-overhead-150ms-per-event-burst-mode-burns-200ms-acumulado`
- **Evidence:** `scripts/helpers/telemetry-send.sh:42`, `scripts/hooks/stop/05-telemetry.sh:19`, and `scripts/hooks/pre-tool-use/02-telemetry.sh:16` each define the function. `telemetry-send.sh` is 289 lines and is re-forked per event (`scripts/update.sh:85-89` calls it twice).
- **Problem:** Three copies of the enablement gate and no shared library; each event spawns a fresh 289-line bash process rather than batching.

### `04-notifier.sh` inlines 45 tip strings to emit at most one per day

- **Fingerprint:** `token-notifier-loads-45-tips-3-languages-emits-1-per-day-99pct-waste`
- **Evidence:** `scripts/hooks/stop/04-notifier.sh:175` — `TIPS_EN=(` (15 entries), `:193` — `TIPS_PTBR=(` (15), `:211` — `TIPS_ES=(` (15). Selection at `:173` — `TIP_INDEX=$(( (DAY - 1) % 15 ))`, gated once per session at `:171`.
- **Problem:** All 45 strings are parsed from disk on every Stop-hook invocation to emit exactly one, from one locale.
- **Why it matters at HEAD:** Externalising to `tips/{locale}.json` would read at most a third of the data, and only when the daily gate opens. The script is now 240 lines. See the [triplication dimension in 01](01-referencias-e-consistencia.md).

---

## LOW-MEDIUM

### `commands/commit.md` loads `conventional-commits` "before doing anything", then may discard it

- **Fingerprint:** `token-conventional-commits-skill-138-lines-loaded-by-commit-and-pr-commands-but-also-mentioned-as-skill-load-in-claude-md-skill-loads-by-table-format-not-prose`
- **Evidence:** `commands/commit.md:1` — "Load the skill at `skills/shared/conventional-commits/SKILL.md` before doing anything." vs `:28` — "If a project-specific pattern is documented → **follow it exclusively** and discard the Conventional Commits default."
- **Problem:** 138 lines loaded up front and possibly thrown away in Step 1. Moving the load *after* pattern detection makes it free on projects with a custom convention.

### The `comments-policy` load directive is duplicated verbatim in exactly 8 agents

- **Fingerprint:** `token-comments-policy-load-directive-duplicated-in-8-agents-multiplied-per-session-in-multi-agent-flows-fullstack-review-spawn-many-agents`
- **Evidence:** `grep -rn "type-annotations, tests → aaa-pattern" agents/` returns 8 hits — `backend-developer:217`, `backend-reviewer:31`, `backend-test-specialist:98`, `code-reviewer:44`, `database-specialist:128`, `devops-specialist:205`, `frontend-reviewer:30`, `frontend-test-specialist:202` — each reading "Load additional sections conditionally based on context (Python → type-annotations, tests → aaa-pattern, legacy review → anti-patterns)".
- **Problem:** A skill's own section-routing rule lives in 8 agents instead of in the skill.
- **Why it matters at HEAD:** Changing the routing requires 8 synchronized edits. The inverse problem — the skill being **missing** from 9 other agents — is in [03](03-agentes-e-skills.md).
- **Merged from:** 2 v1 fingerprints (`token-*` + `ref-*`).

### The `docs-sync` closing directive is duplicated across 13 agents and has begun to drift

- **Fingerprint:** `token-docs-sync-closing-directive-after-completing-any-task-duplicated-verbatim-across-twelve-agents-no-single-source-multiplied-in-multi-agent-flows`
- **Evidence:** A byte-identical sentence at `backend-developer:255`, `backend-test-specialist:154`, `database-specialist:178`, `devops-specialist:233`, `frontend-developer:226`, `frontend-test-specialist:256`, `security-specialist:230`, `software-architect:362`, `technical-writer:175`, `ui-ux-designer:165` — plus **drifted variants** at `mobile-developer:195` and `product-analyst:166` that add "Run in parallel with the commit".
- **Why it matters at HEAD:** The count went from 12 to 13 agents and **the drift the v1 finding predicted has materialized**.

### The SonarQube detection triple is restated in 11 agents plus `project-context`

- **Fingerprint:** `token-sonarqube-detection-block-redundant`
- **Evidence:** `sonar-project.properties` / `.sonarcloud.properties` / `SONAR_TOKEN` appears at `backend-developer:155`, `backend-reviewer:33`, `backend-test-specialist:109`, `code-reviewer:46`, `devops-specialist:95`, `frontend-developer:184`, `frontend-reviewer:32`, `frontend-test-specialist:208`, `mobile-developer:139`, `qa-specialist:43`, `security-specialist:111` — **and** canonically at `skills/shared/project-context/SKILL.md:266`.
- **Problem:** `project-context` is loaded by all of them, so all 11 copies are redundant.
- **Why it matters at HEAD:** Grew from 10 to 11 agents; the canonical row was added without removing any copy.

### The Worktree Isolation cascade is duplicated across 8 coding agents and doubled in size

- **Fingerprint:** `token-worktree-isolation-block-7-lines-x-8-agents`
- **Evidence:** `agents/backend-developer.md:68-82` and the same three-branch cascade in `backend-test-specialist`, `database-specialist`, `devops-specialist`, `frontend-developer`, `frontend-test-specialist`, `mobile-developer`, `ui-ux-designer`.
- **Problem:** The cascade is fully specified in `CLAUDE.md:70-80` **and** in `skills/shared/worktree/SKILL.md`, yet each agent restates all three branches.
- **Why it matters at HEAD:** The block grew from ~7 to ~15 lines per agent (≈120 duplicated lines), so the cost roughly doubled.

### 20 skill descriptions exceed the 95-char budget and no lint gate measures length

- **Fingerprint:** `token-sixteen-skill-descriptions-exceed-95-char-budget-worst-288-inflate-always-loaded-skill-index-regression-of-v1-5-3-trim-no-lint-gate`
- **Evidence:** Measured across `skills/**/SKILL.md`: **20** over budget. Worst: `frontend-code-quality` (288), `frontend-done-checklist` (250), `mobile-design` (250), `architecture-awareness` (247). `helpers/agent-lint.sh:94` checks presence only; `:100-107` checks for non-canonical keys; nothing measures length.
- **Why it matters at HEAD:** Descriptions feed the always-loaded skill index across 133 skills, making this the highest-leverage per-character cost in the repo. The count **regressed from 16 to 20** and no gate was added.

### The `current-context` preamble is copy-pasted into 19 command files

- **Fingerprint:** `token-current-context-block-deduplication`
- **Evidence:** An identical opening line in `commands/{adr,architect,audit,backend,dba,design,devops,docs,fix,frontend,fullstack,mobile,plan,pr,qa,refactor,review,security,tester}.md` — 19 files.
- **Problem:** Copy-paste preamble instead of a shared include; the `interaction-patterns` line directly under it has the same issue.
- **Why it matters at HEAD:** Grew from 18 to 19 files.

### `rollback.sh` duplicates `update.sh`'s HTTP detection and installer-download logic

- **Fingerprint:** `token-rollback-sh-65-lines-duplicates-installer-download-from-update-sh`
- **Evidence:** `scripts/rollback.sh:57-64` is byte-for-byte the `if command -v curl … elif command -v wget …` construct at `scripts/update.sh:43-49`; both also define the identical `GITHUB_OWNER`/`GITHUB_REPO`/`INSTALL_URL` triple and the same `mktemp` + `trap` + download + `bash` + cache-clear sequence.
- **Problem:** No `scripts/lib/install-fetch.sh` was created, though `scripts/lib/` now exists.
- **Why it matters at HEAD:** `rollback.sh` grew 65 → 89 lines, widening the duplicated surface.

### `CHANGELOG.md` reached 441 lines with no rotation and no archive tooling

- **Fingerprint:** `token-changelog-already-growing-and-not-extracted-by-release`
- **Evidence:** **441** lines / 33 KB (was ~130 when first flagged), past the 300-line threshold the v1 finding proposed. No `archive-changelog.sh` exists. The `[Unreleased]` section alone runs ~20 dense entries.
- **Why it matters at HEAD:** The predicted growth materialized (~3.4×). `technical-writer`, `/devteam:docs`, `/devteam:learn` and `skills/shared/release-prep/SKILL.md` all read it.

---

## LOW

### The "Project rules override base standards" sentence is repeated in 14 agents

- **Fingerprint:** `token-project-rules-override-prose-duplicate`
- **Evidence:** One occurrence each in 14 agents, e.g. `agents/backend-developer.md:30`, `frontend-developer.md:29`, `code-reviewer.md:52`, `qa-specialist.md:27`, `security-specialist.md:40`, `technical-writer.md:30`, `ui-ux-designer.md:27`.
- **Problem:** The Coexistence Rule is already canonical at `CLAUDE.md:421`; each agent restates it with a slightly different lead-in.

### Skill-load declarations are split between tables and prose with no rule

- **Fingerprint:** `token-skill-loads-via-table-vs-prose-inconsistent`
- **Evidence:** All-table: `devops-specialist` (18 rows / 0 prose), `software-architect` (17/0), `database-specialist` (15/0). All-prose: `frontend-reviewer` (0/8), `security-specialist` (0/8), `code-reviewer` (0/7). Mixed: `frontend-developer` (11/3).
- **Problem:** Two incompatible conventions coexist; the prose form is roughly 2× the characters per declaration.
- **Why it matters at HEAD:** `CLAUDE.md:88` prescribes "Prefer tables and bullets over prose" for skills but nothing enforces it for agent skill-load blocks.

### The `.claude/agents/dev-team/` path prefix is repeated 72 times across command files

- **Fingerprint:** `token-agent-path-prefix-redundant`
- **Evidence:** 72 occurrences across 20 files in `commands/`; heaviest are `refactor.md` (11), `fullstack.md` (8), `audit.md` (6), `review.md` (6).
- **Why it matters at HEAD:** Grew from ~40 to 72 as commands were added.

### `git log --oneline -20` is used where `-10` is the documented default

- **Fingerprint:** `token-git-log-window-overshoot`
- **Evidence:** `agents/security-specialist.md:36`, `ui-ux-designer.md:23`, `qa-specialist.md:24`, `technical-writer.md:23`, and `skills/shared/setup-scan/SKILL.md:16` use `-20`. The canonical Foundational Rule and the Commit Rule at `CLAUDE.md:371` use `-10`.
- **Problem:** Two windows for the same purpose with no stated rationale for the wider one.

### `commands/commit.md` and `refactor.md` remain far above the command-file median

- **Fingerprint:** `token-commands-commit-md-145-lines-and-refactor-md-156-lines-largest-command-files`
- **Evidence:** `commit.md` is now **177** lines and `refactor.md` **159**, against a median of ~49 across 24 command files. Two files have since overtaken them: `learn.md` (229) and `audit.md` (192).
- **Why it matters at HEAD:** The four largest total 757 lines — ~39% of the entire `commands/` tree (1,959 lines). The oversize class **expanded** rather than shrank. See the missing size gate in [02](02-fluxos-e-workflows.md).

### The READMEs are maintained as two full-length sources with no section anchors

- **Fingerprint:** `token-readme-228-each-after-extraction-still-2-files-no-cross-link-tagging`
- **Evidence:** `README.md` and `README.pt-BR.md` are **329 lines each**. `grep -c '@section'` → 0 for both. The pairing has since expanded to three pairs checked by `.github/scripts/ci/02-readme-sync.sh:34-36`.
- **Problem:** No structural anchors exist to let tooling map EN sections onto pt-BR sections, so sync is enforced by heuristics that cannot detect in-section drift.
- **Why it matters at HEAD:** The manual-sync burden **tripled** — three pairs totalling ~1,180 lines now carry the README Sync Rule obligation.

### The anti-duplication step reads the full 850-line prose index to recover a flat slug list

- **Fingerprint:** `token-dedup-step-reads-full-676-line-prose-index-md-every-run-when-only-fingerprint-slug-list-is-needed-extract-machine-readable-list`
- **Evidence:** `docs/reports/_index.md` is 850 lines of prose and tables; no `docs/reports/_fingerprints.txt` sidecar exists. `helpers/check-fingerprint-uniqueness.sh:14` already proves the slugs are greppable in one line: `grep -E "^- \`[a-z][a-z0-9-]+" "$INDEX_FILE"`.
- **Why it matters at HEAD:** **Partially addressed by this report** — the `_index.md` rewrite drops the file substantially. The missing machine-readable sidecar and the unwired rotation ([02](02-fluxos-e-workflows.md)) remain.

### Token-efficiency rules are mandated with no measurement or feedback loop

- **Fingerprint:** `token-skills-shared-token-efficiency-not-quantified-in-CLAUDE-md-line-218-no-baseline-roi-tracking`
- **Evidence:** `CLAUDE.md:113` — "#### Token Efficiency"; `:120` — four unquantified rules. No Stop sub-script measures context or token usage; `helpers/size-limits.sh` measures line counts only.
- **Problem:** Four normative rules with no observable metric, so **no `token-*` recommendation across 20 v1 audits could ever be validated as having paid off** — which is a plausible contributing cause of this axis having both the largest backlog and the most regressions.
- **Why it matters at HEAD:** The repo carries `helpers/size-limits.sh` and `helpers/agent-lint.sh`, proving the enforcement-script pattern is accepted; the token dimension simply has no equivalent.

---

## Cross-references

| Finding | Filed under |
|---|---|
| `backend-developer` inlines critical rules for 8 integrations | [03 — Agents and Skills](03-agentes-e-skills.md) |
| `security-specialist` inline scanner command block | [03 — Agents and Skills](03-agentes-e-skills.md) |
| `backend-test-specialist` SonarQube coverage matrix in body | [03 — Agents and Skills](03-agentes-e-skills.md) |
| `frontend-test-specialist` loads both React and Vue recipes | [03 — Agents and Skills](03-agentes-e-skills.md) |
| Three reviewers share ~65% of their structure | [03 — Agents and Skills](03-agentes-e-skills.md) |
| `setup-assistant` inline Docker block / duplicate warning | [03 — Agents and Skills](03-agentes-e-skills.md) |
| `architecture-awareness` loads both web halves eagerly | [03 — Agents and Skills](03-agentes-e-skills.md) |
| `_index.md` at 850 lines with rotation wired to nothing | [02 — Flows](02-fluxos-e-workflows.md) |
| `01-check-updates.sh` forks python before its TTL exit | [02 — Flows](02-fluxos-e-workflows.md) |
| Orphan template scan ungated on every Stop | [02 — Flows](02-fluxos-e-workflows.md) |
| `templates/` never symlinked — load paths unreachable | [01 — References](01-referencias-e-consistencia.md) |
| Package-exclusions table duplicates the installer's strip rules | [01 — References](01-referencias-e-consistencia.md) |
