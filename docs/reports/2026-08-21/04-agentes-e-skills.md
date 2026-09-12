# Eixo D — Agentes e skills (2026-08-21)

**Baseline:** `HEAD` = `a67cac9` · **Baseline anterior:** `c03f898`

## HIGH

### Duas seções distintas numeradas `### 5.` em Spawn Integrity quebram as três referências cruzadas a "check 5"

- **Fingerprint:** `skill-orchestration-two-sections-both-numbered-check-5-breaks-cross-refs`
- **Alvo:** `skills/architecture/orchestration/SKILL.md`
- **Evidência:**
  - `skills/architecture/orchestration/SKILL.md:213` — "`### 5. Auto-reactivation — schedule the checkback, don't wait to be asked`"
  - `skills/architecture/orchestration/SKILL.md:245` — "`### 5. Periodic status table`"
  - `skills/architecture/orchestration/SKILL.md:270` — "`  check 5 closes for subagents.`"
  - `agents/software-architect.md:89` — "`**Before ending a turn with an unreturned spawn, call \`ScheduleWakeup\`** instead of going silent (Spawn Integrity check 5, Auto-reactivation).`"
  - `CLAUDE.md:172` — "`Orchestrators load it from \`skills/architecture/orchestration/SKILL.md\` § Spawn Integrity, check 5. Never restate the gate check, loop mechanics, or table format`"
- **Problema:** o commit `a3e6095` (`feat(orchestration): wire work-feedback into Spawn Integrity`) inseriu *Periodic status table* como `### 5.` sem renumerar — a seção *Auto-reactivation*, adicionada antes, já ocupava esse número. A skill tem hoje seis cabeçalhos numerados de 1 a 5, com o 5 repetido. As três referências cruzadas existentes ao "check 5" foram todas escritas antes de `a3e6095` e apontavam para *Auto-reactivation*; depois dele, cada uma resolve para uma seção diferente conforme o leitor. `CLAUDE.md:172` é a mais grave: ela manda o orquestrador carregar `work-feedback` a partir do "check 5", mas o primeiro `### 5.` que o agente encontra ao ler top-down é *Auto-reactivation*, que não menciona `work-feedback` em nenhum ponto.
- **Por que importa:** o único mecanismo que leva `skills/shared/work-feedback/SKILL.md` até um orquestrador é essa referência de `CLAUDE.md`. Se ela resolve para a seção errada, a skill nova nunca é carregada — o feature de `7b491ac`/`a3e6095` fica inerte. Na direção oposta, `agents/software-architect.md:89` diz "check 5, Auto-reactivation": um agente que leia o *segundo* `### 5.` recebe a instrução de emitir uma tabela de status onde deveria agendar um `ScheduleWakeup` de reativação. Numeração é o único endereçamento estável dentro de uma skill de 391 linhas — não há âncora alternativa.
- **Proposta:** renumerar *Periodic status table* para `### 6.` e auditar as cinco referências internas/externas por número (`:109`, `:177`, `:229`, `:234`, `:242`, `:270`, `:276`, `:372`, `software-architect.md:88-89`, `CLAUDE.md:172`) para confirmar que cada uma aponta ao alvo pretendido. Alternativa mais robusta: trocar todas as referências numéricas por referências ao título (`check *Auto-reactivation*`, `check *Periodic status table*`), que não quebram em inserção. Adicionar ao `helpers/agent-lint.sh` uma checagem de numeração monotônica de `### N.` dentro de uma mesma seção `##`.
- **Impacto positivo:** restaura o único caminho de carregamento de `work-feedback`; elimina a ambiguidade em três referências que hoje resolvem para seções semanticamente opostas (agendar wakeup vs. imprimir tabela).
- **Impacto negativo / risco:** a renumeração invalida qualquer referência externa ao "check 5" que não esteja no repositório (mensagens de commit, PRs, notas de sessão). Trocar para referência por título aumenta o custo de manutenção se os títulos mudarem. A checagem no lint pode gerar falso positivo em skills que usem listas numeradas por outro motivo dentro de `###`.
- **Esforço:** Baixo

---

## MEDIUM-HIGH

### `qa-specialist` exige que testes de browser rodem no agente principal, mas todo comando que o invoca proíbe execução no contexto principal

