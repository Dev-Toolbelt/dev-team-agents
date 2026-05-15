# Relatório - Referências e Consistência - 2026-05-14

**Data:** 2026-05-14 — Nona passada (9ª) — 10 sugestões originais

Foco do dia: drift entre tabela CLAUDE.md e implementação real (mobile-developer em commands `/devteam:fix` e `/devteam:review`), regressão acumulativa de CLAUDE.md (557 linhas), modelo Haiku declarado e nunca usado, skills sub-utilizadas, novos sub-escopos quantificados de pendências históricas.

---

### 🔴 1. Drift `/devteam:fix` declara `mobile-developer¹` mas `commands/fix.md` não spawneia

**Fingerprint:** `ref-fix-command-misses-mobile-developer-spawn-vs-claude-md-table`

**Evidência:** `CLAUDE.md` linha 188 declara para `/devteam:fix`: `backend-developer¹ + frontend-developer¹ + mobile-developer¹ → test-specialist¹`. Verificação em `commands/fix.md` (26 linhas, fact-finding §4.2): Phase 1 spawneia somente `backend-developer` e `frontend-developer` — `mobile-developer` ausente. Sister fingerprint do já registrado `ref-tester-command-misses-mobile-developer-spawn-vs-claude-md-table` (2026-05-13, ainda pendente — vide Guardian §1).

**Por quê importa:** Um usuário que rode `/devteam:fix` para um bug em React Native lê na tabela que `mobile-developer` será spawneado, mas o fluxo silenciosamente cai em backend/frontend. Promessa pública não cumprida.

**Impacto positivo da correção:** Wiring real de mobile em fluxo de bug-fix; alinhamento entre documentação declarativa e execução; reduz dívida arquitetural mobile (4ª passada consecutiva).

**Impacto negativo / risco:** Adicionar spawn requer detection rule "is mobile bug?" em `commands/fix.md`; sem heurística clara o spawn pode disparar em contextos incorretos.

**Sugestão concreta:** Em `commands/fix.md` Phase 1, adicionar bloco condicional `mobile-developer` quando paths `ios/`, `android/`, `*.swift`, `*.kt`, `App.tsx` (Expo/RN) ou `pubspec.yaml` (Flutter) detectados no diff/working tree.

---

### 🔴 2. Drift `/devteam:review` declara `mobile-developer¹` mas `commands/review.md` não spawneia

**Fingerprint:** `ref-review-command-misses-mobile-developer-spawn-vs-claude-md-table`

**Evidência:** `CLAUDE.md` linha 184 declara para `/devteam:review`: `code-reviewer + software-architect + security-specialist + database¹ + mobile-developer¹`. `commands/review.md` (17 linhas, fact-finding §4.2): spawneia code-reviewer + software-architect + security-specialist + database-specialist¹ — sem `mobile-developer`. Mesmo padrão de gap do tester e fix.

**Por quê importa:** Reviews de PRs mobile não acionam o agente especialista; defeitos específicos de plataforma (memory pressure iOS, ANR Android, lifecycle Activity/Fragment) escapam.

**Impacto positivo da correção:** Code review mobile com mesma rigorosidade que backend/frontend; consistência cross-stack.

**Impacto negativo / risco:** Spawn extra em PRs não-mobile se detection rule for fraca.

**Sugestão concreta:** Adicionar `mobile-developer¹` como spawn condicional em `commands/review.md` com gating idêntico ao item #1.

---

### 🔴 3. Regressão acumulativa: CLAUDE.md cresceu para 557 linhas (+13 vs 544 reportadas em 2026-05-13)

**Fingerprint:** `ref-claude-md-grew-to-557-lines-after-quiz-first-addition`

**Evidência:** `wc -l CLAUDE.md` = **557 linhas** (fact-finding §4 + §7). Crescimento +13 em 24h por commit `d05242a` (interaction-patterns), `ac6af24`, `ebdcb3a`. Trajetória: 330 → 544 → 557 (+69% em 8 dias). Sub-escopo do pendente `ref-claude-md-grew-to-544-lines-largest-mono-file-in-repo` (2026-05-13).

