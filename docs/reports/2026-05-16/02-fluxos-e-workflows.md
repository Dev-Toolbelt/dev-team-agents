# Fluxos e Workflows — 2026-05-16

> Auditoria de fluxos automatizados (hooks, dispatchers, CI gates), commands, e workflows. Foco: bugs ocultos em scripts, gaps de modularização, regressões silenciosas após "fixes" anteriores.

---

## 1. `flow-stop-04-notifier-fast-path-string-comparison-broken-DEVTEAM_NO_CHANGES-1-vs-true` — CRITICAL

**Arquivos:**
- `scripts/hooks/stop.sh:18-31` (dispatcher exporta a flag)
- `scripts/hooks/stop/04-notifier.sh:88` (consumidor)

**Observação:** o dispatcher exporta `DEVTEAM_NO_CHANGES=1` (numérico):

```bash
DEVTEAM_NO_CHANGES=0
if git rev-parse --is-inside-work-tree &>/dev/null 2>&1; then
    if git diff --quiet 2>/dev/null && git diff --cached --quiet 2>/dev/null; then
        TODAY=$(date +%Y-%m-%d)
        if ! git log --oneline --since="${TODAY} 00:00:00" --format="%h" 2>/dev/null | grep -q .; then
            DEVTEAM_NO_CHANGES=1
        fi
    fi
fi
export DEVTEAM_NO_CHANGES
```

Sub-scripts 01-03 verificam corretamente:

```bash
[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0   # CORRETO
```

Mas `04-notifier.sh:88`:

```bash
if [ "${DEVTEAM_NO_CHANGES:-false}" = "true" ] && [ "${STATE_DATE:-}" = "${TODAY:-}" ]; then
    exit 0
```

**A comparação `"1" = "true"` sempre falha.** O fast-path do notifier **nunca dispara**. Verificado:

```bash
$ DEVTEAM_NO_CHANGES=1 bash -c '[[ "${DEVTEAM_NO_CHANGES:-false}" = "true" ]] && echo YES || echo NO'
NO
```

**Histórico revisitado:**
- Fingerprint `flow-no-stop-hook-04-notifier-fast-path-still-after-2026-05-13` (2026-05-14) foi marcado ✅ Executed.
- A marcação foi feita por **presença de código** (alguém adicionou o `if`), não por **execução correta** do código.
- Spot-check de Guardian falhou em pegar — não havia teste de execução.

**Consequência prática:** sessão puramente conversacional (sem alteração de arquivo, sem commit hoje) executa as 240 linhas de `04-notifier.sh` em toda Stop call: leitura de `preferences.json`, parse de transcript, cálculo de tokens, mensagem-tip aleatória. Overhead estimado: ~80-150ms/Stop × 30 turns = **~3-4,5s/sessão desperdiçados**.

**Impacto positivo do fix:** trocar `"true"` por `"1"` (4 caracteres) — alinha com sub-scripts 01-03 e com o que o dispatcher exporta. **Reabrir** marcação anterior para ⚠️ Partial até teste de execução confirmar.

**Impacto negativo do fix:** zero — bug fix puro.

---

## 2. `flow-stop-no-zombie-state-cleanup-discovery-lock-and-worktree-session-persist-across-sessions` — MEDIUM

**Arquivos relevantes:**
- `.claude/.discovery-lock` (criado por `skills/shared/discovery-mode/SKILL.md`)
- `.dev-team-agents/.worktree-session` (criado por agentes coding e workflows)
- `scripts/hooks/stop.sh` (dispatcher)

**Observação:** dois arquivos de estado de sessão são criados durante execução:

| Arquivo | Criado por | Propósito |
|---------|-----------|-----------|
| `.claude/.discovery-lock` | discovery-mode skill | Lock cooperativo entre 3 agents concorrentes |
| `.dev-team-agents/.worktree-session` | coding agents | Decisão "yes/no" para worktree, ler 1× por sessão |

Ambos têm "regra de cleanup" documentada (discovery: > 30min stale; worktree-session: "ler 1× por sessão") mas **nenhum hook executa essa limpeza**.

