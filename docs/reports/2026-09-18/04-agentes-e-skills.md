# Eixo D — Agentes e Skills — 2026-09-18

**Baseline:** `HEAD` = `ef69da3`

---

## HIGH

### A linha de delegação da Foundational Rule promete "recent git log", conteúdo que a skill canônica não possui, nos 18 agentes

- **Fingerprint:** `agent-project-context-delegation-claims-recent-git-log-absent-from-skill-18x`
- **Alvo:** `skills/shared/project-context/SKILL.md` (+ `agents/*.md`, 18 arquivos)
- **Evidência:** `agents/backend-developer.md:21` — "Load `skills/shared/project-context/SKILL.md` — covers README, CLAUDE.md, AGENTS.md, project.md, session-summary, backlog, development docs, and recent git log."; linha idêntica em `backend-reviewer.md:25`, `code-reviewer.md:43`, `database-specialist.md:22`, `devops-specialist.md:22`, `frontend-developer.md:21`, `frontend-reviewer.md:25`, `frontend-test-specialist.md:43`, `backend-test-specialist.md:45`, `mobile-developer.md:21`, `product-analyst.md:21`, `qa-specialist.md:22`, `security-specialist.md:23` e mais 5 — `grep -c 'recent git log' agents/*.md` → **18 de 18**. Contra isso, `grep -in 'git log' skills/shared/project-context/SKILL.md` retorna **exit 1**: a `## Context Loading Order` (`:97-118`) tem 11 itens numerados e nenhum é histórico git — vai de `1. README.md` a `11. docs/wiki/README.md`.
- **Problema:** os 18 corpos afirmam que a skill canônica cobre "recent git log". Ela não cobre. A delegação declara cobertura inexistente.
- **Por que importa:** nenhum agente lê histórico recente como parte do carregamento de contexto — e nenhum dos 18 tem motivo para suprir a lacuna, porque cada um já declara que a skill resolve. A única leitura de histórico no repo é a do § Commit Rule (`git log --oneline -10`), disparada só na hora de commitar. Em sessão nova, todo agente entra sem saber o que a árvore mudou nos últimos commits.
- **Proposta:** decidir de que lado fechar — acrescentar um item `git log --oneline -10` à `## Context Loading Order` de `project-context` (canônico), **ou** remover "and recent git log" das 18 linhas. Uma das duas, não ambas.
- **Impacto positivo:** elimina uma afirmação falsa replicada 18×; se resolvida pelo lado da skill, todo agente ganha orientação de histórico por ~120 tokens de output.
- **Impacto negativo / risco:** acrescentar o item na skill adiciona um fork de `git` por spawn (em `/devteam:fullstack`, 6–8 forks); removê-lo das 18 linhas toca 18 arquivos e os três que estão em 211 linhas não têm folga para a edição virar aumento.
- **Esforço:** Baixo

---

## MEDIUM-HIGH

### O template de saída de review está triplicado nos três reviewers e já divergiu — os dois especialistas perderam a seção de `comments-policy`

