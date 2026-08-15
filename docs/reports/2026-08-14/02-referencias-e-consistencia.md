# Eixo B — Referências e consistência

**Baseline:** `HEAD` = `c03f898` · **Baseline anterior:** `3fbe371`

## Método

Varredura priorizada no delta `3fbe371..HEAD` (`CHANGELOG.md`, `agents/software-architect.md`,
`scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`, `scripts/update.sh`,
`skills/architecture/orchestration/SKILL.md`, `skills/shared/scoped-test-execution/SKILL.md`),
mais varredura estrutural integral das relações que os helpers **não** cobrem.

Os quatro gates rodaram limpos e são reportados aqui como linha de base, não como achado:

```
$ bash helpers/orphan-skill-scan.sh      → orphan-skill-scan: clean ✓
$ bash helpers/orphan-template-scan.sh   → orphan-template-scan: clean ✓
$ bash helpers/agent-lint.sh             → agent-lint: clean ✓
$ bash helpers/size-limits.sh            → size-limits: clean ✓
```

Verificações mecânicas próprias, todas **sem divergência** (portanto não viram achado):

| Verificação | Resultado |
|---|---|
| `name:` de skill == basename do diretório (151 `SKILL.md`) | 0 divergências |
| `name:` duplicado entre categorias | 0 |
| `description:` de skill > 95 chars | 0 |
| `commands/*.md` ↔ chaves de `scripts/lib/commands.json` | conjuntos idênticos |
| `commands/*.md` ↔ tabela de comandos do `CLAUDE.md` | conjuntos idênticos |
| `grep -L current-context commands/*.md` | exatamente os 6 declarados no `CLAUDE.md` |
| `plan_gate: opt_out` em `commands.json` ↔ lista do `CLAUDE.md` | idênticos (8) |
| Headings e contagem de linhas de tabela `README.md` ↔ `README.pt-BR.md` | 17/17 headings, 87/87 linhas |
| Coluna `Tier` de `docs/agents.md` ↔ `tier:` real dos 18 agentes | **1 divergência** → achado B-1 |

O foco recaiu deliberadamente sobre classes de defeito que os quatro helpers são estruturalmente
incapazes de pegar: (a) tabelas de documentação que espelham frontmatter sem validador,
(b) metadado de renderer declarado como canônico mas nunca consumido, (c) script de enforcement
cujas heurísticas não têm contraparte na skill canônica que ele cita.

Portas anti-duplicação aplicadas por candidato (saídas literais em `## Descartados por duplicação`
e no corpo de cada achado). Nenhum slug candidato existia literalmente em `docs/reports/_index.md`;
o pré-filtro mecânico por basename retornou resultado apenas para `agents.md` e
`02c-full-suite-guard.sh`, comparados semanticamente linha a linha.

---

## HIGH

### A coluna `Tier` de `docs/agents.md` afirma `repetitive` para `backend-test-specialist`, exatamente a alocação que o `CLAUDE.md` proíbe por escrito

- **Fingerprint:** `ref-docs-agents-md-tier-column-stale-backend-test-specialist-listed-repetitive`
- **Alvo:** `docs/agents.md`, `docs/agents.pt-BR.md`
- **Evidência:**
  - `docs/agents.md:28` — "`| `backend-test-specialist` | Backend test coverage (conditional) | DEVELOPMENT | `repetitive` |`"
  - `docs/agents.pt-BR.md:28` — "`| `backend-test-specialist` | Cobertura de testes backend (condicional) | DEVELOPMENT | `repetitive` |`"
  - `agents/backend-test-specialist.md:4` — "`tier: backend-exec`" (com `model: sonnet`, `effort: low`)
  - `CLAUDE.md:87` — "Test authoring is **not** low-judgment: `backend-test-specialist` sits in `backend-exec`, matching `frontend-test-specialist` in `frontend`. Do not move a test agent to `repetitive`."
  - Origem confirmada no git: `1f1c837` (`feat(agents): give every agent an explicit model and a run banner`) trocou `-tier: repetitive` / `+tier: backend-exec` no agente; nenhum commit posterior tocou a linha 28 de `docs/agents.md` (`git log -L28,28:docs/agents.md` para em `bbb311a`).
