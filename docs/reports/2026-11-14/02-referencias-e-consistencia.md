# Eixo B — Referências e Consistência · 2026-11-14

`HEAD` = `c6398e5` · baseline = `5133c8c` · delta de 16 commits / 86 arquivos · árvore medida no HEAD:
**19 agentes, 42 comandos, 168 skills, 125 arquivos em `references/`, 58 ADRs, 11 helpers**.

## Método

Rodei os quatro helpers obrigatórios e li o que a saída limpa deles **não** cobre. `orphan-skill-scan.sh`
→ `clean ✓`: a Fase 1 (referências quebradas) lê só `agents/` e `commands/` (`:53`
`find "$AGENTS_DIR" "$COMMANDS_DIR"`) e só a forma `skills/…/SKILL.md` (`:72`); a Fase 2 deixa a skill
vendorizada nova passar pela isenção de `:131-133`, que exige um `` `security-audit` `` entre backticks
em algum `SKILL.md` fora de `third-party/` — suprido por `skills/security/third-party-security-skills/SKILL.md:16`.
`orphan-template-scan.sh` → `clean ✓`, e o escopo dele é `templates/*.md` apenas, com a distinção
shipped/repo de consumidores. `agent-lint.sh` → `clean ✓`: valida frontmatter, `tier`/`model`/`effort`/run-banner,
`name` = basename do diretório, unicidade global de nomes de skill, o roster de orquestração nos dois
sentidos, `commands.json` ↔ `agents/` + pins de `model:`, o espelhamento de `plan-mode`, a palavra
`verbatim` e § Untrusted Content — foi ele que neste delta forçou `software-architect` para dentro do
roster (`ROSTER_EXEMPT` caiu de 3 para 2 nomes em `:442`). `size-limits.sh` → `clean ✓` com **um WARN
consultivo**: `CLAUDE.md: 602 linhas` (avisa em 600, falha em 700); `skills/third-party/` é isento em
`:68`, que é exatamente o que impede `emil-design-eng/SKILL.md` (674 linhas) de falhar e confirma a
afirmação de `CLAUDE.md:164`; nenhum comando passa de 200 e nenhum agente de 211 linhas.

Nenhum dos quatro lê: nome de agente entre backticks dentro do corpo de um comando, âncora `§ Seção`,
destino de link markdown, ou qualquer contagem em `docs/`. Foi nessas quatro frestas que varri à mão.

**Varreduras próprias, com resultado.** (a) Resolvi as **184 referências distintas** da forma
`skills/**/SKILL.md` em toda a árvore — incluindo `skills/**`, `CLAUDE.md`, `CLAUDE-md/`, `scripts/`,
`docs/`, que o helper não lê: **todas resolvem**; os 21 "misses" são fixtures de teste, histórico do
`CHANGELOG` e formas `<placeholder>`. (b) 1.926 referências de caminho em `agents/ commands/ skills/
CLAUDE.md CLAUDE-md/`: zero quebradas (os aparentes misses são `docs/…` do projeto instalado e o prefixo
`.dev-team-agents/` recortado pelo regex). (c) Links markdown em **201 arquivos** de doc: **1 quebrado**
(achado abaixo). (d) Âncoras `§`: 14 suspeitas, 13 refutadas como captura excessiva do regex, **1 real**
(achado abaixo). (e) `python3 helpers/third-party-skills.py verify` → exit 0, os 5 pins conferem,
inclusive o `sha256` novo de `security-audit`. (f) `bash scripts/index-lint.sh` → silencioso/limpo.
(g) 58 ADRs ↔ 58 linhas do índice `docs/development/adrs/README.md`, sem lacuna nos dois sentidos; os
`**Applies to:**` dos 58 resolvem; as 61 citações `ADR-0xxx` em arquivos versionados resolvem (os 4
misses são fixtures). (h) As 26 chaves canônicas de `preferences-defaults.json` estão nos **5** espelhos
(`CLAUDE-md/preferences.md`, `user-preferences/SKILL.md`, `docs/user-preferences.md`, `.pt-BR.md`,
`scripts/install.sh`). (i) 42 arquivos em `commands/` ↔ 42 chaves em `commands.json`, nos dois sentidos.
(j) Dos 125 arquivos em `references/`, exatamente **um** não é referenciado por ninguém — e já está
registrado. (k) Os 19 arquivos da skill vendorizada são todos internamente alcançáveis a partir do
`SKILL.md` dela. (l) O mecanismo da ADR-0065 foi verificado contra o git: **todas** as linhas dos quatro
blocos v3 históricos (`fae2f89`, `f6ce913`, `98ddf8e`, `5133c8c`) aparecem verbatim em
`legacy-routing-v3.md` — zero faltando —, então o auto-upgrade não pode julgar editada uma seção v3
intacta, em nenhuma das gerações de v3 que já foram instaladas.

