# Relatório — Economia de Tokens (2026-05-12)

Auditoria focada em **duplicação inline, conteúdo carregado eagerly que poderia ser lazy, e oportunidades de extração**. Todas as sugestões com estimativa quantitativa de economia e **originais** ou **variantes com escopo novo**.

> **Premissa:** uma sessão típica multi-agent (`/devteam:plan` ou `/devteam:fullstack`) carrega ~5-7 agents + 15-20 skills. Cada linha duplicada nesses arquivos é multiplicada pelo fanout.

---

## 1. `token-foundational-rule-software-architect-outlier-51-lines`

**Severidade:** 🟡 Média — sub-escopo do pendente `token-foundational-rule-424-lines-across-17-agents`

**Detecção:** Tabela completa do tamanho do Foundational Rule por agent (do relatório 03):

| Agent | Linhas | vs. p50 (22 lines) |
|-------|--------|--------------------|
| software-architect | **51** | +132% |
| code-reviewer | 28 | +28% |
| backend-developer, security | 27 | +23% |
| (p50) | 22 | — |
| setup-assistant | 10 | -55% |

**Sub-escopo novo (vs. fingerprint 424-linhas):** ao focar **apenas no outlier** (software-architect), a economia é cirúrgica:
- Poda alvo: 51 → 25 linhas (~26 linhas, ~210 tokens)
- Replicada 1x (apenas software-architect), mas software-architect é spawned em **9 commands** (plan, architect, refactor, dba, security, review, workflow-* …)

Economia estimada: ~210 tokens × 9 contextos = **~1.900 tokens por dia** num uso médio.

**Impacto positivo:** redução direta sem perda de funcionalidade (o excesso vem de listar steps que já existem em `project-context` skill).

**Impacto negativo (se mantido):** software-architect carrega ~30% mais Foundational do que o p50 — sem ganho mensurável.

---

## 2. `token-extracted-docs-loaded-by-readme-but-may-be-read-fully-by-agents`

**Severidade:** 🟡 Média

**Detecção:** Após `7800516`, README.md (228 linhas) delega para `docs/agents.md` (6714 bytes / ~200 linhas) e `docs/installation.md` (5723 bytes / ~170 linhas). Quando um agent faz `project-context` e o README aponta para estes docs, **alguns agents leem os derivados também** (especialmente setup-assistant em audit). Resultado líquido: o conteúdo voltou a entrar no contexto, só que **fragmentado em 3 arquivos** em vez de 1 README monolítico.

**Verificação direta:**
```bash
grep -l "docs/agents.md\|docs/installation.md" agents/*.md skills/**/SKILL.md
```
Hoje nenhum agent referencia explicitamente, mas o link em README **pode** ser seguido pelo agent em discovery.

**Impacto positivo (se corrigido):** documentar no `setup-assistant.md` que durante audit ele **não deve** ler `docs/installation.md` (só relevante a manutenção do dev-team-agents, não ao projeto-alvo do usuário).

**Impacto negativo (se mantido):** setup-assistant em projeto-alvo pode ler 2 arquivos extras (~370 linhas) sem benefício, gastando ~3.000 tokens.

---

## 3. `token-skill-monitoring-444-lines-loaded-by-devops-and-architect`

**Severidade:** 🟡 Média

**Detecção:** `monitoring/SKILL.md` (444 linhas) é carregada por:
```
agents/devops-specialist.md
agents/software-architect.md   ← carrega via "observability-slo" branch
```

Em commands que invocam ambos (ex.: `/devteam:plan`, `/devteam:devops`), a skill é carregada **2x** (uma vez por agent). Mesmo com cache de Read (Claude Code não tem cache cross-agent), os 444 linhas entram em 2 contextos.

**Combinação com fingerprint pendente:** `skill-monitoring-444-lines-over-limit-needs-references-extraction`. Aqui o ângulo é **quantitativo**:

| Cenário | Tokens consumidos |
|---------|------------------|
| Atual (444 linhas inline × 2 contextos) | ~7.100 |
| Pós-extração para `references/{logs,metrics,traces,slo}.md` (skill index ~80 linhas, references lazy) | ~1.300 |

Economia: **~5.800 tokens por execução de `/devteam:plan` em projeto com monitoring envolvido**.

**Impacto positivo:** maior ganho de extração quantificado neste audit.

**Impacto negativo (se mantido):** alta probabilidade de ser flagada em todo audit futuro.

---

## 4. `token-readme-228-each-pos-extraction-but-ci-sync-still-line-based`

**Severidade:** 🟢 Baixa — variante de fingerprint ⚠️ Partial

**Detecção:** Após extração para `docs/`, README.md e README.pt-BR.md têm **228 linhas cada** (queda de 734 → 228, **-69%**, excelente). Porém o CI `README sync check` ainda usa heurística de line-count com 5% threshold:

```bash
# .github/workflows/ci.yml:32-41
THRESHOLD=$(( MAIN * 5 / 100 + 1 ))  # = 12 lines for 228
```

