# Auditoria Guardiã — 2026-08-14

**Data:** 2026-08-14 · **Baseline:** `HEAD` = `c03f898` · **Baseline anterior:** `3fbe371`

## Sumário executivo

Delta pequeno desde o baseline anterior: **16 arquivos, +624 / −8 linhas**, em 4 commits de código
(2026-08-12 → 2026-08-14). Todos os gates automáticos seguem verdes — `agent-lint`, `size-limits`,
`orphan-skill-scan`, `orphan-template-scan`, `check-fingerprint-uniqueness` e `archive-index
--dry-run`.

**A verificação não é o achado principal deste pass — os eixos são.** A taxa de reabertura ficou em
**6,1%** (3 de 49), bem abaixo do limiar de 15%, e a Fase 1b teve **0% de mortalidade**. O banco está
íntegro. O que o pass encontrou de mais grave está na Fase 2: **26 achados originais**, incluindo
**5 HIGH**, e a confirmação de que a hipótese do pass anterior se repete.

**A hipótese do pass anterior se confirma pela segunda vez.** Em 2026-08-12 (2ª execução) foi
registrado que as 3 mudanças de comportamento do delta traziam defeito verificado e que nenhum gate
automático cobre essa classe. Neste delta, **3 dos 4 commits carregam defeito reproduzido**:

| Commit | O que declara | O que foi verificado |
|---|---|---|
| `c03f898` — detect unscoped make/composer test wrappers | Fecha um buraco do guard | Dois falsos positivos novos reproduzidos (`cmake `, `&&` atravessado, `composer test <path>`), e **não** fechou o `sed` guloso de `:22` que já estava aberto — ampliou a superfície dele |
| `f0fb093` — stop aborting the update on slim installs | Repara o abort | O guard Codex nunca é falso (ramo morto); a classe `exit 1` (jq/python3/snippet vazio) ainda mata o update sob `set -e` — reproduzido |
| `f88ee51` — add commit-and-push step to metrics prompts | Adiciona um passo | Bloco copiado do prompt de métricas: diz "two report files" (são 8), manda `push … main` contra a regra inviolável 8 do próprio arquivo, e carrega a mensagem de commit de métricas |
| `21fceb4` — close orchestrator liveness and background-wait gaps | Fecha lacunas | Sem defeito funcional direto, mas introduziu drift de tool-names entre provedores e duplicou inline uma regra com casa canônica |

Um gate novo (`helpers/preferences-sync-lint.sh`, `26520b9`) foi criado no intervalo e **passa ao
lado do achado que deveria cobrir**: valida os dois espelhos de documentação de
`preferences-defaults.json` e exclui o heredoc de `install.sh`, que é onde a drift de
`auto_learn_before_commit` vive. Reporta "clean ✓" com o defeito ativo.

## Cobertura da Fase 1

Conjunto verificável = **124** (122 ✅ Executed + 2 ⚠️ Partial), acima do limiar de 60 → amostragem.
Critério: **todos** os HIGH (11) e MEDIUM-HIGH (7), mais amostra sistemática de 30% dos 103 restantes
(31 itens, passo determinístico sobre a ordem do banco).

**Verificados: 49 de 124 (40%).**

### Placar

| Marca verificada | Qtd. | % da amostra |
|---|---|---|
| ✅ Feito | 42 | 86% |
| 🟡 Parcialmente feito | 4 | 8% |
| 🔴 Não feito | 3 | 6% |

Taxa de reabertura (🔴): **6,1%** — abaixo do limiar de escalonamento de 15%.

**Nenhuma das 7 divergências é nova.** Cinco (linhas 138, 148, 192, 223, 247) já haviam sido
reabertas ou marcadas 🟡 em passes anteriores e **continuam abertas 14 dias depois**; duas (225, 240)
são reaberturas de primeira vez sobre marcações de 2026-07-31. Em ambos os casos de 🔴 novo, a marca
✅ confundiu **uma parte entregue com o achado inteiro**:

- `token-token-efficiency-skill-itself-154-lines-eager-loaded…` — o commit unificou a *redação* da
  linha de load (escopo do fingerprint vizinho) e nada mais. O load segue eager em **18 de 18**
  agentes e a skill cresceu de 154 para 160 linhas: o achado piorou.
- `token-claude-md-426-lines-still-monolithic…` — segunda confirmação. 586 linhas hoje contra 425 na
  abertura (+38%); a tabela de comandos segue inline em `:211`.

Também foi corrigido um crédito de resolução: a anotação 🟢 da linha 148 atribuía o fecho a
`156771b` (que só reativou arquivos renomeados); a resolução real veio de `f1ca129` em 2026-08-06.

