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
