# Auditoria Guardian — 2026-05-21

> Décima sexta passada. Verificação cruzada com `git log`, releitura arquivo a arquivo das pendências antigas e marcação de status (✅ feito / ⚠️ parcial / 🔴 não feito) para o histórico.

---

## Resumo executivo

| Indicador | Valor |
|-----------|-------|
| Janela auditada | 2026-05-20 → 2026-05-21 |
| Commits na janela | **0** |
| Throughput de implementação | **0%** (3ª janela consecutiva) |
| Último commit do repo | `9f1826d` — 2026-05-18 21:41 -0300 |
| Tempo congelado | **~3,2 dias** |
| Reaberturas antigas | 3 seguem 🔴 não feitas |
| ⚠️ Partial confirmado | `size-limits` enforcement (9/17 agentes > 200 linhas) |
| Discrepância de 2026-05-20 | `docs/agents.md` coluna Model **ainda errada** 🔴 |
| Sugestões originais hoje | 12 (3 por categoria) |

**Conclusão:** o repositório está congelado há mais de três dias. Nenhum fingerprint pendente foi endereçado por commit. Como nas duas passadas anteriores, a geração de hoje prioriza **profundidade estrutural** sobre volume, honrando o mandato anti-duplicação: 12 sugestões inéditas extraídas de leitura de código, não de drift de commit.

---

## 1. Verificação de throughput (cruzamento com git)

```
$ git log -1 --format="%ci %h %s"
2026-05-18 21:41:39 -0300 9f1826d docs(telemetry): add PRIVACY.md, update README and schema docs
```

Não há nenhum commit após `9f1826d`. A janela 2026-05-20 → 2026-05-21 tem **0 commits**, confirmando **throughput de 0%** pela terceira janela consecutiva (2026-05-18→19, 2026-05-19→20 e 2026-05-20→21 todas a 0%).

**Nota operacional (recorrente):** o working tree continua com material **não-commitado** — `docs/reports/_index.md` modificado e os diretórios `docs/reports/2026-05-18/`, `2026-05-19/`, `2026-05-20/` e `.claude/user-data/` ainda como *untracked*. Ou seja, três dias de relatórios de auditoria foram produzidos mas nunca entraram no histórico do git. Isso explica por que o CI (`check-fingerprint-uniqueness`, README sync etc.) nunca os validou: eles não existem para o git.

```
$ git status --short
 M docs/reports/_index.md
?? .claude/user-data/
?? docs/reports/2026-05-18/
?? docs/reports/2026-05-19/
?? docs/reports/2026-05-20/
```

---

## 2. Releitura das 3 reaberturas (todas seguem não feitas)

### R1 — `devops-specialist` corpo ainda stack-prescritivo · 🔴 NÃO FEITO

`agents/devops-specialist.md:134-156` — seções "Decision Framework — Infrastructure Sizing" e "Anti-Overengineering Rules" continuam citando tecnologias concretas no corpo do agente:

```
| < 1k req/day | Single EC2/VPS + Docker Compose |
| 10k–100k req/day | Auto-scaling container service (ECS, Cloud Run, Container Apps) |
...
- Don't use Kubernetes when Docker Compose works
- Don't build a service mesh when Nginx handles the routing
- Don't set up a full observability platform (Datadog, Grafana Cloud) when CloudWatch or a self-hosted Prometheus covers the need
```

Inalterado desde a marcação ⚠️ Partial de 2026-05-18. Viola o mandato stack-agnostic (CLAUDE.md). **Status: 🔴 não feito.**

### R2 — Skills iOS/Android rasas demais · 🔴 NÃO FEITO

```
33  skills/mobile/ios/SKILL.md
35  skills/mobile/android/SKILL.md
218 skills/mobile/ios-hig/SKILL.md
221 skills/mobile/material-design/SKILL.md
```

`ios/SKILL.md` (33 linhas) e `android/SKILL.md` (35 linhas) seguem como wrappers rasos cujo primeiro bullet redireciona para `-hig`/`material-design`. Inalterado. **Status: 🔴 não feito.**

