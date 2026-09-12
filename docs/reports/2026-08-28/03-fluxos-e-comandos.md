# Eixo C — Fluxos, comandos e automação (2026-08-28)

**Baseline:** `HEAD` = `a67cac9` · **Baseline anterior:** `a67cac9`

## Método

1. **Carga do banco anti-duplicação.** Versão de working-tree de `docs/reports/_index.md` (213
   fingerprints) e `docs/reports/2026-08-21/03-fluxos-e-comandos.md` (14 achados do eixo C anterior),
   ambos lidos antes de gerar qualquer candidato.
2. **Delta.** `git log --since=2026-08-21` retorna **zero commits**. Não havia superfície nova — a
   busca foi por ângulos estruturais ainda não explorados, não por drift de commit.
3. **Consistência `commands.json` ↔ corpos ↔ `CLAUDE.md`.** Comparação dos 35 registros de
   `scripts/lib/commands.json` com os 35 arquivos `commands/*.md` (conjuntos idênticos), presença de
   `PLAN GATE`, pins `model:`, carga de `current-context` (`grep -L`) e listas enumeradas em
   `CLAUDE.md:237-258`.
4. **Reprodução executável.** Cada achado com comportamento observável foi reproduzido em sandbox
   `/tmp` sobre cópias descartáveis — o repositório real nunca foi modificado (`git status` final
   idêntico ao inicial): repositório git sintético para o `03e-adr-gap-check.sh`, render dos três
   providers via `render_provider.py`, injeção de prompt plain-text em `agent-lint.sh`, e isolamento
   do padrão `[ "$fail" -eq 0 ] && …` sob `set -euo pipefail`.
5. **Anti-duplicação.** Para cada candidato: `grep -F "<slug>"`, `grep -i "<basename>"` e comparação
   de três atributos. Nove candidatos descartados, listados ao final.

---

## HIGH

### O output do pass de auditoria de 2026-08-21 nunca foi commitado, e nenhum mecanismo detecta isso

- **Fingerprint:** `gov-audit-pass-output-uncommitted-with-no-detection-mechanism`
- **Alvo:** `docs/reports/_prompt-auditoria.md`
- **Evidência:**
  `git log --format='%h %ad' --date=short -1` → `a67cac9 2026-08-21` — **o último commit do
  repositório tem sete dias**, e é o mesmo sha que `docs/reports/2026-08-21/index.md:3` registra como
  seu próprio baseline.
  `git status --short` → ` M docs/reports/_index.md` · `?? docs/reports/2026-08-21/`.
  `git show HEAD:docs/reports/_index.md | grep -cE '^- \`[a-z]'` → **176**; a árvore de trabalho →
  **213**. As 37 fingerprints do pass anterior e os seus sete arquivos de relatório existem apenas no
  disco desta máquina.
  `docs/reports/_prompt-auditoria.md:336-358` prescreve o bloco de commit/push, e `:360-366` prescreve
  a verificação (`git ls-remote … refs/heads/main`). Nada nesse bloco registra que rodou.
- **Problema:** o passo final do prompt de auditoria — commit e push — é a única coisa que transforma
  o trabalho do pass em artefato durável, e ele falhou (ou não foi alcançado) sem deixar rastro. O
  pass produziu 37 fingerprints e sete relatórios, e o resultado ficou indistinguível de um pass que
  nunca rodou para qualquer pessoa ou máquina que não seja esta.
- **Por que importa:** o banco de fingerprints é o mecanismo anti-duplicação de todo o sistema. Um
  pass cuja atualização do banco não chega ao remoto faz o **pass seguinte redescobrir os mesmos 37
  achados** — exatamente a falha que o `_index.md` existe para impedir. Este pass só escapou porque
  detectou a árvore suja na Fase 0 e passou a tratar a versão de working-tree como autoritativa; um
  pass rodando em clone limpo teria gerado 37 duplicatas silenciosas.
  E não há gate: `stop/03b-fingerprint-uniqueness.sh:24` dispara em
  `devteam_touched_matches '^docs/reports/'`, isto é, verifica a **unicidade** dos slugs quando
  `docs/reports/` é tocado, mas nada verifica que o toque foi **commitado**. `01-session-summary.sh`
  detecta árvore suja via `session-summary-detect.sh:20-22` e pede um resumo de sessão — mas
  `user-data/session-summary.md` **não existe** neste repositório, então nem esse rastro sobrou.
