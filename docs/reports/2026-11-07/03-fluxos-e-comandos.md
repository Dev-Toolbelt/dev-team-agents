# Eixo C — Fluxos, Comandos e Automação — 2026-11-07

**Varredura:** `git diff --name-only b64428b..HEAD` (880 arquivos) filtrado para o escopo do eixo —
19 arquivos em `commands/`, 22 em `scripts/hooks/**`, e `install.sh` / `install-cli.sh` /
`install-codex.sh` / `install-opencode.sh` / `install-provider.sh` / `update.sh` /
`lib/render_provider.py` / `lib/provision-tools.sh`. Leitura integral dos 4 comandos novos
(`orchestrate`, `release-qa`, `push`, `down`), de `agents/orchestrator.md`, dos 5 dispatchers de
hook e dos 16 sub-scripts tocados no delta.

Verificações cruzadas que saíram **consistentes** (registro negativo): `commands.json` × frontmatter
× `tiers.json`; matcher `PostToolUse` em 4 cópias; `PostToolUseFailure` e `SubagentStop` em
`install.sh` × `hooks.py` × `codex_hooks_merge.py`; 14 categorias de health-check ×
`checks-list.md`; flags de `doc-path.sh` (todas implementadas); `OPENCODE_PRIMARY_AGENTS` e
`REVIEWERS` (ambos com teste de paridade); 6 passos de `release-qa/SKILL.md` × comando.

**31 candidatos levantados → 8 achados, 5 descartados por duplicação (+1 cross-eixo), 17 refutados
por evidência própria.**

---

## MEDIUM-HIGH

### A tabela Route do orchestrator cobre 10 dos 42 comandos e manda improvisar o resto, contra a sua própria frase de abertura

- **Fingerprint:** `flow-orchestrator-route-table-covers-10-of-42-commands-no-gate`
- **Alvo:** `agents/orchestrator.md`
- **Evidência:** `agents/orchestrator.md:42` — "Classify each request before acting, and **reuse the flow that already exists for it instead of improvising one**"; a tabela `:44-51` nomeia 10 comandos (`plan`, `sprint`, `fix`, `backend`, `frontend`, `mobile`, `fullstack`, `review`, `security`, `qa`) e fecha com `:51` — "| Anything else | Orchestration § Orchestration Flow, with agents from the Agent Roster only |"; `ls commands/*.md | wc -l` = **42**. `skills/shared/auto-routing/SKILL.md:32` declara **MANDATORY** que "A **purely technical decision** with closed scope (ADR, trade-off, architecture, 'should we use X') goes to `architect` … a database-engine or data-model choice to `dba`" — nenhuma das duas linhas existe na tabela. `commands/orchestrate.md:12` manda seguir essas seções "as your own operating rules for the rest of this session". `git grep -n orchestrator -- helpers/agent-lint.sh tests/` só encontra os gates de "nunca spawnar o orchestrator" (`agent-lint.sh:448-457`) e de `orchestrator_default`; nada confere a tabela contra `commands/` nem contra `scripts/lib/commands.json`, que já é o catálogo per-command com `description` para todos os 42.
- **Problema:** 32 comandos — incluindo `refactor`, `architect`, `dba`, `adr`, `spec`, `release-qa`, `audit`, `commit`, `pr`, `push`, `merge`, `up`/`down`, `docs`, `design`, `relayout`, `seo`, `devops`, `learn` — caem no catch-all, que não manda procurar o comando correspondente. Para `architect` e `dba` isso contradiz diretamente uma regra rotulada MANDATORY no bloco de roteamento injetado no `CLAUDE.md` do projeto.
- **Por que importa:** com `orchestrator_default` ligado (ADR-0062, `install.sh` Step 7c grava a chave), **toda** sessão Claude Code roteia por essa tabela. Um pedido de refactor ou de ADR passa a ser orquestrado ad-hoc e perde os gates próprios do comando (PLAN GATE `required` em `refactor`, `architect`, `adr`, `spec`, `release-qa`, conforme `scripts/lib/commands.json`).
- **Proposta:** trocar as 6 linhas da tabela por 1 linha de regra ("um `/devteam:` que cobre o pedido é o fluxo; o catálogo é `devteam catalog commands`") mais as 3 linhas que a tabela acrescenta de fato (planning → `plan`, sprint aprovado → `sprint`, bug → `fix`); e adicionar ao `agent-lint.sh` uma checagem de que todo comando citado na tabela existe em `commands/`.
- **Impacto positivo:** elimina 32 lacunas de roteamento e a contradição com `auto-routing` § Planning; a tabela deixa de ser uma segunda autoridade de roteamento a manter em sincronia com 42 arquivos.
- **Impacto negativo / risco:** o orchestrator passa a depender do catálogo em runtime (um `devteam` fora do PATH deixa o roteamento sem lista); e a decisão "qual comando cobre isto" sai de uma tabela auditável para o julgamento do modelo em mais casos.
- **Esforço:** Baixo

