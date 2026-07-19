# Fluxos e Workflows — 2026-05-19

> Sugestões **originais** de melhoria em fluxos, hooks e gates de CI/Stop. Cada item traz
> evidência, motivo, impacto positivo, risco/impacto negativo e recomendação.

---

## F1 — `size-limits.sh` só roda em CI como `--warn-only`; sem paridade no Stop hook  · **HIGH**

**Fingerprint:** `flow-size-limits-sh-ci-only-warn-only-not-in-stop-dispatcher-asymmetric-with-agent-lint-200-cap-never-blocking`

**Evidência:**

- `.github/workflows/ci.yml:28`: `run: bash helpers/size-limits.sh --warn-only` → nunca falha o build.
- `agent-lint.sh` roda em CI (`ci.yml:18`) **e** no Stop (`scripts/hooks/stop/03-agent-lint.sh`); `size-limits.sh` **não** tem sub-script de Stop equivalente.
- `bash helpers/size-limits.sh` reporta **9/17 agentes** acima de 200 linhas (backend-developer 261, frontend-test-specialist 262, setup-assistant 239, devops-specialist 237, security-specialist 234, frontend-developer 232, code-reviewer 228, qa-specialist 208, backend-reviewer 204).

**Motivo:** a regra "Max ~200 lines per agent" (CLAUDE.md, Authoring Standards) **não é aplicada por
nenhum gate bloqueante**. O único checador roda em modo aviso e só em CI — assimétrico com
`agent-lint`, que é bloqueante e roda também localmente no Stop. Resultado: a violação cresce sem
fricção (53% dos agentes já estourados). Distingue-se do fingerprint `ref-size-limits-warn-only-…`
(2026-05-15, marcado ✅) porque o ângulo aqui é a **assimetria de enforcement vs `agent-lint`** e a
**ausência de paridade no Stop**, não a mera existência da flag.

**Impacto positivo:** pressão real para extrair conteúdo de agentes grandes para `references/`/skills
(economia de tokens recorrente); feedback local no Stop evita descobrir o estouro só no PR.

**Impacto negativo / risco:** ligar enforcement bloqueante **hoje** quebraria CI imediatamente (9
agentes já violam). Precisa de um plano de migração: primeiro reduzir os 9, depois flipar para
bloqueante; ou um "baseline" que bloqueia apenas **novas** violações.

**Recomendação:** (1) adicionar `scripts/hooks/stop/03b-size-limits.sh --warn-only` para feedback
local; (2) criar baseline (`.size-baseline`) e fazer o CI bloquear apenas regressões acima do
baseline; (3) cronograma para zerar o baseline.

---

## F2 — Gate de sync de README compara só contagem de seções e 50% de linhas, não conteúdo  · **MEDIUM**

**Fingerprint:** `flow-readme-sync-ci-gate-checks-only-section-count-and-50pct-line-threshold-not-body-content-passes-while-section-bodies-diverge`

**Evidência:** `.github/workflows/ci.yml`, função `check_pair()`:

- Checagem primária: `grep -c "^## "` em cada arquivo e compara **contagens** (`en_count != ptbr_count`).
- Checagem secundária: diferença de linhas `> EN_LINES/2 + 1` (limiar de 50%).

**Motivo:** o gate só detecta (a) seção adicionada/removida em um idioma e (b) sumiço de blocos
grandes (>50%). Ele **passa** quando uma seção existe nos dois arquivos mas o **corpo diverge** — por
exemplo, EN documenta um novo flag/comportamento dentro de uma seção existente e o PT-BR fica para
trás (drift de conteúdo, não de estrutura). A "README Sync Rule" do CLAUDE.md exige paridade de
conteúdo, mas o gate só garante paridade estrutural grosseira → **falsa confiança**.

**Impacto positivo:** detecção de divergência de conteúdo intra-seção; PT-BR deixa de acumular
defasagem silenciosa entre releases.

**Impacto negativo / risco:** comparar conteúdo entre idiomas é difícil (headers/texto traduzidos).
Uma checagem ingênua geraria falsos positivos. Mitigação realista: comparar **âncoras
language-agnostic** — número de blocos de código, número de links, número de itens de lista, e
nomes de flags/identificadores (que não são traduzidos) por seção.

**Recomendação:** estender `check_pair()` para comparar, por seção, a contagem de fences ```` ``` ````,
de links `](`, e de tokens não-traduzíveis (ex.: `preferences.json`, nomes de flags). Manter
`--warn` no início para calibrar antes de tornar bloqueante.

---

## F3 — Stop dispatcher faz glob `*.sh` sem allowlist nem toggle por sub-script  · **MEDIUM**

**Fingerprint:** `flow-stop-dispatcher-globs-all-sh-no-allowlist-or-per-subscript-toggle-any-dropped-file-auto-executes`

**Evidência:**

- `scripts/hooks/stop.sh:32`: `for script in "$HOOKS_DIR"/*.sh; do … done` — executa **tudo** em `stop/`.
- Diretório atual: `01-session-summary`, `02-orphan-skill-scan`, `02b-orphan-template-scan`, `03-agent-lint`, `04-notifier`, `05-telemetry`.

**Motivo:** o dispatcher não tem allowlist nem flag de habilitação por sub-script. Qualquer arquivo
`.sh` solto na pasta (um rascunho, um `.sh.bak` renomeado, um sub-script meio-pronto de um PR) passa
a rodar a cada Stop, sem opt-in. Também não há forma de o usuário desabilitar um sub-script
específico (ex.: telemetria off já existe via prefs, mas e desligar o notifier?) sem deletar o
arquivo — que o próximo `update.sh` restaura. Isso interage com R3 (`02b-` undocumented): a convenção
não controla o que roda; o glob controla.

**Impacto positivo:** previne execução acidental de scripts não revisados; dá controle granular ao
usuário (paridade com a suppressão por prefs que já existe para notifier/telemetria).

**Impacto negativo / risco:** introduzir allowlist adiciona um ponto de manutenção (esquecer de
registrar um sub-script novo faz ele não rodar — falha silenciosa na direção oposta). Mitigar com
um aviso quando houver `.sh` em `stop/` fora da allowlist.

**Recomendação:** trocar o glob por uma allowlist explícita no topo de `stop.sh` (array de
sub-scripts na ordem desejada) **ou** restringir o glob a um padrão estrito
(`[0-9][0-9]*-*.sh`) e logar arquivos ignorados.

---

## Itens reverificados (já no índice; ver Guardian)

`flow-workflow-detection-skill-only-loaded-by-software-architect`, `flow-telemetry-*` e
`flow-pre-tool-use-dispatcher-no-mention-of-sub-script-order-convention` continuam **🔴 não feitos**
(0 commits na janela). Não repropostos.
