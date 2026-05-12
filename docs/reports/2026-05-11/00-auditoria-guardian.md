# Relatório de Auditoria — Verificação de Guardian sobre Items "Executed" do dia 2026-05-10

**Data**: 2026-05-11
**Agente de research**: Auditoria automatizada (scheduled task)
**Modo**: Guardian — verificação cruzada entre marcações `✅ Executed` no `_index.md` e estado real do código
**Escopo**: 34 sugestões publicadas em 2026-05-10 (marcadas como executadas em 2026-05-11)

---

## Resumo Executivo

A passada de 2026-05-11 marcou **31 items como ✅ Executed** e **2 items como ⚠️ Partial**. A verificação confirma que **30 marcações estão corretas**, **1 marcação está incorreta** (foi posteriormente revertida pelo próprio autor no commit `fc57a86`) e **2 partials estão coerentes com o estado atual**. Adicionalmente, **1 partial pode ser promovido** porque mais sub-itens foram concluídos do que o registrado.

| Status original | Verificado | Status correto |
|------------------|------------|---------------|
| ✅ Executed (31) | 30 batem com o código, 1 não bate | precisa correção em `_index.md` |
| ⚠️ Partial (2) | 1 confere; 1 está sub-relatado | promover sub-itens em 1 |

---

## Tabela de Verificação (fingerprint × evidência)

Legenda da coluna **Status real (2026-05-11)**:
- `✅` = implementado conforme descrito
- `⚠️` = parcialmente implementado
- `❌` = NÃO implementado apesar da marcação

