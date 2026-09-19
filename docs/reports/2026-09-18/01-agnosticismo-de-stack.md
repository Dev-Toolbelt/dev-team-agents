# Eixo A — Agnosticismo de Stack — 2026-09-18

**Baseline:** `HEAD` = `ef69da3` · **Varredura integral** de `agents/` e `commands/` (sem amostragem)

**Varredura semente:** **124 candidatos → 4 violações**

Os 120 restantes caíram assim:

| Motivo | N | Detalhe |
|---|---|---|
| Falso positivo por substring | ~25 | o regex semente não usa fronteira de palavra — `pip` em *pipeline* (×13), `express` em *expressed/expressible*, `rspec` em *perspective*, `react` em *Auto-reactivation*, `nest` em *honest/nested* |
| Tabela de detecção / lista de sinais / roteamento condicional de skill | ~40 | exceção explícita do eixo |
| Bloco rotulado "Examples" | 3 | `code-reviewer.md:79`, `adr.md:12`, `explain.md:63` |
| Ferramenta do próprio harness | ~14 | isolamento Docker por worktree (`product-analyst`, `commit.md`, `merge.md`, `relayout.md`); pré-requisito Python do instalador (`health-check.md:50`) |
| Cláusula anti-acoplamento | 2 | `explain.md:48` ("never defaulting to JavaScript"), `product-analyst.md:179` |
| Porta 5 — já registrado e aberto | 22 | ver tabela de descartes |
| Porta 3 — duplicata semântica | ~12 | ver tabela de descartes |

> **Nota de método.** A contagem de candidatos é **idêntica** à de 2026-09-11 porque
> `git diff 9530551..ef69da3 -- agents/ commands/` é **vazio** — nenhum dos dois diretórios foi
> tocado no delta. As quatro violações abaixo são, portanto, achados de varredura mais profunda,
> não regressões novas.

---

## MEDIUM-HIGH

### O fallback das Routing Rules do `mobile-developer` congela uma matriz de 5 runners que a skill canônica já resolve em 11

- **Fingerprint:** `agent-mobile-developer-routing-rules-restates-five-runner-matrix`
- **Alvo:** `agents/mobile-developer.md`
- **Evidência:** `agents/mobile-developer.md:149` (seção `### Routing Rules`) — "If **no E2E framework** is detected → run the project's unit test command (`jest`, `vitest`, `flutter test`, `xcodebuild test`, `./gradlew test`) scoped to the touched code and note the gap"; três linhas abaixo, `:152` — "Every run above covers only the flows and targets touching your change — the Definition of Done below names the governing skill"; e `:171` — "load `skills/shared/scoped-test-execution/SKILL.md` **before** invoking any test runner and derive the scope from it". A tabela canônica em `skills/shared/scoped-test-execution/SKILL.md` § Runner Filters tem **11 linhas** (Jest · Vitest · Playwright/Cypress · pytest · PHPUnit/Pest · Go · Gradle/JUnit · Flutter · RSpec · Xcode · Cargo) e fecha com "When the project defines its own scoped script in `CLAUDE.md`, `package.json`, or a `Makefile`, that command wins over the table".
- **Problema:** o corpo do agente reescreve um subconjunto estrito (5 de 11) da tabela canônica, sem os filtros de escopo (`--findRelatedTests`, `--tests '<FQCN>'`, `-only-testing:`) e sem a regra de precedência do script do projeto. Viola duas regras ao mesmo tempo: *Canonical Rule Homes — Delegate, Never Restate* (a linha de `scoped-test-execution` no `CLAUDE.md` manda os agentes adicionarem **"Nothing"**) e o agnosticismo de stack — .NET MAUI, Kotlin Multiplatform e NativeScript não têm entrada.
- **Por que importa:** no HEAD o agente recebe duas instruções conflitantes na mesma seção — `:149` entrega o comando pronto, `:171` manda derivá-lo da skill — e a que aparece primeiro na leitura vence. Nenhum gate cobre: `agent-lint.sh` não valida restatements e `orphan-skill-scan.sh` vê a referência de `:171` como satisfeita. O gêmeo backend (`agent-backend-test-specialist-body-114-120-hardcodes-per-language-coverage-command-matrix…`) foi corrigido exatamente assim em 2026-07-31; `mobile-developer` ficou para trás.
- **Proposta:** substituir `:149` por delegação — "If **no E2E framework** is detected → derive the scoped unit-test command from `skills/shared/scoped-test-execution/SKILL.md` § Runner Filters for the stack `stack-detection` resolved, and note the E2E gap" — e remover a enumeração de runners.
- **Impacto positivo:** elimina 1 de 2 restatements de matriz de comandos remanescentes nos agentes; cobertura de runners salta de 5 para 11 mais o override por script do projeto; a contradição interna `:149` vs. `:171` desaparece.
- **Impacto negativo / risco:** o agente passa a depender de um load adicional no caminho de fallback (~60 linhas de `scoped-test-execution`) e perde o atalho de ler o comando direto no corpo — em sessões onde a skill não foi carregada por `project-context`, o fallback fica sem comando até que ela seja lida.
- **Esforço:** Baixo