- **Fingerprint:** `agent-qa-specialist-browser-foreground-rule-unsatisfiable-always-spawned`
- **Alvo:** `agents/qa-specialist.md`
- **Evidência:**
  - `agents/qa-specialist.md:85` — "`Always run browser tests in the main/foreground agent, never delegated to a background subagent — the user must be able to watch the run live, step by step.`"
  - `commands/qa.md:10` — "`**MANDATORY:** Use the Task tool to spawn the agent below. Do NOT handle this task in the main context — always delegate.`"
  - `commands/qa.md:14` — "`- \`qa-specialist\` at \`.claude/agents/dev-team/qa-specialist.md\` — validate feature behavior, acceptance criteria, regression, and end-to-end correctness`"
  - `commands/backend.md:43`, `commands/frontend.md:34`, `commands/fullstack.md:42`, `commands/mobile.md:34`, `commands/review.md:43`, `commands/relayout.md:86` — todas listam `qa-specialist` como agente spawnado
- **Problema:** a regra está escrita dentro do corpo do agente que, por construção, nunca é o agente principal. `qa-specialist` é spawnado via Task em sete comandos; nenhum deles tem exceção. O destinatário da regra ("rode no foreground") é a única entidade que não pode obedecê-la — quem poderia (o orquestrador) nunca lê esse arquivo, porque um corpo de agente só é carregado pelo próprio agente ao ser instanciado.
- **Por que importa:** `456f59a` adicionou a *browser-testing mindset* justamente para que o usuário assista à validação passo a passo. O efeito prático hoje é o oposto: o agente lê uma instrução impossível e ou a ignora (rodando o browser em background, sem visibilidade — o problema original) ou trava tentando cumpri-la. É uma regra colocada na camada errada; a única camada capaz de honrá-la é a de comandos.
- **Proposta:** mover a cláusula de foreground para os comandos que spawnam `qa-specialist` — como uma exceção explícita à linha `MANDATORY: ... always delegate` quando o escopo da validação envolve driving de browser — ou torná-la uma decisão do orquestrador registrada em `skills/architecture/orchestration/SKILL.md`. No corpo do agente, manter apenas o que o agente controla: preferir o browser in-app e reportar progresso incremental.
- **Impacto positivo:** a intenção de `456f59a` (usuário assistindo a validação ao vivo) passa a ter um executor real; remove de `qa-specialist` uma diretiva auto-contraditória.
- **Impacto negativo / risco:** validação de browser no contexto principal consome contexto do orquestrador com logs de navegação — exatamente o que `skills/architecture/orchestration/SKILL.md` § Subagent Report Economy tenta evitar. A exceção precisa ser estreita (só o trecho de driving), não uma licença para rodar QA inteiro inline. Sete comandos precisam da mesma cláusula, criando novo risco de drift se não for delegada a uma home canônica.
- **Esforço:** Médio

---

### `work-feedback` prescreve cadência, teto e formato de `ScheduleWakeup` que contradizem o check Auto-reactivation do mesmo Spawn Integrity

- **Fingerprint:** `skill-work-feedback-wakeup-cadence-cap-output-conflict-auto-reactivation`
- **Alvo:** `skills/shared/work-feedback/SKILL.md`
- **Evidência:**
  - `skills/architecture/orchestration/SKILL.md:223` — "`- If \`ScheduleWakeup\` is available, call it before ending the turn: \`delaySeconds\` in the 1200–1800s`"
  - `skills/shared/work-feedback/SKILL.md:43` — "`2. After spawning, call \`ScheduleWakeup\` with \`delaySeconds\` = the clamped interval from the gate above, and a \`reason\` naming what is being polled.`"
  - `skills/shared/work-feedback/SKILL.md:19` — "`  \"work_feedback_interval_minutes\": 5`"
  - `skills/architecture/orchestration/SKILL.md:236` — "`- **Cap it.** Two reactivation attempts per stalled agent is the default ceiling — past that, stop`"
  - `skills/shared/work-feedback/SKILL.md:49` — "`5. If any step is still not ✅, call \`ScheduleWakeup\` again with the same interval.`"
  - `skills/shared/work-feedback/SKILL.md:48` — "`4. Emit **only** the table (see Format below) — no narration, no preamble, no trailing text in that turn.`"
- **Problema:** as duas seções disparam no mesmo gatilho (subagentes pendentes, turno do orquestrador terminando), chamam a mesma ferramenta (`ScheduleWakeup`) e divergem em três eixos, sem nenhuma regra de precedência entre elas:

  | Eixo | Auto-reactivation (`:213-243`) | work-feedback (`:41-51`) |
  |---|---|---|
  | `delaySeconds` | 1200–1800 s | intervalo do gate, default 300 s |
  | Teto de repetição | 2 tentativas, depois escalar como blocker | sem teto — repete até todos ✅ |
  | Conteúdo do turno | elapsed time, oferta de re-spawn, blocker explícito | apenas a tabela, "no trailing text" |

  Nenhum dos dois textos menciona o outro. O agente que carregar ambos (o caminho previsto por `CLAUDE.md:172`) recebe dois valores incompatíveis para o mesmo argumento.
