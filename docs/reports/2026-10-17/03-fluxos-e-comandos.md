# Eixo C — Fluxos, comandos e automação — 2026-10-17

**Baseline:** `HEAD` = `bb0e883`. Prioridade: o maquinário novo do delta —
`scripts/hooks/lib/warn-once.sh`, `scripts/hooks/stop/03f-spec-lint.sh`,
`scripts/hooks/stop/03c-reuse-lint.sh` (reescrito), `scripts/spec-lint.sh`,
`commands/spec.md`, `commands/sprint.md`.

Os três sub-scripts de `Stop` que saem com código 2 passaram a compartilhar uma biblioteca
(`lib/warn-once.sh`) neste delta. Dos três, **um** aplica o protocolo inteiro. As duas diferenças
estão abaixo.

---

## MEDIUM-HIGH

### A assinatura de aviso do `03f-spec-lint.sh` não inclui a raiz do worktree, e o marcador é compartilhado entre worktrees

- **Fingerprint:** `auto-03f-spec-lint-warn-signature-omits-worktree-root-silences-sibling-worktrees`
- **Alvo:** `scripts/hooks/stop/03f-spec-lint.sh`
- **Evidência:**
  - `scripts/hooks/stop/03f-spec-lint.sh:58` —
    `SIGNATURE="$(printf '%s\n' "$OUTPUT" | git hash-object --stdin 2>/dev/null || true)"`
  - contra `scripts/hooks/stop/03c-reuse-lint.sh:52-56` — "# The worktree root is part of the
    signature: two worktrees share one marker, and each one's findings must not silence the
    other's." seguido de
    `SIGNATURE="$( { printf '%s\n' "$REPO_ROOT"; printf '%s\n' "$BLOCKED"; } | git hash-object --stdin …)"`
  - `scripts/hooks/lib/warn-once.sh:24` —
    `main_root="$(cd "$(git rev-parse --git-common-dir 2>/dev/null)/.." …)"` — o marcador vive no
    state dir do **checkout principal**, logo é um só para todos os worktrees
  - `scripts/lib/spec_lint.py:43` — `rel = safe(os.path.relpath(path, self.root), 200)`: a saída
    é relativa à raiz, então dois worktrees do mesmo repositório produzem **bytes idênticos**
- **Problema:** `03f` assina apenas a saída do lint. Como a saída é relativa e o marcador
  `.spec-lint-warned` é compartilhado por todos os worktrees do repositório, o primeiro worktree
  que fizer `Stop` com um dado conjunto de WARNs grava a assinatura e **silencia todos os
  outros** para o mesmo conjunto. O irmão `03c` resolve exatamente isso, três linhas acima da
  mesma chamada, com um comentário que explica por quê.
- **Por que importa no `HEAD` atual:** `commands/sprint.md` é o fluxo novo deste delta e seu modo
  recomendado é **um worktree por tarefa, tarefas de uma onda em paralelo** (`:49`). Todos os
  worktrees de uma onda carregam o mesmo `docs/specs/` commitado. Uma spec legada ou um cenário
  sem teste produz o mesmo WARN em todos; um worktree o vê, os outros não. O aviso que existe
  para impedir que uma onda inteira avance sobre uma spec quebrada chega a uma tarefa de N.
- **Proposta:** incluir `$REPO_ROOT` na assinatura de `03f:58`, na mesma forma de `03c:56` —
  `{ printf '%s\n' "$REPO_ROOT"; printf '%s\n' "$OUTPUT"; } | git hash-object --stdin`.
- **Impacto positivo:** o aviso volta a ser por worktree; numa onda de N tarefas paralelas o
  WARN chega a N sessões em vez de 1. Uma linha, idêntica à do irmão.
- **Impacto negativo / risco:** o mesmo WARN passa a aparecer N vezes por onda em vez de uma —
  é ruído multiplicado para quem roda muitas tarefas em paralelo sobre a mesma spec legada, e
  cada aparição é um `exit 2` que faz o provider continuar o turno. É o preço que `03c` já paga
  conscientemente; se for julgado alto demais, a alternativa é tornar o marcador por worktree em
  `warn-once.sh`, o que muda o comportamento de `03c` e `03e` junto.
- **Esforço:** Baixo

---

## MEDIUM

### Dois dos três consumidores de `warn-once.sh` nunca chamam `devteam_warn_once_reset`

