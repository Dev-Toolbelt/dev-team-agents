# Eixo A — Agnosticismo de Stack

**Data:** 2026-07-31 · **Baseline:** `f54569a` · **Varredura:** integral sobre `agents/` + `commands/`

---

## Resultado da varredura semente

**108 candidatos → 4 violações.**

Os `108 − 4 = 104` descartados, por motivo:

| Motivo do descarte | Qtd | Exemplos |
|---|---|---|
| **Tabela de detecção / roteamento de skill** — é o mecanismo do agnosticismo, não sua violação: o nome da tecnologia é o *sinal de entrada*, e a regra concreta vive na skill | 61 | `agents/database-specialist.md:57-64` (engine → skill), `agents/devops-specialist.md:63-74` (arquivo → skill), `agents/frontend-developer.md:64-78` (lib UI → skill), `agents/mobile-developer.md:47-67`, `agents/ui-ux-designer.md:50-52` |
| **Exemplo explícito (`e.g.`, `# Examples:`, placeholder)** — o nome ilustra uma regra que já é genérica | 19 | `agents/code-reviewer.md:72` — "# Examples: npm run lint, composer phpcs, ruff check ."; `agents/frontend-developer.md:124` — "any API the framework offers for bypassing escaping (e.g. …)"; `agents/backend-reviewer.md:158-163` — o template de output usa `file.go:42`, `file.php:88` **e** `file.py:33`, um trio deliberadamente multilíngue |
| **Leitura de superfície de ataque / de configuração** — instrução para *ler* um arquivo se ele existir | 11 | `agents/security-specialist.md:22-23`, `agents/backend-reviewer.md:24`, `agents/database-specialist.md:20` |
| **Condicional com gate declarado** — a tecnologia só entra depois de uma detecção explícita | 8 | `agents/product-analyst.md:131-135` — "isolated Docker stack per worktree **only when the project uses Docker** (a compose file exists)", com o comando de detecção na própria linha |
| **Falso positivo do regex** | 3 | `agents/product-analyst.md:88` e `agents/qa-specialist.md:3,7` — a semente casou `nest` dentro de "ho**nest**" |
| **Lista negativa explícita** | 2 | `agents/product-analyst.md:164` — nomeia trackers *que não têm skill* justamente para proibir improvisação |

O padrão dominante é saudável: o repo converteu quase toda menção a stack em sinal de detecção
apontando para uma skill. As 4 violações abaixo são os resíduos — e **três das quatro são o mesmo
defeito que já foi corrigido no agente irmão**, o que as torna especialmente baratas de fechar.

---

## MEDIUM-HIGH

### `frontend-test-specialist` inlina a matriz de comandos de cobertura que o gêmeo backend já teve removida

- **Fingerprint:** `agent-frontend-test-specialist-sonarqube-coverage-block-hardcodes-jest-vitest-commands-and-sonar-javascript-key-while-backend-twin-was-delegated`
- **Alvo:** `agents/frontend-test-specialist.md`
- **Heading da seção:** `## SonarQube Coverage Integration` (`:128`) — seção de comportamento, não de referência
- **Evidência:**
  `:132` — "**Generate coverage in LCOV format** — the standard for JavaScript/TypeScript projects:";
  `:135-136` — "`# Jest` / `jest --coverage --coverageReporters=lcov`";
  `:138-139` — "`# Vitest` / `vitest run --coverage --coverage.reporter=lcov`";
  `:144` — "`sonar.javascript.lcov.reportPaths=coverage/lcov.info`"
- **Problema:** o agente prescreve o runner (Jest ou Vitest), o formato do relatório e a chave do
  `sonar-project.properties` no corpo. Um projeto frontend com Karma, Web Test Runner, Bun test ou
  um runner próprio não é atendido — e a chave `sonar.javascript.*` está errada para um projeto
  TypeScript puro que reporta em `sonar.typescript.*`.
- **Por que importa:** o defeito idêntico no gêmeo backend está registrado e **foi corrigido nesta
  janela** — `agent-backend-test-specialist-body-114-120-hardcodes-per-language-coverage-command-matrix-clover-pytest-jacoco-go-simplecov-stack-prescriptive`, verificado ✅ na Fase 1
  (`grep -i 'clover\|jacoco\|simplecov\|pytest' agents/backend-test-specialist.md` → 0 hits). Os dois
  agentes tinham o mesmo bloco; um foi delegado para skill, o outro não. A assimetria é o achado.
