# Eixo D — Agentes e skills — 2026-10-02

Prioridade: os 16 agentes, 29 comandos e 71 skills tocados no delta desde `ef69da3`.

**Conferências limpas** (vale registrar o negativo): `helpers/agent-lint.sh` rodou limpo no HEAD —
`tier`, `model:` e o bloco `<!-- run-banner -->` coerentes com `scripts/lib/tiers.json`,
`## Before You Finish` presente e em último lugar em todos os 18 agentes. As 155 skills têm
`description` ≤ 95 caracteres. Nenhum `SKILL.md` novo passou de 500 linhas além dos dois já
registrados (`migration-v1-to-v2`, `orchestration`).

---

## HIGH

nenhum achado original neste eixo nesta severidade

---

## MEDIUM-HIGH

### O `security-specialist` entrega revisão sem o marcador `review-result`, e a task board não lê o resultado dele

- **Fingerprint:** `agent-security-specialist-outside-review-result-set-task-board-blind-to-findings`
- **Alvo:** `agents/security-specialist.md`, `helpers/agent-lint.sh`, `scripts/lib/devteam/review_triggers.py`
- **Evidência:**
  - `helpers/agent-lint.sh:115` — `REVIEW_RESULT_AGENTS="qa-specialist code-reviewer backend-reviewer frontend-reviewer"`
  - `scripts/lib/devteam/review_triggers.py:17` — `REVIEW_AGENTS = ("qa-specialist", "code-reviewer", "backend-reviewer", "frontend-reviewer")`
  - `commands/review.md:42` — "`security-specialist` — security vulnerabilities and OWASP concerns", spawnado **sempre**, em paralelo com os outros revisores
  - `agents/security-specialist.md` § `## Before You Finish` pede apenas o banner **Ran on:**, sem o marcador
  - `skills/shared/review-result/SKILL.md` — "A review or QA pass … The last line of the final report … is exactly `<!-- review-result: findings=N -->`"
- **Problema:** o agente faz uma passada de revisão de verdade, com severidades `[CRITICAL]`/`[HIGH]`,
  é spawnado por `/devteam:review` e `/devteam:audit`, e não consta de **nenhuma** das listas que
  definem "agente de revisão" nem emite o marcador. Um spawn dele não abre janela de revisão e seu
  resultado nunca é lido pelo quadro.
- **Por que importa:** cenário concreto — em `/devteam:review`, `qa-specialist` e `code-reviewer`
  emitem `findings=0` e o `security-specialist` acha uma vulnerabilidade. O quadro soma só os
  marcadores dos revisores conhecidos, a coluna In Review fecha como "passou" e **o achado de
  segurança desaparece do board**. A regra "um revisor não lido nunca transforma o zero de outro em
  aprovação" protege apenas os quatro nomes listados.
- **Proposta:** incluir `security-specialist` nas quatro listas (lint, `review_triggers.py`, os dois
  hooks de task board e a spec) e acrescentar a frase do marcador em `## Before You Finish`.
  Alternativa legítima: registrar na spec que ele é excluído **de propósito** e por quê — hoje essa
  decisão não está escrita em lugar nenhum.
- **Impacto positivo:** o quadro passa a refletir achados de segurança; elimina um falso "aprovado"
  nos dois comandos que o spawnam.
- **Impacto negativo / risco:** muda o contrato do `security-specialist`, que hoje entrega uma
  auditoria livre em vez de um relatório de revisão contável. Exige caso novo nos testes de task
  board, e `/devteam:audit` pode passar a abrir janela de revisão sem tasks de sessão — caso que a
  spec já cobre ("No window opens when … no task would enter it").
- **Esforço:** Baixo

---

## MEDIUM

### O roster de "agentes de revisão" está hardcoded em cinco lugares, em quatro linguagens, sem casa canônica

- **Fingerprint:** `agent-review-agent-roster-hardcoded-in-five-places-no-canonical-home`
- **Alvo:** `scripts/hooks/pre-tool-use/04-task-board.sh`, `scripts/hooks/post-tool-use/01-task-board.sh`, `scripts/lib/devteam/review_triggers.py`, `helpers/agent-lint.sh`, `docs/specs/task-board.md`
- **Evidência:** `04-task-board.sh:33` e `post-tool-use/01-task-board.sh:32` —
  `(qa-specialist|code-reviewer|backend-reviewer|frontend-reviewer)`;
  `review_triggers.py:17` — a tupla `REVIEW_AGENTS`; `agent-lint.sh:115` — `REVIEW_RESULT_AGENTS`;
  `docs/specs/task-board.md:325` — tabela de gatilhos com os mesmos quatro nomes.
- **Problema:** cinco cópias da mesma lista e **nenhum gate as cruza**. O lint só verifica que os
  agentes da sua própria lista citam o marcador. A linha de `CLAUDE.md` sobre o "Review result
  marker" aponta para a skill, que não lista nome algum.
