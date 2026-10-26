# Eixo E — Economia de Tokens — 2026-10-24

**Baseline:** `HEAD` = `b64428b`.

## Nenhum achado original neste eixo.

O eixo rendeu zero achados **originais** e um dado que vale mais que eles: cinco dos maiores
consumidores de contexto já registrados **cresceram** desde que foram medidos, e nenhum encolheu.

| Fingerprint aberto | No registro | No `HEAD` | Multiplicador de leitura |
|---|---|---|---|
| `token-claude-md-426-lines-still-monolithic-…` (🔴) | 426 linhas | **582** | toda sessão |
| `token-interaction-patterns-209-lines-loaded-unconditionally-…` | 209 linhas | **318** | 34 comandos + 2 agentes |
| `token-checks-list-loads-all-three-provider-blocks-…` | 681 linhas | **791** | todo `/devteam:health-check` |
| `token-fix-patterns-517-lines-loaded-whole-…` | 517 linhas | **622** | toda aplicação de fix |
| `token-orchestration-skill-377-lines-…-no-references-dir` | 377 linhas | **402** | todo fluxo multi-agente |
| `token-token-efficiency-skill-itself-154-lines-…` (🟡) | 154 linhas | **160** | 18 de 18 agentes |

Somados, os seis valem **2.875 linhas** contra as 2.364 do registro: **+511 linhas (+21,6%)** nos
caminhos mais quentes da frota, sem que nenhuma das propostas de extração registradas tenha sido
executada. `skills/shared/token-efficiency/SKILL.md` segue carregada eagerly pelos 18 agentes, com
redação já uniformizada ("Apply `skills/shared/token-efficiency/SKILL.md`" em 18 de 18) — a
padronização foi feita, a condicionalização não.

## Candidatos levantados e descartados

- **`skills/shared/docs-templates/SKILL.md` carregada inteira para usar um layout de dois.**
  Falso no `HEAD` (153 linhas, não 301) — ver Eixo D.
- **`scripts/hooks/pre-tool-use/04-task-board.sh` forkando antes do marcador.** Já registrado
  (`token-pretooluse-04-task-board-13-forks-before-marker-exit-every-tool-call`); o script foi
  reescrito no delta e ganhou pré-gates em bash puro, mas `:97-98` ainda faz
  `source task-board.sh` + `devteam_task_board_init` antes do teste de `:102`. Porta 5 — re-ancorado
  na Fase 1b, não é achado novo.
- **`token-current-context-block-deduplication`** — 34 dos 40 comandos, 4 redações. Porta 5, 🟡 na
  Fase 1.

Não propor extração de novo onde a proposta já está no banco e não foi executada é o
comportamento correto. O que este eixo entrega hoje é a medição que torna a dívida visível.
