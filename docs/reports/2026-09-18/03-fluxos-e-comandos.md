# Eixo C — Fluxos, Comandos e Automação — 2026-09-18

**Baseline:** `HEAD` = `ef69da3` · **Prioridade de varredura:** o delta de código
(`scripts/install.sh`, `scripts/new-adr.sh` em `ef69da3`), depois amostragem do resto

---

## HIGH

### O gate de reuse-guidelines no Stop testa um arquivo `.csv` que nada no harness jamais cria

- **Fingerprint:** `auto-stop-03c-reuse-lint-gates-on-csv-registry-while-harness-writes-md`
- **Alvo:** `scripts/hooks/stop/03c-reuse-lint.sh`
- **Evidência:** `scripts/hooks/stop/03c-reuse-lint.sh:11` — "`REGISTRY="$REPO_ROOT/docs/development/reuse-guidelines.csv"`"; `:12` — "`[ -f "$REGISTRY" ] || exit 0`"; `:2` — "`# Stop sub-script: hard-enforce docs/development/reuse-guidelines.csv`". Contra `scripts/reuse-lint.sh:15` — "`REGISTRY="$REPO_ROOT/docs/development/reuse-guidelines.md"`", `scripts/lib/commands.json:50` — "Catalog a mandatory reuse/standardization rule into `docs/development/reuse-guidelines.md`." e a tabela *Canonical Rule Homes* do `CLAUDE.md`, que também diz `.md`. `grep -rn "reuse-guidelines.csv" --include=*.sh --include=*.md --include=*.json .` devolve **exatamente 2 linhas, ambas dentro do próprio `03c`** — nenhum comando, skill ou script escreve um `.csv`.
- **Problema:** a extensão do gate diverge da extensão do registro. O `-f` da linha 12 é sempre falso, então o sub-script sai 0 antes de chegar ao `bash "$SCRIPT" --quiet` da linha 20. Reproduzido em repo sintético com registro `.md` populado (`| no-raw-fetch | code-pattern | fetch\( | src/lib/http.ts |`) e um arquivo violando a regra: `03c exit=0`, sem uma linha de saída.
- **Por que importa:** o `reuse-guidelines` é vendido no `CLAUDE.md` como "mandatory reuse/standardization rules … plus the review/lint gates". O gate de lint do lado do Stop — o único automático — está morto em 100% dos projetos instalados desde que o sub-script existe. `/devteam:rule` e `/devteam:sync-rules` continuam catalogando linhas num registro que nenhuma automação lê.
- **Proposta:** trocar `.csv` por `.md` em `03c-reuse-lint.sh:2` e `:11`; ou, melhor, remover o teste de registro do `03c` e deixar o próprio `reuse-lint.sh:16` decidir (ele já sai 0 quando o registro não existe), eliminando a segunda cópia do caminho.
- **Impacto positivo:** reativa o único gate mecânico do registro de reuso; elimina uma das duas cópias do caminho (a segunda cópia foi exatamente o que permitiu a divergência).
- **Impacto negativo / risco:** projetos que já têm um `reuse-guidelines.md` populado passam a receber avisos/bloqueios de `reuse-lint.sh` que nunca viram antes — pode haver pico de falsos positivos no primeiro Stop, e `reuse-lint.sh` ainda calcula `DIFF_RANGE` como `main...HEAD` por padrão, o que precisa ser validado antes de promover.
- **Esforço:** Baixo

### `path_rewrites` move `docs/development/` no texto renderizado, mas os scripts embarcados continuam com o caminho literal

