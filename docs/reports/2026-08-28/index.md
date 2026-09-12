# Auditoria Guardiã — 2026-08-28

**Data:** 2026-08-28 · **Baseline:** `HEAD` = `a67cac9` · **Baseline anterior:** `a67cac9`

## Sumário executivo

**O baseline não se moveu.** `HEAD` é o mesmo `a67cac9` que o pass de 2026-08-21 registrou como o
seu próprio baseline; o último commit do repositório é de 21 de agosto, **sete dias atrás**. O delta
de código é zero arquivo em zero commit.

**E o output daquele pass nunca foi commitado.** `git status --short` devolve
` M docs/reports/_index.md` e `?? docs/reports/2026-08-21/`: os sete relatórios e as **37
fingerprints** do pass anterior existem apenas no disco desta máquina.
`git show HEAD:docs/reports/_index.md | grep -cE '^- \`[a-z]'` devolve **176**; a árvore de trabalho
devolve **213**.

Esse é o achado principal do pass, e ele é sobre o próprio processo de auditoria — registrado como
`gov-audit-pass-output-uncommitted-with-no-detection-mechanism` (HIGH). O banco de fingerprints é o
mecanismo anti-duplicação de todo o sistema; um pass cuja atualização do banco não chega ao remoto faz
o **pass seguinte redescobrir os mesmos 37 achados**. Este pass só escapou porque detectou a árvore
suja na Fase 0 e passou a tratar a versão de working-tree como autoritativa. Um pass rodando em clone
limpo teria gerado 37 duplicatas silenciosas. E não há gate: `stop/03b-fingerprint-uniqueness.sh`
verifica a **unicidade** dos slugs quando `docs/reports/` é tocado, mas nada verifica que o toque foi
**commitado** — e `user-data/session-summary.md` sequer existe neste repositório, então nem esse
rastro sobrou.

**O segundo padrão do pass é a distância entre a regra escrita e o arquivo que o agente realmente
lê.** Quatro dos onze achados são a mesma falha em superfícies diferentes:

1. Os **9 agentes que editam arquivos** delegam a cascata de worktree a `CLAUDE.md` → uma seção que
   não existe com aquele nome, num arquivo que `KEEP_ROOT` (`scripts/install.sh:369`) **remove do
   pacote instalado**. E dois deles mandam explicitamente *não* carregar a skill que contém a
   cascata, no exato ramo em que precisariam dela.
2. O `<HARD-GATE>` do Scope Lock é escrito nominalmente para quatro agentes de execução, e **nenhum
   dos quatro carrega a skill que o contém** — os comandos a carregam no orquestrador, e um `Load` no
   contexto principal não atravessa a fronteira do Task tool.
3. Quatro comandos de implementação mandam usar a ferramenta **`question`**, que não existe no Claude
   Code, exatamente no gate que decide se os findings de review são aplicados.
4. `CLAUDE.md:210` declara a Quiz-first Rule dos comandos imposta por `agent-lint.sh`; **o linter
   nunca lê `commands/*.md`** — reproduzido: um prompt `(yes/no)` injetado em `commands/qa.md` passa
   com `agent-lint: clean ✓`.

Nenhum desses quatro é detectável por gate. Todos foram reproduzidos mecanicamente.

---

## Cobertura e placar

| Métrica | Valor |
|---|---|
| Fingerprints vivos no banco (working tree) | 213 |
| Conjunto verificável (✅ Executed + ⚠️ Partial) | 121 |
| Já verificados em 2026-08-21 contra este mesmo `HEAD` | 48 — inclui **todos** os 18 HIGH/MEDIUM-HIGH |
| **Cobertura da Fase 1 — bloco novo** | **22 de 73 não cobertos (30%)** |
| **Cobertura da Fase 1 — acumulada contra `a67cac9`** | **70 de 121 (58%)** |
| Placar do bloco novo | **18 ✅ · 2 🟡 · 2 🔴** — 82% confirmado, **9,1% reaberto** |
| Placar acumulado contra `a67cac9` | **61 ✅ · 5 🟡 · 4 🔴** — 87% confirmado, **5,7% reaberto** |
| **Mortalidade da Fase 1b** | **0 de 50 (0%)** — 0 🟢 · 0 ⚰️ |
| Achados originais publicados | **21** |
| Candidatos descartados por duplicação | **57** |

