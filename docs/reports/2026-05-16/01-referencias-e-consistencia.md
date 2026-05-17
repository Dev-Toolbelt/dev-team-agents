# Referências e Consistência — 2026-05-16

> Auditoria de cross-references, declarações vs. implementação, e violações de regras canônicas do `CLAUDE.md`. Foco: bugs ocultos em scripts, violações de stack-agnosticism migradas para outro agent, regressão silenciosa do fast-path do notifier, dois templates novos órfãos no dia da criação (já há 3 dias).

---

## 1. `auto-fingerprint-script-regex-actually-matches-zero-entries-CI-gate-permanent-no-op` — CRITICAL

**Arquivo:** `scripts/check-fingerprint-uniqueness.sh:13`

**Diagnóstico refinado (vs. fingerprint pai de 2026-05-15):**

A passada anterior reportou que o regex captura **63 falsos positivos** (nomes de agents, SHAs, comandos). Esta verificação direta encontrou o oposto:

```bash
$ grep -oE '\`[a-z][a-z0-9-]+\`' docs/reports/_index.md | wc -l
0

$ grep -oE '`[a-z][a-z0-9-]+`' docs/reports/_index.md | wc -l    # sem escape
543
```

O regex no script usa `'\`[a-z][a-z0-9-]+\`'`. Como está dentro de single-quotes, o `\` é literal — `grep -E` recebe `\`` que **não é um escape válido** para backtick (backtick não é metachar em ERE). Resultado: a classe `\`` é interpretada como literal `\` seguido de `` ` ``, e a string `_index.md` não contém `` \` ``.

**Consequência prática (pior do que parece):**

Combinando regex broken com `set -euo pipefail` (linha 4) e a atribuição `DUPLICATES=$(grep ... | sort | uniq -d)`:

1. `grep -oE` retorna **exit 1** (zero matches).
2. `pipefail` propaga essa falha através do pipeline.
3. `set -e` aborta o script no momento da atribuição.
4. Script **sempre exita 1**.
5. CI step `Check fingerprint uniqueness` no `.github/workflows/ci.yml:25` **sem `continue-on-error: true`** ⇒ **CI deve estar vermelho desde o commit `847da80` (2026-05-15)**.

Inversamente ao que o fingerprint anterior descreveu (CI cosmético), o gate **falha permanentemente** em qualquer execução. Há duas explicações possíveis para o CI parecer verde:
- Step `set -o pipefail` está sendo subvertido por algum hook do GitHub Actions (improvável).
- Nenhum PR foi mergeado desde 2026-05-15; última passagem CI verde foi no commit anterior.

A última hipótese é a mais provável (já que o último commit é `0bd74d6` em 2026-05-15 12:30 e este audit ocorre 2026-05-16 sem commits intermediários).

Verificação local confirma:
```bash
$ bash scripts/check-fingerprint-uniqueness.sh; echo "EXIT=$?"
EXIT=1
```

- Sub-escopo do fingerprint anterior (`auto-fingerprint-script-matches-body-text-not-entry-line-anchors`) ficou desatualizado no dia seguinte à publicação.

**Por que importa:**
- CI gate fantasma cria falsa confiança ("temos enforcement de unicidade de fingerprints!").
- Promoção de `auto-no-fingerprint-collision-check` (2026-05-08) → fingerprint-uniqueness script (2026-05-15) deveria ter passado spot-check de Guardian.

**Impacto positivo do fix:** trocar `'\`...\`'` por `'`...`'` (4 caracteres deletados); ancorar regex apenas em linhas de entrada via `'^- `([a-z][a-z0-9-]+)`'` opcional; CI passa a falhar em PRs futuros que introduzam colisões reais.

**Impacto negativo do fix:** zero — bug fix puro.

---

## 2. `ref-software-architect-line-117-kubernetes-docker-compose-vps-stack-bias-mirrors-devops-fix` — HIGH

**Arquivo:** `agents/software-architect.md:117`

**Observação:** após o fix de `agent-devops-specialist-violates-stack-agnostic-rule-with-docker-first-bias` (2026-05-13, marcado ✅), uma violação **espelho** persiste no software-architect:

```markdown
**Anti-overengineering rules:**
- Don't recommend microservices when a monolith will work
- Don't recommend a message queue when a simple cron job or synchronous call will work
- Don't recommend distributed caching when database query optimization is needed first
- Don't recommend Kubernetes when Docker Compose on a VPS will handle the load
```

A última linha presume:
1. Que **Docker Compose** é a alternativa default a Kubernetes (e não Nomad, Swarm, ECS, plain systemd, Capistrano, Heroku-style PaaS).
2. Que **VPS** é o ambiente default (e não bare metal, on-prem, Lambda, Cloud Run, App Engine, Fly.io, Render).

Viola CLAUDE.md → "What This Repo Is" (linha 17): "Stack-agnostic, project-aware".

**Padrão observado:** o bias migrou do devops para o architect — não foi eliminado, apenas movido de agente. Outras 3 linhas (`microservices`, `message queue`, `distributed caching`) são princípios genuinamente stack-agnostic; só a 4ª importa este vício.

**Impacto positivo do fix:** trocar por `"Don't recommend orchestrators (Kubernetes, Nomad, ECS) when a single-node container runtime or PaaS will handle the load"` — preserva o princípio (anti-overengineering) sem nomear stack.

**Impacto negativo do fix:** perda de exemplo concreto que ajudava leitores a internalizar a regra; mitigável com nota "examples: Docker Compose, single-host deployments, managed PaaS".

---

## 3. `ref-devops-specialist-description-line-8-still-lists-deployment-defaults-after-body-fix` — sub-escopo

**Arquivo:** `agents/devops-specialist.md:8`

**Observação:** o fix de 2026-05-15 limpou o corpo do agente. Mas a primeira linha do papel (Core identity) ainda lista defaults por categoria:

```
You are a **DevOps Specialist** — a pragmatic infrastructure engineer who builds simple, reliable, cost-efficient deployments. You avoid overengineering. Your default answer to "how should we deploy this?" depends on the project's existing stack, scale, and team expertise — Docker Compose for small teams, Kubernetes for distributed systems, serverless for event-driven workloads.
```

A última cláusula ("Docker Compose for small teams, Kubernetes for distributed systems, serverless for event-driven workloads") **define o default explícito por categoria** — exatamente o que a versão limpa do corpo evita.

**Por que importa:** primeira linha do agente influencia o tom de todas as respostas. Lendo essa linha, o LLM ancora em "Docker Compose = small teams" e tenderá a recomendar mesmo quando o projeto usa, por exemplo, Apache Mesos ou Capistrano legado.

**Impacto positivo do fix:** trocar a frase por `"Your default answer to 'how should we deploy this?' is 'show me what you already use' — never an opinion before evidence."` (mantém o tom pragmatic, remove a tabela mental de stack defaults).

**Impacto negativo do fix:** ~10 palavras a menos na descrição → setup-assistant pode perder pista visual rápida sobre o agent; mitigável com seção "## Stack Examples" no body, descritiva e sem prescrição.

---

## 4. `ref-templates-adr-and-backlog-orphan-since-creation-2026-05-13-no-loader-wired` — HIGH

**Arquivos:**
- `templates/adr-template.md` (31 linhas, commit `c207e3f`)
- `templates/backlog-template.md` (35 linhas, mesmo commit)

**Observação:** `bash scripts/orphan-template-scan.sh` reporta:

```
ACTION REQUIRED — Orphan templates (no agent/skill/command references):
  · templates/adr-template.md
  · templates/backlog-template.md
