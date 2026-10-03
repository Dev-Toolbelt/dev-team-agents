# Eixo B — Referências e consistência — 2026-10-02

Prioridade de varredura: os 728 arquivos do delta desde `ef69da3`, com foco nas áreas novas —
contas/entitlement (ADR-0029), instaladores de CLI (ADR-0028), `infra/`, `plugins/`, task board e a
camada de wiki.

## Saída dos gates auxiliares

| Gate | Saída |
|---|---|
| `helpers/orphan-skill-scan.sh` | `orphan-skill-scan: clean ✓` — sem AUTO-FIXED, sem ACTION REQUIRED. **Esse "clean" é enganoso** — ver o achado `ref-orphan-skill-scan-blind-to-directory-form-skill-refs`. |
| `helpers/orphan-template-scan.sh` | `orphan-template-scan: clean ✓` |
| `helpers/agent-lint.sh` | `agent-lint: clean ✓` |
| `helpers/size-limits.sh` | `⚠ CLAUDE.md: 647 lines (warning threshold: 600, fails at 700)` · `size-limits: clean ✓` (aviso não bloqueante, tema já registrado) |
| `helpers/preferences-sync-lint.sh` | "2 mirrors checked" — ver achado LOW-MEDIUM |
| `helpers/plugin-lint.sh` | limpo |
| `helpers/check-fingerprint-uniqueness.sh` | 266 slugs, todos únicos |
| `.github/scripts/ci/02-readme-sync.sh` | `readme-sync OK ✓` |

Nenhum script alterou arquivos durante a auditoria.

Conferências que vieram **sem divergência** (vale registrar o negativo, para o próximo pass não
repetir o trabalho): valores de `preferences-defaults.json` × as três tabelas JSON em docs × o
heredoc do `install.sh`; `MACHINE_LOCAL_RECORDS` × `CLAUDE-md/cli.md` × `CLAUDE-md/user-data.md`;
todas as homes da tabela *Canonical Rule Homes* existem; links relativos de Markdown resolvem; ADRs
citados existem; o wiki não tem entrada fora do índice nem linha apontando para arquivo ausente;
`commands/*.md` × `commands.json` × `CLAUDE-md/commands.md` estão alinhados.

---

## HIGH

### `CLAUDE-md/user-data.md` descreve o `KEEP_ROOT` e as exclusões do pacote de forma falsa

- **Fingerprint:** `docs-sync-user-data-keep-root-omits-plugins-and-names-wrong-repo-only-skill`
- **Alvo:** `CLAUDE-md/user-data.md`
- **Evidência:**
  - `CLAUDE-md/user-data.md:105` — "`KEEP_ROOT` (in `scripts/install.sh`) is `agents scripts skills templates commands`"
  - `scripts/install.sh:400` — `KEEP_ROOT=(agents scripts skills templates commands plugins)`
  - `CLAUDE-md/user-data.md:99` — "Repo-level Claude config, including the `agent-creator` and `release-prep` skills"; mas `.claude/skills/release-prep` é symlink para `../../skills/shared/release-prep`, que **é distribuída**; o skill só do repositório é `repo-release-prep`
  - A tabela "Package exclusions" não tem linha para `tests/`, `infra/` (`scripts/lib/strip-tarball.sh:25`), `packaging/` nem `app/`
- **Problema:** três afirmações falsas num mesmo parágrafo. `plugins/` é mantido no pacote desde a
  ADR-0019 e a doc afirma o contrário; o skill nomeado como repo-only é justamente o que ships; e
  quatro diretórios removidos do pacote não constam da tabela que `CLAUDE.md` delega a este arquivo.
