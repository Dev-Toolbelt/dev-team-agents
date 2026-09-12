# Fases 1 e 1b — Verificação guardiã (2026-09-04)

**Data:** 2026-09-04 · **Baseline:** `HEAD` = `a67cac9` · **Baseline anterior:** `a67cac9`

---

## O fato que estrutura este pass: terceiro baseline idêntico consecutivo

`git rev-parse --short HEAD` devolve `a67cac9`. É o **mesmo sha** que os passes de 2026-08-21 e
2026-08-28 registraram como seus próprios baselines. O último commit do repositório é
`a67cac9 2026-08-21 docs(changelog): add v2.47.2 entry` — **catorze dias atrás**.

```
$ git log --format='%h %ad %s' --date=short -1
a67cac9 2026-08-21 docs(changelog): add v2.47.2 entry
$ git diff --stat a67cac9..HEAD
(vazio)
```

O delta de código é **zero arquivo em zero commit**, pela terceira vez seguida.

E o output dos **dois** passes anteriores continua não commitado:

```
$ git status --short
 M docs/reports/_index.md
?? docs/reports/2026-08-21/
?? docs/reports/2026-08-28/
$ git show HEAD:docs/reports/_index.md | grep -cE '^- `[a-z]'
176
$ grep -cE '^- `[a-z]' docs/reports/_index.md
234
```

**58 fingerprints existem apenas no disco desta máquina** — as 37 do pass de 2026-08-21 e as 21 do
pass de 2026-08-28. O pass de 2026-08-28 já registrou isso como
`gov-audit-pass-output-uncommitted-with-no-detection-mechanism` (**HIGH**, aberto). A recorrência
confirma o achado sem gerar um novo: pela **Porta 5** do Protocolo Anti-Duplicação, reapresentar um
item já registrado e não implementado é ruído.

O que muda neste pass é operacional, não epistêmico: **esta execução commita e faz push**, o que
fecha a lacuna para as 58 fingerprints pendentes. O mecanismo de detecção que o achado pede — algo
que verifique que `docs/reports/` chegou ao remoto — continua inexistente, e o achado continua
aberto.

---

## Método e cobertura

| Item | Valor |
|---|---|
| Fingerprints vivos no banco (árvore de trabalho) | 234 |
| Conjunto verificável (✅ Executed + ⚠️ Partial) | 121 |
| Já verificados contra `a67cac9` (passes de 2026-08-21 e 2026-08-28) | 70 |
| Não cobertos contra este `HEAD` | 51 — **todos MEDIUM ou abaixo**; os 18 HIGH/MEDIUM-HIGH já foram verificados contra este mesmo sha |
| Critério de amostragem | conjunto > 60 → HIGH e MEDIUM-HIGH **todos** (18/18, cobertos) + **30% dos 51 restantes**, amostra determinística (índices 0, 3, 6, … da lista ordenada) = 16, **+1 item extra** encontrado como divergente durante o Eixo E |
| **Cobertura da Fase 1 — bloco novo** | **17 de 51 não cobertos (33%)** |
| **Cobertura da Fase 1 — acumulada contra `a67cac9`** | **87 de 121 (72%)** |
| Placar do bloco novo | **13 ✅ · 2 🟡 · 2 🔴** — 76% confirmado, **11,8% divergente** |
| Placar acumulado contra `a67cac9` | **74 ✅ · 7 🟡 · 6 🔴** — 85% confirmado, **6,9% reaberto** |
| Conjunto aberto (sem marcador) | 110 → alvos da Fase 1b |
| **Mortalidade Fase 1b** | **0 de 110 (0%)** — ver justificativa abaixo |

A taxa de divergência do bloco novo (11,8%) está **abaixo do limiar de escalonamento de 15%**, e a
acumulada (6,9%) mais ainda. A integridade do banco não é o achado principal deste pass.

**Ressalva sobre as duas 🟡.** Os itens 6 e 15 do bloco já carregavam uma marca 🟡 registrada na
verificação de **2026-08-14**, contra um baseline diferente (`3fbe371`). Não são reaberturas novas:
esta verificação **confirma que a parcialidade persiste em `a67cac9`**. As divergências
genuinamente novas deste pass são as **duas 🔴**.

Todos os 17 itens foram marcados na janela de **2026-07-31**, cujas oito commits de remediação são
`bbb311a`, `b4e219f`, `6919564`, `519ca7e`, `c7535b7`, `cc28900`, `2e12335` e `7736e20`. Cada
veredito foi ancorado em `git show` dessa janela, nunca na leitura do relatório-fonte.

---

## Fase 1 — Bloco de 17 itens

| # | Fingerprint | Marca original | Marca verificada | Commit examinado |
|---|---|---|---|---|
| 1 | `auto-agent-lint-quiz-first-regex-only-matches-yes-no-…` | ✅ 2026-07-31 | ✅ Feito | `c7535b7` |
| 2 | `flow-telemetry-stop-05-runs-after-04-notifier-but-no-fast-path-…` | ✅ 2026-07-31 | ✅ Feito | `6919564` |
| 3 | `ref-orphan-template-scan-consumers-list-omits-helpers-dir-…` | ✅ 2026-07-31 | ✅ Feito | `6919564` + `c7535b7` |
| 4 | `flow-session-summary-closure-step-present-in-eight-of-ten-…` | ✅ 2026-07-31 | ✅ Feito | `6919564` |
| 5 | `flow-setup-slash-command` | ✅ 2026-07-31 | ✅ Feito | `519ca7e` |
| 6 | `agent-frontend-developer-body-92-102-data-fetching-…` | ✅ 2026-07-31 (🟡 2026-08-14) | **🟡 Parcial** | `b4e219f` + `519ca7e` |
| 7 | `agent-setup-assistant-three-roles-bundled-extractable-…` | ✅ 2026-07-31 | ✅ Feito | `b4e219f` |
| 8 | `agent-product-analyst-other-trackers-still-asana-clickup-…` | ✅ 2026-07-31 | ✅ Feito | `b4e219f` |
| 9 | `skill-integrations-gotrue-225-lines-largest-integration-skill-…` | ✅ 2026-07-31 | ✅ Feito | `519ca7e` |
| 10 | `agent-frontend-developer-and-backend-developer-still-loaded-token-efficiency-…` | ✅ 2026-07-31 | ✅ Feito | `b4e219f` |
| 11 | `agent-frontend-developer-loads-jquery-skill-orphan-of-modern-stacks` | ✅ 2026-07-31 | ✅ Feito | `cc28900` |
| 12 | `token-conventional-commits-138-lines-eager-loaded-by-code-reviewer-…` | ✅ 2026-07-31 | ✅ Feito | `b4e219f` |
| 13 | `token-backlog-template-skill-171-lines-unconditionally-loaded-…` | ✅ 2026-07-31 | ✅ Feito | `b4e219f` |
| 14 | `token-conventional-commits-skill-138-lines-loaded-by-commit-and-pr-commands-…` | ✅ 2026-07-31 | **🔴 Não feito** | `6919564` (só a tabela restatada) |
| 15 | `token-sonarqube-detection-block-redundant` | ✅ 2026-07-31 (🟡 2026-08-14) | **🟡 Parcial** | `b4e219f` |
| 16 | `token-rollback-sh-65-lines-duplicates-installer-download-from-update-sh` | ✅ 2026-07-31 | ✅ Feito | `2e12335` |
| 17 | `token-dedup-step-reads-full-676-line-prose-index-md-every-run-…` | ✅ 2026-07-31 | **🔴 Não feito** | **nenhum** |

**Apuração:** 13 ✅ · 2 🟡 · 2 🔴

---

## Detalhes — os quatro vereditos divergentes

### 14. `token-conventional-commits-skill-138-lines-loaded-by-commit-and-pr-commands-but-also-mentioned-as-skill-load-in-claude-md-skill-loads-by-table-format-not-prose` — 🔴

**O que o banco afirma:** "`commands/commit.md` loads `conventional-commits` 'before doing
anything', then may discard it."

**O que o git mostra.** O único commit da janela que tocou `commands/commit.md` é `6919564`. Seu
diff completo no arquivo tem três hunks, e **nenhum deles toca a diretiva de carga**:

```
$ git show 6919564 -- commands/commit.md | grep -E '^[+-][^+-]'
-Load `skills/shared/interaction-patterns/SKILL.md` before asking the user any question…
+Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question…
-1. Read `commands/learn.md` and follow Steps 1–4 exactly…
+1. Run the `/devteam:learn` flow, Steps 1–4 exactly…
-Analyze the staged files and group them by layer or context using the Layered Commits rules…
-| Order | Layer | Examples |
  … (a tabela restatada, removida)
