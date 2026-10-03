# Eixo C — Fluxos, comandos e automação — 2026-10-02

Prioridade: os 728 arquivos do delta. As áreas novas desde `ef69da3` concentram os achados —
contas/entitlement (ADR-0029), instaladores de CLI (ADR-0028), `packaging/windows-cli/`, task board.

Todos os achados abaixo foram **reproduzidos executando o script**, não apenas lidos.

---

## HIGH

### `install-cli.sh` aborta na carga: 52 linhas de corpo órfão fora de `main()` com `$SOURCE` indefinido

- **Fingerprint:** `flow-install-cli-orphan-body-outside-main-aborts-every-run`
- **Alvo:** `scripts/install-cli.sh`
- **Evidência:** `scripts/install-cli.sh:163` —
  `if [ ! -f "$SOURCE/scripts/cli/devteam" ] || [ ! -d "$SOURCE/scripts/lib/devteam" ]; then`.
  O commit `2b410af` ("fix(packaging): ship auth-config.json with every CLI distribution")
  acrescentou 52 linhas (`@@ -160,4 +160,56`) **depois** de `hint_current()` e **antes** de
  `main "$@"` (`:215`). O bloco usa `$SOURCE`, `$VERSION`, `$CLI_HOME`, `$BIN_DIR`, `$PYTHON` e
  `$EXIT_CONFLICT` — variáveis em maiúsculas que só existiam na versão anterior ao refactor para
  `main()`, onde hoje são locais minúsculas.
  **Reprodução (HEAD `5e338d9`):**
  ```
  $ bash scripts/install-cli.sh --help
  scripts/install-cli.sh: line 163: SOURCE: unbound variable
  $ bash -n scripts/install-cli.sh    # passa — o lint de sintaxe não pega
  $ python3 -m unittest discover -s tests -p test_install_cli.py
  Ran 9 tests ... FAILED (failures=8)
  ```
- **Problema:** sob `set -u`, o bloco colado executa no top level, antes de `main`, e mata o script
  antes de qualquer instalação. De quebra, a cópia de `auth-config.json` que o commit queria
  adicionar está dentro desse bloco morto — `main()` continua sem ela.
- **Por que importa:** **o canal de instalação macOS/Linux sem Homebrew (ADR-0028) está 100%
  quebrado no HEAD**, inclusive na forma `curl | bash`. Mesmo se a instalação funcionasse, o CLI
  instalado ficaria sem `auth-config.json` e `load_identity` levantaria `EnvError`. Oito dos nove
  testes de `test_install_cli.py` estão vermelhos, o que significa que o gate de CI
  (`.github/scripts/ci/03-python.sh`) está vermelho neste commit — um merge entrou com o CI quebrado.
- **Proposta:** apagar `:163-214` e inserir dentro de `main()`, junto do `cp -R .../devteam`, a linha
  `cp "$source/scripts/lib/auth-config.json" "$stage/lib/auth-config.json"`.
- **Impacto positivo:** restaura um canal de instalação inteiro e devolve 8 testes ao verde.
- **Impacto negativo / risco:** nenhum relevante — é remover bloco morto e mover uma linha. O único
  custo é que `bash -n` não previne a recorrência; só o teste pega, e o teste já existe.
- **Esforço:** Baixo

### `store install` leva `auth-config.dev.json` para o core, e o CLI do core passa a rodar em ambiente `dev`

- **Fingerprint:** `flow-store-install-ships-dev-auth-config-into-core-despite-sr-27`
- **Alvo:** `packaging/windows-cli/build.py`, `scripts/install-cli.sh`, `scripts/lib/devteam/store.py`
- **Evidência:**
  - `packaging/windows-cli/build.py:60-75,109` — `committed_tree` extrai `git archive HEAD` e copia
    `scripts/` inteiro para o payload, **sem** passar por `apply_strip`
  - `scripts/lib/auth-config.dev.json:3` — "Never packaged … a released build embeds prod keys only
    (ADR-0029 SR-27)"
  - `scripts/lib/devteam/entitlement.py:98-101,222-234` — quando presente, o `auth-config.dev.json`
    é mesclado e **sobrescreve** `environment` com `dev`
  - `.github/scripts/ci/04-packaging.sh:852` — o scan de SR-27 só inspeciona a árvore que passou por
    `apply_strip`

  **Reprodução:** `git archive HEAD | tar -x -C /tmp/arch` e então
  `devteam store install --from /tmp/arch` instala em `core/versions/2.48.0/scripts/` os arquivos
  `lib/auth-config.dev.json`, `install.sh` e `install-cli.sh`. Em seguida,
  `python3 core/versions/2.48.0/scripts/cli/devteam auth check --json` retorna `"environment": "dev"`.
