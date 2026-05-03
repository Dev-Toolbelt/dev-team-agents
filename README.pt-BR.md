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

## Instalação — Nível de Projeto

O `dev-team-agents` instala **dentro do seu projeto** em `.claude/`, não globalmente. Isso mantém a configuração de agentes de cada projeto isolada e com versão fixada.

### Instalação em uma linha (versão mais recente)

Execute a partir da **raiz do seu projeto**:

```bash
curl -sSL https://raw.githubusercontent.com/vaironaegos/dev-team-agents/main/scripts/install.sh | bash
```

### Instalar uma versão específica

```bash
curl -sSL https://raw.githubusercontent.com/vaironaegos/dev-team-agents/main/scripts/install.sh | bash -s v1.0.0
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
├── dev-team-agents/   ← repositório clonado (fonte da verdade)
├── agents/
│   └── dev-team/      ← symlink → .claude/dev-team-agents/agents/
├── skills/
│   ├── project-context/   ← symlink → diretório da skill
│   ├── plan-mode/         ← symlink → diretório da skill
│   └── ...                ← um symlink por skill
└── settings.json      ← hook de verificação de atualizações configurado automaticamente
```

---

## Recomendação de .gitignore

Você pode optar por commitar `.claude/dev-team-agents/` (versão fixada, reproduzível) ou ignorá-lo (sempre buscado do zero). Os symlinks de agentes e skills devem seguir a mesma decisão.

```gitignore
# Opção A: ignorar a instalação (cada desenvolvedor instala localmente)
.claude/dev-team-agents/
.claude/agents/dev-team/
.claude/skills/

# Opção B: commitar tudo (versão fixada no repositório)
# (nenhuma entrada necessária — o git vai rastrear)
```

---

## Versionamento

Este repositório usa **versionamento semântico via git tags** (`v1.0.0`, `v1.1.0`, `v2.0.0`).

- Atualizações são lançadas como tags — sem auto-atualização a cada commit
- Um hook de início de sessão verifica novas tags diariamente (configurado automaticamente pelo `scripts/install.sh`)
- Você controla quando atualizar — o sistema apenas notifica, nunca atualiza automaticamente
- Downgrade para qualquer versão: `.claude/dev-team-agents/scripts/install.sh v1.0.0`

---

## Primeiros Passos — Qualquer Projeto

Após instalar, execute o setup-assistant:

```
"Ajude-me a configurar este projeto com dev-team-agents"
```

O `setup-assistant` vai escanear os arquivos existentes, perguntar sobre o tipo de projeto, configurar o `CLAUDE.md` e criar a estrutura de `.claude/docs/`.

---

## Como Usar os Agentes

Os agentes são invocados pelo papel:

```
"Como o product-analyst, analise este PRD: [documento]"
"Como o software-architect, defina a arquitetura para este projeto."
"Como o backend-developer, implemente [tarefa de .claude/docs/backlog/sprint-01.md]"
"Como o code-reviewer, revise as mudanças em [arquivos]."
```

O Claude carregará automaticamente o agente correto com base no papel especificado.

**Cada agente apresenta um plano para aprovação antes de executar qualquer coisa.** Você revisa, ajusta e aprova — depois a execução começa.

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

## Obrigatório: `anthropic-skills:frontend-design`

Os agentes `frontend-developer` e `ui-ux-designer` **requerem** a skill `anthropic-skills:frontend-design`. Ela fornece os padrões de componentes, técnicas de layout e orientação de design visual dos quais esses agentes dependem.

Instale o plugin `anthropic-skills` antes de usar qualquer agente relacionado a UI:

```
/mcp  →  pesquisar "anthropic-skills"  →  instalar
```

O `setup-assistant` irá lembrá-lo de fazer isso durante o setup do projeto.

---

## Estrutura do Repositório

```
dev-team-agents/
├── agents/          ← definições de agentes (arquivos .md)
├── skills/          ← conhecimento modular de skills
│   ├── shared/      ← usadas por múltiplos agentes (project-context, plan-mode, ...)
│   ├── architecture/
│   ├── testing/
│   ├── security/
│   ├── design/
│   └── devops/      ← uma skill por plataforma
├── workflows/       ← guias passo a passo de workflow
├── templates/       ← templates de documentos (plan, backlog, ADR, etc.)
├── scripts/         ← install.sh, check-updates.sh
├── CLAUDE.md        ← convenções de autoria para este repositório
└── CHANGELOG.md
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
