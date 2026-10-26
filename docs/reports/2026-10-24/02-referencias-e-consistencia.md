# Eixo B — Referências e Consistência — 2026-10-24

**Baseline:** `HEAD` = `b64428b`. Prioridade de varredura: os 704 arquivos do delta
`bb0e883..b64428b`, com atenção às três superfícies novas (`commands/up.md`, `commands/down.md`,
`commands/insights.md`), às 7 ADRs novas (0038–0044) e às 13 skills de `skills/shared` tocadas.

## Helpers — saída integral

```
$ bash helpers/orphan-skill-scan.sh     → orphan-skill-scan: clean ✓      [exit 0]
$ bash helpers/orphan-template-scan.sh  → orphan-template-scan: clean ✓   [exit 0]
$ bash helpers/agent-lint.sh            → agent-lint: clean ✓             [exit 0]
$ bash helpers/size-limits.sh           → size-limits: clean ✓            [exit 0]
```

Os quatro passam limpos. `size-limits.sh` não emitiu nem o aviso de `CLAUDE.md`: 582 linhas no
`HEAD` contra o limiar de aviso de 600 (`helpers/size-limits.sh:86`).

## Checagens manuais que os helpers não cobrem

| Checagem | Resultado |
|---|---|
| `commands/*.md` ↔ chaves de `scripts/lib/commands.json` | **40 ↔ 40**, nenhuma sobra dos dois lados |
| Comandos ausentes de `README.md` / `README.pt-BR.md` | apenas `/devteam:install` — já registrado (`docs-sync-readme-command-table-omits-devteam-install-in-both-languages`) |
| `/devteam:up`, `/devteam:down`, `/devteam:insights` nas tabelas de docs | presentes: `CLAUDE-md/commands.md:47,48` (linhas próprias), `:62,64` (nota de "no agent"), `:58` (exceção de Plan Gate), e ambos os READMEs |
| ADRs 0038–0044 no índice `docs/development/adrs/README.md` | todas as 7 presentes |
| `name:` de skill == basename do diretório; unicidade entre categorias | coberto e aprovado por `helpers/agent-lint.sh:313-319` |
| Templates referenciados resolvem da raiz instalada | coberto e aprovado por `orphan-template-scan.sh` |
| Contagem "18 agentes" em README/README.pt-BR/docs/install-* | bate com a árvore (18) |
| `.worktrees/` rastreado por engano | não — `.gitignore:24`, 0 arquivos versionados |

Uma divergência real apareceu e é **nova**: a chave `interaction_mode`.

---

## MEDIUM-HIGH

### `interaction_mode` muda o corpo renderizado no Codex, não tem gate nem documentação fora do próprio JSON

- **Fingerprint:** `gov-interaction-mode-key-ungated-and-undocumented-outside-commands-json`
- **Alvo:** `scripts/lib/commands.json`
- **Evidência:**
  - `scripts/lib/render_provider.py:223-225` — `def codex_question_fallback_clause(interaction_mode): if interaction_mode == "required": …`, consumida por `codex_question_replacements` (`:240`) e `apply_codex_body_rewrites` (`:332`, default `"optional"`). O valor **reescreve o corpo** de todo comando no render do Codex.
  - `scripts/lib/commands.json` — `_interaction_mode_values` define o que cada valor *significa*, nunca **qual comando recebe qual**. Distribuição no `HEAD`: `required` 8 (`adr`, `architect`, `insights`, `plan`, `refactor`, `security`, `setup`, `spec`), `optional` 32, `none` 0.
  - `git grep -ln interaction_mode HEAD -- helpers/ .github/` → **nenhum resultado**. Os únicos leitores são `render_provider.py` e três arquivos de teste (`tests/test_planning_routing.py`, `tests/test_spec_gate.py`, `tests/test_structured_choice_render.py`), e nenhum deles valida o conjunto de valores nem a atribuição por comando.
  - `git grep -c interaction_mode HEAD -- CLAUDE.md CLAUDE-md/` → **0**. A chave não é mencionada em nenhum arquivo da árvore de documentação.
