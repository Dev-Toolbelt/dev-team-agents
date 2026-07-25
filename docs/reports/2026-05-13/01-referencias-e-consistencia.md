# Relatório — Referências e Consistência (2026-05-13)

Auditoria focada em **referências quebradas/órfãs, drift declarativo, e inconsistências estruturais** detectadas hoje (terça-feira). Todas as sugestões abaixo são **originais** — não constam previamente no `_index.md` em formato idêntico. Quando há sobreposição parcial com fingerprint anterior, o novo escopo é especificado.

> **Contexto:** auditoria executada após o batch de 22 commits entre `e7335a4` (publicação dos relatórios de 2026-05-12) e `ac6af24` (HEAD em 2026-05-13). Foco especial em **drifts criados pelas próprias features novas** (extração massiva para `references/`, lockfile de discovery, hook PreCompact, validate-commit-msg.sh).

---

## 1. `ref-tester-command-misses-mobile-developer-spawn-vs-claude-md-table`

**Severidade:** 🟠 Alta — drift entre declaração e implementação

**Detecção:** `CLAUDE.md` linha que descreve `/devteam:tester` declara: _"backend-test-specialist + frontend-test-specialist¹ + **mobile-developer¹**"_. Porém `cat commands/tester.md` mostra apenas:

```
Always spawn:
- `backend-test-specialist` …
Also spawn if the context includes frontend changes:
- `frontend-test-specialist` …
```

Sem qualquer menção a `mobile-developer`. A nota footer¹ "conditional" da CLAUDE.md sugere que mobile-developer deveria ser spawneado quando há mudanças mobile no contexto.

**Impacto positivo (se corrigido):** restaura paridade entre CLAUDE.md (fonte declarativa) e `commands/tester.md` (implementação); usuários que rodam `/devteam:tester` em projetos mobile ganham cobertura de testes.

**Impacto negativo (se mantido):** projetos mobile que usam `/devteam:tester` ficam sem testes; CLAUDE.md continua mentindo sobre o comportamento real; reforça o padrão de drift entre tabela e código.

**Sugestão:** adicionar bloco em `commands/tester.md`:

```
Also spawn if the context includes mobile changes:
- `mobile-developer` at `.claude/agents/dev-team/mobile-developer.md` — author or update tests for mobile components (Detox, Maestro, Appium)
```

---

## 2. `ref-validate-commit-msg-script-orphaned-from-ci-and-commit-command`

**Severidade:** 🟡 Média

**Detecção:** Commit `bae0f79` criou `scripts/validate-commit-msg.sh` (49 linhas). Porém:

| Local potencial de uso | Referência? |
|------------------------|-------------|
| `commands/commit.md` | ❌ não chama o script |
| `commands/pr.md` | ❌ tem regex inline próprio (Step 0a) |
| `.github/workflows/ci.yml` | ❌ |
| `scripts/install.sh` | ❌ não registra commit-msg git hook |
| `skills/shared/conventional-commits/SKILL.md` | ✅ menciona como exemplo standalone |

A skill apenas **documenta** que o script existe; nenhum fluxo automatizado o invoca.

**Impacto positivo (se corrigido):** validação consistente em CI e commit hook; `commands/commit.md` e `commands/pr.md` chamam o mesmo script (DRY) em vez de regex inline diferentes.

**Impacto negativo (se mantido):** drift entre 3 implementações da mesma regex; usuários precisam rodar o script manualmente; commits malformados continuam passando até o reviewer humano notar.

**Sugestão:**
1. CI step: `bash scripts/validate-commit-msg.sh "$(git log -1 --format=%B HEAD)"` no PR/push.
2. `commands/commit.md` Step 4.5: `printf "$MSG" | bash .dev-team-agents/scripts/validate-commit-msg.sh` antes do `git commit`.
3. `install.sh`: registrar `commit-msg` git hook que invoca o script (opt-in via flag).

---

## 3. `ref-claude-md-update-command-still-claims-two-scripts-after-2026-05-08-finding`

**Severidade:** 🟡 Média — sub-escopo do antigo `docs-sync-update-flow-claude-md` (2026-05-08, ainda pendente)

**Detecção:** A tabela "User-Invocable Commands" do CLAUDE.md mantém:

```
| `/devteam:update` | runs `check-updates.sh` + `update.sh` | …
```

Porém:
- `wc -l scripts/check-updates.sh` = **3 linhas** (shim deprecado que apenas chama `update.sh --check`).
- `cat commands/update.md` invoca apenas `update.sh` (e variantes), nunca `check-updates.sh` standalone.

