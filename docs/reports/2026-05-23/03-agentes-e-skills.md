# Agentes e Skills — 2026-05-23

> 3 sugestões originais. Cada item traz **trecho/evidência**, **motivo** e **impactos positivos e negativos** da correção proposta. Todas foram cruzadas contra o banco de 481 fingerprints (`_index.md`) e são inéditas.

---

## A1 — `frontend-developer` fixa identificadores React (`useState`/`useEffect`) e bibliotecas nomeadas (TanStack Query, SWR) **no corpo** (seção de data fetching) — violação stack-agnostic distinta da seção de segurança já flagrada

**Severidade:** MEDIUM
**Fingerprint:** `agent-frontend-developer-body-92-102-data-fetching-section-hardcodes-usestate-useeffect-tanstack-query-swr-stack-prescriptive`

**Evidência** — `agents/frontend-developer.md:98,102` (princípios no corpo, **fora** da tabela de detecção das linhas 79-92):

```markdown
:98  - **Never duplicate server state in `useState`** — creates synchronization bugs; let the library own the state
:102 - If no library is detected: `useEffect + useState` is acceptable for simple one-off fetches; for
      caching, background refetch, or shared state across components, recommend adopting TanStack Query or SWR
```

**Motivo:** os princípios são bons e genéricos ("não duplique estado de servidor no estado local"; "para cache/refetch, adote uma lib de data-fetching"), mas estão **redigidos com identificadores React** (`useState`, `useEffect`) e **bibliotecas nomeadas** (TanStack Query, SWR) diretamente no corpo do agente — não numa tabela de detecção→skill. Para um projeto Vue (`ref`/`reactive` + Vue Query), Svelte (stores + `svelte-query`) ou Angular (signals + `@tanstack/angular-query`), a redação é estrangeira. É a **mesma classe** da já-flagrada seção de Segurança do mesmo agente (`agent-frontend-developer-security-section-134-139-hardcodes-dangerouslysetinnerhtml-vhtml-vite-next`, 2026-05-20), mas uma **seção diferente** (Data Fetching / State Management) com **identificadores diferentes** — portanto inédita. Observação: as linhas 79-92 logo acima (tabela "Chakra UI / TanStack Query → skill") são o padrão **correto**; o problema é só nos princípios 98 e 102 que escaparam para o corpo.

**Impacto positivo da correção:** reescrever os princípios de forma agnóstica ("nunca duplique estado de servidor no estado local do componente"; "quando precisar de cache/refetch/estado compartilhado, adote a biblioteca de data-fetching do ecossistema detectado — ver tabela de detecção") preserva a orientação e remove o viés; mantém os nomes concretos na tabela de detecção como fonte única.

**Impacto negativo / risco:** baixo. Exemplos concretos ajudam a clareza; mitigação é movê-los para a tabela de detecção (já existente) em vez de apagá-los. Risco de regressão é o mesmo das demais seções stack-prescritivas: reaparece a cada feature — vale o validador de description/corpo agnóstico sugerido em passadas anteriores.

---

## A2 — A skill `security-checklist` é carregada por **dois** agentes (`security-specialist` e `qa-specialist`) sem fronteira documentada — responsabilidade de segurança sobreposta

**Severidade:** LOW-MEDIUM
**Fingerprint:** `skill-security-checklist-eager-loaded-by-both-security-specialist-and-qa-specialist-no-documented-boundary-overlapping-responsibility`

**Evidência** — a mesma skill (123 linhas) carregada por dois papéis:

```
agents/security-specialist.md:22  7. Load skills/security/security-checklist/SKILL.md — OWASP/CWE checklist for structured audit coverage
agents/qa-specialist.md:30        Load security-checklist skill … auth flows, input validation, access
                                  control, and sensitive data exposure are QA concerns, not only security-specialist concerns
```

