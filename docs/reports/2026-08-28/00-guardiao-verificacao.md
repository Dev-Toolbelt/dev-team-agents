# Fases 1 e 1b — Verificação guardiã (2026-08-28)

**Data:** 2026-08-28 · **Baseline:** `HEAD` = `a67cac9` · **Baseline anterior:** `a67cac9`

## O fato que estrutura este pass: o baseline não se moveu

`git rev-parse --short HEAD` devolve `a67cac9` — **o mesmo sha registrado como baseline do pass de
2026-08-21**. `git log --format='%h %ad' --date=short -1` confirma: o último commit do repositório é
de **2026-08-21**, sete dias atrás. O delta de código desde o pass anterior é **zero arquivo em zero
commit**.

A árvore de trabalho, porém, não está limpa:

```
 M docs/reports/_index.md
?? docs/reports/2026-08-21/
```

Os sete arquivos de relatório do pass de 2026-08-21 e as **37 fingerprints** que ele registrou no
banco nunca foram commitados. `git show HEAD:docs/reports/_index.md | grep -cE '^- \`[a-z]'` devolve
**176**; a versão da árvore de trabalho devolve **213**. A diferença de 37 é exatamente o pass
anterior, vivo apenas no disco desta máquina há uma semana.

Isso tem duas consequências metodológicas, e ambas foram aplicadas:

1. **O banco autoritativo é a versão da árvore de trabalho**, não a de `HEAD`. Todas as portas
   anti-duplicação deste pass rodaram contra ela — caso contrário os 37 achados de 2026-08-21 seriam
   redescobertos como novos.
2. **A Fase 1 do pass anterior continua válida por construção.** Ela verificou 48 de 119, incluindo
   **todos** os 18 HIGH e MEDIUM-HIGH, contra este mesmo `a67cac9`. Sem nenhum commit desde então,
   nenhum daqueles vereditos pode ter mudado. Reverificá-los seria gastar orçamento para reproduzir
   um resultado conhecido.

A amostragem deste pass foi portanto redirecionada para o **complemento**: os 73 itens do conjunto
verificável que o pass anterior **não** cobriu. Todos são MEDIUM, LOW-MEDIUM ou LOW — a confirmação
mecânica de que a fatia HIGH/MEDIUM-HIGH está integralmente coberta.

---

## Método e cobertura

| Item | Valor |
|---|---|
| Fingerprints vivos no banco (árvore de trabalho) | 213 |
| Conjunto verificável (✅ Executed + ⚠️ Partial) | 121 |
| Já verificados em 2026-08-21 contra este mesmo `HEAD` | 48 (inclui os 18 HIGH/MEDIUM-HIGH) |
| Não cobertos pelo pass anterior | 73 — todos MEDIUM ou abaixo |
| Critério de amostragem | conjunto > 60 → HIGH e MEDIUM-HIGH **todos** (já cobertos, 18/18) + **30% dos 73 restantes** = 22, amostra determinística |
| **Cobertura da Fase 1 — bloco novo** | **22 de 73 não cobertos (30%)** |
| **Cobertura da Fase 1 — acumulada contra `a67cac9`** | **70 de 121 (58%)** |
| Placar do bloco novo | **18 ✅ · 2 🟡 · 2 🔴** — 82% confirmado, **9,1% reaberto** |
| Placar acumulado contra `a67cac9` | **61 ✅ · 5 🟡 · 4 🔴** — 87% confirmado, **5,7% reaberto** |
| Conjunto aberto (sem marcador) | 79 → alvos da Fase 1b |
| **Mortalidade Fase 1b** | **0 de 50 (0%)** |

A taxa de reabertura do bloco novo (9,1%) e a acumulada (5,7%) estão **abaixo do limiar de
escalonamento de 15%**. A integridade do banco não é o achado principal deste pass — a ausência do
commit do pass anterior é.

