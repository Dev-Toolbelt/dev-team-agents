# Eixo C — Fluxos, comandos e automação (2026-11-14)

**`HEAD`** = `c6398e5` · baseline anterior = `5133c8c` · delta de 16 commits e 86 arquivos.

## Método

Varri, nesta ordem: (1) o banco inteiro — `docs/reports/_index.md` (176 linhas `- \`slug\``) e
`docs/reports/_index-archive-2026-Q3.md` (142), com extração dos 54 fingerprints `flow-*`/`auto-*`/`gov-*`
e leitura integral das notas de estado; (2) os arquivos do delta que caem no eixo —
`commands/sprint.md`, `commands/security.md`, `helpers/agent-lint.sh`, `helpers/third-party-skills.py`,
`scripts/lib/devteam/{cli.py,credentials_local.py,auth_gotrue.py}`, `skills/shared/{auto-routing,spec-gate,interaction-patterns}/SKILL.md`,
`skills/shared/setup-health-check/references/{checks-list.md,fix-patterns.md,legacy-routing-v3.md}`,
`skills/security/third-party-security-skills/SKILL.md`, as ADRs 0064 e 0065 e os quatro arquivos de teste novos;
(3) por dependência, os 42 `commands/*.md`, os 17 sub-scripts de `scripts/hooks/stop/`, o dispatcher
`scripts/hooks/stop.sh`, `helpers/archive-index.sh`, `helpers/check-fingerprint-uniqueness.sh`,
`.github/scripts/ci/01-lint.sh`, `scripts/lib/commands.json` e os quatro agentes de código.

**11 candidatos levantados → 5 achados.** Três candidatos morreram com a premissa refutada ou já
declarada na própria ADR, dois caíram nas Portas 1/3. Reprodução empírica (clone descartável em
`$HOME/scratch-eixoc/repo`, nunca no repositório do usuário) para dois achados: a corrupção do banco por
rotação não-atômica e a divergência de hash do vendor de skills de terceiros. A árvore do usuário segue
limpa em `c6398e5`.

---

## HIGH

### `archive-index.sh` faz append no arquivo morto antes de reescrever `_index.md`, sem rollback — uma falha no `mv` final deixa 32 slugs duplicados e trava o `Stop` e o CI

- **Fingerprint:** `auto-archive-index-appends-archive-before-index-rewrite-no-rollback`
- **Alvo:** `helpers/archive-index.sh`
- **Evidência:**
  - `helpers/archive-index.sh:27` — "`# Exit 0 always (archival is non-destructive; failures degrade to a skip).`"; `:28` — "`set -euo pipefail`"
  - `helpers/archive-index.sh:145-146` — "`cat "$WORK/section-$entry_date" >> "$archive_file"`" / "`echo "" >> "$archive_file"`" (dentro do laço `:124-149`)
  - `helpers/archive-index.sh:162` — "`mv "$WORK/keep.trimmed" "$INDEX_FILE"`" — 16 linhas **depois** dos appends, sem `trap` de rollback (o único `trap` é `:57`, `rm -rf "$WORK"`)
  - `scripts/hooks/stop/99b-archive-index.sh:45-46` — "`The helper exits 0 on every non-fatal path; failures degrade to a skip.`"
  - `scripts/hooks/stop/03b-fingerprint-uniqueness.sh:45` — "`exit 2`"; `scripts/hooks/stop.sh:64` — "`for script in "$HOOKS_DIR"/*.sh`" (ordem lexicográfica: `03b` corre antes de `99b` no mesmo `Stop`)
  - `.github/scripts/ci/01-lint.sh:85` — "`blocking "check-fingerprint-uniqueness" bash helpers/check-fingerprint-uniqueness.sh`"
  - **Reproduzido** no clone em `c6398e5` (`chmod 555 docs/reports` para negar o `mv`): `bash helpers/archive-index.sh` imprime "`→ Archived 2026-08-12`" e "`→ Archived 2026-08-14`", falha em `mv: … Permission denied` e **sai 1**; `_index-archive-2026-Q3.md` vai de 196 para 320 linhas, `_index.md` fica intacto em 823, e `bash helpers/check-fingerprint-uniqueness.sh` passa a sair **1** com **32 slugs duplicados** (34 linhas reportadas, duas delas prosa da seção de descartes).
