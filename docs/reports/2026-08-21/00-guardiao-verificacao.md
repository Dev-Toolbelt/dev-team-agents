# Fases 1 e 1b — Verificação guardiã (2026-08-21)

**Data:** 2026-08-21 · **Baseline:** `HEAD` = `a67cac9` · **Baseline anterior:** `c03f898`

## Método e cobertura

| Item | Valor |
|---|---|
| Fingerprints vivos no banco | 171 |
| Conjunto verificável (✅ Executed + ⚠️ Partial) | 119 |
| Critério de amostragem | conjunto > 60 → **todos** os HIGH e MEDIUM-HIGH (18) + amostra aleatória de 30% do restante (30 de 101), semente `20260821` |
| **Cobertura da Fase 1** | **48 de 119 verificados (40%)** |
| Placar Fase 1 | **43 ✅ · 3 🟡 · 2 🔴** — 90% confirmado, **4,2% reaberto** |
| Conjunto aberto (sem marcador) | 42 → alvos da Fase 1b |
| **Mortalidade Fase 1b** | **1 de 42 (2,4%)** — 1 🟢 · 0 ⚰️ · 41 ainda reproduzem |

A taxa de reabertura (4,2%) está bem abaixo do limiar de escalonamento de 15%. **O banco está íntegro
e a verificação não é o achado principal deste pass** — os eixos são.

O trabalho foi dividido em dois blocos de verificação (A e B) mais o bloco de validade dos achados
abertos, todos ancorados em `git show` da janela da marcação, nunca na leitura do relatório-fonte.

---

## Fase 1 — Bloco A (24 itens)



**Baseline:** `HEAD` = `a67cac9` · **Baseline anterior:** `c03f898`

Todos os 24 itens deste bloco foram marcados na janela de **2026-07-31**. A janela contém 41 commits (`git log --date=short | awk '$2=="2026-07-31"'`), dos quais oito concentram praticamente toda a remediação: `bbb311a`, `b4e219f`, `6919564`, `519ca7e`, `c7535b7`, `cc28900`, `2e12335`, `7736e20`.

| # | Fingerprint | Marca original | Marca verificada | Commit examinado |
|---|---|---|---|---|
| 1 | `ref-docs-agents-md-model-column-wrong-…` | ✅ 2026-07-31 | ✅ Feito | `bbb311a` |
| 2 | `ref-claude-md-183-code-reviewer-roles-…` | ✅ 2026-07-31 | ✅ Feito | `bbb311a` |
| 3 | `ref-two-helpers-dirs-naming-collision-…` | ✅ 2026-07-31 | ✅ Feito | `bbb311a` |
| 4 | `ref-claude-md-file-structure-omits-helpers-…` | ✅ 2026-07-31 | ✅ Feito | `bbb311a` |
| 5 | `ref-templates-backlog-template-md-orphan-…` | ✅ 2026-07-31 | ✅ Feito | `6919564` |
| 6 | `ref-refactor-command-missing-interaction-patterns-…` | ✅ 2026-07-31 | ✅ Feito | `6919564` |
| 7 | `ref-two-malformed-git-tags-…` | ⚠️ Partial 2026-07-31 | 🟡 Parcialmente feito (marca já correta) | `c7535b7` |
| 8 | `ref-claude-md-file-structure-skills-subtree-omits-…` | ✅ 2026-07-31 | ✅ Feito | `bbb311a` |
| 9 | `flow-size-limits-sh-ci-only-warn-only-…` | ✅ + 🟡 ×2 | 🟡 Parcialmente feito | `c7535b7` + `7736e20` |
| 10 | `ref-telemetry-honors-pref-but-pref-defaults-true-…` | ✅ 2026-07-31 | ✅ Feito | `2e12335` |
| 11 | `flow-helpers-archive-index-sh-orphan-of-hook-…` | ✅ 2026-07-31 | ✅ Feito | `cc28900` |
| 12 | `auto-update-no-integrity-check` | ✅ 2026-07-31 | ✅ Feito | `2e12335` |
| 13 | `gov-telemetry-send-sh-posthog-key-comments-…` | ✅ 2026-07-31 | ✅ Feito | `2e12335` + `6919564` |
| 14 | `flow-ci-orphan-skill-scan-step-continue-on-error-true-…` | ✅ 2026-07-31 | ✅ Feito | `c7535b7` |
| 15 | `flow-telemetry-pre-tool-use-02-runs-on-every-tool-call-…` | ✅ → 🔴 → 🟢 ×2 | ✅ Feito (linha já correta) | `f1ca129` + `156771b` |
| 16 | `token-pre-tool-use-01-check-updates-forks-python3-…` | ✅ 2026-07-31 | ✅ Feito | `cc28900` (+ `3c46d04`) |
| 17 | `flow-ci-triggers-both-push-and-pull-request-…` | ✅ 2026-07-31 | ✅ Feito | `c7535b7` |
| 18 | `flow-install-sh-chmod-enumeration-omits-scripts-hooks-lib-…` | ✅ 2026-07-31 | ✅ Feito | `2e12335` |
| 19 | `ref-size-limits-sh-no-line-cap-for-commands-…` | ✅ 2026-07-31 | ✅ Feito | `c7535b7` |
| 20 | `auto-installer-error-output` | ✅ 2026-07-31 | ✅ Feito | `2e12335` |
| 21 | `flow-workflows-no-commit-or-pr-step` | ✅ 2026-07-31 | ✅ Feito | `6919564` |
| 22 | `gov-plan-template-vs-skill-duplication` | ✅ 2026-07-31 | ✅ Feito | `6919564` |
| 23 | `flow-orphan-template-scan-no-mapping-…` | ✅ 2026-07-31 | ✅ Feito | `c7535b7` |
| 24 | `agent-security-specialist-body-130-153-hardcodes-…` | ✅ 2026-07-31 | ✅ Feito | `b4e219f` + `519ca7e` |

**Apuração:** 22 ✅ · 2 🟡 · 0 🔴

---

## Item a item

### 1. `ref-docs-agents-md-model-column-wrong-technical-writer-listed-haiku-actually-sonnet-and-setup-assistant-listed-sonnet-actually-opus`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:115`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `bbb311a` — "docs: correct stale authoring standards, structure maps and command tables" — tocou `docs/agents.md` (+44) e `docs/agents.pt-BR.md` (+44). A mensagem do commit registra a decisão: *"Rather than patch two cells, the column is replaced by the agent's actual tier"*.
- **Evidência no HEAD:** `docs/agents.md:35` — "`| \`technical-writer\` | API docs, READMEs, runbooks, changelogs | SUPPORT | \`repetitive\` |`"; `docs/agents.md:36` — "`| \`setup-assistant\` | Project setup + version management | SETUP | \`reasoning\` |`". O espelho pt-BR carrega os mesmos tiers em `docs/agents.pt-BR.md:35-36`. A coluna `Model` deixou de existir e foi substituída por `Tier`, com o mapeamento provider-específico enunciado uma única vez logo abaixo da tabela (`docs/agents.md:38`: "**Tier is the source of truth, not the model name.**").
- **Reversão silenciosa:** nenhuma. Commits posteriores em `docs/agents*.md` (`affc6fe`, `1b5bb08`) só reorganizaram/adicionaram `seo-specialist`.
- **Conclusão:** Corrigido na raiz — a duplicata manual de `tiers.json` foi eliminada em vez de remendada. Os tiers ao HEAD batem com o frontmatter (`agents/technical-writer.md:4` `tier: repetitive`, `agents/setup-assistant.md:4` `tier: reasoning`).

### 2. `ref-claude-md-183-code-reviewer-roles-says-delegates-to-test-specialists-but-impl-routes-to-backend-frontend-reviewer`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:116`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `bbb311a` — o diff em `CLAUDE.md` adiciona o parágrafo corrigido (linha 110 do diff: `+**Code Reviewer roles:** …`).
- **Evidência no HEAD:** `CLAUDE.md:264` — "`**Code Reviewer roles:** \`code-reviewer\` is the entry-point router for \`/devteam:review\`. Before anything else it loads \`skills/shared/review-router/SKILL.md\`, which classifies the git diff as \`BACKEND\`, \`FRONTEND\`, or \`BOTH\`. It then proceeds as \`backend-reviewer\` (\`BACKEND\`), as \`frontend-reviewer\` (\`FRONTEND\`)…`"
- **Conclusão:** O texto agora descreve o roteamento real (reviewers, não test-specialists) e nomeia a skill que implementa a classificação.

### 3. `ref-two-helpers-dirs-naming-collision-root-stripped-vs-scripts-helpers-shipped-claude-md-file-structure-omits-scripts-helpers`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:117`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `bbb311a` — diff em `CLAUDE.md` adiciona tanto a entrada `scripts/helpers/` na árvore (linha 163 do diff) quanto a tabela desambiguadora (linha 180: `+**Two \`helpers\` directories — do not confuse them:**`).
- **Evidência no HEAD:** `CLAUDE.md:360-367`, tabela com duas linhas:
  - `CLAUDE.md:364` — "`| \`helpers/\` (repo root) | **No** — \`rm -rf\` by \`scripts/lib/strip-tarball.sh\` | Dev-only authoring tools for this repo…`"
  - `CLAUDE.md:365` — "`| \`scripts/helpers/\` | **Yes** — inside the allowlisted \`scripts/\` tree | Runtime helpers used by the installed package. Currently \`telemetry-send.sh\`…`"
  - A afirmação é verdadeira ao HEAD: `scripts/lib/strip-tarball.sh:23` — "`rm -rf "$extracted/helpers"               # dev-only authoring tools — not for user projects`"
- **Conclusão:** A colisão de nomes está documentada e o diretório que *é* embarcado aparece na árvore de `CLAUDE.md`.

### 4. `ref-claude-md-file-structure-omits-helpers-and-privacy-and-claude-md-folder`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:118`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `bbb311a` — o diff adiciona as seis entradas ausentes (`helpers/`, `opencode/`, `user-data/`, `.github/`, `PRIVACY.md`, `CLAUDE-md/`).
- **Evidência no HEAD:** todas presentes na árvore de `CLAUDE.md`:
  - `CLAUDE.md:301` — "`├── CLAUDE-md/       ← companion sections of this file (preferences, notifications, user-data, versioning)`"
  - `CLAUDE.md:308` — "`├── helpers/         ← DEV-ONLY authoring tools, never shipped (see "Two helpers directories" below)`"
  - `CLAUDE.md:318` — "`├── opencode/        ← opencode provider plugin source (plugin/dev-team-agents.ts); stripped at install,`"
  - `CLAUDE.md:348` — "`├── .github/         ← CI workflows, issue/PR templates, CODEOWNERS, scripts/ci/ — stripped at install`"
  - `CLAUDE.md:349` — "`├── user-data/       ← runtime state of this repo's own self-install; gitignored and untracked`"
  - `CLAUDE.md:355` — "`├── PRIVACY.md`"
- **Conclusão:** As seis entradas reais de topo estão mapeadas, cada uma com a semântica de empacotamento anotada.

### 5. `ref-templates-backlog-template-md-orphan-confirmed-by-scanner-but-skill-shared-backlog-template-has-inline-template`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:127`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `6919564` — "refactor(commands,scripts): remove cross-cutting duplication, close the size gate" — `templates/backlog-template.md | 35 -----------` (arquivo removido).
- **Evidência no HEAD:** `ls templates/` retorna apenas `adr-template.md`, `plan-template.md`, `reuse-guidelines-template.md`, `runbook-template.md`, `spec-template.md` — o arquivo não existe. A skill que o sombreava permanece como fonte única: `skills/shared/backlog-template/SKILL.md:2` — "`name: backlog-template`". `bash helpers/orphan-template-scan.sh` ao HEAD imprime "`orphan-template-scan: clean ✓`".
- **Conclusão:** O órfão foi eliminado escolhendo a skill como dono canônico do formato; o scanner confirma zero órfãos hoje.

### 6. `ref-refactor-command-missing-interaction-patterns-load-despite-yes-no-prompts`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:128`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `6919564` — diff em `commands/refactor.md` (linha 66 do diff: `+Load \`skills/shared/current-context/SKILL.md\` … Load \`skills/shared/interaction-patterns/SKILL.md\` …`).
- **Evidência no HEAD:** `commands/refactor.md:6` — "`Load \`skills/shared/interaction-patterns/SKILL.md\` and use \`AskUserQuestion\` for every question with a finite set of answers — never a plain-text prompt.`" As três perguntas do corpo passaram a usar o tool: `commands/refactor.md:22`, `:32` e `:162`, todas com `AskUserQuestion`. Nenhuma ocorrência de `(yes/no)` em texto puro no arquivo.
- **Conclusão:** A skill é carregada e todos os prompts finitos migraram para `AskUserQuestion`.

### 7. `ref-two-malformed-git-tags-v-1-1-0-and-v-1-3-13-violate-vx-y-z-convention-in-versioning-md-break-version-sort-and-gap-clean-sequence`
- **Marca original:** ⚠️ Partial (2026-07-31) — "a CI gate now rejects any new tag outside vX.Y.Z. The two published malformed tags were deliberately NOT deleted…" (`_index.md:132`)
- **Marca verificada:** 🟡 Parcialmente feito — **e a marca original já descreve exatamente esse estado**
- **Commit da janela:** `c7535b7` — "ci: close validator and enforcement gaps, repair the rotation helper" — adicionou o job `tag-name` a `.github/workflows/ci.yml` (linhas 113-131 do diff).
- **Evidência no HEAD:** `.github/workflows/ci.yml:38-56`:
  - `:41` — "`if: ${{ github.ref_type == 'tag' }}`"
  - `:48` — "`if ! printf '%s' "$TAG" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$'; then`"
  - O comentário acima do job registra o escopo deliberado: `.github/workflows/ci.yml:34-37` — "`It never enumerates existing tags, which is why the two already-published malformed tags (v.1.1.0, v.1.3.13) cannot retroactively fail CI — they are not re-pushed, so this job never sees them.`"
