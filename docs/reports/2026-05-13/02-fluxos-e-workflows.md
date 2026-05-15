# Relatório — Fluxos e Workflows (2026-05-13)

Auditoria focada em **gaps de fluxos, comandos novos, hooks e fricção operacional**. Todas as sugestões são **originais** ao `_index.md`. Foco especial nos batches `flow-*` e `auto-*`.

---

## 1. `flow-pre-compact-hook-no-graceful-skip-when-claude-dir-absent`

**Severidade:** 🟠 Alta — pode quebrar flow em projeto recém-clonado

**Detecção:** Commit `57dc8ca` criou `scripts/hooks/pre-compact.sh`. Linha 24-28:

```bash
SUMMARY_FILE=".claude/user-data/session-summary.md"

if [ ! -f "$SUMMARY_FILE" ] || ! grep -q "^## $TODAY" "$SUMMARY_FILE" 2>/dev/null; then
    cat >&2 <<EOF
    SESSION SUMMARY REQUIRED (pre-compact)
```

Cenários onde isso falha silenciosamente ou ruidosamente:
1. **Projeto sem `.claude/user-data/`**: o `[ ! -f "$SUMMARY_FILE" ]` é verdadeiro → emite warning incorreto (não há sessão pra resumir).
2. **Projeto onde `dev-team-agents` foi instalado mas `.gitignore` ainda não tem `.claude/user-data/`**: usuário nunca rodou setup-assistant → `user-data/` não existe.
3. **Múltiplos worktrees**: cada worktree tem seu próprio `.claude/`; pre-compact pode rodar em worktree A e procurar `user-data/` que está em worktree B.

A linha 7 já guarda contra non-git: `git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0`. Falta guarda para "git repo válido mas sem `.claude/user-data/`".

**Impacto positivo (se corrigido):** elimina falso-positivo em projetos recém-clonados; pre-compact não emite ruído desnecessário.

**Impacto negativo (se mantido):** novo usuário roda PreCompact (compactação automática) e vê warning sobre session-summary que ele nunca configurou; experiência hostil.

**Sugestão:** adicionar guarda antes da checagem do summary:

```bash
[ -d ".claude/user-data" ] || exit 0
```

---

## 2. `flow-pr-command-no-base-branch-detection-from-repo-config`

**Severidade:** 🟡 Média

**Detecção:** `commands/pr.md` Step 0a faz fallback para detectar base branch via `git log --oneline -10 main` (assume `main`). Em repos antigos com `master`, ou repos com convenção `develop`/`trunk`, esse comando falha silenciosamente. Não há fallback para:

```bash
# Detect repo's default branch
DEFAULT_BRANCH=$(git config init.defaultBranch 2>/dev/null \
                 || git remote show origin | awk '/HEAD branch/ {print $NF}' \
                 || echo "main")
```

Antigo fingerprint `flow-no-stale-branch-detection` (2026-05-10, ✅ Executed) abordava detecção de branch atrasada, mas não detecção do **nome** do default branch.

**Impacto positivo (se corrigido):** PR command funciona em repos `master`/`develop`/custom; não falha em mid-flight.

**Impacto negativo (se mantido):** `/devteam:pr` em projeto legado (master) gera diff vazio ou entra em fluxo confuso.

**Sugestão:** prepend Step 0 em `commands/pr.md`:

```markdown
**Step 0 — Detect default branch:**
DEFAULT_BRANCH=$(gh repo view --json defaultBranchRef -q '.defaultBranchRef.name' 2>/dev/null \
              || git config init.defaultBranch \
              || git remote show origin | awk '/HEAD branch/{print $NF}' \
              || echo "main")
```

E usar `$DEFAULT_BRANCH` em vez de `main` no resto do comando.

---

## 3. `flow-current-context-cache-no-invalidation-on-branch-switch-within-ttl-window`

**Severidade:** 🟠 Alta — cache pode mentir sobre branch ativa

**Detecção:** `skills/shared/current-context/SKILL.md` linhas 60-78 implementam cache TTL 300s em `.claude/user-data/.context-cache.json`. Schema:

```json
{ "ts": <unix-epoch-seconds>, "branch": "...", "changed": N, "worktree": "yes|no" }
```

A leitura não compara branch atual com `branch` do cache:

```bash
[ "$age" -lt 300 ] && echo "Context (cached): $(cat $CACHE)" && exit 0
```

Cenário: usuário roda agente A em branch `feature/foo`, cache escreve `branch=feature/foo`. Em ≤300s, faz `git checkout main` e roda agente B → cache ainda válido por TTL → agente B opera achando que está em `feature/foo`. **Branch detection falsa**.

**Impacto positivo (se corrigido):** cache nunca mente sobre branch ativa; mantém ganho de TTL para os outros campos.

**Impacto negativo (se mantido):** durante quick agent-hopping (típico em devteam multi-spawn), branch detection desatualiza silenciosamente; risco de operação no scope errado.

**Sugestão:** ler branch atual antes de servir cache:

```bash
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)
if [ -f "$CACHE" ] && [ -n "$CURRENT_BRANCH" ]; then
    cached_branch=$(python3 -c "import json; print(json.load(open('$CACHE'))['branch'])" 2>/dev/null || echo "")
    if [ "$cached_branch" = "$CURRENT_BRANCH" ] && [ "$age" -lt 300 ]; then
        echo "Context (cached): …" && exit 0
    fi
fi
```

---

## 4. `flow-design-command-no-frontend-developer-spawn-for-implementation`

**Severidade:** 🟡 Média

**Detecção:** `cat commands/design.md` mostra que `/devteam:design` spawna **apenas** `ui-ux-designer`:

```
- `ui-ux-designer` … design system, component design, UX flows, visual decisions
```

Para fluxos onde o usuário pede "redesign this signup flow and ship", o ui-ux-designer produz design specs mas **ninguém implementa**. Não há cross-link para `frontend-developer` (mesmo condicional). Asimetria com `/devteam:plan` (que spawna 4-6 agents) e `/devteam:fullstack`.

**Impacto positivo (se corrigido):** `/devteam:design` pode terminar em código se o usuário quiser; sem fricção de ter que mudar de slash command no meio do fluxo.

**Impacto negativo (se mantido):** design vira artifact desconectado; usuário tem que abrir `/devteam:frontend` separadamente para implementar.

**Sugestão:** adicionar spawn condicional:

```
Also spawn if the task includes implementation (default: design spec only):
- `frontend-developer` … implement the design changes (HTML/CSS/JS, component code)
```

E flag `$ARGUMENTS contains "implement"` para ativar.

---

## 5. `flow-installer-no-shellcheck-self-validation-on-its-output`

**Severidade:** 🟡 Média — dogfooding gap

**Detecção:** `.github/workflows/ci.yml` step `Shellcheck scripts` roda:

```yaml
- name: Shellcheck scripts
  run: find scripts -name '*.sh' -exec shellcheck {} +
```

Porém:
1. `scripts/install.sh` (503 linhas) usa heredocs e dynamic content — shellcheck não detecta erros nesse padrão.
2. O **resultado pós-install** (arquivos sob `.claude/dev-team-agents/scripts/`) nunca é validado. Se install.sh introduzir um erro de variável escapada que só aparece após substituição dinâmica, CI passa mas usuários quebram.

**Impacto positivo (se corrigido):** valida o resultado real (não só o source); detecta regressões em heredoc/sed substitutions.

**Impacto negativo (se mantido):** install.sh pode "passar" CI mas gerar scripts quebrados em runtime.

**Sugestão:** adicionar CI step:

```yaml
- name: Validate installed scripts
  run: |
    bash scripts/install.sh --target /tmp/test-install --no-network
    find /tmp/test-install/.claude/dev-team-agents/scripts -name '*.sh' -exec shellcheck {} +
```

(Requer suporte a `--target` e `--no-network` no install.sh — pequeno refactor.)

---

## 6. `flow-conventional-commits-validate-script-no-husky-or-commit-msg-hook-registration`

