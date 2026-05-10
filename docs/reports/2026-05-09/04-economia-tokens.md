# 04 — Economia de Tokens

**Data:** 2026-05-09
**Escopo:** Quarta passada — duplicação no Reviewer Mindset, monolito da skill `comments-policy` (417 linhas), padrão `When loaded` ausente, README bilíngue 2× tamanho, Foundational Rule itens 5–12 em prosa.
**Anti-repetição:** os 75 fingerprints anteriores excluídos.

---

## Sumário

As 3 passadas anteriores cobriram blocos repetidos óbvios (worktree, sonarqube detection, foundational rule items 1-4, REST conventions, current-context block). Esta quarta passada explora **duplicações estruturais menos evidentes**: padrões de prosa ("Reviewer Mindset"), skills monolíticas que poderiam ser fragmentadas, e o custo de carregamento incondicional de skills que poderiam ser condicionais.

Estimativa total de economia possível combinada com sugestões já flagadas: **~400 linhas** de prosa redundante removível dos agentes (sobre as ~200 linhas estimadas em 2026-05-08).

---

## Sugestões

### 1. Bloco `## Reviewer Mindset` duplicado nos 3 reviewers

**Fingerprint:** `token-reviewer-mindset-block-duplicate`

**Evidência:** O bloco "Reviewer Mindset" (~12 linhas com 7 bullets) está em `code-reviewer.md`, `backend-reviewer.md` e `frontend-reviewer.md`. Os bullets variam por especialidade ("race condition lurks" vs "prop combination crashes" vs neutro), mas a **moldura** ("bias of a critic", 7 perguntas, "You are not a linter") é idêntica.

Total bruto: ~36 linhas. Se extraído para `skills/shared/reviewer-mindset/SKILL.md` com a moldura + bullets parametrizados (ou herdada via skill `reviewer-base` proposta no relatório 03), economiza ~24 linhas (cada agente reduz de 12 para 4 linhas de override específico).

**Impacto positivo:** ~24 linhas removíveis dos agentes; mindset consistente; mudança no Mindset propaga para todos automaticamente.

**Impacto negativo:** abstração extra. Se um futuro reviewer (ex.: `database-reviewer`) tiver mindset radicalmente diferente, precisará override.

**Esforço:** Baixo (skill nova + 3 substituições).

---

### 2. Skill `comments-policy` é monolítica (417 linhas)

**Fingerprint:** `token-comments-policy-skill-monolith`

**Evidência:** A maior skill do repositório com 417 linhas. Inclui:

- Core Principle (geral)
- Don't comment what / bad code / noise / commented-out / version-control
- When type annotations ARE required (5 sub-blocos)
- AAA pattern (testes)
- Forbidden Comment Types
- Self-Documentation Techniques

Carregada por 9 agentes (count em grep). Cada agente carrega 417 linhas mesmo quando precisa só de uma seção. Por exemplo, `backend-reviewer` precisa principalmente das regras de "Don't comment what" e "Don't leave commented-out code"; o agente `backend-test-specialist` precisa principalmente do "AAA pattern".

**Impacto positivo:** fragmentar em `comments-policy/SKILL.md` (resumo + index, ~50 linhas) + `comments-policy/references/aaa-pattern.md`, `comments-policy/references/type-annotations.md`, `comments-policy/references/anti-patterns.md`. Cada agente carrega só o resumo + a referência relevante. Economia estimada por agente: ~250 linhas de contexto carregado mas não usado.

**Impacto negativo:** mais arquivos para manter; risco de divergência entre fragmentos.

**Esforço:** Alto (refatoração de skill grande). ROI alto: 9 agentes × 250 linhas = ~2250 linhas de contexto evitado por sessão multi-agente.

---

### 3. Skills carregadas incondicionalmente onde poderiam ser condicionais

**Fingerprint:** `token-when-loaded-conditional-blocks`

**Evidência:** Vários agentes carregam `comments-policy` no Foundational Rule sem condicional, mesmo que o agente esteja respondendo a uma pergunta de design (não toca código). Mesmo padrão para `conventional-commits` em agentes que não vão commitar nesta sessão. O custo é de ~100-400 linhas por skill carregada à toa.

Padrão sugerido (alinhado com `agent-when-loaded-pattern-only-qa` do relatório 03):

