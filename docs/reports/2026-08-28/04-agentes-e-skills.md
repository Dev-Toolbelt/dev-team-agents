# Eixo D — Agentes e skills (2026-08-28)

**Baseline:** `HEAD` = `a67cac9` · **Baseline anterior:** `a67cac9`

## Método

1. **Banco de fingerprints** — versão da árvore de trabalho de `docs/reports/_index.md` (213
   entradas, incluindo as 37 não commitadas de 2026-08-21) e
   `docs/reports/2026-08-21/04-agentes-e-skills.md` na íntegra. Extraídos os 58 fingerprints com
   prefixo `agent-`/`skill-`, separando os 24 abertos dos 34 marcados.
2. **Checagens mecânicas** — `helpers/agent-lint.sh` (limpo ✓), `helpers/size-limits.sh`,
   `helpers/orphan-skill-scan.sh`, `wc -l agents/*.md`, `find skills -name SKILL.md | xargs wc -l`.
3. **Conformidade estrutural** — matriz de 18 agentes × 6 requisitos de `CLAUDE.md` (Foundational
   Rule, Immutability Warning, `## Model Identity`, bloco `<!-- run-banner -->`, `## Before You
   Finish` como última seção, `## Worktree Isolation`). **Todos os 18 passam nos cinco primeiros.**
4. **Espelhamento de tier** — `tier:`/`model:`/`effort:` do frontmatter contra `scripts/lib/tiers.json`
   (incluindo `agent_effort`) e contra a célula Effort de cada run-banner. **Os 18 estão consistentes
   nos três eixos; nenhum achado.**
5. **Deduplicação de regras** — linhas verbatim repetidas em ≥3 corpos (`sort | uniq -c`), cruzadas
   com a tabela *Canonical Rule Homes*.
6. **Cobertura de skills** — para cada linha da tabela, quais agentes carregam a skill vs. quem a
   tabela obriga.
7. **Alcançabilidade em runtime** — para cada regra delegada, se o arquivo-alvo é instalado, via
   `KEEP_ROOT` em `scripts/install.sh:369` e `scripts/lib/strip-tarball.sh`.
8. **Anti-duplicação** — Portas 1, 2 e 3 para os 5 candidatos; comparação de 3 atributos contra cada
   linha colidente; Porta 5 (conjunto aberto).

**Escopo negativo confirmado:** nenhuma SKILL.md excede 500 linhas (maior: `migration-v1-to-v2` com
438, já aberto); nenhuma `description` de skill excede 95 caracteres; nenhum agente excede o teto
imposto de 211.

---

## HIGH

### Os 9 agentes que editam arquivos delegam a cascata de worktree a um `CLAUDE.md` que nunca é instalado, e a skill que a contém está atrás da decisão que ela define

- **Fingerprint:** `agent-worktree-cascade-delegates-to-unshipped-claude-md`
- **Alvo:** `agents/backend-developer.md`, `frontend-developer.md`, `mobile-developer.md`,
  `database-specialist.md`, `devops-specialist.md`, `ui-ux-designer.md`, `backend-test-specialist.md`,
  `frontend-test-specialist.md`, `seo-specialist.md`
- **Evidência:**
  - `scripts/install.sh:369` — "`KEEP_ROOT=(agents scripts skills templates commands)`" — seguido de
    `:371-378`, que faz `rm -rf` em tudo fora da allowlist. **`CLAUDE.md` não está nela.**
  - `agents/mobile-developer.md:39` — "Resolve the worktree decision before editing any file, using
    the canonical cascade in `CLAUDE.md` → **Worktree Isolation** … When the resolved decision is
    `worktree=yes`, load `skills/shared/worktree/SKILL.md` …; **otherwise work on the recorded branch
    and do not load the skill.**"
  - `agents/devops-specialist.md:40` — texto idêntico, incluindo a mesma cláusula final.
  - `scripts/install.sh:829` e `:874` — os **dois** únicos blocos que o instalador anexa ao
    `CLAUDE.md` do projeto-alvo são `pre-compact-auto-summary` e `commit-rule`. A cascata não é
    injetada.
  - `grep -rn 'worktree=no\|worktree=yes' agents/` — **nenhum corpo de agente contém o formato de
    escrita do arquivo de sessão.** Ele existe apenas em `CLAUDE.md:114,118` (não instalado),
    `skills/shared/worktree/SKILL.md:28,37`, `references/session-protocol.md:28,37,53,79` e
    `commands/merge.md:62` (consumidor).
  - `CLAUDE.md:162` declara **duas** casas canônicas para a mesma regra, contrariando a própria
    abertura da seção em `:153` ("lives in exactly **one** skill").
  - `CLAUDE.md:111` — o rótulo real é "**Canonical worktree decision cascade**". Não existe seção
    chamada "Worktree Isolation" em `CLAUDE.md`: `:109` usa esse nome para a seção que o **corpo do
    agente** deve conter. Oito dos nove agentes apontam para o rótulo inexistente; só
    `agents/seo-specialist.md:36` usa o correto.
