# Eixo B — Referências e consistência (2026-08-28)

**Baseline:** `HEAD` = `a67cac9` · **Baseline anterior:** `a67cac9`

## Método

Auditoria read-only sobre `a67cac9`. Para garantir zero escrita no repositório, os quatro helpers
foram executados numa **cópia integral da árvore** (`cp -r` → `/tmp`), preservando o estado git.
Baseline e pós-execução no repositório real são idênticos: `git status --short` = ` M
docs/reports/_index.md` + `?? docs/reports/2026-08-21/`, `git stash list` vazio, antes e depois.
**Nenhum arquivo foi modificado** — em particular, `orphan-skill-scan.sh` (que auto-corrige em
lugar) não disparou nenhum auto-fix nesta passagem.

### Saídas dos helpers

| Helper | Exit | Resumo |
|---|---|---|
| `helpers/orphan-skill-scan.sh` | **0** | Sem órfãs e sem referências quebradas. Só "ACTION SUGGESTED — duplicate skill loads": `backend-test-specialist.md` e `frontend-test-specialist.md` (`test-pyramid`) e `commands/merge.md` (`worktree`). Já verificados como **falsos positivos do scanner** no banco (`_index.md:479`) — a segunda ocorrência é citação de regra, não um segundo load |
| `helpers/orphan-template-scan.sh` | **0** | `orphan-template-scan: clean ✓` — os 5 templates têm consumidor resolvível |
| `helpers/agent-lint.sh` | **0** | `agent-lint: clean ✓` — frontmatter, drift `tiers.json` ↔ `model:` ↔ run-banner, identidade de skills, quiz-first e roster de comandos todos OK |
| `helpers/size-limits.sh` | **1** | Única violação: `⚠ CLAUDE.md: 602 lines (warning threshold: 600)`. Já registrado como HIGH (`auto-size-limits-claude-md-warning-counted-as-violation-turns-ci-lint-red`) |
| *(extra)* `helpers/preferences-sync-lint.sh` | 0 | `clean ✓ (2 mirrors checked)` |
| *(extra)* `.github/scripts/ci/02-readme-sync.sh` | 0 | 6 pares EN ↔ pt-BR estruturalmente paritários |

### Varreduras próprias

- **153 referências `skills/**/SKILL.md`** extraídas de `agents/`, `commands/`, `skills/`,
  `CLAUDE.md`, `CLAUDE-md/`, `templates/`, `README*.md`, `docs/*.md` → **0 quebradas**.
- **152 skills** × `name:` vs. basename do diretório → **0 divergências**; `uniq -d` sobre os
  `name:` → **0 duplicatas**.
- **Órfãs reais** (skill sem menção em `agents/` ou `commands/`) → só `skills/skill-creator`, que é
  user-invocable e isento por regra.
- **Referências `path.md § Seção`** resolvidas contra os headings reais → 0 quebras.
- **Templates**: nenhuma referência `templates/<x>.md` fora do contexto "repo".
- **Tabelas cruzadas verificadas OK**: `commands.json` (35) ↔ `commands/*.md` (35) ↔ tabela do
  `CLAUDE.md`; `plan_gate` ↔ texto do `CLAUDE.md`; `tier` de cada comando ↔ `tier` do agente-lead;
  `grep -L current-context commands/*.md` = exatamente os 6 documentados; 13 categorias em
  `checks-list.md`; `agent_effort` de `tiers.json` ↔ run-banner dos 18 agentes.

---

## HIGH

### `CLAUDE.md` afirma que `effort:` só existe em agentes do tier `repetitive`, enquanto 5 agentes de `backend-exec`/`frontend` carregam a chave

- **Fingerprint:** `docs-sync-claude-md-effort-key-scope-vs-agent-effort-map`
- **Alvo:** `CLAUDE.md`
- **Evidência:** `CLAUDE.md:64` — "A fifth key, `effort:`, is present **only** on agents whose tier
  defines one in `tiers.json` (today: `repetitive`); the lint fails both on a missing one and on an
  extra one"; `CLAUDE.md:73` — "| `backend-exec` | `sonnet` | none — banner shows `session-default` |
  …"; `CLAUDE.md:74` — idem para `frontend`.
  Contra a árvore: `agents/qa-specialist.md`, `agents/database-specialist.md`,
  `agents/devops-specialist.md`, `agents/backend-test-specialist.md` (todos `tier: backend-exec`) e
  `agents/frontend-test-specialist.md` (`tier: frontend`) têm `effort: low` na frontmatter e
  `| … | \`low\` |` no run-banner.
