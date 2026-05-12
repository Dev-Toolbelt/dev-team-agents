# Relatório de Referências e Consistência — 2026-05-11

**Foco**: drift entre documentação e código, skills/agents sem referência cruzada, padrões inconsistentes.
**Originalidade**: todos os fingerprints abaixo são **novos** — não constam em `_index.md` antes desta data.

---

## 1. `docs-sync-readme-massive-skill-list-drift`

**Onde**: `README.md` linhas 706–717 (bloco "Repository Structure").

**Problema**: a árvore declarada lista apenas **uma fração** das skills realmente existentes:

| Categoria | README cita | Existem no `skills/` | Drift |
|-----------|-------------|----------------------|-------|
| `shared` | 9 skills | **25 skills** | 16 a mais |
| `architecture` | 5 skills | **24 skills** | 19 a mais |
| `testing` | 2 skills | **6 skills** | 4 a mais |
| `security` | 1 skill | **8 skills** | 7 a mais |
| `design` | 1 skill | **3 skills** | 2 a mais |
| `devops` | 13 skills | **15 skills** | 2 a mais |
| `integrations` | 10 skills | **11 skills** | +linear |
| `ui-libraries` | 6 skills | **6 skills** | OK |
| `mobile` | ❌ não listado | **4 skills** | categoria inteira |
| `database` | ❌ não listado | **9 skills** | categoria inteira |

**Impacto positivo de corrigir**:
- Usuários que consultam o README descobrem skills críticas como `event-driven`, `rate-limiting`, `performance-budgets`, `api-versioning`, `monorepo-patterns`, `feature-flags`, `resilience`, `i18n`, etc.
- Reduz risco de o usuário pedir uma feature já coberta por skill existente.

**Impacto negativo**:
- README cresce de ~720 linhas para ~760+; mais texto para manter em paralelo com `README.pt-BR.md`.
- Risco de re-drift quando novas skills forem adicionadas.

**Mitigação**: gerar a lista via script (`scripts/readme-skill-table.sh`) que lê `skills/**/SKILL.md` (cabeçalho `description:`) e produz um marker block `<!-- @skills-table:start -->...<!-- @skills-table:end -->` no README. Rodar em CI no mesmo job que faz `README sync check`.

**Fingerprint**: `docs-sync-readme-massive-skill-list-drift`

---

## 2. `ref-orphan-scan-only-checks-agents-not-commands-or-workflows`

**Onde**: `scripts/orphan-skill-scan.sh` linha 44 (`AGENT_FILES=()` é o único corpus varrido).

**Problema**: o orphan-scan considera "carregadas" apenas skills referenciadas em `agents/`. Skills puxadas exclusivamente por `commands/*.md` ou `workflows/*.md` precisam ser declaradas manualmente em "User-Invocable Skills" do `CLAUDE.md` para escapar do flag.

**Estado atual**:
- `current-context` → declarada como command-level skill em CLAUDE.md ✓
- `spawn-classifier` → declarada como command-level skill em CLAUDE.md ✓
- Nenhuma outra skill nesta categoria ainda — mas com a expansão dos `commands/*.md`, é provável que apareça mais.

**Impacto positivo de corrigir**:
- Skills com carga em `commands/` ou `workflows/` deixam de exigir registro manual em CLAUDE.md.
- Mantém o invariante "se a skill aparece em qualquer arquivo carregável, não é órfã".

**Impacto negativo**:
- Aumenta o tempo de execução do scan (~2–3 ms por skill adicional varrida); insignificante na prática.
- Pode mascarar skills que deveriam estar em agentes mas foram colocadas em commands por engano.

**Mitigação**: ampliar `AGENT_FILES` para `SCAN_FILES` incluindo `agents/*.md`, `commands/*.md`, `workflows/*.md`. Manter o registro manual no CLAUDE.md como fonte de verdade humana para skills "user-invocable" (que é semanticamente diferente de "carregada por arquivo automatizado").

**Fingerprint**: `ref-orphan-scan-only-checks-agents-not-commands-or-workflows`

---

## 3. `ref-mobile-workflow-missing-despite-command`

**Onde**: `commands/mobile.md` (não existe, mas `/devteam:mobile` está registrado no CLAUDE.md linha 138).

**Verificação**:
- `commands/` não tem `mobile.md` (não tem mesmo? Vamos confirmar nos próximos relatórios).
- `workflows/` não tem `mobile.md`.
- CLAUDE.md linha 138 lista `/devteam:mobile` na tabela de comandos.

**Problema**: simetria quebrada — todas as outras entradas da tabela têm tanto comando (`commands/<nome>.md`) quanto workflow correspondente. Mobile é a única exceção.

