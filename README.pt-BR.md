# Dev Team Agents

🇺🇸 [See the English Version](README.md)

Um time global de agentes Claude Code especializados para desenvolvimento de software. Agnóstico a tecnologia, ciente do contexto do projeto e mantido colaborativamente.

---

## O que é isso

Um conjunto de agentes e skills do Claude Code que formam um time completo de desenvolvimento de software. Cada agente tem um papel definido, expertise e integração com workflows. Eles coexistem com as regras do seu projeto — as convenções do projeto sempre prevalecem.

17 agentes cobrem todo o ciclo de desenvolvimento: discovery, design, implementação, quality gates e documentação. → Veja a [Referência de Agentes](docs/agents.pt-BR.md) completa.

---

## Como Funciona — Fonte Única, Multi-CLI

Uma fonte canônica de verdade vive neste repositório: `agents/`, `commands/`, `skills/`, `templates/`, `scripts/hooks/`, mais um conjunto pequeno de arquivos JSON de metadados (`scripts/lib/tiers.json`, `tool-map.json`, `command-map.json`, `commands.json`). Nada específico de provedor fica versionado para qualquer CLI.

Um motor de renderização (`scripts/render-provider.sh`, Python puro com só stdlib) lê a fonte canônica e emite a árvore de arquivos esperada por cada CLI. Os instaladores por CLI traduzem o frontmatter dos agentes, prefixam uma curta nota "Convenções de ferramentas" por provedor que mapeia os nomes de ferramenta do Claude Code para as ferramentas nativas daquele CLI, e ligam os hooks de ciclo de vida aos mesmos dispatchers bash em `scripts/hooks/`.

```
                      ┌─────────────────────────────────────────────────────┐
                      │           ESTE REPO (fonte canônica)                 │
                      │     agents/  commands/  skills/  templates/         │
                      │     scripts/hooks/*.sh   (dispatchers bash únicos)  │
                      │     scripts/lib/{tiers, tool-map, command-map,      │
                      │                   commands, preferences}.json       │
                      └──────────────────────────┬──────────────────────────┘
                                                 │
            ┌───────────────────────────────────┴────────────────────────────────────┐
            │                                                                          │
            ▼                                                                          ▼
  ┌───────────────────────────────────┐                            ┌──────────────────────────────┐
  │   scripts/render-provider.sh      │                            │   scripts/install.sh          │
  │   (python3, só stdlib)             │                            │   (instalador do Claude Code) │
  │                                   │                            │   bundle slim para o          │
  │   --provider claude | opencode |  │                            │   .dev-team-agents/   │
  │              codex                 │                            │   do projeto                  │
  └──┬────────────────┬───────────────┘                            └───────────────┬──────────────┘
     │ renderiza      │ renderiza                                                  │ funciona
     ▼                ▼                                                            ▼ direto
  .opencode/          .codex/                                        ┌──────────────────────────────┐
  agents/<n>.md       agents/<n>.toml    ← reshape de frontmatter     │  .claude/                    │
  opencode.json       prompts/devteam-*  ← formato do slash command   │  agents/dev-team/<n>.md      │
  plugins/dev-team-    hooks.json         ← liga os dispatchers bash  │  commands/devteam/<n>.md    │
  agents.ts            skills/ → symlink                              │  skills/<name>/             │
  skills/ → symlink                                                   │  settings.json → hooks/*.sh │
     │                                                                  └──────────────────────────────┘
     │ invocado de um projeto Claude-slim via                            │ tratado pelo caminho Claude
     │                                                                  │ existente — sem bootstrap
     │   bash <(curl -sSL .../install-provider.sh) opencode              │ extra necessário
     │   bash <(curl -sSL .../install-provider.sh) codex
     ▼
  /devteam:plan do a plan          ← UX idêntica entre CLIs (Codex → /prompts:devteam-plan)
```

**Modelo em camadas — três preocupações, mantidas separadas:**

