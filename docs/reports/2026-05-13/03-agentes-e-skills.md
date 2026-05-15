# Relatório — Agentes e Skills (2026-05-13)

Auditoria focada em **assimetrias entre agents/skills, gaps de cobertura, e drift estrutural**. Inclui verificação de **stack-agnosticism** conforme regra do projeto.

---

## Verificação Cruzada — Stack-Agnosticism (Regra do Projeto)

> **Regra (CLAUDE.md:124):** _"Stack-agnostic: no hardcoded framework, language, or tool references in agent core behavior."_

Agents auditados via `grep -niE "\b(react|vue|angular|django|laravel|rails|postgres|...)\b"`. Apenas **violações em diretriz central** (Foundational Rule, Core Principle, descrição do agent) são consideradas — exemplos dentro de detection rules ou skill loads são **legítimos**.

### Violações Detectadas

| Agent | Linha | Trecho | Tipo de violação |
|-------|-------|--------|-------------------|
| `agents/devops-specialist.md` | **3** (description frontmatter) | _"Docker-first infrastructure specialist"_ | **Hardcoded preference** — toma posição sobre stack ("Docker antes de Kubernetes"); um time que padronizou Kubernetes desde o dia 1 não terá um devops "Docker-first" |
| `agents/devops-specialist.md` | **8** (Core identity) | _"You are a Docker-first infrastructure engineer […] Your default answer to 'how should we deploy this?' is Docker on a VPS before it's Kubernetes in the cloud."_ | **Hardcoded preference repetida** — opinião de stack baked-in |
| `agents/backend-developer.md` | **43** | _"Monolithic (server-rendered): Backend renders views directly (Laravel+Blade, Django+Templates, Rails+ERB, etc.)."_ | **Examples-as-pattern** — listar 3 frameworks concretos é OK como "etc.", mas a estrutura do parágrafo trata-os como referência canônica |
| `agents/backend-developer.md` | **104** | _"Generate TypeScript types after schema changes: `supabase gen types typescript`"_ | **Hardcoded TypeScript** — comando assume cliente TS; em Python/Go, equivalente seria diferente. Aparece dentro do bloco "Critical rules when Supabase is detected" — **mitigado**, mas a regra não está modalmente condicionada |
| `agents/backend-test-specialist.md` | **115-119** | Tabela de coverage com `PHP\|Python\|Java\|Ruby` | **Hardcoded matrix** — 4 linguagens enumeradas; outras (Rust, Elixir) ausentes; padrão "tabela enumerada" é fragil mas **acceitável dada a natureza do tooling** |
| `agents/security-specialist.md` | **137-145** | `bandit -r . -ll  # Python\nbundler-audit  # Ruby\n...` | **Hardcoded SAST tools por linguagem** — semelhante; aceitável mas **não exaustivo** |

### Veredicto

- **devops-specialist (linhas 3 e 8)**: **violação real e clara**. A preferência "Docker-first" é stack-opinionated e contradiz a regra de stack-agnosticism. Esses 2 trechos deveriam ser reescritos como neutros (e.g., "infrastructure specialist that picks the simplest deployment that fits the project's scale and team expertise").
- **Outros 4 agents**: **dentro da zona aceitável** (examples within detection contexts). Mitigados pelo uso de "Detection" + skill loading pattern que delega detalhes para skill específica de stack.

### Sugestão de Refactor (devops-specialist)

```diff
- description: Docker-first infrastructure specialist. Sets up dev and production environments with Docker, provisions Linux VPS servers, configures CI/CD pipelines (GitHub Actions, Bitbucket, GitLab, Jenkins), deploys to AWS, GCP, and Azure in a cost-optimized way…
+ description: Infrastructure specialist. Sets up dev and production environments, provisions servers, configures CI/CD pipelines, deploys to cloud or self-hosted infra in a cost-optimized way, and manages monitoring/observability stacks. Picks the right tool for the project (Docker, Compose, Kubernetes, serverless) based on scale, team, and existing setup. Use for any infrastructure, deployment, environment configuration, or observability task.
```

