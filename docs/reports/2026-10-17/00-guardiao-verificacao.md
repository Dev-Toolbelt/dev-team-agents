# Fase 1 e 1b — Verificação Guardiã — 2026-10-17

**Baseline:** `HEAD` = `bb0e883` · **Baseline anterior:** `349f18c` · **Delta:** 76 commits,
157 arquivos.

> **Re-baseline no meio do pass.** A Fase 0 fixou `78c11a6`. Enquanto as Fases 0 e 1 corriam,
> **46 commits e 111 arquivos** entraram no repositório (o working tree de 30 arquivos
> modificados foi commitado e o trabalho de spec/sprint/reuse-lint chegou em bloco). Como o delta
> novo toca `agents/`, `commands/` e `skills/shared/` — exatamente onde a Fase 1 confirma —,
> o baseline foi **re-fixado em `bb0e883`** e **todas as confirmações no `HEAD` foram refeitas
> contra ele**. O relógio virou de 2026-10-17 para 2026-10-18 (UTC) durante o pass; `DATA` ficou
> em 2026-10-17, que é a data fixada na Fase 0 e a data de todos os commits do delta.

> **Plan Gate.** Pass disparado por tarefa agendada, com instrução explícita de executar e
> commitar. Não houve aprovação humana do plano; o critério de amostragem da Fase 1 está
> declarado **antes** dos resultados, que é a garantia que o gate existe para dar.

---

## Conjuntos (Fase 0)

| Conjunto | Tamanho | Critério |
|---|---|---|
| Fingerprints no banco | 290 | `grep -cE '^- \`[a-z]' docs/reports/_index.md` |
| **Verificável** (✅ Executed + ⚠️ Partial, sem 🔴/🟢/⚰️) | **142** | alvos da Fase 1 |
| **Aberto** (sem marcador) | **111** | alvos da Fase 1b |
| Exclusão | 141 ✅ · 15 🟢 · 1 ⚰️ · 0 ↩️ | fora da geração |
| Marcas 🔴 no banco | 21 | reaberturas de passes anteriores, fora do conjunto verificável |

Severidade no conjunto verificável: 20 HIGH · 21 MEDIUM-HIGH · 43 MEDIUM · 38 LOW-MEDIUM ·
19 LOW · 1 sem severidade legível.

**Datas de marcação no conjunto verificável:** 2026-07-31 (109) · 2026-10-02 (30) ·
2026-09-30 (1) · sem data (2). **Nenhuma marca nova desde 2026-10-02** — 15 dias e 76 commits
sem que nada fosse declarado executado. A Fase 1 deste pass é, de novo, sobre **durabilidade**,
não sobre marcações frescas.

**Delta de código por subárvore:** `skills/shared` 21 · `scripts/lib` 10 · `docs/reports` 8 ·
`scripts/hooks` 6 · `docs/wiki` 6 · `app/src` 6 · `docs/development` 4 · `commands/` 30 ·
`agents/` 15 · `tests/` 17. **Arquivos novos que importam:** `commands/spec.md`,
`commands/sprint.md`, `AGENTS.md`, `scripts/hooks/stop/03f-spec-lint.sh`,
`scripts/hooks/lib/warn-once.sh`, `scripts/lib/spec_lint.py`, `scripts/spec-lint.sh`,
`templates/contract-template.md`, ADRs 0035/0036/0037.

**Subárvores cegas no banco:** `scripts/lib/devteam/` (10 arquivos no delta, **0 menções** no
banco), `opencode/plugin/`, `scripts/hooks/user-prompt-submit/04-language.sh`. O trabalho novo
de spec/warn-once também entra com 0 menções — é onde a Fase 2 caçou.

---

## Critério de amostragem da Fase 1

O conjunto verificável (142) excede 60, então a regra do prompt se aplica:

- **todos** os 41 HIGH e MEDIUM-HIGH;
- **30% aleatório** (`random.seed(20261017)`) dos 101 restantes → 30 itens;
- mais qualquer item cujo alvo caia no delta de código (0 adicionais além dos já sorteados).

