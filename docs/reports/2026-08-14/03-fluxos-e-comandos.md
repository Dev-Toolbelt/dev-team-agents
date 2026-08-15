# Eixo C — Fluxos, comandos e automação

**Baseline:** `HEAD` = `c03f898` · **Baseline anterior:** `3fbe371`

## Método

Prioridade total no delta `3fbe371..c03f898` (quatro commits: `21fceb4`, `f88ee51`, `f0fb093`,
`c03f898`), aplicando a hipótese do pass anterior — *toda mudança de comportamento do delta carrega
um defeito verificado, e nenhum gate automático cobre essa classe*. Cada um dos quatro commits foi
lido com `git show`, e as duas mudanças executáveis foram **reproduzidas mecanicamente**:

- `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh` foi alimentado com 11 payloads JSON reais de
  `PreToolUse` via `bash`, comparando "flagged" vs "silent" contra o que a skill citada pelo próprio
  nudge define como escopado.
- O trecho novo de `scripts/update.sh` (linhas 98–126) foi extraído para um projeto sintético em
  `/tmp/fp` com `.opencode/`, `render-provider.sh` e `opencode/plugin/dev-team-agents.ts` presentes,
  e um `install-opencode.sh` falso saindo com o `exit 1` real da linha 80 do script verdadeiro.
- `scripts/render-provider.sh --provider opencode` foi executado de verdade contra a árvore do HEAD
  para conferir o que chega ao `.opencode/agents/software-architect.md` renderizado.

Complementarmente foram lidos `scripts/lib/strip-tarball.sh`, `scripts/install.sh` (`KEEP_ROOT`),
`scripts/install-codex.sh`, `scripts/install-opencode.sh`, `scripts/lib/tool-map.json`, os dois
dispatchers de hook e o inventário de `scripts/hooks/pre-tool-use/` e `scripts/hooks/stop/`.

Todos os candidatos passaram pelas portas literal, pré-filtro mecânico por basename, semântica e de
estado antes de virarem achado — ver `## Descartados por duplicação` no fim.

---

## HIGH

### O guard "slim install" do Codex em `update.sh` é ramo morto, e comentário + CHANGELOG afirmam um strip que `strip-tarball.sh` explicitamente não faz

- **Fingerprint:** `flow-update-sh-codex-slim-guard-dead-branch-false-strip-claim`
- **Alvo:** `scripts/update.sh`
- **Evidência:**
  - `scripts/update.sh:99-100` — "`# Slim Claude installs don't bundle the cross-CLI plumbing (stripped by`" / "`# scripts/lib/strip-tarball.sh), so install-opencode.sh would abort with`"
  - `scripts/lib/strip-tarball.sh:28-29` — "`# Cross-CLI plumbing (opencode/Codex render engine and installer scripts)`" / "`# is now INCLUDED in the slim Claude install so users can add Codex or`"
  - `scripts/lib/strip-tarball.sh:21-26` — a única remoção relacionada é "`rm -rf "$extracted/opencode"              # provider-plugin dir — fetched on demand via install-provider.sh`"; `scripts/` inteiro sobrevive
  - `scripts/install.sh:284` — "`KEEP_ROOT=(agents scripts skills templates commands)`"
  - `scripts/update.sh:118` — "`    if [ -f ".dev-team-agents/scripts/render-provider.sh" ] && [ -f ".dev-team-agents/agents/product-analyst.md" ]; then`"
  - `scripts/install-codex.sh:83` — a condição real do `exit 3` é apenas "`if [[ ! -f "$RENDER_SCRIPT" ]]; then`"
  - `CHANGELOG.md:13` — "`which abort with `exit 3` when the cross-CLI plumbing isn't bundled (slim installs strip it — see `scripts/lib/strip-tarball.sh`)`"
