# Relatório 2026-05-17 — Agentes e Skills

> 12ª passada. Foco: novas violações estruturais introduzidas pelos commits `8b9c48b` (Composition Root) e `8c564bd` (Workflow Detection); assimetrias entre agents que receberam tratamentos diferentes para o mesmo pattern; gaps de extração não aplicados.

---

## 1. `agent-software-architect-now-acts-as-workflow-router-with-workflow-detection-block-but-skill-shared-workflow-detection-doesnt-exist-functional-overlap-with-spawn-classifier`

**Categoria:** novo padrão arquitetural sem extração para skill
**Severidade:** HIGH

`agents/software-architect.md` cresceu de 184 → **208 linhas** após commit `8c564bd`, com inserção de bloco "Workflow Detection" de 25 linhas (linhas 45–69). Sumário do bloco:

```
## Workflow Detection

Before acting on any request, classify the user's intent and load the matching
workflow file from .dev-team-agents/workflows/.

| Intent signals | Workflow to load |
| new project, ... | new-project.md |
| bug, fix, ... | bug-fix.md |
| ... (10 linhas) |
```

Problemas em camadas:

1. **Tamanho:** o agent ainda está dentro do cap de ~200 linhas (208 ≈ cap), mas qualquer adição futura empurra para violação. Os 25 linhas são candidato natural à extração.

2. **Overlap conceitual com `skills/shared/spawn-classifier/SKILL.md` (89 linhas):** spawn-classifier classifica para **decidir spawn de agents condicionais**; workflow-detection classifica para **decidir qual workflow carregar**. Ambas são classificações de intent — sem skill base compartilhada (`skills/shared/intent-classification/`?).

3. **Faltam reuse hooks:** `software-architect` é spawneado em 9 commands (`/devteam:plan`, `/devteam:fix`, `/devteam:refactor`, `/devteam:fullstack`, `/devteam:architect`, `/devteam:adr`, `/devteam:review`, `/devteam:dba`, `/devteam:security`). Os outros 8 commands **não detectam workflow** — só o invocado via `/devteam:architect` o faz.

4. **Não há registro em CLAUDE.md:** seção "Authoring Standards → Agents" (linhas 116–142) não menciona Workflow Detection como mandatório. Próximo agent novo pode (ou não) replicar o padrão sem critério.

**Recomendação técnica:**
- Criar `skills/shared/workflow-detection/SKILL.md` (~40 linhas: tabela canônica + detection rules)
- `software-architect.md` carrega via `Load skills/shared/workflow-detection/SKILL.md` (1 linha)
- Documentar em CLAUDE.md como skill mandatória para todos os agents que executam fluxos multi-fase

**Impacto positivo:** elimina 24 linhas do agent; libera reuse por outros agents (product-analyst, qa-specialist beneficiam de saber o workflow corrente). Token economy quantificada em [04-economia-tokens.md].
**Impacto negativo:** custo de migração; ADR necessário.

---

## 2. `agent-frontend-developer-composition-root-12-line-block-violates-stack-agnostic-mandate-and-grows-agent-from-232-to-244-lines`

**Categoria:** violação de stack-agnosticism + growth de agent
**Severidade:** HIGH

Detalhe completo em `01-referencias-e-consistencia.md` #2. Aqui o angle "agent":

`agents/frontend-developer.md:143-153` (commit `8b9c48b`) cresce o agent de 232 → 244 linhas. Cap declarado: ~200. **Violação +22%** (mantida do estado anterior, agravada hoje).

Frontend-developer agora é o **3º maior agent** (atrás de mobile-developer 263 e backend-developer 261, ambos também acima do cap). Tabela completa:

| Posição | Agent | Linhas | vs cap (~200) |
|---------|-------|--------|---------------|
| 1 | `mobile-developer` | 263 | +31% |
| 2 | `frontend-test-specialist` | 262 | +31% |
| 3 | `backend-developer` | 261 | +30% |
| 4 | `setup-assistant` | 238 | +19% |
| 5 | `devops-specialist` | 237 | +18% |
| 6 | `security-specialist` | 234 | +17% |
| 7 | `frontend-developer` | **244** | **+22%** (era +16% antes do commit de hoje) |
| 8 | `code-reviewer` | 228 | +14% |
| 9 | `software-architect` | **208** | **+4%** (era +0% antes do commit de hoje) |

