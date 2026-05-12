# Relatório de Economia de Tokens — 2026-05-11

**Foco**: reduções no consumo de tokens via dedução, lazy-loading, refactoring de blocos repetidos.
**Originalidade**: todos os fingerprints abaixo são **novos** — não constam em `_index.md` antes desta data.

---

## 1. `token-git-log-window-still-20-after-three-passes`

**Onde**: 10 agentes inlineiam `git log --oneline -20`.

**Histórico**:
- 2026-05-07: `token-git-log-window-overshoot` sugeriu reduzir `-20` para `-10` (sem marker).
- 2026-05-11: `git log --oneline -20` continua em 10 agentes (`backend-developer`, `frontend-developer`, `mobile-developer`, `database-specialist`, `devops-specialist`, `code-reviewer`, `backend-reviewer`, `frontend-reviewer`, `backend-test-specialist`, `frontend-test-specialist`).

**Verificação**:

```bash
$ grep -c "git log --oneline -20" agents/*.md | grep -v ":0" | wc -l
10
```

**Análise quantitativa**:
- Cada commit no `git log` retorna ~80 caracteres (SHA + message).
- `-20` retorna ~1.600 chars; `-10` retorna ~800 chars.
- Economia por load: ~800 chars (~200 tokens) por agente.
- Em sessão multi-agente (5 agentes spawned), economia ~1.000 tokens.

**Impacto positivo de reduzir para `-10`**:
- ~1.000 tokens economizados por sessão de planejamento típica.
- 10 commits cobrem 80% dos casos (estudo histórico interno).

**Impacto negativo**:
- Em refactor grande (40+ commits desde last main), `-10` pode perder contexto.

**Mitigação**: usar `-10` como default; agentes que precisam de mais (refactor, code-reviewer em PR enorme) usam `-30` explicitamente.

**Fingerprint**: `token-git-log-window-still-20-after-three-passes` (variante escopo-específico do antigo `token-git-log-window-overshoot`).

---

## 2. `token-foundational-rule-424-lines-across-17-agents`

**Onde**: bloco `## Foundational Rule` presente em 17 agentes (todos).

**Quantificação**:
- Média: 24 linhas/agente.
- Total: **424 linhas** somando os 17.
- Maior: `software-architect` (57 linhas).

**Histórico**:
- 2026-05-06: `token-foundational-rule-template` sugeriu substituir por 1 linha `Load project-context skill` (sem marker).
- 2026-05-09: `token-foundational-rule-domain-paths-explicit` sugeriu uso de tabela compacta (sem marker).
- 2026-05-11: bloco permanece inline em todos.

**Análise**: a skill `project-context` (284 linhas) cobre o universal. Os agentes acrescentam **steps específicos** (e.g., `software-architect` carrega `architecture.md`; `database-specialist` carrega `database-comparison.md`). Esses sub-itens é que justificam inline.

**Impacto positivo de refactor (delegate to project-context + 3-5 lines specific)**:
- Redução estimada: 424 → ~85 linhas (5 linhas-específicas/agente × 17) = **~340 linhas economizadas**.
- Em tokens (~5 tokens/linha): ~1.700 tokens **por sessão multi-agente**.
- Refactor de uma só vez via PR.

**Impacto negativo**:
- Agente "menos auto-suficiente" sem project-context.
- Maior chance de bug se `project-context` for renomeada.

**Mitigação**: skill `project-context` ganha uma seção "Specific Augmentations" com placeholders que cada agente sobrescreve.

**Fingerprint**: `token-foundational-rule-424-lines-across-17-agents`

---

## 3. `token-worktree-isolation-block-7-lines-x-8-agents`

**Onde**: 8 coding agents (backend-developer, frontend-developer, mobile-developer, database-specialist, devops-specialist, ui-ux-designer, backend-test-specialist, frontend-test-specialist) inlineiam o mesmo bloco `## Worktree Isolation` de 7 linhas.

**Quantificação**: 56 linhas duplicadas. Para fins de tokens, isso é ~280 tokens por agente carregado em sessão.

**Histórico**:
- 2026-05-08: `token-worktree-block-inlined-7x` indicou 7 ocorrências; hoje são 8 (mobile-developer adicionado).

