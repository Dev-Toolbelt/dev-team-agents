# Eixo B — Referências e consistência — 2026-10-17

**Baseline:** `HEAD` = `bb0e883`. Prioridade de varredura: os 157 arquivos do delta desde
`349f18c`, com foco no material novo (`commands/spec.md`, `commands/sprint.md`, `AGENTS.md`,
`scripts/hooks/stop/03f-spec-lint.sh`, `scripts/hooks/lib/warn-once.sh`, `scripts/spec-lint.sh`,
`scripts/lib/spec_lint.py`, ADRs 0035–0037).

## Scans automáticos

```
helpers/orphan-skill-scan.sh      → clean ✓
helpers/orphan-template-scan.sh   → clean ✓
helpers/agent-lint.sh             → clean ✓
helpers/size-limits.sh            → clean ✓ (WARN: CLAUDE.md 678 linhas, teto de aviso 600)
```

Os quatro passam. O `orphan-skill-scan` passar segue valendo pouco: o fingerprint aberto
`ref-orphan-skill-scan-blind-to-directory-form-skill-refs` documenta que ele só casa
`skills/…/SKILL.md` literal, e os 7 caminhos mortos de `commands/relayout.md:35` seguem invisíveis
para ele.

## Registro dos dois comandos novos — consistente

`/devteam:spec` e `/devteam:sprint` entraram completos: `scripts/lib/commands.json` tem 37 linhas
contra 37 arquivos em `commands/` (nenhum órfão nos dois sentidos), `CLAUDE-md/commands.md` tem as
37 linhas da tabela, e `README.md:219-220` / `README.pt-BR.md:219-220` descrevem os dois nos dois
idiomas. Nada a reportar aqui.

---

## MEDIUM-HIGH

### O checklist de aposentadoria de preferência reenumera os espelhos e erra nos dois sentidos

- **Fingerprint:** `docs-sync-preferences-retire-checklist-restates-mirror-list-omits-docs-pair-and-invents-readme-row`
- **Alvo:** `CLAUDE-md/preferences.md`
- **Evidência:** `CLAUDE-md/preferences.md:42` — "**Remove from all mirrors** listed in
  CLAUDE.md § User Preferences (the install.sh heredoc, this file,
  `skills/shared/user-preferences/SKILL.md`, `README.md` worktree table if listed)".
  A lista canônica é `CLAUDE.md:390-395`, uma tabela de **quatro** linhas:
  `scripts/install.sh` heredoc · `CLAUDE-md/preferences.md` · `skills/shared/user-preferences/SKILL.md` ·
  `docs/user-preferences.md` / `docs/user-preferences.pt-BR.md`.
  E `grep -n 'worktree_active\|worktree_commit_action' README.md README.pt-BR.md` → **vazio**.
- **Problema:** a frase manda seguir a lista canônica e em seguida a reescreve errada nas duas
  direções: **omite** o par `docs/user-preferences{,.pt-BR}.md`, que é espelho de verdade, e
  **inventa** uma "`README.md` worktree table", que não existe em nenhum dos dois READMEs.
