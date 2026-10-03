# Auditoria Guardiã — 2026-10-02

**Data:** 2026-10-02 · **Baseline:** `HEAD` = `5e338d9` · **Baseline anterior:** `ef69da3`

> O repositório recebeu commits **durante** este pass: as Fases 1 e 1b foram verificadas contra
> `4db9ed2`, e os Eixos B–E contra `061eb85`→`5e338d9`. Nenhum achado deste pass depende do delta
> interno dessa janela — todos foram reconfirmados no `HEAD` registrado acima.

## Sumário executivo

**O achado principal deste pass é um canal de instalação inteiro quebrado no `HEAD`, com o CI
vermelho e ninguém avisado.**

`scripts/install-cli.sh` — o instalador macOS/Linux sem Homebrew, entregue pela ADR-0028 — aborta na
primeira linha de execução:

```
$ bash scripts/install-cli.sh --help
scripts/install-cli.sh: line 163: SOURCE: unbound variable
```

O commit `2b410af` ("fix(packaging): ship auth-config.json with every CLI distribution") colou 52
linhas de corpo **fora** de `main()`, usando variáveis maiúsculas que o refactor anterior já havia
transformado em locais. `bash -n` passa. `python3 -m unittest … test_install_cli.py` devolve
**8 falhas de 9 testes** — ou seja, o gate `.github/scripts/ci/03-python.sh` está vermelho neste
commit, e o merge entrou de todo jeito. De quebra, a cópia de `auth-config.json` que o commit
pretendia adicionar ficou dentro do bloco morto: mesmo que a instalação funcionasse, o CLI instalado
não teria o arquivo e `load_identity` levantaria `EnvError`.

Dois achados irmãos cercam a mesma área nova:

- `store install --from` numa árvore não stripada copia `scripts/lib/auth-config.dev.json` para o
  core, e o CLI do core — o que `ag_gate` e os hooks executam — passa a resolver o ambiente **`dev`**
  em máquina de usuário. Reproduzido: `devteam auth check --json` devolve `"environment": "dev"`.
  O scan de SR-27 só cobre o caminho `apply_strip`, então isso sai **verde** no CI.
- `release.yml` não tem gate nenhum contra os `REPLACE-ME` de `auth-config.json`. Uma tag publicada
  hoje distribui o CLI nos três canais com login impossível, e nada falha antes do cliente.

Em contraste, a saúde do **banco** é a melhor em três passes: **0 marcações 🔴**, num pass em que 25
dos 68 itens verificados tinham sido marcados nas últimas 48 horas. A integridade das marcações não é
o problema deste repositório hoje; o gate de release é.

---

## Método

| Fase | Método | Cobertura |
|---|---|---|
| 0 | `_index.md` lido, delta calculado desde `ef69da3` | 650 commits · 728 arquivos — **o maior delta da história do banco** |
| 1 | Reconstrução da remediação pelo git (janela da marca) + confirmação por símbolo no `HEAD` + checagem de reversão silenciosa | **68 de 133 (51%)** |
| 1b | Confirmação de que o alvo existe e o problema reproduz no `HEAD` | **97 de 97 (100%)** |
| 2 | Cinco eixos, Eixo A integral, demais priorizados pelo delta | 21 achados originais |

**Critério de amostragem da Fase 1** (o conjunto verificável excede 60 itens): todos os 41 HIGH e
MEDIUM-HIGH, mais amostra aleatória de 30% dos 92 restantes (28 itens), com semente fixa `20261002`
para reprodutibilidade.

---

## Fase 1 — Placar

| Marca verificada | Qtde | % |
|---|---|---|
| ✅ Feito | **64** | 94,1% |
| 🟡 Parcialmente feito | **4** | 5,9% |
| 🔴 Não feito | **0** | **0%** |

Limiar de escalonamento (15% de 🔴) **não atingido**. Histórico de reabertura: 10% (2026-07-31) → 0%
(2026-08-12) → 6,1% → 4,2% → 9,1% → 11,8% → 7,1% → 12,5% (2026-09-18) → **0% (hoje)**.

Os 4 🟡: `token-pre-tool-use-01-check-updates-forks-python3…` (a correção marcada foi **revertida**;
o sintoma morreu por outra via — deveria ser 🟢), `flow-merge-md-rebases-onto-target-while-delegating-to-base-step-8`
(mitigado no caso comum, sem mecanismo para o alvo explícito), `auto-update-no-integrity-check`
(integridade de transporte entregue, autenticidade não — o digest não é publicado e a verificação
falha aberta) e `ref-two-malformed-git-tags…` (⚠️ Partial honesta, mantida).

Detalhe item a item, com commit examinado e trecho citado: [`00-guardiao-verificacao.md`](00-guardiao-verificacao.md).

## Fase 1b — Mortalidade

