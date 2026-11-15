# Fase 1 e 1b — Verificação Guardiã — 2026-11-14

**Data:** 2026-11-14 · **Baseline:** `HEAD` = `c6398e5` · **Baseline anterior:** `5133c8c`

Working tree **limpa** em `c6398e5` na Fase 0 (`git status --porcelain` vazio), ao contrário dos
dois passes anteriores — toda a evidência deste pass vem do disco, não de `git show HEAD:<path>`.

## Conjuntos (Fase 0)

| Conjunto | Qtd | Critério |
|---|---|---|
| Entradas nos dois bancos | **313** | `_index.md` (174) + `_index-archive-2026-Q3.md` (139) |
| **Verificável** (Fase 1) | **151** | ✅ Executed ou ⚠️ Partial — inclui as 30 linhas que já carregavam anotação 🟡/🔴 |
| **Aberto** (Fase 1b) | **140** | 133 sem marcador algum + 7 marcadas apenas 🔴 (reabertas, logo abertas de fato) |
| **Exclusão** | **22** | 🟢 Resolved, ⚰️ Obsoleto ou ↩️ Reverted sem ✅ |

**Amostragem da Fase 1** (conjunto > 60 → regra de amostragem): todos os **43** HIGH e MEDIUM-HIGH
mais **30% dos 108 restantes** (32 itens, `seed=20261114`) → **75 de 151 (49,7%)**.
**Fase 1b:** revalidação **integral**, 140 de 140.

**Distribuição das datas de marca no conjunto verificável:** 118 em 2026-07-31, 30 em 2026-10-02,
1 em 2026-09-30, 2 sem data. **Nenhuma marca nova desde o pass anterior** — os 16 commits do delta
não carregam pass de execução.

## Placar da Fase 1 — 75 de 151 (49,7%)

| Marca verificada | Qtd | % |
|---|---|---|
| ✅ **Feito** | 57 | **76,0%** |
| 🟡 **Parcialmente feito** | 13 | 17,3% |
| 🔴 **Não feito** | 5 | **6,7%** |

**Reaberturas novas: 0** — **quarto pass consecutivo em zero** (2026-10-17, 2026-10-24, 2026-11-07).
As 5 🔴 e 11 das 13 🟡 já carregavam anotação no banco. Os 6,7% de 🔴 ficam muito abaixo do limiar
de escalonamento de 15%: a integridade do banco **não** está comprometida.

**As 2 divergências novas são ambas 🟡** e ambas da mesma classe que o pass anterior nomeou — a
correção entregou o defeito nomeado e deixou um sub-escopo que o relatório-fonte descrevia:

| Fingerprint | Sub-escopo que ficou |
|---|---|
| `ref-02c-guard-make-composer-shapes-have-no-row-in-scoped-test-runner-table` | `TESTPATH=`/`FILTER=` entraram na skill, mas a tabela *Runner Filters* segue sem linha para npm/composer/make, e `make test-unit` / `npm run test:unit` saem exit 2 no HEAD |
| `ref-docs-agents-md-model-column-wrong-…-setup-assistant-listed-sonnet-actually-opus` | As duas células nomeadas foram corrigidas (coluna virou `Tier`), mas o sub-escopo "**and unvalidated**" nunca fechou — e a tabela voltou a divergir: `backend-test-specialist` listado `repetitive` nos dois idiomas contra `tier: backend-exec` no frontmatter |

### Nota de método — aplicada em 53 dos 75 itens

O campo `alvo:` nomeia o arquivo que **descreve** o problema, não necessariamente o **corrigido**
(nota originada em 2026-10-17, reconfirmada em 2026-11-07). Neste pass **53 dos 75** dependeram
dela: 49 itens trazem `alvo: None` (todo o bloco de 2026-07-31) e 4 trazem `alvo:` preenchido cuja
correção vive em outro arquivo (`ref-02c-guard-make-composer-shapes`,
`flow-architect-claude-only-async-tool-names`, `flow-learn-nudge-ancestor-test-inverted`,
`docs-sync-preferences-mirror-registry`). **Nenhum 🔴 falso** foi produzido por aplicar `alvo:`
cegamente.

### Reversões silenciosas — 3

1. **`scripts/install.sh:24`** — `d454f63` (2026-10-02), **posterior a `88834b6` no mesmo dia**,
   reintroduziu `"$(dirname "${BASH_SOURCE[0]}")"` sem guarda *acima* do código que `88834b6`
   acabara de endurecer. O install pipeado morre na linha 24 com
   `BASH_SOURCE[0]: unbound variable`. O teste de regressão
   (`test_piped_install_ignores_cwd_lib_state`) não pega: só assere a ausência do marcador `PWNED`,
   que um abort satisfaz.
2. **`agents/backend-test-specialist.md`** — `1f1c837` (2026-07-31) trocou `tier: repetitive` →
   `backend-exec` depois de `bbb311a` ter escrito `repetitive` em `docs/agents.md` / `.pt-BR.md`
   no mesmo dia. Aberto há ~3,5 meses, sem gate.
3. **`token-pre-tool-use-01-check-updates-…`** — `7dbc646` e `ba39c86` (2026-08-03/06) desfizeram o
   caminho do sidecar `.update-check-interval` e `3c46d04` moveu a checagem para `SessionStart`;
   a remoção do cache está documentada como deliberada em
   `scripts/hooks/lib/update-check.sh:51-60`. Marca correta é 🟢, não 🔴 — já registrada assim
   pelo pass anterior.

Além disso, `CLAUDE.md` passou de **600 → 602 linhas** desde 2026-11-07, recruzando o
`CLAUDE_MD_WARN=600` de `helpers/size-limits.sh`.

## Mortalidade da Fase 1b — 0,71% (1 de 140), cobertura 140 de 140 (100%)

| Estado | Qtd | % |
|---|---|---|
| Ainda reproduz | 139 | 99,3% |
| 🟢 **Resolved** | 1 | 0,71% |
| ⚰️ **Obsoleto** | 0 | 0% |

O único 🟢: `agent-orchestrator-route-has-no-path-to-architecture-work`, resolvido por **`827b1a9`**
("fix(sprint): let software-architect own a sprint task", 2026-11-09, dentro do delta), que
adicionou `software-architect` ao § Agent Roster de `skills/architecture/orchestration/SKILL.md:131`
— o catch-all de `agents/orchestrator.md:51` ("agents from the Agent Roster only") deixou de ser
inexecutável para arquitetura. O achado-pai
(`flow-orchestrator-route-table-covers-10-of-42-commands-no-gate`) segue aberto.

**E a mortalidade baixa não é imobilidade: 36 dos 140 alvos abertos (26%) foram tocados pelo delta
de 86 arquivos, e os 36 seguem reproduzindo.** Dos 16 commits do delta, apenas um (`827b1a9`)
fechou um achado aberto — e o fez por um arquivo que não é o `alvo:` registrado. Dos quatro alvos
tocados que carregam medida numérica (`checks-list.md`, `fix-patterns.md`, `project-context`,
`orchestration`), **os quatro cresceram**.

Nove itens tiveram **sub-evidência** resolvida mas seguem abertos por outra perna (não qualificam
como 🟢): `ref-three-pointers-to-claude-md-hook-subscript-convention…` (3→1 ponteiro, mas
`scripts/hooks/stop.sh:58` segue apontando para seção inexistente),
`agent-database-specialist-rls-as-engine-neutral…`,
`skill-orchestration-spawn-integrity-unreachable-from-devteam-commands` (0→4 comandos carregam;
22 dos 26 que dão spawn seguem sem alcance), `flow-learn-nudge-has-no-canonical-skill-home…`,
`flow-pr-md-default-branch-falls-back-to-global-config…`,
`flow-review-command-writes-and-commits-while-documented-as-read-only`,
`flow-rule-and-sync-rules-listed-as-technical-writer-but-never-delegate`,
`auto-no-gate-validates-claude-md-file-structure-tree-against-real-tree…` e
`flow-prompt-auditoria-commit-step-contradicts-branch-rule`.

### 46 fingerprints abertos mediram pior — recorde do banco

Quase o dobro do recorde anterior (24 em 2026-11-07). Os piores:

| Fingerprint (alvo) | registrado → atual |
|---|---|
| `token-changelog-already-growing…` (`CHANGELOG.md`) | 441 → **2.470** linhas |
| `token-install-sh-503-lines…` (`scripts/install.sh`) | 947 → **1.405** linhas |
| `token-wiki-retrieval-index-13-7kb…` (`docs/wiki/README.md`) | 13.715 B / 51 ln → **27.768 B / 107 ln** |
| `token-interaction-patterns-209-lines…` | 209 → **404** linhas; 26 → **44** carregadores |
| `token-readme-228-each-after-extraction…` | 228 → **501** linhas cada |
| `flow-session-start-118-lines-monolithic…` | 310 → **460** linhas |
| `token-151-skills-flat-symlinked…` | 12.751 B / 155 skills → **19.298 B / 168** |
| `token-fix-patterns-517-lines…` | 517 ln / 22,6 KB → **665 ln / 32,4 KB**; padrões 25→30 |
| `token-checks-list-loads-all-three-provider-blocks…` | 668 → **889** linhas |
| `token-archive-index-rotates-index-sections-only-report-directories-never-pruned` | 1,0 MB → **1,84 MB**; 16 dirs, 0 podados |
| `gov-committed-install-copy-stale-vs-source-no-gate` | 58 de 666 divergem / 16 órfãos / 5 dias → **66 de 735 / 19 / 10 dias** |
| `token-plan-mode-execution-strategy-gate-duplicates…` | 14.853 → **17.111 B**; 26 → **32** carregadores |
| `auto-check-fingerprint-uniqueness-grep-admits-discarded-candidate-lines…` | 237/235 (2 prosa) → **318/313 (5 prosa)** |
| `ref-command-description-duplicated-frontmatter-vs-commands-json` | 35 → **42** descrições divergentes |
| `auto-agent-lint-quiz-first-never-scans-commands-dir` | 35 → **42** comandos sem cobertura |
| `agent-review-agent-roster-hardcoded-in-five-places…` | 5 → **7** casas |
| `token-spec-gate-17kb-loaded-whole…` | 17.463 B / 248 ln → **19.338 B / 264 ln** |
| `gov-seed-scan-regex-blind-to-flutter-swift…` | 36 → **42** linhas invisíveis |

**Cinco mediram melhor:** `token-install-sh-second-unconditional-claude-md-injection…`
(35 ln/1,97 KB → 29 ln/1,81 KB) · `agent-jira-detection-branch-naming-block-duplicated…`
(13 → 11 corpos) · `token-graphify-hint-3-git-forks…` (3 → 2 forks) ·
`agent-three-at-exactly-211-line-ceiling…` (3 de 18 → **1 de 19**) ·
`ref-three-pointers-to-claude-md-hook-subscript-convention…` (3 → 1).

**Re-ancoragem notável:** `docs-sync-claude-md-102-states-skill-desc-strict-false…` **voltou à forma
original**. A nota de 2026-10-10 registrava que `SKILL_DESC_STRICT` havia sido removida; ela foi
reintroduzida (`7736e20d`) como `SKILL_DESC_STRICT=true` em `helpers/agent-lint.sh:98`, enquanto
`CLAUDE.md:160` ainda documenta `false` como o valor corrente.

---

## Fase 1 — item a item

### Itens HIGH e MEDIUM-HIGH (43 de 43)

Pass de auditoria guardiã · DATA 2026-11-14 · HEAD `c6398e5` · baseline anterior `5133c8c`

Janela de referência dos itens 1–25: **2026-10-02** (merge `ce02b1e` "audit/report-findings",
commits `c19f060` · `a2cf59c` · `d958922` · `ddeaee6` · `88834b6` · `2cdec4d`, mais `68cd420`
que gravou as marcas no banco). Item 9: janela **2026-09-30**. Itens 26–43: janela **2026-07-31**.

---

#### `auto-full-suite-guard-sed-absorbs-sibling-json-keys`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `ddeaee6` — "fix(hooks): let exit 2 win over SIGPIPE, scope the full-suite guard, retire stale worktree sessions"
- **Evidência no HEAD:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:32` — "COMMAND=$(printf '%s' \"$INPUT\" | sed -n -E 's/.*\"command\"[[:space:]]*:[[:space:]]*\"(([^\"\\\\]|\\\\.)*)\".*/\\1/p' | head -1)" — a captura passou de `\(.*\)` guloso para uma classe que exclui `\"` não escapado; comentário em `:28-31` documenta exatamente o motivo
- **Reprodução no HEAD:** os dois payloads de comando idêntico (`description` antes e depois de `command`, contendo `--filter FooTest` e `src/a.test.ts`) dão agora **exit 2** idêntico; `npm test -- src/a.test.ts` segue silencioso (exit 0)
- **Reversão posterior:** nenhuma (o arquivo não está em `/tmp/delta_files.txt`; `git log --since=2026-10-02 -- <alvo>` só mostra `ddeaee6`)
- **Marca verificada:** ✅ Feito

#### `flow-learn-run-marker-records-commit-time-not-run-time`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `a2cf59c` — "fix(commands): fire the learn nudge on a moved branch tip, reach worktree finalization in merge"
- **Evidência no HEAD:** `commands/learn.md:174` — "4. Record the run marker (any outcome, also on `--no-commit`; never under `--embedded`, whose caller records it) **after** the commits, so it holds the post-commit HEAD: `echo \"$(date +%s) $(git rev-parse HEAD 2>/dev/null)\" > .dev-team-agents/.learn-last-run`"
- **Evidência complementar:** `commands/commit.md:179` — "Skip — nothing new to capture — only when `<head-sha>` equals the current `git rev-parse HEAD` … **and** `<unix-timestamp>` is not older than the mtime … A missing marker never skips." A condição de skip passou a ser alcançável; o marcador saiu do Step 4 e foi para o Step 5 item 4, depois do auto-commit
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `auto-install-heredoc-omits-auto-learn-before-commit`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `88834b6` — "fix(scripts): stop install.sh sourcing from the piped CWD, escape ADR titles, sync preferences mirrors"
- **Evidência no HEAD:** `scripts/install.sh:1327` — "  \"auto_learn_before_commit\": true," dentro do heredoc de fallback (`# Fallback: write a plain JSON file without python3.`, `:1302`)
- **Gate (o sub-escopo "sem gate" do achado):** `tests/test_audit_report_fixes.py` → `PreferencesMirrorTest.test_install_sh_fallback_heredoc` compara todas as chaves de `scripts/lib/preferences-defaults.json` contra o trecho do heredoc. Executado no HEAD: 4/4 OK. `helpers/preferences-sync-lint.sh` cobre os 2 mirrors de documentação: clean ✓
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `ref-tool-map-tool-rewrites-loaded-but-never-emitted-by-render-provider`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `d958922` — "fix(render): emit tool rewrites for opencode and codex, drop the docs/development path rewrite"
- **Evidência no HEAD:** `scripts/lib/render_provider.py:113` — "def apply_tool_rewrites(body, provider, tool_map):" com emissão real em `:130` (`re.sub(rf\"`?\b{name}\b`?\", f\"`{new}`\", chunk)`), chamada em `:881`, `:911`, `:938`, `:976` (agentes e comandos, opencode e codex)
- **Gate:** `tests/test_render_tool_map.py::test_no_claude_only_tool_name_survives` varre todos os agentes e comandos renderizados nos dois provedores contra `AskUserQuestion, ScheduleWakeup, TaskList, TaskGet, TaskOutput, SendMessage, TodoWrite, WebFetch`. Executado no HEAD: 4/4 OK
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `ref-02c-guard-make-composer-shapes-have-no-row-in-scoped-test-runner-table`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `ddeaee6` (que acrescentou 2 linhas a `skills/shared/scoped-test-execution/SKILL.md`)
- **Evidência no HEAD:** `skills/shared/scoped-test-execution/SKILL.md:61` — "Wrappers (`npm test`, `composer test`, `make test`) are scoped by passing a path, `--filter`, `--`, or `TESTPATH=`/`FILTER=` through. The full-suite guard (`02c-full-suite-guard.sh`) judges only the command actually invoked, so read-only commands that merely name a runner are never blocked."
- **Reversão posterior:** nenhuma
- **Marca verificada:** 🟡 Parcialmente feito
- **Divergência:** 2 dos 3 sub-escopos fechados (`TESTPATH=`/`FILTER=` agora existem na skill; os wrappers ganharam menção). Faltam:
  (a) a **tabela** *Runner Filters* (`:44-57`) segue sem linha para `npm`/`composer`/`make` — os 3 `case` novos só aparecem em prosa solta em `:61`, não na tabela que o achado nomeia;
  (b) a contradição com `:59` ("When the project defines its own scoped script in `CLAUDE.md`, `package.json`, or a `Makefile`, that command wins over the table") **persiste e foi reproduzida no HEAD**: `make test-unit` → exit 2 (BLOCKED) e `npm run test:unit` → exit 2, enquanto `make test TESTPATH=tests/Unit` → exit 0. Ou seja, o script scoped próprio do projeto, declarado legítimo em `:59`, continua sendo bloqueado pelo guard quando não carrega um qualificador reconhecido por `has_scope` (`:53-68`).

#### `flow-02c-composer-fallback-case-ignores-every-scope-qualifier`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `ddeaee6`
- **Evidência no HEAD:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:163-168` — "composer)\n            sub=${1:-}\n            case \"$sub\" in test|test:*) ;; *) return 1 ;; esac\n            shift\n            has_scope \"$@\" || return 0\n            return 1 ;;" — o `case` ganhou a exclusão por escopo
- **Reprodução no HEAD:** `composer test tests/Unit/FooTest.php` → exit 0; `composer test-unit --filter FooTest` → exit 0; `composer test` (sem escopo) → exit 2. Os dois falsos positivos do achado desapareceram
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `flow-architect-claude-only-async-tool-names-rendered-verbatim`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-10-02
- **Commits examinados:** `d958922` (tool-map + emissor) e `c19f060` (hedge na linha do agente)
- **Evidência no HEAD:** `scripts/lib/tool-map.json` → `providers.opencode.tool_unavailable` traz `ScheduleWakeup`, `TaskList`, `TaskGet`, `TaskOutput`, `SendMessage` (idem `providers.codex`); `agents/software-architect.md:89` ganhou o hedge "(Spawn Integrity check 5, Auto-reactivation — the work-feedback loop owns rescheduling when its gate is active, check 6)"
- **Gate:** `tests/test_render_tool_map.py::test_no_claude_only_tool_name_survives` prova que nenhum dos três nomes chega literal ao `.opencode/agents/software-architect.md` renderizado. OK no HEAD
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `token-02c-full-suite-guard-substring-match-injects-nudge-on-non-test-commands`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `ddeaee6`
- **Evidência no HEAD:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:74-77` — "# classify <words…>: the command starts at $1 … A runner name only\n# counts when it is the command being invoked, never an argument to `cat`,\n# `grep`, `git log --grep=` and the like." Os `*jest*`/`*pytest*`/`*rspec*` soltos deram lugar a `classify()` sobre a primeira palavra de cada segmento (`is_full_suite`, `:186-202`)
- **Reprodução no HEAD:** 6 de 6 payloads de leitura (`cat jest.config.js`, `grep -rn pytest .`, `git log --grep=rspec`, `rg jest scripts/`, `ls node_modules/.bin/jest`, `echo pytest`) saem **exit 0 com 0 byte** de `additionalContext`
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `ref-check-updates-shim-and-update-sh-exec-renamed-away-01-check-updates-hook`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-09-30
- **Commit examinado:** `a0df626` — "fix(scripts): make check-updates.sh a real on-demand update check" (janela 2026-09-30; a mensagem do commit descreve o achado literalmente)
- **Evidência no HEAD:** `scripts/check-updates.sh:2-12` — "check-updates.sh — on-demand update check for a v2 install (/devteam:update Step 3, `update.sh --check`) … Prints exactly one line on stdout, and always exits 0: Update available: <current> → <latest> … Could not check for updates: <reason>"; o `exec` para `hooks/pre-tool-use/01-check-updates.sh` desapareceu. `scripts/update.sh:29` — "exec bash \"$SCRIPTS_DIR/check-updates.sh\"". `commands/update.md:99` — "**If the output starts with `Could not check for updates:`** → print that line as is, then stop. Never report \"Up to date\" in this case."
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito
- **Observação (fora do escopo do achado):** `scripts/hooks/lib/update-check.sh:2,6` ainda comenta "Sourced by pre-tool-use/01-check-updates.sh only", nome que hoje é `_disabled-01-check-updates.sh` e que `check-updates.sh:35` também sourceia — comentário obsoleto, sem efeito funcional.

#### `flow-pre-tool-use-dispatcher-sigpipe-141-masks-02c-block`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `ddeaee6`
- **Evidência no HEAD:** `scripts/hooks/pre-tool-use.sh:19-24` — "# The payload is fed to each sub-script from a file, never through a pipe: a\n# sub-script that exits without reading stdin would otherwise kill the writer\n# with SIGPIPE (141) … INPUT_FILE=$(mktemp …)"; `:42` — "env -u BASH_ENV -u ENV bash \"$script\" < \"$INPUT_FILE\" || SCRIPT_EXIT=$?"; `:46` — a regra passou a preservar o `exit 2` ("exit 2 (a refusal) is never masked by an earlier exit 1")
- **Reprodução no HEAD:** payload de **200 080 bytes** com `command: "npm test"` → dispatcher sai **2** e entrega a mensagem bloqueante do `02c` (antes: 141)
- **Reversão posterior:** nenhuma; `64ecf2a` (mesmo dia, "keep exit 2 across dispatchers") reforçou a mesma regra nos outros dispatchers
- **Marca verificada:** ✅ Feito

#### `flow-merge-md-branch-and-tree-resolved-before-worktree-detection`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `a2cf59c`
- **Evidência no HEAD:** `commands/merge.md:17-24` — "## Step 1 — Resolve the worktree session, then the branches … The session file is untracked and lives in the **main checkout**, so a linked worktree cannot see it by a relative path. Resolve it through the main checkout root first: `ROOT=$(cd \"$(git rev-parse --git-common-dir)/..\" && pwd)` / `cat \"$ROOT/.dev-team-agents/.worktree-session\"`"; `:30` — "If the session says `worktree=yes` and you are in the main checkout, it is the branch checked out in the linked worktree"; o antigo Step 2 virou "## Step 2 — Choose the finalization strategy" (`:38`) e consome a sessão já lida
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `flow-learn-nudge-ancestor-test-inverted-in-four-commands`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `a2cf59c`
- **Evidência no HEAD:** `commands/merge.md:72` — "This is the canonical learn-nudge check — other commands reference it rather than restating it"; `:78` — "If the marker is missing, or its `<head-sha>` differs from the working branch tip (commits landed since the last learn run)". A redação invertida ("is **not an ancestor** of the current HEAD") desapareceu; `commands/pr.md:112`, `commands/refactor.md:162`, `commands/audit.md:180` e `commands/sprint.md:92` agora **referenciam** o check canônico em vez de replicá-lo
- **Reversão posterior:** nenhuma. `rg 'ancestor' commands/` devolve só `sprint.md:57` (reuso de worktree de sprint, tema distinto)
- **Marca verificada:** ✅ Feito