- **Problema:** a rotação escreve nos dois lados do banco em duas etapas não atômicas e na ordem errada: primeiro
  acrescenta as seções ao arquivo morto (`:145`), depois tenta remover as mesmas seções de `_index.md` (`:162`).
  Qualquer falha entre as duas — `mv` recusado, disco cheio no `awk` de `:153-160`, ou o sub-script morto por
  timeout do hook — deixa as seções nos **dois** arquivos. Como `check-fingerprint-uniqueness.sh:22-24` varre
  `_index.md` **mais** todo `_index-archive-*.md`, cada slug rotacionado passa a contar duas vezes. O cabeçalho
  `:27` afirma "Exit 0 always (archival is non-destructive)" e `99b-archive-index.sh:45-46` repete a afirmação
  como premissa do seu `|| OUTPUT=""`: as duas são falsas no `HEAD` — o script sai 1 e a falha é destrutiva.
- **Por que importa:** o estado resultante não é silencioso, é bloqueante. Na sessão seguinte
  `03b-fingerprint-uniqueness.sh` sai **2** e o `Stop` devolve a mensagem de recusa a cada encerramento, e
  `01-lint.sh:85` fica vermelho como `blocking` — por um defeito que nenhum autor introduziu num arquivo-fonte.
  A auto-cura depende de uma segunda execução bem-sucedida, que o carimbo diário de `99b:50` adia por 24 h.
  E o detector corre **antes** do mutador no mesmo `Stop` (`03b` < `99b` na ordem lexicográfica do glob de
  `stop.sh:64`), então a corrupção nunca é vista na sessão que a produziu.
- **Proposta:** montar o conteúdo final dos dois lados em `$WORK` e só então publicar, `_index.md` primeiro:
  gerar `archive.new` por `cat "$archive_file" "$WORK/section-*"`, trocar `_index.md` por `keep.trimmed`, e só
  depois `mv "$WORK/archive.new" "$archive_file"`; se qualquer `mv` falhar, sair não-zero sem ter tocado o
  outro lado. Corrigir `:27` para descrever o exit code real.
- **Impacto positivo:** elimina a única janela em que o banco fica internamente inconsistente; o pior caso
  passa a ser "nada rotacionou", que é o no-op já esperado. Remove um modo de falha que trava 100% dos `Stop`
  e o gate `blocking` do CI até a rotação seguinte.
- **Impacto negativo / risco:** a sequência invertida torna possível o espelho — `_index.md` já trimado e o
  arquivo morto ainda sem as seções, isto é, **perda** de 32 entradas em vez de duplicação. Mitigável só
  publicando o arquivo morto primeiro e aceitando a duplicação como falha preferível, ou escrevendo os dois por
  `rename(2)` no mesmo diretório e tratando a falha do segundo como fatal com restauração explícita do primeiro;
  qualquer das duas escolhas precisa ser declarada no cabeçalho, porque hoje ele promete o contrário.
- **Esforço:** Baixo

---

## MEDIUM-HIGH

### A linha de fechamento obrigatória verbatim de todo spawn não pede `Assumptions` nem `Answered from`, e só 1 dos 26 comandos que a carregam pede as listas

- **Fingerprint:** `flow-assumptions-lists-absent-from-the-verbatim-spawn-closing-line`
- **Alvo:** `skills/architecture/orchestration/SKILL.md`
- **Evidência:**
  - `skills/architecture/orchestration/SKILL.md:295-298` — "`That final message must be a **report** … key decisions (with the `Assumptions` and `Answered from` lists of … § Documented Answer First when any exist)`"
  - `skills/architecture/orchestration/SKILL.md:300-306` — "`Every spawn prompt MUST include this instruction **verbatim, as the literal closing line of the prompt text** — not a paraphrase`" seguido do bloco citado, que termina em "`key decisions and why, and anything the user must know`" — **sem** as duas listas
  - `skills/architecture/orchestration/SKILL.md:315-316` — "`Every `commands/*.md` file that spawns an agent carries this exact line inline`"
  - `skills/shared/interaction-patterns/SKILL.md:28` — "`Applies to every agent executing an approved plan, sprint or spec`"; `:52` — "`The orchestrator shows the user each task's `Assumptions` and `Answered from`; those lists are how a wrong default or citation gets caught.`"
  - `skills/shared/spec-gate/SKILL.md:127-134` (`<HARD-GATE>`) — "`a technical default listed under `Assumptions` in the report (§ Documented Answer First)`" como resolução válida de uma suposição aberta
  - `grep -l 'Then close with a concise report only' commands/*.md` → **26 arquivos**; desses, `grep -l 'Assumptions'` → **1** (`commands/sprint.md`, em `:72`, `:83` e `:96`)
  - `tests/test_documented_answer_first.py:104-107` (`test_assumptions_reach_the_user`) lê só `_source("commands/sprint.md")`
