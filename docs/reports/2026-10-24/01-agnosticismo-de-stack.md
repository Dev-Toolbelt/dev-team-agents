# Eixo A — Agnosticismo de Stack — 2026-10-24

**Baseline:** `HEAD` = `b64428b`. Varredura **integral** de `agents/` e `commands/` (18 agentes,
40 comandos), conforme a regra do eixo. Evidência lida via `git show HEAD:<path>`.

## Varredura semente

```
rg -in 'laravel|symfony|django|rails|spring|express|nest|next\.js|react|vue|angular|svelte|
tailwind|bootstrap|eloquent|prisma|hibernate|sequelize|typeorm|phpunit|jest|vitest|pytest|
rspec|composer|npm|yarn|pnpm|pip|maven|gradle|docker|kubernetes|terraform|aws|gcp|azure|
mysql|postgres|mongodb|redis|php|python|ruby|golang|typescript|javascript' agents/ commands/
```

**127 hits → 14 candidatos → 1 violação.**

Distribuição dos hits: `devops-specialist` 23 · `mobile-developer` 12 · `database-specialist` 12 ·
`security-specialist` 8 · `product-analyst` 8 · `frontend-test-specialist` 8 ·
`frontend-developer` 8 · `commit.md` 5 · `backend-developer` 5 · `audit.md` 4 · demais ≤3.

### Por que 113 hits não viraram candidatos

- **Tabelas de detecção** (`Detection signal → Skill to load`): `backend-developer.md:74-82`,
  `devops-specialist.md:70-79`, `ui-ux-designer.md:57-59`, `commit.md:125-134`,
  `setup-assistant.md:146`. Nomear o sinal de detecção é a única forma de detectar.
- **Listas de skills condicionais**: `cicd-*`, `iac-terraform`, `aws`/`gcp`/`azure`,
  `docker-dev`/`docker-prod` — carregamentos condicionais para `skills/devops/*`, exceção legítima
  por design.
- **Caminhos de skill citados literalmente** (`skills/mobile/ios-hig/SKILL.md`, …) — referência,
  não comportamento.
- **Anti-prescrições**: `commands/explain.md:48` — "never defaulting to JavaScript" nomeia a
  linguagem justamente para proibir o default.
- **Prosa de exemplo** em `commands/adr.md:12` (`/devteam:adr Adopt PostgreSQL as primary database`).

### Os 14 candidatos e seu destino

| # | Candidato | Destino |
|---|---|---|
| 1 | `agents/devops-specialist.md:3` — `description` nomeia cloud/CI | Porta 5 — conjunto aberto |
| 2 | `agents/devops-specialist.md:46-56` § Core Expertise | Porta 5 — `agent-devops-specialist-core-expertise-declares-primary-docker-…` |
| 3 | `agents/devops-specialist.md:138-149` checklist Docker/Terraform | Porta 4 — sub-escopo já coberto pelo pai, sem recorte novo |
| 4 | `agents/database-specialist.md:84` RLS | Porta 5 |
| 5 | `agents/security-specialist.md:80-85` | Porta 5 |
| 6 | `agents/frontend-test-specialist.md:141-153` SonarQube | Porta 5 |
| 7 | `agents/frontend-developer.md:3` frameworks na frontmatter | Porta 5 |
| 8 | `agents/frontend-reviewer.md:112,114` React/TS | Porta 3 — descartado em 2026-08-28 |
| 9 | `commands/mobile.md:21,28` stacks na linha de spawn | Porta 5 — `flow-mobile-command-spawn-line-enumerates-stacks-…` |
| 10 | `commands/devops.md:2,14` Docker na `description` | Porta 5 |
| 11 | `commands/audit.md` vendor no prompt de spawn | Porta 5 — `flow-audit-command-devops-analysis-prompt-names-redis-cdn-docker-…` |
| 12 | `commands/commit.md:131,134` `npm run lint` / `vendor/bin/phpcs` | Descartado — tabela de detecção |
| 13 | `commands/up.md:2-3,19` token `docker` em `description`/`argument-hint` | **Descartado — não é violação** (ver abaixo) |
| 14 | `agents/product-analyst.md:151-155` § Step 6 | **VIOLAÇÃO** |

#### Sobre o candidato 13 (`/devteam:up`, arquivo novo no delta)

