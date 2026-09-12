# Fases 1 e 1b — Verificação guardiã (2026-09-11)

**Data:** 2026-09-11 · **Baseline:** `HEAD` = `9530551` · **Baseline anterior:** `a67cac9`

---

## O delta: o baseline finalmente mudou, mas o código não

`git rev-parse --short HEAD` devolve `9530551`. É a primeira vez em quatro passes que o sha difere
do baseline anterior. O delta, porém, não contém código:

```
$ git log --format='%h %ad %s' --date=short a67cac9..HEAD
9530551 2026-09-04 docs(reports): metrics reports updates
$ git diff --stat a67cac9..HEAD
 docs/reports/metrics-last-20-days.en.md | 1167 +++++++++++++++--------------
 docs/reports/metrics-last-20-days.md    | 1123 ++++++++++++++++-------------
 2 files changed, 1288 insertions(+), 1002 deletions(-)
```

Um commit, dois arquivos, ambos relatórios de métricas. O último commit a tocar
`agents/`, `commands/`, `skills/`, `scripts/` ou `helpers/` continua sendo
`a1e3791 2026-08-21 docs(output-format): add readability rule for main-window output` —
**21 dias atrás**.

Consequência metodológica: **todo veredito da Fase 1 registrado contra `a67cac9` permanece válido
contra `9530551`**, porque nenhum alvo de código mudou entre os dois. Este pass não re-verifica os
87 itens já cobertos; ele ataca o resto do conjunto não coberto.

### O output de três passes segue fora do remoto

```
$ git status --short
 M docs/reports/_index.md
?? docs/reports/2026-08-21/
?? docs/reports/2026-08-28/
?? docs/reports/2026-09-04/
$ git show HEAD:docs/reports/_index.md | grep -cE '^- `[a-z]'
176
$ grep -cE '^- `[a-z]' docs/reports/_index.md
237
```

**61 fingerprints existem apenas no disco desta máquina** — as 37 de 2026-08-21, as 21 de
2026-08-28 e as 3 de 2026-09-04. O pass de 2026-09-04 declarou que "esta execução commita e faz
push"; o commit que ele produziu (`9530551`) staged **apenas os dois arquivos de métricas**, e os
três diretórios de relatório continuaram untracked.

Isso não é um achado novo: já está registrado como
`gov-audit-pass-output-uncommitted-with-no-detection-mechanism` (**HIGH**, aberto, 2026-08-28) e
como `flow-prompt-auditoria-commit-step-contradicts-branch-rule` (**MEDIUM**, aberto, 2026-08-14) —
este segundo descreve exatamente o mecanismo do fracasso: o bloco de commit de
`_prompt-auditoria.md:336-358` foi copiado de `docs/prompts/posthog-metrics-report.md`, diz "the two
report files", e carrega a mensagem `docs(reports): metrics reports updates`. O commit `9530551`
tem essa mensagem literal. **Porta 5** do Protocolo Anti-Duplicação: reapresentar um item já
registrado e não implementado é ruído, não descoberta.

O que muda operacionalmente neste pass: o `git add` abaixo enumera os quatro diretórios pendentes
além do deste pass, e a verificação de push confere o SHA remoto.

---

## Método e cobertura

| Item | Valor |
|---|---|
| Linhas `^- \`` no `_index.md` | 237 |
| **Fingerprints vivos reais** | **235** — 2 das 237 são linhas da seção `### Descartados por duplicação` que casam o padrão de contagem (ver Eixo C, achado 4) |
| Conjunto verificável (✅ Executed + ⚠️ Partial) | 121 |
| Já verificados contra `a67cac9` (passes de 2026-08-14 / 08-21 / 08-28 / 09-04) | 87 |
| Não cobertos | 34 — **todos MEDIUM ou abaixo**; os 18 HIGH/MEDIUM-HIGH foram verificados contra o mesmo estado de código |
| Critério de amostragem | conjunto > 60 → HIGH e MEDIUM-HIGH **todos** (18/18, já cobertos) + amostra determinística de 35% dos 34 não cobertos (índices 0, 3, 6, … 33 da lista ordenada por posição no `_index.md`) = **12** |
| **Cobertura da Fase 1 — bloco novo** | **12 de 34 não cobertos (35%)** |
| **Cobertura da Fase 1 — acumulada** | **99 de 121 (82%)** |
| Placar do bloco novo | **9 ✅ · 2 🟡 · 1 🔴** |
| Divergências **novas** deste pass | **2 🟡 (16,7%)** — a única 🔴 do bloco já estava registrada desde 2026-07-31; este pass confirma que persiste |
| Placar acumulado | **83 ✅ · 9 🟡 · 7 🔴** — 84% confirmado, 7,1% reaberto |
| Conjunto aberto (sem marcador) | 113 → alvos da Fase 1b |
| **Mortalidade Fase 1b** | **0 de 113 (0%)** — ver § Fase 1b |