### `/devteam:commit` não tem ramo para a recusa do secret guard da ADR-0059 e oferece "Commit anyway" para um gate sem bypass

- **Fingerprint:** `flow-commit-md-no-branch-for-adr-0059-secret-guard-refusal`
- **Alvo:** `commands/commit.md`
- **Evidência:** `commands/commit.md:121` abre o "Step 4.5 — Pre-commit gate" e `:156` enumera os gates — "If any gate (lint, type-check, tests, or commit message validation) returns non-zero"; `:158` oferece "**Fix and re-stage** (recommended), **Commit anyway**, or **Abort**". `grep -n "gitleaks\|ADR-0059" commands/commit.md` → **0 ocorrências**. `scripts/hooks/pre-tool-use/03b-staged-secret-guard.sh:217-226` recusa o `git commit` com exit 2 e `:25` declara "There is deliberately no environment-variable escape hatch". `commands/commit.md:166` manda "**execute the commits directly** using `git commit`". Além disso `:160` aponta para `skills/shared/feature-learn/SKILL.md:102`, cujo item 5 roda **o mesmo comando** — "Secret scan over the learn-staged files before the pre-commit gate: `gitleaks git --pre-commit --staged --redact`" — que não é escopado aos arquivos de learn e cuja ação ("A hit unstages that file") contradiz a do hook (recusar o commit).
- **Problema:** o único comando que executa commits não conhece o gate que pode recusá-los. A opção mais próxima da recusa ("Commit anyway") é inalcançável por desenho, e nenhuma etapa instrui as duas saídas documentadas pelo hook (`gitleaks:allow` na linha, ou fingerprint em `.gitleaksignore`). Em paralelo, um `/devteam:commit` que rodou o passe de learn paga duas execuções de gitleaks sobre o mesmo índice, com veredictos divergentes.
- **Por que importa:** no `HEAD`, um commit com falso positivo de gitleaks deixa o `/devteam:commit` em loop — o agente vê exit 2, escolhe "Commit anyway", reexecuta `git commit`, é recusado de novo. E o item 5 do learn pode **desindexar silenciosamente um arquivo de código do usuário** (o comando varre todo o índice, não só os docs de learn) antes do hook sequer ver o commit.
- **Proposta:** acrescentar ao `:156` o secret guard como quinto gate, com ramo próprio (sem "Commit anyway"): mostrar as linhas `arquivo:linha (regra)`, oferecer **Remover o valor** / **Marcar com `gitleaks:allow`** / **Fingerprint em `.gitleaksignore`** / **Abortar**; e retirar o item 5 de `feature-learn` (ou escopá-lo com `--no-git -s <paths>`), já que o hook o cobre.
- **Impacto positivo:** fecha o único caminho de recusa sem tratamento do fluxo de commit e remove uma varredura gitleaks por commit (segundos em repositórios grandes).
- **Impacto negativo / risco:** sem o item 5, um projeto com `DEVTEAM_SKIP_TOOLS=1` perde o fallback por grep que hoje existe para os docs de learn — fica dependendo do hint do hook; e `commands/commit.md` passa a citar uma ADR específica, mais um ponteiro a manter.
- **Esforço:** Médio

### A varredura semente do Eixo A é cega a 7 famílias de stack e não vê 36 linhas de `agents/` e `commands/`, incluindo uma adicionada neste delta

