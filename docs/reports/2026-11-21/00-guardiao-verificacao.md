# Fase 1 e 1b — Verificação Guardiã — 2026-11-21

**Baseline:** `HEAD` = `17bfb26` · **Baseline anterior:** `c6398e5` · delta de **14 commits e 271
arquivos**, dos quais **190 são guias do skill vendorizado** `modern-web-guidance` — a superfície
autoral do delta são **55 arquivos**.

Working tree com 4 arquivos modificados em `app/src/renderer/` e `app/test/`, nenhum deles alvo de
fingerprint; toda evidência abaixo foi lida do disco, que coincide com o `HEAD` fora desses 4.

---

## Método

**Conjunto verificável** (Fase 1) = fingerprints ✅ Executed + ⚠️ Partial no `_index.md` vivo:
**22 de 159 entradas**. Abaixo do limiar de 60, logo **sem amostragem: 22 de 22 (100%)**.

**Conjunto de exclusão** = 22 ✅ Executed + 12 🟢 Resolved + 2 ⚰️ Obsoleto + 0 ↩️ Reverted.
**Conjunto aberto** (Fase 1b) = **123 fingerprints** sem marcador.

Nota de método herdada de 2026-10-17 e aplicada em **todos** os 22 itens: o campo `alvo:` nomeia o
arquivo que **descreve** o problema, não o que foi corrigido. A janela de commit foi aberta sobre o
alvo da **remediação** reconstruída do git, não sobre o `alvo:` do registro. Sem isso, ao menos
`skill-spec-gate-scope-lock-hard-gate-unreachable-by-execution-agents` (remediado em `agents/*.md`,
não em `skills/shared/spec-gate/SKILL.md`) teria dado um 🔴 falso.

---

## Placar

| Marca verificada | Itens | % |
|---|---|---|
| ✅ **Feito** | 16 | 72,7% |
| 🟡 **Parcialmente feito** | 5 | 22,7% |
| 🔴 **Não feito** | 1 | 4,5% |

**Divergências novas neste pass: 3** — 1 🔴 e 2 🟡 que nenhum pass anterior havia anotado. As
outras 3 🟡 já carregavam anotação de 2026-10-02 / 2026-11-07 e foram reconfirmadas.

O **4,5% de reaberto novo** está muito abaixo do limiar de escalonamento de 15%, mas **quebra a
sequência de quatro passes em 0%** (2026-10-17, 2026-10-24, 2026-11-07, 2026-11-14).

---

## 🔴 Não feito — 1

### `flow-merge-md-merge-only-option-cites-undefined-follow-up-choice`

- **Marca original:** ✅ **Executed:** 2026-10-02 (LOW-MEDIUM)
- **Marca verificada:** 🔴 **Não feito**
- **Commit examinado:** `a2cf59c` (2026-10-02, `fix(commands): fire the learn nudge on a moved
  branch tip, reach worktree finalization in merge`) — o **único** commit da janela que tocou
  `commands/merge.md`.