`commands/up.md` é território novo — zero ocorrências de `up.md` no banco — e nomeia `docker` em
três superfícies: `description:`, `argument-hint: [docker|local]` e `:19`. Ainda assim **não é uma
violação**: `skills/devops/local-environment/SKILL.md:32` define o vocabulário canônico de modos —
"`docker` is **any** containerised mode; `local` is any other (native, bare metal, per-language
runner)". O token é um identificador de modo do próprio sistema, como um nome de `tier`, não uma
prescrição de ferramenta; e o comportamento central do comando ("Follow § Discovery Order", "do
not restate its rules") é inteiramente delegado. Registrado aqui para que o próximo pass não
redescubra o beco.

---

## MEDIUM

### `product-analyst` condiciona o modelo de isolamento a Docker e inlina uma sonda de compose que outra skill já possui

- **Fingerprint:** `agent-product-analyst-step6-gates-isolated-infra-on-docker-and-inlines-compose-probe`
- **Alvo:** `agents/product-analyst.md`
- **Seção (heading):** `## Step 6 — Sprint Generation (later step, on request)` — seção de
  comportamento, não tabela de detecção nem exemplo.
- **Evidência:** `agents/product-analyst.md:151-155` —
  "**Gate isolated infra on Docker.** State the isolation model explicitly: worktree-per-task
  always; **isolated Docker stack per worktree only when the project uses Docker** (a compose file
  exists). If the project has no Docker, the plan must say parallelism is achieved by worktree
  alone — do not imply isolated infra. Detect quickly:
  `ls docker-compose.yml docker-compose.yaml compose.yml compose.yaml 2>/dev/null | head -1`."
  Duas linhas depois, `:157-158` — "Reference (do not restate the mechanics):
  `skills/shared/worktree/SKILL.md` and `skills/shared/worktree/references/docker-isolation.md`."
- **Problema:** dois defeitos no mesmo bloco. (a) O gate de isolamento é expresso em termos de um
  produto — "only when the project uses Docker" — e não da capacidade que ele representa
  (ambiente conteinerizado, que a skill de ambiente local já abstrai como modo `docker`).
  (b) O agente inlina uma sonda de quatro nomes de arquivo, e essa sonda tem casa canônica:
  `skills/shared/stack-detection/SKILL.md` possui o Docker Compose probe, e
  `agents/setup-assistant.md:66` demonstra o padrão correto — "apply the Docker Compose probe from
  the already-loaded `stack-detection` skill and record its result … so no agent re-probes". O
  `product-analyst` re-sonda, contrariando literalmente essa instrução, e o faz na linha seguinte
  a uma que manda "do not restate the mechanics".
- **Por que importa:** o `product-analyst` escreve o **Parallel Execution Plan** de todo sprint. A
  frase "If the project has no Docker, the plan must say parallelism is achieved by worktree
  alone" transforma um detalhe de ferramenta em cláusula obrigatória do artefato de planejamento,
  num agente de fase DISCOVERY que deveria ser o mais agnóstico da frota. Um projeto que isola com
  Podman, Nix devshells ou LXC cai no ramo "no Docker" e recebe um plano que declara, errado, que
  não há infra isolada. A sonda duplicada também fica surda a `compose.yaml` com outro nome e a
  qualquer arquivo que o `stack-detection` venha a reconhecer.
- **Proposta:** substituir `:151-155` por uma regra em termos de capacidade — "isolated stack per
  worktree only when the project's local environment is containerised" — e trocar a sonda inline
  por "resolve com a sonda de
  `skills/shared/stack-detection/SKILL.md`; quando `setup-assistant` já gravou
  `DOCKER_COMPOSE:` no `CLAUDE.md` do projeto, leia esse valor em vez de re-sondar". Mantém-se o
  ponteiro de `:157-158`.
- **Impacto positivo:** remove a última sonda de stack inline de um agente de DISCOVERY; elimina
  uma re-sondagem que a própria árvore proíbe; o plano de sprint passa a descrever corretamente
  projetos conteinerizados fora do Docker. Três linhas a menos no corpo de um agente de 211 linhas.
- **Impacto negativo / risco:** `stack-detection` passa a ser carregada por mais um agente — o
  `product-analyst` hoje não a carrega, então é uma leitura de skill nova no caminho de DISCOVERY
  (custo de tokens real, não nulo). A leitura de `DOCKER_COMPOSE:` do `CLAUDE.md` do projeto
  acopla o `product-analyst` a um artefato que só existe se o `setup-assistant` rodou antes; o
  fallback (sondar via skill) tem de ficar explícito, ou o agente trava em projeto não configurado.
  E "containerised" é vocabulário que precisa ser consistente com a definição de modo em
  `local-environment` — se as duas divergirem, troca-se um acoplamento por uma inconsistência.
- **Esforço:** Baixo
