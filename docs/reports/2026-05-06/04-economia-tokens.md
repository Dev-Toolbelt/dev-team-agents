# 4. Economia de Tokens

← [Voltar ao índice](index.md)

A oportunidade mais alta está em **reduzir repetição de instruções idênticas** entre
agentes. Como cada agente é carregado integralmente em sua sessão, cada linha redundante
custa tokens **por cada invocação**.

---

## 4.1 Foundational Rule replicada em todos os agentes

Hoje, **16 agentes** repetem (com mínimas variações) o mesmo bloco numerado:

```text
1. README.md, CLAUDE.md, AGENTS.md
2. .claude/docs/project.md
3. .claude/user-data/session-summary.md (most recent only)
...
N. Run `git log --oneline -20`
```

E ainda **adicionam** a frase "This loading order follows the `project-context`
skill (`skills/shared/project-context/SKILL.md`)".

Ou seja, a regra está **definida duas vezes**: inline no agente e centralizada na skill.

> **Fingerprint:** `token-context-loading-dedup`, `token-foundational-rule-template`

**Sugestão:** Substituir o bloco inline por uma única chamada:

```markdown
## Foundational Rule — Load Context First

Apply `skills/shared/project-context/SKILL.md` (loading order canonical).
Then load these agent-specific files:
- .claude/docs/development/<arquivo-relevante>.md
- ...
```

**Estimativa de impacto:** ~12 linhas economizadas por agente × 16 agentes ≈ **192
linhas / ~2.5k tokens** por base de prompts. Como cada agente é carregado **somente
quando invocado**, a economia real depende do mix de invocações — mas em workflows
multi-agent (`/devteam:plan` aciona 6 agentes) o ganho é multiplicado.

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Economia clara de contexto (~5–10% por agente) |
| **Positivo** | Quando a regra muda, edita-se em um único lugar (`project-context`) |
| **Negativo** | Agente fica mais opaco em leitura solta (precisa abrir a skill para ver o que carrega) |
| **Negativo** | Se a skill quebrar/desaparecer, todos perdem a Foundational Rule (mitigado pelo `orphan-skill-scan`) |

## 4.2 Menção redundante de `token-efficiency`

Praticamente todo agente termina o Foundational Rule com:

> "Apply `skills/shared/token-efficiency/SKILL.md` when reading many files…"

Mas o próprio `project-context.md` já recomenda token-efficiency como default. A frase
inline custa tokens e raramente é desabilitada.

> **Fingerprint:** `token-skill-mention-redundancy`

**Sugestão:** Mover essa orientação para o `project-context` e remover dos agentes,
exceto onde houver instrução **adicional** (ex.: `code-reviewer` deve preferir
`git diff` direto, sim faz sentido manter).

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | ~2 linhas a menos por agente; ~32 linhas no total |
| **Negativo** | Risco baixo de o agente "esquecer" da policy se ele falhar em ler `project-context` |

## 4.3 Citações de skill por path completo vs nome

O Foundational Rule cita as skills por path completo
(`skills/shared/conventional-commits/SKILL.md`), o que é útil para o orphan-scan, mas
custa caractere. A convenção `agentskills.io` aceita nome curto. Como o
`orphan-skill-scan.sh` casa **path OU nome** (vimos que `comments-policy` é citado por
nome em alguns agentes e ainda assim é detectado), pode-se padronizar para **nome
curto** quando o agente apenas referencia, e **path** quando ele instrui a carregar.

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Reduz ~30–40% do tamanho de cada citação de skill |
| **Negativo** | Reduz a "navegabilidade" via Cmd+Click no editor |

## 4.4 Modelo Haiku para o `technical-writer` está bem alocado

Auditando os agentes, `technical-writer` está em **Haiku** (correto, é tarefa
estruturada de saída). `code-reviewer` em Sonnet (correto). `security-specialist`
em Opus (correto). Não há realocação evidente — esta é uma confirmação positiva.