**Por quê importa:** CLAUDE.md é carregado em todo session-start e em todo spawn de agente; cada linha adicional multiplica por 7 (spawns/sessão típica). Alvo móvel: enquanto o fingerprint pendente não é endereçado, novos features pioram a base.

**Impacto positivo da correção:** Estancar a regressão antes de fragmentar; cap explícito (~600 linhas) com warning de CI evitaria que cada feature consuma silenciosamente o orçamento.

**Impacto negativo / risco:** CI rígido pode bloquear melhoria genuína de documentação; precisa de override consciente.

**Sugestão concreta:** Adicionar check `wc -l CLAUDE.md` ao `scripts/size-limits.sh` com cap warning em 600 linhas e hard-fail em 700; abrir tracking issue para fragmentação em 3 fases conforme proposta de 2026-05-13.

---

### 🟡 4. Modelo Haiku declarado em CLAUDE.md mas zero agents o usam

**Fingerprint:** `ref-haiku-model-declared-in-claude-md-but-zero-agents-use-it`

**Evidência:** `CLAUDE.md` linha 120 declara: `Model assignment: claude-opus-4-7 (decision-making), claude-sonnet-4-6 (execution), claude-haiku-4-5-20251001 (structured output)`. Fact-finding §5.1: `grep -h "^model:" agents/*.md | sort | uniq -c` → 4 Opus + 13 Sonnet + **0 Haiku**. Authoring rule sem implementação correspondente.

**Por quê importa:** Regra documentada sem owner cria falsa expectativa de cobertura. Quando alguém autorar um novo agente "structured output" (ex.: changelog-formatter), não há referência canônica.

**Impacto positivo da correção:** Ou (a) remover Haiku da regra se decisão consciente, ou (b) identificar 1-2 candidatos legítimos (ex.: `technical-writer` para release notes, antes 🟢 Resolved em 2026-05-12 mas com possibilidade de variant Haiku para sub-task).

**Impacto negativo / risco:** Forçar uso de Haiku sem validar qualidade pode degradar outputs.

**Sugestão concreta:** Decidir explicitamente entre as duas opções acima e atualizar CLAUDE.md L120; se manter, criar `agents/release-formatter.md` (Haiku) ou similar com escopo estrito.

---

### 🟡 5. Skill `security-checklist` zero referências e fora do allowlist user-invocable

**Fingerprint:** `ref-security-checklist-skill-zero-references-not-user-invocable`

**Evidência:** Fact-finding §6.2: `skills/security/security-checklist/SKILL.md` aparece com 0 referências em `agents/`, `commands/`, `workflows/`. Não está registrada na tabela "User-Invocable Skills" da CLAUDE.md (linhas 168-176). Diferente do antigo `skill-security-only-checklist` (2026-05-09) que apenas observava categoria thin — este é o caso isolado de skill órfã efetiva.

**Por quê importa:** Conteúdo investido sem consumo; orphan-skill-scan detecta mas não escala para WARN automático nesta categoria. `security-specialist` (Opus, 234 linhas) deveria ser o consumidor natural.

**Impacto positivo da correção:** Wireamento correto eleva qualidade de auditorias; ou exclusão limpa o repo de dead code.

**Impacto negativo / risco:** Adicionar load no security-specialist aumenta seu footprint (já 234 linhas).

**Sugestão concreta:** Adicionar `Load skills/security/security-checklist/SKILL.md` em `agents/security-specialist.md` Foundational Rule, seção "Skills carregadas para auditorias OWASP/CWE".

---

### 🟡 6. Skill `interaction-patterns` adicionada hoje mas só `commands/update.md` carrega

**Fingerprint:** `ref-interaction-patterns-skill-added-today-but-only-1-command-loaded`

**Evidência:** Commit `d05242a` (2026-05-14) cria `skills/shared/interaction-patterns/SKILL.md` (185 linhas). Commit `ba19882` aplica em `commands/update.md`. Fact-finding §9: nenhum outro arquivo carrega a skill. CLAUDE.md (Quiz-first Rule, ~L141): "All agents and commands must use the AskUserQuestion tool whenever asking the user a question with a finite set of reasonable answers".

