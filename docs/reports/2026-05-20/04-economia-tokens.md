# Economia de Tokens — 2026-05-20

> Sugestões **originais** com foco em economia de tokens nos agentes/skills/hooks. Cada item traz
> evidência, motivo, estimativa de economia, impacto positivo/negativo e recomendação.

---

## T1 — "Critical rules" inline do `backend-developer` são **eager** (~70-80 linhas) e anulam o desenho lazy de detecção  · **HIGH**

**Fingerprint:** `token-backend-developer-integration-awareness-inline-critical-rules-70-80-lines-eager-loaded-every-spawn-defeats-lazy-skill-detection-pattern`

**Evidência:** `agents/backend-developer.md`, seção "Integration Awareness" (linhas ~82-173). O design
é, em tese, lazy: *"Detection: … → Load: skills/integrations/<x>/SKILL.md"*. Mas logo abaixo de cada
"Load" há um bloco **"Critical rules"** que está **no corpo do agente** — portanto carregado **sempre**,
em todo spawn de `backend-developer`, independentemente de a integração existir no projeto. São ~70-80
linhas somando as 7 sub-seções (Supabase, GoTrue, JWT, Kong, Realtime, SonarQube, Async Jobs).

**Motivo:** o ponto de detecção+skill existe justamente para **não** pagar o custo de regras de
integração que o projeto não usa. Ao manter as regras inline, o agente paga o custo das 7 integrações
em **todo** spawn — inclusive em projetos que não usam Supabase, nem Kong, nem SonarQube. É o oposto do
que a detecção promete. Cross-cut com [03-agentes-e-skills.md](03-agentes-e-skills.md) A1 (lá o ângulo é
stack-agnostic; aqui é token/eager-load).

**Estimativa de economia:** mover as "Critical rules" provider-específicas para as skills (que já são
lazy por detecção) recupera ~70-80 linhas (~**900-1.100 tokens**) por spawn de `backend-developer` em
projetos que não disparam todas as integrações — o caso comum. Em fluxos multi-agente que spawnam o
backend (`/devteam:backend`, `/devteam:fullstack`, `/devteam:fix`), o ganho se repete por execução.

**Impacto positivo:** menos tokens por spawn; o corpo do agente encolhe (ajuda no cap de 200 linhas —
backend-developer está em 261); a regra passa a ser carregada **só** quando a integração é detectada.

**Impacto negativo / risco:** se a skill não tiver a regra, mover sem migrar perde a informação. E há
um hop de carregamento a mais quando a integração existe (custo pago só no caso relevante, o que é
aceitável). Mitigar: mover (não deletar) e validar que cada skill `integrations/*` contém a regra.

**Recomendação:** extrair os blocos "Critical rules" para as respectivas
`skills/integrations/<x>/SKILL.md`, mantendo no agente apenas o gatilho de detecção + 1 linha de
princípio agnóstico. Priorizar as maiores (Supabase ~5 linhas, SonarQube ~5 linhas, Async Jobs ~5 linhas).

---

## T2 — Dedup lê o `_index.md` inteiro (676 linhas) todo dia quando só precisa da lista de slugs  · **MEDIUM**

**Fingerprint:** `token-dedup-step-reads-full-676-line-prose-index-md-every-run-when-only-fingerprint-slug-list-is-needed-extract-machine-readable-list`

**Evidência:** o passo anti-duplicação (entrada de toda geração de relatório) precisa do **conjunto de
slugs já usados** para não repropor. Hoje esse conjunto está embutido em `docs/reports/_index.md`, um
arquivo de **676 linhas** (working tree) cheio de prosa: descrições longas, notas Guardian, tabela
Statistics, legendas. Ler o arquivo todo custa ~**11k tokens** só para extrair ~445 slugs.

**Motivo:** a única coisa que o dedup *precisa* comparar é o slug (`kebab-case`) de cada fingerprint —
não a prosa. Manter uma lista achatada e legível por máquina (um slug por linha, ex.:
`docs/reports/_fingerprints.txt`, gerada a partir do índice ou mantida em paralelo) permite o dedup
fazer `grep` numa lista compacta (~445 linhas curtas, ~3-4k tokens, ou nem precisar ler tudo — só
`grep -qx`) em vez de ingerir a prosa inteira. É **distinto** dos fingerprints de "arquivar o índice"
(`token-_index-md-…-archive-index-sh-unhooked`, 7ª/8ª passadas), que tratam de **rotação por tamanho**;
aqui o ângulo é **separar o dado de dedup (slugs) da prosa humana** — uma economia que vale mesmo sem
rotação.

