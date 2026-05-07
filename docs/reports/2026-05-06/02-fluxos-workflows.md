# 2. Pontos de Melhoria nos Fluxos (Workflows)

← [Voltar ao índice](index.md)

---

## 2.1 Padronização do marcador de paralelismo

O `templates/plan-template.md` define a coluna `Par.` para indicar passos paralelizáveis.
Já o `workflows/bug-fix.md` (Step 3+4) e o `workflows/new-project.md` (Phase 4 Quality
Gate) descrevem paralelismo apenas em prosa ("Send all four prompts in a single
message").

> **Fingerprint:** `flow-parallel-marker-bugfix`, `flow-quality-gate-explicit-par-column`

**Sugestão:** Adicionar um bloco mini-plan no início de cada workflow com a coluna
`Par.` preenchida. Padroniza a forma como o usuário lê paralelismo, alinha com o
`plan-template`.

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Reforça consistência visual; usuário aprende a ler `Par.` em todos os artefatos |
| **Positivo** | Reduz tempo de execução real ao tornar paralelismo mais óbvio |
| **Negativo** | Workflows ficam um pouco mais visuais (≈ 6 linhas a mais por workflow) |
| **Negativo** | Manutenção dupla se a tabela for editada manualmente (mitigável com snippet) |

## 2.2 Ausência de "exit criteria" mensurável nos workflows

Cada workflow descreve fases mas termina com texto narrativo como
"The workflow is complete when the quality gate passes". Falta uma checklist final
explícita por workflow.

**Sugestão:** Adicionar uma seção "DoD do Workflow" no rodapé de cada arquivo, com
caixas `☐` que o usuário possa marcar mentalmente.

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Reduz casos em que o usuário "esquece" de rodar o `qa-specialist` ou o `code-reviewer` |
| **Positivo** | Facilita instrumentação futura (script poderia validar o checklist) |
| **Negativo** | Aumenta levemente o tamanho dos workflows |

## 2.3 Inserção de "fast path" para fluxos triviais

`bug-fix.md` exige diagnóstico → fix → QA + review paralelo → testes → docs. Para
**typos** ou **bugs de uma linha**, a sobrecarga de plano + revisor formal não agrega.
O próprio `CLAUDE.md` já abre exceção para "one-liner fixes", mas o workflow não
reflete isso.

**Sugestão:** Criar uma rama "FAST-PATH" no início do `bug-fix.md`:

```text
Se a mudança é one-liner (typo, rename simples):
  - skip Plan Mode (CLAUDE.md já libera)
  - skip QA agent
  - rodar apenas code-reviewer + commit
```

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Economiza dezenas de minutos em correções triviais |
| **Positivo** | Reduz fadiga do usuário com plan mode em casos óbvios |
| **Negativo** | Pode ser usado abusivamente para pular revisão real (mitigar com escopo bem objetivo) |