- **Conclusão:** O gate preventivo existe e é bloqueante; as duas tags publicadas seguem no repositório por decisão explícita do mantenedor (remoção quebraria quem estiver fixado nelas). A linha 132 de `_index.md` já registra isso corretamente e **não precisa de patch** — a parcialidade é uma escolha de projeto documentada, não uma pendência.

### 8. `ref-claude-md-file-structure-skills-subtree-omits-database-mobile-skill-creator-three-of-eleven-domains`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:133`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `bbb311a` — o diff adiciona os três domínios (linhas 120, 124 e 126 do diff).
- **Evidência no HEAD:** `CLAUDE.md:289` — "`│   ├── database/`"; `CLAUDE.md:294` — "`│   ├── mobile/`"; `CLAUDE.md:296` — "`│   ├── skill-creator/ ← user-invocable skill-authoring skill`".
- **Conclusão:** A subárvore `skills/` de `CLAUDE.md` cobre os domínios reais.

### 9. `flow-size-limits-sh-ci-only-warn-only-not-in-stop-dispatcher-asymmetric-with-agent-lint-200-cap-never-blocking`
- **Marca original:** ✅ Executed 2026-07-31, com dois reparos posteriores já registrados: 🟡 Parcial em 2026-07-31 e 🟡 Parcial em 2026-08-14 (`_index.md:139`)
- **Marca verificada:** 🟡 Parcialmente feito — **terceira confirmação**
- **Commits da janela:** `c7535b7` (reescreveu `helpers/size-limits.sh`) e `7736e20` (promoveu o check em `.github/scripts/ci/01-lint.sh`).
- **Evidência no HEAD — parte feita:** `.github/scripts/ci/01-lint.sh:87` — "`blocking "size-limits" bash helpers/size-limits.sh`", precedido pelo registro da promoção em `:82-86` — "`PROMOTED 2026-07-31: every agent, skill and command is now under its declared cap (17/17 agents, 25/25 commands, 138/138 skills).`"
- **Evidência no HEAD — parte faltante (1):** o dispatcher `Stop` continua sem equivalente. `ls scripts/hooks/stop/` retorna `01-session-summary.sh`, `02-orphan-skill-scan.sh`, `02b-orphan-template-scan.sh`, `03-agent-lint.sh`, `03b-fingerprint-uniqueness.sh`, `03c-reuse-lint.sh`, `03d-design-token-lint.sh`, `03e-adr-gap-check.sh`, `05-telemetry.sh`, `99b-archive-index.sh` — nenhum invoca `size-limits.sh`. E `scripts/hooks/stop/03-agent-lint.sh:2` declara o próprio escopo: "`# Stop sub-script: validate agent frontmatter (name / description / tier).`" — `helpers/agent-lint.sh` não contém nenhuma contagem de linhas (`wc -l` não aparece no arquivo).
- **Evidência no HEAD — parte faltante (2), nova:** a afirmação "zero violações" da anotação de 2026-08-14 **não vale mais**. `bash helpers/size-limits.sh` ao HEAD sai com **código 1**: "`⚠ CLAUDE.md: 602 lines (warning threshold: 600)`". O caminho de aviso empurra a mensagem para o mesmo array `VIOLATIONS` (`helpers/size-limits.sh:92`) e o script termina em `exit 1` (`:122`), de modo que o wrapper `blocking` do CI reprova a árvore atual.
- **Conclusão:** Segue 🟡 pelo motivo já registrado (sem gate no `Stop`), agora com um agravante novo: o gate bloqueante do CI está **vermelho no HEAD** por causa do limiar de aviso de `CLAUDE.md`. A parte "zero violações" da anotação de 2026-08-14 ficou obsoleta — sugiro anexar essa observação à linha 139 de `_index.md` e abrir o achado do CI vermelho como item novo da Fase 2.

### 10. `ref-telemetry-honors-pref-but-pref-defaults-true-on-fresh-install-without-prompt-on-non-interactive-curl-bash`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:140`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `2e12335` — "fix(install): make the swap failure-safe and stop enabling telemetry without consent" — `scripts/install.sh | 240 ++++++…`
- **Evidência no HEAD:** `scripts/install.sh:1050-1056` documenta a inversão do default — "`Telemetry is only ever enabled when the user was actually given the chance to decline it. The default is DISABLED… (Previously the value was preset to "true" and the prompt was gated on \`[ -t 0 ]\`, which is false under the documented \`curl … | bash\` install…)`"; `scripts/install.sh:1057` — "`TELEMETRY_VALUE="false"`". O caminho sem TTY é explícito: `scripts/install.sh:1090` — "`echo "→ NOTE: No terminal available to ask about anonymous telemetry, so it is DISABLED."`". O prompt lê de `/dev/tty` via `_can_prompt`/`_prompt_read` (`:993-1010`), o que funciona sob `curl | bash`, e timeout/EOF cai em `TELEMETRY_VALUE="false"` (`:1084`) com o comentário "`# Timeout or EOF — silence is not consent.`"
- **Conclusão:** O consentimento passou a ser condição necessária. `preferences-defaults.json:14` ainda traz `"telemetry": true`, mas isso é o default de arquivo novo — `install.sh` sobrescreve com o valor consentido, e `CLAUDE.md` classifica a chave como `CONSENT_KEY`.

### 11. `flow-helpers-archive-index-sh-orphan-of-hook-eight-days-after-flagged-rotation-90-day-promise-in-index-md-line-19-20-has-no-trigger-cron-ci-stop-hook-or-update-sh`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:141`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `cc28900` — "fix(hooks): gate, decompose and harden the lifecycle dispatchers" — criou `scripts/hooks/stop/99b-archive-index.sh` (+54).
- **Evidência no HEAD:** `scripts/hooks/stop/99b-archive-index.sh:2-3` — "`# Stop sub-script: rotate fingerprint sections older than 90 days out of docs/reports/_index.md into quarterly archives (helpers/archive-index.sh).`"; `:39` — "`OUTPUT="$(bash "$SCRIPT" 2>&1)" || OUTPUT=""`". O sub-script fica no tier de limpeza com justificativa registrada (`:5-9`) e é gateado por um carimbo diário (`:25-33`, `.last-archive-index`). O arquivo **não** tem prefixo `_disabled-`, portanto o dispatcher `scripts/hooks/stop.sh` o executa.
- **Conclusão:** O helper deixou de ser órfão — tem gatilho real (Stop, uma vez por dia) e degrada em no-op silencioso em projetos instalados, onde `helpers/` é removido (`:19-22`).

### 12. `auto-update-no-integrity-check`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:142`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `2e12335` — criou `scripts/lib/installer-fetch.sh` (+256) e reescreveu `scripts/update.sh` e `scripts/rollback.sh` para consumi-lo.
- **Evidência no HEAD:** `scripts/lib/installer-fetch.sh:16` — "`#   dta_fetch_installer <dest> <ref>       → download + verify install.sh`"; `:37` — "`scripts/install.sh.sha256 published at the same ref.`"; `:209` — "`if [ "$(printf '%s' "$_actual" | tr 'A-F' 'a-f')" != "$(printf '%s' "$_expected" | tr 'A-F' 'a-f')" ]; then`" (mismatch → abort, `:183`). `scripts/update.sh:46` — "`INSTALLER_LIB="$SCRIPTS_DIR/lib/installer-fetch.sh"`" e `:89` — "`passes verification (see the integrity model in scripts/lib/installer-fetch.sh).`"
- **Conclusão:** Ref-pinning + verificação de payload (shape/parse + digest sha256) passaram a valer nos três caminhos — `update.sh`, `rollback.sh` e o auto-update do hook. O modelo de ameaça e seus limites estão documentados no próprio arquivo (`:29-44`).

### 13. `gov-telemetry-send-sh-posthog-key-comments-self-contradict-intentionally-public-vs-replace-before-release-todo-on-default-on-path`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:143`)
- **Marca verificada:** ✅ Feito
- **Commits da janela:** `2e12335` e `6919564`, ambos tocando `scripts/helpers/telemetry-send.sh`.
- **Evidência no HEAD:** `scripts/helpers/telemetry-send.sh:22-31` traz um único bloco de comentário coerente — "`POSTHOG_API_KEY below is this project's PostHog *project* key (the \`phc_\` prefix marks a write-only capture key). Such keys are designed to be embedded in client-side code: they can submit events to the project and nothing else — they cannot read, query, export or modify any data. Shipping it in this file is intentional and is not a secret leak…`". Não há mais nenhum `TODO` no arquivo (`rg -i 'TODO|replace before' scripts/helpers/telemetry-send.sh` → sem resultado). O override por ambiente está declarado e implementado: `:31` — "`POSTHOG_API_KEY="${DEVTEAM_POSTHOG_KEY:-phc_…}"`".
- **Conclusão:** A contradição foi resolvida escolhendo uma posição e justificando-a; o TODO pendente de pré-release sumiu.

### 14. `flow-ci-orphan-skill-scan-step-continue-on-error-true-never-blocks-two-duplicate-loads-standing-unaddressed-for-days`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:145`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `c7535b7` — reescreveu `.github/scripts/ci/01-lint.sh` (+103) e `.github/workflows/ci.yml` (+52).
- **Evidência no HEAD:** a política agora é declarada no topo do script — `.github/scripts/ci/01-lint.sh:5-8` — "`ENFORCEMENT POLICY … Every check below runs through exactly one of two wrappers. There is no third tier and no bare invocation — if you add a check, you must pick a wrapper.`" Os dois wrappers estão implementados em `:38-58`, e cada check advisory carrega um `PROMOTE WHEN:` obrigatório (ex.: `:71-72`). `rg 'continue-on-error' .github/` ao HEAD **não retorna nada** — a expressão de "meio-bloqueante" via chave de workflow foi eliminada. A nuance de exit-code também está fixada: `:27-30` — "`An exit code of 2 or higher means the check itself broke … and always fails the build — a check that cannot run is not a check that passed.`"
- **Conclusão:** Os três níveis viraram dois, com política escrita, e a promoção passou a ser uma troca de uma palavra. `orphan-skill-scan` segue advisory, mas agora por decisão registrada com condição de promoção explícita.

### 15. `flow-telemetry-pre-tool-use-02-runs-on-every-tool-call-without-batching-or-deduplication-burns-200ms-per-burst-session`
- **Marca original:** ✅ Executed 2026-07-31 → 🔴 Reaberto 2026-07-31 → 🟢 Resolved 2026-08-12 → 🟢 correção de crédito 2026-08-14 (`_index.md:149`)
- **Marca verificada:** ✅ Feito — e a linha de `_index.md` já registra a história correta
- **Commits examinados:** `f1ca129` (2026-08-06, "perf(hooks): short-circuit before consent/extraction subprocess forks", `scripts/hooks/pre-tool-use/02b-telemetry.sh | 38 +++---`) e `156771b` (2026-08-11, "feat(telemetry): re-enable PreToolUse queue and Stop flush hooks").
- **Evidência no HEAD:** `scripts/hooks/pre-tool-use/02b-telemetry.sh:30-34` — "`Cheap early-exit BEFORE the consent guard / python3 check below: only Task and Bash tool calls are ever queued, so a raw substring check on the still-unparsed payload skips the consent subshell and python3 fork entirely for every other tool (Read, Edit, Grep, ...)`"; a implementação em `:37-41` é um `case` puro em bash que faz `exit 0` no default. O enfileiramento/flush está em `:3-6` — "`Coupled with stop/05-telemetry.sh — this script only queues events; that one is the only Stop-time flush path.`" O sub-script está ativo (sem prefixo `_disabled-`), ao contrário de `_disabled-01-check-updates.sh` no mesmo diretório.
- **Conclusão:** O achado está resolvido no HEAD. A atribuição registrada em 2026-08-14 confere: o early-exit por substring é de `f1ca129`, não de `156771b`, que apenas reativou o módulo desligado por `ba39c86`. **Nenhum patch necessário na linha 149.**

### 16. `token-pre-tool-use-01-check-updates-forks-python3-to-read-interval-before-ttl-early-exit-on-every-tool-call-burst-overhead`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:150`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `cc28900` — reescreveu `scripts/hooks/pre-tool-use/01-check-updates.sh` (213 linhas alteradas) e extraiu a lógica para `scripts/hooks/lib/update-check.sh` (+260).
- **Evidência no HEAD:** o hook foi posteriormente **removido do caminho quente por completo** — `3c46d04` (2026-08-06, "perf(hooks): move update-check from PreToolUse to SessionStart"). O arquivo hoje é `scripts/hooks/pre-tool-use/_disabled-01-check-updates.sh:2-3` — "`# DISABLED (2026-08-06) — moved to scripts/hooks/session-start.sh so the check runs once per session instead of on every tool call.`" O check vive agora em `scripts/hooks/session-start.sh:126-127` — "`UC_INTERVAL_HOURS=$(uc_interval_hours "$PREFS_FILE" "$STATE_FILE")`" / "`if ! uc_ttl_fresh "$STATE_FILE" "$UC_INTERVAL_HOURS" "$UC_NOW"; then`". O motivo de o fork de `python3` ter voltado a ser aceitável está registrado em `scripts/hooks/lib/update-check.sh:56-59` — "`Since this whole block now runs once per SessionStart (not once per tool call, which is what the original hot-path optimization was guarding against), the extra python3 fork here is negligible`".
- **Conclusão:** A remediação da janela (gate TTL fork-free antes de qualquer subprocesso) foi real e depois **superada por uma correção mais forte**: o hook não roda mais por chamada de tool. O custo por burst que o achado media não existe mais.

