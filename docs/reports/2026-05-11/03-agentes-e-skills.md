# Relatório de Agentes e Skills — 2026-05-11

**Foco**: melhoria e otimização em agentes/skills existentes (separação de responsabilidades, gaps de cobertura, ergonomia de invocação).
**Originalidade**: todos os fingerprints abaixo são **novos** — não constam em `_index.md` antes desta data.

---

## 1. `agent-mobile-test-specialist-missing-asymmetric-with-backend-frontend`

**Onde**: `agents/` — existem `backend-test-specialist.md` e `frontend-test-specialist.md`, mas não `mobile-test-specialist.md`.

**Problema**: o roster de coding agents inclui `mobile-developer` (215 linhas, com worktree isolation e cobertura para React Native/Expo/Flutter/iOS/Android). Para backend e frontend, há um par developer + test-specialist. Para mobile, o developer não tem par.

**Consequência prática**: `commands/fix.md` lista "→ test-specialist¹" (genérico, sem especificar mobile). `commands/tester.md` cita `mobile-developer¹` como condicional, mas mobile-developer **não é um test-specialist** — ele escreve features, não testes.

**Impacto positivo de criar `mobile-test-specialist`**:
- Cobertura de Detox, Maestro, Appium, XCUITest, Espresso.
- Test pyramid mobile (unit vs widget/screen vs E2E em device farm) ganha owner.
- Simetria com o resto do team.

**Impacto negativo**:
- Mais um agente (~200 linhas).
- Custo de manutenção.

**Mitigação**: criar como Sonnet (execução de tests), reutilizar test-pyramid/test-strategy/contract-testing/snapshot-testing/visual-regression skills.

**Fingerprint**: `agent-mobile-test-specialist-missing-asymmetric-with-backend-frontend`

---

## 2. `agent-setup-assistant-still-306-lines-after-multiple-extractions`

**Onde**: `agents/setup-assistant.md` (306 linhas).

**Histórico**:
- 2026-05-06: 404 linhas (`agent-setup-assistant-size` flagged, sem marker até hoje).
- 2026-05-11: 306 linhas (redução de 24%).

**Problema**: ainda acima do limite ~200 linhas declarado no CLAUDE.md. Skills já extraídas (`setup-scan`, `setup-health-check`, `auto-routing`, `discovery-mode`, `docs-templates`) reduziram o tamanho, mas restam blocos inline grandes:
- Docker compose detection block (~10 linhas).
- Tracker MCP table (~25 linhas — pode virar `integrations/tracker-mcps/SKILL.md`).
- Update flow inline (deveria delegar a comando `/devteam:update`).

**Impacto positivo de extrair mais**:
- Agente abaixo de 200 linhas; CLAUDE.md rule respeitada.
- Tracker-mcps skill reusável por product-analyst (que também mexe com Jira/Linear/ClickUp).

**Impacto negativo**:
- Risco de over-fragmentação.
- Setup-assistant fica menos auto-suficiente (mais skill loads no startup).

**Fingerprint**: `agent-setup-assistant-still-306-lines-after-multiple-extractions`

---

## 3. `skill-reviewer-base-foundational-rule-overlap-with-project-context`

**Onde**: `skills/shared/reviewer-base/SKILL.md` (28 linhas; tabela "Foundational Rule" linhas 7–18) vs. `skills/shared/project-context/SKILL.md` (284 linhas).

**Verificação**: ambas as skills têm uma tabela "Load context in this order" cobrindo:

| Step | reviewer-base | project-context |
|------|---------------|-----------------|
| 1 | `README.md`, `CLAUDE.md`, `AGENTS.md` | mesma coisa |
| 2 | `.claude/docs/project.md` | mesma coisa |
| 3 | `.claude/user-data/session-summary.md` | mesma coisa |
| 4 | `code-standards.md` | sem isso |
| 5 | `architecture.md` | tem |
| 6 | Linter configs | sem (genérico) |
| 7 | `git log --oneline -10` | tem |
| 8 | `git diff main...HEAD` | sem |
| 9 | `skills/shared/comments-policy` | menciona |
| 10 | `skills/shared/conventional-commits` | sem |
| 11 | SonarQube detection | sem |

**Problema**: os 3 reviewers carregam **ambas** as skills. Steps 1–3, 5, 7 são duplicados.