- **Evidência:** `git show a2cf59c -- commands/merge.md` reescreve os Steps 1, 2 e 4 e **não toca a
  linha do achado**. No `HEAD`, `commands/merge.md:48` — "`- **Merge only (assume already
  committed)** — skip commit, run the merge from whichever of the two paths above was implied by a
  follow-up choice.`" — é o texto literal do enunciado original, e
  `grep -n 'follow-up' commands/merge.md` devolve **essa única linha** no arquivo de 95 linhas: nada
  define o follow-up.
- **Reversão silenciosa:** não houve reversão; a linha nunca foi tocada. `git log --since=2026-10-02
  -- commands/merge.md` lista `a2cf59c`, `f4986ea` (2026-10-17) e `bd1313f` (2026-10-18); nenhum dos
  dois posteriores mexe nessa opção.
- **Por que a marcação está errada:** `a2cf59c` resolveu **três outros** achados do mesmo arquivo na
  mesma janela (`flow-merge-md-branch-and-tree-resolved-before-worktree-detection`,
  `flow-learn-nudge-ancestor-test-inverted-in-four-commands`,
  `flow-merge-md-arguments-target-branch-parse-can-swallow-no-teardown-flag`). A marca ✅ foi
  aplicada em lote ao arquivo, não ao item — o commit nunca tratou deste.

---

## 🔴 Correção de marca fora do conjunto amostrado — 1

Esta marca não pertence ao conjunto verificável (é 🟢, não ✅), mas a varredura do Eixo B produziu
evidência direta de que está errada. Registrá-la aqui, e não como fingerprint novo, é o que a Porta 3
do Protocolo Anti-Duplicação exige (ver "Descartados por duplicação" no `index.md`).

### `flow-claude-md-no-agent-command-list-says-seven-omits-push-and-merge`

- **Marca original:** 🟢 **Resolved:** 2026-10-24 — "o parágrafo dos sete comandos sem agente saiu do
  `CLAUDE.md`".
- **Marca verificada:** 🔴 **Não feito** — o parágrafo **não foi corrigido, foi movido**, e para um
  arquivo que **ships**.
- **Commit examinado:** `309bebc` (`docs(v3): document the global store and bind, extracting the
  command table`) — extraiu a tabela de comandos de `CLAUDE.md` para `CLAUDE-md/commands.md`.
- **Evidência no `HEAD`:** `CLAUDE-md/commands.md:65` — "`/devteam:update`, `/devteam:symlinks`,
  `/devteam:health-check`, `/devteam:install`, `/devteam:explain`, `/devteam:version` and
  `/devteam:status` spawn **no** agent; […] **All seven** name `technical-writer` […] Do not read
  those **seven** rows as a delegation target." Contra `scripts/lib/commands.json`
  (`_filler_agent_note`): "`update`, `symlinks`, `health-check`, `install`, `explain`, `push`,
  `merge`, `version` and `status` spawn NO agent" — **nove**, incluindo `push` e `merge`, exatamente
  os dois que o enunciado original dizia estarem omitidos.
- **Agravante que o pai não tinha:** `CLAUDE.md` é removido do pacote pelo `KEEP_ROOT` de
  `scripts/install.sh:400` (`KEEP_ROOT=(agents scripts skills templates commands plugins)`);
  `CLAUDE-md/` é a fonte do bloco gerenciado que chega ao projeto instalado. A afirmação falsa saiu
  de um arquivo que não ships e entrou em um que ships.
- **Correção aplicada ao `_index.md`:** `— 🔴 **Reaberto na verificação de 2026-11-21:** o parágrafo
  foi movido por `309bebc` para `CLAUDE-md/commands.md:65`, que ships, e segue dizendo "seven"
  contra os nove de `commands.json` (`_filler_agent_note`), `push` e `merge` incluídos.`

---

## 🟡 Parcialmente feito — 5

### `flow-02c-escape-hatch-anchored-while-detection-is-substring` — 🟡 reconfirmada (anotada em 2026-11-07)

- **Commit examinado:** `ddeaee6` / `64ecf2a` (2026-10-02).
- **Entregue:** a escotilha deixou de exigir posição 0 —
  `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:47`:
  `CONFIRM_RE='(^|[[:space:];&|(])DEVTEAM_FULL_SUITE_CONFIRMED=1([[:space:]]|$)'`.
- **Falta, exatamente:** a classe de prefixo não admite `"` nem `'`. O teste da escotilha (`:48`,
  `[[ "$COMMAND" =~ $CONFIRM_RE ]] && exit 0`) corre sobre `$COMMAND` **cru**, antes de
  `is_full_suite` remover as aspas em `:188` (`cmd=$(printf '%s' "$cmd" | tr -d "\"'\`" …)`). O
  wrapper que o próprio arquivo cita em `:184` — `docker exec x sh -c "pnpm test:run"` — segue sem
  escotilha viável: `sh -c "DEVTEAM_FULL_SUITE_CONFIRMED=1 npm test"` tem `"` imediatamente antes da
  variável e não casa.

### `flow-merge-md-rebases-onto-target-while-delegating-to-base-step-8` — 🟡 reconfirmada (anotada em 2026-10-02)

- **Entregue desde então:** `commands/merge.md:33` passou a **avisar** — "If an explicit target
  differs from the worktree base `<b>`, say so: any rebase goes onto the target, not `<b>`".
