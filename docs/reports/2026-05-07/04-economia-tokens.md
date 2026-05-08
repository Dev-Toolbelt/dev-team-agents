# 4. Economia de Tokens (Vetores Inéditos)

← [Voltar ao índice](index.md)

A passada de 2026-05-06 cobriu a **deduplicação do Foundational Rule** (16 agentes), a redundância de menção a `token-efficiency` e o trade-off de path-completo vs nome-curto. Esta seção identifica **três vetores totalmente novos** de economia, todos verificáveis empiricamente.

---

## 4.1 Bloco "current working context" repetido em 22 comandos

Cada arquivo em `commands/*.md` que envolve mais de um agente começa com o mesmo bloco (com mínimas variações):

```markdown
Before acting, identify the current working context:
- Run `git branch --show-current` — active branch
- Run `git diff --name-only HEAD` — locally modified files
- Run `git diff --name-only main...HEAD` — all changes in this branch vs main
- Check `.claude/.worktree-session` if present — active worktree

Restrict all analysis and actions to files and changes within this context.
Do NOT review the full codebase — only what changed in this branch/worktree
unless $ARGUMENTS explicitly requests a broader scope.

---
```

São **8 linhas** repetidas em **pelo menos 18 dos 22 comandos** (`plan.md`, `fix.md`, `backend.md`, `frontend.md`, `fullstack.md`, `review.md`, `architect.md`, `dba.md`, `design.md`, `devops.md`, `docs.md`, `pr.md`, `qa.md`, `refactor.md`, `security.md`, `tester.md`, `workflow-bugfix.md`, `workflow-maintenance.md`).

> **Fingerprint:** `token-current-context-block-deduplication`

**Estimativa:** 8 linhas × 18 comandos ≈ **144 linhas redundantes**. Cada vez que um comando é invocado, todo seu conteúdo entra no contexto. Quando o usuário roda 3 comandos em sequência (`/devteam:plan`, `/devteam:backend`, `/devteam:review`), o bloco é carregado **3 vezes** sem necessidade.

**Sugestão de refatoração:** criar `skills/shared/current-context/SKILL.md` (ou expandir `skills/shared/project-context/SKILL.md`) e substituir o bloco em cada comando por uma referência:

```markdown
Apply `skills/shared/current-context/SKILL.md` to identify scope.

---
```

Reduz cada comando em ~7 linhas. Total economizado: **~130 linhas / ~1.6k tokens** por base.

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Economia clara em comandos curtos (proporcionalmente maior) |
| **Positivo** | Quando a regra de detecção de contexto evoluir (ex.: suporte a `jj`/`hg`), edita-se em um único lugar |
| **Negativo** | Comando fica menos auto-contido — depende da skill estar disponível |
| **Negativo** | Se a skill não carregar (orphan), comportamento degrada silenciosamente |

---

## 4.2 Prefixo `.claude/agents/dev-team/` repetido em todas as linhas de spawn

Cada comando que faz spawn referencia agentes com path completo:

```text
- `software-architect` at `.claude/agents/dev-team/software-architect.md`
```

Esse prefixo (`.claude/agents/dev-team/`) é **constante** em todo o repositório (decorrente do symlink criado em `install.sh`). Aparece pelo menos **40+ vezes** somando todos os comandos.

> **Fingerprint:** `token-agent-path-prefix-redundant`

A própria documentação de Claude Code aceita spawn por **nome do agente** (sem path). Comandos poderiam ser reescritos:

```text
- `software-architect` — system design, trade-offs, ADR authoring
```

Economia por linha: ~30 caracteres × 40 ocorrências = ~1.2k caracteres / ~300 tokens. Não é gigante, mas é **gratuito** e melhora legibilidade.

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Comandos ficam mais legíveis, menos visualmente poluídos |
| **Positivo** | Path do install pode mudar no futuro sem quebrar comandos |
| **Negativo** | Perde-se a "navegabilidade" via Cmd+Click no editor (mitigável: o agente já é conhecido por nome) |

---

## 4.3 `project-context.md` poderia detectar Graphify e desviar leituras de README

`skills/shared/project-context/SKILL.md` (213 linhas) instrui agentes a **ler integralmente** README.md, CLAUDE.md, AGENTS.md, e arquivos em `.claude/docs/`. Em projetos grandes ou neste próprio repositório (README = 700 linhas, CLAUDE.md = 349 linhas), isso é **~1050 linhas por sessão** apenas em context-loading inicial.