- **Problema:** três afirmações do bloco *Agents* estão factualmente erradas no HEAD. O `agent_effort`
  de `tiers.json` sobrepõe o nível do tier em 5 dos 18 agentes, e a frontmatter reflete isso — mas
  `:64` diz "only … (today: `repetitive`)" e a tabela declara `none` justamente para os dois tiers
  onde a exceção vive. O parágrafo "Per-agent effort overrides" (`:80`) descreve o `agent_effort` mas
  nunca corrige a regra de frontmatter nem as células da tabela.
- **Por que importa:** `CLAUDE.md` é a norma de autoria, lida antes de tocar em qualquer agente. Um
  autor que siga `:64` literalmente remove `effort: low` de 5 agentes (a chave "não deveria estar
  ali") e rebaixa a configuração de esforço de todo o time de execução; o `agent-lint.sh` pega o erro
  **depois**, e o mesmo autor pode "consertar" alterando `tiers.json` no sentido errado, que o lint
  aceita. Ler `:73` também leva a supor que `qa-specialist` roda no esforço da sessão, quando roda em
  `low`.
- **Proposta:** reescrever `:64` para "presente exatamente quando `tiers.json` resolve um `claude`
  effort para o agente — por `agent_effort` (5 agentes hoje) ou pelo tier (`repetitive`)"; trocar
  `none` por "none pelo tier — ver `agent_effort`" nas células `backend-exec` e `frontend`.
- **Impacto positivo:** elimina a única regra de frontmatter do repositório que contradiz a própria
  árvore, e alinha a tabela de tiers com o que `agent-lint.sh` de fato exige.
- **Impacto negativo / risco:** a tabela de tiers deixa de ser resposta fechada — passa a exigir
  consulta ao `agent_effort` para saber o efeito real, o que aumenta o custo de leitura. E cria uma
  **quarta** cópia da lista de 5 agentes (já em `tiers.json`, `CLAUDE.md:80` e `docs/providers.md:42`),
  sem gate que a mantenha sincronizada.
- **Esforço:** Baixo

---

## MEDIUM-HIGH

### `docs/agents.md` (e o espelho pt-BR) diz que `backend-developer` "pergunta uma vez" sobre worktree, comportamento que o default `worktree_active: true` não produz

- **Fingerprint:** `docs-sync-docs-agents-md-worktree-asks-once-vs-preference-default`
- **Alvo:** `docs/agents.md`
- **Evidência:** `docs/agents.md:55` — "Reads project context and code standards before writing any
  code. **Asks once whether to isolate work in a git worktree.**";
  `docs/agents.pt-BR.md:55` — "**Pergunta uma vez se deve isolar o trabalho em um git worktree.**";
  `scripts/lib/preferences-defaults.json` — `"worktree_active": true`;
  `CLAUDE.md` § *Canonical worktree decision cascade*, passo 2 — "`true` → set up a worktree
  **without asking**".
- **Problema:** na configuração default de qualquer instalação nova, o agente **não pergunta**: o
  passo 1 lê `.worktree-session` e segue em silêncio, e o passo 2 lê `worktree_active: true` e cria o
  worktree sem prompt. O `AskUserQuestion` só ocorre no passo 3, que é o caso legado (chave ausente).
  A frase descreve exatamente o caminho que deixou de ser o padrão.
- **Por que importa:** `docs/agents.md` é a "canonical agent reference" apontada pelo `README.md:15`
  e `:141`. Um usuário lê que será consultado, roda `/devteam:backend`, e o agente cria um worktree e
  um stack Docker isolado sem perguntar nada — a divergência é sobre o comportamento visível mais
  surpreendente do harness. Como a frase está nos dois idiomas e o gate `02-readme-sync.sh` compara só
  estrutura, ele passa verde com o defeito espelhado.
- **Proposta:** trocar por "Resolve a decisão de worktree pela cascata (`.worktree-session` →
  `worktree_active` → pergunta), sem perguntar quando a preferência já está definida" nos dois
  arquivos, na mesma linha, mantendo a contagem de linhas para não quebrar o gate de paridade.