- **Problema:** três afirmações encadeadas são falsas no HEAD. (1) `strip-tarball.sh` **não** remove
  o render engine nem os installers — o comentário no topo dele diz o contrário do que `update.sh`
  e o CHANGELOG afirmam, citando esse mesmo arquivo como fonte. (2) Como `scripts/` está no
  `KEEP_ROOT` e `agents/` também, as duas condições do guard do Codex (`render-provider.sh` **e**
  `agents/product-analyst.md`) são verdadeiras em **todo** install, slim ou completo — o `else` das
  linhas 121–125 é inalcançável na prática. (3) `install-codex.sh` só sai com 3 quando
  `render-provider.sh` falta, o que num slim install nunca acontece — ou seja, a metade Codex do fix
  guarda um erro que já não existe, com uma sentinela (`agents/product-analyst.md`) que não é
  "cross-CLI plumbing" nenhuma.
- **Por que importa:** o CHANGELOG publicado documenta como verdade uma regra de empacotamento que o
  arquivo citado contradiz explicitamente — quem for mexer em slim install vai partir da premissa
  errada. E, se `product-analyst.md` for renomeado ou removido algum dia, o guard passa a pular o
  re-render do Codex silenciosamente, emitindo a mensagem enganosa "this is a slim install".
- **Proposta:** alinhar a sentinela do Codex à condição real de `install-codex.sh` (só
  `render-provider.sh`), remover `agents/product-analyst.md` do teste, e reescrever comentário +
  entrada do CHANGELOG para dizer o que de fato é removido: **apenas `opencode/plugin/`**.
- **Impacto positivo:** elimina um ramo morto, faz o guard e o script guardado terem a mesma
  pré-condição, e para de propagar uma afirmação falsa sobre `strip-tarball.sh`.
- **Impacto negativo / risco:** com a sentinela reduzida a `render-provider.sh`, o guard do Codex
  passa a ser um `if` que nunca é falso em nenhum install atual — vira código puramente defensivo
  para instalações legadas; reescrever o CHANGELOG mexe em entrada já publicada em `[Unreleased]`.
- **Esforço:** Baixo

---

## MEDIUM-HIGH

### O caso `composer test*` do guard não tem nenhum qualificador de escopo na lista de exclusão, marcando 100% das execuções escopadas como suíte completa

- **Fingerprint:** `flow-02c-composer-fallback-case-ignores-every-scope-qualifier`
- **Alvo:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`
- **Evidência:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:86-89` —
  ```
  case "$cmd" in
      *composer\ test*)
          [[ "$cmd" != *test:* ]] && return 0 ;;
  esac
  ```
  Reproduzido alimentando o sub-script com payloads `PreToolUse` reais:
  ```
  $ run() { printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$1" \
      | bash scripts/hooks/pre-tool-use/02c-full-suite-guard.sh; }
  FLAGGED  : composer test-unit --filter FooTest
  FLAGGED  : composer test tests/Unit/FooTest.php
  silent   : composer test:unit --filter FooTest
  FLAGGED  : composer test
  ```
- **Problema:** os dez casos anteriores da função excluem qualificadores de escopo reais
  (`--filter`, `.test.`, `::`, `-run `, `--tests`, path). Este é o único cuja exclusão — `test:` —
  não é qualificador de escopo nenhum: é só a marca de que o *outro* case já tratou o comando.
  Consequência: `composer test <path>` e `composer test-unit --filter X` — ambos perfeitamente
  escopados — disparam o nudge. Só `composer test:` escapa, e escapa porque cai no case anterior,
  não porque foi reconhecido como escopado.
- **Por que importa:** o nudge injeta em contexto a afirmação "this command looks like an UNSCOPED
  full test suite run" (linha 94) sobre um comando que carrega um path de arquivo explícito. O agente
  é instruído a **parar e re-escopar** algo já escopado — ou refaz o trabalho, ou aprende a ignorar o
  nudge, que é o pior dos dois resultados para um safety net.
- **Proposta:** dar ao terceiro case a mesma lista de exclusão do segundo mais path:
  `[[ "$cmd" != *test:* && "$cmd" != *--filter* && "$cmd" != *--\ * && "$cmd" != *.php* && "$cmd" != *tests/* ]]`.
- **Impacto positivo:** zera o falso positivo em runs escopados de projetos PHP que usam scripts do
  Composer — hoje 3 de 4 formas testadas disparam indevidamente.
