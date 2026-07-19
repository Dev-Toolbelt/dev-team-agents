# Economia de Tokens — 2026-05-23

> 3 sugestões originais. Cada item traz **trecho/evidência**, **motivo** e **impactos positivos e negativos** da correção proposta. Todas foram cruzadas contra o banco de 481 fingerprints (`_index.md`) e são inéditas.

---

## T1 — `qa-specialist` carrega `security-checklist` (123 linhas) **eager em todo spawn**, embora QA comportamental muitas vezes não tenha escopo de segurança — enquanto o SonarQube, no mesmo arquivo, **é gateado**

**Severidade:** MEDIUM
**Fingerprint:** `token-qa-specialist-eager-loads-security-checklist-123-lines-every-spawn-though-behavioral-qa-often-no-security-scope-sonarqube-gated-in-same-file`

**Evidência** — `agents/qa-specialist.md`, seção "Load Skills":

```markdown
:30 Load `security-checklist` skill …                              ← EAGER (sem condição)
:36 SonarQube / SonarCloud — if `sonar-project.properties`,
    `.sonarcloud.properties`, or `SONAR_TOKEN` is present, load … ← GATEADO por sinal de detecção
```

**Motivo:** o `qa-specialist` valida **comportamento e fluxos** — muitas tarefas de QA (regressão de um fluxo, validação de critérios de aceite, edge cases de uma feature) **não têm recorte de segurança**. Ainda assim a skill `security-checklist` (123 linhas, ~1.600 tokens) é carregada **incondicionalmente** em todo spawn. O contraste está no próprio arquivo: a integração SonarQube (linha 36) **é** gateada por sinais de detecção (`sonar-project.properties`/`SONAR_TOKEN`), provando que o agente já sabe carregar condicionalmente — só não aplicou isso à `security-checklist`. Distinto do achado de 2026-05-22 sobre a matriz do `backend-test-specialist` (skill `sonarqube`) e do bloco SAST do `security-specialist` (2026-05-21): aqui o consumidor é o **`qa-specialist`** e a skill é a **`security-checklist`**.

**Impacto positivo da correção:** gatear a carga ("carregue `security-checklist` quando a validação incluir auth/controle de acesso/dados sensíveis, ou quando o quality gate exigir cobertura de segurança") economiza ~1.600 tokens/spawn na maioria das tarefas de QA puramente comportamental, sem perder cobertura quando ela importa.

**Impacto negativo / risco:** risco de **sub**-cobertura se o gate for estreito demais e o LLM não reconhecer um fluxo sensível. Mitigação: o gatilho deve incluir tanto sinais explícitos (palavras como "auth", "login", "permissão") quanto o contexto de quality-gate, mantendo viés conservador para carregar quando em dúvida.

---

## T2 — `conventional-commits` (138 linhas) é carregada **eager pelos 3 agentes de review** (`code-reviewer`, `backend-reviewer`, `frontend-reviewer`) para "validar commit messages" — fora de escopo na maioria das revisões

**Severidade:** MEDIUM
**Fingerprint:** `token-conventional-commits-138-lines-eager-loaded-by-code-reviewer-and-backend-reviewer-and-frontend-reviewer-agents-commit-validation-not-in-scope-every-review`

**Evidência** — a mesma skill carregada incondicionalmente nos três revisores:

```
agents/code-reviewer.md:42      10. Load skills/shared/conventional-commits/SKILL.md — validate commit messages …
agents/backend-reviewer.md:29   12. Load skills/shared/conventional-commits/SKILL.md — validate commit messages …
agents/frontend-reviewer.md:28  11. Load skills/shared/conventional-commits/SKILL.md — validate commit messages …
```

