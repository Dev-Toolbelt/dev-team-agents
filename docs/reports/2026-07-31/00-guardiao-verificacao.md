# Fase 1 e 1b — Verificação Guardiã

**Data:** 2026-07-31 · **Baseline:** `HEAD` = `f54569a` · **Baseline anterior:** `7f85ed7`

---

## Método

O banco registrava **121 itens verificáveis** (120 ✅ Executed + 1 ⚠️ Partial), todos marcados em
**2026-07-31** por um único pass de execução — throughput declarado de 92% em um dia. A janela de
verificação é portanto `7f85ed7..HEAD`: **15 commits**, 268 arquivos, +6.801/−21.927.

Como 121 > 60, aplicou-se a regra de amostragem do prompt:

| Estrato | População | Verificados | Critério |
|---|---|---|---|
| HIGH + MEDIUM-HIGH | 18 | **18** | integral, obrigatório |
| MEDIUM / LOW-MEDIUM / LOW | 103 | **31** | amostra aleatória de 30%, semente fixa `20260731` |
| **Total** | **121** | **49** | **cobertura 40%** |

Cada item foi reconstruído a partir do git (`git log`/`git show` na janela + `git show <ref>:<path>`
para o estado anterior), não a partir do enunciado do problema, e depois confirmado no `HEAD`.

## Placar

| Marca | Tier 1 (18) | Tier 2 (31) | Total (49) | % |
|---|---|---|---|---|
| ✅ Feito | 16 | 25 | **41** | 84% |
| 🟡 Parcialmente feito | 1 | 2 | **3** | 6% |
| 🔴 Não feito | 1 | 4 | **5** | **10%** |

**Escalonamento: não disparado.** A taxa de 🔴 é 10,2%, abaixo do gatilho de 15%. O pass de execução
de 2026-07-31 é, no geral, honesto: 84% das marcações se confirmam com commit na janela e mudança
presente no HEAD. Os 5 🔴 e 3 🟡 abaixo são as exceções, e três deles têm a mesma causa — a marcação
foi aplicada a um *tema* cujo sub-escopo principal não foi tocado.

---

## Tier 1 — HIGH e MEDIUM-HIGH (18 de 18)

### 🔴 Não feito

#### `token-claude-md-426-lines-still-monolithic-three-extractable-blocks-…`

- **Marca original:** ✅ Executed: 2026-07-31 · **Verificado:** 🔴
- **Commit examinado:** `bbb311a`, `7736e20` (ambos tocam `CLAUDE.md`)
- **Evidência:** `CLAUDE.md` passou de **425 linhas** (`git show 7f85ed7:CLAUDE.md | wc -l`) para
  **549** — cresceu 29% (550 no `HEAD` atual, `48b9307`). Os três blocos que o achado apontava como
  extraíveis continuam inline:
  `CLAUDE.md:176` — "#### User-Invocable Commands (`commands/*.md`)";
  `CLAUDE.md:430` — "### Stop Hook Sub-script Convention";
  `CLAUDE.md:473` — "### Hook Files Map".
  `git diff --name-status 7f85ed7..HEAD -- CLAUDE-md/` retorna apenas `M` para os três arquivos
  pré-existentes — **nenhum arquivo novo foi criado em `CLAUDE-md/`**.
- **Por que a marcação está errada:** o commit da janela tocou o alvo, mas para **adicionar** 180
  linhas de conteúdo, não para extrair. O que existe hoje no lugar da extração é um *gate de
  tamanho* (`helpers/size-limits.sh:76-84`, avisa em 600, falha em 700) — um instrumento diferente,
  que mede o problema sem resolvê-lo. Com 549 linhas, o arquivo está a 51 linhas do aviso.

### 🟡 Parcialmente feito

#### `flow-size-limits-sh-ci-only-warn-only-not-in-stop-dispatcher-asymmetric-with-agent-lint-200-cap-never-blocking`

