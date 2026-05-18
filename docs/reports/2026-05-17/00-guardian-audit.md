# Guardian Audit — 2026-05-17

> **Modo Guardian:** verificação cruzada das 26 marcações registradas em `_index.md` para a passada de **2026-05-16**, com `git log --since="2026-05-16"` e leitura direta de arquivos.

---

## 1. Resumo Executivo

| Métrica | Valor |
|---------|-------|
| Fingerprints registrados em 2026-05-16 | **26** |
| ✅ Executed (confirmados) | **0** |
| ⚠️ Partial | **0** |
| 🟢 Resolved | **0** |
| ↩️ Reverted | **0** |
| Pendentes restantes | **26** (100%) |
| Commits desde 2026-05-16 12:30:00 | **4** (`8b9c48b`, `7ea8a74`, `08e80dc`, `8c564bd`) |
| Throughput em 24h | **0%** — todos os commits foram features novas ou doc-sync, **nenhum endereçou um fingerprint pendente** |
| Drift detectado (claim vs realidade atual) | **2** drifts numéricos (line numbers em software-architect.md mudaram de 117 → 143 após inserção de Workflow Detection) |
| Achados estruturais novos (não constavam em `_index.md`) | **5** — quatro deles introduzidos PELOS commits desta janela |

**Veredito:** janela 24h teve **4 commits**, mas todos voltados a **adicionar superfície nova** (Workflow Detection no software-architect, Composition Root no design-patterns + backend/frontend developers, atualização do `_index.md`, ingestão de relatórios atrasados de 2026-05-15/16) — **zero commits fix-only**. Os 26 fingerprints de 2026-05-16 permanecem **integralmente pendentes**.

Pior: três dos quatro commits (`8b9c48b`, `8c564bd`, `08e80dc`) **agravam** problemas de fingerprints pendentes:

- `8c564bd` aumenta `agents/software-architect.md` em **25 linhas** (ainda dentro do cap de 200, mas cresce token-cost em fan-out × 9 commands)
- `8b9c48b` adiciona **100 linhas** a `skills/architecture/design-patterns/SKILL.md` (244 linhas, agora 4ª maior do repo)
- `08e80dc` cresce `_index.md` de 509 → **552 linhas** (+43 linhas em 24h, 6ª passada consecutiva sem rotação)

---

## 2. Estado dos 26 Fingerprints de 2026-05-16

Todos permanecem **pendentes** (sem marker `✅ Executed`/`⚠️ Partial`/`🟢 Resolved`/`↩️ Reverted`).

### 2.1 Referências e Consistência (7) — todos pendentes

| # | Fingerprint | Verificação 2026-05-17 | Status |
|---|-------------|------------------------|--------|
| 1 | `auto-fingerprint-script-regex-actually-matches-zero-entries-CI-gate-permanent-no-op` | **Reclassificação:** rerun de `grep -oE '\`[a-z][a-z0-9-]+\`' docs/reports/_index.md \| wc -l` retorna **568 matches** (não 0). O claim de 2026-05-16 estava errado — a regex matcha pares de backticks, mas **gera falsos positivos** (568 candidatos, ~30 fingerprints únicos reais), exatamente como apontado em 2026-05-15. CI gate é **rumoroso**, não inerte. | 🔴 Pendente / **claim 2026-05-16 incorreto** |
| 2 | `ref-software-architect-line-117-kubernetes-docker-compose-vps-stack-bias-mirrors-devops-fix` | `grep -n "Don't recommend Kubernetes" agents/software-architect.md` → **linha 143** (era 117; deslocada +25 por inserção de Workflow Detection em `8c564bd`). Texto idêntico. Drift de line number, não de conteúdo. | 🔴 Pendente / **drift numérico** |
| 3 | `ref-devops-specialist-description-line-8-still-lists-deployment-defaults-after-body-fix` | `head -10 agents/devops-specialist.md` confirma linha 4 (description) e linha 9 (body) **ambas** prescrevem "Docker Compose for small teams, Kubernetes for distributed systems, serverless..." — inalterado. | 🔴 Pendente |
| 4 | `ref-templates-adr-and-backlog-orphan-since-creation-2026-05-13-no-loader-wired` | `bash scripts/orphan-template-scan.sh` continua reportando: `· templates/adr-template.md` + `· templates/backlog-template.md`. | 🔴 Pendente |
| 5 | `ref-install-sh-both-python-and-fallback-branches-miss-transcript-multiplier-and-model-max-tokens` | `grep -n "transcript_multiplier\|model_max_tokens" scripts/install.sh` → **0 hits** em ambos ramos. | 🔴 Pendente |
| 6 | `ref-setup-assistant-uses-templates-plan-template-relative-path-same-root-cause-as-runbook-skill` | `grep -n "templates/plan-template" agents/setup-assistant.md` → linhas **22 e 131** inalteradas. | 🔴 Pendente |
| 7 | `ref-new-adr-script-creates-templates-inline-via-heredoc-ignoring-templates-adr-template-md` | `grep -c "templates/adr-template" scripts/new-adr.sh` → **0**. Heredoc inline mantido. | 🔴 Pendente |

