# Eixo B — Referências e consistência (2026-08-21)

**Baseline:** `HEAD` = `a67cac9` · **Baseline anterior:** `c03f898`

## Saída dos gates

| Gate | Resultado | Interpretação |
|---|---|---|
| `helpers/agent-lint.sh` | `agent-lint: clean ✓` · exit 0 | Frontmatter, espelho `tier`↔`model`↔run-banner, identidade de skills (`name` == basename do diretório, unicidade) e roster de comandos ↔ `agents/` estão consistentes. Nenhum achado. |
| `helpers/orphan-template-scan.sh` | `orphan-template-scan: clean ✓` · exit 0 | Toda referência a template resolve. Confirmei independentemente: as 4 ocorrências de `templates/<x>.md` em forma nua (`CLAUDE.md:41,164,171`, `skills/shared/spec-gate/SKILL.md:23`) ou estão em contexto `repo` ou carregam a forma instalada na mesma linha. Nenhum achado. |
| `helpers/orphan-skill-scan.sh` | `ACTION SUGGESTED — duplicate skill loads` (3 arquivos) · exit 0 | As 3 ocorrências são **falsos positivos do scanner**, não cargas duplicadas: em `agents/backend-test-specialist.md:72` e `agents/frontend-test-specialist.md:71` há a carga real, e em `:94`/`:132` apenas uma menção narrativa ("enforced by the Hard rule in …"); em `commands/merge.md:57` há a delegação e em `:77` a menção ao dirty-worktree guard. Causa raiz já registrada — ver § Descartados. |
| `helpers/size-limits.sh` | `ERRORS` + exit **1** | Confirmado: o *warning threshold* do `CLAUDE.md` é empurrado para o array `VIOLATIONS`, o que faz o script sair 1. Rodei `.github/scripts/ci/01-lint.sh` inteiro: **exit 1**. O job `lint` do CI está vermelho no HEAD. Achado HIGH abaixo. |
| Varredura própria — existência de skills citadas | 169 referências `skills/<cat>/<skill>/(SKILL.md\|references/*)` em `agents/ commands/ skills/ CLAUDE.md CLAUDE-md/ docs/*.md templates/` · **0 quebradas** | Nenhuma skill citada em caminho inexistente. |
| Varredura própria — skills órfãs | 1 sem referência: `skills/skill-creator` | Excluída por regra (skill user-invocable, registrada na tabela do `CLAUDE.md`). Nenhum achado. |
| Varredura própria — tabela de comandos | `commands/*.md` = 35 · `scripts/lib/commands.json` = 35 · `CLAUDE.md` = 35 · `README.md` = 34 · `README.pt-BR.md` = 34 | `/devteam:install` ausente dos dois READMEs. Achado MEDIUM abaixo. |

---

## HIGH

### O gate `size-limits.sh` trata o *aviso* de tamanho do `CLAUDE.md` como violação e derruba o job `lint` do CI

- **Fingerprint:** `auto-size-limits-claude-md-warning-counted-as-violation-turns-ci-lint-red`
- **Alvo:** `helpers/size-limits.sh`
- **Evidência:**
  - `helpers/size-limits.sh:86-87` — `"CLAUDE_MD_WARN=600"` / `"CLAUDE_MD_FAIL=700"`
  - `helpers/size-limits.sh:90` — `"    VIOLATIONS+=("  · CLAUDE.md: $CLAUDE_MD_LINES lines (limit: $CLAUDE_MD_FAIL)")"`
  - `helpers/size-limits.sh:92` — `"    VIOLATIONS+=("  ⚠ CLAUDE.md: $CLAUDE_MD_LINES lines (warning threshold: $CLAUDE_MD_WARN)")"`
  - `helpers/size-limits.sh:98` — `"if [ ${#VIOLATIONS[@]} -eq 0 ]; then"` … `helpers/size-limits.sh:122` — `"exit 1"`
  - `.github/scripts/ci/01-lint.sh:88` — `"blocking "size-limits" bash helpers/size-limits.sh"`
  - Execução no HEAD: `bash helpers/size-limits.sh` → exit **1**, imprimindo `⚠ CLAUDE.md: 602 lines (warning threshold: 600)` sob o cabeçalho ` ERRORS — Files exceeding declared limits:`
  - Execução no HEAD: `bash .github/scripts/ci/01-lint.sh` → exit **1**