**Motivo:** dois agentes carregam a `security-checklist` e ambos reivindicam o **mesmo território** — "auth flows, input validation, access control". O `qa-specialist:30` explicita que considera segurança "QA concern, não só do security-specialist". Não há, em lugar nenhum (nem na CLAUDE.md, nem nas skills), uma **fronteira documentada** de divisão de trabalho: o que o QA cobre de segurança vs o que o security-specialist cobre, e como evitar que ambos reportem os mesmos achados num quality gate onde os dois rodam. É a **mesma classe** do achado `skill-shared-reviewer-base-and-reviewer-mindset-…-no-documented-boundary` (2026-05-19), mas um **par diferente** (skill `security-checklist` × agentes `security-specialist`/`qa-specialist`). Em fluxos como `/devteam:qa` seguido de `/devteam:security`, o risco é retrabalho e relatórios redundantes.

**Impacto positivo da correção:** documentar a fronteira (ex.: QA valida **comportamento** de controles de segurança em fluxos críticos; security-specialist faz a **auditoria estrutural** OWASP/CWE/cadeia de suprimentos) — uma nota curta na CLAUDE.md ou no topo da skill — elimina sobreposição e duplicação de achados.

**Impacto negativo / risco:** baixo. Risco de **sub**-cobertura se a fronteira for desenhada com lacuna (algo que "ambos achavam que o outro cobria"). Mitigação: a fronteira deve ser explícita e complementar, não exclusiva — segurança "em profundidade" tolera alguma sobreposição intencional.

---

## A3 — O `code-reviewer` (router) tem **10 categorias completas de revisão estrutural** no corpo, contradizendo a CLAUDE.md (que diz que o router **não duplica** as checagens estruturais dos especialistas)

**Severidade:** MEDIUM-HIGH
**Fingerprint:** `agent-code-reviewer-router-has-ten-structural-review-categories-contradicting-claude-md-183-router-does-not-duplicate-specialist-checks`

**Evidência** — a CLAUDE.md descreve o papel do router:

```
CLAUDE.md:183  "… The router does not duplicate the structural checks of the specialists —
                it coordinates and synthesizes their outputs into a single review verdict."
```

Mas `agents/code-reviewer.md` (228 linhas) traz **10 categorias de revisão estrutural completas** no próprio corpo:

```
:57 ## Review Categories
:59 ### 1. Correctness        :87 ### 5. Design & Patterns (SOLID, Object Calisthenics)
:68 ### 2. Code Repetition&DRY :97 ### 6. Linting & Style
:74 ### 3. Race Conditions     :105 ### 7. Performance
:80 ### 4. Silent Bugs         :112 ### 8. Security (surface-level)
                               :120 ### 9. Comments   :129 ### 10. Type Safety
```

**Motivo:** a CLAUDE.md posiciona o `code-reviewer` como **router/coordenador** que classifica o diff, delega a `backend-reviewer`/`frontend-reviewer` e **sintetiza** — explicitamente "não duplica as checagens estruturais dos especialistas". Na prática, o `code-reviewer.md` é um **revisor completo**: 10 categorias estruturais (SOLID, Object Calisthenics, race conditions, performance, type safety…) que são exatamente o que os especialistas fazem. Há, portanto, uma **contradição direta entre a doc e a implementação**, com duas consequências: (1) **duplicação de trabalho** num `/devteam:review` (router revisa tudo, depois cada especialista revisa de novo); (2) o agente router infla para 228 linhas (acima do cap) carregando critérios que, pela doc, não deveriam estar nele. Distinto do fingerprint `ref-claude-md-183-code-reviewer-roles-says-delegates-to-test-specialists-but-impl-routes-to-backend-frontend-reviewer` (2026-05-19), que tratava do **alvo errado da delegação** (test-specialists vs reviewers); este achado é sobre o router **executar** as checagens estruturais que a doc diz que ele **não** executa.

**Impacto positivo da correção:** decidir o papel real e alinhar os dois lados. Se o router deve coordenar: extrair as 10 categorias para os especialistas (o `code-reviewer` encolhe bem abaixo do cap e a duplicação de `/devteam:review` desaparece). Se o router deve revisar: corrigir a CLAUDE.md:183 para refletir que ele faz uma primeira passada estrutural. Em ambos os casos some a contradição.

**Impacto negativo / risco:** médio se a opção for extrair — é preciso garantir que `backend-reviewer`/`frontend-reviewer` cubram **todas** as 10 categorias antes de removê-las do router (senão abre lacuna de cobertura). Mitigação: mapear categoria→especialista antes de mover; alternativa de menor risco é corrigir a doc primeiro e tratar a extração como refactor separado.
