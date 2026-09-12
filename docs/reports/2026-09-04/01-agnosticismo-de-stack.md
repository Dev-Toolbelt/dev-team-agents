# Eixo A — Agnosticismo de stack (2026-09-04)

**Data:** 2026-09-04 · **Baseline:** `HEAD` = `a67cac9` · **Varredura:** integral sobre `agents/` e `commands/`

---

## Apuração

**124 candidatos → 0 violações originais.**

A varredura semente obrigatória rodou integralmente:

```bash
rg -in 'laravel|symfony|django|rails|spring|express|nest|next\.js|react|vue|angular|svelte|\
tailwind|bootstrap|eloquent|prisma|hibernate|sequelize|typeorm|phpunit|jest|vitest|pytest|\
rspec|composer|npm|yarn|pnpm|pip|maven|gradle|docker|kubernetes|terraform|aws|gcp|azure|\
mysql|postgres|mongodb|redis|php|python|ruby|golang|typescript|javascript' agents/ commands/
```

124 hits, distribuídos em 25 arquivos:

| Arquivo | Hits | Arquivo | Hits |
|---|---:|---|---:|
| `agents/devops-specialist.md` | 23 | `agents/setup-assistant.md` | 5 |
| `agents/mobile-developer.md` | 12 | `agents/backend-developer.md` | 5 |
| `agents/database-specialist.md` | 12 | `commands/relayout.md` | 3 |
| `agents/security-specialist.md` | 8 | `commands/explain.md` | 3 |
| `agents/product-analyst.md` | 8 | `commands/audit.md` | 3 |
| `agents/frontend-test-specialist.md` | 8 | `agents/ui-ux-designer.md` | 3 |
| `agents/frontend-developer.md` | 8 | `agents/backend-reviewer.md` | 3 |
| `commands/commit.md` | 5 | outros 10 arquivos | ≤ 2 cada |

---

## Por que os 124 caem

### Grupo 1 — falsos positivos do regex (substring dentro de palavra comum)

Verificados extraindo o texto casado com `rg -io`:

| Arquivo | Substring casada | Palavra real | Termo |
|---|---|---|---|
| `agents/qa-specialist.md:3,9` | `rspec` | pe**rspec**tive | RSpec |
| `agents/software-architect.md:89` | `react` | Auto-**react**ivation | React |
| `commands/rule.md:27` | `express` | not **express**ible as a regex | Express |

Três hits, zero conteúdo de stack. Nenhum é candidato.

### Grupo 2 — tabelas de detecção (exceção por design)

O maior bloco. Uma tabela de detecção **precisa** nomear a tecnologia que detecta; é o mecanismo que
torna o agente agnóstico, não o que o acopla. Exemplos verificados:

- `agents/ui-ux-designer.md:57-59` — tabela mapeando `.xcodeproj`/Swift → `ios-hig`, `build.gradle`/Kotlin → `material-design`, React Native/Expo/Flutter → ambos.
- `agents/frontend-developer.md:72,84,85` — tabela com jQuery → `skills/legacy/jquery`, TanStack Query e SWR → regras abaixo.
- `agents/devops-specialist.md:81` — linha de detecção do SonarQube.

Descartados conforme a regra do eixo.

### Grupo 3 — blocos rotulados "Example" / "Reference"

- `agents/code-reviewer.md:79` — `# Examples: npm run lint, composer phpcs, ruff check ., rubocop`. Comentário dentro de um bloco de exemplo, e deliberadamente plural em quatro ecossistemas — o oposto de prescrever um.
- `commands/adr.md:12` — `"Please provide the ADR title, e.g.: /devteam:adr Adopt PostgreSQL as primary database"`. Texto de exemplo em uma mensagem de erro.

### Grupo 4 — referência a um recurso real do harness, não a uma stack do projeto

- `commands/merge.md:52,57` — "isolated **Docker** infra" / "teardown worktree + isolated **Docker** stack". O isolamento Docker por worktree é uma funcionalidade do próprio `dev-team-agents`, documentada em `skills/shared/worktree/references/docker-isolation.md`. Nomear a ferramenta que o harness usa não acopla o agente à stack do projeto auditado.
- `commands/health-check.md:50` — "12. Python Prerequisite", nome de uma das treze categorias de check. O pré-requisito é do instalador, não do projeto.

### Grupo 5 — o hit é uma cláusula anti-acoplamento

- `commands/explain.md:48` — "a fenced block in the project's actual language and framework, detected from the repo — **never defaulting to JavaScript**." O termo aparece para ser proibido. Contá-lo como violação inverteria o sentido da regra.

### Grupo 6 — candidatos genuínos, já no conjunto aberto (Porta 5)

Os candidatos que **são** acoplamento sob seção de comportamento já estão registrados e não
implementados. Reapresentá-los é ruído, não descoberta. Os passes de 2026-08-21 e 2026-08-28 os
descartaram pela mesma porta, e a árvore não mudou um byte desde então
(`git diff --stat a67cac9..HEAD` vazio):

`frontend-developer.md:3` (frameworks na frontmatter) · `frontend-developer.md:91,96` (data
fetching — reconfirmado 🟡 na Fase 1 deste pass) · `frontend-test-specialist.md:141-153`
(SonarQube) · `database-specialist.md:84` (RLS) · `database-specialist.md:133` (Supabase CLI) ·
`devops-specialist.md:137-148` (checklist Docker/Terraform) · `security-specialist.md:80-85`
(CI/CD) · `backend-reviewer.md:30` (configs de linter) · `mobile-developer.md:159` (checklist com
2 de 5 frameworks) · `audit.md:54,126,128` (Docker/Redis/CDN) · `relayout.md:32`
(Storybook/Tailwind) · `mobile.md:19,26,27` (stacks — reconfirmado na Fase 1b deste pass) ·
`setup-assistant.md:146-147` · `commit.md:125-133` · `devops.md:2,14`.

---

## Conclusão

**Nenhum achado original neste eixo.**

Isso não é ausência de acoplamento — é a consequência aritmética de auditar integralmente uma árvore
idêntica, pela terceira vez, com um banco que já registrou o acoplamento existente. O Eixo A é
sempre integral por regra, e a varredura rodou; o que ela devolveu foi a confirmação de que o
conjunto de violações não se moveu porque o código não se moveu.

O sinal útil aqui é sobre o **backlog**, não sobre a varredura: quinze candidatos genuínos estão
abertos há entre catorze e trinta e seis dias, e nenhum foi endereçado. O gargalo do agnosticismo
neste repositório não é mais a detecção.
