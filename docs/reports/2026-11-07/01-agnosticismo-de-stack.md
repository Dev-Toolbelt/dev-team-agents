# Eixo A — Agnosticismo de Stack — 2026-11-07

**Varredura:** 130 hits → 27 candidatos → **0 violações**

**Nenhum achado original neste eixo.** É o **quarto resultado zero em cinco passes** (2026-10-02,
2026-10-10 e 2026-10-17 também fecharam em zero; 2026-10-24 produziu um único achado,
`agent-product-analyst-step6-…`, hoje em `agents/product-analyst.md:163-167` e ainda aberto).

## Por que os 103 hits não chegaram a candidato

**Tabelas de detecção e listas de carga condicional (≈45 hits).** As matrizes sinal-do-projeto →
skill de `frontend-developer.md:70-71,84`, `mobile-developer.md:46,55-60,71,75,138-142`,
`ui-ux-designer.md:58-60`, `database-specialist.md:55-72`, `backend-developer.md:78-87`,
`devops-specialist.md:70-79,193`, `security-specialist.md:48,147`,
`frontend-test-specialist.md:28,106`, `commit.md:131,134` e `explain.md:63` são exatamente a
exceção que a regra do projeto prevê: nomeiam tecnologia para **rotear** a uma skill de referência
legítima, não para prescrever comportamento.

**Blocos "Example" (4 hits).** `code-reviewer.md:79` é um comentário `# Examples:` dentro de bloco
cercado; `adr.md:12` é o título de ADR de exemplo num prompt de erro; `audit.md:140` é o
`AWS access key at config/x.py:12` que ilustra a regra de nunca citar o valor do segredo;
`backend-reviewer.md:170` está dentro do template cercado de saída.

**Ruído léxico do regex semente (≈13 hits).** `pip`→"pipeline" (`explain.md:28,63`),
`react`→"Auto-reactivation" (`software-architect.md:89`), `nest`→"technical limitation"
(`product-analyst.md:95`), mais `qa-specialist.md:3,9` e `security-specialist.md:74` (TOCTOU) — não
nomeiam tecnologia alguma. É o mesmo padrão 5:1 que 2026-08-28, 09-04, 10-02 e 10-10 registraram.

**Descartes por mérito (≈41 hits).** `health-check.md:51` e `insights.md:20` falam do Python do
próprio harness, não da stack do projeto; `explain.md:48` ("never defaulting to JavaScript") **é** a
regra de agnosticismo; `product-analyst.md:193` ("Any other tracker … do not improvise one") é o
fallback agnóstico correto; `frontend-developer.md:139,147` usam DOM e `new ApiService()` como
primitiva de plataforma e pseudocódigo genérico; `setup-assistant.md:26,66` é citado pelo próprio
banco como **o padrão correto** de delegação da sonda a `stack-detection`.

## Por que o zero é estrutural, não amostral

O delta de `agents/` e `commands/` desde `b64428b` são 5 arquivos modificados e **5 novos**, e os
cinco novos são agnósticos por verificação direta: `agents/orchestrator.md` (81 linhas),
`commands/orchestrate.md`, `commands/release-qa.md`, `commands/push.md` e `commands/down.md`
devolvem **zero** ocorrências para um regex de 40 termos de stack. `commands/up.md`, o único alvo do
eixo sem nenhuma linha no banco, foi auditado inteiro (39 linhas) e está limpo: `skills/devops/
local-environment/SKILL.md:32` define canonicamente os dois modos — "`docker` is any containerised
mode; `local` is any other (native, bare metal, per-language runner)" — e `up.md:19` remete a essa
definição em vez de reescrevê-la. `docker` ali é rótulo de uma classe definida no skill, não
acoplamento de comportamento; é o contra-exemplo do padrão que o eixo pune.

Os 10–13 acoplamentos genuínos que o eixo tem a mostrar **seguem registrados e abertos**. O passivo
deste eixo é de execução, não de descoberta.

## Nota de método — lacuna da semente

