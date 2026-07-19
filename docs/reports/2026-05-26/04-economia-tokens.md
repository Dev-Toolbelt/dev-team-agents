# Relatório — Economia de Tokens

**Data:** 2026-05-26
**Janela auditada:** 2026-05-24 → 2026-05-26
**Foco:** ângulos novos de desperdício de token mensurados nesta passada (sub-escopos refinados ou seções nunca auditadas no eixo token).

---

## T1 — `frontend-code-quality` description tem 288 chars (3× o budget de 95) e a cauda meta-narrativa "Loaded by frontend-developer as the authoritative quality baseline" custa ~70 chars de pura redundância — sub-escopo concreto do fingerprint de 2026-05-24 com o pior offender mensurado

**Fingerprint:** `token-frontend-code-quality-description-288-chars-cauda-loaded-by-frontend-developer-as-authoritative-redundant-trim-target-70-chars-pior-offender-confirmado-na-relista-de-2026-05-26`

**Severidade:** **MEDIUM**

**Evidência:**

```bash
$ for f in $(find skills/ -name "SKILL.md"); do
    desc=$(awk '/^description:/{sub(/^description:[ ]*/, ""); print; exit}' "$f")
    [ ${#desc} -gt 200 ] && echo "${#desc} $f"
  done | sort -rn

288 skills/architecture/frontend-code-quality/SKILL.md
250 skills/shared/frontend-done-checklist/SKILL.md
250 skills/design/mobile-design/SKILL.md
247 skills/shared/architecture-awareness/SKILL.md
239 skills/mobile/material-design/SKILL.md
238 skills/mobile/ios-hig/SKILL.md
235 skills/shared/runbook/SKILL.md
```

Descrição atual de `frontend-code-quality` (288 chars):

> Base code quality standards for frontend development — component size, state management, semantic HTML, accessibility, performance, loading states, metadata, KISS/YAGNI/DRY principles, type safety, and prop sprawl rules. **Loaded by frontend-developer as the authoritative quality baseline.**

A frase em negrito (~70 chars / **24% do total**) é **meta-narrativa interna** — informa _quem_ carrega a skill, não _o que_ ela contém. Essa informação pertence ao agente consumidor (`frontend-developer.md`), não ao description que vai para o índice de skills lido pelo Claude em todo bootstrap.

**Comparação com skills bem dimensionadas:**

```text
graphql:    "GraphQL — schema, resolvers, N+1/DataLoader, pagination."  (59 chars)
gotrue:     "GoTrue auth — JWT validation, app_metadata, RLS handoff."   (~60 chars)
```

`graphql` (235 linhas de skill) descreve-se em 59 chars; `frontend-code-quality` precisa de 288. A discrepância não está no conteúdo, está em **incluir narrativas sobre o consumidor**.

**Impacto:**

- O índice de skills é carregado em cada bootstrap de agente. Os top-7 descriptions (288, 250, 250, 247, 239, 238, 235) somam **1.747 chars** vs ~700 chars idealmente — **diferença ~1.000 chars × 17 agentes = ~17.000 chars/sessão multi-agente** carregados sem necessidade.
- `frontend-code-quality` sozinha pode cair para ~95 chars: `"Frontend code quality baseline — size, state, semantic HTML, a11y, perf, KISS/DRY."` (~85 chars).

**Recomendação:**

Trim em 2 categorias:

1. **Remover cauda meta-narrativa** ("Loaded by X as the authoritative…", "Used when…", "Required for…"). Essa informação fica no agente, não na skill.
2. **Substituir lista exaustiva** ("component size, state management, semantic HTML, accessibility, performance, loading states, metadata, KISS/YAGNI/DRY principles, type safety, and prop sprawl rules") por agrupamento ("size, state, semantic HTML, a11y, perf, principles, type safety").

Aplicar a regra aos 7 maiores descriptions; estender `helpers/agent-lint.sh` para validar `len(description) <= 95` em SKILL.md (já pedido por outro fingerprint hoje em F3).

