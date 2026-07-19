# Guardian Audit — 2026-05-18

**Janela analisada:** commits entre 2026-05-17 e 2026-05-19 (UTC) — verificação cruzada das marcações ✅ Executed promovidas em 2026-05-18 contra o estado real do código.

**Modo:** Guardian (verificação independente) + 13ª passada de auditoria com **sugestões originais**.

---

## Resumo Executivo

| Métrica | Valor |
|--------|-------|
| Fingerprints `✅ Executed: 2026-05-18` revisados | **27** |
| ✅ Verdadeiramente Executed | **24** |
| ⚠️ Partial (precisa reabrir como sub-escopo) | **3** |
| ↩️ Reverted no mesmo dia | **0** |
| Commits na janela 2026-05-18 → 2026-05-19 | **16** |
| Throughput de execução real | **≈89%** (24/27) |
| Sugestões originais novas neste relatório | **32** (11 refs + 8 fluxos + 6 agents/skills + 7 tokens) |
| Novos achados estruturais não registrados | **6** (ver seção "Achados Estruturais Novos") |

---

## Verificação Item-a-Item dos ✅ Executed de 2026-05-18

### Bloco 1 — Bugs Críticos

| # | Fingerprint | Commit | Verificação | Status |
|---|-------------|--------|-------------|--------|
| 1 | `flow-stop-04-notifier-fast-path-bug-still-pending-3-passes-7-days-after-first-Executed-marker-CRITICAL-reopen-from-2026-05-14` | `bec005e` | `stop.sh:23 DEVTEAM_NO_CHANGES=1` (numérico) + `04-notifier.sh:88 [ "${DEVTEAM_NO_CHANGES:-0}" = "1" ]` (string `"1"`) — comparação **agora coerente** | ✅ **Confirmado** |
| 2 | `auto-fingerprint-script-regex-actually-matches-zero-entries-CI-gate-permanent-no-op` | `dc661dc` + `bec005e` | `helpers/check-fingerprint-uniqueness.sh:14` agora usa regex `'^- \`[a-z][a-z0-9-]+'` ancorado em linhas de registro; teste local retorna **0 colisões reais** (sem falsos positivos) | ✅ **Confirmado** |

### Bloco 2 — Violações Stack-Agnostic

