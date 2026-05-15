# Relatório - Economia de Tokens - 2026-05-14

**Data:** 2026-05-14 — Nona passada (9ª) — 10 sugestões originais

Foco do dia: quantificação atualizada das pendências (CLAUDE.md cresceu para 557, project-context fanout massivo, _index.md ritmo de crescimento), novas oportunidades de economia em mobile skills loaded eagerly, recomendações com economia em tokens estimada por linha × refs × 16 tokens/linha.

---

### 🔴 1. CLAUDE.md cresceu para 557 linhas — replicação multi-spawn ~62.400 tokens

**Fingerprint:** `token-claude-md-557-lines-loaded-7-times-per-multi-agent-session-26-700-tokens`

**Evidência:** Sub-escopo quantificado de `token-claude-md-grew-to-544-lines-loaded-every-session-largest-monolith` (2026-05-13). Fact-finding §7: `wc -l CLAUDE.md` = 557 linhas. Multi-agent session típica spawneia ~7 agents (`/devteam:plan` ou `/devteam:fullstack`). 557 × 7 × 16 tokens/linha = **62.384 tokens replicados/sessão**.

**Por quê importa:** Maior monolítico do repo, growth pace +13 linhas em 24h. Cada novo feature adiciona ~10 linhas em CLAUDE.md → ~1.120 tokens/sessão de overhead permanente.

**Impacto positivo:** Fragmentação em 3 fases (overview/auth-rules/operations) reduz por spawn para apenas seção relevante; economia estimada **~45.000 tokens/sessão** (~70%).

**Impacto negativo / risco:** Refactor massivo; risco de perder contexto cross-section.

**Sugestão concreta:** Ver proposta de fragmentação em report 01 #3; preparar PoC com `.claude-md/` modular e load on-demand.

---

### 🔴 2. `project-context` 291 linhas × 14 agents = ~65.184 tokens replicados (maior aggregate cost)

**Fingerprint:** `token-skill-project-context-291-lines-x-14-agents-65-184-tokens-eager-load`

**Evidência:** Fact-finding §6.1 + §7.1: 291 linhas × 14 agents × 16 tokens/linha = **65.184 tokens** se todos os 14 agents forem spawneados na sessão (worst-case `/devteam:plan` + `/devteam:fullstack`). Em sessão típica de 7 spawns: 291 × 7 × 16 = **32.592 tokens**.

**Por quê importa:** Single largest token-cost identificado em todo o audit acumulado de 9 dias. project-context é foundational mas o tamanho cresce sem extração.

**Impacto positivo:** Extrair Contradiction Guard + Wiki blocks (~90 linhas) reduz para ~200 linhas core × 14 = 44.800 tokens; **economia ~20.000 tokens/sessão multi-agent ampla**.

**Impacto negativo / risco:** Extração precisa preservar order-of-operations (Foundational Rule depende de project-context).

**Sugestão concreta:** Idem report 03 #5 — extrair em `references/{contradiction-guard, wiki}.md`.

---

### 🟡 3. `mobile/flutter/SKILL.md` 292 linhas eager-loaded sem stack-detection gate

**Fingerprint:** `token-mobile-flutter-292-lines-loaded-eagerly-by-mobile-developer-without-stack-detection-gate`

**Evidência:** Fact-finding §7.1: 292 linhas. §6.3: loaded por `mobile-developer.md` (1 ref). Sem evidência de gate condicional `if pubspec.yaml exists` no agent body. Custo: 292 × 16 = **4.672 tokens** sempre que mobile-developer spawneia.

**Por quê importa:** Em projeto React Native (não Flutter), 4.672 tokens são overhead 100%. Mobile cross-platform é minoria; precisa de gate.

**Impacto positivo:** Lazy-load com gate `[ -f pubspec.yaml ]` economiza **4.672 tokens/spawn em projetos não-Flutter** (estimado: 70% dos projetos mobile).

**Impacto negativo / risco:** Detection se errar leva a falta de skill quando necessário; mitigar com heurística adicional `*.dart` files.

**Sugestão concreta:** Em `agents/mobile-developer.md`, mover load de flutter para bloco condicional: `If detected (pubspec.yaml OR *.dart): Load skills/mobile/flutter/SKILL.md`.

---

### 🟡 4. `mobile/react-native/SKILL.md` 264 linhas — mesmo eager-load issue

**Fingerprint:** `token-mobile-react-native-264-lines-same-eager-load-issue`

**Evidência:** Fact-finding §7.1: 264 linhas. Loaded por mobile-developer. Custo: 264 × 16 = **4.224 tokens/spawn**. Pareado com flutter — mobile-developer carrega ambas (8.896 tokens combinados) só para descobrir plataforma.

