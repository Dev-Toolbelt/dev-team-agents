# Índice de Sugestões — Histórico Acumulado

Este arquivo é o **banco de fingerprints de sugestões já realizadas** nos relatórios diários
de auditoria do projeto `dev-team-agents`. Ele garante que cada relatório novo entregue
**sugestões originais**, sem repetir recomendações de dias anteriores.

---

## Como Funciona

1. Cada sugestão recebe um **fingerprint** curto (slug, em `kebab-case`) descrevendo o tema.
2. Antes de gerar um relatório novo, o agendador (ou agente) **lê este índice** e exclui
   da geração qualquer fingerprint já registrado.
3. Após publicar o relatório do dia, **as novas fingerprints são acrescentadas** abaixo,
   junto com o link para o relatório de origem.
4. Se um tema crítico exigir reforço, ele pode ser repropos­to com escopo **mais específico**
   (ex.: `token-efficiency-context-loading` é diferente de `token-efficiency-tool-output`).

> Estratégia de evolução: o índice cresce indefinidamente, mas pode ser **rotacionado** a
> cada 90 dias movendo entradas antigas para `_index-archive-YYYY-Q.md`.

---

## Convenção de Fingerprints

| Categoria | Prefixo | Exemplo |
|-----------|---------|---------|
| Documentação fora de sincronia | `docs-sync-*` | `docs-sync-readme-skills-list` |
| Referências quebradas / órfãs | `ref-*` | `ref-agent-creator-location` |
| Melhoria de fluxo / workflow | `flow-*` | `flow-bugfix-parallel-marker` |
| Melhoria em agente | `agent-*` | `agent-setup-assistant-size` |
| Melhoria em skill | `skill-*` | `skill-security-add-incident-response` |
| Economia de tokens | `token-*` | `token-context-loading-dedup` |
| Automação / scripts / hooks | `auto-*` | `auto-skill-frontmatter-validator` |
| Governança / política | `gov-*` | `gov-orphan-scan-redundancy` |

---

## Fingerprints Registrados

<!--
  Formato de cada linha:
    - `<fingerprint>` — `YYYY-MM-DD` — _título-curto_ — [relatório](caminho)
  Mantenha em ordem cronológica decrescente (mais recente primeiro).
-->

### 2026-05-06 — `relatorio-auditoria-inicial.md`

- `docs-sync-readme-architecture-skills` — README lista apenas 5 skills de architecture; existem 11 — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `docs-sync-readme-devops-skills` — README omite `graphify-setup`, `vercel`, `sentry`, `sonarqube` da seção de estrutura — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `docs-sync-readme-design-skills` — README descreve apenas `design-system-audit`; existem três skills de design — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `ref-agent-creator-location` — `agent-creator` mora em `.claude/skills/` enquanto `skill-creator` está em `skills/`; inconsistente — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `flow-fullstack-no-workflow-doc` — Existe o slash command `/devteam:fullstack` mas não há `workflows/fullstack.md` — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `flow-parallel-marker-bugfix` — `bug-fix.md` cita execução paralela em prosa, sem usar a coluna `Par.` do `plan-template` — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `agent-setup-assistant-size` — `setup-assistant.md` tem 404 linhas, ultrapassa o limite ~200 do CLAUDE.md — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `agent-frontend-developer-size` — `frontend-developer.md` tem 331 linhas — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `agent-database-specialist-size` — `database-specialist.md` tem 313 linhas — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `agent-backend-developer-size` — `backend-developer.md` tem 286 linhas — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `skill-add-incident-response` — Falta skill de runbook/incident-response — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `skill-add-feature-flags` — Falta skill de gestão de feature flags — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `skill-add-observability-slo` — Falta skill de observabilidade/SLOs — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `skill-add-load-testing` — Falta skill de load/perf testing — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `token-context-loading-dedup` — Cada agente repete a lista de Foundational Rule, redundante com `project-context` — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `token-skill-mention-redundancy` — "Apply skills/shared/token-efficiency/SKILL.md" repetido em todos os agentes consome tokens sem ganho — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `token-foundational-rule-template` — Substituir 12 itens do Foundational Rule por uma única chamada `Load project-context skill` — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `auto-skill-frontmatter-validator` — Falta validador automático de frontmatter de agente/skill — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `auto-redundant-skill-load-scan` — `orphan-skill-scan` não detecta carregamentos duplicados de skill no mesmo agente — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `gov-readme-pt-br-sync-check` — Falta script para validar sincronia README.md ↔ README.pt-BR.md — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `flow-quality-gate-explicit-par-column` — Workflows poderiam usar `Par.` formal do plan-template em todos os pontos paralelos — [relatório](2026-05-06/relatorio-auditoria-inicial.md)
- `flow-setup-slash-command` — Não existe `/devteam:setup` para invocar `setup-assistant` via slash command — [relatório](2026-05-06/relatorio-auditoria-inicial.md)

---

## Estatísticas

| Data | Sugestões publicadas | Originais (acumulado) |
|------|----------------------|-----------------------|
| 2026-05-06 | 22 | 22 |