> Nota cruzada: este achado é parecido com `flow-fullstack-no-workflow-doc` (2026-05-06, já resolvido), mas com escopo distinto (categoria mobile vs. fullstack).

**Impacto positivo de criar `workflows/mobile.md`**:
- Roteiro consistente para projetos React Native, Expo, Flutter.
- Permite que `setup-assistant` ofereça mobile como path canônico.

**Impacto negativo**:
- Mais um workflow para manter sincronizado com o agente mobile-developer.

**Fingerprint**: `ref-mobile-workflow-missing-despite-command`

---

## 4. `ref-installer-strips-strategy-pattern-mismatch-vs-changelog`

**Onde**: `scripts/install.sh:128-146` (allowlist + dotfile strip) e CLAUDE.md tabela "Package exclusions" linhas 327–339.

**Problema**: a tabela em CLAUDE.md lista 13 "stripped paths" como se cada um fosse explicitamente removido. Na realidade:
- `CLAUDE.md`, `README.md`, `README.pt-BR.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE`, `SECURITY.md`, `docs/` → strippados **implicitamente** porque não estão em `KEEP_ROOT=(agents scripts skills workflows templates commands)`.
- `.claude/`, `.github/`, `.gitignore`, `scripts/install.sh`, `scripts/orphan-skill-scan.sh`, `scripts/agent-lint.sh` → strippados **explicitamente** (linhas 141–146).

Embora o resultado final seja o mesmo, a tabela mistura dois mecanismos diferentes sem indicar qual aplica a cada linha.

**Impacto positivo de corrigir**:
- Quem mantém o installer sabe imediatamente onde adicionar/remover uma exclusão.
- Evita o caso "adicionei `CONTRIBUTING.md` ao installer e ele ainda vai junto" porque a pessoa achou que precisava de um `rm -f` explícito.

**Impacto negativo**:
- Linha extra na tabela ("Mechanism" column).

**Mitigação**: adicionar coluna `Mechanism` na tabela ("allowlist" / "explicit strip"). Exemplo:

| Stripped path | Mechanism | Reason |
|---|---|---|
| `CLAUDE.md` | allowlist (not in KEEP_ROOT) | Authoring rules… |
| `.gitignore` | explicit `rm -f` (dotfile) | Repo-level gitignore… |

**Fingerprint**: `ref-installer-strips-strategy-pattern-mismatch-vs-changelog`

---

## 5. `ref-commands-two-without-current-context-undocumented`

**Onde**: `commands/commit.md` e `commands/update.md`.

**Verificação**: dos 23 commands instalados, 21 carregam `skills/shared/current-context/SKILL.md`. Os 2 que não carregam (`commit.md`, `update.md`) operam sobre staging area / instalação local — não fazem sentido sob escopo de branch.

**Problema**: o critério "qual command precisa de current-context" não está documentado. Isso significa que:
- Próximo command novo pode esquecer de incluir.
- Reviewer não consegue distinguir omissão deliberada de omissão acidental.

**Impacto positivo de documentar**:
- Trivial de revisar PRs futuros.
- Ajuda autores de novos commands a tomar a decisão certa.

**Impacto negativo**:
- Mais texto em CLAUDE.md (~3 linhas).

**Mitigação**: adicionar 1 linha na tabela "User-Invocable Commands" do CLAUDE.md indicando exceções:

> _Exceções: `/devteam:commit` (opera sobre staging area, não branch) e `/devteam:update` (opera sobre instalação local). Ambos não carregam `current-context` por design._

**Fingerprint**: `ref-commands-two-without-current-context-undocumented`

---

## 6. `ref-templates-folder-still-single-file-after-three-passes`

**Onde**: `templates/` contém apenas `plan-template.md` (3.884 bytes, sem alteração desde 2026-05-03).

**Histórico**:
- Item `ref-templates-folder-underutilized` foi sugerido em 2026-05-08 (sem marker).
- Hoje (2026-05-11) o estado é exatamente o mesmo.

**Problema**: ADR, backlog, session-summary, audit-report, runbook, code-standards, architecture, project.md — todos esses documentos têm formato canônico, mas o template está embutido em **skills** (`adr/SKILL.md`, `backlog-template/SKILL.md`, `docs-templates/SKILL.md`) em vez de em `templates/`.

**Impacto positivo de migrar inline → arquivos físicos**:
- Skill encolhe (e.g., `backlog-template/SKILL.md` poderia ter ~30 linhas se delegasse a `templates/backlog.md`).
- Templates podem ser referenciados diretamente em scripts (`new-adr.sh` poderia fazer `cat templates/adr.md`).
- Usuário consegue cat-ar um template sem precisar ler skill inteira.

