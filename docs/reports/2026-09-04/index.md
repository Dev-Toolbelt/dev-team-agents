# Auditoria Guardiã — 2026-09-04

**Data:** 2026-09-04 · **Baseline:** `HEAD` = `a67cac9` · **Baseline anterior:** `a67cac9`

## Sumário executivo

**Terceiro pass consecutivo contra o mesmo baseline.** `HEAD` é `a67cac9`, o mesmo sha que os passes
de 2026-08-21 e 2026-08-28 registraram como seus próprios baselines. O último commit do repositório é
de 21 de agosto, **catorze dias atrás**. `git diff --stat a67cac9..HEAD` é vazio: zero arquivo, zero
commit.

E o output dos **dois** passes anteriores continua fora do remoto. `git status --short` devolve
` M docs/reports/_index.md`, `?? docs/reports/2026-08-21/` e `?? docs/reports/2026-08-28/`;
`git show HEAD:docs/reports/_index.md` tem **176** fingerprints contra **234** na árvore de trabalho.
São **58 fingerprints existindo apenas no disco desta máquina**.

Isso já está registrado como `gov-audit-pass-output-uncommitted-with-no-detection-mechanism`
(**HIGH**, aberto, publicado em 2026-08-28) e por isso **não** vira achado novo — a Porta 5 do
Protocolo Anti-Duplicação existe exatamente para impedir que a repetição de um sintoma conhecido
seja contada como descoberta. O que muda é operacional: **esta execução commita e faz push**, o que
tira as 58 fingerprints pendentes do limbo. O mecanismo de detecção que o achado pede continua
inexistente, e o achado continua aberto.

**Consequência metodológica.** Um pass novo sobre uma árvore que não mudou tem exatamente duas fontes
legítimas de valor: ampliar a cobertura da verificação (Fase 1) e encontrar o que os passes
anteriores não olharam. Foi o que este pass fez — a cobertura acumulada subiu de 58% para **72%**, e
os três achados originais vêm de superfícies que nenhum pass anterior tinha examinado. Os cinco eixos
rodaram integralmente; três deles fecharam com zero achados originais, o que é resultado válido pela
regra 2 e é reportado como tal em vez de preenchido com volume.

---

## Método

| Item | Valor |
|---|---|
| Fingerprints vivos no banco | 234 |
| Conjunto verificável (✅ Executed + ⚠️ Partial) | 121 |
| Conjunto aberto (sem marcador) | 110 |
| Já verificados contra `a67cac9` pelos passes anteriores | 70 |
| Delta de código desde o baseline anterior | **0 arquivos, 0 commits** |

**Amostragem da Fase 1.** Conjunto verificável > 60 → todos os HIGH e MEDIUM-HIGH (18/18, já
cobertos contra este mesmo sha) + 30% dos 51 não cobertos, amostra determinística por índice = 16.
Um 17º item foi verificado por completude ao ser encontrado divergente durante o Eixo E.

**Amostragem da Fase 1b.** 8 itens verificados por inspeção direta, como **teste da premissa** de que
uma árvore imóvel não pode ter matado nenhum achado — não como estimativa estatística. A premissa se
confirmou em 8 de 8.

---

## Cobertura e placar da Fase 1

| Métrica | Bloco novo | Acumulado contra `a67cac9` |
|---|---|---|
| **Cobertura** | **17 de 51 não cobertos (33%)** | **87 de 121 (72%)** |
| ✅ Feito | 13 | 74 |
| 🟡 Parcialmente feito | 2 | 7 |
| 🔴 Não feito | 2 | 6 |
| Confirmado | **76%** | **85%** |
| Reaberto | **11,8%** | **6,9%** |

Abaixo do limiar de escalonamento de 15% nas duas leituras. A integridade do banco não é o achado
principal deste pass.

**Ressalva sobre as duas 🟡:** ambas já carregavam marca 🟡 de 2026-08-14, contra um baseline
diferente. Não são reaberturas novas — esta verificação confirma que a parcialidade persiste em
`a67cac9`. As divergências genuinamente novas são as **duas 🔴**.

### As duas reaberturas

