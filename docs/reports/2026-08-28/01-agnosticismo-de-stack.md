# Eixo A — Agnosticismo de stack (2026-08-28)

**Baseline:** `HEAD` = `a67cac9` · **Baseline anterior:** `a67cac9` · Varredura **integral**, conforme
a regra do eixo.

## Resultado

**124 candidatos → 0 violações.** Nenhum achado original neste eixo.

Este é um resultado válido, não uma varredura incompleta: a varredura semente foi executada na
íntegra sobre `agents/` e `commands/`, cada hit foi classificado, e **todo candidato que sobreviveu à
triagem de seção caiu numa porta anti-duplicação** — a maioria na Porta 5 (estado), contra achados
que os passes de 2026-07-31, 2026-08-14 e 2026-08-21 já registraram e que continuam **abertos**.

O eixo está saturado. O que falta não é descoberta, é execução.

---

## Método

Varredura semente obrigatória, executada antes de qualquer leitura:

```bash
rg -in 'laravel|symfony|django|rails|spring|express|nest|next\.js|react|vue|angular|svelte|\
tailwind|bootstrap|eloquent|prisma|hibernate|sequelize|typeorm|phpunit|jest|vitest|pytest|\
rspec|composer|npm|yarn|pnpm|pip|maven|gradle|docker|kubernetes|terraform|aws|gcp|azure|\
mysql|postgres|mongodb|redis|php|python|ruby|golang|typescript|javascript' agents/ commands/
```

**124 hits em 25 arquivos.** Cada hit foi anotado com o heading da seção que o contém, via um `awk`
que rastreia o último `^#{1,4} ` acima da linha — a promoção a violação exige que o hit esteja sob uma
**seção de comportamento**, e o heading foi registrado junto do trecho.

### Distribuição dos candidatos

| Arquivo | Hits | Arquivo | Hits |
|---|---:|---|---:|
| `agents/devops-specialist.md` | 23 | `agents/backend-developer.md` | 5 |
| `agents/mobile-developer.md` | 12 | `commands/relayout.md` · `explain.md` · `audit.md` | 3 cada |
| `agents/database-specialist.md` | 12 | `agents/ui-ux-designer.md` · `backend-reviewer.md` | 3 cada |
| `agents/security-specialist.md` | 8 | `commands/mobile.md` · `merge.md` · `devops.md` | 2 cada |
| `agents/product-analyst.md` | 8 | `agents/qa-specialist.md` · `frontend-reviewer.md` | 2 cada |
| `agents/frontend-test-specialist.md` | 8 | `commands/rule.md` · `health-check.md` · `adr.md` | 1 cada |
| `agents/frontend-developer.md` | 8 | `agents/software-architect.md` · `code-reviewer.md` | 1 cada |
| `commands/commit.md` · `agents/setup-assistant.md` | 5 cada | | |

### Triagem: por que 124 → 0

| Classe | Qtd. aprox. | Destino |
|---|---:|---|
| **Tabelas de detecção / roteamento condicional de skill** — `## Integration Awareness`, `## Platform Awareness`, `## UI Library Awareness`, `### Platform skills — two-gate routing`, `## Mobile Testing Routing`, tabelas de engine de banco | ~72 | **Exceção legítima por design.** O sinal de detecção *tem* que nomear a tecnologia — é essa a função da linha |
| **Listas de skills condicionais e referências a skills específicas** — `skills/devops/*`, `skills/ui-libraries/*`, `skills/integrations/*`, `skills/mobile/*` | ~24 | **Exceção explícita** na regra do eixo |
| **Superfícies de exemplo / template de saída** — `agents/backend-reviewer.md:170` (`file.php:88`), `:168` (`file.go:42`), `:172` (`file.py:33`); `commands/adr.md:12` ("e.g.: `/devteam:adr Adopt PostgreSQL…`") | ~9 | **Descartado por regra** — hits sob "Example" não promovem |
| **Instrução anti-hardcode** — `commands/explain.md:48`: "a fenced block in the project's actual language and framework, detected from the repo — **never defaulting to JavaScript**" | 1 | Não é violação: é a regra do eixo **sendo aplicada** |
| **Gate condicional legítimo** — `agents/product-analyst.md:132-153`, que condiciona stack Docker isolado a "**only when the project uses Docker** (a compose file exists)" e detecta com `ls docker-compose.yml …` | 6 | Mecanismo de isolamento por worktree, explicitamente gated. Não é prescrição de stack |
| **Candidatos genuínos sob seção de comportamento** | **12** | Todos caíram nas portas anti-duplicação — detalhados abaixo |