18 candidatos → **5 achados**. Os 13 descartes estão no fim, com a porta de cada um.

---

## HIGH

### A página de instalação do opencode promete 22 chaves de comando enquanto o renderer emite 42

- **Fingerprint:** `docs-sync-install-opencode-claims-22-command-keys-while-renderer-emits-42`
- **Alvo:** `docs/install-opencode.md`
- **Evidência:** `docs/install-opencode.md:13` — "This downloads the latest source, renders the 18 agents into `.opencode/agents/`, symlinks skills into `.opencode/skills/dev-team-agents/`, copies the hook adapter plugin to `.opencode/plugins/dev-team-agents.ts`, materialises the hook dispatchers at `.dev-team-agents/scripts/hooks/`, and deep-merges 22 `/devteam:<name>` command keys into `.opencode/opencode.json`." · Medido: `ls commands/*.md | wc -l` → **42**, e `scripts/lib/render_provider.py:1087` itera `sorted(commands_dir.glob("*.md"))` sem nenhum filtro por provider, com `render_command_opencode` (`:936-951`, `snippet_key` em `:949`) devolvendo exatamente um `snippet_key` por arquivo (`f"devteam:{name}"`) — 42 chaves. · O próprio instalador imprime o número real: `scripts/install-opencode.sh:270-271` — `CMD_COUNT=$(jq '. | length' "$snippet_json")` / `echo "  + merged ${CMD_COUNT} command keys into .opencode/opencode.json (key: devteam:<name>)"`, e `:304` reconfere com `jq '.command | length'`. · Essa é a página de destino do README em ambos os idiomas: `README.md:67` e `README.pt-BR.md:67` — `| **opencode** | ... | [docs/install-opencode.md](docs/install-opencode.md) |`.
- **Problema:** a única frase que descreve o que a instalação do opencode faz declara um número de chaves de comando **20 abaixo** do real. Não é uma contagem envelhecida de um dígito: é a diferença entre "o harness registra 22 comandos" e os 42 que ele registra de fato. Nenhum gate confere contagens de saída de instalador nos docs de instalação (`agent-lint.sh` valida `commands.json` ↔ `agents/`, nunca uma contagem em prosa; `02-readme-sync.sh` compara só os pares EN/pt-BR, e `install-opencode.md` não tem par).
- **Por que importa:** quem avalia o provider lê 22, roda o comando e vê `+ merged 42 command keys` na própria tela — a doc contradiz o programa no mesmo minuto. Pior: 20 comandos ficam invisíveis para quem decide pelo doc, entre eles `/devteam:sprint`, `/devteam:orchestrate` e `/devteam:security`, os três fluxos que o delta acabou de ampliar.
- **Proposta:** trocar `22` por `42` em `docs/install-opencode.md:13`, e acrescentar ao gate de docs um teste que compare cada contagem dessa frase com `len(glob('commands/*.md'))` e `len(glob('agents/*.md'))` — o mesmo padrão de `tests/test_planning_routing.py`, que já afere o bloco de roteamento contra a árvore.
- **Impacto positivo:** a frase de abertura do caminho de instalação do opencode passa a ser verdadeira; com o teste, as duas contagens dessa linha deixam de poder envelhecer em silêncio (a contagem de agentes dessa mesma linha está errada desde 2026-11-07 sem ninguém pegar).
- **Impacto negativo / risco:** um teste que afere prosa contra `glob` quebra em todo commit que adiciona um comando, obrigando a editar o doc no mesmo commit — é exatamente o custo que o repo já aceita em `preferences-sync-lint.sh`, mas é custo novo. Sem o teste, a correção é um número que volta a envelhecer.
- **Esforço:** Baixo (o número) · Médio (o gate)

---

## MEDIUM-HIGH

### O gate de findings do `/devteam:mobile` manda spawnar `test-specialist`, que não é um agente

