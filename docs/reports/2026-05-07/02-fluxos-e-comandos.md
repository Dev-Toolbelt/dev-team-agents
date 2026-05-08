# 2. Fluxos e Comandos (Phase Gates, Paralelismo, Spawn Condicional)

← [Voltar ao índice](index.md)

Esta seção investiga os **fluxos não cobertos em 2026-05-06**: comandos individualmente, checkpoints implícitos em workflows, decisões de spawn condicional vs incondicional, e critérios de saída em loops de iteração.

---

## 2.1 `commands/fix.md` declara fases sem usar a coluna `Par.`

`fix.md` (linhas 13–19) descreve duas fases:

```text
Phase 1 — spawn based on where the bug lives (in parallel if both apply):
- backend-developer ...
- frontend-developer ...

Phase 2 — spawn after Phase 1 completes:
- backend-test-specialist ...
- frontend-test-specialist ...
```

O `templates/plan-template.md` define a coluna `Par.` (`A`, `B`, `—`) exatamente para isso, mas **nenhum comando** em `commands/*.md` adota esse padrão. A passada anterior cobriu apenas os **workflows**; os **comandos** ficaram de fora.

> **Fingerprint:** `flow-commands-par-column-missing`

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Usuário vê em formato consistente (A/A/—/B/B) qual paralelismo o comando dispara |
| **Positivo** | Quando o usuário copia o prompt para outro tooling (ex.: agente externo), o paralelismo fica explícito |
| **Negativo** | Adiciona ~5 linhas de tabela por comando × 22 comandos ≈ 110 linhas |
| **Negativo** | Dois comandos usam fluxo trivial (`docs.md`, `qa.md` chamam um agente único) — adicionar tabela seria overkill |

**Recomendação:** adotar a tabela `Par.` apenas em comandos com **2+ agentes**: `plan.md`, `fix.md`, `backend.md`, `frontend.md`, `fullstack.md`, `review.md`, `refactor.md`, `pr.md` (8 comandos). Os outros 14 podem ficar como estão.

---

## 2.2 `database-specialist` é spawn **incondicional** em `/devteam:plan`

Em `commands/plan.md` (linhas 13–16):

```text
Always spawn (in parallel):
- software-architect ...
- product-analyst ...
- database-specialist ...     ← incondicional
```

Mas `backend-developer`, `frontend-developer` e `devops-specialist` são **condicionais** (linhas 18–25). Para um plano de feature **puramente UI** (ex.: redesenho de uma página estática), o `database-specialist` é desnecessário e custa tokens + tempo de execução.

A própria tabela do `CLAUDE.md` (linha 75 da seção de Commands) marca o `database-specialist` com `¹ conditional`:

| Command | Agents invoked |
|---------|---------------|
| `/devteam:plan` | software-architect + product-analyst + database-specialist + backend¹ + frontend¹ + devops¹ |

Mas **não marca** o database como condicional, ao contrário de backend/frontend/devops. **O comando contradiz seu próprio CLAUDE.md** — ou o `database-specialist` deveria ser condicional como os outros, ou os outros deveriam ser incondicionais como o database.

> **Fingerprint:** `flow-plan-database-conditional`

**Recomendação:** mover o `database-specialist` para a seção condicional do `plan.md` com critério explícito:

```text
Also spawn if the task involves data modeling, schema, or database:
- database-specialist at .claude/agents/dev-team/database-specialist.md
```

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Reduz custo de planos UI-only em ~25% (menos um agente Sonnet) |
| **Positivo** | Coerência interna: regras de spawn condicional uniformes |
| **Negativo** | Pequeno risco: planos com requisito de schema implícito não-detectado pelo critério |

---

## 2.3 Critério de "envolve banco / envolve UI" não está definido em lugar nenhum

`plan.md`, `fix.md`, `backend.md`, `frontend.md` usam frases como:

- "spawn if the task involves database changes"
- "spawn if the bug is in client-side code"
- "spawn if the task involves backend code or server-side changes"

**Quem decide se "involves database changes"?** O agente principal lendo `$ARGUMENTS`? O usuário? Em comandos atuais, não há prompt de classificação — fica implícito.

> **Fingerprint:** `flow-conditional-spawn-criteria-undefined`

