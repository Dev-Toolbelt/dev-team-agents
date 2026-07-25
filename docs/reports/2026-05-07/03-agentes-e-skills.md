# 3. Agentes e Skills (Modelo, Templates, Cobertura)

← [Voltar ao índice](index.md)

Esta seção foca em **decisões de modelo**, lacunas de **templates físicos vs templates implícitos em skills**, e clarificações sobre cobertura de skills cuja relação ainda não havia sido analisada.

---

## 3.1 `setup-assistant` está em Sonnet, mas executa decisões de Opus

`agents/setup-assistant.md` linha 4 declara `model: claude-sonnet-4-6`.

A regra do `CLAUDE.md` (linha 62) diz:

> Model assignment: `claude-opus-4-7` (decision-making), `claude-sonnet-4-6` (execution), `claude-haiku-4-5-20251001` (structured output)

O `setup-assistant` é **o primeiro contato** do projeto com o ecossistema. Ele decide:

- Qual o tipo de projeto (`new` / `inherited` / `unfinished` / `maintenance`)
- Qual issue tracker integrar (`github` / `jira` / `linear` / `clickup` / `trello`)
- Se Graphify deve ser configurado e com qual granularidade
- Quais arquivos `docs/` criar (dependendo do tipo)
- Que conteúdo deve entrar no `CLAUDE.md` do projeto-alvo

Tudo isso é **decisão estrutural de longo prazo**, não execução. O `software-architect` e o `product-analyst` (também decisores) já estão em Opus. **`setup-assistant` deveria ser Opus** ou o `CLAUDE.md` deveria reformular o critério.

> **Fingerprint:** `agent-setup-assistant-model-mismatch`

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Onboarding decide melhor (ex.: detecta projetos híbridos, sugere stack mais adequada) |
| **Positivo** | Coerência interna do contrato modelo↔função do `CLAUDE.md` |
| **Negativo** | Custo por sessão sobe (Opus é mais caro); mitigável pelo fato de o `setup-assistant` rodar **uma única vez** por projeto |
| **Negativo** | Latência maior — Opus é ~2× mais lento que Sonnet para a primeira resposta |

**Recomendação:** alterar para `model: claude-opus-4-7` e adicionar um comentário no frontmatter justificando a escolha (decisão estrutural única, não execução repetida).

---

## 3.2 `test-pyramid` e `test-strategy` são complementares — README poderia clarificar

A passada de 2026-05-06 listou os dois como "skills de testing" sem explicar a divisão. Inspeção atual:

| Skill | Escopo | Carregada por |
|-------|--------|----------------|
| `test-strategy/SKILL.md` | **Decisão**: o que testar, quando, AAA, naming, target de coverage | `qa-specialist`, `software-architect` |
| `test-pyramid/SKILL.md` | **Implementação**: estrutura de unit/integration/E2E, ferramentas, antipatterns | `backend-test-specialist`, `frontend-test-specialist` |

São **complementares e não redundantes**. Mas o README atual não explica essa divisão — usuário pode achar que uma é versão antiga da outra.

> **Fingerprint:** `docs-sync-readme-test-skills-clarification`

**Recomendação:** acrescentar uma frase de uma linha em `README.md` (e `README.pt-BR.md`):

> `test-strategy` define o **o quê e quando** testar; `test-pyramid` define o **como** estruturar testes — ambos são carregados em conjunto.

---

## 3.3 `comments-policy` ausente em 5 agentes que produzem código indireto

Skill `skills/shared/comments-policy/SKILL.md` (417 linhas) é a maior do repositório e dita política de comentários. Ela está carregada em 9 agentes que escrevem código direto.

Não está carregada em:
- `software-architect` — escreve snippets em ADRs
- `product-analyst` — escreve pseudocódigo em backlog stories
- `setup-assistant` — escreve trechos no `CLAUDE.md` do projeto
- `technical-writer` — escreve exemplos de código em changelogs/runbooks
- `qa-specialist` — escreve casos de teste em prosa que viram código

Esses agentes produzem **código exemplificativo**, e a falta da skill significa que o exemplo pode violar a política do próprio repo.

> **Fingerprint:** `skill-comments-policy-missing-in-non-coding-agents`

