# Guardian Audit — 2026-05-15

> **Modo Guardian:** verificação cruzada das 40 marcações ✅ Executed / ⚠️ Partial / pendentes registradas no `_index.md` para a passada de **2026-05-14**, com `git log --since="2026-05-14"` e leitura direta dos arquivos.

---

## 1. Resumo Executivo

| Métrica | Valor |
|---------|-------|
| Fingerprints registrados em 2026-05-14 | **40** |
| ✅ Executed (confirmados) | **35** (10 verificados por spot-check direto) |
| ⚠️ Partial | **0** literais — sub-escopo de 5 candidatos |
| 🟢 Resolved | **0** |
| Pendentes restantes | **5** |
| Drift detectado (claim vs realidade atual) | **2** (worsening) |
| Commits desde 2026-05-14 | **39** |
| Throughput | **88%** (35/40) — recorde da série |

**Veredito:** o pacote de 6 fases mergeadas (`4a/4b → 4c → 5a/5b → 5c/5d → 5e–5h → 6a–6i`) entregou de fato as extrações, mobile-developer spawns e fragmentação CLAUDE.md prometidos. Spot-check confirmou claims em todos os 10 itens amostrados (frontend-developer 285→220, ui-ux-designer 285→171, project-context 291→266, mobile-flutter 292→195, kong 277→42, CLAUDE.md 557→425 etc.). **Nenhum DRIFT cosmético detectado**.

Porém: **dois pendentes pioraram** entre 2026-05-14 e 2026-05-15:

| Pendente | Estado em 2026-05-14 | Estado em 2026-05-15 | Delta |
|----------|----------------------|----------------------|-------|
| `token-fingerprint-index-_index-md-380-lines-not-rotated-yet` | 380 linhas | **464 linhas** | **+84 (+22%)** em 24h |
| `token-commands-commit-md-145-lines-and-refactor-md-156-lines-largest-command-files` | commit=145, refactor=156 | commit=**160**, refactor=**152** | commit +15 / refactor −4 |

---

## 2. Spot-Check (10 amostras aleatórias dos 35 Executed)