**Cobertura: 71 de 142 (50%).**

### Método

Para cada item: (1) reconstrução da remediação pelo git na janela da data de marcação
(`git log --since=<data> --until=<data+2d> -- <alvo>`); (2) `commits_after`, que é o teste de
reversão silenciosa; (3) confirmação no `HEAD` por símbolo, nunca por linha antiga.

Dois atalhos declarados, porque mudam o que "verificado" significa:

- **`commits_after = 0`** — o `HEAD` do alvo é o estado deixado pelo commit da janela; reversão
  silenciosa é impossível por construção, e a confirmação no `HEAD` foi feita por amostra dentro
  de cada grupo que compartilha arquivo.
- **`commits_after > 0`** — confirmação manual no `HEAD`, item a item.

**Resolução de alvo.** 31 dos 142 têm o campo `alvo:`; os outros são entradas legadas que nomeiam
agentes e skills por nome. Para essas, o alvo foi resolvido por basename contra `git ls-files` e,
quando isso falhou, pelo nome do agente/skill embutido no slug.

> **O campo `alvo:` não é o alvo da remediação.** Oito itens voltaram "nenhum commit na janela
> tocou o alvo" e **nenhum** era 🔴: em todos, o `alvo:` nomeia o arquivo que *descreve* o
> problema, não o que foi *corrigido*. O caso limpo é
> `skill-spec-gate-scope-lock-hard-gate-unreachable-by-execution-agents` — `alvo:` é
> `skills/shared/spec-gate/SKILL.md`, que nenhum commit de 2026-10-02 tocou, enquanto a
> remediação real é `c19f060` ("load spec-gate in developer agents"), que tocou quatro arquivos
> em `agents/`. Aplicar a regra "nenhum commit na janela ⇒ 🔴 por construção" contra o campo
> `alvo:` teria produzido **8 falsos 🔴 de 71 (11,3%)**, perto do limiar de escalonamento de 15%.
> Quem rodar o próximo pass: valide a janela contra o alvo da **remediação**, não contra o campo.

---

## Placar

| Marca | N | % |
|---|---|---|
| ✅ **Feito** | 66 | 93,0% |
| 🟡 **Parcialmente feito** | 5 | 7,0% |
| 🔴 **Não feito** | 0 | 0% |

**Reaberturas novas neste pass: 0 de 71 (0%).** O limiar de escalonamento (15% da amostra) não
foi atingido; a integridade do banco está intacta. É o segundo melhor placar desde a
consolidação, atrás apenas de 2026-10-02 (94,1%).

---

## 🟡 Parcialmente feito (5) — todas reconfirmações, nenhuma nova

| Fingerprint | Sev | Evidência no `HEAD` (`bb0e883`) |
|---|---|---|
| `flow-size-limits-sh-ci-only-warn-only-not-in-stop-dispatcher-asymmetric-with-agent-lint-200-cap-never-blocking` | HIGH | **4ª confirmação.** `grep -rn size-limits scripts/hooks/ .github/` devolve uma única linha: `.github/scripts/ci/01-lint.sh:91` — `blocking "size-limits" bash helpers/size-limits.sh`. Os 14 sub-scripts de `scripts/hooks/stop/` não têm nenhuma checagem de tamanho — e `bash helpers/size-limits.sh` hoje emite `⚠ CLAUDE.md: 678 lines (warning threshold: 600, fails at 700)`, um WARN que só o CI vê |
| `auto-update-no-integrity-check` | MEDIUM-HIGH | `scripts/install.sh.sha256` não existe; `scripts/lib/installer-fetch.sh:34-42` segue documentando e implementando a falha aberta ("the project publishes no signatures and no out-of-band digests today") |
| `token-review-shared-skills-reloaded-by-router-then-each-specialist-2-3x-fanout-per-devteam-review-no-shared-loaded-context` | MEDIUM | `commands/review.md` tem 76 linhas e 3 cargas de `skills/shared`; o fan-out por spawn isolado segue |
| `token-skill-loads-via-table-vs-prose-inconsistent` | LOW | `agents/frontend-reviewer.md`: 3 linhas de tabela contra 19 referências `skills/` em prosa. Nenhuma regra foi escrita |
| `token-current-context-block-deduplication` | LOW-MEDIUM | **Mediu pior.** 31 de 37 comandos mencionam `current-context` e 26 carregam o `SKILL.md` — contra 29/24 em 2026-10-10. A dedup nunca ocorreu e o bloco se espalhou para os dois comandos novos (`spec.md:6`, `sprint.md:6`) |

