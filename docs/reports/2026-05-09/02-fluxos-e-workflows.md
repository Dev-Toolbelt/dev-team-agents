# 02 — Fluxos e Workflows

**Data:** 2026-05-09
**Escopo:** Quarta passada — gaps em workflows não cobertos pelas 3 passadas anteriores: workflows ausentes, ausência de cross-link, omissão de passos de finalização (commit/PR), `Par.` ainda em prosa fora de `bug-fix.md`.
**Anti-repetição:** os 75 fingerprints anteriores excluídos. Cada item abaixo recebe fingerprint inédito.

---

## Sumário

A passada de 2026-05-08 já apontou que workflows não mencionam ADR ou session-summary. Esta passada explora **gaps de cobertura** (comandos sem workflow correspondente), **ausência de cross-linking** entre workflows, e **omissão sistemática do passo de finalização** (commit + PR). Também se examina `security-patch.md` — não tocado nas passadas anteriores — e identifica falta de checkpoint formal de rollback.

---

## Sugestões

### 1. `commands/refactor.md` existe sem `workflows/refactor.md`

**Fingerprint:** `flow-no-workflow-refactor`

**Evidência:** O comando `/devteam:refactor` está documentado no CLAUDE.md como agente `software-architect → backend-developer¹ + frontend-developer¹`. O arquivo `commands/refactor.md` (20 linhas) prescreve o spawn. Mas não há `workflows/refactor.md` que descreva os passos detalhadamente — diferente de `bug-fix.md`, `new-project.md`, `maintenance.md`, etc.

Refatoração é um dos cenários mais delicados (alto risco de regressão, blast radius difuso). É exatamente o caso que justifica workflow longo com checkpoints.

**Impacto positivo:** workflow guia o usuário (Identificar → Diagnose → Plan → Refactor incremental → Test → Review). Reduz risco de refatoração "big-bang".

**Impacto negativo:** mais um arquivo para manter; risco de divergência com `commands/refactor.md`.

**Esforço:** Médio (criar arquivo seguindo o padrão dos outros 5 workflows).

---

### 2. `commands/review.md` existe sem `workflows/review.md`

**Fingerprint:** `flow-no-workflow-review`

**Evidência:** Mesma classe de gap. `/devteam:review` está documentado e tem `commands/review.md`, mas não há workflow descritivo. Review é um processo multi-agente (code-reviewer + software-architect + security-specialist + database¹) e é onde a arquitetura `review-router` se manifesta — merece workflow para deixar o fluxo de routing transparente.

**Impacto positivo:** workflow torna explícito quando review é "approve fast" vs "deep audit"; documenta o caminho `code-reviewer → routing → backend/frontend-reviewer`.

**Impacto negativo:** sobreposição com `code-reviewer.md` (que já tem prosa de routing).

**Esforço:** Médio.

---

### 3. Nenhum workflow termina com passo de commit ou PR

**Fingerprint:** `flow-workflows-no-commit-or-pr-step`

**Evidência:**

```
$ grep -l "/devteam:commit\|/devteam:pr\|conventional-commits" workflows/*.md
(nenhum match)
```

Os 5 workflows (`bug-fix`, `inherited-project`, `maintenance`, `new-project`, `security-patch`) terminam com Test/Review/Deploy mas **nenhum** instrui o usuário a commitar ou abrir PR. Para um usuário novo, o fluxo aparenta terminar antes da entrega real. O CLAUDE.md tem cláusula explícita "Commit Rule" mas os workflows não cruzam para ela.

**Impacto positivo:** consistência entre workflow e CLAUDE.md; usuário não esquece de seguir `conventional-commits`; integra naturalmente o `/devteam:commit` e `/devteam:pr` como último passo.

**Impacto negativo:** workflows ficam um pouco mais longos (1–2 passos a mais).

**Esforço:** Baixo (5 arquivos × ~10 linhas).

---

### 4. Workflows não fazem cross-linking entre si

**Fingerprint:** `flow-workflows-no-cross-linking`

**Evidência:**

```
$ grep -E "workflows/[a-z-]+\.md" workflows/*.md
(nenhum match)
```

Cenários comuns de roteamento ausente:
- Bug em produção descoberto como vulnerabilidade → caminho deveria saltar de `bug-fix.md` para `security-patch.md`.
- Manutenção que vira refator significativo → `maintenance.md` deveria sugerir `refactor.md`.
- Projeto herdado que tem bug bloqueante → `inherited-project.md` deveria mencionar `bug-fix.md` após audit inicial.

Hoje, o usuário toma essas decisões sem orientação — depende de leitura externa do CLAUDE.md.

**Impacto positivo:** fluxos compostos ficam navegáveis; reduz tempo de orientação para usuário novo.

**Impacto negativo:** se um workflow for renomeado, links quebram (cobrir com checagem em CI futuro).

**Esforço:** Baixo (1 seção "Quando trocar para outro workflow" em cada arquivo).

---

### 5. Apenas `bug-fix.md` cita execução paralela; `Par.` ainda inexistente fora dele

**Fingerprint:** `flow-workflows-no-par-table`

