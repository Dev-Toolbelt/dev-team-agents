# Eixo C — Fluxos, comandos e automação (2026-08-21)

**Baseline:** `HEAD` = `a67cac9` · **Baseline anterior:** `c03f898`

Escopo auditado: `commands/*.md`, `scripts/hooks/**`, `scripts/install.sh`, `scripts/new-adr.sh`, `scripts/lib/commands.json`. Prioridade no delta `c03f898..HEAD` (33 commits). Todos os achados abaixo foram reproduzidos mecanicamente ou têm citação literal do HEAD.

---

## HIGH

### O dispatcher PreToolUse sai com 141 (SIGPIPE) em payloads grandes e mascara o `exit 2` de bloqueio do `02c`

- **Fingerprint:** `flow-pre-tool-use-dispatcher-sigpipe-141-masks-02c-block`
- **Alvo:** `scripts/hooks/pre-tool-use.sh` + `scripts/hooks/pre-tool-use/02-graphify-hint.sh`
- **Evidência:**
  - `scripts/hooks/pre-tool-use.sh:31` — "`    echo "$INPUT" | env -u BASH_ENV -u ENV bash "$script" || SCRIPT_EXIT=$?`"
  - `scripts/hooks/pre-tool-use.sh:33-35` — "`    if [ "$SCRIPT_EXIT" -ne 0 ] && [ "$EXIT_CODE" -eq 0 ]; then`" / "`        EXIT_CODE=$SCRIPT_EXIT`"
  - `scripts/hooks/pre-tool-use/02-graphify-hint.sh:13-14` — "`GRAPH="graphify-out/graph.json"`" / "`[ -f "$GRAPH" ] || exit 0`"
  - `scripts/hooks/pre-tool-use/02-graphify-hint.sh:22` — "`INPUT=$(cat)`" (só depois do `exit 0` acima)
- **Problema:** o dispatcher entrega o payload por **pipe**. `02-graphify-hint.sh` sai na linha 14 (projeto sem `graphify-out/graph.json` — o caso comum) e na linha 20 (marcador já escrito) **antes** de consumir stdin. Quando o payload excede o buffer do pipe (64 KB), o `echo` do dispatcher morre com SIGPIPE; com `pipefail`, o status do pipeline vira 141, o dispatcher grava `EXIT_CODE=141` e sai com 141.

  Pior: a regra é **primeiro não-zero vence** (`&& [ "$EXIT_CODE" -eq 0 ]`), e a ordem alfabética coloca `02-graphify-hint.sh` **antes** de `02c-full-suite-guard.sh`. O `exit 2` bloqueante que `abb8483` acabou de introduzir é sobrescrito por um 141 espúrio.

  Reproduzido ponta a ponta com o dispatcher e os sub-scripts reais do HEAD, fora de projeto com graphify:

  ```
  # payload 300 KB, tool_name=Bash, command="npm test", árvore limpa, sem commits hoje
  A) payload pequeno  -> exit = 2    stderr: "scoped-test-execution: BLOCKED — ..."
  B) payload 300 KB   -> exit = 141  stderr: "scoped-test-execution: BLOCKED — ..."
  ```

  Em (B) a mensagem de bloqueio continua indo para stderr, mas o código de saída deixa de ser 2 — o Claude Code **não bloqueia** a chamada. A guarda degrada de bloqueio para aviso exatamente nos payloads maiores.
- **Por que importa:** dois efeitos ao mesmo tempo. (1) Todo `Write`/`Edit` de arquivo grande em qualquer projeto sem graphify produz um erro de hook não-zero silencioso. (2) A funcionalidade central do commit `abb8483` falha aberta de forma dependente do tamanho do payload — o tipo de bug que nunca aparece em teste manual, porque payloads de teste são pequenos.
- **Proposta:** adotar no `pre-tool-use.sh` o mesmo mecanismo que o `stop.sh` já usa e que `02b-telemetry.sh:19-20` documenta como a diferença entre os dois dispatchers: gravar o payload num `mktemp`, exportar `DEVTEAM_HOOK_PAYLOAD` e redirecionar `< "$HOOK_TMP"` em cada sub-script (`scripts/hooks/stop.sh:16-18`). Alternativa mínima: manter o pipe e mover `INPUT=$(cat)` para a primeira linha executável de `02-graphify-hint.sh`, antes de qualquer `exit 0`. A troca por tempfile é a correção estrutural — resolve para qualquer sub-script futuro que saia cedo.
- **Impacto positivo:** o `exit 2` do `02c` volta a bloquear em 100% dos casos; somem os 141 espúrios; os dois dispatchers passam a usar o mesmo contrato de payload.
- **Impacto negativo / risco:** o tempfile exige `trap ... EXIT` para limpeza (o `stop.sh` já tem o padrão pronto) e cria um arquivo por chamada de ferramenta — volume alto em `/tmp`. Se a correção mínima for escolhida em vez do tempfile, o problema volta no próximo sub-script que saia antes do `cat`.
- **Esforço:** Baixo

