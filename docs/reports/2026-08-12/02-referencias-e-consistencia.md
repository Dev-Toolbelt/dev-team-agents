# Eixo B — Referências e Consistência — 2026-08-12

**Baseline:** `HEAD` = `07e0725`

## Gates automáticos — todos limpos

| Helper | Saída |
|---|---|
| `helpers/orphan-skill-scan.sh --quiet` | limpo (exit 0, sem output) |
| `helpers/orphan-template-scan.sh` | `orphan-template-scan: clean ✓` |
| `helpers/agent-lint.sh` | `agent-lint: clean ✓` |
| `helpers/size-limits.sh` | `size-limits: clean ✓` |

As 11 skills novas do delta (`architecture/data-fetching-integrity`, `ingestion-api`, `resilience`,
`sse-streaming`, `design/seo-optimization`, `devops/tool-installers`, `integrations/wordpress`,
`shared/feature-learn`, `reuse-guidelines`, `scoped-test-execution`, `spec-gate`) estão **todas**:
wired a agentes/comandos (orphan-skill-scan limpo), com `name == basename`, e sob o teto de 500
linhas (maior: `tool-installers` = 174). `feature-learn` → 4 comandos; `spec-gate` → 9 sites;
`reuse-guidelines` → 14 sites.

## Verificações manuais de doc-vs-árvore — sem drift novo

- **`CLAUDE-md/hooks.md`** documenta todos os sub-scripts reais de Stop (`03c`, `03d`, `03e`, `99b`)
  e PreToolUse (`02c`), além dos três renomeados `_disabled-*`. Nenhum sub-script novo ficou sem
  documentação.
- **Gate de sync EN↔pt-BR** (`.github/scripts/ci/02-readme-sync.sh:192`) usa `find . -name
  '*.pt-BR.md'` — **descoberta por glob**, não pares hardcoded. Os pares novos do delta (`docs/harness`,
  `docs/user-preferences`, `docs/credentials.local`) são cobertos automaticamente. Confirma o
  fingerprint executado `flow-readme-sync-ci-hardcodes-three-doc-pairs`.
- **Tabela de comandos do `CLAUDE.md`** lista os 9 comandos novos (`seo`, `status`, `version`,
  `install`, `push`, `rule`, `sync-rules`, `explain`, `relayout`) e o agente novo `seo-specialist`.

## Achado

**Nenhum achado original neste eixo.** Os gates de referência estão limpos e o autor do delta manteve
`hooks.md`, a tabela de comandos e os pares de doc em sincronia. As inconsistências de doc conhecidas
(`docs-sync-claude-md-102-…`, `docs-sync-claude-md-173-…`, `docs-sync-reports-index-md-99-…`)
seguem abertas e foram revalidadas na Fase 1b — não são novas.
