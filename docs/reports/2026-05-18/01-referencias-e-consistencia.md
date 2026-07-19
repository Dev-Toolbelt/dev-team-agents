# Relatório 01 — Referências e Consistência (2026-05-18)

**Foco:** drift introduzido pelos 16 commits da janela 2026-05-17 → 2026-05-19; quebras de sincronização entre código, documentação e marcações ✅ Executed; órfãos novos pós-refactor `scripts → helpers`.

**Convenção:** todos os fingerprints abaixo são **originais** — verificados contra `_index.md` (598 linhas, 401 fingerprints acumulados).

---

## #1 — `auto-docs-rule-violated-changelog-unreleased-missing-7-features-from-2026-05-18-window`

**Severidade:** HIGH
**Arquivo:** `CHANGELOG.md:10-43`

A janela 2026-05-17 → 2026-05-19 introduziu 7 features observáveis (telemetria, PRIVACY.md, refactor `scripts → helpers`, iOS/Android skills, stack-detection wiring, workflow-detection skill, archive-index.sh helper). **Nenhuma** está registrada em `## [Unreleased]`. A Auto-Docs Rule (CLAUDE.md:32) determina que mudanças observáveis sejam refletidas no CHANGELOG no mesmo working session.

**Trecho violador:** o bloco `[Unreleased]` ainda lista itens de `[1.4.0]` (2026-05-10) e antes, sem nenhuma referência a `feat(telemetry)`, `refactor(scripts→helpers)`, `feat(skills): iOS/Android`, etc.

**Impacto positivo do fix:** restaura a Auto-Docs Rule, dá visibilidade aos usuários sobre telemetria opcional antes do próximo `git tag`.

**Impacto negativo:** demanda manutenção contínua a cada commit observável; alternativa é gerar CHANGELOG a partir de Conventional Commits via script (proposto em fingerprint separado).

---

## #2 — `ref-changelog-references-scripts-path-not-helpers-after-refactor`

**Severidade:** MEDIUM
**Arquivo:** `CHANGELOG.md:48,112`

Após o commit `9c7aecd` (refactor: move dev-only tools to helpers/), o CHANGELOG ainda referencia paths antigos:

```
Line 48:  - `scripts/agent-lint.sh` — validates frontmatter on all `agents/*.md`
Line 112: - Orphan skill scan (`scripts/orphan-skill-scan.sh`)
```

Os scripts agora estão em `helpers/`. O CI workflow e os hooks foram atualizados (`b32c5d0`, `5034a19`), mas o CHANGELOG histórico foi deixado para trás. Esse drift impacta **navegação histórica** e **debug de regressões** ("onde estava aquele script em 1.4.0?").

**Impacto positivo:** atualizar com nota de migração em `[Unreleased]` esclarece o histórico.

**Impacto negativo:** alterar entries históricas viola Keep-a-Changelog principle ("changelogs are append-only"). Solução melhor: registrar em `[Unreleased]` com clausula "Renamed: `scripts/{agent-lint,orphan-skill-scan,...}.sh` → `helpers/`".

---

## #3 — `ref-claude-md-file-structure-omits-helpers-and-privacy-and-claude-md-folder`

**Severidade:** HIGH
**Arquivo:** `CLAUDE.md:222-237`

O bloco "File Structure" lista `scripts/`, mas omite:

- `helpers/` — diretório de 1º nível introduzido em `9c7aecd` com 6 scripts dev-only
- `PRIVACY.md` — arquivo de 1º nível introduzido em `9f1826d`
- `CLAUDE-md/` — subdir referenciado em CLAUDE.md:240,247,254,260 mas ausente do bloco ASCII

```
Estado atual (CLAUDE.md:228):
├── scripts/         ← install.sh, update.sh, new-adr.sh, graphify-refresh.sh
│   └── hooks/       ← pre-tool-use.sh, stop.sh (dispatchers) + pre-tool-use/, stop/ (sub-scripts)
```

Faltam: `helpers/`, `PRIVACY.md`, `CLAUDE-md/`. Logo, novos contribuidores que leem o File Structure não enxergam o pacote dev-tool nem onde estão fragmentos de documentação.

**Impacto positivo:** adiciona 3 linhas e elimina 3 drifts conhecidos.

**Impacto negativo:** mantém o tamanho do CLAUDE.md (já 426 linhas — sub-escopo do `token-claude-md-...` ainda relevante).

---

## #4 — `ref-claude-md-hook-files-map-omits-pre-tool-use-02-telemetry-and-stop-05-telemetry-sub-scripts`

**Severidade:** MEDIUM
**Arquivos:** `CLAUDE.md:372-376` (Hook Files Map), `scripts/hooks/pre-tool-use/02-telemetry.sh`, `scripts/hooks/stop/05-telemetry.sh`

A tabela "Hook Files Map" lista o dispatcher `pre-tool-use.sh` ("Update checks, context cache"), mas:
- `02-telemetry.sh` (PreToolUse sub-script, 68 linhas, criado em `bd61ff7`) **não** aparece em nenhuma tabela ou lista
- `05-telemetry.sh` (Stop sub-script, 46 linhas, idem) aparece apenas indiretamente em `CLAUDE.md:359` ("`05-` | External reporting (telemetry) | `05-telemetry.sh`")

Logo, leitores do CLAUDE.md não conseguem mapear o hook PreToolUse para suas 2 responsabilidades atuais. Sub-script convention (CLAUDE.md:351-360) menciona prefixos `01-` a `99-` apenas para Stop — não há tabela equivalente para PreToolUse.

**Impacto positivo:** adicionar tabela "PreToolUse Sub-script Convention" simétrica à de Stop dá visibilidade ao 02-telemetry e prepara para extensões futuras.

**Impacto negativo:** mais ~10 linhas no CLAUDE.md (anti-padrão dado seu tamanho).

---

## #5 — `ref-templates-backlog-template-md-orphan-confirmed-by-scanner-but-skill-shared-backlog-template-has-inline-template`

**Severidade:** MEDIUM
**Arquivos:** `templates/backlog-template.md`, `skills/shared/backlog-template/SKILL.md`

`bash helpers/orphan-template-scan.sh` reporta:

```
ACTION REQUIRED — Orphan templates (no agent/skill/command references):
  · templates/backlog-template.md
```

Investigando: `skills/shared/backlog-template/SKILL.md` (171 linhas) **embute o template inline** em vez de carregar `templates/backlog-template.md`. Mesma anti-pattern de `scripts/new-adr.sh` (corrigido em `eb3168e` para `adr-template.md`). 

O fingerprint pai `ref-templates-adr-and-backlog-orphan-since-creation-2026-05-13-no-loader-wired` (2026-05-16) endereçou apenas `adr-template`; `backlog-template` continua órfão **2 dias depois**.

**Impacto positivo:** consolidar fonte da verdade no template; reduz `SKILL.md` em ~80 linhas.

**Impacto negativo:** se a skill `backlog-template` for invocada via `Skill` tool e o arquivo `.md` não estiver no path resolvable, falha silenciosa (cross-cut com `ref-templates-dir-shipped-but-not-symlinked-relative-path-broken-from-agent-cwd` — 2026-05-15).

---

## #6 — `ref-orphan-skill-scan-reports-design-system-audit-duplicate-load-in-ui-ux-designer-introduced-in-uknown-commit`

**Severidade:** MEDIUM
**Arquivo:** `agents/ui-ux-designer.md:49,85`

Output do scanner:
```
ACTION SUGGESTED — duplicate skill loads detected:
  · agents/ui-ux-designer.md loads skills/design/design-system-audit/SKILL.md more than once
```

Verificação manual:
- Linha 49: `` - `skills/design/design-system-audit/SKILL.md` — for reading and documenting the current visual state``
- Linha 85: `See the **Design System Creation** section in `skills/design/design-system-audit/SKILL.md` (already loaded above)`

O 2º match é **referência narrativa** ("already loaded above"), não um load duplicado real. O scanner não distingue narrativa de carregamento — falso positivo conceitual. Isso é cross-cut com o fingerprint pai `ref-orphan-skill-scan-warn-section-still-reports-pre-2026-05-13-13-duplicate-loads-as-warnings-not-as-errors-after-fingerprint-Executed-marked-on-2026-05-13` (2026-05-17), mas com **angle de classificação**: o scanner precisa distinguir 3 tipos de menção (Load ✓, "already loaded above" ✗, link relativo ✗).

**Impacto positivo:** reduz alarme falso constante no Stop hook (atualmente sempre reporta esta linha).

**Impacto negativo:** mais lógica no scanner aumenta complexidade; precisa de heurística para detectar "narrative reference".

---

## #7 — `ref-orphan-skill-scan-reports-update-md-duplicate-load-of-interaction-patterns-actual-duplicate`

**Severidade:** MEDIUM
**Arquivo:** `commands/update.md:1,7`

Diferentemente de #6, este é um **duplicate real**:

```
Line 1: Load `skills/shared/interaction-patterns/SKILL.md` before asking the user any question with a finite set of answers.
Line 7: **Interaction rule:** All yes/no and multiple-choice prompts in this command use the `AskUserQuestion` tool as defined in `skills/shared/interaction-patterns/SKILL.md`.
```

Linha 1 é o load real; linha 7 é citação contextual. Mesma classe do #6 mas em comando. Atualmente o scanner mistura ambos os tipos.

**Impacto positivo:** elimina uma menção redundante; restaura clean output do scanner.

**Impacto negativo:** mínimo — alteração de 1 linha.

---

## #8 — `ref-telemetry-honors-pref-but-pref-defaults-true-on-fresh-install-without-prompt-on-non-interactive-curl-bash`

**Severidade:** HIGH
**Arquivos:** `scripts/install.sh:420-455`, `scripts/helpers/telemetry-send.sh:42-52`

Verificação do flow:
1. `install.sh:440` faz prompt interativo `Enable anonymous telemetry? [Y/n]:` — default `Y`
2. `install.sh:453-456` lê o resultado e define `telemetry: true` ou `false` em `preferences.json`
3. **Em modo não-interativo** (típico `curl … | bash` ou pipe de heredoc), o prompt cai automaticamente para `Y` sem o usuário ver

**Resultado:** instalações automatizadas (CI/CD, dotfiles managers, scripts de provisão) entram com telemetria ON por padrão sem consentimento explícito. PRIVACY.md afirma "opt-out", mas o opt **default** em modo não-interativo é não-óbvio.

**Impacto positivo:** alterar default para `false` em modo non-interactive (`[ ! -t 0 ] && telemetry=false`) alinha consentimento real ao texto da PRIVACY.md.

**Impacto negativo:** reduz volume de eventos coletados; pode subutilizar o investimento em PostHog.

---

## #9 — `ref-privacy-md-not-listed-in-claude-md-file-structure-nor-in-readme-toc`

**Severidade:** MEDIUM
**Arquivos:** `PRIVACY.md`, `CLAUDE.md:222-237`, `README.md`, `README.pt-BR.md`

PRIVACY.md (2557 B, commit `9f1826d`) foi criado mas:
- Não aparece no bloco "File Structure" do CLAUDE.md (✗)
- `README.md` menciona `telemetry` em linha 226 mas **não linka** para PRIVACY.md (✗)
- `README.pt-BR.md` idem (✗)

Logo, um usuário lendo o README para entender telemetria não acha o link para o documento detalhado de privacidade.

**Impacto positivo:** 1 linha em CLAUDE.md, 1 link cruzado em README; trivial.

**Impacto negativo:** nenhum.

---

## #10 — `ref-skills-mobile-ios-and-android-skills-too-thin-vs-ios-hig-material-design-overlap-without-clear-boundary`

**Severidade:** MEDIUM
**Arquivos:** `skills/mobile/ios/SKILL.md` (33 linhas), `skills/mobile/ios-hig/SKILL.md` (218 linhas)

A skill `ios` recém-criada (commit `c2d2499`) tem 33 linhas e **redireciona para `ios-hig`** no primeiro bullet:

```md
## Design & UX
- Load `skills/mobile/ios-hig/SKILL.md` for the full reference...
```

Status:
- `skills/mobile/ios/SKILL.md` cobre: design (1 redirecionamento), permissions, code signing, SwiftUI
- `skills/mobile/ios-hig/SKILL.md` cobre: 218 linhas detalhadas de HIG

Pergunta de design não-respondida: qual a fronteira entre `ios` e `ios-hig`? Se `ios` virou wrapper raso, ou consolida tudo em `ios-hig` (renomeando), ou move conteúdo único do `ios-hig` para `references/`. Caso simétrico no Android.

Conta como sub-escopo do `agent-mobile-developer-ios-android-platform-blocks-60-lines-no-platform-skills` (2026-05-18 ✅), com **angle de pós-execução**: a extração foi feita, mas o resultado é **assimétrico** (ios=33, ios-hig=218).

**Impacto positivo:** consolidar elimina ambiguidade de qual skill carregar.

**Impacto negativo:** reorg de skills criadas no mesmo dia parece prematura — alternativa é esperar 1 sprint e re-avaliar.

---

## #11 — `ref-helpers-archive-index-script-shipped-but-not-hooked-no-cronjob-no-pre-tool-use-no-stop-trigger`

**Severidade:** HIGH
**Arquivo:** `helpers/archive-index.sh`, `scripts/hooks/{stop,pre-tool-use}/*.sh`

O script existe (66 linhas, commit `eb3168e`) e funciona, mas:
- Não é invocado por **nenhum** sub-script de Stop ou PreToolUse
- Não é mencionado em CI workflow
- Não é chamado pelo `update.sh` nem `install.sh`

Em 90 dias (a partir do oldest entry 2026-05-06), a primeira entrada elegível para archivação ficará disponível **mas o script não rodará automaticamente**. O fingerprint pai foi marcado ✅ Executed, mas a **automação prometida** (CLAUDE.md:20 "pode ser rotacionado a cada 90 dias") não foi implementada.

**Impacto positivo:** adicionar `06-archive-index.sh` ao Stop dispatcher com gate de execução (uma vez por dia, somente se passou 90d) materializa a automação prometida.

**Impacto negativo:** ~5ms adicional por Stop em sessões que não precisam disso (mitigável com TTL persistido em `.claude/user-data/.archive-index-lastrun`).

---

## Resumo

| # | Fingerprint | Severidade | Tipo |
|---|------------|-----------|------|
| 1 | auto-docs-rule-violated-changelog-unreleased-missing-7-features-from-2026-05-18-window | HIGH | Drift |
| 2 | ref-changelog-references-scripts-path-not-helpers-after-refactor | MEDIUM | Drift |
| 3 | ref-claude-md-file-structure-omits-helpers-and-privacy-and-claude-md-folder | HIGH | Drift |
| 4 | ref-claude-md-hook-files-map-omits-pre-tool-use-02-telemetry-and-stop-05-telemetry-sub-scripts | MEDIUM | Drift |
| 5 | ref-templates-backlog-template-md-orphan-confirmed-by-scanner-but-skill-shared-backlog-template-has-inline-template | MEDIUM | Órfão |
| 6 | ref-orphan-skill-scan-reports-design-system-audit-duplicate-load-in-ui-ux-designer-introduced-in-uknown-commit | MEDIUM | Falso positivo scanner |
| 7 | ref-orphan-skill-scan-reports-update-md-duplicate-load-of-interaction-patterns-actual-duplicate | MEDIUM | Duplicate real |
| 8 | ref-telemetry-honors-pref-but-pref-defaults-true-on-fresh-install-without-prompt-on-non-interactive-curl-bash | HIGH | Privacy gap |
| 9 | ref-privacy-md-not-listed-in-claude-md-file-structure-nor-in-readme-toc | MEDIUM | Drift |
| 10 | ref-skills-mobile-ios-and-android-skills-too-thin-vs-ios-hig-material-design-overlap-without-clear-boundary | MEDIUM | Coerência |
| 11 | ref-helpers-archive-index-script-shipped-but-not-hooked-no-cronjob-no-pre-tool-use-no-stop-trigger | HIGH | Automação |
