# Fluxos e Workflows — 2026-05-20

> Sugestões **originais** de melhoria em fluxos, hooks e gates de CI/Stop. Cada item traz
> evidência, motivo, impacto positivo, risco/impacto negativo e recomendação.

---

## F1 — CI roda `orphan-skill-scan` com `continue-on-error: true`; 2 warnings de peso parados há dias  · **MEDIUM**

**Fingerprint:** `flow-ci-orphan-skill-scan-step-continue-on-error-true-never-blocks-two-duplicate-loads-standing-unaddressed-for-days`

**Evidência:** `.github/workflows/ci.yml`:

```
20  - name: Orphan skill scan
21    run: bash helpers/orphan-skill-scan.sh
22    continue-on-error: true
```

- `continue-on-error: true` faz o step **nunca** falhar o build.
- `bash helpers/orphan-skill-scan.sh` reporta **hoje** 2 ocorrências: `ui-ux-designer.md` carrega
  `design-system-audit/SKILL.md` mais de uma vez, e `commands/update.md` carrega
  `interaction-patterns/SKILL.md` mais de uma vez. Esses 2 avisos aparecem nas auditorias desde, ao
  menos, 2026-05-18 — **sem correção**.

**Motivo:** o único gate de CI que detecta drift de carga de skills é declarado como não-bloqueante.
Resultado prático: os warnings viram ruído permanente que ninguém é forçado a resolver (já são "wallpaper"
no log de CI). É um padrão diferente do `flow-size-limits-sh-…-warn-only` (2026-05-19): aquele é sobre
o script `size-limits.sh` chamado com a flag `--warn-only`; **este** é sobre o step do `orphan-skill-scan`
neutralizado pelo `continue-on-error` do GitHub Actions — mecanismo de "não bloqueio" distinto, em
script distinto, e com achados concretos parados.

**Impacto positivo:** transformar o step em bloqueante (ou em "bloqueia apenas duplicatas reais, ignora
falsos positivos conhecidos") força a limpeza dos 2 loads duplicados e impede novos; o scanner volta a
ter dentes.

**Impacto negativo / risco:** ligar bloqueio **hoje** quebraria o CI imediatamente (2 achados ativos).
Além disso, o scanner ainda confunde "load real" com "referência narrativa" (falsos positivos já
documentados em 2026-05-18). Bloquear sem antes ensinar o scanner a distinguir os 3 tipos de menção
geraria falhas legítimas misturadas com ruído.

**Recomendação:** (1) primeiro, corrigir os 2 loads duplicados reais; (2) ensinar o scanner a ignorar
menções narrativas ("already loaded above") — reduzindo falsos positivos; (3) só então remover o
`continue-on-error: true`. Enquanto isso, manter um baseline com os falsos positivos conhecidos para
não bloquear neles.

---

## F2 — Gate de sync de README/docs tem **3 pares hardcoded**; novos pares de tradução não são descobertos  · **MEDIUM**

**Fingerprint:** `flow-readme-sync-ci-hardcodes-three-doc-pairs-no-glob-discovery-any-new-pt-br-translation-pair-silently-unchecked`

**Evidência:** `.github/workflows/ci.yml:65-69`:

```
FAIL=0
check_pair README.md README.pt-BR.md || FAIL=1
check_pair docs/agents.md docs/agents.pt-BR.md || FAIL=1
check_pair docs/installation.md docs/installation.pt-BR.md || FAIL=1
exit $FAIL
```

**Motivo:** os 3 pares EN↔PT-BR são listados manualmente. Se alguém adicionar um novo documento
traduzido — por exemplo `docs/configuration.md` + `docs/configuration.pt-BR.md`, ou um `CONTRIBUTING.pt-BR.md`
— o gate **não o verificará**, porque não há descoberta automática (glob por `*.pt-BR.md` com derivação
do par EN). A "README Sync Rule" do CLAUDE.md fala em manter traduções sincronizadas, mas o gate só
cobre o que foi lembrado de cadastrar à mão → cobertura silenciosamente incompleta para qualquer par
futuro. É **distinto** do F2 de 2026-05-19 (que era sobre a checagem ser só estrutural, não de conteúdo);
aqui o ângulo é a **ausência de descoberta automática de pares**.

**Impacto positivo:** qualquer par `*.pt-BR.md` novo passa a ser verificado automaticamente; a regra de
sync deixa de depender de memória do colaborador.

**Impacto negativo / risco:** glob automático pode pegar pares incompletos durante um PR que adiciona só
o EN (a tradução vem depois) → falha legítima, mas potencialmente irritante. Mitigar tratando "EN existe,
PT-BR ausente" como aviso configurável, e exigindo o par apenas no merge para `main`.

**Recomendação:** substituir as 3 chamadas hardcoded por um loop que descobre `*.pt-BR.md`, deriva o
arquivo EN correspondente e roda `check_pair` em cada par encontrado; manter uma allowlist de exceções
para docs que intencionalmente não têm tradução.

---

## F3 — CI dispara em `push` **e** `pull_request`, ambos `["**"]`; toda branch de PR roda CI em dobro  · **LOW-MEDIUM**

**Fingerprint:** `flow-ci-triggers-both-push-and-pull-request-on-all-branches-duplicate-runs-no-concurrency-cancel-in-progress-guard`

**Evidência:** `.github/workflows/ci.yml:3-7`:

```
on:
  push:
    branches: ["**"]
  pull_request:
    branches: ["**"]
```

**Motivo:** com `push` em todas as branches **e** `pull_request` em todas as branches, uma branch que
tem um PR aberto dispara **dois** workflows a cada push (um pelo evento `push`, outro pelo
`synchronize` do PR). É desperdício de minutos de runner e duplica a sinalização de status. Não há
bloco `concurrency:` para cancelar execuções em andamento quando um novo push chega, então pushes
rápidos enfileiram execuções redundantes. É um item **novo** de eficiência de fluxo.

**Impacto positivo:** ~50% menos execuções de CI em branches com PR; com `concurrency` + `cancel-in-progress`,
pushes consecutivos cancelam runs obsoletos → feedback mais rápido e menos fila.

**Impacto negativo / risco:** restringir `push` a `main`/`tags` faz com que branches **sem PR** não
recebam CI (alguns fluxos dependem de validar antes de abrir o PR). Decisão de trade-off: ou aceitar
que CI só roda via PR, ou manter push só em `main` + confiar no PR para branches de feature.

**Recomendação:** (1) restringir `push` a `["main"]` (e tags, se houver release por tag) e deixar o
`pull_request` cobrir as branches de feature; **ou** (2) manter ambos mas adicionar
`concurrency: { group: ci-${{ github.ref }}, cancel-in-progress: true }` para eliminar runs
sobrepostos. A opção (1) economiza mais; a (2) é mais conservadora.

---

## Itens reverificados (já no índice; ver Guardian)

`flow-size-limits-sh-ci-only-warn-only-...`, `flow-stop-dispatcher-globs-all-sh-no-allowlist-...`
(o mesmo glob não guardado existe também em `pre-tool-use.sh:11` — ver nota Guardian),
`flow-readme-sync-ci-gate-checks-only-section-count-and-50pct-...` e
`flow-workflow-detection-skill-only-loaded-by-software-architect` continuam **🔴 não feitos**
(0 commits na janela). Não repropostos.