**Motivo:** a `conventional-commits` (138 linhas, ~1.800 tokens) entra na sequência **eager** do Foundational Rule dos três revisores. Mas (1) muitas revisões são de **diff de working-tree** ou de um único arquivo, onde não há commit a validar; e (2) o próprio projeto pode **não usar** Conventional Commits — o `commands/commit.md` explicitamente "defere ao padrão do projeto primeiro" (GitHub-style, Jira prefix, etc.). Carregar a skill canônica em todo spawn de review é peso morto nesses casos. Num `/devteam:review` que dispara o router + 1-2 especialistas, são **2-3 cargas** dela por revisão. Distinto do fingerprint `token-conventional-commits-skill-138-lines-loaded-by-commit-and-pr-commands` (2026-05-17), cujo escopo eram os **comandos** `commit`/`pr` — aqui os consumidores são os **agentes de review**.

**Impacto positivo da correção:** gatear ("carregue `conventional-commits` apenas quando a revisão incluir o histórico de commits **e** o projeto usar Conventional Commits") economiza ~1.800 tokens por revisor não-aplicável; em `/devteam:review` multi-especialista, ~3.600-5.400 tokens por sessão.

**Impacto negativo / risco:** baixo. Risco de pular a validação de commits quando ela seria útil; mitigável com o gatilho duplo (escopo de commits + detecção do padrão do projeto), exatamente a mesma lógica que o `commands/commit.md` já usa.

---

## T3 — Em `/devteam:review`, as skills compartilhadas de revisão são **carregadas pelo router e recarregadas por cada especialista** — fan-out de 2-3× por revisão, sem contexto compartilhado

**Severidade:** MEDIUM
**Fingerprint:** `token-review-shared-skills-reloaded-by-router-then-each-specialist-2-3x-fanout-per-devteam-review-no-shared-loaded-context`

**Evidência** — o mesmo conjunto de skills aparece na sequência de carga do router **e** de cada especialista:

```
                       code-reviewer (router)  backend-reviewer  frontend-reviewer
reviewer-mindset (18)        :12                    :12               (sim)
project-context (266)        (Foundational)         :14               :14
comments-policy              :41                    :28               (sim)
conventional-commits (138)   :42                    :29               :28
reviewer-base (19)           :44                    :31               (sim)
token-efficiency (154)       :51                    :35               (sim)
```

**Motivo:** num `/devteam:review`, o `code-reviewer` (router) carrega o pacote de skills compartilhadas, classifica o diff e delega a `backend-reviewer` e/ou `frontend-reviewer` — que, por serem **spawns separados sem contexto carregado em comum**, **recarregam o mesmo pacote** (project-context 266, conventional-commits 138, token-efficiency 154, comments-policy, reviewer-base 19, reviewer-mindset 18). Resultado: o mesmo material é lido **2× (router + 1 especialista)** ou **3× (router + 2 especialistas, em PR full-stack)** na mesma revisão. Só `project-context` + `conventional-commits` + `token-efficiency` já somam ~558 linhas (~7.300 tokens) **por** recarga. Distinto da fronteira reviewer-base/mindset (2026-05-19) e do `project-context × 14 agentes` (que é sobre o fan-out global de spawns, não sobre a **recarga dentro de uma única revisão**).

**Impacto positivo da correção:** como o router já lê o diff e o contexto, ele poderia **passar um sumário enxuto** (decisão de routing + pontos de atenção do project-context) aos especialistas, que carregariam só o **delta** específico do seu domínio em vez do pacote inteiro. Economia estimada de ~7-15k tokens por `/devteam:review` multi-especialista. Alternativa mais simples: marcar explicitamente quais skills do pacote são "carregar-uma-vez no router e não repetir no especialista".

**Impacto negativo / risco:** médio. Especialistas são spawns isolados por design (isolamento de contexto é uma feature, não bug) — reduzir a recarga não pode comprometer a independência do julgamento de cada um. Mitigação: compartilhar **dados** (sumário do diff/contexto), não **conclusões**; manter cada especialista livre para chegar ao próprio veredito. Por isso a recomendação prioriza passar contexto factual, não pular a análise.