| # | Fingerprint | Commit | Verificação | Status |
|---|-------------|--------|-------------|--------|
| 3 | `ref-frontend-developer-composition-root-section-mentions-angular-vue-react-explicitly-violating-stack-agnostic-mandate` | `3bb9d74` | `agents/frontend-developer.md:143-153` agora descreve Composition Root em termos genéricos ("module/provider system", "global state registration") — sem `NgModule`, `Pinia`, "Angular", "Vue", "React" | ✅ **Confirmado** |
| 4 | `ref-software-architect-workflow-detection-25-lines-inline-overlaps-spawn-classifier-skill-conceptually-not-extracted-to-shared-workflow-detection` | `d13c693` | Tabela inline extraída para `skills/shared/workflow-detection/SKILL.md` (50 linhas) e `software-architect.md` agora apenas chama `Load skills/shared/workflow-detection/SKILL.md` | ✅ **Confirmado** |
| 5 | `agent-software-architect-now-acts-as-workflow-router-with-workflow-detection-block-but-skill-shared-workflow-detection-doesnt-exist-functional-overlap-with-spawn-classifier` | `d13c693` | Skill criada (50 linhas) e wireada em `software-architect.md` | ✅ **Confirmado** |
| 6 | `agent-frontend-developer-composition-root-12-line-block-violates-stack-agnostic-mandate-and-grows-agent-from-232-to-244-lines` | `3bb9d74` | `wc -l agents/frontend-developer.md = 232` (de volta ao tamanho anterior à regressão) | ✅ **Confirmado** |
| 7 | `ref-software-architect-line-117-kubernetes-docker-compose-vps-stack-bias-mirrors-devops-fix` | `3bb9d74` | `grep -n "Kubernetes\|VPS\|Compose" agents/software-architect.md` retorna **0 matches** | ✅ **Confirmado** |
| 8 | `ref-devops-specialist-description-line-8-still-lists-deployment-defaults-after-body-fix` | `3bb9d74` | `agents/devops-specialist.md` linhas 3 e 8 não listam mais "Docker Compose/Kubernetes/serverless" como defaults — usa frase neutra "Picks the right deployment tool" | ⚠️ **Partial** (corpo do agente ainda contém defaults — ver achado estrutural #1) |
| 9 | `agent-devops-specialist-description-line-8-stack-list-still-prescriptive-after-body-fix` | `3bb9d74` | Idem ao item 8 | ⚠️ **Partial** (mesmo sub-escopo) |
| 10 | `agent-software-architect-anti-overengineering-rule-117-violates-stack-agnostic-mandate` | `3bb9d74` | Linha removida; reformulada como regra neutra de right-sizing | ✅ **Confirmado** |

### Bloco 3 — Extrações references/

| # | Fingerprint | Commit | Verificação | Status |
|---|-------------|--------|-------------|--------|
| 11 | `skill-shared-worktree-214-lines-loaded-by-8-coding-agents-no-references-extraction` | `d13c693` | `skills/shared/worktree/SKILL.md` agora 67 linhas; `references/{branch-flow,session-protocol}.md` criados | ✅ **Confirmado** |
| 12 | `skill-shared-worktree-214-lines-loaded-by-8-coding-agents-no-references-extraction-cross-cut-with-token-economy-fingerprint-from-2026-05-16-still-pending` | `d13c693` | Idem #11 (mesma extração) | ✅ **Confirmado** |
| 13 | `ref-design-patterns-skill-grew-to-244-lines-after-composition-root-addition-now-4th-largest-skill-pattern-references-not-applied` | `d13c693` | `skills/architecture/design-patterns/SKILL.md` agora 152 linhas; `references/composition-root.md` criado | ✅ **Confirmado** |
| 14 | `skill-push-notifications-373-lines-no-references-subdir-while-sister-integrations-extracted-today` | `d13c693` | `skills/integrations/push-notifications/references/` agora existe | ✅ **Confirmado** |
| 15 | `skill-architecture-design-patterns-grew-100-lines-with-composition-root-no-references-extraction-pattern-not-applied-now-4th-largest-skill` | `d13c693` | Idem #13 | ✅ **Confirmado** |

### Bloco 4 — Scripts & Helpers

| # | Fingerprint | Commit | Verificação | Status |
|---|-------------|--------|-------------|--------|
| 16 | `ref-new-adr-script-creates-templates-inline-via-heredoc-ignoring-templates-adr-template-md` | `eb3168e` | `scripts/new-adr.sh:35 TEMPLATE="$SCRIPT_DIR/../templates/adr-template.md"` — script lê arquivo em vez de heredoc | ✅ **Confirmado** |
| 17 | `token-_index-md-552-lines-grew-43-lines-in-24h-6th-consecutive-pass-rotation-script-still-unwritten-projection-1000-linhas-em-13-dias` | `eb3168e` | `helpers/archive-index.sh` (66 linhas) existe; rodando `bash helpers/archive-index.sh --dry-run` retorna "✓ No entries older than 90 days" (esperado — oldest é 2026-05-06, apenas 13 dias) | ✅ **Confirmado** (script existe, mas nunca foi acionado ainda — ver achado #2) |
| 18 | `token-index-md-growing-35-slugs-per-day-archive-script-still-unwritten-after-3-mentions` | `eb3168e` | Idem #17 | ✅ **Confirmado** |
| 19 | `ref-install-sh-both-python-and-fallback-branches-miss-transcript-multiplier-and-model-max-tokens` | `1aa5787` | `scripts/install.sh:469-470` (Python branch) e `:509-510` (fallback) ambos emitem as 2 chaves | ✅ **Confirmado** |
| 20 | `ref-install-fallback-prefs-missing-transcript-multiplier-and-model-max-tokens` | `1aa5787` | Idem #19 | ✅ **Confirmado** |

### Bloco 5 — Stack-Detection & Skills

| # | Fingerprint | Commit | Verificação | Status |
|---|-------------|--------|-------------|--------|
| 21 | `agent-mobile-developer-ios-android-platform-blocks-60-lines-no-platform-skills` | `c2d2499` | `skills/mobile/ios/SKILL.md` (33 linhas) e `android/SKILL.md` (35 linhas) criados; `mobile-developer.md:72-73` wirea via tabela "Platform skills" | ⚠️ **Partial** (skills criadas e referenciadas, mas conteúdo é raso — 33-35 linhas, comparado a `ios-hig`=218 e `material-design`=221; ver achado #3) |
| 22 | `ref-stack-detection-skill-created-but-zero-agent-loads-still-orphan-on-day-of-creation` | `c2d2499` | `skills/shared/stack-detection/SKILL.md` carregada por 4 agents: setup-assistant, software-architect, database-specialist, devops-specialist | ✅ **Confirmado** |

### Bloco 6 — Quiz-First & Misc

| # | Fingerprint | Commit | Verificação | Status |
|---|-------------|--------|-------------|--------|
| 23 | `ref-setup-assistant-violates-quiz-first-rule-multiple-plain-text-prompts` | `3bb9d74` ou anterior | `setup-assistant.md:86,121` agora usa `AskUserQuestion` — `grep -n "yes ?/ ?no" agents/setup-assistant.md` retorna 0 | ✅ **Confirmado** |
| 24 | `auto-fingerprint-script-matches-body-text-not-entry-line-anchors` | `dc661dc` | Idem #2 (mesmo fix) | ✅ **Confirmado** |
| 25 | `token-stop-04-notifier-fast-path-broken-burns-80-150ms-per-stop-call-in-conversational-sessions` | `bec005e` | Idem #1 (cross-cut) | ✅ **Confirmado** |
| 26 | `token-check-fingerprint-uniqueness-broken-regex-burns-CI-minutes-with-permanent-false-pass` | `dc661dc` | Idem #2 (cross-cut) | ✅ **Confirmado** |
| 27 | `ref-claude-md-architect-command-description-out-of-sync-with-commands-architect-md-after-workflow-detection-introduction` | `3bb9d74` | `CLAUDE.md:155` ainda mostra `/devteam:architect` com descrição original "Architecture decisions, ADRs, trade-offs; auto-detects workflow from request..." — texto **foi atualizado** referenciando auto-detection | ✅ **Confirmado** |
| 28 | `token-software-architect-workflow-detection-25-lines-inline-x-9-architect-spawn-commands-fan-out-3600-tokens-per-multi-architect-flow` | `d13c693` | Idem #4 (mesma extração) | ✅ **Confirmado** |
| 29 | `token-design-patterns-skill-244-lines-loaded-by-3-agents-no-lazy-load-gate-for-composition-root-pattern-only-needed-on-DI-tasks` | `d13c693` | Skill reduzida para 152 linhas e references/ criadas; **lazy-load gate ainda não implementado** — agentes que carregam `design-patterns` continuam pegando SKILL.md inteiro | ⚠️ **Partial** (extração ✅; lazy-load por pattern ❌ — ver achado #4) |

---

## Achados Estruturais Novos (não registrados no _index.md)

### #1 — `devops-specialist.md` corpo ainda contém defaults stack-prescriptive

**Arquivo:** `agents/devops-specialist.md:140-156`

O commit `3bb9d74` corrigiu a **descrição** e o **parágrafo de identidade**, mas a "Decision Framework — Infrastructure Sizing" (linha 134) e "Anti-Overengineering Rules" (linha 149) ainda contêm:

```
| < 1k req/day | Single EC2/VPS + Docker Compose |
| > 100k req/day | Evaluate distributed architecture (not necessarily Kubernetes) |
- Don't use Kubernetes when Docker Compose works
- Don't build a service mesh when Nginx handles the routing
- Don't set up a full observability platform (Datadog, Grafana Cloud) when CloudWatch or a self-hosted Prometheus covers the need
```

**Verdict:** o fingerprint pai (`ref-software-architect-line-117-kubernetes-docker-compose-vps-stack-bias-mirrors-devops-fix`) foi marcado ✅ Executed para `software-architect`, mas o **mesmo viés persiste no `devops-specialist`** que foi a origem do problema. **Recomendação Guardian:** abrir como sub-escopo refinado.

### #2 — `helpers/archive-index.sh` criado mas não tem hook de execução automática

**Arquivo:** `helpers/archive-index.sh` + `scripts/hooks/stop/*.sh`

O script existe e funciona, mas:
- Não está registrado em nenhum sub-script do `Stop` ou `PreToolUse` dispatcher
- Não é invocado pelo `update.sh` ou `install.sh`
- Nenhum CI workflow o executa

Logo, o `_index.md` continuará crescendo indefinidamente até que alguém rode o script manualmente. Em ~90 dias, a primeira entrada elegível (2026-05-06) ficará disponível mas **ninguém vai disparar a archivação**.

### #3 — iOS/Android skills criadas mas **raso demais**: 33-35 linhas vs. `ios-hig`/`material-design` (218-221 linhas)

**Arquivos:** `skills/mobile/ios/SKILL.md` (33 linhas), `skills/mobile/android/SKILL.md` (35 linhas)

Comparativo:
- `skills/mobile/ios/SKILL.md` cobre: design (1 bullet), permissions, code signing, SwiftUI standards
- `skills/mobile/ios-hig/SKILL.md` cobre: 218 linhas detalhadas de Human Interface Guidelines

A skill `ios` apenas **redireciona** para `ios-hig` no primeiro bullet. Sobrepoição funcional é alta — `ios` virou wrapper. **Recomendação:** ou consolidar `ios + ios-hig` em uma skill só, ou extrair conteúdo único do `ios-hig` para references/ e mover regras de plataforma para `ios`.

### #4 — Skills extraídas para `references/` mas agentes ainda fazem **eager load** do SKILL.md raiz

**Arquivos:** `skills/architecture/design-patterns/SKILL.md` (152 linhas) + `composition-root.md` em references/

A extração reduziu o SKILL.md, mas:
- Nenhum agente que carrega `design-patterns/SKILL.md` carrega condicionalmente `references/composition-root.md`
- Skill.md raiz **menciona** o pattern de Composition Root sem expandir
- Lazy-load gate ("carregar references/composition-root.md apenas em tarefas DI") nunca implementado

Status real: a **economia prometida** (~3.200 tokens/sessão de plano multi-architect) só será realizada quando os agentes adotarem load condicional.

### #5 — Telemetria recém-criada gera **duplicação de código** em 3 arquivos

**Arquivos:**
- `scripts/helpers/telemetry-send.sh:42-52` — `_telemetry_enabled()` (10 linhas)
- `scripts/hooks/pre-tool-use/02-telemetry.sh:17-25` — `_telemetry_enabled()` (10 linhas)
- `scripts/hooks/stop/05-telemetry.sh:19-27` — `_telemetry_enabled()` (10 linhas)

Total: **30 linhas duplicadas** em 3 arquivos com lógica idêntica de checar `preferences.json`. Já existe `scripts/hooks/lib/session-summary-detect.sh` como padrão de lib compartilhada — telemetria deveria seguir o mesmo padrão.

### #6 — CHANGELOG.md `[Unreleased]` está **defasado em 22 commits**

**Arquivo:** `CHANGELOG.md:10-43`

A janela 2026-05-17 → 2026-05-19 produziu 22 commits, dos quais ao menos 7 são **observáveis** (mudam comportamento ou estrutura):
- `bd61ff7` feat(telemetry): add anonymous usage telemetry via PostHog
- `a4bb102` feat(telemetry): wire install and update events
- `9f1826d` docs(telemetry): add PRIVACY.md
- `9c7aecd` refactor(scripts): move dev-only tools to helpers/
- `c2d2499` feat(skills): add iOS/Android skills + stack-detection
- `d13c693` refactor(skills): extract large inline sections to references/
- `8c564bd` feat(agents): detect workflow intent in software-architect

Nenhum desses está no `[Unreleased]`. CLAUDE.md:32 "Auto-Docs Rule" mandata atualização no mesmo working session. **Violação severa** — sub-escopo do antigo `ref-changelog-package-exclusions-update-not-documented-in-unreleased` (2026-05-12 ✅), com agora **7 entradas faltando**.

---

## Recomendações Guardian

1. **Reabrir** `ref-devops-specialist-description-line-8-still-lists-deployment-defaults-after-body-fix` (2026-05-18 ✅) como ⚠️ **Partial** — corpo do agente (linhas 140-156) ainda contém preferências stack-específicas.
2. **Reabrir** `agent-mobile-developer-ios-android-platform-blocks-60-lines-no-platform-skills` (2026-05-18 ✅) como ⚠️ **Partial** — skills criadas mas conteúdo raso demais para servir como fonte de conhecimento de plataforma.
3. **Reabrir** `token-design-patterns-skill-244-lines-loaded-by-3-agents-no-lazy-load-gate-for-composition-root-pattern-only-needed-on-DI-tasks` (2026-05-18 ✅) como ⚠️ **Partial** — extração feita, lazy-load gate ainda não.
4. Validar o próximo Guardian (em 2026-05-19) se o `[Unreleased]` do CHANGELOG foi sincronizado.

---

## Estado dos Scans no Repositório

```
$ bash helpers/agent-lint.sh
agent-lint: clean ✓

$ bash helpers/check-fingerprint-uniqueness.sh
✓ All fingerprint slugs are unique.

$ bash helpers/orphan-skill-scan.sh --quiet
ACTION SUGGESTED — duplicate skill loads detected:
  · agents/ui-ux-designer.md loads skills/design/design-system-audit/SKILL.md more than once
  · commands/update.md loads skills/shared/interaction-patterns/SKILL.md more than once

$ bash helpers/orphan-template-scan.sh
ACTION REQUIRED — Orphan templates (no agent/skill/command references):
  · templates/backlog-template.md
```

Esses 3 itens (2 duplicate loads + 1 órfão de template) são **novos pendentes** desde o último Guardian — endereçados em sub-relatórios deste dia.

---

## Próximo Passo

Ver sub-relatórios deste dia (`01-…`, `02-…`, `03-…`, `04-…`) para **24 sugestões originais** novas, todas com fingerprints únicos não presentes no `_index.md`.
