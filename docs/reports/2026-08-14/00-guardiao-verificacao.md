# Fases 1 e 1b — Verificação guardiã

**Data:** 2026-08-14 · **Baseline:** `HEAD` = `c03f898` · **Baseline anterior:** `3fbe371`

## Método

O relatório-fonte descreve o *problema*; o git descreve o *fato*. Cada marcação foi reconstruída a
partir do diff da janela da data da marca (`git log --since/--until`, `git show --stat`,
`git show <sha> -- <alvo>`), reconfirmada no HEAD por símbolo (`rg`, nunca por número de linha
antigo) e checada contra reversão silenciosa (`git log --oneline --since=<data> -- <alvo>`).

> **Nota de fuso.** Commits registrados como `2026-07-31` aparecem sob `--since=2026-07-30
> --until=2026-08-02`. A janela foi alargada em todos os itens antes de se concluir "nenhum commit".

**Amostragem.** Conjunto verificável = 124 (122 ✅ Executed + 2 ⚠️ Partial), acima do limiar de 60.
Critério aplicado: **todos** os HIGH (11) e MEDIUM-HIGH (7) — 18 itens — mais amostra sistemática de
**31 dos 103 restantes** (30%, passo determinístico sobre a ordem do banco). Cobertura declarada:
**49 de 124 verificados (40%)**.

**Placar da Fase 1: 42 ✅ · 4 🟡 · 3 🔴** — taxa de reabertura **6,1%** (3 de 49), abaixo do limiar
de escalonamento de 15%. A integridade do banco **não** está comprometida; os eixos seguem sendo o
resultado principal do pass.

---

## Fase 1 — Marcações HIGH e MEDIUM-HIGH (18 de 18 verificadas)

### `ref-docs-agents-md-model-column-wrong-technical-writer-...-setup-assistant-listed-sonnet-actually-opus`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** HIGH
- **Marca verificada:** ✅ Feito
- **Commit examinado:** `bbb311a` — "docs: correct stale authoring standards, structure maps and command tables"
- **Evidência no HEAD:** `docs/agents.md:35` — "| `technical-writer` | API docs, READMEs, runbooks, changelogs | SUPPORT | `repetitive` |"; `docs/agents.md:36` — "| `setup-assistant` | Project setup + version management | SETUP | `reasoning` |". A coluna `Model` foi **removida** e substituída por `Tier`, eliminando o duplicado hand-maintained de `tiers.json`. Espelho pt-BR em sincronia (`docs/agents.pt-BR.md:35-36`). Sem reversão nos 2 commits posteriores.

### `ref-claude-md-183-code-reviewer-roles-says-delegates-to-test-specialists-but-impl-routes-to-reviewers`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** HIGH
- **Marca verificada:** ✅ Feito
- **Commit examinado:** `bbb311a`
- **Evidência no HEAD:** `CLAUDE.md:262` — "It then proceeds as `backend-reviewer` (`BACKEND`), as `frontend-reviewer` (`FRONTEND`), or emits the parallel routing message and stops (`BOTH`)". O diff da janela remove literalmente a frase "delegates to `backend-test-specialist` or `frontend-test-specialist` as needed".

### `ref-two-helpers-dirs-naming-collision-root-stripped-vs-scripts-helpers-shipped`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** HIGH
- **Marca verificada:** ✅ Feito
- **Commit examinado:** `bbb311a`
- **Evidência no HEAD:** `CLAUDE.md:358` — "**Two `helpers` directories — do not confuse them:**", com a tabela em `:361-363` marcando `scripts/helpers/` como "**Yes** — inside the allowlisted `scripts/` tree … Currently `telemetry-send.sh`". Ambas as linhas são `+` no diff da janela.

### `ref-claude-md-file-structure-omits-helpers-and-privacy-and-claude-md-folder`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** HIGH
- **Marca verificada:** ✅ Feito
- **Commit examinado:** `bbb311a`
- **Evidência no HEAD:** as seis entradas omitidas estão presentes na árvore de `CLAUDE.md`: `:299` `├── CLAUDE-md/`, `:306` `├── helpers/`, `:316` `├── opencode/`, `:346` `├── .github/`, `:347` `├── user-data/`, `:353` `├── PRIVACY.md`. Todas como linhas `+` no diff da janela.

### `flow-size-limits-sh-ci-only-warn-only-not-in-stop-dispatcher-asymmetric-with-agent-lint-200-cap`

- **Marca original:** ✅ Executed 2026-07-31 (já 🟡 desde 2026-07-31) · **Severidade:** HIGH
- **Marca verificada:** 🟡 Parcialmente feito — **segunda confirmação**
- **Commit examinado:** `7736e20` — "docs: sync documentation with six waves of changes, enforce both size gates"
- **Evidência no HEAD:** `.github/scripts/ci/01-lint.sh:88` — "blocking \"size-limits\" bash helpers/size-limits.sh". `bash helpers/size-limits.sh` no HEAD: "size-limits: clean ✓".
- **Nota:** o sub-escopo faltante é o mesmo de 14 dias atrás e **não avançou**: não existe equivalente no dispatcher Stop. `grep -rn 'size-limits\|wc -l' scripts/hooks/stop/*.sh` não retorna nada; `scripts/hooks/stop/03-agent-lint.sh:24` apenas faz `exec bash helpers/agent-lint.sh --quiet`, e `agent-lint.sh` não tem contagem de linhas. A assimetria original (feedback só no CI, depois do push) permanece.