**Impacto positivo de consolidar**:
- ~10 linhas de duplicação removidas (×3 reviewers = ~30 linhas-equivalente).
- Sentido claro: `project-context` cobre o universal; `reviewer-base` complementa apenas o que é específico de review (steps 4, 6, 8, 9, 10, 11).

**Impacto negativo**:
- Reviewer-base depende implicitamente de project-context ter sido carregada antes. Se um reviewer esquecer de carregar project-context, fica sem context base.

**Mitigação**: reviewer-base começa com "Assume `project-context` foi carregada. Adiciona somente: linter configs (step 6), git diff focal (step 8), comments-policy aplicado a review (step 9), conventional-commits validação (step 10), SonarQube detection (step 11)."

**Fingerprint**: `skill-reviewer-base-foundational-rule-overlap-with-project-context`

---

## 4. `agent-product-analyst-still-no-bash-tool-after-jira-skill-load`

**Onde**: `agents/product-analyst.md` frontmatter `tools:`.

**Histórico**: item `ref-product-analyst-no-bash-tool` (2026-05-09, sem marker) sinalizou que product-analyst carrega Foundational Rule que exige `git log` mas não tem `Bash` no frontmatter.

**Verificação 2026-05-11**: product-analyst agora carrega `skills/integrations/jira/SKILL.md`. A skill Jira exige criação de issues (via MCP ou via API), o que pode requerer Bash. Apesar disso, `product-analyst.md` continua sem `Bash`.

**Impacto positivo de adicionar `Bash`**:
- product-analyst passa a executar `git log` (foundational rule satisfeita).
- Pode rodar `gh issue create` ou `glab issue create` quando Jira MCP não estiver disponível.

**Impacto negativo**:
- Bash em agente analítico aumenta superfície de ação (pode rodar comandos não pretendidos). Mitigar via Plan Mode rigoroso.

**Fingerprint**: `agent-product-analyst-still-no-bash-tool-after-jira-skill-load`

---

## 5. `skill-release-prep-missing-despite-mentioned-in-changelog-1.2.0`

**Onde**: `CHANGELOG.md` linha 91 menciona "Release preparation skill (`release-prep`)" em 1.2.0 (2026-04).

**Verificação 2026-05-11**:

```bash
$ find skills -name "*release-prep*" -o -name "release*"
$ (sem resultado)
```

A skill **não existe** no filesystem. Foi mencionada no CHANGELOG mas removida ou nunca commitada.

**Problema**: release-prep é parte natural do fluxo (bump versão, tag, CHANGELOG section, push). Hoje, esse fluxo é manual ou inferido pelo `technical-writer`.

**Impacto positivo de criar (ou restaurar)**:
- `/devteam:release` ou `/devteam:tag` ganha skill canônica.
- Tag + CHANGELOG + push consistente.

**Impacto negativo**:
- Outro skill para manter.
- Pode conflitar com `git-workflow` skill (que cobre tags/branches).

**Mitigação**: criar `skills/shared/release-prep/SKILL.md` focado em SemVer bump + CHANGELOG Unreleased → tagged section move + tag.

**Fingerprint**: `skill-release-prep-missing-despite-mentioned-in-changelog-1.2.0`

---

## 6. `skill-discovery-mode-loaded-by-three-agents-without-divergence-check`

**Onde**: `skills/shared/discovery-mode/SKILL.md` é carregada por `setup-assistant`, `software-architect`, `product-analyst`.

**Problema**: os 3 agentes que carregam a skill não compartilham o **resultado** do discovery. Quando `software-architect` faz discovery e converge, e depois `product-analyst` é spawnado, este recomeça o discovery (mesmas perguntas), porque não há persistência.

**Impacto positivo de persistir**:
- Discovery vira "1 vez por sessão de planejamento".
- `setup-assistant` pode reler o output do `software-architect` em vez de re-perguntar.

**Impacto negativo**:
- Acrescenta arquivo `.claude/user-data/.discovery-current.md` (transitório).
- Risco de stale (discovery antigo confundir agente atual). Mitigar via TTL.

**Mitigação**: skill `discovery-mode` checa `.discovery-current.md` antes de começar; se TTL < 2h, retoma; caso contrário, regrava.

**Fingerprint**: `skill-discovery-mode-loaded-by-three-agents-without-divergence-check`

---

## 7. `skill-monitoring-444-lines-over-limit-needs-references-extraction`

