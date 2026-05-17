# Economia de Tokens — 2026-05-16

> Oportunidades de redução de tokens carregados por spawn de agente ou por execução de hook. Foco: bugs que **inflam custo silenciosamente** (fast-path broken, CI minutes desperdiçados), e quantificações novas de drift acumulado.

---

## 1. `token-stop-04-notifier-fast-path-broken-burns-80-150ms-per-stop-call-in-conversational-sessions` — HIGH

**Arquivo:** `scripts/hooks/stop/04-notifier.sh:88`

**Quantificação:** o fast-path **está broken** (ver [02-fluxos-e-workflows.md#1](02-fluxos-e-workflows.md#1)). Comparação `"1" = "true"` nunca dispara.

**Custo medido em sessão conversacional típica (30 turns Stop):**

| Operação | Tempo médio | × 30 turns |
|----------|-------------|-----------|
| Read `preferences.json` (python3 fork) | ~30ms | 900ms |
| Read transcript JSONL + parse | ~40-80ms | 1.2-2.4s |
| Iterate tip arrays (45 strings) | ~5ms | 150ms |
| Cálculo % janela | ~10ms | 300ms |
| **Total estimado/sessão** | — | **~2.5-3.8s desperdiçados** |

**Cumulativo (assumindo 10 sessões puramente conversacionais/dia × 30 dias):**
- 10 × 30 × 3s = **15 min de wall-clock desperdiçados/mês** apenas neste bug.
- Em modelos onde Stop hooks bloqueiam UX, latência é diretamente sentida pelo usuário.

**Por que importa (token angle):**
- Hooks que poderiam exitar cedo não consomem CPU adicional, mas em modelos serverless / containerized (futuro), cada ms de hook = $custo. Hoje é "apenas tempo"; amanhã pode ser conta.

**Impacto positivo do fix:** trocar `"true"` por `"1"` — recupera ~75% da economia teórica do fast-path quando aplicável.

**Impacto negativo:** zero.

---

## 2. `token-check-fingerprint-uniqueness-broken-regex-burns-CI-minutes-with-permanent-false-pass` — MEDIUM

**Arquivo:** `scripts/check-fingerprint-uniqueness.sh:13`

**Quantificação:**
- CI roda script em **todo PR** (configurado em `.github/workflows/ci.yml:25`).
- Script faz: `grep -oE '\`...\`' _index.md | sort | uniq -d` em arquivo de **509 linhas**.
- Tempo médio: ~150ms.
- Como regex matcha zero entradas + `set -o pipefail` propaga exit 1 ⇒ script **sempre exita 1** e CI fica vermelho permanente (sem `continue-on-error`).
- Custo: ~150ms × N runs futuros desperdiçados em diagnose ("por que CI está vermelho?").

**Mais grave (qualitativo):** próximo PR a ser aberto vai descobrir que o CI bloqueia tudo. Tempo de debug estimado: 30-60 min do mantenedor (procurar regex bug em script novo, validar manualmente, escrever fix, reabrir PR).

**Por que importa:**
- Não é cost angle puro; é **economia de tokens em diagnóstico futuro**. Quando colisão real causar bug em alguma automação que itera fingerprints, debug consumirá ~1h de Opus reasoning + leitura cruzada de 4 arquivos.
- Fix preventivo (4 caracteres deletados) evita ~10-15k tokens de debug futuro.

**Impacto positivo:** ver fix em [01-referencias-e-consistencia.md#1](01-referencias-e-consistencia.md#1).

**Impacto negativo:** zero.

---

## 3. `token-_index-md-509-lines-grew-45-lines-in-24h-rotation-still-not-actioned-after-5-passes` — HIGH

**Arquivo:** `docs/reports/_index.md`

**Trajetória observada:**

| Data | Linhas | Δ | Δ % |
|------|--------|---|-----|
| 2026-05-13 | 380 | — | — |
| 2026-05-14 | ~420 | +40 | +10,5% |
| 2026-05-15 | 464 | +44 | +10,5% |
| **2026-05-16** | **509** | **+45** | **+9,7%** |

**Pace constante: ~45 linhas/dia**, mesmo sem fingerprints novos (a tabela "Estatísticas" cresce 1 linha por audit + os blocos de detalhes Guardian crescem por discussão).

**Projeção:** 1.000 linhas em **2026-06-06** (21 dias); 1.500 linhas em **2026-06-29** (44 dias).

**Custo por audit Guardian:**
- 509 × 16 tokens/linha = **~8.144 tokens** para ler o índice inteiro.
- Spot-check carrega `_index.md` 1× + ~10 arquivos auxiliares.
- Em Opus (custo proxy): cada audit = ~$0,15 só do índice.

**Por que importa:**
- 5ª menção do mesmo problema sem ação concreta. Script `archive-index.sh` foi proposto múltiplas vezes; nunca escrito.
- Sub-fingerprints diferentes (`token-fingerprint-index-_index-md-380-lines-not-rotated-yet`, `token-index-md-growing-35-slugs-per-day-archive-script-still-unwritten-after-3-mentions`) tentaram com escopos progressivos; todos pendentes.

**Impacto positivo:** escrever `scripts/archive-index.sh` (~30 linhas):
```bash
# Move entries older than 90 days to _index-archive-YYYY-QN.md
CUTOFF=$(date -d "90 days ago" +%Y-%m-%d)
awk -v cutoff="$CUTOFF" '...' _index.md
```
Reduz `_index.md` para ~150 linhas (cabeçalho + Estatísticas + últimos 3-5 dias).

**Impacto negativo:** lookup de fingerprint antigo exige `grep _index*.md` em vez de só `_index.md`. Mitigável por `scripts/lookup-fingerprint.sh` wrapper.

---

## 4. `token-CLAUDE-md-425-lines-still-monolithic-after-fase-1-fragmentation-30-line-commands-table-not-extracted` — HIGH

**Arquivo:** `CLAUDE.md` (425 linhas)

**Estado pós-fase-1:** 557 → 425 linhas (−132, −24%) via extração para `CLAUDE-md/{notifications,preferences,user-data,versioning}.md`. ✅ executou parte do trabalho.

**Pendente quantificado:**

| Seção | Linhas atuais em CLAUDE.md | Candidato à extração |
|-------|----------------------------|------------------------|
| "User-Invocable Commands" (tabela de 30 entries) | linhas 144-179 (~36 linhas) | `CLAUDE-md/commands.md` |
| "Stop Hook (Automated Enforcement)" + "Stop Hook Sub-script Convention" + "Hook Files Map" | linhas 339-380 (~42 linhas) | `CLAUDE-md/hooks.md` |
| "Agent Memory System" (Session Summary + ADR + Stop Hook) | linhas 251-380 (~130 linhas) | `CLAUDE-md/memory-system.md` |

**Cost atual:** 425 × 16 × 7 spawns típicos = **~47.600 tokens/sessão multi-agent**.
**Cost pós-extração total estimada:** ~250 × 16 × 7 = **~28.000 tokens** (economia ~19.600/sessão).

**Por que importa:**
- Fase 1 cortou 24%. Próximas extrações são mecânicas (mesma técnica), economia compounding.
- Fingerprint pai (2026-05-15) registrou tema. Sub-escopo aqui quantifica especificamente a tabela de commands e a seção de hooks.

**Impacto positivo:** −175 linhas em CLAUDE.md; setup-assistant pula `commands.md` em onboarding (não precisa); arquitetos não leem `hooks.md` (não tocam hooks normalmente).

**Impacto negativo:** mais arquivos em `CLAUDE-md/` (hoje 4; passaria a 7); navegação por busca substitui scan visual em arquivo único.

---

## 5. `token-orphan-skill-scan-and-template-scan-duplicate-find-passes-on-skills-directory` — MEDIUM

**Arquivos:**
- `scripts/orphan-skill-scan.sh` (183 linhas)
- `scripts/orphan-template-scan.sh` (36 linhas)

**Observação:** ambos scripts fazem `find ...` independentemente sobre o mesmo diretório `skills/` (skill-scan) ou `templates/` (template-scan) — e ambos rodam em sequência no Stop hook (sub-scripts 02 e 02b).

```bash
# 02-orphan-skill-scan.sh chama
find skills -name SKILL.md ...
grep -r ... agents commands workflows ...

# 02b-orphan-template-scan.sh chama
find templates -name "*.md" ...
grep -r ... agents commands workflows skills ...
```

Duplicação:
- 2× `find` em diretórios sobreposíveis (templates é pequeno, skills é grande).
- 2× `grep -r agents commands workflows` (idêntico, ~50ms cada em repo médio).

**Por que importa:**
- ~100ms/Stop desperdiçados em duplicação de I/O.
- Combinado com fast-path broken (item #1) e a falta de filter por path no CI (item #8 do report 02), Stop hook é mais pesado do que precisa.

**Impacto positivo:** consolidar em `scripts/orphan-scan.sh` único que faz **1 pass** sobre `agents+commands+workflows+skills`, popula 2 hashtables (skill_ref_count, template_ref_count), e emite ambos relatórios. ~−50ms/Stop. ~−10k bytes de código.

**Impacto negativo:** acopla 2 scanners; necessidade de mudar 1 sem o outro fica mais cara. Mitigável por modular `--mode=skills|templates|both`.

---

## 6. `token-software-architect-anti-overengineering-rules-extracted-to-skill-loaded-by-5-agents` — LOW

**Cross-cut:** sub-escopo de [03-agentes-e-skills.md#6](03-agentes-e-skills.md#6) com viés token.

**Quantificação:**
- Bloco "Anti-overengineering rules" em `software-architect.md` = 10 linhas (block + 4 bullets) = ~160 tokens.
- Se extraído para `skills/architecture/anti-overengineering/SKILL.md`, ficaria fora do agent — economia de 160 tokens em todo spawn de architect.
- Architect é spawneado em 9 commands → ~1.440 tokens/dia se 1 spawn/command/dia em audit ativo.
- Reaproveitamento: 4 outros agents que carregariam (`code-reviewer`, `security-specialist`, `database-specialist`, `devops-specialist`).

**Por que importa:**
- Economia individual pequena, mas **viabiliza fix do bias** (item #1 do report 03) em **um único arquivo** em vez de 5.

**Impacto positivo:** ~1.440 tokens/dia economizados em audit Opus ativo; centralização de princípios anti-overengineering.

**Impacto negativo:** +1 skill no repo (skills total: 126 → 127); fragmentação cresce; mitigável por skill < 30 linhas.

---

## 7. `token-changelog-130-lines-stable-but-still-not-rotated-after-3rd-mention-archive-script-pending` — LOW (re-afirmação)

**Arquivo:** `CHANGELOG.md` (130 linhas)

**Observação:** 3ª passada. CHANGELOG permanece em 130 linhas (estável, sem crescimento em 24h porque sem release). Threshold proposto para rotação: 300 linhas.

**Cost atual:** 130 linhas × 16 tokens = ~2.080 tokens lidos por `setup-assistant` em FIRST_RUN. Carregamento eager apesar de raro caso de uso (usuário em first-run raramente quer ler todo o histórico).

**Por que importa:**
- Pace observado em meses anteriores: ~80 linhas/mês. A 300 chega em ~2 meses.
- Pattern análogo ao `_index.md` (item #3): script `archive-changelog.sh` proposto várias vezes, nunca escrito.
- Re-afirmação serve para sustentar pressão de prioridade — não para economia imediata.

**Impacto positivo (preventivo):** quando CHANGELOG cruzar 300 linhas, script pronto evita ~3.000 tokens/onboarding.

**Impacto negativo:** zero.

---

## 8. `token-templates-runbook-79-lines-largest-template-load-broken-by-symlink-100pct-waste-in-installed` — sub-escopo (NEW angle)

**Arquivo:** `templates/runbook-template.md` (79 linhas)

**Observação:** sub-escopo do fingerprint `token-runbook-skill-new-loads-unreachable-template-path-installed-projects` (2026-05-15) com viés de **quantificação por template específico**.

`runbook-template.md` é o maior dos 4 templates (79 linhas, vs adr=31, backlog=35, plan=56):

| Template | Linhas | Tokens (×16) |
|----------|--------|--------------|
| `runbook-template.md` | 79 | ~1.264 |
| `plan-template.md` | 56 | ~896 |
| `backlog-template.md` | 35 | ~560 |
| `adr-template.md` | 31 | ~496 |

Em **projetos instalados** (sem symlink), `skills/shared/runbook/SKILL.md` faz 3 chamadas a `Read templates/runbook-template.md`. Cada Read falha silenciosamente (arquivo não encontrado), mas a skill consome tokens próprios (28 linhas SKILL.md) + tentativa de Read (overhead Read tool + erro).

**Cost desperdiçado:** 28 linhas × 16 = ~448 tokens de SKILL.md sem entrega de valor (template prometido nunca chega).

**Por que importa:**
- Skill criada em 2026-05-15 (`19ef0f9`); 100% de waste em produto instalado desde dia 1.
- Cross-link com [01-referencias-e-consistencia.md#6](01-referencias-e-consistencia.md#6) (mesmo root cause).
- Fix do symlink (1 linha em install.sh) recupera ~1.700 tokens reais (28 SKILL + 79 template).

**Impacto positivo:** mesmo do item #6 do report 01. Skill funciona como prometido; technical-writer entrega runbooks com structure consistente.

**Impacto negativo:** zero.
