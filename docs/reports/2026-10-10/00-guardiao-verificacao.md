# Fase 1 e 1b — Verificação Guardiã — 2026-10-10

**Baseline:** `HEAD` = `349f18c` · **Baseline anterior:** `5e338d9` · **Delta:** 62 commits,
183 arquivos.

> O repositório recebeu um commit **durante** este pass: `cd58999`
> ("build(cli): point the dev environment at the provisioned Supabase project", 3 linhas em
> `scripts/lib/auth-config.dev.json`) foi commitado de uma mudança que estava no working tree no
> início. Todas as fases foram verificadas contra `349f18c`; nenhum achado nem nenhuma
> verificação deste pass toca esse arquivo.

> **Plan Gate.** Este pass foi disparado por tarefa agendada, com instrução explícita de
> executar e commitar. Não houve gate humano; o critério de amostragem está declarado abaixo
> antes dos resultados, que é o que o gate existe para garantir.

---

## Conjuntos (Fase 0)

| Conjunto | Tamanho | Critério |
|---|---|---|
| Fingerprints no banco | 287 | `grep -cE '^- \`[a-z]' docs/reports/_index.md` |
| **Verificável** (✅ Executed + ⚠️ Partial) | **153** | alvos da Fase 1 |
| **Aberto** (sem marcador) | **109** | alvos da Fase 1b |
| Exclusão (✅/↩️/🟢/⚰️) | 153 ✅ · 0 ↩️ · 15 🟢 · 1 ⚰️ | fora da geração |
| Marcas 🔴 já no banco | 20 linhas (10 no conjunto verificável) | reaberturas de passes anteriores |

Severidade no banco: 36 HIGH · 52 MEDIUM-HIGH · 99 MEDIUM · 66 LOW-MEDIUM · 32 LOW.

**Datas de marcação no conjunto verificável:** 2026-07-31 (99) · 2026-08-14 (3) · 2026-08-21 (3) ·
2026-08-28 (3) · 2026-09-04 (4) · 2026-09-11 (4) · 2026-09-18 (3) · 2026-09-29 (1) ·
2026-09-30 (1) · 2026-10-02 (32). **Nenhuma marca nova desde o baseline anterior** — os 62 commits
do delta não marcaram nada como executado, então a Fase 1 deste pass é sobre durabilidade, não
sobre marcações frescas.

**Delta de código por subárvore:** `app/src` 32 · `scripts/lib` 23 · `app/test` 20 ·
`docs/reports` 8 · `docs/development` 7 · `skills/shared` 5 · `.github/scripts` 5 ·
`scripts/hooks` 4 · `infra/supabase` 3 · `skills/integrations` 3 · `.github/workflows` 3 ·
`tests/*` 22 arquivos soltos. `agents/` e `commands/` receberam 5 arquivos cada.

---

## Critério de amostragem da Fase 1

O conjunto verificável (153) excede 60, então a regra de amostragem do prompt se aplica:

- **todos** os 43 HIGH e MEDIUM-HIGH;
- **30% aleatório** (`random.seed(20261010)`) dos 110 restantes → 33 itens.

**Cobertura: 76 de 153 (50%).**

### Método

Para cada item: (1) reconstrução da remediação pelo git na janela da data de marcação
(`git log --since=<data> --until=<data+1d> -- <alvo>`); (2) contagem de commits no alvo **depois**
da marca (`commits_after`), que é o teste de reversão silenciosa; (3) confirmação no `HEAD` por
símbolo, nunca por linha antiga.

Dois atalhos mecânicos, declarados porque mudam o que "verificado" significa:

- **`commits_after = 0`** — o `HEAD` do alvo é literalmente o estado deixado pelo commit da
  janela. Reversão silenciosa é impossível por construção; a confirmação no `HEAD` foi feita por
  amostra dentro de cada grupo que compartilha arquivo (o cluster `02c-full-suite-guard.sh`, com
  6 fingerprints num arquivo, foi conferido uma vez e vale para os 6).
- **`commits_after > 0`** — confirmação manual no `HEAD`, item a item.

Alvos não resolvíveis a partir da descrição (entradas legadas sem o campo `alvo:`, que nomeiam
agentes por nome e não por caminho) foram resolvidos por basename contra `git ls-files`; onde nem
isso resolveu, o item foi verificado pela afirmação e não pelo arquivo.

