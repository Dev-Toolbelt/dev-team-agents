# Economia de Tokens — 2026-05-15

> Otimizações de carregamento, deduplicação e lazy-loading com quantificação de impacto.

> **Convenção:** ~16 tokens/linha de markdown (média do repo). Spawns típicos: comandos single-agent = 1 spawn; multi-agent (`/devteam:fullstack`, `/devteam:refactor`) = 4-7 spawns.

---

## 1. `token-setup-assistant-immutability-warning-duplicated-top-and-bottom-30-lines` — HIGH

**Arquivo:** `agents/setup-assistant.md`

**Observação:** o agent contém **dois blocos Immutability Warning** sem motivo aparente:

- Linhas 11-28: Foundational Rule + Immutability Warning (top)
- Linhas 220-238: SECOND Immutability Warning (mais elaborada — bottom)

~30 linhas de prosa sobre immutability load em **cada spawn** do setup-assistant.

**Quantificação:**
- 30 linhas × 16 tokens = **480 tokens duplicados/spawn**.
- setup-assistant é Opus → custo de Opus em tokens custosos.
- Spawn frequency: alto durante onboarding (setup, health-check, update).

**Impacto positivo:** consolidar em **uma** Immutability Warning (top, junto da Foundational); remover bloco bottom; **economia ~480 tokens/spawn**.

**Impacto negativo:** zero — texto duplicado é puro overhead.

---

## 2. `token-notifier-loads-45-tips-3-languages-emits-1-per-day-99pct-waste` — HIGH

**Arquivo:** `scripts/hooks/stop/04-notifier.sh:184-235`

**Observação:** o hook hardcoded **45 strings** (15 tips × 3 idiomas) em arrays Bash. A cada execução do `Stop` hook, todas 45 entram em memória; **apenas 1 é emitida por dia**.

**Quantificação:**
- ~9 KB de strings carregadas por execução.
- Stop hook executa ~30×/sessão → 270 KB de string processing redundante.
- 99% das 45 strings nunca são emitidas no mesmo turno.

Não há benefício em ter todas em memória (no caching de seleção do dia).

**Impacto positivo:**
- Externalizar para `skills/shared/notifier/tips/{pt-BR,en,es}.json`.
- Hook lê APENAS o JSON do locale ativo → **−67% de strings carregadas** (15 em vez de 45).
- Adicionar idiomas (fr, it, de) vira drop-in sem editar hook.

**Impacto negativo:** +1 leitura de FS por Stop (~5ms, desprezível); +1 skill no repo.

---

## 3. `token-claude-md-425-lines-hook-system-and-commands-table-still-inline-not-fragmented` — HIGH

**Arquivo:** `CLAUDE.md` (425 linhas após fragmentação inicial em `CLAUDE-md/`)

**Observação:** apesar da fragmentação para `CLAUDE-md/{preferences,notifications,user-data,versioning}.md`, o CLAUDE.md mantém:

- Linhas 140-183 (44 linhas): tabela "User-Invocable Commands" — referência operacional, não regra
- Linhas 275-376 (~100 linhas): "Agent Memory System" + "Stop Hook Sub-script Convention" + "Hook Files Map" — detalhes de implementação

**Quantificação:**
- 144 linhas × 16 = **2.304 tokens** carregados em CADA session-start de `/devteam:*` (todos os agents Read CLAUDE.md no Foundational Rule).
- 7 spawns/sessão × 2.304 = **16.128 tokens/sessão** apenas dessas seções.

**Impacto positivo:**
- Mover commands table → `CLAUDE-md/commands.md` (44 linhas)
- Mover hook system → `CLAUDE-md/hooks.md` (100 linhas)
- CLAUDE.md cai para ~280 linhas; economia ~2.300 tokens × 7 spawns = **~16.000 tokens/sessão**.

**Impacto negativo:** mais 2 sub-arquivos `CLAUDE-md/`; necessário cross-reference clara para usuários humanos.

---

## 4. `token-index-md-growing-35-slugs-per-day-archive-script-still-unwritten-after-3-mentions`

**Arquivo:** `docs/reports/_index.md` (464 linhas em 2026-05-15)

**Observação:** o próprio `_index.md` declara política de rotação a cada 90 dias:

> Estratégia de evolução: o índice cresce indefinidamente, mas pode ser **rotacionado** a cada 90 dias movendo entradas antigas para `_index-archive-YYYY-Q.md`.

Estatísticas atuais:
- Pace observado: **~35 slugs/dia** × 90 dias = ~3.150 slugs projetados.
- 464 linhas (×16) = ~7.400 tokens **lidos por Guardian a cada audit**.
- Projeção 90d: ~50.000 tokens/audit.

Fingerprint mencionado em 2026-05-11 (`token-changelog-already-growing-and-not-extracted-by-release`), 2026-05-12 (`token-changelog-cresceu-de-119-para-129-linhas-em-um-dia`), 2026-05-13 (`token-changelog-130-lines-after-rotation-suggestion-still-pending-3rd-pass`) — **4ª passada agora**.