```

Verificação manual:

```bash
$ grep -rl "templates/adr-template" agents commands skills workflows
# (empty)
$ grep -rl "templates/backlog-template" agents commands skills workflows
# (empty)
```

**Origem do problema:**
- ADRs são criados via `scripts/new-adr.sh`, que gera o template **inline via heredoc** (linhas 32-73 do script) — **ignora completamente** `templates/adr-template.md`. Dois "ground truths" coexistem; o do script é o que vence.
- `backlog-template.md` foi criado para servir o `product-analyst`, mas o agent carrega a skill `skills/shared/backlog-template/SKILL.md` que tem o template **embutido no próprio SKILL.md** — o arquivo físico em `templates/` nunca é lido.

**Por que importa:**
- 3 dias depois da criação, dois templates são lixo morto — pegada do anti-pattern "criar template antes do consumer".
- Quando `scripts/new-adr.sh` e `templates/adr-template.md` divergirem (heredoc vs arquivo), qual é a fonte? Sem teste, qualquer mudança em um lado dessincroniza silenciosamente.
- Fingerprint `skill-templates-folder-grew-but-no-template-skill-wraps-them` (2026-05-13, ✅ Executed) considerou o problema resolvido apenas pela existência do `runbook-template.md` + skill. ADR e backlog ficaram fora do escopo.

**Impacto positivo do fix:** modificar `scripts/new-adr.sh` para `cat .claude/dev-team-agents/templates/adr-template.md > "$FILENAME"` + substituir placeholders por sed; modificar `skills/shared/backlog-template/SKILL.md` para carregar `templates/backlog-template.md` em vez de embutir. Elimina divergência potencial. **Bloqueado por** fingerprint #3 da passada de 2026-05-15 (symlink de templates ausente).

**Impacto negativo do fix:** dependência runtime de existência do arquivo (mitigável por fallback para heredoc atual).

---

## 5. `ref-install-sh-both-python-and-fallback-branches-miss-transcript-multiplier-and-model-max-tokens` — HIGH

**Arquivo:** `scripts/install.sh:406-462`

**Sub-escopo refinado (vs. fingerprint pai de 2026-05-15):** o fingerprint anterior limitou-se ao ramo fallback. Verificação direta mostra que **o ramo Python também omite** as duas chaves:

```python
defaults = {
    "language": language,
    "context_window_percent_warning": 55,
    "context_window_percent_limit": 60,
    "suppress_notifications": False,
    "session_summary_max_days": 30,
    "session_summary_max_entries": 30,
    "docs_stale_after_days": 30,
    "auto_update": auto_update,
    "update_check_interval_hours": 24,
    # ❌ transcript_multiplier ausente
    # ❌ model_max_tokens ausente
}
```

`CLAUDE-md/preferences.md` (schema canônico) declara explicitamente:

| Field | Default | Purpose |
|-------|---------|---------|
| `transcript_multiplier` | `1.8` | Multiplier para estimar contexto completo |
| `model_max_tokens` | `200000` | Janela do modelo ativo |

Os dois são consumidos por `scripts/hooks/stop/04-notifier.sh` para cálculo de % de janela usada.

**Por que importa:**
- Sem essas chaves no JSON, `04-notifier.sh` cai em hardcoded defaults (provavelmente OK para Sonnet, mas errado para Haiku 200k vs Opus 200k vs futuros modelos com janelas distintas).
- `setup-health-check` valida schema e auto-corrige — mas só se já houver execução prévia que dispare a verificação.
- Toda nova instalação fica com o JSON incompleto.

**Impacto positivo:** +2 linhas no dict Python e +2 no heredoc fallback. Notificação consistente entre instalações.

**Impacto negativo:** zero.

---

## 6. `ref-setup-assistant-uses-templates-plan-template-relative-path-same-root-cause-as-runbook-skill` — sub-escopo

**Arquivo:** `agents/setup-assistant.md:22, 131`

**Observação:** mesmo bug do fingerprint #3 de 2026-05-15 (`ref-templates-dir-shipped-but-not-symlinked-relative-path-broken-from-agent-cwd`), expandido para o setup-assistant. Linha 22 do agent:

```
**Before any non-trivial step, present a plan using `templates/plan-template.md` and wait for approval.**
```

E linha 131:

```
Present a plan using `templates/plan-template.md` before creating any file. Wait for approval.
```

O agent é spawneado em `.claude/agents/dev-team/`, e o cwd típico no spawn não inclui `dev-team-agents/templates/`. Logo o `Read templates/plan-template.md` falha silenciosamente — o agent vai para fallback (apresenta plano sem template formal), mas usuário recebe estrutura diferente da prometida.

**Cross-cut:** mesma raiz também atinge `skills/shared/project-context/SKILL.md:70` (`Present the plan using the canonical format from \`templates/plan-template.md\``) e `skills/shared/runbook/SKILL.md` (3 ocorrências).

