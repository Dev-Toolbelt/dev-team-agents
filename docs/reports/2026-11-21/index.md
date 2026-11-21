# Auditoria Guardiã — 2026-11-21

**Data:** 2026-11-21 · **Baseline:** `HEAD` = `17bfb26` · **Baseline anterior:** `c6398e5`

> **O achado principal deste pass é uma marca 🟢 que esconde um defeito promovido para um arquivo que
> ships.** `flow-claude-md-no-agent-command-list-says-seven-omits-push-and-merge` foi marcado 🟢
> Resolved em 2026-10-24 porque "o parágrafo dos sete comandos sem agente saiu do `CLAUDE.md`". Ele
> não foi corrigido: `309bebc` extraiu a tabela de comandos para `CLAUDE-md/commands.md`, e a
> afirmação falsa foi junto. No `HEAD`, `CLAUDE-md/commands.md:65` segue dizendo "**All seven** name
> `technical-writer`" contra os **nove** de `scripts/lib/commands.json` (`_filler_agent_note`), com
> `push` e `merge` incluídos — exatamente os dois que o enunciado original dizia estarem omitidos. O
> agravante que o pai não tinha: `CLAUDE.md` é removido do pacote pelo `KEEP_ROOT` de
> `scripts/install.sh:400`, enquanto `CLAUDE-md/` é a fonte do bloco que chega ao projeto instalado.
> A afirmação saiu de um arquivo que não ships e entrou em um que ships, e a marca 🟢 impede que
> qualquer pass futuro a reencontre.

---

## Método

Delta de **14 commits e 271 arquivos** desde `c6398e5`, dos quais **190 são guias do skill
vendorizado** `modern-web-guidance` (`535e04a`): a superfície autoral do delta são **55 arquivos**,
concentrados em `skills/design/seo-optimization` (6), `agents/` (5), `docs/development/adrs` (4),
`docs/development/aeo-geo` (3), `scripts/lib` (3) e `tests/` (3). Working tree com 4 arquivos
modificados em `app/`, nenhum deles alvo de fingerprint; evidência lida do disco.

Prioridade de varredura: os 55 arquivos autorais do delta. Eixo A integral, como manda a regra.

---

## Cobertura da Fase 1 — 22 de 22 (100%)

Conjunto verificável = ✅ Executed + ⚠️ Partial = **22 de 159 entradas** do banco vivo. Abaixo do
limiar de 60, logo **sem amostragem**.

| Marca verificada | Itens | % |
|---|---|---|
| ✅ **Feito** | 16 | 72,7% |
| 🟡 **Parcialmente feito** | 5 | 22,7% |
| 🔴 **Não feito** | 1 | 4,5% |

**Divergências novas: 3** (1 🔴 + 2 🟡). As outras 3 🟡 já carregavam anotação de 2026-10-02 /
2026-11-07 e foram reconfirmadas item a item.

O **4,5% de reaberto novo** está muito abaixo do limiar de escalonamento de 15%, mas **quebra quatro
passes consecutivos em 0%** (2026-10-17 a 2026-11-14). A nota de método de 2026-10-17 — o campo
`alvo:` nomeia quem **descreve** o problema, não quem o corrigiu — foi aplicada aos **22** itens;
sem ela, `skill-spec-gate-scope-lock-hard-gate-unreachable-by-execution-agents` teria dado um 🔴
falso.

Mais uma marca foi corrigida **fora** do conjunto amostrado: a 🟢 do achado principal, surgida da
varredura do Eixo B e reclassificada 🔴.

---

## Fase 1b — 123 de 123 (100%) · mortalidade 0%

0 🟢, 0 ⚰️. Nenhum dos 123 alvos deixou de existir.

**O zero não é imobilidade:** o alvo de **19 dos 123 abertos (15%)** foi tocado pelo delta, e os
**19 seguem reproduzindo**. Dez foram **re-ancorados** (linha ou arquivo mudou) e **8 mediram pior**,
entre eles `ref-command-description-duplicated-frontmatter-vs-commands-json` (35 → **43 de 43**
descrições divergentes), `docs-sync-hooks-md-warn-once-library-row-omits-03f-spec-lint…`
(3 → **5** consumidores de `warn-once`), `ref-hooks-md-library-rows-omit-data-dirs-sh…`
(`hooks/lib/` 10 → **14** arquivos, `data-dirs.sh` ainda em 0 linhas de tabela) e
`docs-sync-readme-command-table-omits-devteam-install…` (34/35 → **41/43**, agora com uma segunda
ausência: `down` sem linha, embora `up` tenha).

