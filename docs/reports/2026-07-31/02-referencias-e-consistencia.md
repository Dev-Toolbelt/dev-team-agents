# Eixo B — Referências e Consistência

**Data:** 2026-07-31 · **Baseline:** `f54569a`

---

## Saída dos gates

Todos os quatro validadores passam limpos no `HEAD` — o que significa que os achados deste eixo são,
por construção, coisas que **nenhum gate mede**.

| Gate | Saída |
|---|---|
| `helpers/agent-lint.sh` | `agent-lint: clean ✓` |
| `helpers/size-limits.sh` | `size-limits: clean ✓` |
| `helpers/orphan-skill-scan.sh` | `orphan-skill-scan: clean ✓` |
| `helpers/orphan-template-scan.sh` | `orphan-template-scan: clean ✓` |
| `helpers/check-fingerprint-uniqueness.sh` | `✓ All 131 fingerprint slugs are unique across 1 bank file(s).` |
| `.github/scripts/ci/02-readme-sync.sh` | `readme-sync OK ✓` — 3 pares EN ↔ pt-BR, todos OK |

Verificações de paridade feitas à mão, todas **sem divergência**:

- os 25 comandos da tabela do `CLAUDE.md` são exatamente os 25 de `ls commands/*.md`;
- os 17 agentes de `docs/agents.md` são exatamente os 17 de `ls agents/*.md`;
- `scripts/lib/tiers.json` ↔ `docs/providers.md:31-34` ↔ `docs/agents.md:29` — o mapa tier → model id
  bate nos três lugares, para os três providers;
- `scripts/lib/commands.json` tem `plan_gate` `opt_out` para exatamente `update`, `symlinks`,
  `health-check`, e `review` como `conditional` — igual ao que `CLAUDE.md:215` afirma;
- os 10 membros de `scripts/lib/` estão todos no bloco File Structure.

---

## HIGH

### `CLAUDE.md` documenta o gate de descrição de skill como não-bloqueante; ele foi promovido a bloqueante nesta janela

- **Fingerprint:** `docs-sync-claude-md-102-states-skill-desc-strict-false-non-blocking-while-agent-lint-31-sets-true-and-ci-promoted-it-same-day`
- **Alvo:** `CLAUDE.md`
- **Evidência:**
  `CLAUDE.md:102` — "Keep `description` within **95 characters** … `agent-lint.sh` reports
  over-budget descriptions as a **non-blocking warning today** (`SKILL_DESC_STRICT=false`)".
  Contra `helpers/agent-lint.sh:31` — `SKILL_DESC_STRICT=true`; e
  `helpers/agent-lint.sh:168` — `if [ "$SKILL_DESC_STRICT" = true ]; then` (empurra para `ERRORS`,
  não para `WARNINGS`). E `.github/scripts/ci/01-lint.sh:75-77` documenta explicitamente a promoção:
  "agent-lint is fully blocking as of 2026-07-31 — the 95-char skill `description` budget was its
  last advisory sub-check, and every violator has been trimmed (`SKILL_DESC_STRICT=true` …)".
- **Problema:** o `CLAUDE.md` afirma como verdade corrente o valor oposto ao do código, e cita a
  variável pelo nome com o valor errado. As duas frases foram escritas na mesma janela de commits
  (`bbb311a` tocou `CLAUDE.md`, `c7535b7` e `7736e20` tocaram o lint) e não foram reconciliadas.
- **Por que importa:** o `CLAUDE.md` é a instrução carregada em toda sessão deste repo. Um autor que
  o lê conclui que pode passar do orçamento de 95 chars com um aviso — e descobre no CI que o PR
  está vermelho. Pior: a frase convida a *não* corrigir, porque diz que o gate ainda está em
  rollout. A rubrica classifica isso como HIGH: documenta como verdade algo factualmente falso.
- **Proposta:** trocar a segunda metade de `:102` por "`agent-lint.sh` **falha** em descrições acima
  do orçamento (`SKILL_DESC_STRICT=true`, bloqueante no CI desde 2026-07-31)".
- **Impacto positivo:** elimina a única contradição código↔`CLAUDE.md` encontrada neste eixo; o
  autor descobre o limite antes do CI, não depois.
- **Impacto negativo / risco:** a frase passa a duplicar um estado que vive em duas outras fontes
  (`agent-lint.sh:31` e o comentário do CI). Se `SKILL_DESC_STRICT` voltar a `false` algum dia, há
  agora três lugares para atualizar em vez de dois. O custo é aceitável porque a variável é
  nomeada — mas é o mesmo mecanismo que produziu este achado.
- **Esforço:** Baixo

---

## MEDIUM

### `CLAUDE.md` afirma duas coisas incompatíveis sobre quem carrega `current-context`, com 40 linhas de distância

- **Fingerprint:** `docs-sync-claude-md-173-says-all-devteam-commands-load-current-context-while-213-lists-four-exceptions-as-the-complete-list`
- **Alvo:** `CLAUDE.md`
- **Evidência:**
  `CLAUDE.md:173` — "| `current-context` | **All** `/devteam:*` commands — detects branch/worktree
  state before executing |";
  `CLAUDE.md:213` — "**Exception — commands that do NOT load `current-context`:** `/devteam:commit`
  …, `/devteam:update` …, `/devteam:health-check` …, and `/devteam:learn` …. These four are **the
  complete list** — verify with `grep -L current-context commands/*.md`."
  O comando sugerido confirma que `:213` é o correto: `grep -L current-context commands/*.md` →
  `commands/commit.md`, `commands/learn.md`, `commands/health-check.md`, `commands/update.md`.