---

## Os 12 candidatos genuínos e a porta que os rejeitou

Cada um destes está **de fato** sob uma seção de comportamento e **seria** um achado se o banco
estivesse vazio. Todos já estão registrados.

### 1. `agents/frontend-test-specialist.md:141-153` — bloco SonarQube hardcoda Jest/Vitest/LCOV

O caso mais forte do eixo, e o mais claramente já registrado. A seção `## SonarQube Coverage
Integration` diz "Generate coverage in LCOV format — **the standard for JavaScript/TypeScript
projects**" e inlina `jest --coverage --coverageReporters=lcov`, `vitest run --coverage
--coverage.reporter=lcov` e `sonar.javascript.lcov.reportPaths=coverage/lcov.info`.

O gêmeo backend já foi refatorado para o oposto — `agents/backend-test-specialist.md:108`: "read
`references/quality-gates.md` in that skill for the **per-language** test-runner command, output
artifact, and `sonar.*coverage.reportPaths` key". E a casa canônica existe e já contém as duas linhas
JS: `skills/devops/sonarqube/references/quality-gates.md:75-76`.

- **Porta 5 (estado).** `agent-frontend-test-specialist-sonarqube-coverage-block-hardcodes-jest-vitest-commands-and-sonar-javascript-key-while-backend-twin-was-delegated`
  — **MEDIUM-HIGH, registrado em 2026-07-31, ainda aberto.** Reapresentá-lo seria ruído.

### 2. `agents/database-specialist.md:84` — RLS como default de multi-tenancy

`## Schema Design Principles` — "**Multi-tenant:** RLS (default for PostgreSQL) →
schema-per-tenant → database-per-tenant". Seção de comportamento, cascata ancorada num engine, num
roster de 9 engines em que mysql/mongodb/redis/sqlite/cassandra não têm RLS.

- **Porta 1 (literal).** `agent-database-specialist-rls-as-engine-neutral-multitenant-default-and-gate`
  — **MEDIUM-HIGH, registrado em 2026-08-21, aberto.** Alvo, linha e causa idênticos.

### 3. `agents/devops-specialist.md:137-148` — checklist de "done" gateia em Docker e Terraform

`## What to Do Before Declaring Done` abre com "Docker image builds cleanly and runs in target
environment" **sem condicional**, enquanto os itens de Terraform 10 linhas abaixo trazem "(if
Terraform is in use)". A assimetria é interna à mesma lista, e o próprio agente diz em `:131`
"**Never name a specific product as the answer**".

- **Porta 4 + Porta 5.** `agent-devops-specialist-core-expertise-declares-primary-docker-and-done-checklist-gates-on-docker-terraform-contradicting-own-never-name-a-product-rule`
  — MEDIUM, aberto, e o próprio pass de 2026-08-21 já listou `devops-specialist.md:137-148` como
  descarte de Porta 4. Não há sub-escopo novo.

### 4. `agents/security-specialist.md:80-85` — checklist de CI/CD em vocabulário só do GitHub Actions

Seis itens em `### CI/CD Pipeline Security` usando `${{ github.event.issue.title }}`,
`pull_request_target` e "self-hosted runners", enquanto `:29` manda ler `.gitlab-ci.yml` e
`bitbucket-pipelines.yml`.

- **Porta 1 (literal).** `agent-security-specialist-cicd-checklist-github-actions-only-vocabulary`
  — **MEDIUM-HIGH, 2026-08-21, aberto.**

### 5. `agents/backend-reviewer.md:30` — configs de linter em lista fechada de 4 ecossistemas

"Read the linter / static-analysis configs (`phpcs.xml`, `pyproject.toml`, `.rubocop.yml`,
`golangci.yml`)" — sem `.eslintrc*`, e divergente das outras duas cópias (`reviewer-base:11` com 5
arquivos, `frontend-reviewer:31` com um conjunto JS-only).