- **Problema:** o script define dois patamares para o `CLAUDE.md` — `CLAUDE_MD_WARN=600` e `CLAUDE_MD_FAIL=700` — mas os dois ramos do `if/elif` escrevem no mesmo array `VIOLATIONS`. Como a decisão de saída (`exit 1`) depende apenas de `VIOLATIONS` estar não-vazio, o patamar de *aviso* é indistinguível do patamar de *falha*. `git show a67cac9:CLAUDE.md | wc -l` = **602**; o commit `7e62124` (`docs(learn)`, HEAD~1) levou o arquivo de 589 para 602 e cruzou o limiar. O único item impresso é rotulado com `⚠` e com a palavra "warning threshold" — dentro de um bloco cujo cabeçalho diz `ERRORS`.
- **Por que importa:** `size-limits` é um step **blocking** do job `lint` (promovido em 2026-07-31, com a decisão de bloqueio explicitamente delegada ao wrapper: *"The helper's own `--warn-only` flag is deliberately NOT passed — the wrapper owns the blocking decision"*). O CI está vermelho no HEAD por uma condição que o próprio script se propôs a reportar como não-fatal. O efeito prático é pior que uma falha honesta: o próximo mantenedor vê "ERRORS" com um `⚠` e ou (a) gasta a sessão encurtando o `CLAUDE.md` por um motivo que não era bloqueante, ou (b) começa a ignorar o vermelho do `lint` — e aí os checks realmente bloqueantes (`agent-lint`, `check-fingerprint-uniqueness`, `shellcheck`) perdem o sinal.
- **Proposta:** separar os dois canais no script. Manter `VIOLATIONS` só para o que excede um limite declarado (agentes/skills/comandos e `CLAUDE_MD_FAIL`) e criar um array `WARNINGS` para o patamar de 600. Imprimir os dois blocos com cabeçalhos distintos (`ERRORS` / `WARNINGS`) e computar a saída apenas a partir de `VIOLATIONS`. Alternativa mínima e igualmente correta: elevar `CLAUDE_MD_WARN` deixa de ser opção — o problema não é o número, é a categoria.
- **Impacto positivo:** o `lint` volta a verde no HEAD sem mascarar nada; o aviso continua visível e continua servindo ao propósito de pressionar pela fragmentação do `CLAUDE.md` (tema já registrado em `token-claude-md-426-lines-…`, reaberto duas vezes); a semântica "warning ≠ error" volta a ser verdadeira em todos os consumidores do script (CI, `skills/release-prep`).
- **Impacto negativo / risco:** um aviso que não bloqueia é um aviso que pode ser ignorado indefinidamente — é exatamente o que aconteceu com o crescimento do `CLAUDE.md`. Mitigação: manter o aviso no output do CI (que já aparece), e tratar a fragmentação pelo fingerprint que já existe para ela, não por um bloqueio acidental.
- **Esforço:** Baixo

### `check-updates.sh` e `update.sh --check` executam um sub-script de hook que foi renomeado para fora do disco