**Por que original:** o fingerprint `token-sixteen-skill-descriptions-exceed-95-char-budget-worst-288-inflate-always-loaded-skill-index-regression-of-v1-5-3` (2026-05-24) **deu o número 288** mas não atribuiu ao arquivo nem mostrou a cauda concreta a remover. Este sub-escopo: (a) identifica o pior offender, (b) isola o "what to delete", (c) propõe nova string concreta. Diferente angulação operacional.

---

## T2 — `CLAUDE.md` ainda em 426 linhas; Commands Table (40 linhas) + Stop Sub-script Convention (24 linhas) + Hook Files Map (8 linhas) = 72 linhas extraíveis para sub-arquivos `CLAUDE-md/` que **já existem** mas estão sub-utilizados

**Fingerprint:** `token-claude-md-426-lines-still-monolithic-three-extractable-blocks-commands-table-40-stop-sub-script-convention-24-hook-files-map-8-total-72-lines-while-claude-md-folder-already-exists-with-preferences-notifications-user-data-versioning`

**Severidade:** **MEDIUM-HIGH**

**Evidência:**

```bash
$ wc -l CLAUDE.md
426 CLAUDE.md

$ ls CLAUDE-md/
notifications.md   preferences.md   user-data.md   versioning.md
```

A "fase 1" da fragmentação (User Preferences → `CLAUDE-md/preferences.md`, Notifications → `CLAUDE-md/notifications.md`, User Data → `CLAUDE-md/user-data.md`, Versioning → `CLAUDE-md/versioning.md`) **já abriu o padrão**. Mas ficou parada — 4 sub-arquivos quando há ~10 blocos elegíveis.

Blocos ainda inline na CLAUDE.md que estouram em todo agent spawn:

| Bloco | Linhas | Sugestão de destino |
|---|---:|---|
| Commands Table (linhas ~140-195) | ~40 | `CLAUDE-md/commands.md` |
| Stop Sub-script Convention (linhas ~340-365) | ~24 | `CLAUDE-md/hooks.md` |
| Hook Files Map (linhas ~370-378) | ~8 | `CLAUDE-md/hooks.md` (mesmo arquivo) |
| **Total imediato** | **~72** | |

**Estado anterior do banco:**

- `token-CLAUDE-md-426-lines-still-monolithic-stop-sub-script-convention-table-and-hook-files-map-and-package-exclusions-not-extracted-after-fragmentation-fase-1` (2026-05-18) — **HIGH**, ainda pendente.

→ Este sub-escopo refina com **medições atualizadas** (CLAUDE.md ainda em 426, 0 deltas desde 2026-05-18) e propõe o **destino concreto** (`CLAUDE-md/commands.md`, `CLAUDE-md/hooks.md`), demonstrando que o padrão de fragmentação **já está aceito** pelo repo (4 sub-arquivos existem). A barreira não é arquitetural, é de execução.

**Impacto:**

- Cada bootstrap de agente recebe CLAUDE.md via `claudeMd` system reminder. 426 linhas × 17 agentes em um `/devteam:fullstack` = ~7.200 linhas processadas em paralelo só de framework doc.
- Extração de 72 linhas: economia de ~17% nesse vetor (≈1.200 linhas/sessão multi-agente).
- A Commands Table é raramente consultada **durante** execução de um agente — é referência para humanos selecionarem comando. Extrair para `CLAUDE-md/commands.md` (lazy load via "see also") é zero perda funcional.

**Recomendação:**

Mover **agora** 2 blocos:

1. Commands Table → `CLAUDE-md/commands.md` (40 linhas)
2. Stop Sub-script Convention + Hook Files Map → `CLAUDE-md/hooks.md` (~32 linhas combinadas)

Em CLAUDE.md, substituir cada bloco por:

```markdown
## User-Invocable Commands
→ See [`CLAUDE-md/commands.md`](CLAUDE-md/commands.md) for the canonical roster (30 commands, parallel agent matrix).
```

(Mesmo padrão das 4 extrações já feitas.) Esforço: **15 min**.

**Por que original:** o fingerprint anterior listou os blocos mas não mostrou que **a infraestrutura de destino já existe**. Este angle quebra o pretexto de "muito trabalho" — basta seguir o padrão que **o próprio repo já normalizou**.

---