- **Proposta:** adicionar ao bloco de encerramento do `_prompt-auditoria.md` uma verificação
  obrigatória e **fail-loud**: após o push, confrontar `git rev-parse HEAD` com o sha devolvido por
  `git ls-remote … refs/heads/main` e, em caso de divergência ou de token ausente, encerrar o pass com
  a mensagem de erro como **única** saída no chat. Complementarmente, criar um sub-script
  `stop/03f-report-committed.sh` que avise quando existir arquivo não rastreado sob
  `docs/reports/<YYYY-MM-DD>/`.
- **Impacto positivo:** fecha o modo de falha que custou uma semana de trabalho de auditoria e que
  teria custado 37 achados duplicados no próximo pass. A verificação já está escrita no prompt — falta
  torná-la bloqueante em vez de informativa.
- **Impacto negativo / risco:** um sub-script de Stop que examina arquivos não rastreados vai acender
  em qualquer sessão que esteja **no meio** de escrever um relatório, que é o caso normal de um pass
  em andamento — precisa de um gate por data ou de tolerância explícita ao dia corrente, senão vira
  ruído em toda sessão de auditoria e é desativado por irritação. Tornar o push fail-loud também
  transforma uma falha de credencial em falha do pass inteiro, escondendo relatórios que já estavam
  corretos no disco; a mensagem precisa dizer explicitamente que o conteúdo foi gerado e onde está.
- **Esforço:** Baixo

### `/devteam:review` edita arquivos e cria commits no contexto principal, enquanto `CLAUDE.md` o classifica como "read-only by design" para justificar a ausência de Plan Gate

- **Fingerprint:** `flow-review-command-writes-and-commits-while-documented-as-read-only`
- **Alvo:** `commands/review.md`, `CLAUDE.md`
- **Evidência:** `commands/review.md:66` — "If the user chooses to apply, execute the changes directly
  (edit files, create commits if files were modified). Do not delegate back to agents — apply the
  changes yourself based on the findings already collected."
  `CLAUDE.md:254` — "`/devteam:review` e `/devteam:explain` are `conditional` and **read-only by
  design** (neither body carries a plan-gate step — review reads the diff and delegates; explain
  answers a question and writes nothing), so in practice both execute directly."
  `grep -L "PLAN GATE" commands/*.md` confirma `review.md` entre os 16 sem gate; `commands.json`
  registra `"review": { "plan_gate": "conditional" }`.
- **Problema:** o Step 9 do comando é um caminho de escrita — edita arquivos e cria commits —
  executado diretamente no contexto principal, sem plano, sem aprovação e sem delegação. `CLAUDE.md`
  afirma como fato que o corpo é read-only e usa essa afirmação como a razão pela qual não há passo de
  plano. As duas frases não podem ser verdadeiras ao mesmo tempo.
- **Por que importa:** três regras do harness são atravessadas de uma vez no HEAD: (a) o *Mandatory
  Plan Mode* não se aplica porque a exceção documentada declara o comando inofensivo; (b) a linha
  `:35` do próprio arquivo diz "**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT
  review inline — always delegate" e o `:66` manda o oposto para a fase que escreve; (c) o commit
  criado no `:66` não passa pelo `/devteam:commit` nem pela Commit Rule. Quem lê a exceção de
  `CLAUDE.md` para decidir se precisa auditar o comando conclui, incorretamente, que não precisa.
- **Proposta:** ou remover `review` da cláusula "read-only by design" e adicionar um PLAN GATE ao
  Step 9, ou reescrever o Step 9 para re-spawnar os agentes de implementação (padrão já usado por
  `backend.md`/`frontend.md`/`fullstack.md`/`mobile.md`) em vez de aplicar no contexto principal. A
  segunda opção mantém a exceção verdadeira.
- **Impacto positivo:** reconcilia a única exceção de Plan Gate que hoje protege um caminho de
  escrita; alinha `review.md` ao padrão de resolução de findings dos outros cinco comandos.
