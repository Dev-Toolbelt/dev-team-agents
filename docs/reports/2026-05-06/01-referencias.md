# 1. Verificação de Referências (Skills e Agentes)

← [Voltar ao índice](index.md)

---

## 1.1 Resultado consolidado

| Verificação | Resultado |
|-------------|-----------|
| `orphan-skill-scan.sh` (modo full) | `clean ✓` |
| Skills no filesystem (com `SKILL.md`) | 65 |
| Skills referenciados por path em `agents/` | 62 |
| Skills citados apenas pelo nome (ex.: `security-checklist`) | 3 |
| Agentes com frontmatter válido | 16/16 |
| Slash commands existentes em `commands/` | 22 |

## 1.2 Pontos de atenção encontrados

### A. Inconsistência de localização entre `skill-creator` e `agent-creator`

- `skills/skill-creator/SKILL.md` — **dentro do pacote** distribuído, segue o padrão dos demais skills.
- `.claude/skills/agent-creator/SKILL.md` — **fora do pacote**, vive na pasta `.claude/skills` do próprio repo.

`CLAUDE.md` registra ambos na tabela "User-Invocable Skills", mas as localizações
divergem. O `agent-creator`, por morar em `.claude/skills/`, **não é distribuído**
quando outro projeto faz `curl install.sh`. Isso é coerente com o comentário do próprio
`agent-creator.md` ("it does not get distributed to target projects"), porém o usuário
final não tem como saber pela tabela do `CLAUDE.md`.

> **Fingerprint:** `ref-agent-creator-location`

**Recomendação:** Adicionar uma coluna "Distribuído?" na tabela User-Invocable Skills
do `CLAUDE.md`, ou marcar `agent-creator` com um sufixo `(repo-only)`.

### B. README desatualizado em relação à árvore real de skills

A seção "Repository Structure" do `README.md` (e do `README.pt-BR.md` por simetria)
descreve as skills com listas reduzidas que não refletem o estado atual.

| Pasta | README diz | Real (em disco) |
|-------|------------|-----------------|
| `skills/architecture/` | api-design, async-jobs, design-patterns, graphql, object-calisthenics | **+** accessibility-patterns, component-patterns, css-quality, form-handling, naming-conventions, state-management |
| `skills/devops/` | docker-dev, docker-prod, vps-linux, cicd-*, aws, gcp, azure, cloudflare, iac-terraform, monitoring | **+** vercel, sentry, sonarqube, graphify-setup |
| `skills/design/` | design-system-audit | **+** frontend-design, web-design-guidelines |

> **Fingerprints:** `docs-sync-readme-architecture-skills`, `docs-sync-readme-devops-skills`, `docs-sync-readme-design-skills`

**Impacto positivo da correção:** alinha a regra "README Sync Rule" do próprio
`CLAUDE.md`; ajuda usuários a descobrirem skills existentes sem ter que `ls` no diretório.
**Impacto negativo:** a seção fica mais longa (≈ 12 linhas a mais em cada README); pode
ser mitigado movendo a árvore para uma seção colapsável (`<details>`).

### C. Workflow inexistente para o slash command `/devteam:fullstack`

Em `commands/fullstack.md` o comando dispara backend + frontend, mas não há
`workflows/fullstack.md` correspondente. Os outros comandos `/devteam:workflow-*`
fazem `Load and follow workflows/<file>.md`; aqui falta peer.

> **Fingerprint:** `flow-fullstack-no-workflow-doc`

**Recomendação:** Criar `workflows/fullstack.md` ou referenciar explicitamente os
workflows de bug-fix/maintenance dependendo do contexto.

### D. Falta um slash command para invocar o `setup-assistant`

O setup hoje é disparado apenas por intenção em linguagem natural (gatilhos descritos
no `CLAUDE.md § Setup Trigger`). A descoberta seria mais simples com um
`/devteam:setup` análogo aos demais.

> **Fingerprint:** `flow-setup-slash-command`
