# Eixo D — Agentes e skills

**Método.** Varredura priorizada pelo delta `3fbe371..c03f898`, com leitura integral de
`git show 21fceb4` (único commit da janela que tocou `agents/` ou `skills/`) e dos três arquivos
que ele alterou. A partir daí, três eixos de checagem: (1) confronto de cada regra nova contra a
tabela *Canonical Rule Homes — Delegate, Never Restate* do `CLAUDE.md`; (2) alcance real de cada
regra (`grep` de quem carrega a skill que a hospeda, em `agents/`, `commands/` e `skills/`);
(3) classes que os linters não cobrem — `helpers/agent-lint.sh` e `helpers/size-limits.sh` estão
ambos limpos ✓, então foram auditados os invariantes que eles **não** medem: contradição semântica
entre skills, número documentado do teto vs. número enforçado, e superfícies de spawn que nenhuma
skill alcança. Banners e seções `## Before You Finish` foram extraídos dos 18 agentes e conferidos
um a um contra `scripts/lib/tiers.json` — **zero divergências**, nenhum achado nessa categoria.
Todos os candidatos passaram pelas portas literal, pré-filtro mecânico por basename, semântica e de
estado antes de virarem achado.

---

## HIGH

### `token-efficiency/strategies.md` ensina fire-and-forget e `TaskOutput` para shell de background, contradizendo a disciplina que `21fceb4` acabou de criar

- **Fingerprint:** `skill-token-efficiency-background-mgmt-contradicts-orchestration-discipline`
- **Alvo:** `skills/shared/token-efficiency/strategies.md`
- **Evidência:**
  `skills/shared/token-efficiency/strategies.md:332` — "`Bash(command=\"npm run build\", run_in_background=true)`";
  `strategies.md:335` — "`# Tell user once with the ID, then don't poll`";
  `strategies.md:339` — "`TaskOutput(task_id=\"abc123\")`";
  `strategies.md:342` — "Avoid repeated polling — each check consumes context. Let the user decide when to check results."
  Contra `skills/architecture/orchestration/SKILL.md:253-255` — "**A background command is not fire-and-forget.** Once started, either await it inline (if the answer is needed before continuing) or call `Monitor` so its completion produces a notification. Starting it and moving on without either is the Bash-side version of the gap Spawn Integrity check 5 closes for subagents."
