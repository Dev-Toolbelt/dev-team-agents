# Auditoria Guardian — 2026-05-23

> Décima oitava passada. Verificação cruzada com `git log`, releitura arquivo a arquivo das pendências antigas e marcação de status (✅ feito / ⚠️ parcial / 🔴 não feito) para o histórico.

---

## Resumo executivo

| Indicador | Valor |
|-----------|-------|
| Janela auditada | 2026-05-22 → 2026-05-23 |
| Commits na janela | **0** |
| Throughput de implementação | **0%** (5ª janela consecutiva) |
| Último commit do repo | `9f1826d` — 2026-05-18 21:41 -0300 |
| Tempo congelado | **~5,1 dias** |
| Reaberturas antigas | 3 seguem 🔴 não feitas |
| ⚠️ Partial confirmado | `size-limits` enforcement (9/17 agentes > 200 linhas) |
| Discrepância de 2026-05-20 | `docs/agents.md` coluna Model **ainda errada** 🔴 — espelhada no `docs/agents.pt-BR.md` |
| Pendência de doc (2026-05-18) | CHANGELOG `[Unreleased]` ainda **omite** telemetria/PRIVACY/helpers/iOS/Android/archive |
| Sugestões originais hoje | 12 (3 por categoria) |

**Conclusão:** o repositório está congelado há mais de **cinco dias**. Nenhum fingerprint pendente foi endereçado por commit. Pela quinta janela consecutiva a geração de hoje prioriza **profundidade estrutural** sobre volume: 12 sugestões inéditas extraídas de leitura de código (não de drift de commit), com foco em **uma violação stack-prescritiva em agente ainda não auditado** (`frontend-developer`, na descrição *e* no corpo), **uma duplicata divergente de skill** (`release-prep` em duas árvores), **um gap de cobertura de validação** (ordem de tools só valida o prefixo) e **uma contradição entre a CLAUDE.md e a implementação do `code-reviewer`** (router que, na prática, é um revisor completo).

---

## 1. Verificação de throughput (cruzamento com git)

```
$ git log -1 --format="%ci %h %s"
2026-05-18 21:41:39 -0300 9f1826d docs(telemetry): add PRIVACY.md, update README and schema docs

$ git log --since="2026-05-22 00:00:00" --oneline
(vazio)
```

Não há nenhum commit após `9f1826d`. A janela 2026-05-22 → 2026-05-23 tem **0 commits**, confirmando **throughput de 0%** pela quinta janela consecutiva (2026-05-18→19, 19→20, 20→21, 21→22 e 22→23 todas a 0%).

**Nota operacional (recorrente, agravando):** o working tree segue com material **não-commitado** — `docs/reports/_index.md` modificado e os diretórios `docs/reports/2026-05-18/` … `2026-05-22/` ainda como *untracked*. São agora **cinco dias** de relatórios de auditoria produzidos e nunca incorporados ao histórico do git. O CI (`check-fingerprint-uniqueness`, README sync, `agent-lint`) nunca os validou porque, para o git, eles não existem.

```
$ git status --short
 M docs/reports/_index.md
?? .claude/user-data/
?? docs/reports/2026-05-18/
?? docs/reports/2026-05-19/
?? docs/reports/2026-05-20/
?? docs/reports/2026-05-21/
?? docs/reports/2026-05-22/
```

---

## 2. Releitura das 3 reaberturas (todas seguem não feitas)

### R1 — `devops-specialist` corpo ainda stack-prescritivo · 🔴 NÃO FEITO

`agents/devops-specialist.md` continua citando tecnologias concretas no corpo (números de linha estáveis; arquivo com 237 linhas):

```
:56  VPS Setup: Linux server … Docker install, Nginx reverse proxy, SSL, Fail2Ban
:62  Monitoring: Prometheus/Grafana, CloudWatch, … Datadog, Loki
:140 | < 1k req/day | Single EC2/VPS + Docker Compose |
:142 | 10k–100k req/day | Auto-scaling container service (ECS, Cloud Run, Container Apps) |
:151 - Don't use Kubernetes when Docker Compose works
:154 - Don't build a service mesh when Nginx handles the routing
:156 - Don't set up a full observability platform (Datadog, Grafana Cloud) when CloudWatch … covers the need
```

Inalterado desde a marcação ⚠️ Partial de 2026-05-18. **Status: 🔴 não feito.**

### R2 — Skills iOS/Android rasas demais · 🔴 NÃO FEITO

```
 33  skills/mobile/ios/SKILL.md
 35  skills/mobile/android/SKILL.md
218  skills/mobile/ios-hig/SKILL.md
221  skills/mobile/material-design/SKILL.md
```

`ios/SKILL.md` (33) e `android/SKILL.md` (35) seguem como wrappers rasos sobre `ios-hig`/`material-design`. Inalterado. **Status: 🔴 não feito.**

### R3 — Gate de lazy-load do design-patterns ausente · 🔴 NÃO FEITO

`skills/architecture/design-patterns/references/composition-root.md` existe (4.608 bytes), mas **nenhum agente o carrega**. Todos seguem puxando o `SKILL.md` inteiro:

- `agents/software-architect.md:29-30` → `design-patterns/SKILL.md → Composition Root section`
- `agents/code-reviewer.md:95` → `design-patterns/SKILL.md`
- `agents/backend-developer.md:212` → `design-patterns/SKILL.md`
- `agents/frontend-developer.md:145` → `design-patterns/SKILL.md → Composition Root section`

A extração foi feita; o gate condicional que a justificaria nunca foi ligado. **Status: 🔴 não feito.**

---

## 3. Discrepância ⚠️ Partial reconfirmada — `size-limits` enforcement