- **Impacto negativo / risco:** amplia a lista de exclusões que precisa ser mantida em paralelo com
  a tabela Runner Filters da skill, e abre um falso negativo novo: `composer test --filter` de fato
  aponta a suíte inteira quando o script empacotado ignora o argumento.
- **Esforço:** Baixo

### `update.sh` só espelha a pré-condição do `exit 3`; qualquer outra falha do installer de provider ainda derruba o update inteiro depois do core já ter sucedido

- **Fingerprint:** `flow-update-sh-provider-reinstall-aborts-on-non-exit-3-failures`
- **Alvo:** `scripts/update.sh`
- **Evidência:** `scripts/update.sh:107` — "`        bash .dev-team-agents/scripts/install-opencode.sh`" (chamada nua, sem `|| true` e sem captura de código de saída, sob o `set -euo pipefail` do topo do arquivo). Os caminhos de saída não cobertos existem: `scripts/install-opencode.sh:80` — "`  echo "install-opencode: ERROR: jq is required for opencode.json merge." >&2; exit 1`"; `scripts/install-opencode.sh:150` — "`  echo "install-opencode: ERROR: render-provider produced no command snippet." >&2; exit 1`"; `scripts/install-codex.sh:77` — "`  echo "install-codex: ERROR: python3 is required." >&2; exit 1`".
  Reproduzido com o trecho literal das linhas 98–126 num projeto sintético que **passa** no guard:
  ```
  $ cd /tmp/fp && bash run.sh; echo "update.sh exit=$?"
  core update OK
  → opencode config detected, re-running install-opencode.sh...
  install-opencode: ERROR: jq is required for opencode.json merge.
  Exit code 1
  ```
  A linha `POST-STEPS REACHED: cache invalidated + telemetry sent` nunca é impressa.
- **Problema:** o fix escolheu **espelhar a pré-condição** de um código de saída específico em vez de
  **tolerar a falha** da etapa. O guard cobre exatamente `exit 3`; os `exit 1` por dependência
  ausente (`jq`, `python3`) ou por render vazio continuam propagando sob `set -e` e matando o script
  no mesmo ponto, com o mesmo sintoma — update reportado como falho depois do core ter passado.
- **Por que importa:** `jq` ausente é um cenário comum e o guard das linhas 105 não o detecta. Nesse
  caso o `rm -f .context-cache.json` (linha 129), o envio de telemetria de update e o banner final
  não rodam: o usuário fica com a versão nova instalada, cache de contexto obsoleto e a impressão de
  que o update falhou.
- **Proposta:** trocar as duas chamadas por invocação tolerante — `bash …/install-opencode.sh || echo "⚠ opencode re-render failed (exit $?); core update succeeded — run install-provider.sh manually." >&2` — mantendo o guard atual apenas como mensagem melhor para o caso conhecido.
- **Impacto positivo:** o update passa a ser atômico do ponto de vista do usuário: o re-render de
  provider vira etapa best-effort, e cache/telemetria/banner sempre executam.
- **Impacto negativo / risco:** uma falha real e corrigível do re-render deixa de ser barulhenta —
  passa a ser um aviso em `stderr` fácil de perder no meio da saída do update, e o projeto fica com
  `.opencode/` desatualizado sem nada obrigar o usuário a agir.
- **Esforço:** Baixo

### `software-architect` recebeu invariantes que chamam ferramentas exclusivas do Claude Code, sem hedge e sem entrada no `tool-map.json` — e elas chegam literalmente ao agente renderizado do opencode