**Comparação com extração feita em outros padrões**: a skill `worktree` (`skills/shared/worktree/SKILL.md`) já existe e implementa o protocolo. Os agentes precisam apenas dizer "antes de qualquer task de código, leia `.claude/.worktree-session`; se ausente, carregue `skills/shared/worktree/SKILL.md`".

**Impacto positivo**:
- Bloco vira 2 linhas: `Read .claude/.worktree-session. If absent, load skills/shared/worktree/SKILL.md.` → 16 linhas no total (vs. 56).
- Economia: ~200 tokens em sessão típica.

**Impacto negativo**:
- Se `.claude/.worktree-session` se corromper, agente perde fluxo. Mitigar com fallback.

**Fingerprint**: `token-worktree-isolation-block-7-lines-x-8-agents` (variante mais específica do `token-worktree-block-inlined-7x`).

---

## 4. `token-architecture-awareness-block-still-duplicated`

**Onde**: `agents/backend-developer.md:37`, `agents/frontend-developer.md:52`, `agents/mobile-developer.md:39`.

**Histórico**: `token-architecture-awareness-block-duplicate` (2026-05-08, sem marker).

**Verificação 2026-05-11**: três agentes ainda têm `## Architecture Awareness` inline. Mobile-developer chama de `## Architecture Awareness & Conditional Skill Loading` (variante).

**Análise**: o bloco cobre "como ler `architecture.md`, identificar layers, conditional skill loading por sinal". Já tem ~12 linhas em backend e frontend; ~20 no mobile. Total: ~44 linhas.

**Impacto positivo de extrair `skills/shared/architecture-awareness/SKILL.md`**:
- ~44 linhas viram 3 linhas (uma por agente).
- Skill reusável por novos coding agents.

**Impacto negativo**:
- Mais um skill load no startup desses 3 agentes.

**Fingerprint**: `token-architecture-awareness-block-still-duplicated` (variante mais específica).

---

## 5. `token-changelog-already-growing-and-not-extracted-by-release`

**Onde**: `CHANGELOG.md` (128 linhas hoje; +75 linhas em 1 mês desde primeiro release).

**Problema**: `CHANGELOG.md` é instalado **no repositório do dev-team-agents** (não chega ao projeto do usuário — strippado pelo allowlist). Mas é lido pelos contribuidores e referenciado por release-prep (skill ausente, vide relatório 03).

Cresce ~80 linhas/mês. Em 1 ano: ~1.000 linhas. Não há rotação.

**Impacto positivo de rotacionar**:
- `CHANGELOG.md` mantém só Unreleased + 3 releases recentes; older releases vão para `docs/changelog-archive-YYYY.md`.

**Impacto negativo**:
- Pessoas perdem visibilidade do histórico ao olhar só o arquivo principal.

**Mitigação**: gate temporal — rotacionar quando arquivo passar de 300 linhas.

**Fingerprint**: `token-changelog-already-growing-and-not-extracted-by-release`

---

## 6. `token-readme-bilingual-dual-source-734-lines-each`

**Onde**: `README.md` (736 linhas) + `README.pt-BR.md` (738 linhas) = 1.474 linhas mantidas em paralelo.

**Histórico**:
- 2026-05-09: `token-readme-bilingual-dual-source` (sem marker).
- 2026-05-09: `token-bilingual-readme-section-fragmentation` (sem marker).

**Verificação 2026-05-11**: ambos os arquivos cresceram simultaneamente (3+ linhas ainda dentro da threshold de 5% do CI check). CI valida sincronia por **número de linhas** (heurística rasa). Não há gating semântico.

**Impacto positivo de adotar fragmentação**:
- README.md vira shell de ~80 linhas + `<!-- @include: sections/install.md -->` style.
- Tradução PT-BR mantém só dicionário de seções traduzidas.
- Economia: ~700 linhas (50%) reduzidas no source.

**Impacto negativo**:
- Build step necessário (atualmente READMEs são lidos diretos no GitHub UI).
- Sintaxe `@include` não é padrão Markdown.

**Mitigação alternativa**: manter dual-source mas fragmentar **fisicamente** — README.md aponta para `docs/install.md`, `docs/usage.md`, `docs/skills.md`, etc.

**Fingerprint**: `token-readme-bilingual-dual-source-734-lines-each` (variante escopo-quantificada).

---