### 2.2 Fluxos e Workflows (8) — todos pendentes

| # | Fingerprint | Verificação 2026-05-17 | Status |
|---|-------------|------------------------|--------|
| 1 | `flow-stop-04-notifier-fast-path-string-comparison-broken-DEVTEAM_NO_CHANGES-1-vs-true` | `scripts/hooks/stop.sh:17-27` continua atribuindo `DEVTEAM_NO_CHANGES=1` (numérico). `scripts/hooks/stop/04-notifier.sh:88` continua comparando contra `"true"` (string literal). Fast-path inerte mantido. **Bug crítico de 24h+ ainda em produção.** | 🔴 Pendente / **CRITICAL** |
| 2 | `flow-stop-no-zombie-state-cleanup-discovery-lock-and-worktree-session-persist-across-sessions` | `grep -rn "discovery-lock\|worktree-session" scripts/hooks/stop/` → **0 hits** | 🔴 Pendente |
| 3 | `flow-pre-tool-use-01-check-updates-195-lines-3rd-largest-script-no-fragmentation` | `wc -l scripts/hooks/pre-tool-use/01-check-updates.sh` = **195** | 🔴 Pendente |
| 4 | `flow-orphan-template-scan-no-mapping-of-suggested-consumer-vs-orphan-skill-scan` | `cat scripts/orphan-template-scan.sh` confirma: emite apenas lista de órfãos, sem suggested consumer. | 🔴 Pendente |
| 5 | `flow-session-start-118-lines-monolithic-no-modular-pattern-asymmetric-with-stop-dispatcher` | `wc -l scripts/hooks/session-start.sh` = **118** | 🔴 Pendente |
| 6 | `flow-pre-compact-hook-43-lines-not-listed-in-claude-md-hook-files-map` | `grep -n "PreCompact" CLAUDE.md` → mencionado, mas sem coluna "Dispatcher". | 🔴 Pendente |
| 7 | `flow-cli-commit-validate-msg-script-skipped-silently-when-missing-no-instructive-error` | `commands/commit.md:112` continua com `if [ -f ... ]; then ...; fi` sem fallback warning. | 🔴 Pendente |
| 8 | `flow-orphan-skill-scan-runs-on-every-stop-and-CI-even-when-skills-untouched` | `.github/workflows/ci.yml:23` segue sem path filter em `paths:`. | 🔴 Pendente |

### 2.3 Agentes e Skills (5) — todos pendentes

| # | Fingerprint | Verificação 2026-05-17 | Status |
|---|-------------|------------------------|--------|
| 1 | `agent-software-architect-anti-overengineering-rule-117-violates-stack-agnostic-mandate` | Mesma violação de Refs #2 — line 117 → 143; texto inalterado. | 🔴 Pendente |
| 2 | `agent-devops-specialist-description-line-8-stack-list-still-prescriptive-after-body-fix` | Mesma do Refs #3; description e body ambos prescritivos. | 🔴 Pendente |
| 3 | `skill-shared-worktree-214-lines-loaded-by-8-coding-agents-no-references-extraction` | `wc -l skills/shared/worktree/SKILL.md` = **214**; `ls skills/shared/worktree/` mostra **apenas SKILL.md** (sem `references/`). | 🔴 Pendente |
| 4 | `agent-setup-assistant-immutability-section-225-238-redundant-with-warning-line-24-duplicate-md-headers` | `grep -n "## Immutability Warning" agents/setup-assistant.md` → linhas **24 e 225**. Duplicação md-header mantida. | 🔴 Pendente |
| 5 | `skill-graphify-setup-277-lines-no-conditional-gate-after-4-passes-no-detection-rule` | `wc -l skills/devops/graphify-setup/SKILL.md` = **277**; sem gate de detecção. | 🔴 Pendente |