Sequência típica de bug:
1. Sessão A: `setup-assistant` cria `.claude/.discovery-lock` em 14:30. Crash do Claude antes do trap cleanup.
2. Sessão B: 18:00. `software-architect` tenta lock → encontra arquivo "fresh" (TTL ainda válido até 19:00) → fail-fast.
3. Usuário precisa `rm -f .claude/.discovery-lock` manual.

Para `.worktree-session`:
1. Sessão A: usuário escolhe `worktree=yes branch=main`. Branch é deletada manualmente.
2. Sessão B: agent lê `.dev-team-agents/.worktree-session`, segue silenciosamente, tenta criar worktree em branch inexistente → erro tardio.

**Por que importa:**
- Sintomas atribuídos a "bug do dev-team-agents" quando na verdade são stale state.
- Discovery lock especialmente difícil de diagnosticar (skill já é nova, fingerprint `skill-discovery-mode-three-agents-need-explicit-collision-protocol` de 2026-05-12 foi marcado ✅ via lockfile, mas cleanup não foi parte do escopo).

**Impacto positivo do fix:** novo sub-script `scripts/hooks/stop/00-state-cleanup.sh` (~15 linhas):
```bash
LOCK=".claude/.discovery-lock"
if [ -f "$LOCK" ]; then
  AGE_MIN=$(( ( $(date +%s) - $(stat -c %Y "$LOCK") ) / 60 ))
  [ "$AGE_MIN" -gt 30 ] && rm -f "$LOCK"
fi
# (similar para .worktree-session com TTL maior, ex.: 8h)
```
Auto-rotação evita necessidade de intervenção manual.

**Impacto negativo do fix:** +15 linhas em hook que roda toda Stop; gated por `DEVTEAM_NO_CHANGES=1` evita overhead em sessões conversacionais.

---

## 3. `flow-pre-tool-use-01-check-updates-195-lines-3rd-largest-script-no-fragmentation` — MEDIUM

**Arquivo:** `scripts/hooks/pre-tool-use/01-check-updates.sh` (195 linhas)

**Observação:** Top 5 scripts por tamanho:

| Script | Linhas | Responsabilidade |
|--------|--------|------------------|
| `scripts/install.sh` | 503 | Instalação completa |
| `scripts/hooks/stop/04-notifier.sh` | 240 | Notificação fim de sessão |
| `scripts/hooks/pre-tool-use/01-check-updates.sh` | **195** | Update check |
| `scripts/agent-lint.sh` | 185 | Lint de agents/skills |
| `scripts/orphan-skill-scan.sh` | 183 | Detecção de skills órfãs |

O `01-check-updates.sh` acumula 4 responsabilidades:
1. Leitura de `preferences.json` (auto_update, interval, ...)
2. Fetch GitHub releases API
3. Cache TTL em `.update-cache.json`
4. Semver compare + warning/auto-trigger update

**Por que importa:**
- Script roda **antes de qualquer tool use** em comandos não exceptuados — overhead direto no caminho crítico.
- 195 linhas em path crítico = difícil de testar isoladamente; mudança em qualquer responsabilidade arrisca regressão nas outras.
- Padrão `stop/` (sub-scripts numerados) é mais robusto — por que `pre-tool-use/` só tem 1?

**Impacto positivo:** fragmentar em 4 sub-scripts (`01a-read-prefs.sh`, `01b-fetch-latest.sh`, `01c-cache-check.sh`, `01d-trigger-update.sh`); facilita disable seletivo via flag e teste unitário.

**Impacto negativo:** dispatcher overhead duplica (4 forks em vez de 1) — mitigável por inlining no `pre-tool-use.sh` em modo "produção".

---

## 4. `flow-orphan-template-scan-no-mapping-of-suggested-consumer-vs-orphan-skill-scan` — LOW

**Arquivos:**
- `scripts/orphan-template-scan.sh` (36 linhas, criado 2026-05-15)
- `scripts/orphan-skill-scan.sh` (183 linhas, comparação)

