# Eixo B — Referências e Consistência — 2026-11-07

**Varredura:** `git diff --name-only b64428b..HEAD` (880 arquivos, 154 commits) e varredura das
subárvores prioritárias. Os quatro helpers obrigatórios, saída literal:

```
$ bash helpers/orphan-skill-scan.sh
orphan-skill-scan: clean ✓

$ bash helpers/orphan-template-scan.sh
orphan-template-scan: clean ✓

$ bash helpers/agent-lint.sh
agent-lint: clean ✓

$ bash helpers/size-limits.sh

 WARN — advisory thresholds crossed (non-blocking):
  ⚠ CLAUDE.md: 600 lines (warning threshold: 600, fails at 700)

size-limits: clean ✓
```

**Interpretação.** Os quatro limpos, com cobertura estreita — e é isso que explica os achados.
`orphan-skill-scan.sh` fixa `AGENTS_DIR=agents`, `COMMANDS_DIR=commands`, `SKILLS_DIR=skills`: a
subárvore mais tocada do delta (`.dev-team-agents/skills`, 190 arquivos) não é varrida por nenhum
dos quatro. `size-limits.sh` olha apenas `agents/`, `skills/`, `commands/` e `CLAUDE.md`.
`orphan-template-scan.sh` só itera `templates/*.md`. **Nenhum compara o par fonte ↔ cópia
instalada**, e `helpers/canonical-facts.json` declara `"paths": ["agents","skills","commands",
"templates"]` — fora `README*` e `docs/`.

> **Aviso para passes futuros:** `helpers/orphan-skill-scan.sh` tem uma fase de auto-reparo com
> `sed -i` sobre `agents/` e `commands/` (Phase 1, `:60-110`). Neste `HEAD` ela não encontrou nada
> para reparar, mas rodar o helper num `HEAD` com referência quebrada **modifica a árvore** — o que
> violaria a regra 5 do prompt de auditoria.

**Checagens próprias que saíram limpas** (registro negativo, para não serem reauditadas):
`name:` × basename em 168 `SKILL.md`, 19 agentes e 42 comandos — zero divergência; basenames de
skill duplicados entre categorias — zero; valores `name:` duplicados — zero; 182 referências
`skills/**/SKILL.md` distintas — as 20 que não resolvem vivem todas em `CHANGELOG.md`,
`docs/reports/*` ou são placeholders de documentação; `templates/` — 15 de 15 com referência
resolvível; `skills/third-party/sources.json` no `HEAD` — 4 skills × 4 diretórios, consistente.

**Candidatos:** 6 avaliados → **3 achados**, 3 descartados por duplicação, 2 refutados por
evidência própria.

---

## HIGH

### A cópia instalada versionada em `.dev-team-agents/` está defasada da árvore-fonte, e é ela que as sessões do próprio repositório carregam

- **Fingerprint:** `gov-committed-install-copy-stale-vs-source-no-gate`
- **Alvo:** `.dev-team-agents/` (666 arquivos rastreados)
- **Evidência:**
  - Último sync: `git log -1 --date=short -- .dev-team-agents/` → `ce4de39 2026-10-31 chore(install): sync the installed framework copy`; a fonte mudou até `2026-11-05`.
  - Comparando só pares rastreados nos dois lados: `scripts` 18 drift / 176 · `skills` 31 / 414 · `agents` 3 / 18 · `commands` 6 / 41 · `templates` 0 / 15 = **58 de 664**. Entre eles: `scripts/install.sh`, `scripts/lib/devteam/hooks.py`, `cli.py`, `render_provider.py`, `lib/commands.json`, `lib/preferences-defaults.json`.
  - **16 arquivos-fonte rastreados sem contrapartida alguma** na cópia: `agents/orchestrator.md`, `commands/orchestrate.md`, `scripts/hooks/pre-tool-use/03b-staged-secret-guard.sh`, `scripts/hooks/subagent-supervise.sh`, `scripts/hooks/subagent-stop/00-supervision.sh`, `scripts/hooks/lib/subagent-supervision.sh`, `scripts/lib/devteam/graph.py`, `tools.py`, `default_agent.py`, `tool-pins.json`, `scripts/lib/provision-tools.sh`, e 4 `skills/design/seo-optimization/references/*.md`.
  - As superfícies do provider apontam para a cópia: `.claude/agents/dev-team -> ../../.dev-team-agents/agents`, `.claude/commands/devteam -> ../../.dev-team-agents/commands` (168 symlinks). Consequência medida: `ls .claude/commands/devteam/orchestrate.md` → `No such file or directory`.
  - `scripts/hooks/pre-tool-use.sh:33` — `for script in "$HOOKS_DIR"/*.sh; do`; `diff <(ls scripts/hooks/pre-tool-use/) <(ls .dev-team-agents/scripts/hooks/pre-tool-use/)` → `< 03b-staged-secret-guard.sh` (ADR-0059, `ef3f0dc`, 2026-10-31).
  - Nenhum gate: `grep -rn` em `.github/`, `helpers/` e `scripts/hooks/` só acha validações sobre uma **fixture** de instalação (`provider/50-validate-installed.sh`, `slim-bootstrap.sh`), nunca sobre a cópia versionada; `.claude/skills/repo-release-prep/SKILL.md` não tem passo de sync.