**Recomendação:** ou (a) adicionar `comments-policy` ao Foundational Rule desses 5 agentes, ou (b) — preferível por economia — promover `comments-policy` a skill carregada via `project-context` (universal). Esta segunda opção também economiza tokens no longo prazo.

| Impacto | Detalhe |
|---------|---------|
| **Positivo (a)** | Cobertura imediata; baixo risco |
| **Positivo (b)** | Economia de tokens duradoura; uma decisão central |
| **Negativo (a)** | Repetição da declaração em 5 agentes |
| **Negativo (b)** | Se um agente futuro **não** quiser carregar `comments-policy`, terá que dar opt-out |

---

## 3.4 Templates físicos vs templates inline em skills — desconexão arquitetural

`templates/` contém apenas `plan-template.md`. Mas o repositório referencia uma série de **outros templates** que vivem **inline em skills**:

| Tipo de template | Onde está hoje | Onde deveria estar (canônico) |
|------------------|----------------|--------------------------------|
| ADR | `skills/shared/adr/SKILL.md` (linhas 30–80) | `templates/adr-template.md` |
| Backlog Sprint | `skills/shared/backlog-template/SKILL.md` (linhas 60–140) | `templates/backlog-sprint-template.md` |
| Documentação | `skills/shared/docs-templates/SKILL.md` (várias subseções) | `templates/docs/*.md` |
| Plan | `templates/plan-template.md` ✓ | já correto |

Existem dois caminhos divergentes para o mesmo conceito. O `new-adr.sh` (script) inclusive **já usa** um template inline — o que sugere que a intenção original era ter `.md` físico.

> **Fingerprint:** `gov-templates-physical-vs-inline`

**Recomendação:** mover os blocos de template das skills para arquivos físicos em `templates/`, e referenciá-los nas skills com `@include` (Markdown não suporta nativamente, mas pode ser via instrução textual: "use template at `templates/adr-template.md`"). Mantém uma única fonte da verdade.

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Templates ficam navegáveis (Cmd+Click no editor) |
| **Positivo** | Skills ficam menores — `backlog-template/SKILL.md` (147 linhas) cairia para ~30 |
| **Positivo** | Permite versionar templates como artefatos de primeira classe |
| **Negativo** | Migração precisa atualizar todos os agentes que carregam essas skills |
| **Negativo** | Risco de skill carregar template físico mas o agente não saber abrir |

---

## 3.5 Skills curtas em `integrations/` não estão referenciadas

Confirmação positiva da passada anterior: `offline-first/SKILL.md` (23 linhas) e `pwa/SKILL.md` (32 linhas) **não são stubs** — são intencionais e enxutas. Porém, nesta passada percebi que **nenhum agente as carrega explicitamente**.

```bash
$ grep -lR "offline-first/SKILL.md\|skills/integrations/offline-first" agents/
(vazio)
$ grep -lR "pwa/SKILL.md\|skills/integrations/pwa" agents/
(vazio)
```

O `orphan-skill-scan.sh` provavelmente encontra essas referências por **nome curto** em algum agente, mas a inspeção sugere que estão na linha tênue de "skill órfã, mas válida porque o nome é mencionado em prosa".

> **Fingerprint:** `skill-pwa-offline-weak-references`

**Recomendação:** adicionar ao `frontend-developer.md` (ou criar agente novo `mobile-specialist`) carregamento condicional dessas skills quando o projeto-alvo for PWA/mobile-first.

---

## 3.6 Resumo de fingerprints novos

| Fingerprint | Tema |
|-------------|------|
| `agent-setup-assistant-model-mismatch` | `setup-assistant` em Sonnet contraria CLAUDE.md (deveria ser Opus) |
| `docs-sync-readme-test-skills-clarification` | README não explica complementaridade `test-pyramid` × `test-strategy` |
| `skill-comments-policy-missing-in-non-coding-agents` | `comments-policy` ausente em 5 agentes que produzem código exemplificativo |
| `gov-templates-physical-vs-inline` | Templates dispersos entre `templates/*.md` e blocos inline em skills |
| `skill-pwa-offline-weak-references` | Skills `pwa` e `offline-first` sem load explícito por agente |
