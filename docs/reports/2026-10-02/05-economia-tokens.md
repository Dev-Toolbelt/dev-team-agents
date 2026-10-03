# Eixo E — Economia de tokens (e de forks) — 2026-10-02

Prioridade: `scripts/hooks/**`, `agents/`, `commands/` e `skills/` dentro do delta de 728 arquivos.

Todos os números abaixo foram **medidos**, com `strace -f -e trace=execve` e cronometragem do hook
real contra payloads sintéticos. Linha de base: um `PreToolUse` de um `Read` neste repositório custa
**91 ms** e **42 execves** bem-sucedidos. Esse é o orçamento que os cinco achados deste eixo atacam —
e o maior achado do eixo não é contexto de modelo, é **latência de hook em toda chamada de
ferramenta**.

---

## HIGH

nenhum achado original neste eixo nesta severidade

---

## MEDIUM-HIGH

### `04-task-board` faz 13 forks em toda chamada de ferramenta **antes** de checar o marcador que o encerra

- **Fingerprint:** `token-pretooluse-04-task-board-13-forks-before-marker-exit-every-tool-call`
- **Alvo:** `scripts/hooks/pre-tool-use/04-task-board.sh`, `scripts/hooks/lib/task-board.sh`
- **Evidência:**
  - `04-task-board.sh:19-20` — "This runs on EVERY tool call, so the gate is a bash string test on
    the payload: for any other tool nothing is sourced and no python is forked"
  - A promessa vale só para o **python**. `ANY_TOOL_RE` (`:49`) casa praticamente toda ferramenta, de
    modo que `Read`, `Grep`, `Glob`, `Edit` e `Bash` caem em `MODE="direct"`
  - `:88` faz `source task-board.sh` → `devteam_task_board_init`
    (`task-board.sh:34-49`: `git rev-parse` + `sed -n 1p` + `sed -n 2p` + dois subshells `cd && pwd`)
    → `devteam_task_board_session_id` (`:57`: `grep | head | sed`)
  - **Só depois** vem `[ -f "${TB_STATE_DIR}/task-board/${MARK}${SESSION}" ] && exit 0`
  - **Medido** em estado estacionário (marcador `.direct-s` já presente), num `Read`:
    **14 execves** — 4 `dirname`, 2 `uname` (via `state.sh` → `python.sh`), `git`, 3 `sed`, `grep`,
    `head`, `cat`. **31–33 ms**, contra 4–5 ms do `02b` e do `02c` na mesma carga.
- **Problema:** o gate "barato" resolve raiz do projeto, state-dir e session id por forks — todos
  **antes** do único teste que dá saída. O python é evitado; o custo de bash não.
- **Por que importa:** incide em **toda chamada de ferramenta, de todo provider, em todo projeto
  bound**. O `04` sozinho é ~1/3 dos 91 ms do dispatcher. Com 300 a 1000 chamadas por sessão, são
  **9 a 30 s de latência acumulada**, e cada chamada fica bloqueada até o hook terminar.
- **Proposta:** antes do `init`, extrair o session id com
  `[[ $INPUT =~ \"session_?[iI][dD]\"[^\"]*\"([^\"]*)\" ]]` e resolver o state-dir com a caminhada
  pura em bash já usada em `03-credential-guard.sh:242-250`; trocar `$(dirname "$BASH_SOURCE")` por
  `${BASH_SOURCE%/*}`; chamar `git rev-parse` e as funções do lib **só** quando o marcador não existir.
- **Impacto positivo:** de 13 forks para 0 ou 1 (apenas o `cat`) no caminho estacionário —
  **≈ 27 ms por chamada de ferramenta**. Corrige também o comentário `:19-20`, que hoje descreve o
  gate de forma imprecisa.
- **Impacto negativo / risco:** a regex do session id passa a existir em dois lugares (`04` e
  `task-board.sh`), o que exige teste de paridade. A caminhada pura não cobre um worktree vinculado
  sem ponteiro `state-dir`, então o fallback para `git` tem de ficar — ou seja, o ganho vem com mais
  um caminho condicional para manter.
- **Esforço:** Médio

---

## MEDIUM

### `python.sh` forka `uname -s` duas vezes a cada `source`, e no Linux/macOS nada é cacheado