- **Problema:** o único gate de SR-27 testa o caminho `apply_strip`. Os canais Windows (payload) e
  `install-cli.sh` (`--from`, tarball da tag) chamam `store install --from` numa árvore não
  stripada, e `store.py` não filtra nada.
- **Por que importa:** o CLI do core é exatamente o que `ag_gate` e os hooks executam. Ele passa a
  resolver o ambiente `dev` — URL e chaves de desenvolvimento — em máquinas de usuário final. Isso
  contradiz uma garantia **documentada** ("prod only") e sai **verde** no CI.
- **Proposta:** chamar `apply_strip` em `committed_tree` (`build.py`) e no `source` de
  `install-cli.sh`, ou fazer `store install` aplicar `apply_strip` ao copiar; estender o scan de
  `04-packaging.sh` ao payload do Windows.
- **Impacto positivo:** SR-27 passa a valer nos três canais, e o payload Windows deixa de carregar
  `install.sh` e `install-cli.sh`, que não têm função ali.
- **Impacto negativo / risco:** `store install --from` num checkout de contribuidor deixa de trazer o
  dev config. É o comportamento correto, mas **muda o fluxo de desenvolvimento** de quem hoje depende
  desse vazamento para testar contra o ambiente dev — precisa de uma flag explícita em troca.
- **Esforço:** Médio

---

## MEDIUM-HIGH

### `release.yml` não tem gate contra `REPLACE-ME` em `auth-config.json` nem reporta `gate_mode`

- **Fingerprint:** `auto-release-workflow-has-no-guard-for-auth-config-placeholders`
- **Alvo:** `.github/workflows/release.yml`
- **Evidência:** `scripts/lib/auth-config.json` — `"supabase_url": "https://REPLACE-ME-PROD.supabase.co"`,
  `"anon_key": "REPLACE-ME-PROD-ANON-KEY"`, `"prod-1": "REPLACE-ME-PROD-ED25519-PUBLIC-KEY-BASE64URL"`;
  o `_comment` diz "filled in at release time" e `entitlement.py:141` define `configured` como falso
  enquanto houver placeholder. `grep -n 'REPLACE-ME\|auth-config\|gate_mode' .github/workflows/release.yml`
  → **vazio**; `04-packaging.sh` só trata do `auth-config.dev.json`.
- **Problema:** nenhum job da tag `v*.*.*` — Homebrew, verify, Windows — preenche nem verifica os
  valores de produção. O ADR-0029 afirma que o build "rejects every token" com placeholders; não há
  código que o faça.
- **Por que importa:** uma tag publicada hoje distribui o CLI nos três canais com login
  **impossível**. Quando `gate_mode` virar `enforce`, todos os usuários ficam bloqueados. Nada falha
  antes disso — a falha aparece no cliente, não no pipeline.
- **Proposta:** um passo no job `bump-homebrew-formula` (ou um job comum em `needs`) que falhe se
  `scripts/lib/auth-config.json` contiver `REPLACE-ME`, e que imprima o `gate_mode` efetivo.
- **Impacto positivo:** bloqueia a publicação de uma release sem identidade configurada; ~5 linhas.
- **Impacto negativo / risco:** real — enquanto os valores de produção não existirem, **toda tag
  falha**, inclusive as de teste. O gate precisa nascer atrás de uma variável de repositório, ou ser
  ativado junto com o primeiro valor real.
- **Esforço:** Baixo

---

## MEDIUM

### O fallback de gate de conta em `install-provider.sh` abre quando não há `auth-gate.sh`

