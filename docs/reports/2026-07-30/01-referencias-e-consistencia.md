# References and Consistency — v2 Carry-Over

**Axis:** `ref-*` + `docs-*` · **Verified against:** `HEAD` = `7f85ed7`

Findings that still reproduce in the v2 tree. Every entry was re-verified file by file; line numbers below are current, not the ones quoted in the v1 reports.

---

## HIGH

### `docs/agents.md` Model column is wrong for 2 of 17 agents, mirrored into pt-BR, and unvalidated

- **Fingerprint:** `ref-docs-agents-md-model-column-wrong-technical-writer-listed-haiku-actually-sonnet-and-setup-assistant-listed-sonnet-actually-opus`
- **Evidence:** `docs/agents.md:26` — "| `technical-writer` | … | SUPPORT | Haiku |"; `:27` — "| `setup-assistant` | … | SETUP | Sonnet |"; `:79` — "Assigned Haiku for cost efficiency…". Ground truth: `agents/technical-writer.md` declares `tier: repetitive` → `scripts/lib/tiers.json` maps `repetitive.claude = "claude-sonnet-4-6"`; `agents/setup-assistant.md` declares `tier: reasoning` → `claude-opus-4-7`. Mirrored at `docs/agents.pt-BR.md:26,27,79`.
- **Problem:** Three defects in one surface. (a) The canonical agent reference misstates 2/17 models. (b) The README Sync Rule faithfully propagated the error into the translation, so both canonical references are wrong. (c) `.github/scripts/ci/02-readme-sync.sh:12-27` compares only `^## ` heading counts and a ±50% line threshold — it prints `Sync OK` on factually wrong data.
- **Why it matters at HEAD:** `tiers.json` contains **no Haiku model id for any tier**, so the table advertises a model the render engine cannot emit. The v2 tier→model indirection makes a hand-maintained Model column strictly more drift-prone than the old `model:` key it replaced.
- **Merged from:** 3 v1 fingerprints across the `ref-*` and `auto-*` axes.

### `CLAUDE.md` states `code-reviewer` delegates to the test specialists; it routes to the reviewers

- **Fingerprint:** `ref-claude-md-183-code-reviewer-roles-says-delegates-to-test-specialists-but-impl-routes-to-backend-frontend-reviewer`
- **Evidence:** `CLAUDE.md:180` — "It reads the diff, classifies the change scope, and delegates to `backend-test-specialist` or `frontend-test-specialist` as needed." Implementation: `agents/code-reviewer.md:19` — "**Before any other step**, load and execute `skills/shared/review-router/SKILL.md`"; `:24-25` — "`BACKEND` → you proceed as `backend-reviewer`" / "`FRONTEND` → you proceed as `frontend-reviewer`".
- **Problem:** The canonical description names the wrong two agents.
- **Why it matters at HEAD:** Text and implementation are both unchanged, so the doc actively misdirects anyone tracing the review pipeline.

### Two directories named `helpers` with opposite packaging semantics; the shipped one is undocumented

- **Fingerprint:** `ref-two-helpers-dirs-naming-collision-root-stripped-vs-scripts-helpers-shipped-claude-md-file-structure-omits-scripts-helpers`
- **Evidence:** `helpers/` (root) holds 6 dev tools and is deleted at install — `scripts/lib/strip-tarball.sh:22` — `rm -rf "$extracted/helpers"   # dev-only authoring tools`. `scripts/helpers/telemetry-send.sh` ships and runs — `scripts/install.sh:760` — `_TELEMETRY_SEND="$INSTALL_DIR/scripts/helpers/telemetry-send.sh"`. `CLAUDE.md:215-216` documents neither.
- **Problem:** One name, two directories, inverted packaging outcomes, and the shipped one is absent from the canonical tree entirely.
- **Why it matters at HEAD:** The collision survived the provider port untouched.

### `CLAUDE.md` File Structure omits six real top-level entries