- **Falta, exatamente:** a contradição mecânica permanece. `commands/merge.md:46` ainda manda
  "**Commit + rebase onto `<target>`** […] delegate entirely to `skills/shared/worktree/SKILL.md` §
  Worktree Setup step 8", e `skills/shared/worktree/SKILL.md:56` diz "8. Finalize on merge: **rebase
  onto base** → resolve → commit → merge". O `:111` da skill repete "rebase onto the base first".
  Nenhum mecanismo repassa `<target>` como base, e a skill não é tocada desde `58e58bc`. O aviso
  informa o usuário; não muda o que o passo 8 faz.

### `auto-install-sh-bash-source-fallback-resolves-to-cwd-and-sources-project-lib` — 🟡 reconfirmada (anotada em 2026-11-07)

- **Entregue:** o fallback nomeado está sanado em `scripts/install.sh:62-65` — `if [ -n
  "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then` com o comentário de `:58-61`
  explicando por que `$0` não serve.
- **Falta, exatamente:** `scripts/install.sh:24` —
  `_dta_py="$(dirname "${BASH_SOURCE[0]}")/lib/python.sh"` — reintroduziu o padrão **sem guarda**, 3
  linhas depois de `set -euo pipefail` (`:21`). Sob `curl … | bash`, `BASH_SOURCE[0]` não existe e o
  script aborta com `BASH_SOURCE[0]: unbound variable` antes de chegar à correção de `:62`. O pass de
  2026-11-14 identificou `d454f63` como quem reintroduziu; segue no `HEAD`.

### `auto-ci-never-executes-install-sh-nor-new-adr-sh-only-shellcheck-gate` — 🟡 **nova**

- **Marca original:** ✅ **Executed:** 2026-10-02 (MEDIUM).
- **Entregue, e é real:** `scripts/new-adr.sh` passou a ser **executado** sob sua invocação
  documentada — `tests/test_audit_report_fixes.py:55`
  (`subprocess.run(["bash", str(scripts / "new-adr.sh"), title], cwd=proj, …)`) e
  `tests/test_index_lint.py:268`, ambos rodados em CI por `.github/scripts/ci/03-python.sh`. Os
  instaladores delegados (`install-opencode.sh`, `install-codex.sh`) rodam em fixture via
  `.github/scripts/ci/provider/40-install-fixture.sh:39-40,48`, e `slim-bootstrap.sh:121` **parseia**
  o `KEEP_ROOT` de `install.sh` em vez de restatá-lo.
- **Falta, exatamente:** `scripts/install.sh` — o instalador principal, 1.405 linhas — **segue sem
  execução nenhuma**. A linha que o achado citou está intacta e verbatim:
  `.github/scripts/ci/provider/40-install-fixture.sh:19-21` — "`if [ "$PROVIDER" = "claude" ]; then
  echo "claude fixture install: skipped (Claude installer downloads from network; covered by
  contract.sh against staging)"; exit 0; fi`". Esse arquivo **não foi tocado por nenhum commit da
  janela de 2026-10-02** (último toque: `0d896b7`, 2026-09-30). Nos testes python, `install.sh` só é
  **lido como texto** (`tests/test_installer_gate.py:186` afirma a ordem de duas strings no script),
  nunca invocado.
- **Por que a marcação está errada:** metade do escopo — a metade que cobre o script de 1.405 linhas,
  e justamente o que produziu os dois bugs de runtime de `ef69da3` que motivaram o achado.

### `auto-github-actions-pinned-to-mutable-major-tags` — 🟡 **nova**

- **Marca original:** ✅ **Executed:** 2026-10-02 (MEDIUM).
- **Entregue, e é substancial:** `2cdec4d` e `a4957f0` (2026-10-02) fixaram a terceiros e aos jobs
  de release. Hoje **27 `uses:`** apontam para SHA de 40 caracteres com comentário de versão —
  `actions/checkout@11d5960a…` ×11, `actions/upload-artifact@ea165f8d…` ×6,
  `actions/download-artifact@d3f86a10…` ×6, `ruby/setup-ruby@14594264…` ×3,
  `supabase/setup-cli@1dedf2c6…`, `denoland/setup-deno@22d081ff…`.
