# Relatório - Agentes e Skills - 2026-05-14

**Data:** 2026-05-14 — Nona passada (9ª) — 10 sugestões originais

Foco do dia: outliers de tamanho persistentes (frontend-developer e ui-ux-designer empatados em 285 linhas), skills mobile gigantes sem references/, project-context com fanout massivo, gaps de adoção de interaction-patterns recém-criada, modelo Haiku ausente, gaps de tools (WebSearch).

---

### 🔴 1. `frontend-developer.md` 285 linhas — empatado com ui-ux-designer como maior agent (+42% sobre cap ~200)

**Fingerprint:** `agent-frontend-developer-285-lines-tied-largest-with-ui-ux-designer-after-extractions`

**Evidência:** Fact-finding §1.1 + §7.2: `agents/frontend-developer.md` = **285 linhas**, empatado com `ui-ux-designer.md` em 285. CLAUDE.md L137 declara: "Max ~200 lines per agent; move reference material to skills". Excedente: 85 linhas (+42%). Sub-escopo do antigo `agent-frontend-developer-size` (2026-05-06, ainda pendente).

**Por quê importa:** Frontend-developer é spawneado em `/devteam:frontend`, `/devteam:fullstack`, `/devteam:fix` (4 commands); cada linha custa por spawn. Architecture-awareness block é candidato natural à extração (vide cross-cutting #6 do fact-finding).

**Impacto positivo da correção:** Reduzir para ≤200 linhas economiza ~85 linhas × ~4 spawns/sessão = 340 linhas duplicadas eliminadas (~5.400 tokens).

**Impacto negativo / risco:** Extração pode quebrar contexto se reference skill não for autocontida.

**Sugestão concreta:** Extrair "Architecture Awareness" (~60 linhas) para `skills/shared/architecture-awareness/SKILL.md`, com load condicional em frontend-developer + backend-developer + mobile-developer (3 consumidores diretos).

---

### 🔴 2. `ui-ux-designer.md` 285 linhas sem nenhum padrão references/ aplicado

**Fingerprint:** `agent-ui-ux-designer-285-lines-no-references-pattern-yet-applied`

**Evidência:** Fact-finding §7.2: `agents/ui-ux-designer.md` = 285 linhas. Excede cap ~200 em 85 linhas (+42%). Spawneado em `/devteam:design`, `/devteam:frontend` (condicional), `/devteam:mobile` (condicional). Nenhuma extração para skills/ design realizada nas últimas 13 dias (commits `b8ece69`, `e83eb3b` extraíram devops/jira/monitoring, não design).

**Por quê importa:** Mesma magnitude de violação que frontend-developer, sem o mesmo nível de pendência histórica documentada. design e accessibility skills (`skills/design/`) têm 3 skills — espaço para receber blocos extraídos.

**Impacto positivo da correção:** Pareamento com #1 reduz dois maiores violators no mesmo PR.

**Impacto negativo / risco:** Design tem mais conteúdo prosa (princípios) que cabe inline; risco de extração causar split desnecessário.

**Sugestão concreta:** Identificar bloco "Design System Audit Workflow" (estimado 40-60 linhas via padrão observado em outros agents) e mover para `skills/design/design-system-audit/` (skill já existe — fact-finding §1.4).

---

### 🟡 3. `skills/mobile/flutter/SKILL.md` 292 linhas — maior skill do repo, sem extração references/

**Fingerprint:** `skill-mobile-flutter-292-lines-largest-skill-no-references-extraction`

**Evidência:** Fact-finding §7.1: `skills/mobile/flutter/SKILL.md` = **292 linhas** (maior skill do repo). Lista de 8 skills com `references/` (fact-finding §1.4) **não inclui** mobile/flutter. Carregada por `agents/mobile-developer.md` (1 referência — fact-finding §6.3).

**Por quê importa:** Eager-load de 292 linhas sempre que mobile-developer spawneia, mesmo em projeto React Native ou nativo iOS. Token waste massivo (~4.700 tokens/spawn).

**Impacto positivo da correção:** Extrair em `references/{widgets, navigation, state-management}.md` reduz core para ~80 linhas; resto loadeia condicional.

**Impacto negativo / risco:** Fragmentação demais pode dificultar lookup; manter sumário denso no SKILL.md.

**Sugestão concreta:** Aplicar padrão proven (commit `b8ece69` em monitoring) em flutter/: criar `references/widgets.md`, `references/navigation.md`, `references/state-management.md`; SKILL.md mantém detection rules + load triggers.

---

### 🟡 4. `skills/mobile/react-native/SKILL.md` 264 linhas — mesmo padrão, sem extração

**Fingerprint:** `skill-mobile-react-native-264-lines-no-references-extraction`

**Evidência:** Fact-finding §7.1: `skills/mobile/react-native/SKILL.md` = **264 linhas**. Carregada por mobile-developer (1 ref — §6.3). Empareada com flutter como segundo maior skill mobile sem extraction.

**Por quê importa:** Mesmo problema do #3 com magnitude similar. Mobile-developer carrega ambas eagerly = 556 linhas (~8.900 tokens) só para detectar plataforma.

**Impacto positivo da correção:** Extração paralela ao #3 reduz footprint de mobile-developer significativamente.

**Impacto negativo / risco:** Idem #3.

**Sugestão concreta:** `references/{navigation, state-management, expo-vs-bare}.md`; manter platform-detection no SKILL.md core.

---

### 🔴 5. `skills/shared/project-context/SKILL.md` 291 linhas × 14 agents — fanout massivo

**Fingerprint:** `skill-shared-project-context-291-lines-loaded-by-14-agents`

**Evidência:** Fact-finding §6.1 + §7.1: `project-context` = **291 linhas**, carregada por **14 agents** (Top 5 most-loaded). Sem `references/` extraction (fact-finding §1.4 lista 8 skills com references; project-context não está).

**Por quê importa:** 291 × 14 = 4.074 linhas de project-context replicado em sessão multi-agent ampla. Estimativa: ~65.000 tokens por sessão completa só nesta skill (vide report 04 #2 para quantificação detalhada).

**Impacto positivo da correção:** Maior aggregate cost identificado no audit; extraction pode liberar 30-40% (~20.000 tokens).

**Impacto negativo / risco:** Skill é foundational; mudar layout requer atualização nos 14 agents.

**Sugestão concreta:** Extrair "Contradiction Guard" (estimado 50 linhas) e "Wiki Knowledge Base" (estimado 40 linhas) para `references/{contradiction-guard, wiki}.md`; SKILL.md mantém core + load triggers.

---

### 🟡 6. `skills/integrations/kong/SKILL.md` 277 linhas, loaded por 1 agente, sem references/

**Fingerprint:** `skill-integrations-kong-277-lines-loaded-by-only-one-agent-no-references`

**Evidência:** Fact-finding §7.1: kong = 277 linhas. §6.3 (sample): integrações tipicamente loaded por 1 agent. CLAUDE.md authoring rule: "Max ~500 lines; move long reference material to references/" — kong está em 55% do limite mas ainda é candidato natural.

**Por quê importa:** Eager-load de 277 linhas para todos os spawns de software-architect ou backend-developer (consumidores prováveis), mesmo quando projeto não usa Kong.

**Impacto positivo da correção:** Extrair plugins/auth/rate-limiting reduz SKILL.md core para ~80 linhas + load on-detect.

**Impacto negativo / risco:** Premature optimization se kong já é loaded condicionalmente; verificar consumer.

**Sugestão concreta:** Mover `plugins/`, `consumers/`, `routes-services/` para references/; SKILL.md core descreve apenas detection (presence of `kong.yml`, `kong.conf`).

---

### 🟡 7. `skills/shared/setup-health-check/SKILL.md` 261 linhas sem references/ apesar de extração prévia

**Fingerprint:** `skill-shared-setup-health-check-261-lines-no-references`

**Evidência:** Fact-finding §7.1: `skills/shared/setup-health-check/SKILL.md` = 261 linhas. Skill foi extraída do setup-assistant em passes anteriores (memorial: setup-assistant caiu de 404 → 226 linhas em parte por health-check ter virado skill própria). Apesar de já ser uma extração, mantém-se monolítica.

**Por quê importa:** Skill grande consumida por setup-assistant; cada `/devteam:setup` (FIRST_RUN ou subsequente) carrega 261 linhas.

**Impacto positivo da correção:** Sub-extrair em `references/{checks-list, fix-patterns, audit-format}.md` libera SKILL.md para descrever apenas o flow.

**Impacto negativo / risco:** Skill é orquestradora; muito split dilui legibilidade.

**Sugestão concreta:** Identificar bloco "Health Check Patterns" e "Audit Output Format" (provavelmente ~60-80 linhas combinadas) para references/; SKILL.md core fica em ~150 linhas.

---

### 🟡 8. `interaction-patterns` 185 linhas mas zero retrofit em agents existentes

**Fingerprint:** `skill-shared-interaction-patterns-185-lines-but-zero-yes-no-prompt-fixers-applied-to-existing-agents`

**Evidência:** Fact-finding §9: skill criada hoje (commit `d05242a`); apenas `commands/update.md` carrega (commit `ba19882`). Verificação cruzada com fact-finding sample: setup-assistant, agents coding com worktree question — todos ainda usam padrões legados (`(yes / no)` ou prompts inline). 0 retrofits efetivos.

**Por quê importa:** Skill mandatória que ninguém adota é dead-load. Multiplica problema do report 01 #6 e report 02 #1 — sem incentivo (lint) e sem exemplo (retrofits), regra fica letra morta.

**Impacto positivo da correção:** Pareado com lint do report 02 #1 + adoção em 2-3 agents-modelo, retrofit automático passa a fluir.

**Impacto negativo / risco:** Refactor coordenado entre agents pode introduzir regressão de UX.

**Sugestão concreta:** Pilotar retrofit em `agents/setup-assistant.md` (Opus, com 8+ prompts identificáveis); usar como referência canônica em `interaction-patterns/SKILL.md` ("Real example: setup-assistant.md").

---

### 🟡 9. Sem agente Haiku — gap entre regra CLAUDE.md e implementação

**Fingerprint:** `agent-no-haiku-agent-despite-claude-md-recommendation-for-structured-output`

**Evidência:** CLAUDE.md L120: "Model assignment: claude-opus-4-7 (decision-making), claude-sonnet-4-6 (execution), claude-haiku-4-5-20251001 (structured output)". Fact-finding §5.1: 4 Opus + 13 Sonnet + **0 Haiku**. Pareado com report 01 #4.

**Por quê importa:** Sob ângulo de catálogo de agents (vs ângulo de drift documental do report 01), a ausência indica que talvez a categoria "structured output" seja artificial — nenhum agent natural caiu nela.

**Impacto positivo da correção:** Decisão consciente: ou criar `release-formatter` / `commit-message-formatter` com Haiku, ou simplificar regra CLAUDE.md para 2 modelos.

**Impacto negativo / risco:** Criar agent só para usar Haiku é gold-plating; remover Haiku da regra é mudança de scope.

**Sugestão concreta:** Avaliar candidatos reais: (a) novo agent `commit-msg-suggester` que recebe diff e sugere CC message (Haiku perfect-fit); (b) extrair sub-task de `technical-writer` para Haiku via Task tool. Documentar decisão em ADR.

---

### 🟢 10. WebSearch ausente em setup-assistant e security-specialist (e WebFetch ausente em todos)

**Fingerprint:** `agent-tool-set-with-websearch-only-in-2-agents-but-product-analyst-and-software-architect-loaded-skills-suggest-others-need-it`

**Evidência:** Fact-finding §5.2: WebSearch declarado em 2 agents — `product-analyst` e `software-architect`. `security-specialist` (Opus, 234 linhas) faz lookups CVE/OWASP frequentes. `setup-assistant` (Opus, 226 linhas) faz tracker MCP detection (Jira/Linear/etc.) que beneficiaria de research. Pareado com pendente `agent-architect-frontmatter-no-webfetch-but-loaded-skills-suggest-research` (2026-05-13).

**Por quê importa:** Sem WebSearch, agentes Opus dependem de instruções inline ou docs estáticas; valor de modelo top é subutilizado.

**Impacto positivo da correção:** security-specialist consulta NVD, CVE em real-time; setup-assistant verifica versões de tools.

**Impacto negativo / risco:** WebSearch tem custo per-query e latência adicional (~2-5s).

**Sugestão concreta:** Adicionar WebSearch a `security-specialist` (alta prioridade — auditoria contemporânea exige) e `setup-assistant` (média prioridade); avaliar WebFetch em `software-architect` para leitura full de RFCs/specs.

---

## Síntese — ordem de prioridade

1. **🔴 #5** — `skill-shared-project-context-291-lines-loaded-by-14-agents` (maior aggregate cost)
2. **🔴 #1** — `agent-frontend-developer-285-lines-tied-largest-with-ui-ux-designer-after-extractions`
3. **🔴 #2** — `agent-ui-ux-designer-285-lines-no-references-pattern-yet-applied`
4. **🟡 #3** — `skill-mobile-flutter-292-lines-largest-skill-no-references-extraction`
5. **🟡 #4** — `skill-mobile-react-native-264-lines-no-references-extraction`
6. **🟡 #8** — `skill-shared-interaction-patterns-185-lines-but-zero-yes-no-prompt-fixers-applied-to-existing-agents`
7. **🟡 #6** — `skill-integrations-kong-277-lines-loaded-by-only-one-agent-no-references`
8. **🟡 #7** — `skill-shared-setup-health-check-261-lines-no-references`
9. **🟡 #9** — `agent-no-haiku-agent-despite-claude-md-recommendation-for-structured-output`
10. **🟢 #10** — `agent-tool-set-with-websearch-only-in-2-agents-but-product-analyst-and-software-architect-loaded-skills-suggest-others-need-it`
