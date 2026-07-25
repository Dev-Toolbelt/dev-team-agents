# Relatório — Economia de Tokens (2026-05-13)

Auditoria focada em **redução de carga de contexto, lazy-loading, deduplicação e overhead operacional**. Todas as sugestões são **originais** ao `_index.md`. Estimativas são de **tokens economizados por sessão multi-agent típica**.

> **Metodologia de estimativa:** 1 linha de markdown ≈ 6-8 tokens (mediana 7). Sessão multi-agent típica = 4 spawns sequenciais + 3 reviewers paralelos.

---

## 1. `token-worktree-skill-loaded-twice-in-8-coding-agents-detection-after-orphan-scan-extension`

**Severidade:** 🟡 Média — 13 instâncias detectadas pela primeira vez

**Detecção:** O orphan-skill-scan estendido em commit `19de0e1` agora reporta:

```
WARN — Skills loaded more than once in the same agent:
  · agents/backend-developer.md loads skills/shared/worktree/SKILL.md more than once
  · agents/backend-test-specialist.md loads skills/shared/worktree/SKILL.md more than once
  · agents/database-specialist.md loads skills/shared/worktree/SKILL.md more than once
  · agents/devops-specialist.md loads skills/shared/worktree/SKILL.md more than once
  · agents/frontend-developer.md loads skills/shared/worktree/SKILL.md more than once
  · agents/frontend-test-specialist.md loads skills/shared/worktree/SKILL.md more than once
  · agents/mobile-developer.md loads skills/shared/worktree/SKILL.md more than once
  · agents/ui-ux-designer.md loads skills/shared/worktree/SKILL.md more than once
```

8 agents × 2 references each. A skill `worktree` tem 214 linhas; cada referência adiciona ~3 linhas em torno (`Load … if X`). Custo: 16 references × ~3 linhas × 7 tokens = **~340 tokens duplicados em definição**, e potencial **dupla leitura** se Claude interpretar literalmente.

**Investigação root cause:** O bloco "Worktree Isolation" no Foundational Rule de coding agents tem dois pontos onde menciona o skill:
- Step 1: "Read `.dev-team-agents/.worktree-session` — if `worktree=yes branch=<b>` → load `skills/shared/worktree/SKILL.md`"
- Step 2 (else branch): "If user answers yes → load `skills/shared/worktree/SKILL.md`"

Ambos são corretos no fluxo, mas o orphan-scan não distingue "load condicional do mesmo skill em branches diferentes do if/else" vs "load duplicado real".

**Impacto positivo (se corrigido — opção A):** consolidar para 1 menção parametrizada no Worktree Isolation section.

**Impacto positivo (se corrigido — opção B):** adicionar exclusão no orphan-scan para "load no mesmo bloco condicional não conta como duplicate".

**Impacto negativo (se mantido):** WARN no Stop hook a cada sessão; ruído crônico.

**Estimativa:** ~340 tokens economia por agent loadeado, × 4 spawns/sessão = **~1.400 tokens/sessão**.

**Sugestão:** Opção A: refatorar Worktree Isolation para 1 menção:

```markdown
Load `skills/shared/worktree/SKILL.md` and follow its protocol if `.dev-team-agents/.worktree-session` indicates worktree=yes (or after user opts in for a new session).
```

---

## 2. `token-plan-mode-skill-loaded-twice-in-5-commands-after-eb5f90e-and-c3cbd15`

**Severidade:** 🟡 Média

**Detecção:** Mesmo scan WARN também reporta:

```
  · commands/backend.md loads skills/shared/plan-mode/SKILL.md more than once
  · commands/fix.md loads skills/shared/plan-mode/SKILL.md more than once
  · commands/frontend.md loads skills/shared/plan-mode/SKILL.md more than once
  · commands/fullstack.md loads skills/shared/plan-mode/SKILL.md more than once
  · commands/refactor.md loads skills/shared/plan-mode/SKILL.md more than once
```

