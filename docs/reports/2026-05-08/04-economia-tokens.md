# 4. Economia de Tokens (Vetores Inéditos: Worktree Block, REST inline, SonarQube redundante)

← [Voltar ao índice](index.md)

Esta seção identifica **fontes de inflação de tokens** que ainda não foram fingerprintadas nas duas passadas anteriores. O foco aqui são blocos de prosa idênticos repetidos em múltiplos agentes, e conteúdo inline que poderia carregar de skills existentes.

---

## 4.1 Bloco `## Worktree Isolation` está **inline em 7 agentes**, ~22 linhas cada

Sete agentes carregam exatamente o mesmo bloco de 22 linhas:

```text
$ for f in agents/{backend-developer,frontend-developer,database-specialist,
              devops-specialist,ui-ux-designer,backend-test-specialist,
              frontend-test-specialist}.md; do
    awk '/^## Worktree Isolation/,/^---/' "$f" | wc -l
done
22  backend-developer
22  frontend-developer
22  database-specialist
22  devops-specialist
22  ui-ux-designer
22  backend-test-specialist
22  frontend-test-specialist
```

**Total: 154 linhas de prosa idêntica replicada.** Cada agente carrega:

```markdown
## Worktree Isolation

**Before editing or creating any file**, check for an existing session decision:

​```bash
cat .dev-team-agents/.worktree-session 2>/dev/null
​```

| File content | Action |
|---|---|
| `worktree=no` | Continue on the current branch — no question |
| `worktree=yes branch=<b>` | Load `skills/shared/worktree/SKILL.md` using `<b>` — no question |
| File absent | Ask the user (below) |

**If the file is absent**, ask:

> "Do you want this task isolated in a git worktree? [y/N]"

- **Yes** → Ask: "Which branch should the worktree branch off?..."
- **No** → Write `worktree=no` to `.dev-team-agents/.worktree-session`...

---
```

A skill `skills/shared/worktree/SKILL.md` (215 linhas, segundo `wc -l`) **já contém toda essa lógica e mais detalhe**. O bloco inline é redundante: ele duplica a parte mais visível e tira valor da skill.

> **Fingerprint:** `token-worktree-block-inlined-7x`

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | ~150 linhas de prosa removidas dos agentes coding (≈ 1500–2000 tokens em context loading) |
| **Positivo** | Mudanças no fluxo de worktree se aplicam em um só lugar (a skill) |
| **Negativo** | Quando a skill **não** está carregada, o agente perde contexto da decisão; mas o `CLAUDE.md` já manda carregar foundational skills |
| **Negativo** | Aumenta acoplamento entre os 7 agentes e a skill — se ela quebra, todos perdem |

**Recomendação:** substituir o bloco inteiro por:

```markdown
## Worktree Isolation

Apply `skills/shared/worktree/SKILL.md` — it handles session detection, the
y/N prompt, branch selection, and the load of the worktree skill itself.
```

Em 7 agentes × ~20 linhas removidas = **~140 linhas de redução**, mantendo o comportamento via skill.

---

## 4.2 Convenções REST estão inline em `backend-developer` (35+ linhas), apesar da skill `api-design` existir

`agents/backend-developer.md` linhas 64–107 carregam:

- Resource naming (5 linhas)
- HTTP methods (8 linhas, incluindo tabela)
- HTTP status codes (16 linhas, tabela completa)
- Request / Response (4 linhas)
- Idempotency (3 linhas)

Total: ~36 linhas de **referência inline** que descrevem o estado-da-arte de design de API REST.

A skill `skills/architecture/api-design/SKILL.md` existe mas é referenciada por **apenas um agente**: `software-architect`. Isto é, o `backend-developer` reinventa inline o que já mora numa skill curada — e o `software-architect` carrega a skill mas não escreve REST APIs no dia-a-dia.

A inversão certa: **`backend-developer` carrega a skill** (ele é o consumidor primário); o `software-architect` mantém referência conforme já tem.

> **Fingerprint:** `token-rest-conventions-inlined-in-backend`

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | ~35 linhas removidas do `backend-developer` (sempre carregadas em qualquer call) |
| **Positivo** | Skill `api-design` deixa de ter cobertura assimétrica; ganha o consumidor natural |
| **Positivo** | Quando o time atualizar (ex.: adicionar HTTP 425 Too Early), uma única edição |
| **Negativo** | Detalhes super-importantes (ex.: convenção do envelope JSON) saem da boca do agente para uma skill secundária; risco de não serem lidos |

