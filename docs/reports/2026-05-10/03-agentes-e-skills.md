# 03 — Agentes e Skills

← [Voltar ao índice](index.md) · [← Seção anterior](02-fluxos-e-workflows.md)

**Data:** 2026-05-10
**Escopo:** Quinta passada — `database-specialist` ainda monolítico (6 engines inline), skills estratégicas ausentes (event-driven, rate-limiting, performance budgets, api-versioning, Diátaxis), `product-analyst` desacoplado de jira skill apesar de ter integração.
**Anti-repetição:** Os 110 fingerprints publicados em 2026-05-06 / -07 / -08 / -09 foram excluídos.

---

## Sumário

A passada anterior (09) identificou skills domain-strategic ausentes: caching, i18n, monorepo, resilience, migration-zero-downtime, owasp-top-10, secret-management, sast-pipeline, contract-testing, git-workflow. Verificação mostra que **todas as 10 já existem**, endereçando aqueles fingerprints com criação ativa entre 09 e hoje.

**Esta passada identifica três classes ainda não cobertas:**

1. **Cobertura per-engine ainda monolítica em `database-specialist`** — o agente cobre MySQL/PostgreSQL/SQL Server/MongoDB/Redis/Cassandra/SQLite em 272 linhas inline. A criação recente de `skills/database/migration-zero-downtime/` e `skills/database/db-comparison/` mostra apetite por skills database; falta o split per-engine análogo ao `cicd-base` + `cicd-{github,gitlab,bitbucket,jenkins}` já implementado.

2. **Skills estratégicas ainda não cobertas** — apesar do bom progresso da passada 09, persistem gaps em event-driven architecture (CQRS, saga, event sourcing), rate-limiting (algoritmos), performance budgets (Web Vitals, bundle size), api-versioning dedicado (vai além de `api-design`).

3. **Skills extraídas com prosa inline ainda mantida em agentes** — caso emblemático: `reviewer-mindset` foi extraído como skill (19 linhas), mas `code-reviewer.md` ainda tem 12 linhas de mindset **inline** + carrega a skill como passo 12 do Foundational Rule. Bytes duplicados em ambos.

---

## Sugestões

### 1. `database-specialist` cobre 6+ engines em 272 linhas; sem skills per-engine

**Fingerprint:** `agent-database-specialist-no-per-engine-skills`

**Evidência:**

```bash
$ wc -l agents/database-specialist.md
272 agents/database-specialist.md

$ grep -E "MySQL|PostgreSQL|SQL Server|MongoDB|Redis|Cassandra|SQLite" agents/database-specialist.md | wc -l
35+ menções inline
```

O agente trata todos os engines em prosa única. Decisões e gotchas específicas (MVCC do Postgres vs InnoDB do MySQL, sharding do Mongo vs partitioning do Postgres, etc.) viram bullets misturados. Skills propostas:

```
skills/database/mysql/SKILL.md
skills/database/postgres/SKILL.md
skills/database/mongodb/SKILL.md
skills/database/redis/SKILL.md
skills/database/sqlserver/SKILL.md
skills/database/cassandra/SKILL.md
skills/database/sqlite/SKILL.md
```

Padrão exato do `cicd-base` + variantes per-platform já implementado. O `database-specialist` carregaria a skill correta após detectar engine via `package.json`, `composer.json`, `docker-compose.yml`, `database.yml`, `prisma/schema.prisma`, etc.

Detecção simples:

| Sinal | Engine |
|-------|--------|
| `mysql:` em docker-compose, `mysql2` em package.json | mysql |
| `postgres:` em docker-compose, `pg`/`psycopg2` em deps | postgres |
| `mongodb:` em docker-compose, `mongoose` em deps | mongodb |
| `redis:` em docker-compose | redis |

**Impacto positivo:**
- `database-specialist.md` pode reduzir a ~150 linhas (igual a outros agentes);
- Detalhes engine-specific ficam isolados e fáceis de evoluir;
- Permite que `backend-developer` carregue a skill correta diretamente quando necessário (não precisa invocar database-specialist completo).