- **Fingerprint:** `agent-three-reviewers-review-output-template-triplicated-comments-slot-lost`
- **Alvo:** `agents/code-reviewer.md`, `agents/backend-reviewer.md`, `agents/frontend-reviewer.md`
- **Evidência:** os três abrem a seção com a mesma delegação — `backend-reviewer.md:159` / `frontend-reviewer.md:149` / `code-reviewer.md:124` — "Apply the PR review format from `skills/shared/pr-review/SKILL.md`:" e em seguida inlinam ~30 linhas de template. Divergências no HEAD: `code-reviewer.md:155` tem "### Comments" ("(omit section if none)" / "[what violates comments-policy and why]") e **nenhum** dos dois especialistas tem essa seção; inversamente `backend-reviewer.md:186` e `frontend-reviewer.md:185` têm "### SonarQube" / "Quality Gate: [PASS / FAIL]" e o router tem um bloco separado 20 linhas antes (`code-reviewer.md:113-118`) com campos diferentes ("New Issues: [count by type]"). O rótulo também divergiu: `code-reviewer.md:163` — "- **[NITPICK]** `file.js:12` — [minor point]" contra `backend-reviewer.md:183` — "[NITPICK] file.go:12 — [minor point]" (sem bullet, sem negrito). `code-reviewer.md:125-128` ainda restata as quatro etiquetas (`[BLOCKING]`/`[SUGGESTION]`/`[NITPICK]`/`[QUESTION]`) imediatamente após delegá-las a `pr-review`, que as define em `skills/shared/pr-review/SKILL.md:96-100`.
- **Problema:** um formato de saída com três cópias e nenhuma casa canônica, contra a doutrina *Delegate, Never Restate*. `skills/shared/output-format/SKILL.md` — carregado pelos três uma linha antes (`backend-reviewer.md:157`, `frontend-reviewer.md:147`, `code-reviewer.md:134`) — já hospeda Report, Conformance Report, Post-Implementation Review, Security Review, Plan e Diagnostics (`:50,:85,:106,:121,:144,:187`), mas **não** Code Review, justamente o único triplicado.
- **Por que importa:** `backend-reviewer` e `frontend-reviewer` são os agentes que de fato executam o review (o `code-reviewer` roteia, por `CLAUDE.md` § Code Reviewer roles) e ambos carregam `comments-policy` — mas nenhum dos dois tem slot de saída para reportar violação de comentários. A classe de achado é verificada e não tem onde ser emitida.
- **Proposta:** mover o template para `skills/shared/output-format/SKILL.md` como `## Code Review`, com as seções opcionais marcadas (Data Integrity / Accessibility / Component Design / Comments / SonarQube), e deixar os três agentes só com a linha de carga e o título do relatório.
- **Impacto positivo:** −~90 linhas somadas nos três corpos (folga real: `backend-reviewer` está em 209 e `frontend-reviewer` em 208 de 211); um único lugar para consertar a lacuna de `### Comments`.
- **Impacto negativo / risco:** `output-format` já tem 203 linhas e passaria de ~235; e um template centralizado com cinco seções condicionais tende a ser emitido inteiro por engano, poluindo reviews pequenos.
- **Esforço:** Médio

### `git-workflow` e `worktree` prescrevem convenções de nome de branch mutuamente exclusivas, sem nenhuma referência cruzada

- **Fingerprint:** `skill-git-workflow-type-prefixes-vs-worktree-context-title-branch-naming`
- **Alvo:** `skills/shared/git-workflow/SKILL.md`, `skills/shared/worktree/SKILL.md`
- **Evidência:** `skills/shared/git-workflow/SKILL.md:24-33` — "## Branch Naming" com tabela de prefixos de **tipo**: "`feature/*` | New functionality", "`fix/*`", "`hotfix/*`", "`release/*`", "`chore/*`", e a regra "include a ticket ID when the project uses one (e.g., `fix/PROJ-123-null-pointer`)". Contra `skills/shared/worktree/SKILL.md:59-67` — "## Name Format" / "`<context>/<brief-title>`" / "Examples: `auth/add-oauth-provider`, `payments/fix-refund-calculation`, `api/add-rate-limiting`" / "Both parts must be real, spelled-out words describing the task". `CLAUDE.md` § *Canonical worktree decision cascade*, passo 2, reforça o segundo: "ask only for a new branch name (suggest `<context>/<brief-title>`)". A colisão já vazou para a tabela de apoio: `skills/shared/worktree/references/branch-flow.md:198-199` lista "Cross-cutting | `chore`" e "Bug fixes | `fix`" na coluna **Domain** — dois prefixos de tipo ocupando o slot de domínio.
- **Problema:** duas skills compartilhadas respondem de forma incompatível à mesma pergunta ("como nomear a branch desta tarefa"), nenhuma das duas menciona a outra, e nenhuma linha da tabela *Canonical Rule Homes* cobre nome de branch.
- **Por que importa:** `agents/backend-developer.md:53` roteia "Creating branches, merge strategies, commit naming" para `git-workflow`, e `:65` roteia a cascata de worktree para o formato `<context>/<brief-title>` — o mesmo agente, na mesma tarefa, tem duas respostas. `software-architect.md:51`, `devops-specialist.md:196` e `qa-specialist.md:47` carregam só a variante de tipo; qualquer revisão de convenção feita por eles reprova as branches que a cascata de worktree criou.
- **Proposta:** eleger uma casa canônica de nome de branch (`worktree/references/branch-flow.md` já é a mais completa), substituir `git-workflow:24-33` por um ponteiro para ela, e registrar a linha correspondente na tabela *Canonical Rule Homes* do `CLAUDE.md`.
- **Impacto positivo:** elimina a única convenção do repo com duas definições em conflito; desfaz a contaminação `chore`/`fix` na coluna Domain de `branch-flow.md`.
- **Impacto negativo / risco:** `git-workflow` § Merge Strategy, § Hotfix Flow e § Protected Branch Requirements (`:60`, `:89`, `:99`) referenciam os prefixos de tipo; retirá-los exige reescrever três seções, e projetos que já usam `feature/*` passariam a receber sugestão de domínio sem que nada detecte a convenção instalada.
- **Esforço:** Médio

