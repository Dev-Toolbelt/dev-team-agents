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
| 2026-09-18 | 24 (guardian audit pass) | 263 | Primeiro delta de **código** em 5 passes, e mínimo — `HEAD` = `ef69da3`, 2 arquivos (`scripts/install.sh`, `scripts/new-adr.sh`) num commit de 2026-09-17. Fase 1: **16 de 46 não cobertos (35%)** → 13 ✅ · 1 🟡 · 2 🔴 (**81,3% confirmado, 12,5% reaberto** — maior taxa desde 2026-09-04, abaixo do limiar de 15%); acumulado **115 de 121 (95%)** → 96 ✅ · 10 🟡 · 9 🔴 (**84% / 7,4%**) · Fase 1b: **3,2% de mortalidade** (2 de 63 — 1 🟢 + 1 ⚰️ por premissa refutada) · **4 fingerprints abertos mediram pior que no registro** (`install.sh` 503→1244, `orchestration` 377→391, coding agents 8→9, heredoc 1→3 chaves faltantes) · 67 candidatos descartados por duplicação |
| 2026-10-02 | 21 (guardian audit pass) | 284 | **Maior delta da história do banco** — `HEAD` = `5e338d9`, **650 commits e 728 arquivos** desde `ef69da3`, concentrados em contas/entitlement (ADR-0029), instaladores de CLI (ADR-0028), `infra/` e task board. Fase 1: **68 de 133 verificados (51%)** (todos HIGH/MEDIUM-HIGH + 30% do resto) → 64 ✅ · 4 🟡 · **0 🔴 (94,1% confirmado, 0% reaberto)** — e 25 dos 68 carregavam marca de 24–48 h, todas confirmadas; acumulado **115 de 121 (95%)** do conjunto v2 mais o lote novo de 2026-10-02 · Fase 1b: **97 de 97 (100%)** → **9,3% de mortalidade** (9 🟢, a maior desde a consolidação) · **8 fingerprints abertos mediram pior que no registro** e 2 mudaram de arquivo (re-ancoragem pendente) · Eixo A: **nenhum achado original** (124 hits → 23 candidatos → 0 violações; 17 já abertos) · 56 candidatos descartados por duplicação |
| 2026-10-10 | 3 (guardian audit pass) | 287 | Delta de **62 commits e 183 arquivos** desde `5e338d9`, concentrados em `app/` (52) e `scripts/lib` (23) — subárvores com 1 menção no banco — e **nenhuma marca de execução nova em 8 dias**. Fase 1: **76 de 153 (50%)** (todos HIGH/MEDIUM-HIGH + 30% do resto) → 64 ✅ · 6 🟡 · 6 🔴 (**84,2% confirmado · 1,3% reaberto novo**, 1 de 76; as outras 5 🔴 já estavam reabertas) · Fase 1b: **109 de 109 (100%)** → **1,8% de mortalidade** (2 🟢: o HIGH do `install-cli.sh` por `5dcf340` e o auto-learn pela ADR-0034) · **10 fingerprints abertos mediram pior** e 5 foram re-ancorados · Eixo A: **nenhum achado original** (124 hits → 23 candidatos → 0 violações) · 30 de 33 candidatos descartados |
| 2026-10-17 | 7 (guardian audit pass) | 294 | Delta de **76 commits e 157 arquivos** desde `349f18c` — o maior em `skills/shared` (21) e `commands/` (30) desde a consolidação — com o baseline **re-fixado de `78c11a6` para `bb0e883`** no meio do pass, depois que 46 commits entraram enquanto as Fases 0 e 1 corriam. Fase 1: **71 de 142 (50%)** (todos os 41 HIGH/MEDIUM-HIGH + 30% do resto, `seed=20261017`) → 66 ✅ · 5 🟡 · **0 🔴 (93,0% confirmado, 0% reaberto)** — segundo melhor placar do banco · Fase 1b: **111 de 111 (100%)** → **0% de mortalidade**, e o zero não é imobilidade: **11 alvos abertos foram tocados pelo delta e os 11 seguem reproduzindo** · **5 fingerprints abertos mediram pior** (`interaction-patterns` 209→323 linhas × 34 comandos, `CLAUDE.md` 647→678, `checks-list` 681→715, wiki index 13.715→15.233 B, `project-context` 'git log' 1→0 ocorrências) · Eixo A: **nenhum achado original** (125 hits → 2 candidatos → 0 violações) · 11 candidatos descartados por duplicação · **nota de método:** o campo `alvo:` nomeia o arquivo que descreve o problema, não o corrigido — aplicá-lo como alvo de janela teria dado 8 falsos 🔴 de 71 (11,3%) |

| 2026-10-24 | 2 (guardian audit pass) | 296 | Delta de **98 commits e 704 arquivos** desde `bb0e883` — o segundo maior do banco — com o working tree carregando **79 arquivos modificados e 9 não rastreados** durante todo o pass; toda evidência foi lida de `git show HEAD:<path>` e **2 candidatos morreram na Porta 0** por existirem só no disco (`docs-templates/SKILL.md` 153 linhas no `HEAD` contra 301 no disco). Fase 1: **75 de 152 (49,3%)** (todos os 42 HIGH/MEDIUM-HIGH + 30% do resto, `seed=20261024`) → 61 ✅ · 1 🟢 · 9 🟡 · 4 🔴 (**82,7% confirmado, 0% reaberto novo** — segundo pass consecutivo em zero; as 13 divergências já carregavam anotação) · Fase 1b: **118 de 118 (100%)** → **0,85% de mortalidade** (1 🟢: o parágrafo dos "sete comandos sem agente" saiu do `CLAUDE.md`), e o zero não é imobilidade: **37 alvos abertos foram tocados pelo delta e 36 seguem reproduzindo** · **8 fingerprints abertos mediram pior** (`CLAUDE.md` 426→582, `interaction-patterns` 209→318, `checks-list` 681→791, `fix-patterns` 517→622, `orchestration` 377→402, Jira 11→13 agentes, skills 151→156, descrições de comando divergentes 40 de 40) e 1 re-ancorado (`04-task-board.sh`) · Eixo A: **1 achado original** (127 hits → 14 candidatos → 1 violação) · 21 candidatos descartados por duplicação |

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

- `docs-sync-claude-md-102-states-skill-desc-strict-false-non-blocking-while-agent-lint-31-sets-true-and-ci-promoted-it-same-day` — **HIGH** — alvo: `CLAUDE.md` — Documenta como verdade corrente o valor oposto ao do código, com a variável nomeada — [report](2026-07-31/02-referencias-e-consistencia.md) — 📍 **Mudou de forma em 2026-10-10 e piorou:** `grep -rn SKILL_DESC_STRICT helpers/agent-lint.sh` devolve **vazio** — a variável não existe mais. Sobraram três referências a um knob removido: `CLAUDE.md:139` ("non-blocking warning today (`SKILL_DESC_STRICT=false`)"), `helpers/agent-lint.sh:327` ("warning — see SKILL_DESC_STRICT") e `.github/scripts/ci/01-lint.sh:66` ("`SKILL_DESC_STRICT=true` in helpers/agent-lint.sh"), as duas últimas em desacordo sobre o valor
- `docs-sync-claude-md-173-says-all-devteam-commands-load-current-context-while-213-lists-four-exceptions-as-the-complete-list` — **MEDIUM** — alvo: `CLAUDE.md` — Duas afirmações incompatíveis no mesmo arquivo, 40 linhas de distância — [report](2026-07-31/02-referencias-e-consistencia.md) — 📍 **Re-ancorado em 2026-10-10:** a afirmação está em `CLAUDE.md:216` ("All `/devteam:*` commands") e a lista de exceções migrou para `CLAUDE-md/commands.md:51`, agora com **seis** declaradas "the complete list" mais cinco que só a nomeiam em prosa
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

- `auto-full-suite-guard-sed-absorbs-sibling-json-keys` — **MEDIUM-HIGH** — alvo: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` — Captura gulosa do `sed` (linha 22) absorve `description` e demais chaves irmãs do payload; prosa contendo `.test.`/`.spec.`/`--filter` desliga o nudge silenciosamente — reproduzido com dois payloads de comando idêntico — [report](2026-08-12/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02
- `flow-learn-run-marker-records-commit-time-not-run-time` — **MEDIUM-HIGH** — alvo: `commands/learn.md` — O marcador `.learn-last-run` grava `git log -1 --format=%ct` (commit timestamp do HEAD) e é escrito antes do auto-commit do Step 5; a condição de skip de `commands/commit.md:17` é inalcançável e a economia de contexto que justifica `4734882` não se materializa — [report](2026-08-12/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02
- `auto-install-heredoc-omits-auto-learn-before-commit` — **MEDIUM-HIGH** — alvo: `scripts/install.sh` — O heredoc de fallback sem `python3` (linhas 1022-1025) não recebeu a chave que `4734882` adicionou ao canônico, apesar de o commit ter tocado o arquivo e de o aviso "the two drifted once already" estar na linha 1003; segunda ocorrência da mesma drift, sem gate — [report](2026-08-12/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02
- `docs-sync-02c-comment-cites-graphify-hint-as-sed-precedent` — **LOW-MEDIUM** — alvo: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` — O comentário da linha 18 invoca `02-graphify-hint.sh` como precedente de "pure-bash approach on the hot path", enquanto aquele arquivo (linha 11) documenta ter evitado `grep|sed` justamente para poupar 2 forks — [report](2026-08-12/03-fluxos-e-comandos.md)

### Referências e Consistência (`gov-*`) — 1

