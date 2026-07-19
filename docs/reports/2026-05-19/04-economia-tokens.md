# Economia de Tokens — 2026-05-19

> Sugestões **originais** com foco em economia de tokens nos agentes/skills/hooks. Cada item traz
> evidência, motivo, estimativa de economia, impacto positivo/negativo e recomendação.

---

## T1 — `_index.md` em 647 linhas (8ª passada de crescimento); `archive-index.sh` existe mas nunca dispara  · **HIGH**

**Fingerprint:** `token-_index-md-647-lines-grew-49-in-24h-8th-consecutive-pass-archive-index-sh-shipped-but-still-unhooked-zero-rotation-firing`

> Reproposta com escopo refinado (8ª passada) — permitido pela política do índice para temas críticos
> recorrentes. Distingue-se da 7ª passada (`token-_index-md-598-lines-…`, 2026-05-18) pelo novo
> patamar (647) e pelo fato novo: **mesmo sem nenhum commit na janela, o arquivo cresceu ~49 linhas**.

**Evidência:**

- `wc -l docs/reports/_index.md` = **647** (era 598 em 2026-05-18 → +49 em 24h).
- `grep -rln archive-index` retorna apenas `helpers/archive-index.sh` — **nenhum hook, CI ou `update.sh`** o invoca.
- A "Estratégia de evolução" do próprio `_index.md` promete rotação a cada 90 dias, mas o mecanismo não está conectado.

**Motivo:** o índice é lido **na íntegra** a cada geração de relatório (este fingerprint bank é a
entrada do passo anti-duplicação). A 647 linhas, são ~10,5k tokens só para começar a auditoria, e o
pace é estável (~45-49 linhas/dia) mesmo em dias sem commits — porque a coluna "Executadas/Revertidas"
da tabela Statistics acumula prosa. Projeção: ~1.000 linhas (~16k tokens/leitura) em ~7-8 dias.

**Estimativa de economia:** acionar a rotação/arquivamento mantém o índice "ativo" em ~250-300 linhas
(~4-5k tokens), economizando ~6-11k tokens **por auditoria** (e crescente).

**Impacto positivo:** custo de leitura do índice estabiliza; arquivo ativo fica navegável.

**Impacto negativo / risco:** arquivar entradas antigas pode "esconder" fingerprints e levar a
re-sugestões se a busca anti-duplicação não cobrir o arquivo. Mitigar: o passo de dedup deve fazer
`grep` no `_index.md` **e** nos `_index-archive-*.md`.

**Recomendação:** conectar `helpers/archive-index.sh` a um gatilho (sub-script de Stop com guarda de
tamanho, ou step de CI mensal) e ajustar a checagem de dedup para varrer também os arquivos
arquivados. Alternativa imediata de baixo custo: mover a prosa histórica da coluna "Executadas" para
os relatórios diários e manter na tabela só os contadores.

---

## T2 — `frontend-test-specialist` carrega receitas React **e** Vue em todo spawn, mas o projeto usa um framework só  · **MEDIUM**

**Fingerprint:** `token-frontend-test-specialist-react-and-vue-hook-recipes-both-eager-loaded-per-spawn-but-projects-use-one-framework-per-framework-skill-gate-saves-unused`

> Sub-escopo específico, distinto do genérico `token-frontend-test-specialist-262-lines-…`
> (2026-05-18, sobre extração geral). Aqui o ângulo é o **desperdício do framework não usado**.

**Evidência:** `agents/frontend-test-specialist.md:107-122` — blocos **React** (`renderHook`) e **Vue**
(`withSetup`) lado a lado (~16-30 linhas com os exemplos), ambos sempre presentes no corpo. Cross-cut
com A1 ([03-agentes-e-skills.md](03-agentes-e-skills.md)).

**Motivo:** um projeto real é React **ou** Vue (raramente os dois). Carregar as duas receitas em todo
spawn do agente envia ~50% do conteúdo de hooks/composables como peso morto. Ao extrair para uma skill
por framework com gate de detecção, só a receita do framework ativo é carregada.

**Estimativa de economia:** ~15-30 linhas (~200-400 tokens) por spawn em que apenas um framework está
ativo; multiplicado pelos spawns de `/devteam:frontend` e `/devteam:fullstack`.

**Impacto positivo:** menos tokens por spawn; bônus de consertar a violação stack-agnostic (A1).

**Impacto negativo / risco:** se a detecção falhar, o agente não recebe nenhuma receita. Gate deve ter
fallback (carregar ambas se o sinal for ambíguo).

**Recomendação:** `skills/testing/hook-composable-testing/` com `references/react.md` e
`references/vue.md`, carregadas por sinal de stack; corpo do agente mantém só o princípio.

---

## T3 — 9 agentes somam ~305 linhas acima do cap de 200; sem gate bloqueante, o peso morto multi-agente cresce  · **MEDIUM**

**Fingerprint:** `token-aggregate-9-agents-305-lines-over-200-cap-no-blocking-gate-each-spawn-loads-full-body-multi-agent-flow-amplifies`

**Evidência:** `bash helpers/size-limits.sh` (overage por agente vs cap 200): backend-developer +61,
frontend-test-specialist +62, setup-assistant +39, devops-specialist +37, security-specialist +34,
frontend-developer +32, code-reviewer +28, qa-specialist +8, backend-reviewer +4 → **~305 linhas
agregadas** acima do limite (~4.000 tokens).

**Motivo:** cada agente é carregado **inteiro** no spawn. Em fluxos multi-agente (ex.:
`/devteam:fullstack` spawna backend + frontend + test-specialists + reviewers), o excesso somado
desses corpos vira tokens recorrentes. O fingerprint da flag `--warn-only` (2026-05-15, ✅) tratou a
existência do checador; aqui o ângulo é o **agregado de tokens em fluxo multi-agente** ligado à
ausência de gate bloqueante (cross-cut com F1 em [02-fluxos-e-workflows.md](02-fluxos-e-workflows.md)).

**Estimativa de economia:** trazer os 9 ao cap recupera ~4.000 tokens distribuídos; o ganho real
concentra-se nos fluxos que spawnam vários desses agentes ao mesmo tempo.

**Impacto positivo:** corpos enxutos = menos tokens por spawn e por fluxo; força a mover referência
para `references/` (reutilizável e lazy-loadable).

**Impacto negativo / risco:** extração mal feita pode fragmentar demais e criar muitos hops de load
(o oposto da economia). Priorizar os maiores ofensores (backend-developer, frontend-test-specialist)
e medir antes de continuar.

**Recomendação:** atacar primeiro os 2 maiores (+61/+62) extraindo blocos de exemplo para
`references/`; usar o baseline proposto em F1 para impedir novas regressões.

---

## Reverificações (já no índice; ver Guardian)

`token-telemetry-helper-289-lines … _telemetry_enabled em 3 scripts` e
`token-CLAUDE-md-426-lines-still-monolithic` continuam **🔴 não feitos** (0 commits). Não repostos.