- **Marca original:** ✅ Executed: 2026-07-31 · **Verificado:** 🟡
- **Commit examinado:** `c7535b7`, `7736e20`
- **Entregue:** o gate foi promovido a bloqueante —
  `.github/scripts/ci/01-lint.sh:88` — `blocking "size-limits" bash helpers/size-limits.sh`, com o
  comentário `# PROMOTED 2026-07-31` na linha 84. E as violações sumiram: o maior agente hoje é
  `agents/security-specialist.md` com **198** linhas (limite 200), o maior comando
  `commands/learn.md` com **194**.
- **Falta exatamente isto:** o sub-escopo *"not in stop dispatcher"*. `ls scripts/hooks/stop/` não
  tem nenhum sub-script de size-limits, e `03-agent-lint.sh` chama apenas `helpers/agent-lint.sh`,
  que não faz contagem de linhas (`grep -n 'wc -l\|LIMIT' helpers/agent-lint.sh` só retorna
  `SKILL_DESC_LIMIT=95`). A assimetria com `agent-lint` — que **tem** equivalente no Stop — persiste:
  quem estoura o limite descobre no CI, não ao fim da sessão em que estourou.

### ✅ Feito (16)

| Fingerprint | Commit | Evidência no HEAD |
|---|---|---|
| `ref-docs-agents-md-model-column-wrong-…` | `bbb311a` | `docs/agents.md:9` — a coluna virou `| Agent | Role | Phase | Tier |`; `:29` — "**Tier is the source of truth, not the model name.**" O erro factual foi eliminado removendo o campo que o produzia |
| `ref-claude-md-183-code-reviewer-roles-…` | `bbb311a` | `CLAUDE.md:216` — "It then proceeds as `backend-reviewer` (`BACKEND`), as `frontend-reviewer` (`FRONTEND`)" |
| `ref-two-helpers-dirs-naming-collision-…` | `bbb311a` | `CLAUDE.md:311` — "**Two `helpers` directories — do not confuse them:**", com tabela em `:316` documentando `scripts/helpers/` como shipped |
| `ref-claude-md-file-structure-omits-helpers-and-privacy-and-claude-md-folder` | `bbb311a` | `CLAUDE.md:254` (`CLAUDE-md/`), `:261` (`helpers/`), `:306` (`PRIVACY.md`) presentes no bloco File Structure |
| `ref-telemetry-honors-pref-but-pref-defaults-true-…` | `2e12335`, `7736e20` | `scripts/lib/preferences-defaults.json:13` — `"telemetry": false`; `scripts/lib/telemetry-guard.sh` centraliza o gate e **falha fechado** por design documentado |
| `flow-helpers-archive-index-sh-orphan-of-hook-…` | `c7535b7` | `scripts/hooks/stop/99b-archive-index.sh` existe, referencia `helpers/archive-index.sh:21` e usa stamp diário em `:27` |
| `auto-update-no-integrity-check` | `2e12335` | `scripts/lib/installer-fetch.sh` — `dta_sha256()` (`:72`), `dta_verify_installer()` (`:144`); consumido por `scripts/update.sh:87`, `rollback.sh:18`, `hooks/lib/update-check.sh:253` |
| `gov-telemetry-send-sh-posthog-key-comments-self-contradict-…` | `2e12335`, `6919564` | `scripts/helpers/telemetry-send.sh:23-31` — comentário único e coerente; **nenhum TODO** e nenhuma contradição "replace before release" restante |
| `agent-security-specialist-body-130-153-hardcodes-per-language-sast-…` | `b4e219f` | `grep -i 'bandit\|composer\|trivy\|pip-audit' agents/security-specialist.md` → **0 hits** |
| `agent-backend-developer-integration-awareness-…` | `b4e219f` | `agents/backend-developer.md:63-77` — "Integration Awareness" virou tabela `Detection signal → Skill to load`; nenhuma regra de provider inline |
| `agent-frontend-test-specialist-107-122-hardcodes-react-renderhook-…` | `b4e219f` | `agents/frontend-test-specialist.md:96` — delega para `skills/testing/frontend-hook-tests/SKILL.md`; receitas removidas do corpo |
| `agent-devops-specialist-decision-framework-and-anti-overengineering-…` | `b4e219f` | `agents/devops-specialist.md:123` — delega para `skills/devops/infrastructure-sizing/SKILL.md`; `:125` — "Never name a specific product as the answer". Seção "Decision Framework" não existe mais |
| `agent-code-reviewer-router-has-ten-structural-review-categories-…` | `b4e219f` | As dez seções `### 1. Correctness` … `### 10. Type Safety` (presentes em `7f85ed7:agents/code-reviewer.md:62-132`) foram substituídas por `## Router Responsibilities` com 3 sub-seções. 233 → 185 linhas |
| `agent-backend-test-specialist-body-114-120-hardcodes-per-language-coverage-…` | `b4e219f` | `grep -i 'clover\|jacoco\|simplecov\|pytest' agents/backend-test-specialist.md` → **0 hits** |
| `skill-architecture-awareness-shared-behavioral-skill-enumerates-react-vue-…` | `519ca7e` | `grep -i 'react\|vue\|svelte\|angular\|blade\|twig\|laravel\|django\|rails' skills/shared/architecture-awareness/SKILL.md` → **0 hits** |
| `token-foundational-rule-424-lines-across-17-agents` | `b4e219f` | O bloco virou delegação de uma linha em todos os 17: `agents/backend-developer.md:15` e `agents/software-architect.md:3` (da seção) — "Load `skills/shared/project-context/SKILL.md` — covers README, CLAUDE.md, AGENTS.md, …". O total de 384 → **328** linhas é agora conteúdo *role-specific* (tabelas de load condicional), não duplicação |