### `ref-telemetry-honors-pref-but-pref-defaults-true-on-fresh-install-without-prompt`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** HIGH
- **Marca verificada:** ✅ Feito
- **Commit examinado:** `2e12335` — "fix(install): make the swap failure-safe and stop enabling telemetry without consent"
- **Evidência no HEAD:** `scripts/install.sh:903` — "TELEMETRY_VALUE=\"false\"", sob o comentário `:897-902` ("The default is DISABLED: if no terminal is reachable there is no way to obtain consent"). O gate virou `_can_prompt` (`:906`); timeout/EOF conta como recusa (`:929-933`). Fail-closed espelhado no consumo em `scripts/lib/telemetry-guard.sh:24-26`.

### `flow-helpers-archive-index-sh-orphan-of-hook-...-rotation-90-day-promise-has-no-trigger`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** HIGH
- **Marca verificada:** ✅ Feito
- **Commit examinado:** `cc28900` — "fix(hooks): gate, decompose and harden the lifecycle dispatchers" (criou `scripts/hooks/stop/99b-archive-index.sh`) + `c7535b7` (reparou o parser do helper na mesma janela)
- **Evidência no HEAD:** `scripts/hooks/stop/99b-archive-index.sh:21` — "SCRIPT=\"$REPO_ROOT/helpers/archive-index.sh\"", com stamp diário em `:27`. O arquivo está no tier `99-` do dispatcher e **não** carrega prefixo `_disabled-`. Documentado em `CLAUDE-md/hooks.md:32`.

### `auto-update-no-integrity-check`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM-HIGH
- **Marca verificada:** ✅ Feito
- **Commit examinado:** `2e12335` (criou `scripts/lib/installer-fetch.sh`)
- **Evidência no HEAD:** `scripts/update.sh:46` — "INSTALLER_LIB=\"$SCRIPTS_DIR/lib/installer-fetch.sh\"" e `:89` "passes verification (see the integrity model in scripts/lib/installer-fetch.sh)". O modelo está em `installer-fetch.sh:19-46`: HTTPS-only, ref pinado igual ao do payload, shape + `bash -n` + markers, e "if a SHA-256 digest is available it MUST match, and a mismatch aborts (fail closed)".
- **Nota:** completo no escopo do achado (o `curl … | bash` sem verificação sumiu). Registre para passes futuros que o passo do digest é hoje um hook inerte — `scripts/install.sh.sha256` não existe no repo. O próprio cabeçalho declara isso, o que sustenta ✅ e não 🟡.

### `gov-telemetry-send-sh-posthog-key-comments-self-contradict`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM-HIGH
- **Marca verificada:** ✅ Feito
- **Commit examinado:** `2e12335`
- **Evidência no HEAD:** `scripts/helpers/telemetry-send.sh:23-30` — "the `phc_` prefix marks a write-only capture key … Shipping it in this file is intentional and is not a secret leak". Bloco único e coerente; `grep -i 'TODO'` no arquivo retorna vazio; os dois valores viraram overridable via `DEVTEAM_POSTHOG_KEY` / `DEVTEAM_POSTHOG_ENDPOINT` (`:31-32`).

### `agent-security-specialist-body-130-153-hardcodes-per-language-sast-and-dep-audit-commands`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** HIGH
- **Marca verificada:** ✅ Feito
- **Commit examinado:** `b4e219f` — "refactor(agents): delegate shared context, extract stack-prescriptive bodies"
- **Evidência no HEAD:** `agents/security-specialist.md:122` — "Load `skills/security/dependency-audit/SKILL.md` and follow its order: always-run tier … → ecosystem lockfile signal → matching dependency scanner → language-specific SAST". `rg -in 'bandit|trivy|composer audit|npm audit|semgrep|pip-audit|gosec|brakeman'` no agente retorna **zero** hits.

### `agent-backend-developer-integration-awareness-section-duplicates-provider-specific-rules-inline`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** HIGH
- **Marca verificada:** ✅ Feito
- **Commit examinado:** `b4e219f`
- **Evidência no HEAD:** `agents/backend-developer.md:73` — "Detect the platform from project signals, then load the matching skill **before** writing code. The skill is the source of truth for its rules — never act on these platforms from memory". A seção `:75-84` é hoje tabela pura `Detection signal | Skill to load`, sem regras inline. Agente 265 → 167 linhas.

### `agent-frontend-test-specialist-107-122-hardcodes-react-renderhook-and-vue-withsetup-recipes`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** HIGH
- **Marca verificada:** ✅ Feito
- **Commit examinado:** `b4e219f`
- **Evidência no HEAD:** `agents/frontend-test-specialist.md:103` — "load `skills/testing/frontend-hook-tests/SKILL.md` and read only the framework row its Detection table resolves to". É a **única** ocorrência de `React|Vue|renderHook|withSetup|testing-library` no arquivo, e é a linha de delegação. Agente 266 → 195 linhas.

