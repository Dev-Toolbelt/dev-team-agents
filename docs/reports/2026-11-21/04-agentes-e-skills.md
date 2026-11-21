# Eixo D — Agentes e Skills — 2026-11-21

**Baseline:** `HEAD` = `17bfb26`

**1 achado original** (MEDIUM-HIGH).

---

## MEDIUM-HIGH

### A única instrução que manda o `product-analyst` escrever o briefing vive dentro de um gate que exclui escrever o briefing

- **Fingerprint:** `agent-product-analyst-briefing-load-nested-under-backlog-output-gate`
- **Alvo:** `agents/product-analyst.md`
- **Evidência:** `agents/product-analyst.md:32` é **um parágrafo só**, aberto por um gate:

  > "**Conditional load — only when you are about to produce backlog output** (the requirements
  > document in Step 5, specs in Step 5b, or sprint files in Step 6): load
  > `skills/shared/backlog-template/SKILL.md` for the canonical structure. **A discovery,
  > interrogation, or question-round turn that writes no backlog file does not load it.** When about
  > to write a spec (Step 5b), also load `skills/shared/spec-gate/SKILL.md`. In `gated`, stage 1 does
  > not load backlog-template — only stage 5 does. **When handed a client's filled-in briefing form,
  > load `skills/shared/client-briefing/SKILL.md` and write the `client-briefing` doc it defines.**"

  A frase do briefing é a última de um parágrafo cujo escopo declarado é "only when you are about to
  produce backlog output". E escrever o `client-briefing` **não é** backlog output:
  `skills/shared/doc-flow/SKILL.md:78` é explícito — "Client-level docs | `client-briefing` and
  `brand-guide` **sit outside the per-product chain**". `commands/brief.md` roda o briefing como
  kickoff de cliente, antes de qualquer plano ou sprint.

  Confirmação de que não há outra via: `grep -in 'briefing\|brand' agents/product-analyst.md`
  devolve **apenas a linha 32**. Os 15 headings `##`/`###` do agente (`:10` a `:209`) não têm passo
  de briefing — `Step 5`, `Step 5b`, `Step 6`, `Gated Layout — Stages 0 and 1`, `Backlog Management
  Mode`, `Issue Tracker Integration` e nenhum para o kickoff.

  O que faz o fluxo funcionar hoje mora **fora** do agente: `commands/brief.md:34` — "Instruct it to
  load the `client-briefing` skill, follow it exactly, write the doc, and return the Open Items
  checklist."

- **Problema:** a instrução existe, mas aninhada sob uma condição que ela mesma não satisfaz. Um
  agente que leia seu próprio arquivo literalmente — e a frase do meio do parágrafo manda ler
  literalmente: "A discovery, interrogation, or question-round turn that writes no backlog file does
  **not** load it" — tem um gate fechado na frente da única instrução de briefing que possui.
- **Por que importa:** `/devteam:brief` é o único caminho que funciona, e funciona porque o **corpo
  do comando** restata a instrução. Qualquer outra via ao `product-analyst` — o usuário pedindo
  direto ao agente, um `/devteam:plan` com o formulário em mãos, um spawn vindo de
  `/devteam:orchestrate` — chega sem instrução nenhuma, porque a do arquivo está sob condição falsa.
  E a compensação no corpo do comando é a duplicação de regra que a doutrina de Canonical Rule Homes
  do repositório proíbe: a casa canônica da decisão de carregar a skill passa a ser o comando, não o
  agente. Nenhum gate pega isto — `helpers/agent-lint.sh` valida frontmatter, roster, `plan_gate` e
  `REVIEW_RESULT_AGENTS`, e `orphan-skill-scan` reporta `clean ✓` porque a skill **tem** um loader:
  o loader é justamente esta linha mal condicionada.
