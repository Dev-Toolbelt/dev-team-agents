# Fase 1 e 1b — Verificação Guardiã — 2026-11-07

**Data:** 2026-11-07 · **Baseline:** `HEAD` = `5133c8c` · **Baseline anterior:** `b64428b`

> **Árvore suja durante todo o pass.** Na Fase 0 o working tree carregava **10 arquivos
> modificados e 2 diretórios não rastreados** (`CLAUDE.md`, `README.md`, `README.pt-BR.md`,
> `agents/security-specialist.md`, `commands/security.md`, dois ADRs, `skills/third-party/README.md`,
> `skills/third-party/sources.json`, `tests/test_third_party_skills.py`, mais
> `skills/security/third-party-security-skills/` e `skills/third-party/security-audit/`).
> Toda evidência nesses arquivos vem de `git show HEAD:<path>`; para os demais, disco == `HEAD`.

## Método

**Conjunto verificável** (✅ Executed ou ⚠️ Partial, nos dois bancos): **152** — 31 ✅ em
`_index.md` + 120 ✅ e 1 ⚠️ em `_index-archive-2026-Q3.md`.

**Amostragem.** 152 > 60, logo: **todos os 42 HIGH/MEDIUM-HIGH** (20 HIGH + 22 MEDIUM-HIGH) mais
**amostra aleatória de 30% dos 110 restantes** (33 itens), `seed=20261107`. Cobertura declarada:
**75 de 152 (49,3%)**.

Datas de marcação na amostra: 49 de `2026-07-31`, 25 de `2026-10-02`, 1 de `2026-09-30`.
Apenas **1 dos 75** não teve nenhum commit da janela tocando o campo `alvo:`
(`skill-spec-gate-scope-lock-hard-gate-unreachable-by-execution-agents`) — e esse é precisamente o
caso que a **nota de método de 2026-10-17** prevê: o `alvo:` nomeia o arquivo que *descreve* o
problema, e a remediação estava nos corpos dos agentes. Classificá-lo 🔴 por construção teria sido
um falso positivo; três outros itens da amostra ([18], [25], [41]) dependeram da mesma nota.

## Placar da Fase 1

| Marca verificada | Qtd | % |
|---|---|---|
| ✅ **Feito** | 60 | **80,0%** |
| 🟡 **Parcialmente feito** | 12 | 16,0% |
| 🔴 **Não feito** | 3 | **4,0%** |

**Reaberturas novas: 0.** As 3 🔴 e 5 das 12 🟡 já carregavam anotação de passes anteriores. Este é
o **terceiro pass consecutivo com 0% de reabertura nova** (2026-10-17 e 2026-10-24 também fecharam
em zero). A taxa de 4,0% de 🔴 está muito abaixo do limiar de escalonamento de 15% — a integridade
do banco não está comprometida.

**Nenhuma reversão silenciosa** foi encontrada nos commits posteriores às marcações. Em dois casos
([17], [22]) os commits de AFTER_MARK **endureceram** a correção; em um ([52]) houve desativação
temporária (`ba39c86`, 2026-08-06) com reativação (`156771b`, 2026-08-11) e integridade no `HEAD`.

---

## Divergências novas (7 🟡, sem anotação prévia no banco)

### `flow-02c-escape-hatch-anchored-while-detection-is-substring`
- **Marca original:** ✅ Executed: 2026-10-02 · **Severidade:** MEDIUM-HIGH
- **Marca verificada:** 🟡 Parcialmente feito
- **Commit examinado:** `ddeaee6` — fix(hooks): let exit 2 win over SIGPIPE, scope the full-suite guard, retire stale worktree sessions
- **Evidência:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh:47` — `CONFIRM_RE='(^|[[:space:];&|(])DEVTEAM_FULL_SUITE_CONFIRMED=1([[:space:]]|$)'`
- **Por que a marcação está errada:** a escotilha deixou de exigir posição 0 (`cd frontend && DEVTEAM_FULL_SUITE_CONFIRMED=1 npm test` sai 0, verificado), mas o grupo de prefixos permitidos não inclui aspas. O wrapper que o próprio arquivo cita em `:185` (`docker exec x sh -c "pnpm test:run"`) continua sem escotilha viável: `CONFIRM_RE` não casa porque o caractere anterior é `"`, enquanto `is_full_suite` remove as aspas em `:188` e classifica como full suite. Em árvore limpa isso é `exit 2` sem saída.
- **Falta:** admitir `"` / `'` no grupo de prefixos de `CONFIRM_RE`, ou aplicar a checagem após a normalização de `is_full_suite`.

