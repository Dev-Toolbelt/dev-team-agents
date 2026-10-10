# Eixo E — Economia de Tokens — 2026-10-10

**Baseline:** `HEAD` = `349f18c` · **1 achado original** · 1 candidato descartado.

---

## MEDIUM-HIGH

### O índice de recuperação do wiki cresceu 7,8× em 9 dias, é lido por inteiro e não tem teto

- **Fingerprint:** `token-wiki-retrieval-index-13-7kb-read-whole-by-18-agents-with-no-cap`
- **Alvo:** `skills/shared/project-context/SKILL.md`
- **Evidência:**
  - `docs/wiki/README.md` — **66 linhas, 13.715 bytes, 51 linhas de índice** (`wc -lc`).
  - Carregado por `project-context`, que **todos os 18 agentes** carregam
    (`grep -rln 'project-context/SKILL.md' agents/ | wc -l` → 18).
  - **Duas instruções incompatíveis para o mesmo passo, no mesmo arquivo:**
    `project-context/SKILL.md:114` — "`docs/wiki/README.md` ← retrieval index; **grep it** for the
    task's keywords and open only the entries that match" — contra `:151` — "**read that index** —
    and only that index. Derive two or three keywords from the task … and match them against the
    **Keywords** column … Never load the wiki directory: the index exists precisely so that
    **context cost stays flat as the wiki grows**."
  - Sob a leitura de `:151`, o custo não é flat: é linear no número de entradas. Medido no git,
    byte a byte:

    | Data | Linhas de índice | Bytes |
    |---|---|---|
    | 2026-09-27 (`3b9ba317`, primeiro commit do arquivo) | 6 | 1.757 |
    | 2026-09-30 (`bb4a3454`) | 20 | 5.545 |
    | 2026-10-02 (`4bd1474a`, baseline anterior `5e338d9`) | 50 | 13.406 |
    | 2026-10-06 (`d8d0f612`, `HEAD`) | **51** | **13.715** |

    **7,8× em 9 dias**, ~269 bytes por linha, sem inflexão. Em 2026-10-02 foram 12 entradas em um
    dia.
  - **Não há teto, e a ausência é deliberada:**
    `skills/shared/docs-sync/references/wiki-format.md:99` pede que o arquivo "stay greppable and
    **small**" sem definir nenhum número, e `:118` fecha a porta para medi-lo —
    "**Entry counts are not tracked.** A count is a number to keep in sync that answers no question
    an agent has".
  - **O repositório já resolveu esse problema uma vez, para o outro índice sempre carregado.**
    `helpers/agent-lint.sh:90-92` — "Skill `description` feeds the always-loaded skill index across
    every skill in the repo, so it is the highest-leverage per-character cost in the tree" —
    `SKILL_DESC_LIMIT=95`, com gate. O índice do wiki tem a mesma propriedade e nenhum limite.
- **Problema:** ~13,7 KB (≈ 3.430 tokens) entram no contexto de cada spawn que carrega
  `project-context`, com crescimento linear e sem teto, e a skill diz ao mesmo tempo para *grepar*
  (custo das linhas que casam) e para *ler* (custo total). A justificativa escrita — "context cost
  stays flat as the wiki grows" — só é verdadeira na primeira leitura.
- **Por que importa:** `/devteam:fullstack` spawna 7 agentes; sob a leitura de `:151` são
  ~24.000 tokens só de índice de wiki por rodada, antes de qualquer entrada ser aberta. Na
  trajetória medida, o arquivo passa de 20 KB antes do fim do trimestre e ninguém tem um número
  para apontar quando isso acontecer — `wiki-format.md:118` proíbe exatamente o número que serviria
  de alarme. É o inverso da decisão tomada em `agent-lint.sh` para o índice de skills.
- **Proposta:** (1) resolver a contradição — `:151` passa a mandar `grep -i '<kw1>\|<kw2>' docs/wiki/README.md`
  e ler só as linhas que casam, que é o que `:114` já diz e o que torna o "flat" verdadeiro;
  (2) orçamento por linha no molde do `SKILL_DESC_LIMIT` (hoje a média é 269 bytes; 180 cabe), com
  gate em `helpers/` — o mesmo helper que o fingerprint-pai do Eixo B pede para a árvore de
  File Structure pode validar índice ↔ entradas e o orçamento na mesma passada;
  (3) remover de `wiki-format.md:118` a proibição de contar, que é a única frase que impede medir.
- **Impacto positivo:** sob a leitura por grep, o custo por spawn cai de ~3.430 tokens para as
  duas ou três linhas que casam — ~150 tokens, uma redução de ~95% num caminho que roda em 18
  agentes. O orçamento por linha corta ~30% do arquivo (269 → 180 bytes/linha) sem perder nenhuma
  entrada.
- **Impacto negativo / risco:** real e precisa ser dito. Grepar em vez de ler **perde recuperação
  por associação**: um agente que leu as 51 linhas pode reconhecer uma entrada relevante cujas
  palavras-chave ele não teria derivado da tarefa — e as entradas do wiki existem justamente para
  o que não é derivável. A perda é maior nas entradas com vocabulário distante da tarefa
  (`windows/nul-is-a-tty.md` ao depurar um `getpass` pendurado). Um orçamento por linha também
  empurra a coluna **Keywords** para a brevidade, e `wiki-format.md` exige que ela seja a `Tags`
  da entrada **verbatim** ("the two must not drift") — cortar a linha do índice obriga a cortar a
  `Tags` da entrada, em 51 arquivos, sem gate que confira a não-divergência. Isto é trabalho real,
  não cosmético.
- **Esforço:** Médio.

> **Por que MEDIUM-HIGH e não HIGH.** A rubrica reserva HIGH para quem "documenta como verdade algo
> factualmente falso", e `:151` faz isso ao pé da letra. Mas há uma leitura justa — "flat em
> relação ao conteúdo total do wiki, que não é carregado" — em que a frase é verdadeira, e sob
> `:114` o custo é de fato quase flat. O que é indiscutível é o risco de drift sem gate, que é a
> definição de MEDIUM-HIGH. Fica em MEDIUM-HIGH com o argumento de HIGH registrado aqui, para que
> quem executar decida com a informação na mão em vez de herdar a minha.

---

## Descartados por duplicação — 1

- **155 skills symlinkadas para `.claude/skills/`, 12,7 KB de `name:`+`description:` no índice
  sempre carregado.** É `token-151-skills-flat-symlinked-into-claude-skills-index-12751-chars-per-context`
  (MEDIUM-HIGH, aberto), registrado com 151 de 152; medi **155**. Porta 5 (estado), com re-medição
  anotada no banco.

## Fingerprints de token abertos re-medidos

Nenhum virou achado novo — todos pertencem ao conjunto aberto (Porta 5) — mas as medições do
registro estão defasadas e a re-ancoragem vai para o `_index.md`:

| Fingerprint | Registrado | `HEAD` |
|---|---|---|
| `token-claude-md-426-lines-still-monolithic-…` | 426 → 602 linhas | **647** (`size-limits.sh` já emite WARN; falha em 700) |
| `token-checks-list-loads-all-three-provider-blocks-…` | 668 linhas | **681** |
| `token-fix-patterns-517-lines-loaded-whole-…` | 517 linhas | **457** — mediu melhor |
| `token-151-skills-flat-symlinked-…` | 151 de 152 | **155** |

`CLAUDE.md` em 647 linhas merece destaque: está a 53 linhas do ponto em que
`helpers/size-limits.sh` passa de WARN a falha, e o fingerprint que propõe a extração dos três
blocos está aberto e **reaberto** desde 2026-09-18.
