# dev-team-agents

🇺🇸 [See the English Version](README.md)

Um time global de agentes Claude Code especializados para desenvolvimento de software. Agnóstico a tecnologia, ciente do contexto do projeto e mantido colaborativamente.

---

## O que é isso

Um conjunto de agentes e skills do Claude Code que formam um time completo de desenvolvimento de software. Cada agente tem um papel definido, expertise e integração com workflows. Eles coexistem com as regras do seu projeto — as convenções do projeto sempre prevalecem.

**Time:**

| Agente | Papel | Fase | Modelo |
|--------|-------|------|--------|
| `product-analyst` | Fecha escopo, gera backlog com estimativas | DISCOVERY | Opus |
| `software-architect` | Decisões de arquitetura, tech stack, padrões | DISCOVERY + QUALITY GATE | Opus |
| `backend-developer` | Implementação server-side (API + monolith) | DEVELOPMENT | Sonnet |
| `frontend-developer` | Implementação client-side (SPA + templates) | DEVELOPMENT | Sonnet |
| `ui-ux-designer` | Design system, consistência visual, UX (modo duplo) | DESIGN + DEVELOPMENT | Sonnet |
| `database-specialist` | Schema, otimização de queries, seleção de BD | DEVELOPMENT | Sonnet |
| `devops-specialist` | Docker, CI/CD, VPS, deploy em nuvem | DEVELOPMENT | Sonnet |
| `backend-test-specialist` | Cobertura de testes backend (condicional) | DEVELOPMENT | Sonnet |
| `frontend-test-specialist` | Cobertura de testes frontend (condicional) | DEVELOPMENT | Sonnet |
| `code-reviewer` | Qualidade de código, padrões, lint, bugs | QUALITY GATE | Sonnet |
| `security-specialist` | OWASP, LGPD/GDPR, CVEs de dependências | QUALITY GATE | Opus |
| `qa-specialist` | Validação comportamental, risco de regressão | QUALITY GATE | Sonnet |
| `technical-writer` | Docs de API, READMEs, runbooks, changelogs | SUPPORT | Haiku |
| `setup-assistant` | Setup do projeto + gerenciamento de versão | SETUP | Sonnet |

---

## Pré-requisitos