- **Problema:** a referência canônica de agentes publica, nos dois idiomas, um tier factualmente
  errado — e não um tier qualquer: precisamente o único que o `CLAUDE.md` nomeia como proibido para
  agentes de teste, com justificativa (janela de contexto de 200K do Haiku contra 1M dos demais).
- **Por que importa:** `docs/agents.md` é o documento que um usuário lê para decidir custo e
  capacidade por agente. Hoje ele diz que a escrita de testes de backend roda em Haiku/200K quando
  roda em Sonnet/1M. Pior: quem tentar "corrigir a inconsistência" pela direção errada — alinhar o
  frontmatter à doc — executa a mudança que o `CLAUDE.md:87` existe para impedir, e `agent-lint.sh`
  aprovaria (ele valida `tier:` ↔ `tiers.json` ↔ run-banner, nunca contra `docs/`).
- **Proposta:** corrigir as duas linhas 28 para `` `backend-exec` `` e estender
  `helpers/agent-lint.sh` com uma checagem da coluna `Tier` de `docs/agents.md` e
  `docs/agents.pt-BR.md` contra o `tier:` de cada `agents/*.md`.
- **Impacto positivo:** elimina a única divergência de tier viva entre doc e árvore (1 de 18) e
  fecha a categoria inteira com gate, em vez de fechar uma ocorrência.
- **Impacto negativo / risco:** a checagem nova acopla `agent-lint.sh` ao layout de tabela de dois
  arquivos de `docs/` — uma reformatação de `docs/agents.md` (mudar a ordem das colunas, quebrar a
  tabela em duas) passa a quebrar o lint e o CI; e o lint, que hoje só lê `agents/` e
  `scripts/lib/`, passa a depender de `docs/`, que é stripado do pacote instalado.
- **Esforço:** Baixo
- **Refina:** `ref-docs-agents-md-model-column-wrong-technical-writer-listed-haiku-actually-sonnet-and-setup-assistant-listed-sonnet-actually-opus`
  — o pai (✅ Executed 2026-07-31) tratou da coluna **`Model`**, e sua remediação foi substituí-la
  pela coluna **`Tier`** (commit `bbb311a`). O valor errado aqui está na coluna *substituta*,
  introduzida pelo próprio commit de remediação, e a causa raiz é distinta: não é "a doc duplica
  ids de modelo que envelhecem", é "a coluna nova também não tem validador, e drifou". O pai não
  descreve nem a coluna `Tier`, nem `backend-test-specialist`, nem a regra do `CLAUDE.md:87`.

### `tool_rewrites` de `tool-map.json` nunca chega ao corpo renderizado, mas `CLAUDE.md` e `docs/providers.md` o documentam como mecanismo ativo

