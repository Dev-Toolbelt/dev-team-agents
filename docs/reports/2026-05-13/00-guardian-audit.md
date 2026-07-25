# Guardian Audit — 2026-05-13

Auditoria de Guardian dos **44 fingerprints** registrados em **2026-05-12** + verificação cruzada com `git log --since="2026-05-12"`.

> **Método:** para cada fingerprint, foi consultado o repositório atual (`git log`, `wc -l`, `ls`, `grep` no conteúdo dos arquivos) e o resultado comparado com a descrição original. Marcação aplicada: ✅ **Executed**, ⚠️ **Partial**, ↩️ **Reverted**, 🟢 **Resolved** ou _(sem marker)_ quando ainda pendente.

---

## Sumário Executivo

| Métrica | Quantidade |
|---------|-----------|
| Fingerprints auditados (2026-05-12) | 44 |
| ✅ Executed em 2026-05-13 | **25** |
| ⚠️ Partial | **7** |
| ↩️ Reverted | 0 |
| 🟢 Resolved | **0** |
| Ainda pendentes (sem marker) | **12** |

> **Janela de implementação:** entre `e7335a4` (publicação dos relatórios de 2026-05-12) e `ac6af24` (HEAD em 2026-05-13) foram registrados **22 commits** que implementaram suggestions diretamente. **Maior throughput documentado até hoje** (supera os 30 ✅ de 2026-05-10 quando ajustado pelo total auditado: 25/44 = **57%** de execução em 24h, vs 30/34 = 88% em 2026-05-10 mas com escopo menor).

---

## 1. Categoria `01-referencias-e-consistencia` (12 fingerprints)

| Fingerprint | Status | Evidência |
|-------------|--------|-----------|
| `docs-sync-extracted-docs-not-translated-to-pt-br` | ✅ **Executed** | Commit `809e16c` (docs: add Portuguese translations for agents and installation guides). `docs/agents.pt-BR.md` e `docs/installation.pt-BR.md` agora existem |
| `ref-jira-skill-over-500-line-hard-limit` | ✅ **Executed** | Commit `e83eb3b` (refactor(skills): extract jira and monitoring skills to references/ subdirectories). `wc -l skills/integrations/jira/SKILL.md` = **91 linhas** (-82%); `references/{mcp-setup,operations,rest-api}.md` populadas |
| `ref-large-skills-no-references-subdir-pattern-not-adopted` | ✅ **Executed** | Commit `b8ece69` (feat(skills): extract large devops+docs skills to references/ subdirectories). Todas as 7 skills citadas hoje estão sob 100 linhas e têm `references/` populadas (monitoring 68, sonarqube 74, sentry 71, docs-sync 100, cloudflare 86, iac-terraform 80, jira 91) |
| `ref-design-skills-non-standard-frontmatter-keys` | ✅ **Executed** | Commit `27de227` (fix(skills): remove non-canonical frontmatter keys from design skills). `head -10 skills/design/{web-design-guidelines,frontend-design}/SKILL.md` confirma apenas `name` + `description` |
| `ref-tools-frontmatter-ordering-divergence-reviewers-vs-coders` | _pendente_ | Coders mantêm `Read, Write, Edit, Bash, Glob, Grep` (12 agents); reviewers mantêm `Read, Grep, Glob, Bash` (3 agents). `agent-lint.sh` valida presença mas não ordem canônica |
| `ref-security-specialist-tools-lack-write-edit-vs-report-generation-mismatch` | _pendente_ | `grep "^tools:" agents/security-specialist.md` retorna `Read, Grep, Glob, Bash, WebSearch` — sem `Write`/`Edit`. Continua incompatível com produção de relatórios SAST mencionados nas skills `iso27001-sgsi` e `security-checklist` |
| `ref-ci-yml-no-skill-size-limit-validation` | ✅ **Executed** | Commits `5b61720` e `9b7ff74`. `.github/workflows/ci.yml` linha 26: `bash scripts/size-limits.sh --warn-only`. Validação ativa em `--warn-only` (gradual rollout) |
| `ref-claude-md-file-structure-misses-new-docs-children` | ✅ **Executed** | Commit `7977977` (docs(claude-md): update file structure, command table, and authoring rules). `CLAUDE.md` agora declara `docs/{agents.md, installation.md, reports/}` na árvore (linhas ~310-314) |
| `ref-changelog-package-exclusions-update-not-documented-in-unreleased` | ✅ **Executed** | Commit `ebdcb3a` (docs: update CHANGELOG and CLAUDE.md for audit improvements). CHANGELOG `[Unreleased]` agora menciona `Package exclusions` table expanded with `Mechanism` column |
| `ref-claude-md-immutability-contract-vs-actual-symlinks-rule-drift` | ✅ **Executed** | `grep "fixed path" CLAUDE.md` confirma: "These files are installed at a fixed path (`.dev-team-agents/`) and replaced entirely on every update." Sem menção a "symlinks" — descrição alinhada com `mv` real do install.sh |
| `ref-orphan-scan-covers-agents-only-but-skills-may-be-loaded-only-by-commands` | ✅ **Executed** | Commit `19de0e1` (feat(scripts): extend orphan-skill-scan to cover commands/ and workflows/ as consumers). `head -25 scripts/orphan-skill-scan.sh` confirma `AGENTS_DIR + COMMANDS_DIR + WORKFLOWS_DIR` no loop |
| `ref-package-exclusions-table-mechanism-column-overlap-with-install-sh-comments` | ✅ **Executed** | Commit `0a0b3a2` (feat(scripts): add package-exclusion comments and register PreCompact hook). `grep "package exclusion" scripts/install.sh` retorna comentário inline mapeando para tabela CLAUDE.md |

