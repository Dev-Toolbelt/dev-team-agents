# Auditoria Guardiã — 2026-07-31

**Data:** 2026-07-31 · **Baseline:** `HEAD` = `f54569a` · **Baseline anterior:** `7f85ed7`

> **Drift durante o pass.** Três commits (`bd66764`, `d08042e`, `48b9307` — a regra
> `scoped-test-execution`) entraram no repositório enquanto esta auditoria rodava, movendo `HEAD`
> para `48b9307` e tocando `CLAUDE.md`, 5 agentes, 2 comandos e 2 skills. Todos os 11 achados foram
> **revalidados contra `48b9307`** e continuam reproduzindo, com os mesmos números de linha — a
> única mudança é `CLAUDE.md`, que passou de 549 para **550** linhas. O baseline declarado continua
> `f54569a` de propósito: é o que foi auditado, e assim os três commits entram no delta do próximo
> pass, onde ainda não foram examinados.

---

## Sumário executivo

O pass de execução de 2026-07-31 marcou **120 ✅ Executed + 1 ⚠️ Partial** em um único dia — 92% de
throughput declarado. A Fase 1 verificou 49 dessas marcações contra o git e **confirmou 84% delas**.
A taxa de 🔴 ficou em **10,2%**, abaixo do gatilho de escalonamento de 15%: o banco não está
comprometido, e o pass de execução foi, no geral, honesto.

O padrão dos 5 🔴 é consistente e vale mais que a taxa: **em quatro dos cinco, o commit que motivou
a marcação existiu e tocou o arquivo — mas para resolver um achado *vizinho*, não aquele.**
`flow-cli-commit-validate-msg-script-skipped-silently` foi marcado porque `commands/commit.md` mudou
naquele dia; a mudança foi a adoção do `AskUserQuestion`, e o bloco do achado é byte-idêntico ao
anterior. `flow-telemetry-pre-tool-use-02-…-without-batching` foi marcado porque o arquivo mudou; a
mudança foi um rename e a troca do guard de consentimento. É marcação por proximidade de arquivo,
não por remediação verificada.

Nos eixos novos, **8 achados originais** com evidência, de 108 candidatos varridos no Eixo A e 6
gates rodados no Eixo B. Três deles são a mesma classe de defeito: **uma correção aplicada a um
agente e não ao seu gêmeo** — o bloco de cobertura hardcoded que saiu de `backend-test-specialist` e
ficou em `frontend-test-specialist`; a `description` que foi desacoplada em `mobile-developer` e não
em `frontend-developer`. São os achados mais baratos do pass, porque a forma da correção já existe
no repo.

---

## Método

| Fase | Escopo | Resultado |
|---|---|---|
| 0 | Banco carregado, delta `7f85ed7..HEAD` apurado | 131 fingerprints · 15 commits · 268 arquivos (+6.801 / −21.927) |
| 1 | Verificação ancorada no git dos itens ✅/⚠️ | 49 de 121 (**cobertura 40%**) |
| 1b | Revalidação dos 10 achados abertos | 10 de 10 (integral) |
| 2 | Cinco eixos; A integral, B–E priorizando o delta | 8 achados originais |

**Critério de amostragem da Fase 1** (121 > 60, regra do prompt): todos os 18 HIGH e MEDIUM-HIGH,
mais 31 dos 103 restantes sorteados com semente fixa `20260731`.

---

## Fase 1 — placar

| Marca | Tier 1 (18) | Tier 2 (31) | Total (49) | % |
|---|---|---|---|---|
| ✅ Feito | 16 | 25 | **41** | 84% |
| 🟡 Parcialmente feito | 1 | 2 | **3** | 6% |
| 🔴 Não feito | 1 | 4 | **5** | **10%** |

**Escalonamento não disparado** (10,2% < 15%).

**Os 5 🔴:** `token-claude-md-426-lines-still-monolithic-…` (o `CLAUDE.md` cresceu de 425 para 549
linhas e nenhum dos três blocos foi extraído) · `ref-release-prep-skill-exists-twice-…` (a única
mudança nos dois arquivos foi 1 linha de `description`) · `flow-stop-no-zombie-state-cleanup-…`
(nenhum commit da janela tocou o alvo) · `flow-telemetry-pre-tool-use-02-…-without-batching-or-deduplication` (rename + troca de guard) ·
`flow-cli-commit-validate-msg-script-skipped-silently-when-missing` (bloco byte-idêntico).