**Escalonamento: não disparado.** A regra escala quando mais de 15% da amostra vem 🔴. Neste bloco
**nenhuma 🔴 nova** apareceu (0%). Se a régua for alargada para "qualquer divergência", o bloco dá
16,7% (2 🟡 de 12) — marginalmente acima de 15%, e por isso registrado aqui em vez de omitido; mas
as duas 🟡 são parcialidades de escopo, não marcações falsas.

**Janela de remediação.** Os 12 itens carregam marca ✅ **2026-07-31**. As oito commits da janela
são `bbb311a`, `b4e219f`, `6919564`, `519ca7e`, `c7535b7`, `cc28900`, `2e12335`, `7736e20`. Cada
veredito abaixo foi ancorado em `git show --stat` dessas commits e confirmado por leitura do alvo no
`HEAD`, nunca pela leitura do relatório-fonte.

---

## Fase 1 — Bloco de 12 itens

| # | Fingerprint | Marca original | Marca verificada | Commit examinado |
|---|---|---|---|---|
| 1 | `ref-haiku-residual-claude-md-note-after-executed-removal` | ✅ 2026-07-31 | ✅ **Feito** | `bbb311a` |
| 2 | `ref-claude-md-hook-files-map-omits-pre-tool-use-02-telemetry-and-stop-05-telemetry-…` | ✅ 2026-07-31 | ✅ **Feito** | `bbb311a` + `7736e20` |
| 3 | `flow-orphan-template-scan-runs-in-stop-but-only-checks-references-not-resolvability-…` | ✅ 2026-07-31 | ✅ **Feito** | `c7535b7` |
| 4 | `flow-no-stop-hook-runs-check-fingerprint-uniqueness-after-_index-edit-…` | ✅ 2026-07-31 | ✅ **Feito** | `cc28900` |
| 5 | `flow-cli-commit-validate-msg-script-skipped-silently-when-missing-no-instructive-error` | ✅ 2026-07-31 (🔴 2026-07-31) | 🔴 **Não feito** (persiste) | `6919564` |
| 6 | `flow-commit-md-and-update-md-are-only-2-commands-without-current-context-load-…` | ✅ 2026-07-31 | ✅ **Feito** | `bbb311a` |
| 7 | `agent-frontend-reviewer-body-type-safety-and-code-quality-hardcodes-react-ts-…` | ✅ 2026-07-31 | ✅ **Feito** | `b4e219f` |
| 8 | `agent-three-reviewers-overlap` | ✅ 2026-07-31 | ✅ **Feito** | `b4e219f` |
| 9 | `token-review-shared-skills-reloaded-by-router-then-each-specialist-…` | ✅ 2026-07-31 | 🟡 **Parcialmente feito** | `6919564` + `b4e219f` |
| 10 | `token-comments-policy-load-directive-duplicated-in-8-agents-…` | ✅ 2026-07-31 | ✅ **Feito** | `b4e219f` |
| 11 | `token-sixteen-skill-descriptions-exceed-95-char-budget-…` | ✅ 2026-07-31 | ✅ **Feito** | `7736e20` + `c7535b7` |
| 12 | `token-git-log-window-overshoot` | ✅ 2026-07-31 | 🟡 **Parcialmente feito** | `b4e219f` |