### `agent-devops-specialist-decision-framework-and-anti-overengineering-still-stack-prescriptive`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** HIGH
- **Marca verificada:** ✅ Feito
- **Commit examinado:** `b4e219f`
- **Evidência no HEAD:** `agents/devops-specialist.md:129` — "Load `skills/devops/infrastructure-sizing/SKILL.md` … It defines the capability tiers, the trigger that must fire before moving up a tier, and the anti-overengineering rules". O diff da janela remove a tabela `Traffic | Recommended` e as 6 bullets de Anti-Overengineering; os headings `## Decision Framework` e `## Anti-Overengineering Rules` não existem mais.

### `agent-code-reviewer-router-has-ten-structural-review-categories-contradicting-claude-md`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM-HIGH
- **Marca verificada:** ✅ Feito
- **Commit examinado:** `b4e219f`
- **Evidência no HEAD:** `agents/code-reviewer.md:71` — "## Router Responsibilities", com exatamente três sub-seções (`:75`, `:84`, `:93`). As 10 categorias estruturais sumiram. Agente 233 → 198 linhas. Coerente com `CLAUDE.md:262`.

### `agent-backend-test-specialist-body-114-120-hardcodes-per-language-coverage-command-matrix`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM-HIGH
- **Marca verificada:** ✅ Feito
- **Commit examinado:** `b4e219f`
- **Evidência no HEAD:** `agents/backend-test-specialist.md:106` — "read `references/quality-gates.md` in that skill for the per-language test-runner command, output artifact, and `sonar.*coverage.reportPaths` key". `rg -in 'clover|jacoco|simplecov'` no agente retorna **zero** hits.

### `skill-architecture-awareness-shared-behavioral-skill-enumerates-react-vue-svelte-angular-...`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM-HIGH
- **Marca verificada:** ✅ Feito
- **Commit examinado:** `519ca7e` — "feat(skills): add extraction targets, close domain gaps, fix skill defects"
- **Evidência no HEAD:** `rg -in 'react|vue|svelte|angular|blade|twig|erb|jinja|laravel|django|rails' skills/shared/architecture-awareness/SKILL.md` retorna **zero** hits em 87 linhas. O roteamento é por papel: `:14` — "| Agent implementing server-side code | **Backend Context** |".

### `token-claude-md-426-lines-still-monolithic-three-extractable-blocks`

- **Marca original:** ✅ Executed 2026-07-31 (já 🔴 desde 2026-07-31) · **Severidade:** MEDIUM-HIGH
- **Marca verificada:** 🔴 Não feito — **segunda confirmação**
- **Commit examinado:** nenhum commit da janela extraiu qualquer um dos três blocos. Os commits da janela em `CLAUDE.md` (`bbb311a`, `6919564`, `7736e20`, `48b9307`, `755ecef`) **adicionaram** conteúdo. A única extração real é `2b436ea` (2026-08-03), **fora da janela**.
- **Evidência no HEAD:** `CLAUDE.md` tem **586 linhas** (425 quando o achado foi aberto, 549 na reverificação de 07-31 — +38% sobre a baseline). O maior dos três blocos segue inline: `CLAUDE.md:211` — "| Command | Agents invoked | Use when… |", ~45 linhas dentro do arquivo sempre carregado.
- **Nota:** dois dos três sub-escopos (convenção de sub-scripts do Stop + Hook Files Map) foram resolvidos, mas por `2b436ea` em 2026-08-03 — pelo método isso é 🟢 Resolved para o sub-escopo, nunca ✅ para a marca de 07-31. O sub-escopo maior segue intacto.

### `token-foundational-rule-424-lines-across-17-agents`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM-HIGH
- **Marca verificada:** ✅ Feito
- **Commit examinado:** `b4e219f`
- **Evidência no HEAD:** `agents/backend-developer.md:21` — "Load `skills/shared/project-context/SKILL.md` — covers README, CLAUDE.md, AGENTS.md, project.md, session-summary, backlog, development docs, and recent git log." A lista de 12 itens inline não sobrevive em nenhum agente, e **18 de 18** referenciam a skill.

---

## Fase 1 — Amostra sistemática MEDIUM / LOW-MEDIUM / LOW (31 de 103)

### `ref-skill-ui-libraries-shadcn-frontmatter-name-shadcn-ui-no-validator-enforces-name-equals-dir`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `c7535b7` — "ci: close validator and enforcement gaps, repair the rotation helper"
- **Evidência no HEAD:** `skills/ui-libraries/shadcn/SKILL.md:2` — "`name: shadcn`"; validador em `helpers/agent-lint.sh:305-308` — "name '${name}' does not match directory '${dir_name}' (they must be identical)"; unicidade global em `:330`, invocada em `:489`.

### `ref-claude-md-356-stop-subscript-convention-omits-02b-orphan-template-scan`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `bbb311a`
- **Evidência no HEAD:** `CLAUDE-md/hooks.md:28` — "| `02-` | Repository integrity checks | `02-orphan-skill-scan.sh`, `02b-orphan-template-scan.sh` |"; `:32` — "| `99-` | Final/cleanup tasks | `99b-archive-index.sh` …|".
- **Nota:** a tabela migrou para `CLAUDE-md/hooks.md` em `2b436ea` **preservando** a correção.

