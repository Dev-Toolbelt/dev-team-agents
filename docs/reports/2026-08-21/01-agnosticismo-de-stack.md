# Eixo A — Agnosticismo de stack (2026-08-21)

**Baseline:** `HEAD` = `a67cac9` · **Baseline anterior:** `c03f898`
**Varredura semente:** 124 candidatos → 4 violações. Os 120 descartados se dividem em quatro grupos: (a) ~78 são linhas de **tabela de detecção / roteamento condicional de skill** (`mobile-developer`, `devops-specialist`, `database-specialist`, `ui-ux-designer`, `backend-developer`, `setup-assistant`, `commands/commit.md § 4.5a`), legítimas por design; (b) ~14 são **exemplos rotulados** (`e.g.`, `# Examples:`) ou enumerações já protegidas por uma frase-guarda agnóstica na mesma seção — caso de `frontend-reviewer.md:110` ("Apply whatever type discipline the project has adopted"), `qa-specialist.md:82` (quiz com opção "Other") e `explain.md:48` ("never defaulting to JavaScript"); (c) ~11 são **falsos positivos do regex** (`pip` casando em "pipeline", `express` em "expressed/expressions", `nest`/`spring` sem ocorrência real, `health-check.md:50` "Python Prerequisite" que é pré-requisito do próprio harness, não do projeto do usuário); (d) 17 caem nas portas 1/3/5 da antiduplicação e estão na tabela final.

Varredura secundária complementar (fora da lista-semente: `eslint|prettier|webpack|vite|storybook|playwright|cypress|swift|kotlin|flutter|dart|artisan|npx|supabase|firebase|vercel|netlify|nginx|graphql|grpc|blade|twig|jinja|erb|jquery|htmx|nuxt|astro|remix`) rodada sobre `agents/` + `commands/` — as únicas ocorrências novas relevantes foram as que sustentam os achados 3 e 4 abaixo.

---

## HIGH

Nenhum achado original neste eixo com severidade HIGH.

---

## MEDIUM-HIGH

### O checklist de segurança de CI/CD do `security-specialist` está escrito inteiramente no vocabulário do GitHub Actions, enquanto a própria Foundational Rule do agente manda ler GitLab e Bitbucket

- **Fingerprint:** `agent-security-specialist-cicd-checklist-github-actions-only-vocabulary`
- **Alvo:** `agents/security-specialist.md`
- **Evidência:**
  - `agents/security-specialist.md:80` — "`- Script injection via untrusted input in expressions (e.g., ${{ github.event.issue.title }} in run: steps)`" (seção: `### CI/CD Pipeline Security`)
  - `agents/security-specialist.md:84` — "`- Pull request workflows triggered by untrusted forks with write permissions (pull_request_target misuse)`" (seção: `### CI/CD Pipeline Security`)
  - `agents/security-specialist.md:85` — "`- Self-hosted runners accessible from untrusted branches`" (seção: `### CI/CD Pipeline Security`)
  - Contraprova no mesmo arquivo — `agents/security-specialist.md:29` — "`- Read .github/workflows/*.yml (or .gitlab-ci.yml, bitbucket-pipelines.yml) — CI/CD pipeline attack surface`" (seção: `## Foundational Rule`)