| Veredito | Qtde | % |
|---|---|---|
| Ainda reproduz | 88 | 90,7% |
| 🟢 Resolved | **9** | **9,3%** |
| ⚰️ Obsoleto | 0 | 0% |

**Mortalidade de 9,3%** — a maior desde a consolidação (os seis passes anteriores ficaram entre 0% e
3,2%). Não é deterioração: é o efeito de 650 commits sobre um banco vivo. Oito achados abertos
mediram **pior** do que no registro, dois mediram melhor, e dois mudaram de arquivo e precisam de
re-ancoragem.

---

## Achados originais por eixo

| Eixo | Originais | HIGH | MED-HIGH | MEDIUM | LOW-MED | LOW |
|---|---|---|---|---|---|---|
| A — Agnosticismo de stack (integral) | **0** | — | — | — | — | — |
| B — Referências e consistência | 5 | 1 | 2 | 0 | 2 | 0 |
| C — Fluxos, comandos e automação | 7 | 2 | 1 | 3 | 1 | 0 |
| D — Agentes e skills | 3 | 0 | 1 | 2 | 0 | 0 |
| E — Economia de tokens | 6 | 0 | 1 | 4 | 1 | 0 |
| **Total** | **21** | **3** | **5** | **9** | **4** | **0** |

**O Eixo A rendeu zero, e isso é informação, não omissão.** A varredura semente integral deu 124
linhas de hit → 23 candidatos agrupados por alvo+causa → **0 violações originais**: dezessete dos 23
são itens do banco que seguem **abertos**. O eixo não tem mais o que descobrir em `agents/` e
`commands/`; tem o que executar.

---

## Tabela de severidade

### HIGH (3)

| Fingerprint | Alvo | Uma linha |
|---|---|---|
| `flow-install-cli-orphan-body-outside-main-aborts-every-run` | `scripts/install-cli.sh` | 52 linhas de corpo órfão fora de `main()` matam o script com `SOURCE: unbound variable`; 8 de 9 testes vermelhos |
| `flow-store-install-ships-dev-auth-config-into-core-despite-sr-27` | `packaging/windows-cli/build.py`, `scripts/install-cli.sh`, `store.py` | o CLI do core resolve ambiente `dev` em máquina de usuário; o scan de SR-27 não cobre esses canais |
| `docs-sync-user-data-keep-root-omits-plugins-and-names-wrong-repo-only-skill` | `CLAUDE-md/user-data.md` | três afirmações falsas num parágrafo: `KEEP_ROOT` sem `plugins`, `release-prep` dado como repo-only, 4 exclusões ausentes |

### MEDIUM-HIGH (5)

| Fingerprint | Alvo | Uma linha |
|---|---|---|
| `ref-relayout-quality-skills-list-cites-seven-nonexistent-shared-paths` | `commands/relayout.md` | o passo de qualidade obrigatório aponta 7 de 8 skills para caminhos inexistentes, desde 2026-08-09 |
| `ref-orphan-skill-scan-blind-to-directory-form-skill-refs` | `helpers/orphan-skill-scan.sh` | o gate só valida referências terminadas em `/SKILL.md`, e por isso imprimiu `clean ✓` sobre as 7 acima |
| `auto-release-workflow-has-no-guard-for-auth-config-placeholders` | `.github/workflows/release.yml` | nenhum job verifica os `REPLACE-ME` de produção nem reporta `gate_mode` |
| `agent-security-specialist-outside-review-result-set-task-board-blind-to-findings` | `agents/security-specialist.md` | revisor spawnado sempre, fora das quatro listas e sem marcador: achado de segurança desaparece do quadro |
| `token-pretooluse-04-task-board-13-forks-before-marker-exit-every-tool-call` | `scripts/hooks/pre-tool-use/04-task-board.sh` | 13 forks e 31 ms antes do único teste que dá saída, em toda chamada de ferramenta (9–30 s/sessão) |

### MEDIUM (9)

| Fingerprint | Alvo |
|---|---|
| `flow-install-provider-gate-fallback-fails-open-without-gate-lib` | `scripts/install-provider.sh` |
| `flow-02c-double-dash-counted-as-scope-lets-npm-full-suite-through` | `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` |
| `auto-review-agents-regex-duplicated-in-two-task-board-hooks-no-drift-gate` | hooks de task board |
| `agent-review-agent-roster-hardcoded-in-five-places-no-canonical-home` | 5 arquivos, 4 linguagens |
| `agent-no-claude-attribution-restated-in-five-agents-frontend-dev-has-no-commit-rule` | 6 agentes |
| `token-python-sh-uname-forked-twice-per-source-uncached-on-linux-macos` | `scripts/lib/python.sh` |
| `token-hook-dispatchers-basename-dirname-forks-per-subscript-iteration` | 4 dispatchers |
| `token-plan-mode-execution-strategy-gate-duplicates-orchestration-loaded-by-26` | `skills/shared/plan-mode/SKILL.md` |
| `token-pretooluse-02c-sed-tr-head-forks-before-runner-gate-on-every-bash-call` | `02c-full-suite-guard.sh` |