## Mortalidade da Fase 1b

**0 de 25 (0%)** — 0 🟢 · 0 ⚰️. Os 25 achados abertos foram relocalizados por símbolo e todos
reproduzem no HEAD. Nenhum marcador a aplicar.

Zero mortalidade com banco saudável significa que nada apodreceu — mas **quatro achados
degradaram materialmente** sem que ninguém tenha decidido nada:

| Fingerprint | Abertura | Reverificação anterior | HEAD |
|---|---|---|---|
| `token-changelog-already-growing…` | 441 linhas | 441 | **962** (+118%) |
| `flow-session-start-118-lines-monolithic…` | 118 linhas | 174 | **306** (+76%) |
| `token-install-sh-503-lines…` | 503 linhas | 947 | **1086** (+15%) |
| `token-interaction-patterns-209-lines…` | 26 carregadores | 26 | **33** (≈5.610 linhas agregadas) |

## Achados originais por eixo

| Eixo | Arquivo | Achados |
|---|---|---|
| A — Agnosticismo de stack | [`01-agnosticismo-de-stack.md`](01-agnosticismo-de-stack.md) | 3 (de 122 candidatos) |
| B — Referências e consistência | [`02-referencias-e-consistencia.md`](02-referencias-e-consistencia.md) | 6 |
| C — Fluxos, comandos e automação | [`03-fluxos-e-comandos.md`](03-fluxos-e-comandos.md) | 7 |
| D — Agentes e skills | [`04-agentes-e-skills.md`](04-agentes-e-skills.md) | 5 |
| E — Economia de tokens | [`05-economia-tokens.md`](05-economia-tokens.md) | 5 |
| **Total registrado** | | **26** |

> Os arquivos dos eixos C e D contêm 9 e 6 achados respectivamente; **3 foram consolidados como
> duplicatas cross-axis** na etapa de banco (ver abaixo) e não entram no total registrado.

### Distribuição por severidade

| Severidade | Qtd. |
|---|---|
| HIGH | 5 |
| MEDIUM-HIGH | 8 |
| MEDIUM | 10 |
| LOW-MEDIUM | 3 |
| LOW | 0 |

## Os 3 achados mais graves

### 1. `ref-tool-map-tool-rewrites-loaded-but-never-emitted-by-render-provider` — HIGH

O mapa de reescrita de nomes de ferramentas é lido em `render_provider.py:742` e usado **apenas como
booleano** — nunca é emitido. `CLAUDE.md:67` e `docs/providers.md:127` documentam o rewrite como
mecanismo ativo. Reproduzido: `AskUserQuestion` sai três vezes intacto no
`.opencode/agents/setup-assistant.md` renderizado. Duas superfícies de documentação afirmam como
verdade corrente algo que o código não faz, e o efeito prático é que agentes renderizados para
opencode e Codex instruem o modelo a chamar ferramentas que não existem naquele provedor.

### 2. `skill-token-efficiency-background-mgmt-contradicts-orchestration-discipline` — HIGH

`skills/shared/token-efficiency/strategies.md` § Background Process Management ensina fire-and-forget
("don't poll", "let the user decide") e lê shell de background com `TaskOutput(task_id=…)` — o
oposto direto da § Background Process Discipline que `21fceb4` acabou de criar em
`skills/architecture/orchestration/SKILL.md`. A versão errada alcança **18 de 18** agentes; a certa
alcança **1**. A regra nova nasceu já derrotada pela distribuição.

### 3. `flow-update-sh-codex-slim-guard-dead-branch-false-strip-claim` — HIGH

O guard adicionado por `f0fb093` nunca avalia como falso — `agents/product-analyst.md` e `scripts/`
estão sempre presentes na instalação. Pior, o comentário do próprio commit e a entrada de CHANGELOG
afirmam que `strip-tarball.sh` remove o cross-CLI plumbing, e `strip-tarball.sh` documenta
exatamente o contrário. O modo de falha que motivou o fix (`exit 1` por `jq`/`python3` ausente ou
snippet vazio) **continua matando o update sob `set -e`** depois do core ter sucedido — reproduzido.

## Descartados por duplicação

### Cross-axis (consolidados na etapa de banco)