- **Problema:** num projeto instalado, `.dev-team-agents/CLAUDE.md` não existe — a allowlist o remove.
  O `CLAUDE.md` que o agente encontra é o **do projeto do usuário**, populado com dois blocos
  gerenciados, nenhum deles a cascata. O ponteiro não falha ruidosamente: resolve para um arquivo que
  existe, parece autoritativo e não contém a seção. Pior, a rota de fallback está fechada por
  construção — `mobile-developer` e `devops-specialist` mandam explicitamente **não** carregar
  `skills/shared/worktree/SKILL.md` quando a decisão é `worktree=no`, que é exatamente o ramo em que o
  agente precisa escrever `worktree=no branch=<name>`.
- **Por que importa:** a garantia central declarada em `CLAUDE.md:121` — "This ensures multi-agent
  workflows resolve the worktree decision **exactly once**" — depende inteiramente de o primeiro
  agente **escrever** o arquivo de sessão. Nenhum dos 9 tem fonte instalada para o formato dessa
  escrita no ramo `worktree=no`. O resultado prático em `/devteam:fullstack` (backend + frontend +
  database + ui-ux + dois test-specialists) é que cada agente re-resolve a decisão do zero e volta a
  perguntar, ou grava um marcador com formato inventado que o passo 1 do próximo agente não sabe ler.
  O repositório já reconheceu essa classe exata de falha e a corrigiu para outra regra: o comentário
  de `scripts/install.sh:868-872` justifica o Step 8b dizendo que sem a injeção "a direct-prompt commit
  in an installed project has **no shipped file** telling it to load conventional-commits". O mesmo
  diagnóstico se aplica à cascata de worktree, e ela não recebeu o mesmo tratamento.
- **Proposta:** eleger `skills/shared/worktree/SKILL.md` § Decision Cascade como casa canônica única
  (ela já contém a cascata completa **e é instalada**), reescrever as 9 seções `## Worktree Isolation`
  para carregá-la **incondicionalmente** — antes de resolver a decisão, não depois — e remover as
  cláusulas "do not load the skill". Atualizar `CLAUDE.md:162` para apontar a uma casa só e reduzir
  `:111-121` a um resumo que referencia a skill.
- **Impacto positivo:** a cascata passa a ser alcançável em 100% dos projetos instalados; o formato do
  arquivo de sessão fica disponível nos dois ramos; a garantia "exatamente uma vez" ganha um mecanismo
  real; a tabela *Canonical Rule Homes* deixa de violar a própria regra de casa única.
- **Impacto negativo / risco:** carregar a skill incondicionalmente custa uma leitura (~90 linhas) por
  agente em toda tarefa, **inclusive nas que terminam em `worktree=no`** — em `/devteam:fullstack`
  isso multiplica por 6. O ganho de linhas de corpo não compensa o custo em tokens: é troca deliberada
  de custo por corretude, não otimização. Além disso `skills/shared/worktree/SKILL.md:39` já delega a
  `references/session-protocol.md` "for the full cascade", o que pode transformar uma leitura em duas
  se a redação não deixar claro que o SKILL.md basta para resolver a decisão.
- **Esforço:** Médio

---

## MEDIUM-HIGH

### O `<HARD-GATE>` do Scope Lock é escrito para quatro agentes de execução nomeados, e nenhum dos quatro carrega a skill que o contém

