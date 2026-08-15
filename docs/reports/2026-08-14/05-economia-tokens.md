# Eixo E — Economia de tokens

**Baseline:** `HEAD` = `c03f898` · **Baseline anterior:** `3fbe371`

## Método

Varredura priorizada pelo delta `3fbe371..HEAD` (`skills/architecture/orchestration/SKILL.md` +20,
`skills/shared/scoped-test-execution/SKILL.md` +6, `agents/software-architect.md` +4,
`scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` +18), seguida de medição integral de
`skills/**/SKILL.md`, `agents/*.md`, `commands/*.md` e `CLAUDE-md/*.md`, e de contagem de
carregadores por skill (`grep -rl <skill> agents/ commands/`). Toda skill candidata passou pelo
teste "quantos fluxos leem isto, e quanto do arquivo é acionável naquele fluxo". O hook `02c` foi
executado com payloads reais para medir o custo de injeção de contexto no hot path.

| Medição | Valor |
|---|---|
| `CLAUDE.md` | 586 linhas (`CLAUDE-md/*.md` somam 343) |
| Maiores skills | `migration-v1-to-v2` 438 · **`orchestration` 377** · `project-context` 269 · `backlog-template` 238 |
| Skills mais carregadas | `worktree` 38 · `interaction-patterns` 33 · `current-context` 28 · `plan-mode` 26 · `token-efficiency`/`project-context`/`model-identity` 18 |
| Agentes | 18 arquivos, 3.422 linhas (maior: 211) |
| Comandos | 3.118 linhas (maior: `learn.md` 200) |
| `project-context` carregado por | **18** agentes (todos) |
| Agentes sem carga própria de `scoped-test-execution` | 11 de 18 |
| Skills com `references/` | 20+ · `orchestration` (377 linhas, 2ª maior) **não tem** |

Confirmação do delta: o crescimento de `21fceb4` **caiu em caminho sempre carregado**. As 20
linhas de `## Background Process Discipline` entraram em `orchestration/SKILL.md`, que
`agents/software-architect.md:69` e `:80` tornam obrigatório em todo caminho de execução — apesar
de a linha 38 do mesmo agente listá-lo como carga *condicional*. As 6 linhas de
`scoped-test-execution` (§ "Run Independent Verification Commands in Parallel") entraram numa skill
carregada sob gatilho ("before running any test command"), portanto sem incidência sempre-ligada.

---

## HIGH

Nenhum achado original neste eixo.

---

## MEDIUM-HIGH

### `02c-full-suite-guard.sh` casa substring solta e injeta 405 bytes de contexto em comandos que não rodam teste nenhum

- **Fingerprint:** `token-02c-full-suite-guard-substring-match-injects-nudge-on-non-test-commands`
- **Alvo:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`
- **Evidência:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:30-33` —
  ```
      case "$cmd" in
          *jest*)
              [[ "$cmd" != *--findRelatedTests* && "$cmd" != *.test.* && "$cmd" != *.spec.* ]] && return 0 ;;
      esac
  ```
  Mesmo padrão em `:43` (`*pytest*`), `:47` (`*phpunit*|*pest*`), `:69` (`*rspec*`), `:35` (`*vitest*`).
  Payload emitido em `:94` — `"scoped-test-execution: this command looks like an UNSCOPED full test suite run. […] stop and scope this run to the files touched"`.
- **Problema:** nenhum dos ramos exige que o comando **invoque** um runner — basta a substring
  aparecer em qualquer posição. Execução real dos 6 payloads abaixo contra o script no HEAD:
  `cat jest.config.js`, `rg -n pytest pyproject.toml`, `ls node_modules/.bin | grep vitest`,
  `git log --oneline | grep rspec`, `npx jest --version`, `echo phpunit` — **6 de 6 disparam** o
  nudge. Nenhum roda um teste.
- **Por que importa:** o hook roda em **todo** tool call `Bash` (dispatcher
  `scripts/hooks/pre-tool-use.sh:31`). Cada falso positivo injeta 405 bytes (~100 tokens) de
  `additionalContext` que instruem o modelo a *parar e reescopar* um comando que não é um teste —
  não é só custo, é instrução errada no ponto de decisão. Em sessão de leitura de configuração de
  um projeto Jest/pytest, o disparo é praticamente por comando.
