# Auditoria Guardiã — 2026-10-10

**Data:** 2026-10-10 · **Baseline:** `HEAD` = `349f18c` · **Baseline anterior:** `5e338d9`

> **Plan Gate.** Pass disparado por tarefa agendada, com instrução explícita de executar e
> commitar. Não houve aprovação humana do plano; o critério de amostragem da Fase 1 está declarado
> em `00-guardiao-verificacao.md` **antes** dos resultados, que é a garantia que o gate existe para
> dar.

## Sumário executivo

**O achado principal deste pass é o arquivo que serve de banco de auditoria afirmando, na linha
25, um fato falso sobre a automação do próprio repositório — e essa afirmação está marcada como
corrigida desde 2026-09-11.**

`docs/reports/_index.md:23-26` diz: *"That script currently has no trigger — no hook, no CI job, no
installer call — so rotation has never run."* O gatilho existe:
`scripts/hooks/stop/99b-archive-index.sh`, sub-script Stop na tier de cleanup, com stamp diário,
que dispara `helpers/archive-index.sh`. O fingerprint que descrevia essa divergência
(`docs-sync-reports-index-preamble-declares-archive-index-trigger-less-while-stop-99b-dispatches-it`)
foi marcado ✅ **Executed: 2026-09-11** — e nenhum commit tocou `docs/reports/_index.md` naquela
data. A marca é 🔴 por construção **e** por evidência no `HEAD`. É a única reabertura nova do pass,
e é a mais embaraçosa possível: o preâmbulo errado é a primeira coisa que todo pass de auditoria lê.

O resto do pass é um repositório em boa forma e um banco em estagnação de execução:

- **62 commits e 183 arquivos** desde o baseline, concentrados em `app/` (52) e `scripts/lib` (23) —
  duas subárvores com **uma única menção** nos 287 fingerprints do banco.
- **Nenhuma marca de execução nova** em 8 dias: os 62 commits entregaram funcionalidade (ADRs 0030
  a 0034, instaladores de CLI, release assinado) e não executaram nenhum achado registrado.
- **Dois achados abertos morreram** — um deles o HIGH que abria o pass anterior
  (`install-cli.sh` quebrado, resolvido por `5dcf340`).
- **Todos os sete gates do repositório saem limpos**, incluindo um que sai limpo errado
  (`orphan-skill-scan`, cego à forma de diretório, com 7 caminhos mortos na árvore).
- **Três achados originais**, todos em território que o banco nunca cobriu: dois gates ausentes em
  `app/`/`.github/` e o crescimento sem teto do índice do wiki.

## Método

| Fase | Cobertura | Como |
|---|---|---|
| Fase 1 | **76 de 153 (50%)** | todos os 43 HIGH/MEDIUM-HIGH + 30% aleatório dos 110 restantes (`seed=20261010`) |
| Fase 1b | **109 de 109 (100%)** | 35 com alvo tocado pelo delta → manual; 74 com alvo intocado desde o registro → reproduzem por construção |
| Eixo A | **integral** | 124 linhas de hit em `agents/` + `commands/` |
| Eixos B–E | delta prioritário + amostragem | `app/`, `scripts/lib`, `.github/`, mais os 7 gates |

A partição da Fase 1b é o que torna 100% honesto em vez de decorativo: um problema num arquivo que
nenhum commit tocou desde o registro não foi corrigido, e isso é verificável sem reler o arquivo.
A partição está declarada no relatório da fase.

## Placar da Fase 1

| Marca | N | % |
|---|---|---|
| ✅ **Feito** | 64 | **84,2%** |
| 🟡 **Parcialmente feito** | 6 | 7,9% |
| 🔴 **Não feito** | 6 | 7,9% |

**Reaberturas novas: 1 de 76 (1,3%)** — as outras 5 🔴 já estavam reabertas em passes anteriores.
O limiar de escalonamento de 15% **não** foi atingido: a integridade do banco está intacta, e os
84,2% são a quinta confirmação consecutiva acima de 80%.

As 6 🟡 são todas reconfirmações, três delas pela segunda ou terceira vez:
`flow-size-limits-sh-ci-only-warn-only-not-in-stop-dispatcher-…` (3ª),
`auto-update-no-integrity-check`, `ref-two-malformed-git-tags-…` (⚠️ deliberada),
`ref-notification-system-content-triplicated-…`, `token-git-log-window-overshoot` e
`token-current-context-block-deduplication`.

## Mortalidade da Fase 1b

**2 de 109 → 1,8%**, contra 9,3% no pass anterior.

