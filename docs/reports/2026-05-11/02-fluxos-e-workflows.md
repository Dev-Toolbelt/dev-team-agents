# Relatório de Fluxos e Workflows — 2026-05-11

**Foco**: gaps em commands/workflows, simetrias quebradas, oportunidades de fluxo end-to-end.
**Originalidade**: todos os fingerprints abaixo são **novos** — não constam em `_index.md` antes desta data.

---

## 1. `flow-command-mobile-md-missing-but-claude-md-claims-it`

**Onde**: `commands/` (arquivo `mobile.md` não existe); CLAUDE.md linha 138.

**Evidência**:

```bash
$ ls commands/mobile.md
ls: cannot access 'commands/mobile.md': No such file or directory

$ grep "devteam:mobile" CLAUDE.md
| `/devteam:mobile` | mobile-developer + ui-ux-designer¹ | Implementing mobile features ...
```

**Severidade**: HIGH (referência quebrada documentada).

**Problema**: o slash command `/devteam:mobile` é anunciado na tabela de "User-Invocable Commands" do CLAUDE.md mas não existe no filesystem. Quando o usuário digitar `/devteam:mobile`, vai falhar com "command not found".

**Impacto positivo de criar `commands/mobile.md`**:
- Promessa pública do CLAUDE.md passa a funcionar.
- Mobile-developer ganha um entry-point reduzindo fricção (vs. ter que pedir "como mobile-developer, …").

**Impacto negativo**:
- Mais um command para manter sincronizado com o agente mobile-developer.

**Mitigação**: criar `commands/mobile.md` espelhando a estrutura de `commands/frontend.md` (spawn mobile-developer + ui-ux-designer¹ condicional).

**Fingerprint**: `flow-command-mobile-md-missing-but-claude-md-claims-it`

---

## 2. `flow-no-workflow-command-shortcuts-for-fullstack-refactor-review`

**Onde**: `commands/workflow-*.md` (5 entradas) vs. `workflows/*.md` (8 arquivos).

**Verificação**:

| Workflow file | Slash command equivalente | Existe? |
|---------------|----------------------------|---------|
| `workflows/bug-fix.md` | `/devteam:workflow-bugfix` | ✓ |
| `workflows/inherited-project.md` | `/devteam:workflow-inherited` | ✓ |
| `workflows/maintenance.md` | `/devteam:workflow-maintenance` | ✓ |
| `workflows/new-project.md` | `/devteam:workflow-new` | ✓ |
| `workflows/security-patch.md` | `/devteam:workflow-security-patch` | ✓ |
| `workflows/fullstack.md` | _(ausente)_ | ✗ |
| `workflows/refactor.md` | _(ausente)_ | ✗ |
| `workflows/review.md` | _(ausente)_ | ✗ |

**Problema**: simetria parcial — workflows mais antigos ganham slash, workflows novos não.

**Comentário**: existe `/devteam:refactor` e `/devteam:review` como **commands** (que operam sobre diff atual), mas isso é semanticamente diferente de **workflow-refactor** (refactor de modo deliberado, com múltiplas fases, descrito em `workflows/refactor.md`).

**Impacto positivo de adicionar**:
- Consistência: todo `workflows/<nome>.md` tem um `commands/workflow-<nome>.md`.
- Usuário não precisa ler README para descobrir como invocar.

**Impacto negativo**:
- Confusão entre `/devteam:refactor` (command) e `/devteam:workflow-refactor` (workflow). Mitigar com docstring clara.

**Mitigação alternativa**: padronizar usando o `commands/workflow-*.md` como **wrapper que faz `cat workflows/<nome>.md` e itera** — assim adicionar um novo workflow não exige escrever 2 arquivos manualmente.

**Fingerprint**: `flow-no-workflow-command-shortcuts-for-fullstack-refactor-review`

---

## 3. `flow-spawn-classifier-only-loaded-by-plan-command`

**Onde**: `commands/plan.md:12` é o único command que carrega `skills/shared/spawn-classifier/SKILL.md`.

**Problema**: a skill `spawn-classifier` define um decision tree para spawn condicional de agents (`backend-developer¹`, `database-specialist¹`, etc.). Vários commands têm spawn condicional:

| Command | Tem agente condicional (`¹`)? | Carrega spawn-classifier? |
|---------|-------------------------------|---------------------------|
| `/devteam:plan` | Sim (3 condicionais) | ✓ |
| `/devteam:backend` | Sim (database-specialist¹) | ✗ |
| `/devteam:frontend` | Sim (ui-ux-designer¹) | ✗ |
| `/devteam:fullstack` | Sim (database¹, ui-ux¹) | ✗ |
| `/devteam:refactor` | Sim (4 condicionais) | ✗ |
| `/devteam:fix` | Sim (3 condicionais) | ✗ |
| `/devteam:review` | Sim (database¹, mobile¹) | ✗ |
| `/devteam:mobile` | Sim (ui-ux-designer¹) | ✗ _(arquivo inexistente)_ |

**Impacto positivo de carregar**:
- Cada command decide condicionais com a mesma lógica.
- Reduz divergência: hoje cada command define inline "quando spawn database" por prosa, e essas redações divergem.

**Impacto negativo**:
- spawn-classifier tem ~30 linhas de tabela; carga em 7 commands adicionais aumenta uso de tokens (~210 linhas-equivalente). _Mitigável: a skill é carregada **on demand** apenas quando $ARGUMENTS é avaliado_.

**Mitigação**: aceitar o trade-off ou inserir um wrapper `current-context + spawn-classifier` único para commands multi-agente.

**Fingerprint**: `flow-spawn-classifier-only-loaded-by-plan-command`

---

## 4. `flow-claude-md-workflows-list-incomplete`

**Onde**: CLAUDE.md "## File Structure" linha 196 (lista skills/), README.md linha 706.

**Problema**: CLAUDE.md menciona apenas os 5 workflows base (bug-fix, inherited-project, maintenance, new-project, security-patch). Os 3 workflows mais recentes (`fullstack.md`, `refactor.md`, `review.md`) existem mas não são listados.

**Impacto positivo**:
- Mantenedor sabe quais workflows existem sem precisar `ls workflows/`.
- Auto-Docs rule é seguida.

**Impacto negativo**:
- 3 linhas adicionais.

**Fingerprint**: `flow-claude-md-workflows-list-incomplete`

---

## 5. `flow-no-pre-spawn-installation-freshness-check`

**Onde**: todos os 23 `commands/*.md`.

**Problema**: nenhum command verifica se a instalação local de `dev-team-agents` está desatualizada antes de spawnar agentes. O update check só roda no `PreToolUse` hook a cada 24h (TTL). Se o usuário ficou 48h+ sem comandos, ele pode rodar `/devteam:plan` invocando agentes com bugs já corrigidos upstream.

**Impacto positivo de adicionar check**:
- Garante que cada execução de command usa a versão mais recente vista pelo hook.
- Reduz suporte a "isso já não foi corrigido na v1.5?".

**Impacto negativo**:
- Cada command faz uma comparação leve adicional (`cat .dev-team-agents/user-data/.installed-version` vs `.latest-known`).
- Pode acrescentar ruído ("aviso: você está em vX.Y.Z; latest é vX.Y.Z+1") em commands curtos.

**Mitigação**: gate: avisar somente se versão local for ≥ 2 minor releases atrás.

**Fingerprint**: `flow-no-pre-spawn-installation-freshness-check`

---

## 6. `flow-commit-command-no-type-check-or-tests-gate`

**Onde**: `commands/commit.md` Steps de lint (linhas 74–81).

**Estado atual**: `commit.md` agora roda pre-commit lint (✓ corretamente verificado em 00-auditoria-guardian). Cobertura atual:

- ESLint, Prettier, phpcs, rubocop, `make lint`, `npm run lint`, `pyproject.toml`/black/ruff.

**Gap**: não roda **type-check** (`tsc --noEmit`, `mypy`, `pyright`, `flow check`) nem **testes** afetados (vitest/jest `--changed`).

**Impacto positivo**:
- Type-check captura quebra de tipos antes do commit — falha mais comum que lint.
- Testes em arquivos mudados detectam regressão local.

**Impacto negativo**:
- `tsc --noEmit` em projetos grandes pode levar 30s+. Pode ser opt-in.
- Testes adicionam minutos; muito intrusivo para commit gate.

**Mitigação**:
- Adicionar type-check **incremental** (`tsc --build --noEmit` com cache).
- Testes ficam fora; mover para `/devteam:pr` ou um command separado.