- **Impacto positivo:** remove a última descrição de comportamento pré-`preferences.json` da
  referência canônica de agentes.
- **Impacto negativo / risco:** a frase fica mais longa e mais técnica num documento cuja função é ser
  legível por não-usuários do repo; e passa a ser mais um ponto que precisa ser repatchado sempre que
  a cascata mudar — sem gate que detecte, exatamente como o atual.
- **Esforço:** Baixo

---

## MEDIUM

### O `description` de cada comando existe em duas fontes (frontmatter e `commands.json`) e as 35 já divergem, sem gate

- **Fingerprint:** `ref-command-description-duplicated-frontmatter-vs-commands-json`
- **Alvo:** `scripts/lib/commands.json`
- **Evidência:** `commands/status.md:2` — "description: Show git status, staged/unstaged changes, and
  last 5 commits as formatted tables"; `scripts/lib/commands.json:53` — `"description": "Show git
  status, staged/unstaged changes, and last 5 commits as formatted tables. **Optional branch-name
  argument.**"`. `scripts/lib/render_provider.py:901` (opencode) e `:922` (codex) usam
  `meta.get("description", "")`, isto é, o valor do `commands.json`; `command-map.json` marca `claude`
  com `"frontmatter_passthrough": true`. Comparação automatizada: **35 divergências em 35 comandos**.
- **Problema:** a mesma string de UI tem dois donos. No Claude Code o usuário lê o `description:` da
  frontmatter (repassado byte-a-byte); no opencode e no Codex lê o do `commands.json`. Nenhum lint
  compara os dois — `check_command_roster` valida `tier`, `agent` e o pin de `model:`. A maioria das
  35 divergências é cosmética, mas ao menos uma é informativa: só o `commands.json` menciona o
  argumento opcional de branch do `/devteam:status`.
- **Por que importa:** o mesmo comando se apresenta de forma diferente conforme o provider, e o
  usuário do Claude Code — o provider **default** — é o que recebe a versão sem a menção ao
  argumento. Sendo 35/35 já divergentes, não é risco futuro: é drift consumado.
- **Proposta:** eleger `commands.json` como fonte única e fazer `render_command_claude` reescrever o
  `description:` a partir dele; ou — alternativa mais barata — adicionar a comparação a
  `check_command_roster` e reconciliar as 35 strings.
- **Impacto positivo:** o mesmo comando passa a se apresentar igual nos três providers, e o argumento
  opcional do `/devteam:status` deixa de ser invisível no provider default.
- **Impacto negativo / risco:** a via do renderer quebra a garantia "Claude recebe o arquivo
  byte-idêntico" que o CI contract checker hoje verifica — teria que ser afrouxada. A via do lint
  transforma 35 arquivos numa PR única e adiciona um gate bloqueante a um campo cosmético, com
  fricção em toda futura edição de comando.
- **Esforço:** Médio

### A lista fechada de "Coding agents" do `CLAUDE.md` tem 8 nomes, mas 9 agentes carregam `## Worktree Isolation`

- **Fingerprint:** `docs-sync-claude-md-coding-agents-list-omits-seo-specialist`
- **Alvo:** `CLAUDE.md`
- **Evidência:** `CLAUDE.md:109` — "**Coding agents** (`backend-developer`, `frontend-developer`,
  `mobile-developer`, `database-specialist`, `devops-specialist`, `ui-ux-designer`,
  `backend-test-specialist`, `frontend-test-specialist`) must also include a **`## Worktree
  Isolation`** section. … It used to be inlined in **all eight agents**".
  `grep -c "^## Worktree Isolation" agents/*.md` → 1 em **nove** arquivos, os oito listados **mais
  `agents/seo-specialist.md`**. `agents/seo-specialist.md` entrou em `1b5bb08` (2026-08-03); a lista
  de `:109` foi tocada pela última vez em 2026-05-04.
- **Problema:** a lista é enunciada como fechada ("all eight agents") e nunca foi atualizada quando o
  `seo-specialist` — que edita `robots.txt`, sitemaps, metatags e JSON-LD, portanto escreve código —
  foi adicionado com a seção. Nada valida a lista.
- **Por que importa:** duas leituras erradas possíveis, ambas ruins. Um autor que trate a lista como
  normativa remove a seção do `seo-specialist`, e o agente passa a editar arquivos direto na branch
  corrente ignorando `worktree_active`; um autor que adicione um novo agente de código não sabe que
  precisa incluir a seção, porque a lista não é gate. A entrada
  `token-worktree-isolation-block-7-lines-x-8-agents` do banco também propaga a contagem defasada.