---

## MEDIUM

### Onze agentes têm seção `## Jira Integration` no corpo; a skill `linear` que o pacote embarca é alcançável a partir de um único agente

- **Fingerprint:** `agent-tracker-monoculture-jira-in-eleven-bodies-linear-reachable-from-one`
- **Alvo:** `agents/` (11 corpos com a seção)
- **Evidência:** `grep -rl '## Jira Integration' agents/` devolve **11** arquivos (`software-architect:187` · `technical-writer:169` · `code-reviewer:171` · `devops-specialist:180` · `backend-test-specialist:124` · `security-specialist:150` · `database-specialist:163` · `frontend-test-specialist:169` · `qa-specialist:186` · `mobile-developer:120` · `frontend-developer:162`). `rg -in 'linear' agents/ commands/` devolve **2 linhas**: `agents/product-analyst.md:177` (seção `## Issue Tracker Integration`) — "Load `skills/integrations/jira/SKILL.md` **or** `skills/integrations/linear/SKILL.md` when the project registers that tracker" — e a `description:` de `setup-assistant.md:3`. `skills/integrations/linear/SKILL.md:7-11` traz Detection própria (`LINEAR_API_KEY`, `ENG-123`, `INFRA-456`). Seis agentes prescrevem, em seção de comportamento, "Create the branch using the Jira naming pattern" (`frontend-developer:164` "Always create…", `mobile-developer:126`, `frontend-test-specialist:176`, `database-specialist:170`, `backend-test-specialist:131`, `devops-specialist:187`).
- **Problema:** o eixo exige agnosticismo de **plataforma**, e o tracker é plataforma. O harness embarca duas skills de tracker, mas só uma tem representação no corpo dos agentes: num projeto Linear, os coding agents não têm gatilho, não têm padrão de branch e não carregam `linear/SKILL.md` — enquanto `product-analyst` já demonstra a formulação neutra correta na mesma árvore.
- **Por que importa:** `skills/integrations/linear/SKILL.md` (3.338 bytes) é código morto para 10 dos 11 agentes que fazem trabalho de ticket, e `orphan-skill-scan.sh` **não a reporta** — a referência única em `product-analyst.md:177` satisfaz o check "Skills with no agent reference". A lacuna é estruturalmente invisível ao banco e aos gates.
- **Proposta:** renomear as 11 seções para `## Issue Tracker Integration` e trocar a Detection por roteamento neutro no modelo de `product-analyst.md:177` — "load the skill matching the tracker in use (`skills/integrations/jira/SKILL.md` or `skills/integrations/linear/SKILL.md`); take the branch naming pattern from that skill" —, movendo o padrão `{type}/{issueKey}` para dentro de cada skill.
- **Impacto positivo:** torna `linear` alcançável a partir de 11 agentes em vez de 1; remove 6 cópias do padrão de branch do corpo dos agentes; abre caminho para um terceiro tracker sem tocar em 11 arquivos.
- **Impacto negativo / risco:** a instrução fica um nível mais indireta (o agente precisa ler a skill para saber o formato da branch); e a mudança toca 11 agentes de uma vez, com risco de divergência de redação — o mesmo defeito que o fingerprint pai já registra.
- **Refina:** `agent-jira-detection-branch-naming-block-duplicated-no-canonical-home`
- **Esforço:** Médio

---

## LOW-MEDIUM

### A Foundational Rule do `seo-specialist` nomeia dois pacotes do ecossistema JS como referência de "o que o framework já provê"

