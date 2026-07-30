# Flows, Automation and Governance — v2 Carry-Over

**Axis:** `flow-*` + `auto-*` + `gov-*` · **Verified against:** `HEAD` = `7f85ed7`

This axis had the highest v1 mortality: the `workflows/` directory and the `skills/shared/workflow-detection/` skill were deleted wholesale by the provider port, killing 26 findings outright. Everything below was checked for migration into `commands/<scope>.md` before being kept.

---

## HIGH

### The 200-line agent cap is warn-only in CI, has no Stop-hook equivalent, and 11 of 17 agents violate it

- **Fingerprint:** `flow-size-limits-sh-ci-only-warn-only-not-in-stop-dispatcher-asymmetric-with-agent-lint-200-cap-never-blocking`
- **Evidence:** `.github/scripts/ci/01-lint.sh:19` — `bash helpers/size-limits.sh --warn-only`. No `scripts/hooks/stop/*size*` sub-script exists. Live run at HEAD:

  | Agent | Lines | Over cap |
  |---|---|---|
  | `software-architect` | 372 | +86% |
  | `frontend-test-specialist` | 266 | +33% |
  | `backend-developer` | 265 | +33% |
  | `setup-assistant` | 244 | +22% |
  | `devops-specialist` | 243 | +22% |
  | `security-specialist` | 240 | +20% |
  | `frontend-developer` | 236 | +18% |
  | `code-reviewer` | 233 | +17% |
  | `qa-specialist` | 227 | +14% |
  | `backend-reviewer` | 209 | +5% |
  | `mobile-developer` | 203 | +2% |

- **Problem:** `agent-lint` is both blocking in CI **and** wired into the Stop dispatcher (`03-agent-lint.sh`); `size-limits` is neither. The `CLAUDE.md` "Max ~200 lines per agent" rule has no enforcement path at all.
- **Why it matters at HEAD:** Violations grew from **9/17 to 11/17** while the finding sat open, and `software-architect` — the new worst offender at 372 lines — is not covered by any individual v1 finding.
- **Merged from:** 4 v1 fingerprints (the enforcement gap plus three per-agent size findings).

### Telemetry defaults to enabled on the primary documented install path

- **Fingerprint:** `ref-telemetry-honors-pref-but-pref-defaults-true-on-fresh-install-without-prompt-on-non-interactive-curl-bash`
- **Evidence:** `scripts/install.sh:654` — `TELEMETRY_VALUE="true"`; `:658` — `if [ "$IS_FIRST_INSTALL" = true ] && [ -t 0 ]; then` gates the whole consent block including the prompt at `:673` (`Enable anonymous telemetry? [Y/n]`). Under `curl … | bash`, stdin is a pipe, `[ -t 0 ]` is false, the block is skipped, and the value stays `"true"`.
- **Problem:** The consent prompt never fires on the documented install path, and the pre-set default is on. Reading from `</dev/tty` at `:675` does not help — the `[ -t 0 ]` guard runs first.
- **Why it matters at HEAD:** Byte-identical logic to when first flagged, and `README.md:302` still advertises the feature as opt-out consent.

### `helpers/archive-index.sh` is written, committed, and invoked by nothing

- **Fingerprint:** `flow-helpers-archive-index-sh-orphan-of-hook-eight-days-after-flagged-rotation-90-day-promise-in-index-md-line-19-20-has-no-trigger-cron-ci-stop-hook-or-update-sh`
- **Evidence:** A repo-wide grep for `archive-index` outside `docs/reports/` returns only the script's own header lines. No Stop or PreToolUse sub-script, no CI job, no call in `install.sh` / `update.sh`. No `_index-archive-*.md` has ever been produced.
- **Problem:** A 90-day archival policy implemented and wired to nothing.
- **Why it matters at HEAD:** `docs/reports/_index.md` reached **850 lines** carrying fingerprints back to 2026-05-06 — well past the threshold the script exists to enforce. **This report's rewrite of `_index.md` resets the substrate but does not fix the missing trigger.**
- **Merged from:** 3 v1 fingerprints (`flow-*`, `ref-*`, `token-*`).

---

## MEDIUM-HIGH

### `update.sh` downloads and executes the installer with no integrity verification

