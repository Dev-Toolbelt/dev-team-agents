# Dev Team Agents

🇺🇸 [See the English Version](README.md)

Um time global de agentes Claude Code especializados para desenvolvimento de software. Agnóstico a tecnologia, ciente do contexto do projeto e mantido colaborativamente.

---

## O que é isso

Um conjunto de agentes e skills do Claude Code que formam um time completo de desenvolvimento de software. Cada agente tem um papel definido, expertise e integração com workflows. Eles coexistem com as regras do seu projeto — as convenções do projeto sempre prevalecem.

17 agentes cobrem todo o ciclo de desenvolvimento: discovery, design, implementação, quality gates e documentação. → Veja a [Referência de Agentes](docs/agents.pt-BR.md) completa.

---

## Como Instalar

### Pré-requisitos

- **Claude Code** — CLI, app desktop ou extensão de IDE. Instale em [claude.ai/code](https://claude.ai/code).
- **Git** — o instalador usa `git rev-parse` para verificar a raiz do projeto.
- **curl** ou **wget** — utilizado para baixar o tarball de release.

### Instalar (versão mais recente)

Execute a partir da **raiz do seu projeto**:

```bash
curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh | bash
```

Exemplo de output:

```
[dev-team-agents] Fetching latest release...
[dev-team-agents] Installing v1.2.0...
[dev-team-agents] Extracting to .claude/dev-team-agents/
[dev-team-agents] Creating symlinks...
[dev-team-agents] Configuring hooks in .claude/settings.json...

? Which language should agents use when talking to you? (BCP 47 tag, e.g. en, pt-BR, es) [en]:

[dev-team-agents] Done. Installed v1.2.0.
[dev-team-agents] Run: "Help me set up this project with dev-team-agents"
```

### Idioma de preferência

Durante a instalação, o instalador pergunta em qual idioma os agentes devem conversar com você. Documentos (ADRs, changelogs, comentários de código) permanecem sempre em inglês. Atualize a qualquer momento em `.claude/user-data/preferences.json`:

```json
{ "language": "pt-BR" }
```

Valores comuns: `en` · `pt-BR` · `es` · `fr` · `de` · `ja` · `zh-CN`

> **Opções avançadas** — versão específica, atualizações, pin de versão, auto-update, notificações e layout de diretórios: [docs/installation.pt-BR.md](docs/installation.pt-BR.md)

---

## Primeiros Passos

Após instalar, inicie o fluxo de setup dizendo ao Claude:

```
"Ajude-me a configurar este projeto com dev-team-agents"
```

O `setup-assistant` irá:

1. **Detectar** se é um setup inicial ou um refresh de configuração existente — e adaptar o comportamento
2. **Escanear** arquivos existentes (README, CLAUDE.md, manifestos de pacotes, histórico git) e resumir o que encontrou
3. **Perguntar** qual tipo de projeto é este: novo do zero, herdado/inacabado, ou manutenção de sistema em produção
4. **Coletar** configuração em uma única troca: testes necessários, plataforma de CI/CD, provedor de nuvem, issue tracker
5. **Apresentar um plano** para sua aprovação antes de criar ou modificar qualquer coisa
6. **Gerar** documentos de contexto vivos em `.claude/docs/` (stack, arquitetura, padrões de código, índice de backlog) e acrescentar uma seção `## dev-team-agents` ao `CLAUDE.md`
7. **Confirmar** o que foi configurado e indicar o guia de workflow relevante

O setup completo tipicamente leva de 5 a 10 minutos. Rodar novamente em um projeto existente ativa o modo refresh — lê o histórico git desde a última execução e aplica patches apenas nos docs afetados.

---

## Slash Commands

Após a instalação, 22 slash commands ficam disponíveis sob o namespace `/devteam:`. Cada command dispara os agentes corretos e limita automaticamente sua atuação à branch ou worktree atual do git.

| Command | O que faz |
|---------|-----------|
| `/devteam:plan` | Planejamento — software-architect + product-analyst + database-specialist (+ backend/frontend/devops quando relevante) |
| `/devteam:backend` | Implementação backend — backend-developer + database-specialist → backend-test-specialist |
| `/devteam:frontend` | Implementação frontend — frontend-developer + ui-ux-designer → frontend-test-specialist |
| `/devteam:mobile` | Implementação mobile — mobile-developer + ui-ux-designer (quando relevante) |
| `/devteam:fullstack` | Implementação full-stack — times de backend + frontend em paralelo |
| `/devteam:design` | Design UI/UX — ui-ux-designer |
| `/devteam:fix` | Correção de bug — desenvolvedor(es) relevante(s) → test-specialist |
| `/devteam:refactor` | Refatoração — software-architect planeja, desenvolvedor(es) executam |
| `/devteam:architect` | Decisões de arquitetura e ADRs — software-architect |
| `/devteam:review` | Code review — code-reviewer + software-architect + security-specialist |
| `/devteam:qa` | Garantia de qualidade — qa-specialist |
| `/devteam:security` | Auditoria de segurança — security-specialist + software-architect |
| `/devteam:dba` | Trabalho de banco de dados — database-specialist + software-architect |
| `/devteam:devops` | Infraestrutura / CI/CD — devops-specialist |
| `/devteam:tester` | Apenas testes — backend-test-specialist + frontend-test-specialist |
| `/devteam:docs` | Documentação — technical-writer |
| `/devteam:pr` | Pull request — rascunha título + descrição, pede confirmação antes de criar |
| `/devteam:commit` | Commit — lê mudanças staged, agrupa por camada, escreve e executa commits |
| `/devteam:workflow-new` | Workflow completo de novo projeto |
| `/devteam:workflow-maintenance` | Workflow de manutenção / evolução de feature |
| `/devteam:workflow-bugfix` | Workflow completo de correção de bug |
| `/devteam:workflow-inherited` | Workflow de onboarding de projeto herdado |
| `/devteam:workflow-security-patch` | Workflow de aplicação de patch de segurança |

**Exemplos de uso:**

```
/devteam:plan adicionar exportação para PDF no relatório de abastecimento
/devteam:backend implementar o endpoint de exportação PDF
/devteam:review
/devteam:pr draft
```

---

## Como Usar os Agentes

Os agentes são invocados pelo papel no seu prompt para o Claude:

```
"Como o product-analyst, analise este PRD: [documento]"
"Como o software-architect, defina a arquitetura para este projeto."
"Como o backend-developer, implemente [tarefa]"
"Como o code-reviewer, revise as mudanças em [arquivos]."
```

Funciona no CLI do Claude Code (`claude`), app desktop, app web em [claude.ai/code](https://claude.ai/code) e extensões de IDE (VS Code, JetBrains).

**Cada agente apresenta um plano para aprovação antes de executar qualquer coisa.** Você revisa, ajusta e aprova — depois a execução começa.

---

## Workflows

| Workflow | Command | Use quando |
|----------|---------|------------|
| Novo projeto | `/devteam:workflow-new` | Começando do zero |
| Projeto herdado | `/devteam:workflow-inherited` | Assumindo trabalho inacabado |
| Manutenção | `/devteam:workflow-maintenance` | Projeto em produção, tarefas contínuas |
| Correção de bug | `/devteam:workflow-bugfix` | Bug isolado |
| Patch de segurança | `/devteam:workflow-security-patch` | Vulnerabilidade de segurança |
| Refatoração | `/devteam:refactor` | Reestruturação planejada de código |
| Revisão de código | `/devteam:review` | Revisão de PR antes do merge |

Guias passo a passo completos estão no diretório [`workflows/`](workflows/).

---

## Commitando a Instalação

Como o `install.sh` baixa um tarball (não faz git clone), `.claude/dev-team-agents/` não tem pasta `.git` aninhada. **Commite diretamente** para que todo o time receba os agentes no `git pull`:

```bash
git add .claude/dev-team-agents/ .claude/agents/ .claude/skills/ .claude/commands/ .claude/settings.json
git commit -m "chore: add dev-team-agents"
```

---

## Isolamento com Worktree

Todos os agentes de codificação perguntam uma única vez antes de editar qualquer arquivo:

> "Do you want this task isolated in a git worktree? [y/N]"

A resposta é compartilhada entre todos os agentes da mesma task via `.claude/.worktree-session` — workflows com múltiplos agentes perguntam exatamente uma vez. No "sim", o agente cria `.worktrees/<ctx>/<title>/` e todo o trabalho ocorre dentro dele. No "não", os agentes trabalham na branch corrente.

---

## Memória dos Agentes

Agentes iniciam cada sessão sem memória das anteriores. Três mecanismos minimizam a perda de contexto:

- **Resumo de sessão** — ao final de qualquer sessão com arquivos alterados, os agentes escrevem uma entrada em `.claude/user-data/session-summary.md`. Um hook `Stop` enforça isso automaticamente.
- **ADRs** — decisões significativas e difíceis de reverter são registradas como Architecture Decision Records em `.claude/docs/development/adrs/`. Crie um com: `bash .claude/dev-team-agents/scripts/new-adr.sh "título"`
- **Project context skill** — define a ordem de carregamento de contexto que todo agente segue no startup, incluindo o resumo de sessão e o índice de ADRs.

---

## Coexistência & Customização

Dev Team Agents é uma **camada base**. As convenções do seu projeto sempre têm precedência: `CLAUDE.md` → `AGENTS.md` → `.agents/<agent-name>.md`. Se seu projeto diz usar tabs, os agentes usam tabs.

**Não** modifique arquivos dentro de `.claude/dev-team-agents/` — eles são sobrescritos na atualização. Faça o override no nível do projeto:

```bash
.agents/backend-developer.md          # override por agente
CLAUDE.md                             # regras globais para todos os agentes
.claude/docs/development/code-standards.md  # padrões de código usados pelos reviewers
```

---

## Solução de Problemas

**Agentes não são reconhecidos pelo Claude** — verifique se o symlink existe: `ls .claude/agents/dev-team/`. Se faltando, rode o instalador novamente a partir da raiz do projeto.

**Skills não são carregadas** — verifique se `.claude/skills/` contém symlinks. Rode o instalador para restaurar links quebrados.

**Hook de verificação de atualização dispara a cada tool call** — verifique se `.claude/user-data/.last-update-check` é um arquivo gravável (não um diretório) e se `scripts/hooks/pre-tool-use/01-check-updates.sh` é executável.

**O `setup-assistant` rodou, mas a seção `## dev-team-agents` está ausente do CLAUDE.md** — diga ao Claude: `"Como o setup-assistant, a seção dev-team-agents está faltando no CLAUDE.md — por favor adicione-a."`

**Um agente executou sem apresentar um plano primeiro** — verifique seu CLAUDE.md de projeto por alguma instrução que conflita com o plan mode.

---

## Contribuindo

1. Faça um fork do repositório
2. Crie uma branch: `fix/agent-name-improvement` ou `feat/new-skill`
3. Siga os padrões de autoria em `CLAUDE.md`
4. Abra um PR com uma descrição clara do que mudou e por quê

---

## Licença

MIT