| Fingerprint | Marcação | Evidência observada | Status real |
|-------------|---------|---------------------|-------------|
| `ref-current-context-skill-orphaned-from-commands` | ✅ | 21/23 commands carregam `current-context`. `commit.md` e `update.md` deliberadamente não carregam (escopo diferente). | ✅ |
| `ref-spawn-classifier-skill-only-software-architect` | ✅ | `commands/plan.md:12` carrega `spawn-classifier`. | ✅ |
| `ref-no-security-md` | ✅ | `SECURITY.md` existe (2.212 bytes, 2026-05-11 14:09). | ✅ |
| `ref-no-contributing-md` | ✅ | `CONTRIBUTING.md` existe (2.410 bytes). | ✅ |
| `ref-no-changelog-md` | ✅ | `CHANGELOG.md` existe (5.955 bytes), formato Keep-a-Changelog. | ✅ |
| `ref-no-pr-and-issue-templates` | ✅ | `.github/PULL_REQUEST_TEMPLATE.md` + 3 issue templates (`bug_report`, `feature_request`, `skill_request`). | ✅ |
| `ref-no-codeowners-file` | ✅ | `.github/CODEOWNERS` (1.078 bytes). | ✅ |
| `ref-skill-frontmatter-allowed-tools-key-inconsistency` | ✅ | `skills/shared/worktree/SKILL.md` frontmatter contém apenas `name` e `description`; nenhuma skill em `skills/` possui `allowed-tools:`. | ✅ |
| `ref-stop-hook-shim-numbering-undocumented` | ✅ | CLAUDE.md possui tabela "Stop Sub-script Convention" documentando prefixos `01-` a `99-`. | ✅ |
| `flow-hook-events-only-pretooluse-and-stop` | ⚠️ Partial | `scripts/install.sh` injeta agora `SessionStart` + `PreToolUse` + `Stop` (3 de 7+). Hook `session-start.sh` existe (linha de cabeçalho confirma propósito). | ⚠️ |
| **`flow-update-command-no-rollback-path`** | **✅** | **Commit `fc57a86` (`fix(install): remove rollback feature and .previous directory`) REMOVEU explicitamente a feature de rollback. `scripts/update.sh` e `commands/update.md` não contêm `--rollback` nem backup `.previous`.** | **❌** |
| `flow-commit-no-pre-commit-gate` | ✅ | `commands/commit.md` linhas 74–81 contém tabela de detecção (`npm run lint`, `eslint`, `make lint`, `phpcs`, `husky`, `lefthook`, `.pre-commit-config.yaml`). | ✅ |
| `flow-workflows-no-failure-recovery` | ✅ | Todos os 8 workflows possuem seção `## Recovery Paths`. | ✅ |
| `flow-pr-command-no-template-file-link` | ✅ | `commands/pr.md:9` detecta `.github/PULL_REQUEST_TEMPLATE.md`. | ✅ |
| `flow-no-stale-branch-detection` | ✅ | `skills/shared/current-context/SKILL.md:44-54` faz `git rev-list --count HEAD..origin/main` e oferece rebase. | ✅ |
| `flow-setup-no-docker-compose-version-detection` | ✅ | `agents/setup-assistant.md:51-54` faz fallback `docker compose` (V2) → `docker-compose` (V1). | ✅ |
| `agent-database-specialist-no-per-engine-skills` | ⚠️ Partial | Postgres + MySQL + MongoDB criadas. **Adicionalmente**: `skills/database/redis/`, `sqlserver/`, `cassandra/`, `sqlite/` já existem e estão wireadas no `agents/database-specialist.md:60-63`. **Partial pode ser promovido para ✅ no fingerprint do banco** (todas as 7 engines já estão criadas e referenciadas). O split do agente (272+ linhas) é a parte ainda pendente. | ⚠️ (escopo do split do agente continua pendente) |
| `skill-missing-event-driven-architecture` | ✅ | `skills/architecture/event-driven/SKILL.md` existe; carregada por `software-architect` e `backend-developer`. | ✅ |
| `skill-missing-rate-limiting` | ✅ | `skills/architecture/rate-limiting/SKILL.md` existe; carregada por 2 agentes. | ✅ |
| `skill-missing-performance-budgets` | ✅ | `skills/architecture/performance-budgets/SKILL.md` existe; carregada por `frontend-developer` e `code-reviewer`. | ✅ |
| `skill-missing-api-versioning-dedicated` | ✅ | `skills/architecture/api-versioning/SKILL.md` existe; carregada por 3 agentes. | ✅ |
| `skill-diataxis-not-extracted` | ✅ | `skills/shared/diataxis-framework/SKILL.md` existe; carregada por `technical-writer` e `code-reviewer`. | ✅ |
| `skill-discovery-mode-not-loaded-by-setup-assistant` | ✅ | `agents/setup-assistant.md:95` carrega `discovery-mode`. | ✅ |
| `agent-product-analyst-jira-skill-not-loaded-foundational` | ✅ | `agents/product-analyst.md:135-136` detecta e carrega `skills/integrations/jira/SKILL.md`. | ✅ |
| `skill-database-debug-multitenancy-not-loaded-by-database-specialist` | ✅ | `agents/database-specialist.md:43-51` carrega `database-multitenancy` e `database-debug` condicionalmente. | ✅ |
| `token-current-context-skill-vs-21-inline-blocks` | ✅ | Commands não inlineiam o bloco git; carregam a skill. | ✅ |
| `token-reviewer-mindset-extracted-but-inline-kept-with-double-load` | ✅ | Os 3 reviewers possuem apenas a linha `Load skills/shared/reviewer-mindset/...` na seção; bloco inline removido. | ✅ |
| `token-token-efficiency-apply-line-six-variants` | ✅ | 10 agentes possuem a mesma redação canônica (`prefer grep/head over full reads; filter before reading; summarize instead of dumping`). | ✅ |
| `token-install-sh-blocklist-vs-allowlist` | ✅ | `scripts/install.sh:128` declara `KEEP_ROOT=(agents scripts skills workflows templates commands)` (allowlist). | ✅ |
| `token-stop-hook-orphan-scan-unconditional-rerun` | ✅ | `02-orphan-skill-scan.sh:3-9` gate por `git status --porcelain agents/ skills/`. | ✅ |
| `token-ci-shellcheck-no-binary-cache` | ✅ | `.github/workflows/ci.yml` não roda `apt-get install shellcheck`. | ✅ |
| `token-update-check-no-etag-handling` | ✅ | `scripts/hooks/pre-tool-use/01-check-updates.sh:37,70,75,82` manipula `ETAG_FILE`, `If-None-Match` e detecta `304`. | ✅ |

