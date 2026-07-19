# Economia de Tokens — 2026-05-24

> 3 sugestões originais. Cada item traz **trecho/evidência**, **motivo** e **impactos positivos e negativos** da correção proposta. Todas foram cruzadas contra o banco de 493 fingerprints (`_index.md`) e são inéditas.

---

## T1 — A seção "Docker Development Environment" (22 linhas) está **inline** no `project-context` — a skill mais carregada do repo (14 agentes, eager) — embora seja **condicional por detecção**, exatamente como o SonarQube **logo acima**, que **é** gateado

**Severidade:** MEDIUM
**Fingerprint:** `token-project-context-docker-development-environment-section-22-lines-inlined-eager-loaded-by-14-agents-while-sonarqube-same-file-is-detection-gated`

**Evidência** — `skills/shared/project-context/SKILL.md`:

```
:222  | Detection | Skill to load |                          ← SonarQube: GATEADO por detecção
:224  | sonar-project.properties / SONAR_TOKEN | skills/devops/sonarqube/SKILL.md |
…
:230  ## Docker Development Environment                       ← 22 linhas INLINE
:232  If the project uses Docker in development, all commands … inside the container …
:234  Detection: … docker-compose.yml / compose.yml …
:241  | Run a command | docker compose exec <service> <command> |
:251  Exception: if the user says "run on host", honor it …
```

`project-context` é carregada **eager por 14 agentes** (`agents/*.md`, Foundational Rule).

**Motivo:** o contraste mora no mesmo arquivo. Logo acima da seção Docker, o SonarQube é **extraído** para `skills/devops/sonarqube/SKILL.md` e carregado **só quando detectado** (`sonar-project.properties`/`SONAR_TOKEN`). A seção Docker é **igualmente condicional** ("If the project uses Docker… Detection: docker-compose.yml"), mas seu conteúdo (22 linhas, ~300 tokens) está **inline** — entrando no contexto de **todos os 14 agentes em todo spawn**, inclusive nos projetos (a maioria) que não usam Docker no dev. O comportamento já é gateado; o **custo de token** não. Distinto de `token-skill-project-context-291-lines-x-14-agents` (que trata do **tamanho total** da skill): aqui o achado é uma **seção condicional específica e auto-contida** que pede o mesmo tratamento de extração+gate que o SonarQube ao lado já tem.

**Impacto positivo da correção:** extrair a seção para `project-context/references/docker-dev-environment.md` (ou para uma mini-skill `docker-dev`) e carregá-la **só quando** `docker-compose.yml`/`compose.yml` existir economiza ~300 tokens × 14 agentes em todo projeto não-Docker — e em fluxos multi-agente (fullstack: 6 spawns) o ganho se multiplica. Mantém o comportamento idêntico quando Docker está presente.

**Impacto negativo / risco:** baixo. Risco de o gate falhar e o agente rodar comandos no host quando deveria ser no container — mitigável replicando o padrão de detecção que o SonarQube já usa (mesma tabela `Detection | Skill to load`), que é comprovadamente confiável no projeto.

---

## T2 — `architecture-awareness` carrega **as duas metades** (Frontend SPA + Backend) no contexto dos 3 agentes que a usam — cada agente usa só uma; o `mobile-developer` não usa **nenhuma** das duas seções web

**Severidade:** LOW-MEDIUM
**Fingerprint:** `token-architecture-awareness-eager-loads-both-frontend-spa-and-backend-context-halves-into-three-agents-mobile-developer-uses-neither-web-section`

**Evidência** — `skills/shared/architecture-awareness/SKILL.md` é dividida em duas metades carregadas juntas:

```
:8-19   ## Frontend Context  (SPA: code splitting, tree-shaking, bundle analysis, …)
:23-31  ## Backend Context   (API-first vs monolítico, layer depth, …)

# Consumidores eager (Foundational Rule):
backend-developer.md:39   → usa só a metade Backend (a metade SPA é peso morto)
frontend-developer.md:65  → usa só a metade Frontend
mobile-developer.md:52    → web SPA e server-rendered templates não se aplicam a mobile nativo/RN
```

