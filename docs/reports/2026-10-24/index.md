# Auditoria Guardiã — 2026-10-24

**Data:** 2026-10-24 · **Baseline:** `HEAD` = `b64428b` · **Baseline anterior:** `bb0e883`

> **A árvore estava suja durante todo o pass, e isso mudou o resultado.** No momento da Fase 0 o
> working tree carregava **79 arquivos modificados (3.539 inserções) e 9 não rastreados**, entre
> eles `CLAUDE.md`, os dois `README`, 7 agentes, 6 comandos e 19 skills. Toda a evidência deste
> pass vem de `git show HEAD:<path>`. A diferença não é formal: medido no disco,
> `skills/shared/docs-templates/SKILL.md` tem 301 linhas e manda rodar
> `bash .dev-team-agents/scripts/doc-path.sh`; no `HEAD` tem 153 e não menciona esse script, que
> tampouco existe lá. Auditar o disco teria publicado um HIGH inteiramente falso. Dois candidatos
> deste pass morreram por essa checagem.

## Método

Delta de **98 commits e 704 arquivos** desde `bb0e883` — o segundo maior da história do banco,
concentrado em `.dev-team-agents/skills` (263), `.dev-team-agents/scripts` (140), `app/src` (45),
`.dev-team-agents/commands` (35), `docs/wiki` (30) e `scripts/lib` (28). Em superfície shipped:
9 comandos (3 novos — `up`, `down`, `insights`), 13 skills de `skills/shared`, 1 agente, 7 ADRs
novas.

**Fase 1** — amostragem obrigatória: conjunto verificável de **152** (151 ✅ Executed + 1
⚠️ Partial) acima do limiar de 60, logo todos os 42 HIGH/MEDIUM-HIGH mais 30% do restante
(`seed=20261024`). **Fase 1b** — 118 de 118 abertos, em duas camadas: resolução mecânica do alvo
contra os 704 arquivos do delta, depois verificação individual dos 37 que o delta tocou.
**Fase 2** — Eixo A integral; demais eixos priorizando o delta.

## Fase 1 — cobertura e placar

**75 de 152 verificados (49,3%)** · HIGH 20/20 · MEDIUM-HIGH 22/22 · restante 33/110.

| ✅ Feito | 🟢 Resolvido | 🟡 Parcial | 🔴 Não feito |
|---|---|---|---|
| 61 (81,3%) | 1 (1,3%) | 9 (12,0%) | 4 (5,3%) |

**Confirmado: 82,7% · Reaberto NOVO: 0 (0%)** — segundo pass consecutivo sem uma única marcação
nova derrubada. As 4 🔴 e as 9 🟡 já carregavam anotação de passes anteriores e foram
reconfirmadas contra o `HEAD`; nenhuma mudou de estado. O limiar de escalonamento (15%) não foi
atingido.

## Fase 1b — mortalidade

**118 de 118 (100%)** · **1 🟢 · 0 ⚰️** → **mortalidade de 0,85%**.

O único resolvido é `flow-claude-md-no-agent-command-list-says-seven-omits-push-and-merge`: o
parágrafo contraditório de `CLAUDE.md` desapareceu no delta e a lista canônica ficou só em
`scripts/lib/commands.json:7` e `CLAUDE-md/commands.md:62,64`.

**Este zero não é imobilidade.** 37 dos 118 alvos abertos foram tocados por 98 commits e **36
seguem reproduzindo** — o repositório entrega funcionalidade nova, não a dívida registrada. E
**8 fingerprints abertos mediram pior** que no registro (`CLAUDE.md` 426→582, `interaction-patterns`
209→318, `checks-list` 681→791, `fix-patterns` 517→622, `orchestration` 377→402, Jira 11→13
agentes, skills 151→156, descrições de comando divergentes agora 40 de 40). Um foi re-ancorado
(`04-task-board.sh`, de `:88`/`:49` para `:97-98`/`:102`).

## Fase 2 — achados por eixo

| Eixo | Originais | Nota |
|---|---|---|
| A — Agnosticismo de stack | **1** | 127 hits → 14 candidatos → 1 violação |
| B — Referências e consistência | **1** | 4 helpers limpos; a divergência é uma chave sem gate |
| C — Fluxos e comandos | 0 | nenhum achado original neste eixo |
| D — Agentes e skills | 0 | nenhum achado original neste eixo |
| E — Economia de tokens | 0 | nenhum achado original neste eixo |
| **Total publicado** | **2** | |

## Tabela de severidade

