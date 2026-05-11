# Índice de Sugestões — Histórico Acumulado

Este arquivo é o **banco de fingerprints de sugestões já realizadas** nos relatórios diários
de auditoria do projeto `dev-team-agents`. Ele garante que cada relatório novo entregue
**sugestões originais**, sem repetir recomendações de dias anteriores.

---

## Como Funciona

1. Cada sugestão recebe um **fingerprint** curto (slug, em `kebab-case`) descrevendo o tema.
2. Antes de gerar um relatório novo, o agendador (ou agente) **lê este índice** e exclui
   da geração qualquer fingerprint já registrado.
3. Após publicar o relatório do dia, **as novas fingerprints são acrescentadas** abaixo,
   junto com o link para o relatório de origem.
4. Se um tema crítico exigir reforço, ele pode ser repropos­to com escopo **mais específico**
   (ex.: `token-efficiency-context-loading` é diferente de `token-efficiency-tool-output`).

> Estratégia de evolução: o índice cresce indefinidamente, mas pode ser **rotacionado** a
> cada 90 dias movendo entradas antigas para `_index-archive-YYYY-Q.md`.

---

## Convenção de Fingerprints

| Categoria | Prefixo | Exemplo |
|-----------|---------|---------|
| Documentação fora de sincronia | `docs-sync-*` | `docs-sync-readme-skills-list` |
| Referências quebradas / órfãs | `ref-*` | `ref-agent-creator-location` |
| Melhoria de fluxo / workflow | `flow-*` | `flow-bugfix-parallel-marker` |
| Melhoria em agente | `agent-*` | `agent-setup-assistant-size` |
| Melhoria em skill | `skill-*` | `skill-security-add-incident-response` |
| Economia de tokens | `token-*` | `token-context-loading-dedup` |
| Automação / scripts / hooks | `auto-*` | `auto-skill-frontmatter-validator` |
| Governança / política | `gov-*` | `gov-orphan-scan-redundancy` |

---

## Fingerprints Registrados

<!--
  Formato de cada linha:
    - `<fingerprint>` — descrição — [relatório](caminho) [— ✅ **Executed:** YYYY-MM-DD]
  Mantenha em ordem cronológica decrescente (mais recente primeiro).
  
  Legenda de status:
    ✅ Executed    — item implementado; o agente de research NÃO precisa repropostar
    ⚠️ Partial     — parcialmente endereçado; repropostar somente para o sub-escopo pendente
    (sem marker)  — sugestão registrada, ainda não implementada
-->

### 2026-05-10 — quinta passada (foco em drift declarativo CLAUDE.md↔arquivos, community files, hook events não explorados, skills extraídas com inline mantido)

