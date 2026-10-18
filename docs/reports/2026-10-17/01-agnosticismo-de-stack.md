# Eixo A — Agnosticismo de stack — 2026-10-17

**Baseline:** `HEAD` = `bb0e883` · **Varredura integral** (`agents/` + `commands/`), como manda o
prompt — o eixo nunca é amostrado.

## Varredura semente

```bash
rg -in 'laravel|symfony|django|rails|spring|express|nest|next\.js|react|vue|angular|svelte|
tailwind|bootstrap|eloquent|prisma|hibernate|sequelize|typeorm|phpunit|jest|vitest|pytest|
rspec|composer|npm|yarn|pnpm|pip|maven|gradle|docker|kubernetes|terraform|aws|gcp|azure|
mysql|postgres|mongodb|redis|php|python|ruby|golang|typescript|javascript' agents/ commands/
```

**125 hits em 24 arquivos** (124 em 2026-10-02 e em 2026-10-10). Distribuição:
`devops-specialist` 23 · `mobile-developer` 12 · `database-specialist` 12 ·
`security-specialist` 8 · `product-analyst` 8 · `frontend-test-specialist` 8 ·
`frontend-developer` 8 · `commit.md` 5 · `setup-assistant` 5 · `backend-developer` 5 ·
`audit.md` 4 · os 13 restantes com 3 ou menos.

## Triagem

Os dois passes anteriores trabalharam o mesmo conjunto de 124 hits e fecharam em **0 violações**:
23 candidatos genuínos, todos já registrados no conjunto aberto (porta 5) ou legítimos por
desenho. Este pass não re-litiga essa triagem — ela foi feita contra evidência que não mudou.
O que mudou são as **linhas adicionadas** pelos 76 commits do delta, e é sobre elas que a
promoção foi decidida:

```bash
git diff -U0 349f18c..HEAD -- agents/ commands/ | grep '^+' | rg -in '<mesma alternância>'
```

**2 candidatos novos → 0 violações.**

### Candidato 1 — `commands/audit.md:65` · descartado (Example)

Sob `## Step 5 — Synthesize improvement plan`:

> "Refer to any secret by `file:line` and kind (e.g. `AWS access key at config/x.py:12`), never
> by its value"

`AWS` e `.py` aparecem dentro de um `(e.g. …)` que ensina o **formato** da referência a segredo,
não a tecnologia a procurar. O prompt manda descartar hits sob "Example"; este é um exemplo
inline, explicitamente marcado. A instrução de comportamento ao redor — "nunca pelo valor" — é
agnóstica.

### Candidato 2 — `commands/mobile.md:12` · descartado (tabela de detecção + já registrado)

Fora de heading, no preâmbulo do comando:

> "Phase 0 derives failing tests from the resolved scenarios and commits them red (React Native /
> Expo → `frontend-test-specialist`; Flutter or native → `mobile-developer` in a tests-only
> spawn)"

Duas razões para não promover. **(a)** É roteamento de agente por plataforma dentro do comando
*mobile* — a mesma forma que `:28-29` já carrega ("For React Native / Expo (JS/TS) suites → spawn
`frontend-test-specialist`"), que os passes anteriores classificaram como tabela de detecção
legítima: um comando cujo escopo *é* a plataforma móvel não fica mais agnóstico fingindo não
saber a diferença entre um suite JS e um suite Dart. **(b)** O acoplamento específico de
`mobile.md` já está registrado em
`flow-mobile-command-spawn-line-enumerates-stacks-dropped-from-agent-description` (MEDIUM,
aberto, `alvo: commands/mobile.md`, `:19`) — porta 5.

A **duplicação** entre `:12` e `:28-29` é um problema real, mas de forma, não de agnosticismo;
está avaliada e descartada no Eixo C (porta 3 contra o mesmo fingerprint-pai).

## Resultado

**125 hits → 2 candidatos → 0 violações. Nenhum achado original neste eixo.**

Terceiro pass consecutivo em zero. A leitura honesta: o acoplamento que resta em `agents/` e
`commands/` já está todo catalogado no conjunto aberto e não se move porque ninguém o executou —
não porque não exista. Os dois comandos novos deste delta (`commands/spec.md`,
`commands/sprint.md`, 64 e 96 linhas) **não produzem um único hit** da alternância, o que é o
dado positivo do eixo: o material novo nasceu agnóstico.