- **Fingerprint:** `flow-path-rewrites-move-docs-development-but-shipped-scripts-hardcode-it`
- **Alvo:** `scripts/lib/tool-map.json`
- **Evidência:** `scripts/lib/tool-map.json` — `"opencode": { "path_rewrites": { "docs/development/": "docs/" } }` e o mesmo par em `codex`; `scripts/lib/render_provider.py:95-99` — "`for old_prefix, new_prefix in rewrites.items(): result = result.replace(old_prefix, new_prefix)`". Contra `scripts/new-adr.sh:14` — "`ADR_DIR="docs/development/adrs"`", `scripts/reuse-lint.sh:15` — "`REGISTRY="$REPO_ROOT/docs/development/reuse-guidelines.md"`", `scripts/hooks/stop/03e-adr-gap-check.sh:21` — "`grep -qE 'docs/development/adrs/adr-[0-9]+.*\.md$'`". Renderizado em `.codex/skills/devteam-adr/SKILL.md:29-34`: "run its Check Before Creating step against `docs/adrs/`" … "place it in `docs/adrs/`" … seguido de `bash .dev-team-agents/scripts/new-adr.sh "$ARGUMENTS"`. `grep -rno "docs/development/[a-z0-9./-]*" agents/ commands/ skills/` conta 31 referências a `reuse-guidelines.md` e 20 a `adrs/`.
- **Problema:** o rewrite é textual e cego: atinge as ~115 referências em prosa, mas não os três scripts shell que o harness embarca e que codificam o caminho antigo. Em opencode e Codex, o corpo do comando manda checar/gravar em `docs/adrs/` e `docs/reuse-guidelines.md`, enquanto o script que ele invoca na linha seguinte grava em `docs/development/adrs/` e o lint lê `docs/development/reuse-guidelines.md`.
- **Por que importa:** em `/devteam:adr` sob opencode/Codex o passo *Check Before Creating* varre um diretório que o script nunca popula — logo sempre vazio, logo todo ADR é criado como se fosse o primeiro, que é exatamente o cenário de duplicata que o passo existe para impedir. E o `03e-adr-gap-check.sh` procura ADRs num diretório que o texto renderizado diz não ser o certo. São duas afirmações factualmente falsas entregues ao agente em dois dos três provedores suportados.
- **Proposta:** ou aplicar o mesmo `path_rewrites` aos scripts no momento do render/instalação, ou (mais simples e reversível) tornar o caminho um parâmetro: `ADR_DIR="${DEVTEAM_DOCS_DIR:-docs/development}/adrs"` e equivalente em `reuse-lint.sh`/`03e`, com o instalador de cada provedor exportando o prefixo.
- **Impacto positivo:** elimina o split-brain de caminhos em 2 de 3 provedores e cerca de 51 referências que hoje apontam para onde nenhum script escreve.
- **Impacto negativo / risco:** introduz uma variável de ambiente nova no contrato instalador→script (mais uma coisa a manter em sincronia); projetos opencode/Codex já instalados que criaram ADRs em `docs/development/adrs/` via script vão precisar de migração manual se o prefixo mudar de lado.
- **Esforço:** Médio

---

## MEDIUM-HIGH

### O fallback `${BASH_SOURCE[0]:-$0}` de `ef69da3` resolve para o cwd e faz o instalador dar `source` num arquivo do projeto do usuário

- **Fingerprint:** `auto-install-sh-bash-source-fallback-resolves-to-cwd-and-sources-project-lib`
- **Alvo:** `scripts/install.sh`
- **Evidência:** `scripts/install.sh:51` — "`_INSTALL_SH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"`"; `:52` — "`if [ -f "$_INSTALL_SH_DIR/lib/state.sh" ]; then`"; `:54` — "`source "$_INSTALL_SH_DIR/lib/state.sh"`". No caminho documentado (`curl … | bash`), `$0` é literalmente `bash`, então `dirname` devolve `.` e `cd .` resolve para o **cwd**, que é o `PROJECT_ROOT` do usuário. Reproduzido: projeto sintético com um `lib/state.sh` próprio, prólogo do instalador (`head -140`) piped para `bash` → `!!! HIJACKED: project-local lib/state.sh was sourced by the installer` / `state_set NO-OP from project file` / `_INSTALL_SH_DIR=/tmp/pj`.
- **Problema:** o fallback responde à pergunta errada. Quando `BASH_SOURCE` está vazio sabe-se com certeza que **não existe** um arquivo-irmão, e o correto é pular o `source`; em vez disso o script passa a sondar o diretório do projeto-alvo. Um `lib/state.sh` qualquer no repositório do usuário é executado no contexto do instalador e sobrescreve `state_get`/`state_set`/`state_migrate_legacy` — as mesmas funções pelas quais o Step 9 grava `installed_version`, segundo o comentário de `:44-46`.
- **Por que importa:** é execução de código arbitrário do repositório-alvo durante o `curl | bash` documentado, mais um modo de falha silencioso do `installed_version` idêntico ao que o comentário de `:41-46` diz ter sido corrigido antes. O commit `ef69da3` trocou um erro barulhento (`unbound variable`) por um caminho silencioso.
- **Proposta:** substituir por `_INSTALL_SH_DIR=""; [ -n "${BASH_SOURCE[0]:-}" ] && _INSTALL_SH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"` e condicionar o `if` a `[ -n "$_INSTALL_SH_DIR" ] && [ -f … ]`.
- **Impacto positivo:** fecha o vetor de `source` de arquivo do projeto e restaura o comportamento pretendido (piped ⇒ sempre o fallback embutido), sem reintroduzir o `unbound variable`.
- **Impacto negativo / risco:** duas linhas a mais num prólogo já denso; quem executar o instalador por um wrapper exótico que zere `BASH_SOURCE` mas tenha um `lib/` válido ao lado perde o `source` real e cai no fallback (que, pelo próprio comentário, é funcional).
- **Esforço:** Baixo