**Os 3 🟡:** `flow-size-limits-sh-…` (promovido a bloqueante no CI e zero violações, mas segue sem
equivalente no dispatcher Stop) · `ref-notification-system-content-triplicated-…` (drift da tabela
corrigido e tips extraídos para `tips/*.txt`, mas os 15 tips continuam íntegros em
`skills/shared/notifier/SKILL.md:115-129` — a duplicação virou tripla) ·
`token-skill-loads-via-table-vs-prose-inconsistent` (2 dos 3 agentes citados migraram para tabela;
nenhuma regra foi escrita, e `CLAUDE.md:521` instrui explicitamente a seguir o padrão já existente
de cada agente).

Detalhe item a item em [`00-guardiao-verificacao.md`](00-guardiao-verificacao.md).

---

## Fase 1b — mortalidade

**0% (0 de 10).** Nenhum achado aberto foi resolvido de passagem; nenhum alvo desapareceu. Coerente
com o perfil do pass de execução, que atacou o conjunto verificável e não encostou nos 10 abertos.

O sinal relevante é a **direção**: quatro dos dez pioraram mensuravelmente dentro da janela.

| Achado | Antes | Agora |
|---|---|---|
| `token-install-sh-503-lines-…` | 803 linhas | **947** |
| `token-changelog-already-growing-…` | 441 linhas | **546** |
| `token-readme-228-each-…` | 228 linhas cada | **338** cada |
| `flow-session-start-118-lines-monolithic-…` | 174 linhas | 174 |

São os grupos "decomposição de script" e "sem medição" do `_index.md` — os que ninguém fecha porque
nenhum gate os mede. O gate de `CLAUDE.md` (aviso em 600, falha em 700) criado nesta janela é o
único contra-exemplo, e recai justamente sobre o arquivo que também cresceu 29%.

---

## Fase 2 — achados originais por eixo

| Eixo | Arquivo | Candidatos | Originais |
|---|---|---|---|
| A — Agnosticismo de stack | [`01-agnosticismo-de-stack.md`](01-agnosticismo-de-stack.md) | 108 | **4** |
| B — Referências e consistência | [`02-referencias-e-consistencia.md`](02-referencias-e-consistencia.md) | 6 gates + 5 paridades | **3** |
| C — Fluxos e comandos | [`03-fluxos-e-comandos.md`](03-fluxos-e-comandos.md) | 9 | **2** |
| D — Agentes e skills | [`04-agentes-e-skills.md`](04-agentes-e-skills.md) | 10 | **1** |
| E — Economia de tokens | [`05-economia-tokens.md`](05-economia-tokens.md) | 11 | **1** |
| **Total** | | | **11** |

> Nota: 11 achados publicados. Os eixos D e E fecharam com um achado cada e declaram explicitamente
> "nenhum achado original" nos sub-eixos restantes — o repo fechou nesta janela a maior parte do que
> havia a encontrar nesses dois eixos.

### Tabela de severidade

| Severidade | Qtd | Fingerprints |
|---|---|---|
| **HIGH** | 1 | `docs-sync-claude-md-102-states-skill-desc-strict-false-…` |
| **MEDIUM-HIGH** | 3 | `agent-frontend-test-specialist-sonarqube-coverage-block-…` · `auto-commands-json-plan-gate-field-has-no-consumer-…` · `token-interaction-patterns-209-lines-loaded-unconditionally-…` |
| **MEDIUM** | 4 | `agent-frontend-developer-description-frontmatter-enumerates-eight-frameworks-…` · `agent-devops-specialist-core-expertise-declares-primary-docker-…` · `docs-sync-claude-md-173-says-all-devteam-commands-load-current-context-…` · `skill-shared-migration-v1-to-v2-437-lines-…` |
| **LOW-MEDIUM** | 2 | `flow-audit-command-devops-analysis-prompt-names-redis-cdn-docker-…` · `docs-sync-reports-index-md-99-legend-comment-claims-all-131-entries-unmarked-…` |
| **LOW** | 1 | `flow-pre-tool-use-02b-telemetry-reads-devteam-hook-payload-branch-…` |

---

## Os 3 achados mais graves

1. **`CLAUDE.md:102` documenta `SKILL_DESC_STRICT=false` e "non-blocking warning today"; o valor real
   é `true` desde esta mesma janela** (`helpers/agent-lint.sh:31`), e
   `.github/scripts/ci/01-lint.sh:75-77` documenta a promoção explicitamente. O `CLAUDE.md` é
   carregado em toda sessão deste repo e convida o autor a estourar um orçamento que o CI bloqueia.
   Único HIGH do pass.