#### `flow-02c-escape-hatch-anchored-while-detection-is-substring`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-10-02 · 🟡 já anotada em 2026-11-07
- **Commit examinado:** `ddeaee6`
- **Evidência no HEAD:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:47` — "CONFIRM_RE='(^|[[:space:];&|(])DEVTEAM_FULL_SUITE_CONFIRMED=1([[:space:]]|$)'"
- **Reprodução no HEAD:** `cd frontend && DEVTEAM_FULL_SUITE_CONFIRMED=1 npm test` → exit 0 (posição 0 deixou de ser exigida ✓). Mas `sh -c "DEVTEAM_FULL_SUITE_CONFIRMED=1 npm test"` → **exit 2 (BLOCKED)**, porque o caractere anterior é `"`, que não está na classe de `CONFIRM_RE`, enquanto `is_full_suite` (`:188`) remove as aspas com `tr -d "\"'\`"` e classifica o segmento como full suite. Também `sh -c 'pnpm test:run'` → exit 2, forma que o próprio comentário de `:185-186` cita como caso suportado
- **Reversão posterior:** nenhuma
- **Marca verificada:** 🟡 Parcialmente feito
- **Divergência:** confirmação da anotação de 2026-11-07, sem mudança desde então. Falta admitir `"` e `'` entre os prefixos aceitos por `CONFIRM_RE` (ou testar a escotilha depois do `tr -d` das aspas) — o wrapper `sh -c "…"`/`bash -c "…"` segue sem escotilha viável.

#### `skill-orchestration-two-sections-both-numbered-check-5-breaks-cross-refs`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `c19f060` — "fix(agents): delegate worktree isolation to the shipped skill, load spec-gate in developer agents"
- **Evidência no HEAD:** `rg '^### [0-9]' skills/architecture/orchestration/SKILL.md` devolve seis números únicos — `:162` "### 1. Preflight…", `:177` "### 2. Name validation…", `:185` "### 3. Evidence…", `:202` "### 4. Liveness…", `:225` "### 5. Auto-reactivation — schedule the checkback, don't wait to be asked", `:261` "### 6. Periodic status table". O cabeçalho da seção em `:155` passou de "Three checks" para "**Six checks**, in order"
- **Refs cruzadas, todas resolvendo certo:** `skills/architecture/orchestration/SKILL.md:267` → "see check 5, *One owner per round*"; `agents/software-architect.md:89` → "(Spawn Integrity check 5, Auto-reactivation — the work-feedback loop owns rescheduling when its gate is active, check 6)"; `CLAUDE.md:209` → "§ Spawn Integrity, check 6" (o caminho de carga de `work-feedback`, que o achado apontava para a seção errada)
- **Reversão posterior:** nenhuma. `skills/architecture/orchestration/SKILL.md` está em `/tmp/delta_files.txt`, mas a numeração 1–6 sobreviveu intacta
- **Marca verificada:** ✅ Feito

#### `skill-work-feedback-wakeup-cadence-cap-output-conflict-auto-reactivation`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `c19f060`
- **Evidência no HEAD:** `skills/shared/work-feedback/SKILL.md:58` — "While the gate above is active, this loop is the **only** `ScheduleWakeup` loop for the round — the orchestration skill's check 5 does not schedule its own wakeup alongside it."; lado espelhado em `skills/architecture/orchestration/SKILL.md:235-237` — "**One owner per round.** When check 6's work-feedback gate is active, its loop owns all rescheduling: schedule no separate wakeup here, and run the steps below on its ticks instead."
- **Teto:** `skills/shared/work-feedback/SKILL.md:56` — "6. **Cap it.** On each tick, apply … § Spawn Integrity check 5 … After its two reactivation attempts for a sub-agent, emit the current table, stop scheduling, and surface that sub-agent to the user as a blocker — do not keep polling." — fecha também o conflito "only the table" × blocker, declarando o blocker como o caminho de saída do laço
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `token-two-schedulewakeup-poll-loops-same-spawn-round-300s-vs-1200-1800s`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `c19f060`
- **Evidência no HEAD:** as duas seções deixaram de colidir (`### 5.` e `### 6.` em `skills/architecture/orchestration/SKILL.md:225,261`) e a regra de dono único (`work-feedback/SKILL.md:58` + `orchestration/SKILL.md:235`) elimina o agendamento duplo por rodada; o laço de 300 s, antes o único sem teto, ganhou o teto de duas tentativas em `work-feedback/SKILL.md:56`
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito
- **Observação:** o intervalo default de 5 min (`work-feedback/SKILL.md:30` — "treat it as `active: true`, `interval_minutes: 5`") permanece, portanto ≈12 ticks/hora quando o gate está ligado. Não conta como sub-escopo faltante: é um valor controlado pelo usuário (`work_feedback_interval_minutes`), e o defeito do achado — duas rodadas de wakeup simultâneas e laço sem teto — está fechado.

#### `flow-question-tool-name-in-four-implementation-command-findings-gates`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `d958922`
- **Evidência no HEAD:** `commands/backend.md:66` — "**If findings exist**, use `AskUserQuestion` to ask the user what to do." Idêntico em `commands/frontend.md:57`, `commands/fullstack.md:65` e `commands/mobile.md:57`, coerente com `:6` de cada arquivo. As únicas ocorrências restantes de `question` nesses quatro arquivos são o campo `"question":` do payload JSON do quiz (`backend.md:71` etc.), não um nome de ferramenta
- **Gate:** `tests/test_render_tool_map.py::test_opencode_commands_use_canonical_question_tool`. OK no HEAD
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `agent-worktree-cascade-delegates-to-unshipped-claude-md`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `c19f060`
- **Evidência no HEAD:** os nove agentes que editam arquivos trazem a mesma linha, apontando para a skill que **é** empacotada: `agents/backend-developer.md:66`, `backend-test-specialist.md:38`, `database-specialist.md:41`, `devops-specialist.md:40`, `frontend-developer.md:38`, `frontend-test-specialist.md:38`, `mobile-developer.md:40`, `seo-specialist.md:36`, `ui-ux-designer.md:39` — "Before editing any file, resolve the worktree decision with the cascade in `skills/shared/worktree/SKILL.md` § Decision Cascade (spawn-prompt `WORKTREE_PATH`/`BRANCH` → session file → `worktree_active` preference → ask once). … otherwise work on the recorded branch."
- **Âncora existe:** `skills/shared/worktree/SKILL.md:12` — "## Decision Cascade (load first)". E `skills` está em `KEEP_ROOT` (`scripts/install.sh:400` — "KEEP_ROOT=(agents scripts skills templates commands plugins)"), logo a skill chega ao projeto instalado, ao contrário de `CLAUDE.md`
- **Proibição removida:** o antigo "otherwise work on the recorded branch **and do not load the skill**" de `mobile-developer.md`/`devops-specialist.md` saiu; `CLAUDE.md:119` passou a declarar a skill como casa canônica e o bloco do `CLAUDE.md` como resumo para contribuidores
- **Reversão posterior:** nenhuma (`agents/devops-specialist.md` está em `/tmp/delta_files.txt`, mas a linha `:40` sobreviveu)
- **Marca verificada:** ✅ Feito

#### `skill-spec-gate-scope-lock-hard-gate-unreachable-by-execution-agents`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `c19f060`
- **Evidência no HEAD:** `rg -l spec-gate agents/*.md` devolve nove agentes — `backend-developer`, `backend-test-specialist`, `database-specialist`, `frontend-developer`, `frontend-test-specialist`, `mobile-developer`, `product-analyst`, `qa-specialist`, `software-architect`. Os quatro coding agents que `skills/shared/spec-gate/SKILL.md:110-111` nomeia estão todos lá. Linha inserida, p.ex. `agents/backend-developer.md:27` — "When the task links a spec (`docs/specs/<feature>.md` exists for it), load `skills/shared/spec-gate/SKILL.md` and apply its Scope Lock — the spec's `Given/When/Then` blocks bound the implementation"
- **`<HARD-GATE>` alcançável:** `skills/shared/spec-gate/SKILL.md:127-134` agora é carregado pelo próprio agente de execução, sem depender de um `Load` atravessar a fronteira do Task tool
- **Reversão posterior:** nenhuma (`skills/shared/spec-gate/SKILL.md` está em `/tmp/delta_files.txt`; o bloco `Scope Lock` e o `<HARD-GATE>` seguem presentes)
- **Marca verificada:** ✅ Feito

#### `docs-sync-reports-index-preamble-declares-archive-index-trigger-less-while-stop-99b-dispatches-it`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-09-11 · 🔴 já reaberta em 2026-10-10
- **Commit examinado:** nenhum. `git log --since=2026-09-11 --until=2026-09-12 -- docs/reports/_index.md` é vazio; os commits mais próximos são `3acaa89` (2026-09-12) e `6b3846f` (2026-09-18), ambos "add guardian audit pass(es)", que só acrescentam seções de fingerprints
- **Evidência no HEAD:** `docs/reports/_index.md:24-27` — "> **Rotation:** entries older than 90 days are meant to move to `_index-archive-YYYY-Q.md` via `helpers/archive-index.sh`. **That script currently has no trigger** — no hook, no CI job, no installer call — so rotation has never run."
- **Contraprova no HEAD:** `scripts/hooks/stop/99b-archive-index.sh:21` — "SCRIPT=\"$REPO_ROOT/helpers/archive-index.sh\"" e `:47` — "OUTPUT=\"$(bash \"$SCRIPT\" 2>&1)\" || OUTPUT=\"\"", com gate de stamp diário (`:36-41`); o nome casa o `SUBSCRIPT_RE` do dispatcher Stop
- **Reversão posterior:** `docs/reports/_index.md` **está** em `/tmp/delta_files.txt` (tocado desde o baseline anterior pelo pass de 2026-11-07), mas o bloco 24-27 não foi corrigido nessa passagem
- **Marca verificada:** 🔴 Não feito
- **Divergência:** terceira constatação da mesma marca falsa. O bloco está nas linhas 1-120 que a Fase 0 lê antes de qualquer outra coisa, então segue envenenando todo pass futuro. Correção mínima: trocar as 4 linhas por "rotation runs from `scripts/hooks/stop/99b-archive-index.sh`, gated by a once-per-day stamp" e remover a referência ao fingerprint `flow-helpers-archive-index-sh-orphan-…` como pendente.

#### `ref-comments-policy-routing-table-points-to-sections-dir-not-references`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `c19f060`
- **Evidência no HEAD:** `skills/shared/comments-policy/SKILL.md:107-109` — "| Python files in scope | `skills/shared/comments-policy/references/type-annotations.md` |" (idem `aaa-pattern.md` e `anti-patterns.md`). Os três arquivos existem em `references/` (verificado por `ls`)
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `docs-sync-preferences-mirror-registry-names-readmes-omits-docs-pair`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-10-02
- **Commits examinados:** `c19f060` (registro) e `88834b6` (chave faltante nos dois idiomas)
- **Evidência no HEAD:** `CLAUDE.md:308` — "| `docs/user-preferences.md` / `docs/user-preferences.pt-BR.md` — schema block, key table and effects table | Documentation |" (a linha `README.md`/`README.pt-BR.md` saiu do registro); `docs/user-preferences.md:69,104,127` e `docs/user-preferences.pt-BR.md:69,104,127` trazem `auto_learn_before_commit` no bloco de schema, na tabela de chaves e na de efeitos
- **Reversão posterior:** nenhuma, apesar de 21 commits terem tocado esses três arquivos entre 2026-10-02 e o HEAD
- **Marca verificada:** ✅ Feito

#### `auto-stop-03c-reuse-lint-gates-on-csv-registry-while-harness-writes-md`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `ddeaee6`
- **Evidência no HEAD:** `scripts/hooks/stop/03c-reuse-lint.sh:22` — "REGISTRY_REL=\"docs/development/reuse-guidelines.md\"", resolvido depois por `devteam_doc_path \"$REPO_ROOT\" reuse-guidelines` (`:26`), exatamente o mesmo par de linhas de `scripts/reuse-lint.sh:39,43`. O `.csv` desapareceu do arquivo
- **Reversão posterior:** nenhuma (endurecido depois pela resolução via `lib/docs-root.sh`)
- **Marca verificada:** ✅ Feito

#### `flow-path-rewrites-move-docs-development-but-shipped-scripts-hardcode-it`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-10-02
- **Commit examinado:** `d958922`
- **Evidência no HEAD:** `scripts/lib/tool-map.json` — `providers.opencode.path_rewrites` é `{}` e `providers.codex.path_rewrites` é `{".claude/agents/dev-team/": ".codex/agents/"}`; a entrada `"docs/development/": "docs/"` foi removida dos dois. `commands/adr.md:18,20` e `scripts/new-adr.sh` apontam agora para o mesmo `docs/development/adrs/` em todos os provedores
- **Gate:** `tests/test_render_tool_map.py::test_docs_paths_match_shipped_scripts` fixa os caminhos de `new-adr.sh`, `reuse-lint.sh`, `spec-lint.sh` e `03e-adr-gap-check.sh`. OK no HEAD
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `auto-install-sh-bash-source-fallback-resolves-to-cwd-and-sources-project-lib`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-10-02 · 🟡 já anotada em 2026-11-07
- **Commit examinado:** `88834b6` (correção) e `d454f63` (regressão, mesmo dia, posterior)
- **Evidência no HEAD:** o fallback nomeado está sanado — `scripts/install.sh:62-66` — "_INSTALL_SH_DIR=\"\"\nif [ -n \"${BASH_SOURCE[0]:-}\" ] && [ -f \"${BASH_SOURCE[0]}\" ]; then\n    _INSTALL_SH_DIR=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd)\"\nfi". Mas `scripts/install.sh:24` — "_dta_py=\"$(dirname \"${BASH_SOURCE[0]}\")/lib/python.sh\"" é anterior e não tem guarda
- **Reprodução no HEAD:** `cd /tmp/pipetest && bash < scripts/install.sh` → "bash: line 24: BASH_SOURCE[0]: unbound variable", rc=1. O instalador aborta antes de chegar ao código corrigido
- **Reversão posterior:** **sim, dentro da própria janela** — `git log -S` localiza a linha 24 em `d454f63` 2026-10-02 "fix(scripts): resolve python3 to a working Python 3.9+ on Windows Git Bash", commit posterior a `88834b6` no mesmo dia
- **Marca verificada:** 🟡 Parcialmente feito
- **Divergência:** confirmação da anotação de 2026-11-07. O sintoma mudou de "sourceia código do projeto do usuário" para "aborta o install"; o caminho `curl … | bash`, que a documentação chama de primário, segue quebrado. Correção: `${BASH_SOURCE[0]:-}` com teste `[ -f ]`, igual a `:63-66`. O mesmo padrão sem guarda existe em `scripts/hooks/pre-tool-use.sh:13` e `scripts/check-updates.sh:16`, que porém nunca são pipeados.

---

## Bloco 2026-07-31 — itens 26–43 (campo `alvo:` = `None`)

Para os 18 itens abaixo o banco não traz `alvo:`. O alvo real foi reconstruído pelo tema do achado
contra os commits da janela de **2026-07-31**, em especial `bbb311a` (docs/estruturas),
`b4e219f` (corpos de agentes stack-prescriptivos), `c7535b7` (CI/validadores/rotação),
`cc28900` (dispatchers de ciclo de vida), `2e12335` (install/telemetria), `519ca7e` (skills) e
`6919564` (comandos/scripts).

#### `ref-docs-agents-md-model-column-wrong-technical-writer-listed-haiku-actually-sonnet-and-setup-assistant-listed-sonnet-actually-opus`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-07-31
- **Alvo reconstruído:** `docs/agents.md` + `docs/agents.pt-BR.md` (o campo `alvo:` é `None`)
- **Commit examinado:** `bbb311a` — "docs: correct stale authoring standards, structure maps and command tables"
- **Evidência no HEAD:** o cabeçalho da coluna passou de `Model` para `Tier` (`docs/agents.md:17` — "| Agent | Role | Phase | Tier |") e as duas células nomeadas foram corrigidas: `:35` — "| `technical-writer` | API docs, READMEs, runbooks, changelogs | SUPPORT | `repetitive` |" e `:36` — "| `setup-assistant` | Project setup + version management | SETUP | `reasoning` |", batendo com `tier:` do frontmatter. `docs/agents.md:38` acrescentou "**Tier is the source of truth, not the model name.**"
- **Reversão posterior:** sim, no mesmo dia e nunca detectada — `1f1c837` (2026-07-31, posterior a `bbb311a`) trocou `-tier: repetitive` por `+tier: backend-exec` em `agents/backend-test-specialist.md` sem tocar a tabela
- **Marca verificada:** 🟡 Parcialmente feito
- **Divergência:** o sub-escopo "**and unvalidated**" nunca foi fechado, e a tabela voltou a divergir — reproduzido no HEAD comparando as 19 linhas da tabela contra o frontmatter de `agents/*.md`:
  `docs/agents.md:28` e `docs/agents.pt-BR.md:28` — "| `backend-test-specialist` | Backend test coverage (conditional) | DEVELOPMENT | `repetitive` |" contra `agents/backend-test-specialist.md:4` — "tier: backend-exec".
  Nenhum gate cobre essa tabela: `rg 'docs/agents' .github/scripts/ci helpers tests` devolve uma única linha, e é um **comentário** que assume a lacuna — `.github/scripts/ci/02-readme-sync.sh:16-18` — "Escapes this gate (documented honestly, not a TODO): … wrong-but-faithfully-translated facts (the `docs/agents.md` Model-column incident)". `helpers/agent-lint.sh:488` valida a tier da roster de `skills/architecture/orchestration/SKILL.md`, não a de `docs/agents.md`. A deriva está aberta há ~3,5 meses nos dois idiomas.

#### `ref-claude-md-183-code-reviewer-roles-says-delegates-to-test-specialists-but-impl-routes-to-backend-frontend-reviewer`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-07-31
- **Alvo reconstruído:** `CLAUDE.md` → bloco *Code Reviewer roles* (hoje migrado para `CLAUDE-md/commands.md`)
- **Commit examinado:** `bbb311a` — o diff substitui "delegates to `backend-test-specialist` or `frontend-test-specialist` as needed" pela descrição real do roteamento
- **Evidência no HEAD:** `CLAUDE-md/commands.md:72` — "**Code Reviewer roles:** `code-reviewer` is the entry-point router for `/devteam:review`. Before anything else it loads `skills/shared/review-router/SKILL.md`, which classifies the git diff as `BACKEND`, `FRONTEND`, or `BOTH`. It then proceeds as `backend-reviewer` (`BACKEND`), as `frontend-reviewer` (`FRONTEND`), or emits the parallel routing message and stops (`BOTH`)." Confere com `agents/code-reviewer.md:31-32`
- **Reversão posterior:** nenhuma (o bloco migrou para `CLAUDE-md/commands.md` com o texto corrigido intacto)
- **Marca verificada:** ✅ Feito

#### `ref-two-helpers-dirs-naming-collision-root-stripped-vs-scripts-helpers-shipped-claude-md-file-structure-omits-scripts-helpers`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-07-31
- **Alvo reconstruído:** `CLAUDE.md` → *File Structure* (hoje `CLAUDE-md/file-structure.md`)
- **Commit examinado:** `bbb311a` (a mensagem cita o achado: "named `helpers` and their opposite packaging fates: root helpers/ is stripped at install, scripts/helpers/ ships and runs")
- **Evidência no HEAD:** `CLAUDE-md/file-structure.md:112-119` — a tabela "**Two `helpers` directories — do not confuse them:**" com as duas linhas (`helpers/` "**No** — `rm -rf` by `scripts/lib/strip-tarball.sh`" e `scripts/helpers/` "**Yes** — inside the allowlisted `scripts/` tree") e o fecho "When a rule or script path references \"helpers\", state which of the two it means."; o `scripts/helpers/` ganhou entrada própria na árvore em `:81`; `CLAUDE.md:293` aponta para lá
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `ref-claude-md-file-structure-omits-helpers-and-privacy-and-claude-md-folder`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-07-31 · 🟡 já anotada em 2026-11-07
- **Alvo reconstruído:** `CLAUDE.md` → *File Structure* (hoje `CLAUDE-md/file-structure.md`)
- **Commit examinado:** `bbb311a`
- **Evidência no HEAD:** 6 dos 7 itens do relatório-fonte (`docs/reports/2026-07-30/01-referencias-e-consistencia.md:36`) têm entrada na árvore — `helpers/` (`:36`), `opencode/` (`:51`), `user-data/` (`:100`), `.github/` (`:93`), `PRIVACY.md` (`:106`), `CLAUDE-md/` (`:25`)
- **Reversão posterior:** nenhuma remoção; a árvore apenas voltou a defasar com a árvore real
- **Marca verificada:** 🟡 Parcialmente feito
- **Divergência:** confirmação da anotação de 2026-11-07, sem mudança desde então. `.claude/` segue sem entrada própria (as 2 ocorrências em `CLAUDE-md/file-structure.md:23,60` são menções dentro de outras linhas, não nós da árvore). E a deriva nova continua: comparando `git ls-files` com a árvore, `TERMS.md` e `infra/` são rastreados no topo e têm **zero** ocorrência no arquivo.

#### `flow-size-limits-sh-ci-only-warn-only-not-in-stop-dispatcher-asymmetric-with-agent-lint-200-cap-never-blocking`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-07-31 · 🟡 anotada em 2026-07-31, 2026-08-14, 2026-08-21, 2026-10-10 e 2026-11-07
- **Alvo reconstruído:** `helpers/size-limits.sh` + `.github/scripts/ci/01-lint.sh` + `scripts/hooks/stop/`
- **Commit examinado:** `c7535b7` ("ci: close validator and enforcement gaps…", +20 linhas em `helpers/size-limits.sh`) e `7736e20` ("…enforce both size gates", +15 em `.github/scripts/ci/01-lint.sh`)
- **Evidência no HEAD:** `.github/scripts/ci/01-lint.sh:95` — "blocking \"size-limits\" bash helpers/size-limits.sh" (promovido a bloqueante ✓)
- **Reversão posterior:** nenhuma
- **Marca verificada:** 🟡 Parcialmente feito
- **Divergência:** **quinta** confirmação da mesma lacuna. `rg size-limits scripts/hooks/ .github/` devolve uma única linha (`.github/scripts/ci/01-lint.sh:95`); nenhum dos **16** sub-scripts de `scripts/hooks/stop/` conta linhas (`rg -l 'wc -l' scripts/hooks/stop/` é vazio) e `helpers/agent-lint.sh` também não. Além disso a medição regrediu desde 2026-11-07: `bash helpers/size-limits.sh` agora emite "⚠ CLAUDE.md: **602** lines (warning threshold: 600, fails at 700)" — o aviso que em 2026-11-07 estava em 600 voltou a cruzar o limiar.

