# 01 — Referências e Consistência

← [Voltar ao índice](index.md)

**Data:** 2026-05-10
**Escopo:** Quinta passada — drift declarativo entre `CLAUDE.md` e arquivos materiais, community files ausentes em repositório público com instalador via `curl | bash`, e inconsistência pontual de frontmatter em skills.
**Anti-repetição:** Os 110 fingerprints publicados em 2026-05-06 / -07 / -08 / -09 foram excluídos. Cada item abaixo recebe um fingerprint **inédito** para registro em [`_index.md`](../_index.md).

---

## Sumário

As quatro passadas anteriores resolveram a maioria dos itens de superfície (sizes de agentes, README desincronizado, scripts duplicados, frontmatter inconsistente entre agentes). Verificações dos arquivos modificados desde 2026-05-09 confirmam que `LICENSE` e `.github/workflows/ci.yml` foram adicionados — ambos endereçam fingerprints daquela passada.

**Esta passada identifica três classes ainda não cobertas:**

1. **Drift declarativo: `CLAUDE.md` afirma um uso que o código não materializa** — duas skills explicitamente mapeadas em `CLAUDE.md` (`current-context`, `spawn-classifier`) **não são consumidas** pelos arquivos que deveriam consumi-las. Os 22 commands replicam o conteúdo inline em vez de carregar a skill.

2. **Community files ausentes para um repo público com instalação via `curl | bash`** — não há `SECURITY.md` (vulnerability disclosure), `CONTRIBUTING.md`, `CHANGELOG.md`, `PULL_REQUEST_TEMPLATE.md`, `ISSUE_TEMPLATE/`, nem `CODEOWNERS`. Auditorias prévias trataram `LICENSE` e `CI`; estes faltam.

3. **Inconsistência pontual em frontmatter de skill** — entre 99 skills, apenas `worktree/SKILL.md` declara `allowed-tools:`. Não é erro funcional, mas é divergência detectável por linter.

---

## Sugestões

### 1. `current-context` é skill órfã do uso pretendido (declarado em CLAUDE.md, ignorado por 21 commands)

**Fingerprint:** `ref-current-context-skill-orphaned-from-commands`

**Evidência:**

```bash
$ grep -l "current-context" commands/*.md | wc -l
0

$ grep "git branch --show-current" commands/*.md | wc -l
21
```

E em `CLAUDE.md`:

```
| `current-context` | All `/devteam:*` commands — detects branch/worktree state before executing |
```

A skill `skills/shared/current-context/SKILL.md` (29 linhas) define exatamente o protocolo de detecção:

```
| `git branch --show-current` | Identify the active branch |
| `git diff --name-only HEAD` | List locally modified files |
| `git diff --name-only main...HEAD` | List all files changed in this branch vs main |
| Check `.claude/.worktree-session` (if present) | Identify active worktree and its branch |
```

Os 21 commands (`plan.md`, `backend.md`, `frontend.md`, `fullstack.md`, `fix.md`, `refactor.md`, `qa.md`, etc.) começam com **o mesmo bloco em prosa**, reproduzido literalmente:

```markdown
Before acting, identify the current working context:
- Run `git branch --show-current` — active branch
- Run `git diff --name-only HEAD` — locally modified files
- Run `git diff --name-only main...HEAD` — all changes in this branch vs main
- Check `.claude/.worktree-session` if present — active worktree
```

Substituí-lo por uma linha — `Load `skills/shared/current-context/SKILL.md` before acting.` — alinha código e documentação, remove ~150 linhas de prosa duplicada (21 × ~7 linhas), e centraliza evolução do protocolo (ex.: adicionar `git status --short` no futuro requer 1 edição, não 21).

**Impacto positivo:**
- Documentação e implementação convergem (`CLAUDE.md` deixa de mentir);
- Edições futuras do protocolo de contexto têm 1 fonte única;
- Cada command fica ~6 linhas menor;
- Reduz superfície para o agent-lint detectar drift entre `CLAUDE.md` e `commands/`.

**Impacto negativo:**
- Edição em massa de 21 arquivos (mecânica, mas exige diff revisão);
- Usuário lendo um command isoladamente precisa abrir a skill para entender o que faz (mitigado pelo descritor da skill ser específico).

