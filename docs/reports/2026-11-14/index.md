# Auditoria Guardiã — 2026-11-14

**Data:** 2026-11-14 · **Baseline:** `HEAD` = `c6398e5` · **Baseline anterior:** `5133c8c`

> **O achado principal deste pass é um defeito que corrompe o próprio banco de fingerprints.**
> `helpers/archive-index.sh` faz *append* das seções no arquivo morto (`:145-146`) dezesseis linhas
> **antes** do `mv` que reescreve `_index.md` (`:162`), sem rollback e sob `set -euo pipefail`.
> Quando o `mv` final falha, o arquivo morto fica com as seções duplicadas e o `_index.md` intacto:
> **32 slugs duplicados** e `helpers/check-fingerprint-uniqueness.sh` passando de exit 0 a exit 1 —
> o que faz `03b-fingerprint-uniqueness.sh:45` sair 2 em **todo** `Stop` e `01-lint.sh:85` ficar
> vermelho como `blocking`. O script se autodeclara "Exit 0 always … non-destructive" (`:27`), e
> `99b-archive-index.sh:45-46` repete essa premissa como justificativa para engolir o erro.
> Registrado como `auto-archive-index-appends-archive-before-index-rewrite-no-rollback` (HIGH).

> **Nota de procedência — este pass reproduziu o defeito acima no repositório do usuário.**
> Durante a Fase 1b, um dos sub-auditores executou `helpers/archive-index.sh` (sem `--dry-run`) para
> medir um fingerprint aberto sobre esse mesmo script. O `mv` final foi negado pelo filesystem
> montado em que este pass rodou, e a árvore ficou exatamente no estado descrito: `_index.md`
> intacto em 823 linhas, `_index-archive-2026-Q3.md` com +124 linhas e 32 slugs duplicados,
> `check-fingerprint-uniqueness.sh` saindo 1. **O arquivo foi restaurado de `HEAD` antes de
> qualquer escrita de relatório** (`git show HEAD:docs/reports/_index-archive-2026-Q3.md >` o
> próprio caminho — truncagem no lugar, sem unlink) e a árvore voltou a ficar limpa com o gate em
> exit 0. O defeito **não é um artefato do acidente**: ele foi depois reproduzido de forma isolada
> num clone em `c6398e5`, e as linhas citadas são do `HEAD`.

> **Rotação executada neste pass.** Duas seções passaram dos 90 dias (`2026-08-12` e `2026-08-14`,
> cutoff `2026-08-16`) e foram rotacionadas para `_index-archive-2026-Q3.md` conforme o passo 4 da
> Atualização do Banco. Como o `mv` do helper não funciona no filesystem deste pass, a rotação foi
> aplicada com escrita truncante nos dois arquivos, a partir do resultado **bit a bit** do próprio
> `helpers/archive-index.sh` rodado num clone — não à mão.

## Método

**Fase 0.** Banco lido nos dois arquivos: `docs/reports/_index.md` (174 entradas) e
`docs/reports/_index-archive-2026-Q3.md` (139) = **313** entradas. Conjunto verificável **151**
(✅/⚠️), conjunto aberto **140** (133 sem marcador + 7 marcadas apenas 🔴), conjunto de exclusão
**22**.

**Delta:** **16 commits e 86 arquivos** desde `5133c8c` — o menor delta desde 2026-09-18 e o
primeiro working tree **limpo** em três passes. Concentrado em `skills/third-party` (21),
`skills/shared` (12), `docs/reports` (9), `app/src` (7), `docs/development` (6), `app/test` (5),
`scripts/lib` (3), mais 6 arquivos de teste novos. Temas: skill `security-audit` vendorizada e
pinada (ADR-0047), agentes de execução consultando os documentos do projeto antes de perguntar
(ADR-0064), bump do marcador de bloco de roteamento via health check (ADR-0065), roster de sprint +
modo de review automático, grupos de credenciais duplicáveis e reordenáveis, heading de status na
abertura das respostas de entrega.

**Fase 1.** Amostragem: todos os **43** HIGH/MEDIUM-HIGH + **30% dos 108 restantes** (32),
`seed=20261114` → **75 de 151**.

**Fase 1b.** Conjunto aberto de **140**, revalidado integralmente.

