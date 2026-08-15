# Eixo A — Agnosticismo de stack

**Baseline:** `HEAD` = `c03f898` · **Escopo:** varredura integral de `agents/` + `commands/`

**Resultado: 122 candidatos → 3 violações.**

A varredura semente obrigatória foi executada exatamente como especificada e retornou **122 linhas
com hit** em 24 arquivos (`agents/devops-specialist.md` 23, `agents/mobile-developer.md` 12,
`agents/database-specialist.md` 12, `agents/security-specialist.md` 8, `agents/product-analyst.md` 8,
`agents/frontend-test-specialist.md` 8, `agents/frontend-developer.md` 8, demais ≤ 5).

## Por que 119 candidatos não viraram violação

| Motivo do descarte | Aprox. | Exemplos |
|---|---|---|
| **Falso positivo por substring** — o termo semente aparece dentro de uma palavra inglesa comum | ~24 | `flaws`→`aws` (`agents/security-specialist.md:73`), `expression`/`expressible`→`express` (`agents/security-specialist.md:80`, `commands/rule.md:27`), `honest`→`nest` (`agents/product-analyst.md:94`), `perspective`→`rspec` (`agents/qa-specialist.md:3,9`), `pipeline`→`pip` (dezenas), `Auto-reactivation`→`react` (`agents/software-architect.md:89`), `explicit bootstrap`→`bootstrap` (`agents/backend-developer.md:100`, `agents/frontend-developer.md:139`), `reactive state`→`react` (`agents/frontend-developer.md:147`) |
| **Tabela de detecção / lista de sinais** — a regra de descarte explícita do eixo | ~55 | `agents/database-specialist.md:56-73`, `agents/devops-specialist.md:66-79`, `agents/frontend-developer.md:65-72,82-88`, `agents/mobile-developer.md:135-142`, `agents/ui-ux-designer.md:57-59`, `agents/frontend-test-specialist.md:27` |
| **Bloco de exemplo / template de output** | ~6 | `agents/code-reviewer.md:79` (`# Examples: npm run lint, composer phpcs…`), `agents/backend-reviewer.md:160-175` (formato de review com `file.go`/`file.php`/`file.py`/`file.rb` como placeholders deliberadamente variados), `commands/adr.md:12` (título de ADR de exemplo) |
| **Lista de skill condicional / delegação** | ~12 | `agents/backend-developer.md:79-86`, `agents/security-specialist.md:48,146`, `agents/devops-specialist.md:70-79`, `agents/database-specialist.md:60-73` |
| **Ilustração `e.g.` dentro de regra já agnóstica** — a regra em si não acopla | ~8 | `agents/frontend-developer.md:91` (`e.g. React \`useState\``) e `:96` (a regra é "adopting the server-state library idiomatic to the project's stack"; o parêntese é ilustrativo), `agents/frontend-reviewer.md:110-114` (a linha 110 abre com "Apply whatever type discipline the project has adopted") |
| **Acoplamento real e legítimo à ferramenta do próprio harness** | ~6 | `commands/health-check.md:50` ("Python Prerequisite" — o render engine é Python de fato), `agents/setup-assistant.md:26,66,74` (probe de Compose delegado ao `stack-detection`), `commands/commit.md:46-55` e `commands/relayout.md:43` (teardown/isolamento "isolated Docker stack **only**", que é a redação canônica do skill) |
| **Anti-acoplamento** — o trecho existe justamente para proibir o default de stack | 1 | `commands/explain.md:48` — "detected from the repo — never defaulting to JavaScript" |
| **Já registrado e aberto / já registrado como executado (porta de estado + porta semântica)** | ~7 | ver `## Descartados por duplicação` |

Dois candidatos ficaram na fronteira e **não** foram promovidos, para não inflar volume:

- `agents/database-specialist.md:84` — "**Multi-tenant:** RLS (default for PostgreSQL) → schema-per-tenant…":
  a cascata nomeia um engine, mas o faz como condicional explícita ("default *for* PostgreSQL"),
  não como prescrição cega. Imprecisão sem consequência funcional; abaixo do limiar de LOW-MEDIUM.
- `agents/mobile-developer.md:159` — "Framework skill loaded if applicable (React Native or Flutter)":
  enumera dois frameworks no checklist de Done, mas hedgeado com "if applicable" e espelhando a
  tabela de roteamento das linhas 54-74, que é seção de detecção legítima.