- **Fingerprint:** `ref-mobile-command-findings-gate-spawns-nonexistent-test-specialist-agent`
- **Alvo:** `commands/mobile.md`
- **Evidência:** `commands/mobile.md:78` — "- **Aplicar todos** → spawn `mobile-developer` + the appropriate `test-specialist` in parallel via Task tool"; `:80` — "- **QA** → spawn the appropriate `test-specialist` via Task tool to fix the findings"; e nas descrições do `AskUserQuestion` que alimentam esse despacho, `:67` — "Re-spawn mobile-developer + test-specialist para corrigir tudo." e `:69` — "Re-spawn apenas o test-specialist apropriado para ajustar os testes." · `ls agents/test-specialist.md` → `No such file or directory`; os nomes reais são `backend-test-specialist` e `frontend-test-specialist`. · O próprio arquivo resolve o nome certo nas fases anteriores: `:12` ("React Native / Expo → `frontend-test-specialist`; Flutter or native → `mobile-developer` in a tests-only spawn"), `:28` ("For React Native / Expo (JS/TS) suites → spawn `frontend-test-specialist`.") e `:29` ("For Flutter or native iOS/Android → the `mobile-developer` writes the platform-appropriate tests"). · A regra que isso viola está escrita: `skills/architecture/orchestration/SKILL.md:178-183` — "### 2. Name validation — roster names only / Every `subagent_type` you pass MUST appear verbatim in the Agent Roster above. Do not invent a name, shorten one, or infer one from the role — `test-author`, `test-writer` and `api-dev` are not agents. … An unknown type makes the spawn fail, and a failed spawn narrated as a success is indistinguishable from check 1's failure." · **Assimetria:** os três comandos irmãos nomeiam o agente real verbatim nas mesmas linhas de despacho — `commands/backend.md:85,87` (`backend-test-specialist`), `commands/frontend.md:78,80` (`frontend-test-specialist`), `commands/fullstack.md:84,86` (os dois). `mobile.md` é o único dos quatro que encurta.
- **Problema:** quatro linhas de `commands/mobile.md` entregam à Task tool um nome que não existe em `agents/`, dentro do único trecho do arquivo em que o nome não é derivável da stack (o despacho roda **depois** da review, sem repetir a bifurcação React Native/Flutter de `:28-29`). `agent-lint.sh` valida o roster de orquestração e `commands.json` contra `agents/`, mas nunca lê nomes de agente entre backticks no corpo de um comando; `orphan-skill-scan.sh` só casa caminhos `skills/…/SKILL.md`. Nada no repo pega isso.
- **Por que importa:** o gate de findings é o ramo em que o comando **re-spawna** para corrigir apontamentos de QA. Com `test-specialist` literal, o spawn falha; com "the appropriate", a resolução fica por conta do modelo, num ponto do arquivo onde a informação que decide (RN/Expo vs Flutter/native) está 50 linhas acima e não é repetida. Nas duas saídas o resultado é o que a orquestração nomeia como o pior caso: um spawn que falha e é narrado como sucesso, deixando os findings de QA sem autor.
- **Proposta:** em `:67`, `:69`, `:78` e `:80`, substituir `test-specialist` pela bifurcação que o arquivo já usa em `:28-29` — `frontend-test-specialist` (React Native/Expo) ou `mobile-developer` (Flutter/native) —, igualando o padrão de `backend.md`/`frontend.md`/`fullstack.md`.
- **Impacto positivo:** elimina o único nome de agente inexistente num diretivo de spawn em `commands/` (grep por tokens `-specialist`/`-developer` entre backticks em `agents/ commands/ skills/` devolve exatamente estes 4 sítios + 1 em prosa de persona); o ramo de QA do `/devteam:mobile` passa a ter autor determinado.
- **Impacto negativo / risco:** as linhas ficam mais longas e repetem a bifurcação de stack que `:28-29` já carrega — duplicação deliberada, e `commands/mobile.md` já é alvo de um achado aberto por enumerar stacks (`flow-mobile-command-spawn-line-enumerates-stacks-dropped-from-agent-description`). A alternativa de apontar para `:28-29` em uma linha evita a duplicação mas depende do modelo rolar para trás.
- **Esforço:** Baixo

---

## MEDIUM

### A tabela canônica de comando → agentes ignora o FULL AUDIT MODE que `/devteam:security` acabou de ganhar