---

## MEDIUM

### Três skills de segurança carregam tabelas ecossistema→scanner divergentes; o `security-specialist` pode carregar as três na mesma tarefa

- **Fingerprint:** `skill-three-security-skills-hold-divergent-ecosystem-scanner-tables`
- **Alvo:** `skills/security/dependency-vulnerabilities/SKILL.md`, `skills/security/supply-chain/SKILL.md`, `skills/security/dependency-audit/SKILL.md`
- **Evidência:** `skills/security/dependency-audit/SKILL.md:33-46` — "## Step 2 — Ecosystem Detection → Dependency Scanner" / "| Signal in repo | Ecosystem | Command |" / "| `composer.lock` | PHP | `composer audit` |". `skills/security/dependency-vulnerabilities/SKILL.md:6-20` — "## Scanning Tools by Ecosystem" / "| Ecosystem | Tool | How to run |", tabela que **não tem linha de PHP** e inclui "| Docker images | **Trivy** | `trivy image <image>` |". `skills/security/supply-chain/SKILL.md:50-73` — "## Dependency Auditing" / bloco bash com "composer audit", "safety check", "npx better-npm-audit audit" e "trivy fs ." — três comandos que não existem em nenhuma das outras duas. A skill `dependency-audit` declara a fronteira em `:14` e `:16` ("CVE triage, severity SLAs, update strategy | …dependency-vulnerabilities"; "Typosquatting, action pinning, dependency confusion | …supply-chain"), mas as três mantêm a tabela de scanners.
- **Problema:** o mapeamento ecossistema→scanner tem três cópias já divergentes (PHP presente em duas e ausente na terceira; Trivy em três formas diferentes), embora `dependency-audit` se declare a dona de "Running the right security scanners" (frontmatter `description`).
- **Por que importa:** `agents/security-specialist.md:46`, `:47` e `:50` são três gatilhos distintos na mesma tabela de cargas condicionais; uma tarefa de auditoria de dependências casa com os três e o agente recebe ~350 linhas com três respostas diferentes para a mesma pergunta. Num projeto PHP, qual tabela ele lê primeiro decide se `composer audit` roda.
- **Proposta:** deixar a tabela apenas em `dependency-audit` § Step 2 (a única com detecção por sinal, portanto agnóstica de fato) e trocar `dependency-vulnerabilities:6-20` e `supply-chain:50-73` por um ponteiro de uma linha para ela.
- **Impacto positivo:** −~35 linhas somadas; encerra a divergência de PHP e Trivy; uma auditoria PHP deixa de depender da ordem de leitura.
- **Impacto negativo / risco:** `dependency-vulnerabilities` e `supply-chain` passam a exigir uma carga extra para serem acionáveis sozinhas, o que aumenta o custo de quem só precisa de triagem de CVE; e `safety check` / `better-npm-audit`, hoje só em `supply-chain`, somem se a consolidação não os preservar.
- **Esforço:** Baixo

