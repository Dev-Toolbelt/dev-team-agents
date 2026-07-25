# Fluxos e Workflows — 2026-05-23

> 3 sugestões originais. Cada item traz **trecho/evidência**, **motivo** e **impactos positivos e negativos** da correção proposta. Todas foram cruzadas contra o banco de 481 fingerprints (`_index.md`) e são inéditas.

---

## F1 — O validador de ordem de tools (`agent-lint.sh`) só checa o **prefixo `Read, Write, Edit`** — o restante da ordem canônica (Glob, Grep, Bash, WebSearch, WebFetch) **não é validado**

**Severidade:** MEDIUM (latente)
**Fingerprint:** `auto-agent-lint-tools-order-check-validates-only-read-write-edit-prefix-glob-grep-bash-websearch-webfetch-suffix-order-unenforced`

**Evidência** — `helpers/agent-lint.sh:98-108`:

```bash
if echo "$tl" | grep -q "Write\|Edit"; then
  # Write-capable: Read must come first, then Write, Edit
  if ! echo "$tl" | grep -qE "^tools: Read, Write, Edit"; then
    ERRORS+=("… non-canonical tools order (write-capable agents must start with: Read, Write, Edit, Glob, Grep, Bash)")
  fi
else
  if ! echo "$tl" | grep -qE "^tools: Read"; then
    ERRORS+=("… non-canonical tools order (read-only agents: Read must be first)")
  fi
fi
```

**Motivo:** a CLAUDE.md define a ordem canônica completa: `Read, Write, Edit, Glob, Grep, Bash, WebSearch, WebFetch`. O lint, porém, valida apenas que a linha **começa** com `Read, Write, Edit` (agentes write-capable) ou com `Read` (read-only). Tudo após esse prefixo passa sem checagem. Uma linha como `tools: Read, Write, Edit, Bash, Glob, Grep` (Bash antes de Glob) ou `Read, Write, Edit, Glob, Grep, WebFetch, WebSearch` (WebFetch antes de WebSearch) **passa limpa**. Hoje os 17 agentes estão todos em conformidade (verifiquei: todos seguem `Read[, Write, Edit], Glob, Grep, Bash[, WebSearch[, WebFetch]]`), então o gap é **latente** — mas é justamente o tipo de enforcement parcial que dá falsa confiança: o histórico do repo já flagrou divergências de ordem de tools antes (`ref-tools-frontmatter-ordering-divergence-reviewers-vs-coders`, `agent-tools-frontmatter-canonical-order-not-enforced`). O validador foi adicionado depois desses achados, mas **resolveu só o prefixo**. Distinto dos fingerprints antigos (que eram "não há validador"); aqui o validador **existe e é incompleto**.

**Impacto positivo da correção:** validar a sequência inteira contra a ordem canônica (uma lista de referência + comparação posicional, ~10 linhas de bash) fecha a classe definitivamente e impede regressão futura quando um agente novo adicionar tools fora de ordem.

**Impacto negativo / risco:** baixo. O único cuidado é a regra de WebSearch/WebFetch serem **opcionais** e **append-only** — a validação precisa aceitar a ausência de uma ou ambas, mas exigir a ordem relativa quando presentes. Implementar mal pode gerar falso positivo; mitigável com fixtures (que o lint hoje não tem).

---

## F2 — O passo de **session-summary** existe em 8 dos 10 workflows, mas **falta justamente em `fullstack.md` e `refactor.md`** — os dois fluxos multi-agente de maior fan-out

**Severidade:** MEDIUM-HIGH
**Fingerprint:** `flow-session-summary-closure-step-present-in-eight-of-ten-workflows-but-absent-from-fullstack-and-refactor-highest-fanout`

**Evidência** — quem referencia `session-summary` em `workflows/`:

```
workflows/bug-fix.md          ✓
workflows/security-patch.md   ✓
workflows/new-project.md      ✓
workflows/design.md           ✓
workflows/review.md           ✓
workflows/maintenance.md      ✓
workflows/mobile.md           ✓
workflows/inherited-project.md ✓
workflows/fullstack.md        ✗   (tem "## Workflow Closure" na linha 124, mas sem session-summary)
workflows/refactor.md         ✗   (tem "## Workflow Closure" na linha 239, mas sem session-summary)
```