- **Problema:** a cópia instalada é versionada deliberadamente (commits `chore(install): track the installed framework …`, 2026-10-18) para dogfooding, mas o sync é manual e sem gate. Hoje está 5 dias atrás: 58 arquivos divergem e 16 nem existem lá.
- **Por que importa:** no `HEAD`, `/devteam:orchestrate` e o agente `orchestrator` — entregues em `e0bd8a0` (2026-11-02) — são **inalcançáveis nas sessões deste próprio repositório**, porque os dois symlinks do Claude Code resolvem para a cópia que não os tem. O gate de supervisão do ADR-0062 também não existe lá. O guard de secret staged do ADR-0059 sobrevive apenas pela entrada legada `"command": "scripts/hooks/pre-tool-use.sh"` (relativa, bare) de `.claude/settings.json` — a entrada confiável, o root-walk, resolve para a cópia sem o `03b` —, e `scripts/install.sh:600` documenta por que a forma bare não é confiável ("a relative path then names nothing").
- **Proposta:** adicionar um check bloqueante ao `01-lint.sh` que faça `diff -r` entre cada subárvore de `.dev-team-agents/{agents,commands,skills,scripts,templates}` e sua fonte, falhando com a lista de divergências; rodar o sync e commitá-lo antes de fechar esta janela.
- **Impacto positivo:** fecha 58 divergências e devolve ao repositório o dogfooding de 3 features entregues na janela (orchestrator, supervisão ADR-0062, guard ADR-0059); converte uma classe de drift silenciosa em falha de CI.
- **Impacto negativo / risco:** o gate passa a falhar em todo PR que toque `agents/`, `commands/`, `skills/`, `scripts/` ou `templates/` sem ressincronizar, o que **dobra o diff de quase toda mudança** e aumenta o custo de revisão; automatizado num hook, reescreve 666 arquivos e polui `git status` durante o trabalho. Alternativa mais barata: gate só como `warn`, com sync exigido apenas no `repo-release-prep`, aceitando drift intra-janela.
- **Esforço:** Médio

### O `orchestrator` não existe na Referência de Agentes e quatro superfícies vivas ainda afirmam "18 agentes"

- **Fingerprint:** `docs-sync-agent-reference-omits-orchestrator-and-18-agent-count-claims`
- **Alvo:** `docs/agents.md` · `docs/agents.pt-BR.md`
- **Evidência:**
  - `grep -c orchestrator docs/agents.md` → `0`; idem `docs/agents.pt-BR.md` → `0`. A tabela `## Team` (`docs/agents.md:19-36`) tem 18 linhas e `## Agent Descriptions` (`:48-101`) tem 18 entradas; `ls agents/*.md | wc -l` → `19`.
  - `git show HEAD:README.md` — `:15` "18 agents cover the full development lifecycle … → See the full [Agent Reference](docs/agents.md)." e `:285` "The team has **18 agents** …" — no mesmo arquivo que lista 19 linhas de agente, incluindo `:292` "| orchestrator | High-level coordinator that runs **as the main session** …".
  - `git show HEAD:README.pt-BR.md` — `:15` "18 agentes cobrem todo o ciclo de desenvolvimento" e `:285` "O time tem **18 agentes** …".
  - `docs/install-codex.md:15` — "renders 18 agents as `.codex/agents/<name>.toml`"; `docs/install-opencode.md:13` — "renders the 18 agents into `.opencode/agents/`". Contra `scripts/lib/render_provider.py:861` — `OPENCODE_PRIMARY_AGENTS = ("orchestrator",)`, que renderiza o 19º como `mode: primary`.
  - O commit que criou o agente (`e0bd8a0`) tocou `agents/`, `commands/`, `helpers/agent-lint.sh`, `scripts/lib/commands.json` e duas skills — nenhum dos seis arquivos acima.
  - Sem gate: `02-readme-sync.sh` compara apenas estrutura EN ↔ pt-BR, e a omissão está espelhada nos dois, então o gate passa verde.