#### `ref-telemetry-honors-pref-but-pref-defaults-true-on-fresh-install-without-prompt-on-non-interactive-curl-bash`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-07-31
- **Alvo reconstruído:** `scripts/install.sh` + `scripts/lib/telemetry-guard.sh`
- **Commit examinado:** `2e12335` — "fix(install): make the swap failure-safe and stop enabling telemetry without consent" (a mensagem declara "BEHAVIOR CHANGE — telemetry now defaults to disabled when consent cannot be [obtained]")
- **Evidência no HEAD:** `scripts/install.sh:1207` — "TELEMETRY_VALUE=\"false\""; `:1240` — "echo \"→ NOTE: No terminal available to ask about anonymous telemetry, so it is DISABLED.\""; o valor escrito alimenta tanto o caminho canônico (`:1246`, argv[5]) quanto o heredoc de fallback (`:1323` — "\"telemetry\": $TELEMETRY_VALUE"). `scripts/lib/telemetry-guard.sh:14-18` — "FAILS CLOSED — deliberately. A missing preferences file, an unreadable one, a missing `telemetry` key, or no python3 to read it with all mean the same thing: consent was never recorded."
- **Reversão posterior:** nenhuma. `scripts/lib/preferences-defaults.json` ainda traz `telemetry: true`, mas por desenho documentado — `CLAUDE-md/preferences.md:71` — "written by consent, not by the schema … On first install `install.sh` **overwrites** the schema value with the user's answer"
- **Marca verificada:** ✅ Feito

#### `flow-helpers-archive-index-sh-orphan-of-hook-eight-days-after-flagged-rotation-90-day-promise-in-index-md-line-19-20-has-no-trigger-cron-ci-stop-hook-or-update-sh`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-07-31
- **Alvo reconstruído:** `scripts/hooks/stop/99b-archive-index.sh` (gatilho criado) + `helpers/archive-index.sh`
- **Commit examinado:** `cc28900` — "fix(hooks): gate, decompose and harden the lifecycle dispatchers", que criou `scripts/hooks/stop/99b-archive-index.sh` (+54 linhas)
- **Evidência no HEAD:** `scripts/hooks/stop/99b-archive-index.sh:21` — "SCRIPT=\"$REPO_ROOT/helpers/archive-index.sh\"" e `:47` — "OUTPUT=\"$(bash \"$SCRIPT\" 2>&1)\" || OUTPUT=\"\"", com gate de stamp diário em `:36-41`. O nome casa o `SUBSCRIPT_RE` de `scripts/hooks/stop.sh:62`
- **Reprodução no HEAD:** `DEVTEAM_HOOK_DEBUG=1 … bash scripts/hooks/stop.sh` imprime "[devteam:stop] running: 99b-archive-index.sh" e "[devteam:stop] exit 0: 99b-archive-index.sh" — o sub-script é efetivamente despachado
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito
- **Nota de consistência:** esta marca verdadeira é a contraprova direta do item 🔴 `docs-sync-reports-index-preamble-declares-archive-index-trigger-less-while-stop-99b-dispatches-it` — `docs/reports/_index.md:24-27` ainda cita **este** fingerprint como pendente.

#### `auto-update-no-integrity-check`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-07-31 · 🟡 anotada em 2026-10-02, 2026-10-10 e 2026-11-07
- **Alvo reconstruído:** `scripts/lib/installer-fetch.sh` (criado por `2e12335`) + `scripts/update.sh`
- **Commit examinado:** `2e12335` (que criou `scripts/lib/installer-fetch.sh`, +256 linhas)
- **Evidência no HEAD:** integridade de **transporte** entregue — `scripts/lib/installer-fetch.sh` traz `dta_verify_digest` (`:185`) com pinning de ref, checagem de shebang/tamanho e `bash -n`
- **Reversão posterior:** nenhuma
- **Marca verificada:** 🟡 Parcialmente feito
- **Divergência:** **quarta** confirmação. Falta a autenticidade: `ls scripts/install.sh.sha256` → "No such file or directory", e nenhum workflow em `.github/workflows/` gera esse arquivo. `scripts/lib/installer-fetch.sh:183-184` admite por escrito — "No digest available → proceed (see the integrity model note at the top of this file; the project publishes none today)" — e `:200` — "printf '%s' \"$_expected\" | grep -Eq '^[a-fA-F0-9]{64}$' || return 0" faz `dta_verify_digest` **falhar aberta** em todo caminho real, já que `DEVTEAM_INSTALLER_SHA256` não é definida por ninguém e o download de `${GITHUB_RAW}/${_ref}/scripts/install.sh.sha256` nunca encontra o arquivo.

#### `gov-telemetry-send-sh-posthog-key-comments-self-contradict-intentionally-public-vs-replace-before-release-todo-on-default-on-path`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-07-31
- **Alvo reconstruído:** `scripts/helpers/telemetry-send.sh`
- **Commits examinados:** `2e12335` (−/+25 linhas no arquivo) e `6919564` (−/+22 linhas)
- **Evidência no HEAD:** `scripts/helpers/telemetry-send.sh:28-35` — um único bloco coerente: "POSTHOG_API_KEY below is this project's PostHog *project* key (the `phc_` prefix marks a write-only capture key). Such keys are designed to be embedded in client-side code: they can submit events to the project and nothing else — they cannot read, query, export or modify any data. Shipping it in this file is intentional and is not a secret leak … Both values can be overridden via the environment (DEVTEAM_POSTHOG_KEY / DEVTEAM_POSTHOG_ENDPOINT)"
- **TODO resolvido:** `rg -i 'todo|replace|before release' scripts/helpers/telemetry-send.sh` → zero ocorrências
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `agent-security-specialist-body-130-153-hardcodes-per-language-sast-and-dep-audit-commands-bandit-composer-npm-trivy-stack-prescriptive`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-07-31
- **Alvo reconstruído:** `agents/security-specialist.md` → `skills/security/dependency-audit/SKILL.md` (criada por `519ca7e`, +91 linhas)
- **Commit examinado:** `b4e219f` — "refactor(agents): delegate shared context, extract stack-prescriptive bodies" (a mensagem nomeia "security-specialist's nine-scanner command block")
- **Evidência no HEAD:** `agents/security-specialist.md:121-123` — "## Tooling & Dependency Audit\n\nLoad `skills/security/dependency-audit/SKILL.md` and follow its order: always-run tier (secret history scan + broad SAST) → ecosystem lockfile signal → matching dependency scanner → language-specific SAST. Run only what the repository's signals justify … The skill owns the reporting thresholds, the missing-tool policy (`NOT RUN` is never a pass), and the output discipline"
- **Reprodução no HEAD:** `rg -i 'bandit|trivy|npm audit|pip-audit|composer' agents/security-specialist.md` → zero
- **Reversão posterior:** nenhuma, apesar de `agents/security-specialist.md` estar em `/tmp/delta_files.txt`
- **Marca verificada:** ✅ Feito

#### `agent-backend-developer-integration-awareness-section-duplicates-provider-specific-critical-rules-inline-for-7-integrations-systemic-stack-prescriptive-body`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-07-31
- **Alvo reconstruído:** `agents/backend-developer.md` → `## Integration Awareness`
- **Commit examinado:** `b4e219f` ("backend-developer's eight blocks of inlined integration rules")
- **Evidência no HEAD:** `agents/backend-developer.md:70-88` é agora puramente roteador — "Detect the platform from project signals, then load the matching skill **before** writing code. The skill is the source of truth for its rules — never act on these platforms from memory." seguido de uma tabela `| Detection signal | Skill to load |` com 10 linhas; nenhuma regra de provedor reafirmada inline. `:87` fecha com "Quality-scanner and container-environment detection (SonarQube, Docker) is handled by `project-context`"
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `agent-frontend-test-specialist-107-122-hardcodes-react-renderhook-testing-library-and-vue-withsetup-recipes-in-body-stack-agnostic`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-07-31
- **Alvo reconstruído:** `agents/frontend-test-specialist.md` → `skills/testing/frontend-hook-tests/SKILL.md` (criada por `519ca7e`, +109 linhas)
- **Commit examinado:** `b4e219f` ("frontend-test-specialist's React and Vue hook recipes and its decoupled-frontend material")
- **Evidência no HEAD:** `agents/frontend-test-specialist.md:106` — "When business logic lives in a custom hook or composable, load `skills/testing/frontend-hook-tests/SKILL.md` and read only the framework row its Detection table resolves to. It covers when a hook test is worth writing, the React and Vue recipes, async handling, and the anti-patterns." As 8 ocorrências de `renderHook`/`withSetup` vivem hoje em `skills/testing/frontend-hook-tests/SKILL.md`; `rg 'renderHook|withSetup|@testing-library' agents/*.md` → zero
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `agent-devops-specialist-decision-framework-and-anti-overengineering-still-stack-prescriptive-in-body-after-2026-05-18-fix-on-description-and-identity`
- **Severidade / marca original:** HIGH · ✅ Executed: 2026-07-31
- **Alvo reconstruído:** `agents/devops-specialist.md` → `skills/devops/infrastructure-sizing/SKILL.md` (criada por `519ca7e`, +87 linhas)
- **Commit examinado:** `b4e219f` ("devops-specialist's Kubernetes/Nginx/Datadog decision framework"); o diff remove a tabela "Decision Framework — Infrastructure Sizing" (EC2/VPS/ECS/Cloud Run/Kubernetes) e as seis regras "Anti-Overengineering Rules" (Kubernetes, message queue, multi-region, service mesh/Nginx, serverless, Datadog/Grafana Cloud)
- **Evidência no HEAD:** `agents/devops-specialist.md:124-128` — "## Infrastructure Sizing\n\nLoad `skills/devops/infrastructure-sizing/SKILL.md` whenever you choose a hosting or runtime shape … It defines the capability tiers, the trigger that must fire before moving up a tier, and the anti-overengineering rules.\n\n**Start small, measure, scale.** … Never name a specific product as the answer". Nenhuma das duas seções nomeadas no achado existe mais
- **Reversão posterior:** nenhuma, apesar de `agents/devops-specialist.md` estar em `/tmp/delta_files.txt`
- **Marca verificada:** ✅ Feito
- **Observação (fora do escopo do achado):** `## Core Expertise` (`:46-56`) segue nomeando Docker, Nginx, Fail2Ban e Terraform/OpenTofu. É a declaração de domínio do agente, não as duas seções que o achado nomeia, mas vale registrar como tema aberto para o eixo de agnosticismo de stack.

#### `agent-code-reviewer-router-has-ten-structural-review-categories-contradicting-claude-md-183-router-does-not-duplicate-specialist-checks`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-07-31
- **Alvo reconstruído:** `agents/code-reviewer.md`
- **Commit examinado:** `b4e219f` — "code-reviewer now matches its documented contract: it shipped 10 structural review categories while CLAUDE.md says the router coordinates rather than duplicates specialist checks. Nine were covered by the specialists and were removed; the three checks that existed only here … survive as Router Responsibilities"
- **Evidência no HEAD:** `agents/code-reviewer.md:71-73` — "## Router Responsibilities\n\nThese duties sit outside the specialists' category lists and apply to every review, whichever role you adopt." com exatamente três sub-seções: `:75` "### Run the linters before commenting on style", `:84` "### Sweep for cross-cutting silent bugs", `:93` "### Synthesize". Os `###` posteriores (`:141-169`) estão **dentro** do bloco cercado do template de saída sob `## Review Output Format` (`:132`), não são categorias de revisão
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `agent-backend-test-specialist-body-114-120-hardcodes-per-language-coverage-command-matrix-clover-pytest-jacoco-go-simplecov-stack-prescriptive`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-07-31
- **Alvo reconstruído:** `agents/backend-test-specialist.md` → `skills/devops/sonarqube/references/quality-gates.md`
- **Commit examinado:** `b4e219f` ("backend-test-specialist's five-language coverage matrix")
- **Evidência no HEAD:** `agents/backend-test-specialist.md:108` — "1. **Generate coverage in the format SonarQube expects** — read `references/quality-gates.md` in that skill for the per-language test-runner command, output artifact, and `sonar.*coverage.reportPaths` key, then verify `sonar-project.properties` matches"
- **Reprodução no HEAD:** `rg -i 'clover|jacoco|simplecov|pytest|phpunit' agents/backend-test-specialist.md` → zero
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `skill-architecture-awareness-shared-behavioral-skill-enumerates-react-vue-svelte-angular-blade-twig-erb-jinja-laravel-django-rails-eager-loaded-by-three-coding-agents`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-07-31
- **Alvo reconstruído:** `skills/shared/architecture-awareness/SKILL.md`
- **Commit examinado:** `519ca7e` — "feat(skills): add extraction targets, close domain gaps, fix skill defects" (+82/−? em `skills/shared/architecture-awareness/SKILL.md`)
- **Evidência no HEAD:** `rg -i 'framework|react|vue|svelte|angular|blade|twig|erb|jinja|laravel|django|rails|spring|express|next\.js|nuxt' skills/shared/architecture-awareness/SKILL.md` → **zero** ocorrências em 87 linhas. A skill passou a ser comportamental-pura
- **Reversão posterior:** nenhuma. Segue carregada por `agents/backend-developer.md`, `frontend-developer.md` e `mobile-developer.md`, agora sem custo de nomes de framework
- **Marca verificada:** ✅ Feito

#### `token-claude-md-426-lines-still-monolithic-three-extractable-blocks-commands-table-40-stop-sub-script-convention-24-hook-files-map-8-total-72-lines-while-claude-md-folder-already-exists-with-preferences-notifications-user-data-versioning`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-07-31 · 🔴 reaberta em 2026-07-31, 2026-08-14, 2026-08-21 e 2026-09-18 · 📍 re-medida em 2026-10-10 · 🟡 em 2026-11-07
- **Alvo reconstruído:** `CLAUDE.md` + `CLAUDE-md/`
- **Commit examinado:** nenhum da janela de 2026-07-31 extraiu os blocos (`bbb311a` e `7736e20` só **acrescentaram** a `CLAUDE.md`). As extrações reais são posteriores: `CLAUDE-md/hooks.md` (`2b436ea`, 2026-08-03) e `CLAUDE-md/commands.md`
- **Evidência no HEAD:** os três blocos nomeados estão extraídos e substituídos por ponteiros — `CLAUDE.md:274` — "→ See [`CLAUDE-md/commands.md`](CLAUDE-md/commands.md) for the full command → agents table…" (88 linhas) e `CLAUDE.md:512` — "→ See [`CLAUDE-md/hooks.md`](CLAUDE-md/hooks.md) for the Stop and PreToolUse sub-script conventions, the Session Start Banner echo rule, and the full hook files map." (181 linhas). Nenhum dos três segue inline
- **Reversão posterior:** nenhuma extração revertida
- **Marca verificada:** 🟡 Parcialmente feito
- **Divergência:** confirmação da anotação de 2026-11-07, com a medição **piorando**. A premissa central do achado — `CLAUDE.md` monolítico — segue de pé: `wc -l CLAUDE.md` → **602** linhas (426 no registro do achado, 647 em 2026-10-10, 600 em 2026-11-07). Voltou a cruzar o `CLAUDE_MD_WARN=600` de `helpers/size-limits.sh:88`, que agora emite aviso não bloqueante; o `CLAUDE_MD_FAIL=700` (`:89`) é o único gate real. Em outras palavras, 174 linhas extraídas foram repostas por conteúdo novo e o arquivo cresceu 41% desde o achado.

#### `token-foundational-rule-424-lines-across-17-agents`
- **Severidade / marca original:** MEDIUM-HIGH · ✅ Executed: 2026-07-31
- **Alvo reconstruído:** os 17 (hoje 19) `agents/*.md` → `skills/shared/project-context/SKILL.md`
- **Commit examinado:** `b4e219f` — "Foundational Rule delegated. 15 agents inlined the same 12-item context list, 384 duplicated lines fleet-wide … All 17 now use that shape and keep only genuinely role-specific additions."
- **Evidência no HEAD:** `rg -c 'Load \`skills/shared/project-context/SKILL.md\`' agents/*.md` devolve **1 ocorrência em cada um dos 19 agentes**; p.ex. `agents/devops-specialist.md:22` — "Load `skills/shared/project-context/SKILL.md` — covers README, CLAUDE.md, AGENTS.md, project.md, session-summary, development docs, and recent git log."
- **Reprodução no HEAD:** `rg 'synthesized project overview|read most recent entry only' agents/*.md` → zero; a lista de 12 itens não sobreviveu em nenhum agente. As seções `## Foundational Rule` hoje têm 12–42 linhas cada e contêm apenas adições específicas do papel
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

---

## Placar da Fase 1

**34 ✅ · 8 🟡 · 1 🔴** (43 itens)

### Divergências novas (a linha do banco não trazia anotação 🟡/🔴)
| Fingerprint | SEV | Resumo |
|---|---|---|
| `ref-02c-guard-make-composer-shapes-have-no-row-in-scoped-test-runner-table` | MEDIUM-HIGH | `TESTPATH=`/`FILTER=` documentados, mas a tabela *Runner Filters* segue sem linha para npm/composer/make e `SKILL.md:59` continua declarando legítimo o `make test-unit`/`npm run test:unit` que o guard bloqueia (exit 2, reproduzido) |
| `ref-docs-agents-md-model-column-wrong-…-setup-assistant-listed-sonnet-actually-opus` | HIGH | As duas células nomeadas foram corrigidas, mas o sub-escopo "unvalidated" nunca fechou e a tabela voltou a divergir: `backend-test-specialist` listado `repetitive` nos dois idiomas contra `tier: backend-exec` no frontmatter, desde `1f1c837` (2026-07-31) |

### Divergências já anotadas (reconfirmadas, nenhuma melhorou)
| Fingerprint | SEV | Resumo |
|---|---|---|
| `docs-sync-reports-index-preamble-declares-archive-index-trigger-less-while-stop-99b-dispatches-it` | MEDIUM-HIGH | 🔴 · `_index.md:24-27` segue afirmando que `archive-index.sh` não tem gatilho; `stop/99b-archive-index.sh` o despacha (reproduzido com `DEVTEAM_HOOK_DEBUG=1`) |
| `flow-02c-escape-hatch-anchored-while-detection-is-substring` | MEDIUM-HIGH | 🟡 · `CONFIRM_RE` não admite `"`/`'`; `sh -c "DEVTEAM_FULL_SUITE_CONFIRMED=1 npm test"` segue bloqueado |
| `auto-install-sh-bash-source-fallback-resolves-to-cwd-and-sources-project-lib` | MEDIUM-HIGH | 🟡 · `install.sh:24` reintroduziu `${BASH_SOURCE[0]}` sem guarda; `bash < install.sh` aborta com unbound variable |
| `ref-claude-md-file-structure-omits-helpers-and-privacy-and-claude-md-folder` | HIGH | 🟡 · `.claude/` sem entrada na árvore; `TERMS.md` e `infra/` rastreados e ausentes |
| `flow-size-limits-sh-ci-only-warn-only-…-never-blocking` | HIGH | 🟡 · quinta confirmação: nenhum dos 16 sub-scripts de `stop/` conta linhas; e `CLAUDE.md` voltou a 602 linhas (aviso cruzado) |
| `auto-update-no-integrity-check` | MEDIUM-HIGH | 🟡 · quarta confirmação: `scripts/install.sh.sha256` inexistente, sem workflow que o gere, `dta_verify_digest` falha aberta (`installer-fetch.sh:200`) |
| `token-claude-md-426-lines-still-monolithic-…` | MEDIUM-HIGH | 🟡 · três blocos extraídos, mas `CLAUDE.md` em 602 linhas (426 no achado, 600 em 2026-11-07) — piorou |

### Itens que dependeram da nota de método (o `alvo:` não era o arquivo corrigido)
Os **18** itens do bloco 2026-07-31 (`alvo:` = `None`) exigiram reconstrução do alvo pelo tema.
Além deles, **4** itens com `alvo:` preenchido só se confirmaram fora do `alvo:`:
- `ref-02c-guard-make-composer-shapes-…` — `alvo:` é o hook, a correção está em `skills/shared/scoped-test-execution/SKILL.md`
- `flow-architect-claude-only-async-tool-names-rendered-verbatim` — `alvo:` é `agents/software-architect.md`, a correção está em `scripts/lib/tool-map.json` + `scripts/lib/render_provider.py`
- `flow-learn-nudge-ancestor-test-inverted-in-four-commands` — `alvo:` é `commands/merge.md`, mas a remediação também reescreveu `pr.md`, `refactor.md`, `audit.md` e `sprint.md`
- `docs-sync-preferences-mirror-registry-names-readmes-omits-docs-pair` — `alvo:` é `CLAUDE.md`, mas metade da correção está em `docs/user-preferences{,.pt-BR}.md` (commit diferente)

**Total: 22 de 43 itens dependeram da nota de método.**

### Reversões silenciosas encontradas
1. **`scripts/install.sh:24`** — `d454f63` (2026-10-02, "fix(scripts): resolve python3 to a working Python 3.9+ on Windows Git Bash"), **posterior a `88834b6` no mesmo dia**, reintroduziu `"$(dirname "${BASH_SOURCE[0]}")"` sem guarda acima do código que `88834b6` acabara de endurecer. Sob `set -euo pipefail` (`:21`) o install pipeado morre na linha 24. Nenhum teste pega: `tests/test_audit_report_fixes.py::test_piped_install_ignores_cwd_lib_state` só assere a ausência do marcador `PWNED`, que um abort satisfaz.
2. **`agents/backend-test-specialist.md` tier** — `1f1c837` (2026-07-31) trocou `tier: repetitive` → `tier: backend-exec` **depois** de `bbb311a` ter escrito `repetitive` em `docs/agents.md` e `docs/agents.pt-BR.md` no mesmo dia. Aberto há ~3,5 meses; nenhum gate cobre essa tabela.
3. **`CLAUDE.md` 600 → 602 linhas** — regressão de medição desde a verificação de 2026-11-07, suficiente para recruzar `CLAUDE_MD_WARN=600` (`helpers/size-limits.sh:88`). Afeta os itens `token-claude-md-426-lines-…` e `flow-size-limits-sh-…`.

### Amostra aleatória de 30% — MEDIUM / LOW-MEDIUM / LOW (32 itens, `seed=20261114`)


