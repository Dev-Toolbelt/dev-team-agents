# 3. Agentes e Skills (Cobertura ADR, Modelo do technical-writer, Trackers, Dogfooding)

← [Voltar ao índice](index.md)

Esta seção foca em três classes de problema dos agentes/skills atuais: **cobertura assimétrica** de skills críticas, **escolha de modelo desalinhada** com o tipo de output produzido, e **discrepância entre listas declaradas no setup-assistant e cobertura real nos agentes**.

---

## 3.1 Skill `adr` é referenciada por **um único** agente

A skill `skills/shared/adr/SKILL.md` (formato MADR completo, gatilho de criação, exemplos) é carregada por exatamente **1** agente:

```text
$ grep -l "skills/shared/adr\|\`adr\`" agents/*.md
agents/software-architect.md
```

Mas, na prática, decisões dignas de ADR também emergem em:

| Agente | Decisão típica que merece ADR |
|--------|-------------------------------|
| `database-specialist` | Estratégia de multi-tenancy (RLS × schema-per-tenant); escolha entre OLTP single vs réplica de leitura |
| `devops-specialist` | Plataforma cloud, infra IaC vs hand-rolled, estratégia de orquestração (compose × ECS × Cloud Run) |
| `backend-developer` | Adoção de mensageria, escolha de fila (SQS × Redis × RabbitMQ), padrão de retry/DLQ |
| `security-specialist` | Estratégia de auth (JWT × sessão × OAuth provider) |
| `frontend-developer` | Adoção de SSR vs CSR vs ISR; escolha de gerenciamento de estado (Redux × Zustand × Context) |

Hoje essas decisões aparecem soltas em commits, PRs ou no `architecture.md` — sem o gatilho explícito que a skill `adr` carrega. Como nenhum desses agentes tem a skill carregada, o reflexo "essa decisão merece um ADR?" não dispara.

> **Fingerprint:** `skill-adr-coverage-only-architect`

| Impacto | Detalhe |
|---------|---------|
| **Positivo (expandir)** | Decisões pesadas em 4+ domínios passam a ter rastro institucional |
| **Positivo (expandir)** | Reduz dependência exclusiva do `software-architect` para registrar decisões |
| **Negativo** | Risco de ADR-spam — decisões triviais sendo registradas; mitigar com critério explícito (de novo, o gatilho do `CLAUDE.md`) |

**Recomendação:** adicionar load referência da skill `adr` em pelo menos `database-specialist`, `devops-specialist`, `backend-developer` e `security-specialist`. Acompanhar com uma frase: *"Antes de declarar done em uma decisão arquitetural, avalie a regra de gatilho de ADR e crie via `new-adr.sh` se aplicável."*

---

## 3.2 `technical-writer` está em **Haiku**, mas produz outputs de Sonnet

`agents/technical-writer.md` linha 4: `model: claude-haiku-4-5-20251001`.

O catálogo do próprio repositório (`skills/shared/token-efficiency/SKILL.md` linhas 16–20) classifica:

| Tipo de tarefa | Modelo |
|----------------|--------|
| Aprender uma codebase, arquitetura, análise profunda | **Opus** |
| **Escrever código, debug, testes, documentação**, perguntas rotineiras | **Sonnet** (default) |
| Output estruturado, extração repetitiva rápida | **Haiku** |

O `technical-writer` faz exatamente o que está sublinhado em **Sonnet**: produz README, runbooks, ADRs, changelogs — texto longo e nuançado, não extração estruturada repetitiva. Haiku é apropriado para "extrair os 5 verbos do diff e gerar uma string conventional-commit", **não** para "redigir um runbook de incident response em Diátaxis".

A escolha atual cria um descasamento: o agente entrega documentação que é tecnicamente estruturada, mas pode soar mecânica em comparação com o conteúdo já existente no repositório (ex.: a prosa do `README.md` deste projeto, claramente escrita com mais cuidado).

> **Fingerprint:** `agent-technical-writer-haiku-mismatch`

| Impacto | Detalhe |
|---------|---------|
| **Positivo (mudar para Sonnet)** | Documentação ganha tom adulto, mais coerente com a voz do projeto |
| **Positivo** | Alinha com a tabela do `token-efficiency` (uma única fonte da verdade) |
| **Negativo** | Custo por sessão de doc sobe — Sonnet é ~5× mais caro por token que Haiku |
| **Negativo** | Para tarefas pequenas (changelog de 1 linha), Sonnet é overkill |