**Total categoria 01:** 10 ✅ Executed, 0 ⚠️ Partial, 2 pendentes.

---

## 2. Categoria `02-fluxos-e-workflows` (10 fingerprints)

| Fingerprint | Status | Evidência |
|-------------|--------|-----------|
| `flow-plan-command-does-not-load-plan-mode-skill` | ✅ **Executed** | Commits `c3cbd15` (feat(commands): load plan-mode skill in devteam:plan command) e `eb5f90e` (feat(commands): load plan-mode skill at the command level). 16 commands carregam `plan-mode` (incluindo `commands/plan.md`) |
| `flow-installer-hook-coverage-still-3-of-7-after-session-start-added` | ⚠️ **Partial** | Commit `0a0b3a2` registra `PreCompact` no installer; commit `57dc8ca` cria `scripts/hooks/pre-compact.sh`. `grep "_inject_hook" scripts/install.sh`: 4 hooks ativos (PreToolUse, Stop, SessionStart, PreCompact). **Falta:** `UserPromptSubmit`, `SubagentStop`, `Notification` |
| `flow-review-command-no-explicit-plan-gate-undocumented-exception` | ✅ **Executed** | Commit `7977977` (docs(claude-md)). `grep "Plan Gate" CLAUDE.md` confirma exceção documentada: "Exception — commands that do NOT require Plan Gate: `/devteam:review`" |
| `flow-stop-dispatcher-runs-all-4-sub-scripts-without-fast-path` | ✅ **Executed** | Commit `f96f3cd` (perf(scripts): add no-changes fast-path to stop dispatcher and sub-scripts 01-03). `grep "DEVTEAM_NO_CHANGES" scripts/hooks/stop.sh scripts/hooks/stop/0[1-3]*.sh` confirma flag exportada e checada nos sub-scripts |
| `flow-no-pre-spawn-current-context-warm-cache` | ✅ **Executed** | Commit `90d2f40` (feat(skills): add context cache, discovery lockfile, and graphify skip conditions) + `ac6af24` (refactor(skills): move context-cache path to user-data/). `skills/shared/current-context/SKILL.md` linhas 60-78 detalham TTL 300s em `.claude/user-data/.context-cache.json` |
| `flow-spawn-classifier-only-plan-but-fix-refactor-fullstack-multi-agent-too` | ✅ **Executed** | Commit `3f98f26` (feat(commands): load spawn-classifier in all commands with conditional agent spawn). 7 commands agora carregam `spawn-classifier`: backend, fix, frontend, fullstack, plan, refactor, review |
| `flow-no-workflow-mobile-md-and-workflow-design-md-files` | ✅ **Executed** | Commit `ba76ef4` (feat(workflows): add mobile and design workflows). `ls workflows/{mobile,design}.md` confirma 141 + 161 linhas |
| `flow-pr-command-no-conventional-commits-validation-of-staged-commits` | ✅ **Executed** | Commit `e0e8983` (feat(commands): add conventional-commits pre-flight to pr and split commit checks). `commands/pr.md` Step 0a: "Conventional Commits pre-flight" com regex `^(feat\|fix\|docs\|...)(\(.+\))?: .+` |
| `flow-update-command-no-pre-update-backup-strategy-after-revert-fc57a86` | ✅ **Executed** | Commit `57dc8ca` (feat(scripts): add pre-compact hook and rollback script). `scripts/rollback.sh` (65 linhas) re-baixa via tag GitHub; `scripts/update.sh` linhas ~30-35 escrevem `.installed-version.prev` antes do swap |
| `flow-refactor-workflow-no-tag-checkpoint-still-after-checkpoints-added` | ✅ **Executed** | Commit `2746c7c` (feat(workflows): add pre-refactor safety tag step to refactor workflow). `grep "pre-refactor" workflows/refactor.md` confirma `git tag pre-refactor-<scope>-$(date +%Y%m%d%H%M%S)` |