### `ref-templates-backlog-template-md-orphan-confirmed-by-scanner`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `6919564` (`templates/backlog-template.md | 35 -----`)
- **Evidência no HEAD:** `ls templates/backlog-template.md` → "No such file or directory"; a skill homônima permanece em `skills/shared/backlog-template/SKILL.md:2`. `bash helpers/orphan-template-scan.sh` → "clean ✓".
- **Nota:** a remediação escolhida foi **remover** o template órfão, não casá-lo com a skill; registrado em `CHANGELOG.md:518`.

### `ref-three-reviewers-todo-fixme-issue-tracker-tickets-bullet-duplicated-verbatim`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** LOW-MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `b4e219f` (remove as 3 linhas duplicadas)
- **Evidência no HEAD:** `rg -i 'TODO|FIXME' agents/*.md` retorna só `agents/product-analyst.md:103` (contexto não relacionado); a regra vive em `skills/shared/comments-policy/SKILL.md:33`.

### `docs-sync-claude-md-package-exclusions`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** LOW-MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `bbb311a`
- **Evidência no HEAD:** `CLAUDE-md/user-data.md:47` — "| `opencode/` | explicit `rm -rf` | opencode provider-plugin source …|", pareando com `scripts/lib/strip-tarball.sh:24`. A tabela inteira (16 linhas) confere com `strip-tarball.sh:21-26` + `KEEP_ROOT`.

### `flow-ci-orphan-skill-scan-step-continue-on-error-true-never-blocks`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `c7535b7`
- **Evidência no HEAD:** política em `.github/scripts/ci/01-lint.sh:10-27`; os três níveis viraram dois wrappers (`:38` `blocking()`, `:44` `advisory()`); o tier tolerante restante é único (`:74`) e carrega `PROMOTE WHEN` em `:72`.
- **Nota:** resta deriva **cosmética** em `:80-88` — o comentário abre com "NOT blocking today: 11 of 17 agents exceed the 200-line agent cap" e fecha três linhas abaixo com "PROMOTED 2026-07-31 … so this is blocking". Comentário contraditório, sem efeito de comportamento; fora do escopo deste fingerprint.

### `flow-telemetry-pre-tool-use-02-runs-on-every-tool-call-without-batching-or-deduplication`

- **Marca original:** ✅ Executed 2026-07-31 (já 🔴 em 07-31, 🟢 anotado em 08-12) · **Severidade:** MEDIUM
- **Marca verificada:** 🔴 confirmado na janela; 🟢 procede no HEAD, **com atribuição de sha incorreta**
- **Commit examinado:** `cc28900` — único da janela a tocar o alvo, e é rename puro (`{02-telemetry.sh => 02b-telemetry.sh} | 0`)
- **Evidência no HEAD:** `scripts/hooks/pre-tool-use/02b-telemetry.sh:29-41` — "Cheap early-exit BEFORE the consent guard / python3 check below".
- **Nota:** a atribuição "resolvido por `156771b`" está errada em duas metades. (a) O enfileiramento (`--queue`/flush no Stop) já existia desde `bd61ff7`, antes da marcação — o que **reforça** o 🔴. (b) O early-exit por substring veio de `f1ca129` (2026-08-06); `156771b` (2026-08-11) apenas reativou os arquivos renomeados após a desativação de `ba39c86`. O estado final é o descrito; só o crédito precisa de correção.

### `ref-orphan-skill-scan-reports-design-system-audit-duplicate-load-in-ui-ux-designer`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `c7535b7` (substitui o regex de path por um programa awk)
- **Evidência no HEAD:** `helpers/orphan-skill-scan.sh:154-156` — "A bare path regex cannot tell a load directive from a narrative mention"; `:169` `LOAD_DIRECTIVE_AWK=`, consumido em `:190`. Execução no HEAD: "orphan-skill-scan: clean ✓".

### `flow-readme-sync-ci-gate-checks-only-section-count-and-50pct-line-threshold`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `c7535b7` (`.github/scripts/ci/02-readme-sync.sh | 205 ++-`)
- **Evidência no HEAD:** `:7-9` — "the ordered sequence of headings, and per-section counts of lines, code fences, table rows and links"; extrator em `:60`; comparações em `:113-137`.
- **Nota:** o gate segue **estrutural**, não semântico — `:17` declara que uma tradução fiel de conteúdo errado passa. Limite reconhecido de lint, não sub-escopo faltante.

### `flow-telemetry-stop-05-runs-after-04-notifier-but-no-fast-path-skip-when-DEVTEAM_NO_CHANGES-is-1`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** LOW-MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `cc28900`
- **Evidência no HEAD:** `scripts/hooks/stop/05-telemetry.sh:39` — "if [ \"${DEVTEAM_NO_CHANGES:-0}\" = \"1\" ]; then", com flush + `exit 0`; a flag é exportada em `scripts/hooks/stop.sh:32`.
- **Nota:** o arquivo ficou desativado entre `ba39c86` e `156771b`, mas o fast-path sobreviveu ao rename.

### `flow-install-sh-chmod-enumeration-omits-scripts-hooks-lib-subdir`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** LOW-MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `2e12335`
- **Evidência no HEAD:** `scripts/install.sh:820-824` — "The manual list silently went stale when scripts/hooks/lib/, scripts/helpers/ and scripts/lib/ were added — a recursive find cannot drift that way" + `find … -name '*.sh' -exec chmod +x {} +`.