**7 dos 17 agents (41%) acima do cap**, dois deles crescidos hoje. Tendência sistêmica: features novas inflam agents em vez de empurrar para skills.

**Recomendação:** **moratória de growth em agents** até taxa abaixo do cap voltar a ≥80% (atualmente 59%). Toda adição de funcionalidade dever-se-ia primeiro perguntar: "isto vai para skill?".

**Impacto positivo:** restaura disciplina arquitetural. Composition Root vai para skill (já existe — design-patterns), agent só referencia.
**Impacto negativo:** custo de revisão de adições; trade-off com velocidade de iteração.

---

## 3. `agent-backend-developer-composition-root-rule-1-line-vs-frontend-developer-12-lines-asymmetric-coverage-of-identical-pattern-no-justification`

**Categoria:** assimetria de tratamento entre agents pares
**Severidade:** MEDIUM

O mesmo commit `8b9c48b` adicionou Composition Root em **3 agents**, com pesos drasticamente diferentes:

| Agent | Linhas adicionadas | Conteúdo |
|-------|--------------------|----------|
| `backend-developer` | 1 | rule item: "Use DI over hard-coded singletons; load Composition Root from design-patterns" |
| `frontend-developer` | 12 | seção completa com bullets, regra explícita, exemplos por framework |
| `software-architect` | 1 | conditional load para "DI/wiring/IoC tasks" |

Composition Root é tão relevante em backend quanto em frontend (Spring `@Configuration`, NestJS providers, Laravel container, ASP.NET `Program.cs`). Por que frontend ganha 12 linhas explícitas e backend só 1?

Mensagem implícita do tratamento assimétrico: "Composition Root é frontend concern". Falso historicamente — o pattern foi formalizado por Mark Seemann **em contexto backend .NET** ("Dependency Injection in .NET", 2011).

**Recomendação:**
- OU expandir backend-developer com seção análoga (mas isto piora violação do cap — backend já está em +30%)
- OU **contrair frontend-developer** para 1 linha + load condicional, espelhando o pattern adotado em backend (preferido, evita inflar agent já em +22% do cap)

**Impacto positivo:** simetria de tratamento. Sinaliza que pattern é cross-stack, não frontend-only. Reduz frontend-developer de 244 → ~233 linhas.
**Impacto negativo:** perda de exemplos imediatos no agent (mas exemplos vivem na skill).

---

## 4. `skill-architecture-design-patterns-grew-100-lines-with-composition-root-no-references-extraction-pattern-not-applied-now-4th-largest-skill`

**Categoria:** padrão de extração não aplicado
**Severidade:** MEDIUM

