# Fase 1 e 1b — Verificação Guardiã — 2026-10-24

**Baseline:** `HEAD` = `b64428b` · **Baseline anterior:** `bb0e883` · delta de **98 commits e 704
arquivos**.

> **Nota de método — a árvore estava suja durante todo o pass.** No momento da Fase 0 o working
> tree carregava **79 arquivos modificados (3.539 inserções, 201 remoções) e 9 não rastreados**,
> incluindo `CLAUDE.md`, os dois `README`, 7 agentes, 6 comandos e 19 skills. Toda evidência deste
> relatório vem de `git show HEAD:<path>`, **nunca do disco**. A distinção não é acadêmica: no
> disco `skills/shared/docs-templates/SKILL.md` tem 301 linhas e manda rodar
> `bash .dev-team-agents/scripts/doc-path.sh`; no `HEAD` tem 153 linhas e não menciona esse script
> (que também só existe no disco). Auditar o disco teria produzido um achado HIGH inteiramente
> falso.

---

## Critério de amostragem

Conjunto verificável (✅ Executed + ⚠️ Partial) = **152** de 297 fingerprints vivos. Acima do
limiar de 60, logo: **todos os HIGH e MEDIUM-HIGH (42)** mais **amostra aleatória de 30% do
restante (33 de 110, `seed=20261024`)** → **75 de 152 verificados (49,3%)**.

| Severidade | No conjunto verificável | Verificados |
|---|---|---|
| HIGH | 20 | 20 (100%) |
| MEDIUM-HIGH | 22 | 22 (100%) |
| MEDIUM | 48 | 14 (29%) |
| LOW-MEDIUM | 42 | 13 (31%) |
| LOW | 20 | 6 (30%) |
| **Total** | **152** | **75 (49,3%)** |

## Placar

| Marca verificada | Nº | % |
|---|---|---|
| ✅ Feito | 61 | 81,3% |
| 🟢 Resolvido por outra via | 1 | 1,3% |
| 🟡 Parcialmente feito | 9 | 12,0% |
| 🔴 Não feito | 4 | 5,3% |
| **Confirmado (✅ + 🟢)** | **62** | **82,7%** |
| **Reaberto NOVO neste pass** | **0** | **0%** |

**As 13 divergências já estavam registradas.** Nenhuma das 4 🔴 e nenhuma das 9 🟡 é nova: todas
carregam anotação de um pass anterior e foram **reconfirmadas** contra o `HEAD` atual. O limiar de
escalonamento (15% da amostra em 🔴) não foi atingido, nem de longe — a taxa de reabertura nova é
zero pelo segundo pass consecutivo.

---

## 🔴 Reconfirmadas (4) — todas já reabertas em passes anteriores

### `flow-telemetry-pre-tool-use-02-runs-on-every-tool-call-without-batching-or-deduplication…`
- Reaberta em 2026-07-31, depois marcada 🟢. Estado atual: o alvo foi renomeado para
  `scripts/hooks/pre-tool-use/02b-telemetry.sh` e sobrevive no `HEAD`. Sem mudança desde a
  anotação; nada a reescrever.

### `auto-new-adr-sh-sed-title-substitution-breaks-on-pipe-ampersand-backslash…`
- 🔴 desde 2026-09-18. `scripts/new-adr.sh` foi tocado no delta
  (`a251a4a 2026-10-18 fix(hooks): clear the shellcheck findings in the lint resolver and new-adr.sh`),
  mas o commit trata de shellcheck, não do escape do título. A marca ✅ de 2026-07-31 segue
  incorreta.

### `agent-software-architect-foundational-rule-51-lines-2x-avg`
- 🔴 desde 2026-08-21. **Evidência no HEAD:** `agents/software-architect.md` — bloco
  `## Foundational Rule` com **43 linhas**, contra média de **20,7** nos 18 agentes. Encolheu de 51
  para 43, mas segue o maior da árvore e >2× a média. A marca ✅ continua errada.

