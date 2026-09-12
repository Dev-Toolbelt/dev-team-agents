# Auditoria Guardiã — 2026-09-11

**Data:** 2026-09-11 · **Baseline:** `HEAD` = `9530551` · **Baseline anterior:** `a67cac9`

## Sumário executivo

O baseline mudou pela primeira vez em quatro passes, mas o **código** não. O único commit do delta
(`9530551 docs(reports): metrics reports updates`) tocou dois arquivos, ambos relatórios de
métricas PostHog. O último commit a tocar `agents/`, `commands/`, `skills/`, `scripts/` ou
`helpers/` é `a1e3791`, de **21 dias atrás**. Isso preserva a validade de todos os 87 vereditos da
Fase 1 registrados contra `a67cac9` e concentra o trabalho deste pass no que ainda não foi coberto.

**Integridade do banco não é o achado principal.** A amostra de 12 itens não produziu **nenhuma
🔴 nova** (0%, contra o limiar de escalonamento de 15%). As duas divergências são 🟡 de sub-escopo,
ambas com o que falta descrito por linha e arquivo.

**O achado principal é outro, e é sobre o próprio protocolo de auditoria.** A ausência de um gate
que valide a § File Structure do `CLAUDE.md` contra a árvore real produziu **quatro** divergências
em seis semanas — `docs/prompts/` (2026-08-14), 3 de 5 templates (2026-08-21), `docs/harness.md`
(2026-08-28) e `scripts/hooks/lib/agent-usage.sh` (hoje). Cada uma foi corretamente descartada como
duplicata pela Porta 3 contra a família `ref-claude-md-file-structure-*`, e por isso a **classe**
nunca foi atacada. O protocolo anti-duplicação está funcionando exatamente como especificado e, ao
fazê-lo, torna esta classe estruturalmente invisível.

**Nota operacional.** O output de três passes (61 fingerprints) seguia fora do remoto. O commit de
2026-09-04 usou a mensagem `docs(reports): metrics reports updates` — literal do template de
`docs/prompts/posthog-metrics-report.md` — e fez stage apenas dos dois arquivos de métricas. É o
mecanismo já descrito em `flow-prompt-auditoria-commit-step-contradicts-branch-rule` (MEDIUM,
aberto). Esta execução enumera os quatro diretórios pendentes no `git add`.

---

## Método

| Fase | Escopo |
|---|---|
| **0** | Banco carregado (`_index.md`, 235 fingerprints vivos); baseline anterior `a67cac9` recuperado do cabeçalho do pass de 2026-09-04; delta calculado (`1 commit, 2 arquivos, 0 de código`) |
| **1** | Verificação ancorada no git de fingerprints ✅ Executed / ⚠️ Partial não cobertos por passes anteriores |
| **1b** | Revalidação dos 113 achados abertos contra o `HEAD` |
| **2** | Cinco eixos, varredura integral no Eixo A e priorizada pelo delta nos demais |

### Cobertura da Fase 1

| Item | Valor |
|---|---|
| Conjunto verificável (✅ + ⚠️) | 121 |
| Já cobertos contra o mesmo estado de código | 87 |
| **Verificados neste pass** | **12 de 34 não cobertos (35%)** |
| **Cobertura acumulada** | **99 de 121 (82%)** |
| Critério de amostragem | HIGH e MEDIUM-HIGH: 18/18 já cobertos · amostra determinística de 35% dos 34 restantes (índices 0, 3, 6, … 33) |

### Placar

| | Bloco novo (12) | Acumulado (99) |
|---|---:|---:|
| ✅ **Feito** | 9 (75%) | 83 (84%) |
| 🟡 **Parcialmente feito** | 2 (16,7%) | 9 (9,1%) |
| 🔴 **Não feito** | 1 (8,3%) | 7 (7,1%) |

A única 🔴 do bloco (`flow-cli-commit-validate-msg-script-skipped-silently-…`) **já estava
registrada como 🔴 desde 2026-07-31**; este pass confirma que persiste. Divergências genuinamente
novas: **2 🟡**.

### Mortalidade da Fase 1b

**0 de 113 (0%).** Estrutural, não amostral: o delta tocou dois arquivos de relatório de métricas,
e nenhum dos 113 achados abertos tem alvo neles. Seis achados foram relocalizados como teste da
premissa e todos reproduzem no `HEAD`. Como nos dois passes anteriores, o indicador reflete a
imobilidade da árvore, não a durabilidade do banco.