**Severidade:** 🟡 Média — sub-escopo de fingerprint #2 do relatório de Referências

**Detecção:** `scripts/validate-commit-msg.sh` existe mas:
- `install.sh` não registra um `commit-msg` git hook que o invoque.
- Nenhum `package.json` `husky.hooks` ou `lefthook.yml` é gerado pelo setup-assistant.

Resultado: o script só vale se o usuário rodar manualmente. Em projetos com Husky/Lefthook já configurados, nada é integrado.

**Impacto positivo (se corrigido):** validação automática a cada `git commit` localmente; reduz fricção do reviewer.

**Impacto negativo (se mantido):** `validate-commit-msg.sh` é "documentação executável" sem consumidor real.

**Sugestão:** estender setup-assistant com pergunta opt-in:

> "Detectei [Husky | Lefthook | nenhum hook manager]. Quer que eu registre `validate-commit-msg.sh` como `commit-msg` hook? (yes / no)"

E gerar:
- Husky: `npx husky add .husky/commit-msg 'bash .claude/dev-team-agents/scripts/validate-commit-msg.sh "$(cat $1)"'`
- Lefthook: bloco em `lefthook.yml`.
- Sem manager: `cp scripts/validate-commit-msg.sh .git/hooks/commit-msg && chmod +x ...`.

---

## 7. `flow-stop-hook-04-notifier-no-skip-when-no-changes-via-fast-path-flag`

**Severidade:** 🟡 Média — sub-escopo de `flow-stop-dispatcher-runs-all-4-sub-scripts-without-fast-path` (✅ Executed em 2026-05-13)

**Detecção:** Commit `f96f3cd` adicionou `DEVTEAM_NO_CHANGES=1` fast-path em `01-session-summary.sh`, `02-orphan-skill-scan.sh`, `03-agent-lint.sh`. Porém `04-notifier.sh` **não** respeita esta flag — sempre roda para incrementar turn-counter.

Em sessões puramente conversacionais (sem mudanças), `04-notifier.sh` ainda paga ~50ms por Stop para incrementar turn. Sub-escopo: a quase-totalidade dos turns conversacionais não precisam emitir notificação (só o limiar % do warning matters).

**Impacto positivo (se corrigido):** sessões 100% conversacionais ficam ~50ms mais rápidas por Stop.

**Impacto negativo (se mantido):** ganho do fast-path é parcial; notifier executa Python+jq mesmo sem necessidade.

**Sugestão:** detectar "no-context-change" via `DEVTEAM_NO_CONTEXT_CHANGE` (nova flag computada no dispatcher comparando turn token estimate vs. last) e early-exit no 04-notifier também. Trade-off: complexidade adicional vs ganho marginal — talvez não vale a pena.

---

## 8. `flow-rollback-no-pre-state-validation-vs-update-sh`

**Severidade:** 🟡 Média

**Detecção:** `scripts/rollback.sh` re-baixa o installer e o executa. Mas não valida:
1. Se a versão atual já é `$TARGET` (rollback no-op).
2. Se há mudanças locais não commitadas em `.claude/dev-team-agents/` (que serão sobrescritas).
3. Se o usuário tem rollback _ao mesmo_ tag em curso (race condition).

`scripts/update.sh` tampouco valida (1) e (2). Risco simétrico.

**Impacto positivo (se corrigido):** rollback fica idempotente; usuário sabe que ação será destrutiva antes de executar.

**Impacto negativo (se mantido):** rollback duas vezes seguidas re-baixa e re-extrai pacote (waste); modificações locais perdidas silenciosamente.

**Sugestão:** prepend em rollback.sh:

```bash
CURRENT=$(cat "$CURRENT_VERSION_FILE" 2>/dev/null || echo "unknown")
if [ "$CURRENT" = "$TARGET" ]; then
    echo "→ Already at $TARGET; nothing to do."
    exit 0
fi

# Warn about local modifications
if [ -d "$INSTALL_DIR/.git" ] || git -C "$INSTALL_DIR" status --porcelain 2>/dev/null | grep -q .; then
    echo "⚠ Local modifications detected in $INSTALL_DIR. They will be lost."
    echo "  Continue? (y/N)"
    read -r ANSWER
    [ "$ANSWER" = "y" ] || exit 1
fi
```