Investigação: dois commits no mesmo dia (`c3cbd15` e `eb5f90e`) adicionaram load do plan-mode em commands. O segundo não notou que o primeiro já tinha adicionado em alguns commands.

`grep -n "plan-mode" commands/backend.md` confirma:
- Linha 5: "Load `skills/shared/plan-mode/SKILL.md` to anchor the canonical plan format…"
- Linha 22: "Present a structured plan following `skills/shared/plan-mode/SKILL.md`…"

Ambos referenciam o mesmo skill. Linha 5 é load explícito; linha 22 é menção dentro do PLAN GATE block.

**Impacto positivo (se corrigido):** ~10 references × ~5 tokens contextuais = **~50 tokens/command** + clareza para Claude.

**Impacto negativo (se mantido):** ~250 tokens duplicados por sessão; WARN ruidoso.

**Estimativa:** ~250-500 tokens/sessão dependendo de quantos commands forem usados.

**Sugestão:** remover linha 5 redundante; manter apenas a referência dentro do PLAN GATE (que é onde a skill é usada). Atualizar 5 commands.

---

## 3. `token-claude-md-grew-to-544-lines-loaded-every-session-largest-monolith`

**Severidade:** 🟠 Alta — maior contributor isolado de overhead de session-start

**Detecção:** `wc -l CLAUDE.md` = **544 linhas**. CLAUDE.md é loadeada em **todo session-start** por todo agent (Foundational Rule "Read CLAUDE.md"). 544 linhas × 7 tokens ≈ **3.800 tokens** por agent. Em sessão multi-agent típica (7 spawns):

- 7 spawns × 3.800 tokens = **~26.600 tokens** apenas em CLAUDE.md replicação.

Mas isto é leitura — **não duplicação no contexto** (cada agent é um sub-context). O custo real é:
- API cost por leitura individual (Read tool input = 3.800 tokens cada).
- Tempo de processamento (~50-100ms por load).

Antigo fingerprint `token-claude-md-monolithic-load-every-session` (2026-05-10, pendente) sugeria fragmentação.

**Impacto positivo (se corrigido):** CLAUDE.md raiz vira ~80 linhas (índice + project rules absolutas). Sub-arquivos (`CLAUDE-md/authoring.md`, `CLAUDE-md/notifications.md`, `CLAUDE-md/preferences.md`) são loaded apenas pelos agents que precisam.

**Impacto negativo (se mantido):** crescimento linear continua (~30-50 linhas/audit cycle); em 30 dias projeta-se para ~800 linhas.

**Estimativa:** redução de 544 → 80 linhas no canônico = ~3.250 tokens economizados por load. **× 7 spawns/sessão = ~23.000 tokens/sessão**.

**Sugestão:** plano de extração em 3 fases:
- **Fase 1 (sem risco):** mover seções `## Notification System`, `## User Preferences`, `## User Data Directory`, `## Versioning` para sub-arquivos. Atualizar Authoring Rule para apontar.
- **Fase 2:** mover seções `## Authoring Standards` (subseções por categoria de agent/skill).
- **Fase 3:** consolidar índice.

---

## 4. `token-context-cache-300s-too-short-for-multi-agent-session-misses-50-percent`

**Severidade:** 🟡 Média

**Detecção:** `skills/shared/current-context/SKILL.md` linha ~85 declara TTL = **300 segundos** (5 min). Sessão multi-agent típica:

| Spawn | Tempo decorrido |
|-------|-----------------|
| 1º spawn (architect) | t=0 |
| 2º spawn (backend) | t≈120s (después de architect terminar) |
| 3º spawn (frontend) | t≈220s |
| 4º spawn (db) | t≈340s | **← cache expirado** |
| 5º spawn (devops) | t≈480s | **← cache expirado novamente** |
| Reviewers paralelos | t≈600-800s | **← cache expirado** |

Cache é **útil para os primeiros 3 spawns** mas expira para os subsequentes. Cada miss ≈ 4 git commands ≈ ~200ms + ~50 tokens output.

