# Relatório — Fluxos e Workflows (2026-05-12)

Auditoria focada em **commands, workflows, hooks e dispatchers** — gaps, asimetrias e oportunidades de orquestração detectadas hoje. Todas as sugestões abaixo são **originais** ou **variantes com sub-escopo novo** de fingerprints pendentes do `_index.md`.

---

## 1. `flow-plan-command-does-not-load-plan-mode-skill`

**Severidade:** 🟠 Alta — ironia conceitual

**Detecção:** O comando `/devteam:plan` é o command oficial para gerar planos. Porém `commands/plan.md` **não carrega `skills/shared/plan-mode/SKILL.md`**:

```
grep -l plan-mode commands/*.md
→ (vazio para plan.md)

grep -l plan-mode agents/*.md
→ backend-developer, code-reviewer, database-specialist,
   devops-specialist, frontend-developer, mobile-developer,
   software-architect (7 agents)
```

O plan-mode é carregado pelos **agentes spawnados** (software-architect, etc.), mas o command em si delega sem garantir que o skill está visível ao spawn.

**Impacto positivo (se corrigido):** plan-mode (143 linhas, com template canonical do formato STEPS table + Par. column) é carregado uma vez no command em vez de implicitamente por cada agent spawn — economiza tokens e garante consistência mesmo se um agent esquecer de carregar.

**Impacto negativo (se mantido):** três agents do plan (software-architect, product-analyst, database-specialist) podem gerar planos com formatos divergentes; product-analyst hoje **não carrega plan-mode** ainda assim.

**Sugestão:** adicionar linha 1 em `commands/plan.md`: `Load skills/shared/plan-mode/SKILL.md to anchor the canonical plan format.`

---

## 2. `flow-installer-hook-coverage-still-3-of-7-after-session-start-added`

**Severidade:** 🟡 Média — variante de fingerprint ⚠️ Partial (2026-05-10)

**Detecção:** Após commit `f63ed64` (que adicionou SessionStart), o `install.sh` registra agora **3 de 7+** hook events suportados pelo Claude Code:

```bash
# Registrados
_inject_hook "PreToolUse"   ...
_inject_hook "Stop"         ...
_inject_hook "SessionStart" ...

# Não registrados (4 eventos)
UserPromptSubmit  ← oportunidade: detectar setup trigger, language drift
SubagentStop      ← oportunidade: agregação multi-agent summary
Notification      ← oportunidade: roteamento de mensagens DEV TEAM
PreCompact        ← oportunidade: salvar session-summary antes do compact
```

**Impacto positivo (se corrigido):** cada evento adicional habilita uma classe nova de comportamento sem aumentar tamanho de agents/skills (lógica fica em hook scripts).

**Impacto negativo (se mantido):** funcionalidades hoje implementadas inline em agentes (ex.: detecção do trigger "set up dev-team-agents", session-summary post-multi-agent) poderiam ser hooks; mantê-las inline aumenta token cost por sessão.

**Sugestão de ordenação:** implementar **`PreCompact` primeiro** (maior valor: garante que session-summary é escrito mesmo se o usuário aplicar compact mid-task), depois `SubagentStop`.

---

## 3. `flow-review-command-no-explicit-plan-gate-undocumented-exception`

**Severidade:** 🟡 Média

**Detecção:** `commands/review.md` (1049 bytes) **não tem PLAN GATE** — diferente de 20 outros commands que têm o bloco mandatório. CLAUDE.md linha 154 documenta exceção apenas para `commit` e `update`:

```
> Exception — commands that do NOT load `current-context`:
> /devteam:commit … /devteam:update … Both omit current-context by design.
```

`review.md` carrega current-context **mas omite plan gate**. A justificativa provável é que `code-reviewer` é read-only (não modifica arquivos), então plan gate não se aplica. Mas:
- `code-reviewer` carrega `comments-policy` skill, que pode **sugerir** mudanças ao usuário
- Não há documentação formal da exceção

**Impacto positivo (se corrigido com doc):** alinha exceções explicitamente; remove ambiguidade para novos commands futuros (ex.: `/devteam:audit`, `/devteam:scan`).

**Impacto negativo (se mantido):** padrão "review é read-only logo dispensa plan" é tácito; risco de futuro command read-only ser criado sem plan e sem documentação.

**Sugestão:** estender a "Exception" em CLAUDE.md para incluir review e renomear: _"Exception — commands that do NOT require Plan Gate: /devteam:review (read-only by design)"_.

---

## 4. `flow-stop-dispatcher-runs-all-4-sub-scripts-without-fast-path`

**Severidade:** 🟡 Média