- **Fingerprint:** `auto-update-no-integrity-check`
- **Evidence:** `scripts/update.sh:67-68` — `HTTP_DL "$TMP_INSTALLER" "$INSTALL_URL"` followed immediately by `bash "$TMP_INSTALLER" "$VERSION_ARG"`. No `sha256`, `shasum`, `gpg`, or checksum reference anywhere in the file.
- **Problem:** A raw `raw.githubusercontent.com` fetch piped straight into `bash`, with no digest pin; the fetched script then unpacks a tarball over the user's project.
- **Why it matters at HEAD:** `/devteam:update` invokes this path, so it is the routine user-facing upgrade mechanism.

### The PostHog key carries self-contradicting comments and an unresolved pre-release TODO

- **Fingerprint:** `gov-telemetry-send-sh-posthog-key-comments-self-contradict-intentionally-public-vs-replace-before-release-todo-on-default-on-path`
- **Evidence:** `scripts/helpers/telemetry-send.sh:23-25` — "# The capture API key is intentionally public (client-side key, not secret)." immediately followed by "# Replace POSTHOG_API_KEY with the real project key before release.", then the hardcoded `POSTHOG_API_KEY="${DEVTEAM_POSTHOG_KEY:-phc_…}"`.
- **Problem:** The two comments cannot both be true — either the committed key is production (and the TODO is stale and misleading) or it is a placeholder shipping in released installs. The reader cannot tell which.
- **Why it matters at HEAD:** The helper is invoked unconditionally from `install.sh`, `update.sh`, and both telemetry hooks on a default-on path. It is the only pre-release runtime TODO left in the repo.

---

## MEDIUM

### `install.sh` deletes the install directory before the `mv`, with no rollback

- **Fingerprint:** `auto-install-no-rollback-on-second-mv-failure`
- **Evidence:** `scripts/install.sh:160-166` — `rm -rf "$INSTALL_DIR"` / `mv "$EXTRACTED_ROOT" "$INSTALL_DIR"` … `rm -rf "$USER_DATA_DIR"` / `mv "$USER_DATA_BACKUP/user-data" "$USER_DATA_DIR"`. `set -euo pipefail` is at `:21` and the file registers **no** `trap`.
- **Problem:** Each destructive `rm -rf` precedes its `mv` with nothing to restore from. If the first `mv` fails (cross-device, permissions, ENOSPC) the existing install is already gone; if the second fails, `user-data/` is recoverable only from an unadvertised `mktemp -d`.
- **Why it matters at HEAD:** This is the update path for every existing install, and `user-data/` holds `preferences.json` and `session-summary.md`.

### CI lint expresses three different enforcement levels in seven lines, with no stated policy — and the tolerant tier has live findings

- **Fingerprint:** `flow-ci-orphan-skill-scan-step-continue-on-error-true-never-blocks-two-duplicate-loads-standing-unaddressed-for-days` (merged with `flow-ci-fingerprint-check-strict-while-orphan-scan-tolerant-asymmetric-gates`)
- **Evidence:** `.github/scripts/ci/01-lint.sh:13` — `bash helpers/orphan-skill-scan.sh || true` (never blocks); `:16` — `bash helpers/check-fingerprint-uniqueness.sh` (bare, blocking under `set -euo pipefail`); `:19` — `bash helpers/size-limits.sh --warn-only` (third tier). Running the orphan scan now yields **1 ACTION REQUIRED** (`skills/shared/migration-v1-to-v2/SKILL.md` has no agent reference) and **2 ACTION SUGGESTED** duplicate loads in `agents/software-architect.md`.
- **Problem:** Three structurally similar hygiene checks, three opposite blocking semantics, no policy in the script or in `CLAUDE.md` explaining which is which — and the non-blocking tier is sitting on real unaddressed findings.
- **Why it matters at HEAD:** Confirmed with live output, not inference. The v2 skill `migration-v1-to-v2` is itself the orphan.
- **Merged from:** 2 v1 fingerprints.

### Stop never cleans up zombie session state

