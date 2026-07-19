# Fluxos e Workflows — 2026-05-22

> 3 sugestões originais sobre validação automática, CI e scripts. Cada item traz **evidência**, **motivo** e **impactos positivos e negativos**. Deduplicadas contra os 449 fingerprints do banco.

---

## F1 — Nenhum validador cruza a coluna **Model** do `docs/agents.md`/`docs/agents.pt-BR.md` contra o frontmatter dos agentes → a discrepância sobrevive há 4 dias invisível ao CI

**Severidade:** MEDIUM
**Fingerprint:** `auto-no-validator-cross-checks-docs-agents-md-model-column-against-agent-frontmatter-discrepancy-survived-four-days-unseen`

**Evidência** — `helpers/agent-lint.sh:54-71` valida o `model:` **do frontmatter** contra a lista permitida:

```bash
VALID_MODELS=("claude-opus-4-7" "claude-sonnet-4-6" "claude-haiku-4-5-20251001")
# … valida que agents/<x>.md tem um model: válido
```

…mas **nada** lê o `docs/agents.md` (a referência canônica) e compara a coluna **Model** lá declarada com o `model:` real do agente. O `README sync check` do CI (`ci.yml`) compara apenas **contagem de seções** e **contagem de linhas** entre EN e pt-BR — nunca o conteúdo das células.

**Motivo:** é exatamente **por isso** que o erro de `technical-writer` (Haiku, deveria ser Sonnet) e `setup-assistant` (Sonnet, deveria ser Opus) persiste há quatro dias e ainda foi espelhado no pt-BR (ver `01/R1`). Há um validador que confere o frontmatter (`agent-lint`), e há um validador que confere a estrutura da tradução (`README sync`), mas **não há ponte** entre a tabela canônica e a fonte de verdade (o frontmatter). Um achado de drift como esse deveria ser **mecanicamente impossível de persistir**. O banco tem `auto-no-frontmatter-tools-validator` (já implementado) e `auto-skill-frontmatter-validator`, mas nenhum sobre **cross-check doc↔frontmatter**.

**Impacto positivo da correção:** um bloco de ~12 linhas em `agent-lint.sh` — extrair `| \`<agente>\` | … | <MODEL> |` do `docs/agents.md`, mapear o rótulo (`Opus`/`Sonnet`/`Haiku`) para o string real e comparar com o frontmatter — transforma esse drift num erro de CI bloqueante. Cobre os dois idiomas se rodado sobre os dois arquivos. Custo-benefício excelente: pequeno, determinístico, fecha permanentemente uma classe de bug que já reincidiu.

**Impacto negativo / risco:** acopla o linter ao formato da tabela do `docs/agents.md` (se a coluna mudar de posição, o parser precisa acompanhar). Mitigável ancorando por cabeçalho de coluna em vez de posição fixa. Há também o risco de o pt-BR usar rótulos traduzidos para o modelo — mas hoje usa "Haiku"/"Sonnet"/"Opus" idênticos ao EN, então o mesmo parser serve.

---

## F2 — O regex "quiz-first" do `agent-lint.sh` só pega `(yes/no)`; **ignora o `(a / b / c)` de múltipla escolha** que a mesma regra proíbe → enforcement parcial dá falsa confiança

**Severidade:** MEDIUM
**Fingerprint:** `auto-agent-lint-quiz-first-regex-only-matches-yes-no-variants-misses-a-b-c-multiple-choice-plain-text-prompts-forbidden-by-same-rule`

**Evidência** — `helpers/agent-lint.sh:112`:

```bash
if grep -qE "\([yY]es[/ ][nN]o\)|\(y[/]n\)|\(yes\|no\)|\( yes / no \)" "$file" 2>/dev/null; then
```

E a regra que ele pretende fazer cumprir (CLAUDE.md, "Quiz-first Rule"):

> Plain text prompts like `(yes / no)` **or `(a / b / c)`** are not allowed.