**Observação:** o `orphan-skill-scan.sh` sugere consumer ("Suggested consumer: all coding agents or commands"), mas o `orphan-template-scan.sh` apenas lista o arquivo órfão:

```
ACTION REQUIRED — Orphan templates (no agent/skill/command references):
  · templates/adr-template.md
  · templates/backlog-template.md
```

Sem instrução acionável → mensagem termina sem CTA.

**Por que importa:**
- Inconsistência de UX entre dois scanners da mesma família.
- ACTION REQUIRED sem "ACTION RECOMMENDED" → usuário fica com "...ok, mas o que faço?"
- Tabela mental de mapeamento ADR→`new-adr.sh` ou backlog→`backlog-template skill` é óbvia para autor original, opaca para qualquer outra pessoa.

**Impacto positivo:** adicionar 5 linhas no scanner:

```bash
case "$template" in
  *adr*)     echo "    → Suggested consumer: scripts/new-adr.sh or skills/architecture/adr/SKILL.md" ;;
  *backlog*) echo "    → Suggested consumer: agents/product-analyst.md or skills/shared/backlog-template/" ;;
  *plan*)    echo "    → Suggested consumer: skills/shared/plan-mode/SKILL.md or skills/shared/project-context/SKILL.md" ;;
  *runbook*) echo "    → Suggested consumer: agents/technical-writer.md or skills/shared/runbook/SKILL.md" ;;
esac
```

**Impacto negativo:** hardcoded mapping pode ficar stale; mitigável quando templates passarem dos 4 atuais para algo mais — pivotar para metadata em comentário HTML dentro de cada template.

---

## 5. `flow-session-start-118-lines-monolithic-no-modular-pattern-asymmetric-with-stop-dispatcher` — MEDIUM

**Arquivo:** `scripts/hooks/session-start.sh` (118 linhas)

**Observação:** comparado com `scripts/hooks/stop.sh` (dispatcher) + `stop/01-04.sh` (sub-scripts modulares), o session-start é monolítico:

| Hook | Padrão | Sub-scripts |
|------|--------|-------------|
| `SessionStart` | **Monolítico** (118 linhas em 1 arquivo) | 0 |
| `Stop` | Modular (41 linhas dispatcher + 5 sub-scripts) | 5 |
| `PreToolUse` | Misto (20 linhas dispatcher + 1 sub-script de 195 linhas) | 1 |
| `PreCompact` | Monolítico (43 linhas em 1 arquivo) | 0 |

`session-start.sh` faz: leitura de prefs (~10 linhas), detecção de stale (~20 linhas), warnings (~15 linhas), gating de notificações (~10 linhas), language fallback (~8 linhas), session-id write (~5 linhas), + plumbing.

**Por que importa:**
- Adicionar nova check (ex.: warn sobre install version desatualizada, sobre stale ADRs) força modificar 1 arquivo grande sem isolation.
- Padrão "dispatcher + sub-scripts numerados" foi adotado para Stop e cresceu bem; SessionStart não acompanhou.
- Assimetria torna difícil para autor novo entender qual padrão seguir.

**Impacto positivo:** refatorar para `session-start.sh` (dispatcher) + `session-start/01-read-prefs.sh`, `02-stale-detection.sh`, `03-update-check.sh`, `04-notify.sh`. Permite adicionar novos checks sem tocar arquivos existentes.

**Impacto negativo:** custo de fragmentação (1 commit grande); +4 forks por SessionStart (mas hook roda apenas 1× por sessão, overhead negligível).

---

## 6. `flow-pre-compact-hook-43-lines-not-listed-in-claude-md-hook-files-map` — LOW

**Arquivos:**
- `scripts/hooks/pre-compact.sh` (43 linhas)
- `CLAUDE.md:368-373` (Hook Files Map)

**Observação:** a tabela "Hook Files Map" em CLAUDE.md lista:

```
| `SessionStart` | `scripts/hooks/session-start.sh` | — |
| `PreToolUse` | `scripts/hooks/pre-tool-use.sh` | Dispatcher |
| `PreCompact` | `scripts/hooks/pre-compact.sh` | — |
| `Stop` | `scripts/hooks/stop.sh` | Dispatcher |
```

