# Modo Guardião — Verificação (Fases 1 e 1b) — 2026-10-02

**Baseline:** `HEAD` = `4db9ed2` · **Baseline anterior:** `ef69da3` (2026-09-18)
**Delta:** 650 commits · 728 arquivos tocados — **o maior delta da história do banco**, e o primeiro
pass desde 2026-08-21 com movimento real de código.

---

## Método e cobertura

| Item | Valor |
|---|---|
| Fingerprints vivos no banco | 266 linhas (`grep -cE '^- \`[a-z]'`) · 264 parseáveis com severidade |
| Conjunto verificável (✅ Executed limpo + ⚠️ Partial) | **133** |
| Conjunto aberto (sem marcador) | **97** |
| Conjunto de exclusão (🟢 / ⚰️ / já 🔴 / já 🟡) | 34 |

O conjunto verificável excede 60 itens, então se aplicou a regra de amostragem do prompt:
**todos os HIGH e MEDIUM-HIGH (41) + amostra aleatória de 30% do restante (28 de 92)** — semente
fixa `20261002` para reprodutibilidade. **Cobertura da Fase 1: 68 de 133 (51%).**

A Fase 1b cobriu **97 de 97 (100%)** dos achados abertos — viável porque a maioria resolve com uma
checagem de símbolo única.

---

## Fase 1 — Placar

| Marca verificada | Quantidade | % |
|---|---|---|
| ✅ Feito | **64** | 94,1% |
| 🟡 Parcialmente feito | **4** | 5,9% |
| 🔴 Não feito | **0** | **0%** |

**Nenhuma marca 🔴 neste pass.** É o segundo pass consecutivo sem reabertura por marcação falsa
(2026-09-18 teve 12,5%), e vem logo depois de um lote de 30 marcações novas aplicadas hoje mesmo
(`68cd420`), o que era exatamente o cenário de maior risco. O limiar de escalonamento de 15% não foi
atingido — a integridade do banco está saudável.

Dos 68 itens verificados, **25 carregam marca de 2026-10-02 ou 2026-09-30**, ou seja, foram
verificados contra o próprio commit que os fechou, na janela de 24h. Todos os 25 passaram
(23 ✅ e 2 🟡), o que é o resultado mais forte do pass: o lote de execução de hoje não inflou o placar.

### Os 4 🟡 — sub-escopo pendente

#### `token-pre-tool-use-01-check-updates-forks-python3-to-read-interval-before-ttl-early-exit-on-every-tool-call-burst-overhead`
- **Marca original:** ✅ Executed: 2026-07-31 (MEDIUM)
- **Commit examinado:** `cc28900` (2026-07-31) — criou o sidecar `.update-check-interval` com gate `[ prefs -nt cache ]`
- **Evidência:** `scripts/hooks/lib/update-check.sh:56-61` — "…the extra python3 fork here is negligible — so the cache is dropped and the preference is read directly."; `scripts/hooks/pre-tool-use/_disabled-01-check-updates.sh:42` — `INTERVAL_HOURS=$(uc_interval_hours "$PREFS_FILE" "$INTERVAL_CACHE_FILE")`
- **Por que 🟡:** a correção marcada foi **revertida** por `7dbc646` (08-03) e `ba39c86` (08-06), que removeram o sidecar e desativaram o hook. O sintoma desapareceu por outra via — a checagem migrou para o `SessionStart` (`scripts/hooks/session-start.sh:191` — "# ── Update check (moved from pre-tool-use/01-check-updates.sh)"), então o fork é 1× por sessão e não 1× por tool call. **A marca deveria ser 🟢 (resolvido por outra via), não ✅.**

#### `flow-merge-md-rebases-onto-target-while-delegating-to-base-step-8`
- **Marca original:** ✅ Executed: 2026-10-02 (MEDIUM)
- **Commit examinado:** `a2cf59c` (2026-10-02) — fix(commands): fire the learn nudge on a moved branch tip, reach worktree finalization in merge
- **Evidência:** `commands/merge.md:52` — "**Commit + rebase onto `<target>` + merge + teardown** (recommended) — delegate entirely to `skills/shared/worktree/SKILL.md` § Worktree Setup step 8"; `skills/shared/worktree/SKILL.md:55` — "8. Finalize on merge: rebase onto base → resolve → commit → merge…"
- **Falta:** a contradição central permanece. O commit mitigou o caso comum (`merge.md:37` — "with `worktree=yes branch=<b>`, the target defaults to the worktree base `<b>`") e passou a anunciar a divergência (`:39`), mas **não existe mecanismo que repasse `<target>` como base ao delegar** ao passo 8. A skill não foi tocada desde `e05ce90` (2026-08-18). Com um alvo explícito diferente da base, "delegate entirely" ainda rebaseia na base errada.

