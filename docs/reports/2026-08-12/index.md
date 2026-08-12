# Auditoria Guardiã — 2026-08-12

**Data:** 2026-08-12 · **Baseline:** `HEAD` = `07e0725` · **Baseline anterior:** `f54569a`

## Sumário executivo

Delta grande desde o baseline anterior: **187 arquivos, +10.487 / −1.431 linhas** (2026-08-01 →
2026-08-11) — novo agente `seo-specialist`, 9 comandos novos, 11 skills novas, telemetria
re-habilitada, `render_provider.py` reescrito. Apesar do volume, o repositório está em **saúde
excelente**: todos os gates automáticos (`agent-lint`, `size-limits`, `orphan-skill-scan`,
`orphan-template-scan`) verdes, `hooks.md` e os pares de doc EN↔pt-BR em sincronia.

**A verificação é o achado principal, não os eixos.** Nenhuma marcação ✅ veio 🔴 nesta
verificação (0% de reabertura), e o delta **fechou de passagem** 3 itens que estavam abertos/reabertos.
A Fase 2 rendeu **1 achado original** (Eixo A, LOW-MEDIUM) — os outros quatro eixos não renderam
achados originais com evidência, resultado válido por regra ("nunca invente volume").

## Cobertura da Fase 1

Conjunto verificável ≈124 (>60 → amostragem). Verificados **30 de 124**: 100% dos HIGH (11) e
MEDIUM-HIGH (7), 100% dos 8 itens antes anotados 🔴/🟡, 100% dos 6 "still open", + amostra do
restante. Critério de escalonamento (>15% 🔴) **não atingido**.

## Placar da Fase 1

| ✅ Feito (sobrevive) | 🟢 Resolvido de passagem | 🔴 Reaberto novo |
|---|---|---|
| 26 | 2 | 0 |

Resolvidos pelo delta:
- `flow-telemetry-pre-tool-use-02-…` → 🟢 por `156771b` (fila/batch + early-exit antes do fork python3)
- `gov-installer-rigor-asymmetry` → 🟢 por `872477b`+`ae77545` (repo agora dogfooda 4 dispatchers)

## Mortalidade da Fase 1b

**1 de 11 = 9%** — `auto-commands-json-plan-gate-field-has-no-consumer` resolvido (o render engine
agora consome `plan_gate` via `soften_plan_gate()`). Os outros 10 abertos reproduzem no HEAD.

## Achados originais por eixo

| Eixo | Originais | Nota |
|---|---|---|
| A — Agnosticismo de stack (integral) | **1** | `relayout.md` nomeia Storybook/Tailwind na descoberta de design (LOW-MEDIUM) |
| B — Referências e consistência | 0 | gates limpos, docs sincronizadas |
| C — Fluxos e comandos | 0 | dispatchers com allowlist, sub-scripts reusam touched-set |
| D — Agentes e skills | 0 | skills novas wired, sob limite, sem duplicação de regra |
| E — Economia de tokens | 0 | dívidas materiais já registradas e revalidadas |

## Severidade dos achados originais

| Severidade | Contagem |
|---|---|
| HIGH | 0 |
| MEDIUM-HIGH | 0 |
| MEDIUM | 0 |
| LOW-MEDIUM | 1 |
| LOW | 0 |

## Descartados por duplicação

| Candidato | Porta | Motivo |
|---|---|---|
| `frontend-developer.md:96` nomeia TanStack/SWR/React/Vue na seção Data Fetching | Porta 3 (semântica) | Alvo + causa-raiz coincidem com `agent-frontend-developer-body-92-102-data-fetching-section-hardcodes-usestate-useeffect-tanstack-query-swr…` (✅). O `useState` só sobrevive como anti-exemplo (`:91`); a marcação ✅ se sustenta |
| `CLAUDE.md` cresceu para 586 linhas | Porta 5 (estado) | Item já registrado e aberto (`token-claude-md-426-lines`, 🔴) |
| `install.sh`/`CHANGELOG`/`session-start` crescimento | Porta 5 (estado) | Já registrados e abertos |
| Sub-scripts `03c/03d/03e` "re-forkam git" | Porta 3 (semântica) | Hipótese refutada por evidência — reusam `DEVTEAM_TOUCHED_PATHS`; nenhum achado |
| `_disabled-*` scripts "auto-executam" | — | Hipótese refutada — ambos dispatchers têm `SUBSCRIPT_RE` allowlist |

## Os 3 achados mais graves

1. **Integridade do banco confirmada** (não é defeito): 0% de reabertura na Fase 1, 9% de mortalidade
   na Fase 1b — o banco resistiu a um delta de 187 arquivos sem drift silencioso.
2. **`relayout.md` acopla a descoberta de design a Storybook/Tailwind** (LOW-MEDIUM) — único
   acoplamento de stack novo nos 9 comandos novos.
3. **Dívidas estruturais abertas seguem crescendo** — `install.sh` (1085), `CHANGELOG` (959),
   `CLAUDE.md` (586), `session-start.sh` (306). Nenhuma nova, mas todas piores; são as candidatas
   naturais do próximo pass de execução.

---

# Pass incremental — 2026-08-12 (2ª execução)

**Data:** 2026-08-12 · **Baseline:** `HEAD` = `3fbe371` · **Baseline anterior:** `07e0725`

## Sumário executivo