- **Problema:** quatro superfícies vivas afirmam como fato uma contagem errada, e o documento canônico ao qual as duas READMEs mandam o leitor "para os detalhes completos" não tem nenhuma linha sobre o 19º agente.
- **Por que importa:** o `orchestrator` é a única persona que roda como sessão principal e tem preferência própria (`orchestrator_default`); quem segue o link da README para a Referência de Agentes não encontra nada, e as duas páginas de instalação por provider prometem renderizar 18 quando o renderer emite 19. É a falha mais fácil de propagar: a próxima release repete a contagem.
- **Proposta:** acrescentar a linha de `orchestrator` em `## Team` e a seção `### \`orchestrator\`` em `docs/agents.md` e `docs/agents.pt-BR.md`; corrigir 18→19 em `README.md:15,285`, `README.pt-BR.md:15,285`, `docs/install-codex.md:15` e `docs/install-opencode.md:13`.
- **Impacto positivo:** elimina 6 afirmações falsas e torna a Referência de Agentes completa (19/19), restaurando o valor do link que as duas READMEs já publicam.
- **Impacto negativo / risco:** a contagem literal volta a driftar no próximo agente adicionado, porque nada a valida — a correção é pontual e não cria gate. Criar o gate (incluir `README*.md` e `docs/` em `canonical-facts.json`, ou um check `ls agents/*.md` ↔ `docs/agents.md`) é mudança separada e passa a exigir manutenção da lista de padrões.
- **Esforço:** Baixo

## LOW

### A descoberta de pares do gate de README não exclui `.worktrees/`, ao contrário do seu vizinho no mesmo diretório

- **Fingerprint:** `ref-readme-sync-pair-discovery-does-not-exclude-worktrees`
- **Alvo:** `.github/scripts/ci/02-readme-sync.sh`
- **Evidência:** `:211` — `done < <(find . -name '*.pt-BR.md' -not -path './.git/*' -not -path './node_modules/*' | sort)`. Rodando esse `find` no `HEAD`: 12 resultados, 6 deles cópias de `./.worktrees/fix/backlog-packed-fields/…`; `git ls-files | grep pt-BR.md | wc -l` → `6`. O irmão no mesmo diretório já exclui: `.github/scripts/ci/secret_scan.py:26` — `SKIP_DIRS = {".git", "node_modules", "__pycache__", ".worktrees", "dist", "out"}`. `.gitignore` também lista `.worktrees/`.
- **Problema:** a lista de exclusões do `find` ficou atrás da convenção que o próprio diretório já adotou; com worktrees presentes o gate valida 12 pares, metade cópias.
- **Por que importa:** pouco, e é por isso que é LOW — `grep -rn readme-sync` acha uma única invocação, `.github/workflows/ci.yml:107`, e lá o checkout é limpo (`.worktrees/` é gitignored e não existe). O custo real aparece só quando um contribuidor roda o script à mão com worktrees abertos: o relatório dobra e um par defasado de um branch não relacionado vira `FAIL`.
- **Proposta:** acrescentar `-not -path './.worktrees/*'` ao `find` de `:211`.
- **Impacto positivo:** o script passa a produzir o mesmo resultado à mão e no CI; elimina 6 pares espúrios na execução local.
- **Impacto negativo / risco:** nenhum funcional — justificativa: o script tem uma única invocação, em ambiente onde o caminho excluído não existe, e a mudança não altera o conjunto de pares rastreados. O risco residual é de manutenção: a lista de exclusões passa a existir em dois lugares (`02-readme-sync.sh` e `secret_scan.py`) e pode driftar de novo; eliminar isso exigiria uma constante compartilhada, escopo maior que o defeito.
- **Esforço:** Baixo

