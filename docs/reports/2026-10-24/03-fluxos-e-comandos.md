# Eixo C — Fluxos, Comandos e Automação — 2026-10-24

**Baseline:** `HEAD` = `b64428b`. Prioridade: `commands/` (9 arquivos no delta, 3 deles novos),
`scripts/hooks/` (14 arquivos) e `scripts/lib` (28).

## Nenhum achado original neste eixo.

O delta trouxe três comandos novos e uma reordenação de hooks, e os dois chegaram com os gates
que a convenção pede. O que foi examinado e **passou**:

| Verificação | Resultado no `HEAD` |
|---|---|
| `/devteam:up` e `/devteam:down` declaram `plan_gate` | `opt_out` em `scripts/lib/commands.json`, e ambos aparecem na lista de exceção de `CLAUDE-md/commands.md:58` |
| …e justificam a ausência de gate no corpo | `commands/up.md:10` — "No Plan Gate: the confirmation in Step 3 shows the exact commands before anything runs, and is the guardrail"; `commands/down.md:9` idem para o Step 2 |
| …e declaram o não-spawn de agente | `commands/up.md:8`, `commands/down.md:8`, com a razão (processos de vida longa que o contexto principal precisa seguir), espelhada em `CLAUDE-md/commands.md:64` |
| …e não restatem a skill que carregam | ambos: "Every step below points into it; do not restate its rules" |
| Confirmação antes de executar comando do projeto | `skills/devops/local-environment/SKILL.md:69-75` — imprime verbatim todo comando e sua origem, e sinaliza `privileged`, montagem de `/` ou `docker.sock`, `network_mode: host`, `sudo`, downloads, `rm` e portas em `0.0.0.0` antes de perguntar |
| Remoção de volumes/dados é confirmação separada | `commands/down.md:21` — "A request to also remove volumes, images or data is a separate, explicit confirmation (§ Stop, step 5) — never folded into this one" |
| Ordem de spawn do dispatcher `Stop` | `scripts/hooks/stop/` tem 16 sub-scripts; `00b-task-board.sh` ordena antes dos lints `0[2-3]*`, que é exatamente o que `6d4e002 fix(hooks): run the task board Stop hook before the lints` pretendia. A ordenação é lexicográfica no glob de `stop.sh:64` e não depende de lista manual |
| Convenção de nome do dispatcher cobre os novos | `stop.sh:62` — `SUBSCRIPT_RE='^[0-9]{2}[a-z]?-[a-z0-9]([a-z0-9-]*[a-z0-9])?\.sh$'` aceita `00b-`, `03h-`, `99b-` |
| `/devteam:insights` muda algo? | `plan_gate: opt_out` com razão declarada em `_plan_gate_values`: "commands that change nothing themselves and hand any change to plan mode (insights)" — coerente com `commands/insights.md` |

## Candidatos levantados e descartados

- **`/devteam:down` não aceita modo enquanto `/devteam:up` aceita.** Não é assimetria: `down`
  identifica o que está rodando para este checkout (§ Stop, steps 1–2) em vez de perguntar o modo,
  o que é mais robusto, não menos. Descartado — não é defeito.
- **`commands/up.md` sem Plan Gate.** Coberto pela confirmação do Step 3 e registrado na lista
  canônica. Descartado.
- **`commands/learn.md`, `plan.md`, `setup.md`, `sprint.md`, `relayout.md`, `health-check.md`
  modificados no working tree.** Fora do `HEAD`; por regra do eixo, não auditados. Voltam ao
  escopo do próximo pass quando forem commitados.