### `auto-install-sh-bash-source-fallback-resolves-to-cwd-and-sources-project-lib`
- **Marca original:** ✅ Executed: 2026-10-02 · **Severidade:** MEDIUM-HIGH
- **Marca verificada:** 🟡 Parcialmente feito
- **Commit examinado:** `88834b6` — fix(scripts): stop install.sh sourcing from the piped CWD, escape ADR titles, sync preferences mirrors
- **Evidência:** corrigido em `scripts/install.sh:63-66` — `if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then`. Residual em `scripts/install.sh:24` — `_dta_py="$(dirname "${BASH_SOURCE[0]}")/lib/python.sh"`, sem guarda.
- **Por que a marcação está errada:** o defeito nomeado (fallback `:-$0` → `source` de `lib/state.sh` do CWD) está sanado, mas `:24` reintroduziu o mesmo padrão sem guarda. Reproduzido: sob `echo … | bash`, `BASH_SOURCE[0]` fica unset e, com `set -euo pipefail` ativo em `:21`, o `curl -sSL … | bash` documentado em `README.md:66` aborta com `BASH_SOURCE[0]: unbound variable`.
- **Falta:** a mesma guarda de `:63-66` aplicada a `:24`.

### `ref-claude-md-file-structure-omits-helpers-and-privacy-and-claude-md-folder`
- **Marca original:** ✅ Executed: 2026-07-31 · **Severidade:** HIGH
- **Marca verificada:** 🟡 Parcialmente feito
- **Commit examinado:** `bbb311a` — docs: correct stale authoring standards, structure maps and command tables (árvore movida para `CLAUDE-md/file-structure.md` em `38f5417`)
- **Evidência:** presentes na árvore — `CLAUDE-md/file-structure.md:25` (`├── CLAUDE-md/`), `:36` (`├── helpers/`), `:51` (`├── opencode/`), `:92` (`├── .github/`), `:102` (`├── user-data/`), `:107` (`├── PRIVACY.md`). Ausente: `.claude/` não tem entrada de árvore.
- **Por que a marcação está errada:** 6 dos 7 itens que o relatório-fonte nomeia foram documentados; `.claude/` segue sem entrada. Pior, a árvore voltou a defasar: `TERMS.md` e `infra/` entraram em 2026-10-02 (`ad3dfa7`, `48fbd2d`) e `.dev-team-agents/` é rastreado — nenhum dos três aparece, apesar de `git ls-tree HEAD` listá-los no topo.

### `agent-three-reviewers-overlap`
- **Marca original:** ✅ Executed: 2026-07-31 · **Severidade:** LOW-MEDIUM
- **Marca verificada:** 🟡 Parcialmente feito
- **Commit examinado:** `b4e219f` — refactor(agents): delegate shared context, extract stack-prescriptive bodies
- **Evidência:** `agents/backend-reviewer.md:33` — "Load `skills/shared/reviewer-base/SKILL.md` — canonical base review checklist shared with `code-reviewer` and `frontend-reviewer`". Esqueleto de saída ainda copiado em `backend-reviewer.md:155-185`, `frontend-reviewer.md:147-180` e `code-reviewer.md:132-169`.
- **Por que a marcação está errada:** a metade do Foundational Rule foi resolvida (`diff` dos blocos dá 18 linhas divergentes contra 4 idênticas; eram "9 linhas divergentes" na abertura), mas o relatório-fonte nomeia explicitamente dois sub-escopos: "Only the Foundational Rule duplication and the report skeleton remain". O esqueleto (`### Summary / Blocking Issues / Security Findings / Performance Findings / Suggestions / Nitpicks / Architecture Conformance`) segue verbatim nos três sem casa canônica — `skills/shared/pr-review/SKILL.md:73` tem um "Review Comment Format" diferente.