---

## HIGH

Nenhum achado original nesta severidade.

## MEDIUM-HIGH

### `/devteam:audit` manda subir stack Docker isolado incondicionalmente, ignorando os dois gates canônicos do skill de worktree

- **Fingerprint:** `flow-audit-step2-unconditional-docker-stack-ignores-isolate-pref-compose-gate`
- **Alvo:** `commands/audit.md`
- **Evidência:**
  - `commands/audit.md:44` — heading da seção: "`## Step 2 — Worktree + isolated infra`"
  - `commands/audit.md:54` — "`3. After worktree creation, spin up an isolated Docker stack following the worktree's docker-isolation references.`"
  - `commands/audit.md:49` — "`**Isolated worktree** — dedicated worktree plus an isolated infrastructure stack`"
  - Regra canônica contrariada, `skills/shared/worktree/references/docker-isolation.md:10-12` — "`Applies only when **both** hold:`" / "`- \`worktree_docker_isolate\` is \`true\` in \`.dev-team-agents/user-data/preferences.json\`, and`" / "`- the project uses Docker Compose (a compose file exists and \`docker\` is running).`"
  - `grep -c worktree_docker_isolate commands/audit.md` → `0` (o comando nunca lê a preferência)
- **Problema:** o passo 3 é imperativo e incondicional ("spin up an isolated Docker stack"), enquanto
  o skill que ele manda seguir declara dois gates obrigatórios — a preferência `worktree_docker_isolate`
  e a existência de compose file com daemon ativo. `commands/audit.md` é o **único** comando do repo que
  ordena o spin-up sem hedge: `commands/relayout.md:43` diz "isolate any project-specific infra (Docker
  stack, ports, seeded volumes) **per that skill**" e `commands/commit.md:50` usa a redação canônica
  "isolated Docker stack **only**". O `product-analyst` chega a ter um item de plano só para isso —
  `agents/product-analyst.md:146-150`: "`4. **Gate isolated infra on Docker.** … **isolated Docker stack per worktree only when the project uses Docker** (a compose file exists).`"
- **Por que importa:** num projeto sem Compose o passo é impossível e o agente improvisa (cria compose,
  pula silenciosamente, ou reporta falha); num projeto com Compose mas com `worktree_docker_isolate: false`,
  o comando **sobrepõe uma preferência explícita do usuário** — e `/devteam:audit` é um comando de
  análise, que não precisa de stack no ar para ler código. O custo é containers subidos sem necessidade
  em toda auditoria com worktree.
- **Proposta:** trocar o passo 3 por uma delegação hedgeada, no mesmo padrão de `relayout.md:43`:
  "Se `worktree_docker_isolate` estiver ativo **e** houver compose file, siga `references/docker-isolation.md`;
  caso contrário, prossiga só com o worktree." Sem restatement dos mecanismos.
- **Impacto positivo:** elimina um passo impossível/indesejado em duas classes de projeto, alinha o
  comando aos outros dois que já delegam corretamente e devolve o controle à preferência do usuário.
- **Impacto negativo / risco:** o passo passa a ter uma condicional que o autor do comando precisa manter
  em sincronia com o skill; e em projeto Docker onde a auditoria de fato roda serviços, o agente pode
  precisar de um passo extra explícito para subir a stack, que hoje vem de graça.
- **Esforço:** Baixo

## MEDIUM

### O comando `/devteam:mobile` reintroduz na linha de spawn a enumeração de stacks que já foi removida da identidade do `mobile-developer`

- **Fingerprint:** `flow-mobile-command-spawn-line-enumerates-stacks-dropped-from-agent-description`
- **Alvo:** `commands/mobile.md`
- **Evidência:**
  - `commands/mobile.md:18` — heading/linha de seção: "`Phase 1 — spawn in parallel:`"
  - `commands/mobile.md:19` — "`- \`mobile-developer\` — implement the mobile changes (React Native, Expo, Flutter, native iOS/Android)`"
  - Estado atual do alvo do fix anterior, `agents/mobile-developer.md:3` — "`description: Implements mobile features for iOS and Android, whether the project is native or cross-platform. Detects the project's mobile stack and follows its platform conventions.`"
