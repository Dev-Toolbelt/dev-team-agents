# Relatório 2026-05-17 — Referências e Consistência

> 12ª passada de auditoria. Foco da janela: **drift introduzido pelos 4 commits de 2026-05-17** (Workflow Detection no software-architect, Composition Root pattern, doc-sync de `_index.md`), violações estruturais não cobertas em passadas anteriores, sub-escopo refinado de fingerprints pendentes que mudaram de superfície sem mudar de raiz.

---

## 1. `ref-claude-md-architect-command-description-out-of-sync-with-commands-architect-md-after-workflow-detection-introduction`

**Categoria:** documentação fora de sincronia / drift intra-janela
**Severidade:** HIGH

`commands/architect.md` linha 7 (commit `8c564bd`, 2026-05-17 16:02) agora contém:

> "`software-architect` at `.claude/agents/dev-team/software-architect.md` — architecture decisions, system design, trade-offs, ADR authoring, API contracts, design patterns. **The agent will automatically detect the appropriate workflow from the user's request** (new project, bug fix, refactor, security patch, design, mobile, fullstack, review, inherited project) and follow it. Falls back to the maintenance workflow when no clear signal is found."

`CLAUDE.md:194` (tabela "User-Invocable Commands") mantém apenas:

> `/devteam:architect` | `software-architect` | Architecture decisions, ADRs, trade-offs

A coluna "Agents invoked" e "Use when…" não capturam que o `software-architect` agora atua também como **workflow router**, conduta nova introduzida na mesma janela. Viola explicitamente a regra **Auto-Docs Rule** (CLAUDE.md:32):

> "After completing any task that changes **observable behavior** (...) — **automatically update `README.md`, `README.pt-BR.md`, and `CLAUDE.md`** before considering the task done."

**Impacto positivo da correção:** restaura coerência declarativa entre tabela master e arquivo de comando. Bloco de 25 linhas em `software-architect.md` é visível para usuário via `/devteam:architect`, mas invisível na tabela canônica.
**Impacto negativo:** trivial (1–2 linhas adicionais em CLAUDE.md).

---

## 2. `ref-frontend-developer-composition-root-section-mentions-angular-vue-react-explicitly-violating-stack-agnostic-mandate`

**Categoria:** violação de stack-agnosticism
**Severidade:** HIGH

`agents/frontend-developer.md:143-153` (commit `8b9c48b`, 2026-05-17 11:26) introduz nova seção:

```
## Composition Root (SPA / Framework DI)

When the frontend uses a DI container or explicit app bootstrap (Angular modules,
Vue `createApp` providers, React context wiring at `main.tsx`), apply the
Composition Root pattern...

- Setting up or reviewing Angular `NgModule` / standalone providers
- Configuring Vue `app.provide()` / Pinia store registration
- Designing a React context tree or service layer for a large SPA
```

Três frameworks (**Angular, Vue, React**) e três detalhes de API (NgModule, `createApp`, `main.tsx`, `app.provide`, Pinia) estão **embedded na diretriz core** do agente, não em referência condicional. Viola CLAUDE.md:124:

> "Stack-agnostic: no hardcoded framework, language, or tool references in agent core behavior"

**Padrão histórico:** a mesma classe de violação foi:
- Corrigida em `devops-specialist` em 2026-05-13 (✅ Executed)
- Identificada espelhada em `software-architect.md:117` em 2026-05-16 (🔴 Pendente)
- Agora **reintroduzida** em `frontend-developer.md` em 2026-05-17

Isto não é "drift residual" — é **regressão sistêmica**. O lint `scripts/agent-lint.sh` (185 linhas) não tem regra que detecte enumeração explícita de frameworks/linguagens em diretrizes core.

**Impacto positivo da correção:** restaura stack-agnostic mandate. Sugestão: mover detalhes para `skills/architecture/design-patterns/SKILL.md` → seção Composition Root, e deixar no agent apenas: "When the framework uses explicit app bootstrap and DI, apply Composition Root — load `skills/architecture/design-patterns/SKILL.md`".
**Impacto negativo:** perda de exemplos imediatos (mas exemplos pertencem à skill, não ao agent).

---

## 3. `ref-software-architect-workflow-detection-25-lines-inline-overlaps-spawn-classifier-skill-conceptually-not-extracted-to-shared-workflow-detection`

**Categoria:** governança / pattern de extração não aplicado
**Severidade:** HIGH

`agents/software-architect.md:45-69` (commit `8c564bd`) introduz 25 linhas de tabela "Intent signals → Workflow":

