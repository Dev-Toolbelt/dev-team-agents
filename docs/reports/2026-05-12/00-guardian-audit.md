# Guardian Audit — 2026-05-12

Auditoria de Guardian dos 50 fingerprints registrados em **2026-05-11** + verificação cruzada com `git log --since="2026-05-11"`.

> **Método:** para cada fingerprint, foi consultado o repositório atual (`git log`, `wc -l`, `ls`, `grep` no conteúdo dos arquivos) e o resultado comparado com a descrição original. Marcação aplicada: ✅ **Executed**, ⚠️ **Partial**, ↩️ **Reverted**, 🟢 **Resolved** ou _(sem marker)_ quando ainda pendente.

---

## Sumário Executivo

| Métrica | Quantidade |
|---------|-----------|
| Fingerprints auditados (2026-05-11) | 50 |
| ✅ Executed em 2026-05-12 | **13** |
| ⚠️ Partial | **4** |
| ↩️ Reverted | 0 |
| 🟢 Resolved | **1** |
| Ainda pendentes (sem marker) | **32** |

> **Janela de implementação:** entre `b9c8b44` (publicação dos relatórios de 2026-05-11) e `c3b8db2` (HEAD em 2026-05-12) foram registrados **11 commits** que implementaram suggestions diretamente, principalmente nas áreas de **referências, commands faltantes (mobile + adr), gate diário do notifier, README sync e git log window**.

---

## 1. Categoria `01-referencias-e-consistencia` (12 fingerprints)

| Fingerprint | Status | Evidência |
|-------------|--------|-----------|
| `docs-sync-readme-massive-skill-list-drift` | ✅ **Executed** | Commits `0475b6a` (atualiza skill structure com 10 categorias + contagens corretas) e `7800516` (extrai `docs/agents.md`). README.md hoje delega lista detalhada ao `docs/agents.md` |
| `ref-orphan-scan-only-checks-agents-not-commands-or-workflows` | _pendente_ | `scripts/orphan-skill-scan.sh:33` ainda usa `AGENTS_DIR` exclusivo; nenhum loop sobre `commands/` ou `workflows/` |
| `ref-mobile-workflow-missing-despite-command` | _pendente_ | `commands/mobile.md` agora existe, mas `workflows/mobile.md` continua ausente (`ls workflows/` confirma 8 arquivos, nenhum mobile) |
| `ref-installer-strips-strategy-pattern-mismatch-vs-changelog` | ⚠️ **Partial** | Commit `09c00ca` expandiu a tabela "Package exclusions" do CLAUDE.md para 14 itens, separando coluna `Mechanism` (allowlist vs explicit `rm -f`/`rm -rf`). Falta a **mesma documentação no CHANGELOG** ligando a feature ao commit, e o **install.sh continua sem comentário inline explicando a estratégia dual** |
| `ref-commands-two-without-current-context-undocumented` | ✅ **Executed** | Commit `09c00ca` adicionou linha 154 do CLAUDE.md: "Exception — commands that do NOT load `current-context`: `/devteam:commit` … `/devteam:update`" |
| `ref-templates-folder-still-single-file-after-three-passes` | _pendente_ | `ls templates/` continua mostrando apenas `plan-template.md` (4ª passada consecutiva sem migração ADR/backlog/runbook) |
| `ref-claude-md-mentions-agents-creator-as-claude-skills-path` | _pendente_ | Tabela "User-Invocable Skills" em CLAUDE.md ainda mistura `skills/skill-creator/SKILL.md` (path repo) com `.claude/skills/agent-creator/SKILL.md` (path pós-install) |
| `ref-stop-hook-04-notifier-undocumented-in-changelog-unreleased` | ✅ **Executed** | Commit `e86550c` adicionou entrada para `04-notifier.sh` na seção `[Unreleased]` do CHANGELOG |
| `ref-database-specialist-still-258-lines-after-engine-split` | ⚠️ **Partial** | `wc -l agents/database-specialist.md` retorna 252 linhas (era 258 → redução de 6 linhas). Ainda 26% acima do limite ~200; **split inline → engine skills ainda pendente** |
| `ref-no-orphan-template-scan-with-zero-templates-still-pending` | _pendente_ | `templates/` continua com 1 arquivo; gatilho de "3+ arquivos" não disparado |
| `ref-graphify-setup-skill-referenced-by-name-not-path-blind-spot` | ✅ **Executed** | Commit `8ee6713` (fix(agents): use full path for graphify-setup skill reference in setup-assistant) |
| `docs-sync-claude-md-package-exclusions-includes-LICENSE-without-marking` | ✅ **Executed** | CLAUDE.md tabela "Package exclusions" agora lista explicitamente LICENSE, CHANGELOG.md, CONTRIBUTING.md, SECURITY.md, docs/ (commit `09c00ca`) |