---

## MEDIUM

### A CI nunca executa `install.sh` nem `new-adr.sh` — o único gate shell é o shellcheck, cego para as duas classes de bug corrigidas em `ef69da3`

- **Fingerprint:** `auto-ci-never-executes-install-sh-nor-new-adr-sh-only-shellcheck-gate`
- **Alvo:** `.github/workflows/ci.yml`
- **Evidência:** `.github/scripts/ci/01-lint.sh:92-93` — "`blocking "shellcheck scripts + helpers" \`" / "`find scripts helpers -name '*.sh' -exec shellcheck -x {} +`"; `.github/scripts/ci/provider/40-install-fixture.sh:19-21` — "`if [ "$PROVIDER" = "claude" ]; then`" / "`echo "claude fixture install: skipped (Claude installer downloads from network; covered by contract.sh against staging)"`" / "`exit 0`"; `.github/scripts/ci/slim-bootstrap.sh:40` — "`"scripts/new-adr.sh"`" aparece apenas na `SLIM_KEEP_LIST` (asserção de existência). `grep -rn "install\.sh\|new-adr" .github/scripts/ci/` só devolve comentários e essa entrada de lista.
- **Problema:** nenhum script shipped é **executado** pela CI sob sua invocação documentada. Os dois defeitos de `ef69da3` são exclusivamente de runtime: `bash -n /tmp/adr-old.sh` sai 0 ("syntax valid"), e só a execução revela `line 36: 008: value too great for base (error token is "008")` — reproduzido criando `adr-001..adr-008` e rodando a versão `ef69da3~1`. O mesmo vale para o `unbound variable` de `install.sh`, que shellcheck não modela.
- **Por que importa:** a CI já tem o molde (`40-install-fixture.sh` instala de verdade para opencode e Codex) e ainda assim dois bugs de runtime atravessaram a esteira inteira num único commit. `new-adr.sh` é offline, determinístico e roda em menos de um segundo — é o caso mais barato possível de smoke e não tem nenhum.
- **Proposta:** acrescentar ao job `lint` um step que roda `new-adr.sh` em `mktemp -d` nove vezes seguidas (cobre a faixa 001→009, onde o octal morde) e valida os nomes gerados; e um step que faz `cat scripts/install.sh | DEVTEAM_NONINTERACTIVE=1 bash` com flag de dry-run (ou, sem ela, apenas o prólogo até o primeiro download) para exercitar a resolução de `_INSTALL_SH_DIR` sem rede.
- **Impacto positivo:** os dois bugs de `ef69da3` teriam falhado a CI; custo marginal de ~2 s por run, sem rede.
- **Impacto negativo / risco:** exige uma flag de dry-run em `install.sh` (superfície nova a manter) ou aceitar cobertura só do prólogo; um smoke de `new-adr.sh` cria arquivos e precisa de isolamento cuidadoso para não sujar o checkout.
- **Esforço:** Médio

---

## LOW-MEDIUM

### `99b-archive-index.sh` grava o carimbo do dia mesmo quando a rotação falhou, e engole o erro

