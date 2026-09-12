# Eixo B — Referências e consistência (2026-09-04)

**Data:** 2026-09-04 · **Baseline:** `HEAD` = `a67cac9`

---

## Saída dos gates

Os quatro helpers de autoria foram executados no `HEAD`:

| Helper | Saída | Leitura |
|---|---|---|
| `helpers/agent-lint.sh` | `agent-lint: clean ✓` | frontmatter, espelho `tiers.json` ↔ `model:` ↔ run-banner, identidade de skills, quiz-first e roster de comandos, todos íntegros |
| `helpers/orphan-template-scan.sh` | `orphan-template-scan: clean ✓` | todas as referências a templates resolvem |
| `helpers/orphan-skill-scan.sh` | `ACTION SUGGESTED` — 3 cargas duplicadas | **falsos positivos conhecidos**, ver abaixo |
| `helpers/size-limits.sh` | exit **1** — `⚠ CLAUDE.md: 602 lines (warning threshold: 600)` sob o cabeçalho `ERRORS` | reprodução de `auto-size-limits-claude-md-warning-counted-as-violation-turns-ci-lint-red` (**HIGH**, aberto) |

### Sobre as três "cargas duplicadas"

```
· agents/backend-test-specialist.md loads skills/testing/test-pyramid/SKILL.md more than once
· agents/frontend-test-specialist.md loads skills/testing/test-pyramid/SKILL.md more than once
· commands/merge.md loads skills/shared/worktree/SKILL.md more than once
```

O pass de 2026-08-21 já verificou os três: a segunda ocorrência em cada arquivo é **citação de
regra**, não um segundo `load`. A causa raiz — o scanner não distingue diretiva de carga de menção
narrativa — é exatamente o enunciado de
`ref-orphan-skill-scan-reports-design-system-audit-duplicate-load-in-ui-ux-designer-introduced-in-uknown-commit`
(✅ Executed). Novo candidato descartado pela **Porta 3**: alvo e causa raiz coincidem (2 de 3).

---

## Verificações de paridade documental

| Checagem | Resultado |
|---|---|
| Descrições de skill acima do orçamento de 95 caracteres | **0 de 152** — confirma a remediação de `token-sixteen-skill-descriptions-exceed-95-char-budget-…` |
| `commands/` vs. `scripts/lib/commands.json` | 35 arquivos, 35 linhas — paridade íntegra |
| Tabela de comandos do `README.md` vs. `commands/` | 34 de 35 — falta `/devteam:install`; **já no conjunto aberto**, descartado pela Porta 5 |
| `CLAUDE.md` § File Structure vs. `docs/` real | omite `harness.md`, `credentials.local.md`, `user-preferences.md`, `development/`, `prompts/`; **Porta 3** — alvo, causa raiz e remediação coincidem com a família `ref-claude-md-file-structure-*` (3 de 3), a mesma porta pela qual o pass de 2026-08-14 já descartou o caso `docs/prompts/` |

---

## MEDIUM

### O gate de paridade EN ↔ pt-BR descobre pares por um único sufixo e é cego ao par de métricas, que inverte a convenção

- **Fingerprint:** `ref-readme-sync-gate-discovers-only-pt-br-suffix-blind-to-inverted-en-suffix-pair`
- **Alvo:** `.github/scripts/ci/02-readme-sync.sh`
- **Refina:** `flow-readme-sync-ci-hardcodes-three-doc-pairs-no-glob-discovery-any-new-pt-br-translation-pair-silently-unchecked`
- **Evidência:**
  - `.github/scripts/ci/02-readme-sync.sh:192` — `done < <(find . -name '*.pt-BR.md' -not -path './.git/*' -not -path './node_modules/*' | sort)`
  - `:183` — `en="${ptbr%.pt-BR.md}.md"`
  - `:13-14` (comentário do próprio script) — "Pairs are DISCOVERED, not hardcoded: every `*.pt-BR.md` in the tree must have an EN counterpart"
  - Árvore real: `find . -name '*.en.md'` devolve **exatamente um** arquivo — `docs/reports/metrics-last-20-days.en.md`, 594 linhas, par de `docs/reports/metrics-last-20-days.md`, 594 linhas
  - Execução no `HEAD`: o gate imprime `OK` para **6** pares (`README`, `docs/agents`, `docs/credentials.local`, `docs/harness`, `docs/installation`, `docs/user-preferences`) e termina em `readme-sync OK ✓`. O sétimo par nunca aparece na saída.
- **Problema:** a descoberta é convencional, não semântica. Ela assume que toda tradução se expressa
  como `X.md` (EN) + `X.pt-BR.md` (pt-BR). O par de métricas inverte os dois papéis: o arquivo sem
  sufixo é o **português** e o inglês carrega `.en.md`. O `find` não casa `.en.md`, e o par escapa
  inteiro — nem como par verificado, nem como erro.
- **Por que importa:** são 1.188 linhas de documento traduzido, o segundo maior par do repositório
  depois de `README`, sob um gate que reporta `OK ✓` como se cobrisse tudo. O comentário em `:13-14`
  afirma "**every** `*.pt-BR.md` in the tree" — verdade literal que soa como cobertura total e não
  é. Um `FOUND=6` silencioso é pior que um hardcode de três pares: o hardcode ao menos era
  visivelmente parcial. A `README Sync Rule` do `CLAUDE.md:29` também nomeia só `README.pt-BR.md`,
  então nada — nem regra, nem gate — obriga o par de métricas a permanecer sincronizado.
- **Proposta:** normalizar a convenção. Renomear `metrics-last-20-days.md` → `metrics-last-20-days.en.md`
  não resolve (inverteria de novo); o caminho limpo é `metrics-last-20-days.md` (EN) +
  `metrics-last-20-days.pt-BR.md` (pt-BR), com os conteúdos trocados de arquivo — aí a descoberta
  atual passa a cobrir o par sem uma linha de código novo. Alternativa mínima se a nomenclatura
  precisar ficar: adicionar `*.en.md` ao `find` e derivar o par pelo lado inglês.
- **Impacto positivo:** o sétimo par entra no gate; `FOUND` passa de 6 para 7 e a afirmação de
  cobertura do script vira verdadeira. Uma única convenção de nomenclatura para traduções no repo.
- **Impacto negativo / risco:** a troca de nomes quebra qualquer link externo para
  `docs/reports/metrics-last-20-days.md` — e esse é o caminho que o prompt de métricas
  (`docs/prompts/posthog-metrics-report.md`) e o bloco de commit do `_prompt-auditoria.md`
  presumivelmente escrevem. Os dois prompts precisam ser atualizados no mesmo commit, senão a
  próxima geração de métricas recria o arquivo com o nome antigo e o repositório passa a ter três
  arquivos. Além disso, o par entra no gate **com dívida**: os dois arquivos foram gerados em
  2026-08-14 e podem já divergir estruturalmente, o que faria o CI ficar vermelho no commit da
  renomeação.
- **Esforço:** Baixo

---

## Nada mais neste eixo

Nenhum outro achado original. Com a árvore congelada em `a67cac9` desde 2026-08-21 e dois passes já
executados contra este mesmo sha, o Protocolo Anti-Duplicação absorveu todos os demais candidatos —
ver a seção "Descartados por duplicação" do `index.md`.