**Recomendação (cirúrgica):** manter Haiku em rotinas de **extração** (changelog enxuto, lista de PRs do mês) — mas **mover o agente padrão para Sonnet** porque a maioria dos calls envolve prosa. Alternativa: bipartir em `technical-writer` (Sonnet, prosa) e `release-notes-bot` (Haiku, extração) — mas isso é over-engineering para o tamanho do repo. Mover só o modelo é o caminho.

---

## 3.3 `templates/plan-template.md` **duplica** o conteúdo de `skills/shared/plan-mode/SKILL.md`

Comparação dos arquivos:

| Bloco | `templates/plan-template.md` | `skills/shared/plan-mode/SKILL.md` |
|-------|------------------------------|------------------------------------|
| Header `━━━ PLAN · [Task] ━━━` | linhas 1–3 | linhas 40–42 |
| `CONTEXT` / `SCOPE` / `APPROACH` | linhas 5–22 | linhas 44–61 |
| Tabela `STEPS` com colunas `Par.` | linhas 24–35 | linhas 63–74 |
| `RISKS & DEPENDENCIES` | linhas 37–40 | linhas 76–79 |
| `DEFINITION OF DONE` | linhas 42–47 | linhas 81–86 |
| Footer "Awaiting your approval" | linhas 49–56 | linhas 88–94 |

São **dois arquivos com o mesmo conteúdo**. Quando o template muda, ambos precisam mudar — e o autor que altera o template provavelmente ignora a skill, e vice-versa.

> **Fingerprint:** `gov-plan-template-vs-skill-duplication`

| Impacto | Detalhe |
|---------|---------|
| **Positivo (consolidar)** | Uma única fonte da verdade; correções/melhorias propagam imediatamente |
| **Positivo (consolidar)** | Simplifica explicação para contribuintes ("plan format vive em X") |
| **Negativo** | Refatorar exige decidir qual fica autoritativo (skill ou template) |

**Recomendação:** manter `templates/plan-template.md` como **a** fonte e fazer `skills/shared/plan-mode/SKILL.md` referenciá-lo (com link, não cópia). Os agentes que carregam `plan-mode` lêem **uma única vez**: `Use the format defined in templates/plan-template.md`. A skill então fica focada nas regras de aprovação/rejeição/replanejamento (que não estão no template — bom complemento).

Alternativa equivalente: matar o `templates/plan-template.md` e fazer todo mundo apontar para a skill. Resultado é o mesmo — só inverte o local autoritativo.

---

## 3.4 `product-analyst` só tem seção dedicada para **Jira**; ignora Linear/ClickUp/Trello/GitHub Issues

`agents/product-analyst.md` tem uma seção `## Jira Integration` (10 ocorrências da palavra "jira"), mas:

```
$ grep -i "linear\|clickup\|trello\|github.issues" agents/product-analyst.md
(zero ou quase-zero resultados)
```

Já o `setup-assistant.md` Step 3 lista trackers configuráveis: **GitHub Issues, Jira, Linear, ClickUp, Trello, etc.**. O usuário pode escolher qualquer um dos 5+ trackers — mas ao invocar o `product-analyst`, **só Jira** ganha tratamento dedicado.

Hoje, se o projeto usa Linear, o `product-analyst` cai no fluxo genérico (markdown local em `.claude/docs/backlog/`) sem aproveitar as tools MCP do tracker remoto. O mesmo skill (`integrations/jira/SKILL.md`) tem irmãos potenciais (`integrations/linear`, `integrations/clickup`) que **não existem**.

> **Fingerprint:** `agent-product-analyst-jira-only-tracker`

| Impacto | Detalhe |
|---------|---------|
| **Positivo (paridade)** | Usuários de Linear/ClickUp obtêm o mesmo nível de integração que usuários de Jira |
| **Positivo** | `setup-assistant` deixa de "vender" trackers que o `product-analyst` ignora |
| **Negativo** | Criar 4 skills novas é trabalho não-trivial; manutenção contínua |
| **Negativo** | Risco de skills "stub" que não cobrem nada útil; aumentaria a contagem sem agregar |

**Recomendação:** uma das duas estratégias:

1. **Skill genérica `tracker-integration`** que descreve o **padrão** (detect → fetch backlog → create issues → naming convention) e referencia tools MCP-específicas via tabela. Cada tracker contribui só com a tabela de tools MCP, não com 50 linhas de prosa duplicada.
2. **Reduzir o setup-assistant** para listar apenas Jira como integração "premium" e os outros como "supported via local backlog only". Honesto; menos trabalho.

A opção (1) escala melhor se o projeto cresce; a (2) é honesta com a realidade atual.

---

## 3.5 `setup-assistant.md` tem seções de Roles em ordem `1 → 3 → 2`

Estrutura atual do arquivo:

```
## Role 1 — Project Setup            (linhas 28–217)
## Role 3 — Health Check             (linhas 219–369)
## Role 2 — Update Manager           (linhas 372–388)
## Immutability Warning              (linhas 391–404)
```

`Role 2` (Update Manager) aparece **depois** de `Role 3` (Health Check). Quem lê o arquivo de cima para baixo vê: "ah, deve ter sido renumerado e ninguém arrumou". Não é um bug funcional, é um sinal de **drift de manutenção** — exatamente o tipo de detalhe que erode confiança numa codebase ao longo do tempo.

Adicionalmente: o agente é o único que oficialmente referencia `templates/plan-template.md` (item 3.3 acima); se for quebrado em sub-skills (já fingerprintado em 2026-05-06 como `agent-setup-assistant-size`), faz sentido reordenar agora.

> **Fingerprint:** `agent-setup-assistant-roles-out-of-order`

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Leitor não tropeça em inconsistência cosmética |
| **Negativo** | Pura cosmética; sem ganho operacional |

**Recomendação:** renomear para ordem natural (`Role 1 — Project Setup` → `Role 2 — Update Manager` → `Role 3 — Health Check`) ou substituir por nomes descritivos sem numeração (`## Project Setup`, `## Update Manager`, `## Health Check`).

---

## 3.6 Stop hook do repo é "self-eat": dispatcher canônico não é exercitado em casa

(Este item é a contraparte agente-skill do fingerprint `gov-dev-repo-no-stop-dispatcher` da seção 1.4. Aqui o ângulo é **a perda de feedback operacional**.)

Quem desenvolve `dev-team-agents` nunca dispara o `01-session-summary.sh` ao trabalhar no próprio repo. Resultado: o autor do hook não vê, em primeira pessoa:

- Se o exit-code-2 do hook está aparecendo bem na UI do Claude Code;
- Se a mensagem é educativa ou irritante após N tentativas;
- Se o detector de "commit do dia" tem falso-positivo em rebases / amends;
- Se o caminho `[ ! -f "$SUMMARY_FILE" ]` realmente acerta no FIRST_RUN do próprio repo.

Esse "loop de feedback ausente" é a razão funcional por que projetos de tooling devem dogfoodar agressivamente o que distribuem.

> **Fingerprint:** `gov-stop-dispatcher-self-eat`

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Bugs sutis do hook são caçados antes de chegar ao usuário final |
| **Positivo** | O `session-summary.md` do repo vira um "log institucional" valioso para contribuintes |
| **Negativo** | Cada Stop signal ganha 100–300ms; perceptível em sessões curtas |
| **Negativo** | Decisão sobre versionar `session-summary.md` precisa ser explícita (commitar = histórico verboso; ignorar = perde a vantagem) |

**Recomendação:** ativar o dispatcher em `.claude/settings.json` deste repo. Para o `session-summary.md` deste repo especificamente: **commitar**, deixando que ele acumule histórico do desenvolvimento do próprio `dev-team-agents`. Vira documentação viva.

---

## 3.7 Resumo de fingerprints novos

| Fingerprint | Tema |
|-------------|------|
| `skill-adr-coverage-only-architect` | Skill `adr` referenciada por 1 agente; deveria estar em 4+ |
| `agent-technical-writer-haiku-mismatch` | `technical-writer` em Haiku, mas produz outputs típicos de Sonnet |
| `gov-plan-template-vs-skill-duplication` | `templates/plan-template.md` e `plan-mode/SKILL.md` carregam o mesmo formato |
| `agent-product-analyst-jira-only-tracker` | `product-analyst` cobre só Jira; setup-assistant lista 5+ trackers |
| `agent-setup-assistant-roles-out-of-order` | Roles ordenadas 1, 3, 2 no `setup-assistant.md` |
| `gov-stop-dispatcher-self-eat` | Dev-team-agents não dogfooda seu próprio dispatcher de hooks |
