# Agentes e Skills — 2026-05-19

> Sugestões **originais** sobre conteúdo de agentes e skills, com foco especial na regra
> **stack-agnostic** (CLAUDE.md: "no hardcoded framework, language, or tool references in agent core
> behavior"). Cada item traz evidência, motivo, impacto positivo/negativo e recomendação.

---

## A1 — `frontend-test-specialist` embute receitas React/Vue no corpo (violação stack-agnostic)  · **HIGH**

**Fingerprint:** `agent-frontend-test-specialist-107-122-hardcodes-react-renderhook-testing-library-and-vue-withsetup-recipes-in-body-stack-agnostic`

**Trecho (evidência):** `agents/frontend-test-specialist.md`

```
107  When business logic lives in custom hooks (React) or composables (Vue), test them directly …
109  **React** — use `renderHook` from `@testing-library/react`:
112  const { result } = renderHook(() => useCartTotal(mockItems));
119  **Vue** — call composables directly inside a thin `withSetup` wrapper:
121  const { count, increment } = withSetup(() => useCounter());
```

**Motivo:** o corpo do agente (comportamento central) **hardcoda** APIs específicas de frameworks —
`@testing-library/react`, `renderHook`, `withSetup` da Vue. Isso é exatamente o que a regra
stack-agnostic proíbe no core behavior: o detalhamento por framework deveria viver em uma skill
carregada condicionalmente. É uma violação **diferente** da do `devops-specialist` (já reaberta) e
ainda não fingerprintada. O agente também é o **maior do repo (262 linhas)**, então a violação
soma-se ao problema de tamanho.

**Impacto positivo da correção:** agente volta a ser stack-agnostic; receitas viram skill reutilizável
(`skills/testing/hook-composable-testing/SKILL.md`) carregada só quando o stack frontend é detectado;
reduz o corpo do agente.

**Impacto negativo / risco:** mover exemplos para skill adiciona um hop de carregamento; se o gate de
detecção não disparar, o test-specialist perde a receita. Mitigar com gate por sinal de stack
(presença de `@testing-library/*` no `package.json`).

**Recomendação:** extrair os blocos React/Vue (linhas ~107-122) para uma skill de testing e
referenciá-la com gate de detecção, mantendo no corpo apenas o princípio agnóstico ("teste hooks/
composables diretamente, não via componente wrapper").

---

## A2 — `backend-developer` embute regras realtime Supabase/Postgres no corpo apesar de já carregar a skill `realtime`  · **MEDIUM**

**Fingerprint:** `agent-backend-developer-realtime-critical-rules-135-137-supabase-postgres-replica-identity-specific-in-body-belongs-in-realtime-skill`

**Trecho (evidência):** `agents/backend-developer.md`

```
132  Load: `skills/integrations/realtime/SKILL.md`
135  - RLS is enforced on Postgres Changes — enable it on tables before streaming to clients
136  - Run `alter table <name> replica identity full` for tables where UPDATE/DELETE …
137  - Broadcast from server via the REST API — no persistent WebSocket connection needed server-side
```

**Motivo:** o agente **manda carregar** a skill `realtime` (linha 132) e, logo abaixo, **duplica no
corpo** regras que são específicas de Supabase/Postgres ("Postgres Changes", `replica identity full`,
broadcast via REST API). Isso (a) viola stack-agnostic (terminologia de um provedor específico no
core behavior) e (b) duplica conteúdo que deveria ser fonte única na skill. Original — não há
fingerprint para realtime no `backend-developer`.

**Impacto positivo:** corpo do agente fica agnóstico; a regra mora só na skill `realtime` (fonte
única); evita divergência entre as duas cópias.

**Impacto negativo / risco:** baixo. Se a skill não detalhar essas 3 regras, é preciso movê-las para
lá antes de remover do agente (não apenas deletar).

**Recomendação:** mover as 3 "Critical rules (backend perspective)" para
`skills/integrations/realtime/SKILL.md` (seção backend) e deixar no agente só "carregue a skill
realtime para regras específicas do provedor".

---

## A3 — `reviewer-base` (19 linhas) e `reviewer-mindset` (18 linhas): duas skills compartilhadas sem fronteira documentada  · **LOW-MEDIUM**

**Fingerprint:** `skill-shared-reviewer-base-and-reviewer-mindset-two-overlapping-checklist-skills-loaded-by-4-review-agents-no-documented-boundary`

**Evidência:**

- `skills/shared/reviewer-base/SKILL.md` = 19 linhas ("canonical base review checklist").
- `skills/shared/reviewer-mindset/SKILL.md` = 18 linhas ("production-survival bias").
- Ambas carregadas por `code-reviewer`, `backend-reviewer` e `frontend-reviewer` (`*.md:12` mindset, `*.md:31/30` base).

**Motivo:** dois artefatos pequenos e conceitualmente próximos ("checklist base" vs "mindset de
revisão") carregados sempre juntos pelos mesmos 4 agentes. Não há documentação da **fronteira** entre
eles (o que vai em qual). É distinto do fingerprint `agent-three-reviewers-overlap` (2026-05-09), que
era sobre os **agentes** compartilharem ~80% de estrutura; aqui o ponto é a **duplicação conceitual
entre as duas skills** e a falta de critério de o que pertence a cada uma.

**Impacto positivo:** consolidar (ou documentar claramente a fronteira) reduz ambiguidade de autoria
e o número de loads; um único `reviewer-foundation` simplifica a manutenção.

**Impacto negativo / risco:** se forem genuinamente ortogonais (checklist acionável vs postura
mental), fundir pode misturar "o que checar" com "como pensar". Avaliar antes de consolidar.

**Recomendação:** decidir via ADR curta: **fundir** em `reviewer-foundation` (se redundantes) **ou**
adicionar um cabeçalho em cada skill declarando seu escopo exclusivo (se complementares).

---

## Reverificações (já no índice; ver Guardian)

`devops-specialist` body stack-prescriptive (linhas 140-156) e skills iOS/Android rasas (33/35
linhas) continuam **🔴 não feitos** — são reaberturas de 2026-05-18, não sugestões novas.
