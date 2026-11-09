# Eixo D — Agentes e Skills — 2026-11-07

**Varredura:** delta `b64428b..HEAD` com prioridade em `agents/` (1 novo + 13 modificados),
`skills/shared` (3 novas + 23 modificadas), `skills/design/seo-optimization` (SKILL + 14
`references/`), `skills/architecture/orchestration`, `skills/security`, `skills/devops`.

Medições: **19 agentes** (máx. 211 linhas = exatamente `AGENT_LIMIT`, nenhum acima), **163
`SKILL.md` próprios** (máx. 414 = `migration-v1-to-v2`, abaixo de `SKILL_LIMIT=500`), **42
comandos** (máx. 199, abaixo de `COMMAND_LIMIT=200`). Gates no `HEAD`: `helpers/agent-lint.sh` →
`clean ✓`, `helpers/size-limits.sh` → `clean ✓` (só o warning advisory de `CLAUDE.md` em 600),
`helpers/orphan-skill-scan.sh` → `clean ✓`.

Checagens que saíram **limpas** (registro negativo): frontmatter agente por agente contra
`scripts/lib/tiers.json` (`name`/`tier`/`model`/`effort` + linha do `run-banner`) — zero
divergências, inclusive nos dois agentes do delta (`orchestrator` `reasoning/opus` sem `effort`,
correto pelo `_claude_note`; `seo-specialist` `frontend/sonnet`, correto); varredura mecânica de
frases ≥70 caracteres repetidas em ≥3 agentes — 15 clusters, **todos** delegações de uma linha
conformes às *Canonical Rule Homes* (`CLAUDE.md:183-232`), nenhuma regra reescrita nova;
`§ Conditional References` da skill de SEO × os 14 arquivos em `references/` — 14/14 alcançáveis.

Cruzamentos feitos: roster de `orchestration/SKILL.md` × `agents/` × `ROSTER_EXEMPT`;
`REVIEW_RESULT_AGENTS` × `REVIEWERS` do hook de SubagentStop × `review_triggers.REVIEW_AGENTS` ×
`docs/specs/task-board.md` § In Review; `PLAN_MODE_LOADERS` × agentes que de fato carregam
`plan-mode`.

**9 candidatos → 5 achados, 4 descartados por duplicação.** Os dois diretórios não rastreados
(`skills/security/third-party-security-skills/`, `skills/third-party/security-audit/`) foram
excluídos de toda evidência por não estarem no `HEAD`.

---

## HIGH

### O gate de SubagentStop exige o marcador `review-result` exatamente nos três casos em que a casa canônica manda não emitir nenhum, e o `findings=0` forçado fecha a janela como "passed"