### `/devteam:merge` resolve branch e árvore de trabalho **antes** de detectar o worktree — o caminho worktree é inalcançável a partir de qualquer cwd

- **Fingerprint:** `flow-merge-md-branch-and-tree-resolved-before-worktree-detection`
- **Alvo:** `commands/merge.md`
- **Evidência:**
  - `commands/merge.md:16` — "`git status --porcelain`" (Step 0, pre-flight de alterações não commitadas)
  - `commands/merge.md:28` — "`git branch --show-current`" (Step 1)
  - `commands/merge.md:34` — "- If the current branch **is** the default branch: there is nothing to merge from — tell the user and stop."
  - `commands/merge.md:49` — "`cat .dev-team-agents/.worktree-session 2>/dev/null`" (Step 2, só depois do stop acima)
- **Problema:** o comando roda `git` sem `-C` e lê `.dev-team-agents/` por caminho relativo, sem em momento nenhum resolver a raiz do repositório principal (`git rev-parse --git-common-dir`), que é o que `scripts/hooks/session-start.sh:16` e `scripts/hooks/pre-tool-use/02-graphify-hint.sh:17` fazem. As duas leituras possíveis de cwd quebram:

  Reproduzido em repo com worktree vinculado (`main` + `auth/add-oauth`, `.dev-team-agents/.worktree-session` = `worktree=yes branch=auth/add-oauth`):

  ```
  --- cwd = árvore principal (a convenção do skill: worktree/SKILL.md:54 manda commitar com `git -C <wt-path>`) ---
  git branch --show-current  -> main            # = default branch  => Step 1 PARA: "nothing to merge"
  git status --porcelain     -> [?? .dev-team-agents/]   # não enxerga o trabalho sujo dentro do worktree
  --- cwd = dentro do worktree ---
  ls .worktree/.dev-team-agents -> No such file or directory   # gitignorado, existe só na árvore principal
  ```

  Ou seja: a partir da árvore principal o comando **aborta no Step 1** antes de ler `.worktree-session`; a partir do worktree, o Step 2 não encontra o arquivo de sessão e cai no ramo "plain feature branch, no isolation", nunca oferecendo rebase/teardown. O Step 0 é cego para o único lugar onde há trabalho pendente.
- **Por que importa:** worktree-aware finalization é *a* razão de existir do comando (`b0383d6`). O autor conhecia a distinção — `commands/merge.md:77` diz explicitamente "if `git status --porcelain` **inside the worktree** is non-empty" —, mas os Steps 0 e 1 não receberam o mesmo tratamento, e a ordem dos passos coloca a detecção depois do abort.
- **Proposta:** promover a detecção de worktree para Step 0: resolver `MAIN_ROOT="$(cd "$(git rev-parse --git-common-dir)/.." && pwd)"`, ler `$MAIN_ROOT/.dev-team-agents/.worktree-session`, e só então derivar branch e status — com `git -C <wt-path>` quando `worktree=yes`. O `current-context` skill, que o comando já carrega na linha 7, é o lugar natural para essa resolução se ela ainda não existir lá.
- **Impacto positivo:** o comando passa a funcionar no cenário para o qual foi escrito, e o pre-flight de Step 0 passa a inspecionar a árvore que realmente tem trabalho.
- **Impacto negativo / risco:** o Step 1 deixa de ter uma checagem simples "estou na default branch?" e passa a depender de resolução de duas árvores — mais superfície para errar quando não há worktree. Exige um caso de teste explícito para o caminho sem worktree, hoje o único que funciona.
- **Esforço:** Médio

### O teste de "ancestor" do nudge de `/devteam:learn` está invertido e foi replicado em quatro comandos

- **Fingerprint:** `flow-learn-nudge-ancestor-test-inverted-in-four-commands`
- **Alvo:** `commands/merge.md`, `commands/pr.md`, `commands/refactor.md`, `commands/audit.md`
- **Evidência:**
  - `commands/merge.md:89` — "If the marker is absent, or its recorded commit hash is **not an ancestor** of the current `HEAD` (i.e. commits landed since the last learn run), tell the user before finishing:"
  - `commands/pr.md:148` — texto idêntico
  - `commands/refactor.md:162` — "If the marker is absent, or its recorded commit hash is not an ancestor of the current `HEAD`, ask via `AskUserQuestion`…"
  - `commands/learn.md:166` — "`echo "$(git log -1 --format=%ct 2>/dev/null || date +%s) $(git rev-parse HEAD 2>/dev/null)" > .dev-team-agents/.learn-last-run`"
