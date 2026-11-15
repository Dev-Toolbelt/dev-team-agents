# Eixo A — Agnosticismo de stack

`DATA` 2026-11-14 · `HEAD` `c6398e5` · baseline `5133c8c` · varredura integral de `agents/` + `commands/`

## Método

A varredura semente obrigatória rendeu **130 hits** em `agents/` e `commands/` — o mesmo volume do pass
de 2026-11-07. Triagem: **130 hits → 49 candidatos → 0 violações originais na semente**. Os `130 − 49 = 81`
hits caíram antes da promoção em três grupos mecânicos: **13 falsos positivos de substring**, em que o
regex casou dentro de uma palabra sem tecnologia alguma no texto (`ho**nest**a` em
`agents/product-analyst.md:95`, `pe**rspec**tive` em `agents/qa-specialist.md:3,9`, `re**act**ivation` em
`agents/software-architect.md:89`, `fl**aws**` em `agents/security-specialist.md:74`, `**Pip**eline` em
`agents/security-specialist.md:80`, `can't **express** the type` em `agents/backend-reviewer.md:136`,
`**bootstrap** file` no sentido de entrypoint em `agents/backend-developer.md:101` e
`agents/frontend-developer.md:139`, `**pip**eline` em `agents/devops-specialist.md:118,195` e
`commands/explain.md:28,63`); **60 hits em tabelas de detecção, linhas de carregamento condicional de skill
e sinais de arquivo** (`## Integration Awareness` de `backend-developer`/`database-specialist`,
`## Integration Awareness — Platform Auto-Detection` de `devops-specialist`, `## UI Library Awareness` e a
tabela de server-state de `frontend-developer`, as duas portas de `mobile-developer`,
`### Mobile Platform Design Skills` de `ui-ux-designer`, `## Platform Awareness` de `security-specialist`,
as sondas delegadas a `stack-detection` em `setup-assistant:26,66,74`, a matriz de lint de
`commands/commit.md:131,134`, o `commands/up.md` cuja própria razão de existir é o ambiente local, e o
`python3` de ferramental interno do framework em `commands/health-check.md:51` e `commands/insights.md:20`);
e **8 hits rotulados como exemplo ou como regra anticoplamento** (`# Examples:` em
`agents/code-reviewer.md:79`, `e.g.:` em `commands/adr.md:12`, o `AWS access key at config/x.py:12` que é
ilustração de como citar um segredo em `commands/audit.md:140`, o `never defaulting to JavaScript` de
`commands/explain.md:48`, que é a própria regra agnóstica, e os `e.g.` de
`agents/frontend-reviewer.md:114,116` e `agents/frontend-developer.md:91,96`, que ficam **sob um preâmbulo
agnóstico explícito** — `### 10. Type Safety` abre com "Apply whatever type discipline the project has
adopted" e o fallback de server-state manda "recommend adopting the server-state library idiomatic to the
project's stack", de modo que a regra que governa é neutra e a tecnologia só ilustra).

Dos **49 candidatos**, **42 caíram nas portas 1/3/5** — já estão no banco como tema aberto, sem marcador
`✅ **Executed:**` — e **7 não são violação**: `commands/commit.md:36,40,45`, `commands/merge.md:41,46` e
`commands/relayout.md:43` nomeiam "isolated Docker stack" apenas ao **delegar** a
`skills/shared/worktree/SKILL.md`, cujo primitivo de isolamento *é* o project name do Compose por desenho
(`skills/shared/worktree/references/docker-isolation.md:14` — "The isolation primitive is Docker Compose's
**project name**"), e `agents/devops-specialist.md:171` enumera artefatos de escopo ("shell scripts,
Dockerfiles, CI/CD configs, or infrastructure-as-code") antes de regras que são todas agnósticas.
**Nenhuma linha adicionada pelo delta em `agents/` ou `commands/` contém qualquer token de stack**
(`git diff 5133c8c..c6398e5 -- agents/ commands/ | grep '^+' | rg -i '<regex semente>'` → vazio), o que
inclui os cinco arquivos de atenção especial: as mudanças em `agents/devops-specialist.md`,
`agents/product-analyst.md`, `agents/security-specialist.md`, `commands/security.md` e `commands/sprint.md`
são de banner de entrega, `Refs`, roteamento de skill vendorizada, modo de auditoria e economia de prompt —
todas neutras.

Como varredura complementar, rodei um segundo regex com os tokens que a semente não cobre (`flutter`,
`swift`, `kotlin`, `rust`, `cargo`, `supabase`, `expo`, `nuxt`, `astro`, `vite`, `podman`, `helm`,
`ansible`, `nginx`, `github actions`, `sonarqube`, `graphql`, `eslint`, `ruff`, `rubocop`, `psql`,
`sqlite`, `kafka`, `celery`, `sidekiq`, …): **138 hits → 11 candidatos → 1 violação**. Dez caíram por
serem listas de sinais de arquivo (`commands/design.md:21`, `commands/review.md:48`,
`commands/tester.md:24`, `commands/fix.md:23`), roteamento de agente por plataforma
(`commands/spec.md:44`, `commands/fix.md:29`), delegação correta do comando por linguagem a uma referência
de skill (`agents/backend-test-specialist.md:104-108`, `agents/code-reviewer.md:101-113`) ou tema já
registrado (`agents/seo-specialist.md:27`). A violação restante está abaixo. Ela não aparece na semente
porque o regex obrigatório não tem `gh` nem `github` — lacuna já registrada e aberta como
`gov-seed-scan-regex-blind-to-flutter-swift-kotlin-rn-dotnet-rust-supabase`, que não re-reporto aqui.

**Total do eixo: 1 violação original.**

---

## MEDIUM-HIGH

### `/devteam:pr` cria o PR exclusivamente via `gh`/GitHub enquanto seu comando irmão `/devteam:review` e o skill canônico de PR são neutros de plataforma

- **Fingerprint:** `flow-pr-md-pr-creation-github-only-while-review-md-is-platform-neutral`
- **Alvo:** `commands/pr.md`
- **Portas do protocolo:** 1 sem hit. 2 **com** hit — `commands/pr.md` aparece no banco em `flow-pr-md-default-branch-falls-back-to-global-config-then-literal-main` (MEDIUM, aberto) e `token-pr-md-unbounded-full-diff-to-repetitive-tier-while-same-file-caps-git-log` (aberto). Porta 3 avaliada **só contra essas linhas**: coincide **1 de 3** atributos (o alvo). Causas raiz divergem — lá é a ordem da cascata de resolução da branch base e o volume de diff enviado ao tier; aqui é a ausência de qualquer caminho fora do GitHub para o passo de criação. Remediações divergem — lá, reordenar a cascata / limitar o diff; aqui, abstrair a criação do PR como o `pr-review` já abstrai a leitura. **Não é duplicata**; também não é sub-escopo contido (porta 4 não se aplica) nem item do conjunto aberto (porta 5 não se aplica).
- **Evidência:**
  - `commands/pr.md:30` — § `## Step 0a — Conventional Commits pre-flight` — "`DEFAULT_BRANCH=$(gh repo view --json defaultBranchRef -q '.defaultBranchRef.name' 2>/dev/null \`"
  - `commands/pr.md:65` — § `## Step 0b — Detect PR template` — "`1. Check if `.github/PULL_REQUEST_TEMPLATE.md` exists`"
  - `commands/pr.md:97` — corpo de criação do PR, sob § `## Step 0b` — "`**NEVER run `gh pr create` without explicit user confirmation.**`"
  - `commands/pr.md:104` — § `## Post-create — Watch GitHub Actions` — "`Before `gh pr create` runs the push, load `skills/shared/github-actions/SKILL.md``"
  - `commands/pr.md:108` — § `## Post-create — Session summary (opening a PR is a finalization signal)` — "`After `gh pr create` succeeds, apply the Session Summary Rule from `CLAUDE.md` right now`"
  - Contraste, mesmo repositório: `commands/review.md:28` — "`use the platform CLI/API to fetch the diff (`gh pr diff <url-or-number>` for GitHub; for GitLab/Bitbucket use the available MCP/CLI or fetch the diff)`"
  - Contraste, abstração canônica: `skills/shared/pr-review/SKILL.md:143` — "`| GitLab | `glab mr view <mr> --output json` (`author`, `assignees`); self: `glab api user` | …`"; `:144` — "`| Other (Bitbucket, Azure DevOps…) | Available MCP or API | …`"
  - Regra violada: `CLAUDE.md:118` — "`- Stack-agnostic: no hardcoded framework, language, or tool references in agent core behavior`"; `CLAUDE.md:225` manda apontar para o `pr-review` e "`never restate the format, mention rule, or platform commands`"
- **Tecnologia acoplada:** GitHub + `gh` CLI (plataforma de hospedagem git).
- **Problema:** o comportamento central de `commands/pr.md` — resolver a branch base, achar o template e
  **criar o PR** — só existe na forma GitHub. As 122 linhas do arquivo não mencionam `glab`, merge request,
  GitLab, Bitbucket nem qualquer caminho alternativo ou degradação. O `gh repo view` de `:30` falha em
  silêncio (`2>/dev/null`) num projeto GitLab e o fluxo segue até `:97`, onde o único verbo de criação é
  `gh pr create`; `:65` procura o template apenas em `.github/PULL_REQUEST_TEMPLATE.md`, não em
  `.gitlab/merge_request_templates/`. O repositório **não** se declara GitHub-only em lugar algum
  (`README.md:252` descreve o comando sem qualificador de plataforma) e já suporta as outras plataformas em
  três lugares: `commands/review.md:21,28`, `skills/shared/pr-review/SKILL.md:138-144` e o Remote mode de
  `agents/product-analyst.md:187` ("GitHub/GitLab/Bitbucket Issues").
- **Por que importa:** num projeto GitLab ou Bitbucket, `/devteam:pr` gasta a cascata de pre-flight, o
  `technical-writer` e opcionalmente o `code-reviewer` para então chegar a um passo que não pode executar —
  todo o custo de spawn, zero entrega. O irmão `/devteam:review` lê um MR sem problema, o que torna a
  assimetria invisível até o momento da criação. A parte de CI (`:102-104`) **não** é o defeito: ela tem
  gate explícito e degrada de propósito ("If the preconditions fail, skip silently and push normally"); o
  defeito é a criação do PR, que não tem gate nenhum.
- **Proposta:** acrescentar ao `## Step 0a` uma resolução de plataforma delegada a
  `skills/shared/pr-review/SKILL.md` § Platform (GitHub → `gh`, GitLab → `glab mr create`, outras → MCP/API
  disponível), trocar `:97` por "nunca criar o PR/MR sem confirmação, pelo comando da plataforma resolvida"
  e estender `:65` a `.gitlab/merge_request_templates/*.md` além de `.github/PULL_REQUEST_TEMPLATE.md`.
- **Impacto positivo:** `/devteam:pr` passa a terminar em projetos GitLab e Bitbucket em vez de abortar no
  último passo; elimina a assimetria com `commands/review.md` e reaproveita a tabela de plataforma que já
  existe, sem criar uma segunda fonte de verdade.
- **Impacto negativo / risco:** o comando é `model: haiku` (`commands/pr.md:4`) e ganha um passo de
  resolução de plataforma — mais uma decisão num comando deliberadamente barato. A tabela de
  `pr-review/SKILL.md` § Platform cobre leitura/comentário/aprovação, não criação, então **ela também
  precisa de uma coluna ou linha nova** para `glab mr create` — sem isso o comando aponta para uma seção que
  não responde à pergunta, e passam a ser dois arquivos a manter em lockstep. O caminho "Other (Bitbucket,
  Azure DevOps…) → MCP ou API disponível" é inerentemente não determinístico e vai falhar em máquinas sem
  MCP configurado, trocando um erro claro (`gh` ausente) por um erro mais difuso.
- **Esforço:** Médio

---

## Descartados por duplicação

Candidatos da semente que caíram nas portas do protocolo anti-duplicação. Todos os temas listados estão no
**conjunto aberto** (registrados sem marcador `✅ **Executed:**`), o que os bloqueia também pela porta 5.

| Candidato (arquivo:linha) | Fingerprint-pai | Porta |
|---|---|---|
| `agents/devops-specialist.md:3,46,48,50,52,54,56,134,135,138,144,145` — `## Core Expertise` "**Primary**: Docker" e o checklist de done gateado em Docker/Terraform, contra a própria regra de `:128` | `agent-devops-specialist-core-expertise-declares-primary-docker-and-done-checklist-gates-on-docker-terraform-contradicting-own-never-name-a-product-rule` | 1 (slug literal) + 5 |
| `agents/frontend-test-specialist.md:144,147,148,150,151,156` — `## SonarQube Coverage Integration` com `jest --coverage`, `vitest run --coverage` e `sonar.javascript.lcov.reportPaths` inline, enquanto `agents/backend-test-specialist.md:108` delega o comando por linguagem a `references/quality-gates.md` | `agent-frontend-test-specialist-sonarqube-coverage-block-hardcodes-jest-vitest-commands-and-sonar-javascript-key-while-backend-twin-was-delegated` | 1 + 5 |
| `agents/product-analyst.md:147,163,164,165,167,170` — item 4 "**Gate isolated infra on Docker**" e a sonda `ls docker-compose.yml …` inline; a seção foi renomeada de `## Step 6 — Sprint Generation` para `### Design for Parallel Execution (mandatory)`, o defeito é o mesmo | `agent-product-analyst-step6-gates-isolated-infra-on-docker-and-inlines-compose-probe` | 3 (a+b+c) + 5 |
| `agents/security-specialist.md:3,81` — `### CI/CD Pipeline Security` em vocabulário exclusivo do GitHub Actions (`${{ github.event.issue.title }}`) | `agent-security-specialist-cicd-checklist-github-actions-only-vocabulary` | 1 + 5 |
| `agents/database-specialist.md:83` — RLS como primeiro degrau da cascata de multi-tenancy em `## Schema Design Principles` | `agent-database-specialist-rls-as-engine-neutral-multitenant-default-and-gate` | 1 + 5 |
| `agents/database-specialist.md:134` — `## Database Access` inlina `psql "$SUPABASE_DB_URL"` logo após dizer que os CLIs vivem nos skills por engine | `agent-database-specialist-access-inlines-supabase-cli-while-delegating-others` | 1 + 5 |
| `agents/backend-reviewer.md:30` — `## Foundational Rule` enumera `phpcs.xml`, `pyproject.toml`, `.rubocop.yml`, `golangci.yml` | `agent-reviewer-linter-config-three-divergent-ecosystem-incomplete-copies` | 1 + 5 |
| `agents/backend-reviewer.md:170` — `### Data Integrity` fixa `file.php:88` no placeholder de saída | `agent-code-reviewer-output-template-pins-file-js-six-placeholders` | 3 (b+c — a entrada já cita `backend-reviewer.md:166-17x` como o contraste) + 5 |
| `agents/frontend-developer.md:3` — frontmatter enumera oito frameworks na superfície de identidade | `agent-frontend-developer-description-frontmatter-enumerates-eight-frameworks-react-vue-svelte-angular-blade-twig-erb-jinja-on-identity-surface` | 1 + 5 |
| `agents/frontend-developer.md:147` — `## Testability` pressupõe modelo de componente reativo | `agent-frontend-developer-testability-presumes-reactive-component-model` | 1 + 5 |
| `agents/mobile-developer.md:150` — `### Routing Rules` congela a matriz de 5 runners | `agent-mobile-developer-routing-rules-restates-five-runner-matrix` | 1 + 5 |
| `agents/product-analyst.md:193` — `## Issue Tracker Integration` com Jira/Linear como únicos skills | `agent-tracker-monoculture-jira-in-eleven-bodies-linear-reachable-from-one` | 1 + 5 |
| `agents/seo-specialist.md:27` — `## Foundational Rule` ilustra com `next-seo`/`astro-seo` (varredura complementar) | `agent-seo-specialist-foundational-rule-names-next-seo-astro-seo` | 1 + 5 |
| `commands/audit.md:48` — `## Step 2` sobe stack Docker isolado sem o gate `worktree_docker_isolate` | `flow-audit-step2-unconditional-docker-stack-ignores-isolate-pref-compose-gate` | 1 + 5 |
| `commands/audit.md:118,120` — `### Phase 4a` nomeia Redis/CDN/Docker dentro da instrução de spawn | `flow-audit-command-devops-analysis-prompt-names-redis-cdn-docker-inside-spawn-instruction` | 1 + 5 |
| `commands/mobile.md:21` — linha de spawn enumera as cinco stacks | `flow-mobile-command-spawn-line-enumerates-stacks-dropped-from-agent-description` | 1 + 5 |
| `commands/relayout.md:32,37` — descoberta de design nomeia Storybook e Tailwind | `flow-relayout-design-discovery-names-storybook-tailwind` | 1 + 5 |
| `commands/sprint.md:53,57` — `## Step 3` condiciona a infra isolada a "when the project uses Docker" / "when that applies", omitindo o gate `worktree_docker_isolate` do skill. Alvo novo (porta 2 só devolveu `flow-path-rewrites-…` e `gov-seed-scan-…`, temas distintos), mas **causa raiz e remediação idênticas** às duas entradas de gate-de-Docker abertas | `flow-audit-step2-unconditional-docker-stack-ignores-isolate-pref-compose-gate` · `agent-product-analyst-step6-gates-isolated-infra-on-docker-and-inlines-compose-probe` | 3 (b+c) + 5 |
| Lacuna do regex semente (sem `gh`/`github`/`glab`), que é a razão pela qual a violação deste pass não apareceu na varredura obrigatória | `gov-seed-scan-regex-blind-to-flutter-swift-kotlin-rn-dotnet-rust-supabase` | 1 + 5 |

Não-violações (não entram em porta de duplicação — simplesmente não quebram a regra do projeto):
`commands/commit.md:36,40,45`, `commands/merge.md:41,46` e `commands/relayout.md:43` delegam o teardown ao
`worktree/SKILL.md`, cujo primitivo de isolamento é o Compose por desenho; `agents/devops-specialist.md:171`
enumera artefatos de escopo, não uma regra acoplada.