| Intent signals (keywords) | Workflow to load |
|---|---|
| new project, start from scratch, ... | `new-project.md` |
| bug, fix, broken, error, ... | `bug-fix.md` |
| refactor, cleanup, ... | `refactor.md` |
| ... (10 linhas no total) | ... |

Conceitualmente, isto é **classificação de intenção** — exatamente o que `skills/shared/spawn-classifier/SKILL.md` (89 linhas) faz, com a diferença de mapear para **agents condicionais** em vez de **workflows**.

A decisão de inlinear em agent (vs extrair para `skills/shared/workflow-detection/SKILL.md`) viola três regras estabelecidas:

1. **CLAUDE.md:128** "Max ~200 lines per agent; move reference material to skills"
2. **Princípio de DRY entre classificadores** — duas heurísticas inline/skill divergentes para resolver problema correlato
3. **Auto-Docs Rule** — Workflow Detection não foi documentado em CLAUDE.md como "skill mandatória" nem como "padrão arquitetural canônico"

**Impacto positivo da correção:** extrai 25 linhas do agent (≈ 12% do tamanho), libera ~400 tokens/spawn × 9 commands que carregam software-architect = ~3.600 tokens/sessão. Skill `workflow-detection` torna-se canônica, reaproveitável por outros agents (qa-specialist, product-analyst também precisam saber o workflow corrente).
**Impacto negativo:** custo de migração (criar skill + atualizar load no software-architect).

---

## 4. `ref-design-patterns-skill-grew-to-244-lines-after-composition-root-addition-now-4th-largest-skill-pattern-references-not-applied`

**Categoria:** drift de tamanho de skill / pattern de extração ignorado
**Severidade:** MEDIUM

`skills/architecture/design-patterns/SKILL.md` (commit `8b9c48b`) cresceu de **144 → 244 linhas** (+69% em 1 commit). Agora ocupa **4ª posição** entre as maiores skills do repo:

| Posição | Skill | Linhas |
|---------|-------|--------|
| 1 | `skills/integrations/push-notifications/SKILL.md` | 373 |
| 2 | `skills/devops/graphify-setup/SKILL.md` | 277 |
| 3 | `skills/shared/project-context/SKILL.md` | 266 |
| 4 | `skills/architecture/design-patterns/SKILL.md` | **244** |
| 5 | `skills/architecture/graphql/SKILL.md` | 235 |

O **pattern de extração para `references/`** foi aplicado em massa em 2026-05-13 (commits `b8ece69`, `e83eb3b`, `19ef0f9`) para 7 skills devops+docs+integrations. Em 2026-05-17, a adição massiva à design-patterns **não seguiu o pattern** — sem subdir `references/{composition-root,strategy,...}/`. Mesma classe de drift que `skill-push-notifications-373-lines-no-references-subdir...` (pendente desde 2026-05-15).

**Impacto positivo da correção:** sub-extração libera ~150 linhas × 3 agents (backend, frontend, software-architect) = ~7.200 tokens/sessão. Composition Root vira lazy-load condicional para tarefas DI/wiring.
**Impacto negativo:** custo de refatoração (criar references/composition-root.md + manter API de invocação).

---

## 5. `ref-architect-command-mentions-workflow-but-claude-md-line-194-table-omits-and-claude-md-line-218-workflow-list-doesnt-cross-link-architect`

**Categoria:** sub-escopo de #1 com angle quantitativo
**Severidade:** MEDIUM

CLAUDE.md tem **três blocos** que conceitualmente deveriam se referenciar:

1. **Linha 188–215** — tabela "User-Invocable Commands": lista `/devteam:architect` sem mencionar workflow detection
2. **Linha 217–224** — tabela "User-Invocable Workflows": lista os 10 workflows (`new-project`, `bug-fix`, `refactor`, ...)
3. **Linha 230** — bloco "Setup Trigger" menciona spawn de setup-assistant para project setup, mas não conecta com workflow detection do architect

Após `8c564bd`, o software-architect agora **lê os workflows declarados no bloco #2**, criando dependência declarativa nova. A omissão em #1 é o sub-escopo crítico; mas os blocos #2 e #3 também precisam de cross-link "agentes que leem workflows: `software-architect`".

**Impacto positivo da correção:** restaura coerência entre as 3 tabelas. Cross-link explícito ajuda novos contribuidores a entender que workflows são consumidos por agents (não só por usuários via slash command).
**Impacto negativo:** trivial (~3 linhas).

---

## 6. `ref-orphan-skill-scan-quiet-warn-section-still-reports-pre-2026-05-13-13-duplicate-loads-as-warnings-not-as-errors-after-fingerprint-Executed-marked-on-2026-05-13`

