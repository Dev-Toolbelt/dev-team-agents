# Guardian Audit — 2026-05-16

> **Modo Guardian:** verificação cruzada das 28 marcações registradas em `_index.md` para a passada de **2026-05-15**, com `git log --since="2026-05-15"` e leitura direta dos arquivos.

---

## 1. Resumo Executivo

| Métrica | Valor |
|---------|-------|
| Fingerprints registrados em 2026-05-15 | **28** |
| ✅ Executed (confirmados) | **0** |
| ⚠️ Partial | **0** |
| 🟢 Resolved | **0** |
| Pendentes restantes | **28** (100%) |
| Commits desde 2026-05-15 12:30 | **0** |
| Throughput em 24h | **0%** — janela de implementação sem atividade |
| Drift detectado (claim vs realidade atual) | **0** (todos os fingerprints permanecem aplicáveis) |
| Achados estruturais novos (não constavam em `_index.md`) | **8** |

**Veredito:** janela de 24h sem nenhum commit. O último commit registrado é `0bd74d6 2026-05-15 12:30:00 docs(reports): update _index.md...`. Todos os 28 fingerprints publicados em 2026-05-15 permanecem **pendentes e aplicáveis** — nenhum foi endereçado, e nenhum sofreu drift (porque o repo não foi tocado).

Apesar de ausência de drift "novo", a verificação direta de arquivo desta passada **revelou regressões ocultas que estavam presentes desde 2026-05-15** mas passaram batido na auditoria anterior — especialmente o bug do script `check-fingerprint-uniqueness.sh` (cuja regex matcha **zero** entradas em vez de 63 falsos positivos como reportado) e o bug de comparação de string no fast-path de `04-notifier.sh`.

---

## 2. Estado dos 28 Fingerprints de 2026-05-15

Tabela completa abaixo. Todos permanecem **pendentes** (sem marker `✅ Executed`/`⚠️ Partial`/`🟢 Resolved`).

### 2.1 Referências e Consistência (7) — todos pendentes

