# Fluxos e Workflows — 2026-05-21

> 3 sugestões originais sobre CI, hooks e orquestração. Cada item traz **evidência**, **motivo** e **impactos positivos e negativos**. Deduplicadas contra os 437 fingerprints do banco.

---

## F1 — `check-fingerprint-uniqueness.sh` varre só o `_index.md`; é cego à rotação de arquivo de arquivo documentada → duplicatas cross-file passam despercebidas

**Severidade:** MEDIUM
**Fingerprint:** `flow-check-fingerprint-uniqueness-scans-only-index-md-blind-to-documented-archive-rotation-cross-file-dupes-undetected`

**Evidência** — `helpers/check-fingerprint-uniqueness.sh`:

```bash
INDEX_FILE="docs/reports/_index.md"
...
DUPLICATES=$(grep -E "^- \`[a-z][a-z0-9-]+" "$INDEX_FILE" ... | sort | uniq -d)
```

O script (rodado no CI, sem `continue-on-error`, portanto **bloqueante**) considera apenas `_index.md`. Mas o próprio `_index.md` documenta uma estratégia de rotação:

> "o índice cresce indefinidamente, mas pode ser **rotacionado** a cada 90 dias movendo entradas antigas para `_index-archive-YYYY-Q.md`."

**Motivo:** assim que a rotação acontecer, um slug que viveu no índice será movido para `_index-archive-*.md`. A partir daí, nada impede que o mesmo slug seja **re-registrado** no `_index.md` — a checagem de unicidade só dedup dentro de um arquivo. A garantia de unicidade silenciosamente encolhe de "global" para "dentro do arquivo atual", justamente quando a rotação for ligada (que é o mecanismo recomendado para conter o crescimento do índice). É um gap distinto do `token-_index-md-...archive` (que trata a rotação não disparar) e do gate de README sync por glob — aqui o problema é a **fronteira de varredura da checagem de unicidade**.

**Impacto positivo da correção:** mudar para `INDEX_FILES=(docs/reports/_index.md docs/reports/_index-archive-*.md)` e dedup sobre a união preserva a unicidade global mesmo após a rotação; o passo de dedup do agente de research deve varrer os mesmos arquivos (alinhamento de fonte).

**Impacto negativo / risco:** baixíssimo. Com `nullglob`/`shopt`, é preciso tratar o caso "ainda não há arquivos de arquivo" para o glob não falhar; e o custo do `grep` cresce levemente conforme arquivos de arquivo aparecem (negligenciável vs. o ganho de correção).

---

## F2 — `02b-orphan-template-scan.sh` é a única varredura "gated por mudança" SEM o fast-path `DEVTEAM_NO_CHANGES` que seus irmãos `02`/`03` têm → varre em todo Stop, inclusive sessões sem mudança

**Severidade:** MEDIUM
**Fingerprint:** `flow-02b-orphan-template-scan-lacks-devteam-no-changes-fast-path-and-git-scoped-gate-runs-full-scan-every-stop`

**Evidência** — presença do fast-path por sub-script de Stop:

```
01-session-summary.sh   → tem DEVTEAM_NO_CHANGES
02-orphan-skill-scan.sh → tem DEVTEAM_NO_CHANGES + gate por git status agents/ skills/
02b-orphan-template-scan.sh → NENHUM fast-path, NENHUM gate
03-agent-lint.sh        → tem DEVTEAM_NO_CHANGES + gate por git status
04-notifier.sh          → tem fast-path condicional
05-telemetry.sh         → sem fast-path (já registrado em 2026-05-18)
```

Corpo do `02b` (íntegro):

```bash
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
SCRIPT="$REPO_ROOT/helpers/orphan-template-scan.sh"
[ -f "$SCRIPT" ] || exit 0
bash "$SCRIPT" --quiet
```

**Motivo:** o irmão `02-orphan-skill-scan.sh` cedo retorna em sessões sem mudança e só roda se `agents/`/`skills/` foram tocados. O `02b` não faz nenhuma das duas coisas: invoca `orphan-template-scan.sh` (que faz `git rev-parse` + grep em todo `agents/`/`skills/`/`commands/`) em **todo** Stop, mesmo numa sessão puramente conversacional sem nenhuma edição. É uma assimetria clara — o `02b` "esqueceu" o padrão que o `02` adotou. (O caso do `05-telemetry` já está no banco; o do `02b` é inédito.)

**Impacto positivo da correção:** adicionar `[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0` no topo (e, idealmente, um gate por `git status templates/ skills/ agents/ commands/`) elimina trabalho redundante em toda sessão sem mudança; torna os três scanners de Stop consistentes.

**Impacto negativo / risco:** quase nulo. O único efeito é não rodar a varredura de templates quando nada mudou — exatamente o comportamento desejado dos irmãos. Cuidado para manter o `set -euo pipefail` e a ordem (fast-path antes de qualquer comando).

---

## F3 — O dispatcher de Stop calcula `DEVTEAM_NO_CHANGES` uma vez, mas `02` e `03` recomputam, cada um, o mesmo `git status`/`git log` em vez do dispatcher exportar o conjunto de paths tocados

**Severidade:** LOW-MEDIUM
**Fingerprint:** `flow-stop-dispatcher-computes-no-changes-once-but-02-and-03-each-recompute-identical-git-status-and-git-log-no-shared-touched-set`

**Evidência** — `scripts/hooks/stop.sh` já paga o custo de inspecionar o git uma vez:

```bash
if git diff --quiet 2>/dev/null && git diff --cached --quiet 2>/dev/null; then
    TODAY=$(date +%Y-%m-%d)
    if ! git log --oneline --since="${TODAY} 00:00:00" --format="%h" ...; then
        DEVTEAM_NO_CHANGES=1
    fi
fi
export DEVTEAM_NO_CHANGES
```

Mas, quando **há** mudança (fast-path não dispara), tanto `02-orphan-skill-scan.sh` quanto `03-agent-lint.sh` rodam, **cada um**, exatamente:

```bash
TOUCHED=$(git status --porcelain agents/ skills/ 2>/dev/null | head -1)
TODAY_COMMITS=$(git log --since="$(date +%Y-%m-%d) 00:00:00" --oneline -- agents/ skills/ ...)
```

**Motivo:** o dispatcher só exporta o booleano `DEVTEAM_NO_CHANGES`. Ele já tem o contexto para computar **uma vez** se `agents/`/`skills/` foram tocados e exportar isso (ex.: `DEVTEAM_TOUCHED_AGENTS_SKILLS=1`). Em vez disso, dois sub-scripts repetem o mesmo par `git status` + `git log` — 4 forks de git redundantes por Stop com mudança. É um angle distinto do fast-path (que cobre só o caso "sem mudança") e do `flow-stop-dispatcher-globs-all-sh-no-allowlist` (2026-05-19, sobre a varredura de arquivos do loop).

**Impacto positivo da correção:** centralizar o cálculo dos paths tocados no dispatcher e exportar o resultado elimina a duplicação; corta ~4 invocações de git por Stop "com mudança"; cria fonte única para futuros sub-scripts gated por mudança.

**Impacto negativo / risco:** acopla os sub-scripts a uma variável exportada pelo dispatcher — se rodados isoladamente (fora do dispatcher, ex.: em teste manual), precisam de fallback. Mitigável com `: "${DEVTEAM_TOUCHED_AGENTS_SKILLS:=$(git status --porcelain ...)}"` (usa o exportado se existir, recomputa se não). Ganho modesto em valor absoluto; o maior benefício é consistência e fonte única.