Todos os 22 itens foram marcados na janela de **2026-07-31**, cujas oito commits de remediação são
`bbb311a`, `b4e219f`, `6919564`, `519ca7e`, `c7535b7`, `cc28900`, `2e12335` e `7736e20`. Cada
veredito foi ancorado em `git show` dessa janela, nunca na leitura do relatório-fonte.

---

## Fase 1 — Bloco de 22 itens

| # | Fingerprint | Marca original | Marca verificada | Commit examinado |
|---|---|---|---|---|
| 1 | `ref-haiku-residual-claude-md-note-after-executed…` | ✅ 2026-07-31 | ✅ Feito | `bbb311a` |
| 2 | `ref-templates-dir-shipped-but-not-symlinked-rel…` | ✅ 2026-07-31 | ✅ Feito | `6919564` + `7736e20` |
| 3 | `ref-skill-ui-libraries-shadcn-frontmatter-name-…` | ✅ 2026-07-31 | ✅ Feito | `c7535b7` |
| 4 | `ref-release-prep-skill-exists-twice-shared-88-l…` | ✅ 2026-07-31 | **🔴 Não feito** | `7736e20` (só `description`) |
| 5 | `ref-claude-md-hook-files-map-and-file-structure…` | ✅ 2026-07-31 | ✅ Feito | `bbb311a` |
| 6 | `ref-claude-md-file-structure-scripts-enumeratio…` | ✅ 2026-07-31 | ✅ Feito | `bbb311a` |
| 7 | `ref-claude-md-356-stop-subscript-convention-omi…` | ✅ 2026-07-31 | ✅ Feito | `bbb311a` |
| 8 | `ref-notification-system-content-triplicated-acr…` | ✅ 2026-07-31 | **🟡 Parcial** | `6919564` + `bbb311a` |
| 9 | `ref-claude-md-130-agent-creator-points-to-exter…` | ✅ 2026-07-31 | ✅ Feito | `bbb311a` |
| 10 | `ref-agent-creator-location` | ✅ 2026-07-31 | **🟡 Parcial** | `bbb311a` |
| 11 | `ref-three-reviewers-todo-fixme-issue-tracker-ti…` | ✅ 2026-07-31 | ✅ Feito | `b4e219f` |
| 12 | `ref-claude-md-hook-files-map-omits-pre-tool-use…` | ✅ 2026-07-31 | ✅ Feito | `bbb311a` + `cc28900` |
| 13 | `docs-sync-claude-md-package-exclusions` | ✅ 2026-07-31 | ✅ Feito | `bbb311a` |
| 14 | `auto-install-no-rollback-on-second-mv-failure` | ✅ 2026-07-31 | ✅ Feito | `2e12335` |
| 15 | `flow-stop-no-zombie-state-cleanup-discovery-loc…` | ✅ 2026-07-31 | **🔴 Não feito** | **nenhum** |
| 16 | `flow-stop-dispatcher-globs-all-sh-no-allowlist-…` | ✅ 2026-07-31 | ✅ Feito | `cc28900` |
| 17 | `flow-pre-tool-use-dispatcher-no-mention-of-sub-…` | ✅ 2026-07-31 | ✅ Feito | `bbb311a` + `cc28900` |
| 18 | `flow-02b-orphan-template-scan-lacks-devteam-no-…` | ✅ 2026-07-31 | ✅ Feito | `cc28900` |
| 19 | `flow-orphan-template-scan-runs-in-stop-but-only…` | ✅ 2026-07-31 | ✅ Feito | `c7535b7` |
| 20 | `ref-orphan-skill-scan-reports-design-system-aud…` | ✅ 2026-07-31 | ✅ Feito | `c7535b7` |
| 21 | `flow-check-fingerprint-uniqueness-scans-only-in…` | ✅ 2026-07-31 | ✅ Feito | `c7535b7` |
| 22 | `flow-readme-sync-ci-gate-checks-only-section-co…` | ✅ 2026-07-31 | ✅ Feito | `c7535b7` |

**Apuração:** 18 ✅ · 2 🟡 · 2 🔴

---

