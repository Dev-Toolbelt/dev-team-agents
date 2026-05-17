# Agentes e Skills — 2026-05-15

> Melhorias estruturais em agentes e skills: extrações, deduplicações, e gaps de cobertura.

---

## 1. `agent-setup-assistant-docker-compose-detection-belongs-in-stack-detection-skill`

**Arquivo:** `agents/setup-assistant.md:54-70`

**Observação:** o agent contém bloco bash inline de ~10 linhas para detecção de Docker Compose version (V1 `docker-compose` vs V2 `docker compose`). Skill `skills/shared/stack-detection/SKILL.md` (criada hoje) é o lar canônico esperado, mas:

- A skill foi criada com escopo mínimo (36 linhas).
- O bloco de detecção continua inline no agent.

**Por que importa:**
- Duplicação iminente: outros agents (`devops-specialist`, `database-specialist`) replicarão a heurística inline em vez de carregar a skill nova.
- Fingerprint `skill-stack-detection-still-missing-3rd-pass-shared-base-needed` (2026-05-13) foi resolvido criando a skill, mas **migração de conteúdo inline → skill** ficou pendente.

**Impacto positivo:** mover bloco para `stack-detection/SKILL.md`; setup-assistant carrega skill condicionalmente; reduz inline de ~10 linhas em N agents.

**Impacto negativo:** stack-detection skill cresce de 36 → ~50 linhas; aceitável dentro do cap ~500.

---

## 2. `agent-setup-assistant-three-roles-bundled-extractable-health-checker-update-manager`

**Arquivo:** `agents/setup-assistant.md` (238 linhas — **4º maior agent**)

**Observação:** o agent acumula 3 papéis distintos:

1. **Setup / FIRST_RUN** — bootstrap inicial de projeto (linhas 1-180)
2. **Health Check** — verificação de instalação (linhas 180-210)
3. **Update Manager** — orquestração de updates (linhas 210-238)

Cada papel:
- Tem trigger distinto (setup é via `Setup Trigger` em CLAUDE.md; Health Check é interno; Update Manager via `/devteam:update`)
- Carrega skills diferentes
- Não compartilha estado entre invocações

**Por que importa:**
- Quebra single-responsibility: spawning setup-assistant para Health Check carrega ~150 linhas de Setup que não serão usadas.
- Extração para `agents/health-checker.md` e `agents/update-manager.md` reduziria custo de spawn ~60% em casos não-setup.

**Impacto positivo:**
- setup-assistant cai para ~180 linhas (dentro do cap).
- 2 agents pequenos novos (~30 linhas cada).
- Loading time reduzido em Health Check / Update flows.

**Impacto negativo:**
- Aumenta `ls agents/` de 17 → 19 arquivos.
- Requer documentação de "qual spawnar quando" em CLAUDE.md.

---

## 3. `agent-backend-developer-95-line-integration-awareness-section-duplicates-skill-content`

**Arquivo:** `agents/backend-developer.md:82-176` (261 linhas total — **3º maior agent**)

**Observação:** seção "Integration Awareness" lista 7 sub-blocos inline:

- Supabase (linhas 82-95)
- GoTrue (96-108)
- JWT (109-121)
- Kong API Gateway (122-138)
- Realtime / WebSocket (139-150)
- Jira / Linear (151-162)
- SonarQube (163-176)

Cada bloco tem skill correspondente em `skills/integrations/*`. O padrão repo é **conditional load**, não inline.

**Por que importa:**
- Loaders inline ficam stale quando skills são atualizadas (caso clássico: jira refactor de 2026-05-13 reduziu skill de 516 → 91 linhas; agente ainda inline pre-refactor).
- 95 linhas que poderiam ser 7 referências de path = ~13 linhas.

**Impacto positivo:** backend-developer cai de 261 → ~180 linhas (dentro do cap); single-source-of-truth para cada integração; economia ~1.500 tokens/spawn.

**Impacto negativo:** Foundational Rule fica mais longa (mais loaders condicionais); precisa de detection logic clara para evitar load desnecessário.

---

## 4. `agent-mobile-developer-ios-android-platform-blocks-60-lines-no-platform-skills`

**Arquivo:** `agents/mobile-developer.md` (263 linhas — **2º maior agent**)

**Observação:** o agent contém dois blocos paralelos:

- **iOS** (linhas 80-110) — Design (Material/HIG), Permissions, Code Signing, Native standards
- **Android** (linhas 111-143) — mesma estrutura, conteúdo paralelo

Total: ~62 linhas de conteúdo platform-specific que pertence a skills inexistentes `skills/mobile/ios/SKILL.md` e `skills/mobile/android/SKILL.md` (hoje só existem `material-design`, `ios-hig` parciais).