- **Problema:** a seção introduzida como "CI/CD Pipeline Security" — genérica no título e na `description:` do frontmatter ("CI/CD pipeline security") — codifica seis itens dos quais três só existem no GitHub Actions (`${{ github.event.* }}`, `pull_request_target`, "self-hosted runners" no sentido do GHA) e um em GitHub+CircleCI ("actions or orbs"). Nenhum item cobre os vetores equivalentes do GitLab CI (`CI_PIPELINE_SOURCE == "merge_request_event"` sem guarda, variáveis protegidas expostas em branch não protegida, escopo do `CI_JOB_TOKEN`), do Bitbucket Pipelines ou do Jenkins. Isso apesar de o harness já embarcar `skills/devops/cicd-github`, `cicd-gitlab`, `cicd-bitbucket` e `cicd-jenkins`, e de `skills/security/sast-pipeline/SKILL.md:62` já ter um "### GitLab CI example".
- **Por que importa:** no HEAD atual, um `/devteam:security` sobre um projeto GitLab-only executa uma seção de checklist que o agente deve tratar como aplicável, mas cujos seis itens são inendereçáveis — o resultado prático é uma auditoria de pipeline que sai vazia (ou pior, "sem achados") num projeto que nunca foi analisado. É o único ponto do agente onde a superfície de ataque de CI é enumerada; a Foundational Rule manda abrir o arquivo do GitLab e a seção não diz o que procurar nele.
- **Proposta:** trocar os seis itens por 4–5 formulações agnósticas de plataforma (injeção de entrada não confiável em expressão de pipeline · dependência de terceiro no pipeline não fixada por SHA · segredo impresso em log · escopo de token/credencial do job maior que o mínimo · execução de pipeline disparada por origem não confiável com permissão de escrita), e adicionar uma linha de roteamento: "para os identificadores concretos da plataforma detectada, carregue `skills/devops/cicd-<platform>/SKILL.md`".
- **Impacto positivo:** a seção passa a produzir achados em projetos GitLab/Bitbucket/Jenkins; o vocabulário concreto fica no lugar onde o harness já o mantém por plataforma, sem cópia no corpo do agente.
- **Impacto negativo / risco:** a formulação agnóstica é menos acionável para o caso GitHub, que hoje é o mais coberto — sem carregar `cicd-github` o agente perde o gancho literal `pull_request_target`, que é um sinal de grep muito eficiente. Mitigação: manter os identificadores GitHub como exemplo entre parênteses em **um** item, não como o corpo dos seis.
- **Esforço:** Baixo

### `database-specialist` trata RLS como o padrão neutro de multi-tenancy e transforma isso num item de "done", para um roster de 9 engines em que 5 não têm RLS

- **Fingerprint:** `agent-database-specialist-rls-as-engine-neutral-multitenant-default-and-gate`
- **Alvo:** `agents/database-specialist.md`
- **Evidência:**
  - `agents/database-specialist.md:84` — "`**Multi-tenant:** RLS (default for PostgreSQL) → schema-per-tenant (≤ few hundred tenants) → database-per-tenant (strict compliance). Load multitenancy skill when RLS, pgvector, or tenant_id signals are detected.`" (seção: `## Schema Design Principles`)
  - `agents/database-specialist.md:154` — "`- [ ] All new tables have RLS enabled if this is a multi-tenant or Supabase project`" (seção: `## What to Do Before Declaring Done`)
- **Problema:** a cascata de decisão de multi-tenancy é apresentada como princípio de design geral (`## Schema Design Principles`, o mesmo bloco que traz "**Relational:**" e "**Document:**" — ambos escritos de forma agnóstica), mas seu primeiro degrau é uma feature exclusiva do PostgreSQL. O item de checklist em `:154` é pior: não tem qualquer ressalva de engine e condiciona o "done" a "todas as novas tabelas têm RLS", disparando por "multi-tenant **or** Supabase". O roster de engines do próprio agente (`skills/database/`) contém `mysql`, `mongodb`, `redis`, `sqlite` e `cassandra` — nenhum deles implementa RLS; `sqlserver` implementa, com sintaxe e semântica diferentes.
- **Por que importa:** num projeto MySQL ou MongoDB multi-tenant no HEAD atual, o agente chega ao checklist final com um item que não pode ser satisfeito nem marcado como cumprido, e chegou ao design da tabela com um "default" que não existe naquele engine — a decisão real (discriminador `tenant_id` + escopo forçado na camada de acesso, ou schema/database por tenant) não está escrita em lugar nenhum do corpo. Não há gate que pegue isso: `helpers/agent-lint.sh` não valida conteúdo, e a linha 84 já delega para a skill de multitenancy apenas *depois* de ter fixado o default.
- **Proposta:** reescrever `:84` como cascata neutra ("isolamento por linha quando o engine oferece política nativa (ex.: RLS no PostgreSQL) → schema-per-tenant → database-per-tenant"), e reescrever `:154` como "`- [ ] Estratégia de isolamento de tenant aplicada a todas as novas tabelas/coleções, conforme a cascata da skill de multitenancy`".
- **Impacto positivo:** o checklist volta a ser verificável nos 9 engines suportados; a escolha de isolamento deixa de ser pré-decidida por um engine antes da skill de multitenancy ser consultada.
- **Impacto negativo / risco:** perde-se a força do default explícito no caso PostgreSQL/Supabase, que é hoje o caminho mais comum e o mais fácil de errar por omissão (esquecer `ENABLE ROW LEVEL SECURITY` é uma falha silenciosa de vazamento entre tenants). A reescrita precisa manter o gancho para esse caso dentro da skill, ou o ganho de agnosticismo custa uma regressão de segurança no engine mais usado.
- **Esforço:** Médio