- **Problema:** a descrição do agente foi desenumerada (fingerprint `agent-mobile-developer-description-frontmatter-enumerates-five-stacks-…`, ✅ Executed em 2026-07-31), mas a linha de spawn do comando que invoca esse mesmo agente ainda carrega o conjunto fechado
  "React Native, Expo, Flutter, native iOS/Android" — as cinco stacks originais, verbatim. A correção foi aplicada a uma superfície e não à outra.
- **Por que importa:** essa linha é comportamento, não referência: é o texto que descreve o escopo do
  spawn na Fase 1. Um projeto mobile fora dessas cinco stacks (KMP, .NET MAUI, Ionic/Capacitor, Tauri Mobile)
  lê como fora de escopo do comando, exatamente o efeito que a remoção na descrição do agente pretendia
  evitar. É também drift ativo: o gate que pegou o defeito na descrição (`agent-lint.sh` não cobre corpo de comando) não pega esta cópia.
- **Proposta:** trocar o parêntese por "implement the mobile changes for the project's detected stack
  (native or cross-platform)" — a mesma redação que a descrição do agente já usa.
- **Impacto positivo:** fecha o último resquício da enumeração no fluxo mobile e torna `/devteam:mobile`
  aplicável a qualquer stack detectada, sem mudar nenhum mecanismo.
- **Impacto negativo / risco:** perde-se a pista concreta que ajudava o leitor humano a reconhecer
  imediatamente para que serve o comando; e a linha 26 (`For React Native / Expo (JS/TS) suites → spawn \`frontend-test-specialist\``)
  continua nomeando stack — se só a linha 19 for corrigida, o arquivo fica internamente inconsistente.
- **Esforço:** Baixo
- **Refina:** `agent-mobile-developer-description-frontmatter-enumerates-five-stacks-swift-kotlin-react-native-expo-flutter-on-identity-surface` — o pai descreveu e corrigiu apenas o frontmatter do agente; a linha de spawn do comando não foi descrita nem tocada.

## LOW-MEDIUM

### `database-specialist` delega os padrões de CLI aos skills por engine e, na mesma linha, inlina o de um fornecedor

- **Fingerprint:** `agent-database-specialist-access-inlines-supabase-cli-while-delegating-others`
- **Alvo:** `agents/database-specialist.md`
- **Evidência:**
  - `agents/database-specialist.md:131` — heading da seção: "`## Database Access`"
  - `agents/database-specialist.md:133` — "`Discover connections from: \`DATABASE_URL\`/\`SUPABASE_DB_URL\`/\`MONGO_URI\`/\`REDIS_URL\` env vars → … CLI patterns are in each engine's per-engine skill. Supabase PostgreSQL: \`psql "$SUPABASE_DB_URL"\`.`"
- **Problema:** a própria frase estabelece a regra ("CLI patterns are in each engine's per-engine skill")
  e a quebra na sentença seguinte, inlinando o comando de conexão de **um** fornecedor gerenciado
  (Supabase) no corpo do agente. Nenhum outro engine ou provedor recebe tratamento equivalente ali —
  MySQL, MongoDB, Redis, SQL Server e os gerenciados de AWS/GCP/Azure são todos roteados via tabela
  (linhas 66-73) para seus skills.
- **Por que importa:** cria um precedente assimétrico dentro de uma seção de comportamento — o próximo
  autor que precisar de um atalho para outro provedor tem um exemplo autorizando inlinar mais uma linha,
  e o corpo do agente vira o segundo lugar onde padrões de CLI vivem. O `psql "$SUPABASE_DB_URL"` também
  não acrescenta informação: a variável já está listada na própria frase e `psql` já pertence a
  `skills/database/postgres/SKILL.md`.
- **Proposta:** remover a sentença final e, se o atalho tiver valor, movê-lo para
  `skills/database/postgres/SKILL.md` (ou `skills/integrations/database-production/SKILL.md`, onde os
  gerenciados já moram), preservando só a regra de delegação.
- **Impacto positivo:** restaura casa canônica única para padrões de CLI e remove ~1 linha de acoplamento
  a fornecedor de uma seção de comportamento carregada em toda invocação do agente.