#### `auto-update-no-integrity-check`
- **Marca original:** ✅ Executed: 2026-07-31 (MEDIUM-HIGH)
- **Commit examinado:** `2e12335` (2026-07-31) — criou `scripts/lib/installer-fetch.sh` com ref pinning, validação de shebang/tamanho/`bash -n` e abort em mismatch de digest
- **Evidência:** `scripts/lib/installer-fetch.sh` (`dta_verify_digest`) — "No digest available → proceed (see the integrity model note at the top of this file; the project publishes none today)."; o código faz `printf '%s' "$_expected" | grep -Eq '^[a-fA-F0-9]{64}$' || return 0`
- **Falta:** `scripts/install.sh.sha256` não existe nem é gerado por nenhum workflow (`rg` só acha a referência em `installer-fetch.sh:37,193`), então a verificação SHA-256 **falha aberta**. O que foi entregue é integridade de **transporte**; falta integridade de **autenticidade** (publicar o digest/assinatura e torná-los obrigatórios).

#### `ref-two-malformed-git-tags-v-1-1-0-and-v-1-3-13-violate-vx-y-z-convention`
- **Marca original:** ⚠️ Partial (2026-07-31) (LOW-MEDIUM)
- **Commit examinado:** `c7535b76` (2026-07-31)
- **Evidência:** `.github/workflows/ci.yml:44-50` — "Validate pushed tag matches vX.Y.Z … grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$'"; `git tag | rg 'v\.'` em HEAD ainda devolve `v.1.1.0` e `v.1.3.13`
- **Veredito:** a marca ⚠️ Partial é **honesta** — o gate existe e as duas tags seguem publicadas de propósito. Mantida como está.

### Ressalvas registradas sem rebaixar a marca

Três itens passaram como ✅ com observação que vale para o próximo pass:

| Fingerprint | Ressalva |
|---|---|
| `auto-install-heredoc-omits-auto-learn-before-commit` | A chave `auto_learn_before_commit` chegou ao heredoc (`scripts/install.sh:1289`), mas **nenhum gate** impede a quarta recorrência da drift; o comentário de `:1268` continua só prosa ("the two drifted once already"). |
| `ref-docs-agents-md-model-column-wrong-…` | A coluna foi trocada por `tier`, que é a fonte de verdade, mas **nenhum lint cruza `docs/agents.md` com `tiers.json`** — a causa raiz (cópia manual) saiu, a validação não entrou. |
| `flow-02c-escape-hatch-anchored-while-detection-is-substring` | A escotilha casa após espaço/`;`/`&`/`\|`/`(`, mas `sh -c "DEVTEAM_FULL_SUITE_CONFIRMED=1 npm test"` ainda é bloqueada (caractere anterior é `"`). Há saída viável prefixando por fora, então não é beco sem saída. |

### Confirmações de maior valor

- `flow-pre-tool-use-dispatcher-sigpipe-141-masks-02c-block` (HIGH) — ✅ em duas camadas:
  `scripts/hooks/pre-tool-use.sh:22-24` passa o payload por `mktemp` em vez de pipe, e `:44-46`
  garante "exit 2 (a refusal) is never masked by an earlier exit 1". Coberto por 168 linhas novas em
  `tests/test_pretooluse_hooks.py`.
- `ref-tool-map-tool-rewrites-loaded-but-never-emitted-by-render-provider` (HIGH) — ✅ **reproduzido
  em sandbox**: renderizando opencode, `.opencode/agents/setup-assistant.md:89` sai com "Use the
  `question` tool" e `rg -c AskUserQuestion` devolve zero.
- `token-02c-full-suite-guard-substring-match-injects-nudge-on-non-test-commands` (MEDIUM-HIGH) — ✅
  **executando o hook com payloads reais**: `cat jest.config.js`, `grep -rn pytest docs`,
  `git log --grep=rspec` → 0 bytes; `npx jest` sem escopo → 405 bytes de nudge.
- `auto-install-sh-bash-source-fallback-resolves-to-cwd` (MEDIUM-HIGH) — ✅ **reproduzido**: o trecho
  sob `cat snip.sh | bash` com um `./lib/state.sh` plantado na CWD imprimiu `FALLBACK`, não
  `SOURCED_PROJECT_LIB`.

---

## Fase 1b — Validade dos achados abertos

**Cobertura: 97 de 97 (100%).**

| Veredito | Quantidade | % |
|---|---|---|
| Ainda reproduz | **88** | 90,7% |
| 🟢 Resolved (corrigido de passagem) | **9** | **9,3%** |
| ⚰️ Obsoleto | 0 | 0% |

**Mortalidade do pass: 9,3%** — a maior desde a consolidação (os seis passes anteriores ficaram entre
0% e 3,2%). Isso não é deterioração do banco: é o efeito direto de 650 commits. Nove achados
abertos foram fechados sem que ninguém os tenha mirado, o que é o comportamento esperado de um banco
vivo sobre uma árvore em movimento.

### Os 9 resolvidos de passagem