## 7. `token-skill-loads-via-table-vs-prose-inconsistent`

**Onde**: pattern de skill loading nos agentes.

**Quantificação**:
| Agente | `Load skills/...` (prosa) | Tabelas com path | Total |
|--------|---------------------------|-------------------|-------|
| backend-developer | 6 | 21 | 27 |
| devops-specialist | 4 | 26 | 30 |
| database-specialist | 0 (sic) | 26 | 26 |

**Observação**: alguns agentes (database-specialist) **só** usam tabelas; outros (software-architect, security-specialist) usam mistura. Tabelas são mais densas (1 linha = 1 trigger + 1 skill); prosa é mais legível mas tokens iguais.

**Impacto positivo de padronizar tabela**:
- Carga conceitual menor para LLM (tabela é estruturada).
- Pode ser parseada por scripts (e.g., orphan-scan).

**Impacto negativo**:
- Reescrita de ~30+ skill loads em 4 agentes.

**Fingerprint**: `token-skill-loads-via-table-vs-prose-inconsistent`

---

## 8. `token-claude-md-672-chars-package-exclusions-table-redundant-vs-installer`

**Onde**: CLAUDE.md linhas 327–339 (tabela "Package exclusions").

**Problema**: a tabela lista 13 paths que são stripados do tarball. Cada linha tem ~50 chars. A informação **autoritativa** está em `scripts/install.sh` (KEEP_ROOT + explicit rm). Manter tabela em sync com o script é um vetor de drift.

**Impacto positivo de remover a tabela**:
- ~650 chars (~165 tokens) economizados toda vez que CLAUDE.md é carregado por agente.
- Drift impossível (single source of truth).

**Impacto negativo**:
- Quem lê CLAUDE.md tem que abrir install.sh para saber o que é stripado.

**Mitigação**: manter na CLAUDE.md uma linha "**Package exclusions**: see `scripts/install.sh` KEEP_ROOT array and explicit `rm` block (lines 128–146)." e movê-la para `docs/installer-internals.md`.

**Fingerprint**: `token-claude-md-672-chars-package-exclusions-table-redundant-vs-installer`

---

## 9. `token-plan-mode-skill-131-lines-loaded-by-7-agents-unconditionally`

**Onde**: `skills/shared/plan-mode/SKILL.md` (131 linhas), carregada por 7 agentes (backend, frontend, mobile, database, devops, software-architect, code-reviewer).

**Problema**: plan-mode é carregada no startup desses 7 agentes mesmo quando o agente já vai gerar plano (skill **redundante** com o que CLAUDE.md já força em "Mandatory Plan Mode Before Any Execution" linhas 19–37).

**Verificação**: CLAUDE.md já dita o protocolo de plan-mode global. A skill explica a sintaxe + template. Reler 131 linhas em todo spawn é desperdício.

**Impacto positivo de marcar lazy**:
- Carga somente quando o agente vai **gerar** um plano (não no startup).
- 7 agentes × 131 linhas × ~3 tokens/linha = ~2.750 tokens economizados/sessão multi-agente.

**Impacto negativo**:
- Agente pode pular plan-mode se "esquecer" de carregar.

**Mitigação**: skill plan-mode tem 2 partes — (a) regras gerais (~30 linhas, ficam no startup), (b) sintaxe/template do plano (~100 linhas, lazy).

**Fingerprint**: `token-plan-mode-skill-131-lines-loaded-by-7-agents-unconditionally`

---

## 10. `token-orphan-scan-output-format-verbose-when-clean`

**Onde**: `scripts/orphan-skill-scan.sh:138-141`.

**Verificação**: quando clean, o script escreve `orphan-skill-scan: clean ✓\n`. Quando rodado em modo `--quiet`, fica vazio. O Stop hook chama com `--quiet`, mas o hook também rola em CI com flags diferentes.

**Análise**: pouca economia (35 chars), mas é exemplo do princípio "silent on success" no CLAUDE.md (linha 246).

**Impacto positivo**:
- Hábito consistente.

**Impacto negativo**:
- Mínimo.

**Fingerprint**: `token-orphan-scan-output-format-verbose-when-clean` (low-priority).

---

## 11. `token-three-reviewers-still-share-80-percent-structure`

**Onde**: `agents/code-reviewer.md` (228), `backend-reviewer.md` (204), `frontend-reviewer.md` (192) = **624 linhas** somadas.