- **Fingerprint:** `flow-install-provider-gate-fallback-fails-open-without-gate-lib`
- **Alvo:** `scripts/install-provider.sh`
- **Evidência:** `scripts/install-provider.sh:118-125` —
  `elif command -v devteam …; if [[ "$_ip_rc" != 0 ]] && printf '%s' "$_ip_out" | grep -q '"gate_mode": *"enforce"'; then … exit 5`.
  **Não existe `else`.** `scripts/lib/auth-gate.sh:11-13` afirma o contrário: sem CLI, ou com crash,
  o modo `enforce` bloqueia (SR-42).
- **Problema:** com o script rodando via `curl` (sem árvore própria) e um tarball antigo sem
  `auth-gate.sh`, há três saídas sem bloqueio: sem `devteam` no PATH não há gate algum; com `devteam`
  e crash ou exit 3/4 o corpo não traz `gate_mode`; e um JSON reformatado quebra o `grep`. Em todos,
  um release em `enforce` se comporta como `allow`.
- **Por que importa:** é exatamente a classe de lacuna que o `CLAUDE.md` registra na Provider Parity
  Rule ("a guarantee that `bind.py` enforces for Claude natively must be enforced for the delegated
  providers through their installers too — ADR-0022 is what that gap cost"), agora no gate de conta.
- **Proposta:** ler o modo pelo `DEFAULT` embutido e falhar fechado quando `AG_DEFAULT_MODE` for
  `enforce`; trocar o `grep` por um parse em python.
- **Impacto positivo:** o fail-closed deixa de depender de formatação de texto e da existência do CLI.
- **Impacto negativo / risco:** em `warn` nada muda. Em `enforce`, instalações via `curl` sem CLI
  passam a ser **bloqueadas** — é o comportamento desejado por SR-42, mas é uma quebra visível para
  quem instala em ambiente sem o CLI no PATH.
- **Esforço:** Baixo

### Guard `02c`: `npm test --` conta como escopo e a suíte completa passa sem bloqueio

- **Fingerprint:** `flow-02c-double-dash-counted-as-scope-lets-npm-full-suite-through`
- **Alvo:** `scripts/hooks/pre-tool-use/02c-full-suite-guard.sh`
- **Evidência:** a regra de `has_scope` (~`:55`) aceita `--filter*|…|--) return 0`.
  **Reprodução** em repositório limpo, sem nenhum arquivo tocado:
  | Comando | Exit |
  |---|---|
  | `npm test` | **2** (bloqueado, correto) |
  | `npm test --` | **0** (passa) |
  | `npm test -- --coverage` | **0** (passa) |
  | `pytest -x` | 2 (bloqueado, correto) |
- **Problema:** `--` é só o separador de argumentos do npm/pnpm/yarn. Sem um seletor **depois** dele,
  a execução continua sendo a suíte inteira.
- **Por que importa:** `npm test -- --coverage`, `-- --watch=false`, `-- --runInBand` são a forma
  mais comum de passar flags ao runner. Nessa forma a suíte completa roda sem nudge, na sessão limpa
  — o caso exato para o qual o guard foi escrito.
- **Proposta:** em `has_scope`, remover `--` da lista de seletores (ou tratá-lo como `-*`) e avaliar
  apenas o que vem depois dele.
- **Impacto positivo:** fecha a forma mais comum de contornar o bloqueio, sem tocar na detecção.
- **Impacto negativo / risco:** o fallback `make … -- ARGS` documentado num comentário (~`:100`)
  passa a exigir `FILTER=`/`TESTPATH=`, o que é uma mudança de contrato para quem usa `make`. Precisa
  de caso novo em `tests/test_pretooluse_hooks.py`.
- **Esforço:** Baixo

### A lista de agentes de review está copiada como regex em dois hooks, sem teste de paridade

- **Fingerprint:** `auto-review-agents-regex-duplicated-in-two-task-board-hooks-no-drift-gate`
- **Alvo:** `scripts/hooks/pre-tool-use/04-task-board.sh`, `scripts/hooks/post-tool-use/01-task-board.sh`
- **Evidência:** `04-task-board.sh:33` e `01-task-board.sh:32` têm, ambos,
  `REVIEW_TYPE_RE='…(qa-specialist|code-reviewer|backend-reviewer|frontend-reviewer)"'`.
  A fonte canônica é `review_triggers.REVIEW_AGENTS` (`scripts/lib/devteam/review_triggers.py:17`),
  e os testes (`tests/test_agent_tasks.py:87`, `tests/test_review_board.py:160`) iteram **só** a
  tupla Python. `grep -rn REVIEW_TYPE_RE tests` → vazio; `agent-lint.sh` valida
  `REVIEW_RESULT_AGENTS`, não os hooks.
- **Problema:** três cópias da mesma lista, e as duas em bash não têm nenhum gate de paridade.
- **Por que importa:** ao adicionar um revisor novo, os hooks continuam sem enxergá-lo. O spawn vira
  "task" comum, nenhuma janela de review abre no task board, **em silêncio** — e o marcador
  `<!-- review-result: findings=N -->` não encontra onde aterrar.
- **Proposta:** um teste que extraia o regex dos dois `.sh` e compare com `REVIEW_AGENTS`; ou
  pré-computar a alternância num arquivo que os dois hooks leiam.
- **Impacto positivo:** o drift passa a falhar no CI; teste de ~15 linhas.
- **Impacto negativo / risco:** nenhum funcional — é um teste a mais. Custo: o teste acopla-se ao
  formato do regex nos `.sh`, então uma refatoração de estilo nos hooks passa a poder quebrá-lo.
- **Esforço:** Baixo

---

## LOW-MEDIUM

### `/devteam:update` no caminho v3 descarta `--run-health-check`, `--skip-health-check` e `--yes`

- **Fingerprint:** `flow-update-md-v3-step-0-drops-documented-health-check-and-yes-flags`
- **Alvo:** `commands/update.md`
- **Evidência:** `commands/update.md:28-29` documenta as duas flags de health-check na tabela de
  argumentos. `:38` — "run `devteam update` …, print its output, and **stop**" — mapeia apenas
  `<version tag>`, `--no`, `--enable-auto` e `--disable-auto`. As linhas que honram as flags
  (`:133-135,172-174`) ficam **depois** do Passo 0, no caminho v2.
- **Problema:** um projeto v3 nunca alcança as linhas que processam as flags.
  `--run-health-check`/`--skip-health-check` são aceitas e ignoradas, `--yes` não é mapeado, e o
  `argument-hint` omite `--enable-auto`/`--disable-auto`.
- **Por que importa:** o caminho **padrão** (v3) não cumpre o contrato da própria tabela de
  argumentos, e o health-check pós-update é silenciosamente pulado.
- **Proposta:** no Passo 0, mapear `--run-health-check` para rodar `/devteam:health-check` depois do
  `devteam update`; documentar `--skip-health-check` e `--yes` como no-op, ou marcar as flags como
  "somente v2".
- **Impacto positivo:** o contrato do comando volta a valer no caminho padrão.
- **Impacto negativo / risco:** nenhum funcional (é texto de comando). Se a opção escolhida for rodar
  o health-check no v3, o `/devteam:update` fica mais lento por padrão.
- **Esforço:** Baixo

---

## LOW

nenhum achado original neste eixo nesta severidade

---

## Descartados por duplicação

- `02c-substring-match-nudge` — porta 3 — `token-02c-full-suite-guard-substring-match-injects-nudge-on-non-test-commands` cobre alvo e causa.
- `02c-composer-scope-ignored` — porta 3 — `flow-02c-composer-fallback-case-ignores-every-scope-qualifier` já descreve o `case` do composer.
- `02c-escape-hatch-anchor` — porta 3 — `flow-02c-escape-hatch-anchored-while-detection-is-substring`, mesmo alvo e mesma causa.
- `dispatchers-sigpipe` — porta 1 — `flow-pre-tool-use-dispatcher-sigpipe-141-masks-02c-block` já registrado, e o dispatcher atual já usa arquivo temporário.
- `release-actions-mutable-tags` — porta 1 — `auto-github-actions-pinned-to-mutable-major-tags` já registrado.
