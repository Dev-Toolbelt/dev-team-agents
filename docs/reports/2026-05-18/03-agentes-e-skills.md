# Relatório 03 — Agentes e Skills (2026-05-18)

**Foco:** drift estrutural em agents pós-extrações de 2026-05-18; skills criadas no mesmo dia sem o padrão `references/`; assimetrias persistentes; orphan-template scanner reporta inconsistências.

---

## #1 — `agent-devops-specialist-decision-framework-and-anti-overengineering-still-stack-prescriptive-in-body-after-2026-05-18-fix-on-description-and-identity`

**Severidade:** HIGH
**Arquivo:** `agents/devops-specialist.md:134-156`

O commit `3bb9d74` corrigiu **descrição** (linha 3) e **parágrafo de identidade** (linha 8), trocando "Docker Compose for small teams, Kubernetes for distributed systems, serverless for event-driven workloads" por linguagem neutra. **Mas as seções "Decision Framework — Infrastructure Sizing" e "Anti-Overengineering Rules" mantêm as preferências de stack:**

```md
| Traffic | Recommended |
|---------|-------------|
| < 1k req/day | Single EC2/VPS + Docker Compose |
| > 100k req/day | Evaluate distributed architecture (not necessarily Kubernetes) |

## Anti-Overengineering Rules
- Don't use Kubernetes when Docker Compose works
- Don't build a service mesh when Nginx handles the routing
- Don't set up a full observability platform (Datadog, Grafana Cloud) when CloudWatch or a self-hosted Prometheus covers the need
```

Esse é o **terceiro ponto** dessa classe de regressão no repo (devops-specialist linha 8 — 2026-05-13 ✅; software-architect linha 117 — 2026-05-16 corrigido em 2026-05-18; agora linhas 134-156 do mesmo devops-specialist — pendente). Padrão: o fix sempre toca uma seção e deixa outra atrás.

**Impacto positivo:** Trocar a tabela por categorias neutras ("single-server", "managed container service", "auto-scaled containers", "distributed architecture") elimina o viés sem perder o valor pedagógico.

**Impacto negativo:** perde-se especificidade ilustrativa. Mitigável: mover exemplos opinativos para `references/decision-examples.md`.

---

## #2 — `agent-mobile-developer-ios-android-skills-too-thin-33-and-35-lines-versus-ios-hig-218-and-material-design-221-no-clear-content-boundary`

**Severidade:** MEDIUM
**Arquivos:** `skills/mobile/ios/SKILL.md`, `skills/mobile/android/SKILL.md`, `skills/mobile/ios-hig/SKILL.md`, `skills/mobile/material-design/SKILL.md`

O fingerprint pai (2026-05-18 ✅) propôs criar `skills/mobile/ios/` e `skills/mobile/android/` como skills de **plataforma**. A criação ocorreu, mas o conteúdo é tão raso que o primeiro bullet de cada uma é **"Load `skills/mobile/<platform>-hig|material-design`/SKILL.md for the full reference"** — ou seja, viraram **wrappers de redirecionamento**.

Estado atual:
| Skill | Linhas | Função |
|-------|--------|--------|
| `mobile/ios/SKILL.md` | 33 | Wrapper + permissions + signing |
| `mobile/ios-hig/SKILL.md` | 218 | Detalhamento HIG |
| `mobile/android/SKILL.md` | 35 | Wrapper + permissions + signing |
| `mobile/material-design/SKILL.md` | 221 | Detalhamento Material Design |

Não há fronteira clara. Em uma sessão real, `mobile-developer` carrega **as duas** (`ios` + `ios-hig`) consumindo ~250 linhas para uma feature simples de iOS.

**Impacto positivo:** consolidar `ios + ios-hig` numa só skill (ou mover unique-content do `-hig` para `references/`) reduz pull em 218 linhas/spawn (worst-case 4.176 tokens).

**Impacto negativo:** reorganiza skills recém-criadas; o tradeoff é entre estabilidade ("não mexer no que acabamos de criar") e qualidade ("a estrutura está errada").

---

## #3 — `agent-mobile-developer-platform-skills-loaded-eager-without-actual-platform-detection-gate-in-current-mobile-developer-md-line-72`

**Severidade:** MEDIUM
**Arquivo:** `agents/mobile-developer.md:72-78`

A tabela "Platform skills" diz:

```
| **iOS target** | `.xcodeproj`/`.xcworkspace`, `ios/` directory, or Swift files | `skills/mobile/ios/SKILL.md` + `skills/mobile/ios-hig/SKILL.md` |
| **Android target** | `android/` directory, `build.gradle`/`build.gradle.kts`, or Kotlin files | `skills/mobile/android/SKILL.md` + `skills/mobile/material-design/SKILL.md` |
| **Cross-platform (both platforms)** | React Native, Flutter, or Expo targeting both iOS and Android | Load **both** platform skill pairs above |
```

A coluna "Detection Signals" descreve o gate, mas **o agent não tem um bloco bash** que efetivamente verifica isso (como faz `setup-assistant` para Docker Compose). A tabela é uma **instrução narrativa** que depende do modelo seguir corretamente.

Para projetos cross-platform RN com 1 target ativo (ex: iOS only), o modelo pode carregar pessimisticamente os 4 SKILL.md (487 linhas total). Sem gate executável, o LLM decide.

**Impacto positivo:** mover gates para script bash (`mobile-developer.md` style do que existe em `setup-assistant.md` linhas 54-70) torna a decisão determinística.

**Impacto negativo:** mais bash inline no agent (anti-padrão de stack-detection skill); o ideal é `skills/shared/stack-detection/SKILL.md` ganhar uma seção "Mobile platform detection".

---

## #4 — `skill-shared-workflow-detection-50-lines-mas-without-references-test-fixtures-or-precedence-rules-when-multiple-keywords-match`