- **Problema:** a ADR-0064 introduziu uma via em que o agente **não** pergunta e aplica um default técnico,
  registrando-o sob `Assumptions`; a única salvaguarda contra um default errado é a frase de
  `interaction-patterns:52` ("o orquestrador mostra ao usuário"). Essa salvaguarda não tem portador: a
  instrução que a skill declara obrigatória *verbatim no ponto de geração* (`:300-306`) não menciona as listas,
  e quem as pede é uma linha ad-hoc de `commands/sprint.md:72`. Nos outros 25 comandos que carregam a frase
  verbatim o agente nunca é instruído a emiti-las, e nenhum comando as exibe.
- **Por que importa:** o `<HARD-GATE>` do spec-gate é carregado pelos quatro agentes de código
  (`agents/backend-developer.md:27`, `frontend-developer.md:27`, `mobile-developer.md:27`,
  `database-specialist.md:29`) e por 10 comandos, não só por `/devteam:sprint`. No `HEAD`, em
  `/devteam:backend|frontend|fullstack|mobile|fix`, um agente pode encerrar uma suposição aberta escrevendo-a
  sob `Assumptions` num relatório que ninguém pediu e nenhum comando lê — exatamente o "I assumed X and moved
  on" que o gate existe para proibir, agora com uma saída formalmente válida. E a própria seção
  (`:308-314`) documenta por que isso falha: a instrução que só vive na definição estática do subagente foi
  perdida em 6 de 6 execuções multi-mensagem.