**Por quê importa:** Regra mandatória declarada mas adoção em 1/28 commands e 0/17 agents. Se alguém autorar agente novo seguindo padrão atual de "(yes/no)" inline, não recebe lint warning.

**Impacto positivo da correção:** Adoção propaga AskUserQuestion para `setup-assistant`, `commands/adr.md`, `commands/commit.md`, `commands/pr.md` (locais com prompts conhecidos).

**Impacto negativo / risco:** Refactor abrangente; cada agent revisado é potencial regressão.

**Sugestão concreta:** Plano em fases — Fase 1: setup-assistant + 4 commands top de uso (`commit`, `pr`, `adr`, `update`); Fase 2: agents coding (refatorar prompts de worktree question); Fase 3: lint rule em `agent-lint.sh` que falha em literal `(yes/no)` ou `(y/n)`.

---

### 🟡 7. Tools frontmatter divergence: 4 patterns ainda sem ordem canônica definida

**Fingerprint:** `ref-tool-ordering-split-bash-glob-grep-vs-grep-glob-bash-canonical-order-still-undefined`

**Evidência:** Sub-escopo do pendente `ref-tools-frontmatter-ordering-divergence-reviewers-vs-coders` (2026-05-12). Fact-finding §5.2: 4 patterns observados — `Read, Grep, Glob, Bash` (3 reviewers); `Read, Grep, Glob, Bash, WebSearch` (security-specialist); `Read, Write, Edit, Bash, Glob, Grep` (11 write-capable); `Read, Write, Edit, Bash, Glob, Grep, WebSearch` (product-analyst, software-architect). `Bash` aparece antes de `Glob/Grep` em writers e depois em reviewers.

**Por quê importa:** Sem ordem canônica, refactors em massa via `sed` exigem regex complexo; `agent-lint.sh` (commit `72ff0ee`/2026-05-13) valida presença mas não ordem (Guardian 2026-05-13 confirma ⚠️ Partial).

**Impacto positivo da correção:** Permite migrações bulk simples; futuras adições de tool (ex.: WebFetch) são pos-fixadas previsíveis.

**Impacto negativo / risco:** Reordenação simultânea em 17 agents é commit ruidoso; risco zero funcional.

**Sugestão concreta:** Definir ordem canônica `Read, Write, Edit, Glob, Grep, Bash, WebSearch, WebFetch` em CLAUDE.md "Authoring Standards"; aplicar via `sed -i` em todos os 17 agents num único commit; estender `agent-lint.sh` para validar ordem.

---

### 🟡 8. Templates folder atingiu 4 arquivos — trigger de orphan-templates-scan ainda não implementado

**Fingerprint:** `ref-template-orphan-scan-still-missing-after-templates-folder-hit-4-files`

**Evidência:** `auto-no-orphan-templates-scan` (2026-05-08) foi adiado com nota "deferir até 3+ arquivos". Fact-finding §1.6: `templates/` agora tem **4 arquivos** (adr-template, backlog-template, plan-template, runbook-template). Trigger atingido, scan não implementado. Adicionalmente, `runbook-template.md` (79 linhas) está sem skill que o referencie (vide pendente `skill-templates-folder-grew-but-no-template-skill-wraps-them`).

**Por quê importa:** Template órfão é acumulação silenciosa; `runbook-template.md` é o caso atual.

**Impacto positivo da correção:** Detecção automática paralela ao orphan-skill-scan; permite políticas claras (template novo deve ser wireado em 1 skill ou agent).

**Impacto negativo / risco:** Falsos positivos para templates de uso humano (ADR é copiado manualmente, não loadeado).

**Sugestão concreta:** Estender `scripts/orphan-skill-scan.sh` ou criar `scripts/orphan-template-scan.sh` que faz `grep -l "templates/<arquivo>" agents/ skills/ commands/ workflows/ scripts/`; rodar como sub-script `02b-orphan-template-scan.sh` no Stop hook.

---