| Fingerprint | Claim | Verificação | Veredito |
|-------------|-------|-------------|----------|
| `agent-frontend-developer-285-lines-tied-largest-with-ui-ux-designer-after-extractions` | reduzir de 285 | `wc -l agents/frontend-developer.md` = **220** | ✅ Confirmado (−65 / −23%) |
| `agent-ui-ux-designer-285-lines-no-references-pattern-yet-applied` | reduzir de 285 | `wc -l agents/ui-ux-designer.md` = **171** | ✅ Confirmado (−114 / −40%) |
| `ref-claude-md-grew-to-557-lines-after-quiz-first-addition` | reduzir de 557 | `wc -l CLAUDE.md` = **425** | ✅ Confirmado (−132 via fragmentação para `CLAUDE-md/`) |
| `skill-shared-project-context-291-lines-loaded-by-14-agents` | extração para references/ | `wc -l skills/shared/project-context/SKILL.md` = **266** + `references/` populada | ✅ Confirmado (−25) |
| `skill-mobile-flutter-292-lines-largest-skill-no-references-extraction` | extração para references/ | `wc -l skills/mobile/flutter/SKILL.md` = **195** + `references/` populada | ✅ Confirmado (−97 / −33%) |
| `skill-mobile-react-native-264-lines-no-references-extraction` | extração para references/ | `wc -l skills/mobile/react-native/SKILL.md` = **170** + 3 references/ files | ✅ Confirmado (−94 / −36%) |
| `skill-integrations-kong-277-lines-loaded-by-only-one-agent-no-references` | extração para references/{plugins,consumers,routes-services} | `wc -l skills/integrations/kong/SKILL.md` = **42** + 3 references/ files | ✅ Confirmado (−235 / −85%) |
| `ref-fix-command-misses-mobile-developer-spawn-vs-claude-md-table` | adicionar mobile-developer ao `commands/fix.md` | Linhas 14-15 spawnam `mobile-developer¹` condicional | ✅ Confirmado |
| `ref-review-command-misses-mobile-developer-spawn-vs-claude-md-table` | adicionar mobile-developer ao `commands/review.md` | Linhas 17-18 spawnam `mobile-developer¹` condicional | ✅ Confirmado |
| `ref-haiku-model-declared-in-claude-md-but-zero-agents-use-it` | resolver gap (criar agent ou simplificar regra) | 0 Haiku agents; commit `19ef0f9` simplifica regra | ✅ Confirmado (via simplificação) — porém prosa residual em CLAUDE.md:120 mantém-se (novo fingerprint reaberto em [01-referencias-e-consistencia](01-referencias-e-consistencia.md#5)) |

**Resultado: 10/10 Confirmed; 0 DRIFT.**

---

## 3. Pendentes de 2026-05-14 (5 fingerprints sem marcador ✅)

Os 5 entries sem `✅ Executed` na entrada de 2026-05-14 são:

| # | Fingerprint | Estado em 2026-05-15 | Ação Recomendada |
|---|-------------|----------------------|------------------|
| 1 | `flow-update-command-quiz-first-applied-but-no-rollback-prompt-quiz` | `rollback.sh` ganhou `pre-rollback-<TARGET>` tag (L70-73) mas **quiz-first AskUserQuestion ainda ausente** | Repropor com sub-escopo "apenas quiz-first em rollback.sh" — descontar tag (foi resolvida em separado) |
| 2 | `flow-spawn-classifier-loaded-by-7-commands-but-no-classifier-output-cached` | `skills/shared/spawn-classifier/SKILL.md` sem lógica de cache; multi-agent `/devteam:fullstack` re-classifica | Repropor com fingerprint inalterado |
| 3 | `token-skill-monitoring-extracted-but-references-files-may-be-loaded-eagerly` | Referências listadas em tabela na `skills/devops/monitoring/SKILL.md:29-31` — padrão lazy-load **de facto resolvido**, mas sem marcador `🟢 Resolved` | Promover a `🟢 Resolved` |
| 4 | `token-fingerprint-index-_index-md-380-lines-not-rotated-yet-rotation-policy-says-90d-current-pace-30d` | `_index.md` cresceu para **464 linhas** (+84 / +22% em 24h) | Repropor + criar script `archive-index.sh` (vide [04-economia-tokens](04-economia-tokens.md#4)) |
| 5 | `token-commands-commit-md-145-lines-and-refactor-md-156-lines-largest-command-files` | commit.md = **160 linhas** (+15), refactor.md = **152 linhas** (−4) | Repropor com sub-escopo de extração específica (vide [02-fluxos-e-workflows](02-fluxos-e-workflows.md#1) e [02-fluxos-e-workflows](02-fluxos-e-workflows.md#2)) |

---

## 4. Achados Estruturais NOVOS (não constam do _index.md)

### 4.1 Orphan skill criado hoje

`skills/shared/stack-detection/SKILL.md` foi criado **hoje** (commit `4307f31`, 36 linhas) em resposta ao fingerprint pendente `skill-stack-detection-still-missing-3rd-pass-shared-base-needed` (2026-05-13).

**Problema:** **Zero agentes carregam-na.** Os 4 candidatos naturais (`setup-assistant`, `software-architect`, `database-specialist`, `devops-specialist`) continuam com heurísticas inline. Skill nasceu órfã. Vide [01-referencias-e-consistencia](01-referencias-e-consistencia.md#4).

### 4.2 Duplicate loads detectados

`bash scripts/orphan-skill-scan.sh` reporta 2 instâncias de skill carregada mais de uma vez no mesmo arquivo:

```
ACTION SUGGESTED — duplicate skill loads detected:
  · agents/ui-ux-designer.md loads skills/design/design-system-audit/SKILL.md more than once
  · commands/update.md loads skills/shared/interaction-patterns/SKILL.md more than once
```

Ambos são byproducts dos commits de hoje (`2cdfa9d` extração ui-ux-designer; `e0e8983` rollback-script + quiz-first em update.md). Vide [04-economia-tokens](04-economia-tokens.md#7).

### 4.3 Stack-agnosticism — 0 violações

Sweep across 17 agents com regex covering `docker-first`, `kubernetes-first`, `react-first`, `prefer (postgres|mysql|django|laravel|...)`, etc.:

- Único hit em `agents/frontend-developer.md:147` — `"Avoid direct DOM manipulation — prefer reactive state"` — **falso positivo** (`reactive state` é conceito genérico, não framework).
- `agents/devops-specialist.md` (alvo histórico): linha 3 e 8 agora descrevem "stack-aware fork", não opinião baked-in. Fingerprint `agent-devops-specialist-violates-stack-agnostic-rule-with-docker-first-bias` (2026-05-13) **genuinamente resolvido**.

---

## 5. Promoções históricas adicionais

Esta passada **não detectou** fingerprints anteriores (2026-05-11/12/13) que tenham sido executados na janela 2026-05-14 → 2026-05-15 e ainda não promovidos. O backlog histórico estabilizou.

---

## 6. Conclusão Guardian

- ✅ **Confiança alta** nos 35 Executed de 2026-05-14 (10/10 spot-check OK).
- ⚠️ **Pendentes 4 e 5** pioraram em 24h — sub-escopo precisa ser reaberto.
- 🆕 **3 achados estruturais novos** (orphan skill nascido órfão, 2 duplicate loads, regressão de adoção da `stack-detection`).
- 📊 **Throughput 88%** — sustentado por automação de extração (`scripts/orphan-skill-scan.sh`, `size-limits.sh --warn-only`, CI `fingerprint-uniqueness`).

> Próxima passada (2026-05-16) deverá focar em: (a) wireamento da `stack-detection` em 4 agentes, (b) deduplicação dos 2 duplicate loads, (c) preparação proativa do `archive-index.sh` para rotação do `_index.md`.