- **Impacto negativo / risco:** com PLAN GATE, `/devteam:review` ganha um passo de aprovação num fluxo
  hoje contínuo — mais fricção em revisões pequenas. Com delegação, o custo de tokens sobe (spawn
  extra por findings já coletados) e a latência aumenta. Nenhuma das duas é gratuita: a versão atual é
  rápida justamente porque pula ambos.
- **Esforço:** Baixo

### `CLAUDE.md:210` declara que a Quiz-first Rule dos comandos é imposta por `agent-lint.sh`, mas o linter nunca lê `commands/*.md`

- **Fingerprint:** `auto-agent-lint-quiz-first-never-scans-commands-dir`
- **Alvo:** `helpers/agent-lint.sh`, `CLAUDE.md`
- **Evidência:** `CLAUDE.md:210` — "Commands are subject to the same authoring discipline as agents:
  **max ~200 lines each**, enforced by `helpers/size-limits.sh`, and the **Quiz-first Rule** below,
  enforced by `helpers/agent-lint.sh`."
  `helpers/agent-lint.sh:478-481` — o único laço que chama `check_agent` (que invoca
  `check_quiz_first` em `:236-237`) é `for agent_file in agents/*.md`. `check_command_roster`
  (`:408-470`) valida apenas `tier`, `agent` e o pin `model:`, nunca o corpo.
  **Reproduzido:** anexando `Proceed with the merge? (yes/no)` a `commands/qa.md` numa cópia,
  `bash helpers/agent-lint.sh` retorna `agent-lint: clean ✓`. A mesma linha em
  `agents/qa-specialist.md` produz `· plain-text yes/no prompt found — use AskUserQuestion tool
  instead` e falha o lint.
- **Problema:** a regra vale para 35 comandos, o gate cobre 0 deles. `size-limits.sh` (a outra metade
  da mesma frase) de fato cobre comandos; a metade do Quiz-first não. A frase documenta como corrente
  uma imposição que não existe.
- **Por que importa:** `01-lint.sh:67` roda `blocking "agent-lint" bash helpers/agent-lint.sh` — é o
  gate bloqueante do CI. Um comando novo pode entrar com prompt plain-text `(yes/no)` e passar em CI e
  no `Stop` hook sem nenhum sinal. O achado seguinte deste relatório (ferramenta `question` em quatro
  comandos) é a demonstração de que o corpo dos comandos não é auditado por nada além de leitura
  humana.
- **Proposta:** adicionar um laço `for cmd_file in commands/*.md` que chame `check_quiz_first` com os
  dois regexes já existentes (`QUIZ_YESNO_RE`, `QUIZ_MC_RE`), ou extrair de `check_agent` uma
  `check_body_prompts` compartilhada.
- **Impacto positivo:** fecha a metade não implementada de uma regra declarada obrigatória, com custo
  marginal — a função já existe e já é chamada duas vezes.
- **Impacto negativo / risco:** o `check_quiz_first` tem falsos positivos conhecidos (o regex de
  múltipla escolha casa qualquer `?` seguido de parênteses com barras — a linha de teste acima
  disparou **ambos** os regexes). Estender a 35 arquivos novos pode acender erros bloqueantes em prosa
  legítima, exigindo uma rodada de ajuste de regex ou reescrita de linhas antes de promover a
  bloqueante.
- **Esforço:** Baixo

---

## MEDIUM-HIGH

### Quatro comandos de implementação mandam usar a ferramenta `question` — que não existe no Claude Code — exatamente no gate de resolução de findings

