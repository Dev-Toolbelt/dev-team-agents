# Referências e Consistência — 2026-05-15

> Auditoria de cross-references, declarações vs. implementação, e violações de regras canônicas do `CLAUDE.md`.

---

## 1. `auto-fingerprint-script-matches-body-text-not-entry-line-anchors` — HIGH

**Arquivo:** `scripts/check-fingerprint-uniqueness.sh:13`

```bash
grep -oE '`[a-z][a-z0-9-]+`' "$INDEX" | sort | uniq -d
```

**Observação:** o regex captura **qualquer** kebab-case envolvido em backticks no corpo do `_index.md` — não apenas as entradas de fingerprint reais. Testes locais revelam **63 falsos positivos** identificados como "duplicados":

- Nomes de agents: `setup-assistant` (×7), `product-analyst` (×6), `software-architect` (×5)
- SHAs de commit: `b8ece69`, `f96f3cd`, `d05242a`, `7977977`...
- Comandos shell mencionados em explicações: `curl`, `git-log`
- Menções narrativas dentro de descrições de outros fingerprints

**Por que importa:**
- O gate CI é **efetivamente cosmético** — 0 colisões reais existem hoje (validado via `sed -nE 's/^- \`([a-z][a-z0-9-]+)\`.*/\1/p' _index.md | sort | uniq -d`).
- Em algum momento, dois SHAs ou nomes de agents coincidirão → CI vermelho sem causa real.
- Sugere fix: ancorar regex em `^- \`([a-z][a-z0-9-]+)\`` (apenas linhas de entrada).

**Impacto positivo do fix:** elimina ruído crítico no CI; permite enforcement real de unicidade.
**Impacto negativo do fix:** zero — é estritamente bug fix.

---

## 2. `ref-install-fallback-prefs-missing-transcript-multiplier-and-model-max-tokens` — HIGH

**Arquivo:** `scripts/install.sh:493-503`

**Observação:** o ramo de fallback do `install.sh` (quando `python3` está ausente) escreve `preferences.json` **sem** as chaves `transcript_multiplier` e `model_max_tokens`. Ambas:

- Estão declaradas como obrigatórias em `CLAUDE-md/preferences.md` (schema canônico).
- São consumidas por `scripts/hooks/stop/04-notifier.sh` para estimação de janela de contexto.

**Por que importa:**
- Em usuários sem `python3` (raros mas existem: Alpine puro, contêineres minimal), `04-notifier.sh` falha ao ler chaves inexistentes → notification silenciosamente desligada.
- Ramo Python merge defaults; ramo fallback emite arquivo incompleto. Divergência funcional sem registro.

**Impacto positivo do fix:** paridade Python/fallback; notificação consistente.
**Impacto negativo do fix:** +5 linhas no fallback `cat << EOF` block.

---

## 3. `ref-templates-dir-shipped-but-not-symlinked-relative-path-broken-from-agent-cwd`

**Arquivos:**
- `agents/setup-assistant.md:22, 131`
- `skills/shared/runbook/SKILL.md:8, 17, 28`
- `CLAUDE.md:38` (mandatory plan-template reference)

**Observação:** ambos os arquivos referenciam `templates/plan-template.md` e `templates/runbook-template.md` como path **relativo**. O `install.sh` faz symlink de `.dev-team-agents/templates/` mas **não cria atalho em `.claude/templates/`**. Agentes lendo a partir de `.claude/agents/dev-team/` resolvem o path para nada.

**Por que importa:**
- Quando agent é spawneado em projeto instalado, `Read templates/plan-template.md` falha (arquivo não encontrado).
- Documentação implícita assume path repo-relative; instalação não preserva.

**Impacto positivo:** adicionar 1 linha de symlink em `install.sh` (`ln -sf "$INSTALL_DIR/templates" "$HOME/.claude/templates"`) ou ajustar agents para usar `.dev-team-agents/templates/...` (path absoluto pós-install).

**Impacto negativo:** decisão de path absoluto fragmenta o padrão usado em outros loads (skills usam relative paths). Discussão de padrão necessária.

---

## 4. `ref-stack-detection-skill-created-but-zero-agent-loads-still-orphan-on-day-of-creation`

**Arquivo:** `skills/shared/stack-detection/SKILL.md` (criada hoje, 36 linhas, commit `4307f31`)