### `skill-discovery-mode-no-stale-lock-cleanup-script-30min-rule-only-documented`
- **Marca original:** ✅ Executed: 2026-07-31 · **Severidade:** LOW-MEDIUM
- **Marca verificada:** 🟡 Parcialmente feito
- **Commit examinado:** `519ca7e` — feat(skills): add extraction targets, close domain gaps, fix skill defects
- **Evidência:** `skills/shared/discovery-mode/SKILL.md:122` — `if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +30 2>/dev/null)" ]; then`; `:143` — "No scheduled job sweeps orphaned locks."
- **Por que a marcação está errada:** os defeitos (b) ordenação (sweep antes do bail-out, `:120-128`) e (c) portabilidade macOS (`date -d` → `find -mmin`) foram corrigidos. O defeito (a) do slug não: `grep -rn "discovery-lock" scripts/ helpers/` devolve zero — não existe script nem helper de limpeza, e a regra de 30 min continua sendo um snippet que o agente precisa executar, hoje reconhecido como lacuna deliberada em `:143`.

### `flow-stop-dispatcher-globs-all-sh-no-allowlist-or-per-subscript-toggle-any-dropped-file-auto-executes`
- **Marca original:** ✅ Executed: 2026-07-31 · **Severidade:** MEDIUM
- **Marca verificada:** 🟡 Parcialmente feito
- **Commit examinado:** `cc28900` — fix(hooks): gate, decompose and harden the lifecycle dispatchers
- **Evidência:** `scripts/hooks/stop.sh:62` — `SUBSCRIPT_RE='^[0-9]{2}[a-z]?-[a-z0-9]([a-z0-9-]*[a-z0-9])?\.sh$'`; `:64` — `for script in "$HOOKS_DIR"/*.sh; do`.
- **Por que a marcação está errada:** o glob `*.sh` continua; o que foi adicionado é um filtro por convenção de nome, não um allowlist. Drafts, `.sh.bak` e `notes.sh` passam a ser ignorados, mas qualquer arquivo nomeado `NN-nome.sh` solto em `stop/` ainda auto-executa. O segundo sub-escopo do slug também falta: não há toggle por sub-script — `grep -rn "DEVTEAM_DISABLE\|disabled_hooks"` em `scripts/` e `CLAUDE-md/` devolve zero, e `CLAUDE-md/hooks.md:36` documenta o filtro de nome como a única barreira.

### `flow-commit-command-160-lines-pre-commit-gates-extractable-skill`
- **Marca original:** ✅ Executed: 2026-07-31 · **Severidade:** LOW
- **Marca verificada:** 🟡 Parcialmente feito
- **Commit examinado:** `6919564` — refactor(commands,scripts): remove cross-cutting duplication, close the size gate
- **Evidência:** `commands/commit.md:92` — "…the **Layered Commits** ordering table in the loaded `conventional-commits` skill … **It ends at layer 7 (tests)**; this command continues with **8 — Config / CI** … and **9 — Docs**". Contra `skills/shared/conventional-commits/SKILL.md:71-72` — `| 8 | Config / CI | … |` / `| 9 | Docs | README, changelog, ADRs, runbooks |`.
- **Por que a marcação está errada:** a cópia da tabela foi removida, mas o **mesmo commit** `6919564` acrescentou as camadas 8 e 9 ao skill *e* escreveu em `commit.md:92` que o skill "ends at layer 7" — afirmação falsa desde o primeiro dia. O sub-escopo do slug ("pre-commit gates extractable skill") também não foi feito: a tabela de lint/type-check segue inline em `commands/commit.md:129-139`, não existe skill de pre-commit gates (`find skills -iname "*pre-commit*"` = vazio) e o arquivo cresceu de 160 para 193 linhas.

---

## Divergências confirmadas (já anotadas no banco)

### 🔴 — 3 itens, nenhum novo

