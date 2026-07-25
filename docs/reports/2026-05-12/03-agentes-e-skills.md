# Relatório — Agentes e Skills (2026-05-12)

Auditoria focada em **estrutura interna de agentes e skills** — tamanho, ferramentas, modelos, padrões emergentes, gaps de cobertura. Todas as sugestões são **originais** ou **variantes com sub-escopo novo**.

---

## 1. `agent-software-architect-foundational-rule-51-lines-2x-avg`

**Severidade:** 🟡 Média

**Detecção:** Análise das linhas do bloco `## Foundational Rule` em cada agent:

| Agent | Linhas Foundational | Diferença vs. média |
|-------|--------------------|--------------------|
| `software-architect` | **51** | +132% (outlier) |
| `code-reviewer` | 28 | +28% |
| `backend-developer`, `security-specialist` | 27 | +23% |
| (média de 17 agents) | ~22 | — |
| `setup-assistant` | **10** | -55% (outlier inverso) |

**Insight:** software-architect tem o foundational mais detalhado (descreve 12+ etapas explícitas). setup-assistant é o mais minimal (10 linhas). A divergência sugere **falta de regra explícita** sobre o que vai inline vs. delegado.

**Impacto positivo (se corrigido com extração):** redução de ~30 linhas de software-architect; coerência entre agents. Foundational pode virar **gradient**: 5 linhas comuns inline + skill `project-context` cobre o resto.

**Impacto negativo (se mantido):** software-architect carrega ~250 tokens a mais que a média no startup, sem ganho de capacidade.

**Sugestão:** definir limite em CLAUDE.md (ex.: "max 25 lines Foundational Rule inline; o restante via skill load"). Auditar e podar software-architect.

---

## 2. `agent-setup-assistant-foundational-rule-only-10-lines-undersized`

**Severidade:** 🟢 Baixa — variante inversa do #1

**Detecção:** `agents/setup-assistant.md` tem apenas 10 linhas de Foundational Rule. É o **classificador inicial** do projeto (decide stack, gera audit). Linhas reduzidas sugerem que o agent **pula contexto** que outros 16 agents leem.

Comparação: setup-assistant **não carrega** `current-context` skill (não há branch a inferir antes do FIRST_RUN), mas também **não carrega** `project-context` skill (lê `README.md`/`CLAUDE.md`/`AGENTS.md` inline em vez de delegar). Esta exceção não está documentada.

**Impacto positivo (se corrigido):** setup-assistant pode delegar parte do scan inicial à `setup-scan` skill (já existe!) reduzindo inline ainda mais. E o gap explícito é documentado.

**Impacto negativo (se mantido):** novos contribuidores podem replicar o padrão minimalista em outros agents inadvertidamente.

---

## 3. `skill-token-efficiency-not-loaded-by-six-non-coding-agents`

**Severidade:** 🟡 Média

**Detecção:** `grep -c token-efficiency agents/*.md` revela 6 agentes que **não carregam** a skill:

```
product-analyst.md       : 0
qa-specialist.md         : 0
security-specialist.md   : 0
setup-assistant.md       : 0
technical-writer.md      : 0
ui-ux-designer.md        : 0
```

Argumento contrário: estes são "decision agents" / produzem outputs (backlog, audit, doc) que cabem em poucos arquivos. Argumento a favor: **todos os 6** rodam `Read`/`Grep` intensivamente em fase de discovery (setup-assistant audita repositório inteiro; security-specialist faz SAST scan; technical-writer lê tudo para gerar doc). Token efficiency é especialmente valioso para eles.

**Impacto positivo (se corrigido):** os 6 agents passam a usar `grep`/`head` em vez de `Read` completo em arquivos grandes (CHANGELOG, projeto inteiro). Economia estimada de **~5-15% tokens por sessão de discovery**.

**Impacto negativo (se mantido):** discovery-heavy agents continuam ineficientes; especialmente setup-assistant que pode ler 100+ arquivos em um audit.

---

## 4. `agent-mobile-developer-no-detox-or-maestro-test-routing-still-pending`

**Severidade:** 🟡 Média — reforço de fingerprint pendente

**Detecção:** Variante específica do `agent-mobile-developer-no-detox-or-maestro-test-routing` (2026-05-11, pendente). `grep -i -E "(detox|maestro|appium)" agents/mobile-developer.md` retorna **zero** hits.

**Sub-escopo novo:** considerando a decisão (consciente?) de **não criar mobile-test-specialist**, há duas opções:

| Opção | Impacto |
|-------|---------|
| (A) Criar mobile-test-specialist (~150 linhas) | Simetria com backend/frontend, mas mais um agente |
| (B) Adicionar seção `## Mobile Testing Routing` em `mobile-developer.md` (~30 linhas) | Solução pragmática; mobile-developer chama detox/maestro/appium inline |