### Item a item

**1 — `ref-haiku-residual-claude-md-note-after-executed-removal` → ✅ Feito**
`bbb311a` reescreveu 104 linhas de `CLAUDE.md`. No `HEAD`, `CLAUDE.md:64` enuncia a frontmatter
corrente (`name`, `description`, `tier`, `model`) e `:67` declara explicitamente
`- **No \`tools:\` key**, and therefore no tools-order rule.` O resíduo apontado pelo achado não
existe mais. Sem reversão: `git log --oneline --since=2026-07-31 -- CLAUDE.md` não mostra restauro.

**2 — `ref-claude-md-hook-files-map-omits-…-telemetry-sub-scripts` → ✅ Feito**
O mapa migrou para `CLAUDE-md/hooks.md`. `:31` lista `| \`05-\` | External reporting (telemetry) |
\`05-telemetry.sh\` |` e `:55` lista `02b-telemetry.sh — queues telemetry events for agent spawns
and devteam commands`. Ambos os sub-scripts que o achado dizia ausentes estão documentados.

**3 — `flow-orphan-template-scan-…-only-checks-references-not-resolvability` → ✅ Feito**
`c7535b7` reescreveu `helpers/orphan-template-scan.sh` (+146 linhas). O cabeçalho no `HEAD` abre com
`:3` — `# references that do not actually resolve at runtime.` e o corpo faz resolução real:
`:53` `[ -f "$template_file" ] || continue`, `:91` `unresolved_refs=$((unresolved_refs + 1))`,
`:130` `echo " ACTION REQUIRED — Template references that do not resolve at runtime:"`.
`bash helpers/orphan-template-scan.sh` sai `orphan-template-scan: clean ✓`.

**4 — `flow-no-stop-hook-runs-check-fingerprint-uniqueness-…` → ✅ Feito**
`cc28900` criou `scripts/hooks/stop/03b-fingerprint-uniqueness.sh` (+48 linhas). O cabeçalho declara
o propósito exato do achado: `:8` — `# It gives the same-session feedback that the CI gate
(.github/scripts/ci/01-lint.sh) can only give after a push.` O nome casa o `SUBSCRIPT_RE` do
dispatcher (`stop.sh:57`), logo é efetivamente despachado.

**5 — `flow-cli-commit-validate-msg-script-skipped-silently-…` → 🔴 Não feito (persiste)**
Já reaberto em 2026-07-31; esta verificação confirma contra `9530551`. `commands/commit.md:144-147`:

```bash
if [ -f ".dev-team-agents/scripts/validate-commit-msg.sh" ]; then
    echo "$COMMIT_MSG" | bash .dev-team-agents/scripts/validate-commit-msg.sh
fi
```

Não há ramo `else`. O script ausente continua sendo um silêncio, não um erro instrutivo. A única
mudança que `6919564` fez no arquivo foi a adoção de `AskUserQuestion` no tratamento de falha
(`:150-153`) — que só roda quando um gate **retorna** não-zero, e um gate ausente não retorna nada.