#### `flow-cli-commit-validate-msg-script-skipped-silently-when-missing-no-instructive-error`
- **Marca verificada:** 🔴 Não feito — **terceira confirmação** (2026-07-31, 2026-09-11, hoje)
- **Commit examinado:** `b49cac1` (2026-10-17, último toque em `commands/commit.md`)
- **Evidência:** `commands/commit.md:151-153` — `if [ -f ".dev-team-agents/scripts/validate-commit-msg.sh" ]; then` / `echo "$COMMIT_MSG" | bash .dev-team-agents/scripts/validate-commit-msg.sh` / `fi`
- **Nota:** segue sem ramo `else` — script ausente ⇒ validação pulada sem uma palavra. O `AskUserQuestion` de `:157-158` é condicionado a "If any gate … **returns non-zero**", e um script que nunca executa não retorna nada. Agravante novo: o comentário de `:150` ("skipped if project has its own commit-msg hook") declara uma condição que o código não testa — o `-f` checa a existência do próprio validador.

#### `agent-software-architect-foundational-rule-51-lines-2x-avg`
- **Marca verificada:** 🔴 Não feito — **segunda confirmação** (2026-08-21, hoje)
- **Commit examinado:** `b4e219f`
- **Evidência:** `agents/software-architect.md:19` — `## Foundational Rule`, bloco até `:62` = **42 linhas** no `HEAD`. Progressão: `b4e219f~1` = 36 → commit remediador = 40 → `HEAD` = 42.
- **Nota:** o commit apontado como remediação **aumentou** o bloco em 4 linhas. Segue o maior Foundational Rule do repo (~2,3× a mediana de 18); o segundo é `security-specialist` com 37.

#### `token-conventional-commits-skill-138-lines-loaded-by-commit-and-pr-commands-but-also-mentioned-as-skill-load-in-claude-md-skill-loads-by-table-format-not-prose`
- **Marca verificada:** 🔴 Não feito — **segunda confirmação** (2026-09-04, hoje)
- **Commit examinado:** `6919564`
- **Evidência:** `commands/commit.md:7` — "Load the skill at `skills/shared/conventional-commits/SKILL.md` before doing anything."; `CLAUDE.md:520` (via `git show HEAD:`) — "**Defer to the project's own pattern first** … If a project-specific pattern is clearly in use, follow it instead."
- **Nota:** a diretiva de carga incondicional está intacta e o skill cresceu de 138 para **169 linhas**. `6919564` só removeu a tabela de camadas restatada.

### 🟡 — 5 confirmações

| Fingerprint | Confirmação | Sub-escopo que falta no `HEAD` |
|---|---|---|
| `flow-size-limits-sh-ci-only-warn-only-not-in-stop-dispatcher-…` | 4ª | `grep -rn size-limits scripts/hooks/ .github/` devolve uma única linha, `.github/scripts/ci/01-lint.sh:95` (`blocking`); nenhum dos 16 sub-scripts de `scripts/hooks/stop/` conta linhas e `helpers/agent-lint.sh` não tem `wc -l`. Atualização: a árvore voltou a passar — `bash helpers/size-limits.sh` sai 0 com aviso não bloqueante "CLAUDE.md: 600 lines (warning threshold: 600, fails at 700)" |
| `auto-update-no-integrity-check` | 3ª | integridade de **transporte** entregue (`dta_is_safe_ref` em `installer-fetch.sh:128`, shebang `:162`, tamanho `:154`, `bash -n` `:174`); **autenticidade** não — `scripts/install.sh.sha256` não existe no `HEAD` nem é gerado por workflow, e `:200` (`grep -Eq '^[a-fA-F0-9]{64}$' \|\| return 0`) faz `dta_verify_digest` **falhar aberta** em todo caminho real |
| `token-skill-loads-via-table-vs-prose-inconsistent` | 3ª, **pior que o registrado** | `frontend-reviewer` 21 refs `skills/` e **0** linhas de tabela; `backend-reviewer` 17 refs e **0** tabela (antes só o frontend estava em zero), contra `code-reviewer.md:53-58` com tabela Trigger\|Skill. Nenhuma regra de formato escrita — `grep -rn -i "conditional load" CLAUDE.md CLAUDE-md/` devolve zero |
| `token-pre-tool-use-01-check-updates-forks-python3-to-read-interval-before-ttl-early-exit-…` | 2ª — **a marca correta é 🟢** | a correção marcada (sidecar `.update-check-interval`, `cc28900`) não está no `HEAD`; o script original só existe desativado (`_disabled-01-check-updates.sh`). O sintoma morreu por outra via (`3c46d04`, "perf(hooks): move update-check from PreToolUse to SessionStart") — `session-start.sh:191-212`. A ordenação original persiste (`update-check.sh:39-42` forka `python3` antes do early-return de TTL) mas custa 1 fork por sessão, não por tool call |
| `token-claude-md-426-lines-still-monolithic-…` | **melhorou: 🔴 → 🟡** | os **três** blocos nomeados estão hoje extraídos — `CLAUDE-md/commands.md` (88 linhas, ponteiro em `CLAUDE.md:272`) e `CLAUDE-md/hooks.md` (181 linhas, ponteiro em `:510`); `grep` no `HEAD` não acha a tabela comando→agentes nem o mapa de hooks inline. Falta a premissa central: `CLAUDE.md` está em **600 linhas** (426 no registro, 647 em 2026-10-10), exatamente no `CLAUDE_MD_WARN=600` de `helpers/size-limits.sh:88`. A marca de 2026-07-31 também era falsa na data: nenhuma extração ocorreu naquela janela (`2b436ea` é de 2026-08-03, `309bebc` de 2026-09-27) |