- **Por que importa:** `ScheduleWakeup` aceita um `delaySeconds` por chamada. Na prática o agente escolhe um dos dois arbitrariamente — se escolher 300 s, o teto de duas tentativas de Auto-reactivation é consumido em 10 minutos e o orquestrador escala como blocker uma tarefa perfeitamente saudável; se escolher 1800 s, o feedback periódico que o usuário configurou para 5 minutos chega a cada 30. A regra "emit only the table" também suprime exatamente a mensagem de blocker que Auto-reactivation exige.
- **Proposta:** declarar precedência explícita em `skills/architecture/orchestration/SKILL.md` § Spawn Integrity: quando `work_feedback_active` é `true`, o wakeup periódico é *um só* — usa o intervalo do gate, e cada tick executa as duas responsabilidades (tabela + checagem de liveness), com a mensagem de blocker de Auto-reactivation permitida como exceção nomeada ao "only the table". O teto de duas tentativas passa a contar reativações efetivas (`SendMessage` enviado), não ticks. Quando `work_feedback_active` é `false`, vale a cadência 1200–1800 s.
- **Impacto positivo:** elimina um conflito de argumento que hoje é resolvido por sorteio; evita falso-blocker em rounds normais e preserva o intervalo que o usuário configurou.
- **Impacto negativo / risco:** um tick a cada 5 minutos que também consulta `TaskList` custa mais tokens que um tick só de tabela, e o intervalo é controlado pelo usuário — um valor baixo multiplica esse custo. A exceção ao "only the table" reabre a porta para narração, que era o motivo da regra existir; precisa ser redigida como lista fechada de casos, não como permissão geral.
- **Esforço:** Médio

---

### `qa-specialist` detecta o browser in-app por um prefixo de ferramenta que não existe em lugar nenhum

- **Fingerprint:** `agent-qa-specialist-in-app-browser-prefix-mcp-claude-browser-nonexistent`
- **Alvo:** `agents/qa-specialist.md`
- **Evidência:**
  - `agents/qa-specialist.md:79` — "`1. **Prefer the Claude app browser.** If the in-app browser tools are available (\`mcp__Claude_Browser__*\`), use them **by default** — no need to ask. This is the priority option.`"
  - `grep -rn "mcp__" agents/ skills/ commands/` retorna, além dessa linha, apenas `mcp__atlassian__*` — nenhuma outra ocorrência de `Claude_Browser`, e nenhum arquivo do repositório define ou documenta esse namespace
- **Problema:** o namespace real das ferramentas de browser in-app do Claude é `mcp__claude-in-chrome__*` (`navigate`, `computer`, `read_page`, `tabs_create_mcp`, …). `mcp__Claude_Browser__*` não corresponde a nenhum servidor MCP conhecido — nem em convenção de nomenclatura, que é kebab/lowercase no prefixo do servidor, nunca `Snake_Case` capitalizado. O passo 1 do fluxo de decisão do agente é, portanto, sempre falso.
- **Por que importa:** o passo 1 é o único caminho "não pergunte nada". Com ele permanentemente falso, todo agente cai no passo 2 (`agents/qa-specialist.md:80`, "CLI (in-app browser unavailable) → always ask") e pergunta ao usuário qual browser usar, inclusive quando roda dentro do app Claude com as ferramentas de browser disponíveis. O usuário é interrogado sobre uma escolha que a regra dizia ser automática, e a "priority option" nunca é exercida.
- **Proposta:** substituir o teste por prefixo literal por um teste por capacidade — "se a lista de ferramentas do turno contiver ferramentas de controle de browser fornecidas pelo host (hoje `mcp__claude-in-chrome__*`), use-as por default". Citar o prefixo atual como exemplo, não como condição. Se um prefixo literal for mantido, corrigi-lo para `mcp__claude-in-chrome__*`.
- **Impacto positivo:** restaura o caminho zero-pergunta que o passo 1 pretende; remove do arquivo a única string `mcp__` do repositório que não corresponde a um servidor real.
- **Impacto negativo / risco:** prefixos de servidor MCP são estáveis por convenção, não por contrato — fixar `claude-in-chrome` troca um nome errado por um nome que pode envelhecer. Um teste por capacidade é mais resiliente, mas depende de o agente inspecionar a própria lista de ferramentas de forma confiável, o que nenhuma outra regra do repositório exige hoje. Vale confirmar o namespace no ambiente-alvo antes de fixar qualquer literal.
- **Esforço:** Baixo