**Motivo:** a skill (31 linhas, ~450 tokens) entra inteira no contexto dos 3 agentes, mas cada um aproveita no máximo metade. O `backend-developer` carrega as dicas de otimização de bundle SPA (`vite-bundle-visualizer`, code splitting) que nunca vai usar; o `mobile-developer` carrega **as duas** seções web (SPA e templates server-rendered) sendo que trabalha em iOS/Android/React Native — onde "Blade/Twig/ERB" e "tree-shaking de SPA web" não têm aplicação. Distinto do achado de prescritividade (`03/A1`, que é sobre **conformidade** stack-agnostic): aqui o eixo é **token** — conteúdo irrelevante por papel carregado eager.

**Impacto positivo da correção:** dividir em `architecture-awareness/references/frontend.md` e `.../backend.md` e fazer cada agente carregar só a sua metade (e o `mobile-developer` carregar uma orientação **mobile-específica**, ou nenhuma) economiza ~225 tokens por spawn dos coders web e ~450 por spawn do mobile. Em `/devteam:fullstack` (backend+frontend+mobile) o ganho acumula.

**Impacto negativo / risco:** baixo. Risco de um agente full-stack precisar das duas metades — mitigável permitindo que ele carregue ambas explicitamente quando a tarefa cruzar as camadas. A maioria dos spawns é mono-camada, então o caso comum economiza.

---

## T3 — **16 descriptions de skill excedem o orçamento de ≤95 caracteres** (pior: `frontend-code-quality` com 288, ~3×) — regressão da otimização de `v1.5.3` ("trim descriptions to reduce context budget"), sem lint que a sustente

**Severidade:** LOW-MEDIUM
**Fingerprint:** `token-sixteen-skill-descriptions-exceed-95-char-budget-worst-288-inflate-always-loaded-skill-index-regression-of-v1-5-3-trim-no-lint-gate`

**Evidência** — varredura de `description:` em todos os `skills/**/SKILL.md`:

```
288  architecture/frontend-code-quality      173  shared/stack-detection
250  shared/frontend-done-checklist          168  mobile/react-native
250  design/mobile-design                    163  mobile/android
247  shared/architecture-awareness           157  shared/workflow-detection
239  mobile/material-design                  153  integrations/push-notifications
238  mobile/ios-hig                          143  mobile/ios
235  shared/runbook                          139  shared/release-prep
                                             119  mobile/flutter
                                             104  shared/interaction-patterns
→ 16 skills acima de 95 chars

# Histórico da otimização que regrediu:
v.1.3.13  perf(skills): shorten all 67 descriptions to ≤95 chars
v1.5.3    perf(skills): trim all descriptions to reduce context budget usage
```

**Motivo:** houve um esforço explícito (duas releases) para manter descriptions de skill ≤95 chars **com o objetivo declarado de reduzir orçamento de contexto** — porque as descriptions entram no índice de skills sempre presente. O esforço **regrediu**: das ~67 skills originais o repo cresceu para **129**, e as novas (e algumas antigas) voltaram a ultrapassar o limite, com casos de **~3×** (288 chars). O `helpers/agent-lint.sh` valida **presença** de `name`/`description` e chaves canônicas, mas **não valida comprimento** (`agent-lint.sh:138,150`) — então nada impede a deriva. Distinto de `skill-frontmatter-strict-validation-missing-from-lint` (que era sobre presença/chaves): aqui é o **comprimento** da description e seu custo no índice de skills.

**Impacto positivo da correção:** aparar as 16 descriptions de volta a ≤95 chars reduz o índice de skills sempre carregado (as 7 piores sozinhas somam ~1.700 chars contra um teto de ~665) e restaura o ganho de `v1.5.3`. Adicionar ao `agent-lint.sh` um check de `${#description} -le 95` (warn ou erro) **sustenta** a otimização e evita a próxima regressão — fechando a classe em vez de só limpar a instância.

**Impacto negativo / risco:** baixo. Risco de descriptions curtas demais perderem precisão de triggering (a description guia quando a skill é selecionada) — mitigável tratando 95 como **warn** (não erro bloqueante) e priorizando clareza nas skills cujo disparo é ambíguo; o objetivo é cortar verbosidade, não informação útil.