**Detecção:** `scripts/hooks/stop.sh` executa **todos os 4 sub-scripts** (`01-session-summary.sh`, `02-orphan-skill-scan.sh`, `03-agent-lint.sh`, `04-notifier.sh`) em série, sem checkpoint algum:

```bash
for script in "$HOOKS_DIR"/*.sh; do
    [ -f "$script" ] || continue
    bash "$script" || SCRIPT_EXIT=$?
done
```

Cada sub-script já tem internamente seu próprio gate (ex.: `04-notifier.sh` agora tem `last_shown_date`; `02-orphan-skill-scan` checa mudanças em `agents/`/`skills/`). Mas o dispatcher **invoca todos** mesmo quando `git diff` indica zero mudanças relevantes.

**Impacto positivo (se corrigido):** dispatcher computa diff uma vez (~30ms) e passa flag `--skip-if-no-changes` ou variável `DEVTEAM_HOOK_NO_RELEVANT_CHANGES=1` aos sub-scripts, que decidem pular cedo. Soma ~150ms→~30ms em sessões read-only puras.

**Impacto negativo (se mantido):** Stop hook adiciona ~150-300ms de overhead em sessões que não modificaram nada (ex.: `/devteam:review`, `/devteam:qa`).

---

## 5. `flow-no-pre-spawn-current-context-warm-cache`

**Severidade:** 🟡 Média

**Detecção:** 23 de 25 commands carregam `current-context` antes de spawn. Cada agent spawn então tipicamente **re-executa** o mesmo `git branch`, `git diff main…HEAD`, leitura de `.claude/.worktree-session` etc. — overhead de ~5-10s por spawn em projetos grandes.

`current-context/SKILL.md` é mecânica de leitura, mas não tem cache. Não há contrato de "pré-aquecimento" — o command poderia gravar o resultado em `.claude/user-data/.context-cache.json` (TTL curto, ex.: 5min) e cada agent spawned ler dali.

**Impacto positivo (se corrigido):** em commands multi-spawn (plan, refactor, fix com 3-5 agents), elimina o re-trabalho. Em projetos grandes (>1GB git), redução estimada de 30-60s wall-clock.

**Impacto negativo (se mantido):** spawn-fanout é a operação mais lenta hoje em commands tipo plan/refactor. Custo é proporcional ao número de agents.

**Sugestão:** estender `current-context/SKILL.md` com seção "Cache write" (escreve cache) + "Cache read" (lê se TTL válido). Cache key: `(branch-sha, worktree-session-md5)`.

---

## 6. `flow-spawn-classifier-only-plan-but-fix-refactor-fullstack-multi-agent-too`

**Severidade:** 🟡 Média — sub-escopo de fingerprint pendente

**Detecção:** `spawn-classifier` skill é carregada apenas por `commands/plan.md`. Porém commands com spawn condicional documentado em CLAUDE.md também deveriam invocá-la:

| Command | Spawn condicional declarado em CLAUDE.md | Carrega spawn-classifier? |
|---------|------------------------------------------|---------------------------|
| `/devteam:plan` | backend¹, frontend¹, devops¹ | ✅ |
| `/devteam:backend` | database-specialist¹ | ❌ |
| `/devteam:frontend` | ui-ux-designer¹ | ❌ |
| `/devteam:fullstack` | database¹, ui-ux¹ | ❌ |
| `/devteam:fix` | backend¹ + frontend¹ + mobile¹ → test-specialist¹ | ❌ |
| `/devteam:refactor` | database¹, backend¹, frontend¹ | ❌ |
| `/devteam:review` | database¹, mobile-developer¹ | ❌ |

7 commands têm spawn condicional documentado, **apenas 1 carrega o classifier**.

**Impacto positivo (se corrigido):** spawn condicional fica determinístico e auditável; menos chance de spawn de agent irrelevante (= economia de tokens nos 6 commands).

**Impacto negativo (se mantido):** cada command decide spawn condicional inline com heurística ad-hoc; classifier vira "código morto" para 6 dos 7 casos.

---

## 7. `flow-no-workflow-mobile-md-and-workflow-design-md-files`

**Severidade:** 🟡 Média — variante de fingerprint pendente

**Detecção:** Sub-escopo específico do antigo `ref-mobile-workflow-missing-despite-command` (2026-05-11): **dois commands têm asymmetria com workflows**:

| Command | Workflow correspondente | Existe? |
|---------|--------------------------|---------|
| `/devteam:mobile` | `workflows/mobile.md` | ❌ |
| `/devteam:design` | `workflows/design.md` | ❌ |

Ambos os commands existem (commits `1c8be69` e anteriores) mas não têm workflow guide associado. CLAUDE.md linha 167 lista **8 workflows existentes** — nenhum cobre mobile ou design isoladamente.

