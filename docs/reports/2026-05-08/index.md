# Relatório de Auditoria — `dev-team-agents`

**Data:** 2026-05-08
**Escopo:** Terceira passada — vetores não cobertos em 2026-05-06 (auditoria inicial) e 2026-05-07 (segunda passada).
**Autor:** Tarefa agendada (execução autônoma)
**Tipo:** Auditoria temática — scripts duplicados, gaps em workflows, cobertura assimétrica de skills, novos vetores de economia de tokens, gaps de automação.
**Estratégia anti-repetição:** Os 47 fingerprints publicados em 2026-05-06 (22) + 2026-05-07 (25) foram **excluídos da geração**. Cada sugestão deste relatório recebe um fingerprint **novo**, registrado em [`docs/reports/_index.md`](../_index.md). Esta passada acrescenta **28 fingerprints inéditos**, totalizando 75 acumulados.

---

## Seções

- [1. Referências e Consistência (Scripts, CLAUDE.md, Templates, Dogfooding)](01-referencias-e-consistencia.md)
- [2. Fluxos e Workflows (ADR, Session-Summary, Comando × Doc, Numeração)](02-fluxos-e-workflows.md)
- [3. Agentes e Skills (Cobertura ADR, Modelo do technical-writer, Trackers)](03-agentes-e-skills.md)
- [4. Economia de Tokens (Worktree Block, REST inline, SonarQube redundante)](04-economia-tokens.md)
- [5. Automação e Dogfooding (Validadores Faltantes, Self-Eat)](05-automacao-e-dogfooding.md)

---

## Sumário Executivo

A primeira passada (2026-05-06) cobriu o panorama macro. A segunda (2026-05-07) mergulhou em camadas mais profundas — comandos, robustez de scripts, modelos de agente. **Esta terceira passada** identifica três classes de problema novas:

1. **Código morto e duplicação silenciosa** — `scripts/check-updates.sh` é uma versão obsoleta de `scripts/hooks/pre-tool-use/01-check-updates.sh` que ainda é referenciada por `CLAUDE.md` e `commands/update.md`. Os dois scripts já divergiram (a versão obsoleta não tem auto-update). O fluxo `/devteam:update` declarado no `CLAUDE.md` não corresponde ao que `update.sh --check` realmente faz hoje.

2. **Workflows não reforçam regras globais que existem em outros lugares** — `CLAUDE.md` declara obrigatoriedade de session-summary e gatilho de ADR, mas **nenhum dos 5 workflows** menciona qualquer um dos dois. `workflows/bug-fix.md` exige diagnose pelo `software-architect`, mas `commands/fix.md` (o slash command equivalente) pula o agente. `maintenance.md` tem fases numeradas inconsistentes (`Step 1, Step 2, Phase 2, Phase 3`).

3. **Dogfooding assimétrico** — o instalador empurra para projetos clientes um `.claude/settings.json` rico (PreToolUse + Stop dispatchers), mas o próprio repositório `dev-team-agents` registra apenas `orphan-skill-scan.sh` como Stop hook. Quem desenvolve as regras nunca dispara o `01-session-summary.sh` em casa.

A descoberta de **maior impacto operacional** é o conjunto worktree-block + REST conventions + sonarqube-detection — três fontes de duplicação de prosa que somam **~200 linhas** distribuídas em 7–10 agentes. A skill `worktree`, a skill `api-design` e a skill `project-context` (com extensão para detecção de scanners) já existem como destinos canônicos; o trabalho é só de migração.

---

## Lista Priorizada de Ações (Hoje)

| Prioridade | Sugestão | Esforço | Impacto |
|------------|----------|---------|---------|
| P0 | Remover/transformar em shim `scripts/check-updates.sh` e atualizar `commands/update.md` + `CLAUDE.md` | Baixo | Alto (elimina divergência) |
| P0 | Ativar dispatcher canônico de Stop hook no `.claude/settings.json` deste repo | Baixo | Alto (dogfooding) |
| P1 | Substituir bloco `Worktree Isolation` em 7 agentes por `Load skills/shared/worktree/SKILL.md` | Médio | Alto (~140 linhas) |
| P1 | Mover REST conventions de `backend-developer` para `skills/architecture/api-design/SKILL.md` | Médio | Médio (~35 linhas) |
| P1 | Adicionar passo de session-summary e ADR-trigger em todos os workflows | Médio | Alto (alinha workflows com `CLAUDE.md`) |
| P1 | Migrar `technical-writer` de Haiku para Sonnet | Baixo | Médio (qualidade dos docs) |
| P2 | Alinhar `commands/fix.md` com `workflows/bug-fix.md` (incluir software-architect) ou documentar a divergência | Baixo | Médio |
| P2 | Adicionar load `adr` skill em backend/database/devops/security developers | Baixo | Médio |
| P2 | Renomear fases inconsistentes em `maintenance.md` | Baixo | Baixo |
| P2 | Adicionar passo explícito `database-specialist` em `new-project.md` Phase 3 | Baixo | Médio |
| P3 | Centralizar detecção de SonarQube em `project-context` (manter "When loaded" em cada agente) | Médio | Médio |
| P3 | Resolver duplicação `templates/plan-template.md` × `skills/shared/plan-mode/SKILL.md` | Baixo | Baixo |
| P3 | Documentar `docs/audit/` no `CLAUDE.md` § User Data Directory | Baixo | Baixo |
| P3 | Adicionar checagens automáticas: unicidade de skill name, unicidade de fingerprint | Baixo | Médio (preventivo) |
| P3 | Adicionar passo de rollback/deploy-failure em workflows | Baixo | Médio |

---

## Conclusão

O projeto continua maduro. **Não há defeitos críticos.** O padrão das três passadas é coerente: 2026-05-06 levantou higiene de surface; 2026-05-07 atacou robustez de runtime; 2026-05-08 aborda **drift de manutenção** — pontos onde o código já evoluiu mas a documentação, comandos e dogfood não acompanharam.

A política de fingerprints continua funcionando: das **28 sugestões** levantadas hoje, **nenhuma** sobrepõe os 47 fingerprints já registrados em 2026-05-06 e 2026-05-07. A taxa de novo/total continua próxima de 100%.

Próxima execução agendada: **2026-05-09**, consultando `_index.md` com **75 fingerprints** registrados (47 anteriores + 28 desta passada).

---

## Estatísticas da Passada

| Métrica | Valor |
|---------|-------|
| Fingerprints novos | **28** |
| Cumulative (2026-05-06 + -07 + -08) | **75** |
| Reports estruturados | **5** |
| Linhas de prosa duplicada identificadas para remoção | **~200** |
| Scripts redundantes | **1** (`check-updates.sh`) |
| Gaps de doc identificados em CLAUDE.md | **3** (update flow, audit folder, templates structure) |

---

**Próxima execução agendada:** 2026-05-09 (consultará `_index.md` com 74+ fingerprints registrados — 22 + 25 + 27).