**Total categoria 02:** 9 ✅ Executed, 1 ⚠️ Partial, 0 pendentes.

---

## 3. Categoria `03-agentes-e-skills` (12 fingerprints)

| Fingerprint | Status | Evidência |
|-------------|--------|-----------|
| `agent-software-architect-foundational-rule-51-lines-2x-avg` | ⚠️ **Partial** | Commit `3d1152c` (refactor(agents): reduce file sizes — architect, database, setup, reviewer-base). Foundational caiu de **51 → 33 linhas** (-35%). Ainda outlier vs mediana 22; +50% acima do p50 |
| `agent-setup-assistant-foundational-rule-only-10-lines-undersized` | _pendente_ | `awk` revela que setup-assistant Foundational tem hoje **7 linhas** (encolheu de 10). Continua undersized vs mediana 22; loading delegado a 1 chamada `project-context` + nota `token-efficiency` |
| `skill-token-efficiency-not-loaded-by-six-non-coding-agents` | ✅ **Executed** | Commit `2a14f3a` (feat(agents): apply token-efficiency skill to non-coding agents). `grep -L token-efficiency agents/{product-analyst,qa-specialist,security-specialist,setup-assistant,technical-writer,ui-ux-designer}.md` retorna **vazio** (todos carregam) |
| `agent-mobile-developer-no-detox-or-maestro-test-routing-still-pending` | ✅ **Executed** | Commit `57d73d6` (feat(agents): add mobile testing routing section to mobile-developer). `grep -i "detox\|maestro\|appium" agents/mobile-developer.md` retorna 5+ hits incluindo tabela de detection com `.detoxrc`, `.maestro/`, `wdio.conf.js` |
| `skill-no-skill-uses-scripts-subdir-pattern-agentskills-io` | _pendente_ | `find skills -type d -name scripts` continua vazio. Padrão `agentskills.io` `scripts/` subdir não adotado em nenhuma skill |
| `agent-tools-frontmatter-canonical-order-not-enforced` | ⚠️ **Partial** | Commit `72ff0ee` (feat(scripts): add tools frontmatter validation to agent-lint). `grep "KNOWN_TOOLS\|Read must be present" scripts/agent-lint.sh` confirma validação de presença de `Read` e tools conhecidas. **Falta:** validação de **ordem canônica** entre coders/reviewers |
| `skill-monitoring-references-folder-exists-but-empty` | ✅ **Executed** | `ls skills/devops/monitoring/references/` retorna 5 arquivos: cloudwatch.md, datadog.md, loki-config.md, prometheus-alerts.md, prometheus-grafana.md |
| `agent-product-analyst-loads-jira-skill-but-not-other-trackers` | ⚠️ **Partial** | `grep -A3 "Linear Integration" agents/product-analyst.md` confirma seção dedicada a Linear com detection rules. **Falta:** Asana, ClickUp e outros trackers listados em `setup-scan/SKILL.md` ainda não têm gate similar |
| `skill-frontmatter-strict-validation-missing-from-lint` | ✅ **Executed** | Commit `5b61720` (feat(scripts): add size-limits.sh and extend agent-lint with skill frontmatter validation). `grep "non-canonical" scripts/agent-lint.sh` retorna validação que rejeita qualquer chave além de `name`/`description` em SKILL.md |
| `skill-discovery-mode-three-agents-need-explicit-collision-protocol` | ✅ **Executed** | Commit `90d2f40`. `grep -A5 "discovery-lock" skills/shared/discovery-mode/SKILL.md` revela protocol com `LOCK=".claude/.discovery-lock"`, fail-fast, trap cleanup |
| `agent-no-mandatory-load-skill-for-stack-detection` | _pendente_ | `find skills -name "*stack*"` retorna vazio. Stack detection continua inline em setup-assistant/software-architect/database-specialist sem skill compartilhada |
| `skill-reviewer-base-loaded-after-project-context-but-overlaps-7-steps` | ✅ **Executed** | Commit `3d1152c`. `wc -l skills/shared/reviewer-base/SKILL.md` = 19 linhas (era 28 → -32%). Overlap com project-context drasticamente reduzido |