Olhando agora, `PreCompact` está listado, então isto não é problema. **Mas:** a coluna "Dispatcher" está vazia (`—`) para PreCompact apesar de poder se beneficiar do mesmo padrão modular (item #5 acima).

**Por que importa:**
- Eventual adição de check pré-compactação (ex.: warn se session-summary não foi salva, dump de ADRs novos) cai em monolítico de novo.
- Sub-fingerprint do item #5 (mesma raiz).

**Impacto positivo:** quando #5 for adotado, aplicar mesmo padrão a pre-compact.

**Impacto negativo:** apenas se #5 for descartado — então este perde sentido.

---

## 7. `flow-cli-commit-validate-msg-script-skipped-silently-when-missing-no-instructive-error` — LOW

**Arquivo:** `commands/commit.md:112-117`

**Observação:** o gate pre-commit em `commit.md`:

```bash
if [ -f ".dev-team-agents/scripts/validate-commit-msg.sh" ]; then
    echo "$COMMIT_MSG" | bash .dev-team-agents/scripts/validate-commit-msg.sh
fi
```

**Comportamento atual:**
- Se script existe e mensagem inválida → bloqueia commit. ✅ OK.
- Se script existe e mensagem válida → permite commit. ✅ OK.
- Se script **NÃO** existe → segue commit sem qualquer warning. ❌ silently skipped.

Casos onde script não existe:
- Pre-2026-05-15 (antes de `e5786b7` mover para `scripts/`).
- Instalações antigas que não fizeram update.
- Override de `DEVTEAM_INSTALL_DIR` para caminho não-padrão.

**Por que importa:**
- Usuário pensa que tem validação ativa quando não tem.
- Asymmetric com outros gates (Lint/Type-check/Tests) que **avisam** quando ferramenta não está disponível.

**Impacto positivo:** adicionar `else` clause:

```bash
else
    echo "⚠️  validate-commit-msg.sh not found at expected path; skipping commit-msg validation"
    echo "    Update dev-team-agents: bash .dev-team-agents/scripts/update.sh latest"
fi
```

**Impacto negativo:** ruído visual em cada commit em instalações antigas; mitigável com `DEVTEAM_QUIET=1`.

---

## 8. `flow-orphan-skill-scan-runs-on-every-stop-and-CI-even-when-skills-untouched` — MEDIUM

**Arquivos:**
- `scripts/hooks/stop/02-orphan-skill-scan.sh` (gated por DEVTEAM_NO_CHANGES)
- `.github/workflows/ci.yml` (sem cache)

**Observação:** o scan é gated localmente (Stop hook respeita `DEVTEAM_NO_CHANGES=1`), mas no CI roda **toda push/PR**, mesmo quando o PR só altera `README.md` ou `templates/`:

```yaml
- name: Orphan skill scan
  run: bash scripts/orphan-skill-scan.sh
  continue-on-error: true
```

`scripts/orphan-skill-scan.sh` faz `find skills/...` + `grep -r agents commands workflows` (~2-3s em CI). Em 30 PRs/mês × 2 runs/PR (push + reopen) = ~60 execuções desperdiçadas/mês.

**Por que importa:**
- 60 × 3s = ~3min CI desperdiçado/mês.
- `continue-on-error: true` torna o scan informativo, não bloqueante — ideal para gating por `paths` filter.

**Impacto positivo:** adicionar filter na step:

```yaml
- name: Orphan skill scan
  if: |
    contains(github.event.head_commit.message, '[scan]') ||
    contains(toJson(github.event.pull_request.changed_files), 'skills/') ||
    contains(toJson(github.event.pull_request.changed_files), 'agents/')
  run: bash scripts/orphan-skill-scan.sh
  continue-on-error: true
```

**Impacto negativo:** complexidade de YAML; falso negativo se commit message tem `[scan]` esquecido em PR que toca skills. Mitigável por path-based glob filter em vez de jobs-level if.