- **Falta, exatamente:** **17 `uses:` seguem em tag major mutável** —
  `actions/checkout@v4` ×9, `actions/setup-python@v5` ×5, `actions/setup-node@v4` ×3. Dois deles
  carregam a dívida por escrito: `actions/setup-node@v4 # not SHA-pinned: same as ci.yml; pin after
  verifying the SHA`. O enunciado original ("todos os 16 `uses:` apontam para tags major mutáveis")
  virou 17 de 44 — melhor em proporção, pior em número absoluto, porque o workflow dobrou de tamanho
  desde a marca.

---

## ✅ Feito — 16

Cada item: commit da janela que tocou o alvo da remediação + evidência de sobrevivência no `HEAD`.

| Fingerprint | Commit da janela | Evidência no `HEAD` |
|---|---|---|
| `ref-check-updates-shim-and-update-sh-exec-renamed-away-01-check-updates-hook` | `a0df626` (2026-09-30, `fix(scripts): make check-updates.sh a real on-demand update check`) | `scripts/check-updates.sh` é um script real de 50 linhas (`:13` `set -euo pipefail`, `:25-28` `cannot()`, `:40` `uc_setup_http`); `scripts/update.sh:29` faz `exec bash "$SCRIPTS_DIR/check-updates.sh"`, não o hook renomeado; `commands/update.md:99` trata o caso de erro — "Never report 'Up to date' in this case" |
| `flow-pre-tool-use-dispatcher-sigpipe-141-masks-02c-block` | `ddeaee6`, `64ecf2a` (2026-10-02) | `scripts/hooks/pre-tool-use.sh:46` implementa a precedência: `if [ "$SCRIPT_EXIT" -ne 0 ] && { [ "$EXIT_CODE" -eq 0 ] \|\| { [ "$SCRIPT_EXIT" -eq 2 ] && [ "$EXIT_CODE" -ne 2 ]; }; }`; `:42` isola cada sub-script com `env -u BASH_ENV -u ENV bash "$script" < "$INPUT_FILE"` (arquivo, não pipe) e `:21` documenta o SIGPIPE que motivou |
| `flow-merge-md-branch-and-tree-resolved-before-worktree-detection` | `a2cf59c` (2026-10-02) | `commands/merge.md:22` — `ROOT=$(cd "$(git rev-parse --git-common-dir)/.." && pwd)` — resolve o checkout principal **antes** de `:23` ler `.worktree-session`; o Step 2 passou a "Choose the finalization strategy" usando a sessão já lida |
| `flow-learn-nudge-ancestor-test-inverted-in-four-commands` | `a2cf59c` (2026-10-02) | o teste invertido saiu: `commands/merge.md` § Step 4 agora compara `<head-sha>` com a ponta do branch; `grep -rn ancestor commands/*.md` devolve **só** `sprint.md:57`, um uso correto de `git merge-base --is-ancestor`. As três cópias viraram referência: `pr.md:112`, `refactor.md:162`, `audit.md:180` — todas "the canonical learn-nudge check in `commands/merge.md` § Step 4" |
| `flow-merge-md-arguments-target-branch-parse-can-swallow-no-teardown-flag` | `a2cf59c` (2026-10-02) | `commands/merge.md:31` — "strip every `--flag` and the `skip-commit` / `abort-on-dirty` tokens from `$ARGUMENTS`; the first remaining token, if any, is the target" |
| `skill-orchestration-two-sections-both-numbered-check-5-breaks-cross-refs` | `c19f060` (2026-10-02) | `grep -n '^### [0-9]\.' skills/architecture/orchestration/SKILL.md` → 1,2,3,4,5,6 em `:162,177,185,202,225,261`, sem repetição |
| `skill-orchestration-preamble-says-three-checks-but-section-has-five` | `c19f060` (2026-10-02) | `skills/architecture/orchestration/SKILL.md:158` — "**Six checks**, in order" — contra os seis cabeçalhos acima |
| `skill-work-feedback-wakeup-cadence-cap-output-conflict-auto-reactivation` | `c19f060` (2026-10-02) | as duas seções `### 5.` sumiram; `skills/shared/work-feedback/SKILL.md:29` define um intervalo único (`work_feedback_interval_minutes`, clamp `[60, 3600]`) e `:58` fixa a precedência: "this loop is the **only** `ScheduleWakeup` loop for the round — the orchestration skill's check 5 does not schedule its own wakeup alongside it" |
| `token-two-schedulewakeup-poll-loops-same-spawn-round-300s-vs-1200-1800s` | `c19f060` (2026-10-02) | mesma evidência: um loop, um intervalo configurável, teto explícito em `:54` ("If all steps are ✅ […] stop scheduling (`stop: true`)") |
| `flow-question-tool-name-in-four-implementation-command-findings-gates` | `d958922` (2026-10-02) | `commands/backend.md:66` — "use `AskUserQuestion` to ask the user what to do"; as ocorrências restantes de `question` em `backend/frontend/fullstack/mobile.md` são chaves do payload JSON (`"questions": [{ "question": …`), não nome de ferramenta |
| `agent-worktree-cascade-delegates-to-unshipped-claude-md` | `c19f060` (2026-10-02) | `agents/mobile-developer.md:40` e `agents/devops-specialist.md:40` (idênticos nos 9) — "resolve the worktree decision with the cascade in `skills/shared/worktree/SKILL.md` § Decision Cascade" — a skill ships. A proibição no ramo `worktree=no` também caiu: a cascata é carregada antes de qualquer edição, "otherwise work on the recorded branch" |
| `skill-spec-gate-scope-lock-hard-gate-unreachable-by-execution-agents` | `c19f060` (2026-10-02, `fix(agents): […] load spec-gate in developer agents`) | `grep -ln spec-gate agents/*.md` → **9** agentes, incluindo os 4 de execução que o `<HARD-GATE>` nomeia: `backend-developer`, `frontend-developer`, `mobile-developer`, `database-specialist` (antes: só `product-analyst`, `qa-specialist`, `software-architect`) |
| `ref-comments-policy-routing-table-points-to-sections-dir-not-references` | `c19f060` (2026-10-02) | `skills/shared/comments-policy/SKILL.md:108-110` roteiam para `references/type-annotations.md`, `references/aaa-pattern.md`, `references/anti-patterns.md`; os três existem em `references/`. A tabela de `:93-96` é outra coisa — seções por linguagem, que de fato vivem em `sections/` (4 arquivos, todos presentes) |
| `docs-sync-preferences-mirror-registry-names-readmes-omits-docs-pair` | `88834b6` (2026-10-02, `fix(scripts): […] sync preferences mirrors`) | `CLAUDE.md:308` lista "`docs/user-preferences.md` / `docs/user-preferences.pt-BR.md`" como espelho; os READMEs saíram do registro. A segunda metade também: `grep -c auto_learn_before_commit` → **3** em cada um dos dois docs |
| `auto-stop-03c-reuse-lint-gates-on-csv-registry-while-harness-writes-md` | `ddeaee6` (2026-10-02) | `scripts/hooks/stop/03c-reuse-lint.sh:22` — `REGISTRY_REL="docs/development/reuse-guidelines.md"` — e `:26` resolve pelo mapa canônico: `REGISTRY_REL="$(devteam_doc_path "$REPO_ROOT" reuse-guidelines)"` |
| `flow-path-rewrites-move-docs-development-but-shipped-scripts-hardcode-it` | `d958922` (2026-10-02, `fix(render): […] drop the docs/development path rewrite`) | `scripts/lib/tool-map.json`: `path_rewrites` é `{}` em claude e opencode, e em codex só `{".claude/agents/dev-team/": ".codex/agents/"}`. Do outro lado, `grep -n 'docs/development' scripts/new-adr.sh helpers/reuse-lint.sh scripts/hooks/stop/03e-adr-gap-check.sh` → **vazio**: os três passaram a resolver por `scripts/lib/docs-root.sh` (`devteam_doc_path`) |

