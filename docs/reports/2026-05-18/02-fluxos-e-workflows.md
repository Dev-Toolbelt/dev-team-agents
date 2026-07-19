# Relatório 02 — Fluxos e Workflows (2026-05-18)

**Foco:** gaps de fluxo introduzidos pelos novos hooks de telemetria, helpers refatorados, workflow-detection skill, e workflows existentes que ainda não absorveram as mudanças recentes.

---

## #1 — `flow-telemetry-pre-tool-use-02-runs-on-every-tool-call-without-batching-or-deduplication-burns-200ms-per-burst-session`

**Severidade:** HIGH
**Arquivo:** `scripts/hooks/pre-tool-use/02-telemetry.sh`, `scripts/helpers/telemetry-send.sh`

O sub-script `02-telemetry.sh` é invocado **em todo tool call** pelo dispatcher PreToolUse. Para detectar eventos `agent_spawned` ou `command_invoked`, ele:

1. Roda `_telemetry_enabled` (lê `preferences.json` via python3) → ~30-50ms se python3 startup é frio
2. Lê payload do stdin
3. Roda `python3 -c "import json; …"` em outro fork para parsear o payload (~30-50ms)
4. Chama `telemetry-send.sh --queue …` em outro fork (~50ms)

Em uma sessão burst típica (`/devteam:fullstack` = ~40 tool calls), isso é **40 × ~150ms = ~6 segundos** de overhead acumulado. Não há cache de "telemetria já checada nesta sessão" — `_telemetry_enabled` é recomputado a cada chamada.

**Impacto positivo do fix:** introduzir `.claude/.telemetry-session-cache` com TTL = sessão (compara timestamp do `.claude/.last-session-id`). Recompute somente quando sessão muda. Economia ~5,5s/sessão burst.

**Impacto negativo:** se preference muda no meio da sessão, cache fica stale por até 1 sessão. Mitigável: invalidar cache no SessionStart hook.

---

## #2 — `flow-telemetry-stop-05-runs-after-04-notifier-but-no-fast-path-skip-when-DEVTEAM_NO_CHANGES-is-1`

**Severidade:** MEDIUM
**Arquivos:** `scripts/hooks/stop.sh`, `scripts/hooks/stop/05-telemetry.sh`

O fix do fast-path em `04-notifier.sh` (commit `bec005e`) corrigiu a comparação `DEVTEAM_NO_CHANGES`, mas `05-telemetry.sh` (criado no mesmo dia em `bd61ff7`) **não respeita o fast-path**:

```bash
# scripts/hooks/stop/05-telemetry.sh:30
_telemetry_enabled || exit 0
# (não checa $DEVTEAM_NO_CHANGES)
```

Em sessões puramente conversacionais (sem changes), `05-telemetry.sh` queue um evento `session_end` mesmo que nenhuma atividade significativa tenha ocorrido. Custo: ~50ms por sessão null + 1 evento PostHog desnecessário.

**Impacto positivo:** adicionar `[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0` no topo de `05-telemetry.sh` alinha com a semântica do fast-path.

**Impacto negativo:** subestima volume real de sessões; pode prejudicar análise de retenção. Alternativa: enviar com flag `session_type=conversational`.

---

## #3 — `flow-workflow-detection-skill-only-loaded-by-software-architect-but-9-other-commands-spawn-architect-without-using-it`

**Severidade:** HIGH
**Arquivos:** `skills/shared/workflow-detection/SKILL.md`, `agents/software-architect.md`

A skill `workflow-detection` (50 linhas, commit `d13c693`) é carregada **apenas** quando software-architect age como router em `/devteam:architect`. Os outros 9 commands que spawneiam software-architect (`/devteam:plan`, `fullstack`, `refactor`, `review`, `security`, `dba`, `architect`, `workflow-new`, `workflow-fullstack`) **não invocam** workflow-detection.

Resultado: tarefa "Refatorar este componente" invocada via `/devteam:plan` faz software-architect agir **sem** consultar o workflow `refactor.md`, perdendo o pipeline canônico de coverage-first.