**Critério de amostragem.** O conjunto verificável excede 60, então a regra manda verificar todos os
HIGH e MEDIUM-HIGH mais 30% do restante. Os 18 HIGH/MEDIUM-HIGH foram integralmente verificados em
2026-08-21 **contra este mesmo sha**; sem nenhum commit desde então, nenhum daqueles vereditos pode
ter mudado. A amostra deste pass foi portanto redirecionada ao complemento: 22 dos 73 itens que o pass
anterior não cobriu — todos MEDIUM ou abaixo.

A reabertura (9,1% no bloco novo, 5,7% acumulada) está **abaixo do limiar de escalonamento de 15%**.
A integridade do banco não é o problema deste pass.

A **mortalidade zero da Fase 1b não é sinal de saúde**: com zero commits desde o registro, não havia
mecanismo pelo qual um achado pudesse ter sido corrigido de passagem. Ela mede a imobilidade do
repositório, não a durabilidade do banco.

### Os quatro vereditos divergentes da Fase 1

| Fingerprint | Marca | Motivo |
|---|---|---|
| `ref-release-prep-skill-exists-twice-…` | 🔴 | O único commit da janela tocou o alvo para reescrever **uma linha de `description`** — efeito colateral do corte para o orçamento de 95 chars. As duas cópias seguem com 88 vs. 182 linhas e destinos de instalação opostos |
| `flow-stop-no-zombie-state-cleanup-…` | 🔴 | **Nenhum commit da janela tocou o alvo.** `.worktree-session` segue sem TTL e sem rotina de limpeza; um marcador remanescente direciona em silêncio a próxima sessão não relacionada |
| `ref-notification-system-content-triplicated-…` | 🟡 | Dois dos três vértices resolvidos; `skills/shared/notifier/SKILL.md:113-133` ainda carrega a fórmula e os 15 textos de tip — agora como **quarta** cópia |
| `ref-agent-creator-location` | 🟡 | `bbb311a` documentou a divergência (remediação do fingerprint **irmão**), mas não moveu nenhum arquivo; `agent-creator` segue inalcançável por qualquer provider instalado |

---

## Achados por eixo

| Eixo | Originais | Observação |
|---|---:|---|
| **A** — Agnosticismo de stack (varredura integral) | **0** | 124 candidatos → 0 violações. **Eixo saturado** — dos 12 candidatos genuínos sob seção de comportamento, **10 já estão registrados e abertos**, dois deles MEDIUM-HIGH há mais de um mês |
| **B** — Referências e consistência | **6** | 1 HIGH · 1 MEDIUM-HIGH · 2 MEDIUM · 1 LOW-MEDIUM · 1 LOW. Os quatro helpers rodam limpos exceto `size-limits.sh` (achado já aberto) |
| **C** — Fluxos, comandos e automação | **7** | 3 HIGH · 3 MEDIUM-HIGH · 1 MEDIUM. Todos reproduzidos em sandbox descartável |
| **D** — Agentes e skills | **5** | 1 HIGH · 1 MEDIUM-HIGH · 3 MEDIUM. Os 18 agentes passam nos cinco requisitos estruturais e no espelhamento de tier |
| **E** — Economia de tokens | **3** | 1 MEDIUM-HIGH · 2 MEDIUM, todos quantificados |
| **Total** | **21** | — |

## Tabela de severidade