- **Problema:** o marcador grava o `HEAD` do momento em que `/devteam:learn` rodou. Se commits aterrissaram depois, esse hash **é** ancestral do `HEAD` atual — que é exatamente o caso em que o nudge deveria disparar. A condição escrita é a negação disso, e o parêntese explicativo ("i.e. commits landed since the last learn run") afirma como equivalente algo que é o oposto.

  Reproduzido:

  ```
  recorded=b8cf74e (HEAD no momento do learn); +2 commits; head=ccb44bd
  git merge-base --is-ancestor b8cf74e HEAD  -> 0 (É ancestral)
  => condição de merge.md:89 FALSA => NENHUM nudge
  git rev-list --count b8cf74e..HEAD         -> 2 commits desde o learn
  ```

  O nudge só dispara no caso oposto — quando o hash gravado deixou de ser ancestral, isto é, após um rebase/amend que órfã o commit. Ironia: o caminho recomendado do próprio `/devteam:merge` faz rebase antes do Step 4, então ali o nudge dispara por acidente, pelo motivo errado.
- **Por que importa:** `7e62124` acabou de criar a Learn Trigger Rule e propagou o mesmo texto para três arquivos, transformando um erro lógico em quatro pontos de falha. O mecanismo inteiro fica desligado no caminho normal — a captura de conhecimento que a regra existe para proteger é justamente a que se perde.
- **Proposta:** trocar por igualdade simples: disparar quando o marcador estiver ausente **ou** `[ "$(cut -d' ' -f2 .learn-last-run)" != "$(git rev-parse HEAD)" ]`. Corrigir nos quatro pontos no mesmo commit (o próprio `CLAUDE.md` § Learn Trigger Rule manda "patch all of them together").
- **Impacto positivo:** o nudge passa a disparar quando há o que capturar e a ficar quieto quando não há.
- **Impacto negativo / risco:** o nudge passa a aparecer com muito mais frequência (toda sessão com commit e sem learn), o que pode virar ruído em fluxos que rodam `/devteam:pr` várias vezes. Vale considerar limitar a um disparo por sessão.
- **Esforço:** Baixo

---

## MEDIUM-HIGH

### A escotilha de escape do `02c` exige o marcador na posição 0, enquanto a detecção casa substring em qualquer posição

- **Fingerprint:** `flow-02c-escape-hatch-anchored-while-detection-is-substring`
- **Alvo:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`
- **Evidência:**
  - `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:41-43` — "`case "$COMMAND" in`" / "`    DEVTEAM_FULL_SUITE_CONFIRMED=1\ *) exit 0 ;;`" / "`esac`"
  - `:59` — "`        *pnpm\ test*|*npm\ test*|*npm\ run\ test*|*yarn\ test*|*bun\ test*)`" (sem âncora)
  - `:122` — "reissue the command prefixed with DEVTEAM_FULL_SUITE_CONFIRMED=1 (e.g. 'DEVTEAM_FULL_SUITE_CONFIRMED=1 npm test')"
- **Problema:** a detecção é substring solta — casa `npm test` em qualquer ponto da string, inclusive depois de `cd`, `&&` ou dentro de `sh -c "..."`. A escotilha, ao contrário, só casa com o marcador **no início absoluto** do comando. Resultado: comandos que a guarda bloqueia não conseguem usar a saída documentada.

  Reproduzido extraindo `is_full_suite()` do HEAD:

  ```
  full=YES hatch=no  :: cd frontend && npm test
  full=YES hatch=YES :: DEVTEAM_FULL_SUITE_CONFIRMED=1 npm test
  full=YES hatch=no  :: cd frontend && DEVTEAM_FULL_SUITE_CONFIRMED=1 npm test
  full=YES hatch=no  :: export DEVTEAM_FULL_SUITE_CONFIRMED=1; npm test
  full=YES hatch=no  :: docker compose exec app sh -c "DEVTEAM_FULL_SUITE_CONFIRMED=1 pytest"
  ```
- **Por que importa:** em monorepo (`cd frontend && npm test`) ou stack conteinerizada (`docker exec ... sh -c "..."`) — as duas formas que o comentário da linha 29 do próprio arquivo cita como motivo do `sed` guloso — o usuário fica sem escape. Um bloqueio sem saída viável é o padrão que leva alguém a desativar o hook inteiro.
- **Proposta:** trocar o `case` ancorado por um teste de substring simétrico ao da detecção: `case "$COMMAND" in *DEVTEAM_FULL_SUITE_CONFIRMED=1*) exit 0 ;; esac`. Alternativa mais limpa: checar a variável de ambiente `${DEVTEAM_FULL_SUITE_CONFIRMED:-}` — mas ela não chega ao hook, então o teste na string é o caminho.
- **Impacto positivo:** a escotilha cobre todas as formas que a detecção cobre; a mensagem de bloqueio da linha 122 deixa de instruir algo que falha na prática.
- **Impacto negativo / risco:** substring solta afrouxa o bloqueio — um comando com o marcador em comentário ou em outra sub-shell escapa. É a mesma classe de imprecisão que a detecção já aceita, então a assimetria some, mas nenhum dos dois lados fica rigoroso.
- **Esforço:** Baixo

### Documentação da preference `auto_learn_before_commit` continua descrevendo o Step 0 pré-commit que `576dcfa` removeu

- **Fingerprint:** `docs-sync-auto-learn-before-commit-still-documented-as-pre-commit-step-0`
- **Alvo:** `CLAUDE-md/preferences.md`, `skills/shared/user-preferences/SKILL.md`
- **Evidência:**
  - `CLAUDE-md/preferences.md:55` — "| `auto_learn_before_commit` | `true` | When `true`, `/devteam:commit` **Step 0** auto-runs `/devteam:learn` **before committing** so knowledge capture is never forgotten. …"
  - `skills/shared/user-preferences/SKILL.md:70` — "| `auto_learn_before_commit` | bool | `true` | Auto-run `/devteam:learn` **before** every commit (`false` = skip by default) |"
  - `commands/commit.md:175` — "`## Step 6 — Auto knowledge capture`" (e `:177` referencia a mesma chave)