- **Fingerprint:** `gov-seed-scan-regex-blind-to-flutter-swift-kotlin-rn-dotnet-rust-supabase`
- **Alvo:** `docs/reports/_prompt-auditoria.md`
- **Evidência:** `docs/reports/_prompt-auditoria.md:143-146` traz o regex semente de 40 termos; nenhum dos termos `flutter`, `swift`, `kotlin`, `react native`, `dotnet`, `rust`, `supabase` está na lista. Medido: `grep -rinE 'flutter|swift|kotlin|react native|dotnet|\brust\b|supabase' agents/ commands/` → **36 linhas**, entre elas `agents/mobile-developer.md:143` (5× flutter), `agents/backend-developer.md:76` e `agents/frontend-developer.md:124` (supabase), `commands/mobile.md:12,21,28,29`, `commands/tester.md:24`, `commands/review.md:48`, `commands/design.md:21`, `commands/fix.md:23,29` e **`commands/sprint.md:74`** — "`mobile-developer` for Flutter/native" —, linha reescrita neste delta. `commands/spec.md:44` ("in a tests-only spawn for **Flutter/native**") dá **zero hits** sob o regex semente, confirmado por execução.
- **Problema:** a "varredura semente **obrigatória**, antes de qualquer leitura" tem falso-negativo estrutural para mobile nativo, cross-platform, .NET, Rust e Supabase — exatamente as famílias que o Eixo A existe para pegar, e as que o delta mexeu.
- **Por que importa:** os passes de 2026-09-11, 2026-10-10 e seguintes registram "Eixo A: **nenhum achado original**" com ~124 linhas de hit; as 36 linhas acima nunca entraram nesse denominador. `commands/sprint.md:74` é uma linha de spawn nova e prescritiva de stack que a semente deste pass não mostrou.
- **Proposta:** acrescentar `flutter|swift|kotlin|react[- ]native|dotnet|\.net|rust|cargo|supabase|nuxt|flask|fastapi` ao regex e, no mesmo passe, ancorar com `\b` os termos curtos (`pip`, `nest`, `express`, `rspec`, `react`).
- **Impacto positivo:** +36 linhas de cobertura em `agents/`+`commands/` (≈+29% sobre as ~124 atuais) nas famílias hoje invisíveis; combinado com o `\b`, a razão sinal/ruído melhora nas duas pontas (medido: `pip` 18 hits → 0 com `\b`; `nest` 1 → 0; `rspec` 2 → 0).
- **Impacto negativo / risco:** o Eixo A tende a reportar mais candidatos nos próximos passes, com custo de triagem; `supabase` e `docker` em tabelas de detecção legítimas vão gerar falsos positivos que a regra de descarte de `:150-152` precisa absorver.
- **Esforço:** Baixo

## MEDIUM

### Quatro hooks leem o mesmo tipo de preferência `*_active` com três ordens de precedência diferentes e um grep cru, sem helper compartilhado

- **Fingerprint:** `flow-hook-prefs-gates-three-precedence-orders-raw-grep-no-helper`
- **Alvo:** `scripts/hooks/lib/data-dirs.sh`
- **Evidência:** quatro consumidores, três ordens. `scripts/hooks/session-start.sh:452` — `[ -f "$PREFS_FILE" ] && grep -qE '"branch_overlap_active"…false'`, com `:57` `PREFS_FILE="$(devteam_prefs_file "$MAIN_REPO_ROOT")"` (**só MAIN**). `scripts/hooks/post-tool-use/04-branch-overlap.sh:41-46` — o comentário diz "The preferences live in the MAIN checkout **only, never in a linked worktree**" e o código imediatamente abaixo testa `[ -f "$CH_ROOT/.dev-team-agents/resolved/preferences.json" ]` **primeiro** (**worktree antes de MAIN**). `scripts/hooks/post-tool-use/03-repair-detect.sh:46-47` e `scripts/hooks/user-prompt-submit/05-recall.sh:46-47` — `devteam_prefs_file "$CH_MAIN"` com fallback para o root (**MAIN antes de worktree**). `grep -n "^devteam_prefs" scripts/hooks/lib/data-dirs.sh` → apenas `devteam_prefs_file()` e `devteam_prefs_is_legacy()`; não existe helper de "esta preferência está desligada".
- **Problema:** a mesma decisão ("esta preferência booleana está `false`?") está replicada em 4 sítios com 3 precedências e um `grep -qE` sobre o JSON. Num worktree com projeção `resolved/`, `session-start.sh` (o refresher) e `04-branch-overlap.sh` (o consumidor) podem ler arquivos diferentes e discordar. E `04` tem um comentário que afirma o oposto do que o código abaixo faz.
- **Por que importa:** os três hooks novos do delta entregam hints ao modelo. Um `branch_overlap_active: false` posto no arquivo "errado" produz o pior dos dois mundos: o refresher roda em background (gastando `git fetch`) e o consumidor cala, ou o inverso. O grep cru também lê `false` como `true` se o JSON vier com chave e valor em linhas diferentes — formato que `devteam prefs set` não produz hoje, mas que nada impede.
- **Proposta:** adicionar `devteam_prefs_off <root> <key>` a `scripts/hooks/lib/data-dirs.sh` (uma precedência, uma leitura, tolerante a formatação) e fazer os 4 sítios chamá-la; corrigir o comentário de `04-branch-overlap.sh:41` para descrever a ordem que ele usa.
- **Impacto positivo:** 1 definição em vez de 4; a precedência passa a ser uma decisão única e testável, e o comentário deixa de contradizer o código ao lado.
- **Impacto negativo / risco:** mais uma função no `data-dirs.sh`, que já tem fan-in de 12 scripts; e unificar a precedência **muda o comportamento efetivo de um dos 4 hooks em worktrees** — precisa de teste antes.
- **Esforço:** Baixo