| Severidade | Qtd. | Fingerprints |
|---|---:|---|
| **HIGH** | 5 | `gov-audit-pass-output-uncommitted-with-no-detection-mechanism` · `flow-review-command-writes-and-commits-while-documented-as-read-only` · `auto-agent-lint-quiz-first-never-scans-commands-dir` · `agent-worktree-cascade-delegates-to-unshipped-claude-md` · `docs-sync-claude-md-effort-key-scope-vs-agent-effort-map` |
| **MEDIUM-HIGH** | 6 | `flow-question-tool-name-in-four-implementation-command-findings-gates` · `auto-adr-gap-check-dependency-signal-blind-to-staged-and-committed-changes` · `auto-slim-bootstrap-shape-contract-cannot-fail-the-build` · `skill-spec-gate-scope-lock-hard-gate-unreachable-by-execution-agents` · `token-status-and-version-inline-bash-scripts-paid-twice-per-invocation` · `docs-sync-docs-agents-md-worktree-asks-once-vs-preference-default` |
| **MEDIUM** | 8 | `ref-command-description-duplicated-frontmatter-vs-commands-json` · `docs-sync-claude-md-coding-agents-list-omits-seo-specialist` · `flow-rule-and-sync-rules-listed-as-technical-writer-but-never-delegate` · `agent-jira-detection-branch-naming-block-duplicated-no-canonical-home` · `agent-docs-sync-task-closure-missing-mobile-devops` · `agent-seo-specialist-outside-coding-agent-contract` · `token-checks-list-loads-all-three-provider-blocks-after-step-0-resolved-one` · `token-fix-patterns-517-lines-loaded-whole-to-apply-one-of-25-auto-fixes` |
| **LOW-MEDIUM** | 1 | `docs-sync-claude-md-context-list-item-count-12-vs-11` |
| **LOW** | 1 | `docs-sync-readme-ptbr-agents-link-points-to-english-doc` |

**Total: 21 fingerprints publicados** — 5 HIGH · 6 MEDIUM-HIGH · 8 MEDIUM · 1 LOW-MEDIUM · 1 LOW.

---

## Os três achados mais graves

### 1. `gov-audit-pass-output-uncommitted-with-no-detection-mechanism` — HIGH

O pass de 2026-08-21 gerou 37 fingerprints e sete relatórios que nunca chegaram ao remoto, e nenhum
mecanismo do repositório detecta essa condição. O banco anti-duplicação existe exatamente para impedir
que um pass redescubra o que outro já achou; um pass que não commita o banco garante essa
redescoberta. A verificação já está escrita no `_prompt-auditoria.md:360-366` — falta torná-la
bloqueante em vez de informativa.

### 2. `agent-worktree-cascade-delegates-to-unshipped-claude-md` — HIGH