#### `flow-merge-md-arguments-target-branch-parse-can-swallow-no-teardown-flag`
- **Severidade / marca original:** LOW · ✅ Executed: 2026-10-02
- **Commit examinado:** `a2cf59c` — "fix(commands): fire the learn nudge on a moved branch tip, reach worktree finalization in merge"
- **Evidência no HEAD:** `commands/merge.md:31` — "**Target** — strip every `--flag` and the `skip-commit` / `abort-on-dirty` tokens from `$ARGUMENTS`; the first remaining token, if any, is the target."
- **Reversão posterior:** nenhuma (`f4986ea`, `bd1313f` só ampliaram o strip e o nudge)
- **Marca verificada:** ✅ Feito

#### `ref-templates-dir-shipped-but-not-symlinked-relative-path-broken-from-agent-cwd`
- **Severidade / marca original:** MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `6919564` — "refactor(commands,scripts): remove cross-cutting duplication, close the size gate" (+ `7736e20` para o padrão de autoria e `c7535b7` para o validador)
- **Evidência no HEAD:** `skills/shared/runbook/SKILL.md:8` — "Use the template at `.dev-team-agents/templates/runbook-template.md`."; `CLAUDE.md:135` (em `7736e20`) — "**Reference templates by their installed path** — `.dev-team-agents/templates/<name>.md>`"; `helpers/orphan-template-scan.sh` passa limpo no HEAD ("orphan-template-scan: clean ✓")
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito
- *Nota de método aplicada:* o `alvo:` era `None`; o alvo real foi reconstruído pelo tema (consumidores de `templates/*` + `scripts/install.sh` + validador).

#### `ref-refactor-command-missing-interaction-patterns-load-despite-yes-no-prompts`
- **Severidade / marca original:** MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `6919564` — "refactor(commands,scripts): remove cross-cutting duplication, close the size gate"
- **Evidência no HEAD:** `commands/refactor.md:6` — "Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt."; os dois prompts em texto puro viraram `AskUserQuestion` (`:22` e `:32`)
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `ref-three-reviewers-todo-fixme-issue-tracker-tickets-bullet-duplicated-verbatim-no-shared-source-distinct-from-reviewer-base-and-reviewer-mindset-already-extracted`
- **Severidade / marca original:** LOW-MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `b4e219f` — "refactor(agents): delegate shared context, extract stack-prescriptive bodies"
- **Evidência no HEAD:** as três cópias desapareceram (`rg -n 'TODO/FIXME' agents/ skills/` só devolve `skills/third-party/security-audit/ATTACK-CLASSES.md:114`, não relacionado); a casa canônica é `skills/shared/comments-policy/SKILL.md:33` — "| TODO / FIXME | Create an issue tracker ticket |", carregada pelos três revisores (`frontend-reviewer.md:33`, `backend-reviewer.md:32`, `code-reviewer.md:57`)
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `auto-install-no-rollback-on-second-mv-failure`
- **Severidade / marca original:** MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `2e12335` — "fix(install): make the swap failure-safe and stop enabling telemetry without consent"
- **Evidência no HEAD:** `scripts/install.sh:306` — `trap _cleanup EXIT`; `:268-301` restaura `OLD_DIR` quando `SWAP_DONE != true`; o swap renomeia de lado em vez de apagar antes (`:445-489`: `NEW_DIR="$INSTALL_DIR.new.$$"` → `OLD_DIR="$INSTALL_DIR.old.$$"` → `_mv_or_copy "$NEW_DIR" "$INSTALL_DIR"` → `SWAP_DONE=true`); o `rm -rf "$USER_DATA_DIR"` antes do `mv` saiu — hoje é `cp -R "$USER_DATA_DIR" "$NEW_DIR/user-data"` (`:451-453`)
- **Reversão posterior:** nenhuma (43 commits posteriores no arquivo, todos preservando `trap`/`SWAP_DONE`)
- **Marca verificada:** ✅ Feito

#### `flow-stop-dispatcher-globs-all-sh-no-allowlist-or-per-subscript-toggle-any-dropped-file-auto-executes`
- **Severidade / marca original:** MEDIUM · ✅ Executed: 2026-07-31 (🟡 anotado em 2026-11-07)
- **Commit examinado:** `cc28900` — "fix(hooks): gate, decompose and harden the lifecycle dispatchers"
- **Evidência no HEAD:** `scripts/hooks/stop.sh:64` — `for script in "$HOOKS_DIR"/*.sh; do` (glob intacto); o que entrou foi `:62` — `SUBSCRIPT_RE='^[0-9]{2}[a-z]?-[a-z0-9]([a-z0-9-]*[a-z0-9])?\.sh$'`, filtro por convenção de nome; `grep -rn "DEVTEAM_DISABLE\|disabled_hooks" scripts/ CLAUDE-md/` → zero
- **Reversão posterior:** nenhuma
- **Marca verificada:** 🟡 Parcialmente feito
- **Divergência:** confirma a anotação de 2026-11-07. O glob não foi trocado por allowlist: qualquer `NN-nome.sh` solto em `stop/` (e em `pre-tool-use/`, `:31-37`) continua auto-executando. O segundo sub-escopo do slug — toggle por sub-script — não existe em nenhuma forma.

#### `flow-pre-tool-use-dispatcher-no-mention-of-sub-script-order-convention-asymmetric-with-stop-dispatcher`
- **Severidade / marca original:** MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `bbb311a` — "docs: correct stale authoring standards, structure maps and command tables" (convenção) + `cc28900` — "fix(hooks): gate, decompose and harden the lifecycle dispatchers" (colisão `02-`)
- **Evidência no HEAD:** `CLAUDE-md/hooks.md:51` — "### PreToolUse Hook Sub-script Convention" com tiers e `:63` — "One script per bare number … Add a **lowercase letter suffix** (`02b-`, `02c-`, …) instead."; a colisão real foi desfeita — `ls scripts/hooks/pre-tool-use/` mostra `02-graphify-hint.sh` e `02b-telemetry.sh`
- **Reversão posterior:** nenhuma (o bloco migrou de `CLAUDE.md` para `CLAUDE-md/hooks.md`, referenciado em `CLAUDE.md:512`)
- **Marca verificada:** ✅ Feito

#### `token-pre-tool-use-01-check-updates-forks-python3-to-read-interval-before-ttl-early-exit-on-every-tool-call-burst-overhead`
- **Severidade / marca original:** MEDIUM · ✅ Executed: 2026-07-31 (🟡 2026-10-02 · 🟢 2026-11-07)
- **Commit examinado:** `cc28900` — "fix(hooks): gate, decompose and harden the lifecycle dispatchers" (introduziu `INTERVAL_CACHE_FILE="$USER_DATA_DIR/.update-check-interval"`, `01-check-updates.sh:24`, lido por `uc_interval_hours` antes do `uc_ttl_fresh` em `:40-41`)
- **Evidência no HEAD:** o sidecar foi removido de propósito — `scripts/hooks/lib/update-check.sh:51-60`: "This used to cache the resolved value in a standalone sidecar file … so the cache is dropped and the preference is read directly"; a ordenação persiste (`:63-70` `uc_interval_hours` → `uc_read_pref` forka `python3`, chamada antes de `uc_ttl_fresh` em `session-start.sh:211-212`), mas só 1× por sessão; o script original existe apenas desativado (`scripts/hooks/pre-tool-use/_disabled-01-check-updates.sh`, 89 linhas)
- **Reversão posterior:** `7dbc646` (2026-08-03) e `ba39c86` (2026-08-06) desfizeram o caminho; `3c46d04` (2026-08-06) "perf(hooks): move update-check from PreToolUse to SessionStart" matou o sintoma por outra via
- **Marca verificada:** 🔴 Não feito
- **Divergência:** confirma as duas anotações anteriores. A remediação da janela (sidecar de intervalo) foi revertida, logo o ✅ de 2026-07-31 não corresponde a nenhum fato sobrevivente; a marca correta é 🟢 (sintoma extinto por relocação em 2026-08-06), já registrada na linha do banco.

#### `flow-check-fingerprint-uniqueness-scans-only-index-md-blind-to-documented-archive-rotation-cross-file-dupes-undetected`
- **Severidade / marca original:** MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `c7535b7` — "ci: close validator and enforcement gaps, repair the rotation helper"
- **Evidência no HEAD:** `helpers/check-fingerprint-uniqueness.sh:19-24` — "Build the list of bank files: the live index first, then any quarterly archives." com `find "$REPORTS_DIR" -maxdepth 1 -name '_index-archive-*.md' … | sort`; execução no HEAD: "✓ All 318 fingerprint slugs are unique across 2 bank file(s)."
- **Reversão posterior:** nenhuma (nenhum commit tocou o helper depois de `c7535b7`)
- **Marca verificada:** ✅ Feito

#### `flow-session-summary-closure-step-present-in-eight-of-ten-workflows-but-absent-from-fullstack-and-refactor-highest-fanout`
- **Severidade / marca original:** LOW-MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `6919564` — "refactor(commands,scripts): remove cross-cutting duplication, close the size gate"
- **Evidência no HEAD:** `commands/fullstack.md:92` e `commands/refactor.md:157` — "## Session close (mandatory)", com o passo 1 "**Session summary** — append this session's contribution to today's entry in `.dev-team-agents/user-data/session-summary.md`" nos dois arquivos
- **Reversão posterior:** nenhuma (o bloco está hoje em 9 comandos)
- **Marca verificada:** ✅ Feito

#### `flow-workflows-no-commit-or-pr-step`
- **Severidade / marca original:** LOW-MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `6919564` — "refactor(commands,scripts): remove cross-cutting duplication, close the size gate"
- **Evidência no HEAD:** `commands/fullstack.md:99` — "**Hand off** — the working tree is left dirty on purpose. Close with one line naming the next step: `/devteam:commit` … then `/devteam:pr`"; o mesmo passo existe nos seis comandos nomeados pelo achado (`backend`, `frontend`, `fullstack`, `mobile`, `design`, `refactor`) e em `relayout`, `seo`, `spec`
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `flow-pre-tool-use-01-check-updates-195-lines-3rd-largest-script-no-fragmentation`
- **Severidade / marca original:** LOW · ✅ Executed: 2026-07-31
- **Commit examinado:** `cc28900` — "fix(hooks): gate, decompose and harden the lifecycle dispatchers"
- **Evidência no HEAD:** o monolito foi fragmentado na própria janela (209 → 78 linhas em `cc28900`, com `scripts/hooks/lib/update-check.sh` novo em 260 linhas) e a fragmentação sobreviveu: hoje `scripts/hooks/pre-tool-use/_disabled-01-check-updates.sh` tem 89 linhas e a biblioteca compartilhada `scripts/hooks/lib/update-check.sh` tem 326
- **Reversão posterior:** nenhuma (a lógica migrou para `session-start.sh` em `3c46d04`, mantendo a biblioteca extraída)
- **Marca verificada:** ✅ Feito

#### `flow-setup-slash-command`
- **Severidade / marca original:** LOW · ✅ Executed: 2026-07-31
- **Commit examinado:** `519ca7e` — "feat(skills): add extraction targets, close domain gaps, fix skill defects" (criou `commands/setup.md`, 47 linhas, + 1 linha em `scripts/lib/commands.json`)
- **Evidência no HEAD:** `commands/setup.md:2` — "description: Onboard this project into dev-team-agents (first run or refresh)"; registrado em `scripts/lib/commands.json:21` — `"setup": { "tier": "reasoning", "agent": "setup-assistant", … }`
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `auto-no-skill-name-uniqueness-check`
- **Severidade / marca original:** LOW · ✅ Executed: 2026-07-31
- **Commit examinado:** `c7535b7` — "ci: close validator and enforcement gaps, repair the rotation helper"
- **Evidência no HEAD:** `helpers/agent-lint.sh:350-362` — "── Skill names must be globally unique" / `check_skill_name_uniqueness()` com `ERRORS+=("  · duplicate skill name '${dup}' declared in: ${files}")`, invocado em `:596`; o check irmão `name == basename(dir)` também entrou (`:306`)
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `agent-setup-assistant-lines-60-70-docker-compose-version-detection-inline-bash-block-stack-prescriptive-in-agent-body-while-mobile-detection-and-stack-detection-already-extracted-to-skills`
- **Severidade / marca original:** MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `b4e219f` — "refactor(agents): delegate shared context, extract stack-prescriptive bodies"
- **Evidência no HEAD:** o bloco bash inline saiu; `agents/setup-assistant.md:66` — "**Docker Compose command form:** only when the scan finds a compose file, apply the Docker Compose probe from the already-loaded `stack-detection` skill"; a sonda está na casa canônica, `skills/shared/stack-detection/SKILL.md:40-57` ("### Docker Compose command form")
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `agent-frontend-developer-security-section-134-139-hardcodes-dangerouslysetinnerhtml-vhtml-vite-next-public-framework-apis-in-agent-body`
- **Severidade / marca original:** MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `b4e219f` — "refactor(agents): delegate shared context, extract stack-prescriptive bodies"
- **Evidência no HEAD:** `agents/frontend-developer.md:130` — "**Raw HTML injection**: any API the framework offers for bypassing escaping (e.g. `dangerouslySetInnerHTML`, `v-html`, `innerHTML`) …"; `:132` — "only variables carrying the build tool's public prefix (e.g. `VITE_*`, `NEXT_PUBLIC_*`) reach the client". As duas linhas citadas pelo achado foram reescritas: a regra é neutra e os identificadores sobrevivem só como exemplo parentético
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `skill-mobile-ios-and-android-wrapper-pattern-first-instruction-is-load-ios-hig-or-material-design-doubling-token-cost-251-and-256-lines-total-instead-of-218-and-221-net-loss-vs-loading-the-large-skill-directly`
- **Severidade / marca original:** MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `519ca7e` (wrappers) + `b4e219f` (gate no agente)
- **Evidência no HEAD:** os dois defeitos compostos caíram. (a) a linha de carga duplicada saiu do wrapper — `skills/mobile/ios/SKILL.md:6-10` agora é "## Scope … The **design** half lives in `skills/mobile/ios-hig/SKILL.md` … Load it **only when the task touches UI**" (antes, `519ca7e~1:7` era "Load `skills/mobile/ios-hig/SKILL.md` for the full reference"). (b) o gate narrativo virou dois gates explícitos — `agents/mobile-developer.md:73` "**Gate 2 — does the task touch UI?** Add the design skill **only** when …" e `:75` "run both gates **per platform actually targeted**"
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `agent-frontend-test-specialist-262-vs-backend-160-asymmetric-decoupled-frontend-block-inlined`
- **Severidade / marca original:** MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `b4e219f` — "refactor(agents): delegate shared context, extract stack-prescriptive bodies" (alvo de extração criado por `519ca7e`: `skills/testing/decoupled-frontend/SKILL.md`, 104 linhas)
- **Evidência no HEAD:** `agents/frontend-test-specialist.md:124-126` — "## Decoupled Frontend … load `skills/testing/decoupled-frontend/SKILL.md` — network-layer mocking with MSW, the mandatory async state-coverage table, contract awareness, test data factories, visual regression, and the selector priority table"; os blocos inline (MSW, tabela de estados, Selector Priority) não existem mais no corpo do agente. Assimetria: 266/164 (+102) antes → 180/135 (+45) no commit → 200/152 (+48) no HEAD
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `agent-backend-developer-description-enumerates-rest-graphql-mvc-server-rendered-paradigms-on-identity-surface-last-coding-agent-desc-while-body-claims-stack-agnostic`
- **Severidade / marca original:** LOW-MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `b4e219f` — "refactor(agents): delegate shared context, extract stack-prescriptive bodies"
- **Evidência no HEAD:** `agents/backend-developer.md:3` — "Adapts to whatever server-side style the project uses — API-first or server-rendered, layered or flat." (antes: "Works in both decoupled (REST API, GraphQL) and monolithic (MVC, server-rendered templates) architectures")
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `agent-setup-assistant-immutability-section-225-238-redundant-with-warning-line-24-duplicate-md-headers`
- **Severidade / marca original:** LOW-MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `b4e219f` — "refactor(agents): delegate shared context, extract stack-prescriptive bodies" (o diff remove um `## Immutability Warning`)
- **Evidência no HEAD:** `rg -n '^## Immutability' agents/setup-assistant.md` devolve uma única ocorrência — `:180`
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `agent-software-architect-foundational-rule-51-lines-2x-avg`
- **Severidade / marca original:** LOW-MEDIUM · ✅ Executed: 2026-07-31 (🔴 2026-08-21 · 🔴 2026-11-07)
- **Commit examinado:** `b4e219f` — "refactor(agents): delegate shared context, extract stack-prescriptive bodies"
- **Evidência no HEAD:** `agents/software-architect.md:19-62` — bloco `## Foundational Rule` de **43 linhas**, o maior do repo; medição em todos os 19 agentes: 43 (software-architect) · 39 (security-specialist) · 30 (code-reviewer) · mediana **18** → 2,39× a mediana. Trajetória: 37 linhas em `b4e219f~1` → 41 no próprio commit remediador → 43 no HEAD
- **Reversão posterior:** nenhuma reversão; crescimento contínuo
- **Marca verificada:** 🔴 Não feito
- **Divergência:** terceira confirmação das anotações de 2026-08-21 e 2026-11-07. O commit da janela tocou o arquivo mas **aumentou** o bloco em vez de reduzi-lo, e ele segue crescendo; a condição do achado (maior Foundational Rule do repo, ~2× a média) nunca foi satisfeita.

#### `agent-three-reviewers-overlap`
- **Severidade / marca original:** LOW-MEDIUM · ✅ Executed: 2026-07-31 (🟡 2026-11-07)
- **Commit examinado:** `b4e219f` — "refactor(agents): delegate shared context, extract stack-prescriptive bodies"
- **Evidência no HEAD:** o primeiro sub-escopo saiu — os Foundational Rules divergiram (17 linhas em `backend-reviewer.md:23`, 19 em `frontend-reviewer.md:23`, 30 em `code-reviewer.md:41`). O segundo sub-escopo persiste: o esqueleto de relatório segue inline e quase verbatim nos três — `backend-reviewer.md:155-188`, `frontend-reviewer.md:147-...`, `code-reviewer.md:132-168`, cada um abrindo com a mesma linha "Load `skills/shared/output-format/SKILL.md` — all review output must follow pure markdown format…" e repetindo as mesmas seções (`### Summary` / `### Blocking Issues` / `### Security Findings` / `### Suggestions` / `### Nitpicks` / `### Architecture Conformance`). `skills/shared/pr-review/SKILL.md` tem "## Review Comment Format" (`:73`) mas não o esqueleto de relatório, logo não há casa canônica
- **Reversão posterior:** nenhuma
- **Marca verificada:** 🟡 Parcialmente feito
- **Divergência:** confirma a anotação de 2026-11-07 — falta extrair o esqueleto de relatório para uma casa canônica (candidata natural: `skills/shared/pr-review/SKILL.md`).

#### `skill-integrations-gotrue-225-lines-largest-integration-skill-fourth-largest-overall-no-references-extraction-narrative-load-gate`
- **Severidade / marca original:** LOW-MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `519ca7e` — "feat(skills): add extraction targets, close domain gaps, fix skill defects"
- **Evidência no HEAD:** `skills/integrations/gotrue/SKILL.md` tem **73 linhas** (eram 225) e `:61-62` é a tabela de carga condicional — "| `references/client-and-admin-api.md` | Implementing sign-in, sessions, refresh, the Admin API, or server-side JWT verification |" / "| `references/claims-and-hooks.md` | Adding custom claims, writing RLS against them, or configuring GoTrue hooks |"; os dois arquivos existem em `skills/integrations/gotrue/references/`
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `skill-discovery-mode-no-stale-lock-cleanup-script-30min-rule-only-documented`
- **Severidade / marca original:** LOW-MEDIUM · ✅ Executed: 2026-07-31 (🟡 2026-11-07)
- **Commit examinado:** `519ca7e` — "feat(skills): add extraction targets, close domain gaps, fix skill defects"
- **Evidência no HEAD:** ordenação e portabilidade corrigidas — `skills/shared/discovery-mode/SKILL.md:114` "The staleness sweep must come *before* the bail-out" e `:122` `if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +30 2>/dev/null)" ]`. Mas o defeito nomeado no slug persiste: `grep -rn discovery-lock scripts/ helpers/` devolve zero, e `:148` admite — "No scheduled job sweeps orphaned locks. A lock whose owner crashed persists until the next agent runs step 1 above"
- **Reversão posterior:** nenhuma
- **Marca verificada:** 🟡 Parcialmente feito
- **Divergência:** confirma a anotação de 2026-11-07 — não existe script/hook de limpeza de lock órfão; a regra dos 30 min continua só documentada dentro da própria skill.

#### `skill-sonarqube-435-lines-overlap-with-reviewer-base-detection-block`
- **Severidade / marca original:** LOW · ✅ Executed: 2026-07-31
- **Commit examinado:** `519ca7e` — "feat(skills): add extraction targets, close domain gaps, fix skill defects"
- **Evidência no HEAD:** `skills/shared/reviewer-base/SKILL.md:17` — "Detect SonarQube using the `## Detection Signals` table in `skills/devops/sonarqube/SKILL.md` — if **any** signal in that table matches, load the skill. That table is the single source of truth; do not maintain or infer a signal list here"; a lista de 3 sinais restatada foi removida e a tabela canônica (6 sinais) está em `skills/devops/sonarqube/SKILL.md:8-18`
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `token-token-efficiency-skill-itself-154-lines-eager-loaded-by-all-17-agents-meta-irony-multiplied-in-multi-agent-flows`
- **Severidade / marca original:** MEDIUM · ✅ Executed: 2026-07-31 (🔴 2026-08-14)
- **Commit examinado:** `b4e219f` — "refactor(agents): delegate shared context, extract stack-prescriptive bodies" (mensagem: "The token-efficiency load line, drifted into nine wordings, is now one")
- **Evidência no HEAD:** a linha de carga continua no Foundational Rule de **18 dos 19 agentes** (só `agents/orchestrator.md` não a tem) — ex. `agents/software-architect.md:31` "Apply `skills/shared/token-efficiency/SKILL.md` — prefer `grep`/`head` over full reads." (dentro do bloco FR, `:19-62`); a skill está em **160 linhas** (eram 154); `CLAUDE.md:239-244` continua escopando a carga completa a três casos de autoria e declara "Key rules (apply without loading the full skill)"
- **Reversão posterior:** nenhuma; apenas unificação de redação
- **Marca verificada:** 🔴 Não feito
- **Divergência:** confirma a anotação de 2026-08-14. O commit da janela padronizou o texto da linha, não a condicionou: o load segue incondicional em 18/18 agentes que o declaram e a skill cresceu, contra a própria regra de `CLAUDE.md`.