- **Fingerprint:** `flow-stop-no-zombie-state-cleanup-discovery-lock-and-worktree-session-persist-across-sessions`
- **Evidence:** No Stop sub-script touches `.worktree-session` or `.discovery-lock`; `scripts/hooks/session-start.sh:1-174` does not clear them either. `.dev-team-agents/.worktree-session` appears in `scripts/install.sh:575` only as a `.gitignore` entry.
- **Problem:** `.discovery-lock` at least has a documented 30-minute staleness escape hatch; `.worktree-session` has **no** TTL and no cleanup at all.
- **Why it matters at HEAD:** Every coding agent's worktree cascade reads `.worktree-session` first and "follows the stored decision silently" per `CLAUDE.md`, so a stale file from a merged branch silently steers the next unrelated session.

### The Stop dispatcher auto-executes any `.sh` dropped into `stop/`

- **Fingerprint:** `flow-stop-dispatcher-globs-all-sh-no-allowlist-or-per-subscript-toggle-any-dropped-file-auto-executes`
- **Evidence:** `scripts/hooks/stop.sh:37` — `for script in "$HOOKS_DIR"/*.sh; do`. Same pattern at `scripts/hooks/pre-tool-use.sh:16`.
- **Problem:** No allowlist, no per-sub-script toggle. A draft, a renamed `.bak`, or a half-finished script executes on every Stop, and a non-zero exit propagates to the user.
- **Why it matters at HEAD:** The surface grew from 5 to 7 Stop sub-scripts.

### PreToolUse sub-script ordering is undocumented and already collides

- **Fingerprint:** `flow-pre-tool-use-dispatcher-no-mention-of-sub-script-order-convention-asymmetric-with-stop-dispatcher`
- **Evidence:** `CLAUDE.md` has a "Stop Hook Sub-script Convention" table with reserved prefixes `01-`…`99-` and nothing for PreToolUse. On disk: `scripts/hooks/pre-tool-use/02-graphify-hint.sh` **and** `02-telemetry.sh` share the `02-` prefix.
- **Problem:** The predicted drift already happened — a numeric-prefix collision resolved only by alphabetical tiebreak, with no documented tier meaning.
- **Why it matters at HEAD:** `pre-tool-use.sh:16` depends on glob order, so a rename silently reorders execution.

### PreToolUse telemetry forks `python3` twice on every tool call before its own filter

- **Fingerprint:** `flow-telemetry-pre-tool-use-02-runs-on-every-tool-call-without-batching-or-deduplication-burns-200ms-per-burst-session`
- **Evidence:** `scripts/hooks/pre-tool-use/02-telemetry.sh:20-23` (`_telemetry_enabled` → `python3 -c …`) then `:41-43` (`TOOL_NAME=$(python3 -c …)`) — both unconditional, both **before** the `case "$TOOL_NAME"` filter at `:47`.
- **Problem:** Only `Task` and `Bash` produce an event, but every Read, Grep, Glob and Edit pays two interpreter startups first. The queue batches the network send, not the per-call work.
- **Why it matters at HEAD:** A burst command issuing ~40 tool calls pays ~80 python startups for at most a handful of events.

### `01-check-updates.sh` forks `python3` before its own TTL early-return

- **Fingerprint:** `token-pre-tool-use-01-check-updates-forks-python3-to-read-interval-before-ttl-early-exit-on-every-tool-call-burst-overhead`
- **Evidence:** `scripts/hooks/pre-tool-use/01-check-updates.sh:15-19` reads `UPDATE_INTERVAL_HOURS` via `python3 -c` unconditionally; the TTL early-exit is only reached at `:28-35`.
- **Problem:** The 24-hour cache short-circuits the network call but cannot prevent the fork, because the interval is read in order to *compute* the cache window.
- **Why it matters at HEAD:** Reading the timestamp file first and consulting prefs only on a cache miss would make the common path pure bash. This is the hook that runs most often.
- **Merged from:** 2 v1 fingerprints (`token-*` + `flow-*`).

### `02b-orphan-template-scan.sh` is the only Stop sub-script with no change gate

- **Fingerprint:** `flow-02b-orphan-template-scan-lacks-devteam-no-changes-fast-path-and-git-scoped-gate-runs-full-scan-every-stop`
- **Evidence:** `scripts/hooks/stop/02b-orphan-template-scan.sh:1-10` has no `DEVTEAM_NO_CHANGES` check and no `git status` gate. Contrast `02-orphan-skill-scan.sh:4` — `[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0`. The helper it calls issues 4 templates × 4 recursive greps = 16 tree walks per Stop.
- **Problem:** A full recursive scan across `agents skills commands scripts` on every Stop, including purely conversational sessions.
- **Why it matters at HEAD:** The dispatcher computes the fast-path flag one line away; `02b` just does not read it. The asymmetry is fresh — the gate was added to one script and not its sibling.
- **Merged from:** 2 v1 fingerprints.