- **Problema:** a chave irmã `plan_gate` tem as duas defesas que esta não tem. Documentação:
  `CLAUDE-md/commands.md:58` nomeia a chave, lista os três valores e aponta o JSON como canônico.
  Gate: `helpers/agent-lint.sh:374` lê `plan_gate` do JSON e verifica os comandos marcados
  `required`/`conditional`. `interaction_mode` não tem nenhuma das duas, embora tenha o mesmo
  perfil de risco — um valor por comando, consumido no render, invisível na revisão do `.md`.
- **Por que importa:** 29 dos 40 comandos carregam no corpo a mesma linha obrigatória —
  "use `AskUserQuestion` for every question with a finite set of answers — never a plain-text
  prompt" — e ainda assim recebem `optional`, enquanto 8 recebem `required`. Pela definição em
  `_interaction_mode_values`, a diferença é concreta no Codex: `required` roteia o usuário para
  `/plan` quando o chooser estruturado não está disponível na turn; `optional` degrada para uma
  lista numerada em conversa. Isso significa que `/devteam:merge`, `/devteam:commit` e
  `/devteam:review` — que perguntam sobre rebase, teardown de worktree e descarte de trabalho —
  degradam para prosa, enquanto `/devteam:adr`, que pergunta um título, roteia para `/plan`. Pode
  ser deliberado; nada na árvore diz que é, e nada impede que um comando novo nasça com o valor
  errado. `commands/up.md` e `commands/down.md` entraram neste delta com `optional` e ninguém tinha
  um critério contra o qual conferir.
- **Proposta:** (1) acrescentar a `CLAUDE-md/commands.md`, ao lado da nota de Plan Gate em `:58`,
  um parágrafo "Exception — structured-choice mode" com o critério de atribuição em uma frase
  (p.ex. "`required` quando uma escolha errada é irreversível ou muda o plano; `optional` caso
  contrário") e o ponteiro para o JSON; (2) estender o bloco de `helpers/agent-lint.sh:374` para
  também falhar quando um comando não declara `interaction_mode` ou declara valor fora de
  `{required, optional, none}`.
- **Impacto positivo:** fecha a última chave de `commands.json` com efeito de render que ainda
  não tem gate. O lint já roda em CI e no hook `Stop`, então o custo marginal é uma leitura de
  JSON que ele já faz — `agent-lint.sh:374` abre o mesmo arquivo. Pega o valor errado no commit em
  vez de no primeiro usuário de Codex que encontra o fallback trocado.
- **Impacto negativo / risco:** um gate de **presença** reprova de imediato qualquer comando sem a
  chave, então os 40 precisam estar completos antes do merge (hoje estão — mas é um acoplamento
  novo entre o lint e o JSON). Um gate de **critério** é impossível de automatizar: o lint só
  pode checar o conjunto de valores, e o parágrafo de critério continua sendo prosa que pode
  divergir da prática sem que nada perceba — a mesma classe de drift que este achado descreve,
  só que um nível acima. E documentar o critério convida a revisitar as 8 atribuições
  `required` atuais, o que é um trabalho de produto, não de lint.
- **Esforço:** Baixo

---

## Gates do banco (rodados após a atualização do `_index.md`)

```
$ bash helpers/check-fingerprint-uniqueness.sh
✓ All 299 fingerprint slugs are unique across 1 bank file(s).          [exit 0]

$ bash helpers/archive-index.sh --dry-run
✓ No entries older than 90 days (cutoff 2026-07-26) in docs/reports/_index.md.   [exit 0]
```

A rotação não precisa rodar: a seção mais antiga do banco é de 2026-07-30, quatro dias dentro da
janela de 90 dias. Ela cruza o corte em **2026-10-28**, e o `99b-archive-index.sh` no dispatcher
`Stop` deve disparar sozinho a partir daí — este é o primeiro pass em que o gate chega perto de
ter trabalho a fazer.
