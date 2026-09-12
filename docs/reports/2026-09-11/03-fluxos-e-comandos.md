# Eixo C — Fluxos, comandos e automação (2026-09-11)

**Data:** 2026-09-11 · **Baseline:** `HEAD` = `9530551`

**Achados originais: 2** (1 MEDIUM-HIGH, 1 MEDIUM).

---

## MEDIUM-HIGH

### Nenhum gate valida a § File Structure do `CLAUDE.md` contra a árvore real — quatro passes já pegaram e descartaram a mesma classe

- **Fingerprint:** `auto-no-gate-validates-claude-md-file-structure-tree-against-real-tree-four-recurrences-each-discarded-as-duplicate`
- **Alvo:** `helpers/`
- **Evidência:**
  - Nenhum validador existe:
    `grep -rli "file structure" helpers/*.sh .github/scripts/ci/*.sh scripts/hooks/stop/*.sh`
    devolve **zero** arquivos. `helpers/agent-lint.sh` valida frontmatter, tiers, banners, roster e
    quiz-first; `helpers/size-limits.sh` conta linhas; `orphan-skill-scan.sh` e
    `orphan-template-scan.sh` resolvem referências de skill e template. Nenhum compara a árvore
    ASCII de `CLAUDE.md:296-358` com `find`.
  - Quatro instâncias da mesma divergência, cada uma encontrada por um pass diferente e cada uma
    **individualmente descartada** como duplicata pela Porta 3:

    | Pass | Instância | Onde ficou registrado |
    |---|---|---|
    | 2026-08-14 | `docs/prompts/` ausente da árvore | `_index.md:341` (Descartados) |
    | 2026-08-21 | `CLAUDE.md:300` lista 3 de 5 templates | `_index.md:481` (Descartados, Porta 3) |
    | 2026-08-28 | `docs/harness.md` ausente | `_index.md:609` (Descartados) |
    | **2026-09-11** | `CLAUDE.md:344-347` enumera `scripts/hooks/lib/` como três arquivos — `session-summary-detect.sh`, `touched-paths.sh`, `update-check.sh` — fechando a lista com `└──`. A árvore tem **quatro**: `agent-usage.sh` (6.488 bytes, `e4c96b4`/2026-08-11) está ausente. | este relatório |
  - `agent-usage.sh` não é um arquivo marginal: `CLAUDE-md/hooks.md:76` o documenta como "Sourced by
    `stop/05-telemetry.sh` to queue the `agent_completed` telemetry event", e
    `docs/reports/metrics-last-20-days.md` § 0 registra `agent_completed` como **36,9% de todos os
    eventos** (2.051 de 5.563). Os dois mapas do repositório discordam sobre a existência do
    arquivo que produz o segundo maior tipo de evento de telemetria.
  - Divergência adicional no mesmo bloco: `CLAUDE.md:341-343` mostra `stop/` com um único
    subdiretório (`tips/`); `ls scripts/hooks/stop/` devolve 11 sub-scripts ativos mais dois
    `_disabled-*`.
- **Problema:** o `CLAUDE.md` tem gates para tudo que o repositório considera crítico — frontmatter,
  tier, banner, tamanho, roster, referências de skill, referências de template, unicidade de
  fingerprint — e **nenhum** para o mapa que descreve onde as coisas estão. A consequência não é a
  ausência de uma linha: é que a divergência é **estruturalmente invisível para o próprio protocolo
  de auditoria**. Cada instância nova casa 3 de 3 atributos com a família
  `ref-claude-md-file-structure-*` (todos ✅ Executed), cai pela Porta 3, e some na seção
  "Descartados". O banco registra corretamente que não é achado novo, e ao fazer isso garante que a
  classe nunca é atacada.
- **Por que importa:** é a definição literal de MEDIUM-HIGH — "cria risco real de drift sem gate que
  o pegue". Quatro recorrências em seis semanas, num repositório cujo último commit de código tem 21
  dias, é uma taxa de ~1 divergência a cada 10 dias de atividade. O mapa é a primeira coisa que um
  agente ou contribuidor lê para localizar um arquivo; um mapa que erra em 25% de um diretório manda
  o leitor procurar em `CLAUDE-md/hooks.md` — que está certo — ou desistir.
