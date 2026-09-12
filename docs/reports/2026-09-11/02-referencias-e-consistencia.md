# Eixo B — Referências e consistência (2026-09-11)

**Data:** 2026-09-11 · **Baseline:** `HEAD` = `9530551`

**Gates executados:** `helpers/agent-lint.sh` → `clean ✓` · `helpers/orphan-template-scan.sh` →
`clean ✓` · `helpers/orphan-skill-scan.sh` → 3 avisos de carga duplicada, todos já verificados como
**falsos positivos do scanner** em 2026-08-21 (a segunda ocorrência é citação de regra, não segundo
load) · `helpers/size-limits.sh` → `⚠ CLAUDE.md: 602 lines`, já registrado em
`auto-size-limits-claude-md-warning-counted-as-violation-turns-ci-lint-red` ·
`helpers/check-fingerprint-uniqueness.sh` → `✓ All 237 fingerprint slugs are unique` (ver Eixo C,
achado 4, sobre o "237").

**Achados originais: 2** (1 HIGH, 1 MEDIUM-HIGH).

---

## HIGH

### `CLAUDE.md` e a skill de preferências afirmam que `telemetry` nasce `true`; o instalador escreve `false`

- **Fingerprint:** `docs-sync-telemetry-fresh-install-default-documented-true-while-install-sh-writes-false-without-consent`
- **Alvo:** `CLAUDE.md`
- **Evidência:**
  - `CLAUDE.md:386` — "**`telemetry` and `auto_update` are `CONSENT_KEYS`** — both default to
    `true` in a fresh file, but are backfilled as `false` into a pre-existing one"
  - `skills/shared/user-preferences/SKILL.md:50` — "**Consent keys — `telemetry` and
    `auto_update`.** Both default to `true` in a fresh file, where the installer prompts for them."
  - `skills/shared/user-preferences/SKILL.md:66` — `| \`telemetry\` | bool | \`true\` | Anonymous
    usage telemetry (opt out with \`false\`) (consent key) |`
  - Contra o código: `scripts/install.sh:1057` — `TELEMETRY_VALUE="false"`, sob o comentário
    `:1051-1056` — "Telemetry is only ever enabled when the user was actually given the chance to
    decline it. **The default is DISABLED**"
  - `scripts/install.sh:1174` escreve `"telemetry": $TELEMETRY_VALUE` no arquivo novo, e `:1117`
    (`defaults["telemetry"] = telemetry`) **sobrescreve** o valor do schema antes da serialização
  - E os outros dois espelhos já dizem o correto: `CLAUDE-md/preferences.md:51` — "written by
    consent, not by the schema … it is `false` unless the user actively accepted";
    `README.md:277` — "Answering `n`, not answering within 60 seconds, setting
    `DEVTEAM_NONINTERACTIVE=1`, or having no terminal at all each leave it **disabled**"
- **Problema:** dois dos quatro espelhos obrigatórios do schema de preferências afirmam o **oposto**
  do código e dos outros dois espelhos. `preferences-defaults.json:14` de fato carrega
  `"telemetry": true`, mas esse valor nunca chega a um `preferences.json` novo: `install.sh` o
  substitui pelo resultado do consentimento antes de escrever. Para `auto_update` a frase é
  correta (`AUTO_UPDATE_VALUE="true"` incondicional em `:1040`); para `telemetry` é falsa.
- **Por que importa:** o `CLAUDE.md` é carregado como instrução de projeto em **toda** sessão, e
  `skills/shared/user-preferences/SKILL.md` é o documento que os agentes leem quando precisam
  decidir sobre preferências — é o espelho com maior probabilidade de ser consultado em tempo de
  execução. Um agente que responda "sim, telemetria vem ligada por padrão" a partir dessas duas
  fontes dá ao usuário uma resposta errada sobre coleta de dados — a classe de erro que o
  `PRIVACY.md` e o prompt de consentimento de `install.sh:1063-1078` existem para evitar. A
  divergência é residual: é o texto que descrevia o comportamento **anterior** a `2e12335`
  (2026-07-31, *"stop enabling telemetry without consent"*), e a remediação corrigiu o código sem
  corrigir estes dois espelhos.
- **Proposta:** reescrever `CLAUDE.md:386` para "`auto_update` defaults to `true` in a fresh file;
  `telemetry` is written from the install-time consent answer and is `false` unless actively
  accepted — both are backfilled as `false` into a pre-existing file"; alinhar
  `user-preferences/SKILL.md:50` com a mesma frase e trocar a coluna Default de `:66` para
  `por consentimento (`false` sem resposta)`, como já está em `CLAUDE-md/preferences.md:51`.
