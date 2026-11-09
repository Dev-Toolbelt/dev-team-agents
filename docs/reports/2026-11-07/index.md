# Auditoria Guardiã — 2026-11-07

**Data:** 2026-11-07 · **Baseline:** `HEAD` = `5133c8c` · **Baseline anterior:** `b64428b`

> **O achado principal deste pass não é um defeito de código: é que a cópia instalada do framework
> dentro do próprio repositório está 5 dias atrás da fonte, e são os symlinks dela que as sessões
> deste repo carregam.** `/devteam:orchestrate` e o agente `orchestrator`, entregues em `e0bd8a0`
> (2026-11-02), são **inalcançáveis** aqui: `ls .claude/commands/devteam/orchestrate.md` →
> `No such file or directory`. O gate de supervisão do ADR-0062 e o guard de secret staged do
> ADR-0059 também não existem na cópia. São **58 arquivos divergentes de 664** e **16 arquivos-fonte
> sem contrapartida alguma**, sem nenhum gate que detecte — registrado como
> `gov-committed-install-copy-stale-vs-source-no-gate` (HIGH). O repositório parou de dogfoodar três
> features da própria janela.

> **Árvore suja durante todo o pass.** Na Fase 0 o working tree carregava 10 arquivos modificados e
> 2 diretórios não rastreados. Toda evidência nesses arquivos vem de `git show HEAD:<path>`; nenhum
> achado se apoia nos dois diretórios não rastreados, que não estão no `HEAD`.

## Método

**Delta:** 154 commits e 880 arquivos desde `b64428b` — o terceiro maior do banco. Concentrado em
`.dev-team-agents/skills` (190), `skills/third-party` (131), `.dev-team-agents/scripts` (81),
`scripts/lib` (43), `app/src` (40), `.dev-team-agents/commands` (31), `app/test` (30),
`skills/shared` (29), `docs/development` (28), `scripts/hooks` (22), `docs/wiki` (21). Temas: canvas
view + task graph (ADR-0063), persona `orchestrator` + `/devteam:orchestrate` + supervision gate
(ADR-0062), run plan único (ADR-0058), secret guard no commit (ADR-0059), helper tools (ADR-0060),
sprints em worktrees isolados, assinatura Windows via eSigner (ADR-0055), third-party skills
vendorizadas e pinadas (ADR-0047), retenção de 24 h no board e no canvas.

**Fase 1.** Conjunto verificável de **152** (✅/⚠️ nos dois bancos). Amostragem: todos os **42**
HIGH/MEDIUM-HIGH + **30% dos 110 restantes** (33), `seed=20261107`.

**Fase 1b.** Conjunto aberto de **130**, revalidado integralmente.

**Fase 2.** Cinco eixos, com o Eixo A em varredura integral e os demais priorizando o delta. Todo
candidato passou pelas cinco portas do Protocolo Anti-Duplicação, mais uma rodada de deduplicação
**cross-eixo** (2 pares de achados independentes colidiram em 3 de 3 atributos e foram fundidos).

## Cobertura e placar da Fase 1 — **75 de 152 (49,3%)**

| Marca verificada | Qtd | % |
|---|---|---|
| ✅ **Feito** | 60 | **80,0%** |
| 🟡 **Parcialmente feito** | 12 | 16,0% |
| 🔴 **Não feito** | 3 | **4,0%** |

**Reaberturas novas: 0.** As 3 🔴 e 5 das 12 🟡 já carregavam anotação. É o **terceiro pass
consecutivo em zero** (2026-10-17 e 2026-10-24 também). Os 4,0% de 🔴 estão muito abaixo do limiar
de escalonamento de 15%: a integridade do banco **não** está comprometida. Nenhuma reversão
silenciosa; em dois casos os commits posteriores **endureceram** a correção.

As 7 divergências novas são todas 🟡 e todas da mesma classe — a correção entregou o defeito nomeado
e deixou um sub-escopo que o relatório-fonte descrevia. Um item **melhorou** de 🔴 para 🟡
(`token-claude-md-426-lines-…`: os três blocos estão hoje extraídos) e um deveria ser 🟢, não 🟡
(`token-pre-tool-use-01-check-updates-…`: o sintoma morreu por outra via).

Apenas **1 dos 75** não teve commit da janela tocando o campo `alvo:` — e é exatamente o caso que a
nota de método de 2026-10-17 prevê. Classificá-lo 🔴 por construção teria sido um falso positivo;
três outros itens dependeram da mesma nota.