## T3 — `agents/setup-assistant.md` carrega `skills/devops/docker-dev/SKILL.md` implicitamente em todo onboarding ao executar `Docker Compose version detection` inline (linhas 60-70) — gasta ~120 tokens no agente E ~600 tokens na skill correspondente quando o projeto sequer usa Docker

**Fingerprint:** `token-setup-assistant-inline-docker-compose-detection-block-60-70-spawned-on-every-onboarding-regardless-of-docker-presence-120-tokens-eager-plus-implicit-load-of-docker-dev-skill-when-project-has-no-docker`

**Severidade:** **MEDIUM**

**Evidência:**

Linhas 60-70 do `setup-assistant.md` (ver A2): 10 linhas de bash de detecção Docker no corpo do agente, **antes** de qualquer condição de detecção. O agente carrega esse bloco em todo onboarding — mesmo em projeto Python+SQLite, Rust+nada, PHP-procedural-shared-hosting, front-end-estático etc.

**Cálculo:**

- 10 linhas × ~12 tokens/linha = **~120 tokens/spawn** carregados desnecessariamente em projetos sem Docker.
- O setup-assistant é o primeiro agente spawneado em todo onboarding (regra "Setup Trigger" da CLAUDE.md:421) — multiplica em **100% das instalações**.
- Em onboarding de projetos com Docker, o bloco já está **no agente**, então a skill `docker-dev` (que tem o mesmo padrão duplicado) é carregada por cima — token desperdiçado em ambos os caminhos.

**Comparação com o ideal:**

- Pattern atual: bloco bash inline + nenhuma detecção condicional.
- Pattern correto (já usado por `database-specialist`, `mobile-developer`): tabela "Detection Signals" → skill load condicional.

**Status no banco:**

- A2 deste mesmo relatório trata da **dimensão de stack-agnosticism** (princípio violado).
- Este fingerprint trata da **dimensão de token** (custo concreto).
- Distinto de `token-backend-developer-integration-awareness-inline-critical-rules-70-80-lines-eager-loaded-every-spawn-defeats-lazy-skill-detection-pattern` (2026-05-20) — aquele era backend-developer + 70-80 linhas de 7 integrações; este é setup-assistant + 10 linhas de Docker isolado mas com 100% de fan-out no onboarding.

**Impacto:**

- Em 1 onboarding sem Docker: ~120 tokens perdidos.
- Em 1 onboarding com Docker: ~120 tokens + carga implícita da skill `docker-dev` (~600 tokens) duplicando.
- Setup-assistant é o **único agente sem alternativa** — não há "outro caminho" para o usuário no primeiro contato com o repo. Custo é 100% atrelado à decisão de adotar dev-team-agents.

**Recomendação:**

Substituir as linhas 60-70 por:

```markdown
**Runtime tooling:** If `Dockerfile` or `docker-compose*.yml` is detected,
load `skills/devops/docker-dev/SKILL.md` § "Compose version detection" and
record the resolved command in the project's `CLAUDE.md`.
```

Esforço: ~5 min. Economia: 120 tokens × 100% das instalações + elimina duplicação semântica com a skill.

**Por que original:** ângulo de token distinto de A2 (mesmo achado, dimensão diferente). Pareando: **A2 = "viola princípio"; T3 = "custa X tokens em Y% dos casos"**. Ambos os ângulos justificam fingerprints separados pela convenção do banco (categoria diferente: `agent-*` vs `token-*`).

---

## Sumário das 3 recomendações

| # | Fingerprint | Severidade | Economia esperada |
|---|---|---|---|
| T1 | `frontend-code-quality` description 288 chars; trim 70 chars de cauda meta | MEDIUM | ~17k chars/sessão multi-agente |
| T2 | CLAUDE.md 426 linhas; extrair 72 linhas para `CLAUDE-md/{commands,hooks}.md` | MEDIUM-HIGH | ~1.200 linhas/sessão multi-agente |
| T3 | `setup-assistant` inline Docker detection — 100% fan-out no onboarding | MEDIUM | ~120 tokens × 100% das instalações |

Total potencial: **3 mudanças pequenas** (~30 min combinados), com economia sobre **o pior caminho de carga** (multi-agent + onboarding).