- **Fingerprint:** `agent-seo-specialist-foundational-rule-names-next-seo-astro-seo`
- **Alvo:** `agents/seo-specialist.md`
- **Evidência:** `agents/seo-specialist.md:27` (seção `## Foundational Rule`, bullet obrigatório de "SEO-specific additions after project-context loads") — "Read `docs/development/tech-stack.md` to know what the framework already provides (built-in sitemap generation, `next-seo`, `astro-seo`, etc.) before proposing a new dependency".
- **Problema:** a única ilustração do que "o framework já provê" são dois pacotes npm de dois metaframeworks JS. Para um projeto WordPress (Yoast/RankMath), Laravel (`spatie/laravel-sitemap`), Django (`django.contrib.sitemaps`) ou Rails (`sitemap_generator`), a lista não oferece ancoragem — e é justamente a linha que decide se uma dependência nova será proposta.
- **Por que importa:** `seo-specialist` é auto-spawnado por `/devteam:frontend` e `/devteam:fullstack` (`frontend.md:21`, `fullstack.md:21-22`) em qualquer projeto que case um Detection Signal de site público, incluindo stacks server-rendered. A imprecisão enviesa a busca inicial para o ecossistema errado no único agente de 86 linhas que ainda não passou por revisão de agnosticismo.
- **Proposta:** trocar o parêntese por formulação neutra — "(built-in sitemap generation, a first-party or community SEO/meta package, canonical-tag helpers — whatever the stack already ships)".
- **Impacto positivo:** remove os 2 únicos nomes de produto do corpo do agente, deixando-o 100% agnóstico; alinha `seo-specialist` ao padrão já aplicado em `backend-developer` e `security-specialist`.
- **Impacto negativo / risco:** a instrução perde concretude — um exemplo nomeado ancora melhor a busca do que uma categoria abstrata, e em projetos Next/Astro (a maioria do público-alvo do agente) a versão atual acerta de primeira.
- **Esforço:** Baixo

---

## LOW

### O template de saída do `code-reviewer` — roteador declaradamente agnóstico — fixa `file.js` nos seis placeholders, inclusive no caminho Backend

- **Fingerprint:** `agent-code-reviewer-output-template-pins-file-js-six-placeholders`
- **Alvo:** `agents/code-reviewer.md`
- **Evidência:** `agents/code-reviewer.md:144,148,153,157,160,163` (seção `## Review Output Format`) — `file.js:42`, `file.js:88`, `file.js:33`, `file.js:15`, `file.js:67`, `file.js:12`; a mesma seção abre em `:136` com "State the adopted role on the first line, as the router instructs (`Review type: Backend` / `Review type: Frontend`)". O irmão `agents/backend-reviewer.md:166-186` (mesma seção) faz o oposto de propósito, rodando `file.go:42` · `file.php:88` · `file.py:33` · `file.rb:67` · `file.ts:15`.
- **Problema:** o template que o roteador deve emitir quando assume o papel `Backend` ilustra todas as seis categorias — incluindo Performance e Security — com extensão `.js`. Duas formulações do mesmo template coexistem na árvore, uma agnóstica por rotação e outra monolíngue, sem regra que as reconcilie.
- **Por que importa:** consequência funcional nula (são placeholders), mas é a superfície de saída de `/devteam:review`, e o contraste com `backend-reviewer.md` mostra que a rotação de extensões já é a convenção adotada no repo — o roteador é a exceção não intencional.
- **Proposta:** alinhar `code-reviewer.md:144-163` à rotação do `backend-reviewer`, ou neutralizar para `path/to/file:42` nos seis placeholders.
- **Impacto positivo:** elimina a última extensão de linguagem fixa no corpo do agente que roteia ambos os lados; convenção única de placeholder entre os três reviewers.
- **Impacto negativo / risco:** `frontend-reviewer.md:158-177` usa `Component.tsx`/`Form.tsx`/`Modal.tsx`, deliberadamente evocativos do domínio — padronizar os três exigiria decidir se a terceira variante também muda, ampliando um achado LOW para uma mudança em três arquivos já cobertos por outro fingerprint aberto.
- **Esforço:** Baixo

---

## Descartados por duplicação