### 17. `flow-ci-triggers-both-push-and-pull-request-on-all-branches-duplicate-runs-no-concurrency-cancel-in-progress-guard`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:162`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `c7535b7` — o diff em `.github/workflows/ci.yml` adiciona tanto o estreitamento do trigger quanto o bloco `concurrency` (linhas 77-102 do diff).
- **Evidência no HEAD:** `.github/workflows/ci.yml:16-20` — "`push:` / `branches: [main]` / `tags: ["**"]` / `pull_request:` / `branches: ["**"]`"; `:25-27` — "`concurrency:` / `group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}` / `cancel-in-progress: ${{ github.ref_type != 'tag' }}`". O raciocínio está no cabeçalho (`:3-14`), inclusive por que só a concorrência não resolveria: "`a branch push and its PR event carry different \`github.ref\` values … and therefore land in different concurrency groups`", e o trade-off assumido: "`a branch with no open PR no longer gets CI on push`".
- **Conclusão:** Duplicação eliminada na causa (trigger) e runs supersedidos cancelados, com tags preservadas de cancelamento.

### 18. `flow-install-sh-chmod-enumeration-omits-scripts-hooks-lib-subdir-manual-per-subdir-list-drifts-on-new-hook-subtree`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:163`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `2e12335` — o diff substitui quatro linhas enumeradas por uma varredura recursiva (linhas 293-301 do diff: `-chmod +x "$INSTALL_DIR/scripts/"*.sh` … `+    find "$INSTALL_DIR/scripts" -type f -name '*.sh' -exec chmod +x {} +`). A mensagem do commit registra o diagnóstico: "`chmod enumerated four directories by hand and had drifted past three`".
- **Evidência no HEAD:** `scripts/install.sh:977` — "`find "$INSTALL_DIR/scripts" -type f -name '*.sh' -exec chmod +x {} + 2>/dev/null || true`". É a única invocação de `chmod +x` no arquivo (as demais são `chmod 600` no `credentials.local.json`, `:520`, `:562`, `:571`).
- **Conclusão:** A enumeração manual foi trocada por uma varredura que não pode driftar quando um novo subdiretório de hook é adicionado.

### 19. `ref-size-limits-sh-no-line-cap-for-commands-and-workflows-refactor-md-278-lines-largest-immutable-content-file-unguarded`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:164`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `c7535b7` — o diff em `helpers/size-limits.sh` adiciona `COMMANDS_DIR`, `COMMAND_LIMIT` e o laço de verificação (linhas 86-111 do diff).
- **Evidência no HEAD:** `helpers/size-limits.sh:50` — "`COMMAND_LIMIT=200`", com a justificativa em `:46-49`; o laço em `:74-82`; e o rodapé em `:117` — "`echo " Agents: max $AGENT_LIMIT lines | Skills: max $SKILL_LIMIT lines | Commands: max $COMMAND_LIMIT lines"`". O maior command ao HEAD é `commands/learn.md` com **200** linhas — dentro do cap; `commands/refactor.md` caiu de 278 para 168.
- **Conclusão:** O cap existe, é aplicado e a árvore de `commands/` está limpa. (O gate agregado que o executa no CI está vermelho por outro motivo — ver item 9.)

### 20. `auto-installer-error-output`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:167`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `2e12335` — o diff troca `2>/dev/null` por captura em arquivo nas três chamadas HTTP (linhas 134-171 do diff). Antes: `git show 2e12335^:scripts/install.sh` linha 66 — "`_releases_json=$(HTTP_GET "${GITHUB_API}/releases/latest" 2>/dev/null || true)`".
- **Evidência no HEAD:** `scripts/install.sh:289` — "`_API_ERR="$TMP_DIR/github-api.err"`"; `:292` — "`_releases_json=$(HTTP_GET "${GITHUB_API}/releases/latest" 2>>"$_API_ERR" || true)`"; `:299` (idem para `/tags`); `:326` — "`_DL_ERR="$TMP_DIR/download.err"`"; `:329` — "`HTTP_GET_FILE "$TARBALL_URL" "$TMP_TAR" 2>"$_DL_ERR"`". O stderr capturado é impresso ao usuário no caminho de falha: `:308` e `:336` — "`_print_http_error "$_API_ERR" "  "`" / "`_print_http_error "$_DL_ERR" "  "`".
- **Conclusão:** Nenhum download descarta mais o stderr; o erro do curl/wget chega ao usuário quando o install falha.

### 21. `flow-workflows-no-commit-or-pr-step`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:170`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `6919564` — o diff adiciona a linha de handoff em quatro dos cinco arquivos citados no relatório de origem (linhas 109, 200, 259, 313 do diff).
- **Escopo original:** `docs/reports/2026-07-30/02-fluxos-e-workflows.md:260-261` nomeia exatamente cinco comandos — "`same shape in \`frontend.md\`, \`fullstack.md\`, \`mobile.md\`, \`design.md\``" a partir de `backend.md`.
- **Evidência no HEAD:** todos os cinco fecham com um terminus explícito — `commands/backend.md:99`, `commands/frontend.md:90`, `commands/fullstack.md:98`, `commands/mobile.md:108`, `commands/design.md:29`, todos com o mesmo texto: "`**Hand off** — the working tree is left dirty on purpose. Close with one line naming the next step: \`/devteam:commit\` to group and commit the changes, then \`/devteam:pr\` when the branch is ready for review.`" Comandos criados depois herdaram o padrão (`commands/seo.md:26`, `commands/relayout.md:114`).
- **Conclusão:** Os cinco comandos do escopo original têm terminus. (Nota fora do escopo deste fingerprint, para a Fase 2: `commands/fix.md` — também um comando de implementação — segue sem linha de handoff.)

### 22. `gov-plan-template-vs-skill-duplication`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:171`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `6919564` — `skills/shared/plan-mode/SKILL.md | 70 ++++-----------------` (remoção da cópia) e `templates/plan-template.md | 7 +++`.
- **Evidência no HEAD:** `skills/shared/plan-mode/SKILL.md:39` — "`Load \`.dev-team-agents/templates/plan-template.md\` and fill it in. That file is the canonical`". A skill não contém mais nenhuma renderização da tabela de STEPS (nenhuma linha `| Par.` nem caracteres de box-drawing); suas seções são `When a Plan Is Required`, `Plan Format`, `Approval Protocol`, `Execution Strategy Gate`, `Replanning During Execution`, `Agents Must Self-Enforce`, `Context Self-Monitoring`. A referência usa a forma de caminho instalado (`.dev-team-agents/templates/…`), que é o que `helpers/orphan-template-scan.sh` exige resolver.
- **Conclusão:** Uma única definição do formato, com a skill delegando ao template — o mesmo padrão de `skills/shared/runbook/SKILL.md` citado como contraste no relatório de origem.

### 23. `flow-orphan-template-scan-no-mapping-of-suggested-consumer-vs-orphan-skill-scan`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:174`)
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `c7535b7` — `helpers/orphan-template-scan.sh | 146 +++++++++++++++++----`.
- **Evidência no HEAD:** `helpers/orphan-template-scan.sh:42-43` — "`# Suggested consumer for an orphan template, mirroring orphan-skill-scan.sh.`" / "`suggest_consumer() {`"; a saída usa a função em `:103` — "`ORPHAN_MSGS+=("  · $rel_template\n    → Suggested consumer: $(suggest_consumer "$template_name")\n    → Add a reference using the installed path form: \`.dev-team-agents/templates/$template_name\`")`" e em `:106` para o caso de referência não-resolvível. O scanner também ganhou a distinção `shipped` vs `repo-only` consumer (`:36-37`) e a semântica "referência precisa **resolver**, não só ser mencionada" (`:5`, `:15-16`).
- **Conclusão:** A assimetria com `orphan-skill-scan.sh` foi fechada — o scan sugere um consumidor e a forma de caminho correta. Execução ao HEAD: "`orphan-template-scan: clean ✓`".

### 24. `agent-security-specialist-body-130-153-hardcodes-per-language-sast-and-dep-audit-commands-bandit-composer-npm-trivy-stack-prescriptive`
- **Marca original:** ✅ Executed 2026-07-31 (`_index.md:185`)
- **Marca verificada:** ✅ Feito
- **Commits da janela:** `b4e219f` — "refactor(agents): delegate shared context, extract stack-prescriptive bodies" — `agents/security-specialist.md | 136 +++++--------`; e `519ca7e`, que criou o destino da extração: `skills/security/dependency-audit/SKILL.md` (+91).
- **Evidência no HEAD:** `rg -i 'bandit|composer|npm audit|trivy|pip-audit|semgrep' agents/security-specialist.md` **não retorna nada** — nenhum comando por ecossistema sobrou no corpo. A delegação está em `agents/security-specialist.md:122` — "`Load \`skills/security/dependency-audit/SKILL.md\` and follow its order: always-run tier (secret history scan + broad SAST) → ecosystem lockfile signal → matching dependency scanner → language-specific SAST. Run only what the repository's signals justify… The skill owns the reporting thresholds, the missing-tool policy (\`NOT RUN\` is never a pass), and the output discipline for scanner results.`" A tabela de roteamento do agente também aponta para a skill (`:50`) e para `skills/security/sast-pipeline/SKILL.md` (`:48`).
- **Conclusão:** O corpo do agente voltou a ser stack-agnóstico; a prescrição por linguagem vive na skill, carregada condicionalmente conforme os sinais do repositório.

---

## Observações fora do escopo desta fase (candidatas à Fase 2)

Levantadas incidentalmente durante a verificação, todas com evidência ao HEAD `a67cac9`:

1. **`helpers/size-limits.sh` reprova a árvore atual e derruba o gate bloqueante do CI.** `bash helpers/size-limits.sh` → exit 1 com "`⚠ CLAUDE.md: 602 lines (warning threshold: 600)`". O caminho de aviso empilha no mesmo array de violações (`helpers/size-limits.sh:91-92`) e o script termina em `exit 1` (`:122`), sem distinguir aviso de erro. Como `.github/scripts/ci/01-lint.sh:87` o invoca via `blocking`, o job `lint` está vermelho.
2. **`AGENT_LIMIT` divergiu da documentação.** `helpers/size-limits.sh:44` — "`AGENT_LIMIT=211`" com o comentário "`200 lines of agent CONTENT, plus 11 lines of fixed-size model-identity boilerplate`". `CLAUDE.md` afirma duas vezes que o limite é **205** ("`helpers/size-limits.sh enforces 205 — the extra 5 lines are the fixed-size run-banner block`" e "`agents 205 (200 content + 5 run-banner)`" na árvore de arquivos).
3. **`SKILL_DESC_STRICT` divergiu da documentação.** `.github/scripts/ci/01-lint.sh:64-66` afirma "`every violator has been trimmed (\`SKILL_DESC_STRICT=true\` in helpers/agent-lint.sh)`", mas o lint ao HEAD ainda emite as descrições longas como WARNING não-bloqueante (`helpers/agent-lint.sh:516`), coerente com `CLAUDE.md` ("`SKILL_DESC_STRICT=false`"). As duas afirmações não podem ser ambas verdadeiras.
4. **`CLAUDE.md` referencia hooks desativados.** A tabela de comandos aponta `/devteam:update` para "`hooks/pre-tool-use/01-check-updates.sh`", mas o arquivo é `_disabled-01-check-updates.sh` desde `3c46d04` (2026-08-06); a lógica migrou para `scripts/hooks/session-start.sh`. Mesma classe de drift para `stop/04-notifier.sh` e `stop/99-graphify-refresh.sh`, ambos hoje `_disabled-`.
5. **`commands/fix.md` não tem passo de handoff**, ao contrário dos outros seis comandos de implementação (ver item 21).

---

## Fase 1 — Bloco B (24 itens)

Escopo: 24 linhas de `docs/reports/_index.md` (L186–L251), todas marcadas `✅ **Executed:** 2026-07-31`.
HEAD verificado: `a67cac9`. Commits de remediação da janela (2026-07-31): `b4e219f`, `519ca7e`, `6919564`, `7736e20`.

