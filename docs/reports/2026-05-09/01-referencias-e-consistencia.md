# 01 — Referências e Consistência

**Data:** 2026-05-09
**Escopo:** Quarta passada — gaps de governança, frontmatter inconsistente, skills setup-only com referência única, ausência de licenciamento e CI.
**Anti-repetição:** Os 75 fingerprints publicados em 2026-05-06 / -07 / -08 foram excluídos. Cada item abaixo recebe um fingerprint **inédito** para registro em [`_index.md`](../_index.md).

---

## Sumário

A primeira passada (06) cobriu surface-level. A segunda (07) entrou em comandos e robustez. A terceira (08) focou drift de manutenção. **Esta quarta passada identifica três classes não cobertas até aqui:**

1. **Inconsistências de frontmatter entre agentes** — campos `tools` declarados de formas sutilmente diferentes; um agente declara `Write` sem `Edit`; outro não declara `Bash` mas o Foundational Rule de seus pares exige `git log`.
2. **Governança ausente que impacta distribuição** — não há `LICENSE`, não há `.github/` (CI), e o instalador strippa `docs/` mas não documenta a estratégia de itens não strippados (`templates/`).
3. **Skills setup-only com referência única (quase órfãos funcionais)** — quatro skills (`auto-routing`, `backlog-template`, `docs-templates`, `setup-scan`) são carregadas exclusivamente pelo `setup-assistant`. Não são órfãs (passam no scan), mas a categoria está implícita e não documentada.

---

## Sugestões

### 1. `qa-specialist` declara `Write` sem `Edit`

**Fingerprint:** `ref-qa-specialist-write-without-edit`

**Evidência:**

```
agents/qa-specialist.md:tools: Read, Write, Bash, Glob, Grep
```

Todos os outros 8 agentes que produzem arquivos declaram `Read, Write, Edit, Bash, Glob, Grep`. O `qa-specialist` é o único com `Write` mas sem `Edit`. Em revisões de comportamento, o agente frequentemente atualiza um relatório de QA existente (acrescenta sessões de teste, corrige observações). Sem `Edit`, ele precisa reescrever o arquivo inteiro para mudar uma linha.

**Impacto positivo:** corrige a capacidade real do agente; alinha com seu uso descrito ("Validates product behavior, user flows").

**Impacto negativo:** nenhum. `Edit` é estritamente mais permissivo que `Write` em relação a integridade.

**Esforço:** Baixo (1 linha).

---

### 2. `product-analyst` sem `Bash`, mas Foundational Rule exige `git log`

**Fingerprint:** `ref-product-analyst-no-bash-tool`

**Evidência:**

```
agents/product-analyst.md:tools: Read, Write, Edit, Glob, Grep, WebSearch
```

Único agente "produtor" sem `Bash`. Ao mesmo tempo, o `Foundational Rule` padrão (presente em 14 agentes) inclui passos `git log --oneline -20` para identificar contexto recente. O `product-analyst.md` não inclui esse passo (count `0`), mas se incluísse, falharia por falta de tool.

**Decisão a tomar:** ou (a) confirmar que `product-analyst` opera só sobre PRDs e não precisa de git log — e nesse caso documentar a exceção no agente; ou (b) adicionar `Bash` para alinhar com o padrão.

**Impacto positivo:** elimina ambiguidade. Hoje um leitor não sabe se a omissão de Bash foi intencional ou esquecimento.

**Impacto negativo de (b):** `Bash` dá superfície para erros de execução.

**Esforço:** Baixo.

---

### 3. `setup-assistant` não inclui passo `git log` no Foundational Rule

**Fingerprint:** `ref-setup-assistant-no-git-log-loading`

**Evidência:** Dos 16 agentes, 14 incluem o passo `Run \`git log --oneline -20\``. As exceções são `product-analyst` (justificável: lê PRDs) e `setup-assistant` (que **deveria** olhar histórico para decidir se é projeto novo, herdado ou em manutenção — exatamente o que o agente classifica).

O `setup-assistant.md` (404 linhas) tem lógica complexa de classificação de projeto, mas pula a fonte de informação mais barata: histórico de commits. Hoje o agente pergunta ao usuário; com `git log`, poderia inferir e confirmar.

**Impacto positivo:** UX de setup mais inteligente; menos perguntas para o usuário em projetos com histórico.

**Impacto negativo:** mais leitura inicial (mitigado: `--oneline -20` custa pouco).

**Esforço:** Baixo (acrescentar passo no Foundational Rule ou na fase de classificação).

---

### 4. `technical-writer` é o único com `tools` declarados em ordem inconsistente