`helpers/size-limits.sh` segue rodando **`--warn-only`** no CI (`ci.yml:28`) e não há sub-script de Stop equivalente. O cap "Max ~200 lines" continua sem enforcement real. Contagem atual (inalterada): **9 de 17 agentes acima de 200 linhas**.

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

## 4. Discrepância de 2026-05-20 reconfirmada — coluna Model do `docs/agents.md` (+ espelho pt-BR)

A correção recomendada em 2026-05-20 **não foi aplicada** (repo congelado). Releitura desta passada confirma o erro nos **dois** arquivos canônicos:

| Arquivo : linha | Listado | Real (frontmatter) | Status |
|-----------------|---------|--------------------|--------|
| `docs/agents.md:26` | `technical-writer` → **Haiku** | `claude-sonnet-4-6` | 🔴 errado |
| `docs/agents.md:27` | `setup-assistant` → **Sonnet** | `claude-opus-4-7` | 🔴 errado |
| `docs/agents.md` (seção `### technical-writer`) | "Assigned **Haiku** for cost efficiency" | Sonnet | 🔴 errado |
| `docs/agents.pt-BR.md:26` | `technical-writer` → **Haiku** | `claude-sonnet-4-6` | 🔴 errado (espelhado) |
| `docs/agents.pt-BR.md:27` | `setup-assistant` → **Sonnet** | `claude-opus-4-7` | 🔴 errado (espelhado) |

O caso Haiku contradiz a própria CLAUDE.md ("Haiku is available for future micro-agents"; **0 agentes usam Haiku**). **Status: 🔴 não feito** — em **dois** arquivos canônicos. A causa-raiz (não há validador cruzando a coluna Model contra o frontmatter) já está registrada em `02/A...` de 2026-05-22.

---

## 5. Pendência de documentação reconfirmada — CHANGELOG `[Unreleased]`

O fingerprint `auto-docs-rule-violated-changelog-unreleased-missing-7-features-from-2026-05-18-window` (2026-05-18) **segue não feito**. Varredura da seção `## [Unreleased]` do `CHANGELOG.md` retorna **0 menções** a telemetria, PRIVACY, helpers, iOS, Android, stack-detection ou archive — exatamente as features observáveis introduzidas na janela de 2026-05-17→19 e exigidas pela Auto-Docs Rule (CLAUDE.md). **Status: 🔴 não feito.**

---

## 6. Falsos positivos descartados nesta passada

A releitura desta passada testou várias hipóteses que **não** viraram sugestão (registradas aqui para rigor e para não reaparecerem como "achados" futuros):

- **Referências de skill quebradas:** revarredura de todos os paths `skills/**/SKILL.md` citados em `agents/` e `commands/` → **100% resolvem** (repo congelado; mantém o resultado de 2026-05-22). (Descartado.)
- **Tabela de commands fora de sincronia:** os **30** arquivos em `commands/*.md` batem 1:1 com as entradas `/devteam:*` da CLAUDE.md — nenhum arquivo sem entrada, nenhuma entrada sem arquivo. (Descartado.)
- **`skill-creator` órfão:** o scanner por substring acusaria `skills/skill-creator/` como órfão (nenhum agente o carrega), mas ele é **user-invocable** (registrado na tabela "User-Invocable Skills" da CLAUDE.md, disparado por `/skill-creator`) e a própria regra de orphan-scan o **exclui**. (Descartado.)
- **`docs/agents.md` com 19 "agentes":** um grep ingênuo de linhas `| \`nome\`` retorna 19, mas **2 dessas linhas pertencem à tabela "## Design Skills"** (`frontend-design`, `web-design-guidelines` — que são skills, não agentes). O roster real é **17/17**, correto. (Descartado.)
- **README "17 agents":** `README.md:13` afirma "17 agents" — confere com os 17 arquivos em `agents/`. (Descartado.)
- **README EN ↔ pt-BR fora de sync:** `README.md` e `README.pt-BR.md` têm **14/14 seções `##` e 244/244 linhas**. (Descartado.)
- **`git-workflow` mal-gateado:** a skill (106 linhas) é carregada por 4 agentes (`software-architect`, `devops-specialist`, `backend-developer`, `qa-specialist`) — todas as 4 cargas são **condicionais** ("when …"). (Descartado.)
- **`lib/session-summary-detect.sh` não enviado no pacote:** o `install.sh` move a árvore `scripts/` inteira (`KEEP_ROOT`), então `scripts/hooks/lib/` **é enviado**; não há bug de hook quebrado em produção. O achado real é apenas a **falta de documentação** (`01/R2`) e a enumeração de chmod (`02/F3`). (Descartado como bug; mantido como doc-gap.)

---

## 7. Recomendação ao mantenedor

O gargalo do projeto **não é geração de sugestões** — são **481 fingerprints** acumulados e **cinco dias** de relatórios prontos. O gargalo é **execução e commit**. Recomenda-se, em ordem:

1. **Commitar** os relatórios pendentes (2026-05-18 → 23) e o `_index.md` para que o CI passe a validá-los.
2. Aplicar as correções de **baixo risco e alto valor** que se acumulam: coluna Model (`docs/agents.md` + `docs/agents.pt-BR.md`), CHANGELOG `[Unreleased]`, e as **3 reaberturas 🔴** (conformidade stack-agnostic + economia de token).
3. Atacar a **nova classe** desta passada: a violação stack-prescritiva do `frontend-developer` (descrição **e** corpo) — terceiro agente da família descrição após `database`/`mobile`/`devops`.
4. Decidir conscientemente sobre o `size-limits` ⚠️ Partial: aplicar enforcement (remover `--warn-only`) ou ajustar o cap documentado para refletir a realidade (9/17 já o excedem).