`CLAUDE.md` chegou a **602 linhas** e cruzou o *warning threshold* de 600 de
`helpers/size-limits.sh:88`. `agents/product-analyst.md` e `agents/frontend-developer.md` estão em
**exatamente 211 linhas**, o `AGENT_LIMIT` — fato que é a causa provável do achado do Eixo D.

---

## Achados originais por eixo — 4

| Eixo | Achados | Nota |
|---|---|---|
| A — Agnosticismo de stack | **0** | 130 hits → 14 candidatos → 0 violações. Sexto zero em sete passes. A ponte `third-party-web-skills` é **mais** agnóstica que a média do repositório |
| B — Referências e consistência | **2** | 1 MEDIUM-HIGH, 1 LOW-MEDIUM. Um terceiro candidato morreu na Porta 3 e virou a correção de marca 🔴 acima |
| C — Fluxos, comandos e automação | **0** | cinco sondagens sobre o comando, o hook e as chaves de doc novos; cinco premissas refutadas |
| D — Agentes e skills | **1** | MEDIUM-HIGH |
| E — Economia de tokens | **1** | MEDIUM |

### Tabela de severidade

| Severidade | Achados |
|---|---|
| HIGH | 0 |
| MEDIUM-HIGH | 2 |
| MEDIUM | 1 |
| LOW-MEDIUM | 1 |
| LOW | 0 |

Nenhum HIGH novo. Os quatro achados, do mais grave ao menos:

1. **`auto-canonical-facts-scans-vendored-third-party-trees-with-no-legal-fix`** (MEDIUM-HIGH) — o
   gate bloqueante `canonical-facts` varre **285 arquivos `.md` sob `skills/third-party/`**, conteúdo
   vendorizado que `CLAUDE.md:164` proíbe editar e que `third-party-skills.py verify` protege por
   hash. Passa hoje por sorte: um `sync` futuro ou um fato novo no JSON derruba o CI num arquivo que
   ninguém tem permissão de consertar, e a única outra saída — alargar um `allow` — enfraquece o
   tripwire na árvore inteira. O delta já tem o precedente: `6fbf868` resolveu o caso idêntico do
   `gitleaks` com uma exclusão por caminho; o `canonical-facts` não tem equivalente.
2. **`agent-product-analyst-briefing-load-nested-under-backlog-output-gate`** (MEDIUM-HIGH) — a
   única instrução que manda o `product-analyst` carregar `client-briefing` e escrever o doc está
   grudada no fim de um parágrafo cujo gate é "only when you are about to produce backlog output" —
   e o briefing explicitamente **não** é backlog output (`doc-flow:78`). `/devteam:brief` funciona
   porque o corpo do comando restata a instrução, de fora; qualquer outro caminho ao agente chega sem
   nenhuma. Causa provável: o arquivo está em exatamente 211 linhas, o cap.
3. **`token-seo-detection-signals-costs-25kb-skill-load-at-three-spawn-gates`** (MEDIUM) — três
   portas de decisão de spawn (`spawn-classifier:39`, `commands/frontend.md:23`,
   `product-analyst:57`) carregam 25.107 bytes de `seo-optimization/SKILL.md` para consultar uma
   tabela de **1.168 bytes**: 95,3% descartado por consulta. A skill foi construída em volta da
   carga condicional (17 referências, 108 KB) e a seção mais consultada é a única fora desse padrão.
4. **`docs-sync-aeo-geo-implementation-plan-status-says-uncommitted-at-head`** (LOW-MEDIUM) — a
   linha de status do plano diz "alterações não commitadas aguardando revisão" sobre um trabalho que
   `db2f240` commitou, inclusive o próprio arquivo.

---

## Descartados por duplicação — 9 de 13 candidatos

