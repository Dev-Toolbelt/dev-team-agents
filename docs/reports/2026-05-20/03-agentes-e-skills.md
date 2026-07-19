# Agentes e Skills — 2026-05-20

> Sugestões **originais** sobre conteúdo de agentes e skills, com foco especial na regra
> **stack-agnostic** (CLAUDE.md: "no hardcoded framework, language, or tool references in agent core
> behavior"). Cada item traz evidência, motivo, impacto positivo/negativo e recomendação.

---

## A1 — `backend-developer`: a seção "Integration Awareness" duplica "Critical rules" inline para **7 integrações** (violação stack-agnostic sistêmica)  · **HIGH**

**Fingerprint:** `agent-backend-developer-integration-awareness-section-duplicates-provider-specific-critical-rules-inline-for-7-integrations-systemic-stack-prescriptive-body`

**Trecho (evidência):** `agents/backend-developer.md`, seção "Integration Awareness" (linhas ~82-173).
O padrão se repete em **7 sub-seções**: cada uma diz *"Load: `skills/integrations/<x>/SKILL.md`"* e,
logo abaixo, lista **"Critical rules"** específicas do provedor **dentro do corpo do agente**:

```
86   ### Supabase (Cloud or Self-Hosted)
92   Critical rules when Supabase is detected:
93   - RLS is the authorization layer — every table exposed via PostgREST must have RLS enabled …
95   - Use the Supabase CLI for migrations …
96   - Generate TypeScript types after schema changes: `supabase gen types typescript`
98   ### GoTrue (Auth)        → 104-106 (app_metadata, getUser()/getSession())
108  ### JWT                  → 114-116 (exp/iss/aud, none algorithm)
118  ### Kong (API Gateway)   → 124-126 (kong.yml declarativo, strip_path)
128  ### Realtime / WebSocket → 134-137 (replica identity full, Postgres Changes)
149  ### SonarQube/SonarCloud → 155-159 (quality gate, hotspots, code smells)
163  ### Async Jobs/Workers   → 169-173 (idempotência, DLQ, backoff)
```

**Motivo:** o corpo do agente (comportamento central) **hardcoda terminologia de provedores
específicos** — Supabase, PostgREST, `service_role`, `supabase gen types typescript`, GoTrue,
`app_metadata`, Kong, `kong.yml`, `replica identity full`. Isso é exatamente o que a regra
stack-agnostic proíbe no *core behavior*. Pior: cada bloco **manda carregar a skill** e **mesmo assim
repete as regras** logo abaixo — ou seja, há **duplicação de conteúdo** que deveria ser fonte única na
skill. O fingerprint de 2026-05-19 (`agent-backend-developer-realtime-critical-rules-135-137-...`)
cobria **apenas** a sub-seção Realtime (3 linhas). **Este item generaliza o achado**: o problema é o
**padrão sistêmico** de "Load skill + repetir Critical rules inline" em 7 integrações, das quais ao
menos 5 são fortemente provider-locked (Supabase, GoTrue, Kong + as derivadas). JWT e Async Jobs são
agnósticos e podem ficar; o foco da correção são as provider-específicas.

**Impacto positivo da correção:** o corpo do agente volta a ser stack-agnostic; as regras críticas
moram só nas skills `integrations/*` (fonte única, já carregadas por detecção); o agente encolhe
(backend-developer hoje = 261 linhas, o 2º maior do repo).

**Impacto negativo / risco:** as "Critical rules" inline funcionam como uma "rede de segurança" caso a
detecção/carregamento da skill falhe. Mover tudo para a skill exige garantir que cada
`skills/integrations/<x>/SKILL.md` já contenha essas regras (mover, não apenas deletar) e que o gate de
detecção seja confiável. Mitigar mantendo no agente **só** o gatilho de detecção + 1 linha de princípio
agnóstico por integração.

**Recomendação:** para cada integração provider-locked, remover o bloco "Critical rules" do agente
após confirmar que a regra existe na skill correspondente; manter no agente apenas
*"Detection: … → Load: skills/integrations/<x>/SKILL.md (segue as regras críticas de lá)"*. Aplicar
primeiro a Supabase/GoTrue/Kong (mais provider-específicas). Cross-cut com economia de tokens
([04-economia-tokens.md](04-economia-tokens.md), T1).

---

## A2 — `frontend-developer`: a seção "Security" hardcoda APIs de framework no corpo  · **MEDIUM**

**Fingerprint:** `agent-frontend-developer-security-section-134-139-hardcodes-dangerouslysetinnerhtml-vhtml-vite-next-public-framework-apis-in-agent-body`

**Trecho (evidência):** `agents/frontend-developer.md:134-139`:

```
136  - dangerouslySetInnerHTML / v-html / innerHTML: only render HTML from trusted … sources …
138  - Environment variables: only expose vars prefixed for the build tool (VITE_*, NEXT_PUBLIC_*) …
```

**Motivo:** o corpo embute APIs específicas de framework/build-tool — `dangerouslySetInnerHTML` (React),
`v-html` (Vue), `VITE_*` (Vite), `NEXT_PUBLIC_*` (Next.js). São **princípios** de segurança válidos
(não renderizar HTML não sanitizado; não vazar segredos no bundle), mas redigidos com identificadores
de stack no *core behavior*, o que a regra stack-agnostic restringe. É **distinto** do achado do
`frontend-test-specialist` (2026-05-19, receitas React/Vue de teste de hooks) — aqui é a **seção
Security** do `frontend-developer`, outro agente e outra superfície.

**Impacto positivo da correção:** a regra de segurança fica agnóstica e portável para qualquer
framework; os exemplos concretos (com nomes de API) migram para uma skill de segurança frontend
carregada por detecção, mantendo a utilidade sem poluir o corpo.

**Impacto negativo / risco:** o princípio agnóstico ("nunca injete HTML não confiável; nunca exponha
segredos no bundle do cliente") é menos acionável sem os exemplos nominais. Mitigar deixando no corpo o
princípio e movendo a tabela "framework → API perigosa equivalente" para
`skills/security/frontend-injection/` ou para a skill de UI já carregada por framework.

**Recomendação:** reescrever `frontend-developer.md:134-139` em forma agnóstica e mover os exemplos
nominais (`dangerouslySetInnerHTML`/`v-html`, `VITE_*`/`NEXT_PUBLIC_*`) para uma skill de segurança
frontend com gate de detecção por framework.

---

## A3 — `database-specialist`: a `description` (frontmatter) enumera ~12 engines + DBs gerenciados de 3 nuvens  · **MEDIUM**

**Fingerprint:** `agent-database-specialist-description-frontmatter-enumerates-12-engines-and-three-cloud-managed-db-families-stack-prescriptive-identity-surface`

**Trecho (evidência):** `agents/database-specialist.md:3` (`description:`):

> *"Covers MySQL, PostgreSQL, SQL Server, MongoDB, Redis, Cassandra, SQLite and managed cloud services
> (AWS RDS/Aurora/DynamoDB, GCP Cloud SQL/Firestore/Spanner, Azure SQL/Cosmos DB)."*

**Motivo:** a `description` é a superfície de identidade do agente (é o que o roteador/usuário lê para
decidir spawná-lo) e aqui ela **fixa uma lista fechada** de ~12 engines + famílias gerenciadas de
AWS/GCP/Azure. É o mesmo tipo de problema já reconhecido e **ainda aberto** no `devops-specialist`
(`ref-devops-specialist-description-line-8-still-lists-deployment-defaults`, reaberto ⚠️ Partial) — mas
aqui é um **agente diferente, ainda não fingerprintado**. Riscos: (a) tom não-agnóstico na identidade
do agente; (b) lista que envelhece (um engine novo, ex.: um Postgres-compatível gerenciado, "não está
coberto" pela leitura literal); (c) redundância com a tabela de detecção→skill que já existe no corpo
(linhas 63-66) e que é o lugar correto para mapear engines.

**Impacto positivo da correção:** a `description` vira agnóstica ("bancos relacionais, documento,
chave-valor e column-family, on-prem ou gerenciados em nuvem"), enquanto a **lista concreta** de engines
permanece onde pertence: a tabela de detecção→skill no corpo. Consistência com o princípio que o
projeto já aplica ao `devops-specialist`.

**Impacto negativo / risco:** a lista nominal na description ajuda a *descoberta* ("este agente sabe de
Cosmos DB?"). Removê-la pode reduzir a precisão do roteamento por palavra-chave. Mitigar mantendo
2-3 exemplos representativos ("ex.: PostgreSQL, MongoDB, Redis") + a frase agnóstica, em vez da lista
fechada de 12.

**Recomendação:** reescrever a `description` para a forma por-categoria com poucos exemplos; deixar a
enumeração completa de engines apenas na tabela de detecção→skill (`database-specialist.md:63-66`).
Idealmente, resolver junto com a reabertura do `devops-specialist` (mesmo padrão) numa única passada de
"agnosticização de descriptions".

---

## Reverificações (já no índice; ver Guardian)

`devops-specialist` body stack-prescriptive (linhas 140-156), skills iOS/Android rasas (33/35 linhas) e
`frontend-test-specialist` receitas React/Vue (107-122) continuam **🔴 não feitos** — são itens já
registrados, não sugestões novas.