**Total categoria 01:** 5 ✅ Executed, 2 ⚠️ Partial, 5 pendentes.

---

## 2. Categoria `02-fluxos-e-workflows` (13 fingerprints)

| Fingerprint | Status | Evidência |
|-------------|--------|-----------|
| `flow-command-mobile-md-missing-but-claude-md-claims-it` | ✅ **Executed** | Commit `1c8be69` cria `commands/mobile.md` (1396 bytes); inclui Plan Gate e spawn de mobile-developer + ui-ux-designer |
| `flow-no-workflow-command-shortcuts-for-fullstack-refactor-review` | _pendente_ | `ls commands/workflow-*.md` retorna apenas 5 (bugfix, inherited, maintenance, new, security-patch); faltam `workflow-fullstack.md`, `workflow-refactor.md`, `workflow-review.md` |
| `flow-spawn-classifier-only-loaded-by-plan-command` | _pendente_ | `grep -l "spawn-classifier" commands/*.md` retorna **apenas** `commands/plan.md`; comandos multi-agent (backend/frontend/fullstack/refactor/fix/review/mobile) continuam sem carregamento condicional |
| `flow-claude-md-workflows-list-incomplete` | ✅ **Executed** | CLAUDE.md linha 167 agora lista todos 8 workflows: `new-project.md`, `bug-fix.md`, `maintenance.md`, `inherited-project.md`, `security-patch.md`, `fullstack.md`, `refactor.md`, `review.md` (commit `09c00ca`) |
| `flow-no-pre-spawn-installation-freshness-check` | _pendente_ | Nenhum command verifica frescor antes de spawn; `PreToolUse` TTL 24h continua único gate |
| `flow-commit-command-no-type-check-or-tests-gate` | ⚠️ **Partial** | Commit `dd637ca` adicionou pre-commit gate em `commands/commit.md` (linhas 74-81: ESLint, `npm run lint`, Makefile lint, hooks Husky/Lefthook). **Lint resolvido**; **type-check (`tsc --noEmit`, `mypy`) e tests gate continuam pendentes** |
| `flow-refactor-workflow-no-rollback-tag-recommendation` | _pendente_ | `workflows/refactor.md` tem CHECKPOINTs mas nenhuma menção a `pre-refactor-<ctx>` git tag para rollback |
| `flow-security-patch-no-mttr-tracking` | _pendente_ | `workflows/security-patch.md` continua sem captura de `started_at`/`deployed_at` |
| `flow-no-adr-command-despite-script` | ✅ **Executed** | Commit `1c8be69` cria `commands/adr.md` (1545 bytes); chama `bash .dev-team-agents/scripts/new-adr.sh` e delega preenchimento ao `software-architect` |
| `flow-pr-command-no-draft-mode-flag` | ✅ **Executed** | `commands/pr.md` linhas 37 e 44 expõem `draft` em `$ARGUMENTS`: "Draft status (default: false, set to true if $ARGUMENTS contains `draft`)" |
| `flow-no-cross-link-between-workflows-still` | _pendente_ | `grep -n "Next step" workflows/*.md` retorna **vazio** — nenhum workflow contém linha de cross-link |
| `flow-stop-hook-04-notifier-no-gate-runs-every-session` | ✅ **Executed** | Commit `e59e364` (fix(hooks): add daily gate to notifier tip-of-session) — `04-notifier.sh` agora usa `last_shown_date` em `.notifier-state` |
| `flow-discovery-loop-still-no-iteration-cap` | _pendente_ | `discovery-mode` skill segue sem teto explícito de iterações |

**Total categoria 02:** 5 ✅ Executed, 1 ⚠️ Partial, 7 pendentes.

---

## 3. Categoria `03-agentes-e-skills` (13 fingerprints)