- **Fingerprint:** `docs-sync-commands-md-security-row-omits-full-audit-mode-spawns`
- **Alvo:** `CLAUDE-md/commands.md`
- **Evidência:** `CLAUDE-md/commands.md:33` — "| `/devteam:security` | security-specialist + software-architect | Security audit or vulnerability analysis |" (a coluna de descrição é a de `commands.json` palavra por palavra). · O comando ganhou um segundo modo neste delta: `commands/security.md:26` — "**FULL AUDIT MODE:** when $ARGUMENTS matches the Full audit row of `skills/security/third-party-security-skills/SKILL.md` § Routing, this conversation runs that skill's § Full Audit Mode as the parent instead of the two spawns above." · Nesse modo os agentes são outros e em outro número: `skills/security/third-party-security-skills/SKILL.md:38` — "| Independent verifier | A new `security-specialist` spawn, never the one that found the candidate |" e `:41` — "Before reconnaissance, show the run profile and the agent budget the upstream estimate produces, and ask the user to approve them with `AskUserQuestion`. The full workflow spawns many agents; never start it on a guess." — ou seja, N spawns de `security-specialist` e **nenhum** `software-architect`. · A tabela carrega modo e sequência para todo comando em que isso importa: `:17` (`/devteam:sprint`, "main conversation orchestrates → each task's own agent …"), `:19` (`/devteam:spec`), `:18` (`/devteam:orchestrate`, "none — the main session adopts `agents/orchestrator.md`"), `:30` (`/devteam:review`, "with no args, asks a dynamic quiz"). · O dono declarado dessa tabela é `CLAUDE.md:274` — "See [`CLAUDE-md/commands.md`](CLAUDE-md/commands.md) for the full command → agents table, the conditional/test-gated spawn markers, …".
- **Problema:** a casa canônica de "quais agentes cada comando invoca" descreve `/devteam:security` como dois spawns fixos, quando no HEAD ele tem dois modos: os dois spawns, ou a conversa principal como **parent** de um workflow com caçadores paralelos e verificadores independentes sob orçamento aprovado. A linha 33 é a única da tabela cujo comando tem modo alternativo e não o registra.
- **Por que importa:** essa tabela é o que um contribuinte lê antes de mexer em roteamento, orçamento de spawn ou supervisão. Quem partir dela vai dimensionar `/devteam:security` como um comando de 2 agentes e não vai encontrar o único fluxo do repo que pede aprovação de orçamento de agentes antes de começar — justamente o gate que a ADR-0047 § full audit mode criou para ele.
- **Proposta:** estender `:33` para `| /devteam:security | security-specialist + software-architect — ou, no FULL AUDIT MODE, a conversa principal como parent → N spawns de security-specialist (hunters + verificadores independentes) sob orçamento aprovado | …`, apontando `skills/security/third-party-security-skills/SKILL.md` § Routing como a casa dos triggers.
- **Impacto positivo:** a tabela volta a cobrir 42/42 comandos no eixo que ela própria declara possuir; o modo que mais gasta agentes em todo o repo deixa de ser invisível na superfície que os contribuintes leem primeiro.
- **Impacto negativo / risco:** mais uma linha longa num arquivo que só existe porque `CLAUDE.md` passou do teto de tamanho (`size-limits.sh` já avisa em 602 linhas no arquivo pai), e um segundo sítio que precisa acompanhar § Routing — o tipo de espelho que o próprio `CLAUDE.md:224` manda evitar ("never name a vendored skill's script path or restate its run limits"). Mitiga-se mantendo a célula em uma frase e deixando os triggers só na skill.
- **Esforço:** Baixo

---

## LOW-MEDIUM

### A entrada do wiki sobre o Keychain linka uma ADR-0010 que nunca existiu, por um caminho de profundidade errada