**Severidade:** MEDIUM
**Arquivo:** `skills/shared/workflow-detection/SKILL.md`

A skill (50 linhas, commit `d13c693`) extrai a tabela inline do software-architect, mas:

1. **Sem fixtures**: nenhum teste valida que "Refactor security audit" → `refactor.md` vs `security-patch.md` (ambos têm match)
2. **Sem precedence rules quando overlap**: a regra "match dominantes" depende do LLM julgar
3. **Sem version**: keywords podem evoluir sem ADR

Sub-escopo de `flow-software-architect-workflow-detection-classification-has-no-tests-no-fixtures-no-validation-pipeline-no-precedence-rules` (2026-05-17), com **angle pós-extração**: a skill foi criada **importando o problema sem corrigi-lo**.

**Impacto positivo:** adicionar `skills/shared/workflow-detection/references/fixtures.md` com 10-15 example requests e workflow esperado dá lint pipeline.

**Impacto negativo:** mais lint pra rodar; pode encontrar regressões que adiam features.

---

## #5 — `skill-shared-worktree-extracted-references-branch-flow-and-session-protocol-but-not-loaded-conditionally-by-the-8-coding-agents-eager-load-pattern-persists`

**Severidade:** MEDIUM
**Arquivos:** `skills/shared/worktree/SKILL.md` (67 linhas), `skills/shared/worktree/references/{branch-flow,session-protocol}.md`

A extração reduziu o SKILL.md raiz de 214 → 67 linhas. **Excelente.** Mas:

- Os 8 coding agents (backend-developer, frontend-developer, mobile-developer, database-specialist, devops-specialist, ui-ux-designer, backend-test-specialist, frontend-test-specialist) carregam o SKILL.md raiz pelo bloco "Worktree Isolation"
- Nenhum carrega condicionalmente `references/branch-flow.md` ou `references/session-protocol.md`
- Logo, em uma sessão multi-agent (`/devteam:fullstack` = 4-5 spawns), o SKILL.md raiz é carregado 4-5 vezes (67 × 5 = 335 linhas), mas as references **nunca** entram em jogo

A economia foi parcial (anteriormente 214 × 5 = 1.070 linhas → agora 67 × 5 = 335 linhas, ~70% redução), mas a **lógica de "carregar mais detalhe sob demanda"** não está implementada — references são fetch manual para o LLM decidir.

**Impacto positivo:** documentar em `worktree/SKILL.md` quando cada reference deve ser puxada (ex: branch-flow apenas em comandos com merge, session-protocol apenas quando worktree-session é criado/lido) habilita decisão consciente.

**Impacto negativo:** mínimo — adição de ~6 linhas de gating.

---

## #6 — `agent-frontend-developer-and-backend-developer-still-loaded-token-efficiency-inline-line-vs-load-pattern-divergence`

**Severidade:** LOW
**Arquivos:** `agents/{backend,frontend,mobile,backend-reviewer,frontend-reviewer,...}.md`

Verificando o padrão pós-2026-05-15:

```
agents/backend-developer.md:29:Apply `skills/shared/token-efficiency/SKILL.md` — prefer `grep`/`head` over full reads; filter before reading; summarize instead of dumping.
agents/database-specialist.md:21:Apply `skills/shared/token-efficiency/SKILL.md` — prefer `grep`/`head` over full reads.
agents/frontend-developer.md:28:Apply `skills/shared/token-efficiency/SKILL.md` — prefer `grep`/`head` over full reads; filter before reading; summarize instead of dumping.
agents/setup-assistant.md:16:3. Apply `skills/shared/token-efficiency/SKILL.md` — prefer `grep`/`find`/`head` over full reads
```

Divergências:
- Most agents: `prefer grep/head over full reads; filter before reading; summarize instead of dumping`
- `database-specialist`: encurtado para `prefer grep/head over full reads`
- `setup-assistant`: usa `grep/find/head` (inclui `find`)
- `mobile-developer:27`: encurtado para `prefer grep/head over full reads; summarize instead of dumping`

Sub-escopo do antigo `token-efficiency apply line standardised to one canonical form across 10 agents` (CHANGELOG `[Unreleased]`), mas verificação mostra **4 variantes** ainda no repo. Padronização anunciada não foi executada completamente.

**Impacto positivo:** unificar economiza ~1 linha por agent × 17 agents × tokens — trivial em si, mas habilita lint regex e detecta novos drifts.

**Impacto negativo:** nenhum.

---

## Resumo

| # | Fingerprint | Severidade | Tipo |
|---|------------|-----------|------|
| 1 | agent-devops-specialist-decision-framework-and-anti-overengineering-still-stack-prescriptive-in-body-after-2026-05-18-fix-on-description-and-identity | HIGH | Stack-agnostic |
| 2 | agent-mobile-developer-ios-android-skills-too-thin-33-and-35-lines-versus-ios-hig-218-and-material-design-221-no-clear-content-boundary | MEDIUM | Coerência skills |
| 3 | agent-mobile-developer-platform-skills-loaded-eager-without-actual-platform-detection-gate-in-current-mobile-developer-md-line-72 | MEDIUM | Gate executável |
| 4 | skill-shared-workflow-detection-50-lines-mas-without-references-test-fixtures-or-precedence-rules-when-multiple-keywords-match | MEDIUM | Validação |
| 5 | skill-shared-worktree-extracted-references-branch-flow-and-session-protocol-but-not-loaded-conditionally-by-the-8-coding-agents-eager-load-pattern-persists | MEDIUM | Lazy-load gate |
| 6 | agent-frontend-developer-and-backend-developer-still-loaded-token-efficiency-inline-line-vs-load-pattern-divergence | LOW | Padronização |