- **Fingerprint:** `ref-tool-map-tool-rewrites-loaded-but-never-emitted-by-render-provider`
- **Alvo:** `scripts/lib/render_provider.py`, `scripts/lib/tool-map.json`, `CLAUDE.md`, `docs/providers.md`
- **Evidência:**
  - `scripts/lib/render_provider.py:742` — "`    renames = prov_entry.get("tool_rewrites", {}) or {}`"
  - `scripts/lib/render_provider.py:748-753` — "`    if not renames and not idioms:`" … "`    else:`" / "`        for line in idioms:`" / "`            note_lines.append(f"> {line}")`" — `renames` é lido, usado apenas como condição booleana e **nunca iterado nem emitido**; só `idiom_notes` entra na nota.
  - `scripts/lib/render_provider.py:735-736` (docstring da função) — "`      1. Per-provider native tool name for the Claude Code tool names the body`" / "`         references (tool_rewrites from tool-map.json).`"
  - `CLAUDE.md:67` — "Tool availability is provider-native; the renderer rewrites tool names per provider from `scripts/lib/tool-map.json`."
  - `docs/providers.md:127` — "**Add a row to `scripts/lib/tool-map.json`** — `providers.<provider>.tool_rewrites` listing the Claude tool-name → your provider's tool-name mapping (empty `{}` if identity)."
  - Reprodução no HEAD: `bash scripts/render-provider.sh --provider opencode --source-dir . --target-dir <tmp>` → `grep -c AskUserQuestion <tmp>/.opencode/agents/setup-assistant.md` = **3** (o fonte também tem 3); a nota `> **Provider: opencode.**` renderizada contém as 3 linhas de `idiom_notes` e **zero** linha de rename.
- **Problema:** `tool_rewrites` é dado morto no caminho de render. O corpo do agente sai com os
  nomes Claude intactos e sem qualquer instrução de tradução — a única cobertura é a frase genérica
  "This body uses Claude Code idioms", que não diz que `AskUserQuestion` é `question` no opencode
  nem `request_user_input` no Codex, embora o mapa contenha exatamente esse par.
- **Por que importa:** dois documentos afirmam como verdade um comportamento que não existe. Um
  contribuidor seguindo o passo 2 de `docs/providers.md` para portar um provider novo preenche um
  campo sem efeito e testa a integração acreditando que a tradução está coberta. O delta atual
  agrava o custo: `agents/software-architect.md:88-89` introduziu `TaskList`/`TaskGet`/`TaskOutput`,
  `ScheduleWakeup` e `SendMessage` no corpo, e todos passam verbatim — confirmado no render
  (`ScheduleWakeup` = 1 ocorrência no `.opencode/agents/software-architect.md` e 1 no
  `.codex/agents/software-architect.toml`). O `check-codex-compat.sh` linta termos proibidos, não
  nomes de ferramenta Claude não mapeados.
- **Proposta:** emitir `renames` na nota (uma linha `> · **Tool names.** `Claude` → `provider`, …`)
  ou, se a decisão for que `idiom_notes` basta, remover `tool_rewrites` de `tool-map.json` e
  reescrever `CLAUDE.md:67`, `docs/providers.md:127` e a docstring das linhas 735-736 para descrever
  o que o renderer realmente faz.
- **Impacto positivo:** fecha a divergência entre três documentos e o código; e, na variante
  "emitir", entrega ao opencode/Codex a tradução de 5 e 7 nomes de ferramenta que hoje se perde.
- **Impacto negativo / risco:** emitir adiciona 1–2 linhas ao topo de **todos** os 18 corpos de
  agente renderizados por provider (custo de contexto recorrente, em conflito com o Eixo E); e
  amplia o mapa Codex (`Glob`→`Bash`, `Grep`→`Bash`, `WebFetch`→`WebSearch`) para instrução
  explícita, o que pode confundir mais que ajudar num runtime cujos nomes de ferramenta o próprio
  `_comment` admite serem instáveis. A variante "remover" descarta um mecanismo já desenhado e
  obriga cada provider novo a resolver tradução de ferramenta só por prosa.
- **Esforço:** Médio

---

## MEDIUM-HIGH

### O guard `02c` passou a sinalizar formas `make`/`composer` que a tabela de runners da skill canônica não define — e que a linha 59 da mesma skill declara legítimas

