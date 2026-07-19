# Auditoria Guardian — 2026-05-26

> **Modo Guardian:** verifica se o que está marcado como ✅ Executed nos passes
> anteriores realmente foi implementado, reverifica as reaberturas abertas, e
> calcula o throughput real na janela observada.

---

## 1. Janela observada

| Métrica | Valor |
|---|---|
| Última passada com auditoria | 2026-05-24 |
| Janela auditada | 2026-05-24 → 2026-05-26 |
| Commits na janela | **0** |
| Throughput de execução | **0%** |
| Último commit do repo | `9f1826d` — 2026-05-18 21:41:39 -0300 |
| Tempo desde o último commit | **~7,3 dias** (8ª janela consecutiva com 0 commits) |

Comando de verificação:

```bash
git log --since="2026-05-24" --oneline   # vazio
git log -1 --format="%H %ci"             # 9f1826d 2026-05-18 21:41:39 -0300
```

---

## 2. Reaberturas pendentes (3 itens de 2026-05-18)

Releitura arquivo a arquivo: as 3 reaberturas seguem **🔴 não feitas**.

### 2.1 `devops-specialist` corpo stack-prescritivo

- **Arquivo:** `agents/devops-specialist.md`
- **Linhas confirmadas hoje:**
  - `54` (`Primary: Docker`)
  - `56` (`VPS Setup: Linux server — Docker install, Nginx reverse proxy`)
  - `58` (`CI/CD: GitHub Actions (primary), Bitbucket Pipelines, GitLab CI, Jenkins, Azure DevOps, AWS CodePipeline`)
  - `60` (`Cloud: AWS, GCP, Azure`)
  - `62` (`Monitoring: Prometheus/Grafana, CloudWatch, Datadog, Loki`)
  - `64` (`IaC: Terraform/OpenTofu`)
  - `140` (`Single EC2/VPS + Docker Compose`)
  - `143` (`Kubernetes`)
  - `151–156` (anti-overengineering: Docker Compose, Nginx, Datadog, Grafana Cloud, CloudWatch, Prometheus)
- **Status:** 🔴 não feito — após 8 dias

### 2.2 iOS/Android skills rasas

- `skills/mobile/ios/SKILL.md`: **33 linhas** (vs `ios-hig` = 218)
- `skills/mobile/android/SKILL.md`: **35 linhas** (vs `material-design` = 221)
- Cada uma começa com "Load `…/ios-hig/SKILL.md`" / "Load `…/material-design/SKILL.md`" — wrappers rasos sem fronteira de conteúdo
- **Status:** 🔴 não feito

### 2.3 `design-patterns` lazy-load gate ausente

- `skills/architecture/design-patterns/references/composition-root.md` existe (extração ✅ 2026-05-18)
- Mas estes 4 agentes ainda puxam o `SKILL.md` inteiro:
  - `software-architect.md:29-30`
  - `code-reviewer.md:95`
  - `backend-developer.md:198,212`
  - `frontend-developer.md:145`
- **Status:** 🔴 não feito — gate condicional nunca foi adicionado

---

## 3. ⚠️ Partial mantido — `size-limits` enforcement

`helpers/size-limits.sh` ainda roda `--warn-only` em CI; **9/17 agentes** estouram o cap de 200 linhas (mesma contagem desde 2026-05-19):

| Agente | Linhas | Excesso |
|---|---:|---:|
| `frontend-test-specialist` | 262 | +62 |
| `backend-developer` | 261 | +61 |
| `setup-assistant` | 239 | +39 |
| `devops-specialist` | 237 | +37 |
| `security-specialist` | 234 | +34 |
| `frontend-developer` | 232 | +32 |
| `code-reviewer` | 228 | +28 |
| `qa-specialist` | 208 | +8 |
| `backend-reviewer` | 204 | +4 |

Soma de excesso: **305 linhas** (~4 mil tokens por fluxo multi-agente).

---

## 4. 🔴 Discrepância de 2026-05-20 — `docs/agents.md` coluna Model

- `docs/agents.md:26` lista `technical-writer` como **Haiku** → frontmatter real: `claude-sonnet-4-6`
- `docs/agents.md:27` lista `setup-assistant` como **Sonnet** → frontmatter real: `claude-opus-4-7`
- Espelhado em `docs/agents.pt-BR.md` (sync rule propagou o erro)
- **Status:** 🔴 sem correção há 7 dias; nenhum validador cruza coluna Model × frontmatter