- `gov-repo-gitignore-omits-three-installer-written-entries` — **MEDIUM** — alvo: `.gitignore` — O repo dogfooda a instalação mas seu `.gitignore` tem 1 das 4 entradas que `install.sh:774-779` escreve e que `agents/setup-assistant.md:153` declara obrigatórias; `.learn-last-run` e `.worktree-session` ficam untracked e não ignorados — [report](2026-08-12/02-referencias-e-consistencia.md) — 🟢 **Resolved:** 2026-10-02 — resolvido de passagem por `5174b6d`

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
- `ref-tool-map-tool-rewrites-loaded-but-never-emitted-by-render-provider` — **HIGH** — alvo: `scripts/lib/render_provider.py` — `renames` é lido em `:742` e usado só como booleano, nunca emitido, enquanto `CLAUDE.md:67` e `docs/providers.md:127` documentam o rewrite como ativo; reproduzido com `AskUserQuestion` saindo 3× intacto no `.opencode/agents/setup-assistant.md` — [report](2026-08-14/02-referencias-e-consistencia.md) — ✅ **Executed:** 2026-10-02
- `ref-02c-guard-make-composer-shapes-have-no-row-in-scoped-test-runner-table` — **MEDIUM-HIGH** — alvo: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` — Os 3 `case` novos de `c03f898` não têm linha na tabela de runners da skill, `TESTPATH=`/`FILTER=` não existem nela, e `SKILL.md:59` declara legítimo o `Makefile` scoped que o guard sinaliza — [report](2026-08-14/02-referencias-e-consistencia.md) — ✅ **Executed:** 2026-10-02
- `docs-sync-changelog-unreleased-omits-full-suite-guard-and-orchestration-deltas` — **MEDIUM** — alvo: `CHANGELOG.md` — `[Unreleased]` registra 1 dos 3 commits de comportamento do delta; `c03f898` e `21fceb4` ficaram fora, contra `.github/pull_request_template.md:21`, sem gate automatizado — [report](2026-08-14/02-referencias-e-consistencia.md) — 🟢 **Resolved:** 2026-10-02 — resolvido de passagem por `68cd420`
- `ref-scoped-test-execution-bash-parallelism-section-outside-declared-canonical-scope` — **MEDIUM** — alvo: `skills/shared/scoped-test-execution/SKILL.md` — A seção nova (`:63-65`) trata de paralelismo de chamadas Bash, fora do escopo canônico declarado em `CLAUDE.md:166` e ausente da `description:` que alimenta o índice sempre carregado — [report](2026-08-14/02-referencias-e-consistencia.md)
- `docs-sync-hooks-md-64-full-suite-guard-examples-predate-wrapper-detection` — **LOW-MEDIUM** — alvo: `CLAUDE-md/hooks.md` — A única prosa do guard na árvore de docs exemplifica só runners nomeados; a classe nova (wrappers opacos, maior superfície de falso positivo) não aparece — [report](2026-08-14/02-referencias-e-consistencia.md)

### Fluxos e Comandos (`flow-*`) — 7

- `flow-update-sh-codex-slim-guard-dead-branch-false-strip-claim` — **HIGH** — alvo: `scripts/update.sh` — O guard Codex nunca avalia como falso (`agents/product-analyst.md` e `scripts/` sempre presentes), e o comentário do commit mais a entrada de CHANGELOG afirmam que `strip-tarball.sh` remove o cross-CLI plumbing, enquanto o script documenta o oposto — [report](2026-08-14/03-fluxos-e-comandos.md)
- `flow-02c-composer-fallback-case-ignores-every-scope-qualifier` — **MEDIUM-HIGH** — alvo: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` — Único `case` da função sem qualificador de escopo na exclusão; `composer test tests/Unit/FooTest.php` e `composer test-unit --filter FooTest` disparam o nudge (reproduzido) — [report](2026-08-14/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02
- `flow-update-sh-provider-reinstall-aborts-on-non-exit-3-failures` — **MEDIUM-HIGH** — alvo: `scripts/update.sh` — O fix espelha só a pré-condição do `exit 3`; `exit 1` por `jq`/`python3`/snippet vazio ainda mata o update sob `set -e` depois do core ter sucedido (reproduzido) — [report](2026-08-14/03-fluxos-e-comandos.md) — 🟢 **Resolved:** 2026-10-02 — resolvido de passagem por `60a1798`
- `flow-architect-claude-only-async-tool-names-rendered-verbatim` — **MEDIUM-HIGH** — alvo: `agents/software-architect.md` — `ScheduleWakeup`/`TaskList`/`SendMessage` aparecem como invariante não-negociável, sem hedge e sem entrada em `tool-map.json`; chegam literais ao `.opencode/agents/software-architect.md` renderizado — [report](2026-08-14/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02
- `flow-02c-make-pattern-substring-matches-cmake-and-chained-cmds` — **MEDIUM** — alvo: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` — `*make\ *test*` casa com `cmake ` e atravessa `&&`; `cmake --build . && ./run_tests` e `make migrate-test-db && phpunit --filter X` disparam (reproduzido) — [report](2026-08-14/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02
- `flow-prompt-auditoria-commit-step-contradicts-branch-rule` — **MEDIUM** — alvo: `docs/reports/_prompt-auditoria.md` — Bloco copiado do prompt de métricas: diz "two report files" (são 8), manda `push … main` contra a regra inviolável 8 do próprio arquivo, e carrega a mensagem de commit de métricas — [report](2026-08-14/03-fluxos-e-comandos.md)
- `flow-background-process-discipline-monitor-no-availability-fallback` — **LOW-MEDIUM** — alvo: `skills/architecture/orchestration/SKILL.md` — `Monitor` é declarado "única forma legítima" sem a cláusula de indisponibilidade que a check 5, seis linhas acima, carrega — [report](2026-08-14/03-fluxos-e-comandos.md)

### Agentes e Skills (`skill-*`, `agent-*`) — 5

- `skill-token-efficiency-background-mgmt-contradicts-orchestration-discipline` — **HIGH** — alvo: `skills/shared/token-efficiency/strategies.md` — § Background Process Management ensina fire-and-forget e lê shell de background com `TaskOutput(task_id=…)`, contradizendo a § Background Process Discipline criada em `21fceb4`; a versão errada alcança 18/18 agentes, a certa alcança 1 — [report](2026-08-14/04-agentes-e-skills.md)
- `agent-line-cap-205-documented-in-claude-md-vs-211-enforced-by-size-limits` — **HIGH** — alvo: `CLAUDE.md` — `:92` e `:311` dizem "enforces 205 (200+5)"; `helpers/size-limits.sh:44` tem `AGENT_LIMIT=211` desde `705acd1`, que não tocou o `CLAUDE.md` — 3 agentes estão exatamente em 211 — [report](2026-08-14/04-agentes-e-skills.md) — 🟢 **Resolved:** 2026-10-02 — resolvido de passagem por `c19f060`
- `agent-software-architect-inlines-spawn-integrity-4-5-no-availability-guard` — **MEDIUM-HIGH** — alvo: `agents/software-architect.md` — A linha 89 (nova em `21fceb4`) reescreve o check 5 inteiro em vez de delegar, e já diverge: manda chamar `ScheduleWakeup` sem o guard de disponibilidade nem o fallback de `orchestration:234-236` — [report](2026-08-14/04-agentes-e-skills.md)
- `skill-orchestration-spawn-integrity-unreachable-from-devteam-commands` — **MEDIUM** — alvo: `commands/*.md` — Zero dos 34 comandos carrega a skill de orquestração (única ocorrência é prosa em `architect.md:22`); os checks 1–5 alcançam 1 das ~16 superfícies que dão spawn — [report](2026-08-14/04-agentes-e-skills.md)
- `skill-orchestration-restates-scoped-test-execution-exception` — **MEDIUM** — alvo: `skills/architecture/orchestration/SKILL.md` — O passo 4 do Autonomous Sprint (`:68-70`) reescreve a exceção que `CLAUDE.md:166` manda nunca reescrever, duplicando o § Orchestrator Rule que já existe em `scoped-test-execution:18-20` — [report](2026-08-14/04-agentes-e-skills.md)

### Economia de Tokens (`token-*`) — 5

- `token-02c-full-suite-guard-substring-match-injects-nudge-on-non-test-commands` — **MEDIUM-HIGH** — alvo: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` — `is_full_suite()` casa substring solta (`*jest*`, `*pytest*`, `*rspec*`) sem âncora de invocação; 6 de 6 payloads de leitura testados no HEAD disparam 405 bytes de `additionalContext` em comandos que não rodam teste — [report](2026-08-14/05-economia-tokens.md) — ✅ **Executed:** 2026-10-02
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

- `auto-size-limits-claude-md-warning-counted-as-violation-turns-ci-lint-red` — **HIGH** — alvo: `helpers/size-limits.sh` — `:92` empurra o *warning threshold* do `CLAUDE.md` (600) no mesmo array `VIOLATIONS` do limite de falha (700), e `:98`/`:122` derivam o exit code só desse array — `bash .github/scripts/ci/01-lint.sh` sai **1** no HEAD (step `blocking` em `01-lint.sh:88`), com `CLAUDE.md` em 602 linhas desde `7e62124` — [report](2026-08-21/02-referencias-e-consistencia.md) — 🟢 **Resolved:** 2026-10-02 — resolvido de passagem por `a99dc3e`
- `ref-check-updates-shim-and-update-sh-exec-renamed-away-01-check-updates-hook` — **HIGH** — alvo: `scripts/check-updates.sh` — `:3` e `scripts/update.sh:24` fazem `exec` de `hooks/pre-tool-use/01-check-updates.sh`, que virou `_disabled-01-check-updates.sh`; `commands/update.md:82` chama o shim e trata ausência de stdout como "Up to date", então `/devteam:update` reporta atualizado num projeto desatualizado — [report](2026-08-21/02-referencias-e-consistencia.md) — ✅ **Executed:** 2026-09-30
- `ref-notifier-documented-as-live-in-four-docs-while-hook-file-is-disabled` — **HIGH** — alvo: `skills/shared/notifier/SKILL.md` — `:52`, `:60` e `:102` descrevem `stop/04-notifier.sh` disparando "After each turn" e incrementando `.notifier-state`; o arquivo é `_disabled-04-notifier.sh` e nenhum hook toca esse contador — skill shipped e alcançada por todo agente via `project-context/SKILL.md:61` — [report](2026-08-21/02-referencias-e-consistencia.md) — 🟢 **Resolved:** 2026-10-02 — resolvido de passagem por `f92db85`
- `docs-sync-readme-command-table-omits-devteam-install-in-both-languages` — **MEDIUM** — alvo: `README.md` — tabela de comandos lista 34 de 35; `/devteam:install` não aparece em `README.md`, `README.pt-BR.md` nem em `docs/*.md`, apesar de `CLAUDE.md:248` chamá-lo de "single entrypoint for tool installs" — o gate `02-readme-sync.sh` compara EN↔pt-BR, não a árvore — [report](2026-08-21/02-referencias-e-consistencia.md) — 📍 **Re-medido em 2026-10-10:** `grep -c "devteam:install"` devolve **0** em `README.md` e em `README.pt-BR.md`
- `ref-three-pointers-to-claude-md-hook-subscript-convention-moved-to-hooks-md` — **MEDIUM** — alvo: `CLAUDE-md/notifications.md` — `:65`, `scripts/hooks/stop.sh:53` e `scripts/hooks/pre-tool-use.sh:17` apontam para uma seção "Hook Sub-script Convention" do `CLAUDE.md` que não existe mais; as seções vivem em `CLAUDE-md/hooks.md:21,48`, e os dois dispatchers shipam para projetos onde `CLAUDE-md/` nem é instalado — [report](2026-08-21/02-referencias-e-consistencia.md)

### Fluxos e Comandos (`flow-*`, `docs-sync-*`) — 14

- `flow-pre-tool-use-dispatcher-sigpipe-141-masks-02c-block` — **HIGH** — alvo: `scripts/hooks/pre-tool-use.sh` — O dispatcher entrega o payload por pipe e `02-graphify-hint.sh:14` sai antes de consumir stdin; payload >64KB gera SIGPIPE → `pipefail` → exit 141, e a regra "primeiro não-zero vence" (`:33-35`) sobrescreve o `exit 2` bloqueante do `02c`, que falha aberto — [report](2026-08-21/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02
- `flow-merge-md-branch-and-tree-resolved-before-worktree-detection` — **HIGH** — alvo: `commands/merge.md` — Steps 0/1 rodam `git status`/`git branch --show-current` sem `-C` e sem `--git-common-dir` antes do Step 2 ler `.worktree-session`; da árvore principal o comando aborta em `:34` ("nothing to merge"), de dentro do worktree o arquivo de sessão é invisível — o caminho worktree é inalcançável — [report](2026-08-21/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02
- `flow-learn-nudge-ancestor-test-inverted-in-four-commands` — **HIGH** — alvo: `commands/merge.md` — "recorded commit hash is **not an ancestor** of the current HEAD (i.e. commits landed since the last learn run)" afirma como equivalentes condições opostas; com commits desde o learn o hash **é** ancestral e o nudge nunca dispara; replicado em `merge.md:89`, `pr.md:148`, `refactor.md:162` e referenciado por `audit.md:188` — [report](2026-08-21/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02
- `flow-02c-escape-hatch-anchored-while-detection-is-substring` — **MEDIUM-HIGH** — alvo: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` — A detecção casa substring em qualquer posição mas a escotilha (`:41-43`) exige `DEVTEAM_FULL_SUITE_CONFIRMED=1` na posição 0; `cd frontend && DEVTEAM_FULL_SUITE_CONFIRMED=1 npm test` e o wrapper `sh -c "..."` que o próprio arquivo cita são bloqueados sem saída viável — [report](2026-08-21/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02
- `docs-sync-auto-learn-before-commit-still-documented-as-pre-commit-step-0` — **MEDIUM-HIGH** — alvo: `CLAUDE-md/preferences.md` — `:55` e `skills/shared/user-preferences/SKILL.md:70` descrevem "`/devteam:commit` Step 0 auto-runs `/devteam:learn` before committing" depois de `576dcfa` mover a captura para o Step 6, pós-commit; o nome da chave em `preferences-defaults.json:18` também diz o contrário do comportamento — [report](2026-08-21/03-fluxos-e-comandos.md) — 🟢 **Resolved:** 2026-10-10 — resolvido pela ADR-0034 (`f754cde`, `b3c0dc1`) e **não** pela remediação proposta: em vez de a documentação mudar para "pós-commit", o código voltou para antes do commit. `commands/commit.md:88` roda `/devteam:learn --embedded` no Step 2.7 antes do agrupamento, e `CLAUDE-md/preferences.md:69` descreve exatamente isso
- `flow-claude-md-no-agent-command-list-says-seven-omits-push-and-merge` — **MEDIUM-HIGH** — alvo: `CLAUDE.md` — `:258` enumera sete comandos sem agente e diz "All seven name technical-writer", enquanto `scripts/lib/commands.json:7` (`_filler_agent_note`) lista nove incluindo `push` e `merge`; `b0383d6` atualizou o JSON e a lista de plan gate mas não o parágrafo — [report](2026-08-21/03-fluxos-e-comandos.md) — 📍 **Re-ancorado em 2026-10-10:** o parágrafo migrou de `CLAUDE.md:258` para `CLAUDE-md/commands.md:57` e **ainda diz "All seven"**, contra `scripts/lib/commands.json:7`, que enumera nove — 🟢 **Resolved:** 2026-10-24 — resolvido no delta `bb0e883..b64428b`: o parágrafo de `CLAUDE.md` que enumerava sete comandos sem agente não existe mais, e a lista canônica ficou só em `scripts/lib/commands.json:7` (`_filler_agent_note`, nove comandos) e `CLAUDE-md/commands.md:62,64`, que trata `/devteam:up` e `/devteam:down` à parte
- `flow-merge-md-rebases-onto-target-while-delegating-to-base-step-8` — **MEDIUM** — alvo: `commands/merge.md` — `:57` rotula a opção recomendada como "rebase onto `<target>`" e manda "delegate entirely" ao passo 8 do worktree skill, que faz "rebase onto **base**" (`SKILL.md:55`); `target` vem de quiz e `base` de `worktree_base_branch`, sem nada que resolva a divergência no único caminho destrutivo — [report](2026-08-21/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02 — 🟡 **Parcial na verificação de 2026-10-02:** `a2cf59c` mitigou o caso comum (`merge.md:37` faz o alvo assumir a base do worktree) mas a contradição central permanece — `:52` ainda manda "delegate entirely" ao passo 8, que rebaseia na base, e não existe mecanismo que repasse `<target>` como base; a skill não é tocada desde `e05ce90`.
- `flow-learn-nudge-has-no-canonical-skill-home-three-inline-copies` — **MEDIUM** — alvo: `CLAUDE.md` — A Learn Trigger Rule designa um **corpo de comando** (`commands/merge.md` § Step 4) como casa canônica, contra a doutrina "lives in exactly one skill"; `pr.md` e `refactor.md` carregam cópias inline e `audit.md:188` referencia "merge.md", caminho que não resolve em projeto instalado nem no Codex — [report](2026-08-21/03-fluxos-e-comandos.md)
- `flow-fix-md-only-implementation-command-without-review-qa-handoff` — **MEDIUM** — alvo: `commands/fix.md` — Zero ocorrências de `code-reviewer`/`qa-specialist` nas 42 linhas, enquanto `backend.md`, `frontend.md`, `fullstack.md`, `mobile.md` e `refactor.md` terminam todos em review+QA obrigatórios; com `TESTS_REQUIRED=no` o comando não tem nenhum gate após a alteração — [report](2026-08-21/03-fluxos-e-comandos.md)
- `flow-pr-md-default-branch-falls-back-to-global-config-then-literal-main` — **MEDIUM** — alvo: `commands/pr.md` — `:60-63` prefere `git config init.defaultBranch` (preferência global da máquina) ao `git remote show origin` e termina em `|| echo "main"`, literal proibido por `merge.md:32` e `worktree/SKILL.md:109`; alimenta `git log/diff ${DEFAULT_BRANCH}..HEAD` e a base do PR — [report](2026-08-21/03-fluxos-e-comandos.md)
- `flow-merge-md-merge-only-option-cites-undefined-follow-up-choice` — **LOW-MEDIUM** — alvo: `commands/merge.md` — `:59` manda rodar o merge "from whichever of the two paths above was implied by a follow-up choice", follow-up que o comando nunca define; a ambiguidade fica entre teardown do worktree e preservação dele — [report](2026-08-21/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02
- `docs-sync-session-start-comment-cites-nonexistent-02b-full-suite-guard` — **LOW-MEDIUM** — alvo: `scripts/hooks/session-start.sh` — `:175` aponta `pre-tool-use/02b-full-suite-guard.sh` como rede de segurança complementar; o arquivo é `02c-full-suite-guard.sh` e `02b-` é `02b-telemetry.sh` — único ponteiro do arquivo para a guarda que `abb8483` tornou bloqueante — [report](2026-08-21/03-fluxos-e-comandos.md) — 📍 **Re-ancorado em 2026-10-10:** `scripts/hooks/session-start.sh:249`
- `docs-sync-touched-paths-lib-header-says-stop-only-after-02c-sources-it` — **LOW-MEDIUM** — alvo: `scripts/hooks/lib/touched-paths.sh` — `:2` e `:12` declaram consumo exclusivo por `stop.sh` depois que `02c-full-suite-guard.sh:15-17` passou a fazer `source`; o cabeçalho também é o contrato de cache `DEVTEAM_TOUCHED_PATHS`, que o caminho PreToolUse não tem — cada detecção forka `git status`+`git log` — [report](2026-08-21/03-fluxos-e-comandos.md)
- `flow-merge-md-arguments-target-branch-parse-can-swallow-no-teardown-flag` — **LOW** — alvo: `commands/merge.md` — `:35` trata `$ARGUMENTS` como nome de branch sem remover flags antes; `/devteam:merge --no-teardown` sem alvo deixa a flag como única string candidata, enquanto `pr.md:25-28` mostra o padrão correto — [report](2026-08-21/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02

### Agentes e Skills (`skill-*`, `agent-*`) — 8

- `skill-orchestration-two-sections-both-numbered-check-5-breaks-cross-refs` — **HIGH** — alvo: `skills/architecture/orchestration/SKILL.md` — `a3e6095` criou um segundo `### 5.` (`:245`) ao lado do existente (`:213`); as três refs a "check 5" (`:270`, `software-architect.md:89`, `CLAUDE.md:172`) passam a resolver para seções opostas, e o único caminho de carga de `work-feedback` aponta para a errada — [report](2026-08-21/04-agentes-e-skills.md) — ✅ **Executed:** 2026-10-02
- `agent-qa-specialist-browser-foreground-rule-unsatisfiable-always-spawned` — **MEDIUM-HIGH** — alvo: `agents/qa-specialist.md` — `:85` exige rodar testes de browser "in the main/foreground agent, never delegated to a background subagent", mas `commands/qa.md:10` e mais 6 comandos spawnam `qa-specialist` via Task sem exceção — regra na camada errada, impossível de cumprir — [report](2026-08-21/04-agentes-e-skills.md)
- `skill-work-feedback-wakeup-cadence-cap-output-conflict-auto-reactivation` — **MEDIUM-HIGH** — alvo: `skills/shared/work-feedback/SKILL.md` — mesmo gatilho e mesma ferramenta que o check Auto-reactivation, com `delaySeconds` (300 vs 1200–1800), teto (nenhum vs 2) e conteúdo do turno ("only the table" vs blocker) divergentes, sem regra de precedência — [report](2026-08-21/04-agentes-e-skills.md) — ✅ **Executed:** 2026-10-02
- `agent-qa-specialist-in-app-browser-prefix-mcp-claude-browser-nonexistent` — **MEDIUM-HIGH** — alvo: `agents/qa-specialist.md` — `:79` detecta o browser in-app por `mcp__Claude_Browser__*`, namespace inexistente (o real é `mcp__claude-in-chrome__*`); o passo 1 "no need to ask" é sempre falso e o agente sempre pergunta — [report](2026-08-21/04-agentes-e-skills.md) — ⚰️ **Obsoleto:** 2026-09-18 — **premissa refutada**, não corrigida: o namespace `mcp__Claude_Browser__*` existe e coexiste com `mcp__claude-in-chrome__*`; `agents/qa-specialist.md:79` está correto como escrito. O achado era inválido na origem
- `agent-unit-test-isolation-rule-mirrored-five-agents-no-canonical-home` — **MEDIUM** — alvo: `agents/backend-test-specialist.md` — `9a64920` parafraseou a Hard rule em 5 agentes sem linha na tabela Canonical Rule Homes; as variantes de frontend atribuem `localStorage`/`IndexedDB`/cookies a `test-pyramid:44`, que não menciona storage de browser — [report](2026-08-21/04-agentes-e-skills.md)
- `skill-orchestration-preamble-says-three-checks-but-section-has-five` — **MEDIUM** — alvo: `skills/architecture/orchestration/SKILL.md` — `:152` declara "Three checks, in order, around every delegation round" numa seção com cabeçalhos 1–5; quem confiar no preâmbulo pula Liveness, Auto-reactivation e a tabela periódica — [report](2026-08-21/04-agentes-e-skills.md) — ✅ **Executed:** 2026-10-02
- `skill-work-feedback-description-names-credentials-json-not-local-variant` — **LOW-MEDIUM** — alvo: `skills/shared/work-feedback/SKILL.md` — `:3` nomeia `credentials.json` no índice de skills sempre carregado; é a única ocorrência dessa string no repo, o arquivo real é `credentials.local.json` (usado no corpo da própria skill em `:14`) — [report](2026-08-21/04-agentes-e-skills.md)
- `agent-three-at-exactly-211-line-ceiling-zero-headroom-for-additions` — **LOW** — alvo: `agents/software-architect.md` — 3 de 18 agentes no valor exato do teto e mais 5 a ≤3 linhas; qualquer acréscimo de uma linha falha o gate do `Stop`/CI, e corpos de agente não têm `references/` como saída — [report](2026-08-21/04-agentes-e-skills.md)

### Economia de Tokens (`token-*`) — 6

- `token-graphify-hint-3-git-forks-before-marker-early-exit-on-every-tool-call` — **MEDIUM-HIGH** — alvo: `scripts/hooks/pre-tool-use/02-graphify-hint.sh` — O bloco de resolução do marcador (`:16-20`) foi inserido acima do `case` de tool-name e do próprio `[ -f "$MARKER" ]`, então todo tool call num projeto com `graph.json` paga 3 forks antes de qualquer filtro — 13,4 ms/chamada medidos, contra 0 fork antes do delta — [report](2026-08-21/05-economia-tokens.md)
- `token-two-schedulewakeup-poll-loops-same-spawn-round-300s-vs-1200-1800s` — **MEDIUM-HIGH** — alvo: `skills/shared/work-feedback/SKILL.md` — Duas seções ambas numeradas `### 5.` agendam `ScheduleWakeup` e chamam `TaskList` na mesma rodada de background, com cadências de 1200–1800 s e 300 s; o laço de 300 s é o default ligado e o único sem teto — ≈12 acordadas/hora contra as 2 previstas, ≈3–5K tokens/hora — [report](2026-08-21/05-economia-tokens.md) — ✅ **Executed:** 2026-10-02
- `token-output-format-third-copy-of-plan-format-42-lines-nine-load-sites` — **MEDIUM** — alvo: `skills/shared/output-format/SKILL.md` — `:144-185` guarda uma terceira cópia do formato de plano (42 linhas) que o fix de `gov-plan-template-vs-skill-duplication` não tocou, já divergente no sentinela da coluna `Par.`, carregada inteira por 7 agentes + 2 comandos que nunca emitem plano — **Refina:** `gov-plan-template-vs-skill-duplication` — [report](2026-08-21/05-economia-tokens.md)
- `token-install-sh-second-unconditional-claude-md-injection-35-lines-every-session` — **MEDIUM** — alvo: `scripts/install.sh` — O Step 8b (`:862-886`) anexa um segundo bloco gerenciado ao `CLAUDE.md` do projeto-alvo; somado ao Step 8 são 35 linhas / ~1,97 KB lidas em 100% das sessões de todo projeto instalado, com 2 das 4 regras restatando `conventional-commits/SKILL.md` e sem gate que compare as duas cópias — [report](2026-08-21/05-economia-tokens.md)
- `token-work-feedback-opt-out-gate-lives-inside-the-71-line-skill-it-gates` — **LOW-MEDIUM** — alvo: `skills/shared/work-feedback/SKILL.md` — As 71 linhas são carregadas antes de `:14` mandar ler `credentials.local.json` para descobrir se a skill deve ser ignorada; `CLAUDE.md:172` e `orchestration:249` proíbem mover o teste booleano para o chamador, invertendo o padrão de gatilho-no-chamador já usado por `project-context` — [report](2026-08-21/05-economia-tokens.md)
- `token-pr-md-14-line-verbatim-learn-nudge-while-audit-md-delegates-in-one-line` — **LOW-MEDIUM** — alvo: `commands/pr.md` — `:140-152` é cópia verbatim de `commands/merge.md:81-93` (14 linhas / 718 bytes) enquanto `commands/audit.md:188` resolve o mesmo nudge em uma linha; quatro variantes do mecanismo na mesma janela — [report](2026-08-21/05-economia-tokens.md) — 🟢 **Resolved:** 2026-10-02 — resolvido de passagem por `a2cf59c`

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

- `gov-audit-pass-output-uncommitted-with-no-detection-mechanism` — **HIGH** — alvo: `docs/reports/_prompt-auditoria.md` — Os sete relatórios e as 37 fingerprints do pass de 2026-08-21 nunca chegaram ao remoto (`git show HEAD:docs/reports/_index.md` = 176 entradas vs. 213 na árvore); o bloco de commit/push de `:336-366` não registra que rodou e nenhum hook verifica que `docs/reports/` foi commitado — o pass seguinte redescobriria os 37 — [report](2026-08-28/03-fluxos-e-comandos.md) — 🟢 **Resolved:** 2026-09-18 — resolvido por `3acaa89` ("docs(reports): add guardian audit passes 2026-08-21 through 2026-09-11"); `git show HEAD:docs/reports/_index.md | grep -cE '^- .[a-z]'` = 241, idêntico à árvore. A cláusula secundária (nenhum hook verifica que `docs/reports/` foi commitado) permanece aberta como sub-escopo distinto
- `auto-agent-lint-quiz-first-never-scans-commands-dir` — **HIGH** — alvo: `helpers/agent-lint.sh` — `CLAUDE.md:210` declara a Quiz-first Rule dos 35 comandos imposta por `agent-lint.sh`, mas o único laço que chama `check_quiz_first` é `for agent_file in agents/*.md` (`:478-481`); reproduzido: `(yes/no)` injetado em `commands/qa.md` retorna `agent-lint: clean ✓` — [report](2026-08-28/03-fluxos-e-comandos.md)
- `auto-adr-gap-check-dependency-signal-blind-to-staged-and-committed-changes` — **MEDIUM-HIGH** — alvo: `scripts/hooks/stop/03e-adr-gap-check.sh` — `:32` usa `git diff` sem `--cached` e sem range, então o sinal de nova dependência morre assim que o arquivo é staged ou commitado, enquanto migration e provider-config (`:40`) disparam sobre conteúdo commitado; reproduzido em repo sintético (4 casos) — [report](2026-08-28/03-fluxos-e-comandos.md)
- `auto-slim-bootstrap-shape-contract-cannot-fail-the-build` — **MEDIUM-HIGH** — alvo: `.github/scripts/ci/slim-bootstrap.sh` — `:96` é `[ "$fail" -eq 0 ] && echo …` e `$fail` nunca é lido depois; as três asserções da seção 2 imprimem FAIL em stderr e o script sai 0, deixando os 15 arquivos de `SLIM_KEEP_LIST` sem gate — [report](2026-08-28/03-fluxos-e-comandos.md) — 🟢 **Resolved:** 2026-10-02 — resolvido de passagem por `9ed2964`

### Fluxos e comandos (`flow-*`) — 3

- `flow-review-command-writes-and-commits-while-documented-as-read-only` — **HIGH** — alvo: `commands/review.md` — `:66` manda editar arquivos e criar commits no contexto principal, contra `:35` do mesmo arquivo ("Do NOT review inline — always delegate") e contra `CLAUDE.md:254`, que classifica o comando como "read-only by design" e usa isso como razão para não ter Plan Gate — [report](2026-08-28/03-fluxos-e-comandos.md)
- `flow-question-tool-name-in-four-implementation-command-findings-gates` — **MEDIUM-HIGH** — alvo: `commands/backend.md` (+ `frontend.md`, `fullstack.md`, `mobile.md`) — `:66` manda usar a ferramenta `question`, nome nativo do opencode, no gate de resolução de findings; Claude recebe o corpo verbatim e a ferramenta não existe lá, enquanto `:6` do mesmo arquivo exige `AskUserQuestion` — [report](2026-08-28/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02
- `flow-rule-and-sync-rules-listed-as-technical-writer-but-never-delegate` — **MEDIUM** — alvo: `CLAUDE.md` — `:240-241` nomeiam `technical-writer` na coluna "Agents invoked", mas `grep -c "Task tool"` retorna 0 nos dois corpos, e a `_filler_agent_note` de `commands.json:7` enumera nove linhas-filler sem incluir essas duas — [report](2026-08-28/03-fluxos-e-comandos.md)

### Referências e consistência (`ref-*`, `docs-sync-*`) — 6

- `docs-sync-claude-md-effort-key-scope-vs-agent-effort-map` — **HIGH** — alvo: `CLAUDE.md` — `:64` afirma que `effort:` existe "only" em agentes do tier `repetitive` e `:73-74` declaram `none` para `backend-exec`/`frontend`, mas 5 agentes desses dois tiers carregam `effort: low` via `agent_effort`; seguir `:64` literalmente rebaixa o esforço de todo o time de execução — [report](2026-08-28/02-referencias-e-consistencia.md)
- `docs-sync-docs-agents-md-worktree-asks-once-vs-preference-default` — **MEDIUM-HIGH** — alvo: `docs/agents.md` — `:55` (espelhado em `agents.pt-BR.md:55`) diz que `backend-developer` "asks once whether to isolate work in a git worktree", mas com o default `worktree_active: true` a cascata cria o worktree sem perguntar; o gate `02-readme-sync.sh` compara estrutura e passa verde com o defeito espelhado — [report](2026-08-28/02-referencias-e-consistencia.md)
- `ref-command-description-duplicated-frontmatter-vs-commands-json` — **MEDIUM** — alvo: `scripts/lib/commands.json` — O `description` de cada comando tem dois donos (frontmatter para Claude, `commands.json` para opencode/Codex) e as **35** já divergem; `check_command_roster` valida `tier`/`agent`/`model:` e não o campo, e só o `commands.json` menciona o argumento de branch do `/devteam:status` — [report](2026-08-28/02-referencias-e-consistencia.md)
- `docs-sync-claude-md-coding-agents-list-omits-seo-specialist` — **MEDIUM** — alvo: `CLAUDE.md` — `:109` enuncia como fechada uma lista de oito coding agents ("all eight agents"), mas `grep -c "^## Worktree Isolation" agents/*.md` retorna nove; `seo-specialist` entrou em `1b5bb08` e a lista não é tocada desde 2026-05-04, e nenhum lint a valida — [report](2026-08-28/02-referencias-e-consistencia.md)
- `docs-sync-claude-md-context-list-item-count-12-vs-11` — **LOW-MEDIUM** — alvo: `CLAUDE.md` — `:158` chama a Context Loading Order de "12 items"; ela tem 11 hoje e tinha 10 em `7736e20`, o commit que introduziu o número — o único fato verificável da tabela *Canonical Rule Homes* nunca esteve correto — [report](2026-08-28/02-referencias-e-consistencia.md) — 🟢 **Resolved:** 2026-10-02 — resolvido de passagem por `e80903e`
- `docs-sync-readme-ptbr-agents-link-points-to-english-doc` — **LOW** — alvo: `README.pt-BR.md` — `:141` linka `docs/agents.md` enquanto `:15` linka `docs/agents.pt-BR.md`; o `02-readme-sync.sh` compara contagem de links por seção, não alvo, então um link idêntico ao do EN é indistinguível de tradução correta — [report](2026-08-28/02-referencias-e-consistencia.md) — 📍 **Re-medido em 2026-10-10:** **7** links para docs EN, não 1 — `README.pt-BR.md:60,61,62,66,262`, `docs/harness.pt-BR.md:179` e `docs/installation.pt-BR.md:5` (×2)

### Agentes e skills (`agent-*`, `skill-*`) — 5

- `agent-worktree-cascade-delegates-to-unshipped-claude-md` — **HIGH** — alvo: `agents/mobile-developer.md` (+ 8 coding agents) — Os 9 agentes que editam arquivos apontam para `CLAUDE.md` → "Worktree Isolation", rótulo inexistente (`:111` chama a seção de outro nome) num arquivo que `KEEP_ROOT` (`install.sh:369`) remove do pacote; e `mobile-developer:39`/`devops-specialist:40` proíbem carregar a skill no ramo `worktree=no`, o único que precisa do formato de escrita do arquivo de sessão — [report](2026-08-28/04-agentes-e-skills.md) — ✅ **Executed:** 2026-10-02
- `skill-spec-gate-scope-lock-hard-gate-unreachable-by-execution-agents` — **MEDIUM-HIGH** — alvo: `skills/shared/spec-gate/SKILL.md` — `:54-55` nomeia quatro coding agents e `:65-70` define o `<HARD-GATE>` que proíbe encerrar com suposição aberta, mas `grep -ln spec-gate agents/*.md` devolve só product-analyst, qa-specialist e software-architect; os cinco comandos carregam a skill no orquestrador, e um `Load` não atravessa a fronteira do Task tool — [report](2026-08-28/04-agentes-e-skills.md) — ✅ **Executed:** 2026-10-02
- `agent-jira-detection-branch-naming-block-duplicated-no-canonical-home` — **MEDIUM** — alvo: `agents/database-specialist.md` (+ 12 agentes) — O bloco Detection → branch naming está em 13 corpos sem linha na tabela *Canonical Rule Homes*, e já divergiu da skill em placeholder (`{issueKey}` vs. `{taskId}`), tipos (subconjuntos incompatíveis por agente) e gate de aprovação (a skill exige "propose → on approval"; seis cópias mandam "create") — [report](2026-08-28/04-agentes-e-skills.md)
- `agent-docs-sync-task-closure-missing-mobile-devops` — **MEDIUM** — alvo: `agents/devops-specialist.md`, `agents/mobile-developer.md` — Os dois são coding agents por `CLAUDE.md:109` e não carregam `docs-sync`, obrigatória por `:157`; `devops-specialist:26` lê `docs/devops/` sem regra para escrever de volta e `:122` carrega uma diretiva de documentação própria, a duplicação exata que a tabela proíbe — [report](2026-08-28/04-agentes-e-skills.md)
- `agent-seo-specialist-outside-coding-agent-contract` — **MEDIUM** — alvo: `agents/seo-specialist.md` — Tem `## Worktree Isolation` (`:35`) e edita templates de página, mas está fora da enumeração de `CLAUDE.md:109` e por isso ficou sem `comments-policy` e sem `reuse-guidelines`; é o único dos nove que usa o rótulo correto da cascata, sinal de que foi escrito por outro caminho — [report](2026-08-28/04-agentes-e-skills.md)

### Economia de tokens (`token-*`) — 3

- `token-status-and-version-inline-bash-scripts-paid-twice-per-invocation` — **MEDIUM-HIGH** — alvo: `commands/status.md` (e `commands/version.md`) — Os dois únicos comandos que declaram economia de tokens como razão de existir embutem 132 linhas de bash no corpo, que o modelo lê **e** reemite: ~2.700 tokens por `/devteam:status` contra ~280 no padrão de uma linha de `commands/adr.md:23` (−90%) — [report](2026-08-28/05-economia-tokens.md)
- `token-checks-list-loads-all-three-provider-blocks-after-step-0-resolved-one` — **MEDIUM** — alvo: `skills/shared/setup-health-check/references/checks-list.md` — O Passo 0 resolve o provider ativo e `checks-list.md` é lido inteiro mesmo assim; 179 de 668 linhas (27% / ~7,8 KB) são os blocos dos outros dois providers, e o bloco Codex (158 linhas) é o que mais cresce — [report](2026-08-28/05-economia-tokens.md) — 📍 **Re-medido em 2026-10-10:** `checks-list.md` em **681** linhas (668 no registro)
- `token-fix-patterns-517-lines-loaded-whole-to-apply-one-of-25-auto-fixes` — **MEDIUM** — alvo: `skills/shared/setup-health-check/references/fix-patterns.md` — 517 linhas / 22,6 KB (29% do fluxo de `/devteam:health-check`) lidas para aplicar de zero a três dos 25 padrões, porque 9 dos 13 ponteiros de `checks-list.md` não nomeiam a seção — contra a regra de `token-efficiency`, carregada por 18/18 agentes — [report](2026-08-28/05-economia-tokens.md) — 📍 **Re-medido em 2026-10-10:** `fix-patterns.md` em **457** linhas (517 no registro) — mediu melhor

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

- `docs-sync-telemetry-fresh-install-default-documented-true-while-install-sh-writes-false-without-consent` — **HIGH** — alvo: `CLAUDE.md` — `:386` e `skills/shared/user-preferences/SKILL.md:50,66` dizem que `telemetry` nasce `true` em arquivo novo; `scripts/install.sh:1057` define `TELEMETRY_VALUE="false"` e `:1117` sobrescreve o valor do schema antes de serializar — os outros dois espelhos (`CLAUDE-md/preferences.md:51`, `README.md:277`) já dizem o correto; é texto residual do comportamento anterior a `2e12335` — [report](2026-09-11/02-referencias-e-consistencia.md) — 📍 **Re-ancorado em 2026-10-10:** `CLAUDE.md:370` e `scripts/install.sh:1181` (`TELEMETRY_VALUE="false"`); a contradição persiste no caminho não-interativo (`curl … | bash`), onde `:1215` registra "No terminal available … so it is DISABLED"
- `docs-sync-reports-index-preamble-declares-archive-index-trigger-less-while-stop-99b-dispatches-it` — **MEDIUM-HIGH** — alvo: `docs/reports/_index.md` — `:23-26` afirma que `helpers/archive-index.sh` "currently has no trigger — no hook, no CI job, no installer call"; `scripts/hooks/stop/99b-archive-index.sh` existe desde `cc28900` e casa o `SUBSCRIPT_RE` de `stop.sh:57`, e o fingerprint citado no próprio aviso está ✅ Executed em `:144` — o bloco está dentro das linhas 1-120 que a Fase 0 lê antes de qualquer outra coisa — [report](2026-09-11/02-referencias-e-consistencia.md) — 🔴 **Reaberto na verificação de 2026-10-10:** nenhum commit da janela de 2026-09-11 tocou `docs/reports/_index.md` (os commits em volta são `3acaa89` de 2026-09-12 e `6b3846f` de 2026-09-18, ambos "add guardian audit pass"), e no `HEAD` `_index.md:23-26` segue afirmando "That script currently has no trigger — no hook, no CI job, no installer call — so rotation has never run" contra `scripts/hooks/stop/99b-archive-index.sh:21`, que dispara `helpers/archive-index.sh` com stamp diário

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

---

## 2026-09-18 — Auditoria guardiã (verificação + 5 eixos)

Baseline `ef69da3`, baseline anterior `9530551`. Delta de código de **2 arquivos**. Fase 1: 16
verificados → 13 ✅ · 1 🟡 · 2 🔴. Fase 1b: 63 de 117, mortalidade 3,2%. **24 achados originais**, 67
candidatos descartados pelo Protocolo Anti-Duplicação. Ver [o relatório do pass](2026-09-18/index.md).

### Agnosticismo de Stack (`agent-*`) — 4

- `agent-mobile-developer-routing-rules-restates-five-runner-matrix` — **MEDIUM-HIGH** — alvo: `agents/mobile-developer.md` — `:149` (§ Routing Rules) congela uma matriz de 5 runners (`jest`, `vitest`, `flutter test`, `xcodebuild test`, `./gradlew test`) que `scoped-test-execution` § Runner Filters resolve em 11 com filtros de escopo e override por script do projeto; contradiz `:171`, que manda derivar da skill — [report](2026-09-18/01-agnosticismo-de-stack.md)
- `agent-tracker-monoculture-jira-in-eleven-bodies-linear-reachable-from-one` — **MEDIUM** — alvo: `agents/` — 11 agentes têm `## Jira Integration` e 6 prescrevem o padrão de branch do Jira em seção de comportamento, enquanto `skills/integrations/linear/SKILL.md` só é alcançável de `product-analyst.md:177`; `orphan-skill-scan` não reporta porque a referência única satisfaz o check — [report](2026-09-18/01-agnosticismo-de-stack.md) — **Refina:** `agent-jira-detection-branch-naming-block-duplicated-no-canonical-home`
- `agent-seo-specialist-foundational-rule-names-next-seo-astro-seo` — **LOW-MEDIUM** — alvo: `agents/seo-specialist.md` — `:27` (§ Foundational Rule) ilustra "o que o framework já provê" apenas com `next-seo` e `astro-seo`, na linha que decide se uma dependência nova será proposta, num agente auto-spawnado também em stacks server-rendered — [report](2026-09-18/01-agnosticismo-de-stack.md)
- `agent-code-reviewer-output-template-pins-file-js-six-placeholders` — **LOW** — alvo: `agents/code-reviewer.md` — `:144,148,153,157,160,163` (§ Review Output Format) usam `file.js` nos seis placeholders, inclusive no caminho `Review type: Backend`, enquanto `backend-reviewer.md:166-186` roda `.go/.php/.py/.rb/.ts` de propósito — [report](2026-09-18/01-agnosticismo-de-stack.md)

### Referências e Consistência (`ref-*`, `docs-sync-*`, `auto-*`) — 5

- `ref-comments-policy-routing-table-points-to-sections-dir-not-references` — **MEDIUM-HIGH** — alvo: `skills/shared/comments-policy/SKILL.md` — `:107-109` roteiam para `sections/type-annotations.md`, `sections/aaa-pattern.md` e `sections/anti-patterns.md`; os três vivem em `references/` e `sections/` contém outros arquivos — a tabela que `CLAUDE.md:161` declara canônica tem 3 caminhos mortos, em skill carregada por 8+ agentes — [report](2026-09-18/02-referencias-e-consistencia.md) — ✅ **Executed:** 2026-10-02
- `docs-sync-preferences-mirror-registry-names-readmes-omits-docs-pair` — **MEDIUM-HIGH** — alvo: `CLAUDE.md` — `:382` lista `README.md`/`README.pt-BR.md` como espelhos de `preferences-defaults.json`, mas a tabela migrou em `affc6fe` para `docs/user-preferences{,.pt-BR}.md`, que não constam do registro e já perderam `auto_learn_before_commit` nos dois idiomas — [report](2026-09-18/02-referencias-e-consistencia.md) — ✅ **Executed:** 2026-10-02
- `auto-orphan-skill-scan-user-invocable-parser-overruns-into-next-table` — **MEDIUM** — alvo: `helpers/orphan-skill-scan.sh` — o `awk` de `:37` termina em `/^### /`, que não casa `#### User-Invocable Commands`, então a janela vai de `CLAUDE.md:189` a `:266` e captura 5 nomes em vez de 3 — `current-context` e `spawn-classifier` ficam isentas da detecção de órfãos — [report](2026-09-18/02-referencias-e-consistencia.md)
- `ref-monitoring-loki-config-reference-unreachable-no-gate-covers-references-dir` — **LOW-MEDIUM** — alvo: `skills/devops/monitoring/references/loki-config.md` — `rg -n 'loki-config' .` devolve só o próprio arquivo (83 linhas shipadas); `orphan-skill-scan.sh:122-123` pula `references/` por construção, `orphan-template-scan` só cobre `templates/` e `size-limits.sh` isenta o diretório — reachability de `references/` não tem gate algum — [report](2026-09-18/02-referencias-e-consistencia.md)
- `docs-sync-providers-md-zen-premium-column-mixes-namespaces-pinned-ids` — **LOW-MEDIUM** — alvo: `docs/providers.md` — `:215-218` sugerem `opencode/claude-opus-4-7`, `opencode/gpt-5.6-terra` e `opencode/gpt-5.6-luna`: ids Codex com prefixo trocado, mais o id pinado que `:51` declara aposentado, num documento que convida à substituição em `tiers.json` — [report](2026-09-18/02-referencias-e-consistencia.md)

### Fluxos, Comandos e Automação (`auto-*`, `flow-*`) — 5

- `auto-stop-03c-reuse-lint-gates-on-csv-registry-while-harness-writes-md` — **HIGH** — alvo: `scripts/hooks/stop/03c-reuse-lint.sh` — `:11` testa `docs/development/reuse-guidelines.csv` e `:12` sai 0 quando ausente; o registro que `/devteam:rule` escreve e `reuse-lint.sh:15` lê é `.md` — o único gate automático do sistema de reuse-guidelines nunca rodou em nenhum projeto instalado — [report](2026-09-18/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02
- `flow-path-rewrites-move-docs-development-but-shipped-scripts-hardcode-it` — **HIGH** — alvo: `scripts/lib/tool-map.json` — `path_rewrites` reescreve `docs/development/` → `docs/` em opencode e Codex, mas `new-adr.sh:14`, `reuse-lint.sh:15` e `03e-adr-gap-check.sh:21` codificam o caminho antigo; o *Check Before Creating* de `/devteam:adr` varre um diretório que o script que ele invoca nunca popula — [report](2026-09-18/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02
- `auto-install-sh-bash-source-fallback-resolves-to-cwd-and-sources-project-lib` — **MEDIUM-HIGH** — alvo: `scripts/install.sh` — `:51` usa `${BASH_SOURCE[0]:-$0}`; sob `curl … | bash`, `$0` é `bash`, `dirname` devolve `.` e `:54` dá `source` num `lib/state.sh` do projeto do usuário, sobrescrevendo `state_get`/`state_set` — reproduzido; `ef69da3` trocou um erro barulhento por um caminho silencioso — [report](2026-09-18/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02
- `auto-ci-never-executes-install-sh-nor-new-adr-sh-only-shellcheck-gate` — **MEDIUM** — alvo: `.github/workflows/ci.yml` — nenhum script shipped é executado sob sua invocação documentada (`40-install-fixture.sh:19-21` pula Claude; `new-adr.sh` só aparece na `SLIM_KEEP_LIST`); os dois bugs de runtime de `ef69da3` passam limpos por `bash -n` e por shellcheck — [report](2026-09-18/03-fluxos-e-comandos.md) — ✅ **Executed:** 2026-10-02
- `auto-99b-archive-index-writes-daily-stamp-even-when-rotation-failed` — **LOW-MEDIUM** — alvo: `scripts/hooks/stop/99b-archive-index.sh` — `:44` faz `|| OUTPUT=""` (destrói exit code e stderr) e `:46-47` gravam o carimbo do dia incondicionalmente; uma rotação quebrada fica indistinguível de uma sem trabalho e o gate diário de `:33` bloqueia nova tentativa por 24 h — [report](2026-09-18/03-fluxos-e-comandos.md)

### Agentes e Skills (`agent-*`, `skill-*`) — 6

- `agent-project-context-delegation-claims-recent-git-log-absent-from-skill-18x` — **HIGH** — alvo: `skills/shared/project-context/SKILL.md` — `grep -c 'recent git log' agents/*.md` → 18 de 18 afirmam que a skill cobre histórico git; `grep -i 'git log'` na skill sai 1 e a § Context Loading Order tem 11 itens, nenhum de histórico — nenhum agente lê o que a árvore mudou, e nenhum tem motivo para suprir a lacuna — [report](2026-09-18/04-agentes-e-skills.md)
- `agent-three-reviewers-review-output-template-triplicated-comments-slot-lost` — **MEDIUM-HIGH** — alvo: `agents/code-reviewer.md` — os três reviewers delegam a `pr-review` e em seguida inlinam ~30 linhas de template cada; já divergiu: só o router tem `### Comments` (`:155`) e só os especialistas têm `### SonarQube` — os dois agentes que de fato executam o review não têm onde reportar violação de `comments-policy` — [report](2026-09-18/04-agentes-e-skills.md)
- `skill-git-workflow-type-prefixes-vs-worktree-context-title-branch-naming` — **MEDIUM-HIGH** — alvo: `skills/shared/git-workflow/SKILL.md` — `:24-33` prescreve `feature/*`,`fix/*`,`hotfix/*` (prefixo de tipo) e `worktree/SKILL.md:59-67` prescreve `<context>/<brief-title>`; nenhuma menciona a outra, `CLAUDE.md` reforça a segunda, e a colisão já vazou para `branch-flow.md:198-199`, com `chore`/`fix` na coluna Domain — [report](2026-09-18/04-agentes-e-skills.md)
- `skill-three-security-skills-hold-divergent-ecosystem-scanner-tables` — **MEDIUM** — alvo: `skills/security/dependency-audit/SKILL.md` — a tabela ecossistema→scanner existe em três skills que `security-specialist.md:46,47,50` pode carregar na mesma tarefa, já divergentes (PHP presente em duas, ausente na terceira; Trivy em três formas); num projeto PHP, a ordem de leitura decide se `composer audit` roda — [report](2026-09-18/04-agentes-e-skills.md)
- `skill-test-strategy-inlines-test-pyramid-section-both-loaded-together` — **MEDIUM** — alvo: `skills/testing/test-strategy/SKILL.md` — `:20-55` (36 linhas) duplicam a skill `test-pyramid`, carregada na mesma frase por ambos os test-specialists; os critérios já não batem (`:44` autoriza banco real para integração contra a Hard rule que 5 agentes citam como `[BLOCKING]`) — [report](2026-09-18/04-agentes-e-skills.md)
- `skill-design-system-md-two-divergent-schemas-docs-sync-vs-design-system-audit` — **LOW-MEDIUM** — alvo: `skills/design/design-system-audit/SKILL.md` — `:104` aponta para o esquema canônico de `docs-sync:86-92` (5 seções, com `<!-- last-updated -->`) e `:108-135` emite um concorrente de 7 seções sem o marcador, com três nomes divergentes — a skill precisa de uma linha de prosa para desautorizar o próprio conteúdo — [report](2026-09-18/04-agentes-e-skills.md)

### Economia de Tokens (`token-*`) — 4

- `token-151-skills-flat-symlinked-into-claude-skills-index-12751-chars-per-context` — **MEDIUM-HIGH** — alvo: `scripts/install.sh` — `:599-610` symlinkam 151 das 152 skills para `.claude/skills/`, colocando 12.751 chars (~3.187 tokens) de `name:`+`description:` no índice sempre carregado de **cada** contexto; um `/devteam:fullstack` paga ~22.300 tokens só de índice, enquanto as 483 cargas reais são por caminho explícito — [report](2026-09-18/05-economia-tokens.md) — 📍 **Re-medido em 2026-10-10:** **155** skills (151 de 152 no registro)
- `token-current-context-cache-block-36-of-105-lines-fails-own-scope-rule` — **MEDIUM** — alvo: `skills/shared/current-context/SKILL.md` — `:58-93` (34% do arquivo, ~420 tokens) são implementação bash de um cache carregado por 29 de 35 comandos; no hit (`:81`) o payload não traz as duas listas de arquivos que `:17-18,:23` exigem para a Scope Rule, e o TTL diverge do espelho em `CLAUDE-md/user-data.md:17` — [report](2026-09-18/05-economia-tokens.md)
- `token-graphify-setup-os-detection-30-lines-diverges-from-tool-installers` — **MEDIUM** — alvo: `skills/devops/graphify-setup/SKILL.md` — `:24-53` duplicam a detecção de SO num passo que `:64` já delega a `/devteam:install`, e a cópia divergiu na direção destrutiva: barra o usuário Windows com `winget` que `tool-installers/SKILL.md:12` atende nativamente — [report](2026-09-18/05-economia-tokens.md)
- `token-telemetry-consent-guard-reforks-python3-above-the-fast-path` — **MEDIUM** — alvo: `scripts/hooks/stop/05-telemetry.sh` — `:31` roda `_telemetry_enabled` (1 fork de `python3`, 8 ms medidos) **acima** do fast-path de `:39` que existe para evitar forks; com K agentes o Stop paga 3+K forks do mesmo veredito imutável, e no default (telemetria `false`) todos são desperdício — [report](2026-09-18/05-economia-tokens.md)

- `auto-github-actions-pinned-to-mutable-major-tags` — **MEDIUM** — alvo: `.github/workflows/ci.yml`, `.github/workflows/release.yml` — todos os 16 `uses:` apontam para tags major mutáveis (`actions/checkout@v4` ×8, `actions/setup-python@v5` ×4, `setup-node`, `upload-artifact`, `download-artifact`, e `ruby/setup-ruby@v1` — o único terceiro); quem controla a tag controla o que roda no CI. Recomendação: fixar `ruby/setup-ruby@v1` em SHA (terceiro, e `release.yml` é o workflow privilegiado) e deixar `actions/*` na tag major até existir config Dependabot para `github-actions`, sem a qual fixar tudo troca um risco pequeno por patches de segurança que ninguém aplica — [report](2026-09-29/00-security-scanners.md) — ✅ **Executed:** 2026-10-02

### Descartados por duplicação — 67

Detalhe por eixo nos relatórios. Distribuição: Eixo A 28 (13 pela Porta 5), B 13, C 7, D 10, E 9.
Três descartes de tipo distinto ficam registrados aqui para não serem redescobertos:

- **Refutados por evidência, não duplicados.** As referências "quebradas" a `workflow-detection`, `jquery`, `learn-nudge` e `model-identity/references/format.md` existem só em `CHANGELOG.md:601` e em relatórios históricos; `agents/mobile-test-specialist.md`, citado como inexistente, é a **opção A rejeitada** de `docs/development/adrs/0006-mobile-pipeline-architecture.md:17-18`.
- **`gov-claude-md-158-foundational-context-list-says-12-items-canonical-has-11`** foi proposto pelo Eixo D e revertido na consolidação — Porta 5 contra `docs-sync-claude-md-context-list-item-count-12-vs-11`.
- **As três "cargas duplicadas" do `orphan-skill-scan`** (`test-pyramid` ×2, `worktree` em `merge.md`) continuam falsos positivos do scanner, como em 2026-08-21 e 2026-08-28, e continuam custando 12 linhas de contexto por Stop.

---

## 2026-10-02 — Auditoria guardiã (verificação + 5 eixos)

Baseline `5e338d9` · baseline anterior `ef69da3` · **delta de 650 commits e 728 arquivos — o maior da
história do banco**. Fase 1: **68 de 133 (51%)** → 64 ✅ · 4 🟡 · **0 🔴**. Fase 1b: **97 de 97 (100%)**
→ 88 ainda reproduzem · 9 🟢 · 0 ⚰️ (**mortalidade de 9,3%**, a maior desde a consolidação).
21 achados originais · 56 candidatos descartados por duplicação. Eixo A: nenhum achado original.
Ver [o sumário executivo](2026-10-02/index.md).

### Agnosticismo de Stack (Eixo A) — 0

Varredura integral: 124 linhas de hit → 23 candidatos → **0 violações originais**. Dezessete dos 23
são itens do banco que seguem abertos. O eixo não tem mais o que descobrir em `agents/` e
`commands/` — tem o que executar. Detalhe em [01-agnosticismo-de-stack.md](2026-10-02/01-agnosticismo-de-stack.md).

### Referências e Consistência (`ref-*`, `docs-sync-*`) — 5

- `docs-sync-user-data-keep-root-omits-plugins-and-names-wrong-repo-only-skill` — **HIGH** — alvo: `CLAUDE-md/user-data.md` — `:105` diz que `KEEP_ROOT` é `agents scripts skills templates commands`, mas `install.sh:400` traz também `plugins`; `:99` nomeia `release-prep` como skill repo-only quando o symlink aponta para a skill distribuída (o repo-only é `repo-release-prep`, cuja colisão de nome já bloqueou um `devteam bind`); a tabela de exclusões não tem linha para `tests/`, `infra/`, `packaging/` nem `app/` — [report](2026-10-02/02-referencias-e-consistencia.md)
- `ref-relayout-quality-skills-list-cites-seven-nonexistent-shared-paths` — **MEDIUM-HIGH** — alvo: `commands/relayout.md` — `:35` ("Quality skills to apply before declaring done") lista 8 skills em `skills/shared/`, das quais só `frontend-done-checklist` existe ali; as outras 7 moram em `skills/design/*` e `skills/architecture/*` desde `c3f91be` (2026-08-09), então o relayout fecha sem os checks de design system, acessibilidade, CSS e padrões de componente — [report](2026-10-02/02-referencias-e-consistencia.md)
- `ref-orphan-skill-scan-blind-to-directory-form-skill-refs` — **MEDIUM-HIGH** — alvo: `helpers/orphan-skill-scan.sh` — `:72` casa só `skills/…/SKILL.md`, então toda referência na forma de diretório escapa da Fase 1 do scanner; com os 7 caminhos mortos de `relayout.md:35` na árvore o scan imprimiu `clean ✓`, e é por isso que eles sobreviveram 54 dias, três auditorias e centenas de hooks `Stop` — [report](2026-10-02/02-referencias-e-consistencia.md)
- `docs-sync-preferences-sync-lint-two-of-five-mirrors-key-presence-only` — **LOW-MEDIUM** — alvo: `helpers/preferences-sync-lint.sh` — `:28-31` tem `MIRRORS` com 2 dos 5 espelhos que `CLAUDE.md` lista, e `:58` só testa presença do nome da chave; o heredoc do `install.sh` — o único mirror que já driftou (`qa_browser`) — e o par `docs/user-preferences*.md` ficam fora do gate. **Refina:** `docs-sync-preferences-mirror-registry-names-readmes-omits-docs-pair` (o pai trata do registro no `CLAUDE.md`, este do gate) — [report](2026-10-02/02-referencias-e-consistencia.md)
- `ref-hooks-md-library-rows-omit-data-dirs-sh-sourced-by-ten-scripts` — **LOW-MEDIUM** — alvo: `CLAUDE-md/hooks.md` — `scripts/hooks/lib/` tem 10 arquivos e `data-dirs.sh` é o único sem linha "Shared library", apesar de ser o de maior fan-in (10 scripts) e de definir a resolução de `state-dir`/`memory-dir` entre layout 1 e 2 (ADR-0013). **Refina:** `ref-claude-md-hook-files-map-and-file-structure-omit-scripts-hooks-lib-session-summary-detect-shared-dep-of-two-hooks` (fan-in 2 lá, 10 aqui) — [report](2026-10-02/02-referencias-e-consistencia.md)

### Fluxos, Comandos e Automação (`flow-*`, `auto-*`) — 7

- `flow-install-cli-orphan-body-outside-main-aborts-every-run` — **HIGH** — alvo: `scripts/install-cli.sh` — `2b410af` colou 52 linhas (`:163-214`) fora de `main()` usando `$SOURCE`/`$VERSION`/`$CLI_HOME`/`$BIN_DIR`/`$PYTHON`, que o refactor anterior tornou locais minúsculas; sob `set -u` o script morre com `line 163: SOURCE: unbound variable` (reproduzido), `bash -n` passa, `test_install_cli.py` dá 8 falhas de 9 — o canal macOS/Linux sem Homebrew (ADR-0028) está 100% quebrado e o CI está vermelho no commit; a cópia de `auth-config.json` que o commit queria adicionar ficou no bloco morto — [report](2026-10-02/03-fluxos-e-comandos.md) — 🟢 **Resolved:** 2026-10-10 — resolvido por `5dcf340` ("fix(cli): remove stale duplicate install code from install-cli.sh"); no `HEAD` `bash scripts/install-cli.sh --help` sai 0, `main()` abre em `:27` e fecha em `:163`, e `:165` é `main "$@"` — não há corpo órfão
- `flow-store-install-ships-dev-auth-config-into-core-despite-sr-27` — **HIGH** — alvo: `packaging/windows-cli/build.py` — `committed_tree` (`:60-75,109`) copia `scripts/` inteiro sem `apply_strip`, e `install-cli.sh` faz o mesmo via `--from`; `store.py` não filtra, então `auth-config.dev.json` chega ao core e `entitlement.py:98-101,222-234` sobrescreve `environment` com `dev` — reproduzido: `devteam auth check --json` devolve `"environment": "dev"`, contra a garantia SR-27, e `04-packaging.sh:852` sai verde porque só inspeciona a árvore stripada — [report](2026-10-02/03-fluxos-e-comandos.md)
- `auto-release-workflow-has-no-guard-for-auth-config-placeholders` — **MEDIUM-HIGH** — alvo: `.github/workflows/release.yml` — `grep 'REPLACE-ME\|auth-config\|gate_mode'` sai vazio; nenhum job da tag preenche nem verifica os três `REPLACE-ME-PROD-*` de `scripts/lib/auth-config.json`, que `entitlement.py:141` usa para marcar `configured: false` — uma tag publicada hoje distribui o CLI nos três canais com login impossível, e quando `gate_mode` virar `enforce` todos os usuários ficam bloqueados — [report](2026-10-02/03-fluxos-e-comandos.md)
- `flow-install-provider-gate-fallback-fails-open-without-gate-lib` — **MEDIUM** — alvo: `scripts/install-provider.sh` — `:118-125` tem o fallback de gate de conta sem `else`: sem `devteam` no PATH não há gate, com crash ou exit 3/4 o corpo não traz `gate_mode`, e um JSON reformatado quebra o `grep` — um release em `enforce` se comporta como `allow`, contra o que `scripts/lib/auth-gate.sh:11-13` promete (SR-42) e na mesma classe de lacuna de paridade da ADR-0022 — [report](2026-10-02/03-fluxos-e-comandos.md)
- `flow-02c-double-dash-counted-as-scope-lets-npm-full-suite-through` — **MEDIUM** — alvo: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` — `has_scope` aceita `--` como seletor; reproduzido em árvore limpa: `npm test` → exit 2, mas `npm test --` e `npm test -- --coverage` → exit 0, e `-- <flags>` é a forma mais comum de passar opções ao runner, então a suíte completa roda sem nudge — [report](2026-10-02/03-fluxos-e-comandos.md)
- `auto-review-agents-regex-duplicated-in-two-task-board-hooks-no-drift-gate` — **MEDIUM** — alvo: `scripts/hooks/pre-tool-use/04-task-board.sh` — `:33` e `post-tool-use/01-task-board.sh:32` repetem `REVIEW_TYPE_RE` com os quatro revisores, cuja fonte canônica é `review_triggers.py:17`; `grep -rn REVIEW_TYPE_RE tests` sai vazio e `agent-lint.sh` valida só `REVIEW_RESULT_AGENTS` — um revisor novo some do task board em silêncio — [report](2026-10-02/03-fluxos-e-comandos.md)
- `flow-update-md-v3-step-0-drops-documented-health-check-and-yes-flags` — **LOW-MEDIUM** — alvo: `commands/update.md` — `:28-29` documenta `--run-health-check`/`--skip-health-check`, mas o Passo 0 (`:38`, caminho v3 e padrão) manda rodar `devteam update` e **parar**, mapeando só `<version tag>`, `--no`, `--enable-auto` e `--disable-auto`; as linhas que honram as flags (`:133-135,172-174`) ficam no caminho v2, e `--yes` não é mapeado — [report](2026-10-02/03-fluxos-e-comandos.md)

### Agentes e Skills (`agent-*`, `skill-*`) — 3

- `agent-security-specialist-outside-review-result-set-task-board-blind-to-findings` — **MEDIUM-HIGH** — alvo: `agents/security-specialist.md` — `commands/review.md:42` o spawna sempre, com severidades `[CRITICAL]`/`[HIGH]`, mas ele não consta de `agent-lint.sh:115` (`REVIEW_RESULT_AGENTS`), de `review_triggers.py:17` (`REVIEW_AGENTS`), dos dois hooks de task board nem da spec, e seu `## Before You Finish` não pede o marcador `<!-- review-result: findings=N -->` — com `qa-specialist` e `code-reviewer` em `findings=0`, a coluna In Review fecha como aprovada e a vulnerabilidade desaparece do quadro — [report](2026-10-02/04-agentes-e-skills.md)
- `agent-review-agent-roster-hardcoded-in-five-places-no-canonical-home` — **MEDIUM** — alvo: `scripts/lib/devteam/review_triggers.py` — a lista dos quatro revisores vive em duas regexes bash, uma tupla Python, uma variável de lint e `docs/specs/task-board.md:325`, e nenhum gate cruza as cinco; a linha de `CLAUDE.md` sobre o marcador aponta para uma skill que não lista nome algum, e a tabela *Canonical Rule Homes* não tem linha para esse roster — [report](2026-10-02/04-agentes-e-skills.md)
- `agent-no-claude-attribution-restated-in-five-agents-frontend-dev-has-no-commit-rule` — **MEDIUM** — alvo: `agents/frontend-developer.md` — a regra de não-atribuição, cuja casa canônica é `conventional-commits/SKILL.md:44-52`, está reescrita em 5 corpos com 3 redações (`backend-developer:164`, `devops-specialist:177`, `technical-writer:192`, `database-specialist`, `mobile-developer`), enquanto `grep -n commit agents/frontend-developer.md` sai vazio — o agente de implementação de frontend commita sem a convenção e sem o aviso, e dois agentes com a duplicata estão em 211/211 linhas — [report](2026-10-02/04-agentes-e-skills.md)

### Economia de Tokens (`token-*`) — 6

- `token-pretooluse-04-task-board-13-forks-before-marker-exit-every-tool-call` — **MEDIUM-HIGH** — alvo: `scripts/hooks/pre-tool-use/04-task-board.sh` — `:19-20` promete que "no python is forked" para outras ferramentas, mas `ANY_TOOL_RE` (`:49`) casa quase tudo e `:88` faz `source task-board.sh` + `init` (`git rev-parse`, 2 `sed`, 2 subshells) + `session_id` (`grep|head|sed`) **antes** do `[ -f marker ] && exit 0`; medido com `strace`: 14 execves e 31–33 ms por `Read`, contra 4–5 ms do 02b/02c, ~1/3 dos 91 ms do dispatcher, 9–30 s por sessão — [report](2026-10-02/05-economia-tokens.md)
- `token-python-sh-uname-forked-twice-per-source-uncached-on-linux-macos` — **MEDIUM** — alvo: `scripts/lib/python.sh` — `:27` resolve plataforma com `$(uname -s)` dentro de `_dta_is_windows`, chamada em `:75` e `~:111` (2× por `source`), e no Linux/macOS nada é exportado, então o cache nunca se arma; 4 dos 42 execves de um `PreToolUse` de `Read` são `uname`, ~5 ms por `source`, em 8 dispatchers mais `state.sh`/`telemetry-guard.sh`/`self-heal.sh` — `$OSTYPE` é builtin e cobre os três casos (`msys`, `cygwin`, `linux-gnu`) — [report](2026-10-02/05-economia-tokens.md)
- `token-hook-dispatchers-basename-dirname-forks-per-subscript-iteration` — **MEDIUM** — alvo: `scripts/hooks/pre-tool-use.sh` — `~:38` faz `$(basename "$script")` uma vez por arquivo do glob, num filtro que existe justamente para ser barato ("every single tool call", `:29-33`); `strace` de um `Read`: 7 `basename` + 8 `dirname` de 42 execves (~8 ms), e `_disabled-01-check-updates.sh` (89 linhas, morto) custa 1 `basename` por chamada — `${script##*/}` e `${BASH_SOURCE[0]%/*}` resolvem sem processo — [report](2026-10-02/05-economia-tokens.md)
- `token-plan-mode-execution-strategy-gate-duplicates-orchestration-loaded-by-26` — **MEDIUM** — alvo: `skills/shared/plan-mode/SKILL.md` — `:151-206` (56 linhas, 3.202 B de 14.853 B) repetem os cinco passos de `orchestration/SKILL.md:13-48`, incluindo o mesmo `python3 -c` e o mesmo quiz; o gate é exigido só por `software-architect.md:62` e `commands/architect.md:30`, mas o skill é carregado por 7 agentes + 19 comandos, e `interaction-patterns:190` aponta o `plan-mode` como casa canônica enquanto o architect aponta o `orchestration` — duas fontes canônicas, ~83 KB de contexto por rodada. **Refina:** `token-plan-mode-skill-131-lines-loaded-by-7-agents-unconditionally` — [report](2026-10-02/05-economia-tokens.md)
- `token-pretooluse-02c-sed-tr-head-forks-before-runner-gate-on-every-bash-call` — **MEDIUM** — alvo: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` — `:30` (`printf|sed|head`) e `:182` (`tr|sed`) rodam sem nenhum teste prévio por substring de runner, então todo comando `Bash` paga 4 forks; medido: 18 ms num `Bash` trivial contra 5 ms num `Read`, +13 ms por chamada, ~2,6 s a cada 200 — [report](2026-10-02/05-economia-tokens.md)
- `token-02b-telemetry-resolves-state-for-every-bash-call-needs-devteam-substring` — **LOW-MEDIUM** — alvo: `scripts/hooks/pre-tool-use/02b-telemetry.sh` — `:37-39` aceita `Bash` e segue para resolver `MAIN_REPO_ROOT` (`:52-56`), state-dir, prefs e consent guard (`:68-69`) **antes** de `:80-90` conferir `/devteam:` no payload; medido: 29 ms num `Bash` trivial contra 4,5 ms num `Read`, 7 forks por chamada, inclusive com telemetria desligada. **Refina:** `flow-telemetry-pre-tool-use-02-runs-on-every-tool-call-without-batching-or-deduplication-burns-200ms-per-burst-session` — [report](2026-10-02/05-economia-tokens.md)

### Descartados por duplicação — 56

Distribuição: Eixo A 30 (17 pela Porta 5) · B 6 · C 5 · D 6 · E 9. A lista nominal, com porta e
razão, está ao fim de cada relatório de eixo. Dois descartes de tipo distinto ficam registrados aqui:

- **`agent-cloudflare-api-skill-unreachable` caiu na Porta 2 por ser falso positivo do próprio auditor** — a skill é carregada por `devops-specialist`, `backend-developer` e `security-specialist`.
- **`99b-archive-index sem fast-path` e `stop/03c-03d-03e re-forkam git` caíram na Porta 3 contra a lista de hipóteses já refutadas por evidência** — exatamente o que a seção de descartes existe para impedir que o próximo pass redescubra.
- **O regex semente do Eixo A produz 5:1 de ruído** (124 linhas para 23 grupos). Ancorar os termos curtos com `\b` cortaria os falsos positivos de `nest`/`express`/`rails`/`spring` sem perder cobertura.

## 2026-10-10 — Auditoria guardiã (verificação + 5 eixos)

Baseline `349f18c` · baseline anterior `5e338d9` · delta de **62 commits e 183 arquivos**,
concentrados em `app/` (52) e `scripts/lib` (23) — duas subárvores com **uma única menção** nos 287
fingerprints do banco. **Nenhuma marca de execução nova em 8 dias.** Fase 1: **76 de 153 (50%)**
(todos os HIGH/MEDIUM-HIGH + 30% do resto) → 64 ✅ · 6 🟡 · 6 🔴 (**84,2% confirmado, 1,3%
reaberto novo** — as outras 5 🔴 já estavam reabertas). Fase 1b: **109 de 109 (100%)** →
**1,8% de mortalidade** (2 🟢, contra 9,3% no pass anterior). **10 fingerprints abertos mediram
pior que no registro** e 5 precisaram de re-ancoragem. Eixo A: nenhum achado original (124 hits →
23 candidatos → 0 violações, terceiro pass seguido em zero). **3 achados originais** · 30
candidatos descartados de 33. Ver [o sumário executivo](2026-10-10/index.md).

> **Reabertura do pass:** a marca ✅ de 2026-09-11 em
> `docs-sync-reports-index-preamble-declares-archive-index-trigger-less-while-stop-99b-dispatches-it`
> é 🔴 — nenhum commit da janela tocou o alvo, e o preâmbulo deste arquivo (`:23-26`) segue
> afirmando que `helpers/archive-index.sh` não tem gatilho, contra
> `scripts/hooks/stop/99b-archive-index.sh`. **A correção é um pass de execução, não deste.**

### Agnosticismo de Stack (Eixo A) — 0

Varredura integral: 124 linhas de hit → 23 candidatos → **0 violações originais**. Treze caíram
pela regra do próprio eixo (tabelas de detecção, blocos "Example") ou por ruído léxico do regex
(`react` dentro de `reactive`/`Auto-reactivation`), seis pela Porta 5 e quatro pela Porta 3. Os 10
acoplamentos genuínos de `agents/`/`commands/` seguem registrados e abertos. Detalhe em
[01-agnosticismo-de-stack.md](2026-10-10/01-agnosticismo-de-stack.md).

### Referências e Consistência (Eixo B) — 0

Sete gates rodados, todos limpos (um deles limpo errado: `orphan-skill-scan`, cego à forma de
diretório, com os 7 caminhos mortos de `relayout.md:35` na árvore). Checagens mecânicas adicionais
sem achado: `name:` ≠ basename em 0 de 155 skills · 0 nomes duplicados entre categorias · índice do
wiki com 51 entradas e 51 linhas, zero órfãs nos dois sentidos · 29 ADRs sem colisão, e
`scripts/new-adr.sh:74-78` deriva o próximo número do máximo, não da contagem. Seis candidatos
descartados (4 Porta 5, 2 Porta 3) em
[02-referencias-e-consistencia.md](2026-10-10/02-referencias-e-consistencia.md).

### Fluxos, Comandos e Automação (`flow-*`, `auto-*`) — 2

- `auto-ipc-trusted-sender-rule-has-no-gate-only-a-wiki-note-to-grep` — **MEDIUM-HIGH** — alvo: `app/src/main/security.ts` — as quatro casas de registro de IPC passam pelo `trustedHandler` (`ipc.ts:393-394`, `notificationIpc.ts:28-29`, `taskBoardIpc.ts:74-75`, `accountIpc.ts:123`), mas nenhum passo de `05-app.sh` (preflight, pin de node, contrato de scripts, `npm ci`, typecheck, lint, build, testes) lê `ipcMain.handle`; a única proteção é a seção *Gotchas* de `docs/wiki/electron/ipc-channels-need-the-trusted-sender-check.md:45` mandando rodar o grep à mão depois de cada rebase, escrita depois de o incidente já ter acontecido (`:3` — "found by grep only | 2026-09-30"); o check qualifica como `blocking` hoje pela ENFORCEMENT POLICY de `01-lint.sh:11-13` — [report](2026-10-10/03-fluxos-e-comandos.md)
- `auto-stamp-code-signed-cjs-outside-every-js-gate-in-the-tree` — **MEDIUM** — alvo: `.github/scripts/release/stamp-code-signed.cjs` — único arquivo JS/TS da árvore sem gate algum: `app/package.json:15` (`eslint .`) roda com `cwd = app/`, `01-lint.sh:139` (`SHELLCHECK_TARGETS`) só vê `*.sh` e `03-python.sh:16-17` só vê python; é executado duas vezes num release (`release.yml:768`, `:835`) para reescrever `app/src/main/build-info.ts` por um `replace` ancorado na linha literal `export const CODE_SIGNED = false;` (`:21`), então uma reformatação de `build-info.ts:14` mata a tag depois do build assinado do macOS — e os dois renderizadores python do mesmo diretório ganharam `tests/test_release_render.py` exatamente por esse motivo — [report](2026-10-10/03-fluxos-e-comandos.md)

### Agentes e Skills (Eixo D) — 0

Medições dentro dos limites que a árvore declara: maior agente 211 (`AGENT_LIMIT=211`), maior skill
435 (`SKILL_LIMIT=500`), `agent-lint` limpo. Dois candidatos descartados — três agentes no teto
exato já é `agent-three-at-exactly-211-line-ceiling-zero-headroom-for-additions` (Porta 1), e a
suposta segunda casa do protocolo do wiki (`project-context/references/wiki.md`) tem 9 linhas e é
um ponteiro, não cópia (descarte por mérito). Detalhe em
[04-agentes-e-skills.md](2026-10-10/04-agentes-e-skills.md).

### Economia de Tokens (`token-*`) — 1

- `token-wiki-retrieval-index-13-7kb-read-whole-by-18-agents-with-no-cap` — **MEDIUM-HIGH** — alvo: `skills/shared/project-context/SKILL.md` — `docs/wiki/README.md` tem 13.715 B / 51 linhas de índice contra 1.757 B / 6 linhas em 2026-09-27 (`3b9ba317`), **7,8× em 9 dias**, ~269 B por linha, sem inflexão e sem teto; a skill manda **grepar** em `:114` e **ler** em `:151`, e é `:151` que justifica o desenho com "context cost stays flat as the wiki grows" — verdadeiro sob a primeira leitura, falso sob a segunda, que custa ~3.430 tokens por spawn nos 18 agentes que carregam `project-context` e ~24.000 num `/devteam:fullstack`; para o outro índice sempre carregado o repositório já resolveu isso (`SKILL_DESC_LIMIT=95` em `agent-lint.sh:92`), enquanto `wiki-format.md:118` proíbe até contar as entradas — [report](2026-10-10/05-economia-tokens.md)

### Descartados por duplicação — 30 de 33 candidatos

Distribuição: Eixo A 23 (13 pela regra do eixo ou ruído do regex · 6 Porta 5 · 4 Porta 3) ·
B 6 (4 Porta 5 · 2 Porta 3) · C 1 (Porta 5) · D 2 (1 Porta 1 · 1 por mérito) · E 1 (Porta 5).
A lista nominal, com porta e razão, está ao fim de cada relatório de eixo. Três descartes de tipo
distinto ficam registrados aqui:

- **Um gate que valide o índice do wiki contra as entradas em disco caiu na Porta 3** contra
  `auto-no-gate-validates-claude-md-file-structure-tree-against-real-tree-…` (mesma causa raiz,
  mesma remediação). É o descarte mais doloroso do pass: a árvore está limpa hoje — 51 entradas, 51
  linhas, zero órfãs nos dois sentidos — que é exatamente a condição para um check `blocking`, e o
  delta adicionou 12 entradas em um dia. **A execução do fingerprint-pai deve cobrir o wiki no
  mesmo helper.**
- **A quinta recorrência da árvore de File Structure do `CLAUDE.md` caiu na Porta 5** —
  `.github/scripts/release/` enumera 1 de 5 arquivos, `scripts/lib/devteam/` 20 de ~44, e `infra/`
  não tem linha nenhuma apesar de hospedar as Edge Functions que emitem o entitlement assinado da
  ADR-0029.
- **Quatro hipóteses foram refutadas por evidência** e estão listadas em
  `2026-10-10/03-fluxos-e-comandos.md`: o quoting de `cmd.exe` com barra final em
  `shellQuote.ts:62-65` não reproduz · nenhum canal IPC novo do delta está sem guarda · o job
  Windows **verifica** Authenticode (`release.yml:846-866`) · `codex_hooks_merge.py` e
  `permission_rules.py` ficam fora do `compileall` de `03-python.sh:16` mas são importados por
  testes que o mesmo gate roda.

---

## 2026-10-17 — Auditoria guardiã (verificação + 5 eixos)

Baseline `bb0e883`, re-fixado no meio do pass depois que 46 commits entraram sobre o `78c11a6`
original. Delta de **76 commits e 157 arquivos** desde `349f18c`, o maior em `skills/shared` (21)
e `commands/` (30) desde a consolidação: camada de spec (ADR-0037), reuse-lint com escopo e
severidade (ADR-0036), sequência de planejamento (ADR-0035), dois comandos novos
(`/devteam:spec`, `/devteam:sprint`), um sub-script de `Stop` novo (`03f-spec-lint.sh`) e uma
biblioteca de hook nova (`lib/warn-once.sh`). Fase 1: **71 de 142 (50%)** → 66 ✅ · 5 🟡 ·
**0 🔴**. Fase 1b: **111 de 111 (100%)** → **0% de mortalidade**, com os 11 alvos tocados pelo
delta todos reproduzindo. Eixo A: nenhum achado original (125 hits → 2 candidatos → 0 violações).
Ver [o relatório do pass](2026-10-17/index.md).

### References and Consistency (`docs-sync-*`) — 2

- `docs-sync-preferences-retire-checklist-restates-mirror-list-omits-docs-pair-and-invents-readme-row` — **MEDIUM-HIGH** — alvo: `CLAUDE-md/preferences.md` — `:42` manda remover a chave "de todos os espelhos listados em CLAUDE.md § User Preferences" e reescreve a lista errada nos dois sentidos: omite `docs/user-preferences.md` / `docs/user-preferences.pt-BR.md`, que são linhas reais de `CLAUDE.md:395`, e inventa uma "`README.md` worktree table" que não existe (`grep worktree_active README*.md` → vazio); sem gate, uma chave aposentada sobrevive nos dois docs de usuário — [report](2026-10-17/02-referencias-e-consistencia.md)
- `docs-sync-hooks-md-warn-once-library-row-omits-03f-spec-lint-contradicting-line-41` — **MEDIUM** — alvo: `CLAUDE-md/hooks.md` — `:121` diz que `lib/warn-once.sh` é carregada por `03c-reuse-lint.sh` e `03e-adr-gap-check.sh`, enquanto `:41` do mesmo arquivo nomeia os três consumidores e `grep -ln warn-once scripts/hooks/stop/*.sh` confirma `03f-spec-lint.sh:60`; a tabela de bibliotecas é o índice de fan-in e diz dois onde são três — [report](2026-10-17/02-referencias-e-consistencia.md)

### Flows, Commands and Automation (`auto-*`, `flow-*`) — 3

- `auto-03f-spec-lint-warn-signature-omits-worktree-root-silences-sibling-worktrees` — **MEDIUM-HIGH** — alvo: `scripts/hooks/stop/03f-spec-lint.sh` — `:58` assina o aviso só com a saída do lint, que é relativa à raiz (`scripts/lib/spec_lint.py:43`), enquanto o marcador vive no state dir do checkout principal (`lib/warn-once.sh:24`) e é compartilhado por todos os worktrees; o irmão `03c-reuse-lint.sh:52-56` inclui `$REPO_ROOT` com um comentário explicando este risco, e numa onda de `/devteam:sprint` (um worktree por tarefa, em paralelo) o WARN chega a uma tarefa e é silenciado nas outras — [report](2026-10-17/03-fluxos-e-comandos.md)
- `auto-warn-once-reset-never-called-by-03e-and-03f-cleared-warning-never-returns` — **MEDIUM** — alvo: `scripts/hooks/stop/03f-spec-lint.sh` — `grep -rn warn_once_reset scripts/hooks/` devolve uma única chamada (`03c-reuse-lint.sh:46`); `03f` sai limpo em `:13`, `:16`, `:24` e `:35` e `03e` em `:23`, `:33`, `:43` e `:103` sem nunca esquecer a assinatura, então um aviso resolvido e depois reintroduzido com os mesmos bytes fica mudo para sempre, contra o contrato em `lib/warn-once.sh:30-32` — [report](2026-10-17/03-fluxos-e-comandos.md)
- `flow-spec-command-step6-item5-inlined-into-item4-breaking-its-own-cross-reference` — **LOW-MEDIUM** — alvo: `commands/spec.md` — `:53` traz "4. … in one `AskUserQuestion`. 5. Session summary and hand-off …" numa linha só, então o passo de fechamento de sessão não renderiza como item de lista e o "skip items 4 and 5" de `:55` aponta para um item que não existe — [report](2026-10-17/03-fluxos-e-comandos.md)

### Agents and Skills (`skill-*`) — 1

- `skill-spec-gate-touches-accepts-database-layer-with-no-test-author-in-any-track` — **MEDIUM-HIGH** — alvo: `skills/shared/spec-gate/SKILL.md` — `:27` e `scripts/lib/spec_lint.py:21` tratam `database` como layer de primeira classe em `touches` (fora da tupla é ERROR), mas as três listas de autor de teste — `:126`, `:132` ("backend, frontend, and mobile alike") e `commands/spec.md:44` — cobrem três tracks; uma spec `touches: [database]` entra no Step 5 sem agente para spawnar e, ao chegar a `implemented`, dispara o WARN de `check_coverage` (`spec_lint.py:282-293`) a cada `Stop` sobre uma lacuna que nenhum agente tem mandato para fechar — [report](2026-10-17/04-agentes-e-skills.md)

### Token Economy (`token-*`) — 1

- `token-spec-gate-17kb-loaded-whole-by-six-execution-agents-that-scope-two-sections` — **MEDIUM** — alvo: `skills/shared/spec-gate/SKILL.md` — 17.463 B / 248 linhas (102 antes deste delta), 2ª maior skill de `skills/shared/`, sem `references/`; quatro coding agents a carregam inteira por § Scope Lock (1.250 B, 7,2%) e dois test specialists por § Test-First Derivation + § Traceability (2.868 B, 16,4%), o que dá **94.042 B de ~90% fora de escopo** num `/devteam:fullstack` com spec que spawna os seis, multiplicado por tarefa numa onda de sprint — [report](2026-10-17/05-economia-tokens.md)

## 2026-10-24 — Auditoria guardiã (verificação + 5 eixos)

Delta de 98 commits e 704 arquivos desde `bb0e883`, com o working tree carregando 79 arquivos
modificados durante todo o pass — toda evidência foi lida de `git show HEAD:<path>`. Fase 1:
75 de 152 (49,3%) → 61 ✅ · 1 🟢 · 9 🟡 · 4 🔴, **0 reaberta nova**. Fase 1b: 118 de 118 (100%),
mortalidade 0,85%. Eixos C, D e E: nenhum achado original.
Ver [o relatório do pass](2026-10-24/index.md).

### Agnosticismo de Stack (`agent-*`) — 1

- `agent-product-analyst-step6-gates-isolated-infra-on-docker-and-inlines-compose-probe` — **MEDIUM** — alvo: `agents/product-analyst.md` — `:151-155`, sob `## Step 6 — Sprint Generation`, condiciona o modelo de isolamento do Parallel Execution Plan a "the project uses Docker" e inlina `ls docker-compose.yml docker-compose.yaml compose.yml compose.yaml`, duas linhas antes de mandar "do not restate the mechanics"; `agents/setup-assistant.md:66` demonstra o padrão correto, delegando a sonda a `stack-detection` "so no agent re-probes" — [report](2026-10-24/01-agnosticismo-de-stack.md)

### Governança (`gov-*`) — 1

- `gov-interaction-mode-key-ungated-and-undocumented-outside-commands-json` — **MEDIUM-HIGH** — alvo: `scripts/lib/commands.json` — a chave reescreve o corpo de todo comando no render do Codex (`scripts/lib/render_provider.py:223-225,240,332`), decidindo entre rotear para `/plan` e degradar para lista numerada, mas não tem gate (`git grep interaction_mode HEAD -- helpers/ .github/` → vazio) nem menção em `CLAUDE.md`/`CLAUDE-md/` (0 ocorrências); a chave irmã `plan_gate` tem as duas defesas (`CLAUDE-md/commands.md:58`, `helpers/agent-lint.sh:374`) — [report](2026-10-24/02-referencias-e-consistencia.md)
