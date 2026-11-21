# Eixo A — Agnosticismo de Stack — 2026-11-21

**Baseline:** `HEAD` = `17bfb26` · varredura **integral** de `agents/` e `commands/`, mais varredura
complementar sobre a superfície autoral do delta.

---

## Resultado

**Nenhum achado original neste eixo.**

`130 hits → 14 candidatos → 0 violações.` Sexto zero em sete passes.

---

## Varredura semente (obrigatória, integral)

```bash
rg -in 'laravel|symfony|django|rails|spring|express|nest|next\.js|react|vue|angular|svelte|\
tailwind|bootstrap|eloquent|prisma|hibernate|sequelize|typeorm|phpunit|jest|vitest|pytest|\
rspec|composer|npm|yarn|pnpm|pip|maven|gradle|docker|kubernetes|terraform|aws|gcp|azure|\
mysql|postgres|mongodb|redis|php|python|ruby|golang|typescript|javascript' agents/ commands/
```

**130 hits** em 27 arquivos (idêntico em contagem ao pass de 2026-11-07; o delta não moveu o total).
Distribuição: `devops-specialist` 24 · `mobile-developer` 12 · `database-specialist` 12 ·
`security-specialist` 8 · `product-analyst` 8 · `frontend-test-specialist` 8 · `frontend-developer` 8
· `commit.md` 5 · `backend-developer` 5 · demais ≤ 4.

### Promoção para candidato

A superfície autoral do delta em `agents/`+`commands/` são 6 arquivos:
`agents/frontend-developer.md`, `agents/frontend-reviewer.md`, `agents/product-analyst.md`,
`agents/security-specialist.md`, `agents/ui-ux-designer.md`, `commands/brief.md`. Os hits dos outros
21 arquivos já foram promovidos, julgados e registrados em passes anteriores — reavaliá-los seria
redescobrir becos sem saída (Porta 5). Os hits dos 6 arquivos do delta:

| Arquivo | Hits | Candidatos | Por que caíram |
|---|---|---|---|
| `agents/frontend-developer.md` | 8 | 2 | `:3` é a `description:`, que nomeia os dois modos deliberadamente ("decoupled SPAs (React, Vue, Svelte, Angular) **and** server-rendered templates (Blade, Twig, ERB, Jinja)") — equilíbrio explícito, não acoplamento · `:70,71,84` são **tabelas de detecção** com rota para `skills/ui-libraries/*` (exceção legítima por design) · `:139` fala de "DI container or an explicit bootstrap", genérico · **`:147` já é achado aberto** (`agent-frontend-developer-testability-presumes-reactive-component-model`, Porta 5) |
| `agents/frontend-reviewer.md` | 2 | 2 | ambos sob `### 10. Type Safety` (`:111`), cuja primeira linha é "Apply **whatever type discipline the project has adopted** — a type system, a runtime prop/schema validator, or documented contracts". `:114` cita três ecossistemas lado a lado ("TypeScript interfaces, PropTypes, or Vue `defineProps`") e `:116` dá `React.ChangeEvent<HTMLInputElement>` como `e.g.` de um padrão agnóstico ("a generic `Event` where the specific event type exists"). O heading desautoriza o acoplamento antes de citá-lo |
| `agents/product-analyst.md` | 8 | 4 | `:96` é "real technical limitation", falso positivo do regex · `:194` enumera trackers sem skill para **recusar** improvisar (`ClickUp, Trello, Asana…`) e já é achado aberto · `:171` roteia para `skills/shared/worktree/references/docker-isolation.md` · **`:148,164-168` já é achado aberto** (`agent-product-analyst-step6-gates-isolated-infra-on-docker-and-inlines-compose-probe`, Porta 5) |
| `agents/security-specialist.md` | 8 | 3 | `:3` é `description:` listando os domínios de auditoria · `:28,29` leem `Dockerfile`/`docker-compose.yml` **e** `.gitlab-ci.yml`/`bitbucket-pipelines.yml` na mesma frase — cobertura, não monocultura · `:48,148` são tabelas de rota condicional para `skills/security/sast-pipeline` e `skills/integrations/wordpress` (exceção por design) · **`:82,86` já é achado aberto** (`agent-security-specialist-cicd-checklist-github-actions-only-vocabulary`, Porta 5) |
| `agents/ui-ux-designer.md` | 3 | 0 | `:60-62` é a tabela de detecção de plataforma móvel, roteando para `skills/mobile/ios-hig` e `skills/mobile/material-design` — exceção explícita da regra do eixo |
| `commands/brief.md` | 0 | 0 | o comando novo do delta não nomeia linguagem, framework, ferramenta ou plataforma em nenhuma linha |

**14 candidatos → 0 violações.** Os 14−0 caíram por três razões, nesta proporção: **5** sob heading
que desautoriza explicitamente o acoplamento ou sob `description:` que nomeia os dois lados; **5** em
tabela de detecção ou rota condicional para skill de referência específica (exceção por design);
**4** já pertencem ao conjunto aberto (Porta 5).

---

## Varredura complementar — o delta vendorizado e as skills novas

O delta deste pass é dominado por um skill de terceiros (190 guias de
`skills/third-party/modern-web-guidance/guides/`) e por três skills autorais novas. A regra do eixo
cobre `agents/` e `commands/`; como em 2026-11-14, a varredura foi estendida às skills autorais do
delta, que todo agente de frontend carrega:

```bash
rg -in '<mesma lista>' skills/shared/client-briefing/ skills/design/brand-design-system/ \
  skills/architecture/third-party-web-skills/SKILL.md skills/shared/doc-flow/SKILL.md \
  skills/shared/docs-sync/SKILL.md skills/shared/frontend-done-checklist/SKILL.md \
  commands/brief.md templates/process-template.md
```

**1 hit, 0 candidatos.** `skills/architecture/third-party-web-skills/SKILL.md:69` nomeia `npx` e
`npm install` exatamente para **proibi-los**: "Nothing. It ships as Markdown only; its command-line
tool is not vendored […] The tool is never downloaded or run, by any runner." Citar a ferramenta para
vedá-la é o oposto de acoplar-se a ela.

Vale registrar o contrário do que se esperaria de um delta que vendoriza 190 guias de plataforma web:
a ponte `third-party-web-skills` é **mais** agnóstica que a média do repositório. `:9` subordina o
conteúdo de terceiros às regras do projeto — "Project rules, the project's design system, the UI
library skill in use (`skills/ui-libraries/`) and the framework's own frontend skills […] win over a
third-party guide" — e a tabela de `:49-56` desautoriza, item por item, as instruções upstream que
pressupõem um runner de pacotes. `skills/design/brand-design-system/SKILL.md` não nomeia uma única
ferramenta de build, framework ou linguagem em 69 linhas.
