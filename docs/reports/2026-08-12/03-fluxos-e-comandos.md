# Eixo C — Fluxos, Comandos e Automação — 2026-08-12

**Baseline:** `HEAD` = `07e0725`

Foco no delta: dispatchers de hooks, sub-scripts novos (`03c`, `03d`, `03e`, `02c`, `99b`), scripts
`_disabled-*`, e os 9 comandos novos.

## Hipóteses testadas e refutadas por evidência

Duas hipóteses de falha plausíveis foram levantadas e **descartadas** após verificação — registradas
aqui para o próximo pass não as reabrir:

1. **"Os scripts `_disabled-*` ainda auto-executam porque o dispatcher globa `*.sh`."**
   Refutada. **Ambos** os dispatchers têm allowlist por regex: `scripts/hooks/stop.sh:57` e
   `scripts/hooks/pre-tool-use.sh:20` usam `SUBSCRIPT_RE='^[0-9]{2}[a-z]?-[a-z0-9]…\.sh$'`. Arquivos
   com prefixo `_disabled-` não casam e são pulados. Isso, aliás, confirma o fingerprint executado
   `flow-stop-dispatcher-globs-all-sh-no-allowlist`.

2. **"Os sub-scripts novos `03c/03d/03e` re-forkam `git status`/`git log` (dupla do fingerprint
   `flow-stop-dispatcher-computes-no-changes-once…`)."**
   Refutada. `03c`/`03d` respeitam o fast-path `DEVTEAM_NO_CHANGES` (linha 8). `03e-adr-gap-check.sh`
   consome `DEVTEAM_TOUCHED_PATHS` via `scripts/hooks/lib/touched-paths.sh` (linhas 13-16), o
   conjunto tocado computado **uma vez** pelo `stop.sh`. Padrão correto, sem re-fork.

## Achado

**Nenhum achado original neste eixo.** Os dispatchers têm allowlist, os sub-scripts novos reusam o
conjunto tocado compartilhado, e os comandos novos (`status`, `version` sem spawn de agente;
`explain` no contexto principal por design) seguem as convenções declaradas no `CLAUDE.md`. Os
fluxos degradados conhecidos (`flow-cli-commit-validate-msg` silencioso, ausência de `commit-msg`
hook) seguem abertos e foram revalidados na Fase 1 — não são novos.

---

# Pass incremental — 2026-08-12 (2ª execução), baseline `3fbe371`

Eixo concentrado no delta `07e0725..3fbe371`, onde estão as três mudanças de comportamento do
período: `4734882` (guarda de sessão do auto-learn), `58d86a5` (full-suite guard) e
`b9f00a7` (gitignore de credenciais).

## MEDIUM-HIGH

### O `sed` do full-suite guard engole as chaves JSON vizinhas, e o texto do `description` decide se o nudge dispara