| # | Fingerprint | Marca original | Marca verificada | Commit examinado |
|---|---|---|---|---|
| 1 (L186) | `agent-backend-developer-integration-awareness-section-duplicates-provider-specific-critical-rules-inline-for-7-integrations-…` | ✅ Executed 2026-07-31 | ✅ Feito | `b4e219f` |
| 2 (L187) | `agent-frontend-test-specialist-107-122-hardcodes-react-renderhook-testing-library-and-vue-withsetup-recipes-in-body-stack-agnostic` | ✅ Executed 2026-07-31 | ✅ Feito | `b4e219f` + `519ca7e` |
| 3 (L188) | `agent-devops-specialist-decision-framework-and-anti-overengineering-still-stack-prescriptive-in-body-…` | ✅ Executed 2026-07-31 | ✅ Feito | `b4e219f` + `519ca7e` |
| 4 (L189) | `agent-code-reviewer-router-has-ten-structural-review-categories-contradicting-claude-md-183-…` | ✅ Executed 2026-07-31 | ✅ Feito | `b4e219f` |
| 5 (L190) | `agent-backend-test-specialist-body-114-120-hardcodes-per-language-coverage-command-matrix-…` | ✅ Executed 2026-07-31 | ✅ Feito | `b4e219f` + `519ca7e` |
| 6 (L191) | `skill-architecture-awareness-shared-behavioral-skill-enumerates-react-vue-svelte-angular-…` | ✅ Executed 2026-07-31 | ✅ Feito | `519ca7e` |
| 7 (L192) | `agent-setup-assistant-lines-60-70-docker-compose-version-detection-inline-bash-block-…` | ✅ Executed 2026-07-31 | ✅ Feito | `b4e219f` + `519ca7e` |
| 8 (L196) | `agent-database-specialist-description-frontmatter-enumerates-12-engines-…` | ✅ Executed 2026-07-31 | ✅ Feito | `b4e219f` |
| 9 (L197) | `skill-mobile-ios-and-android-wrapper-pattern-first-instruction-is-load-ios-hig-or-material-design-…` | ✅ Executed 2026-07-31 | ✅ Feito | `519ca7e` + `b4e219f` |
| 10 (L200) | `agent-backend-developer-description-enumerates-rest-graphql-mvc-server-rendered-paradigms-…` | ✅ Executed 2026-07-31 | ✅ Feito | `b4e219f` |
| 11 (L202) | `agent-setup-assistant-immutability-section-225-238-redundant-with-warning-line-24-duplicate-md-headers` | ✅ Executed 2026-07-31 | ✅ Feito | `b4e219f` |
| 12 (L203) | `agent-code-reviewer-15-item-foundational-rule-longest-in-repo-5-conditional-loads-eager-listed` | ✅ Executed 2026-07-31 | ✅ Feito | `b4e219f` |
| 13 (L205) | `agent-software-architect-foundational-rule-51-lines-2x-avg` | ✅ Executed 2026-07-31 | 🔴 Não feito | `b4e219f` |
| 14 (L211) | `skill-discovery-mode-no-stale-lock-cleanup-script-30min-rule-only-documented` | ✅ Executed 2026-07-31 | ✅ Feito | `519ca7e` |
| 15 (L214) | `skill-sonarqube-435-lines-overlap-with-reviewer-base-detection-block` | ✅ Executed 2026-07-31 | ✅ Feito | `519ca7e` |
| 16 (L220) | `skill-add-load-testing` | ✅ Executed 2026-07-31 | ✅ Feito | `519ca7e` |
| 17 (L224) | `token-claude-md-426-lines-still-monolithic-three-extractable-blocks-…` | ✅ Executed (já reaberto 2×) | 🔴 Não feito | nenhum na janela |
| 18 (L225) | `token-foundational-rule-424-lines-across-17-agents` | ✅ Executed 2026-07-31 | ✅ Feito | `b4e219f` |
| 19 (L227) | `token-project-context-docker-development-environment-section-22-lines-inlined-eager-loaded-…` | ✅ Executed 2026-07-31 | ✅ Feito | `b4e219f` |
| 20 (L228) | `token-qa-specialist-eager-loads-security-checklist-123-lines-every-spawn-…` | ✅ Executed 2026-07-31 | ✅ Feito | `b4e219f` |
| 21 (L234) | `token-frontend-code-quality-description-288-chars-cauda-…` | ✅ Executed 2026-07-31 | ✅ Feito | `7736e20` |
| 22 (L237) | `token-notifier-loads-45-tips-3-languages-emits-1-per-day-99pct-waste` | ✅ Executed 2026-07-31 | ✅ Feito | `6919564` |
| 23 (L242) | `token-worktree-isolation-block-7-lines-x-8-agents` | ✅ Executed 2026-07-31 | ✅ Feito | `b4e219f` |
| 24 (L251) | `token-commands-commit-md-145-lines-and-refactor-md-156-lines-largest-command-files` | ✅ Executed 2026-07-31 | 🟡 Parcialmente feito | `6919564` |

**Placar: 21 ✅ / 1 🟡 / 2 🔴**

---

## Item a item

### 1. `agent-backend-developer-integration-awareness-section-duplicates-provider-specific-critical-rules-inline-for-7-integrations-systemic-stack-prescriptive-body` (L186)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `b4e219f` — "refactor(agents): delegate shared context, extract stack-prescriptive bodies" — tocou `agents/backend-developer.md` (190 linhas alteradas). O diff remove as subseções por integração: `-### Supabase (Cloud or Self-Hosted)`, `-Critical rules when Supabase is detected:`, `-- **RLS is the authorization layer** …`, `-### GoTrue (Auth)`, `-### JWT`.
- **Evidência no HEAD:** `agents/backend-developer.md:73` — "Detect the platform from project signals, then load the matching skill **before** writing code. The skill is the source of truth for its rules — never act on these platforms from memory."; `:75-84` é uma tabela `| Detection signal | Skill to load |` com 8 linhas e zero regra inline.
- **Conclusão:** A seção virou roteamento puro sinal→skill. Nenhuma regra de provider sobreviveu no corpo do agente. Não houve reversão (`git log --since=2026-07-31 -- agents/backend-developer.md` mostra 8 commits, todos aditivos de skills).

### 2. `agent-frontend-test-specialist-107-122-hardcodes-react-renderhook-testing-library-and-vue-withsetup-recipes-in-body-stack-agnostic` (L187)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `b4e219f` — `agents/frontend-test-specialist.md | 120 ++---` (17 inserções, 103 remoções); `519ca7e` criou o destino `skills/testing/frontend-hook-tests/SKILL.md` (109 linhas novas).
- **Evidência no HEAD:** `agents/frontend-test-specialist.md:103` — "When business logic lives in a custom hook or composable, load `skills/testing/frontend-hook-tests/SKILL.md` and read only the framework row its Detection table resolves to. It covers when a hook test is worth writing, the React and Vue recipes, async handling, and the anti-patterns." Busca por `renderHook|withSetup|testing-library` no corpo do agente retorna zero ocorrências fora dessa linha de delegação.
- **Conclusão:** Receitas extraídas para skill com gate de detecção por framework; o corpo do agente ficou stack-agnóstico.

### 3. `agent-devops-specialist-decision-framework-and-anti-overengineering-still-stack-prescriptive-in-body-after-2026-05-18-fix-on-description-and-identity` (L188)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `b4e219f` removeu `## Decision Framework — Infrastructure Sizing` (tabela `< 1k req/day → Single EC2/VPS + Docker Compose` etc.) e `## Anti-Overengineering Rules` inteiro (`- Don't use Kubernetes when Docker Compose works`, `- Don't set up a full observability platform (Datadog, Grafana Cloud) …`); `519ca7e` criou `skills/devops/infrastructure-sizing/SKILL.md` (87 linhas).
- **Evidência no HEAD:** `agents/devops-specialist.md:129` — "Load `skills/devops/infrastructure-sizing/SKILL.md` whenever you choose a hosting or runtime shape … It defines the capability tiers, the trigger that must fire before moving up a tier, and the anti-overengineering rules."; `:131` — "Never name a specific product as the answer — pick the tier, then the platform the project already runs and the team can operate."
- **Conclusão:** Ambas as seções nomeadas no fingerprint saíram do corpo. (Observação para a Fase 2, fora do escopo desta marca: o checklist `## What to Do Before Declaring Done` em `:135-149` ainda cita Docker e Terraform nominalmente.)

### 4. `agent-code-reviewer-router-has-ten-structural-review-categories-contradicting-claude-md-183-router-does-not-duplicate-specialist-checks` (L189)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `b4e219f` — o diff remove `-## Review Categories` e as dez subseções numeradas (`-### 1. Correctness` … `-### 10. Type Safety`) e insere `+## Router Responsibilities` com três subseções.
- **Evidência no HEAD:** `agents/code-reviewer.md:71` — "## Router Responsibilities", seguido de `:75` "### Run the linters before commenting on style", `:84` "### Sweep for cross-cutting silent bugs", `:93` "### Synthesize". Nenhuma seção `## Review Categories` existe no arquivo.
- **Conclusão:** O router deixou de duplicar as checagens estruturais dos especialistas, alinhando-se ao papel documentado em `CLAUDE.md`.

### 5. `agent-backend-test-specialist-body-114-120-hardcodes-per-language-coverage-command-matrix-clover-pytest-jacoco-go-simplecov-stack-prescriptive` (L190)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `b4e219f` remove as linhas da matriz (`-   | PHP | \`--coverage-clover coverage/clover.xml\` | Clover XML |`, `-   | Java | JaCoCo plugin | \`target/site/jacoco/jacoco.xml\` |`); `519ca7e` moveu a matriz para `skills/devops/sonarqube/references/quality-gates.md`.
- **Evidência no HEAD:** `agents/backend-test-specialist.md:108` — "**Generate coverage in the format SonarQube expects** — read `references/quality-gates.md` in that skill for the per-language test-runner command, output artifact, and `sonar.*coverage.reportPaths` key". Busca por `clover|jacoco|simplecov` no agente: zero ocorrências.
- **Conclusão:** Matriz de cinco linguagens removida do corpo e movida para `references/`, carregada sob demanda.

### 6. `skill-architecture-awareness-shared-behavioral-skill-enumerates-react-vue-svelte-angular-blade-twig-erb-jinja-laravel-django-rails-eager-loaded-by-three-coding-agents` (L191)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `519ca7e` — reescreveu `skills/shared/architecture-awareness/SKILL.md`, removendo `-**Decoupled SPA**: React, Vue, Svelte, Angular consuming an API…` e `-**Server-rendered templates**: Blade, Twig, ERB, Jinja, Handlebars…`, e adicionando tabelas sinal-estrutural→modelo.
- **Evidência no HEAD:** `skills/shared/architecture-awareness/SKILL.md:11` — "**Read only the section that matches your context.** Loading this skill does not mean reading all of it."; `:106` — "| A build step emits a JS bundle; server returns a shell HTML document; routes resolve client-side | **Decoupled client** | …". Busca case-insensitive por `react|vue|svelte|angular|blade|twig|erb|jinja|laravel|django|rails` no arquivo: **zero ocorrências**. Arquivo com 87 linhas.
- **Conclusão:** Skill comportamental agora descreve modelos por sinal estrutural, com gate de roteamento por consumidor. Nenhum framework nomeado sobrou.

### 7. `agent-setup-assistant-lines-60-70-docker-compose-version-detection-inline-bash-block-stack-prescriptive-in-agent-body-while-mobile-detection-and-stack-detection-already-extracted-to-skills` (L192)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `b4e219f` removeu o bloco bash inline (`-if docker compose version >/dev/null 2>&1; then` / `-    DOCKER_COMPOSE="docker compose"` …); `519ca7e` inseriu a sonda em `skills/shared/stack-detection/SKILL.md` sob `+## Tooling Detection` → `+### Docker Compose command form`.
- **Evidência no HEAD:** `agents/setup-assistant.md:66` — "**Docker Compose command form:** only when the scan finds a compose file, apply the Docker Compose probe from the already-loaded `stack-detection` skill and record its result in the project's `CLAUDE.md` as `DOCKER_COMPOSE: <form>` so no agent re-probes."
- **Conclusão:** Bloco extraído para a skill cujo consumidor é todo agente, não só o setup. O único bloco bash restante no agente (`:49`) é a detecção FIRST_RUN/REFRESH, fora do escopo do fingerprint.

### 8. `agent-database-specialist-description-frontmatter-enumerates-12-engines-and-three-cloud-managed-db-families-stack-prescriptive-identity-surface` (L196)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `b4e219f` — diff da frontmatter: remove "Covers MySQL, PostgreSQL, SQL Server, MongoDB, Redis, Cassandra, SQLite and managed cloud services (AWS RDS/Aurora/DynamoDB, GCP Cloud SQL/Firestore/Spanner, Azure SQL/Cosmos DB)".
- **Evidência no HEAD:** `agents/database-specialist.md:3` — "description: Expert in database design, query optimization, indexing strategy, and schema decisions across relational, document, key-value, and column-family engines, whether self-hosted or managed in the cloud. …"
- **Conclusão:** A lista fechada de engines saiu da superfície de identidade; ficaram as famílias de modelo de dados.

### 9. `skill-mobile-ios-and-android-wrapper-pattern-first-instruction-is-load-ios-hig-or-material-design-…` (L197)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `519ca7e` (wrappers) + `b4e219f` (gate no agente). O diff de `skills/mobile/ios/SKILL.md` remove `-- Load \`skills/mobile/ios-hig/SKILL.md\` for the full reference…` e adiciona `+## Scope`. `b4e219f` substituiu a linha de tabela `-| **Cross-platform (both platforms)** | React Native, Flutter, or Expo … | Load **both** platform skill pairs above |` por um gate explícito.
- **Evidência no HEAD:** `skills/mobile/ios/SKILL.md:10` — "The **design** half lives in `skills/mobile/ios-hig/SKILL.md` … Load it **only when the task touches UI** … A signing, build, or non-UI logic task does not need it."; `agents/mobile-developer.md:72` — "**Gate 2 — does the task touch UI?** Add the design skill **only** when the task involves screen layout, navigation, or visual/interaction design … A signing, build, dependency, or non-UI logic task loads neither."; `:74` — "**Cross-platform projects** … run both gates **per platform actually targeted**". Tamanhos: ios 38 linhas, android 40 (eram 33 e 35 de wrapper *empilhado sobre* 218/221).
- **Conclusão:** Os dois defeitos compostos foram resolvidos: o wrapper deixou de duplicar a carga que o agente já fazia, e o gate deixou de ser prosa numa célula de tabela.

