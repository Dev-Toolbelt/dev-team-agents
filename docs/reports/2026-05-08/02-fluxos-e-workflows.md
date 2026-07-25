# 2. Fluxos e Workflows (ADR, Session-Summary, Comando × Doc, Numeração de Fases)

← [Voltar ao índice](index.md)

Esta seção mergulha nos arquivos `workflows/*.md` em busca de **lacunas estruturais**: políticas globais que existem no `CLAUDE.md` mas que os workflows não reforçam; comandos que prometem uma coisa enquanto a documentação descreve outra; e fases sem numeração coerente. Os achados aqui complementam — mas não repetem — os fingerprints `flow-*` já registrados nos relatórios anteriores.

---

## 2.1 Nenhum workflow menciona criação de ADR

`CLAUDE.md § Agent Memory System` declara como regra global:

> Write an ADR when a decision is hard to reverse, affects multiple components, or has non-obvious reasoning. **Create an ADR by running `bash .dev-team-agents/scripts/new-adr.sh "title"`**.

Apesar disso, executando `grep -i "adr\|architecture decision record" workflows/*.md` retorna **zero resultados**. Os 5 workflows (`new-project`, `inherited-project`, `maintenance`, `bug-fix`, `security-patch`) descrevem dezenas de momentos onde uma decisão arquitetural é tomada (Phase 1.2 do `new-project`, Phase 3 do `inherited-project`, Step 1 do `bug-fix`), mas **nunca instruem o agente a parar e considerar um ADR**.

Pior: o `new-adr.sh` existe, está em `scripts/`, e funciona — mas o usuário só descobre lendo o `CLAUDE.md`. Se ele estiver seguindo `workflows/new-project.md` linearmente, **nunca verá a referência**.

> **Fingerprint:** `flow-workflows-no-adr-trigger`

| Impacto | Detalhe |
|---------|---------|
| **Positivo (corrigir)** | Decisões arquiteturais relevantes passam a ser documentadas no momento certo |
| **Positivo (corrigir)** | O `new-adr.sh` deixa de ser uma feature invisível |
| **Negativo** | Adiciona ~5 linhas em cada workflow; risco de virar checkbox vazio se o gatilho for vago |

**Recomendação:** adicionar, em `new-project.md` Phase 1.2 e em `inherited-project.md` Phase 3, um sub-passo:

> 📝 **ADR check**: ao final desta fase, o `software-architect` deve listar as decisões tomadas e, para cada uma que satisfaça o gatilho da seção `## ADR Trigger Rule` do `CLAUDE.md`, registrar via `bash .dev-team-agents/scripts/new-adr.sh "title"`.

Em `bug-fix.md` Step 1 e `security-patch.md` Step 1, mencionar que **diagnoses não-óbvias devem virar ADR** se o root-cause revelar um buraco de design.

---

## 2.2 Nenhum workflow menciona Session Summary

A `CLAUDE.md § Session Summary Rule` define que **toda sessão que cria ou modifica arquivos** precisa de uma entrada em `.dev-team-agents/user-data/session-summary.md`. Mas:

```
$ grep -i "session.summary\|session summary" workflows/*.md
(zero results)
```

O hook `01-session-summary.sh` cobre o caso "sessão termina com mudanças sem entrada do dia" — mas essa rede de proteção é reativa. Os workflows são o lugar **proativo** onde o desenvolvedor lê o que precisa fazer, e ali a regra de session-summary não aparece.

A consequência prática: sessões longas que envolvem 3 ou 4 agentes terminam com várias mudanças e zero contexto sobre quem decidiu o quê — exatamente o problema que o session-summary deveria resolver.

> **Fingerprint:** `flow-workflows-no-session-summary-step`

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | A rede de proteção do hook é menos exercitada (menos "exit 2" reactivo) |
| **Positivo** | Próxima sessão começa com contexto explícito do que foi feito |
| **Negativo** | Cada workflow ganha 3–6 linhas no fim; baixíssimo, mas não-zero |

**Recomendação:** adicionar, em cada workflow, uma seção final padronizada `## Workflow Closure`:

```markdown
## Workflow Closure

Antes de fechar a sessão:
1. Cada agente que tocou em arquivos **anexa** sua contribuição em `.dev-team-agents/user-data/session-summary.md` no formato multi-agent (ver `CLAUDE.md § Session Summary Rule`).
2. Se houve commits hoje, garantir que existe entrada do dia (`## YYYY-MM-DD HH:MM:SS | <título>`).
```

Isso sincroniza o workflow com o hook em vez de só o hook fazer o trabalho de detecção.

---

## 2.3 `workflows/bug-fix.md` × `commands/fix.md`: documentação e comando discordam sobre `software-architect`

`workflows/bug-fix.md` Step 1 (linhas 9–20) é **inequívoco**:

> **Step 1: Diagnosis** — `As the software-architect, load the project context and identify the root cause.` Do not jump to fixing before the root cause is confirmed.

Já `commands/fix.md` (slash command `/devteam:fix`, linhas 13–19) **não invoca o `software-architect` em nenhuma fase**:

```
Phase 1 — spawn based on where the bug lives:
- backend-developer
- frontend-developer
Phase 2 — spawn after Phase 1:
- backend-test-specialist
- frontend-test-specialist
```

Ou seja, a doc diz "diagnostique antes de corrigir"; o comando pula direto pra corrigir. Isso significa que o usuário tem **dois caminhos divergentes**:

| Caminho | Comportamento real |
|---------|--------------------|
| Lê `workflows/bug-fix.md` e copia/cola prompts | software-architect → developer → qa+code-reviewer paralelos → test specialist |
| Roda `/devteam:fix` | developer → test specialist (sem diagnose, sem QA, sem review) |

A regra "Fix the root cause, not the symptom" — destaque do workflow — é estruturalmente desativada quando o usuário pega o atalho do slash command.

> **Fingerprint:** `flow-bugfix-doc-vs-command-mismatch`

| Impacto | Detalhe |
|---------|---------|
| **Positivo (alinhar)** | O comando passa a entregar o que a documentação promete |
| **Positivo (alinhar)** | Bugs ganham análise antes de patch (que é exatamente a regra de ouro do workflow) |
| **Negativo** | `/devteam:fix` fica mais pesado (4 agentes em vez de 1–2); usuário pode preferir o atalho |

**Recomendação:** uma das duas opções:

1. **Alinhar** `commands/fix.md` para ter `Phase 0: software-architect (diagnose)` antes da Phase 1 (correção), seguido por uma Phase 3 com `qa-specialist + code-reviewer` em paralelo (igual ao workflow).
2. **Documentar a divergência** em `commands/fix.md` com um aviso no topo: "este comando assume que o root-cause já está identificado. Para diagnose+fix completo, siga `workflows/bug-fix.md` ou rode `/devteam:plan` antes."

A opção (1) é mais consistente; a (2) preserva o uso "rápido" do atalho.

---

## 2.4 `workflows/maintenance.md` tem fases inconsistentes (Step 1 → Step 2 → Phase 2)

A estrutura do `maintenance.md`:

```
## How to Start a Task
  ### Step 1: Task Pickup
  ### Step 2: Scope Validation (product-analyst — optional but recommended)
## Phase 2: DEVELOPMENT
## Phase 3: QUALITY GATE (Regression Priority)
## PR and Deploy
## Coexistence in Maintenance Projects
```

Onde está a **Phase 1**? Os "Steps 1 e 2" sob `## How to Start a Task` parecem ter sido renomeados de `Phase 1` em algum momento, mas a numeração das fases seguintes (`Phase 2`, `Phase 3`) ficou. Resultado: um leitor encontra "Phase 2" sem ter visto "Phase 1", o que sugere uma seção faltando.

Esse é o tipo de fricção que custa 5 segundos por leitor — multiplicado por todos os usuários do `maintenance.md`, é manutenção barata demais para deixar.

> **Fingerprint:** `flow-maintenance-phase-numbering`

| Impacto | Detalhe |
|---------|---------|
| **Positivo (corrigir)** | Leitor não procura por "Phase 1" inexistente |
| **Negativo** | Mudança puramente cosmética |

**Recomendação:** uma das duas:
- Renomear `## How to Start a Task` para `## Phase 1: TASK PICKUP` (e os sub-itens passam a ser `Step 1.1` / `Step 1.2`); ou
- Renomear `Phase 2: DEVELOPMENT` → `## Phase 1: DEVELOPMENT` e `Phase 3` → `## Phase 2: QUALITY GATE`.

A primeira é mais consistente com os outros workflows (que começam em Phase 1).

