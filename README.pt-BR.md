# Dev Team Agents

🇺🇸 [See the English Version](README.md)

**Multi-agent development harness** — um harness para organizar agentes de IA no desenvolvimento de software. Agnóstico a tecnologia, ciente do contexto do projeto e mantido colaborativamente.

---

## O que é isso

Não é apenas um pacote de agentes; é a camada que controla como esses agentes planejam, executam, testam, revisam e registram o trabalho.

Cada agente tem um papel definido, expertise e integração com workflows. O que faz disso um harness, e não uma coleção, é tudo o que existe em volta deles — o plan gate que barra execução silenciosa, os hooks de ciclo de vida que garantem memória entre sessões, o roteamento de review, os validadores que mantêm a árvore inteira honesta. Eles coexistem com as regras do seu projeto — as convenções do projeto sempre prevalecem.

18 agentes cobrem todo o ciclo de desenvolvimento: discovery, design, implementação, quality gates e documentação. → Veja a [Referência de Agentes](docs/agents.pt-BR.md) completa.

---

## Começo rápido — Primeiro resultado em menos de 10 minutos

### App desktop (macOS / Windows)

1. Baixe o app na [página de releases](https://github.com/Dev-Toolbelt/dev-team-agents/releases) e abra — ele instala a linha de comando para você
2. Faça login
3. O app verifica git, Python e seu provedor de IA (Claude Code, Codex ou opencode), e oferece corrigir o que for possível
4. Escolha a pasta do projeto, confirme o que foi detectado e inicie a primeira tarefa

A primeira tarefa só lê o código: auditar um módulo ou revisar suas últimas mudanças, no modo somente leitura do provedor.

### Só a linha de comando

```bash
brew install dev-toolbelt/devteam/devteam    # macOS, quando o primeiro release for publicado
winget install DevToolbelt.Devteam           # Windows, quando o primeiro release for publicado
bash scripts/install-cli.sh --from .         # hoje: a partir de um clone
devteam start                                # dentro do seu projeto
```

Comece com cinco comandos — `plan`, `fix`, `review`, `commit`, `pr`. Os outros aparecem conforme você usa.

## Pré-requisitos

**Python 3** precisa estar instalado no sistema — ele alimenta o motor de renderização, o graphify e os merges seguros de JSON no `settings.json`. Nada além do seu CLI de escolha é necessário.

Se estiver ausente, o instalador, o atualizador e o `/devteam:health-check` vão avisar e continuar em modo degradado. Instale com:

| Sistema | Comando |
|---------|---------|
| macOS | `brew install python3` |
| Linux (Debian/Ubuntu) | `sudo apt install python3` |
| Linux (Fedora/RHEL) | `sudo dnf install python3` |
| Windows | [python.org/downloads](https://www.python.org/downloads/) ou `winget install Python.Python.3` — no Git Bash, `python3`, `python` ou o launcher `py` funcionam: os scripts usam o que for Python 3.9+ (o stub da Microsoft Store é ignorado) |

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

## Entrando na conta

Uma conta com dev-team-agents é necessária para usar o framework ([ADR-0029](docs/development/adrs/0029-mandatory-accounts-owned-by-the-cli-licensed-through-a-signed-offline-entitlement.md)).

**Nesta versão**, a exigência da conta é anunciada mas não é obrigatória — você pode rodar sem entrar na conta, embora um banner vá lembrá-lo. **A próxima versão minor vai impor a exigência** e bloqueará comandos gated até que você entre.

### Entre uma vez por máquina

Após a instalação, entre com:

```bash
devteam auth login
```

Você será perguntado qual método quer usar para entrar:

| Método | Como funciona |
|--------|---------------|
| Email (sem senha) | Receba um código de 8 dígitos por email, digite-o para entrar. Nenhuma senha para lembrar. |
| Email + senha | Crie uma conta com email e senha (10–64 caracteres). |
| Google OAuth | Entre com sua conta Google; abre seu navegador de sistema. |
| GitHub OAuth | Entre com sua conta GitHub; abre seu navegador de sistema. |

O token de atualização é armazenado na sua máquina: no Keychain no macOS, com DPAPI no Windows e, no Linux, em um arquivo 0600, que `devteam auth status` informa como inseguro porque lá não há keychain do SO. Você pode revogá-lo a qualquer momento com `devteam auth logout`.

### O que funciona offline

Depois de entrar, dev-team-agents funciona **offline por até 7 dias**. Depois disso, uma verificação online é necessária para atualizar sua licença e continuar. Isso garante que você tenha tempo para trabalhar ininterruptamente mesmo se estiver longe da rede.

### Saiba mais

- **Política de Privacidade**: [PRIVACY.md](PRIVACY.md) — que dados coletamos e como os protegemos
- **Termos de Uso**: [TERMS.md](TERMS.md) — exigências de conta, trial e licenciamento

---

## Instalação global (prévia da v3)

O `devteam` instala o framework **uma vez por máquina** e vincula cada projeto a ela, então uma atualização é aplicada uma vez em vez de uma vez por projeto. O marco M1 — store, bind, pin de versão e migração do v2 — já funciona. O CLI é instalado junto com suas dependências ([ADR-0028](docs/development/adrs/0028-the-devteam-cli-installs-with-its-dependencies-on-windows-and-macos.md)), a partir da primeira release que o contém:

| Plataforma | Instalar o CLI | Dependências |
|------------|----------------|--------------|
| macOS / Linux | `curl -fsSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install-cli.sh \| bash` — ou `bash scripts/install-cli.sh --from .` num clone | Python 3.9+ e git; no macOS o script abre o instalador das Command Line Tools quando faltam |
| Windows | `devteam-setup-<versão>-<arch>.exe` das [releases](https://github.com/Dev-Toolbelt/dev-team-agents/releases), ou **Install the CLI** no app desktop | Nenhuma: o instalador traz o próprio Python e oferece instalar o Git for Windows |

Os dois instalam só para o seu usuário, colocam o `devteam` no PATH e instalam o framework no store. O tap do Homebrew e o pacote winget ainda serão publicados.

| Passo | Comando |
|-------|---------|
| Vincular um projeto | `devteam bind /caminho/do/projeto` |
| Listar o que está disponível | `devteam catalog agents|skills|commands` |
| Gerenciar suas skills globais do Claude / Codex / opencode | `devteam skills list\|show\|install\|remove` |
| Conectar contas do GitHub e Jira | `devteam integration connect github\|jira`, test, disconnect, config |
| Ver as tarefas dos agentes em todos os projetos vinculados (o Quadro do app lê o mesmo) | `devteam tasks list\|watch` |
| Atualizar todos os projetos de uma vez | `devteam update` |
| Manter um projeto numa versão | `devteam pin 3.0.0` |
| Converter uma instalação v2 existente, em qualquer formato (o `bind` recusa; o diálogo de bind do app oferece) | `devteam migrate --apply --untrack`, depois o commit |
| Mover a memória de um projeto para o store | `devteam upgrade --apply` |
| Gerenciar credenciais (definir, obter, auditar, migrar v2) | `devteam cred set\|get\|list\|unset\|import\|check\|backends` |

Rodando de um clone no Windows, chame o CLI como `py -3 scripts\cli\devteam …` — o shebang do arquivo sem extensão não executa lá. Um projeto vinculado guarda um `.dev-team-agents/project.json` commitado (sua identidade e suas pastas de conhecimento) e dois links para o store (`scripts/`, `templates/`); nenhuma cópia do framework, e nenhum diff de framework no repositório do seu produto.

`devteam bind` usa `--mode=auto` por padrão, que resolve para **`link`** (symlinks para o store) em qualquer sistema de arquivos que suporte — o modo recomendado, já que um `devteam update` posterior chega a todo projeto vinculado assim sem nenhum passo extra. `copy` (o fallback do Windows quando symlinks não estão disponíveis) e o modo opcional `vendored` precisam de um `devteam sync` explícito por projeto após cada atualização para captar a mudança. Se um link sumir — um `git rebase` para um commit que ainda tinha `.dev-team-agents/scripts` vendorizado o remove — o próximo hook refaz o bind do projeto sozinho através do pointer `.dev-team-agents/core-dir`, no Claude Code, no Codex e no opencode.

> Layout do store, modos de bind, registro de hooks, contrato `--json` e códigos de saída: [CLAUDE-md/cli.md](CLAUDE-md/cli.md)

### Integrações — GitHub e Jira

Conecte suas contas GitHub e Jira uma vez; cada projeto na sua máquina pode usá-las. Tokens são armazenados de forma segura no keychain do SO e nunca são exibidos novamente. Vinculações específicas por projeto (qual repositório, qual projeto Jira) são commitadas em cada projeto para que seu time fique sincronizado.

**Crie tokens:**
- **GitHub**: [Tokens de acesso pessoal (fine-grained)](https://github.com/settings/personal-access-tokens/new) — selecione **Repository access: Public repositories (read-only)** e permissões **Metadata (read-only)**, ou para repositórios privados conceda **Contents (read-only)** + **Metadata (read-only)**.
- **Jira Cloud**: Tokens de API em [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens). Você também precisará do seu email. Para Jira Data Center auto-hospedado, use um Personal Access Token (PAT).

Conecte com:
```bash
devteam integration connect github
devteam integration connect jira --field site_url=https://acme.atlassian.net --field email=me@example.com
```

Cada prompt lê o token apenas da entrada padrão — nunca da linha de comando, o que o deixaria no histórico do shell. O token é enviado apenas à origem configurada via HTTPS e armazenado no keychain da sua máquina.

Depois, em cada projeto, vincule a integração ao seu repositório ou projeto:
```bash
devteam integration config set github repository owner/repo-name
devteam integration config set jira project_key PROJ
```

Ou descubra de forma interativa na aba **Integrações** do app desktop, ou com `devteam integration resources github repos` e `devteam integration resources jira projects`.

O app desktop também tem uma aba **Credentials** (Credenciais) em cada tela de projeto para criar e editar `.dev-team-agents/credentials.local.json` como uma árvore livre, com segredos por campo, flag de produção por grupo e busca — ou use `devteam cred local init`, `show` e `patch` da CLI.

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

## Métricas de Uso

Curioso sobre como os agentes e comandos são usados na prática? Veja o relatório mais recente de uso anônimo: [docs/reports/metrics-last-20-days.md](docs/reports/metrics-last-20-days.md).

---

## Slash Commands

Após a instalação, Claude Code e opencode expõem slash commands sob o namespace `/devteam:`. No Codex, o padrão local ao projeto é o caminho por skill `$devteam-<name>`. Cada entrypoint dispara os agentes corretos e limita automaticamente sua atuação à branch ou worktree atual do git.

| Command | O que faz |
|---------|-----------|
| `/devteam:setup` | Onboarding — detecta primeira execução ou refresh, e então o setup-assistant configura `CLAUDE.md`, `docs/`, a wiki e suas preferências |
| `/devteam:plan` | Planejamento — o product-analyst lidera e produz um documento de requisitos só de negócio, pronto para virar sprints; o software-architect entra apenas em pedido técnico explícito |
| `/devteam:backend` | Implementação backend — backend-developer + database-specialist → backend-test-specialist |
| `/devteam:frontend` | Implementação frontend — frontend-developer + ui-ux-designer → frontend-test-specialist |
| `/devteam:mobile` | Implementação mobile — mobile-developer + ui-ux-designer (quando relevante) |
| `/devteam:fullstack` | Implementação full-stack — times de backend + frontend em paralelo |
| `/devteam:design` | Design UI/UX — ui-ux-designer |
| `/devteam:relayout` | Refazer o layout de uma tela existente para corresponder a referências visuais — ui-ux-designer + frontend-developer, gate obrigatório de referência/tela alvo, worktree isolada, review automática pós-execução |
| `/devteam:seo` | Quality gate de SEO — seo-specialist (técnico, on-page, Core Web Vitals, dados estruturados, GEO/LLM) |
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
| `/devteam:pr` | Pull request — rascunha título + descrição, pede confirmação antes de criar; antes do push, pergunta com um quiz sensível a CI/CD (acompanhar Actions vs. só o push) quando o GitHub Actions está configurado |
| `/devteam:push` | Push — pergunta com um quiz sensível a CI/CD (acompanhar CI + auto-correção vs. só o push vs. outro) quando o GitHub Actions está configurado; faz push normalmente caso contrário |
| `/devteam:merge` | Merge — detecta um branch de trabalho fora do padrão e pergunta o alvo; detecta worktree/infra isolada e oferece commit + rebase + merge + teardown (recomendado) vs. commit + merge apenas vs. merge apenas; reforça rodar `/devteam:learn` caso ele não tenha sido executado desde o último commit |
| `/devteam:commit` | Commit — lê mudanças staged, agrupa por camada, escreve e executa commits |
| `/devteam:learn` | Captura de conhecimento — consolida decisões, padrões e descobertas da sessão em docs, wiki e ADRs, e então faz o commit automaticamente (declara o manifesto de commits no plano). `--auto` pula a pergunta de aprovação e limita o learn ao que a sessão, branch ou worktree atual tocou |
| `/devteam:rule` | Padronização — cataloga uma regra obrigatória de reuso (ex.: `/devteam:rule use o componente XPTO em todo o projeto`) em `docs/development/reuse-guidelines.md`, para que trabalhos futuros nunca a ignorem. Classificada como `code-pattern`, `path-convention` ou `design-rule`; aplicada pelo gate de review e, para os tipos mecanizáveis, por um lint no Stop hook |
| `/devteam:sync-rules` | Backfill — varre `docs/` em busca de convenções já documentadas em prosa mas nunca catalogadas em `reuse-guidelines.md`, e roda a rotina classify → propose → confirm → append do `/devteam:rule` para cada candidata, uma confirmação por vez. Sugerido após install/update e sinalizado pelo `/devteam:health-check` |
| `/devteam:explain` | Glossário sob demanda — explica um termo, sigla ou jargão que você viu na sessão. Direto por princípio: expande toda sigla, diz o problema que aquilo resolve, dá um exemplo na linguagem do seu projeto e desenha um diagrama mermaid quando o termo é uma forma (um fluxo, uma troca entre partes, uma hierarquia, um ciclo de vida) e não apenas uma definição. Fecha oferecendo um quiz interativo |
| `/devteam:health-check` | Diagnóstico da instalação — detecta o provedor ativo (Claude / opencode / Codex), roda 13 verificações (symlinks, scripts, user data, config do provedor, graphify, CLAUDE.md, .gitignore, preferências, notifier, credenciais, artefatos de memória, pré-requisito do Python, ferramentas de produtividade/eficiência de tokens) e aplica correções automáticas seguras. Quase nunca apaga: o que não souber onde colocar vai para `.dev-team-agents/user-data/legacy/<data>/`, arquivos que acumulam conhecimento são adaptados no lugar nunca regenerados, e a única exceção é um `.pre-migration.bak` confirmado, cujo valor já está em `state.json` |
| `/devteam:adr` | Architecture Decision Record — roda `scripts/new-adr.sh` para criar um ADR numerado, e então o software-architect preenche o template |
| `/devteam:update` | Atualização — verifica se há uma nova release do dev-team-agents e a aplica |
| `/devteam:symlinks` | Reparo de symlinks — detecta o SO, repara links materializados como arquivos comuns e guia a correção quando o SO bloqueia symlinks nativos |
| `/devteam:version` | Checagem de versão — imprime a versão instalada do dev-team-agents no mesmo layout do banner de início de sessão; uma única chamada bash, sem spawn de agente, custo mínimo de token |
| `/devteam:status` | Snapshot do git status — branch/worktree, mudanças unstaged e staged, últimos 5 commits e totais em tabelas markdown formatadas; uma única chamada bash, sem spawn de agente, custo mínimo de token. `/devteam:status <nome-da-branch>` inspeciona essa branch em vez da atual |

**Exemplos de uso:**

```
/devteam:plan adicionar exportação para PDF no relatório de abastecimento
/devteam:backend implementar o endpoint de exportação PDF
/devteam:review
/devteam:pr draft
/devteam:explain SPA, SSR, tenant, middleware
```

Os detalhes de tier de modelo, renderização por provedor e orquestração específica do Codex agora ficam em [Arquitetura do Harness](docs/harness.pt-BR.md).

---

## Agentes

O time tem **18 agentes** cobrindo todo o ciclo de vida. Detalhes completos na [Referência de Agentes](docs/agents.md).

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
| `seo-specialist` | Quality gate de SEO — técnico, on-page, Core Web Vitals, dados estruturados, GEO/LLM |
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

Isolamento com worktree, thresholds de notificação, idioma e outros ajustes locais de runtime agora ficam em [Preferências do Usuário](docs/user-preferences.pt-BR.md).

Para a estrutura de acesso a staging/produção, veja [Referência de Credentials](docs/credentials.local.pt-BR.md).

---

## Memória dos Agentes

Agentes iniciam cada sessão sem memória das anteriores. Cinco camadas minimizam a perda de contexto, cada uma guardando um tipo de coisa:

| Camada | Onde | Guarda | Vida útil |
|--------|------|--------|-----------|
| Estrutural | `docs/project.md`, `docs/development/` | Stack, arquitetura, padrões | Reescrita — sempre descreve o agora |
| Episódica | `<memory-dir>/session-summary.md` (pointer em `.dev-team-agents/memory-dir`) | O que aconteceu, em ordem | Expira em ~30 dias |
| Semântica | `docs/wiki/` | O que não dá para deduzir do código | Permanente; substituída, nunca apagada |
| Decisional | `docs/development/adrs/` | Por que uma escolha difícil de reverter foi feita | Permanente e imutável |
| Mecânica | `graphify-out/graph.json` | Onde as coisas estão no código | Regenerada |

**Uma pergunta decide onde algo vai: dá para deduzir isso lendo o código?** Se sim, não é escrito em lugar nenhum — essa regra é o que impede a memória de virar uma segunda fonte de verdade que envelhece e passa a contradizer o repositório.

- **Resumo de sessão** — escrito ao final de qualquer sessão com arquivos alterados; um hook `Stop` enforça. Antes de entradas antigas serem removidas, os agentes verificam se as decisões nelas chegaram a virar ADR ou entrada de wiki, e avisam quais não viraram em vez de descartá-las em silêncio.
- **Wiki** — `docs/wiki/README.md` é um índice por palavra-chave, uma linha por entrada. Os agentes fazem grep nele para a tarefa atual e abrem só o que casar, então um wiki com 200 entradas custa o mesmo no startup que um com 5.
- **ADRs** — crie um com `bash .dev-team-agents/scripts/new-adr.sh "título"`.
- **`/devteam:learn`** — promove o que a sessão aprendeu da camada episódica para as duráveis.

Nada nesse sistema apaga conhecimento automaticamente. A camada episódica é a única exceção, por design, e a verificação de promoção acima é o que a protege.

---

## Plugins

Integrações opcionais, por projeto, construídas sobre um sistema de manifests. Ative-as com os comandos `devteam plugin` — o app desktop também tem uma aba **Plugins** na tela de cada projeto.

**Graphify** (plugin de referência) — constrói um grafo de conhecimento do código para que os agentes leiam a estrutura antes de buscar nos arquivos brutos:

```bash
devteam plugin enable graphify          # ativa e preenche a config pela detecção automática
devteam plugin config get graphify      # veja o que foi detectado
devteam plugin run graphify rebuild     # constrói o grafo agora
devteam plugin config set graphify auto_refresh true   # (opcional) reconstrói ao fim da sessão quando o código mudou
```

Todos os plugins vêm no core — sem instalação remota, sem integrações de terceiros. Para detalhes de design, autoria e comandos: [plugins/README.md](plugins/README.md) e [ADR-0019](docs/development/adrs/0019-plugins-as-manifest-declared-per-project-integrations.md).

---

## Coexistência & Customização

Overrides no nível do projeto, regras de precedência e orientações de customização agora ficam em [Arquitetura do Harness](docs/harness.pt-BR.md).

---

## Solução de Problemas

**Agentes não são reconhecidos pelo CLI** — verifique se o symlink existe: `ls .claude/agents/dev-team/` (Claude Code), `ls .opencode/agents/` (opencode), `ls .codex/agents/` (Codex CLI). Se faltando, rode o instalador daquele provedor novamente a partir da raiz do projeto.

**Skills não são carregadas** — verifique se `.claude/skills/` (ou `.opencode/skills/`, `.codex/skills/`) contém symlinks. Rode o instalador para restaurar links quebrados.

**Windows: o dev-team inteiro some (sem `/devteam:*`, sem agentes, sem skills)** — no Windows sem o Modo de Desenvolvedor, o git/MSYS grava os symlinks como arquivos-texto de ~62 bytes: os links de `.claude/` na instalação do Claude Code e o link de `skills/` dentro de `.opencode/` ou `.codex/` nos demais provedores. O `ls -la` do `git-bash` ainda os mostra como `lrwxrwxrwx`, mas o CLI enxerga arquivos comuns, então nada carrega. Confirme com `test -L .claude/commands/devteam && echo link || echo quebrado`. Repare a árvore do Claude rodando `bash .dev-team-agents/scripts/fix-symlinks.sh` — ele repara automaticamente quando possível e, caso contrário, imprime três opções: (1) ativar o **Modo de Desenvolvedor** (Configurações → Sistema → Para desenvolvedores — recomendado, sem admin), (2) rodar `git config core.symlinks true && git checkout -- .claude` uma vez em um **PowerShell elevado**, ou (3) executar o **seu CLI como administrador** (feche-o por completo antes, incluindo o ícone na bandeja). Para opencode e Codex, rode novamente o instalador daquele provedor assim que os symlinks nativos estiverem habilitados. Reinicie o seu CLI após reparar para ele reindexar o dev-team. Se o `fix-symlinks.sh` imprimir `[DEVTEAM:SYMLINK_COMMIT_NEEDED]`, a correção funcionou localmente mas o blob commitado ainda é um arquivo comum — rode `git add`/`git commit` nos caminhos listados, ou os mesmos links quebram de novo no próximo checkout, pull, ou em um clone novo de um colega.

**Verificação de atualização parece travada / não dispara** — a checagem roda uma vez por sessão a partir do `SessionStart` (`scripts/hooks/session-start.sh`), não a cada tool call. Verifique se `.dev-team-agents/user-data/state.json` é um arquivo gravável (não um diretório) e se `session-start.sh` é executável — a chave `last_update_check` agora vive lá. O refresh do Graphify ao fim da sessão é a configuração opcional `auto_refresh` do plugin (`devteam plugin config set graphify auto_refresh true`).

**As notificações e o quadro de tarefas chegam ao app desktop.** Nenhum provider mostra ao usuário a saída de um hook (a do `SessionStart` vira contexto do modelo, a do `Stop` não é exibida), então os hooks capturam atualizações de tarefas e enfileiram as notificações — janela de contexto, trabalho sem commit, docs desatualizados, atualizações, a dica do dia. O app desktop mostra:
- **Notificações** como alertas do sistema, inclusive com a janela fechada
- **Quadro** — visualização Kanban de todas as tarefas que os agentes criam, de todos os projetos vinculados, com tempo gasto em cada etapa, quando cada tarefa foi criada e, depois de concluída, quando terminou; o card Direct work leva o título da sessão e acompanha as renomeações. Sessões são capturadas automaticamente pelos hooks para Claude Code, Codex e opencode; passos de planos aprovados e agentes disparados viram tarefas ali (agentes built-in e de revisão/QA excluídos), e o que a própria sessão faz entra num único card **Direct work** por sessão, listando os prompts que o originaram — em andamento quando altera algo (uma edição, um commit), em A fazer quando só lê (uma verificação, uma busca), escondido depois de um tempo configurável se ninguém der continuidade. O quadro é somente leitura. O quadro de um projeto tem cinco colunas lado a lado — A fazer, Em andamento, **Em Revisão**, **PR/MR Criado**, Concluído — numa linha que rola na horizontal quando a janela é estreita; uma tarefa entra em **Em Revisão** só quando uma revisão é disparada, mostra ali seus achados de revisão e sai quando a revisão passa ou seus achados são corrigidos; entra em **PR/MR Criado** quando um PR ou MR é feito. As tarefas mostram badges de PR/MR (clicáveis) e badges de issue (Jira, GitHub — clicáveis) que linkam ao seu tracker. Equivalente CLI: `devteam tasks list` e `watch`.

Sem o app, as notificações e registros de tarefas esperam na fila: `devteam notifications list` e `devteam tasks list` as mostram. Detalhes: `CLAUDE-md/notifications.md`.

**O `setup-assistant` rodou, mas a seção `## dev-team-agents` está ausente do CLAUDE.md** — diga ao seu CLI: `"Como o setup-assistant, a seção dev-team-agents está faltando no CLAUDE.md — por favor adicione-a."`

**Um agente executou sem apresentar um plano primeiro** — verifique seu CLAUDE.md de projeto por alguma instrução que conflita com o plan mode.

---

## Telemetria Anônima (BETA)

O dev-team-agents pode coletar **dados de uso anônimos e agregados** para nos ajudar a entender quais agentes e comandos são mais valiosos. **Fica desativado a menos que você o ative.**

**Consentimento:** o instalador pergunta uma única vez, na primeira instalação, abrindo seu terminal diretamente — então o prompt aparece até no caminho `curl … | bash`. Responder `n`, não responder em 60 segundos, definir `DEVTEAM_NONINTERACTIVE=1` ou não ter terminal algum deixam tudo **desativado**. Nada é enfileirado ou enviado enquanto o `preferences.json` não disser `"telemetry": true`.

**O que é coletado** (somente quando ativado): nomes de agentes/comandos, eventos de instalação e atualização, contagem de sessões, família de SO e versão instalada. Nenhum código, caminho de arquivo, nome de projeto ou dado pessoal é coletado.

**Mude a qualquer momento** — num projeto vinculado com `devteam bind`, pelas configurações do projeto no app desktop ou com `devteam prefs set telemetry false --scope project` (`true` para ativar). Uma instalação v2 ainda não vinculada continua lendo `.dev-team-agents/user-data/preferences.json`; o `devteam bind` importa esse arquivo para as preferências do projeto e o move para fora do projeto:

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
