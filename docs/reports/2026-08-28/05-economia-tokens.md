# Eixo E — Economia de tokens (2026-08-28)

**Baseline:** `HEAD` = `a67cac9` · **Baseline anterior:** `a67cac9` · Banco consultado:
`docs/reports/_index.md` (working tree, com as 37 fingerprints não commitadas de 2026-08-21) +
`docs/reports/2026-08-21/05-economia-tokens.md`.

## Método

1. Medição das superfícies sempre carregadas (`wc -l` sobre `agents/`, `commands/`, `CLAUDE.md`,
   `CLAUDE-md/`, `skills/**/SKILL.md`, `skills/**/references/`).
2. Contagem de multiplicador por skill (`grep -rlF <skill> agents/*.md commands/*.md`) para separar
   carga eager de carga condicional.
3. Reconstrução do **conjunto real de arquivos lidos** em dois fluxos concretos: `/devteam:status` e
   `/devteam:health-check` (comando → skill → `references/`), somando linhas e bytes ponta a ponta.
4. Varredura de blocos ```` ```bash ```` embutidos em `commands/*.md` e `agents/*.md` (script Python,
   contagem de linhas por bloco) para achar conteúdo que o modelo precisa **reemitir** além de ler.
5. Portas anti-duplicação aplicadas a cada candidato antes de virar achado.

### Superfícies medidas

| Superfície | Linhas | Bytes | Carregada por | Já no banco? |
|---|---:|---:|---|---|
| `commands/status.md` | 130 (**106** = bash inline, `:22-127`) | 5.131 | toda invocação de `/devteam:status` | **Não** |
| `commands/version.md` | 47 (**26** = bash inline, `:19-44`) | 2.114 | toda invocação de `/devteam:version` | **Não** |
| `commands/adr.md` (contraprova) | 1 linha de invocação (`:23`) | — | `/devteam:adr` → `scripts/new-adr.sh` | — |
| `commands/health-check.md` | 116 | 4.701 | `/devteam:health-check` | **Não** |
| `skills/shared/setup-health-check/SKILL.md` | 88 | 6.149 | idem | **Não** |
| └ `references/checks-list.md` | **668** | 37.174 | idem, Passo 1 — **integral** | **Não** |
| &nbsp;&nbsp;└ Cat. 4 · Claude (`:128-139`) | 12 | 1.663 | idem | — |
| &nbsp;&nbsp;└ Cat. 4 · opencode (`:140-160`) | 21 | 926 | idem | — |
| &nbsp;&nbsp;└ Cat. 4 · Codex (`:161-318`) | **158** | 6.875 | idem | — |
| └ `references/fix-patterns.md` | **517** (25 seções de fix) | 22.623 | idem, Passo 2 + `setup-assistant:185` | **Não** |
| └ `references/audit-format.md` | 40 | 1.965 | idem, Passo 3 | — |
| `skills/shared/output-format/SKILL.md` | 203 | 5.325 | idem + 7 agentes + 1 comando | Sim (§ Plan Template) |
| **Total lido numa corrida de `/devteam:health-check`** | **1.632** | **77.937** | — | — |
| Índice de skills (soma das `description:`) | 152 skills / 13.030 chars | — | sempre | 0 acima de 95 chars |

Nenhuma `description:` excede o orçamento de 95 caracteres no HEAD.

### Portas anti-duplicação aplicadas

| Alvo pesquisado no banco | Resultado |
|---|---|
| `status.md`, `version.md` | 0 ocorrências |
| `checks-list`, `fix-patterns`, `setup-health-check` | 0 ocorrências |
| `install.md`, `tool-installers` | 0 ocorrências |
| `token-*` (56 linhas) | lidas integralmente; colisões na seção final |

---

## HIGH

Nenhum achado nesta severidade.

---

## MEDIUM-HIGH

### `/devteam:status` e `/devteam:version` embutem 132 linhas de bash no corpo do comando e pagam o script duas vezes por invocação, contra o padrão de 1 linha que `/devteam:adr` já usa

- **Fingerprint:** `token-status-and-version-inline-bash-scripts-paid-twice-per-invocation`
- **Alvo:** `commands/status.md` (e `commands/version.md`)
- **Evidência:**
  - `commands/status.md:9` — "Its job: print a **token-efficient**, formatted snapshot of the current
    git state … One bash call, no agent spawn, no skill load, no analysis, no commentary before or
    after."
  - `commands/status.md:19` — "Run this exactly, substituting only `$ARGUMENTS` …" seguido de um único
    bloco ```` ```bash ```` de **106 linhas / 4.065 bytes** (`:22-127`), com `build_table()`, `awk`
    com aspas escapadas em três níveis (`:39`, `:71-76`), `paste -sd, -` e `sed`.
  - `commands/version.md:8` — "print the same `[DEVTEAM:SESSION_BANNER]` block … **at minimum token
    cost**. One bash call, one exact-format echo" seguido de bloco de **26 linhas / 1.364 bytes**
    (`:19-44`).
  - `commands/adr.md:23` — `bash .dev-team-agents/scripts/new-adr.sh "$ARGUMENTS"` — o padrão canônico
    do repo para um comando que roda um script, em **uma** linha.
  - `helpers/size-limits.sh:7` — "commands/ — max ~200 lines each (**shipped verbatim into user
    projects**)" — confirma que o corpo inteiro é injetado no prompt.
  - `commands/version.md:24-43` reimplementa em `grep -oE` a mesma leitura de `installed_version` /
    `language` / `auto_update` / `worktree_active` que `scripts/hooks/session-start.sh:185-200` já faz
    em bash — **segunda cópia** do mesmo banner.
- **Problema:** o repo já tem a superfície certa — `scripts/*.sh` é allowlisted no pacote
  (`strip-tarball.sh:26` só remove `install.sh`) e há 15 scripts shipados, invocados por comandos em
  uma linha. Os dois únicos comandos que **declaram** economia de tokens como sua razão de existir são
  justamente os que fogem do padrão: colam o script no corpo do prompt. O custo não é só de leitura —
  para executar, o modelo tem de **reemitir literalmente** as 106 linhas dentro do argumento da
  chamada Bash. O script é pago **duas vezes**: uma como entrada, outra como saída.
- **Por que importa:** `/devteam:status` é comando de consulta rápida, feito para ser chamado várias
  vezes por sessão. Medido: 5.131 bytes lidos (~1.400 tokens) + 4.065 bytes reemitidos (~1.300 tokens
  de **saída**, tipicamente a parte mais cara) ≈ **2.700 tokens por invocação** para imprimir uma
  tabela de git status. Somando `/devteam:version` (~900 tokens), o par que existe para custar pouco
  custa ~3.600. Há ainda risco de correção: as 106 linhas contêm aspas aninhadas dentro de
  `bash -c '…'` com `awk -v b="…\$2==b…"` — transcrição verbatim de um bloco assim é exatamente onde
  um modelo introduz erro de escape, e o comando não tem teste.
- **Proposta:** extrair `commands/status.md:22-127` para `scripts/status.sh` e
  `commands/version.md:19-44` para `scripts/version.sh`; substituir cada bloco por
  `bash .dev-team-agents/scripts/status.sh "$ARGUMENTS"`, no formato de `commands/adr.md:23`. Fazer
  `version.sh` reutilizar as leituras de `state.json`/`preferences.json` de `session-start.sh` em vez
  de reimplementá-las.
- **Impacto positivo:** `commands/status.md` de 130 → **~25 linhas** (~950 bytes) e a chamada de tool
  de 4.065 → ~60 bytes: **~2.700 → ~280 tokens por `/devteam:status`** (**−90%**).
  `commands/version.md` de 47 → **~14 linhas**: ~900 → ~200 tokens (−78%). Numa sessão que consulta
  status 4 vezes, **~9,7K tokens economizados**. Vale para 100% das invocações dos dois comandos, em
  todo projeto instalado e nos três providers (o caminho `.dev-team-agents/scripts/` é
  provider-agnóstico, ao contrário do corpo renderizado). Elimina de quebra a segunda cópia do layout
  do banner que hoje vive fora de `session-start.sh`.
- **Impacto negativo / risco:** os dois comandos passam a **depender de `.dev-team-agents/scripts/`
  estar íntegro** — hoje funcionam mesmo num projeto cujos symlinks materializaram no Windows (a
  condição que `/devteam:symlinks` e a Categoria 1 do health-check existem para tratar), e
  `/devteam:status` é plausivelmente o primeiro comando que alguém roda para diagnosticar.
  **Mitigação obrigatória:** manter um fallback textual de 2 linhas no corpo (`git status --short &&
  git log --oneline -5`) para quando o script não existir. Segundo custo: os dois scripts novos entram
  no escopo da Categoria 2 do health-check (`checks-list.md:46-60` lista os scripts que precisam ser
  executáveis) — a lista precisa ser estendida no mesmo commit, senão eles nunca são verificados.
- **Esforço:** Baixo

---

## MEDIUM

### `checks-list.md` entrega os blocos de verificação dos três providers depois de o Passo 0 já ter resolvido qual é o ativo — 179 de 668 linhas mortas em toda corrida

- **Fingerprint:** `token-checks-list-loads-all-three-provider-blocks-after-step-0-resolved-one`
- **Alvo:** `skills/shared/setup-health-check/references/checks-list.md`
- **Evidência:**
  - `commands/health-check.md:9` — "## Step 0 — Detect provider / Run each detection command; the
    first one that succeeds determines the active provider" → "Store the result as `<provider>`."
  - `commands/health-check.md:37` — "Run the 13 health check categories from
    `setup-health-check/references/checks-list.md` **in order**" — **sem nenhum recorte por
    `<provider>`**.
  - `commands/health-check.md:53` — "For **Category 4**, adapt the check to the detected provider" — a
    adaptação é de *execução*, não de *carga*.
  - `skills/shared/setup-health-check/SKILL.md:19` — "1. Load `references/checks-list.md`"
  - `checks-list.md:128` — `### For Claude provider` (12 linhas / 1.663 bytes); `:140` — `### For
    opencode provider` (21 linhas / 926 bytes); `:161` — `### For Codex provider` (**158 linhas /
    6.875 bytes**, incluindo heredocs `python3` completos para `hooks.json`, skills geradas, prompts
    legados, banner em `AGENTS.md` e mapeamento de `model`/`model_reasoning_effort` contra
    `tiers.json`)
- **Problema:** o discriminador já foi calculado — o Passo 0 existe justamente para isso — mas o
  arquivo de referência é lido inteiro. Num projeto Claude (o provider **default**), as 179 linhas de
  opencode + Codex (`:140-318`) são **27% de `checks-list.md`** lidas para nunca serem executadas. A
  Categoria 4 sozinha ocupa 198 linhas, das quais no máximo 21 se aplicam a qualquer corrida
  individual.
- **Por que importa:** `/devteam:health-check` já é o fluxo mais caro do harness — 1.632 linhas /
  77,9 KB somando comando, skill, três `references/` e `output-format`. As 179 linhas são ~7,8 KB
  (~2.000 tokens) que o Passo 0 poderia ter descartado gratuitamente, e o bloco Codex é o que mais
  cresce (heredocs de `python3` com JSON parsing inline). É também a única parte do arquivo que aumenta
  a cada feature nova de um provider que a maioria das instalações não usa.
- **Proposta:** mover cada `### For <provider> provider` da Categoria 4 para
  `references/provider-checks-<provider>.md` (três arquivos: 12, 21 e 158 linhas) e deixar em
  `checks-list.md` uma linha de rota: "Category 4 — load `references/provider-checks-<provider>.md`
  for the `<provider>` resolved in Step 0." Registrar os três na tabela `## Load on Demand` de
  `SKILL.md:84-88`, que já é o mecanismo certo.
- **Impacto positivo:** `checks-list.md` de 668 → **~495 linhas**, e o arquivo efetivamente lido numa
  corrida Claude de 668 → **~507** (−24% / −7,0 KB / ~1.800 tokens). O total do fluxo cai de 1.632 →
  ~1.470 linhas. Vale para 100% das corridas do comando e para a Categoria 4 lida por
  `setup-assistant`. O ganho **cresce com o tempo**, porque o bloco Codex é o que mais recebe linhas.
- **Impacto negativo / risco:** três arquivos a manter em vez de um, e a Categoria 4 passa a ser a
  única cujo conteúdo não está em `checks-list.md` — assimetria que um próximo autor pode desfazer sem
  perceber. Se o Passo 0 resolver `unknown` (caminho já previsto em `commands/health-check.md:19-25`),
  o agente precisa de regra explícita para **pular** a Categoria 4 em vez de cair num arquivo
  inexistente. E não há gate que verifique que os três arquivos novos continuam referenciados —
  `orphan-template-scan.sh` cobre `templates/`, não `references/`.
- **Esforço:** Médio

### `fix-patterns.md` é lido inteiro — 517 linhas / 22,6 KB — para aplicar 1 dos seus 25 padrões, e 9 dos 13 ponteiros que levam até ele não nomeiam a seção

- **Fingerprint:** `token-fix-patterns-517-lines-loaded-whole-to-apply-one-of-25-auto-fixes`
- **Alvo:** `skills/shared/setup-health-check/references/fix-patterns.md`
- **Evidência:**
  - `skills/shared/setup-health-check/SKILL.md:22` — "4. Apply auto-fixes from
    `references/fix-patterns.md`" — sem recorte por categoria.
  - `commands/health-check.md:68` — "Follow the fix patterns from
    `setup-health-check/references/fix-patterns.md`." — idem.
  - `fix-patterns.md` tem **25 seções `##` independentes e mutuamente exclusivas** (`:3`
    `includeCoAuthoredBy`, `:40` symlinks ausentes, `:53` symlinks materializados, `:110` drift do
    Codex, `:144` migração de `.gitignore`, `:213` `state.json`, `:314` `preferences.json`, `:449`
    opencode model/variant, `:493` backfill de `reuse-guidelines.md`, …), em 517 linhas / 22.623 bytes.
  - Dos **13** ponteiros em `checks-list.md` para o arquivo, apenas **4** nomeiam a seção (`:73`,
    `:94`, `:114`, `:115`, `:117`). Os outros nove (`:25`, `:26`, `:134`, `:138`, `:433`, `:434`,
    `:478`, `:593`, …) dizem apenas "see fix-patterns.md".
  - `skills/shared/token-efficiency/SKILL.md` (carregada por **18/18** agentes) prescreve `grep`/`head`
    em vez de leitura integral — a regra que este fluxo não segue no seu próprio arquivo mais pesado.
- **Problema:** `fix-patterns.md` é um **catálogo**, não um procedimento: uma corrida típica aplica de
  zero a três padrões. Como a maioria dos ponteiros não diz **qual** seção ler, a única leitura
  possível é a integral. Numa instalação saudável (nenhum FIX) o arquivo idealmente não seria lido;
  numa com um sintoma, lêem-se 517 linhas para usar ~20.
- **Por que importa:** é o segundo maior arquivo do fluxo (22,6 KB, **29%** dos 77,9 KB de
  `/devteam:health-check`) e o de pior razão sinal/custo: ≥95% do conteúdo é irrelevante para qualquer
  corrida concreta. O health-check é justamente o comando que se roda **quando algo já está errado** —
  o momento em que se quer diagnóstico rápido, não 22 KB de patches para condições que não ocorreram.
  E o mesmo arquivo é apontado por `agents/setup-assistant.md:185`, no meio do onboarding.
- **Proposta:** (a) completar os 9 ponteiros de `checks-list.md` para nomear a seção exata, no formato
  que os outros 4 já usam; (b) trocar `SKILL.md:22` e `commands/health-check.md:68` por "load only the
  named section — `sed -n '/^## <section>/,/^## /p' references/fix-patterns.md`", que é a própria
  receita de `token-efficiency`; (c) opcionalmente adicionar um índice de 25 linhas (seção →
  categoria) no topo, para que a resolução caiba num `head -30`.
- **Impacto positivo:** de 517 → **~25–60 linhas** lidas (índice + 1–2 seções) por corrida com fix:
  **−20 KB / ~5.000 tokens**. O total do fluxo `/devteam:health-check` cai de 1.632 → **~1.180
  linhas** (−28%). Vale para toda corrida que encontre ao menos um item WARN/FIX, mais o caminho de
  `setup-assistant`.
- **Impacto negativo / risco:** um ponteiro cuja seção foi renomeada passa a **falhar silenciosamente**
  — hoje, com leitura integral, o agente ainda encontra o padrão certo; com `sed` ancorado, ele volta
  vazio e o fix simplesmente não é aplicado, **sem erro**. Isso torna os 13 ponteiros um contrato que
  precisa de gate, e não existe um (`orphan-skill-scan.sh` valida caminhos de skill, não âncoras dentro
  de `references/`). **Mitigação obrigatória:** fallback explícito "se a seção nomeada não for
  encontrada, leia o arquivo inteiro antes de reportar" — sem isso a proposta troca custo por falha
  silenciosa, que é o pior lado do trade.
- **Esforço:** Médio

---

## LOW-MEDIUM

Nenhum achado nesta severidade.

## LOW

Nenhum achado nesta severidade.

---

## Descartados por duplicação

| Candidato | Porta | Fingerprint colidido / motivo |
|---|---|---|
| `skills/shared/reuse-guidelines/SKILL.md` (87 linhas) eager em 10 agentes + 4 comandos, mas `:34` declara "The file does not exist until a project creates one" — num projeto sem `docs/development/reuse-guidelines.md` as 87 linhas são inertes | Porta 3 (2/3) | `token-work-feedback-opt-out-gate-lives-inside-the-71-line-skill-it-gates`: causa-raiz ("o gate que torna a skill inerte vive dentro da própria skill") e remediação ("levar o teste de uma linha para o chamador") idênticas |
| `reuse-guidelines/SKILL.md:68-87` ("Growing/Updating the Registry", 20 linhas) só se aplica a `/devteam:rule` e `/devteam:sync-rules`, mas é lida pelos 10 agentes | Porta 3 (2/3) | `token-orchestration-skill-377-lines-138-conditional-path-only-no-references-dir` |
| `commands/install.md:38-46` restata a tabela Supported Tools (9 linhas) que `skills/devops/tool-installers/SKILL.md:16-24` já tem e que o próprio comando manda carregar em `:11`; já divergiu em 2 de 7 linhas (a coluna `Depends on` — `jq` como dependência de `graphify` — some na cópia) | Porta 3 (2/3) | `token-output-format-third-copy-of-plan-format-42-lines-nine-load-sites` |
| Cinco reviewers mandam rodar `git diff main...HEAD` sem filtro de caminho | Porta 3 (2/3) | `token-pr-md-unbounded-full-diff-to-repetitive-tier-while-same-file-caps-git-log` |
| `commands/health-check.md:39-51` restata a lista das 13 categorias (310 bytes) que `SKILL.md:64-79` já traz e que reaparece como headings em `checks-list.md` — três cópias na mesma corrida | Porta 4 (escopo insuficiente) | 310 bytes contra 77,9 KB do fluxo; registrado como evidência dentro do achado de `checks-list.md` |
| `CLAUDE.md` em 602 linhas, ainda monolítico | Porta 5 (estado, já reaberto 3×) | `token-claude-md-426-lines-still-monolithic-…` |
| `interaction-patterns/SKILL.md` 209 linhas × 34 sítios de carga | Porta 5 | `token-interaction-patterns-209-lines-loaded-unconditionally-by-24-commands-…` |
| `token-efficiency/SKILL.md` 160 linhas eager em 18/18 agentes | Porta 5 (reaberto em 2026-08-14) | `token-token-efficiency-skill-itself-154-lines-eager-loaded-by-all-17-agents-…` |
| `orchestration/SKILL.md` 391 linhas sem `references/` | Porta 5 | `token-orchestration-skill-377-lines-…` |
| `scripts/install.sh` em 1.240 linhas, 176 `echo`/`printf`, sem decomposição | Porta 3 (3/3) | `token-install-sh-503-lines-largest-single-script-not-fragmented-…` |
| `migration-v1-to-v2/SKILL.md` 438 linhas sem `references/` | Porta 5 | já descarte em `_index.md:407`; além disso a carga é genuinamente condicional (`setup-assistant.md:178`), então o custo esperado é ~0 na maioria das sessões |
| 31 arquivos de `agents/`/`commands/` mandam ler `preferences.json` inteiro para extrair um campo | Porta 4 (escopo insuficiente) | o arquivo canônico tem 23 linhas; ganho por sítio desprezível, não sustenta achado quantificado |
| `project-context/SKILL.md` § Context Loading Order deixa os passos 9 e 10 sem mecanismo de índice, enquanto o 11 (wiki) tem um explícito | Porta 4 (escopo insuficiente) | `docs-sync/SKILL.md:42,53,65` já impõe tetos de 60/100/80 linhas aos três arquivos de `docs/development/`, então o custo é limitado por outro mecanismo e não é quantificável como desperdício |