1. **Conhecimento** (skills, prompts de papel dos agentes, prompts de fluxo dos comandos, comportamento dos hooks). Autorado uma vez, versionado neste repo, idêntico entre provedores.
2. **Adaptadores** (formato de frontmatter por provedor, tabela de mapeamento de nomes de ferramenta, formato de saída do slash command). Definidos uma vez por provedor em `scripts/lib/*.json` e renderizados no install time. Adicionar um provedor novo = uma coluna em `tiers.json` + uma linha em `tool-map.json` + uma linha em `command-map.json` + um `install-<provider>.sh` enxuto.
3. **Ligação** (`.claude/settings.json` para Claude, `.opencode/plugins/dev-team-agents.ts` para opencode, `.codex/hooks.json` para Codex). Os três invocam os MESMOS dispatchers em `scripts/hooks/*.sh` — sem duplicação de hooks por provedor.

**Model id por agente é rígido por tier.** Cada agente declara um de `reasoning | backend-exec | frontend | repetitive`. Cada tier é resolvido para um model id concreto via `tiers.json` por provedor, então trocar de provedor é uma mudança de uma coluna — sem editar o corpo de qualquer agente.

> Referência completa: [docs/providers.md](docs/providers.md)

---

## Instalação rápida

| CLI | Comando único | Docs |
|-----|---------------|------|
| **Claude Code** | `curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh \| bash` | [docs/install-claude.md](docs/install-claude.md) |
| **opencode** | `bash <(curl -sSL .../scripts/install-provider.sh) opencode` | [docs/install-opencode.md](docs/install-opencode.md) |
| **Codex CLI** | `bash <(curl -sSL .../scripts/install-provider.sh) codex` | [docs/install-codex.md](docs/install-codex.md) |

Execute o comando a partir da **raiz do seu projeto**. O instalador Claude pergunta o idioma preferido. opencode e Codex CLI **não são empacotados** no slim install do Claude — eles são inicializados sob demanda via `install-provider.sh`.

> Mapa tier → modelo completo, limitações conhecidas e como adicionar um novo provider: [docs/providers.md](docs/providers.md)

Após instalar o Claude, inicie o fluxo de setup:

```
Ajude-me a configurar este projeto com dev-team-agents
```

> **Opções avançadas do Claude** — versão específica, atualização, pin de versão, auto-update, notificações e layout de diretórios: [docs/installation.pt-BR.md](docs/installation.pt-BR.md)

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
6. **Gerar** documentos de contexto vivos em `docs/` (stack, arquitetura, padrões de código, índice de backlog) e acrescentar uma seção `## dev-team-agents` ao `CLAUDE.md`
7. **Confirmar** o que foi configurado e indicar o guia de workflow relevante

O setup completo tipicamente leva de 5 a 10 minutos. Rodar novamente em um projeto existente ativa o modo refresh — lê o histórico git desde a última execução e aplica patches apenas nos docs afetados.

---

## Slash Commands

Após a instalação, os slash commands ficam disponíveis sob o namespace `/devteam:`. Cada command dispara os agentes corretos e limita automaticamente sua atuação à branch ou worktree atual do git.

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
| `/devteam:learn` | Captura de conhecimento — consolida decisões, padrões e descobertas da sessão em docs, wiki e ADRs, e então faz o commit automaticamente (declara o manifesto de commits no plano) |

**Exemplos de uso:**

```
/devteam:plan adicionar exportação para PDF no relatório de abastecimento
/devteam:backend implementar o endpoint de exportação PDF
/devteam:review
/devteam:pr draft
```

---

## Agentes

O time tem **17 agentes** cobrindo todo o ciclo de vida. Detalhes completos na [Referência de Agentes](docs/agents.md).

**Planejamento & arquitetura**

| Agente | O que faz |
|--------|-----------|
| `product-analyst` | Protagonista do planejamento — transforma um pedido em um documento de requisitos **de negócio** fechado, pronto para virar sprints |
| `software-architect` | Design de sistema, trade-offs, contratos de API, padrões de projeto e ADRs |
| `database-specialist` | Modelagem de esquema, migrations e otimização de queries |

**Implementação**

| Agente | O que faz |
|--------|-----------|
| `backend-developer` | Código server-side — APIs, serviços, regras de negócio |
| `frontend-developer` | Código client-side — telas, componentes, fluxos de UI |
| `mobile-developer` | Features mobile — React Native, Expo, Flutter, iOS/Android nativo |
| `ui-ux-designer` | Design system, fluxos de UX e decisões visuais |
| `devops-specialist` | CI/CD, Docker, infraestrutura e scripts de deploy |