Segunda execução do pass guardião no mesmo dia, contra o delta que entrou depois do baseline da
manhã: **11 commits, 23 arquivos, +1.603 / −12**, dos quais 8 são código ou documentação de
comportamento. Escopo deliberadamente estreito — reverificar a amostra de 30 itens seis horas
depois não produziria informação; o valor está no delta.

**O delta introduziu três mudanças de comportamento e as três têm defeito verificado.**
`4734882` (guarda de sessão do auto-learn) entrega uma otimização cuja condição de skip é
inalcançável e esquece o espelho do `install.sh` que o `CLAUDE.md` nomeia; `58d86a5` (full-suite
guard) conserta o truncamento em aspas aninhadas mas mantém o transbordo do `sed` para as chaves
JSON vizinhas, de modo que a prosa do `description` decide se o nudge dispara. Todos os gates
automáticos seguem verdes — nenhum deles cobre esta classe de defeito.

## Cobertura da Fase 1

Não houve nova amostragem: os 30 de 124 verificados de manhã valem para o dia. Verificados aqui
os **2** fingerprints corrigidos de manhã (sobrevivência das marcações no `HEAD`) e os **4** cujo
alvo o delta tocou (`scripts/install.sh`, `commands/commit.md`).

## Placar da 2ª execução

| ✅ Sobrevive | 🟡 Parcial | 🔴 Reaberto novo |
|---|---|---|
| 3 | 0 | 0 |

Os 3 🔴 pré-existentes com alvo no delta (`install.sh` 1086 linhas, sem registro de `commit-msg`
hook; validação silenciosa em `commit.md`) **seguem abertos** — o delta não os tocou.
Critério de escalonamento (>15% 🔴) não atingido. As 2 marcações 🟢 da manhã estão íntegras;
contagem do banco em `3fbe371`: 122 ✅ · 4 🟢 · 5 🔴 · 3 🟡 · 2 ⚠️ sobre 144 fingerprints.

## Mortalidade da Fase 1b

**0% (0 de 2 revalidados).** Apenas 2 dos 10 achados abertos têm alvo dentro do delta; ambos
reproduzem no `HEAD`.

## Achados originais por eixo

| Eixo | Originais | Observação |
|---|---|---|
| A — Agnosticismo de stack | 0 | Varredura integral: 121 candidatos, 9 no delta, todos sob tabela de detecção ou condicional gated |
| B — Referências e consistência | 1 | Gates verdes; o achado é o `.gitignore` do próprio repo |
| C — Fluxos, comandos e automação | 4 | 3 MEDIUM-HIGH + 1 LOW-MEDIUM, todos no delta |
| D — Agentes e skills | 0 | Superfície de 3 linhas alteradas; gates verdes |
| E — Economia de tokens | 0 | O achado de token do delta é o mesmo do Eixo C — não recontado |

**Total: 5 achados originais.**

## Tabela de severidade

| Severidade | Qtd | Fingerprints |
|---|---|---|
| HIGH | 0 | — |
| MEDIUM-HIGH | 3 | `auto-full-suite-guard-sed-absorbs-sibling-json-keys` · `flow-learn-run-marker-records-commit-time-not-run-time` · `auto-install-heredoc-omits-auto-learn-before-commit` |
| MEDIUM | 1 | `gov-repo-gitignore-omits-three-installer-written-entries` |
| LOW-MEDIUM | 1 | `docs-sync-02c-comment-cites-graphify-hint-as-sed-precedent` |

## Os 3 achados mais graves

1. **O `description` do payload decide se o full-suite guard dispara**
   (`02c-full-suite-guard.sh:22`). Captura gulosa absorve as chaves JSON irmãs; exclusões de
   escopo casam contra prosa. Reproduzido: dois payloads com o mesmo comando e descrições
   diferentes produzem vereditos opostos.
2. **A guarda de sessão do auto-learn é um no-op permanente** (`commit.md:17` × `learn.md:166`).
   O marcador grava o *commit timestamp do HEAD*, não a hora da execução, e é escrito antes do
   auto-commit do Step 5. A economia de contexto que justifica `4734882` não se materializa.
3. **O heredoc de fallback sem `python3` não recebeu `auto_learn_before_commit`**
   (`install.sh:1022-1025`). É o primeiro dos cinco espelhos que o `CLAUDE.md` nomeia, o commit
   que criou a chave editou o arquivo mas não o bloco, e o aviso "the two drifted once already"
   está na linha imediatamente acima — segunda ocorrência da mesma drift.

## Descartados por duplicação

| Candidato | Porta | Motivo |
|---|---|---|
| `CLAUDE.md` File Structure não lista `docs/prompts/` (criado hoje por `d10d541`) | 3 (semântica) | Alvo, causa raiz e remediação coincidem com 3 fingerprints ✅ Executed da família `ref-claude-md-file-structure-*` |
| Economia de tokens da guarda de sessão que não dispara | 3 (semântica) | Mesmo alvo, causa e remediação do achado do Eixo C |
| `install.sh` com 1086 linhas · sem registro de `commit-msg` hook | 5 (estado) | Pertencem ao conjunto aberto — reapresentar é ruído |
| Hits de stack em `commit.md:135-138` (npm/phpcs) e `setup-assistant.md:146-147` (jest/pytest/phpunit) | Eixo A, regra de descarte | Tabelas de detecção e listas de sinais — exceção explícita da regra |