- **Fingerprint:** `flow-question-tool-name-in-four-implementation-command-findings-gates`
- **Alvo:** `commands/backend.md`, `commands/frontend.md`, `commands/fullstack.md`, `commands/mobile.md`
- **Evidência:** `commands/backend.md:66` — "**If findings exist**, use the `question` tool to ask the
  user what to do." (idêntico em `frontend.md:57`, `fullstack.md:65`, `mobile.md:57`).
  Contradiz a primeira linha do mesmo arquivo — `commands/backend.md:6`: "Load
  `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a
  finite set of answers — never a plain-text prompt."
  **Reproduzido nos três renders:** Codex corrige (sai como "use `request_user_input` (Plan mode)",
  via `_CODEX_BODY_REPLACEMENTS` em `render_provider.py:161-163`); opencode mantém `question`, que é
  o nome nativo correto lá; **Claude recebe o corpo verbatim** (`render_command_claude` relê o
  arquivo-fonte) e vê `question`, ferramenta inexistente.
- **Problema:** o corpo canônico é escrito para Claude — Claude é o caso identidade, os comandos são
  symlinkados e nunca renderizados. Nesses quatro pontos ele carrega o nome de ferramenta do
  opencode. O payload JSON logo abaixo já está no formato do `AskUserQuestion`
  (`questions[].{question, header, options[].{label, description}}`), então **só o nome está errado**.
- **Por que importa:** é o único ponto de decisão do usuário nos quatro comandos de implementação mais
  usados — o gate que decide se os findings de `code-reviewer` e `qa-specialist` são aplicados. Com um
  nome inexistente, o modelo cai em improviso: prompt de texto puro (violando a Quiz-first Rule
  declarada sessenta linhas acima no mesmo arquivo) ou adivinhação do nome correto. E nenhum gate
  detecta: `agent-lint.sh` não lê `commands/*.md` (achado anterior) e `render_provider.py` só
  reescreve para Codex.
- **Proposta:** trocar `` use the `question` tool `` por `` use the **`AskUserQuestion`** tool `` nas
  quatro linhas — a regra de reescrita de Codex já cobre `AskUserQuestion`
  (`codex_question_replacements`, `render_provider.py:190-200`), então o render continua correto nos
  três providers.
- **Impacto positivo:** restaura o quiz estruturado no gate de findings dos quatro comandos; elimina a
  única ocorrência de nome de ferramenta não-Claude no corpo-fonte.
- **Impacto negativo / risco:** em opencode, `AskUserQuestion` no corpo passa a depender do mapeamento
  de nomes em vez do nome nativo literal — regressão de legibilidade para quem lê o `template`
  renderizado. E o achado `ref-tool-map-tool-rewrites-loaded-but-never-emitted-by-render-provider`
  (HIGH, aberto) registra que o rewrite de ferramentas para opencode **não é emitido hoje**, então o
  nome chegaria literal lá.
- **Esforço:** Baixo

### O sinal de "nova dependência" do `03e-adr-gap-check.sh` morre no instante em que o trabalho é commitado — os outros dois sinais do mesmo arquivo sobrevivem

- **Fingerprint:** `auto-adr-gap-check-dependency-signal-blind-to-staged-and-committed-changes`
- **Alvo:** `scripts/hooks/stop/03e-adr-gap-check.sh`
- **Evidência:** `:32` — `if git -C "$REPO_ROOT" diff --unified=0 -- "$manifest" 2>/dev/null | grep -qE '^\+[^+]'; then`
  Compare com os outros dois sinais, que são casamento puro de caminho sobre o conjunto touched:
  `:40` — `printf '%s\n' "$DEVTEAM_TOUCHED_PATHS" | grep -qE '(^|/)(migrations?|db/migrate)/…' && NEW_MIGRATION=1`.
  E `scripts/hooks/lib/touched-paths.sh:22-27` mostra que o conjunto inclui
  `git log --since="${today} 00:00:00" --name-only` — arquivos **commitados hoje**.
  **Reproduzido** em repositório git sintético, com o script real e a lib real:

  | Caso | `package.json` | exit |
  |---|---|---|
  | A | nova dependência **unstaged** | `2` (avisa) |
  | B | mesma dependência **commitada hoje** | `0` (silencioso) |
  | C | migration **commitada hoje** | `2` (avisa) |
  | D | nova dependência **apenas staged** | `0` (silencioso) |

- **Problema:** `git diff` sem `--cached` e sem range de commits vê só a working tree suja. O caminho
  entra no conjunto touched (por isso o `grep` de `:29` passa), mas o `git diff` de `:32` retorna
  vazio assim que o arquivo é staged ou commitado, e `NEW_DEP` fica 0. Os casos C e D provam que a
  assimetria é interna ao arquivo.
- **Por que importa:** o `Stop` hook roda no fim da sessão, quando o normal é o trabalho já estar
  commitado — exatamente o caso B. A safety net automatizada da ADR Trigger Rule (que cita "a
  dependency manifest" como o **primeiro** dos três gatilhos) está cega precisamente no momento em que
  deveria disparar. Uma sessão que adiciona uma dependência pesada e commita nunca recebe o aviso; uma
  que deixa a árvore suja recebe.
- **Proposta:** trocar `:32` por uma varredura que cubra os três estados — `git diff --unified=0
  HEAD~<n> -- "$manifest"` sobre os commits de hoje, unido a `git diff` e `git diff --cached` — ou,
  para manter o custo baixo, alinhar o sinal aos outros dois e aceitar qualquer toque no manifesto
  como gatilho heurístico.
- **Impacto positivo:** restaura o gatilho mais citado da regra no cenário mais comum.
- **Impacto negativo / risco:** aumenta materialmente os falsos positivos — qualquer bump de versão,
  lockfile ou reordenação de `package.json` commitado hoje passa a acender o aviso, que sai com
  `exit 2` e é realimentado no contexto. O comentário `:25-26` documenta que a restrição a linhas
  adicionadas existe justamente para separar "novo pacote" de "bump de versão"; alargar o range sem
  manter esse filtro joga fora a distinção. Além disso `:5` já declara "this never blocks Stop"
  enquanto `:64` faz `exit 2` — mais disparos tornam essa imprecisão mais visível.
- **Esforço:** Médio

### O contrato de "slim install shape" do CI imprime FAIL e deixa o build verde: `$fail` nunca é lido depois do `&&`

- **Fingerprint:** `auto-slim-bootstrap-shape-contract-cannot-fail-the-build`
- **Alvo:** `.github/scripts/ci/slim-bootstrap.sh`
- **Evidência:** `:96` — `[ "$fail" -eq 0 ] && echo "slim install shape OK ✓"`.
  `grep -n "fail" .github/scripts/ci/slim-bootstrap.sh` devolve exatamente: `14` (`set -euo
  pipefail`), `72` (`fail=0`), `76`/`84`/`92` (`fail=1`), `96`. **Não há `exit`, `return` nem teste
  posterior.**
  **Reproduzido** com o padrão isolado sob `set -euo pipefail`: com `fail=1`, o teste falho é o
  comando *anterior* ao `&&` final, então `set -e` não encerra o shell; a execução segue e o script
  termina com `EXIT=0` mesmo tendo impresso `slim: FAIL — expected … not found after strip` em stderr.
- **Problema:** as três asserções da seção 2 (`SLIM_KEEP_LIST` presente, `SLIM_STRIP_LIST`/
  `SLIM_STRIP_DIRS` ausentes) não têm efeito sobre o exit code. O arquivo se descreve em `:2-3` como
  "End-to-end **contract test**", e as seções 3 e 4 do mesmo arquivo usam o padrão correto
  (`|| { echo …; exit 1; }` em `:118-123`, `:125-127`, `:159-163`) — a assimetria é interna.
- **Por que importa:** é o único gate que verifica se o pacote instalado ainda contém os 15 arquivos
  runtime essenciais de `SLIM_KEEP_LIST` (`scripts/update.sh`, `scripts/rollback.sh`, os quatro
  dispatchers de hook, `scripts/lib/preferences-defaults.json`, `strip-tarball.sh`…). Uma mudança em
  `apply_strip` que remova qualquer um deles passa em CI com o FAIL apenas em stderr. Como
  `SLIM_STRIP_LIST` e `SLIM_STRIP_DIRS` estão vazios hoje (`:29-30`), a lista KEEP é a **totalidade**
  da proteção — e ela não protege.
- **Proposta:** trocar `:96` por `if [ "$fail" -ne 0 ]; then echo "slim: shape contract FAILED" >&2;
  exit 1; fi` seguido do `echo … OK ✓`, alinhando ao padrão já usado nas seções 3 e 4.
- **Impacto positivo:** uma linha transforma um contrato decorativo no gate bloqueante que ele se
  declara ser, protegendo os 15 arquivos runtime do pacote slim.
- **Impacto negativo / risco:** se houver divergência latente hoje (um item de `SLIM_KEEP_LIST` que já
  não sobrevive ao strip), o CI fica vermelho imediatamente ao aplicar a correção — o mesmo risco de
  promoção que a política `advisory → blocking` de `01-lint.sh:16-25` existe para gerenciar. Convém
  rodar `bash .github/scripts/ci/slim-bootstrap.sh . /tmp/f` localmente antes de mudar a linha.
- **Esforço:** Baixo

---

## MEDIUM

### `/devteam:rule` e `/devteam:sync-rules` são listados como delegando a `technical-writer`, mas nenhum dos dois corpos faz spawn — e nenhum consta da lista de linhas-filler

- **Fingerprint:** `flow-rule-and-sync-rules-listed-as-technical-writer-but-never-delegate`
- **Alvo:** `commands/rule.md`, `commands/sync-rules.md`, `CLAUDE.md`, `scripts/lib/commands.json`
- **Evidência:** `CLAUDE.md:240` — "| `/devteam:rule` | technical-writer | Cataloging a mandatory
  reuse/standardization rule … |" e `:241` — "| `/devteam:sync-rules` | technical-writer | Scanning
  `docs/` … |".
  `grep -c "Task tool" commands/rule.md commands/sync-rules.md` retorna `0` em ambos; `grep -c
  "run-banner"` também `0` — são os únicos comandos cuja coluna "Agents invoked" nomeia um agente sem
  que o corpo contenha uma única menção à ferramenta de spawn.
  `scripts/lib/commands.json:7` (`_filler_agent_note`) — "…all **nine** name `technical-writer` so the
  filler stays consistent … Do not read those nine rows as a delegation target." Os nove enumerados
  são `update`, `symlinks`, `health-check`, `install`, `explain`, `push`, `merge`, `version`,
  `status` — `rule` e `sync-rules` estão **fora**.
- **Problema:** a tabela usa consistentemente a forma "none — …" para comandos sem agente (`merge`,
  `push`, `commit`, `version`, `status`, `explain`, `health-check`, `install`). Para `rule` e
  `sync-rules` ela nomeia `technical-writer` como se houvesse delegação. E a nota canônica que existe
  justamente para marcar linhas-filler enumera nove entradas sem incluir essas duas.
- **Por que importa:** duas consequências concretas. (1) O único protocolo de prova de execução do
  harness é a run banner devolvida pelo subagente (`skills/architecture/orchestration/SKILL.md`
  § Spawn Integrity, check 3): um comando anunciado como spawn que nunca devolve banner é
  indistinguível de um spawn fantasma para quem audita a sessão. (2) Em opencode o campo `agent` do
  snippet faz o comando rodar **como** aquele agente, então a mesma linha tem semânticas diferentes
  por provider — e a lista que registra quais linhas não devem ser lidas como delegação está
  incompleta em 2 de 11 casos.
- **Proposta:** trocar a coluna de `CLAUDE.md:240-241` para "none — thin wrapper around
  `skills/shared/reuse-guidelines/SKILL.md`" (o que ambos os corpos de fato fazem, via
  `commands/rule.md:7`) e estender a enumeração de `_filler_agent_note` de nove para onze.
- **Impacto positivo:** fecha a última divergência entre a coluna "Agents invoked" e os corpos, e
  completa a única lista que documenta quais linhas `agent:` são filler.
- **Impacto negativo / risco:** é a segunda edição da mesma enumeração em duas semanas — o achado
  aberto `flow-claude-md-no-agent-command-list-says-seven-omits-push-and-merge` já pede que ela vá de
  sete para nove. A lista é mantida à mão em dois arquivos e vai driftar de novo. A correção só é
  durável junto de um gate: `check_command_roster` já lê `commands.json` e o arquivo de comando, e
  poderia derivar o conjunto filler de `grep -c "Task tool"` em vez de confiar numa prosa enumerada.
- **Esforço:** Baixo

---

## LOW-MEDIUM

Nenhum achado original nesta faixa neste pass.

## LOW

Nenhum achado original nesta faixa neste pass.

---

## Descartados por duplicação

| Candidato | Evidência levantada | Gate que rejeitou |
|---|---|---|
| `scripts/check-updates.sh:3` faz `exec` de `hooks/pre-tool-use/01-check-updates.sh`, renomeado para `_disabled-…` (reproduzido: exit **127**); `scripts/update.sh:24` idem | Reprodução direta em cópia de `/tmp` | **Porta 3 (3/3)** — `ref-check-updates-shim-and-update-sh-exec-renamed-away-01-check-updates-hook` (HIGH, aberto) |
| `scripts/lib/command-map.json` é carregado em `render_provider.py:945` e **nunca** consumido — todos os caminhos de saída estão hardcoded | `grep -n "command_map" …` retorna apenas `:945` e o docstring `:6` | **Porta 3 (3/3)** — `ref-tool-map-tool-rewrites-loaded-but-never-emitted-by-render-provider` (HIGH, aberto): mesmo alvo, mesma causa (metadado canônico carregado e nunca emitido), mesma remediação |
| `scripts/hooks/lib/update-check.sh:6` — "Sourced by pre-tool-use/01-check-updates.sh **only**", enquanto o único consumidor real é `session-start.sh:113-116` | Leitura direta | **Porta 3 (2/3)** — `docs-sync-touched-paths-lib-header-says-stop-only-after-02c-sources-it`: causa e remediação idênticas |
| `scripts/hooks/session-start.sh:175` cita `pre-tool-use/02b-full-suite-guard.sh`; o real é `02c-` e `02b-` é telemetria | `ls scripts/hooks/pre-tool-use/` | **Porta 1** — `docs-sync-session-start-comment-cites-nonexistent-02b-full-suite-guard`, aberto |
| `commands/architect.md` sem seção `PLAN GATE` apesar de `commands.json` declarar `"plan_gate": "required"` | `grep -L "PLAN GATE" commands/*.md` | **Status 🟢 Resolved** — `auto-commands-json-plan-gate-field-has-no-consumer-…`, resolvido em 2026-08-12; a instrução do índice proíbe re-propor |
| `commands/architect.md:49-50` pede "### Agents spawned / [list of agents and what they did]", contra a regra "never let a summary template ask for a list of agents from memory" | Leitura do template | **Porta 3 (3/3)** — `skill-orchestration-spawn-integrity-unreachable-from-devteam-commands` |
| `skills/architecture/orchestration/SKILL.md` tem duas seções numeradas `### 5.` e o preâmbulo `:152` diz "Three checks" numa seção com cinco | Leitura direta | **Porta 1** — `skill-orchestration-two-sections-both-numbered-check-5-…` e `skill-orchestration-preamble-says-three-checks-but-section-has-five`, ambos abertos |
| `scripts/update.sh:129` e `scripts/rollback.sh:95` usam caminho **relativo** para invalidar `.context-cache.json` enquanto definem `$USER_DATA_DIR` absoluto; falha em silêncio se executados de um subdiretório | Leitura dos dois arquivos | **Não-duplicado, descartado por consequência insuficiente** — `skills/shared/current-context/SKILL.md:78-82` aplica TTL de 1800 s e invalidação por troca de branch, então a janela de cache obsoleto é ≤30 min e não sobrevive a um `git checkout` |
| `01-lint.sh:92-93` roda shellcheck sobre `scripts` e `helpers`, deixando os 5 scripts de `.github/scripts/ci/**` (615+ linhas) sem cobertura | `find` + leitura de `:90-93` | **Descartado por falta de evidência** — `shellcheck` indisponível neste ambiente, então não foi possível exibir um defeito real nos arquivos não cobertos. Sem defeito concreto é proposta de escopo, não achado. Registrado para um pass futuro com a ferramenta disponível |
| `soften_plan_gate` (`render_provider.py:129-130`) remove incondicionalmente `\n+Task: \$ARGUMENTS` no ramo `opt_out` | `grep -n '\$ARGUMENTS' commands/{update,install,push,merge,sync-rules,status}.md` | **Refutado por evidência** — nenhum dos nove comandos `opt_out` carrega uma linha isolada `Task: $ARGUMENTS`; todos usam `$ARGUMENTS` inline. O `re.sub` é no-op hoje. Risco latente, sem manifestação no HEAD |