**Qualidade & revisão**

| Agente | O que faz |
|--------|-----------|
| `code-reviewer` | Revisor de entrada — roteia para os revisores de backend/frontend e sintetiza um único veredito |
| `backend-reviewer` | Revisão estrutural profunda de mudanças no backend |
| `frontend-reviewer` | Revisão estrutural profunda de mudanças no frontend |
| `qa-specialist` | Valida comportamento do produto, fluxos de usuário e risco de regressão |
| `security-specialist` | Auditorias de segurança, análise de vulnerabilidades, questões OWASP |
| `backend-test-specialist` | Escreve e mantém testes de backend |
| `frontend-test-specialist` | Escreve e mantém testes de frontend |

**Habilitação**

| Agente | O que faz |
|--------|-----------|
| `technical-writer` | Docs, changelogs, runbooks, release notes e descrições de PR |
| `setup-assistant` | Configura o dev-team-agents para um projeto e roda health checks |

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

## Tarefas Comuns

Escolha o command que corresponde ao seu objetivo — o tratamento de ciclo de vida (novo projeto, correção de bug, manutenção, código herdado, patch de segurança) agora está embutido nos agentes, sem necessidade de um command de workflow separado.

| Objetivo | Command |
|----------|---------|
| Planejar uma feature / novo projeto | `/devteam:plan` |
| Corrigir um bug | `/devteam:fix` |
| Refatorar | `/devteam:refactor` |
| Auditoria / patch de segurança | `/devteam:security` |
| Decisão de arquitetura, mudança em código herdado/manutenção | `/devteam:architect` |
| Revisão de código antes do merge | `/devteam:review` |

Cada preocupação específica de escopo (design, fullstack, mobile, refactor, review) é tratada pelo seu command dedicado `/devteam:<scope>`, que delega para o agente certo — sem diretório de workflows separado.

---

## Commitando a Instalação

Como o `install.sh` baixa um tarball (não faz git clone), `.dev-team-agents/` não tem pasta `.git` aninhada. **Commite diretamente** para que todo o time receba os agentes no `git pull`:

```bash
git add .dev-team-agents/ .claude/agents/ .claude/skills/ .claude/commands/ .claude/settings.json
git commit -m "chore: add dev-team-agents"
```

---

## Isolamento com Worktree

Os agentes de codificação resolvem a decisão de worktree por uma **cascata de três níveis**:

1. **`.dev-team-agents/.worktree-session`** (override da sessão) — compartilhado entre todos os agentes da task, então workflows com múltiplos agentes resolvem exatamente uma vez.
2. **Defaults do `preferences.json`** — defina `worktree_active: true` para os agentes criarem uma worktree por task **sem perguntar**. A base branch vem de `worktree_base_branch` (ou é detectada automaticamente — nunca hardcoded como `main`/`master`), e as worktrees são criadas em `worktree_path` (padrão `.claude/worktrees/<ctx>/<title>/`).
3. **Perguntar uma vez** — apenas em instalações legadas onde a chave de preferência não existe.

**Isolamento Docker** — quando `worktree_active` está ligado e o projeto usa Docker Compose, os agentes podem subir um **stack compose isolado por worktree** (`worktree_docker_isolate: true`). Containers, redes e volumes são namespaceados com um nome claro (`<projeto>-wt-<ctx>-<title>`), as portas do host não são publicadas, e nada toca no stack principal.

**Finalização** — quando você pede o merge, o agente faz **rebase na base branch**, resolve conflitos, commita, faz o merge e então derruba **somente** a worktree e seu stack Docker isolado.

| Preferência | Padrão | Propósito |
|-----------|--------|-----------|
| `worktree_active` | `false` | Criar uma worktree por task por padrão (sem prompt) |
| `worktree_base_branch` | `null` | Base branch (`null` = auto-detectar) |
| `worktree_path` | `.claude/worktrees` | Onde as worktrees são criadas |
| `worktree_docker_isolate` | `true` | Stack Docker isolado por worktree (quando há Docker) |

---

## Memória dos Agentes