---

## Tier 2 — amostra aleatória (31 de 103)

### 🔴 Não feito (4)

#### `ref-release-prep-skill-exists-twice-shared-88-lines-shipped-vs-claude-skills-181-lines-dev-divergent-content-no-sync-rule`

- **Marca original:** ✅ Executed: 2026-07-31 · **Verificado:** 🔴
- **Commit examinado:** `7736e20` — o único da janela a tocar qualquer um dos dois arquivos
- **Evidência:** `git diff --stat 7f85ed7..HEAD -- skills/shared/release-prep/SKILL.md
  .claude/skills/release-prep/SKILL.md` → **`1 file changed, 1 insertion(+), 1 deletion(-)`**. A
  única linha alterada foi a `description:` do arquivo shipped, para caber no orçamento de 95
  chars — trabalho de outro achado. As duas cópias continuam lá e continuam divergentes:
  `skills/shared/release-prep/SKILL.md` = **88** linhas, `description: Pre-release checklist for
  dev-team-agents — semver bump, tagging, rollback.`;
  `.claude/skills/release-prep/SKILL.md` = **181** linhas, `description: Guides the pre-release
  process for the dev-team-agents repository. …`
- **Por que a marcação está errada:** `grep -rn 'release-prep' CLAUDE.md CONTRIBUTING.md .github/
  helpers/ scripts/` → **0 hits**. Nem reconciliação, nem regra de sync, nem sequer registro do
  desvio. O achado ("no sync rule") está intocado.

#### `flow-stop-no-zombie-state-cleanup-discovery-lock-and-worktree-session-persist-across-sessions`

- **Marca original:** ✅ Executed: 2026-07-31 · **Verificado:** 🔴
- **Evidência:** `grep -rn 'worktree-session\|discovery-lock\|zombie' scripts/hooks/` → nenhum hit
  em `stop/` nem em `stop.sh`. O único `rm` no dispatcher é
  `scripts/hooks/stop.sh:18` — `trap 'rm -f "$HOOK_TMP"' EXIT`, que limpa o próprio tempfile do
  payload, não estado de sessão. O tier `99-` (cleanup) tem dois scripts —
  `99-graphify-refresh.sh` e `99b-archive-index.sh` — e nenhum toca em estado zumbi.
- **Estado do alvo no HEAD:** `.dev-team-agents/.worktree-session` continua sendo escrito por
  `commands/audit.md:55` e `commands/refactor.md:25` e lido por `skills/shared/worktree/SKILL.md:18`
  sem nenhuma expiração; `.claude/.discovery-lock` é criado em
  `skills/shared/discovery-mode/SKILL.md:117` e a única limpeza descrita (`:123`) é *dentro* da
  própria skill, dependente de outro agente rodar discovery depois.
