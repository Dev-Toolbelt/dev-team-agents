# Relatório 2026-05-17 — Economia de Tokens

> 12ª passada. Foco quantitativo: custo dos novos blocos introduzidos hoje (Workflow Detection em software-architect + Composition Root em 3 agents), inflação do `_index.md` (552 linhas), assimetria de fragmentação CLAUDE.md vs skills, gaps de lazy-load condicional.

> **Base de cálculo:** 1 linha ≈ 16 tokens (padrão arquivado em passadas anteriores). Multipliers aplicados a fanout por session/spawn.

---

## 1. `token-software-architect-workflow-detection-25-lines-inline-x-9-architect-spawn-commands-fan-out-3600-tokens-per-multi-architect-flow`

**Categoria:** custo do bloco novo introduzido hoje
**Severidade:** HIGH

Bloco "Workflow Detection" em `agents/software-architect.md:45-69` tem **25 linhas** (~400 tokens). `software-architect` é spawneado em 9 commands:

`/devteam:plan`, `/devteam:fix`, `/devteam:refactor`, `/devteam:fullstack`, `/devteam:architect`, `/devteam:adr`, `/devteam:review`, `/devteam:dba`, `/devteam:security`.

| Cenário | Spawns de `software-architect` | Tokens replicados do bloco |
|---------|------------------------------|----------------------------|
| Sessão simples (`/devteam:plan`) | 1 | 400 |
| Sessão fullstack (`/devteam:fullstack` + `/devteam:review`) | 2 | 800 |
| Sessão refactor formal (`/devteam:refactor`) | 1 (entry) + N waves | 400–1.600 |
| **Worst-case multi-architect flow** | 9 spawns ao longo do dia | **3.600 tokens/sessão diária** |

**Economy mediante extração para `skills/shared/workflow-detection/SKILL.md`:**

- Skill loaded **1 vez** por sessão (~400 tokens inicial)
- Cada subsequent spawn pula o load (project-context cache)
- Tokens economizados em worst-case: **3.600 − 400 = 3.200 tokens/sessão** (-89%)

**Impacto negativo:** primeira invocação paga overhead. Mas project-context já demonstrou que load única amortizada > inline replicado.

---

## 2. `token-design-patterns-skill-244-lines-loaded-by-3-agents-no-lazy-load-gate-for-composition-root-pattern-only-needed-on-DI-tasks`

**Categoria:** lazy-load condicional não aplicado
**Severidade:** HIGH

`skills/architecture/design-patterns/SKILL.md` (244 linhas, **3.904 tokens**) é carregada por:

| Agent | Condicional? | Frequência |
|-------|--------------|-----------|
| `software-architect` | conditional (DI/wiring/IoC tasks) | Baixa |
| `backend-developer` | **eager (rule item; sempre)** | Alta |
| `frontend-developer` | conditional (SPA/framework DI tasks) | Média |

Apenas backend-developer carrega eagerly. Mas mesmo o eager load **não é diferenciado por task**: Composition Root é só **1 dos 5 patterns** na skill. Pull de toda a skill é desperdício em ≥80% das invocações de backend-developer (que cobrem CRUD, query optimization, API, etc., não DI).

**Recomendação técnica:** após extração para `references/{strategy,factory,observer,repository,composition-root}.md`, fazer SKILL.md carregar apenas o **diretório de patterns relevantes** (~50 linhas = ~800 tokens). Each pattern reference loaded sob demanda.

| Cenário | Hoje | Após extração + lazy load |
|---------|------|---------------------------|
| backend-developer carrega skill | 3.904 tokens | 800 tokens (cabeçalho) |
| backend-developer pula para DI task | 0 adicionais | +1.600 (composition-root.md) |
| backend-developer em CRUD task | 3.904 tokens (todos os patterns) | 800 tokens |

**Economy worst-case em backend-developer em sessão CRUD:** 3.904 − 800 = **3.104 tokens** (-79%).

**Spawn fanout:** backend-developer aparece em 6 commands. Worst-case multi-command CRUD session: **6 × 3.104 = ~18.624 tokens economizados**.

---

## 3. `token-frontend-developer-244-lines-after-composition-root-grew-12-lines-no-extraction-to-architecture-aware-skill-eager-load-12-tokens-per-spawn`

**Categoria:** growth de agent + ausência de extração
**Severidade:** MEDIUM

Composition Root section em `frontend-developer.md:143-153` (12 linhas, ~192 tokens) é **eager** — vive no agent body, não em skill com gate condicional.