| # | Fingerprint | Verificação 2026-05-16 | Status |
|---|-------------|------------------------|--------|
| 1 | `auto-fingerprint-script-matches-body-text-not-entry-line-anchors` | `head -25 scripts/check-fingerprint-uniqueness.sh` mostra regex inalterado; **na realidade matcha 0 entradas, não 63** — ver [01-referencias-e-consistencia.md#1](01-referencias-e-consistencia.md#1) | 🔴 Pendente |
| 2 | `ref-install-fallback-prefs-missing-transcript-multiplier-and-model-max-tokens` | `sed -n '405,460p' scripts/install.sh` confirma ausência; **descoberta nova: o ramo Python TAMBÉM omite as chaves** — sub-escopo expandido | 🔴 Pendente |
| 3 | `ref-templates-dir-shipped-but-not-symlinked-relative-path-broken-from-agent-cwd` | `grep -n "templates" scripts/install.sh` — sem symlink criado para `.claude/templates/`; agentes ainda referenciam path relativo | 🔴 Pendente |
| 4 | `ref-stack-detection-skill-created-but-zero-agent-loads-still-orphan-on-day-of-creation` | `grep -rl "stack-detection" agents commands workflows` retorna 0; skill segue órfã | 🔴 Pendente |
| 5 | `ref-haiku-residual-claude-md-note-after-executed-removal` | `grep -n "Haiku" CLAUDE.md` → linha 63 (não 120 — fragmentação mudou linha): nota residual permanece | 🔴 Pendente |
| 6 | `ref-refactor-command-missing-interaction-patterns-load-despite-yes-no-prompts` | `grep "interaction-patterns" commands/refactor.md` → 0 hits; adoção em commands hoje **3/30** (backend, frontend, update) | 🔴 Pendente |
| 7 | `ref-setup-assistant-violates-quiz-first-rule-multiple-plain-text-prompts` | `agents/setup-assistant.md:120` ainda contém `**yes / no**` | 🔴 Pendente |

### 2.2 Fluxos e Workflows (7) — todos pendentes

| # | Fingerprint | Verificação 2026-05-16 | Status |
|---|-------------|------------------------|--------|
| 1 | `flow-refactor-command-duplicates-workflows-refactor-md-content-with-full-prompts-inline` | `commands/refactor.md` = 152 linhas, `workflows/refactor.md` = 278 — inalterado | 🔴 Pendente |
| 2 | `flow-commit-command-160-lines-pre-commit-gates-extractable-skill` | `wc -l commands/commit.md` = 160 — inalterado | 🔴 Pendente |
| 3 | `flow-install-script-strip-list-stale-misses-new-dev-only-scripts-fingerprint-orphan-template-rollback` | `sed -n '140,150p' scripts/install.sh` confirma: 3 scripts stripped, **mas check-fingerprint-uniqueness.sh e orphan-template-scan.sh ainda passam para usuários** | 🔴 Pendente |
| 4 | `flow-notifier-hardcodes-45-tip-strings-in-bash-array-no-externalized-data` | `sed -n '180,235p' scripts/hooks/stop/04-notifier.sh` confirma 3 arrays inline | 🔴 Pendente |
| 5 | `flow-commit-references-nonexistent-validate-commit-msg-script-dead-conditional` | `commands/commit.md:112` ainda usa path absoluto sem override `DEVTEAM_INSTALL_DIR` | 🔴 Pendente |
| 6 | `flow-ci-fingerprint-check-strict-while-orphan-scan-tolerant-asymmetric-gates` | `cat .github/workflows/ci.yml` — assimetria mantida; **agravante: fingerprint-check está literalmente broken e nunca falha** | 🔴 Pendente |
| 7 | `flow-workflows-plan-template-reference-density-1x-vs-8x-inconsistent-enforcement` | `grep -c "plan-template\|present a Plan\|plan gate" workflows/*.md` revela variação 0×–9× | 🔴 Pendente |

### 2.3 Agentes e Skills (7) — todos pendentes

| # | Fingerprint | Verificação 2026-05-16 | Status |
|---|-------------|------------------------|--------|
| 1 | `agent-setup-assistant-docker-compose-detection-belongs-in-stack-detection-skill` | bloco bash continua inline; `stack-detection` órfã | 🔴 Pendente |
| 2 | `agent-setup-assistant-three-roles-bundled-extractable-health-checker-update-manager` | `wc -l agents/setup-assistant.md` = 238 — inalterado | 🔴 Pendente |
| 3 | `agent-backend-developer-95-line-integration-awareness-section-duplicates-skill-content` | `wc -l agents/backend-developer.md` = 261 — inalterado | 🔴 Pendente |
| 4 | `agent-mobile-developer-ios-android-platform-blocks-60-lines-no-platform-skills` | `wc -l agents/mobile-developer.md` = 263 — inalterado | 🔴 Pendente |
| 5 | `agent-frontend-test-specialist-262-vs-backend-160-asymmetric-decoupled-frontend-block-inlined` | `wc -l agents/frontend-test-specialist.md` = 262 — inalterado | 🔴 Pendente |
| 6 | `agent-code-reviewer-15-item-foundational-rule-longest-in-repo-5-conditional-loads-eager-listed` | `wc -l agents/code-reviewer.md` = 228 — inalterado | 🔴 Pendente |
| 7 | `skill-push-notifications-373-lines-no-references-subdir-while-sister-integrations-extracted-today` | `wc -l skills/integrations/push-notifications/SKILL.md` = 373 — inalterado | 🔴 Pendente |

### 2.4 Economia de Tokens (7) — todos pendentes

| # | Fingerprint | Verificação 2026-05-16 | Status |
|---|-------------|------------------------|--------|
| 1 | `token-setup-assistant-immutability-warning-duplicated-top-and-bottom-30-lines` | `grep -n "Immutability" agents/setup-assistant.md` → linhas 24 + 225; duplicação mantida | 🔴 Pendente |
| 2 | `token-notifier-loads-45-tips-3-languages-emits-1-per-day-99pct-waste` | Confirmado via inspeção de `scripts/hooks/stop/04-notifier.sh:184-235` | 🔴 Pendente |
| 3 | `token-claude-md-425-lines-hook-system-and-commands-table-still-inline-not-fragmented` | `wc -l CLAUDE.md` = 425 — inalterado; commands table (30 entradas) e Hook Files Map ainda inline | 🔴 Pendente |
| 4 | `token-index-md-growing-35-slugs-per-day-archive-script-still-unwritten-after-3-mentions` | `wc -l docs/reports/_index.md` = **509 linhas** (era 464 em 2026-05-15) → **+45 linhas em 24h apenas pela atualização da tabela de Estatísticas** | 🔴 Pendente / **PIOROU +9,7%** |
| 5 | `token-code-reviewer-still-eager-loads-comments-policy-after-lazy-load-fix-applied` | `grep -n "comments-policy" agents/code-reviewer.md` → linha 41 ainda eager-load (apesar de condicional ter sido adicionado) | 🔴 Pendente |
| 6 | `token-worktree-isolation-block-136-duplicate-lines-across-8-coding-agents` | `grep -l "## Worktree Isolation" agents/*.md \| wc -l` = 8 — inalterado | 🔴 Pendente |
| 7 | `token-runbook-skill-new-loads-unreachable-template-path-installed-projects` | `cat skills/shared/runbook/SKILL.md` confirma 3 referências a `templates/runbook-template.md` sem symlink | 🔴 Pendente |

---

## 3. Spot-Check: Drift entre 2026-05-15 e 2026-05-16 (regressões silenciosas)

Embora não tenha havido commit, **duas métricas pioraram** apenas pela atualização do próprio `_index.md`:

| Item | 2026-05-15 | 2026-05-16 | Delta |
|------|------------|------------|-------|
| `_index.md` (linhas) | 464 | **509** | **+45 (+9,7%)** em 24h |
| Fingerprints acumulados | 347 | **347** (sem novos) | — |
| Span da tabela "Fingerprints Registrados" | 380→464→509 em 3 dias | **+34% em 3 dias** | trajetória explosiva |

Projeção: ao pace atual de ~45 linhas/dia (apenas para Statistics, sem novos fingerprints), o `_index.md` cruza 1.000 linhas em **2026-06-06** (21 dias).

---

## 4. Achados Estruturais NOVOS (não constam de `_index.md`)

### 4.1 `check-fingerprint-uniqueness.sh` está **literalmente broken**

Verificado por execução:

```bash
$ bash scripts/check-fingerprint-uniqueness.sh; echo "EXIT=$?"
EXIT=1
```

Mas a saída é **completamente vazia** — e o script **sempre exita 1** (não apenas quando há duplicates). Causa raiz dupla:

1. O regex `'\`[a-z][a-z0-9-]+\`'` (com backticks escapados em single-quotes) **não matcha nenhuma entrada** — testado manualmente:

```bash
$ echo 'hello `test-fp` world' | grep -oE '\`[a-z][a-z0-9-]+\`'
# (zero output)
$ echo 'hello `test-fp` world' | grep -oE '`[a-z][a-z0-9-]+`'
`test-fp`
```

O regex correto exige backticks **literais** (sem `\`).

2. `set -euo pipefail` (linha 4) combinado com `DUPLICATES=$(grep ... | sort | uniq -d)` faz com que o exit 1 do grep (zero matches) seja propagado pelo pipefail e cause **abort do script** antes de chegar no `if [ -n "$DUPLICATES" ]`. Resultado:

- **0 matches reais** (não 63 falsos positivos como reportado em 2026-05-15)
- Script **sempre exita 1**
- CI step **sem `continue-on-error: true`** ⇒ CI vermelho permanente desde o commit `847da80`
- Provável razão de ninguém ter notado: zero PRs/pushes desde 2026-05-15 12:30 (último commit é o próprio audit anterior)

O fingerprint `auto-fingerprint-script-matches-body-text-not-entry-line-anchors` (2026-05-15) descreveu o bug com sub-escopo incorreto. Refinado em [01-referencias-e-consistencia.md#1](01-referencias-e-consistencia.md#1) com novo fingerprint.

### 4.2 `04-notifier.sh` fast-path está **broken silenciosamente**

`stop.sh` (linha 23, 26) exporta `DEVTEAM_NO_CHANGES=1` (numérico). Sub-scripts 01-03 verificam:

```bash
[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0   # CORRETO
```

Mas `04-notifier.sh:88`:

```bash
if [ "${DEVTEAM_NO_CHANGES:-false}" = "true" ] && [ "${STATE_DATE:-}" = "${TODAY:-}" ]; then
    exit 0
```

A comparação `"1" = "true"` **sempre falha**. O fast-path **nunca dispara**. Confirmado:

```bash
$ DEVTEAM_NO_CHANGES=1 bash -c '[[ "${DEVTEAM_NO_CHANGES:-false}" = "true" ]] && echo YES || echo NO'
NO
```

O fingerprint pendente `flow-no-stop-hook-04-notifier-fast-path-still-after-2026-05-13` foi marcado ✅ Executed em 2026-05-14 — **promoção incorreta**. Detalhes em [02-fluxos-e-workflows.md#1](02-fluxos-e-workflows.md#1).

### 4.3 Stack-agnosticism — **1 violação NOVA**

Sweep de `agents/*.md` com regex `prefer (postgres|...)|defaults? to (docker|kubernetes|...)|don't recommend`:

- ✅ `agents/devops-specialist.md` — fingerprint `agent-devops-specialist-violates-stack-agnostic-rule-with-docker-first-bias` (2026-05-13) marcado ✅; corpo do agente limpo, mas **descrição linha 8 ainda lista defaults** ("Docker Compose for small teams, Kubernetes for distributed systems, serverless for event-driven workloads") — sub-escopo a reabrir.
- 🔴 **NOVO:** `agents/software-architect.md:117` — `"Don't recommend Kubernetes when Docker Compose on a VPS will handle the load"` — espelho exato da violação que foi removida do devops-specialist. Padrão de bias migrado, não eliminado.

Detalhes em [01-referencias-e-consistencia.md#2](01-referencias-e-consistencia.md#2).

### 4.4 Templates órfãos detectados pelo novo scanner

`bash scripts/orphan-template-scan.sh` (criado em 2026-05-15) reporta:

```
ACTION REQUIRED — Orphan templates (no agent/skill/command references):
  · templates/adr-template.md
  · templates/backlog-template.md
```

Os 2 templates foram criados em commit `c207e3f` (2026-05-13) mas **nenhuma skill/agent/command os referencia**. ADRs são criados via `scripts/new-adr.sh` que **não consulta** o template físico (gera template inline via heredoc). O `backlog-template.md` é referenciado apenas via skill `backlog-template` (carregada por `product-analyst`), mas a skill carrega o arquivo dela mesma — não o template.

Detalhes em [01-referencias-e-consistencia.md#4](01-referencias-e-consistencia.md#4).

### 4.5 Skill `stack-detection` ainda órfã (2ª passada)

Sem mudança desde 2026-05-15. Os 4 candidatos canônicos (setup-assistant, software-architect, database-specialist, devops-specialist) continuam com heurística inline. **Cross-link** com fingerprint #1 da seção 2.3 (setup-assistant inline detection).

### 4.6 Duplicate loads ainda presentes

Mesmos 2 duplicate loads reportados em 2026-05-15:

- `agents/ui-ux-designer.md` carrega `skills/design/design-system-audit/SKILL.md` mais de uma vez
- `commands/update.md` carrega `skills/shared/interaction-patterns/SKILL.md` mais de uma vez

Sem deduplicação em 24h. Detalhes em [04-economia-tokens.md#5](04-economia-tokens.md#5).

### 4.7 `session-start.sh` monolítico (assimetria com Stop dispatcher)

`scripts/hooks/session-start.sh` (118 linhas) é monolítico — sem padrão modular `session-start/01-*`, `02-*` como `scripts/hooks/stop/`. Cresceu para acomodar leitura de prefs, detecção de stale, gating de notificações; tornou-se difícil de testar isoladamente.

Detalhes em [02-fluxos-e-workflows.md#5](02-fluxos-e-workflows.md#5).

### 4.8 `scripts/hooks/pre-tool-use/01-check-updates.sh` = 195 linhas

3º maior script do repo (depois de install.sh=503 e 04-notifier.sh=240). Acumula 4 responsabilidades: leitura de prefs, fetch GitHub, cache TTL, semver compare. Candidato natural à fragmentação.

Detalhes em [02-fluxos-e-workflows.md#3](02-fluxos-e-workflows.md#3).

---

## 5. Promoções históricas adicionais

Nenhuma. Sem commits na janela 2026-05-15 → 2026-05-16, não há fingerprints anteriores executados nesta passada.

---

## 6. Conclusão Guardian

- 🔴 **Throughput 0%** — janela vazia de commits.
- 🔴 **28 fingerprints pendentes** + drift de `_index.md` +9,7%.
- 🆕 **8 achados estruturais novos** — 2 bugs cobertos (fingerprint regex broken + notifier fast-path string mismatch), 1 nova violação de stack-agnosticism, 2 templates órfãos, 1 skill órfã reconfirmada, 2 duplicate loads pendentes, 2 scripts monolíticos.
- 📊 **Promoções incorretas detectadas:** `flow-no-stop-hook-04-notifier-fast-path` (2026-05-13) marcado ✅ Executed em 2026-05-14 mas comparação de string está broken — deveria ser ⚠️ Partial.

> Próxima passada (2026-05-17) deverá focar em: (a) commit de qualquer um dos 28 pendentes para reativar throughput, (b) fix do regex de `check-fingerprint-uniqueness.sh`, (c) fix do fast-path de `04-notifier.sh`, (d) wiring de `stack-detection` em 4 agentes.

---

## 7. Recomendação de reabertura de marcações

| Fingerprint | Marcação atual | Recomendação Guardian | Razão |
|-------------|----------------|------------------------|-------|
| `flow-no-stop-hook-04-notifier-fast-path-still-after-2026-05-13` (2026-05-14) | ✅ Executed | **⚠️ Partial** | Código presente em 04-notifier.sh:88 mas comparação `"1" = "true"` nunca dispara — fast-path inerte |
| `auto-fingerprint-script-matches-body-text-not-entry-line-anchors` (2026-05-15) | (sem marker) | **Reabrir com sub-escopo** | Diagnóstico errado: regex não matcha 63 falsos positivos, matcha **zero** — CI gate é no-op total |