**Por que importa:**
- Padrão de extração já estabelecido para `flutter` e `react-native` (extraídos hoje).
- iOS / Android nativos puros (Swift, Kotlin) são casos de uso reais sem owner direto.

**Impacto positivo:**
- mobile-developer cai de 263 → ~200 linhas.
- 2 novas skills com conteúdo já produzido (apenas mover).
- Roteamento condicional por detecção `xcodebuild` / `gradlew` no projeto.

**Impacto negativo:** mais 2 skills no orphan-scan; gate inline ficará mais complexo no agent.

---

## 5. `agent-frontend-test-specialist-262-vs-backend-160-asymmetric-decoupled-frontend-block-inlined`

**Arquivos:**
- `agents/frontend-test-specialist.md` (**262 linhas**)
- `agents/backend-test-specialist.md` (**160 linhas**)

**Observação:** assimetria estrutural significativa entre os dois test-specialists. Auditoria do conteúdo do frontend mostra:

- ~40 linhas de seção "Decoupled Frontend — Extra Practices" inline (testes com API mocked, CORS edge cases, contract tests)
- ~10 linhas de "Selector Priority" inline (data-testid > role > text)
- Code samples extensos (~60 linhas) para Testing Library e Cypress

Backend-test-specialist mantém structure leaner referenciando skills (`skills/testing/*`).

**Por que importa:**
- Frontend evolui mais rápido que backend (libs novas trimestralmente) → manutenção do conteúdo inline acumula.
- Asimetria sugere falta de "test-specialist-base" skill compartilhada.

**Impacto positivo:**
- Extrair "Decoupled Frontend" para `skills/testing/decoupled-frontend/SKILL.md` (~40 linhas).
- Extrair "Selector Priority" para `skills/testing/selectors-priority/SKILL.md` (~10 linhas).
- frontend-test-specialist cai para ~200 linhas (dentro do cap).

**Impacto negativo:** 2 skills pequenas (~50 linhas combined) — borderline para extração; alternativa é absorver em `skills/testing/frontend/SKILL.md` agregadora.

---

## 6. `agent-code-reviewer-15-item-foundational-rule-longest-in-repo-5-conditional-loads-eager-listed`

**Arquivo:** `agents/code-reviewer.md:35-50` (228 linhas total)

**Observação:** code-reviewer possui Foundational Rule de **15 itens** — a mais longa do repo (p50 = 10-12 itens). Itens 11-15 são loads condicionais:

```
11. Load skills/security/sonarqube/SKILL.md if SonarQube configured
12. Load skills/performance/performance-budgets/SKILL.md if frontend
13. Load skills/api-design/api-versioning/SKILL.md if API change
14. Load skills/documentation/diataxis-framework/SKILL.md if docs
15. Load skills/shared/reviewer-base/SKILL.md (always)
```

Itens 11-14 são "load if X" mas **listados eagerly na Foundational Rule** — leitor humano vê 15 items, e na prática só 3-4 carregam por sessão.

**Por que importa:**
- Cosmetic: parece exigir muito loading; intimida autores de novos reviewers.
- Estruturalmente: deveriam estar em seção "Conditional Loads" após Foundational Rule (padrão estabelecido em outros agents).

**Impacto positivo:**
- Mover itens 11-14 para nova seção "Conditional Loads"; Foundational reduce para 10 items (p50).
- code-reviewer cai marginalmente; clareza estrutural significativa.

**Impacto negativo:** zero. Apenas reorganização.

---

## 7. `skill-push-notifications-373-lines-no-references-subdir-while-sister-integrations-extracted-today`

**Arquivo:** `skills/integrations/push-notifications/SKILL.md` (**373 linhas — maior skill do repo hoje**)

**Observação:** após a batch de extrações de hoje (commits `b8ece69` monitoring, `e83eb3b` jira, kong, realtime, database-multitenancy todas reduzidas para `references/`), `push-notifications` **não foi tocado**.

Blocos cleanly extraíveis:

- Service Worker Registration (43-83) → `references/service-worker.md`
- VAPID Keys (63-118) → `references/vapid-keys.md`
- Sending Push from Node (275-309) → `references/node-sender.md`
- Framework Integration (310-321) → `references/framework-integration.md`
- Security Checklist (348-360) → `references/security.md`

**Por que importa:**
- Skill carregada por backend-developer + mobile-developer → 373 × 2 = ~12.000 tokens/sessão multi-agent.
- Pattern de extração já validado e automatizável.
- Skip aparente sem ADR documentado.

**Impacto positivo:**
- SKILL.md cai para ~60 linhas (índice).
- Lazy-loading de references/ pelos agents conforme necessidade.
- Economia ~9.000 tokens/spawn.

**Impacto negativo:** mais arquivos em `references/`; mas padrão já estabelecido para 6+ integrations.