- **Fingerprint:** `ref-02c-guard-make-composer-shapes-have-no-row-in-scoped-test-runner-table`
- **Alvo:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`, `skills/shared/scoped-test-execution/SKILL.md`
- **Evidência:**
  - `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:25-27` (comentário, inalterado no delta) — "`# Each pattern below is a command shape with NO scope qualifier (no path,`" / "`# no --filter/-k/--tests/-only-testing/-run), matching the "Scoped command"`" / "`# column in scoped-test-execution/SKILL.md's runner table.`"
  - `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:78-81` (adicionado em `c03f898`) — "`        *make\ *test*|*make\ *-e2e*)`" / "`            [[ "$cmd" != *TESTPATH=* && "$cmd" != *FILTER=* && "$cmd" != *--\ * ]] && return 0 ;;`"
  - `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:86-89` — "`        *composer\ test*)`" / "`            [[ "$cmd" != *test:* ]] && return 0 ;;`"
  - `skills/shared/scoped-test-execution/SKILL.md:45-57` — tabela `| Stack | Scoped command |` com 11 linhas: Jest, Vitest, Playwright/Cypress, pytest, PHPUnit/Pest, Go, Gradle/JUnit, Flutter, RSpec, Xcode, Cargo. **Nenhuma linha Make ou Composer.**
  - `skills/shared/scoped-test-execution/SKILL.md:59` — "When the project defines its own scoped script in `CLAUDE.md`, `package.json`, or a `Makefile`, that command wins over the table."
- **Problema:** três divergências encadeadas. (1) O comentário do próprio script afirma que cada
  padrão espelha a coluna "Scoped command" da tabela — afirmação que deixou de ser verdadeira para
  os três `case` novos. (2) `TESTPATH=`/`FILTER=` não aparecem em lugar nenhum da skill: são
  convenções de um projeto específico promovidas a heurística global sem contraparte canônica.
  (3) A linha 59 diz explicitamente que um script scoped definido num `Makefile` **vence** a tabela,
  enquanto o guard sinaliza qualquer `make …test…` que não carregue `TESTPATH=`/`FILTER=`/`-- ` —
  ou seja, sinaliza justamente o caso que a skill declara legítimo.
- **Por que importa:** o nudge injetado (linha 94) manda o agente aplicar
  `skills/shared/scoped-test-execution/SKILL.md`. Um agente que abre a skill atrás da forma scoped
  de `make test-unit` ou `composer test` não encontra linha alguma, e encontra na linha 59 a
  afirmação oposta à do nudge. O resultado prático é um falso positivo sem caminho documentado de
  conformidade — num projeto que roteia tudo por Make/Composer (exatamente o alvo declarado do
  commit), isso dispara em toda invocação de teste.
- **Proposta:** acrescentar à tabela da skill uma linha `| Make / Composer wrapper |` com a forma
  scoped que o guard reconhece (`make test TESTPATH=<path>` · `composer test:<suite> -- --filter`),
  e reescrever a linha 59 para dizer que o script próprio do projeto vence *desde que carregue um
  qualificador de escopo*.
- **Impacto positivo:** o nudge passa a ter destino verificável; o comentário das linhas 25-27
  volta a ser verdadeiro; e a heurística `TESTPATH=`/`FILTER=` ganha casa canônica em vez de viver
  só no script.
- **Impacto negativo / risco:** documentar `TESTPATH=`/`FILTER=` na skill canoniza a convenção de
  um projeto para todos os instalados — é acoplamento a nomes de variável de Makefile numa skill
  `shared/`, e roça a regra de agnosticismo do Eixo A. Além disso, condicionar a linha 59 a "carregar
  qualificador" enfraquece uma regra hoje absoluta e cria um caso de julgamento onde não havia.
- **Esforço:** Baixo

---

## MEDIUM

### O `CHANGELOG.md [Unreleased]` registra 1 dos 3 commits de comportamento do delta, contrariando o checklist do PR template