- **Fingerprint:** `flow-architect-claude-only-async-tool-names-rendered-verbatim`
- **Alvo:** `agents/software-architect.md`, `scripts/lib/tool-map.json`
- **Evidência:**
  - `agents/software-architect.md:89` — "`- **Before ending a turn with an unreturned spawn, call `ScheduleWakeup`** instead of going silent (Spawn Integrity check 5, Auto-reactivation). On wakeup, check `TaskList`/`TaskGet`/`TaskOutput` first; if still no return, resume with `SendMessage` rather than re-spawning or fabricating progress.`" — sob o heading "Non-negotiable spawn invariants"
  - `scripts/lib/tool-map.json` — o bloco `providers.opencode.tool_rewrites` cobre apenas `AskUserQuestion`, `Task`, `TodoWrite`, `WebSearch`, `WebFetch`; não há entrada para `ScheduleWakeup`, `TaskList`, `TaskGet`, `TaskOutput`, `SendMessage` nem `Monitor`
  - Renderização real executada contra o HEAD:
    ```
    $ bash scripts/render-provider.sh --provider opencode --source-dir . --target-dir /tmp/rend
    $ grep -n "ScheduleWakeup\|TaskList\|SendMessage" /tmp/rend/.opencode/agents/software-architect.md
    96:- **Before ending a turn with an unreturned spawn, call `ScheduleWakeup`** … resume with `SendMessage` …
    ```
  - Contraste com a skill, que **tem** o hedge: `skills/architecture/orchestration/SKILL.md:234` — "`If `ScheduleWakeup` is not available in the current context, this check cannot be satisfied — fall`"
- **Problema:** o corpo do agente promove a nomes de ferramenta específicos do Claude Code o status de
  invariante **não negociável**, sem a cláusula de indisponibilidade que a skill canônica carrega. Como
  nenhum desses nomes está no `tool-map.json`, o renderer os copia verbatim para opencode (verificado)
  e para Codex, onde não existem.
- **Por que importa:** um `software-architect` rodando em opencode lê a instrução de "chamar
  `ScheduleWakeup` antes de encerrar o turno" como obrigação. Sem a ferramenta, o desfecho provável é
  o que a própria check 5 proíbe: afirmar que um checkback foi agendado quando não foi.