**Categoria:** marcação Executed sem validação cruzada / Guardian audit detail
**Severidade:** MEDIUM

`token-worktree-skill-loaded-twice-in-8-coding-agents-detection-after-orphan-scan-extension` foi marcado ✅ **Executed: 2026-05-15** no `_index.md:271`. Verificação manual hoje:

```bash
$ bash scripts/orphan-skill-scan.sh 2>&1 | grep -c "Duplicate skill load"
13   # ainda reporta 13 duplicate loads (8 worktree + 5 plan-mode)
```

O scan **detecta** a duplicação, mas a marcação Executed assume que ela foi resolvida. Discrepância: o que foi feito em 2026-05-13 (commit `19de0e1`) foi **estender o scan para detectar**, não **eliminar as duplicações**. Detection ≠ Fix.

Recomendação Guardian: **reabrir** o fingerprint como `⚠️ Partial` com sub-escopo: "Detection extended; duplicate loads themselves still present in 8 agents."

**Impacto positivo da correção:** elimina 8 duplicate loads de worktree (= 17 linhas × 8 agents = 136 linhas) + 5 duplicate loads de plan-mode (= ~10 linhas × 5 = 50 linhas) = **~3.000 tokens/sessão multi-agent**.
**Impacto negativo:** ordem de migração crítica (worktree precisa ser carregada antes de qualquer operação git, então a deduplicação deve preservar ordering).

---

## 7. `ref-templates-runbook-only-template-with-loader-skill-but-runbook-skill-also-references-broken-relative-path-templates-runbook-template-md`

**Categoria:** sub-escopo orphan templates + path relativo
**Severidade:** MEDIUM

`bash scripts/orphan-template-scan.sh` hoje reporta apenas **2 órfãos** (adr-template, backlog-template). Por que? Porque `runbook-template.md` é referenciado por `skills/shared/runbook/SKILL.md`.

**Mas:** `skills/shared/runbook/SKILL.md` faz referência por path **relativo** (`templates/runbook-template.md`) — exatamente a mesma falha do `ref-templates-dir-shipped-but-not-symlinked-...` (pendente desde 2026-05-15). Resultado: o template é "referenciado" pelo orphan scan, mas é **inalcançável em produção** (em projeto instalado sem symlink).

Padrão real:

| Template | Referenced? | Reachable in install? |
|----------|-------------|------------------------|
| `adr-template.md` | ❌ (orphan) | ❌ (não-referenciado) |
| `backlog-template.md` | ❌ (orphan) | ❌ (não-referenciado) |
| `plan-template.md` | ✅ (2 refs) | ❌ (path relativo, no symlink) |
| `runbook-template.md` | ✅ (1 ref) | ❌ (path relativo, no symlink) |

**100% dos templates (4/4) são inalcançáveis em produção.** O scan atual mascara metade do problema porque só checa "tem referência?", não "referência funciona?".

**Impacto positivo da correção:** estender `orphan-template-scan.sh` para validar resolvability do path em contexto de instalação. Pequena mudança de regex + um `test -e` faz o serviço.
**Impacto negativo:** scan fica ~10% mais lento (negligível).

---

## Resumo

7 fingerprints originais nesta categoria, todos não-duplicados do histórico (verificado contra todas as passadas 2026-05-06 → 2026-05-16):

| # | Fingerprint | Severidade |
|---|-------------|------------|
| 1 | `ref-claude-md-architect-command-description-out-of-sync-with-commands-architect-md-after-workflow-detection-introduction` | HIGH |
| 2 | `ref-frontend-developer-composition-root-section-mentions-angular-vue-react-explicitly-violating-stack-agnostic-mandate` | HIGH |
| 3 | `ref-software-architect-workflow-detection-25-lines-inline-overlaps-spawn-classifier-skill-conceptually-not-extracted-to-shared-workflow-detection` | HIGH |
| 4 | `ref-design-patterns-skill-grew-to-244-lines-after-composition-root-addition-now-4th-largest-skill-pattern-references-not-applied` | MEDIUM |
| 5 | `ref-architect-command-mentions-workflow-but-claude-md-line-194-table-omits-and-claude-md-line-218-workflow-list-doesnt-cross-link-architect` | MEDIUM |
| 6 | `ref-orphan-skill-scan-quiet-warn-section-still-reports-pre-2026-05-13-13-duplicate-loads-as-warnings-not-as-errors-after-fingerprint-Executed-marked-on-2026-05-13` | MEDIUM |
| 7 | `ref-templates-runbook-only-template-with-loader-skill-but-runbook-skill-also-references-broken-relative-path-templates-runbook-template-md` | MEDIUM |