### `ref-orphan-template-scan-consumers-list-omits-helpers-dir-and-claude-md`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** LOW-MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `c7535b7`
- **Evidência no HEAD:** `helpers/orphan-template-scan.sh:36-37` — `SHIPPED_CONSUMERS="agents skills commands scripts"` / `REPO_CONSUMERS="CLAUDE.md CLAUDE-md helpers"`, com a distinção documentada em `:21-24` e selecionada em `:63-65`.

### `flow-session-summary-closure-step-absent-from-fullstack-and-refactor`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** LOW-MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `6919564`
- **Evidência no HEAD:** `commands/fullstack.md:96` e `commands/refactor.md:161` — "1. **Session summary** — append this session's contribution to today's entry …".
- **Nota:** o passo se difundiu além dos dois alvos (`backend.md:97`, `frontend.md:88`, `mobile.md:106`, `design.md:28`, `seo.md:25`, `relayout.md:113`, `push.md:60`, `pr.md:136`). Doze commits posteriores não o removeram.

### `flow-orphan-template-scan-no-mapping-of-suggested-consumer-vs-orphan-skill-scan`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** LOW · **Verificada:** ✅ Feito
- **Commit examinado:** `c7535b7`
- **Evidência no HEAD:** `helpers/orphan-template-scan.sh:42-43` — "Suggested consumer for an orphan template, mirroring orphan-skill-scan.sh." / `suggest_consumer() {`; usado em `:103` e `:106`.

### `flow-setup-slash-command`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** LOW · **Verificada:** ✅ Feito
- **Commit examinado:** `519ca7e` (criou `commands/setup.md`, `--diff-filter=A` confirma)
- **Evidência no HEAD:** `commands/setup.md:11` — "`test -f docs/project.md && echo \"REFRESH\" || echo \"FIRST_RUN\"`"; registrado em `scripts/lib/commands.json:19`.

### `agent-frontend-developer-body-92-102-data-fetching-hardcodes-tanstack-query-swr`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM
- **Marca verificada:** 🟡 Parcialmente feito
- **Commit examinado:** `b4e219f`
- **Evidência no HEAD:** `agents/frontend-developer.md:96` — "recommend adopting the server-state library idiomatic to the project's stack (**TanStack Query and SWR** are the common choices in the **React/Vue** ecosystem) rather than hand-rolling one"
- **Nota:** o commit da janela entregou a parte principal — a tabela de detecção ganhou coluna `Rules to apply` + linha `None detected`, e o `useEffect + useState` prescritivo do fallback virou "a fetch inside the framework's own effect/lifecycle primitive". **Falta o sub-escopo exato do fingerprint:** identificadores de stack fora da tabela de detecção. Restam dois — `:96` (TanStack/SWR nominais, ancorados no "React/Vue ecosystem"; um projeto Svelte/Angular recebe duas libs do ecossistema errado) e `:91` ("e.g. React `useState`").

### `skill-mobile-ios-and-android-wrapper-pattern-net-loss`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `519ca7e` (skills) + `b4e219f` (roteamento no agente)
- **Evidência no HEAD:** `skills/mobile/ios/SKILL.md:8` — "This skill is the **engineering** half of iOS support"; a linha que empilhava o wrapper sobre a skill completa foi removida. Gate por sinal em `agents/mobile-developer.md:69` e `:72`.

### `agent-frontend-test-specialist-262-vs-backend-160-asymmetric-decoupled-frontend-block-inlined`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `519ca7e` + `b4e219f` (−120 linhas no agente)
- **Evidência no HEAD:** `agents/frontend-test-specialist.md:123` — "load `skills/testing/decoupled-frontend/SKILL.md` — network-layer mocking with MSW…". Assimetria fechada: 195 contra 150 linhas (era 262 vs 160).

### `agent-code-reviewer-15-item-foundational-rule-5-conditional-loads-eager-listed`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** LOW-MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `b4e219f`
- **Evidência no HEAD:** `agents/code-reviewer.md:57` — "**Conditional loads** — load at the point of use, never at startup:" seguido da tabela `| Trigger | Skill |`.

### `skill-architecture-graphql-235-lines-no-references-extraction-narrative-gate`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** LOW-MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `519ca7e` (−209 no SKILL.md, +187 em dois `references/`)
- **Evidência no HEAD:** `skills/architecture/graphql/SKILL.md` tem 92 linhas; `:8` — "## Detection Signals" com 7 sinais; `references/schema-and-operations.md` e `references/resolvers-and-errors.md` presentes.

### `skill-security-checklist-eager-loaded-by-both-security-specialist-and-qa-specialist`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** LOW-MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `519ca7e` (+44 linhas)
- **Evidência no HEAD:** `skills/security/security-checklist/SKILL.md:8` — "## Ownership Boundary — Security Audit vs QA", com partição explícita por seção OWASP e protocolo de cruzamento em `:46`.

### `agent-backend-developer-composition-root-rule-1-line-vs-frontend-developer-12-lines`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** LOW · **Verificada:** ✅ Feito
- **Commit examinado:** `b4e219f`
- **Evidência no HEAD:** `agents/backend-developer.md:100` — "Load `skills/architecture/design-patterns/SKILL.md` → Composition Root section when:" com três gatilhos; `agents/frontend-developer.md:139` cobre o mesmo em forma condensada.