- **Fingerprint:** `skill-spec-gate-scope-lock-hard-gate-unreachable-by-execution-agents`
- **Alvo:** `skills/shared/spec-gate/SKILL.md`
- **Evidência:**
  - `:52` — "`## Scope Lock — Execution Agents`"
  - `:54-55` — "Every coding agent (`backend-developer`, `frontend-developer`, `mobile-developer`,
    `database-specialist`) reads the spec (and contract, if one exists) linked from its sprint task
    **before** writing code"
  - `:65-70` — "`<HARD-GATE>` … A feature is never marked implemented or `done` while an open
    assumption remains. … **\"I assumed X and moved on\" is not a valid end state at any severity** —
    this holds even when the assumption turned out correct."
  - `grep -ln spec-gate agents/*.md` → `product-analyst.md`, `qa-specialist.md`,
    `software-architect.md`. **Nenhum dos quatro agentes nomeados na própria seção.**
  - `CLAUDE.md:171` — "Load it wherever the table applies — … **coding agents (scope-lock, business
    amendments)**, qa-specialist (sync gate)."
  - `commands/backend.md:10` (idem `frontend.md:10`, `fullstack.md:10`, `mobile.md:10`, `fix.md:12`) —
    "If the task links a spec …, load `skills/shared/spec-gate/SKILL.md` — every spawned agent below
    treats its Given/When/Then as the implementation boundary and asks rather than assumes."
- **Problema:** a skill é carregada no **orquestrador**, não no subagente. Um `Load` executado no
  contexto principal não atravessa a fronteira do Task tool: o agente spawnado recebe o prompt de
  spawn, o próprio corpo e as skills que **ele** carrega. O que os cinco comandos repassam é uma
  paráfrase de uma linha, que não contém o `<HARD-GATE>`, não contém a regra de precedência
  contrato-vs-spec (`:62-63`) e não contém a instrução de usar `AskUserQuestion`. `CLAUDE.md:171`
  manda os coding agents carregarem a skill; nenhum dos oito o faz.
- **Por que importa:** o `<HARD-GATE>` é a única regra do repositório que proíbe encerrar uma feature
  com uma suposição em aberto, e é dirigida **nominalmente** a quatro agentes que não podem lê-la.
  Fora dos cinco comandos que carregam a skill a cobertura é zero: `/devteam:refactor`,
  `/devteam:relayout` e `/devteam:audit` não a carregam, e uma invocação direta de `backend-developer`
  (via prompt do usuário ou roteamento de `/devteam:architect`) não passa por comando nenhum. Nenhum
  gate detecta: `helpers/agent-lint.sh` valida frontmatter, identidade de skill e roster — não
  cobertura de skill por agente.
- **Proposta:** adicionar o load de `skills/shared/spec-gate/SKILL.md` — condicionado à existência de
  `docs/specs/<feature>.md` no contexto da tarefa — aos quatro agentes nomeados em `:54-55`. Como os
  quatro nomes estão hard-coded na skill e podem envelhecer, trocar a enumeração por "todo agente com
  `## Worktree Isolation`" ou adicionar ao `agent-lint.sh` uma checagem que compare a lista de
  `:54-55` com quem realmente carrega a skill.
- **Impacto positivo:** o `<HARD-GATE>` passa a alcançar os executores para quem foi escrito,
  inclusive nos caminhos que não passam por um dos cinco comandos; elimina a divergência entre
  `CLAUDE.md:171` e a árvore.
- **Impacto negativo / risco:** `spec-gate` tem 120+ linhas e quatro dos alvos (`backend-developer`
  183, `frontend-developer` **211**, `database-specialist` 197, `mobile-developer` 188) somam custo de
  contexto a cada spawn — `frontend-developer` está **no teto** e não comporta a linha de load sem
  extração prévia. O load precisa ser genuinamente condicional à presença do spec, ou o custo recai
  sobre todas as tarefas sem spec, que são a maioria. Há ainda risco de dupla aplicação: com o comando
  **e** o agente carregando a skill, o orquestrador pode reexecutar o Sync Gate que pertence ao
  `qa-specialist`.
- **Esforço:** Médio

---

## MEDIUM