- **Fingerprint:** `ref-check-updates-shim-and-update-sh-exec-renamed-away-01-check-updates-hook`
- **Alvo:** `scripts/check-updates.sh`
- **Evidência:**
  - `scripts/check-updates.sh:3` — `"exec "$(dirname "${BASH_SOURCE[0]}")/hooks/pre-tool-use/01-check-updates.sh" "$@""`
  - `scripts/update.sh:24` — `"    exec bash "$(dirname "${BASH_SOURCE[0]}")/hooks/pre-tool-use/01-check-updates.sh""`
  - `ls scripts/hooks/pre-tool-use/` → `02-graphify-hint.sh`, `02b-telemetry.sh`, `02c-full-suite-guard.sh`, `_disabled-01-check-updates.sh` — **não existe** `01-check-updates.sh`
  - `commands/update.md:82` — `"bash .dev-team-agents/scripts/check-updates.sh"`
  - `CLAUDE-md/hooks.md:86` — `"| `pre-tool-use/_disabled-01-check-updates.sh` | `01-check-updates.sh` | Superseded — logic moved into `session-start.sh` …"`
  - `CLAUDE.md:245` — `"| `/devteam:update` | runs `update.sh` (which delegates freshness check to `hooks/pre-tool-use/01-check-updates.sh`) | …"`
  - `CLAUDE.md:347` — `"│           └── update-check.sh           ← update-check engine behind pre-tool-use/01-"`
  - `CLAUDE-md/preferences.md:42` — `"| `suppress_notifications` | … | `scripts/hooks/stop/04-notifier.sh`, `scripts/hooks/session-start.sh`, `scripts/hooks/pre-tool-use/01-check-updates.sh` |"`
  - `CLAUDE-md/preferences.md:46` — `"… gates `scripts/hooks/pre-tool-use/01-check-updates.sh` |"`
- **Problema:** o sub-script foi desativado pela convenção de renome (`_disabled-` sai do padrão `^[0-9]{2}[a-z]?-…\.sh$` que o dispatcher exige) e a lógica migrou para `session-start.sh`. A renomeação atualizou **apenas** `CLAUDE-md/hooks.md`. Os dois únicos chamadores diretos por caminho — o shim `check-updates.sh` e o modo `--check` do `update.sh` — continuam apontando para o nome antigo. `exec` sobre um arquivo inexistente é erro fatal do shell (`No such file or directory`, exit 126/127), e ambos os scripts rodam sob `set -euo pipefail`.
- **Por que importa:** `commands/update.md` Step 3 é o caminho canônico do `/devteam:update`: ele zera o TTL, remove o ETag em cache e chama `bash .dev-team-agents/scripts/check-updates.sh`. Esse comando quebra. Pior, o comando trata **ausência de output** como "já está atualizado" (`"**If the script produces no output** → already up to date"`) — um `exec` que falha escreve em `stderr`, não em `stdout`, então o modo de falha é silencioso e **afirmativamente errado**: o `/devteam:update` reporta "Up to date" para um projeto desatualizado. Somando: `CLAUDE.md:245`/`:347` e `CLAUDE-md/preferences.md:42,46` documentam esse mesmo caminho morto como vivo, então nem a documentação nem o comando avisam.
- **Proposta:** (a) repontar `scripts/check-updates.sh:3` e `scripts/update.sh:24` para a rotina viva — o engine é `scripts/hooks/lib/update-check.sh`, já sourced por `scripts/hooks/session-start.sh:113`; expor uma entrada executável dele ou fazer os dois chamarem `session-start.sh` no modo apropriado; (b) no `commands/update.md` Step 3, distinguir "sem output" de "comando falhou" (checar o exit code antes de concluir "Up to date"); (c) corrigir `CLAUDE.md:245,347` e `CLAUDE-md/preferences.md:42,46`.
- **Impacto positivo:** `/devteam:update` volta a detectar versões novas; some a classe de falha "reporta atualizado quando não está", que é a pior forma de bug num mecanismo de atualização; os quatro pontos de documentação passam a descrever a árvore real.
- **Impacto negativo / risco:** repontar para `update-check.sh` exige verificar que o engine funciona fora do contexto de hook (sem stdin JSON, sem as variáveis que `session-start.sh` prepara) — pode ser necessário um pequeno wrapper. Enquanto isso não é feito, o item (b) sozinho já converte a falha silenciosa numa falha visível, o que é estritamente melhor.
- **Esforço:** Médio

### O notifier é documentado como canal ativo em quatro arquivos — inclusive numa skill carregada por todo agente — enquanto o hook está desativado