---

## Achado Crítico: `flow-update-command-no-rollback-path`

**Marcação no índice (2026-05-11)**: ✅ Executed
**Estado real**: ❌ NÃO implementado — feature foi explicitamente revertida.

Histórico:
- Commit `4dc27c1` ou anterior (não localizado): possivelmente introduziu uma feature `.previous/` de backup automático em updates.
- Commit `fc57a86` (`Mon May 11 18:56:45 2026 -0300`): **removeu** a feature.
  - Mensagem: _"The .previous backup directory created during updates was left behind after successful installs, polluting the user's workspace. Rollback was rarely needed and the orphaned directory caused confusion."_
  - Diff: `commands/update.md` perdeu 14 linhas; `scripts/update.sh` perdeu 14 linhas; `scripts/install.sh` perdeu 3 linhas.

**Estado atual do código**:
- `scripts/update.sh`: sem `--rollback`, sem cópia `.previous`, sem `trap` que restaure.
- `commands/update.md`: documenta `--enable-auto`, `--disable-auto`, `vX.Y.Z`, mas não `--rollback`.
- `scripts/install.sh:148-156`: faz `rm -rf "$INSTALL_DIR"` e `mv "$EXTRACTED_ROOT" "$INSTALL_DIR"` sem manter backup.

**Recomendação**: corrigir a marcação no `_index.md` de `✅ Executed: 2026-05-11` para `↩️ Reverted: 2026-05-11` (ou status análogo) e mover o fingerprint para a tabela de **decisões deliberadas**, anotando que rollback foi avaliado e descartado pelo time. O fingerprint não deve ser repropos­to.

---

## Achado de Sub-Relato: `agent-database-specialist-no-per-engine-skills`

**Marcação**: ⚠️ Partial (Postgres+MySQL+MongoDB done; Redis/SQL Server/Cassandra/SQLite + split do agente pendentes).

**Estado real**:
- Postgres, MySQL, MongoDB criadas ✓ (já marcadas).
- **Redis, SQL Server, Cassandra, SQLite TAMBÉM já criadas** (`skills/database/{redis,sqlserver,cassandra,sqlite}/SKILL.md` existem) e **wireadas** em `agents/database-specialist.md:60-63`.
- O que ainda falta: split do `database-specialist.md` (252 linhas, ainda dentro do limite ~200 segundo CLAUDE.md mas próximo).

**Recomendação**: dividir o fingerprint em dois sub-itens:
1. `agent-database-specialist-per-engine-skills-done` → ✅ Executed (todas 7 engines).
2. `agent-database-specialist-split-into-router-and-engine-skills` → ainda pendente; pode ser repropos­to.

---

## Conclusões

1. **Marcação `_index.md` precisa de uma correção** (`flow-update-command-no-rollback-path` → ↩️ Reverted) para evitar que o agente de research repropose esse item achando que ainda não foi tocado.
2. **Convenção de status precisa de uma 4ª flag**: hoje o índice tem `✅ Executed`, `⚠️ Partial`, e ausência de marker. Falta `↩️ Reverted` para captures de decisões revertidas, evitando que ressurjam como sugestão.
3. **Estatística**: a tabela `Estatísticas` do `_index.md` (linhas 215–221) registra "**31** ✅ + 2 ⚠️ partial". A verificação confirma 30 ✅, 1 ❌ (Reverted), 2 ⚠️ (sendo um sub-relatado). A linha de 2026-05-10 será atualizada nesta passada.
4. **Nenhuma falsificação intencional**: o item revertido foi marcado Executed antes do revert do mesmo dia (intervalo de horas). É uma falha de timing de marcação, não fraude de registro.

---

## Próximas Verificações Sugeridas

- Para futuras passadas Guardian: cruzar marcações `✅` contra `git log --since="<data-da-marcação>"` para detectar reverts no mesmo dia.
- Adicionar regra ao processo: marcação `✅ Executed` só pode ser feita **após o último commit do dia** que altera os arquivos afetados.