**Observação:** a skill foi criada em resposta ao fingerprint pendente de 2026-05-13 (`skill-stack-detection-still-missing-3rd-pass-shared-base-needed`). Porém **nenhum agent foi alterado para carregá-la**:

```bash
grep -rl "skills/shared/stack-detection" agents commands workflows
# → 0 hits
```

**Por que importa:**
- Os 4 agentes-alvo (`setup-assistant`, `software-architect`, `database-specialist`, `devops-specialist`) continuam com heurística inline divergente.
- Skill nasceu órfã no dia da criação — anti-padrão.
- Reportado pelo `scripts/orphan-skill-scan.sh` na execução de hoje.

**Impacto positivo do fix:** wiring em 4 agentes (~4 linhas) elimina divergência de heurísticas; consolida fonte de verdade.

**Impacto negativo do fix:** +36 linhas eager-loaded em 4 agentes (~576 tokens × spawn). Mitigável via gate condicional ou lazy-load (vide [04-economia-tokens](04-economia-tokens.md)).

---

## 5. `ref-haiku-residual-claude-md-note-after-executed-removal`

**Arquivo:** `CLAUDE.md:120`

**Observação:** o fingerprint `ref-haiku-model-declared-in-claude-md-but-zero-agents-use-it` (2026-05-14) foi marcado ✅ Executed via simplificação da regra. Porém **prosa residual permanece**:

```
> Note: Haiku is available for future micro-agents with strict latency/cost requirements; add it back when a concrete candidate emerges.
```

**Por que importa:**
- Regra "dangling" sem enforcement nem candidato concreto.
- Cria ambiguidade para autor de novo agent: "posso usar Haiku?" → sim, mas sem critério explícito.
- Viola princípio de "rules são vinculantes — observações vão para docs".

**Impacto positivo:** remover linha ou mover para `docs/reports/historical-decisions.md`; CLAUDE.md fica 1 linha menor.

**Impacto negativo:** perde histórico de decisão (mitigável com link para ADR).

---

## 6. `ref-refactor-command-missing-interaction-patterns-load-despite-yes-no-prompts`

**Arquivo:** `commands/refactor.md` (152 linhas)

**Observação:** o command carrega `spawn-classifier`, `plan-mode` e `worktree`, mas **não carrega `skills/shared/interaction-patterns/SKILL.md`** — apesar de fazer:
- Pergunta worktree yes/no
- Confirmação de escopo
- Quiz de fast-track sim/não

A skill é obrigatória por `CLAUDE.md:141` ("Quiz-first Rule"). Sibling commands (`backend.md`, `fix.md`, `update.md`) já carregam.

**Por que importa:**
- Maior risco de plain-text prompts no fluxo de refactoring.
- Inconsistência de adoção da skill — só 4/30 commands carregam após 24h de propagação.

**Impacto positivo:** +1 linha no command; comportamento alinhado com regra canônica.
**Impacto negativo:** +185 linhas eager-loaded para a skill no spawn. Lazy-load condicional preferível.

---

## 7. `ref-setup-assistant-violates-quiz-first-rule-multiple-plain-text-prompts`

**Arquivo:** `agents/setup-assistant.md`

**Observação:** o agent viola a Quiz-first Rule (CLAUDE.md:141) em pelo menos 2 lugares:

- Linha 124: `"Set up Graphify now? **yes / no**"` (plain-text yes/no)
- Step 2: numbered choice list (`1. New project / 2. Unfinished / 3. Maintenance`) em vez de `AskUserQuestion`

Zero ocorrências de `AskUserQuestion` no agent inteiro.

**Por que importa:**
- Setup-assistant é o **primeiro contato** do usuário com o repo (`/devteam:setup` trigger).
- Viola regra crítica em local de maior visibilidade.
- Bloqueia execução do fingerprint `skill-shared-interaction-patterns-185-lines-but-zero-yes-no-prompt-fixers-applied-to-existing-agents` (2026-05-14, ✅) — agent não foi retrofitado.

**Impacto positivo:** substituir 2 prompts por `AskUserQuestion`; melhora UX; alinha com regra canônica.
**Impacto negativo:** breaking change em fluxo conhecido — usuários acostumados a digitar `yes` precisarão escolher botão (pequeno atrito UX).