## Mortalidade da Fase 1b — **3,85% (5 de 130)**, cobertura **130 de 130 (100%)**

| Estado | Qtd | % |
|---|---|---|
| Ainda reproduz | 125 | 96,2% |
| 🟢 **Resolved** | 4 | 3,1% |
| ⚰️ **Obsoleto** | 1 | 0,8% |

Segunda maior mortalidade desde a consolidação, atrás apenas dos 9,3% de 2026-10-02. **E o número
não é imobilidade: 71 dos 130 alvos abertos (55%) foram tocados pelo delta, e 66 desses 71 seguem
reproduzindo.** O banco está medindo durabilidade real.

**24 fingerprints abertos mediram pior** — o triplo do recorde anterior (8 em 2026-10-24). As piores:
`interaction-patterns` **+240% agregado** (209 ln × 26 → 372 × 45); `docs/wiki/README.md`
13.715 → **27.768 B** (+102% em 28 dias, 15,8× sobre setembro); `CHANGELOG.md` 441 → **2.463 ln**;
`session-start.sh` 118 → **460 ln**; `install.sh` 503 → **1.405 ln**; índice de skills symlinkadas
12.751 → **19.360 chars**; `checks-list.md` 668 → **887 ln**; `fix-patterns.md` 517 → **654 ln**.

## Achados originais por eixo — **19**

| Eixo | Achados | Nota |
|---|---|---|
| **A — Agnosticismo de stack** | **0** | 130 hits → 27 candidatos → 0 violações. Quarto zero em cinco passes, e **estrutural**: os 5 arquivos novos de `agents/`/`commands/` são agnósticos por verificação direta |
| **B — Referências e consistência** | **3** | 2 HIGH, 1 LOW. Os quatro helpers saem limpos — e é a estreiteza da cobertura deles que explica os dois HIGH |
| **C — Fluxos, comandos e automação** | **8** | 3 MEDIUM-HIGH, 2 MEDIUM, 2 LOW-MEDIUM, 1 LOW. 31 candidatos levantados |
| **D — Agentes e skills** | **5** | 1 HIGH, 3 MEDIUM-HIGH, 1 LOW-MEDIUM. Quatro dos cinco são sobre a persona e o gate novos do ADR-0062 |
| **E — Economia de tokens** | **3** | 1 MEDIUM-HIGH, 2 MEDIUM. Eixo mais saturado do banco: 8 dos 11 candidatos morreram no pré-filtro |

## Tabela de severidade

| Severidade | Qtd | Fingerprints |
|---|---|---|
| **HIGH** | 3 | `gov-committed-install-copy-stale-vs-source-no-gate` · `docs-sync-agent-reference-omits-orchestrator-and-18-agent-count-claims` · `gov-supervision-gate-demands-review-marker-in-documented-no-marker-cases` |
| **MEDIUM-HIGH** | 7 | `flow-orchestrator-route-table-covers-10-of-42-commands-no-gate` · `flow-commit-md-no-branch-for-adr-0059-secret-guard-refusal` · `gov-seed-scan-regex-blind-to-flutter-swift-kotlin-rn-dotnet-rust-supabase` · `agent-orchestrator-session-guard-signal-fails-under-nested-spawn` · `agent-orchestrator-missing-from-plan-mode-loaders-gate` · `agent-orchestrator-route-has-no-path-to-architecture-work` · `token-project-context-untrusted-table-duplicated-headerless-19-agents` |
| **MEDIUM** | 4 | `flow-hook-prefs-gates-three-precedence-orders-raw-grep-no-helper` · `flow-findings-gate-dispatch-keyed-to-hardcoded-pt-br-labels-in-four-commands` · `token-branch-overlap-hook-forks-python-and-reparses-cache-per-path` · `token-language-hook-restates-370-char-policy-on-every-prompt-uncapped` |
| **LOW-MEDIUM** | 3 | `flow-install-md-yes-strip-rule-listed-after-the-branch-it-must-precede` · `auto-subagent-start-stop-dispatchers-opposite-exit-policies-undocumented` · `ref-size-limits-and-ci-lint-comments-state-stale-agent-command-counts` |
| **LOW** | 2 | `ref-readme-sync-pair-discovery-does-not-exclude-worktrees` · `flow-down-md-restates-two-local-environment-stop-rules-it-forbids-restating` |

## Os três achados mais graves