### `test-strategy` inlina uma seção `## Test Pyramid` completa enquanto a skill `test-pyramid` existe e é carregada na mesma linha

- **Fingerprint:** `skill-test-strategy-inlines-test-pyramid-section-both-loaded-together`
- **Alvo:** `skills/testing/test-strategy/SKILL.md`
- **Evidência:** `skills/testing/test-strategy/SKILL.md:20` — "## Test Pyramid", seguida de diagrama ASCII e das subseções "### Unit Tests" (`:35`), "### Integration Tests" (`:42`) e "### E2E Tests" (`:48`), até `:55` — **36 linhas**. A skill dedicada `skills/testing/test-pyramid/SKILL.md` (167 linhas) cobre o mesmo escopo em "## Unit Tests" (`:8`), "## Integration Tests" (`:56`), "## E2E Tests" (`:103`). A própria seção duplicada aponta para a canônica no meio do corpo: `test-strategy:37` — "Inject and mock any such dependency; see the Hard rule in `skills/testing/test-pyramid/SKILL.md`". As duas são carregadas juntas, na mesma frase: `agents/backend-test-specialist.md:72` e `agents/frontend-test-specialist.md:71` — "Load and apply `skills/testing/test-strategy/SKILL.md` and `skills/testing/test-pyramid/SKILL.md`."
- **Problema:** duas definições do mesmo conteúdo, uma delas num arquivo cujo nome é o assunto da outra, entregues no mesmo carregamento — e sem linha na tabela *Canonical Rule Homes*.
- **Por que importa:** os dois test-specialists leem a taxonomia unidade/integração/E2E duas vezes por spawn, com critérios que já não batem: `test-strategy:44` autoriza "May use real database (test DB), real filesystem" para integração, enquanto a regra dura que `test-pyramid` hospeda é citada por cinco agentes como gate `[BLOCKING]` (`backend-reviewer.md:103`, `frontend-reviewer.md:122`, `qa-specialist.md:66`, `backend-test-specialist.md:94`, `frontend-test-specialist.md:132`). Qualquer ajuste de fronteira precisa ser feito em dois arquivos.
- **Proposta:** remover `test-strategy:20-55` e substituir por uma linha de delegação a `test-pyramid`, mantendo em `test-strategy` só o que é decisão (framework de decisão, coverage targets, AAA, naming).
- **Impacto positivo:** −36 linhas em `test-strategy` (132 → ~97); uma única definição de camada de teste para os cinco agentes que a usam como gate.
- **Impacto negativo / risco:** `test-strategy` deixa de ser autocontida para quem a carrega sozinha — `qa-specialist.md:37` carrega só ela ("Load `test-strategy` skill before planning validation") e passaria a precisar da segunda carga ou a perder a taxonomia.
- **Esforço:** Baixo

---

## LOW-MEDIUM

### `docs/design/design-system.md` tem dois esquemas divergentes, um deles dentro da skill que aponta para o outro