### O gate de findings de 4 comandos de implementação despacha por rótulos pt-BR literais que o próprio bloco manda traduzir

- **Fingerprint:** `flow-findings-gate-dispatch-keyed-to-hardcoded-pt-br-labels-in-four-commands`
- **Alvo:** `commands/backend.md` (+ `frontend.md`, `fullstack.md`, `mobile.md`)
- **Evidência:** `commands/backend.md:66` — "Read `.dev-team-agents/resolved/preferences.json` → `language` (default: `en`) and **present the quiz in that language**"; `:74-78` o JSON com `"label": "Aplicar todos os findings (Recomendado)"`, `"Não aplicar nada agora"`, `"Outro"`; e `:85-89` a tabela de despacho — "- **Aplicar todos** → spawn `backend-developer` + `backend-test-specialist` in parallel", "- **Não aplicar nada agora** → end the review", "- **Outro** → ask the user to describe their desired approach". Mesmo padrão em `frontend.md:59/67/78`, `fullstack.md:65/73/84`, `mobile.md:59/67/78`. Dois bullets (`**Code Review**`, `**QA**`) não casam literalmente com rótulo nenhum, nem em português.
- **Problema:** a condicional que decide **quais agentes re-spawnar** é keyed por string literal numa língua que o default de instalação (`en`) nunca renderiza. É uma condicional implícita onde deveria haver chave estável.
- **Por que importa:** no default `en`, o modelo apresenta rótulos em inglês e depois tem de remapeá-los para as cinco chaves em português para escolher o ramo — e dois dos cinco ramos já são abreviações que não casam com rótulo nenhum. Ambiguidade no único ponto desses comandos que re-spawna agentes de correção.
- **Proposta:** substituir os rótulos literais por chaves de opção (`apply_all`, `review_only`, `qa_only`, `none`, `other`) na tabela de despacho, mantendo o JSON como exemplo explicitamente marcado "example, render in the user's language".
- **Impacto positivo:** o despacho de 5 ramos × 4 comandos deixa de depender de tradução; 20 condicionais ficam explícitas.
- **Impacto negativo / risco:** o JSON de exemplo em português continua convidando a copiar rótulos; se não for marcado como exemplo, o conserto é parcial. E `AskUserQuestion` não retorna ids — o mapeamento ainda fica por posição/semântica, não por contrato de ferramenta.
- **Esforço:** Baixo

## LOW-MEDIUM

### A regra de descartar `--yes` em `/devteam:install` está listada depois dos ramos que ela precisa anteceder