- **Fingerprint:** `ref-notifier-documented-as-live-in-four-docs-while-hook-file-is-disabled`
- **Alvo:** `skills/shared/notifier/SKILL.md`
- **Evidência:**
  - `ls scripts/hooks/stop/` → `_disabled-04-notifier.sh` (não `04-notifier.sh`); `CLAUDE-md/hooks.md:85` — `"| `stop/_disabled-04-notifier.sh` | `04-notifier.sh` | Pending review — disabled 2026-08-06 …"`
  - `skills/shared/notifier/SKILL.md:52` — `"| `stop/04-notifier.sh` | Session progress (`warning`/`critical`) + tip (`info`) | After each turn |"`
  - `skills/shared/notifier/SKILL.md:60` — `"**stop/04-notifier conditions:**"`
  - `skills/shared/notifier/SKILL.md:102` — `"The stop hook increments a per-session turn counter stored at `.dev-team-agents/user-data/.notifier-state`."` — `grep -n "notifier-state" scripts/hooks/stop.sh scripts/hooks/session-start.sh` não retorna nada
  - `skills/shared/project-context/SKILL.md:61` — `"When emitting system notifications (context window warnings, missing config, tips), load `skills/shared/notifier/SKILL.md` …"` (project-context é carregada por todos os agentes)
  - `CLAUDE-md/notifications.md:27` — `"| `stop/04-notifier.sh` | Session progress: context window warnings, tip of session, uncommitted-progress warning |"`
  - `CLAUDE-md/notifications.md:53` — `"`stop/04-notifier.sh` fires a `warning` at most once per session when all three hold: the turn count has reached `session_no_commit_turns` (default `8`) …"`
  - `CLAUDE-md/preferences.md:50` — `"| `session_no_commit_turns` | `8` | Turn count after which a `warning` fires … | `scripts/hooks/stop/04-notifier.sh` |"`
  - `skills/shared/setup-health-check/references/checks-list.md:556` — `"| `session_head` missing | OK — created automatically by `session-start.sh` on next session; until then the uncommitted-progress warning stays silent …"` — contradiz `skills/shared/setup-health-check/SKILL.md:76` — `"| 9 | Notifier | Disabled by design (`_disabled-04-notifier.sh`) — do not report as missing …"`, no mesmo pacote de skill
- **Problema:** o desligamento de 2026-08-06 atualizou `CLAUDE-md/hooks.md` e a Categoria 9 do health-check, e parou aí. Quatro outros lugares continuam descrevendo o hook como vivo. O caso mais grave é `skills/shared/notifier/SKILL.md`, que é **shipped** e alcançada por `project-context` — ou seja, todo agente instalado lê uma tabela de "Channel Rules" afirmando que um script inexistente dispara avisos "After each turn". A funcionalidade de *uncommitted-progress warning* está inteiramente morta e, ainda assim, tem prosa dedicada em `CLAUDE-md/notifications.md:53`, uma linha de tabela em `CLAUDE-md/preferences.md:50`, uma condição em `notifier/SKILL.md:60` e um efeito colateral vivo (`session-start.sh` gravando `session_head` para um consumidor que não existe).
- **Por que importa:** documentar um mecanismo desligado como ligado é o modo de falha mais caro deste repositório, porque o público-alvo é um agente. Um agente que lê `notifier/SKILL.md:52` conclui que o aviso de janela de contexto é responsabilidade do hook e pode legitimamente **não emitir** o aviso que a mesma skill pede dele em `:72-74` — a redundância que existia por design (hook + agente) virou um único emissor que acredita ser redundante. E `checks-list.md:556` faz o `/devteam:health-check` reportar como saudável um caminho que nunca dispara, contradizendo a Categoria 9 do próprio arquivo de skill que o carrega.
- **Proposta:** (a) em `skills/shared/notifier/SKILL.md`, remover a linha `:52` da tabela de canais e o bloco `:60-64`, e reescrever `:102` — a seção "Context Window Heuristic (shell hooks)" descreve um contador que ninguém incrementa; o que sobra e continua válido é a emissão feita pelo próprio agente (`:70-98`); (b) em `CLAUDE-md/notifications.md`, remover `:27` da tabela de canais e a seção *Uncommitted-Progress Warning* (`:53`), ou marcá-las explicitamente como suspensas com ponteiro para `CLAUDE-md/hooks.md § Disabled Hooks`; (c) em `CLAUDE-md/preferences.md:40,41,42,48,49,50`, corrigir a coluna "Read by": para `context_window_percent_warning`/`_limit` o leitor real hoje é o agente via `notifier/SKILL.md`, e `session_no_commit_turns`, `transcript_multiplier` e `model_max_tokens` **não têm leitor algum** (verificado: só aparecem em `install.sh`, `preferences-defaults.json`, no próprio `_disabled-04-notifier.sh` e em docs); (d) corrigir `checks-list.md:556`.
- **Impacto positivo:** a documentação volta a descrever o que roda; os agentes deixam de contar com um canal inexistente; fica visível que três chaves de `preferences.json` estão inertes, o que é a informação necessária para decidir entre reativar o hook ou removê-las.
- **Impacto negativo / risco:** o `CLAUDE-md/hooks.md:85` classifica o notifier como "Pending review" — ou seja, a reativação está em aberto. Apagar a documentação agora torna a reativação mais cara. Mitigação: preferir a variante "marcar como suspenso com ponteiro" em (b) e (c) a apagar, e reservar a remoção dura para `notifier/SKILL.md`, que é o arquivo shipped e o único onde a informação errada causa dano de comportamento.
- **Esforço:** Médio

