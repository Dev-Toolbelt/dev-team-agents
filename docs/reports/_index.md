# Suggestion Index — Fingerprint Bank

This file is the **bank of audit fingerprints** for `dev-team-agents`. It guarantees that each new
audit pass delivers **original** findings instead of re-proposing what is already registered.

Reset on **2026-07-30** for v2. The v1 bank held 517 fingerprints accumulated across 20 daily passes
between 2026-05-06 and 2026-05-26; 184 of those were resolved and 177 were invalidated by the
multi-provider port (which removed the `workflows/` directory, the `workflow-detection` skill, and the
`model:` / `tools:` agent frontmatter keys). The 131 entries below are the findings that were
re-verified against the v2 tree with fresh evidence. The full v1 history remains in git at `c9cb5c2`.

---

## How It Works

1. Each finding gets a short **fingerprint** (kebab-case slug) describing the theme.
2. Before generating a new report, the agent **reads this index** and excludes any fingerprint already
   registered here.
3. After publishing, new fingerprints are **appended** below with a link to their source report.
4. A critical theme may be re-proposed only with a **narrower scope** (e.g.
   `token-efficiency-context-loading` is distinct from `token-efficiency-tool-output`).

> **Rotation:** entries older than 90 days are meant to move to `_index-archive-YYYY-Q.md` via
> `helpers/archive-index.sh`. **That script currently has no trigger** — no hook, no CI job, no
> installer call — so rotation has never run. This is registered below as a HIGH finding
> (`flow-helpers-archive-index-sh-orphan-of-hook-…`) and must be fixed before the bank grows back.

---

## Fingerprint Convention

| Category | Prefix | Example |
|----------|--------|---------|
| Docs out of sync | `docs-sync-*` | `docs-sync-readme-skills-list` |
| Broken / orphaned references | `ref-*` | `ref-agent-creator-location` |
| Flow / workflow improvement | `flow-*` | `flow-bugfix-parallel-marker` |
| Agent improvement | `agent-*` | `agent-setup-assistant-size` |
| Skill improvement | `skill-*` | `skill-security-add-incident-response` |
| Token economy | `token-*` | `token-context-loading-dedup` |
| Automation / scripts / hooks | `auto-*` | `auto-skill-frontmatter-validator` |
| Governance / policy | `gov-*` | `gov-orphan-scan-redundancy` |

---

## Statistics

| Date | Published | Originals (cumulative) | Executed / Reverted |
|------|-----------|------------------------|---------------------|
| 2026-05-06 → 2026-05-26 | 517 across 20 passes | 517 | 181 ✅ · 2 ↩️ · 1 🟢 — [archived in git at `c9cb5c2`] |
| 2026-07-30 | 131 (consolidation, no new findings) | 131 | — |
| 2026-07-31 | — (execution pass, no new findings) | 131 | **120 ✅ · 1 ⚠️ · 10 🔴** — throughput **92%** declarado |
| 2026-07-31 | 11 (guardian audit pass) | 142 | Fase 1: **49 de 121 verificados** → 41 ✅ · 3 🟡 · 5 🔴 (**84% confirmado, 10% reaberto**) · Fase 1b: **0% de mortalidade** (0 de 10) |

**v1 → v2 triage:** 334 candidates verified against `HEAD` = `7f85ed7` · 157 survived · 177 died
(53% mortality) · 26 merged as cross-axis duplicates → **131 registered**.

Severity at registration: 11 HIGH · 7 MEDIUM-HIGH · 44 MEDIUM · 42 LOW-MEDIUM · 27 LOW.
**All 11 HIGH are ✅ Executed.**

### The 10 that remain open

Each was verified against the tree on 2026-07-31 and is annotated inline below with why it is
still open. They cluster into three groups:

| Group | Findings | Why they were not closed |
|---|---|---|
| Script decomposition | `install.sh` (now 947 lines), `session-start.sh` (174) | Both grew rather than shrank. Real work, no blocker — simply not reached in this pass. |
| Unadopted patterns | skills `scripts/` subdir, `commit-msg`/Husky registration, 3 unregistered hook events, repo dogfooding only `Stop`, `adr` skill reachable from 1 agent, README `@section` anchors | Each proposes adopting a mechanism the repo does not use anywhere yet. That is a design decision, not a repair. |
| No measurement | CHANGELOG rotation, token-efficiency metric | Both need a threshold or metric nobody has defined. |

The one ⚠️ Partial is the malformed git tags: a CI gate now blocks new ones, and the two published
tags were deliberately left in place because deleting a published tag breaks anyone pinned to it.

> **Instruction for the research agent:** when reading this index, **exclude from generation**:
> - every fingerprint marked ✅ **Executed** — already implemented;
> - every fingerprint marked ↩️ **Reverted** — implemented then deliberately removed;
> - every fingerprint marked 🟢 **Resolved** — resolved by a related change.
>
> ⚠️ **Partial** fingerprints may be re-proposed with a **narrower scope** covering only the pending
> sub-scope described in the note.
>
> **Guardian mode (optional):** when verifying ✅ Executed marks, cross-check against
> `git log --since="<mark-date>"` to detect same-day reverts.

---

## Registered Fingerprints

<!--
  Line format:
    - `<fingerprint>` — **SEVERITY** — description — [report](path) [— ✅ **Executed:** YYYY-MM-DD]

  Status legend:
    ✅ Executed    — implemented; do not re-propose
    ⚠️ Partial     — partially addressed; re-propose only the pending sub-scope
    ↩️ Reverted    — implemented then deliberately reverted; do not re-propose
    🟢 Resolved    — resolved by a related change
    (no marker)   — registered, not yet implemented

  All 131 entries below are unmarked: they were re-verified as reproducing at HEAD 7f85ed7.
