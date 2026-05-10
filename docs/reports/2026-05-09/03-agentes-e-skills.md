# 03 — Agentes e Skills

**Data:** 2026-05-09
**Escopo:** Quarta passada — sobreposição de agentes reviewers, skills ausentes em domínios estratégicos, cobertura assimétrica entre `devops/` (rica) e `security/`/`testing/` (rasas), padrão `When loaded` adotado por apenas 1 agente.
**Anti-repetição:** os 75 fingerprints anteriores excluídos.

---

## Sumário

`devops/` tem 11 skills, `integrations/` tem 11, `architecture/` tem 11. `security/` tem 1. `testing/` tem 2. `design/` tem 3. Essa assimetria é o tema central desta passada — os agentes mais críticos (`security-specialist`, `qa-specialist`, `backend-test-specialist`, `frontend-test-specialist`) estão sustentados por uma base de skills muito mais magra que seus pares de devops/integrations.

A segunda observação é estrutural: os 3 agentes reviewers (`code-reviewer`, `backend-reviewer`, `frontend-reviewer`) compartilham ~80% de estrutura mas vivem como arquivos independentes — alvo natural de templating.

---

## Sugestões

### 1. Sobreposição estrutural entre os 3 agentes reviewers

**Fingerprint:** `agent-three-reviewers-overlap`

**Evidência:** `diff agents/backend-reviewer.md agents/frontend-reviewer.md` produz 272 linhas de diff sobre arquivos de 212 e 201 linhas respectivamente — ou seja, ~30% comum. Comparando os 3 reviewers:

| Bloco | code-reviewer | backend-reviewer | frontend-reviewer |
|-------|---------------|-------------------|---------------------|
| `## Reviewer Mindset` | ~12 linhas | ~12 linhas (variantes) | ~12 linhas (variantes) |
| `## Foundational Rule` | ~13 linhas | ~13 linhas | ~12 linhas |
| `## Routing` (router load) | sim | parcial (recebe routing) | parcial |
| Categorias de review | 7 genéricas | 7 backend-specific | 7 frontend-specific |

A diferença real é só nas **categorias** (parte legítima e específica). Os outros 4 blocos são quase iguais.

**Impacto positivo:** extrair `skills/shared/reviewer-base/SKILL.md` com Mindset + Foundational Rule + Routing pode reduzir cada um dos 3 agentes em ~40 linhas. Ganho total ~120 linhas. Manutenção centralizada.

**Impacto negativo:** uma mudança no Mindset agora se reflete instantaneamente nos 3; isso é normalmente bom, mas dificulta divergência intencional (ex.: reviewer de segurança com mindset diferente).

**Esforço:** Médio.

---

### 2. Faltam skills de caching strategies

**Fingerprint:** `skill-missing-caching-strategies`

**Evidência:** Não há skill em `skills/architecture/`, `skills/integrations/` ou outro lugar para caching (Redis, in-memory, ETag, CDN edge cache, browser cache). `database-specialist` cobre Redis como database mas não como cache layer. `devops-specialist` cobre `cloudflare` (CDN) sem o ângulo de cache strategy.

Caching é decisão arquitetural transversal: invalidação, TTL, write-through vs write-back, cache stampede. Hoje, agentes que precisam dessa decisão a tomam ad-hoc.

**Impacto positivo:** skill `skills/architecture/caching/SKILL.md` cobre patterns + heurísticas de invalidação. `backend-developer`, `database-specialist`, `frontend-developer` carregam quando relevante.

**Impacto negativo:** mais uma skill para manter.

**Esforço:** Médio (1 skill nova, ~150 linhas).

---

### 3. Faltam skills de i18n / l10n

**Fingerprint:** `skill-missing-i18n-l10n`

**Evidência:** Repo é bilíngue (`README.md` + `README.pt-BR.md`) mas não tem skill para projetos com requisito de i18n. Decisões típicas (ICU vs gettext, lazy-load de bundles de tradução, RTL handling, plurals) ficam ad-hoc.

**Impacto positivo:** skill `skills/architecture/i18n/SKILL.md` cobre tooling, arquitetura de bundles, fluxo de tradução. Útil para `frontend-developer` e `backend-developer`.