---

## Achados originais por eixo

| Eixo | Arquivo | Originais |
|---|---|---:|
| A — Agnosticismo de stack | [01](01-agnosticismo-de-stack.md) | **0** (124 candidatos → 0 violações) |
| B — Referências e consistência | [02](02-referencias-e-consistencia.md) | **2** |
| C — Fluxos, comandos e automação | [03](03-fluxos-e-comandos.md) | **2** |
| D — Agentes e skills | [04](04-agentes-e-skills.md) | **0** |
| E — Economia de tokens | [05](05-economia-tokens.md) | **0** |
| **Total** | | **4** |

## Tabela de severidade

| Severidade | Qtd | Fingerprints |
|---|---:|---|
| **HIGH** | 1 | `docs-sync-telemetry-fresh-install-default-documented-true-while-install-sh-writes-false-without-consent` |
| **MEDIUM-HIGH** | 2 | `auto-no-gate-validates-claude-md-file-structure-tree-against-real-tree-four-recurrences-each-discarded-as-duplicate` · `docs-sync-reports-index-preamble-declares-archive-index-trigger-less-while-stop-99b-dispatches-it` |
| **MEDIUM** | 1 | `auto-check-fingerprint-uniqueness-grep-admits-discarded-candidate-lines-as-slugs-inflating-count-and-silent-sed-fallthrough` |
| LOW-MEDIUM | 0 | — |
| LOW | 0 | — |

---

## Os 3 achados mais graves

**1. `CLAUDE.md:386` e `user-preferences/SKILL.md:50,66` afirmam que `telemetry` nasce `true` em
instalação nova — `install.sh:1057` escreve `false`.** (HIGH) Dois dos quatro espelhos obrigatórios
do schema de preferências dizem o oposto do código e dos outros dois (`CLAUDE-md/preferences.md:51`
e `README.md:277` estão corretos). É texto residual do comportamento anterior a `2e12335`
(2026-07-31, *"stop enabling telemetry without consent"*): a remediação corrigiu o código e deixou
estes dois espelhos. O agravante é onde eles estão — o `CLAUDE.md` entra em toda sessão, e
`user-preferences/SKILL.md` é o documento que um agente lê quando precisa responder sobre
preferências. Um agente que cite qualquer um dos dois dá ao usuário a resposta errada sobre coleta
de dados.

**2. Nenhum gate valida a § File Structure do `CLAUDE.md`, e a lacuna é invisível ao próprio banco.**
(MEDIUM-HIGH) Quatro divergências em seis semanas, cada uma descartada individualmente pela Porta 3.
A instância de hoje: `CLAUDE.md:344-347` enumera `scripts/hooks/lib/` como três arquivos e fecha a
lista com `└──`; há quatro — falta `agent-usage.sh`, que `CLAUDE-md/hooks.md:76` documenta como a
fonte do evento `agent_completed`, **36,9% de toda a telemetria** segundo
`metrics-last-20-days.md` § 0. Os dois mapas do repositório discordam sobre a existência do arquivo
que produz o segundo maior tipo de evento.

**3. O preâmbulo do `_index.md` declara sem trigger um script que tem trigger desde 2026-07-31.**
(MEDIUM-HIGH) `_index.md:23-26` afirma que `helpers/archive-index.sh` "currently has no trigger —
no hook, no CI job, no installer call". `scripts/hooks/stop/99b-archive-index.sh` existe desde
`cc28900` e casa o `SUBSCRIPT_RE` do dispatcher; o próprio fingerprint citado no aviso está marcado
**✅ Executed: 2026-07-31** 120 linhas abaixo, no mesmo arquivo. O bloco está dentro das linhas
1-120 que a Fase 0 do prompt manda ler **antes de qualquer outra coisa**, em todo pass — é a
primeira coisa que o auditor lê, e é falsa.

---

## Descartados por duplicação

