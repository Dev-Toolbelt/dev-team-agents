# Auditoria Guardiã — 2026-08-21

**Data:** 2026-08-21 · **Baseline:** `HEAD` = `a67cac9` · **Baseline anterior:** `c03f898`

## Sumário executivo

Delta grande desde o baseline anterior: **39 arquivos de código em 33 commits** (2026-08-14 →
2026-08-21), incluindo um comando novo (`/devteam:merge`), uma skill nova (`work-feedback`), e a
promoção do `02c-full-suite-guard.sh` a **hook bloqueante**. O banco continua íntegro: reabertura de
**4,2%** na Fase 1 (limiar de escalonamento: 15%) e **2,4% de mortalidade** na Fase 1b.

**O achado principal do pass são os eixos, e dentro deles um padrão que já é o terceiro pass
consecutivo a se repetir: as mudanças de comportamento do delta carregam defeito verificado, e
nenhum gate automático cobre essa classe.** Dos 7 HIGH deste pass, **5 vieram de commits do delta** —
`b0383d6` (merge), `abb8483` (guarda bloqueante), `a3e6095` (orchestration), `7e62124` (learn nudge)
e `7e62124`/`a1e3791` (CLAUDE.md em 602 linhas).

**Três consequências imediatas, verificadas mecanicamente:**

1. **O job `lint` do CI está vermelho no HEAD.** `helpers/size-limits.sh:92` empilha o *warning
   threshold* do `CLAUDE.md` (600) no mesmo array das violações de falha (700), e o exit code deriva
   só desse array. `bash .github/scripts/ci/01-lint.sh` sai **1**, e `01-lint.sh:88` o invoca como
   `blocking`. Qualquer push encontra CI vermelho por essa causa, independentemente do conteúdo.
2. **O hook bloqueante que `abb8483` criou falha aberto.** O dispatcher `pre-tool-use.sh` entrega o
   payload por pipe; `02-graphify-hint.sh:14` sai antes de consumir stdin; payload >64 KB produz
   SIGPIPE → `pipefail` → exit 141, e a regra "primeiro não-zero vence" sobrescreve o `exit 2` do
   `02c`. Reproduzido com payload de 300 KB.
3. **`/devteam:merge` não alcança o caminho worktree, e o nudge de `/devteam:learn` nunca dispara.**
   Os Steps 0/1 resolvem branch e árvore sem `-C`/`--git-common-dir` antes do Step 2 ler
   `.worktree-session`; e o teste de ancestralidade do nudge está invertido em quatro comandos
   (`merge.md:89`, `pr.md:148`, `refactor.md:162`, referenciado por `audit.md:188`).

Um quarto item merece registro pela natureza: **dois hooks documentados como vivos estão desativados
no disco** — `_disabled-01-check-updates.sh` (com `check-updates.sh` e `update.sh` fazendo `exec`
dele, o que faz `/devteam:update` reportar "Up to date" num projeto desatualizado) e
`_disabled-04-notifier.sh` (descrito em quatro documentos como disparando a cada turno). Ambos são
HIGH pelo critério "documenta como verdade algo factualmente falso".

**Créditos ao delta**, que não viram achado: o marcador uma-vez-por-sessão do `02-graphify-hint.sh`
elimina reinjeções de `additionalContext`, e `8267da1` trocou o `git diff` cru de `pr.md:99` por um
diff escopado — resolvendo o único fingerprint que a Fase 1b fechou.

---

## Método

| Fase | Escopo | Resultado |
|---|---|---|
| **0** | Carregar banco, fixar baselines, apurar delta | 176 fingerprints vivos · delta `c03f898..a67cac9` = 39 arquivos de código, 33 commits |
| **1** | Verificação ancorada em git das marcas ✅/⚠️ | **48 de 119** verificados |
| **1b** | Validade dos 42 achados abertos | 1 🟢 · 0 ⚰️ · 41 ainda reproduzem |
| **2** | Cinco eixos (A integral, B–E priorizados pelo delta) | **37 achados originais** |