- **Fingerprint:** `auto-full-suite-guard-sed-absorbs-sibling-json-keys`
- **Alvo:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`
- **Evidência:**
  - `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:22` —
    `COMMAND=$(printf '%s' "$INPUT" | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\(.*\)"[[:space:]]*[,}].*/\1/p' | head -1)`
  - Reproduzido contra um payload realista de `tool_input` do Bash (que carrega `description`
    ao lado de `command`):

    ```
    payload: {"tool_name":"Bash","tool_input":{"command":"pnpm vitest run",
              "description":"Run the auth .spec. suite"}}
    $COMMAND extraído: pnpm vitest run","description":"Run the auth .spec. suite
    veredito do guard: (nenhuma saída — nudge NÃO dispara)
    ```

    e o controle, mesmo comando, `description` sem `.spec.`:

    ```
    payload: … "description":"Run the auth suite"
    veredito do guard: {"hookSpecificOutput":{…"looks like an UNSCOPED full test suite run"…}}
    ```
  - A causa é `02c-full-suite-guard.sh:40` — a cláusula de exclusão
    `[[ "$cmd" != *.test.* && "$cmd" != *.spec.* … ]]` roda sobre a string poluída.
- **Problema:** `\(.*\)` é guloso e casa até a **última** aspa seguida de `,` ou `}` no payload
  inteiro, não até o fim do valor de `command`. Tudo que vier depois — `description`, `timeout`,
  qualquer chave irmã — entra em `$COMMAND`.
- **Por que importa:** o guard é a rede de segurança do `skills/shared/scoped-test-execution/SKILL.md`
  para sessões fora do roteamento `/devteam:*`. Como as exclusões de escopo casam por substring,
  **prosa em linguagem natural no `description` desliga o nudge**: qualquer descrição contendo
  `.test.`, `.spec.`, `-t `, `--filter` ou `--related` produz falso negativo. É silencioso e não
  reproduzível pelo usuário — dois comandos idênticos se comportam de forma diferente.
  O commit `58d86a5` resolveu o truncamento em aspas aninhadas que era seu objetivo declarado,
  mas o transbordo para as chaves irmãs permanece.
- **Proposta:** delimitar a captura ao valor de `command` — trocar o `.*` guloso por uma classe
  negada que pare na primeira aspa não escapada
  (`"\(\([^"\\]\|\\.\)*\)"`), preservando o suporte a aspas escapadas que motivou `58d86a5`.
- **Impacto positivo:** elimina toda uma classe de falso negativo e devolve determinismo ao
  guard; o nudge passa a depender só do comando.
- **Impacto negativo / risco:** a BRE com classe negada é bem menos legível que o `.*`, e o
  hook está no caminho quente de **todo** `PreToolUse` de Bash — uma regex mal fechada aqui
  degrada cada chamada. Exige teste com payloads de aspas escapadas antes de entrar.
- **Esforço:** Baixo

### A guarda de sessão do auto-learn não consegue satisfazer a própria condição — a otimização é um no-op permanente

- **Fingerprint:** `flow-learn-run-marker-records-commit-time-not-run-time`
- **Alvo:** `commands/commit.md`, `commands/learn.md`
- **Evidência:**
  - `commands/commit.md:17` — "check `.dev-team-agents/.learn-last-run` (format:
    `<unix-timestamp> <head-sha>`). Compare its `<head-sha>` against the current `git rev-parse HEAD`,
    and **its timestamp against the mtime of** `.dev-team-agents/user-data/session-summary.md`.
    If HEAD hasn't moved and the session summary hasn't changed **since that run**, skip…"
  - `commands/learn.md:166` — "Record the run marker (any outcome):
    `echo "$(git log -1 --format=%ct 2>/dev/null || date +%s) $(git rev-parse HEAD 2>/dev/null)" > .dev-team-agents/.learn-last-run`"
  - `commands/learn.md:168` — `## Step 5 — Auto-commit` vem **depois** da linha 166.
- **Problema:** dois defeitos independentes, cada um suficiente para impedir o skip.
  **(a)** O primeiro campo é `git log -1 --format=%ct`, o *commit timestamp do `HEAD`* — não a
  hora em que o learn rodou. O fallback `|| date +%s` só se aplica se o `git log` falhar, o que
  em repo com histórico nunca ocorre. Comparar o carimbo do último commit contra o mtime de um
  arquivo tocado *durante* a sessão sempre acusa "mudou desde aquela execução".
  **(b)** O marcador é gravado no Step 4, e o Step 5 do próprio `learn` faz auto-commit — no
  caminho `/devteam:learn` autônomo, o `<head-sha>` registrado já nasce obsoleto.