**Impacto negativo:**
- Muito conteúdo para escrever (7 skills × ~150 linhas);
- Sobreposição com `db-comparison` existente — precisa decidir granularidade;
- Engines de nicho (Cassandra, SQLite) podem ter pouco volume de uso real, gerando manutenção sem retorno.

**Esforço:** Alto. Recomenda começar com os 3 mais usados (postgres, mysql, mongodb).

---

### 2. Sem skill para event-driven architecture

**Fingerprint:** `skill-missing-event-driven-architecture`

**Evidência:**

```bash
$ ls skills/architecture/ | grep -i "event\|cqrs\|saga\|message"
```

(vazio)

Skills relacionadas existentes: `async-jobs` (queue patterns), `resilience` (retry/circuit breaker). Faltam os padrões de **comunicação assíncrona orientada a eventos**:

- **Event sourcing** — store-of-events em vez de current-state;
- **CQRS** — separação de read e write models;
- **Saga pattern** — coordenação de transações distribuídas (orchestration vs choreography);
- **Domain events vs integration events** — granularity e versionamento;
- **Idempotency keys + deduplication** — receber o mesmo evento duas vezes;
- **Schema registry + event versioning** — Avro, Protobuf, JSON Schema;
- **Eventual consistency tradeoffs**.

Esses padrões são especialmente relevantes a `backend-developer` (implementação), `software-architect` (decisões) e `database-specialist` (event store).

**Impacto positivo:**
- Cobertura crítica para microsserviços e sistemas distribuídos;
- Decisões arquiteturais importantes sem skill hoje vão por intuição do agente;
- Complementa `async-jobs` (que cobre queue/job, não event sourcing).

**Impacto negativo:**
- Conteúdo extenso (~300+ linhas);
- Risco de overengineering em projetos monolíticos (mitigado pela descrição "load when project uses event sourcing or message-driven architecture").

**Esforço:** Alto.

---

### 3. Sem skill para rate-limiting algorithms

**Fingerprint:** `skill-missing-rate-limiting`

**Evidência:**

```bash
$ find skills -name "SKILL.md" | xargs grep -l "rate limit" 2>/dev/null
skills/devops/cloudflare/SKILL.md
skills/security/iso27001-sgsi/SKILL.md
skills/security/owasp-top-10/SKILL.md
```

Os 3 arquivos mencionam rate-limit como conceito, mas nenhum é skill dedicada. Faltam:

- **Algoritmos**: token bucket, leaky bucket, fixed window, sliding window, sliding log;
- **Onde aplicar**: edge (CloudFlare/CDN), API gateway (Kong/Tyk), app-level (middleware), per-DB-query;
- **Granularidade**: per-user, per-IP, per-API-key, per-endpoint, per-tenant;
- **Storage**: in-memory (single-instance), Redis (distributed), DynamoDB streams;
- **Failure modes**: degraded mode quando o store de rate-limit falha;
- **Headers**: `Retry-After`, `X-RateLimit-{Limit,Remaining,Reset}`.

Skill proposta: `skills/architecture/rate-limiting/SKILL.md`.

**Impacto positivo:**
- Decisões consistentes entre `backend-developer` (middleware) e `devops-specialist` (edge);
- Cobre área onde decisões erradas têm impacto operacional (DDoS, ataque de cliente "maluco");
- Complementa `resilience` (foco em retry/circuit, não em prevenção).

**Impacto negativo:**
- Algumas escolhas dependem fortemente do tech stack (já tem Redis? CDN? gateway?).

**Esforço:** Médio.

---

### 4. Sem skill para performance budgets (Web Vitals, bundle size)

**Fingerprint:** `skill-missing-performance-budgets`

**Evidência:**

```bash
$ find skills -name "SKILL.md" | xargs grep -l "Web Vitals\|Core Web Vitals\|performance budget" 2>/dev/null
```

(vazio)

`frontend-developer` e `ui-ux-designer` produzem código que vai para o navegador, mas não há referência a performance budgets formais:

- **Core Web Vitals**: LCP < 2.5s, FID/INP < 200ms, CLS < 0.1;
- **Bundle size budgets**: JS inicial < 200KB gzip; total < 500KB;
- **Lighthouse CI**: rodar em PR, gate em score mínimo;
- **Image optimization**: budget de KB por viewport, formats (AVIF > WebP > JPEG);
- **Critical CSS**: inline first-paint, defer rest;
- **Resource hints**: preload, prefetch, modulepreload — quando usar cada;
- **Long Animation Frames (LoAF)** — sinal de jank novo do Chrome.