### `orphan-template-scan.sh` proves a name is mentioned, not that the path resolves

- **Fingerprint:** `flow-orphan-template-scan-runs-in-stop-but-only-checks-references-not-resolvability-masks-templates-broken-by-relative-path`
- **Evidence:** `helpers/orphan-template-scan.sh:20` — `if grep -rl "$template_name" "$dir/"` (basename match only). Consumers use bare relative paths that do not resolve in an installed project (see [01 — templates unreachable](01-referencias-e-consistencia.md)).
- **Problem:** The scan reports `plan-template.md` and `runbook-template.md` as referenced and therefore healthy, while the paths those references use are unreachable.
- **Why it matters at HEAD:** A scan that reports green on unreachable templates is worse than no scan.

### `orphan-skill-scan.sh` still cannot distinguish a load directive from a narrative mention

- **Fingerprint:** `ref-orphan-skill-scan-reports-design-system-audit-duplicate-load-in-ui-ux-designer-introduced-in-uknown-commit`
- **Evidence:** The scan now reports "`agents/software-architect.md` loads `skills/shared/model-identity/SKILL.md` more than once". The two hits are `:11` (a genuine load) and `:143` (prose about subagents: "The subagent will auto-announce its model via the model-identity skill"). Detection is a bare path regex at `helpers/orphan-skill-scan.sh:61` / `:132`.
- **Problem:** Any mention of a skill path counts as a load, so narrative references produce false duplicate-load reports.
- **Why it matters at HEAD:** The scan runs in CI and as a Stop hook, emitting a standing ACTION SUGGESTED item that cannot be resolved without deleting correct prose. The specific file cited in v1 (`ui-ux-designer.md`) is clean now; the defect class simply moved.

### Fingerprint uniqueness is scoped to a single file, blind to the rotation it is meant to survive

- **Fingerprint:** `flow-check-fingerprint-uniqueness-scans-only-index-md-blind-to-documented-archive-rotation-cross-file-dupes-undetected`
- **Evidence:** `helpers/check-fingerprint-uniqueness.sh:6` — `INDEX_FILE="docs/reports/_index.md"`.
- **Problem:** Dedup happens only inside `_index.md`. Once `archive-index.sh` moves slugs into `_index-archive-*.md`, an archived slug could be re-registered undetected.
- **Why it matters at HEAD:** This is a *blocking* CI gate whose guarantee silently degrades from global to per-file the moment rotation happens.

### The README-sync gate compares heading counts and line totals, never section bodies

- **Fingerprint:** `flow-readme-sync-ci-gate-checks-only-section-count-and-50pct-line-threshold-not-body-content-passes-while-section-bodies-diverge`
- **Evidence:** `.github/scripts/ci/02-readme-sync.sh:13-28` — `grep -c "^## "` equality plus `THRESHOLD=$(( EN_LINES / 2 + 1 ))`.
- **Problem:** An EN section can be fully rewritten while the pt-BR one stays stale and the gate still passes.
- **Why it matters at HEAD:** It produces false confidence in a rule `CLAUDE.md` declares mandatory per-commit — and it is the exact mechanism that let the wrong Model column pass green in both languages.

### `agent-lint.sh` enforces only half the Quiz-first Rule

- **Fingerprint:** `auto-agent-lint-quiz-first-regex-only-matches-yes-no-variants-misses-a-b-c-multiple-choice-plain-text-prompts-forbidden-by-same-rule`
- **Evidence:** `helpers/agent-lint.sh:68` — `grep -qE "\([yY]es[/ ][nN]o\)|\(y[/]n\)|\(yes\|no\)|\( yes / no \)"` — every alternative is a yes/no variant. The error text at `:72` names only that case.
- **Problem:** The rule forbids plain-text prompts for *any* finite answer set; a hand-written `(a / b / c)` prompt passes lint clean — which is exactly what `commands/refactor.md:26` does.
- **Why it matters at HEAD:** The check runs on every CI build, so it reads as full enforcement while covering half the rule.