E na linha 8 (Core identity), reescrever em forma neutra ou prefixar com "Default in absence of project signals: Docker on a VPS for small teams; let the project's existing stack drive otherwise."

> **Fingerprint:** `agent-devops-specialist-violates-stack-agnostic-rule-with-docker-first-bias`

---

## 2. `agent-mobile-test-specialist-3rd-consecutive-pass-still-missing`

**Severidade:** 🟠 Alta — registrado em 2026-05-11 e 2026-05-12, **sem owner**

**Detecção:** `ls agents/*mobile*` retorna apenas `agents/mobile-developer.md`. Não há `agents/mobile-test-specialist.md` apesar de:
- backend tem `backend-test-specialist`.
- frontend tem `frontend-test-specialist`.
- mobile-developer hoje cobre tanto **implementação** quanto **testes** (Detox/Maestro/Appium routing adicionado em 2026-05-12).

A partir de 3 passadas, a sugestão precisa de **decisão consciente**: criar agent novo, ou renomear `mobile-developer` para esclarecer responsabilidade dual.

**Impacto positivo (se corrigido — opção A):** simetria com backend/frontend pipeline; `/devteam:tester` pode spawnar 3 specialists.

**Impacto positivo (se corrigido — opção B):** evita sprawl; documentação clara de que mobile é "monolítico por design".

**Impacto negativo (se mantido):** ambiguidade permanece; CLAUDE.md tabela `/devteam:tester` cita `mobile-developer¹` mas o command nunca o spawna.

**Sugestão:** abrir ADR `0006-mobile-pipeline-decision.md` decidindo:
- A: criar `mobile-test-specialist` (mover test routing de mobile-developer); ou
- B: documentar oficialmente que `mobile-developer` é dual-purpose; atualizar `commands/tester.md` para incluir spawn condicional dele.

---

## 3. `agent-architect-frontmatter-no-webfetch-but-loaded-skills-suggest-research`

**Severidade:** 🟡 Média

**Detecção:** `grep "^tools:" agents/software-architect.md` retorna:

```
tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch
```

Tem `WebSearch` mas **não** `WebFetch`. Skills carregadas pelo architect frequentemente exigem leitura de URL específica:
- ADR research: precisa `WebFetch` para ler RFCs / Stack Overflow / vendor docs.
- API design references: precisa `WebFetch` para ler OpenAPI specs externos.

`WebSearch` retorna snippets; `WebFetch` retorna conteúdo full. Architect vai esbarrar nesse limite quando precisar ler um artigo técnico inteiro.

**Impacto positivo (se corrigido):** architect pode embed referências completas em ADRs sem hop manual via WebSearch + leitura humana.

**Impacto negativo (se mantido):** ADRs com bibliografia rasa; usuário precisa fazer fetch externo para passar conteúdo de volta.

**Sugestão:** atualizar frontmatter:

```yaml
tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch
```

Mesmo padrão para `security-specialist` (que precisa fetch CVE pages, vendor advisories).

---

## 4. `skill-stack-detection-still-missing-3rd-pass-shared-base-needed`

**Severidade:** 🟡 Média — reforço de fingerprint registrado em 2026-05-12

**Detecção:** `find skills -name "*stack*"` continua vazio. Stack detection inline em **4 agents**:
- `setup-assistant` (FIRST_RUN audit)
- `software-architect` (architecture decisions)
- `database-specialist` (engine routing)
- `devops-specialist` (CI/CD platform routing)

Cada agent tem heurística ligeiramente diferente. Exemplo de divergência:

| Agent | Heurística para "Python project" |
|-------|-----------------------------------|
| `setup-assistant` | `pyproject.toml` OR `requirements.txt` OR `*.py` no root |
| `software-architect` | `pyproject.toml` only |
| `database-specialist` | (não relevante) |
| `devops-specialist` | inline `docker-compose.yml` heuristic, no Python rule |