| Fingerprint | Status | Evidência |
|-------------|--------|-----------|
| `agent-mobile-test-specialist-missing-asymmetric-with-backend-frontend` | _pendente_ | `ls agents/*mobile*` retorna apenas `mobile-developer.md`; sem `mobile-test-specialist` |
| `agent-setup-assistant-still-306-lines-after-multiple-extractions` | _pendente_ | `wc -l agents/setup-assistant.md` permanece em **306 linhas** (idêntico ao reportado) |
| `skill-reviewer-base-foundational-rule-overlap-with-project-context` | _pendente_ | `reviewer-base/SKILL.md` (28 linhas) ainda contém steps 1-7 que sobrepõem `project-context`. Tamanho reduzido mas overlap conceitual permanece |
| `agent-product-analyst-still-no-bash-tool-after-jira-skill-load` | ✅ **Executed** | `grep "^tools:" agents/product-analyst.md` agora retorna `tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch` (`Bash` presente) |
| `skill-release-prep-missing-despite-mentioned-in-changelog-1.2.0` | _pendente_ | `find skills -name "*release*"` retorna vazio; CHANGELOG linha 93 ainda menciona "Release preparation skill (`release-prep`)" sem artefato correspondente |
| `skill-discovery-mode-loaded-by-three-agents-without-divergence-check` | _pendente_ | `grep -l discovery-mode agents/*.md` retorna 3 agents (product-analyst, setup-assistant, software-architect); sem persistência cruzada |
| `skill-monitoring-444-lines-over-limit-needs-references-extraction` | _pendente_ | `wc -l skills/devops/monitoring/SKILL.md` = 444 linhas (inalterado); a pasta `references/` **existe** mas continua vazia |
| `skill-sonarqube-435-lines-overlap-with-reviewer-base-detection-block` | _pendente_ | `wc -l skills/devops/sonarqube/SKILL.md` = 435 linhas (inalterado); detection block em `reviewer-base/SKILL.md:24` continua presente |
| `agent-mobile-developer-no-detox-or-maestro-test-routing` | _pendente_ | `grep -i -E "(detox\|maestro\|appium)" agents/mobile-developer.md` retorna 0 hits |
| `skill-missing-prompt-engineering-or-llm-integration` | _pendente_ | Nenhuma skill nova de LLM/RAG/embeddings/vector-db criada nesta janela |
| `agent-technical-writer-haiku-mismatch-resolved-by-diataxis-extraction` | 🟢 **Resolved** | Já marcado como meta-resolvido na própria sugestão original; sem ação adicional necessária. Promovendo para 🟢 oficialmente. |
| `skill-current-context-not-loaded-by-fix-or-refactor-workflows` | ✅ **Executed** | Commit `926185e` adiciona Step 0 (current-context) em `workflows/bug-fix.md:13` e `workflows/refactor.md:21` |
| `skill-graphify-setup-no-conditional-by-project-language` | _pendente_ | `skills/devops/graphify-setup/SKILL.md` permanece em 265 linhas sem gate por linguagem/tipo de projeto |

**Total categoria 03:** 2 ✅ Executed, 1 🟢 Resolved, 10 pendentes.

---

## 4. Categoria `04-economia-tokens` (12 fingerprints)