---

## ✅ Amostra da confirmação (itens verificados manualmente no `HEAD`)

- `ref-telemetry-honors-pref-but-pref-defaults-true-on-fresh-install-without-prompt-on-non-interactive-curl-bash`
  — HIGH. `scripts/install.sh:1181` abre com `TELEMETRY_VALUE="false"` e `:1208` mantém `false`
  no caminho não-interativo; o prompt em `:1203-1204` é o único que pode ligar.
- `gov-telemetry-send-sh-posthog-key-comments-self-contradict-intentionally-public-vs-replace-before-release-todo-on-default-on-path`
  — MEDIUM-HIGH. `scripts/helpers/telemetry-send.sh:27-37` traz um bloco único e coerente (chave
  de *projeto* PostHog, pública por desenho, com override por `DEVTEAM_POSTHOG_KEY`); nenhum
  TODO "replace before release" sobrou.
- `token-foundational-rule-424-lines-across-17-agents` — MEDIUM-HIGH. A remediação foi `b4e219f`
  ("refactor(agents): delegate shared context"): a § Foundational Rule dos 18 agentes agora
  **delega** a `skills/shared/project-context/SKILL.md` (ex.: `agents/backend-developer.md:21`) e
  o que resta são adições específicas por agente — 369 linhas somadas contra 384 registradas,
  com um agente a mais.
- `token-comments-policy-load-directive-duplicated-in-8-agents-…` — LOW-MEDIUM. A evidência
  original era `grep -rn "type-annotations, tests → aaa-pattern" agents/` → 8 hits. Hoje → **0**:
  o roteamento de seções virou tabela dentro da própria skill
  (`skills/shared/comments-policy/SKILL.md:107-109`).
- `skill-comments-policy-missing-in-non-coding-agents` — LOW-MEDIUM. 15 de 18 agentes carregam a
  skill (era 8 de 17); os dois coding agents que a motivaram têm a carga
  (`frontend-developer.md:30`, `mobile-developer.md`). Seguem sem ela `seo-specialist`,
  `setup-assistant` e `technical-writer` — nenhum escreve código de produção.
- `flow-check-fingerprint-uniqueness-scans-only-index-md-blind-to-documented-archive-rotation-cross-file-dupes-undetected`
  — MEDIUM. `helpers/check-fingerprint-uniqueness.sh:24` faz
  `find "$REPORTS_DIR" -maxdepth 1 -name '_index-archive-*.md'` e reporta o arquivo-fonte de cada
  ocorrência. Rodado hoje: `✓ All 290 fingerprint slugs are unique across 1 bank file(s).`
- `flow-ci-orphan-skill-scan-step-continue-on-error-true-never-blocks-…` — MEDIUM.
  `.github/scripts/ci/01-lint.sh:74-77` agora declara a política por tier e a condição de
  promoção ("PROMOTE WHEN: the scan reports zero orphans on a clean tree AND…") antes do
  `advisory "orphan-skill-scan"`.
- `docs-sync-preferences-mirror-registry-names-readmes-omits-docs-pair` — MEDIUM-HIGH.
  `CLAUDE.md:369` lista `docs/user-preferences.md` / `docs/user-preferences.pt-BR.md` na tabela
  de espelhos. *(A mesma lista foi reencontrada incompleta em outro arquivo — ver o Eixo B.)*
- `token-pre-tool-use-01-check-updates-forks-python3-…` — MEDIUM.
  `scripts/hooks/pre-tool-use/_disabled-01-check-updates.sh` está desativado por nome e
  `scripts/hooks/session-start.sh:191-197` carrega o check uma vez por sessão.