- 🟢 `flow-install-cli-orphan-body-outside-main-aborts-every-run` (**HIGH**) — resolvido por
  `5dcf340`; `bash scripts/install-cli.sh --help` sai 0 no `HEAD` e `main()` fecha em `:163` sem
  corpo órfão.
- 🟢 `docs-sync-auto-learn-before-commit-still-documented-as-pre-commit-step-0` (**MEDIUM-HIGH**) —
  resolvido pela ADR-0034 e **não** pela remediação proposta: em vez de corrigir a documentação
  para dizer "pós-commit", `f754cde` moveu o código de volta para antes do commit e a documentação
  ficou certa.

A queda de 9,3% para 1,8% não é sinal de banco saudável: é o retrato de um delta que entregou
funcionalidade nova em `app/` sem passar perto dos 109 itens abertos. **Dez fingerprints abertos
mediram pior que no registro** e quatro precisam de re-ancoragem de arquivo (a tabela está em
`00-guardiao-verificacao.md`); o pior é `CLAUDE.md`, de 426 → 602 → **647** linhas, a 53 linhas do
ponto em que `helpers/size-limits.sh` deixa de avisar e passa a falhar.

Um achado aberto **mudou de forma e piorou**:
`docs-sync-claude-md-102-states-skill-desc-strict-false-…` (HIGH, o mais antigo em aberto) era uma
contradição entre dois valores; hoje `SKILL_DESC_STRICT` **não existe mais** em
`helpers/agent-lint.sh`, e sobraram três arquivos citando o knob removido — dois deles discordando
entre si sobre o valor dele.

## Achados originais por eixo

| Eixo | Originais | Nota |
|---|---|---|
| A — Agnosticismo de stack | **0** | 124 hits → 23 candidatos → 0 violações. Terceiro pass seguido em zero. |
| B — Referências e consistência | **0** | 6 candidatos, todos nas portas 3 ou 5. Sete gates limpos. |
| C — Fluxos, comandos e automação | **2** | 1 MEDIUM-HIGH, 1 MEDIUM — ambos em `app/`/`.github/` |
| D — Agentes e skills | **0** | 2 candidatos, ambos já registrados |
| E — Economia de tokens | **1** | 1 MEDIUM-HIGH, quantificado por 9 dias de git |

**Total: 3 achados originais.**

### Tabela de severidade

| Severidade | N | Fingerprints |
|---|---|---|
| HIGH | 0 | — |
| MEDIUM-HIGH | 2 | `auto-ipc-trusted-sender-rule-has-no-gate-only-a-wiki-note-to-grep` · `token-wiki-retrieval-index-13-7kb-read-whole-by-18-agents-with-no-cap` |
| MEDIUM | 1 | `auto-stamp-code-signed-cjs-outside-every-js-gate-in-the-tree` |
| LOW-MEDIUM | 0 | — |
| LOW | 0 | — |

## Os três achados mais graves

1. **A regra de sender confiável para canais IPC é cumprida só por grep humano**
   (MEDIUM-HIGH, `app/src/main/security.ts`). As quatro casas de registro passam pelo
   `trustedHandler` hoje, mas nada no CI verifica: `05-app.sh` roda preflight, pin de node,
   contrato de scripts, `npm ci`, typecheck, lint, build e testes, e nenhum passo lê
   `ipcMain.handle`. O repositório sabe — escreveu
   `docs/wiki/electron/ipc-channels-need-the-trusted-sender-check.md`, cuja origem é literalmente
   "a rebased app branch added IPC channels that passed linting and tests without the security
   check; found by grep only", e cuja seção *Gotchas* é um recado para rodar o grep à mão depois
   de cada rebase. Pela ENFORCEMENT POLICY de `01-lint.sh:11-13` o check qualifica como
   `blocking` hoje: determinístico, zero violações, violação é bug de correção.

2. **O índice do wiki cresceu 7,8× em 9 dias, é lido por inteiro por 18 agentes e não tem teto**
   (MEDIUM-HIGH, `skills/shared/project-context/SKILL.md`). 13.715 bytes / 51 linhas no `HEAD`,
   contra 1.757 / 6 em 2026-09-27. A skill manda *grepar* em `:114` e *ler* em `:151`, e é `:151`
   que justifica o desenho com "context cost stays flat as the wiki grows" — verdade sob a
   primeira leitura, falsa sob a segunda, que custa ~3.430 tokens por spawn e ~24.000 num
   `/devteam:fullstack`. Para o outro índice sempre carregado o repositório já resolveu isso
   (`SKILL_DESC_LIMIT=95` em `agent-lint.sh:92`); aqui `wiki-format.md:118` proíbe até contar as
   entradas.

