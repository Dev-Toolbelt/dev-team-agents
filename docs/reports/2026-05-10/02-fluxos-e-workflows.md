# 02 — Fluxos e Workflows

← [Voltar ao índice](index.md) · [← Seção anterior](01-referencias-e-consistencia.md)

**Data:** 2026-05-10
**Escopo:** Quinta passada — eventos de hook não explorados, recovery/rollback ausente em commands críticos, gate de pre-commit, detecção de branch stale, integração com PR templates.
**Anti-repetição:** Os 110 fingerprints publicados em 2026-05-06 / -07 / -08 / -09 foram excluídos. Cada item recebe um fingerprint inédito.

---

## Sumário

A passada anterior (09) documentou que dos 5 workflows existentes, nenhum termina com commit ou PR explícito, nenhum cita comandos `/devteam:*` correspondentes, e tabelas `Par.` são usadas apenas em `bug-fix.md`. Aquela passada também sugeriu criar `workflows/refactor.md` e `workflows/review.md` — verificação mostra que **ambos já existem** desde então (`workflows/refactor.md`, `workflows/review.md`), endereçando dois fingerprints daquela passada.

**Esta passada identifica quatro classes ainda não cobertas:**

1. **Eventos de hook do Claude Code sub-utilizados** — só `PreToolUse` e `Stop` são registrados pelo installer; cinco outros eventos (`SessionStart`, `UserPromptSubmit`, `SubagentStop`, `Notification`, `PreCompact`) têm casos de uso natural para este projeto.

2. **Recovery/rollback ausente em commands críticos** — `/devteam:update` instala mas não tem `--rollback`; workflows não definem o que fazer quando um step intermediário falha; `/devteam:commit` não roda pre-commit gate.

3. **Workflows não dialogam com Git operacional** — nenhum verifica se a branch está stale (>7 dias atrás de main) antes de operar; nenhum verifica conflito potencial com main antes de implementar.

4. **`/devteam:pr` desacoplado de `.github/PULL_REQUEST_TEMPLATE.md`** — o command produz prosa, mas não lê e respeita o template do repositório.

---

## Sugestões

### 1. Apenas 2 de 7+ eventos de hook são explorados

**Fingerprint:** `flow-hook-events-only-pretooluse-and-stop`

**Evidência:**

`scripts/install.sh` (template padrão de `.claude/settings.json`):

```json
{
  "hooks": {
    "PreToolUse": [ ... ],
    "Stop": [ ... ]
  }
}
```

Claude Code suporta os seguintes eventos de hook:

| Evento | Uso natural no dev-team-agents | Status |
|--------|--------------------------------|--------|
| `PreToolUse` | Update check | ✅ Usado |
| `Stop` | Session summary, orphan-scan, agent-lint | ✅ Usado |
| `SessionStart` | Load proativo de `project.md` ou aviso de stale `session-summary.md` | ❌ Não usado |
| `UserPromptSubmit` | Validar Plan Mode antes de Claude começar a executar | ❌ Não usado |
| `SubagentStop` | Append em `session-summary.md` o que o subagente fez (alimenta padrão multi-agent já documentado) | ❌ Não usado |
| `Notification` | Confirmar destrutivas; integração com sistema de alerta | ❌ Não usado |
| `PreCompact` | Antes de compactação, dumpar contexto crítico em `session-summary.md` | ❌ Não usado |

Casos com maior valor:

**`SessionStart`** — hoje cada agente lê `README.md → CLAUDE.md → AGENTS.md → project.md → session-summary.md → settings.json` a cada invocação. Um hook `SessionStart` poderia exibir resumo do projeto + última entry de session-summary uma vez por sessão, evitando que cada agente repita o trabalho.

**`SubagentStop`** — multi-agent é central no projeto (`/devteam:plan` spawn 3-6 agentes em paralelo). Capturar o que cada subagente decidiu, automaticamente, dispensaria a regra atual ("cada agente faz append em session-summary.md").

**`PreCompact`** — sessões longas com vários agentes consomem contexto rapidamente. Antes do auto-compact, dump de "decisões importantes" para session-summary previne perda de contexto.

**Impacto positivo:**
- Centraliza fluxos hoje espalhados como regras nos agentes (cada agente carrega ~10 linhas de "append em session-summary");
- Aproveita capacidade nativa do Claude Code;
- Reduz quantidade de tokens lidos por agente (load de project context vira hook → memo, não read por agente).

**Impacto negativo:**
- Mais surface de hook → mais lugares onde algo pode quebrar silenciosamente;
- Cada hook adicional precisa de equivalente de `agent-lint.sh` para validar comportamento;
- `SessionStart` muito verboso polui início de toda sessão.