---

## Fase 1b — Validade dos achados abertos

**123 de 123 verificados (100%).** **Mortalidade: 0%** — 0 🟢, 0 ⚰️.

**O zero não é imobilidade.** O alvo de **19 dos 123 abertos (15%)** foi tocado pelo delta, e os
**19 seguem reproduzindo**. Nenhum dos 123 alvos deixou de existir.

### Os 19 alvos tocados pelo delta — todos reproduzem

| Fingerprint | Evidência de que reproduz no `HEAD` |
|---|---|
| `agent-security-specialist-cicd-checklist-github-actions-only-vocabulary` | `agents/security-specialist.md:82` (`${{ github.event.issue.title }}`) e `:86` (`pull_request_target` misuse) sob `### CI/CD Pipeline Security` (`:81`), contra `:29` que manda ler `.gitlab-ci.yml`/`bitbucket-pipelines.yml` |
| `agent-frontend-developer-testability-presumes-reactive-component-model` | `agents/frontend-developer.md:146-147` sob `## Testability` (`:143`): "Decouple data fetching from rendering (smart/dumb component pattern)", "Avoid direct DOM manipulation — prefer reactive state" |
| `docs-sync-readme-command-table-omits-devteam-install-in-both-languages` | **mediu pior.** `grep -c 'devteam:install'` → **0** em `README.md` e `README.pt-BR.md`. A tabela passou de 34 de 35 para **41 de 43**, e agora com **duas** ausências: `install` (ausente do arquivo todo) e `down` (sem linha na tabela, embora `up` tenha) |
| `flow-learn-nudge-has-no-canonical-skill-home-three-inline-copies` | **re-ancorado.** A casa canônica segue sendo um corpo de comando, não uma skill: `CLAUDE.md:483` — "The canonical nudge implementation is `commands/merge.md` § Step 4" — e `pr.md:112`, `refactor.md:162`, `audit.md:180` apontam para lá. O que mudou é que as cópias inline viraram referências ao mesmo caminho que não resolve em projeto instalado nem no Codex |
| `flow-rule-and-sync-rules-listed-as-technical-writer-but-never-delegate` | **re-ancorado** de `CLAUDE.md:240-241` para `scripts/lib/commands.json`: `rule` e `sync-rules` seguem com `"agent": "technical-writer"`, e `grep -c 'Task tool' commands/rule.md commands/sync-rules.md` → **0** nos dois. `CLAUDE-md/commands.md:44-45` herdou as linhas e `:65` não as inclui na lista de filler |
| `docs-sync-claude-md-effort-key-scope-vs-agent-effort-map` | **re-ancorado** de `:64` para `CLAUDE.md:92`: "A fifth key, `effort:`, is present **only** on agents whose tier defines one in `tiers.json` (today: `repetitive`)". `grep -l '^effort:' agents/*.md` → **6** agentes, dos quais só `technical-writer` é `repetitive`; os outros 5 são os do `agent_effort` de `:107` |
| `ref-command-description-duplicated-frontmatter-vs-commands-json` | **mediu pior:** 35 → **43 comandos comparados, 43 com `description` divergente** entre o frontmatter e `commands.json` |
| `docs-sync-claude-md-coding-agents-list-omits-seo-specialist` | `CLAUDE.md:137` enumera **oito** coding agents e diz "It used to be inlined in all eight agents"; `grep -l '^## Worktree Isolation' agents/*.md` → **nove**, com `agents/seo-specialist.md` fora da lista |
| `docs-sync-readme-ptbr-agents-link-points-to-english-doc` | `grep -c 'docs/agents.md' README.pt-BR.md` → **1** |
| `docs-sync-telemetry-fresh-install-default-documented-true-while-install-sh-writes-false-without-consent` | **re-ancorado:** `CLAUDE.md:312` — "`telemetry`, `auto_update` and `branch_overlap_active` are `CONSENT_KEYS` — all default to `true` in a fresh file" — contra `scripts/install.sh:1207` `TELEMETRY_VALUE="false"` (era `:1181`) |
| `docs-sync-reports-index-preamble-declares-archive-index-trigger-less-while-stop-99b-dispatches-it` | verbatim: `docs/reports/_index.md:23-26` segue dizendo "**That script currently has no trigger** — no hook, no CI job, no installer call — so rotation has never run", contra `scripts/hooks/stop/99b-archive-index.sh:21` (`SCRIPT="$REPO_ROOT/helpers/archive-index.sh"`) que casa o `SUBSCRIPT_RE` de `stop.sh:62` |
| `skill-design-system-md-two-divergent-schemas-docs-sync-vs-design-system-audit` | **re-ancorado:** `skills/design/design-system-audit/SKILL.md:102` abre o Step 4 e `:111-137` emitem o concorrente de 7 seções (`## Status`, `## Color Tokens`, `## Typography`, `## Spacing`, `## Components`, `## Patterns to Follow`, `## Patterns to Avoid`), sem `<!-- last-updated -->` |
| `ref-hooks-md-library-rows-omit-data-dirs-sh-sourced-by-ten-scripts` | **mediu pior:** `scripts/hooks/lib/` passou de 10 para **14** arquivos, e `grep -c 'data-dirs.sh' CLAUDE-md/hooks.md` → **0** |
| `agent-security-specialist-outside-review-result-set-task-board-blind-to-findings` | **mediu pior em contraste:** `helpers/agent-lint.sh:117` — `REVIEW_RESULT_AGENTS="qa-specialist code-reviewer backend-reviewer frontend-reviewer seo-specialist"` — cresceu de 4 para **5** agentes e `security-specialist` segue fora; `grep -c 'review-result' agents/security-specialist.md` → **0** |
| `agent-no-claude-attribution-restated-in-five-agents-frontend-dev-has-no-commit-rule` | `grep -c commit agents/frontend-developer.md` → **0**; a regra segue restatada fora da casa canônica (`skills/shared/conventional-commits/SKILL.md:40,48`) em `backend-developer:164`, `devops-specialist:160` **e** `:175` (duas redações no mesmo arquivo), `technical-writer:193`, `mobile-developer:175` |
| `docs-sync-hooks-md-warn-once-library-row-omits-03f-spec-lint-contradicting-line-41` | **mediu pior:** `grep -l warn-once scripts/hooks/stop/*.sh` → **5** consumidores (`03c`, `03e`, `03f`, `03g`, `03h`), contra os dois que a tabela de bibliotecas de `CLAUDE-md/hooks.md` declara. Eram 3 no registro |
| `agent-product-analyst-step6-gates-isolated-infra-on-docker-and-inlines-compose-probe` | **re-ancorado** de `:151-155` para `agents/product-analyst.md:164-168`: "**Gate isolated infra on Docker.** […] only when the **project uses Docker** (a compose file exists) […] Detect quickly: `ls docker-compose.yml docker-compose.yaml compose.yml compose.yaml 2>/dev/null \| head -1`" |
| `gov-interaction-mode-key-ungated-and-undocumented-outside-commands-json` | **mediu pior:** `git grep -c interaction_mode HEAD -- helpers/ .github/ CLAUDE.md CLAUDE-md/` → **vazio**, e o delta adicionou um consumidor novo da chave (`brief`, `"interaction_mode": "optional"`), levando a 43 comandos com a chave e zero gates |
| `docs-sync-commands-md-security-row-omits-full-audit-mode-spawns` | **re-ancorado** de `:33` para `CLAUDE-md/commands.md:34` — "`/devteam:security` \| security-specialist + software-architect \| Security audit or vulnerability analysis" — contra `commands/security.md:26`, que define o FULL AUDIT MODE sem `software-architect` |
| `agent-orchestrator-route-has-no-path-to-architecture-work` (+ o pai `flow-orchestrator-route-table-covers-10-of-42-commands-no-gate`) | **mediu pior:** `agents/orchestrator.md` menciona **11 de 43** comandos (era 10 de 42) |