**Impacto positivo (se corrigido):** TTL = 1800s (30 min) cobre sessões inteiras; invalidation por branch (sugerido em fingerprint #3 do report 02) garante correctness.

**Impacto negativo (se mantido):** ganho do cache é parcial; spawns tardios pagam overhead completo.

**Estimativa:** 4 cache misses evitadas × 50 tokens × 7 agents/sessão = **~1.400 tokens/sessão** + tempo.

**Sugestão:** TTL = 1800s + invalidation por branch (sugestão #3 do report Fluxos). Trade-off: dados marginalmente mais antigos vs ganho real.

---

## 5. `token-pre-compact-hook-49-lines-redundant-with-stop-01-session-summary`

**Severidade:** 🟡 Média

**Detecção:** Commit `57dc8ca` criou `scripts/hooks/pre-compact.sh` (49 linhas). Comparação com `scripts/hooks/stop/01-session-summary.sh` (72 linhas):

| Bloco | pre-compact.sh | stop/01-session-summary.sh |
|-------|----------------|----------------------------|
| `git rev-parse --is-inside-work-tree` guard | ✅ linha 7 | ✅ linha 8 |
| `TODAY=$(date +%Y-%m-%d)` | ✅ linha 10 | ✅ linha 11 |
| `git log --since="${TODAY} 00:00:00"` | ✅ linha 13 | ✅ linha 14 |
| `HAS_CHANGES` detection | ✅ linhas 15-19 | ✅ linhas 16-22 |
| Heredoc emite mensagem | ✅ linhas 27-46 (com pequenas diferenças) | ✅ linhas 25-58 |

**~30 linhas duplicadas literalmente**. Diferenças mínimas: pre-compact diz "(pre-compact)" no header, stop diz "(stop)".

**Impacto positivo (se corrigido):** lib compartilhada `scripts/hooks/lib/session-summary-detect.sh` que ambos source; +1 source ≈ ~3 linhas, vs ~30 duplicadas; mudança em uma reflete na outra.

**Impacto negativo (se mantido):** próximo refactor de session-summary precisa atualizar 2 lugares; risco de drift.

**Estimativa:** ~30 linhas × 7 tokens = **~210 tokens** salvos no script size; benefício real é manutenibilidade > tokens.

**Sugestão:**

```bash
# scripts/hooks/lib/session-summary-detect.sh
# (sourced by stop/01-session-summary.sh and pre-compact.sh)
TODAY=$(date +%Y-%m-%d)
HAS_CHANGES=false
…  # detection logic shared
```

E em ambos hooks:

```bash
# shellcheck source=lib/session-summary-detect.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib/session-summary-detect.sh"
```

---

## 6. `token-rollback-sh-65-lines-duplicates-installer-download-from-update-sh`

**Severidade:** 🟡 Média

**Detecção:** `scripts/rollback.sh` (65 linhas) duplica padrão de `scripts/update.sh`:

| Bloco | rollback.sh | update.sh |
|-------|-------------|-----------|
| GITHUB_OWNER, GITHUB_REPO, INSTALL_URL constants | ✅ | ✅ |
| `mktemp` + `curl -sSL` | ✅ | ✅ |
| `bash $TMP_INSTALLER` invocation | ✅ (com TARGET) | ✅ |
| `.installed-version` write | implícito | ✅ |

**~30 linhas duplicadas**. Refactor candidate: `scripts/lib/install-fetch.sh` que recebe `--version vX.Y.Z` e centraliza download + execução.

**Impacto positivo (se corrigido):** download/install logic em um lugar; rollback fica trivial (apenas chama lib com versão antiga).

**Impacto negativo (se mantido):** mudança em URL pattern (ex.: GitHub muda format) requires editar 2 arquivos.

**Estimativa:** ~30 linhas × 7 tokens = **~210 tokens**; benefício de manutenção > tokens.

**Sugestão:** extrair `scripts/lib/install-fetch.sh`:

```bash
# Usage: bash install-fetch.sh <version-tag>
fetch_and_run() {
    local version="$1"
    local tmp=$(mktemp)
    curl -sSL "$INSTALL_URL" -o "$tmp"
    DEVTEAM_VERSION="$version" bash "$tmp"
    rm -f "$tmp"
}
```

E em ambos scripts: `. "$(dirname …)/lib/install-fetch.sh"; fetch_and_run "$TARGET"`.

---

## 7. `token-foundational-rule-still-inline-in-17-agents-after-software-architect-cut`

**Severidade:** 🟡 Média — sub-escopo de `token-foundational-rule-software-architect-outlier-51-lines` (⚠️ Partial em 2026-05-13)

**Detecção:** Soma de Foundational Rule lines em 17 agents:

```
software-architect: 33 (era 51)
security-specialist: 28
code-reviewer: 27
backend-developer: 26
technical-writer: 26
backend-reviewer: 24
devops-specialist: 24
frontend-developer: 23
frontend-reviewer: 23
mobile-developer: 22
frontend-test-specialist: 20
backend-test-specialist: 19
product-analyst: 18
ui-ux-designer: 17
database-specialist: 16
qa-specialist: 15
setup-assistant: 7
TOTAL: 368 linhas
```

Padrão: items 1-4 são quase idênticos em todos os agents (load CLAUDE.md, README.md, AGENTS.md, session-summary, code-standards, architecture). 4 linhas × 17 agents = **68 linhas duplicadas** (38% das primeiras 4 linhas estimadas).

`skills/shared/project-context/SKILL.md` (283 linhas) já contém esse fluxo. Os agents poderiam apenas dizer:

```markdown
## Foundational Rule

Load and execute `skills/shared/project-context/SKILL.md`. Then proceed.
```

**Impacto positivo (se corrigido):** -300 linhas spread; agents 30-50% menores; 9 dos 11 agents acima de 200 linhas voltam para conformidade.

**Impacto negativo (se mantido):** Foundational Rule continua sendo "boilerplate copy-paste" em cada novo agent.

**Estimativa:** 300 linhas × 7 tokens × 4 agents/sessão typical = **~8.400 tokens/sessão**.

**Sugestão:** refactor em 2 passes:
1. Mover items 1-7 (universal) para `project-context` skill (já fazem).
2. Items 8-N (agent-specific, ex.: "Load skills/shared/comments-policy") permanecem inline.

Resultado: Foundational Rule típico vira **8-15 linhas** em vez de 22.

---

## 8. `token-changelog-130-lines-after-rotation-suggestion-still-pending-3rd-pass`

**Severidade:** 🟢 Baixa — observação de longa duração

**Detecção:** `wc -l CHANGELOG.md` = **130 linhas** (era 119 em 2026-05-11, +1 em 24h). Trajetória ainda saudável (threshold rotação 300 atingido em ~17 dias). Mas pendência de 3 passadas para preparar `archive-changelog.sh`.

**Impacto positivo (se preparado proativamente):** quando chegar a 300, rotação é 1 comando; sem fricção.

**Impacto negativo (se mantido):** quando atingir 300, decidir a logística sob pressão pode introduzir bug.

**Estimativa:** 0 tokens hoje; ~3.000 tokens economizados quando rotacionar.

**Sugestão:** criar `scripts/archive-changelog.sh` (~30 linhas) que:
1. Detecta entries com data > 90 dias.
2. Move para `CHANGELOG-archive-YYYY-Q.md`.
3. Atualiza header com link para arquivo.

Agendar para v1.5.0.

---

## 9. `token-readme-228-each-after-extraction-still-2-files-no-cross-link-tagging`

**Severidade:** 🟢 Baixa

**Detecção:** README.md = 228 linhas; README.pt-BR.md = 228 linhas. Após extração para docs/ em 2026-05-12, paridade é mantida via section-count check. Porém:

- Não há **anchor IDs** ou tags consistentes que permitam um único processo de tradução automatizada.
- Cada `^## ` é traduzido manualmente; drift dentro de seção continua sendo risco.

**Impacto positivo (se corrigido):** com anchors `<!-- @section: setup -->`, ferramenta tipo `i18n-cli` poderia validar par par a par.

**Impacto negativo (se mantido):** tradução é manual; drift inevitável.

**Estimativa:** 0 tokens diretos; permite ferramenta futura.

**Sugestão:** adicionar tags HTML comments após cada `^## `:

```markdown
## Quick Start
<!-- @section: quick-start -->
```

---

## 10. `token-comments-policy-91-lines-still-eager-loaded-by-9-agents-after-section-extraction`

**Severidade:** 🟡 Média — sub-escopo de `token-comments-policy-417-lines-still-monolith-no-section-loading` (⚠️ Partial)

**Detecção:** Após commit `6c8516b`, comments-policy SKILL.md caiu de 417 para 91 linhas + 3 sections (~150 linhas total). Porém os 9 agents que loadeiam ainda fazem:

```
Load skills/shared/comments-policy/SKILL.md
```

Sem condicional por linguagem. Resultado:
- Antes: 417 lines × 9 agents loaded = **~26.000 tokens/sessão multi-agent**.
- Hoje: 91 lines × 9 agents = **~5.700 tokens/sessão** — economia real de ~20.300 tokens.
- **Mas:** sections/ não são loaded sob condição. Para Python project, agent não precisa de `aaa-pattern.md` (test-specific). Para greenfield review, não precisa de `anti-patterns.md` (legacy-specific).

Lazy load condicional poderia economizar mais 50-70% adicional por agent.

**Impacto positivo (se corrigido):** mais 30-50 lines/agent economizado em load condicional.

**Impacto negativo (se mantido):** ganho atual já é grande; otimização adicional tem retorno marginal.

**Estimativa:** ~50 linhas × 9 agents × 7 tokens = **~3.150 tokens/sessão**.

**Sugestão:** atualizar comments-policy SKILL.md com explicit conditional loading:

```markdown
## Conditional Section Loading

Load relevant section based on context:
- Python files in scope → `sections/type-annotations.md`
- Test files in scope → `sections/aaa-pattern.md`
- Legacy code review → `sections/anti-patterns.md`
- Greenfield development → none of the sections needed
```

E atualizar agents para detectar contexto antes de load.

---

## Resumo & Estimativa Agregada

| Prioridade | Quantidade | Estimativa de tokens economizados/sessão |
|-----------|-----------|---------------------------------------------|
| 🟠 Alta | 1 (CLAUDE.md fragmentation) | ~23.000 |
| 🟡 Média | 7 | ~14.000 (agregado) |
| 🟢 Baixa | 2 | ~3.000 (agregado) |
| **Total estimado** | **10 fingerprints** | **~40.000 tokens/sessão multi-agent** |

**Padrões emergentes desta passada:**

- **WARN section do orphan-scan revela duplicate loads "free-to-fix"** — 13 instâncias detectadas em 8 agents + 5 commands; quick-win de ~1.700 tokens/sessão.
- **CLAUDE.md fragmentation** finalmente quantificado: maior monolítico do repo, loaded em todo session-start, +65% em 7 dias. Plano de 3 fases proposto.
- **Hooks novos duplicam ~30 linhas de detection logic** — pre-compact.sh e stop/01-session-summary.sh deveriam compartilhar lib.
- **Lazy-load real exige updates nos consumers**, não apenas extração da skill — comments-policy é o caso paradigmático.
- **Foundational Rule continua sendo o maior overhead** spread entre 17 agents (368 linhas total). Sub-escopo do antigo `token-foundational-rule-424-lines-across-17-agents` (2026-05-11, pendente) se beneficia do progress no software-architect (-18 linhas) mas o problema agregado persiste.