---

## MEDIUM-HIGH

Nenhum achado nesta severidade.

---

## MEDIUM

### A tabela de comandos do `README.md` e do `README.pt-BR.md` lista 34 dos 35 comandos — `/devteam:install` nunca chegou lá

- **Fingerprint:** `docs-sync-readme-command-table-omits-devteam-install-in-both-languages`
- **Alvo:** `README.md`
- **Evidência:**
  - `ls commands/*.md | wc -l` → **35**; `scripts/lib/commands.json` → **35** entradas; linhas `| \`/devteam:…\`` únicas: `CLAUDE.md` → **35**, `README.md` → **34**, `README.pt-BR.md` → **34**
  - `grep -rn "devteam:install" README.md README.pt-BR.md docs/*.md` → **nenhum resultado**
  - `CLAUDE.md:248` (linha da tabela) — `"| `/devteam:install` | loads `skills/devops/tool-installers/SKILL.md`; no agents spawned | Installing/configuring a complementary tool from the closed allowlist — `rg`, `fd`, `jq`, `ast-grep`, `tokei`, `delta`, `graphify`. …"`
  - `git log --oneline -3 -- commands/install.md` → `c9fd760 feat(commands): add /devteam:install as the tool-installer entrypoint`
  - `CHANGELOG.md:93` e `:114` mencionam `/devteam:install` — apenas em correções posteriores, nunca na entrada de introdução
- **Problema:** `c9fd760` criou o comando e registrou-o em `commands.json` e no `CLAUDE.md`, mas não nos dois READMEs. A Auto-Docs Rule do `CLAUDE.md` exige exatamente isso (*"automatically update `README.md`, `README.pt-BR.md`, and `CLAUDE.md`"*), e a README Sync Rule não pega o caso: EN e pt-BR estão igualmente errados, então o gate estrutural `.github/scripts/ci/02-readme-sync.sh` — que compara EN contra pt-BR, não contra a árvore — passa limpo. É o ponto cego declarado no cabeçalho do próprio gate.
- **Por que importa:** os READMEs são o único catálogo voltado ao usuário final. O `CLAUDE.md` não é instalado no projeto do usuário; `commands.json` é metadado de render. Um usuário instalado que queira instalar `rg`/`fd`/`jq`/`ast-grep` não tem como descobrir que existe um comando para isso — e `/devteam:health-check` Categoria 13 e `graphify-setup` **delegam** a esse comando (`CLAUDE.md:248`: *"The single entrypoint for tool installs"*), então o único ponto de entrada documentado do fluxo é invisível na porta de entrada da documentação.
- **Proposta:** adicionar a linha de `/devteam:install` na tabela de comandos dos dois READMEs, no mesmo commit, na posição correspondente à do `CLAUDE.md` (junto de `/devteam:health-check` e `/devteam:symlinks`, que já estão lá). Traduzir a célula de descrição para o pt-BR seguindo o padrão das linhas vizinhas para não quebrar a paridade estrutural do gate.
- **Impacto positivo:** fecha a última lacuna entre o roster real (35) e o catálogo do usuário; restaura a invariante "README lista todos os comandos", que é o que torna qualquer futura divergência detectável por contagem simples.
- **Impacto negativo / risco:** duas linhas a mais em dois arquivos já longos, e a paridade EN↔pt-BR precisa ser mantida na mesma alteração (o gate `02-readme-sync.sh` falha se só um dos dois for tocado). Risco real: nenhum — mas vale notar que corrigir o sintoma não corrige a causa; a contagem `commands/` vs. `README` não é verificada por gate algum e voltará a divergir no próximo comando novo.
- **Esforço:** Baixo

