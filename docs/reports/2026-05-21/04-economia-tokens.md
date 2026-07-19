# Economia de Tokens — 2026-05-21

> 3 sugestões originais focadas em desperdício de tokens/overhead nos agentes e hooks. Cada item traz **evidência**, **motivo** e **impactos positivos e negativos**. Deduplicadas contra os 437 fingerprints.

---

## T1 — Bloco de comandos SAST do `security-specialist` (~24 linhas) é carregado eager em todo spawn, virando peso morto em stacks que não o usam

**Severidade:** MEDIUM
**Fingerprint:** `token-security-specialist-sast-command-block-24-lines-eager-loaded-every-spawn-dead-weight-on-non-matching-stacks`

**Evidência** — `agents/security-specialist.md:130-153` (o bloco bash detalhado em A1: `semgrep`/`bandit`/`npm audit`/`composer audit`/`pip-audit`/`trivy`/`snyk`). São ~24 linhas (~300-400 tokens) presentes no corpo do agente.

**Motivo:** por estar no corpo (e não numa skill com gate), o bloco inteiro é carregado **em todo spawn** do `security-specialist`, independentemente da stack do projeto. Um projeto Python puro carrega as linhas de `composer audit`/`npm audit`; um projeto Node carrega `bandit`/`pip-audit`. A maior parte do bloco é peso morto em qualquer stack específica. É o angle de **token** do achado A1 (stack-prescritivo) — mesma raiz, dimensão diferente, seguindo o padrão de relatórios anteriores (registrar a violação agnóstica e o custo de token separadamente).

**Impacto positivo da correção:** mover a matriz para uma skill com gate de detecção do ecossistema faz o agente carregar só os comandos relevantes (ou nenhum, até o gate disparar); economiza ~300-400 tokens/spawn em projetos single-stack; amplifica em fluxos onde o `security-specialist` é spawnado junto com outros (`/devteam:review`, `/devteam:security`).

**Impacto negativo / risco:** indireção (já discutida em A1); risco de o LLM carregar a skill "por precaução" e anular a economia se o gate for narrativo em vez de determinístico — por isso o gate deve ser por sinal de detecção, não por frase.

---

## T2 — A própria skill `token-efficiency` (154 linhas) é carregada eager pelos 17 agentes — ironia meta, multiplicada em fluxos multi-agente

**Severidade:** MEDIUM
**Fingerprint:** `token-token-efficiency-skill-itself-154-lines-eager-loaded-by-all-17-agents-meta-irony-multiplied-in-multi-agent-flows`

**Evidência:**

```
$ wc -l skills/shared/token-efficiency/SKILL.md   → 154
$ grep -rl "token-efficiency/SKILL.md" agents/ | wc -l → 17  (todos os agentes)
```

A CLAUDE.md inclusive já inlina as regras essenciais ("Key rules (apply without loading the full skill): prefer grep/head/tail…") e diz para carregar a skill completa apenas em casos específicos (autoria/otimização, seleção de modelo multi-step).

**Motivo:** a skill cuja função é **economizar tokens** é carregada na íntegra (154 linhas, ~2.000 tokens) por todos os 17 agentes, mesmo quando as "key rules" já estão na CLAUDE.md e bastariam para a maioria das tarefas. Em `/devteam:fullstack` (até 6 agentes) isso é ~12.000 tokens só da skill de economia de tokens, repetida. Inédito no banco (nenhum fingerprint sobre a `token-efficiency` em si — só sobre divergência da *linha de carga* dela, 2026-05-18). Distinto de `project-context` (já flagrada por tamanho×14 agentes): aqui o ponto é a auto-referência — a ferramenta de economia é o próprio gasto.

**Impacto positivo da correção:** trocar a carga eager por uma diretiva "as key rules estão na CLAUDE.md; carregue a skill completa só ao [autorar agente / otimizar workflow / escolher modelo]" remove ~2.000 tokens/agente do caso comum; o ganho escala linearmente com o nº de agentes do fluxo.

**Impacto negativo / risco:** depende de as "key rules" da CLAUDE.md realmente cobrirem o dia a dia (cobrem: grep/head/tail, cp/sed/awk, summarize output, --quiet). Se um agente precisar do detalhe e não carregar, pode perder uma otimização — mas o gate cobre exatamente esses casos. Requer confiar que a CLAUDE.md (já sempre em contexto) é fonte suficiente.

---

## T3 — `01-check-updates.sh` faz fork de `python3` para ler o intervalo de update ANTES do early-exit por TTL, em toda chamada de tool

**Severidade:** MEDIUM
**Fingerprint:** `token-pre-tool-use-01-check-updates-forks-python3-to-read-interval-before-ttl-early-exit-on-every-tool-call-burst-overhead`

**Evidência** — `scripts/hooks/pre-tool-use/01-check-updates.sh`, ordem das operações:

```bash
# 1) Lê update_check_interval_hours via python3  ← fork de python ACONTECE AQUI
UPDATE_INTERVAL_HOURS=24
if [ -f "$PREFS_FILE" ] && command -v python3 >/dev/null 2>&1; then
    UPDATE_INTERVAL_HOURS=$(python3 -c "import json; ...")
fi
TWENTY_FOUR_HOURS=$(( UPDATE_INTERVAL_HOURS * 3600 ))

# 2) SÓ DEPOIS checa o TTL e sai cedo
if [ -f "$LAST_CHECK_FILE" ]; then
    ... if [ "$DIFF" -lt "$TWENTY_FOUR_HOURS" ]; then exit 0; fi
fi
```

**Motivo:** `PreToolUse` dispara a **cada chamada de tool**. Na esmagadora maioria das chamadas (dentro da janela de 24h), o script vai sair cedo pelo TTL. Mas ele faz o **fork de `python3`** (~30-50ms) para ler `update_check_interval_hours` *antes* de chegar ao early-exit. Numa sessão burst (`/devteam:fullstack` ≈ 40+ tool calls), são ~40 forks de python (~1,5-2s acumulados) só para ler um valor de config que muda no máximo uma vez a cada 24h. É um sub-angle **mais específico** do `flow-pre-tool-use-01-check-updates-runs-every-tool-call-but-has-no-rate-limit-beyond-24h-cache` (2026-05-19): aquele dizia "roda em todo tool call"; este aponta o **erro de ordenação** — o cache de 24h não evita o fork porque o fork vem antes da checagem do cache.

**Impacto positivo da correção:** inverter a ordem — ler o `.last-update-check` e comparar contra um intervalo default (24h) **primeiro**, e só fazer o fork de python para refinar o intervalo quando um refresh estiver realmente devido — elimina ~40 forks de python por sessão burst. Ganho concentrado exatamente nas sessões mais pesadas.

**Impacto negativo / risco:** se o usuário configurou `update_check_interval_hours` para **menos** de 24h, usar o default 24h no short-circuit poderia atrasar a checagem até o próximo tool call após o TTL default. Mitigável usando o **menor** entre default e o último valor conhecido, ou cacheando o intervalo lido num arquivo `.update-interval-cache` lido com um único `cat` (sem python). Risco baixo; o pior caso é uma checagem de update levemente atrasada, nunca perdida.