---

## MEDIUM

### O passo "leia os configs de linter" existe em três cópias divergentes e ecossistemicamente incompletas, todas carregadas na mesma sessão de review

- **Fingerprint:** `agent-reviewer-linter-config-three-divergent-ecosystem-incomplete-copies`
- **Alvo:** `agents/backend-reviewer.md`, `agents/frontend-reviewer.md`
- **Evidência:**
  - `agents/backend-reviewer.md:30` — "`- Read the linter / static-analysis configs (phpcs.xml, pyproject.toml, .rubocop.yml, golangci.yml) — they are the source of truth for style, not your preferences`" (seção: `## Foundational Rule`)
  - `agents/frontend-reviewer.md:31` — "`- Read the linter/style configs (.eslintrc, .prettierrc, stylelint.config.js) — the source of truth for style; never report what a formatter already owns`" (seção: `## Foundational Rule`)
  - Casa canônica que ambos carregam — `skills/shared/reviewer-base/SKILL.md:11` — "`- Read linter configs (.eslintrc*, pyproject.toml, .rubocop.yml, phpcs.xml, golangci.yml) — source of truth for style`" (seção: `## Foundational Rule`)
  - Tratamento correto no terceiro reviewer — `agents/code-reviewer.md:79` — "`# Examples: npm run lint, composer phpcs, ruff check ., rubocop`" (seção: `### Run the linters before commenting on style`)
- **Problema:** três listas fechadas e mutuamente inconsistentes do mesmo passo. `reviewer-base` (a casa canônica, carregada por `backend-reviewer.md:33` e `frontend-reviewer.md:35`) lista 5 arquivos; `backend-reviewer` restata a mesma lista **removendo** `.eslintrc*` — ou seja, um review de backend Node/TypeScript não recebe instrução para abrir a config de lint que o projeto de fato usa; `frontend-reviewer` restata um conjunto completamente diferente, só do ecossistema JS, sem `stylelint` na versão canônica e sem nada para projetos com template server-rendered (Blade/Twig/ERB/Jinja, que a `description` do `frontend-developer` declara suportar). Nenhuma das duas cópias em `agents/` é rotulada como exemplo — leem-se como o conjunto fechado a ler. Java, C#, Rust, Elixir e Kotlin não aparecem em nenhuma das três. Isso viola diretamente a regra "Canonical Rule Homes — Delegate, Never Restate" do `CLAUDE.md`: a regra tem casa (`reviewer-base`) e mesmo assim há duas paráfrases divergentes.
- **Por que importa:** custo de manutenção concreto e já materializado — três lugares para editar quando um ecossistema entra, e a divergência já produziu a perda de `.eslintrc*` no backend. `helpers/orphan-skill-scan.sh` não detecta restatement de regra, e `agent-lint.sh` não valida corpo, então nada no CI pega a terceira cópia divergindo da segunda.
- **Proposta:** apagar `backend-reviewer.md:30` e `frontend-reviewer.md:31`; em `reviewer-base/SKILL.md:11`, trocar a lista fechada por "leia o config de lint/análise estática do ecossistema detectado (a lista canônica de sinais está em `skills/shared/stack-detection/SKILL.md`)", com no máximo dois exemplos rotulados como tal.
- **Impacto positivo:** uma cópia só; ecossistemas novos entram em um arquivo; some a assimetria que hoje cega o backend-reviewer para ESLint.
- **Impacto negativo / risco:** a formulação por detecção custa uma consulta a `stack-detection` que hoje não acontece nesse passo, e a instrução literal com nomes de arquivo é um gancho de grep barato que o agente segue sem raciocinar. Há risco real de o passo virar "genérico demais para ser executado" — mitigável mantendo 2 exemplos e a frase "não reporte o que o formatador já cobre", que é a parte comportamental e deve sobreviver intacta.
- **Esforço:** Baixo

### `## Testability` do `frontend-developer` pressupõe modelo de componente reativo, contradizendo o escopo server-rendered que o próprio agente declara e o modelo de renderização que o harness já formaliza