- **Proposta:** mover o bloco para `skills/devops/sonarqube/SKILL.md` (que já é a casa canônica da
  detecção SonarQube) como uma tabela `runner detectado → comando de cobertura → chave sonar`, e
  deixar em `frontend-test-specialist.md` a mesma linha de delegação de uma frase que o
  `backend-test-specialist` recebeu.
- **Impacto positivo:** remove ~18 linhas do corpo; fecha a última matriz de comandos hardcoded em
  agentes; alinha os dois test-specialists no mesmo padrão, que é o que a Canonical Rule Homes
  table do `CLAUDE.md` exige.
- **Impacto negativo / risco:** um passo de indireção a mais para o caso comum (Jest/Vitest cobrem a
  maioria dos projetos frontend), e a skill `sonarqube` cresce — hoje ela é carregada
  condicionalmente por `project-context`, então o custo cai sobre quem já a carregou. Se a tabela
  ficar incompleta, o agente perde uma receita que hoje tem à mão.
- **Esforço:** Baixo

---

## MEDIUM

### A `description` de `frontend-developer` fixa oito frameworks na superfície de identidade

- **Fingerprint:** `agent-frontend-developer-description-frontmatter-enumerates-eight-frameworks-react-vue-svelte-angular-blade-twig-erb-jinja-on-identity-surface`
- **Alvo:** `agents/frontend-developer.md`
- **Heading da seção:** frontmatter — `description:` (`:3`)
- **Evidência:** `agents/frontend-developer.md:3` — "Works in both decoupled SPAs (React, Vue,
  Svelte, Angular) and server-rendered templates (Blade, Twig, ERB, Jinja)."
- **Problema:** a `description` é a superfície pela qual o agente é selecionado — é lida antes de
  qualquer detecção de stack. Fixar oito frameworks nela sugere que o agente é *para* esses oito.
  Um projeto Lit, Qwik, Solid, Astro, Alpine ou Handlebars lê a própria descrição do agente como
  sinal de que não é atendido.
- **Por que importa:** o defeito idêntico em `mobile-developer` está registrado
  (`agent-mobile-developer-description-frontmatter-enumerates-five-stacks-swift-kotlin-react-native-expo-flutter-on-identity-surface`) e **foi corrigido nesta janela** — verificado ✅ na Fase 1:
  `agents/mobile-developer.md:3` hoje diz "whether the project is native or cross-platform. Detects
  the project's mobile stack". A correção parou em um dos dois agentes.
- **Proposta:** reescrever para a mesma forma que `mobile-developer` recebeu — algo como
  "Implements frontend features following the project's design system and architecture, in both
  decoupled SPAs and server-rendered templates. Detects the project's frontend stack and follows
  its conventions." A enumeração já existe onde deve: nas tabelas de detecção do corpo (`:64-78`).
- **Impacto positivo:** a identidade do agente para de excluir stacks por omissão; alinha os dois
  agentes que tinham o mesmo defeito.
- **Impacto negativo / risco:** real e não trivial — a `description` é o que o roteador usa para
  escolher o agente, e nomes concretos de framework são sinal de match forte. Uma descrição
  puramente abstrata pode degradar a seleção automática em projetos onde o prompt do usuário diz
  "React". Mitigação: manter "SPAs" e "server-rendered templates" como os dois eixos concretos, que
  é o que carrega o sinal de roteamento sem fixar vendors.
- **Esforço:** Baixo

### `devops-specialist` declara Docker como ferramenta "Primary" e contradiz a própria regra 15 linhas depois

- **Fingerprint:** `agent-devops-specialist-core-expertise-declares-primary-docker-and-done-checklist-gates-on-docker-terraform-contradicting-own-never-name-a-product-rule`
- **Alvo:** `agents/devops-specialist.md`
- **Heading da seção:** `## Core Expertise` (`:37`) e `## What to Do Before Declaring Done` (`:129`)
- **Evidência:**
  `:39` — "**Primary**: Docker — development environments and production containers";
  `:43` — "**CI/CD**: GitHub Actions (primary), Bitbucket Pipelines, GitLab CI, …";
  `:131` — "- [ ] Docker image builds cleanly and runs in target environment";
  `:132` — "- [ ] No secrets hardcoded in Dockerfiles, compose files, CI configs, or `.tf` files";
  `:141` — "- [ ] IaC state stored remotely with locking (if Terraform is in use)".
  Contra: `:125` — "**Never name a specific product as the answer** — pick the tier, then the
  platform the project already runs and the team can operate."
