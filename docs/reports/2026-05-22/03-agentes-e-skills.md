# Agentes e Skills — 2026-05-22

> 3 sugestões originais. Foco do dia: **violação stack-prescritiva em agente ainda não auditado** (`backend-test-specialist`), uma **skill grande sem extração** em domínio distinto do de ontem, e a **enumeração de stacks na diretriz principal** de um agente. Cada item traz **trecho**, **motivo** e **impactos positivos e negativos**. Deduplicadas contra os 449 fingerprints.

---

## A1 — `backend-test-specialist` fixa no corpo uma matriz de comandos de cobertura **por linguagem** (Clover/pytest/JaCoCo/go test/SimpleCov) — stack-prescritivo

**Severidade:** MEDIUM-HIGH
**Fingerprint:** `agent-backend-test-specialist-body-114-120-hardcodes-per-language-coverage-command-matrix-clover-pytest-jacoco-go-simplecov-stack-prescriptive`

**Evidência** — `agents/backend-test-specialist.md:114-120` (dentro de "SonarQube Coverage Integration"):

```
| Language | Test runner flag | Output |
|---|---|---|
| PHP    | `--coverage-clover coverage/clover.xml`  | Clover XML |
| Python | `pytest --cov --cov-report=xml`          | `coverage.xml` |
| Java   | JaCoCo plugin                            | `target/site/jacoco/jacoco.xml` |
| Go     | `go test -coverprofile=coverage.out ./...` | `coverage.out` |
| Ruby   | SimpleCov (configured in `spec_helper`)  | `coverage/.resultset.json` |
```

**Motivo:** é a **mesma classe** das reaberturas do `devops-specialist` (corpo stack-prescritivo) e do achado do `security-specialist` de 2026-05-21 (matriz SAST por ferramenta), mas em um agente **ainda não flagrado** para isso — o banco só tinha sobre o `backend-test-specialist` o item de assimetria de tamanho (`agent-frontend-test-specialist-262-vs-backend-160-asymmetric`). O princípio ("gere cobertura no formato que o SonarQube espera, conforme `sonar.*coverage.reportPaths`") é stack-agnostic e correto; a **matriz concreta de linguagem→flag→arquivo** deveria viver na skill `skills/devops/sonarqube/SKILL.md` (que o agente já carrega por detecção), deixando no corpo apenas o princípio + o ponteiro para a skill. Observação: embora a seção seja "gated" por detecção de SonarQube na narrativa, a matriz está **no corpo do agente** e é carregada em todo spawn (ver dimensão de token em `04/T1`).

**Impacto positivo da correção:** conforma mais um agente ao mandato stack-agnostic; centraliza a matriz de cobertura na skill de SonarQube (mais fácil estender com novas linguagens — Rust, .NET, Node/c8); reduz o corpo do agente (160 linhas, ainda dentro do cap, mas a extração ajuda a manter assim).

**Impacto negativo / risco:** a indireção (agente → skill) significa que, para projetos com SonarQube, o LLM precisa carregar a skill para ver a matriz. Como o carregamento já é condicionado à detecção de SonarQube, o custo só incide quando relevante — risco baixo. Cuidado para mover a matriz **verbatim** e não perder nenhuma linguagem na migração.

---

## A2 — Skill `integrations/gotrue` (225 linhas, a **maior skill de integração** e 4ª maior do repo) nunca recebeu a extração `references/` e é carregada por gate narrativo

**Severidade:** LOW-MEDIUM
**Fingerprint:** `skill-integrations-gotrue-225-lines-largest-integration-skill-fourth-largest-overall-no-references-extraction-narrative-load-gate`

**Evidência** — tamanho e carregamento:

```
225 skills/integrations/gotrue/SKILL.md   # nenhum subdiretório references/
agents/backend-developer.md:102 → "Load: skills/integrations/gotrue/SKILL.md"
skills/integrations/supabase/SKILL.md:59 → "See skills/integrations/gotrue/SKILL.md for full detail."
```