**Fingerprint**: `flow-commit-command-no-type-check-or-tests-gate`

---

## 7. `flow-refactor-workflow-no-rollback-tag-recommendation`

**Onde**: `workflows/refactor.md`.

**Problema**: refactor é uma das classes de mudança com maior risco de regressão. O workflow tem `## Recovery Paths` mas não recomenda criar um **tag git** antes do refactor (`pre-refactor-<context>-YYYYMMDD`) para servir de ponto de rollback instantâneo via `git reset --hard <tag>`.

**Impacto positivo**:
- Reverter um refactor inteiro vira `git checkout <tag>` (segundos) em vez de `git revert <30 commits>` (minutos + risco).
- Tags são leves e podem ser limpas após N dias via cron/hook.

**Impacto negativo**:
- Mais tags no remoto; pode poluir lista; usuário precisa limpá-las.

**Mitigação**: incluir Step "Tag rollback point" como **opcional** com comando pronto.

**Fingerprint**: `flow-refactor-workflow-no-rollback-tag-recommendation`

---

## 8. `flow-security-patch-no-mttr-tracking`

**Onde**: `workflows/security-patch.md`.

**Problema**: workflow não captura métricas. Em pós-mortem de incidentes de segurança, o time não consegue reconstruir MTTR (Mean Time To Resolution) porque não há ponto de captura de `tempo de início` vs `tempo do deploy do patch`.

**Impacto positivo**:
- Time consegue avaliar performance de resposta ao longo do tempo.
- Métrica pública (em compliance / SOC2 / ISO 27001) sem trabalho extra.

**Impacto negativo**:
- 2 linhas a mais no workflow ("registre `started_at` no início; `deployed_at` ao final no `docs/security/incidents/YYYY-MM-DD.md`").
- Risco de drift se o usuário esquecer um dos dois timestamps.

**Mitigação**: adicionar script `scripts/security-incident.sh start|deployed` que escreve timestamp automaticamente em `incidents/` dir.

**Fingerprint**: `flow-security-patch-no-mttr-tracking`

---

## 9. `flow-no-adr-command-despite-script`

**Onde**: `scripts/new-adr.sh` existe; `commands/adr.md` (e `/devteam:adr`) **não existe**.

**Problema**: criar um ADR exige rodar bash. Em um time de dev-team-agents que usa slash commands quase para tudo (commit, pr, plan, fix, refactor, …), ADR fica como exceção: precisa de bash literal.

**Comparação**:
- `/devteam:commit` → wrapper de `git commit` com features extras.
- `/devteam:adr` → poderia wrapper de `bash scripts/new-adr.sh "$ARGUMENTS"` + spawn software-architect para preencher o template.

**Impacto positivo**:
- Cria ADR vira workflow guiado (LLM preenche a partir do contexto).
- Reduz fricção; ADRs serão escritos mais frequentemente.

**Impacto negativo**:
- Mais um command; mais uma entrada em CLAUDE.md.
- LLM pode escrever ADR genérico se não tiver contexto suficiente. Mitigar exigindo $ARGUMENTS específico.

**Fingerprint**: `flow-no-adr-command-despite-script`

---

## 10. `flow-pr-command-no-draft-mode-flag`

**Onde**: `commands/pr.md`.

**Problema**: `/devteam:pr` cria PR direto (provavelmente "ready for review"). Não há flag para criar como **draft** — útil quando a PR é parcial, em discussão técnica, ou aguarda dependência externa.

**Impacto positivo**:
- Padrão GitHub/GitLab (draft PR) sem precisar editar no UI.
- Permite o time abrir PR cedo (visibilidade) sem disparar reviewers.

**Impacto negativo**:
- Argumento adicional a documentar.

**Mitigação**: adicionar `$ARGUMENTS` flag `draft` que passa `--draft` ao `gh pr create` ou `glab mr create --draft`.

**Fingerprint**: `flow-pr-command-no-draft-mode-flag`

---

## 11. `flow-no-cross-link-between-workflows-still`

**Onde**: `workflows/*.md`.

**Histórico**: item `flow-workflows-no-cross-linking` (2026-05-09, sem marker) ainda não tratado.

