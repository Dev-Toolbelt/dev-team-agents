# Eixo E — Economia de tokens (2026-09-11)

**Data:** 2026-09-11 · **Baseline:** `HEAD` = `9530551`

---

## Resultado

> **Nenhum achado original neste eixo.**

O eixo foi medido, não estimado. Todas as medições estão abaixo. Cada carga de custo relevante que
a varredura encontrou já está registrada no banco, e cada candidato foi confrontado com a porta
correspondente antes do descarte.

---

## Medições executadas

### Carga incondicional por spawn de agente

Skills carregadas fora de tabela condicional, na Foundational Rule de cada agente:

| Skill | Linhas | Sítios de carga | Custo bruto (linhas × sítios) | Estado no banco |
|---|---:|---:|---:|---|
| `shared/interaction-patterns` | 209 | 34 | 7.106 | **aberto** — "209×34" |
| `shared/project-context` | 269 | 18 | 4.842 | **aberto** — via `token-review-shared-skills-reloaded-…` (🟡 nesta Fase 1) |
| `shared/token-efficiency` | 160 | 18 | 2.880 | **aberto** — "160×18" |
| `shared/output-format` | 203 | 9 | 1.827 | **descartado 2×** por Porta 4 (2026-08-21, 2026-09-04) — retorna só como o sub-escopo § Plan Template, já registrado em `token-output-format-third-copy-of-plan-format-42-lines-nine-load-sites` |
| `shared/plan-mode` | 153 | 7 agentes + 16 comandos | 3.519 | **✅ Executed** — `token-plan-mode-skill-131-lines-loaded-by-7-agents-unconditionally` |
| `shared/comments-policy` | — | 15 agentes | — | verificado na Fase 1 (item 10): 15 formulações distintas, é delegação prescrita, não duplicação |

### Skills grandes com consumidor único

`shared/migration-v1-to-v2` 438 linhas × 1 (`setup-assistant`) · `architecture/orchestration` 391 × 2
· `shared/backlog-template` 238 × 1 (`product-analyst`). Os três já estão no conjunto aberto.

### Foundational Rules mais caras

`software-architect.md` referencia 29 skills no bloco da Foundational Rule (3.901 linhas somadas),
mas **5 são incondicionais** (`project-context` 269 + `output-format` 203 + `token-efficiency` 160 +
`plan-mode` 153 + `reuse-guidelines`) — as outras 24 estão sob o heading
`**Conditional skill loads (load when the task matches):**` (`:31-56`), que é exatamente o padrão
que o eixo recomenda. Não é achado. A Foundational Rule ser a maior do repo (43 linhas) já está
registrado e **🔴 reaberto** em 2026-08-21 (`agent-software-architect-foundational-rule-51-lines-2x-avg`).

### Custo de I/O dos hooks

Dos 11 sub-scripts ativos do `Stop`, **10** consomem `DEVTEAM_NO_CHANGES` ou
`DEVTEAM_TOUCHED_PATHS` computados uma vez pelo dispatcher. O único que não consome —
`99b-archive-index.sh` — o justifica no cabeçalho (`:11-12`: rotação é temporal, não baseada em
mudança) e usa um stamp diário (`:26-30`). Sem desperdício mensurável.

### Superfície sempre carregada

`CLAUDE.md` em **602 linhas** entra em toda sessão como instrução de projeto. Já registrado e
**🔴 reaberto três vezes** (`token-claude-md-426-lines-still-monolithic-…`, MEDIUM-HIGH), com o
detalhe de que os blocos extraíveis (`:212` tabela de comandos, `:418` Agent Memory System) seguem
inline. Os cinco arquivos de `CLAUDE-md/` somam 343 linhas e não têm teto em `size-limits.sh` — mas
confrontado com o mesmo fingerprint pela **Porta 3** (alvo `CLAUDE.md`/`CLAUDE-md/` + causa raiz
"monólito não extraído" coincidem, **2 de 3**), é duplicata. Descartado.

---

## Candidatos verificados e descartados

| Candidato | Porta | Motivo |
|---|---|---|
| `output-format` 203 linhas × 9 sítios | 4 | escopo menor sem sub-escopo novo — o único sub-escopo (§ Plan Template, 42 linhas) já é `token-output-format-third-copy-of-plan-format-…` |
| `interaction-patterns` 209 × 34 | 5 | conjunto aberto |
| `token-efficiency` 160 × 18 | 5 | conjunto aberto |
| `migration-v1-to-v2` 438 × 1 | 5 | conjunto aberto |
| `orchestration` 391 sem `references/` | 5 | conjunto aberto |
| `preferences.json` (23 linhas) lido inteiro em 31 sítios | 4 | já descartado por Porta 4 em 2026-09-04 |
| `CLAUDE-md/*.md` sem teto em `size-limits.sh` | 3 | 2 de 3 contra `token-claude-md-426-lines-still-monolithic-…` |
| Fan-out de `/devteam:review` recarrega o pacote compartilhado em 8 execuções isoladas | 5 | já registrado — e **marcado 🟡 nesta Fase 1** (item 9), com o sub-escopo pendente descrito: o mecanismo de passagem de sumário entre spawns continua inexistente |

---

## Nota sobre por que o eixo rendeu zero

O Eixo E rendeu 11 achados em 2026-07-31 e volumes decrescentes desde então. A razão é mecânica: o
custo de contexto é função do tamanho dos arquivos × número de sítios de carga, e **nenhum dos dois
mudou desde `a1e3791` (2026-08-21)**. As quatro maiores cargas do repositório já têm fingerprint
aberto; propor de novo qualquer uma delas seria violar a Porta 5, e propor um recorte arbitrário
delas violaria a Porta 4 — que é exatamente o que os passes de 2026-08-21 e 2026-09-04 já
recusaram para `output-format`.

Registrar zero aqui é o resultado correto. O eixo volta a render quando um arquivo crescer ou uma
skill ganhar sítio de carga novo.