- **Proposta:** ancorar cada padrão numa forma de invocação em vez de substring — exigir que o
  runner esteja em posição de comando (início da string, após `|`, `&&`, `;`, `npx `, `bin/`,
  `vendor/bin/`) e adicionar um descarte prévio para verbos de leitura (`cat`, `grep`, `rg`, `ls`,
  `echo`, `head`, `--version`, `--help`).
- **Impacto positivo:** elimina ~100 tokens de contexto espúrio por comando de leitura que mencione
  um runner; incide em 100% das sessões `Bash` de qualquer projeto com Jest/pytest/PHPUnit/RSpec no
  nome de arquivo ou dependência.
- **Impacto negativo / risco:** o casamento passa a ser sensível à forma do comando — invocações
  exóticas (`docker compose run --rm app sh -c "…"`, aliases, `env FOO=1 pytest`) podem escapar do
  guard e virar falso negativo, que é o modo de falha oposto e mais caro. Cada ancoragem nova é
  mais uma linha de `case` para manter.
- **Esforço:** Médio

### `commands/pr.md` manda o agente de menor janela de contexto derivar o corpo do PR de um `git diff` sem limite, no mesmo arquivo que já limita o `git log` a `head -20`

- **Fingerprint:** `token-pr-md-unbounded-full-diff-to-repetitive-tier-while-same-file-caps-git-log`
- **Alvo:** `commands/pr.md`
- **Evidência:** `commands/pr.md:99` — `"- Fill each section with content derived from \`git diff ${DEFAULT_BRANCH}...HEAD\` and recent commits"`;
  `commands/pr.md:112` — `"- \`technical-writer\` — reads the commits and diff, writes the PR title and description based solely on what changed in this branch"`.
  Contraste no mesmo arquivo: `commands/pr.md:80` — `git log ${DEFAULT_BRANCH}..HEAD --format="%s" 2>/dev/null | head -20`;
  e `commands/commit.md:42` — `"Run \`git status --short\`, \`git diff --cached --stat\`, and \`git diff --stat\`"`.
- **Problema:** `technical-writer` é `tier: repetitive` → Haiku, e o `CLAUDE.md` registra
  explicitamente que essa é a única tier com janela de 200K contra 1M das demais. `pr.md` é o único
  comando que entrega a esse agente um `git diff` **completo e sem filtro** de branch inteira. As
  outras duas leituras de git do próprio arquivo já são limitadas (`head -20`, `--stat`).
- **Por que importa:** numa branch de feature média (30–60 arquivos), o diff bruto é a maior
  entrada única de qualquer fluxo `/devteam:*`, e vai para o agente com um quinto da janela dos
  outros. O corpo do PR precisa de *o que mudou*, não de *cada linha* — `--stat` mais leitura
  dirigida dos arquivos que a seção do template exige entrega o mesmo texto.
- **Proposta:** trocar a linha 99 por `git diff ${DEFAULT_BRANCH}...HEAD --stat` + leitura dirigida
  só dos arquivos citados na seção do template, e reescrever a linha 112 para "reads the commit
  list and the diff **stat**, abrindo arquivos individuais só quando a seção exigir".
- **Impacto positivo:** troca uma entrada proporcional ao tamanho da branch por uma proporcional ao
  número de arquivos (~1 linha por arquivo). Incide em todo `/devteam:pr` — 1 spawn por PR aberto,
  no agente de menor janela.
- **Impacto negativo / risco:** o PR body perde acesso automático a detalhes que só aparecem no
  diff (mudança de assinatura, flag nova, quebra de contrato). Descrições podem ficar mais rasas em
  branches onde a mensagem de commit é pobre, e o agente passa a precisar decidir *quais* arquivos
  abrir — uma decisão a mais que ele pode errar.
- **Esforço:** Baixo

---

## MEDIUM

### `orchestration/SKILL.md` cresceu para 377 linhas sem `references/`, e 138 delas só valem em caminhos condicionais que a maioria das rodadas nunca atinge

