# Eixo D — Agentes e Skills — 2026-10-10

**Baseline:** `HEAD` = `349f18c`

## Resultado

**Nenhum achado original neste eixo.** 2 candidatos, ambos já no banco.

## Medições

| Medida | `HEAD` | Limite | Fonte |
|---|---|---|---|
| Maior agente | 211 linhas (`software-architect`, `qa-specialist`, `devops-specialist`) | `AGENT_LIMIT=211` | `helpers/size-limits.sh:44` |
| Agentes a ≤ 3 linhas do teto | 6 de 18 | — | `wc -l agents/*.md` |
| Maior skill | 435 linhas (`skills/shared/migration-v1-to-v2`) | `SKILL_LIMIT=500` | `helpers/size-limits.sh:45` |
| Maior comando | — | `COMMAND_LIMIT=200` | `helpers/size-limits.sh:50` |
| Skills na árvore | 155 | — | `find skills -name SKILL.md` |
| Total de linhas em `skills/*/SKILL.md` | 18.364 | — | — |
| Skills > 250 linhas **sem** `references/` | 2 (`migration-v1-to-v2` 435, `architecture/orchestration` 399) | — | ambas registradas e abertas |
| `name:` ≠ basename do diretório | **0** de 155 | — | — |
| Nomes de skill duplicados entre categorias | **0** | — | — |

`helpers/agent-lint.sh` sai `clean ✓`: frontmatter, campos obrigatórios
(`REQUIRED_FIELDS=("name" "description" "tier" "model")`, `:20`), quiz-first e orçamento de
`description` (`SKILL_DESC_LIMIT=95`, `:92`).

## Candidatos descartados

### Porta 1 (literal) — 1

- **Três agentes exatamente no teto de 211, sem folga.** O histórico do teto é um high-water mark:
  `5b61720` (2026-05-13) criou `AGENT_LIMIT=200`; `d17d575` (2026-07-31) subiu para 205
  ("raise the agent line ceiling by the run-banner block size"); `705acd1` (mesmo dia) subiu para
  211. `CLAUDE.md:102` fecha a porta — "Do not raise that ceiling again to make a long agent fit"
  — mas a próxima linha adicionada a qualquer um dos três deixa o CI vermelho sem que ninguém
  tenha pedido um corte. Já registrado como
  `agent-three-at-exactly-211-line-ceiling-zero-headroom-for-additions` (LOW, aberto).

### Porta 3 (semântica) — 1

- **`skills/shared/project-context/references/wiki.md` como segunda casa do protocolo do wiki.**
  `CLAUDE.md:178` nomeia `skills/shared/docs-sync/references/wiki-format.md` como casa canônica do
  formato, e `project-context/SKILL.md:177` aponta para
  `project-context/references/wiki.md` como "full protocol". Lido: o segundo arquivo tem **9
  linhas** e é um ponteiro, não uma cópia — `wiki-format.md:153` declara explicitamente a divisão
  ("This is the wiki's **read** path. Writing entries is … wiki-format.md, which owns the index
  row format the lookup depends on"). Não há duplicação de regra; o candidato caiu por mérito, não
  por duplicata, e fica registrado aqui para que o próximo pass não releia os dois arquivos.

## Leitura do eixo

A família `agent-*`/`skill-*` tem 24 fingerprints abertos, nove deles MEDIUM-HIGH ou acima
(`agent-security-specialist-outside-review-result-set-…`,
`agent-review-agent-roster-hardcoded-in-five-places-…`,
`agent-frontend-test-specialist-sonarqube-…`, entre outros). As medições acima dizem que a árvore
está dentro dos limites que ela mesma declara; o que está fora é a execução do que já está
registrado. Varredura nova neste eixo tem retorno decrescente até esse estoque cair.