- **Fingerprint:** `token-python-sh-uname-forked-twice-per-source-uncached-on-linux-macos`
- **Alvo:** `scripts/lib/python.sh`
- **Evidência:** `python.sh:27` — `case "$(uname -s 2>/dev/null)"`, dentro de `_dta_is_windows`, que é
  chamada em `dta_python_resolve` (`:75`) **e** no guard de `PYTHONUTF8` (`~:111`) — 2× por `source`.
  No Linux/macOS com `python3` no PATH, nada é exportado (`DTA_PYTHON` vazio), então o cache nunca se
  arma e `DEVTEAM_PLATFORM` não é setada. `strace` de um `PreToolUse` de `Read`: **4 `uname`** — 2 do
  dispatcher (`pre-tool-use.sh:13`) e 2 do `04`, via `task-board.sh` → `data-dirs.sh` → `state.sh:17`
  → `python.sh`. Consumidores: 8 dispatchers/hooks, mais `state.sh`, `telemetry-guard.sh` e
  `self-heal.sh`. **Medido: `source python.sh` custa ~7 ms contra ~1,5 ms de um bash vazio.**
- **Problema:** a detecção de plataforma usa um comando externo quando `$OSTYPE` é builtin do bash
  (`msys*`, `cygwin*`, `linux-gnu`, `darwin*`) — e é executada duas vezes, sem memoização.
- **Por que importa:** 4 dos 42 execves de um `PreToolUse` de `Read`, ~5 ms por `source`, em **toda
  chamada de ferramenta, todo prompt e todo Stop**.
- **Proposta:** em `_dta_is_windows`, usar
  `case "${DEVTEAM_PLATFORM:-$OSTYPE}" in win*|msys*|cygwin*)`, manter `uname` apenas como fallback
  quando `OSTYPE` estiver vazio, e memoizar o resultado numa variável de shell.
- **Impacto positivo:** de 2–4 forks para 0 por `source` — ≈ 5 ms por dispatch e por sub-script que
  carrega `state.sh`.
- **Impacto negativo / risco:** `$OSTYPE` é `msys` no Git Bash, `cygwin` no Cygwin e `linux-gnu` no
  WSL; a equivalência com `uname -s` é exata nesses casos, **mas** é um comportamento de shell e não
  de sistema, então um shell não-bash que faça `source` do arquivo perde a detecção. Precisa de teste
  cobrindo os três valores.
- **Esforço:** Baixo

### Os dispatchers forkam `basename`/`dirname` onde parameter expansion basta — 15 forks por `PreToolUse`

- **Fingerprint:** `token-hook-dispatchers-basename-dirname-forks-per-subscript-iteration`
- **Alvo:** `scripts/hooks/pre-tool-use.sh`, `post-tool-use.sh`, `user-prompt-submit.sh`, `stop.sh`
- **Evidência:** `pre-tool-use.sh:~38` — `if [[ ! "$(basename "$script")" =~ $SUBSCRIPT_RE ]]`, uma
  vez **por arquivo do glob**. O glob traz 7 arquivos, incluindo `_disabled-01-check-updates.sh`
  (89 linhas, morto), rejeitado pelo regex a cada chamada. `strace` de um `PreToolUse` de `Read`:
  **7 `basename` + 8 `dirname`** de 42 execves. `stop.sh` tem 4 ocorrências de `basename`; os outros
  dois dispatchers repetem o laço.
- **Problema:** o filtro de nomes — que existe justamente para ser barato ("every single tool call",
  `:29-33`) — paga `fork+exec` por arquivo, quando `${script##*/}` faz o mesmo sem processo.
- **Por que importa:** ≈ 15 forks por `PreToolUse` (~8 ms medidos), em toda chamada de ferramenta;
  `post-tool-use` e `user-prompt-submit` repetem o padrão em escala menor.
- **Proposta:** `base=${script##*/}` antes do teste; `${BASH_SOURCE[0]%/*}` em lugar de
  `$(dirname …)`; mover o `_disabled-*` para fora do diretório varrido.
- **Impacto positivo:** de ~15 forks para 0 por `PreToolUse`.
- **Impacto negativo / risco:** `${BASH_SOURCE[0]%/*}` devolve o próprio nome quando o script é
  invocado sem diretório (`bash pre-tool-use.sh`), então o `cd -P` precisa continuar cobrindo o caso
  relativo. Mover o `_disabled-` exige um passe de grep antes: `check-updates.sh` e `update.sh` o
  referenciam.
- **Esforço:** Baixo