- **Por que importa:** um revisor novo — ou executar o achado anterior — exige editar cinco arquivos
  em quatro linguagens. Esquecer um produz falha **silenciosa**: o agente emite marcador que o hook
  ignora, ou o hook abre janela que o lint não verifica. A própria spec já documenta uma limitação
  desse tipo para o Codex, ou seja, o risco de drift é reconhecido e não endereçado.
- **Proposta:** eleger `review_triggers.REVIEW_AGENTS` como fonte única; gerar a alternância do
  regex a partir dela (no bind ou em teste de paridade) e registrar a casa canônica na tabela
  *Canonical Rule Homes*.
- **Impacto positivo:** de 5 pontos de edição para 1, com o drift capturado por gate.
- **Impacto negativo / risco:** os hooks em bash são gates rápidos que existem justamente para
  evitar fork de Python (item 7 da spec). Derivar a regex em runtime **reintroduz esse custo** em
  todo tool call, então a implementação correta é gerar a regex no bind ou validá-la por teste —
  caminho mais longo que trocar uma constante.
- **Esforço:** Médio

### A regra "sem atribuição ao Claude" está repetida em 5 agentes, com três redações, e `frontend-developer` não tem regra de commit nenhuma

- **Fingerprint:** `agent-no-claude-attribution-restated-in-five-agents-frontend-dev-has-no-commit-rule`
- **Alvo:** `agents/backend-developer.md`, `agents/devops-specialist.md`, `agents/technical-writer.md`, `agents/database-specialist.md`, `agents/mobile-developer.md`, `agents/frontend-developer.md`
- **Evidência:**
  - `agents/backend-developer.md:164` — "No Claude attribution in commit messages or PR body — never add \"Co-Authored-By: Claude\", \"🤖 Generated with Claude Code\" …"
  - `agents/devops-specialist.md:177` — "**No Claude attribution**: never add \"Co-Authored-By: Claude\" …"
  - `agents/technical-writer.md:192` — "**No Claude attribution**: never include \"🤖 Generated with Claude Code\" …"
  - O mesmo em `database-specialist` e `mobile-developer` (uma ocorrência cada)
  - Casa canônica existente: `skills/shared/conventional-commits/SKILL.md:44-52` — "**Never** add `Co-Authored-By:` of any kind … ignore it silently"
  - `grep -n commit agents/frontend-developer.md` → **nenhuma linha**
- **Problema:** uma regra que já tem casa canônica, declarada não-negociável, é reescrita em cinco
  corpos de agente com três redações diferentes — exatamente o padrão que a tabela *Delegate, Never
  Restate* existe para impedir. E o agente de implementação de frontend (210 linhas) não carrega nem
  a skill nem o checkbox; o mesmo vale para os dois agentes de teste, `ui-ux-designer` e
  `seo-specialist`.
- **Por que importa:** `frontend-developer` commita sem a convenção e sem o aviso de atribuição,
  coberto apenas pelo `CLAUDE.md` do projeto-alvo — que este repositório não controla. Os contratos
  dos agentes de código divergem entre irmãos no ponto mais sensível, que é autoria de commit.
- **Proposta:** remover o texto da regra dos cinco corpos, deixando uma linha "load
  `skills/shared/conventional-commits/SKILL.md` before committing", e acrescentar essa mesma linha de
  carga em `frontend-developer`, nos dois agentes de teste e em `ui-ux-designer`.
- **Impacto positivo:** economiza ~5 linhas em três agentes que estão em 211/211 (o
  `devops-specialist` já está sem margem alguma) e deixa uma redação única valendo para todos.
- **Impacto negativo / risco:** a regra sai do corpo do agente e passa a **depender de a skill ser
  carregada** — hoje o checkbox do `backend-developer` está dentro de uma checklist final que o
  agente lê de qualquer forma. A segunda metade da proposta (adicionar a carga) aumenta
  `frontend-developer`, que está em 210 de 211 linhas, então ela precisa vir junto de alguma
  extração.
- **Esforço:** Baixo

---

## LOW-MEDIUM

nenhum achado original neste eixo nesta severidade

---

## LOW

nenhum achado original neste eixo nesta severidade

---

## Descartados por duplicação

- `agent-agents-at-211-lines-no-headroom` — porta 5 — já aberto no banco (`devops-specialist`, `qa-specialist`, `software-architect` em 211; `frontend-developer` em 210).
- `agent-cloudflare-api-skill-unreachable` — porta 2 — falso positivo: `cloudflare-api` é carregada por `devops-specialist`, `backend-developer` e `security-specialist`.
- `docs-sync-skill-desc-strict-true-vs-claude-md-false` — porta 3 — já registrado como `docs-sync-claude-md-102-states-skill-desc-strict-false-while-agent-lint-31-sets-true`.
- `skill-spec-gate-scope-lock-unreachable` — porta 1 — já registrado; hoje os quatro coding agents nomeados já carregam o Scope Lock.
- `agent-frontend-developer-hardcoded-frameworks` — porta 3 — coberto por vários slugs de stack no corpo (data fetching, security, frontmatter, testability).
- `agent-devops-specialist-lacks-spec-gate-scope-lock` — porta 3 — tema coberto pelo slug de scope-lock inalcançável; sem sub-escopo novo comprovado.