| Descartado | Porta | Absorvido por |
|---|---|---|
| `flow-02c-wrappers-have-no-scoped-row-in-runner-filters-table` (Eixo C) | 3 — alvo, causa raiz e remediação coincidem (3 de 3) | `ref-02c-guard-make-composer-shapes-have-no-row-in-scoped-test-runner-table` (Eixo B, MEDIUM-HIGH) |
| `flow-parallel-bash-rule-homed-in-scoped-test-execution-skill` (Eixo C) | 3 — mesmo alvo, mesma causa, mesma remediação | `ref-scoped-test-execution-bash-parallelism-section-outside-declared-canonical-scope` (Eixo B, MEDIUM) |
| `skill-scoped-test-execution-hosts-general-parallel-bash-rule-off-topic` (Eixo D) | 3 — terceira formulação do mesmo achado | idem |

### Por eixo (registrados nos relatórios de origem)

**Eixo A — 119 dos 122 candidatos caíram.** ~24 falsos positivos por substring
(`flaws`→aws, `expression`→express, `honest`→nest, `perspective`→rspec, `pipeline`→pip,
`Auto-reactivation`→react, `explicit bootstrap`→bootstrap); ~55 tabelas de detecção; ~6 blocos de
exemplo/template de output; ~12 listas de skill condicional; ~8 ilustrações `e.g.` dentro de regra
já agnóstica; ~6 acoplamentos legítimos ao próprio harness; 1 anti-acoplamento. Rejeitados por porta:
`relayout.md:32`, `frontend-test-specialist.md:139-151`, `frontend-developer.md:3`,
`devops-specialist.md:46-56`, `audit.md:126-128`, `commit.md:135-138`, `setup-assistant.md:146-147`
(porta 5 — conjunto aberto); `devops-specialist.md:137-148` (porta 4); `devops.md:2,14`,
`frontend-reviewer.md:112,114`, `database-specialist.md:66-73` (porta 3).

**Eixo B — 7 descartes.** `sed` guloso do `02c` e comentário graphify-precedent (porta 5); rotação do
CHANGELOG (porta 3, 2/3); omissões da File Structure do `CLAUDE.md` (porta 5); "agent-lint não valida
coluna Tier" (porta 3 — é a remediação de outro achado); `composer test --filter` como falso positivo
lógico (fora de eixo → Eixo C); Background Process Discipline sem cláusula de indisponibilidade
(porta 3, absorvido como evidência).

**Eixo C — 7 descartes.** `sed` guloso do `02c` (porta 5); comentário graphify-precedent (portas 1+5);
JSON concatenado de dois sub-scripts PreToolUse (**refutado** — Glob/Grep e Bash são exclusivos);
`session-start.sh` monolítico e `install.sh` não fragmentado (porta 5); `update.sh` sem integrity
check (porta 3, a+b); dispatcher sem allowlist (**refutado** — `SUBSCRIPT_RE` existe nos dois).

**Eixo D — 6 descartes.** `orchestration/SKILL.md` 377 linhas sem `references/` (porta 3);
divergência de redação do `## Before You Finish` (**não reproduz** — as 18 seções são byte-idênticas);
divergência de banner vs. `tiers.json`/`agent_effort` (**não reproduz** — 18/18 batem, incluindo os
cinco `low`); roster sem `software-architect`/`setup-assistant` (gateado por `ROSTER_EXEMPT`);
`software-architect.md` no teto de 211 (porta 3 — o ângulo novo foi reportado com alvo `CLAUDE.md`);
`skill-adr-coverage-only-architect` (porta 5).

**Eixo E — 9 descartes.** `02c` captura `sed` gulosa (porta 3); `CLAUDE.md` monolito (porta 5 — tema
reaberto 🔴); `interaction-patterns`, `migration-v1-to-v2` (porta 5); `token-efficiency` 160×18
(portas 1+3); `backlog-template` e bloco Docker eager de `project-context` (porta 1);
`software-architect.md:88-89` duplicando Spawn Integrity 4–5 (porta 3 — matéria do Eixo D);
`output-format` 190×9 (porta 4 — sem hit no banco, mas todo o arquivo é template acionável, sem
achado).

## Gates

```
agent-lint:                     clean ✓
size-limits:                    clean ✓
orphan-skill-scan:              clean ✓
orphan-template-scan:           clean ✓
check-fingerprint-uniqueness:   ✓ All 150 fingerprint slugs are unique across 1 bank file(s).
archive-index --dry-run:        ✓ No entries older than 90 days (cutoff 2026-05-16).
```

Rotação não é necessária neste pass.

## Nota de execução

Este pass rodou como tarefa agendada, sem o usuário presente. O **Plan Gate** da regra 7 do prompt
foi executado sem aprovação interativa por essa razão; nenhuma escolha de escopo foi feita fora do
que o prompt já especifica. Nenhum arquivo fora de `docs/reports/2026-08-14/` e
`docs/reports/_index.md` foi modificado, conforme a regra 5.