- **Impacto negativo / risco:** projetos Supabase perdem o atalho imediato no corpo do agente e passam a
  depender de o skill de PostgreSQL ser carregado antes do acesso — um round-trip a mais quando o skill
  ainda não estiver em contexto.
- **Esforço:** Baixo

## LOW

Nenhum achado original nesta severidade.

---

## Descartados por duplicação

| Candidato | Evidência | Porta que rejeitou |
|---|---|---|
| `commands/relayout.md:32` — "`a Storybook config, a Tailwind/theme config`" na descoberta de design system | `commands/relayout.md:32` | **Porta 5 (estado)** — `flow-relayout-design-discovery-names-storybook-tailwind` está no conjunto aberto |
| `agents/frontend-test-specialist.md:139-151` — bloco de coverage SonarQube com `jest --coverage` / `vitest run --coverage` e `sonar.javascript.lcov.reportPaths` | `agents/frontend-test-specialist.md:142-151` | **Porta 5 (estado)** — `agent-frontend-test-specialist-sonarqube-coverage-block-hardcodes-jest-vitest-commands…` aberto |
| `agents/frontend-developer.md:3` — "`(React, Vue, Svelte, Angular)`" e "`(Blade, Twig, ERB, Jinja)`" no frontmatter | `agents/frontend-developer.md:3` | **Porta 5 (estado)** — `agent-frontend-developer-description-frontmatter-enumerates-eight-frameworks…` aberto |
| `agents/devops-specialist.md:46-56` — "`**Primary**: Docker`", AWS/GCP/Azure, Terraform em Core Expertise | `agents/devops-specialist.md:46` | **Porta 5 (estado)** — `agent-devops-specialist-core-expertise-declares-primary-docker…` aberto |
| `agents/devops-specialist.md:137-148` — checklist de Done com Docker e "`(if Terraform is in use)`" | `agents/devops-specialist.md:137,147,148` | **Porta 4 (escopo menor)** — o slug aberto já nomeia explicitamente `…-and-done-checklist-gates-on-docker-terraform`; não é sub-escopo não descrito |
| `commands/audit.md:126,128` — "`Caching opportunities (Redis, CDN, HTTP caching)`" / "`Docker/resource concerns`" no prompt de spawn | `commands/audit.md:126-128` | **Porta 5 (estado)** — `flow-audit-command-devops-analysis-prompt-names-redis-cdn-docker-inside-spawn-instruction` aberto |
| `commands/devops.md:2,14` — "`description: CI/CD, Docker, infra, and deploy scripts`" | `commands/devops.md:2` | **Porta 3 (semântica)** — vs. `agent-devops-specialist-core-expertise-declares-primary-docker…`: causa raiz (Docker como produto-título da superfície devops) e remediação (redação agnóstica) coincidem — 2 de 3 |
| `agents/frontend-reviewer.md:112,114` — `PropTypes`, `Vue defineProps`, `React.ChangeEvent<HTMLInputElement>` | `agents/frontend-reviewer.md:112,114` | **Porta 3 (semântica)** — mesmo alvo, mesma causa e mesma remediação de `agent-frontend-reviewer-body-type-safety-and-code-quality-hardcodes-react-ts-identifiers-proptypes-react-changeevent-hocs` (3 de 3). *Nota para a Fase 1:* aquele fingerprint está marcado ✅ Executed em 2026-07-31 e os identificadores citados **seguem presentes** no HEAD — a linha 110 ganhou o preâmbulo agnóstico, mas os exemplos não saíram. Sugere-se reverificação como 🟡, não como achado novo deste eixo. |
| `commands/commit.md:135-138` — `npm run lint`, `vendor/bin/phpcs` | `commands/commit.md:135,138` | **Porta 5 (estado)** — já listado em `_index.md:340` como descarte anterior deste eixo |
| `agents/setup-assistant.md:146-147` — `jest.config.*`, `pytest.ini`, `phpunit.xml` | `agents/setup-assistant.md:146-147` | **Porta 5 (estado)** — já listado em `_index.md:340` como descarte anterior deste eixo |
| `agents/database-specialist.md:66-73` — tabela de engines e gerenciados | `agents/database-specialist.md:66-73` | **Porta 3 (semântica)** parcial + regra de descarte do eixo (tabela de detecção); tema já coberto por `agent-database-specialist-description-frontmatter-enumerates-12-engines…` |