- `docs-sync-claude-md-package-exclusions` — LOW-MEDIUM. `CLAUDE-md/user-data.md:103` tem a linha
  `opencode/`, que era a lacuna registrada.
- **Cluster `02c-full-suite-guard.sh`** (6 fingerprints, marca 2026-10-02, `commits_after = 0`) e
  **cluster `commands/merge.md`** (4 fingerprints): reconfirmados; nenhum dos 76 commits do delta
  tocou os dois arquivos.
- **Varredura de reversão silenciosa.** Dos 142 alvos do conjunto verificável, **1** foi tocado
  pelo delta: `skills/shared/project-context/SKILL.md`
  (`token-project-context-docker-development-environment-section-22-lines-inlined-…`). A mudança
  é a diretiva de língua (`:59`), não a seção Docker — que segue extraída, como linha de tabela
  de detecção em `:261` apontando para `skills/devops/docker-dev/SKILL.md`. **Nenhuma reversão
  silenciosa no delta.**

---

# Fase 1b — Validade dos achados abertos

**Cobertura: 111 de 111 (100%).**

### Método

O conjunto aberto foi particionado pelo delta de código:

- **11 itens** cujo alvo foi tocado por algum dos 76 commits → verificação manual no `HEAD`, um a
  um. É onde uma correção de passagem pode ter acontecido.
- **100 itens** cujo alvo não recebeu commit nenhum desde o registro → ainda reproduzem por
  construção. O atalho está declarado para que o próximo pass saiba o que foi e o que não foi
  lido.

## Mortalidade: 0 de 111 (0%)

Nenhum 🟢, nenhum ⚰️. **Os 11 alvos tocados pelo delta seguem todos reproduzindo** — e o delta é
o maior em volume de `skills/shared` e `commands/` desde a consolidação. Um delta de 76 commits
que não fecha um único achado aberto é o dado de saúde deste pass: o trabalho novo não passa
perto do que está registrado.

| Fingerprint | Sev | Evidência no `HEAD` |
|---|---|---|
| `agent-project-context-delegation-claims-recent-git-log-absent-from-skill-18x` | HIGH | **Mediu pior.** `grep -c 'recent git log' agents/*.md` → **18 de 18**; `grep -ci 'git log' skills/shared/project-context/SKILL.md` → **0** (era 1 no registro). Os 18 agentes delegam histórico git a uma skill de 321 linhas que não menciona git log uma vez |
| `token-wiki-retrieval-index-13-7kb-read-whole-by-18-agents-with-no-cap` | MEDIUM-HIGH | **Mediu pior.** `docs/wiki/README.md`: **15.233 B / 71 linhas** contra 13.715 B / 51 linhas em 2026-10-10 — **+11% em 7 dias**, 5 entradas novas no delta, ainda sem teto |
| `flow-audit-step2-unconditional-docker-stack-ignores-isolate-pref-compose-gate` | MEDIUM-HIGH | `commands/audit.md:48` segue incondicional: "After worktree creation, spin up an isolated Docker stack" |
| `token-project-context-restates-scoped-test-exception-table-read-by-18-agents` | MEDIUM | `skills/shared/project-context/SKILL.md:226-233` segue com a carga e a tabela de exceções |
| `token-checks-list-loads-all-three-provider-blocks-after-step-0-resolved-one` | MEDIUM | **Mediu pior.** `checks-list.md`: **715 linhas** contra 681 em 2026-10-10 e 668 no registro |
| `flow-audit-command-devops-analysis-prompt-names-redis-cdn-docker-inside-spawn-…` | LOW-MEDIUM | `commands/audit.md:118,120` seguem com "Caching opportunities (Redis, CDN, HTTP caching)" e "Docker/resource concerns" dentro do prompt de spawn |
| `docs-sync-reports-index-md-99-legend-comment-claims-all-131-entries-unmarked-…` | LOW-MEDIUM | `docs/reports/_index.md` segue afirmando "All 131 entries below are unmarked" num arquivo de **290** entradas, 179 delas marcadas |
| `docs-sync-hooks-md-64-full-suite-guard-examples-predate-wrapper-detection` | LOW-MEDIUM | `CLAUDE-md/hooks.md:75` segue exemplificando só `pytest` sem path/`-k` e `vendor/bin/phpunit` sem `--filter` |
| `docs-sync-session-start-comment-cites-nonexistent-02b-full-suite-guard` | LOW-MEDIUM | `scripts/hooks/session-start.sh:249` segue citando `pre-tool-use/02b-full-suite-guard.sh`; o arquivo real é `02c-`, e `02b-` é telemetria |
| `ref-hooks-md-library-rows-omit-data-dirs-sh-sourced-by-ten-scripts` | LOW-MEDIUM | **Mediu pior.** `scripts/hooks/lib/` tem agora **11** arquivos (entrou `warn-once.sh`) e `data-dirs.sh` segue como o único sem linha "Shared library" — com fan-in de **12** scripts, porque `warn-once.sh:18` também o carrega |
| `docs-sync-providers-md-zen-premium-column-mixes-namespaces-pinned-ids` | LOW-MEDIUM | `docs/providers.md:285-292` segue com a coluna premium e a ressalva de que só a primeira é lida pelo renderer |