### `skill-missing-prompt-engineering-or-llm-integration`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** LOW · **Verificada:** ✅ Feito
- **Commit examinado:** `519ca7e` (criou `skills/architecture/llm-integration/SKILL.md`, +220)
- **Evidência no HEAD:** skill com 222 linhas + `references/`; ponteiro corrigido em `skills/database/db-comparison/SKILL.md:37`; consumidor em `agents/software-architect.md:57`.

### `token-token-efficiency-skill-itself-154-lines-eager-loaded-by-all-17-agents`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM
- **Marca verificada:** 🔴 Não feito
- **Commit examinado:** `b4e219f` — tocou os 17 agentes, mas apenas **unificou a redação** da linha de load, que é o escopo do fingerprint vizinho `agent-…-token-efficiency-inline-line-vs-load-pattern-divergence`. Nenhum commit da janela tocou `skills/shared/token-efficiency/`.
- **Evidência no HEAD:** o load segue **eager em 18 de 18 agentes** (`rg -l token-efficiency agents/ | wc -l` = 18). Ex.: `agents/backend-developer.md:28` — "Apply `skills/shared/token-efficiency/SKILL.md` — prefer `grep`/`head` over full reads." A skill **cresceu de 154 para 160 linhas** e contraria `CLAUDE.md:177` — "Load it explicitly when: …".
- **Nota:** o achado **piorou** desde a marcação (16 → 18 consumidores, 154 → 160 linhas). A marcação ✅ confundiu a padronização da redação (entregue) com a remoção do load eager (não entregue).

### `token-code-reviewer-still-eager-loads-comments-policy-after-lazy-load-fix-applied`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `b4e219f`
- **Evidência no HEAD:** `agents/code-reviewer.md:57-60` — sob "**Conditional loads** — load at the point of use, never at startup:", a linha "| About to comment on comments in the code under review | `skills/shared/comments-policy/SKILL.md` |".

### `token-frontend-code-quality-description-288-chars-cauda`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `7736e20`
- **Evidência no HEAD:** `skills/architecture/frontend-code-quality/SKILL.md:3` — "description: Base frontend code quality rules — component size, state, a11y, performance, type safety." = **89 caracteres**, dentro do orçamento de 95.
- **Nota:** o gate associado existe em `helpers/agent-lint.sh:92` (`SKILL_DESC_LIMIT=95`) com `SKILL_DESC_STRICT=true` em `:98` — divergência com `CLAUDE.md`, já registrada no conjunto aberto.

### `token-notifier-loads-45-tips-3-languages-emits-1-per-day-99pct-waste`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `6919564` (criou `tips/tips.{en,pt-BR,es}.txt`, −76 no notifier)
- **Evidência no HEAD:** `scripts/hooks/stop/_disabled-04-notifier.sh:34` — "Rotating tips live in locale-keyed data files next to this script"; `:293-297` resolve um único `TIP_FILE`.
- **Nota:** o script foi **renomeado** para `_disabled-04-notifier.sh` em `ba39c86` — desativação deliberada do módulo, não reversão da extração.

### `token-sonarqube-detection-block-redundant`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** LOW-MEDIUM
- **Marca verificada:** 🟡 Parcialmente feito
- **Commit examinado:** `b4e219f` + `519ca7e`
- **Evidência no HEAD:** 10 das 11 cópias saíram (`backend-developer.md:86`, `qa-specialist.md:52`, `backend-reviewer.md:145`, `frontend-reviewer.md:135`, `security-specialist.md:103`, `code-reviewer.md:103`, `backend-test-specialist.md:104` todos deferem). **Sobra uma:** `agents/devops-specialist.md:81` — "| `sonar-project.properties`, `.sonarcloud.properties`, `sonarqube` service in compose, or `SONAR_TOKEN` env var | `skills/devops/sonarqube/SKILL.md` |".
- **Nota:** essa linha é subconjunto de 4 dos 6 sinais da tabela canônica (`skills/devops/sonarqube/SKILL.md:12-19`) — exatamente o padrão que `CLAUDE.md:160` proíbe ("Route to the table; never restate a subset of the signals").

### `token-rollback-sh-65-lines-duplicates-installer-download-from-update-sh`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** LOW-MEDIUM · **Verificada:** ✅ Feito
- **Commit examinado:** `2e12335`
- **Evidência no HEAD:** `scripts/rollback.sh:22` — "live in `scripts/lib/installer-fetch.sh`, shared with `update.sh`." e `:24`; par simétrico em `scripts/update.sh:44-46`. O bloco `if command -v curl … elif command -v wget …` não existe mais.
- **Nota:** o achado pedia `install-fetch.sh`; o entregue é `installer-fetch.sh` — mesma função, nome já canonizado no `CLAUDE.md`.

### `token-skill-loads-via-table-vs-prose-inconsistent`