**Recomendação:** mover as subseções "HTTP methods", "HTTP status codes", "Request/Response" e "Idempotency" para `skills/architecture/api-design/SKILL.md` (se ainda não cobrem isso lá), e substituir as linhas 64–107 do `backend-developer.md` por:

```markdown
## REST API Conventions

Load `skills/architecture/api-design/SKILL.md` when implementing or modifying
any REST endpoint. It covers resource naming, HTTP methods, status codes,
request/response envelope, and idempotency.
```

Manter a frase "use plural nouns, never use verbs in URLs" como primer no agente (3 linhas) é OK para reduzir miss da skill em chamadas curtas.

---

## 4.3 Bloco de detecção de SonarQube/SonarCloud é **inline em 10 agentes**

Levantamento via `grep -c "sonar-project.properties" agents/*.md`:

| Agente | Ocorrências |
|--------|-------------|
| backend-developer | 1 |
| backend-reviewer | 1 |
| backend-test-specialist | 2 |
| code-reviewer | 2 |
| devops-specialist | 1 |
| frontend-developer | 1 |
| frontend-reviewer | 1 |
| frontend-test-specialist | 2 |
| qa-specialist | 1 |
| security-specialist | 1 |

O bloco típico (4–6 linhas):

```markdown
**SonarQube / SonarCloud** — if `sonar-project.properties`, `.sonarcloud.properties`,
or `SONAR_TOKEN` is present, load `skills/devops/sonarqube/SKILL.md`. When loaded:
- ...regras específicas do agente...
```

A **detecção** é idêntica nos 10 agentes; só a parte "When loaded:" varia. Isto é exatamente o tipo de coisa que o `skills/shared/project-context/SKILL.md` já faz para Docker dev (`Docker Development Environment`, linhas 177–198): centraliza detecção, e cada agente apenas decide o que fazer **se** a detecção der positivo.

> **Fingerprint:** `token-sonarqube-detection-block-redundant`

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | ~30–40 linhas removidas (3–4 linhas de detecção × 10 agentes) |
| **Positivo** | Adicionar uma quarta heurística (ex.: `sonarqube` service em compose) é uma única edição em `project-context` |
| **Negativo** | A parte "When loaded" ainda fica no agente — agente ainda precisa carregar isso; ganho menor que parece |
| **Negativo** | `project-context` cresce; risco de virar "skill catch-all" |

**Recomendação:** mover a **detecção** para `project-context` numa subseção `## Quality / Security Scanners`, com a regra "if SonarQube detected → load `skills/devops/sonarqube/SKILL.md`". Cada agente mantém apenas a parte "When loaded:" (que **é** específica por agente).

---

## 4.4 Sessões `## Architecture Awareness` em `backend-developer` e `frontend-developer` são paralelas, sem skill compartilhada

`backend-developer.md § Architecture Awareness` (linhas 38–48) descreve **decoupled (API-first) × monolithic (server-rendered)**.
`frontend-developer.md § Architecture Awareness` (linhas 70–82) descreve **decoupled SPA × server-rendered templates**.

São duas seções de ~12 linhas cada com o mesmo eixo conceitual ("decoupled vs monolithic"), só que pelo lado backend e pelo lado frontend. Existe ali um conceito reutilizável: **arquitetura cliente/servidor** — que é exatamente o que uma skill como `skills/architecture/client-server-topology` (não existe) cobriria.

Sem essa abstração, sempre que a equipe ajustar o conteúdo (ex.: adicionar um terceiro modo "edge-rendered SSR") será preciso editar **dois arquivos** e mantê-los coerentes.

> **Fingerprint:** `token-architecture-awareness-block-duplicate`

| Impacto | Detalhe |
|---------|---------|
| **Positivo (extrair skill)** | ~24 linhas removidas dos dois agentes; uma fonte para o eixo decoupled/monolithic |
| **Positivo** | Espaço natural para adicionar SSR-edge, ISR, micro-frontends sem inflar agentes |
| **Negativo** | Pequena nova skill (não é alto retorno isolado); só vale se o conceito for evoluir |
| **Negativo** | Risco de over-engineering — duas seções de 12 linhas é tolerável |

**Recomendação:** **adiar**. Isolar as duas seções num `skills/architecture/topology/SKILL.md` só compensa se o conteúdo for evoluir. Se ficar parado por 6 meses, a duplicação atual tem custo zero. Marcar para revisão na próxima passada (2026-06-XX).

---