Skill proposta: `skills/architecture/performance-budgets/SKILL.md`.

**Impacto positivo:**
- Foco em UX de produção (não só código limpo);
- Permite `code-reviewer` flagar `[BLOCKING] bundle-size-over-budget`;
- Complementa CI ideias (Lighthouse CI step).

**Impacto negativo:**
- Budgets variam por projeto (mitigado: skill define como decidir, projeto registra valores em `code-standards.md`);
- Não aplicável a aplicações backend-only.

**Esforço:** Médio.

---

### 5. Sem skill para API versioning estratégico

**Fingerprint:** `skill-missing-api-versioning-dedicated`

**Evidência:**

`skills/architecture/api-design/SKILL.md` aborda versioning brevemente, misturado com naming/pagination/idempotency. Faltam discussão profunda:

- **Strategies**: URL (`/v1/`, `/v2/`), header (`Accept-Version`), content negotiation (`Accept: application/vnd.api+json; version=2`), query param (`?version=2`);
- **Deprecation lifecycle**: warning header, sunset header, removal timeline;
- **Backwards-compatible changes vs breaking**: adicionar campo (compatível); remover campo, alterar tipo, mudar required→optional inverso (breaking);
- **Versionamento de SDK vs API**: relação cross-language;
- **API gateway routing** entre versões;
- **Mobile/long-tail clients**: políticas de support window;
- **OpenAPI evolution**: como diff entre versões.

Skill proposta: `skills/architecture/api-versioning/SKILL.md`, com `api-design` cross-referenciando.

**Impacto positivo:**
- Decisão upfront que afeta toda a vida do produto;
- Complementa `api-design` sem inflar;
- Útil para `backend-developer`, `software-architect`, e `code-reviewer` (flag breaking changes).

**Impacto negativo:**
- Sobreposição com `api-design` — precisa decidir o escopo claro;
- Algumas estratégias são religiosas; risco de virar guideline opinativo.

**Esforço:** Médio.

---

### 6. Conteúdo de Diátaxis não extraído como skill

**Fingerprint:** `skill-diataxis-not-extracted`

**Evidência:**

```bash
$ grep -l "Diátaxis" agents/ skills/ -r
agents/technical-writer.md
```

`technical-writer.md` (173 linhas) tem seção "Diátaxis Document Types" inline (Tutoriais, How-to, Reference, Explanation). É conhecimento reusável que:

- `software-architect` pode precisar ao decidir estrutura de docs;
- `code-reviewer` pode usar para flagar "esse README mistura tutorial com reference";
- Skill própria permite expandir (templates por tipo, exemplos, anti-patterns).

Skill proposta: `skills/shared/diataxis-framework/SKILL.md`.

**Impacto positivo:**
- Reaproveitável fora do `technical-writer`;
- `technical-writer` fica ~30-50 linhas menor;
- Permite cross-link com `docs-templates` skill existente.

**Impacto negativo:**
- Trade-off pequeno (já era inline funcional);
- Skill própria pode ficar curta (~80 linhas) — limiar de "vale a extração?".

**Esforço:** Médio.

---

### 7. `discovery-mode` skill carregada por dois agentes mas não pelo `setup-assistant` (que também classifica projetos)

**Fingerprint:** `skill-discovery-mode-not-loaded-by-setup-assistant`

**Evidência:**

```bash
$ grep -rl "discovery-mode" agents/
agents/software-architect.md
agents/product-analyst.md
```

`setup-assistant` Step 2 pergunta o tipo de projeto ("new / unfinished / maintenance") — exatamente o tipo de decisão que `discovery-mode` skill suporta. Mas o setup-assistant não carrega a skill.

Verificar se `discovery-mode` contém conteúdo aplicável: se sim, adicionar ao setup-assistant Foundational Rule. Se não, documentar por que setup-assistant tem caminho próprio (sem skill).

