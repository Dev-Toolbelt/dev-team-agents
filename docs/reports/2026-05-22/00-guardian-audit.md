# Auditoria Guardian — 2026-05-22

> Décima sétima passada. Verificação cruzada com `git log`, releitura arquivo a arquivo das pendências antigas e marcação de status (✅ feito / ⚠️ parcial / 🔴 não feito) para o histórico.

---

## Resumo executivo

| Indicador | Valor |
|-----------|-------|
| Janela auditada | 2026-05-21 → 2026-05-22 |
| Commits na janela | **0** |
| Throughput de implementação | **0%** (4ª janela consecutiva) |
| Último commit do repo | `9f1826d` — 2026-05-18 21:41 -0300 |
| Tempo congelado | **~4,1 dias** |
| Reaberturas antigas | 3 seguem 🔴 não feitas |
| ⚠️ Partial confirmado | `size-limits` enforcement (9/17 agentes > 200 linhas) |
| Discrepância de 2026-05-20 | `docs/agents.md` coluna Model **ainda errada** 🔴 — e agora confirmada **espelhada no `docs/agents.pt-BR.md`** |
| Sugestões originais hoje | 12 (3 por categoria) |

**Conclusão:** o repositório está congelado há mais de quatro dias. Nenhum fingerprint pendente foi endereçado por commit. Pela quarta janela consecutiva a geração de hoje prioriza **profundidade estrutural** sobre volume: 12 sugestões inéditas extraídas de leitura de código (não de drift de commit), com foco em **gaps de validação automática** (por que erros sobrevivem), uma **violação stack-prescritiva em agente ainda não auditado** (`backend-test-specialist`) e um **bug de robustez de script** (`new-adr.sh`).

---

## 1. Verificação de throughput (cruzamento com git)

```
$ git log -1 --format="%ci %h %s"
2026-05-18 21:41:39 -0300 9f1826d docs(telemetry): add PRIVACY.md, update README and schema docs
```

Não há nenhum commit após `9f1826d`. A janela 2026-05-21 → 2026-05-22 tem **0 commits**, confirmando **throughput de 0%** pela quarta janela consecutiva (2026-05-18→19, 19→20, 20→21 e 21→22 todas a 0%).

**Nota operacional (recorrente, agravando):** o working tree segue com material **não-commitado** — `docs/reports/_index.md` modificado e os diretórios `docs/reports/2026-05-18/` … `2026-05-21/` ainda como *untracked*. São agora **quatro dias** de relatórios de auditoria produzidos e nunca incorporados ao histórico do git. O CI (`check-fingerprint-uniqueness`, README sync, `agent-lint`) nunca os validou porque, para o git, eles não existem.

```
$ git status --short
 M docs/reports/_index.md
?? .claude/user-data/
?? docs/reports/2026-05-18/
?? docs/reports/2026-05-19/
?? docs/reports/2026-05-20/
?? docs/reports/2026-05-21/
```

---

## 2. Releitura das 3 reaberturas (todas seguem não feitas)

### R1 — `devops-specialist` corpo ainda stack-prescritivo · 🔴 NÃO FEITO

`agents/devops-specialist.md:138-156` — "Decision Framework — Infrastructure Sizing" e "Anti-Overengineering Rules" continuam citando tecnologias concretas no corpo:

```
| < 1k req/day | Single EC2/VPS + Docker Compose |
| 10k–100k req/day | Auto-scaling container service (ECS, Cloud Run, Container Apps) |
- Don't use Kubernetes when Docker Compose works
- Don't build a service mesh when Nginx handles the routing
- Don't set up a full observability platform (Datadog, Grafana Cloud) when CloudWatch or a self-hosted Prometheus covers the need
```

Inalterado desde a marcação ⚠️ Partial de 2026-05-18. **Status: 🔴 não feito.**

### R2 — Skills iOS/Android rasas demais · 🔴 NÃO FEITO

```
 33  skills/mobile/ios/SKILL.md
 35  skills/mobile/android/SKILL.md
218  skills/mobile/ios-hig/SKILL.md
221  skills/mobile/material-design/SKILL.md
```

`ios/SKILL.md` (33) e `android/SKILL.md` (35) seguem como wrappers rasos. Inalterado. **Status: 🔴 não feito.**

### R3 — Gate de lazy-load do design-patterns ausente · 🔴 NÃO FEITO

`skills/architecture/design-patterns/references/composition-root.md` existe, mas **nenhum agente o carrega**. Todos seguem puxando o `SKILL.md` inteiro:

- `agents/software-architect.md:30` → `design-patterns/SKILL.md → Composition Root section`
- `agents/code-reviewer.md:95` → `design-patterns/SKILL.md`
- `agents/backend-developer.md:212` → `design-patterns/SKILL.md`
- `agents/frontend-developer.md:145` → `design-patterns/SKILL.md → Composition Root section`