#### `token-notifier-loads-45-tips-3-languages-emits-1-per-day-99pct-waste`
- **Severidade / marca original:** MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `6919564` — "refactor(commands,scripts): remove cross-cutting duplication, close the size gate"
- **Evidência no HEAD:** os 45 strings saíram do script para `scripts/hooks/stop/tips/tips.{en,pt-BR,es}.txt` (15 linhas cada); `scripts/hooks/stop/04-notifier.sh:213-216` — "Dedupe before reading the file: after the first Stop of the day this is a single grep and the tip file is never opened" + `TIP=$(sed -n "$((TIP_INDEX + 1))p" "$TIP_FILE" …)`, isto é, uma única linha de um único locale, e só quando o gate diário abre
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `token-conventional-commits-skill-138-lines-loaded-by-commit-and-pr-commands-but-also-mentioned-as-skill-load-in-claude-md-skill-loads-by-table-format-not-prose`
- **Severidade / marca original:** LOW-MEDIUM · ✅ Executed: 2026-07-31 (🔴 2026-09-04 · 🔴 2026-11-07)
- **Commit examinado:** `6919564` — "refactor(commands,scripts): remove cross-cutting duplication, close the size gate" (removeu a tabela de camadas restatada em `commands/commit.md`, não a diretiva de carga)
- **Evidência no HEAD:** `commands/commit.md:7` — "Load the skill at `skills/shared/conventional-commits/SKILL.md` before doing anything."; a skill está em **169 linhas** (eram 138); `CLAUDE.md:521-522` manda carregá-la e, no item seguinte, "**Defer to the project's own pattern first** … If a project-specific pattern is clearly in use, follow it instead" — ou seja, o carregamento incondicional pode ser descartado
- **Reversão posterior:** nenhuma
- **Marca verificada:** 🔴 Não feito
- **Divergência:** terceira confirmação (2026-09-04 e 2026-11-07). Nenhum commit, na janela ou depois, tocou a diretiva de carga de `commands/commit.md:7`; a contradição com a Commit Rule permanece e o custo cresceu de 138 para 169 linhas.

#### `token-docs-sync-closing-directive-after-completing-any-task-duplicated-verbatim-across-twelve-agents-no-single-source-multiplied-in-multi-agent-flows`
- **Severidade / marca original:** LOW-MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `b4e219f` — "refactor(agents): delegate shared context, extract stack-prescriptive bodies"
- **Evidência no HEAD:** casa canônica criada no próprio commit — `skills/shared/docs-sync/SKILL.md:137` "## Task Closure Rule" com "**This is the canonical statement of the rule. Agents reference it; they do not restate it.**"; `rg -n 'After completing any task' agents/` devolve **zero** e cada um dos 13 agentes tem só um ponteiro de uma linha (ex. `agents/backend-developer.md:170` — "Load `skills/shared/docs-sync/SKILL.md` — its Task Closure Rule governs when delivered work requires a `docs/` patch")
- **Reversão posterior:** nenhuma
- **Marca verificada:** ✅ Feito

#### `token-sonarqube-detection-block-redundant`
- **Severidade / marca original:** LOW-MEDIUM · ✅ Executed: 2026-07-31 (🟡 2026-08-14 · 🟡 2026-09-04)
- **Commit examinado:** `b4e219f` — "refactor(agents): delegate shared context, extract stack-prescriptive bodies" (mensagem: "the SonarQube detection triple (11 copies) is in project-context")
- **Evidência no HEAD:** 10 das 11 cópias saíram; a 11ª persiste — `agents/devops-specialist.md:82` "| `sonar-project.properties`, `.sonarcloud.properties`, `sonarqube` service in compose, or `SONAR_TOKEN` env var | `skills/devops/sonarqube/SKILL.md` |", restatando 4 dos 6 sinais da tabela canônica de `skills/devops/sonarqube/SKILL.md:12-18` (faltam `sonar-scanner`/`mvn sonar:sonar`/`./gradlew sonar` em CI e `SONAR_HOST_URL`); a linha canônica de rota está em `skills/shared/project-context/SKILL.md:331`
- **Reversão posterior:** nenhuma
- **Marca verificada:** 🟡 Parcialmente feito
- **Divergência:** terceira confirmação das anotações de 2026-08-14 e 2026-09-04 (a linha migrou de `:81` para `:82`, conteúdo idêntico). Falta remover a última cópia em `devops-specialist`.

#### `token-worktree-isolation-block-7-lines-x-8-agents`
- **Severidade / marca original:** LOW-MEDIUM · ✅ Executed: 2026-07-31
- **Commit examinado:** `b4e219f` — "refactor(agents): delegate shared context, extract stack-prescriptive bodies"
- **Evidência no HEAD:** a cascata de 3 ramos deixou de ser restatada; nos 9 agentes de código o bloco `## Worktree Isolation` tem **uma linha de prosa** delegando à skill — `agents/backend-developer.md:66` "resolve the worktree decision with the cascade in `skills/shared/worktree/SKILL.md` § Decision Cascade (spawn-prompt `WORKTREE_PATH`/`BRANCH` → session file → `worktree_active` preference → ask once)"; a casa canônica é `skills/shared/worktree/SKILL.md` (113 linhas)
- **Reversão posterior:** nenhuma (`c19f060`, 2026-10-02, reforçou a delegação)
- **Marca verificada:** ✅ Feito

#### `token-commands-commit-md-145-lines-and-refactor-md-156-lines-largest-command-files`
- **Severidade / marca original:** LOW · ✅ Executed: 2026-07-31 (🟡 2026-08-21)
- **Commit examinado:** `6919564` — "refactor(commands,scripts): remove cross-cutting duplication, close the size gate" (+ `c7535b7`, que estendeu `helpers/size-limits.sh` a `commands/`)
- **Evidência no HEAD:** o gate existe e passa — `helpers/size-limits.sh:50` `COMMAND_LIMIT=200`, execução "size-limits: clean ✓". Mas os dois arquivos não encolheram: `commands/commit.md` = **193** linhas e `commands/refactor.md` = **172** (eram 177/159 no achado e 145/156 no slug); mediana dos 42 comandos = **63**, máximo = 199 (`learn.md`). `commit.md` é o 4º maior comando do repo
- **Reversão posterior:** nenhuma reversão; crescimento contínuo (+16 em `commit.md` e +13 em `refactor.md` desde a verificação de 2026-08-21)
- **Marca verificada:** 🟡 Parcialmente feito
- **Divergência:** confirma a anotação de 2026-08-21 e piora os números. O sub-escopo entregue foi o gate de 200 linhas e a de-duplicação; o sub-escopo do slug — trazer os dois maiores arquivos de comando para perto da mediana — nunca foi feito: ambos seguem a 2,7–3,1× a mediana, logo abaixo do teto do gate.

---

## Placar

**23 ✅ · 5 🟡 · 4 🔴** (32 itens)

---

## Fase 1b — item a item (140 de 140)


## Lote f1b_1 (itens 1–35)

- `flow-relayout-design-discovery-names-storybook-tailwind` — **ainda reproduz** — `commands/relayout.md:32` "a Storybook config, a Tailwind/theme config" — seção de design discovery segue nomeando os dois; `rg -c` = 1 ocorrência de cada (igual ao registro), só re-ancorada de linha.
- `docs-sync-02c-comment-cites-graphify-hint-as-sed-precedent` — **ainda reproduz** — `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:28` "consistent with 02-graphify-hint.sh's pure-bash approach on the hot path" — comentário migrou de `:18` para `:28` e o precedente citado agora está DEPRECATED (ADR-0019) com a justificativa dos "2 forked subprocesses" ainda viva em `02-graphify-hint.sh:32`; piorou em qualidade: cita como precedente um arquivo marcado para remoção.
- `flow-audit-step2-unconditional-docker-stack-ignores-isolate-pref-compose-gate` — **ainda reproduz** — `commands/audit.md:48` "After worktree creation, spin up an isolated Docker stack following the worktree's docker-isolation references." — incondicional, sem os dois gates; re-ancorado de `:54` para `:48`.
- `flow-mobile-command-spawn-line-enumerates-stacks-dropped-from-agent-description` — **ainda reproduz** — `commands/mobile.md:21` "(React Native, Expo, Flutter, native iOS/Android)" — as 5 stacks seguem na linha de spawn e seguem ausentes da `description:` de `agents/mobile-developer.md`; re-ancorado de `:19` para `:21`.
- `agent-database-specialist-access-inlines-supabase-cli-while-delegating-others` — **ainda reproduz** — `agents/database-specialist.md:134` "CLI patterns are in each engine's per-engine skill. Supabase PostgreSQL: `psql \"$SUPABASE_DB_URL\"`." — delegação e inline na mesma linha; re-ancorado de `:133` para `:134` (`## Database Access` em `:132`).
- `ref-docs-agents-md-tier-column-stale-backend-test-specialist-listed-repetitive` — **ainda reproduz** — `docs/agents.md:28` e `docs/agents.pt-BR.md:28` "| `backend-test-specialist` | … | `repetitive` |" — tier real segue `backend-exec` (`agents/backend-test-specialist.md:4`) e a proibição escrita segue viva, re-ancorada em `CLAUDE.md:115` ("Do not move a test agent to `repetitive`") — registro apontava `CLAUDE.md:87`.
- `ref-scoped-test-execution-bash-parallelism-section-outside-declared-canonical-scope` — **ainda reproduz** — `skills/shared/scoped-test-execution/SKILL.md:66-68` § "Run Independent Verification Commands in Parallel" — segue fora do escopo canônico (agora `CLAUDE.md:198`) e ausente da `description:` (`:3`, só "Run only tests covering the touched code"); re-ancorado de `:63-65`; skill em 93 linhas.
- `docs-sync-hooks-md-64-full-suite-guard-examples-predate-wrapper-detection` — **ainda reproduz** — `CLAUDE-md/hooks.md:78` "(e.g. `pytest` with no path/`-k`, `vendor/bin/phpunit` with no `--filter`)" — só runners nomeados; `rg -c -i wrapper` = 3 em `hooks.md`, nenhuma delas sobre a detecção de wrappers do guard (`02-graphify-hint`, hooks de usuário, self-heal); re-ancorado de `:64` para `:78`.
- `flow-prompt-auditoria-commit-step-contradicts-branch-rule` — **ainda reproduz** — `docs/reports/_prompt-auditoria.md:322` "After the two report files are written, commit **only** them and push to `main`." — contra a regra inviolável `:34` ("push apenas na branch designada da sessão"); medida registrada "são 8" arquivos → atual **7** (`docs/reports/2026-11-07/` tem 00–05 + `index.md`), i.e. a medida mudou mas o erro "two" segue 5 a mais do que o texto diz.
- `flow-background-process-discipline-monitor-no-availability-fallback` — **ainda reproduz** — `skills/architecture/orchestration/SKILL.md:277-279` "exactly one legitimate way to be watched: `Monitor`" sem cláusula de indisponibilidade; **piorou**: a cláusula da check 5 estava "seis linhas acima" no registro e hoje está em `:257`, a **22 linhas** de distância; skill em 414 linhas.
- `skill-token-efficiency-background-mgmt-contradicts-orchestration-discipline` — **ainda reproduz** — `skills/shared/token-efficiency/strategies.md:328-343` "Tell user once with the ID, then don't poll" + `TaskOutput(task_id=\"abc123\")` para shell de background — contradição intacta com § Background Process Discipline (`orchestration:271-288`); alcance registrado 18/18 vs 1 → atual **18 de 19** agentes para a versão errada e **2 de 19** (`software-architect`, `orchestrator`) para a certa.
- `agent-software-architect-inlines-spawn-integrity-4-5-no-availability-guard` — **ainda reproduz** — `agents/software-architect.md:89` "Before ending a turn with an unreturned spawn, call `ScheduleWakeup`" — segue reescrevendo a check 5 inteira, sem o guard de disponibilidade nem o fallback, que hoje vive em `orchestration:257` (registro apontava `:234-236`); mesma linha 89.
- `skill-orchestration-spawn-integrity-unreachable-from-devteam-commands` — **ainda reproduz (parcial)** — `commands/*.md` — a medida registrada ("zero dos 34 comandos") **melhorou**: hoje **4 de 42** comandos carregam/citam a skill (`sprint.md:8`, `release-qa.md:8`, `spec.md:52`, `architect.md:31`), com `sprint.md` e `release-qa.md` fazendo Load explícito; mas **26** comandos usam a Task tool e 22 deles seguem sem alcance aos checks 1–5 — o buraco estrutural persiste; roster de comandos piorou de 34 → **42**.
- `skill-orchestration-restates-scoped-test-execution-exception` — **ainda reproduz** — `skills/architecture/orchestration/SKILL.md:76-80` "never instruct a subagent to run the project's full test suite… Only relay a full-suite run when the user asked for one in this session" — reescreve a exceção que `CLAUDE.md:198` manda nunca restatar, duplicando `scoped-test-execution:18` § Orchestrator Rule; re-ancorado de `:68-70` para `:76-80`.
- `token-orchestration-skill-377-lines-138-conditional-path-only-no-references-dir` — **ainda reproduz / PIOROU** — `skills/architecture/orchestration/SKILL.md` — **377 → 414 linhas** (+37, +9,8%), sem `references/` (o diretório só tem `SKILL.md`); hoje empatada com `migration-v1-to-v2` (414) como maior skill de 1ª parte sem `references/`.
- `token-model-identity-32-of-58-lines-are-format-spec-and-examples-held-inline` — **ainda reproduz / PIOROU no alcance** — `skills/shared/model-identity/SKILL.md` — medida confirmada na mosca: § Format `:27-39` + § Examples `:40-58` = **32 de 58** linhas (idêntico ao registro, 58 linhas totais); alcance registrado 18 agentes → atual **19 de 19**.
- `token-project-context-restates-scoped-test-exception-table-read-by-18-agents` — **ainda reproduz / PIOROU no alcance** — `skills/shared/project-context/SKILL.md:281-290` "Do not work from this table alone" — tabela segue com **6 linhas** de dados (registro: 6) e a confissão re-ancorada de `:216` para `:290`; skill em 374 linhas; lida por **19 de 19** agentes (registro: 18 de 18), **12** dos quais sem carga própria de `scoped-test-execution` (só 7 a carregam) — registro dizia 11.
- `agent-security-specialist-cicd-checklist-github-actions-only-vocabulary` — **ainda reproduz / PIOROU** — `agents/security-specialist.md:80-86` § CI/CD Pipeline Security — os **6** itens seguem em vocabulário GitHub-only (`${{ github.event.issue.title }}`, `pull_request_target`, self-hosted runners) enquanto `:29` manda ler `.gitlab-ci.yml`/`bitbucket-pipelines.yml`; o harness passou de **4 → 5** skills `cicd-*` (`cicd-base/github/gitlab/bitbucket/jenkins`) — alvo tocado pelo delta (`agents/security-specialist.md` está em `/tmp/delta_files.txt`) e segue reproduzindo.
- `agent-database-specialist-rls-as-engine-neutral-multitenant-default-and-gate` — **ainda reproduz (metade resolvida)** — `agents/database-specialist.md:155` "All new tables have RLS enabled if this is a multi-tenant or Supabase project" — o item de "done" segue sem ressalva de engine para projeto multi-tenant não-PostgreSQL; a cascata de `:83` **foi corrigida** em `3d1152c4` ("RLS (default for PostgreSQL) → schema-per-tenant → database-per-tenant"); re-ancorado de `:84`/`:154` para `:83`/`:155`.
- `agent-reviewer-linter-config-three-divergent-ecosystem-incomplete-copies` — **ainda reproduz** — `agents/backend-reviewer.md:30` "(`phpcs.xml`, `pyproject.toml`, `.rubocop.yml`, `golangci.yml`)" — as 3 cópias divergentes seguem exatas no registro: `skills/shared/reviewer-base/SKILL.md:11` com **5** arquivos, `backend-reviewer:30` com **4** e sem `.eslintrc*`, `frontend-reviewer:31` com **3** JS-only (`.eslintrc`, `.prettierrc`, `stylelint.config.js`); nenhuma linha em Canonical Rule Homes.
- `agent-frontend-developer-testability-presumes-reactive-component-model` — **ainda reproduz** — `agents/frontend-developer.md:143-147` "Decouple data fetching from rendering (smart/dumb component pattern)" / "Avoid direct DOM manipulation — prefer reactive state" — pressuposto reativo intacto contra a `description:` server-rendered (Blade/Twig/ERB/Jinja) e o roteamento jQuery de `:72`; `## Client Rendering Model` formalizado em `:57` e ainda ignorado pela seção; re-ancorado de `:145-147`.
- `docs-sync-readme-command-table-omits-devteam-install-in-both-languages` — **ainda reproduz** — `README.md` / `README.pt-BR.md` — `grep -c "devteam:install"` = **0** em ambos (idêntico à re-medição de 2026-10-10); varredura comando-a-comando confirma `install` como o **único** ausente; tabela registrada "34 de 35" → atual **41 de 42** comandos; alvo tocado pelo delta (`README.md`, `README.pt-BR.md`) e segue reproduzindo.
- `ref-three-pointers-to-claude-md-hook-subscript-convention-moved-to-hooks-md` — **ainda reproduz (1 de 3 ponteiros)** — `scripts/hooks/stop.sh:58` "(see CLAUDE.md, \"Stop Hook Sub-script Convention\")" — a seção vive em `CLAUDE-md/hooks.md:21`; os outros dois ponteiros **foram corrigidos**: `CLAUDE-md/notifications.md` (o alvo nominal) não tem mais a string (`ad5b8b2`) e `scripts/hooks/pre-tool-use.sh` também não; medida registrada 3 ponteiros → atual **1**.
- `flow-learn-nudge-has-no-canonical-skill-home-three-inline-copies` — **ainda reproduz (parcial)** — `CLAUDE.md:483` "The canonical nudge implementation is `commands/merge.md` § Step 4" — corpo de comando segue designado como casa canônica contra "lives in exactly one skill", e `audit.md:180`, `pr.md:112`, `refactor.md:162` referenciam o caminho `commands/merge.md`, que não resolve em projeto instalado nem no Codex; as **3 cópias inline melhoraram** — hoje são referências, não cópias; re-ancorado (Learn Trigger Rule em `CLAUDE.md:481`).
- `flow-pr-md-default-branch-falls-back-to-global-config-then-literal-main` — **ainda reproduz (parcial)** — `commands/pr.md:30-33` — `gh repo view --json defaultBranchRef` **foi inserido como 1ª preferência** (melhoria), mas `git config init.defaultBranch` (`:31`) segue acima de `git remote show origin` (`:32`) e a cascata segue terminando em `|| echo "main")` (`:33`), literal proibido por `merge.md:28` e `worktree/SKILL.md:110`; alimenta `${DEFAULT_BRANCH}..HEAD` (`:50`, `:69`) e a base do PR (`:94`); re-ancorado de `:60-63`.
- `docs-sync-session-start-comment-cites-nonexistent-02b-full-suite-guard` — **ainda reproduz** — `scripts/hooks/session-start.sh:249` "pre-tool-use/02b-full-suite-guard.sh" — arquivo real é `02c-full-suite-guard.sh` e `02b-` é `02b-telemetry.sh`; linha exatamente onde a re-ancoragem de 2026-10-10 a deixou (`:249`); arquivo em 460 linhas.
- `docs-sync-touched-paths-lib-header-says-stop-only-after-02c-sources-it` — **ainda reproduz** — `scripts/hooks/lib/touched-paths.sh:2` "Shared touched-path detection for Stop sub-scripts." e `:12` "Not a hook. Sourced by stop.sh and by stop/02-, 02b-, 03-, 03b- sub-scripts." — segue sem mencionar o `source` de `02c-full-suite-guard.sh:16-17` (caminho PreToolUse, sem o cache `DEVTEAM_TOUCHED_PATHS` que só `stop.sh:50-52` exporta); linhas idênticas ao registro.
- `agent-qa-specialist-browser-foreground-rule-unsatisfiable-always-spawned` — **ainda reproduz / PIOROU** — `agents/qa-specialist.md:78` "Always run browser tests in the main/foreground agent, never delegated to a background subagent" — regra segue na camada errada; comandos que nomeiam `qa-specialist` passaram de **7 → 11** (`backend, frontend, fullstack, mobile, qa, refactor, relayout, release-qa, review, spec, sprint`); re-ancorado de `:85` para `:78`.
- `agent-unit-test-isolation-rule-mirrored-five-agents-no-canonical-home` — **ainda reproduz** — `agents/backend-test-specialist.md:94` "this is a hard rule, not a preference, enforced by the Hard rule in `skills/testing/test-pyramid/SKILL.md`" — **5** agentes com a paráfrase (registro: 5), `test-pyramid` **não tem linha alguma** na Canonical Rule Homes (`rg -n test-pyramid CLAUDE.md` = 0) e `test-pyramid` segue sem mencionar storage de browser (`rg -i localStorage|IndexedDB|cookie` = 0), enquanto `frontend-test-specialist.md:135` lhe atribui `localStorage`/`IndexedDB`/cookies.
- `skill-work-feedback-description-names-credentials-json-not-local-variant` — **ainda reproduz** — `skills/shared/work-feedback/SKILL.md:3` "gated by credentials.json." — o arquivo real segue `credentials.local.json`, usado no corpo em `:16` (registro: `:14`); medida registrada "única ocorrência da string no repo" → **não é mais única**: também em `scripts/lib/devteam/creds.py`, `tests/test_client_gate.py` e `skills/third-party/security-audit/ATTACK-CLASSES.md` — a desambiguação piorou.
- `agent-three-at-exactly-211-line-ceiling-zero-headroom-for-additions` — **ainda reproduz / mediu melhor** — `helpers/size-limits.sh:44` `AGENT_LIMIT=211`; o alvo nominal `agents/software-architect.md` caiu para **210** (não está mais no teto exato), mas a classe persiste: **1** agente em 211 exatos (`frontend-developer`) e **6** a ≤2 linhas (3×210, 3×209) — registro: 3 no teto + 5 a ≤3; roster de 18 → **19** agentes.
- `token-graphify-hint-3-git-forks-before-marker-early-exit-on-every-tool-call` — **ainda reproduz / mediu melhor** — `scripts/hooks/pre-tool-use/02-graphify-hint.sh:22-23` (`git rev-parse --show-toplevel`, `git rev-parse --git-common-dir`) segue **acima** do `[ -f "$MARKER" ] && exit 0` (`:28`) e do `case` de tool-name (`:35`); forks git registrados **3 → 2** (e `data-dirs.sh` agora é `source`, sem fork), e dois novos early-exits (`:18` plugin-settings, `:21` `graph.json`) entraram antes do bloco — mas num projeto com `graph.json` e sem o plugin, todo tool call ainda paga os 2 forks antes de qualquer filtro de tool.
- `token-output-format-third-copy-of-plan-format-42-lines-nine-load-sites` — **ainda reproduz / PIOROU no alcance** — `skills/shared/output-format/SKILL.md:162-203` § Plan Template — **42 linhas** confirmadas (`## Plan Template` em `:162`, `## Diagnostics` em `:205`), sentinela `Par.` divergente ainda em `:186`; sítios de carga registrados "7 agentes + 2 comandos" → atual **8 agentes + 3 comandos** (11, contra 9); skill em 221 linhas.
- `token-install-sh-second-unconditional-claude-md-injection-35-lines-every-session` — **ainda reproduz / mediu melhor** — `scripts/install.sh:992` "Step 8b: Inject Commit Rule into project CLAUDE.md" — os dois blocos gerenciados seguem incondicionais (guardados só por marcador) e sem gate que compare as cópias; medida registrada **35 linhas / ~1,97 KB** → atual **29 linhas / 1.851 B (~1,81 KB)** (Step 8 = 21 l/902 B, Step 8b = 8 l/949 B); 2 das 4 regras de 8b seguem restatando `conventional-commits/SKILL.md` (`:1008`, `:1011`); re-ancorado de `:862-886` para `:958-1022`.
- `token-work-feedback-opt-out-gate-lives-inside-the-71-line-skill-it-gates` — **ainda reproduz / PIOROU** — `skills/shared/work-feedback/SKILL.md:16` manda ler `credentials.local.json` para descobrir se a skill deve ser ignorada, depois que a skill inteira já foi carregada; medida registrada **71 linhas → atual 82** (+11, +15%); a proibição de mover o teste booleano ao chamador segue, re-ancorada em `CLAUDE.md:209` ("Never restate the gate check…") e em orchestration § Spawn Integrity check 6.