- **Fingerprint:** `ref-claude-md-file-structure-omits-helpers-and-privacy-and-claude-md-folder`
- **Evidence:** The ASCII tree at `CLAUDE.md:197-224` lists `agents/ skills/ commands/ templates/ docs/ scripts/` plus the root markdown files. `ls` additionally returns `helpers/`, `opencode/`, `user-data/`, `.github/`, `.claude/`, `PRIVACY.md`, and `CLAUDE-md/` — the last cross-referenced four times inside `CLAUDE.md` itself (`:230`, `:236`, `:242`, `:248`).
- **Problem:** Six top-level entries missing, including a subdirectory the same file links to four times.
- **Why it matters at HEAD:** The original three omissions persist and the provider port added three more.

---

## MEDIUM

### `CLAUDE.md` Authoring Standards still mandate `model:` and `tools:` frontmatter that no longer exists

- **Fingerprint:** `ref-haiku-residual-claude-md-note-after-executed-removal`
- **Evidence:** `CLAUDE.md:63` — "Frontmatter: `name`, `description`, `model`, `tools`"; `:64` — "Model assignment: `claude-opus-4-7` … `claude-sonnet-4-6`"; `:65` — the Haiku note; `:66` — "Tools order: `Read, Write, Edit, Glob, Grep, Bash, WebSearch, WebFetch`". Against the tree: `grep -c "^tools:" agents/` = **0**; `grep -c "^model:" agents/` = **0**. All 17 agents declare `tier:`, and `helpers/agent-lint.sh:18` enforces `REQUIRED_FIELDS=("name" "description" "tier")`.
- **Problem:** The entire Authoring Standards block for agents is stale. The two keys it mandates were removed by the multi-provider port and replaced by `tier:` + `scripts/lib/tiers.json`, which the block never mentions.
- **Why it matters at HEAD:** **This is the single most v2-specific finding in the set.** Anyone authoring a new agent by following `CLAUDE.md` would add `model:` and `tools:` keys the linter does not understand, and omit the `tier:` key CI hard-fails on.

### `templates/*-template.md` are referenced by bare relative paths that do not resolve in an installed project

- **Fingerprint:** `ref-templates-dir-shipped-but-not-symlinked-relative-path-broken-from-agent-cwd`
- **Evidence:** `CLAUDE.md:40`, `agents/setup-assistant.md:26` and `:135`, `skills/shared/project-context/SKILL.md:112` all use the bare path `templates/plan-template.md`; `skills/shared/runbook/SKILL.md:8,17,28` uses `templates/runbook-template.md`. Packaging: `scripts/install.sh:130` — `KEEP_ROOT=(agents scripts skills templates commands)` places files at `.dev-team-agents/templates/`, but the only `ln -s` calls are for `agents` (`:260`), skills (`:275`) and `commands` (`:303`). There is no `.claude/templates` symlink.
- **Problem:** Six reference sites point at a path that resolves to `<project>/templates/…`, which does not exist.
- **Why it matters at HEAD:** The fix pattern already exists in-repo — `scripts/new-adr.sh:35` resolves script-relative (`"$SCRIPT_DIR/../templates/adr-template.md"`) and is the only reference that works.
- **Merged from:** 2 v1 fingerprints (`ref-*` + `token-*`).

### `shadcn` skill `name:` does not match its directory, and no validator enforces the convention

- **Fingerprint:** `ref-skill-ui-libraries-shadcn-frontmatter-name-shadcn-ui-with-hyphen-while-directory-basename-is-shadcn-no-validator-enforces-name-equals-dir-convention`
- **Evidence:** `skills/ui-libraries/shadcn/SKILL.md:2` — `name: shadcn-ui`; directory basename is `shadcn`. A full sweep comparing `basename(dirname)` to `name:` across all 133 `SKILL.md` files returns exactly one mismatch. `helpers/agent-lint.sh:80-110` (`check_skill`) validates field presence and rejects non-canonical keys but never compares `name` to the directory; neither does `.github/scripts/ci/01-lint.sh` or `provider/_contract.py`.
- **Problem:** The only skill whose declared `name` diverges from its folder, with no gate to catch it.
- **Why it matters at HEAD:** The v2 renderer resolves opencode skills **by `name`** (`scripts/lib/tool-map.json` idiom_notes: `skill({ name: '<name>' })`) while installers symlink **by directory**. The mismatch is now load-bearing across providers.
- **Merged from:** 2 v1 fingerprints (`ref-*` + `auto-*`).

### `release-prep` skill exists twice with divergent content and opposite install fates