**6 — `flow-commit-md-and-update-md-…-without-current-context-load` → ✅ Feito**
A descrição registrada no `_index.md` para este slug fala de `/devteam:health-check` ausente das
listas canônicas — divergência de pareamento herdada do banco, não deste pass. Ambas as leituras
verificam ✅: `grep -c "devteam:health-check"` devolve 4 em `CLAUDE.md`, 3 em `README.md` e 3 em
`README.pt-BR.md`; e `CLAUDE.md:246` agora enumera explicitamente a lista fechada de seis comandos
que não carregam `current-context`, com `/devteam:commit` e `/devteam:update` nomeados e
justificados ("operates on the staging area, not a branch scope" / "operates on the local
installation").

**7 — `agent-frontend-reviewer-…-hardcodes-react-ts-identifiers-proptypes-react-changeevent-hocs` → ✅ Feito**
`b4e219f` reescreveu 50 linhas de `agents/frontend-reviewer.md`. A seção alvo hoje
(`### 10. Type Safety`, `:109-115`) abre agnóstica e demote os identificadores a exemplos:

> `Apply whatever type discipline the project has adopted — a type system, a runtime prop/schema
> validator, or documented contracts:`
> `- Component inputs with no declared contract — e.g. missing TypeScript interfaces, PropTypes, or
> Vue \`defineProps\` types`

`### 11. Code Quality & Conventions` (`:117`) igualmente: `wrappers wrapping wrappers (HOC chains)`
com HOC como exemplo parentético, não como critério. É exatamente a reescrita que o achado pedia.

**8 — `agent-three-reviewers-overlap` → ✅ Feito**
`b4e219f` tocou os três alvos (`code-reviewer.md` −166, `backend-reviewer.md` −45,
`frontend-reviewer.md` −50). O bloco duplicado virou **uma linha** de delegação idêntica em cada
(`code-reviewer.md:43`, `backend-reviewer.md:25`, `frontend-reviewer.md:25`):
`Load \`skills/shared/project-context/SKILL.md\` — covers README, CLAUDE.md, AGENTS.md, project.md,
session-summary, development docs, and recent git log.` Isso é precisamente o que `CLAUDE.md` § Canonical
Rule Homes prescreve ("Delegate in one line"), não uma duplicação residual.

**9 — `token-review-shared-skills-reloaded-by-router-then-each-specialist-…` → 🟡 Parcialmente feito**
**O que foi entregue:** `6919564` encolheu `commands/review.md` (hoje 68 linhas) e `b4e219f` reduziu
`skills/shared/project-context/SKILL.md` de 321 para **269** linhas (−16%), baixando o multiplicador.
**O que falta — exatamente:** o problema enunciado era *"No mechanism passes a factual summary
between spawns"*, e esse mecanismo continua inexistente. `commands/review.md:41-52` ainda dispara
4 spawns incondicionais (`code-reviewer`, `software-architect`, `security-specialist`,
`qa-specialist`) + 2 condicionais (`database-specialist`, `mobile-developer`), e `code-reviewer`
roteia internamente para mais 2 — **8 execuções isoladas**, cada uma re-executando sua Foundational
Rule sobre `project-context` (269), `token-efficiency` (160), `interaction-patterns` (209),
`comments-policy` e `reviewer-base`. A única redução foi no tamanho do que é recarregado, não na
contagem de recargas.

**10 — `token-comments-policy-load-directive-duplicated-in-8-agents-…` → ✅ Feito**
A diretiva hoje aparece em 15 agentes, mas **não é mais duplicação verbatim**: das 16 ocorrências,
15 são textos distintos, papel a papel (`— governs every comment you write in production code` no
backend-developer; `— applies when reviewing comments in the diff` no frontend-reviewer; linhas de
tabela de roteamento condicional no software-architect e no security-specialist). Apenas uma
formulação se repete duas vezes, nos dois test-specialists, onde a regra AAA é genuinamente comum.
O achado pedia o fim da cópia idêntica de um bloco; o que existe hoje é a linha de delegação que o
`CLAUDE.md` exige, particularizada por papel.

**11 — `token-sixteen-skill-descriptions-exceed-95-char-budget-…-no-lint-gate` → ✅ Feito**
Duas metades, ambas entregues. Medição no `HEAD`: **0 de 152** skills excedem 95 caracteres de
`description`. E o gate existe: `helpers/agent-lint.sh:92` `SKILL_DESC_LIMIT=95`, `:98`
`SKILL_DESC_STRICT=true`, `:318` empurra a violação para `ERRORS+=(…)`. `7736e20` reescreveu 20
descrições; `c7535b7` adicionou o gate.
*(Nota: `CLAUDE.md:129` ainda descreve esse gate como `SKILL_DESC_STRICT=false` / não-bloqueante —
divergência já registrada como `docs-sync-claude-md-102-states-skill-desc-strict-false-…`, **HIGH**,
aberta. Porta 5: não vira achado novo.)*

**12 — `token-git-log-window-overshoot` → 🟡 Parcialmente feito**
O achado nomeava **cinco** alvos: `agents/security-specialist.md:36`, `ui-ux-designer.md:23`,
`qa-specialist.md:24`, `technical-writer.md:23` e `skills/shared/setup-scan/SKILL.md:16`.
`b4e219f` tocou os quatro agentes e todos convergiram para a janela documentada.
**O que falta — exatamente:** o quinto alvo. `skills/shared/setup-scan/SKILL.md:16` ainda tem
`git log --oneline -20`, e nenhuma commit da janela de 2026-07-31 tocou esse arquivo
(`git log -- skills/shared/setup-scan/SKILL.md` devolve `e4c96b4` 2026-08-11, `f67d202` 2026-07-31
— este último é o rename de descrição do harness, não a janela de remediação, e não alterou a
linha). É hoje a **única** ocorrência de `-20` no repositório contra o `-10` canônico de
`CLAUDE.md` § Commit Rule.

---

## Fase 1b — Validade dos achados abertos

**Conjunto aberto:** 113 fingerprints sem marcador.

**Mortalidade: 0 de 113 (0%).**

A justificativa é estrutural, não amostral. O delta `a67cac9..HEAD` contém **um** commit que tocou
**dois** arquivos, ambos em `docs/reports/`. Nenhum achado aberto tem alvo nesses dois arquivos —
são relatórios de métricas PostHog gerados por `docs/prompts/posthog-metrics-report.md`, fora da
superfície de agentes, comandos, skills, scripts e docs canônicos onde os 113 achados vivem.
Por construção: **nenhum alvo aberto pôde ser corrigido de passagem nem ficar obsoleto**, porque
nada que os contém mudou.

Como teste da premissa — e não como amostra estatística — seis achados abertos foram relocalizados
no `HEAD` e todos reproduzem:

| Fingerprint | Reprodução no `HEAD` |
|---|---|
| `docs-sync-claude-md-102-states-skill-desc-strict-false-…` | `CLAUDE.md:129` diz `SKILL_DESC_STRICT=false`; `helpers/agent-lint.sh:98` diz `true` |
| `agent-line-cap-205-documented-in-claude-md-vs-211-enforced-by-size-limits` | `CLAUDE.md:92` e `:313` dizem 205; `helpers/size-limits.sh:44` tem `AGENT_LIMIT=211` |
| `auto-size-limits-claude-md-warning-counted-as-violation-turns-ci-lint-red` | `bash helpers/size-limits.sh` imprime `⚠ CLAUDE.md: 602 lines` sob o cabeçalho `ERRORS` |
| `agent-three-at-exactly-211-line-ceiling-zero-headroom-for-additions` | `software-architect.md`, `qa-specialist.md` e `frontend-developer.md` em exatamente 211 |
| `docs-sync-claude-md-coding-agents-list-omits-seo-specialist` | `CLAUDE.md:109` lista oito; `grep -l "## Worktree Isolation" agents/*.md` devolve nove |
| `ref-readme-sync-gate-discovers-only-pt-br-suffix-blind-to-inverted-en-suffix-pair` | `02-readme-sync.sh:192` descobre por `-name '*.pt-BR.md'`; o par `metrics-last-20-days.md`/`.en.md` escapa |

**Taxa de mortalidade do pass: 0%.** Como nos dois passes anteriores, isso reflete a imobilidade da
árvore, não a durabilidade do banco — e o indicador só volta a ter valor diagnóstico quando houver
um delta de código real para medir contra.

---

## Correções de marcação aplicadas ao `_index.md`

| Fingerprint | Ação |
|---|---|
| `token-review-shared-skills-reloaded-by-router-then-each-specialist-…` | `— 🟡 **Parcial na verificação de 2026-09-11:** …` |
| `token-git-log-window-overshoot` | `— 🟡 **Parcial na verificação de 2026-09-11:** …` |
| `flow-cli-commit-validate-msg-script-skipped-silently-…` | `— 🔴 **Reaberto na verificação de 2026-09-11:** …` (segunda confirmação) |

Nenhuma marcação da Fase 1b foi alterada: nenhum achado aberto foi resolvido ou ficou obsoleto.