- **Fingerprint:** `flow-install-md-yes-strip-rule-listed-after-the-branch-it-must-precede`
- **Alvo:** `commands/install.md`
- **Evidência:** `commands/install.md:21-24`, na ordem em que estão escritos: `:21` "**No argument, or the literal `list`** → run `devteam tools list` … Stop."; `:22` "**`all`** → Step 2 with no names."; `:23` "**One or more space-separated names** → Step 2 with those names."; `:24` "**`--yes`** → **drop it before parsing**. It confirmed the old per-install question, which no longer exists". `:3` `argument-hint: [tool1 tool2 ...|all|list]` já não menciona `--yes`. `commands/install.md:30` — "An unknown name makes the command exit 2 and print the known names".
- **Problema:** a instrução "drop it before parsing" é o quarto item de uma lista lida em ordem. `install all --yes` casa `:23` ("one or more names") antes de `:24` ser lido, e vira `devteam tools install all --yes` → nome desconhecido → exit 2. E `--yes` sozinho, após o descarte, não tem ramo declarado.
- **Por que importa:** o CHANGELOG promete que `--yes` "is accepted and ignored until the next minor version"; seguido à risca na ordem escrita, o comando falha com exit 2 em vez de ignorar a flag.
- **Proposta:** mover a regra para um pré-passo acima da lista ("Step 0 — descarte `--yes`/`--no-tools` de `$ARGUMENTS`; se nada sobrar, trate como `list`") e deixar os três ramos intactos.
- **Impacto positivo:** o único caminho de compatibilidade do comando deixa de depender de o leitor ler a lista fora de ordem.
- **Impacto negativo / risco:** mais um passo numerado num comando de 44 linhas que foi deliberadamente encurtado neste delta (111 linhas removidas).
- **Esforço:** Baixo

### `subagent-start.sh` e `subagent-stop.sh`, criados no mesmo delta, têm políticas de exit opostas e só uma delas justifica a sua

- **Fingerprint:** `auto-subagent-start-stop-dispatchers-opposite-exit-policies-undocumented`
- **Alvo:** `scripts/hooks/subagent-start.sh`
- **Evidência:** `subagent-start.sh:5` — "a non-zero exit from any sub-script **is propagated**" e `:8` — "**Exits 0 always on its own**, prints nothing"; o código `:37-42` propaga (`exit $EXIT_CODE`, com exit 2 vencendo exit 1). O irmão `subagent-stop.sh:5-6` força o contrário **e diz por quê**: "every sub-script runs and the dispatcher **always exits 0**: an exit 2 on a stop event would keep a Codex child running, and a board hook must never do that" — `:50` `exit 0`. O único sub-script de `subagent-start/` declara `01-task-board.sh:8` "Exits 0 always, prints nothing", logo a propagação nunca é exercida hoje.
- **Problema:** o cabeçalho afirma as duas coisas ao mesmo tempo ("propagado" / "sempre 0"), e a divergência de política entre os dois dispatchers irmãos não tem razão registrada em nenhum dos dois — ao contrário do `stop`, que documenta a sua.
- **Por que importa:** o contrato de exit é o que um sub-script futuro vai ler para decidir se pode recusar um evento. Em `SubagentStart` uma propagação de exit 2 bloqueia o spawn do filho no Codex; hoje isso é inalcançável, mas nada no arquivo diz se é desejado ou acidental.
- **Proposta:** escolher uma política e escrevê-la em uma frase com a razão — se `SubagentStart` pode recusar um spawn, remover o "Exits 0 always on its own" de `:8`; se não pode, alinhar com `subagent-stop.sh` e forçar `exit 0`.
- **Impacto positivo:** o contrato de exit dos 5 dispatchers passa a ser inequívoco em todos; remove a única frase autocontraditória dos cabeçalhos de hook.
- **Impacto negativo / risco:** nenhum funcional hoje (o único sub-script sai 0) — justificativa: a propagação é inalcançável na árvore atual. Se a política escolhida for `exit 0`, um futuro guard de `SubagentStart` perde a via de recusa, e isso precisa ficar explícito no cabeçalho.
- **Esforço:** Baixo

## LOW

### `down.md` manda não reescrever as regras do skill e reescreve duas delas

- **Fingerprint:** `flow-down-md-restates-two-local-environment-stop-rules-it-forbids-restating`
- **Alvo:** `commands/down.md`
- **Evidência:** `commands/down.md:13` — "Load `skills/devops/local-environment/SKILL.md`. Every step below points into it; **do not restate its rules**." Depois, `:19` — "Nothing running for this checkout → say so and end", que é `local-environment/SKILL.md` § Stop step 3 ("Nothing running → say so and stop"); e `:23` — "A request to also remove volumes, images or data is a separate, explicit confirmation (§ Stop, step 5) — never folded into this one", que é o conteúdo do step 5 ("Only when the user asks for it explicitly, and then confirmed again as its own question").
- **Problema:** duas das três etapas do comando novo reescrevem exatamente o texto que a linha 13 proíbe reescrever, ao lado do ponteiro correto.
- **Por que importa:** custo de manutenção — uma mudança em § Stop steps 3 ou 5 passa a exigir editar também `down.md`, que é a única cópia e não tem gate que a detecte.
- **Proposta:** reduzir `:19` e `:23` aos ponteiros ("Follow § Stop, steps 1–3", "§ Stop, step 5 é confirmação própria"), sem o texto da regra.
- **Impacto positivo:** elimina a terceira cópia das duas regras; `down.md` passa a ter uma única autoridade.
- **Impacto negativo / risco:** o comando fica menos autoexplicativo quando lido sem o skill carregado — e `:8`/`:10-11` passam a depender de o leitor entender que a confirmação do Step 2 é o guardrail.
- **Esforço:** Baixo