- **Fingerprint:** `ref-wiki-keychain-entry-adr-0010-link-wrong-depth-and-nonexistent-filename`
- **Alvo:** `docs/wiki/security/macOS-keychain-add-generic-password-double-entry.md`
- **Evidência:** `docs/wiki/security/macOS-keychain-add-generic-password-double-entry.md:65` — "- [ADR-0010](../docs/development/adrs/0010-credential-references-and-the-secret-backend-cascade.md) — Credential references and backend cascade". Dois defeitos na mesma linha: (1) `../docs/development/adrs/` a partir de `docs/wiki/security/` resolve para `docs/wiki/docs/development/adrs/…`, que não existe — a forma correta de duas subpastas é `../../development/adrs/…`; (2) o nome do arquivo não existe em nenhuma profundidade: `ls docs/development/adrs/0010*` → `0010-credential-values-in-the-os-keychain-with-non-secret-reference-files.md`. · As irmãs do mesmo diretório-pai acertam as duas coisas: `docs/wiki/electron/project-naming-scope.md:39` — "[ADR-0016](../../development/adrs/0016-the-project-display-name-is-app-local-and-never-reaches-the-cli.md)" e `docs/wiki/store/machine-identity-in-roaming-profile.md:37-38` — "[Global core and data store replacing per-project vendored install](../../development/adrs/0007-…md)". · É o **único** link markdown quebrado nos 201 arquivos de doc do repo.
- **Problema:** um link de referência que não abre, com nome de ADR inventado, na entrada de wiki que documenta a armadilha do `security add-generic-password` — a mesma matéria que a ADR-0010 real decide.
- **Por que importa:** a entrada é alcançável por recall determinístico por prompt (ADR-0048) e pelo índice `docs/wiki/README.md`, então um agente que caia nela ao mexer em `scripts/lib/devteam/secrets.py` segue o ponteiro e não acha nada — e o título inventado ("Credential references and the secret backend cascade") é plausível o suficiente para o agente afirmar que leu a decisão. `scripts/index-lint.sh` (ADR-0038/0039) confere índice ↔ entradas e as linhas de status de plano; ele nunca abre um link **dentro** de uma entrada, e rodou limpo aqui.
- **Proposta:** trocar a linha por `- [ADR-0010](../../development/adrs/0010-credential-values-in-the-os-keychain-with-non-secret-reference-files.md) — Credential values in the OS keychain with non-secret reference files`, e acrescentar a `scripts/lib/index_lint.py` uma checagem de link relativo em `docs/wiki/**` e `docs/development/adrs/**` (o mesmo varredor que usei: 201 arquivos, ~2 s).
- **Impacto positivo:** zero links quebrados nos docs; com a checagem, a classe inteira passa a ser pega pelo lint que já roda no `03g-index-lint` (cobertura nova sobre 201 arquivos e 58 ADRs).
- **Impacto negativo / risco:** um checador de link relativo gera falso positivo em caminhos que só resolvem no projeto instalado (`docs/project.md`, `.dev-team-agents/…`), e o wiki está cheio deles — precisa de allowlist de prefixos, senão o lint vira ruído e alguém desliga. Só a correção da linha não tem risco.
- **Esforço:** Baixo (a linha) · Médio (o lint)

### O health check manda ler `docs-sync` § Core Rules, uma seção que não existe nesse arquivo