---

## 9. `flow-installer-strips-validate-commit-msg-not-but-keeps-it-vs-other-dev-tools`

**Severidade:** 🟡 Média — inconsistência de classificação

**Detecção:** `grep "rm -f" scripts/install.sh` revela:

```bash
rm -f  "$EXTRACTED_ROOT/scripts/orphan-skill-scan.sh" # dev tool for this repo only
rm -f  "$EXTRACTED_ROOT/scripts/agent-lint.sh"        # dev tool for this repo only
rm -f  "$EXTRACTED_ROOT/scripts/size-limits.sh"       # dev tool for this repo only
```

Porém `scripts/validate-commit-msg.sh` **não é stripado**, enquanto `agent-lint.sh` e `size-limits.sh` são. Critério: "dev tool for this repo only" — mas `validate-commit-msg.sh` também é referenciado apenas por skill `conventional-commits` que documenta uso no projeto destino. Falta clareza:
- Se é dev-only: deveria ser stripado.
- Se é user-facing: deveria ser referenciado por algum command/skill loaded path.

CLAUDE.md "Package exclusions" tabela não menciona `validate-commit-msg.sh`.

**Impacto positivo (se corrigido):** classificação clara e documentada; `install.sh` consistente.

**Impacto negativo (se mantido):** ambiguidade futura sobre qual script vai/fica; risco de strip equivocado.

**Sugestão:** decidir e documentar:
- **Opção A:** keep no projeto destino + adicionar entrada em "Package inclusions/exclusions" da CLAUDE.md + wirear a `commands/commit.md`.
- **Opção B:** strip + remover referência da `conventional-commits/SKILL.md` ou apontar para shell function inline.

---

## 10. `flow-orphan-skill-scan-warn-output-not-silenced-in-quiet-mode`

**Severidade:** 🟢 Baixa — fingerprint específico de UX

**Detecção:** `bash scripts/orphan-skill-scan.sh --quiet` esperaria **silêncio** quando há WARNs (não ACTION REQUIREDs). Comportamento atual:

```bash
$ bash scripts/orphan-skill-scan.sh --quiet
# (output ainda aparece se há WARNs)
```

A flag `--quiet` foi originalmente projetada para "silent on success when possible" (CLAUDE.md scripts standards). WARNs caem em zona cinzenta: não são erros, mas também não são success.

**Impacto positivo (se corrigido):** Stop hook sob `--quiet` não polui; usuário vê WARNs apenas em scan manual.

**Impacto negativo (se mantido):** WARNs aparecem a cada Stop em projetos com duplicate loads (todos os 8 agents/5 commands hoje), até serem corrigidos.

**Sugestão:** redefinir semântica:
- `--quiet` suprime success messages mas mantém WARNs e ERRORs.
- `--super-quiet` ou `--errors-only` para suprimir tudo exceto ACTION REQUIRED.

E usar `--errors-only` no Stop hook.

---

## Resumo

| Prioridade | Quantidade |
|-----------|-----------|
| 🟠 Alta | 2 (`pre-compact-no-graceful-skip`, `current-context-cache-branch-invalidation`) |
| 🟡 Média | 7 |
| 🟢 Baixa | 1 |

**Padrões emergentes desta passada:**

- **Hooks novos sem validação de ambiente** — `pre-compact.sh` foi adicionado sem guarda para projetos sem `.claude/user-data/`. Padrão repete-se em scripts que assumem layout do projeto destino.
- **Cache sem invalidação semântica** — `.context-cache.json` foi excelente para reduzir overhead de git, mas falta camada de validação cross-attribute (branch, commit hash).
- **Scripts criados mas não wireados** — terceira passada consecutiva onde um script novo (`validate-commit-msg.sh`) foi criado mas sem pipeline de uso real (CI, hook, command).