A extração foi feita; o gate condicional que a justificaria nunca foi ligado. **Status: 🔴 não feito.**

---

## 3. Discrepância ⚠️ Partial reconfirmada — `size-limits` enforcement

`helpers/size-limits.sh` segue rodando **`--warn-only`** no CI (`ci.yml:24`) e não há sub-script de Stop equivalente. O cap "Max ~200 lines" continua sem enforcement real. Contagem atual (inalterada): **9 de 17 agentes acima de 200 linhas**.

```
262 frontend-test-specialist   228 code-reviewer
261 backend-developer          208 qa-specialist
239 setup-assistant            204 backend-reviewer
237 devops-specialist          (199 mobile-developer — no limite)
234 security-specialist
232 frontend-developer
```

**Status: ⚠️ Partial mantido.**

---

## 4. Discrepância de 2026-05-20 reconfirmada — e agora espelhada na tradução

A correção do `docs/agents.md` recomendada em 2026-05-20 **não foi aplicada** (repo congelado). Releitura desta passada **confirma que o erro está duplicado no `docs/agents.pt-BR.md`** — a "README Sync Rule" propagou fielmente o **erro** para a tradução:

| Arquivo : linha | Listado | Real (frontmatter) | Status |
|-----------------|---------|--------------------|--------|
| `docs/agents.md:26` | `technical-writer` → **Haiku** | `claude-sonnet-4-6` | 🔴 errado |
| `docs/agents.md:27` | `setup-assistant` → **Sonnet** | `claude-opus-4-7` | 🔴 errado |
| `docs/agents.md:79` | "Assigned **Haiku** for cost efficiency" | Sonnet | 🔴 errado |
| `docs/agents.pt-BR.md:26` | `technical-writer` → **Haiku** | `claude-sonnet-4-6` | 🔴 errado (espelhado) |
| `docs/agents.pt-BR.md:27` | `setup-assistant` → **Sonnet** | `claude-opus-4-7` | 🔴 errado (espelhado) |
| `docs/agents.pt-BR.md:79` | "Atribuído ao **Haiku**…" | Sonnet | 🔴 errado (espelhado) |

O caso Haiku contradiz a própria CLAUDE.md ("Haiku is available for future micro-agents"; **0 agentes usam Haiku**). **Status: 🔴 não feito** — agora em **dois** arquivos canônicos. O novo achado `01/R1` registra a dimensão da tradução; o `02/F1` registra **por que** o erro sobrevive (não há validador cruzando a coluna Model contra o frontmatter).

---

## 5. Falsos positivos descartados nesta passada

- **Referências de skill quebradas:** revarredura de todos os paths `skills/**/SKILL.md` citados em `agents/` e `commands/` → **100% resolvem** (repo congelado; mantém o resultado de 2026-05-21). (Descartado.)
- **Pares de doc pt-BR inexistentes no CI:** o `README sync check` referencia `docs/agents.pt-BR.md` e `docs/installation.pt-BR.md` — ambos **existem** e passam na checagem de contagem de seções (95/95 e 169/169 linhas). (Descartado.)
- **`adr-template.md` órfão:** segue lido por `scripts/new-adr.sh` (já descartado). (Descartado.)
- **`backlog-template.md` "duplicado" da skill:** na releitura, o template físico (35 linhas, item único de backlog) e a skill `backlog-template` (171 linhas, estrutura multi-arquivo) **não são duplicatas** — têm conteúdos diferentes sob o mesmo nome (ver nota em `04/T2`). O fingerprint antigo sobre "skill com template inline" continua válido; o ângulo de **divergência de conteúdo sob nome igual** é novo mas foi tratado pela ótica de token, não reaberto aqui.

---

## 6. Recomendação ao mantenedor

O gargalo do projeto **não é geração de sugestões** — são 449 fingerprints acumulados e **quatro dias** de relatórios prontos. O gargalo é **execução e commit**. Recomenda-se, em ordem:

1. **Commitar** os relatórios pendentes (2026-05-18 → 22) e o `_index.md` para que o CI passe a validá-los.
2. Aplicar a correção de **dois arquivos** do `docs/agents.md` + `docs/agents.pt-BR.md` (coluna Model) — e, no mesmo PR, adicionar o validador automático proposto em `02/F1` para a discrepância nunca mais reaparecer silenciosamente.
3. Atacar as **3 reaberturas 🔴** — correções pequenas, baixo risco, alto valor (conformidade stack-agnostic + economia de token).
4. Decidir conscientemente sobre o `size-limits` ⚠️ Partial: aplicar enforcement (remover `--warn-only`) ou ajustar o cap documentado para refletir a realidade (9/17 já o excedem).