+Analyze the staged files and group them by layer or context using the **Layered Commits** ordering table…
```

A remediação real de `6919564` foi **outro achado** — a tabela de camadas duplicada. O achado deste
fingerprint é a carga incondicional, e ela sobrevive intacta no `HEAD`:

- `commands/commit.md:7` — "Load the skill at `skills/shared/conventional-commits/SKILL.md` **before doing anything**."
- `skills/shared/conventional-commits/SKILL.md` tem **169 linhas** hoje (eram 138 na abertura do achado — cresceu 22%).
- `CLAUDE.md:` § Commit Rule, item 2: "**Defer to the project's own pattern first**: run `git log --oneline -10` … If a project-specific pattern is clearly in use, **follow it instead**."

Ou seja: o comando carrega 169 linhas antes de qualquer coisa, e a regra canônica manda descartá-las
quando o projeto usa outro padrão. É exatamente a condição descrita no achado.

**Por que a marcação está errada:** a marca ✅ foi atribuída porque `6919564` tocou o arquivo-alvo.
Tocou — para resolver um achado diferente. O enunciado deste nunca foi endereçado.

### 17. `token-dedup-step-reads-full-676-line-prose-index-md-every-run-when-only-fingerprint-slug-list-is-needed-extract-machine-readable-list` — 🔴

Este item **não estava na amostra determinística**; foi encontrado durante o Eixo E e verificado por
completude.

**O que o banco afirma:** "The anti-duplication step reads the full 850-line prose index to recover
a flat slug list." Remediação pedida no slug: `extract-machine-readable-list`.

**O que o git mostra.** Dos oito commits da janela, **apenas `7736e20` tocou `docs/reports/`**, e
apenas o próprio `_index.md`:

```
$ for sha in bbb311a b4e219f 6919564 519ca7e c7535b7 cc28900 2e12335 7736e20; do
    git show --stat --format='' $sha | grep 'docs/reports'; done
 docs/reports/_index.md | 280 +++++++++++----------