- **Fingerprint:** `gov-supervision-gate-demands-review-marker-in-documented-no-marker-cases`
- **Alvo:** `scripts/hooks/lib/subagent-supervision.sh`
- **Evidência:** `scripts/hooks/lib/subagent-supervision.sh:36` — `REVIEWERS = {"qa-specialist", "code-reviewer", "backend-reviewer", "frontend-reviewer", "seo-specialist"}`; `:56` — `if agent in REVIEWERS and MARKER not in message:` (sem nenhuma condição sobre o tipo de passagem); `:81-82` — "Your final message has no review-result marker. End it with `<!-- review-result: findings=N -->` … (N = the number of findings in your Findings Table; **0 when clean**)". Contra `skills/shared/review-result/SKILL.md:26` — "A pass that could not run (missing environment, nothing to review) **emits no marker** — say why instead."; `:28` — "A routing-only pass (`code-reviewer` in router mode, which only delegates) **emits no marker**: the specialists it spawns each emit theirs."; e `git show HEAD:agents/seo-specialist.md:90` — "An advisory answer is not a review and **emits none**." Modo router é alcançável por desenho: `agents/code-reviewer.md:33` — "`BOTH` → emit the router's parallel routing message and stop". Consequência no quadro: `docs/specs/task-board.md:413` — "`Result findings = 0` | Window resolved (`resolution: "passed"`); its tasks go to Done if completed", enquanto `:388` reafirma "A routing-only pass … emits no marker".
- **Problema:** o gate de supervisão da ADR-0062 (decisão 4) testa só `agent in REVIEWERS`, sem olhar que tipo de passagem foi. Os três casos documentados de ausência legítima do marcador — passagem que não pôde rodar, `code-reviewer` em modo router `BOTH`, e `seo-specialist` em postura advisory — são bloqueados e instruídos a emitir `findings=N`, com a própria mensagem do hook sugerindo "`0 when clean`".
- **Por que importa:** o agente devolve o relatório de novo com `findings=0`, e `task-board.md:413` resolve a janela como `"passed"`, mandando as tarefas para Done. **Uma QA que não conseguiu rodar e um router que apenas delegou passam a ler como revisão aprovada** — exatamente o falso positivo que `task-board.md:659` item (5) ("an unread reviewer never turns another's zero into a pass") foi escrito para impedir, e o mesmo mecanismo do achado aberto `agent-security-specialist-outside-review-result-set-task-board-blind-to-findings`. O `stop_hook_active` impede loop, mas não impede o marcador falso; e toda passagem advisory de `seo-specialist` (spawn condicional em `commands/frontend.md:23` e `commands/fullstack.md:21`) paga um re-relatório completo a mais.
- **Proposta:** condicionar a exigência do marcador em `:56` à presença de um sinal de revisão executada no relatório (Findings Table ou veredito), ou aceitar uma linha explícita de no-marker (`<!-- review-result: none reason=… -->`) que o scan do quadro leia como `unread`; e alinhar a mensagem de `:81-82` para nunca sugerir `0` quando a passagem não rodou.
- **Impacto positivo:** elimina a conversão silenciosa de "não rodou"/"só roteou" em "aprovado" nas 3 rotas documentadas; devolve o `result not read` de `task-board.md:388` ao seu papel; corta um round-trip forçado por spawn advisory de `seo-specialist`.
- **Impacto negativo / risco:** o gate deixa de ser um teste de uma linha e passa a depender de heurística sobre o conteúdo do relatório, o que é mais frágil; um revisor que de fato esqueceu o marcador e não tem Findings Table pode escapar. Introduzir uma forma `none` cria um **terceiro formato de marcador** para manter em sincronia entre o hook, a skill e `docs/specs/task-board.md`.
- **Esforço:** Médio

## MEDIUM-HIGH

### O sinal de detecção do Session Guard do orquestrador ("sem ferramenta de spawn ⇒ fui spawnado") não pode disparar no Claude Code, pela própria premissa da ADR-0062

- **Fingerprint:** `agent-orchestrator-session-guard-signal-fails-under-nested-spawn`
- **Alvo:** `agents/orchestrator.md`
- **Evidência:** `agents/orchestrator.md:21` — "You only work as the main session (ADR-0062). **If you have no tool to spawn agents, you were started as a subagent**: stop, change nothing, and return one line saying the orchestrator runs only as the main session". Contra `docs/development/adrs/0062-….md:19` — "Nesting is no longer the obstacle: **Claude Code lets a subagent spawn subagents up to three levels deep.**" e `:39-40` — "`mode: primary`, so its `task` tool cannot spawn it; **Claude Code and Codex can still spawn it by name, and its Session Guard is the runtime defense**: with no spawn tool it stops and says so."
- **Problema:** a ADR declara, no mesmo documento, que (a) no Claude Code um subagente *tem* ferramenta de spawn e (b) o Session Guard é a defesa de runtime para o orquestrador spawnado no Claude Code. As duas não podem ser verdadeiras: um `orchestrator` spawnado via `Task` no Claude Code recebe a ferramenta de spawn, a condição de `:21` é falsa, e o guard não dispara. A defesa só funciona onde o problema já não existe (opencode, que bloqueia o spawn por `mode: primary`).
- **Por que importa:** a proteção declarada é inoperante no provider principal. `helpers/agent-lint.sh:449-459` (`check_orchestrator_not_spawned`) cobre apenas o que está escrito em `agents/`, `commands/` e `skills/` do repositório — não cobre um `subagent_type: orchestrator` digitado pelo usuário ou escrito num `.agents/` de projeto. Nesse caso o orquestrador spawnado roda silenciosamente e produz exatamente a falha que a ADR usou para rejeitar a alternativa: "No question tool and only its final message returns: every decision becomes a relay and the user loses wave-level visibility". A ADR documenta como verdade corrente uma defesa que não existe.
- **Proposta:** trocar o sinal de `:21` por um que realmente distinga as duas situações (presença da ferramenta de pergunta ao usuário combinada com a de spawn, ou um marcador passado por `commands/orchestrate.md` / pela preferência `orchestrator_default`), e corrigir `0062:39-40` para dizer que no Claude Code a defesa é o lint + a convenção, não o guard.
- **Impacto positivo:** fecha o único caminho em que o orquestrador roda como subagente sem ninguém perceber; alinha a ADR ao comportamento real em 1 de 3 providers.
- **Impacto negativo / risco:** qualquer sinal alternativo tem falso positivo próprio — a ADR já registra que a ferramenta de pergunta falta em *toda* execução não interativa, persona ou não, então condicionar nela faria o orquestrador se recusar a rodar em CI e no modo default do Codex. Se o novo sinal for um marcador vindo do comando, a ativação por `orchestrator_default` (que não lê `commands/orchestrate.md`) precisa de um segundo caminho para fornecê-lo.
- **Esforço:** Médio

