# Eixo A — Agnosticismo de stack (2026-09-11)

**Data:** 2026-09-11 · **Baseline:** `HEAD` = `9530551` · **Varredura:** integral sobre
`agents/` (18 arquivos) e `commands/` (35 arquivos)

---

## Resultado

> **Nenhum achado original neste eixo.**

**Contagem: 124 candidatos → 0 violações originais.**

A varredura semente obrigatória rodou integralmente antes de qualquer leitura:

```bash
rg -in 'laravel|symfony|django|rails|spring|express|nest|next\.js|react|vue|angular|svelte|\
tailwind|bootstrap|eloquent|prisma|hibernate|sequelize|typeorm|phpunit|jest|vitest|pytest|\
rspec|composer|npm|yarn|pnpm|pip|maven|gradle|docker|kubernetes|terraform|aws|gcp|azure|\
mysql|postgres|mongodb|redis|php|python|ruby|golang|typescript|javascript' agents/ commands/
```

124 linhas com hit, distribuídas em 25 arquivos. Nenhuma sobreviveu às portas.

---

## Por que os 124 caíram

| Classe de descarte | Linhas | Detalhe |
|---|---:|---|
| **Falso positivo do regex** (termo embutido em palavra maior) | **25** | `pip`×13 (em *pipeline*, *pipe*), `express`×3 (*expressible*, *express* verbo), `rspec`×2 (em *perspective*), `react`×2 (*reactivation*), `postgres`×2, `docker`×2, `aws`×2, `php`×1, `golang`×1, `nest`×1 (*nested*) — em cada uma dessas linhas **toda** ocorrência está colada a caracteres alfabéticos nos dois lados |
| **Tabela de detecção / roteamento de skill** (exceção explícita da regra) | ~48 | `backend-developer.md:79,83,84` · `ui-ux-designer.md:57-59` · `product-analyst.md:179` · `devops-specialist.md` (tabelas de plataforma) · `mobile-developer.md` (tabela de stacks) · `database-specialist.md` (tabela de engines) |
| **Bloco rotulado `Example` / comentário de exemplo** | ~9 | `code-reviewer.md:79` — `# Examples: npm run lint, composer phpcs, ruff check ., rubocop` · `adr.md:12` — `e.g.: /devteam:adr Adopt PostgreSQL as primary database` |
| **Skill de referência específica por design** (`skills/devops/*`, `ui-libraries/*`, `integrations/*`, `legacy/*`, `mobile/*` citadas por nome) | ~17 | citações de caminho de skill não são acoplamento do corpo do agente |
| **Uso agnóstico explícito** | ~3 | `explain.md:48` — *"a fenced block in the project's actual language and framework, detected from the repo — **never defaulting to JavaScript**"* — é a regra de agnosticismo, não a violação dela |
| **Porta 5 — já registrado e aberto no banco** | **22** | ver tabela abaixo |

### Os 22 candidatos genuínos que já estão no banco (Porta 5)

Todos são achados legítimos de acoplamento de stack sob seção de comportamento. Nenhum é
descoberta deste pass: todos constam do `_index.md` **sem marcador** (conjunto aberto), e a Porta 5
do Protocolo Anti-Duplicação existe exatamente para impedir que a repetição de um sintoma
registrado e não implementado seja contada como achado.

`frontend-developer.md:3` (oito frameworks na frontmatter) · `frontend-developer.md:91,96`
(`React useState`, TanStack Query/SWR sob `## Server State & Data Fetching`) ·
`frontend-developer.md:72` (skill jQuery) · `frontend-developer.md:134-139` (seção Security:
`dangerouslySetInnerHTML`/`v-html`, `VITE_*`/`NEXT_PUBLIC_*`) ·
`frontend-test-specialist.md:141-153` (SonarQube) · `database-specialist.md:66-73` (engines na
frontmatter) · `database-specialist.md:84` (RLS como neutro) · `database-specialist.md:133`
(Supabase CLI) · `devops-specialist.md:46-56` (Docker como primário) ·
`devops-specialist.md:137-148` (checklist Docker/Terraform) · `security-specialist.md:80-85`
(vocabulário CI/CD só GitHub Actions) · `security-specialist.md` § Tooling SAST ·
`backend-reviewer.md:30` (configs de linter) · `frontend-reviewer.md:112,114` ·
`mobile-developer.md:159` (checklist com 2 de 5 frameworks) ·
`mobile-developer.md` description (cinco stacks na superfície de identidade) ·
`setup-assistant.md:146-147` · `commit.md:125-133` · `audit.md:54,126,128` (Docker/Redis/CDN) ·
`relayout.md:32` (Storybook/Tailwind) · `mobile.md:19,26,27` (stacks) · `devops.md:2,14`.

---

## Um candidato examinado a fundo e descartado

`agents/product-analyst.md:146-153`, sob o heading `### Design for Parallel Execution (mandatory)`
— uma seção de comportamento, portanto elegível:

> `4. **Gate isolated infra on Docker.** State the isolation model explicitly: worktree-per-task
> always; **isolated Docker stack per worktree only when the project uses Docker** (a compose file
> exists). […] Detect quickly:
> \`ls docker-compose.yml docker-compose.yaml compose.yml compose.yaml 2>/dev/null | head -1\``

**Por que não é violação de agnosticismo:** o bloco *já* é um gate condicional — nomeia Docker para
declarar que a isolação de infra só se aplica quando o projeto usa Docker, e instrui explicitamente
o contrário ("If the project has no Docker, the plan must say parallelism is achieved by worktree
alone — do not imply isolated infra"). Não prescreve Docker; condiciona-o. E o `CLAUDE.md` §
*Canonical worktree decision cascade* nomeia Docker no mesmo papel.

**O que sobra é um problema de outra natureza** — o bloco restata mecânica que ele próprio manda
não restatar duas linhas abaixo (`Reference (do not restate the mechanics)`). Confrontado com
`token-worktree-isolation-block-7-lines-x-8-agents` (✅ Executed) pela **Porta 3**: alvo diferente
(`product-analyst` não está entre os nove agentes com `## Worktree Isolation`), mas causa raiz
(cascata de worktree restatada em corpo de agente) e remediação (delegar à skill) coincidem —
**2 de 3 ⇒ duplicata. Descartado.**

---

## Observação metodológica (não é achado)

**A varredura semente tem 20% de ruído estrutural.** 25 das 124 linhas (**20,2%**) casam apenas por
substring dentro de palavra maior — `pip` dentro de *pipeline* responde sozinho por 13. O regex do
prompt não usa fronteira de palavra (`\b`). Isso não corrompe o resultado (a triagem manual pega
todas), mas infla o denominador `N` que todo pass reporta, e o custo de leitura de 25 linhas
irrelevantes recai sobre cada execução.

Isso **não** é registrado como fingerprint: o alvo é `docs/reports/_prompt-auditoria.md:143-146`, e
a família de achados sobre defeitos desse arquivo já tem três entradas abertas
(`flow-prompt-auditoria-commit-step-contradicts-branch-rule`,
`flow-prompt-auditoria-interactive-plan-gate-unsatisfiable-in-unattended-run`,
`gov-audit-pass-output-uncommitted-with-no-detection-mechanism`). Fica registrado aqui como nota
para quem for editar o prompt: envolver os termos em `\b(...)\b` corta ~20% do trabalho de triagem
de cada pass, ao custo de perder hits legítimos em identificadores compostos (`docker-compose`,
`next.js` já escapado) — o que se resolve mantendo esses casos fora do grupo com fronteira.
