# Eixo D — Agentes e skills — 2026-10-17

**Baseline:** `HEAD` = `bb0e883`. `helpers/agent-lint.sh` e `helpers/size-limits.sh` passam
limpos; nenhum agente acima do teto de 211 linhas, nenhuma linha do Agent Roster divergente da
árvore. A varredura deste eixo foi para a cobertura da camada de spec, que é o material novo.

---

## MEDIUM-HIGH

### A camada de spec reconhece quatro layers em `touches` e só tem autor de teste para três — `database` não tem nenhum

- **Fingerprint:** `skill-spec-gate-touches-accepts-database-layer-with-no-test-author-in-any-track`
- **Alvo:** `skills/shared/spec-gate/SKILL.md`
- **Evidência:**
  - `skills/shared/spec-gate/SKILL.md:27` — "`touches: [backend, frontend, database, mobile]`
    (layers this feature affects — list only the ones that actually change)"
  - `scripts/lib/spec_lint.py:21` — `LAYERS = ("backend", "frontend", "database", "mobile")`,
    e `:157-163` rejeita como ERROR qualquer layer fora dessa tupla: `database` é um valor de
    primeira classe
  - `skills/shared/spec-gate/SKILL.md:126` — "The test author for the track —
    `backend-test-specialist`, `frontend-test-specialist`, or `mobile-developer` for
    Flutter/native suites —"; e `:132` — "Every implementation command applies this per track:
    **backend, frontend, and mobile alike**". Três tracks.
  - `commands/spec.md:44` — "Spawn one test author per `touches` layer, in parallel
    (`backend-test-specialist`, `frontend-test-specialist`, or `mobile-developer` in a tests-only
    spawn for Flutter/native)". Três de novo.
  - `commands/spec.md:42` — o Step 5 só é pulado "when `TESTS_REQUIRED=no` … or when the spec's
    `touches` is **empty**". `touches: [database]` não é vazio.
- **Problema:** `database` é aceito pelo template, pela skill e pelo lint, mas nenhuma das três
  listas de autor de teste o cobre. Uma spec `touches: [database]` entra no Step 5 de
  `/devteam:spec`, e no § Test-First Derivation de `/devteam:sprint` e dos comandos de
  implementação, sem agente para spawnar. `database-specialist` está no Agent Roster
  (`skills/architecture/orchestration/SKILL.md:131`) e carrega o Scope Lock
  (`agents/database-specialist.md:29`), mas não é autor de teste em lugar nenhum — e
  `commands/dba.md` não menciona `spec-gate` uma vez (`grep -c spec-gate commands/dba.md` → 0).
- **Por que importa no `HEAD` atual:** o efeito não é só uma etapa pulada, é um aviso permanente.
  `scripts/lib/spec_lint.py:282-293` (`check_coverage`) emite WARN para toda spec `implemented`
  cujos IDs não carreguem o token `[spec:<feature>#S<n>]`. Uma spec de migração/esquema nunca
  recebe esse token, porque nenhum track é responsável por taggeá-la — então ela avisa a cada
  `Stop` que toque a camada, para sempre, sobre uma lacuna que o fluxo não tem como fechar. Isso
  também é exatamente o par do achado do Eixo C sobre o reset que nunca é chamado: um WARN que o
  turno não consegue limpar é o cenário que `lib/warn-once.sh` existe para administrar.
- **Proposta:** decidir qual das duas, e aplicar nos três lugares de uma vez — (a) nomear
  `backend-test-specialist` como autor do track `database` em `spec-gate:126,132` e
  `commands/spec.md:44` (testes de migração e query rodam no suite de backend na maioria das
  stacks), ou (b) tirar `database` de `LAYERS` e do template, tratando esquema como parte do
  track backend.
- **Impacto positivo:** fecha o único layer declarado sem dono; elimina uma classe de WARN
  permanente do `spec-lint`; devolve consistência entre `spec_lint.py:21`, `spec-gate:27` e as
  duas listas de autor.
- **Impacto negativo / risco:** a opção (a) dá a `backend-test-specialist` um track cuja
  execução depende de ferramenta de migração que ele não conhece — testes de esquema costumam
  exigir banco de verdade, e um autor de teste que não consegue rodar o suite escreve asserção
  cega; é um caminho novo para o `<HARD-GATE>` do Scope Lock disparar. A opção (b) remove
  expressividade: uma spec puramente de esquema perde a forma de declarar o que toca, e specs já
  escritas com `touches: [database]` passam a falhar no lint — exige um passo de migração.
- **Esforço:** Médio