**Esforço:** Médio (21 substituições). Pode ser script: `sed` em bloco delimitado por `\---\n`.

---

### 2. `spawn-classifier` declarada para `/devteam:plan` mas carregada apenas por `software-architect`

**Fingerprint:** `ref-spawn-classifier-skill-only-software-architect`

**Evidência:**

`CLAUDE.md`:

```
| `spawn-classifier` | `/devteam:plan` and multi-agent commands — decides conditional agent spawn |
```

Mas:

```bash
$ grep -rl "spawn-classifier" agents/ commands/
agents/software-architect.md
```

`commands/plan.md` não menciona a skill. Ele lista agentes para spawn e diz "Also spawn if the task involves backend code", mas a lógica de classificação textual está embutida em prosa, não delegada à skill.

A skill `skills/shared/spawn-classifier/SKILL.md` (89 linhas) contém heurísticas para decidir spawn condicional — exatamente o que `commands/plan.md` faz informalmente. Em vez de duas verdades (skill + prosa do command), uma só:

```markdown
## Conditional spawn
Load `skills/shared/spawn-classifier/SKILL.md` and apply its decision tree
to the task described in $ARGUMENTS to determine which optional agents
to invoke alongside the always-spawned trio.
```

**Impacto positivo:**
- Heurística única para classificação;
- `commands/plan.md`, `commands/fullstack.md`, `commands/fix.md` (multi-agent) podem compartilhar a mesma fonte;
- Permite testar a classificação em isolado.

**Impacto negativo:**
- Skill atualmente está orientada a software-architect — pode precisar generalizar antes da extração;
- Risco de "skill é overkill para o command" se a lógica for trivial (mitigado: lógica condicional já é não-trivial em `plan.md`).

**Esforço:** Médio (revisar SKILL.md para garantir generalidade; substituir em `plan.md`).

---

### 3. Sem `SECURITY.md` em repositório público com instalador via `curl | bash`

**Fingerprint:** `ref-no-security-md`

**Evidência:**

```bash
$ ls SECURITY*
ls: cannot access 'SECURITY*': No such file or directory
```

Em `README.md`:

```
curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh | bash
```

Repositórios públicos cujo método de instalação primário é executar um shell script remoto **precisam** de canal explícito para vulnerability disclosure responsável. Sem `SECURITY.md`, um pesquisador que descubra:
- Path traversal no installer;
- Comportamento de DNS rebinding em `HTTP_GET`;
- Possibilidade de inject em hooks;

não sabe para onde reportar. Issue público é o pior caminho (expõe antes de patch).

**Conteúdo mínimo:**

```markdown
# Security Policy

## Supported Versions
| Version | Supported |
|---------|-----------|
| 1.x     | ✅        |
| < 1.0   | ❌        |

## Reporting a Vulnerability
Please report vulnerabilities privately to **<email>**.
Do not open public issues for security problems.

Expected response time: 72 hours.
```

GitHub também usa este arquivo para mostrar o link "Security" no header do repo.

**Impacto positivo:**
- Canal responsável para disclosure;
- Bom selo de qualidade ("OpenSSF best practices");
- Permite habilitar Private Vulnerability Reporting no GitHub.

**Impacto negativo:**
- Compromisso de responder em 72h.

**Esforço:** Baixo.

---

### 4. Sem `CONTRIBUTING.md` apesar de regras detalhadas em `CLAUDE.md`

**Fingerprint:** `ref-no-contributing-md`

**Evidência:**

```bash
$ ls CONTRIBUTING*
ls: cannot access 'CONTRIBUTING*': No such file or directory
```

`CLAUDE.md` contém ~270 linhas com regras de autoria: padrão de frontmatter, limite de 200 linhas/agente, regra do Plan Mode, README sync, Auto-Docs, language policy, hooks de session-summary, ADR triggers, etc. Esse conteúdo é estruturalmente um `CONTRIBUTING.md`, mas:

- `CLAUDE.md` é orientado a Claude (segunda pessoa, "you must");
- Contribuintes humanos precisam de uma versão mais navegável, com tabela de comandos para rodar localmente, processo de PR, branch naming, etc.

A separação:
- **`CLAUDE.md`** — instruções para o agente (permanece como está);
- **`CONTRIBUTING.md`** — instruções para humanos contribuindo (link para `CLAUDE.md` como referência para alinhamento com agentes).