- **Problema:** `576dcfa` moveu a captura de Step 0 (antes dos commits) para Step 6 (depois dos commits e de qualquer finalize de worktree), mas nenhum dos dois espelhos da schema foi corrigido. Os dois afirmam como verdadeiro um passo que não existe mais e uma ordem que é a inversa da atual. `skills/shared/user-preferences/SKILL.md` é lido por agentes — não é documentação passiva.

  O nome da chave (`auto_learn_**before**_commit`) também passou a descrever o contrário do comportamento, e é canônico em `scripts/lib/preferences-defaults.json:18`.
- **Por que importa:** a Auto-Docs Rule do `CLAUDE.md` exige atualizar os espelhos na mesma sessão da mudança de comportamento; `scripts/lib/preferences-defaults.json` é declarado single source of truth com uma tabela explícita de espelhos a patchear junto — e o commit passou por ela sem gate nenhum. É a segunda ocorrência da mesma classe de drift nesse conjunto de arquivos.
- **Proposta:** corrigir as duas linhas para "Step 6 — auto-runs `/devteam:learn` **after** the commits (and after any worktree finalize)". Quanto ao nome da chave: manter `auto_learn_before_commit` como alias e adicionar uma nota de uma linha explicando a divergência, ou renomear para `auto_learn_on_commit` com backfill no `session-start.sh` — a segunda opção é mais limpa mas mexe em arquivo de usuário.
- **Impacto positivo:** os agentes que leem `user-preferences/SKILL.md` param de receber uma ordem de passos errada.
- **Impacto negativo / risco:** renomear a chave exige tocar os cinco espelhos listados no `CLAUDE.md` e uma migração no backfill do `session-start.sh`; feito pela metade, cria uma preference fantasma que ninguém lê.
- **Esforço:** Baixo (só o texto) / Médio (com rename)

### `CLAUDE.md` ainda diz "sete" comandos sem agente e omite `push` e `merge`; `commands.json` diz nove

- **Fingerprint:** `flow-claude-md-no-agent-command-list-says-seven-omits-push-and-merge`
- **Alvo:** `CLAUDE.md`, `scripts/lib/commands.json`
- **Evidência:**
  - `CLAUDE.md:258` — "`/devteam:update`, `/devteam:symlinks`, `/devteam:health-check`, `/devteam:install`, `/devteam:explain`, `/devteam:version` and `/devteam:status` spawn **no** agent; … All seven name `technical-writer` … Do not read those seven rows as a delegation target."
  - `scripts/lib/commands.json:7` — "`_filler_agent_note`: "`update`, `symlinks`, `health-check`, `install`, `explain`, `push`, `merge`, `version` and `status` spawn NO agent. … all **nine** name `technical-writer` …""
- **Problema:** `b0383d6` atualizou a tabela de comandos e a lista de exceções de plan gate no `CLAUDE.md`, e atualizou o `_filler_agent_note` no `commands.json` para nove — mas o parágrafo da linha 258 ficou em sete. `push` já estava faltando antes de `merge`; agora são duas omissões. As duas notas são o mesmo fato declarado em dois lugares e discordam.
- **Por que importa:** a linha 258 é a instrução que diz explicitamente "do not read those rows as a delegation target". Um leitor que confie nela conclui que a linha `merge` de `commands.json` (`"agent": "technical-writer"`) é um alvo real de delegação — exatamente o erro que a nota existe para prevenir. `helpers/agent-lint.sh` valida tier↔agent, não a enumeração em prosa, então nada pega isso.
- **Proposta:** substituir a enumeração em prosa por uma referência ao `_filler_agent_note` do `commands.json` (fonte única), ou — se a duplicação for para ficar — acrescentar ao `check_command_roster` uma verificação de que todo comando com `agent` de preenchimento aparece nas duas listas.
- **Impacto positivo:** elimina uma contradição entre dois documentos canônicos e fecha um caminho de leitura que produz delegação errada.
- **Impacto negativo / risco:** apontar para o `commands.json` reduz a legibilidade do `CLAUDE.md` (o leitor precisa abrir um segundo arquivo). Um gate no lint é mais robusto, mas exige parsear prosa — frágil.
- **Esforço:** Baixo