- **Fingerprint:** `docs-sync-changelog-unreleased-omits-full-suite-guard-and-orchestration-deltas`
- **Alvo:** `CHANGELOG.md`
- **Evidência:**
  - `CHANGELOG.md:10-13` — "`## [Unreleased]`" / "`### Fixed`" / "`- **`update.sh` aborted the whole update on slim installs with opencode/Codex configured**: …`" — **entrada única**, referente a `f0fb093`.
  - `.github/pull_request_template.md:21` — "`- [ ] `CHANGELOG.md` [Unreleased] section updated (if user-visible behavior changed)`"
  - `git diff --stat 3fbe371..HEAD` toca `CHANGELOG.md` (+3 linhas, todas de `f0fb093`), enquanto
    `c03f898` alterou `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` (+18 linhas, três novos
    `case` que mudam quando o nudge dispara) e `21fceb4` alterou
    `skills/architecture/orchestration/SKILL.md` (+20 linhas, seção `## Background Process
    Discipline`) e `agents/software-architect.md` (nova invariante `ScheduleWakeup`) — nenhum dos
    dois deixou entrada.
- **Problema:** dois dos três commits de comportamento do delta alteram o que o usuário observa —
  um hook que passa a injetar contexto em comandos `make`/`composer` que antes ignorava, e um
  orquestrador que passa a agendar wakeups e a exigir `Monitor` em processos de background — sem
  registro no `[Unreleased]`.
- **Por que importa:** o `[Unreleased]` é o insumo do release note e da checagem que o usuário faz
  após `/devteam:update` para entender por que o comportamento mudou. Um usuário que passe a receber
  o nudge de full-suite em `make test` na próxima versão não encontra explicação no changelog. O
  item do PR template não é gate automatizado — não há verificação em `helpers/` nem em
  `.github/scripts/ci/` que ligue "commit tocou hook/skill/agente" a "changelog tocado".
- **Proposta:** adicionar duas entradas ao `[Unreleased]` (uma `### Fixed` para a detecção
  Make/Composer do `02c`, uma `### Changed` para a disciplina de background e a auto-reativação do
  orquestrador) e considerar um sub-script `Stop` heurístico, no molde de `03e-adr-gap-check.sh`,
  que avise quando a sessão tocou `agents/`, `skills/` ou `scripts/hooks/` sem tocar o `CHANGELOG`.
- **Impacto positivo:** restaura a completude do `[Unreleased]` e, com a heurística, fecha uma
  categoria de omissão que hoje depende inteiramente de disciplina humana no PR.
- **Impacto negativo / risco:** um aviso `Stop` a mais em cada sessão que toca agente ou skill —
  ruído recorrente com alta taxa de falso positivo (refactor interno, correção de typo em skill), e
  mais um item na sequência do dispatcher `Stop`, que já roda 10 sub-scripts. O `CHANGELOG.md` já
  está sinalizado como grande demais e sem rotação (`token-changelog-already-growing-…`, aberto),
  então adicionar entradas piora esse item.
- **Esforço:** Baixo

### A seção nova de paralelismo de Bash ficou dentro de `scoped-test-execution`, fora do escopo canônico declarado da skill e invisível ao índice de skills

- **Fingerprint:** `ref-scoped-test-execution-bash-parallelism-section-outside-declared-canonical-scope`
- **Alvo:** `skills/shared/scoped-test-execution/SKILL.md`
- **Evidência:**
  - `skills/shared/scoped-test-execution/SKILL.md:63-65` (adicionado em `21fceb4`) — "`## Run Independent Verification Commands in Parallel`" … "`issue them as **separate Bash tool calls in the same message**, not chained in one shell with `;`/`&&`.`"
  - `skills/shared/scoped-test-execution/SKILL.md:3` (frontmatter, inalterado) — "`description: Run only tests covering the touched code; full suite only on explicit user request.`"
  - `CLAUDE.md:166` (Canonical Rule Homes) — "`| Which tests to execute when finishing a task — scoped to the touched code, full suite only on explicit user request | `skills/shared/scoped-test-execution/SKILL.md` …`"
  - Regra irmã já existente noutro lugar: `skills/architecture/orchestration/SKILL.md:351` — "`   - Agents with no dependency on each other MUST be spawned in **parallel**`"; e `CLAUDE.md:49` "`### Parallel Execution After Approval`".
  - `grep -i parallel skills/shared/token-efficiency/SKILL.md` → **0 ocorrências**, apesar de o `CLAUDE.md` § Token Efficiency nomear essa skill como referência canônica de padrões de eficiência.
