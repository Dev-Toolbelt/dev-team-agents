# Eixo D — Agentes e Skills — 2026-08-12

**Baseline:** `HEAD` = `07e0725`

Foco no delta: agente novo `seo-specialist`, 11 skills novas, e o crescimento de skills existentes
(`orchestration` +219, `setup-health-check/references/checks-list.md` +436).

## Observações (sem violação)

- **Tabelas de detecção por-papel não são duplicação de regra.** As skills novas `ingestion-api`,
  `sse-streaming`, `resilience`, `data-fetching-integrity` são carregadas por 2–4 agentes cada, mas
  cada agente traz um **gatilho de detecção específico do seu papel** (arquiteto: "designing an
  inbound data boundary"; backend: sinais `ingest`/`webhook`/`telemetry`; database: "idempotency
  keys, dedupe constraints, DLQ tables"). A **regra** vive na skill; os agentes só roteiam. Esse é o
  padrão canônico do repo, não uma regra duplicada pedindo casa única.
- **Tamanhos sob controle.** Nenhuma skill nova excede 500 linhas (maior: `tool-installers` = 174).
  `orchestration/SKILL.md` cresceu para 357 mas segue sob o teto. `checks-list.md` tem 665 linhas,
  porém está em `references/` (isento do teto por design) e é carregado sob demanda por
  `/devteam:health-check`.
- **`agent-lint.sh` limpo** cobre frontmatter, drift `tiers.json↔model↔run-banner`, identidade de
  skill e roster de orquestração — todos verdes, incluindo o agente novo `seo-specialist`.

## Achado

**Nenhum achado original neste eixo.** As maiores dívidas de agentes/skills conhecidas
(`skill-shared-migration-v1-to-v2` 438 linhas, `token-foundational-rule` duplicada) já estão no banco;
a de migração foi revalidada aberta na Fase 1b. O delta adicionou superfície nova sem introduzir
duplicação de regra nem estouro de limite.

---

# Pass incremental — 2026-08-12 (2ª execução), baseline `3fbe371`

Superfície do delta neste eixo: `agents/setup-assistant.md` (1 linha alterada — Step 7 passou de
"three entries" para "four entries" no `.gitignore`) e `skills/shared/user-preferences/SKILL.md`
(2 linhas — a nova chave no schema e na tabela de campos). Nenhuma skill criada, removida ou
movida; nenhuma regra nova candidata a casa canônica.

Gates de tamanho e identidade em `3fbe371`: `size-limits: clean ✓` · `agent-lint: clean ✓` —
nenhum agente acima de 205 linhas, nenhum comando acima de 200, nenhuma skill acima de 500,
`name:` == basename em todas, sem duplicata entre categorias.

Os dois espelhos de documentação exigidos pela regra de `preferences.json` que **pertencem a este
eixo** foram atualizados corretamente no mesmo commit (`4734882`):
`skills/shared/user-preferences/SKILL.md:40` (schema) e `:70` (tabela de campos). O espelho que
**não** foi atualizado é o heredoc do `install.sh`, reportado no Eixo C.

**Nenhum achado original neste eixo.**