- **Proposta:** `helpers/file-structure-lint.sh` que extraia os caminhos do bloco ASCII entre
  `` ```\n dev-team-agents/ `` e o fechamento, e falhe quando (a) um caminho listado não existir na
  árvore, ou (b) um arquivo existir num diretório cujo bloco é enumerado exaustivamente (marcado por
  um comentário `<!-- exhaustive -->` na linha do diretório). Despachar como
  `scripts/hooks/stop/03f-file-structure-lint.sh` e adicionar a `.github/scripts/ci/01-lint.sh`.
- **Impacto positivo:** fecha a classe inteira, não a quarta instância dela. Elimina ~1 candidato
  descartado por pass do trabalho de triagem, e recupera os três já perdidos.
- **Impacto negativo / risco:** o mais caro deste relatório. Um parser de ASCII-art é frágil:
  `├──`/`└──`/`│` com profundidade variável, linhas de continuação (`CLAUDE.md:343` é a continuação
  da `:342`), e comentários `←` que não são caminhos. Marcar quais blocos são exaustivos exige
  decidir isso arquivo a arquivo — e um bloco marcado exaustivo por engano transforma cada arquivo
  novo numa falha de CI, que é exatamente o atrito que o `auto-size-limits-claude-md-warning-…`
  (HIGH, aberto) já causa hoje. Alternativa mais barata e menos completa: validar só a **existência**
  dos caminhos listados (direção (a)), que pega metade dos casos com 20% do código e nenhum falso
  positivo — mas **não** teria pego nenhuma das quatro instâncias acima, que são todas omissões.
  Assumir esse custo é a decisão real aqui.
- **Esforço:** Médio
- **Relação declarada (não é `Refina:`):** a família `ref-claude-md-file-structure-*` (3 entradas,
  todas ✅ Executed) tem como remediação "adicionar a entrada faltante". Porta 3 contra ela: alvo
  difere (`helpers/` vs. `CLAUDE.md`), causa raiz difere (ausência de verificador mecânico vs.
  ausência de uma linha), remediação difere (criar gate vs. editar o mapa). **1 de 3.**

---

## MEDIUM

### `check-fingerprint-uniqueness.sh` admite linhas da seção "Descartados por duplicação" como fingerprints

- **Fingerprint:** `auto-check-fingerprint-uniqueness-grep-admits-discarded-candidate-lines-as-slugs-inflating-count-and-silent-sed-fallthrough`
- **Alvo:** `helpers/check-fingerprint-uniqueness.sh`
- **Evidência:**
  - `helpers/check-fingerprint-uniqueness.sh:35-37`:
    ```bash
    grep -E "^- \`[a-z][a-z0-9-]+" "$bank_file" 2>/dev/null \
        | sed "s/^- \`\([a-z][a-z0-9-]*\)\`.*/\1/" \
        | sed "s|\$|\t$rel_bank|"
    ```
    O `grep` não tem âncora de seção: casa **qualquer** linha do arquivo que comece com
    `` - ` `` seguido de minúscula. As seções `### Descartados por duplicação` usam exatamente esse
    formato para listar candidatos **rejeitados**.
  - Duas linhas de descarte casam hoje — `docs/reports/_index.md:311`
    (`` - `frontend-developer.md:96` nomeia TanStack/SWR/React/Vue — Porta 3 (semântica)… ``) e
    `:343` (`` - `install.sh` com 1086 linhas · sem registro de `commit-msg` hook — Porta 5… ``).
  - O `sed` de extração **não casa** nessas linhas (`frontend-developer.md:96` contém `.` e `:`,
    fora da classe `[a-z0-9-]`), e `sed` sem match passa a linha adiante **inalterada**. O "slug"
    emitido é a frase inteira.
  - Resultado medido: `bash helpers/check-fingerprint-uniqueness.sh` imprime
    `✓ All 237 fingerprint slugs are unique across 1 bank file(s)`. A contagem real de fingerprints
    vivos é **235**.
  - O mesmo defeito está no comando da Fase 0 de `docs/reports/_prompt-auditoria.md:44`
    (`grep -cE '^- \`[a-z]' docs/reports/_index.md`), de onde todo pass tira o número que registra
    na tabela **Estatísticas**.
- **Problema:** duas falhas encadeadas. (1) O escopo do `grep` inclui uma seção cujo propósito é
  listar o que **não** entrou no banco. (2) O `sed` de extração falha em silêncio nessas linhas em
  vez de rejeitá-las, promovendo uma frase de prosa a chave de comparação de unicidade.