| Fingerprint | Por que a marca ✅ está errada |
|---|---|
| `token-conventional-commits-skill-…-loaded-by-commit-and-pr-commands-…` | O único commit da janela que tocou `commands/commit.md` (`6919564`) resolveu **outro** achado — a tabela de camadas restatada. A diretiva `:7` "Load … **before doing anything**" nunca foi tocada, e o skill cresceu de 138 para 169 linhas |
| `token-dedup-step-reads-full-676-line-prose-index-md-every-run-…-extract-machine-readable-list` | Nenhuma lista legível por máquina existe (`ls docs/reports/*.txt *.json` → nada). O único commit da janela que tocou `docs/reports/` (`7736e20`) alterou marcação de status e prosa. As Portas 1 e 2 seguem varrendo 548 linhas / 109 KB |

## Fase 1b — mortalidade

**0 de 110 (0%).**

Nenhum 🟢 Resolved, nenhum ⚰️ Obsoleto. Este número mede a **imobilidade do repositório**, não a
durabilidade do banco: nenhum byte mudou desde a última medição, logo nenhuma mudança pode ter
resolvido nada. Lê-lo como atestado de saúde seria converter um artefato de medição em conclusão.

**Deriva registrada:** `flow-session-start-118-lines-monolithic-…` está no banco com 118 linhas e
anotado em 2026-07-31 com 174. `scripts/hooks/session-start.sh` tem **310** hoje — 2,6× o número do
slug. O achado não foi resolvido; piorou de um jeito que o texto do banco não comunica mais.

---

## Achados originais por eixo

| Eixo | Originais | Observação |
|---|---:|---|
| **A** — Agnosticismo de stack | **0** | Varredura integral obrigatória executada: **124 candidatos → 0 violações originais**. 15 candidatos genuínos já estão no conjunto aberto (Porta 5) |
| **B** — Referências e consistência | **1** | MEDIUM |
| **C** — Fluxos, comandos e automação | **1** | MEDIUM-HIGH |
| **D** — Agentes e skills | **0** | Todos os gates de autoria passam; o passivo do eixo é backlog não executado, não deriva nova |
| **E** — Economia de tokens | **1** | LOW-MEDIUM |
| **Total** | **3** | |

### Tabela de severidade

| Severidade | Qtd. | Achados |
|---|---:|---|
| HIGH | 0 | — |
| MEDIUM-HIGH | 1 | `flow-prompt-auditoria-interactive-plan-gate-unsatisfiable-in-unattended-run` |
| MEDIUM | 1 | `ref-readme-sync-gate-discovers-only-pt-br-suffix-blind-to-inverted-en-suffix-pair` |
| LOW-MEDIUM | 1 | `token-archive-index-rotates-index-sections-only-report-directories-never-pruned` |
| LOW | 0 | — |

### Os três achados

**1. O prompt de auditoria é interativo e desassistido ao mesmo tempo** (MEDIUM-HIGH,
`docs/reports/_prompt-auditoria.md`). A regra **inviolável** 7 exige aprovação humana antes de
qualquer escrita (`:31-33`), e `:7` manda "colar o bloco em uma sessão nova" — mas `:320-358` executa
`git add`/`commit`/`push` para `main` sem nenhum ponto de confirmação, com tratamento de erro escrito
para quando ninguém está olhando (`:333-334`, `:345-347`). Numa execução desassistida o pass ou trava
esperando um interlocutor inexistente, ou viola em silêncio uma regra rotulada como inviolável — e o
julgamento "esta regra não se aplica aqui" fica então disponível para as regras 1, 3 e 5.

**2. O gate de paridade EN ↔ pt-BR é cego ao par que inverte a convenção** (MEDIUM,
`.github/scripts/ci/02-readme-sync.sh`). A descoberta é `find . -name '*.pt-BR.md'` (`:192`), com o
par derivado por `${ptbr%.pt-BR.md}.md` (`:183`). `docs/reports/metrics-last-20-days.md` (pt-BR, 594
linhas) e `docs/reports/metrics-last-20-days.en.md` (EN, 594 linhas) invertem os dois papéis e
escapam inteiros — o gate imprime `OK` para 6 pares e termina em `readme-sync OK ✓` sem nunca
mencionar o sétimo. São 1.188 linhas de tradução sem gate e sem regra que as obrigue a permanecer em
sincronia. **Refina** o fingerprint executado `flow-readme-sync-ci-hardcodes-three-doc-pairs-…`.