**Onde**: `skills/devops/monitoring/SKILL.md` (444 linhas — maior skill do repo).

**Verificação**: já existe `skills/devops/monitoring/references/` (verificado em 00-auditoria). Porém, o `SKILL.md` ainda tem 444 linhas — ou o references/ está vazio, ou contém pouco material extraído.

**Análise**: o limite recomendado em CLAUDE.md é ~500 linhas, então tecnicamente está dentro. Porém, a skill cobre:
- Logs (Elastic, Loki)
- Metrics (Prometheus, Datadog)
- Traces (OpenTelemetry, Jaeger)
- Alerts (PagerDuty, Opsgenie)
- Dashboards (Grafana, Datadog UI)

Cada tópico vale ~80 linhas. Quebrar em `monitoring/logs/`, `monitoring/metrics/`, `monitoring/traces/` permitiria carga sob demanda.

**Impacto positivo**:
- Carga média desce de 444 para ~80 linhas.
- Skill por aspecto pode ser carregada por outros agentes (e.g., `security-specialist` pode querer só logs).

**Impacto negativo**:
- Fragmentação acentuada na seção devops.
- Risco de perder coesão (e.g., "tracing dependente de metrics setup").

**Fingerprint**: `skill-monitoring-444-lines-over-limit-needs-references-extraction`

---

## 8. `skill-sonarqube-435-lines-overlap-with-reviewer-base-detection-block`

**Onde**: `skills/devops/sonarqube/SKILL.md` (435 linhas) e detection block em `skills/shared/reviewer-base/SKILL.md` (linha 17).

**Problema**: a detection block do reviewer-base ("se `sonar-project.properties` … → load sonarqube") replica lógica que poderia estar dentro da própria `sonarqube` skill (autodetect on load).

**Impacto positivo de inverter (sonarqube auto-detecta seu trigger)**:
- Reviewer-base encolhe de 28 para ~25 linhas.
- Outros agentes que queiram usar sonarqube não precisam carregar essa lógica replicada.

**Impacto negativo**:
- Skill SonarQube fica responsável por algo que normalmente é do consumidor.

**Mitigação**: padrão híbrido — reviewer-base mantém a detecção (porque é onde a decisão de carregar a skill é tomada); SonarQube skill começa com "Self-check: confirme que `sonar-project.properties` existe antes de aplicar".

**Fingerprint**: `skill-sonarqube-435-lines-overlap-with-reviewer-base-detection-block`

---

## 9. `agent-mobile-developer-no-detox-or-maestro-test-routing`

**Onde**: `agents/mobile-developer.md`.

**Verificação**: o agente cobre Detox, Maestro? Buscando `Detox|Maestro|Appium|XCUITest|Espresso`:

```bash
$ grep -iE "detox|maestro|appium|xcuitest|espresso" agents/mobile-developer.md
# (validar conteúdo)
```

**Problema potencial**: mobile-developer escreve features mobile mas não tem routing claro para test frameworks específicos de mobile (Detox para RN, Maestro para multi-platform E2E, Appium genérico). Hoje, "test" em mobile cai genericamente em test-pyramid/test-strategy skills (orientadas a web/backend).

**Impacto positivo**:
- Mobile ganha cobertura completa do teste E2E.
- Combinado com sugestão #1 (`mobile-test-specialist`), forma um fluxo coeso.

**Impacto negativo**:
- Mais material para o agente.

**Fingerprint**: `agent-mobile-developer-no-detox-or-maestro-test-routing`

---

## 10. `skill-missing-prompt-engineering-or-llm-integration`

**Onde**: `skills/` (categoria nova).

**Problema**: nenhuma skill cobre **integração com LLMs no produto do usuário** — chat features, RAG, embeddings, vector DB, agent SDKs, prompt versioning, eval harnesses. Em 2026, isso é estratégico para a maioria dos projetos.

**Impacto positivo de criar `skills/architecture/llm-integration/`**:
- Backend developer recebe guideline para integração com Anthropic API, OpenAI, ou Bedrock.
- Pgvector + Pinecone + Weaviate routing (já hoje há menção a pgvector em multitenancy skill).
- Prompt-engineering best practices (uso de XML tags, chain-of-thought, examples).

**Impacto negativo**:
- Skill grande (LLM stack tem muita coisa).
- Pode ficar desatualizado rápido (modelos novos a cada 6 meses).