```

E esse diff é marcação de status e prosa — `+| 2026-07-31 | — (execution pass…`,
`+**All 11 HIGH are ✅ Executed.**`, `+### The 10 that remain open` — **não** a extração de uma
lista. Nenhum artefato legível por máquina foi criado:

```
$ ls docs/reports/*.txt docs/reports/*.json 2>/dev/null
(nada)
```

**Confirmação no `HEAD`.** O Protocolo Anti-Duplicação do próprio `_prompt-auditoria.md` continua
fazendo `grep -F "<slug>" docs/reports/_index.md` (Porta 1, `:195`) e
`grep -i "<basename>" docs/reports/_index.md` (Porta 2, `:201`) contra o arquivo em prosa, que hoje
tem **548 linhas / 109.001 bytes**.

**Nuance registrada em favor da marca.** `7736e20` introduziu o campo `alvo:` no formato de linha, e
é ele que torna a Porta 2 barata. Isso reduz o custo do problema, mas não é a remediação descrita, e
a Porta 2 ainda varre o arquivo inteiro. Marca correta: **🔴**, com a redução de custo anotada.

### 6. `agent-frontend-developer-body-92-102-data-fetching-…` — 🟡 (segunda confirmação)

A tabela de detecção em `agents/frontend-developer.md:84-85` é **exceção legítima** — detecção de
stack é por design específica. O sub-escopo pendente está fora dela, sob o heading
`## Server State & Data Fetching`:

- `:91` — "Never mirror fetched data into a second, component-local store (e.g. **React `useState`**)"
- `:96` — "recommend adopting the server-state library idiomatic to the project's stack (**TanStack Query and SWR** are the common choices in the **React/Vue** ecosystem)"

Ambas as linhas são regra de comportamento, não detecção. A parcialidade registrada em 2026-08-14
persiste sem alteração em `a67cac9`.

### 15. `token-sonarqube-detection-block-redundant` — 🟡 (segunda confirmação)

Dez das onze cópias foram removidas por `b4e219f` — `agents/backend-developer.md:86`,
`backend-reviewer.md:146`, `backend-test-specialist.md:106` e `code-reviewer.md:103` agora todas
delegam ("handled by `project-context`", "defers to the skill's own `## Detection Signals` table").

A décima primeira sobrevive. `agents/devops-specialist.md:81`:

```
| `sonar-project.properties`, `.sonarcloud.properties`, `sonarqube` service in compose, or `SONAR_TOKEN` env var | `skills/devops/sonarqube/SKILL.md` |
```

São **4 dos 6 sinais** da tabela canônica em `skills/devops/sonarqube/SKILL.md:12-19`. Faltam
`sonar-scanner` / `mvn sonar:sonar` / `./gradlew sonar` em arquivos de CI e `sonarqube-scanner` em
`package.json`/`pom.xml`/`build.gradle`. Um projeto que só tem o scanner no pipeline não dispara a
carga por esta linha, mas dispararia pela tabela canônica. É precisamente a deriva que a regra
"Delegate, Never Restate" existe para impedir.

---

## Detalhes — quatro ✅ representativos

### 1. `auto-agent-lint-quiz-first-regex-only-matches-yes-no-variants-misses-a-b-c-multiple-choice`

`c7535b7` reescreveu o bloco de regex. `helpers/agent-lint.sh:101-104` agora define **dois**
padrões, e `:236-237` aplica os dois:

```
101: # answer set — yes/no *and* 2–4 option multiple choice.
102: #   Pattern 1 — yes/no parentheticals, matched anywhere on the line.
103: QUIZ_YESNO_RE='\([yY]es[/ ][nN]o\)|\(y[/]n\)|\(yes\|no\)|\( yes / no \)'
104: #   Pattern 2 — multiple-choice prompts: a question mark immediately followed by
236:   check_quiz_first "$file" "$QUIZ_YESNO_RE" "plain-text yes/no prompt found"
237:   check_quiz_first "$file" "$QUIZ_MC_RE"    "plain-text multiple-choice prompt found"
```

`bash helpers/agent-lint.sh` sai limpo no `HEAD` (`agent-lint: clean ✓`).

### 7. `agent-setup-assistant-three-roles-bundled-extractable-health-checker-update-manager`

`b4e219f` cortou 106 linhas do agente. O `HEAD` não descreve mais os procedimentos secundários —
`agents/setup-assistant.md:169-172` delega explicitamente:

> "Both roles have their own command and their own canonical procedure. **Do not restate either
> procedure here; load it and follow it.**"

A tabela abaixo aponta para `skills/shared/setup-health-check/SKILL.md`, o fluxo `/devteam:update` e
`skills/shared/migration-v1-to-v2/SKILL.md`. O agente ficou em 208 linhas com três papéis
**referenciados**, não bundled.

### 9. `skill-integrations-gotrue-225-lines-largest-integration-skill-…-no-references-extraction`

`519ca7e` extraiu o material de referência. `skills/integrations/gotrue/SKILL.md` foi de **225 para
73 linhas**, com `references/claims-and-hooks.md` e `references/client-and-admin-api.md` ao lado.

### 16. `token-rollback-sh-65-lines-duplicates-installer-download-from-update-sh`

`2e12335` criou `scripts/lib/installer-fetch.sh` (256 linhas) e apontou os dois consumidores para
ele. `scripts/rollback.sh:20-31` e `scripts/update.sh:42-44` carregam a mesma biblioteca, cada um
com o comentário nomeando o outro consumidor. `rollback.sh` está em 99 linhas com a lógica de
download compartilhada.

---

## Fase 1b — Validade dos achados abertos

### Método e cobertura

| Item | Valor |
|---|---|
| Conjunto aberto (fingerprints sem marcador) | **110** |
| Verificados por inspeção direta no `HEAD` | **8** (amostra determinística, índices 0, 14, 28, … da lista ordenada) |
| Mortalidade observada | **0 de 8** |
| **Mortalidade declarada do pass** | **0 de 110 (0%)** |

**Por que a extrapolação para 110 é legítima aqui, e só aqui.** A mortalidade da Fase 1b mede
quantos achados abertos foram resolvidos ou tornados obsoletos **por mudanças na árvore**. A árvore
não mudou: `git diff --stat a67cac9..HEAD` é vazio, e `a67cac9` é o mesmo sha contra o qual o pass
de 2026-08-28 mediu 0% de mortalidade sobre 50 itens. Nenhum byte mudou desde então, logo nenhuma
mudança pode ter resolvido nada. A amostra de 8 serve como **verificação da premissa**, não como
estimativa estatística.

Esse 0% é, portanto, um indicador da **imobilidade do repositório**, não da durabilidade do banco —
exatamente a ressalva que o pass de 2026-08-28 registrou. Repetir a leitura sem repetir a ressalva
seria transformar um artefato de medição em um atestado de saúde.

### Resultado da amostra — 8 de 8 reproduzem

| # | Fingerprint | Evidência no `HEAD` | Veredito |
|---|---|---|---|
| 1 | `flow-session-start-118-lines-monolithic-…` | `scripts/hooks/session-start.sh` = **310 linhas** (118 na abertura, 174 em 2026-07-31) | reproduz |
| 2 | `docs-sync-claude-md-…-all-devteam-commands-load-current-context-…-four-exceptions` | `CLAUDE.md:203` "All `/devteam:*` commands"; `:252` lista **seis** como "the complete list" mais cinco em prosa | reproduz |
| 3 | `flow-mobile-command-spawn-line-enumerates-stacks-dropped-from-agent-description` | `commands/mobile.md:19` — "implement the mobile changes (React Native, Expo, Flutter, native iOS/Android)" | reproduz |
| 4 | `flow-background-process-discipline-monitor-no-availability-fallback` | `skills/architecture/orchestration/SKILL.md:262` declara `Monitor` a única forma legítima; a cláusula de indisponibilidade só existe para `ScheduleWakeup` (`:241`) | reproduz |
| 5 | `auto-size-limits-claude-md-warning-counted-as-violation-turns-ci-lint-red` | `helpers/size-limits.sh:91` empurra o warning no array `VIOLATIONS`; `bash helpers/size-limits.sh` imprime "**ERRORS** — Files exceeding declared limits: ⚠ CLAUDE.md: 602 lines (warning threshold: 600)" e sai 1 | reproduz |
| 6 | `flow-pr-md-default-branch-falls-back-to-global-config-then-literal-main` | `commands/pr.md:60-63` — `git config init.defaultBranch` antes de `git remote show origin`, terminando em `\|\| echo "main"` | reproduz |
| 7 | `token-two-schedulewakeup-poll-loops-same-spawn-round-300s-vs-1200-1800s` | `skills/architecture/orchestration/SKILL.md:223` agenda 1200–1800 s + `TaskList` (`:228`); `skills/shared/work-feedback/SKILL.md:43,49` agenda o intervalo configurado (default 5 min) na mesma rodada | reproduz |
| 8 | `ref-command-description-duplicated-frontmatter-vs-commands-json` | `scripts/lib/commands.json` carrega **35** campos `description`, um por comando, espelhando o frontmatter | reproduz |

Nenhum 🟢 Resolved e nenhum ⚰️ Obsoleto a aplicar.

### Deriva observada — o achado reproduz, mas o número do banco envelheceu

`flow-session-start-118-lines-monolithic-no-modular-pattern-asymmetric-with-stop-dispatcher` está
registrado com **118 linhas** e anotado em 2026-07-31 com **174**. O arquivo tem **310** hoje — 2,6×
o número no slug. O achado não só reproduz: piorou em uma ordem de grandeza que o próprio texto do
banco não comunica mais. Não é uma reabertura (o item nunca foi marcado executado), e o slug não é
reescrito — apenas se registra a deriva para que o próximo pass não leia "118" como o estado atual.

---

## Correções de marcação a aplicar no `_index.md`

| Fingerprint | Anexar |
|---|---|
| `token-conventional-commits-skill-138-lines-loaded-by-commit-and-pr-commands-…` | `— 🔴 **Reaberto na verificação de 2026-09-04:** nenhum commit da janela tocou a diretiva de carga; `commit.md:7` ainda carrega o skill (hoje 169 linhas) "before doing anything", que a Commit Rule do `CLAUDE.md` manda descartar quando o projeto usa outro padrão` |
| `token-dedup-step-reads-full-676-line-prose-index-md-every-run-…` | `— 🔴 **Reaberto na verificação de 2026-09-04:** nenhuma lista legível por máquina existe; as Portas 1 e 2 seguem varrendo `_index.md` em prosa (548 linhas / 109 KB). O campo `alvo:` de `7736e20` barateia a Porta 2 mas não é a extração pedida` |
| `agent-frontend-developer-body-92-102-data-fetching-…` | `— 🟡 **Parcial na verificação de 2026-09-04:** segunda confirmação — `:91` (`React useState`) e `:96` (TanStack Query/SWR, ecossistema React/Vue) seguem sob `## Server State & Data Fetching`, fora da tabela de detecção` |
| `token-sonarqube-detection-block-redundant` | `— 🟡 **Parcial na verificação de 2026-09-04:** segunda confirmação — `devops-specialist.md:81` ainda restata 4 dos 6 sinais; faltam `sonar-scanner`/`mvn sonar:sonar` em CI e `sonarqube-scanner` em manifestos` |
| `flow-session-start-118-lines-monolithic-…` | `— 📈 **Deriva registrada em 2026-09-04:** `session-start.sh` está em **310 linhas** (118 no slug, 174 em 2026-07-31); o achado segue aberto e o número do slug está obsoleto` |