- **Proposta:** substituir a enumeração por um critério ("todo agente que escreve arquivos do
  projeto") + a lista atual dos 9 como exemplo, e adicionar ao `agent-lint.sh` um check de presença
  de `## Worktree Isolation` nesses agentes.
- **Impacto positivo:** fecha a janela em que um agente de código nasce sem isolamento de worktree, e
  alinha a contagem citada em três lugares.
- **Impacto negativo / risco:** um critério em prosa ("escreve arquivos do projeto") é mais ambíguo
  que a lista fechada — `technical-writer` e `product-analyst` também escrevem arquivos, e a fronteira
  passa a exigir julgamento. Se o check for adicionado ao lint, ele precisa de uma allowlist própria,
  que é a mesma lista voltando por outra porta.
- **Esforço:** Baixo

---

## LOW-MEDIUM

### `CLAUDE.md` chama a Context Loading Order de "12 items"; ela tem 11 (e tinha 10 quando o número foi escrito)

- **Fingerprint:** `docs-sync-claude-md-context-list-item-count-12-vs-11`
- **Alvo:** `CLAUDE.md`
- **Evidência:** `CLAUDE.md:158` — "| Foundational Rule context list (**12 items**) |
  `skills/shared/project-context/SKILL.md` | Delegate in one line… |";
  `skills/shared/project-context/SKILL.md:102`–`:114` — a lista vai de `1. README.md` a
  `11. docs/wiki/README.md`. `git show 7736e20:skills/shared/project-context/SKILL.md` — no commit
  que **introduziu** "12 items" a lista terminava em `10. docs/backlog/`. O número nunca esteve
  correto.
- **Problema:** o único número na tabela *Canonical Rule Homes* que descreve o conteúdo da casa
  canônica está errado desde que foi escrito — por duas unidades na origem, por uma hoje.
- **Por que importa:** consequência funcional nenhuma — nenhum script lê o número. O custo é de
  confiança: é a tabela que o `CLAUDE.md` usa para provar que uma regra tem uma cópia só, e o único
  fato verificável nela não confere. Um autor que use "12 items" como checklist ao revisar a skill
  vai procurar um item inexistente.
- **Proposta:** remover a contagem — "Foundational Rule context list" basta, e é a forma que não
  envelhece a cada item acrescentado.
- **Impacto positivo:** tira do `CLAUDE.md` um número que só pode ficar errado, já que a lista cresce
  e ele não tem gate.
- **Impacto negativo / risco:** perde-se a única pista de tamanho que o `CLAUDE.md` dava sobre a
  lista, o que torna a linha da tabela menos informativa para quem decide se vale abrir a skill.
- **Esforço:** Baixo

---

## LOW

### `README.pt-BR.md:141` aponta para a referência de agentes em inglês, enquanto `:15` aponta para a tradução

- **Fingerprint:** `docs-sync-readme-ptbr-agents-link-points-to-english-doc`
- **Alvo:** `README.pt-BR.md`
- **Evidência:** `README.pt-BR.md:141` — "O time tem **18 agentes** cobrindo todo o ciclo de vida.
  Detalhes completos na [Referência de Agentes](docs/agents.md)."; `README.pt-BR.md:15` — "→ Veja a
  [Referência de Agentes](docs/agents.pt-BR.md) completa." `docs/agents.pt-BR.md` existe e é mantido
  em paridade.
- **Problema:** os dois links para o mesmo documento no mesmo README apontam para arquivos
  diferentes; o de `:141` leva o leitor pt-BR ao texto em inglês.
- **Por que importa:** o `02-readme-sync.sh` compara a **contagem** de links por seção entre EN e
  pt-BR, não o **alvo** deles — um link idêntico ao do EN é exatamente o padrão que o gate não
  distingue de uma tradução correta. Custo real baixo, mas é inconsistência interna no arquivo de
  entrada do público pt-BR.
- **Proposta:** trocar `docs/agents.md` por `docs/agents.pt-BR.md` em `README.pt-BR.md:141`.
- **Impacto positivo:** os dois pontos de entrada passam a levar o leitor pt-BR ao mesmo documento
  traduzido.
- **Impacto negativo / risco:** aumenta a superfície de tradução obrigatória — um período em que
  `docs/agents.pt-BR.md` ficar defasado expõe o leitor ao conteúdo antigo em vez de ao inglês atual.
  `docs/providers.md` e os três `docs/install-*.md`, sem par pt-BR, continuam linkados em inglês em
  `:38-40` e `:44` — a inconsistência não some, só muda de lugar.
- **Esforço:** Baixo

---

## Descartados por duplicação

| Candidato | Porta que rejeitou |
|---|---|
| `helpers/size-limits.sh` sai 1 no HEAD por `CLAUDE.md: 602 lines` | **Porta 5 (estado)** — `auto-size-limits-claude-md-warning-counted-as-violation-turns-ci-lint-red` (HIGH, aberto) |
| Teto de agente documentado como 205 (`CLAUDE.md:92`/`:313`) vs. `AGENT_LIMIT=211` (`size-limits.sh:44`) | **Porta 5** — `agent-line-cap-205-documented-in-claude-md-vs-211-enforced-by-size-limits` |
| Cargas duplicadas de `test-pyramid` e `worktree/SKILL.md` reportadas pelo `orphan-skill-scan` | **Porta 5** — `_index.md:479` já as classificou como falsos positivos do scanner nesta mesma árvore |
| `docs/agents.md:28` lista `backend-test-specialist` no tier `repetitive` | **Porta 5** — `ref-docs-agents-md-tier-column-stale-…` (HIGH) |
| `CLAUDE.md:245` aponta `/devteam:update` para `hooks/pre-tool-use/01-check-updates.sh`, renomeado para `_disabled-…` | **Porta 3 (2 de 3)** — `ref-check-updates-shim-and-update-sh-exec-renamed-away-01-check-updates-hook`: mesma causa raiz e mesma remediação; só o alvo difere |
| `CLAUDE-md/preferences.md:42,46` citam `01-check-updates.sh` e `:40-50` citam `stop/04-notifier.sh`, ambos desativados | **Porta 3 (2 de 3)** — combinação de `ref-check-updates-shim-…` e `ref-notifier-documented-as-live-in-four-docs-while-hook-file-is-disabled` (HIGH) |
| `skills/shared/notifier/SKILL.md:52,60` descrevem `stop/04-notifier.sh` disparando "After each turn" | **Porta 1 (literal)** — `ref-notifier-documented-as-live-in-four-docs-…`, alvo e linhas idênticos |
| `helpers/preferences-sync-lint.sh` não é invocado por nada e não consta da árvore `helpers/` do `CLAUDE.md:308-317` | **Porta 3 (2 de 3)** — `flow-helpers-archive-index-sh-orphan-of-hook-…` (HIGH): mesma causa raiz ("helper escrito, commitado e invocado por nada") e mesma remediação; só o alvo difere. A omissão no *File Structure* isolada cai na **Porta 5** |
| `CLAUDE.md:300` lista 3 dos 5 templates em *File Structure* | **Porta 5** |
| Tabela de comandos do `README.md`/`README.pt-BR.md` omite `/devteam:install` (34 de 35) | **Porta 5** |
| `docs/reports/_index.md` diz "All 131 entries" com o banco já em 213 | **Porta 5** — `docs-sync-reports-index-md-99-legend-comment-claims-all-131-entries-unmarked…` |
| `CLAUDE.md:131` diz `SKILL_DESC_STRICT=false` enquanto `agent-lint.sh` usa `true` | **Porta 1 (literal)** — `docs-sync-claude-md-102-states-skill-desc-strict-false-…` (HIGH) |
| `docs/agents.md:42` descreve o run banner só na abertura, enquanto `CLAUDE.md` e `docs/providers.md:63` exigem duas emissões | **Descartado por mérito** — passou as três portas, mas a frase remete a `skills/shared/model-identity/SKILL.md`, que carrega a regra completa; é omissão com ponteiro válido, não afirmação falsa. Registrado para o próximo pass |
| `docs/providers.md` e os três `docs/install-*.md` sem par pt-BR, linkados em inglês no `README.pt-BR.md:38-40,44` | **Descartado por mérito** — o `02-readme-sync.sh` só exige o sentido pt-BR → EN e a regra de sincronia cobre apenas o par `README.md` ↔ `README.pt-BR.md`. Traduzir é escolha editorial, não drift |