- **Causa provável, e ela importa para a proposta:** `agents/product-analyst.md` está em
  **exatamente 211 linhas**, o cap de `helpers/size-limits.sh:44` (`AGENT_LIMIT=211`). Com o arquivo
  no limite, uma regra nova não cabe como linha nova — cabe grudada no fim de um parágrafo que já
  existe. `agents/frontend-developer.md` também está em 211, e 7 dos 19 agentes estão entre 209 e
  211.
- **Proposta:** tirar a frase do briefing do parágrafo de backlog e dar-lhe sua própria condicional,
  chaveada no que de fato a dispara ("When handed a client's filled-in briefing form …"); então
  reescrever `commands/brief.md:34` para **apontar** para ela em vez de restatá-la. Se as 211 linhas
  não deixarem espaço, o corte barato no mesmo arquivo é `:194` (a enumeração de trackers sem skill),
  que já é achado aberto e pede extração.
- **Impacto positivo:** o briefing passa a funcionar por qualquer caminho que alcance o agente, não
  só pelo comando; a decisão de carga volta para a casa canônica; e a condição deixa de contradizer
  o `doc-flow`.
- **Impacto negativo / risco:** mais uma condicional para o agente avaliar em todo turno (hoje são
  duas no parágrafo, passariam a três linhas de gate), e o arquivo já está no cap — a mudança **exige**
  remover ou extrair outra coisa no mesmo commit, senão `size-limits` passa a falhar (não avisar:
  `AGENT_LIMIT` é `VIOLATIONS`, bloqueante). Separar a condicional também cria um segundo lugar que
  precisa ser patcheado junto se o nome da skill mudar, a menos que `brief.md` passe a referenciar em
  vez de repetir — o que é parte da proposta, não um custo extra.
- **Esforço:** Baixo

---

## Verificações sem achado

- **`name:` vs basename, nomes duplicados:** 172 skills, **0** divergências, **0** nomes duplicados
  entre categorias.
- **Skills grandes pedindo `references/`:** as cinco maiores autorais são
  `skills/architecture/orchestration/SKILL.md` (414 linhas / 23 KB),
  `skills/shared/migration-v1-to-v2/SKILL.md` (414 / 15,6 KB),
  `skills/shared/interaction-patterns/SKILL.md` (404 / 23,7 KB),
  `skills/shared/backlog-template/SKILL.md` (335 / 16,4 KB) e
  `skills/shared/docs-templates/SKILL.md` (301 / 11,3 KB) — nenhuma com `references/`. Todas as
  cinco já têm fingerprint aberto; Porta 5. A maior do repositório,
  `skills/third-party/emil-design-eng/SKILL.md` (674 / 27 KB), é vendorizada e não pode ser
  reestruturada aqui (ADR-0047).
- **Agentes acima do cap:** nenhum. Dois em exatamente 211 (`product-analyst`,
  `frontend-developer`); re-medição registrada na Fase 1b sob `agent-line-cap-…`.
- **Sobreposição entre as duas skills de design novas:** procurei conflito entre
  `skills/design/brand-design-system/SKILL.md` e `skills/design/design-system-audit/SKILL.md`, que
  escrevem o mesmo doc `design-system`. Não há: `brand-design-system:19` subordina o schema e o cap
  a uma casa única (`skills/shared/docs-sync/SKILL.md` § `design-system`, "which also owns how the
  two docs relate"), `docs-sync:136` nomeia as duas skills e declara a divisão fixa, e
  `design-system-audit:159` roteia para a outra quando o ponto de partida é uma imagem de marca. A
  divisão de responsabilidade está escrita nos três lugares e concorda.
- **Cobertura de dono das skills novas:** `brand-design-system` declara "Owner: `ui-ux-designer`, in
  Design Mode" e `agents/ui-ux-designer.md:52` carrega-a condicionalmente ("When handed a brand
  reference image (logo, moodboard), also load …") — a ponte existe no agente, não só no comando. É
  o contraste que torna o achado acima um defeito e não o padrão da casa: a skill irmã foi ligada ao
  agente certo, a do briefing não.