**Recomendação:** adicionar uma seção comum (ou skill `skills/shared/spawn-classifier/SKILL.md`) que liste **gatilhos textuais ou de path** que definam o que conta como backend, frontend, database, devops. Exemplo:

```markdown
## Trigger heuristics
- "database": menciona schema/migration/SQL OR `$ARGUMENTS` contém path em `migrations/`, `prisma/`, `db/`
- "frontend": menciona UI/UX/page/component OR `$ARGUMENTS` contém path em `src/components/`, `pages/`, `templates/`
- "backend": menciona API/endpoint/service OR `$ARGUMENTS` contém path em `src/api/`, `controllers/`, `routes/`
- "devops": menciona deploy/CI/Docker/infra OR `$ARGUMENTS` contém path em `.github/`, `Dockerfile`, `terraform/`
```

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Decisão de spawn fica determinística e auditável |
| **Positivo** | Permite um teste de regressão automático (dado um prompt, quais agentes spawnam) |
| **Negativo** | Falsos positivos quando o `$ARGUMENTS` é abstrato ("melhore a performance") sem pista de path |

---

## 2.4 `inherited-project.md` não tem checkpoint formal entre fases paralelas

`workflows/inherited-project.md` (Phase 1 AUDIT, linhas 15–27) spawn 3 agentes em paralelo (software-architect, database-specialist, security-specialist). **Não há linha explícita** dizendo "wait for all 3 reports before Phase 2".

A Phase 2 (linhas 30+) começa com "Once the audit reports are in…" — frase em prosa, não estruturada. Em workflows multi-agente longos, a falta desse checkpoint formal pode levar o usuário (ou um agente orquestrador) a iniciar Phase 2 antes de ter os 3 reports.

> **Fingerprint:** `flow-inherited-no-explicit-await-checkpoint`

**Recomendação:** introduzir um marcador padrão `▶ CHECKPOINT — await: <agent-list>` no formato canônico de workflows. Exemplo:

```text
Phase 1 — AUDIT (parallel):
| Par. | Step                                  | Agent                |
|------|---------------------------------------|----------------------|
| A    | Read codebase, classify components    | software-architect   |
| A    | Map data layer                        | database-specialist  |
| A    | Identify CVEs and OWASP risks         | security-specialist  |

▶ CHECKPOINT — await all Phase 1 reports before continuing.

Phase 2 — STABILIZATION (...)
```

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Elimina ambiguidade temporal em workflows de múltiplos passos |
| **Positivo** | Possibilita validação programática (um futuro `workflow-lint.sh` poderia exigir CHECKPOINT entre fases) |
| **Negativo** | Mais sintaxe a memorizar; mitigável com 2 linhas de comentário no `plan-template.md` |

---

## 2.5 `workflows/inherited-project.md` tem loop sem critério de saída

Linhas 50–61 (Phase 3, descoberta) descrevem:

```text
Repeat until scope is 100% closed.
```

**Quantas iterações são "razoáveis"?** Sem teto, um projeto herdado complexo pode rodar 8–10 ciclos com diminishing returns. O `discovery-mode/SKILL.md` menciona padrões de descoberta mas também não fixa teto.

> **Fingerprint:** `flow-discovery-loop-exit-criteria`

**Recomendação:** definir convenção:

> O loop de descoberta termina quando: (a) o `product-analyst` reporta confidence ≥ 90% **ou** (b) 5 iterações foram executadas (o que vier primeiro). No segundo caso, registrar as zonas cinzas no `session-summary.md` para próximo ciclo.

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Evita loops infinitos em projetos com requisitos genuinamente vagos |
| **Negativo** | Forçar saída pode mascarar requisitos críticos não descobertos; mitigado pelo escape-hatch para session-summary |

---

## 2.6 Resumo de fingerprints novos

| Fingerprint | Tema |
|-------------|------|
| `flow-commands-par-column-missing` | Comandos não usam coluna `Par.` do plan-template |
| `flow-plan-database-conditional` | `database-specialist` incondicional em `/devteam:plan` |
| `flow-conditional-spawn-criteria-undefined` | Falta heurística para decidir spawn condicional |
| `flow-inherited-no-explicit-await-checkpoint` | Workflow herdado sem checkpoint formal entre fases paralelas |
| `flow-discovery-loop-exit-criteria` | Loop de descoberta sem critério explícito de saída |