**Fase 2.** Cinco eixos, Eixo A em varredura integral e os demais priorizando o delta. Todo
candidato passou pelas cinco portas do Protocolo Anti-Duplicação, mais uma rodada de deduplicação
**cross-eixo** — **1 par fundido** (Eixos D ↔ E, 3 de 3 atributos).

## Cobertura e placar da Fase 1 — **75 de 151 (49,7%)**

| Marca verificada | Qtd | % |
|---|---|---|
| ✅ **Feito** | 57 | **76,0%** |
| 🟡 **Parcialmente feito** | 13 | 17,3% |
| 🔴 **Não feito** | 5 | **6,7%** |

**Reaberturas novas: 0** — **quarto pass consecutivo em zero**. As 5 🔴 e 11 das 13 🟡 já carregavam
anotação. Os 6,7% ficam muito abaixo do limiar de escalonamento de 15%: a integridade do banco
**não** está comprometida.

As **2 divergências novas** são ambas 🟡 e da mesma classe dos passes anteriores — a correção
entregou o defeito nomeado e deixou um sub-escopo que o relatório-fonte já descrevia
(`ref-02c-guard-make-composer-shapes-…`: a tabela *Runner Filters* segue sem linha para
npm/composer/make; `ref-docs-agents-md-model-column-wrong-…`: o sub-escopo "and unvalidated" nunca
fechou e a tabela voltou a divergir em `backend-test-specialist`).

**Nota de método aplicada em 53 dos 75 itens** (49 com `alvo: None` + 4 cuja correção vive em outro
arquivo). Nenhum 🔴 falso produzido por aplicar `alvo:` cegamente.

**Três reversões silenciosas**, duas delas sem gate há meses: `scripts/install.sh:24` (o `d454f63`
reintroduziu, no mesmo dia, o `BASH_SOURCE[0]` sem guarda que o `88834b6` acabara de endurecer — o
install pipeado aborta, e o teste de regressão não pega porque só assere a ausência do marcador
`PWNED`) e `agents/backend-test-specialist.md` (`tier:` trocado depois de os dois docs já terem
sido escritos com o valor antigo).

## Mortalidade da Fase 1b — **0,71% (1 de 140)**, cobertura **140 de 140 (100%)**

| Estado | Qtd | % |
|---|---|---|
| Ainda reproduz | 139 | 99,3% |
| 🟢 **Resolved** | 1 | 0,71% |
| ⚰️ **Obsoleto** | 0 | 0% |

O único 🟢 é `agent-orchestrator-route-has-no-path-to-architecture-work`, por `827b1a9`.
**E o número baixo não é imobilidade: 36 dos 140 alvos abertos (26%) foram tocados pelo delta, e os
36 seguem reproduzindo** — dos 16 commits, apenas um fechou um achado aberto, e por um arquivo que
não é o `alvo:` registrado.

**46 fingerprints abertos mediram pior — recorde do banco** (quase o dobro dos 24 de 2026-11-07,
sobre um delta cinco vezes menor). As piores: `CHANGELOG.md` 441 → **2.470** linhas · `install.sh`
947 → **1.405** · wiki index 13.715 → **27.768 B** · `interaction-patterns` 209 ln × 26 → **404 × 44**
· READMEs 228 → **501** cada · `session-start.sh` 310 → **460** · índice de skills symlinkadas
12.751 B / 155 → **19.298 B / 168** · `fix-patterns.md` 517 → **665** · `checks-list.md` 668 → **889**
· diretórios de report 1,0 → **1,84 MB** com 0 podados · a cópia instalada versionada passou de
58 divergentes de 666 e 5 dias para **66 de 735 e 10 dias**. Cinco mediram melhor.

## Achados originais por eixo — **17**