---

## 5. 🔴 CHANGELOG x git tag — deriva de release confirmada

```bash
git tag | sort -V | tail -5
# v1.6.5  v1.6.6  v1.6.7  v1.7.0  +malformadas v.1.1.0 v.1.3.13

grep "^## \[" CHANGELOG.md | head -3
# ## [Unreleased]
# ## [1.4.0] — 2026-05-10
```

- HEAD `9f1826d` corresponde a tag `v1.7.0`
- Última versão documentada no CHANGELOG: `[1.4.0]`
- Deriva: **3 minor versions** (`v1.5.0` → `v1.7.0`) e cerca de **7 patches** sem entrada
- **Status:** 🔴 não corrigido (1º cross-check feito em 2026-05-24)

---

## 6. `.gitignore` malformado — confirmado

```bash
$ cat .gitignore | tail -3
.claude/settings.local.json
.claude/user-data/session-summary.md
.claude/user-data/.notifier-stateuser-data/
```

A linha 7 funde `.notifier-state` e `user-data/` numa única entrada inválida.
`git check-ignore` confirma que `.claude/user-data/` **não é ignorado**.
**Status:** 🔴 — causa-raiz já identificada em 2026-05-24, mas sem fix.

---

## 7. Falsos positivos descartados

- **Refs de skill:** 130 paths `skills/.../SKILL.md` em `agents/`, `commands/`, `skills/`, `workflows/`, `helpers/`, `scripts/`, `CLAUDE.md` — **129/130 resolvem**. O único "MISSING" é `skills/agent-creator/SKILL.md`, citado apenas em `CLAUDE.md:130` como **path `.claude/skills/...` instalado pelo cliente Claude global**, não path interno do repo (esperado).
- **`skill-creator` órfão:** é user-invocable, excluído pela regra do CLAUDE.md.
- **`fullstack.md` faltando session-summary:** descartado — o arquivo tem `Session summary written` na lista de Workflow Closure (apenas o termo grep com hífen `session-summary` não bate, mas o passo está presente). Reverte parcialmente a discrepância de 2026-05-23 `flow-session-summary-closure-step-present-in-eight-of-ten-workflows-but-absent-from-fullstack-and-refactor-highest-fanout`: ele se aplica APENAS a `refactor.md` (ver 02/F2 do report do dia).
- **Fingerprint uniqueness:** `bash helpers/check-fingerprint-uniqueness.sh` reporta **"All fingerprint slugs are unique"** — gate verde.
- **Orphan template scan:** reporta apenas `templates/backlog-template.md` (esperado — sub-escopo de 2026-05-18 ainda pendente).
- **Orphan skill scan:** confirma 2 duplicate loads conhecidos (ui-ux-designer, commands/update.md) — pendentes há dias.

---

## 8. Resumo do throughput consecutivo

| Janela | Commits | Throughput |
|---|---:|---:|
| 2026-05-18 → 2026-05-19 | 0 | 0% |
| 2026-05-19 → 2026-05-20 | 0 | 0% |
| 2026-05-20 → 2026-05-21 | 0 | 0% |
| 2026-05-21 → 2026-05-22 | 0 | 0% |
| 2026-05-22 → 2026-05-23 | 0 | 0% |
| 2026-05-23 → 2026-05-24 | 0 | 0% |
| 2026-05-24 → 2026-05-26 | 0 | 0% |

**8ª janela consecutiva com 0 commits.** O backlog acumulado de 12 fingerprints/dia × 6 dias (=72 sugestões) permanece inteiramente pendente, somando-se as 3 reaberturas, o ⚠️ Partial do `size-limits` e as discrepâncias estruturais novas (`docs/agents.md` Model, CHANGELOG drift, `.gitignore`).

---

## 9. Recomendação operacional

1. Priorizar **commit das pendências de release** (CHANGELOG → `[1.5.0]`…`[1.7.0]`, `.gitignore` fix, modelos no `docs/agents.md` × `pt-BR`) antes de aceitar novos fingerprints — caso contrário a próxima passada (2026-05-27) entregará outro `_index.md` ainda mais inflado sem nenhum reset.
2. Promover os 2 itens de **bug crítico latente** (4 dias+ no banco) a ↩️ caso a decisão consciente seja não corrigir — mas ações concretas estão paradas, não decisões.

---

**Próximo Guardian:** 2026-05-27 (cruzar `git log --since="2026-05-26"`).