### 10. `agent-backend-developer-description-enumerates-rest-graphql-mvc-server-rendered-paradigms-on-identity-surface-last-coding-agent-desc-while-body-claims-stack-agnostic` (L200)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `b4e219f` — remove "Works in both decoupled (REST API, GraphQL) and monolithic (MVC, server-rendered templates) architectures."
- **Evidência no HEAD:** `agents/backend-developer.md:3` — "…Adapts to whatever server-side style the project uses — API-first or server-rendered, layered or flat. …"
- **Conclusão:** A enumeração de paradigmas saiu da description; a alegação de stack-neutralidade quatro linhas abaixo (`:8` "You are not attached to any specific stack") deixou de ser contraditória.

### 11. `agent-setup-assistant-immutability-section-225-238-redundant-with-warning-line-24-duplicate-md-headers` (L202)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `b4e219f` — a mensagem do commit registra "setup-assistant's duplicate Immutability Warning headings are merged"; o diff remove o primeiro `-## Immutability Warning` e preserva o segundo.
- **Evidência no HEAD:** `rg 'Immutability' agents/setup-assistant.md` retorna uma única linha: `189:## Immutability Warning`.
- **Conclusão:** Cabeçalho duplicado eliminado; resta uma ocorrência.

### 12. `agent-code-reviewer-15-item-foundational-rule-longest-in-repo-5-conditional-loads-eager-listed` (L203)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `b4e219f` — mensagem: "Its 15-item Foundational Rule, which mixed five conditional loads into the mandatory list, is now split."
- **Evidência no HEAD:** `agents/code-reviewer.md:43` — "Load `skills/shared/project-context/SKILL.md` — covers README, CLAUDE.md, AGENTS.md, project.md, session-summary, development docs, and recent git log."; `:57` — "**Conditional loads** — load at the point of use, never at startup:", seguido de tabela `| Trigger | Skill |` com 7 linhas.
- **Conclusão:** Lista obrigatória e cargas condicionais estão separadas, com a condicional explicitamente marcada como *point of use*.

### 13. `agent-software-architect-foundational-rule-51-lines-2x-avg` (L205)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** 🔴 **Não feito**
- **Commit da janela:** `b4e219f` — tocou `agents/software-architect.md` (261 linhas alteradas), mas **não reduziu a Foundational Rule**. O diff da seção remove uma linha (o parágrafo do cascade de worktree, que é a remediação do fingerprint `token-worktree-isolation-block-7-lines-x-8-agents`) e **adiciona quatro linhas de tabela condicional**: `+| Writing or reviewing any architecture document | skills/architecture/architecture-docs/SKILL.md |`, `+| Delegating implementation to subagents | skills/architecture/orchestration/SKILL.md |`, `+| Reviewing or emitting code samples in any document | skills/shared/comments-policy/SKILL.md |`, `+| LLM or AI feature in the stack | skills/architecture/llm-integration/SKILL.md |`.
- **Evidência no HEAD:** `agents/software-architect.md:19` — "## Foundational Rule" — a seção vai até `:61` (antes de `:62 ## Execution Strategy Gate (Mandatory)`), ou seja **43 linhas**. Medição comparativa das seções `## Foundational Rule` de todos os 18 agentes no HEAD: `software-architect 43`, `security-specialist 38`, `code-reviewer 30`, `technical-writer 23`, `ui-ux-designer 18`, `setup-assistant 18` — continua sendo **a maior do repositório**.
- **Trajetória medida:** 37 linhas em `b4e219f~1` (estado do achado) → **41** em `b4e219f` (o próprio commit de remediação) → **43** no HEAD.
- **Conclusão:** A marca `✅ Executed` está errada. O commit da janela tocou o arquivo, mas o bloco alvo **cresceu** em vez de encolher — dentro do próprio commit dito remediador (+4 linhas) e mais +2 desde então. O achado ("maior Foundational Rule do repo, ~2× a mediana") permanece integralmente válido e agravado no HEAD.

### 14. `skill-discovery-mode-no-stale-lock-cleanup-script-30min-rule-only-documented` (L211)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `519ca7e` — mensagem: "The acquire block returned before the staleness check could ever run … the check used GNU-only `date -d` with `|| echo 0`, which on macOS made every lock look stale … Both fixed with `find -mmin`, verified across GNU, BSD and dash."
- **Evidência no HEAD:** `skills/shared/discovery-mode/SKILL.md:114` — "Run the block below **verbatim and in this order**. The staleness sweep must come *before* the bail-out, otherwise a lock left behind by a crashed agent blocks discovery forever."; `:122` — `if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +30 2>/dev/null)" ]; then`; `:140` — "Never compute the age with `date -d \"$(awk ...)\"`: `date -d` is GNU-only, so on macOS it fails, and a `|| echo 0` fallback makes every lock look infinitely old and deletes locks that are still live."
- **Conclusão:** Ambos os bugs (ordenação e portabilidade macOS) corrigidos, com o racional gravado como regra para impedir regressão.

### 15. `skill-sonarqube-435-lines-overlap-with-reviewer-base-detection-block` (L214)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `519ca7e` — diff em `skills/shared/reviewer-base/SKILL.md` substitui `-   - Detect SonarQube: if \`sonar-project.properties\`, \`.sonarcloud.properties\`, or \`SONAR_TOKEN\` is present → load …`.
- **Evidência no HEAD:** `skills/shared/reviewer-base/SKILL.md:16` — "Detect SonarQube using the `## Detection Signals` table in `skills/devops/sonarqube/SKILL.md` — if **any** signal in that table matches, load the skill. That table is the single source of truth; do not maintain or infer a signal list here…"
- **Conclusão:** O subconjunto restatement virou delegação à tabela canônica, alinhado à regra "Canonical Rule Homes" do `CLAUDE.md`.

### 16. `skill-add-load-testing` (L220)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `519ca7e` — `skills/testing/load-testing/SKILL.md | 151 ++++++`.
- **Evidência no HEAD:** `skills/testing/load-testing/SKILL.md:2-3` — "name: load-testing" / "description: Load testing — smoke/load/stress/soak/spike profiles, SLO thresholds, tooling." (151 linhas). Referenciada por agente: `agents/backend-test-specialist.md:79` — "`skills/testing/load-testing/SKILL.md` — when the task concerns throughput, latency or capacity … Distinct from `skills/architecture/performance-budgets/SKILL.md`, which covers client-side budgets".
- **Conclusão:** Skill criada, dentro do limite de 500 linhas, com fronteira explícita contra `performance-budgets` e com referência de carga em agente (não é órfã).

### 17. `token-claude-md-426-lines-still-monolithic-three-extractable-blocks-commands-table-40-stop-sub-script-convention-24-hook-files-map-8-total-72-lines-while-claude-md-folder-already-exists-…` (L224)
- **Marca original:** ✅ Executed 2026-07-31 (já reaberta 🔴 em 2026-07-31 e 2026-08-14)
- **Marca verificada:** 🔴 **Não feito** — terceira confirmação
- **Commit da janela:** **nenhum**. `git log --since=2026-07-31 --until=2026-08-01T23:59 -- CLAUDE.md` retorna apenas commits de **2026-08-01** (`9c1b93a`, `871b200`, `3421afb`, `16fd34b`), todos aditivos de conteúdo, nenhum de extração. `git log --since=2026-07-31 -- CLAUDE-md/` não contém nenhum commit de 2026-07-31; a única extração real, `CLAUDE-md/hooks.md`, veio de `2b436ea` em **2026-08-03**, fora da janela.
- **Evidência no HEAD:** `wc -l CLAUDE.md` → **602 linhas** (575 já em `483cba5`, no fim do próprio dia da marca; o relatório de abertura media 425). A tabela de comandos segue inline: `CLAUDE.md:206` — "#### User-Invocable Commands (`commands/*.md`)" com cabeçalho de tabela em `:212` — "| Command | Agents invoked | Use when… |". O bloco `## Agent Memory System` segue inline em `:418`. `CLAUDE-md/` contém apenas `hooks.md`, `notifications.md`, `preferences.md`, `user-data.md`, `versioning.md`.
- **Conclusão:** A marcação `✅ Executed` é falsa por construção — nenhum commit da janela tocou os blocos alvo. O arquivo cresceu 41% desde a abertura do achado (425 → 602) e nenhum dos três blocos extraíveis nomeados no fingerprint foi movido. Deve ser reclassificada como 🔴 pela terceira vez.

### 18. `token-foundational-rule-424-lines-across-17-agents` (L225)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `b4e219f` — mensagem: "Foundational Rule delegated. 15 agents inlined the same 12-item context list, 384 duplicated lines fleet-wide … All 17 now use that shape and keep only genuinely role-specific additions."
- **Evidência no HEAD:** `grep -L 'Load \`skills/shared/project-context/SKILL.md\`' agents/*.md` retorna **vazio** — os 18 agentes atuais (17 da época + `seo-specialist`, adicionado depois) delegam. Exemplo: `agents/backend-developer.md` e `agents/code-reviewer.md:43` carregam a linha única de delegação; a lista de 12 itens não aparece em nenhum corpo.
- **Conclusão:** Duplicação eliminada em toda a frota, incluindo o agente criado após a remediação — sinal de que o padrão foi adotado, não só aplicado uma vez.

### 19. `token-project-context-docker-development-environment-section-22-lines-inlined-eager-loaded-by-14-agents-while-sonarqube-same-file-is-detection-gated` (L227)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `b4e219f` — remove `-## Docker Development Environment` e as 22 linhas inline (tabela `| Run a script or CLI command | docker compose exec <service> <command> |`, exceção de host etc.), inserindo `+## Development Environment` com tabela de detecção; criou `skills/devops/docker-dev/SKILL.md` (171 linhas no HEAD).
- **Evidência no HEAD:** `skills/shared/project-context/SKILL.md:238` — "| `docker-compose.yml`, `docker-compose.override.yml`, or `compose.yml` at the root | `skills/devops/docker-dev/SKILL.md` |"; a linha seguinte declara "When loaded, that skill governs the command execution contract".
- **Conclusão:** A seção Docker passou a ser gated por detecção, com a mesma forma da rota SonarQube no mesmo arquivo. O conteúdo eager saiu do caminho carregado por todos os agentes.

### 20. `token-qa-specialist-eager-loads-security-checklist-123-lines-every-spawn-though-behavioral-qa-often-no-security-scope-sonarqube-gated-in-same-file` (L228)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `b4e219f` — remove `-Load \`security-checklist\` skill to validate security behavior as part of QA — auth flows, input validation, access control…` e insere uma tabela `+| Trigger | Skill |`.
- **Evidência no HEAD:** `agents/qa-specialist.md:45` — "| The changeset touches auth, access control, input validation, or API behavior | `skills/security/security-checklist/SKILL.md` |". Única ocorrência de `security-checklist` no arquivo, e ela está dentro da tabela condicional.
- **Conclusão:** A carga passou de eager a condicional por gatilho, coerente com o SonarQube gated logo abaixo. `git log` posterior mostra 5 commits no agente, nenhum reintroduzindo a carga eager.

### 21. `token-frontend-code-quality-description-288-chars-cauda-loaded-by-frontend-developer-as-authoritative-redundant-trim-target-70-chars-pior-offender-confirmado-na-relista-de-2026-05-26` (L234)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `7736e20` (2026-07-31) — "docs: sync documentation with six waves of changes, enforce both size gates". `git log -L` sobre a linha `description:` confirma que esse é o único commit desde `2cdfa9d` (2026-05-15) a alterá-la.
- **Evidência no HEAD:** `skills/architecture/frontend-code-quality/SKILL.md:3` — "description: Base frontend code quality rules — component size, state, a11y, performance, type safety." — **89 caracteres**, dentro do orçamento de 95 do `CLAUDE.md`. A cauda meta-narrativa "Loaded by frontend-developer as the authoritative quality baseline." foi removida.
- **Conclusão:** 288 → 89 caracteres, cauda eliminada. Note que o commit da janela é `7736e20`, não os três principais — a marca está correta mesmo assim.

### 22. `token-notifier-loads-45-tips-3-languages-emits-1-per-day-99pct-waste` (L237)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `6919564` — `scripts/hooks/stop/04-notifier.sh | 76 ++++-------` mais três arquivos novos `scripts/hooks/stop/tips/tips.{en,es,pt-BR}.txt` de 15 linhas cada. O diff remove os arrays inline `-    TIPS_EN=(` / `-    TIPS_PTBR=(` com as 45 strings.
- **Evidência no HEAD:** `scripts/hooks/stop/tips/` contém `tips.en.txt`, `tips.es.txt`, `tips.pt-BR.txt`, 15 linhas cada (45 no total, em dados). `scripts/hooks/stop/_disabled-04-notifier.sh:36` — `TIPS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)/tips"`; `:293-295` selecionam **um** arquivo por locale (`pt-BR|pt) TIP_FILE="$TIPS_DIR/tips.pt-BR.txt" ;;`).
- **Conclusão:** Extração confirmada e sobrevivente: apenas o arquivo do locale ativo é lido, e só quando o gate diário abre. O script foi renomeado para `_disabled-04-notifier.sh` depois (desativado como hook), o que não reverte a remediação.