- **Problema:** a regra adicionada não é sobre *quais* testes executar — é sobre *como emitir
  chamadas Bash independentes*, e vale para lint, type-check, build e qualquer par de comandos sem
  dependência. Ela ficou hospedada numa skill cujo escopo canônico o `CLAUDE.md:166` define em uma
  frase que não a comporta, e cuja `description:` — o texto que alimenta o índice sempre carregado —
  não a menciona.
- **Por que importa:** a regra fica inalcançável por busca. Um agente que precise decidir se
  encadeia `lint && build` só a encontra se já tiver carregado a skill de escopo de testes por outro
  motivo. E, por ser genérica, ela é candidata natural a ser reescrita numa segunda casa
  (`token-efficiency`, `orchestration`) por quem não souber que existe aqui — que é exatamente o
  cenário que a seção "Canonical Rule Homes — Delegate, Never Restate" existe para prevenir.
- **Proposta:** mover a seção para `skills/shared/token-efficiency/SKILL.md` (casa canônica de
  padrões de eficiência segundo o `CLAUDE.md`), deixando em `scoped-test-execution` no máximo uma
  linha de referência; ou, se ficar, ampliar a `description:` e a linha 166 do `CLAUDE.md` para
  declarar o escopo real da skill.
- **Impacto positivo:** a regra passa a ser encontrável pelo índice de skills e ganha uma única casa
  declarada, fechando a porta para uma segunda redação divergente.
- **Impacto negativo / risco:** mover custa uma referência cruzada nova entre duas skills `shared/`
  e tira a regra do ponto exato onde ela é mais aplicável (o fim de tarefa, quando teste e lint
  rodam juntos) — um agente que carregue só `scoped-test-execution` deixa de vê-la. Ampliar a
  `description:` empurra a skill contra o orçamento de 95 caracteres do índice sempre carregado.
- **Esforço:** Baixo

---

## LOW-MEDIUM

### A única descrição em prosa do guard `02c` na árvore de docs continua exemplificando só runners nativos, depois de o guard passar a cobrir wrappers opacos

- **Fingerprint:** `docs-sync-hooks-md-64-full-suite-guard-examples-predate-wrapper-detection`
- **Alvo:** `CLAUDE-md/hooks.md`
- **Evidência:**
  - `CLAUDE-md/hooks.md:64` — "`02c-full-suite-guard.sh` is the per-command safety net for `skills/shared/scoped-test-execution/SKILL.md`: when a `Bash` command matches an unscoped full-suite shape (e.g. `pytest` with no path/`-k`, `vendor/bin/phpunit` with no `--filter`), it injects an `additionalContext` reminder of the rule"
  - `CLAUDE-md/hooks.md:55` — "`02c-full-suite-guard.sh` — nudges on unscoped full-suite test commands (Bash), see below"
  - Contraparte no HEAD: `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:72-77` — "`# `make <target>` and `composer test:*` are opaque wrappers around a real`" / "`# runner (Docker exec, phpunit, etc.) — the literal command string never`" / "`# contains a runner name for the patterns above to match`"
- **Problema:** os dois exemplos da linha 64 são runners cujo nome aparece literalmente no comando.
  O commit `c03f898` acrescentou a classe oposta — wrappers que **não** contêm nome de runner — e é
  justamente a classe com maior superfície de falso positivo (qualquer alvo de Make cujo nome
  contenha `test`). A doc não é falsa (são "e.g."), mas descreve o guard estritamente menor do que
  ele é.