**Esforço:** Médio-Alto. Sugestão: começar por `SubagentStop` (alta sinergia com session-summary multi-agent) e `SessionStart` minimalista (apenas warn se `project.md` > 30 dias, que já é regra hoje).

---

### 2. `/devteam:update` não tem path de rollback

**Fingerprint:** `flow-update-command-no-rollback-path`

**Evidência:**

`scripts/install.sh` linhas 138-147:

```bash
if [ -d "$INSTALL_DIR" ]; then
    OLD_INSTALL="${INSTALL_DIR}.old.$$"
    mv "$INSTALL_DIR" "$OLD_INSTALL"
    mv "$EXTRACTED_ROOT" "$INSTALL_DIR"
    rm -rf "$OLD_INSTALL" "$TMP_DIR" || true
```

A instalação preserva temporariamente `$INSTALL_DIR.old.$$` durante o swap, mas **deleta imediatamente** após o segundo `mv` ter sucesso. Não há janela para rollback se o usuário descobrir, dois prompts depois, que a versão nova está com bug.

`/devteam:update` (`commands/update.md`) e `scripts/update.sh` não expõem `--rollback`. O `.installed-version` é sobrescrito sem histórico.

Proposta:

```bash
# install.sh — guardar última versão por 24h antes de descartar
PREVIOUS_DIR="${INSTALL_DIR}.previous"
[ -d "$PREVIOUS_DIR" ] && rm -rf "$PREVIOUS_DIR"
mv "$INSTALL_DIR" "$PREVIOUS_DIR"
mv "$EXTRACTED_ROOT" "$INSTALL_DIR"

# Trim job: na próxima execução, se PREVIOUS_DIR > 7 dias, remover
```

`commands/update.md` adiciona:

```
| `--rollback` | Restore the previously-installed version from .previous |
```

`scripts/update.sh`:

```bash
if [[ "${1:-}" == "--rollback" ]]; then
    PREVIOUS_DIR="${INSTALL_DIR}.previous"
    [ -d "$PREVIOUS_DIR" ] || { echo "No previous version to roll back to."; exit 1; }
    rm -rf "$INSTALL_DIR"
    mv "$PREVIOUS_DIR" "$INSTALL_DIR"
    echo "✓ Rolled back to previous version."
fi
```

**Impacto positivo:**
- Recovery operacional em caso de update problemático;
- Reduz medo de fazer update (mais users em latest);
- Confiança em auto-update (`.auto-update` flag) aumenta.

**Impacto negativo:**
- Disco: ~5-10MB por janela de 7 dias;
- Complica `install.sh` (mais um arquivo gerenciado);
- Versão "previous" não tem `.installed-version` sincronizado para detectar exatamente qual era.

**Esforço:** Médio.

---

### 3. `/devteam:commit` não roda pre-commit gate (linters/formatters)

**Fingerprint:** `flow-commit-no-pre-commit-gate`

**Evidência:**

`commands/commit.md` Steps 1-5 cobrem: detectar padrão, inspecionar staged, agrupar por layer, escrever mensagens, executar. **Não há step que rode linters/formatters/tests rápidos antes do commit.**

Cenário típico: agente faz refactor, comita, push, CI quebra em lint. O ciclo é:
1. Agente comita;
2. Push;
3. CI roda lint, falha;
4. Agente edita, comita "fix(style): apply linter";
5. Repete.

Pre-commit gate elimina o ciclo:

```markdown
## Step 4.5 — Pre-commit gate (before executing commits)

Run quick validations on the staged files:

| Project signal | Command |
|---------------|---------|
| `package.json` with `lint` script | `npm run lint --silent` |
| `composer.json` with `phpcs` | `composer phpcs -- --error-severity=10` |
| `.eslintrc*` | `npx eslint <staged-files>` |
| `.prettierrc*` | `npx prettier --check <staged-files>` |
| `phpcs.xml` | `vendor/bin/phpcs <staged-files>` |
| `pyproject.toml` + `ruff` | `ruff check <staged-files>` |
| Generic: `make lint` | `make lint` |

If any returns non-zero:
- Show the output to the user
- Ask whether to (a) fix and re-stage, (b) commit anyway with `--no-verify`-like intent, (c) abort
- Do NOT auto-fix without explicit user consent
```

Convivência com pre-commit hooks Git (Husky, lefthook, pre-commit framework): se o projeto já tem, **não duplicar** — apenas confiar e deixar o `git commit` rodar o hook.

**Impacto positivo:**
- Reduz ciclo de "commit → CI quebra → commit again";
- Aproxima local de CI;
- Detecta typos óbvios antes de virar PR.