### `orchestrator` carrega `plan-mode` mas está fora de `PLAN_MODE_LOADERS`, e na rota `orchestrator_default` ele é o único portador do ponteiro

- **Fingerprint:** `agent-orchestrator-missing-from-plan-mode-loaders-gate`
- **Alvo:** `helpers/agent-lint.sh`
- **Evidência:** `helpers/agent-lint.sh:374` — `PLAN_MODE_LOADERS="software-architect backend-developer frontend-developer mobile-developer database-specialist devops-specialist code-reviewer"` (7 nomes), contra `grep -ln "plan-mode/SKILL.md" agents/*.md` → **8** arquivos, com `agents/orchestrator.md:32` — "| `skills/shared/plan-mode/SKILL.md` | Plan before execution, approval, Task List Mirroring |". E `git show HEAD:CLAUDE.md:206` — "`agent-lint.sh` (`PLAN_MODE_LOADERS`, `PLAN_MODE_COMMAND_EXEMPT`) **fails when the section, an agent's plan-mode load** or a plan-gated command's pointer disappears".
- **Problema:** a persona nova é um agente que planeja (o § Route conduz `/devteam:plan` e `/devteam:sprint`, e o § Supervise roda entre waves), carrega `plan-mode` e não está na lista que o gate percorre. A linha 206 do `CLAUDE.md` enuncia a cobertura como completa ("an agent's plan-mode load"), o que deixou de ser verdade quando `agents/orchestrator.md` entrou.
- **Por que importa:** `plan_gate: "conditional"` em `commands.json` faz o gate cobrir `commands/orchestrate.md:12` ("Every plan you present follows `skills/shared/plan-mode/SKILL.md`"), mas a ADR-0062 decisão 3 cria uma **segunda rota de ativação** — `orchestrator_default` escrevendo `"agent": "orchestrator"` em `.claude/settings.local.json` — em que `commands/orchestrate.md` nunca é lido. Nessa rota `agents/orchestrator.md:32` é o único ponteiro para `plan-mode`, e se ele cair **nenhum gate falha**: a sessão default perde § Task List Mirroring, que é "the only way a plan reaches the task board".
- **Proposta:** acrescentar `orchestrator` a `PLAN_MODE_LOADERS` em `helpers/agent-lint.sh:374` (o laço de `:390-396` já valida existência do arquivo e presença do load, sem mudança de código).
- **Impacto positivo:** uma palavra fecha a lacuna; o gate volta a corresponder ao que `CLAUDE.md:206` afirma, e a rota `orchestrator_default` passa a ter proteção equivalente à rota por comando.
- **Impacto negativo / risco:** `PLAN_MODE_LOADERS` é mais uma lista de agentes mantida à mão, do mesmo gênero já registrado em `agent-review-agent-roster-hardcoded-in-five-places-no-canonical-home`; adicionar uma entrada não resolve o padrão e o próximo agente que planejar vai repetir a omissão. Fixa também o load em `orchestrator.md:32` como contrato, encarecendo um refactor futuro que mova a tabela de loads da persona para a skill de orquestração.
- **Esforço:** Baixo

