# Referência de Agentes

Lista completa dos agentes incluídos no Dev Team Agents, seus papéis, fases do desenvolvimento e modelos atribuídos.

---

## Time

| Agente | Papel | Fase | Modelo |
|--------|-------|------|--------|
| `product-analyst` | Fecha escopo, gera backlog com estimativas | DISCOVERY | Opus |
| `software-architect` | Decisões de arquitetura, stack tecnológico, padrões de código | DISCOVERY + QUALITY GATE | Opus |
| `backend-developer` | Implementação server-side (API + monolito) | DEVELOPMENT | Sonnet |
| `frontend-developer` | Implementação client-side (SPA + templates) | DEVELOPMENT | Sonnet |
| `mobile-developer` | Implementação mobile (React Native, Expo, Flutter, iOS/Android nativo) | DEVELOPMENT | Sonnet |
| `ui-ux-designer` | Design system, consistência visual, UX (modo duplo) | DESIGN + DEVELOPMENT | Sonnet |
| `database-specialist` | Schema design, otimização de queries, seleção de banco | DEVELOPMENT | Sonnet |
| `devops-specialist` | Docker, CI/CD, VPS, deploy em nuvem | DEVELOPMENT | Sonnet |
| `backend-test-specialist` | Cobertura de testes backend (condicional) | DEVELOPMENT | Sonnet |
| `frontend-test-specialist` | Cobertura de testes frontend (condicional) | DEVELOPMENT | Sonnet |
| `code-reviewer` | Roteia para reviewer especialista com base no diff (backend / frontend / ambos) | QUALITY GATE | Sonnet |
| `backend-reviewer` | Review backend: contratos de API, transações, N+1, auth, jobs, SOLID | QUALITY GATE | Sonnet |
| `frontend-reviewer` | Review frontend: components, re-renders, a11y, bundle, estado, XSS | QUALITY GATE | Sonnet |
| `security-specialist` | OWASP, LGPD/GDPR, CVEs de dependências | QUALITY GATE | Opus |
| `qa-specialist` | Validação comportamental, risco de regressão | QUALITY GATE | Sonnet |
| `technical-writer` | Docs de API, READMEs, runbooks, changelogs | SUPPORT | Haiku |
| `setup-assistant` | Setup do projeto + gerenciamento de versão | SETUP | Sonnet |

---

## Descrições dos Agentes

### `product-analyst`
Responsável pela definição do escopo e geração de backlog. Trabalha diretamente com documentos de requisitos, PRDs ou descrições brutas do usuário. Produz itens de backlog prontos para sprint com estimativas de esforço. Itera por Q&A de clarificação até que o escopo esteja 100% fechado antes de confirmar as estimativas.

### `software-architect`
Dono das decisões de arquitetura, seleção de stack tecnológico e padrões de código. Produz `architecture.md`, `tech-stack.md` e `code-standards.md`. Também atua como quality gate — revisa implementações para conformidade com as decisões estabelecidas. Cria Architecture Decision Records (ADRs) para escolhas difíceis de reverter.

### `backend-developer`
Implementa lógica server-side: REST APIs, serviços monolíticos, background jobs, autenticação e regras de negócio. Lê o contexto do projeto e os padrões de código antes de escrever qualquer código. Pergunta uma vez se deve isolar o trabalho em um git worktree. Delega cobertura de testes ao `backend-test-specialist`.

### `frontend-developer`
Implementa UI client-side: SPAs, templates server-rendered, bibliotecas de componentes. Trabalha em conjunto com `ui-ux-designer` na consistência visual. Lê o stack do projeto e o design system antes de começar. Delega cobertura de testes ao `frontend-test-specialist`.

### `mobile-developer`
Implementa features mobile em React Native, Expo, Flutter e iOS/Android nativo. Adapta-se a padrões específicos de plataforma (HIG para iOS, Material Design para Android). Agente condicional — spawned apenas quando a tarefa envolve escopo mobile.

### `ui-ux-designer`
Opera em dois modos: **modo design** (produz docs de design system, specs de componentes, fluxos de UX) e **modo development** (audita implementação contra o design system e guidelines de interface web). Condicional — spawned quando a tarefa envolve decisões visuais ou de UX.

### `database-specialist`
Responsável por schema design, otimização de queries, estratégia de índices e seleção de banco de dados. Produz arquivos de migration e planos de migração zero-downtime. Condicional — spawned quando a tarefa toca modelos de dados ou infraestrutura de banco.

### `devops-specialist`
Configura Docker (dev e prod), pipelines de CI/CD (GitHub Actions, GitLab CI, Bitbucket, Jenkins), deployments em VPS e infraestrutura em nuvem (AWS, GCP, Azure, Cloudflare). Condicional — spawned quando a tarefa envolve infraestrutura ou deploy.

### `backend-test-specialist`
Escreve e mantém cobertura de testes backend: testes unitários, de integração, de contrato. Executa após o `backend-developer` completar a implementação. Aplica skills de estratégia de testes e pirâmide de testes.

### `frontend-test-specialist`
Escreve e mantém cobertura de testes frontend: testes de componentes, regressão visual, snapshot testing. Executa após o `frontend-developer` completar a implementação.

### `code-reviewer`
Ponto de entrada de roteamento para `/devteam:review`. Lê o diff, classifica o escopo da mudança e delega para `backend-reviewer`, `frontend-reviewer` ou ambos. Sintetiza os resultados em um único veredicto de review.

### `backend-reviewer`
Review profundo de backend: correção de contratos de API, limites de transação, detecção de N+1, autenticação e autorização, segurança de background jobs, princípios SOLID.

### `frontend-reviewer`
Review profundo de frontend: design de componentes, re-renders desnecessários, acessibilidade (a11y), impacto no tamanho do bundle, correção do gerenciamento de estado, superfície de XSS.

### `security-specialist`
Auditoria focada em segurança: OWASP Top 10, conformidade com LGPD/GDPR, scanning de CVEs de dependências, gerenciamento de secrets, risco na cadeia de suprimentos. Executa no quality gate e também como auditoria standalone (`/devteam:security`).

### `qa-specialist`
Valida o comportamento de features contra critérios de aceitação. Identifica risco de regressão, casos de borda ausentes e gaps comportamentais. Não escreve código — produz um relatório de validação comportamental.

### `technical-writer`
Produz documentação de API, READMEs, runbooks, changelogs e release notes. Atribuído ao Haiku para eficiência de custo em tarefas de escrita estruturada e de baixa ambiguidade.

### `setup-assistant`
Conduz o fluxo completo de setup e refresh do projeto. Escaneia arquivos existentes, pergunta sobre o tipo de projeto, coleta configuração e gera documentos de contexto vivos em `.claude/docs/`. Rodar novamente em um projeto existente ativa o modo refresh — lê o histórico git desde a última execução e aplica patches apenas nos docs afetados.

---

## Skills de Design

Duas skills de design são empacotadas e vinculadas automaticamente pelo instalador:

| Skill | Caminho | Propósito |
|-------|---------|-----------|
| `frontend-design` | `skills/design/frontend-design/` | Padrões de componentes, técnicas de layout, orientações de design visual |
| `web-design-guidelines` | `skills/design/web-design-guidelines/` | Audita código de UI contra as Web Interface Guidelines da Vercel |

Ambas são necessárias para `frontend-developer` e `ui-ux-designer` trabalharem em tarefas de UI. Nenhuma configuração adicional é necessária — o instalador as vincula automaticamente.
