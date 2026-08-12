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