## Lote f1b_2 (itens 36–70)

- `auto-agent-lint-quiz-first-never-scans-commands-dir` — **ainda reproduz / PIOROU** — `helpers/agent-lint.sh:252-253` `check_quiz_first "$file" …` segue dentro de `check_agent()` (`:122`), e `check_agent` é chamado **só** por `for agent_file in agents/*.md` (`:585-588`); nenhum laço sobre `commands/*.md` chama a função (o único toque em comandos é o grep de `:424`, outro check); `CLAUDE.md:272` segue declarando a Quiz-first Rule dos comandos "enforced by `helpers/agent-lint.sh`"; comandos sem cobertura **35 → 42**; alvo tocado pelo delta (`helpers/agent-lint.sh`) e segue reproduzindo.
- `auto-adr-gap-check-dependency-signal-blind-to-staged-and-committed-changes` — **ainda reproduz** — `scripts/hooks/stop/03e-adr-gap-check.sh:67` `git -C "$REPO_ROOT" diff --unified=0 -- "$manifest"` — segue sem `--cached` e sem range, enquanto migration (`:75`) e provider-config (`:78`) leem `DEVTEAM_TOUCHED_PATHS` (que inclui staged e commits de hoje); a assimetria segue intacta — o caminho de "further dependency" (`:89`) usa `diff HEAD`, provando que o autor conhece a forma correta; re-ancorado de `:32` para `:67`; script em 117 linhas.
- `flow-review-command-writes-and-commits-while-documented-as-read-only` — **ainda reproduz (parcial)** — `commands/review.md:70` "execute the changes directly (edit files, create commits if files were modified)" contra `:35` "Do NOT review inline — always delegate" do mesmo arquivo; a 3ª evidência **sumiu**: `CLAUDE.md` não contém mais "read-only by design" (`rg -i read-only CLAUDE.md` só devolve `:221`, sobre `docs/source/`); re-ancorado de `:66` para `:70`.
- `flow-rule-and-sync-rules-listed-as-technical-writer-but-never-delegate` — **ainda reproduz (re-homed)** — `scripts/lib/commands.json` — o alvo nominal **perdeu** a evidência: `CLAUDE.md` não tem mais tabela "Agents invoked" (`rg -n "Agents invoked" CLAUDE.md` = 0, nem linhas `devteam:rule`/`sync-rules`); o defeito segue vivo em `commands.json`, que atribui `agent: technical-writer` a `rule` e `sync-rules`, `grep -c "Task tool"` = **0** em ambos os corpos, e a `_filler_agent_note` de `:7` segue enumerando **nove** linhas-filler sem incluir essas duas.
- `docs-sync-claude-md-effort-key-scope-vs-agent-effort-map` — **ainda reproduz** — `CLAUDE.md:92` "`effort:`, is present **only** on agents whose tier defines one in `tiers.json` (today: `repetitive`)" e `:101` "`backend-exec` | `sonnet` | none" — mas `tiers.json` § `agent_effort` dá `claude: low` a **5** agentes de `backend-exec`/`frontend` (`backend-test-specialist`, `frontend-test-specialist`, `database-specialist`, `devops-specialist`, `qa-specialist`), todos com `effort: low` no frontmatter (`:6`); medida registrada 5 agentes → atual **5** (inalterada); re-ancorado de `:64`/`:73-74` para `:92`/`:101`; alvo tocado pelo delta (`CLAUDE.md`) e segue reproduzindo.
- `docs-sync-docs-agents-md-worktree-asks-once-vs-preference-default` — **ainda reproduz** — `docs/agents.md:55` "Asks once whether to isolate work in a git worktree" e `docs/agents.pt-BR.md:55` ("Pergunta uma vez se deve isolar…") — linhas idênticas ao registro, contra `worktree_active: true` por default (`skills/shared/user-preferences/SKILL.md:65,100`).
- `ref-command-description-duplicated-frontmatter-vs-commands-json` — **ainda reproduz / PIOROU** — `scripts/lib/commands.json` — comparação automática frontmatter×`commands.json`: **42 de 42** descrições divergem (registro: as 35); o roster passou de **35 → 42** comandos e `check_command_roster` segue sem validar o campo `description`.
- `docs-sync-claude-md-coding-agents-list-omits-seo-specialist` — **ainda reproduz** — `CLAUDE.md:137` enumera oito coding agents e diz "It used to be inlined in all eight agents" — `grep -c "^## Worktree Isolation" agents/*.md` devolve **9** (`seo-specialist` incluído, mais `ui-ux-designer`); medida registrada 9 → atual **9** (inalterada); re-ancorado de `:109` para `:137`; alvo tocado pelo delta (`CLAUDE.md`) e segue reproduzindo.
- `docs-sync-readme-ptbr-agents-link-points-to-english-doc` — **ainda reproduz / PIOROU** — `README.pt-BR.md:285` "[Referência de Agentes](docs/agents.md)" contra `:15` "[Referência de Agentes](docs/agents.pt-BR.md)" — re-ancorado de `:141` para `:285`; links para docs EN em arquivos pt-BR: registrado **7 → atual 8** (`README.pt-BR.md:66,67,68,72,285`, `docs/harness.pt-BR.md:179`, `docs/installation.pt-BR.md:5` ×2); alvo tocado pelo delta (`README.pt-BR.md`) e segue reproduzindo. Nota lateral: `:15` e `:285` ainda dizem "18 agentes" (reais: 19).
- `agent-jira-detection-branch-naming-block-duplicated-no-canonical-home` — **ainda reproduz / mediu melhor** — `agents/database-specialist.md:164-172` § Jira Integration "Create the branch using the Jira naming pattern: `{type}/{issueKey}_short-description`" — bloco duplicado em **11** corpos (registro: 13), sem linha em Canonical Rule Homes (`grep -n jira CLAUDE.md` = 0); divergências intactas: placeholder `{issueKey}` nos agentes vs. `{taskId}` na skill (`skills/integrations/jira/SKILL.md:56,59`), tipos em subconjuntos incompatíveis por agente, e gate de aprovação — a skill (`:72`) exige "Propose branch name → on approval, create branch" enquanto **5** cópias mandam "Create the branch" (registro: 6).
- `agent-docs-sync-task-closure-missing-mobile-devops` — **ainda reproduz** — `agents/devops-specialist.md` e `agents/mobile-developer.md` — `grep -c docs-sync` = **0** em ambos, enquanto são coding agents por `CLAUDE.md:137` e a Task Closure Rule é obrigatória por `CLAUDE.md:189` ("Load docs-sync and reference the rule; write no closing directive of their own"); `devops-specialist:26` segue lendo `docs/devops/` sem regra de escrita de volta; re-ancorado de `:157` para `:189`; alvo tocado pelo delta (`agents/devops-specialist.md`) e segue reproduzindo.
- `agent-seo-specialist-outside-coding-agent-contract` — **ainda reproduz** — `agents/seo-specialist.md:34` `## Worktree Isolation` presente, mas o agente segue fora da enumeração de `CLAUDE.md:137` e **sem** `comments-policy` e **sem** `reuse-guidelines` (`rg -n` = 0 para ambos); re-ancorado de `:35` para `:34`.
- `token-status-and-version-inline-bash-scripts-paid-twice-per-invocation` — **ainda reproduz / PIOROU** — `commands/status.md` (130 linhas, **106** de bash) e `commands/version.md` (62 linhas, **41** de bash) — bash embutido medido registrado **132 → atual 147 linhas** (+11%), contra o padrão de uma linha de `commands/adr.md:23` (`bash .dev-team-agents/scripts/new-adr.sh "$ARGUMENTS"`), intacto.
- `token-checks-list-loads-all-three-provider-blocks-after-step-0-resolved-one` — **ainda reproduz / PIOROU muito** — `skills/shared/setup-health-check/references/checks-list.md` — medida registrada **668 linhas** (re-medida 2026-10-10: 681) → **atual 889 linhas / 55.495 B** (+33% sobre o registro, +31% sobre a re-medição); `SKILL.md:19` segue mandando "Load `references/checks-list.md`" inteiro, com os blocos `### For opencode provider` (`:230`) e `### For Codex provider` (`:251`) lidos sempre (40 linhas citam Codex, 10 citam opencode).
- `token-fix-patterns-517-lines-loaded-whole-to-apply-one-of-25-auto-fixes` — **ainda reproduz / PIOROU muito** — `skills/shared/setup-health-check/references/fix-patterns.md` — medida registrada **517 linhas / 22,6 KB** (re-medida 2026-10-10: 457, "mediu melhor") → **atual 665 linhas / 33.133 B (32,4 KB)**, **+45%** sobre a re-medição e +29% sobre o registro; padrões `##` passaram de 25 → **30**; ponteiros em `checks-list.md` passaram de 13 → **22**, dos quais **8** seguem sem nomear a seção; alvo tocado pelo delta e segue reproduzindo.
- `ref-readme-sync-gate-discovers-only-pt-br-suffix-blind-to-inverted-en-suffix-pair` — **ainda reproduz / PIOROU** — `.github/scripts/ci/02-readme-sync.sh:211` `find . -name '*.pt-BR.md'` e `:202` `en="${ptbr%.pt-BR.md}.md"` — o par invertido `docs/reports/metrics-last-20-days.md` (pt-BR) + `.en.md` (EN) segue escapando inteiro; tamanho registrado **594 → atual 737 linhas** em cada arquivo (+24%); o gate segue imprimindo OK para os **6** pares descobertos e ignorando o sétimo; re-ancorado de `:192`/`:183`; script em 218 linhas.
- `flow-prompt-auditoria-interactive-plan-gate-unsatisfiable-in-unattended-run` — **ainda reproduz** — `docs/reports/_prompt-auditoria.md:31-33` (regra **inviolável** 7: "aguarde aprovação antes de escrever") e `:7` ("Cole o bloco abaixo em uma sessão nova"), contra `git add` (`:342`) / `commit` / `git push … main` (`:354`) sem ponto de confirmação, com tratamento de erro escrito para execução desassistida; linhas da regra idênticas ao registro; bloco de commit/push re-ancorado de `:320-358` para `:320-365`; arquivo em 365 linhas.
- `token-archive-index-rotates-index-sections-only-report-directories-never-pruned` — **ainda reproduz / PIOROU** — `helpers/archive-index.sh:34` `INDEX_FILE="$REPORTS_DIR/_index.md"` e `scripts/hooks/stop/99b-archive-index.sh:2-3` repetem o escopo; os **16** diretórios `docs/reports/<YYYY-MM-DD>/` nunca são podados — o mais antigo (`2026-07-30`, >90 dias, além do corte do próprio script) segue no disco; medida registrada **1,0 MB em 36 dias** → **atual 1.880 KB (1,84 MB)** em `docs/reports/`, com `_index.md` em 144 KB; por pass 141 KB → **132 KB** (único número que mediu melhor).
- `docs-sync-telemetry-fresh-install-default-documented-true-while-install-sh-writes-false-without-consent` — **ainda reproduz** — `CLAUDE.md:312` "all default to `true` in a fresh file" e `skills/shared/user-preferences/SKILL.md:64,84` ("`\"telemetry\": true`" no schema / "All default to `true` in a fresh file") contra `scripts/install.sh:1207` `TELEMETRY_VALUE="false"`, `:1234` ("silence is not consent") e `:1240` ("No terminal available … so it is DISABLED") — a contradição segue viva no caminho não-interativo (`curl … | bash`); espelhos corretos: `CLAUDE-md/preferences.md:41`, `README.md:476`; re-ancorado de `CLAUDE.md:370`/`install.sh:1181` para `:312`/`:1207`; alvo tocado pelo delta (`CLAUDE.md`, `CLAUDE-md/preferences.md`, `skills/shared/user-preferences/SKILL.md`) e segue reproduzindo.
- `auto-no-gate-validates-claude-md-file-structure-tree-against-real-tree-four-recurrences-each-discarded-as-duplicate` — **ainda reproduz (instância obsoleta, classe viva)** — `helpers/` — `grep -rli "file structure\|file-structure" helpers/ .github/scripts/ scripts/hooks/` devolve **zero**: nenhum gate valida a árvore; a evidência pontual **ficou obsoleta** — `CLAUDE.md` não contém mais árvore alguma (`grep -c "├──\|└──" CLAUDE.md` = **0**; `:291` § File Structure só delega) e a árvore migrou para `CLAUDE-md/file-structure.md` (119 linhas), onde `hooks/lib/` aparece em `:87` **sem enumerar arquivos** — logo a divergência "três `└──` contra quatro arquivos" não existe mais (reais hoje: 14 arquivos em `scripts/hooks/lib/`).
- `auto-check-fingerprint-uniqueness-grep-admits-discarded-candidate-lines-as-slugs-inflating-count-and-silent-sed-fallthrough` — **ainda reproduz / PIOROU** — `helpers/check-fingerprint-uniqueness.sh:36-37` — `grep -E "^- \`[a-z][a-z0-9-]+"` segue casando linhas de `### Descartados por duplicação` (10 seções dessas no banco) e o `sed` segue repassando-as **inalteradas**; reproduzido: o gate imprime "✓ All **318** fingerprint slugs are unique", mas **5** dessas entradas são prosa, não slug (reais: 313) — medida registrada **237 reportados / 235 vivos (2 prosa) → atual 318 / 313 (5 prosa)**; mesmo defeito no comando da Fase 0 em `_prompt-auditoria.md:44`.
- `agent-mobile-developer-routing-rules-restates-five-runner-matrix` — **ainda reproduz** — `agents/mobile-developer.md:150` "(`jest`, `vitest`, `flutter test`, `xcodebuild test`, `./gradlew test`)" em § Routing Rules (`:145`) — a matriz de **5** runners congelada segue contradizendo `:172`, que manda derivar de `scoped-test-execution`; a § Runner Filters da skill (`:43`) resolve **11** stacks com filtros de escopo + override por script do projeto (medida registrada 11 → atual 11); re-ancorado de `:149`/`:171` para `:150`/`:172`.
- `agent-tracker-monoculture-jira-in-eleven-bodies-linear-reachable-from-one` — **ainda reproduz** — `agents/` — **11** agentes com `## Jira Integration` (registro: 11, inalterado) e **5** prescrevendo o padrão de branch do Jira em seção de comportamento (registro: 6); `skills/integrations/linear/SKILL.md` segue alcançável de **um** único ponto, `agents/product-analyst.md:191` (registro: `:177`); `orphan-skill-scan` segue satisfeito pela referência única; alvo tocado pelo delta (`agents/product-analyst.md`) e segue reproduzindo.
- `agent-seo-specialist-foundational-rule-names-next-seo-astro-seo` — **ainda reproduz** — `agents/seo-specialist.md:27` "(built-in sitemap generation, `next-seo`, `astro-seo`, etc.) before proposing a new dependency" — § Foundational Rule em `:19`; linha idêntica ao registro (`:27`).
- `agent-code-reviewer-output-template-pins-file-js-six-placeholders` — **ainda reproduz** — `agents/code-reviewer.md:145,149,153,157,160,163` `` `file.js:42` `` etc. — **6** placeholders `file.js` (registro: 6; `grep -c` = 6), inclusive no caminho `Review type: Backend`, enquanto `backend-reviewer.md:166-186` roda `.go/.php/.py/.rb/.ts` de propósito; § Review Output Format em `:132`; re-ancorado de `:144,148` para `:145,149`.
- `auto-orphan-skill-scan-user-invocable-parser-overruns-into-next-table` — **ainda reproduz / PIOROU** — `helpers/orphan-skill-scan.sh:37` `awk '…found && /^### /{found=0}'` — segue sem casar `#### User-Invocable Commands` (`CLAUDE.md:268`); reproduzido: a janela **começa em `CLAUDE.md:164`** (primeira menção à tabela, dentro da prosa de third-party), atravessa a tabela Canonical Rule Homes inteira e só fecha no `### ` de `:276`, somando 57 linhas, e o parser captura **6** nomes onde a tabela real tem **4** — `current-context` e `spawn-classifier` seguem isentos da detecção de órfãos; medida registrada **5 em vez de 3 → atual 6 em vez de 4**.
- `ref-monitoring-loki-config-reference-unreachable-no-gate-covers-references-dir` — **ainda reproduz** — `skills/devops/monitoring/references/loki-config.md` — **83 linhas** (idêntico ao registro); `rg -n 'loki-config'` fora de `docs/reports/` devolve só o próprio arquivo — nenhum ponteiro em `skills/devops/monitoring/SKILL.md`; `helpers/orphan-skill-scan.sh:121-122` segue pulando `references/` por construção (`[[ "$rel_path" == *"/references/"* ]] && continue`); re-ancorado de `:122-123` para `:121-122`.
- `docs-sync-providers-md-zen-premium-column-mixes-namespaces-pinned-ids` — **ainda reproduz** — `docs/providers.md:318-321` sugerem `opencode/claude-opus-4-7`, `opencode/gpt-5.6-terra` e `opencode/gpt-5.6-luna` — ids Codex com prefixo `opencode/` trocado, mais o id pinado que `:51` segue declarando aposentado ("It previously held pinned ids (`claude-opus-4-7`, `claude-sonnet-4-6`) and had drifted a generation behind"); re-ancorado de `:215-218` para `:318-321`.
- `auto-99b-archive-index-writes-daily-stamp-even-when-rotation-failed` — **ainda reproduz** — `scripts/hooks/stop/99b-archive-index.sh:47` `OUTPUT="$(bash "$SCRIPT" 2>&1)" || OUTPUT=""` (destrói exit code e stderr) e `:49-50` gravam `$TODAY` no `.last-archive-index` incondicionalmente, com o gate diário de `:37-41` bloqueando nova tentativa por 24 h; re-ancorado de `:44`/`:46-47`/`:33`; script em 62 linhas.
- `agent-project-context-delegation-claims-recent-git-log-absent-from-skill-18x` — **ainda reproduz / PIOROU** — `skills/shared/project-context/SKILL.md` — `grep -c 'recent git log' agents/*.md` → **19 de 19** agentes afirmam que a skill cobre histórico git (registro: 18 de 18), mas `grep -ci 'git log'` na skill caiu de **1 → 0** (nenhuma menção sobreviveu) e a § Context Loading Order passou de 11 → **12** itens, nenhum de histórico; alvo tocado pelo delta (`skills/shared/project-context/SKILL.md`) e segue reproduzindo — piorou nas duas pontas.
- `agent-three-reviewers-review-output-template-triplicated-comments-slot-lost` — **ainda reproduz / PIOROU** — `agents/code-reviewer.md:132` § Review Output Format — os três reviewers delegam a `pr-review` (`code-reviewer:124`, `backend-reviewer:159`, `frontend-reviewer:151`) e em seguida inlinam o template: ~**39 / 36 / 38** linhas (registro: ~30 cada); `### Comments` segue **só** no router (`:155`, linha idêntica ao registro) e ausente dos dois especialistas que de fato executam o review; divergência adicional: `### SonarQube` agora está nos **três** (registro: só nos especialistas).
- `skill-git-workflow-type-prefixes-vs-worktree-context-title-branch-naming` — **ainda reproduz** — `skills/shared/git-workflow/SKILL.md:24-33` § Branch Naming (`feature/*`, `fix/*`, `hotfix/*`, `release/*`, `chore/*`) contra `skills/shared/worktree/SKILL.md:60-67` § Name Format (`<context>/<brief-title>`); nenhuma menciona a outra (`grep -c git-workflow` em worktree = **0**); a colisão segue vazada para `skills/shared/worktree/references/branch-flow.md:198-199`, com `chore` e `fix` na coluna **Domain**; linhas idênticas ao registro.
- `skill-three-security-skills-hold-divergent-ecosystem-scanner-tables` — **ainda reproduz** — `skills/security/dependency-audit/SKILL.md:39-41,58-59` — a tabela ecossistema→scanner segue em **três** skills (`dependency-audit`, `dependency-vulnerabilities`, `sast-pipeline`), todas carregáveis na mesma tarefa por `agents/security-specialist.md:46,47,48`; divergências intactas: PHP presente em `dependency-audit:40` (`composer audit`) e em `sast-pipeline:16` (PHPCS), **ausente** de `dependency-vulnerabilities`; Trivy em **três** formas (`trivy config .`/`trivy image` em dependency-audit, `trivy image <image>` em dependency-vulnerabilities, `trivy fs .` em supply-chain:73).
- `skill-test-strategy-inlines-test-pyramid-section-both-loaded-together` — **ainda reproduz** — `skills/testing/test-strategy/SKILL.md:20-55` § Test Pyramid — **36 linhas** (idêntico ao registro) duplicando a skill `test-pyramid` (167 linhas), carregada na mesma frase por ambos os test-specialists (`backend-test-specialist:72`, `frontend-test-specialist:73`); `:43` segue autorizando "May use real database (test DB), real filesystem" contra a Hard rule que 5 agentes citam como `[BLOCKING]`; re-ancorado de `:44` para `:43`; test-strategy em 132 linhas.
- `skill-design-system-md-two-divergent-schemas-docs-sync-vs-design-system-audit` — **ainda reproduz (mitigação parcial)** — `skills/design/design-system-audit/SKILL.md:104` aponta o esquema canônico de `docs-sync` (hoje `skills/shared/docs-sync/SKILL.md:122`, 5 seções, com `<!-- last-updated -->` em `docs-sync:21`) e `:106-140` segue emitindo um concorrente de **7** seções (`Status`, `Color Tokens`, `Typography`, `Spacing`, `Components`, `Patterns to Follow`, `Patterns to Avoid`) sem o marcador e com três nomes divergentes; a linha de prosa que desautoriza o próprio conteúdo **continua sendo o único mecanismo** ("Condense to that schema…; do not emit every sub-section below verbatim") — re-ancorado de `:108-135` para `:106-140`.