- **Fingerprint:** `auto-warn-once-reset-never-called-by-03e-and-03f-cleared-warning-never-returns`
- **Alvo:** `scripts/hooks/stop/03f-spec-lint.sh`
- **Evidência:**
  - `scripts/hooks/lib/warn-once.sh:30-32` define o contrato: "`devteam_warn_once_reset
    <marker-basename>` — forget the last signature, so the same findings warn again if they come
    back after the condition was cleared."
  - `grep -rn warn_once_reset scripts/hooks/` → **uma única chamada**:
    `scripts/hooks/stop/03c-reuse-lint.sh:46` — `devteam_warn_once_reset .reuse-lint-warned`,
    sob o comentário "# Clean again: forget the last signature, so the same findings warn if they
    return."
  - `scripts/hooks/stop/03f-spec-lint.sh` sai limpo em `:13`, `:16`, `:24` e `:35`
    (`[ -n "$OUTPUT" ] || exit 0`) sem nunca resetar; `scripts/hooks/stop/03e-adr-gap-check.sh`
    sai em `:23`, `:33`, `:43` e `:103` idem.
- **Problema:** metade do protocolo da biblioteca está implementada em dois dos três
  consumidores. A assinatura é gravada quando o aviso dispara, mas nunca é esquecida quando a
  condição é resolvida.
- **Por que importa no `HEAD` atual:** o caso é concreto em `03f`. A pessoa resolve o WARN (marca
  a spec legada com `status:`, cobre o cenário) — a saída esvazia, `:35` sai antes de qualquer
  reset, e a assinatura antiga continua gravada. Semanas depois a **mesma** condição volta (um
  merge traz a spec legada de volta, um teste com o token `[spec:…]` é removido): a saída volta a
  ser byte a byte igual, `devteam_warn_once` encontra a assinatura e retorna 1, e o hook fica
  mudo — permanentemente, para aquele conjunto exato de findings. Em `03e` o efeito é mais raro
  porque a assinatura embute o diff dos manifests, mas a ausência da chamada é a mesma.
- **Proposta:** chamar `devteam_warn_once_reset .spec-lint-warned` no caminho de saída limpa de
  `03f` (antes do `exit 0` de `:35`, e no ramo `STATUS = 0` sem saída) e
  `devteam_warn_once_reset .adr-gap-warned` no `exit 0` final de `03e:103`.
- **Impacto positivo:** o contrato documentado da biblioteca passa a valer para os três
  consumidores; um aviso resolvido e depois reintroduzido volta a ser visto.
- **Impacto negativo / risco:** `03f` passa a escrever no state dir em sessões hoje silenciosas
  (todo `Stop` que toca a camada de spec e sai limpo faz um `rm -f`), e um WARN que oscila
  (aparece, some, volta) passa a avisar a cada volta em vez de uma vez só — mais ruído para quem
  convive com uma spec legada que entra e sai do diff.
- **Esforço:** Baixo

---

## LOW-MEDIUM

### O item 5 do § Step 6 de `/devteam:spec` está colado no item 4, e o próprio comando referencia "items 4 and 5"

- **Fingerprint:** `flow-spec-command-step6-item5-inlined-into-item4-breaking-its-own-cross-reference`
- **Alvo:** `commands/spec.md`
- **Evidência:** `commands/spec.md:53` — uma única linha:
  "4. Each scenario kept as intended → offer `/devteam:fix` with its ID and the observed behavior,
  in one `AskUserQuestion`. 5. Session summary and hand-off as `/devteam:fullstack` § Session
  close items 1 and 4."
  E `:55` — "When another command started this one, **skip items 4 and 5**: hand back to it with
  the spec path…".
- **Problema:** `5.` está no meio do parágrafo do item 4, não no início de uma linha. A lista de
  `## Step 6 — Close` tem três itens renderizados (1, 2, 3) e um quarto cujo texto termina com o
  que deveria ser o quinto. A instrução de `:55` aponta para um item que não existe como item.
- **Por que importa:** o fechamento de sessão (`:53`) é o passo que grava o session summary e faz
  o hand-off — o único do comando com efeito fora da conversa. Embutido no item 4, ele vira a
  cauda de uma frase sobre oferecer `/devteam:fix`, e some junto quando o item 4 é pulado por
  outro motivo. Os arquivos de comando são renderizados por provider
  (`scripts/lib/render_provider.py`), então a lista malformada é o que chega a Codex e opencode
  também.
- **Proposta:** quebrar a linha em dois itens — `4.` termina em "`AskUserQuestion`." e `5.` começa
  em "Session summary and hand-off…".
- **Impacto positivo:** `:55` volta a referenciar itens que existem; o passo de fechamento fica
  visível como passo.
- **Impacto negativo / risco:** nenhum funcional — é uma quebra de linha. O custo é que o
  comando ganha uma linha e `commands/spec.md` (64 linhas) fica um pouco mais perto do teto de
  ~200 de `helpers/size-limits.sh`, que hoje tem folga larga. Declarado porque a regra do
  relatório exige nomear o custo: aqui ele é desprezível, e a razão é que a mudança não altera
  comportamento nenhum, só o agrupamento visual de duas frases que já estão no arquivo.
- **Esforço:** Baixo

---

## Candidato levantado e descartado

`commands/mobile.md:12` repete o roteamento de autor de teste que `:28-29` já define (React Native
/ Expo → `frontend-test-specialist`; Flutter/nativo → `mobile-developer`). Descartado pela porta 3
contra `flow-mobile-command-spawn-line-enumerates-stacks-dropped-from-agent-description` — mesmo
arquivo e mesma remediação ("não reenumerar a stack no comando"). Registrado em
[`index.md`](index.md) § Descartados por duplicação.

Também avaliado e **não** promovido: o guard `[ -d "$REPO_ROOT/docs/specs" ] || exit 0` de
`scripts/spec-lint.sh:12` e `03f-spec-lint.sh:16`, que estreita o gatilho documentado
("docs/specs/ **ou** docs/backlog/sprints/"). Não é defeito: sem `docs/specs/` nenhum arquivo de
spec existe, e o caso que o lint perderia — uma tarefa de sprint apontando para uma spec
inexistente — já é checado explicitamente pelo pré-flight em `commands/sprint.md:31`
("`Spec` names a file that exists"). Registrado aqui para que o próximo pass não refaça a
análise.