## Descartados por duplicação

**Porta 3 — semântica, 3 de 3 atributos coincidindo:**

- **`.claude/settings.json` do repo omite `SubagentStop`.** Reproduzido: `json.load` dá 8 eventos (`PostToolUse`, `PostToolUseFailure`, `PreCompact`, `PreToolUse`, `SessionEnd`, `SessionStart`, `Stop`, `UserPromptSubmit`), sem `SubagentStop`, contra `scripts/install.sh:834`. **Duplicata 3/3** de `flow-hook-events-only-pretooluse-and-stop`, cuja própria nota de verificação nomeia o evento: "UserPromptSubmit, SubagentStop and Notification are still unregistered". A porta 4 não resgata: o sub-escopo `SubagentStop` **já está descrito** no registro. Além disso `_index.md:81` classifica o tema inteiro ("3 unregistered hook events, repo dogfooding only `Stop`") como padrão não adotado — decisão de design, não reparo.
- **Tabela de comandos do README lista 40 de 42.** Medido: `git show HEAD:README.md | grep -cE '^\| \`/devteam:'` → `40`; `ls commands/*.md | wc -l` → `42`; faltam `down` e `install`. **Duplicata 3/3** de `docs-sync-readme-command-table-omits-devteam-install-in-both-languages` (MEDIUM, aberto) — mesmo arquivo, mesma causa, mesma remediação. Reprovado também pela porta 5. **Re-medição para o banco: de 34/35 para 40/42, e o segundo ausente é `down`.**
- **`README.pt-BR.md:285` linka `docs/agents.md` em vez de `docs/agents.pt-BR.md`.** Confirmado no `HEAD` (`:15` linka o pt-BR, `:285` o EN). **Duplicata 3/3** de `docs-sync-readme-ptbr-agents-link-points-to-english-doc` (LOW, aberto). A âncora migrou de `:141` para `:285`.

**Cross-eixo, Porta 3:**

- **O comentário de `helpers/size-limits.sh:36` fala de "17 agents" numa árvore de 19.** Mesmo alvo, causa e remediação do achado do Eixo D `ref-size-limits-and-ci-lint-comments-state-stale-agent-command-counts`, que é estritamente mais amplo (cobre também `.github/scripts/ci/01-lint.sh:87-93`). Registrado lá.

**Refutados por evidência própria (passaram as portas, não sustentam achado):**

- **`02-readme-sync.sh:211` afetaria o gate de CI.** O fato procede e virou o achado LOW acima, mas **não na severidade implícita no candidato**: `grep -rn readme-sync` devolve uma só invocação (`ci.yml:107`), em checkout limpo onde `.worktrees/` é gitignored e ausente.
- **`scripts/install.sh` não injetaria `PostToolUseFailure` no caminho de upgrade.** Levantado ao comparar as 8 chamadas de `_inject_hook` (`:827-834`) com os 9 eventos de `scripts/lib/devteam/hooks.py:53-65`. **Refutado:** `install.sh:879-907` tem um bloco Python dedicado ("`# A failed subagent launch never reaches PostToolUse: the same dispatcher retires it.`") que injeta a entrada fora do `_inject_hook`, coberto por `tests/test_tasks.py:1420` (`test_the_failure_hook_is_injected_once_and_never_duplicated`). Os 9 eventos chegam.

**Território novo confirmado (porta 2 sem resultado):** `grep -i` em ambos os índices por
`dev-team-agents/skills`, `installed framework copy`, `install-codex`, `install-opencode`, `03b`,
`0059`, `gitleaks`, `staged-secret` e `orchestrator` (fora de
`skill-orchestration-restates-scoped-test-execution-exception`, que trata de outra skill) retorna
vazio; `grep -F` dos três slugs propostos retorna vazio nos dois arquivos.