| Eixo | Candidatos → achados | Nota |
|---|---|---|
| **A — Agnosticismo de stack** | 60 → **1** | Varredura semente obrigatória: **130 hits → 49 candidatos → 0 violações** (quinto zero em seis passes, e estrutural: nenhuma linha que o delta adicionou em `agents/`/`commands/` contém token de stack). A única violação veio da **varredura complementar** — e a lacuna do regex semente (sem `gh`/`github`/`glab`) é ela mesma um fingerprint aberto |
| **B — Referências e consistência** | 18 → **5** | 1 HIGH, 1 MEDIUM-HIGH, 1 MEDIUM, 2 LOW-MEDIUM. Os quatro helpers saem **limpos** (1 WARN consultivo: `CLAUDE.md` 602 linhas) — e é a estreiteza da cobertura deles que explica os dois piores achados |
| **C — Fluxos, comandos e automação** | 11 → **5** | 1 HIGH, 2 MEDIUM-HIGH, 2 MEDIUM. Inclui o achado principal do pass |
| **D — Agentes e skills** | 18 → **4** | 1 MEDIUM-HIGH, 2 MEDIUM, 1 LOW-MEDIUM (5 sobreviveram às portas; 1 fundido cross-eixo com o Eixo E). Quatro dos cinco são sobre a skill `security-audit` vendorizada no delta |
| **E — Economia de tokens** | 8 → **2** | 2 MEDIUM. Eixo mais saturado do banco; os dois achados são no território novo da skill vendorizada, não nos alvos já registrados |

## Tabela de severidade

| Severidade | Qtd | Fingerprints |
|---|---|---|
| **HIGH** | 2 | `auto-archive-index-appends-archive-before-index-rewrite-no-rollback` · `docs-sync-install-opencode-claims-22-command-keys-while-renderer-emits-42` |
| **MEDIUM-HIGH** | 5 | `flow-pr-md-pr-creation-github-only-while-review-md-is-platform-neutral` · `ref-mobile-command-findings-gate-spawns-nonexistent-test-specialist-agent` · `flow-assumptions-lists-absent-from-the-verbatim-spawn-closing-line` · `auto-third-party-sync-hashes-the-git-index-not-the-extracted-tree` · `skill-third-party-security-full-audit-approval-not-emitted-as-plan-approved` |
| **MEDIUM** | 7 | `docs-sync-commands-md-security-row-omits-full-audit-mode-spawns` · `flow-ask-rather-than-assume-stale-in-five-implementation-commands` · `flow-security-full-audit-branches-on-a-skill-the-command-never-loads` · `skill-three-third-party-bridges-triplicate-provider-path-table-no-home` · `skill-security-output-template-has-no-home-for-needs-validation-records` · `token-security-audit-guidance-row-loads-13-8kb-full-audit-only-plus-phase-file` · `token-promotion-procedure-tripled-while-wrapper-declares-nothing-is-promoted` |
| **LOW-MEDIUM** | 3 | `ref-wiki-keychain-entry-adr-0010-link-wrong-depth-and-nonexistent-filename` · `ref-checks-list-points-at-docs-sync-core-rules-section-that-does-not-exist` · `agent-devops-specialist-cites-output-format-section-without-loading-skill` |
| **LOW** | 0 | — |

## Os três achados mais graves

1. **`auto-archive-index-appends-archive-before-index-rewrite-no-rollback` (HIGH)** — a rotação do
   banco não é atômica e não tem rollback; uma falha no `mv` final deixa 32 slugs duplicados e
   derruba o gate de unicidade em todo `Stop`. Reproduzido empiricamente duas vezes neste pass.
2. **`docs-sync-install-opencode-claims-22-command-keys-while-renderer-emits-42` (HIGH)** —
   `docs/install-opencode.md:13` promete 22 chaves de comando enquanto `render_provider.py:1087`
   itera `commands/*.md` sem filtro e emite 42; o próprio instalador imprime o número real na tela
   do usuário, e a página é o destino do README nos dois idiomas. Nenhum gate confere contagens de
   saída de instalador contra os docs.
3. **`ref-mobile-command-findings-gate-spawns-nonexistent-test-specialist-agent` (MEDIUM-HIGH)** —
   `commands/mobile.md:78,80` mandam spawnar `test-specialist`, agente que não existe; o próprio
   arquivo resolve o nome certo em `:12,28,29`, e os três comandos irmãos nomeiam o agente real nas
   mesmas linhas. `orchestration/SKILL.md:178-183` diz que um tipo desconhecido faz o spawn falhar.

## Descartados por duplicação

**98 candidatos descartados** (115 levantados → 17 registrados). A lista completa, candidato por
candidato e com a porta de cada um, está no fim de cada arquivo de eixo. Resumo:

| Eixo | Descartados | Distribuição |
|---|---|---|
| **A** | 59 | 42 pelas portas 1/3/5 (19 temas agrupados, todos com fingerprint-pai no conjunto aberto), 7 não eram violação da regra, 10 falsos positivos de substring (`ho**nest**a`, `pe**rspec**tive`, `re**act**ivation`, `fl**aws**`, `**pip**eline`) |
| **B** | 13 | 8 pelas portas 1/3/5 — incluindo um **fundido com o Eixo D no próprio pass** — e **5 premissas refutadas pela evidência própria** |
| **C** | 6 | 2 pelas portas 1/3, 2 mortos **antes** da porta 1 por estarem declarados em ADR (0064:30, 0065:35), 2 premissas refutadas |
| **D** | 14 | 1 **fundido cross-eixo** com o Eixo E (Porta 3, 3 de 3), 4 pelas portas 3/4/5, **9 premissas refutadas pela evidência própria** |
| **E** | 6 | 3 pelas portas 3/5, 3 mortos na evidência |

**O par fundido cross-eixo:** o Eixo D levantou
`skill-third-party-security-guidance-row-loads-full-audit-only-reporting-file` (a linha de Guidance
Mode do roteador manda carregar um arquivo que é 100% procedimento de full audit, proibido nesse
modo) e o Eixo E levantou
`token-security-audit-guidance-row-loads-13-8kb-full-audit-only-plus-phase-file` (a mesma linha
carrega 13,8 KB de material exclusivo de full audit). Mesmo alvo, mesma causa raiz, mesma
remediação — **3 de 3**. Registrado o do Eixo E, que quantifica o custo; a evidência de correção do
Eixo D foi absorvida no relatório do Eixo E.

**As 16 premissas refutadas pela evidência própria** são o outro indicador de saúde do filtro: em
nove casos a cadeia que parecia quebrada fechava por um arquivo que o candidato não tinha lido
(`project-context:235` levando § Documented Answer First a todo agente; `orchestration:377` já
exigindo `PLAN_APPROVED:` no contrato genérico de spawn; `output-format:46` e `ai-writing-signs:60`
já permitindo o heading com emoji; `size-limits.sh:67-68` isentando `skills/third-party/` por
decisão registrada).

## Arquivos deste pass

| Arquivo | Conteúdo |
|---|---|
| [`00-guardiao-verificacao.md`](00-guardiao-verificacao.md) | Fases 1 e 1b, item a item (75 + 140) |
| [`01-agnosticismo-de-stack.md`](01-agnosticismo-de-stack.md) | Eixo A — 1 achado |
| [`02-referencias-e-consistencia.md`](02-referencias-e-consistencia.md) | Eixo B — 5 achados |
| [`03-fluxos-e-comandos.md`](03-fluxos-e-comandos.md) | Eixo C — 5 achados |
| [`04-agentes-e-skills.md`](04-agentes-e-skills.md) | Eixo D — 4 achados |
| [`05-economia-tokens.md`](05-economia-tokens.md) | Eixo E — 2 achados |

## Gates

```
$ bash helpers/check-fingerprint-uniqueness.sh
✓ All 335 fingerprint slugs are unique across 2 bank file(s).        # exit 0

$ bash helpers/archive-index.sh --dry-run
→ 2 dated section(s) older than 2026-08-16:
    2026-08-12 — 8 fingerprint entr(ies) → docs/reports/_index-archive-2026-Q3.md
    2026-08-14 — 26 fingerprint entr(ies) → docs/reports/_index-archive-2026-Q3.md
→ Dry-run: no files modified. docs/reports/_index.md would go from 879 to 757 lines.

# rotação aplicada (resultado bit a bit do helper, ver nota de procedência acima)
$ bash helpers/archive-index.sh --dry-run
✓ No entries older than 90 days (cutoff 2026-08-16) in docs/reports/_index.md.
$ bash helpers/check-fingerprint-uniqueness.sh
✓ All 335 fingerprint slugs are unique across 2 bank file(s).        # exit 0
```

Pós-rotação: `_index.md` com **159** entradas (757 linhas), `_index-archive-2026-Q3.md` com **171**
— 330 fingerprints no banco, 313 antes do pass mais os 17 deste. Os 335 slugs que o gate conta
incluem as 5 linhas de prosa que `auto-check-fingerprint-uniqueness-grep-admits-discarded-candidate-lines-as-slugs`
(aberto) descreve.