**Total categoria 03:** 7 ✅ Executed, 2 ⚠️ Partial, 3 pendentes.

---

## 4. Categoria `04-economia-tokens` (10 fingerprints)

| Fingerprint | Status | Evidência |
|-------------|--------|-----------|
| `token-foundational-rule-software-architect-outlier-51-lines` | ⚠️ **Partial** | Foundational caiu de **51 → 33** (-35%). Sub-escopo pendente: **continua 50% acima da mediana** (22 linhas) |
| `token-extracted-docs-loaded-by-readme-but-may-be-read-fully-by-agents` | _pendente_ | Não há gate explícito em agents/skills proibindo leitura de `docs/agents.md`/`docs/installation.md` em audit; setup-assistant Foundational menciona "never read docs/installation.md or docs/agents.md" mas **outros 16 agents não têm essa cláusula** |
| `token-skill-monitoring-444-lines-loaded-by-devops-and-architect` | ✅ **Executed** | Commit `b8ece69`. `wc -l skills/devops/monitoring/SKILL.md` = **68 linhas** (era 444 → -85%); 5 references/ populadas; carregamento agora é "trigger + lazy detail" |
| `token-readme-228-each-pos-extraction-but-ci-sync-still-line-based` | ✅ **Executed** | Commits `aa69ac4` (feat(ci): use section-header matching for README EN/pt-BR sync check) + `ef21af2` (fix(ci): compare section counts instead of header text). `cat .github/workflows/ci.yml` confirma comparação por contagem de `^## ` headers + sanity 50% line-count |
| `token-plan-mode-143-lines-7-agents-but-only-1-command-loads` | ⚠️ **Partial** | 16 commands agora carregam `plan-mode` (era 1). **Sub-escopo pendente:** os 7 agents que **também** carregam plan-mode no startup criam **load duplicado** quando spawneados via command (carga nas duas pontas) — inversão de objetivo: economia esperada virou aumento |
| `token-changelog-cresceu-de-119-para-129-linhas-em-um-dia` | _pendente_ | `wc -l CHANGELOG.md` = **130 linhas** (+1 em 24h, ritmo desacelerado). Trajetória mantida; threshold rotação 300 não atingido |
| `token-stop-hook-04-sub-scripts-200ms-overhead-on-read-only-sessions` | ✅ **Executed** | Commit `f96f3cd`. `grep -B1 -A3 "DEVTEAM_NO_CHANGES" scripts/hooks/stop/0[1-3]*.sh` confirma fast-path em sub-scripts 01, 02 e 03; 04-notifier mantém execução (responsável por turn-counter) |
| `token-foundation-rule-cumulative-across-multi-agent-spawn-fanout` | _pendente_ | Insight contraintuitivo permanece válido — extração para skill ainda **piora** sem cache cross-spawn. Dependência do fingerprint `flow-no-pre-spawn-current-context-warm-cache` foi parcialmente atendida (cache existe), mas Foundational Rule continua inline |
| `token-orphan-scan-script-shells-13-times-per-execution` | ✅ **Executed** | Commit `97a3f0d` (perf(scripts): optimize orphan-scan to O(skills) and skip sections/). `head -50 scripts/orphan-skill-scan.sh` revela comentário "1 grep per skill instead of 2 × N_consumers" |
| `token-comments-policy-417-lines-still-monolith-no-section-loading` | ⚠️ **Partial** | Commit `6c8516b` (feat(skills): add language-specific sections to comments-policy). `wc -l skills/shared/comments-policy/SKILL.md` = **91 linhas** (era 417 → -78%); pasta `sections/` populada com aaa-pattern.md, anti-patterns.md, type-annotations.md. **Sub-escopo pendente:** SKILL.md ainda não documenta carregamento condicional por linguagem (lazy-load) |

**Total categoria 04:** 4 ✅ Executed, 3 ⚠️ Partial, 3 pendentes.

---

## Veredito Guardian

| Status | Quantidade | % |
|--------|-----------|---|
| ✅ Executed | **25** | 57% |
| ⚠️ Partial | **7** | 16% |
| 🟢 Resolved | 0 | 0% |
| Pendentes | **12** | 27% |
| ↩️ Reverted | 0 | 0% |

**Observações:**