- **Proposta:** ou adicionar os nomes ao `tool_rewrites`/`idiom_notes` de opencode e Codex, ou
  reescrever a linha 89 delegando ao hedge da skill ("per Spawn Integrity check 5 — including its
  availability fallback"), como as demais linhas de delegação do agente já fazem.
- **Impacto positivo:** fecha um drift entre provedores que nenhum gate pega hoje — `agent-lint.sh`
  não valida nomes de ferramenta e o contract checker de CI só compara estrutura renderizada.
- **Impacto negativo / risco:** listar ferramentas no `tool-map.json` cria mais um mapa para manter
  sincronizado a cada mudança de roster do Claude Code; a alternativa (delegar) encurta o agente mas
  tira da vista do orquestrador a regra que o commit `21fceb4` quis justamente tornar visível.
- **Esforço:** Médio

---

## MEDIUM

### O padrão `make` casa por substring com `cmake` e com qualquer comando encadeado que contenha "test"

- **Fingerprint:** `flow-02c-make-pattern-substring-matches-cmake-and-chained-cmds`
- **Alvo:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`
- **Evidência:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:78-81` —
  ```
  case "$cmd" in
      *make\ *test*|*make\ *-e2e*)
          [[ "$cmd" != *TESTPATH=* && "$cmd" != *FILTER=* && "$cmd" != *--\ * ]] && return 0 ;;
  esac
  ```
  Reproduzido:
  ```
  FLAGGED  : cmake --build . && ./run_tests
  FLAGGED  : make migrate-test-db && vendor/bin/phpunit --filter FooTest
  silent   : make test TESTPATH=tests/Unit/FooTest.php
  ```
- **Problema:** o glob `*make\ *test*` é ancorado em nada. `cmake ` contém `make ` como substring, e
  o `*` do meio atravessa `&&`, então basta a palavra "test" aparecer em qualquer ponto posterior do
  comando. As exclusões (`TESTPATH=`, `FILTER=`, `-- `) são variáveis de Make: não reconhecem
  `--filter`, path, `::` nem `-k`, que são justamente os qualificadores do comando *real* encadeado
  depois do alvo do Make.
- **Por que importa:** um `phpunit --filter` corretamente escopado, encadeado após um alvo de Make de
  preparação, recebe o nudge de "suíte completa não escopada". E projetos C/C++ com `cmake` disparam
  o guard sem qualquer relação com testes. É o mesmo custo do achado anterior: nudge que o agente
  aprende a ignorar.
- **Proposta:** ancorar o padrão no início do comando ou de um segmento (`make `/`^make `/`&& make `),
  e acrescentar `--filter`/`-k`/path às exclusões, ou avaliar apenas o último segmento do comando.
- **Impacto positivo:** elimina duas classes de falso positivo reproduzidas, sem perder a detecção
  legítima de `make test` nu.
- **Impacto negativo / risco:** ancorar por segmento significa fatiar `$cmd` por `&&`/`;`/`|` em
  bash puro — mais código no hot path de *todo* `PreToolUse` de Bash, o oposto da economia de forks
  que o `02-graphify-hint.sh` documenta como princípio do diretório.
- **Esforço:** Médio

### O guard passou a detectar wrappers Make/Composer que a skill citada pelo nudge não sabe escopar — e cujo Makefile ela manda respeitar

- **Fingerprint:** `flow-02c-wrappers-have-no-scoped-row-in-runner-filters-table`
- **Alvo:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`, `skills/shared/scoped-test-execution/SKILL.md`
- **Evidência:**
  - `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:25-27` — "`# Each pattern below is a command shape with NO scope qualifier (no path,`" / "`# no --filter/-k/--tests/-only-testing/-run), matching the "Scoped command"`" / "`# column in scoped-test-execution/SKILL.md's runner table.`"
  - A tabela em `skills/shared/scoped-test-execution/SKILL.md:45-57` tem 11 linhas (`| Jest |` na 47 … `| Cargo | `cargo test <filter>` |` na 57) e **nenhuma** para Make ou Composer; `TESTPATH=` e `FILTER=`, as convenções que o guard usa como prova de escopo, não aparecem em lugar nenhum da skill
  - `skills/shared/scoped-test-execution/SKILL.md:59` — "`When the project defines its own scoped script in `CLAUDE.md`, `package.json`, or a `Makefile`, that command wins over the table.`"
- **Problema:** duas contradições ao mesmo tempo. A primeira: o comentário das linhas 25–27 afirma
  correspondência 1:1 com a tabela da skill, e as três novas cláusulas quebraram essa correspondência
  — o texto virou falso no mesmo commit que o escreveu. A segunda é pior: a linha 59 da skill diz
  explicitamente que um alvo de `Makefile` definido pelo projeto **ganha da tabela**, enquanto o guard
  passou a tratar `make *test*` como suíte completa por padrão.
- **Por que importa:** o nudge da linha 94 manda o agente aplicar "skills/shared/scoped-test-execution/SKILL.md"
  a um `make test`. Ao abrir a skill, o agente encontra (a) nenhuma forma escopada para Make/Composer e
  (b) uma regra dizendo que o script do projeto prevalece. O safety net aponta para um documento que
  não confirma o alerta.
- **Proposta:** acrescentar linhas Make e Composer à tabela Runner Filters (com `TESTPATH=`/`FILTER=`
  e `composer test:<suite>` como formas escopadas) e reescrever o comentário das linhas 25–27 para
  descrever o contrato real, incluindo os wrappers.
- **Impacto positivo:** o agente que recebe o nudge passa a ter uma ação documentada; a afirmação de
  correspondência guard↔skill volta a ser verdadeira.
- **Impacto negativo / risco:** `TESTPATH=`/`FILTER=` são convenções de um projeto específico, não
  padrão de ecossistema — canonizá-las numa skill obrigatória para todo agente injeta na skill mais
  agnóstica do repo um vocabulário que a maioria dos Makefiles não usa.
- **Esforço:** Baixo

### O passo "Commit and push" acrescentado ao prompt de auditoria foi copiado do prompt de métricas e contradiz a regra inviolável 8 do próprio arquivo

- **Fingerprint:** `flow-prompt-auditoria-commit-step-contradicts-branch-rule`
- **Alvo:** `docs/reports/_prompt-auditoria.md`
- **Evidência:**
  - `docs/reports/_prompt-auditoria.md:322` — "`After the two report files are written, commit **only** them and push to `main`.`"
  - `docs/reports/_prompt-auditoria.md:34` — "`8. Trabalhe e faça push apenas na branch designada da sessão.`"
  - `docs/reports/_prompt-auditoria.md:244-253` — a tabela de saída do protocolo lista **oito** arquivos, de `| Ordem | Arquivo | Conteúdo |` (244) até "`| 8 | `_index.md` (raiz de reports) | Banco de fingerprints |`" (253), não dois
  - `docs/reports/_prompt-auditoria.md:348` — "`  git -c commit.gpgsign=false commit --no-gpg-sign -m "docs(reports): metrics reports updates"`"
  - `docs/reports/_prompt-auditoria.md:342` — "`git add file1 file2 ....`"
- **Problema:** o bloco foi transplantado literalmente do prompt de métricas do PostHog (o commit
  `f88ee51` diz "Both the English and pt-BR PostHog metrics report prompts") sem adaptação: fala em
  "the two report files" num protocolo que produz oito, hardcoda `push … main` contra a regra 8 que
  manda usar a branch designada da sessão, e prescreve a mensagem de commit `"docs(reports): metrics
  reports updates"` — errada para um pass de auditoria. O arquivo ainda termina sem newline final.
- **Por que importa:** este é o prompt que dirige o pass de auditoria diário. Um agente que siga
  "Run exactly" empurra para `main` desobedecendo a regra 8 do mesmo documento, e — seguindo "the two
  report files" ao pé da letra — pode deixar seis dos oito arquivos fora do commit.
- **Proposta:** parametrizar o bloco: "commit os arquivos de `docs/reports/<DATA>/` mais `_index.md`",
  push na branch designada da sessão (a mesma da regra 8), e mensagem no padrão
  `docs(reports): add the <DATA> guardian audit pass`.
- **Impacto positivo:** remove a única contradição interna do protocolo e alinha o passo final com a
  regra 8 e com a tabela de saída.
- **Impacto negativo / risco:** parametrizar troca um bloco "Run exactly" copiável por um que exige
  substituição pelo agente — abre espaço para erro de preenchimento onde hoje havia comando literal;
  e a regra 8 não define onde a "branch designada" é declarada, então a ambiguidade se desloca.
- **Esforço:** Baixo

---

## LOW-MEDIUM

### `Monitor` foi elevado a "única forma legítima" de acompanhar um processo de background sem a cláusula de indisponibilidade que a check 5 vizinha carrega

- **Fingerprint:** `flow-background-process-discipline-monitor-no-availability-fallback`
- **Alvo:** `skills/architecture/orchestration/SKILL.md`
- **Evidência:** `skills/architecture/orchestration/SKILL.md:246-249` — "`- **Never open a new `sleep`/poll-loop Bash command to re-check something already being waited`" / "`  on.** A background command already running (a build, a test suite, a migration) has exactly one`" / "`  legitimate way to be watched: `Monitor` on that same command.`". Comparar com `skills/architecture/orchestration/SKILL.md:234` — "`If `ScheduleWakeup` is not available in the current context, this check cannot be satisfied — fall`". `Monitor` também não consta de `scripts/lib/tool-map.json`.
- **Problema:** a seção nova, escrita seis linhas abaixo de uma que trata explicitamente o caso
  "ferramenta indisponível", proíbe a alternativa (`sleep`/poll) em termos absolutos e nomeia como
  única saída uma ferramenta que pode não existir na sessão — e que, sem entrada no `tool-map.json`,
  chega verbatim ao opencode e ao Codex.
- **Por que importa:** onde `Monitor` não existe, a regra fecha as duas saídas de uma vez: proíbe o
  poll e prescreve o que não pode ser chamado. Um agente que a leve a sério fica sem forma de
  acompanhar um build em background.
- **Proposta:** acrescentar uma linha simétrica à da check 5 — se `Monitor` não estiver disponível,
  aguardar o comando inline e dizer isso, em vez de abrir um segundo shell de polling.
- **Impacto positivo:** torna a seção executável em qualquer provedor e alinha o padrão de hedge
  dentro do mesmo arquivo.
- **Impacto negativo / risco:** abre uma brecha declarada na proibição, que é exatamente o que a
  seção quis fechar — um agente pode usar "Monitor indisponível" como desculpa para o poll-loop.
- **Esforço:** Baixo

### Uma regra geral de paralelismo de chamadas Bash foi hospedada dentro da skill de escopo de testes, e ela mesma admite duplicar a regra de spawn

- **Fingerprint:** `flow-parallel-bash-rule-homed-in-scoped-test-execution-skill`
- **Alvo:** `skills/shared/scoped-test-execution/SKILL.md`
- **Evidência:** `skills/shared/scoped-test-execution/SKILL.md:63` — "`## Run Independent Verification Commands in Parallel`"; `:65` — "`Tests, linters, and static analysis are independent of each other … This is the same "no dependency → parallel tool calls" rule this repo already applies to agent spawning; it applies equally to your own Bash calls within one task.`"
- **Problema:** o escopo da regra (testes **+ linters + análise estática**) é mais largo que o da
  skill que a hospeda, e o texto declara no próprio corpo que está reafirmando uma regra já existente
  em outro lugar — exatamente o padrão que o `CLAUDE.md` proíbe em "Canonical Rule Homes — Delegate,
  Never Restate". As casas canônicas de paralelismo hoje são `skills/architecture/orchestration/SKILL.md`
  (spawn paralelo) e o `CLAUDE.md` § *Parallel Execution After Approval*.
- **Por que importa:** o custo hoje é baixo — `project-context` § Test Execution obriga o load da
  skill para todo agente — mas cria a terceira cópia de uma regra de paralelismo e o risco de drift
  entre as três, sem gate que pegue. Um fluxo que rode só lint (revisor, docs) encontra a regra num
  documento cujo título diz "scoped **test** execution".
- **Proposta:** mover a seção para a casa canônica de paralelismo (orquestração ou
  `token-efficiency`) e deixar em `scoped-test-execution` uma linha de referência, como o repositório
  já faz para o Task Closure Rule e a cascata de worktree.
- **Impacto positivo:** uma cópia só da regra, alcançável por fluxos que não rodam testes.
- **Impacto negativo / risco:** afastar a regra do ponto onde ela mais se aplica (o momento de rodar
  teste + lint) reduz a chance de ser lida na hora certa; e `orchestration` é skill de orquestrador,
  não de todo agente, o que pode diminuir o alcance efetivo em vez de aumentar.
- **Esforço:** Baixo

---

## LOW

Nenhum achado original nesta severidade.

---

## Descartados por duplicação

| Candidato | Porta | Motivo |
|---|---|---|
| Captura gulosa do `sed` na linha 22 do `02c` absorvendo chaves irmãs do payload | Porta de estado | `auto-full-suite-guard-sed-absorbs-sibling-json-keys` já está no conjunto aberto; os achados novos deste eixo tratam da função `is_full_suite`, não do parsing |
| Comentário da linha 18 do `02c` citando `02-graphify-hint.sh` como precedente de pure-bash | Porta literal + estado | `docs-sync-02c-comment-cites-graphify-hint-as-sed-precedent`, aberto |
| Dois sub-scripts de `PreToolUse` emitindo `hookSpecificOutput` concatenado e produzindo JSON inválido | Porta 4 (hipótese refutada) | `02-graphify-hint.sh:14-18` dispara só em `Glob`/`Grep` e `02c:12-15` só em `Bash` — mutuamente exclusivos, não reproduz |
| `session-start.sh` monolítico sem padrão de sub-scripts | Porta de estado | `flow-session-start-118-lines-monolithic-no-modular-pattern-asymmetric-with-stop-dispatcher`, aberto |
| `install.sh` grande demais e não fragmentado | Porta de estado | `token-install-sh-503-lines-largest-single-script-not-fragmented…`, aberto |
| `update.sh` sem verificação de integridade do installer | Porta semântica (a+b) | `auto-update-no-integrity-check`, mesmo alvo e mesma causa — e já ✅ Executed via `installer-fetch.sh` |
| Dispatchers executando qualquer `.sh` solto no diretório | Porta semântica | `flow-stop-dispatcher-globs-all-sh-no-allowlist…` — refutado no HEAD: ambos os dispatchers têm `SUBSCRIPT_RE` |