A descrição na CLAUDE.md continua **incorreta após 5 passadas consecutivas**. O antigo fingerprint foi registrado em 2026-05-08 mas focava em "dois scripts"; este escopo agora é **mais específico**: a coluna "Agentes invocados" cita um script obsoleto.

**Impacto positivo (se corrigido):** elimina referência a script morto; CLAUDE.md vira fonte confiável.

**Impacto negativo (se mantido):** novos contribuidores leem CLAUDE.md e tentam editar `check-updates.sh` (3 linhas) achando que é o canônico; ruído permanente.

**Sugestão:** alterar para:

```
| `/devteam:update` | runs `update.sh` (which delegates to `hooks/pre-tool-use/01-check-updates.sh` for the freshness check) | …
```

E remover `scripts/check-updates.sh` em commit separado (ou adicionar deprecation comment apontando para o canônico).

---

## 4. `ref-no-workflow-mobile-shortcut-command-asymmetric-with-fullstack-refactor-review`

**Severidade:** 🟡 Média

**Detecção:** Após commit `13fd0dc` (workflow shortcut commands), 8 dos 10 workflows têm shortcut `/devteam:workflow-<nome>`. Porém:

| Workflow | Shortcut command? |
|----------|-------------------|
| `workflows/new-project.md` | ✅ `commands/workflow-new.md` |
| `workflows/maintenance.md` | ✅ `commands/workflow-maintenance.md` |
| `workflows/bug-fix.md` | ✅ `commands/workflow-bugfix.md` |
| `workflows/inherited-project.md` | ✅ `commands/workflow-inherited.md` |
| `workflows/security-patch.md` | ✅ `commands/workflow-security-patch.md` |
| `workflows/fullstack.md` | ✅ `commands/workflow-fullstack.md` |
| `workflows/refactor.md` | ✅ `commands/workflow-refactor.md` |
| `workflows/review.md` | ✅ `commands/workflow-review.md` |
| `workflows/mobile.md` | ❌ **falta** `commands/workflow-mobile.md` |
| `workflows/design.md` | ❌ **falta** `commands/workflow-design.md` |

**Impacto positivo (se corrigido):** simetria de UX (10/10 workflows acessíveis via slash command); CLAUDE.md tabela de commands fica completa.

**Impacto negativo (se mantido):** usuários precisam abrir e ler `workflows/mobile.md` manualmente, enquanto outros workflows são "one-liner".

**Sugestão:** criar `commands/workflow-mobile.md` e `commands/workflow-design.md` no padrão dos existentes (~14 linhas cada). Atualizar tabela de commands na CLAUDE.md.

---

## 5. `ref-size-limits-warn-only-permanent-tech-debt-11-agents-violating`

**Severidade:** 🟠 Alta — limite explícito violado em 11 de 17 agents (65%)

**Detecção:** `bash scripts/size-limits.sh` (sem `--warn-only`) hoje retornaria 11 violações:

| Agente | Linhas | Acima do limite |
|--------|--------|------------------|
| `frontend-developer.md` | 285 | +43% |
| `ui-ux-designer.md` | 285 | +43% |
| `backend-developer.md` | 269 | +35% |
| `frontend-test-specialist.md` | 262 | +31% |
| `mobile-developer.md` | 249 | +25% |
| `devops-specialist.md` | 237 | +19% |
| `security-specialist.md` | 234 | +17% |
| `code-reviewer.md` | 228 | +14% |
| `setup-assistant.md` | 226 | +13% |
| `qa-specialist.md` | 208 | +4% |
| `backend-reviewer.md` | 204 | +2% |

CI usa `--warn-only` desde commit `9b7ff74` ("for gradual CI rollout"), mas **não há plano declarado** de mover para enforce mode. Este flag é tipicamente usado por 1-2 sprints, não por tempo indeterminado.

**Impacto positivo (se corrigido):** força extração para skills/sections; remove o "limite ~200 linhas" como mentira polida em CLAUDE.md.

**Impacto negativo (se mantido):** limite de 200 linhas vira sugestão decorativa; novos agents espontaneamente excedem; tech debt cresce.

**Sugestão:** definir cronograma explícito — ex.: até `v1.5.0`, mover para `--strict` (default sem flag). Documentar no CHANGELOG. Em paralelo, abrir issue com plano de extração para os 11 agents (priorizando `frontend-developer` e `ui-ux-designer` que estão 43% acima).

---

## 6. `ref-orphan-skill-scan-warn-section-not-actionable-no-fix-template`

**Severidade:** 🟡 Média — output sem instrução de fix

**Detecção:** Após commit `97a3f0d` e `19de0e1`, a saída de `bash scripts/orphan-skill-scan.sh` agora inclui uma seção **WARN** (não ACTION REQUIRED):