- **Fingerprint:** `ref-release-prep-skill-exists-twice-shared-88-lines-shipped-vs-claude-skills-181-lines-dev-divergent-content-no-sync-rule`
- **Evidence:** `wc -l` → `88 skills/shared/release-prep/SKILL.md`, `181 .claude/skills/release-prep/SKILL.md`. Both git-tracked. The 88-line copy ships via `KEEP_ROOT`; the 181-line copy is stripped by `scripts/lib/strip-tarball.sh:20`.
- **Problem:** Same skill name, two files, ~2× content difference, no sync rule.
- **Why it matters at HEAD:** Line counts unchanged from the v1 finding — nothing was reconciled.

### `CLAUDE.md` maps never mention `scripts/hooks/lib/`, the one file shared by two hooks

- **Fingerprint:** `ref-claude-md-hook-files-map-and-file-structure-omit-scripts-hooks-lib-session-summary-detect-shared-dep-of-two-hooks`
- **Evidence:** `scripts/hooks/lib/session-summary-detect.sh` is sourced by both `scripts/hooks/pre-compact.sh` and `scripts/hooks/stop/01-session-summary.sh`. `CLAUDE.md:215-216` shows only `hooks/ ← pre-tool-use.sh, stop.sh (dispatchers) + pre-tool-use/, stop/ (sub-scripts)`; the Hook Files Map names only the four entry points.
- **Problem:** The shared dependency is invisible in both canonical maps.
- **Why it matters at HEAD:** An author editing session-summary detection for one hook gets no signal that the other consumes the same code.

### `CLAUDE.md` File Structure documents 5 of 15 scripts and none of the provider machinery

- **Fingerprint:** `ref-claude-md-file-structure-scripts-enumeration-omits-check-updates-rollback-validate-commit-msg-three-shipped-runtime-scripts`
- **Evidence:** `CLAUDE.md:215` — "├── scripts/ ← install.sh, update.sh, new-adr.sh, graphify-refresh.sh, fix-symlinks.sh". `ls scripts/` returns 15 scripts plus two subdirs. Undocumented: `check-updates.sh`, `rollback.sh`, `validate-commit-msg.sh`, plus the entire port — `install-codex.sh`, `install-opencode.sh`, `install-provider.sh`, `render-provider.sh`, `migrate-to-root.sh`, `check-codex-compat.sh` — and all of `scripts/lib/`.
- **Problem:** Two thirds of the directory is undocumented.
- **Why it matters at HEAD:** `scripts/lib/tiers.json` is now the canonical model map and appears nowhere in the File Structure block.

### Stop sub-script convention table omits `02b-` and wrongly calls the `99-` tier unused

- **Fingerprint:** `ref-claude-md-356-stop-subscript-convention-omits-02b-orphan-template-scan-undocumented-prefix-in-02-tier`
- **Evidence:** `CLAUDE.md:343` — "| `02-` | Repository integrity checks | `02-orphan-skill-scan.sh` |"; `CLAUDE.md:347` — "| `99-` | Final/cleanup tasks | _(reserved, unused)_ |". Actual `ls scripts/hooks/stop/`: `01-`, `02-`, `02b-orphan-template-scan.sh`, `03-`, `04-`, `05-`, `99-graphify-refresh.sh`.
- **Problem:** Two errors in one table — a missing sub-script whose letter-suffix form is unaccounted for by the stated rule, and a tier declared unused while occupied.
- **Why it matters at HEAD:** The `99-` inaccuracy is **new** since the v1 finding — the table drifted further, not less.

### Notification rules live in three places and the `notifications.md` table has drifted

- **Fingerprint:** `ref-notification-system-content-triplicated-across-04-notifier-sh-notifier-skill-and-claude-md-notifications-md-stop-subscript-table-already-drifted-omitting-05-telemetry`
- **Evidence:** `CLAUDE-md/notifications.md:51-57` — table rows jump `04-` → `99-` with no `05-` row, while `CLAUDE.md:346` does carry `| 05- | External reporting (telemetry) |`. The 15 tips exist both as `skills/shared/notifier/SKILL.md:111-113` and as literal bash arrays at `scripts/hooks/stop/04-notifier.sh:175,193,211`.
- **Problem:** Format, types, suppression, tip index, and the prefix convention are documented in `CLAUDE-md/notifications.md`, restated in the notifier skill, and implemented in the hook — no single source.
- **Why it matters at HEAD:** Both copies of the sub-script table are now wrong in *different* ways, which is the concrete cost of the triplication.

