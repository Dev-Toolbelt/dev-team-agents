# Relatório - Fluxos e Workflows - 2026-05-14

**Data:** 2026-05-14 — Nona passada (9ª) — 10 sugestões originais

Foco do dia: governança de regras novas (quiz-first sem lint), gaps em scripts pós-mudança de path (context-cache), assimetrias de hooks (rollback vs refactor), debt acumulada (notifier sem fast-path, fingerprint collision check pendente), efeitos colaterais de commits do dia 2026-05-13 (spawn-classifier, plan-mode, pr).

---

### 🔴 1. Quiz-first Rule sem validação no lint — adoção fica a critério do autor

**Fingerprint:** `flow-quiz-first-rule-no-lint-validation-of-askuserquestion-adoption`

**Evidência:** Commit `d05242a` (2026-05-14) adicionou skill `interaction-patterns` (185 linhas) e CLAUDE.md L141 declara: "All agents and commands must use the AskUserQuestion tool whenever asking the user a question with a finite set of reasonable answers". `scripts/agent-lint.sh` (158 linhas, fact-finding §1.5) **não** valida ausência de literais `(yes/no)`, `(y/n)`, `(a/b/c)` em agents/commands.

**Por quê importa:** Regra mandatória sem enforcement automatizado é regra opcional na prática. Setup-assistant, commit, pr e adr ainda usam prompts inline.

**Impacto positivo da correção:** Lint impede regressão; autor recebe feedback no momento da escrita; adoção propaga sem campanha manual.

**Impacto negativo / risco:** Falsos positivos em strings dentro de exemplos de código (markdown inside agent body).

**Sugestão concreta:** Adicionar regex `\([yY]es?[/ ][nN]o?\)` e `\([y][/][n]\)` em `agent-lint.sh` com whitelist por bloco code-fenced; emitir warning + sugerir `Load skills/shared/interaction-patterns/SKILL.md`.

---

### 🟡 2. `.context-cache.json` movido para `user-data/` mas update.sh/rollback.sh não invalidam cache stale

**Fingerprint:** `flow-context-cache-moved-to-user-data-but-no-cleanup-script-for-stale-cache-on-version-bump`

**Evidência:** Commit `ac6af24` (2026-05-13) moveu `.context-cache.json` para `.claude/user-data/` (CLAUDE.md L283 lista o arquivo como gitignored). `scripts/update.sh` (76 linhas) e `scripts/rollback.sh` (65 linhas) não removem o cache pós-update. Versionar muda paths/skills mas o cache pode apontar para arquivos extintos.

**Por quê importa:** Após `update.sh` rodar e instalar v1.3 sobre v1.2, cache de current-context (TTL 300s) ainda válido pode referenciar paths obsoletos da v1.2; primeira invocação pós-update pega snapshot inválido.

**Impacto positivo da correção:** Cache invalidado proativamente em mudança de versão; primeira invocação pós-update sempre gera contexto fresco.

**Impacto negativo / risco:** Re-detecção custa ~5-10s mas paga uma vez por update (≈ semanal).

**Sugestão concreta:** Adicionar `rm -f .claude/user-data/.context-cache.json` no final de `update.sh` e `rollback.sh` (após swap de versão); idempotente, custo zero.

---

### 🟡 3. `rollback.sh` sem `git tag pre-rollback-<version>` — assimétrico vs refactor workflow

**Fingerprint:** `flow-rollback-sh-no-pre-rollback-tag-creation`

**Evidência:** `scripts/rollback.sh` (65 linhas) imediatamente reinstala versão alvo. Compare com `workflows/refactor.md` (commit `2746c7c`/2026-05-13) que cria `git tag pre-refactor-<scope>` antes de tocar arquivos. Rollback de versão é mudança igualmente arriscada (substitui ~150 arquivos em `.dev-team-agents/`).

**Por quê importa:** Se rollback corromper algo, não há checkpoint físico para `git reset --hard pre-rollback-vX.Y.Z`. Assimetria operacional: refactor lógico tem safety net; rollback de versão não.

**Impacto positivo da correção:** Recovery determinístico em caso de regressão pós-rollback.

**Impacto negativo / risco:** Tag adicional em cada rollback polui `git tag --list`; mitigado por padrão `pre-rollback-*` filtrável.

**Sugestão concreta:** Em `rollback.sh` antes do download/swap: `git tag "pre-rollback-$(cat .claude/user-data/.installed-version 2>/dev/null || echo unknown)" 2>/dev/null || true`.

---

### 🟡 4. `pre-compact.sh` (49 linhas) não consta na tabela CLAUDE.md "Stop Sub-script Convention"

**Fingerprint:** `flow-pre-compact-hook-49-lines-but-not-listed-in-claude-md-stop-hook-section`

**Evidência:** Commit `57dc8ca` adicionou `scripts/hooks/pre-compact.sh` (49 linhas, fact-finding §1.5). CLAUDE.md "Stop Sub-script Convention" (linhas 247-256 e 408-417) lista convenção `01-` a `99-` para `stop/` — sem nenhuma menção a `pre-compact.sh`. Hook é evento separado (`PreCompact`), mas a estrutura conceitual é gêmea.