### `plan-mode` carrega uma segunda cópia de 56 linhas do Execution Strategy Gate, usada por 1 de 26 consumidores

- **Fingerprint:** `token-plan-mode-execution-strategy-gate-duplicates-orchestration-loaded-by-26`
- **Refina:** `token-plan-mode-skill-131-lines-loaded-by-7-agents-unconditionally`
- **Alvo:** `skills/shared/plan-mode/SKILL.md` § Execution Strategy Gate (`:151-206`)
- **Evidência:** `plan-mode/SKILL.md:152` — "This optional gate applies … When an agent's
  configuration mandates it". Só `agents/software-architect.md:62` e `commands/architect.md:30` o
  exigem — e `software-architect.md:68-69` diz que o procedimento está "defined in
  `skills/architecture/orchestration/SKILL.md`". `orchestration/SKILL.md:13-48` traz **os mesmos
  cinco passos**: as prefs de worktree com o mesmo `python3 -c`, os mesmos defaults, a mesma
  recomendação por `worktree_active`, o quiz com as mesmas 4 opções e a ação por escolha.
  Seção no `plan-mode`: **56 linhas / 3.202 B**, num arquivo de 235 linhas / 14.853 B.
  Consumidores do `plan-mode`: **7 agentes + 19 comandos = 26**.
  `interaction-patterns/SKILL.md:190` aponta o `plan-mode` como casa canônica do gate, enquanto o
  architect aponta o `orchestration` — **duas fontes canônicas**.
- **Problema:** o mesmo procedimento mora em dois skills; o carregado por 26 consumidores é o que
  nenhum deles executa, e o carregado por quem executa é o outro. Isso é exatamente o que a regra
  *Delegate, Never Restate* existe para impedir, e já produziu duas referências canônicas divergentes.
- **Por que importa:** 25 dos 26 consumidores pagam 3,2 KB (22% do skill) por conteúdo que nunca
  usam, em toda execução de plano — **≈ 83 KB de contexto por rodada completa**. E há drift real a
  caminho: o `orchestration` recebeu 3 commits no delta.