---

## MEDIUM

### A Hard rule de isolamento de teste unitário foi espelhada em cinco agentes sem linha na tabela Canonical Rule Homes, e já diverge da fonte citada

- **Fingerprint:** `agent-unit-test-isolation-rule-mirrored-five-agents-no-canonical-home`
- **Alvo:** `agents/backend-test-specialist.md`, `agents/frontend-test-specialist.md`, `agents/backend-reviewer.md`, `agents/frontend-reviewer.md`, `agents/qa-specialist.md`
- **Evidência:**
  - `skills/testing/test-pyramid/SKILL.md:44` (fonte) — "`A unit test **never** touches a real database, external API, filesystem, message queue, cache server, or any other out-of-process dependency — not even a test/staging instance of one.`"
  - `agents/backend-test-specialist.md:94` — "`**No external agents in unit tests**: a unit test never touches a real database, external API, filesystem, queue, or cache — this is a hard rule, not a preference, enforced by the Hard rule in \`skills/testing/test-pyramid/SKILL.md\`.`"
  - `agents/frontend-test-specialist.md:132` — "`**No external agents in unit/component tests**: never let a unit or component test make a real network call, hit a real API, or touch real browser storage (\`localStorage\`, \`IndexedDB\`, cookies) — this is a hard rule, not a preference, enforced by the Hard rule in \`skills/testing/test-pyramid/SKILL.md\`.`"
  - `agents/backend-reviewer.md:103` — "`flag as \`[BLOCKING]\` per the Hard rule in \`skills/testing/test-pyramid/SKILL.md\``"
  - `agents/frontend-reviewer.md:122` — "`flag as \`[BLOCKING]\` per the Hard rule in \`skills/testing/test-pyramid/SKILL.md\``"
  - `agents/qa-specialist.md:66` — "`a \"unit\" test hitting a real DB/API/filesystem/storage → \`[cross-boundary → test-specialist]\` per the Hard rule in \`skills/testing/test-pyramid/SKILL.md\``"
  - `CLAUDE.md:153` — "`A rule that applies to more than one agent lives in exactly **one** skill. Agents load that skill and reference the rule by name; they must not paraphrase or inline it.`"
- **Problema:** `9a64920` criou a regra em `test-pyramid` e, na mesma mudança, a parafraseou em cinco corpos de agente. Nenhuma linha foi adicionada à tabela *Canonical Rule Homes — Delegate, Never Restate* de `CLAUDE.md`, que é o gate documental para exatamente esse padrão. A divergência já existe em HEAD: `frontend-test-specialist.md:132` e `frontend-reviewer.md:122` estendem a regra a `localStorage`/`IndexedDB`/cookies e atribuem a extensão à "Hard rule in test-pyramid" — mas a Hard rule em `test-pyramid:44` não menciona storage de browser em nenhuma forma. As variantes de backend, por sua vez, omitem "or any other out-of-process dependency" e "not even a test/staging instance", que é justamente a cláusula que o commit foi escrito para adicionar.
- **Por que importa:** cinco cópias, cinco redações diferentes, todas alegando a mesma autoridade. Um leitor que abra `test-pyramid` para confirmar o escopo da regra de storage de browser não a encontra — a citação aponta para um texto que não contém o que ela afirma. Corrigir a regra na home canônica não propaga para nenhuma das cinco cópias, e nenhum linter detecta a divergência: `helpers/agent-lint.sh` valida frontmatter, identidade de skill e roster, não conteúdo restatado.
- **Proposta:** estender a Hard rule em `skills/testing/test-pyramid/SKILL.md` para cobrir explicitamente storage de browser (a cláusula que os agentes de frontend já pressupõem), reduzir as cinco cópias a uma linha de delegação por nome ("aplique a *Hard rule — no external agents* de `test-pyramid`; violação é `[BLOCKING]`"), e adicionar a linha correspondente à tabela *Canonical Rule Homes* de `CLAUDE.md`.
- **Impacto positivo:** uma edição futura da regra passa a valer para os cinco agentes; elimina a citação que hoje atribui à fonte algo que ela não diz; fecha a lacuna de storage de browser na própria skill.
- **Impacto negativo / risco:** revisores (`backend-reviewer`, `frontend-reviewer`) precisam do critério de flag em linha para decidir `[BLOCKING]` sem carregar a skill inteira — uma delegação pura pode custar uma leitura extra de arquivo por review, ou pior, ser ignorada. A linha de delegação precisa carregar o veredito (`[BLOCKING]`) mesmo delegando o conteúdo. Cinco arquivos tocados de uma vez, três deles a ≤ 8 linhas do teto de tamanho.
- **Esforço:** Médio