**Por quê importa:** Quem ler CLAUDE.md fica com impressão de que apenas Stop tem hooks de session-summary; pre-compact passa invisível. Documentação incompleta para quem precisa adicionar nova lógica de pre-compact.

**Impacto positivo da correção:** Mapeamento explícito de eventos hook → arquivos hook → propósitos.

**Impacto negativo / risco:** Adiciona mais 5-10 linhas em CLAUDE.md (já 557 linhas — vide report 01).

**Sugestão concreta:** Adicionar pequena tabela em CLAUDE.md "Hook Files Map" listando os 4 hooks (session-start, pre-tool-use, pre-compact, stop) com linhas, propósito e dispatcher se aplicável; manter em ≤8 linhas.

---

### 🔴 5. Sem fingerprint uniqueness check — `_index.md` em 380 linhas com risco de duplicate slugs

**Fingerprint:** `flow-no-fingerprint-uniqueness-check-script-_index-now-380-lines`

**Evidência:** `auto-no-fingerprint-collision-check` (2026-05-08, pendente — vide _index.md L329). Verificação de hoje: `_index.md` ~408 linhas (medido durante leitura — fact-finding §7); estatísticas mostram 279 fingerprints acumulados em 2026-05-13 + 40 hoje = 319 fingerprints. Sem script `unique` check, autor de relatório (Claude ou humano) pode reusar slug e silenciosamente sobrescrever histórico.

**Por quê importa:** O índice é sistema de memória institucional; collision = memória corrompida. Quanto maior, maior o risco e mais difícil detectar manualmente.

**Impacto positivo da correção:** Fingerprint duplicado é falha de CI antes do commit; histórico permanece confiável.

**Impacto negativo / risco:** Custo de CI: ~100ms para `awk -F'`' '{print $2}' _index.md | sort | uniq -d`.

**Sugestão concreta:** Criar `scripts/check-fingerprint-uniqueness.sh` (10-15 linhas) que faz `grep -oE '` `[a-z][a-z0-9-]+` `' docs/reports/_index.md | sort | uniq -d`; exit 1 se non-empty; rodar em `.github/workflows/ci.yml` no push para main.

---

### 🟢 6. Quiz-first aplicado em update.md mas sem quiz para confirmar abort de rollback

**Fingerprint:** `flow-update-command-quiz-first-applied-but-no-rollback-prompt-quiz`

**Evidência:** Commit `ba19882` (2026-05-14) aplicou quiz-first em `commands/update.md` (140 linhas — fact-finding §1.2). Verificação em `scripts/rollback.sh` e `commands/update.md` (busca por "rollback"): rollback flow não pergunta confirmação via AskUserQuestion. Apenas executa.

**Por quê importa:** Update tem confirmation explícita; rollback (operação mais destrutiva) não tem. Inconsistência interativa.

**Impacto positivo da correção:** UX consistente — operações destrutivas sempre precedidas de quiz.

**Impacto negativo / risco:** Adiciona um round-trip; usuários experientes podem achar verboso.

**Sugestão concreta:** Em `commands/update.md` ou wrapper futuro de rollback, AskUserQuestion `"Confirma rollback para v<X>? Mudanças locais em .dev-team-agents/ serão sobrescritas"` com opções [Yes / No / Show diff first].

---

### 🟡 7. Orphan-skill-scan estendido mas CI não roda em quiet mode

**Fingerprint:** `flow-orphan-skill-scan-extended-but-still-no-skill-orphans-from-ci-mode`