**Impacto positivo (se corrigido):** skill `skills/shared/stack-detection/SKILL.md` única, ~80 linhas, define matriz `signal → stack`. Cada agent loadeia e tem mesma resposta.

**Impacto negativo (se mantido):** detecções divergentes; usuário pode receber recomendações conflitantes em `/devteam:plan` que invoca múltiplos agents.

**Sugestão:** criar `skills/shared/stack-detection/SKILL.md` com tabela canônica:

| Signal file | Inferred stack |
|-------------|-----------------|
| `pyproject.toml`, `requirements.txt`, `*.py` no root | Python |
| `package.json`, `tsconfig.json`, `*.ts`/`*.js` no `src/` | Node/TS/JS |
| `Cargo.toml` | Rust |
| `composer.json` | PHP |
| `Gemfile` | Ruby |
| `go.mod` | Go |
| `pom.xml`, `build.gradle` | Java/Kotlin |
| `*.csproj`, `Cargo.toml` | C# |

E remover heurísticas inline duplicadas. Estimativa: -120 linhas spread, +80 linhas em skill, **economia ~40 linhas + paridade semântica**.

---

## 5. `skill-graphify-setup-still-no-conditional-skip-3rd-pass-277-lines`

**Severidade:** 🟡 Média — reforço pendente

**Detecção:** `wc -l skills/devops/graphify-setup/SKILL.md` = **277 linhas** (inalterado). Skill é loadeada por setup-assistant em FIRST_RUN. Para projetos puramente docs (ex.: livro técnico em md), graphify não agrega valor.

Não há gate explícito tipo:

```bash
# Skip graphify if project has no source code
SOURCE_FILES=$(find . -name '*.py' -o -name '*.ts' -o -name '*.go' -o -name '*.java' 2>/dev/null | head -1)
[ -z "$SOURCE_FILES" ] && exit 0
```

**Impacto positivo (se corrigido):** ~5.500 tokens salvos em projetos não-código; setup-assistant não pergunta sobre graphify em context impróprio.

**Impacto negativo (se mantido):** projeto de documentação carrega skill irrelevante de 277 linhas.

**Sugestão:** adicionar seção "When to Skip" no top da skill:

```markdown
## When to Skip This Skill

Skip if:
- Project has no source files (only `.md`, `.rst`, configuration)
- Project has < 20 source files (graphify overhead > benefit)
- User declines via `setup-assistant` prompt
```

E ajustar setup-assistant para fazer essa checagem antes do load.

---

## 6. `skill-templates-folder-grew-but-no-template-skill-wraps-them`

**Severidade:** 🟡 Média

**Detecção:** Commit `c207e3f` adicionou `templates/{adr,backlog,plan,runbook}-template.md`. Hoje `ls templates/` mostra 4 arquivos. Porém:

| Template | Skill que o referencia |
|----------|------------------------|
| `plan-template.md` | `skills/shared/plan-mode/SKILL.md` ✅ |
| `adr-template.md` | `skills/shared/adr/SKILL.md` ✅ |
| `backlog-template.md` | `skills/shared/backlog-template/SKILL.md` ✅ (próprio skill) |
| `runbook-template.md` | ❌ **nenhuma skill** (template órfão) |

Antigo fingerprint `auto-no-orphan-templates-scan` (2026-05-08, pendente) foi adiado para "quando houver 3+ templates". Hoje há 4. **Trigger atingido**.

**Impacto positivo (se corrigido):** simetria; runbook template ganha skill that documents how to fill it; orphan template scan ativável.

**Impacto negativo (se mantido):** template órfão; usuário não sabe que existe ou quando usar.