**Por quê importa:** Mobile-developer é spawneado em `/devteam:mobile`, `/devteam:fullstack`¹, `/devteam:fix`¹ (vide drift report 01 #1). Custo se replica.

**Impacto positivo:** Gate condicional economiza **8.896 tokens** quando ambas não se aplicam (projeto nativo iOS/Android puro).

**Impacto negativo / risco:** Detection precisa cobrir `package.json` com `react-native` dep + `App.tsx`/`index.js` patterns.

**Sugestão concreta:** Mover load de react-native para condicional similar ao #3: `If detected (package.json with "react-native" dep OR app.json with expo): Load skills/mobile/react-native/SKILL.md`.

---

### 🟡 5. Verificar se `monitoring/references/*` é loaded lazily ou eagerly pós-extração

**Fingerprint:** `token-skill-monitoring-extracted-but-references-files-may-be-loaded-eagerly`

**Evidência:** Commit `b8ece69` (2026-05-13) extraiu monitoring para references/ (5 arquivos: cloudwatch, datadog, loki-config, prometheus-alerts, prometheus-grafana). Fact-finding §1.4 confirma 5 references. Não verificado se `monitoring/SKILL.md` core lista os references como "load if needed" (lazy) ou se algum agent carrega eagerly.

**Por quê importa:** O ganho da extração só se materializa com lazy-load. Se devops-specialist carrega `monitoring/SKILL.md` + 5 references no startup, soma original (~444 linhas) é mantida.

**Impacto positivo:** Confirmação de lazy-load fecha o ganho; eager-load detectado = oportunidade de re-engineering.

**Impacto negativo / risco:** Depende de inspeção manual.

**Sugestão concreta:** Auditar `agents/devops-specialist.md` em busca de loads condicionais (`if [ -f prometheus.yml ]`, `if [ -f datadog.yaml ]`); medir antes/depois com line count após extração para confirmar o ganho dos 376 linhas reportados.

---

### 🟢 6. `interaction-patterns` 185 linhas — oportunidade de instituir lazy-load desde o início

**Fingerprint:** `token-interaction-patterns-185-lines-loaded-by-update-md-but-no-agent-uses-conditional-load-yet`

**Evidência:** Fact-finding §9: skill criada hoje, 185 linhas, loaded por 1 command (`update.md`). Custo atual: 185 × 16 = **2.960 tokens/sessão de update**. Conforme adoção propaga para 28 commands + 17 agents (vide report 01 #6), custo cresceria para ~3.100 spawns × 2.960 = milhões de tokens/dia agregados.

**Por quê importa:** Janela de oportunidade — instituir lazy-load PADRÃO desde a primeira propagação evita tech debt similar à comments-policy (vide pendente `token-comments-policy-91-lines-still-eager-loaded-by-9-agents`).

**Impacto positivo:** Skill loaded only quando "agent precisa fazer prompt complexo" (heurística: `if asking finite-set question`); economia escala com adoção.

**Impacto negativo / risco:** Lazy-load requer determinação ahead-of-time se prompt será feito; pode falhar em fluxos dinâmicos.

**Sugestão concreta:** Documentar em `interaction-patterns/SKILL.md` "Loading pattern: lazy — load only when agent reaches a decision point with finite options"; instruir adoção via `When loaded` block padronizado.

---

### 🟡 7. `_index.md` em ~408 linhas — pace 42 linhas/dia, rotação 90d virá em 1.500+ linhas

**Fingerprint:** `token-fingerprint-index-_index-md-380-lines-not-rotated-yet-rotation-policy-says-90d-current-pace-30d`

**Evidência:** Header CLAUDE.md / _index.md (linha 19): "rotacionado a cada 90 dias movendo entradas antigas para `_index-archive-YYYY-Q.md`". Hoje (dia 9 do ciclo): 319 fingerprints acumulados; pace = 319/9 = **~35 fingerprints/dia** (~ 42 linhas considerando estatísticas + headers). Em 90 dias: ~3.150 fingerprints, ~3.700 linhas no _index.md.

**Por quê importa:** _index.md é loaded a cada audit (pelo agente de research) e por humanos verificando histórico. 3.700 linhas × 16 tokens = **59.200 tokens/load**. Rotação tardia onerea cada audit.

**Impacto positivo:** Rotação proativa por trimestre (ou ao atingir 1.000 fingerprints) mantém arquivo manageable; archive permite consulta cold quando necessário.

**Impacto negativo / risco:** Quebra de contexto se pesquisa de fingerprint precisar varrer múltiplos arquivos.

**Sugestão concreta:** Adicionar `scripts/rotate-fingerprint-index.sh` que move entradas > 60 dias para `_index-archive-YYYY-Q<n>.md`; rodar via cron mensal ou hook pre-commit quando _index.md > 1.000 linhas.

---

### 🟡 8. Três skills integrations grandes (kong, realtime, multitenancy) somam 761 linhas sem references/

**Fingerprint:** `token-three-large-integration-skills-kong-realtime-multitenancy-700-lines-combined-no-references`

**Evidência:** Fact-finding §7.1: kong=277 + realtime=246 + database-multitenancy=238 = **761 linhas combinadas**. Fact-finding §1.4: nenhuma das 3 está na lista de skills com references/. Custo combinado se todas forem loaded por software-architect: 761 × 16 = **12.176 tokens**.

**Por quê importa:** Integrações são especializadas; eager-load é raro mas multi-load em sessions de architect amplia. Padrão de extraction já comprovado em 8 skills.

**Impacto positivo:** Aplicar references/ pattern reduz para ~80 linhas core × 3 = 240 + carregamento condicional; **economia ~9.000 tokens** em sessões com architect intensivo.

**Impacto negativo / risco:** Tempo de extração ~30min/skill.

**Sugestão concreta:** Replicar receita do commit `b8ece69` (monitoring/jira) para os 3: `references/{patterns, examples, troubleshooting}.md`.

---

### 🟢 9. `commands/commit.md` 145 linhas e `refactor.md` 156 linhas — maiores command files

**Fingerprint:** `token-commands-commit-md-145-lines-and-refactor-md-156-lines-largest-command-files`

**Evidência:** Fact-finding §1.2: `commit.md` = 145 linhas, `refactor.md` = 156 linhas. Sobre média (`update.md` 140 também grande). Total commands = 938 linhas (média 33,5 — desvio positivo significativo). Custo loaded: (145+156) × 16 = **4.816 tokens** quando ambos invocados.

**Por quê importa:** Commands não devem replicar lógica que pertence a skills/agents. `commit.md` 145 linhas sugere prosa que poderia ser skill `commit-flow`.

**Impacto positivo:** Extrair detection patterns + group-by-layer logic para `skills/shared/commit-orchestration/` libera command para ~40 linhas (apenas Plan Gate + Load + Spawn).

**Impacto negativo / risco:** Refactor de commit flow é alto risco — usuário usa diariamente.

**Sugestão concreta:** Análise antes de execução: medir quanto de `commit.md` é único (vs duplicado em conventional-commits skill); estimar economia real antes de extrair.

---

### 🟢 10. Tool ordering divergence sem economia direta mas impede dedup tooling

**Fingerprint:** `token-tool-ordering-divergence-no-savings-but-impedes-deduplication-tooling`

**Evidência:** Fact-finding §5.2: 4 patterns de ordering. Pareado com report 01 #7. Argumento token aqui: padronização permite refactors em massa via simples `sed`, viabilizando consolidação futura (ex.: extrair foundational rule unificado por tier).

**Por quê importa:** Não é economia imediata, mas habilitador de economia futura. Quando next-step for "remover Foundational Rule duplicado em 17 agents", ordering canônico simplifica de 17 patterns regex para 1.

**Impacto positivo:** Habilita scripts de dedup posterior (ex.: estimativa de economia futura ~6.000 tokens em foundational-rule consolidation).

**Impacto negativo / risco:** Premature refactoring se não houver next-step concreto.

**Sugestão concreta:** Decidir ordering canônico (vide report 01 #7); depois quando rodar consolidation de foundational, ganho será direto.

---

## Síntese — ordem de prioridade (por economia estimada)

1. **🔴 #2** — `token-skill-project-context-291-lines-x-14-agents-65-184-tokens-eager-load` (~20.000 tokens/sessão economizáveis)
2. **🔴 #1** — `token-claude-md-557-lines-loaded-7-times-per-multi-agent-session-26-700-tokens` (~45.000 tokens/sessão)
3. **🟡 #4** — `token-mobile-react-native-264-lines-same-eager-load-issue` (~4.224 tokens/spawn)
4. **🟡 #3** — `token-mobile-flutter-292-lines-loaded-eagerly-by-mobile-developer-without-stack-detection-gate` (~4.672 tokens/spawn)
5. **🟡 #8** — `token-three-large-integration-skills-kong-realtime-multitenancy-700-lines-combined-no-references` (~9.000 tokens/sessão)
6. **🟡 #7** — `token-fingerprint-index-_index-md-380-lines-not-rotated-yet-rotation-policy-says-90d-current-pace-30d` (~30.000 tokens/audit em 90d)
7. **🟡 #5** — `token-skill-monitoring-extracted-but-references-files-may-be-loaded-eagerly` (verificação)
8. **🟢 #6** — `token-interaction-patterns-185-lines-loaded-by-update-md-but-no-agent-uses-conditional-load-yet` (preventivo)
9. **🟢 #9** — `token-commands-commit-md-145-lines-and-refactor-md-156-lines-largest-command-files` (~4.800 tokens)
10. **🟢 #10** — `token-tool-ordering-divergence-no-savings-but-impedes-deduplication-tooling` (habilitador)