Agentes iniciam cada sessão sem memória das anteriores. Três mecanismos minimizam a perda de contexto:

- **Resumo de sessão** — ao final de qualquer sessão com arquivos alterados, os agentes escrevem uma entrada em `.dev-team-agents/user-data/session-summary.md`. Um hook `Stop` enforça isso automaticamente.
- **ADRs** — decisões significativas e difíceis de reverter são registradas como Architecture Decision Records em `docs/development/adrs/`. Crie um com: `bash .dev-team-agents/scripts/new-adr.sh "título"`
- **Project context skill** — define a ordem de carregamento de contexto que todo agente segue no startup, incluindo o resumo de sessão e o índice de ADRs.

---

## Coexistência & Customização

Dev Team Agents é uma **camada base**. As convenções do seu projeto sempre têm precedência: `CLAUDE.md` → `AGENTS.md` → `.agents/<agent-name>.md`. Se seu projeto diz usar tabs, os agentes usam tabs.

**Não** modifique arquivos dentro de `.dev-team-agents/` — eles são sobrescritos na atualização. Faça o override no nível do projeto:

```bash
.agents/backend-developer.md          # override por agente
CLAUDE.md                             # regras globais para todos os agentes
docs/development/code-standards.md  # padrões de código usados pelos reviewers
```

---

## Solução de Problemas

**Agentes não são reconhecidos pelo Claude** — verifique se o symlink existe: `ls .claude/agents/dev-team/`. Se faltando, rode o instalador novamente a partir da raiz do projeto.

**Skills não são carregadas** — verifique se `.claude/skills/` contém symlinks. Rode o instalador para restaurar links quebrados.

**Windows: o dev-team inteiro some (sem `/devteam:*`, sem agentes, sem skills)** — no Windows sem o Modo de Desenvolvedor, o git/MSYS grava os links de `.claude/` como arquivos-texto de ~62 bytes em vez de symlinks. O `ls -la` do `git-bash` ainda os mostra como `lrwxrwxrwx`, mas o Claude Code enxerga arquivos, então nada carrega. Confirme com `test -L .claude/commands/devteam && echo link || echo quebrado`. Corrija rodando `bash .dev-team-agents/scripts/fix-symlinks.sh` — ele repara automaticamente quando possível e, caso contrário, imprime três opções: (1) ativar o **Modo de Desenvolvedor** (Configurações → Sistema → Para desenvolvedores — recomendado, sem admin), (2) rodar `git config core.symlinks true && git checkout -- .claude` uma vez em um **PowerShell elevado**, ou (3) executar o **Claude Code como administrador** (feche-o por completo antes, incluindo o ícone na bandeja). Reinicie o Claude Code após reparar para ele reindexar o dev-team.

**Hook de verificação de atualização dispara a cada tool call** — verifique se `.dev-team-agents/user-data/.last-update-check` é um arquivo gravável (não um diretório) e se `scripts/hooks/pre-tool-use/01-check-updates.sh` é executável.

**O `setup-assistant` rodou, mas a seção `## dev-team-agents` está ausente do CLAUDE.md** — diga ao Claude: `"Como o setup-assistant, a seção dev-team-agents está faltando no CLAUDE.md — por favor adicione-a."`

**Um agente executou sem apresentar um plano primeiro** — verifique seu CLAUDE.md de projeto por alguma instrução que conflita com o plan mode.

---

## Telemetria Anônima

O dev-team-agents coleta **dados de uso anônimos e agregados** para nos ajudar a entender quais agentes e comandos são mais valiosos.

**O que é coletado:** nomes de agentes/comandos, eventos de instalação e atualização, contagem de sessões, família de SO e versão instalada. Nenhum código, caminho de arquivo, nome de projeto ou dado pessoal é coletado.

**Desative a qualquer momento** editando `.dev-team-agents/user-data/preferences.json`:

```json
{ "telemetry": false }
```

Detalhes completos em [PRIVACY.md](PRIVACY.md).

---

## Contribuindo

1. Faça um fork do repositório
2. Crie uma branch: `fix/agent-name-improvement` ou `feat/new-skill`
3. Siga os padrões de autoria em `CLAUDE.md`
4. Abra um PR com uma descrição clara do que mudou e por quê

---

## Licença

MIT