- **Impacto positivo:** elimina a única afirmação sobre coleta de dados que os quatro espelhos não
  concordam entre si; alinha a fonte lida por agentes com a lida por humanos.
- **Impacto negativo / risco:** o texto fica mais longo e mais difícil de manter em quatro cópias —
  a divergência existe porque o espelhamento é manual. A correção não instala gate nenhum, então o
  quinto espelho que alguém adicionar amanhã pode divergir de novo. O `CLAUDE.md` já está em 602
  linhas contra um teto de aviso de 600, então qualquer acréscimo piora esse outro gate.
- **Esforço:** Baixo
- **Relação declarada (não é `Refina:`):** `ref-telemetry-honors-pref-but-pref-defaults-true-on-fresh-install-without-prompt-on-non-interactive-curl-bash`
  (**HIGH**, ✅ Executed 2026-07-31) atacava o **código**; este achado é o resíduo documental que a
  remediação daquele deixou. Porta 3: alvo, causa raiz e remediação divergem — 1 de 3.

---

## MEDIUM-HIGH

### O preâmbulo do próprio banco declara sem trigger um script que tem trigger desde 2026-07-31

- **Fingerprint:** `docs-sync-reports-index-preamble-declares-archive-index-trigger-less-while-stop-99b-dispatches-it`
- **Alvo:** `docs/reports/_index.md`
- **Evidência:**
  - `docs/reports/_index.md:23-26` — "> **Rotation:** entries older than 90 days are meant to move
    to `_index-archive-YYYY-Q.md` via `helpers/archive-index.sh`. **That script currently has no
    trigger** — no hook, no CI job, no installer call — so rotation has never run. This is
    registered below as a HIGH finding (`flow-helpers-archive-index-sh-orphan-of-hook-…`) and must
    be fixed before the bank grows back."
  - Contra o mesmo arquivo, 120 linhas abaixo — `docs/reports/_index.md:144`:
    `` - `flow-helpers-archive-index-sh-orphan-of-hook-…` — **HIGH** — `helpers/archive-index.sh` is
    written, committed, and invoked by nothing — [report](…) — ✅ **Executed:** 2026-07-31 ``
  - Contra a árvore: `scripts/hooks/stop/99b-archive-index.sh` existe desde `cc28900` (2026-07-31),
    tem 2.402 bytes, e seu cabeçalho `:2-3` declara o papel — `# Stop sub-script: rotate fingerprint
    sections older than 90 days out of docs/reports/_index.md into quarterly archives`
  - O nome casa o allowlist do dispatcher: `scripts/hooks/stop.sh:57`
    `SUBSCRIPT_RE='^[0-9]{2}[a-z]?-[a-z0-9]([a-z0-9-]*[a-z0-9])?\.sh$'` → `99b-archive-index.sh`
    passa, logo é efetivamente despachado a cada `Stop`