### Fingerprints abertos que mediram pior — 8

`ref-command-description-duplicated-frontmatter-vs-commands-json` (35 → 43 de 43 divergentes) ·
`ref-hooks-md-library-rows-omit-data-dirs-sh-sourced-by-ten-scripts` (10 → 14 arquivos em
`hooks/lib/`) · `docs-sync-hooks-md-warn-once-library-row-omits-03f-spec-lint…` (3 → 5 consumidores)
· `docs-sync-readme-command-table-omits-devteam-install-in-both-languages` (34/35 → 41/43, com uma
segunda ausência) · `gov-interaction-mode-key-ungated-and-undocumented-outside-commands-json`
(+1 consumidor, 0 gates) · `flow-orchestrator-route-table-covers-10-of-42-commands-no-gate`
(10/42 → 11/43) · `agent-security-specialist-outside-review-result-set-task-board-blind-to-findings`
(`REVIEW_RESULT_AGENTS` 4 → 5, ainda sem ele) · `agent-line-cap-…`:
`agents/product-analyst.md` e `agents/frontend-developer.md` estão em **exatamente 211 linhas**, o
cap de `helpers/size-limits.sh:44`, e 7 dos 19 agentes estão entre 209 e 211.

### Métricas de crescimento do banco, re-medidas