`frontend-developer` é spawneado em 5 commands (`/devteam:frontend`, `/devteam:fullstack`, `/devteam:fix`, `/devteam:design`, `/devteam:mobile`¹). Worst-case fan-out diário (3 spawns) = **576 tokens replicados** somente para o bloco Composition Root.

Trivial isolado. **Mas:** é o tipo de gordura que acumula. CLAUDE.md cresceu de ~330 → 425 linhas em 11 dias **principalmente por adições de 5–20 linhas individuais que pareciam triviais**.

Recomendação técnica:
- Mover a seção Composition Root para `skills/architecture/design-patterns/references/composition-root.md`
- No agent, deixar 2–3 linhas: "When the project uses framework DI (Angular, Vue, React SPA, etc.), load `skills/architecture/design-patterns/SKILL.md` → Composition Root section"

**Impacto positivo:** ~10 linhas a menos no agent; ~150 tokens/spawn economizados.
**Impacto negativo:** trivial.

---

## 4. `token-_index-md-552-lines-grew-43-lines-in-24h-6th-consecutive-pass-rotation-script-still-unwritten-projection-1000-linhas-em-13-dias`

**Categoria:** drift acumulativo / 6ª passada consecutiva
**Severidade:** HIGH

Trajetória do `_index.md`:

| Data | Linhas | Delta | Tokens |
|------|--------|-------|--------|
| 2026-05-14 | 380 | — | 6.080 |
| 2026-05-15 | 464 | +84 | 7.424 |
| 2026-05-16 | 509 | +45 | 8.144 |
| 2026-05-17 | **552** | +43 | **8.832** |

Pace **conservador** (apenas updates de Statistics): ~43 linhas/dia.
Pace **agressivo** (com novos fingerprints): ~50 linhas/dia.
Projeção 1.000 linhas: **13 dias** (2026-05-30) no agressivo, **21 dias** (2026-06-07) no conservador.

Sub-escopo refinado em relação ao fingerprint pendente (`token-_index-md-509-lines-grew-45-lines-in-24h-rotation-still-not-actioned-after-5-passes` — 2026-05-16): **mecanismo de growth mudou**. Antes era predominância de **novos fingerprints**; agora é **growth da tabela Statistics** com prosa crescente em "Executadas / Revertidas".

Sub-recomendação: a coluna "Executadas / Revertidas" da tabela Statistics não precisa de prosa expandida — apenas valores numéricos. Restringir a `N ✅ + M ⚠️ + K 🟢 / pendentes` reduziria growth diário em ~5 linhas. Sem o cleanup, o índice cresce 5 linhas/dia **apenas pelo storytelling**.

**Impacto positivo:** clamp na coluna libera ~25% do growth diário. Adicional: `scripts/archive-index.sh` cortando entradas > 30 dias liberaria ~150 linhas de uma vez.
**Impacto negativo:** perda de narrativa histórica (mas isso pertence a CHANGELOG, não a index de fingerprints).

---

## 5. `token-install-sh-503-lines-largest-single-script-not-fragmented-vs-stop-dispatcher-pattern-13-functions-extractable-each-100-tokens`

**Categoria:** governance + monolito de script
**Severidade:** MEDIUM

`scripts/install.sh` tem **503 linhas** — o maior script do repositório, **3× maior** que a média (`183` linhas mediana). Compare com Stop dispatcher (`scripts/hooks/stop.sh` = 40 linhas) que delega para 5 sub-scripts.

Análise de funções em `install.sh`:

| Função | Linhas aprox |
|--------|-------------|
| `_detect_python` | 15 |
| `_download` | 25 |
| `_strip_dev_only` | 30 |
| `_emit_preferences_json` | 80 |
| `_inject_hook` | 60 |
| `_install_skills` | 40 |
| `_install_agents` | 25 |
| ... (outras 8 funções) | ~200 |

Pattern simétrico ao Stop dispatcher seria:

```
scripts/install.sh           (cli + dispatcher, ~80 linhas)
scripts/install/
├── 01-detect-environment.sh
├── 02-download-payload.sh
├── 03-emit-preferences.sh
├── 04-inject-hooks.sh
├── 05-install-skills.sh
└── 06-install-agents.sh
```

**Impacto positivo:**
- Cada sub-script testável isoladamente
- Quando bug em `_emit_preferences_json` (e.g., missing `transcript_multiplier` — pendente desde 2026-05-15), debug isolado
- Onboarding facilitado (novo contribuidor não precisa entender 503 linhas para fix em hook injection)