**Evidência:** `flow-parallel-marker-bugfix` (2026-05-06) flagou que `bug-fix.md` cita paralelismo em prosa, sem usar a coluna `Par.`. Esta passada confirma que o problema é **mais amplo**: `security-patch.md` Step 5 também usa `⚡ Parallel tip` em prosa; `new-project.md` e `inherited-project.md` têm fases que **podem** ser paralelas mas o leitor precisa inferir.

Diferença em relação ao fingerprint anterior: aquele cobria só `bug-fix.md`. Esta sugestão é por uma **migração consistente** dos 5 workflows para tabelas `Par.` no formato do `plan-template.md`.

**Impacto positivo:** prompt do usuário pode ser literalmente `"send all Par.A prompts in a single message"` — instrução clara, mecânica. Reduz o "achismo" de quando paralelizar.

**Impacto negativo:** workflows ficam mais densos visualmente; tabelas em Markdown quebram em terminal estreito.

**Esforço:** Médio (5 arquivos × revisão estrutural).

---

### 6. `security-patch.md` Step 6 menciona rollback inline mas sem checkpoint formal

**Fingerprint:** `flow-security-patch-no-rollback-checkpoint`

**Evidência:** `flow-no-rollback-or-deploy-failure-step` (2026-05-08) cobriu a ausência genérica de rollback em workflows. Este item é **mais específico**: `security-patch.md` Step 6 pede ao `devops-specialist` "consider rollback options", mas não há um Step 6.5 ou Step 7 dedicado a:

- Verificar que monitoring (Sentry, métricas) confirma que o patch reduziu/eliminou o vetor.
- Disparar rollback automático se métricas pioraram em janela definida.
- Documentar o ponto-de-rollback (commit hash) no security-incident.

Para vulnerabilidades CRITICAL, é especialmente arriscado deployar sem checkpoint formal de "OK, está estável".

**Impacto positivo:** transforma Step 6 de "deploy and hope" em "deploy + verify + rollback if needed" — alinhado com práticas de progressive rollout.

**Impacto negativo:** alonga o workflow; pode ser overkill para patches triviais (CSS escape, header config).

**Esforço:** Baixo (1 sub-passo).

---

### 7. `inherited-project.md` audit não tem critério explícito de saída

**Fingerprint:** `flow-inherited-audit-exit-criteria`

**Evidência:** O workflow `inherited-project.md` (132 linhas) tem fase de discovery/audit. O fingerprint `flow-discovery-loop-exit-criteria` (2026-05-07) flagou loop sem teto de iterações em discovery genérico. Este item é mais específico para `inherited-project`: não há definição clara de **quando o audit é "good enough"**. Ex.: "audit completo quando: arquitetura mapeada + testes existentes catalogados + 3 maiores riscos identificados". Hoje, é prosa solta.

**Impacto positivo:** evita audit sem fim; dá ao usuário o "quando devo aprovar e seguir adiante".

**Impacto negativo:** critério rígido demais pode pular nuances.

**Esforço:** Baixo (parágrafo de "Definition of Audit Done").

---

### 8. `maintenance.md` e `new-project.md` não enumeram comandos `/devteam:*` recomendados por fase

**Fingerprint:** `flow-workflows-no-command-shortcuts`

**Evidência:** Os 5 workflows usam o padrão `Prompt: "As the X agent, do Y"` — instrução em prosa direta para o agente. Nenhum sugere "ou use `/devteam:plan` neste passo". Isso significa que slash commands existem mas o usuário precisa saber **independentemente** que existem.

Para usuários que rodam `/devteam:workflow-new`, faria sentido o próprio workflow citar quando usar `/devteam:plan`, `/devteam:architect`, `/devteam:dba` em vez de prompts manuais.

**Impacto positivo:** elimina a curva de "decorar comandos"; fluxo virtuoso (workflow ensina os comandos enquanto guia).

**Impacto negativo:** se um comando for renomeado, todos os workflows precisam atualizar (exatamente o que `flow-bugfix-doc-vs-command-mismatch` flagou em 2026-05-08).

**Esforço:** Baixo (1 coluna nas tabelas de step).

---

## Lista Priorizada

| Prioridade | Sugestão | Esforço | Impacto |
|------------|----------|---------|---------|
| P1 | Adicionar passo de commit/PR em todos os workflows | Baixo | Alto (consistência com CLAUDE.md) |
| P1 | Criar `workflows/refactor.md` | Médio | Alto (lacuna em cenário de risco) |
| P2 | Criar `workflows/review.md` | Médio | Médio |
| P2 | Adicionar cross-links entre workflows | Baixo | Médio |
| P2 | Migrar prosa "parallel tip" para tabelas `Par.` em todos os workflows | Médio | Médio |
| P3 | Adicionar checkpoint de rollback em `security-patch.md` | Baixo | Médio |
| P3 | Definir critério de saída para audit em `inherited-project.md` | Baixo | Baixo |
| P3 | Cross-referência de comandos `/devteam:*` em workflows | Baixo | Baixo |

---

## Próxima passada

Ângulos ainda não cobertos: comportamento dos workflows quando o agente referenciado está marcado `inactive` no `auto-routing` (CLAUDE.md do projeto cliente); fluxo de "abandono parcial" (usuário começa workflow e desiste no meio — onde fica o estado?); como workflows interagem com worktree (todos os passos no mesmo worktree? troca de worktree entre fases?).