---

## Placar

| Marca | N | % |
|---|---|---|
| ✅ **Feito** | 64 | 84,2% |
| 🟡 **Parcialmente feito** | 6 | 7,9% |
| 🔴 **Não feito** | 6 | 7,9% |

**Reaberturas novas neste pass: 1 de 76 (1,3%)** — as outras 5 🔴 já estavam reabertas em passes
anteriores e foram reconfirmadas. O limiar de escalonamento (15% da amostra) **não** foi atingido:
a integridade do banco está intacta.

---

## 🔴 Reabertura nova

### `docs-sync-reports-index-preamble-declares-archive-index-trigger-less-while-stop-99b-dispatches-it`

- **Marca original:** ✅ **Executed:** 2026-09-11 · **Severidade:** MEDIUM-HIGH
- **Alvo:** `docs/reports/_index.md`
- **Commit examinado:** nenhum. `git log --since='2026-09-11 00:00' --until='2026-09-11 23:59' -- docs/reports/_index.md`
  devolve vazio. Os commits do arquivo em volta da data são `3acaa89` (2026-09-12) e `6b3846f`
  (2026-09-18), ambos "add guardian audit pass", nenhum tocando o preâmbulo. **A marca é 🔴 por
  construção.**
- **Evidência no `HEAD`:** `docs/reports/_index.md:23-26` —
  "**Rotation:** entries older than 90 days are meant to move to `_index-archive-YYYY-Q.md` via
  `helpers/archive-index.sh`. **That script currently has no trigger** — no hook, no CI job, no
  installer call — so rotation has never run."
  Contra `scripts/hooks/stop/99b-archive-index.sh:21` — `SCRIPT="$REPO_ROOT/helpers/archive-index.sh"` —
  um sub-script Stop que existe, está na tier de cleanup e tem stamp diário
  (`:35` `STAMP_FILE="$STAMP_DIR/.last-archive-index"`).
- **Por que a marcação está errada:** a remediação registrada foi a criação do `99b`, que de fato
  aconteceu (e o fingerprint `flow-helpers-archive-index-sh-orphan-of-hook-…` está corretamente
  ✅). O que **não** aconteceu foi a correção do preâmbulo que esse mesmo fingerprint cita. O
  arquivo que serve de banco de auditoria afirma, na linha 25, um fato falso sobre a própria
  automação do repositório — e é a primeira coisa que todo pass de auditoria lê.

---

## 🟡 Parcialmente feito (6) — todas reconfirmações

| Fingerprint | Sev | Evidência no `HEAD` |
|---|---|---|
| `flow-size-limits-sh-ci-only-warn-only-not-in-stop-dispatcher-asymmetric-with-agent-lint-200-cap-never-blocking` | HIGH | **3ª confirmação.** `grep -rn size-limits scripts/hooks/ .github/` devolve uma única linha: `.github/scripts/ci/01-lint.sh:91` — `blocking "size-limits" bash helpers/size-limits.sh`. CI segue bloqueante; `scripts/hooks/stop/` (13 sub-scripts) não tem nenhuma checagem de tamanho. |
| `auto-update-no-integrity-check` | MEDIUM-HIGH | `scripts/install.sh.sha256` não existe (`ls` → No such file) e `scripts/lib/installer-fetch.sh:182-197` documenta e implementa a falha aberta: "No digest available → proceed … the project publishes none today". Integridade de transporte, não de autenticidade. |
| `ref-two-malformed-git-tags-v-1-1-0-and-v-1-3-13-violate-vx-y-z-convention` | LOW-MEDIUM | ⚠️ Partial confirmada: `git tag` tem 177 tags conformes e exatamente as 2 malformadas (`v.1.1.0`, `v.1.3.13`), deixadas de propósito. |
| `ref-notification-system-content-triplicated-across-04-notifier-sh-notifier-skill-and-claude-md-notifications-md` | MEDIUM | O sub-escopo do drift fechou (`CLAUDE-md/hooks.md:31` já tem a linha `05-` de telemetria), a triplicação não: `skills/shared/notifier/SKILL.md` 82 linhas · `CLAUDE-md/notifications.md` 116 · `scripts/hooks/stop/04-notifier.sh` 221. |
| `token-git-log-window-overshoot` | LOW | `git log --oneline -10` segue inline em `agents/security-specialist.md:31`, `agents/ui-ux-designer.md:29` e `agents/qa-specialist.md:28`, nos três com o `project-context` já carregado logo acima (`:23`, `:21`, `:22`), que cobre "recent git log". |
| `token-current-context-block-deduplication` | LOW-MEDIUM | 29 de 32 arquivos em `commands/` mencionam `current-context`; 24 carregam o `SKILL.md`. A dedup parcial entregue não removeu o bloco repetido. |