- **Porta 1 (literal).** `agent-reviewer-linter-config-three-divergent-ecosystem-incomplete-copies`
  — MEDIUM, 2026-08-21, aberto.

### 6. `agents/mobile-developer.md:159` — checklist de "done" nomeia 2 dos 5 frameworks roteados

"Framework skill loaded if applicable (**React Native or Flutter**)" numa seção de comportamento,
enquanto a tabela de roteamento de `:70-74` cobre iOS, Android, React Native, Expo e Flutter.

- **Porta 3 (semântica, 2 de 3).** Contra
  `flow-mobile-command-spawn-line-enumerates-stacks-dropped-from-agent-description` (MEDIUM, aberto):
  o **alvo** difere (agente vs. comando), mas a **causa raiz** ("superfície de comportamento enumera
  stacks concretas depois que a enumeração foi removida do frontmatter") e a **remediação**
  ("substituir pela forma agnóstica — *a skill de framework detectada*") coincidem. Dois de três ⇒
  duplicata.

### 7–12. Os demais

| Candidato | Porta | Fingerprint colidido |
|---|---|---|
| `agents/frontend-developer.md:3` — oito frameworks na frontmatter | Porta 5 | `agent-frontend-developer-description-frontmatter-enumerates-eight-frameworks…` (MEDIUM, aberto) |
| `agents/frontend-developer.md:91,96` — `React useState` e fallback de data fetching | Porta 3 (já descartado assim em 2026-08-21) | `agent-frontend-developer-body-92-102-data-fetching-section-hardcodes-u…` (✅ Executed) |
| `agents/frontend-reviewer.md:112,114` — `React.ChangeEvent<HTMLInputElement>`, `defineProps` | Porta 3 (2 de 3, já descartado em 2026-08-21) | família `agent-*-hardcodes-react-*` |
| `agents/database-specialist.md:133` — `psql "$SUPABASE_DB_URL"` inline em `## Database Access` | Porta 5 | `agent-database-specialist-access-inlines-supabase-cli-while-delegating-others` (LOW-MEDIUM, aberto) |
| `commands/audit.md:54,126,128` — Docker/Redis/CDN dentro da instrução de spawn | Porta 5 | `flow-audit-command-devops-analysis-prompt-names-redis-cdn-docker-inside-spawn-instruction` + `flow-audit-step2-unconditional-docker-stack-ignores-isolate-pref-compose-gate` (ambos abertos) |
| `commands/relayout.md:32` — Storybook / Tailwind na descoberta de design | Porta 5 | `flow-relayout-design-discovery-names-storybook-tailwind` (aberto) |
| `commands/mobile.md:19,26` — "React Native, Expo, Flutter, native iOS/Android" na linha de spawn | Porta 5 | `flow-mobile-command-spawn-line-enumerates-stacks-dropped-from-agent-description` (MEDIUM, aberto) |
| `commands/devops.md:2,14` — "CI/CD, Docker, infra" na `description` e na linha de spawn | Porta 3 (já descartado em 2026-08-14 e 08-21) | família `agent-devops-specialist-*` |
| `agents/setup-assistant.md:146-147` — extensões de config de teste e DevOps na geração de docs | Porta 5 | listado como aberto desde 2026-07-31 |
| `commands/commit.md:125-128` — tabela de comandos de lint por ecossistema | Porta 5 + exceção de tabela de detecção | listado como aberto desde 2026-07-31 |

---

## Leitura do eixo

O padrão que sai desta varredura não é sobre agnosticismo — é sobre **fila**. Dos 12 candidatos
genuínos, **10 estão registrados e abertos**, dois deles MEDIUM-HIGH há mais de um mês
(`frontend-test-specialist` SonarQube desde 2026-07-31; `security-specialist` CI/CD e
`database-specialist` RLS desde 2026-08-21). O eixo A não produz achado novo porque tudo o que ele
encontraria já está encontrado.

Isso é consistente com o achado principal do pass, registrado no `index.md`: o problema deste
repositório hoje não é a taxa de descoberta, é a taxa de execução — agravada por sete dias sem um
único commit e pelo output do pass anterior que nunca chegou ao remoto.

**Nenhum achado original neste eixo.**