- **Por que importa:** `CLAUDE-md/hooks.md` é onde alguém investiga por que um nudge disparou. Quem
  vir o nudge após `make migrate-test-db` e ler a linha 64 conclui que o guard não deveria ter
  disparado, e vai procurar o bug no dispatcher em vez de nos três `case` novos.
- **Proposta:** acrescentar à lista de exemplos da linha 64 um terceiro caso — "`make <target>` ou
  `composer test` sem qualificador de escopo" — indicando que wrappers opacos são cobertos por
  correspondência no nome do alvo, não no runner.
- **Impacto positivo:** a prosa volta a delimitar o alcance real do guard; o diagnóstico de um
  disparo inesperado passa a apontar para o lugar certo em uma leitura.
- **Impacto negativo / risco:** amarra `CLAUDE-md/hooks.md` à lista concreta de shapes do script,
  criando um segundo ponto a atualizar a cada novo `case` — a linha 64 hoje é deliberadamente
  genérica, e enumerar padrões é o começo de uma duplicação da função `is_full_suite()` em prosa.
- **Esforço:** Baixo

---

## LOW

Nenhum achado original nesta severidade.

---

## Descartados por duplicação

| Candidato | Alvo | Porta que rejeitou | Motivo |
|---|---|---|---|
| Captura `sed` do `02c` continua gulosa e absorve chaves irmãs do payload | `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` | Porta 5 (estado) | Já registrado e **aberto**: `auto-full-suite-guard-sed-absorbs-sibling-json-keys` — **MEDIUM-HIGH** — o delta `c03f898` não tocou a linha 22, o problema reproduz igual, mas reapresentá-lo é ruído. |
| Comentário do `02c` cita `02-graphify-hint.sh` como precedente de "pure-bash on the hot path" | `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` | Porta 5 (estado) | Já registrado e aberto: `docs-sync-02c-comment-cites-graphify-hint-as-sed-precedent` — **LOW-MEDIUM**. |
| `CHANGELOG.md` cresceu sem rotação nem tooling de arquivo | `CHANGELOG.md` | Porta 3 (semântica, 2/3) | `token-changelog-already-growing-and-not-extracted-by-release` — mesmo alvo e mesma remediação (rotação/arquivo). O achado `docs-sync-changelog-unreleased-omits-…` acima passa porque a causa raiz é omissão de entrada, não tamanho, e a remediação é oposta (acrescentar, não extrair). |
| `CLAUDE.md` § File Structure não lista `docs/prompts/`, `docs/harness.md`, `docs/credentials.local.md`, `docs/user-preferences.md` | `CLAUDE.md` | Porta 5 (estado) + instrução do pass | Família `ref-claude-md-file-structure-*` está ✅ Executed; "CLAUDE.md File Structure omits X" está explicitamente vetada para re-levantamento. |
| `helpers/agent-lint.sh` não valida a coluna `Tier` de `docs/agents.md` | `helpers/agent-lint.sh` | Porta 3 (semântica, 2/3 contra o próprio B-1) | É a remediação proposta do achado B-1, não um achado autônomo — separá-lo produziria duas entradas com a mesma correção. |
| `composer test --filter=Foo` é sinalizado como não-scoped pelo `case` da linha 86-89 | `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` | Fora de eixo | É defeito lógico de heurística, território do Eixo C — repassado para lá em vez de duplicado aqui. |
| `skills/architecture/orchestration/SKILL.md` § Background Process Discipline exige `Monitor` sem cláusula de indisponibilidade, ao contrário do check 5 (`ScheduleWakeup`) | `skills/architecture/orchestration/SKILL.md` | Porta 3 (semântica, 2/3 contra B-2) | Mesma causa raiz do achado `ref-tool-map-tool-rewrites-…` (nome de ferramenta Claude sem tradução nem fallback fora do Claude Code) e mesma remediação; coberto lá como evidência, não como achado separado. |