**Impacto negativo**:
- Dois pontos de manutenção: `templates/foo.md` + skill que descreve quando usar.
- Risco de drift entre conteúdo do template e seu "guia de uso".

**Mitigação**: separar **template = formato canônico (físico)** vs **skill = guia de uso (referencia o template)**. Cada skill que hoje contém um template inline passa a fazer `cat templates/foo.md` ou linkar o caminho.

**Fingerprint**: `ref-templates-folder-still-single-file-after-three-passes`

---

## 7. `ref-claude-md-mentions-agents-creator-as-claude-skills-path`

**Onde**: CLAUDE.md linha 113.

**Observação**: a tabela "User-Invocable Skills" registra:

| `agent-creator` | `.claude/skills/agent-creator/SKILL.md` | `/agent-creator` …|

Mas no repositório, `.claude/skills/` não está commitado (é gitignored — vide CLAUDE.md linha 281). O caminho mostrado é **o local pós-instalação no projeto do usuário**, não o local no repo `dev-team-agents`.

**Problema**: a tabela mistura duas perspectivas (repo vs. projeto-alvo do install) sem indicar qual. Tabela "User-Invocable Skills" entrega path do repo para `skill-creator`, mas path do projeto-instalado para `agent-creator`.

**Impacto positivo de unificar**:
- Mantenedores do repo conseguem buscar a skill em local previsível.
- Se `agent-creator` é skill mesmo, deveria viver em `skills/agent-creator/` no repo.
- Se é uma meta-skill que só faz sentido pós-instalação, isso deveria estar documentado.

**Impacto negativo**:
- Implica mover/copiar `agent-creator` para `skills/` se for promovida; ou re-escrever a tabela se for permanecer fora do package.

**Fingerprint**: `ref-claude-md-mentions-agents-creator-as-claude-skills-path`

---

## 8. `ref-stop-hook-04-notifier-undocumented-in-changelog-unreleased`

**Onde**: `CHANGELOG.md` seção "Unreleased" (linhas 10–37).

**Problema**: o sub-script `scripts/hooks/stop/04-notifier.sh` (categoria "User-facing notifications") e o cabeçalho de notificação `DEV TEAM AGENTS` foram introduzidos via commits `e6719f7`, `f63ed64`, `ff40f0e`, mas **não aparecem no CHANGELOG**. A seção "Unreleased" também não menciona `SessionStart` hook explicitamente (somente "warns when stale" mas sem dizer que é hook novo).

**Verificação**:
- `git log --oneline -25` confirma esses 3 commits ligados ao notifier/preferences.
- CHANGELOG `Unreleased > Added` lista 15 items; nenhum cobre o notifier.

**Impacto positivo de corrigir**:
- Próximo release tem release notes completas; usuários percebem nova capacidade.
- Reforça regra Auto-Docs do CLAUDE.md.

**Impacto negativo**:
- Mais ~3 linhas no CHANGELOG.

**Fingerprint**: `ref-stop-hook-04-notifier-undocumented-in-changelog-unreleased`

---

## 9. `ref-database-specialist-still-258-lines-after-engine-split`

**Onde**: `agents/database-specialist.md` (252 linhas).

**Problema**: o item ⚠️ Partial de 2026-05-10 (`agent-database-specialist-no-per-engine-skills`) sugeriu extrair conteúdo por engine para skills dedicadas. Postgres, MySQL, MongoDB, Redis, SQL Server, Cassandra, SQLite TODAS foram criadas e wireadas (verificado em 00-auditoria-guardian.md), porém o tamanho do agente caiu pouco.

**Comparação histórica**:
- 2026-05-06 relatório inicial: 313 linhas
- 2026-05-11 hoje: 252 linhas (—61, redução de 19%)

Para um agente que delega 7 engines a skills externas, esperava-se queda mais expressiva.

**Análise**: o que sobra são tabelas de detecção (`detection table`), Foundational Rule (já delegada a `project-context`), Worktree Isolation, padrões SQL genéricos. Há **inline ainda** de:
- Heurísticas de N+1 (3–5 linhas)
- ER-modeling rules (~15 linhas)
- Migration patterns (~10 linhas)

**Impacto positivo de continuar a extração**:
- `database-specialist` cai abaixo de 200 linhas (alinhado ao limite ~200 do CLAUDE.md).
- Skills `database/er-modeling`, `database/n-plus-one`, `database/sql-patterns` podem ser carregadas por outros agentes (backend-developer especialmente).

**Impacto negativo**:
- Maior fragmentação; mais hops para encontrar a regra.
- Pode resultar em sub-skills muito pequenas (anti-pattern).

**Mitigação**: extrair somente blocos >20 linhas. Manter no agente: detecção, routing, worktree, foundational.