**Impacto negativo:** projeto pequeno raramente precisa; skill carregada à toa pode poluir contexto.

**Esforço:** Médio.

---

### 4. Faltam skills de monorepo patterns

**Fingerprint:** `skill-missing-monorepo-patterns`

**Evidência:** Sem skill para Turborepo, Nx, pnpm workspaces, Yarn workspaces, Bazel, Lerna. Monorepo é tendência clara em 2026; `devops-specialist` e `software-architect` precisam dessa skill ao decidir estrutura de repo de uma equipe.

**Impacto positivo:** skill cobre trade-offs (compartilhamento de tipo, build cache, ownership). Reduz "stack inferido por hábito".

**Impacto negativo:** se mal escrita, pode endossar prematuramente monorepo onde polyrepo é melhor (anti-padrão).

**Esforço:** Médio.

---

### 5. Faltam skills de migração de dados zero-downtime

**Fingerprint:** `skill-missing-data-migration-zero-downtime`

**Evidência:** `database-specialist` (325 linhas) cobre design de schema e queries. Skills `database-debug`, `database-multitenancy`, `database-production` cobrem operação. Não há skill específica para **migração** complexa: backfill em chunks, expand-contract, double-write, blue-green schema, transformação de coluna em produção sem lock.

**Impacto positivo:** skill formaliza patterns que hoje vivem como "todo dev sênior sabe". Crítico em projetos com tabelas > 10M de linhas.

**Impacto negativo:** sobreposição com `database-production` (que toca operação). Risco de borrar fronteira.

**Esforço:** Médio.

---

### 6. Faltam skills de resilience patterns

**Fingerprint:** `skill-missing-resilience-patterns`

**Evidência:** Circuit breaker, retry-with-backoff, bulkhead, timeout, jitter, hedge requests. Tópicos elementares para microsserviços e integrações. Hoje `backend-developer` e `software-architect` enfrentam essas decisões sem skill de apoio. `architecture/async-jobs/SKILL.md` toca em retry mas no contexto de jobs, não de integrações síncronas.

**Impacto positivo:** skill `skills/architecture/resilience/SKILL.md` formaliza padrões — especialmente útil em revisão (`backend-reviewer` ganha base).

**Impacto negativo:** pode encorajar uso preventivo onde não há justificativa (over-engineering).

**Esforço:** Médio.

---

### 7. `skills/security/` tem apenas 1 skill (`security-checklist`)

**Fingerprint:** `skill-security-only-checklist`

**Evidência:** `security-specialist.md` (223 linhas, modelo Opus) declara cobertura de OWASP Top 10, OWASP API Top 10, LGPD/GDPR, CI/CD security, business logic flaws, SAST, secrets scanning, infrastructure hardening — 8 áreas distintas. O suporte de skills é uma única `security-checklist`. Comparativamente:

| Categoria | Skills count | Agente principal |
|-----------|--------------|-------------------|
| `security/` | 1 | security-specialist (Opus) |
| `devops/` | 11 | devops-specialist (Sonnet) |
| `architecture/` | 11 | software-architect (Opus) |
| `integrations/` | 11 | (genérico) |

Skills úteis para criar (sem necessariamente todas):

- `security/owasp-top-10/` — referência por categoria
- `security/secret-management/` — vault, env vars, rotação
- `security/lgpd-gdpr-checklist/`
- `security/sast-pipeline/` — Semgrep, CodeQL, Snyk
- `security/dependency-vulnerabilities/` — Renovate, Dependabot, fixing CVEs
- `security/incident-response/` — runbook (já flagado em 2026-05-06 como skill ausente, complementar aqui)

**Impacto positivo:** alinhamento entre o "modelo Opus do agent" e a profundidade do material que ele consulta. Hoje o agente é potente mas opera com pouca skill backing.

**Impacto negativo:** explosão de skills se cada subitem virar skill própria; canalizar em 3-4 skills temáticas é o sweet spot.

**Esforço:** Alto (3-5 skills novas).

---

### 8. `skills/testing/` tem 2 skills, faltam padrões avançados

**Fingerprint:** `skill-testing-thin-coverage`

**Evidência:** `test-pyramid` + `test-strategy`. Faltam:

- `testing/contract-testing/` — Pact, consumer-driven contracts
- `testing/mutation-testing/` — Stryker, mutmut
- `testing/snapshot-testing/` — bem usado vs anti-pattern
- `testing/visual-regression/` — Percy, Chromatic, Playwright snapshots

Os agentes `backend-test-specialist` e `frontend-test-specialist` são modelo Sonnet com 162 e 263 linhas respectivamente — eles **escolhem** estratégias de teste, mas escolhem com material de apoio limitado.

**Impacto positivo:** `frontend-test-specialist` ganha capacidade de propor visual regression em projetos com design system maduro; `backend-test-specialist` ganha contract testing em arquiteturas microsserviços.

**Impacto negativo:** dilui o agente em tópicos que nem todo projeto precisa.

**Esforço:** Alto (4 skills novas — implementar 2 ainda agrega valor).

---

### 9. Falta skill de git workflow strategy

**Fingerprint:** `skill-missing-git-workflow`

**Evidência:** Trunk-based development, gitflow, GitHub flow, GitLab flow — decisões de fluxo de branch são tomadas no início do projeto (`software-architect` ou `devops-specialist`). Hoje, sem skill, decisão é "o que o time conhece". `skills/shared/conventional-commits/` cobre formato de mensagem mas não estratégia de branching.

**Impacto positivo:** skill apresenta trade-offs (CI maturity, hotfix handling, release cadence). Útil em `inherited-project.md` (audit de fluxo herdado) e em `setup-assistant`.

**Impacto negativo:** baixo — material é razoavelmente estável.

**Esforço:** Médio (1 skill, ~120 linhas).

---

### 10. Padrão `When loaded` adotado por apenas 1 agente

**Fingerprint:** `agent-when-loaded-pattern-only-qa`

**Evidência:** Grep `When loaded` em `agents/*.md` retorna 1 match (em `qa-specialist.md`). O resto dos agentes carrega skills incondicionalmente no Foundational Rule. Para skills "condicionais" (ex.: `sonarqube` só se houver `sonar-project.properties`), o pattern atual é prosa: "load `skills/devops/sonarqube/` if `SONAR_TOKEN` is present".

Padronizar como "When loaded:" / "Trigger:" + "Load:" tornaria as condicionais explícitas, parseable e auditáveis. Isso também é pré-requisito para um futuro validador automático que verifique qual skill é potencialmente carregada por cada agente.

**Impacto positivo:** tooling futuro (orphan-skill-scan v2, validator de frontmatter) pode parsear cabeçalhos. Reduz prosa repetida.

**Impacto negativo:** padronização exige editar 14+ agentes (1x); risco de divergência durante a migração.

**Esforço:** Médio.

---

## Lista Priorizada

| Prioridade | Sugestão | Esforço | Impacto |
|------------|----------|---------|---------|
| P1 | Extrair `skills/shared/reviewer-base/SKILL.md` (~120 linhas economizadas nos 3 reviewers) | Médio | Alto |
| P1 | Criar 3-4 skills de `security/` (owasp + secret-mgmt + sast + dependency) | Alto | Alto (alinha com modelo Opus do agent) |
| P2 | Skill `architecture/caching/` | Médio | Médio |
| P2 | Skill `architecture/resilience/` | Médio | Médio |
| P2 | Skill `database/migration-zero-downtime/` | Médio | Médio |
| P2 | Skill `testing/contract-testing/` | Médio | Médio |
| P3 | Skill `architecture/i18n/` | Médio | Médio (depende de público) |
| P3 | Skill `architecture/monorepo-patterns/` | Médio | Médio |
| P3 | Skill `shared/git-workflow/` | Médio | Médio |
| P3 | Skill `testing/visual-regression/` | Médio | Baixo (uso situacional) |
| P3 | Padronizar bloco `When loaded` em todos os agentes | Médio | Médio (preventivo) |

---

## Próxima passada

Ângulos ainda não cobertos: critério para promover uma skill de `integrations/` para `architecture/` quando ela vira pattern transversal; cobertura de testing em monolitos vs microsserviços; fronteira entre `database-specialist` e skills de `database-*` em `integrations/`.