- **Fingerprint:** `skill-design-system-md-two-divergent-schemas-docs-sync-vs-design-system-audit`
- **Alvo:** `skills/design/design-system-audit/SKILL.md`
- **Evidência:** `skills/shared/docs-sync/SKILL.md:86-92` — "### `docs/design/design-system.md` — max 80 lines (UI projects only)" / "`<!-- last-updated: YYYY-MM-DD -->`" / "## UI Library / Color Tokens / Typography Scale / Component Inventory / Spacing Scale". `skills/design/design-system-audit/SKILL.md:104` reconhece a fronteira — "see `skills/shared/docs-sync/SKILL.md` § `docs/design/design-system.md` for the enforced schema … do not emit every sub-section below verbatim" — e mesmo assim `:108-135` emite um template concorrente: "# Design System — [Project Name]" com "## Status", "## Color Tokens", "## Typography", "## Spacing", "## Components", "## Patterns to Follow", "## Patterns to Avoid", sem `<!-- last-updated -->` e sem "UI Library".
- **Problema:** o mesmo arquivo de saída tem dois esquemas no repo: 5 seções na casa canônica contra 7 na skill que a cita, com três nomes divergentes (`Typography` vs `Typography Scale`, `Components` vs `Component Inventory`, `Spacing` vs `Spacing Scale`).
- **Por que importa:** `ui-ux-designer` é o único consumidor e lê o template inline logo depois do aviso; o resultado prático é um `design-system.md` sem o marcador `last-updated` e com cabeçalhos que nenhuma outra skill sabe localizar. O aviso de `:104` é exatamente o sintoma: a skill precisa de uma linha de prosa para desautorizar o próprio conteúdo.
- **Proposta:** substituir o bloco `:108-135` pelas 5 seções do esquema de `docs-sync`, com o `<!-- last-updated -->` incluído, ou apagá-lo e deixar só o ponteiro de `:104`.
- **Impacto positivo:** −~28 linhas em `design-system-audit` (195 → ~167) e um único esquema para o arquivo.
- **Impacto negativo / risco:** "Patterns to Follow" e "Patterns to Avoid" não existem no esquema de `docs-sync` e é justamente o que o modo Consultivo (`:140`) valida; consolidar pelo lado canônico perde esse par salvo se o esquema de `docs-sync` for estendido junto — e estendê-lo pressiona o teto de 80 linhas que ele mesmo impõe.
- **Esforço:** Baixo

---

## Descartados por duplicação

| Candidato | Porta | Fingerprint colidente |
|---|---|---|
| `CLAUDE.md:158` declara "12 items" para a Context Loading Order, que tem 11 | 5 (estado) | `docs-sync-claude-md-context-list-item-count-12-vs-11` — **candidato promovido por engano pelo eixo e revertido na consolidação** |
| `orphan-skill-scan` reporta carga dupla de `test-pyramid` nos dois test-specialists e de `worktree` em `merge.md` | 3 | `ref-orphan-skill-scan-reports-design-system-audit-duplicate-load-…` (falso positivo do scanner, verificado em 2026-08-21 e 2026-08-28) |
| Nenhum coding agent carrega `spec-gate`, apesar de `CLAUDE.md` mandar | 5 | `skill-spec-gate-scope-lock-hard-gate-unreachable-by-execution-agents` |
| `seo-specialist` tem `## Worktree Isolation` mas está fora da enumeração de coding agents e não carrega `comments-policy` nem `reuse-guidelines` | 1 | `agent-seo-specialist-outside-coding-agent-contract` |
| `frontend-reviewer.md:190` escreve diretiva de fechamento própria em vez de delegar a `docs-sync` | 3 | `token-docs-sync-closing-directive-…-twelve-agents-…` |
| Só 2 dos 18 agentes carregam `interaction-patterns` enquanto 6 usam `AskUserQuestion` | — (refutado) | `skills/shared/project-context/SKILL.md:195` ("Load `interaction-patterns` before asking the user any question") cobre os 18 |
| `templates/backlog-template.md` não existe | 1 | `ref-templates-backlog-template-md-orphan-confirmed-by-scanner-…` |
| `software-architect.md`, `qa-specialist.md` e `frontend-developer.md` exatamente em 211 linhas | 5 | `agent-three-at-exactly-211-line-ceiling-zero-headroom-for-additions` |
| `size-limits.sh` acusa `CLAUDE.md` com 602 linhas acima do limiar de 600 | 5 | `token-claude-md-426-lines-still-monolithic-…` |
| `code-reviewer.md:125-128` restata as 4 etiquetas de `pr-review` logo após delegá-las | 4 | Incorporado como evidência em `agent-three-reviewers-review-output-template-triplicated-comments-slot-lost` |