- **Fingerprint:** `token-orchestration-skill-377-lines-138-conditional-path-only-no-references-dir`
- **Alvo:** `skills/architecture/orchestration/SKILL.md`
- **Evidência:** `skills/architecture/orchestration/SKILL.md:49-51` — `"Activates when the user signals fully autonomous execution — \"execute everything autonomously\", \"don't ask me\" […] In this mode the Execution Strategy Gate quiz is **skipped entirely**"`;
  `:91` — `"After every subagent in an autonomous sprint returns, emit one short visible line"`;
  `:191` — `"Note the wall-clock time of each spawn. If the user asks for status and no return has arrived:"`;
  `:246-247` — `"**Never open a new \`sleep\`/poll-loop Bash command to re-check something already being waited on.**"`.
  Carga obrigatória em `agents/software-architect.md:69` — `"Both procedures […] are defined in \`skills/architecture/orchestration/SKILL.md\`. Load it before the gate."` — e `:80` — `"Load \`skills/architecture/orchestration/SKILL.md\` for the agent roster […]"`.
- **Problema:** medição por seção: Autonomous Sprint Protocol 37 · Progress Visibility 27 · Spawn
  Integrity checks 4–5 (Liveness + Auto-reactivation) 54 · Background Process Discipline 20 = **138
  de 377 linhas (8.690 de 20.732 bytes, 42%)** que só se aplicam a três gatilhos raros: modo
  autônomo declarado, spawn que não retornou, e comando `Bash` em background. Tudo carregado de
  saída, antes de qualquer um dos três existir. É a **2ª maior skill do repo** e uma das poucas
  desse porte sem `references/` — mais de 20 outras já usam o padrão.
- **Por que importa:** a skill é carregada por `software-architect`, que 8 comandos spawnam
  (`adr`, `architect`, `dba`, `learn`, `plan`, `refactor`, `review`, `security`). O
  `agents/software-architect.md:38` a lista como condicional, mas as linhas 69 e 80 a tornam
  obrigatória em qualquer execução — ou seja, 377 linhas por spawn de arquiteto, das quais 138 são
  prefetch de caminho não tomado. O crescimento de `21fceb4` (+20) foi inteiramente nesse bloco
  condicional.
- **Proposta:** mover Autonomous Sprint Protocol + Progress Visibility para
  `references/autonomous-sprint.md` e Spawn Integrity 4–5 + Background Process Discipline para
  `references/liveness-and-background.md`, deixando no `SKILL.md` uma linha de gatilho por bloco
  ("usuário pediu execução autônoma → carregue X"; "um spawn não retornou → carregue Y").
- **Impacto positivo:** 377 → ~245 linhas (20.7KB → ~12KB) no caminho sempre carregado, incidindo
  em todo spawn de `software-architect` a partir de 8 comandos.
- **Impacto negativo / risco:** as checks 4 e 5 existem exatamente porque o orquestrador **não
  percebe** que está no caminho delas — o gatilho "um spawn não retornou" é observado tarde, e uma
  regra atrás de `references/` pode simplesmente não ser carregada no momento em que faz falta. É a
  mesma classe de falha que o `CLAUDE.md` documenta para o banner de fechamento (14/16 abertura,
  0/6 fechamento). Extrair Liveness é a parte arriscada da proposta; extrair o Autonomous Sprint
  Protocol não é.
- **Esforço:** Médio

### `model-identity/SKILL.md` é carregada "antes de qualquer outra ação" por 18 agentes, e 32 das suas 58 linhas são formato e exemplos que o agente já tem inline

