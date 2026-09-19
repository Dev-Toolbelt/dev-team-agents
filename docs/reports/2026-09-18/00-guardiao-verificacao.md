# Fase 1 e 1b — Verificação Guardiã — 2026-09-18

**Baseline:** `HEAD` = `ef69da3` · **Baseline anterior:** `9530551`

---

## Método

O banco tem **241 fingerprints**: 120 ✅ Executed, 1 ⚠️ Partial, 4 🟢 Resolved, 0 ↩️/⚰️ e **117
abertos**. O conjunto verificável (✅ + ⚠️) é de **121 itens** — acima do limite de 60, logo a regra
de amostragem se aplica.

**Cobertura acumulada.** Passes anteriores já verificaram 99 dos 121 contra `a67cac9`/`9530551`. O
delta de código desde o baseline anterior é de **dois arquivos** — `scripts/install.sh` e
`scripts/new-adr.sh`, ambos no commit `ef69da3` ("fix(scripts): fix ADR octal parsing and install.sh
unbound BASH_SOURCE") — e todo o restante do delta está sob `docs/reports/`. Isso preserva a
validade dos vereditos anteriores e concentra este pass nos **46 itens ainda não cobertos**.

**Critério de amostragem declarado:**

| Grupo | Regra | N |
|---|---|---|
| Obrigatório | todos os HIGH e MEDIUM-HIGH ainda não cobertos | 1 |
| Prioridade de delta | fingerprint cujo alvo está no delta de código | 1 |
| Amostra aleatória | 30% dos 44 restantes, semente `20260918` | 14 |
| **Total deste pass** | | **16** |

**Cobertura da Fase 1: 16 de 46 não cobertos (35%) · acumulado 115 de 121 (95%).**

Todas as 16 marcas são datadas **2026-07-31**. A janela de remediação é o conjunto de commits
daquele dia — de `bbb311a` (14:30 UTC) a `483cba5` (20:43 −0300) —, reconstruída por
`git log --since=2026-07-31 --until=2026-08-01` e confirmada item a item por `git show <sha> -- <path>`.

---

## Placar

| Veredito | N | % |
|---|---|---|
| ✅ Feito | 13 | 81,3% |
| 🟡 Parcialmente feito | 1 | 6,3% |
| 🔴 Não feito | 2 | 12,5% |

**Acumulado contra o banco:** 115 de 121 (95%) → **96 ✅ · 10 🟡 · 9 🔴** (84% confirmado, 7,4%
divergente).

**Escalonamento não disparado.** 12,5% de 🔴 está abaixo do limiar de 15%, mas é a maior taxa desde
2026-09-04 e as duas 🔴 são **reaberturas de itens já reabertos antes**, não descobertas novas — ver
a nota ao final desta seção.

---

## Fase 1 — item a item

### 1. `token-claude-md-426-lines-still-monolithic-three-extractable-blocks-commands-table-40-stop-sub-script-convention-24-hook-files-map-8-total-72-lines-while-claude-md-folder-already-exists-with-preferences-notifications-user-data-versioning`

- **Severidade:** MEDIUM-HIGH
- **Marca original:** ✅ Executed 2026-07-31
- **Veredito:** 🔴 **Não feito**
- **Commit examinado:** `bbb311a` — `docs: correct stale authoring standards, structure maps and command tables` e `7736e20` — `docs: sync documentation with six waves of changes, enforce both size gates`. Ambos tocaram `CLAUDE.md` na janela, mas **acrescentaram** conteúdo; nenhum extraiu bloco algum para `CLAUDE-md/`.
- **Evidência:** `CLAUDE.md:212` — "`| Command | Agents invoked | Use when… |`" (tabela de comandos ainda inline); `CLAUDE.md:418` — "`## Agent Memory System`" (ainda inline). `git show bbb311a~1:CLAUDE.md | wc -l` → **425**; `wc -l CLAUDE.md` → **602**.
- **Análise:** Quarta confirmação de reabertura. Nenhum dos três blocos apontados foi extraído dentro da janela. A única extração real — `CLAUDE-md/hooks.md`, que levou a Stop sub-script convention e o Hook Files Map — veio de `2b436ea` em **2026-08-03**, fora da janela; por construção isso é 🟢 parcial por outra via, não ✅. E o arquivo cresceu **177 linhas líquidas** desde a abertura da marca.

### 2. `auto-new-adr-sh-sed-title-substitution-breaks-on-pipe-ampersand-backslash-in-free-form-adr-title-no-escaping`

- **Severidade:** LOW-MEDIUM · **prioridade de delta** (alvo tocado por `ef69da3`)
- **Marca original:** ✅ Executed 2026-07-31
- **Veredito:** 🔴 **Não feito**
- **Commit examinado:** **nenhum commit da janela tocou o alvo** — `git log --format='%h %s' bbb311a~1..483cba5 -- scripts/new-adr.sh` retorna vazio.
- **Evidência:** `scripts/new-adr.sh:61` — "`    -e "s|\[Title\]|$TITLE|g" \`", com `scripts/new-adr.sh:6` — "`TITLE="${1:-}"`", sem escaping intermediário.
- **Análise:** A linha está byte-idêntica à evidência original do relatório (`:44` na época, `:61` hoje após inserções acima). O delimitador `|` continua sendo exatamente o caractere que quebra a substituição quando presente no título, e `&` segue expandindo para o texto casado. Os três commits pós-janela no arquivo — `e3edd7b` (ADRs duplicados), `59b9db2` (diretório vazio) e `ef69da3` (parsing octal + `BASH_SOURCE` unbound, 2026-09-17) — não tocam o escaping. `ef69da3` alterou apenas `:39`: "`NEXT=$(printf "%03d" $(( 10#${LAST:-0} + 1 )))`". **O delta deste pass passou pelo arquivo e não corrigiu o defeito marcado como corrigido há sete semanas.**

### 3. `agent-frontend-reviewer-body-type-safety-and-code-quality-hardcodes-react-ts-identifiers-proptypes-react-changeevent-hocs`

- **Veredito:** ✅ **Feito**
- **Commit examinado:** `b4e219f` — `refactor(agents): delegate shared context, extract stack-prescriptive bodies`
- **Evidência:** `agents/frontend-reviewer.md:110` — "Apply whatever type discipline the project has adopted — a type system, a runtime prop/schema validator, or documented contracts:"; `:112` — "Component inputs with no declared contract — e.g. missing TypeScript interfaces, PropTypes, or Vue `defineProps` types"; `:118` — "KISS violations: abstraction layers that add no behavior — e.g. wrappers wrapping wrappers (HOC chains)".
- **Análise:** O commit da janela reescreveu §10 Type Safety e §11 Code Quality em forma framework-neutra, rebaixando `PropTypes`, `React.ChangeEvent<HTMLInputElement>` e HOC a exemplos após um critério genérico. Sobreviveu aos quatro commits posteriores no arquivo.

### 4. `agent-mobile-developer-description-frontmatter-enumerates-five-stacks-swift-kotlin-react-native-expo-flutter-on-identity-surface`

- **Veredito:** ✅ **Feito**
- **Commit examinado:** `b4e219f`
- **Evidência:** `agents/mobile-developer.md:3` — "`description: Implements mobile features for iOS and Android, whether the project is native or cross-platform. Detects the project's mobile stack and follows its platform conventions.`"
- **Análise:** O diff da janela substituiu a linha antiga (`— native (Swift/Kotlin) and cross-platform (React Native, Expo, Flutter)`) pela redação atual. Nenhum commit posterior reintroduziu a enumeração.

### 5. `agent-product-analyst-other-trackers-still-asana-clickup-monday-ungated`

- **Veredito:** ✅ **Feito**
- **Commit examinado:** `b4e219f`
- **Evidência:** `agents/product-analyst.md:179` — "**Any other tracker** (ClickUp, Trello, Asana, Azure Boards, Shortcut, …) has no skill — do not improvise one and do not silently fall back to local files."
- **Análise:** O gate existe e é explícito: trackers sem skill são nomeados, improviso é proibido e há fallback declarado para `docs/backlog/` em `:182`.

### 6. `auto-no-skill-name-uniqueness-check`

- **Veredito:** ✅ **Feito**
- **Commit examinado:** `c7535b7` — `ci: close validator and enforcement gaps, repair the rotation helper`
- **Evidência:** `helpers/agent-lint.sh:330` — "`check_skill_name_uniqueness() {`"; `:337` — "`ERRORS+=("  · duplicate skill name '${dup}' declared in: ${files}")`"; invocação em `:489`.
- **Análise:** `git log -S'check_skill_name_uniqueness' -- helpers/agent-lint.sh` devolve um único commit, `c7535b7`, dentro da janela. Empurra para `ERRORS` (bloqueante), não para warnings.

### 7. `flow-commit-md-and-update-md-are-only-2-commands-without-current-context-load-but-both-touch-git-state`

- **Veredito:** ✅ **Feito**
- **Commit examinado:** `bbb311a`
- **Evidência:** `CLAUDE.md:252` — "**Exception — commands that do NOT load `current-context`:** … These six are the complete list — verify with `grep -L current-context commands/*.md`."
- **Análise:** O commit corrigiu a lista contra o próprio `grep -L` e inseriu `/devteam:health-check` na tabela canônica e nos dois READMEs. Verificação no HEAD: o grep devolve exatamente `commit, health-check, learn, rule, sync-rules, update`.

### 8. `flow-pre-tool-use-dispatcher-no-mention-of-sub-script-order-convention-asymmetric-with-stop-dispatcher`

- **Veredito:** ✅ **Feito**
- **Commit examinado:** `bbb311a` (criou a seção) + `7736e20` (resolveu a colisão de prefixo)
- **Evidência:** `CLAUDE-md/hooks.md:48` — "`### PreToolUse Hook Sub-script Convention`"; `:57` — "Add a **lowercase letter suffix** (`02b-`, `02c-`, …) instead." Colisão desfeita em disco: `02-graphify-hint.sh`, `02b-telemetry.sh`, `02c-full-suite-guard.sh`.
- **Análise:** Os dois eixos do achado fecharam dentro da janela. A migração para `CLAUDE-md/hooks.md` em `2b436ea` é relocação, não reversão.

### 9. `flow-readme-sync-ci-gate-checks-only-section-count-and-50pct-line-threshold-not-body-content-passes-while-section-bodies-diverge`

- **Veredito:** ✅ **Feito**
- **Commit examinado:** `c7535b7` (+183/−22 no arquivo)
- **Evidência:** `.github/scripts/ci/02-readme-sync.sh:137-139` — "`compare_exact "code fences" …`" / "`compare_exact "table rows" …`" / "`compare_exact "links" …`"; `:34-35` — "`SECTION_PCT=10`" / "`SECTION_FLOOR=3`".
- **Análise:** O gate antigo (`grep -c "^## "` + `THRESHOLD=$(( EN_LINES / 2 + 1 ))`) deu lugar a um extrator AWK que compara o esqueleto ordenado de headings e, por seção, fences/linhas de tabela/links em igualdade exata. Nenhum commit tocou o arquivo desde então.

### 10. `flow-readme-sync-ci-hardcodes-three-doc-pairs-no-glob-discovery-any-new-pt-br-translation-pair-silently-unchecked`

- **Veredito:** ✅ **Feito**
- **Commit examinado:** `c7535b7`
- **Evidência:** `.github/scripts/ci/02-readme-sync.sh:192` — "`done < <(find . -name '*.pt-BR.md' -not -path './.git/*' … | sort)`".
- **Análise:** As três chamadas literais `check_pair` sumiram e deram lugar a descoberta por glob, com falha explícita quando falta o par EN. O refinamento posterior já registrado (`ref-readme-sync-gate-discovers-only-pt-br-suffix-blind-to-inverted-en-suffix-pair`) é defeito novo do mecanismo de descoberta, não reversão.

### 11. `flow-telemetry-stop-05-runs-after-04-notifier-but-no-fast-path-skip-when-DEVTEAM_NO_CHANGES-is-1`

- **Veredito:** ✅ **Feito**
- **Commit examinado:** `cc28900` — `fix(hooks): gate, decompose and harden the lifecycle dispatchers`
- **Evidência:** `scripts/hooks/stop/05-telemetry.sh:39-42` — "`if [ "${DEVTEAM_NO_CHANGES:-0}" = "1" ]; then`" / "`    bash "$TELEMETRY_SEND" --flush 2>/dev/null || true`" / "`    exit 0`".
- **Análise:** O guard existe e o dispatcher continua exportando a variável (`scripts/hooks/stop.sh:32`). O arquivo foi desativado em `ba39c86` e reativado em `156771b`, mas o fast path sobreviveu intacto. O `--flush` que permanece é deliberado — é o único caminho de entrega dos eventos enfileirados pelo PreToolUse.

### 12. `ref-claude-md-130-agent-creator-points-to-external-claude-skills-path-shipped-by-host-not-by-repo-no-validator-checks-the-path-exists-at-runtime-and-orphan-scan-cannot-cover-it`

- **Veredito:** ✅ **Feito**
- **Commit examinado:** `bbb311a`
- **Evidência:** `CLAUDE.md:196` — "`.claude/skills/agent-creator/SKILL.md` — tracked in this repo, but `.claude/` is stripped from the package by `scripts/lib/strip-tarball.sh`, so it never reaches an installed project."
- **Análise:** A inverdade factual ("global Claude skill — **not in this repo**") foi removida. `git log -S'global Claude skill' -- CLAUDE.md` confirma `bbb311a` como o commit que apagou a string, sem reintrodução.

### 13. `ref-claude-md-file-structure-scripts-enumeration-omits-check-updates-rollback-validate-commit-msg-three-shipped-runtime-scripts`

- **Veredito:** ✅ **Feito**
- **Commit examinado:** `bbb311a`
- **Evidência:** `CLAUDE.md:321` — "`│   ├── install.sh · update.sh · rollback.sh   ← install / update / rollback lifecycle`"; `:326-327` — "`fix-symlinks.sh · check-updates.sh (shim) · new-adr.sh`" / "`graphify-refresh.sh · validate-commit-msg.sh · reuse-lint.sh · design-token-lint.sh`".
- **Análise:** A linha única virou um bloco de 28 linhas cobrindo os três scripts faltantes, toda a máquina de provedores e o conteúdo de `scripts/lib/`. Os 32 commits posteriores em `CLAUDE.md` apenas acrescentaram entradas.

### 14. `skill-mobile-ios-and-android-wrapper-pattern-first-instruction-is-load-ios-hig-or-material-design-doubling-token-cost-251-and-256-lines-total-instead-of-218-and-221-net-loss-vs-loading-the-large-skill-directly`

- **Veredito:** ✅ **Feito**
- **Commit examinado:** `519ca7e` — `feat(skills): add extraction targets, close domain gaps, fix skill defects`
- **Evidência:** `skills/mobile/ios/SKILL.md:10` — "The **design** half lives in `skills/mobile/ios-hig/SKILL.md` … Load it **only when the task touches UI**"; `agents/mobile-developer.md:72` — "**Gate 2 — does the task touch UI?**".
- **Análise:** Os dois defeitos compostos fecharam: o wrapper não abre mais mandando carregar a referência grande, e a regra cross-platform "Load **both** platform skill pairs" virou roteamento de dois portões por plataforma. Custo atual para tarefas não-UI: 38 e 40 linhas, contra 251/256 antes.

### 15. `token-agent-path-prefix-redundant`

- **Veredito:** ✅ **Feito**
- **Commit examinado:** `6919564` — `refactor(commands,scripts): remove cross-cutting duplication, close the size gate`
- **Evidência:** `commands/backend.md:12` — "**Agent base path:** `.claude/agents/dev-team/` — the agents named below all live there, one file per agent name; spawn each by name with the Task tool."
- **Análise:** Medido em git: **73** ocorrências do prefixo em `commands/` no pai do commit, **21** logo após, **23** no HEAD — o crescimento de 2 vem de dois comandos novos (`relayout.md:8`, `seo.md:8`), cada um com uma única declaração de base path.

### 16. `token-current-context-block-deduplication`

- **Marca original:** ✅ Executed 2026-07-31
- **Veredito:** 🟡 **Parcialmente feito**
- **Commit examinado:** `6919564`
- **Evidência:** `commands/backend.md:6` — "Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt."
- **O que foi feito:** os três parágrafos copiados (ver `git show 6919564^:commands/backend.md`, linhas 1–5) colapsaram numa única linha, ~35% mais curta.
- **O que falta:** a deduplicação em si. O problema registrado é "Copy-paste preamble instead of a shared include", e essa linha é hoje **byte-idêntica em 23 arquivos** (`adr.md:6`, `architect.md:6`, `audit.md:6`, `backend.md:6`, `dba.md:6`, `design.md:6`, `devops.md:6`, `docs.md:7`, `fix.md:6`, `frontend.md:6`, `fullstack.md:6`, `mobile.md:6`, `plan.md:6`, `pr.md:7`, `push.md:7`, `qa.md:6`, `refactor.md:6`, `relayout.md:6`, `review.md:6`, `security.md:6`, `seo.md:6`, `setup.md:6`, `tester.md:6`) contra **20** antes da correção — a contagem de cópias **subiu**. A mensagem do commit assume a recusa ("No include mechanism was invented — these are prompt files a model reads top to bottom"), o que é defensável, mas significa que o sub-escopo de deduplicação nunca foi executado: só o custo por cópia caiu.

---

## Nota sobre as duas 🔴

Nenhuma das duas é uma descoberta deste pass, e essa é a observação relevante:

| Fingerprint | Já reaberto antes? | Padrão |
|---|---|---|
| `token-claude-md-426-lines-…` | sim — **quarta** reabertura | `CLAUDE.md` cresce (425 → 602 linhas) enquanto a marca afirma extração |
| `auto-new-adr-sh-sed-title-substitution-…` | não — primeira verificação | nenhum commit jamais tocou o escaping; o delta deste pass passou pelo arquivo |

A segunda é o caso limpo do modo guardião: `scripts/new-adr.sh` foi editado **ontem** (`ef69da3`),
o que prova que o arquivo não é intocável — apenas que ninguém executou a correção marcada como
executada. Um pass que confiasse na marcação nunca teria olhado.

---

## Fase 1b — Validade dos achados abertos

**Critério de amostragem:** (a) todos os fingerprints abertos cujo alvo está no delta de código
(`scripts/install.sh`; nenhum aberto tem `scripts/new-adr.sh` como alvo) — 7 entradas; (b) todos os
19 HIGH e 31 MEDIUM-HIGH abertos; (c) 9 adicionais de LOW/LOW-MEDIUM/MEDIUM escolhidos para cobrir
os 8 prefixos do banco. **Cobertura: 63 de 117 (54%).**

### Achados do delta de código (`scripts/install.sh`)

| Fingerprint | Estado | Evidência |
|---|---|---|
| `flow-conventional-commits-validate-script-no-husky-or-commit-msg-hook-registration` | Ainda reproduz | `grep -niE 'husky\|lefthook\|commit-msg\|core.hooksPath' scripts/install.sh` → zero linhas |
| `token-install-sh-503-lines-largest-single-script-…` | Ainda reproduz | `wc -l` → **1244** (progressão 503 → 803 → 947 → 1244) |
| `auto-install-heredoc-omits-auto-learn-before-commit` | Ainda reproduz | `scripts/install.sh:1164-1187` — heredoc termina em `"ci_cd_detected": null`; faltam `auto_learn_before_commit`, `work_feedback_active`, `work_feedback_interval_minutes` |
| `gov-repo-gitignore-omits-three-installer-written-entries` | Ainda reproduz | `.gitignore:7-8` traz 2 das 6 entradas de `install.sh:932-937` |
| `token-install-sh-second-unconditional-claude-md-injection-35-lines-every-session` | Ainda reproduz | `scripts/install.sh:866` — "`# ── Step 8b: Inject Commit Rule into project CLAUDE.md ───`" |

O delta tocou `install.sh` e **não fechou nenhum** dos cinco. Dois pioraram: a drift do heredoc
agora é tripla (a chave original mais as duas `work_feedback_*`), e o arquivo cresceu de 947 para
1244 linhas.

### Mudanças de estado

| Fingerprint | Novo estado | Motivo |
|---|---|---|
| `gov-audit-pass-output-uncommitted-with-no-detection-mechanism` | 🟢 **Resolved** | `git show HEAD:docs/reports/_index.md \| grep -cE '^- `[a-z]'` → 241, idêntico à árvore; `git status --porcelain docs/reports/` vazio. Resolvido por `3acaa89` ("docs(reports): add guardian audit passes 2026-08-21 through 2026-09-11"). A cláusula secundária — nenhum hook verifica que `docs/reports/` foi commitado — permanece, mas é sub-escopo distinto. |
| `agent-qa-specialist-in-app-browser-prefix-mcp-claude-browser-nonexistent` | ⚰️ **Obsoleto** | **Premissa refutada.** O namespace `mcp__Claude_Browser__*` existe e coexiste com `mcp__claude-in-chrome__*`; a linha `agents/qa-specialist.md:79` está correta como escrita. O achado era inválido na origem, não corrigido. |

**Mortalidade do pass: 3,2% (2 de 63)** — 1 🟢 + 1 ⚰️.

### Os 61 restantes — ainda reproduzem

Verificados com `path:linha` e trecho literal no HEAD. Destaques por gravidade:

**HIGH (14 de 19 amostrados, todos reproduzindo):**

- `auto-size-limits-claude-md-warning-counted-as-violation-turns-ci-lint-red` — **reprodução direta**: `bash helpers/size-limits.sh` no HEAD imprime `ERRORS — Files exceeding declared limits:` / `⚠ CLAUDE.md: 602 lines (warning threshold: 600)` e **sai 1**. O gate bloqueante de CI está vermelho hoje por um aviso.
- `agent-line-cap-205-documented-in-claude-md-vs-211-enforced-by-size-limits` — `CLAUDE.md:92` diz "enforces 205", `helpers/size-limits.sh:44` diz `AGENT_LIMIT=211`; três agentes estão exatamente em 211.
- `ref-check-updates-shim-and-update-sh-exec-renamed-away-01-check-updates-hook` — `scripts/check-updates.sh:3` faz `exec` para `hooks/pre-tool-use/01-check-updates.sh`, que não existe (`_disabled-01-check-updates.sh`). `/devteam:update` reporta "atualizado" num projeto desatualizado.
- `ref-notifier-documented-as-live-in-four-docs-while-hook-file-is-disabled` — `skills/shared/notifier/SKILL.md:52` documenta `stop/04-notifier.sh`; em disco há `_disabled-04-notifier.sh`.
- `ref-tool-map-tool-rewrites-loaded-but-never-emitted-by-render-provider` — `render_provider.py:742` carrega `tool_rewrites` e o usa apenas como booleano em `:748`; o laço emissor de `:752` itera `idioms`. `CLAUDE.md:67` documenta um rewrite que não existe.
- `skill-orchestration-two-sections-both-numbered-check-5-breaks-cross-refs` — `:213` e `:245` são ambos `### 5.`; as três referências a "check 5" resolvem para seções opostas.
- `flow-learn-nudge-ancestor-test-inverted-in-four-commands` — `commands/merge.md:89` (e `pr.md:148`, `refactor.md:162`): com commits desde o learn o hash **é** ancestral, logo o nudge nunca dispara.
- `flow-pre-tool-use-dispatcher-sigpipe-141-masks-02c-block`, `flow-merge-md-branch-and-tree-resolved-before-worktree-detection`, `flow-review-command-writes-and-commits-while-documented-as-read-only`, `flow-update-sh-codex-slim-guard-dead-branch-false-strip-claim`, `auto-agent-lint-quiz-first-never-scans-commands-dir`, `agent-worktree-cascade-delegates-to-unshipped-claude-md`, `docs-sync-claude-md-102-states-skill-desc-strict-false-…`, `docs-sync-claude-md-effort-key-scope-vs-agent-effort-map`, `docs-sync-telemetry-fresh-install-default-documented-true-…`, `ref-docs-agents-md-tier-column-stale-backend-test-specialist-listed-repetitive`, `skill-token-efficiency-background-mgmt-contradicts-orchestration-discipline`.

**MEDIUM-HIGH (todos os 31 amostrados reproduzem).** Quatro deles pertencem ao mesmo alvo
(`scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`: sed guloso, fallback `composer` sem
qualificador, match por substring sem âncora, escotilha ancorada contra detecção não-ancorada) —
um único arquivo concentra 13% dos MEDIUM-HIGH abertos.

**Progressões medidas (o achado piorou desde o registro):**

| Fingerprint | No registro | No HEAD |
|---|---|---|
| `token-install-sh-503-lines-…` | 503 linhas | **1244** |
| `token-orchestration-skill-377-lines-…` | 377 linhas | **391** |
| `docs-sync-claude-md-coding-agents-list-omits-seo-specialist` | 8 agentes listados | **9** com `## Worktree Isolation` |
| `auto-install-heredoc-omits-auto-learn-before-commit` | 1 chave faltando | **3** |

### Leitura da mortalidade

**3,2% é baixo, e isso não é saúde.** A mortalidade mede quantos achados abertos morreram por
terem sido resolvidos de passagem ou por perda do alvo. Com um delta de dois arquivos em catorze
dias, a taxa próxima de zero reflete **imobilidade do repositório**, não durabilidade do banco — a
mesma leitura registrada em 2026-08-28 e 2026-09-04. Dos dois óbitos, um (`⚰️`) é correção de um
achado que nunca deveria ter entrado no banco, não remediação.

O sinal preocupante é o inverso: **quatro fingerprints abertos mediram pior hoje do que no dia em
que foram registrados.** Um banco cujos achados crescem enquanto a mortalidade cai não está estável
— está parado enquanto a dívida acumula.
