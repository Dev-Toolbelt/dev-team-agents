# Eixo E — Economia de Tokens — 2026-09-18

**Baseline:** `HEAD` = `ef69da3`

---

## MEDIUM-HIGH

### As 151 skills são symlinkadas em lote para `.claude/skills/`, colocando ~3,2K tokens de índice sempre carregado em cada contexto e em cada subagente

- **Fingerprint:** `token-151-skills-flat-symlinked-into-claude-skills-index-12751-chars-per-context`
- **Alvo:** `scripts/install.sh`
- **Evidência:** `scripts/install.sh:599-610` — "`for SKILL_CATEGORY in "$INSTALL_DIR/skills"/*/; do`" / "`for SKILL_DIR in "$SKILL_CATEGORY"*/; do`" … "`ln -s "../../.dev-team-agents/${REL_SKILL}" "$SKILL_TARGET_PATH"`". Medição: `find skills -name SKILL.md | wc -l` = **152**, das quais **151** estão em profundidade 4 e são linkadas pelo laço (`skills/skill-creator/SKILL.md`, profundidade 3, é a única que escapa — e é justamente uma das três registradas como *User-Invocable* em `CLAUDE.md:190-194`). Soma de `name:` + `description:` das 152 = **12.751 caracteres ≈ 3.187 tokens** (média de 69 chars por `description`, nenhuma acima de 95 — o corte de `token-sixteen-skill-descriptions…` está aplicado). Carregado por **todo contexto** (principal + cada spawn); `grep -rno "skills/.../SKILL.md" agents/ commands/` = **483** referências, todas por caminho explícito.
- **Problema:** o harness carrega skills por caminho explícito no corpo do agente (`Load skills/shared/project-context/SKILL.md`), mas o instalador registra **todas** elas como skills descobríveis pelo modelo. As ~148 que nenhum humano invoca e nenhum prompt dispara por si (integrations, ui-libraries, legacy, mobile, devops por plataforma) pagam entrada no índice sempre carregado sem nunca serem acionadas por ele.
- **Por que importa:** no HEAD, cada spawn de subagente reabre o índice completo. Um `/devteam:fullstack` (backend + frontend + database + ui-ux + 2 test-specialists + reviewer + qa) chega a 7–9 contextos: **7 × 3.187 ≈ 22.300 tokens** por execução só de índice, antes de qualquer `Load`. É o único custo do repositório que escala com o número de skills e não com o trabalho pedido — e cresceu para 152 arquivos sem nenhum gate medindo isso.
- **Proposta:** symlinkar apenas o subconjunto de fato invocável pelo usuário/modelo (hoje 3, conforme a tabela *User-Invocable Skills*) e referenciar o resto pelo caminho instalado `.dev-team-agents/skills/<cat>/<name>/SKILL.md` — exatamente a regra que `CLAUDE.md:295` já impõe a `templates/` depois de `ref-templates-dir-shipped-but-not-symlinked-…`.
- **Impacto positivo:** índice de ~12.751 → ~250 caracteres; economia de **≈3.100 tokens por contexto**, ~22K por run multi-agente.
- **Impacto negativo / risco:** perde-se a descoberta automática por `description` — uma skill só entra em jogo se algum agente a citar, e as 483 referências viram caminhos longos (a serem reescritos junto com `helpers/orphan-skill-scan.sh`, que resolve por basename, e com o resolvedor opencode, que resolve por `name` de frontmatter). Uma skill esquecida em nenhum corpo passa a ser **inalcançável** em vez de meramente órfã.
- **Esforço:** Alto

---

## MEDIUM

### O bloco `## Cache` ocupa 34% da skill `current-context`, é carregado por 29 comandos e guarda um payload que não satisfaz a Scope Rule da própria skill