Os 9 agentes que editam arquivos apontam para `CLAUDE.md` → "Worktree Isolation", um rótulo que não
existe (`CLAUDE.md:111` chama a seção de "Canonical worktree decision cascade") num arquivo que
`KEEP_ROOT` remove do pacote. O `CLAUDE.md` que o agente encontra é o **do projeto do usuário**, que o
instalador populou com dois blocos gerenciados, **nenhum deles a cascata** — o ponteiro resolve para
um arquivo que existe, parece autoritativo e está errado. E a rota de fallback está fechada por
construção: `mobile-developer:39` e `devops-specialist:40` mandam explicitamente *não* carregar
`skills/shared/worktree/SKILL.md` no ramo `worktree=no`, que é exatamente o ramo em que o agente
precisa escrever `worktree=no branch=<name>` — formato que `grep -rn 'worktree=no' agents/` mostra
não existir em **nenhum** corpo de agente. A garantia de `CLAUDE.md:121` ("resolve the worktree
decision **exactly once**") não tem mecanismo em projeto instalado.

O repositório já diagnosticou essa classe exata de falha para outra regra — o comentário de
`scripts/install.sh:868-872` justifica o Step 8b dizendo que sem a injeção não há "shipped file"
mandando carregar `conventional-commits`. A cascata de worktree não recebeu o mesmo tratamento.

### 3. `flow-review-command-writes-and-commits-while-documented-as-read-only` — HIGH

`commands/review.md:66` manda editar arquivos e criar commits no contexto principal, sem plano e sem
delegação — contradizendo a linha `:35` do próprio arquivo ("**MANDATORY:** … Do NOT review inline —
always delegate"). E `CLAUDE.md:254` classifica `/devteam:review` como "**read-only by design**",
usando exatamente essa classificação como a razão pela qual o comando não precisa de Plan Gate. É a
única exceção de Plan Gate do repositório que hoje protege um caminho de escrita, e ela se
autojustifica com uma afirmação falsa.

---

## Descartados por duplicação

**57 candidatos rejeitados** — 12 no Eixo A, 14 no B, 10 no C, 8 no D e 13 no E — distribuídos por
porta:

| Porta | Qtd. | Natureza |
|---|---:|---|
| **Porta 1 — literal** (slug já existe) | 5 | `ref-notifier-documented-as-live-in-four-docs-…`, `docs-sync-claude-md-102-states-skill-desc-strict-false-…`, `agent-database-specialist-rls-as-engine-neutral-…`, `agent-security-specialist-cicd-checklist-github-actions-only-vocabulary`, `agent-reviewer-linter-config-three-divergent-…` |
| **Porta 3 — semântica** (2 ou 3 de 3 atributos) | 21 | Famílias `ref-check-updates-shim-…`, `ref-tool-map-tool-rewrites-…`, `token-work-feedback-opt-out-gate-…`, `token-output-format-third-copy-…`, `token-install-sh-503-lines-…`, `flow-helpers-archive-index-sh-orphan-…`, `skill-orchestration-spawn-integrity-…`, `ref-orphan-skill-scan-reports-design-system-audit-…` |
| **Porta 4 — escopo menor sem sub-escopo novo** | 5 | `devops-specialist.md:137-148`, `output-format` 190×9, lista das 13 categorias em `health-check.md:39-51`, `preferences.json` lido inteiro em 31 sítios, passos 9–10 da Context Loading Order |
| **Porta 5 — estado** (já no conjunto aberto) | 25 | `CLAUDE.md` 602 linhas · `interaction-patterns` 209×34 · `token-efficiency` 160×18 · `orchestration` 391 linhas · `migration-v1-to-v2` 438 linhas · teto 205 vs. 211 · `size-limits.sh` exit 1 · `frontend-test-specialist` SonarQube · `frontend-developer.md:3` · `database-specialist.md:133` · `audit.md:54,126,128` · `relayout.md:32` · `mobile.md:19,26` · `setup-assistant.md:146-147` · `commit.md:125-128` · `_index.md:103` legenda "All 131 entries" · `work-feedback` inalcançável |
| **Refutado por evidência** | 1 | `soften_plan_gate` removeria `Task: $ARGUMENTS` nos comandos `opt_out` — **nenhum** deles carrega essa linha isolada; o `re.sub` é no-op hoje |
| **Descartado por mérito** (passou as portas, não sustenta achado) | 3 | `docs/agents.md:42` (omissão com ponteiro válido) · `docs/*.md` sem par pt-BR (escolha editorial) · `.github/scripts/ci/**` sem shellcheck (ferramenta indisponível — sem defeito concreto é proposta de escopo, não achado) |

O **Eixo A** concentra o maior volume de descartes: dos 12 candidatos genuínos sob seção de
comportamento, 10 caíram na Porta 5. O detalhamento completo, com o motivo por candidato, está em
[`01-agnosticismo-de-stack.md`](01-agnosticismo-de-stack.md) e na seção "Descartados por duplicação"
de cada relatório de eixo.

---

## Leitura do pass

Três passes consecutivos vinham apontando que as mudanças de comportamento do delta carregavam
defeito verificado sem gate que as pegasse. **Este pass não tem delta.** O que ele mede é o outro
lado: um repositório parado há sete dias, com 79 achados abertos, mortalidade zero por ausência de
commits, e o output do pass anterior nunca publicado.

A taxa de descoberta não é o gargalo — o Eixo A prova isso ao render 124 candidatos e zero achados
originais, porque tudo o que ele encontraria já está encontrado e **aberto**. O gargalo é a
execução, e o achado nº 1 deste pass mostra que o próprio ciclo de auditoria não está fechando: o
trabalho é feito, escrito no disco e não commitado.

---

## Arquivos deste pass

| Arquivo | Conteúdo |
|---|---|
| [`00-guardiao-verificacao.md`](00-guardiao-verificacao.md) | Fases 1 e 1b, item a item |
| [`01-agnosticismo-de-stack.md`](01-agnosticismo-de-stack.md) | Eixo A — varredura integral, 124 → 0 |
| [`02-referencias-e-consistencia.md`](02-referencias-e-consistencia.md) | Eixo B |
| [`03-fluxos-e-comandos.md`](03-fluxos-e-comandos.md) | Eixo C |
| [`04-agentes-e-skills.md`](04-agentes-e-skills.md) | Eixo D |
| [`05-economia-tokens.md`](05-economia-tokens.md) | Eixo E |
