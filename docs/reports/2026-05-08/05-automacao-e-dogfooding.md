# 5. Automação e Dogfooding (Validadores Faltantes, Self-Eat, Fingerprint Hygiene)

← [Voltar ao índice](index.md)

Esta seção foca em **gaps de automação** que ainda não foram fingerprintados e em uma classe específica de problema visível no repo: o `dev-team-agents` produz scripts e regras que ele próprio não exercita. As recomendações aqui se sobrepõem em parte com a seção 1 e a seção 3 (na questão do dispatcher de Stop), mas o ângulo aqui é estritamente **automação que falta**.

---

## 5.1 Não existe scan que detecte **templates órfãos** em `templates/`

O repositório tem `scripts/orphan-skill-scan.sh` que detecta:
- Skills sem referência em agente;
- Referências quebradas em agentes (paths que não existem).

Mas não existe equivalente para `templates/`. Hoje só há um arquivo (`plan-template.md`); se um contribuinte adicionar `templates/runbook-template.md` ou `templates/incident-template.md` (ambos plausíveis), nada detecta:

- Se o template é referenciado por algum agente / skill / workflow;
- Se algum agente tenta ler `templates/runbook-template.md` mas escreveu o nome errado;
- Se um template duplica conteúdo de uma skill (caso real: `plan-template.md` × `plan-mode/SKILL.md`, ver seção 3.3).

Hoje o risco é baixo (1 arquivo); fica baixo se o repo crescer pra 2 ou 3 templates; vira problema com 5+.

> **Fingerprint:** `auto-no-orphan-templates-scan`

| Impacto | Detalhe |
|---------|---------|
| **Positivo (preventivo)** | Templates novos chegam com referência garantida em pelo menos 1 lugar |
| **Positivo** | Ortogonal ao orphan-skill-scan; fácil de modelar em paralelo |
| **Negativo** | Pouco retorno isolado dado o tamanho atual (1 arquivo); investimento prematuro |

**Recomendação:** **adiar** até `templates/` chegar a 3+ arquivos. Quando chegar, copiar o esqueleto do `orphan-skill-scan.sh` e adaptar — gera `orphan-template-scan.sh`. Anti-padrão: criar agora e o script ficar parado sem rodar contra nada relevante.

---

## 5.2 Não existe validador que confira `tools:` no frontmatter dos agentes

O fingerprint `auto-skill-frontmatter-validator` (2026-05-06) cobriu validar **presença** de `name`, `description`, `model`, `tools` no frontmatter. O ângulo **novo** aqui: validar que o conteúdo de `tools:` corresponde ao que o agente **realmente usa** no corpo.

Exemplos reais detectados durante a leitura desta passada:

| Agente | `tools:` declarado | Sinais no corpo |
|--------|---------------------|-----------------|
| `code-reviewer` | `Read, Grep, Glob, Bash` | Não tem `Write` nem `Edit` declarado, e isso bate (ele só revisa). ✅ |
| `setup-assistant` | `Read, Write, Edit, Bash, Glob, Grep` | Confere — escreve docs, edita CLAUDE.md, executa scripts. ✅ |
| `qa-specialist` | `Read, Write, Bash, Glob, Grep` | Tem `Write` mas **não** `Edit` — pode produzir relatório novo, mas não modificar relatório existente. Inconsistente com "Validation Tiers" que sugere iteração. |

O caso do `qa-specialist` é o tipo de coisa que um validador pegaria: agente que recebe pedido para "atualizar o relatório anterior" precisaria de `Edit` mas não tem. Também há o oposto — agentes que declaram tools que nunca usam, gastando o token-budget de prompt à toa.

> **Fingerprint:** `auto-no-frontmatter-tools-validator`

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Detecta cedo descasamentos entre intenção (tools) e implementação (corpo) |
| **Positivo** | Reduz ruído de "ferramenta declarada nunca usada" |
| **Negativo** | Heurística não-trivial: "o agente menciona escrita inline em fenced-block?" pode dar falso-positivo |
| **Negativo** | Ferramenta aspirante a linter; risco de virar regra anti-produtividade |

**Recomendação:** começar simples — script que **lista**, para cada agente, as tools no frontmatter e as menções de cada tool no corpo (`Read`, `Write`, `Edit`, `Bash`, `Grep`, `Glob`). Reportar discrepâncias como informação, não como erro. Se virar útil, evoluir para regra dura.

---

## 5.3 Não existe checagem de **unicidade de nome** de skill entre categorias

`skills/` tem 14 categorias e dezenas de subdiretórios. Hoje, por convenção, o nome da skill (último componente do path) **deve ser único globalmente** porque o orphan-skill-scan resolve por nome:

```bash
# scripts/orphan-skill-scan.sh linhas 90–95
if grep -qE "\`${skill_name}\`|...
```

Se houvesse duas skills chamadas `database` (ex.: `skills/integrations/database/` e `skills/architecture/database/`), o scan **não distinguiria** — qualquer match de "database" no agente satisfaria ambos os arquivos.

Hoje **não existe** colisão (verificado por `find skills -name SKILL.md | xargs -I{} dirname {} | xargs -I{} basename {} | sort | uniq -d` — zero output). Mas:

- Não há script automatizado que verifique;
- Um contribuinte que crie `skills/security/auth/SKILL.md` e `skills/integrations/auth/SKILL.md` introduziria a colisão silenciosa;
- O orphan-skill-scan continuaria reportando "clean" mesmo com a ambiguidade.

> **Fingerprint:** `auto-no-skill-name-uniqueness-check`

| Impacto | Detalhe |
|---------|---------|
| **Positivo (preventivo)** | Colisão silenciosa fica impossível de chegar em main |
| **Positivo** | One-liner no Stop hook: pouco custo de manutenção |
| **Negativo** | Incrementa o já popular Stop hook em mais um sub-script; adiciona ~30ms |

**Recomendação:** adicionar um sub-script `scripts/hooks/stop/02-skill-name-uniqueness.sh` (1 comando bash):

```bash
DUPS=$(find "$REPO_ROOT/skills" -name "SKILL.md" \
         | xargs -I{} dirname {} \
         | xargs -I{} basename {} \
         | sort | uniq -d)
if [ -n "$DUPS" ]; then
    echo "ERROR: skill name collision: $DUPS" >&2
    exit 1
fi
```

Custo: ~10 linhas de bash; benefício: classe inteira de bug eliminada.

---

## 5.4 `_index.md` cresce indefinidamente sem checagem de unicidade de fingerprint

`docs/reports/_index.md` é o **banco de fingerprints** central — a estratégia anti-repetição depende de cada novo fingerprint ser **único**. Hoje, a unicidade é mantida por **disciplina manual** do agente que escreve o relatório.

Riscos:
- Erro de digitação acidental cria fingerprint que parece novo mas é o mesmo (ex.: `token-context-loading-dedup` × `token-context-loading-dedupe`);
- Fingerprint do dia 2026-05-15 colide com um da semana 2026-04-XX que ninguém checou;
- Não existe relatório de saúde do índice ("quantos fingerprints, qual a distribuição por categoria, qual a taxa de novo/dia").

> **Fingerprint:** `auto-no-fingerprint-collision-check`

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Impossível introduzir fingerprint duplicado; preserva a integridade do banco |
| **Positivo** | Bonus: relatório de saúde permite ver "estamos rodando em circunlóquio?" (fingerprints muito próximos demais) |
| **Negativo** | Adiciona ~20 linhas de bash; mantenedor do hook precisa lidar com 1 sub-script a mais |

**Recomendação:** adicionar `scripts/check-fingerprints.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
INDEX_FILE="$REPO_ROOT/docs/reports/_index.md"
DUPS=$(grep -oE '`[a-z][a-z-]+-[a-z][a-z-]+`' "$INDEX_FILE" \
       | sort | uniq -d)
[ -z "$DUPS" ] || { echo "Duplicate fingerprints: $DUPS" >&2; exit 1; }
```

Pode rodar como sub-script do Stop hook, ou ser invocado ao final da geração de cada relatório.

---

## 5.5 Inversão do `gov-stop-dispatcher-self-eat` (seção 3.6) — instalador é mais rigoroso que o repo

O instalador (`scripts/install.sh` linhas 195–222) **força** `.claude/settings.json` no projeto do usuário a ter o dispatcher de Stop. O `.claude/settings.json` deste próprio repo (15 linhas) tem **só** `orphan-skill-scan.sh --quiet`.

A relação é assimétrica: o repo distribui rigor que ele próprio não exercita. Reaproveitando dado da seção 3.6, fica claro que isso é um **gap operacional**, não estilístico:

| Quem? | Hooks ativos hoje |
|-------|-------------------|
| Projeto do usuário (após `install.sh`) | PreToolUse (check updates), Stop (session-summary, orphan-skill-scan) |
| dev-team-agents (este repo) | Stop (orphan-skill-scan APENAS) |

> **Fingerprint:** `gov-installer-rigor-asymmetry`

| Impacto | Detalhe |
|---------|---------|
| **Positivo (alinhar)** | Equipe sente, em casa, qualquer atrito do hook antes de empurrar pra usuário |
| **Positivo** | Reduz a chance de bug do tipo "rodou em CI mas não testou no próprio repo" |
| **Negativo** | Decisão sobre versionar ou não o `session-summary.md` deste repo; precisa ser explícita |

**Recomendação:** já coberta nas seções 1.4 e 3.6. O fingerprint aqui é independente porque o **ângulo de automação** (assimetria entre instalado e instalador) é distinto do fingerprint anterior (dogfood).

---

## 5.6 Resumo de fingerprints novos

| Fingerprint | Tema |
|-------------|------|
| `auto-no-orphan-templates-scan` | Sem scan de templates órfãos em `templates/` (adiar até 3+ arquivos) |
| `auto-no-frontmatter-tools-validator` | Sem validação de `tools:` declarado × usado no corpo do agente |
| `auto-no-skill-name-uniqueness-check` | Sem checagem de colisão de nome de skill entre categorias |
| `auto-no-fingerprint-collision-check` | `_index.md` cresce indefinidamente sem checagem de unicidade |
| `gov-installer-rigor-asymmetry` | Instalador empurra hooks que o próprio repo não consome |
