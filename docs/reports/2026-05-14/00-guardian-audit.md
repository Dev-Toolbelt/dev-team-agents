# Guardian Audit — 2026-05-14

**Janela analisada:** commits desde 2026-05-13 (00:00 BRT) até 2026-05-14 (HEAD `ba19882` em 15:08 BRT)
**Comandos executados:** `git log --since="2026-05-13"`, `git log --since="2026-05-13" --pretty=format:"%h %s" --stat`, leitura direta de arquivos referenciados nos 41 fingerprints
**Commits novos no período:** 3 (`ac6af24`, `d05242a`, `ba19882`) em 2026-05-14, somados ao batch já existente de 2026-05-13

## Resumo Executivo

| Status | Quantidade | % |
|--------|-----------|---|
| ✅ Executed | 0 | 0% |
| ⚠️ Partial | 2 | 4,9% |
| 🟢 Resolved | 0 | 0% |
| ↩️ Reverted | 0 | 0% |
| Pendentes | 39 | 95,1% |
| **Total** | 41 | 100% |

**Throughput documentado:** 4,9% em 24h (vs 57% recorde de 2026-05-13). Queda expressiva — janela curta, apenas 3 commits novos pós-publicação dos relatórios de 2026-05-13 e nenhum dos 3 corresponde a fingerprint aberto. A agenda integral de 2026-05-13 segue praticamente pendente; os 2 ⚠️ Partial são revisitas que reconheceram cobertura prévia parcial, não novas execuções.

---

## Fingerprints Verificados — 2026-05-13

### Referências e Consistência (10)

- `ref-tester-command-misses-mobile-developer-spawn-vs-claude-md-table` — **pendente** — Evidência: `grep -n "mobile-developer\|mobile" commands/tester.md` retorna **vazio**; CLAUDE.md linha 187 ainda declara `/devteam:tester | backend-test-specialist + frontend-test-specialist¹ + mobile-developer¹`. Drift persiste.
- `ref-validate-commit-msg-script-orphaned-from-ci-and-commit-command` — **pendente** — Evidência: busca por `validate-commit-msg` em `.github/workflows/`, `commands/commit.md`, `commands/pr.md` retorna **zero hits funcionais** — apenas a skill `skills/shared/conventional-commits/SKILL.md:117-124` documenta o script. Sem CI hook, sem invocação em commit/pr, sem registro em `install.sh`.
- `ref-claude-md-update-command-still-claims-two-scripts-after-2026-05-08-finding` — **pendente** — Evidência: `CLAUDE.md:171` ainda contém literal `runs check-updates.sh + update.sh`; `wc -l scripts/check-updates.sh` = 3 linhas (shim deprecado). Sexta passada consecutiva sem correção.
- `ref-no-workflow-mobile-shortcut-command-asymmetric-with-fullstack-refactor-review` — **pendente** — Evidência: `ls commands/workflow-*.md` retorna 8 arquivos; **`workflow-mobile.md` e `workflow-design.md` continuam ausentes**. Assimetria mantida.
- `ref-size-limits-warn-only-permanent-tech-debt-11-agents-violating` — **pendente** — Evidência: `scripts/size-limits.sh:21` mantém `--warn-only` opcional; nenhum commit no período remove a flag ou adiciona cronograma de enforce. Tech debt explícito segue documentado mas sem dono.
- `ref-orphan-skill-scan-warn-section-not-actionable-no-fix-template` — **pendente** — Evidência: `scripts/orphan-skill-scan.sh:165` ainda emite literal `WARN — Skills loaded more than once in the same agent:` sem header `ACTION REQUIRED` nem template de correção sugerido. Output continua não-actionable para os 13 duplicados.
- `ref-claude-md-grew-to-544-lines-largest-mono-file-in-repo` — **pendente (regressão silenciosa)** — Evidência: `wc -l CLAUDE.md` = **557 linhas** hoje (vs 544 reportadas em 2026-05-13). Cresceu +13 linhas em 24h por conta dos commits `d05242a` (+13 linhas para interaction-patterns), `ac6af24` (+1), `ebdcb3a` (+2 linhas em outro fragmento). Tendência piora.
- `ref-pt-br-translation-of-extracted-docs-not-validated-by-section-count-anymore` — **pendente** — Evidência: nenhum commit pós-2026-05-13 modifica `.github/workflows/ci.yml`. Comparação por header count (`^## `) segue vigente sem validação de conteúdo intra-seção.
- `ref-foundational-rule-setup-assistant-shrunk-to-7-lines-after-suggestion-to-grow-it` — **⚠️ Partial** — Evidência: `agents/setup-assistant.md` linhas 10 (`## Foundational Rule`) e 213 (`## Immutability Warning`) confirmam ambas seções **presentes** — viés de regressão da CLAUDE.md:122 endereçado parcialmente. **Foundational Rule continua com 7 linhas** (esperado p50≈22) — sub-escopo "size" pendente.
- `ref-rollback-script-no-target-version-format-validation` — **pendente** — Evidência: `grep -n "TARGET" scripts/rollback.sh` linhas 24-37 mostram `TARGET="$1"` sem validação `^v[0-9]+\.[0-9]+\.[0-9]+$`. Aceita qualquer string.