- **Por que importa:** quem seguir o checklist ao pé da letra aposenta uma chave e a deixa viva
  nos dois documentos de usuário, em inglês e em português — exatamente o drift que a tabela de
  espelhos de `CLAUDE.md:388` existe para impedir ("the set had already drifted five ways before
  it was reconciled"). Não há gate: nenhum helper compara a lista do checklist com a tabela.
  O par de docs foi tocado neste mesmo delta, então o caminho está quente. E o fingerprint
  `docs-sync-preferences-mirror-registry-names-readmes-omits-docs-pair` já corrigiu esta mesma
  lacuna em `CLAUDE.md`; a cópia errada sobreviveu em outro arquivo.
- **Proposta:** trocar a parentética por "listed in CLAUDE.md § User Preferences" e nada mais —
  o passo já aponta para a lista canônica; reenumerá-la é o defeito. Se a enumeração inline for
  considerada necessária para quem lê offline, corrigi-la para as quatro linhas reais e anotar
  na tabela de `CLAUDE.md:390` que ela tem um espelho em `CLAUDE-md/preferences.md:42`.
- **Impacto positivo:** elimina o único lugar do repositório que descreve a lista de espelhos de
  preferências de forma falsa, e remove um espelho da própria lista de espelhos — uma linha a
  menos para manter em sincronia a cada chave nova.
- **Impacto negativo / risco:** quem lê só `CLAUDE-md/preferences.md` perde a enumeração inline e
  precisa abrir `CLAUDE.md` — um salto a mais num runbook de seis passos. Se `CLAUDE.md § User
  Preferences` for renomeada, o ponteiro quebra silenciosamente, enquanto a cópia errada ao menos
  dizia alguma coisa.
- **Esforço:** Baixo

---

## MEDIUM

### A linha do `warn-once.sh` em `hooks.md` contradiz a linha 41 do próprio arquivo sobre quem o usa

- **Fingerprint:** `docs-sync-hooks-md-warn-once-library-row-omits-03f-spec-lint-contradicting-line-41`
- **Alvo:** `CLAUDE-md/hooks.md`
- **Evidência:** `CLAUDE-md/hooks.md:121` — "`scripts/hooks/lib/warn-once.sh` | Shared library |
  … Sourced by `stop/03c-reuse-lint.sh` (`.reuse-lint-warned`) and `stop/03e-adr-gap-check.sh`
  (`.adr-gap-warned`)". Contra `:41` do mesmo arquivo — "`03e-adr-gap-check.sh`,
  `03c-reuse-lint.sh` and the warning path of `03f-spec-lint.sh` remember the signature they
  warned about through `lib/warn-once.sh` (`<state-dir>/.adr-gap-warned`,
  `<state-dir>/.reuse-lint-warned`, `<state-dir>/.spec-lint-warned` …)". E contra o código:
  `grep -ln warn-once scripts/hooks/stop/*.sh` → `03c-reuse-lint.sh`, `03e-adr-gap-check.sh`,
  `03f-spec-lint.sh` (`scripts/hooks/stop/03f-spec-lint.sh:60`).
- **Problema:** o mesmo commit que criou a biblioteca documentou os três consumidores em `:41` e
  só dois na linha de biblioteca em `:121`. O arquivo se contradiz sobre um fato mecânico.
- **Por que importa:** a tabela de bibliotecas é o índice de fan-in — é por ela que se decide se
  mexer em `warn-once.sh` afeta um hook, dois ou três. Ela diz dois. Uma mudança no contrato de
  `devteam_warn_once` validada contra `03c` e `03e` passaria sem que ninguém olhasse `03f`, que é
  justamente o consumidor com o uso mais incomum (ver o Eixo D: é o único que assina só a saída,
  sem a raiz do worktree). Nenhum helper verifica a tabela.
- **Proposta:** acrescentar `stop/03f-spec-lint.sh` (`.spec-lint-warned`) à linha `:121`, na mesma
  forma das outras duas.
- **Impacto positivo:** o índice de fan-in volta a bater com `grep -ln warn-once`, e o leitor de
  `:121` para de receber o oposto do que `:41` diz.
- **Impacto negativo / risco:** é a terceira enumeração manual da mesma relação no repositório
  (`:41`, `:121`, mais os cabeçalhos dos próprios sub-scripts); corrigir uma delas sem gate deixa
  a próxima a derivar do mesmo jeito. O custo real é admitir que a tabela precisa de um lint, que
  este achado não propõe.
- **Esforço:** Baixo

---

## Candidatos levantados e descartados

Ver a seção "Descartados por duplicação" do [`index.md`](index.md) — três candidatos deste eixo
caíram lá, dois por porta 3 (semântica) e um por porta 5 (estado).

Nenhum achado original adicional neste eixo.