### R3 — Gate de lazy-load do design-patterns ausente · 🔴 NÃO FEITO

`skills/architecture/design-patterns/references/composition-root.md` existe (4.608 bytes), mas **nenhum agente o carrega**. Todos seguem puxando o `SKILL.md` inteiro:

- `agents/software-architect.md:30` → `design-patterns/SKILL.md → Composition Root section`
- `agents/code-reviewer.md:95` → carrega `design-patterns/SKILL.md`
- `agents/backend-developer.md:212` → carrega `design-patterns/SKILL.md`
- `agents/frontend-developer.md:145` → `design-patterns/SKILL.md → Composition Root section`

A extração foi feita, mas o gate condicional que justificaria a extração nunca foi ligado. **Status: 🔴 não feito.**

---

## 3. Discrepância ⚠️ Partial reconfirmada — `size-limits` enforcement

`helpers/size-limits.sh` segue rodando **`--warn-only`** no CI (`ci.yml`) e não há sub-script de Stop equivalente. O cap "Max ~200 lines" continua sem enforcement real. Contagem atual: **9 de 17 agentes acima de 200 linhas** (inalterado vs. 2026-05-19/20):

```
262 frontend-test-specialist   228 code-reviewer
261 backend-developer          208 qa-specialist
239 setup-assistant            204 backend-reviewer
237 devops-specialist          (199 mobile-developer — no limite)
234 security-specialist
232 frontend-developer
```

**Status: ⚠️ Partial mantido** (flag existe; enforcement nunca aplicado).

---

## 4. Discrepância de 2026-05-20 reconfirmada — `docs/agents.md` coluna Model

A correção recomendada em 2026-05-20 **não foi aplicada** (repo congelado). A referência canônica segue errada:

| Linha | Lista | Real (frontmatter) | Status |
|-------|-------|--------------------|--------|
| `docs/agents.md:26` | `technical-writer` → **Haiku** | `claude-sonnet-4-6` | 🔴 errado |
| `docs/agents.md:27` | `setup-assistant` → **Sonnet** | `claude-opus-4-7` | 🔴 errado |
| `docs/agents.md:79` | narrativa: "Assigned **Haiku** for cost efficiency" (technical-writer) | Sonnet | 🔴 errado (compõe o mesmo erro) |

O caso Haiku contradiz a própria CLAUDE.md, que afirma que **0 agentes usam Haiku** ("Haiku is available for future micro-agents"). **Status: 🔴 não feito.**

---

## 5. Falsos positivos descartados nesta passada

- **Referências de skill quebradas:** varredura de todos os paths `skills/**/SKILL.md` citados em `agents/` e `commands/` → **100% resolvem**. Nenhuma referência quebrada. (Descartado.)
- **`03-agent-lint.sh` sem fast-path:** ao contrário do que se poderia supor, o sub-script JÁ tem o fast-path `DEVTEAM_NO_CHANGES` + gate por `git status`. Bem otimizado. (Descartado — não é achado.)
- **ETag no update-check:** `token-update-check-no-etag-handling` (sugestão antiga) está, na prática, **implementado** — `01-check-updates.sh` faz `If-None-Match`/304. (Não reproposto.)
- **`adr-template.md` órfão:** segue sendo lido por `scripts/new-adr.sh` (já descartado em 2026-05-20). (Descartado.)

---

## 6. Recomendação ao mantenedor

O gargalo do projeto **não é geração de sugestões** — são 457 fingerprints acumulados e três dias de relatórios prontos. O gargalo é **execução e commit**. Recomenda-se:

1. **Commitar** os relatórios pendentes (2026-05-18/19/20/21) e o `_index.md` para que o CI passe a validá-los.
2. Atacar as **3 reaberturas 🔴** e a discrepância do `docs/agents.md` — são correções pequenas, de baixo risco e alto valor (consistência da referência canônica + conformidade stack-agnostic).
3. Decidir conscientemente sobre o `size-limits` ⚠️ Partial: ou aplicar enforcement (remover `--warn-only`) ou ajustar o cap documentado para refletir a realidade (9/17 já o excedem).