**Critério de amostragem da Fase 1:** o conjunto verificável (119) excede 60, então foram
verificados **todos** os HIGH e MEDIUM-HIGH (18) mais uma amostra aleatória de **30% do restante**
(30 de 101, semente `20260821`). Cobertura declarada: **48 de 119 (40%)**.

Toda verificação partiu de `git show` da janela da marcação, nunca da leitura do relatório-fonte —
o relatório descreve o *problema*, o git descreve o *fato*.

## Placar da Fase 1

| Marca verificada | Qtd | % |
|---|---|---|
| ✅ **Feito** | 43 | 89,6% |
| 🟡 **Parcialmente feito** | 3 | 6,2% |
| 🔴 **Não feito** | 2 | **4,2%** |

Abaixo do limiar de escalonamento de 15%. As duas reaberturas:

- `agent-software-architect-foundational-rule-51-lines-2x-avg` → 🔴. `b4e219f` tocou o arquivo, mas a
  Foundational Rule **cresceu**: 37 linhas antes do commit remediador → 41 dentro dele → **43 no
  HEAD**. Segue a maior do repo.
- `token-claude-md-426-lines-still-monolithic-…` → 🔴 pela **terceira vez**. Nenhum commit da janela
  tocou `CLAUDE.md`/`CLAUDE-md/`; o arquivo está em **602 linhas** contra 425 na abertura do achado.
  É também a causa direta do CI vermelho descrito acima.

As três parciais são reincidentes de escopo conhecido (`size-limits` sem equivalente no dispatcher
`Stop`; tags publicadas mantidas por decisão; `commit.md`/`refactor.md` ainda acima da mediana).

## Mortalidade da Fase 1b

**1 de 42 (2,4%)** — indicador de saúde do banco. Único fechamento:
`token-pr-md-unbounded-full-diff-to-repetitive-tier-…` → 🟢 resolvido por `8267da1`.

Os 41 restantes foram re-evidenciados no HEAD. Quatro tiveram o problema **agravado** pelo delta e
estão re-anotados no relatório da fase: a legenda do `_index.md` (agora 213 entradas contra "131"),
`CLAUDE-md/hooks.md:64` (que diz "it never blocks" sobre um hook que agora bloqueia), o casamento por
substring do `02c` (que antes só injetava contexto e agora bloqueia) e a skill `orchestration`
(377 → 391 linhas).

## Achados originais por eixo

| Eixo | HIGH | MEDIUM-HIGH | MEDIUM | LOW-MEDIUM | LOW | Total |
|---|---|---|---|---|---|---|
| A — Agnosticismo de stack | 0 | 2 | 2 | 0 | 0 | **4** |
| B — Referências e consistência | 3 | 0 | 2 | 0 | 0 | **5** |
| C — Fluxos e comandos | 3 | 3 | 4 | 3 | 1 | **14** |
| D — Agentes e skills | 1 | 3 | 2 | 1 | 1 | **8** |
| E — Economia de tokens | 0 | 2 | 2 | 2 | 0 | **6** |
| **Total** | **7** | **10** | **12** | **6** | **2** | **37** |

O Eixo A rodou **varredura integral** (não amostrada), conforme a regra: **124 candidatos → 4
violações**. Os 120 descartes são, em ordem de volume: ~78 linhas de tabela de detecção e roteamento
condicional (legítimas por design), ~14 exemplos rotulados ou já protegidos por frase-guarda
agnóstica na mesma seção, ~11 falsos positivos de substring do regex, e 17 barrados pelas portas de
antiduplicação.

## Os 3 achados mais graves

1. **`auto-size-limits-claude-md-warning-counted-as-violation-turns-ci-lint-red`** (HIGH,
   `helpers/size-limits.sh`) — o CI está vermelho agora, e a causa é um *warning* tratado como
   violação. Bloqueia todo merge até ser corrigido, e a correção é de uma linha.