- **Marca original:** ✅ Executed 2026-07-31 (já 🟡 em 07-31) · **Severidade:** LOW
- **Marca verificada:** 🟡 Parcialmente feito — **inalterado desde a reverificação anterior**
- **Commit examinado:** `b4e219f` (migrou `security-specialist` e `code-reviewer` para tabela)
- **Evidência no HEAD:** `agents/frontend-reviewer.md` segue **0 linhas de tabela contra 17 referências em prosa** — ex.: `:33` "- Load `skills/shared/comments-policy/SKILL.md` — applies when reviewing comments in the diff". Nenhuma regra de formato foi escrita; `CLAUDE.md:539` instrui o oposto.

### `token-dedup-step-reads-full-676-line-prose-index-md-extract-machine-readable-list`

- **Marca original:** ✅ Executed 2026-07-31 · **Severidade:** LOW · **Verificada:** ✅ Feito
- **Commit examinado:** `3f94594` (criou `_prompt-auditoria.md` já com o protocolo baseado em grep) + `7736e20`
- **Evidência no HEAD:** `docs/reports/_prompt-auditoria.md:195` e `:200`, com a instrução em `:202` "aplique a porta 3 **somente contra essas linhas**". A FASE 0 lê `sed -n '1,120p'` + `grep -cE`, nunca o arquivo inteiro. `_index.md` caiu de 850 para 340 linhas.
- **Nota:** o sidecar `_fingerprints.txt` nomeado no slug **não** foi criado — a remediação atingiu o mesmo objetivo por leitura escopada via grep. Divergência de meio, não de resultado.

---

## Correções de marcação a aplicar no `_index.md` (Fase 1)

| Linha | Fingerprint | Correção |
|---|---|---|
| 138 | `flow-size-limits-sh-ci-only-warn-only-not-in-stop-dispatcher…` | 🟡 2ª confirmação — CI bloqueante, mas `scripts/hooks/stop/` segue sem checagem de tamanho |
| 148 | `flow-telemetry-pre-tool-use-02-runs-on-every-tool-call…` | 🟢 com sha corrigido — `f1ca129` (2026-08-06), não `156771b` |
| 192 | `agent-frontend-developer-body-92-102-data-fetching…` | 🟡 — `:96` mantém TanStack/SWR nominais e o "React/Vue ecosystem"; `:91` mantém "e.g. React `useState`" |
| 223 | `token-claude-md-426-lines-still-monolithic…` | 🔴 2ª confirmação — 586 linhas, tabela de comandos inline em `:211` |
| 225 | `token-token-efficiency-skill-itself-154-lines-eager-loaded…` | 🔴 — eager em 18/18, skill cresceu para 160 linhas |
| 240 | `token-sonarqube-detection-block-redundant` | 🟡 — resta `devops-specialist.md:81` restatando 4 dos 6 sinais |
| 247 | `token-skill-loads-via-table-vs-prose-inconsistent` | 🟡 — quadro inalterado; `frontend-reviewer` segue 0 tabela / 17 prosa |

---

## Fase 1b — Validade dos 25 achados abertos

**Mortalidade: 0 de 25 (0%)** — 0 🟢 · 0 ⚰️. Todos foram relocalizados por símbolo e reproduzem no
HEAD `c03f898`. Nenhuma linha do `_index.md` precisa de marcador nesta fase.

**Três achados degradaram materialmente** desde a última reverificação, e essa é a informação mais
útil da fase: as medições que os sustentam pioraram sem que ninguém tivesse decidido nada.

| Fingerprint | Medição na abertura | Reverificação anterior | HEAD `c03f898` |
|---|---|---|---|
| `token-changelog-already-growing-and-not-extracted-by-release` | 441 linhas | 441 | **962** (+118%) |
| `flow-session-start-118-lines-monolithic…` | 118 linhas | 174 | **306** (+76%) |
| `token-install-sh-503-lines-largest-single-script…` | 503 linhas | 947 | **1086** (+15%) |
| `token-interaction-patterns-209-lines-loaded-unconditionally…` | 24 comandos + 2 agentes | 26 pontos | **33 pontos** (≈5.610 linhas agregadas, era ≈4.130) |

### Itens com evidência relocalizada

