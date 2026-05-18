# Relatório 2026-05-17 — Fluxos e Workflows

> 12ª passada de auditoria. Foco: novo fluxo de **Workflow Detection** introduzido hoje em `software-architect.md` (commit `8c564bd`), assimetrias remanescentes em hooks Stop/PreCompact, scripts de governance que dispararam silenciosamente nas últimas janelas, e gaps de fast-path persistentes desde 2026-05-13.

---

## 1. `flow-software-architect-workflow-detection-classification-has-no-tests-no-fixtures-no-validation-pipeline-no-precedence-rules`

**Categoria:** novo fluxo introduzido sem garantias de correção
**Severidade:** HIGH

A tabela "Intent signals → Workflow" em `agents/software-architect.md:48-60` (commit `8c564bd`) define 10 mapeamentos heurísticos baseados em keywords case-insensitive. **Detection rule #2** diz: "If multiple signals match, pick the workflow whose signals are most dominant in the request."

Problemas estruturais:

1. **Não há definição de "dominant"** — frequência? primeiro match? número de keywords distintas? O agent terá que improvisar a cada invocação, gerando classificações divergentes para o mesmo input.
2. **Não há fixture suite** em `scripts/` ou `tests/` que valide a classificação para inputs típicos. Comparativo: `agent-lint.sh` (185 linhas) valida frontmatter, `check-fingerprint-uniqueness.sh` valida slugs — mas nada valida **a próprio classificação semântica** introduzida hoje.
3. **Sem mecanismo de versionamento da tabela** — quando keywords forem adicionadas/removidas, não há changelog específico, nem ADR registrando a evolução.
4. **Ambiguidade de keywords overlap:** "refactor" + "security" pode aparecer no mesmo request ("refactor para corrigir vulnerabilidade") — qual workflow vence? A tabela define `security-patch.md` se "vulnerability" estiver presente, e `refactor.md` se "refactor" estiver — ambos podem coocorrer.

**Impacto positivo da correção:** criar `scripts/test-workflow-detection.sh` com 20–30 fixtures (mapeando request texto → workflow esperado) + ADR registrando a heurística como **versionada**. Reduz risco de regressão silenciosa quando a tabela for editada.
**Impacto negativo:** custo upfront de criar test harness (~2h de trabalho); manutenção contínua dos fixtures.

---

## 2. `flow-stop-04-notifier-fast-path-bug-still-pending-3-passes-7-days-after-first-Executed-marker-CRITICAL-reopen-from-2026-05-14`

**Categoria:** bug crítico de produção em fast-path
**Severidade:** CRITICAL

Histórico do fingerprint:

| Data | Estado | Evidência |
|------|--------|-----------|
| 2026-05-13 | Identificado como pendente (sub-escopo de `flow-stop-dispatcher-runs-all-4-sub-scripts-without-fast-path`) | — |
| 2026-05-14 | Marcado ✅ **Executed: 2026-05-15** em `_index.md:193` | commit `f96f3cd` adicionou `DEVTEAM_NO_CHANGES` |
| 2026-05-16 | Reaberto como **CRITICAL** após Guardian descobrir bug de comparação `"1" = "true"` (sempre falso) | — |
| 2026-05-17 (hoje) | **AINDA quebrado** após mais 24h, **zero ações na janela** | — |

Verificação atual:

```bash
$ grep -n "DEVTEAM_NO_CHANGES" scripts/hooks/stop.sh
17:# DEVTEAM_NO_CHANGES=1 means: no staged/unstaged changes AND no commits today.
18:DEVTEAM_NO_CHANGES=0
23:            DEVTEAM_NO_CHANGES=1
27:export DEVTEAM_NO_CHANGES

$ grep -n "DEVTEAM_NO_CHANGES" scripts/hooks/stop/04-notifier.sh
86:# If no file changes were detected (DEVTEAM_NO_CHANGES=true) AND the tip for
88:if [ "${DEVTEAM_NO_CHANGES:-false}" = "true" ] && [ "${STATE_DATE:-}" = "${TODAY:-}" ]; then
```

Comparação de string literal: `"1" = "true"` é **sempre falso**. Em **toda sessão sem mudanças**, o fast-path do notifier é pulado e os ~80–150ms de overhead se acumulam.