**Sugestão:**
1. Criar `skills/shared/runbook/SKILL.md` (~80 linhas) referenciando o template e ensinando fluxo de incident-response → runbook. Wirear a `incident-response/SKILL.md`.
2. Implementar `auto-no-orphan-templates-scan` (rosa-script de ~30 linhas) e adicioná-lo ao Stop hook.

---

## 7. `skill-discovery-mode-no-stale-lock-cleanup-script-30min-rule-only-documented`

**Severidade:** 🟡 Média

**Detecção:** `skills/shared/discovery-mode/SKILL.md` linha ~115:

```bash
LOCK=".claude/.discovery-lock"
…
# If the lock is stale (older than 30 minutes), remove it and proceed
```

Porém:
- A lógica de "stale > 30min" é **documentada** mas não implementada como helper.
- Cada agent que usa discovery copia inline.
- Sem garbage collection automático: se um agent morrer (Claude crash), lock fica indefinidamente até alguém detectar.

**Impacto positivo (se corrigido):** lock cleanup centralizado; sem boilerplate inline duplicado em 3 agents.

**Impacto negativo (se mantido):** lock pode persistir indefinidamente em corner cases; usuário precisa `rm .claude/.discovery-lock` manualmente.

**Sugestão:** criar `scripts/cleanup-stale-locks.sh` (~20 linhas) e:
- Wirear ao Stop hook (`scripts/hooks/stop/05-stale-locks.sh`).
- Atualizar discovery-mode skill para apontar a esse script em vez de inline bash.

---

## 8. `agent-frontend-developer-loads-jquery-skill-orphan-of-modern-stacks`

**Severidade:** 🟢 Baixa — observação de governança

**Detecção:** `skills/ui-libraries/jquery/SKILL.md` (80 linhas) existe entre 6 ui-libraries skills (mui, shadcn, antd, chakra-ui, bootstrap, jquery). frontend-developer condicionalmente carrega cada uma. Porém:

- jQuery não é "ui library" no mesmo sentido das outras (é library DOM, não componente).
- Em projetos modernos, jQuery aparece tipicamente em legado, não em greenfield.
- A descrição da skill não distingue "modern app" vs "maintenance of jQuery codebase".

Decisão arquitetural: manter ou mover para `skills/legacy/jquery/`?

**Impacto positivo (se decidido):** clareza de que jquery é categoria diferente; agente ui-ux-designer pode pular sua consideração para greenfield.

**Impacto negativo (se mantido):** ambiguidade; jquery skill aparece junto com Chakra UI em sugestões.

**Sugestão:** mover para `skills/integrations/jquery/SKILL.md` e atualizar referências; ou criar categoria `skills/legacy/`.

---

## 9. `skill-frontmatter-validation-now-strict-but-tests-not-included`

**Severidade:** 🟡 Média — sub-escopo de `skill-frontmatter-strict-validation-missing-from-lint` (✅ Executed em 2026-05-13)

**Detecção:** Commit `5b61720` adicionou validação de skill frontmatter. Porém:
- Não há **fixture tests** para o validator (e.g., `tests/fixtures/invalid-frontmatter.md`).
- Mudanças no validator podem regredir silenciosamente.
- CI roda o lint contra o **próprio repo** apenas; não há test suite que prove "esses 5 padrões são detectados; esses 3 não são falsos positivos".

**Impacto positivo (se corrigido):** validador testado; refactor do `agent-lint.sh` preserva comportamento.

**Impacto negativo (se mantido):** próximo refactor de agent-lint pode quebrar validações existentes sem CI pegar.

**Sugestão:** criar `tests/agent-lint-fixtures/` com:
- `01-valid.md` (deve passar)
- `02-missing-tools.md` (deve falhar com mensagem específica)
- `03-non-canonical-key.md` (deve falhar)
- `04-tools-without-Read.md` (deve falhar)

E CI step:
```yaml
- name: agent-lint fixture tests
  run: bash scripts/test-agent-lint.sh
```

---