### 23. `token-worktree-isolation-block-7-lines-x-8-agents` (L242)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** ✅ Feito
- **Commit da janela:** `b4e219f` — remove o cascade inline de 3 passos (`-1. \`.dev-team-agents/.worktree-session\` present:` … `-3. Key absent (legacy install) → use the \`AskUserQuestion\` tool…`) dos agentes de código.
- **Evidência no HEAD:** `agents/backend-developer.md` § `## Worktree Isolation` — "Before editing any file, resolve the worktree decision using the cascade in `CLAUDE.md` → Worktree Isolation: `.dev-team-agents/.worktree-session` → `worktree_active` in `.dev-team-agents/user-data/preferences.json` → ask once via `AskUserQuestion`." Medição da seção nos 8 agentes de código: backend-developer 8, frontend-developer 6, mobile-developer 6, database-specialist 8, devops-specialist 6, ui-ux-designer 6, backend-test-specialist 8, frontend-test-specialist 6 — todas delegam, nenhuma restata o cascade.
- **Conclusão:** O cascade tem uma única cópia (em `CLAUDE.md` + `skills/shared/worktree/SKILL.md`), exatamente como a regra "Delegate, Never Restate" exige. As 2 linhas de variação entre agentes são a linha em branco / separador, não divergência de conteúdo.

### 24. `token-commands-commit-md-145-lines-and-refactor-md-156-lines-largest-command-files` (L251)
- **Marca original:** ✅ Executed 2026-07-31
- **Marca verificada:** 🟡 **Parcialmente feito**
- **Commit da janela:** `6919564` — tocou ambos os alvos (`commands/commit.md | 20 ++----`, `commands/refactor.md | 41 +++++------`) removendo duplicação cross-cutting (a tabela de commit por camada foi delegada a `skills/shared/conventional-commits/SKILL.md`, e `commands/learn.md` caiu 95 linhas). `7736e20` adicionou o teto de 200 linhas para comandos em `helpers/size-limits.sh` (`# commands/ — max ~200 lines each`).
- **Evidência no HEAD:** `wc -l commands/commit.md commands/refactor.md` → **193** e **172**. Mediana atual de `commands/*.md` (n=35): **71**. Ou seja, `commit.md` está a 2,7× a mediana e `refactor.md` a 2,4×.
- **Trajetória medida:** `commit.md` 177 (`6919564~1`, estado do achado) → 165 (`6919564`) → **193** (HEAD). `refactor.md` 159 → **164 no próprio commit dito remediador** (cresceu +5) → **172** (HEAD).
- **O que falta exatamente:** a redução ao patamar da mediana nunca aconteceu. `commit.md` está **+16 linhas acima** do tamanho registrado no achado e `refactor.md` **+13**. O que de fato foi entregue e sobreviveu é (a) a remoção da duplicação da tabela de camadas e (b) o gate de 200 linhas que impede o crescimento indefinido — `3a1cce6 fix(commands): trim commit.md under the 200-line command size limit` e `b1340f2 fix(ci): satisfy size limit and shellcheck gates` mostram o gate funcionando como cinto de segurança, não como redução.
- **Conclusão:** Marca 🟡 e não ✅. A classe "oversize" foi **limitada** por um gate de CI, mas os dois arquivos nomeados no fingerprint continuam sendo os maiores da árvore junto com `learn.md` (200) e `audit.md` (197), e ambos estão maiores hoje do que quando o achado foi aberto.

---

## Fase 1b — Validade dos achados abertos

**Baseline anterior:** `c03f898` · **HEAD verificado:** `a67cac9` · 33 commits na janela.

**Taxa de mortalidade do pass:** 1 de 42 (2,4%) — 1 🟢 resolvido · 0 ⚰️ obsoletos · 41 ainda reproduzem

Todos os 42 alvos foram confirmados existentes no HEAD. Seis achados tiveram o alvo tocado na janela
sem que o defeito fosse corrigido (`02c-full-suite-guard.sh`, `.gitignore`, `commands/audit.md`,
`agents/software-architect.md`, `skills/architecture/orchestration/SKILL.md`, `CHANGELOG.md`) — em
dois casos o commit da janela **agravou** a situação (ver notas de #7, #26 e #40).

| # | Fingerprint | Alvo | Estado |
|---|---|---|---|
| 1 | `agent-frontend-test-specialist-sonarqube-coverage-block-hardcodes-jest-vitest-commands…` | `agents/frontend-test-specialist.md` | Ainda reproduz |
| 2 | `agent-frontend-developer-description-frontmatter-enumerates-eight-frameworks…` | `agents/frontend-developer.md` | Ainda reproduz |
| 3 | `agent-devops-specialist-core-expertise-declares-primary-docker…` | `agents/devops-specialist.md` | Ainda reproduz |
| 4 | `flow-audit-command-devops-analysis-prompt-names-redis-cdn-docker-inside-spawn-instruction` | `commands/audit.md` | Ainda reproduz |
| 5 | `docs-sync-claude-md-102-states-skill-desc-strict-false…` | `CLAUDE.md` | Ainda reproduz |
| 6 | `docs-sync-claude-md-173-says-all-devteam-commands-load-current-context…` | `CLAUDE.md` | Ainda reproduz |
| 7 | `docs-sync-reports-index-md-99-legend-comment-claims-all-131-entries-unmarked…` | `docs/reports/_index.md` | Ainda reproduz (agravado) |
| 8 | `flow-pre-tool-use-02b-telemetry-reads-devteam-hook-payload-branch…` | `scripts/hooks/pre-tool-use/02b-telemetry.sh` | Ainda reproduz |
| 9 | `skill-shared-migration-v1-to-v2-437-lines-largest-in-repo…` | `skills/shared/migration-v1-to-v2/SKILL.md` | Ainda reproduz |
| 10 | `token-interaction-patterns-209-lines-loaded-unconditionally…` | `skills/shared/interaction-patterns/SKILL.md` | Ainda reproduz |
| 11 | `flow-relayout-design-discovery-names-storybook-tailwind` | `commands/relayout.md` | Ainda reproduz |
| 12 | `auto-full-suite-guard-sed-absorbs-sibling-json-keys` | `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` | Ainda reproduz |
| 13 | `flow-learn-run-marker-records-commit-time-not-run-time` | `commands/learn.md` | Ainda reproduz (parcial) |
| 14 | `auto-install-heredoc-omits-auto-learn-before-commit` | `scripts/install.sh` | Ainda reproduz |
| 15 | `docs-sync-02c-comment-cites-graphify-hint-as-sed-precedent` | `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` | Ainda reproduz |
| 16 | `gov-repo-gitignore-omits-three-installer-written-entries` | `.gitignore` | Ainda reproduz (parcial) |
| 17 | `flow-audit-step2-unconditional-docker-stack-ignores-isolate-pref-compose-gate` | `commands/audit.md` | Ainda reproduz |
| 18 | `flow-mobile-command-spawn-line-enumerates-stacks-dropped-from-agent-description` | `commands/mobile.md` | Ainda reproduz |
| 19 | `agent-database-specialist-access-inlines-supabase-cli-while-delegating-others` | `agents/database-specialist.md` | Ainda reproduz |
| 20 | `ref-docs-agents-md-tier-column-stale-backend-test-specialist-listed-repetitive` | `docs/agents.md` | Ainda reproduz |
| 21 | `ref-tool-map-tool-rewrites-loaded-but-never-emitted-by-render-provider` | `scripts/lib/render_provider.py` | Ainda reproduz |
| 22 | `ref-02c-guard-make-composer-shapes-have-no-row-in-scoped-test-runner-table` | `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` | Ainda reproduz |
| 23 | `docs-sync-changelog-unreleased-omits-full-suite-guard-and-orchestration-deltas` | `CHANGELOG.md` | Ainda reproduz |
| 24 | `ref-scoped-test-execution-bash-parallelism-section-outside-declared-canonical-scope` | `skills/shared/scoped-test-execution/SKILL.md` | Ainda reproduz |
| 25 | `docs-sync-hooks-md-64-full-suite-guard-examples-predate-wrapper-detection` | `CLAUDE-md/hooks.md` | Ainda reproduz (agravado) |
| 26 | `flow-update-sh-codex-slim-guard-dead-branch-false-strip-claim` | `scripts/update.sh` | Ainda reproduz |
| 27 | `flow-02c-composer-fallback-case-ignores-every-scope-qualifier` | `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` | Ainda reproduz |
| 28 | `flow-update-sh-provider-reinstall-aborts-on-non-exit-3-failures` | `scripts/update.sh` | Ainda reproduz |
| 29 | `flow-architect-claude-only-async-tool-names-rendered-verbatim` | `agents/software-architect.md` | Ainda reproduz |
| 30 | `flow-02c-make-pattern-substring-matches-cmake-and-chained-cmds` | `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` | Ainda reproduz |
| 31 | `flow-prompt-auditoria-commit-step-contradicts-branch-rule` | `docs/reports/_prompt-auditoria.md` | Ainda reproduz |
| 32 | `flow-background-process-discipline-monitor-no-availability-fallback` | `skills/architecture/orchestration/SKILL.md` | Ainda reproduz |
| 33 | `skill-token-efficiency-background-mgmt-contradicts-orchestration-discipline` | `skills/shared/token-efficiency/strategies.md` | Ainda reproduz |
| 34 | `agent-line-cap-205-documented-in-claude-md-vs-211-enforced-by-size-limits` | `CLAUDE.md` | Ainda reproduz |
| 35 | `agent-software-architect-inlines-spawn-integrity-4-5-no-availability-guard` | `agents/software-architect.md` | Ainda reproduz |
| 36 | `skill-orchestration-spawn-integrity-unreachable-from-devteam-commands` | `commands/*.md` | Ainda reproduz |
| 37 | `skill-orchestration-restates-scoped-test-execution-exception` | `skills/architecture/orchestration/SKILL.md` | Ainda reproduz |
| 38 | `token-02c-full-suite-guard-substring-match-injects-nudge-on-non-test-commands` | `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` | Ainda reproduz |
| 39 | `token-pr-md-unbounded-full-diff-to-repetitive-tier…` | `commands/pr.md` | 🟢 **Resolved** |
| 40 | `token-orchestration-skill-377-lines-138-conditional-path-only-no-references-dir` | `skills/architecture/orchestration/SKILL.md` | Ainda reproduz (agravado) |
| 41 | `token-model-identity-32-of-58-lines-are-format-spec-and-examples-held-inline` | `skills/shared/model-identity/SKILL.md` | Ainda reproduz |
| 42 | `token-project-context-restates-scoped-test-exception-table-read-by-18-agents` | `skills/shared/project-context/SKILL.md` | Ainda reproduz |

---

## Item a item

### 1. `agent-frontend-test-specialist-sonarqube-coverage-block-hardcodes-jest-vitest-commands-and-sonar-javascript-key-while-backend-twin-was-delegated`
- **Alvo:** `agents/frontend-test-specialist.md` (`_index.md` L267)
- **Estado:** Ainda reproduz
- **Evidência:** `agents/frontend-test-specialist.md:145` — "`jest --coverage --coverageReporters=lcov`"; `:148` — "`vitest run --coverage --coverage.reporter=lcov`"; `:153` — "`sonar.javascript.lcov.reportPaths=coverage/lcov.info`". O gêmeo já delega: `agents/backend-test-specialist.md:108` — "read `references/quality-gates.md` in that skill for the per-language test-runner command".
- **Nota:** `9a64920` tocou o arquivo na janela (isolamento de teste unitário) sem encostar no bloco SonarQube.

### 2. `agent-frontend-developer-description-frontmatter-enumerates-eight-frameworks-react-vue-svelte-angular-blade-twig-erb-jinja-on-identity-surface`
- **Alvo:** `agents/frontend-developer.md`
- **Estado:** Ainda reproduz
- **Evidência:** `agents/frontend-developer.md:3` — "Works in both decoupled SPAs (React, Vue, Svelte, Angular) and server-rendered templates (Blade, Twig, ERB, Jinja)."
- **Nota:** Contraste com `agents/mobile-developer.md:3` — "Detects the project's mobile stack and follows its platform conventions", sem enumerar stack.

### 3. `agent-devops-specialist-core-expertise-declares-primary-docker-and-done-checklist-gates-on-docker-terraform-contradicting-own-never-name-a-product-rule`
- **Alvo:** `agents/devops-specialist.md`
- **Estado:** Ainda reproduz
- **Evidência:** `agents/devops-specialist.md:46` — "**Primary**: Docker — development environments and production containers"; contra `:131` — "Never name a specific product as the answer — pick the tier, then the platform the project already runs". Checklist ainda gateia em produto: `:137` — "Docker image builds cleanly"; `:147` — "IaC state stored remotely with locking (if Terraform is in use)".
- **Nota:** Distância entre a declaração e a regra: 85 linhas.

### 4. `flow-audit-command-devops-analysis-prompt-names-redis-cdn-docker-inside-spawn-instruction`
- **Alvo:** `commands/audit.md`
- **Estado:** Ainda reproduz
- **Evidência:** `commands/audit.md:126` — "Caching opportunities (Redis, CDN, HTTP caching)"; `:128` — "Docker/resource concerns specific to the module".
- **Nota:** `7e62124` tocou o arquivo na janela (nudge de `/devteam:learn`) sem alterar o bloco de spawn.

### 5. `docs-sync-claude-md-102-states-skill-desc-strict-false-non-blocking-while-agent-lint-31-sets-true-and-ci-promoted-it-same-day`
- **Alvo:** `CLAUDE.md`
- **Estado:** Ainda reproduz
- **Evidência:** `CLAUDE.md:129` — "`agent-lint.sh` reports over-budget descriptions as a non-blocking warning today (`SKILL_DESC_STRICT=false`)"; contra `helpers/agent-lint.sh:98` — "`SKILL_DESC_STRICT=true`" e `:317` — "`if [ "$SKILL_DESC_STRICT" = true ]; then`".
- **Nota:** HIGH mais antigo em aberto do banco; `CLAUDE.md` foi tocado na janela sem correção.

### 6. `docs-sync-claude-md-173-says-all-devteam-commands-load-current-context-while-213-lists-four-exceptions-as-the-complete-list`
- **Alvo:** `CLAUDE.md`
- **Estado:** Ainda reproduz
- **Evidência:** `CLAUDE.md:203` — "| `current-context` | All `/devteam:*` commands — detects branch/worktree state before executing |"; contra `:252` — "These six are the complete list — verify with `grep -L current-context commands/*.md`". O `grep` confirmado no HEAD retorna 6 arquivos (`commit`, `health-check`, `learn`, `rule`, `sync-rules`, `update`).
- **Nota:** As linhas migraram (173→203, 213→252) e a lista de exceções cresceu de quatro para seis; a contradição com "All" permanece literal.

### 7. `docs-sync-reports-index-md-99-legend-comment-claims-all-131-entries-unmarked-while-121-carry-executed-or-partial-marks`
- **Alvo:** `docs/reports/_index.md`
- **Estado:** Ainda reproduz (agravado)
- **Evidência:** `docs/reports/_index.md:103` — "All 131 entries below are unmarked: they were re-verified as reproducing at HEAD 7f85ed7." Contagem real no HEAD: 179 entradas `^- \`` e 14 linhas carregando marcador (`🟢`/`⚰️`/`Executado`/`Parcial`).
- **Nota:** O arquivo foi tocado na janela (novos achados de 2026-08-14) sem que o comentário de legenda fosse atualizado; a divergência de contagem cresceu de 131 para 179.

### 8. `flow-pre-tool-use-02b-telemetry-reads-devteam-hook-payload-branch-that-only-stop-dispatcher-ever-sets-dead-path-in-pretooluse`
- **Alvo:** `scripts/hooks/pre-tool-use/02b-telemetry.sh`
- **Estado:** Ainda reproduz
- **Evidência:** `scripts/hooks/pre-tool-use/02b-telemetry.sh:22` — "`if [ -f "${DEVTEAM_HOOK_PAYLOAD:-}" ]; then`". A única exportação da variável está em `scripts/hooks/stop.sh:17` — "`export DEVTEAM_HOOK_PAYLOAD="$HOOK_TMP"`"; `scripts/hooks/pre-tool-use.sh` não a define.
- **Nota:** O próprio comentário em `:19-20` admite a assimetria ("but PreToolUse dispatcher passes it via stdin directly") e mantém o ramo morto mesmo assim.

### 9. `skill-shared-migration-v1-to-v2-437-lines-largest-in-repo-single-conditional-loader-in-setup-assistant-no-references-extraction-and-no-retirement-criterion`
- **Alvo:** `skills/shared/migration-v1-to-v2/SKILL.md`
- **Estado:** Ainda reproduz
- **Evidência:** `wc -l` = **438** linhas (cresceu 1 desde a baseline); `ls skills/shared/migration-v1-to-v2/` retorna apenas `SKILL.md` — nenhum `references/`. Único carregador fora do próprio arquivo: `agents/setup-assistant.md`.
- **Nota:** Segue sem critério de aposentadoria declarado.

### 10. `token-interaction-patterns-209-lines-loaded-unconditionally-by-24-commands-and-2-agents-while-only-38-lines-are-the-rule-and-159-are-json-examples-and-recurring-patterns`
- **Alvo:** `skills/shared/interaction-patterns/SKILL.md`
- **Estado:** Ainda reproduz
- **Evidência:** `wc -l` = **209** linhas, idêntico à baseline; `ls skills/shared/interaction-patterns/` retorna apenas `SKILL.md` — nenhum `references/` foi criado.
- **Nota:** Nenhum commit da janela tocou o diretório.

### 11. `flow-relayout-design-discovery-names-storybook-tailwind`
- **Alvo:** `commands/relayout.md`
- **Estado:** Ainda reproduz
- **Evidência:** `commands/relayout.md:32` — "look in common locations (`docs/design-system.md`, `.claude/docs/ui/design-system.md`, a Storybook config, a Tailwind/theme config) for tokens".
- **Nota:** Arquivo não tocado na janela.

### 12. `auto-full-suite-guard-sed-absorbs-sibling-json-keys`
- **Alvo:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`
- **Estado:** Ainda reproduz
- **Evidência:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:31` — "`COMMAND=$(printf '%s' "$INPUT" | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\(.*\)"[[:space:]]*[,}].*/\1/p' | head -1)`". Reproduzido no HEAD com dois payloads cujo `command` é `npm test` (que sozinho dispara o nudge — controle confirmado):
  - `{"tool_name":"Bash","tool_input":{"command":"npm test","description":"run .test. files with --filter"}}` → **silêncio**
  - `{"tool_name":"Bash","tool_input":{"command":"npm test"},"description":"checking the .spec. suite"}` → **silêncio**