### `token-claude-md-426-lines-still-monolithic-three-extractable-blocks…`
- 🔴/🟡 desde 2026-07-31, reconfirmada em 4 passes. **Evidência no HEAD:** `CLAUDE.md` = **582
  linhas** (registro: 426; medição de 2026-10-17: 678) com `CLAUDE-md/` já em **8 fragmentos**. O
  arquivo continua monolítico; a extração prometida nunca cobriu os blocos citados.

---

## 🟡 Reconfirmadas (9) — sub-escopo pendente inalterado

| Fingerprint | Sub-escopo que falta, no HEAD |
|---|---|
| `flow-size-limits-sh-ci-only-warn-only-not-in-stop-dispatcher…` | Metade entregue: `helpers/size-limits.sh` é **bloqueante** em CI (`.github/scripts/ci/01-lint.sh:91` — `blocking "size-limits" bash helpers/size-limits.sh`). A outra metade não: `scripts/hooks/stop/` tem 16 sub-scripts e **nenhum** chama `size-limits.sh` |
| `auto-update-no-integrity-check` | Integridade de **transporte** entregue; autenticidade não. `scripts/lib/installer-fetch.sh:40` admite em comentário: "project publishes no signatures and no out-of-band digests today" |
| `ref-notification-system-content-triplicated…` | A tabela canônica migrou para `CLAUDE-md/hooks.md`, mas `CLAUDE-md/notifications.md:114` ainda carrega uma seção "Stop Sub-script Convention" própria |
| `ref-agent-creator-location` | `agent-creator` e `skill-creator` agora coabitam em `.claude/skills/`, mas o destino de empacotamento segue documentado só no relatório irmão |
| `token-review-shared-skills-reloaded-by-router-then-each-specialist…` | `commands/review.md:37` manda cada spawn carregar `review-result/SKILL.md` individualmente; não há contexto compartilhado entre os spawns |
| `token-sonarqube-detection-block-redundant` | **9 agentes** ainda citam SonarQube no corpo além de `skills/shared/project-context/SKILL.md` (registro: 11 cópias; 2 removidas) |
| `token-current-context-block-deduplication` | Colapsado para 1 linha, mas ainda copiado em **34 dos 40** comandos, em **4 redações distintas** |
| `token-skill-loads-via-table-vs-prose-inconsistent` | Tabela e prosa seguem coexistindo sem regra escrita |
| `flow-merge-md-rebases-onto-target-while-delegating-to-base-step-8` | `commands/merge.md:33` resolve o conflito em prosa ("any rebase goes onto the target, not `<b>`"), mas `:46` continua delegando inteiro ao step 8 da skill, que rebaseia na base |

---

## ✅ Confirmadas — destaques da amostra

Os 20 HIGH e 22 MEDIUM-HIGH foram verificados integralmente. Amostra da evidência:

| Fingerprint | Evidência no `HEAD` = `b64428b` |
|---|---|
| `ref-docs-agents-md-model-column-wrong…` | `docs/agents.md:17` — a coluna Model não existe mais: `\| Agent \| Role \| Phase \| Tier \|`. O incidente virou comentário de gate em `.github/scripts/ci/02-readme-sync.sh:18` |
| `ref-claude-md-183-code-reviewer-roles…` | `CLAUDE.md:79` — "`code-reviewer` always — when it classifies the diff as `BOTH`, spawn `backend-reviewer` and `frontend-reviewer`". Casa com a implementação |
| `ref-telemetry-honors-pref-but-pref-defaults-true-on-fresh-install…` | `scripts/install.sh:1204` pergunta (`Enable anonymous telemetry? [Y/n]`) e `:1218` **desabilita** quando não há terminal |
| `flow-helpers-archive-index-sh-orphan-of-hook…` | `scripts/hooks/stop/99b-archive-index.sh` existe e está no dispatcher |
| `gov-telemetry-send-sh-posthog-key-comments-self-contradict…` | `scripts/helpers/telemetry-send.sh:28-35` — comentário único e coerente, sem TODO pendente |
| `flow-stop-dispatcher-globs-all-sh-no-allowlist…` | `scripts/hooks/stop.sh:62` — `SUBSCRIPT_RE='^[0-9]{2}[a-z]?-[a-z0-9]([a-z0-9-]*[a-z0-9])?\.sh$'`; nomes fora do padrão são pulados |
| `flow-readme-sync-ci-hardcodes-three-doc-pairs…` | `.github/scripts/ci/02-readme-sync.sh:13-14,211` — pares **descobertos** por `find . -name '*.pt-BR.md'` |
| `agent-security-specialist-body-…-bandit-composer-npm-trivy` | Zero ocorrências de `bandit\|trivy\|composer audit\|npm audit` em `agents/security-specialist.md` |
| `agent-backend-developer-integration-awareness-section-duplicates…` | `agents/backend-developer.md:70-74` — virou tabela `Detection signal → Skill to load` |
| `agent-frontend-test-specialist-…-renderhook…` | Zero ocorrências de `renderHook\|withSetup\|testing-library` |
| `agent-code-reviewer-router-has-ten-structural-review-categories…` | `agents/code-reviewer.md:71` — `## Router Responsibilities` com 3 itens; as 10 categorias sumiram |
| `token-foundational-rule-424-lines-across-17-agents` | **18 de 18** agentes delegam a `skills/shared/project-context/SKILL.md`; o total caiu de 384 linhas duplicadas para **371 linhas role-specific**. `CHANGELOG.md:1938` documenta a delegação |
| `ref-tool-map-tool-rewrites-loaded-but-never-emitted…` | `scripts/lib/render_provider.py:875,905,932` — `apply_tool_rewrites` é efetivamente chamado por provider |
| `flow-pre-tool-use-dispatcher-sigpipe-141-masks-02c-block` | `scripts/hooks/pre-tool-use.sh:21` documenta e trata o SIGPIPE |
| `flow-merge-md-branch-and-tree-resolved-before-worktree-detection` | `commands/merge.md:17` — "Step 1 — Resolve the worktree session, **then** the branches" |
| `skill-orchestration-two-sections-both-numbered-check-5…` | `skills/architecture/orchestration/SKILL.md:258,278` — as referências cruzadas a "check 5" resolvem sem ambiguidade |
| `token-two-schedulewakeup-poll-loops-same-spawn-round…` | `skills/shared/work-feedback/SKILL.md:58` — "this loop is the **only** `ScheduleWakeup` loop for the round" |
| `agent-worktree-cascade-delegates-to-unshipped-claude-md` | `agents/mobile-developer.md:40` delega a `skills/shared/worktree/SKILL.md` § Decision Cascade |
| `skill-spec-gate-scope-lock-hard-gate-unreachable…` | `skills/shared/spec-gate/SKILL.md:107` — `## Scope Lock — Execution Agents`, alcançável por **9** agentes |
| `ref-comments-policy-routing-table-points-to-sections-dir…` | O diretório `skills/shared/comments-policy/sections/` foi criado (4 arquivos); a tabela `:93-96` resolve |
| `auto-stop-03c-reuse-lint-gates-on-csv-registry…` | `scripts/hooks/stop/03c-reuse-lint.sh:22` — `REGISTRY_REL="docs/development/reuse-guidelines.md"` |
| `auto-install-sh-bash-source-fallback-resolves-to-cwd…` | `scripts/install.sh:55-59` — só um `BASH_SOURCE` que nomeia arquivo real conta |
| `auto-ci-never-executes-install-sh-nor-new-adr-sh…` | `.github/workflows/ci.yml:269` — job "Install into fixture project"; mais `:281` "Slim install + provider bootstrap" e `tests/test_install_cli.py`, `tests/test_installer_gate.py` |

---

# FASE 1b — Validade dos achados abertos

**Conjunto aberto:** 118 fingerprints sem marcador. **Cobertura: 118 de 118 (100%).**

Método em duas camadas. Primeiro, mecânica: para cada fingerprint, resolver o campo `alvo:` (ou o
primeiro caminho citado na descrição — 116 dos 118 resolveram), checar existência no `HEAD` e
cruzar com os 704 arquivos do delta. **Nenhum alvo deixou de existir** (zero candidatos a ⚰️) e
**37 alvos foram tocados pelo delta** — esses, e só esses, podiam ter sido corrigidos de passagem.
Segundo, verificação individual dos 37 contra o `HEAD`.