- **Fingerprint:** `token-model-identity-32-of-58-lines-are-format-spec-and-examples-agent-already-holds-inline`
- **Alvo:** `skills/shared/model-identity/SKILL.md`
- **Evidência:** `skills/shared/model-identity/SKILL.md:8` — `"**Before any other action** — before reading a file, running a command, or answering — emit your run banner"`;
  `:12` — `"Find the block marked \`<!-- run-banner -->\` in your own agent definition"`;
  `:23` — `"That block is generated at render time from \`scripts/lib/tiers.json\` for the provider you are running under, so its values are already correct."`;
  e então `:29-31` redefine o formato —
  ```
  | Agent | Tier | Model | Effort |
  |---|---|---|---|
  | `agent-name` | `tier` | `model-id` | `effort` |
  ```
  seguido de `:40-58`, três exemplos completos (`backend-developer`/`sonnet`, `software-architect`/`opencode-go/qwen3.7-plus`, `technical-writer`/`gpt-5.6-luna`).
- **Problema:** o procedimento é "copie verbatim o bloco que já está no seu próprio arquivo". A
  seção `## Format` (12 linhas) especifica as colunas de uma tabela que o agente vai copiar sem ler
  a especificação, e `## Examples` (19 linhas) mostra três banners de *outros* agentes, dois deles
  com model ids de provedores que o leitor não está rodando. São 32 linhas de 58 (1.186 de 4.192
  bytes, 28%) sem efeito no output.
- **Por que importa:** é a **primeira** skill carregada em toda invocação de agente — 18 agentes,
  e num `/devteam:fullstack` isso é ~6 spawns × 58 linhas = 348 linhas só para renderizar 4 linhas
  de tabela que cada agente já carrega no corpo. Cada exemplo com model id fictício também é
  superfície de drift quando um provedor muda de nome de modelo.
- **Proposta:** mover `## Format` e `## Examples` para
  `skills/shared/model-identity/references/format.md`, mantendo no `SKILL.md` o procedimento
  (linhas 8–25) e o fallback de bloco ausente (`:25`).
- **Impacto positivo:** 58 → ~27 linhas (4.2KB → ~3KB) no caminho mais quente do repo; ~186 linhas
  economizadas por rodada de 6 spawns.