### 2.4 Economia de Tokens (6) — todos pendentes

| # | Fingerprint | Verificação 2026-05-17 | Status |
|---|-------------|------------------------|--------|
| 1 | `token-stop-04-notifier-fast-path-broken-burns-80-150ms-per-stop-call-in-conversational-sessions` | Cross-cut com Fluxos #1; bug ainda ativo. | 🔴 Pendente |
| 2 | `token-check-fingerprint-uniqueness-broken-regex-burns-CI-minutes-with-permanent-false-pass` | Cross-cut com Refs #1; reclassificado mas ainda problemático (568 falsos positivos potenciais). | 🔴 Pendente |
| 3 | `token-_index-md-509-lines-grew-45-lines-in-24h-rotation-still-not-actioned-after-5-passes` | `wc -l docs/reports/_index.md` = **552** (era 509). **+43 linhas em 24h.** **6ª passada consecutiva, PIOROU +8,4%.** | 🔴 Pendente / **PIOROU** |
| 4 | `token-CLAUDE-md-425-lines-still-monolithic-after-fase-1-fragmentation-30-line-commands-table-not-extracted` | `wc -l CLAUDE.md` = **425**, inalterado; commands table (36 linhas, 30 entradas) ainda inline. | 🔴 Pendente |
| 5 | `token-orphan-skill-scan-and-template-scan-duplicate-find-passes-on-skills-directory` | `02-orphan-skill-scan.sh` e `02b-orphan-template-scan.sh` rodam consecutivamente em Stop, ambos com `find` em diretórios sobrepostos. | 🔴 Pendente |
| 6 | `token-templates-runbook-79-lines-largest-template-load-broken-by-symlink-100pct-waste-in-installed` | Cross-cut com Refs #6 (path relativo sem symlink). | 🔴 Pendente |

---

## 3. Spot-Check: Drift entre 2026-05-16 e 2026-05-17 (regressões silenciosas)

Apesar dos 4 commits da janela, todas as métricas pioraram:

| Item | 2026-05-16 | 2026-05-17 | Delta |
|------|------------|------------|-------|
| `_index.md` (linhas) | 509 | **552** | **+43 (+8,4%)** em 24h |
| `agents/software-architect.md` (linhas) | 184 | **208** | **+24 (+13%)** por inserção de Workflow Detection |
| `skills/architecture/design-patterns/SKILL.md` (linhas) | 144 | **244** | **+100 (+69%)** por inserção de Composition Root |
| `agents/frontend-developer.md` (linhas) | 232 | **244** | **+12 (+5,2%)** por seção Composition Root nova |
| Fingerprints acumulados | 373 | **373** (sem novos antes deste relatório) | — |

Projeção atualizada: ao pace atual **conservador** de ~43 linhas/dia (apenas Statistics), o `_index.md` cruza 1.000 linhas em **2026-06-07** (21 dias). Se contarmos fingerprints novos a cada passada (~25–50), o pace agressivo coloca a marca em **~13 dias**.

---

## 4. Achados Estruturais NOVOS (não constam em `_index.md`)

### 4.1 `commands/architect.md` description grew but CLAUDE.md table didn't — doc drift introduced today

`commands/architect.md` (commit `8c564bd`) ganhou nova descrição:

> "The agent will automatically detect the appropriate workflow from the user's request (...) Falls back to the maintenance workflow when no clear signal is found."

`CLAUDE.md:194` (tabela "User-Invocable Commands") ainda diz apenas:

> `/devteam:architect` | `software-architect` | Architecture decisions, ADRs, trade-offs

Doc drift introduzido na mesma janela. Promovido a fingerprint em `01-referencias-e-consistencia.md` (`ref-claude-md-architect-command-description-out-of-sync-with-commands-architect-md-after-workflow-detection-introduction`).