**Fingerprint:** `ref-tools-frontmatter-grep-glob-order-mismatch`

**Evidência:**

```
agents/technical-writer.md:tools: Read, Write, Edit, Bash, Grep, Glob
```

Os outros 15 agentes declaram `..., Glob, Grep` (Glob antes de Grep). O `technical-writer` declara `..., Grep, Glob`. Não há impacto funcional (a ordem não importa para Claude), mas é o tipo de divergência que um linter de frontmatter pegaria.

**Impacto positivo:** uniformidade do frontmatter. Possibilita validador automático com regex `^tools: Read, Write, Edit, Bash, Glob, Grep(, .+)?$`.

**Impacto negativo:** nenhum.

**Esforço:** Trivial (1 swap).

---

### 5. Repositório sem `LICENSE`

**Fingerprint:** `ref-license-file-missing`

**Evidência:** `ls LICENSE*` → não encontrado. O `install.sh` distribui o repositório como tarball para projetos terceiros via `curl`. Sem licença explícita, todo o conteúdo cai em copyright padrão — usuários downstream não têm permissão clara de uso, modificação ou redistribuição. Isso é especialmente relevante porque:

- O README declara intenção de distribuição global (`A global team of specialized Claude Code agents`).
- O `install.sh` baixa de URL pública via `curl`, implicando uso por terceiros.
- O CLAUDE.md tem cláusula de "Immutability Contract" mas não cláusula de licenciamento.

**Impacto positivo:** elimina ambiguidade legal; possibilita contribuições externas; permite forks legítimos.

**Impacto negativo:** decisão de licença (MIT? Apache-2.0? AGPL?) precisa ser tomada — e cada uma carrega trade-offs.

**Recomendação:** MIT ou Apache-2.0 (compatível com uso comercial e fork de skills).

**Esforço:** Baixo (1 arquivo) + decisão.

---

### 6. Sem CI (`.github/` ausente) — repo ensina mas não dogfooda

**Fingerprint:** `ref-no-ci-config-in-repo`

**Evidência:** Não há `.github/`, `.gitlab-ci.yml`, `bitbucket-pipelines.yml` ou Jenkinsfile. O projeto distribui o agente `devops-specialist` e 4 skills de CI/CD (`cicd-bitbucket`, `cicd-github`, `cicd-gitlab`, `cicd-jenkins`), mas o próprio repositório que produz esse conteúdo não roda **nada** automaticamente.

CI mínimo recomendado para este repo:
- Validar frontmatter de agentes/skills (campos obrigatórios, ordem de `tools`).
- Rodar `orphan-skill-scan.sh` em PR.
- Validar que `README.md` e `README.pt-BR.md` têm o mesmo número de seções H2.
- Rodar `shellcheck` em `scripts/**/*.sh`.

**Impacto positivo:** dogfooding completa o ciclo (instalador empurra hooks, agente devops empurra CI — mas hoje o repo não usa nada disso). Cada PR pega divergências que hoje só são pegas pela tarefa agendada de auditoria.

**Impacto negativo:** custo de manutenção do CI; risco de "false positive" em validadores muito rígidos.

**Esforço:** Médio (1 workflow inicial com 3 jobs).

---

### 7. Estratégia de strip do instalador é assimétrica e não documentada

**Fingerprint:** `ref-installer-strip-strategy-undocumented`

**Evidência:** O `install.sh` strippa antes de instalar:

```
rm -rf "$EXTRACTED_ROOT/.claude"
rm -rf "$EXTRACTED_ROOT/docs"
rm -f  "$EXTRACTED_ROOT/CLAUDE.md"
rm -f  "$EXTRACTED_ROOT/README.md"
rm -f  "$EXTRACTED_ROOT/README.pt-BR.md"
rm -f  "$EXTRACTED_ROOT/.gitignore"
rm -f  "$EXTRACTED_ROOT/scripts/install.sh"
rm -f  "$EXTRACTED_ROOT/scripts/orphan-skill-scan.sh"
```

Mantém `templates/`, `workflows/`, `commands/`, `agents/`, `skills/`, `scripts/hooks/`, `scripts/update.sh`, `scripts/check-updates.sh`, `scripts/new-adr.sh`, `scripts/graphify-refresh.sh`. O CLAUDE.md § "Package exclusions" lista exceções e justifica `CLAUDE.md`, `install.sh`, `orphan-skill-scan.sh`, `docs/`. Não justifica explicitamente o strip de `.gitignore`, `README.md`, `README.pt-BR.md` — embora o motivo (arquivos do repositório, não relevantes ao usuário) seja inferível.