### O bloco de detecção e nomenclatura de branch do Jira está replicado em 13 agentes sem linha na tabela Canonical Rule Homes, e já divergiu em placeholder, tipos e gate de aprovação

- **Fingerprint:** `agent-jira-detection-branch-naming-block-duplicated-no-canonical-home`
- **Alvo:** `agents/backend-test-specialist.md`, `database-specialist.md`, `devops-specialist.md`,
  `frontend-test-specialist.md`, `mobile-developer.md`, `frontend-developer.md` (+ 7 outros com o
  bloco de detecção)
- **Evidência:**
  - `skills/integrations/jira/SKILL.md:56` (fonte) — "Pattern: `{type}/{taskId}_short-description`"
  - `:58` — "`{type}` — Conventional Commits type (feat, fix, docs, chore, refactor, perf, test,
    build, ci, revert)"
  - `:71-73` — "**Start work on an issue:** … 2. **Propose** branch name → **on approval**, create
    branch (or worktree)"
  - `agents/database-specialist.md:170` — "Create the branch using the Jira naming pattern:
    `{type}/{issueKey}_short-description` — use `fix` for bug-driven schema fixes, `feat` for new
    schema additions, `refactor` for restructuring"
  - `agents/devops-specialist.md:187` — mesma linha com **quatro** tipos diferentes (`ci`, `build`,
    `chore`, `feat`)
  - `agents/backend-test-specialist.md:131` e `frontend-test-specialist.md:176` — "Create the branch
    using the Jira naming pattern **with type `test`**"
  - `grep -ln 'integrations/jira/SKILL.md' agents/*.md | wc -l` → **13**; a linha "**Detection**: load
    `skills/integrations/jira/SKILL.md` when any of the following are true:" aparece verbatim em 9
  - `grep -rno '{issueKey}' agents/ | wc -l` → **5** · `grep -rno '{taskId}' skills/integrations/jira/SKILL.md | wc -l` → **2**
  - `CLAUDE.md:153` — "A rule that applies to more than one agent lives in exactly **one** skill.
    Agents load that skill and reference the rule by name; they must not paraphrase or inline it."
- **Problema:** o bloco *Detection → When Jira is active → branch naming* foi replicado em 13 corpos
  sem nenhuma linha correspondente na tabela *Canonical Rule Homes*, que é o gate documental
  exatamente para esse padrão. A divergência já está instalada, em três eixos: **(a) placeholder** — a
  skill define `{taskId}`, os agentes escrevem `{issueKey}`, nome que não existe na fonte; **(b)
  tipos** — a skill lista os 10 tipos e manda derivar o tipo do resumo e do issue type, enquanto cada
  agente pré-restringe a um subconjunto próprio e incompatível entre si; **(c) gate de aprovação** — a
  skill exige "Propose branch name → **on approval**, create branch", e as seis cópias mandam "Create
  the branch" **sem nenhuma etapa de aprovação**.
  Existe precedente direto e já executado: `skills/devops/sonarqube/SKILL.md` ganhou linha na tabela
  (`CLAUDE.md:160`) e `token-sonarqube-detection-block-redundant` removeu 10 das 11 cópias. O Jira tem
  a mesma forma e não recebeu o mesmo tratamento — o banco não tem **um único** fingerprint contendo
  "jira".
- **Por que importa:** 13 cópias, redações divergentes, todas invocando a mesma skill como autoridade.
  Uma correção na skill não propaga para nenhuma. O item (c) é o de consequência concreta: a skill foi
  escrita para que o nome de branch seja **proposto** antes de criado, e seis agentes criam direto —
  num fluxo com worktree isso materializa um diretório e uma branch com nome não aprovado, e a seção
  `## Worktree Isolation` do mesmo agente ainda prescreve um **segundo** padrão de nome
  (`<context>/<brief-title>`) sem nenhuma regra de precedência entre os dois. O item (a) faz
  `grep {taskId}` na skill não encontrar o que os agentes usam, e vice-versa.