2. **`plan_gate` em `scripts/lib/commands.json` não tem consumidor nem validador, e já divergiu.**
   `grep -rn 'plan_gate' --include='*.py' --include='*.sh' .` → zero hits fora do próprio JSON.
   Dos 6 comandos `required`, cinco carregam o gate no corpo e `commands/architect.md` carrega
   **zero** — o gate só é alcançado porque o agente que ele spawna carrega `plan-mode` por conta
   própria. A regra mais forte do `CLAUDE.md` depende, nesse caminho, de uma propriedade de
   terceiros.

3. **`interaction-patterns` é carregada incondicionalmente na primeira linha dos 24 comandos, e 76%
   dela é catálogo de exemplos.** 26 × 209 = 5.434 linhas de superfície agregada, das quais 38
   linhas são a regra normativa. Extrair `:49-209` para `references/` economiza ≈ **4.130 linhas** e
   incide em 100% das invocações `/devteam:*` — a maior economia isolada disponível hoje.

---

## Descartados por duplicação

| Candidato | Porta | Motivo |
|---|---|---|
| `pre-tool-use.sh` não computa estado compartilhado; cada sub-script paga seu guard por tool call | **5 (estado)** | Pertence a `flow-telemetry-pre-tool-use-02-…-without-batching-or-deduplication`, que esta mesma Fase 1 acabou de reabrir como 🔴. Reapresentar item registrado e não implementado é ruído |
| `01-check-updates.sh` e `02b-telemetry.sh` re-derivam `USER_DATA_DIR`/`PREFS_FILE` independentemente | **3 (semântica)** | Mesmo alvo, mesma causa raiz e mesma remediação do item acima |
| `release-prep` é user-invocable e não consta na tabela User-Invocable Skills do `CLAUDE.md` | **3 (semântica)** | Mesmo alvo e mesma remediação de `ref-release-prep-skill-exists-twice-…`, reaberto 🔴 nesta Fase 1 |
| `project-context` — 309 linhas, 17 loaders incondicionais, sem `references/` | **4 (escopo menor)** | O banco já registra dois sub-escopos específicos deste arquivo (`token-project-context-docker-development-environment-section-22-lines-…` e `token-sonarqube-detection-block-redundant`), ambos abertos. Um achado sobre o tamanho total é escopo **maior**, não menor — a porta só admite o contrário |
| `commit` / `learn` / `pr` são `conditional` sem passo de plano no corpo | — | `conditional` significa "o comando decide"; não há contrato violado |
| `docs/agents.md` teria 19 agentes para 17 arquivos | — | Falso positivo de regex: `:94-95` são linhas de uma tabela de skills |
| `.codex/` na raiz, não listado no `.gitignore` | — | `find .codex -type f` → 0 arquivos; `git status --untracked-files=all` limpo |
| 142 `SKILL.md` na árvore vs "138/138" na mensagem de `7736e20` | — | Mensagem de commit não é documentação mantida; sem gate nem doc que reafirme o número |
| ~39 caminhos "não resolvidos" no `CLAUDE.md` / `README.md` | — | Nomes-base em prosa e caminhos do projeto instalado. `helpers/orphan-template-scan.sh`, que testa resolução real, passa limpo |
| `backend-reviewer` usa `file.php:88` no template de output | — | O mesmo template usa `file.go:42` e `file.py:33`: trio deliberadamente multilíngue, não acoplamento |
| 7 skills > 200 linhas em `integrations/` · `mobile/` · `devops/` sem `references/` | — | Categorias isentas por design (`CLAUDE.md`), carregadas só sob detecção |

---

## Gates

```
helpers/check-fingerprint-uniqueness.sh  → ✓ All 131 fingerprint slugs are unique across 1 bank file(s).  (pré-atualização)
helpers/archive-index.sh --dry-run       → ✓ No entries older than 90 days (cutoff 2026-05-02).
helpers/agent-lint.sh                    → agent-lint: clean ✓
helpers/size-limits.sh                   → size-limits: clean ✓
helpers/orphan-skill-scan.sh             → orphan-skill-scan: clean ✓
helpers/orphan-template-scan.sh          → orphan-template-scan: clean ✓
.github/scripts/ci/02-readme-sync.sh     → readme-sync OK ✓  (3 pares EN ↔ pt-BR)
```