- **Impacto negativo / risco:** o fallback de `:25` ("emit the table with `unknown` in the Model and
  Effort cells") passa a não ter formato ao lado — um agente sem bloco `<!-- run-banner -->` perde a
  referência de colunas exatamente no caso em que ela é necessária. Exige manter a especificação de
  colunas duplicada no `agent-lint.sh` ou aceitar que o fallback fique mais frágil.
- **Esforço:** Baixo

### `project-context` embute uma tabela de 6 linhas que reafirma a exceção de `scoped-test-execution` e admite, na linha seguinte, que ela não basta

- **Fingerprint:** `token-project-context-restates-scoped-test-exception-table-unusable-alone-read-by-18-agents`
- **Alvo:** `skills/shared/project-context/SKILL.md`
- **Evidência:** `skills/shared/project-context/SKILL.md:207-214` —
  ```
  | Situation | What runs |
  |-----------|-----------|
  | You changed code and want to verify it | Tests covering the change and its direct dependents |
  | A scoped test failed | Fix it — a failure never authorizes widening the run |
  | The change touches shared code, or the suite is fast | Still scoped. Neither is an escalation signal |
  ```
  contra `skills/shared/scoped-test-execution/SKILL.md:28` — `"No other signal authorizes it. Not a fast suite, not a wide refactor, not a change to shared code, not a scoped test that failed"`.
  E `skills/shared/project-context/SKILL.md:216` — `"Load the skill for the blast-radius derivation and the per-stack runner filters. **Do not work from this table alone.**"`
- **Problema:** o bloco 205–216 (1.197 bytes) restata a seção "The Only Exception" da skill e a
  frase de escopo (`scoped-test-execution/SKILL.md:12`, `"Who this binds: every agent that invokes a
  test runner"`), e a própria linha 216 declara que a tabela é insuficiente para agir. Quem vai
  rodar teste carrega a skill e lê o conteúdo de novo; quem não vai rodar teste leu 17 linhas que
  nunca serão usadas.
- **Por que importa:** `project-context` é carregada por **18 de 18** agentes — é o arquivo mais
  universalmente lido do repo. Onze desses agentes (`backend-reviewer`, `code-reviewer`,
  `devops-specialist`, `frontend-reviewer`, `product-analyst`, `security-specialist`,
  `seo-specialist`, `setup-assistant`, `software-architect`, `technical-writer`, `ui-ux-designer`)
  não têm sequer linha de carga de `scoped-test-execution` no próprio corpo. Custo agregado por
  fluxo multi-agente: 17 linhas × N spawns, mais releitura do mesmo texto em cada agente que roda
  teste de fato.
- **Proposta:** reduzir `## Test Execution — Scoped by Default` à diretiva de carga com gatilho
  ("antes de invocar qualquer runner de teste, carregue `skills/shared/scoped-test-execution/SKILL.md`
  — ela vincula todo agente, não só os especialistas"), removendo a tabela de 6 linhas que a linha
  216 já declara insuficiente.
- **Impacto positivo:** 17 → 3 linhas (1.197 → ~250 bytes) num arquivo lido por 18 agentes; ~250
  linhas economizadas num fluxo `/devteam:fullstack` completo (≈6 spawns + review).
- **Impacto negativo / risco:** a tabela é hoje a única defesa contra o agente que **não** carrega a
  skill (por esquecimento ou por caminho fora de `/devteam:*`) e escala para suíte cheia por conta
  própria. Removê-la transfere toda a proteção para o hook `02c`, cujo casamento por substring está
  reportado acima como impreciso nos dois sentidos. Fazer as duas mudanças no mesmo pass deixaria a
  regra sem nenhuma rede confiável.
- **Esforço:** Baixo

---

## LOW-MEDIUM

Nenhum achado original neste eixo.

---

## LOW

Nenhum achado original neste eixo.

---

## Descartados por duplicação

| Candidato | Porta | Motivo |
|---|---|---|
| `02c-full-suite-guard.sh` — captura `sed` gulosa afeta o custo do nudge | Porta 3 (semântica) | Coincide em (a) alvo e (b) causa-raiz com `auto-full-suite-guard-sed-absorbs-sibling-json-keys` (2026-08-12). O achado publicado acima é o modo de falha **oposto** (falso positivo por substring, não falso negativo por captura), e coincide só em (a) |
| `CLAUDE.md` com 586 linhas / blocos extraíveis | Porta 5 (estado) | `token-claude-md-426-lines-still-monolithic-three-extractable-blocks…` está ✅ Executed mas **reaberto 🔴**; tema registrado, proibido re-levantar |
| `interaction-patterns` 209 linhas × 33 carregadores | Porta 5 (estado) | Já no conjunto aberto: `token-interaction-patterns-209-lines-loaded-unconditionally-by-24-commands-and-2-agents…` (contagem hoje é 33, não 26 — refinamento numérico não é sub-escopo novo) |
| `migration-v1-to-v2` 438 linhas, maior skill do repo | Porta 5 (estado) | Já no conjunto aberto: `skill-shared-migration-v1-to-v2-437-lines-largest-in-repo…` |
| `token-efficiency` 160 linhas eager em 18 agentes | Porta 1 (literal) + 3 | `token-token-efficiency-skill-itself-154-lines-eager-loaded-by-all-17-agents-meta-irony…` — mesmo alvo, mesma causa, mesma remediação |
| `backlog-template` 238 linhas carregado por `product-analyst` | Porta 1 (literal) | `token-backlog-template-skill-171-lines-unconditionally-loaded-every-product-analyst-spawn…` |
| `project-context` — bloco Docker eager vs. SonarQube gated | Porta 1 (literal) | `token-project-context-docker-development-environment-section-22-lines-inlined-eager-loaded-by-14-agents…` |
| `software-architect.md:88-89` duplica Spawn Integrity checks 4–5 do `orchestration` | Porta 3 (semântica) | Coincide em (b) causa e (c) remediação com o achado de `orchestration` publicado acima; além disso é matéria do Eixo D (casa canônica), não de economia — ganho de ~2 linhas não sustenta achado próprio |
| `output-format` 190 linhas × 9 carregadores | Porta 4 (escopo menor) | Sem hit no banco, mas o arquivo é integralmente templates de saída acionáveis (Report, Conformance, Security, Plan, Diagnostics) — nenhum bloco identificado como caminho-não-tomado; não há achado, não só duplicata |