- **Nota:** A linha do `sed` migrou de `:22` para `:31` e o comentário `:28-30` agora declara a ganância **deliberada** ("Greedy match … so a command wrapped in nested quotes … is captured whole"), sem tratar o efeito colateral nas chaves irmãs. `abb8483` tocou o arquivo na janela.

### 13. `flow-learn-run-marker-records-commit-time-not-run-time`
- **Alvo:** `commands/learn.md`
- **Estado:** Ainda reproduz (metade secundária resolvida)
- **Evidência:** `commands/learn.md:166` — "`echo "$(git log -1 --format=%ct 2>/dev/null || date +%s) $(git rev-parse HEAD 2>/dev/null)" > .dev-team-agents/.learn-last-run`" — literal inalterado; ainda grava o timestamp do commit do HEAD, não o horário da execução.
- **Nota:** A segunda metade do achado (condição de skip inalcançável em `commands/commit.md`) foi corrigida por `576dcfa`, que moveu a captura para depois dos commits — `commands/commit.md:179` agora diz "now reflecting the commits just made". O defeito de timestamp permanece e ainda afeta a comparação com o mtime de `session-summary.md` na execução standalone de `/devteam:learn`.

### 14. `auto-install-heredoc-omits-auto-learn-before-commit`
- **Alvo:** `scripts/install.sh`
- **Estado:** Ainda reproduz
- **Evidência:** heredoc de fallback em `scripts/install.sh:1160-1182` lista 21 chaves e **não** contém `auto_learn_before_commit`; o canônico `scripts/lib/preferences-defaults.json:18` — "`"auto_learn_before_commit": true,`". `rg -n auto_learn scripts/install.sh` → zero ocorrências.
- **Nota:** O aviso de drift continua no lugar, agora em `:1155-1156` — "the two drifted once already (qa_browser was missing)". `scripts/install.sh` foi tocado na janela sem que a chave fosse espelhada.

### 15. `docs-sync-02c-comment-cites-graphify-hint-as-sed-precedent`
- **Alvo:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`
- **Estado:** Ainda reproduz
- **Evidência:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:27` — "consistent with 02-graphify-hint.sh's pure-bash approach on the hot path" — logo acima de um `sed` com fork; contra `scripts/hooks/pre-tool-use/02-graphify-hint.sh:24` — "Pure-bash substring match instead of grep|sed: skips 2 forked subprocesses".
- **Nota:** `53f912f` reescreveu `02-graphify-hint.sh` na janela e o comentário dos 2 forks migrou de `:11` para `:24`, mas sobreviveu — a contradição continua literal.

### 16. `gov-repo-gitignore-omits-three-installer-written-entries`
- **Alvo:** `.gitignore`
- **Estado:** Ainda reproduz (parcialmente corrigido)
- **Evidência:** `git check-ignore -v .dev-team-agents/.learn-last-run` → **não ignorado**. `.gitignore` no HEAD (11 linhas) não contém `.dev-team-agents/.learn-last-run` nem `!.dev-team-agents/user-data/graphify.json`, ambos escritos por `scripts/install.sh:929` e `:932`; `agents/setup-assistant.md:153` continua declarando as quatro obrigatórias.
- **Nota:** `8e428a7` ("add worktree-session") fechou **uma** das entradas faltantes — `.gitignore:8` agora tem `.dev-team-agents/.worktree-session`. Restam duas; o achado deve ser re-escopado de "three" para "two" quando for atacado.

### 17. `flow-audit-step2-unconditional-docker-stack-ignores-isolate-pref-compose-gate`
- **Alvo:** `commands/audit.md`
- **Estado:** Ainda reproduz
- **Evidência:** `commands/audit.md:54` — "After worktree creation, spin up an isolated Docker stack following the worktree's docker-isolation references." Sem condicional. Os dois gates seguem em `skills/shared/worktree/references/docker-isolation.md:11-12` — "`worktree_docker_isolate` is `true` … and the project uses Docker Compose (a compose file exists and `docker` is running)".
- **Nota:** `7e62124` tocou `commands/audit.md` na janela sem corrigir o Step 2.

### 18. `flow-mobile-command-spawn-line-enumerates-stacks-dropped-from-agent-description`
- **Alvo:** `commands/mobile.md`
- **Estado:** Ainda reproduz
- **Evidência:** `commands/mobile.md:19` — "`mobile-developer` — implement the mobile changes (React Native, Expo, Flutter, native iOS/Android)"; contra `agents/mobile-developer.md:3` — "Detects the project's mobile stack and follows its platform conventions."
- **Nota:** Arquivo não tocado na janela.

### 19. `agent-database-specialist-access-inlines-supabase-cli-while-delegating-others`
- **Alvo:** `agents/database-specialist.md`
- **Estado:** Ainda reproduz
- **Evidência:** `agents/database-specialist.md:133` — "CLI patterns are in each engine's per-engine skill. Supabase PostgreSQL: `psql "$SUPABASE_DB_URL"`." — as duas sentenças permanecem adjacentes.
- **Nota:** Arquivo não tocado na janela.

### 20. `ref-docs-agents-md-tier-column-stale-backend-test-specialist-listed-repetitive`
- **Alvo:** `docs/agents.md`
- **Estado:** Ainda reproduz
- **Evidência:** `docs/agents.md:28` — "| `backend-test-specialist` | Backend test coverage (conditional) | DEVELOPMENT | `repetitive` |"; espelhado em `docs/agents.pt-BR.md:28`. Valor real: `agents/backend-test-specialist.md:4` — "`tier: backend-exec`". `CLAUDE.md:87` continua proibindo por escrito — "Do not move a test agent to `repetitive`."
- **Nota:** HIGH; nenhum commit da janela tocou `docs/agents.md`.

### 21. `ref-tool-map-tool-rewrites-loaded-but-never-emitted-by-render-provider`
- **Alvo:** `scripts/lib/render_provider.py`
- **Estado:** Ainda reproduz
- **Evidência:** `scripts/lib/render_provider.py:742` — "`renames = prov_entry.get("tool_rewrites", {}) or {}`"; usado apenas como booleano em `:748` — "`if not renames and not idioms:`"; o único laço de emissão itera `idioms` (`:752-753` — "`for line in idioms: note_lines.append(f"> {line}")`"). Nenhum `for … in renames` no arquivo.
- **Nota:** HIGH; `CLAUDE.md:67` e `docs/providers.md:127` seguem documentando o rewrite como ativo.