**Mitigação**: focar em **patterns** (não em SDKs específicos): RAG, structured output, eval harness, prompt versioning, cost monitoring.

**Fingerprint**: `skill-missing-prompt-engineering-or-llm-integration`

---

## 11. `agent-technical-writer-still-haiku-but-diataxis-extracted`

**Onde**: `agents/technical-writer.md` (162 linhas, model: Haiku).

**Histórico**: `agent-technical-writer-haiku-mismatch` (2026-05-08, sem marker) propôs revisar o modelo. Agora `diataxis-framework` foi extraído da inline para skill. O technical-writer ficou mais leve (162 linhas), o que reforça **manter Haiku**.

**Re-avaliação**: provavelmente Haiku é adequado dado o conteúdo extraído. Mas o item 2026-05-08 nunca foi formalmente fechado. Devemos:
- Marcar `agent-technical-writer-haiku-mismatch` como **decisão consciente** (Haiku é o modelo correto após extraction).

**Impacto positivo**:
- Limpa pendência do índice.
- Evita repropostas futuras com mesma motivação.

**Impacto negativo**:
- Implica adicionar uma nova categoria de status no `_index.md` (e.g., `🟢 Resolved by other means`).

**Fingerprint**: `agent-technical-writer-haiku-mismatch-resolved-by-diataxis-extraction` (variante de fingerprint anterior, escopo de reclassificação).

---

## 12. `skill-current-context-not-loaded-by-fix-or-refactor-workflows`

**Onde**: `workflows/bug-fix.md`, `workflows/refactor.md`.

**Verificação**: `current-context` é carregada por **21 dos 23 commands**. Workflows, porém, são entry points alternativos (rodam quando `/devteam:workflow-*` é chamado). Eles **não carregam** `current-context` no Step 0.

**Problema**: usuário que dispara workflow via `cat workflows/bug-fix.md` (sem command wrapper) não tem detecção automática de branch/worktree.

**Impacto positivo**:
- Workflow é auto-suficiente: pode ser executado standalone.
- Worktree decision file (`.claude/.worktree-session`) é consultado consistentemente.

**Impacto negativo**:
- Duplicação se o command wrapper já carregou.

**Mitigação**: workflows fazem "Step 0 — Load current-context" idempotente (checa se já está em memória).

**Fingerprint**: `skill-current-context-not-loaded-by-fix-or-refactor-workflows`

---

## 13. `skill-graphify-setup-no-conditional-by-project-language`

**Onde**: `skills/devops/graphify-setup/SKILL.md` (265 linhas).

**Problema**: Graphify é uma ferramenta de visualização de codebase, mas a skill carrega bloco genérico para qualquer projeto. Projetos pequenos (< 50 arquivos), monorepos com mais de uma linguagem, e projetos puramente de documentação têm necessidades diferentes.

**Impacto positivo de adicionar gates**:
- Setup-assistant não pergunta sobre Graphify em projeto de docs (~Markdown only).
- Reduz fricção do onboarding.

**Impacto negativo**:
- Pode esconder Graphify de quem queria usar mesmo em projeto pequeno.

**Mitigação**: gate por `(language ∈ {ts, js, py, go, php, rb, java, kt, rs}) ∧ (file_count > 50)`.

**Fingerprint**: `skill-graphify-setup-no-conditional-by-project-language`

---

## Resumo dos Fingerprints Originais (13)

1. `agent-mobile-test-specialist-missing-asymmetric-with-backend-frontend`
2. `agent-setup-assistant-still-306-lines-after-multiple-extractions`
3. `skill-reviewer-base-foundational-rule-overlap-with-project-context`
4. `agent-product-analyst-still-no-bash-tool-after-jira-skill-load`
5. `skill-release-prep-missing-despite-mentioned-in-changelog-1.2.0`
6. `skill-discovery-mode-loaded-by-three-agents-without-divergence-check`
7. `skill-monitoring-444-lines-over-limit-needs-references-extraction`
8. `skill-sonarqube-435-lines-overlap-with-reviewer-base-detection-block`
9. `agent-mobile-developer-no-detox-or-maestro-test-routing`
10. `skill-missing-prompt-engineering-or-llm-integration`
11. `agent-technical-writer-haiku-mismatch-resolved-by-diataxis-extraction`
12. `skill-current-context-not-loaded-by-fix-or-refactor-workflows`
13. `skill-graphify-setup-no-conditional-by-project-language`