**Verificação atual**: dos 8 workflows, **nenhum** referencia outro workflow no corpo principal (exceto a seção Recovery que aponta vagamente para `session-summary.md`).

**Impacto positivo de cross-linkar**:
- `workflows/refactor.md` deveria apontar para `workflows/review.md` no encerramento ("após refactor, rode review").
- `workflows/bug-fix.md` deveria apontar para `workflows/security-patch.md` ("se o bug for vulnerabilidade").
- `workflows/maintenance.md` deveria apontar para `workflows/refactor.md` ("se a feature exige refactor preliminar").

**Impacto negativo**:
- Risco de loops circulares (mitigar com checklist).
- Mais texto.

**Fingerprint**: `flow-no-cross-link-between-workflows-still` (escopo: somente acrescentar 1 linha "Next step" no fim de cada workflow).

---

## 12. `flow-stop-hook-04-notifier-no-gate-runs-every-session`

**Onde**: `scripts/hooks/stop/04-notifier.sh`.

**Verificação**: os sub-scripts `02-orphan-skill-scan.sh` e `03-agent-lint.sh` já são gateados por `git status --porcelain` de `agents/` / `skills/` (verificado nas linhas 3–9 dos dois arquivos). `04-notifier.sh`, porém, é executado em **toda** sessão (sem gate), embora também produza ruído (tip rotativo, warnings) em sessões puramente de leitura.

**Problema**: notifier sempre roda; mesmo em sessões onde o usuário só faz `cat` em um arquivo. Para usuários que mantêm sessões longas, isso significa o mesmo "tip do dia" repetido várias vezes (índice é `(day_of_month - 1) % 15`, então estável dentro do dia).

**Impacto positivo de adicionar gate**:
- Notificação aparece **uma vez por dia** (não a cada Stop).
- Tip ganha peso pelo fato de aparecer raramente.

**Impacto negativo**:
- Usuário pode perder o tip se rodar Claude só uma vez no dia em uma sessão muito curta. _Mitigação_: gate por "rodar se hoje ainda não rodou" via flag em `.dev-team-agents/user-data/.notifier-state` (já existe!).

**Mitigação**: usar `.notifier-state` que já é mantido pelo notifier — comparar `last_shown_date` com `date +%Y-%m-%d` e sair cedo se igual.

**Fingerprint**: `flow-stop-hook-04-notifier-no-gate-runs-every-session`

---

## 13. `flow-discovery-loop-still-no-iteration-cap`

**Onde**: `skills/shared/discovery-mode/SKILL.md`.

**Histórico**: item `flow-discovery-loop-exit-criteria` (2026-05-07, sem marker) sugeriu teto de iterações.

**Verificação 2026-05-11**: skill `discovery-mode` existe e é carregada por `setup-assistant`, `software-architect`, `product-analyst`. Mas ainda não há cap explícito ("após N rodadas, abort com warning").

**Impacto positivo de adicionar cap (e.g., 5 iterações)**:
- Previne loop infinito em projetos onde requisitos são genuinamente nebulosos.
- Força usuário a tomar decisão se o discovery não converge.

**Impacto negativo**:
- Cap pode interromper discovery legítimo em projeto complexo.

**Mitigação**: cap configurável via `preferences.json` (`discovery_max_iterations: 5`).

**Fingerprint**: `flow-discovery-loop-still-no-iteration-cap` (variante mais específica do antigo `flow-discovery-loop-exit-criteria`).

---

## Resumo dos Fingerprints Originais (13)

1. `flow-command-mobile-md-missing-but-claude-md-claims-it` *(HIGH — broken reference)*
2. `flow-no-workflow-command-shortcuts-for-fullstack-refactor-review`
3. `flow-spawn-classifier-only-loaded-by-plan-command`
4. `flow-claude-md-workflows-list-incomplete`
5. `flow-no-pre-spawn-installation-freshness-check`
6. `flow-commit-command-no-type-check-or-tests-gate`
7. `flow-refactor-workflow-no-rollback-tag-recommendation`
8. `flow-security-patch-no-mttr-tracking`
9. `flow-no-adr-command-despite-script`
10. `flow-pr-command-no-draft-mode-flag`
11. `flow-no-cross-link-between-workflows-still`
12. `flow-stop-hook-04-notifier-no-gate-runs-every-session`
13. `flow-discovery-loop-still-no-iteration-cap`