---

## 2.5 `workflows/new-project.md` Phase 3 não tem passo explícito para `database-specialist`

`new-project.md § Phase 3: DEVELOPMENT` lista:
1. Environment Setup (devops)
2. Backend Implementation (backend-developer)
3. Frontend Implementation (frontend-developer)
4. Tests (test-specialists)

Em **nenhum** desses passos o `database-specialist` aparece. A única referência ao agente está em Phase 1.2 (architecture definition):

> Optionally collaborate with `database-specialist` for data decisions

Mas "optionally collaborate" durante a definição de arquitetura **não** cobre o trabalho de:
- Criar migration inicial
- Definir índices não-óbvios
- Modelar relações entre tabelas que ainda não existem em código
- Escolher estratégia de seeds para dev/test

Hoje, esse trabalho fica difuso: o `backend-developer` é forçado a tomar essas decisões inline, sem skill carregada (`database-specialist` carrega `database-multitenancy`, `database-debug`, `database-production` — `backend-developer` não).

> **Fingerprint:** `flow-new-project-database-implicit`

| Impacto | Detalhe |
|---------|---------|
| **Positivo (explicitar)** | Decisões de schema saem do `backend-developer` (que não é especialista em DB) |
| **Positivo (explicitar)** | Migration inicial fica versionada antes do primeiro endpoint |
| **Negativo** | Adiciona um passo formal no workflow; pequeno aumento de latência |

**Recomendação:** inserir uma seção `### Schema Definition (database-specialist)` em `new-project.md` Phase 3, **antes** da implementação backend, com o prompt:

```
Prompt: "As the database-specialist, define the initial schema for this project
         based on docs/development/architecture.md. Produce migrations
         and document the schema in docs/development/database.md."
```

Isso reflete o que `commands/plan.md` já faz (que spawn database-specialist em paralelo com architect).

---

## 2.6 Nenhum workflow tem passo de **rollback / hotfix** quando o deploy falha

`new-project.md` e `maintenance.md` terminam com "PR and Deploy" / "Workflow Complete". `security-patch.md` Step 6 menciona estratégia de deploy mas **não** o caminho de rollback.

Casos reais que ficam fora dos workflows:
- Deploy passou em CI mas falhou em produção (ex.: variável de ambiente missing).
- Migration aplicada parcialmente; precisa rollback antes de re-tentar.
- Quality gate passou mas regressão emergiu nas primeiras 24h.

O `devops-specialist` tem a expertise (a checklist `## What to Do Before Declaring Done` menciona "Rollback strategy documented (and tested where possible)"), mas o workflow não dá um trigger explícito.

> **Fingerprint:** `flow-no-rollback-or-deploy-failure-step`

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Time tem caminho documentado quando o deploy fura — incidente vira processo, não improviso |
| **Positivo** | Casa naturalmente com a skill `incident-response` faltante (já fingerprintada em 2026-05-06) |
| **Negativo** | Adiciona uma seção em 2 ou 3 workflows; aumenta tamanho |

**Recomendação:** adicionar uma seção opcional `## Phase X+1: POST-DEPLOY VERIFICATION + ROLLBACK PATH` em `new-project.md` e `maintenance.md`:

```
Prompt: "As the devops-specialist, verify the deploy succeeded
         (health checks, key metrics, error rates).
         If anything is off, present a rollback plan and execute after approval."
```

Esse passo materializa o que hoje é folclore: "todo mundo sabe que tem rollback, mas ninguém escreveu".

---

## 2.7 Resumo de fingerprints novos

| Fingerprint | Tema |
|-------------|------|
| `flow-workflows-no-adr-trigger` | Nenhum workflow menciona criação de ADR |
| `flow-workflows-no-session-summary-step` | Nenhum workflow tem passo de session-summary |
| `flow-bugfix-doc-vs-command-mismatch` | `commands/fix.md` pula `software-architect` que `bug-fix.md` mandata |
| `flow-maintenance-phase-numbering` | `maintenance.md` salta de `Step 2` para `Phase 2` (Phase 1 inexistente) |
| `flow-new-project-database-implicit` | Phase 3 do `new-project.md` não tem passo explícito para `database-specialist` |
| `flow-no-rollback-or-deploy-failure-step` | Workflows não cobrem o caminho de rollback / deploy falho |