- **Claude Code** — CLI, app desktop ou extensão de IDE. Instale em [claude.ai/code](https://claude.ai/code) se ainda não disponível.
- **Git** — o instalador usa `git rev-parse` para verificar a raiz do projeto.
- **curl** ou **wget** — utilizado para baixar o tarball de release. Um dos dois geralmente já está disponível no sistema.

Nenhuma outra dependência global é necessária.

---

## Instalação — Nível de Projeto

O `dev-team-agents` instala **dentro do seu projeto** em `.claude/`, não globalmente. Isso mantém a configuração de agentes de cada projeto isolada e com versão fixada.

### Instalação em uma linha (versão mais recente)

Execute a partir da **raiz do seu projeto**:

```bash
curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh | bash
```

### Instalar uma versão específica

```bash
curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh | bash -s v1.0.0
```

### Atualizar para a versão mais recente (após a primeira instalação)

```bash
.claude/dev-team-agents/scripts/install.sh latest
```

### Fixar em uma versão específica / fazer downgrade

```bash
.claude/dev-team-agents/scripts/install.sh v1.0.0
```

Após a instalação, `.claude/` conterá:

```
.claude/
├── dev-team-agents/   ← extraído de tarball (sem pasta .git — seguro para commitar)
├── agents/
│   └── dev-team/      ← symlink → .claude/dev-team-agents/agents/
├── skills/
│   ├── project-context/   ← symlink → diretório da skill
│   ├── plan-mode/         ← symlink → diretório da skill
│   └── ...                ← um symlink por skill
└── settings.json      ← hook de verificação de atualizações configurado automaticamente
```

---

## Commitando no Seu Projeto

Como o `install.sh` baixa um tarball (não faz git clone), `.claude/dev-team-agents/` não contém nenhuma pasta `.git` aninhada. **Commite diretamente** — todo o time recebe os agentes e skills no `git pull`, sem passo de setup adicional.

```bash
git add .claude/dev-team-agents/ .claude/agents/ .claude/skills/ .claude/settings.json
git commit -m "chore: add dev-team-agents"
```

Se preferir que cada desenvolvedor instale localmente (ex.: setup pessoal/experimental), adicione ao `.gitignore`:

```gitignore
# Opcional: ignorar a instalação (cada desenvolvedor instala localmente)
.claude/dev-team-agents/
.claude/agents/dev-team/
.claude/skills/

# Sempre ignore o arquivo efêmero de sessão worktree
.claude/.worktree-session
```

---

## Experimento Rápido

Se quiser testar um agente antes de rodar o setup completo, você pode invocar qualquer agente diretamente após a instalação:

```
"Como o code-reviewer, revise o arquivo src/api/users.ts e aponte problemas."
"Como o software-architect, explique a arquitetura de alto nível deste codebase."
"Como o backend-developer, qual seria a forma mais limpa de adicionar paginação a este endpoint?"
```

Nenhuma configuração adicional é necessária — os agentes leem os arquivos do projeto e aplicam seu papel. O fluxo completo com o `setup-assistant` é recomendado para uso contínuo em equipe, mas não há setup obrigatório antes da primeira invocação de um agente.

---

## Versionamento

Este repositório usa **versionamento semântico via git tags** (`v1.0.0`, `v1.1.0`, `v2.0.0`).

- Atualizações são lançadas como tags — sem auto-atualização a cada commit
- Um hook verifica novas versões diariamente via GitHub API (configurado automaticamente pelo `scripts/install.sh`)
- Você controla quando atualizar — o sistema apenas notifica, nunca atualiza automaticamente
- Downgrade para qualquer versão: `.claude/dev-team-agents/scripts/install.sh v1.0.0`

---

## Primeiros Passos — Qualquer Projeto

Após instalar, inicie o fluxo de setup dizendo ao Claude:

```
"Ajude-me a configurar este projeto com dev-team-agents"
```

O `setup-assistant` irá:

1. **Escanear** os arquivos existentes — README, CLAUDE.md, manifestos de pacotes, histórico git — e resumir o que encontrou, incluindo a versão instalada
2. **Perguntar** qual tipo de projeto é este: novo do zero, herdado/inacabado, ou manutenção de sistema em produção
3. **Coletar** a configuração em uma única troca: testes necessários, plataforma de CI/CD, provedor de nuvem, issue tracker
4. **Apresentar um plano** para sua aprovação antes de criar ou modificar qualquer coisa
5. **Criar** a estrutura de diretórios `.claude/docs/` e acrescentar uma seção `## dev-team-agents` ao `CLAUDE.md`
6. **Confirmar** o que foi configurado e indicar o workflow relevante

O setup completo tipicamente leva de 5 a 10 minutos.

---

## Skill `frontend-design` (Necessária para trabalho com UI)

Os agentes `frontend-developer` e `ui-ux-designer` requerem a skill `frontend-design` do marketplace do Claude Code.

**O `scripts/install.sh` faz o link automaticamente** a partir do cache do marketplace — nenhum passo extra é necessário se você já a instalou antes.

Se o instalador exibir um aviso de que a skill não foi encontrada:

1. Abra o Claude Code
2. Execute `/plugins` → pesquise `frontend-design` → instale
3. Rode o instalador novamente: `.claude/dev-team-agents/scripts/install.sh latest`

A skill fornece padrões de componentes, técnicas de layout e orientação de design visual utilizada por ambos os agentes.

---

## Como Usar os Agentes

Os agentes são invocados pelo papel no seu prompt para o Claude:

```
"Como o product-analyst, analise este PRD: [documento]"
"Como o software-architect, defina a arquitetura para este projeto."
"Como o backend-developer, implemente [tarefa de .claude/docs/backlog/sprint-01.md]"
"Como o code-reviewer, revise as mudanças em [arquivos]."
```

Isso funciona no CLI do Claude Code (`claude`), no app desktop, no app web em [claude.ai/code](https://claude.ai/code) e em extensões de IDE (VS Code, JetBrains).

**Cada agente apresenta um plano para aprovação antes de executar qualquer coisa.** Você revisa, ajusta e aprova — depois a execução começa. Nenhum agente escreve arquivos ou executa comandos até você confirmar.

Se um agente não for reconhecido, verifique se `.claude/agents/dev-team/` existe e contém os arquivos `.md` dos agentes. Rode o instalador novamente se o symlink estiver ausente ou quebrado.

---

## Isolamento com Worktree

Todos os agentes de codificação (`backend-developer`, `frontend-developer`, `database-specialist`, `devops-specialist`, `ui-ux-designer`, `backend-test-specialist`, `frontend-test-specialist`) perguntam **uma única vez** antes de editar qualquer arquivo:

> "Do you want this task isolated in a git worktree? [y/N]"

**A resposta é compartilhada entre todos os agentes da mesma task** via `.claude/.worktree-session`. Se um workflow envolver múltiplos agentes (ex.: backend + frontend + testes), apenas o primeiro agente pergunta — os demais leem a decisão gravada silenciosamente.

| Resposta | Comportamento |
|----------|--------------|
| Sim | O agente pergunta a branch base (padrão: `main`), cria `.worktrees/<ctx>/<title>/`, e todo o trabalho subsequente ocorre dentro dele |
| Não | Todos os agentes trabalham na branch corrente |

O arquivo de sessão é removido automaticamente quando o worktree é limpo (Step 8 da skill worktree). Adicione ao `.gitignore` — a skill faz isso automaticamente no cleanup:

```gitignore
.claude/.worktree-session
```

---

## Idioma

**Todos os documentos gerados estão em inglês por padrão.** Para solicitar um documento específico em outro idioma, diga explicitamente para aquele documento. O padrão sempre volta para o inglês.

---

## Workflows

| Workflow | Arquivo | Use quando |
|----------|---------|------------|
| Novo projeto | `workflows/new-project.md` | Começando do zero |
| Projeto herdado | `workflows/inherited-project.md` | Assumindo trabalho inacabado |
| Manutenção | `workflows/maintenance.md` | Projeto em produção, tarefas contínuas |
| Correção de bug | `workflows/bug-fix.md` | Bug isolado |
| Patch de segurança | `workflows/security-patch.md` | Vulnerabilidade de segurança |

### A — Novo Projeto do Zero

```
  [Entrada: documento de requisitos]
               │
               ▼
  ┌────────────────────────────┐
  │         DISCOVERY          │
  │                            │
  │  product-analyst           │
  │    · fecha escopo          │
  │    · gera backlog          │
  │    · estimativas de sprint │
  │                            │
  │  software-architect        │
  │    · architecture.md       │
  │    · tech-stack.md         │
  │    · code-standards.md     │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │    DESIGN  (opcional)      │
  │                            │
  │  ui-ux-designer            │
  │    · design-system.md      │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │        DEVELOPMENT         │
  │                            │
  │  devops-specialist         │
  │    · ambiente de dev       │
  │  backend-developer         │
  │    · implementa tarefas    │
  │  frontend-developer        │
  │    · implementa UI         │
  │  database-specialist       │
  │    · schema + migrations   │
  │  [test-specialists]        │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │       QUALITY GATE         │
  │                            │
  │  code-reviewer             │
  │  security-specialist       │
  │  qa-specialist             │
  │  software-architect        │
  │    · conformance check     │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │           SHIP             │
  │                            │
  │  technical-writer          │
  │    · changelog + docs      │
  └────────────────────────────┘
```

### B — Projeto Herdado / Inacabado

```
  [Entrada: codebase + lista de tarefas do cliente]
               │
               ▼
  ┌────────────────────────────┐
  │          AUDIT             │
  │                            │
  │  software-architect        │
  │    · auditoria arquitetural│
  │    · mapeamento de débito  │
  │  database-specialist       │
  │    · auditoria de schema   │
  │  security-specialist       │
  │    · findings críticos     │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │      CLIENT SCOPING        │
  │                            │
  │  product-analyst           │
  │    · Q&A de clarificação   │
  │    · itera até o escopo    │
  │      estar 100% fechado    │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │       GAP ANALYSIS         │
  │                            │
  │  product-analyst           │
  │    · backlog completo      │
  │    · previsão de entrega   │
  │  software-architect        │
  │    · refatorar vs reescrever│
  └─────────────┬──────────────┘
                │
                ▼
     DEVELOPMENT + QUALITY GATE
        (igual ao Workflow A)
```

### C — Manutenção / Projeto em Produção

```
  [Entrada: ticket do board]
               │
               ▼
  ┌────────────────────────────┐
  │       TASK PICKUP          │
  │                            │
  │  software-architect        │
  │    · carrega contexto      │
  │    · análise de blast radius│
  │    · sinaliza riscos legacy│
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │    SCOPE VALIDATION        │
  │       (recomendado)        │
  │                            │
  │  product-analyst           │
  │    · valida critérios de   │
  │      aceite                │
  │    · resolve ambiguidades  │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │       DEVELOPMENT          │
  │                            │
  │  backend-developer         │
  │  frontend-developer        │
  │    · escopo mínimo         │
  │    · sem refatorações      │
  │      silenciosas           │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │  QUALITY GATE              │
  │  (foco em regressão)       │
  │                            │
  │  code-reviewer             │
  │  qa-specialist             │
  │  [security-specialist]     │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │       PR + DEPLOY          │
  │                            │
  │  technical-writer          │
  │  devops-specialist         │
  └────────────────────────────┘
```

### Correção de Bug

```
  [Entrada: bug report / stack trace]
               │
               ▼
  ┌────────────────────────────┐
  │        DIAGNOSIS           │
  │                            │
  │  software-architect        │
  │    · análise de causa raiz │
  │    · relatório de diagnóstico│
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │           FIX              │
  │                            │
  │  backend-developer  ou     │
  │  frontend-developer        │
  │    · corrige causa raiz    │
  │    · sem mudanças extras   │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │    REGRESSION CHECK        │
  │                            │
  │  qa-specialist             │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │      CODE REVIEW           │
  │                            │
  │  code-reviewer             │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │   REGRESSION TEST          │
  │    (se necessário)         │
  │                            │
  │  backend-test-specialist   │
  │  frontend-test-specialist  │
  └────────────────────────────┘
```

### Patch de Segurança

```
  [Entrada: CVE / finding de segurança]
               │
               ▼
  ┌────────────────────────────┐
  │     ASSESS SEVERITY        │
  │                            │
  │  security-specialist       │
  │    · CVSS score            │
  │    · superfície de ataque  │
  │    · evidência de exploração│
  └─────────────┬──────────────┘
                │
        ┌───────┴────────┐
        │   CRÍTICO?     │
        └──┬─────────────┘
      sim  │         não │
       ▼                 │
  escalar +              │
  notificar              │
  stakeholders           │
           └─────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │          PATCH             │
  │                            │
  │  backend-developer         │
  │    · correção mínima       │
  │  devops-specialist         │
  │    · upgrade de dependência│
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │    SECURITY REVIEW         │
  │                            │
  │  security-specialist       │
  │    · verifica o patch      │
  │    · nenhum novo vetor     │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │    CODE REVIEW + QA        │
  │                            │
  │  code-reviewer             │
  │  qa-specialist             │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │         DEPLOY             │
  │                            │
  │  devops-specialist         │
  │    · estratégia mais rápida│
  │      e segura              │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │      POST-INCIDENT         │
  │                            │
  │  technical-writer          │
  │    · security-incidents.md │
  └────────────────────────────┘
```

---

## Coexistência — Regras do Projeto Sobrepõem a Base

Estes agentes são uma **camada base**. As convenções do seu próprio projeto sempre têm precedência:

- `CLAUDE.md` → maior prioridade — regras específicas do Claude para o projeto
- `AGENTS.md` → overrides de agentes específicos do projeto
- `README.md` → setup e convenções do projeto
- `.agents/<agent-name>.md` → override de agente por projeto

**Se seu projeto diz usar tabs, os agentes usam tabs. Se seu projeto define um padrão específico, os agentes o seguem. Os padrões base apenas preenchem as lacunas.**

---

## Personalizando para um Projeto

**Não** modifique arquivos dentro de `.claude/dev-team-agents/` — eles serão sobrescritos na atualização.

Em vez disso, faça o override no nível do projeto:

```bash
# Override de agente no nível do projeto (tem precedência sobre o agente base)
.agents/backend-developer.md

# Regras no nível do projeto para todos os agentes
CLAUDE.md  # adicione uma seção ## Project Rules

# Padrões de código específicos do projeto (usados pelo code-reviewer e developers)
.claude/docs/development/code-standards.md
```

---

## Solução de Problemas

**Agentes não são reconhecidos pelo Claude**
Verifique se o symlink existe: `ls .claude/agents/dev-team/`. Se o diretório estiver faltando, rode o instalador novamente a partir da raiz do projeto.

**Skills não são carregadas**
Verifique se `.claude/skills/` contém symlinks apontando para cada diretório de skill. Rode o instalador para restaurar links quebrados: `.claude/dev-team-agents/scripts/install.sh latest`.

**Skill `frontend-design` não encontrada**
A skill não está no cache do marketplace nesta máquina. Abra o Claude Code → `/plugins` → pesquise `frontend-design` → instale. Depois rode o instalador novamente.

**Hook de verificação de atualização dispara a cada tool call**
O hook lê um arquivo de timestamp e só exibe uma mensagem uma vez por dia. Se estiver imprimindo sempre, verifique se `.claude/dev-team-agents/.last-update-check` é um arquivo gravável (não um diretório) e se `check-updates.sh` é executável.

**O `setup-assistant` rodou, mas a seção `## dev-team-agents` está ausente do CLAUDE.md**
O assistente acrescenta ao arquivo existente — nunca substitui o conteúdo. Pesquise por `## dev-team-agents` no seu CLAUDE.md. Se estiver ausente, diga ao Claude: `"Como o setup-assistant, a seção dev-team-agents está faltando no CLAUDE.md — por favor adicione-a."`

**Um agente executou sem apresentar um plano primeiro**
Todo agente é configurado para apresentar um plano antes de agir. Se isso não aconteceu, seu CLAUDE.md de projeto pode conter uma regra que conflita com o requisito de plano. Verifique se há alguma instrução que desativa o plan mode.

---

## Estrutura do Repositório

```
dev-team-agents/
├── agents/          ← definições de agentes (arquivos .md)
├── skills/          ← conhecimento modular de skills
│   ├── shared/      ← usadas por múltiplos agentes (project-context, plan-mode, adr, comments-policy, conventional-commits, pr-review, backlog-template, worktree)
│   ├── architecture/ ← api-design, async-jobs, design-patterns, graphql, object-calisthenics
│   ├── testing/     ← test-strategy, test-pyramid
│   ├── security/    ← security-checklist
│   ├── design/      ← design-system-audit
│   ├── devops/      ← docker-dev, docker-prod, vps-linux, cicd-github, cicd-gitlab, cicd-bitbucket, cicd-jenkins, aws, gcp, azure, cloudflare, iac-terraform, monitoring
│   ├── integrations/ ← supabase, gotrue, jwt, kong, realtime, database-debug, database-multitenancy, database-production, pwa, offline-first
│   └── ui-libraries/ ← shadcn, mui, antd, bootstrap, chakra-ui, jquery
├── workflows/       ← guias passo a passo de workflow
├── templates/       ← templates de documentos (plan, backlog, ADR, etc.)
├── scripts/         ← install.sh, check-updates.sh
└── CLAUDE.md        ← convenções de autoria para este repositório
```

---

## Contribuindo

1. Faça um fork do repositório
2. Crie uma branch: `fix/agent-name-improvement` ou `feat/new-skill`
3. Siga os padrões de autoria em `CLAUDE.md`
4. Abra um PR com uma descrição clara do que mudou e por quê
5. Os releases são tagueados pelos mantenedores — sua mudança vai no próximo lançamento

---

## Licença

MIT