**Impacto positivo:** decidir se workflow-detection é responsabilidade do command (loadável em todos os commands relevantes) ou do agent (loadável uma vez em todo spawn). Padronizar reduz drift.

**Impacto negativo:** load adicional em 9 commands = ~450 tokens × 9 = 4.050 tokens/sessão worst-case. Mitigável: carregar apenas no command de mais alta entropia (`/devteam:plan`, `/devteam:architect`).

---

## #4 — `flow-pre-tool-use-dispatcher-no-mention-of-sub-script-order-convention-asymmetric-with-stop-dispatcher`

**Severidade:** MEDIUM
**Arquivo:** `CLAUDE.md:351-360` (Stop Hook Sub-script Convention), `scripts/hooks/pre-tool-use/`

A convenção de sub-scripts numerados está documentada **apenas** para Stop:

```
| Prefix | Reserved for | Current scripts |
|--------|-------------|-----------------|
| `01-` | State detection | `01-session-summary.sh` |
| `02-` | Repository integrity checks | `02-orphan-skill-scan.sh` |
| ...
```

`scripts/hooks/pre-tool-use/` agora tem 2 sub-scripts (`01-check-updates.sh`, `02-telemetry.sh`) mas sem convenção documentada de **ordem** ou **semântica de prefixo**. Próxima adição (ex: `03-rate-limit.sh`) precisará de decisão ad hoc.

**Impacto positivo:** adicionar tabela simétrica no CLAUDE.md previne drift; comunica intent.

**Impacto negativo:** +10 linhas no CLAUDE.md.

---

## #5 — `flow-update-sh-deletes-helpers-but-orphan-skill-scan-shipped-by-old-install-sh-leaves-dangling-symlink-in-installed-projects`

**Severidade:** MEDIUM
**Arquivo:** `scripts/update.sh`, `scripts/install.sh:188-203` (prune stale skill symlinks)

O commit `19939eb` adicionou pruning de **symlinks órfãos de skills** no `install.sh`, mas o equivalente para **scripts movidos de `scripts/` para `helpers/`** não foi implementado em `update.sh`:

Após update de v1.4.x → v1.5.x (que move dev tools para helpers/):
- `.claude/dev-team-agents/scripts/agent-lint.sh` (instalado pela v1.4) continua existindo
- `.claude/dev-team-agents/helpers/agent-lint.sh` (instalado pela v1.5) também
- Resultado: 2 cópias no FS do usuário

**Impacto positivo:** adicionar bloco de pruning em `update.sh` simétrico ao de skills (linhas 188-203 do install) elimina drift.

**Impacto negativo:** mais complexidade em update.sh; precisa de allowlist de paths conhecidos por versão.

---

## #6 — `flow-commit-md-and-update-md-are-only-2-commands-without-current-context-load-but-both-touch-git-state`

**Severidade:** MEDIUM
**Arquivos:** `commands/commit.md`, `commands/update.md`

CLAUDE.md:209 documenta a exceção: "/devteam:commit e /devteam:update não carregam current-context por design". Verificação:

- `/devteam:commit` opera sobre staging area — exceção válida
- `/devteam:update` opera sobre instalação local — **mas pode estar em qualquer branch/worktree do projeto**

`update.sh` é invocado de qualquer cwd; se rodar de dentro de um worktree do projeto, pode "atualizar" baseado em estado incorreto. Sub-escopo do fingerprint pai `flow-current-context-cache-no-invalidation-on-branch-switch-within-ttl-window` (2026-05-13 ✅), mas com **angle escope-de-exceção**: o design rationale (CLAUDE.md:209) pode estar incompleto.

**Impacto positivo:** revisar se update.sh precisa de uma "consciência de branch atual" mínima (ex: warn se branch != main/master).

**Impacto negativo:** atrita com simplicidade do `update.sh` atual.

---

## #7 — `flow-spawn-classifier-loaded-by-7-commands-but-not-by-architect-tester-dba-security-design-mobile-workflow-detection-not-coordinated`

