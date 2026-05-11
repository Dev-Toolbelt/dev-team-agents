# Relatório de Auditoria — `dev-team-agents`

**Data:** 2026-05-10

**Escopo:** Quinta passada — vetores não cobertos em 2026-05-06 (auditoria inicial), 2026-05-07 (robustez de comandos), 2026-05-08 (drift de manutenção) e 2026-05-09 (governance + cobertura estratégica).

**Autor:** Tarefa agendada (execução autônoma)

**Tipo:** Auditoria temática — *drift entre `CLAUDE.md` e arquivos materiais*, *gaps de community files (PR template, SECURITY, CONTRIBUTING, CHANGELOG)*, *cobertura limitada de eventos de hook*, *recovery/rollback ausente em commands*, *skills extraídas mas inline mantido*, *cobertura per-engine ainda monolítica*.

**Estratégia anti-repetição:** Os 110 fingerprints publicados em 2026-05-06 (22) + 2026-05-07 (25) + 2026-05-08 (28) + 2026-05-09 (35) foram **excluídos da geração**. Cada sugestão deste relatório recebe um fingerprint **novo**, registrado em [`docs/reports/_index.md`](../_index.md).

---

## Seções

- [1. Referências e Consistência (Drift CLAUDE.md ↔ arquivos, community files, frontmatter inconsistente em skills)](01-referencias-e-consistencia.md)
- [2. Fluxos e Workflows (Hook events não cobertos, rollback, pre-commit, stale branches)](02-fluxos-e-workflows.md)
- [3. Agentes e Skills (Per-engine database, event-driven, rate-limiting, performance budgets, Diátaxis)](03-agentes-e-skills.md)
- [4. Economia de Tokens (Skills extraídas com inline mantido, current-context não consumido, install allowlist)](04-economia-tokens.md)

---

## Sumário Executivo

As quatro passadas anteriores mapearam, sucessivamente: hygiene de superfície (06), robustez em runtime (07), drift entre código e docs (08) e governance + skills estratégicas ausentes (09). **Esta quinta passada identifica quatro classes ainda não cobertas:**

1. **Drift entre `CLAUDE.md` e arquivos materiais** — `CLAUDE.md` declara que skills como `current-context` são consumidas por "todos os `/devteam:*` commands"; auditoria mostra que **0 dos 22 commands** carregam essa skill — todos inlinearam o bloco `git branch --show-current`/`git diff` em prosa. O mesmo padrão se repete com `spawn-classifier` (declarada para `/devteam:plan`; carregada apenas por `software-architect`). A declaração na documentação não está conectada ao comportamento real.

2. **Community files ausentes em repositório público com instalador via `curl | bash`** — desde 2026-05-09 o repo ganhou `LICENSE` e `.github/workflows/ci.yml`; permanece sem `PULL_REQUEST_TEMPLATE.md`, `ISSUE_TEMPLATE/`, `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md` e `CODEOWNERS`. Repositórios distribuídos por `curl | bash` precisam de canal explícito de vulnerability disclosure (`SECURITY.md`).

3. **Cobertura assimétrica de eventos de hook** — o installer registra apenas `PreToolUse` e `Stop` em `.claude/settings.json`. Claude Code suporta pelo menos 5 outros eventos (`SessionStart`, `UserPromptSubmit`, `SubagentStop`, `Notification`, `PreCompact`); nenhum é explorado pelo dev-team-agents. Eventos como `SessionStart` (load project context proativamente) e `UserPromptSubmit` (validar regra de Plan Mode) têm casos de uso natural.

4. **Recovery/rollback ausente em commands críticos** — `/devteam:update` baixa e instala mas não tem `--rollback` para versão anterior, apesar do `install.sh` já preservar `INSTALL_DIR.old.$$` durante o swap atômico. `/devteam:commit` não roda linters/formatters antes do commit (pre-commit gate). Workflows não definem o que fazer se um step intermediário falhar.

A descoberta de **maior impacto operacional** desta passada é o conjunto `current-context` + `spawn-classifier` órfãos do uso pretendido: **a documentação afirma um padrão que o código não materializa**. Aplicar o que `CLAUDE.md` já promete economiza ~150 linhas de prosa inline replicada em 21 commands, mantém um único lugar para evoluir o protocolo de detecção de contexto, e elimina três sugestões prováveis em passadas futuras (mantenedores tendem a repetir o mesmo padrão até que a divergência seja explicitada).

---

## Lista Priorizada de Ações (Hoje)