**Motivo:** em 2026-05-13 o padrão `references/` foi aplicado a 7 skills grandes para permitir lazy-load por seção. A `gotrue` (225 linhas) é hoje a **maior skill do domínio `integrations/`** e a 4ª maior do repo (atrás de graphify-setup, project-context e graphql), e **nunca recebeu** esse tratamento — segue monolítica. É distinta da sugestão de ontem (`skill-architecture-graphql-…`): aquela era no domínio `architecture/`; esta é em `integrations/`, um domínio inteiro que escapou da onda de extração. O carregamento é um "Load:" narrativo no `backend-developer`, não um sinal de detecção estruturado (embora o `backend-developer` tenha tabelas de detecção para outras integrações, a do gotrue é prosa).

**Impacto positivo da correção:** extrair seções volumosas para `references/` (ex.: `flows.md`, `token-management.md`, `admin-api.md`) permite carregar só o que a tarefa precisa; e converter o gate em sinal de detecção (presença de `GOTRUE_*`/`@supabase/gotrue-js` no manifesto) torna o load determinístico.

**Impacto negativo / risco:** vale a lição da reabertura do design-patterns (R3 do Guardian): **extrair sem ligar o gate não economiza nada**. Recomenda-se fazer as duas coisas juntas (extrair **e** carregar por seção/detecção) ou nenhuma. Como `gotrue` é específica de um stack (Supabase Auth), há quem argumente que a skill inteira já é "a referência" — por isso a prioridade é LOW-MEDIUM, atrás das violações stack-prescritivas.

---

## A3 — `mobile-developer` enumera cinco stacks na **diretriz principal** (frontmatter `description`): Swift/Kotlin/React Native/Expo/Flutter

**Severidade:** LOW-MEDIUM
**Fingerprint:** `agent-mobile-developer-description-frontmatter-enumerates-five-stacks-swift-kotlin-react-native-expo-flutter-on-identity-surface`

**Evidência** — `agents/mobile-developer.md:3` (frontmatter):

```
description: Implements mobile features for iOS and Android — native (Swift/Kotlin)
and cross-platform (React Native, Expo, Flutter). Adapts to the project's stack and
platform conventions. Use for any mobile implementation task.
```

**Motivo:** o frontmatter `description` é a **diretriz principal** do agente — a superfície que o roteador usa para decidir spawn e que define a identidade do agente. Listar cinco tecnologias concretas (`Swift`, `Kotlin`, `React Native`, `Expo`, `Flutter`) é a **mesma classe** já aceita no banco para `database-specialist` (`agent-database-specialist-description-frontmatter-enumerates-12-engines`) e `devops-specialist` (`agent-devops-specialist-description-line-8-stack-list`), porém o `mobile-developer` **nunca foi flagrado** por isso. O corpo do agente já faz a coisa certa (tabela de Detection Signals nas linhas 56-73 que carrega a skill correta por sinal); a inconsistência é só na `description`, que poderia dizer "native and cross-platform stacks (detected per project)" e deixar a enumeração para os sinais de detecção.

**Impacto positivo da correção:** consistência com o tratamento dado às descrições de `database-specialist`/`devops-specialist` quando forem corrigidas; a identidade do agente passa a sobreviver ao surgimento de novos frameworks mobile (ex.: Kotlin Multiplatform, .NET MAUI) sem reescrita.

**Impacto negativo / risco:** **contra-argumento legítimo** — mobile é, por natureza, iOS/Android, e nomear os dois ecossistemas nativos + os cross-platform dominantes ajuda o roteador a casar a intenção do usuário ("preciso de algo em Flutter") com o agente certo. Generalizar demais a `description` pode **piorar o roteamento**. Por isso a severidade é LOW-MEDIUM e a recomendação é **suavizar** (manter "iOS e Android" + "stacks nativas e cross-platform detectadas por projeto", citando exemplos entre parênteses como ilustração, não como lista canônica), não apagar.