Quantificação: ~10 sessões/dia × 30 dias × ~110ms = **33s/mês de wall-clock desperdiçado**. Trivial em isolamento, **mas é o tipo de bug que indica falha de QA em hot path** — e revela que o fingerprint marcado ✅ Executed nunca foi validado por execução.

**Impacto positivo da correção:** trocar `= "true"` por `-eq 1` ou inicializar `DEVTEAM_NO_CHANGES=true` em `stop.sh:18`. 1 linha alterada, fast-path restaurado.
**Impacto negativo:** zero.

**Recomendação Guardian:** padronizar **boolean ENV semantics** no projeto. Decisão entre numérico (`0/1`) ou string (`true/false`) tem que ser explicitada em ADR. Hoje o codebase mistura ambos em scripts adjacentes.

---

## 3. `flow-architect-command-now-routes-workflows-but-fix-fullstack-refactor-mobile-design-still-pick-static-workflow-asymmetric-router-pattern`

**Categoria:** assimetria de routing entre commands
**Severidade:** HIGH

Após commit `8c564bd`, `/devteam:architect` agora atua como **workflow router dinâmico** via tabela de intent signals.

Compare com outros commands que **também** poderiam beneficiar de detection:

| Command | Trigger | Hoje | Deveria? |
|---------|---------|------|----------|
| `/devteam:fix` | bug, regressão | spawneia backend/frontend/mobile + test-specialist (estático) | `bug-fix.md` workflow |
| `/devteam:refactor` | refatoração | spawneia 9 agents em fases (estático) | `refactor.md` workflow (já tem) |
| `/devteam:fullstack` | feature E2E | backend + frontend + database/ui-ux¹ | `fullstack.md` workflow (já tem) |
| `/devteam:design` | UX | spawneia ui-ux-designer (estático) | `design.md` workflow (já tem) |
| `/devteam:mobile` | mobile | mobile-developer + ui-ux¹ (estático) | `mobile.md` workflow (já tem) |
| `/devteam:security` | audit | security + architect (estático) | `security-patch.md` (já tem) |

**Inconsistência arquitetural:** o `software-architect` é o único agent que detecta workflow — todos os outros commands têm workflow **embedded staticamente** no command file. Mas o usuário pode invocar `/devteam:architect "refactor the auth layer"` (workflow detection → refactor.md) **ou** `/devteam:refactor "refactor the auth layer"` (workflow estático → refactor.md). Mesma intent, dois caminhos.

**Pergunta de design não-respondida:** workflow detection é responsabilidade do **command** (entry point) ou do **agent** (executor)? Hoje a resposta é "ambos, dependendo".