| Candidato | Porta | Por quê |
|---|---|---|
| "seven commands" agora em `CLAUDE-md/commands.md:65` | **3** | mesmo problema e mesma remediação do pai `flow-claude-md-no-agent-command-list-says-seven-omits-push-and-merge`; só o arquivo mudou. 2 de 3 atributos coincidem ⇒ duplicata. **Convertido em correção de marca 🔴** na Fase 1, que é o instrumento certo para uma marca 🟢 errada |
| `down` sem linha na tabela de comandos dos READMEs | **3** | mesmo arquivo, mesma causa raiz (`02-readme-sync.sh` compara EN↔pt-BR, não a tabela contra `commands.json`) e mesma remediação de `docs-sync-readme-command-table-omits-devteam-install-in-both-languages`. 3 de 3 ⇒ duplicata. Virou re-medição do pai |
| `/devteam:brief` ausente de `auto-routing`/`spawn-classifier`/`orchestrator` | **5** | pertence ao conjunto aberto via `flow-orchestrator-route-table-covers-10-of-42-commands-no-gate`. Virou re-medição: 10/42 → 11/43 |
| `frontend-developer.md:147` "prefer reactive state" | **5** | `agent-frontend-developer-testability-presumes-reactive-component-model`, aberto |
| `product-analyst.md:164-168` gate de Docker + sonda inline | **5** | `agent-product-analyst-step6-gates-isolated-infra-on-docker-and-inlines-compose-probe`, aberto |
| `security-specialist.md:82,86` vocabulário de GitHub Actions | **5** | `agent-security-specialist-cicd-checklist-github-actions-only-vocabulary`, aberto |
| `product-analyst.md:194` trackers sem skill | **5** | `agent-product-analyst-other-trackers-still-asana-clickup-monday-ungated`, aberto |
| `interaction-patterns`/`backlog-template`/`project-context` como carga incondicional grande | **5** | os três já abertos |
| `emil-design-eng/SKILL.md` com 674 linhas pedindo `references/` | **4** | é árvore vendorizada: não há sub-escopo acionável aqui, ADR-0047 proíbe a reestruturação |

### Premissas refutadas pela evidência própria — 12

Hipóteses plausíveis que a verificação matou, registradas para que o próximo pass não as refaça.

**Eixo B (7):** categorias `privacy`/`wasm` da tabela de rota inexistentes (existem; 17 diretórios) ·
`third-party-skills.py verify` sem gate (tem: `tests/test_third_party_skills.py:108-114` contra a
árvore real) · docs pt-BR de `aeo-geo/` violando a regra de idioma (os três carregam marcador de
exceção na linha 1, o mecanismo que `CLAUDE.md:30` prevê) · `/devteam:brief` não registrado nos
espelhos (está nos quatro) · bloco PLAN GATE incondicional num comando `conditional` (é o estilo da
casa em `backend`, `frontend`, `design`, `seo`, `docs`) · lista de `opt_out` divergente (casa nos 12)
· índice de ADRs fora de sincronia (60 linhas para 60 arquivos).

**Eixo C (3):** dispatcher de `Stop` sem saída rápida (`stop.sh:44-51` computa os caminhos tocados
uma vez e exporta) · hook novo sem registro (`CLAUDE-md/hooks.md:59,70,84` + 170 linhas de teste) ·
chaves de doc novas sem espelho bash (`docs-root.sh:42,44`).

**Eixo D (2):** sobreposição entre `brand-design-system` e `design-system-audit` sobre o doc
`design-system` (a divisão está escrita e concorda em `brand-design-system:19`, `docs-sync:136` e
`design-system-audit:159`) · skill nova sem dono no agente (`ui-ux-designer:52` carrega
`brand-design-system` condicionalmente).

---

## Rotação do banco

`helpers/archive-index.sh --dry-run` apontou 1 seção com mais de 90 dias (2026-08-21, 37 entradas).
Executado sem `--dry-run` por instrução do prompt, **falhou** — e é a **terceira reprodução** do HIGH
aberto `auto-archive-index-appends-archive-before-index-rewrite-no-rollback`, esta vez com o modo de
falha nomeado: o `mv` de `:162` é **entre dispositivos**, logo copy + unlink do alvo, e quebra com
`unable to remove target: Operation not permitted` **depois** de o append ao arquivo morto ter
sucedido — deixando **37 slugs duplicados** e `check-fingerprint-uniqueness.sh` vermelho em todo
`Stop`. Script sai 1 sem desfazer nada. Estado restaurado de snapshot; `✓ All 339 fingerprint slugs
are unique` confirmado. **A rotação não aconteceu** e a seção de 2026-08-21 segue no banco vivo.
Detalhe e o alvo preciso da correção em
[`00-guardiao-verificacao.md`](00-guardiao-verificacao.md#rotação-do-banco--executada-falhou-estado-restaurado).

---

## Relatórios

| Arquivo | Conteúdo |
|---|---|
| [`00-guardiao-verificacao.md`](00-guardiao-verificacao.md) | Fases 1 e 1b, item a item |
| [`01-agnosticismo-de-stack.md`](01-agnosticismo-de-stack.md) | Eixo A — 0 achados |
| [`02-referencias-e-consistencia.md`](02-referencias-e-consistencia.md) | Eixo B — 2 achados |
| [`03-fluxos-e-comandos.md`](03-fluxos-e-comandos.md) | Eixo C — 0 achados |
| [`04-agentes-e-skills.md`](04-agentes-e-skills.md) | Eixo D — 1 achado |
| [`05-economia-tokens.md`](05-economia-tokens.md) | Eixo E — 1 achado |