| Alvo | No registro | `HEAD` = `17bfb26` |
|---|---|---|
| `CHANGELOG.md` | 441 → 2.470 | **2.473** |
| `scripts/install.sh` | 503 → 947 → 1.405 | **1.405** (estável) |
| `skills/shared/interaction-patterns/SKILL.md` | 209 → 404 | **404** (estável), × 43 comandos |
| `CLAUDE.md` | 426 → 582 → 602 | **602** — cruza o *warning threshold* de 600 de `helpers/size-limits.sh:88` |
| `README.md` / `README.pt-BR.md` | 228 → 501 | **503** cada |
| `skills/shared/setup-health-check/references/checks-list.md` | 681 → 791 | **889** |
| Total de skills | 151 → 156 | **172** (|- 13 vendorizadas em `skills/third-party/`) |

### Os 104 abertos não tocados pelo delta

Alvo verificado como existente para os **104**; nenhum desapareceu. Com a superfície autoral do delta
em 55 arquivos e nenhum deles alvo desses 104, nenhum caminho de resolução de passagem existe —
coerente com a mortalidade de 0%.

---

## Rotação do banco — executada, falhou, estado restaurado

`bash helpers/archive-index.sh --dry-run` apontou **1 seção com mais de 90 dias** (2026-08-21, 37
entradas). O prompt manda executar sem `--dry-run` nesse caso, e foi executado — com snapshot prévio
dos dois arquivos do banco, porque o próprio banco carrega um HIGH aberto sobre este script.