**Impacto positivo:**
- GitHub mostra link de "Contributing" no PR template;
- Onboarding humano vs. onboarding de Claude separados;
- Permite checklist específico de humano (assinar commits, rebase strategy, etc.).

**Impacto negativo:**
- Mais um arquivo para sincronizar com `CLAUDE.md` (mitigado: linkar em vez de duplicar).

**Esforço:** Médio.

---

### 5. Sem `CHANGELOG.md` apesar de versionamento semântico

**Fingerprint:** `ref-no-changelog-md`

**Evidência:**

```bash
$ ls CHANGELOG*
ls: cannot access 'CHANGELOG*': No such file or directory

$ git tag | head -3
v1.0.0
v1.1.0
v1.2.0
```

`CLAUDE.md` define a política de versionamento:

```
- Semantic versioning via git tags: `v1.0.0`, `v1.1.0`, `v2.0.0`
- Breaking changes ... → major version bump
- New agents/skills → minor version bump
- Fixes, clarifications → patch bump
```

Mas não há `CHANGELOG.md` no formato [Keep a Changelog](https://keepachangelog.com/). O hook `01-check-updates.sh` referencia o changelog:

```
echo "│  See .dev-team-agents/CHANGELOG.md for details.      │"
```

— mas o arquivo não existe no instalável (e a comparação para `RESOLVED != CURRENT` não tem human-readable diff).

**Impacto positivo:**
- Notificação "update available" passa a apontar para release notes reais;
- GitHub releases podem ser geradas automaticamente a partir do CHANGELOG;
- Conventional Commits + `git cliff` permite geração automática.

**Impacto negativo:**
- Manutenção entre lançamentos (mitigado por `git cliff`/`release-please`).

**Esforço:** Médio (criar arquivo + sync com tags existentes + processo para próximas releases).

---

### 6. Sem `PULL_REQUEST_TEMPLATE.md` e `ISSUE_TEMPLATE/`

**Fingerprint:** `ref-no-pr-and-issue-templates`

**Evidência:**

```bash
$ ls .github
workflows
```

Falta:
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`
- `.github/ISSUE_TEMPLATE/skill_request.md` (específico do projeto)

O command `/devteam:pr` produz um PR body usando o `technical-writer`, mas sem template **GitHub não substitui automaticamente** — o agente gera prosa, GitHub não impõe estrutura. Um template no repo:
- Garante seções fixas (Description, Testing, Checklist);
- Permite checklist de "actualizei `README.pt-BR.md`?", "rodei `agent-lint.sh`?";
- O `technical-writer` pode **detectar e respeitar** o template.

**Impacto positivo:**
- Qualidade de contribuições externas;
- Possibilita `/devteam:pr` ler e preencher o template do projeto;
- Reduz revisões de "esqueceu de testar".

**Impacto negativo:**
- Maintainer-only PRs ainda têm overhead mínimo.

**Esforço:** Médio.

---

### 7. Sem `.github/CODEOWNERS`

**Fingerprint:** `ref-no-codeowners-file`

**Evidência:**

```bash
$ cat .github/CODEOWNERS
cat: .github/CODEOWNERS: No such file or directory
```

Embora seja um projeto único-mantenedor hoje, codificar ownership por path:

```
agents/                   @Dev-Toolbelt/maintainers
skills/shared/            @Dev-Toolbelt/maintainers
skills/devops/            @Dev-Toolbelt/devops-leads
scripts/                  @Dev-Toolbelt/maintainers
docs/reports/             # auto-generated; no required reviewer
```

permite:
- Auto-request review baseado em path;
- Documentar quem decide o quê;
- Proteger paths críticos via branch protection rules.

**Impacto positivo:**
- Suporte para crescimento do time;
- Documentação implícita de áreas de responsabilidade.

**Impacto negativo:**
- Em time único, pouco valor imediato (mitigado: investimento barato, retorna quando time crescer).

**Esforço:** Baixo.

---

### 8. `worktree/SKILL.md` é a única skill com `allowed-tools:` em frontmatter

**Fingerprint:** `ref-skill-frontmatter-allowed-tools-key-inconsistency`

**Evidência:**

```bash
$ find skills -name "SKILL.md" -exec grep -l "^allowed-tools:" {} \;
skills/shared/worktree/SKILL.md
```

Frontmatter atual:

```yaml
---
name: worktree
description: Git worktree per task ...
allowed-tools: Bash, Read
---
```

Entre 99 skills, nenhuma outra declara `allowed-tools:`. O CLAUDE.md de autoring diz:

> Skills (`skills/**/*.md`)
> - Frontmatter: `name`, `description`

Sem mencionar `allowed-tools:`. Duas possibilidades:

(a) `allowed-tools:` é semântica oficial do Claude Code SDK e a documentação de autoring está incompleta — então padronizar **adicionando** em todas as skills relevantes;

(b) `allowed-tools:` é redundante e foi um experimento — remover de `worktree/SKILL.md` para uniformizar.

A decisão precisa ser explícita na documentação. Hoje, um contribuinte tem evidência ambígua.

**Impacto positivo:**
- Frontmatter validável (`scripts/orphan-skill-scan.sh` ou um novo `skill-lint.sh` poderia checar);
- Decisão documentada elimina perguntas futuras.

**Impacto negativo:**
- Se (a) for o caso, são 99 skills para atualizar (alto esforço).
- Se (b), trivial.

**Esforço:** Baixo (decisão) + Trivial-Alto (execução).

---

### 9. Ordem dos sub-scripts do `Stop` dispatcher não documentada

**Fingerprint:** `ref-stop-hook-shim-numbering-undocumented`

**Evidência:**

```bash
$ ls scripts/hooks/stop/
01-session-summary.sh
02-orphan-skill-scan.sh
03-agent-lint.sh
```

`scripts/hooks/stop.sh` (o dispatcher) processa por ordem alfabética. **O significado de `01/02/03` não está documentado em CLAUDE.md.**

Cenários problemáticos:
- Contribuinte adiciona `02-format-check.sh`, sem perceber que `02-orphan-skill-scan.sh` já existe → colisão silenciosa (alfabética → ambiguidade);
- Contribuinte adiciona `00-pre-check.sh` para rodar antes de tudo — atualmente funciona, mas comportamento não é documentado;
- Não é claro se a ordem é **importante** (resultado de `01` afeta `02`?) ou apenas estética.

**Mínimo:**

```markdown
### Stop hook dispatcher

Sub-scripts em `scripts/hooks/stop/` são executados pela ordem alfabética
do filename. Prefixo numérico de 2 dígitos (`01-`, `02-`, etc.) controla
a ordem. Convenções:

- `00-` reservado para precondições (não usar em release atual)
- `01-`: detecção/coleta de estado da sessão (session-summary)
- `02-`: integridade do repositório (orphan-skill-scan)
- `03-`: validações estáticas (agent-lint)
- `99-`: tarefas finais (não usado atualmente)

Cada sub-script deve aceitar `--quiet` e sair com código 0 quando tudo OK.
```

**Impacto positivo:**
- Convenção previsível para contribuintes;
- Permite testar sub-scripts em isolado;
- Garante que próximas adições não criem ambiguidade.

**Impacto negativo:**
- Nenhum.

**Esforço:** Baixo (≤30 linhas em CLAUDE.md).

---

## Resumo dos Fingerprints

| # | Fingerprint | Categoria | Esforço |
|---|------------|-----------|---------|
| 1 | `ref-current-context-skill-orphaned-from-commands` | Drift CLAUDE.md ↔ commands | Médio |
| 2 | `ref-spawn-classifier-skill-only-software-architect` | Drift CLAUDE.md ↔ commands | Médio |
| 3 | `ref-no-security-md` | Community files | Baixo |
| 4 | `ref-no-contributing-md` | Community files | Médio |
| 5 | `ref-no-changelog-md` | Community files | Médio |
| 6 | `ref-no-pr-and-issue-templates` | Community files | Médio |
| 7 | `ref-no-codeowners-file` | Community files | Baixo |
| 8 | `ref-skill-frontmatter-allowed-tools-key-inconsistency` | Frontmatter de skills | Baixo |
| 9 | `ref-stop-hook-shim-numbering-undocumented` | Documentação de convenção | Baixo |

---

← [Voltar ao índice](index.md) · [Próxima seção →](02-fluxos-e-workflows.md)