## Detalhes — os quatro vereditos divergentes

### 4. `ref-release-prep-skill-exists-twice-shared-88-lines-shipped-vs-claude-skills-181-lines-dev-divergent-content-no-sync-rule`

- **Alvo:** `skills/shared/release-prep/SKILL.md` · `.claude/skills/release-prep/SKILL.md`
- **Commit da janela:** `7736e20` — *docs: sync documentation with six waves of changes, enforce both
  size gates*. Tocou o alvo para reescrever **uma linha de `description`**
  (`-Pre-release checklist and versioning strategy…` → `+Pre-release checklist for dev-team-agents —
  semver bump, tagging, rollback.`)
- **Evidência no HEAD:** `wc -l` → `88 skills/shared/release-prep/SKILL.md` e
  `182 .claude/skills/release-prep/SKILL.md`; ambas declaram `name: release-prep` na linha 2.
  `grep -rn "release-prep" CLAUDE.md README.md helpers/ .github/` não retorna nada.
- **Veredito:** 🔴 **Não feito**
- **Por que a marcação diverge:** o único commit da janela que tocou qualquer um dos dois arquivos
  alterou uma linha de `description` no arquivo `shared/` — efeito colateral do corte de descrições
  de skills para o orçamento de 95 caracteres, não uma remediação desta constatação. As duas cópias
  continuam existindo com conteúdo divergente (88 vs. 182 linhas), destinos de instalação **opostos**
  (`shared/` embarca via `KEEP_ROOT`; `.claude/` é removido por `strip-tarball.sh`) e nenhuma regra
  de sincronização em `CLAUDE.md`, no README, nos helpers ou na CI. Nenhum commit posterior a
  `7736e20` tocou nenhum dos dois.

### 15. `flow-stop-no-zombie-state-cleanup-discovery-lock-and-worktree-session-persist-across-sessions`

- **Alvo:** `scripts/hooks/stop/` (sub-script de limpeza inexistente) · `scripts/hooks/session-start.sh`
- **Commit da janela:** **nenhum**. `cc28900` reescreveu `stop.sh` e adicionou `03b-`, `99b-` e
  `lib/touched-paths.sh`, mas nenhuma lógica de limpeza de estado.
- **Evidência no HEAD:** `grep -rn "\.worktree-session\|discovery-lock" scripts/` retorna **uma**
  ocorrência — `scripts/install.sh:931` — `_add_gitignore ".dev-team-agents/.worktree-session"`.
  `ls scripts/hooks/stop/` lista 10 sub-scripts ativos, nenhum de cleanup; `session-start.sh` também
  não toca nenhum dos dois arquivos.
- **Veredito:** 🔴 **Não feito**
- **Por que a marcação diverge:** o estado no HEAD é idêntico ao descrito no relatório de 2026-07-30.
  `.worktree-session` continua sem TTL e sem rotina de limpeza. A consequência é ativa, não teórica:
  o passo 1 da cascata canônica manda todo agente de código "follow the stored decision **silently**"
  ao encontrar o arquivo, de modo que um marcador remanescente de um branch já mesclado direciona em
  silêncio a próxima sessão não relacionada. A marcação ✅ não tem nenhum commit correspondente.

### 8. `ref-notification-system-content-triplicated-across-04-notifier-sh-notifier-skill-and-claude-md-notifications-md-stop-subscript-table-already-drifted-omitting-05-telemetry`

- **Alvo:** `scripts/hooks/stop/04-notifier.sh` · `skills/shared/notifier/SKILL.md` ·
  `CLAUDE-md/notifications.md`
- **Commit da janela:** `6919564` (tips saem do bash para `scripts/hooks/stop/tips/tips.{en,pt-BR,es}.txt`)
  + `bbb311a` (adiciona a linha `05-` à tabela de sub-scripts)
