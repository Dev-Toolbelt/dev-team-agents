# Eixo C — Fluxos, Comandos e Automação

**Data:** 2026-07-31 · **Baseline:** `f54569a` · **Prioridade:** delta de 268 arquivos (`scripts/` 25, `commands/` 24)

---

## MEDIUM-HIGH

### `plan_gate` é declarado canônico em `commands.json`, não é lido por nenhum código, e já divergiu em 1 dos 6 comandos `required`

- **Fingerprint:** `auto-commands-json-plan-gate-field-has-no-consumer-and-no-validator-architect-declared-required-but-body-carries-no-plan-step`
- **Alvo:** `scripts/lib/commands.json`
- **Evidência:**
  `CLAUDE.md:215` — "o valor `plan_gate` canônico por comando vive em `scripts/lib/commands.json`
  (`required` / `conditional` / `opt_out`)".
  Mas `grep -rn 'plan_gate' --include='*.py' --include='*.sh' .` retorna **zero** hits fora do
  próprio JSON: nem `scripts/lib/render_provider.py`, nem `helpers/`, nem `.github/scripts/ci/`
  leem o campo.
  E a divergência já ocorreu: dos 6 comandos `required`,
  `plan` / `refactor` / `security` / `setup` / `adr` têm **2** referências a `plan-mode` / "Plan
  Gate" no corpo cada; `commands/architect.md` tem **0** — `grep -ci 'plan-mode\|Plan Gate'
  commands/architect.md` → `0`, em um arquivo de 47 linhas cujo bloco de orquestração
  (`commands/architect.md:19-31`) delega tudo ao agente.
- **Problema:** `plan_gate` é metadado declarativo sem consumidor e sem validador. Nada garante que
  um comando marcado `required` de fato carregue o gate, e nada impede que um comando `opt_out`
  ganhe um. O campo descreve uma intenção que o repositório não verifica.
- **Por que importa:** o Plan Gate é a regra mais forte do `CLAUDE.md` ("**Never execute and then
  explain**"). No caso do `architect`, o gate ainda é alcançado por acidente feliz —
  `agents/software-architect.md:21` carrega `plan-mode` por conta própria — mas isso é uma
  propriedade do *agente*, não do comando. Trocar o agente de `architect` para outro que não carregue
  `plan-mode` remove o gate silenciosamente, e nenhum gate pega. Os outros cinco `required` protegem
  o caso no corpo do comando; `architect` depende de terceiros.
- **Proposta:** adicionar ao `helpers/agent-lint.sh` (ou a um `helpers/command-gate-lint.sh` chamado
  pelo mesmo wrapper `blocking` do `01-lint.sh`) uma checagem: todo comando com
  `plan_gate == "required"` em `commands.json` deve conter ao menos uma referência a
  `skills/shared/plan-mode/SKILL.md` no corpo; todo `opt_out` não deve conter nenhuma. Corrigir
  `commands/architect.md` acrescentando a linha de carga que os outros cinco já têm.
- **Impacto positivo:** o campo passa a ter um consumidor, que é o que o transforma de comentário em
  contrato. 6 comandos ganham verificação contínua de uma regra que hoje é honrada por convenção.
- **Impacto negativo / risco:** o lint passa a acoplar `commands.json` ao *texto* dos comandos, e um
  comando que legitimamente delegue o gate ao agente (como `architect` faz hoje) passa a falhar o
  CI até ser reescrito — ou a precisar de uma terceira categoria (`delegated`), que é justamente a
  ambiguidade que a política de `01-lint.sh:20-24` proíbe. A decisão real é: `architect` deve
  carregar o gate ou declarar `conditional`? Escolher uma antes de escrever o lint.
- **Esforço:** Médio

---

## LOW

### `02b-telemetry.sh` prefere `DEVTEAM_HOOK_PAYLOAD`, que só o dispatcher de Stop define

- **Fingerprint:** `flow-pre-tool-use-02b-telemetry-reads-devteam-hook-payload-branch-that-only-stop-dispatcher-ever-sets-dead-path-in-pretooluse`
- **Alvo:** `scripts/hooks/pre-tool-use/02b-telemetry.sh`
- **Evidência:**
  `scripts/hooks/pre-tool-use/02b-telemetry.sh:26-31` —
  `if [ -f "${DEVTEAM_HOOK_PAYLOAD:-}" ]; then PAYLOAD=$(cat "$DEVTEAM_HOOK_PAYLOAD" …) elif [ ! -t 0 ]; then PAYLOAD=$(cat …) fi`,
  precedido pelo comentário `:24-25` que já admite o descompasso: "stdin was captured by the
  dispatcher into DEVTEAM_HOOK_PAYLOAD, **but PreToolUse dispatcher passes it via stdin directly**".
  De fato: `scripts/hooks/stop.sh:17` — `export DEVTEAM_HOOK_PAYLOAD="$HOOK_TMP"`;
  `scripts/hooks/pre-tool-use.sh:14` — `INPUT=$(cat)` e `:35` — `echo "$INPUT" | env … bash "$script"`,
  sem nenhum export equivalente.
- **Problema:** o ramo preferido do `if` é morto no contexto em que o script roda. Os dois
  dispatchers têm contratos de entrega de payload diferentes — arquivo+env var no Stop, stdin no
  PreToolUse — e o sub-script carrega código para os dois.
- **Por que importa:** consequência funcional hoje é nula (o `elif` cobre o caso real). O custo é de
  manutenção e de risco latente: se um dia `DEVTEAM_HOOK_PAYLOAD` vazar para o ambiente de um
  PreToolUse — por herança de env de um processo pai, ou porque alguém unificar os dispatchers — o
  sub-script lê um payload de Stop **obsoleto** e emite telemetria com o `tool_name` errado. O
  `trap 'rm -f "$HOOK_TMP"' EXIT` do Stop reduz a janela, mas não a fecha.
- **Proposta:** unificar o contrato — fazer `pre-tool-use.sh` exportar `DEVTEAM_HOOK_PAYLOAD` como
  `stop.sh` faz, **ou** remover o primeiro ramo de `02b-telemetry.sh` e ler só de stdin. A segunda é
  menor e suficiente; a primeira é a que remove a assimetria entre os dois dispatchers.
- **Impacto positivo:** um caminho de leitura de payload em vez de dois; o comentário que documenta
  a discrepância deixa de ser necessário.
- **Impacto negativo / risco:** se a opção escolhida for remover o ramo, o script deixa de funcionar
  caso algum dia seja movido para `stop/` — improvável, mas é uma porta que se fecha. Se for
  unificar os dispatchers, `pre-tool-use.sh` passa a criar e apagar um tempfile **em toda chamada de
  ferramenta**, o que é exatamente o custo por-tool-call que outro achado do banco quer eliminar.
  A opção barata é a certa aqui.
- **Esforço:** Baixo

---

## Candidatos descartados neste eixo

| Candidato | Porta / motivo |
|---|---|
| `pre-tool-use.sh` não computa estado compartilhado (`DEVTEAM_NO_CHANGES` / touched-paths) como `stop.sh` faz, e cada sub-script paga seu próprio guard em toda chamada de ferramenta | **Porta 5 (estado)** — o custo por-tool-call do PreToolUse pertence a `flow-telemetry-pre-tool-use-02-runs-on-every-tool-call-without-batching-or-deduplication-burns-200ms-per-burst-session`, **reaberto como 🔴 nesta mesma Fase 1**. Reapresentar um achado que este pass acabou de declarar não-implementado é ruído |
| `01-check-updates.sh` e `02b-telemetry.sh` re-derivam independentemente `USER_DATA_DIR` / `PREFS_FILE` | **Porta 3** — mesmo alvo, mesma causa raiz e mesma remediação do item acima |
| `commit` / `learn` / `pr` são `conditional` sem nenhum passo de plano no corpo | `conditional` significa exatamente "o comando decide"; não há contrato violado. Diferente de `architect`, que é `required` |
| `symlinks` é `opt_out` e menciona "Plan Gate" | `commands/symlinks.md:14` menciona para **negar** — "does **not** load `current-context` and has no Plan Gate". Coerente |
| Ordem de spawn e paralelismo dos comandos multi-agente | Verificado contra a tabela de `CLAUDE.md:183-207`: os marcadores ¹ (condicional) e ² (test-gated) batem com o corpo dos 7 comandos que os usam; `TESTS_REQUIRED` aparece em exatamente os 7 comandos marcados ². **Nenhum achado original neste sub-eixo** |
| `stop.sh` / `pre-tool-use.sh` — `set -e` com o idioma `[ -n "${VAR:-}" ] && echo …` como último comando do laço | Não é bug: sob `set -e`, um comando que falha à esquerda de `&&` não dispara a saída. Idioma correto |