---

## MEDIUM

### `/devteam:merge` diz "rebase onto `<target>`" mas delega ao passo do skill que faz rebase onto `<base>`

- **Fingerprint:** `flow-merge-md-rebases-onto-target-while-delegating-to-base-step-8`
- **Alvo:** `commands/merge.md`, `skills/shared/worktree/SKILL.md`
- **Evidência:**
  - `commands/merge.md:57` — "- **Commit + rebase onto `<target>` + merge + teardown** (recommended) — delegate entirely to `skills/shared/worktree/SKILL.md` § Worktree Setup step 8 … Do not reimplement that sequence here — load the skill and follow it."
  - `skills/shared/worktree/SKILL.md:55` — "8. Finalize on merge: rebase onto **base** → resolve → commit → merge → **dirty-worktree guard** … → teardown worktree + isolated Docker stack only"
  - `commands/merge.md:36-40` — o `<target>` vem de uma pergunta ao usuário (`AskUserQuestion`), que pode escolher **Other** e digitar qualquer branch
- **Problema:** `<target>` e `<base>` não são o mesmo conceito. `base` é o branch de origem do worktree, resolvido por `worktree_base_branch` → project config → default branch detectado (`SKILL.md:50`). `target` é o destino do merge escolhido no Step 1. Quando divergem — merge de uma feature num branch de release, por exemplo — o comando promete rebase em `<target>` e o passo delegado faz rebase em `<base>`. Uma das duas coisas acontece, e a instrução não diz qual.
- **Por que importa:** rebase no branch errado é destrutivo e difícil de desfazer, e é o caminho marcado como "(recommended)". O texto ainda reforça "delegate entirely" e "do not reimplement", o que empurra o agente para o passo 8 — ou seja, para `base` — enquanto a etiqueta da opção que o usuário leu dizia `target`.
- **Proposta:** decidir explicitamente. Ou (a) o Step 2 detecta `base` e, quando `base != target`, avisa e pergunta em qual rebasear; ou (b) a opção passa a se chamar "Commit + rebase onto the worktree base + merge into `<target>` + teardown", deixando claro que são duas branches distintas.
- **Impacto positivo:** remove ambiguidade do único caminho destrutivo do comando.
- **Impacto negativo / risco:** a opção (a) acrescenta uma pergunta a um comando que já faz três — custo de UX real num fluxo que se quer rápido.
- **Esforço:** Baixo

### O nudge de `/devteam:learn` não tem casa canônica: três cópias inline e uma referência a `merge.md` que não resolve em nenhum provider

- **Fingerprint:** `flow-learn-nudge-has-no-canonical-skill-home-three-inline-copies`
- **Alvo:** `CLAUDE.md`, `commands/audit.md`, `commands/pr.md`, `commands/refactor.md`
- **Evidência:**
  - `CLAUDE.md` § Learn Trigger Rule — "The canonical nudge implementation is `commands/merge.md` § Step 4 … The following commands carry the same check at their own closing point — patch all of them together if the mechanism ever changes"
  - `commands/audit.md:188` — "3. Nudge `/devteam:learn` per the merge.md Step 4 marker check (`.dev-team-agents/.learn-last-run`) …"
  - `commands/pr.md:140-152` e `commands/refactor.md:162` — cópias inline do mesmo bloco
- **Problema:** o `CLAUDE.md` designa um **corpo de comando** como casa canônica de uma regra usada por quatro comandos, contrariando sua própria doutrina ("A rule that applies to more than one agent lives in exactly **one** skill … When a duplicated rule is found, delete the copy — do not 'reconcile' the two wordings"). A mitigação declarada é manual ("patch all of them together") e já falhou na primeira oportunidade: o achado HIGH acima é o mesmo erro lógico replicado nas três cópias.

  A referência de `audit.md:188` também não resolve em runtime: num projeto instalado o arquivo é `.claude/commands/devteam/merge.md`, e no Codex a superfície é `.codex/skills/devteam-merge/SKILL.md` — nenhum dos dois é "merge.md".