### O § Route do orquestrador não tem caminho executável para trabalho de arquitetura: nem linha de comando, nem linha no Agent Roster

- **Fingerprint:** `agent-orchestrator-route-has-no-path-to-architecture-work`
- **Alvo:** `agents/orchestrator.md`
- **Refina:** `flow-orchestrator-route-table-covers-10-of-42-commands-no-gate`
- **Evidência:** a tabela `:44-51` fecha com `:51` — "| Anything else | Orchestration § Orchestration Flow, **with agents from the Agent Roster only** |". O Agent Roster tem 16 linhas e **nenhuma é `software-architect`** (`helpers/agent-lint.sh:442` — `ROSTER_EXEMPT=("software-architect" "setup-assistant" "orchestrator")`), enquanto `skills/architecture/orchestration/SKILL.md:178` — "Every `subagent_type` you pass **MUST appear verbatim in the Agent Roster** above."
- **Problema:** o pai registra que 32 comandos caem no catch-all. Este sub-escopo, estritamente contido e não descrito no pai, é que para **trabalho de arquitetura o catch-all não tem saída alguma**: as três opções restantes são todas proibidas — passar `software-architect` viola § Spawn Integrity check 2, fazer o trabalho ele mesmo viola `:8` ("You never write implementation code yourself" e o papel de coordenador), ou devolver ao usuário um pedido que tem comando próprio (`/devteam:architect`, `/devteam:adr`).
- **Por que importa:** é o único ramo do § Route que não é apenas subótimo, e sim **inexecutável**. Para os demais 31 comandos o orquestrador consegue improvisar com o roster (perdendo os gates, que é o defeito do pai); para arquitetura e ADR ele não tem nem agente elegível. Nenhum gate cobre: `check_orchestration_roster` valida roster × `agents/`, e nada valida § Route × `commands/`.
- **Proposta:** acrescentar ao § Route a linha "arquitetura, trade-off, ADR → `/devteam:architect` ou `/devteam:adr`" (e, no mesmo passe, `dba`, `devops`, `design`, `seo`, `docs`, `spec`, `release-qa`), deixando "Anything else" só para o que não tem comando.
- **Impacto positivo:** fecha o único ramo inexecutável da tabela; de passagem dá rota a ~13 fluxos hoje sem destino.
- **Impacto negativo / risco:** engorda um agente hoje em 81 linhas e cria uma segunda cópia do mapa pedido→comando, que já vive em `commands.json` (`description`, `related`) e parcialmente em `skills/shared/auto-routing/SKILL.md:37-57` — mais um par para divergir, sem gate que o cruze. A correção estrutural (§ Route apontando para um mapa único) é a do fingerprint-pai; esta é a versão barata que torna o ramo executável.
- **Esforço:** Baixo

## LOW-MEDIUM

### Os comentários que justificam `AGENT_LIMIT=211` e o status *blocking* do `size-limits` declaram contagens de agentes, comandos e skills que já não são as da árvore