### `.github/CODEOWNERS` leaves half the skill domains unowned and still names a deleted directory

- **Fingerprint:** `gov-codeowners-coverage-gaps-helpers-readme-pair-canonical-docs-and-skill-domains-unowned-asymmetric`
- **Evidence:** Entries exist for `skills/architecture/`, `security/`, `devops/`, `database/`, `testing/` — but not `skills/integrations/`, `ui-libraries/`, `mobile/`, `design/`, `skill-creator/`. Also no entry for `helpers/`, `README.md`, `README.pt-BR.md`, `docs/agents.md`, `docs/installation.md`, or `.github/scripts/ci/`. And `.github/CODEOWNERS:9` — `workflows/  @Dev-Toolbelt/maintainers` — points at a directory the port removed.
- **Problem:** Ownership is asymmetric across sibling domains; the telemetry code in `helpers/` and the two sync-governed READMEs can be changed with no required reviewer.
- **Why it matters at HEAD:** The port *added* `skills/mobile/` and `.github/scripts/ci/` (both unowned) while removing `workflows/`, so the gap widened and one rule became dead weight.

---

## LOW-MEDIUM

### Stop sub-scripts `02` and `03` recompute git state the dispatcher already holds

- **Fingerprint:** `flow-stop-dispatcher-computes-no-changes-once-but-02-and-03-each-recompute-identical-git-status-and-git-log-no-shared-touched-set`
- **Evidence:** `scripts/hooks/stop/02-orphan-skill-scan.sh:6-7` and `03-agent-lint.sh:6-7` are byte-identical. `scripts/hooks/stop.sh:32` exports only the boolean `DEVTEAM_NO_CHANGES`.
- **Problem:** Four redundant git forks per Stop when anything changed; the dispatcher could export the touched-path set once.

### `05-telemetry.sh` ignores the dispatcher's no-changes fast path

- **Fingerprint:** `flow-telemetry-stop-05-runs-after-04-notifier-but-no-fast-path-skip-when-DEVTEAM_NO_CHANGES-is-1`
- **Evidence:** `scripts/hooks/stop/05-telemetry.sh:1-45` contains no `DEVTEAM_NO_CHANGES` reference. Contrast `04-notifier.sh:88`, which has the guard.
- **Problem:** A `session_end` event plus a flush attempt is queued for every purely conversational Stop.
- **Why it matters at HEAD:** The fix landed in `04-notifier.sh` and was never propagated one file over.

### Fingerprint uniqueness is only checked after push

- **Fingerprint:** `flow-no-stop-hook-runs-check-fingerprint-uniqueness-after-_index-edit-only-on-CI-after-push-feedback-too-late`
- **Evidence:** `helpers/check-fingerprint-uniqueness.sh` is invoked exactly once, at `.github/scripts/ci/01-lint.sh:16`. No Stop sub-script runs it.
- **Problem:** A duplicate slug surfaces only after commit + push + CI, whereas `agent-lint` and `orphan-skill-scan` both give same-session feedback.
- **Why it matters at HEAD:** It is a blocking gate, so late feedback means a red build rather than a warning.

### The README-sync gate hardcodes three doc pairs with no glob discovery

- **Fingerprint:** `flow-readme-sync-ci-hardcodes-three-doc-pairs-no-glob-discovery-any-new-pt-br-translation-pair-silently-unchecked`
- **Evidence:** `.github/scripts/ci/02-readme-sync.sh:35-37` — three literal `check_pair` calls.
- **Problem:** `find . -name '*.pt-BR.md'` currently returns exactly those three, so nothing escapes today — but a fourth translation would be silently unchecked.

### CI fires on both push and pull_request for all branches with no concurrency guard

- **Fingerprint:** `flow-ci-triggers-both-push-and-pull-request-on-all-branches-duplicate-runs-no-concurrency-cancel-in-progress-guard`
- **Evidence:** `.github/workflows/ci.yml:3-7` — `on: push: branches: ["**"] / pull_request: branches: ["**"]`; no `concurrency:` block.
- **Problem:** Every push to a branch with an open PR runs the full matrix twice; superseded runs are never cancelled.
- **Why it matters at HEAD:** Worse than when filed — the workflow grew from 1 job to 3 including a 3-way provider matrix, so each duplicate now costs 5 runners instead of 1.