## Mortalidade: 1 de 118 = **0,85%**

### 🟢 Resolvido

- `flow-claude-md-no-agent-command-list-says-seven-omits-push-and-merge` — **🟢 Resolved:**
  2026-10-24 — resolvido no delta `bb0e883..b64428b`. O parágrafo de `CLAUDE.md` que enumerava
  sete comandos sem agente e afirmava "All seven name technical-writer" não existe mais; a lista
  canônica vive agora em `scripts/lib/commands.json:7` (`_filler_agent_note`, **nove** comandos) e
  em `CLAUDE-md/commands.md:62,64`, que trata `/devteam:up` e `/devteam:down` à parte. As duas
  afirmações incompatíveis deixaram de coexistir.

### Os outros 36 alvos tocados seguem reproduzindo

Tocar o arquivo não corrigiu o achado. Verificação individual no `HEAD`:

| Fingerprint (abrev.) | Estado no `HEAD` |
|---|---|
| `agent-devops-specialist-core-expertise-declares-primary-docker…` | `agents/devops-specialist.md:46` — "**Primary**: Docker" intacto |
| `docs-sync-claude-md-…-skill-desc-strict-false…` | `CLAUDE.md:158` diz `SKILL_DESC_STRICT=false`; `helpers/agent-lint.sh:98` diz `SKILL_DESC_STRICT=true`. Contradição viva |
| `docs-sync-claude-md-…-all-devteam-commands-load-current-context…` | `CLAUDE.md:247` "All `/devteam:*` commands" vs. `CLAUDE-md/commands.md:56` "These six are the complete list". A contradição apenas **mudou de arquivo** |
| `docs-sync-reports-index-md-…-legend-comment-claims-all-131-entries-unmarked` | O comentário de legenda segue afirmando 131 entradas sem marcador, contra 297 linhas e 192 marcadores |
| `token-interaction-patterns-209-lines-loaded-unconditionally…` | **318 linhas** (registro: 209) |
| `docs-sync-hooks-md-…-full-suite-guard-examples-predate-wrapper-detection` | `CLAUDE-md/hooks.md:78` ainda exemplifica só runners nomeados (`pytest`, `vendor/bin/phpunit`); a classe de wrappers opacos (`make`, `composer`) não aparece |
| `token-project-context-restates-scoped-test-exception-table…` | `skills/shared/project-context/SKILL.md:269` — "Do not work from this table alone" |
| `docs-sync-readme-command-table-omits-devteam-install…` | 0 ocorrências de `devteam:install` em `README.md` e `README.pt-BR.md`; 40 comandos na árvore |
| `ref-three-pointers-to-claude-md-hook-subscript-convention-moved…` | `scripts/hooks/stop.sh:58` aponta para `CLAUDE.md, "Stop Hook Sub-script Convention"`; a seção vive em `CLAUDE-md/hooks.md:21` |
| `flow-learn-nudge-has-no-canonical-skill-home-three-inline-copies` | 3 cópias: `commands/learn.md`, `commands/merge.md`, `skills/shared/feature-learn/SKILL.md` |
| `flow-pr-md-default-branch-falls-back-to-global-config-then-literal-main` | `commands/pr.md:27` — `\|\| echo "main"` |
| `docs-sync-session-start-comment-cites-nonexistent-02b-full-suite…` | `scripts/hooks/session-start.sh:249` cita `pre-tool-use/02b-full-suite-guard.sh`; o arquivo é `02c-` |
| `auto-adr-gap-check-dependency-signal-blind-to-staged-and-committed` | Zero ocorrências de `diff --cached` em `scripts/hooks/stop/03e-adr-gap-check.sh` |
| `flow-review-command-writes-and-commits-while-documented-as-read-only` | `commands/review.md:70` — "execute the changes directly (edit files, create commits…)" |
| `docs-sync-claude-md-coding-agents-list-omits-seo-specialist` | Lista inalterada |
| `ref-command-description-duplicated-frontmatter-vs-commands-json` | **40 de 40** descrições divergem entre o frontmatter e `scripts/lib/commands.json` |
| `docs-sync-readme-ptbr-agents-link-points-to-english-doc` | `README.pt-BR.md:15` aponta para `docs/agents.pt-BR.md` (correto) mas `:274` ainda aponta para `docs/agents.md` |
| `agent-docs-sync-task-closure-missing-mobile-devops` | 0 ocorrências de `docs-sync` em `agents/mobile-developer.md` e `agents/devops-specialist.md` |
| `token-checks-list-loads-all-three-provider-blocks…` | **791 linhas** (registro: 681; 2026-10-17: 715) |
| `token-fix-patterns-517-lines-loaded-whole…` | **622 linhas** (registro: 517) |
| `docs-sync-telemetry-fresh-install-default-documented-true…` | `CLAUDE.md:294` diz que `telemetry` "default to `true` in a fresh file"; `scripts/install.sh:1218` desabilita no caminho não-interativo |
| `agent-tracker-monoculture-jira-in-eleven-bodies…` | **13 agentes** citam Jira (registro: 11) |
| `agent-project-context-delegation-claims-recent-git-log-absent…` | **0** ocorrências de `git log` em `skills/shared/project-context/SKILL.md` |
| `token-151-skills-flat-symlinked-into-claude-skills…` | **156** SKILL.md na árvore; `scripts/install.sh:35` segue com `SKILLS_TARGET="$PROJECT_ROOT/.claude/skills"` plano |
| `docs-sync-user-data-keep-root-omits-plugins…` | `CLAUDE-md/user-data.md` — 0 ocorrências de `plugins` na tabela `KEEP_ROOT` |
| `ref-hooks-md-library-rows-omit-data-dirs-sh…` | `CLAUDE-md/hooks.md` lista `shipped-lint.sh`, `touched-paths.sh`, `warn-once.sh`; **não** lista `data-dirs.sh` |
| `token-pretooluse-04-task-board-13-forks-before-marker-exit` | **Re-ancorado.** O script foi reescrito no delta (`b36ab51`, `6d4e002`) e ganhou pré-gates puramente bash, mas `:97-98` ainda faz `source task-board.sh` + `devteam_task_board_init` **antes** do teste de marcador em `:102`. Antes era `:88` vs. `:49` |
| `token-wiki-retrieval-index-…-read-whole-by-18-agents` | Índice intacto |
| `auto-03f-spec-lint-warn-signature-omits-worktree-root` | `scripts/hooks/stop/03f-spec-lint.sh:76` — `devteam_warn_once .spec-lint-warned "$SIGNATURE"`, assinatura inalterada |
| `auto-warn-once-reset-never-called-by-03e-and-03f` | Nenhum reset em `03f-spec-lint.sh` |
| `token-orchestration-skill-377-lines-…-no-references-dir` | **402 linhas**, ainda sem `references/` (registro: 377; 2026-10-17: 391) |
| …e mais 5 de docs/hooks sem mudança material | — |