```markdown
## Skills (carga condicional)

| Trigger | Skill | When |
|---------|-------|------|
| Toca arquivo de código | comments-policy | Antes de Edit |
| Vai commitar nesta sessão | conventional-commits | Antes de git commit |
| Toca review em PR | pr-review | Em /devteam:pr review=on |
```

A leitura humana do agente deixa claro **quando** cada skill é necessária. Carga lazy reduz contexto.

**Impacto positivo:** redução média de 30-50% no contexto carregado por sessão simples.

**Impacto negativo:** se o trigger for ambíguo, agente pode esquecer de carregar a skill quando deveria.

**Esforço:** Médio.

---

### 4. README bilíngue como dual-source de 1402 linhas

**Fingerprint:** `token-readme-bilingual-dual-source`

**Evidência:**

```
README.md       — 700 linhas
README.pt-BR.md — 702 linhas
                 = 1402 linhas em sync manual
```

A regra "README Sync Rule" no CLAUDE.md exige que cada mudança em um se reflita no outro. Sem tooling, isso depende de disciplina humana (vulnerável ao drift; já flagado em 2026-05-06 como `gov-readme-pt-br-sync-check` — falta de validador).

Esta sugestão é um ângulo **de economia de tokens**, não de governança: 700 linhas é o tamanho de uma documentação completa de produto. Para um agente que precisa carregar README como contexto inicial, isso é caro. Sugestões alternativas:

a) **Fragmentar README** em `README.md` (overview, ~150 linhas) + `docs/installation.md` + `docs/agents.md` + `docs/skills.md` + `docs/workflows.md`. Cada agente carrega só o que precisa.

b) **Sumário-em-vez-de-conteúdo no README**: README vira índice apontando para `docs/`. Agentes leem o índice (~50 linhas) primeiro, decidem o que carregar.

c) **Manter monolítico mas marcar seções com tags estruturadas** (HTML comments) que permitam grep eficiente: `<!-- @section: agents -->`, `<!-- @section: install -->`. Foundational Rule pode `grep` a seção em vez de read full.

**Impacto positivo (a/b):** economia drástica de contexto inicial; cada agente carrega ~150 linhas em vez de 700.

**Impacto negativo (a/b):** quebra de convenção (README virou índice é menos comum); maior surface de drift entre arquivos.

**Esforço:** Alto (a/b), Baixo (c).

---

### 5. Foundational Rule itens 5–12 em prosa enumerada vs tabela compacta

**Fingerprint:** `token-foundational-rule-domain-paths-explicit`

**Evidência:** O Foundational Rule típico tem 12 itens enumerados (1–12). Itens 1–4 são universais (já flagados como `token-foundational-rule-extension-pattern`). Itens 5–12 são domínio-específicos:

```
5. AGENTS.md
6. .claude/docs/development/architecture.md
7. .claude/docs/development/tech-stack.md
8. .claude/docs/development/code-standards.md
9. .claude/docs/development/api-contracts.md   ← backend-specific
10. .claude/docs/development/database.md       ← backend/database
11. .claude/docs/backlog/                      ← product/all
12. Run `git log --oneline -20`                ← all
```

Cada agente repete prosa "Run `git log…` — reveals recent patterns…". Em forma de tabela:

```markdown
## Domain Context Files (load if exists, in this order)

| Path | Why |
|------|-----|
| .claude/docs/development/architecture.md | architectural decisions |
| .claude/docs/development/tech-stack.md   | chosen technologies |
| ... | ... |

## Final Step

Run `git log --oneline -20` to surface recent patterns.
```

Tabela é mais compacta que enumeração com prosa explicativa. Economia estimada: ~5-7 linhas por agente × 14 agentes = ~80 linhas.

**Impacto positivo:** ~80 linhas removíveis; tabela é mais fácil de manter (adicionar novo path = 1 linha).

**Impacto negativo:** tabelas em Markdown podem quebrar visualmente em terminais estreitos.

**Esforço:** Baixo.

---

### 6. README.pt-BR.md é candidato a fragmentação por seção

**Fingerprint:** `token-bilingual-readme-section-fragmentation`