- **Fingerprint:** `ref-size-limits-and-ci-lint-comments-state-stale-agent-command-counts`
- **Alvo:** `helpers/size-limits.sh`
- **Evidência:** `helpers/size-limits.sh:36` — "it is identical in shape across **all 17 agents** and the renderer rewrites parts of it per provider"; `.github/scripts/ci/01-lint.sh:87-88` — "NOT blocking today: **11 of 17 agents** exceed the 200-line agent cap. Enforcing now would fail every PR regardless of content."; `:92-93` — "PROMOTED 2026-07-31: every agent, skill and command is now under its declared cap (**17/17 agents, 25/25 commands, 138/138 skills**)". Medido no `HEAD`: `ls agents/*.md | wc -l` → **19**, `ls commands/*.md | wc -l` → **42**, `find skills -name SKILL.md -not -path 'skills/third-party/*' | wc -l` → **163**. A substância do comentário de `:36` continua verdadeira: `agents/orchestrator.md` carrega os três blocos citados (`:5 model:`, `:14 <!-- run-banner -->`, `:79 ## Before You Finish`).
- **Problema:** três comentários que são a justificativa escrita de um limite numérico e de uma decisão de bloqueio no CI citam contagens defasadas em 2 agentes, 17 comandos e 25 skills. O parágrafo de `01-lint.sh:87-88` ainda descreve o estado anterior à promoção que o parágrafo seguinte anuncia, lado a lado.
- **Por que importa:** não altera a aritmética de `AGENT_LIMIT` (o bloco de 11 linhas é por agente, não total) nem o exit code — `size-limits` sai 0 e `agent-lint` sai limpo. O custo é de leitura: quem avaliar uma demoção do step, ou um aumento do teto, decide a partir da condição registrada ("11 de 17 excedem", "17/17 sob o teto"), que não descreve mais a árvore. O bloco de `:30-45` diz explicitamente "Raise this ONLY when a new mandatory block is added to every agent" — é regra de governança decidida sobre um número errado. Nenhum gate conta esses números.
- **Proposta:** atualizar as três contagens para 19/42/163 e remover o parágrafo pré-promoção de `01-lint.sh:87-88`, que só sobrevive como histórico contraditório do parágrafo abaixo dele; ou reescrever `:36` como "across every agent", que não volta a driftar.
- **Impacto positivo:** elimina 3 afirmações falsas na justificativa escrita de um teto e de um gate bloqueante.
- **Impacto negativo / risco:** contagens literais em comentário voltam a envelhecer no próximo agente ou comando adicionado, e não há gate que as valide — a correção compra alguns meses, não resolve a classe. A forma genérica ("every agent") remove um sinal útil: é justamente a contagem que torna visível que o comentário envelheceu. E remover o parágrafo histórico apaga o registro de por que o step um dia foi advisory.
- **Esforço:** Baixo

## Descartados por duplicação

- **Coluna `Tier` de `docs/agents.md:28` dá `repetitive` a `backend-test-specialist` (real: `backend-exec`)** — portas 1 e 2 positivas; porta 3: arquivo, causa raiz e remediação idênticos a `ref-docs-agents-md-tier-column-stale-backend-test-specialist-listed-repetitive` (HIGH, aberto). 3 de 3.
- **`CLAUDE.md:137` enumera 8 coding agents com `## Worktree Isolation`, e `grep -c "^## Worktree Isolation" agents/*.md` devolve 9** — porta 3: mesmo alvo, mesma causa (lista fechada não tocada quando `seo-specialist` entrou) e mesma remediação de `docs-sync-claude-md-coding-agents-list-omits-seo-specialist` (MEDIUM, aberto). 3 de 3.
- **`seo-specialist` com `## Worktree Isolation` mas fora do contrato de coding agent (sem `comments-policy`, sem `reuse-guidelines`)** — coberto por `agent-seo-specialist-outside-coding-agent-contract` (MEDIUM, aberto). 3 de 3.
- **`skills/architecture/orchestration/SKILL.md` em 410 linhas sem `references/` e `skills/shared/migration-v1-to-v2/SKILL.md` em 414** — ambos sob `SKILL_LIMIT=500`; tema de tamanho de skill registrado e re-medido no banco (a nota "`orchestration/SKILL.md` sem `references/`" já consta como descartada na Porta 3 de um pass anterior). **Porta 5.**
- **Roster de revisores replicado em `agent-lint.sh:117`, no `REVIEWERS` do hook de supervisão, em `review_triggers.REVIEW_AGENTS`, nas regexes de task board e na spec** — `agent-review-agent-roster-hardcoded-in-five-places-no-canonical-home` e `auto-review-agents-regex-duplicated-in-two-task-board-hooks-no-drift-gate`, ambos abertos. **Porta 5.** O achado HIGH acima é outro eixo (o gate ignora o *tipo de passagem*, não a lista), com causa e remediação distintas.

**Encaminhado ao Eixo B (fora do escopo deste eixo):** `docs/agents.md` não menciona `orchestrator`
em nenhuma linha e `README*` afirmam "18 agents" contra 19 arquivos. Passou as portas, mas o alvo é
documentação de referência, não desenho de agentes/skills — registrado como
`docs-sync-agent-reference-omits-orchestrator-and-18-agent-count-claims`.