### 4.2 Workflow Detection inlined em software-architect duplica conceito de `skills/shared/spawn-classifier/SKILL.md`

`agents/software-architect.md:45-69` (commit `8c564bd`) adiciona tabela de 25 linhas de "Intent signals → Workflow to load". Conceitualmente, é uma **classificação de intenção** — exatamente o que `skills/shared/spawn-classifier/SKILL.md` (89 linhas) já existe para fazer, com a diferença que spawn-classifier mapeia para **agents condicionais** em vez de **workflows**.

Decisão arquitetural não documentada: por que classificar workflow inline em vez de extrair para `skills/shared/workflow-detection/SKILL.md` simétrica? Promovido a fingerprint em `03-agentes-e-skills.md`.

### 4.3 Composition Root section em `frontend-developer.md` enumera Angular/Vue/React explicitamente

`agents/frontend-developer.md:143-153` (commit `8b9c48b`) adiciona seção mencionando:

- "Angular `NgModule` / standalone providers"
- "Vue `app.provide()` / Pinia store registration"
- "React context tree or service layer for a large SPA"

Isso é **stack bias dentro da diretriz core do agente** — viola CLAUDE.md:124 "Stack-agnostic: no hardcoded framework, language, or tool references in agent core behavior". Cross-cut com a mesma classe de violação que `devops-specialist` (corrigida em 2026-05-13 mas espelhada em `software-architect` em 2026-05-16 e agora **introduzida novamente** em `frontend-developer` em 2026-05-17). Promovido a fingerprint em `01-referencias-e-consistencia.md`.

### 4.4 `agents/backend-developer.md` recebeu apenas 1 linha sobre Composition Root, enquanto `frontend-developer.md` recebeu seção de 12 linhas — tratamento assimétrico do mesmo pattern

`8b9c48b` adicionou em `backend-developer.md`:

```
- "Use DI (Dependency Injection) over hard-coded singletons; load Composition Root pattern from design-patterns skill when wiring services"
```

Mas em `frontend-developer.md`, **12 linhas** com bullets, regra explícita e exemplos. Sem justificativa para a assimetria — Composition Root é igualmente relevante em backend (Spring DI, NestJS providers, Laravel container). Promovido a fingerprint em `03-agentes-e-skills.md`.

### 4.5 `_index.md` cresceu 43 linhas em 24h sem novos fingerprints — só pela atualização da tabela "Estatísticas"

Inspeção: commit `08e80dc` adicionou **88 linhas** ao `_index.md`, mas o **delta líquido** foi +43 (porque também removeu 45 linhas redundantes em outras seções). Causa: a tabela "Estatísticas" segue acumulando, e a coluna "Executadas / Revertidas" carrega prosa cada vez maior. Sub-escopo do fingerprint pendente `token-_index-md-509-lines-grew-...` — mas o **mecanismo de growth** mudou: não é só fingerprint, é prosa cumulativa em statistics.

---

## 5. Resumo Final do Estado de 2026-05-16

```
26 fingerprints publicados
 0 ✅ Executed
 0 ⚠️ Partial
 0 🟢 Resolved
 0 ↩️ Reverted
26 🔴 Pendentes (100%)

 4 commits na janela 24h
 0 endereçaram fingerprints
 4 introduziram drift (1 doc-sync, 3 features novas)

 5 achados estruturais novos
 4 deles causados pelos commits da janela
```

**Recomendação Guardian:** congelar **toda adição de funcionalidade nova em agents/ e skills/** até throughput de pendentes voltar acima de 30%. Pace acumulado de 5 dias (2026-05-13 → 2026-05-17):

- 2026-05-13 → 2026-05-14: 68% throughput
- 2026-05-14 → 2026-05-15: 88% throughput (recorde)
- 2026-05-15 → 2026-05-16: 0% throughput
- 2026-05-16 → 2026-05-17: 0% throughput
- **Tendência:** queda livre em janela de 48h após o pico de 2026-05-15.

A queda coincide exatamente com a inflexão "features novas em vez de fixes" detectada nos 4 commits desta janela.

---

**Fim do Guardian Audit 2026-05-17.**