- **Por que importa:** o efeito de hoje é cosmético — a contagem publicada erra por 2 (0,85%) e
  cresce a cada pass que escreve uma seção de descarte. O efeito latente não é: a chave de
  comparação vira o **texto completo** da linha de descarte, então dois passes que rejeitem o mesmo
  candidato com a mesma redação produzem um "slug duplicado" e o gate sai **1** — bloqueando o CI
  (`01-lint.sh`) e o `Stop` (`03b-fingerprint-uniqueness.sh`) por uma coincidência de prosa numa
  seção de itens descartados. É improvável, mas o modo de falha é um gate bloqueante disparando
  sobre dados que ele nunca deveria ter lido, com uma mensagem de erro que nomearia uma frase
  inteira como "slug".
- **Proposta:** restringir a extração à seção viva e falhar alto em vez de silenciosamente — ler só
  a partir de `## Registered Fingerprints`, parar em cada `### Descartados por duplicação` até o
  próximo `##`, e trocar o `sed` por `grep -oP '^- \`\K[a-z][a-z0-9-]*(?=\`)'`, que **descarta** o
  que não casa em vez de repassar.
- **Impacto positivo:** a contagem publicada passa a ser verdadeira; o modo de falha latente some;
  a mesma correção aplicada a `_prompt-auditoria.md:44` alinha a tabela Estatísticas ao gate.
- **Impacto negativo / risco:** um parser com estado (dentro/fora de seção) é mais frágil que um
  `grep` de uma linha, e passa a depender do título exato `### Descartados por duplicação` — se um
  pass futuro escrever "Descartes por duplicação", o filtro volta a vazar sem avisar. Trocar para
  `grep -oP` também introduz dependência de PCRE, que nem todo `grep` de sistema tem (macOS BSD
  `grep` não suporta `-P`) — o script roda no `Stop` de máquinas de desenvolvimento, então ou se usa
  `sed -n` com ramo explícito de rejeição, ou se aceita a dependência. O ganho é pequeno; a correção
  precisa ser proporcionalmente barata.
- **Esforço:** Baixo

---

## Candidatos verificados e descartados neste eixo

| Candidato | Porta | Motivo |
|---|---|---|
| O output de três passes (61 fingerprints) nunca chegou ao remoto | 5 | `gov-audit-pass-output-uncommitted-with-no-detection-mechanism` (HIGH, aberto) |
| O bloco de commit de `_prompt-auditoria.md:336-358` diz "the two report files" (são 8) e usa a mensagem de commit do prompt de métricas | 5 | `flow-prompt-auditoria-commit-step-contradicts-branch-rule` (MEDIUM, aberto) — confirmado por `9530551`, que carrega essa mensagem literal e staged só os dois arquivos de métricas |
| Regra inviolável 7 (Plan Gate) insatisfazível em execução desassistida | 5 | `flow-prompt-auditoria-interactive-plan-gate-unsatisfiable-in-unattended-run` (MEDIUM-HIGH, aberto) |
| `99b-archive-index.sh` é o único sub-script do `Stop` sem `DEVTEAM_NO_CHANGES`/`DEVTEAM_TOUCHED_PATHS` | — | **não é achado**: o próprio cabeçalho (`:11-12`) justifica — "The rotation is time-based, not change-based, so the gate is a once-per-day stamp rather than a touched-path match", e o stamp existe em `:26-30` |
| `helpers/size-limits.sh` não impõe teto a `CLAUDE-md/*.md`, que é o destino de extração do `CLAUDE.md` (343 linhas somadas, sem cap) | 3 | alvo + causa raiz coincidem com `token-claude-md-426-lines-still-monolithic-…` (MEDIUM-HIGH, reaberto 3×), cuja remediação é justamente extrair para `CLAUDE-md/` — **2 de 3** |
| `commands/commit.md:144-147` pula a validação de mensagem em silêncio | 5 | já registrado e 🔴 reaberto (Fase 1, item 5) |
| `docs/prompts/` tem um prompt (`posthog-metrics-report.md`) e `docs/reports/` tem outro (`_prompt-auditoria.md`) — dois lares para a mesma classe de artefato | 3 | alvo + remediação coincidem com a família `ref-claude-md-file-structure-*` / o caso `docs/prompts/` já descartado em 2026-08-14 — **2 de 3** |