## Fingerprints abertos que **mediram pior** que no registro (8)

| Fingerprint | No registro | No `HEAD` |
|---|---|---|
| `token-interaction-patterns-…` | 209 linhas | **318** |
| `token-checks-list-…` | 681 linhas | **791** |
| `token-fix-patterns-517-lines-…` | 517 linhas | **622** |
| `token-orchestration-skill-377-lines-…` | 377 linhas | **402** |
| `token-claude-md-426-lines-…` (🔴) | 426 linhas | **582** |
| `agent-tracker-monoculture-jira-in-eleven-bodies` | 11 agentes | **13** |
| `token-151-skills-flat-symlinked-…` | 151 skills | **156** |
| `ref-command-description-duplicated-frontmatter-vs-commands-json` | divergência parcial | **40 de 40** |

## Leitura

Mortalidade de **0,85%** com um delta de 704 arquivos. Diferente dos passes de agosto/setembro,
este zero **não** é imobilidade: 37 dos 118 alvos abertos foram efetivamente tocados por 98
commits, e 36 deles seguem reproduzindo. O banco está vivo e as correções de passagem são raras —
o que o repositório entrega é funcionalidade nova (trace de execução, loop de otimização, board de
tarefas, ambiente local), não a dívida registrada. Oito itens abertos **cresceram** desde o
registro; nenhum encolheu.
