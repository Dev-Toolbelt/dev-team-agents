# Eixo E — Economia de tokens (2026-08-21)

**Baseline:** `HEAD` = `a67cac9` · **Baseline anterior:** `c03f898`

---

## Medições

### Superfícies sempre carregadas ou de caminho quente

| Superfície | Linhas hoje | Linhas em `c03f898` | Carregada por | Condicional? |
|---|---:|---:|---|---|
| `CLAUDE.md` (repo) | 602 | 586 | toda sessão do repo | **Não** |
| `skills/shared/project-context/SKILL.md` | 269 | 269 | 18/18 agentes + 7 skills | **Não** (Foundational Rule) |
| `skills/shared/interaction-patterns/SKILL.md` | 209 | 209 | 32 comandos + 2 agentes | **Não** |
| `skills/shared/output-format/SKILL.md` | **203** | 190 | 7 agentes + 2 comandos + `plan-mode` | **Não** — carregada inteira |
| `skills/architecture/orchestration/SKILL.md` | **391** | 377 | `software-architect` + `orchestration` refs | **Não** (dentro do fluxo de orquestração) |
| `skills/shared/conventional-commits/SKILL.md` | **169** | 140 | 8 agentes + 4 comandos + 6 skills | **Sim** (gated por "há commits a validar") |
| `skills/shared/comments-policy/SKILL.md` | 116 | 102 | 18 refs | **Sim** (Conditional Section Loading) |
| `skills/shared/token-efficiency/SKILL.md` | 160 | 160 | 18/18 agentes | **Não** (achado já registrado) |
| `skills/shared/work-feedback/SKILL.md` | **71** (novo) | 0 | `orchestration` § Spawn Integrity check 5 | **Parcial** — carregada antes do gate (ver MEDIUM-HIGH #2 / LOW-MEDIUM #5) |
| `commands/merge.md` | **105** (novo) | 0 | só em `/devteam:merge` | Sim |
| `commands/commit.md` | 193 | 189 | só em `/devteam:commit` | Sim |
| `commands/pr.md` | 162 | 148 | só em `/devteam:pr` | Sim |
| `scripts/install.sh` | **1240** | 1086 | instalação/atualização | n/a |
| `scripts/hooks/pre-tool-use/02-graphify-hint.sh` | 34 | 20 | **toda chamada de tool** (PreToolUse) | ver HIGH-adjacente #1 |
| Índice de skills (soma de todas as `description:`) | 11.041 chars (~2,8K tokens) | — | sempre | **Não** |

Nenhuma `description:` de skill excede hoje o orçamento de 95 chars (achado `token-sixteen-skill-descriptions…` segue resolvido). A skill nova (`work-feedback`, 91 chars) está dentro.

### Ganho já entregue no delta (registrado como crédito, não como achado)

- `02-graphify-hint.sh` passou a emitir o bloco `additionalContext` **uma vez por sessão** em vez de a cada `Glob`/`Grep`. Em sessões de exploração longa isso elimina dezenas de reinjeções do mesmo texto no transcript retido. O mecanismo do marcador está correto; o problema é **onde** ele foi posicionado (ver achado #1).
- `commands/pr.md:99` trocou `git diff base...HEAD` cru por `--stat` + `git log` + diffs pontuais. Isso endereça diretamente o fingerprint aberto `token-pr-md-unbounded-full-diff-to-repetitive-tier-while-same-file-caps-git-log` — a verificação de estado desse item pertence à Fase 1, não a este relatório.
- `skills/shared/output-format/SKILL.md:10-21` (Readability Rule) e `skills/shared/comments-policy/SKILL.md` § Length Rule são regras que **reduzem** tokens de saída. Custo somado de 27 linhas contra um teto explícito de 3 linhas por comentário e parágrafos de 2–4 linhas: saldo positivo.

---

## HIGH

Nenhum achado nesta severidade.

---

## MEDIUM-HIGH

### `02-graphify-hint.sh` forka 3 subprocessos antes do próprio early-exit, em toda chamada de tool de um projeto com graphify

- **Fingerprint:** `token-graphify-hint-3-git-forks-before-marker-early-exit-on-every-tool-call`
- **Alvo:** `scripts/hooks/pre-tool-use/02-graphify-hint.sh`
- **Evidência:**
  - `scripts/hooks/pre-tool-use/02-graphify-hint.sh:16-20` —
    ```
    PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || PROJECT_ROOT="$(pwd)"
    MAIN_REPO_ROOT="$(cd "$(git rev-parse --git-common-dir 2>/dev/null)/.." 2>/dev/null && pwd)"
    [ -n "$MAIN_REPO_ROOT" ] || MAIN_REPO_ROOT="$PROJECT_ROOT"
    MARKER="${MAIN_REPO_ROOT}/.dev-team-agents/user-data/.graphify-hint-shown"
    [ -f "$MARKER" ] && exit 0
    ```
  - `scripts/hooks/pre-tool-use/02-graphify-hint.sh:24-26` (comentário pré-existente, ainda no arquivo) — "Pure-bash substring match instead of grep|sed: skips 2 forked subprocesses on every tool call that isn't Glob/Grep — the common case whenever a knowledge graph is present."
- **Problema:** o bloco de resolução do marcador foi inserido **acima** tanto do `case` de tool-name (linhas 27-31, bash puro, zero fork) quanto do próprio `[ -f "$MARKER" ]`. O resultado é que, num projeto onde `graphify-out/graph.json` existe, **toda chamada de tool** — `Read`, `Edit`, `Bash`, `Task`, qualquer uma — paga 3 forks (`git rev-parse --show-toplevel`, subshell `$(cd …)`, `git rev-parse --git-common-dir`) antes de qualquer filtro. Antes de `c03f898..HEAD` o custo desse hook para tools não-`Glob`/`Grep` era **zero fork**. Pior: o `PROJECT_ROOT` da linha 16 só é usado como fallback na linha 18 — é um fork desperdiçado no caminho feliz.
- **Por que importa:** o arquivo carrega, três linhas abaixo, o comentário que documenta exatamente a decisão de projeto que a mudança inverteu ("skips 2 forked subprocesses on every tool call"). A correção de reinjeção de contexto (real e valiosa) foi paga com uma regressão de latência no hot path, e o comentário que deveria impedir isso continua lá, agora factualmente contrariado pelo código acima dele. Medição no workspace Linux: 200 iterações do par de `git rev-parse` = **2,671 s reais → ~13,4 ms por chamada de tool**. Em macOS (plataforma do usuário) o spawn de processo é tipicamente 2–4× mais caro. Uma sessão de 500 tool calls num projeto com graphify: **~6,7 s (Linux) a ~25 s (macOS)** de latência adicionada, integralmente evitável a partir da segunda chamada.
- **Proposta:** reordenar sem mudar semântica — (a) mover o `case "$INPUT"` de tool-name (linhas 22-31) para **antes** da resolução do marcador, para que tool calls não-`Glob`/`Grep` saiam com zero fork; (b) tentar primeiro o caminho barato `[ -f ".dev-team-agents/user-data/.graphify-hint-shown" ] && exit 0`, que acerta no checkout principal (caso dominante) sem nenhum fork; (c) só resolver `MAIN_REPO_ROOT` via `git rev-parse` quando esse teste falhar — ou seja, no máximo uma vez por sessão em worktree linkado. `PROJECT_ROOT` passa a ser calculado dentro do fallback, não antes dele.
- **Impacto positivo:** 3 forks → **0 forks** em ~95% das chamadas de tool (tudo que não é `Glob`/`Grep`) e 3 forks → 0 nas chamadas `Glob`/`Grep` após a primeira, no checkout principal. ~13,4 ms × N tool calls economizados por sessão em todo projeto com `graphify-out/graph.json`; hook roda em 100% das sessões desses projetos.
- **Impacto negativo / risco:** em worktree linkado, o marcador local (`.dev-team-agents/user-data/` dentro do worktree) pode não existir mesmo já tendo sido escrito no checkout principal — nesse caso o fallback com `git rev-parse` roda e o comportamento fica idêntico ao de hoje (nenhuma regressão, só nenhum ganho nesse caso). Reordenar o `case` significa que `INPUT=$(cat)` passa a ser lido antes do teste do marcador; isso é leitura de stdin, não fork, e o hook já precisa consumir stdin de qualquer forma.
- **Esforço:** Baixo

### Dois laços de `ScheduleWakeup` disputam a mesma rodada de spawn, com cadências de 300 s e 1200–1800 s e nenhum ciente do outro

- **Fingerprint:** `token-two-schedulewakeup-poll-loops-same-spawn-round-300s-vs-1200-1800s`
- **Alvo:** `skills/architecture/orchestration/SKILL.md` + `skills/shared/work-feedback/SKILL.md`
- **Evidência:**
  - `skills/architecture/orchestration/SKILL.md:223-225` — "If `ScheduleWakeup` is available, call it before ending the turn: `delaySeconds` in the 1200–1800s range for routine rounds […] `reason` naming which agent(s) are still outstanding."
  - `skills/architecture/orchestration/SKILL.md:228-229` — "On that wakeup, call the actual status tool (`TaskList`/`TaskGet`/`TaskOutput`) before doing anything else"
  - `skills/architecture/orchestration/SKILL.md:245-247` — "### 5. Periodic status table / While background sub-agents are working, load `skills/shared/work-feedback/SKILL.md` and follow it"
  - `skills/shared/work-feedback/SKILL.md:19` — `"work_feedback_interval_minutes": 5`
  - `skills/shared/work-feedback/SKILL.md:43-44` — "After spawning, call `ScheduleWakeup` with `delaySeconds` = the clamped interval […] On each wake-up, check the real status of in-flight sub-agents (`TaskList`/`TaskOutput` […])"
  - `skills/architecture/orchestration/SKILL.md:213` e `:245` — ambas as seções são numeradas **`### 5.`**, e `CLAUDE.md:172` aponta para "§ Spawn Integrity, check 5" sem desambiguar qual.
- **Problema:** os dois blocos disparam na mesma situação (rodada de delegação com subagentes ainda sem banner de retorno / rodando em background), ambos agendam `ScheduleWakeup`, ambos chamam `TaskList` no wake-up, e nenhum dos dois menciona o outro. As cadências divergem em **4× a 6×**: 1200–1800 s no check de auto-reativação contra 300 s (padrão) no `work-feedback`. O check de reativação tem teto explícito ("Two reactivation attempts per stalled agent is the default ceiling", `:236`); o `work-feedback` não tem teto — ele só para quando todos os passos estão ✅ (`:49`). E o padrão de `work_feedback_active` é `true`, então o laço mais caro é o que está ligado por omissão em toda instalação.
- **Por que importa:** numa rodada de background de 1 hora, o desenho pretendido pelo check de reativação são 2 acordadas; o `work-feedback` adiciona **12** acordadas, cada uma com uma chamada `TaskList` mais uma tabela de 8–12 linhas emitida no contexto principal — ou seja, 12 turnos extras de assistant que ninguém pediu, sobre um mecanismo cujo objetivo declarado é reduzir o re-prompt do usuário. Estimativa conservadora de 250–400 tokens por tick (payload do `TaskList` + tabela) → **≈3–5K tokens por hora de trabalho em background**, contra ≈0,6–0,9K se o mesmo status viesse anexado às acordadas que o check de reativação já agenda. A numeração duplicada `### 5.` (e o cabeçalho `:152` que ainda diz "Three checks, in order" para 5 checks) é o sintoma: o segundo laço foi anexado sem que o primeiro fosse reconciliado.
- **Proposta:** unificar em **um** laço. Concretamente: (a) reescrever `orchestration:245` como um sub-item do check de auto-reativação, não como um check irmão — "quando `work_feedback_active` for `true`, a acordada agendada por este check emite a tabela do `work-feedback` em vez de apenas registrar liveness"; (b) fazer `work_feedback_interval_minutes` **derivar** do intervalo do check de reativação em vez de ter um default próprio de 5 min, ou no mínimo elevar o default para 15 min (900 s) para ficar dentro da mesma ordem de grandeza; (c) importar o teto de 2 tentativas do check de reativação para o laço do `work-feedback`, que hoje é ilimitado; (d) renumerar as seções (o segundo `### 5.` vira `### 6.` ou some, conforme (a)) e corrigir `CLAUDE.md:172`, que hoje aponta para um "check 5" ambíguo.
- **Impacto positivo:** 12 acordadas/hora → 2–4; ≈3–5K tokens/hora → ≈0,6–1,2K, em todo fluxo que orquestra subagentes em background (`/devteam:backend`, `/devteam:frontend`, `/devteam:fullstack`, `/devteam:mobile`, `/devteam:refactor`, `/devteam:audit`, `/devteam:review`, `/devteam:plan` — 8 comandos + `software-architect` direto). Elimina também a ambiguidade de "check 5" em `CLAUDE.md:172`.
- **Impacto negativo / risco:** elevar o intervalo reduz a granularidade de feedback que o usuário pediu explicitamente quando essa feature foi criada (`.dev-team-agents/user-data/session-summary.md:23-25`). Mitigação: `work_feedback_interval_minutes` continua sendo o botão do usuário — mudar apenas o **default**, não o range aceito. Unificar os laços também acopla dois mecanismos que hoje podem ser desligados de forma independente (`work_feedback_active` desliga um, o outro não tem chave); a proposta (a) precisa preservar o comportamento de liveness quando `work_feedback_active` é `false`.
- **Esforço:** Médio

---

## MEDIUM

### `output-format/SKILL.md` guarda uma terceira cópia do formato de plano, já divergente, em 42 linhas carregadas por 9 sítios

- **Fingerprint:** `token-output-format-third-copy-of-plan-format-42-lines-nine-load-sites`
- **Refina:** `gov-plan-template-vs-skill-duplication`
- **Alvo:** `skills/shared/output-format/SKILL.md`
- **Evidência:**
  - `templates/plan-template.md:5-6` — "This file is the single source of truth for the plan structure, the Par.-column semantics, and the approval closer. **Do not restate them anywhere else.**"
  - `skills/shared/output-format/SKILL.md:144-185` — bloco `## Plan Template` de 42 linhas / 1.008 bytes, reproduzindo `## Plan — [Task Name]`, `### Context`, `### Scope`, `### Approach`, a tabela `### Steps` com coluna `Par.`, `### Risks & Dependencies`, `### Definition of Done` e o fecho "Awaiting your approval before proceeding."
  - `skills/shared/output-format/SKILL.md:168` — "Par.: same letter = parallel, — = sequential"
  - `templates/plan-template.md:32` — "Use \"---\" for steps that must wait for the previous one to complete."
  - `CLAUDE.md:164` (§ Canonical Rule Homes) — "Plan document format | `templates/plan-template.md`, loaded via `skills/shared/plan-mode/SKILL.md` | Load the template; never ship a second rendering of the format"
- **Problema:** o fingerprint `gov-plan-template-vs-skill-duplication` (✅ Executed 2026-07-31) removeu a cópia divergente que vivia em `plan-mode/SKILL.md`. Uma **terceira** cópia sobreviveu em `output-format/SKILL.md` e não foi tocada — e já divergiu no sentinela da coluna `Par.`: o canônico manda `"---"`, esta cópia manda `—` (travessão). Não é cosmético: são dois caracteres diferentes num campo que um agente preenche literalmente ao renderizar um plano. O nome da coluna também diverge (`Files` aqui, `Files / Areas Affected` no canônico).
- **Por que importa:** `output-format/SKILL.md` é carregada **inteira** por 7 agentes (`software-architect`, `code-reviewer`, `backend-reviewer`, `frontend-reviewer`, `security-specialist`, `database-specialist`, `qa-specialist`), 2 comandos (`explain`, `health-check`) e apontada por `plan-mode/SKILL.md:49`. Desses 9 sítios, **nenhum** carrega a skill para emitir um plano — os 7 agentes a carregam no fecho, para formatar review/report/QA output ("all review output must follow pure markdown format"). São 42 linhas irrelevantes para o consumidor em 100% dos load sites, mais o risco de o agente renderizar um plano a partir da cópia errada. Somando os 9 sítios: **≈378 linhas agregadas** por fluxo multi-agente que carrega a skill em cada spawn.
- **Proposta:** apagar `skills/shared/output-format/SKILL.md:144-185` e substituir por uma linha de rota: "Plan documents follow `.dev-team-agents/templates/plan-template.md`, loaded via `skills/shared/plan-mode/SKILL.md` — this skill does not restate it." Corrigir o sentinela da coluna `Par.` de uma vez: `CLAUDE.md` (§ Parallel Execution After Approval) usa `—`, `templates/plan-template.md:32` usa `"---"`; escolher um e alinhar os dois no mesmo commit.
- **Impacto positivo:** `output-format/SKILL.md` de 203 → **162 linhas** (−20%), em 9 sítios de carga; ≈378 → ≈9 linhas agregadas. Elimina a terceira cópia de um formato que o próprio template declara ser fonte única, e fecha a única divergência de sentinela que sobrou.
- **Impacto negativo / risco:** um agente que hoje renderiza um plano a partir de `output-format` sem carregar `plan-mode` passa a precisar de um load a mais. Levantamento dos 9 sítios não encontrou nenhum nessa situação (os 7 agentes carregam `plan-mode` via `project-context`), mas o risco não é zero se um comando novo carregar só `output-format` e esperar o template de plano ali.
- **Esforço:** Baixo

### `install.sh` ganhou um segundo bloco injetado no `CLAUDE.md` do projeto-alvo, sem orçamento e restatando a skill que ele mesmo manda carregar

- **Fingerprint:** `token-install-sh-second-unconditional-claude-md-injection-35-lines-every-session`
- **Alvo:** `scripts/install.sh` (Step 8 + Step 8b) e `skills/shared/setup-health-check/references/fix-patterns.md`
- **Evidência:**
  - `scripts/install.sh:862` — "# ── Step 8b: Inject Commit Rule into project CLAUDE.md ───────────────────────"
  - `scripts/install.sh:872-882` — bloco anexado (11 linhas / 1.006 bytes), com as regras 1–4; regra 3: "Never include AI attribution: no `Co-Authored-By: Claude`, no `🤖 Generated with Claude Code`…"
  - `skills/shared/conventional-commits/SKILL.md:48` — "**Never** add `Co-Authored-By:` of any kind — not for Claude, not for any AI tool, not for any automated process"
  - `scripts/install.sh:833-856` — Step 8, bloco pré-existente (24 linhas / 959 bytes)
  - `skills/shared/setup-health-check/references/fix-patterns.md:270-287` — segunda cópia do mesmo bloco, como auto-fix da Category 6
- **Problema:** o `CLAUDE.md` de todo projeto instalado passa a carregar **35 linhas / ~1,97 KB** de blocos gerenciados (Step 8 = 24, Step 8b = 11), lidos em 100% das sessões daquele projeto. O bloco do Step 8b é acionável apenas nas sessões que fazem commit, e 2 das suas 4 regras já estão dentro da skill que a regra 1 manda carregar (a proibição de `Co-Authored-By` é literalmente `conventional-commits:48`; a Work Summary Table da regra 4 é uma seção da mesma skill). Não existe teto declarado para esse mecanismo: `install.sh` hoje tem dois `cat >> CLAUDE.md` marcados, `fix-patterns.md` replica ambos, e nada em `CLAUDE.md` ou no lint limita um terceiro.
- **Por que importa:** essa é a única superfície do harness que grava direto no arquivo mais caro do projeto do usuário — aquele que o provider lê antes de qualquer outra coisa, em toda sessão, sem gate possível. É também o mecanismo com pior razão sinal/custo do repo hoje: a regra 3 é redundante com a skill, a regra 2 duplica o `git log --oneline -10` que a própria skill descreve, e o texto é mantido em **duas** cópias (install.sh e fix-patterns.md) que precisam ser patcheadas juntas sem nenhum gate que verifique isso — o lint não compara os dois heredocs.
- **Proposta:** (a) comprimir o bloco do Step 8b para 3 linhas — cabeçalho, "load `.dev-team-agents/skills/shared/conventional-commits/SKILL.md` and follow it, including its § Work Summary Table", e "defer to the project's existing `git log` pattern if it differs" — deixando as regras de atribuição onde já vivem, na skill; (b) registrar em `CLAUDE.md` um teto explícito para blocos injetados no `CLAUDE.md` do projeto-alvo (p.ex. "no máximo 2 blocos gerenciados, ≤ 30 linhas somadas; qualquer regra nova entra numa skill referenciada, não inline"); (c) extrair o texto dos dois heredocs para um único arquivo lido por `install.sh` e por `fix-patterns.md`, ou adicionar um check ao `helpers/agent-lint.sh` que compare os dois blocos.
- **Impacto positivo:** 35 → ~27 linhas gerenciadas no `CLAUDE.md` de cada projeto instalado, lidas em 100% das sessões desse projeto (~450 bytes/sessão economizados por projeto, permanentemente). O teto e o check fecham a porta para o terceiro bloco e para a divergência entre as duas cópias do heredoc.
- **Impacto negativo / risco:** a regra 3 (sem atribuição de IA) é a que o usuário mais sente quando falha, e movê-la para "dentro da skill" só funciona se a regra 1 for de fato seguida. Se um commit por prompt direto ignorar o load da skill, hoje ele ainda vê a proibição inline; depois da compressão, não. Mitigação: manter a regra 3 inline e comprimir só as regras 2 e 4 (ganho menor, ~4 linhas, mas risco zero). O Step 8 é append-only e idempotente por marcador — encurtar o bloco não reescreve os `CLAUDE.md` já instalados; o texto antigo permanece até o `health-check` da Category 6 ser ensinado a substituir, e ele não pode deletar (No-Destruction Rule). Isso é um argumento para acertar o tamanho **agora**, antes que a base instalada cresça.
- **Esforço:** Médio

---

## LOW-MEDIUM

### `work-feedback` guarda o próprio opt-out dentro da skill: 71 linhas são carregadas antes do agente poder saber que não deve rodar

- **Fingerprint:** `token-work-feedback-opt-out-gate-lives-inside-the-71-line-skill-it-gates`
- **Alvo:** `skills/shared/work-feedback/SKILL.md`
- **Evidência:**
  - `skills/shared/work-feedback/SKILL.md:14` — "Read `.dev-team-agents/user-data/credentials.local.json` before doing anything in this skill"
  - `skills/shared/work-feedback/SKILL.md:23` — "`work_feedback_active: false` → **do not** run any part of this skill. No table, no scheduling. Proceed with the task silently as if this skill did not exist."
  - `skills/architecture/orchestration/SKILL.md:247-250` — "While background sub-agents are working, load `skills/shared/work-feedback/SKILL.md` and follow it […] Do not restate its gate check, loop mechanics, or table format here."
  - `CLAUDE.md:172` — "Never restate the gate check, loop mechanics, or table format"
- **Problema:** o orquestrador carrega as 71 linhas (4.063 bytes) da skill e só então, na linha 14, descobre que precisa ler um JSON para saber se deve ignorar tudo o que acabou de ler. Quando `work_feedback_active` é `false`, as 71 linhas foram custo puro. A regra "never restate the gate check" em `CLAUDE.md:172` e em `orchestration:249` é justamente o que impede a solução óbvia — colocar o teste de uma linha no chamador.
- **Por que importa:** é o padrão inverso do que o repo já pratica em outros pontos: `project-context/SKILL.md:23-28` (First-Time Setup Guard), `:140-142` (Session Summary write rules) e `:146-148` (Contradiction Guard) todos declaram o **gatilho** no chamador e só mandam carregar o corpo depois que o gatilho bate. `work-feedback` inverteu isso. O custo é baixo por invocação e o default é `true`, então na maioria dos casos não há desperdício — mas o precedente vale mais que o número: a regra canônica escrita em `CLAUDE.md` hoje proíbe explicitamente a otimização.
- **Proposta:** distinguir *gate check* (o teste booleano) de *gate semantics* (o que cada valor significa, o clamp de `[60,3600]`, o fallback quando o arquivo falta). Permitir que `orchestration:247` carregue o teste — `grep -q '"work_feedback_active"[[:space:]]*:[[:space:]]*false' .dev-team-agents/user-data/credentials.local.json && skip` — e manter tudo o mais na skill. Ajustar `CLAUDE.md:172` de "Never restate the gate check" para "Never restate the gate semantics, loop mechanics, or table format; the caller may carry the one-line boolean test."
- **Impacto positivo:** 71 linhas → 1 linha nas rodadas em que a feature está desligada. Aplica-se aos 8 comandos que orquestram em background mais `software-architect` invocado direto. Ganho nulo quando a feature está ligada (o default), o que limita o valor prático — o retorno real é remover uma regra canônica que proíbe o padrão de lazy-load que o resto do repo usa.
- **Impacto negativo / risco:** um `grep` sobre JSON é frágil se o arquivo for reformatado (chave e valor em linhas separadas). Mitigação: usar o mesmo `python3 -c` de leitura que `project-context/SKILL.md:52-54` já usa para `preferences.json`, com fallback para "ativo". Segundo risco: mexer numa linha da tabela Canonical Rule Homes é exatamente o tipo de flexibilização que degrada com o tempo — a redação nova precisa ser específica ("o teste booleano, nada além dele"), não uma exceção genérica.
- **Esforço:** Baixo

### `pr.md` carrega 14 linhas verbatim do nudge do `/devteam:learn` que `audit.md` resolve em uma

- **Fingerprint:** `token-pr-md-14-line-verbatim-learn-nudge-while-audit-md-delegates-in-one-line`
- **Alvo:** `commands/pr.md`
- **Evidência:**
  - `commands/pr.md:140-152` — "## Post-create — Nudge `/devteam:learn` if not run this session" + bloco `bash` `cat .dev-team-agents/.learn-last-run 2>/dev/null` + citação de 1 linha + "Ask via `AskUserQuestion` (Yes / No). If yes, hand off by telling the user to invoke `/devteam:learn` (do not spawn it inline — it is a separate command with its own plan gate)." — 14 linhas / 718 bytes
  - `commands/merge.md:81-93` — bloco idêntico, palavra por palavra, sob "## Step 4 — Nudge `/devteam:learn` if not run this session"
  - `commands/audit.md:188` — "3. Nudge `/devteam:learn` per the merge.md Step 4 marker check (`.dev-team-agents/.learn-last-run`) — this report is a finalization signal even on **Report only**." — 1 linha
  - `CLAUDE.md:487` — "The canonical nudge implementation is `commands/merge.md` § Step 4 […] The following commands carry the same check at their own closing point — patch all of them together if the mechanism ever changes"
- **Problema:** o mesmo nudge existe em quatro formas na mesma janela de commits: cópia integral em `merge.md` (canônica), cópia integral **verbatim** em `pr.md`, uma linha densa reescrita em `refactor.md:162`, e uma delegação de uma linha em `audit.md:188`. `audit.md` prova que a forma comprimida funciona e é legível; `pr.md` é o único que paga o texto inteiro para dizer o mesmo.
- **Por que importa:** `CLAUDE.md:487` já admite o custo ao instruir "patch all of them together" — mas quatro variantes, duas delas idênticas e duas reescritas, é o cenário exato que a tabela Canonical Rule Homes existe para evitar. `commands/pr.md` está em 162 linhas contra um teto de 200 (`helpers/size-limits.sh`); as 14 linhas são 8,6% do orçamento do arquivo gasto numa citação.
- **Proposta:** substituir `commands/pr.md:140-152` pela forma de `audit.md:188` — uma linha delegando a `merge.md` § Step 4 —, e alinhar `commands/refactor.md:162` na mesma redação. `merge.md` permanece a única cópia integral.
- **Impacto positivo:** `pr.md` de 162 → **149 linhas** (−13, ~660 bytes), carregadas em toda invocação de `/devteam:pr`. Reduz de 4 para 2 as variantes do nudge (1 canônica + 3 delegações idênticas), o que torna "patch all of them together" um `sed` em vez de uma revisão manual de quatro redações.
- **Impacto negativo / risco:** delegar de comando para comando (`per the merge.md Step 4`) só resolve se o arquivo referenciado estiver acessível ao agente no momento — `audit.md` já assume isso, então o precedente existe, mas é uma resolução em tempo de execução que a forma inline não precisava. Em provider renderizado (opencode/Codex), o caminho `commands/merge.md` vira outro caminho; a referência precisa nomear o comando (`/devteam:merge`), não o arquivo-fonte.
- **Esforço:** Baixo

---

## LOW

Nenhum achado nesta severidade.

---

## Descartados por duplicação

| Candidato | Porta | Fingerprint colidido |
|---|---|---|
| `CLAUDE.md` em 602 linhas (era 586), ainda monolítico, +18 no delta sem nenhuma extração para `CLAUDE-md/` | Porta 5 (estado) | `token-claude-md-426-lines-still-monolithic-three-extractable-blocks-…` — registrado ✅ e reverificado 🔴 hoje na Fase 1 |
| `skills/shared/interaction-patterns/SKILL.md` 209 linhas carregada incondicionalmente por 32 comandos | Porta 5 (estado — conjunto aberto) | `token-interaction-patterns-209-lines-loaded-unconditionally-by-24-commands-…` |
| `skills/architecture/orchestration/SKILL.md` cresceu 377 → 391 linhas, ainda sem `references/` | Porta 5 (estado — conjunto aberto) | `token-orchestration-skill-377-lines-138-conditional-path-only-no-references-dir` |
| `skills/shared/project-context/SKILL.md` reafirma a tabela de exceção de testes, lida por 18 agentes | Porta 5 (estado — conjunto aberto) | `token-project-context-restates-scoped-test-exception-table-read-by-18-agents` |
| `commands/pr.md:99` entregava diff completo sem filtro ao tier `repetitive` | Porta 5 (estado — corrigido no delta, verificação é da Fase 1) | `token-pr-md-unbounded-full-diff-to-repetitive-tier-while-same-file-caps-git-log` |
| `02c-full-suite-guard.sh` injeta `additionalContext` por casamento de substring solto | Porta 5 (estado — conjunto aberto) | `token-02c-full-suite-guard-substring-match-injects-nudge-on-non-test-commands` |
| `skills/shared/token-efficiency/SKILL.md` 160 linhas eager em 18/18 agentes | Porta 5 (estado — reaberto em 2026-08-14) | `token-token-efficiency-skill-itself-154-lines-eager-loaded-by-all-17-agents-…` |
| `scripts/install.sh` em 1240 linhas (era 1086), sem decomposição | Porta 3 (semântica: mesmo alvo, mesma causa-raiz, mesma remediação) | `token-install-sh-503-lines-largest-single-script-not-fragmented-vs-stop-dispatcher-pattern-…` |
| `skills/shared/output-format/SKILL.md` 203 linhas × 9 sítios de carga (escopo genérico) | Porta 4 (escopo menor) — só retorna com o sub-escopo do § Plan Template, que é o achado MEDIUM acima | descarte anterior registrado em `_index.md:408` ("`output-format` 190×9") |
| `skills/shared/model-identity` 32 de 58 linhas são spec de formato inline | Porta 5 (estado — conjunto aberto) | `token-model-identity-32-of-58-lines-are-format-spec-and-examples-held-inline` |
| Cópias duplicadas do quiz de finalização de worktree entre `commands/commit.md:13-50` e `commands/merge.md:44-71` | Porta 3 (b + c: mesma causa-raiz "cascata de worktree restatada" e mesma remediação "delegar à skill canônica") | `token-worktree-isolation-block-7-lines-x-8-agents` |
| Forks de subprocesso antes de early-exit em sub-script de `PreToolUse` (padrão genérico) | Porta 2 → 3: o pré-filtro mecânico por basename (`02-graphify-hint`) devolve só `_index.md:330`, cujo alvo (`02c-full-suite-guard.sh`), causa-raiz (comentário enganoso) e remediação divergem — 0 de 3. **Não descartado**; segue como achado MEDIUM-HIGH #1, com nota de que o padrão já apareceu em `01-check-updates.sh` (fingerprint distinto, executado) | — |
