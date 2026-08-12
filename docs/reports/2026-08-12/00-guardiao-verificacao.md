# Auditoria Guardiã — Fases 1 e 1b — 2026-08-12

**Baseline:** `HEAD` = `07e0725` · **Baseline anterior:** `f54569a`

O delta desde o baseline anterior é grande: **187 arquivos, +10.487 / −1.431 linhas**, ~2 semanas de
trabalho (2026-08-01 → 2026-08-11). Isso reordena a prioridade deste pass: a maior parte das
marcações ✅ foi aplicada em 2026-07-31 e já verificada pelo pass guardião daquele dia; o valor novo
aqui é (a) confirmar que essas marcações **sobreviveram ao delta** sem reversão silenciosa e (b)
detectar quais achados **abertos/reabertos foram fechados de passagem** pelo delta.

---

## FASE 1 — Modo Guardião

### Amostragem e cobertura

O conjunto verificável (✅ Executed + ⚠️ Partial) excede 60 itens (≈124). Critério aplicado, conforme
a regra de amostragem:

- **Todos os HIGH (11) e MEDIUM-HIGH (7)** — verificados por relocalização de símbolo no `HEAD`
  (não por linha antiga) + checagem de reversão silenciosa no delta.
- **Todos os 8 itens já anotados 🔴/🟡** pelo pass de 2026-07-31 — reavaliados contra o delta.
- **Todos os 6 itens "🔴 Still open (2026-07-31)"** — reavaliados contra o delta.
- **Amostra de ~5 itens MEDIUM/LOW** para detecção de reversão silenciosa.

**Cobertura declarada: 30 de 124 marcações verificáveis** (100% dos HIGH/MEDIUM-HIGH e dos itens
previamente sinalizados; amostra do restante). Critério de escalonamento (>15% 🔴 na amostra) **não
atingido**: nenhuma marcação ✅ nova veio 🔴. O banco não está comprometido.

### Placar da Fase 1

| Resultado | Contagem |
|---|---|
| ✅ Feito — sobrevive no HEAD, sem reversão | 26 |
| 🟢 Resolvido de passagem pelo delta (antes 🔴/aberto) | 2 |
| 🔴 Reaberto novo nesta verificação | 0 |

### HIGH / MEDIUM-HIGH — confirmação de sobrevivência

Todas as 18 marcações HIGH/MEDIUM-HIGH ✅ sobrevivem no `HEAD`. Amostra da evidência:

| Fingerprint | Evidência no HEAD |
|---|---|
| `ref-docs-agents-md-model-column-wrong` | `docs/agents.md:35-36` — coluna trocada por **Tier** (`repetitive`/`reasoning`), correto por construção |
| `ref-claude-md-183-code-reviewer-roles` | `agents/code-reviewer.md` carrega `review-router` e roteia para os reviewers |
| `flow-helpers-archive-index-sh-orphan` | trigger existe: `scripts/hooks/stop/99b-archive-index.sh` |
| `agent-security-specialist-…-sast` | `agents/security-specialist.md` — `grep bandit/composer audit/npm audit/trivy` = **limpo** |
| `agent-backend-developer-integration-awareness` | `agents/backend-developer.md:71` — seção virou **tabela de detecção que delega a skills** ("The skill is the source of truth… never act on these platforms from memory") |
| `agent-frontend-test-specialist-…-recipes` | `renderHook/withSetup/testing-library` recipes = **limpo** |

### Itens previamente 🔴/🟡 — reavaliados contra o delta

| Fingerprint | Estado 2026-07-31 | Estado 2026-08-12 | Evidência |
|---|---|---|---|
| `flow-telemetry-pre-tool-use-02-runs-on-every-tool-call-without-batching-or-deduplication…` | 🔴 Reaberto | **🟢 Resolvido** | `scripts/hooks/pre-tool-use/02b-telemetry.sh:38-45` — agora enfileira eventos (batch flushado no Stop por `05-telemetry.sh`) e faz early-exit por substring *antes* do fork `python3` para tools que não sejam Task/Bash. Resolvido por `156771b`. |
| `release-prep-skill-exists-twice…` | 🔴 Reaberto | 🔴 (reproduz) | `.claude/skills/release-prep/SKILL.md` (182) e `skills/shared/release-prep/SKILL.md` (88) seguem divergentes; nenhuma regra de sync |
| `flow-stop-no-zombie-state-cleanup…` | 🔴 Reaberto | 🔴 (reproduz) | `grep -rln 'worktree-session\|discovery-lock' scripts/hooks/stop/` = vazio |
| `flow-cli-commit-validate-msg-script-skipped-silently…` | 🔴 Reaberto | 🔴 (reproduz) | `commands/commit.md:150-152` — `if [ -f … ]` sem `else`; ainda pula silenciosamente quando o script falta |
| `token-claude-md-426-lines…` | 🔴 Reaberto | 🔴 (reproduz, pior) | `CLAUDE.md` foi de 549 → **586** linhas; nenhum dos três blocos extraído |
| `ref-notification-system-…-triplicated` | 🟡 Parcial | 🟡 (melhorou) | notifier agora `_disabled-04-notifier.sh`; `notifier/SKILL.md` caiu para 133 linhas / 9 tips (era 15). Ainda carrega índice de tips — sub-escopo pendente |
| `flow-size-limits-sh-ci-only-warn-only…` | 🟡 Parcial | 🟡 (reproduz) | `size-limits` segue ausente de `scripts/hooks/stop/`; `agent-lint.sh` não conta linhas |
| `token-skill-loads-via-table-vs-prose…` | 🟡 Parcial | 🟡 (reproduz) | `agents/frontend-reviewer.md` — 0 tabelas / 17 refs de skill |

