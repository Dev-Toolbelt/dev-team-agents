# Eixo E — Economia de Tokens — 2026-11-21

**Baseline:** `HEAD` = `17bfb26`

**1 achado original** (MEDIUM).

---

## MEDIUM

### Três portas de decisão de spawn carregam 25 KB de skill de SEO para ler uma tabela de 1,1 KB

- **Fingerprint:** `token-seo-detection-signals-costs-25kb-skill-load-at-three-spawn-gates`
- **Alvo:** `skills/design/seo-optimization/SKILL.md`
- **Evidência:** três pontos decidem **se** `seo-specialist` deve ser spawnado, e os três mandam
  carregar a skill inteira para consultar uma única seção:
  - `skills/shared/spawn-classifier/SKILL.md:39` — "Project is a public site, landing page,
    e-commerce/online store, or blog (see `skills/design/seo-optimization/SKILL.md` § Detection
    Signals)"
  - `commands/frontend.md:23` — "`seo-specialist` — SEO quality gate (spawn when the project matches
    a Detection Signal in `skills/design/seo-optimization/SKILL.md` …)"
  - `agents/product-analyst.md:57` — "**Public indexable surface** — when the project matches a
    Detection Signal in `skills/design/seo-optimization/SKILL.md`, record as open scope decision"

  Medido no `HEAD`: `wc -lc skills/design/seo-optimization/SKILL.md` → **273 linhas / 25.107 bytes**.
  A seção que as três portas querem é `## Detection Signals — When SEO Is Required`,
  **linhas 36-49 = 1.168 bytes** (tabela de 5 tipos de sinal + a linha "**Not required** for"). As
  outras 259 linhas são o gate de SEO em si — `## Audit Procedure` (`:50`), os três checklists
  (`:70`, `:97`, `:108`), `## Core Web Vitals` (`:117`), `## Structured Data` (`:133`),
  `## AI Search — AEO / GEO` (`:157`), `## Quality Gate Output Format` (`:214`) e
  `## SEO Quality Gate` (`:219`) — nada disso serve para responder sim/não.
- **Problema:** **95,3% do que é lido é descartado** em cada uma das três portas (23.939 de 25.107
  bytes). Quem toma a decisão nunca executa a auditoria: o `spawn-classifier` classifica, o
  `/devteam:frontend` decide o roster, o `product-analyst` registra escopo aberto. Só o
  `seo-specialist` (`agents/seo-specialist.md:25`, "**required**, before anything else in this
  agent") precisa do corpo todo.
- **Por que importa:** o delta tornou o custo maior e assimétrico. `db2f240` levou a skill de 268
  para 273 linhas (23.547 → 25.107 bytes) e pendurou **5 referências novas** nas 12 existentes:
  `references/` agora soma **1.083 linhas / 108.183 bytes** em 17 arquivos. Isto é, a skill foi
  construída em volta do padrão de carga condicional — seu próprio `## Conditional References`
  (`:12-35`) é uma tabela de 17 linhas que diz "Load a reference only when its signal is present" —
  e a seção **mais** consultada do arquivo é a única que não participa desse padrão: fica no corpo
  sempre-carregado. `commands/frontend.md` é um dos comandos mais usados do harness, e o
  `spawn-classifier` corre em toda classificação de spawn.
- **Proposta:** mover a tabela para `skills/design/seo-optimization/references/detection-signals.md`
  e deixar em `:36` um ponteiro de uma linha (como as 17 linhas de `## Conditional References` já
  fazem); apontar as três portas de decisão para o arquivo de referência. `seo-specialist` continua
  carregando o `SKILL.md` e lê a referência como as outras 17.
- **Impacto positivo:** cada porta de decisão passa de 25.107 para ~1.300 bytes — **≈23,9 KB (95%)
  menos por consulta**, em três fluxos, sendo dois deles de alta frequência (`/devteam:frontend`,
  `spawn-classifier` em toda rodada de spawn). O `SKILL.md` cai ~14 linhas, afastando-se do
  `SKILL_LIMIT` de `helpers/size-limits.sh`.
- **Impacto negativo / risco:** o `seo-specialist`, que hoje tem a tabela no mesmo arquivo que já
  carrega, passa a precisar de **uma leitura a mais** — troca certa, porque é um spawn por
  auditoria contra três consultas por fluxo, mas é uma regressão real para ele. O risco maior é
  **drift**: se o `:36` virar uma cópia resumida em vez de um ponteiro puro, passam a existir duas
  casas para a mesma tabela e nenhum gate as compara — `helpers/canonical-facts.py` checa fatos
  errados, não divergência entre espelhos. A mitigação é que `:36` não contenha sinal nenhum, só o
  caminho. E é o 18º arquivo em `references/`, num diretório que já cresceu 42% neste delta.
- **Esforço:** Baixo

---

## Verificações sem achado

- **Skill sempre-carregada que poderia ser condicional:** varri os carregamentos incondicionais dos
  19 agentes. As candidatas que sobraram — `interaction-patterns` (404 linhas × 43 comandos),
  `backlog-template` (335 linhas), `token-efficiency`, `project-context` (374 linhas) — todas já têm
  fingerprint aberto. Porta 5.
- **Custo do skill vendorizado novo:** `skills/third-party/modern-web-guidance/` traz 190 guias, mas
  **não** é carga incondicional: `skills/architecture/third-party-web-skills/SKILL.md` (83 linhas) é
  a ponte, e sua § Routing manda "Read only the guides the task calls for: one discipline guide at
  most, plus the use-case guides that match", com § Finding a Guia mandando **listar o diretório**
  antes de ler ("List the category directory with the provider's file tools. File names are the guide
  ids"), e `:35` fecha com "A backend-only, infrastructure, tooling or test-only task reads none of
  them." É o desenho correto para 190 arquivos; nada a propor.
- **Leitura de arquivo inteiro onde `grep`/`head` bastaria:** `scripts/hooks/stop.sh:44-51` computa
  os caminhos tocados uma vez e exporta (`DEVTEAM_TOUCHED_PATHS`), em vez de cada um dos 16
  sub-scripts re-forkar `git status` + `git log` — o padrão que este eixo pediria já está
  implementado, com o comentário explicando a economia.
- **Output verboso de comando:** `helpers/canonical-facts.py` aceita `--quiet` e
  `.github/scripts/ci/01-lint.sh` imprime uma linha por gate. A economia real nesse caminho é
  reduzir **escopo**, não output: ver
  `auto-canonical-facts-scans-vendored-third-party-trees-with-no-legal-fix` em
  [`02-referencias-e-consistencia.md`](02-referencias-e-consistencia.md), cuja proposta remove 285
  de ~460 arquivos `.md` do gate (−62% de I/O por execução, em CI e em todo `Stop`). Registrado lá
  por ser primariamente um defeito de referência, não de economia; o ganho de tokens é consequência.
