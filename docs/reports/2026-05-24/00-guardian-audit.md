# Auditoria Guardian — 2026-05-24

> Décima nona passada. Verificação cruzada com `git log` **e `git tag`**, releitura arquivo a arquivo das pendências antigas e marcação de status (✅ feito / ⚠️ parcial / 🔴 não feito) para o histórico.

---

## Resumo executivo

| Indicador | Valor |
|-----------|-------|
| Janela auditada | 2026-05-23 → 2026-05-24 |
| Commits na janela | **0** |
| Throughput de implementação | **0%** (6ª janela consecutiva) |
| Último commit do repo | `9f1826d` — 2026-05-18 21:41 -0300 |
| Tempo congelado | **~6,1 dias** |
| Reaberturas antigas | 3 seguem 🔴 não feitas |
| ⚠️ Partial confirmado | `size-limits` enforcement (9/17 agentes > 200 linhas) |
| Discrepância de 2026-05-20 | `docs/agents.md` + `docs/agents.pt-BR.md` coluna Model **ainda errada** 🔴 |
| Pendência de doc (2026-05-18) | CHANGELOG `[Unreleased]` ainda **omite** telemetria/PRIVACY/helpers/iOS/Android/archive |
| **Descoberta nova (crítica)** | O CHANGELOG não está só "incompleto": **as tags `v1.5.0`–`v1.7.0` já foram criadas** e o `HEAD` **é** `v1.7.0` — o conteúdo do `[Unreleased]` **já foi lançado** sob 6 tags. Detalhe em `02/F1`. |
| Sugestões originais hoje | 12 (3 por categoria) |

**Conclusão:** o repositório está congelado há mais de **seis dias**. Nenhum fingerprint pendente foi endereçado por commit. Pela sexta janela consecutiva a geração de hoje prioriza **profundidade estrutural** sobre volume. A passada de hoje incluiu pela primeira vez o cruzamento com `git tag`, que revelou a descoberta mais relevante do ciclo: **o CHANGELOG está 3 versões minor atrás das tags** (a pendência de doc não é "esquecimento de `[Unreleased]`", é deriva de release real). Além disso, a leitura de arquivos recém-criados encontrou: um **`.gitignore` malformado** (causa-raiz da nota recorrente de "user-data não-rastreado"), um **TODO de pré-release na telemetria que dispara por padrão**, **conteúdo de notificação triplicado** e a **skill `user-preferences` defasada** do schema autoritativo.

---

## 1. Verificação de throughput (cruzamento com git)

```
$ git log -1 --format="%ci %h %s"
2026-05-18 21:41:39 -0300 9f1826d docs(telemetry): add PRIVACY.md, update README and schema docs

$ git log --since="2026-05-23 00:00:00" --oneline
(vazio)
```

Não há nenhum commit após `9f1826d`. A janela 2026-05-23 → 2026-05-24 tem **0 commits**, confirmando **throughput de 0%** pela sexta janela consecutiva (18→19, 19→20, 20→21, 21→22, 22→23 e 23→24 todas a 0%).

**Nota operacional (recorrente — agora com causa-raiz identificada):** o working tree segue com material **não-commitado** — `docs/reports/_index.md` modificado e os diretórios `docs/reports/2026-05-18/` … `2026-05-23/` ainda como *untracked*, além de `.dev-team-agents/user-data/`. **A causa de `.dev-team-agents/user-data/` aparecer como untracked foi finalmente localizada nesta passada:** o `.gitignore` tem uma linha malformada que não casa com o diretório (ver `02/F3`). São agora **seis dias** de relatórios de auditoria produzidos e nunca incorporados ao histórico do git.

```
$ git status --short
 M docs/reports/_index.md
?? .dev-team-agents/user-data/
?? docs/reports/2026-05-18/ … 2026-05-23/
```

---

## 2. Releitura das 3 reaberturas (todas seguem não feitas)

### R1 — `devops-specialist` corpo ainda stack-prescritivo · 🔴 NÃO FEITO

`agents/devops-specialist.md` (237 linhas) continua citando tecnologias concretas no corpo, números de linha estáveis:

```
:56  VPS Setup: … Docker install, Nginx reverse proxy, SSL, Fail2Ban
:62  Monitoring: Prometheus/Grafana, CloudWatch, … Datadog, Loki
:85  amazon-cloudwatch-agent.json or CloudWatch resource in Terraform
:140 | < 1k req/day | Single EC2/VPS + Docker Compose |
:142 | 10k–100k req/day | Auto-scaling container service (ECS, Cloud Run, Container Apps) |
:151 Don't use Kubernetes when Docker Compose works
:156 Don't set up a full observability platform (Datadog, Grafana Cloud) …
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

`skills/architecture/design-patterns/references/composition-root.md` existe (4.608 bytes), mas **nenhum agente o carrega**. Todos seguem puxando o `SKILL.md` inteiro: `software-architect:29-30`, `code-reviewer:95`, `backend-developer:212`, `frontend-developer:145`. A extração foi feita; o gate condicional que a justificaria nunca foi ligado. **Status: 🔴 não feito.**

---

## 3. Discrepância ⚠️ Partial reconfirmada — `size-limits` enforcement

`helpers/size-limits.sh` segue rodando **`--warn-only`** no CI (`ci.yml:28`) e não há sub-script de Stop equivalente. O cap "Max ~200 lines" continua sem enforcement real. Contagem atual (inalterada): **9 de 17 agentes acima de 200 linhas**.

```
262 frontend-test-specialist   232 frontend-developer
261 backend-developer          228 code-reviewer
239 setup-assistant            208 qa-specialist
237 devops-specialist          204 backend-reviewer
234 security-specialist        (199 mobile-developer — no limite)
```

**Status: ⚠️ Partial mantido.**

---

## 4. Discrepância de 2026-05-20 reconfirmada — coluna Model do `docs/agents.md` (+ espelho pt-BR)

A correção recomendada em 2026-05-20 **não foi aplicada** (repo congelado). Releitura desta passada confirma o erro nos **dois** arquivos canônicos:

| Arquivo : linha | Listado | Real (frontmatter) | Status |
|-----------------|---------|--------------------|--------|
| `docs/agents.md:26` | `technical-writer` → **Haiku** | `claude-sonnet-4-6` | 🔴 errado |
| `docs/agents.md:27` | `setup-assistant` → **Sonnet** | `claude-opus-4-7` | 🔴 errado |
| `docs/agents.pt-BR.md:26-27` | idem (espelhado) | idem | 🔴 errado |

**Status: 🔴 não feito** — em **dois** arquivos canônicos.

---

## 5. Pendência de documentação reconfirmada **e reclassificada** — CHANGELOG

O fingerprint `auto-docs-rule-violated-changelog-unreleased-missing-7-features-from-2026-05-18-window` (2026-05-18) **segue não feito**. A varredura da seção `## [Unreleased]` retorna **0 menções** a telemetria, PRIVACY, helpers, iOS, Android, stack-detection ou archive. **Status: 🔴 não feito.**

**Reclassificação importante (descoberta de hoje):** o cruzamento com `git tag` mostrou que o problema é **mais grave do que "esquecer de preencher `[Unreleased]`"**. As tags `v1.5.0`, `v1.5.1`…`v1.6.7` e **`v1.7.0`** já existem e apontam para commits desta história (`v1.7.0` → `9f1826d`, o próprio `HEAD`). Ou seja: **o conteúdo do `[Unreleased]` já foi lançado sob 6 tags**, mas o CHANGELOG ainda diz que a última release é a `[1.4.0]`. Isso reposiciona a pendência de "doc atrasada" para "**deriva de versionamento real**". Detalhe e remediação em `02/F1`.

---

## 6. Causa-raiz encontrada para uma nota operacional antiga

Por **5 passadas** os relatórios anotaram que `.dev-team-agents/user-data/` aparece como *untracked* no working tree, tratando isso como "material não-commitado". A releitura do `.gitignore` desta passada encontrou a **causa-raiz**: a última linha do arquivo está **malformada** (`.dev-team-agents/user-data/.notifier-stateuser-data/`), fundindo duas entradas numa só que não casa com nada. `git check-ignore` confirma que `.dev-team-agents/user-data/` **não está sendo ignorado**. Não é "esqueceram de commitar" — é "o ignore está quebrado". Detalhe em `02/F3`.

---

## 7. Falsos positivos descartados nesta passada

A releitura testou hipóteses que **não** viraram sugestão (registradas para rigor e para não reaparecerem como "achados" futuros):

- **Referências de skill quebradas:** revarredura dos paths `skills/**/SKILL.md` citados em `agents/` e `commands/` → **100% resolvem** (repo congelado).
- **`skill-creator` órfão:** é **user-invocable** (disparado por `/skill-creator`), excluído pela regra de orphan-scan. (Descartado.)
- **README "17 agents":** confere com os 17 arquivos em `agents/`. (Descartado.)
- **Arrays de tips do notifier desbalanceados:** `TIPS_EN`, `TIPS_PTBR` e `TIPS_ES` têm **15 entradas cada** — índice `(DAY-1) % 15` nunca estoura. Sem bug de índice. (Descartado como bug; a **duplicação** script×skill vira o achado `01/R1`.)
- **`backend-developer` description "decoupled (REST API, GraphQL)" = produtos:** REST/GraphQL/MVC são **paradigmas**, não frameworks/linguagens — bem mais brando que as enumerações de produtos já flagradas (database/mobile/frontend). Mantido como achado **LOW** honesto em `03/A3`, não como violação dura.
- **`user-preferences` skill inexistente:** ela **existe** (`skills/shared/user-preferences/SKILL.md`, 3.982 B) — não é referência quebrada. O achado real é que ela está **defasada** do schema (`03/A2`), não ausente. (Descartado como ref quebrada.)

---

## 8. Recomendação ao mantenedor

O gargalo do projeto **não é geração de sugestões** — são **493 fingerprints** acumulados e **seis dias** de relatórios prontos. O gargalo é **execução e commit**. Em ordem de prioridade desta passada:

1. **Reconciliar versionamento × CHANGELOG** (`02/F1`): promover `[Unreleased]` para as seções `1.5.0`…`1.7.0` já tagueadas — esta é a maior dívida de governança encontrada.
2. **Corrigir o `.gitignore` malformado** (`02/F3`): destrava o rastreio de `user-data/` e encerra a nota operacional recorrente.
3. **Resolver o TODO de pré-release da telemetria** (`02/F2`) — caminho default-on com chave marcada "replace before release".
4. **Sincronizar as fontes duplicadas**: conteúdo de notificação triplicado (`01/R1`) e schema de preferências defasado na skill (`03/A2`).
5. Aplicar as correções acumuladas de baixo risco: coluna Model, as 3 reaberturas 🔴 e a decisão consciente sobre `size-limits`.