- **Evidência no HEAD:** `CLAUDE-md/notifications.md:73` — "`| 05- | External reporting (telemetry) |
  05-telemetry.sh |`" e `:59` — "Tip text lives in **locale data files**, never in the script".
  Porém `skills/shared/notifier/SKILL.md:113-133` ainda contém `## Tip of Session`, a fórmula
  `Index: (day_of_month - 1) % 15` e a tabela completa com os 15 textos.
- **Veredito:** 🟡 **Parcialmente feito**
- **Sub-escopo faltante:** dois dos três vértices foram resolvidos — a deriva da tabela de
  sub-scripts e a extração dos textos de tip do bash. O terceiro não: `skills/shared/notifier/SKILL.md`
  segue carregando fórmula e textos na íntegra, agora como **quarta** cópia paralela a
  `scripts/hooks/stop/tips/tips.en.txt`. Nenhum commit posterior removeu o bloco.

### 10. `ref-agent-creator-location`

- **Alvo:** `.claude/skills/agent-creator/SKILL.md` vs. `skills/skill-creator/SKILL.md`
- **Commit da janela:** `bbb311a` — reescreveu a célula de `agent-creator` na tabela *User-Invocable
  Skills*, mas não moveu nenhum dos dois arquivos.
- **Evidência no HEAD:** `CLAUDE.md:196` — "…tracked in this repo, but `.claude/` is stripped from
  the package by `scripts/lib/strip-tarball.sh`, so it never reaches an installed project."
  `git log -- .claude/skills/agent-creator/` mostra `c9cb5c2` como último commit — **anterior à
  janela**.
- **Veredito:** 🟡 **Parcialmente feito**
- **Sub-escopo faltante:** o que `bbb311a` entregou foi a documentação honesta do destino de
  empacotamento — que é a remediação do fingerprint irmão
  `ref-claude-md-130-agent-creator-points-to-external-claude-skills-path…` (item 9), não deste. A
  condição estrutural permanece: duas skills de autoria irmãs, registradas na mesma tabela, vivem em
  árvores diferentes com destinos de instalação opostos, e `agent-creator` segue inalcançável por
  qualquer provider instalado. Classificado 🟡 e não 🔴 porque o commit da janela tocou o local de
  registro compartilhado e tornou a divergência explícita — apenas não a normalizou.

---

## Detalhes — cinco ✅ representativos

### 2. `ref-templates-dir-shipped-but-not-symlinked-relative-path-broken-from-agent-cwd`

- **Alvo:** `agents/setup-assistant.md`, `skills/shared/runbook/SKILL.md`,
  `skills/shared/plan-mode/SKILL.md`, `skills/shared/project-context/SKILL.md`, `CLAUDE.md`
- **Commit da janela:** `6919564` (as seis referências `templates/…` nuas passaram ao caminho
  instalado) + `7736e20` (regra de autoria em `CLAUDE.md`)
- **Evidência no HEAD:** `agents/setup-assistant.md:33` — "present a plan using
  `.dev-team-agents/templates/plan-template.md`"; `CLAUDE.md:270` — "**Reference templates by their
  installed path** — `.dev-team-agents/templates/<name>.md`".
  `bash helpers/orphan-template-scan.sh --quiet` sai 0.
- **Veredito:** ✅ Feito

### 3. `ref-skill-ui-libraries-shadcn-frontmatter-name-shadcn-ui-with-hyphen-while-directory-basename-is-shadcn-no-validator-enforces-name-equals-dir-convention`

- **Alvo:** `skills/ui-libraries/shadcn/SKILL.md` · `helpers/agent-lint.sh`
- **Commit da janela:** `c7535b7` — *ci: close validator and enforcement gaps, repair the rotation
  helper* (`-name: shadcn-ui` → `+name: shadcn`, mais +130 linhas em `agent-lint.sh`)
- **Evidência no HEAD:** `skills/ui-libraries/shadcn/SKILL.md:2` — "`name: shadcn`";
  `helpers/agent-lint.sh:308` — "`ERRORS+=("  · ${rel}: name '${name}' does not match directory
  '${dir_name}' (they must be identical)")`", complementado por `check_skill_name_uniqueness()` em
  `:330`. A remediação entregou **o dado e o gate**.