**Impacto positivo (se corrigido):** quando o usuário pede `/devteam:mobile` em uma feature complexa multi-tela, há um guia ordenado de steps (design → desenvolvimento → testes); idem para design isolado (design-system audit, redesign).

**Impacto negativo (se mantido):** mobile/design operam com prompt único livre; perdem o benefício de step-by-step com checkpoint que outros workflows oferecem.

---

## 8. `flow-pr-command-no-conventional-commits-validation-of-staged-commits`

**Severidade:** 🟢 Baixa

**Detecção:** `commands/pr.md` chama `technical-writer` para draft do PR. **Não valida** se os commits da branch seguem Conventional Commits (a regra existe na skill `conventional-commits` mas só é usada em commit-time). Resultado: PR pode ser aberta com commit messages misturando padrões (alguns Conventional, outros não).

**Impacto positivo (se corrigido):** pre-flight check no `commands/pr.md` Step 0: rodar `git log main..HEAD` e validar via heurística simples (regex `^(feat|fix|chore|docs|refactor|perf|test|ci|build|style)(\(.+\))?: `).

**Impacto negativo (se mantido):** PR pode ser aberta com história inconsistente; corrigir pós-fact requer `git rebase -i` (caro em colaboração).

---

## 9. `flow-update-command-no-pre-update-backup-strategy-after-revert-fc57a86`

**Severidade:** 🟡 Média — derivado de decisão ↩️ Reverted

**Detecção:** O fingerprint `flow-update-command-no-rollback-path` foi marcado ↩️ Reverted em 2026-05-11 — o time conscientemente removeu `.previous/` (commit `fc57a86`). **Porém, o `update.sh` hoje **não tem backup algum**.** Se uma atualização corrompe `.claude/dev-team-agents/`, o usuário precisa reinstalar do zero.

**Sub-escopo novo (não coberto pelo revert):** alternativas mais leves que `.previous/` não foram exploradas:

| Estratégia | Custo | Cobertura |
|-----------|-------|-----------|
| `.previous/` (revertido) | Alto (pasta órfã pós-update) | Total |
| Git tag pré-update (`devteam-pre-update-<timestamp>`) | Zero (só se o user tracking `.claude/`) | Parcial |
| Lockfile `installed-version` + script de re-download por tag | Zero | Total (rede-dependente) |

**Impacto positivo (se corrigido):** UX de recovery sem o problema de pasta órfã.

**Impacto negativo (se mantido):** estratégia atual é "se quebrar, reinstale via curl" — funciona, mas é assustador para usuários novos.

**Sugestão:** `scripts/update.sh` registrar `.claude/user-data/.installed-version` antes do swap; criar `scripts/rollback.sh` que aceita versão e re-baixa via curl (`/v$VERSION/devteam.tar.gz`).

---

## 10. `flow-refactor-workflow-no-tag-checkpoint-still-after-checkpoints-added`

**Severidade:** 🟡 Média — variante focada de fingerprint pendente

**Detecção:** Sub-escopo do antigo `flow-refactor-workflow-no-rollback-tag-recommendation` (2026-05-11, pendente). `workflows/refactor.md` agora **tem 5 CHECKPOINTs** (linhas 40, 68, 153, 187, 188) — bom progresso. Mas nenhum cria git tag explícita. O CHECKPOINT semântico é "aguardar aprovação"; o CHECKPOINT físico (rollback artifact) está ausente.

Adição mínima: após o Step 1 (worktree/branch ready), adicionar 1 linha:
```
▶ COMMAND — bash: git tag pre-refactor-<scope>-<timestamp>
```

**Impacto positivo (se corrigido):** rollback fica em 1 comando (`git reset --hard pre-refactor-foo-202605120930`); usuários nervosos com refactor aceitam o processo mais facilmente.

**Impacto negativo (se mantido):** rollback exige reconstrução manual via `git reflog` ou `git log` — friction alto em refactors mal-sucedidos.

---

## Resumo

| Severidade | Quantidade |
|------------|-----------|
| 🟠 Alta (ironia conceitual ou viola regra explícita) | 1 |
| 🟡 Média | 7 |
| 🟢 Baixa | 1 |
| **Total** | **9** + 1 sub-escopo |

**Top 3 prioridades:**

1. `flow-plan-command-does-not-load-plan-mode-skill` — ironia que o próprio command "plan" não carregue o plan skill.
2. `flow-stop-dispatcher-runs-all-4-sub-scripts-without-fast-path` — economia direta de 100-200ms/sessão; baixo risco.
3. `flow-spawn-classifier-only-plan-but-fix-refactor-fullstack-multi-agent-too` — fecha o gap entre declaração (CLAUDE.md) e execução real em 6 commands.
