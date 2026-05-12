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
    ↩️ Reverted    — implementado e depois revertido por decisão consciente; NÃO repropostar
    🟢 Resolved    — resolvido por outra mudança correlata (ex.: extração quebrou a necessidade)
    (sem marker)  — sugestão registrada, ainda não implementada
-->

### 2026-05-11 — sexta passada — modo Guardian + 50 sugestões originais (foco em verificar Executed de 2026-05-10, drift README, mobile broken refs, foundational rule overhead)

- `docs-sync-readme-massive-skill-list-drift` — README "Repository Structure" lista 5 architecture skills (existem 24), 9 shared (25), 1 security (8); categorias `mobile` (4) e `database` (9) inteiras ausentes — [relatório](2026-05-11/01-referencias-e-consistencia.md)
- `ref-orphan-scan-only-checks-agents-not-commands-or-workflows` — `scripts/orphan-skill-scan.sh` varre só `agents/`; skills carregadas exclusivamente por commands/workflows exigem registro manual em CLAUDE.md — [relatório](2026-05-11/01-referencias-e-consistencia.md)
- `ref-mobile-workflow-missing-despite-command` — `/devteam:mobile` declarado mas `workflows/mobile.md` não existe; simetria com `/devteam:fullstack`/`refactor`/`review` quebrada — [relatório](2026-05-11/01-referencias-e-consistencia.md)
- `ref-installer-strips-strategy-pattern-mismatch-vs-changelog` — tabela "Package exclusions" no CLAUDE.md mistura allowlist (KEEP_ROOT) com explicit strip sem distinguir mecanismo — [relatório](2026-05-11/01-referencias-e-consistencia.md)
- `ref-commands-two-without-current-context-undocumented` — `commit.md` e `update.md` não carregam `current-context` por design; exceção não documentada — [relatório](2026-05-11/01-referencias-e-consistencia.md)
- `ref-templates-folder-still-single-file-after-three-passes` — `templates/` tem 1 arquivo desde 2026-05-03; ADR/backlog/runbook templates continuam inline em skills — [relatório](2026-05-11/01-referencias-e-consistencia.md)
- `ref-claude-md-mentions-agents-creator-as-claude-skills-path` — CLAUDE.md mistura paths repo (`skills/skill-creator/`) e pós-install (`.claude/skills/agent-creator/`) na mesma tabela — [relatório](2026-05-11/01-referencias-e-consistencia.md)
- `ref-stop-hook-04-notifier-undocumented-in-changelog-unreleased` — sub-script `04-notifier.sh` e formato DEV TEAM AGENTS não aparecem na seção Unreleased do CHANGELOG — [relatório](2026-05-11/01-referencias-e-consistencia.md)
- `ref-database-specialist-still-258-lines-after-engine-split` — apesar de 7 engines extraídas, agente caiu só de 313 → 252 linhas; resta heurística N+1, ER modeling, migration patterns inline — [relatório](2026-05-11/01-referencias-e-consistencia.md)
- `ref-no-orphan-template-scan-with-zero-templates-still-pending` — scan condicionado a "3+ arquivos"; será necessário ao migrar templates inline → físicos — [relatório](2026-05-11/01-referencias-e-consistencia.md)
- `ref-graphify-setup-skill-referenced-by-name-not-path-blind-spot` — `setup-assistant.md:134` invoca por nome (`graphify-setup`); 99% das skills usam path completo — [relatório](2026-05-11/01-referencias-e-consistencia.md)
- `docs-sync-claude-md-package-exclusions-includes-LICENSE-without-marking` — `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md` listados como stripados mas ausentes da seção File Structure — [relatório](2026-05-11/01-referencias-e-consistencia.md)
- `flow-command-mobile-md-missing-but-claude-md-claims-it` — **HIGH** — `/devteam:mobile` declarado em CLAUDE.md:138 mas `commands/mobile.md` não existe (broken reference pública) — [relatório](2026-05-11/02-fluxos-e-workflows.md)
- `flow-no-workflow-command-shortcuts-for-fullstack-refactor-review` — `workflows/fullstack.md|refactor.md|review.md` existem mas não há `/devteam:workflow-fullstack|refactor|review` correspondentes — [relatório](2026-05-11/02-fluxos-e-workflows.md)
- `flow-spawn-classifier-only-loaded-by-plan-command` — `/devteam:backend|frontend|fullstack|refactor|fix|review|mobile` têm spawn condicional mas não carregam a skill — [relatório](2026-05-11/02-fluxos-e-workflows.md)
- `flow-claude-md-workflows-list-incomplete` — File Structure do CLAUDE.md menciona só 5 workflows; existem 8 (faltam fullstack/refactor/review) — [relatório](2026-05-11/02-fluxos-e-workflows.md)
- `flow-no-pre-spawn-installation-freshness-check` — commands não verificam frescor da instalação antes de spawn; PreToolUse TTL de 24h pode estar atrasado — [relatório](2026-05-11/02-fluxos-e-workflows.md)
- `flow-commit-command-no-type-check-or-tests-gate` — lint gate existe; falta type-check (`tsc --noEmit`, `mypy`) — [relatório](2026-05-11/02-fluxos-e-workflows.md)
- `flow-refactor-workflow-no-rollback-tag-recommendation` — `workflows/refactor.md` sem Step "Tag rollback point" (`pre-refactor-<context>`) — [relatório](2026-05-11/02-fluxos-e-workflows.md)
- `flow-security-patch-no-mttr-tracking` — workflow security-patch não captura `started_at`/`deployed_at` para MTTR (SOC2/ISO 27001) — [relatório](2026-05-11/02-fluxos-e-workflows.md)
- `flow-no-adr-command-despite-script` — `/devteam:adr` não existe; ADR criação exige `bash scripts/new-adr.sh` literal — [relatório](2026-05-11/02-fluxos-e-workflows.md)
- `flow-pr-command-no-draft-mode-flag` — `commands/pr.md` sem flag `draft` para PR como rascunho — [relatório](2026-05-11/02-fluxos-e-workflows.md)
- `flow-no-cross-link-between-workflows-still` — 8 workflows sem 1 linha "Next step" cross-link; reformulação de `flow-workflows-no-cross-linking` (2026-05-09) com escopo mínimo — [relatório](2026-05-11/02-fluxos-e-workflows.md)
- `flow-stop-hook-04-notifier-no-gate-runs-every-session` — `02/03` gateadas por changes; `04-notifier.sh` roda em toda Stop; usar `.notifier-state` `last_shown_date` — [relatório](2026-05-11/02-fluxos-e-workflows.md)
- `flow-discovery-loop-still-no-iteration-cap` — discovery sem teto de iterações; variante mais específica do antigo `flow-discovery-loop-exit-criteria` — [relatório](2026-05-11/02-fluxos-e-workflows.md)
- `agent-mobile-test-specialist-missing-asymmetric-with-backend-frontend` — backend/frontend têm test-specialist; mobile não; Detox/Maestro/Appium sem owner — [relatório](2026-05-11/03-agentes-e-skills.md)
- `agent-setup-assistant-still-306-lines-after-multiple-extractions` — caiu de 404 → 306; ainda acima do limite ~200; tracker MCP table (~25l) e update flow inline podem virar skills — [relatório](2026-05-11/03-agentes-e-skills.md)
- `skill-reviewer-base-foundational-rule-overlap-with-project-context` — `reviewer-base` repete steps 1-3, 5, 7 de `project-context` quando ambas são carregadas pelos 3 reviewers — [relatório](2026-05-11/03-agentes-e-skills.md)
- `agent-product-analyst-still-no-bash-tool-after-jira-skill-load` — `product-analyst` carrega jira skill mas frontmatter sem `Bash`; impede `gh issue create` fallback — [relatório](2026-05-11/03-agentes-e-skills.md)
- `skill-release-prep-missing-despite-mentioned-in-changelog-1.2.0` — CHANGELOG menciona "Release preparation skill" em 1.2.0; arquivo `release-prep` não existe em `skills/` — [relatório](2026-05-11/03-agentes-e-skills.md)
- `skill-discovery-mode-loaded-by-three-agents-without-divergence-check` — `discovery-mode` carregada por setup-assistant/architect/analyst sem persistência; outputs divergem — [relatório](2026-05-11/03-agentes-e-skills.md)
- `skill-monitoring-444-lines-over-limit-needs-references-extraction` — maior skill do repo (444 linhas); `references/` existe mas vazio; quebrar em logs/metrics/traces sub-skills — [relatório](2026-05-11/03-agentes-e-skills.md)
- `skill-sonarqube-435-lines-overlap-with-reviewer-base-detection-block` — detection block do reviewer-base replica trigger interno da sonarqube — [relatório](2026-05-11/03-agentes-e-skills.md)
- `agent-mobile-developer-no-detox-or-maestro-test-routing` — mobile-developer não roteia para Detox/Maestro/Appium; falha cascateia sem `mobile-test-specialist` — [relatório](2026-05-11/03-agentes-e-skills.md)
- `skill-missing-prompt-engineering-or-llm-integration` — sem skill para integração LLM no produto do usuário (RAG, embeddings, vector DB, prompt versioning) — [relatório](2026-05-11/03-agentes-e-skills.md)
- `agent-technical-writer-haiku-mismatch-resolved-by-diataxis-extraction` — antigo `agent-technical-writer-haiku-mismatch` (2026-05-08) torna-se decisão consciente após diataxis-framework extract; Haiku adequado — [relatório](2026-05-11/03-agentes-e-skills.md)
- `skill-current-context-not-loaded-by-fix-or-refactor-workflows` — workflows não carregam `current-context` standalone; usuário que rode workflow sem command wrapper perde detecção — [relatório](2026-05-11/03-agentes-e-skills.md)
- `skill-graphify-setup-no-conditional-by-project-language` — skill 265 linhas sem gate por linguagem/tamanho; setup pergunta sobre Graphify mesmo em projeto puramente docs — [relatório](2026-05-11/03-agentes-e-skills.md)
- `token-git-log-window-still-20-after-three-passes` — `git log --oneline -20` em 10 agentes; ~1.000 tokens economizados se for `-10`; variante do antigo `token-git-log-window-overshoot` — [relatório](2026-05-11/04-economia-tokens.md)
- `token-foundational-rule-424-lines-across-17-agents` — Foundational Rule inline soma 424 linhas; média 24 lines/agente; maior `software-architect` (57); ~1.700 tokens economizados/sessão multi-agente — [relatório](2026-05-11/04-economia-tokens.md)
- `token-worktree-isolation-block-7-lines-x-8-agents` — bloco Worktree de 7 linhas em 8 agentes = 56 dup; mobile-developer adicionado (era 7×; hoje 8×); variante do antigo `token-worktree-block-inlined-7x` — [relatório](2026-05-11/04-economia-tokens.md)
- `token-architecture-awareness-block-still-duplicated` — backend/frontend/mobile devs inlineiam Architecture Awareness; ~44 linhas dup; variante de fingerprint anterior — [relatório](2026-05-11/04-economia-tokens.md)
- `token-changelog-already-growing-and-not-extracted-by-release` — CHANGELOG cresce ~80 linhas/mês sem rotação; archive sugerido a 300 linhas — [relatório](2026-05-11/04-economia-tokens.md)
- `token-readme-bilingual-dual-source-734-lines-each` — README + README.pt-BR somam 1.474 linhas; CI valida por threshold de 5% (heurística rasa); variante quantificada do antigo `token-readme-bilingual-dual-source` — [relatório](2026-05-11/04-economia-tokens.md)
- `token-skill-loads-via-table-vs-prose-inconsistent` — alguns agentes usam tabelas de skill loads; outros prosa; `database-specialist` é all-table; padronização economiza parsing — [relatório](2026-05-11/04-economia-tokens.md)
- `token-claude-md-672-chars-package-exclusions-table-redundant-vs-installer` — tabela de 13 exclusões no CLAUDE.md duplica `KEEP_ROOT` do install.sh; substituir por 1 linha + link — [relatório](2026-05-11/04-economia-tokens.md)
- `token-plan-mode-skill-131-lines-loaded-by-7-agents-unconditionally` — `plan-mode` skill (131 linhas) carregada por 7 agentes no startup; lazy-load para "quando for gerar plano" economiza ~2.750 tokens — [relatório](2026-05-11/04-economia-tokens.md)
- `token-orphan-scan-output-format-verbose-when-clean` — `orphan-skill-scan: clean ✓` em modo non-quiet; baixa prioridade — [relatório](2026-05-11/04-economia-tokens.md)
- `token-three-reviewers-still-share-80-percent-structure` — 3 reviewers somam 624 linhas; mesmo após reviewer-mindset extracted, ainda ~100 linhas duplicadas; variante do antigo `agent-three-reviewers-overlap` — [relatório](2026-05-11/04-economia-tokens.md)
- `token-changelog-unreleased-section-grows-without-rollover` — Unreleased acumula 25 items sem cross-link aos fingerprints do `_index.md`; HTML comments `<!-- fingerprint: ... -->` sugerido — [relatório](2026-05-11/04-economia-tokens.md)

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
- `flow-update-command-no-rollback-path` — `/devteam:update` não tem `--rollback`; `INSTALL_DIR.old.$$` é deletado imediatamente após swap — [relatório](2026-05-10/02-fluxos-e-workflows.md) — ↩️ **Reverted:** 2026-05-11 (commit `fc57a86` removeu a feature `.previous/` por causar pasta órfã pós-update; rollback foi avaliado e descartado pelo time. **NÃO repropostar.**)
- `flow-commit-no-pre-commit-gate` — `/devteam:commit` não roda linters/formatters antes de commitar — [relatório](2026-05-10/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-05-11
- `flow-workflows-no-failure-recovery` — Workflows não definem caminho de falha intermediária (review loop infinito, abort no meio, commit travado) — [relatório](2026-05-10/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-05-11
- `flow-pr-command-no-template-file-link` — `/devteam:pr` produz prosa sem detectar `.github/PULL_REQUEST_TEMPLATE.md` — [relatório](2026-05-10/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-05-11
- `flow-no-stale-branch-detection` — Nenhum workflow detecta branch atrasada de main antes de operar — [relatório](2026-05-10/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-05-11
- `flow-setup-no-docker-compose-version-detection` — `setup-assistant` assume `docker compose` (V2); não testa fallback `docker-compose` (V1) — [relatório](2026-05-10/02-fluxos-e-workflows.md) — ✅ **Executed:** 2026-05-11
- `flow-no-merge-conflict-preflight` — Workflows fix/refactor não rodam `git merge-tree` para detectar conflito potencial com main — [relatório](2026-05-10/02-fluxos-e-workflows.md)
- `agent-database-specialist-no-per-engine-skills` — `database-specialist` (272 linhas) cobre 6+ engines inline; padrão `cicd-base+variantes` não replicado para database — [relatório](2026-05-10/03-agentes-e-skills.md) — ⚠️ **Partial:** 2026-05-11 (todas as 7 engines — `postgres`, `mysql`, `mongodb`, `redis`, `sqlserver`, `cassandra`, `sqlite` — criadas e wireadas em `database-specialist.md:57-63`; somente o **split do agente** continua pendente — vide novo fingerprint `ref-database-specialist-still-258-lines-after-engine-split` em 2026-05-11)
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

| Data | Sugestões publicadas | Originais (acumulado) | Executadas / Revertidas |
|------|----------------------|-----------------------|--------------------------|
| 2026-05-06 | 22 | 22 | — |
| 2026-05-07 | 25 | 47 | — |
| 2026-05-08 | 28 | 75 | — |
| 2026-05-09 | 35 | 110 | — |
| 2026-05-10 | 34 | 144 | **30** ✅ + 2 ⚠️ partial + **1 ↩️ reverted** (verificado por Guardian em 2026-05-11) |
| 2026-05-11 | 50 + auditoria Guardian | 194 | — |

> **Instrução para o agente de research:** Ao ler este índice, **exclua da geração**:
> - todos os fingerprints marcados com ✅ **Executed** — estão implementados;
> - todos os fingerprints marcados com ↩️ **Reverted** — foram implementados e depois removidos por decisão consciente;
> - todos os fingerprints marcados com 🟢 **Resolved** — foram resolvidos por outra mudança.
>
> Fingerprints ⚠️ **Partial** podem ser repropostos com escopo **mais específico** cobrindo apenas a parte pendente descrita na nota.
>
> **Modo Guardian (opcional):** ao verificar marcações ✅ Executed, cruzar com `git log --since="<data-da-marcação>"` para detectar reverts no mesmo dia. Marcação pode ser corrigida para ↩️ Reverted se aplicável.