---

# Fase 1b — Validade dos achados abertos

**Conjunto aberto:** **130** fingerprints sem marcador (109 em `_index.md` + 10 no arquivo Q3, mais
os 11 que carregam só anotação 🔴/🟡 de reabertura e permanecem abertos na prática).
**Cobertura: 130 de 130 (100%).**

| Estado | Qtd | % |
|---|---|---|
| Ainda reproduz | 125 | 96,2% |
| 🟢 **Resolved** | 4 | 3,1% |
| ⚰️ **Obsoleto** | 1 | 0,8% |

**Mortalidade do pass: 3,85%** (5 de 130) — a segunda maior desde a consolidação, atrás apenas dos
9,3% de 2026-10-02.

**E a mortalidade baixa não é imobilidade.** **71 dos 130 alvos abertos (55%) foram tocados pelo
delta** de 154 commits e 880 arquivos, e 66 desses 71 seguem reproduzindo. O banco está medindo
durabilidade real, não uma árvore parada.

## Os 5 que morreram

| Fingerprint | Marca | Resolvido por | Evidência |
|---|---|---|---|
| `flow-update-sh-codex-slim-guard-dead-branch-false-strip-claim` | 🟢 | `f0fb093` + `60a1798` | `scripts/update.sh` não tem mais guard algum — `:123` delega `po_rerender_providers`; o guard reescrito testa plumbing real em `scripts/lib/provider-ownership.sh:184`. A premissa da "false strip claim" caiu: `strip-tarball.sh:35-37` declara o plumbing **incluído** no slim install |
| `flow-fix-md-only-implementation-command-without-review-qa-handoff` | 🟢 | `f4986ea` | `commands/fix.md:35-37` — "## Next step (mandatory)" / "run the **Review Next-Step Gate** from the interaction-patterns skill loaded above"; gate canônico em `skills/shared/interaction-patterns/SKILL.md:267-279` com modos `ask`/`auto`/`skip` |
| `flow-store-install-ships-dev-auth-config-into-core-despite-sr-27` | 🟢 | `0d37214` + `ebff2fe` | `scripts/lib/auth-config.dev.json` não existe mais no `HEAD`, e `packaging/windows-cli/build.py:41` virou allowlist explícita (`CLI_LIB_FILES`) em vez de copiar `scripts/` inteiro |
| `flow-hook-events-only-pretooluse-and-stop` | 🟢 (parcial) | `2049748` + `1411813` | `scripts/install.sh:701` registra `"UserPromptSubmit"` e `:711`/`:834` registram `"SubagentStop"`. **9 eventos** registrados hoje contra 2 no registro. `Notification` segue sem registro |
| `auto-release-workflow-has-no-guard-for-auth-config-placeholders` | ⚰️ | `0d37214` | Premissa refutada: os `REPLACE-ME-PROD-*` deixaram de existir. `scripts/lib/auth-config.json` traz valores reais (`"environment": "prod"`, `supabase_url`, `entitlement_keys`), e `entitlement.py:142` resolve `configured` = `True`. Não há mais nada para um job de tag preencher nem verificar |