**3. A rotação de 90 dias só move texto** (LOW-MEDIUM, `helpers/archive-index.sh`). O script opera
inteiramente sobre `INDEX_FILE` (`:34`, `:162`); os diretórios `docs/reports/<data>/` que suas linhas
referenciam nunca são podados. São 141 KB por pass, 1,0 MB acumulado em 36 dias, projetando ~7,3
MB/ano em um diretório que nenhum agente lê e todo contribuidor clona — e a Fase 0 de todo pass
executa `ls docs/reports/` sobre uma lista que só cresce.

---

## Descartados por duplicação

| Candidato | Porta | Motivo |
|---|---|---|
| Output do pass anterior não commitado, sem mecanismo de detecção | **5** | `gov-audit-pass-output-uncommitted-with-no-detection-mechanism` (HIGH, aberto) — a recorrência confirma, não descobre |
| `CLAUDE.md:92,313` dizem teto 205; `size-limits.sh:44` tem `AGENT_LIMIT=211` | **5** | `agent-line-cap-205-documented-in-claude-md-vs-211-enforced-by-size-limits` (HIGH, aberto desde 2026-08-14) |
| `size-limits.sh` sai 1 por `CLAUDE.md: 602 lines` sob cabeçalho `ERRORS` | **5** | `auto-size-limits-claude-md-warning-counted-as-violation-turns-ci-lint-red` (HIGH, aberto) |
| `orphan-skill-scan` reporta 3 cargas duplicadas que são citação de regra | **3** | Alvo e causa raiz coincidem com `ref-orphan-skill-scan-…-cannot-distinguish-load-from-narrative-mention` (2 de 3) |
| `CLAUDE.md` § File Structure omite `docs/harness.md`, `credentials.local.md`, `user-preferences.md`, `development/`, `prompts/` | **3** | Alvo, causa raiz e remediação coincidem com a família `ref-claude-md-file-structure-*` (3 de 3) — mesma porta pela qual o caso `docs/prompts/` já caiu |
| Tabela de comandos do `README.md` omite `/devteam:install` | **5** | Já no conjunto aberto |
| Os 15 candidatos genuínos do Eixo A (`frontend-developer.md:3,91,96` · `frontend-test-specialist.md:141-153` · `database-specialist.md:84,133` · `devops-specialist.md:137-148` · `security-specialist.md:80-85` · `backend-reviewer.md:30` · `mobile-developer.md:159` · `audit.md:54,126,128` · `relayout.md:32` · `mobile.md:19,26,27` · `setup-assistant.md:146-147` · `commit.md:125-133` · `devops.md:2,14`) | **5** | Todos registrados e abertos; árvore idêntica à dos dois passes anteriores |
| `orchestration` 391 linhas · `interaction-patterns` 209×34 · `token-efficiency` 160×18 · `migration-v1-to-v2` 438 linhas · `CLAUDE.md` 602 linhas · `install.sh` 1.240 linhas | **5** | Todos no conjunto aberto |
| Dois laços de `ScheduleWakeup` concorrentes (1200–1800 s vs. 300 s) | **5** | `token-two-schedulewakeup-poll-loops-same-spawn-round-300s-vs-1200-1800s` (MEDIUM-HIGH, aberto) — reconfirmado na amostra da Fase 1b |
| Cópia verbatim de 14 linhas do nudge de learn em `pr.md:140-152` | **5** | `token-pr-md-14-line-verbatim-learn-nudge-…` (aberto) |
| `_prompt-auditoria.md` diz "two report files" (são 8) e manda push em `main` contra a regra 8 | **5** | `flow-prompt-auditoria-commit-step-contradicts-branch-rule` (MEDIUM, aberto). O achado 1 deste pass passou pela Porta 3 contra ele: alvo coincide, causa raiz e remediação não (1 de 3) |

---

## Leitura final

O repositório está parado há catorze dias e o banco de fingerprints está saturado para esta árvore:
110 achados abertos, dos quais 3 HIGH, aguardando execução. Três passes de auditoria consecutivos
contra o mesmo `HEAD` produziram 37, 21 e agora 3 achados originais — a curva descendente é o
resultado correto de um protocolo anti-duplicação funcionando, não de um repositório ficando limpo.

O gargalo mudou de lugar. Não é mais descobrir; é executar. O próximo pass de maior valor
provavelmente não é uma auditoria.