Entretanto, `skills/devops/graphify-setup/SKILL.md` (265 linhas) descreve uma camada de **navegação por knowledge graph** que evita leituras integrais. **Não há instrução** no `project-context.md` para verificar se Graphify está disponível e desviar leituras para queries de grafo.

> **Fingerprint:** `token-graphify-routing-in-project-context`

**Sugestão:** acrescentar ao `project-context.md`:

```markdown
## Pre-flight: Graphify availability

Before reading large files (README.md > 200 lines, codebase scan, etc.),
check `.claude/user-data/graphify.json`. If present and `enabled: true`:

- Replace full README.md read with `graphify query --topic README`
- Replace full file scans with `graphify query --path <pattern>`
- Read CLAUDE.md and AGENTS.md fully (these are short policy files)
```

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Em projetos com README/codebase grandes, redução pode ser de 10–40% do contexto inicial |
| **Positivo** | Promove adoção de Graphify (que já existe como skill e ainda é subaproveitada) |
| **Negativo** | Adiciona ~10 linhas ao `project-context.md` |
| **Negativo** | Agentes precisam saber operar `graphify query` — ainda não está no `project-context.md`. Se o agente não souber, fallback silencioso para leitura completa |

---

## 4.4 Resumo do `git log --oneline -20` em `project-context` é excessivo

Lendo `skills/shared/project-context/SKILL.md`, há instrução para rodar `git log --oneline -20`. Cada linha de commit consome ~80 caracteres × 20 = **1.6k caracteres / ~400 tokens**.

Para a **maioria das tarefas**, conhecer os **últimos 5–10 commits** é suficiente. `-20` é supérfluo, especialmente quando o agente já vai rodar `git diff main...HEAD` (que mostra mudança real, não histórico).

> **Fingerprint:** `token-git-log-window-overshoot`

**Sugestão:** reduzir para `-10` por padrão, com instrução explícita de ampliar para `-20` apenas em cenário de "investigação histórica" (ex.: bisect, identificar regressão).

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Economia consistente de ~200 tokens em **toda sessão** |
| **Positivo** | Histórico mais focado no recente (mais relevante na maioria dos casos) |
| **Negativo** | Em projetos com muitos commits pequenos por dia, 10 pode pular contexto importante; mitigável com `--since=yesterday` |

---

## 4.5 `setup-assistant.md` (404 linhas) é carregado integralmente — extração de runbook

A passada anterior já levantou o tamanho do `setup-assistant.md`. Esta passada complementa com um **vetor específico de economia**: o agente carrega instruções de **9 issue trackers** (GitHub Issues, Jira, Linear, ClickUp, Trello, Asana, Plane, Shortcut, e none) **sempre**, mesmo quando o usuário escolhe um único.

> **Fingerprint:** `token-setup-assistant-conditional-tracker-loading`

**Sugestão:** transformar essas seções em `skills/integrations/issue-trackers/<nome>/SKILL.md` e fazer carregamento sob demanda **após o usuário responder qual tracker quer usar**. O agente principal ficaria com o roteador (ler resposta → carregar uma única skill).

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | `setup-assistant.md` cai de 404 para ~150 linhas (estimativa) |
| **Positivo** | Cada sessão carrega 1 tracker, não 9 (economia ~80% nesse subbloco) |
| **Negativo** | Precisa criar 8–9 skills novas (manutenção), ainda que cada uma seja pequena |
| **Negativo** | Se o usuário trocar de ideia ("agora quero usar Linear, não Jira"), agente carrega segunda skill e duplica contexto |

---

## 4.6 Resumo de fingerprints novos

| Fingerprint | Tema |
|-------------|------|
| `token-current-context-block-deduplication` | Bloco de detecção de worktree repetido em 18+ comandos |
| `token-agent-path-prefix-redundant` | `.claude/agents/dev-team/` constante em todas as linhas de spawn |
| `token-graphify-routing-in-project-context` | `project-context` não desvia leituras para Graphify quando disponível |
| `token-git-log-window-overshoot` | `git log --oneline -20` excessivo; `-10` cobre 80% dos casos |
| `token-setup-assistant-conditional-tracker-loading` | `setup-assistant` carrega 9 trackers; deveria carregar sob demanda |