| Prioridade | Sugestão | Esforço | Impacto |
|------------|----------|---------|---------|
| P0 | Adicionar `SECURITY.md` (vulnerability disclosure) | Baixo | Alto (responsabilidade legal/comunidade) |
| P0 | Wire `current-context` skill em todos os 21 commands (eliminar inline) | Médio | Alto (~150 linhas + drift removido) |
| P0 | Adicionar `CHANGELOG.md` (Keep a Changelog format) | Baixo | Alto (releases têm SemVer mas sem histórico legível) |
| P1 | Wire `spawn-classifier` skill em `commands/plan.md` | Baixo | Médio (alinha com CLAUDE.md) |
| P1 | Criar `.github/PULL_REQUEST_TEMPLATE.md` e `.github/ISSUE_TEMPLATE/` | Médio | Médio (qualidade de contribuições) |
| P1 | Adicionar `CONTRIBUTING.md` (com regras já presentes em CLAUDE.md) | Médio | Médio (separar instruções de Claude × instruções de humanos) |
| P1 | Remover bloco "Reviewer Mindset" inline de `code-reviewer.md` (skill já existe) | Baixo | Médio (~12 linhas + duplo carregamento) |
| P1 | Criar `workflows/fullstack.md` para alinhar com `/devteam:fullstack` | Médio | Médio |
| P1 | Adicionar `/devteam:update --rollback` consumindo `INSTALL_DIR.old.$$` | Médio | Alto (recovery operacional) |
| P2 | Explorar `SessionStart` hook para load proativo de project-context | Médio | Alto (UX) |
| P2 | Padronizar 10 variantes da frase `Apply token-efficiency` em 1 só | Baixo | Baixo (~3 linhas/agente) |
| P2 | Gate `02-orphan-skill-scan.sh` por diff em `agents/`/`skills/` | Baixo | Baixo (CPU; relevante em CI) |
| P2 | Criar skill `architecture/event-driven/` (CQRS, saga, message queue) | Alto | Alto |
| P2 | Criar skill `architecture/rate-limiting/` (token bucket, sliding window) | Médio | Alto |
| P2 | Criar skill `architecture/performance-budgets/` (Web Vitals, bundle size) | Médio | Médio |
| P2 | Documentar ordem do dispatcher `Stop` hook (01/02/03) no CLAUDE.md | Baixo | Baixo |
| P3 | Per-engine skills em `skills/database/<mysql|postgres|mongo|redis>/` | Alto | Médio |
| P3 | Criar skill `shared/diataxis-framework/` extraindo de `technical-writer` | Médio | Médio |
| P3 | Padronizar `allowed-tools:` vs ausência em frontmatter de skills | Baixo | Baixo (consistência) |
| P3 | CI: usar `ludeeus/action-shellcheck` em vez de `apt-get install` | Baixo | Baixo (~10s/run) |
| P3 | `install.sh`: refatorar strip de blocklist → allowlist (whitelist) | Médio | Médio (mais robusto a novos arquivos) |
| P3 | `CLAUDE.md`: fragmentar em `.claude-md/` modular para load on demand | Alto | Médio (longo prazo) |
| P3 | Skill `architecture/api-versioning/` (URL, header, content negotiation) | Médio | Médio |
| P3 | Detectar branch stale (>7 dias sem rebase) em workflows | Baixo | Baixo |

---

## Conclusão

O projeto continua maduro e **sem defeitos críticos**. As duas correções mais recentes (LICENSE e CI desde 09) confirmam que o ciclo de auditoria está sendo absorvido. O padrão das cinco passadas:

- **06** — surface hygiene (docs, sizes, missing skills básicos);
- **07** — robustness em runtime (scripts, comandos, modelos);
- **08** — drift de manutenção (código vs docs vs comandos);
- **09** — governance e cobertura assimétrica (LICENSE, CI, skills domain-strategic, duplicação estrutural);
- **10** — **drift declarativo (CLAUDE.md promete mais do que entrega)**, community files, hook events não explorados, recovery paths ausentes.

A política de fingerprints continua eficaz: das **34 sugestões** levantadas hoje, **nenhuma** sobrepõe os 110 fingerprints já registrados. A taxa de novo/total permanece em ~100%.

Próxima execução agendada: **2026-05-11**, consultando `_index.md` com **144 fingerprints** registrados (110 anteriores + 34 desta passada).

---

## Estatísticas da Passada

| Métrica | Valor |
|---------|-------|
| Fingerprints novos | **34** |
| Cumulative (06+07+08+09+10) | **144** |
| Reports estruturados | **4** |
| Community files identificados como ausentes | **5** (PR template, issue templates, SECURITY, CONTRIBUTING, CHANGELOG) |
| Skills declaradas no CLAUDE.md mas órfãs do uso pretendido | **2** (`current-context`, `spawn-classifier`) |
| Hook events não explorados | **5** (`SessionStart`, `UserPromptSubmit`, `SubagentStop`, `Notification`, `PreCompact`) |
| Skills sugeridas para criação | **5** (`event-driven`, `rate-limiting`, `performance-budgets`, `api-versioning`, `diataxis-framework`) |
| Skills sugeridas para extração de inline | **2** (Reviewer Mindset já extraído mas inline mantido; Diátaxis ainda inline) |
| Linhas de prosa redundante identificadas (current-context inline) | **~150** (21 commands × 7 linhas) |
| Drift entre CLAUDE.md e arquivos reais | **2** padrões distintos |

---

**Próxima execução agendada:** 2026-05-11 (consultará `_index.md` com 144 fingerprints registrados — 22 + 25 + 28 + 35 + 34).