### 22. `ref-02c-guard-make-composer-shapes-have-no-row-in-scoped-test-runner-table`
- **Alvo:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`
- **Estado:** Ainda reproduz
- **Evidência:** `02c-full-suite-guard.sh:100` — "`[[ "$cmd" != *TESTPATH=* && "$cmd" != *FILTER=* && "$cmd" != *--\ * ]] && return 0`". A tabela em `skills/shared/scoped-test-execution/SKILL.md:45-57` tem 11 linhas (Jest → Cargo) e **nenhuma** de Make ou Composer; `rg TESTPATH|FILTER=` na skill → zero. `SKILL.md:59` segue declarando legítimo o caminho que o guard sinaliza — "When the project defines its own scoped script in `CLAUDE.md`, `package.json`, or a `Makefile`, that command wins over the table."
- **Nota:** `abb8483` tocou o guard na janela; a skill não foi tocada.

### 23. `docs-sync-changelog-unreleased-omits-full-suite-guard-and-orchestration-deltas`
- **Alvo:** `CHANGELOG.md`
- **Estado:** Ainda reproduz (âncora mudou)
- **Evidência:** `rg -n "composer|Makefile|opaque wrapper|Background Process|fire-and-forget" CHANGELOG.md` → **zero ocorrências**. O comportamento de `c03f898` ("detect unscoped make/composer test wrappers") e o § Background Process Discipline de `21fceb4` seguem sem entrada. `.github/pull_request_template.md:21` continua exigindo o registro.
- **Nota:** A seção `[Unreleased]` foi consumida na janela (só resta o link de comparação em `CHANGELOG.md:983`) e `c03f898` **parcialmente** entrou como 2.45.1 ("Unscoped full-suite test runs now blocked, not just nudged") — mas essa entrada descreve `abb8483`, não a detecção de wrappers. Segue sem gate automatizado.

### 24. `ref-scoped-test-execution-bash-parallelism-section-outside-declared-canonical-scope`
- **Alvo:** `skills/shared/scoped-test-execution/SKILL.md`
- **Estado:** Ainda reproduz
- **Evidência:** `skills/shared/scoped-test-execution/SKILL.md:63-65` — "## Run Independent Verification Commands in Parallel … issue them as **separate Bash tool calls in the same message**". A `description:` em `:3` continua "Run only tests covering the touched code; full suite only on explicit user request." — sem menção a paralelismo; `CLAUDE.md:166` mantém o escopo canônico restrito a "Which tests to execute when finishing a task".
- **Nota:** Arquivo não tocado na janela.

### 25. `docs-sync-hooks-md-64-full-suite-guard-examples-predate-wrapper-detection`
- **Alvo:** `CLAUDE-md/hooks.md`
- **Estado:** Ainda reproduz (agravado)
- **Evidência:** `CLAUDE-md/hooks.md:64` — "when a `Bash` command matches an unscoped full-suite shape (e.g. `pytest` with no path/`-k`, `vendor/bin/phpunit` with no `--filter`), it injects an `additionalContext` reminder of the rule — **it never blocks**".
- **Nota:** Além da classe de wrappers opacos continuar ausente dos exemplos, `abb8483` introduziu na janela um caminho de bloqueio (`02c-full-suite-guard.sh:124` — "`exit 2`") sem tocar `CLAUDE-md/hooks.md`, então a prosa agora afirma o **oposto** do comportamento. Mesma contradição em `:55` — "nudges on unscoped full-suite test commands".

### 26. `flow-update-sh-codex-slim-guard-dead-branch-false-strip-claim`
- **Alvo:** `scripts/update.sh`
- **Estado:** Ainda reproduz
- **Evidência:** `scripts/update.sh:118` — "`if [ -f ".dev-team-agents/scripts/render-provider.sh" ] && [ -f ".dev-team-agents/agents/product-analyst.md" ]; then`". `scripts/lib/strip-tarball.sh:21-24` remove apenas `.claude`, `.github`, `helpers` e `opencode` — nem `scripts/` nem `agents/` são tocados, logo o guard nunca avalia falso. O comentário em `:99-100` segue afirmando "cross-CLI plumbing … stripped by `scripts/lib/strip-tarball.sh`".
- **Nota:** HIGH; `scripts/update.sh` não foi tocado na janela. O guard **opencode** (`:104`) testa `.dev-team-agents/opencode/plugin/dev-team-agents.ts`, que de fato é stripado — só o guard Codex está morto.

### 27. `flow-02c-composer-fallback-case-ignores-every-scope-qualifier`
- **Alvo:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`
- **Estado:** Ainda reproduz
- **Evidência:** `02c-full-suite-guard.sh:106-108` — "`*composer\ test*) [[ "$cmd" != *test:* ]] && return 0`" — único `case` da função sem qualificador de escopo. Reproduzido no HEAD: `composer test tests/Unit/FooTest.php` e `composer test-unit --filter FooTest` disparam o `additionalContext` de 405 bytes.
- **Nota:** `abb8483` tocou o arquivo na janela sem alterar esse `case`.

### 28. `flow-update-sh-provider-reinstall-aborts-on-non-exit-3-failures`
- **Alvo:** `scripts/update.sh`
- **Estado:** Ainda reproduz
- **Evidência:** `scripts/update.sh:106` — "`bash .dev-team-agents/scripts/install-opencode.sh`" e `:120` — "`bash .dev-team-agents/scripts/install-codex.sh`" — ambas sem `|| true` e sem captura de código de saída, sob o `set -euo pipefail` do topo do script. Qualquer `exit 1` (falta de `jq`/`python3`, snippet vazio) derruba o update depois do core já ter sucedido.
- **Nota:** O fix anterior espelhou apenas a pré-condição do `exit 3`.

### 29. `flow-architect-claude-only-async-tool-names-rendered-verbatim`
- **Alvo:** `agents/software-architect.md`
- **Estado:** Ainda reproduz
- **Evidência:** `agents/software-architect.md:88` — "**On a status question, call `TaskList`/`TaskGet`/`TaskOutput` first**"; `:89` — "**Before ending a turn with an unreturned spawn, call `ScheduleWakeup`** … resume with `SendMessage`". `rg "ScheduleWakeup|SendMessage|TaskList|Monitor" scripts/lib/tool-map.json` → **zero ocorrências**.
- **Nota:** `a3e6095` tocou o arquivo na janela sem adicionar hedge nem entrada no tool-map; os nomes seguem chegando literais ao render de opencode/Codex.

### 30. `flow-02c-make-pattern-substring-matches-cmake-and-chained-cmds`
- **Alvo:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`
- **Estado:** Ainda reproduz
- **Evidência:** `02c-full-suite-guard.sh:99` — "`*make\ *test*|*make\ *-e2e*)`". Reproduzido no HEAD: `cmake --build . && ./run_tests` e `make migrate-test-db && phpunit --filter X` disparam o nudge.
- **Nota:** Sem âncora de início de comando e sem barreira em `&&`/`;`.

### 31. `flow-prompt-auditoria-commit-step-contradicts-branch-rule`
- **Alvo:** `docs/reports/_prompt-auditoria.md`
- **Estado:** Ainda reproduz
- **Evidência:** `docs/reports/_prompt-auditoria.md:322` — "After the two report files are written, commit **only** them and push to `main`." (a auditoria produz 8 arquivos); `:348` — mensagem de commit de métricas "`docs(reports): metrics reports updates`"; `:354` — "`git push "https://${TOKEN}@github.com/…" main`". Contra a regra inviolável 8 do próprio arquivo, `:34` — "Trabalhe e faça push apenas na branch designada da sessão."
- **Nota:** Bloco claramente copiado do prompt de métricas; arquivo não tocado na janela.

### 32. `flow-background-process-discipline-monitor-no-availability-fallback`
- **Alvo:** `skills/architecture/orchestration/SKILL.md`
- **Estado:** Ainda reproduz
- **Evidência:** `skills/architecture/orchestration/SKILL.md:262` — "has exactly one legitimate way to be watched: `Monitor` on that same command." Nenhuma cláusula de indisponibilidade no § Background Process Discipline (`:254-272`), enquanto o check de auto-reativação carrega a sua em `:241-243` — "If `ScheduleWakeup` is not available in the current context, this check cannot be satisfied — fall back to check 4's reactive behavior".
- **Nota:** `a3e6095` tocou o arquivo na janela e criou um **segundo** `### 5.` (`:213` "Auto-reactivation" e `:245` "Periodic status table"), tornando ambíguas as referências cruzadas a "check 5" em `:271` e em `agents/software-architect.md:89` — candidato a achado novo na Fase 2.

### 33. `skill-token-efficiency-background-mgmt-contradicts-orchestration-discipline`
- **Alvo:** `skills/shared/token-efficiency/strategies.md`
- **Estado:** Ainda reproduz
- **Evidência:** `skills/shared/token-efficiency/strategies.md:328` — "## Background Process Management"; `:334` — "# Tell user once with the ID, then don't poll"; `:339` — "`TaskOutput(task_id="abc123")`" para ler um shell de background; `:342` — "Avoid repeated polling … Let the user decide when to check results." Contra `skills/architecture/orchestration/SKILL.md:267-269` — "**A background command is not fire-and-forget.** Once started, either await it inline … or call `Monitor`".
- **Nota:** HIGH; `token-efficiency` é carregado por 18 agentes, `orchestration` por 1. Nenhum dos dois arquivos foi corrigido na janela.

### 34. `agent-line-cap-205-documented-in-claude-md-vs-211-enforced-by-size-limits`
- **Alvo:** `CLAUDE.md`
- **Estado:** Ainda reproduz
- **Evidência:** `CLAUDE.md:92` — "`helpers/size-limits.sh` enforces 205 — the extra 5 lines are the fixed-size run-banner block"; `CLAUDE.md:313` — "size-limits.sh ← agents 205 (200 content + 5 run-banner)". Contra `helpers/size-limits.sh:44` — "`AGENT_LIMIT=211`".
- **Nota:** HIGH; `CLAUDE.md` foi tocado na janela sem que a divergência fosse fechada.

### 35. `agent-software-architect-inlines-spawn-integrity-4-5-no-availability-guard`
- **Alvo:** `agents/software-architect.md`
- **Estado:** Ainda reproduz
- **Evidência:** `agents/software-architect.md:89` — "**Before ending a turn with an unreturned spawn, call `ScheduleWakeup`** instead of going silent (Spawn Integrity check 5, Auto-reactivation)." Sem o guard de `skills/architecture/orchestration/SKILL.md:241-243` ("If `ScheduleWakeup` is not available … fall back to check 4's reactive behavior and say so if asked").
- **Nota:** `a3e6095` tocou a linha na janela sem restaurar a delegação; e como agora existem dois `### 5.` na skill, a referência "check 5" no corpo do agente aponta para o alvo errado.

### 36. `skill-orchestration-spawn-integrity-unreachable-from-devteam-commands`
- **Alvo:** `commands/*.md`
- **Estado:** Ainda reproduz
- **Evidência:** `rg -ln "architecture/orchestration|orchestration/SKILL" commands/` → **zero arquivos** entre os 35 comandos. Única ocorrência da palavra é prosa em `commands/architect.md:22` — "…and orchestration of implementation agents."
- **Nota:** Os checks 1–5 continuam alcançando apenas `agents/software-architect.md`.

### 37. `skill-orchestration-restates-scoped-test-execution-exception`
- **Alvo:** `skills/architecture/orchestration/SKILL.md`
- **Estado:** Ainda reproduz
- **Evidência:** `skills/architecture/orchestration/SKILL.md:74-77` — "4. **Scoped test execution** — never instruct a subagent to run the project's full test suite … Only relay a full-suite run when the user asked for one in this session". Duplica `skills/shared/scoped-test-execution/SKILL.md:20` (§ Orchestrator Rule) — "Relay a full run only when the user asked for one in this session, and say so explicitly." `CLAUDE.md:166` proíbe a reescrita.
- **Nota:** O bloco migrou de `:68-70` para `:74-77`; conteúdo inalterado.

### 38. `token-02c-full-suite-guard-substring-match-injects-nudge-on-non-test-commands`
- **Alvo:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`
- **Estado:** Ainda reproduz
- **Evidência:** `02c-full-suite-guard.sh:51` — "`*jest*)`", `:63` — "`*pytest*)`", `:89` — "`*rspec*)`" — sem âncora de invocação. Reproduzido no HEAD, 3 de 3 comandos de leitura disparam os 405 bytes de `additionalContext`: `cat jest.config.js`, `ls -la pytest.ini`, `git log --oneline -- spec/rspec_helper.rb`.
- **Nota:** Com `abb8483` o risco subiu: numa árvore limpa sem commits do dia, esses mesmos comandos passam a **bloquear** (`exit 2`), não apenas injetar contexto.

### 39. `token-pr-md-unbounded-full-diff-to-repetitive-tier-while-same-file-caps-git-log`
- **Alvo:** `commands/pr.md`
- **Estado:** 🟢 **Resolved:** 2026-08-21 — resolvido por `8267da1`
- **Evidência:** `commands/pr.md:99` — "Fill each section from `git diff ${DEFAULT_BRANCH}...HEAD --stat`, `git log ${DEFAULT_BRANCH}...HEAD`, and recent commits. **Do not pull the full unscoped diff into context — a PR body is a summary, not a diff reproduction.** Pull a targeted `git diff ${DEFAULT_BRANCH}...HEAD -- <path>` only for the handful of files whose specific content the template section actually needs".
- **Nota:** `8267da1` ("fix(skills): scope reviewer and PR diffs to avoid oversized prompts") trocou o `git diff base...HEAD` irrestrito por `--stat` + diffs por caminho; registrado no CHANGELOG 2.45.1.

### 40. `token-orchestration-skill-377-lines-138-conditional-path-only-no-references-dir`
- **Alvo:** `skills/architecture/orchestration/SKILL.md`
- **Estado:** Ainda reproduz (agravado)
- **Evidência:** `wc -l` = **391** linhas (era 377); `ls skills/architecture/orchestration/` retorna apenas `SKILL.md` — nenhum `references/`.
- **Nota:** Os dois commits da janela (`a3e6095`, `a06102d`) somaram +14 linhas, e o novo `### 5. Periodic status table` (`:245-251`) caiu justamente no bloco condicional que o achado aponta como extraível.

### 41. `token-model-identity-32-of-58-lines-are-format-spec-and-examples-held-inline`
- **Alvo:** `skills/shared/model-identity/SKILL.md`
- **Estado:** Ainda reproduz
- **Evidência:** `wc -l` = **58** linhas, inalterado. `## Format` em `:27` e `## Examples` em `:40` seguem inline, com três tabelas de exemplo de outros agentes (`:46` `backend-developer`, `:52` `software-architect`, `:58` `technical-writer`).
- **Nota:** Arquivo não tocado na janela.

### 42. `token-project-context-restates-scoped-test-exception-table-read-by-18-agents`
- **Alvo:** `skills/shared/project-context/SKILL.md`
- **Estado:** Ainda reproduz
- **Evidência:** `skills/shared/project-context/SKILL.md:207-213` — tabela de 6 linhas reafirmando a exceção ("| A scoped test failed | Fix it — a failure never authorizes widening the run |", "| The change touches shared code, or the suite is fast | Still scoped…"); `:216` — "Load the skill for the blast-radius derivation and the per-stack runner filters. **Do not work from this table alone.**"
- **Nota:** A auto-admissão em `:216` permanece; `CLAUDE.md:166` proíbe a reescrita da exceção fora de `scoped-test-execution`.