- **Por que a marcação está errada:** nenhum commit da janela tocou o alvo.

#### `flow-telemetry-pre-tool-use-02-runs-on-every-tool-call-without-batching-or-deduplication-burns-200ms-per-burst-session`

- **Marca original:** ✅ Executed: 2026-07-31 · **Verificado:** 🔴
- **Commit examinado:** `cc28900`, `2e12335`
- **Evidência:** o diff do arquivo na janela é **um rename** (`02-telemetry.sh` → `02b-telemetry.sh`)
  mais a troca do guard inline por `scripts/lib/telemetry-guard.sh`. A estrutura de execução é
  idêntica ao estado anterior: `scripts/hooks/pre-tool-use/02b-telemetry.sh:21` — `_telemetry_enabled
  || exit 0` (que forka `python3` dentro do guard), depois `:35` — segundo fork de `python3` para
  extrair `tool_name`, e só então `:42` — o `case "$TOOL_NAME"` que é o filtro. Para `Bash`, um
  **terceiro** fork em `:50`. Nenhum batching, nenhuma deduplicação, nenhum pré-filtro barato.
- **Por que a marcação está errada:** a mudança que houve pertence a `auto-update-no-integrity-check`
  / `ref-telemetry-honors-pref-…` (consentimento), não a este achado. O efeito colateral é real —
  com `telemetry: false` por padrão, o caminho caro agora só roda em instalação opt-in — mas isso
  reduz a *população* afetada, não o custo por tool call de quem optou.

#### `flow-cli-commit-validate-msg-script-skipped-silently-when-missing-no-instructive-error`

- **Marca original:** ✅ Executed: 2026-07-31 · **Verificado:** 🔴
- **Evidência:** o bloco é **byte-idêntico** ao de `7f85ed7`.
  `commands/commit.md:110-112` — `if [ -f ".dev-team-agents/scripts/validate-commit-msg.sh" ]; then
  … fi`, sem `else`. `commands/commit.md:115` continua com a mesma frase.
- **O que mudou no arquivo:** apenas `:119`, que trocou o prompt `(a) fix and re-stage, (b) commit
  anyway, (c) abort` por `AskUserQuestion` — trabalho da Quiz-first Rule, achado distinto.
- **Por que a marcação está errada:** nenhum commit da janela tocou o alvo do achado.

### 🟡 Parcialmente feito (2)

#### `ref-notification-system-content-triplicated-across-04-notifier-sh-notifier-skill-and-claude-md-notifications-md-…`

- **Marca original:** ✅ Executed: 2026-07-31 · **Verificado:** 🟡
- **Entregue:** o drift da tabela foi corrigido — `CLAUDE-md/notifications.md:63` agora traz
  `| 05- | External reporting (telemetry) | 05-telemetry.sh |`. E os 15 tips saíram do bash: o hook
  lê arquivos de dados (`scripts/hooks/stop/04-notifier.sh:27` — `TIPS_DIR=…/tips`; `:185-189`
  seleciona `tips.pt-BR.txt` / `tips.es.txt` / `tips.en.txt`).