- **Por que importa:** é a doc consultada para decidir onde um arquivo novo deve morar. Hoje ela
  responde errado em duas das perguntas mais frequentes ("isso chega ao projeto do usuário?" e "esse
  skill é só do repo?"). A colisão `release-prep` × `repo-release-prep` já bloqueou um
  `devteam bind` uma vez — repetir o nome errado na doc reabre o caminho para o mesmo erro.
- **Proposta:** corrigir `:105` para `agents scripts skills templates commands plugins`; em `:99`
  trocar `release-prep` por `repo-release-prep`; acrescentar linhas para `tests/`, `infra/`,
  `packaging/` e `app/` na tabela de exclusões.
- **Impacto positivo:** elimina três afirmações factualmente falsas e leva a tabela de exclusões de
  15 para 19 itens cobertos.
- **Impacto negativo / risco:** nenhum funcional — é texto. Custo: a tabela cresce 4 linhas e passa a
  precisar de sincronia com `strip-tarball.sh`, que é justamente o que nenhum gate valida hoje.
- **Esforço:** Baixo

---

## MEDIUM-HIGH

### `commands/relayout.md` manda carregar 7 skills em caminhos que não existem

- **Fingerprint:** `ref-relayout-quality-skills-list-cites-seven-nonexistent-shared-paths`
- **Alvo:** `commands/relayout.md`
- **Evidência:** `commands/relayout.md:35` (seção **Design-system discovery**, passo "Quality skills
  to apply before declaring done") — "`skills/shared/frontend-design`,
  `skills/shared/design-system-audit`, `skills/shared/frontend-code-quality`,
  `skills/shared/component-patterns`, `skills/shared/css-quality`,
  `skills/shared/accessibility-patterns`, `skills/shared/mobile-design`,
  `skills/shared/frontend-done-checklist`".
  Dos oito, **só `frontend-done-checklist` existe em `shared/`**. Os outros sete moram em
  `skills/design/frontend-design`, `skills/design/design-system-audit`, `skills/design/mobile-design`,
  `skills/architecture/frontend-code-quality`, `skills/architecture/component-patterns`,
  `skills/architecture/css-quality` e `skills/architecture/accessibility-patterns`. A linha existe
  assim desde `c3f91be` (2026-08-09).
- **Problema:** o passo de qualidade obrigatório do comando aponta 7 de 8 caminhos para o lugar errado.
- **Por que importa:** cada agente que `/devteam:relayout` spawna tenta carregar 7 caminhos
  inexistentes. O relayout é fechado **sem** os checks de design system, acessibilidade, qualidade de
  CSS e padrões de componente — exatamente os checks que justificam o comando existir. São 54 dias
  e três auditorias sem detecção, pelo motivo do achado seguinte.
- **Proposta:** reescrever `:35` com os sete caminhos reais, ou citar as skills pelo nome simples
  (forma já usada nas outras linhas do mesmo arquivo e resolvida pelo loader).
- **Impacto positivo:** o passo de qualidade volta a carregar 8 de 8 skills em vez de 1 de 8.
- **Impacto negativo / risco:** o relayout passa a carregar 7 skills de verdade, o que aumenta o
  contexto de cada agente spawnado de forma não trivial. Vale conferir se a intenção era carga
  incondicional ou condicional por sinal; corrigir o caminho sem revisar isso troca um bug silencioso
  por um custo de token silencioso.
- **Esforço:** Baixo

### `orphan-skill-scan.sh` é cego a referências de skill em forma de diretório

- **Fingerprint:** `ref-orphan-skill-scan-blind-to-directory-form-skill-refs`
- **Alvo:** `helpers/orphan-skill-scan.sh`
- **Evidência:** `helpers/orphan-skill-scan.sh:72` — `grep -oE 'skills/[a-zA-Z0-9/_-]+/SKILL\.md'`.
  Só referências terminadas em `/SKILL.md` entram na validação. Com os 7 caminhos quebrados de
  `relayout.md:35` na árvore, o scan imprimiu `clean ✓`.
- **Problema:** a Fase 1 do scanner — reparar ou reportar referência quebrada — ignora toda
  referência na forma `` `skills/<categoria>/<nome>` `` sem o sufixo. O `CLAUDE.md` promete que o
  scan cobre "skills referenciadas por agentes que não existem no caminho citado"; essa promessa só
  vale para metade das formas em que a referência aparece na prática.
- **Por que importa:** é a **causa raiz** do achado anterior ter sobrevivido 54 dias, três
  auditorias e centenas de execuções do hook `Stop`. Qualquer outra referência em forma de diretório
  pode quebrar do mesmo jeito, com o gate dizendo `clean`.
- **Proposta:** estender o `grep` para `skills/[a-z0-9-]+/[a-z0-9-]+(/SKILL\.md)?` e validar a forma
  sem sufixo testando a existência de `<dir>/SKILL.md`.
- **Impacto positivo:** fecha uma classe inteira de referências quebradas com uma linha de regex —
  hoje são 7 ocorrências escapando, todas num único arquivo.
- **Impacto negativo / risco:** real e não trivial. O auto-fix por basename passaria a reescrever
  mais arquivos, e o scan roda **sem supervisão** no `Stop`. A forma sem sufixo também aparece em
  prosa que cita pastas legitimamente, o que gera falso positivo. Mitigação: na primeira versão,
  tratar a forma sem sufixo como **somente-reportar**, sem `sed`.
- **Esforço:** Baixo

---

## MEDIUM

nenhum achado original neste eixo nesta severidade

---

## LOW-MEDIUM

### `preferences-sync-lint.sh` cobre 2 dos 5 espelhos e só verifica presença de chave

- **Fingerprint:** `docs-sync-preferences-sync-lint-two-of-five-mirrors-key-presence-only`
- **Refina:** `docs-sync-preferences-mirror-registry-names-readmes-omits-docs-pair`
- **Alvo:** `helpers/preferences-sync-lint.sh`
- **Evidência:** `helpers/preferences-sync-lint.sh:28-31` —
  `MIRRORS=("CLAUDE-md/preferences.md" "skills/shared/user-preferences/SKILL.md")`; o teste de
  presença (`:58`) é `grep -qE "\`${key}\`"`. O `CLAUDE.md` lista **cinco** espelhos: o heredoc do
  `install.sh`, `CLAUDE-md/preferences.md`, o skill `user-preferences`, `docs/user-preferences.md` e
  o par pt-BR.
- **Problema:** o heredoc do `install.sh` e o par `docs/user-preferences*.md` não passam pelo gate, e
  nenhum espelho tem valor ou tipo conferido — só o nome da chave.
- **Por que importa:** a divergência que motivou registrar o tema (`qa_browser` ausente do heredoc) é
  exatamente a que este lint não pega. Conferi à mão neste HEAD: **hoje não há divergência**. O risco
  é prospectivo, e o pai do achado (`docs-sync-preferences-mirror-registry…`) trata do registro no
  `CLAUDE.md`, não do gate — sub-escopo estritamente contido.
- **Proposta:** acrescentar os dois docs de `docs/` à lista `MIRRORS` e comparar o heredoc com o JSON
  canônico, no mínimo por conjunto de chaves.
- **Impacto positivo:** o gate passa de 2 para 5 espelhos, cobrindo o único mirror que já drift­ou.
- **Impacto negativo / risco:** `docs/user-preferences.md` usa tabela com coluna de default em
  formato diferente dos outros espelhos, então o parser precisa tolerar dois formatos — mais
  superfície de manutenção no próprio lint.
- **Esforço:** Médio

### `CLAUDE-md/hooks.md` documenta 5 libs de hook e omite `data-dirs.sh`, a de maior fan-in

- **Fingerprint:** `ref-hooks-md-library-rows-omit-data-dirs-sh-sourced-by-ten-scripts`
- **Refina:** `ref-claude-md-hook-files-map-and-file-structure-omit-scripts-hooks-lib-session-summary-detect-shared-dep-of-two-hooks`
- **Alvo:** `CLAUDE-md/hooks.md`
- **Evidência:** `scripts/hooks/lib/` tem 10 arquivos; `grep "data-dirs" CLAUDE-md/hooks.md CLAUDE.md`
  não encontra nada. `scripts/hooks/lib/data-dirs.sh:1-4` descreve o resolvedor de `state-dir`,
  `memory-dir` e do arquivo de preferências (ADR-0013). É carregado por
  `pre-tool-use/03-credential-guard.sh`, `02-graphify-hint.sh`, `02b-telemetry.sh`,
  `stop/05-telemetry.sh`, `99b-archive-index.sh`, `04-notifier.sh`, `03e-adr-gap-check.sh`,
  `session-start.sh`, `lib/task-board.sh` e `lib/plugins.sh`. As outras libs
  (`task-board`, `session-summary-detect`, `plugins`, `touched-paths`, `agent-usage`) têm linha
  "Shared library" na tabela.
- **Problema:** a lib da qual mais scripts dependem é a única sem linha no mapa de hooks — e é
  justamente a que define a regra de resolução de caminhos entre layout 1 e layout 2.
- **Por que importa:** quem altera a resolução de `state-dir`/`memory-dir` não descobre pela doc que
  10 scripts dependem desse arquivo. O pai do achado cobre `session-summary-detect.sh`, uma lib com
  fan-in de 2; aqui o fan-in é 10, e o conteúdo é a topologia de dados — sub-escopo distinto.
- **Proposta:** acrescentar a linha `scripts/hooks/lib/data-dirs.sh | Shared library` no mesmo
  formato das outras, nomeando `devteam_state_dir`, `devteam_memory_dir` e `devteam_prefs_file`.
- **Impacto positivo:** o mapa de hooks passa a cobrir 10 de 10 libs.
- **Impacto negativo / risco:** nenhum funcional. O custo é o mesmo de qualquer linha de doc: uma
  entrada a mais para manter sincronizada, sem gate que a valide — o que é o tema do achado
  `auto-no-gate-validates-claude-md-file-structure-tree-against-real-tree`, já aberto.
- **Esforço:** Baixo

---

## LOW

nenhum achado original neste eixo nesta severidade

---

## Descartados por duplicação

- `docs-agents-md-backend-test-specialist-tier-repetitive` — porta 5 — `docs/agents.md:28` e o espelho pt-BR ainda dizem `repetitive`, mas o item está **aberto** no banco.
- `claude-md-file-structure-omits-hooks-lib-and-devteam-modules` (`hooks/lib/`, `post-tool-use/`, `user-prompt-submit/`, CI `06`/`07`, `scripts/lib/devteam/auth*`, `entitlement`, `tasks`) — porta 3 — alvo, causa e remédio coincidem com a família `ref-claude-md-file-structure-*` e com `auto-no-gate-validates-claude-md-file-structure-tree-against-real-tree`.
- `loki-config-md-unreferenced` — porta 1 — já registrado como `ref-monitoring-loki-config-reference-unreachable-no-gate-covers-references-dir`.
- `orphan-skill-scan-false-positive-duplicate-loads` — porta 5 — aberto no banco; nenhum falso positivo apareceu neste HEAD.
- `claude-md-647-lines-size-warning` — porta 3 — coberto pelo tema do monolito `CLAUDE.md`.
- `test-global-skills-hardcodes-providers-without-ALL_PROVIDERS` — descartado por avaliação própria: `tests/test_global_skills.py` cobre as raízes de skill globais (ADR-0020), que não constam da lista de comportamentos da Provider Parity Rule. Evidência fraca para promover.