### `templates/backlog-template.md` is the last orphan template, shadowed by a same-named skill

- **Fingerprint:** `ref-templates-backlog-template-md-orphan-confirmed-by-scanner-but-skill-shared-backlog-template-has-inline-template`
- **Evidence:** `bash helpers/orphan-template-scan.sh` → "ACTION REQUIRED — Orphan templates: · templates/backlog-template.md". Every consumer (`agents/product-analyst.md:22,96,110,124`) points at `skills/shared/backlog-template/SKILL.md`, which carries the template inline.
- **Problem:** A shipped 35-line template with zero readers, shadowed by a 237-line inline copy.
- **Why it matters at HEAD:** It is now the *only* remaining orphan — the sibling `adr-template.md` was wired up — so it is a lone, clearly-fixable outlier.

### `commands/refactor.md` asks a plain-text multiple-choice question, violating the Quiz-first Rule

- **Fingerprint:** `ref-refactor-command-missing-interaction-patterns-load-despite-yes-no-prompts`
- **Evidence:** `commands/refactor.md:26` — `> "Should I work in a new worktree or a new branch? (worktree / branch)"`. `grep -n "interaction-patterns" commands/refactor.md` → nothing; `grep -n "AskUserQuestion"` → nothing. The rule: `CLAUDE.md:94` — "Plain text prompts like `(yes / no)` or `(a / b / c)` are **not allowed**."
- **Problem:** A finite-choice prompt rendered as parenthesised text in a command that never loads the canonical interaction skill.
- **Why it matters at HEAD:** Adoption is 15/24 commands, so `refactor.md` is a live holdout in an otherwise majority-enforced rule. See also the linter gap in [02 — `agent-lint` quiz-first regex](02-fluxos-e-workflows.md).

---

## LOW-MEDIUM

### `CLAUDE.md` claims the `agent-creator` skill is "not in this repo" — it is git-tracked

- **Fingerprint:** `ref-claude-md-130-agent-creator-points-to-external-claude-skills-path-shipped-by-host-not-by-repo-no-validator-checks-the-path-exists-at-runtime-and-orphan-scan-cannot-cover-it`
- **Evidence:** `CLAUDE.md:133` — "| `agent-creator` | `.claude/skills/agent-creator/SKILL.md` (global Claude skill — **not in this repo**) |". But `git ls-files .claude` returns `.claude/skills/agent-creator/SKILL.md`.
- **Problem:** The canonical table states a factual untruth. The file is tracked but stripped at install (`scripts/lib/strip-tarball.sh:20`), so it ships to nobody — a different problem from the documented one.
- **Why it matters at HEAD:** Anyone editing the skill follows the doc to a "global" location that does not exist, while the real tracked copy drifts undelivered.

### `agent-creator` and `skill-creator` live in different trees with inverted install fates

- **Fingerprint:** `ref-agent-creator-location`
- **Evidence:** `skills/skill-creator/SKILL.md` is a first-class skill domain shipping via `KEEP_ROOT`. `.claude/skills/agent-creator/SKILL.md` sits under the dotdir and is deleted at install. Both are registered side by side at `CLAUDE.md:132-133`.
- **Problem:** Two sibling authoring skills in one table, two trees, opposite packaging outcomes.
- **Why it matters at HEAD:** The provider port did not normalize them; only one is reachable through any provider install.

### The TODO/FIXME reviewer bullet is triplicated and has already forked into two variants

- **Fingerprint:** `ref-three-reviewers-todo-fixme-issue-tracker-tickets-bullet-duplicated-verbatim-no-shared-source-distinct-from-reviewer-base-and-reviewer-mindset-already-extracted`
- **Evidence:** `agents/code-reviewer.md:127` — "TODO/FIXME comments (should be issue tracker tickets)"; `agents/backend-reviewer.md:136` and `agents/frontend-reviewer.md:125` — "TODO/FIXME that should be issue tracker tickets".
- **Problem:** One review rule inline in three agents with no shared source; the wording has already diverged.
- **Why it matters at HEAD:** The extraction pattern reached `reviewer-base` and `reviewer-mindset` but left this bullet behind.