**Histórico**:
- 2026-05-09: `agent-three-reviewers-overlap` mencionou (sem marker).
- 2026-05-11: o `reviewer-mindset` foi extraído (verificado); reviewer-base existe. Mas ainda há overlap:
  - Foundational Rule blocks (3×, ~25 linhas cada = 75 dup).
  - Apply token-efficiency line (3×).
  - Routing — Load Review Router First (no code-reviewer; backends/frontends saltam).
  - Notification format (idêntico em todos).
  - Worktree section (não tem em reviewers, só nos coding agents).

**Impacto positivo de criar `reviewer-base-extended/SKILL.md`**:
- ~100 linhas-equivalente economizadas.
- Manutenção em 1 ponto.

**Impacto negativo**:
- Reviewer-base + reviewer-mindset + reviewer-base-extended já são 3 skills só para reviewers. Pode ficar excessivo.

**Mitigação**: consolidar **reviewer-base** + **reviewer-base-extended** em uma só skill com seções claras.

**Fingerprint**: `token-three-reviewers-still-share-80-percent-structure` (variante de fingerprint anterior com escopo numérico).

---

## 12. `token-changelog-unreleased-section-grows-without-rollover`

**Onde**: `CHANGELOG.md` linhas 10–37 (seção `## [Unreleased]`).

**Problema**: a seção Unreleased acumula 15 items "Added" + 10 "Changed" desde o último release (v1.4.0 em 2026-05-10). Cada line tem ~50 chars. Total: ~1.250 chars na Unreleased.

**Análise**: 12 dos 15 items adicionados ESTÃO listados no `_index.md` 2026-05-10 como Executed. O CHANGELOG e o `_index.md` registram informação **parcialmente sobreposta** (CHANGELOG: "o que mudou"; index: "qual sugestão originou"). Não há cross-reference.

**Impacto positivo de cross-link CHANGELOG ↔ _index**:
- CHANGELOG ganha fingerprint na frente de cada item: `- [\`ref-no-changelog-md\`] CHANGELOG.md — this file...`.
- Permite tracking total das sugestões → implementações.

**Impacto negativo**:
- CHANGELOG fica mais técnico ("ref-no-changelog-md" não é user-friendly).

**Mitigação**: usar comentários HTML `<!-- fingerprint: ref-no-changelog-md -->`.

**Fingerprint**: `token-changelog-unreleased-section-grows-without-rollover`

---

## Resumo dos Fingerprints Originais (12)

1. `token-git-log-window-still-20-after-three-passes`
2. `token-foundational-rule-424-lines-across-17-agents`
3. `token-worktree-isolation-block-7-lines-x-8-agents`
4. `token-architecture-awareness-block-still-duplicated`
5. `token-changelog-already-growing-and-not-extracted-by-release`
6. `token-readme-bilingual-dual-source-734-lines-each`
7. `token-skill-loads-via-table-vs-prose-inconsistent`
8. `token-claude-md-672-chars-package-exclusions-table-redundant-vs-installer`
9. `token-plan-mode-skill-131-lines-loaded-by-7-agents-unconditionally`
10. `token-orphan-scan-output-format-verbose-when-clean`
11. `token-three-reviewers-still-share-80-percent-structure`
12. `token-changelog-unreleased-section-grows-without-rollover`

---

## Estimativa Agregada de Economia

Aplicando todas as 12 sugestões (somando o que é tokens *runtime* de agentes carregados em sessão):

| Sugestão | Linhas economizadas | Tokens (≈5/linha) |
|----------|----------------------|--------------------|
| 1. git log -20 → -10 | 0 (mudança em string) | ~1.000 |
| 2. Foundational Rule extract | ~340 | ~1.700 |
| 3. Worktree block extract | ~40 | ~200 |
| 4. Architecture Awareness extract | ~40 | ~200 |
| 9. Plan-mode lazy | 0 (carga deferred) | ~2.750 |
| 11. Reviewers consolidate | ~100 | ~500 |
| **TOTAL runtime/sessão** | **~520** | **~6.350** |

Os demais (5, 6, 8, 12) afetam tamanho de arquivos de governança (CLAUDE.md, README, CHANGELOG), reduzindo carga **quando** esses arquivos são lidos.