- **Fingerprint:** `auto-99b-archive-index-writes-daily-stamp-even-when-rotation-failed`
- **Alvo:** `scripts/hooks/stop/99b-archive-index.sh`
- **Evidência:** `scripts/hooks/stop/99b-archive-index.sh:44` — "`OUTPUT="$(bash "$SCRIPT" 2>&1)" || OUTPUT=""`"; `:46-47` — "`mkdir -p "$STAMP_DIR" 2>/dev/null || true`" / "`printf '%s\n' "$TODAY" > "$STAMP_FILE" 2>/dev/null || true`"; `:50` — "`[ -n "$OUTPUT" ] || exit 0`". Reproduzido com um `helpers/archive-index.sh` que faz `exit 7`: run 1 → `exit=0`, `stamp: 2026-09-18`; run 2 no mesmo dia → `exit=0` (curto-circuito do gate diário).
- **Problema:** o carimbo é escrito incondicionalmente, antes de qualquer verificação de sucesso, e o `|| OUTPUT=""` destrói tanto o status de saída quanto o stderr. Uma rotação que falha fica indistinguível de uma que não tinha nada a rotacionar, e o gate `:33` impede qualquer nova tentativa no mesmo dia.
- **Por que importa:** a rotação dos 90 dias é a única defesa contra o crescimento de `docs/reports/_index.md` (687 linhas hoje). Se `archive-index.sh` quebrar — por mudança de formato do índice, `date` incompatível, ou qualquer erro sob o `set -euo pipefail` dele —, o banco cresce indefinidamente e ninguém fica sabendo, porque o sub-script reporta sucesso todo dia.
- **Proposta:** capturar o código de saída (`RC=0; OUTPUT="$(bash "$SCRIPT" 2>&1)" || RC=$?`), só gravar o carimbo quando `RC -eq 0`, e imprimir uma linha em stderr quando `RC -ne 0` (mantendo `exit 0`, para não bloquear o Stop).
- **Impacto positivo:** torna visível uma falha hoje 100% silenciosa e permite nova tentativa no mesmo dia em vez de queimar 24 h.
- **Impacto negativo / risco:** se `archive-index.sh` passar a falhar de forma persistente, o usuário vê a mesma mensagem em **todo** Stop (o gate diário deixa de suprimi-la) — o que é o objetivo, mas é ruído novo numa superfície hoje muda.
- **Esforço:** Baixo

---

## Descartados por duplicação

| Candidato | Porta | Fingerprint colidente |
|---|---|---|
| `new-adr.sh:58` — `sed -e "s\|[Title]\|$TITLE\|g"` injeta título livre sem escapar `\|`, `&`, `\` | 1 (literal) | `auto-new-adr-sh-sed-title-substitution-breaks-on-pipe-ampersand-backslash-…` (verificado 🔴 na Fase 1 deste pass) |
| `soften_plan_gate` (`render_provider.py:129-130`) remove `Task: $ARGUMENTS` nos comandos `opt_out` | 3 (3/3) — e já **refutado por evidência** no índice (`:546`); confirmado no HEAD: nenhum dos 9 `opt_out` carrega a linha, `re.sub` é no-op | linha `:546` do `_index.md` |
| `install.sh` com 1244 linhas, sem decomposição | 5 (estado) | `token-install-sh-503-lines-largest-single-script-not-fragmented-…` |
| `03e-adr-gap-check.sh` não enxerga dependências já staged/commitadas | 5 (estado) | `auto-adr-gap-check-dependency-signal-blind-to-staged-and-committed-changes` |
| `reuse-lint.sh:20-23` deriva `DIFF_RANGE` de `main...HEAD` sem filtro de escopo | 3 (2/3 — mesma causa-raiz e remediação) | linha `:540` do `_index.md`, "cinco reviewers com `git diff main...HEAD` sem filtro" |
| `helpers/archive-index.sh` sem trigger / escopo só do índice | 1 + 3 | `flow-helpers-archive-index-sh-orphan-of-hook-…` e `token-archive-index-rotates-index-sections-only-report-directories-never-pruned` |
| `01-lint.sh` não roda shellcheck em `.github/scripts/ci/**` | 3 — já registrado como **descartado por mérito** (`:548`) | linha `:548` do `_index.md` |
