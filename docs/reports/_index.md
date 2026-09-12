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
| 2026-08-12 | 1 (guardian audit pass) | 143 | Fase 1: **30 de 124 verificados** → 26 ✅ · 2 🟢 · **0 🔴 (0% reaberto)** · Fase 1b: **9% de mortalidade** (1 de 11 🟢) · delta de 187 arquivos |
| 2026-08-12 | 5 (guardian audit pass, 2ª execução) | 148 | Fase 1: **6 verificados** (2 marcações da manhã + 4 alvos no delta) → 3 ✅ · **0 🔴** · Fase 1b: **0% de mortalidade** (0 de 2) · delta de 23 arquivos desde `07e0725` |
| 2026-08-14 | 26 (guardian audit pass) | 174 | Fase 1: **49 de 124 verificados** (todos HIGH/MEDIUM-HIGH + 30% do resto) → 42 ✅ · 4 🟡 · 3 🔴 (**86% confirmado, 6,1% reaberto**) · Fase 1b: **0% de mortalidade** (0 de 25) · delta de 16 arquivos desde `3fbe371` |
| 2026-08-21 | 37 (guardian audit pass) | 211 | Fase 1: **48 de 119 verificados** (todos HIGH/MEDIUM-HIGH + 30% do resto) → 43 ✅ · 3 🟡 · 2 🔴 (**90% confirmado, 4,2% reaberto**) · Fase 1b: **2,4% de mortalidade** (1 de 42 🟢) · delta de 39 arquivos em 33 commits desde `c03f898` |
| 2026-08-28 | 21 (guardian audit pass) | 232 | **Delta zero** — `HEAD` = `a67cac9` = baseline anterior; o output do pass de 2026-08-21 estava não commitado. Fase 1: **22 de 73 não cobertos** (os 18 HIGH/MEDIUM-HIGH já verificados contra este mesmo sha em 2026-08-21) → 18 ✅ · 2 🟡 · 2 🔴 (**82% confirmado, 9,1% reaberto**); acumulado contra `a67cac9`: **70 de 121 (58%)** → 61 ✅ · 5 🟡 · 4 🔴 (**87% / 5,7%**) · Fase 1b: **0% de mortalidade** (0 de 50) — reflete a imobilidade do repositório, não durabilidade do banco |
| 2026-09-04 | 3 (guardian audit pass) | 235 | **Delta zero pelo 3º pass consecutivo** — `HEAD` = `a67cac9` = baseline anterior; o output de 2026-08-21 e 2026-08-28 seguia não commitado (58 fingerprints só no disco). Fase 1: **17 de 51 não cobertos (33%)** → 13 ✅ · 2 🟡 · 2 🔴 (**76% confirmado, 11,8% divergente**); acumulado contra `a67cac9`: **87 de 121 (72%)** → 74 ✅ · 7 🟡 · 6 🔴 (**85% / 6,9%**) · Fase 1b: **0% de mortalidade** (0 de 110; 8 verificados como teste da premissa de árvore imóvel) |
| 2026-09-11 | 4 (guardian audit pass) | 239 | Primeiro delta de baseline em 4 passes, mas **zero de código** — `HEAD` = `9530551`, um commit (`docs(reports): metrics reports updates`) sobre 2 arquivos de métricas; último commit de código `a1e3791`, 21 dias. Fase 1: **12 de 34 não cobertos (35%)** → 9 ✅ · 2 🟡 · 1 🔴 — **0 🔴 nova** (a única 🔴 já estava registrada desde 2026-07-31); acumulado **99 de 121 (82%)** → 83 ✅ · 9 🟡 · 7 🔴 (**84% / 7,1%**) · Fase 1b: **0% de mortalidade** (0 de 113; 6 verificados como teste da premissa) · Eixos A, D e E: nenhum achado original |

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
- `ref-release-prep-skill-exists-twice-shared-88-lines-shipped-vs-claude-skills-181-lines-dev-divergent-content-no-sync-rule` — **MEDIUM** — `release-prep` skill exists twice with divergent content and opposite install fates — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31 — 🔴 **Reaberto na verificação de 2026-07-31:** a única mudança nos dois arquivos na janela foi 1 linha de `description`; as duas cópias (88 e 181 linhas) e a ausência de regra de sync seguem intactas — 🔴 **Reaberto na verificação de 2026-08-28:** `7736e20` tocou o alvo apenas para reescrever 1 linha de `description` (corte para o orçamento de 95 chars), não para remediar; as duas cópias seguem com 88 vs. 182 linhas, destinos de instalação opostos (`KEEP_ROOT` vs. `strip-tarball.sh`) e nenhuma regra de sincronização
- `ref-claude-md-hook-files-map-and-file-structure-omit-scripts-hooks-lib-session-summary-detect-shared-dep-of-two-hooks` — **MEDIUM** — `CLAUDE.md` maps never mention `scripts/hooks/lib/`, the one file shared by two hooks — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-claude-md-file-structure-scripts-enumeration-omits-check-updates-rollback-validate-commit-msg-three-shipped-runtime-scripts` — **MEDIUM** — `CLAUDE.md` File Structure documents 5 of 15 scripts and none of the provider machinery — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-claude-md-356-stop-subscript-convention-omits-02b-orphan-template-scan-undocumented-prefix-in-02-tier` — **MEDIUM** — Stop sub-script convention table omits `02b-` and wrongly calls the `99-` tier unused — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-notification-system-content-triplicated-across-04-notifier-sh-notifier-skill-and-claude-md-notifications-md-stop-subscript-table-already-drifted-omitting-05-telemetry` — **MEDIUM** — Notification rules live in three places and the `notifications.md` table has drifted — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31 — 🟡 **Parcial na verificação de 2026-07-31:** a linha `05-` foi adicionada e os tips saíram do bash, mas `skills/shared/notifier/SKILL.md:113-129` ainda carrega o índice e os 15 tips na íntegra — 🟡 **Parcial na verificação de 2026-08-28:** dois dos três vértices resolvidos (linha `05-` na tabela por `bbb311a`; tips extraídos para `stop/tips/*.txt` por `6919564`), mas `skills/shared/notifier/SKILL.md:113-133` ainda carrega a fórmula de índice e os 15 textos — quarta cópia paralela a `tips.en.txt`
- `ref-templates-backlog-template-md-orphan-confirmed-by-scanner-but-skill-shared-backlog-template-has-inline-template` — **MEDIUM** — `templates/backlog-template.md` is the last orphan template, shadowed by a same-named skill — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-refactor-command-missing-interaction-patterns-load-despite-yes-no-prompts` — **MEDIUM** — `commands/refactor.md` asks a plain-text multiple-choice question, violating the Quiz-first Rule — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-claude-md-130-agent-creator-points-to-external-claude-skills-path-shipped-by-host-not-by-repo-no-validator-checks-the-path-exists-at-runtime-and-orphan-scan-cannot-cover-it` — **LOW-MEDIUM** — `CLAUDE.md` claims the `agent-creator` skill is "not in this repo" — it is git-tracked — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-agent-creator-location` — **LOW-MEDIUM** — `agent-creator` and `skill-creator` live in different trees with inverted install fates — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31 — 🟡 **Parcial na verificação de 2026-08-28:** `bbb311a` documentou o destino de empacotamento (remediação do fingerprint irmão `ref-claude-md-130-agent-creator-…`), mas não moveu arquivo algum; `git log -- .claude/skills/agent-creator/` para em `c9cb5c2`, anterior à janela, e a skill segue inalcançável por qualquer provider instalado
- `ref-three-reviewers-todo-fixme-issue-tracker-tickets-bullet-duplicated-verbatim-no-shared-source-distinct-from-reviewer-base-and-reviewer-mindset-already-extracted` — **LOW-MEDIUM** — The TODO/FIXME reviewer bullet is triplicated and has already forked into two variants — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-two-malformed-git-tags-v-1-1-0-and-v-1-3-13-violate-vx-y-z-convention-in-versioning-md-break-version-sort-and-gap-clean-sequence` — **LOW-MEDIUM** — Two malformed git tags violate the documented `vX.Y.Z` convention — [report](2026-07-30/01-referencias-e-consistencia.md) — ⚠️ **Partial (2026-07-31):** a CI gate now rejects any new tag outside vX.Y.Z. The two published malformed tags were deliberately NOT deleted — removal would break anyone pinned to them and is not safely reversible. Maintainer decision.
- `ref-claude-md-file-structure-skills-subtree-omits-database-mobile-skill-creator-three-of-eleven-domains` — **LOW-MEDIUM** — `CLAUDE.md` File Structure lists 8 of 11 skill domains — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `ref-claude-md-hook-files-map-omits-pre-tool-use-02-telemetry-and-stop-05-telemetry-sub-scripts` — **LOW-MEDIUM** — The Hook Files Map documents four dispatchers and none of the `pre-tool-use/` sub-scripts — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31
- `docs-sync-claude-md-package-exclusions` — **LOW-MEDIUM** — The package-exclusions table has fallen behind `strip-tarball.sh` again — `opencode/` is undocumented — [report](2026-07-30/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-07-31

### Flows, Automation and Governance (`flow-*`, `auto-*`, `gov-*`) — 43

- `flow-size-limits-sh-ci-only-warn-only-not-in-stop-dispatcher-asymmetric-with-agent-lint-200-cap-never-blocking` — **HIGH** — The 200-line agent cap is warn-only in CI, has no Stop-hook equivalent, and 11 of 17 agents violate it — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31 — 🟡 **Parcial na verificação de 2026-07-31:** promovido a bloqueante no CI e zero violações, mas segue sem equivalente no dispatcher Stop — `agent-lint.sh` não faz contagem de linhas — 🟡 **Parcial na verificação de 2026-08-14:** segunda confirmação — CI segue bloqueante e a árvore limpa, mas `scripts/hooks/stop/` não tem checagem de tamanho e `helpers/agent-lint.sh` não conta linhas — 🟡 **Parcial na verificação de 2026-08-21:** terceira confirmação — `scripts/hooks/stop/` segue sem checagem de tamanho; e a nota de 2026-08-14 ("a árvore limpa") ficou obsoleta: `bash helpers/size-limits.sh` sai 1 no HEAD por `CLAUDE.md: 602 lines`
- `ref-telemetry-honors-pref-but-pref-defaults-true-on-fresh-install-without-prompt-on-non-interactive-curl-bash` — **HIGH** — Telemetry defaults to enabled on the primary documented install path — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-helpers-archive-index-sh-orphan-of-hook-eight-days-after-flagged-rotation-90-day-promise-in-index-md-line-19-20-has-no-trigger-cron-ci-stop-hook-or-update-sh` — **HIGH** — `helpers/archive-index.sh` is written, committed, and invoked by nothing — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `auto-update-no-integrity-check` — **MEDIUM-HIGH** — `update.sh` downloads and executes the installer with no integrity verification — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `gov-telemetry-send-sh-posthog-key-comments-self-contradict-intentionally-public-vs-replace-before-release-todo-on-default-on-path` — **MEDIUM-HIGH** — The PostHog key carries self-contradicting comments and an unresolved pre-release TODO — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `auto-install-no-rollback-on-second-mv-failure` — **MEDIUM** — `install.sh` deletes the install directory before the `mv`, with no rollback — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-ci-orphan-skill-scan-step-continue-on-error-true-never-blocks-two-duplicate-loads-standing-unaddressed-for-days` — **MEDIUM** — CI lint expresses three different enforcement levels in seven lines, with no stated policy — and the tolerant tier has live findings — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-stop-no-zombie-state-cleanup-discovery-lock-and-worktree-session-persist-across-sessions` — **MEDIUM** — Stop never cleans up zombie session state — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31 — 🔴 **Reaberto na verificação de 2026-07-31:** nenhum commit da janela tocou o alvo; `grep -rn 'worktree-session\|discovery-lock' scripts/hooks/` não retorna nada em `stop/` — 🔴 **Reaberto na verificação de 2026-08-28:** nenhum commit da janela de 2026-07-31 tocou o alvo; `grep -rn '\.worktree-session' scripts/` devolve só `install.sh:931` (gitignore), `ls scripts/hooks/stop/` não tem sub-script de cleanup e `session-start.sh` não limpa nada — um marcador remanescente segue direcionando a próxima sessão em silêncio
- `flow-stop-dispatcher-globs-all-sh-no-allowlist-or-per-subscript-toggle-any-dropped-file-auto-executes` — **MEDIUM** — The Stop dispatcher auto-executes any `.sh` dropped into `stop/` — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-pre-tool-use-dispatcher-no-mention-of-sub-script-order-convention-asymmetric-with-stop-dispatcher` — **MEDIUM** — PreToolUse sub-script ordering is undocumented and already collides — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-telemetry-pre-tool-use-02-runs-on-every-tool-call-without-batching-or-deduplication-burns-200ms-per-burst-session` — **MEDIUM** — PreToolUse telemetry forks `python3` twice on every tool call before its own filter — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31 — 🔴 **Reaberto na verificação de 2026-07-31:** o diff da janela foi um rename (`02-`→`02b-`) mais a troca do guard de consentimento; nenhum batching e nenhuma dedup foram adicionados — 🟢 **Resolved:** 2026-08-12 — resolvido por `156771b`: `02b-telemetry.sh` agora enfileira eventos (flush no Stop) e faz early-exit por substring antes do fork `python3` — 🟢 **Resolved:** correção de crédito em 2026-08-14 — o early-exit veio de `f1ca129` (2026-08-06), não de `156771b` (que só reativou o sub-script renomeado); o enfileiramento já existia desde `bd61ff7`, anterior à marcação
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
- `flow-cli-commit-validate-msg-script-skipped-silently-when-missing-no-instructive-error` — **LOW-MEDIUM** — `commands/commit.md` skips message validation silently when the script is absent — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31 — 🔴 **Reaberto na verificação de 2026-07-31:** o bloco `commands/commit.md:110-112` é byte-idêntico ao de `7f85ed7`; o que mudou no arquivo foi a adoção do `AskUserQuestion` — 🔴 **Reaberto na verificação de 2026-09-11:** segunda confirmação, agora contra `9530551` — `commands/commit.md:144-147` segue sem ramo `else`; a adoção do `AskUserQuestion` (`:150-153`) só dispara quando um gate **retorna** não-zero, e um script ausente não retorna nada
- `flow-session-summary-closure-step-present-in-eight-of-ten-workflows-but-absent-from-fullstack-and-refactor-highest-fanout` — **LOW-MEDIUM** — Multi-agent flows close without a session-summary handoff — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-workflows-no-commit-or-pr-step` — **LOW-MEDIUM** — Implementation commands end without a commit or PR handoff — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `gov-plan-template-vs-skill-duplication` — **LOW-MEDIUM** — `templates/plan-template.md` and `plan-mode/SKILL.md` carry two divergent copies of the plan format — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-pre-tool-use-01-check-updates-195-lines-3rd-largest-script-no-fragmentation` — **LOW** — `01-check-updates.sh` is a 209-line monolith — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-session-start-118-lines-monolithic-no-modular-pattern-asymmetric-with-stop-dispatcher` — **LOW** — `session-start.sh` is monolithic and has grown 47% — [report](2026-07-30/02-fluxos-e-workflows.md) — 🔴 **Still open (2026-07-31):** still a 174-line monolith; the sub-script pattern was applied to pre-tool-use/ but not here — 📈 **Deriva registrada em 2026-09-04:** `scripts/hooks/session-start.sh` está em **310 linhas** (118 no slug, 174 em 2026-07-31); o achado segue aberto e o número do slug está obsoleto
- `flow-orphan-template-scan-no-mapping-of-suggested-consumer-vs-orphan-skill-scan` — **LOW** — `orphan-template-scan.sh` reports orphans without suggesting a consumer — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-commit-command-160-lines-pre-commit-gates-extractable-skill` — **LOW** — `commands/commit.md` duplicates the layered-commit table it already loads via a skill — [report](2026-07-30/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-07-31
- `flow-conventional-commits-validate-script-no-husky-or-commit-msg-hook-registration` — **LOW** — The installer never registers a `commit-msg` hook or Husky/Lefthook entry — [report](2026-07-30/02-fluxos-e-workflows.md) — 🔴 **Still open (2026-07-31):** no commit-msg hook or Husky/Lefthook registration in install.sh; a plain git commit still bypasses validation
- `flow-hook-events-only-pretooluse-and-stop` — **LOW** — Three Claude Code hook events remain unregistered — [report](2026-07-30/02-fluxos-e-workflows.md) — 🔴 **Still open (2026-07-31):** UserPromptSubmit, SubagentStop and Notification are still unregistered
- `gov-installer-rigor-asymmetry` — **LOW** — The repo installs four hook events into user projects but dogfoods only one — [report](2026-07-30/02-fluxos-e-workflows.md) — 🔴 **Still open (2026-07-31):** the repo self-registers only Stop; 3 of 4 dispatchers remain undogfooded — 🟢 **Resolved:** 2026-08-12 — resolvido por `872477b`+`ae77545`: `.claude/settings.json` agora registra Stop, PreToolUse, SessionStart e PreCompact
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
- `agent-frontend-developer-body-92-102-data-fetching-section-hardcodes-usestate-useeffect-tanstack-query-swr-stack-prescriptive` — **MEDIUM** — `frontend-developer` Data Fetching rules hardcode React/TanStack identifiers outside the detection table — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31 — 🟡 **Parcial na verificação de 2026-08-14:** a tabela de detecção ganhou coluna de regras, mas `frontend-developer.md:96` ainda recomenda TanStack Query e SWR nominalmente ancorado no "React/Vue ecosystem", e `:91` mantém "e.g. React `useState`" fora da tabela — 🟡 **Parcial na verificação de 2026-09-04:** segunda confirmação, agora contra `a67cac9` — `:91` (`React useState`) e `:96` (TanStack Query/SWR, "React/Vue ecosystem") seguem sob o heading `## Server State & Data Fetching`, fora da tabela de detecção
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
- `agent-software-architect-foundational-rule-51-lines-2x-avg` — **LOW-MEDIUM** — `software-architect` has the largest Foundational Rule in the repo, and it regrew — [report](2026-07-30/03-agentes-e-skills.md) — ✅ **Executed:** 2026-07-31 — 🔴 **Reaberto na verificação de 2026-08-21:** `b4e219f` tocou o arquivo, mas a Foundational Rule **cresceu** — 37 linhas em `b4e219f~1` → 41 no próprio commit remediador → **43 no HEAD**; segue a maior do repo (2ª: `security-specialist`, 38)
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

- `token-claude-md-426-lines-still-monolithic-three-extractable-blocks-commands-table-40-stop-sub-script-convention-24-hook-files-map-8-total-72-lines-while-claude-md-folder-already-exists-with-preferences-notifications-user-data-versioning` — **MEDIUM-HIGH** — `CLAUDE.md` is still monolithic at 425 lines while `CLAUDE-md/` fragmentation is already live — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31 — 🔴 **Reaberto na verificação de 2026-07-31:** CLAUDE.md foi de 425 para 549 linhas e nenhum dos três blocos (`:176`, `:430`, `:473`) foi extraído; nada novo em `CLAUDE-md/` — 🔴 **Reaberto na verificação de 2026-08-14:** segunda confirmação — `CLAUDE.md` agora em 586 linhas (425 na abertura), a tabela de comandos segue inline em `:211`, e a única extração (`CLAUDE-md/hooks.md`) veio de `2b436ea` em 2026-08-03, fora da janela da marca — 🔴 **Reaberto na verificação de 2026-08-21:** terceira confirmação — nenhum commit de 2026-07-31 tocou `CLAUDE.md`/`CLAUDE-md/`; `CLAUDE.md` está em **602 linhas** (425 na abertura), tabela de comandos inline em `:212` e `## Agent Memory System` inline em `:418`
- `token-foundational-rule-424-lines-across-17-agents` — **MEDIUM-HIGH** — The Foundational Rule block is duplicated inline across 17 agents (384 lines total) — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-token-efficiency-skill-itself-154-lines-eager-loaded-by-all-17-agents-meta-irony-multiplied-in-multi-agent-flows` — **MEDIUM** — The `token-efficiency` skill (154 lines) is eager-loaded by 16 agents, against `CLAUDE.md`'s own instruction — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31 — 🔴 **Reaberto na verificação de 2026-08-14:** o commit da janela só unificou a redação da linha de load; o load segue eager em 18/18 agentes e a skill cresceu de 154 para 160 linhas, contra `CLAUDE.md:177`
- `token-project-context-docker-development-environment-section-22-lines-inlined-eager-loaded-by-14-agents-while-sonarqube-same-file-is-detection-gated` — **MEDIUM** — `project-context` inlines an eager Docker section while gating SonarQube in the same file — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-qa-specialist-eager-loads-security-checklist-123-lines-every-spawn-though-behavioral-qa-often-no-security-scope-sonarqube-gated-in-same-file` — **MEDIUM** — `qa-specialist` eager-loads `security-checklist` (123 lines) while gating SonarQube eight lines below — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-conventional-commits-138-lines-eager-loaded-by-code-reviewer-and-backend-reviewer-and-frontend-reviewer-agents-commit-validation-not-in-scope-every-review` — **MEDIUM** — `conventional-commits` (138 lines) is a mandatory Foundational Rule step in all three reviewers — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-code-reviewer-still-eager-loads-comments-policy-after-lazy-load-fix-applied` — **MEDIUM** — `code-reviewer` still eager-loads `comments-policy` as a Foundational Rule step — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-review-shared-skills-reloaded-by-router-then-each-specialist-2-3x-fanout-per-devteam-review-no-shared-loaded-context` — **MEDIUM** — `/devteam:review` fan-out reloads the same shared skill package in every isolated spawn — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31 — 🟡 **Parcial na verificação de 2026-09-11:** `6919564` encolheu `commands/review.md` (68 linhas) e `b4e219f` reduziu `project-context` de 321 para 269 linhas (−16%), mas o problema enunciado — nenhum mecanismo passa sumário factual entre spawns — segue intacto: `review.md:41-52` dispara 4 spawns incondicionais + 2 condicionais e `code-reviewer` roteia para mais 2, **8 execuções isoladas**, cada uma re-executando `project-context` (269) + `token-efficiency` (160) + `interaction-patterns` (209) + `comments-policy` + `reviewer-base`; reduziu-se o tamanho do que é recarregado, não a contagem de recargas
- `token-backlog-template-skill-171-lines-unconditionally-loaded-every-product-analyst-spawn-diverged-from-physical-template-same-name` — **MEDIUM** — `product-analyst` loads the 237-line `backlog-template` skill unconditionally — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-plan-mode-skill-131-lines-loaded-by-7-agents-unconditionally` — **MEDIUM** — `plan-mode` (199 lines) is loaded by 7 agents *and* 16 commands — duplicated, not moved — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-frontend-code-quality-description-288-chars-cauda-loaded-by-frontend-developer-as-authoritative-redundant-trim-target-70-chars-pior-offender-confirmado-na-relista-de-2026-05-26` — **MEDIUM** — `frontend-code-quality` has a 288-character description — 3× the budget, with a 67-char meta-narrative tail — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-install-sh-503-lines-largest-single-script-not-fragmented-vs-stop-dispatcher-pattern-13-functions-extractable-each-100-tokens` — **MEDIUM** — `scripts/install.sh` grew to 803 lines with three functions and no decomposition — [report](2026-07-30/04-economia-tokens.md) — 🔴 **Still open (2026-07-31):** install.sh grew 803 → 947 lines; installer-fetch.sh was extracted but the script itself was never decomposed
- `token-telemetry-helper-289-lines-loaded-by-2-sub-scripts-plus-install-update-shell-fork-overhead-150ms-per-event-burst-mode-burns-200ms-acumulado` — **MEDIUM** — `_telemetry_enabled()` is defined three times across the telemetry scripts — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-notifier-loads-45-tips-3-languages-emits-1-per-day-99pct-waste` — **MEDIUM** — `04-notifier.sh` inlines 45 tip strings to emit at most one per day — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-conventional-commits-skill-138-lines-loaded-by-commit-and-pr-commands-but-also-mentioned-as-skill-load-in-claude-md-skill-loads-by-table-format-not-prose` — **LOW-MEDIUM** — `commands/commit.md` loads `conventional-commits` "before doing anything", then may discard it — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31 — 🔴 **Reaberto na verificação de 2026-09-04:** nenhum commit da janela tocou a diretiva de carga; `commands/commit.md:7` ainda carrega o skill (hoje 169 linhas, eram 138) "before doing anything", que a Commit Rule do `CLAUDE.md` manda descartar quando o projeto usa outro padrão — `6919564` só removeu a tabela de camadas restatada
- `token-comments-policy-load-directive-duplicated-in-8-agents-multiplied-per-session-in-multi-agent-flows-fullstack-review-spawn-many-agents` — **LOW-MEDIUM** — The `comments-policy` load directive is duplicated verbatim in exactly 8 agents — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-docs-sync-closing-directive-after-completing-any-task-duplicated-verbatim-across-twelve-agents-no-single-source-multiplied-in-multi-agent-flows` — **LOW-MEDIUM** — The `docs-sync` closing directive is duplicated across 13 agents and has begun to drift — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-sonarqube-detection-block-redundant` — **LOW-MEDIUM** — The SonarQube detection triple is restated in 11 agents plus `project-context` — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31 — 🟡 **Parcial na verificação de 2026-08-14:** 10 das 11 cópias removidas, mas `devops-specialist.md:81` ainda restata 4 dos 6 sinais da tabela canônica de `skills/devops/sonarqube/SKILL.md` — 🟡 **Parcial na verificação de 2026-09-04:** segunda confirmação — `devops-specialist.md:81` ainda restata 4 dos 6 sinais da tabela canônica; faltam `sonar-scanner`/`mvn sonar:sonar`/`./gradlew sonar` em CI e `sonarqube-scanner` em `package.json`/`pom.xml`/`build.gradle`
- `token-worktree-isolation-block-7-lines-x-8-agents` — **LOW-MEDIUM** — The Worktree Isolation cascade is duplicated across 8 coding agents and doubled in size — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-sixteen-skill-descriptions-exceed-95-char-budget-worst-288-inflate-always-loaded-skill-index-regression-of-v1-5-3-trim-no-lint-gate` — **LOW-MEDIUM** — 20 skill descriptions exceed the 95-char budget and no lint gate measures length — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-current-context-block-deduplication` — **LOW-MEDIUM** — The `current-context` preamble is copy-pasted into 19 command files — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-rollback-sh-65-lines-duplicates-installer-download-from-update-sh` — **LOW-MEDIUM** — `rollback.sh` duplicates `update.sh`'s HTTP detection and installer-download logic — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-changelog-already-growing-and-not-extracted-by-release` — **LOW-MEDIUM** — `CHANGELOG.md` reached 441 lines with no rotation and no archive tooling — [report](2026-07-30/04-economia-tokens.md) — 🔴 **Still open (2026-07-31):** CHANGELOG is 441 lines and still has no rotation or archive tooling
- `token-project-rules-override-prose-duplicate` — **LOW** — The "Project rules override base standards" sentence is repeated in 14 agents — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-skill-loads-via-table-vs-prose-inconsistent` — **LOW** — Skill-load declarations are split between tables and prose with no rule — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31 — 🟡 **Parcial na verificação de 2026-07-31:** `security-specialist` e `code-reviewer` migraram para tabela; `frontend-reviewer` segue 0 tabela / 15 refs e nenhuma regra foi escrita (`CLAUDE.md:521` instrui o contrário) — 🟡 **Parcial na verificação de 2026-08-14:** quadro inalterado desde 2026-07-31 — `frontend-reviewer` segue 0 tabela / 17 refs em prosa, e nenhuma regra de formato foi escrita (`CLAUDE.md:539` instrui o oposto)
- `token-agent-path-prefix-redundant` — **LOW** — The `.claude/agents/dev-team/` path prefix is repeated 72 times across command files — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31
- `token-git-log-window-overshoot` — **LOW** — `git log --oneline -20` is used where `-10` is the documented default — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31 — 🟡 **Parcial na verificação de 2026-09-11:** `b4e219f` corrigiu 4 dos 5 alvos (`security-specialist.md`, `ui-ux-designer.md`, `qa-specialist.md`, `technical-writer.md`); o quinto, `skills/shared/setup-scan/SKILL.md:16`, mantém `git log --oneline -20` e nenhuma commit da janela de 2026-07-31 tocou o arquivo — é hoje a única ocorrência de `-20` no repositório contra o `-10` canônico do `CLAUDE.md` § Commit Rule
- `token-commands-commit-md-145-lines-and-refactor-md-156-lines-largest-command-files` — **LOW** — `commands/commit.md` and `refactor.md` remain far above the command-file median — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31 — 🟡 **Parcial na verificação de 2026-08-21:** `6919564` removeu duplicação e criou um gate de 200 linhas, mas `commit.md` está em **193** e `refactor.md` em **172** (177/159 no achado; mediana dos 35 comandos = 71) — `refactor.md` cresceu +5 dentro do próprio commit remediador
- `token-readme-228-each-after-extraction-still-2-files-no-cross-link-tagging` — **LOW** — The READMEs are maintained as two full-length sources with no section anchors — [report](2026-07-30/04-economia-tokens.md) — 🔴 **Still open (2026-07-31):** no @section anchors; the sync gate got structural checks instead, so the need is reduced but not gone
- `token-dedup-step-reads-full-676-line-prose-index-md-every-run-when-only-fingerprint-slug-list-is-needed-extract-machine-readable-list` — **LOW** — The anti-duplication step reads the full 850-line prose index to recover a flat slug list — [report](2026-07-30/04-economia-tokens.md) — ✅ **Executed:** 2026-07-31 — 🔴 **Reaberto na verificação de 2026-09-04:** nenhuma lista legível por máquina existe (`ls docs/reports/*.txt docs/reports/*.json` → nada); as Portas 1 e 2 seguem varrendo `_index.md` em prosa (548 linhas / 109 KB). O campo `alvo:` de `7736e20` barateia a Porta 2 mas não é a extração pedida
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

- `auto-commands-json-plan-gate-field-has-no-consumer-and-no-validator-architect-declared-required-but-body-carries-no-plan-step` — **MEDIUM-HIGH** — alvo: `scripts/lib/commands.json` — Metadado declarado canônico sem consumidor, já divergente em 1 dos 6 comandos `required` — [report](2026-07-31/03-fluxos-e-comandos.md) — 🟢 **Resolved:** 2026-08-12 — `scripts/lib/render_provider.py:105` `soften_plan_gate()` consome `meta.get("plan_gate")` (linhas 899, 921, 928)
- `flow-pre-tool-use-02b-telemetry-reads-devteam-hook-payload-branch-that-only-stop-dispatcher-ever-sets-dead-path-in-pretooluse` — **LOW** — alvo: `scripts/hooks/pre-tool-use/02b-telemetry.sh` — Ramo morto de leitura de payload; contrato assimétrico entre os dois dispatchers — [report](2026-07-31/03-fluxos-e-comandos.md)

### Agentes e Skills (`skill-*`) — 1

- `skill-shared-migration-v1-to-v2-437-lines-largest-in-repo-single-conditional-loader-in-setup-assistant-no-references-extraction-and-no-retirement-criterion` — **MEDIUM** — alvo: `skills/shared/migration-v1-to-v2/SKILL.md` — Maior skill do repo, um carregador, sem `references/` e sem critério de aposentadoria — [report](2026-07-31/04-agentes-e-skills.md)

### Economia de Tokens (`token-*`) — 1

- `token-interaction-patterns-209-lines-loaded-unconditionally-by-24-commands-and-2-agents-while-only-38-lines-are-the-rule-and-159-are-json-examples-and-recurring-patterns` — **MEDIUM-HIGH** — alvo: `skills/shared/interaction-patterns/SKILL.md` — 76% é catálogo de exemplos; extrair para `references/` economiza ≈4.130 linhas agregadas — [report](2026-07-31/05-economia-tokens.md)

---

## 2026-08-12 — Auditoria guardiã (verificação + 5 eixos)

Segundo pass guardião sobre o banco v2, contra um delta grande (187 arquivos desde `f54569a`).
Verificou 30 das 124 marcações ✅/⚠️ (100% dos HIGH/MEDIUM-HIGH e de todos os itens antes
sinalizados) com **0% de reabertura**, revalidou os 11 achados abertos (**9% de mortalidade** — 1 🟢),
detectou 2 marcações reabertas/abertas **fechadas de passagem** pelo delta, e produziu 1 achado
original. Ver [o relatório do pass](2026-08-12/index.md) para método, placar e descartados por
duplicação.

### Agnosticismo de Stack (`flow-*`) — 1

- `flow-relayout-design-discovery-names-storybook-tailwind` — **LOW-MEDIUM** — alvo: `commands/relayout.md` — A descoberta de contexto de design (seção obrigatória) nomeia Storybook e Tailwind como locais de tokens, acoplando o comando ao ecossistema JS/React — [report](2026-08-12/01-agnosticismo-de-stack.md)

### Descartados por duplicação

- `frontend-developer.md:96` nomeia TanStack/SWR/React/Vue — Porta 3 (semântica): alvo + causa-raiz coincidem com `agent-frontend-developer-body-92-102-data-fetching-section-hardcodes-usestate-useeffect-tanstack-query-swr…` (✅)
- `CLAUDE.md` 586 linhas / `install.sh` 1085 / `CHANGELOG` 959 / `session-start.sh` 306 — Porta 5 (estado): itens já registrados e abertos
- Sub-scripts `03c/03d/03e` "re-forkam git" — Porta 3: hipótese refutada por evidência (reusam `DEVTEAM_TOUCHED_PATHS`)
- `_disabled-*` "auto-executam" — hipótese refutada (ambos dispatchers têm `SUBSCRIPT_RE` allowlist)

---

## 2026-08-12 — Auditoria guardiã, 2ª execução (delta pós-`07e0725`)

Segunda execução do pass guardião no mesmo dia, contra os 11 commits que entraram depois do
baseline da manhã (`07e0725` → `3fbe371`, 23 arquivos, +1.603/−12). Sem nova amostragem da Fase 1
— a de manhã vale para o dia; verificou a sobrevivência das 2 marcações 🟢 aplicadas de manhã e
os 4 fingerprints cujo alvo o delta tocou (**3 ✅ · 0 🟡 · 0 🔴 novos**), e revalidou os 2 abertos
com alvo no delta (**0% de mortalidade**). O delta trouxe 3 mudanças de comportamento e as 3 têm
defeito verificado — todos os gates automáticos seguem verdes e nenhum cobre esta classe.
Ver [o relatório do pass](2026-08-12/index.md).

### Fluxos e Comandos (`auto-*`, `flow-*`, `docs-sync-*`) — 4

- `auto-full-suite-guard-sed-absorbs-sibling-json-keys` — **MEDIUM-HIGH** — alvo: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` — Captura gulosa do `sed` (linha 22) absorve `description` e demais chaves irmãs do payload; prosa contendo `.test.`/`.spec.`/`--filter` desliga o nudge silenciosamente — reproduzido com dois payloads de comando idêntico — [report](2026-08-12/03-fluxos-e-comandos.md)
- `flow-learn-run-marker-records-commit-time-not-run-time` — **MEDIUM-HIGH** — alvo: `commands/learn.md` — O marcador `.learn-last-run` grava `git log -1 --format=%ct` (commit timestamp do HEAD) e é escrito antes do auto-commit do Step 5; a condição de skip de `commands/commit.md:17` é inalcançável e a economia de contexto que justifica `4734882` não se materializa — [report](2026-08-12/03-fluxos-e-comandos.md)
- `auto-install-heredoc-omits-auto-learn-before-commit` — **MEDIUM-HIGH** — alvo: `scripts/install.sh` — O heredoc de fallback sem `python3` (linhas 1022-1025) não recebeu a chave que `4734882` adicionou ao canônico, apesar de o commit ter tocado o arquivo e de o aviso "the two drifted once already" estar na linha 1003; segunda ocorrência da mesma drift, sem gate — [report](2026-08-12/03-fluxos-e-comandos.md)
- `docs-sync-02c-comment-cites-graphify-hint-as-sed-precedent` — **LOW-MEDIUM** — alvo: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` — O comentário da linha 18 invoca `02-graphify-hint.sh` como precedente de "pure-bash approach on the hot path", enquanto aquele arquivo (linha 11) documenta ter evitado `grep|sed` justamente para poupar 2 forks — [report](2026-08-12/03-fluxos-e-comandos.md)

### Referências e Consistência (`gov-*`) — 1

- `gov-repo-gitignore-omits-three-installer-written-entries` — **MEDIUM** — alvo: `.gitignore` — O repo dogfooda a instalação mas seu `.gitignore` tem 1 das 4 entradas que `install.sh:774-779` escreve e que `agents/setup-assistant.md:153` declara obrigatórias; `.learn-last-run` e `.worktree-session` ficam untracked e não ignorados — [report](2026-08-12/02-referencias-e-consistencia.md)

### Descartados por duplicação

- `CLAUDE.md` File Structure não lista `docs/prompts/` (criado hoje por `d10d541`) — Porta 3 (semântica): alvo, causa raiz e remediação coincidem com 3 fingerprints ✅ Executed da família `ref-claude-md-file-structure-*`
- Economia de tokens da guarda de sessão que não dispara — Porta 3: mesmo alvo, causa e remediação de `flow-learn-run-marker-records-commit-time-not-run-time`
- `install.sh` com 1086 linhas · sem registro de `commit-msg` hook — Porta 5 (estado): pertencem ao conjunto aberto
- Hits de stack em `commands/commit.md:135-138` (npm/phpcs) e `agents/setup-assistant.md:146-147` (jest/pytest/phpunit) — Eixo A, regra de descarte: tabelas de detecção e listas de sinais

---

## 2026-08-14 — Auditoria guardiã (verificação + 5 eixos)

Pass guardião contra um delta pequeno (16 arquivos, 4 commits de código desde `3fbe371`). Verificou
**49 das 124** marcações ✅/⚠️ — todos os HIGH e MEDIUM-HIGH mais amostra sistemática de 30% do resto
— com **6,1% de reabertura** (3 🔴 · 4 🟡), abaixo do limiar de escalonamento; revalidou os 25 achados
abertos com **0% de mortalidade** e quatro degradações materiais de medição. A hipótese do pass
anterior se confirmou pela segunda vez: **3 dos 4 commits do delta carregam defeito reproduzido** e
nenhum gate automático cobre essa classe. Produziu **26 achados originais** (5 HIGH). Ver
[o relatório do pass](2026-08-14/index.md) para método, placar e descartados por duplicação.

### Agnosticismo de Stack (`flow-*`, `agent-*`) — 3

- `flow-audit-step2-unconditional-docker-stack-ignores-isolate-pref-compose-gate` — **MEDIUM-HIGH** — alvo: `commands/audit.md` — O Step 2 manda subir stack Docker isolado incondicionalmente (`:54`), contrariando os dois gates do skill (`worktree_docker_isolate` + compose presente) e sobrepondo preferência do usuário — [report](2026-08-14/01-agnosticismo-de-stack.md)
- `flow-mobile-command-spawn-line-enumerates-stacks-dropped-from-agent-description` — **MEDIUM** — alvo: `commands/mobile.md` — A linha de spawn da Fase 1 (`:19`) ainda enumera "React Native, Expo, Flutter, native iOS/Android", as cinco stacks já removidas do frontmatter do `mobile-developer` — [report](2026-08-14/01-agnosticismo-de-stack.md)
- `agent-database-specialist-access-inlines-supabase-cli-while-delegating-others` — **LOW-MEDIUM** — alvo: `agents/database-specialist.md` — `## Database Access` diz "CLI patterns are in each engine's per-engine skill" e na sentença seguinte inlina `psql "$SUPABASE_DB_URL"` (`:133`) — [report](2026-08-14/01-agnosticismo-de-stack.md)

### Referências e Consistência (`ref-*`, `docs-sync-*`) — 6

- `ref-docs-agents-md-tier-column-stale-backend-test-specialist-listed-repetitive` — **HIGH** — alvo: `docs/agents.md` — A coluna `Tier` diz `repetitive` para `backend-test-specialist` (real: `backend-exec`, mudado em `1f1c837`) — exatamente a alocação que `CLAUDE.md:87` proíbe por escrito; espelhado no pt-BR — [report](2026-08-14/02-referencias-e-consistencia.md)
- `ref-tool-map-tool-rewrites-loaded-but-never-emitted-by-render-provider` — **HIGH** — alvo: `scripts/lib/render_provider.py` — `renames` é lido em `:742` e usado só como booleano, nunca emitido, enquanto `CLAUDE.md:67` e `docs/providers.md:127` documentam o rewrite como ativo; reproduzido com `AskUserQuestion` saindo 3× intacto no `.opencode/agents/setup-assistant.md` — [report](2026-08-14/02-referencias-e-consistencia.md)
- `ref-02c-guard-make-composer-shapes-have-no-row-in-scoped-test-runner-table` — **MEDIUM-HIGH** — alvo: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` — Os 3 `case` novos de `c03f898` não têm linha na tabela de runners da skill, `TESTPATH=`/`FILTER=` não existem nela, e `SKILL.md:59` declara legítimo o `Makefile` scoped que o guard sinaliza — [report](2026-08-14/02-referencias-e-consistencia.md)
- `docs-sync-changelog-unreleased-omits-full-suite-guard-and-orchestration-deltas` — **MEDIUM** — alvo: `CHANGELOG.md` — `[Unreleased]` registra 1 dos 3 commits de comportamento do delta; `c03f898` e `21fceb4` ficaram fora, contra `.github/pull_request_template.md:21`, sem gate automatizado — [report](2026-08-14/02-referencias-e-consistencia.md)
- `ref-scoped-test-execution-bash-parallelism-section-outside-declared-canonical-scope` — **MEDIUM** — alvo: `skills/shared/scoped-test-execution/SKILL.md` — A seção nova (`:63-65`) trata de paralelismo de chamadas Bash, fora do escopo canônico declarado em `CLAUDE.md:166` e ausente da `description:` que alimenta o índice sempre carregado — [report](2026-08-14/02-referencias-e-consistencia.md)
- `docs-sync-hooks-md-64-full-suite-guard-examples-predate-wrapper-detection` — **LOW-MEDIUM** — alvo: `CLAUDE-md/hooks.md` — A única prosa do guard na árvore de docs exemplifica só runners nomeados; a classe nova (wrappers opacos, maior superfície de falso positivo) não aparece — [report](2026-08-14/02-referencias-e-consistencia.md)

### Fluxos e Comandos (`flow-*`) — 7

- `flow-update-sh-codex-slim-guard-dead-branch-false-strip-claim` — **HIGH** — alvo: `scripts/update.sh` — O guard Codex nunca avalia como falso (`agents/product-analyst.md` e `scripts/` sempre presentes), e o comentário do commit mais a entrada de CHANGELOG afirmam que `strip-tarball.sh` remove o cross-CLI plumbing, enquanto o script documenta o oposto — [report](2026-08-14/03-fluxos-e-comandos.md)
- `flow-02c-composer-fallback-case-ignores-every-scope-qualifier` — **MEDIUM-HIGH** — alvo: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` — Único `case` da função sem qualificador de escopo na exclusão; `composer test tests/Unit/FooTest.php` e `composer test-unit --filter FooTest` disparam o nudge (reproduzido) — [report](2026-08-14/03-fluxos-e-comandos.md)
- `flow-update-sh-provider-reinstall-aborts-on-non-exit-3-failures` — **MEDIUM-HIGH** — alvo: `scripts/update.sh` — O fix espelha só a pré-condição do `exit 3`; `exit 1` por `jq`/`python3`/snippet vazio ainda mata o update sob `set -e` depois do core ter sucedido (reproduzido) — [report](2026-08-14/03-fluxos-e-comandos.md)
- `flow-architect-claude-only-async-tool-names-rendered-verbatim` — **MEDIUM-HIGH** — alvo: `agents/software-architect.md` — `ScheduleWakeup`/`TaskList`/`SendMessage` aparecem como invariante não-negociável, sem hedge e sem entrada em `tool-map.json`; chegam literais ao `.opencode/agents/software-architect.md` renderizado — [report](2026-08-14/03-fluxos-e-comandos.md)
- `flow-02c-make-pattern-substring-matches-cmake-and-chained-cmds` — **MEDIUM** — alvo: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` — `*make\ *test*` casa com `cmake ` e atravessa `&&`; `cmake --build . && ./run_tests` e `make migrate-test-db && phpunit --filter X` disparam (reproduzido) — [report](2026-08-14/03-fluxos-e-comandos.md)
- `flow-prompt-auditoria-commit-step-contradicts-branch-rule` — **MEDIUM** — alvo: `docs/reports/_prompt-auditoria.md` — Bloco copiado do prompt de métricas: diz "two report files" (são 8), manda `push … main` contra a regra inviolável 8 do próprio arquivo, e carrega a mensagem de commit de métricas — [report](2026-08-14/03-fluxos-e-comandos.md)
- `flow-background-process-discipline-monitor-no-availability-fallback` — **LOW-MEDIUM** — alvo: `skills/architecture/orchestration/SKILL.md` — `Monitor` é declarado "única forma legítima" sem a cláusula de indisponibilidade que a check 5, seis linhas acima, carrega — [report](2026-08-14/03-fluxos-e-comandos.md)

### Agentes e Skills (`skill-*`, `agent-*`) — 5

- `skill-token-efficiency-background-mgmt-contradicts-orchestration-discipline` — **HIGH** — alvo: `skills/shared/token-efficiency/strategies.md` — § Background Process Management ensina fire-and-forget e lê shell de background com `TaskOutput(task_id=…)`, contradizendo a § Background Process Discipline criada em `21fceb4`; a versão errada alcança 18/18 agentes, a certa alcança 1 — [report](2026-08-14/04-agentes-e-skills.md)
- `agent-line-cap-205-documented-in-claude-md-vs-211-enforced-by-size-limits` — **HIGH** — alvo: `CLAUDE.md` — `:92` e `:311` dizem "enforces 205 (200+5)"; `helpers/size-limits.sh:44` tem `AGENT_LIMIT=211` desde `705acd1`, que não tocou o `CLAUDE.md` — 3 agentes estão exatamente em 211 — [report](2026-08-14/04-agentes-e-skills.md)
- `agent-software-architect-inlines-spawn-integrity-4-5-no-availability-guard` — **MEDIUM-HIGH** — alvo: `agents/software-architect.md` — A linha 89 (nova em `21fceb4`) reescreve o check 5 inteiro em vez de delegar, e já diverge: manda chamar `ScheduleWakeup` sem o guard de disponibilidade nem o fallback de `orchestration:234-236` — [report](2026-08-14/04-agentes-e-skills.md)
- `skill-orchestration-spawn-integrity-unreachable-from-devteam-commands` — **MEDIUM** — alvo: `commands/*.md` — Zero dos 34 comandos carrega a skill de orquestração (única ocorrência é prosa em `architect.md:22`); os checks 1–5 alcançam 1 das ~16 superfícies que dão spawn — [report](2026-08-14/04-agentes-e-skills.md)
- `skill-orchestration-restates-scoped-test-execution-exception` — **MEDIUM** — alvo: `skills/architecture/orchestration/SKILL.md` — O passo 4 do Autonomous Sprint (`:68-70`) reescreve a exceção que `CLAUDE.md:166` manda nunca reescrever, duplicando o § Orchestrator Rule que já existe em `scoped-test-execution:18-20` — [report](2026-08-14/04-agentes-e-skills.md)

### Economia de Tokens (`token-*`) — 5

- `token-02c-full-suite-guard-substring-match-injects-nudge-on-non-test-commands` — **MEDIUM-HIGH** — alvo: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` — `is_full_suite()` casa substring solta (`*jest*`, `*pytest*`, `*rspec*`) sem âncora de invocação; 6 de 6 payloads de leitura testados no HEAD disparam 405 bytes de `additionalContext` em comandos que não rodam teste — [report](2026-08-14/05-economia-tokens.md)
- `token-pr-md-unbounded-full-diff-to-repetitive-tier-while-same-file-caps-git-log` — **MEDIUM-HIGH** — alvo: `commands/pr.md` — A linha 99 manda derivar o corpo do PR de `git diff base...HEAD` sem filtro, entregue ao `technical-writer` (`repetitive`/Haiku, janela 200K), enquanto a linha 80 do mesmo arquivo limita o `git log` a `head -20` — [report](2026-08-14/05-economia-tokens.md) — 🟢 **Resolved:** 2026-08-21 — resolvido por `8267da1` (`commands/pr.md:99` agora manda usar `git diff ${DEFAULT_BRANCH}...HEAD -- <path>` escopado)
- `token-orchestration-skill-377-lines-138-conditional-path-only-no-references-dir` — **MEDIUM** — alvo: `skills/architecture/orchestration/SKILL.md` — 138 de 377 linhas (42%) só valem em 3 gatilhos raros e são carregadas de saída; 2ª maior skill do repo sem `references/`, e o +20 de `21fceb4` caiu inteiro nesse bloco — [report](2026-08-14/05-economia-tokens.md)
- `token-model-identity-32-of-58-lines-are-format-spec-and-examples-held-inline` — **MEDIUM** — alvo: `skills/shared/model-identity/SKILL.md` — 32 de 58 linhas são spec de colunas e 3 exemplos de outros agentes, numa skill carregada "antes de qualquer outra ação" por 18 agentes, só para copiar verbatim um bloco que o agente já tem inline — [report](2026-08-14/05-economia-tokens.md)
- `token-project-context-restates-scoped-test-exception-table-read-by-18-agents` — **MEDIUM** — alvo: `skills/shared/project-context/SKILL.md` — Tabela de 6 linhas reafirma "The Only Exception" da skill, e a linha 216 admite "Do not work from this table alone"; 17 linhas lidas por 18 de 18 agentes, 11 dos quais sem carga própria da skill — [report](2026-08-14/05-economia-tokens.md)

### Descartados por duplicação

**Cross-axis, consolidados na etapa de banco (porta 3 — 3 de 3 atributos coincidem):**

- (Eixo C) `flow-02c-wrappers-have-no-scoped-row-in-runner-filters-table` → absorvido por `ref-02c-guard-make-composer-shapes-have-no-row-in-scoped-test-runner-table`
- (Eixo C) `flow-parallel-bash-rule-homed-in-scoped-test-execution-skill` → absorvido por `ref-scoped-test-execution-bash-parallelism-section-outside-declared-canonical-scope`
- (Eixo D) `skill-scoped-test-execution-hosts-general-parallel-bash-rule-off-topic` → idem

**Por porta:**

- Porta 5 (estado — conjunto aberto): `sed` guloso do `02c`, comentário graphify-precedent, `session-start.sh` monolítico, `install.sh` não fragmentado, `CLAUDE.md` monolito, `interaction-patterns`, `migration-v1-to-v2`, `relayout.md:32` Storybook/Tailwind, `frontend-test-specialist.md:139-151`, `frontend-developer.md:3`, `devops-specialist.md:46-56`, `audit.md:126-128`, `commit.md:135-138`, `setup-assistant.md:146-147`, `skill-adr-coverage-only-architect`
- Porta 3 (semântica): rotação do CHANGELOG, "agent-lint não valida coluna Tier", `update.sh` sem integrity check, `orchestration/SKILL.md` sem `references/`, `software-architect.md` no teto de 211, `token-efficiency` 160×18, `devops.md:2,14`, `frontend-reviewer.md:112,114`, `database-specialist.md:66-73`
- Porta 4 (escopo menor, sem sub-escopo novo): `devops-specialist.md:137-148`, `output-format` 190×9
- Porta 1 (literal): `backlog-template` 238 linhas, bloco Docker eager de `project-context`
- **Hipóteses refutadas por evidência:** JSON concatenado de dois sub-scripts PreToolUse (Glob/Grep e Bash são exclusivos); dispatcher sem allowlist (`SUBSCRIPT_RE` existe nos dois); divergência de redação do `## Before You Finish` (as 18 seções são byte-idênticas); divergência de run-banner vs. `tiers.json`/`agent_effort` (18/18 batem, incluindo os cinco `low`)
- **Falsos positivos por substring no Eixo A** (~24 de 122 candidatos): `flaws`→aws, `expression`→express, `honest`→nest, `perspective`→rspec, `pipeline`→pip, `Auto-reactivation`→react, `explicit bootstrap`→bootstrap

---

## 2026-08-21 — Auditoria guardiã (verificação + 5 eixos)

Baseline `HEAD` = `a67cac9` · baseline anterior `c03f898` · delta de **39 arquivos de código** em
**33 commits**. Fase 1: **48 de 119 verificados** (todos HIGH/MEDIUM-HIGH + 30% do resto) →
43 ✅ · 3 🟡 · 2 🔴 (**90% confirmado, 4,2% reaberto**). Fase 1b: **2,4% de mortalidade** (1 de 42).
**37 achados originais.** Ver [o relatório do pass](2026-08-21/index.md).

### Agnosticismo de Stack (`agent-*`) — 4

- `agent-security-specialist-cicd-checklist-github-actions-only-vocabulary` — **MEDIUM-HIGH** — alvo: `agents/security-specialist.md` — `### CI/CD Pipeline Security` codifica 6 itens em vocabulário exclusivo do GitHub Actions (`${{ github.event.* }}`, `pull_request_target`, self-hosted runners) enquanto `:29` manda ler `.gitlab-ci.yml`/`bitbucket-pipelines.yml` e o harness embarca 4 skills `cicd-*` — [report](2026-08-21/01-agnosticismo-de-stack.md)
- `agent-database-specialist-rls-as-engine-neutral-multitenant-default-and-gate` — **MEDIUM-HIGH** — alvo: `agents/database-specialist.md` — `:84` põe RLS como primeiro degrau da cascata de multi-tenancy em `## Schema Design Principles` e `:154` transforma isso em item de "done" sem ressalva de engine, num roster de 9 engines em que mysql/mongodb/redis/sqlite/cassandra não têm RLS — [report](2026-08-21/01-agnosticismo-de-stack.md)
- `agent-reviewer-linter-config-three-divergent-ecosystem-incomplete-copies` — **MEDIUM** — alvo: `agents/backend-reviewer.md` — o passo "leia os configs de linter" tem 3 cópias divergentes (`reviewer-base:11` com 5 arquivos, `backend-reviewer:30` com 4 e sem `.eslintrc*`, `frontend-reviewer:31` com um conjunto JS-only diferente), violando Canonical Rule Homes — [report](2026-08-21/01-agnosticismo-de-stack.md)
- `agent-frontend-developer-testability-presumes-reactive-component-model` — **MEDIUM** — alvo: `agents/frontend-developer.md` — `## Testability` (`:145-147`) pressupõe componente reativo ("prefer reactive state", "smart/dumb component pattern") contra o escopo server-rendered da própria `description:` e o roteamento jQuery de `:72`, ignorando o `## Client Rendering Model` que o harness já formaliza — [report](2026-08-21/01-agnosticismo-de-stack.md)

### Referências e Consistência (`ref-*`, `auto-*`, `docs-sync-*`) — 5

- `auto-size-limits-claude-md-warning-counted-as-violation-turns-ci-lint-red` — **HIGH** — alvo: `helpers/size-limits.sh` — `:92` empurra o *warning threshold* do `CLAUDE.md` (600) no mesmo array `VIOLATIONS` do limite de falha (700), e `:98`/`:122` derivam o exit code só desse array — `bash .github/scripts/ci/01-lint.sh` sai **1** no HEAD (step `blocking` em `01-lint.sh:88`), com `CLAUDE.md` em 602 linhas desde `7e62124` — [report](2026-08-21/02-referencias-e-consistencia.md)
- `ref-check-updates-shim-and-update-sh-exec-renamed-away-01-check-updates-hook` — **HIGH** — alvo: `scripts/check-updates.sh` — `:3` e `scripts/update.sh:24` fazem `exec` de `hooks/pre-tool-use/01-check-updates.sh`, que virou `_disabled-01-check-updates.sh`; `commands/update.md:82` chama o shim e trata ausência de stdout como "Up to date", então `/devteam:update` reporta atualizado num projeto desatualizado — [report](2026-08-21/02-referencias-e-consistencia.md)
- `ref-notifier-documented-as-live-in-four-docs-while-hook-file-is-disabled` — **HIGH** — alvo: `skills/shared/notifier/SKILL.md` — `:52`, `:60` e `:102` descrevem `stop/04-notifier.sh` disparando "After each turn" e incrementando `.notifier-state`; o arquivo é `_disabled-04-notifier.sh` e nenhum hook toca esse contador — skill shipped e alcançada por todo agente via `project-context/SKILL.md:61` — [report](2026-08-21/02-referencias-e-consistencia.md)
- `docs-sync-readme-command-table-omits-devteam-install-in-both-languages` — **MEDIUM** — alvo: `README.md` — tabela de comandos lista 34 de 35; `/devteam:install` não aparece em `README.md`, `README.pt-BR.md` nem em `docs/*.md`, apesar de `CLAUDE.md:248` chamá-lo de "single entrypoint for tool installs" — o gate `02-readme-sync.sh` compara EN↔pt-BR, não a árvore — [report](2026-08-21/02-referencias-e-consistencia.md)
- `ref-three-pointers-to-claude-md-hook-subscript-convention-moved-to-hooks-md` — **MEDIUM** — alvo: `CLAUDE-md/notifications.md` — `:65`, `scripts/hooks/stop.sh:53` e `scripts/hooks/pre-tool-use.sh:17` apontam para uma seção "Hook Sub-script Convention" do `CLAUDE.md` que não existe mais; as seções vivem em `CLAUDE-md/hooks.md:21,48`, e os dois dispatchers shipam para projetos onde `CLAUDE-md/` nem é instalado — [report](2026-08-21/02-referencias-e-consistencia.md)

### Fluxos e Comandos (`flow-*`, `docs-sync-*`) — 14

- `flow-pre-tool-use-dispatcher-sigpipe-141-masks-02c-block` — **HIGH** — alvo: `scripts/hooks/pre-tool-use.sh` — O dispatcher entrega o payload por pipe e `02-graphify-hint.sh:14` sai antes de consumir stdin; payload >64KB gera SIGPIPE → `pipefail` → exit 141, e a regra "primeiro não-zero vence" (`:33-35`) sobrescreve o `exit 2` bloqueante do `02c`, que falha aberto — [report](2026-08-21/03-fluxos-e-comandos.md)
- `flow-merge-md-branch-and-tree-resolved-before-worktree-detection` — **HIGH** — alvo: `commands/merge.md` — Steps 0/1 rodam `git status`/`git branch --show-current` sem `-C` e sem `--git-common-dir` antes do Step 2 ler `.worktree-session`; da árvore principal o comando aborta em `:34` ("nothing to merge"), de dentro do worktree o arquivo de sessão é invisível — o caminho worktree é inalcançável — [report](2026-08-21/03-fluxos-e-comandos.md)
- `flow-learn-nudge-ancestor-test-inverted-in-four-commands` — **HIGH** — alvo: `commands/merge.md` — "recorded commit hash is **not an ancestor** of the current HEAD (i.e. commits landed since the last learn run)" afirma como equivalentes condições opostas; com commits desde o learn o hash **é** ancestral e o nudge nunca dispara; replicado em `merge.md:89`, `pr.md:148`, `refactor.md:162` e referenciado por `audit.md:188` — [report](2026-08-21/03-fluxos-e-comandos.md)
- `flow-02c-escape-hatch-anchored-while-detection-is-substring` — **MEDIUM-HIGH** — alvo: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` — A detecção casa substring em qualquer posição mas a escotilha (`:41-43`) exige `DEVTEAM_FULL_SUITE_CONFIRMED=1` na posição 0; `cd frontend && DEVTEAM_FULL_SUITE_CONFIRMED=1 npm test` e o wrapper `sh -c "..."` que o próprio arquivo cita são bloqueados sem saída viável — [report](2026-08-21/03-fluxos-e-comandos.md)
- `docs-sync-auto-learn-before-commit-still-documented-as-pre-commit-step-0` — **MEDIUM-HIGH** — alvo: `CLAUDE-md/preferences.md` — `:55` e `skills/shared/user-preferences/SKILL.md:70` descrevem "`/devteam:commit` Step 0 auto-runs `/devteam:learn` before committing" depois de `576dcfa` mover a captura para o Step 6, pós-commit; o nome da chave em `preferences-defaults.json:18` também diz o contrário do comportamento — [report](2026-08-21/03-fluxos-e-comandos.md)
- `flow-claude-md-no-agent-command-list-says-seven-omits-push-and-merge` — **MEDIUM-HIGH** — alvo: `CLAUDE.md` — `:258` enumera sete comandos sem agente e diz "All seven name technical-writer", enquanto `scripts/lib/commands.json:7` (`_filler_agent_note`) lista nove incluindo `push` e `merge`; `b0383d6` atualizou o JSON e a lista de plan gate mas não o parágrafo — [report](2026-08-21/03-fluxos-e-comandos.md)
- `flow-merge-md-rebases-onto-target-while-delegating-to-base-step-8` — **MEDIUM** — alvo: `commands/merge.md` — `:57` rotula a opção recomendada como "rebase onto `<target>`" e manda "delegate entirely" ao passo 8 do worktree skill, que faz "rebase onto **base**" (`SKILL.md:55`); `target` vem de quiz e `base` de `worktree_base_branch`, sem nada que resolva a divergência no único caminho destrutivo — [report](2026-08-21/03-fluxos-e-comandos.md)
- `flow-learn-nudge-has-no-canonical-skill-home-three-inline-copies` — **MEDIUM** — alvo: `CLAUDE.md` — A Learn Trigger Rule designa um **corpo de comando** (`commands/merge.md` § Step 4) como casa canônica, contra a doutrina "lives in exactly one skill"; `pr.md` e `refactor.md` carregam cópias inline e `audit.md:188` referencia "merge.md", caminho que não resolve em projeto instalado nem no Codex — [report](2026-08-21/03-fluxos-e-comandos.md)
- `flow-fix-md-only-implementation-command-without-review-qa-handoff` — **MEDIUM** — alvo: `commands/fix.md` — Zero ocorrências de `code-reviewer`/`qa-specialist` nas 42 linhas, enquanto `backend.md`, `frontend.md`, `fullstack.md`, `mobile.md` e `refactor.md` terminam todos em review+QA obrigatórios; com `TESTS_REQUIRED=no` o comando não tem nenhum gate após a alteração — [report](2026-08-21/03-fluxos-e-comandos.md)
- `flow-pr-md-default-branch-falls-back-to-global-config-then-literal-main` — **MEDIUM** — alvo: `commands/pr.md` — `:60-63` prefere `git config init.defaultBranch` (preferência global da máquina) ao `git remote show origin` e termina em `|| echo "main"`, literal proibido por `merge.md:32` e `worktree/SKILL.md:109`; alimenta `git log/diff ${DEFAULT_BRANCH}..HEAD` e a base do PR — [report](2026-08-21/03-fluxos-e-comandos.md)
- `flow-merge-md-merge-only-option-cites-undefined-follow-up-choice` — **LOW-MEDIUM** — alvo: `commands/merge.md` — `:59` manda rodar o merge "from whichever of the two paths above was implied by a follow-up choice", follow-up que o comando nunca define; a ambiguidade fica entre teardown do worktree e preservação dele — [report](2026-08-21/03-fluxos-e-comandos.md)
- `docs-sync-session-start-comment-cites-nonexistent-02b-full-suite-guard` — **LOW-MEDIUM** — alvo: `scripts/hooks/session-start.sh` — `:175` aponta `pre-tool-use/02b-full-suite-guard.sh` como rede de segurança complementar; o arquivo é `02c-full-suite-guard.sh` e `02b-` é `02b-telemetry.sh` — único ponteiro do arquivo para a guarda que `abb8483` tornou bloqueante — [report](2026-08-21/03-fluxos-e-comandos.md)
- `docs-sync-touched-paths-lib-header-says-stop-only-after-02c-sources-it` — **LOW-MEDIUM** — alvo: `scripts/hooks/lib/touched-paths.sh` — `:2` e `:12` declaram consumo exclusivo por `stop.sh` depois que `02c-full-suite-guard.sh:15-17` passou a fazer `source`; o cabeçalho também é o contrato de cache `DEVTEAM_TOUCHED_PATHS`, que o caminho PreToolUse não tem — cada detecção forka `git status`+`git log` — [report](2026-08-21/03-fluxos-e-comandos.md)
- `flow-merge-md-arguments-target-branch-parse-can-swallow-no-teardown-flag` — **LOW** — alvo: `commands/merge.md` — `:35` trata `$ARGUMENTS` como nome de branch sem remover flags antes; `/devteam:merge --no-teardown` sem alvo deixa a flag como única string candidata, enquanto `pr.md:25-28` mostra o padrão correto — [report](2026-08-21/03-fluxos-e-comandos.md)

### Agentes e Skills (`skill-*`, `agent-*`) — 8

- `skill-orchestration-two-sections-both-numbered-check-5-breaks-cross-refs` — **HIGH** — alvo: `skills/architecture/orchestration/SKILL.md` — `a3e6095` criou um segundo `### 5.` (`:245`) ao lado do existente (`:213`); as três refs a "check 5" (`:270`, `software-architect.md:89`, `CLAUDE.md:172`) passam a resolver para seções opostas, e o único caminho de carga de `work-feedback` aponta para a errada — [report](2026-08-21/04-agentes-e-skills.md)
- `agent-qa-specialist-browser-foreground-rule-unsatisfiable-always-spawned` — **MEDIUM-HIGH** — alvo: `agents/qa-specialist.md` — `:85` exige rodar testes de browser "in the main/foreground agent, never delegated to a background subagent", mas `commands/qa.md:10` e mais 6 comandos spawnam `qa-specialist` via Task sem exceção — regra na camada errada, impossível de cumprir — [report](2026-08-21/04-agentes-e-skills.md)
- `skill-work-feedback-wakeup-cadence-cap-output-conflict-auto-reactivation` — **MEDIUM-HIGH** — alvo: `skills/shared/work-feedback/SKILL.md` — mesmo gatilho e mesma ferramenta que o check Auto-reactivation, com `delaySeconds` (300 vs 1200–1800), teto (nenhum vs 2) e conteúdo do turno ("only the table" vs blocker) divergentes, sem regra de precedência — [report](2026-08-21/04-agentes-e-skills.md)
- `agent-qa-specialist-in-app-browser-prefix-mcp-claude-browser-nonexistent` — **MEDIUM-HIGH** — alvo: `agents/qa-specialist.md` — `:79` detecta o browser in-app por `mcp__Claude_Browser__*`, namespace inexistente (o real é `mcp__claude-in-chrome__*`); o passo 1 "no need to ask" é sempre falso e o agente sempre pergunta — [report](2026-08-21/04-agentes-e-skills.md)
- `agent-unit-test-isolation-rule-mirrored-five-agents-no-canonical-home` — **MEDIUM** — alvo: `agents/backend-test-specialist.md` — `9a64920` parafraseou a Hard rule em 5 agentes sem linha na tabela Canonical Rule Homes; as variantes de frontend atribuem `localStorage`/`IndexedDB`/cookies a `test-pyramid:44`, que não menciona storage de browser — [report](2026-08-21/04-agentes-e-skills.md)
- `skill-orchestration-preamble-says-three-checks-but-section-has-five` — **MEDIUM** — alvo: `skills/architecture/orchestration/SKILL.md` — `:152` declara "Three checks, in order, around every delegation round" numa seção com cabeçalhos 1–5; quem confiar no preâmbulo pula Liveness, Auto-reactivation e a tabela periódica — [report](2026-08-21/04-agentes-e-skills.md)
- `skill-work-feedback-description-names-credentials-json-not-local-variant` — **LOW-MEDIUM** — alvo: `skills/shared/work-feedback/SKILL.md` — `:3` nomeia `credentials.json` no índice de skills sempre carregado; é a única ocorrência dessa string no repo, o arquivo real é `credentials.local.json` (usado no corpo da própria skill em `:14`) — [report](2026-08-21/04-agentes-e-skills.md)
- `agent-three-at-exactly-211-line-ceiling-zero-headroom-for-additions` — **LOW** — alvo: `agents/software-architect.md` — 3 de 18 agentes no valor exato do teto e mais 5 a ≤3 linhas; qualquer acréscimo de uma linha falha o gate do `Stop`/CI, e corpos de agente não têm `references/` como saída — [report](2026-08-21/04-agentes-e-skills.md)

### Economia de Tokens (`token-*`) — 6

- `token-graphify-hint-3-git-forks-before-marker-early-exit-on-every-tool-call` — **MEDIUM-HIGH** — alvo: `scripts/hooks/pre-tool-use/02-graphify-hint.sh` — O bloco de resolução do marcador (`:16-20`) foi inserido acima do `case` de tool-name e do próprio `[ -f "$MARKER" ]`, então todo tool call num projeto com `graph.json` paga 3 forks antes de qualquer filtro — 13,4 ms/chamada medidos, contra 0 fork antes do delta — [report](2026-08-21/05-economia-tokens.md)
- `token-two-schedulewakeup-poll-loops-same-spawn-round-300s-vs-1200-1800s` — **MEDIUM-HIGH** — alvo: `skills/shared/work-feedback/SKILL.md` — Duas seções ambas numeradas `### 5.` agendam `ScheduleWakeup` e chamam `TaskList` na mesma rodada de background, com cadências de 1200–1800 s e 300 s; o laço de 300 s é o default ligado e o único sem teto — ≈12 acordadas/hora contra as 2 previstas, ≈3–5K tokens/hora — [report](2026-08-21/05-economia-tokens.md)
- `token-output-format-third-copy-of-plan-format-42-lines-nine-load-sites` — **MEDIUM** — alvo: `skills/shared/output-format/SKILL.md` — `:144-185` guarda uma terceira cópia do formato de plano (42 linhas) que o fix de `gov-plan-template-vs-skill-duplication` não tocou, já divergente no sentinela da coluna `Par.`, carregada inteira por 7 agentes + 2 comandos que nunca emitem plano — **Refina:** `gov-plan-template-vs-skill-duplication` — [report](2026-08-21/05-economia-tokens.md)
- `token-install-sh-second-unconditional-claude-md-injection-35-lines-every-session` — **MEDIUM** — alvo: `scripts/install.sh` — O Step 8b (`:862-886`) anexa um segundo bloco gerenciado ao `CLAUDE.md` do projeto-alvo; somado ao Step 8 são 35 linhas / ~1,97 KB lidas em 100% das sessões de todo projeto instalado, com 2 das 4 regras restatando `conventional-commits/SKILL.md` e sem gate que compare as duas cópias — [report](2026-08-21/05-economia-tokens.md)
- `token-work-feedback-opt-out-gate-lives-inside-the-71-line-skill-it-gates` — **LOW-MEDIUM** — alvo: `skills/shared/work-feedback/SKILL.md` — As 71 linhas são carregadas antes de `:14` mandar ler `credentials.local.json` para descobrir se a skill deve ser ignorada; `CLAUDE.md:172` e `orchestration:249` proíbem mover o teste booleano para o chamador, invertendo o padrão de gatilho-no-chamador já usado por `project-context` — [report](2026-08-21/05-economia-tokens.md)
- `token-pr-md-14-line-verbatim-learn-nudge-while-audit-md-delegates-in-one-line` — **LOW-MEDIUM** — alvo: `commands/pr.md` — `:140-152` é cópia verbatim de `commands/merge.md:81-93` (14 linhas / 718 bytes) enquanto `commands/audit.md:188` resolve o mesmo nudge em uma linha; quatro variantes do mecanismo na mesma janela — [report](2026-08-21/05-economia-tokens.md)

### Descartados por duplicação

**Porta 5 (estado — já no conjunto aberto):** `frontend-developer.md:3` frameworks na frontmatter · `frontend-test-specialist.md:141-153` SonarQube · `devops-specialist.md:46-56` Docker primário · `database-specialist.md:133` Supabase CLI · `audit.md:54` e `:126,128` Docker/Redis/CDN · `relayout.md:32` Storybook/Tailwind · `mobile.md:19,26,27` stacks · `setup-assistant.md:146-147` · `commit.md:125-133` · `CLAUDE.md:92,313` teto 205 vs 211 · `_index.md:103` legenda "All 131 entries" · `CLAUDE.md` 602 linhas monolítico · `interaction-patterns` 209×32 · `orchestration` 391 linhas sem `references/` · `project-context` tabela de escopo de testes · `pr.md:99` diff completo · `02c` casamento de substring · `token-efficiency` 160×18 · `work-feedback` inalcançável pelos comandos · `learn.md:166` marcador com SHA defasado.

**Porta 3 (semântica — 2 ou 3 de 3 atributos coincidem):** `frontend-developer.md:91,96` data fetching · `:72` skill jQuery · `frontend-reviewer.md:112,114` React/TS · `database-specialist.md:66-73` engines na frontmatter · `security-specialist.md` § Tooling SAST · `devops.md:2,14` · cargas duplicadas de `test-pyramid` e de `worktree/SKILL.md` reportadas pelo `orphan-skill-scan` (verificadas como **falsos positivos do scanner** — a segunda ocorrência é citação de regra, não um segundo load) · `CLAUDE.md:300` File Structure lista 3 de 5 templates · `CLAUDE-md/notifications.md:66-76` tabela de sub-scripts defasada · `pr.md:43` segunda cópia da ordenação em camadas · `install.sh` 1240 linhas sem decomposição.

**Porta 4 (escopo menor sem sub-escopo novo):** `output-format` 203 linhas × 9 sítios (retorna apenas como o sub-escopo § Plan Template) · `02c` sem pré-cômputo de touched paths (absorvido no achado do cabeçalho da lib).

**Porta 1 (literal):** `new-adr.sh:58` quebra com `&` no título — slug já registrado e marcado ✅, reabertura é matéria da fase de verificação.

**Falsos positivos por substring no Eixo A** (~11 de 124 candidatos): `pip`→"pipeline", `express`→"expressed", `react`→"Auto-reactivation", "Python Prerequisite" (pré-requisito do próprio harness).

---

## 2026-08-28 — Auditoria guardiã (verificação + 5 eixos)

Pass sobre `HEAD` = `a67cac9` — **o mesmo sha do baseline anterior**. Zero commits desde 2026-08-21;
os relatórios e as 37 fingerprints daquele pass estavam **não commitados** na árvore de trabalho. O
achado principal é sobre o próprio ciclo de auditoria. Ver [o relatório do pass](2026-08-28/index.md).

### Governança e automação (`gov-*`, `auto-*`) — 4

- `gov-audit-pass-output-uncommitted-with-no-detection-mechanism` — **HIGH** — alvo: `docs/reports/_prompt-auditoria.md` — Os sete relatórios e as 37 fingerprints do pass de 2026-08-21 nunca chegaram ao remoto (`git show HEAD:docs/reports/_index.md` = 176 entradas vs. 213 na árvore); o bloco de commit/push de `:336-366` não registra que rodou e nenhum hook verifica que `docs/reports/` foi commitado — o pass seguinte redescobriria os 37 — [report](2026-08-28/03-fluxos-e-comandos.md)
- `auto-agent-lint-quiz-first-never-scans-commands-dir` — **HIGH** — alvo: `helpers/agent-lint.sh` — `CLAUDE.md:210` declara a Quiz-first Rule dos 35 comandos imposta por `agent-lint.sh`, mas o único laço que chama `check_quiz_first` é `for agent_file in agents/*.md` (`:478-481`); reproduzido: `(yes/no)` injetado em `commands/qa.md` retorna `agent-lint: clean ✓` — [report](2026-08-28/03-fluxos-e-comandos.md)
- `auto-adr-gap-check-dependency-signal-blind-to-staged-and-committed-changes` — **MEDIUM-HIGH** — alvo: `scripts/hooks/stop/03e-adr-gap-check.sh` — `:32` usa `git diff` sem `--cached` e sem range, então o sinal de nova dependência morre assim que o arquivo é staged ou commitado, enquanto migration e provider-config (`:40`) disparam sobre conteúdo commitado; reproduzido em repo sintético (4 casos) — [report](2026-08-28/03-fluxos-e-comandos.md)
- `auto-slim-bootstrap-shape-contract-cannot-fail-the-build` — **MEDIUM-HIGH** — alvo: `.github/scripts/ci/slim-bootstrap.sh` — `:96` é `[ "$fail" -eq 0 ] && echo …` e `$fail` nunca é lido depois; as três asserções da seção 2 imprimem FAIL em stderr e o script sai 0, deixando os 15 arquivos de `SLIM_KEEP_LIST` sem gate — [report](2026-08-28/03-fluxos-e-comandos.md)

### Fluxos e comandos (`flow-*`) — 3

- `flow-review-command-writes-and-commits-while-documented-as-read-only` — **HIGH** — alvo: `commands/review.md` — `:66` manda editar arquivos e criar commits no contexto principal, contra `:35` do mesmo arquivo ("Do NOT review inline — always delegate") e contra `CLAUDE.md:254`, que classifica o comando como "read-only by design" e usa isso como razão para não ter Plan Gate — [report](2026-08-28/03-fluxos-e-comandos.md)
- `flow-question-tool-name-in-four-implementation-command-findings-gates` — **MEDIUM-HIGH** — alvo: `commands/backend.md` (+ `frontend.md`, `fullstack.md`, `mobile.md`) — `:66` manda usar a ferramenta `question`, nome nativo do opencode, no gate de resolução de findings; Claude recebe o corpo verbatim e a ferramenta não existe lá, enquanto `:6` do mesmo arquivo exige `AskUserQuestion` — [report](2026-08-28/03-fluxos-e-comandos.md)
- `flow-rule-and-sync-rules-listed-as-technical-writer-but-never-delegate` — **MEDIUM** — alvo: `CLAUDE.md` — `:240-241` nomeiam `technical-writer` na coluna "Agents invoked", mas `grep -c "Task tool"` retorna 0 nos dois corpos, e a `_filler_agent_note` de `commands.json:7` enumera nove linhas-filler sem incluir essas duas — [report](2026-08-28/03-fluxos-e-comandos.md)

### Referências e consistência (`ref-*`, `docs-sync-*`) — 6

- `docs-sync-claude-md-effort-key-scope-vs-agent-effort-map` — **HIGH** — alvo: `CLAUDE.md` — `:64` afirma que `effort:` existe "only" em agentes do tier `repetitive` e `:73-74` declaram `none` para `backend-exec`/`frontend`, mas 5 agentes desses dois tiers carregam `effort: low` via `agent_effort`; seguir `:64` literalmente rebaixa o esforço de todo o time de execução — [report](2026-08-28/02-referencias-e-consistencia.md)
- `docs-sync-docs-agents-md-worktree-asks-once-vs-preference-default` — **MEDIUM-HIGH** — alvo: `docs/agents.md` — `:55` (espelhado em `agents.pt-BR.md:55`) diz que `backend-developer` "asks once whether to isolate work in a git worktree", mas com o default `worktree_active: true` a cascata cria o worktree sem perguntar; o gate `02-readme-sync.sh` compara estrutura e passa verde com o defeito espelhado — [report](2026-08-28/02-referencias-e-consistencia.md)
- `ref-command-description-duplicated-frontmatter-vs-commands-json` — **MEDIUM** — alvo: `scripts/lib/commands.json` — O `description` de cada comando tem dois donos (frontmatter para Claude, `commands.json` para opencode/Codex) e as **35** já divergem; `check_command_roster` valida `tier`/`agent`/`model:` e não o campo, e só o `commands.json` menciona o argumento de branch do `/devteam:status` — [report](2026-08-28/02-referencias-e-consistencia.md)
- `docs-sync-claude-md-coding-agents-list-omits-seo-specialist` — **MEDIUM** — alvo: `CLAUDE.md` — `:109` enuncia como fechada uma lista de oito coding agents ("all eight agents"), mas `grep -c "^## Worktree Isolation" agents/*.md` retorna nove; `seo-specialist` entrou em `1b5bb08` e a lista não é tocada desde 2026-05-04, e nenhum lint a valida — [report](2026-08-28/02-referencias-e-consistencia.md)
- `docs-sync-claude-md-context-list-item-count-12-vs-11` — **LOW-MEDIUM** — alvo: `CLAUDE.md` — `:158` chama a Context Loading Order de "12 items"; ela tem 11 hoje e tinha 10 em `7736e20`, o commit que introduziu o número — o único fato verificável da tabela *Canonical Rule Homes* nunca esteve correto — [report](2026-08-28/02-referencias-e-consistencia.md)
- `docs-sync-readme-ptbr-agents-link-points-to-english-doc` — **LOW** — alvo: `README.pt-BR.md` — `:141` linka `docs/agents.md` enquanto `:15` linka `docs/agents.pt-BR.md`; o `02-readme-sync.sh` compara contagem de links por seção, não alvo, então um link idêntico ao do EN é indistinguível de tradução correta — [report](2026-08-28/02-referencias-e-consistencia.md)

### Agentes e skills (`agent-*`, `skill-*`) — 5

- `agent-worktree-cascade-delegates-to-unshipped-claude-md` — **HIGH** — alvo: `agents/mobile-developer.md` (+ 8 coding agents) — Os 9 agentes que editam arquivos apontam para `CLAUDE.md` → "Worktree Isolation", rótulo inexistente (`:111` chama a seção de outro nome) num arquivo que `KEEP_ROOT` (`install.sh:369`) remove do pacote; e `mobile-developer:39`/`devops-specialist:40` proíbem carregar a skill no ramo `worktree=no`, o único que precisa do formato de escrita do arquivo de sessão — [report](2026-08-28/04-agentes-e-skills.md)
- `skill-spec-gate-scope-lock-hard-gate-unreachable-by-execution-agents` — **MEDIUM-HIGH** — alvo: `skills/shared/spec-gate/SKILL.md` — `:54-55` nomeia quatro coding agents e `:65-70` define o `<HARD-GATE>` que proíbe encerrar com suposição aberta, mas `grep -ln spec-gate agents/*.md` devolve só product-analyst, qa-specialist e software-architect; os cinco comandos carregam a skill no orquestrador, e um `Load` não atravessa a fronteira do Task tool — [report](2026-08-28/04-agentes-e-skills.md)
- `agent-jira-detection-branch-naming-block-duplicated-no-canonical-home` — **MEDIUM** — alvo: `agents/database-specialist.md` (+ 12 agentes) — O bloco Detection → branch naming está em 13 corpos sem linha na tabela *Canonical Rule Homes*, e já divergiu da skill em placeholder (`{issueKey}` vs. `{taskId}`), tipos (subconjuntos incompatíveis por agente) e gate de aprovação (a skill exige "propose → on approval"; seis cópias mandam "create") — [report](2026-08-28/04-agentes-e-skills.md)
- `agent-docs-sync-task-closure-missing-mobile-devops` — **MEDIUM** — alvo: `agents/devops-specialist.md`, `agents/mobile-developer.md` — Os dois são coding agents por `CLAUDE.md:109` e não carregam `docs-sync`, obrigatória por `:157`; `devops-specialist:26` lê `docs/devops/` sem regra para escrever de volta e `:122` carrega uma diretiva de documentação própria, a duplicação exata que a tabela proíbe — [report](2026-08-28/04-agentes-e-skills.md)
- `agent-seo-specialist-outside-coding-agent-contract` — **MEDIUM** — alvo: `agents/seo-specialist.md` — Tem `## Worktree Isolation` (`:35`) e edita templates de página, mas está fora da enumeração de `CLAUDE.md:109` e por isso ficou sem `comments-policy` e sem `reuse-guidelines`; é o único dos nove que usa o rótulo correto da cascata, sinal de que foi escrito por outro caminho — [report](2026-08-28/04-agentes-e-skills.md)

### Economia de tokens (`token-*`) — 3

- `token-status-and-version-inline-bash-scripts-paid-twice-per-invocation` — **MEDIUM-HIGH** — alvo: `commands/status.md` (e `commands/version.md`) — Os dois únicos comandos que declaram economia de tokens como razão de existir embutem 132 linhas de bash no corpo, que o modelo lê **e** reemite: ~2.700 tokens por `/devteam:status` contra ~280 no padrão de uma linha de `commands/adr.md:23` (−90%) — [report](2026-08-28/05-economia-tokens.md)
- `token-checks-list-loads-all-three-provider-blocks-after-step-0-resolved-one` — **MEDIUM** — alvo: `skills/shared/setup-health-check/references/checks-list.md` — O Passo 0 resolve o provider ativo e `checks-list.md` é lido inteiro mesmo assim; 179 de 668 linhas (27% / ~7,8 KB) são os blocos dos outros dois providers, e o bloco Codex (158 linhas) é o que mais cresce — [report](2026-08-28/05-economia-tokens.md)
- `token-fix-patterns-517-lines-loaded-whole-to-apply-one-of-25-auto-fixes` — **MEDIUM** — alvo: `skills/shared/setup-health-check/references/fix-patterns.md` — 517 linhas / 22,6 KB (29% do fluxo de `/devteam:health-check`) lidas para aplicar de zero a três dos 25 padrões, porque 9 dos 13 ponteiros de `checks-list.md` não nomeiam a seção — contra a regra de `token-efficiency`, carregada por 18/18 agentes — [report](2026-08-28/05-economia-tokens.md)

### Descartados por duplicação

**57 candidatos rejeitados** — 12 no Eixo A, 14 no B, 10 no C, 8 no D, 13 no E.

**Porta 5 (estado — já no conjunto aberto), 25:** os 10 candidatos genuínos do Eixo A (`frontend-test-specialist.md:141-153` SonarQube · `database-specialist.md:84` RLS · `devops-specialist.md:137-148` checklist Docker/Terraform · `security-specialist.md:80-85` CI/CD · `backend-reviewer.md:30` configs de linter · `frontend-developer.md:3,91,96` · `database-specialist.md:133` Supabase · `audit.md:54,126,128` · `relayout.md:32` · `mobile.md:19,26`) · `CLAUDE.md` 602 linhas · `interaction-patterns` 209×34 · `token-efficiency` 160×18 · `orchestration` 391 linhas · `migration-v1-to-v2` 438 linhas · teto 205 vs. 211 · `size-limits.sh` exit 1 · `setup-assistant.md:146-147` · `commit.md:125-128` · `_index.md` legenda "All 131 entries" · `work-feedback` inalcançável pelos comandos · `CLAUDE.md:300` 3 de 5 templates · tabela de comandos do README omite `/devteam:install`.

**Porta 3 (semântica — 2 ou 3 de 3 atributos), 21:** `check-updates.sh` e `update.sh` apontando ao hook `_disabled-` (3/3 contra `ref-check-updates-shim-…`) · `command-map.json` carregado e nunca consumido (3/3 contra `ref-tool-map-tool-rewrites-…`) · `update-check.sh:6` nomeia o consumidor errado · `preferences-sync-lint.sh` órfão de trigger (contra `flow-helpers-archive-index-sh-orphan-…`) · `CLAUDE-md/preferences.md:42,46` e `notifier/SKILL.md:52,60` sobre hooks desativados · `architect.md:49-50` template de sumário por memória · `reuse-guidelines` eager e inerte · `install.md:38-46` tabela restatada · cinco reviewers com `git diff main...HEAD` sem filtro · `install.sh` 1240 linhas · `mobile-developer.md:159` checklist com 2 de 5 frameworks · `devops.md:2,14` · `frontend-reviewer.md:112,114` · cargas duplicadas de `test-pyramid`/`worktree` (falsos positivos do scanner) · `VHI-450` como exemplo em 7 lugares.

**Porta 4 (escopo menor sem sub-escopo novo), 5:** `devops-specialist.md:137-148` · `output-format` 203×9 · lista das 13 categorias em `health-check.md:39-51` (310 bytes contra 77,9 KB) · `preferences.json` lido inteiro em 31 sítios (arquivo de 23 linhas) · passos 9–10 da Context Loading Order (já limitados pelos tetos de `docs-sync`).

**Porta 1 (literal), 5:** `ref-notifier-documented-as-live-in-four-docs-…` · `docs-sync-claude-md-102-states-skill-desc-strict-false-…` · `agent-database-specialist-rls-as-engine-neutral-…` · `agent-security-specialist-cicd-checklist-github-actions-only-vocabulary` · `agent-reviewer-linter-config-three-divergent-…`.

**Refutado por evidência, 1:** `soften_plan_gate` (`render_provider.py:129-130`) removeria `Task: $ARGUMENTS` nos nove comandos `opt_out` — nenhum deles carrega essa linha isolada; o `re.sub` é no-op no HEAD.

**Descartado por mérito (passou as três portas, não sustenta achado), 3:** `docs/agents.md:42` descreve só a emissão de abertura do run banner, mas remete a `model-identity/SKILL.md`, que carrega a regra completa — omissão com ponteiro válido, não afirmação falsa · `docs/providers.md` e os três `docs/install-*.md` sem par pt-BR — o gate só exige o sentido pt-BR → EN e a regra de sincronia cobre apenas o par README · `.github/scripts/ci/**` (615+ linhas) fora do escopo do shellcheck de `01-lint.sh:92-93` — ferramenta indisponível neste ambiente, sem defeito concreto é proposta de escopo.

**Falsos positivos por substring no Eixo A** (~11 de 124 candidatos, mesmo padrão do pass anterior): `pip`→"pipeline", `express`→"expressed", `react`→"Auto-reactivation", `nest`→"honest", "Python Prerequisite" (pré-requisito do próprio harness).

---

## 2026-09-04 — Auditoria guardiã (verificação + 5 eixos)

Terceiro pass consecutivo contra `a67cac9`, com delta de código zero e o output dos dois passes
anteriores ainda fora do remoto (58 fingerprints existindo só no disco). A cobertura acumulada da
Fase 1 subiu de 58% para **72%** (87 de 121) e rendeu duas reaberturas. Os três achados originais
vêm de superfícies que nenhum pass anterior tinha examinado; os eixos A e D fecharam com zero
achados originais — resultado válido pela regra 2, reportado como tal. Ver
[o relatório do pass](2026-09-04/index.md) para método, cobertura e descartes.

### Referências e consistência (`ref-*`) — 1

- `ref-readme-sync-gate-discovers-only-pt-br-suffix-blind-to-inverted-en-suffix-pair` — **MEDIUM** — alvo: `.github/scripts/ci/02-readme-sync.sh` — `:192` descobre pares por `find . -name '*.pt-BR.md'` e `:183` deriva o par por `${ptbr%.pt-BR.md}.md`; o par `docs/reports/metrics-last-20-days.md` (pt-BR, 594 linhas) + `.en.md` (EN, 594 linhas) inverte os papéis e escapa inteiro — o gate imprime `OK` para 6 pares e termina em `readme-sync OK ✓` sem mencionar o sétimo, e a README Sync Rule (`CLAUDE.md:29`) só nomeia `README.pt-BR.md` — **Refina:** `flow-readme-sync-ci-hardcodes-three-doc-pairs-no-glob-discovery-any-new-pt-br-translation-pair-silently-unchecked` — [report](2026-09-04/02-referencias-e-consistencia.md)

### Fluxos, comandos e automação (`flow-*`) — 1

- `flow-prompt-auditoria-interactive-plan-gate-unsatisfiable-in-unattended-run` — **MEDIUM-HIGH** — alvo: `docs/reports/_prompt-auditoria.md` — A regra **inviolável** 7 (`:31-33`) exige aprovação humana antes de qualquer escrita e `:7` manda colar o bloco "em uma sessão nova", mas `:320-358` executa `git add`/`commit`/`push` para `main` sem ponto de confirmação, com tratamento de erro escrito para execução desassistida (`:333-334`, `:345-347`); numa execução sem interlocutor o pass ou trava ou viola em silêncio uma regra rotulada inviolável — e o julgamento fica disponível para as regras 1, 3 e 5 — [report](2026-09-04/03-fluxos-e-comandos.md)

### Economia de tokens (`token-*`) — 1

- `token-archive-index-rotates-index-sections-only-report-directories-never-pruned` — **LOW-MEDIUM** — alvo: `helpers/archive-index.sh` — O script opera inteiramente sobre `INDEX_FILE` (`:34`, `:162`) e o hook `99b-archive-index.sh:2-3` repete o escopo; os diretórios `docs/reports/<YYYY-MM-DD>/` que as linhas rotacionadas referenciam nunca são podados — 141 KB por pass, 1,0 MB em 36 dias, projetando ~7,3 MB/ano num diretório que nenhum agente lê, e a Fase 0 de todo pass roda `ls docs/reports/` sobre uma lista monotonicamente crescente — [report](2026-09-04/05-economia-tokens.md)

### Agnosticismo de stack (Eixo A) — 0

Varredura integral obrigatória executada: **124 candidatos → 0 violações originais**. Três hits são
falsos positivos por substring (`perspective`→`rspec`, `Auto-reactivation`→`react`,
`expressible`→`express`); o restante cai em tabelas de detecção (exceção por design), blocos
"Example", referência a ferramenta do próprio harness (isolamento Docker por worktree, pré-requisito
Python do instalador) e uma cláusula anti-acoplamento (`explain.md:48`, "never defaulting to
JavaScript"). Os 15 candidatos genuínos já estão no conjunto aberto — Porta 5.
[report](2026-09-04/01-agnosticismo-de-stack.md)

### Agentes e skills (Eixo D) — 0

Todos os gates de autoria passam: `agent-lint` limpo, `orphan-template-scan` limpo, 18/18 agentes ·
152/152 skills · 35/35 comandos dentro dos limites, 0 de 152 descrições de skill acima do orçamento
de 95 caracteres, paridade `commands/` ↔ `commands.json` íntegra. Único gate vermelho é
`size-limits.sh` saindo 1 por `CLAUDE.md: 602 lines`, que é o bug já registrado como
`auto-size-limits-claude-md-warning-counted-as-violation-turns-ci-lint-red` (HIGH, aberto). O
passivo do eixo é backlog não executado, não deriva nova. [report](2026-09-04/04-agentes-e-skills.md)

### Descartados por duplicação — 2026-09-04

**Porta 5 (estado — já registrados e abertos), 11 temas:** output do pass anterior não commitado
(`gov-audit-pass-output-uncommitted-…`, HIGH) · teto 205 documentado vs. 211 enforçado
(`agent-line-cap-205-…`, HIGH) · `size-limits.sh` saindo 1 por `CLAUDE.md` (`auto-size-limits-…`,
HIGH) · tabela de comandos do README omitindo `/devteam:install` · os 15 candidatos genuínos do Eixo
A (`frontend-developer.md:3,91,96` · `frontend-test-specialist.md:141-153` ·
`database-specialist.md:84,133` · `devops-specialist.md:137-148` · `security-specialist.md:80-85` ·
`backend-reviewer.md:30` · `mobile-developer.md:159` · `audit.md:54,126,128` · `relayout.md:32` ·
`mobile.md:19,26,27` · `setup-assistant.md:146-147` · `commit.md:125-133` · `devops.md:2,14`) ·
`orchestration` 391 linhas · `interaction-patterns` 209×34 · `token-efficiency` 160×18 ·
`migration-v1-to-v2` 438 linhas · `CLAUDE.md` 602 linhas monolítico · `install.sh` 1.240 linhas ·
dois laços de `ScheduleWakeup` concorrentes · nudge de learn verbatim em `pr.md:140-152`.

**Porta 3 (semântica — 2 ou 3 de 3 atributos coincidem), 2:** as três "cargas duplicadas" reportadas
pelo `orphan-skill-scan` (alvo + causa raiz coincidem com `ref-orphan-skill-scan-…`, e as três são
citação de regra, não segundo load) · `CLAUDE.md` § File Structure omitindo `docs/harness.md`,
`credentials.local.md`, `user-preferences.md`, `development/` e `prompts/` (3 de 3 contra a família
`ref-claude-md-file-structure-*`, mesma porta pela qual o caso `docs/prompts/` já caiu em 2026-08-14).

**Nota sobre o achado 1 e a Porta 3.** `flow-prompt-auditoria-interactive-plan-gate-unsatisfiable-in-unattended-run`
foi confrontado com `flow-prompt-auditoria-commit-step-contradicts-branch-rule` (MEDIUM, aberto,
mesmo alvo): o alvo coincide, mas a causa raiz (cópia do prompt de métricas vs. dois modos de
operação incompatíveis) e a remediação (corrigir o bloco vs. declarar um modo desassistido) divergem
— 1 de 3, abaixo do limiar de duplicata.

**Falsos positivos por substring no Eixo A** (3 de 124, padrão consistente com os dois passes
anteriores): `rspec`→"perspective", `react`→"Auto-reactivation", `express`→"expressible".

---

## 2026-09-11 — Auditoria guardiã (verificação + 5 eixos)

Baseline `9530551` · baseline anterior `a67cac9` · delta de **1 commit / 2 arquivos, nenhum de
código** (último commit de código: `a1e3791`, 21 dias). Fase 1: **12 de 34 não cobertos (35%)** →
9 ✅ · 2 🟡 · 1 🔴 (a 🔴 já registrada desde 2026-07-31; **0 🔴 nova**); acumulado **99 de 121 (82%)**
→ 83 ✅ · 9 🟡 · 7 🔴. Fase 1b: **0% de mortalidade** (0 de 113). Eixos A, D e E: nenhum achado
original — ver os relatórios para as medições que sustentam o zero.

### Referências e Consistência (`docs-sync-*`) — 2

- `docs-sync-telemetry-fresh-install-default-documented-true-while-install-sh-writes-false-without-consent` — **HIGH** — alvo: `CLAUDE.md` — `:386` e `skills/shared/user-preferences/SKILL.md:50,66` dizem que `telemetry` nasce `true` em arquivo novo; `scripts/install.sh:1057` define `TELEMETRY_VALUE="false"` e `:1117` sobrescreve o valor do schema antes de serializar — os outros dois espelhos (`CLAUDE-md/preferences.md:51`, `README.md:277`) já dizem o correto; é texto residual do comportamento anterior a `2e12335` — [report](2026-09-11/02-referencias-e-consistencia.md)
- `docs-sync-reports-index-preamble-declares-archive-index-trigger-less-while-stop-99b-dispatches-it` — **MEDIUM-HIGH** — alvo: `docs/reports/_index.md` — `:23-26` afirma que `helpers/archive-index.sh` "currently has no trigger — no hook, no CI job, no installer call"; `scripts/hooks/stop/99b-archive-index.sh` existe desde `cc28900` e casa o `SUBSCRIPT_RE` de `stop.sh:57`, e o fingerprint citado no próprio aviso está ✅ Executed em `:144` — o bloco está dentro das linhas 1-120 que a Fase 0 lê antes de qualquer outra coisa — [report](2026-09-11/02-referencias-e-consistencia.md)

### Fluxos, Comandos e Automação (`auto-*`) — 2

- `auto-no-gate-validates-claude-md-file-structure-tree-against-real-tree-four-recurrences-each-discarded-as-duplicate` — **MEDIUM-HIGH** — alvo: `helpers/` — `grep -rli "file structure" helpers/*.sh .github/scripts/ci/*.sh scripts/hooks/stop/*.sh` devolve zero; quatro divergências em seis semanas (`docs/prompts/` 08-14 · 3 de 5 templates 08-21 · `docs/harness.md` 08-28 · `hooks/lib/agent-usage.sh` hoje), cada uma corretamente descartada pela Porta 3 contra `ref-claude-md-file-structure-*`, o que torna a classe estruturalmente invisível ao banco — `CLAUDE.md:344-347` fecha `hooks/lib/` com `└──` em três arquivos e há quatro — [report](2026-09-11/03-fluxos-e-comandos.md)
- `auto-check-fingerprint-uniqueness-grep-admits-discarded-candidate-lines-as-slugs-inflating-count-and-silent-sed-fallthrough` — **MEDIUM** — alvo: `helpers/check-fingerprint-uniqueness.sh` — `:35` casa qualquer `^- \`[a-z]`, inclusive linhas da seção `### Descartados por duplicação` (`_index.md:311`, `:343`), e o `sed` de `:36` não casa nelas e as repassa **inalteradas**, promovendo prosa a chave de unicidade; o gate reporta 237 onde há 235 vivos, e dois descartes com a mesma redação disparariam falha bloqueante no CI e no `Stop` — mesmo defeito no comando da Fase 0 em `_prompt-auditoria.md:44` — [report](2026-09-11/03-fluxos-e-comandos.md)

### Descartados por duplicação

**Porta 5 (estado — já registrado e aberto), 34:** os 22 candidatos genuínos do Eixo A
(`frontend-developer.md:3,72,91,96,134-139` · `frontend-test-specialist.md:141-153` ·
`database-specialist.md:66-73,84,133` · `devops-specialist.md:46-56,137-148` ·
`security-specialist.md:80-85` e § Tooling SAST · `backend-reviewer.md:30` ·
`frontend-reviewer.md:112,114` · `mobile-developer.md:159` e description ·
`setup-assistant.md:146-147` · `commit.md:125-133` · `audit.md:54,126,128` · `relayout.md:32` ·
`mobile.md:19,26,27` · `devops.md:2,14`) · `SKILL_DESC_STRICT` false vs. true · teto 205 vs. 211 ·
lista de oito coding agents vs. nove · README sem `/devteam:install` · par `metrics-last-20-days`
fora do gate de sync · output de três passes fora do remoto · bloco de commit "two report files" ·
Plan Gate insatisfazível · `commands/commit.md:144-147` · `seo-specialist` fora do contrato ·
três agentes em 211 linhas · `spec-gate` inalcançável · `migration-v1-to-v2` 438×1 ·
`orchestration` 391 · `interaction-patterns` 209×34 · `token-efficiency` 160×18 · `CLAUDE.md` 602.

**Porta 3 (semântica — 2 ou 3 de 3 atributos), 6:** `CLAUDE.md:344-347` omitindo
`hooks/lib/agent-usage.sh` (**3 de 3** contra a família `ref-claude-md-file-structure-*`; a lacuna
de *gate* virou achado próprio acima) · `product-analyst.md:128-153` restatando a cascata de
worktree (2 de 3 contra `token-worktree-isolation-block-7-lines-x-8-agents`) · `CLAUDE-md/*.md` sem
teto em `size-limits.sh` (2 de 3 contra `token-claude-md-426-lines-still-monolithic-…`) · os quatro
docs de instalação sem menção a telemetria/`PRIVACY.md` (2 de 3 contra o achado HIGH deste pass) ·
`docs/prompts/` e `docs/reports/` como dois lares para prompts (2 de 3) · as 3 cargas duplicadas do
`orphan-skill-scan` (falsos positivos do scanner, verificados em 2026-08-21).

**Porta 4 (escopo menor sem sub-escopo novo), 2:** `output-format` 203 × 9 sítios (terceira
rejeição por esta porta; o único sub-escopo já é `token-output-format-third-copy-of-plan-format-…`)
· `preferences.json` lido inteiro em 31 sítios.

**Hipóteses refutadas por evidência, 5:** `99b-archive-index.sh` "ignora o fast-path do
dispatcher" (cabeçalho `:11-12` justifica: gate temporal com stamp diário em `:26-30`) ·
`software-architect` "carrega 29 skills incondicionalmente" (24 sob `**Conditional skill loads**`,
`:31-56`) · `comments-policy` "duplicada em 15 agentes" (15 formulações distintas por papel) ·
Foundational Rule "idêntica nos três reviewers" (é a linha única de delegação prescrita) ·
`/devteam:seo` "declarado mas não disparado" (honrado em `frontend.md:21`, `fullstack.md:21-22`,
`spawn-classifier:38-39`).

**Verificados como corretos, 3:** `commands.json` × tabela do `CLAUDE.md` × `commands/` (35=35=35) ·
`tiers.json` `agent_effort` × os cinco especialistas do `CLAUDE.md` · resolução de todas as
referências de template.

**Falsos positivos por substring no Eixo A: 25 de 124 (20,2%)** — o regex semente de
`_prompt-auditoria.md:143-146` não usa fronteira de palavra: `pip`×13 (em *pipeline*), `express`×3,
`rspec`×2 (*perspective*), `react`×2 (*reactivation*), `postgres`×2, `docker`×2, `aws`×2, `php`,
`golang`, `nest` (*nested*). Proporção muito acima dos 3 de 124 reportados em 2026-09-04, que
contava apenas as linhas inspecionadas manualmente.