## Degradações medidas — 24 fingerprints abertos mediram pior

Mais que o dobro do recorde anterior (8 em 2026-10-24 e em 2026-10-02). As dez piores:

| Fingerprint / alvo | Registrado | `HEAD` | Δ |
|---|---|---|---|
| `token-interaction-patterns-209-lines-…` | 209 ln × 26 carregadores | **372 ln × 45** | **+240% agregado** |
| `docs/wiki/README.md` (`token-wiki-retrieval-index-13-7kb-…`) | 13.715 B / 51 ln | **27.768 B / 107 ln** | +102% em 28 dias; **15,8×** sobre `3b9ba317` |
| `CHANGELOG.md` (`token-changelog-already-growing-…`) | 441 ln | **2.463 ln** | +458% |
| `scripts/hooks/session-start.sh` (`flow-session-start-118-lines-…`) | 118 ln | **460 ln** | +290%; único hook de evento sem subdiretório |
| `scripts/install.sh` (`token-install-sh-503-lines-…`) | 503 ln | **1.405 ln** | +179%; 11 funções, todas utilitárias |
| `.claude/skills` índice (`token-151-skills-flat-symlinked-…`) | 151/152 skills, 12.751 chars | **167/168, 19.360 chars** | +52% no índice sempre carregado |
| `references/checks-list.md` (`token-checks-list-…`) | 668 ln (681 em out.) | **887 ln / 55.170 B** | +33%; bloco Codex 158 → 193 ln |
| `fix-patterns.md` (`token-fix-patterns-517-lines-…`) | 517 ln (457 em out.) | **654 ln / 32.288 B** | +27% / +43% |
| `README.md` / `README.pt-BR.md` (`token-readme-228-each-…`) | 228 ln cada | **500 ln cada** | +119%; `@section`: 0 → 0 |
| `REVIEW_TYPE_RE` / roster de revisores | 2 hooks / 5 casas | **4 hooks / 8 casas** | pior; 4 regexes bash sem gate |

Outras degradações estruturais: `scripts/hooks/lib/` foi de 10 para **14** arquivos e
`CLAUDE-md/hooks.md` documenta **10 de 14** (`data-dirs.sh`, `context-hints.sh`, `self-heal.sh`,
`subagent-supervision.sh` sem linha); `warn-once.sh` ganhou dois consumidores (`03g`, `03h`) que
herdaram **ambos** os defeitos registrados (assinatura sem `$REPO_ROOT` e ausência de
`warn_once_reset`), levando de 2/3 para **4/5** os hooks afetados; uma 5ª casa de registro IPC
(`taskGraphIpc.ts:104`) entrou sem gate; um 2º arquivo JS sem gate apareceu
(`scripts/lib/devteam/qa_login.mjs`); `qa-specialist` foreground foi de 7 para **11** chamadores;
`ref-command-description-duplicated-frontmatter-vs-commands-json` saltou de 35 divergentes para
**42 de 42**; `auto-orphan-skill-scan-user-invocable-parser-overruns` abriu a janela do parser de
77 para **110 linhas**, extraindo 6 nomes em vez de 4; e os execves do dispatcher `pre-tool-use`
por `Read` subiram de 42 para **91**.

## Melhorias parciais — achado sobrevive, premissa enfraquecida