**Impacto negativo:**
- Custo de refatoração grande (~3h)
- Possível breaking changes em curl/wget pipe (`curl ... | bash`) — mas o instalador já faz download de payload, sub-scripts seriam baixados em conjunto

---

## 6. `token-conventional-commits-skill-138-lines-loaded-by-commit-and-pr-commands-but-also-mentioned-as-skill-load-in-claude-md-skill-loads-by-table-format-not-prose`

**Categoria:** lazy-load gate ausente
**Severidade:** LOW

`skills/shared/conventional-commits/SKILL.md` (138 linhas, ~2.208 tokens) é carregada por **2 commands** (`commit.md`, `pr.md`). CLAUDE.md:455 mandata "Load `skills/shared/conventional-commits/SKILL.md` before writing the commit message".

Mas: `commit.md:99-112` faz **defer ao padrão do projeto primeiro** (executa `git log --oneline -10` para detectar padrão custom). Se o projeto tem padrão GitHub-style (`[feature]`), a skill canônica de Conventional Commits **não é necessária**.

Pattern adequado:

```
1. Load skills/shared/current-context/ (já feito)
2. Detect commit pattern from git log
3a. Se Conventional Commits → load skills/shared/conventional-commits/
3b. Se outro padrão → não carregar (~2.208 tokens economizados)
```

**Quantificação:** ~30% dos projetos usam padrão custom (estimativa baseada em projects-encountered counts). 30% × 2.208 = **662 tokens economizados em média por commit command invocation**.

**Impacto positivo:** elimina overhead em projetos com padrão custom.
**Impacto negativo:** zero.

---

## 7. `token-skills-shared-token-efficiency-not-quantified-in-CLAUDE-md-line-218-no-baseline-roi-tracking`

**Categoria:** medição faltando / dogfood gap
**Severidade:** LOW

CLAUDE.md:218-224 lista regras de token efficiency mas **não tem métrica observável**:

> "Prefer grep/head/tail over reading entire files"
> "Prefer cp/sed/awk bash commands over Read + Write"
> "Summarize command output instead of dumping raw content"
> "Use --quiet/-q flags by default"

**Quantificação ausente:** quantas operações grep+head são executadas/sessão? Quantos Read full-file? Sem baseline, não há feedback loop. Cada relatório diário (incluindo este) propõe economia em **tokens estimados**, mas nada valida que as economias propostas se materializaram.

Recomendação operacional: adicionar `scripts/hooks/stop/05-token-efficiency-check.sh` (~30 linhas) que:
- Conta total de `Read` calls com `limit:` vs sem `limit:`
- Conta `grep -r` vs `Read` em arquivos > 1.000 linhas
- Emite warning se ratio < 70%

**Impacto positivo:** baseline de ROI tracking; permite medir efetividade dos fingerprints `token-*`.
**Impacto negativo:** adiciona sub-script ao Stop (~10ms overhead/session).

---

## Resumo

7 fingerprints originais nesta categoria:

| # | Fingerprint | Tokens economizados (worst-case/sessão) | Severidade |
|---|-------------|------------------------------------------|------------|
| 1 | `token-software-architect-workflow-detection-25-lines-inline-x-9-architect-spawn-commands-fan-out-3600-tokens-per-multi-architect-flow` | **3.200** | HIGH |
| 2 | `token-design-patterns-skill-244-lines-loaded-by-3-agents-no-lazy-load-gate-for-composition-root-pattern-only-needed-on-DI-tasks` | **18.624** | HIGH |
| 3 | `token-frontend-developer-244-lines-after-composition-root-grew-12-lines-no-extraction-to-architecture-aware-skill-eager-load-12-tokens-per-spawn` | 576 | MEDIUM |
| 4 | `token-_index-md-552-lines-grew-43-lines-in-24h-6th-consecutive-pass-rotation-script-still-unwritten-projection-1000-linhas-em-13-dias` | (drift) | HIGH |
| 5 | `token-install-sh-503-lines-largest-single-script-not-fragmented-vs-stop-dispatcher-pattern-13-functions-extractable-each-100-tokens` | (manutenção) | MEDIUM |
| 6 | `token-conventional-commits-skill-138-lines-loaded-by-commit-and-pr-commands-but-also-mentioned-as-skill-load-in-claude-md-skill-loads-by-table-format-not-prose` | 662 (média) | LOW |
| 7 | `token-skills-shared-token-efficiency-not-quantified-in-CLAUDE-md-line-218-no-baseline-roi-tracking` | (governance) | LOW |

**Total estimado economy worst-case/sessão (somando #1–#3, #6):** ~23.062 tokens.