```
 WARN — Skills loaded more than once in the same agent:
  · agents/backend-developer.md loads skills/shared/worktree/SKILL.md more than once
  · commands/backend.md loads skills/shared/plan-mode/SKILL.md more than once
  …
```

Hoje há **8 agents** carregando `worktree` em duplicidade e **5 commands** carregando `plan-mode` em duplicidade — total de **13 instâncias**. A seção WARN aparece, mas:
- Não tem título "ACTION REQUIRED" (como a de skills órfãs).
- Não fornece template de fix (só lista o problema).
- Não documenta se é um WARN bloqueante ou meramente informativo.
- O Stop hook executa o script mas a saída WARN aparece a cada Stop sem ser silenciada.

**Impacto positivo (se corrigido):** padroniza linguagem de outputs do scanner; reduz fadiga de notificação no Stop hook; deixa claro o que esperar do fix.

**Impacto negativo (se mantido):** usuário vê a mesma WARN a cada Stop e ignora; comportamento aprende ruído.

**Sugestão:** padronizar o título como `ACTION SUGGESTED — duplicate skill loads` (ou suprimir WARN no `--quiet`); incluir template de fix:

```
Suggested fix:
  Edit <file>, find the duplicate `<skill-path>` reference, and remove the
  redundant occurrence (keep the first; the second is harmless but inflates tokens).
```

---

## 7. `ref-claude-md-grew-to-544-lines-largest-mono-file-in-repo`

**Severidade:** 🟡 Média — anti-pattern de "regras inflando ao invés de fragmentando"

**Detecção:** `wc -l CLAUDE.md` = **544 linhas** (em 2026-05-06 era ~330; +65% em 7 dias). Crescimento por categoria nos últimos commits:

| Commit | Categoria adicionada | Linhas adicionadas (estim.) |
|--------|----------------------|------------------------------|
| `7977977` | docs/, commands table, authoring rules | ~50 |
| `09c00ca` | Package exclusions table 14-row + exceptions | ~30 |
| `7bc755d` | Plan Gate enforcement notes | ~20 |
| `f6f5d55`, `5d5ff39` | preferences.json schema (12 fields + table) | ~40 |
| Outros | — | ~50 |

Antigo fingerprint `token-claude-md-monolithic-load-every-session` (2026-05-10, pendente) propunha fragmentar em `.claude-md/*`. Este novo escopo quantifica o **crescimento** absoluto e propõe extração específica.

**Impacto positivo (se corrigido):** carregamento de CLAUDE.md (loaded em todo session-start) cai de ~10.000 tokens para ~3.000-4.000; sub-arquivos como `CLAUDE.md/preferences.md`, `CLAUDE.md/commands.md`, `CLAUDE.md/notifications.md` ficam navegáveis.

**Impacto negativo (se mantido):** cada novo audit cycle adiciona ~30-50 linhas; CLAUDE.md vira o equivalente a CLAUDE-monorepo; em 30 dias projetará para ~800 linhas.

**Sugestão:** criar `.claude-md/` com índice em CLAUDE.md raiz:

```markdown
# CLAUDE.md (índice)
Authoring → see CLAUDE-md/authoring.md
Memory system → see CLAUDE-md/memory.md
Notifications → see CLAUDE-md/notifications.md
Preferences → see CLAUDE-md/preferences.md
…
```

Carregar sub-arquivo apenas quando agente precisar daquela seção específica.

---

## 8. `ref-pt-br-translation-of-extracted-docs-not-validated-by-section-count-anymore`

**Severidade:** 🟡 Média — sub-escopo de `token-readme-228-each-pos-extraction-but-ci-sync-still-line-based` (✅ Executed em 2026-05-13)

**Detecção:** Após commit `aa69ac4` + `ef21af2`, o CI sync check agora compara **contagem de `^## ` headers** entre EN e pt-BR. Porém, o check só examina:

```
check_pair README.md README.pt-BR.md
check_pair docs/agents.md docs/agents.pt-BR.md
check_pair docs/installation.md docs/installation.pt-BR.md
```

Limitação: **section-count match ignora drift de conteúdo dentro da mesma seção**. Se EN ganhar 50 linhas em `## Setup` e pt-BR ficar igual, o check passa (mesmo número de `##`). O fallback de `50% line-count threshold` é genérico demais.

**Impacto positivo (se corrigido):** detecta drift de conteúdo, não só de estrutura.

**Impacto negativo (se mantido):** pt-BR pode ficar permanentemente desatualizado dentro de seções existentes; usuários brasileiros leem README desatualizado.

