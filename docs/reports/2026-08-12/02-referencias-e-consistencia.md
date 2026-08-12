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

---

# Pass incremental — 2026-08-12 (2ª execução), baseline `3fbe371`

Gates automáticos reexecutados em `3fbe371` — **todos verdes**:

```
agent-lint: clean ✓
size-limits: clean ✓
orphan-skill-scan: (sem saída — nenhum órfão, nenhuma referência quebrada)
orphan-template-scan: clean ✓
```

Links novos introduzidos pelo delta (`bb9f14c`) verificados manualmente:
`README.md` → `docs/reports/metrics-last-20-days.en.md` ✓ resolve ·
`README.pt-BR.md` → `docs/reports/metrics-last-20-days.md` ✓ resolve. O par EN↔pt-BR foi
atualizado no mesmo commit, cumprindo a *README Sync Rule*.

## MEDIUM

### O `.gitignore` do próprio repositório tem 1 das 4 entradas que o `install.sh` escreve em todo projeto instalado

- **Fingerprint:** `gov-repo-gitignore-omits-three-installer-written-entries`
- **Alvo:** `.gitignore`
- **Evidência:**
  - `scripts/install.sh:774-779` — o instalador escreve seis entradas no projeto alvo:
    `".dev-team-agents/user-data/"`, `"!.dev-team-agents/user-data/graphify.json"`,
    `".dev-team-agents/user-data/credentials.local.json"`, `".dev-team-agents/.worktree-session"`,
    `".dev-team-agents/.learn-last-run"` (adicionada hoje por `4734882`), `".worktrees/"`.
  - `agents/setup-assistant.md:153` — "Verify **four** entries exist and add any that are missing:
    `.dev-team-agents/user-data/` …, `!.dev-team-agents/user-data/graphify.json` …,
    `.dev-team-agents/.worktree-session`, and `.dev-team-agents/.learn-last-run`."
  - `.gitignore:9` — `.dev-team-agents/user-data/` — **é a única das quatro presente**.
    O arquivo completo tem 12 linhas; `grep -n "learn-last-run\|worktree-session" .gitignore`
    retorna vazio, e não há `!.dev-team-agents/user-data/graphify.json` nem `.worktrees/`.
  - `ls -a .dev-team-agents/` → `user-data` — o repositório **dogfooda** a instalação, então os
    dois marcadores de sessão são escritos exatamente aqui quando `/devteam:commit` ou o fluxo
    de worktree roda.
- **Problema:** o repositório de referência não aplica a si mesmo três das quatro entradas que
  seu próprio instalador e seu próprio `setup-assistant` declaram obrigatórias.
- **Por que importa:** `.dev-team-agents/.learn-last-run` e `.dev-team-agents/.worktree-session`
  ficam **untracked e não ignorados** no `git status` deste repo. Um `git add -A` — forma que
  aparece em fluxos de commit — varre um marcador de sessão para dentro de um commit público.
  A entrada `.learn-last-run` foi criada hoje para o projeto alvo e esquecida aqui no mesmo commit.
- **Proposta:** acrescentar ao `.gitignore` da raiz as três linhas ausentes
  (`.dev-team-agents/.worktree-session`, `.dev-team-agents/.learn-last-run`, `.worktrees/`) e a
  exceção `!.dev-team-agents/user-data/graphify.json`, espelhando `install.sh:774-779`.
- **Impacto positivo:** o repo passa a dogfoodar a saída do próprio instalador; elimina duas
  fontes de ruído permanente no `git status` e o risco de commitar estado de sessão.
- **Impacto negativo / risco:** cria um **quinto espelho** do bloco `_add_gitignore` sem gate que
  o valide — a mesma classe de drift que já produziu esta divergência. Mitigação real seria a
  Categoria 7 do `/devteam:health-check` (`.gitignore`) rodar também contra este repo, não só
  contra projetos instalados.
- **Esforço:** Baixo

## Descartados por duplicação neste eixo

- **`CLAUDE.md` File Structure não lista `docs/prompts/`**, diretório criado hoje por `d10d541`
  (`docs/prompts/posthog-metrics-report.md`, 129 linhas). Bloco da árvore em `CLAUDE.md:300`
  enumera `docs/` com `agents.md`, `installation.md`, `install-*.md`, `providers.md` e `reports/`.
  **Porta 3 (semântica):** alvo (`CLAUDE.md` File Structure), causa raiz (a árvore omite um
  diretório real) e remediação (acrescentar a linha) coincidem com **três** fingerprints já
  registrados e ✅ Executed — `ref-claude-md-file-structure-omits-helpers-and-privacy-…`,
  `…-scripts-enumeration-omits-…`, `…-skills-subtree-omits-database-mobile-skill-creator-…`.
  Três de três atributos coincidem. Descartado.