| Fingerprint | Resolvido por | Evidência |
|---|---|---|
| `gov-repo-gitignore-omits-three-installer-written-entries` | `5174b6d` | `.gitignore:8-9` — ".dev-team-agents/.worktree-session" / ".dev-team-agents/.learn-last-run" |
| `docs-sync-changelog-unreleased-omits-full-suite-guard-and-orchestration-deltas` | `68cd420` | `CHANGELOG.md:124` — "The full-suite guard matches a runner only when it is the invoked command…"; `:131` — "`orchestration` numbers its checks 1–6…" |
| `flow-update-sh-provider-reinstall-aborts-on-non-exit-3-failures` | `60a1798` | `scripts/update.sh:123` — `po_rerender_providers \|\| _PROVIDER_FAILED=1`; `:158-159` — "Update finished, but at least one provider re-render failed" |
| `agent-line-cap-205-documented-in-claude-md-vs-211-enforced-by-size-limits` | `c19f060` | `CLAUDE.md:102` — "`helpers/size-limits.sh` enforces 211"; `rg "205"` no `CLAUDE.md` → 0 |
| `auto-size-limits-claude-md-warning-counted-as-violation-turns-ci-lint-red` | `a99dc3e` | `helpers/size-limits.sh` — "# A warning is not a violation… WARNINGS=()"; com `CLAUDE.md` em 647 linhas o script sai 0 |
| `ref-notifier-documented-as-live-in-four-docs-while-hook-file-is-disabled` | `f92db85` | `ls scripts/hooks/stop` lista `04-notifier.sh` sem o prefixo `_disabled-` |
| `token-pr-md-14-line-verbatim-learn-nudge-while-audit-md-delegates-in-one-line` | `a2cf59c` | `commands/pr.md:142` — "Run the canonical learn-nudge check in `commands/merge.md` § Step 4…" |
| `auto-slim-bootstrap-shape-contract-cannot-fail-the-build` | `9ed2964` | `.github/scripts/ci/slim-bootstrap.sh:244` — `[ "$fail" -eq 0 ] \|\| exit 1` |
| `docs-sync-claude-md-context-list-item-count-12-vs-11` | `e80903e` | `skills/shared/project-context/SKILL.md:116` — "12. extra context_paths" (a lista ganhou o índice do wiki) |

### Achados abertos cuja medição piorou

A Fase 1b também re-mede os números que o achado cita. Oito mediram pior do que no registro — vale
reabrir a prioridade deles, não o fingerprint:

| Fingerprint | Registro | HEAD |
|---|---|---|
| `token-orchestration-skill-377-lines-…` | 377 linhas | **399** |
| `auto-no-gate-validates-claude-md-file-structure-tree-against-real-tree` | 3 de 4 arquivos listados | **4 de 10** em `scripts/hooks/lib/` |
| `token-status-and-version-inline-bash-scripts-paid-twice` | 132 linhas de bash | **147** |
| `docs-sync-reports-index-md-99-legend-claims-all-131-entries-unmarked` | 121 marcadas | **~189 marcadas** de 266 |
| `agent-jira-detection-branch-naming-block-duplicated` | 13 corpos | **15** |
| `token-work-feedback-opt-out-gate-lives-inside-the-skill-it-gates` | 71 linhas | **82** |
| `auto-orphan-skill-scan-user-invocable-parser-overruns` | 5 nomes capturados | **6** (`repo-release-prep` entrou na janela) |
| `token-151-skills-flat-symlinked-into-claude-skills-index` | 152 `SKILL.md` | **153** |

Dois mediram melhor (`token-fix-patterns-517-lines` → 444; `token-checks-list` 668 → 646) e um
encolheu de ~30 para ~10 linhas (`token-graphify-setup-os-detection`), sem que a divergência
documental que o achado descreve tenha mudado.

### Achados abertos que mudaram de endereço

Dois precisam de **re-ancoragem** no próximo pass, porque o alvo migrou de arquivo:

- `flow-update-sh-codex-slim-guard-dead-branch-false-strip-claim` — o guard saiu de
  `scripts/update.sh` para `scripts/lib/provider-ownership.sh` (`60a1798`); o ramo morto e a
  afirmação falsa ("stripped by scripts/lib/strip-tarball.sh" contra
  `strip-tarball.sh:35-36` — "is now INCLUDED in the slim Claude install") persistem no novo arquivo.
- `ref-three-pointers-to-claude-md-hook-subscript-convention-moved-to-hooks-md` — de 3 ponteiros
  restaram 2 (`scripts/hooks/stop.sh:58` e `scripts/hooks/pre-tool-use.sh:28`); o terceiro saiu com
  a reescrita de `CLAUDE-md/notifications.md`.

Vários achados de `CLAUDE.md` migraram para a família `CLAUDE-md/*.md` (`commands.md`,
`preferences.md`, `hooks.md`) sem deixar de reproduzir — a contradição simplesmente passou a morar
entre dois arquivos em vez de dentro de um. Isso vale para
`docs-sync-claude-md-173-says-all-devteam-commands-load-current-context`,
`flow-claude-md-no-agent-command-list-says-seven`,
`flow-rule-and-sync-rules-listed-as-technical-writer-but-never-delegate` e
`flow-review-command-writes-and-commits-while-documented-as-read-only`.