**Evidência:** Commit `19de0e1` (2026-05-13) estendeu `orphan-skill-scan.sh` para cobrir commands/ e workflows/ como consumidores. `.github/workflows/ci.yml`: verificação confirma que CI **não** invoca `bash scripts/orphan-skill-scan.sh --quiet`. Apenas Stop hook local roda. Resultado: PR pode mergear introduzindo skill órfã (caso `security-checklist` é exemplo, vide report 01 #5).

**Por quê importa:** Single-point detection (Stop hook) só protege quem rodou Claude Code localmente; PR de colaborador externo via CI passa.

**Impacto positivo da correção:** Detection paralela em CI; orphan introduzido por PR é falha imediata.

**Impacto negativo / risco:** Pode gerar warning histórico (security-checklist atual); resolver primeiro o backlog.

**Sugestão concreta:** Adicionar step em `.github/workflows/ci.yml`: `- name: Orphan skill scan` rodando `bash scripts/orphan-skill-scan.sh --quiet`; tornar fail-on-warn opcional via env var até backlog limpar.

---

### 🟡 8. `04-notifier.sh` sem fast-path — overhead persistente em sessões puramente conversacionais

**Fingerprint:** `flow-no-stop-hook-04-notifier-fast-path-still-after-2026-05-13`

**Evidência:** Sub-escopo do pendente `flow-stop-hook-04-notifier-no-skip-when-no-changes-via-fast-path-flag` (2026-05-13). Guardian §`flow-stop-hook-04...`: `grep -n "DEVTEAM_NO_CHANGES\|fast-path" scripts/hooks/stop/04-notifier.sh` retorna **0 hits**. Sub-scripts 01-03 já adotaram via commit `f96f3cd`. Quantificação: ~50ms × 30 turns/sessão = **1,5s/sessão** desperdiçado em sessões sem changes.

**Por quê importa:** Overhead pequeno mas multiplicador (10 sessões/dia × 1,5s = 15s/dia/desenvolvedor; 100 devs = 25min/dia agregado). Tip-of-day computation é o maior custo em 04-notifier.

**Impacto positivo da correção:** -73% em sessões read-only (mesma medida das 01-03); paridade arquitetural com sub-scripts irmãos.

**Impacto negativo / risco:** Tip-of-day pode pular dia se sessões forem puramente conversacionais (mitigado: tip não é critical-path).

**Sugestão concreta:** Adicionar early-exit em `04-notifier.sh`: `[ "${DEVTEAM_NO_CHANGES:-false}" = "true" ] && [ "$(date +%j)" = "$(cat $TIP_STATE_FILE 2>/dev/null)" ] && exit 0`.

---

### 🟡 9. `pr.md` valida Conventional Commits mesmo em projetos que usam outros formatos

**Fingerprint:** `flow-pr-command-validates-conventional-commits-but-not-on-detected-non-cc-projects`

**Evidência:** Commit `e0e8983` (2026-05-13) adicionou Step 0a "Conventional Commits pre-flight" em `commands/pr.md` (61 linhas — fact-finding §1.2). CLAUDE.md "Commit Rule" (~L460): "Defer to the project's own pattern first: run `git log --oneline -10` and check whether the existing history follows Conventional Commits or a different format (e.g., GitHub-style `[feature]`...)". Verificação em `commands/pr.md`: pre-flight valida CC sem checar histórico do projeto primeiro.

**Por quê importa:** Em projeto que usa `[feature] descrição` por convenção, pre-flight do `/devteam:pr` reportará "não-conformidade" para commits que estão corretos pelo padrão local. Contradiz a regra coexistence (CLAUDE.md L552).

**Impacto positivo da correção:** Comando respeita convenção do projeto; falsos positivos eliminados.

**Impacto negativo / risco:** Detection heurística pode classificar errado; necessita 2-3 amostras para confiança.

**Sugestão concreta:** Em `pr.md` Step 0a, antes de validar contra CC: rodar `git log --oneline -10 | grep -cE "^[a-f0-9]+ (feat|fix|chore|docs|style|refactor|perf|test|build|ci)(\(.+\))?:"`; se ratio < 50%, skip pre-flight com warning informativo "Project not following CC — skipping validation".

---

### 🟡 10. spawn-classifier loadeada por 7 commands sem caching de output

**Fingerprint:** `flow-spawn-classifier-loaded-by-7-commands-but-no-classifier-output-cached`

**Evidência:** Commit `3f98f26` (2026-05-13) carregou spawn-classifier em 7 commands (backend, fix, frontend, fullstack, plan, refactor, review — fact-finding §8 + Guardian §`flow-spawn-classifier...`). Cada invocação re-roda lógica de classificação (parsing de diff, decision tree). Em fluxo `/devteam:fullstack` que internamente chama backend e frontend, classificação roda 3 vezes contra o mesmo working tree.

**Por quê importa:** Trabalho duplicado em multi-agent. Não é crítico mas aumenta latência percebida.

**Impacto positivo da correção:** Cache em `.claude/user-data/.spawn-classifier-cache.json` (TTL 60s ou hash do diff) elimina re-execução.

**Impacto negativo / risco:** Cache stale entre branches; mitigar com TTL curto + hash do `git rev-parse HEAD`.

**Sugestão concreta:** Adicionar em spawn-classifier output JSON com chave `{branch, head_sha, decision, ts}`; commands reutilizam se `head_sha` corresponde e age < 60s.

---

## Síntese — ordem de prioridade

1. **🔴 #1** — `flow-quiz-first-rule-no-lint-validation-of-askuserquestion-adoption` (regra nova sem enforcement)
2. **🔴 #5** — `flow-no-fingerprint-uniqueness-check-script-_index-now-380-lines` (memória institucional em risco, 5ª passada)
3. **🟡 #2** — `flow-context-cache-moved-to-user-data-but-no-cleanup-script-for-stale-cache-on-version-bump`
4. **🟡 #7** — `flow-orphan-skill-scan-extended-but-still-no-skill-orphans-from-ci-mode`
5. **🟡 #3** — `flow-rollback-sh-no-pre-rollback-tag-creation`
6. **🟡 #8** — `flow-no-stop-hook-04-notifier-fast-path-still-after-2026-05-13`
7. **🟡 #9** — `flow-pr-command-validates-conventional-commits-but-not-on-detected-non-cc-projects`
8. **🟡 #4** — `flow-pre-compact-hook-49-lines-but-not-listed-in-claude-md-stop-hook-section`
9. **🟡 #10** — `flow-spawn-classifier-loaded-by-7-commands-but-no-classifier-output-cached`
10. **🟢 #6** — `flow-update-command-quiz-first-applied-but-no-rollback-prompt-quiz`