Hoje não há **nenhuma** das duas. Mobile testing é cego.

**Impacto positivo (se A ou B):** cobertura mobile fica completa; fingerprint pendente fecha.

**Impacto negativo (se mantido):** projetos React Native/Expo/Flutter chamam `/devteam:mobile` e recebem apenas desenvolvimento, sem orientação de E2E test.

---

## 5. `skill-no-skill-uses-scripts-subdir-pattern-agentskills-io`

**Severidade:** 🟢 Baixa

**Detecção:** [agentskills.io specification](https://agentskills.io/specification) (referenciada em `CLAUDE.md:130`) suporta `scripts/` subdir dentro de uma skill, com scripts executáveis que o agent pode invocar. `find skills -name scripts -type d` retorna **vazio** — **zero skills** usam o padrão.

Casos onde o padrão seria útil:
- `skills/devops/sonarqube/scripts/run-quality-gate.sh` (em vez de bash heredoc inline na skill)
- `skills/shared/conventional-commits/scripts/validate-message.sh` (parser regex reaproveitável)
- `skills/database/migration-zero-downtime/scripts/expand-contract-dry-run.sh`

**Impacto positivo (se adotado):** lógica complexa reutilizável; testável isoladamente; reduz tamanho do SKILL.md.

**Impacto negativo (se mantido):** padrões scripts permanecem como bash heredoc dentro das skills (formato verboso + sem reuse).

**Sugestão:** começar com 1 caso piloto — `skills/shared/conventional-commits/scripts/validate.sh` (regex parser pequeno, testável).

---

## 6. `agent-tools-frontmatter-canonical-order-not-enforced`

**Severidade:** 🟢 Baixa

**Detecção:** Conforme relatório `01-referencias-e-consistencia.md` item 5 — ordering inconsistente entre famílias. Aqui o ângulo é **enforcement automatizado**:

`scripts/agent-lint.sh` hoje valida:
- Presença de `name`, `description`, `model`, `tools`
- `model` está na lista permitida

**Não valida:**
- Ordem canônica de `tools:`
- Presença obrigatória de `Read` (todo agent precisa ler)
- Tools declaradas mas não usadas no body (ex.: agent declara `WebSearch` mas nunca chama)

**Impacto positivo (se corrigido):** lint cria pressão para padronização; quando um agent novo é criado, lint pega divergência antes do PR merge.

**Impacto negativo (se mantido):** divergência permanece como "estilo livre".

---

## 7. `skill-monitoring-references-folder-exists-but-empty`

**Severidade:** 🟡 Média

**Detecção:** `monitoring/SKILL.md` é a maior skill (444 linhas). Em algum momento alguém criou `skills/devops/monitoring/references/` (pasta existe), mas **nunca populou**. A skill segue monolítica.

```
skills/devops/monitoring/
├── SKILL.md (444 lines)
└── references/   ← criada, vazia
```

**Impacto positivo (se corrigido):** extração de logs.md / metrics.md / traces.md / SLI-SLO-glossary.md em `references/`. SKILL.md fica como índice (~80 linhas com triggers de "load references/logs.md when...").

**Impacto negativo (se mantido):** sinal contraditório — pasta criada implica intenção, mas nada foi movido. Confunde quem auditar a skill no futuro.

**Sugestão imediata:** ou (a) preencher references/, ou (b) remover a pasta vazia para não dar sinal falso.

---

## 8. `agent-product-analyst-loads-jira-skill-but-not-other-trackers`

**Severidade:** 🟢 Baixa — variante pendente

**Detecção:** Fingerprint `agent-product-analyst-jira-only-tracker` (2026-05-08) reformulada: hoje `product-analyst.md` carrega `jira` skill (✅ feito), mas `skills/integrations/` inclui:

```
linear/ ← existe; não carregada pelo product-analyst
gotrue/ kong/ realtime/ supabase/ ← não trackers, OK
```

Setup-assistant lista trackers, mas product-analyst só conhece Jira e Linear.

**Sub-escopo novo:** detecção condicional do tracker do projeto. `product-analyst` poderia:
1. Detectar (via `setup-scan` skill) qual tracker está configurado
2. Carregar **apenas** o skill correspondente

**Impacto positivo (se corrigido):** product-analyst funciona em projetos Linear sem fallback inline. Token cost por sessão menor (carrega 1 skill em vez de N).

**Impacto negativo (se mantido):** product-analyst em projeto Linear cai num formato Jira-shaped por default.

---

## 9. `skill-frontmatter-strict-validation-missing-from-lint`

**Severidade:** 🟡 Média

**Detecção:** `agent-lint.sh` valida frontmatter de **agents** (linha por linha em `agents/*.md`). **Não valida frontmatter de skills** (`skills/**/SKILL.md`). Resultado: as 2 violações detectadas no relatório `01-referencias-e-consistencia` (design skills com 3 chaves) não foram pegas pelo CI.

**Impacto positivo (se corrigido):** novo script `scripts/skill-lint.sh` (mesma estrutura do agent-lint), executado pelo CI. Atalho: estender o próprio `agent-lint.sh` (renomeá-lo para `frontmatter-lint.sh` ou adicionar modo `--target=skills`).

**Impacto negativo (se mantido):** violação silenciosa do CLAUDE.md "Skills frontmatter rule".

---

## 10. `skill-discovery-mode-three-agents-need-explicit-collision-protocol`

**Severidade:** 🟡 Média — sub-escopo do pendente `skill-discovery-mode-loaded-by-three-agents-without-divergence-check`

**Detecção:** `discovery-mode` é carregada por product-analyst, setup-assistant, software-architect. Nenhuma marcação de "quem é a fonte de verdade" se os 3 são rodados em paralelo (ex.: `/devteam:plan` spawna os 3).

**Sub-escopo novo:** protocolo simples de collision avoidance via **lockfile**:
```
.claude/.discovery-lock.json
{
  "owner": "software-architect",
  "started_at": "2026-05-12T22:15:00Z",
  "expires_at": "2026-05-12T22:30:00Z"
}
```

Agents subsequentes detectam o lockfile e **passam** discovery (recebem o output do owner).

**Impacto positivo (se corrigido):** elimina re-trabalho em `/devteam:plan`; reduz token cost spawn-fanout em ~25%.

**Impacto negativo (se mantido):** os 3 agents repetem discovery em paralelo; outputs divergem (timestamps, paths visitados).

---

## 11. `agent-no-mandatory-load-skill-for-stack-detection`

**Severidade:** 🟢 Baixa

**Detecção:** Stack detection é feita inline por vários agents (setup-assistant, software-architect, database-specialist). Não há `skills/shared/stack-detection/SKILL.md` consolidando heurísticas (package.json → Node, pyproject → Python, Cargo.toml → Rust, go.mod → Go, etc.).

**Impacto positivo (se criado):** lógica centralizada e versionada; agents passam a fazer `load skills/shared/stack-detection/SKILL.md` em uma linha.

**Impacto negativo (se mantido):** cada agent reimplementa stack detection inline (~10-20 linhas cada); divergências sutis (ex.: setup detecta monorepo, software-architect não).

---

## 12. `skill-reviewer-base-loaded-after-project-context-but-overlaps-7-steps`

**Severidade:** 🟡 Média — sub-escopo do pendente `skill-reviewer-base-foundational-rule-overlap-with-project-context`

**Detecção:** Comparação linha a linha de `reviewer-base/SKILL.md` (28 linhas) vs. `project-context/SKILL.md`:

| Step em reviewer-base | Já está em project-context? |
|-----------------------|----------------------------|
| 1. README/CLAUDE/AGENTS | ✅ |
| 2. docs/project.md | ✅ |
| 3. session-summary | ✅ |
| 4. code-standards.md | ✅ |
| 5. architecture.md | ✅ |
| 6. linter configs | ❌ (único de reviewer) |
| 7. git log -10 | ✅ |
| 8. git diff main…HEAD | ❌ (único de reviewer) |
| 9. comments-policy | ❌ |
| 10. conventional-commits | ❌ |
| 11. SonarQube detection | ❌ |

**5 dos 11 steps são duplicação.** O bloco poderia ser:
```markdown
## Foundational Rule
1. Load skills/shared/project-context/SKILL.md
2. Additionally for review:
   - linter configs
   - git diff main…HEAD
   - skills: comments-policy, conventional-commits
   - SonarQube detection
```

Reduz de 11 steps para 6.

**Impacto positivo (se corrigido):** ~15 linhas economizadas em `reviewer-base`; os 3 reviewer agents (code, backend, frontend) sentem o ganho 3x.

**Impacto negativo (se mantido):** quando project-context é alterada (ex.: adição de step 12), reviewer-base precisa ser atualizada manualmente.

---

## Resumo

| Severidade | Quantidade |
|------------|-----------|
| 🟠 Alta | 0 |
| 🟡 Média | 8 |
| 🟢 Baixa | 4 |
| **Total** | **12** |

**Top 3 prioridades:**

1. `skill-monitoring-references-folder-exists-but-empty` — fix barato, sinal claro de "completude" da maior skill.
2. `skill-token-efficiency-not-loaded-by-six-non-coding-agents` — economia direta de tokens em 6 agents que ainda são "discovery-heavy".
3. `skill-frontmatter-strict-validation-missing-from-lint` — bloqueia regressão futura da classe de problema das design skills.