**Estimativa de economia:** ~7-8k tokens por geração de relatório (lê-se a lista compacta em vez da
prosa de 676 linhas); cresce junto com o índice.

**Impacto positivo:** dedup mais barato e mais robusto (comparar slugs exatos é menos sujeito a erro do
que varrer prosa); a prosa do `_index.md` continua existindo para humanos, sem ser lida pela máquina a
cada passada.

**Impacto negativo / risco:** introduz um segundo artefato que precisa ficar em sincronia com o índice
(risco de drift). Mitigar **gerando** `_fingerprints.txt` a partir do `_index.md` (script idempotente
no Stop ou no CI) em vez de mantê-lo à mão; assim a fonte única continua sendo o índice.

**Recomendação:** criar `helpers/extract-fingerprints.sh` que extrai todos os slugs `kebab-case` do
`_index.md` (e dos `_index-archive-*.md`) para `docs/reports/_fingerprints.txt`; o passo de dedup passa
a consultar esse arquivo. Bônus: cobre também os arquivos arquivados, fechando o gap apontado nas
passadas de "archive".

---

## T3 — Diretiva `comments-policy` duplicada em 8 agentes vira multiplicador de tokens em fluxos multi-agente  · **MEDIUM**

**Fingerprint:** `token-comments-policy-load-directive-duplicated-in-8-agents-multiplied-per-session-in-multi-agent-flows-fullstack-review-spawn-many-agents`

**Evidência:** a mesma diretiva multi-linha de carga do `comments-policy` (com o parêntese
`(Python → type-annotations, tests → aaa-pattern, legacy review → anti-patterns)`) aparece em **8
agentes** (`backend-developer`, `backend-reviewer`, `backend-test-specialist`, `code-reviewer`,
`database-specialist`, `devops-specialist`, `frontend-reviewer`, `frontend-test-specialist`). Ver
[01-referencias-e-consistencia.md](01-referencias-e-consistencia.md) R2 para o ângulo de consistência.

**Motivo:** num spawn isolado, só 1 agente é carregado, então o custo é 1 cópia (irrelevante). Mas em
**fluxos multi-agente** o contexto da sessão acumula vários desses corpos ao mesmo tempo: `/devteam:fullstack`
pode spawnar backend + frontend + database + 2 test-specialists; `/devteam:review` spawna
`code-reviewer` + `backend-reviewer` + `frontend-reviewer`. Nesses casos, a **mesma diretiva de ~3-4
linhas é carregada 3 a 6 vezes** na mesma janela — peso morto redundante. Ângulo **distinto** do R2
(que é manutenção/fonte-única); aqui é a **amplificação de tokens em fluxo multi-agente**.

**Estimativa de economia:** ~3-4 linhas (~40-60 tokens) × (N-1) agentes redundantes por fluxo. Em
`/devteam:review` (3 agentes) e `/devteam:fullstack` (até 6), recupera ~80-300 tokens por execução —
pequeno por fluxo, recorrente em todos eles.

**Impacto positivo:** corpos mais enxutos; menos repetição idêntica no contexto de fluxos multi-agente;
casa com a consolidação proposta em R2 (one-liner apontando para a tabela de roteamento na skill).

**Impacto negativo / risco:** baixíssimo. O único risco é o de R2 (perder a "dica" inline), mitigado
movendo o roteamento para dentro do `comments-policy/SKILL.md`.

**Recomendação:** aplicar a consolidação de R2 (substituir as 8 frases longas por uma curta) — resolve
simultaneamente a consistência (R2) e a amplificação de tokens (T3).

---

## Reverificações (já no índice; ver Guardian)

`token-_index-md-647-lines-…-archive-index-sh-still-unhooked` (8ª passada; índice hoje em 676 linhas,
crescimento confirmado, mas **não reproposto** — o ângulo de rotação já está coberto; T2 acima ataca um
ângulo diferente, o de separar slugs da prosa), `token-telemetry-helper-289-lines … _telemetry_enabled
em 3 scripts` e `token-frontend-test-specialist-react-and-vue-hook-recipes-both-eager-loaded` continuam
**🔴 não feitos** (0 commits). Não repostos.