- **Fingerprint:** `token-current-context-cache-block-36-of-105-lines-fails-own-scope-rule`
- **Alvo:** `skills/shared/current-context/SKILL.md`
- **Evidência:** `skills/shared/current-context/SKILL.md:60` — "Running 4 git commands on every invocation adds latency. Use a short-lived cache stored at `.dev-team-agents/user-data/.context-cache.json`"; o payload em `:63` é `{ "ts": …, "branch": "...", "changed": N, "worktree": "yes|no" }`, enquanto `:17-18` pedem `git diff --name-only HEAD` e `git diff --name-only main...HEAD` (**listas de arquivos**) e `:23` manda "Restrict all analysis and actions to files and changes within the detected context". Medição: **36 de 105 linhas (`:58-93`) ≈ 420 tokens**, carregadas por **29 de 35 comandos** (`grep -L current-context commands/*.md` devolve só `commit`, `health-check`, `learn`, `rule`, `sync-rules`, `update`).
- **Problema:** um terço de uma skill carregada incondicionalmente em quase todo comando é implementação bash de cache — conteúdo que o modelo lê e não raciocina sobre. Pior: no hit de cache (`:81`, `[ "$age" -lt 1800 ] && echo "Context (cached): …" && exit 0`) o agente fica sem as duas listas de arquivos, ou seja, sem o insumo da Scope Rule que é a razão de existir da skill.
- **Por que importa:** ~420 tokens por invocação de comando, para um mecanismo que economiza **96 ms medidos** de `git` ao custo de 2 forks de `python3` (**20 ms medidos**) e que, quando acerta, devolve menos informação do que o caminho não-cacheado. O TTL também já divergiu do espelho: `CLAUDE-md/user-data.md:17` diz "TTL 300s", a skill diz 1800.
- **Proposta:** remover `:58-93` do SKILL.md — ou movê-lo para um `scripts/` da skill invocado por uma linha — e, se o cache continuar existindo, incluir as duas listas de arquivos no payload.
- **Impacto positivo:** 105 → ~71 linhas; **−420 tokens por invocação** em 29 comandos; some a divergência de TTL entre skill e espelho.
- **Impacto negativo / risco:** perde-se a economia de ~96 ms por invocação em projetos grandes (onde `git diff --name-only main...HEAD` custa mais que aqui), e passa a existir um script a mais para instalar, versionar e checar no health-check.
- **Esforço:** Baixo

### `graphify-setup` carrega 30 linhas de detecção de SO que duplicam — e contradizem — a seção canônica de `tool-installers`, num passo que já delega a instalação

- **Fingerprint:** `token-graphify-setup-os-detection-30-lines-diverges-from-tool-installers`
- **Alvo:** `skills/devops/graphify-setup/SKILL.md`
- **Evidência:** `skills/devops/graphify-setup/SKILL.md:24-53` — "## Step 1 — OS Detection" … "> Windows without WSL is not supported. Please activate WSL first"; contra `skills/devops/tool-installers/SKILL.md:12` — "On Windows, **prefer native install first** (`winget`, falling back to `choco` or `scoop` if present) — no WSL round-trip"; e o próprio `graphify-setup/SKILL.md:64`, que já diz "run `/devteam:install graphify jq` … Do not install them directly here; this avoids duplicating install commands in two places". Medição: **30 linhas de 226 (13%)**; `CLAUDE.md:248` declara `/devteam:install` "The single entrypoint for tool installs — `graphify-setup` … delegate here instead of duplicating install commands".
- **Problema:** a cópia local da detecção de SO sobreviveu à consolidação. Nenhum passo posterior (`Step 4`–`Step 10`, geração de `graphify.json`, hooks, `.gitignore`, build, injeção no CLAUDE.md) consome `uname`: o único consumidor real era o install, que o Step 2 já terceirizou.
- **Por que importa:** além das 30 linhas pagas em todo setup de graphify, a cópia **já divergiu na direção destrutiva** — um usuário Windows com `winget` é barrado em `:47-53` ("Do not continue on Windows until WSL is confirmed active") pelo caminho que a skill canônica atende nativamente.
- **Proposta:** substituir `:24-53` por uma linha delegando a `skills/devops/tool-installers/SKILL.md` § OS Detection, e renumerar (o arquivo já pula de Step 2 para Step 4).
- **Impacto positivo:** 226 → ~197 linhas (−13%); elimina a única fonte que contradiz a política Windows-nativo do harness.
- **Impacto negativo / risco:** `graphify-setup` passa a depender de uma segunda skill para um passo hoje autocontido — se o setup rodar sem `tool-installers` carregado, a detecção de SO deixa de existir em vez de existir errada.
- **Esforço:** Baixo

### O gate de consentimento de telemetria refaz o mesmo fork de `python3` de 3 a 3+K vezes por Stop, acima do fast-path que existe para evitá-lo

