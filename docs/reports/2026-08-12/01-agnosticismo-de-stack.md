# Eixo A — Agnosticismo de Stack — 2026-08-12

**Baseline:** `HEAD` = `07e0725` · varredura **integral** de `agents/` e `commands/`.

## Varredura semente

```
rg -in '<seed de 40+ tecnologias>' agents/ commands/  → 112 hits
```

Priorizados os arquivos **novos/tocados no delta** (onde rendem achados originais): agente novo
`seo-specialist.md` e comandos novos `explain.md`, `install.md`, `push.md`, `relayout.md`, `rule.md`,
`status.md`, `sync-rules.md`, `version.md`, `seo.md`.

**Resultado nos arquivos novos: 5 candidatos → 1 violação.** Os `5−1 = 4` que caíram:

| Candidato | Por que caiu |
|---|---|
| `commands/explain.md:48` "the project's actual language and framework… never defaulting to JavaScript" | É o **oposto** de acoplamento — instrui detecção e proíbe default de stack. Descartado. |
| `commands/rule.md:27` "…not expressible as a regex → `design-rule`" | Falso-positivo do seed (casou "express"). Sem tecnologia nomeada. Descartado. |
| `commands/relayout.md:37` / `:43` "Docker stack, ports, seeded volumes" | Sob Worktree Isolation, **delega** ao skill de docker-isolation; "Docker" aparece como exemplo de infra, consistente com o uso já aceito em `skills/shared/worktree/`. Descartado. |
| `agents/seo-specialist.md` (0 hits do seed) | Agente novo é limpo de acoplamento de stack; termos são de domínio SEO (Core Web Vitals, structured data), não de framework. |

Os demais hits do seed (112 no total) estão sob os fingerprints já registrados
(`agent-frontend-developer-description…`, `agent-devops-specialist-core-expertise…`,
`agent-frontend-test-specialist-…-coverage`, `flow-audit-command-…-redis-cdn-docker`) — revalidados
na Fase 1b, não são novos.

---

## LOW-MEDIUM

### `commands/relayout.md` nomeia Storybook e Tailwind na descoberta de contexto de design

- **Fingerprint:** `flow-relayout-design-discovery-names-storybook-tailwind`
- **Alvo:** `commands/relayout.md`
- **Evidência:** `commands/relayout.md:32`, sob o heading **`## 1. Design context discovery — REQUIRED
  for every spawned agent`** — "look in common locations (`docs/design-system.md`,
  `.claude/docs/ui/design-system.md`, **a Storybook config, a Tailwind/theme config**) for tokens".
- **Problema:** a instrução central e obrigatória do comando (descobrir o design system de *todo*
  projeto antes de qualquer markup) nomeia dois produtos específicos — Storybook e Tailwind — como
  locais de busca. Um projeto que use Chromatic, Ladle, Panda CSS, vanilla-extract, tokens de tema
  próprios ou um design system em Figma/JSON não é coberto pela dica, que ancora o agente em duas
  ferramentas do ecossistema JS/React.
- **Por que importa:** `relayout` é um comando de UI que roda em qualquer stack de frontend. É o
  único ponto de acoplamento de stack introduzido pelos 9 arquivos novos do delta, e está numa
  seção de comportamento (não numa tabela de detecção que roteia para skill). O `/theme config`
  generaliza parcialmente, mas "a Storybook config" é um nome de produto cru.
- **Proposta:** trocar por classe de artefato: *"a component-explorer or design-token config (e.g.
  a theme/tokens file, a component-catalog config, or a documented design-system page)"*.
- **Impacto positivo:** remove o último acoplamento de stack dos comandos novos; alinha `relayout`
  ao padrão dos demais comandos (descrever o artefato, não o produto).
- **Impacto negativo / risco:** a versão genérica é levemente menos "acionável" para quem usa
  exatamente Storybook+Tailwind — perde o exemplo concreto que ajuda o reconhecimento imediato. O
  ganho de agnosticismo supera esse custo, mas ele existe.
- **Esforço:** Baixo

---

# Pass incremental — 2026-08-12 (2ª execução), baseline `3fbe371`

Varredura semente reexecutada **integral** sobre `agents/` e `commands/`, conforme a regra
("o Eixo A é sempre integral"): **121 candidatos**.

Arquivos de `agents/` e `commands/` tocados pelo delta `07e0725..3fbe371`:
`agents/setup-assistant.md`, `commands/commit.md`, `commands/learn.md` — **9 candidatos**
entre os 121.

| Candidato | Heading da seção | Veredito |
|---|---|---|
| `commands/commit.md:135` — "`package.json` with `lint` script → `npm run lint --silent`" | `## Step 4 — Pre-commit gates` (tabela de detecção) | Descartado — tabela de detecção, exceção explícita da regra |
| `commands/commit.md:138` — "`phpcs.xml` … → `vendor/bin/phpcs`" | idem | Descartado — mesma tabela |
| `commands/commit.md:46,50,55` — "Docker stack" | `## Step 0.5 — Worktree finalization quiz` | Descartado — refere-se ao stack Docker **isolado do worktree**, gated por `worktree_docker_isolate`; não presume Docker |
| `agents/setup-assistant.md:26,66` — "Docker Compose command form" | `## Foundational Rule` / detecção de stack | Descartado — roteia para `skills/shared/stack-detection/SKILL.md`, que é o mecanismo agnóstico |
| `agents/setup-assistant.md:146,147` — `Dockerfile`, `jest.config.*`, `pytest.ini`, `phpunit.xml` | `### Step 6 — …` (mapa de sinais → documento) | Descartado — lista de sinais de detecção, exceção explícita |

**121 candidatos → 0 violações novas.** Os 9 candidatos do delta caem todos sob tabelas de
detecção, listas de sinais ou condicionais gated — as três classes que a regra manda descartar.

**Nenhum achado original neste eixo nesta execução.** A única violação do dia
(`flow-relayout-design-discovery-names-storybook-tailwind`) já foi registrada pelo pass da manhã
e não é redescoberta aqui.