### `install.sh` chmod enumeration omits three shipped subtrees

- **Fingerprint:** `flow-install-sh-chmod-enumeration-omits-scripts-hooks-lib-subdir-manual-per-subdir-list-drifts-on-new-hook-subtree`
- **Evidence:** `scripts/install.sh:616-619` enumerates `scripts/*.sh`, `scripts/hooks/*.sh`, `pre-tool-use/*.sh`, `stop/*.sh` — and now misses `scripts/hooks/lib/`, `scripts/helpers/`, and `scripts/lib/`.
- **Problem:** A manual list that has drifted further since being flagged.
- **Why it matters at HEAD:** A recursive `find … -exec chmod +x` would close the class permanently.

### `size-limits.sh` enforces no cap on `commands/`, which now exceeds the agent limit

- **Fingerprint:** `ref-size-limits-sh-no-line-cap-for-commands-and-workflows-refactor-md-278-lines-largest-immutable-content-file-unguarded`
- **Evidence:** `helpers/size-limits.sh:27-31` defines only `AGENTS_DIR` / `SKILLS_DIR` with caps 200 / 500, plus a `CLAUDE.md` check. `commands/` is never read. Current largest: `commands/learn.md` = 229, `audit.md` = 192, `commit.md` = 177.
- **Problem:** The v1 example (`workflows/refactor.md`) is gone with the directory, but `commands/learn.md` now exceeds the 200-line agent limit with no gate.
- **Why it matters at HEAD:** `commands/` is installed verbatim into user projects and is the only shipped content category with no size discipline.

### `orphan-template-scan.sh` consumer list omits `helpers/`, `CLAUDE.md`, and `CLAUDE-md/`

- **Fingerprint:** `ref-orphan-template-scan-consumers-list-omits-helpers-dir-and-claude-md-false-orphan-risk-asymmetric-with-helpers-refactor`
- **Evidence:** `helpers/orphan-template-scan.sh:11` — `CONSUMERS="agents skills commands scripts"`. `CLAUDE.md:40` references `templates/plan-template.md` and is not scanned.
- **Problem:** A template referenced only from `CLAUDE.md`, `CLAUDE-md/`, or a helper would be reported as an orphan.
- **Why it matters at HEAD:** Latent — every current template happens to have a consumer inside the scanned set. The obsolete `workflows` entry was correctly removed; the omissions were not added.

### `scripts/new-adr.sh` injects an unescaped free-form title into a `sed` replacement

