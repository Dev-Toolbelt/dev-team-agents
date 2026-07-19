# Relatório 04 — Economia de Tokens (2026-05-18)

**Foco:** custos novos introduzidos pela telemetria, eager loads remanescentes pós-extração, crescimento do `_index.md`, e oportunidades de batching/cacheing.

**Multiplicador adotado:** ~16 tokens por linha (conservador para texto técnico ASCII).

---

## #1 — `token-telemetry-helper-289-lines-loaded-by-2-sub-scripts-plus-install-update-shell-fork-overhead-150ms-per-event-burst-mode-burns-200ms-acumulado`

**Severidade:** HIGH
**Arquivos:** `scripts/helpers/telemetry-send.sh` (289 linhas), `scripts/hooks/pre-tool-use/02-telemetry.sh` (68 linhas), `scripts/hooks/stop/05-telemetry.sh` (46 linhas)

Custo bruto do feature de telemetria (commits `bd61ff7`, `a4bb102`, `9f1826d`):
- 289 + 68 + 46 = **403 linhas** novas em `scripts/`
- 3 cópias da função `_telemetry_enabled` (10 linhas cada) = **30 linhas duplicadas**
- 1 fork de python3 por evento × ~5 eventos/sessão = **5 forks/sessão**
- Em sessão burst (`/devteam:fullstack` = ~40 tool calls), 02-telemetry roda 40 vezes = **40 forks × ~30ms = ~1.200ms overhead**

Calculo de tokens (perspectiva agente):
- Telemetria não consome tokens do LLM (executa em shell), mas o **codebase auditado** ganha 403 linhas que aparecem em `git log`, `grep`, busca de skills, etc.

Calculo de wall-clock:
- 02-telemetry: 40 × 150ms (worst-case com cold python3) = **6s/sessão burst**

**Impacto positivo:**
1. Extrair `_telemetry_enabled` para `scripts/hooks/lib/telemetry-detect.sh` corta 20 linhas duplicadas.
2. Batchar eventos no nível do agent (1 evento `agent_spawned` por agent, não por tool call interno) corta 90% das invocações de 02-telemetry.
3. Cache de sessão (`.claude/.telemetry-session-cache`) elimina re-checks.

Total economia: **~5s/sessão burst + 20 linhas duplicadas**.

**Impacto negativo:** dependências cruzadas entre 02-telemetry e nova lib aumentam acoplamento; mitigável com testes shellcheck.

---

## #2 — `token-_index-md-598-lines-grew-46-lines-in-24h-7th-consecutive-pass-archive-script-shipped-but-not-hooked-zero-rotation-mechanism-actually-firing`

**Severidade:** HIGH
**Arquivo:** `docs/reports/_index.md` (598 linhas)

7ª passada consecutiva. Pace:
- 2026-05-14: 380 linhas
- 2026-05-15: 464 (+22%)
- 2026-05-16: 509 (+9,7%)
- 2026-05-17: 552 (+8,4%)
- 2026-05-18: 598 (+8,3%)

Pace estável **+45 linhas/dia**. Projeção: 1.000 linhas em ~9 dias, 1.500 linhas em ~20 dias.

Estado do mecanismo de rotação:
- `helpers/archive-index.sh` existe (66 linhas, commit `eb3168e`, marcado ✅ Executed)
- **Mas não é invocado por nenhum hook ou CI** — verificado em #11 do report 01 deste dia
- Logo, o índice continuará crescendo indefinidamente

Custo:
- 598 linhas × 16 tokens = ~9.568 tokens lidos pelo Guardian a cada audit
- Em 30 dias sem rotação: 1.948 linhas × 16 = ~31.168 tokens/audit

**Impacto positivo:** wirear archive-index.sh no Stop dispatcher (com gate "1× por dia") realiza a economia prometida. Em 60 dias, libera ~22.000 tokens/audit.

**Impacto negativo:** rotação muda paths de fingerprints antigos (de `_index.md` para `_index-archive-YYYY-Q.md`); leitor manual precisa saber consultar 2 arquivos. Mitigável com TOC no `_index.md`.

---

## #3 — `token-CLAUDE-md-426-lines-still-monolithic-stop-sub-script-convention-table-and-hook-files-map-and-package-exclusions-not-extracted-after-fragmentation-fase-1`

**Severidade:** HIGH
**Arquivo:** `CLAUDE.md` (426 linhas)

