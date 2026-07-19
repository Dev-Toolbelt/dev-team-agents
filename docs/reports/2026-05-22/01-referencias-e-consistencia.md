# Referências e Consistência — 2026-05-22

> 3 sugestões originais. Cada item traz **trecho/evidência**, **motivo** e **impactos positivos e negativos** da correção proposta. Todas foram cruzadas contra o banco de 449 fingerprints (`_index.md`) e são inéditas.

---

## R1 — A "README Sync Rule" propagou um **erro** para a tradução: `docs/agents.pt-BR.md` espelha a coluna Model errada do `docs/agents.md`

**Severidade:** MEDIUM
**Fingerprint:** `ref-docs-agents-pt-br-mirrors-wrong-model-column-from-agents-md-sync-rule-faithfully-propagated-the-error-both-canonical-refs-now-wrong`

**Evidência** — as duas referências canônicas, lado a lado:

```
docs/agents.md:26       | `technical-writer` | … | SUPPORT | Haiku |
docs/agents.pt-BR.md:26 | `technical-writer` | … | SUPPORT | Haiku |
docs/agents.md:27       | `setup-assistant`  | … | SETUP   | Sonnet |
docs/agents.pt-BR.md:27 | `setup-assistant`  | … | SETUP   | Sonnet |
docs/agents.pt-BR.md:79 | "…Atribuído ao Haiku para eficiência de custo…"
```

Frontmatter real: `technical-writer` = `claude-sonnet-4-6`, `setup-assistant` = `claude-opus-4-7`.

**Motivo:** o achado de 2026-05-20 (`ref-docs-agents-md-model-column-wrong-…`) tratava apenas do arquivo **EN**. A releitura desta passada confirma que o **mesmo erro existe no arquivo pt-BR** — porque a "README Sync Rule" da CLAUDE.md exige que toda mudança no EN seja refletida no pt-BR, e a tradução foi feita fielmente, **inclusive replicando o dado errado**. É um caso ilustrativo de uma regra de sincronização que garante "mesmas seções nos dois idiomas" mas **não** garante "mesmos dados corretos": o gate de CI compara contagem de seções e de linhas, nunca o conteúdo das células. Resultado: um erro factual na referência canônica agora vive em **dois** arquivos, e o mecanismo de sync o **multiplicou** em vez de detectá-lo. Distinto do fingerprint EN-only de 2026-05-20: aqui o achado é especificamente a **propagação à tradução** e a lição de que sync estrutural não protege contra erro de conteúdo.

**Impacto positivo da correção:** corrigir as duas linhas em **ambos** os arquivos restaura a coerência da referência canônica em PT e EN; reforça que correções de conteúdo devem ser aplicadas ao par, não só ao EN.

**Impacto negativo / risco:** mínimo (edição de doc). O risco real é **esquecer um dos dois arquivos** ao corrigir — exatamente o failure mode que originou o problema. Mitigação: aplicar no mesmo commit e, idealmente, junto com o validador automático de `02/F1`.

---

## R2 — `orphan-template-scan.sh` varre `agents skills commands workflows scripts` mas **omite `helpers/` e `CLAUDE.md`/`CLAUDE-md/`** → risco de falso "órfão" após o refactor `helpers/`

**Severidade:** LOW-MEDIUM
**Fingerprint:** `ref-orphan-template-scan-consumers-list-omits-helpers-dir-and-claude-md-false-orphan-risk-asymmetric-with-helpers-refactor`

**Evidência** — `helpers/orphan-template-scan.sh:11`:

```bash
CONSUMERS="agents skills commands workflows scripts"
```

E os consumidores reais de templates hoje:

```
plan-template.md    → agents/setup-assistant.md, skills/.../project-context, CLAUDE.md
adr-template.md     → scripts/new-adr.sh
backlog-template.md → agents/product-analyst.md, skills/.../backlog-template
runbook-template.md → skills/.../runbook
```