Cross-cut com `ref-design-patterns-skill-grew-to-244-lines...` (Referências #4). Angle "skill":

`skills/architecture/design-patterns/SKILL.md` agora tem 244 linhas, organizadas conceitualmente em:

- Cabeçalho + Foundational (≈ 30 linhas)
- Strategy Pattern (≈ 35 linhas — pré-existente)
- Factory Pattern (≈ 30 linhas — pré-existente)
- Observer / Pub-Sub (≈ 35 linhas — pré-existente)
- Repository Pattern (≈ 14 linhas — pré-existente)
- **Composition Root** (≈ 100 linhas — adicionada hoje)

A seção adicionada hoje é **41% do total** da skill. Padrão de extração natural:

```
skills/architecture/design-patterns/
├── SKILL.md (cabeçalho + matriz de patterns + when-to-load)
├── references/
│   ├── strategy.md
│   ├── factory.md
│   ├── observer.md
│   ├── repository.md
│   └── composition-root.md
```

Adoção desse pattern reduz SKILL.md para ~50 linhas. Cada subseção é loaded sob demanda quando o agent identificar o pattern relevante.

**Impacto positivo:** economy de tokens (cálculo em 04-economia-tokens.md). Padrão consistente com migrações de 2026-05-13 (kong, monitoring, jira, realtime, multitenancy, sonarqube).
**Impacto negativo:** custo da extração (~30min); risco de breaking links se outras referências citarem seções específicas.

---

## 5. `agent-software-architect-immutability-warning-section-still-not-explicitly-listed-in-grep-after-workflow-detection-insertion-shifts-line-numbers`

**Categoria:** verificação de consistência mandatória
**Severidade:** LOW

CLAUDE.md:122 mandata "Every agent must include: **Foundational Rule** (load context first) + **Immutability Warning**".

Verificação atual:

```bash
$ grep -L "Immutability Warning" agents/*.md
agents/backend-test-specialist.md
agents/frontend-test-specialist.md
agents/product-analyst.md
agents/qa-specialist.md
agents/security-specialist.md
agents/technical-writer.md
agents/ui-ux-designer.md
```

**7 dos 17 agents (41%)** não têm Immutability Warning. Inclui agents proeminentes em fluxos multi-agent (qa-specialist, security-specialist, ui-ux-designer).

A regra CLAUDE.md:122 é declarativa, mas `scripts/agent-lint.sh` (185 linhas) **não valida sua presença**. Não há CI gate. Os 7 agents sem warning podem ter modificações destrutivas sem o usuário ser notificado.

**Impacto positivo:** adicionar regra ao agent-lint (~5 linhas em shell) + completar os 7 agents (cada warning é ~5 linhas). Total: ~40 linhas em 7 arquivos.
**Impacto negativo:** trivial.

---

## 6. `skill-shared-worktree-214-lines-loaded-by-8-coding-agents-no-references-extraction-cross-cut-with-token-economy-fingerprint-from-2026-05-16-still-pending`

**Categoria:** sub-escopo agent-side
**Severidade:** MEDIUM

Cross-cut com `skill-shared-worktree-214-lines-loaded-by-8-coding-agents-no-references-extraction` (2026-05-16 pendente) — Angle agent: cada coding-agent carrega a skill **inteira** em seu Worktree Isolation block. Olhando os agents:

- 8 agents (backend-developer, frontend-developer, mobile-developer, database-specialist, devops-specialist, ui-ux-designer, backend-test-specialist, frontend-test-specialist) têm `## Worktree Isolation` block hardcoded — ~17 linhas cada × 8 = **136 linhas duplicadas no repo**.
- Adicionalmente, cada um carrega a skill `skills/shared/worktree/SKILL.md` (214 linhas).
- Total fanout: 17 × 8 + 214 × N_invocations_per_session.

Há **dois** pontos de duplicação:
1. **Inline block** repetido 8 vezes (sub-escopo de `token-worktree-isolation-block-136-duplicate-lines-...` pendente)
2. **Skill load** dispara 214 linhas em multi-agent flows

**Recomendação:**
- Extrair o block inline para `skills/shared/worktree-isolation/SKILL.md` (~25 linhas: cabeçalho + decision tree)
- A skill main (`skills/shared/worktree/SKILL.md`) é carregada **apenas quando** `worktree=yes` na decision file `.dev-team-agents/.worktree-session`

**Impacto positivo:** economy de ~7.000 tokens/sessão multi-agent.
**Impacto negativo:** custo de migração em 8 agents (mas pode ser sed-driven se ordering das tools for canônica — pendente desde 2026-05-12).

---

## Resumo

6 fingerprints originais nesta categoria:

| # | Fingerprint | Severidade |
|---|-------------|------------|
| 1 | `agent-software-architect-now-acts-as-workflow-router-with-workflow-detection-block-but-skill-shared-workflow-detection-doesnt-exist-functional-overlap-with-spawn-classifier` | HIGH |
| 2 | `agent-frontend-developer-composition-root-12-line-block-violates-stack-agnostic-mandate-and-grows-agent-from-232-to-244-lines` | HIGH |
| 3 | `agent-backend-developer-composition-root-rule-1-line-vs-frontend-developer-12-lines-asymmetric-coverage-of-identical-pattern-no-justification` | MEDIUM |
| 4 | `skill-architecture-design-patterns-grew-100-lines-with-composition-root-no-references-extraction-pattern-not-applied-now-4th-largest-skill` | MEDIUM |
| 5 | `agent-software-architect-immutability-warning-section-still-not-explicitly-listed-in-grep-after-workflow-detection-insertion-shifts-line-numbers` | LOW |
| 6 | `skill-shared-worktree-214-lines-loaded-by-8-coding-agents-no-references-extraction-cross-cut-with-token-economy-fingerprint-from-2026-05-16-still-pending` | MEDIUM |