**Impacto positivo:**
- Criar `scripts/archive-index.sh` proativo: extrai entradas > 30 dias para `_index-archive-2026-Q2.md`.
- Reduz carga de leitura do Guardian em 60-70%.
- Modelar política em código antes que vire incidente.

**Impacto negativo:** script novo (+50 linhas); risco mínimo de mover entrada errada (mitigável com `--dry-run`).

---

## 5. `token-code-reviewer-still-eager-loads-comments-policy-after-lazy-load-fix-applied`

**Arquivo:** `agents/code-reviewer.md`

**Observação:** o commit `4307f31` aplicou padrão lazy-load condicional por linguagem para `skills/shared/comments-policy/SKILL.md` em 9 agents. Porém **code-reviewer** (mais frequente consumidor) ainda carrega eager em Foundational Rule item 9.

**Quantificação:**
- comments-policy SKILL.md (pós-extração) = 91 linhas × 16 = 1.456 tokens.
- code-reviewer spawneado em `/devteam:review` e `/devteam:pr` (2 commands).
- Lazy-load condicional carrega apenas seções relevantes (~25 linhas) → economia ~1.000 tokens/spawn.

**Impacto positivo:** **~1.000 tokens/spawn** (×2 commands × ~10 spawns/dia) = ~20.000 tokens/dia.

**Impacto negativo:** code-reviewer Foundational fica com 1 linha a mais ("Load comments-policy/sections/<lang>.md if relevant"); aceitável.

---

## 6. `token-worktree-isolation-block-136-duplicate-lines-across-8-coding-agents` — HIGH

**Arquivos:** todos os coding agents (8): `backend-developer`, `frontend-developer`, `mobile-developer`, `database-specialist`, `devops-specialist`, `ui-ux-designer`, `backend-test-specialist`, `frontend-test-specialist`

**Observação:** cada um inline um bloco "Worktree Isolation" de **17 linhas** com instruções idênticas (read `.claude/.worktree-session`, perguntar se necessário, carregar worktree skill etc.).

**Quantificação:**
- 17 linhas × 8 agents = **136 linhas duplicadas no repo**.
- × 16 tokens = ~2.176 tokens × N spawns por sessão.
- Multi-agent flow típico (`/devteam:fullstack` = 4-5 coding agents) = ~10.000 tokens duplicados.

**Impacto positivo:**
- Extrair para `skills/shared/worktree-isolation/SKILL.md` (já existe `worktree/SKILL.md` que é diferente — handle worktree, este é a logic de detecção).
- Cada agent reduce 17 → 1 linha (`Load skills/shared/worktree-isolation/SKILL.md`).
- Economia 16 × 8 = **128 linhas no repo**; ~2.000 tokens/spawn em multi-agent flows.

**Impacto negativo:** mais um skill no repo; pequeno aumento na complexidade do orphan-scan.

---

## 7. `token-runbook-skill-new-loads-unreachable-template-path-installed-projects`

**Arquivo:** `skills/shared/runbook/SKILL.md` (criada hoje via commit `19ef0f9`, 28 linhas)

**Observação:** a skill referencia `templates/runbook-template.md` como path relativo. Conforme [01-referencias-e-consistencia #3](01-referencias-e-consistencia.md#3), o `install.sh` não symlinka `templates/` em `.claude/templates/`. Em projetos instalados, agent carrega skill que aponta para arquivo **inexistente**.

**Quantificação:**
- Skill: 28 linhas × 16 = 448 tokens/spawn.
- Consumer: `agents/technical-writer.md:25` (1 carga).
- Carga útil real: **0 tokens** (arquivo destino não resolve).

100% waste em produto instalado; funciona apenas no repo dev-time.

**Impacto positivo:**
- Fix #3 acima (symlink templates/) elimina o waste; OU
- Inline o template no SKILL.md (28 → ~60 linhas, mas autoconto).

**Impacto negativo:** depende da decisão de path absoluto vs relativo em todo o repo (vide #3).

---

## Resumo Quantitativo

| # | Fingerprint | Token economy / spawn | Frequência | Total estimado/dia |
|---|-------------|----------------------|------------|--------------------|
| 1 | setup-assistant immutability | ~480 | 5 spawns | ~2.400 |
| 2 | notifier tips externalize | overhead −67% | 30 stops | overhead-only |
| 3 | CLAUDE.md hook+commands extract | ~2.300 × 7 | per session | ~16.000 |
| 4 | _index.md archive | ~5.000 | 1 audit | ~5.000 |
| 5 | comments-policy lazy in reviewer | ~1.000 | 20 spawns | ~20.000 |
| 6 | worktree-isolation extract | ~2.000 | multi-agent | ~10.000 |
| 7 | runbook template fix | ~450 (recuperado) | 1 spawn | ~450 |
| **Total** | | | | **~54.000 tokens/dia** |