- **Fingerprint:** `ref-checks-list-points-at-docs-sync-core-rules-section-that-does-not-exist`
- **Alvo:** `skills/shared/setup-health-check/references/checks-list.md`
- **Evidência:** `skills/shared/setup-health-check/references/checks-list.md:762` — "| `project.md` `last-updated` older than `docs_stale_after_days`, or any of the three files printing `NO_DATE` | WARN | Report it; suggest `setup-assistant` in REFRESH mode for `project.md`. A date outside line 1 is adapted in place to `<!-- last-updated: … -->` on line 1 (`skills/shared/docs-sync/SKILL.md` § Core Rules) |". · `grep -n '^#' skills/shared/docs-sync/SKILL.md` devolve: `# Docs Sync`, `## Token Economy Rules`, `## Document Schemas`, `## Task Closure Rule`, `## Document Lifecycle`, `## When to Update What` — **não há `## Core Rules`**. · A regra citada existe, em outra seção: `skills/shared/docs-sync/SKILL.md:21` — "| **Freshness marker** | Every file has `<!-- last-updated: YYYY-MM-DD -->` on line 1. Update it on every write. Line 1 is the canonical form: rewrite a date written elsewhere (`last-updated: …` lower in the file) into it. |", que é uma linha da tabela de `## Token Economy Rules`. · Os outros seis ponteiros para essa skill na árvore nomeiam seções reais (`§ Document Lifecycle` em `CLAUDE.md:202`, `fix-patterns.md:519`, `doc-flow/references/migration.md:12`, `interaction-patterns/SKILL.md:40`, ADR-0038:24; `§ Task Closure Rule` em `CLAUDE.md:189`; `§ \`design-system\`` em `design-system-audit/SKILL.md:104`). `§ Core Rules` é o único inválido — e `## Core Rules` existe sim, mas em `skills/shared/output-format/SKILL.md:41`, outro arquivo.
- **Problema:** âncora morta numa linha de auto-fix do `/devteam:health-check`. O agente é mandado a uma seção inexistente para saber **como** mover uma data para a linha 1, e o nome da seção que ele procura existe em outro arquivo da mesma pasta `shared/`.
- **Por que importa:** `checks-list.md` tem 55 KB e é lido inteiro no fluxo do health check (já registrado como custo em `token-checks-list-loads-all-three-provider-blocks-after-step-0-resolved-one`); no melhor caso o agente lê `docs-sync/SKILL.md` inteiro para achar a regra, no pior aplica a correção de `output-format` § Core Rules, que trata de markdown puro e proibição de box-drawing — nada a ver com `last-updated`. Nenhum gate confere âncora `§`: `agent-lint.sh` não lê seções cruzadas, e `index-lint` não olha skills.
- **Proposta:** trocar `§ Core Rules` por `§ Token Economy Rules → Freshness marker` em `checks-list.md:762`; opcionalmente promover a regra a `## Freshness Marker` em `docs-sync/SKILL.md` e apontar para ela, já que quatro arquivos dependem dessa linha.
- **Impacto positivo:** zero âncoras `§` mortas na árvore (eram 1 em 14 suspeitas; as outras 13 são captura excessiva de regex); o único auto-fix de data do health check passa a ter destino.
- **Impacto negativo / risco:** `§ Token Economy Rules → Freshness marker` é um ponteiro de dois níveis, mais frágil que um de um nível — se a tabela for reorganizada, a âncora morre de novo e nada avisa. Promover a regra a `##` própria resolve isso, mas acrescenta um heading a uma skill que `CLAUDE.md:163` manda manter em tabelas e bullets.
- **Esforço:** Baixo

---

## Descartados por duplicação

**Porta 1 (literal) — mesmo pass.**

1. **§ Locating a skill triplicada nas três pontes de third-party** (`design:29-33`, `writing:45-49`, `security:63-67`, a terceira nova em `d506595`, com preâmbulos já divergentes) — eu havia levantado isso como candidato próprio; o fingerprint já está publicado neste mesmo pass por `04-agentes-e-skills.md` como `skill-three-third-party-bridges-triplicate-provider-path-table-no-home`, com evidência mais ampla (inclui a frase de precedência e `tests/test_third_party_skills.py:65-70`). Descartado sem reescrita.

**Porta 3 (semântica) + Porta 5 (estado — conjunto aberto).**

2. **`.claude/skills/security-audit` ausente e a cópia instalada ainda em `devteam:routing v3`** — `ls .claude/skills/security-audit` → `No such file or directory` (as outras 4 third-party têm symlink, de 30/10) e `.dev-team-agents/skills/shared/auto-routing/SKILL.md:14` → `<!-- devteam:routing v3 -->` contra `v4` na fonte. Porta 3 contra `gov-committed-install-copy-stale-vs-source-no-gate` (HIGH, aberto): mesmo alvo (`.dev-team-agents/` + os symlinks de `.claude/`), mesma causa raiz (cópia instalada versionada atrás da fonte) e mesma remediação (sincronizar + gate que compare os dois lados) — 3 de 3.
3. **`README.md:15,285` e `README.pt-BR.md:15,285` dizem "18 agents"; `docs/install-codex.md:15` e `docs/install-opencode.md:13` dizem "18 agents"** contra 19 arquivos em `agents/` e 19 renderizados por `render_provider.py:1066-1081`. Porta 1 e Porta 5 contra `docs-sync-agent-reference-omits-orchestrator-and-18-agent-count-claims` (HIGH, aberto), que nomeia essas quatro superfícies linha por linha. *Nota de escopo:* o achado HIGH acima é sobre a **contagem de chaves de comando** da mesma linha `install-opencode.md:13` — causa raiz independente (número de comandos, não a ausência do `orchestrator` em `docs/agents.md`) e remediação independente (`22`→`42` não corrige `18`→`19`): 1 de 3 na Porta 3, mantido.
4. **`/devteam:install` ausente das tabelas de comando dos dois READMEs** (medido: 41 de 42 presentes em cada). Porta 2 → Porta 3 e Porta 5 contra `docs-sync-readme-command-table-omits-devteam-install-in-both-languages` (MEDIUM, aberto): mesmo alvo, mesma causa, mesma remediação.
5. **`helpers/size-limits.sh:36` fala de "all 17 agents"** contra 19. Porta 1 contra `ref-size-limits-and-ci-lint-comments-state-stale-agent-command-counts` (LOW-MEDIUM, aberto), que cita essa linha.
6. **`skills/devops/monitoring/references/loki-config.md` é o único dos 125 arquivos em `references/` que ninguém referencia.** Porta 1 contra `ref-monitoring-loki-config-reference-unreachable-no-gate-covers-references-dir`. O censo completo que rodei (124 dos 125 referenciados) confirma o pai e não acrescenta sub-escopo.
7. **A Fase 1 de `orphan-skill-scan.sh` lê só `agents/` e `commands/` (`:53`), cega para as referências `skills/…/SKILL.md` em `skills/**`, `CLAUDE.md`, `CLAUDE-md/`, `scripts/` e `docs/`.** Porta 3 contra `ref-orphan-skill-scan-blind-to-directory-form-skill-refs` (MEDIUM-HIGH, aberto): mesmo alvo (`helpers/orphan-skill-scan.sh`) e mesma remediação (ampliar a varredura do mesmo helper) — 2 de 3. Além disso, sem consequência hoje: verifiquei as 184 referências à mão e todas resolvem.
8. **O parser de `User-Invocable Skills` de `orphan-skill-scan.sh:37` termina em `/^### /` e o heading é `#### User-Invocable Skills`, então ele absorve a tabela "Command-level skills" seguinte.** Porta 1 contra `auto-orphan-skill-scan-user-invocable-parser-overruns-into-next-table`.

