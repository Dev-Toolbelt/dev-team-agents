# Dev Team Agents

🇺🇸 [See the English Version](README.md)

**Multi-agent development harness** — um harness para organizar agentes de IA no desenvolvimento de software. Agnóstico a tecnologia, ciente do contexto do projeto e mantido colaborativamente.

---

## O que é isso

Não é apenas um pacote de agentes; é a camada que controla como esses agentes planejam, executam, testam, revisam e registram o trabalho.

Cada agente tem um papel definido, expertise e integração com workflows. O que faz disso um harness, e não uma coleção, é tudo o que existe em volta deles — o plan gate que barra execução silenciosa, os hooks de ciclo de vida que garantem memória entre sessões, o roteamento de review, os validadores que mantêm a árvore inteira honesta. Eles coexistem com as regras do seu projeto — as convenções do projeto sempre prevalecem.

18 agentes cobrem todo o ciclo de desenvolvimento: discovery, design, implementação, quality gates e documentação. → Veja a [Referência de Agentes](docs/agents.pt-BR.md) completa.

---

## Pré-requisitos

**Python 3** precisa estar instalado no sistema — ele alimenta o motor de renderização, o graphify e os merges seguros de JSON no `settings.json`. Nada além do seu CLI de escolha é necessário.

Se estiver ausente, o instalador, o atualizador e o `/devteam:health-check` vão avisar e continuar em modo degradado. Instale com:

| Sistema | Comando |
|---------|---------|
| macOS | `brew install python3` |
| Linux (Debian/Ubuntu) | `sudo apt install python3` |
| Linux (Fedora/RHEL) | `sudo dnf install python3` |
| Windows | [python.org/downloads](https://www.python.org/downloads/) ou `winget install Python.Python.3` |

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
| `/devteam:commit` | Commit — lê mudanças staged, agrupa por camada, escreve e executa commits |
| `/devteam:learn` | Captura de conhecimento — consolida decisões, padrões e descobertas da sessão em docs, wiki e ADRs, e então faz o commit automaticamente (declara o manifesto de commits no plano) |
| `/devteam:rule` | Padronização — cataloga uma regra obrigatória de reuso (ex.: `/devteam:rule use o componente XPTO em todo o projeto`) em `docs/development/reuse-guidelines.md`, para que trabalhos futuros nunca a ignorem. Classificada como `code-pattern`, `path-convention` ou `design-rule`; aplicada pelo gate de review e, para os tipos mecanizáveis, por um lint no Stop hook |
| `/devteam:sync-rules` | Backfill — varre `docs/` em busca de convenções já documentadas em prosa mas nunca catalogadas em `reuse-guidelines.md`, e roda a rotina classify → propose → confirm → append do `/devteam:rule` para cada candidata, uma confirmação por vez. Sugerido após install/update e sinalizado pelo `/devteam:health-check` |
| `/devteam:explain` | Glossário sob demanda — explica um termo, sigla ou jargão que você viu na sessão. Direto por princípio: expande toda sigla, diz o problema que aquilo resolve, dá um exemplo na linguagem do seu projeto e desenha um diagrama mermaid quando o termo é uma forma (um fluxo, uma troca entre partes, uma hierarquia, um ciclo de vida) e não apenas uma definição. Fecha oferecendo um quiz interativo |
| `/devteam:health-check` | Diagnóstico da instalação — detecta o provedor ativo (Claude / opencode / Codex), roda 13 verificações (symlinks, scripts, user data, config do provedor, graphify, CLAUDE.md, .gitignore, preferências, notifier, credenciais, artefatos de memória, pré-requisito do Python, ferramentas de produtividade/eficiência de tokens) e aplica correções automáticas seguras. Ele nunca apaga: o que não souber onde colocar vai para `.dev-team-agents/user-data/legacy/<data>/`, e arquivos que acumulam conhecimento são adaptados no lugar, nunca regenerados |
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
| Episódica | `.dev-team-agents/user-data/session-summary.md` | O que aconteceu, em ordem | Expira em ~30 dias |
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

**Verificação de atualização parece travada / não dispara** — a checagem roda uma vez por sessão a partir do `SessionStart` (`scripts/hooks/session-start.sh`), não a cada tool call. Verifique se `.dev-team-agents/user-data/.last-update-check` é um arquivo gravável (não um diretório) e se `session-start.sh` é executável. Os hooks de notifier, telemetria e refresh automático do Graphify estão desativados por padrão no momento — veja `CLAUDE-md/hooks.md` § Disabled Hooks para status e como reativar.

**O `setup-assistant` rodou, mas a seção `## dev-team-agents` está ausente do CLAUDE.md** — diga ao seu CLI: `"Como o setup-assistant, a seção dev-team-agents está faltando no CLAUDE.md — por favor adicione-a."`

**Um agente executou sem apresentar um plano primeiro** — verifique seu CLAUDE.md de projeto por alguma instrução que conflita com o plan mode.

---

## Telemetria Anônima (BETA)

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