**Impacto positivo:**
- Consistência: classificação de projeto fica em um lugar;
- Possibilita melhor handoff `setup-assistant` → `product-analyst`/`software-architect`.

**Impacto negativo:**
- Pode adicionar carga desnecessária se discovery-mode for orientado a outro caso;
- Risco de "skill nova vira fonte de verdade falsa" se setup-assistant tinha lógica diferente por razão.

**Esforço:** Baixo (decisão).

---

### 8. `product-analyst` não carrega `jira` skill no Foundational Rule apesar do CLAUDE.md mencionar Jira como tracker primário

**Fingerprint:** `agent-product-analyst-jira-skill-not-loaded-foundational`

**Evidência:**

`agents/product-analyst.md` tem `tools: Read, Write, Edit, Glob, Grep, WebSearch` e o Foundational Rule não inclui `skills/integrations/jira/SKILL.md`. No entanto:

- `qa-specialist` carrega jira skill condicionalmente (presença de Jira key);
- `code-reviewer` carrega jira skill condicionalmente;
- `product-analyst` produz backlog **inicial** — momento ideal de criar Jira issues a partir de epics/sprints.

O agente lida com PRDs (documentos), gera estrutura de backlog. Se o projeto usa Jira (registrado em CLAUDE.md), o agente deveria oferecer criar issues correspondentes.

```markdown
## Step N — Tracker integration (product-analyst)

If CLAUDE.md registers `TRACKER: jira`:
- Load `skills/integrations/jira/SKILL.md`
- Offer to create issues/epics/stories from the generated backlog
- Wait for user approval before creating
```

**Impacto positivo:**
- Backlog em markdown + Jira sincronizados;
- Reduz "copia da markdown para Jira" manual;
- Aproveita capacidade já presente (skill existe e funciona).

**Impacto negativo:**
- Risco de duplo source-of-truth se markdown e Jira evoluem independente;
- Criação em massa de issues pode ser indesejada (mitigado: confirmação por epic).

**Esforço:** Baixo (carga condicional).

---

### 9. Skills `database-debug` e `database-multitenancy` órfãs do `database-specialist`

**Fingerprint:** `skill-database-debug-multitenancy-not-loaded-by-database-specialist`

**Evidência:**

```bash
$ grep -l "database-debug" agents/
agents/database-specialist.md (verifique se realmente carrega)

$ grep "database-debug\|database-multitenancy" agents/database-specialist.md
```

Ambas as skills estão em `skills/integrations/`, mas `database-specialist` é o consumidor natural. Validar se o load está explícito no Foundational Rule do `database-specialist` ou se é condicional na detecção (multitenancy detectado por presença de `tenant_id` em schemas, por exemplo).

**Impacto positivo:**
- Cobertura completa do domain do agente;
- Pattern de detecção condicional já estabelecido (jira, sonarqube, supabase, etc.).

**Impacto negativo:**
- Se a heurística de detecção for fraca (e.g., assumir multi-tenancy só por nome de coluna), gera falso positivo.

**Esforço:** Baixo (verificação + adição condicional).

---

## Resumo dos Fingerprints

| # | Fingerprint | Categoria | Esforço |
|---|------------|-----------|---------|
| 1 | `agent-database-specialist-no-per-engine-skills` | Decomposição de agente | Alto |
| 2 | `skill-missing-event-driven-architecture` | Skill nova | Alto |
| 3 | `skill-missing-rate-limiting` | Skill nova | Médio |
| 4 | `skill-missing-performance-budgets` | Skill nova | Médio |
| 5 | `skill-missing-api-versioning-dedicated` | Skill nova | Médio |
| 6 | `skill-diataxis-not-extracted` | Extração de inline | Médio |
| 7 | `skill-discovery-mode-not-loaded-by-setup-assistant` | Cobertura de carregamento | Baixo |
| 8 | `agent-product-analyst-jira-skill-not-loaded-foundational` | Cobertura de carregamento | Baixo |
| 9 | `skill-database-debug-multitenancy-not-loaded-by-database-specialist` | Cobertura de carregamento | Baixo |

---

← [Seção anterior](02-fluxos-e-workflows.md) · [Voltar ao índice](index.md) · [Próxima seção →](04-economia-tokens.md)