3. **`stamp-code-signed.cjs` fica fora de todos os gates de JS** (MEDIUM,
   `.github/scripts/release/stamp-code-signed.cjs`). É o único arquivo JS/TS da árvore sem gate
   algum — `eslint .` roda com `cwd = app/`, `SHELLCHECK_TARGETS` só vê `*.sh`, `03-python.sh` só
   vê python — e é executado duas vezes num release (`release.yml:768` e `:835`) para reescrever
   `app/src/main/build-info.ts` ancorado numa linha literal. Os dois renderizadores python do
   mesmo diretório ganharam `tests/test_release_render.py` exatamente por esse motivo
   ("without these tests the first execution would be a real tag"); o `.cjs` vizinho não ganhou nem
   `node --check`.

## Descartados por duplicação

**33 candidatos avaliados · 3 sobreviveram · 30 descartados.**

| Eixo | Candidatos | Porta 1 | Porta 3 | Porta 5 | Regra do eixo / ruído | Mérito | Sobreviveram |
|---|---|---|---|---|---|---|---|
| A | 23 | 0 | 4 | 6 | 13 | 0 | 0 |
| B | 6 | 0 | 2 | 4 | 0 | 0 | 0 |
| C | 3 | 0 | 0 | 1 | 0 | 0 | 2 |
| D | 2 | 1 | 0 | 0 | 0 | 1 | 0 |
| E | 2 | 0 | 0 | 1 | 0 | 0 | 1 |

A lista nominal, com porta e razão, está ao fim de cada relatório de eixo. Três descartes de tipo
distinto ficam registrados aqui:

- **Um gate que valide o índice do wiki contra as entradas em disco caiu na Porta 3** contra
  `auto-no-gate-validates-claude-md-file-structure-tree-against-real-tree-four-recurrences-each-discarded-as-duplicate`
  — mesma causa raiz (invariante 1:1 documentada sem verificação), mesma remediação. É o descarte
  mais doloroso do pass: a árvore está limpa hoje (51 entradas, 51 linhas, zero órfãs nos dois
  sentidos), o que é exatamente a condição para um check `blocking`, e o delta adicionou 12
  entradas em um dia. Fica aqui para que a execução do fingerprint-pai cubra o wiki no mesmo
  helper.
- **A quinta recorrência da árvore de File Structure do `CLAUDE.md` caiu na Porta 5** —
  `.github/scripts/release/` enumera 1 de 5 arquivos, `scripts/lib/devteam/` 20 de ~44, e `infra/`
  não tem linha nenhuma apesar de emitir o entitlement assinado da ADR-0029. Registrar como achado
  novo é precisamente o que o fingerprint-pai existe para impedir.
- **Quatro hipóteses foram refutadas por evidência e estão registradas em
  `03-fluxos-e-comandos.md`** (quoting de `cmd.exe` com barra final, canal IPC novo sem guarda,
  ausência de verificação Authenticode no job Windows, `compileall` sem os dois módulos de
  `scripts/lib/`) — para que o próximo pass não gaste o mesmo tempo nelas.

## Saída dos gates

```
orphan-skill-scan            clean ✓   (falso negativo conhecido: cego à forma de diretório)
orphan-template-scan         clean ✓
agent-lint                   clean ✓
size-limits                  clean ✓   WARN: CLAUDE.md 647 linhas (aviso 600, falha 700)
check-fingerprint-uniqueness ✓ 287 slugs únicos em 1 arquivo de banco
preferences-sync-lint        clean ✓   (2 de 5 espelhos — fingerprint aberto)
archive-index --dry-run      nenhuma seção com > 90 dias (a mais antiga, 2026-07-30, tem 72)
```

## Relatórios

| Arquivo | Conteúdo |
|---|---|
| [00-guardiao-verificacao.md](00-guardiao-verificacao.md) | Fases 1 e 1b, item a item |
| [01-agnosticismo-de-stack.md](01-agnosticismo-de-stack.md) | Eixo A — varredura integral |
| [02-referencias-e-consistencia.md](02-referencias-e-consistencia.md) | Eixo B — gates e checagens mecânicas |
| [03-fluxos-e-comandos.md](03-fluxos-e-comandos.md) | Eixo C — 2 achados |
| [04-agentes-e-skills.md](04-agentes-e-skills.md) | Eixo D — medições |
| [05-economia-tokens.md](05-economia-tokens.md) | Eixo E — 1 achado |