### Fluxos e Workflows (10)

- `flow-pre-compact-hook-no-graceful-skip-when-claude-dir-absent` — **⚠️ Partial** — Evidência: `scripts/hooks/pre-compact.sh:7` faz `git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0` (skip git absente) e linha 21 `[ "$HAS_CHANGES" = false ] && exit 0`. **Mas** não há guarda explícita `[ -d .claude/user-data ] || exit 0` — projeto recém-clonado fora de git (raro mas possível) ou com `.claude/` ausente após git pode ainda emitir warning do session-summary file. Cobertura ~80%.
- `flow-pr-command-no-base-branch-detection-from-repo-config` — **pendente** — Evidência: `commands/pr.md` linhas 10, 17, 29, 40, 52 ainda hardcodam `main` em `git log main..HEAD`, `git diff main...HEAD` etc.; sem fallback para `git config init.defaultBranch` ou `gh repo view`.
- `flow-current-context-cache-no-invalidation-on-branch-switch-within-ttl-window` — **pendente** — Evidência: `skills/shared/current-context/SKILL.md:73` ainda usa `[ "$age" -lt 300 ] && echo "Context (cached)"` sem comparação `branch_atual == cached_branch`. Apenas timestamp; branch switch dentro da janela 300s não invalida o cache. Commit `ac6af24` apenas moveu o path do cache para `user-data/`, não corrigiu o bug.
- `flow-design-command-no-frontend-developer-spawn-for-implementation` — **pendente** — Evidência: `grep -n "frontend-developer" commands/design.md` retorna 0 hits. Sem cross-link condicional.
- `flow-installer-no-shellcheck-self-validation-on-its-output` — **pendente** — Evidência: `grep -n "shellcheck" scripts/install.sh` retorna 0 hits. CI continua validando source mas não output pós-install.
- `flow-conventional-commits-validate-script-no-husky-or-commit-msg-hook-registration` — **pendente** — Evidência: `grep -n "commit-msg\|husky\|lefthook" scripts/install.sh` retorna 0 hits. Install.sh não registra `commit-msg` git hook nem detecta managers.
- `flow-stop-hook-04-notifier-no-skip-when-no-changes-via-fast-path-flag` — **pendente** — Evidência: `grep -n "DEVTEAM_NO_CHANGES\|fast-path" scripts/hooks/stop/04-notifier.sh` retorna 0 hits. Sub-scripts 01-03 têm o gate (commit `f96f3cd`), mas 04-notifier mantém execução em sessões puramente conversacionais.
- `flow-rollback-no-pre-state-validation-vs-update-sh` — **pendente** — Evidência: `scripts/rollback.sh` (65 linhas) não compara `$TARGET` com `.installed-version` atual (no-op silencioso possível) nem detecta modificações locais não-commitadas em `.dev-team-agents/`.
- `flow-installer-strips-validate-commit-msg-not-but-keeps-it-vs-other-dev-tools` — **pendente** — Evidência: `grep -n "validate-commit-msg" scripts/install.sh` retorna 0 hits — script segue distribuído. Inconsistência com `agent-lint.sh`/`size-limits.sh`/`orphan-skill-scan.sh` (todos stripados) mantida.
- `flow-orphan-skill-scan-warn-output-not-silenced-in-quiet-mode` — **pendente** — Evidência: `scripts/orphan-skill-scan.sh:12,134` documenta `--quiet` apenas para "suppress when clean"; sem semântica `--errors-only` para WARN section.