- **Veredito:** ✅ Feito

### 14. `auto-install-no-rollback-on-second-mv-failure`

- **Alvo:** `scripts/install.sh`
- **Commit da janela:** `2e12335` — *fix(install): make the swap failure-safe and stop enabling
  telemetry without consent* (+240 linhas)
- **Evidência no HEAD:** `scripts/install.sh:200` — "`SWAP_DONE=false`"; `:275` — "`trap _cleanup
  EXIT`". O padrão `rm -rf "$INSTALL_DIR"; mv …` foi substituído por staging em `NEW_DIR`,
  movimentação do antigo para `OLD_DIR` e restauração automática via `_cleanup()` quando
  `SWAP_DONE != true`.
- **Veredito:** ✅ Feito

### 16. `flow-stop-dispatcher-globs-all-sh-no-allowlist-or-per-subscript-toggle-any-dropped-file-auto-executes`

- **Alvo:** `scripts/hooks/stop.sh`
- **Commit da janela:** `cc28900` — *fix(hooks): gate, decompose and harden the lifecycle dispatchers*
- **Evidência no HEAD:** `scripts/hooks/stop.sh:57` — "`SUBSCRIPT_RE='^[0-9]{2}[a-z]?-[a-z0-9]([a-z0-9-]*[a-z0-9])?\.sh$'`",
  com `continue` e traço via `DEVTEAM_HOOK_DEBUG` para arquivos não conformes. O mesmo mecanismo
  virou o toggle por sub-script: `_disabled-04-notifier.sh` e `_disabled-99-graphify-refresh.sh`
  estão desativados por renomeação fora do padrão, documentado em `CLAUDE-md/hooks.md` § Disabled
  Hooks. A remediação cobriu os **dois** sub-escopos do fingerprint.
- **Veredito:** ✅ Feito

### 21. `flow-check-fingerprint-uniqueness-scans-only-index-md-blind-to-documented-archive-rotation-cross-file-dupes-undetected`

- **Alvo:** `helpers/check-fingerprint-uniqueness.sh`
- **Commit da janela:** `c7535b7` (+54 linhas)
- **Evidência no HEAD:** `helpers/check-fingerprint-uniqueness.sh:21-24` —
  "`[ -f "$INDEX_FILE" ] && BANK_FILES+=("$INDEX_FILE")`" seguido do laço sobre
  `find "$REPORTS_DIR" -maxdepth 1 -name '_index-archive-*.md'`; a saída passou a reportar o arquivo
  de origem de cada ocorrência.
- **Veredito:** ✅ Feito

---

## Fase 1b — Validade dos achados abertos

### Método e cobertura

| Métrica | Valor |
|---|---|
| Achados abertos no banco (sem marcador) | 79 |
| Verificados integralmente (passes de 2026-07-31, 08-12 e 08-14) | 42 |
| Amostrados (os 37 do pass de 2026-08-21) | 8 |
| **Total checado no HEAD `a67cac9`** | **50** |

Os 37 achados de 2026-08-21 foram registrados **contra este mesmo `a67cac9`** e o HEAD não se moveu
desde então, logo nenhum deles pode ter mudado de estado. Foram amostrados 8 — um por eixo,
priorizando HIGH e alvos executáveis — e **os 8 reproduziram**, consistente com a premissa. Os outros
42 foram verificados um a um.

### Resultado

**Nenhum achado aberto deixou de reproduzir.** Zero 🟢, zero ⚰️, 50 de 50 ainda presentes no HEAD.

**Mortalidade da Fase 1b: 0 de 50 (0%).**

Esse número é o esperado e não é um sinal de saúde: com zero commits desde o registro, não havia
mecanismo pelo qual um achado pudesse ter sido corrigido de passagem. A mortalidade zero deste pass
mede a imobilidade do repositório, não a durabilidade do banco.

### Derivas observadas — o achado reproduz, mas o texto do banco envelheceu

Onze entradas continuam válidas com o alvo deslocado ou o problema **ampliado**. Nenhuma muda de
marcador; todas merecem releitura antes de virarem tarefa.

| Fingerprint | Deriva |
|---|---|
| `docs-sync-claude-md-102-states-skill-desc-strict-false…` | O par contraditório migrou de `CLAUDE.md:102` para `:129`, contra `helpers/agent-lint.sh:98` (`SKILL_DESC_STRICT=true`) |
| `docs-sync-claude-md-173-says-all-devteam-commands-load-current-context…` | As "quatro exceções" viraram **seis** (`CLAUDE.md:252`) contra o "All `/devteam:*` commands" de `:203`. A contradição **piorou** |
| `docs-sync-reports-index-md-99-legend-comment-claims-all-131-entries-unmarked…` | A legenda ainda diz "All 131 entries below are unmarked"; o banco tem **213** entradas e **134** com marcador |
| Seis fingerprints do `02c-full-suite-guard.sh` | O `sed` guloso migrou da linha 22 para `:31`; as **seis** patologias do guard seguem intactas no mesmo arquivo |
| `flow-learn-run-marker-records-commit-time-not-run-time` | `commands/commit.md` foi reestruturado por `576dcfa` e o guard compara `<head-sha>`, mas `commands/learn.md:166` grava o marcador **antes** do auto-commit do Step 5 — o HEAD sempre se move depois e o skip segue inalcançável. `commit.md:179` afirma o contrário |
| `gov-repo-gitignore-omits-three-installer-written-entries` | Atenuado: `.gitignore` ganhou `.worktree-session`, mas seguem faltando `!…/user-data/graphify.json` e `.dev-team-agents/.learn-last-run` |
| `install.sh` grande · `validate-commit-msg.sh` sem registro (legado, sem slug) | `scripts/install.sh` foi de 1086 → **1240** linhas; `validate-commit-msg.sh` segue sem registro como git hook (única invocação: `commands/commit.md:145`) |
| `docs-sync-changelog-unreleased-omits-full-suite-guard-and-orchestration-deltas` | A seção `[Unreleased]` deixou de existir, mas `c03f898` e `21fceb4` continuam sem entrada; a menção a "Liveness" em `CHANGELOG.md:160` pertence a `[2.32.1]`, anterior aos dois |
| `docs-sync-hooks-md-64-full-suite-guard-examples-predate-wrapper-detection` | Além dos exemplos, `CLAUDE-md/hooks.md:64` ainda afirma "it never blocks" — desatualizado desde que `abb8483` introduziu o `exit 2` |
| `agent-line-cap-205-documented-in-claude-md-vs-211-enforced…` e `agent-three-at-exactly-211-line-ceiling…` | `size-limits.sh:44` segue em `AGENT_LIMIT=211` contra `CLAUDE.md:92`/`:313` ("enforces 205"); em 211 hoje: `frontend-developer`, `qa-specialist`, `software-architect`; logo atrás `devops-specialist` (210) e `backend-reviewer` (209) |
| `skill-orchestration-spawn-integrity-unreachable-from-devteam-commands` e `token-orchestration-skill-377-lines…` | A contagem de comandos subiu de 34 para **35** e `grep -l 'orchestration/SKILL.md' commands/*.md` segue vazio; a skill cresceu de 377 → **391** linhas, ainda sem `references/` |

---

## Correções de marcação a aplicar no `_index.md`

| Fingerprint | Correção |
|---|---|
| `ref-release-prep-skill-exists-twice-…` | `— 🔴 **Reaberto na verificação de 2026-08-28:** …` |
| `flow-stop-no-zombie-state-cleanup-…` | `— 🔴 **Reaberto na verificação de 2026-08-28:** …` |
| `ref-notification-system-content-triplicated-…` | `— 🟡 **Parcial na verificação de 2026-08-28:** …` |
| `ref-agent-creator-location` | `— 🟡 **Parcial na verificação de 2026-08-28:** …` |