- `flow-session-start-118-lines-monolithic…` — `scripts/hooks/session-start.sh` é arquivo único de **306 linhas**; `ls scripts/hooks/` não mostra diretório `session-start/`. A assimetria com `stop.sh`/`pre-tool-use.sh` (ambos com subdiretório) só aumentou.
- `flow-conventional-commits-validate-script-no-husky-or-commit-msg-hook-registration` — `grep -n "commit-msg\|husky\|lefthook" scripts/install.sh` → zero hits; `scripts/validate-commit-msg.sh` existe e nunca é registrado.
- `flow-hook-events-only-pretooluse-and-stop` — `scripts/install.sh:672-675` registra 4 eventos (PreToolUse, Stop, SessionStart, PreCompact). `UserPromptSubmit`, `SubagentStop` e `Notification` seguem sem registro. O título do fingerprint já está desatualizado, mas o achado permanece.
- `skill-no-skill-uses-scripts-subdir-pattern-agentskills-io` — `find skills -type d -name scripts | wc -l` → **0**, contra 151 SKILL.md. Adoção de `references/` subiu de 20 para 22 diretórios.
- `skill-adr-coverage-only-architect` — `agents/software-architect.md:39` é o **único** hit de `shared/adr` em `agents/`.
- `token-readme-228-each-after-extraction-still-2-files-no-cross-link-tagging` — `wc -l` → **301 / 301**; `grep -c "@section"` → 0 em ambos. A paridade exata confirma duas fontes full-length espelhadas.
- `token-skills-shared-token-efficiency-not-quantified…` — a linha citada migrou de 218 para **`CLAUDE.md:177`**. `skills/shared/token-efficiency/` contém só `SKILL.md` e `strategies.md` — nenhum baseline, métrica ou loop de feedback.
- `agent-frontend-test-specialist-sonarqube-coverage-block-hardcodes-jest-vitest…` — `agents/frontend-test-specialist.md:143` — "`jest --coverage --coverageReporters=lcov`"; `:146` vitest; `:151` `sonar.javascript.lcov.reportPaths`. Bloco intacto.
- `agent-frontend-developer-description-frontmatter-enumerates-eight-frameworks…` — `agents/frontend-developer.md:3` — "Works in both decoupled SPAs (React, Vue, Svelte, Angular) and server-rendered templates (Blade, Twig, ERB, Jinja)."
- `agent-devops-specialist-core-expertise-declares-primary-docker…` — `:46` "**Primary**: Docker" contra `:131` "Never name a specific product as the answer". A contradição está a **85** linhas de distância, não 86.
- `flow-audit-command-devops-analysis-prompt-names-redis-cdn-docker…` — `commands/audit.md:126` e `:128`. (`:54` também cita Docker, mas ali é a referência legítima ao `docker-isolation` do worktree.)
- `docs-sync-claude-md-102-states-skill-desc-strict-false…` — `CLAUDE.md:129` diz "non-blocking warning today (`SKILL_DESC_STRICT=false`)" contra `helpers/agent-lint.sh:98` — "`SKILL_DESC_STRICT=true`". Ambas migraram de linha; a contradição é literal e é o **HIGH mais antigo em aberto**.
- `docs-sync-claude-md-173-says-all-devteam-commands-load-current-context…` — `CLAUDE.md:202` ("All `/devteam:*` commands") contra `:250` ("These **six** are the complete list"). A lista de exceções cresceu de quatro para seis, tornando a afirmação "All" ainda mais falsa.
- `docs-sync-reports-index-md-99-legend-comment-claims-all-131-entries-unmarked…` — `docs/reports/_index.md:102` — "All 131 entries below are unmarked". O banco tem hoje **150** fingerprints, dos quais **124 carregam marcador**. O comentário erra o total e a premissa, e ancora num HEAD (`7f85ed7`) de duas semanas atrás.
- `flow-pre-tool-use-02b-telemetry-reads-devteam-hook-payload-branch…` — `02b-telemetry.sh:22` lê `DEVTEAM_HOOK_PAYLOAD` contra `pre-tool-use.sh:31`, que entrega por **stdin**. Só `stop.sh:17` exporta a variável. Ramo morto em 100% das invocações PreToolUse.
- `skill-shared-migration-v1-to-v2-437-lines…` — **438 linhas**, ainda a maior skill do repo (2ª é `architecture/orchestration` com 377). Um carregador, zero `references/`, zero critério de aposentadoria.
- `flow-relayout-design-discovery-names-storybook-tailwind` — `commands/relayout.md:32` inalterada; a seção continua sendo de descoberta obrigatória.
- `flow-learn-run-marker-records-commit-time-not-run-time` — `commands/learn.md:166` inalterada; nenhum commit tocou o arquivo desde `4734882`, que introduziu o defeito.
- `gov-repo-gitignore-omits-three-installer-written-entries` — `.gitignore:9` tem `.dev-team-agents/user-data/` como **única** das entradas. `install.sh:774-779` hoje escreve **seis**; placar atualizado: **1 de 6**.

### O delta não fechou o que se esperava que fechasse

- **`c03f898` não fechou nenhum dos dois achados de `02c-full-suite-guard.sh`.** O commit adicionou os padrões `make`/`composer` (`:72-89`) sem tocar o `sed` guloso de `:22` nem o comentário de `:18`. Reproduzido de novo no HEAD: o payload `{"command":"npm test","description":"run the suite for src/foo.test.ts"}` produz saída **vazia** (nudge suprimido), enquanto o payload idêntico com `"description":"run"` emite o nudge. O commit na verdade **amplia** a superfície do bug: `make`/`composer`/`TESTPATH=`/`FILTER=` são termos ainda mais prováveis de aparecer numa `description` em prosa.
- **`21fceb4` não toca o conjunto aberto** — nenhum dos 25 fingerprints tem `skills/architecture/orchestration/SKILL.md` ou `skills/shared/scoped-test-execution/SKILL.md` como alvo.
- **Um gate novo passou ao lado do achado que deveria cobrir.** `helpers/preferences-sync-lint.sh` (`26520b9`) valida os dois espelhos de documentação de `preferences-defaults.json` — `MIRRORS=("CLAUDE-md/preferences.md" "skills/shared/user-preferences/SKILL.md")` — e **exclui** o heredoc de `install.sh`, que é exatamente onde a drift de `auto_learn_before_commit` vive. Rodando no HEAD: "preferences-sync-lint: clean ✓ (2 mirrors checked)", exit 0, com o defeito ativo.