---

## ✅ Amostra da confirmação (itens com `commits_after > 0`, verificados no `HEAD`)

- `ref-docs-agents-md-model-column-wrong-…` — HIGH. A coluna "Model" não existe mais em
  `docs/agents.md`; `:20-34` traz `Tier` (`reasoning`, `backend-exec`, `frontend`, `repetitive`).
  O dado errado foi removido junto com a coluna.
- `ref-claude-md-183-code-reviewer-roles-…` — HIGH. `grep -n code-reviewer CLAUDE.md` devolve só
  `:210` (tabela de comandos); os papéis do router migraram para `CLAUDE-md/commands.md` e em
  nenhum dos dois há a afirmação de delegação aos test specialists.
- `ref-two-helpers-dirs-naming-collision-…` e `ref-claude-md-file-structure-omits-helpers-and-privacy-and-claude-md-folder`
  — HIGH. `CLAUDE.md:315` documenta `scripts/helpers/` ("SHIPS and runs in user projects"),
  `:349` a semântica oposta de `helpers/`, e `PRIVACY.md` e `CLAUDE-md/` aparecem na árvore
  (13 referências a `CLAUDE-md/`).
- `flow-helpers-archive-index-sh-orphan-of-hook-…` — HIGH. `scripts/hooks/stop/99b-archive-index.sh`
  existe e dispara `helpers/archive-index.sh` com stamp diário.
- `ref-check-updates-shim-and-update-sh-exec-renamed-away-01-check-updates-hook` — HIGH
  (marca de 2026-09-30, commit `a0df626`). `scripts/check-updates.sh` foi reescrito: 30 linhas sem
  nenhum `exec` de hook, e `scripts/hooks/session-start.sh:191` traz o comentário
  "Update check (moved from pre-tool-use/01-check-updates.sh)".
- `agent-line-cap-205-documented-in-claude-md-vs-211-enforced-by-size-limits` — HIGH
  (marca de 2026-10-02). `CLAUDE.md:102` agora diz "enforces 211" contra
  `helpers/size-limits.sh:44` — `AGENT_LIMIT=211`. Convergente.
- `ref-agent-creator-location` — LOW-MEDIUM. `CLAUDE.md:208-209` descreve corretamente a
  localização (`.claude/skills/agent-creator/`), o destino no pacote (stripado por
  `strip-tarball.sh`) e, de quebra, o `repo-release-prep` renomeado. O sub-escopo que mantinha a
  marca em 🟡 fechou; promovido a ✅.
- **Cluster `02c-full-suite-guard.sh`** (6 fingerprints, marca 2026-10-02, `commits_after = 0`):
  os comentários de remediação estão no `HEAD` — `:30` explica o consumo de pares de escape que
  resolvia as chaves-irmãs do JSON, `:152` registra "`cmake` is a different command and never
  lands here", `:40` o escape hatch restrito ao caminho de bloqueio. Confirmados.
- **Cluster `commands/merge.md`** (4 fingerprints, marca 2026-10-02): `:23-25` resolve a sessão de
  worktree **antes** das branches, e `:37` faz o strip de `--flag` antes de pegar o target.
  Confirmados.
- `flow-pre-tool-use-dispatcher-sigpipe-141-masks-02c-block` — HIGH. `scripts/hooks/pre-tool-use.sh:21`
  documenta o SIGPIPE 141 e `:10` traz o `set -euo pipefail` que o trata.

---

# Fase 1b — Validade dos achados abertos

**Cobertura: 109 de 109 (100%).**

### Método

O conjunto aberto foi particionado pelo delta de código:

- **35 itens** cujo alvo foi tocado por algum dos 62 commits desde `5e338d9` → verificação manual
  no `HEAD`, um a um. É onde uma correção de passagem pode ter acontecido.