| Candidato | Porta | Fingerprint colidente |
|---|---|---|
| `frontend-developer.md:3` (8 frameworks na `description`) | 5 (estado) | `agent-frontend-developer-description-frontmatter-enumerates-eight-frameworks-…` |
| `frontend-developer.md:91,96` (React `useState`, TanStack/SWR) | 5 (estado) | `agent-frontend-developer-body-92-102-data-fetching-section-hardcodes-…` |
| `frontend-developer.md:147` (`prefer reactive state`) | 5 (estado) | `agent-frontend-developer-testability-presumes-reactive-component-model` |
| `frontend-developer.md:72` (roteamento jQuery) | 3 (semântica, 3/3) | `agent-frontend-developer-testability-presumes-reactive-component-model` |
| `frontend-test-specialist.md:141-153` (jest/vitest + `sonar.javascript.lcov`) | 5 (estado) | `agent-frontend-test-specialist-sonarqube-coverage-block-hardcodes-jest-vitest-…` |
| `frontend-test-specialist.md:103` (React/Vue nas hook recipes) | 3 (semântica, 3/3) | `agent-frontend-test-specialist-107-122-hardcodes-react-renderhook-…` (✅) |
| `frontend-test-specialist.md:132` e `frontend-reviewer.md:122` (MSW) | 3 (semântica, 2/3) | `agent-unit-test-isolation-rule-mirrored-five-agents-no-canonical-home` |
| `frontend-reviewer.md:112,114` (PropTypes, `React.ChangeEvent`) | 5 (estado) | `agent-frontend-reviewer-body-type-safety-and-code-quality-hardcodes-react-ts-…` |
| `frontend-reviewer.md:158-177` (placeholders `.tsx` ×6) | 3 (semântica, 2/3) | `agent-frontend-reviewer-body-type-safety-and-code-quality-hardcodes-react-ts-…` |
| `database-specialist.md:84,154` (RLS como default neutro) | 5 (estado) | `agent-database-specialist-rls-as-engine-neutral-multitenant-default-and-gate` |
| `database-specialist.md:133` (`psql "$SUPABASE_DB_URL"`) | 5 (estado) | `agent-database-specialist-access-inlines-supabase-cli-while-delegating-others` |
| `database-specialist.md:27` (`docker-compose.yml` na Foundational Rule) | 3 (semântica, 2/3) | `agent-database-specialist-access-inlines-supabase-cli-while-delegating-others` |
| `devops-specialist.md:46-56` ("Primary: Docker") | 5 (estado) | `agent-devops-specialist-core-expertise-declares-primary-docker-…` |
| `devops-specialist.md:28,137-148,172` (Docker/Terraform no checklist) | 3 (semântica, 2/3) | `agent-devops-specialist-core-expertise-declares-primary-docker-…` |
| `security-specialist.md:79-85` (vocabulário GitHub Actions) | 5 (estado) | `agent-security-specialist-cicd-checklist-github-actions-only-vocabulary` |
| `backend-reviewer.md:30` (configs de linter, 4 ecossistemas) | 5 (estado) | `agent-reviewer-linter-config-three-divergent-ecosystem-incomplete-copies` |
| `mobile-developer.md:159` (checklist "React Native or Flutter") | 5 (estado) | registrado desde 2026-08-21 (`_index.md:602,649`) |
| `setup-assistant.md:146-147` (jest/pytest/phpunit) | 5 (estado) | registrado desde 2026-08-14 (`_index.md:345`) |
| `commands/commit.md:125-133` (matriz de lint npm/phpcs/ruff/mypy) | 5 (estado) | registrado desde 2026-08-21 (`_index.md:480`) |
| `commands/audit.md:54,126,128` (stack Docker, Redis/CDN) | 5 (estado) | `flow-audit-step2-unconditional-docker-stack-…` + `flow-audit-command-devops-analysis-prompt-names-redis-cdn-docker-…` |
| `commands/relayout.md:32` (Storybook/Tailwind) | 5 (estado) | `flow-relayout-design-discovery-names-storybook-tailwind` |
| `commands/mobile.md:19,26` (React Native/Expo/Flutter na linha de spawn) | 5 (estado) | `flow-mobile-command-spawn-line-enumerates-stacks-dropped-from-agent-description` |
| `commands/devops.md:2,14` (Docker na `description` e no spawn) | 3 (semântica, 2/3) | `agent-devops-specialist-core-expertise-declares-primary-docker-…` |
| `product-analyst.md:132-153` (gate Docker na decomposição) | 3 (semântica, 2/3) | `token-worktree-isolation-block-7-lines-x-8-agents` |
| Tabelas de detecção em `backend-developer.md:79,83,84` · `security-specialist.md:48,146` · `ui-ux-designer.md:57-59` · `mobile-developer.md:49-74,137-142` · `devops-specialist.md:70-82` · `database-specialist.md:56-73` · `frontend-developer.md:67-74` · `frontend-test-specialist.md:27` | — | Exceção explícita do eixo |
| `code-reviewer.md:79` · `adr.md:12` · `explain.md:63` | — | Blocos rotulados "Examples" — regra de descarte do eixo |
| `commit.md:36,40,45` · `merge.md:52,57` · `relayout.md:43` · `health-check.md:50` | — | Ferramenta do próprio harness (Docker por worktree, Python do instalador) |
| `explain.md:48` · `product-analyst.md:179` | — | Cláusulas anti-acoplamento |