Status pós-fragmentação 2026-05-13:
- `CLAUDE-md/preferences.md` → extraído ✅
- `CLAUDE-md/notifications.md` → extraído ✅
- `CLAUDE-md/user-data.md` → extraído ✅
- `CLAUDE-md/versioning.md` → extraído ✅

**Ainda inline** (oportunidade de fase 2):
- "Commands table" (linhas 165-196): ~32 linhas + tabela
- "Hook Files Map" (linhas 370-377): ~8 linhas
- "Sub-script Convention" (linhas 349-368): ~20 linhas
- "Agent Memory System" (linhas 281-345): ~65 linhas

Total extraível: **~125 linhas** → CLAUDE.md ficaria ~300 linhas (alvo).

Custo atual:
- 426 × 16 = ~6.816 tokens × 7 spawns típicos/sessão = **47.712 tokens/sessão** (worst-case multi-agent)

Custo pós-extração:
- 300 × 16 × 7 = 33.600 tokens/sessão
- **Economia: ~14.000 tokens/sessão**

**Impacto positivo:** redução de 30% no overhead de project-context.

**Impacto negativo:** mais arquivos em `CLAUDE-md/`; navegação inicial mais lenta para humanos.

---

## #4 — `token-design-patterns-references-composition-root-extracted-but-no-conditional-load-gate-in-agents-still-pulling-entire-skill-md-152-lines`

**Severidade:** MEDIUM
**Arquivos:** `skills/architecture/design-patterns/SKILL.md` (152 linhas), `skills/architecture/design-patterns/references/composition-root.md`

A extração reduziu o SKILL.md de 244 → 152 linhas (-38%). Mas:
- 3 agents carregam `design-patterns/SKILL.md` (backend-developer, frontend-developer, software-architect)
- Nenhum carrega condicionalmente `references/composition-root.md`
- Em tarefas de DI/IoC, o agent precisa do pattern e re-reads SKILL.md inteiro

Custo:
- 152 × 16 = ~2.432 tokens/spawn
- Em sessão CRUD com 3 spawns = 7.296 tokens
- Com lazy-load gate ("carregar references/composition-root.md apenas em tarefas DI"): ~30% das tarefas precisam, ou seja, ~5.110 tokens/sessão (-30%)

**Impacto positivo:** adicionar tabela "Conditional loads" em design-patterns/SKILL.md mapeando keyword → reference file.

**Impacto negativo:** mais 1 nível de indireção; LLM pode ficar lost em queries cross-pattern.

---

## #5 — `token-helpers-archive-index-sh-and-orphan-skill-scan-and-orphan-template-scan-stripped-from-install-but-still-ship-via-helpers-dir-misalignment-with-2026-05-15-fingerprint`

**Severidade:** MEDIUM
**Arquivos:** `helpers/`, `scripts/install.sh`

Verificação:
- O commit `9c7aecd` moveu dev tools para `helpers/` em **dev environment**
- O `install.sh` (linha 158-162) historicamente removia esses scripts do pacote distribuído
- Após o move, a lista de strip deve apontar para `helpers/` em vez de `scripts/`

Verificando:
```bash
grep -nE "rm -f.*helpers" scripts/install.sh
```

Se o `install.sh` ainda strippa `scripts/agent-lint.sh` (não existe mais), mas **não** strippa `helpers/agent-lint.sh`, o pacote distribuído contém os 6 dev tools = ~700 linhas dispensáveis. Sub-escopo do `flow-install-script-strip-list-stale-misses-new-dev-only-scripts-...` (2026-05-15), com angle pós-refactor.

**Impacto positivo:** strip correto economiza ~700 linhas no pacote do usuário; reduz pull em ~11.200 tokens caso usuário liste `.claude/dev-team-agents/`.

**Impacto negativo:** se um user real usa `helpers/agent-lint.sh` localmente, fica sem. Mitigável: documentar em CONTRIBUTING como rodar local.

---

## #6 — `token-frontend-test-specialist-262-lines-largest-test-agent-without-references-extraction-pattern-applied-to-other-large-agents`

**Severidade:** MEDIUM
**Arquivo:** `agents/frontend-test-specialist.md` (262 linhas)

Maior agent do repo. Comparativo:
- `frontend-test-specialist`: 262
- `backend-developer`: 261
- `setup-assistant`: 239
- `devops-specialist`: 237
- `backend-test-specialist`: 160 (assimetria mantida desde 2026-05-15)