**1. `gov-committed-install-copy-stale-vs-source-no-gate` (HIGH).** A cópia instalada versionada em
`.dev-team-agents/` é o que os 168 symlinks de `.claude/` resolvem, e está 5 dias atrás: 58 de 664
arquivos divergem e 16 nem existem lá, entre eles `agents/orchestrator.md`,
`commands/orchestrate.md`, `03b-staged-secret-guard.sh` e todo o plumbing de supervisão do
ADR-0062. Nenhum gate compara os dois lados. Consequência verificada: três features desta janela
são inalcançáveis nas sessões do próprio repositório, e o guard de secret sobrevive apenas por uma
entrada legada de caminho relativo que `scripts/install.sh:600` documenta como não confiável.

**2. `gov-supervision-gate-demands-review-marker-in-documented-no-marker-cases` (HIGH).** O gate de
SubagentStop do ADR-0062 testa só `agent in REVIEWERS`, sem olhar o tipo de passagem — então
bloqueia exatamente os três casos em que `skills/shared/review-result/SKILL.md:26,28` e
`agents/seo-specialist.md:90` mandam **não** emitir marcador, e a mensagem do hook sugere
"`0 when clean`". O agente reemite com `findings=0`, e `docs/specs/task-board.md:413` resolve a
janela como `"passed"`: **uma QA que não conseguiu rodar e um router que apenas delegou passam a
ler como revisão aprovada** — o falso positivo que o item (5) de `:659` existe para impedir.

**3. `flow-commit-md-no-branch-for-adr-0059-secret-guard-refusal` (MEDIUM-HIGH).** O único comando
que executa commits não conhece o gate que pode recusá-los: `grep -n "gitleaks\|ADR-0059"
commands/commit.md` → 0 ocorrências, enquanto `03b-staged-secret-guard.sh:217-226` recusa com exit 2
e `:25` declara que não há escape hatch. A opção que o comando oferece ("Commit anyway") é
inalcançável por desenho, então um falso positivo de gitleaks deixa o `/devteam:commit` em loop. Em
paralelo, o item 5 de `skills/shared/feature-learn/SKILL.md:102` roda o mesmo gitleaks **sem escopo**
e pode desindexar silenciosamente um arquivo de código do usuário.

## Descartados por duplicação — **51**

| Eixo | Descartados | Portas predominantes |
|---|---|---|
| A | 27 | 15 na Porta 1 (literal), 6 na Porta 3, 2 na Porta 4, 2 na Porta 5, 2 por mérito após Porta 2 |
| B | 3 (+2 refutados por evidência própria) | Porta 3, 3 de 3 nos três casos |
| C | 5 (+1 cross-eixo) | Portas 1, 3 e 4 |
| D | 5 | Porta 3 (3 de 3) em três; Porta 5 em dois |
| E | 8 | Portas 2, 3 e 4; 1 descartado no mérito |
| **cross-eixo** | **2 pares fundidos** | `size-limits` comment (B↔D) e `04-branch-overlap` forks (C↔E), ambos 3 de 3 |

Dois descartes merecem registro como **re-medição**, não como achado: a tabela de comandos do README
passou de 34/35 para **40/42** (o segundo ausente é `down`, não só `install`), e
`interaction-patterns` está em **58 carregadores** (era 45 na re-medição da Fase 1b).

Dois candidatos foram **refutados por evidência própria**, o que é o valor da seção: a premissa de
que `scripts/lib/auth-config.json` `gate_mode` não tem gate de CI é falsa
(`tests/test_auth_gate.py:186-188` fixa as três cópias e `03-python.sh:25` roda a suíte), e a de que
`install.sh` não injetaria `PostToolUseFailure` no upgrade também
(`install.sh:879-907` tem bloco dedicado, coberto por `tests/test_tasks.py:1420`).

## Correções de registro

Sete correções de premissa estão em `00-guardiao-verificacao.md` § Correções de premissa. As duas
que mais importam para o próximo pass: **`SKILL_DESC_STRICT` não foi removido** — a nota de
2026-10-10 em `docs-sync-claude-md-102-states-skill-desc-strict-false-…` está errada, a variável
está viva em `helpers/agent-lint.sh:98` (`=true`) e o achado volta à forma original; e
**`scripts/n.sh` nunca existiu** — é artefato de um `rg -r n` sobre `validate-commit-msg.sh`,
citado em três relatórios.

**Aviso operacional:** `helpers/orphan-skill-scan.sh` tem uma fase de auto-reparo com `sed -i`
sobre `agents/` e `commands/` (`:60-110`). Neste `HEAD` não havia nada a reparar, mas rodá-lo num
`HEAD` com referência quebrada **modifica a árvore** — o que violaria a regra 5 do prompt de
auditoria.
