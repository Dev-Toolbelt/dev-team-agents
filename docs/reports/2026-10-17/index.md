# Auditoria Guardiã — 2026-10-17

**Data:** 2026-10-17 · **Baseline:** `HEAD` = `bb0e883` · **Baseline anterior:** `349f18c`

> **O baseline foi re-fixado no meio do pass.** A Fase 0 fixou `78c11a6`. Enquanto as Fases 0 e 1
> corriam, **46 commits e 111 arquivos** entraram no repositório — o working tree de 30 arquivos
> modificados foi commitado e o trabalho de spec/sprint/reuse-lint chegou em bloco. Como esse
> material toca `agents/`, `commands/` e `skills/shared/`, exatamente onde a Fase 1 confirma, o
> baseline foi re-fixado em `bb0e883` e **todas as confirmações no `HEAD` foram refeitas contra
> ele**. O relógio UTC virou para 2026-10-18 durante o pass; `DATA` permanece 2026-10-17, que é a
> data fixada na Fase 0 e a data de todos os 76 commits do delta.

> **Plan Gate.** Pass disparado por tarefa agendada com instrução explícita de executar e
> commitar. Não houve aprovação humana do plano; o critério de amostragem da Fase 1 está
> declarado em [`00-guardiao-verificacao.md`](00-guardiao-verificacao.md) **antes** dos
> resultados, que é a garantia que o gate existe para dar.

## Sumário executivo

**O delta mais substantivo em `skills/shared` e `commands/` desde a consolidação — 76 commits,
157 arquivos, duas skills novas de fluxo, dois comandos novos, um hook de `Stop` novo — não
fechou um único dos 111 achados abertos, e piorou a medida de cinco deles.**

A Fase 1 saiu limpa: **0 reaberturas em 71 itens verificados**, o segundo melhor placar do banco.
A Fase 1b saiu em **0% de mortalidade sobre 111 de 111** — e esse zero não é imobilidade, como
nos passes de agosto e setembro: onze alvos abertos *foram* tocados por este delta e os onze
seguem reproduzindo. O trabalho novo passou ao lado do que está registrado.

Os sete achados originais vêm todos do material novo, e três deles têm a mesma forma: **uma
biblioteca nova (`scripts/hooks/lib/warn-once.sh`) ganhou três consumidores e só um aplica o
protocolo inteiro** — `03c-reuse-lint.sh` inclui a raiz do worktree na assinatura e reseta o
marcador quando a condição some; `03f-spec-lint.sh` não faz nem um nem outro, e
`CLAUDE-md/hooks.md` descreve o fan-in da biblioteca de duas formas contraditórias no mesmo
arquivo. O quarto padrão é de cobertura: a camada de spec aceita `database` em `touches` e não
tem autor de teste para ele em lugar nenhum, o que produz um WARN de `spec-lint` que o fluxo não
tem como limpar.

**Nota de método que vale para o próximo pass:** o campo `alvo:` do banco nomeia o arquivo que
*descreve* o problema, não o que é *corrigido*. Aplicar a regra "nenhum commit na janela tocou o
alvo ⇒ 🔴 por construção" contra esse campo teria produzido **8 falsos 🔴 de 71 (11,3%)**, perto
do limiar de escalonamento de 15%. Valide a janela contra o alvo da remediação.

## Cobertura e placar

| Fase | Cobertura | Resultado |
|---|---|---|
| **Fase 1** (verificação guardiã) | **71 de 142 (50%)** — todos os 41 HIGH/MEDIUM-HIGH + 30% aleatório (`seed=20261017`) dos 101 restantes | **66 ✅ · 5 🟡 · 0 🔴** — 93,0% confirmado, **0% reaberto** |
| **Fase 1b** (validade dos abertos) | **111 de 111 (100%)** — 11 com alvo no delta verificados à mão, 100 com alvo intocado desde o registro | **0 🟢 · 0 ⚰️ — mortalidade 0%** |

As 5 🟡 são reconfirmações, nenhuma nova. O limiar de escalonamento (15% da amostra em 🔴) não
foi atingido.

## Achados originais por eixo