**Impacto positivo da correção:** extrair workflow detection para `skills/shared/workflow-detection/SKILL.md` (cross-cut com Referências #3) e fazer **todos os commands de entrada multi-agent** carregarem essa skill — incluindo o próprio `software-architect`. Lógica fica em 1 lugar.
**Impacto negativo:** mudança maior; requer ADR; expansão para mais commands.

---

## 4. `flow-orphan-template-scan-runs-in-stop-but-only-checks-references-not-resolvability-masks-templates-broken-by-relative-path`

**Categoria:** scan inflate confidence / governance leak
**Severidade:** MEDIUM

`scripts/orphan-template-scan.sh` é registrado como **02b-orphan-template-scan.sh** no Stop dispatcher. Sua lógica:

```bash
CONSUMERS="agents skills commands workflows scripts"
# para cada template em templates/, verifica se há grep -r "templates/<name>" em CONSUMERS
```

Cross-check com fingerprint pendente `ref-templates-dir-shipped-but-not-symlinked-relative-path-broken-from-agent-cwd` (2026-05-15) revela:

| Template | Detected as orphan? | Actually reachable in install? |
|----------|---------------------|--------------------------------|
| `adr-template.md` | YES (orphan) | NO (broken — no consumer) |
| `backlog-template.md` | YES (orphan) | NO (broken — no consumer) |
| `plan-template.md` | NO (referenced) | **NO (path relativo sem symlink)** |
| `runbook-template.md` | NO (referenced) | **NO (path relativo sem symlink)** |

**Status real:** 100% dos templates inalcançáveis em produção. Scan reporta 50%.

Recomendação operacional: o Stop hook deveria também executar um **resolvability test** após o orphan scan. Sub-script `02c-template-resolvability-check.sh` (~30 linhas) faria `[ -L .claude/templates/<name> ] || echo BROKEN`.

**Impacto positivo da correção:** scan deixa de mascarar problema real. Templates conhecidamente quebrados disparam ACTION REQUIRED no Stop em vez de "OK" silencioso.
**Impacto negativo:** adiciona 1 sub-script ao Stop dispatcher (~30ms overhead/Stop).

---

## 5. `flow-graphify-refresh-script-166-lines-distributed-but-loaded-by-no-stop-dispatcher-sub-script-orphan-trigger-when-graphify-disabled`

**Categoria:** script de pipeline inativo / orphan trigger
**Severidade:** MEDIUM

`scripts/graphify-refresh.sh` (166 linhas, 5ª maior script do repo) é **distribuído pelo instalador** mas:

```bash
$ ls scripts/hooks/stop/
01-session-summary.sh
02-orphan-skill-scan.sh
02b-orphan-template-scan.sh
03-agent-lint.sh
04-notifier.sh
# Nenhum sub-script invoca graphify-refresh.sh
```

`skills/devops/graphify-setup/SKILL.md:157` instrui o `setup-assistant` a **criar** o sub-script `02-graphify-refresh.sh` no Stop dispatcher **se** Graphify estiver habilitado. Mas isto é **conditional setup** durante onboarding, não regra default.

**Consequências:**
- Em projeto onde Graphify **não** foi habilitado, `graphify-refresh.sh` é dead code distribuído (~3KB inúteis no install)
- Em projeto onde Graphify **foi** habilitado durante setup, o sub-script `02-graphify-refresh.sh` é criado por `setup-assistant` mas **nunca documentado em CLAUDE.md** como item do dispatcher — drift declarativo

Cross-cut com fingerprint pendente `flow-install-script-strip-list-stale-misses-new-dev-only-scripts-fingerprint-orphan-template-rollback` (2026-05-15): o instalador deveria **strip graphify-refresh.sh** se Graphify não estiver habilitado, ou registrá-lo como Stop sub-script se estiver.

**Impacto positivo da correção:** lógica condicional de install fica explícita. Reduz bloat (~3KB) em instalações sem Graphify. Documenta o sub-script no CLAUDE.md quando ativado.
**Impacto negativo:** custo de adicionar branch condicional no `install.sh` (já 503 linhas).

---

## 6. `flow-no-validation-of-workflow-keyword-collisions-between-software-architect-detection-table-and-orphan-skill-scan-spawn-classifier-rules`

**Categoria:** governança / sem cross-validation entre classificadores
**Severidade:** MEDIUM

`agents/software-architect.md:48-60` (commit `8c564bd`) define keywords para classificação de **workflow**.
`skills/shared/spawn-classifier/SKILL.md` (89 linhas) define keywords para classificação de **agent**.

Há overlap conceitual:

| Keyword | Workflow Detection mapeia a | spawn-classifier mapeia a |
|---------|------------------------------|----------------------------|
| `refactor` | `refactor.md` | (eventualmente) `software-architect` first |
| `mobile` | `mobile.md` | `mobile-developer` |
| `security` | `security-patch.md` | `security-specialist` |
| `design` | `design.md` | `ui-ux-designer` |

Mas:
- Nenhum lint cross-valida que as keywords são consistentes
- A tabela do architect pode evoluir sem refletir em spawn-classifier (e vice-versa)
- Não há ADR registrando que **workflows + agents formam um conjunto coordenado**

Recomendação: criar `skills/shared/intent-vocabulary/SKILL.md` como **fonte única** de keywords; tanto workflow detection quanto spawn-classifier importam dessa skill (ou seu conteúdo via inclusão).

**Impacto positivo da correção:** elimina divergência futura. Adicionar keyword nova ("mobile crash" → `bug-fix.md` + `mobile-developer`) é atomic operation.
**Impacto negativo:** introduz 1 skill nova; muda a arquitetura de classificação para hub-and-spoke.

---

## 7. `flow-no-stop-hook-runs-check-fingerprint-uniqueness-after-_index-edit-only-on-CI-after-push-feedback-too-late`

**Categoria:** governance gap / late feedback loop
**Severidade:** MEDIUM

`scripts/check-fingerprint-uniqueness.sh` é executado **apenas pelo CI** (`.github/workflows/ci.yml:23`) após push.

`_index.md` é editado **localmente** durante geração de relatório diário, sem validação. Cenário:

1. Agente escreve relatório com fingerprint `foo-bar-baz` (já existente)
2. Agente edita `_index.md` adicionando o fingerprint sem detectar colisão
3. Commit + push
4. CI roda check-fingerprint-uniqueness — falha
5. Desenvolvedor reverte o commit, refaz

Cinco etapas para descobrir colisão. Se o check rodasse no **Stop hook** após edit de `_index.md`, falha seria detectada antes do commit.

Adicionalmente: cross-cut com fingerprint pendente `auto-fingerprint-script-regex-actually-matches-zero-entries-CI-gate-permanent-no-op` (2026-05-16) que **erroneamente** alegou regex broken. Reclassificação Guardian de hoje mostra que a regex matcha 568 entradas (não 0), mas com falsos positivos.

**Impacto positivo da correção:** feedback antecipado; evita commit + push + revert. Combina com Stop dispatcher para detection local.
**Impacto negativo:** ~50ms adicional/Stop em sessões que editam `_index.md`.

---

## 8. `flow-pre-tool-use-01-check-updates-runs-every-tool-call-but-has-no-rate-limit-beyond-24h-cache-degrades-on-bursts`

**Categoria:** governance / scaling do hook
**Severidade:** LOW

`scripts/hooks/pre-tool-use/01-check-updates.sh` (195 linhas, 3ª maior script) corre **antes de cada tool call**. Tem cache TTL 24h, mas:

1. Em sessão multi-agent com bursts de ferramentas (ex: `/devteam:fullstack` invoca ~40 tool calls em 5 minutos), o cache é **eficaz** mas o overhead de **checar o cache** acumula ~5ms × 40 = 200ms total.
2. Sem early-return: o script sempre completa init antes de validar TTL.

**Impacto positivo da correção:** early-return logic no topo do script (`[ -f cache ] && [ $(...) -lt 86400 ] && exit 0`). Corta overhead em ~80% para tool calls não-primeiras da sessão.
**Impacto negativo:** complica a lógica do script existente (que já está 195 linhas).

---

## Resumo

8 fingerprints originais nesta categoria:

| # | Fingerprint | Severidade |
|---|-------------|------------|
| 1 | `flow-software-architect-workflow-detection-classification-has-no-tests-no-fixtures-no-validation-pipeline-no-precedence-rules` | HIGH |
| 2 | `flow-stop-04-notifier-fast-path-bug-still-pending-3-passes-7-days-after-first-Executed-marker-CRITICAL-reopen-from-2026-05-14` | CRITICAL |
| 3 | `flow-architect-command-now-routes-workflows-but-fix-fullstack-refactor-mobile-design-still-pick-static-workflow-asymmetric-router-pattern` | HIGH |
| 4 | `flow-orphan-template-scan-runs-in-stop-but-only-checks-references-not-resolvability-masks-templates-broken-by-relative-path` | MEDIUM |
| 5 | `flow-graphify-refresh-script-166-lines-distributed-but-loaded-by-no-stop-dispatcher-sub-script-orphan-trigger-when-graphify-disabled` | MEDIUM |
| 6 | `flow-no-validation-of-workflow-keyword-collisions-between-software-architect-detection-table-and-orphan-skill-scan-spawn-classifier-rules` | MEDIUM |
| 7 | `flow-no-stop-hook-runs-check-fingerprint-uniqueness-after-_index-edit-only-on-CI-after-push-feedback-too-late` | MEDIUM |
| 8 | `flow-pre-tool-use-01-check-updates-runs-every-tool-call-but-has-no-rate-limit-beyond-24h-cache-degrades-on-bursts` | LOW |