- **74 itens** cujo alvo **não** recebeu nenhum commit desde o registro → ainda reproduzem por
  construção: um problema num arquivo que ninguém tocou não foi corrigido. Esse é o atalho que
  torna 100% de cobertura honesto em vez de decorativo, e está declarado aqui para que o próximo
  pass saiba exatamente o que foi e o que não foi lido.

## Mortalidade: 2 de 109 (1,8%)

### 🟢 Resolved

- `flow-install-cli-orphan-body-outside-main-aborts-every-run` — **HIGH**, o achado principal do
  pass de 2026-10-02 — **resolvido por `5dcf340`** ("fix(cli): remove stale duplicate install code
  from install-cli.sh"), commit posterior ao baseline `5e338d9`. No `HEAD`:
  `bash scripts/install-cli.sh --help` sai 0 e imprime o uso; `main()` abre em `:27`, fecha em
  `:163` e `:165` é `main "$@"` — não há corpo órfão. O canal macOS/Linux da ADR-0028 voltou.
- `docs-sync-auto-learn-before-commit-still-documented-as-pre-commit-step-0` — **MEDIUM-HIGH** —
  **resolvido pela ADR-0034**, não pela remediação proposta. A proposta era corrigir a
  documentação para dizer "pós-commit"; `f754cde` ("feat(commit): run learn silently before
  grouping commits") e `b3c0dc1` moveram o *código* de volta para antes do commit, e a
  documentação, que já dizia isso, ficou correta. `commands/commit.md:88` roda
  `/devteam:learn --embedded` no Step 2.7 antes do agrupamento; `CLAUDE-md/preferences.md:69`
  e `skills/shared/user-preferences/SKILL.md:97` descrevem exatamente isso.

### ⚰️ Obsoleto: nenhum.

## Alvos tocados pelo delta que **não** foram corrigidos (amostra verificada)

Vinte dos 21 achados de 2026-10-02 seguem reproduzindo. Os que mais importam, com evidência fresca:

| Fingerprint | Evidência no `HEAD` |
|---|---|
| `ref-relayout-quality-skills-list-cites-seven-nonexistent-shared-paths` | 7 dos 8 caminhos de `commands/relayout.md:35` seguem mortos: `frontend-design` e `design-system-audit` e `mobile-design` estão em `skills/design/`, `frontend-code-quality`/`component-patterns`/`css-quality`/`accessibility-patterns` em `skills/architecture/`. Só `frontend-done-checklist` existe em `skills/shared/`. |
| `ref-orphan-skill-scan-blind-to-directory-form-skill-refs` | `helpers/orphan-skill-scan.sh:72` segue com `grep -oE 'skills/[a-zA-Z0-9/_-]+/SKILL\.md'`. Rodado hoje: `clean ✓` — com os 7 caminhos mortos acima na árvore. |
| `docs-sync-user-data-keep-root-omits-plugins-and-names-wrong-repo-only-skill` | `CLAUDE-md/user-data.md:105` segue dizendo `agents scripts skills templates commands` contra `scripts/install.sh:400` — `KEEP_ROOT=(agents scripts skills templates commands plugins)`; `:99` segue nomeando `release-prep`. Dois commits pós-baseline (`aa56667`, `82a5772`) tocaram o arquivo sem corrigir. |
| `auto-release-workflow-has-no-guard-for-auth-config-placeholders` | `grep 'REPLACE-ME\|auth-config\|gate_mode' .github/workflows/release.yml` → vazio, **mesmo depois** de `a2933cd` ("ci(release): prepare Homebrew, winget and signed app releases") reescrever o workflow. |
| `flow-02c-double-dash-counted-as-scope-lets-npm-full-suite-through` | `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:57` — o `case` de `has_scope` segue com `--) return 0`. |
| `agent-security-specialist-outside-review-result-set-task-board-blind-to-findings` | `helpers/agent-lint.sh:115` — `REVIEW_RESULT_AGENTS="qa-specialist code-reviewer backend-reviewer frontend-reviewer"`; `scripts/lib/devteam/review_triggers.py:17` idem. `security-specialist` fora dos dois, e `433e4e1` tocou o agente (para rotear a skill Cloudflare) sem incluí-lo. |
| `agent-review-agent-roster-hardcoded-in-five-places-no-canonical-home` | A regex segue duplicada literalmente: `pre-tool-use/04-task-board.sh:33` e `post-tool-use/01-task-board.sh:32`, e `grep -rn REVIEW_TYPE_RE tests/` continua vazio. |
| `agent-no-claude-attribution-restated-in-five-agents-frontend-dev-has-no-commit-rule` | `grep -c commit agents/frontend-developer.md` → **0**. |
| `flow-install-provider-gate-fallback-fails-open-without-gate-lib` | `scripts/install-provider.sh:126-128` — sem `devteam` no PATH o `else` imprime "account check skipped" e segue; um release em `enforce` se comporta como `allow`. |

## Fingerprints abertos que **mediram pior** que no registro (re-ancoragem pendente)

| Fingerprint | Registrado | `HEAD` |
|---|---|---|
| `token-claude-md-426-lines-still-monolithic-…` | 426 → 602 linhas | **647** linhas (`size-limits.sh` já emite WARN: "647 lines (warning threshold: 600, fails at 700)") |
| `token-151-skills-flat-symlinked-into-claude-skills-index-12751-chars-per-context` | 151 de 152 skills | **155** skills |
| `token-checks-list-loads-all-three-provider-blocks-after-step-0-resolved-one` | 668 linhas | **681** linhas |
| `docs-sync-readme-ptbr-agents-link-points-to-english-doc` | 1 link (`:141`) | **7 links** para docs EN: `README.pt-BR.md:60,61,62,66,262`, `docs/harness.pt-BR.md:179`, `docs/installation.pt-BR.md:5` (×2) |
| `docs-sync-readme-command-table-omits-devteam-install-in-both-languages` | 34 de 35 | `grep -c 'devteam:install'` → **0** em `README.md` e em `README.pt-BR.md` |
| `docs-sync-claude-md-173-says-all-devteam-commands-load-current-context-while-213-lists-four-exceptions` | 4 exceções, `CLAUDE.md:173/213` | **re-ancorar:** a afirmação está em `CLAUDE.md:216` ("All `/devteam:*` commands") e a lista de exceções migrou para `CLAUDE-md/commands.md:51`, agora com **seis** declaradas "the complete list" mais cinco que "name it in prose" |
| `flow-claude-md-no-agent-command-list-says-seven-omits-push-and-merge` | `CLAUDE.md:258` | **re-ancorar:** o parágrafo migrou para `CLAUDE-md/commands.md:57` e **ainda diz "All seven"**, contra `scripts/lib/commands.json:7`, que enumera nove |
| `docs-sync-telemetry-fresh-install-default-documented-true-while-install-sh-writes-false-without-consent` | `CLAUDE.md:386`, `install.sh:1057/1117` | **re-ancorar:** `CLAUDE.md:370` e `scripts/install.sh:1181` (`TELEMETRY_VALUE="false"`); a contradição persiste no caminho não-interativo (`curl … \| bash`) |
| `docs-sync-session-start-comment-cites-nonexistent-02b-full-suite-guard` | `session-start.sh:175` | **re-ancorar:** `scripts/hooks/session-start.sh:249` |
| `token-fix-patterns-517-lines-loaded-whole-to-apply-one-of-25-auto-fixes` | 517 linhas | **457** linhas — o único que mediu **melhor** |

## Mudança de forma num achado aberto

`docs-sync-claude-md-102-states-skill-desc-strict-false-non-blocking-while-agent-lint-31-sets-true-and-ci-promoted-it-same-day`
(**HIGH**, o mais antigo em aberto) **mudou de forma e ficou pior**. No registro, a contradição era
`CLAUDE.md` dizendo `SKILL_DESC_STRICT=false` contra `helpers/agent-lint.sh` dizendo `true`. No
`HEAD`, `grep -rn SKILL_DESC_STRICT helpers/agent-lint.sh` devolve **vazio**: a variável não existe
mais. Sobraram três referências a um knob que não existe — `CLAUDE.md:139`
("non-blocking warning today (`SKILL_DESC_STRICT=false`)"), `helpers/agent-lint.sh:327`
("description budget (warning — see SKILL_DESC_STRICT)") e
`.github/scripts/ci/01-lint.sh:66` ("`SKILL_DESC_STRICT=true` in helpers/agent-lint.sh"), as duas
últimas em desacordo entre si sobre o valor de uma variável removida. A re-ancoragem está anotada
no banco; não abri achado novo porque o tema é o do fingerprint-pai.
