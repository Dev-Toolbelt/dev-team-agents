# Eixo B — Referências e Consistência — 2026-11-21

**Baseline:** `HEAD` = `17bfb26` · prioridade sobre os 55 arquivos autorais do delta.

**2 achados originais** (1 MEDIUM-HIGH, 1 LOW-MEDIUM). Um terceiro candidato — o parágrafo dos "sete
comandos sem agente" agora em `CLAUDE-md/commands.md:65` — morreu na Porta 3 e virou **correção de
marca 🔴** no [relatório da Fase 1](00-guardiao-verificacao.md#-correção-de-marca-fora-do-conjunto-amostrado--1).

---

## Gates executados

| Gate | Saída |
|---|---|
| `helpers/orphan-skill-scan.sh` | `clean ✓` |
| `helpers/orphan-template-scan.sh` | `clean ✓` |
| `helpers/agent-lint.sh` | `clean ✓` |
| `helpers/size-limits.sh` | `clean ✓` com 1 aviso: `⚠ CLAUDE.md: 602 lines (warning threshold: 600, fails at 700)` |
| `helpers/check-fingerprint-uniqueness.sh` | `✓ All 335 fingerprint slugs are unique across 2 bank file(s).` |
| `helpers/preferences-sync-lint.sh` | `clean ✓ (2 mirrors checked)` |
| `helpers/canonical-facts.py` | `clean ✓` |
| `python3 helpers/third-party-skills.py verify` | exit 0 |
| `.github/scripts/ci/01-lint.sh` | exit **127** — `shellcheck` não está instalado nesta máquina de auditoria; os passos anteriores ao step `shellcheck version` todos passam. **Não é defeito do repositório**, e o `auto-size-limits-…` que fazia este script sair 1 está de fato resolvido: `size-limits` agora separa `WARNINGS` de `VIOLATIONS` (`helpers/size-limits.sh:95-99`) |

Checagens estruturais extras, todas limpas: 172 skills com `name:` == basename do diretório e **zero**
nomes duplicados entre categorias · índice de ADRs com **60 linhas para 60 arquivos** · as 10
"discipline guides" que a tabela de rota de `third-party-web-skills` cita existem todas em
`guides/<categoria>/<id>.md` · as 17 categorias de `guides/` cobrem as 16 que a tabela nomeia ·
`doc-layouts.json` e o espelho bash `scripts/lib/docs-root.sh` concordam nas 21 chaves com coluna
`development` não-nula, incluindo as duas novas (`client-briefing`, `brand-guide`) · a lista de
`opt_out` de `CLAUDE-md/commands.md` casa exatamente os 12 de `commands.json` · as três skills novas
do delta são alcançadas pelos agentes que as declaram donas (`ui-ux-designer:52`,
`product-analyst:32`, `frontend-developer:49`, `frontend-reviewer:36`, `security-specialist:52`).

---

## MEDIUM-HIGH

### O gate de fatos canônicos varre as árvores vendorizadas, onde nenhuma das duas correções possíveis é legal

- **Fingerprint:** `auto-canonical-facts-scans-vendored-third-party-trees-with-no-legal-fix`
- **Alvo:** `helpers/canonical-facts.json`
- **Evidência:** `helpers/canonical-facts.json:3-8` — `"paths": [ "agents", "skills", "commands",
  "templates" ]`; `helpers/canonical-facts.py:60` varre cada entrada com
  `for md in sorted(base.rglob("*.md"))`, sem exclusão. Medido: a entrada `"skills"` alcança
  **285 arquivos `.md` sob `skills/third-party/`** (190 só de `modern-web-guidance`, vendorizado
  neste delta). O gate é **bloqueante** em CI — `.github/scripts/ci/01-lint.sh:74`:
  `blocking "canonical-facts" python3 -I helpers/canonical-facts.py`. E as duas saídas estão
  fechadas: `CLAUDE.md:164` — "**`skills/third-party/` is vendored upstream content, not authored
  here** (ADR-0047). **Never edit it in place**" — e
  `helpers/third-party-skills.py:246-247` recusa a árvore editada
  (`elif tree_hash(tree) != entry["sha256"]: failures.append(f"{name}: content differs from the
  recorded hash")`), checado por `tests/test_third_party_skills.py:108-114`.
- **Problema:** `canonical-facts` existe para pegar uma afirmação errada **escrita aqui** — o
  `_doc` do JSON diz "a tripwire for restated claims". Aplicado a conteúdo upstream, ele não pode
  ser satisfeito: editar o arquivo viola ADR-0047 e quebra o gate de hash; a única outra via é
  alargar um regex de `allow`, que vale para a árvore **inteira** e enfraquece o tripwire sobre o
  conteúdo autoral que ele foi feito para proteger.
- **Por que importa:** hoje passa por sorte, não por construção — nenhum dos 285 arquivos casa um
  dos padrões atuais. Um `sync` futuro de qualquer das 13 skills vendorizadas, ou um fato novo no
  JSON (a lista cresce a cada pass de SEO), derruba o CI num arquivo que ninguém tem permissão de
  consertar. O delta mostra que o cenário é concreto e já tem precedente: `6fbf868`
  (`chore(security): baseline an algorithm name in a vendored web guide`) resolveu exatamente este
  problema para o `gitleaks` — via `.gitleaksignore`, isto é, uma exclusão por caminho. O
  `canonical-facts` não tem o equivalente.
- **Proposta:** acrescentar ao schema de `canonical-facts.json` uma chave `exclude` (lista de
  prefixos, default `["skills/third-party/"]`) honrada por `scan()` em `canonical-facts.py:59`, e
  uma linha no `_doc` dizendo por que conteúdo não-autoral está fora. Uma afirmação errada num guia
  upstream é assunto da revisão do diff vendorizado que `CLAUDE.md:164` já exige, não de um lint sem
  remediação legal.
- **Impacto positivo:** remove 285 de ~460 arquivos `.md` do escopo do gate (−62% de I/O por
  execução, em CI e no `Stop`) e fecha a única classe de falha do gate que não tem correção
  permitida.
- **Impacto negativo / risco:** um fato factualmente errado num guia vendorizado deixa de ser
  sinalizado por qualquer automação — passa a depender da revisão humana do diff de `sync`, que é
  grande (190 arquivos nesta rodada). Um `exclude` mal escrito silenciaria conteúdo autoral; o
  default precisa ser o prefixo exato e o teste de `tests/test_canonical_facts.py` precisa pinar que
  um arquivo autoral sob `skills/` **continua** sendo varrido.
- **Esforço:** Baixo

---

## LOW-MEDIUM

### O plano de implementação de AEO/GEO afirma que seu próprio trabalho está não commitado

- **Fingerprint:** `docs-sync-aeo-geo-implementation-plan-status-says-uncommitted-at-head`
- **Alvo:** `docs/development/aeo-geo/implementation-plan.md`
- **Evidência:** `docs/development/aeo-geo/implementation-plan.md:5` — "**Status:** Aprovado e
  implementado em 2026-11-16 (Abordagem 1) — evidência: ADR-0066, novas referências em
  `skills/design/seo-optimization/references/`; **alterações não commitadas aguardando revisão**".
  As alterações estão no `HEAD`: `db2f240` (2026-11-17, `feat(seo): cover AI answer engines and AI
  shopping feeds`) commitou `skills/design/seo-optimization/SKILL.md` e os cinco arquivos novos de
  `references/` (`ai-commerce-feeds.md`, `ai-crawlers.md`, `answer-engines.md`, `monitoring.md`,
  `page-type-playbook.md`), e o próprio `implementation-plan.md` entrou no mesmo delta.
- **Problema:** um documento versionado declara, na sua linha de status, que o trabalho que ele
  descreve ainda não foi commitado — afirmação que o commit do próprio arquivo já desmentia.
- **Por que importa:** é a linha que um leitor usa para decidir se há trabalho pendente. Hoje ela
  diz que há, e manda procurar um working tree que não existe mais. O diretório `aeo-geo/` é o
  registro de decisão de um fluxo que `ADR-0066` encerrou; se o status mente, o registro perde a
  função. O mesmo padrão aparece no `adr-draft.md` do diretório, que **acerta** — `:3` diz
  "**Histórico:** rascunho substituído por [ADR-0066] (Accepted, 2026-11-16). Mantido como
  registro." — mostrando que a convenção existe e só não foi aplicada aqui.
- **Proposta:** trocar o fragmento final de `:5` por "implementado e commitado em `db2f240`
  (2026-11-17)", seguindo a redação de `adr-draft.md:3`.
- **Impacto positivo:** o único fato verificável da linha de status passa a ser verdadeiro, e o
  diretório fica legível como registro fechado.
- **Impacto negativo / risco:** fixa um sha num documento de prosa, que fica errado se o histórico
  for reescrito (rebase, squash) — o repositório já aceita esse custo em `adr-draft.md:3` e nas
  linhas de evidência do próprio banco de fingerprints. Nenhuma automação valida a linha, então ela
  pode drifar de novo no próximo passo do fluxo.
- **Esforço:** Baixo

---

## Candidatos descartados — premissas refutadas pela evidência

Sete hipóteses plausíveis morreram na própria verificação. Registradas para que o próximo pass não
as refaça:

1. **"As categorias `privacy` e `wasm` da tabela de rota de `third-party-web-skills` não existem"** —
   existem; `ls guides/` devolve 17 diretórios, os dois incluídos. A suspeita veio de eu ter lido o
   delta agrupado por diretório, que corta em ≤1 arquivo alterado.
2. **"`helpers/third-party-skills.py verify` não tem gate"** — tem:
   `tests/test_third_party_skills.py:108-114` o invoca contra a árvore real e exige exit 0, e
   `.github/scripts/ci/03-python.sh` roda a suíte.
3. **"Os documentos pt-BR de `docs/development/aeo-geo/` violam a regra de idioma de
   `CLAUDE.md:30`"** — não violam: os três carregam marcador de exceção na linha 1
   (`<!-- Exceção de idioma: documento em pt-BR a pedido do usuário. -->`), que é o mecanismo que a
   própria regra prevê ("unless a specific piece of content is explicitly marked as an exception").
4. **"`/devteam:brief` não foi registrado nos espelhos"** — foi: está em `commands.json` (43 de 43),
   `CLAUDE-md/commands.md` e nos dois READMEs.
5. **"O bloco PLAN GATE de `brief.md` é incondicional para um comando `plan_gate: conditional`"** —
   é o estilo da casa: `backend`, `frontend`, `design`, `seo` e `docs`, todos `conditional`, abrem o
   bloco com a mesma frase verbatim ("PLAN GATE — mandatory for every spawned agent").
6. **"A lista de `opt_out` de `CLAUDE-md/commands.md` divergiu de `commands.json`"** — casa
   exatamente nos 12.
7. **"`down` sem linha na tabela dos READMEs é achado novo"** — morreu na **Porta 3** contra
   `docs-sync-readme-command-table-omits-devteam-install-in-both-languages`: mesmo arquivo, mesma
   causa raiz (o gate `02-readme-sync.sh` compara EN↔pt-BR, não a tabela contra `commands.json`) e
   mesma remediação. Virou re-medição do pai (34/35 → 41/43, agora com duas ausências).
