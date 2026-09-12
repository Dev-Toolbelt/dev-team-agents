# Eixo C — Fluxos, comandos e automação (2026-09-04)

**Data:** 2026-09-04 · **Baseline:** `HEAD` = `a67cac9`

---

## MEDIUM-HIGH

### O prompt de auditoria é ao mesmo tempo um roteiro interativo e um lote não assistido, e as duas leituras se contradizem no Plan Gate

- **Fingerprint:** `flow-prompt-auditoria-interactive-plan-gate-unsatisfiable-in-unattended-run`
- **Alvo:** `docs/reports/_prompt-auditoria.md`
- **Evidência:**
  - `:7` — "Cole o bloco abaixo em **uma sessão nova** para executar um pass de auditoria." — pressupõe um operador humano colando o texto.
  - `:31-33`, regra **inviolável** 7 — "**Plan Gate.** Apresente o plano no formato de `templates/plan-template.md` … e **aguarde aprovação antes de escrever**, salvo se eu já tiver dito 'pode executar direto'." — a única dispensa prevista é uma fala do operador, na mesma sessão.
  - `:320-358`, § *Commit and push the report* — sequência completa de `git add` / `git commit` / `git push` sobre HTTPS com token, **sem nenhum ponto de confirmação**, e com tratamento de erro que descreve o comportamento correto quando ninguém está olhando: `:333-334` — "If `github.token` is missing from `credentials.local.json`, **stop and report** that the report was generated and committed but could not be pushed".
  - `:345-347` — `if git diff --cached --quiet; then echo "No report changes to commit — skipping commit/push."` — um fast-path silencioso, escrito para execução desassistida.
- **Problema:** o arquivo assume dois modos de operação incompatíveis. A regra 7 exige uma aprovação
  humana antes de qualquer escrita; a seção de encerramento executa a operação mais irreversível do
  pass — um push para `main` — sem pedir nada, e prevê explicitamente cenários de falha
  não-interativos. Em uma execução desassistida (agendada, batch, CI) a regra 7 não tem como ser
  satisfeita: o pass ou trava esperando um interlocutor que não existe, ou viola em silêncio uma
  regra que o próprio arquivo rotula como inviolável.
- **Por que importa:** a regra 7 é o único freio entre o auditor e a escrita de oito arquivos mais a
  reescrita do banco de fingerprints — o artefato do qual todo o sistema anti-duplicação depende. Uma
  regra inviolável que só é satisfazível em metade dos modos de execução do arquivo não é um freio;
  é uma formalidade que o executor aprende a ignorar. E o aprendizado não fica contido: o mesmo
  julgamento ("esta regra claramente não se aplica aqui") passa a estar disponível para as regras 1
  (evidência ou nada), 3 (sem duplicata) e 5 (nunca altere código).
- **Proposta:** dar ao arquivo um modo declarado. Acrescentar à regra 7 uma cláusula de execução
  desassistida — "quando não houver interlocutor na sessão, o Plan Gate é satisfeito publicando o
  plano como a primeira seção do `index.md` do pass, e a **regra 5** (nunca altere código) passa a
  ser a única salvaguarda; nenhuma escrita fora de `docs/reports/` é permitida nesse modo" — e
  espelhá-la em `:7`, que hoje só descreve o modo interativo.
- **Impacto positivo:** o pass fica executável sem ambiguidade nos dois modos, e o plano continua
  auditável no modo desassistido (fica no `index.md`, revisável depois) em vez de desaparecer. Fecha
  a porta para o executor tratar regras invioláveis como negociáveis por conta própria.
- **Impacto negativo / risco:** formalizar o modo desassistido **remove** o único ponto em que um
  humano poderia interromper um pass antes de ele reescrever `_index.md` e empurrar para `main`. Hoje
  essa proteção é acidental (o pass trava); depois da mudança ela deixa de existir por escrito. A
  compensação — restringir a escrita a `docs/reports/` — depende inteiramente do executor respeitar a
  regra 5, que é o mesmo tipo de regra que a mudança admite ser dispensável em algum modo. Também
  acrescenta ~6 linhas a um arquivo que já é o mais denso do diretório.
- **Esforço:** Baixo

---

## Nada mais neste eixo

Nenhum outro achado original.

O candidato mais forte deste pass — a ausência de qualquer mecanismo que verifique que o output de um
pass chegou ao remoto — já está registrado como
`gov-audit-pass-output-uncommitted-with-no-detection-mechanism` (**HIGH**, aberto, publicado em
2026-08-28). A recorrência é discutida na abertura do relatório da Fase 1 e descartada aqui pela
**Porta 5**.

Os demais candidatos de fluxo levantados durante a varredura caíram nas Portas 3 e 5 e estão listados
em "Descartados por duplicação", no `index.md`. Com `git diff --stat a67cac9..HEAD` vazio, nenhum
comando, hook ou script de install/update/render mudou desde os dois passes anteriores — o espaço de
busca deste eixo é literalmente o mesmo que eles já percorreram.