2. **`flow-pre-tool-use-dispatcher-sigpipe-141-masks-02c-block`** (HIGH,
   `scripts/hooks/pre-tool-use.sh`) — a guarda que `abb8483` acabou de tornar bloqueante falha aberto
   sempre que o payload passa de 64 KB. Um gate de segurança que falha aberto é pior que a ausência
   de gate, porque cria confiança injustificada.
3. **`skill-orchestration-two-sections-both-numbered-check-5-breaks-cross-refs`** (HIGH,
   `skills/architecture/orchestration/SKILL.md`) — `a3e6095` criou um segundo `### 5.`; as três
   referências cruzadas a "check 5" (`:270`, `software-architect.md:89`, `CLAUDE.md:172`) passaram a
   resolver para seções opostas, e o **único** caminho de carga da skill `work-feedback` aponta para
   a errada.

Menção obrigatória fora do pódio: `ref-check-updates-shim-and-update-sh-exec-renamed-away-…` e
`ref-notifier-documented-as-live-in-four-docs-…` — dois hooks renomeados para `_disabled-` sem que
nenhum dos documentos que os descrevem tenha sido atualizado. O primeiro faz `/devteam:update`
mentir sobre estar atualizado.

## Descartados por duplicação

Ver a seção **"Descartados por duplicação"** ao final de
[`docs/reports/_index.md`](../_index.md), sob a seção `## 2026-08-21`. Resumo por porta:

| Porta | Critério | Candidatos barrados |
|---|---|---|
| **1 — literal** | Slug já existe no banco | 1 |
| **3 — semântica** | 2 ou 3 de 3 atributos (alvo, causa raiz, remediação) coincidem | ~12 |
| **4 — escopo menor** | Tema registrado, sem sub-escopo estritamente contido e inédito | 2 |
| **5 — estado** | Já pertence ao conjunto aberto (registrado, não implementado) | ~21 |

Um achado passou pela porta 4 **com** sub-escopo válido e foi registrado com `**Refina:**`:
`token-output-format-third-copy-of-plan-format-42-lines-nine-load-sites`, que refina
`gov-plan-template-vs-skill-duplication` — o fix original consolidou duas cópias do formato de plano
e não tocou a terceira, em `output-format/SKILL.md:144-185`.

Dois "achados" propostos pelo `orphan-skill-scan.sh` foram verificados um a um e descartados como
**falsos positivos do próprio scanner**: as segundas ocorrências de `test-pyramid/SKILL.md` em
`backend-test-specialist.md`/`frontend-test-specialist.md` e de `worktree/SKILL.md` em `merge.md` são
citações de regra ou delegação a seção distinta, não um segundo `load`.

## Gates

| Gate | Saída no HEAD |
|---|---|
| `helpers/agent-lint.sh` | ✓ clean |
| `helpers/orphan-template-scan.sh` | ✓ clean |
| `helpers/orphan-skill-scan.sh` | 3 avisos de "duplicate skill loads" — **todos falsos positivos**, ver acima |
| `helpers/size-limits.sh` | **exit 1** — `CLAUDE.md: 602 lines (warning threshold: 600)` contado como violação (achado HIGH nº1) |
| `helpers/check-fingerprint-uniqueness.sh` | ✓ 213 slugs únicos |
| `helpers/archive-index.sh --dry-run` | ver seção de encerramento do banco |

## Arquivos deste pass

| Arquivo | Conteúdo |
|---|---|
| [`00-guardiao-verificacao.md`](00-guardiao-verificacao.md) | Fases 1 e 1b, item a item |
| [`01-agnosticismo-de-stack.md`](01-agnosticismo-de-stack.md) | Eixo A — varredura integral |
| [`02-referencias-e-consistencia.md`](02-referencias-e-consistencia.md) | Eixo B |
| [`03-fluxos-e-comandos.md`](03-fluxos-e-comandos.md) | Eixo C |
| [`04-agentes-e-skills.md`](04-agentes-e-skills.md) | Eixo D |
| [`05-economia-tokens.md`](05-economia-tokens.md) | Eixo E |
| [`../_index.md`](../_index.md) | Banco de fingerprints — 213 entradas |