| Eixo | Originais | Nota |
|---|---|---|
| **A** — Agnosticismo de stack | **0** | 125 hits → 2 candidatos novos → 0 violações. Terceiro pass consecutivo em zero. Os dois comandos novos (160 linhas somadas) não produzem um único hit |
| **B** — Referências e consistência | **2** | 1 MEDIUM-HIGH, 1 MEDIUM |
| **C** — Fluxos, comandos e automação | **3** | 1 MEDIUM-HIGH, 1 MEDIUM, 1 LOW-MEDIUM |
| **D** — Agentes e skills | **1** | 1 MEDIUM-HIGH |
| **E** — Economia de tokens | **1** | 1 MEDIUM |
| **Total** | **7** | |

## Tabela de severidade

| Severidade | N | Fingerprints |
|---|---|---|
| HIGH | 0 | — |
| MEDIUM-HIGH | 3 | `docs-sync-preferences-retire-checklist-restates-mirror-list-omits-docs-pair-and-invents-readme-row` · `auto-03f-spec-lint-warn-signature-omits-worktree-root-silences-sibling-worktrees` · `skill-spec-gate-touches-accepts-database-layer-with-no-test-author-in-any-track` |
| MEDIUM | 3 | `docs-sync-hooks-md-warn-once-library-row-omits-03f-spec-lint-contradicting-line-41` · `auto-warn-once-reset-never-called-by-03e-and-03f-cleared-warning-never-returns` · `token-spec-gate-17kb-loaded-whole-by-six-execution-agents-that-scope-two-sections` |
| LOW-MEDIUM | 1 | `flow-spec-command-step6-item5-inlined-into-item4-breaking-its-own-cross-reference` |
| LOW | 0 | — |

## Os três achados mais graves

1. **`auto-03f-spec-lint-warn-signature-omits-worktree-root-silences-sibling-worktrees`** —
   `03f-spec-lint.sh:58` assina o aviso só com a saída do lint, que é relativa à raiz
   (`spec_lint.py:43`), enquanto o marcador vive no state dir do checkout principal
   (`warn-once.sh:24`) e é compartilhado por todos os worktrees. O irmão `03c-reuse-lint.sh:52-56`
   inclui `$REPO_ROOT` na assinatura com um comentário explicando exatamente este risco. Numa
   onda de `/devteam:sprint` — um worktree por tarefa, em paralelo, todos com o mesmo
   `docs/specs/` — o WARN chega a uma tarefa e é silenciado nas outras.
2. **`skill-spec-gate-touches-accepts-database-layer-with-no-test-author-in-any-track`** —
   `touches` aceita quatro layers (`spec_lint.py:21` os valida como ERROR fora da tupla) e as
   três listas de autor de teste (`spec-gate:126,132`, `commands/spec.md:44`) cobrem três.
   Uma spec `touches: [database]` que chegue a `implemented` dispara o WARN de `check_coverage`
   (`spec_lint.py:282-293`) a cada `Stop`, sobre uma lacuna que nenhum agente tem mandato para
   fechar.
3. **`docs-sync-preferences-retire-checklist-restates-mirror-list-omits-docs-pair-and-invents-readme-row`** —
   `CLAUDE-md/preferences.md:42` manda remover a chave "de todos os espelhos listados em CLAUDE.md
   § User Preferences" e em seguida reescreve a lista errada nos dois sentidos: omite
   `docs/user-preferences{,.pt-BR}.md`, que são espelhos reais (`CLAUDE.md:395`), e inventa uma
   "`README.md` worktree table", que não existe em nenhum dos dois READMEs
   (`grep worktree_active README*.md` → vazio).

## Descartados por duplicação

Onze candidatos avaliados e rejeitados, com a porta que os barrou. A lista existe para que o
próximo pass não redescubra os mesmos becos.