- **Problema:** a cláusula "That script currently has no trigger — no hook, no CI job, no installer
  call" é factualmente falsa há seis semanas. A cláusula seguinte ("so rotation has never run")
  continua verdadeira — `ls docs/reports/_index-archive-*` não devolve nada — mas pela razão oposta
  à declarada: o gate existe e é temporal (`99b-archive-index.sh:11-12`, "The rotation is
  time-based, not change-based"), e nenhuma seção do banco cruzou 90 dias ainda.
- **Por que importa:** este bloco está entre as linhas 1-120 do `_index.md`, que é **exatamente** o
  trecho que a Fase 0 de `_prompt-auditoria.md:43` manda ler (`sed -n '1,120p'`) antes de qualquer
  outra coisa, em todo pass. É a primeira coisa que o auditor lê, e diz a ele que um mecanismo
  existente não existe. O § *Atualização do banco* do mesmo prompt (passo 4) instrui a rodar
  `helpers/archive-index.sh --dry-run` e executá-lo sem `--dry-run` se houver seção >90 dias — um
  auditor que acredite no preâmbulo conclui que precisa fazer isso à mão para sempre, e não tem
  motivo para verificar se o hook já cuida disso. A falsidade se auto-perpetua porque o aviso
  também é a razão pela qual ninguém revisita o item ✅.
- **Proposta:** substituir as quatro linhas por uma: "> **Rotação:** seções com mais de 90 dias são
  movidas para `_index-archive-YYYY-Q.md` por `helpers/archive-index.sh`, disparado uma vez por dia
  pelo `Stop` via `scripts/hooks/stop/99b-archive-index.sh`. Nenhuma seção cruzou 90 dias ainda,
  logo nenhum arquivo de archive existe."
- **Impacto positivo:** remove a única afirmação falsa do bloco que todo pass lê primeiro; elimina o
  trabalho manual redundante que o passo 4 do prompt induz.
- **Impacto negativo / risco:** perde-se o aviso "must be fixed before the bank grows back", que
  hoje funciona como lembrete de que o banco cresce sem limite. O texto substituto deve manter
  alguma menção ao crescimento, ou a próxima pessoa a olhar 235 fingerprints não terá sinal nenhum.
  E a correção é pontual: nada impede que o preâmbulo divirja de novo na próxima remediação.
- **Esforço:** Baixo
- **Relação declarada (não é `Refina:`):**
  `docs-sync-reports-index-md-99-legend-comment-claims-all-131-entries-unmarked-while-121-carry-executed-or-partial-marks`
  (**LOW-MEDIUM**, aberto) também aponta texto defasado no preâmbulo do `_index.md`. Porta 3: alvo
  coincide (`docs/reports/_index.md`); causa raiz difere (contagem de marcadores não atualizada vs.
  achado HIGH resolvido ainda anunciado como aberto); remediação difere (recontar a legenda vs.
  retratar o aviso de rotação). **1 de 3 ⇒ não é duplicata.**

---

## Candidatos verificados e descartados neste eixo

| Candidato | Porta | Motivo |
|---|---|---|
| `CLAUDE.md:129` diz `SKILL_DESC_STRICT=false`; `agent-lint.sh:98` diz `true` | 5 | `docs-sync-claude-md-102-states-skill-desc-strict-false-…` (HIGH, aberto) |
| `CLAUDE.md:92,313` dizem teto de agente 205; `size-limits.sh:44` tem `AGENT_LIMIT=211` | 5 | `agent-line-cap-205-documented-in-claude-md-vs-211-enforced-by-size-limits` (HIGH, aberto) |
| `CLAUDE.md:109` lista oito coding agents; `seo-specialist` é o nono com `## Worktree Isolation` | 5 | `docs-sync-claude-md-coding-agents-list-omits-seo-specialist` (MEDIUM, aberto) |
| `CLAUDE.md:344-347` enumera `scripts/hooks/lib/` como três arquivos; há quatro (`agent-usage.sh`, 6.5 KB, 2026-08-11, fonte do evento `agent_completed` que responde por 36,9% da telemetria) | 3 | alvo + causa raiz + remediação coincidem com a família `ref-claude-md-file-structure-*` (3 fingerprints ✅ Executed) — **3 de 3**. Mesma porta pela qual `docs/prompts/` caiu em 2026-08-14 e `docs/harness.md` em 2026-08-28. *A recorrência em si virou achado no Eixo C.* |
| Tabela de comandos do `README.md` omite `/devteam:install` (35 em `commands.json`, 34 no README) | 5 | já no conjunto aberto |
| Par `metrics-last-20-days.md` / `.en.md` escapa ao gate de sync por inverter o sufixo | 5 | `ref-readme-sync-gate-discovers-only-pt-br-suffix-blind-to-inverted-en-suffix-pair` (MEDIUM, aberto) |
| 3 cargas duplicadas reportadas por `orphan-skill-scan.sh` (`test-pyramid`×2, `worktree`×1) | 3 | verificadas como falsos positivos do scanner em 2026-08-21 |
| `docs/install-claude.md`, `install-codex.md`, `install-opencode.md` e `installation.md` não mencionam telemetria nem `PRIVACY.md` (0 ocorrências nos quatro) | 3 | alvo + causa raiz coincidem com o achado HIGH deste eixo (mesma lacuna documental sobre consentimento de telemetria) — **2 de 3** |
| `commands.json` (35 comandos) × tabela do `CLAUDE.md` (39 linhas `/devteam:`) × arquivos em `commands/` | — | verificado: **conjuntos idênticos**, nenhuma divergência |
| `scripts/lib/tiers.json` `agent_effort` × os cinco especialistas nomeados em `CLAUDE.md` | — | verificado: **idênticos** (`backend-test-specialist`, `frontend-test-specialist`, `database-specialist`, `devops-specialist`, `qa-specialist`) |
| `/devteam:seo` auto-spawn declarado em `CLAUDE.md:222` | — | verificado: honrado em `commands/frontend.md:21`, `commands/fullstack.md:21-22` e `skills/shared/spawn-classifier/SKILL.md:38-39` |