- **Fingerprint:** `agent-frontend-developer-testability-presumes-reactive-component-model`
- **Alvo:** `agents/frontend-developer.md`
- **Evidência:**
  - `agents/frontend-developer.md:145-147` — "`Write components that are naturally testable:`" / "`- Decouple data fetching from rendering (smart/dumb component pattern)`" / "`- Avoid direct DOM manipulation — prefer reactive state`" (seção: `## Testability`)
  - Contraprova no mesmo arquivo — `agents/frontend-developer.md:72` — "`| **jQuery** | jquery dep or CDN <script>, $() / $.ajax() usage | skills/legacy/jquery/SKILL.md |`" (seção: `## UI Library Awareness`)
  - Contraprova no harness — `skills/shared/architecture-awareness/SKILL.md:61` — "`| Views are rendered by the same application that owns the routes and data | **Monolithic (server-rendered)** | Routing, controllers, and views change together |`" (seção: `## Client Rendering Model`)
- **Problema:** as três diretrizes de `## Testability` são regras de comportamento (não exemplos, não tabela de detecção) e todas três só fazem sentido sob um framework de componentes reativo: "components", "smart/dumb component pattern" e "prefer reactive state". Num projeto server-rendered (Blade/Twig/ERB/Jinja) ou legado jQuery — ambos explicitamente no escopo do agente, o primeiro pela `description:` da linha 3 e o segundo pela linha 72 que roteia para `skills/legacy/jquery/` — não existe "reactive state" a preferir, e manipulação direta do DOM é o modelo de execução, não um antipadrão. A instrução, aplicada literalmente ali, é conselho errado. O harness já modela isso corretamente em outro lugar: `architecture-awareness` trata "Monolithic (server-rendered)" como um Client Rendering Model de primeira classe, e `mobile-developer.md:45` já sabe pular as seções orientadas a browser — só `frontend-developer` não faz o gate no seu próprio corpo.
- **Por que importa:** `## Testability` é a última seção substantiva antes do checklist de "done" e é lida em toda execução de `/devteam:frontend` e `/devteam:fullstack`. Num projeto server-rendered a seção empurra o implementador para um modelo que o projeto não tem — o efeito prático é sugestão de refactor fora de escopo, ou uma nota de "testabilidade ruim" contra código que está idiomático para o seu stack. É uma seção pequena e sem gate: nenhum lint valida coerência entre a `description:` do agente e as pressuposições do corpo.
- **Proposta:** reescrever os três bullets em termos de unidade de renderização em vez de componente reativo — "separe a obtenção de dados da renderização", "mantenha a lógica testável fora da camada que toca o DOM/template", "torne efeitos colaterais explícitos e injetáveis" — e abrir a seção com uma linha de gate: "aplique conforme o Client Rendering Model resolvido por `skills/shared/architecture-awareness/SKILL.md`".
- **Impacto positivo:** a seção passa a valer nos dois modos que a `description:` do agente declara suportar, e reaproveita o gate de rendering model que o harness já mantém, sem uma segunda cópia da classificação.
- **Impacto negativo / risco:** "unidade de renderização" é mais abstrato que "componente" e perde o gancho nominal do smart/dumb pattern, que é reconhecível e acionável no caso SPA — que é a maioria dos projetos. Também adiciona uma dependência de leitura (`architecture-awareness`) a uma seção que hoje custa 4 linhas e zero tool calls; se o gate for lido eagermente, é custo de contexto em toda sessão de frontend. Mitigação: manter o gate como condicional ("se a detecção da linha 72 casou jQuery ou o projeto renderiza views no servidor").
- **Esforço:** Baixo

---

## LOW-MEDIUM

Nenhum achado original neste eixo com severidade LOW-MEDIUM.

---

## LOW

Nenhum achado original neste eixo com severidade LOW.

---

## Descartados por duplicação