- **Por que importa:** é a única entrada da Learn Trigger Rule que não aparece na tabela "Canonical Rule Homes — Delegate, Never Restate", e é exatamente o padrão que aquela tabela existe para impedir. Sem skill, não há alvo único para corrigir nem para o `orphan-skill-scan` enxergar.
- **Proposta:** extrair para `skills/shared/learn-nudge/SKILL.md` (ou uma seção em `skills/shared/docs-sync/SKILL.md`, que já é a casa da Task Closure Rule), com o comando de checagem e o texto da pergunta; os quatro comandos passam a carregar o skill em uma linha. Acrescentar a linha correspondente à tabela de Canonical Rule Homes.
- **Impacto positivo:** um ponto de correção em vez de quatro; a próxima mudança de mecanismo não depende de disciplina manual.
- **Impacto negativo / risco:** mais um skill compartilhado a carregar em quatro comandos — custo de contexto pequeno mas real, e `pr.md`/`refactor.md` já carregam vários.
- **Esforço:** Baixo

### `/devteam:fix` é o único comando de implementação sem handoff para `code-reviewer` + `qa-specialist`

- **Fingerprint:** `flow-fix-md-only-implementation-command-without-review-qa-handoff`
- **Alvo:** `commands/fix.md`
- **Evidência:**
  - `commands/fix.md` (42 linhas, arquivo inteiro) — `grep -n "code-reviewer\|qa-specialist" commands/fix.md` retorna **zero** ocorrências; o fluxo termina em "Phase 1b — … spawn the matching developer agent(s) in parallel to fix the bug until those tests … are green" (`:30`)
  - `commands/backend.md:42-43`, `commands/frontend.md:33-34`, `commands/fullstack.md:41-42`, `commands/mobile.md:33-34` — todos com "- `code-reviewer` — scope: all files changed this session (`git diff` against the base branch)" e "- `qa-specialist` — scope: validate the behavior of the changes against acceptance criteria and regression risk"
  - `commands/refactor.md` — Phase 4 é `code-reviewer`/`qa-specialist` (citada em `:168`)
- **Problema:** cinco comandos que escrevem código de produção terminam em review + QA obrigatórios; `fix.md` termina no desenvolvedor. A tabela do `CLAUDE.md` registra a ausência ("`/devteam:fix` | backend-developer¹ + frontend-developer¹ + mobile-developer¹ → test-specialist²"), mas em nenhum lugar há a razão — é uma condicional implícita que deveria ser explícita.
- **Por que importa:** correção de bug é a classe de mudança com maior risco de regressão por unidade de linha alterada, e é onde `qa-specialist` (que valida comportamento observável contra critérios) tem mais retorno. Quando `TESTS_REQUIRED=no`, `fix.md` não tem **nenhum** gate após a alteração: sem teste, sem review, sem QA.
- **Proposta:** ou acrescentar a fase de handoff igual à dos irmãos (condicionada ao mesmo "no user confirmation" que `fullstack.md:102` documenta), ou — se a omissão for deliberada, para manter o comando rápido — registrar a razão numa linha do próprio `fix.md` e no `_comment` da linha `fix` de `commands.json`, para que a próxima auditoria não trate como esquecimento.
- **Impacto positivo:** fecha o único caminho de escrita de código sem gate de verificação; ou, na segunda opção, converte um silêncio em decisão registrada.
- **Impacto negativo / risco:** acrescentar dois agentes encarece e alonga o comando que hoje é o mais barato dos cinco — para um one-liner de correção pode ser desproporcional. Uma condicional por tamanho de diff seria melhor, mas acrescenta lógica ao comando.
- **Esforço:** Baixo

### `/devteam:pr` deriva a default branch do config **global** do git e cai num literal `main`

- **Fingerprint:** `flow-pr-md-default-branch-falls-back-to-global-config-then-literal-main`
- **Alvo:** `commands/pr.md`
- **Evidência:**
  - `commands/pr.md:60-63` — "`DEFAULT_BRANCH=$(gh repo view --json defaultBranchRef -q '.defaultBranchRef.name' 2>/dev/null \`" / "`              || git config init.defaultBranch 2>/dev/null \`" / "`              || git remote show origin 2>/dev/null | awk '/HEAD branch/{print $NF}' \`" / "`              || echo "main")`"
  - `commands/merge.md:32` — "The second command … gives the **default branch** — never hardcode `main`, `master`, `beta`, or `develop`."
  - `skills/shared/worktree/SKILL.md:109` — "**Never** hardcode `main`, `master`, or `beta` as base — resolve from `worktree_base_branch`, project config, or the auto-detected default branch"