- **Problema:** o agente carrega duas regras opostas no mesmo corpo. `## Infrastructure Sizing`
  proíbe nomear produto; `## Core Expertise`, 86 linhas antes, nomeia um produto como *primário* e
  outro como CI/CD *primário*. E o checklist de saída (`:131`, `:141-142`) só é satisfazível em
  projeto Docker + Terraform: um projeto que faz deploy por buildpack, Nix, Ansible, ou um binário
  em systemd, não tem como marcar o primeiro item.
- **Por que importa:** um agente que se contradiz resolve a contradição por proximidade — a regra
  que ele lê por último, ou a mais específica para a tarefa, vence. O default "Primary: Docker" está
  posicionado no bloco de identidade, que é lido primeiro e ancora o resto da sessão. Na prática o
  gate de `:125` chega tarde demais.
- **Proposta:** reescrever `## Core Expertise` como domínios de capacidade sem produto primário
  ("containerização", "CI/CD", "IaC", "observabilidade"), deixando os produtos apenas na tabela de
  detecção `:63-74` que já existe. No checklist, trocar `:131` por "o artefato de deploy do projeto
  builda e roda no ambiente alvo" e condicionar `:132` a "os arquivos de infra do projeto".
- **Impacto positivo:** elimina a contradição interna; alinha o agente com a regra que ele mesmo
  declara; o checklist passa a ser satisfazível em qualquer projeto.
- **Impacto negativo / risco:** perda real de sinal. "Primary: Docker" é uma heurística que acerta
  na grande maioria dos projetos, e o checklist concreto pega erros concretos ("secret no
  Dockerfile") que um checklist abstrato ("secret nos arquivos de infra") pega com menos força. O
  ganho é consistência; o custo é especificidade.
- **Esforço:** Médio
- **Refina:** `agent-devops-specialist-decision-framework-and-anti-overengineering-still-stack-prescriptive-in-body-after-2026-05-18-fix-on-description-and-identity` — o pai
  cobria `## Decision Framework` e `## Anti-Overengineering Rules`, ambos hoje delegados para
  `skills/devops/infrastructure-sizing/SKILL.md` (verificado ✅ na Fase 1). `## Core Expertise` e
  `## What to Do Before Declaring Done` são seções irmãs, nunca descritas, e sobreviveram à correção.

---

## LOW-MEDIUM

### O prompt de análise do `/devteam:audit` nomeia Redis e Docker para o devops-specialist

- **Fingerprint:** `flow-audit-command-devops-analysis-prompt-names-redis-cdn-docker-inside-spawn-instruction`
- **Alvo:** `commands/audit.md`
- **Heading da seção:** `4. **devops-specialist**` → "Analyze for:" (`:115-121`)
- **Evidência:** `commands/audit.md:119` — "- Caching opportunities (Redis, CDN, HTTP caching)";
  `:121` — "- Docker/resource concerns specific to the module"
- **Problema:** o comando monta o prompt do subagente e fixa nele duas tecnologias. Todas as outras
  linhas do mesmo bloco são agnósticas ("Missing or inadequate monitoring/alerting", "Deployment
  considerations (migrations, seeders, environment config)") — as duas destoam.
- **Por que importa:** consequência pequena mas concreta: em um projeto sem Redis e sem Docker, duas
  das cinco linhas de escopo do devops-specialist não se aplicam, e o agente ou as ignora ou
  inventa aderência. Comandos são shipped verbatim para o projeto do usuário, então o texto é lido
  como está.
- **Proposta:** trocar `:119` por "Caching opportunities (application, HTTP, CDN layers)" e `:121`
  por "Runtime and resource concerns specific to the module" — mesma intenção, sem vendor.
- **Impacto positivo:** o bloco fica internamente consistente; `commands/audit.md` deixa de ser o
  único comando com nome de produto em instrução de spawn.
- **Impacto negativo / risco:** "Redis" e "Docker" funcionam como âncora concreta e provavelmente
  produzem achados mais específicos em projetos que de fato os usam. A versão abstrata depende do
  agente inferir a camada certa. Risco baixo, mas não é zero.
- **Esforço:** Baixo
