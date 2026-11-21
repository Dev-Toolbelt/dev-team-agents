# Eixo C — Fluxos, Comandos e Automação — 2026-11-21

**Baseline:** `HEAD` = `17bfb26`

---

## Resultado

**Nenhum achado original neste eixo.**

O delta trouxe um comando novo (`commands/brief.md`), um hook novo
(`scripts/hooks/pre-tool-use/03c-modern-web-guidance-guard.sh`) e duas chaves novas no mapa de docs.
Cinco sondagens foram feitas sobre eles; todas as cinco premissas foram refutadas pela evidência.

---

## Sondagens e por que cada uma caiu

### 1. Ordem e custo do dispatcher de `Stop`

**Hipótese:** com 16 sub-scripts em `scripts/hooks/stop/` (12 deles `03*`), o dispatcher roda tudo em
todo turno sem saída rápida.

**Refutada.** `scripts/hooks/stop.sh:44-51` computa os caminhos tocados **uma vez** e exporta para os
filhos — "Only worth computing when something changed — with `DEVTEAM_NO_CHANGES=1` every consumer
exits at its own fast path anyway" (`:40-41`) — com
`DEVTEAM_TOUCHED_PATHS`/`DEVTEAM_TOUCHED_COMPUTED` em `:52`. O laço de `:64` filtra por
`SUBSCRIPT_RE` (`:62`) para não auto-executar rascunhos, e `:77` aplica a mesma regra de precedência
do `pre-tool-use` (exit 2 nunca mascarado por exit 1). `:84-87` zera o exit 2 quando
`stop_hook_active: true`, para que uma condição que o turno não pode limpar não bloqueie para sempre.
É um dispatcher com gate, não sem.

### 2. Registro do hook novo

**Hipótese:** `03c-modern-web-guidance-guard.sh` entrou sem registro na documentação de hooks nem na
lista de exceções de exit code.

**Refutada, e com folga.** `CLAUDE-md/hooks.md:59` o registra na linha dos guards `03-`;
`:70` o inclui na lista nominal das cinco exceções de exit 2; `:84` dedica um parágrafo ao
comportamento, ao fail-open e à ausência de variável de bypass; e
`tests/test_modern_web_guidance_guard.py` (170 linhas, novo no delta) cobre o payload de cada
provider.

### 3. Chaves novas no mapa de docs

**Hipótese:** `client-briefing` e `brand-guide` entraram em `scripts/lib/doc-layouts.json` sem o
espelho bash, quebrando `bash .dev-team-agents/scripts/doc-path.sh <key>` que `commands/brief.md:21`
invoca.

**Refutada.** `scripts/lib/docs-root.sh:42` (`client-briefing) "product/briefing.md"`) e `:44`
(`brand-guide) "design/brand-guide.md"`) espelham o JSON, e as 21 chaves com coluna `development`
não-nula casam uma a uma entre os dois arquivos.

### 4. Roteamento automático do comando novo

**Hipótese:** `/devteam:brief` não aparece em `skills/shared/auto-routing/SKILL.md`,
`skills/shared/spawn-classifier/SKILL.md` nem `agents/orchestrator.md` — logo é inalcançável sem
invocação explícita.

**Medida, mas não é achado deste eixo.** `auto-routing` menciona 4 de 43 comandos,
`spawn-classifier` 0 de 43 e `orchestrator.md` 11 de 43. A lacuna é geral, não do `brief`: já está
registrada como `flow-orchestrator-route-table-covers-10-of-42-commands-no-gate` (aberta) e sua
refinação `agent-orchestrator-route-has-no-path-to-architecture-work`. Porta 5 — reapresentar item
aberto é ruído. Virou **re-medição** do pai: 10 de 42 → **11 de 43**, registrada na
[Fase 1b](00-guardiao-verificacao.md#fase-1b--validade-dos-achados-abertos).

### 5. Gates e ordem de spawn de `commands/brief.md`

**Hipótese:** o comando novo tem etapa redundante, gate ausente ou paralelismo não explorado.

**Refutada em cada ponto.** O Step 1 (`:18-23`) delega os nomes de input, o local, a checagem de
git-ignore e a regra de conteúdo não confiável a uma casa única
(`skills/shared/client-briefing/SKILL.md` § Inputs) em vez de restatá-los — exatamente a doutrina de
Canonical Rule Homes. O Step 1.3 cobre os três estados de input (ambos, exatamente um, nenhum) com
`AskUserQuestion`, e o Step 2 fecha o caso degenerado com "Never guess, never fabricate a briefing or
a palette". O Step 3 (`:36`) exige o run banner como prova de spawn — "no banner, no Step 4" — via
`skills/architecture/orchestration/SKILL.md` § Spawn Integrity. A serialização do Step 4 é
**justificada e não redundante** (`:38`: "Run after Step 3 (sequential: the briefing is its
supporting context)"): o briefing é entrada do guia de marca, então não há paralelismo a explorar. O
Session close declara a árvore suja de propósito e nomeia o próximo passo.

O único defeito que a leitura de `brief.md` produziu é do **Eixo D**: o comando compensa, de fora,
uma instrução que o corpo do `product-analyst` tem sob condição errada — ver
[`04-agentes-e-skills.md`](04-agentes-e-skills.md).