- **Problema:** dois defeitos na mesma cadeia. (1) `git config init.defaultBranch` é uma preferência **global da máquina** para nomear branches em `git init` — não tem relação nenhuma com a default branch deste repositório; ela vem antes do `git remote show origin`, que é a fonte correta, e frequentemente está setada como `main` mesmo em repos cuja default é `develop` ou `beta`. (2) O último elo é o literal `main`, exatamente o que o `merge.md` recém-escrito e o worktree skill proíbem.
- **Por que importa:** `DEFAULT_BRANCH` alimenta `git log ${DEFAULT_BRANCH}..HEAD` (`:80`), `git diff ${DEFAULT_BRANCH}...HEAD --stat` (`:99`) e a base do PR (`:124`). Num repo cuja default é `beta`, o resultado é um range inválido (log/diff vazios ou erro) e um PR aberto contra a branch errada. `merge.md` mostra a forma correta (`git symbolic-ref refs/remotes/origin/HEAD`), no mesmo delta.
- **Proposta:** substituir a cadeia por `git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'` como primeiro fallback depois de `gh`, remover `git config init.defaultBranch` da cadeia e, no lugar do `echo "main"`, perguntar ao usuário via `AskUserQuestion` quando nada resolver.
- **Impacto positivo:** alinha `pr.md` à regra que o resto do repo já segue e elimina uma fonte silenciosa de PR contra a base errada.
- **Impacto negativo / risco:** `symbolic-ref refs/remotes/origin/HEAD` não existe em clones onde nunca se rodou `git remote set-head`; sem o literal final, o comando passa a perguntar em casos em que hoje "adivinha certo". É o trade-off correto, mas é uma pergunta a mais.
- **Esforço:** Baixo

---

## LOW-MEDIUM

### A opção "Merge only" do `/devteam:merge` remete a uma "follow-up choice" que o comando nunca define

- **Fingerprint:** `flow-merge-md-merge-only-option-cites-undefined-follow-up-choice`
- **Alvo:** `commands/merge.md`
- **Evidência:** `commands/merge.md:59` — "- **Merge only (assume already committed)** — skip commit, run the merge from whichever of the two paths above was implied by **a follow-up choice**."
- **Problema:** não há pergunta de follow-up em lugar nenhum do arquivo. O Step 3 (`:77`) diz "Follow exactly what was confirmed in Step 2" — mas o Step 2 não confirma nada para essa opção: o agente fica entre "rebase + teardown" e "merge simples sem teardown", que são resultados materialmente diferentes (um destrói o worktree, o outro não). É um ramo morto do ponto de vista de execução.
- **Por que importa:** a ambiguidade cai no lado destrutivo do fluxo. Combinada com o Step 0 (que já ofereceu "Commit them now"), essa opção é também redundante — quem commitou no Step 0 recebe no Step 2 a mesma escolha commit/no-commit de novo.
- **Proposta:** ou remover a opção (o Step 0 já cobre "já está commitado": basta escolher "Skip and continue" e depois a opção 1 ou 2), ou torná-la explícita — "Merge only, keep worktree" e "Merge only, then teardown" como duas entradas separadas.
- **Impacto positivo:** elimina um ramo sem semântica definida num comando que faz rebase e `git worktree remove`.
- **Impacto negativo / risco:** remover uma opção do quiz muda a UX de um comando novo, antes de haver uso real para saber qual variante as pessoas querem.
- **Esforço:** Baixo

### Comentário do `session-start.sh` cita `pre-tool-use/02b-full-suite-guard.sh`, arquivo que não existe (`02b-` é telemetria)

- **Fingerprint:** `docs-sync-session-start-comment-cites-nonexistent-02b-full-suite-guard`
- **Alvo:** `scripts/hooks/session-start.sh`
- **Evidência:**
  - `scripts/hooks/session-start.sh:175` — "`# as the structural fix for that gap. pre-tool-use/02b-full-suite-guard.sh`" / `:176` — "`# is the complementary per-command safety net.`"
  - `ls scripts/hooks/pre-tool-use/` → `02-graphify-hint.sh`, `02b-telemetry.sh`, `02c-full-suite-guard.sh`
- **Problema:** o arquivo sempre se chamou `02c-` (criado assim em `4d69714`, junto com esse comentário). `02b-` é `02b-telemetry.sh` — um script sem relação nenhuma com escopo de teste. Como o comentário nomeia um caminho concreto, quem for procurar acha o script errado.
- **Por que importa:** é o único ponteiro no `session-start.sh` para a guarda que `abb8483` acabou de tornar bloqueante; a referência errada custa uma busca a cada leitura e leva ao script de telemetria.
- **Proposta:** corrigir para `pre-tool-use/02c-full-suite-guard.sh`.
- **Impacto positivo:** o ponteiro passa a resolver.
- **Impacto negativo / risco:** nenhum.
- **Esforço:** Baixo

### O cabeçalho de `lib/touched-paths.sh` continua declarando uso exclusivo por sub-scripts de `Stop` depois que o `02c` (PreToolUse) passou a fazer `source` dele

