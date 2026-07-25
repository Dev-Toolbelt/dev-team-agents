# Agentes e Skills — 2026-05-16

> Auditoria de agentes e skills: tamanho, foundational rules, padrão de extração, opinião de stack baked-in. Foco: novas violações de stack-agnosticism, skills > 200 linhas sem `references/`, asimetrias de tamanho entre agents de papéis equivalentes.

---

## 1. `agent-software-architect-anti-overengineering-rule-117-violates-stack-agnostic-mandate` — HIGH

**Arquivo:** `agents/software-architect.md:117`

**Observação:** dentro do bloco "Anti-overengineering rules" (linhas 113-117):

```markdown
- Don't recommend microservices when a monolith will work
- Don't recommend a message queue when a simple cron job or synchronous call will work
- Don't recommend distributed caching when database query optimization is needed first
- Don't recommend Kubernetes when Docker Compose on a VPS will handle the load
```

A 4ª linha viola CLAUDE.md (linha 17 — "Stack-agnostic, project-aware") porque presume **Docker Compose** como alternativa default a Kubernetes e **VPS** como ambiente default. As outras 3 linhas usam termos arquiteturais genéricos (microservices, message queue, distributed caching), mas a 4ª substitui esses por stack-specifics.

**Cross-cut com [01-referencias-e-consistencia.md#2](01-referencias-e-consistencia.md#2):** mesmo achado, ângulo "agente" vs ângulo "consistência". Listado em ambos por relevância pedagógica.

**Por que importa:**
- `software-architect` é spawneado em 9 commands (CLAUDE.md tabela) — bias amplifica em todo `/devteam:plan`, `/devteam:refactor`, `/devteam:architect`, etc.
- Repete o mesmo padrão que justificou o fix do `devops-specialist` (2026-05-13 ✅). Bias migrou, não foi eliminado.

**Impacto positivo:** substituir por:
```markdown
- Don't recommend distributed orchestration (Kubernetes, Nomad, ECS) when a single-node container runtime or managed PaaS will handle the load
```
Mantém princípio (anti-overengineering); remove naming de stack default.

**Impacto negativo:** perde exemplo concreto que ajudava leitor a internalizar; mitigável com "Examples: Docker Compose, Fly.io, single-host systemd" como nota fora da regra.

---

## 2. `agent-devops-specialist-description-line-8-stack-list-still-prescriptive-after-body-fix` — sub-escopo

**Arquivo:** `agents/devops-specialist.md:8`

**Observação:** o fix de 2026-05-15 removeu prescrições "Docker-first" do corpo do agente. **A descrição (linha 8) permanece prescritiva:**

```
You are a **DevOps Specialist** — a pragmatic infrastructure engineer who builds simple, reliable, cost-efficient deployments. You avoid overengineering. Your default answer to "how should we deploy this?" depends on the project's existing stack, scale, and team expertise — Docker Compose for small teams, Kubernetes for distributed systems, serverless for event-driven workloads.
```

A última cláusula define o mapeamento default → stack:
- "small teams" → Docker Compose
- "distributed systems" → Kubernetes
- "event-driven" → serverless

Esta é exatamente a lista que devia ter saído junto com o restante do bias removido. A versão "stack-aware" do corpo é boa; **a "stack-prescriptive" da descrição passou batido no audit**.

**Por que importa:**
- Descrição é o **primeiro contato** do LLM com o papel (linha 3 é metadata, linha 8 é prosa de identidade).
- Influencia framework de raciocínio antes do corpo ser lido.
- Sub-escopo legítimo do fingerprint anterior (que foi marcado ✅ apenas para o corpo).

**Impacto positivo:** substituir a cláusula por `"Your default answer depends on what the team already runs — Docker, bare-metal, PaaS, serverless, anything; opinion follows evidence, not the other way around."` (16 palavras vs 18; mais agnostic; mantém tom).

**Impacto negativo:** zero — apenas reformulação.

---

## 3. `skill-push-notifications-373-lines-largest-skill-in-repo-no-references-extraction-2nd-pass` — HIGH (re-afirmação)

**Arquivo:** `skills/integrations/push-notifications/SKILL.md` (373 linhas)

**Observação:** 2ª passada. Sem mudança desde 2026-05-15. Continua sendo a **maior skill do repo**:

| # | Skill | Linhas | references/ ? |
|---|-------|--------|---------------|
| 1 | `skills/integrations/push-notifications/SKILL.md` | **373** | ❌ |
| 2 | `skills/devops/graphify-setup/SKILL.md` | 277 | ❌ |
| 3 | `skills/shared/project-context/SKILL.md` | 266 | ✅ (pós 2026-05-15) |
| 4 | `skills/architecture/graphql/SKILL.md` | 235 | ❌ |
| 5 | `skills/integrations/gotrue/SKILL.md` | 225 | ❌ |

Blocos extraíveis identificados por inspeção:
- Cross-browser detection (~80 linhas) → `references/browser-detection.md`
- Service Worker bootstrap (~70 linhas) → `references/service-worker.md`
- iOS Safari PWA quirks (~60 linhas) → `references/ios-safari.md`
- VAPID key generation (~40 linhas) → `references/vapid.md`
- Subscription lifecycle (~50 linhas) → `references/subscription-lifecycle.md`

**Loaded por:** `frontend-developer` (eager) + `mobile-developer` (conditional via push detection rules).

**Por que importa:**
- 373 × 16 tokens = ~5.968 tokens eager × 2 loaders = ~12k tokens/sessão multi-agent.
- Padrão references/ foi aplicado em 7 skills devops + 1 docs-sync na batch de 2026-05-13 (`b8ece69`). Push-notifications ficou de fora.
- 1ª passada (2026-05-15) registrou o ponto; foi pulado na batch — sinal de que precisa explicitamente entrar no próximo pacote de extração.

**Impacto positivo:** ~280 linhas vão para `references/`; SKILL.md cai para ~93 linhas; tokens eager-load cortam ~75%.

**Impacto negativo:** lazy-load por trigger (browser detected, push permission requested) precisa ser documentado nos consumers.

---

## 4. `skill-shared-worktree-214-lines-loaded-by-8-coding-agents-no-references-extraction` — HIGH (NEW)

**Arquivo:** `skills/shared/worktree/SKILL.md` (214 linhas)

**Observação:** carregada por 8 coding agents:

```bash
$ grep -l "skills/shared/worktree" agents/*.md | wc -l
8
```

(backend-developer, frontend-developer, mobile-developer, database-specialist, devops-specialist, backend-test-specialist, frontend-test-specialist, ui-ux-designer)

Sem `references/` directory. Worst-case load: 8 × 214 × 16 = **~27.400 tokens/multi-agent session**.

Inspeção do conteúdo revela blocos extraíveis:
- "Naming Conventions" (~30 linhas) — só relevante quando criando branch nova
- "Recovery from broken worktree" (~25 linhas) — incident-only
- "Git worktree gotchas" (~40 linhas) — reference cookbook
- "CI/CD interaction" (~30 linhas) — only when commands/pr.md em jogo

Apenas ~90 linhas são core (decisão worktree/branch + naming basics).

**Por que importa:**
- Fingerprint `token-worktree-isolation-block-136-duplicate-lines-across-8-coding-agents` (2026-05-15) endereçou o **bloco inline de 17 linhas** que existe em cada agent; mas o SKILL.md em si também tem volume alto.
- Combinado: extração inline (sugerida em 2026-05-15) + extração references/ (este fingerprint) corta ~80% dos tokens.

**Impacto positivo:** SKILL.md cai para ~90 linhas core; references/ guardam material consultado raramente.

**Impacto negativo:** se incident acontece e usuário precisa de "Recovery from broken worktree", agent precisa fazer 2º Read — latência +1s.

---

## 5. `agent-setup-assistant-immutability-section-225-238-redundant-with-warning-line-24` — sub-escopo (NEW)

**Arquivo:** `agents/setup-assistant.md` (238 linhas)

**Observação:** o agent contém **dois blocos** sobre o tema "Immutability":

| Localização | Linhas | Conteúdo |
|-------------|--------|----------|
| Foundational Rule (top) | 24 | 1 linha resumida: "Never modify files inside `.dev-team-agents/`..." |
| Section "Immutability Warning" (bottom) | 220-238 | 19 linhas: descrição completa do warning, exemplos de overrides, link para repo |

**Verificação:**
```bash
$ grep -n "Immutability" agents/setup-assistant.md
24:## Immutability Warning
225:## Immutability Warning
```

Dois headers `## Immutability Warning` no mesmo arquivo — **violação estrutural** de markdown (assume duplicated section IDs em renderizadores estritos).

**Por que importa:**
- Fingerprint `token-setup-assistant-immutability-warning-duplicated-top-and-bottom-30-lines` (2026-05-15) registrou o tema em **economia de tokens**. Este sub-escopo é **estrutural** (header duplicado é bug renderização independente de tokens).
- Renderizadores que constroem ToC ou anchors quebram o segundo link.

**Impacto positivo:** renomear o segundo header para `## Immutability Warning — Full Reference` (ou similar) OU mesclar os dois removendo a versão top e mantendo apenas a completa, com nota cross-link de Foundational Rule.

**Impacto negativo:** quebra anchor interno se algo linkar para `#immutability-warning`; mitigável por busca/substituição no PR.

---

## 6. `agent-software-architect-anti-overengineering-rules-block-candidato-extracao-skill-archive-decisions` — LOW

**Arquivo:** `agents/software-architect.md:113-117`

**Observação:** as 4 regras anti-overengineering (mesmo bloco do item #1) são princípios **transferíveis** — não específicos do papel de architect. Eles fazem sentido para `code-reviewer`, `security-specialist`, `database-specialist` quando avaliam decisões.

Atualmente o bloco está inline. Outros agents que enfrentam decisões parecidas (microservices vs monolith, queue vs cron) não têm acesso a essas heurísticas — replicam ou improvisam.

**Por que importa:**
- Skill canônica `skills/architecture/anti-overengineering/SKILL.md` (não existe) seria carregada por ~5 agents — reduz drift de princípios entre reviewers.
- Resolveria simultaneamente o item #1 (a versão extraída pode ser corrigida em 1 lugar).

**Impacto positivo:** ~10 linhas eager × 5 agents = ~800 tokens/multi-agent session economia. Princípios consolidados em 1 fonte.

**Impacto negativo:** mais 1 skill — fragmentação adicional aumenta cognitive load do mantenedor; mitigável fazendo a skill < 30 linhas (cabe na cabeça inteira).

---

## 7. `skill-graphify-setup-277-lines-no-conditional-gate-after-4-passes-no-detection-rule` — sub-escopo (re-afirmação)

**Arquivo:** `skills/devops/graphify-setup/SKILL.md` (277 linhas)

**Observação:** 4ª passada consecutiva. Tipos de mudança em janelas anteriores: zero. Skill continua:
- 2ª maior do repo (depois de push-notifications)
- Sem `references/` (não foi extraída na batch de 2026-05-13)
- Loaded **eagerly** por `setup-assistant` sem stack-detection prévia
- `setup-assistant.md:120` ainda pergunta "Set up Graphify now? **yes / no**" em **todo onboarding**, mesmo em projeto puramente docs (Hugo, Markdown, etc.) onde Graphify não agrega nada

**Por que importa repetir:**
- Padrão "fingerprint nunca-implementado" + "skill cresce e fica" = anti-pattern observável.
- 4ª menção sem ação sinaliza que o owner precisa decidir: (a) extrair references/, (b) gate condicional por linguagem, (c) deprecate skill e tornar opcional via plugin separado.

**Impacto positivo:** caminho (b) — gate detecta presença de `.graphify/` OU código em linguagem suportada → senão pula skip silencioso. Economiza ~277 × 16 = ~4.432 tokens/onboarding em projetos não-aplicáveis (~30% dos casos).

**Impacto negativo:** falso negativo onde usuário **quer** Graphify mas projeto não tem heurística detectável; mitigável por flag `--force-graphify` no `setup-assistant` ou pergunta opt-in (não opt-out).
