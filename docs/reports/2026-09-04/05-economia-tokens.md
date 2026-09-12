# Eixo E — Economia de tokens (2026-09-04)

**Data:** 2026-09-04 · **Baseline:** `HEAD` = `a67cac9`

---

## LOW-MEDIUM

### A rotação de 90 dias move o texto do banco mas deixa os diretórios de relatório que ele referencia crescendo sem teto

- **Fingerprint:** `token-archive-index-rotates-index-sections-only-report-directories-never-pruned`
- **Alvo:** `helpers/archive-index.sh`
- **Evidência:**
  - `helpers/archive-index.sh:3` — "…rotate fingerprint sections older than 90 days out of `docs/reports/_index.md` into quarterly archives (`_index-archive-YYYY-Q.md`)". Todo o script opera sobre uma única variável de arquivo: `:34` `INDEX_FILE="$REPORTS_DIR/_index.md"`, e as escritas terminam em `:162` `mv "$WORK/keep.trimmed" "$INDEX_FILE"`. Não há uma linha que toque um diretório de pass.
  - `scripts/hooks/stop/99b-archive-index.sh:2-3` repete o escopo — "rotate fingerprint sections … into quarterly archives" — e é o único gatilho registrado.
  - Execução no `HEAD`: `bash helpers/archive-index.sh --dry-run` → `✓ No entries older than 90 days (cutoff 2026-06-06) in docs/reports/_index.md.`
  - Tamanho real do que **não** rotaciona:

    ```
    $ du -sh docs/reports/2026-*
    124K  2026-07-30      168K  2026-08-14
     88K  2026-07-31      260K  2026-08-21
     64K  2026-08-12      144K  2026-08-28
    $ du -sh docs/reports
    1.0M  docs/reports
    ```

    Seis passes em 36 dias, média de **141 KB por pass**, ~1,0 MB acumulado. `_index.md` sozinho tem
    548 linhas / **109.001 bytes**.
- **Problema:** a rotação foi desenhada para conter o crescimento do banco, e contém — mas só a
  camada de texto. Cada linha rotacionada carrega um link `[report](<YYYY-MM-DD>/<arquivo>.md)`, e o
  diretório do outro lado desse link permanece em `docs/reports/` indefinidamente. O nome do script e
  o comentário do hook descrevem "rotação", palavra que sugere que o material antigo sai de cena;
  o que sai é a linha de índice.
- **Por que importa:** dois custos, ambos mensuráveis. (1) **Repositório:** ~141 KB por pass, em
  cadência semanal, projeta ~7,3 MB/ano em `docs/reports/`, num repo cujo `agents/` + `skills/` +
  `commands/` somados são menores que isso — e o diretório é clonado por todo contribuidor sem
  jamais ser lido por um agente. (2) **Contexto:** a Fase 0 de todo pass executa `ls docs/reports/`,
  e a lista de diretórios cresce monotonicamente; o auditor passa a escolher baselines e relatórios-
  fonte dentro de um espaço que só aumenta, sem sinal de qual parte já está arquivada. Depois da
  primeira rotação real (a primeira seção completa 90 dias em 2026-10-28) a assimetria fica visível:
  `_index-archive-2026-Q3.md` referenciará diretórios que continuam misturados aos vivos, sem
  nenhuma marca que os distinga.
- **Proposta:** estender o escopo da rotação, ou declarar explicitamente que ele não se estende.
  Caminho mínimo: quando `archive-index.sh` move uma seção para o arquivo trimestral, mover também os
  diretórios `docs/reports/<YYYY-MM-DD>/` daquela janela para `docs/reports/archive/<YYYY-Q>/` e
  reescrever os links da seção arquivada com o novo prefixo — uma operação, os links continuam
  resolvendo. Caminho alternativo, custo zero: acrescentar duas linhas ao cabeçalho do script
  dizendo que os diretórios são permanentes por design e por quê.
- **Impacto positivo:** `docs/reports/` na raiz passa a listar apenas passes vivos (hoje 6, com
  rotação ~13 no pior caso antes de arquivar), e a Fase 0 lê uma lista de tamanho estável em vez de
  monotonicamente crescente. O crescimento do repositório deixa de ser irrestrito.
- **Impacto negativo / risco:** mover diretórios **quebra todo link externo** para
  `docs/reports/<data>/<arquivo>.md` — issues, PRs e o histórico do próprio `_index.md`, cujas
  entradas legadas não seriam reescritas. Um `git mv` em massa também polui o `git log --follow` de
  cada arquivo movido. E acrescenta a `archive-index.sh` — hoje um script que edita **um** arquivo,
  idempotente e trivialmente reversível — a responsabilidade de mover diretórios, o que o torna
  destrutivo o bastante para merecer seu próprio `--dry-run` mais cuidadoso e um teste. O caminho
  alternativo (documentar) não tem nenhum desses riscos e também não tem nenhum dos ganhos.
- **Esforço:** Médio (rotação de diretórios) · Baixo (só documentar o escopo)

---

## Verificação de fôlego: o custo do próprio Protocolo Anti-Duplicação

Durante este eixo foi verificado — e reaberto na Fase 1 — o fingerprint
`token-dedup-step-reads-full-676-line-prose-index-md-every-run-…`. O detalhamento está em
`00-guardiao-verificacao.md`; o número relevante aqui: as Portas 1 e 2 do protocolo varrem
`docs/reports/_index.md` em prosa, **548 linhas / 109 KB**, uma vez por candidato. Nenhuma lista
legível por máquina foi extraída, apesar da marca ✅. O campo `alvo:` introduzido por `7736e20`
barateia a Porta 2 sem eliminar a varredura.

---

## Candidatos descartados neste eixo

Todos por **Porta 5** (já registrados e abertos), com a árvore idêntica à dos dois passes anteriores:

`skills/shared/interaction-patterns/SKILL.md` (209 linhas × 34 consumidores) ·
`skills/shared/token-efficiency/SKILL.md` (160 × 18, a ironia meta já registrada) ·
`skills/architecture/orchestration/SKILL.md` (391 linhas sem `references/`) ·
`skills/shared/migration-v1-to-v2/SKILL.md` (438 linhas) · `CLAUDE.md` em 602 linhas, monolítico ·
os dois laços de `ScheduleWakeup` concorrentes (`orchestration:223` a 1200–1800 s contra
`work-feedback` a 300 s) · a cópia verbatim de 14 linhas do nudge de learn em `pr.md:140-152` ·
`scripts/install.sh` em 1.240 linhas sem decomposição.