## 4.5 `scripts/check-updates.sh` ainda existe como código morto (≈ 70 linhas mantidas)

(Cross-reference com fingerprint `ref-check-updates-script-duplicate` da seção 1.) O ângulo desta seção é **token economy do mantenedor**, não do agente:

- 72 linhas de bash duplicadas;
- Cada vez que `01-check-updates.sh` evolui (ex.: timeout em curl, fingerprintado em 2026-05-07), o `check-updates.sh` precisa ser revisitado;
- Risco real: a versão obsoleta **diverge** silenciosamente da canônica (já está divergindo: a obsoleta não tem auto-update).

Removendo o script duplicado, **o repositório livra ~70 linhas de bash mantidas em paralelo**, e o `commands/update.md` passa a chamar `update.sh --check` (que já delega corretamente).

> **Fingerprint:** `token-update-script-duplicate-bytes`

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | ~70 linhas de bash a menos para revisar a cada release |
| **Positivo** | Elimina classe inteira de bug "atualizei o hook mas esqueci do script legado" |
| **Negativo** | Quem chamar `check-updates.sh` direto via shell quebra (mitigar via shim de 1 linha) |

**Recomendação:** já coberta na seção 1 — converter `scripts/check-updates.sh` em shim de 1 linha **ou** removê-lo e atualizar `commands/update.md`. Foco aqui é só destacar que o ganho é também de **economia de tokens de manutenção**, não só de runtime.

---

## 4.6 `## Foundational Rule — Load Context First` é repetido em **15 dos 16 agentes**, com pequena variação

Levantamento parcial: todos os agentes coding e de revisão começam com:

```markdown
## Foundational Rule — Load Context First

**Before [acting/writing code/reviewing]**, load the project context in this order:
1. README.md ...
2. CLAUDE.md ...
3. docs/project.md ...
4. .dev-team-agents/user-data/session-summary.md ...
5–11. (variações por agente: architecture, code-standards, design-system...)
12. Run `git log --oneline -20` ...
```

O fingerprint **`token-context-loading-dedup`** (2026-05-06) e **`token-foundational-rule-template`** (2026-05-06) já cobriram a deduplicação macro: substituir tudo por `Load skills/shared/project-context/SKILL.md`.

O ângulo **inédito** desta passada: os items 1–4 são **idênticos** nos 16 agentes. Os items 5–11 (que variam) **também** poderiam ser deduplicados via "ProjectContext-extension" — cada agente declara apenas os arquivos da camada `development/` que precisa.

Hipótese:

```markdown
## Foundational Rule

Load skills/shared/project-context/SKILL.md (handles steps 1–4 + git log).
Then read these task-specific files:
- docs/development/architecture.md
- docs/development/code-standards.md
- (specifics per agent)
```

Em vez de repetir 11 itens, repete-se só o subset variável (3–5 itens). Nos 16 agentes, somam-se ~6–8 linhas a menos por agente = ~100 linhas removidas no total.

> **Fingerprint:** `token-foundational-rule-extension-pattern`

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | ~100 linhas removidas no agregado (refinement do fingerprint anterior, não duplicação) |
| **Positivo** | Documenta o padrão "core context + extensions" como design pattern do repo |
| **Negativo** | Mudança coordenada em 16 arquivos; não-trivial |
| **Negativo** | Aproxima do *anti-pattern* "skill que chama skill que chama skill"; manter ≤ 1 nível de indireção |

**Recomendação:** aplicar gradualmente em conjunto com a refatoração `token-foundational-rule-template` (já fingerprintado). O ganho aqui é incremental ao já registrado, mas significativo no agregado.

---

## 4.7 Resumo de fingerprints novos

| Fingerprint | Tema |
|-------------|------|
| `token-worktree-block-inlined-7x` | `## Worktree Isolation` (~22 linhas) duplicado em 7 agentes coding |
| `token-rest-conventions-inlined-in-backend` | 35+ linhas de REST inline no `backend-developer`; skill `api-design` existe |
| `token-sonarqube-detection-block-redundant` | Detecção de SonarQube duplicada em 10 agentes |
| `token-architecture-awareness-block-duplicate` | Sessão "Architecture Awareness" paralela em backend e frontend developers |
| `token-update-script-duplicate-bytes` | `scripts/check-updates.sh` mantido em paralelo com hook canônico |
| `token-foundational-rule-extension-pattern` | Items 1–4 do Foundational Rule são idênticos em 16 agentes; refinamento do anterior |