- **Fingerprint:** `auto-new-adr-sh-sed-title-substitution-breaks-on-pipe-ampersand-backslash-in-free-form-adr-title-no-escaping`
- **Evidence:** `scripts/new-adr.sh:44` — `-e "s|\[Title\]|$TITLE|g"`, with `$TITLE` coming straight from `TITLE="${1:-}"` at `:6` with no escaping.
- **Problem:** `|` is the delimiter, so a pipe in the title truncates or errors; `&` expands to the whole match and `\` starts an escape.
- **Why it matters at HEAD:** `CLAUDE.md` classifies the ADR title as "strict free-form input" and `/devteam:adr` passes user text directly into this script.

### `install.sh` discards curl/wget stderr on every download

- **Fingerprint:** `auto-installer-error-output`
- **Evidence:** `scripts/install.sh:101` — `if ! HTTP_GET_FILE "$TARBALL_URL" "$TMP_TAR" 2>/dev/null; then`; same at `:66` and `:73`.
- **Problem:** The real failure reason (TLS error, 404 on a bad version tag, proxy rejection, rate limit) is discarded; the user sees only the generic message at `:104`.
- **Why it matters at HEAD:** This is the sole install/update entry point, so every install failure is undiagnosable from the output.

### `commands/commit.md` skips message validation silently when the script is absent

- **Fingerprint:** `flow-cli-commit-validate-msg-script-skipped-silently-when-missing-no-instructive-error`
- **Evidence:** `commands/commit.md:129-131` — `if [ -f ".dev-team-agents/scripts/validate-commit-msg.sh" ]; then … fi` — no `else`, no warning, while `:134` still tells the user validation happened.
- **Problem:** On a slim install, a partial update, or a non-Claude provider tree, validation is skipped with zero output.

### Multi-agent flows close without a session-summary handoff

- **Fingerprint:** `flow-session-summary-closure-step-present-in-eight-of-ten-workflows-but-absent-from-fullstack-and-refactor-highest-fanout`
- **Evidence:** `commands/refactor.md:125-140` ends at "technical-writer … draft the PR body"; `commands/fullstack.md` ends at the findings-resolution block. `grep -ln "session-summary" commands/*.md` matches only `commands/learn.md`.
- **Problem:** The two highest fan-out commands finish without instructing any agent to write the session-summary entry; the only enforcement is the reactive Stop-hook warning.
- **Why it matters at HEAD:** Context loss is most expensive precisely in the flows that spawn the most agents. **Migrated:** `workflows/{fullstack,refactor}.md` → `commands/{fullstack,refactor}.md`.

### Implementation commands end without a commit or PR handoff

- **Fingerprint:** `flow-workflows-no-commit-or-pr-step`
- **Evidence:** `commands/backend.md:73` is the last instruction before the PLAN GATE boilerplate; same shape in `frontend.md`, `fullstack.md`, `mobile.md`, `design.md`. Contrast `commands/architect.md:48` and `commands/refactor.md:140`, which do define a terminus.
- **Problem:** Five of six implementation commands leave the working tree dirty with no pointer to `/devteam:commit` or `/devteam:pr`.
- **Why it matters at HEAD:** Two commands in the same family do define closure, so this is an inconsistency **inside the current command set**, not a legacy gap. **Migrated:** `workflows/*.md` → `commands/*.md`.

### `templates/plan-template.md` and `plan-mode/SKILL.md` carry two divergent copies of the plan format

- **Fingerprint:** `gov-plan-template-vs-skill-duplication`
- **Evidence:** `templates/plan-template.md:19-26` renders the steps table as markdown; `skills/shared/plan-mode/SKILL.md:65-75` renders the same table with box-drawing characters. Both independently restate the Par.-column semantics and the approval closer. The skill never references the template.
- **Problem:** Two full, non-identical definitions of the same canonical artifact.
- **Why it matters at HEAD:** `CLAUDE.md` points at the template while agents load the skill, so the two audiences receive different formats. Contrast `skills/shared/runbook/SKILL.md:28`, which correctly delegates.
- **Note:** This absorbs the broader `gov-templates-physical-vs-inline` finding — plan-mode is the only remaining instance.

---

## LOW

### `01-check-updates.sh` is a 209-line monolith

- **Fingerprint:** `flow-pre-tool-use-01-check-updates-195-lines-3rd-largest-script-no-fragmentation`
- **Evidence:** 209 lines (was 195). Responsibilities in one file: preference read, TTL cache, HTTP tool detection, ETag-cached release fetch, version compare, auto-update trigger.
- **Why it matters at HEAD:** It grew 14 lines since being flagged and is the hook that runs most often.

### `session-start.sh` is monolithic and has grown 47%

- **Fingerprint:** `flow-session-start-118-lines-monolithic-no-modular-pattern-asymmetric-with-stop-dispatcher`
- **Evidence:** 174 lines (was 118), covering seven distinct concerns with no sub-script directory, unlike `stop.sh` / `pre-tool-use.sh`.
- **Why it matters at HEAD:** It is registered as a hook where a syntax error breaks session startup.

### `orphan-template-scan.sh` reports orphans without suggesting a consumer

- **Fingerprint:** `flow-orphan-template-scan-no-mapping-of-suggested-consumer-vs-orphan-skill-scan`
- **Evidence:** `helpers/orphan-template-scan.sh:29` — `echo "  · $template_file"` and nothing more. The sibling scan prints a suggested consumer and a remediation hint.
- **Why it matters at HEAD:** There is a live orphan (`backlog-template.md`) the scan cannot tell anyone how to fix.

### `commands/commit.md` duplicates the layered-commit table it already loads via a skill

- **Fingerprint:** `flow-commit-command-160-lines-pre-commit-gates-extractable-skill`
- **Evidence:** `commands/commit.md:54-64` is byte-for-byte the `| Order | Layer | Examples |` table from `skills/shared/conventional-commits/SKILL.md:62-66` — and `commit.md:1` already loads that skill.
- **Problem:** A change to layer ordering must be made in two files or they silently diverge. (The "largest command" half of the v1 claim is now false — `learn.md` is 229 lines.)

### The installer never registers a `commit-msg` hook or Husky/Lefthook entry

- **Fingerprint:** `flow-conventional-commits-validate-script-no-husky-or-commit-msg-hook-registration`
- **Evidence:** `grep -n "commit-msg\|husky\|lefthook" scripts/install.sh` → no matches. `scripts/validate-commit-msg.sh` ships but its only caller is `commands/commit.md:129-131`.
- **Problem:** A plain `git commit` bypasses validation entirely.

### Three Claude Code hook events remain unregistered

- **Fingerprint:** `flow-hook-events-only-pretooluse-and-stop`
- **Evidence:** `scripts/install.sh:472-475` registers exactly four — `PreToolUse`, `Stop`, `SessionStart`, `PreCompact`. `UserPromptSubmit`, `SubagentStop`, and `Notification` appear nowhere.
- **Why it matters at HEAD:** Reduced, not resolved (2 → 4 registered). `SubagentStop` is the natural place to enforce the per-agent session-summary append that `CLAUDE.md` mandates for multi-agent sessions.

### The repo installs four hook events into user projects but dogfoods only one

- **Fingerprint:** `gov-installer-rigor-asymmetry`
- **Evidence:** `scripts/install.sh:472-475` registers all four; the repo's own `.claude/settings.json` declares only a `Stop` entry.
- **Why it matters at HEAD:** Partially improved — the Stop dispatcher is now dogfooded — but 3 of 4 dispatchers still have no self-hosted feedback loop.

### There is still no `/devteam:setup` command

- **Fingerprint:** `flow-setup-slash-command`
- **Evidence:** `commands/setup.md` does not exist; none of the 24 commands invokes `setup-assistant`. `CLAUDE.md`'s Setup Trigger relies purely on natural-language intent matching.
- **Why it matters at HEAD:** `commands/health-check.md` was added in the meantime, proving the slot exists — setup was simply not given one.

### `/devteam:health-check` is absent from every canonical list

- **Fingerprint:** `flow-commit-md-and-update-md-are-only-2-commands-without-current-context-load-but-both-touch-git-state`
- **Evidence:** `CLAUDE.md:176` lists exactly four `current-context` exceptions — `commit`, `update`, `symlinks`, `learn`. Commands actually lacking the load: `commit.md`, `health-check.md`, `learn.md`, `update.md`. `health-check` is also missing from the canonical command table in `CLAUDE.md` and from both READMEs.
- **Problem:** The "by design" claim in `CLAUDE.md` is unverifiable for one command.
- **Why it matters at HEAD:** Independently surfaced by two triage slices. The exception list is the only record of why these commands are branch-unaware.

### No check for skill `name` collisions across categories

- **Fingerprint:** `auto-no-skill-name-uniqueness-check`
- **Evidence:** Uniqueness checks cover only report slugs (`helpers/check-fingerprint-uniqueness.sh`) and tool-map slugs (`provider/_contract.py:290`). `agent-lint.sh`'s `check_skill` has no cross-file state. Currently latent: 133 skills, zero duplicate `name:` values.
- **Why it matters at HEAD:** Skills are referenced by bare backtick name and `helpers/orphan-skill-scan.sh:111` resolves them by name regex, so a collision would make both references ambiguous.

---

## Cross-references

| Finding | Filed under |
|---|---|
| `shadcn` skill `name` ≠ directory, no validator | [01 — References](01-referencias-e-consistencia.md) |
| `commands/refactor.md` plain-text prompt | [01 — References](01-referencias-e-consistencia.md) |
| PreToolUse sub-scripts undocumented in the Hook Files Map | [01 — References](01-referencias-e-consistencia.md) |
| `04-notifier.sh` inlines 45 tip strings | [04 — Token Economy](04-economia-tokens.md) |
| `_telemetry_enabled()` defined three times | [04 — Token Economy](04-economia-tokens.md) |
| `install.sh` at 803 lines with 3 functions | [04 — Token Economy](04-economia-tokens.md) |