| Candidato | Porta | Contra |
|---|---|---|
| `commands/mobile.md:12` repete o roteamento de autor de teste de `:28-29` | **3** (arquivo + remediação) | `flow-mobile-command-spawn-line-enumerates-stacks-dropped-from-agent-description` |
| `stop.sh:39` e `CLAUDE-md/hooks.md:115` dizem que `touched-paths.sh` é consumido por "02/02b/03/03b" quando são **6** sub-scripts (entraram `03e` e `03f`) | **3** (causa raiz + remediação) | `docs-sync-touched-paths-lib-header-says-stop-only-after-02c-sources-it` — anotado como re-ancoragem: a lista obsoleta está agora em três lugares |
| Tabela de package exclusions sem linha para `AGENTS.md`, `TERMS.md`, `scripts/install-cli.sh`, `scripts/lib/auth-config.dev.json` e a poda de `__pycache__` | **5** (conjunto aberto) | `docs-sync-user-data-keep-root-omits-plugins-and-names-wrong-repo-only-skill` — mediu pior: 5 regras de `strip-tarball.sh:24-33` sem linha, contra 4 no registro |
| `interaction-patterns` 323 linhas / 14.750 B carregada por 34 comandos | **5** | `token-interaction-patterns-209-lines-loaded-unconditionally-by-24-commands-…` — mediu pior em ambos os eixos |
| Execution Strategy Gate agora em quatro lugares (`orchestration`, `plan-mode:151-206`, `interaction-patterns:180`, ressalva em `commands/sprint.md:45`) | **5** | `token-plan-mode-execution-strategy-gate-duplicates-orchestration-loaded-by-26` |
| `CLAUDE.md` em 678 linhas, 22 do teto de falha | **5** | `token-claude-md-426-lines-still-monolithic-…` |
| `checks-list.md` em 715 linhas | **5** | `token-checks-list-loads-all-three-provider-blocks-after-step-0-resolved-one` |
| `docs/wiki/README.md` em 15.233 B / 71 linhas, +11% em 7 dias | **5** | `token-wiki-retrieval-index-13-7kb-read-whole-by-18-agents-with-no-cap` |
| `data-dirs.sh` segue como a única lib sem linha em `hooks.md`, agora com 11 arquivos e fan-in 12 | **5** | `ref-hooks-md-library-rows-omit-data-dirs-sh-sourced-by-ten-scripts` |
| `CLAUDE-md/commands.md:59` "All seven" contra `commands.json:_filler_agent_note` "all nine" | **5** | `flow-claude-md-no-agent-command-list-says-seven-omits-push-and-merge` |
| Os 23 candidatos do Eixo A triados nos passes de 2026-10-02 e 2026-10-10 | **5** | já no conjunto aberto; evidência inalterada |

Fora do protocolo anti-duplicação, dois candidatos caíram na triagem do próprio eixo e estão
documentados onde foram levantados: `commands/audit.md:65` ("`AWS access key at config/x.py:12`")
como Example no Eixo A, e o guard `[ -d docs/specs ]` de `spec-lint.sh:12` / `03f:16` no Eixo C —
este último analisado e **não** promovido, porque o caso que o lint perderia já é checado pelo
pré-flight de `commands/sprint.md:31`.

## Gates

```
helpers/check-fingerprint-uniqueness.sh → ✓ All 290 fingerprint slugs are unique across 1 bank file(s).
helpers/archive-index.sh --dry-run      → ✓ No entries older than 90 days (cutoff 2026-07-20).
helpers/agent-lint.sh                   → clean ✓
helpers/orphan-skill-scan.sh            → clean ✓
helpers/orphan-template-scan.sh         → clean ✓
helpers/size-limits.sh                  → clean ✓ (WARN: CLAUDE.md 678 linhas, teto de aviso 600)
```

Nenhuma seção do banco tem mais de 90 dias, então `archive-index.sh` não foi executado sem
`--dry-run`.

## Relatórios

| Arquivo | Conteúdo |
|---|---|
| [`00-guardiao-verificacao.md`](00-guardiao-verificacao.md) | Fases 1 e 1b, item a item |
| [`01-agnosticismo-de-stack.md`](01-agnosticismo-de-stack.md) | Eixo A — 0 achados |
| [`02-referencias-e-consistencia.md`](02-referencias-e-consistencia.md) | Eixo B — 2 achados |
| [`03-fluxos-e-comandos.md`](03-fluxos-e-comandos.md) | Eixo C — 3 achados |
| [`04-agentes-e-skills.md`](04-agentes-e-skills.md) | Eixo D — 1 achado |
| [`05-economia-tokens.md`](05-economia-tokens.md) | Eixo E — 1 achado |