**Motivo:** o linter detecta apenas variações de yes/no. A própria regra proíbe **também** prompts de múltipla escolha em texto plano como `(a / b / c)` ou `(1 / 2 / 3)` — que devem usar `AskUserQuestion`. Como o linter cobre só metade da regra, um agente pode introduzir um prompt de múltipla escolha plain-text e **passar limpo**, criando a falsa sensação de que a regra está mecanicamente garantida. É um enforcement parcial — pior que ausência, porque inspira confiança indevida. O banco tem `flow-quiz-first-rule-no-lint-validation-of-askuserquestion-adoption` (de quando **não havia** validação); agora **há** validação, mas **incompleta** — um sub-escopo inédito e mais específico.

**Impacto positivo da correção:** estender o regex para capturar padrões `(\s*[a-z0-9]\s*/\s*[a-z0-9]\s*/…)` (duas ou mais opções separadas por `/`) faz o linter cobrir a regra inteira; reduz falsos negativos sem custo de runtime relevante (é CI-only).

**Impacto negativo / risco:** regex de múltipla escolha é mais propenso a **falso positivo** (ex.: `a/b` em "and/or", caminhos `src/a/b`, ou exemplos legítimos dentro de blocos de código). Mitigação: reaproveitar o filtro já existente no script que ignora linhas de bloco de código/`backtick`, e exigir ao menos dois separadores `/` com espaços ao redor para reduzir colisão. Testar contra os 17 agentes atuais antes de ligar como erro.

---

## F3 — `new-adr.sh` injeta o título livre do ADR num `sed -e "s|\[Title\]|$TITLE|g"` → títulos com `|`, `&` ou `\` corrompem ou quebram a substituição

**Severidade:** LOW-MEDIUM
**Fingerprint:** `auto-new-adr-sh-sed-title-substitution-breaks-on-pipe-ampersand-backslash-in-free-form-adr-title-no-escaping`

**Evidência** — `scripts/new-adr.sh:42`:

```bash
sed \
    -e "s/\[NUMBER\]/$NEXT/g" \
    -e "s|\[Title\]|$TITLE|g" \
    -e "s/\[YYYY-MM-DD\]/$TODAY/g" \
    "$TEMPLATE" > "$FILENAME"
```

**Motivo:** `$TITLE` vem de **input livre do usuário** — e a própria CLAUDE.md classifica título de ADR como "Strict free-form input". O delimitador da substituição do título é a barra vertical (`s|…|…|`), então um título contendo `|` (ex.: `"Use S3 | CloudFront para CDN"`) **quebra o `sed`** com erro de comando. Mesmo sem `|`, o lado de substituição do `sed` interpreta `&` (insere o texto casado) e `\` (escapes), corrompendo silenciosamente títulos como `"Migração A&B"` ou caminhos com contrabarra. O `[NUMBER]` e a data são seguros (gerados internamente), mas o `[Title]` é a única injeção de dado externo — e a única não sanitizada. O banco tem achados de robustez de outros scripts (`ref-rollback-script-no-target-version-format-validation`, `auto-curl-no-timeout-update-check`), mas nada sobre injeção em `sed` no `new-adr.sh`.

**Impacto positivo da correção:** escapar o título antes do `sed` (ex.: `TITLE_ESC=$(printf '%s' "$TITLE" | sed -e 's/[&|\\]/\\&/g')` e usar `TITLE_ESC` na substituição) — ou, mais robusto, fazer a substituição com `awk`/parâmetro de ambiente em vez de interpolar no programa `sed` — elimina toda uma classe de falhas e corrupções silenciosas em títulos legítimos.

**Impacto negativo / risco:** baixíssimo. O único cuidado é escapar **na ordem certa** (a contrabarra primeiro) para não duplicar escapes. Recomenda-se um teste rápido com um título contendo `| & \ /` antes de fechar.