**Motivo:** o `plan-template.md` é referenciado **na própria CLAUDE.md** (e também em `agents/`, por sorte). Mas a lista `CONSUMERS` **não inclui** `CLAUDE.md`, `CLAUDE-md/` nem `helpers/`. Como o commit `9c7aecd` ("refactor(scripts): move dev-only tools to helpers/") moveu ferramentas de `scripts/` para `helpers/`, qualquer template que passe a ser referenciado **apenas** por um helper ou apenas pela CLAUDE.md seria reportado como órfão indevidamente. Hoje o gap é **latente** (todo template tem ao menos um consumidor dentro da lista), mas é uma assimetria clara: o scanner foi escrito antes do refactor e nunca acompanhou o novo diretório `helpers/`. Distinto dos achados anteriores de resolvability (`flow-orphan-template-scan-runs-in-stop-but-only-checks-references-not-resolvability`) — aqui o problema é a **fronteira de varredura** (quais diretórios são considerados consumidores).

**Impacto positivo da correção:** trocar para `CONSUMERS="agents skills commands workflows scripts helpers CLAUDE.md CLAUDE-md"` (tratando arquivos e diretórios) fecha o gap antes que ele dispare um falso positivo; alinha o scanner ao layout pós-refactor.

**Impacto negativo / risco:** baixíssimo. Incluir `CLAUDE.md` (arquivo, não diretório) exige tratar os dois casos no loop de `grep -rl` (já tolerável). Custo de varredura cresce de forma negligenciável.

---

## R3 — `size-limits.sh` aplica cap a `agents/` (200) e `skills/` (500), mas **não tem cap para `commands/` nem `workflows/`** — `workflows/refactor.md` (278 linhas) é o maior arquivo de conteúdo do repo e fica sem guarda

**Severidade:** LOW-MEDIUM
**Fingerprint:** `ref-size-limits-sh-no-line-cap-for-commands-and-workflows-refactor-md-278-lines-largest-immutable-content-file-unguarded`

**Evidência** — `helpers/size-limits.sh` valida apenas três alvos:

```bash
# agents (cap 200), skills (cap 500), CLAUDE.md (warn 600 / fail 700)
find "$AGENTS_DIR" -name "*.md"     # cap 200
find "$SKILLS_DIR" -name "SKILL.md" # cap 500
wc -l < "$REPO_ROOT/CLAUDE.md"      # 600/700
```

Tamanhos reais não cobertos:

```
278 workflows/refactor.md   ← maior que QUALQUER agente e que todas as skills, exceto graphify-setup
224 workflows/new-project.md
198 workflows/security-patch.md
156 commands/refactor.md
145 commands/commit.md
```

**Motivo:** `commands/` e `workflows/` também são **arquivos imutáveis instalados** (`.claude/commands/devteam/` e guias de workflow), e a CLAUDE.md trata tamanho como dívida técnica em agentes/skills. Porém `workflows/refactor.md` (278 linhas) é **maior que o maior agente** (`frontend-test-specialist`, 262) e maior que todas as skills, exceto a `graphify-setup` (277) — e mesmo assim nenhuma guarda de tamanho o observa. O banco já tem achados por-arquivo (`flow-refactor-command-duplicates-workflows-refactor-md`, `token-commands-commit-md-145-lines-and-refactor-md-156-lines`), mas o ângulo **sistêmico** — `size-limits.sh` simplesmente não cobre essas duas árvores — é inédito.

**Impacto positivo da correção:** adicionar caps (sugestão: `commands/` ~150, `workflows/` ~250, ambos em `--warn-only` no início) torna a vigilância de tamanho consistente em todas as árvores de conteúdo instalado; cria pressão para extrair os prompts inline duplicados de `refactor.md`.

**Impacto negativo / risco:** workflows são, por natureza, mais longos (guias passo a passo), então um cap muito agressivo geraria ruído. Mitigação: começar com caps generosos e em modo warn, exatamente como a estratégia de rollout que o próprio script já documenta (`--warn-only`). Antes de ligar enforcement, decidir os números conscientemente — caso contrário vira mais uma flag `--warn-only` permanente, repetindo o problema do `size-limits` para agentes.