- **Proposta:** adicionar linha à tabela *Canonical Rule Homes* apontando
  `skills/integrations/jira/SKILL.md` § Branch / Worktree Naming como casa única; reduzir as 13 cópias
  ao gatilho de detecção (2–3 linhas, conteúdo genuinamente por-agente) mais uma delegação por nome;
  mover para a skill o único conteúdo específico que vale preservar — o mapeamento papel → tipo de
  branch — como tabela fechada `agente → tipos sugeridos`. Declarar na skill a precedência entre o
  nome Jira e o nome `<context>/<brief-title>` da cascata de worktree.
- **Impacto positivo:** restaura o gate de aprovação do nome de branch em seis agentes; elimina a
  divergência `{issueKey}`/`{taskId}`; uma edição futura da regra passa a valer para os 13; fecha a
  lacuna de precedência entre os dois esquemas de nomenclatura que hoje coexistem no mesmo corpo.
- **Impacto negativo / risco:** o mapeamento papel → tipo hoje inline é justamente o que dá utilidade
  ao bloco **sem** carregar a skill; uma delegação pura custa uma leitura de `jira/SKILL.md` (91
  linhas) sempre que um issue key é mencionado, inclusive em tarefas onde só o nome da branch importa.
  Mover o mapeamento para a skill também transfere para lá conhecimento por-agente, empurrando a skill
  na direção de virar um roster — precisa ser tabela fechada, não seção por agente. São 13 arquivos
  tocados de uma vez, e `devops-specialist` (210) e `frontend-developer` (211) estão no teto ou a uma
  linha dele.

  > **Nota correlata**, deliberadamente **não** promovida a achado próprio por ser território do Eixo
  > A: o exemplo `VHI-450` — prefixo de projeto real, não placeholder genérico — aparece em
  > `skills/integrations/jira/SKILL.md:59,62` e em 6 corpos de agente, sempre ao lado do `PROJ-123`
  > genérico. A consolidação proposta acima reduz de 7 para 1 os lugares onde ele precisa ser trocado.
- **Esforço:** Médio

### A Task Closure Rule não alcança `mobile-developer` nem `devops-specialist`, dois dos oito coding agents canônicos

- **Fingerprint:** `agent-docs-sync-task-closure-missing-mobile-devops`
- **Alvo:** `agents/mobile-developer.md`, `agents/devops-specialist.md`
- **Evidência:**
  - `CLAUDE.md:157` — "| Task Closure Rule — after finishing a task, patch the docs the work triggers
    … | `skills/shared/docs-sync/SKILL.md` § Task Closure Rule | Load docs-sync and reference the
    rule; **write no closing directive of their own** |"
  - `CLAUDE.md:109` lista os oito coding agents, incluindo `mobile-developer` e `devops-specialist`
  - `for f in agents/*.md; do grep -q docs-sync $f || echo $f; done` → `devops-specialist.md`,
    `mobile-developer.md`, `product-analyst.md`, `qa-specialist.md`, `software-architect.md` —
    **13 dos 18 carregam `docs-sync`; estes 5 não**
  - `agents/devops-specialist.md:26` — "Read `docs/devops/` — synthesized infrastructure and
    deployment context, if present" (o agente **lê** a pasta)
  - `agents/devops-specialist.md:122` — "4. Document which secrets are needed and where to configure
    them in the README or CLAUDE.md" — **diretiva de documentação própria**, exatamente o que a coluna
    "Agents must" proíbe
  - Ambos os agentes terminam em `## Before You Finish` contendo **apenas** a instrução de run-banner;
    nenhuma etapa de fechamento documental
- **Problema:** a Task Closure Rule é declarada obrigatória para todo agente cuja entrega dispara
  patch de documentação, e os dois agentes cujo trabalho mais o dispara — features mobile e mudanças
  de infra/CI/deploy — não carregam a skill. `devops-specialist` é o caso mais nítido: lê
  `docs/devops/` na Foundational Rule e nunca tem regra para escrever de volta, de modo que a pasta
  que ele consome só é mantida por outro agente. No lugar da regra canônica ele carrega uma diretiva
  própria em `:122`, que é a forma exata de duplicação que a tabela existe para impedir, e que cobre
  só segredos.