**Motivo:** o "Session Summary Rule" da CLAUDE.md é o mecanismo central contra perda de contexto entre sessões, e o `Stop` hook reforça-o. Oito workflows já o incorporaram na seção de fechamento. Os **dois que faltam — `fullstack.md` e `refactor.md` — são exatamente os de maior número de agentes** (`/devteam:fullstack` spawna backend + frontend + database + ui-ux + 2 test-specialists; `refactor.md` orquestra architect → test-specialists → security → developers → reviewer → qa). São os fluxos onde **mais decisões são tomadas por mais agentes** e, portanto, onde a perda de contexto é mais cara — e ambos têm uma seção "## Workflow Closure" que **poderia** hospedar o passo, mas não o faz. O banco tem `flow-workflows-no-session-summary-step` (geral, de quando **nenhum** workflow tinha o passo); este achado é o **sub-escopo refinado**: a assimetria 8/10 com os dois piores casos descobertos.

**Impacto positivo da correção:** adicionar um passo "Escrever entrada em `.dev-team-agents/user-data/session-summary.md` (multi-agente: cada agente *append*a sua contribuição)" ao "## Workflow Closure" de ambos alinha os 10 workflows e protege os fluxos mais complexos; reforça o protocolo multi-agente já descrito na CLAUDE.md.

**Impacto negativo / risco:** mínimo. O único risco é redundância com o `Stop` hook (que já cobra o summary) — mas o passo no workflow é **proativo** (orienta o fan-out a *append*ar em vez de sobrescrever), enquanto o hook é **reativo** (detecta a ausência). São complementares, não duplicados.

---

## F3 — O bloco de `chmod` do `install.sh` enumera `hooks/`, `pre-tool-use/` e `stop/` manualmente, mas **omite `scripts/hooks/lib/`** — enumeração que deriva a cada nova subárvore de hook

**Severidade:** LOW-MEDIUM
**Fingerprint:** `flow-install-sh-chmod-enumeration-omits-scripts-hooks-lib-subdir-manual-per-subdir-list-drifts-on-new-hook-subtree`

**Evidência** — `scripts/install.sh:386-389`:

```bash
chmod +x "$INSTALL_DIR/scripts/"*.sh
chmod +x "$INSTALL_DIR/scripts/hooks/"*.sh 2>/dev/null || true
chmod +x "$INSTALL_DIR/scripts/hooks/pre-tool-use/"*.sh 2>/dev/null || true
chmod +x "$INSTALL_DIR/scripts/hooks/stop/"*.sh 2>/dev/null || true
# (sem entrada para scripts/hooks/lib/)
```

**Motivo:** o instalador dá `+x` percorrendo **uma lista manual de subdiretórios** de `scripts/hooks/`. O subdiretório `lib/` (adicionado em 2026-05-15, com `session-summary-detect.sh`) **não está na lista**. Hoje isso é **inofensivo** — `lib/session-summary-detect.sh` é `source`-ado (`.`), não executado, então não precisa de bit de execução. Mas o padrão de **enumeração manual por subdiretório** é frágil: ele derivou silenciosamente quando `lib/` nasceu, e vai derivar de novo a cada nova subárvore de hook. Se um dia alguém colocar um script **executável** em `lib/` (ou criar `scripts/hooks/<novo>/`), ele será enviado **sem `+x`** e o hook correspondente falhará em produção de forma difícil de diagnosticar. É o mesmo failure-mode das enumerações manuais já flagradas em outros contextos (File Structure, strip list), mas aqui no caminho crítico do **install**.

**Impacto positivo da correção:** trocar as 4 linhas por uma varredura recursiva única — `find "$INSTALL_DIR/scripts" -name '*.sh' -exec chmod +x {} +` — torna o chmod **auto-descobrível**, eliminando a classe inteira de deriva (nunca mais um subdir novo de hook fica sem `+x`).

**Impacto negativo / risco:** baixo. O `find` recursivo daria `+x` também a arquivos `lib/` que só são sourced (inócuo) e a qualquer `.sh` solto. Mitigação opcional: manter o recursivo mas excluir `lib/` se houver razão para mantê-lo sem `+x`. Custo de execução: uma varredura em vez de quatro globs — negligenciável.