| Fingerprint | Status | Evidência |
|-------------|--------|-----------|
| `token-git-log-window-still-20-after-three-passes` | ✅ **Executed** | Commit `590c34a` (perf(agents): reduce git log window from -20 to -10 in 10 agents) |
| `token-foundational-rule-424-lines-across-17-agents` | _pendente_ | Foundational Rule continua inline em todos os 17 agents (variação de 10–51 linhas; outlier `software-architect` em 51, soma agregada ~370 linhas) |
| `token-worktree-isolation-block-7-lines-x-8-agents` | _pendente_ | Bloco "## Worktree Isolation" inline em 8 agents (6 linhas cada = ~48 linhas duplicadas) |
| `token-architecture-awareness-block-still-duplicated` | _pendente_ | "Architecture Awareness" inline em backend-developer, frontend-developer, mobile-developer |
| `token-changelog-already-growing-and-not-extracted-by-release` | _pendente_ | `wc -l CHANGELOG.md` = 129 linhas (cresceu ~10 linhas desde 2026-05-11); ainda abaixo do threshold sugerido (300) mas trajetória mantida |
| `token-readme-bilingual-dual-source-734-lines-each` | ⚠️ **Partial** | Commit `7800516` extraiu Agent Reference e Installation para `docs/agents.md` e `docs/installation.md`. README.md e README.pt-BR.md hoje têm **228 linhas cada** (queda de ~70% vs 734). **Heurística CI de 5% line-count permanece** (`.github/workflows/ci.yml:32-41`); o sync ainda é dual-source |
| `token-skill-loads-via-table-vs-prose-inconsistent` | _pendente_ | `database-specialist` mantém formato tabela; outros agents mantêm prosa; sem padronização |
| `token-claude-md-672-chars-package-exclusions-table-redundant-vs-installer` | _pendente_ | Tabela em CLAUDE.md cresceu (agora 14 linhas) — **aumento** da redundância em vez de redução; install.sh continua fonte real |
| `token-plan-mode-skill-131-lines-loaded-by-7-agents-unconditionally` | _pendente_ | `wc -l skills/shared/plan-mode/SKILL.md` = 143 linhas (cresceu); carregada por 7 agents (backend, code-reviewer, database, devops, frontend, mobile-developer, software-architect) |
| `token-orphan-scan-output-format-verbose-when-clean` | _pendente_ | `scripts/orphan-skill-scan.sh` mantém output verbose em modo non-quiet |
| `token-three-reviewers-still-share-80-percent-structure` | _pendente_ | code-reviewer (228), backend-reviewer (204), frontend-reviewer (192) = 624 linhas; sobreposição estrutural preservada |
| `token-changelog-unreleased-section-grows-without-rollover` | _pendente_ | Seção `[Unreleased]` continua acumulando itens sem cross-link aos fingerprints do `_index.md` (sugestão de HTML comments inline ainda não aplicada) |

**Total categoria 04:** 1 ✅ Executed, 1 ⚠️ Partial, 10 pendentes.

---

## Veredito Guardian

| Status | Quantidade | % |
|--------|-----------|---|
| ✅ Executed | **13** | 26% |
| ⚠️ Partial | **4** | 8% |
| 🟢 Resolved | **1** | 2% |
| Pendentes | **32** | 64% |
| ↩️ Reverted | 0 | 0% |

**Observações:**

1. **Cadência de implementação saudável** — 13 sugestões executadas em 24h é o **maior throughput desde 2026-05-10** (que teve 30 ✅). Diferença: 2026-05-10 concentrou-se em automação infra-estrutural (community files, hook events); 2026-05-12 priorizou **fechamento de gaps declarativos** (CLAUDE.md ↔ arquivos, commands faltantes, contagens drift no README).
2. **Pendências de alta prioridade** — fingerprints `flow-no-workflow-command-shortcuts-for-fullstack-refactor-review` (3 commands faltantes), `agent-mobile-test-specialist-missing-asymmetric` (asymmetria pipeline mobile) e `ref-orphan-scan-only-checks-agents-not-commands-or-workflows` (governança) seguem pendentes por **2+ passadas consecutivas** e merecem reforço.
3. **Padrão `references/` ainda não adotado** — apesar da sugestão `skill-monitoring-444-lines-over-limit-needs-references-extraction` ter criado a pasta `references/`, ela continua vazia. Outras skills grandes (sonarqube, sentry, cloudflare, iac-terraform, docs-sync) **nem sequer criaram** a pasta.
4. **Nenhum revert detectado nesta janela** — `git log` confirma que as 13 implementações foram aceitas e não revertidas (boa qualidade de PR/decisão).

---

## Atualizações Aplicadas ao `_index.md`

As marcações deste audit foram propagadas para `docs/reports/_index.md` (seção 2026-05-11). Linha por linha:

- ✅ Executed: 13 entries
- ⚠️ Partial: 3 entries (com sub-escopo pendente descrito)
- 🟢 Resolved: 1 entry (`agent-technical-writer-haiku-mismatch-resolved-by-diataxis-extraction`)

> Para reproposta no próximo audit, **fingerprints ⚠️ Partial** podem ser repropostas **somente** para o sub-escopo pendente (descrito na coluna "Evidência" acima).

---

## Cross-link com fingerprints anteriores (auditoria estendida)

Esta passada também detectou um sub-escopo ainda pendente do fingerprint **`flow-hook-events-only-pretooluse-and-stop`** (2026-05-10, ⚠️ Partial em 2026-05-11): o `SessionStart` foi adicionado, mas os 4 eventos restantes (`UserPromptSubmit`, `SubagentStop`, `Notification`, `PreCompact`) continuam sem registro no `install.sh`. Reforço repropostável.