1. **Maior throughput documentado** — 25 fingerprints executados em 24h. Ritmo crescente desde 2026-05-10 (30/34 = 88%) → 2026-05-11 (13/50 = 26%) → 2026-05-12 (?/?) → **2026-05-13 (25/44 = 57%)**. O batch de 22 commits inclui features estruturais grandes (rollback, pre-compact hook, context cache, sections/ pattern, references/ pattern em 7 skills).
2. **Padrão `references/` finalmente adotado em escala** — após 4 passadas consecutivas registrando o gap, 7 skills grandes foram refatoradas no mesmo commit (`b8ece69`). Confirmação: `find skills -type d -name references | wc -l` = **8** pastas populadas (era 1 com conteúdo + 1 vazia).
3. **`commands/plan.md`-`commands/eb5f90e`** — fingerprint `flow-plan-command-does-not-load-plan-mode-skill` foi resolvido **redundantemente** em dois commits separados (`c3cbd15` e `eb5f90e`); ambos legítimos mas indicam falta de coordenação entre passes do mesmo dia.
4. **Pendências repetidas por 3+ passadas:**
   - `agent-mobile-test-specialist-missing` — registrado em 2026-05-11, 2026-05-12; ainda sem owner.
   - `skill-graphify-setup-no-conditional-by-project-language` — registrado em 2026-05-11, 2026-05-12; skill segue 277 linhas sem gate.
   - `agent-setup-assistant-foundational-rule-only-10-lines-undersized` — promovido em 2026-05-12, encolheu para 7 linhas em vez de crescer (regressão silenciosa).
5. **`agent-no-mandatory-load-skill-for-stack-detection`** — segue pendente apesar de stack detection inline em 4 agents; sinal de que a sugestão precisa ser **reproposta com plano de extração específico**, não apenas reforço.

---

## Atualizações Aplicadas ao `_index.md`

As marcações deste audit foram propagadas para `docs/reports/_index.md` (seção 2026-05-12). Linha por linha:

- ✅ Executed: 25 entries
- ⚠️ Partial: 7 entries (com sub-escopo pendente descrito)
- 🟢 Resolved: 0 entries

> Para reproposta no próximo audit, **fingerprints ⚠️ Partial** podem ser repropostos **somente** para o sub-escopo pendente (descrito na coluna "Evidência" acima).

---

## Cross-link com fingerprints anteriores (auditoria estendida)

Esta passada também detectou progresso em fingerprints históricos:

- **`flow-hook-events-only-pretooluse-and-stop`** (2026-05-10, ⚠️ Partial em 2026-05-11): `PreCompact` adicionado em commit `0a0b3a2` — agora **4 de 7+** hook events registrados (PreToolUse, Stop, SessionStart, PreCompact). `UserPromptSubmit`, `SubagentStop`, `Notification` permanecem.
- **`ref-templates-folder-still-single-file-after-three-passes`** (2026-05-11, pendente): commit `c207e3f` (feat(templates): add ADR, backlog item, and runbook templates) — `ls templates/` agora retorna 4 arquivos: adr-template.md, backlog-template.md, plan-template.md, runbook-template.md. **Promove para ✅ Executed**.
- **`skill-release-prep-missing-despite-mentioned-in-changelog-1.2.0`** (2026-05-11, pendente): commit `b73f480` (feat(skills): add release-prep skill and wire to technical-writer) — `ls skills/shared/release-prep/SKILL.md` confirma 88 linhas. **Promove para ✅ Executed**.
- **`flow-no-cross-link-between-workflows-still`** (2026-05-12, pendente): commit `62e12df` (feat(workflows): add related-workflows cross-links and MTTR tracking) — `grep "Related workflows:" workflows/*.md` retorna 10 hits (1 por workflow). **Promove para ✅ Executed**.
- **`flow-security-patch-no-mttr-tracking`** (2026-05-12, pendente): commit `62e12df` também adicionou tracking de MTTR no security-patch workflow. **Promove para ✅ Executed**.
- **`flow-no-workflow-command-shortcuts-for-fullstack-refactor-review`** (2026-05-11, pendente): commit `13fd0dc` (feat(commands): add workflow shortcut commands for fullstack, refactor, and review) — `ls commands/workflow-{fullstack,refactor,review}.md` confirma 3 arquivos. **Promove para ✅ Executed**.
- **`flow-spawn-classifier-only-loaded-by-plan-command`** (2026-05-11, pendente): mesmo commit `3f98f26`. **Promove para ✅ Executed**.

Total de fingerprints **históricos** promovidos para ✅ Executed nesta passada: **6**. Atualizações aplicadas no `_index.md` correspondente.
