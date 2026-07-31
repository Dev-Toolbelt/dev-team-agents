# Eixo E — Economia de Tokens

**Data:** 2026-07-31 · **Baseline:** `f54569a`

---

## Mapa de custo agregado das skills `shared/`

Custo agregado = `nº de arquivos que carregam × linhas da skill`. Não é o custo de uma sessão — é a
superfície total de contexto que a skill representa no repositório.

| Skill | Loaders | Linhas | Agregado | Carga |
|---|---|---|---|---|
| `interaction-patterns` | **26** | 209 | **5.434** | incondicional |
| `project-context` | 17 | 309 | 5.253 | incondicional (é a regra fundacional) |
| `plan-mode` | 24 | 151 | 3.624 | incondicional |
| `token-efficiency` | 17 | 156 | 2.652 | incondicional |
| `current-context` | 20 | 105 | 2.100 | incondicional |
| `conventional-commits` | 11 | 140 | 1.540 | condicional |
| `comments-policy` | 15 | 102 | 1.530 | condicional |
| `output-format` | 8 | 190 | 1.520 | incondicional |
| `docs-sync` | 13 | 108 | 1.404 | incondicional |
| `worktree` | 11 | 108 | 1.188 | condicional |
| `model-identity` | 17 | 45 | 765 | incondicional |

`interaction-patterns` lidera, e é a única do topo cuja maior parte é material de referência e não
regra. `project-context` é grande por mandato do `CLAUDE.md`; `plan-mode` já foi reduzida de 199
para 151 nesta janela extraindo o formato para o template.

---

## MEDIUM-HIGH

### 76% de `interaction-patterns` é catálogo de exemplos, e os 24 comandos a carregam inteira na primeira linha

- **Fingerprint:** `token-interaction-patterns-209-lines-loaded-unconditionally-by-24-commands-and-2-agents-while-only-38-lines-are-the-rule-and-159-are-json-examples-and-recurring-patterns`
- **Alvo:** `skills/shared/interaction-patterns/SKILL.md`
- **Evidência:**
  Estrutura medida por seção:
  `## Core Rule` (`:8`) — 15 linhas · `## "Other" Option Rule` (`:24`) — 13 · `## Language Rule`
  (`:38`) — 10 · `## AskUserQuestion JSON Patterns` (`:49`) — **60** · `## Common Recurring
  Patterns` (`:110`) — **99**.
  Regra normativa = 38 linhas (`:8-48`). Material de referência = 159 linhas (`:49-209`), **76%**
  do arquivo.
  Carregadores: 26 — `grep -rl 'shared/interaction-patterns/SKILL.md' agents/ commands/` → 24
  comandos + 2 agentes. Nos 24 comandos a carga é **incondicional e está na primeira linha**, por
  exemplo `commands/backend.md:1` — "Load `skills/shared/interaction-patterns/SKILL.md` and use
  `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt."
- **Problema:** a frase de carga já contém a regra inteira. Os 209 linhas são abertos para reafirmar
  o que a linha de invocação diz, mais 159 linhas de payloads JSON de exemplo e padrões recorrentes
  que só importam no momento de **escrever** uma pergunta — não em toda invocação de comando.
- **Por que importa, quantificado:**
  - Agregado atual: 26 × 209 = **5.434** linhas. Após extrair `:49-209` para
    `references/askuserquestion-patterns.md`: 26 × ~50 = **1.300**. Economia agregada ≈ **4.130
    linhas (76%)**.
  - Por sessão, que é o número que o usuário sente: um fluxo típico `/devteam:backend` carrega o
    comando + 3 a 5 agentes. Hoje isso são de 2 a 3 cópias de 209 linhas (comando + agentes que
    também a carregam) ≈ **418-627 linhas**; após a extração ≈ **100-150**. Em `/devteam:fullstack`,
    que envolve 6 agentes e o comando, a diferença é maior.
  - Os fluxos onde incide são **todos os 24 comandos** — ou seja, toda invocação `/devteam:*` do
    produto.
- **Proposta:** manter em `SKILL.md` as três seções normativas (`Core Rule`, `"Other" Option Rule`,
  `Language Rule` — 38 linhas) e mover `## AskUserQuestion JSON Patterns` e `## Common Recurring
  Patterns` para `references/askuserquestion-patterns.md`, com uma linha de roteamento no fim do
  `SKILL.md`: "ao montar uma chamada `AskUserQuestion`, leia `references/askuserquestion-patterns.md`".
  É exatamente o padrão que `skills/integrations/gotrue/` adotou nesta janela (225 → 73 linhas).
- **Impacto positivo:** ~4.130 linhas de superfície de contexto agregada removidas — a maior
  economia isolada disponível no repo hoje; incide em 100% dos comandos. `interaction-patterns` sai
  da lista de skills > 200 linhas sem `references/`.
- **Impacto negativo / risco:** concreto e vale nomear. A Quiz-first Rule é a regra que o
  `agent-lint.sh` **bloqueia** — um agente que erra o formato do `AskUserQuestion` falha o CI. Hoje
  os payloads de exemplo estão à mão no mesmo arquivo; depois da extração o agente precisa decidir
  carregar um segundo arquivo no momento certo, e um agente que não carregue vai improvisar o JSON.
  A mitigação é a linha de roteamento ser imperativa ("leia antes de montar a chamada"), não
  sugestiva — e mesmo assim resta risco de queda de qualidade nos payloads. Vale medir: se o
  `agent-lint` começar a pegar violações de quiz-first após a mudança, a extração foi longe demais.
- **Esforço:** Baixo

---

## Nenhum achado original nos demais sub-eixos

- **Leitura de arquivo inteiro onde `grep`/`head` bastaria:** o alvo histórico era o passo de
  deduplicação lendo o `_index.md` inteiro. Resolvido — o banco caiu de ~850 para 250 linhas e o
  passo virou grep dirigido (`docs/reports/_prompt-auditoria.md:195,201`), verificado ✅ na Fase 1.
- **Output verboso de comando:** os quatro helpers e os dois dispatchers aceitam `--quiet` e são
  silenciosos em sucesso — verificado rodando os seis, todos emitem uma linha ou nenhuma.
- **Conteúdo duplicado lido duas vezes:** os candidatos vivos (`project-context` § Docker,
  bloco de detecção SonarQube em 11 agentes, `conventional-commits` eager em três reviewers) já
  estão registrados no banco e **não estão implementados** — Porta 5 os exclui.
- **Skill sempre-carregada que poderia ser condicional:** além de `interaction-patterns` acima, os
  outros quatro do topo da tabela (`project-context`, `plan-mode`, `token-efficiency`,
  `current-context`) são incondicionais por decisão explícita do `CLAUDE.md`, e três deles
  encolheram nesta janela. Nenhum candidato original.