**Porta 5 (estado — item já registrado e aberto), 34:** os 22 candidatos genuínos do Eixo A
(`frontend-developer.md:3,72,91,96,134-139` · `frontend-test-specialist.md:141-153` ·
`database-specialist.md:66-73,84,133` · `devops-specialist.md:46-56,137-148` ·
`security-specialist.md:80-85` e § Tooling SAST · `backend-reviewer.md:30` ·
`frontend-reviewer.md:112,114` · `mobile-developer.md:159` e description · `setup-assistant.md:146-147` ·
`commit.md:125-133` · `audit.md:54,126,128` · `relayout.md:32` · `mobile.md:19,26,27` · `devops.md:2,14`)
· `CLAUDE.md:129` `SKILL_DESC_STRICT=false` vs. `true` · `CLAUDE.md:92,313` teto 205 vs. `AGENT_LIMIT=211`
· `CLAUDE.md:109` lista oito coding agents e há nove · README omite `/devteam:install` ·
par `metrics-last-20-days.md`/`.en.md` fora do gate de sync · output de três passes fora do remoto ·
bloco de commit do prompt dizendo "two report files" · Plan Gate insatisfazível em execução
desassistida · `commands/commit.md:144-147` · `seo-specialist` fora do contrato de coding agent ·
três agentes em 211 linhas · `spec-gate` inalcançável pelos coding agents · `migration-v1-to-v2`
438×1 · `orchestration` 391 sem `references/` · `interaction-patterns` 209×34 · `token-efficiency`
160×18 · `CLAUDE.md` 602 linhas monolítico.

**Porta 3 (semântica — 2 ou 3 de 3 atributos), 6:** `CLAUDE.md:344-347` omitindo
`hooks/lib/agent-usage.sh` (**3 de 3** contra a família `ref-claude-md-file-structure-*` — mesma
porta pela qual `docs/prompts/` caiu em 2026-08-14 e `docs/harness.md` em 2026-08-28) ·
`product-analyst.md:128-153` restatando a mecânica da cascata de worktree (2 de 3 contra
`token-worktree-isolation-block-7-lines-x-8-agents`) · `CLAUDE-md/*.md` sem teto em
`size-limits.sh` (2 de 3 contra `token-claude-md-426-lines-still-monolithic-…`) · os quatro docs de
instalação sem menção a telemetria/`PRIVACY.md` (2 de 3 contra o achado HIGH deste pass) ·
`docs/prompts/` e `docs/reports/` como dois lares para prompts (2 de 3) · 3 cargas duplicadas do
`orphan-skill-scan` (falsos positivos do scanner, já verificados em 2026-08-21).

**Porta 4 (escopo menor sem sub-escopo novo), 2:** `output-format` 203 × 9 sítios (terceira vez que
cai por esta porta; o único sub-escopo já é `token-output-format-third-copy-of-plan-format-…`) ·
`preferences.json` lido inteiro em 31 sítios.

**Hipóteses refutadas por evidência (não chegaram a candidato), 5:** `99b-archive-index.sh` "não
usa o fast-path do dispatcher" (o cabeçalho `:11-12` justifica: gate temporal, com stamp diário em
`:26-30`) · `software-architect` "carrega 29 skills incondicionalmente" (24 estão sob
`**Conditional skill loads**`, `:31-56`) · `comments-policy` "duplicada em 15 agentes" (15
formulações distintas, particularizadas por papel) · Foundational Rule "idêntica nos três
reviewers" (é a linha única de delegação que o `CLAUDE.md` prescreve) · `/devteam:seo` "declarado
mas não disparado" (honrado em `frontend.md:21`, `fullstack.md:21-22` e `spawn-classifier:38-39`).

**Verificados como corretos (nenhuma divergência), 3:** `commands.json` × tabela do `CLAUDE.md` ×
arquivos em `commands/` (35 = 35 = 35) · `tiers.json` `agent_effort` × os cinco especialistas
nomeados no `CLAUDE.md` · resolução de todas as referências de template
(`orphan-template-scan: clean ✓`).

---

## Gates executados

```
bash helpers/agent-lint.sh                   → agent-lint: clean ✓                (exit 0)
bash helpers/orphan-template-scan.sh         → orphan-template-scan: clean ✓
bash helpers/orphan-skill-scan.sh            → 3 avisos (falsos positivos verificados)
bash helpers/size-limits.sh                  → ⚠ CLAUDE.md: 602 linhas (achado já aberto)
bash helpers/check-fingerprint-uniqueness.sh → ✓ All 237 slugs unique             (ver Eixo C, achado 4)
bash helpers/archive-index.sh --dry-run      → nenhuma seção com mais de 90 dias; nada a rotacionar
```