**Refutados por evidência, não duplicados** (candidatos que a varredura levantou e a medição derrubou — ficam aqui para que o próximo pass não os re-levante):

9. **`CLAUDE-md/cli.md:292` → `docs/specs/task-board.md` § Stored vs emitted.** Refutado: o texto existe no destino, como rótulo em negrito (`docs/specs/task-board.md:450` — "**Stored vs emitted.** The record never keeps a URL:"), e o próprio arquivo usa a forma `§ Stored vs emitted` em `:680`. Convenção do repo, não âncora morta.
10. **`skills/shared/third-party-writing-skills/SKILL.md:18` → `ai-writing-signs` § Exempt lists** (o heading é `## Exempt`). Refutado: a linha é prosa — "Load none of them for the text `…` § Exempt lists." —, "lists" é o verbo, não parte do nome da seção.
11. **14 dos 19 agentes não carregam `interaction-patterns`, logo não alcançariam § Documented Answer First (ADR-0064).** Refutado: o ponteiro universal é `skills/shared/project-context/SKILL.md:235` — "| Project is ambiguous or silent on a topic | Apply our base standard and note the assumption; during approved work, `skills/shared/interaction-patterns/SKILL.md` § Documented Answer First says when silence is a question instead |" —, e `agent-lint.sh:259-261` falha qualquer agente que não carregue `project-context`. Há ainda duas rotas: `spec-gate/SKILL.md:115-117` (9 agentes) e a instrução verbatim de `commands/sprint.md:72`.
12. **`legacy-routing-v3.md` estaria incompleto para projetos ligados antes das linhas que mudaram sem bump (ADR-0065:12 cita `mobile-developer`, `seo-specialist`, `security-specialist`).** Refutado contra o git: as linhas de `mobile-developer` e `seo-specialist` foram **adições** em `f6ce913` (ausentes em `fae2f89`, o primeiro bloco v3), e um bloco com menos linhas continua "unedited" na regra unidirecional de `fix-patterns.md:289` ("every line must appear verbatim in `legacy-routing-v3.md`"). Diferença medida dos quatro blocos v3 históricos (`fae2f89`, `f6ce913`, `98ddf8e`, `5133c8c`) contra `legacy-routing-v3.md`: **0 linhas faltando em cada um**.
13. **`docs/install-opencode.md` e `docs/install-codex.md` não têm par pt-BR, enquanto `docs/installation.md` tem.** Refutado no mérito: tradução ausente não é referência quebrada, e a cegueira do gate de pares já está registrada (`flow-readme-sync-ci-hardcodes-three-doc-pairs-no-glob-discovery-any-new-pt-br-translation-pair-silently-unchecked`, `ref-readme-sync-gate-discovers-only-pt-br-suffix-blind-to-inverted-en-suffix-pair`).
