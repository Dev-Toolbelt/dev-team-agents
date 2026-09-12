# Eixo D — Agentes e skills (2026-09-11)

**Data:** 2026-09-11 · **Baseline:** `HEAD` = `9530551`

---

## Resultado

> **Nenhum achado original neste eixo.**

O eixo foi varrido integralmente e nada sobreviveu às portas do Protocolo Anti-Duplicação. Isto é
resultado válido, não ausência de trabalho: o que a varredura encontrou está registrado abaixo com a
porta pela qual caiu.

---

## Varredura executada

| Verificação | Comando / método | Resultado |
|---|---|---|
| Frontmatter, tier↔`tiers.json`↔run-banner, identidade de skill, quiz-first, roster↔`agents/` | `bash helpers/agent-lint.sh` | `clean ✓` (exit 0) |
| Tetos de linha (agentes 211 · skills 500 · comandos 200) | `bash helpers/size-limits.sh` | apenas `⚠ CLAUDE.md: 602 lines` — nenhum agente, skill ou comando acima do teto |
| Skills órfãs e caminhos quebrados | `bash helpers/orphan-skill-scan.sh` | 3 avisos de carga duplicada, todos falsos positivos já verificados |
| Skills grandes com poucos consumidores (candidatas a `references/` ou a gate condicional) | contagem de linhas × `grep -rl <nome> agents/ commands/` | 14 skills ≥ 198 linhas mapeadas — ver tabela abaixo |
| Agentes no teto exato | `wc -l agents/*.md` | `software-architect` 211 · `qa-specialist` 211 · `frontend-developer` 211 · `devops-specialist` 210 · `backend-reviewer` 209 |
| Contrato de coding agent (`## Worktree Isolation`) | `grep -l "## Worktree Isolation" agents/*.md` | 9 agentes; `CLAUDE.md:109` enumera 8 |
| Alcance do `spec-gate` pelos coding agents | `grep -l spec-gate agents/*.md` | 3 agentes (product-analyst, qa-specialist, software-architect) |

### Skills grandes × consumidores

| Linhas | Consumidores | Skill | Estado |
|---:|---:|---|---|
| 438 | 1 | `shared/migration-v1-to-v2` | Porta 5 — já no conjunto aberto |
| 391 | 2 | `architecture/orchestration` | Porta 5 — "sem `references/`", já aberto |
| 269 | 18 | `shared/project-context` | Porta 5 — coberto por `token-review-shared-skills-reloaded-…` (🟡 nesta Fase 1) |
| 238 | 1 | `shared/backlog-template` | Porta 5 — `token-backlog-template-skill-…`, já registrado |
| 226 | 2 | `devops/graphify-setup` | sob teto, dois consumidores legítimos — sem achado |
| 222 | 1 | `integrations/database-production` | skill de referência específica — exceção por design |
| 222 | 1 | `architecture/llm-integration` | skill de referência específica — exceção por design |
| 221 / 218 | 2 cada | `mobile/material-design`, `mobile/ios-hig` | `skills/mobile/*` — exceção por design |
| 216 | 3 | `integrations/supabase` | `skills/integrations/*` — exceção por design |
| 209 | 34 | `shared/interaction-patterns` | Porta 5 — "209×34", já no conjunto aberto |
| 206 | 1 | `integrations/jwt` | exceção por design |
| 203 | 9 | `shared/output-format` | sob teto; carga é condicional na maioria — sem achado |
| 198 | 1 | `devops/vps-linux` | `skills/devops/*` — exceção por design |

---

## Candidatos verificados e descartados

| Candidato | Porta | Motivo |
|---|---|---|
| `agents/seo-specialist.md` tem `## Worktree Isolation` (`:35`) mas está fora da enumeração de `CLAUDE.md:109`, e por isso ficou sem `comments-policy` e sem `reuse-guidelines` | 5 | `agent-seo-specialist-outside-coding-agent-contract` (MEDIUM, aberto) e `docs-sync-claude-md-coding-agents-list-omits-seo-specialist` (MEDIUM, aberto) |
| Três agentes em exatamente 211 linhas, sem folga e sem `references/` como saída | 5 | `agent-three-at-exactly-211-line-ceiling-zero-headroom-for-additions` (LOW, aberto) |
| `agents/product-analyst.md:128-153` restata a mecânica da cascata de worktree/Docker duas linhas antes de mandar não restatá-la | 3 | causa raiz + remediação coincidem com `token-worktree-isolation-block-7-lines-x-8-agents` (✅ Executed) — **2 de 3**. Detalhado no [Eixo A](01-agnosticismo-de-stack.md) |
| `skills/shared/spec-gate/SKILL.md` nomeia quatro coding agents mas nenhum deles a carrega | 5 | `skill-spec-gate-scope-lock-hard-gate-unreachable-by-execution-agents` (MEDIUM-HIGH, aberto) |
| `shared/migration-v1-to-v2` com 438 linhas e 1 consumidor (`setup-assistant`) | 5 | já no conjunto aberto |
| `architecture/orchestration` com 391 linhas sem `references/` | 5 | já no conjunto aberto |
| Diretiva de `comments-policy` presente em 15 agentes | — | **não é achado**: verificado na Fase 1 (item 10) como 15 formulações distintas, particularizadas por papel — é a delegação que o `CLAUDE.md` § Canonical Rule Homes exige, não duplicação |
| Foundational Rule idêntica nos três reviewers | — | **não é achado**: verificado na Fase 1 (item 8) como uma linha de delegação, exatamente a forma prescrita |
| `agents/backend-developer.md` é o maior agente em bytes (12.5 KB) e tem zero menções no banco | — | 193 linhas, sob o teto; leitura do corpo não revelou regra duplicada, seção extraível nem sobreposição de responsabilidade não registrada |
| `agents/qa-specialist.md` e `agents/product-analyst.md` casam o regex do Eixo A | — | falso positivo: `rspec` dentro de *perspective* |

---

## Nota sobre a produtividade deste eixo

O Eixo D produziu 26 achados em 2026-08-14, 37 em 2026-08-21 e 21 em 2026-08-28 — quando o
repositório ainda recebia commits de código. Desde `a1e3791` (2026-08-21) nada em `agents/` ou
`skills/` mudou, e os quatro passes desde então já extraíram o que a árvore estática oferece: o
conjunto aberto tem 113 fingerprints, dos quais a maioria com alvo em `agents/` ou `skills/`.
Zero achados originais aqui é o comportamento esperado de um banco maduro contra uma árvore parada,
não falha de varredura. O indicador volta a ter valor quando houver delta de código.