- **Problema:** a linha da tabela é uma generalização que a nota de exceção contradiz. A tabela é o
  que se lê ao procurar "quem usa esta skill"; a exceção está em outra seção, sob a tabela de
  comandos.
- **Por que importa:** as duas afirmações são carregadas na mesma sessão. Um agente que aplique a
  linha `:173` literalmente adiciona `current-context` a `commit.md` ou `learn.md` — o que é
  exatamente o que `:213` proíbe, e por um motivo bom (esses comandos não operam sobre escopo de
  branch). É um convite a uma regressão.
- **Proposta:** trocar o texto da célula de "All `/devteam:*` commands" para "Todos os `/devteam:*`
  **exceto os quatro listados na nota de exceção abaixo**" — ou simplesmente "os 21 comandos com
  escopo de branch (ver exceções)".
- **Impacto positivo:** remove a contradição; a tabela deixa de convidar a uma mudança que a nota
  proíbe.
- **Impacto negativo / risco:** a célula fica dependente da nota — quem lê só a tabela precisa
  navegar. E o número "21" vira mais um valor a manter sincronizado com a árvore, que é o tipo de
  contagem que já apodreceu antes neste arquivo. Preferir a forma sem número.
- **Esforço:** Baixo

---

## LOW-MEDIUM

### O comentário de convenção do próprio banco de fingerprints afirma que todas as 131 entradas estão sem marcador

- **Fingerprint:** `docs-sync-reports-index-md-99-legend-comment-claims-all-131-entries-unmarked-while-121-carry-executed-or-partial-marks`
- **Alvo:** `docs/reports/_index.md`
- **Evidência:** `docs/reports/_index.md:99` — "All 131 entries below are unmarked: they were
  re-verified as reproducing at HEAD 7f85ed7." Contra a contagem real no mesmo arquivo:
  `grep -E '^- \`[a-z]' docs/reports/_index.md | grep -cE '✅ \*\*Executed'` → **120**, mais 1
  ⚠️ Partial. Apenas **10** seguem sem marcador.
- **Problema:** a frase está dentro do bloco de comentário que define a legenda de status — o lugar
  exato onde um agente de auditoria procura para entender o estado do banco. Ela ficou verdadeira
  por menos de um dia: foi escrita em `e24b170` (2026-07-30) e invalidada pelo pass de execução do
  dia seguinte, que não a atualizou.
- **Por que importa:** o prompt de auditoria manda construir o *conjunto de exclusão* e o *conjunto
  verificável* a partir dos marcadores. Um agente que confie no comentário em vez de contar conclui
  que não há nada a verificar na Fase 1 — e pula a metade guardiã do pass inteiro. Este mesmo pass
  encontrou 5 marcações 🔴 que só apareceram porque a contagem foi refeita.
- **Proposta:** substituir a frase por uma que não carregue número — "Marcadores são aplicados por
  passes de execução e reverificados pela Fase 1 do pass seguinte; conte sempre, nunca confie nesta
  linha" — e mover a contagem para a tabela **Estatísticas**, que já é atualizada a cada pass.
- **Impacto positivo:** remove um número que apodrece por design de dentro do arquivo de controle;
  a contagem passa a viver no único lugar que tem rotina de atualização.
- **Impacto negativo / risco:** perde-se um resumo rápido no topo do arquivo. Quem só abre o
  `_index.md` passa a precisar rodar dois greps para saber o estado. Aceitável: o prompt de
  auditoria já manda rodar exatamente esses greps na Fase 0.
- **Esforço:** Baixo

---

## Candidatos descartados neste eixo

| Candidato | Porta / motivo |
|---|---|
| `docs/agents.md` teria 19 linhas de agente para 17 arquivos | **Falso positivo do meu próprio regex** — `:94-95` são linhas de uma tabela de *skills* (`frontend-design`, `web-design-guidelines`), não de agentes. Ambos existem em `skills/design/` |
| `.codex/` presente na raiz e não listado no `.gitignore` | `find .codex -type f` → **0 arquivos**. São diretórios vazios de um render local; `git status --untracked-files=all` está limpo. Sem consequência |
| `scripts/lib/__pycache__/` shipped | Já coberto: `.gitignore:10` |
| `release-prep` é user-invocable e não está na tabela User-Invocable Skills do `CLAUDE.md` | **Porta 3** — mesmo alvo e mesma remediação do 🔴 `ref-release-prep-skill-exists-twice-…` reaberto na Fase 1. Reapresentar seria contar o mesmo problema duas vezes |
| 142 arquivos `SKILL.md` na árvore vs "138/138 skills" afirmado na mensagem de `7736e20` | Mensagem de commit não é documentação mantida; não há gate nem doc que reafirme o número. Sem custo de manutenção concreto |
| ~30 "referências não resolvidas" no `CLAUDE.md` (`install.sh`, `stop.sh`, `tiers.json`, …) | Nomes-base citados em prosa, não caminhos. `helpers/orphan-template-scan.sh` — que testa resolução de verdade — passa limpo |
| ~9 "referências não resolvidas" no `README.md` | Idem, mais caminhos do projeto *instalado* (`.dev-team-agents/…`), que por definição não resolvem a partir deste repo |