O regex semente de `docs/reports/_prompt-auditoria.md:143-146` **não cobre `flutter`, `swift`,
`kotlin`, `react native`, `dotnet`, `rust` nem `supabase`**. `commands/spec.md:44` contém
"Flutter/native" numa linha de spawn e dá **zero hits** sob a semente, confirmado por execução.
Isso está registrado neste pass como achado do Eixo C
(`gov-seed-scan-regex-blind-to-flutter-swift-kotlin-rn-dotnet-rust-supabase`, MEDIUM-HIGH): são
**36 linhas** de `agents/` + `commands/` invisíveis à varredura obrigatória, uma delas
(`commands/sprint.md:74`) reescrita neste próprio delta.

## Descartados por duplicação

**Porta 1 (literal — `grep -F` do slug devolveu entrada no banco), 15:**

| Candidato | Fingerprint-pai | Estado |
|---|---|---|
| `devops-specialist.md:46-56` "**Primary**: Docker", "GitHub Actions (primary)" sob `## Core Expertise` | `agent-devops-specialist-core-expertise-declares-primary-docker-and-done-checklist-gates-on-docker-terraform-…` | MEDIUM, aberto |
| `devops-specialist.md:134-145` checklist com Docker não-gated e Terraform gated | mesmo pai | MEDIUM, aberto |
| `database-specialist.md:83` RLS como primeiro degrau da cascata multi-tenant | `agent-database-specialist-rls-as-engine-neutral-multitenant-default-and-gate` | MEDIUM-HIGH, aberto |
| `database-specialist.md:134` `psql "$SUPABASE_DB_URL"` inlinado | `agent-database-specialist-access-inlines-supabase-cli-while-delegating-others` | LOW-MEDIUM, aberto |
| `security-specialist.md:80-81` `${{ github.event.issue.title }}`, `pull_request_target` | `agent-security-specialist-cicd-checklist-github-actions-only-vocabulary` | MEDIUM-HIGH, aberto |
| `frontend-test-specialist.md:144-156` LCOV / `jest --coverage` / `vitest run` / `sonar.javascript.*` | `agent-frontend-test-specialist-sonarqube-coverage-block-hardcodes-jest-vitest-…` | MEDIUM-HIGH, aberto |
| `backend-reviewer.md:30` `phpcs.xml`/`pyproject.toml`/`.rubocop.yml`/`golangci.yml` | `agent-reviewer-linter-config-three-divergent-ecosystem-incomplete-copies` | MEDIUM, aberto |
| `mobile-developer.md:150` matriz de 5 runners | `agent-mobile-developer-routing-rules-restates-five-runner-matrix` | MEDIUM-HIGH, aberto |
| `product-analyst.md:147,163-167,170` gate em Docker + `ls docker-compose.yml …` inlinado | `agent-product-analyst-step6-gates-isolated-infra-on-docker-and-inlines-compose-probe` | MEDIUM, aberto |
| `frontend-developer.md:3` oito frameworks na `description:` | `agent-frontend-developer-description-frontmatter-enumerates-eight-frameworks-…` | MEDIUM, aberto |
| `audit.md:48` "spin up an isolated Docker stack" incondicional | `flow-audit-step2-unconditional-docker-stack-ignores-isolate-pref-compose-gate` | MEDIUM-HIGH, aberto |
| `audit.md:118,120` Redis/CDN e Docker no prompt de spawn | `flow-audit-command-devops-analysis-prompt-names-redis-cdn-docker-inside-spawn-instruction` | LOW-MEDIUM, aberto |
| `mobile.md:12,21,28` "React Native, Expo, Flutter, native iOS/Android" | `flow-mobile-command-spawn-line-enumerates-stacks-dropped-from-agent-description` | MEDIUM, aberto |
| `software-architect.md:89` `ScheduleWakeup`/`TaskList`/`TaskGet`/`SendMessage` | `flow-architect-claude-only-async-tool-names-rendered-verbatim` (✅) + `agent-software-architect-inlines-spawn-integrity-4-5-no-availability-guard` (aberto, cita "A linha 89") | matéria da Fase 1, não deste eixo |
| `database-specialist.md:65-72` engines na tabela de detecção | `agent-database-specialist-description-frontmatter-enumerates-12-engines-…` | MEDIUM |

**Porta 3 (semântica — 2 ou 3 de 3 atributos coincidem), 6:**