- `ref-current-context-skill-orphaned-from-commands` — `CLAUDE.md` declara `current-context` para "todos os /devteam:*"; 0 dos 22 commands carregam — 21 inlinearam bloco git — [relatório](2026-05-10/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-05-11
- `ref-spawn-classifier-skill-only-software-architect` — `CLAUDE.md` declara `spawn-classifier` para `/devteam:plan`; só `software-architect` carrega; `commands/plan.md` ignora — [relatório](2026-05-10/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-05-11
- `ref-no-security-md` — Sem `SECURITY.md` em repo público com instalador via `curl | bash` — [relatório](2026-05-10/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-05-11
- `ref-no-contributing-md` — Sem `CONTRIBUTING.md` apesar de 270+ linhas de regras em CLAUDE.md (orientadas a Claude, não a humanos) — [relatório](2026-05-10/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-05-11
- `ref-no-changelog-md` — Sem `CHANGELOG.md` apesar de SemVer e referência no hook de update — [relatório](2026-05-10/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-05-11
- `ref-no-pr-and-issue-templates` — Sem `.github/PULL_REQUEST_TEMPLATE.md` e `.github/ISSUE_TEMPLATE/` — [relatório](2026-05-10/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-05-11
- `ref-no-codeowners-file` — Sem `.github/CODEOWNERS` — [relatório](2026-05-10/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-05-11
- `ref-skill-frontmatter-allowed-tools-key-inconsistency` — `worktree/SKILL.md` é única skill com `allowed-tools:` entre 99; padrão não documentado em CLAUDE.md — [relatório](2026-05-10/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-05-11
- `ref-stop-hook-shim-numbering-undocumented` — Sub-scripts `01/02/03` em `hooks/stop/` numerados; convenção não documentada — [relatório](2026-05-10/01-referencias-e-consistencia.md) — ✅ **Executed:** 2026-05-11
- `flow-hook-events-only-pretooluse-and-stop` — Installer registra só 2 de 7+ hook events suportados; `SessionStart`, `UserPromptSubmit`, `SubagentStop`, `Notification`, `PreCompact` inexplorados — [relatório](2026-05-10/02-fluxos-e-workflows.md) — ⚠️ **Partial:** 2026-05-11 (`SessionStart` adicionado; `UserPromptSubmit`, `SubagentStop`, `Notification`, `PreCompact` permanecem para próxima passada)
- `flow-update-command-no-rollback-path` — `/devteam:update` não tem `--rollback`; `INSTALL_DIR.old.$$` é deletado imediatamente após swap — [relatório](2026-05-10/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-05-11
- `flow-commit-no-pre-commit-gate` — `/devteam:commit` não roda linters/formatters antes de commitar — [relatório](2026-05-10/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-05-11
- `flow-workflows-no-failure-recovery` — Workflows não definem caminho de falha intermediária (review loop infinito, abort no meio, commit travado) — [relatório](2026-05-10/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-05-11
- `flow-pr-command-no-template-file-link` — `/devteam:pr` produz prosa sem detectar `.github/PULL_REQUEST_TEMPLATE.md` — [relatório](2026-05-10/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-05-11
- `flow-no-stale-branch-detection` — Nenhum workflow detecta branch atrasada de main antes de operar — [relatório](2026-05-10/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-05-11
- `flow-setup-no-docker-compose-version-detection` — `setup-assistant` assume `docker compose` (V2); não testa fallback `docker-compose` (V1) — [relatório](2026-05-10/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-05-11
- `flow-no-merge-conflict-preflight` — Workflows fix/refactor não rodam `git merge-tree` para detectar conflito potencial com main — [relatório](2026-05-10/02-fluxos-e-workflows.md)
- `agent-database-specialist-no-per-engine-skills` — `database-specialist` (272 linhas) cobre 6+ engines inline; padrão `cicd-base+variantes` não replicado para database — [relatório](2026-05-10/03-agentes-e-skills.md) — ⚠️ **Partial:** 2026-05-11 (`postgres`, `mysql`, `mongodb` criadas e wired; `redis`, `sqlserver`, `cassandra`, `sqlite` e split do agente permanecem)
- `skill-missing-event-driven-architecture` — Sem skill para CQRS/saga/event-sourcing/domain-vs-integration events — [relatório](2026-05-10/03-agentes-e-skills.md) — ✅ **Executed:** 2026-05-11
- `skill-missing-rate-limiting` — Sem skill dedicada para algoritmos (token bucket, leaky bucket, sliding window) — [relatório](2026-05-10/03-agentes-e-skills.md) — ✅ **Executed:** 2026-05-11
- `skill-missing-performance-budgets` — Sem skill para Core Web Vitals budgets, bundle size, Lighthouse CI — [relatório](2026-05-10/03-agentes-e-skills.md) — ✅ **Executed:** 2026-05-11
- `skill-missing-api-versioning-dedicated` — `api-design` toca versioning brevemente; sem skill dedicada (URL/header/content negotiation/deprecation lifecycle) — [relatório](2026-05-10/03-agentes-e-skills.md) — ✅ **Executed:** 2026-05-11
- `skill-diataxis-not-extracted` — Framework Diátaxis inline em `technical-writer.md`; sem skill `diataxis-framework` reusável por outros agentes — [relatório](2026-05-10/03-agentes-e-skills.md) — ✅ **Executed:** 2026-05-11
- `skill-discovery-mode-not-loaded-by-setup-assistant` — Skill carregada por `software-architect` e `product-analyst`; `setup-assistant` (que classifica projetos) não — [relatório](2026-05-10/03-agentes-e-skills.md) — ✅ **Executed:** 2026-05-11
- `agent-product-analyst-jira-skill-not-loaded-foundational` — `product-analyst` cria backlog mas não carrega `skills/integrations/jira/SKILL.md` (carga só em qa/code-reviewer) — [relatório](2026-05-10/03-agentes-e-skills.md) — ✅ **Executed:** 2026-05-11
- `skill-database-debug-multitenancy-not-loaded-by-database-specialist` — Skills `database-debug` e `database-multitenancy` em `integrations/`; `database-specialist` é consumidor natural mas verificação de carga ausente — [relatório](2026-05-10/03-agentes-e-skills.md) — ✅ **Executed:** 2026-05-11
- `token-current-context-skill-vs-21-inline-blocks` — Skill `current-context` (29 linhas) existe; 21 commands inlinearam ~7 linhas de git block + ~30 linhas de scope rule — ~150 linhas duplicadas — [relatório](2026-05-10/04-economia-tokens.md) — ✅ **Executed:** 2026-05-11
- `token-reviewer-mindset-extracted-but-inline-kept-with-double-load` — Skill extraída E inline mantido em 3 reviewer agents; ambos carregados no startup — [relatório](2026-05-10/04-economia-tokens.md) — ✅ **Executed:** 2026-05-11
- `token-token-efficiency-apply-line-six-variants` — Frase "Apply token-efficiency..." em 10 agentes com 6 redações distintas — [relatório](2026-05-10/04-economia-tokens.md) — ✅ **Executed:** 2026-05-11
- `token-install-sh-blocklist-vs-allowlist` — `install.sh` strippa por blocklist (8 itens); allowlist seria mais robusto a novos arquivos no repo — [relatório](2026-05-10/04-economia-tokens.md) — ✅ **Executed:** 2026-05-11
- `token-stop-hook-orphan-scan-unconditional-rerun` — `02-orphan-skill-scan.sh` roda a cada Stop sem gate por mudança em `agents/` ou `skills/` — [relatório](2026-05-10/04-economia-tokens.md) — ✅ **Executed:** 2026-05-11
- `token-claude-md-monolithic-load-every-session` — `CLAUDE.md` (272 linhas) carrega instruções de authoring + setup + memory + commit; fragmentar em `.claude-md/*` modular permite load on demand — [relatório](2026-05-10/04-economia-tokens.md)
- `token-ci-shellcheck-no-binary-cache` — CI `apt-get install shellcheck` reinstala a cada run; usar action ou binário pré-instalado — [relatório](2026-05-10/04-economia-tokens.md) — ✅ **Executed:** 2026-05-11
- `token-update-check-no-etag-handling` — `01-check-updates.sh` faz GET completo a cada 24h sem `If-None-Match` para `304 Not Modified` — [relatório](2026-05-10/04-economia-tokens.md) — ✅ **Executed:** 2026-05-11

### 2026-05-09 — quarta passada (foco em governance, frontmatter inconsistente, skills domain-strategic, duplicação estrutural)

- `ref-qa-specialist-write-without-edit` — `qa-specialist` declara `Write` sem `Edit` — único agente nessa configuração — [relatório](2026-05-09/01-referencias-e-consistencia.md)
- `ref-product-analyst-no-bash-tool` — `product-analyst` sem `Bash`; Foundational Rule de pares exige `git log` — [relatório](2026-05-09/01-referencias-e-consistencia.md)
- `ref-setup-assistant-no-git-log-loading` — `setup-assistant` (404 linhas, classificador) não inclui passo `git log` que outros 14 agentes têm — [relatório](2026-05-09/01-referencias-e-consistencia.md)
- `ref-tools-frontmatter-grep-glob-order-mismatch` — `technical-writer` é o único com `Grep, Glob` em vez de `Glob, Grep` — [relatório](2026-05-09/01-referencias-e-consistencia.md)
- `ref-license-file-missing` — repositório sem `LICENSE`; instalador distribui via `curl` para terceiros sem licença explícita — [relatório](2026-05-09/01-referencias-e-consistencia.md)
- `ref-no-ci-config-in-repo` — `.github/` ausente; repo ensina CI mas não dogfooda — [relatório](2026-05-09/01-referencias-e-consistencia.md)
- `ref-installer-strip-strategy-undocumented` — `install.sh` strippa por blocklist; estratégia de o que **fica** não documentada e vulnerável a adições futuras — [relatório](2026-05-09/01-referencias-e-consistencia.md)
- `ref-near-orphan-setup-only-skills` — `auto-routing`, `backlog-template`, `docs-templates`, `setup-scan` referenciados só por agente único; categoria implícita — [relatório](2026-05-09/01-referencias-e-consistencia.md)
- `ref-code-reviewer-vs-specialists-roles-undocumented` — relação code-reviewer (router) × backend/frontend-reviewer não documentada no CLAUDE.md — [relatório](2026-05-09/01-referencias-e-consistencia.md)
- `flow-no-workflow-refactor` — `commands/refactor.md` existe sem `workflows/refactor.md` correspondente — [relatório](2026-05-09/02-fluxos-e-workflows.md)
- `flow-no-workflow-review` — `commands/review.md` existe sem `workflows/review.md` correspondente — [relatório](2026-05-09/02-fluxos-e-workflows.md)
- `flow-workflows-no-commit-or-pr-step` — nenhum dos 5 workflows termina com passo de commit ou PR — [relatório](2026-05-09/02-fluxos-e-workflows.md)
- `flow-workflows-no-cross-linking` — workflows não se referenciam entre si (bug-fix→security-patch, maintenance→refactor, etc.) — [relatório](2026-05-09/02-fluxos-e-workflows.md)
- `flow-workflows-no-par-table` — fora do `bug-fix.md`, nenhum workflow usa coluna Par. do plan-template (security-patch usa prosa) — [relatório](2026-05-09/02-fluxos-e-workflows.md)
- `flow-security-patch-no-rollback-checkpoint` — `security-patch.md` Step 6 menciona rollback inline mas sem checkpoint formal — [relatório](2026-05-09/02-fluxos-e-workflows.md)
- `flow-inherited-audit-exit-criteria` — `inherited-project.md` audit sem critério explícito de "good enough" — [relatório](2026-05-09/02-fluxos-e-workflows.md)
- `flow-workflows-no-command-shortcuts` — workflows usam prompts em prosa; não citam comandos `/devteam:*` correspondentes — [relatório](2026-05-09/02-fluxos-e-workflows.md)
- `agent-three-reviewers-overlap` — code-reviewer + backend-reviewer + frontend-reviewer compartilham ~80% estrutura (Mindset, Foundational, Routing) — [relatório](2026-05-09/03-agentes-e-skills.md)
- `skill-missing-caching-strategies` — sem skill para Redis/CDN/ETag/cache invalidation — [relatório](2026-05-09/03-agentes-e-skills.md)
- `skill-missing-i18n-l10n` — sem skill para internacionalização — [relatório](2026-05-09/03-agentes-e-skills.md)
- `skill-missing-monorepo-patterns` — sem skill para Turborepo/Nx/pnpm workspaces — [relatório](2026-05-09/03-agentes-e-skills.md)
- `skill-missing-data-migration-zero-downtime` — sem skill para migração zero-downtime / expand-contract / blue-green schema — [relatório](2026-05-09/03-agentes-e-skills.md)
- `skill-missing-resilience-patterns` — sem skill para circuit breaker / retry-backoff / bulkhead — [relatório](2026-05-09/03-agentes-e-skills.md)
- `skill-security-only-checklist` — `skills/security/` tem 1 skill; security-specialist (Opus, 8 áreas) operando sub-suportado — [relatório](2026-05-09/03-agentes-e-skills.md)
- `skill-testing-thin-coverage` — `skills/testing/` tem 2 skills; faltam contract testing, mutation, snapshot, visual-regression — [relatório](2026-05-09/03-agentes-e-skills.md)
- `skill-missing-git-workflow` — sem skill para trunk-based vs gitflow vs GitHub flow — [relatório](2026-05-09/03-agentes-e-skills.md)
- `agent-when-loaded-pattern-only-qa` — bloco `When loaded` só em `qa-specialist`; padrão útil mas não disseminado — [relatório](2026-05-09/03-agentes-e-skills.md)
- `token-reviewer-mindset-block-duplicate` — bloco "Reviewer Mindset" replicado em 3 reviewer agents (~36 linhas raw) — [relatório](2026-05-09/04-economia-tokens.md)
- `token-comments-policy-skill-monolith` — skill `comments-policy` (417 linhas) carregada por 9 agentes mesmo quando só uma seção é necessária — [relatório](2026-05-09/04-economia-tokens.md)
- `token-when-loaded-conditional-blocks` — skills carregadas incondicionalmente (comments-policy, conventional-commits) onde poderiam ser condicionais — [relatório](2026-05-09/04-economia-tokens.md)
- `token-readme-bilingual-dual-source` — README + README.pt-BR somam 1402 linhas em sync manual; opção: fragmentar ou marcar com `<!-- @section: -->` — [relatório](2026-05-09/04-economia-tokens.md)
- `token-foundational-rule-domain-paths-explicit` — itens 5-12 do Foundational Rule em prosa; tabela compacta economiza ~80 linhas — [relatório](2026-05-09/04-economia-tokens.md)
- `token-bilingual-readme-section-fragmentation` — ângulo PT-BR especificamente: README pt-BR pode virar sumário + scripts/readme-sync-check.sh — [relatório](2026-05-09/04-economia-tokens.md)
- `token-project-rules-override-prose-duplicate` — frase "**Project rules override base standards**" repetida em 14 agentes; 1 linha basta — [relatório](2026-05-09/04-economia-tokens.md)
- `token-cicd-skills-shared-structure` — 4 skills `cicd-*` com ~70% concept overlap; extrair `cicd-base/SKILL.md` (~320 linhas) — [relatório](2026-05-09/04-economia-tokens.md)

### 2026-05-08 — terceira passada (foco em scripts duplicados, gaps em workflows, dogfooding)

- `ref-check-updates-script-duplicate` — `scripts/check-updates.sh` é versão obsoleta de `scripts/hooks/pre-tool-use/01-check-updates.sh` — [relatório](2026-05-08/01-referencias-e-consistencia.md)
- `docs-sync-update-flow-claude-md` — `CLAUDE.md` descreve `/devteam:update` rodando dois scripts; o real é um (via `update.sh --check`) — [relatório](2026-05-08/01-referencias-e-consistencia.md)
- `ref-templates-folder-underutilized` — `templates/` tem 1 arquivo; ADR + backlog + docs templates vivem inline em skills — [relatório](2026-05-08/01-referencias-e-consistencia.md)
- `gov-dev-repo-no-stop-dispatcher` — `.claude/settings.json` deste repo registra só `orphan-skill-scan.sh`, não o dispatcher canônico — [relatório](2026-05-08/01-referencias-e-consistencia.md)
- `docs-sync-setup-assistant-audit-folder` — `setup-assistant.md` Step 1b cria `.claude/docs/audit/` mas CLAUDE.md/README não documentam — [relatório](2026-05-08/01-referencias-e-consistencia.md)
- `flow-workflows-no-adr-trigger` — Nenhum dos 5 workflows menciona criação de ADR — [relatório](2026-05-08/02-fluxos-e-workflows.md)
- `flow-workflows-no-session-summary-step` — Nenhum dos 5 workflows tem passo proativo de session-summary — [relatório](2026-05-08/02-fluxos-e-workflows.md)
- `flow-bugfix-doc-vs-command-mismatch` — `workflows/bug-fix.md` mandata `software-architect` para diagnose; `commands/fix.md` pula — [relatório](2026-05-08/02-fluxos-e-workflows.md)
- `flow-maintenance-phase-numbering` — `maintenance.md` salta de `Step 1, Step 2` para `Phase 2` (Phase 1 inexistente) — [relatório](2026-05-08/02-fluxos-e-workflows.md)
- `flow-new-project-database-implicit` — Phase 3 do `new-project.md` não tem passo explícito para `database-specialist` — [relatório](2026-05-08/02-fluxos-e-workflows.md)
- `flow-no-rollback-or-deploy-failure-step` — Workflows não cobrem caminho de rollback/deploy-failure — [relatório](2026-05-08/02-fluxos-e-workflows.md)
- `skill-adr-coverage-only-architect` — Skill `adr` referenciada por 1 agente; deveria estar em backend/database/devops/security — [relatório](2026-05-08/03-agentes-e-skills.md)
- `agent-technical-writer-haiku-mismatch` — `technical-writer` em Haiku, mas produz outputs típicos de Sonnet — [relatório](2026-05-08/03-agentes-e-skills.md)
- `gov-plan-template-vs-skill-duplication` — `templates/plan-template.md` e `skills/shared/plan-mode/SKILL.md` carregam o mesmo formato — [relatório](2026-05-08/03-agentes-e-skills.md)
- `agent-product-analyst-jira-only-tracker` — `product-analyst` cobre só Jira; setup-assistant lista 5+ trackers — [relatório](2026-05-08/03-agentes-e-skills.md)
- `agent-setup-assistant-roles-out-of-order` — Roles ordenadas 1, 3, 2 no `setup-assistant.md` — [relatório](2026-05-08/03-agentes-e-skills.md)
- `gov-stop-dispatcher-self-eat` — Dev-team-agents não dogfooda seu próprio dispatcher de hooks (ângulo feedback operacional) — [relatório](2026-05-08/03-agentes-e-skills.md)
- `token-worktree-block-inlined-7x` — `## Worktree Isolation` (~22 linhas) duplicado em 7 agentes coding — [relatório](2026-05-08/04-economia-tokens.md)
- `token-rest-conventions-inlined-in-backend` — 35+ linhas de REST inline no `backend-developer`; skill `api-design` existe — [relatório](2026-05-08/04-economia-tokens.md)
- `token-sonarqube-detection-block-redundant` — Detecção de SonarQube duplicada em 10 agentes — [relatório](2026-05-08/04-economia-tokens.md)
- `token-architecture-awareness-block-duplicate` — "Architecture Awareness" paralela em backend/frontend developers — [relatório](2026-05-08/04-economia-tokens.md)
- `token-update-script-duplicate-bytes` — `scripts/check-updates.sh` mantido em paralelo com hook canônico (~70 linhas mortas) — [relatório](2026-05-08/04-economia-tokens.md)
- `token-foundational-rule-extension-pattern` — Items 1–4 do Foundational Rule são idênticos em 16 agentes (refinamento) — [relatório](2026-05-08/04-economia-tokens.md)
- `auto-no-orphan-templates-scan` — Sem scan de templates órfãos em `templates/` (adiar até 3+ arquivos) — [relatório](2026-05-08/05-automacao-e-dogfooding.md)
- `auto-no-frontmatter-tools-validator` — Sem validador de `tools:` declarado × usado no corpo — [relatório](2026-05-08/05-automacao-e-dogfooding.md)
- `auto-no-skill-name-uniqueness-check` — Sem checagem de colisão de nome de skill entre categorias — [relatório](2026-05-08/05-automacao-e-dogfooding.md)
- `auto-no-fingerprint-collision-check` — `_index.md` cresce sem checagem de unicidade de fingerprint — [relatório](2026-05-08/05-automacao-e-dogfooding.md)
- `gov-installer-rigor-asymmetry` — Instalador empurra hooks que o próprio repo não consome — [relatório](2026-05-08/05-automacao-e-dogfooding.md)

### 2026-05-07 — segunda passada (foco em comandos, robustez de scripts e modelo)

- `docs-sync-claude-md-package-exclusions` — `install.sh` strippa `.claude/`, `README.md`, `README.pt-BR.md`, `.gitignore` mas o CLAUDE.md não documenta — [relatório](2026-05-07/01-referencias-e-consistencia.md)
- `ref-commit-no-worktree-context` — `commit.md` é o único comando multi-passo que não detecta worktree atual — [relatório](2026-05-07/01-referencias-e-consistencia.md)
- `docs-sync-commands-arguments-table` — Tabela de `$ARGUMENTS` existe apenas em `commit.md` (1/22 comandos) — [relatório](2026-05-07/01-referencias-e-consistencia.md)
- `auto-installer-error-output` — `install.sh` engole stderr do `curl`/`wget` em downloads que falham — [relatório](2026-05-07/01-referencias-e-consistencia.md)
- `flow-commands-par-column-missing` — Comandos com 2+ agentes não usam coluna `Par.` do plan-template — [relatório](2026-05-07/02-fluxos-e-comandos.md)
- `flow-plan-database-conditional` — `database-specialist` é spawn incondicional em `/devteam:plan`, contradizendo a coluna conditional do CLAUDE.md — [relatório](2026-05-07/02-fluxos-e-comandos.md)
- `flow-conditional-spawn-criteria-undefined` — Não há heurística textual/de path para decidir spawn condicional — [relatório](2026-05-07/02-fluxos-e-comandos.md)
- `flow-inherited-no-explicit-await-checkpoint` — `inherited-project.md` não tem checkpoint formal entre fases paralelas — [relatório](2026-05-07/02-fluxos-e-comandos.md)
- `flow-discovery-loop-exit-criteria` — Loop "repeat until scope is 100% closed" sem teto de iterações — [relatório](2026-05-07/02-fluxos-e-comandos.md)
- `agent-setup-assistant-model-mismatch` — `setup-assistant` em Sonnet, mas executa decisões de Opus — [relatório](2026-05-07/03-agentes-e-skills.md)
- `docs-sync-readme-test-skills-clarification` — README não explica complementaridade `test-pyramid` × `test-strategy` — [relatório](2026-05-07/03-agentes-e-skills.md)
- `skill-comments-policy-missing-in-non-coding-agents` — `comments-policy` ausente em 5 agentes que produzem código exemplificativo — [relatório](2026-05-07/03-agentes-e-skills.md)
- `gov-templates-physical-vs-inline` — Templates dispersos entre `templates/*.md` e blocos inline em skills — [relatório](2026-05-07/03-agentes-e-skills.md)
- `skill-pwa-offline-weak-references` — Skills `pwa` e `offline-first` sem load explícito por agente — [relatório](2026-05-07/03-agentes-e-skills.md)
- `token-current-context-block-deduplication` — Bloco "current working context" repetido em 18+ comandos — [relatório](2026-05-07/04-economia-tokens.md)
- `token-agent-path-prefix-redundant` — `.claude/agents/dev-team/` em todas as 40+ linhas de spawn — [relatório](2026-05-07/04-economia-tokens.md)
- `token-graphify-routing-in-project-context` — `project-context` não desvia leituras para Graphify quando disponível — [relatório](2026-05-07/04-economia-tokens.md)
- `token-git-log-window-overshoot` — `git log --oneline -20` é supérfluo; `-10` cobre 80% dos casos — [relatório](2026-05-07/04-economia-tokens.md)
- `token-setup-assistant-conditional-tracker-loading` — `setup-assistant` carrega 9 trackers; deveria carregar 1 sob demanda — [relatório](2026-05-07/04-economia-tokens.md)
- `auto-hook-dispatchers-missing-errexit` — `pre-tool-use.sh` e `stop.sh` usam `set -uo pipefail` (faltando `-e`) — [relatório](2026-05-07/05-robustez-scripts.md)
- `auto-curl-no-timeout-update-check` — `curl` no hook de update sem `--connect-timeout`/`--max-time` — [relatório](2026-05-07/05-robustez-scripts.md)
- `auto-install-no-rollback-on-second-mv-failure` — `install.sh` corrompe instalação se o segundo `mv` falhar — [relatório](2026-05-07/05-robustez-scripts.md)
- `auto-update-no-integrity-check` — Auto-update baixa e executa installer sem SHA256/GPG — [relatório](2026-05-07/05-robustez-scripts.md)
- `auto-session-summary-no-git-detection` — Hook de session-summary não detecta ausência de repo git — [relatório](2026-05-07/05-robustez-scripts.md)
- `auto-check-updates-mkdir-resilience` — `01-check-updates.sh` aborta em FS onde `mkdir` falha — [relatório](2026-05-07/05-robustez-scripts.md)

### 2026-05-06 — `relatorio-auditoria-inicial.md`

- `docs-sync-readme-architecture-skills` — README lista apenas 5 skills de architecture; existem 11 — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `docs-sync-readme-devops-skills` — README omite `graphify-setup`, `vercel`, `sentry`, `sonarqube` da seção de estrutura — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `docs-sync-readme-design-skills` — README descreve apenas `design-system-audit`; existem três skills de design — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `ref-agent-creator-location` — `agent-creator` mora em `.claude/skills/` enquanto `skill-creator` está em `skills/`; inconsistente — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `flow-fullstack-no-workflow-doc` — Existe o slash command `/devteam:fullstack` mas não há `workflows/fullstack.md` — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `flow-parallel-marker-bugfix` — `bug-fix.md` cita execução paralela em prosa, sem usar a coluna `Par.` do `plan-template` — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `agent-setup-assistant-size` — `setup-assistant.md` tem 404 linhas, ultrapassa o limite ~200 do CLAUDE.md — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `agent-frontend-developer-size` — `frontend-developer.md` tem 331 linhas — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `agent-database-specialist-size` — `database-specialist.md` tem 313 linhas — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `agent-backend-developer-size` — `backend-developer.md` tem 286 linhas — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `skill-add-incident-response` — Falta skill de runbook/incident-response — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `skill-add-feature-flags` — Falta skill de gestão de feature flags — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `skill-add-observability-slo` — Falta skill de observabilidade/SLOs — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `skill-add-load-testing` — Falta skill de load/perf testing — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `token-context-loading-dedup` — Cada agente repete a lista de Foundational Rule, redundante com `project-context` — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `token-skill-mention-redundancy` — "Apply skills/shared/token-efficiency/SKILL.md" repetido em todos os agentes consome tokens sem ganho — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `token-foundational-rule-template` — Substituir 12 itens do Foundational Rule por uma única chamada `Load project-context skill` — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `auto-skill-frontmatter-validator` — Falta validador automático de frontmatter de agente/skill — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `auto-redundant-skill-load-scan` — `orphan-skill-scan` não detecta carregamentos duplicados de skill no mesmo agente — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `gov-readme-pt-br-sync-check` — Falta script para validar sincronia README.md ↔ README.pt-BR.md — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `flow-quality-gate-explicit-par-column` — Workflows poderiam usar `Par.` formal do plan-template em todos os pontos paralelos — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `flow-setup-slash-command` — Não existe `/devteam:setup` para invocar `setup-assistant` via slash command — [relatório](2026-05-06/relatorio-auditoria-inicial.md)

---

## Estatísticas

| Data | Sugestões publicadas | Originais (acumulado) | Executadas |
|------|----------------------|-----------------------|------------|
| 2026-05-06 | 22 | 22 | — |
| 2026-05-07 | 25 | 47 | — |
| 2026-05-08 | 28 | 75 | — |
| 2026-05-09 | 35 | 110 | — |
| 2026-05-10 | 34 | 144 | **31** ✅ + 2 ⚠️ partial (2026-05-11) |

> **Instrução para o agente de research:** Ao ler este índice, **exclua da geração** todos os fingerprints marcados com ✅ **Executed** — eles estão implementados no código. Fingerprints ⚠️ **Partial** podem ser repropostos com escopo **mais específico** cobrindo apenas a parte pendente descrita na nota.