**Sugestão:** estender check com tolerância por seção: para cada par de `^## ` headers, comparar line-count daquela seção entre EN e pt-BR. Tolerância: 30%. Exemplo:

```bash
# Para cada header EN, extrair conteúdo entre esse header e o próximo
# Comparar wc -l do bloco com o mesmo header em pt-BR
```

Alternativa mais leve: hash dos primeiros 20 caracteres de cada parágrafo (drift estrutural).

---

## 9. `ref-foundational-rule-setup-assistant-shrunk-to-7-lines-after-suggestion-to-grow-it`

**Severidade:** 🟡 Média — regressão silenciosa (oposto ao sugerido)

**Detecção:** Em 2026-05-12, o fingerprint `agent-setup-assistant-foundational-rule-only-10-lines-undersized` recomendava **crescer** a Foundational Rule de setup-assistant para alinhar com p50 (22 linhas). Em 2026-05-13:

```
$ awk '/^## Foundational/{flag=1} flag; /^## [A-Z]/ && !/Foundational/{if(flag){flag=0}}' agents/setup-assistant.md | wc -l
7
```

Encolheu de **10 → 7 linhas** (-30%). Conteúdo atual:

```
## Foundational Rule

Load `skills/shared/project-context/SKILL.md`. After loading, also check `.claude/settings.json` and `.agents/`. Apply `skills/shared/token-efficiency/SKILL.md` — prefer `grep`/`find`/`head` over full reads; never read `docs/installation.md` or `docs/agents.md`.

**All output must be written in English. Before any non-trivial step, present a plan using `templates/plan-template.md` and wait for approval.**
```

A redução pode ser **proposital** (delegação para `project-context`), mas viola CLAUDE.md linha 122: _"Every agent must include: **Foundational Rule** (load context first) + **Immutability Warning**"_ — pois o **Immutability Warning** (rule sobre `.dev-team-agents/` ser substituído na update) **não está mais presente** na seção Foundational do setup-assistant.

**Impacto positivo (se corrigido):** restaura paridade com a regra de CLAUDE.md; setup-assistant é o agente mais sensível à modificação de `.dev-team-agents/` (ele é o setup_!_).

**Impacto negativo (se mantido):** setup-assistant pode editar arquivos do próprio package sem warning; FIRST_RUN flow pode introduzir mutações que serão sobrescritas no próximo update.

**Sugestão:** adicionar Immutability Warning ao Foundational Rule do setup-assistant (mesmo padrão dos outros 16 agents); ou documentar a exceção em CLAUDE.md.

---

## 10. `ref-rollback-script-no-target-version-format-validation`

**Severidade:** 🟡 Média

**Detecção:** `cat scripts/rollback.sh` aceita qualquer string como argumento de versão:

```bash
if [ -n "${1:-}" ]; then
    TARGET="$1"
else
    …
fi
```

Sem validação que `$TARGET` matches `^v[0-9]+\.[0-9]+\.[0-9]+$`. Argumentos inválidos como `bash rollback.sh main` ou `bash rollback.sh latest` (que existem em `update.sh`) silenciosamente vão para o fluxo de download, retornam 404, e o usuário fica confuso.

**Impacto positivo (se corrigido):** mensagem de erro clara antes da chamada de rede; consistência com `update.sh` que aceita explicitamente `latest|vX.Y.Z`.

**Impacto negativo (se mantido):** UX ruim em cenário de incidente (rollback é usado em pressão).

**Sugestão:** após o `if [ -n "${1:-}" ]`, adicionar:

```bash
if [[ ! "$TARGET" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "✗ Invalid version format: '$TARGET'" >&2
    echo "  Expected: vX.Y.Z (e.g., v1.2.3)" >&2
    echo "  See: https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/releases" >&2
    exit 1
fi
```

---

## Resumo

| Prioridade | Quantidade |
|-----------|-----------|
| 🟠 Alta | 2 (`tester-misses-mobile`, `size-limits-warn-only-permanent`) |
| 🟡 Média | 8 |

**Padrões emergentes desta passada:**

- **Drift entre tabela CLAUDE.md e implementação real** continua sendo a categoria mais frequente (3 dos 10 fingerprints: `tester-misses-mobile`, `update-command-still-claims-two-scripts`, `workflow-mobile-shortcut-missing`).
- **Regressões pós-implementação** começam a aparecer: `setup-assistant` Foundational encolheu em vez de crescer; `references/` resolveu 7 skills mas comments-policy ainda eager-loaded.
- **Scripts órfãos** (não wireados) seguem sendo problema: `validate-commit-msg.sh` é o novo `check-updates.sh` (criado, documentado, mas nunca chamado pelo fluxo principal).