- **Proposta:** reduzir a seção do `plan-mode` a um ponteiro de 3 linhas ("quando mandatado, ver
  `orchestration` § Execution Strategy Gate") e repontar `interaction-patterns:190` para o
  `orchestration`.
- **Impacto positivo:** `plan-mode` de 235 → ~182 linhas (−3,2 KB), em 26 fluxos; e uma das duas
  casas canônicas deixa de existir.
- **Impacto negativo / risco:** o `plan-mode` deixa de ser autossuficiente para o architect — que já
  carrega o `orchestration` antes do gate (`software-architect.md:70`), então na prática não há
  perda. Se `agent-lint.sh` passar a exigir a seção, o lint precisa de ajuste.
- **Esforço:** Baixo

### `02c-full-suite-guard` faz 4 forks extras em toda chamada `Bash` antes de saber se há runner de teste

- **Fingerprint:** `token-pretooluse-02c-sed-tr-head-forks-before-runner-gate-on-every-bash-call`
- **Alvo:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`
- **Evidência:** `:30` extrai o comando com `printf | sed -n -E … | head -1` (2 forks); `:182` roda
  `is_full_suite` com `tr -d … | sed -E …` (2 forks); `:13` tem `$(cd …/lib && pwd)` e `dirname`.
  **Não há nenhum teste por substring de runner** entre o gate de `"tool_name":"Bash"` e o `sed`.
  `strace` com `ls -la src`: `sed`×2, `head`, `tr`, `dirname`, `cat`.
  **Medido: 18 ms num `Bash` trivial contra 5 ms num `Read`** — +13 ms por chamada `Bash`.
- **Problema:** o gate pula `Read`/`Grep`/`Edit`, mas **todo** comando `Bash` (`ls`, `git status`,
  `cat`) paga extração e classificação por processos, mesmo sem nenhum token de runner no payload.
- **Por que importa:** `Bash` é tipicamente a ferramenta mais frequente de uma sessão de
  desenvolvimento. 4 forks e ~13 ms por chamada — **~2,6 s a cada 200 chamadas `Bash`**.
- **Proposta:** logo após o gate de `Bash`, inserir
  `case "$INPUT" in *test*|*jest*|*rspec*|*phpunit*|*pest*|*e2e*) ;; *) exit 0 ;; esac`.
- **Impacto positivo:** de 5 forks para 0 nas chamadas `Bash` sem token de runner, que são a grande
  maioria — ~13 ms por chamada.
- **Impacto negativo / risco:** **real e do tipo mais perigoso.** A lista de substrings passa a ter
  de acompanhar o `classify`, e um runner novo sem `test` no nome sai **silenciosamente** do guard —
  a mesma classe de falha do gap já registrado nos `case` `make`/`composer`. Só é aceitável com um
  teste que itere os runners do `classify` e confirme que todos atravessam o pré-gate.
- **Esforço:** Baixo

---

## LOW-MEDIUM

### `02b-telemetry` resolve git, state-dir e prefs (7 forks) para qualquer `Bash`, mas só interessam comandos com `/devteam:`

- **Fingerprint:** `token-02b-telemetry-resolves-state-for-every-bash-call-needs-devteam-substring`
- **Refina:** `flow-telemetry-pre-tool-use-02-runs-on-every-tool-call-without-batching-or-deduplication`
- **Alvo:** `scripts/hooks/pre-tool-use/02b-telemetry.sh`
- **Evidência:** `:37-39` aceita `Bash` ou `Task` e segue; `:52-56` resolve `MAIN_REPO_ROOT` com dois
  subshells e `git`; `:57`/`:62` rodam `devteam_state_dir` e `devteam_prefs_file`; `:68-69` fazem o
  consent guard. **Só no ramo `Bash` (`:80-90`)** o payload é conferido contra `/devteam:`.
  `strace` com `ls -la src`: `git`, 4 `dirname`, 2 `uname`.
  **Medido: 29 ms num `Bash` trivial contra 4,5 ms num `Read`.**
- **Problema:** o único dado de que o ramo `Bash` precisa (`/devteam:<nome>` no comando) está no
  payload bruto desde a primeira linha, mas só é testado **depois** de resolver git, state-dir e
  consentimento.
- **Por que importa:** ≈ 25 ms e 7 forks por chamada `Bash`, em todo projeto que carrega o hook,
  **mesmo com telemetria desligada** — o consent guard vem depois da resolução, então quem recusou
  telemetria paga o custo inteiro.
- **Proposta:** transformar o `case` de `:37-39` em
  `*'"tool_name":"Bash"'*) [[ "$PAYLOAD" == */devteam:* ]] || exit 0; TOOL_NAME=Bash`.
- **Impacto positivo:** de 7 forks (~25 ms) para 0 em toda chamada `Bash` que não cita `/devteam:` —
  quase todas.
- **Impacto negativo / risco:** a substring `/devteam:` pode aparecer num campo que não é o comando
  (em `description`, por exemplo), gerando o mesmo falso positivo que o ramo já tem hoje. O gate é
  um pré-filtro e não muda a semântica, mas herda esse ruído.
- **Esforço:** Baixo

---

## LOW

nenhum achado original neste eixo nesta severidade

---

## Descartados por duplicação

- `token-graphify-hint-3-forks` — porta 1 — `token-graphify-hint-3-git-forks-before-marker-early-exit-on-every-tool-call`, mesmo alvo e causa.
- `token-efficiency 160 linhas × 18 agentes` — porta 3 — alvo, causa e remédio coincidem com `token-token-efficiency-skill-itself-154-lines-eager-loaded-by-all-17-agents`.
- `plan-mode carregado por 7 agentes + 16 commands` — porta 3 — tema registrado e já executado; só o sub-escopo "gate duplicado" voltou, acima, com `Refina`.
- `stop/03c-03d-03e re-forkam git` — porta 3 — hipótese já refutada no banco (reusam `DEVTEAM_TOUCHED_PATHS`).
- `99b-archive-index sem fast-path` — porta 3 — consta no banco entre as hipóteses refutadas por evidência.
- `05-telemetry` consent guard e fast-path — porta 1 — registrados e abertos.
- `check-updates` fork de python3 — porta 1 — `token-pre-tool-use-01-check-updates-forks-python3-to-read-interval-before-ttl-early-exit`.
- `interaction-patterns 209 × 34`, `orchestration 399`, `migration-v1-to-v2`, `fix-patterns`, `current-context` — porta 5 — todos no conjunto aberto desta rodada.
- `post-tool-use` / `user-prompt-submit` — porta 4 — sem achado: gates puros em bash com saída antes de qualquer fork próprio (16 execves, quase todos do dispatcher e do `python.sh`, já cobertos pelos dois achados acima).
