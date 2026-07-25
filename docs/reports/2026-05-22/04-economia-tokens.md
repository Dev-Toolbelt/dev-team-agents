# Economia de Tokens — 2026-05-22

> 3 sugestões originais focadas em desperdício de tokens/overhead nos agentes. Cada item traz **evidência**, **motivo** e **impactos positivos e negativos**. Deduplicadas contra os 449 fingerprints.

---

## T1 — A matriz de cobertura SonarQube (~15 linhas) está **no corpo** do `backend-test-specialist` e é carregada em todo spawn, mesmo sem SonarQube no projeto

**Severidade:** MEDIUM
**Fingerprint:** `token-backend-test-specialist-sonarqube-coverage-matrix-fifteen-lines-in-agent-body-eager-loaded-every-spawn-even-when-sonarqube-absent`

**Evidência** — `agents/backend-test-specialist.md:104-126`: a seção "SonarQube Coverage Integration" inteira (texto de detecção + a matriz de 5 linguagens analisada em `03/A1` + threshold + "don't pad coverage") vive no **corpo** do agente, não numa skill carregada por detecção.

**Motivo:** a narrativa diz "When SonarQube is detected…", mas o **texto inteiro já está no corpo** — logo é carregado em **todo** spawn do `backend-test-specialist`, independentemente de o projeto usar SonarQube. Em qualquer projeto **sem** SonarQube (a maioria), essas ~15-22 linhas (~250-350 tokens) são peso morto. É a dimensão de **token** do achado `03/A1` (mesma raiz, dimensão diferente) — seguindo o padrão dos relatórios anteriores de registrar a violação agnóstica e o custo de token separadamente. Distinto do `token-frontend-test-specialist-react-and-vue-hook-recipes-…` (outro agente, outras receitas).

**Impacto positivo da correção:** mover a seção para `skills/devops/sonarqube/SKILL.md` com gate de detecção (`sonar-project.properties`/`SONAR_TOKEN`) — que o agente **já** referencia — faz o corpo carregar apenas um princípio de 2-3 linhas + o ponteiro; economiza ~250-350 tokens/spawn em projetos sem SonarQube; amplifica em `/devteam:tester` e `/devteam:fullstack`, onde o agente é spawnado junto com outros.

**Impacto negativo / risco:** indireção (já discutida em `03/A1`); em projetos **com** SonarQube, o LLM passa a carregar a skill — mas só quando o gate de detecção dispara, então não há perda no caso relevante. Garantir que o gate seja por sinal de detecção (arquivo/env), não por frase, para a economia se materializar.

---

## T2 — A skill `backlog-template` (171 linhas) é carregada **eager** em todo spawn do `product-analyst`, e não tem relação de fonte única com o `templates/backlog-template.md`

**Severidade:** MEDIUM
**Fingerprint:** `token-backlog-template-skill-171-lines-unconditionally-loaded-every-product-analyst-spawn-diverged-from-physical-template-same-name`

**Evidência** — `agents/product-analyst.md:19` (carga **incondicional** na Foundational Rule):

```
6. Load `skills/shared/backlog-template/SKILL.md` — use it as the canonical structure
   when generating backlog documents
```

E os dois artefatos com o **mesmo nome**, mas conteúdos **diferentes**:

```
171 skills/shared/backlog-template/SKILL.md  → estrutura multi-arquivo (docs/backlog/: overview.md, dod.md, epics.md)
 35 templates/backlog-template.md            → item único de backlog (Story, AC, Estimate, DoD)
```

**Motivo:** a skill de 171 linhas é carregada **toda vez** que o `product-analyst` é spawnado, mesmo quando a tarefa é apenas clarificação de escopo (Q&A de discovery) e **nenhum** documento de backlog será gerado naquele turno — a estrutura só é necessária no momento da geração. São ~2.200 tokens eager por spawn. Pior: existe um `templates/backlog-template.md` físico (35 linhas) com estrutura **divergente** e o `product-analyst` **nunca o usa** — ele só consome a skill. O banco tem o ângulo de **referência** (`ref-templates-backlog-template-md-orphan-…-skill-has-inline-template`), mas o ângulo de **token** (171 linhas eager por spawn) e a constatação de que os dois artefatos de mesmo nome **já divergiram** (drift sem regra de sync entre eles) são inéditos.