### LOW-MEDIUM (4)

| Fingerprint | Alvo |
|---|---|
| `docs-sync-preferences-sync-lint-two-of-five-mirrors-key-presence-only` | `helpers/preferences-sync-lint.sh` |
| `ref-hooks-md-library-rows-omit-data-dirs-sh-sourced-by-ten-scripts` | `CLAUDE-md/hooks.md` |
| `flow-update-md-v3-step-0-drops-documented-health-check-and-yes-flags` | `commands/update.md` |
| `token-02b-telemetry-resolves-state-for-every-bash-call-needs-devteam-substring` | `02b-telemetry.sh` |

### LOW (0)

nenhum achado original nesta severidade

---

## Os 3 achados mais graves

1. **`flow-install-cli-orphan-body-outside-main-aborts-every-run`** — o canal de instalação
   macOS/Linux sem Homebrew está 100% quebrado no `HEAD`, com oito testes vermelhos no CI, e a
   correção que o commit queria entregar (copiar `auth-config.json`) nunca roda.
2. **`flow-store-install-ships-dev-auth-config-into-core-despite-sr-27`** — o CLI do core passa a
   apontar para o ambiente `dev` em máquina de usuário, contrariando uma garantia documentada, e o
   gate de SR-27 sai verde porque só inspeciona um dos três canais.
3. **`ref-orphan-skill-scan-blind-to-directory-form-skill-refs`** — o gate que deveria pegar
   referência de skill quebrada só vê metade das formas em que elas aparecem. Foi o que deixou
   `commands/relayout.md:35` com 7 caminhos mortos por 54 dias, três auditorias e centenas de hooks
   `Stop`, sempre reportando `clean ✓`. É o achado com maior alcance futuro: todo outro gate deste
   repositório é tão confiável quanto a forma que ele consegue enxergar.

---

## Gates executados

| Gate | Saída |
|---|---|
| `helpers/orphan-skill-scan.sh` | `clean ✓` — **falso negativo**, ver achado MEDIUM-HIGH |
| `helpers/orphan-template-scan.sh` | `clean ✓` |
| `helpers/agent-lint.sh` | `clean ✓` — tier/`model:`/run-banner coerentes com `tiers.json`; `## Before You Finish` presente e último em todos os 18 agentes |
| `helpers/size-limits.sh` | `⚠ CLAUDE.md: 647 lines` (aviso não bloqueante) · `clean ✓` |
| `helpers/preferences-sync-lint.sh` | "2 mirrors checked" — ver achado LOW-MEDIUM |
| `helpers/plugin-lint.sh` | limpo |
| `helpers/check-fingerprint-uniqueness.sh` | 266 slugs, todos únicos |
| `.github/scripts/ci/02-readme-sync.sh` | `readme-sync OK ✓` |
| `python3 -m unittest … test_install_cli.py` | **FAILED (failures=8) de 9** |

---

## Descartados por duplicação

**56 candidatos** descartados pelas cinco portas do Protocolo Anti-Duplicação:

| Eixo | Descartados | Porta dominante |
|---|---|---|
| A | 30 | porta 5 (item aberto no banco) e exceção de seção |
| B | 6 | portas 1, 3 e 5 |
| C | 5 | portas 1 e 3 |
| D | 6 | portas 1, 2, 3 e 5 |
| E | 9 | portas 1, 3, 4 e 5 |

A lista nominal, com a porta e a razão de cada descarte, está ao final de cada relatório de eixo.
Dois descartes merecem destaque porque mostram o filtro funcionando nos dois sentidos:
`agent-cloudflare-api-skill-unreachable` caiu na **porta 2** por ser falso positivo do próprio
auditor (a skill é carregada por três agentes), e `99b-archive-index sem fast-path` caiu na
**porta 3** contra a lista de hipóteses já refutadas por evidência — exatamente o que a seção de
descartes existe para impedir que o próximo pass redescubra.

---

## Relatórios deste pass

| Arquivo | Conteúdo |
|---|---|
| [`00-guardiao-verificacao.md`](00-guardiao-verificacao.md) | Fases 1 e 1b, item a item |
| [`01-agnosticismo-de-stack.md`](01-agnosticismo-de-stack.md) | Eixo A — varredura integral |
| [`02-referencias-e-consistencia.md`](02-referencias-e-consistencia.md) | Eixo B |
| [`03-fluxos-e-comandos.md`](03-fluxos-e-comandos.md) | Eixo C |
| [`04-agentes-e-skills.md`](04-agentes-e-skills.md) | Eixo D |
| [`05-economia-tokens.md`](05-economia-tokens.md) | Eixo E |