| Candidato | Porta | Fingerprint colidido |
|---|---|---|
| `agents/frontend-developer.md:3` — `description:` enumera React/Vue/Svelte/Angular/Blade/Twig/ERB/Jinja | Porta 5 (estado — conjunto aberto) | `agent-frontend-developer-description-frontmatter-enumerates-eight-frameworks-react-vue-svelte-angular-blade-twig-erb-jinja-on-identity-surface` |
| `agents/frontend-developer.md:91,96` — "e.g. React `useState`" e "TanStack Query and SWR … React/Vue ecosystem" em `## Server State & Data Fetching` | Porta 3 (semântica: alvo + causa-raiz + remediação) | `agent-frontend-developer-body-92-102-data-fetching-section-hardcodes-usestate-useeffect-tanstack-query-swr-stack-prescriptive` |
| `agents/frontend-developer.md:130,132` — `dangerouslySetInnerHTML` / `v-html` / `VITE_*` / `NEXT_PUBLIC_*` em `## Security` | Porta 1 (literal) | `agent-frontend-developer-security-section-134-139-hardcodes-dangerouslysetinnerhtml-vhtml-vite-next-public-framework-apis-in-agent-body` |
| `agents/frontend-developer.md:72` — jQuery roteada junto com libs modernas | Porta 3 (semântica) | `agent-frontend-developer-loads-jquery-skill-orphan-of-modern-stacks` |
| `agents/frontend-test-specialist.md:141-153` — bloco LCOV com `jest --coverage` / `vitest run --coverage` / `sonar.javascript.*` | Porta 5 (estado — conjunto aberto) | `agent-frontend-test-specialist-sonarqube-coverage-block-hardcodes-jest-vitest-commands-and-sonar-javascript-key-while-backend-twin-was-delegated` |
| `agents/frontend-test-specialist.md:103` — roteamento de hook/composable por framework | Porta 3 (semântica) | `agent-frontend-test-specialist-107-122-hardcodes-react-renderhook-testing-library-and-vue-withsetup-recipes-in-body-stack-agnostic` |
| `agents/frontend-reviewer.md:112,114` — `PropTypes`, `defineProps`, `React.ChangeEvent<HTMLInputElement>` em `### 10. Type Safety` | Porta 3 (semântica) | `agent-frontend-reviewer-body-type-safety-and-code-quality-hardcodes-react-ts-identifiers-proptypes-react-changeevent-hocs` |
| `agents/devops-specialist.md:46-56` — `## Core Expertise` declara "**Primary**: Docker" + AWS/GCP/Azure/Terraform/Prometheus | Porta 5 (estado — conjunto aberto) | `agent-devops-specialist-core-expertise-declares-primary-docker-...` |
| `agents/database-specialist.md:66-73` — tabela de engines postgres/mysql/mongo/redis/mssql/RDS/Aurora | Porta 3 (semântica) | `agent-database-specialist-description-frontmatter-enumerates-12-engines-and-three-cloud-managed-db-families-stack-prescriptive-identity-surface` |
| `agents/database-specialist.md:133` — `psql "$SUPABASE_DB_URL"` inline em `## Database Access` | Porta 5 (estado — conjunto aberto) | `agent-database-specialist-access-inlines-supabase-cli-while-delegating-others` |
| `agents/security-specialist.md` § Tooling — comandos SAST/dep-audit por ecossistema | Porta 3 (semântica: mesmo alvo, mesma remediação "delegar para skill") | `agent-security-specialist-body-130-153-hardcodes-per-language-sast-and-dep-audit-commands-bandit-composer-npm-trivy-stack-prescriptive` |
| `agents/setup-assistant.md:146-147` — `jest.config.*`/`vitest.config.*`/`pytest.ini`/`phpunit.xml`/`vercel.json`/`netlify.toml` | Porta 5 (estado — conjunto aberto) | (conjunto aberto, `_index.md:406`) |
| `commands/commit.md:125-133` — tabela de lint/type-check `npm`/`npx eslint`/`phpcs`/`tsc`/`pyright` | Porta 5 (estado — conjunto aberto, referenciado como `commit.md:135-138`) | (conjunto aberto, `_index.md:406`) |
| `commands/audit.md:126,128` — "Caching opportunities (Redis, CDN…)" e "Docker/resource concerns" | Porta 5 (estado — conjunto aberto) | `flow-audit-command-devops-analysis-prompt-names-redis-cdn-docker-...` |
| `commands/audit.md:54` — stack Docker isolada incondicional no Step 2 | Porta 5 (estado — conjunto aberto) | `flow-audit-step2-unconditional-docker-stack-ignores-isolate-pref-compose-gate` |
| `commands/relayout.md:32` — "a Storybook config, a Tailwind/theme config" | Porta 5 (estado — conjunto aberto) | `flow-relayout-design-discovery-names-storybook-tailwind` |
| `commands/mobile.md:19,26,27` — linha de spawn enumera React Native/Expo/Flutter/iOS/Android e `flutter test`/XCTest/Espresso | Porta 5 (estado — conjunto aberto) | `flow-mobile-command-spawn-line-enumerates-stacks-...` |
| `commands/devops.md:2,14` — `description:` e linha de spawn nomeiam "CI/CD, Docker, infra" | Porta 3 (semântica) | (`devops.md:2,14`, registrado em `_index.md:407`) |