## 10. `agent-product-analyst-other-trackers-still-asana-clickup-monday-ungated`

**Severidade:** 🟡 Média — sub-escopo de `agent-product-analyst-loads-jira-skill-but-not-other-trackers` (⚠️ Partial em 2026-05-13)

**Detecção:** product-analyst hoje tem detection sections para Jira e Linear. Porém `skills/shared/setup-scan/SKILL.md` lista **5+ trackers**:

| Tracker | Skill existe? | Detection in product-analyst? |
|---------|----------------|--------------------------------|
| Jira | ✅ | ✅ |
| Linear | ✅ | ✅ |
| Asana | ❌ | ❌ |
| ClickUp | ❌ | ❌ |
| Monday | ❌ | ❌ |
| GitHub Issues | ❌ (implícito em git-workflow) | ❌ |

**Impacto positivo (se corrigido):** product-analyst funciona em projetos não-Atlassian; reduz acoplamento implícito a Jira/Linear.

**Impacto negativo (se mantido):** projetos com Asana/ClickUp/Monday acabam com backlog desconectado do tracker real.

**Sugestão:** roadmap incremental:
1. Adicionar `skills/integrations/github-issues/SKILL.md` (delta menor — `gh` CLI já presente).
2. Adicionar detection generic em product-analyst: "if no tracker MCP detected → fallback to `gh issue create`".
3. Skills Asana/ClickUp/Monday podem ser opt-in (não bloqueante).

---

## 11. `skill-comments-policy-sections-extracted-but-no-language-aware-loader-in-agents`

**Severidade:** 🟡 Média — sub-escopo de `token-comments-policy-417-lines-still-monolith-no-section-loading` (⚠️ Partial em 2026-05-13)

**Detecção:** Commit `6c8516b` extraiu `comments-policy` para 91 linhas + `sections/{aaa-pattern,anti-patterns,type-annotations}.md`. Porém os agents que loadeiam `comments-policy` ainda fazem load eager (full SKILL.md), sem condicional por linguagem.

Padrão ideal:

```markdown
Load `skills/shared/comments-policy/SKILL.md`. If the project uses Python, also load `sections/type-annotations.md`. If reviewing test files, also load `sections/aaa-pattern.md`.
```

Padrão atual: cada agent só faz `Load skills/shared/comments-policy/SKILL.md`.

**Impacto positivo (se corrigido):** lazy-load real (ex.: agent só carrega `sections/type-annotations.md` se touched-file is `*.py`); economia ~30-50 linhas dependendo do contexto.

**Impacto negativo (se mantido):** extração para `sections/` é sintaxe sem semântica — skill mais curta mas comportamento igual.

**Sugestão:** adicionar bloco "Conditional Section Loading" no comments-policy/SKILL.md; atualizar 9 agents para checar linguagem antes de loadear sections/.

---

## Resumo

| Prioridade | Quantidade |
|-----------|-----------|
| 🟠 Alta | 1 (`agent-devops-specialist-violates-stack-agnostic` + `agent-mobile-test-specialist-3rd-consecutive`) — duas violações Alta na verdade |
| 🟡 Média | 8 |
| 🟢 Baixa | 1 |

**Padrões emergentes desta passada:**

- **Stack-agnosticism violation finalmente identificada** — após 7 audits, a regra `stack-agnostic` não havia sido cruzada com o conteúdo real dos agents. devops-specialist viola explicitamente.
- **Sugestões reforçadas pela 3ª vez** (mobile-test-specialist, stack-detection skill, graphify gating) merecem **decisão arquitetural formal via ADR** em vez de reproposta.
- **Padrão de "extração sem semântica"** — `comments-policy` foi extraído mas o lazy-load real depende de updates nos consumers. Refactor incompleto.
- **Fixtures/tests para tools de governança** — agent-lint, size-limits, orphan-skill-scan não têm test suite; validação de validators é metaproblema.