---

### O preâmbulo de Spawn Integrity anuncia "três checks" numa seção que tem cinco

- **Fingerprint:** `skill-orchestration-preamble-says-three-checks-but-section-has-five`
- **Alvo:** `skills/architecture/orchestration/SKILL.md`
- **Evidência:**
  - `skills/architecture/orchestration/SKILL.md:152` — "`**A spawn that did not happen must never be reported as one that did.** Three checks, in order,`"
  - `skills/architecture/orchestration/SKILL.md:153` — "`around every delegation round.`"
  - cabeçalhos reais na seção: `:156` `### 1. Preflight`, `:171` `### 2. Name validation`, `:179` `### 3. Evidence`, `:190` `### 4. Liveness`, `:213` `### 5. Auto-reactivation`, `:245` `### 5. Periodic status table`
- **Problema:** a contagem no preâmbulo nunca foi atualizada conforme os checks 4 e 5 foram adicionados. O texto declara três, existem cinco números distintos e seis cabeçalhos.
- **Por que importa:** o preâmbulo é a única instrução sobre *quantos* checks precisam rodar e em que ordem — "Three checks, in order, around every delegation round". Um agente que confie nele executa os checks 1–3 e considera o round completo, pulando Liveness, Auto-reactivation e a tabela periódica. Esse é o modo de falha exato que a seção existe para prevenir, e ele é induzido pela primeira frase dela.
- **Proposta:** substituir a contagem literal por uma formulação que não envelheça a cada inserção — "Os checks abaixo, em ordem, em torno de cada delegation round" — em vez de corrigir "Three" para "Five" e repetir o problema no próximo check adicionado.
- **Impacto positivo:** remove uma instrução que autoriza pular 40% da seção; imuniza o preâmbulo contra a próxima inserção.
- **Impacto negativo / risco:** perde-se o sinal de quantos checks esperar, que tem valor para um agente verificar se leu a seção inteira. Se a contagem for considerada necessária, ela precisa de um gate no lint, e nenhum existe hoje.
- **Esforço:** Baixo

---

## LOW-MEDIUM

### A `description` de `work-feedback` nomeia `credentials.json` — a única ocorrência dessa string no repositório inteiro

- **Fingerprint:** `skill-work-feedback-description-names-credentials-json-not-local-variant`
- **Alvo:** `skills/shared/work-feedback/SKILL.md`
- **Evidência:**
  - `skills/shared/work-feedback/SKILL.md:3` — "`description: Periodic status-table check-ins while background sub-agents work, gated by credentials.json.`"
  - `skills/shared/work-feedback/SKILL.md:14` (corpo da própria skill) — "`Read \`.dev-team-agents/user-data/credentials.local.json\` before doing anything in this skill:`"
  - `grep -rno "credentials\.json" --include=*.md .` retorna exatamente uma linha: `./skills/shared/work-feedback/SKILL.md:3`
- **Problema:** o arquivo real é `credentials.local.json`, nome usado consistentemente em `CLAUDE.md:172`, `skills/shared/setup-health-check/references/checks-list.md:565-594`, `references/fix-patterns.md:346-388` e no corpo da própria skill. Só a `description` diverge.
- **Por que importa:** a `description` alimenta o índice de skills sempre carregado — é o único trecho desta skill que todo agente vê sem abri-la. Um agente que decida a partir do índice se precisa consultar credenciais recebe um nome de arquivo que não existe; um `grep`/`Read` direto por `credentials.json` retorna vazio, e o custo é uma tentativa desperdiçada ou a conclusão errada de que o arquivo está ausente.
- **Proposta:** corrigir para `credentials.local.json`. A `description` fica em 91 caracteres, ainda dentro do orçamento de 95 documentado em `CLAUDE.md`.
- **Impacto positivo:** alinha o índice sempre carregado ao único nome de arquivo usado no resto do repositório.
- **Impacto negativo / risco:** nenhum funcional. A correção consome 6 caracteres do orçamento de 95 da `description`, deixando 4 de folga — qualquer edição futura desse texto precisa reencurtá-lo.
- **Esforço:** Baixo

