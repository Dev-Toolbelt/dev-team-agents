# Eixo C — Fluxos, Comandos e Automação — 2026-08-12

**Baseline:** `HEAD` = `07e0725`

Foco no delta: dispatchers de hooks, sub-scripts novos (`03c`, `03d`, `03e`, `02c`, `99b`), scripts
`_disabled-*`, e os 9 comandos novos.

## Hipóteses testadas e refutadas por evidência

Duas hipóteses de falha plausíveis foram levantadas e **descartadas** após verificação — registradas
aqui para o próximo pass não as reabrir:

1. **"Os scripts `_disabled-*` ainda auto-executam porque o dispatcher globa `*.sh`."**
   Refutada. **Ambos** os dispatchers têm allowlist por regex: `scripts/hooks/stop.sh:57` e
   `scripts/hooks/pre-tool-use.sh:20` usam `SUBSCRIPT_RE='^[0-9]{2}[a-z]?-[a-z0-9]…\.sh$'`. Arquivos
   com prefixo `_disabled-` não casam e são pulados. Isso, aliás, confirma o fingerprint executado
   `flow-stop-dispatcher-globs-all-sh-no-allowlist`.

2. **"Os sub-scripts novos `03c/03d/03e` re-forkam `git status`/`git log` (dupla do fingerprint
   `flow-stop-dispatcher-computes-no-changes-once…`)."**
   Refutada. `03c`/`03d` respeitam o fast-path `DEVTEAM_NO_CHANGES` (linha 8). `03e-adr-gap-check.sh`
   consome `DEVTEAM_TOUCHED_PATHS` via `scripts/hooks/lib/touched-paths.sh` (linhas 13-16), o
   conjunto tocado computado **uma vez** pelo `stop.sh`. Padrão correto, sem re-fork.

## Achado

**Nenhum achado original neste eixo.** Os dispatchers têm allowlist, os sub-scripts novos reusam o
conjunto tocado compartilhado, e os comandos novos (`status`, `version` sem spawn de agente;
`explain` no contexto principal por design) seguem as convenções declaradas no `CLAUDE.md`. Os
fluxos degradados conhecidos (`flow-cli-commit-validate-msg` silencioso, ausência de `commit-msg`
hook) seguem abertos e foram revalidados na Fase 1 — não são novos.