### 🟡 9. `validate-commit-msg.sh` redistribuído em `scripts/` mas ainda sem CI hook nem invocação por commit/pr

**Fingerprint:** `ref-validate-commit-msg-script-now-distributed-but-still-orphan-from-ci-and-commit-command`

**Evidência:** Sub-escopo de `ref-validate-commit-msg-script-orphaned-from-ci-and-commit-command` (2026-05-13, pendente). Commit `e5786b7` (2026-05-13) moveu o script de `scripts/hooks/` para `scripts/` (49 linhas — fact-finding §1.5). Distribuição feita; integração ausente. Guardian §`ref-validate...` confirma 0 hits em `.github/workflows/`, `commands/commit.md`, `commands/pr.md`.

**Por quê importa:** Quinta passada consecutiva detectando script criado e nunca wireado (mesmo padrão de `check-updates.sh` em 2026-05-08). A redistribuição apenas moveu o problema sem resolver.

**Impacto positivo da correção:** CI ou commit-msg hook valida mensagens antes de chegar à branch; commit command poderia auto-validar antes de chamar `git commit`.

**Impacto negativo / risco:** CI gating em commit messages é controverso para colaboradores externos.

**Sugestão concreta:** Mínimo viável — invocar `scripts/validate-commit-msg.sh "$MESSAGE"` em `commands/commit.md` Step antes de `git commit -m`; documentar como manual gate, não CI.

---

### 🟢 10. `commands/workflow-review.md` 11 linhas — assimétrico vs outros 7 workflow-* shortcuts (14 linhas cada)

**Fingerprint:** `ref-commands-workflow-review-only-11-lines-asymmetric-with-other-workflow-shortcuts`

**Evidência:** Fact-finding §1.2: `commands/workflow-bugfix.md`, `workflow-fullstack.md`, `workflow-inherited.md`, `workflow-maintenance.md`, `workflow-new.md`, `workflow-refactor.md`, `workflow-security-patch.md` — todos 14 linhas. `commands/workflow-review.md` é 11 linhas. Diferença de 3 linhas (sem PLAN GATE, conforme exception em CLAUDE.md ~L195 "commands that do NOT require Plan Gate").

**Por quê importa:** Diferença está documentada (review é read-only), mas a assimetria visual no diretório é confusa; quem autorar novo workflow shortcut pode copiar o errado como template.

**Impacto positivo da correção:** Adicionar comentário `<!-- read-only command — no Plan Gate per CLAUDE.md exception -->` torna a diferença explicit e evita "fix" indevido.

**Impacto negativo / risco:** Mudança puramente cosmética.

**Sugestão concreta:** Adicionar 2 linhas de comentário HTML no topo de `commands/workflow-review.md` explicando a exceção; padronizar em 13 linhas.

---

## Síntese — ordem de prioridade

1. **🔴 #1** — `ref-fix-command-misses-mobile-developer-spawn-vs-claude-md-table` (drift público)
2. **🔴 #2** — `ref-review-command-misses-mobile-developer-spawn-vs-claude-md-table` (drift público)
3. **🔴 #3** — `ref-claude-md-grew-to-557-lines-after-quiz-first-addition` (regressão silenciosa, 9 dias seguidos)
4. **🟡 #6** — `ref-interaction-patterns-skill-added-today-but-only-1-command-loaded` (regra nova sem adoção)
5. **🟡 #4** — `ref-haiku-model-declared-in-claude-md-but-zero-agents-use-it`
6. **🟡 #5** — `ref-security-checklist-skill-zero-references-not-user-invocable`
7. **🟡 #7** — `ref-tool-ordering-split-bash-glob-grep-vs-grep-glob-bash-canonical-order-still-undefined`
8. **🟡 #9** — `ref-validate-commit-msg-script-now-distributed-but-still-orphan-from-ci-and-commit-command` (5ª passada)
9. **🟡 #8** — `ref-template-orphan-scan-still-missing-after-templates-folder-hit-4-files`
10. **🟢 #10** — `ref-commands-workflow-review-only-11-lines-asymmetric-with-other-workflow-shortcuts`