**Falhou, e é a terceira reprodução de `auto-archive-index-appends-archive-before-index-rewrite-no-rollback`:**

```
→ Archived 2026-08-21 → docs/reports/_index-archive-2026-Q3.md
mv: inter-device move failed: '…/tmp/devteam-archive.8U3Swa/keep.trimmed'
    to '…/docs/reports/_index.md'; unable to remove target: Operation not permitted
```

Exit code real do script: **1**. Estado resultante antes da restauração: `_index.md` **inalterado**
com 787 linhas (a seção de 2026-08-21 ainda lá) e `_index-archive-2026-Q3.md` crescido de 320 para
394 linhas com a mesma seção — **37 slugs duplicados** e
`helpers/check-fingerprint-uniqueness.sh` saindo `✗ Duplicate fingerprint slugs found`, isto é, um
`Stop` vermelho em todo turno do repositório.

Este pass **nomeia o modo de falha** que as duas reproduções anteriores descreveram só como "uma
falha no `mv`": o `mv` de `helpers/archive-index.sh:162` é **entre dispositivos** — `$WORK` fica no
tmp da sessão e o alvo no repositório — logo não é um rename atômico, é copy + **unlink do alvo**.
Qualquer ambiente sem permissão de unlink no diretório do repositório (sandbox, montagem sem delete,
ACL) quebra ali, depois de o append de `:145-146` já ter sucedido. A contagem subiu de 32 para 37
duplicatas apenas porque a seção elegível agora é a de 2026-08-21.

Ambos os arquivos foram restaurados de snapshot e `check-fingerprint-uniqueness.sh` volta a dizer
`✓ All 339 fingerprint slugs are unique across 2 bank file(s)`. **A rotação não aconteceu**: a seção
de 2026-08-21 segue em `_index.md` e o banco vivo segue com 163 entradas.

Nada de novo a registrar — o defeito é o HIGH aberto, e a evidência entrou como re-medição na linha
dele (Porta 5). O que mudou é que a correção agora tem um alvo preciso: ou escrever o resultado
in-place (`cat "$WORK/keep.trimmed" > "$INDEX_FILE"`, que não precisa de unlink e foi o que
funcionou na restauração), ou mover o append do arquivo morto para **depois** da reescrita do índice,
com rollback.