- **Fingerprint:** `docs-sync-touched-paths-lib-header-says-stop-only-after-02c-sources-it`
- **Alvo:** `scripts/hooks/lib/touched-paths.sh`
- **Evidência:**
  - `scripts/hooks/lib/touched-paths.sh:2` — "`# Shared touched-path detection for Stop sub-scripts.`"
  - `:12` — "`# Not a hook. Sourced by stop.sh and by stop/02-, 02b-, 03-, 03b- sub-scripts.`"
  - `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:15-17` — "`HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)"`" / "`source "$HOOK_DIR/touched-paths.sh"`"
- **Problema:** o cabeçalho documenta um conjunto fechado de consumidores que deixou de ser verdade. Também é a linha que registra o contrato de cache: `DEVTEAM_TOUCHED_PATHS` é calculado **uma vez** pelo `stop.sh` e reusado. O `02c` chama `devteam_compute_touched_paths` diretamente (`:114`), sem cache, então cada comando de suíte completa forka `git status` + `git log` — o dispatcher de PreToolUse não tem o pré-cômputo que o de Stop tem.
- **Por que importa:** o cabeçalho é o único lugar que descreve quem depende dessa lib e sob qual contrato de cache; desatualizado, o próximo refactor pode assumir que só `Stop` a usa. O custo de fork por chamada é pequeno em valor absoluto, mas contradiz a otimização que o próprio arquivo documenta como sua razão de existir.
- **Proposta:** atualizar as duas linhas para incluir `pre-tool-use/02c-`, e anotar explicitamente que no caminho PreToolUse não há pré-cômputo — o cálculo é sob demanda e só ocorre quando `is_full_suite` já casou.
- **Impacto positivo:** o contrato da lib volta a descrever a realidade antes que alguém otimize em cima de uma premissa falsa.
- **Impacto negativo / risco:** nenhum (só comentário).
- **Esforço:** Baixo

---

## LOW

### `$ARGUMENTS` de `/devteam:merge` pode ler `--no-teardown` como nome de branch alvo

- **Fingerprint:** `flow-merge-md-arguments-target-branch-parse-can-swallow-no-teardown-flag`
- **Alvo:** `commands/merge.md`
- **Evidência:**
  - `commands/merge.md:35` — "- If the current branch is a **working branch** (anything else) and `$ARGUMENTS` names a target branch, use it."
  - `commands/merge.md:71` — "`--no-teardown` in `$ARGUMENTS` forces the worktree to be kept regardless of which option is chosen…"
  - `commands/merge.md:103-105` — o bloco de opções lista `[target-branch]` e `--no-teardown` sem regra de precedência
- **Problema:** nada instrui a remover as flags antes de tratar `$ARGUMENTS` como nome de branch. Em `/devteam:merge --no-teardown` (sem alvo), a única string presente é a flag, e o Step 1 pode aceitá-la como target — resultando em `git merge` contra um branch inexistente, ou, pior, em pular a pergunta do alvo. `commands/pr.md:25-28` mostra o padrão correto: resolver flags conhecidas primeiro, por `$ARGUMENTS contains <flag>`.
- **Por que importa:** falha ruidosa (o merge erra e para), não silenciosa — daí LOW. Mas o comando é novo e o hábito de parse se propaga.
- **Proposta:** acrescentar uma linha ao Step 1: "strip every token starting with `--` from `$ARGUMENTS` before treating the remainder as a branch name; if nothing remains, ask."
- **Impacto positivo:** parse previsível, alinhado ao padrão de `pr.md`.
- **Impacto negativo / risco:** nenhum.
- **Esforço:** Baixo

---

## Descartados por duplicação

| Candidato | Porta | Fingerprint colidido |
|---|---|---|
| `learn.md:166` grava o marcador no Step 4, antes do auto-commit do Step 5, então o SHA registrado já nasce defasado e a guarda de sessão de `commit.md:179` nunca pula | Porta 3 (semântica): mesmo alvo (`commands/learn.md:166`) e mesmo efeito declarado ("a condição de skip de `commands/commit.md` é inalcançável") | `flow-learn-run-marker-records-commit-time-not-run-time` |
| `commands/pr.md:43` carrega uma segunda cópia inline da ordenação em camadas ("data/schema → domain → … → docs"), contrariando o Canonical Rule Home que manda carregar `conventional-commits/SKILL.md` | Porta 3 (semântica): alvo difere (`pr.md` vs `commit.md`), mas causa raiz e remediação são idênticas — 2 de 3 | `flow-commit-command-160-lines-pre-commit-gates-extractable-skill` |
| `scripts/new-adr.sh:58` — `s\|\[Title\]\|$TITLE\|g` ainda quebra com `&` no título (sed expande `&` para o match inteiro) | Porta 1 (literal): o slug já está registrado no `_index.md` (marcado ✅ Executed — reabertura é matéria da fase de verificação, não desta) | `auto-new-adr-sh-sed-title-substitution-breaks-on-pipe-ampersand-backslash-in-free-form-adr-title-no-escaping` |
| `02c-full-suite-guard.sh` continua sem pré-cômputo de touched paths, forkando `git status`+`git log` por comando detectado | Porta 4 → absorvido: sub-escopo de `docs-sync-touched-paths-lib-header-says-stop-only-after-02c-sources-it`, reportado dentro dele | — |
