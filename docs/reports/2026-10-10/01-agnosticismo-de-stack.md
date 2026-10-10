# Eixo A — Agnosticismo de Stack — 2026-10-10

**Baseline:** `HEAD` = `349f18c` · varredura **integral** de `agents/` e `commands/`.

## Resultado

**124 linhas de hit → 23 candidatos → 0 violações originais.**

**Nenhum achado original neste eixo** — o terceiro pass consecutivo com esse resultado
(2026-09-11, 2026-10-02, hoje).

## Varredura semente

```
rg -in 'laravel|symfony|django|rails|spring|express|nest|next\.js|react|vue|angular|svelte|
tailwind|bootstrap|eloquent|prisma|hibernate|sequelize|typeorm|phpunit|jest|vitest|pytest|
rspec|composer|npm|yarn|pnpm|pip|maven|gradle|docker|kubernetes|terraform|aws|gcp|azure|
mysql|postgres|mongodb|redis|php|python|ruby|golang|typescript|javascript' agents/ commands/
```

124 linhas. O delta de código tocou 5 arquivos em `agents/` (`backend-developer`,
`devops-specialist`, `security-specialist`, `seo-specialist`, `setup-assistant`) e 5 em
`commands/` (`audit`, `commit`, `learn`, `seo`, `setup`) — todos varridos, nenhum introduziu
acoplamento novo sob seção de comportamento.

## Por que os 23 candidatos caíram

### Descartados pela regra do próprio eixo — 9

Hits sob "Example", tabela de detecção ou lista de skills condicionais não são violações:

- `agents/mobile-developer.md:55-75,138-150` — tabelas de detecção (`package.json` contém
  `react-native`, `android/` existe, `.detoxrc.js`) e a tabela E2E. Detecção, não comportamento.
- `agents/ui-ux-designer.md:57-59` — tabela de detecção de plataforma → `ios-hig` /
  `material-design`.
- `agents/database-specialist.md:55,59,65-72` — tabela de detecção por engine (`postgres:`,
  `mysql2`, `mongoose`, `ioredis`) → skill correspondente.
- `agents/devops-specialist.md:70-79` — tabela de detecção de arquivo → skill de CI/cloud.
- `agents/backend-developer.md:78,82,83,85` — tabela de detecção → skill de integração.
- `agents/security-specialist.md:48,146,148` — idem.
- `agents/code-reviewer.md:79` — literalmente `# Examples: npm run lint, composer phpcs, ruff check ., rubocop`.
- `commands/adr.md:12` — `e.g.: /devteam:adr Adopt PostgreSQL as primary…`, exemplo de título.
- `agents/backend-developer.md:87` — delega a detecção de SonarQube/Docker ao `project-context`;
  é o oposto de prescrever.

### Ruído do próprio regex — 4

`react` casa dentro de `reactive`, `Auto-reactivation` e `reactivação`; `aws` e `nest` casam dentro
de palavras comuns. `agents/software-architect.md:89` ("Auto-reactivation"),
`agents/frontend-developer.md:146` ("reactive state"), `agents/qa-specialist.md:3,9` e
`agents/product-analyst.md:94` são falsos positivos léxicos.

> **O relatório anterior já registrou isto e a recomendação segue válida:** ancorar os termos
> curtos com `\b` (`\bnest\b`, `\bexpress\b`, `\brails\b`, `\bspring\b`, `\breact\b`) corta a razão
> de ruído de 5:1 sem perder cobertura. Não está no banco como achado porque é uma melhoria do
> instrumento de auditoria, não do repositório — mas quem rodar o próximo pass economiza uma hora.

### Porta 5 (estado — já no conjunto aberto) — 6

- `agents/frontend-developer.md:3,90,95` → `agent-frontend-developer-body-92-102-data-fetching-…`
  e o item da frontmatter.
- `agents/frontend-reviewer.md:112,114` (TypeScript/PropTypes/`React.ChangeEvent` sob
  § Type Safety) → `agent-frontend-reviewer-body-type-safety-and-code-quality-hardcodes-react-ts-identifiers-proptypes-react-changeevent-hocs`.
- `agents/frontend-test-specialist.md:141-153` (LCOV/Jest/Vitest/`sonar.javascript`) →
  `agent-frontend-test-specialist-sonarqube-coverage-block-hardcodes-jest-vitest-commands-…`.
- `agents/devops-specialist.md:46-56` ("**Primary**: Docker") e `:138-149` (checklist
  Docker/Terraform) →
  `agent-devops-specialist-core-expertise-declares-primary-docker-and-done-checklist-gates-on-docker-terraform-…`.
- `agents/database-specialist.md:83` (RLS como default) e `:132` (Supabase CLI) → dois
  fingerprints abertos.
- `commands/audit.md:56,128,130`, `commands/relayout.md:32`, `commands/mobile.md:19,26`,
  `commands/devops.md:2,14`, `agents/setup-assistant.md:146-147`, `commands/commit.md:131,134`,
  `agents/seo-specialist.md:27` → todos no conjunto aberto.

### Porta 3 (semântica) — 4

- `agents/security-specialist.md:28-29` — o passo de leitura inicial fixa `Dockerfile`,
  `docker-compose.yml`, `.github/workflows/*.yml` com `.gitlab-ci.yml`/`bitbucket-pipelines.yml`
  entre parênteses. Contra
  `agent-security-specialist-cicd-checklist-github-actions-only-vocabulary` (aberto): mesmo
  arquivo, mesma causa raiz (vocabulário GitHub-Actions-first), mesma remediação (nomear o
  artefato de CI genericamente). 3 de 3 → duplicata.
- `agents/product-analyst.md:132,146-153` — "Gate isolated infra on Docker" com o probe
  `ls docker-compose.yml …` inline. Já descartado em pass anterior pela mesma porta
  (`product-analyst.md:128-153` restatando a cascata); o *gate* condicional é a forma agnóstica
  correta, e o que sobra é a cascata duplicada, que é outro fingerprint.
- `agents/backend-reviewer.md:30` (configs de linter por ecossistema) →
  `agent-reviewer-linter-config-three-divergent-ecosystem-incomplete-copies`.
- `agents/backend-reviewer.md:170` (`file.php:88` no template de output) — sob § Output Format,
  exemplo de formato; mesma família do item acima.

## Leitura do eixo

Três passes seguidos sem achado original em `agents/`/`commands/` não significam que o eixo está
limpo: significa que **os 10 acoplamentos genuínos já estão registrados e nenhum foi executado**.
O eixo não tem mais o que descobrir aqui — tem o que executar. A varredura seguinte renderá mais
se for estendida a `skills/shared/` (comportamental, fora das categorias de exceção por design),
que nunca passou por varredura integral neste eixo.
