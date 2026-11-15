# Eixo E — Economia de Tokens · 2026-11-14

`HEAD` = `c6398e5` · baseline = `5133c8c` · delta de 16 commits / 86 arquivos.

## Método

Levantei **8 candidatos** sobre o delta, priorizando a skill vendorizada nova
`skills/third-party/security-audit/` (15 arquivos, 259.803 B, território com **zero** ocorrências
em `docs/reports/_index.md` e `docs/reports/_index-archive-2026-Q3.md` na Porta 2), as nove skills
de `skills/shared/*` tocadas, as duas referências de `setup-health-check/` e `helpers/third-party-skills.py`.
**Seis morreram** — três na Porta 3 ou 5 contra itens já registrados (`token-151-skills-flat-symlinked-…`,
`token-interaction-patterns-209-lines-…`, `token-install-sh-second-unconditional-claude-md-injection-…`),
três na própria coleta de evidência, por não haver duplicação nem contexto morto a medir.
Restaram **2 achados**, ambos na cadeia nova `commands/security.md` → `skills/security/third-party-security-skills/SKILL.md`
→ `skills/third-party/security-audit/`. Não reapresento nenhuma das medidas já colhidas nos itens
abertos do banco (`checks-list.md`, `fix-patterns.md`, `interaction-patterns`, `spec-gate`, `plan-mode`,
`orchestration`, índice de skills symlinkadas, `CLAUDE.md`, `install.sh`, `CHANGELOG.md`,
`session-start.sh`, índice da wiki).

## MEDIUM

### A linha de Guidance Mode do roteador carrega 13,8 KB de material exclusivo de full audit e um arquivo 100% de fases

- **Fingerprint:** `token-security-audit-guidance-row-loads-13-8kb-full-audit-only-plus-phase-file`
- **Fundido cross-eixo:** absorveu o candidato independente do Eixo D (`skill-third-party-security-guidance-row-loads-full-audit-only-reporting-file`), que coincidia em **3 de 3** atributos da Porta 3 — mesmo alvo (`:16`), mesma causa raiz e mesma remediação. A evidência de correção que ele trazia: os **8** cabeçalhos de `VALIDATION-AND-REPORTING.md` (186 linhas) são `:3` Phase 3, `:9` candidate-verifier prompt, `:95` Phase 4, `:120` Phase 5, `:151` Phase 6, `:155` `REPORT.md`, `:169` `FINDINGS-DETAIL.md`, `:180` `NEEDS-VALIDATION.md` — nenhum é regra de evidência; o modo veta todos (`:23` "launch no agent", `:24` "Create no output directory, write no audit artifact and run no target code"); e as regras de evidência que a linha 16 diz querer estão em `skills/third-party/security-audit/SKILL.md:136-166` § Core principles, já carregado e parafraseado na ponte em `:27`. Logo o ponteiro não só custa tokens: **nomeia o arquivo errado**.
- **Alvo:** `skills/security/third-party-security-skills/SKILL.md`
- **Evidência:**
  - `skills/security/third-party-security-skills/SKILL.md:16` — "`security-audit`: `SKILL.md` plus only the companion files the task touches (`ATTACK-CLASSES.md`, the matching domain file, `VALIDATION-AND-REPORTING.md` for evidence rules)"
  - `skills/security/third-party-security-skills/SKILL.md:24` — "Create no output directory, write no audit artifact and run no target code."
  - `skills/third-party/security-audit/SKILL.md:46` — "In full audit mode, resolve these values before reconnaissance:"
  - `skills/third-party/security-audit/SKILL.md:90` — "The coverage, prior-run, profile, and budget requirements in this section apply only in full audit mode."
  - `skills/third-party/security-audit/SKILL.md:170` — "In full audit mode, follow all six phases in order:"
  - `skills/third-party/security-audit/VALIDATION-AND-REPORTING.md:3` — "### Phase 3: Independently validate every candidate" (as **nove** headings do arquivo são `Phase 3` a `Phase 6`, `#### Candidate-verifier prompt`, `#### REPORT.md`, `#### FINDINGS-DETAIL.md`, `#### NEEDS-VALIDATION.md`)