- **Falta exatamente isto:** a terceira cópia. `skills/shared/notifier/SKILL.md:113` ainda declara
  o índice — "Index: `(day_of_month - 1) % 15`" — e `:115-129` ainda lista **os 15 tips na íntegra**.
  O tip 7 da skill ("Run a health check occasionally: *"Run a health check on this project"* — it
  auto-fixes stale hooks, broken symlinks, and outdated preferences.") é o mesmo texto de
  `scripts/hooks/stop/tips/tips.en.txt:8`. A extração criou um novo lugar para o dado sem apagar o
  antigo: a duplicação saiu de `hook ↔ skill` e virou `hook ↔ tips/*.txt ↔ skill`.

#### `token-skill-loads-via-table-vs-prose-inconsistent`

- **Marca original:** ✅ Executed: 2026-07-31 · **Verificado:** 🟡
- **Entregue:** dois dos três agentes "all-prose" citados na evidência de origem migraram para
  tabela — `agents/security-specialist.md` tem hoje 10 linhas de tabela de skill-load (era 0/8) e
  `agents/code-reviewer.md` tem 7 (era 0/7).
- **Falta exatamente isto:** o terceiro, `agents/frontend-reviewer.md`, continua **0 linhas de
  tabela para 15 referências a `SKILL.md`** — inteiramente em prosa. E, mais relevante, **nenhuma
  regra foi escrita**: `grep -i 'conditional skill load\|skill-loading pattern' CLAUDE.md` retorna
  só `CLAUDE.md:521`, que instrui explicitamente o contrário — "following that agent's existing
  skill-loading pattern (full path or backtick name form, **whichever is already used**)". As duas
  convenções seguem coexistindo por escrito. Cinco agentes têm 0 linhas de tabela hoje
  (`product-analyst`, `frontend-test-specialist`, `frontend-reviewer`, `backend-test-specialist`,
  `backend-reviewer`).

### ✅ Feito (25)

| Fingerprint | Evidência no HEAD |
|---|---|
| `agent-backend-developer-composition-root-rule-1-line-vs-frontend-developer-12-lines-…` | Assimetria resolvida nos dois sentidos: `agents/backend-developer.md:89-97` ganhou seção `## Composition Root` própria (antes era 1 bullet em `7f85ed7:…:202`); `agents/frontend-developer.md:131-133` foi condensada. Ambas delegam para a mesma seção da skill |
| `agent-frontend-developer-security-section-134-139-hardcodes-dangerouslysetinnerhtml-…` | `agents/frontend-developer.md:124` — a regra virou "**Raw HTML injection**: any API the framework offers for bypassing escaping (e.g. …)"; `:126` — "only variables carrying the build tool's public prefix (e.g. `VITE_*`, `NEXT_PUBLIC_*`)". Antes os nomes eram o *rótulo* do bullet; agora são exemplo de uma regra agnóstica |
| `agent-mobile-developer-description-frontmatter-enumerates-five-stacks-…` | `agents/mobile-developer.md:3` — "whether the project is native or cross-platform. Detects the project's mobile stack". Nenhum stack nomeado |
| `auto-install-no-rollback-on-second-mv-failure` | `scripts/install.sh:102` — `trap _cleanup EXIT`; `:81-90` restaura `OLD_DIR` → `INSTALL_DIR` e imprime o comando manual se o restore falhar; `:235-237` trata `mv` cross-filesystem com fallback para cópia |
| `flow-ci-triggers-both-push-and-pull-request-on-all-branches-…` | `.github/workflows/ci.yml:16-20` — `push: branches: [main], tags: ["**"]`; `:25-27` — bloco `concurrency` com `cancel-in-progress: ${{ github.ref_type != 'tag' }}`. O comentário `:4-14` documenta por que concurrency sozinha não resolvia |
| `flow-pre-tool-use-01-check-updates-195-lines-3rd-largest-script-no-fragmentation` | `scripts/hooks/pre-tool-use/01-check-updates.sh` = **78** linhas (orquestrador fino) + `scripts/hooks/lib/update-check.sh` = 260 (motor) |
| `flow-readme-sync-ci-hardcodes-three-doc-pairs-…` | `.github/scripts/ci/02-readme-sync.sh:13-14` — "Pairs are DISCOVERED, not hardcoded: every `*.pt-BR.md` in the tree must have an EN counterpart …, or this script fails" |
| `flow-setup-slash-command` | `commands/setup.md` existe; `CLAUDE.md` registra `/devteam:setup` na tabela de comandos |
| `flow-stop-dispatcher-computes-no-changes-once-but-02-and-03-each-recompute-…` | Os quatro sub-scripts consomem o conjunto compartilhado: `02-orphan-skill-scan.sh:14`, `02b-orphan-template-scan.sh:16`, `03-agent-lint.sh:14`, `03b-fingerprint-uniqueness.sh:22` — "Consumes DEVTEAM_TOUCHED_PATHS computed once by the dispatcher" |
| `flow-telemetry-stop-05-runs-after-04-notifier-but-no-fast-path-skip-when-DEVTEAM_NO_CHANGES-is-1` | `scripts/hooks/stop/05-telemetry.sh:32` — `if [ "${DEVTEAM_NO_CHANGES:-0}" = "1" ]; then` |
| `gov-codeowners-coverage-gaps-helpers-readme-pair-canonical-docs-and-skill-domains-unowned-…` | `.github/CODEOWNERS:14` — catch-all `*  @Dev-Toolbelt/maintainers` colocado primeiro deliberadamente (`:5-7` explica a ordenação); `helpers/` explicitamente coberto com justificativa; os 10 domínios de skill listados |
| `ref-agent-creator-location` | `CLAUDE.md:166` — antes dizia "(global Claude skill — **not in this repo**)", o que era falso. Hoje: "tracked in this repo, but `.claude/` is stripped from the package by `scripts/lib/strip-tarball.sh`, so it never reaches an installed project. Available to contributors working inside this repo only" |
| `ref-claude-md-file-structure-skills-subtree-omits-database-mobile-skill-creator-…` | `CLAUDE.md:242-253` lista os 12 domínios; `ls skills/` retorna exatamente esses 12 |
| `ref-skill-ui-libraries-shadcn-frontmatter-name-…-no-validator-enforces-name-equals-dir` | `skills/ui-libraries/shadcn/SKILL.md:2` — `name: shadcn`; e o validador existe: `helpers/agent-lint.sh:150-154` — "name must equal the directory basename" |
| `skill-add-load-testing` | `skills/testing/load-testing/SKILL.md` criado — "Load testing — smoke/load/stress/soak/spike profiles, SLO thresholds, tooling" |
| `skill-comments-policy-missing-in-non-coding-agents` | 15 de 17 agentes referenciam `comments-policy`; os 2 ausentes (`setup-assistant`, `technical-writer`) não são os coding agents write-capable que o achado citava |
| `skill-integrations-gotrue-225-lines-…-no-references-extraction` | `skills/integrations/gotrue/SKILL.md` = **73** linhas + `references/` |
| `skill-mobile-ios-and-android-wrapper-pattern-first-instruction-is-load-ios-hig-…` | O wrapper virou partição explícita: `skills/mobile/ios/SKILL.md:8` — "engineering half"; `:10` — "The **design** half lives in … Load it **only when the task touches UI**". Mesma estrutura em `skills/mobile/android/SKILL.md:8-10`. O gate deixou de ser prosa e virou condição declarada |
| `skill-security-checklist-eager-loaded-by-both-security-specialist-and-qa-specialist-…` | Fronteira particionada: `agents/security-specialist.md:32` — "security-audit column only, see below"; `agents/qa-specialist.md:39` — load condicional a "changeset touches auth, access control, input validation, or API behavior" |
| `token-backlog-template-skill-171-lines-unconditionally-loaded-…` | `agents/product-analyst.md:25` — "**Conditional load — only when you are about to produce backlog output** … A discovery, interrogation, or question-round turn that writes no backlog file does **not** load it" |
| `token-dedup-step-reads-full-676-line-prose-index-md-every-run-…` | Resolvido por dois lados: `docs/reports/_index.md` caiu de ~850 para **250** linhas, e o passo de dedup virou grep dirigido — `docs/reports/_prompt-auditoria.md:195` (`grep -F "<slug>"`) e `:201` (pré-filtro por basename do alvo). O custo era ler prosa inteira; hoje não se lê |
| `token-frontend-code-quality-description-288-chars-…` | `description` hoje tem **91** chars — "Base frontend code quality rules — component size, state, a11y, performance, type safety." Sem cauda meta-narrativa. O gate correspondente virou bloqueante (`SKILL_DESC_STRICT=true`) |
| `token-notifier-loads-45-tips-3-languages-emits-1-per-day-99pct-waste` | `scripts/hooks/stop/tips/` — 3 arquivos de 15 linhas; `04-notifier.sh:185-189` lê **um** deles, e só depois do gate diário |
| `token-plan-mode-skill-131-lines-loaded-by-7-agents-unconditionally` | 199 → **151** linhas; o formato saiu da skill: `skills/shared/plan-mode/SKILL.md:39` — "Load `.dev-team-agents/templates/plan-template.md` … That file is the canonical" |
| `token-project-rules-override-prose-duplicate` | A frase sumiu dos 14 agentes. Os hits residuais de `override` são o Immutability Warning (`agents/backend-developer.md:167`) e texto não relacionado (`agents/code-reviewer.md:29`) |

---

## Fase 1b — Validade dos 10 achados abertos

Todos os 10 foram checados contra o `HEAD`.

| Fingerprint | Estado | Evidência |
|---|---|---|
| `flow-session-start-118-lines-monolithic-…` | **ainda reproduz** | `scripts/hooks/session-start.sh` = **174** linhas, sem sub-diretório |
| `flow-conventional-commits-validate-script-no-husky-or-commit-msg-hook-registration` | **ainda reproduz** | `grep -n 'husky\|commit-msg\|lefthook' scripts/install.sh` → 0 hits |
| `flow-hook-events-only-pretooluse-and-stop` | **ainda reproduz** (escopo menor) | `scripts/install.sh:569-572` registra 4 eventos — `PreToolUse`, `Stop`, `SessionStart`, `PreCompact`. Os demais (`PostToolUse`, `SubagentStop`, `UserPromptSubmit`, `SessionEnd`, `Notification`) seguem não registrados |
| `gov-installer-rigor-asymmetry` | **ainda reproduz — piorou** | O instalador registra 4 eventos; o próprio repo dogfooda **1**: `python3 -c "…json.load(open('.claude/settings.json'))…"` → `['Stop']`. A assimetria era 4:1 no enunciado e continua 4:1, mas agora com 4 eventos reais em jogo |
| `skill-no-skill-uses-scripts-subdir-pattern-agentskills-io` | **ainda reproduz** | `find skills -type d -name scripts` → vazio |
| `skill-adr-coverage-only-architect` | **ainda reproduz** | `grep -rln 'shared/adr' agents/ commands/` → `agents/software-architect.md` (1 agente) e `commands/learn.md` |
| `token-install-sh-503-lines-…` | **ainda reproduz — piorou** | `scripts/install.sh` = **947** linhas. O slug registra 503, a nota do banco registra 803. Cresceu 18% desde a última medição e 88% desde o slug |
| `token-changelog-already-growing-and-not-extracted-by-release` | **ainda reproduz — piorou** | `CHANGELOG.md` = **546** linhas (nota do banco: 441). Nenhum arquivo de arquivo em `docs/` |
| `token-readme-228-each-after-extraction-still-2-files-no-cross-link-tagging` | **ainda reproduz — piorou** | `README.md` e `README.pt-BR.md` = **338** linhas cada (nota do banco: 228). Âncoras de seção: **0** |
| `token-skills-shared-token-efficiency-not-quantified-…` | **ainda reproduz** | `grep -i 'baseline\|measure\|metric\|roi' skills/shared/token-efficiency/SKILL.md` → 0 hits |

**Mortalidade da Fase 1b: 0% (0 de 10).** Nenhum achado aberto foi resolvido de passagem e nenhum
alvo desapareceu. Isso é coerente com o perfil do pass de execução — ele atacou o conjunto
verificável e não encostou nos 10 abertos, exatamente como o `_index.md` já declarava.

O sinal relevante não é a mortalidade e sim a **direção**: quatro dos dez pioraram
mensuravelmente na janela (`install.sh` +144 linhas, `CHANGELOG.md` +105, cada README +110,
`session-start.sh` estável mas ainda 47% acima do slug). São os achados do grupo "decomposição de
script" e "sem medição" do `_index.md` — os que ninguém fecha porque nenhum gate os mede. O gate de
`CLAUDE.md` (600/700) criado nesta janela é o único contra-exemplo, e é justamente sobre o arquivo
que também cresceu.