## Fingerprints abertos que mediram pior ou mudaram de forma

Além dos cinco acima:

| Fingerprint | Registrado / última medida | `HEAD` = `bb0e883` |
|---|---|---|
| `token-claude-md-426-lines-still-monolithic-…` | 426 → 602 → 647 | **678 linhas** — `size-limits.sh` emite WARN; faltam 22 linhas para o teto de falha (700) |
| `token-interaction-patterns-209-lines-loaded-unconditionally-by-24-commands-and-2-agents-…` | 209 linhas × 24 comandos | **323 linhas / 14.750 B × 34 comandos** (+114 linhas neste delta, com as novas § Review Next-Step Gate e § Visual Check Gate). O pior agravamento do banco neste pass |
| `token-plan-mode-execution-strategy-gate-duplicates-orchestration-loaded-by-26` | 14.853 B | **16.602 B / 265 linhas**, e o Execution Strategy Gate agora existe em **quatro** lugares: `orchestration/SKILL.md`, `plan-mode/SKILL.md:151-206`, `interaction-patterns/SKILL.md:180` e, como ressalva explícita, `commands/sprint.md:45` ("it replaces the orchestration Execution Strategy Gate") |
| `flow-claude-md-no-agent-command-list-says-seven-omits-push-and-merge` | "All seven" vs. nove | Inalterado e agora explícito nos dois lados: `CLAUDE-md/commands.md:59` diz "All seven" e enumera sete; `scripts/lib/commands.json:_filler_agent_note` diz "all nine name `technical-writer`" e inclui `push` e `merge` |
| tabela de package exclusions (`CLAUDE-md/user-data.md:85-105`) | sem linha para `tests/`, `infra/`, `packaging/`, `app/` | **Mediu pior:** também faltam `AGENTS.md`, `TERMS.md`, `scripts/install-cli.sh`, `scripts/lib/auth-config.dev.json` e a poda de `__pycache__` — cinco regras de `strip-tarball.sh:24-33` sem linha |

## Gates

```
$ bash helpers/check-fingerprint-uniqueness.sh
✓ All 290 fingerprint slugs are unique across 1 bank file(s).

$ bash helpers/archive-index.sh --dry-run
✓ No entries older than 90 days (cutoff 2026-07-20) in docs/reports/_index.md.

$ bash helpers/agent-lint.sh         → agent-lint: clean ✓
$ bash helpers/orphan-skill-scan.sh  → orphan-skill-scan: clean ✓
$ bash helpers/orphan-template-scan.sh → orphan-template-scan: clean ✓
$ bash helpers/size-limits.sh        → WARN CLAUDE.md 678 linhas (teto de aviso 600) · clean ✓
```