**Evidência:** Distinto da sugestão #4 (que é macro). Aqui o foco é específico em `README.pt-BR.md`: tradução manual de 702 linhas é o cenário de drift mais provável. Estratégia híbrida: manter `README.md` canônico, e o `README.pt-BR.md` ser **só sumário com links** para `README.md#section` quando seções mais técnicas (agentes, skills) coincidirem.

Alternativa: introduzir tooling `scripts/readme-sync-check.sh` que compara contagem de seções H2 e ordem entre os dois arquivos. Falha CI se divergem.

**Impacto positivo:** reduz superfície de drift em 50-80% se sumário-only; tooling automatizado captura drift restante.

**Impacto negativo:** experiência do leitor PT-BR fica um clique mais distante do conteúdo.

**Esforço:** Médio.

---

### 7. Foundational Rule prosa "**Project rules override base standards**" duplicada

**Fingerprint:** `token-project-rules-override-prose-duplicate`

**Evidência:** A frase "**Project rules override base standards. Always.** This loading order follows the **`project-context`** skill" aparece em 14 agentes (count via grep). Já está embutida no espírito da skill `project-context`. Repetição da frase em cada agente é redundante:

```bash
$ grep -c "Project rules override" agents/*.md
agents/backend-developer.md:1
agents/code-reviewer.md:1
agents/database-specialist.md:1
[...]
```

Substituição: cada agente fecha o Foundational Rule com `Apply skills/shared/project-context/SKILL.md` (sem repetir a explicação). A própria skill já cobre esse princípio na primeira linha.

**Impacto positivo:** ~28 linhas removíveis (2 linhas × 14 agentes).

**Impacto negativo:** se um leitor olhar só o agente sem abrir a skill, perde a regra-de-precedência. Mitigação: deixar nota sintética de 1 linha.

**Esforço:** Trivial.

---

### 8. Skills `cicd-*` (4 skills × ~300 linhas) sobrepostas em estrutura

**Fingerprint:** `token-cicd-skills-shared-structure`

**Evidência:** 4 skills (`cicd-bitbucket`, `cicd-github`, `cicd-gitlab`, `cicd-jenkins`) cobrem CI/CD por plataforma. Cada uma tem estrutura provavelmente similar (triggers, runners, secrets, caching, deploy stages). Padrão típico: ~70% comum + ~30% sintaxe-específica.

Estratégia sugerida: `skills/devops/cicd-base/SKILL.md` com conceitos transversais (gates, rollback, parallel stages, secret management) + cada plataforma cobre apenas a tradução para sua sintaxe. Economia estimada por skill: ~80 linhas de prosa redundante. Total: ~320 linhas.

**Impacto positivo:** ~320 linhas economizadas; conceitos consistentes entre plataformas (impossível um conceito ficar em só 1 das 4 skills).

**Impacto negativo:** `devops-specialist` precisa carregar 2 skills em vez de 1 quando atende a um projeto específico.

**Esforço:** Médio (refatoração de 4 skills + criação de 1).

---

## Lista Priorizada (por ROI: linhas economizadas / esforço)

| Prioridade | Sugestão | Linhas economizadas (est.) | Esforço |
|------------|----------|-----------------------------|---------|
| P0 | `comments-policy` → resumo + references/ | ~250 × 9 agentes = ~2250 (lazy-load) | Alto |
| P0 | `cicd-*` skills → base + 4 plataformas | ~320 | Médio |
| P1 | `Reviewer Mindset` extraído para skill | ~24 (raw) + dedup conceitual | Baixo |
| P1 | Padrão `When loaded` para skills condicionais | 30-50% redução em sessões simples | Médio |
| P2 | Foundational Rule itens 5-12 como tabela | ~80 | Baixo |
| P2 | "Project rules override" — remover repetição | ~28 | Trivial |
| P3 | README → fragmentação por seção | ~550 (de 700 para ~150) | Alto |
| P3 | README pt-BR → sumário + script de sync | ~600 (50% drift surface) | Médio |

---

## Próxima passada

Ângulos ainda não cobertos: economia em outputs gerados (não só no contexto carregado) — ex.: relatórios de QA / security-specialist tendem a ser longos; quantos tokens são realmente úteis vs prosa de cabeçalho. Análise de skills "frequentemente carregadas mas raramente citadas no output final" — candidatos a downgrading para summary-only.