### Três referências apontam para uma seção "Hook Sub-script Convention" do `CLAUDE.md` que foi movida para `CLAUDE-md/hooks.md`

- **Fingerprint:** `ref-three-pointers-to-claude-md-hook-subscript-convention-moved-to-hooks-md`
- **Alvo:** `CLAUDE-md/notifications.md`
- **Evidência:**
  - `CLAUDE-md/notifications.md:65` — `"Canonical version of this table lives in `CLAUDE.md` → "Stop Hook Sub-script Convention", together with the mandatory `NN[a-z]-name.sh` filename pattern the dispatcher enforces."`
  - `scripts/hooks/stop.sh:53` — `"# NN-name.sh or NNx-name.sh (see CLAUDE.md, "Stop Hook Sub-script Convention")."`
  - `scripts/hooks/pre-tool-use.sh:17` — `"# NN-name.sh or NNx-name.sh (see CLAUDE.md, "PreToolUse Hook Sub-script"` / `:18` — `"# Convention"). …"`
  - `grep -n "Sub-script Convention" CLAUDE.md` → **nenhum resultado**; as duas seções vivem em `CLAUDE-md/hooks.md:21` (`### Stop Hook Sub-script Convention`) e `CLAUDE-md/hooks.md:48` (`### PreToolUse Hook Sub-script Convention`)
  - Contraste com o mesmo padrão já corrigido: `scripts/hooks/stop/_disabled-04-notifier.sh:2` — `"# DISABLED (2026-08-06) — pending review, see CLAUDE-md/hooks.md § Disabled Hooks."`
- **Problema:** a extração das seções de hook para `CLAUDE-md/hooks.md` (commit `2b436ea`) não repontou os três lugares que citavam a seção pelo nome dentro do `CLAUDE.md`. Dois deles são comentários em `scripts/hooks/stop.sh` e `scripts/hooks/pre-tool-use.sh` — os **dispatchers**, arquivos que **shipam** para o projeto do usuário, onde `CLAUDE.md` designa um arquivo completamente diferente (o CLAUDE.md do projeto do usuário). O terceiro é um ponteiro de "cópia canônica" numa tabela que se declara reprodução.
- **Por que importa:** o valor do ponteiro é permitir que quem mexe no dispatcher confira a convenção antes de nomear um sub-script novo. Um ponteiro que não resolve devolve o leitor para um arquivo sem a seção — no repo, ele conclui que a convenção não está documentada; no projeto instalado, ele lê o `CLAUDE.md` do projeto e não encontra nada. A convenção de nomes é o que impede um arquivo `.sh` solto de ser auto-executado a cada tool call, então é exatamente o tipo de regra que não pode depender de um ponteiro morto. O ponteiro de `notifications.md:65` tem um efeito adicional: ele justifica manter uma **segunda cópia** da tabela ("Reproduced here"), e com a fonte declarada inexistente essa cópia deixa de ter um original contra o qual ser reconciliada.
- **Proposta:** repontar os três para `CLAUDE-md/hooks.md`, na mesma forma já usada em `_disabled-04-notifier.sh:2` (`see CLAUDE-md/hooks.md § Stop Hook Sub-script Convention`). Nos dois dispatchers, **não** usar `.dev-team-agents/CLAUDE-md/hooks.md`: `scripts/install.sh:369` tem `KEEP_ROOT=(agents scripts skills templates commands)`, ou seja, `CLAUDE-md/` não é instalado. A forma correta ali é nomear a origem explicitamente ("see CLAUDE-md/hooks.md § … in the dev-team-agents source repo"), o que também deixa registrado que a convenção é regra de autoria, não de runtime do projeto do usuário.
- **Impacto positivo:** três ponteiros voltam a resolver; a tabela duplicada em `notifications.md` volta a ter um original identificável, o que é pré-requisito para eventualmente eliminá-la; fica explícito nos dois dispatchers shipados que a convenção mora no repo fonte e não no projeto.
- **Impacto negativo / risco:** baixo — é edição de comentário e de prosa. O risco residual é o oposto do desejado: um ponteiro que diz "source repo" não ajuda quem está lendo o dispatcher dentro de um projeto instalado. Isso é inerente a `CLAUDE-md/` não ser empacotado e não é resolvível repontando; a alternativa (empacotar `CLAUDE-md/`) é uma decisão de escopo de pacote, não um reparo de referência.
- **Esforço:** Baixo