---

## Resumo — FASE 1b metade 1

**70 de 70 verificados.** `ainda reproduz` **70** · 🟢 Resolved **0** · ⚰️ Obsoleto **0**.

Nenhum achado foi integralmente corrigido de passagem e nenhum alvo deixou de existir. **9** itens
tiveram *sub-evidência* resolvida (continuam abertos por outra perna):
`ref-three-pointers-to-claude-md-hook-subscript-convention-moved-to-hooks-md` (3→1 ponteiro; o alvo
nominal `CLAUDE-md/notifications.md` foi limpo em `ad5b8b2`) ·
`agent-database-specialist-rls-as-engine-neutral-multitenant-default-and-gate` (cascata corrigida em
`3d1152c4`; item de "done" segue) · `skill-orchestration-spawn-integrity-unreachable-from-devteam-commands`
(0→4 comandos carregam a skill) · `flow-learn-nudge-has-no-canonical-skill-home-three-inline-copies`
(cópias inline → referências) · `flow-pr-md-default-branch-falls-back-to-global-config-then-literal-main`
(`gh repo view` inserido como 1ª preferência) · `flow-review-command-writes-and-commits-while-documented-as-read-only`
(`CLAUDE.md` não diz mais "read-only by design") · `flow-rule-and-sync-rules-listed-as-technical-writer-but-never-delegate`
(evidência saiu de `CLAUDE.md`, vive em `commands.json`) ·
`auto-no-gate-validates-claude-md-file-structure-tree-against-real-tree-*` (a árvore saiu de `CLAUDE.md`;
a classe segue sem gate) · `flow-prompt-auditoria-commit-step-contradicts-branch-rule` (8→7 arquivos de report).

### Fingerprints que mediram pior (registrado → atual)

| Fingerprint | Registrado → atual |
|---|---|
| `token-checks-list-loads-all-three-provider-blocks-after-step-0-resolved-one` | 668 (681 em 10-10) → **889 linhas** |
| `token-fix-patterns-517-lines-loaded-whole-to-apply-one-of-25-auto-fixes` | 517 l / 22,6 KB (457 em 10-10) → **665 l / 32,4 KB**; padrões 25 → 30; ponteiros 13 → 22 |
| `token-archive-index-rotates-index-sections-only-report-directories-never-pruned` | 1,0 MB → **1,84 MB**; 0 dirs podados de **16** |
| `auto-check-fingerprint-uniqueness-grep-admits-discarded-candidate-lines-as-slugs-*` | 237/235 (2 prosa) → **318/313 (5 prosa)** |
| `ref-readme-sync-gate-discovers-only-pt-br-suffix-blind-to-inverted-en-suffix-pair` | par invertido 594 → **737 linhas** |
| `token-orchestration-skill-377-lines-138-conditional-path-only-no-references-dir` | 377 → **414 linhas** |
| `token-status-and-version-inline-bash-scripts-paid-twice-per-invocation` | 132 → **147 linhas de bash** |
| `token-work-feedback-opt-out-gate-lives-inside-the-71-line-skill-it-gates` | 71 → **82 linhas** |
| `ref-command-description-duplicated-frontmatter-vs-commands-json` | 35 → **42 descrições divergentes** |
| `auto-agent-lint-quiz-first-never-scans-commands-dir` | 35 → **42 comandos sem cobertura** |
| `agent-qa-specialist-browser-foreground-rule-unsatisfiable-always-spawned` | 7 → **11 comandos que spawnam** |
| `agent-project-context-delegation-claims-recent-git-log-absent-from-skill-18x` | 18/18 → **19/19 agentes**; menções na skill 1 → **0**; ordem 11 → 12 itens |
| `token-project-context-restates-scoped-test-exception-table-read-by-18-agents` | 18 → **19 leitores**; 11 → **12** sem carga própria |
| `token-model-identity-32-of-58-lines-are-format-spec-and-examples-held-inline` | 18 → **19 agentes** (32/58 inalterado) |
| `token-output-format-third-copy-of-plan-format-42-lines-nine-load-sites` | 9 → **11 sítios de carga** |
| `agent-security-specialist-cicd-checklist-github-actions-only-vocabulary` | 4 → **5 skills `cicd-*`** |
| `auto-orphan-skill-scan-user-invocable-parser-overruns-into-next-table` | 5 em vez de 3 → **6 em vez de 4**; janela agora de `:164` a `:276` |
| `agent-three-reviewers-review-output-template-triplicated-comments-slot-lost` | ~30 → **~36/38/39 linhas** por cópia |
| `docs-sync-readme-ptbr-agents-link-points-to-english-doc` | 7 → **8 links para docs EN** |
| `flow-background-process-discipline-monitor-no-availability-fallback` | cláusula a 6 linhas → **22 linhas** de distância |
| `skill-work-feedback-description-names-credentials-json-not-local-variant` | "única ocorrência" → **4 ocorrências** de `credentials.json` |
| `skill-orchestration-spawn-integrity-unreachable-from-devteam-commands` | roster 34 → **42 comandos** (cobertura 0 → 4) |

### Mediram melhor

`token-install-sh-second-unconditional-claude-md-injection-35-lines-every-session` (35 l/1,97 KB → 29 l/1,81 KB) ·
`agent-jira-detection-branch-naming-block-duplicated-no-canonical-home` (13 → 11 corpos; 6 → 5 cópias "create") ·
`token-graphify-hint-3-git-forks-before-marker-early-exit-on-every-tool-call` (3 → 2 forks git) ·
`agent-three-at-exactly-211-line-ceiling-zero-headroom-for-additions` (3 → 1 agente no teto exato) ·
`ref-three-pointers-to-claude-md-hook-subscript-convention-moved-to-hooks-md` (3 → 1 ponteiro) ·
`token-archive-index-*` (141 → 132 KB por pass, único número em queda nesse item).

### Alvos tocados pelo delta

**20 de 70** alvos aparecem em `/tmp/delta_files.txt` — e **20 de 20 seguem reproduzindo**:
`skills/architecture/orchestration/SKILL.md` (3 itens), `skills/shared/project-context/SKILL.md` (2),
`CLAUDE.md` (4), `commands/*.md` (1), `agents/security-specialist.md` (1), `README.md` (1),
`README.pt-BR.md` (1), `skills/shared/output-format/SKILL.md` (1), `helpers/agent-lint.sh` (1),
`agents/devops-specialist.md` (1), `agents/product-analyst.md` (1),
`skills/shared/setup-health-check/references/checks-list.md` (1) e `.../fix-patterns.md` (1).
Dos 16 commits do delta, nenhum fechou um achado aberto desta metade; os que tocaram alvos
(`checks-list.md`, `fix-patterns.md`, `project-context`, `orchestration`) **aumentaram** a medida
registrada em todos os quatro.


## Lote /tmp/f1b_3.txt (35 itens)

- `token-151-skills-flat-symlinked-into-claude-skills-index-12751-chars-per-context` — **ainda reproduz** — `scripts/install.sh:518-527` "symlinkam 151 das 152 skills para `.claude/skills/`, 12.751 chars de índice" — loop de symlink intacto (`ln -s` em `:526`), `.claude/skills/` tem 168 links; índice `name:`+`description:` **piorou: 12.751 B registrado (155 skills em 2026-10-10) → 19.298 B / 168 skills agora**
- `token-current-context-cache-block-36-of-105-lines-fails-own-scope-rule` — **ainda reproduz** — `skills/shared/current-context/SKILL.md:58-93` "34% do arquivo é implementação bash de cache" — 36 de 105 linhas (medida estável); no hit (`:81`) o payload segue sem as duas listas da Scope Rule (`:21`), e o TTL divergente persiste: skill 1800s vs espelho `CLAUDE-md/user-data.md:36` 300s (registrado em `:17`); 36 comandos carregam a skill
- `token-graphify-setup-os-detection-30-lines-diverges-from-tool-installers` — **ainda reproduz** — `skills/devops/graphify-setup/SKILL.md:27-36` "duplicam a detecção de SO num passo que já delega a /devteam:install" — Step 1 ainda inlina `uname -s` + `wsl --status` e barra Windows sem WSL, enquanto `skills/devops/tool-installers/SKILL.md:12` atende `winget` nativamente; delegação agora em `:44` (registrado `:64`); bloco encurtou 30 → 10 linhas
- `token-telemetry-consent-guard-reforks-python3-above-the-fast-path` — **ainda reproduz** — `scripts/hooks/stop/05-telemetry.sh:54` "_telemetry_enabled acima do fast-path" — guard em `:54` (registrado `:31`) continua acima do fast-path `DEVTEAM_NO_CHANGES` em `:64-68` (registrado `:39`); arquivo 90 linhas
- `docs-sync-user-data-keep-root-omits-plugins-and-names-wrong-repo-only-skill` — **ainda reproduz** — `CLAUDE-md/user-data.md:110` "`KEEP_ROOT` é `agents scripts skills templates commands`" — `scripts/install.sh:400` é `(agents scripts skills templates commands plugins)`; `:104` (registrado `:99`) ainda nomeia `release-prep` como repo-only, mas existem `.claude/skills/release-prep` (link para a distribuída) e `.claude/skills/repo-release-prep`; tabela de exclusões segue sem linha para `tests/`, `infra/`, `packaging/`, `app/` (0 linhas)
- `ref-relayout-quality-skills-list-cites-seven-nonexistent-shared-paths` — **ainda reproduz** — `commands/relayout.md:35` "lista 8 skills em `skills/shared/`" — verificado um a um: 7 de 8 inexistentes em `skills/shared/` (`frontend-design`, `design-system-audit`, `mobile-design` → `skills/design/`; `frontend-code-quality`, `component-patterns`, `css-quality`, `accessibility-patterns` → `skills/architecture/`); só `frontend-done-checklist` existe
- `ref-orphan-skill-scan-blind-to-directory-form-skill-refs` — **ainda reproduz** — `helpers/orphan-skill-scan.sh:72` "casa só `skills/…/SKILL.md`" — linha idêntica (`grep -oE 'skills/[a-zA-Z0-9/_-]+/SKILL\.md'`), nenhuma fase lê a forma de diretório; os 7 caminhos mortos de `relayout.md:35` estão exatamente nessa forma e seguem invisíveis; script cresceu para 258 linhas
- `docs-sync-preferences-sync-lint-two-of-five-mirrors-key-presence-only` — **ainda reproduz** — `helpers/preferences-sync-lint.sh:28-31` "`MIRRORS` com 2 dos 5 espelhos" — `MIRRORS` segue com 2 entradas (`CLAUDE-md/preferences.md`, `skills/shared/user-preferences/SKILL.md`); `CLAUDE.md:304-308` lista 4 linhas / 5 arquivos de espelho; teste de presença de chave em `:60` (registrado `:58`); heredoc do `install.sh` e par `docs/user-preferences*.md` seguem fora do gate
- `ref-hooks-md-library-rows-omit-data-dirs-sh-sourced-by-ten-scripts` — **ainda reproduz** — `CLAUDE-md/hooks.md` "`data-dirs.sh` é o único sem linha Shared library" — `grep -n data-dirs CLAUDE-md/hooks.md` → **0 ocorrências**; medidas **pioraram**: `scripts/hooks/lib/` 10 → **14 arquivos**, fan-in de `data-dirs.sh` 10 → **12 scripts**
- `flow-install-provider-gate-fallback-fails-open-without-gate-lib` — **ainda reproduz** — `scripts/install-provider.sh:114-127` "fallback de gate de conta sem `else`" — o `else` foi adicionado (`:125`) mas só imprime "account check skipped" e **segue em frente**: sem gate lib e sem CLI o release em `enforce` ainda se comporta como `allow`, e `:121` continua decidindo por `grep -q '"gate_mode": *"enforce"'` sobre o corpo JSON (crash/exit sem corpo ou JSON reformatado → fail-open), contra `scripts/lib/auth-gate.sh:8-16` (SR-42)
- `flow-02c-double-dash-counted-as-scope-lets-npm-full-suite-through` — **ainda reproduz** — `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:57` "`has_scope` aceita `--` como seletor" — `--` continua no primeiro `case` de aceitação (`has_scope()` em `:53`), então `npm test --` e `npm test -- --coverage` seguem passando sem nudge
- `auto-review-agents-regex-duplicated-in-two-task-board-hooks-no-drift-gate` — **ainda reproduz** — `scripts/hooks/pre-tool-use/04-task-board.sh:34` "`:33` e `post-tool-use/01-task-board.sh:32` repetem `REVIEW_TYPE_RE`" — **piorou: 2 → 4 cópias** (`pre-tool-use/04:34`, `post-tool-use/01:34`, `subagent-stop/01:12`, `subagent-start/01:14`); `grep -rn REVIEW_TYPE_RE tests` segue vazio e `agent-lint.sh:117` valida só `REVIEW_RESULT_AGENTS`
- `flow-update-md-v3-step-0-drops-documented-health-check-and-yes-flags` — **ainda reproduz** — `commands/update.md:38` "Passo 0 mapeia só `<version tag>`, `--no`, `--enable-auto`, `--disable-auto`" — Step 0 (`:36-38`) idêntico e manda "stop"; `--run-health-check`/`--skip-health-check` só em `:172-174` e `--yes` só em `:133`, ambos no caminho v2
- `agent-security-specialist-outside-review-result-set-task-board-blind-to-findings` — **ainda reproduz** — `agents/security-specialist.md:182` "não consta de `REVIEW_RESULT_AGENTS` nem pede o marcador" — `commands/review.md:42` ainda o spawna; ausente de `helpers/agent-lint.sh:117`, de `review_triggers.py:17`, dos 4 hooks de task board e de `docs/specs/task-board.md:343`; `## Before You Finish` (`:182`, arquivo com 184 linhas) sem `<!-- review-result: findings=N -->`; **tocado pelo delta** e segue reproduzindo
- `agent-review-agent-roster-hardcoded-in-five-places-no-canonical-home` — **ainda reproduz** — `scripts/lib/devteam/review_triggers.py:17` "a lista dos quatro revisores vive em cinco lugares" — **piorou: 5 → 7 casas** (4 regexes bash em `pre-tool-use/04`, `post-tool-use/01`, `subagent-stop/01`, `subagent-start/01`, + tupla `review_triggers.py:17`, + `agent-lint.sh:117`, + `docs/specs/task-board.md:343`); nenhum gate cruza as sete e *Canonical Rule Homes* (`CLAUDE.md:183`) segue sem linha para o roster
- `agent-no-claude-attribution-restated-in-five-agents-frontend-dev-has-no-commit-rule` — **ainda reproduz** — `agents/frontend-developer.md` "`grep -n commit agents/frontend-developer.md` sai vazio" — re-medido: `grep -ci commit` → **0** no frontend-developer (211 linhas, no teto `AGENT_LIMIT=211`), contra 3/4/7/3/2 nos cinco que reescrevem a regra cuja casa é `conventional-commits/SKILL.md:48-52`; os dois agentes "em 211/211 linhas" estão agora em 209/209 (`devops-specialist`, `technical-writer`)
- `token-pretooluse-04-task-board-13-forks-before-marker-exit-every-tool-call` — **ainda reproduz** — `scripts/hooks/pre-tool-use/04-task-board.sh:97-99` "source task-board.sh + init antes do `[ -f marker ] && exit 0`" — `. task-board.sh` (`:97`) + `devteam_task_board_init` (`:99`) seguem **acima** do teste de marcador em `:103`; `ANY_TOOL_RE` em `:39` (registrado `:49`) ainda casa quase tudo e a promessa "no python is forked" está em `:22-23`; forks/ms não re-medidos (sem strace no ambiente), estrutura idêntica
- `token-python-sh-uname-forked-twice-per-source-uncached-on-linux-macos` — **ainda reproduz** — `scripts/lib/python.sh:27` "`$(uname -s)` dentro de `_dta_is_windows`, chamada 2× por source" — **piorou: 2 → 3 call sites** (`:75`, `:100`, `:113`); `$OSTYPE` continua sem uso e nada é exportado no Linux/macOS
- `token-hook-dispatchers-basename-dirname-forks-per-subscript-iteration` — **ainda reproduz** — `scripts/hooks/pre-tool-use.sh:35` "`$(basename "$script")` uma vez por arquivo do glob" — 4 usos de `basename` (`:35,:37,:41,:43`) + 2 `dirname` (`:13,:17`) num dispatcher de 51 linhas; **piorou: 7 → 9 entradas no glob** `pre-tool-use/`, e `_disabled-01-check-updates.sh` (89 linhas, morto) continua lá custando 1 `basename` por chamada
- `token-plan-mode-execution-strategy-gate-duplicates-orchestration-loaded-by-26` — **ainda reproduz** — `skills/shared/plan-mode/SKILL.md:185-240` "56 linhas, 3.202 B de 14.853 B" — bloco § Execution Strategy Gate re-medido: **exatamente 56 linhas / 3.202 B** (estável), mas o arquivo **piorou de 14.853 B → 17.111 B (269 linhas)** e os carregadores **de 26 → 32** (8 agentes + 24 comandos); duplicata em `skills/architecture/orchestration/SKILL.md:15` intacta e as duas casas canônicas persistem (`interaction-patterns:234`, `software-architect.md:69`); **tocado pelo delta**
- `token-pretooluse-02c-sed-tr-head-forks-before-runner-gate-on-every-bash-call` — **ainda reproduz** — `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:32` "`printf|sed|head` e `tr|sed` sem teste prévio de runner" — `:32` (registrado `:30`) e `:188` (registrado `:182`) idênticos, nenhum teste por substring de runner antes; arquivo 220 linhas; ms não re-medidos
- `token-02b-telemetry-resolves-state-for-every-bash-call-needs-devteam-substring` — **ainda reproduz** — `scripts/hooks/pre-tool-use/02b-telemetry.sh:36-39` "aceita `Bash` e resolve state antes de conferir `/devteam:`" — ordem intacta: aceita `Bash` em `:36`, resolve `MAIN_REPO_ROOT`/state-dir/prefs em `:50-58`, consent guard em `:75`, e só em `:84-92` procura `/devteam:` no payload (registrado `:80-90`); arquivo 99 linhas
- `auto-ipc-trusted-sender-rule-has-no-gate-only-a-wiki-note-to-grep` — **ainda reproduz** — `app/src/main/security.ts:244` "nenhum passo de `05-app.sh` lê `ipcMain.handle`" — `grep -n ipcMain .github/scripts/ci/05-app.sh` → **vazio**; a única proteção segue sendo o *Gotchas* de `docs/wiki/electron/ipc-channels-need-the-trusted-sender-check.md` ("found by grep only | 2026-09-30"); **piorou: 4 → 5 casas de registro** (`ipc.ts:406`, `notificationIpc.ts:29`, `taskBoardIpc.ts:75`, `accountIpc.ts`, + nova `taskGraphIpc.ts:104`), 6 `ipcMain.handle` no total
- `auto-stamp-code-signed-cjs-outside-every-js-gate-in-the-tree` — **ainda reproduz** — `.github/scripts/release/stamp-code-signed.cjs:21` "único arquivo JS/TS da árvore sem gate algum" — `eslint .` segue com `cwd = app/` (`app/package.json:15`), `SHELLCHECK_TARGETS` (`01-lint.sh:143`) só `*.sh`, `03-python.sh` só python; `replace` ainda ancorado na linha literal `export const CODE_SIGNED = false;` que vive em `app/src/main/build-info.ts:14`; executado em `release.yml:700` e `:758` (registrado `:768,:835`); **piorou: 1 → 3 `.cjs` sem gate** (somam-se `skills/third-party/security-audit/validate-{findings,coverage-ledger}.cjs`)
- `token-wiki-retrieval-index-13-7kb-read-whole-by-18-agents-with-no-cap` — **ainda reproduz** — `skills/shared/project-context/SKILL.md:170` "`docs/wiki/README.md` tem 13.715 B / 51 linhas … sem teto" — **piorou muito: 13.715 B / 51 linhas → 27.768 B / 107 linhas** (1.757 B / 6 linhas em 2026-09-27: **15,8× em 48 dias**), ~260 B/linha, ainda sem teto; a instrução de **ler** o índice está em `:170` com a justificativa "context cost stays flat as the wiki grows" e o grep em `:131`; carregadores **18 → 19 agentes**; **tocado pelo delta**
- `docs-sync-preferences-retire-checklist-restates-mirror-list-omits-docs-pair-and-invents-readme-row` — **ainda reproduz** — `CLAUDE-md/preferences.md:48` "remove de todos os espelhos … `README.md` worktree table if listed" — a lista reescrita segue omitindo `docs/user-preferences.md` / `.pt-BR.md` (linhas reais em `CLAUDE.md:308`) e inventando a tabela de worktree nos READMEs (`grep -c worktree_active README*.md` → **0 e 0**); linha migrou `:42 → :48`; sem gate; **tocado pelo delta** e segue reproduzindo
- `docs-sync-hooks-md-warn-once-library-row-omits-03f-spec-lint-contradicting-line-41` — **ainda reproduz** — `CLAUDE-md/hooks.md:142` "diz dois onde são três" — **piorou: diz três onde são cinco**; `:142` (registrado `:121`) nomeia `03c`, `03e`, `03h`, enquanto `grep -ln warn-once scripts/hooks/stop/*.sh` devolve **5** (`03c`, `03e`, `03f`, `03g`, `03h`) e `:43` do mesmo arquivo nomeia os cinco
- `auto-03f-spec-lint-warn-signature-omits-worktree-root-silences-sibling-worktrees` — **ainda reproduz** — `scripts/hooks/stop/03f-spec-lint.sh:73` "assina o aviso só com a saída do lint" — `SIGNATURE="$(printf '%s\n' "$OUTPUT" | git hash-object --stdin)"` em `:73` (registrado `:58`), sem `$REPO_ROOT`, contra o irmão `03c-reuse-lint.sh:63` que o inclui com o comentário explicando o risco (`:57-58`); marcador compartilhado via `lib/warn-once.sh`
- `auto-warn-once-reset-never-called-by-03e-and-03f-cleared-warning-never-returns` — **ainda reproduz** — `scripts/hooks/stop/03f-spec-lint.sh` "uma única chamada de `warn_once_reset` (`03c:46`)" — `grep -rn warn_once_reset scripts/hooks/` → 1 chamada, agora em `03c-reuse-lint.sh:53`; **piorou**: saídas limpas sem reset em `03f` **4 → 8** (`:13,:16,:33,:36,:38,:44,:46,:50`) e em `03e` **4 → 5** (`:23,:25,:33,:57,:117`), e os consumidores de `warn_once` subiram a 5 com um só reset
- `flow-spec-command-step6-item5-inlined-into-item4-breaking-its-own-cross-reference` — **ainda reproduz** — `commands/spec.md:53` "4. … in one `AskUserQuestion`. 5. Session summary and hand-off" — linha única idêntica em `:53`, e o "skip items 4 and 5" segue em `:55` apontando para um item que não renderiza
- `skill-spec-gate-touches-accepts-database-layer-with-no-test-author-in-any-track` — **ainda reproduz** — `skills/shared/spec-gate/SKILL.md:27` "`database` é layer de primeira classe em `touches`, mas as listas de autor de teste cobrem três tracks" — `:27` e `scripts/lib/spec_lint.py:43` (`LAYERS`) seguem com `database`; as listas de autor estão em `:140` e `:146` ("backend, frontend, and mobile alike") — registradas em `:126`/`:132` — mais `commands/spec.md`; `check_coverage` agora em `spec_lint.py:490` (registrado `:282-293`); **tocado pelo delta** e segue reproduzindo
- `token-spec-gate-17kb-loaded-whole-by-six-execution-agents-that-scope-two-sections` — **ainda reproduz** — `skills/shared/spec-gate/SKILL.md` "17.463 B / 248 linhas, 2ª maior skill de `skills/shared/`, sem `references/`" — **piorou: 19.338 B / 264 linhas**; diretório segue só com `SKILL.md` (sem `references/`); deixou de ser a 2ª e é a **3ª** maior de `skills/shared/` (project-context 25.686 B, interaction-patterns 23.833 B); § Scope Lock (`:108`), § Test-First Derivation (`:136`) e § Traceability (`:150`) seguem como os únicos escopos reais; **tocado pelo delta**
- `agent-product-analyst-step6-gates-isolated-infra-on-docker-and-inlines-compose-probe` — **ainda reproduz** — `agents/product-analyst.md:163-167` "condiciona o isolamento a Docker e inlina `ls docker-compose.yml …`" — bloco migrou `:151-155 → :163-167` sob § Step 6 (`:137`) e continua idêntico, com o `ls docker-compose.yml docker-compose.yaml compose.yml compose.yaml` inline; `agents/setup-assistant.md:66` segue demonstrando a delegação a `stack-detection` "so no agent re-probes"; **tocado pelo delta** e segue reproduzindo
- `gov-interaction-mode-key-ungated-and-undocumented-outside-commands-json` — **ainda reproduz** — `scripts/lib/commands.json` "sem gate e sem menção em CLAUDE.md/CLAUDE-md/" — re-medido: **43 ocorrências** de `interaction_mode` em `commands.json`, **0** em `helpers/`, `.github/`, `CLAUDE.md` e `CLAUDE-md/`; leitores em `render_provider.py:223-225,240,332,971,985`; a chave irmã `plan_gate` mantém as duas defesas (`CLAUDE-md/commands.md:60`, `helpers/agent-lint.sh:384`)
- `gov-committed-install-copy-stale-vs-source-no-gate` — **ainda reproduz** — `.dev-team-agents/` "666 arquivos, 58 de 664 divergem, 16 arquivos-fonte sem contrapartida, 5 dias atrás" — **piorou em todas as medidas: 735 arquivos** na cópia instalada, **66 arquivos divergem** (ignorando `__pycache__`), **19 entradas-fonte sem contrapartida** (incluindo `agents/orchestrator.md`, `commands/orchestrate.md`, `skills/third-party/security-audit`, `skills/security/third-party-security-skills`), e a defasagem foi de **5 → 10 dias** (último sync `ce4de39`, 2026-10-31; HEAD 2026-11-10); `ls .claude/commands/devteam/orchestrate.md` → `No such file or directory`; 168 symlinks em `.claude/`; nenhum gate compara os dois lados