12 linhas de threshold em 228 = **5.2% tolerância**. Suficiente para diff sintático (formatação), insuficiente para detectar uma seção inteira faltando (12 linhas podem ser facilmente o bloco "Installation" inteiro).

**Sub-escopo novo:** com README menor, o threshold absoluto faz menos sentido. Heurística melhor: **checkar seções com `## ` match em ambos arquivos**.

**Impacto positivo (se corrigido):** detecta drift estrutural (seção removida) que line-count não pega.

**Impacto negativo (se mantido):** drift estrutural passa silenciosamente até audit manual.

---

## 5. `token-plan-mode-143-lines-7-agents-but-only-1-command-loads`

**Severidade:** 🟡 Média — ironia + variante de pendente

**Detecção:** `plan-mode/SKILL.md` cresceu de 131 → 143 linhas. Continua carregada por 7 agents no startup (relatório 03 item 1 + fingerprint pendente).

**Sub-escopo novo:** o **command** `/devteam:plan` (que é o caso de uso primário do skill!) **não carrega** a skill — os agents spawned é que carregam.

| Local de load | Quantos |
|---------------|---------|
| Agents (eager, no startup) | 7 |
| Commands | 0 ❗ |

Asimetria perfeita: o command que pede plan **assume** que os agents carregam o skill. Quando há mismatch (ex.: produto-analyst não carrega plan-mode), o output diverge.

**Impacto positivo (se corrigido):**
- Carregar a skill no `/devteam:plan` command (1x por sessão)
- Remover das 7 agents (skill já carregada pelo command parent)
- Total: -7 carregamentos + 1 carregamento = **-6 × 143 = ~7.200 tokens economizados** por sessão multi-agent

**Impacto negativo (se mantido):** continua sendo carregada eagerly em todo agent spawn que carrega plan-mode, mesmo quando a sessão não vai gerar plano (ex.: `/devteam:fix` simples).

---

## 6. `token-changelog-cresceu-de-119-para-129-linhas-em-um-dia`

**Severidade:** 🟢 Baixa — quantificação do pendente `token-changelog-already-growing-and-not-extracted-by-release`

**Detecção:** CHANGELOG.md em 2026-05-11 reportado em ~119 linhas (cálculo retroativo). Hoje: **129 linhas** (+10 em 24h). Trajetória mantida: ~10 linhas/dia × 90 dias = ~900 linhas se não rotacionar.

**Limiar de "release":** quando atingir 300 linhas (~17 dias se mantida cadência), criar `CHANGELOG.archive-2026-Q2.md` movendo entradas anteriores a 1.X.

**Impacto positivo (se preparado):** rotação fica trivial quando o limiar bater (script `archive-changelog.sh` pode existir desde já).

**Impacto negativo (se mantido):** quando passar de 500 linhas (~37 dias), o changelog vira "skill-sized" e começa a impactar contexto de release workflows.

---

## 7. `token-stop-hook-04-sub-scripts-200ms-overhead-on-read-only-sessions`

**Severidade:** 🟡 Média — quantificação do flow #4 do relatório 02

**Detecção:** Stop hook executa 4 sub-scripts em série a cada `Stop`:

| Sub-script | Tempo típico | Tem gate? |
|-----------|--------------|----------|
| `01-session-summary.sh` | ~30ms (git status + grep) | Parcial (check uncommitted) |
| `02-orphan-skill-scan.sh` | ~80ms (find + grep across skills) | Sim (--quiet skip) |
| `03-agent-lint.sh` | ~50ms (validate 17 agents) | Não |
| `04-notifier.sh` | ~40ms (read .notifier-state) | ✅ (last_shown_date) |

**Total típico:** ~200ms por Stop. Em sessão de 30 turns (média), são **30 × 200 = 6s** de overhead.