**Severidade:** MEDIUM
**Arquivos:** `skills/shared/spawn-classifier/SKILL.md`, `skills/shared/workflow-detection/SKILL.md`

Hoje:
- `spawn-classifier` (decide quais agents spawnear) → carregado por 7 commands: backend, fix, frontend, fullstack, plan, refactor, review
- `workflow-detection` (decide qual workflow seguir) → carregado por 1 agent (software-architect)

Os dois são **classificadores de intent** mas operam em domínios diferentes (agents vs workflows). Sem coordenação:
- `/devteam:architect` decide workflow mas não dispara `spawn-classifier`
- `/devteam:plan` decide agents (via spawn-classifier) mas não consulta workflow-detection

Fingerprint pai `flow-no-validation-of-workflow-keyword-collisions-between-software-architect-detection-table-and-orphan-skill-scan-spawn-classifier-rules` (2026-05-17) identificou o overlap conceitual. Este aborda o **angle de coordenação operacional**: deveria existir uma skill `intent-router` que invoca os dois em sequência?

**Impacto positivo:** unificar reduz ambiguidade; permite decisão "este request é refactor → carrega refactor.md → spawn backend + code-reviewer".

**Impacto negativo:** adicionar uma 3ª skill mantém o problema de 3 fontes de classification; alternativa é fundir spawn-classifier e workflow-detection.

---

## #8 — `flow-telemetry-flush-only-on-stop-05-no-flush-on-update-sh-or-install-sh-completion-events-queued-but-never-sent`

**Severidade:** MEDIUM
**Arquivos:** `scripts/install.sh:524-540`, `scripts/update.sh:73-90`, `scripts/helpers/telemetry-send.sh`

Os hooks de install/update queueam eventos (commit `a4bb102`), mas o **flush** só acontece em `Stop` quando TTL 24h é atingido ou queue cap 100. Cenário comum:

1. Usuário roda `bash install.sh` em CI fresh (sem `.claude/user-data/` pré-existente)
2. Evento `install` é queueado
3. Mas não há sessão Claude Code após install → Stop nunca dispara
4. Evento fica em `telemetry-queue.json` indefinidamente até a próxima sessão real

Para users que **só** rodam install.sh (provisioning automation), telemetria nunca sai. Métrica de install é subestimada.

**Impacto positivo:** adicionar `telemetry-send.sh --flush --background` no final de `install.sh` + `update.sh` garante envio em uso primário.

**Impacto negativo:** install.sh leva +~2s para `curl` ao PostHog; mitigável com `&` background + descarte de exit code.

---

## Resumo

| # | Fingerprint | Severidade | Tipo |
|---|------------|-----------|------|
| 1 | flow-telemetry-pre-tool-use-02-runs-on-every-tool-call-without-batching-or-deduplication-burns-200ms-per-burst-session | HIGH | Performance |
| 2 | flow-telemetry-stop-05-runs-after-04-notifier-but-no-fast-path-skip-when-DEVTEAM_NO_CHANGES-is-1 | MEDIUM | Fast-path |
| 3 | flow-workflow-detection-skill-only-loaded-by-software-architect-but-9-other-commands-spawn-architect-without-using-it | HIGH | Coverage |
| 4 | flow-pre-tool-use-dispatcher-no-mention-of-sub-script-order-convention-asymmetric-with-stop-dispatcher | MEDIUM | Doc drift |
| 5 | flow-update-sh-deletes-helpers-but-orphan-skill-scan-shipped-by-old-install-sh-leaves-dangling-symlink-in-installed-projects | MEDIUM | Pruning |
| 6 | flow-commit-md-and-update-md-are-only-2-commands-without-current-context-load-but-both-touch-git-state | MEDIUM | Design rationale |
| 7 | flow-spawn-classifier-loaded-by-7-commands-but-not-by-architect-tester-dba-security-design-mobile-workflow-detection-not-coordinated | MEDIUM | Coordenação |
| 8 | flow-telemetry-flush-only-on-stop-05-no-flush-on-update-sh-or-install-sh-completion-events-queued-but-never-sent | MEDIUM | Eventos perdidos |