**Por que importa:** templates físicos foram introduzidos para serem **a fonte canônica** (vs. inline). Se nenhuma consumer lê do path correto, voltam ao mesmo problema que o esforço pretendia resolver.

**Impacto positivo:** uma única correção no `install.sh` (adicionar `ln -sf "$INSTALL_DIR/templates" "$HOME/.claude/templates"` na seção "Step 4: Link agents") resolve TODOS os consumers de uma vez. Alternativa: ajustar todos os consumers para usar `.claude/dev-team-agents/templates/...` (path absoluto pós-install) — mais arquivos para tocar.

**Impacto negativo:** se o usuário rodar `rm -rf .claude/templates/` deliberadamente, symlink dangling. Mitigável por health-check que recria.

---

## 7. `ref-new-adr-script-creates-templates-inline-via-heredoc-ignoring-templates-adr-template-md` — MEDIUM

**Arquivo:** `scripts/new-adr.sh:32-73`

**Observação:** o script tem 73 linhas; ~42 delas são um heredoc inline gerando o template. Em paralelo, `templates/adr-template.md` existe há 3 dias (fingerprint #4 acima) e **nunca é lido**.

```bash
# Trecho relevante
cat > "$FILENAME" <<EOF
# $TITLE

**Status**: Proposed
**Date**: $TODAY
**Deciders**: [names or roles involved]

## Context
...
EOF
```

**Por que importa:**
- Anti-pattern de "dois templates" — divergência inevitável quando alguém atualizar um sem o outro.
- O fingerprint `flow-no-adr-command-despite-script` (2026-05-11, ✅) propôs criar `/devteam:adr` que delega ao script. Foi feito. Mas o script ainda não consume o template físico.
- Manutenção do template ADR exige editar `.sh` (programadores) em vez de `.md` (escritores) — fricção desnecessária.

**Impacto positivo:** transformar o heredoc em `cat "$INSTALL_DIR/templates/adr-template.md" | sed "s/{{TITLE}}/$TITLE/; s/{{DATE}}/$TODAY/" > "$FILENAME"`. Reduz script para ~30 linhas. Template editável em markdown puro.

**Impacto negativo:** dependência runtime do arquivo (mitigável por fallback heredoc).

---

## 8. `ref-frontmatter-allowed-tools-key-mention-in-claude-md-but-not-enforced-by-agent-lint` — LOW

**Arquivos:**
- `CLAUDE.md:117` — `> Note: \`allowed-tools:\` is **not** a standard frontmatter key for skills in this repo. Use only \`name\` and \`description\`. The \`allowed-tools:\` key in \`skills/shared/worktree/SKILL.md\` was an experiment and has been removed.`
- `scripts/agent-lint.sh` (185 linhas) — valida frontmatter de agents e SKILL.md, mas grep mostra **zero** menção a `allowed-tools`.

**Observação:** a regra está documentada em CLAUDE.md mas sem enforcement. Qualquer skill nova pode reintroduzir `allowed-tools:` sem ser pega pelo lint. A nota explicativa sobre experimento removido (`skills/shared/worktree/SKILL.md`) é apenas histórica — não ativa.

**Por que importa:**
- Regras documentadas sem enforcement caem em desuso (anti-pattern "rule on paper").
- Mesma classe de problema do fingerprint `flow-quiz-first-rule-no-lint-validation` (2026-05-14, ✅ implementado para quiz-first; mas allowed-tools ficou de fora).

**Impacto positivo:** adicionar 3 linhas em `scripts/agent-lint.sh`:

```bash
for skill in $(find skills -name SKILL.md); do
  if grep -q "^allowed-tools:" "$skill"; then
    echo "ERR: $skill has non-standard 'allowed-tools:' key (use only 'name' and 'description')"
    EXIT_CODE=1
  fi
done
```

**Impacto negativo:** falso positivo se algum experimento futuro precisar de chave extra; mitigável com allowlist explícita no script.

---

## 9. `ref-stack-detection-skill-still-orphan-2nd-day-zero-wiring-attempted` — sub-escopo (re-afirmação)

**Arquivo:** `skills/shared/stack-detection/SKILL.md` (36 linhas, commit `4307f31`)

**Observação:** 2ª passada sobre o mesmo achado. Sem mudança em 24h:

```bash
$ grep -rl "stack-detection" agents commands workflows
# (zero hits)
```

Os 4 candidatos canônicos (setup-assistant, software-architect, database-specialist, devops-specialist) continuam com heurística inline divergente. `orphan-skill-scan.sh` continua reportando como ACTION REQUIRED.

**Por que importa repetir:**
- Ciclos de 24h sem ação reforçam que skill criada-órfã não tem owner natural — talvez seja necessário ADR para definir critério ou despriorização explícita.
- Fingerprint anterior é sub-escopo. Este é meta-observação: **regressão para órfão estabilizada**.

**Impacto positivo:** decisão consciente — escrever ADR "stack-detection: wired vs deprecated"; OU wirar imediatamente em pelo menos 1 agent piloto (sugestão: `setup-assistant` por usar detecção em FIRST_RUN).

**Impacto negativo:** ambos caminhos custam ~10 min — adiar não custa nada hoje, mas constrói tech debt.