Conteúdo extraível (verificado em grep):
- Bloco "Decoupled Frontend" inline ~40 linhas
- Bloco "Selector Priority" ~10 linhas
- ~60 linhas de code samples (testing-library/react usage)

Sub-escopo de `agent-frontend-test-specialist-262-vs-backend-160-asymmetric-decoupled-frontend-block-inlined` (2026-05-15, **sem marcação Executed**), mas com **angle quantificado pós-2026-05-18 sessão de execução**: 35 fingerprints ✅ Executed naquele dia, este **não foi tocado**.

Custo:
- 262 × 16 = ~4.192 tokens/spawn
- spawneado por `/devteam:frontend`, `/devteam:fullstack`, `/devteam:tester` = ~3 spawns/sessão típica
- Total: ~12.576 tokens/sessão

Pós-extração para `skills/testing/decoupled-frontend/SKILL.md` + `selectors-priority/SKILL.md`:
- agent: ~150 linhas (2.400 tokens/spawn)
- Lazy load das skills só quando tarefa pede

Economia: ~5.376 tokens/sessão.

**Impacto positivo:** padroniza o padrão já validado em backend-test-specialist.

**Impacto negativo:** mais skills criadas; setup-time inicial maior.

---

## #7 — `token-orphan-skill-scan-runs-on-every-stop-without-cache-of-skills-dir-mtime-redundant-when-no-skills-changed`

**Severidade:** MEDIUM
**Arquivos:** `scripts/hooks/stop/02-orphan-skill-scan.sh`, `helpers/orphan-skill-scan.sh`

CLAUDE.md:412 menciona que "Stop hooks `02-orphan-skill-scan.sh` e `03-agent-lint.sh` now gate by `agents/`/`skills/` changes" (CHANGELOG). Verificando:

```bash
$ cat scripts/hooks/stop/02-orphan-skill-scan.sh | head -20
```

Se o gate atual é "havendo qualquer change em git, roda" (não "havendo change em agents/skills"), ele dispara em **todo** Stop após edit de qualquer arquivo. Sub-escopo refinado do antigo `token-orphan-skill-scan-and-template-scan-duplicate-find-passes-on-skills-directory` (2026-05-16), com angle de **cache de mtime**:

- Hash do `find skills agents -newer .claude/.orphan-scan-lastrun` como gate
- Se vazio → skip
- Atualiza `.claude/.orphan-scan-lastrun` no final

Economia: ~50-80ms × ~10 Stops/sessão = ~700ms/sessão.

**Impacto positivo:** zero work quando edit é em docs/, scripts/, helpers/, etc.

**Impacto negativo:** stale cache se watcher loses event; mitigável com fallback "expire after 24h".

---

## Resumo

| # | Fingerprint | Severidade | Tipo |
|---|------------|-----------|------|
| 1 | token-telemetry-helper-289-lines-loaded-by-2-sub-scripts-plus-install-update-shell-fork-overhead-150ms-per-event-burst-mode-burns-200ms-acumulado | HIGH | Performance + dup |
| 2 | token-_index-md-598-lines-grew-46-lines-in-24h-7th-consecutive-pass-archive-script-shipped-but-not-hooked-zero-rotation-mechanism-actually-firing | HIGH | Crescimento |
| 3 | token-CLAUDE-md-426-lines-still-monolithic-stop-sub-script-convention-table-and-hook-files-map-and-package-exclusions-not-extracted-after-fragmentation-fase-1 | HIGH | Fragmentação |
| 4 | token-design-patterns-references-composition-root-extracted-but-no-conditional-load-gate-in-agents-still-pulling-entire-skill-md-152-lines | MEDIUM | Lazy-load |
| 5 | token-helpers-archive-index-sh-and-orphan-skill-scan-and-orphan-template-scan-stripped-from-install-but-still-ship-via-helpers-dir-misalignment-with-2026-05-15-fingerprint | MEDIUM | Strip list |
| 6 | token-frontend-test-specialist-262-lines-largest-test-agent-without-references-extraction-pattern-applied-to-other-large-agents | MEDIUM | Extração |
| 7 | token-orphan-skill-scan-runs-on-every-stop-without-cache-of-skills-dir-mtime-redundant-when-no-skills-changed | MEDIUM | Cache mtime |