- **Problema:** a linha de Guidance Mode da tabela § Routing escopa os **companions** ("only the companion
  files the task touches") mas manda carregar `SKILL.md` inteiro e nomeia `VALIDATION-AND-REPORTING.md`.
  Medido no HEAD: `SKILL.md` tem 22.026 B / 192 linhas, das quais `:44-134` (12.336 B / 91 linhas, §
  Full audit setup + § Write isolation + § Full audit planning) e `:168-179` (1.496 B / 12 linhas, § Full
  audit workflow) são **13.832 B / 103 linhas = 62,8%** declaradas pelo próprio upstream como válidas só
  em full audit — e o § Guidance Mode do roteador (`:24`) proíbe exatamente o que essas linhas descrevem
  (output directory, artefatos, código do alvo). `VALIDATION-AND-REPORTING.md` são 17.843 B / 186 linhas
  de maquinário das Fases 3–6; o único parágrafo útil fora de full audit é `:87` (~470 B, as definições de
  `confirmed`/`needs_validation`/`rejected`), e a barra de evidência que a linha diz buscar ali já está em
  `SKILL.md:136-167` § Core principles (3.108 B), que o mesmo spawn já leu.
- **Por que importa:** por spawn em Guidance Mode o agente lê 13.832 B + 17.373 B = **31.205 B
  (~7.800 tokens)** de contexto que as regras do próprio roteador o proíbem de usar, contra 8.192 B de
  `SKILL.md` que são de fato aplicáveis (`:1-43`, `:136-167`, `:181-192`). Seis comandos spawnam
  `security-specialist` — `security.md:16`, `audit.md:105`, `plan.md:41`, `refactor.md:91`, `review.md:42`
  e `sprint.md:80` (este **por tarefa, por onda**) — e a linha condicional `agents/security-specialist.md:52`
  decide se a cadeia carrega, de modo que o custo incide uma vez por spawn que seja pesquisa de
  vulnerabilidade ou triagem de achado. O desenho mostra que o autor sabia escopar: ele escopou os
  companions na mesma célula.
- **Proposta:** na célula `Load` da linha Guidance de `:16`, nomear as seções de `SKILL.md` do mesmo jeito
  que a célula já nomeia companions (§ Operating modes, § Platform terminology, § Universal execution
  safety, § Core principles, § Anti-patterns) e remover `VALIDATION-AND-REPORTING.md` da linha, já que
  § Guidance Mode `:25` restata o mapeamento de severidade e o tratamento de `needs_validation` que o
  `:87` daquele arquivo fornece.
- **Impacto positivo:** 39.869 B → 8.664 B de leitura por spawn em Guidance Mode (−78%, ~7.800 tokens),
  numa cadeia alcançada por 6 comandos, um deles (`/devteam:sprint` Step 5) por tarefa de cada onda.
- **Impacto negativo / risco:** carga por seção acopla o roteador aos **títulos** do upstream: um bump do
  pin em `skills/third-party/sources.json` que renomeie uma seção invalida a célula sem que nada falhe —
  `helpers/third-party-skills.py` valida hash de conteúdo, não nomes de seção, então o drift aparece como
  seção não encontrada em tempo de execução. Remover `VALIDATION-AND-REPORTING.md` da linha também aposta
  que `§ Guidance Mode :25` continue cobrindo os três verdictos; se essa restatement for enxugada depois,
  a barra de verdicto fica sem fonte.
- **Esforço:** Baixo

### O procedimento de promotion existe em três cópias idênticas e é emitido em cada prompt de hunter e verifier, enquanto o roteador declara que nada é promovido

- **Fingerprint:** `token-promotion-procedure-tripled-while-wrapper-declares-nothing-is-promoted`
- **Alvo:** `skills/third-party/security-audit/HUNTING.md`
- **Evidência:**
  - `skills/third-party/security-audit/SKILL.md:82` — "[HUNTING.md](HUNTING.md) and [VALIDATION-AND-REPORTING.md](VALIDATION-AND-REPORTING.md) carry this procedure as one identical fenced block for hunter and verifier prompts; it states the same rules in the same order as this list."
  - `skills/third-party/security-audit/HUNTING.md:20` — "6. The core hunting method below, followed by the promotion procedure block."
  - `skills/third-party/security-audit/HUNTING.md:99` — "#### Promotion procedure — copy this promotion procedure verbatim into every hunter prompt"
  - `skills/third-party/security-audit/HUNTING.md:103` — "Reference only for you: the parent performs these steps; you never perform them."
  - `skills/third-party/security-audit/VALIDATION-AND-REPORTING.md:48` — "Copy this promotion procedure verbatim into every candidate-verifier prompt:"
  - `skills/security/third-party-security-skills/SKILL.md:44` — "The upstream promotion of files from `scratch/` to `artifacts/` needs trusted descriptor-based code the parent does not have. Nothing is promoted; evidence that only a promoted file would carry stays `needs_validation`."
  - `skills/security/third-party-security-skills/SKILL.md:42` — "It also keeps its read-only constraint: it writes no file anywhere and returns its candidates, ledger rows and evidence as text."
- **Problema:** o procedimento de 11 passos aparece três vezes no mesmo diretório — `SKILL.md:68-81`
  (1.979 B / 14 linhas), `HUNTING.md:99-136` (2.267 B / 38 linhas) e `VALIDATION-AND-REPORTING.md:48-85`
  (2.251 B / 38 linhas), **6.497 B** de texto idêntico — e `SKILL.md:82` declara a triplicação como
  desenho. Em Full Audit Mode o parent (a conversa principal, `commands/security.md:26`) lê os três
  arquivos, ou seja lê o mesmo procedimento três vezes antes do primeiro spawn; depois `HUNTING.md:20`
  e `:99` exigem 2.267 B dele **verbatim em todo prompt de hunter** e `VALIDATION-AND-REPORTING.md:48`
  outros 2.251 B em todo prompt de verifier. O roteador do framework (`:44`) já estabeleceu que o
  procedimento nunca corre aqui ("Nothing is promoted") e `:42` já proíbe o agente spawnado de escrever
  qualquer arquivo — e o próprio bloco se autodeclara inerte para quem o recebe (`HUNTING.md:103`:
  "the parent performs these steps; you never perform them").
- **Por que importa:** é contexto morto por construção, pago em dois lugares. Leitura: 6.497 B em vez de
  ~2.250 B (o parent relê a mesma coisa 3×). Emissão: com um hunter por unidade do ledger e um verifier
  por candidato, uma rodada `standard` de 8 unidades e 8 candidatos emite 8 × 2.267 B + 8 × 2.251 B =
  **36.144 B (~9.000 tokens)** de prompt para um procedimento que o roteador diz que não roda, sobre um
  orçamento de agentes que `SKILL.md:121-134` manda contar à mão.
- **Proposta:** acrescentar uma linha ao § Full Audit Mode do roteador: prompts de hunter e verifier
  substituem o bloco de promotion pela frase de `:44` ("nothing is promoted; evidência que só um arquivo
  promovido carregaria fica `needs_validation`"), e o parent dispensa os 11 passos de `SKILL.md`
  § Write isolation — mantendo as regras que de fato valem (escrita só em `scratch/`, nada de
  `/tmp` ou `$HOME`).
- **Impacto positivo:** −4.246 B de leitura por rodada no parent e −2,2 KB por prompt em cada spawn de
  hunter/verifier; na rodada de 8+8 acima, 36.144 B → ~1.400 B (−96%), num fluxo que já é o mais
  caro em spawns do repositório.
- **Impacto negativo / risco:** se o framework ganhar depois código parent com descritores confiáveis, a
  omissão deixa de ser inerte e vira lacuna de segurança em silêncio — a linha nova precisa ficar amarrada
  a `:44`, e qualquer mudança lá tem de reverter as duas juntas. O prompt também passa a divergir do
  contrato upstream do item 6 de `HUNTING.md:20`, de modo que um bump do pin em `sources.json` exige
  reler essa lista; e `method: "local"` de `report-schema.json` fica permanentemente inutilizável por
  desenho declarado, não por acidente.
- **Esforço:** Baixo

## Descartados por duplicação

| Candidato | Porta | Motivo |
|---|---|---|
| Descrições das 5 skills vendorizadas somam 1.721 chars (12,9% dos 13.334 chars de descrição de 168 skills) com `helpers/agent-lint.sh:308,340` isentando `skills/third-party/*` do `SKILL_DESC_LIMIT=95`, enquanto `scripts/install.sh:518-529` as symlinka no índice sempre carregado; `security-audit` entra neste delta com 359 chars | **3** | Mecanismo (descrição no índice sempre carregado) e remediação (tirar do laço de symlink) coincidem com `token-151-skills-flat-symlinked-into-claude-skills-index-12751-chars-per-context`; parente também de `token-sixteen-skill-descriptions-exceed-95-char-budget-…` (causa + remediação) |
| `skills/shared/interaction-patterns/SKILL.md:24-54` — § Documented Answer First nova (+32 linhas, ~2,4 KB) num arquivo de 404 linhas / 23.833 B lido por 59 arquivos, aplicável só "during approved work" | **5** | `interaction-patterns` 404 linhas × 44 carregadores já está no conjunto aberto; a remediação (extrair bloco para `references/`) é a do item pai |
| Bloco gerenciado `## dev-team-agents` de `skills/shared/auto-routing/SKILL.md` (6.094 B, 19 carregadores) crescendo com o bump de marcador v3→v4 do delta, injetado no `CLAUDE.md` de todo projeto instalado | **5** | Mesmo alvo e remediação de `token-install-sh-second-unconditional-claude-md-injection-35-lines-every-session`, no conjunto aberto |
| `skills/shared/output-format/SKILL.md:23-40` — § Delivery Confirmation Heading nova (+18 linhas) em skill com 14 carregadores | — | Morreu na evidência, não numa porta: `CLAUDE.md:219` manda "never restate the heading table" e nenhuma cópia da tabela existe — `auto-routing:60`, `agents/devops-specialist.md:165` e `ai-writing-signs:60` carregam só ponteiro de uma linha. Sem duplicação a medir |
| `skills/shared/setup-health-check/references/legacy-routing-v3.md` novo (4.523 B / 64 linhas), ao lado de `legacy-routing-v2.md` (8.300 B / 112 linhas): 12.823 B de snapshots congelados, um por bump de marcador, append-only por ADR-0065 | — | Morreu na evidência: `fix-patterns.md:289` só o lê quando aquele padrão de fix dispara — é referência sob demanda, não contexto sempre carregado; sem custo de token a quantificar no HEAD |
| `helpers/third-party-skills.py` (280 linhas) — output de comando verboso | — | Morreu na evidência: três `print()` no arquivo (`:223`, `:258`, `:260`), uma linha por skill sincronizada. Nada a cortar |