- `skill-orchestration-spawn-integrity-unreachable-from-devteam-commands`: 0/34 → **3/42** comandos carregam a skill (`sprint.md:8`, `release-qa.md:8`, `architect.md:31`). Mas 23 das 26 superfícies de spawn em `commands/` seguem descobertas — o defeito piorou em números absolutos.
- `skill-token-efficiency-background-mgmt-contradicts-orchestration-discipline`: `strategies.md` passou a disclosure progressiva — **0 de 19** agentes o carregam diretamente (antes 18/18). Contradição textual intacta.
- `token-graphify-setup-os-detection-30-lines-…`: duplicação encolheu de ~30 para **9 linhas** (`:27-35`) — mas sobrou exatamente a parte destrutiva (barrar Windows sem WSL), divergindo de `tool-installers/SKILL.md:12`.
- `flow-install-provider-gate-fallback-fails-open-without-gate-lib`: o `else` ausente foi adicionado por `1660e91` (`install-provider.sh:125-126`) — como **no-op**: avisa e prossegue. Em `enforce` continua se comportando como `allow`, nos dois casos (sem CLI; CLI que quebra).
- `agent-three-at-exactly-211-line-ceiling-zero-headroom`: de 3 agentes no teto para **1** (`frontend-developer.md` = 211). Ironia registrada: `frontend-developer` é justamente o único dos cinco agentes de `agent-no-claude-attribution-restated-in-five-agents` que **não** tem a regra de commit — e o teto é agora o obstáculo a adicionar a linha de delegação.
- `skill-test-strategy-inlines-test-pyramid-section`: a contradição de `:44` sobre banco real foi resolvida por `9a64920`; a duplicação de 36 linhas (`:20-55`) permanece.
- `agent-three-reviewers-review-output-template-triplicated-comments-slot-lost`: a divergência `### SonarQube` convergiu nos três (router `:113`, backend `:186`, frontend `:187`); a de `### Comments` não.
- `token-spec-gate-17kb-loaded-whole-by-six-execution-agents`: já não é a 2ª maior skill de `skills/shared/` — porque `project-context` (25.266 B) e `interaction-patterns` (20.440 B) cresceram mais. O arquivo foi de 17.463 B para **19.029 B** e os carregadores de 6 para **9**.
- `token-archive-index-rotates-index-sections-only-report-directories-never-pruned`: a rotação do índice **passou a rodar** (`_index-archive-2026-Q3.md` existe, `2e4e3ee` e `47d15e0`), o que confirma que o hook funciona e **isola** o defeito: zero dos 14 diretórios datados (1,4 MB) foi podado.

## Correções de premissa — material para o próximo pass

1. **`docs-sync-claude-md-102-states-skill-desc-strict-false-…`** — a nota anexada em 2026-10-10 afirma que `SKILL_DESC_STRICT` "não existe mais". **Isso está errado no `HEAD`:** a variável está viva em `helpers/agent-lint.sh:98` (`=true`), é consumida em `:341` e empurra para `ERRORS` (bloqueante). O achado volta à sua forma original: `CLAUDE.md:160` documenta `false`/não-bloqueante e o código seta `true`. `.github/scripts/ci/01-lint.sh:66` está **correto** e deve sair da lista de referências stale. A nota de outubro provavelmente veio de um `git grep` truncado.
2. **`scripts/n.sh` nunca existiu** — relatórios de 2026-07-30, 2026-08-28 e 2026-09-11 citam esse caminho. É artefato de um `rg -r n` (flag de substituição) aplicado sobre `validate-commit-msg.sh`. O nome real é `scripts/validate-commit-msg.sh`.
3. **`agents/reviewer-base.md` nunca existiu** — é `skills/shared/reviewer-base/SKILL.md`.
4. **`skills/shared/orchestration/` migrou para `skills/architecture/orchestration/`** — fingerprints que citem o caminho antigo precisam ser reancorados.
5. **`skill-shared-migration-v1-to-v2-437-lines-largest-in-repo`** — "largest in repo" caducou (`skills/third-party/emil-design-eng/SKILL.md` = 674 ln). Continua a **maior skill autoral** (414 ln), com 1 carregador condicional, sem `references/` e sem critério de aposentadoria.
6. **`flow-prompt-auditoria-interactive-plan-gate-unsatisfiable-in-unattended-run`** — `git log -S'pode executar direto'` devolve só `3f94594`, o commit que criou o prompt: a cláusula de dispensa **sempre existiu**, logo a regra 7 nunca foi estritamente inviolável. O que reproduz de fato é outra coisa: a regra 7 cobre a escrita de relatórios, mas o bloco `git add`/`commit`/`push` de `_prompt-auditoria.md:342-358` não tem gate algum.
7. **Re-ancoragens de linha** (para o pré-filtro mecânico): tabela de comandos e exceções de Plan Gate migraram de `CLAUDE.md` para `CLAUDE-md/commands.md:43,44,58,60`; *Canonical Rule Homes* está em `CLAUDE.md:183-232`; a Learn Trigger Rule em `CLAUDE.md:479`; o laço do `agent-lint` foi de `:478` para `:585`.
