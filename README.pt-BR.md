# Dev Team Agents

🇺🇸 [See the English Version](README.md)

**Multi-agent development harness** — um harness para organizar agentes de IA no desenvolvimento de software. Agnóstico a tecnologia, ciente do contexto do projeto e mantido colaborativamente.

---

## O que é isso

Não é apenas um pacote de agentes; é a camada que controla como esses agentes planejam, executam, testam, revisam e registram o trabalho.

Cada agente tem um papel definido, expertise e integração com workflows. O que faz disso um harness, e não uma coleção, é tudo o que existe em volta deles — o plan gate que barra execução silenciosa, os hooks de ciclo de vida que garantem memória entre sessões, o roteamento de review, os validadores que mantêm a árvore inteira honesta. Eles coexistem com as regras do seu projeto — as convenções do projeto sempre prevalecem.

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
  /devteam:plan do a plan          ← UX idêntica entre CLIs (Codex → /prompts:devteam-plan ou $devteam-plan)
```

**Modelo em camadas — três preocupações, mantidas separadas:**

1. **Conhecimento** (skills, prompts de papel dos agentes, prompts de fluxo dos comandos, comportamento dos hooks). Autorado uma vez, versionado neste repo, idêntico entre provedores.
2. **Adaptadores** (formato de frontmatter por provedor, tabela de mapeamento de nomes de ferramenta, formato de saída do slash command). Definidos uma vez por provedor em `scripts/lib/*.json` e renderizados no install time. Adicionar um provedor novo = uma coluna em `tiers.json` + uma linha em `tool-map.json` + uma linha em `command-map.json` + um `install-<provider>.sh` enxuto.
3. **Ligação** (`.claude/settings.json` para Claude, `.opencode/plugins/dev-team-agents.ts` para opencode, `.codex/hooks.json` para Codex). Os três invocam os MESMOS dispatchers em `scripts/hooks/*.sh` — sem duplicação de hooks por provedor.

**Model id por agente é rígido por tier.** Cada agente declara um de `reasoning | backend-exec | frontend | repetitive`. Cada tier é resolvido para um model id concreto via `tiers.json` por provedor, então trocar de provedor é uma mudança de uma coluna — sem editar o corpo de qualquer agente. No Claude Code isso significa que arquitetura e segurança rodam em Opus, implementação e review em Sonnet, e geração de docs em Haiku, em vez de todo subagente compartilhar o modelo da sessão.

**Todo agente abre com um run banner** — uma tabela agente/tier/modelo/effort impressa antes de qualquer outra coisa, nos três provedores, para você sempre ver qual modelo está fazendo o trabalho.

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

Após instalar, inicie o fluxo de setup dizendo ao seu CLI:

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
| `/devteam:setup` | Onboarding — detecta primeira execução ou refresh, e então o setup-assistant configura `CLAUDE.md`, `docs/`, a wiki e suas preferências |
| `/devteam:plan` | Planejamento — o product-analyst lidera e produz um documento de requisitos só de negócio, pronto para virar sprints; o software-architect entra apenas em pedido técnico explícito |
| `/devteam:backend` | Implementação backend — backend-developer + database-specialist → backend-test-specialist |
| `/devteam:frontend` | Implementação frontend — frontend-developer + ui-ux-designer → frontend-test-specialist |
| `/devteam:mobile` | Implementação mobile — mobile-developer + ui-ux-designer (quando relevante) |
| `/devteam:fullstack` | Implementação full-stack — times de backend + frontend em paralelo |
| `/devteam:design` | Design UI/UX — ui-ux-designer |
| `/devteam:fix` | Correção de bug — desenvolvedor(es) relevante(s) → test-specialist |
| `/devteam:refactor` | Refatoração — software-architect planeja, desenvolvedor(es) executam |
| `/devteam:architect` | Decisões de arquitetura e ADRs — software-architect |
| `/devteam:audit` | Análise profunda de módulo/área — backend-developer + frontend-developer + security-specialist + devops-specialist; salva relatório em `docs/audit/` |
| `/devteam:review` | Code review — code-reviewer + software-architect + security-specialist + qa-specialist |
| `/devteam:qa` | Garantia de qualidade — qa-specialist |
| `/devteam:security` | Auditoria de segurança — security-specialist + software-architect |
| `/devteam:dba` | Trabalho de banco de dados — database-specialist + software-architect |
| `/devteam:devops` | Infraestrutura / CI/CD — devops-specialist |
| `/devteam:tester` | Apenas testes — backend-test-specialist + frontend-test-specialist |
| `/devteam:docs` | Documentação — technical-writer |
| `/devteam:pr` | Pull request — rascunha título + descrição, pede confirmação antes de criar |
| `/devteam:commit` | Commit — lê mudanças staged, agrupa por camada, escreve e executa commits |
| `/devteam:learn` | Captura de conhecimento — consolida decisões, padrões e descobertas da sessão em docs, wiki e ADRs, e então faz o commit automaticamente (declara o manifesto de commits no plano) |
| `/devteam:explain` | Glossário sob demanda — explica um termo, sigla ou jargão que você viu na sessão. Direto por princípio: expande toda sigla, diz o problema que aquilo resolve, dá um exemplo na linguagem do seu projeto e desenha um diagrama mermaid quando o termo é uma forma (um fluxo, uma troca entre partes, uma hierarquia, um ciclo de vida) e não apenas uma definição. Fecha oferecendo um quiz interativo |
| `/devteam:health-check` | Diagnóstico da instalação — detecta o provedor ativo (Claude / opencode / Codex), roda 9 verificações (symlinks, scripts, user data, config do provedor, graphify, CLAUDE.md, .gitignore, preferências, notifier) e aplica correções automáticas seguras |
| `/devteam:adr` | Architecture Decision Record — roda `scripts/new-adr.sh` para criar um ADR numerado, e então o software-architect preenche o template |
| `/devteam:update` | Atualização — verifica se há uma nova release do dev-team-agents e a aplica |
| `/devteam:symlinks` | Reparo de symlinks — detecta o SO, repara links materializados como arquivos comuns e guia a correção quando o SO bloqueia symlinks nativos |

**Exemplos de uso:**

```
/devteam:plan adicionar exportação para PDF no relatório de abastecimento
/devteam:backend implementar o endpoint de exportação PDF
/devteam:review
/devteam:pr draft
/devteam:explain SPA, SSR, tenant, middleware
```

**Em qual modelo cada comando roda.** Todo comando declara um tier em `scripts/lib/commands.json`, e no opencode e no Codex esse tier vira um modelo concreto na hora da instalação. No Claude Code o corpo é symlinkado como está, então o tier só chega até ele por uma chave `model:` no frontmatter do comando — e essa chave é usada apenas nos sete comandos `repetitive` (`docs`, `pr`, `commit`, `learn`, `update`, `symlinks`, `health-check`), que rodam em Haiku. Todos os outros herdam o modelo em que sua sessão está. O motivo é deliberado: `model:` sobrescreve a sessão, então fixar um comando de planejamento em Opus desfaria em silêncio uma sessão que você baixou para economizar, enquanto um pin em Haiku só pode custar menos do que você escolheu.

No **Codex especificamente**, esse pin por tier vale para os **agentes** renderizados em `.codex/agents/*.toml`. Os arquivos `/prompts:devteam-*` são prompts Markdown simples, então não carregam campos runtime de `model` ou `model_reasoning_effort` por conta própria — eles dependem dos agentes que disparam para aplicar a política de modelo/esforço no Codex.

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

Os agentes são invocados pelo papel no seu prompt:

```
"Como o product-analyst, analise este PRD: [documento]"
"Como o software-architect, defina a arquitetura para este projeto."
"Como o backend-developer, implemente [tarefa]"
"Como o code-reviewer, revise as mudanças em [arquivos]."
```

Nomear o papel funciona em todos os CLIs suportados — Claude Code (o CLI `claude`, app desktop, app web em [claude.ai/code](https://claude.ai/code), extensões de IDE), opencode e Codex CLI — porque os agentes são renderizados a partir de uma única fonte canônica por provedor.

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
2. **Defaults do `preferences.json`** — `worktree_active` já vem `true`, então os agentes criam uma worktree por task **sem perguntar**; defina `false` para trabalhar direto numa branch. A base branch vem de `worktree_base_branch` (ou é detectada automaticamente — nunca hardcoded como `main`/`master`), e as worktrees são criadas em `worktree_path` (padrão `.dev-team-agents/worktrees/<ctx>/<title>/`).
3. **Perguntar uma vez** — apenas em instalações legadas onde a chave de preferência não existe.

**Isolamento Docker** — quando `worktree_active` está ligado e o projeto usa Docker Compose, os agentes podem subir um **stack compose isolado por worktree** (`worktree_docker_isolate: true`). Containers, redes e volumes são namespaceados com um nome claro (`<projeto>-wt-<ctx>-<title>`), as portas do host não são publicadas, e nada toca no stack principal.

**Finalização** — quando você pede o merge, o agente faz **rebase na base branch**, resolve conflitos, commita, faz o merge e então derruba **somente** a worktree e seu stack Docker isolado.

| Preferência | Padrão | Propósito |
|-----------|--------|-----------|
| `worktree_active` | `true` | Criar uma worktree por task por padrão (sem prompt) |
| `worktree_base_branch` | `null` | Base branch (`null` = auto-detectar) |
| `worktree_path` | `.dev-team-agents/worktrees` | Onde as worktrees são criadas |
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

**Agentes não são reconhecidos pelo CLI** — verifique se o symlink existe: `ls .claude/agents/dev-team/` (Claude Code), `ls .opencode/agents/` (opencode), `ls .codex/agents/` (Codex CLI). Se faltando, rode o instalador daquele provedor novamente a partir da raiz do projeto.

**Skills não são carregadas** — verifique se `.claude/skills/` (ou `.opencode/skills/`, `.codex/skills/`) contém symlinks. Rode o instalador para restaurar links quebrados.

**Windows: o dev-team inteiro some (sem `/devteam:*`, sem agentes, sem skills)** — no Windows sem o Modo de Desenvolvedor, o git/MSYS grava os symlinks como arquivos-texto de ~62 bytes: os links de `.claude/` na instalação do Claude Code e o link de `skills/` dentro de `.opencode/` ou `.codex/` nos demais provedores. O `ls -la` do `git-bash` ainda os mostra como `lrwxrwxrwx`, mas o CLI enxerga arquivos comuns, então nada carrega. Confirme com `test -L .claude/commands/devteam && echo link || echo quebrado`. Repare a árvore do Claude rodando `bash .dev-team-agents/scripts/fix-symlinks.sh` — ele repara automaticamente quando possível e, caso contrário, imprime três opções: (1) ativar o **Modo de Desenvolvedor** (Configurações → Sistema → Para desenvolvedores — recomendado, sem admin), (2) rodar `git config core.symlinks true && git checkout -- .claude` uma vez em um **PowerShell elevado**, ou (3) executar o **seu CLI como administrador** (feche-o por completo antes, incluindo o ícone na bandeja). Para opencode e Codex, rode novamente o instalador daquele provedor assim que os symlinks nativos estiverem habilitados. Reinicie o seu CLI após reparar para ele reindexar o dev-team.

**Hook de verificação de atualização dispara a cada tool call** — verifique se `.dev-team-agents/user-data/.last-update-check` é um arquivo gravável (não um diretório) e se `scripts/hooks/pre-tool-use/01-check-updates.sh` é executável.

**O `setup-assistant` rodou, mas a seção `## dev-team-agents` está ausente do CLAUDE.md** — diga ao seu CLI: `"Como o setup-assistant, a seção dev-team-agents está faltando no CLAUDE.md — por favor adicione-a."`

**Um agente executou sem apresentar um plano primeiro** — verifique seu CLAUDE.md de projeto por alguma instrução que conflita com o plan mode.

---

## Telemetria Anônima

O dev-team-agents pode coletar **dados de uso anônimos e agregados** para nos ajudar a entender quais agentes e comandos são mais valiosos. **Fica desativado a menos que você o ative.**

**Consentimento:** o instalador pergunta uma única vez, na primeira instalação, abrindo seu terminal diretamente — então o prompt aparece até no caminho `curl … | bash`. Responder `n`, não responder em 60 segundos, definir `DEVTEAM_NONINTERACTIVE=1` ou não ter terminal algum deixam tudo **desativado**. Nada é enfileirado ou enviado enquanto o `preferences.json` não disser `"telemetry": true`.

**O que é coletado** (somente quando ativado): nomes de agentes/comandos, eventos de instalação e atualização, contagem de sessões, família de SO e versão instalada. Nenhum código, caminho de arquivo, nome de projeto ou dado pessoal é coletado.

**Mude a qualquer momento** editando `.dev-team-agents/user-data/preferences.json` — `false` para desativar, `true` para ativar:

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