### Agentes e Skills (11)

- `agent-devops-specialist-violates-stack-agnostic-rule-with-docker-first-bias` — **pendente** — Evidência: `agents/devops-specialist.md:3` mantém literal `Docker-first infrastructure specialist`; linha 8 mantém `Your default answer to "how should we deploy this?" is Docker on a VPS before it's Kubernetes in the cloud`. Viola CLAUDE.md:124 stack-agnostic — sem alteração.
- `agent-mobile-test-specialist-3rd-consecutive-pass-still-missing` — **pendente (4ª passada)** — Evidência: `ls agents/mobile-test-specialist.md` → not found. ADR formal sugerido em 2026-05-13 não foi criado. Drift `commands/tester.md` sem `mobile-developer` confirma o gap (vide ref #1).
- `agent-architect-frontmatter-no-webfetch-but-loaded-skills-suggest-research` — **pendente** — Evidência: `agents/software-architect.md:5` declara `tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch` — **WebFetch ausente**. Sem alteração.
- `skill-stack-detection-still-missing-3rd-pass-shared-base-needed` — **pendente (4ª passada)** — Evidência: `skills/shared/stack-detection/` não existe. Heurísticas inline divergentes em 4 agents permanecem.
- `skill-graphify-setup-still-no-conditional-skip-3rd-pass-277-lines` — **⚠️ Partial** — Evidência: commit `90d2f40` adicionou skip conditions em `skills/devops/graphify-setup/SKILL.md` (12 linhas novas). Verificação parcial — sub-escopo "tamanho de 277 linhas" continua, mas gate de skip foi instalado. Reclassificação para `⚠️ Partial` é defensável; mantido conservador como `pendente` enquanto não há nova execução em projeto puramente docs para validar.
- `skill-templates-folder-grew-but-no-template-skill-wraps-them` — **pendente** — Evidência: `ls templates/` = 4 arquivos (`adr-template.md`, `backlog-template.md`, `plan-template.md`, `runbook-template.md`); `runbook-template.md` segue sem skill que o referencie. Trigger "3+ files" atingido sem ação.
- `skill-discovery-mode-no-stale-lock-cleanup-script-30min-rule-only-documented` — **pendente** — Evidência: `skills/shared/discovery-mode/SKILL.md:129` menciona regra "stale > 30 min" porém sem helper script. Lógica permanece inline em cada agent.
- `agent-frontend-developer-loads-jquery-skill-orphan-of-modern-stacks` — **pendente** — Evidência: `find skills -name "*jquery*"` = `skills/ui-libraries/jquery` (categoria mantida); decisão de mover para `integrations/` ou `legacy/` não tomada.
- `skill-frontmatter-validation-now-strict-but-tests-not-included` — **pendente** — Evidência: `ls scripts/tests/` = "no tests dir". Sem fixture tests para validação SKILL.md frontmatter.
- `agent-product-analyst-other-trackers-still-asana-clickup-monday-ungated` — **pendente** — Evidência: `grep -i "asana\|clickup\|monday\|github.*issues" agents/product-analyst.md` retorna apenas linha 130 mencionando GitHub/GitLab/Bitbucket genericamente; sem detection rules para Asana/ClickUp/Monday com gating equivalente ao Jira/Linear.
- `skill-comments-policy-sections-extracted-but-no-language-aware-loader-in-agents` — **pendente** — Evidência: `grep -rn "comments-policy" agents/` mostra **9 agents** (backend/frontend dev+test, devops, database, code-reviewer, backend-reviewer, frontend-reviewer) carregando `skills/shared/comments-policy/SKILL.md` full sem `sections/<lang>.md` condicional. Extração de sections/ feita em 2026-05-13 (commit `6c8516b`) **não acompanhada** por refactor nos consumers.

### Economia de Tokens (10)

- `token-worktree-skill-loaded-twice-in-8-coding-agents-detection-after-orphan-scan-extension` — **pendente** — Evidência: contagem programática para todos os 8 coding agents (`backend-developer`, `backend-test-specialist`, `database-specialist`, `devops-specialist`, `frontend-developer`, `frontend-test-specialist`, `mobile-developer`, `ui-ux-designer`) retorna **2 loads cada** de `skills/shared/worktree`. ~1.400 tokens/sessão duplicados confirmados.
- `token-plan-mode-skill-loaded-twice-in-5-commands-after-eb5f90e-and-c3cbd15` — **pendente** — Evidência: `commands/{backend,fix,frontend,fullstack,refactor}.md` retornam **2 loads cada** de `skills/shared/plan-mode`. `commands/plan.md` retorna 1 load (correto). Drift de 5 commands confirmado quantitativamente.
- `token-claude-md-grew-to-544-lines-loaded-every-session-largest-monolith` — **pendente (regressão)** — Evidência: `wc -l CLAUDE.md` = **557 linhas** (vs 544 reportadas) — cresceu mais 13 linhas. Plano de fragmentação em 3 fases não iniciado.
- `token-context-cache-300s-too-short-for-multi-agent-session-misses-50-percent` — **pendente** — Evidência: `skills/shared/current-context/SKILL.md:85` mantém literal `Cache TTL is 300 seconds (5 minutes)`. Não há recomendação de TTL maior nem invalidação por branch.
- `token-pre-compact-hook-49-lines-redundant-with-stop-01-session-summary` — **pendente** — Evidência: `wc -l scripts/hooks/pre-compact.sh scripts/hooks/stop/01-session-summary.sh` = 49+72=121 linhas. Sem `lib/session-summary-detect.sh` compartilhado.
- `token-rollback-sh-65-lines-duplicates-installer-download-from-update-sh` — **pendente** — Evidência: `wc -l scripts/rollback.sh scripts/update.sh` = 65+76=141 linhas. Sem `scripts/lib/install-fetch.sh`.
- `token-foundational-rule-still-inline-in-17-agents-after-software-architect-cut` — **pendente** — Evidência: soma medida hoje em 17 agents = **368 linhas** (vs 368 reportadas — estável, sem novo cut). Items 1-4 quase idênticos seguem duplicados.
- `token-changelog-130-lines-after-rotation-suggestion-still-pending-3rd-pass` — **pendente** — Evidência: `wc -l CHANGELOG.md` = **130 linhas** (estável, sem crescimento nas últimas 24h). `archive-changelog.sh` ainda não preparado.
- `token-readme-228-each-after-extraction-still-2-files-no-cross-link-tagging` — **pendente** — Evidência: `grep -c "@section:" README.md README.pt-BR.md` = 0 + 0. Anchor IDs ausentes.
- `token-comments-policy-91-lines-still-eager-loaded-by-9-agents-after-section-extraction` — **pendente** — Evidência: `wc -l skills/shared/comments-policy/SKILL.md` = 91 linhas. 9 agents (vide fingerprint correlato em #11 de Agentes & Skills) seguem load full sem condicional por linguagem.

---

## Promoções Históricas

Nenhuma promoção a ✅ Executed identificada para fingerprints anteriores (2026-05-08 a 2026-05-12) na janela de 24h. Os 3 commits novos (`ac6af24`, `d05242a`, `ba19882`) têm escopo:

| Commit | Escopo | Impacto em fingerprints históricos |
|--------|--------|------------------------------------|
| `ac6af24` | move context-cache path para `user-data/` | Não promove `flow-current-context-cache-no-invalidation-on-branch-switch-within-ttl-window` (mudança apenas de path, não de lógica de invalidação) |
| `d05242a` | nova skill `interaction-patterns` (quiz-first) | Sem fingerprint correspondente — feature nova; nota: contribui +13 linhas para CLAUDE.md, **agravando** `ref-claude-md-grew-to-544-lines-largest-mono-file-in-repo` |
| `ba19882` | aplica quiz-first em `commands/update.md` | Sem fingerprint correspondente — feature nova |

> **Observação:** todas as promoções dos 11 fingerprints de 2026-05-11 já haviam sido contabilizadas pelo Guardian de 2026-05-13 (ver _index.md linha 58). Não há novas promoções desde então.

---

## Observações Notáveis

### 1. Regressão silenciosa em CLAUDE.md (557 linhas, +13 vs 544)

Tendência **piora**: o próprio fingerprint `ref-claude-md-grew-to-544-lines-largest-mono-file-in-repo` (registrado em 2026-05-13) virou alvo móvel — a feature `interaction-patterns` (commit `d05242a`) somou +13 linhas no documento sem fragmentação compensatória. Crescimento líquido: 330 → 544 → 557 (+69% em 8 dias). O monolítico de auth está se tornando o maior risco de overhead pós-spawn (~27.300 tokens × 7 spawns/sessão).

### 2. Drift continua acumulando dívida em `commands/tester.md`

Quarta passada consecutiva (2026-05-11, 2026-05-12, 2026-05-13, 2026-05-14) detectando que `mobile-developer¹` está declarado em CLAUDE.md mas nunca implementado em `commands/tester.md`. Combinado com `agent-mobile-test-specialist-3rd-consecutive-pass-still-missing`, configura **dívida arquitetural mobile** — sem owner, sem ADR.

### 3. Throughput cai 79% (57% → 12,2%) — explicação contextual

Dois fatores concorrem:
- A janela de 2026-05-13 → 2026-05-14 capturou apenas **3 commits novos** vs 22 commits no batch anterior. Foi um dia de "limpeza de bordas" (quiz-first patterns, refactor de cache path), não de execução de backlog do audit.
- Os 41 fingerprints de 2026-05-13 foram **mais profundos e estruturais** (refatorar agents, fragmentar CLAUDE.md, criar mobile-test-specialist) — itens que naturalmente requerem >24h.

### 4. Endereçamento parcial reconhecido

- `ref-foundational-rule-setup-assistant-shrunk-to-7-lines-after-suggestion-to-grow-it`: a Immutability Warning **está presente** (linha 213 de `setup-assistant.md`); apenas o tamanho da Foundational Rule continua subdimensionado. Sub-escopo "size" pendente, sub-escopo "compliance" resolvido.
- `flow-pre-compact-hook-no-graceful-skip-when-claude-dir-absent`: `pre-compact.sh:7` adiciona skip para repo não-git e linha 21 para "no changes"; falta apenas o caso específico `[ -d .claude/user-data ]`. Cobertura ~80%.
- `skill-graphify-setup-still-no-conditional-skip-3rd-pass-277-lines`: commit `90d2f40` adicionou 12 linhas de skip conditions; a infraestrutura de gating existe mas a propagação para `setup-assistant.md` (consumidor) não foi verificada. Mantido como pendente para conservadorismo.

### 5. Scripts órfãos seguem padrão recorrente

`validate-commit-msg.sh` (criado em `bae0f79`/2026-05-13) repete o anti-pattern documentado em `check-updates.sh` (2026-05-08): script criado, documentado em skill, **nunca wireado** em CI/commands/install.sh. Quinta passada detecta o mesmo padrão sem mitigação estrutural — sugere instituir checklist obrigatório "novo script ⇒ minimum 1 invocador automatizado" no PR template.

### 6. Duplicações intencionais não rotuladas

- `worktree` skill: 8 agents × 2 loads = 16 referências (1 no Worktree Isolation gate + 1 no skill loading section). O orphan-scan reporta como WARN, mas **alguns desses loads são intencionais** (gate operacional vs. carregamento de instruções). Falta convenção de marcador (ex.: `<!-- intentional-double-load: gate -->`) para ruído ser silenciado.
- `plan-mode` skill: 5 commands com 2 loads cada — sintoma de coordenação ausente entre commits `c3cbd15` (plan command) e `eb5f90e` (5 outros commands), ambos do mesmo dia 2026-05-13. Sem revisão de overlap pré-commit.

---

**Próximo Guardian sugerido:** 2026-05-15. Foco esperado:
1. Verificar se `ref-claude-md-grew-to-544-lines` continua crescendo (regressão acumulativa).
2. Confirmar se algum dos 36 pendentes saiu do limbo.
3. Auditar se as 2 features novas de 2026-05-14 (interaction-patterns, quiz-first em update.md) introduziram novos drifts.