- **Por que importa:** o commit `4734882` justifica-se por custo de contexto ("spiking context
  usage in commit-heavy sessions") e entrega dois mecanismos: o opt-out
  `auto_learn_before_commit` (funciona) e a guarda de sessão (não dispara). A economia atribuída
  à guarda não se materializa, e a mensagem de commit descreve como funcionando um caminho
  inalcançável — quem for medir o ganho vai procurar no lugar errado.
- **Proposta:** gravar o instante da execução, não o do commit — `date +%s` direto — e mover a
  gravação do marcador para **depois** do Step 5, de modo que o `<head-sha>` seja o HEAD
  pós-commit. Alternativamente, dispensar o campo de tempo e comparar apenas
  `<head-sha>` + mtime do `session-summary.md` contra o mtime do próprio marcador.
- **Impacto positivo:** torna real a economia declarada; em sessões com vários commits sem
  código novo, elimina uma passada completa de coleta de evidências por commit.
- **Impacto negativo / risco:** uma guarda que **de fato** dispara pode pular captura legítima —
  edições em `docs/` que não movem o HEAD nem tocam `session-summary.md` deixariam de ser
  capturadas. O `4734882` promete "without dropping the always-on-by-default capture guarantee";
  consertar a guarda é o que efetivamente coloca essa promessa à prova.
- **Esforço:** Médio

### O heredoc de fallback sem `python3` do `install.sh` não recebeu a chave adicionada no mesmo commit

- **Fingerprint:** `auto-install-heredoc-omits-auto-learn-before-commit`
- **Alvo:** `scripts/install.sh`
- **Evidência:**
  - `scripts/install.sh:1000-1004` — o comentário do próprio bloco:
    "…there is no JSON parser on this path to read the schema with. **When you add or change a key
    there, change it here too; the two drifted once already (`qa_browser` was missing).**"
  - `scripts/install.sh:1022-1025` — `"worktree_base_branch": null,` / `"worktree_commit_action": "ask",`
    / `"worktree_path": ".worktrees",` — **`auto_learn_before_commit` não está entre elas**.
  - `scripts/lib/preferences-defaults.json:18` — `"auto_learn_before_commit": true,` (canônico).
  - `grep -rn "auto_learn_before_commit" scripts/` retorna **apenas** a linha do JSON canônico —
    zero ocorrências em `install.sh`.
  - `git show 4734882 --stat` — o commit que adicionou a chave **tocou** `scripts/install.sh`,
    mas só para acrescentar `_add_gitignore ".dev-team-agents/.learn-last-run"` (linha 778).
- **Problema:** o `CLAUDE.md` nomeia esse heredoc como o primeiro dos cinco espelhos obrigatórios
  de `preferences-defaults.json`, justamente porque não há parser para ler o canônico. O commit
  que criou a chave editou o arquivo do espelho — e não o espelho.
- **Por que importa:** numa instalação sem `python3`, o `preferences.json` gerado nasce sem a
  chave. O comportamento não quebra (`commands/commit.md:15` assume `true` na ausência), mas o
  usuário perde a única via de descobrir e desligar o auto-learn: o campo não existe no arquivo
  que ele abriria para editar. É a segunda ocorrência da mesma drift, com o aviso escrito na
  linha imediatamente acima do bloco — evidência de que comentário não é gate.
- **Proposta:** acrescentar `"auto_learn_before_commit": true,` ao heredoc entre
  `worktree_commit_action` e `worktree_path`, mantendo a ordem do canônico; e adicionar ao
  `helpers/agent-lint.sh` (ou a um gate de CI dedicado) a comparação do conjunto de chaves do
  heredoc contra `scripts/lib/preferences-defaults.json`.
- **Impacto positivo:** fecha a divergência atual e transforma um comentário de advertência —
  já falho duas vezes — num gate mecânico que não depende de memória.
- **Impacto negativo / risco:** extrair as chaves de dentro de um heredoc com interpolação
  (`$PREFS_LANGUAGE`, `$AUTO_UPDATE_VALUE`, `$TELEMETRY_VALUE`) exige um parser tolerante a
  `$VAR` no lugar do valor; um gate frágil aqui gera CI vermelho por motivo errado e acaba
  desativado — pior que não ter gate.
- **Esforço:** Baixo (a chave) · Médio (o gate)

## LOW-MEDIUM

### O comentário do `02c` invoca como precedente exatamente a abordagem que o arquivo citado rejeita

- **Fingerprint:** `docs-sync-02c-comment-cites-graphify-hint-as-sed-precedent`
- **Alvo:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`
- **Evidência:**
  - `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:17-18` — "Pull the command string out of
    tool_input.command without a JSON parser — **consistent with `02-graphify-hint.sh`'s pure-bash
    approach on the hot path.**"
  - `scripts/hooks/pre-tool-use/02-graphify-hint.sh:11` — "**Pure-bash substring match instead of
    `grep|sed`: skips 2 forked subprocesses**"
  - `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:22` usa `printf | sed` — dois forks por
    invocação, exatamente o que o arquivo citado documenta ter evitado.
- **Problema:** o comentário afirma consistência com um arquivo que documenta a decisão oposta.
  "pure-bash" ali significa *sem `sed`*; aqui significa *sem parser JSON*.
- **Por que importa:** `02c` roda em **todo** `PreToolUse` de Bash, o mesmo caminho quente. O
  comentário desarma a pergunta certa — "por que este hook forka onde o vizinho não forka?" —
  ao apresentar o custo como precedente estabelecido. Quem for otimizar o caminho quente lê a
  linha 18 e segue adiante.
- **Proposta:** reescrever o comentário para o que é verdade — "extração por `sed` porque o
  padrão exige captura de grupo, que `case` não faz; `02-graphify-hint.sh` evita o fork porque
  só precisa de substring" — ou eliminar o fork substituindo a extração por `${INPUT#*"command"*:*\"}`
  + `${VAR%%\"*}`.
- **Impacto positivo:** o comentário volta a descrever o código; a segunda opção elimina 2 forks
  por chamada de Bash da sessão inteira.
- **Impacto negativo / risco:** expansão de parâmetro em bash para desempacotar JSON é ilegível
  e quebra em aspas escapadas — o caso que `58d86a5` acabou de consertar. Corrigir só o
  comentário é a mudança segura; trocar o mecanismo reabre o bug que hoje está fechado.
- **Esforço:** Baixo