**Sub-escopo novo (vs. fingerprint #4 do flow):** quantificar o ganho. Se o dispatcher passa flag `DEVTEAM_NO_CHANGES=1` quando `git diff --quiet`:
- 01-session-summary pula (não há mudanças)
- 02-orphan-skill-scan pula (sem mudança em agents/skills)
- 03-agent-lint pula (sem mudança em agents)
- 04-notifier roda (notification é independente de mudanças)

Resultado: **~150ms → ~40ms (-73%)**.

**Impacto positivo:** sessão read-only fica imperceptível em wall-clock.

**Impacto negativo (se mantido):** UX de "Claude responde, depois pausa 200ms" persiste em todo turn.

---

## 8. `token-foundation-rule-cumulative-across-multi-agent-spawn-fanout`

**Severidade:** 🟡 Média — variante de cálculo

**Detecção:** Quando `/devteam:plan` spawna 6 agents em paralelo (software-architect, product-analyst, database-specialist, backend, frontend, devops), o foundational rule **total** carregado é:

| Agent | Foundational lines |
|-------|-------------------|
| software-architect | 51 |
| product-analyst | 18 |
| database-specialist | 21 |
| backend-developer | 27 |
| frontend-developer | 24 |
| devops-specialist | 25 |
| **Total inline** | **166 linhas** |

Se substituído por `Load skills/shared/project-context/SKILL.md` (1 linha) por agent:
- 6 × 1 = 6 linhas inline + 1 × ~80 linhas da skill (cached cross-spawn? não — Claude Code não cacheia)
- Real: 6 × 80 = 480 linhas (pior!)

**Conclusão contraintuitiva:** com cross-spawn cache, a skill ganharia. Sem cache, a duplicação é menor inline. **O ganho real só vem com `current-context` cache** (fingerprint #5 do relatório 02).

**Impacto positivo:** este audit revela que a otimização de foundational depende **primeiro** da implementação do cache cross-spawn. Sem ele, mover para skill **piora**.

**Impacto negativo (se prossegue sem cache):** tentativas de extrair foundational regridem o token cost.

**Recomendação:** registrar como **dependência** do fingerprint `flow-no-pre-spawn-current-context-warm-cache` (relatório 02 item 5).

---

## 9. `token-orphan-scan-script-shells-13-times-per-execution`

**Severidade:** 🟢 Baixa

**Detecção:** `scripts/orphan-skill-scan.sh` (não totalmente vista, mas com ~100 linhas estimadas) usa pattern bash de loops aninhados com `grep`/`find` por skill. Cada execução faz ~13 `find` + ~50 `grep` no repositório.

Em Stop hook (executa toda Stop), isso multiplica:
- 30 turns × 13 finds = 390 finds/sessão

Otimização: **batch single `find` + awk dispatcher**:
```bash
find skills agents -type f -name "*.md" | xargs grep -H "<pattern>" \
  | awk '{ classify($0) }'
```

Reduz a 1 `find` + 1 `xargs grep`.

**Impacto positivo:** Stop hook fica mais responsivo; CPU local poupa ~50ms/Stop.

**Impacto negativo (se mantido):** overhead silencioso constante; usuário em laptop fraco pode notar.

---

## 10. `token-comments-policy-417-lines-still-monolith-no-section-loading`

**Severidade:** 🟡 Média — variante de fingerprint pendente desde 2026-05-09

**Detecção:** `comments-policy/SKILL.md` (417 linhas) é carregada por 9 agents (backend-developer, frontend-developer, mobile-developer, database, devops, reviewers ×3, test-specialists ×2). É a **skill mais "espalhada"** do repo.

Conteúdo dividido em seções claras (regras gerais → exemplos linguagem-específicos → casos limítrofes). Mas é carregada inteira sempre. Cada agent só usa ~30% da skill (sua linguagem específica + regras gerais).

**Sub-escopo novo (vs. fingerprint 2026-05-09):** propor um **mecanismo de seção-loading universal** no agentskills.io spec hierarchy:
```
skills/shared/comments-policy/
├── SKILL.md (~80 linhas — regras gerais + table de seções)
└── sections/
    ├── javascript.md
    ├── typescript.md
    ├── python.md
    ├── php.md
    └── …
```

Agent loads `SKILL.md` + condicionalmente `sections/<detected-lang>.md`.

**Impacto positivo:** 417 → ~120 linhas no agent context (skill index + 1 section). **Redução de 70%** em 9 agents. Sessão multi-agent: ~9 × 297 linhas × 7 tokens/linha = **~18.700 tokens economizados**.

**Impacto negativo (se mantido):** comments-policy continua sendo o "monolito" do shared/.

---

## Resumo & Estimativa Agregada

| Sugestão | Economia estimada (tokens/sessão multi-agent) |
|----------|----------------------------------------------|
| #3 monitoring extraction | ~5.800 |
| #5 plan-mode skill load no command | ~7.200 |
| #10 comments-policy section-loading | ~18.700 |
| #1 software-architect foundational poda | ~1.900 |
| #7 Stop hook fast path | ~0 (UX, não tokens) |
| **Total combinado (estimativa otimista)** | **~33.600 tokens/sessão** |

> Para referência: uma sessão de Claude Code com context-window 200k usa tipicamente 60-80k tokens em multi-agent ops. **33.600 tokens = ~40-55% de redução do "overhead de skills/foundational"**.

**Top 3 prioridades:**

1. `token-comments-policy-417-lines-still-monolith-no-section-loading` — maior ganho absoluto + viabilizado por padrão genérico (mecanismo se aplica a outras skills monolíticas).
2. `token-plan-mode-143-lines-7-agents-but-only-1-command-loads` — corrige asimetria + economia mensurável + simplicidade de implementação.
3. `token-skill-monitoring-444-lines-loaded-by-devops-and-architect` — pasta references/ já existe; baixo custo, alto ganho.

**Dependência crítica:** #8 (foundational rule across spawn fanout) **só ganha** depois que o cache cross-spawn (`current-context` cache do relatório 02) for implementado. Não tentar #8 isolado.