### Two malformed git tags violate the documented `vX.Y.Z` convention

- **Fingerprint:** `ref-two-malformed-git-tags-v-1-1-0-and-v-1-3-13-violate-vx-y-z-convention-in-versioning-md-break-version-sort-and-gap-clean-sequence`
- **Evidence:** `git ls-remote --tags origin` returns `refs/tags/v.1.1.0` and `refs/tags/v.1.3.13` (dot after `v`) alongside well-formed `v1.0.0 … v1.11.0`. `CLAUDE-md/versioning.md:3` prescribes `v1.0.0`, `v1.1.0`, `v2.0.0`. `v1.3.12` and `v1.3.14` exist; `v1.3.13` is absent from the clean sequence.
- **Problem:** Two published tags in a format the repo's own versioning doc forbids; no check validates tag names.
- **Why it matters at HEAD:** `sort -V` and version-pin logic in the update path see a broken sequence with a visible gap.

### `CLAUDE.md` File Structure lists 8 of 11 skill domains

- **Fingerprint:** `ref-claude-md-file-structure-skills-subtree-omits-database-mobile-skill-creator-three-of-eleven-domains`
- **Evidence:** `CLAUDE.md:200-208` lists `shared/ architecture/ testing/ security/ design/ devops/ integrations/ ui-libraries/`. `ls skills/` returns those plus `database/`, `mobile/`, `skill-creator/`.
- **Problem:** Three domains — each with a dedicated agent or a registered user-invocable skill — are absent.
- **Why it matters at HEAD:** Unchanged from the v1 count (8 documented vs 11 real).

### The Hook Files Map documents four dispatchers and none of the `pre-tool-use/` sub-scripts

- **Fingerprint:** `ref-claude-md-hook-files-map-omits-pre-tool-use-02-telemetry-and-stop-05-telemetry-sub-scripts`
- **Evidence:** The map has exactly four rows, with `PreToolUse` described only as "Update checks, context cache". `ls scripts/hooks/pre-tool-use/` returns `01-check-updates.sh`, `02-graphify-hint.sh`, `02-telemetry.sh` — none documented, and there is no PreToolUse counterpart to the Stop sub-script convention.
- **Problem:** Asymmetric treatment; `02-telemetry.sh`, a network-sending script, is entirely undocumented.
- **Why it matters at HEAD:** Two files now share the `02-` prefix with no convention governing them. See [02 — PreToolUse ordering collision](02-fluxos-e-workflows.md).

### The package-exclusions table has fallen behind `strip-tarball.sh` again — `opencode/` is undocumented

- **Fingerprint:** `docs-sync-claude-md-package-exclusions`
- **Evidence:** `scripts/lib/strip-tarball.sh:23` — `rm -rf "$extracted/opencode"`. The 13-row table at `CLAUDE-md/user-data.md:29` onward does not mention `opencode/`.
- **Problem:** `strip-tarball.sh:2` bills itself as "Single source of truth for the slim tarball strip rules" while the canonical doc lists 13 of its 14 removals.
- **Why it matters at HEAD:** The four items originally flagged were fixed and the table promptly drifted again one release later — the same pattern, not a new one.

---

## Cross-references

Findings whose primary axis is elsewhere but that are reference/consistency defects in nature:

| Finding | Filed under |
|---|---|
| `helpers/archive-index.sh` invoked by nothing | [02 — Flows](02-fluxos-e-workflows.md) |
| Telemetry defaults ON in non-interactive installs | [02 — Flows](02-fluxos-e-workflows.md) |
| `orphan-skill-scan` cannot distinguish a load from a mention | [02 — Flows](02-fluxos-e-workflows.md) |
| `orphan-template-scan` CONSUMERS list omits `helpers/` and `CLAUDE.md` | [02 — Flows](02-fluxos-e-workflows.md) |
| `size-limits.sh` has no cap for `commands/` | [02 — Flows](02-fluxos-e-workflows.md) |
| `comments-policy` directive duplicated verbatim in 8 agents | [04 — Token Economy](04-economia-tokens.md) |