---

## LOW-MEDIUM

Nenhum achado nesta severidade.

---

## LOW

Nenhum achado nesta severidade.

---

## Descartados por duplicação

| Candidato | Porta | Fingerprint colidido |
|---|---|---|
| `orphan-skill-scan.sh` reporta carga duplicada de `skills/testing/test-pyramid/SKILL.md` em `agents/backend-test-specialist.md` (`:72` carga, `:94` menção narrativa) e `agents/frontend-test-specialist.md` (`:71` carga, `:132` menção narrativa) | 3 (semântica — 3/3: alvo = o scanner, causa = não distingue diretiva de carga de menção em prosa, remediação = tornar o matcher sensível ao contexto) | `ref-orphan-skill-scan-reports-design-system-audit-duplicate-load-in-ui-ux-designer-introduced-in-uknown-commit` |
| `orphan-skill-scan.sh` reporta carga duplicada de `skills/shared/worktree/SKILL.md` em `commands/merge.md` (`:57` delegação real, `:77` menção ao dirty-worktree guard) | 3 (semântica — 3/3, idem acima; alvo novo é `commands/merge.md`, mas causa e remediação são as mesmas e o alvo real do reparo é o scanner) | `ref-orphan-skill-scan-reports-design-system-audit-duplicate-load-in-ui-ux-designer-introduced-in-uknown-commit` |
| `CLAUDE.md:300` (File Structure) descreve `templates/` como "adr-template.md, plan-template.md, runbook-template.md" — a árvore tem 5 arquivos, faltam `spec-template.md` (citado pelo próprio `CLAUDE.md:171`) e `reuse-guidelines-template.md` | 3 (semântica — 3/3: alvo = bloco File Structure do `CLAUDE.md`, causa = bloco não acompanhou a árvore, remediação = completar a enumeração). Mesmo tratamento já dado ao candidato `docs/prompts/` registrado em `_index.md:338` | família `ref-claude-md-file-structure-omits-helpers-and-privacy-and-claude-md-folder` / `…-skills-subtree-omits-…` / `…-scripts-enumeration-omits-…` |
| `CLAUDE-md/notifications.md:66-76` — a tabela reproduzida da convenção de sub-scripts do Stop omite `02b-`, `03c-`, `03d-`, `03e-` e ainda lista `99-graphify-refresh.sh`, desativado | 3 (semântica — 3/3: alvo = a tabela triplicada em `notifications.md`, causa = conteúdo de notificação vive em três lugares e deriva, remediação = deduplicar) | `ref-notification-system-content-triplicated-across-04-notifier-sh-notifier-skill-and-claude-md-notifications-md-stop-subscript-table-already-drifted-omitting-05-telemetry` |
| `CLAUDE.md:92` e `CLAUDE.md:313` dizem que `size-limits.sh` "enforces 205 (200 content + 5 run-banner)"; o script tem `AGENT_LIMIT=211` e o comentário fala em 11 linhas de boilerplate | 5 (estado — já no conjunto OPEN) | `agent-line-cap-205-documented-in-claude-md-vs-211-enforced-by-size-limits` |
| `docs/reports/_index.md:103` — legenda desatualizada ("All 131 entries below are unmarked") | 5 (estado — já no conjunto OPEN, exclusão explícita no escopo desta passagem) | `docs-sync-reports-index-md-99-legend-…` |