Também não documenta o que **fica**. Nenhum mecanismo formal evita um futuro contribuidor adicionar pasta nova ao repo (ex: `audits/`) e ela vazar para projetos cliente.

**Impacto positivo de (a) documentar:** clareza de contrato. **Impacto positivo de (b) script com allowlist em vez de blocklist:** mais seguro contra adições futuras.

**Impacto negativo de (b):** quebra se nova pasta legítima for adicionada e esquecida na allowlist.

**Esforço:** Baixo para (a). Médio para (b).

---

### 8. Quatro skills exclusivamente carregadas pelo `setup-assistant`

**Fingerprint:** `ref-near-orphan-setup-only-skills`

**Evidência:** Análise de referências em `agents/`, `skills/`, `workflows/`, `commands/`:

| Skill | Carregada por (excl. SKILL.md self) |
|-------|--------------------------------------|
| `auto-routing` | só `setup-assistant.md` |
| `backlog-template` | só `product-analyst.md` |
| `docs-templates` | só `setup-assistant.md` |
| `setup-scan` | só `setup-assistant.md` |

`backlog-template` é único de `product-analyst` (ok — é uma skill de papel específico). As outras três são todas "setup-time" mas vivem em `skills/shared/` ao lado de skills usadas por todos (worktree, project-context). O leitor casual de `skills/shared/` não consegue distinguir skill universal de skill setup-only.

**Impacto positivo:** mover para `skills/setup/` ou prefixar (`skills/shared/setup-auto-routing/`) torna o domínio explícito; reduz noise no diretório `shared/`.

**Impacto negativo:** quebra paths absolutos em `setup-assistant.md` (esforço de migração) e exige bump de versão (paths são parte do contrato).

**Esforço:** Médio. Recomendação alternativa: criar README em `skills/shared/` que classifica cada skill ("Universal", "Setup-only", "Per-domain").

---

### 9. Relação entre `code-reviewer` e os dois reviewers especialistas é implícita

**Fingerprint:** `ref-code-reviewer-vs-specialists-roles-undocumented`

**Evidência:** O CLAUDE.md tabela "User-Invocable Commands" associa `/devteam:review` a "code-reviewer + software-architect + security-specialist + database¹". Não menciona `backend-reviewer` ou `frontend-reviewer`. Mas dentro do `code-reviewer.md`:

> "Automatically routes to backend-reviewer or frontend-reviewer based on the changeset."

Ou seja, há três agentes de review no repositório (`code-reviewer`, `backend-reviewer`, `frontend-reviewer`) mas o CLAUDE.md trata como se houvesse só um. Para um leitor novo, fica obscuro: quando invocar `code-reviewer` direto vs invocar um dos especialistas?

**Impacto positivo:** documentar o fluxo (ex: "Sempre invoque `/devteam:review`; o code-reviewer faz routing internamente; backend-reviewer e frontend-reviewer não são invocáveis diretamente") elimina ambiguidade.

**Impacto negativo:** se a intenção real é permitir invocação direta dos especialistas, falta uma tabela de exceção no CLAUDE.md.

**Esforço:** Baixo (1 parágrafo no CLAUDE.md ou nota nos 3 agentes).

---

## Lista Priorizada

| Prioridade | Sugestão | Esforço | Impacto |
|------------|----------|---------|---------|
| P0 | Criar `LICENSE` (MIT ou Apache-2.0) | Baixo | Alto (clareza legal de distribuição) |
| P1 | Adicionar CI mínimo (`.github/workflows/ci.yml`) com 3 jobs | Médio | Alto (dogfooding + drift catch) |
| P1 | Adicionar `Edit` ao `qa-specialist` | Baixo | Médio (capacidade real) |
| P2 | Decidir Bash em `product-analyst` ou documentar exceção | Baixo | Médio |
| P2 | Documentar relação code-reviewer × backend/frontend-reviewer | Baixo | Médio |
| P2 | Padronizar ordem `Glob, Grep` no `technical-writer` | Trivial | Baixo |
| P3 | Adicionar passo `git log` ao Foundational Rule do `setup-assistant` | Baixo | Médio |
| P3 | Documentar estratégia de strip do instalador no CLAUDE.md | Baixo | Baixo |
| P3 | Reorganizar/documentar skills setup-only | Médio | Médio (preventivo) |

---

## Próxima passada

Ângulos ainda não explorados após esta quarta passada (úteis para futuros relatórios): ergonomia dos comandos (UX dos `/devteam:*` quando o usuário passa argumentos inesperados), diferença entre `pre-tool-use` hooks no repo dev e nos projetos cliente, estratégia de versionamento semântico em relação a quebras silenciosas de skill paths.