**Impacto positivo da correção:** trocar a carga eager por condicional — "carregue `backlog-template/SKILL.md` **quando for gerar** documentos de backlog" (no momento da geração, não na Foundational Rule) — remove ~2.200 tokens/spawn das interações de discovery puro. Como bônus, decidir uma **fonte única** (deprecar o `templates/backlog-template.md` órfão ou alinhá-lo à skill) elimina a divergência silenciosa.

**Impacto negativo / risco:** se a maioria dos spawns do `product-analyst` de fato terminar gerando backlog, o ganho é menor (a skill seria carregada de qualquer forma). Mitigação: medir; mas mesmo no pior caso, mover a carga para o ponto de uso não tem custo — apenas adia. Cuidado para não quebrar o fluxo de discovery que pressupõe a estrutura disponível ao final.

---

## T3 — A diretriz de fechamento "After completing any task, check the Update Triggers table in `docs-sync/SKILL.md`…" está duplicada **quase verbatim em ~12 agentes** — sem fonte única

**Severidade:** LOW-MEDIUM
**Fingerprint:** `token-docs-sync-closing-directive-after-completing-any-task-duplicated-verbatim-across-twelve-agents-no-single-source-multiplied-in-multi-agent-flows`

**Evidência** — a mesma diretriz aparece, com redação praticamente idêntica, em 12 agentes:

```
agents/backend-developer.md:251       agents/devops-specialist.md:227
agents/backend-test-specialist.md:150 agents/frontend-developer.md:222
agents/database-specialist.md:172     agents/frontend-test-specialist.md:252
agents/mobile-developer.md:191        … + variante de review em
agents/code-reviewer.md:220, backend-reviewer.md:196, frontend-reviewer.md:184
```

Texto típico: *"After completing any task, check whether the work delivered triggered any entry in the Update Triggers table defined in `skills/shared/docs-sync/SKILL.md`. If yes, load that skill and apply the surgical patch…"*

**Motivo:** é o **mesmo padrão** já flagrado para a `comments-policy` (`ref-comments-policy-load-directive-…-duplicated-verbatim-in-8-agents` + `token-comments-policy-load-directive-duplicated-in-8-agents-multiplied-per-session`), mas para uma **diretriz diferente** (docs-sync), ainda não registrada. São ~2-3 linhas repetidas em 12 arquivos: custo de token modesto por agente, mas **multiplicado** em fluxos multi-agente (`/devteam:fullstack`, `/devteam:review` spawnam vários), e — mais importante — uma **violação de fonte única**: mudar o protocolo de docs-sync exige editar 12 arquivos, e a redação já varia levemente entre as variantes "task" e "review" (sinal de drift incipiente).

**Impacto positivo da correção:** consolidar a diretriz num único lugar (a própria `docs-sync/SKILL.md` já é o destino; basta os agentes referenciá-la por uma linha curta padronizada, ou a CLAUDE.md inliná-la como regra global como já faz com outras) elimina a duplicação e o drift; uma mudança futura no protocolo passa a ser editada uma vez.

**Impacto negativo / risco:** a diretriz de fechamento serve como **lembrete in-context** no fim do corpo do agente — removê-la por completo pode reduzir a taxa de adesão (o agente "esquece" de patchar docs). Mitigação: manter **uma linha** de ponteiro ("Ao terminar, aplique o protocolo de docs-sync") em vez do parágrafo completo, ou promover a regra à CLAUDE.md (sempre em contexto). O ganho de token é menor que o de `T1`/`T2`; o valor maior é **manutenibilidade e consistência**.