- `security-specialist.md:28-29` (via `git show HEAD:`) — "Read `Dockerfile` and `docker-compose.yml`", "Read `.github/workflows/*.yml` (or `.gitlab-ci.yml`, `bitbucket-pipelines.yml`)" — **2 de 3** contra `agent-security-specialist-cicd-checklist-github-actions-only-vocabulary`: alvo e remediação idênticos, só a causa raiz difere (lista de descoberta vs. vocabulário de achado). E `:29` já enumera três plataformas com "or", sendo *menos* acoplado que o bloco `:80-85` já registrado.
- `database-specialist.md:27` ("Check `.env`, `.env.local`, `docker-compose.yml` for connection strings") — **2 de 3** contra `agent-database-specialist-access-inlines-supabase-cli-while-delegating-others`: mesmo alvo e mesma remediação; a cascata de `:134` (a linha do próprio fingerprint) já repete `docker-compose.yml`.
- `frontend-reviewer.md:114,116` (TypeScript/PropTypes/`defineProps`, `React.ChangeEvent<HTMLInputElement>`) — já descartado por esta porta em 2026-08-21 e 2026-09-04; linhas deslocadas, conteúdo idêntico.
- `frontend-developer.md:91,96` (React `useState`, TanStack Query/SWR) — já descartado por esta porta em 2026-08-21; `:96` abre com "idiomatic to the project's stack", que é a formulação agnóstica.
- `sprint.md:53,57` · `merge.md:41,46` · `commit.md:36,40,45` · `relayout.md:43` (infra isolada "when the project uses Docker") — **2 de 3** contra `agent-product-analyst-step6-…`. Reforço por mérito: os quatro **delegam** a `skills/shared/worktree/SKILL.md` sem inlinar sonda — `merge.md:46` chega a dizer "Do not reimplement that sequence here".
- `devops.md:2,14` (Docker/CI na `description:` e na lista de agentes) — já descartado por esta porta em 2026-08-21, 08-28 e 09-11.

**Porta 4 (escopo estritamente menor, sem sub-escopo novo), 2:**

- `devops-specialist.md:28,118,169` ("Docker files", "GitHub Secrets, CI variables", "shell scripts, Dockerfiles, CI/CD configs") — sub-escopo de `agent-devops-specialist-core-expertise-…` sem nada que o pai não cubra; `:118` diz "that platform's secret store" (agnóstico, com exemplo). O banco já descartou `devops-specialist.md:137-148` por esta porta em 2026-08-21 e 08-28.
- `mobile-developer.md:160` (`[ ] Framework skill loaded if applicable (React Native or Flutter)`) — registrado como `mobile-developer.md:159` nos conjuntos de descarte de 2026-09-04 e 09-11.

**Porta 5 (estado — já registrado e aberto), 2:**

- `relayout.md:32` (Storybook/Tailwind entre as localizações de design system) — no conjunto aberto desde 2026-08-21.
- `commands/spec.md:44` ("`mobile-developer` in a tests-only spawn for Flutter/native") — **candidato fora da semente**, achado varrendo os arquivos novos do delta. Cai duas vezes: a linha é citada textualmente como evidência em `skill-spec-gate-touches-accepts-database-layer-with-no-test-author-in-any-track` (MEDIUM-HIGH, aberto), e causa raiz e remediação coincidem com `flow-mobile-command-spawn-line-enumerates-stacks-…`.

**Porta 2 (território novo) seguido de descarte por mérito, 2:**

- `up.md:2,3,19` — `grep -i "up.md"` nos dois índices devolve **zero**: território genuinamente novo, o único do eixo. Auditado integralmente e sem defeito (ver acima).
- `backend-reviewer.md:136` (`Missing @throws or exception docs where the type system can't express the type`) — `@throws` existe em Javadoc, PHPDoc e JSDoc, e "or exception docs" na mesma linha já generaliza. Nada a corrigir.
- `backend-reviewer.md:170` (`file.php:88`) — o template de `:160-186` rotaciona `.go/.php/.py/.rb/.ts` de propósito, fato que o próprio banco consigna no corpo de `agent-code-reviewer-output-template-pins-file-js-six-placeholders`. Hipótese refutada por evidência já registrada.
