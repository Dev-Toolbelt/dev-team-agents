# Auditoria Guardiã — 2026-09-18

**Data:** 2026-09-18 · **Baseline:** `HEAD` = `ef69da3` · **Baseline anterior:** `9530551`

## Sumário executivo

**O achado principal deste pass é uma marca verde sobre um arquivo editado ontem.**

`scripts/new-adr.sh` foi tocado no delta — commit `ef69da3`, de 2026-09-17, que corrigiu o parsing
octal do número de sequência. O mesmo arquivo carrega desde 2026-07-31 a marca ✅ Executed do
fingerprint `auto-new-adr-sh-sed-title-substitution-…`, e a verificação desta Fase 1 mostra que
**nenhum commit jamais tocou o escaping**: a linha `:61` — `-e "s|\[Title\]|$TITLE|g" \` — está
byte-idêntica à evidência original. Um pass que confiasse na marcação nunca teria olhado; um que
olhasse só o `git log` do arquivo teria visto três commits recentes e assumido manutenção ativa. É
o caso de uso do modo guardião em forma pura, e vale registrá-lo como tal.

**A integridade do banco não está comprometida, mas piorou.** 12,5% de 🔴 na amostra está abaixo do
limiar de escalonamento de 15% — é a maior taxa desde 2026-09-04, e nenhuma das duas 🔴 é achado
novo: uma é a quarta reabertura consecutiva do mesmo item (`CLAUDE.md` monolítico, que cresceu de
425 para 602 linhas enquanto a marca afirma extração), e a outra é a primeira verificação de um item
que nunca foi executado.

**O delta de código foi de dois arquivos em catorze dias**, e a Fase 1b mostra o efeito colateral
disso: mortalidade de 3,2%, próxima de zero pelo quarto pass. Essa taxa não é saúde — é imobilidade.
O sinal de fato preocupante é o inverso: **quatro fingerprints abertos mediram pior hoje do que no
dia em que foram registrados** (`install.sh` 503 → 1244 linhas; `orchestration` 377 → 391; a lista
de coding agents 8 → 9; o heredoc de preferências, de 1 chave faltante para 3). Um banco cujos
achados crescem enquanto a mortalidade cai está parado, não estável.

**Dois HIGH novos são gates mortos**, e os dois pelo mesmo mecanismo — um caminho literal duplicado
que divergiu: `03c-reuse-lint.sh` testa um `.csv` que nada no harness cria (o registro é `.md`),
logo o único gate automático do sistema de reuse-guidelines nunca rodou em nenhum projeto
instalado; e `path_rewrites` move `docs/development/` no texto renderizado para opencode e Codex sem
tocar nos três scripts embarcados, de modo que em dois dos três provedores o comando diz para checar
ADRs num diretório que o script que ele invoca na linha seguinte nunca popula.

---

## Método

| Fase | O que foi feito |
|---|---|
| **0** | Banco lido (241 fingerprints), baseline anterior recuperado (`9530551`), delta calculado: **2 arquivos de código** (`scripts/install.sh`, `scripts/new-adr.sh` em `ef69da3`), o resto sob `docs/reports/` |
| **1** | 16 fingerprints ✅/⚠️ verificados contra o git, item a item, com relocalização por símbolo |
| **1b** | 63 dos 117 fingerprints abertos reconfirmados no HEAD |
| **2** | 5 eixos — A integral, B–E priorizando o delta, todos sob o Protocolo Anti-Duplicação de 5 portas |

**Cobertura da Fase 1: 16 de 46 não cobertos (35%) · acumulado 115 de 121 (95%).**

Critério de amostragem: todos os HIGH/MEDIUM-HIGH não cobertos (1) + prioridade de delta (1) + 30%
aleatório dos 44 restantes, semente `20260918` (14).

### Placar da Fase 1

| Veredito | N | % |
|---|---|---|
| ✅ Feito | 13 | 81,3% |
| 🟡 Parcialmente feito | 1 | 6,3% |
| 🔴 Não feito | 2 | 12,5% |

**Acumulado:** 115 de 121 → 96 ✅ · 10 🟡 · 9 🔴 (84% confirmado, 7,4% divergente).
Escalonamento **não** disparado (12,5% < 15%).

### Fase 1b

**Cobertura:** 63 de 117 (54%) — todos os do delta, todos os 19 HIGH e 31 MEDIUM-HIGH, mais 9
cobrindo os 8 prefixos. **Mortalidade: 3,2% (2 de 63)** — 1 🟢 Resolved (`gov-audit-pass-output-uncommitted…`,
resolvido por `3acaa89`) e 1 ⚰️ Obsoleto (`agent-qa-specialist-in-app-browser-prefix-mcp-claude-browser-nonexistent`,
premissa refutada: o namespace existe).

---

## Achados originais por eixo

| Eixo | Arquivo | Originais |
|---|---|---|
| A — Agnosticismo de stack (varredura integral) | [`01-agnosticismo-de-stack.md`](01-agnosticismo-de-stack.md) | 4 |
| B — Referências e consistência | [`02-referencias-e-consistencia.md`](02-referencias-e-consistencia.md) | 5 |
| C — Fluxos, comandos e automação | [`03-fluxos-e-comandos.md`](03-fluxos-e-comandos.md) | 5 |
| D — Agentes e skills | [`04-agentes-e-skills.md`](04-agentes-e-skills.md) | 6 |
| E — Economia de tokens | [`05-economia-tokens.md`](05-economia-tokens.md) | 4 |
| **Total** | | **24** |

### Tabela de severidade

| Severidade | N | Achados |
|---|---|---|
| **HIGH** | 3 | gate de reuse-lint em `.csv` · `path_rewrites` vs. scripts embarcados · "recent git log" prometido por 18 agentes e ausente da skill |
| **MEDIUM-HIGH** | 7 | matriz de 5 runners no `mobile-developer` · tabela `sections/` quebrada no `comments-policy` · registro de espelhos de preferências defasado · `BASH_SOURCE` fallback resolvendo para o cwd · template de review triplicado · `git-workflow` vs. `worktree` no nome de branch · 151 skills no índice sempre carregado |
| **MEDIUM** | 8 | monocultura Jira/Linear · parser do `orphan-skill-scan` invadindo a tabela seguinte · CI nunca executa `install.sh`/`new-adr.sh` · três tabelas de scanner de segurança divergentes · `test-strategy` inlinando `test-pyramid` · bloco de cache do `current-context` · detecção de SO do `graphify-setup` · gate de telemetria reforkando |
| **LOW-MEDIUM** | 5 | `next-seo`/`astro-seo` no `seo-specialist` · `loki-config.md` inalcançável · coluna zen de `providers.md` · carimbo do `99b-archive-index` em falha · dois esquemas para `design-system.md` |
| **LOW** | 1 | `file.js` nos seis placeholders do `code-reviewer` |

### Varredura semente do Eixo A

**124 candidatos → 4 violações.** A contagem é **idêntica** à de 2026-09-11 porque
`git diff 9530551..ef69da3 -- agents/ commands/` é vazio. Os 120 descartes: ~25 falsos positivos por
substring (o regex não usa fronteira de palavra), ~40 em tabelas de detecção e roteamentos
condicionais, 3 sob "Examples", ~14 referências a ferramenta do próprio harness, 2 cláusulas
anti-acoplamento, 22 pela Porta 5 e ~12 pela Porta 3.

---

## Descartados por duplicação

O filtro é o que separa descoberta de reapresentação. Contagem por eixo (detalhe em cada relatório):

| Eixo | Candidatos descartados | Porta dominante |
|---|---|---|
| A | 28 | 5 (estado) — 13 de 28 |
| B | 13 | 5 e 3, meio a meio |
| C | 7 | 3 (semântica) |
| D | 10 | 5 (estado) |
| E | 9 | 3 (semântica) |
| **Total** | **67** | |

Três descartes merecem nota, porque são de tipo diferente:

1. **Refutados por evidência, não duplicados.** Quatro referências "quebradas" a skills
   (`workflow-detection`, `jquery`, `learn-nudge`, `model-identity/references/format.md`) existem
   apenas em `CHANGELOG.md:601` e em relatórios históricos — nenhuma em superfície viva. E
   `agents/mobile-test-specialist.md`, citado como inexistente, é a **opção A rejeitada** de
   `docs/development/adrs/0006-mobile-pipeline-architecture.md:17-18`.
2. **Um candidato promovido por engano e revertido na consolidação.** O Eixo D propôs
   `gov-claude-md-158-…` para o "12 items" da Context Loading Order; o item já está registrado e
   aberto como `docs-sync-claude-md-context-list-item-count-12-vs-11`. Porta 5.
3. **As três "cargas duplicadas" que o `orphan-skill-scan` reporta a cada Stop** continuam sendo
   falsos positivos do scanner, como verificado em 2026-08-21 e 2026-08-28 — e continuam custando
   12 linhas de contexto por Stop, agora registrado pelo Eixo E como descarte de Porta 3 contra o
   fingerprint pai.

---

## Os três achados mais graves

### 1. O gate de reuse-guidelines nunca rodou em projeto nenhum

`auto-stop-03c-reuse-lint-gates-on-csv-registry-while-harness-writes-md` — HIGH.
`scripts/hooks/stop/03c-reuse-lint.sh:11` testa `docs/development/reuse-guidelines.csv`; o registro
que `/devteam:rule` e `/devteam:sync-rules` escrevem, que `scripts/reuse-lint.sh:15` lê e que o
`CLAUDE.md` declara canônico é `.md`. O `-f` da linha 12 é sempre falso. Todo o sistema de reuse-
guidelines — comandos, skill, template, lint — tem seu único gate automático morto por uma
extensão. Correção: uma palavra.

### 2. Em dois dos três provedores, `/devteam:adr` checa duplicatas num diretório vazio por construção

`flow-path-rewrites-move-docs-development-but-shipped-scripts-hardcode-it` — HIGH.
`path_rewrites` reescreve `docs/development/` → `docs/` no texto renderizado para opencode e Codex,
mas `new-adr.sh:14`, `reuse-lint.sh:15` e `03e-adr-gap-check.sh:21` codificam o caminho antigo. O
comando manda checar `docs/adrs/`; o script que ele invoca na linha seguinte grava em
`docs/development/adrs/`. O passo *Check Before Creating* — que existe exatamente para impedir ADRs
duplicados — vê sempre um diretório vazio.

### 3. Dezoito agentes afirmam que a skill de contexto cobre o histórico git; ela não cobre

`agent-project-context-delegation-claims-recent-git-log-absent-from-skill-18x` — HIGH.
`grep -c 'recent git log' agents/*.md` → 18 de 18; `grep -i 'git log' skills/shared/project-context/SKILL.md`
→ exit 1. A `## Context Loading Order` tem 11 itens e nenhum é histórico. Nenhum agente lê o que a
árvore mudou nos últimos commits, e nenhum tem motivo para suprir a lacuna — cada um já declara que
a skill resolve.