| Severidade | Nº | Fingerprints |
|---|---|---|
| HIGH | 0 | — |
| MEDIUM-HIGH | 1 | `gov-interaction-mode-key-ungated-and-undocumented-outside-commands-json` |
| MEDIUM | 1 | `agent-product-analyst-step6-gates-isolated-infra-on-docker-and-inlines-compose-probe` |
| LOW-MEDIUM | 0 | — |
| LOW | 0 | — |

## Os achados

1. **MEDIUM-HIGH** — `interaction_mode` reescreve o corpo de todo comando no render do Codex
   (`scripts/lib/render_provider.py:223-225`), decide entre rotear para `/plan` e degradar para
   lista numerada, e não tem **nem** gate (`git grep interaction_mode HEAD -- helpers/ .github/`
   → vazio) **nem** menção em qualquer arquivo de documentação (`CLAUDE.md`, `CLAUDE-md/` → 0).
   A chave irmã `plan_gate` tem as duas coisas: `CLAUDE-md/commands.md:58` e
   `helpers/agent-lint.sh:374`. `/devteam:up` e `/devteam:down` nasceram neste delta com
   `optional` sem critério contra o qual conferir.
2. **MEDIUM** — `agents/product-analyst.md:151-155`, sob `## Step 6 — Sprint Generation`,
   condiciona o modelo de isolamento do Parallel Execution Plan a "the project uses Docker" e
   inlina `ls docker-compose.yml docker-compose.yaml compose.yml compose.yaml`, duas linhas antes
   de dizer "do not restate the mechanics" — enquanto `agents/setup-assistant.md:66` demonstra o
   padrão correto ("apply the Docker Compose probe from the already-loaded `stack-detection`
   skill … so no agent re-probes").
3. *(terceiro mais grave — não há um)* Com dois achados publicados, o terceiro item desta lista é
   a observação de método no topo: um pass rodado sobre o disco, e não sobre o `HEAD`, teria
   publicado pelo menos um HIGH falso hoje.

## Descartados por duplicação

**21 candidatos descartados.**

**Porta 5 (estado — já no conjunto aberto), 11:** `devops-specialist.md:3` e `:46-56` ·
`database-specialist.md:84` RLS · `security-specialist.md:80-85` ·
`frontend-test-specialist.md:141-153` SonarQube · `frontend-developer.md:3` frontmatter ·
`commands/mobile.md:21,28` · `commands/devops.md:2,14` · `commands/audit.md` vendor no spawn ·
`orchestration` 402 linhas sem `references/` · `interaction-patterns` 318 linhas ·
`checks-list` 791 / `fix-patterns` 622 · `04-task-board.sh` forks antes do marcador ·
`current-context` em 34 de 40 comandos · `/devteam:install` ausente dos READMEs · descrições de
comando divergentes entre frontmatter e `commands.json`.

**Porta 4 (escopo menor sem sub-escopo novo), 1:** `devops-specialist.md:138-149` checklist
Docker/Terraform.

**Porta 3 (semântica — 2 de 3 atributos), 2:** `frontend-reviewer.md:112,114` React/TS (descartado
em 2026-08-28) · duplicação da sonda de compose entre `product-analyst` e `stack-detection`
(mesmo alvo e mesma remediação do achado publicado no Eixo A; conta uma vez).

**Descartados por não serem violação, 4:** `commands/commit.md:131,134` e
`ui-ux-designer.md:57-59` (tabelas de detecção) · `commands/explain.md:48` (anti-prescrição) ·
`commands/up.md:2-3,19` (o token `docker` é o vocabulário canônico de modo definido em
`skills/devops/local-environment/SKILL.md:32`, não uma prescrição de ferramenta) ·
`commands/down.md` sem argumento de modo (identifica o que roda em vez de perguntar).

**Descartados na Porta 0 (evidência inexistente no `HEAD`), 2:** `docs-templates/SKILL.md` com 301
linhas e chamada a `scripts/doc-path.sh` · `scripts/docs-migrate.py` referenciado por skill —
ambos só existem no working tree sujo.

## Gates

```
$ bash helpers/check-fingerprint-uniqueness.sh   → ver 02-referencias-e-consistencia.md
$ bash helpers/archive-index.sh --dry-run        → nenhuma seção acima de 90 dias
$ bash helpers/orphan-skill-scan.sh              → clean ✓
$ bash helpers/orphan-template-scan.sh           → clean ✓
$ bash helpers/agent-lint.sh                     → clean ✓
$ bash helpers/size-limits.sh                    → clean ✓
```