- **Fingerprint:** `token-telemetry-consent-guard-reforks-python3-above-the-fast-path`
- **Alvo:** `scripts/hooks/stop/05-telemetry.sh`
- **Evidência:** `scripts/hooks/stop/05-telemetry.sh:31` — "`_telemetry_enabled "$PREFS_FILE" || exit 0`" aparece **acima** de `:39` — "`if [ "${DEVTEAM_NO_CHANGES:-0}" = "1" ]; then`", cujo comentário em `:36` justifica o fast-path dizendo que esses eventos "cost two python3 forks each"; o mesmo gate é reexecutado em `scripts/helpers/telemetry-send.sh:311` (`--queue`) e `:320` (`--flush`), e `scripts/hooks/lib/agent-usage.sh:140` chama "`bash "$telemetry_send" --queue "agent_completed" "$props"`" **uma vez por agente**. Cada chamada forka `python3` (`scripts/lib/telemetry-guard.sh:27-35`) sobre o mesmo arquivo de **23 linhas**. Medição: **8 ms por fork** (20 forks = 175 ms neste container); com K=4 agentes o Stop paga **3+K = 7 forks ≈ 56 ms**, e o Stop dispara a cada turno do assistente. Com o default de instalação (`scripts/install.sh:1061` — "`TELEMETRY_VALUE="false"`"), sobra **1 fork puramente desperdiçado por turno**, mais 1 por chamada Bash/Task (`scripts/hooks/pre-tool-use/02b-telemetry.sh:52`).
- **Problema:** o consentimento é um valor imutável dentro de um mesmo Stop, mas é reavaliado por processo, com um interpretador novo a cada vez. E o gate caro está posicionado antes do fast-path barato que o próprio arquivo documenta como a defesa contra forks.
- **Por que importa:** numa sessão de 200 turnos e 300 chamadas Bash, o caminho default (telemetria desligada) gasta ~500 forks de `python3` ≈ **4 s acumulados** para decidir 500 vezes a mesma coisa; com telemetria ligada e spawns multi-agente o custo por Stop cresce linearmente com o número de agentes.
- **Proposta:** mover `:31` para **abaixo** do bloco `DEVTEAM_NO_CHANGES` e memoizar o veredito — `telemetry-guard.sh` exporta `DEVTEAM_TELEMETRY_OK` na primeira avaliação e `telemetry-send.sh` o respeita em vez de reler `preferences.json`.
- **Impacto positivo:** de 3+K forks por Stop para 1; no default (desligado), 0 fork após o primeiro turno. ~8 ms × (2+K) recuperados por Stop.
- **Impacto negativo / risco:** enfraquece o *fail-closed* — uma variável de ambiente herdada é uma superfície a mais que um arquivo relido, e um usuário que desliga a telemetria no meio da sessão continuaria enfileirando até o próximo Stop. Exige documentar o novo contrato nos três consumidores listados no cabeçalho de `telemetry-guard.sh:6-8`.
- **Esforço:** Médio

---

## Descartados por duplicação

| Candidato | Porta | Fingerprint colidente |
|---|---|---|
| `orphan-skill-scan.sh` emite 12 linhas de falso positivo no contexto a cada Stop que toca `agents/`/`skills/` — o filtro awk `:170-182` não isenta "enforced by the Hard rule in" nem "delegate entirely to" | 3 (alvo + causa raiz) | `ref-orphan-skill-scan-reports-design-system-audit-duplicate-load-…` |
| `output-format/SKILL.md:121-142` — template de Security Review (22 linhas) já superado por `skills/security/security-checklist/references/output-template.md`, mandado na mesma linha (`security-specialist.md:128`) | 3 (3/3) | `token-output-format-third-copy-of-plan-format-42-lines-nine-load-sites` |
| Split integral de `output-format` (203 linhas × 9 sítios, 7 templates de relatório) | 4 (sem sub-escopo novo) | `token-output-format-third-copy-of-plan-format-42-lines-nine-load-sites` |
| Ramo `Bash` de `02b-telemetry.sh` forka `python3` antes de filtrar por `/devteam:` no payload cru | 3 (3/3) | `flow-telemetry-pre-tool-use-02-runs-on-every-tool-call-without-batching-…` (🟢 Resolved) |
| Bloco Jira Detection + branch naming: 133 linhas espalhadas por 13 corpos de agente | 3 (alvo + causa raiz) | `agent-jira-detection-branch-naming-block-duplicated-no-canonical-home` |
| `model-identity/SKILL.md` (58 linhas × 18 agentes) redundante com o `<!-- run-banner -->` e o `## Before You Finish` inline | 3 (alvo + causa raiz) | `token-model-identity-32-of-58-lines-are-format-spec-and-examples-held-inline` |
| Bloco PLAN GATE de 4 linhas verbatim em 16–19 comandos (`backend.md:103-106` e pares) | 3 (3/3) | `token-current-context-block-deduplication` (🟡 Parcial nesta Fase 1) |
| Sufixo de 455 chars do run-banner repetido literalmente em 23 comandos (`fullstack.md:16` e pares) | 3 (3/3) | `token-current-context-block-deduplication` |
| `commands/update.md` (192) e `commands/symlinks.md` (179) como os maiores wrappers "thin script runner" | 3 (alvo + causa raiz) | `token-commands-commit-md-145-lines-and-refactor-md-156-lines-largest-command-files` |