- **Por que importa:** `docs/devops/` e a documentação mobile degradam silenciosamente a cada tarefa.
  Não há gate que detecte a ausência: `agent-lint.sh` não verifica cobertura de skill por agente, e
  `orphan-skill-scan.sh` roda na **direção oposta** — encontra skill sem agente que a referencie, não
  agente sem a skill que a tabela obriga. Como `docs-sync` já é carregada por 13 agentes, a lacuna é
  invisível em qualquer contagem agregada.
- **Proposta:** adicionar aos dois a mesma linha de delegação que os outros já usam ("Load
  `skills/shared/docs-sync/SKILL.md` — its Task Closure Rule governs when delivered work requires a
  `docs/` patch."), com escopo por papel; remover a diretiva concorrente de `devops-specialist.md:122`,
  cujo conteúdo passa a ser item de escopo dentro da regra canônica.
- **Impacto positivo:** fecha a lacuna nos dois coding agents que faltam; elimina a diretiva de
  fechamento paralela; `docs/devops/` passa a ter um escritor além do `technical-writer`.
- **Impacto negativo / risco:** `devops-specialist` está a **1 linha** do teto (210 de 211) e
  `mobile-developer` a 23 — a inserção no devops exige extrair conteúdo no mesmo commit. Adicionar
  Task Closure a um agente de infra também aumenta a chance de patches de doc em toda tarefa de CI,
  incluindo mudanças triviais de pipeline, gerando ruído em `docs/devops/` se o escopo não for
  redigido de forma estreita. Os outros três agentes sem a skill (`product-analyst`, `qa-specialist`,
  `software-architect`) foram deliberadamente **deixados fora**: nenhum é coding agent e cada um tem
  artefato documental próprio (spec, relatório de QA, ADR), então a decisão sobre eles é separada e
  não deve ser resolvida por simetria.
- **Esforço:** Baixo

### `seo-specialist` edita arquivos do projeto mas está fora do contrato de coding agent — `CLAUDE.md:109` enumera oito, a árvore tem nove

- **Fingerprint:** `agent-seo-specialist-outside-coding-agent-contract`
- **Alvo:** `agents/seo-specialist.md`, `CLAUDE.md`
- **Evidência:**
  - `CLAUDE.md:109` — enumeração de oito nomes; `seo-specialist` **ausente**
  - `grep -c '^## Worktree Isolation' agents/*.md` → **nove** arquivos com a seção; o nono é
    `agents/seo-specialist.md:35`
  - `agents/seo-specialist.md:36` — "Before editing any file, resolve the worktree decision using the
    cascade in `CLAUDE.md` → *Canonical worktree decision cascade*" — o agente **edita arquivos do
    projeto**
  - `grep -L comments-policy agents/*.md` e `grep -L reuse-guidelines agents/*.md` → ambos incluem
    `seo-specialist.md`, contra `CLAUDE.md:161` e `:170`, que exigem as duas skills
  - `grep -i 'seo-specialist' docs/reports/_index.md` → **0 ocorrências** em todo o banco
- **Problema:** `seo-specialist` foi adicionado com a seção `## Worktree Isolation` — ou seja, tratado
  como agente que escreve no repositório do usuário — mas não entrou na enumeração de `:109`, que é a
  lista a partir da qual as demais obrigações de coding agent são atribuídas. A consequência é que
  ficou fora de `comments-policy` e de `reuse-guidelines`, ambas exigidas de agentes que introduzem
  código ou padrão novo — e é exatamente isso que ele faz: insere blocos JSON-LD / schema.org, meta
  tags e `canonical` em templates de página. É também o único dos nove que usa o rótulo **correto**
  ("Canonical worktree decision cascade") em vez do inexistente "Worktree Isolation", o que confirma
  que foi escrito depois e por outro caminho, sem passar pelo mesmo molde dos oito.
- **Por que importa:** a lista de `:109` é a superfície de onde um autor deriva "o que este agente
  também precisa carregar". Enquanto ela disser oito e a árvore tiver nove, todo requisito futuro de
  coding agent nasce com o mesmo furo, e o furo não é detectável: `agent-lint.sh` está limpo no HEAD
  porque valida frontmatter, identidade de skill e roster — não a correspondência entre a enumeração e
  quem carrega a seção. Na prática, `seo-specialist` insere structured data em templates sem passar
  pela política de comentários nem consultar `docs/development/reuse-guidelines.md` para verificar se
  o projeto já tem um componente canônico de SEO/meta.
- **Proposta:** incluir `seo-specialist` na enumeração de `:109` e adicionar ao agente os loads de
  `comments-policy` e `reuse-guidelines`. Substituir a enumeração literal por uma regra derivável
  ("todo agente que contenha `## Worktree Isolation`") e adicionar ao `agent-lint.sh` a checagem
  bidirecional entre lista e presença da seção — a mesma forma de gate que o lint já aplica ao roster
  de comandos.
- **Impacto positivo:** fecha três lacunas de contrato num agente que escreve em arquivos do usuário;
  converte uma lista manual — já defasada uma vez — em invariante verificada; o gate bidirecional
  impede que o décimo agente repita o mesmo caminho.
- **Impacto negativo / risco:** `seo-specialist` tem 86 linhas, o menor do roster, e parte da sua
  economia vem justamente de carregar poucas skills; três loads a mais encarecem um agente que hoje é
  barato, e ele é **auto-spawnado** por `/devteam:frontend` e `/devteam:fullstack` sob Detection
  Signal, então o custo incide em fluxos que já spawnam muitos agentes. Há ainda a possibilidade
  legítima de que a omissão tenha sido deliberada — que ele seja considerado um gate de qualidade que
  edita pouco — e nesse caso a correção correta é a **inversa**: remover a seção `## Worktree
  Isolation` e declará-lo read-only. Vale confirmar a intenção antes de enrolá-lo no contrato
  completo.
- **Esforço:** Baixo

---

## LOW-MEDIUM

Nenhum achado original nesta faixa neste pass.

## LOW

Nenhum achado original nesta faixa neste pass.

---

## Descartados por duplicação

| Candidato | Porta | Fingerprint colidido / motivo |
|---|---|---|
| `software-architect.md`, `qa-specialist.md` e `frontend-developer.md` em exatamente 211 linhas, no teto, sem margem | Porta 3 (3/3) | `agent-three-at-exactly-211-line-ceiling-zero-headroom-for-additions` e `agent-line-cap-205-documented-in-claude-md-vs-211-enforced-by-size-limits` |
| `skills/shared/migration-v1-to-v2/SKILL.md` com 438 linhas, maior do repo, sem extração para `references/` | Porta 5 (estado) | `skill-shared-migration-v1-to-v2-437-lines-largest-in-repo-…` |
| `skills/architecture/orchestration/SKILL.md` com 391 linhas sem `references/` | Porta 5 | já listado como descarte de Porta 5 em `_index.md:477` |
| `skills/shared/output-format/SKILL.md` (203 linhas) eager em 9 agentes | Porta 4 (escopo menor sem sub-escopo novo) | `output-format` 190×9, já registrado como descarte de Porta 4 |
| `orphan-skill-scan.sh` reporta "duplicate skill loads" em `backend-test-specialist.md`, `frontend-test-specialist.md` (`test-pyramid`) e `commands/merge.md` (`worktree`) | Porta 3 (3/3) | `ref-orphan-skill-scan-reports-design-system-audit-duplicate-load-…`; reconfirmados como **falsos positivos do scanner** — a segunda ocorrência é citação de regra, não segundo load |
| `skills/shared/work-feedback/SKILL.md` carregada por um único agente e inalcançável a partir dos comandos `/devteam:*` | Porta 5 | `skill-orchestration-spawn-integrity-unreachable-from-devteam-commands` |
| `VHI-450` hardcoded em `jira/SKILL.md:59,62` e em 6 corpos de agente | Porta 3 | família `agent-*-description-frontmatter-enumerates-*` / território do Eixo A — mantido como nota dentro do achado do Jira, cuja consolidação reduz de 7 para 1 os pontos de correção |
| `conventional-commits` ausente de `frontend-developer`, `backend-test-specialist` e `frontend-test-specialist`, enquanto `backend-developer` a carrega | **Descartado por não ser obrigação verificável** | `CLAUDE.md:167` associa a regra a quem escreve mensagem de commit, e o commit é roteado por `/devteam:commit`, que carrega a skill diretamente; não há linha que obrigue o agente. Assimetria real, obrigação não demonstrável |