## Descartados por duplicação

1. **`scripts/lib/auth-config.json:6` `gate_mode: warn` sem gate de CI** → **Porta 3, 3 de 3** contra `auto-release-workflow-has-no-guard-for-auth-config-placeholders`: mesmo alvo (`.github/workflows/release.yml`), mesma causa, mesma remediação — e aquela entrada já cita `gate_mode` nominalmente. **A premissa também é falsa por evidência própria:** `tests/test_auth_gate.py:186-188` fixa as três cópias (`auth-gate.sh` `AG_DEFAULT_MODE`, `entitlement.DEFAULT_GATE_MODE`, o `gate_mode` empacotado) com a mensagem "flip auth-config.json and DEFAULT_GATE_MODE together", e `.github/scripts/ci/03-python.sh:25` roda `python3 -m unittest discover -s tests`. Existe gate de CI. *Sobrevive uma variante estritamente menor e fora deste eixo:* `app/src/shared/accountRules.ts:38` — `DEFAULT_GATE_MODE: AuthGateMode = 'warn'` — é a quarta cópia, importada por `accountOperations.ts:19` e `AccountContext.tsx:3`, e `git grep -ln DEFAULT_GATE_MODE app/test/` é vazio. Alvo em `app/`, fora do escopo.
2. **Ancorar `pip`/`react`/`express`/`nest`/`rspec` com `\b` no regex semente** → **Porta 1/4**: já registrado literalmente em `docs/reports/_index.md:622`, na seção de descartes de 2026-10-02 ("Ancorar os termos curtos com `\b` cortaria os falsos positivos"). Só a metade dos **falsos negativos** volta, como sub-escopo estritamente contido (o achado `gov-seed-scan-regex-blind-…` acima).
3. **`stop/03g-index-lint.sh:17-23` resolve o docs root (fork de `python3 -I docs_root.py`) acima do gate de caminho de `:31`, enquanto o irmão `03f-spec-lint.sh:32-38` faz o teste barato em `docs/` primeiro** → **Porta 3, 2 de 3** contra `token-telemetry-consent-guard-reforks-python3-above-the-fast-path`: alvo diferente, mesma causa (fork de python acima do fast-path que existe para evitá-lo) e mesma remediação.
4. **`stop/03e-adr-gap-check.sh:48` e `stop/03h-adr-scope-check.sh:35` forkam ambos `bash new-adr.sh --dir` no mesmo Stop, e o dispatcher que já içou `DEVTEAM_TOUCHED_PATHS` não iça o ADR dir** → **Porta 3** contra a lista nominal de hipóteses já refutadas em `_index.md:621` ("`stop/03c-03d-03e re-forkam git`"). Alvo, causa (trabalho duplicado por sub-script) e remediação (içar no dispatcher) coincidem.
5. **`commands/sprint.md:22` codifica `docs/backlog/sprints/` enquanto `:8` resolve o índice por `doc-path.sh backlog-index`** → **Porta 3, 2 de 3** contra `flow-path-rewrites-move-docs-development-but-shipped-scripts-hardcode-it` (HIGH, ✅): alvo diferente, mesma causa (caminho de docs codificado onde existe resolvedor) e mesma remediação.
6. **Cross-eixo — `04-branch-overlap.sh` forka `python3` uma vez por caminho, contra o "python is forked once" do seu próprio cabeçalho (`:10-12`)** → **Porta 3, 3 de 3** contra o achado do Eixo E `token-branch-overlap-hook-forks-python-and-reparses-cache-per-path`, que quantifica o mesmo defeito (25 ms por fork medidos, 5→1 num patch de 5 arquivos) e carrega a mesma remediação. A contradição do cabeçalho foi incorporada ao achado do Eixo E.

**Nota para o próximo pass:** `commands/` tem **42** arquivos no `HEAD`, não 35 nem 40 — vários
textos do banco usam contagens antigas.