## Lote /tmp/f1b_4.txt (35 itens)

- `docs-sync-agent-reference-omits-orchestrator-and-18-agent-count-claims` — **ainda reproduz** — `docs/agents.md` "`grep -c orchestrator docs/agents.md` → 0; 18 linhas contra 19 arquivos" — re-medido: **0** ocorrências em `docs/agents.md` e em `docs/agents.pt-BR.md`, **18** entradas `###` de descrição, **19** arquivos em `agents/`; as quatro superfícies seguem com a contagem errada (`README.md:15,285`, `README.pt-BR.md:15,285`, `docs/install-codex.md:15` "18 agents", `docs/install-opencode.md:13` "the 18 agents") e `render_provider.py:859-862` segue renderizando o 19º como `primary`
- `ref-readme-sync-pair-discovery-does-not-exclude-worktrees` — **ainda reproduz** — `.github/scripts/ci/02-readme-sync.sh:211` "o `find` exclui `.git` e `node_modules` mas não `.worktrees/`" — linha idêntica em `:211`; medida confirmada sem deriva: **12 arquivos `*.pt-BR.md`** encontrados pelo `find` do gate contra **6** pares reais (`.worktrees/feat`, `.worktrees/fix` e `.dev-team-agents/` entram); `secret_scan.py:26` segue com `.worktrees` em `SKIP_DIRS`
- `flow-orchestrator-route-table-covers-10-of-42-commands-no-gate` — **ainda reproduz** — `agents/orchestrator.md:44-51` "nomeia 10 dos 42 comandos e fecha com catch-all" — re-medido: a tabela nomeia **10 comandos** e `ls commands/*.md` → **42**; `:42` ("reuse the flow that already exists") e as regras MANDATORY de `skills/shared/auto-routing/SKILL.md:31,35` intactas; nada confere a tabela contra `commands/` nem contra `scripts/lib/commands.json`
- `flow-commit-md-no-branch-for-adr-0059-secret-guard-refusal` — **ainda reproduz** — `commands/commit.md` "`grep -n gitleaks\|ADR-0059` → 0" — re-medido **0**; `03b-staged-secret-guard.sh` segue recusando com `exit 2` (`:226`) e declarando "deliberadamente sem escape hatch" (`:25`), e a opção "Commit anyway" segue em `commands/commit.md:158`; `skills/shared/feature-learn/SKILL.md:106` (registrado `:102`) ainda roda o mesmo gitleaks sem escopo
- `gov-seed-scan-regex-blind-to-flutter-swift-kotlin-rn-dotnet-rust-supabase` — **ainda reproduz** — `docs/reports/_prompt-auditoria.md:143-147` "o regex semente não tem flutter, swift, kotlin, react native, dotnet, rust, supabase" — regex idêntico (nenhum dos 7 termos presente); **piorou: 36 → 42 linhas** invisíveis à varredura (`grep -rinE` por esses termos em `agents/ commands/`)
- `flow-hook-prefs-gates-three-precedence-orders-raw-grep-no-helper` — **ainda reproduz** — `scripts/hooks/lib/data-dirs.sh:115` "não existe helper de gate, só `devteam_prefs_file`" — confirmado: `data-dirs.sh` expõe só `devteam_prefs_file`; as três precedências persistem — `session-start.sh:452` só MAIN com `grep -qE` cru, `post-tool-use/04-branch-overlap.sh:41-47` worktree (`CH_ROOT`) antes de MAIN com o comentário "the preferences live in the MAIN checkout only" afirmando o oposto do código, e `post-tool-use/03-repair-detect.sh` + `user-prompt-submit/05-recall.sh:46-48` MAIN antes do root
- `flow-findings-gate-dispatch-keyed-to-hardcoded-pt-br-labels-in-four-commands` — **ainda reproduz** — `commands/backend.md:85-89` "tabela de despacho keyed por rótulos literais em português" — `:85` `Aplicar todos`, `:88` `Não aplicar nada agora`, `:89` `Outro`, com `:66` mandando renderizar o quiz no idioma do usuário (default de instalação `en`); os ramos `Code Review` e `QA` (`:86-87`) seguem sem rótulo correspondente; mesmo padrão confirmado em `frontend.md:78`, `fullstack.md`, `mobile.md`
- `flow-install-md-yes-strip-rule-listed-after-the-branch-it-must-precede` — **ainda reproduz** — `commands/install.md:24` "`--yes` → drop it before parsing é o quarto item" — ordem idêntica: `:23` "One or more space-separated names" vem antes de `:24`, então `install all --yes` casa primeiro; `--yes` sozinho segue sem ramo após o descarte
- `auto-subagent-start-stop-dispatchers-opposite-exit-policies-undocumented` — **ainda reproduz** — `scripts/hooks/subagent-start.sh:5` "non-zero exit propagated" vs `:8` "Exits 0 always on its own" — as duas afirmações seguem no cabeçalho e o código propaga (`:37-42`, `exit $EXIT_CODE`); o irmão `subagent-stop.sh:5-6` força `exit 0` (`:50`) e registra a razão; a divergência de política continua sem razão escrita no `subagent-start.sh`
- `flow-down-md-restates-two-local-environment-stop-rules-it-forbids-restating` — **ainda reproduz** — `commands/down.md:13` "do not restate its rules" com `:19`/`:23` — arquivo **não mudou uma linha** desde o achado (único commit: `749af59`); `:19` e `:23` seguem nomeando § Stop steps 1–2, 3 e 5, e `:23` parafraseia a regra de confirmação separada do step 5
- `gov-supervision-gate-demands-review-marker-in-documented-no-marker-cases` — **ainda reproduz** — `scripts/hooks/lib/subagent-supervision.sh:56` "testa só `agent in REVIEWERS` sem olhar o tipo de passagem" — `:56` idêntico, `REVIEWERS` em `:36` (5 nomes); os três casos sem marcador seguem documentados (`review-result/SKILL.md:26` passagem que não rodou, `:28` router-only, `agents/seo-specialist.md:90` resposta advisory) e a sugestão "`0 when clean`" segue em `:81-82`, com `docs/specs/task-board.md:413` resolvendo `findings = 0` como `"passed"`
- `agent-orchestrator-session-guard-signal-fails-under-nested-spawn` — **ainda reproduz** — `agents/orchestrator.md:21` "detecta spawn aninhado por 'If you have no tool to spawn agents'" — linha idêntica em `:21`, contra `docs/development/adrs/0062-*.md:19` ("spawn subagents up to three levels deep") e `:40` ("its Session Guard is the runtime defense"); `helpers/agent-lint.sh:448` (`check_orchestrator_not_spawned`, registrado `:449-459`) segue cobrindo só o que está escrito no repo
- `agent-orchestrator-missing-from-plan-mode-loaders-gate` — **ainda reproduz** — `helpers/agent-lint.sh:374` "`PLAN_MODE_LOADERS` tem 7 nomes e `grep -ln plan-mode/SKILL.md agents/*.md` devolve 8" — re-medido: **7 nomes** em `:374` e **8 agentes** carregando a skill; `agents/orchestrator.md:32` segue fora do gate, contra `CLAUDE.md:206`; **tocado pelo delta** e segue reproduzindo
- `agent-orchestrator-route-has-no-path-to-architecture-work` — **🟢 Resolved — 827b1a9** — `agents/orchestrator.md:51` "o catch-all é inexecutável: o roster não tem `software-architect`" — `827b1a9` ("fix(sprint): let software-architect own a sprint task", 2026-11-09, dentro do delta) adicionou `| \`software-architect\` | \`reasoning\` |` ao § Agent Roster de `skills/architecture/orchestration/SKILL.md:131`, então o catch-all "agents from the Agent Roster only" passa a ter saída executável para arquitetura e a exigência de `:179` ("verbatim no roster") é satisfeita; o pai (`flow-orchestrator-route-table-covers-10-of-42-commands-no-gate`) segue aberto
- `ref-size-limits-and-ci-lint-comments-state-stale-agent-command-counts` — **ainda reproduz** — `helpers/size-limits.sh:36` "justifica `AGENT_LIMIT=211` falando de 'all 17 agents'" — `:36` idêntico com `AGENT_LIMIT=211` em `:44`, e `.github/scripts/ci/01-lint.sh:87,92` segue com "11 of 17 agents exceed" e "17/17 agents, 25/25 commands, 138/138 skills"; medido agora: **19 agentes, 42 comandos, 168 skills** — **piorou nas skills: 163 → 168**; a regra de governança do teto (`:30-45`) continua decidida sobre números errados e sem gate
- `token-project-context-untrusted-table-duplicated-headerless-19-agents` — **ainda reproduz** — `skills/shared/project-context/SKILL.md:314-320` "a tabela § Untrusted Content aparece duas vezes, a segunda com separador órfão" — § Untrusted Content em `:294`, tabela canônica em `:296-312` e a duplicata com `-----------|------------|` sem cabeçalho em **`:314-320`** (registrado `:311-318`), medida **910 B / 7 linhas** (registrado ~1.000 B), com a redação antiga que não cobre texto oculto/codificado, relay de § Open Decisions, memória nem faixas de IP; arquivo em **374 linhas** (registrado 371), bem sob `SKILL_LIMIT=500`, carregado por **19 de 19 agentes**; **tocado pelo delta** e segue reproduzindo
- `token-branch-overlap-hook-forks-python-and-reparses-cache-per-path` — **ainda reproduz** — `scripts/hooks/post-tool-use/04-branch-overlap.sh:75-77` "o cabeçalho declara 'python is forked once' e o laço forka um por caminho" — `:11-12` segue afirmando "python is forked once, only when all hold" e o `for P in "${PATHS[@]}"` (`:75`) segue forkando `python3 -I -c … match` por caminho, com `match()` em `branch_overlap.py:341` (registrado `:345`) re-lendo e re-parseando o cache inteiro; ms não re-medidos
- `token-language-hook-restates-370-char-policy-on-every-prompt-uncapped` — **ainda reproduz** — `scripts/hooks/user-prompt-submit/04-language.sh:32` "reemite 370 caracteres de política em todo prompt, sem marcador de sessão" — **piorou: 370 → 386 caracteres** na linha `:32`; `grep -c "warn-once\|context-shown"` → **0**, enquanto o irmão `05-recall.sh:81` usa `.context-shown-<session>`; orçamento vizinho segue em `DEVTEAM_HINTS_MAX_CHARS=1200` (`context-hints.sh:30`) e o caminho caro segue sendo o default (`preferences-defaults.json:2` → `pt-BR`)
- `flow-session-start-118-lines-monolithic-no-modular-pattern-asymmetric-with-stop-dispatcher` — **ainda reproduz** — `scripts/hooks/session-start.sh` "118 linhas no slug, 174 em 2026-07-31, 310 em 2026-09-04" — **piorou: 310 → 460 linhas**; não existe diretório `scripts/hooks/session-start/`, logo o padrão de sub-scripts segue aplicado a `pre-tool-use/`, `stop/`, `post-tool-use/` e não aqui
- `flow-conventional-commits-validate-script-no-husky-or-commit-msg-hook-registration` — **ainda reproduz** — `scripts/install.sh` "o instalador nunca registra um hook `commit-msg` ou Husky/Lefthook" — `grep -rn "commit-msg\|husky\|lefthook" scripts/install.sh scripts/lib/*.sh` → **vazio**; `scripts/validate-commit-msg.sh` existe e é citado apenas na lista de arquivos de `.github/scripts/ci/slim-bootstrap.sh:41`, então um `git commit` comum segue sem validação
- `skill-no-skill-uses-scripts-subdir-pattern-agentskills-io` — **ainda reproduz** — "0 de 138 skills usam o subdir `scripts/` da spec; `references/` em 20" — **0 de 168 skills próprias** seguem sem usar o subdir (o único `skills/*/*/scripts` da árvore é `skills/third-party/ui-ux-pro-max/scripts`, vendorizado, não autoria do framework); adoção de `references/` **melhorou: 20 → 30** diretórios
- `skill-adr-coverage-only-architect` — **ainda reproduz** — `skills/shared/adr` "alcançável de apenas um agente" — re-medido: **1 agente** (`agents/software-architect.md`) e 2 comandos (`commands/adr.md`, `commands/learn.md`); os agentes que tomam decisões difíceis de reverter seguem sem caminho até ela
- `token-install-sh-503-lines-largest-single-script-not-fragmented-vs-stop-dispatcher-pattern-13-functions-extractable-each-100-tokens` — **ainda reproduz** — `scripts/install.sh` "803 → 947 linhas, `installer-fetch.sh` extraído mas o script nunca decomposto" — **piorou: 947 → 1.405 linhas** (503 no slug), 11 funções de nível superior; `scripts/lib/installer-fetch.sh` segue como a única extração
- `token-changelog-already-growing-and-not-extracted-by-release` — **ainda reproduz** — `CHANGELOG.md` "441 linhas, sem rotação e sem ferramenta de arquivo" — **piorou: 441 → 2.470 linhas**; nenhum arquivo de changelog arquivado e nenhum helper de rotação (`grep -rn CHANGELOG helpers/*.sh` → vazio); **tocado pelo delta** e segue reproduzindo
- `token-readme-228-each-after-extraction-still-2-files-no-cross-link-tagging` — **ainda reproduz** — READMEs "duas fontes de corpo inteiro sem âncoras de seção" — `grep -c "@section"` → **0 e 0**; **piorou: 228 → 501 linhas cada** (1.002 linhas somadas); **tocado pelo delta** e segue reproduzindo
- `agent-frontend-test-specialist-sonarqube-coverage-block-hardcodes-jest-vitest-commands-and-sonar-javascript-key-while-backend-twin-was-delegated` — **ainda reproduz** — `agents/frontend-test-specialist.md:140-156` "matriz de comandos de cobertura hardcoded que o gêmeo backend já teve removida" — § SonarQube Coverage Integration em `:140` segue com `jest --coverage --coverageReporters=lcov`, `vitest run --coverage` e a chave `sonar.javascript.lcov.reportPaths` (`:156`), enquanto `agents/backend-test-specialist.md:104-108` delega ao `references/quality-gates.md` da skill
- `agent-frontend-developer-description-frontmatter-enumerates-eight-frameworks-react-vue-svelte-angular-blade-twig-erb-jinja-on-identity-surface` — **ainda reproduz** — `agents/frontend-developer.md:3` "oito frameworks fixados na superfície de identidade" — `description:` segue nomeando React, Vue, Svelte, Angular, Blade, Twig, ERB e Jinja (8/8), defeito já corrigido no `mobile-developer`
- `agent-devops-specialist-core-expertise-declares-primary-docker-and-done-checklist-gates-on-docker-terraform-contradicting-own-never-name-a-product-rule` — **ainda reproduz** — `agents/devops-specialist.md:46` "**Primary**: Docker" — `:46` intacto (mais `:50` "GitHub Actions (primary)" e `:56` Terraform/OpenTofu), contradizendo a própria regra em `:128` ("Never name a specific product as the answer"); distância **86 → 82 linhas**; arquivo 209 linhas; **tocado pelo delta** e segue reproduzindo
- `flow-audit-command-devops-analysis-prompt-names-redis-cdn-docker-inside-spawn-instruction` — **ainda reproduz** — `commands/audit.md:118,120` "duas das cinco linhas de escopo do devops-specialist nomeiam vendor" — `:118` "Caching opportunities (Redis, CDN, HTTP caching)" e `:120` "Docker/resource concerns specific to the module" seguem dentro da instrução de spawn (registrado `:126,128`)
- `docs-sync-claude-md-102-states-skill-desc-strict-false-non-blocking-while-agent-lint-31-sets-true-and-ci-promoted-it-same-day` — **ainda reproduz (na forma original)** — `CLAUDE.md:160` "non-blocking warning today (`SKILL_DESC_STRICT=false`)" — a nota de 2026-10-10 dizia que a variável havia sido **removida**; ela voltou: `helpers/agent-lint.sh:98` define **`SKILL_DESC_STRICT=true`** (reintroduzida em `7736e20d`) e é usada em `:341`, com `.github/scripts/ci/01-lint.sh:66` concordando com o código — logo `CLAUDE.md:160` documenta como verdade corrente o valor oposto ao do código, com a variável nomeada, exatamente como no achado original; **tocado pelo delta** e segue reproduzindo
- `docs-sync-claude-md-173-says-all-devteam-commands-load-current-context-while-213-lists-four-exceptions-as-the-complete-list` — **ainda reproduz** — `CLAUDE.md:265` "All `/devteam:*` commands — detects branch/worktree state" vs `CLAUDE-md/commands.md:58` — a lista de exceções (registrada em `:51`) segue declarando **seis** "the complete list" e **piorou: 5 → 6** comandos que só a nomeiam em prosa (`symlinks`, `install`, `explain`, `version`, `status`, `insights`); as duas afirmações seguem incompatíveis; **tocado pelo delta** e segue reproduzindo
- `docs-sync-reports-index-md-99-legend-comment-claims-all-131-entries-unmarked-while-121-carry-executed-or-partial-marks` — **ainda reproduz** — `docs/reports/_index.md:115` "All 131 entries below are unmarked: they were re-verified as reproducing at HEAD 7f85ed7" — comentário de legenda intacto (migrou `:99 → :115`), contra `:51` do mesmo arquivo ("**120 ✅ · 1 ⚠️ · 10 🔴**") e contra **72** linhas com marcadores; **piorou também a contagem**: o banco tem agora **183** entradas `- \`slug\``, não 131; **tocado pelo delta** e segue reproduzindo
- `flow-pre-tool-use-02b-telemetry-reads-devteam-hook-payload-branch-that-only-stop-dispatcher-ever-sets-dead-path-in-pretooluse` — **ainda reproduz** — `scripts/hooks/pre-tool-use/02b-telemetry.sh:19-20` "ramo morto de leitura de payload" — `[ -f "${DEVTEAM_HOOK_PAYLOAD:-}" ]` segue em `:19`, e `DEVTEAM_HOOK_PAYLOAD` só é exportado por `scripts/hooks/stop.sh:22` — `scripts/hooks/pre-tool-use.sh` não o define, logo o ramo segue morto no PreToolUse e o contrato dos dois dispatchers segue assimétrico
- `skill-shared-migration-v1-to-v2-437-lines-largest-in-repo-single-conditional-loader-in-setup-assistant-no-references-extraction-and-no-retirement-criterion` — **ainda reproduz** — `skills/shared/migration-v1-to-v2/SKILL.md` "437 linhas, maior do repo, um carregador, sem `references/`, sem critério de aposentadoria" — re-medido **414 linhas / 15.724 B** (encolheu 437 → 414, segue a maior em linhas de `skills/shared/`), diretório só com `SKILL.md` (sem `references/`) e **1** carregador (`agents/setup-assistant.md`); nenhum critério de aposentadoria adicionado
- `token-interaction-patterns-209-lines-loaded-unconditionally-by-24-commands-and-2-agents-while-only-38-lines-are-the-rule-and-159-are-json-examples-and-recurring-patterns` — **ainda reproduz** — `skills/shared/interaction-patterns/SKILL.md` "209 linhas carregadas por 24 comandos e 2 agentes" — **piorou em tudo: 209 → 404 linhas / 23.833 B** e carregadores **26 → 44** (39 comandos + 5 agentes); diretório segue só com `SKILL.md`, sem extração para `references/`; **tocado pelo delta** e segue reproduzindo