**Impacto negativo:**
- Lentidão (lint pode levar 10-30s em projetos médios);
- Falsos positivos do linter atrasam commits legítimos;
- Se o projeto não tem linter configurado, o step vira no-op silencioso.

**Esforço:** Médio (precisa detectar todas as ferramentas comuns).

---

### 4. Workflows não definem caminho de falha intermediária

**Fingerprint:** `flow-workflows-no-failure-recovery`

**Evidência:** Os 7 workflows (`bug-fix`, `inherited-project`, `maintenance`, `new-project`, `refactor`, `review`, `security-patch`) definem fluxo feliz. Nenhum define o que fazer se:

- **Phase 2 (implementation) falha** — agente diz "não consigo, falta contexto X";
- **Phase 3 (quality gate) retorna [BLOCKING]** repetidamente (loop infinito);
- **Phase 4 (commit) trava** — conflito de merge, hooks rejeitando;
- **User aborta no meio**, depois quer retomar.

Hoje o usuário improvisa. `bug-fix.md` tem uma frase ("Repeat until no [BLOCKING] findings remain") mas sem teto de iterações (similar a `flow-discovery-loop-exit-criteria` da passada 07, mas aqui é o ângulo de **review loop**, não de **discovery loop**).

Proposta: adicionar em cada workflow:

```markdown
## Recovery Paths

| Failure point | Recovery |
|---------------|----------|
| Agent reports insufficient context | Spawn `software-architect` for clarifying questions; user provides info |
| [BLOCKING] findings persist after 3 review cycles | Escalate: re-scope, possibly create ADR for the contested decision |
| Commit/PR blocked by Git state | Run `/devteam:fix git-state` (new command) or manual intervention |
| User aborts mid-workflow | Workflow state lives in `session-summary.md` — resume by re-reading and continuing from last completed CHECKPOINT |
```

**Impacto positivo:**
- Workflows ficam mais robustos a falhas reais;
- Reduz "agora o que faço?" para users;
- session-summary ganha role estrutural (não só log).

**Impacto negativo:**
- Workflows ficam ~15-20 linhas maiores cada;
- Recovery paths podem virar "código morto" se nunca exercitados.

**Esforço:** Médio (replicar padrão em 7 workflows).

---

### 5. `/devteam:pr` não respeita `.github/PULL_REQUEST_TEMPLATE.md`

**Fingerprint:** `flow-pr-command-no-template-file-link`

**Evidência:** `commands/pr.md` (36 linhas) instrui o `technical-writer` a produzir body do PR. Mas:

```bash
$ grep -i "template" commands/pr.md
```

Não há detecção de `.github/PULL_REQUEST_TEMPLATE.md`. Quando o template existir:
- GitHub já preenche automaticamente no Web UI;
- `gh pr create` aceita `--body-file` (e respeita template via `--body $(cat template)`);
- O `technical-writer` deveria **ler** o template do projeto e preencher cada seção, não inventar uma estrutura.

Proposta para `commands/pr.md`:

```markdown
## Step 0 — Detect PR template

If `.github/PULL_REQUEST_TEMPLATE.md` exists:
- Read it
- Use it as scaffold; fill each section with content derived from git diff and recent commits
- Preserve structure exactly (checklist items, headers)

If it doesn't exist:
- Use the default structure (current behavior)
```

**Impacto positivo:**
- Respeita convenção do projeto;
- Reduz "PR mal formatado" em fork-based contributions;
- Auto-fills checklists ("✅ Updated docs" se o diff tocou docs/).

**Impacto negativo:**
- Templates com markdown muito específico (HTML comments, formatação) podem requerer parse complexo;
- Heurística para "preencher seção X" pode errar.

**Esforço:** Baixo-Médio.

---

### 6. Workflows não detectam branch stale antes de operar

**Fingerprint:** `flow-no-stale-branch-detection`

**Evidência:** Nenhum dos 7 workflows roda algo como:

```bash
git fetch origin
git log --oneline main..HEAD     # quantos commits a branch tem
git log --oneline HEAD..main     # quantos commits a branch está atrás
```

Cenário problemático: branch criada há 14 dias, main avançou 50 commits. Usuário pede `/devteam:fix` para corrigir um bug. O agente pode:
- Quebrar (conflito de merge na hora do commit);
- Reescrever código que já foi mudado em main (overwrite);
- Validar contra arquitetura desatualizada.

Sugestão em `skills/shared/current-context/SKILL.md` (que será carregada por todos commands — ver sugestão #1 da seção 01):

```markdown
## Step 2 — Branch freshness check

```bash
git fetch --quiet origin
BEHIND=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo 0)
```

If `BEHIND > 7` (or last `git fetch` > 24h ago):
- Warn the user: "This branch is N commits behind main. Recommended: rebase before continuing."
- Offer: (a) rebase now, (b) continue anyway, (c) abort.
```