### Itens "🔴 Still open (2026-07-31)" — reavaliados

| Fingerprint | Estado 2026-08-12 | Evidência |
|---|---|---|
| `gov-installer-rigor-asymmetry` | **🟢 Resolvido** | `.claude/settings.json` agora registra **Stop, PreToolUse, SessionStart, PreCompact** (4 dispatchers dogfooded, era só Stop). Resolvido por `872477b` + `ae77545` |
| `flow-session-start-118-lines-monolithic` | 🔴 (reproduz, pior) | `scripts/hooks/session-start.sh` cresceu 174 → **306** linhas |
| `token-install-sh-503-lines…` | 🔴 (reproduz, pior) | `scripts/install.sh` cresceu 947 → **1085** linhas, ainda não decomposto |
| `token-changelog-already-growing…` | 🔴 (reproduz, pior) | `CHANGELOG.md` cresceu 441 → **959** linhas, sem rotação |
| `flow-conventional-commits-validate-script-no-husky…` | 🔴 (reproduz) | `grep commit-msg\|husky\|lefthook scripts/install.sh` = vazio |
| `flow-hook-events-only-pretooluse-and-stop` | 🔴 (reproduz) | `UserPromptSubmit`, `SubagentStop`, `Notification` seguem não registrados no install |
| `skill-no-skill-uses-scripts-subdir…` | 🔴 (reproduz) | `find skills -type d -name scripts` = vazio |
| `skill-adr-coverage-only-architect` | 🔴 (reproduz) | `grep -rln 'shared/adr' agents/` = só `software-architect.md` |
| `token-readme-…-no-cross-link-tagging` | 🔴 (reproduz) | sem `@section` anchors |
| `token-skills-shared-token-efficiency-not-quantified…` | 🔴 (reproduz) | nenhuma métrica/feedback loop |

> **Nota de método.** A marcação `flow-telemetry-pre-tool-use-02` era um ✅ que fora reaberto 🔴; a
> remediação real veio de um commit posterior (`156771b`), não da execução original de 2026-07-31.
> Pela rubrica isso é **🟢 Resolved** (resolvido por outra via), não ✅ retroativo. Mesmo raciocínio
> para `gov-installer-rigor-asymmetry`.

---

## FASE 1b — Validade dos achados abertos

Os 11 achados originais do pass guardião de 2026-07-31 (sem marcador). Alvos revalidados no `HEAD`.

| Fingerprint | Alvo | Estado | Evidência |
|---|---|---|---|
| `auto-commands-json-plan-gate-field-has-no-consumer…` | `scripts/lib/commands.json` | **🟢 Resolvido** | `scripts/lib/render_provider.py:105` `soften_plan_gate()` consome `meta.get("plan_gate")` (linhas 899, 921, 928). O campo agora tem consumidor real no render engine |
| `agent-frontend-test-specialist-sonarqube-coverage-block-hardcodes-jest-vitest…` | `agents/frontend-test-specialist.md` | 🔴 reproduz | `:142-151` — bloco `jest --coverage` / `vitest run --coverage` / `sonar.javascript.lcov.reportPaths` intacto |
| `agent-frontend-developer-description-frontmatter-enumerates-eight-frameworks` | `agents/frontend-developer.md` | 🔴 reproduz | `description:` enumera React, Vue, Svelte, Angular, Blade, Twig, ERB, Jinja |
| `agent-devops-specialist-core-expertise-declares-primary-docker…` | `agents/devops-specialist.md` | 🔴 reproduz | `:46` "**Primary**: Docker" |
| `flow-audit-command-devops-analysis-prompt-names-redis-cdn-docker…` | `commands/audit.md` | 🔴 reproduz | `:126` "Caching opportunities (Redis, CDN…)", `:128` "Docker/resource concerns" |
| `docs-sync-claude-md-102-states-skill-desc-strict-false…` | `CLAUDE.md` | 🔴 reproduz | `CLAUDE.md:129` diz `SKILL_DESC_STRICT=false`; `helpers/agent-lint.sh:98` seta `SKILL_DESC_STRICT=true` |
| `docs-sync-claude-md-173-says-all-devteam-commands-load-current-context…` | `CLAUDE.md` | 🔴 reproduz | `:202` "All `/devteam:*` commands" carregam current-context vs `:250` lista 11 exceções |
| `docs-sync-reports-index-md-99-legend-comment-claims-all-131-unmarked…` | `docs/reports/_index.md` | 🔴 reproduz (pior) | `:100` "All 131 entries below are unmarked" — hoje 136 carregam marcadores |
| `flow-pre-tool-use-02b-telemetry-reads-devteam-hook-payload-branch-dead-path…` | `scripts/hooks/pre-tool-use/02b-telemetry.sh` | 🔴 reproduz | `:22` `[ -f "${DEVTEAM_HOOK_PAYLOAD:-}" ]` — ramo que só o dispatcher Stop popula |
| `skill-shared-migration-v1-to-v2-437-lines-largest…` | `skills/shared/migration-v1-to-v2/SKILL.md` | 🔴 reproduz | 438 linhas, sem `references/` |
| `token-interaction-patterns-209-lines-loaded-unconditionally…` | `skills/shared/interaction-patterns/SKILL.md` | 🔴 reproduz | 209 linhas, sem `references/` |

**Mortalidade da Fase 1b: 1 de 11 = 9%** (1 🟢 Resolvido, 0 ⚰️ Obsoleto, 10 reproduzem). Banco
saudável — bem abaixo dos 53% da consolidação v1→v2.