- **Problema:** duas skills dão instruções opostas sobre o mesmo primitivo. `strategies.md` manda
  iniciar o processo em background, avisar o usuário e **não** acompanhar ("let the user decide when
  to check"); `orchestration` proíbe exatamente esse comportamento e exige `Monitor`. Além disso, o
  bloco de exemplo lê o resultado de um shell de background com `TaskOutput(task_id=…)` — ferramenta
  de spawn de Task, não de comando Bash em background, que devolve um shell id lido por
  `Monitor`/`BashOutput`. O exemplo está documentado como verdade e não funciona.
- **Por que importa:** `skills/shared/token-efficiency` é carregada por **18 de 18 agentes**
  (`grep -c token-efficiency agents/*.md` → 18 arquivos), e `strategies.md` é a referência apontada
  para "padrões de bash detalhados" (`SKILL.md:160`). A regra nova mora em
  `skills/architecture/orchestration/SKILL.md`, carregada por **um** agente
  (`software-architect`, e ainda assim por load condicional). O resultado no HEAD é que a orientação
  que perde vale para 18 agentes e a que vence vale para 1: qualquer agente que rode build, migração
  ou suíte em background segue a versão errada, e a versão errada nomeia a ferramenta errada.
- **Proposta:** reescrever `## Background Process Management` em `strategies.md` para `Monitor` +
  `BashOutput` (a instrução correta), remover "don't poll / let the user decide" e apontar a regra
  para a casa canônica; ou mover a *Background Process Discipline* para `token-efficiency` e deixar
  `orchestration` só referenciando-a.
- **Impacto positivo:** elimina a contradição e leva a regra de disciplina de background de 1 para
  18 agentes de alcance, corrigindo de quebra uma chamada de ferramenta inválida documentada.
- **Impacto negativo / risco:** `Monitor` é primitivo de provider — a instrução passa a citar uma
  ferramenta que opencode/Codex podem não expor, exigindo um guard de disponibilidade (que hoje
  `orchestration:234-236` tem e a versão reescrita precisará repetir). Também aumenta ligeiramente o
  custo de tokens do fluxo, já que "não acompanhe" é mais barato que acompanhar.
- **Esforço:** Baixo

### `CLAUDE.md` documenta teto de 205 linhas por agente enquanto `size-limits.sh` enforça 211

- **Fingerprint:** `agent-line-cap-205-documented-in-claude-md-vs-211-enforced-by-size-limits`
- **Alvo:** `CLAUDE.md` (§ Authoring Standards → Agents; § File Structure)
- **Evidência:**
  `CLAUDE.md:92` — "`helpers/size-limits.sh` enforces 205 — the extra 5 lines are the fixed-size run-banner block every agent carries, not content budget. Do not raise that ceiling again to make a long agent fit.";
  `CLAUDE.md:311` — "`size-limits.sh             ← agents 205 (200 content + 5 run-banner) · commands 200 · skills 500`";
  contra `helpers/size-limits.sh:44` — "`AGENT_LIMIT=211`" e `helpers/size-limits.sh:34-35` —
  "200 lines of agent CONTENT, plus 11 lines of fixed-size model-identity boilerplate every agent carries".
- **Problema:** o número e a decomposição estão errados nos dois pontos do `CLAUDE.md`. O teto real é
  **211** (200 + 11), elevado em `705acd1` (2026-07-31, "Ceiling moves 205 -> 211, the exact size of
  the mandatory boilerplate") — commit que tocou 17 agentes, `agent-lint.sh` e `size-limits.sh`, e
  **não** tocou o `CLAUDE.md`. A divergência vive há 14 dias.
- **Por que importa:** o `CLAUDE.md` é a instrução carregada em toda sessão deste repositório, e é a
  fonte que um autor consulta antes de decidir se corta conteúdo de um agente. Hoje ele diz que
  `software-architect.md`, `qa-specialist.md` e `frontend-developer.md` — todos com exatamente 211
  linhas — estouraram o limite em 6 linhas, quando na verdade estão colados no teto com zero folga.
  Pior: a frase "Do not raise that ceiling again" descreve como invariante um teto que já foi
  levantado, o que retira do texto a capacidade de sinalizar a próxima elevação indevida.
- **Proposta:** atualizar `CLAUDE.md:92` e `:311` para 211 (200 conteúdo + 11 de boilerplate
  obrigatório), preservando a condição já escrita em `size-limits.sh:41-43` — elevar somente quando
  um novo bloco obrigatório for adicionado a todos os agentes, e exatamente pelo tamanho dele.
- **Impacto positivo:** remove a única afirmação numérica falsa sobre o gate de tamanho; devolve
  sentido à regra "não eleve de novo" e torna visível que três agentes estão sem folga.
- **Impacto negativo / risco:** o `CLAUDE.md` passa a repetir um número que mora no script — mais um
  espelho para manter sincronizado, e nenhum gate automatizado verifica esse par (a próxima elevação
  reabre a divergência). A alternativa — fazer o texto citar o script sem número — perde a
  informação que o autor busca sem abrir o arquivo.
- **Esforço:** Baixo

---

## MEDIUM-HIGH

### `software-architect` reescreve inline os checks 4 e 5 do Spawn Integrity e perde o guard de disponibilidade do `ScheduleWakeup`

- **Fingerprint:** `agent-software-architect-inlines-spawn-integrity-4-5-no-availability-guard`
- **Alvo:** `agents/software-architect.md`
- **Evidência:**
  `agents/software-architect.md:89` — "**Before ending a turn with an unreturned spawn, call `ScheduleWakeup`** instead of going silent (Spawn Integrity check 5, Auto-reactivation). On wakeup, check `TaskList`/`TaskGet`/`TaskOutput` first; if still no return, resume with `SendMessage` rather than re-spawning or fabricating progress. Cap two attempts per agent, then surface it to the user as a blocker.";
  contra `skills/architecture/orchestration/SKILL.md:216` — "If `ScheduleWakeup` **is available**, call it before ending the turn: `delaySeconds` in the 1200–1800s range…" e `orchestration/SKILL.md:234-236` — "If `ScheduleWakeup` is not available in the current context, this check cannot be satisfied — fall back to check 4's reactive behavior and say so if asked, rather than claiming a checkback is scheduled when none was.";
  regra violada: `CLAUDE.md:165` — "Spawn integrity … | `skills/architecture/orchestration/SKILL.md` § Spawn Integrity | Load it and delegate. **Never write a second \"verify the spawn\" rule**".
- **Problema:** a linha 89 (introduzida por `21fceb4`) não delega — ela reexecuta o procedimento
  inteiro do check 5 em quatro orações: quando chamar, o que checar no wakeup, como retomar e qual o
  teto de tentativas. É a segunda cópia que a tabela de casas canônicas proíbe, e já nasce divergente:
  o corpo manda chamar `ScheduleWakeup` incondicionalmente, enquanto a skill condiciona à
  disponibilidade da ferramenta e define o fallback explícito para quando ela não existe. A faixa
  `delaySeconds` de 1200–1800s também só existe na skill.
- **Por que importa:** o corpo do agente é lido sempre; a skill de orquestração é *load condicional*
  (`agents/software-architect.md:38`, linha "Delegating implementation to subagents"). Numa rodada em
  que o arquiteto não carregue a skill — ou num provider sem `ScheduleWakeup` — a única instrução
  vigente é a versão sem guard, que produz exatamente o comportamento que `orchestration:236` proíbe:
  "claiming a checkback is scheduled when none was". Nenhum linter compara corpo de agente com skill;
  `agent-lint.sh` só verifica frontmatter, banner, identidade de skill e roster.
- **Proposta:** reduzir as linhas 88–89 a um único bullet de delegação ("Status e reativação de spawns
  seguem `orchestration` § Spawn Integrity, checks 4 e 5 — carregue antes de delegar"), deixando
  procedimento, faixa de delay e fallback só na skill.
- **Impacto positivo:** elimina a divergência já existente entre as duas cópias, devolve ~4 linhas ao
  orçamento de um agente que está exatamente no teto (211/211) e restaura a regra da tabela canônica.
- **Impacto negativo / risco:** perde-se a redundância deliberada de ter a regra no corpo, que é
  justamente o argumento que `skills/shared/model-identity/SKILL.md:19` usa para justificar repetir o
  banner de fechamento — uma instrução só na skill condicional pode não ser lida na rodada em que
  importa. Se a delegação for adotada, o load da skill de orquestração deveria deixar de ser
  condicional para o arquiteto.
- **Esforço:** Baixo

---

## MEDIUM

### Nenhum dos 34 comandos carrega a skill de orquestração — Spawn Integrity alcança 1 das ~16 superfícies que dão spawn

- **Fingerprint:** `skill-orchestration-spawn-integrity-unreachable-from-devteam-commands`
- **Alvo:** `commands/*.md` × `skills/architecture/orchestration/SKILL.md`
- **Evidência:**
  `grep -rn "architecture/orchestration" commands/` → **nenhum resultado**; a única ocorrência da
  palavra é prosa: `commands/architect.md:22` — "…design patterns, and orchestration of implementation agents.";
  ao mesmo tempo os comandos dão spawn direto: `commands/backend.md:14` — "**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT write code directly in the main context — always delegate.";
  e carregam apenas a parte de economia de relatório: `commands/backend.md:16` — "Every Task spawn prompt below MUST end with, verbatim: \"Before your last paragraph, emit your run-banner table under **Ran on:**…\"".
- **Problema:** os cinco checks de Spawn Integrity (preflight sem Task tool, validação de nome contra
  o roster, banner como única prova de execução, liveness, auto-reativação) moram numa skill que
  nenhum comando carrega. O que os comandos replicaram foi só o parágrafo do § *Subagent Report
  Economy*, copiado literalmente em 15+ arquivos. `orchestration/SKILL.md:283` inclusive reconhece a
  cópia — "Every `commands/*.md` file that spawns an agent carries this exact line inline" — mas nada
  equivalente existe para os checks.
- **Por que importa:** `/devteam:backend`, `/devteam:fullstack`, `/devteam:review` e companhia dão
  spawn a partir do contexto principal, onde o mesmo silêncio de subagente que `21fceb4` foi corrigir
  ocorre igual. No HEAD, um `/devteam:fullstack` com quatro spawns paralelos não tem instrução de
  liveness, não tem checkback agendado, e sua tabela de resumo pode ser preenchida de memória —
  precisamente o que `CLAUDE.md:165` proíbe ("never let a summary template ask for a list of agents
  from memory").
- **Proposta:** adicionar uma linha de load de `skills/architecture/orchestration/SKILL.md` §
  Spawn Integrity nos comandos que dão spawn de agente, ou extrair os checks 1–5 para uma skill
  pequena e dedicada que comandos e arquiteto carreguem em comum.
- **Impacto positivo:** leva a integridade de spawn (incluindo liveness e auto-reativação) de 1 para
  ~16 superfícies, sem uma segunda cópia da regra.
- **Impacto negativo / risco:** cada comando passa a carregar uma skill de 377 linhas para usar ~90 —
  custo de tokens real em todo `/devteam:*`, o que empurra para a extração de uma skill menor e,
  portanto, para um arquivo novo a manter. Comandos também têm teto de 200 linhas
  (`helpers/size-limits.sh:50`), e vários já estão perto dele.
- **Esforço:** Médio

### `orchestration` reescreve a exceção da execução escopada de testes que o `CLAUDE.md` manda nunca reescrever

- **Fingerprint:** `skill-orchestration-restates-scoped-test-execution-exception`
- **Alvo:** `skills/architecture/orchestration/SKILL.md`
- **Evidência:**
  `skills/architecture/orchestration/SKILL.md:68-70` — "never instruct a full-suite run… Only relay a full-suite run when the user asked for one in this session — and then say so explicitly in the spawn prompt.";
  duplicando `skills/shared/scoped-test-execution/SKILL.md:20` — "When you spawn a subagent, never write \"run the tests\" unqualified into the prompt, and never instruct a full-suite run. State the touched scope and let the subagent derive its own blast radius. Relay a full run only when the user asked for one in this session, and say so explicitly.";
  regra violada: `CLAUDE.md:166` — "…never restate the exception, and never add a second escalation criterion (suite speed, refactor width, shared code)".
- **Problema:** a skill de destino já tem uma seção `## Orchestrator Rule` escrita para exatamente
  esse público (`scoped-test-execution/SKILL.md:18-20`), e `orchestration` a repete parafraseada no
  passo 4 do Autonomous Sprint. As duas versões coincidem hoje, mas são duas superfícies de edição
  para uma regra que o `CLAUDE.md` declara ter casa única — e a exceção ("only when the user asked in
  this session") é justamente a parte que o texto manda não reescrever.
- **Por que importa:** custo de manutenção concreto e assimétrico: um ajuste na exceção feito na casa
  canônica não chega ao passo 4 do sprint autônomo, que é o caminho executado quando o usuário pede
  "faça tudo sozinho" — o modo em que ninguém está olhando para pegar a divergência.
- **Proposta:** reduzir o passo 4 a "Execução escopada de testes — siga
  `skills/shared/scoped-test-execution/SKILL.md` § Orchestrator Rule ao montar cada prompt de spawn",
  sem repetir a condição nem a exceção.
- **Impacto positivo:** uma casa só para a exceção; −3 linhas numa skill de 377 que já é a segunda
  maior do repositório.
- **Impacto negativo / risco:** o sprint autônomo passa a depender de o orquestrador realmente
  carregar `scoped-test-execution` no momento do spawn; hoje a regra está inline no ponto de uso, que
  é a posição mais confiável. Vale só se o load da skill estiver garantido pelo `project-context`.
- **Esforço:** Baixo

---

## LOW-MEDIUM

### Regra geral de paralelismo de chamadas Bash mora dentro da skill de escopo de testes, fora do que a sua `description` anuncia

- **Fingerprint:** `skill-scoped-test-execution-hosts-general-parallel-bash-rule-off-topic`
- **Alvo:** `skills/shared/scoped-test-execution/SKILL.md`
- **Evidência:**
  `skills/shared/scoped-test-execution/SKILL.md:63-65` — "## Run Independent Verification Commands in Parallel … issue them as **separate Bash tool calls in the same message**, not chained in one shell with `;`/`&&`. … This is the same \"no dependency → parallel tool calls\" rule this repo already applies to agent spawning; it applies equally to your own Bash calls within one task.";
  contra a própria `description` em `scoped-test-execution/SKILL.md:3` — "Run only tests covering the touched code; full suite only on explicit user request.";
  e `grep -rln "separate Bash tool calls" skills/ agents/ commands/` → **um único arquivo**, este.
- **Problema:** a única formulação da disciplina de paralelismo de chamadas Bash do repositório está
  arquivada dentro de uma skill cujo nome, `name:` e `description` tratam de outro assunto. O
  índice de skills sempre carregado — alimentado justamente pela `description` — não sinaliza que a
  regra existe ali.
- **Por que importa:** a regra de fato alcança todos os agentes (o `project-context` torna o load
  obrigatório), então não há falha funcional; o custo é de descoberta e de duplicação futura. Quem
  procurar "como paralelizar chamadas de ferramenta" não acha, e a saída natural é escrever uma
  segunda cópia noutro lugar — o padrão que a tabela de casas canônicas do `CLAUDE.md` existe para
  evitar. O `21fceb4` já ilustrou o risco ao criar uma terceira seção sobre concorrência
  (`orchestration` § Background Process Discipline) sem cruzar com esta.
- **Proposta:** mover a seção para `skills/shared/token-efficiency/SKILL.md` (casa natural de
  disciplina de chamadas de ferramenta, também de load obrigatório) e deixar em
  `scoped-test-execution` uma linha de referência; ou, mantendo-a onde está, citá-la na
  `description` dentro do orçamento de 95 caracteres.
- **Impacto positivo:** a regra passa a ser encontrável pelo assunto que ela trata e ganha vizinhança
  com as duas outras regras de concorrência, reduzindo a chance de uma quarta cópia.
- **Impacto negativo / risco:** mover perde o contexto que a torna concreta hoje ("teste escopado +
  lint na mesma mensagem"), e `token-efficiency/SKILL.md` cresce; se em vez disso a `description`
  mudar, ela passa a anunciar duas regras em 95 caracteres e fica menos precisa como gatilho.
- **Esforço:** Baixo

---

## LOW

Nenhum achado original nesta faixa.

---

## Descartados por duplicação

| Candidato | Porta que rejeitou | Motivo |
|---|---|---|
| `skills/architecture/orchestration/SKILL.md` com 377 linhas, segunda maior do repo, sem extração para `references/` | Porta 3 (semântica) | Mesma causa raiz e mesma remediação de `skill-shared-migration-v1-to-v2-437-lines-largest-in-repo-…` (conjunto **aberto**) e de `skill-architecture-graphql-235-lines-…` / `skill-integrations-gotrue-225-lines-…` — "skill grande sem `references/`". 2 de 3 atributos coincidem (causa + remediação); só o alvo difere. Além disso 377 < 500 e `size-limits.sh` está limpo ✓ |
| Divergência de redação da seção `## Before You Finish` entre os 18 agentes | Porta 4 / evidência | Não reproduz: as 18 seções são **byte-idênticas** (extraídas e comparadas uma a uma). Sem achado |
| Divergência de banner vs. `tiers.json` (`agent_effort`) | Porta de evidência | Não reproduz: os 18 banners batem com `scripts/lib/tiers.json`, incluindo os cinco `low` de `agent_effort` (`backend-test-specialist`, `frontend-test-specialist`, `database-specialist`, `devops-specialist`, `qa-specialist`) |
| Roster de `orchestration` sem `software-architect` e `setup-assistant` | Porta de evidência | Ausência deliberada e gateada: `helpers/agent-lint.sh:352` — `ROSTER_EXEMPT=("software-architect" "setup-assistant")`, com o motivo documentado em `:350-351` ("the orchestrator itself, and the onboarding agent, which the user invokes and no orchestrator delegates to"). Sem achado |
| `agents/software-architect.md` com 211 linhas, no teto | Porta 3 (semântica) | Mesmo alvo e mesma causa (tamanho do corpo do arquiteto) de `agent-software-architect-foundational-rule-51-lines-2x-avg` (✅ Executed). O ângulo novo — teto documentado 205 vs. enforçado 211 — foi reportado com alvo `CLAUDE.md`, não como problema do agente |
| `skill-adr-coverage-only-architect` (alcance da skill `adr`) | Porta 5 (estado) | Já pertence ao conjunto **aberto** deste eixo |