**Impacto positivo:**
- Detecta cedo a maior fonte de conflito em workflows;
- Educa user sobre rebase regular;
- Cross-cutting: vale para todos os workflows uma vez.

**Impacto negativo:**
- `git fetch` requer rede; pode falhar offline (mitigado: cair silently se sem rede);
- Pode bloquear workflows legítimos onde a branch está atrasada de propósito (mitigado: opção "continue anyway").

**Esforço:** Baixo (em `current-context` skill) + zero em commands se já carregam a skill.

---

### 7. `setup-assistant` não detecta versão de Docker (`docker compose` vs `docker-compose`)

**Fingerprint:** `flow-setup-no-docker-compose-version-detection`

**Evidência:** `skills/shared/project-context/SKILL.md` linhas 226-245 documentam:

```
**Default behavior when Docker is detected:**
| Task | Command form |
| Run a script or CLI command | `docker compose exec <service> <command>` |
```

Mas usa **apenas** `docker compose` (V2, plugin). Projetos legados usam `docker-compose` (V1, standalone). A detecção em `setup-assistant.md` Step 1 lista `Dockerfile`/`docker-compose*.yml` mas não testa qual binário está disponível.

Comandos como `docker compose exec` falham silenciosamente em V1, gerando erro "unknown command". Detecção mínima:

```bash
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE=""  # not available
fi
```

Registrar resultado em `CLAUDE.md`:

```
DOCKER_COMPOSE: docker compose  # ou docker-compose
```

— para que outros agentes (`backend-developer`, `devops-specialist`) usem a forma correta sem detectar de novo.

**Impacto positivo:**
- Compatibilidade com projetos legados;
- Reduz "command not found" em pipelines híbridos;
- Centraliza detecção.

**Impacto negativo:**
- Pequeno overhead no Step 1 do setup;
- Manter compatibilidade com legado dificulta deprecation futura.

**Esforço:** Baixo.

---

### 8. Workflows não verificam conflito potencial com main antes de implementar

**Fingerprint:** `flow-no-merge-conflict-preflight`

**Evidência:** Nenhum dos workflows roda:

```bash
git merge-tree $(git merge-base HEAD main) HEAD main
# ou
git fetch origin main:main; git merge --no-commit --no-ff main || git merge --abort
```

Cenário: agente vai modificar `src/api/users.controller.ts`. Branch tem ele inalterado, mas em main houve refactor que renomeou para `src/api/v2/users.controller.ts`. O agente edita o arquivo antigo; commit/push funciona; rebase de mãe-PR vai gerar conflito brutal porque o arquivo nem existe mais em main.

Em workflows de fix/refactor, valeria um preflight:

```markdown
## Step 0.5 — Preflight: merge preview

Run silently: `git merge-tree $(git merge-base HEAD main) HEAD main`

If output mentions paths the workflow is about to touch:
- Warn user: "files X, Y will conflict on merge to main; please rebase or
  reconsider the change"
- Offer: (a) rebase first, (b) continue, document risk in plan, (c) abort
```

**Impacto positivo:**
- Detecta conflito antes do trabalho ser feito (não depois);
- Especialmente valioso em projetos com main muito ativo.

**Impacto negativo:**
- Custo computacional do `git merge-tree` em repos grandes;
- Heurística "esse arquivo vai ser tocado" é não-trivial (depende do plano do agente).

**Esforço:** Médio.

---

## Resumo dos Fingerprints

| # | Fingerprint | Categoria | Esforço |
|---|------------|-----------|---------|
| 1 | `flow-hook-events-only-pretooluse-and-stop` | Hook events | Médio-Alto |
| 2 | `flow-update-command-no-rollback-path` | Recovery | Médio |
| 3 | `flow-commit-no-pre-commit-gate` | Quality gate | Médio |
| 4 | `flow-workflows-no-failure-recovery` | Recovery | Médio |
| 5 | `flow-pr-command-no-template-file-link` | Integração com `.github/` | Baixo-Médio |
| 6 | `flow-no-stale-branch-detection` | Git operacional | Baixo |
| 7 | `flow-setup-no-docker-compose-version-detection` | Detecção de ambiente | Baixo |
| 8 | `flow-no-merge-conflict-preflight` | Git operacional | Médio |

---

← [Seção anterior](01-referencias-e-consistencia.md) · [Voltar ao índice](index.md) · [Próxima seção →](03-agentes-e-skills.md)