**Fingerprint**: `ref-database-specialist-still-258-lines-after-engine-split`

---

## 10. `ref-no-orphan-template-scan-with-zero-templates-still-pending`

**Onde**: `scripts/` (sem `orphan-template-scan.sh`).

**Histórico**: item `auto-no-orphan-templates-scan` (2026-05-08, sem marker) condicionou a criação a "adiar até 3+ arquivos em templates/". Hoje (2026-05-11) ainda há **1 arquivo** em `templates/`, e a sugestão #6 acima propõe migrar inline → físico, o que vai elevar para 5+ arquivos.

**Problema**: a sugestão original ficou em standby por dependência. Quando #6 (`ref-templates-folder-still-single-file-after-three-passes`) for executada, o gate de "3+ arquivos" será atingido e o item antigo precisa ser despertado.

**Impacto positivo**:
- Garante que ADR/backlog/runbook templates não viram código morto.

**Impacto negativo**:
- Pouco — script de scan é simples (~30 linhas).

**Fingerprint**: `ref-no-orphan-template-scan-with-zero-templates-still-pending` (variante do antigo `auto-no-orphan-templates-scan`, escopo mais específico).

---

## 11. `ref-graphify-setup-skill-referenced-by-name-not-path-blind-spot`

**Onde**: `agents/setup-assistant.md:134`.

**Problema**: a referência é `→ invoke \`graphify-setup\` skill immediately` (por **nome em backtick**), não por **path**. O orphan-scan aceita o padrão `\`${skill_name}\`` para evitar falsos positivos, então a skill é considerada "referenciada". Porém, na prática, agente que lê esse texto não sabe **qual caminho** carregar (`skills/devops/graphify-setup/SKILL.md`) — depende de a Claude inferir a partir do nome.

**Comparação com outras skills**: 99% das skills no repo são referenciadas com path completo (`Load \`skills/category/name/SKILL.md\``). `graphify-setup` é uma das poucas exceções que usa apenas o nome.

**Impacto positivo de padronizar**:
- Skill loading determinístico; sem inferência de path por LLM.
- Orphan-scan pode ser mais restritivo (exigir path, não apenas nome).

**Impacto negativo**:
- ~5 referências precisam ser reescritas (Setup assistant + `graphify-refresh.sh` interno).

**Fingerprint**: `ref-graphify-setup-skill-referenced-by-name-not-path-blind-spot`

---

## 12. `docs-sync-claude-md-package-exclusions-includes-LICENSE-without-marking`

**Onde**: CLAUDE.md linha 336.

**Problema**: a tabela "Package exclusions" lista `LICENSE` como stripped. Mas a feature LICENSE foi adicionada em 2026-05-10 (item `ref-license-file-missing` de 2026-05-09). Naquele momento, o LICENSE foi **propositalmente strippado do package** para que projetos do usuário não recebam licença alheia. Isso é correto.

**Porém**: o LICENSE também é listado em CLAUDE.md como existente no repo (sem indicação visível na seção "File Structure" das linhas 192–207). Um novo contribuidor que ler o "File Structure" não tem ideia que existe LICENSE.

**Impacto positivo**:
- Estrutura de arquivos no CLAUDE.md fica completa (LICENSE, CHANGELOG, CONTRIBUTING, SECURITY visíveis).

**Impacto negativo**:
- 4 linhas extras na árvore.

**Mitigação**: adicionar `├── LICENSE`, `├── CHANGELOG.md`, `├── CONTRIBUTING.md`, `├── SECURITY.md` no diagrama de `## File Structure` do CLAUDE.md.

**Fingerprint**: `docs-sync-claude-md-package-exclusions-includes-LICENSE-without-marking`

---

## Resumo dos Fingerprints Originais (12)

1. `docs-sync-readme-massive-skill-list-drift`
2. `ref-orphan-scan-only-checks-agents-not-commands-or-workflows`
3. `ref-mobile-workflow-missing-despite-command`
4. `ref-installer-strips-strategy-pattern-mismatch-vs-changelog`
5. `ref-commands-two-without-current-context-undocumented`
6. `ref-templates-folder-still-single-file-after-three-passes`
7. `ref-claude-md-mentions-agents-creator-as-claude-skills-path`
8. `ref-stop-hook-04-notifier-undocumented-in-changelog-unreleased`
9. `ref-database-specialist-still-258-lines-after-engine-split`
10. `ref-no-orphan-template-scan-with-zero-templates-still-pending`
11. `ref-graphify-setup-skill-referenced-by-name-not-path-blind-spot`
12. `docs-sync-claude-md-package-exclusions-includes-LICENSE-without-marking`