-->

## 2026-07-30 — v1 → v2 consolidation

Twenty v1 audit passes collapsed into one verified carry-over set. No new findings were generated;
every entry is a v1 fingerprint that still reproduces in the v2 tree, re-evidenced with current
`path:line` references. See [the consolidation report](2026-07-30/index.md) for method and mortality
breakdown.

### References and Consistency (`ref-*`, `docs-*`) — 21

- `ref-docs-agents-md-model-column-wrong-technical-writer-listed-haiku-actually-sonnet-and-setup-assistant-listed-sonnet-actually-opus` — **HIGH** — `docs/agents.md` Model column is wrong for 2 of 17 agents, mirrored into pt-BR, and unvalidated — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-claude-md-183-code-reviewer-roles-says-delegates-to-test-specialists-but-impl-routes-to-backend-frontend-reviewer` — **HIGH** — `CLAUDE.md` states `code-reviewer` delegates to the test specialists; it routes to the reviewers — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-two-helpers-dirs-naming-collision-root-stripped-vs-scripts-helpers-shipped-claude-md-file-structure-omits-scripts-helpers` — **HIGH** — Two directories named `helpers` with opposite packaging semantics; the shipped one is undocumented — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-claude-md-file-structure-omits-helpers-and-privacy-and-claude-md-folder` — **HIGH** — `CLAUDE.md` File Structure omits six real top-level entries — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-haiku-residual-claude-md-note-after-executed-removal` — **MEDIUM** — `CLAUDE.md` Authoring Standards still mandate `model:` and `tools:` frontmatter that no longer exists — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-templates-dir-shipped-but-not-symlinked-relative-path-broken-from-agent-cwd` — **MEDIUM** — `templates/*-template.md` are referenced by bare relative paths that do not resolve in an installed project — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-skill-ui-libraries-shadcn-frontmatter-name-shadcn-ui-with-hyphen-while-directory-basename-is-shadcn-no-validator-enforces-name-equals-dir-convention` — **MEDIUM** — `shadcn` skill `name:` does not match its directory, and no validator enforces the convention — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-release-prep-skill-exists-twice-shared-88-lines-shipped-vs-claude-skills-181-lines-dev-divergent-content-no-sync-rule` — **MEDIUM** — `release-prep` skill exists twice with divergent content and opposite install fates — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31 — 🔴 **Reaberto na verificação de 2026-07-31:** a única mudança nos dois arquivos na janela foi 1 linha de `description`; as duas cópias (88 e 181 linhas) e a ausência de regra de sync seguem intactas
- `ref-claude-md-hook-files-map-and-file-structure-omit-scripts-hooks-lib-session-summary-detect-shared-dep-of-two-hooks` — **MEDIUM** — `CLAUDE.md` maps never mention `scripts/hooks/lib/`, the one file shared by two hooks — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-claude-md-file-structure-scripts-enumeration-omits-check-updates-rollback-validate-commit-msg-three-shipped-runtime-scripts` — **MEDIUM** — `CLAUDE.md` File Structure documents 5 of 15 scripts and none of the provider machinery — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-claude-md-356-stop-subscript-convention-omits-02b-orphan-template-scan-undocumented-prefix-in-02-tier` — **MEDIUM** — Stop sub-script convention table omits `02b-` and wrongly calls the `99-` tier unused — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-notification-system-content-triplicated-across-04-notifier-sh-notifier-skill-and-claude-md-notifications-md-stop-subscript-table-already-drifted-omitting-05-telemetry` — **MEDIUM** — Notification rules live in three places and the `notifications.md` table has drifted — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31 — 🟡 **Parcial na verificação de 2026-07-31:** a linha `05-` foi adicionada e os tips saíram do bash, mas `skills/shared/notifier/SKILL.md:113-129` ainda carrega o índice e os 15 tips na íntegra
- `ref-templates-backlog-template-md-orphan-confirmed-by-scanner-but-skill-shared-backlog-template-has-inline-template` — **MEDIUM** — `templates/backlog-template.md` is the last orphan template, shadowed by a same-named skill — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-refactor-command-missing-interaction-patterns-load-despite-yes-no-prompts` — **MEDIUM** — `commands/refactor.md` asks a plain-text multiple-choice question, violating the Quiz-first Rule — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-claude-md-130-agent-creator-points-to-external-claude-skills-path-shipped-by-host-not-by-repo-no-validator-checks-the-path-exists-at-runtime-and-orphan-scan-cannot-cover-it` — **LOW-MEDIUM** — `CLAUDE.md` claims the `agent-creator` skill is "not in this repo" — it is git-tracked — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-agent-creator-location` — **LOW-MEDIUM** — `agent-creator` and `skill-creator` live in different trees with inverted install fates — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-three-reviewers-todo-fixme-issue-tracker-tickets-bullet-duplicated-verbatim-no-shared-source-distinct-from-reviewer-base-and-reviewer-mindset-already-extracted` — **LOW-MEDIUM** — The TODO/FIXME reviewer bullet is triplicated and has already forked into two variants — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-two-malformed-git-tags-v-1-1-0-and-v-1-3-13-violate-vx-y-z-convention-in-versioning-md-break-version-sort-and-gap-clean-sequence` — **LOW-MEDIUM** — Two malformed git tags violate the documented `vX.Y.Z` convention — [report](2026-07-30/01-referencias-e-consistencia.md) — ⚠️ **Partial (2026-07-31):** a CI gate now rejects any new tag outside vX.Y.Z. The two published malformed tags were deliberately NOT deleted — removal would break anyone pinned to them and is not safely reversible. Maintainer decision.
- `ref-claude-md-file-structure-skills-subtree-omits-database-mobile-skill-creator-three-of-eleven-domains` — **LOW-MEDIUM** — `CLAUDE.md` File Structure lists 8 of 11 skill domains — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-claude-md-hook-files-map-omits-pre-tool-use-02-telemetry-and-stop-05-telemetry-sub-scripts` — **LOW-MEDIUM** — The Hook Files Map documents four dispatchers and none of the `pre-tool-use/` sub-scripts — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `docs-sync-claude-md-package-exclusions` — **LOW-MEDIUM** — The package-exclusions table has fallen behind `strip-tarball.sh` again — `opencode/` is undocumented — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31

### Flows, Automation and Governance (`flow-*`, `auto-*`, `gov-*`) — 43

- `flow-size-limits-sh-ci-only-warn-only-not-in-stop-dispatcher-asymmetric-with-agent-lint-200-cap-never-blocking` — **HIGH** — The 200-line agent cap is warn-only in CI, has no Stop-hook equivalent, and 11 of 17 agents violate it — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31 — 🟡 **Parcial na verificação de 2026-07-31:** promovido a bloqueante no CI e zero violações, mas segue sem equivalente no dispatcher Stop — `agent-lint.sh` não faz contagem de linhas
- `ref-telemetry-honors-pref-but-pref-defaults-true-on-fresh-install-without-prompt-on-non-interactive-curl-bash` — **HIGH** — Telemetry defaults to enabled on the primary documented install path — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-helpers-archive-index-sh-orphan-of-hook-eight-days-after-flagged-rotation-90-day-promise-in-index-md-line-19-20-has-no-trigger-cron-ci-stop-hook-or-update-sh` — **HIGH** — `helpers/archive-index.sh` is written, committed, and invoked by nothing — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `auto-update-no-integrity-check` — **MEDIUM-HIGH** — `update.sh` downloads and executes the installer with no integrity verification — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `gov-telemetry-send-sh-posthog-key-comments-self-contradict-intentionally-public-vs-replace-before-release-todo-on-default-on-path` — **MEDIUM-HIGH** — The PostHog key carries self-contradicting comments and an unresolved pre-release TODO — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `auto-install-no-rollback-on-second-mv-failure` — **MEDIUM** — `install.sh` deletes the install directory before the `mv`, with no rollback — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-ci-orphan-skill-scan-step-continue-on-error-true-never-blocks-two-duplicate-loads-standing-unaddressed-for-days` — **MEDIUM** — CI lint expresses three different enforcement levels in seven lines, with no stated policy — and the tolerant tier has live findings — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-stop-no-zombie-state-cleanup-discovery-lock-and-worktree-session-persist-across-sessions` — **MEDIUM** — Stop never cleans up zombie session state — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31 — 🔴 **Reaberto na verificação de 2026-07-31:** nenhum commit da janela tocou o alvo; `grep -rn 'worktree-session\|discovery-lock' scripts/hooks/` não retorna nada em `stop/`
- `flow-stop-dispatcher-globs-all-sh-no-allowlist-or-per-subscript-toggle-any-dropped-file-auto-executes` — **MEDIUM** — The Stop dispatcher auto-executes any `.sh` dropped into `stop/` — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-pre-tool-use-dispatcher-no-mention-of-sub-script-order-convention-asymmetric-with-stop-dispatcher` — **MEDIUM** — PreToolUse sub-script ordering is undocumented and already collides — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-telemetry-pre-tool-use-02-runs-on-every-tool-call-without-batching-or-deduplication-burns-200ms-per-burst-session` — **MEDIUM** — PreToolUse telemetry forks `python3` twice on every tool call before its own filter — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31 — 🔴 **Reaberto na verificação de 2026-07-31:** o diff da janela foi um rename (`02-`→`02b-`) mais a troca do guard de consentimento; nenhum batching e nenhuma dedup foram adicionados
- `token-pre-tool-use-01-check-updates-forks-python3-to-read-interval-before-ttl-early-exit-on-every-tool-call-burst-overhead` — **MEDIUM** — `01-check-updates.sh` forks `python3` before its own TTL early-return — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-02b-orphan-template-scan-lacks-devteam-no-changes-fast-path-and-git-scoped-gate-runs-full-scan-every-stop` — **MEDIUM** — `02b-orphan-template-scan.sh` is the only Stop sub-script with no change gate — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-orphan-template-scan-runs-in-stop-but-only-checks-references-not-resolvability-masks-templates-broken-by-relative-path` — **MEDIUM** — `orphan-template-scan.sh` proves a name is mentioned, not that the path resolves — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `ref-orphan-skill-scan-reports-design-system-audit-duplicate-load-in-ui-ux-designer-introduced-in-uknown-commit` — **MEDIUM** — `orphan-skill-scan.sh` still cannot distinguish a load directive from a narrative mention — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-check-fingerprint-uniqueness-scans-only-index-md-blind-to-documented-archive-rotation-cross-file-dupes-undetected` — **MEDIUM** — Fingerprint uniqueness is scoped to a single file, blind to the rotation it is meant to survive — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-readme-sync-ci-gate-checks-only-section-count-and-50pct-line-threshold-not-body-content-passes-while-section-bodies-diverge` — **MEDIUM** — The README-sync gate compares heading counts and line totals, never section bodies — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `auto-agent-lint-quiz-first-regex-only-matches-yes-no-variants-misses-a-b-c-multiple-choice-plain-text-prompts-forbidden-by-same-rule` — **MEDIUM** — `agent-lint.sh` enforces only half the Quiz-first Rule — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `gov-codeowners-coverage-gaps-helpers-readme-pair-canonical-docs-and-skill-domains-unowned-asymmetric` — **MEDIUM** — `.github/CODEOWNERS` leaves half the skill domains unowned and still names a deleted directory — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-stop-dispatcher-computes-no-changes-once-but-02-and-03-each-recompute-identical-git-status-and-git-log-no-shared-touched-set` — **LOW-MEDIUM** — Stop sub-scripts `02` and `03` recompute git state the dispatcher already holds — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-telemetry-stop-05-runs-after-04-notifier-but-no-fast-path-skip-when-DEVTEAM_NO_CHANGES-is-1` — **LOW-MEDIUM** — `05-telemetry.sh` ignores the dispatcher's no-changes fast path — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-no-stop-hook-runs-check-fingerprint-uniqueness-after-_index-edit-only-on-CI-after-push-feedback-too-late` — **LOW-MEDIUM** — Fingerprint uniqueness is only checked after push — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-readme-sync-ci-hardcodes-three-doc-pairs-no-glob-discovery-any-new-pt-br-translation-pair-silently-unchecked` — **LOW-MEDIUM** — The README-sync gate hardcodes three doc pairs with no glob discovery — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-ci-triggers-both-push-and-pull-request-on-all-branches-duplicate-runs-no-concurrency-cancel-in-progress-guard` — **LOW-MEDIUM** — CI fires on both push and pull_request for all branches with no concurrency guard — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-install-sh-chmod-enumeration-omits-scripts-hooks-lib-subdir-manual-per-subdir-list-drifts-on-new-hook-subtree` — **LOW-MEDIUM** — `install.sh` chmod enumeration omits three shipped subtrees — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `ref-size-limits-sh-no-line-cap-for-commands-and-workflows-refactor-md-278-lines-largest-immutable-content-file-unguarded` — **LOW-MEDIUM** — `size-limits.sh` enforces no cap on `commands/`, which now exceeds the agent limit — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `ref-orphan-template-scan-consumers-list-omits-helpers-dir-and-claude-md-false-orphan-risk-asymmetric-with-helpers-refactor` — **LOW-MEDIUM** — `orphan-template-scan.sh` consumer list omits `helpers/`, `CLAUDE.md`, and `CLAUDE-md/` — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `auto-new-adr-sh-sed-title-substitution-breaks-on-pipe-ampersand-backslash-in-free-form-adr-title-no-escaping` — **LOW-MEDIUM** — `scripts/new-adr.sh` injects an unescaped free-form title into a `sed` replacement — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `auto-installer-error-output` — **LOW-MEDIUM** — `install.sh` discards curl/wget stderr on every download — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-cli-commit-validate-msg-script-skipped-silently-when-missing-no-instructive-error` — **LOW-MEDIUM** — `commands/commit.md` skips message validation silently when the script is absent — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31 — 🔴 **Reaberto na verificação de 2026-07-31:** o bloco `commands/commit.md:110-112` é byte-idêntico ao de `7f85ed7`; o que mudou no arquivo foi a adoção do `AskUserQuestion`
- `flow-session-summary-closure-step-present-in-eight-of-ten-workflows-but-absent-from-fullstack-and-refactor-highest-fanout` — **LOW-MEDIUM** — Multi-agent flows close without a session-summary handoff — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-workflows-no-commit-or-pr-step` — **LOW-MEDIUM** — Implementation commands end without a commit or PR handoff — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `gov-plan-template-vs-skill-duplication` — **LOW-MEDIUM** — `templates/plan-template.md` and `plan-mode/SKILL.md` carry two divergent copies of the plan format — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-pre-tool-use-01-check-updates-195-lines-3rd-largest-script-no-fragmentation` — **LOW** — `01-check-updates.sh` is a 209-line monolith — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-session-start-118-lines-monolithic-no-modular-pattern-asymmetric-with-stop-dispatcher` — **LOW** — `session-start.sh` is monolithic and has grown 47% — [report](2026-07-30/02-fluxos-e-workflows.md) — 🔴 **Still open (2026-07-31):** still a 174-line monolith; the sub-script pattern was applied to pre-tool-use/ but not here
- `flow-orphan-template-scan-no-mapping-of-suggested-consumer-vs-orphan-skill-scan` — **LOW** — `orphan-template-scan.sh` reports orphans without suggesting a consumer — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-commit-command-160-lines-pre-commit-gates-extractable-skill` — **LOW** — `commands/commit.md` duplicates the layered-commit table it already loads via a skill — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-conventional-commits-validate-script-no-husky-or-commit-msg-hook-registration` — **LOW** — The installer never registers a `commit-msg` hook or Husky/Lefthook entry — [report](2026-07-30/02-fluxos-e-workflows.md) — 🔴 **Still open (2026-07-31):** no commit-msg hook or Husky/Lefthook registration in install.sh; a plain git commit still bypasses validation
- `flow-hook-events-only-pretooluse-and-stop` — **LOW** — Three Claude Code hook events remain unregistered — [report](2026-07-30/02-fluxos-e-workflows.md) — 🔴 **Still open (2026-07-31):** UserPromptSubmit, SubagentStop and Notification are still unregistered
- `gov-installer-rigor-asymmetry` — **LOW** — The repo installs four hook events into user projects but dogfoods only one — [report](2026-07-30/02-fluxos-e-workflows.md) — 🔴 **Still open (2026-07-31):** the repo self-registers only Stop; 3 of 4 dispatchers remain undogfooded
- `flow-setup-slash-command` — **LOW** — There is still no `/devteam:setup` command — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-commit-md-and-update-md-are-only-2-commands-without-current-context-load-but-both-touch-git-state` — **LOW** — `/devteam:health-check` is absent from every canonical list — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `auto-no-skill-name-uniqueness-check` — **LOW** — No check for skill `name` collisions across categories — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31

### Agents and Skills (`agent-*`, `skill-*`) — 36

- `agent-security-specialist-body-130-153-hardcodes-per-language-sast-and-dep-audit-commands-bandit-composer-npm-trivy-stack-prescriptive` — **HIGH** — `security-specialist` hardcodes per-ecosystem SAST and dependency-audit commands in the body — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-backend-developer-integration-awareness-section-duplicates-provider-specific-critical-rules-inline-for-7-integrations-systemic-stack-prescriptive-body` — **HIGH** — `backend-developer` "Integration Awareness" re-states provider rules inline for 8 integrations — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-frontend-test-specialist-107-122-hardcodes-react-renderhook-testing-library-and-vue-withsetup-recipes-in-body-stack-agnostic` — **HIGH** — `frontend-test-specialist` embeds React and Vue hook-test recipes with code samples — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-devops-specialist-decision-framework-and-anti-overengineering-still-stack-prescriptive-in-body-after-2026-05-18-fix-on-description-and-identity` — **HIGH** — `devops-specialist` Decision Framework and Anti-Overengineering Rules remain stack-prescriptive — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-code-reviewer-router-has-ten-structural-review-categories-contradicting-claude-md-183-router-does-not-duplicate-specialist-checks` — **MEDIUM-HIGH** — `code-reviewer` carries 10 full structural review categories, contradicting its documented router role — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-backend-test-specialist-body-114-120-hardcodes-per-language-coverage-command-matrix-clover-pytest-jacoco-go-simplecov-stack-prescriptive` — **MEDIUM-HIGH** — `backend-test-specialist` hardcodes a five-language coverage command matrix — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `skill-architecture-awareness-shared-behavioral-skill-enumerates-react-vue-svelte-angular-blade-twig-erb-jinja-laravel-django-rails-eager-loaded-by-three-coding-agents` — **MEDIUM-HIGH** — `shared/architecture-awareness` is a behavioral skill that hardcodes framework names, eager-loaded by 3 coding agents — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-setup-assistant-lines-60-70-docker-compose-version-detection-inline-bash-block-stack-prescriptive-in-agent-body-while-mobile-detection-and-stack-detection-already-extracted-to-skills` — **MEDIUM** — `setup-assistant` embeds an inline Docker Compose detection bash block — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-frontend-developer-body-92-102-data-fetching-section-hardcodes-usestate-useeffect-tanstack-query-swr-stack-prescriptive` — **MEDIUM** — `frontend-developer` Data Fetching rules hardcode React/TanStack identifiers outside the detection table — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-frontend-developer-security-section-134-139-hardcodes-dangerouslysetinnerhtml-vhtml-vite-next-public-framework-apis-in-agent-body` — **MEDIUM** — `frontend-developer` Security section hardcodes framework and build-tool APIs — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-frontend-reviewer-body-type-safety-and-code-quality-hardcodes-react-ts-identifiers-proptypes-react-changeevent-hocs` — **MEDIUM** — `frontend-reviewer` type-safety criteria are written in React+TypeScript identifiers — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-database-specialist-description-frontmatter-enumerates-12-engines-and-three-cloud-managed-db-families-stack-prescriptive-identity-surface` — **MEDIUM** — `database-specialist` description pins a closed list of engines — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `skill-mobile-ios-and-android-wrapper-pattern-first-instruction-is-load-ios-hig-or-material-design-doubling-token-cost-251-and-256-lines-total-instead-of-218-and-221-net-loss-vs-loading-the-large-skill-directly` — **MEDIUM** — `mobile/ios` and `mobile/android` are thin wrappers, and platform loading is gated only by prose — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-setup-assistant-three-roles-bundled-extractable-health-checker-update-manager` — **MEDIUM** — `setup-assistant` bundles three distinct roles in one 244-line agent — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-frontend-test-specialist-262-vs-backend-160-asymmetric-decoupled-frontend-block-inlined` — **MEDIUM** — `frontend-test-specialist` inlines reference blocks its backend twin keeps in skills — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-backend-developer-description-enumerates-rest-graphql-mvc-server-rendered-paradigms-on-identity-surface-last-coding-agent-desc-while-body-claims-stack-agnostic` — **LOW-MEDIUM** — `backend-developer` description enumerates paradigms four lines above a stack-neutrality claim — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-mobile-developer-description-frontmatter-enumerates-five-stacks-swift-kotlin-react-native-expo-flutter-on-identity-surface` — **LOW-MEDIUM** — `mobile-developer` description pins five concrete stacks — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-setup-assistant-immutability-section-225-238-redundant-with-warning-line-24-duplicate-md-headers` — **LOW-MEDIUM** — `setup-assistant` contains two `## Immutability Warning` headers — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-code-reviewer-15-item-foundational-rule-longest-in-repo-5-conditional-loads-eager-listed` — **LOW-MEDIUM** — `code-reviewer` mixes five conditional loads into a 15-item mandatory Foundational Rule — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-product-analyst-other-trackers-still-asana-clickup-monday-ungated` — **LOW-MEDIUM** — `product-analyst` has no gate for Asana / ClickUp / Monday / GitHub Issues / Trello — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-software-architect-foundational-rule-51-lines-2x-avg` — **LOW-MEDIUM** — `software-architect` has the largest Foundational Rule in the repo, and it regrew — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-three-reviewers-overlap` — **LOW-MEDIUM** — The three reviewers still duplicate their Foundational Rule almost verbatim — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `skill-architecture-graphql-235-lines-third-largest-no-references-extraction-loaded-by-narrative-gate-not-detection-signal` — **LOW-MEDIUM** — `architecture/graphql` — 235 lines, no `references/` extraction, narrative load gate — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `skill-integrations-gotrue-225-lines-largest-integration-skill-fourth-largest-overall-no-references-extraction-narrative-load-gate` — **LOW-MEDIUM** — `integrations/gotrue` — 225 lines, largest in its domain, no `references/` extraction — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `skill-security-checklist-eager-loaded-by-both-security-specialist-and-qa-specialist-no-documented-boundary-overlapping-responsibility` — **LOW-MEDIUM** — `security-checklist` is loaded by two agents with the overlap asserted rather than partitioned — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `skill-comments-policy-missing-in-non-coding-agents` — **LOW-MEDIUM** — `comments-policy` is absent from 9 of 17 agents, including two write-capable coding agents — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `skill-discovery-mode-no-stale-lock-cleanup-script-30min-rule-only-documented` — **LOW-MEDIUM** — `discovery-mode` stale-lock handling has an ordering bug and a macOS portability failure — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-frontend-developer-and-backend-developer-still-loaded-token-efficiency-inline-line-vs-load-pattern-divergence` — **LOW** — The `token-efficiency` load line has drifted into nine distinct wordings — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-backend-developer-composition-root-rule-1-line-vs-frontend-developer-12-lines-asymmetric-coverage-of-identical-pattern-no-justification` — **LOW** — Composition Root guidance is asymmetric between the two coding agents — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `skill-sonarqube-435-lines-overlap-with-reviewer-base-detection-block` — **LOW** — `reviewer-base` restates a strict subset of the `sonarqube` skill's own detection signals — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `agent-when-loaded-pattern-only-qa` — **LOW** — The `When loaded` sub-block pattern exists in exactly one agent — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `skill-no-skill-uses-scripts-subdir-pattern-agentskills-io` — **LOW** — No skill uses the `scripts/` subdirectory the agentskills.io spec allows — [report](2026-07-30/03-agentes-e-skills.md) — 🔴 **Still open (2026-07-31):** 0 of 138 skills use the spec scripts/ subdir; references/ adoption is unchanged at 20
- `skill-adr-coverage-only-architect` — **LOW** — `shared/adr` is reachable from only one agent — [report](2026-07-30/03-agentes-e-skills.md) — 🔴 **Still open (2026-07-31):** still reachable from 1 agent; the agents that make hard-to-reverse calls have no path to it
- `agent-frontend-developer-loads-jquery-skill-orphan-of-modern-stacks` — **LOW** — `jQuery` sits in `skills/ui-libraries/` alongside modern component libraries — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `skill-missing-prompt-engineering-or-llm-integration` — **LOW** — No skill covers LLM / RAG / prompt-engineering integration, and the one pointer is broken — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31
- `skill-add-load-testing` — **LOW** — No skill covers load / performance testing — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31

### Token Economy (`token-*`) — 31

- `token-claude-md-426-lines-still-monolithic-three-extractable-blocks-commands-table-40-stop-sub-script-convention-24-hook-files-map-8-total-72-lines-while-claude-md-folder-already-exists-with-preferences-notifications-user-data-versioning` — **MEDIUM-HIGH** — `CLAUDE.md` is still monolithic at 425 lines while `CLAUDE-md/` fragmentation is already live — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31 — 🔴 **Reaberto na verificação de 2026-07-31:** CLAUDE.md foi de 425 para 549 linhas e nenhum dos três blocos (`:176`, `:430`, `:473`) foi extraído; nada novo em `CLAUDE-md/`
- `token-foundational-rule-424-lines-across-17-agents` — **MEDIUM-HIGH** — The Foundational Rule block is duplicated inline across 17 agents (384 lines total) — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-token-efficiency-skill-itself-154-lines-eager-loaded-by-all-17-agents-meta-irony-multiplied-in-multi-agent-flows` — **MEDIUM** — The `token-efficiency` skill (154 lines) is eager-loaded by 16 agents, against `CLAUDE.md`'s own instruction — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-project-context-docker-development-environment-section-22-lines-inlined-eager-loaded-by-14-agents-while-sonarqube-same-file-is-detection-gated` — **MEDIUM** — `project-context` inlines an eager Docker section while gating SonarQube in the same file — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-qa-specialist-eager-loads-security-checklist-123-lines-every-spawn-though-behavioral-qa-often-no-security-scope-sonarqube-gated-in-same-file` — **MEDIUM** — `qa-specialist` eager-loads `security-checklist` (123 lines) while gating SonarQube eight lines below — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-conventional-commits-138-lines-eager-loaded-by-code-reviewer-and-backend-reviewer-and-frontend-reviewer-agents-commit-validation-not-in-scope-every-review` — **MEDIUM** — `conventional-commits` (138 lines) is a mandatory Foundational Rule step in all three reviewers — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-code-reviewer-still-eager-loads-comments-policy-after-lazy-load-fix-applied` — **MEDIUM** — `code-reviewer` still eager-loads `comments-policy` as a Foundational Rule step — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-review-shared-skills-reloaded-by-router-then-each-specialist-2-3x-fanout-per-devteam-review-no-shared-loaded-context` — **MEDIUM** — `/devteam:review` fan-out reloads the same shared skill package in every isolated spawn — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-backlog-template-skill-171-lines-unconditionally-loaded-every-product-analyst-spawn-diverged-from-physical-template-same-name` — **MEDIUM** — `product-analyst` loads the 237-line `backlog-template` skill unconditionally — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-plan-mode-skill-131-lines-loaded-by-7-agents-unconditionally` — **MEDIUM** — `plan-mode` (199 lines) is loaded by 7 agents *and* 16 commands — duplicated, not moved — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-frontend-code-quality-description-288-chars-cauda-loaded-by-frontend-developer-as-authoritative-redundant-trim-target-70-chars-pior-offender-confirmado-na-relista-de-2026-05-26` — **MEDIUM** — `frontend-code-quality` has a 288-character description — 3× the budget, with a 67-char meta-narrative tail — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-install-sh-503-lines-largest-single-script-not-fragmented-vs-stop-dispatcher-pattern-13-functions-extractable-each-100-tokens` — **MEDIUM** — `scripts/install.sh` grew to 803 lines with three functions and no decomposition — [report](2026-07-30/04-economia-tokens.md) — 🔴 **Still open (2026-07-31):** install.sh grew 803 → 947 lines; installer-fetch.sh was extracted but the script itself was never decomposed
- `token-telemetry-helper-289-lines-loaded-by-2-sub-scripts-plus-install-update-shell-fork-overhead-150ms-per-event-burst-mode-burns-200ms-acumulado` — **MEDIUM** — `_telemetry_enabled()` is defined three times across the telemetry scripts — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-notifier-loads-45-tips-3-languages-emits-1-per-day-99pct-waste` — **MEDIUM** — `04-notifier.sh` inlines 45 tip strings to emit at most one per day — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-conventional-commits-skill-138-lines-loaded-by-commit-and-pr-commands-but-also-mentioned-as-skill-load-in-claude-md-skill-loads-by-table-format-not-prose` — **LOW-MEDIUM** — `commands/commit.md` loads `conventional-commits` "before doing anything", then may discard it — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-comments-policy-load-directive-duplicated-in-8-agents-multiplied-per-session-in-multi-agent-flows-fullstack-review-spawn-many-agents` — **LOW-MEDIUM** — The `comments-policy` load directive is duplicated verbatim in exactly 8 agents — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-docs-sync-closing-directive-after-completing-any-task-duplicated-verbatim-across-twelve-agents-no-single-source-multiplied-in-multi-agent-flows` — **LOW-MEDIUM** — The `docs-sync` closing directive is duplicated across 13 agents and has begun to drift — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-sonarqube-detection-block-redundant` — **LOW-MEDIUM** — The SonarQube detection triple is restated in 11 agents plus `project-context` — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-worktree-isolation-block-7-lines-x-8-agents` — **LOW-MEDIUM** — The Worktree Isolation cascade is duplicated across 8 coding agents and doubled in size — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-sixteen-skill-descriptions-exceed-95-char-budget-worst-288-inflate-always-loaded-skill-index-regression-of-v1-5-3-trim-no-lint-gate` — **LOW-MEDIUM** — 20 skill descriptions exceed the 95-char budget and no lint gate measures length — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-current-context-block-deduplication` — **LOW-MEDIUM** — The `current-context` preamble is copy-pasted into 19 command files — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-rollback-sh-65-lines-duplicates-installer-download-from-update-sh` — **LOW-MEDIUM** — `rollback.sh` duplicates `update.sh`'s HTTP detection and installer-download logic — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-changelog-already-growing-and-not-extracted-by-release` — **LOW-MEDIUM** — `CHANGELOG.md` reached 441 lines with no rotation and no archive tooling — [report](2026-07-30/04-economia-tokens.md) — 🔴 **Still open (2026-07-31):** CHANGELOG is 441 lines and still has no rotation or archive tooling
- `token-project-rules-override-prose-duplicate` — **LOW** — The "Project rules override base standards" sentence is repeated in 14 agents — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-skill-loads-via-table-vs-prose-inconsistent` — **LOW** — Skill-load declarations are split between tables and prose with no rule — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31 — 🟡 **Parcial na verificação de 2026-07-31:** `security-specialist` e `code-reviewer` migraram para tabela; `frontend-reviewer` segue 0 tabela / 15 refs e nenhuma regra foi escrita (`CLAUDE.md:521` instrui o contrário)
- `token-agent-path-prefix-redundant` — **LOW** — The `.claude/agents/dev-team/` path prefix is repeated 72 times across command files — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-git-log-window-overshoot` — **LOW** — `git log --oneline -20` is used where `-10` is the documented default — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-commands-commit-md-145-lines-and-refactor-md-156-lines-largest-command-files` — **LOW** — `commands/commit.md` and `refactor.md` remain far above the command-file median — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-readme-228-each-after-extraction-still-2-files-no-cross-link-tagging` — **LOW** — The READMEs are maintained as two full-length sources with no section anchors — [report](2026-07-30/04-economia-tokens.md) — 🔴 **Still open (2026-07-31):** no @section anchors; the sync gate got structural checks instead, so the need is reduced but not gone
- `token-dedup-step-reads-full-676-line-prose-index-md-every-run-when-only-fingerprint-slug-list-is-needed-extract-machine-readable-list` — **LOW** — The anti-duplication step reads the full 850-line prose index to recover a flat slug list — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-skills-shared-token-efficiency-not-quantified-in-CLAUDE-md-line-218-no-baseline-roi-tracking` — **LOW** — Token-efficiency rules are mandated with no measurement or feedback loop — [report](2026-07-30/04-economia-tokens.md) — 🔴 **Still open (2026-07-31):** no metric or feedback loop; the token axis still cannot validate its own recommendations

---

## 2026-07-31 — Auditoria guardiã (verificação + 5 eixos)

Primeiro pass guardião sobre o banco v2. Verificou 49 das 121 marcações ✅/⚠️ aplicadas pelo pass de
execução do mesmo dia (84% confirmadas, 10% reabertas), revalidou os 10 achados abertos (0% de
mortalidade) e produziu 11 achados originais. Ver [o relatório do pass](2026-07-31/index.md) para
método, placar e candidatos descartados por duplicação.

### Agnosticismo de Stack (`agent-*`, `flow-*`) — 4

- `agent-frontend-test-specialist-sonarqube-coverage-block-hardcodes-jest-vitest-commands-and-sonar-javascript-key-while-backend-twin-was-delegated` — **MEDIUM-HIGH** — alvo: `agents/frontend-test-specialist.md` — Matriz de comandos de cobertura hardcoded que o gêmeo backend já teve removida — [report](2026-07-31/01-agnosticismo-de-stack.md)
- `agent-frontend-developer-description-frontmatter-enumerates-eight-frameworks-react-vue-svelte-angular-blade-twig-erb-jinja-on-identity-surface` — **MEDIUM** — alvo: `agents/frontend-developer.md` — Oito frameworks fixados na superfície de identidade, defeito já corrigido em `mobile-developer` — [report](2026-07-31/01-agnosticismo-de-stack.md)
- `agent-devops-specialist-core-expertise-declares-primary-docker-and-done-checklist-gates-on-docker-terraform-contradicting-own-never-name-a-product-rule` — **MEDIUM** — alvo: `agents/devops-specialist.md` — O agente declara produto primário e contradiz a própria regra 86 linhas depois — [report](2026-07-31/01-agnosticismo-de-stack.md)
- `flow-audit-command-devops-analysis-prompt-names-redis-cdn-docker-inside-spawn-instruction` — **LOW-MEDIUM** — alvo: `commands/audit.md` — Duas das cinco linhas de escopo do devops-specialist nomeiam vendor — [report](2026-07-31/01-agnosticismo-de-stack.md)

### Referências e Consistência (`docs-sync-*`) — 3

- `docs-sync-claude-md-102-states-skill-desc-strict-false-non-blocking-while-agent-lint-31-sets-true-and-ci-promoted-it-same-day` — **HIGH** — alvo: `CLAUDE.md` — Documenta como verdade corrente o valor oposto ao do código, com a variável nomeada — [report](2026-07-31/02-referencias-e-consistencia.md)
- `docs-sync-claude-md-173-says-all-devteam-commands-load-current-context-while-213-lists-four-exceptions-as-the-complete-list` — **MEDIUM** — alvo: `CLAUDE.md` — Duas afirmações incompatíveis no mesmo arquivo, 40 linhas de distância — [report](2026-07-31/02-referencias-e-consistencia.md)
- `docs-sync-reports-index-md-99-legend-comment-claims-all-131-entries-unmarked-while-121-carry-executed-or-partial-marks` — **LOW-MEDIUM** — alvo: `docs/reports/_index.md` — O comentário de legenda do próprio banco contradiz a contagem de marcadores — [report](2026-07-31/02-referencias-e-consistencia.md)

### Fluxos e Comandos (`auto-*`, `flow-*`) — 2

- `auto-commands-json-plan-gate-field-has-no-consumer-and-no-validator-architect-declared-required-but-body-carries-no-plan-step` — **MEDIUM-HIGH** — alvo: `scripts/lib/commands.json` — Metadado declarado canônico sem consumidor, já divergente em 1 dos 6 comandos `required` — [report](2026-07-31/03-fluxos-e-comandos.md)
- `flow-pre-tool-use-02b-telemetry-reads-devteam-hook-payload-branch-that-only-stop-dispatcher-ever-sets-dead-path-in-pretooluse` — **LOW** — alvo: `scripts/hooks/pre-tool-use/02b-telemetry.sh` — Ramo morto de leitura de payload; contrato assimétrico entre os dois dispatchers — [report](2026-07-31/03-fluxos-e-comandos.md)

### Agentes e Skills (`skill-*`) — 1

- `skill-shared-migration-v1-to-v2-437-lines-largest-in-repo-single-conditional-loader-in-setup-assistant-no-references-extraction-and-no-retirement-criterion` — **MEDIUM** — alvo: `skills/shared/migration-v1-to-v2/SKILL.md` — Maior skill do repo, um carregador, sem `references/` e sem critério de aposentadoria — [report](2026-07-31/04-agentes-e-skills.md)

### Economia de Tokens (`token-*`) — 1

- `token-interaction-patterns-209-lines-loaded-unconditionally-by-24-commands-and-2-agents-while-only-38-lines-are-the-rule-and-159-are-json-examples-and-recurring-patterns` — **MEDIUM-HIGH** — alvo: `skills/shared/interaction-patterns/SKILL.md` — 76% é catálogo de exemplos; extrair para `references/` economiza ≈4.130 linhas agregadas — [report](2026-07-31/05-economia-tokens.md)