---

## LOW

### Três agentes estão exatamente no teto de 211 linhas, sem margem para qualquer adição de uma linha

- **Fingerprint:** `agent-three-at-exactly-211-line-ceiling-zero-headroom-for-additions`
- **Refina:** `agent-line-cap-205-documented-in-claude-md-vs-211-enforced-by-size-limits`
- **Alvo:** `agents/software-architect.md`, `agents/qa-specialist.md`, `agents/frontend-developer.md`
- **Evidência:**
  - `wc -l agents/*.md` em HEAD — `211 agents/software-architect.md`, `211 agents/qa-specialist.md`, `211 agents/frontend-developer.md`, `210 agents/devops-specialist.md`, `209 agents/backend-reviewer.md`, `208 agents/technical-writer.md`, `208 agents/setup-assistant.md`, `208 agents/frontend-reviewer.md`
  - `bash helpers/size-limits.sh` — "`Agents: max 211 lines | Skills: max 500 lines | Commands: max 200 lines`" (nenhum agente reportado como erro; os três estão no limite, não acima)
- **Problema:** 3 de 18 agentes estão no valor exato do teto e outros 5 estão a ≤ 3 linhas dele. Metade do roster está sem folga prática. `helpers/size-limits.sh` roda no `Stop` hook e em CI, então qualquer acréscimo de uma linha a esses três arquivos falha o gate imediatamente.
- **Por que importa:** o teto passa a atuar como bloqueio em vez de sinal. A saída correta prevista pelo repositório ("move long reference material to a references/ subdirectory") não se aplica a corpos de agente, que não têm `references/` — a única saída real é mover conteúdo para uma skill, o que é uma decisão de arquitetura, não um ajuste de tamanho. Uma correção urgente de uma linha num desses três agentes obriga a uma refatoração no mesmo commit ou a burlar o gate.
- **Proposta:** identificar, nos três arquivos no teto, o bloco mais adequado a virar skill (candidato em `qa-specialist`: § Browser Testing, `:75-87`, 13 linhas, já com regra própria) e extraí-lo, criando folga real. Tratar "agente a ≥ 205 linhas" como sinal de revisão no lint, com aviso não bloqueante, para que o teto seja atingido com aviso prévio em vez de de repente.
- **Impacto positivo:** devolve margem operacional a metade do roster; converte um gate binário em um gradiente com aviso antecipado.
- **Impacto negativo / risco:** extrair conteúdo de um corpo de agente para uma skill troca linhas por uma leitura de arquivo em runtime — o custo em tokens pode subir, não descer, se a skill for carregada sempre. O aviso a 205 linhas gera ruído recorrente no `Stop` hook para 8 dos 18 agentes já hoje, exatamente o padrão de ruído que o item descartado abaixo documenta.
- **Esforço:** Médio

---

## Descartados por duplicação

| Candidato | Porta | Fingerprint colidido |
|---|---|---|
| `orphan-skill-scan.sh` reporta "duplicate skill loads" em `backend-test-specialist.md`, `frontend-test-specialist.md` e `commands/merge.md`, onde a segunda ocorrência é citação de regra (`:94`, `:132`) ou delegação a seção distinta (`merge.md:57` § step 8 vs. `:77` dirty-worktree guard), não um segundo load — ruído permanente a cada `Stop` | Porta 3 (semântica: mesmo alvo, mesma causa-raiz "não distingue load de menção", mesma remediação) | `ref-orphan-skill-scan-reports-design-system-audit-duplicate-load-in-ui-ux-designer-introduced-in-uknown-commit` |
| `skills/shared/work-feedback/SKILL.md` é alcançável apenas via `skills/architecture/orchestration/SKILL.md` § Spawn Integrity, que nenhum dos comandos `/devteam:*` carrega — a skill nova nasce inacessível às ~16 superfícies que dão spawn | Porta 5 (estado: já no conjunto OPEN) | `skill-orchestration-spawn-integrity-unreachable-from-devteam-commands` |
| `skills/shared/output-format/SKILL.md` cresceu para 203 linhas com a § Readability Rule de `a1e3791`, carregada eagerly por 9 agentes | Porta 4 (escopo menor sem sub-escopo novo) | `output-format` 190×9, já registrado como descarte de Porta 4 em `docs/reports/_index.md` |