- **Proposta:** acrescentar as duas listas ao bloco verbatim de `:303-306` ("… e, quando existirem, suas listas
  `Assumptions` e `Answered from`") e replicar a linha nos 26 `commands/*.md`; ou, se a via deve ficar restrita
  ao sprint, limitar o item `Assumptions` do `<HARD-GATE>` aos fluxos que carregam `PLAN_APPROVED:`.
- **Impacto positivo:** fecha a salvaguarda nos 25 comandos onde hoje ela não existe, usando o mecanismo que a
  própria skill identificou como o único que funciona (instrução no ponto de geração). Dá ao teste
  `test_assumptions_reach_the_user` um alvo verificável por comando em vez de um único arquivo.
- **Impacto negativo / risco:** a linha verbatim cresce ~15 palavras e é replicada 26 vezes, aumentando o custo
  de toda troca futura nela (o banco já registra drift dessa família de linhas replicadas); e `Assumptions`
  passa a aparecer em relatórios de comandos de um único agente, onde a lista raramente terá mais de uma entrada
  e vira ruído.
- **Esforço:** Médio

### O `sync` de skills de terceiros no caminho Windows hasheia o índice git em vez da árvore que acabou de extrair

- **Fingerprint:** `auto-third-party-sync-hashes-the-git-index-not-the-extracted-tree`
- **Alvo:** `helpers/third-party-skills.py`
- **Evidência:**
  - `helpers/third-party-skills.py:34` — "`EXEC_BIT_FROM_GIT = os.name == "nt"`"
  - `:50-60` — `_git_executables(root)` roda "`["git", "-C", str(root), "ls-files", "-s", "-z"]`" e devolve as entradas "`100755 `" — isto é, o **índice**, que lista só arquivos rastreados
  - `:82,84` — "`git_executables = _git_executables(root) if EXEC_BIT_FROM_GIT else None`" / "`is_executable = rel in git_executables if EXEC_BIT_FROM_GIT else path.stat().st_mode & stat.S_IXUSR`"
  - `:213` — "`os.replace(staged, current)`" (árvore recém-extraída, ainda não indexada) e `:220` — "`entry["sha256"] = tree_hash(current)`", sete linhas depois
  - `tests/test_third_party_skills.py:249-255` — o teste novo faz "`git … add .`" **antes** de "`expected = helper.tree_hash(root)`": cobre só a árvore já rastreada
  - **Reproduzido** no clone em `c6398e5`: para `skills/third-party/security-audit` (2 dos arquivos em `100755`), o hash gravado em `sources.json` e o POSIX coincidem em `c713eab6…`; o mesmo conteúdo copiado para um diretório não rastreado e hasheado com `EXEC_BIT_FROM_GIT = True` — o estado exato em que `:220` corre — dá `611e5837…`
- **Problema:** `fetch` preserva o bit de execução do tarball ao extrair (ADR-0047 §3), mas no Windows
  `tree_hash` lê esse bit do índice git, e em `:220` a árvore acabou de ser substituída por `os.replace`: um
  skill vendorizado pela primeira vez está inteiramente fora do índice, e um re-sync lê os modos **antigos**
  que o índice ainda guarda. O hash gravado no manifesto descreve, portanto, uma árvore diferente da que está
  em disco, para todo arquivo cujo bit de execução na extração divirja do que o índice registra.
- **Por que importa:** esse hash é o mecanismo de detecção de adulteração da ADR-0047 ("any edit made outside
  `sync` fails `verify`") e é o valor contra o qual `:199` recusa sobrescrever e `:246` falha. Um `sync` feito
  no Windows — a forma suportada de atualizar um pin — grava um valor de referência que não corresponde à
  árvore; o resultado é ou `tests/test_third_party_skills.py:90` (que executa `verify`) vermelho num checkout
  POSIX, ou, se o commit nivelar os modos por baixo, o bit de execução dos dois validadores
  (`validate-findings.cjs`, `validate-coverage-ledger.cjs`) perdido em silêncio com o gate verde. O teste
  adicionado no mesmo commit não alcança nenhum dos dois casos.
- **Proposta:** em `sync_one`, calcular o hash a partir dos modos que `fetch` acabou de aplicar (passando o
  conjunto de executáveis extraídos a `tree_hash`) em vez de consultar o índice; manter a consulta ao índice
  apenas em `verify`, onde a árvore é sempre a rastreada.
- **Impacto positivo:** torna `sources.json` independente da plataforma onde o `sync` correu, que é o objetivo
  declarado de `387433a`. Fecha o caso não coberto com um teste de uma linha (hashear antes do `git add`).
- **Impacto negativo / risco:** `tree_hash` ganha um parâmetro e duas fontes de verdade para o mesmo bit, o que
  é mais superfície do que a condicional atual; e `_git_executables` continua chamando `git` com `check=True`
  sem tratamento, então num checkout Windows sem `git` no `PATH` o `verify` segue morrendo com traceback em vez
  da mensagem própria do script.
- **Esforço:** Médio

---

## MEDIUM

### Cinco comandos de implementação ainda mandam "asks rather than assumes", regra que o `spec-gate` que eles carregam substituiu neste delta

- **Fingerprint:** `flow-ask-rather-than-assume-stale-in-five-implementation-commands`
- **Alvo:** `commands/backend.md`
- **Evidência:**
  - `commands/backend.md:10` — "`Every spawned agent below treats the resolved scenarios as the implementation boundary and asks rather than assumes when something isn't covered.`"; idêntico em `commands/frontend.md:10`, `commands/fullstack.md:10`, `commands/mobile.md:10`
  - `commands/fix.md:12` — "`treat its Given/When/Then as the fix boundary and ask rather than assume when something isn't covered`"
  - `skills/shared/spec-gate/SKILL.md:115-118` — "`resolve it per `skills/shared/interaction-patterns/SKILL.md` § Documented Answer First: a spec is business-level, so what it omits is often decided in another document. Stop and ask only when that section's result table says so.`"
  - `tests/test_documented_answer_first.py:88-92` (`test_scope_lock_no_longer_stops_before_looking`) exige "`Stop and ask only`" na Scope Lock; nenhum teste olha os cinco corpos de comando
  - `grep -rn 'Documented Answer First' commands/` → apenas `commands/sprint.md`
- **Problema:** o delta trocou a regra na casa canônica (`spec-gate` § Scope Lock) e deixou a paráfrase antiga
  nos cinco comandos que carregam essa mesma skill. As duas frases dizem o oposto para o caso comum: a antiga
  manda perguntar sempre que a spec não cobre; a nova manda procurar nos documentos e só perguntar quando a
  tabela de resultado disser. O comando é o último texto que o orquestrador lê antes de montar os prompts.
- **Por que importa:** é a tempestade de perguntas que a ADR-0064 foi escrita para eliminar
  ("Sprints on well-documented projects stopped for questions the documents already answered"), reinstalada
  nos cinco comandos de implementação de tarefa única — isto é, em todo caminho fora de `/devteam:sprint`. E o
  teste novo blinda a frase nova na skill, o que faz a divergência sobreviver a qualquer execução da suíte.
- **Proposta:** substituir a cláusula final das cinco linhas por um ponteiro à regra
  ("… e resolve o que a spec não cobre per `spec-gate` § Scope Lock"), sem reescrever a regra no corpo do comando.
- **Impacto positivo:** remove a contradição em cinco arquivos com uma edição de uma cláusula cada, e alinha
  os cinco comandos ao comportamento que a skill e a suíte já exigem.
- **Impacto negativo / risco:** o comando deixa de dizer no próprio corpo o que o agente faz com uma lacuna da
  spec, trocando uma frase legível por uma indireção a mais num texto que o orquestrador lê a cada invocação;
  e a frase antiga é hoje o único lugar fora da skill que lembra o orquestrador de não aceitar suposição
  silenciosa.
- **Esforço:** Baixo

### O FULL AUDIT MODE de `/devteam:security` ramifica sobre uma tabela da skill que o comando nunca manda carregar

- **Fingerprint:** `flow-security-full-audit-branches-on-a-skill-the-command-never-loads`
- **Alvo:** `commands/security.md`
- **Evidência:**
  - `commands/security.md:6` — a lista de carga do comando: "`Load `skills/shared/current-context/SKILL.md` … Load `skills/shared/interaction-patterns/SKILL.md``" — e nada mais
  - `commands/security.md:26` — "`**FULL AUDIT MODE:** when $ARGUMENTS matches the Full audit row of `skills/security/third-party-security-skills/SKILL.md` § Routing, this conversation runs that skill's § Full Audit Mode as the parent instead of the two spawns above.`"
  - `skills/security/third-party-security-skills/SKILL.md:19` — "`When a request could mean either mode, the main conversation asks once with `AskUserQuestion` before any file is created or any agent is spawned for the full workflow.`"; `:31` — "`The main conversation is the upstream **parent**. It owns the output directory, the coverage ledger and every write.`"; `:41` — "`Before reconnaissance, show the run profile and the agent budget … never start it on a guess.`"
  - `agents/security-specialist.md:52` — a skill é roteada **no agente**, não no comando
  - `skills/third-party/README.md:20` — "`Agents load these skills through the routing skill of their category`"
  - padrão dos irmãos: `commands/backend.md:8` — "`Load `skills/shared/spawn-classifier/SKILL.md` and apply its decision tree to $ARGUMENTS`"
- **Problema:** a condicional que decide entre o fluxo de dois spawns e o workflow completo é implícita. Para
  avaliá-la a conversa principal precisa ter em contexto a § Routing da skill, e para executar o ramo precisa
  da § Full Audit Mode — mas o comando não tem instrução de carga para ela, e o único `Load` dessa skill no
  repositório está na tabela de roteamento de `agents/security-specialist.md:52`, isto é, do lado errado da
  fronteira do Task tool: em FULL AUDIT MODE o agente não é o pai.
- **Por que importa:** as regras que protegem o caminho mais pesado do framework vivem todas na skill não
  carregada — a pergunta de desambiguação de `:19`, a aprovação de perfil e budget de `:41` (que `:26` do
  comando promove a aprovação do PLAN GATE), o diretório de saída fora do projeto e o sandbox para rodar código
  do alvo. Sem a carga explícita, a conversa decide o ramo e pode começar a escrever sem nenhuma dessas
  cláusulas em contexto, e `security` é `plan_gate: "required"` em `scripts/lib/commands.json:30` justamente
  por ser o oposto de um runner fino.
- **Proposta:** acrescentar em `commands/security.md`, antes do bloco MANDATORY, a carga explícita no padrão
  de `backend.md:8` — "Load `skills/security/third-party-security-skills/SKILL.md` e aplique sua § Routing a
  $ARGUMENTS" — e reduzir `:26` a uma referência ao ramo já carregado.
- **Impacto positivo:** torna a condicional explícita e põe em contexto, antes da decisão, as quatro cláusulas
  de contenção do modo pesado; alinha o comando ao padrão de carga que os outros dois roteadores de terceiros
  já seguem.
- **Impacto negativo / risco:** a skill (67 linhas) passa a ser carregada em **toda** invocação de
  `/devteam:security`, inclusive nas focadas que nunca entram no modo completo — custo de contexto num comando
  que já carrega `current-context` e `interaction-patterns`, e que o Eixo E deste mesmo pass aponta como
  carregando material de auditoria completa onde só a via de orientação roda.
- **Esforço:** Baixo

---

## Descartados por duplicação

- **`99b-archive-index.sh` engole o exit code (`:47`, `|| OUTPUT=""`) e grava o carimbo do dia
  incondicionalmente (`:49-50`)** — **Porta 1 (literal)** e **Porta 3 (3 de 3)** contra
  `auto-99b-archive-index-writes-daily-stamp-even-when-rotation-failed` (LOW-MEDIUM, 2026-09-18, aberto):
  mesmo alvo, mesma causa raiz e mesma remediação. O achado HIGH acima é outro defeito, em outro arquivo
  (`helpers/archive-index.sh`, ordem não-atômica das escritas), e cita o registro só como a razão de a
  corrupção não ser reportada nem retentada.
- **`commands/security.md:26` substitui a aprovação do PLAN GATE por uma aprovação de perfil e budget sem que
  `scripts/lib/commands.json:30` (`plan_gate: "required"`, "Always present plan + wait for approval") registre
  a exceção, e sem validador** — **Porta 3 (2 de 3)** contra
  `auto-commands-json-plan-gate-field-has-no-consumer-and-no-validator-architect-declared-required-but-body-carries-no-plan-step`
  (MEDIUM-HIGH, 2026-07-31, 🟢 Resolved): coincidem a causa raiz (corpo divergindo do `plan_gate` declarado) e
  a remediação (consumidor/validador do campo).
- **A check `STALE: routing v3` de `checks-list.md:515` codifica a versão literalmente, então todo bump futuro
  exige uma linha nova de check, uma seção nova de fix e um `legacy-routing-vN.md`** — morre antes da Porta 1:
  a premissa já está declarada como consequência negativa aceita na própria ADR-0065:35, com a generalização
  nomeada como plano B ("If bumps become frequent, generalize to one check").
- **`legacy-routing-v3.md` carrega o wording antigo de apenas uma das três linhas que a ADR-0065:12 diz terem
  mudado sob v3, então instalações antigas cairiam no WARN em vez do auto-fix** — premissa refutada pela própria
  evidência: `git show 98ddf8e -- skills/shared/auto-routing/SKILL.md` mostra que as linhas
  `mobile-developer` e `seo-specialist` foram **acrescentadas** sob v3, não reescritas, e a ADR-0065:36 declara
  que uma seção com linhas ausentes conta como não editada e as recebe de volta. Só o `security-specialist`
  precisava de wording antigo, e está em `legacy-routing-v3.md:63`.
- **`PLAN_APPROVED:` é emitido só por `/devteam:sprint`, deixando os outros comandos de implementação sem a
  isenção de plano dentro de um plano já aprovado** — morre antes da Porta 1: declarado como consequência
  neutra em ADR-0064:30 ("Other commands keep their behavior until they adopt it").
- **`_apply_reorder` (`scripts/lib/devteam/credentials_local.py:1096-1118`) insere no índice errado após o
  `pop` no ramo de lista** — premissa refutada por leitura: `at - 1 if at > source else at` compensa
  exatamente o deslocamento, nos dois sentidos.
