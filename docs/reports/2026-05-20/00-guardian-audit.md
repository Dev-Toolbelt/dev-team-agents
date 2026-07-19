# Auditoria Guardian — 2026-05-20 (décima quinta passada)

> Modo Guardian: cruzamento de marcações ✅ Executed e reaberturas pendentes contra o
> estado real do repositório (`git log` + leitura de arquivos), **antes** de gerar qualquer
> sugestão nova. Objetivo: confirmar que o que está marcado como feito **realmente foi
> feito**, e marcar cada item como **feito / parcialmente feito / não feito**.

---

## Resumo Executivo

| Métrica | Valor |
|---------|-------|
| Janela auditada | 2026-05-19 (geração do último relatório) → 2026-05-20 |
| Commits na janela | **0** (último commit: `9f1826d`, 2026-05-18 21:41) |
| Throughput da janela | **0%** — nenhum fingerprint pendente foi endereçado |
| Reaberturas de 2026-05-18 reverificadas | 3 → **3 ainda não feitas** (status idêntico) |
| Pendências HIGH amostradas de 2026-05-18/19 | 6 → **6 ainda pendentes** |
| Nova discrepância Guardian encontrada | 1 (`docs/agents.md` coluna Model errada em 2 agentes) |
| Falsos positivos descartados nesta passada | 1 (`adr-template.md` "órfão" — usado por `new-adr.sh`) |
| Estado dos relatórios diários | 2026-05-18, 2026-05-19 e edições do `_index.md` **não commitados** (working tree) |

**Veredito:** repositório **congelado** há ~2 dias (nenhum commit desde `9f1826d`). O estado dos
arquivos é byte-a-byte idêntico ao observado nas auditorias de 2026-05-18 e 2026-05-19.
Consequentemente, **todas as reaberturas e pendências HIGH continuam válidas**. Como não há "drift
por commit" para auditar, o foco do dia 2026-05-20 é (a) confirmar a estagnação, (b) reverificar as
3 reaberturas arquivo a arquivo, e (c) levantar **ângulos novos por leitura estrutural** ainda não
fingerprintados.

> **Observação operacional (contexto, não defeito do projeto):** o último commit que persistiu
> relatórios de auditoria foi `91abe8e` (2026-05-18 14:36, "add 2026-05-17 guardian audit"). As pastas
> `docs/reports/2026-05-18/`, `docs/reports/2026-05-19/` e as edições acumuladas do `_index.md`
> aparecem como **untracked / modified** no `git status`. Ou seja: a própria esteira de auditoria
> deixou de ser commitada. Isso explica por que `git log` enxerga "0 commits" mesmo havendo trabalho
> de relatório sendo gerado, e implica que `archive-index.sh` (que opera sobre o arquivo em disco)
> **nunca verá** o crescimento refletido em histórico. Não é um defeito do código do projeto — é um
> efeito de a esteira rodar sem etapa de commit — mas é relevante para interpretar o "throughput 0%".

---

## 1. Verificação das 3 reaberturas recomendadas em 2026-05-18 (reverificadas arquivo a arquivo)

| # | Item | Status verificado (2026-05-20) | Evidência atual |
|---|------|-------------------------------|-----------------|
| 1 | `devops-specialist` body ainda stack-prescriptive | 🔴 **NÃO FEITO** | `agents/devops-specialist.md:140` (`Single EC2/VPS + Docker Compose`), `:143` (`not necessarily Kubernetes`), `:151` (`Don't use Kubernetes when Docker Compose works`), `:154` (`service mesh when Nginx`), `:156` (`Datadog, Grafana Cloud … CloudWatch … Prometheus`) — seções "Decision Framework" e "Anti-Overengineering Rules" intactas |
| 2 | skills iOS/Android rasas demais | 🔴 **NÃO FEITO** | `skills/mobile/ios/SKILL.md` = **33 linhas**, `skills/mobile/android/SKILL.md` = **35 linhas** (vs `ios-hig` 218, `material-design` 221) — inalteradas |
| 3 | design-patterns lazy-load gate ausente | 🟡 **PARCIAL (inalterado)** | `references/composition-root.md` existe, mas **nenhum agente o carrega**: `backend-developer.md:212`, `code-reviewer.md:95`, `frontend-developer.md:145` e `software-architect.md:29-30` ainda puxam o `SKILL.md` inteiro. Gate condicional continua ausente |

**Conclusão:** as 3 reaberturas permanecem com o **mesmo status** registrado em 2026-05-18/19. Devem
continuar marcadas como ⚠️ Partial / 🔴 no índice.

---

## 2. Reverificação de pendências HIGH (amostra de 2026-05-18 e 2026-05-19)

| Fingerprint | Status verificado | Evidência atual |
|-------------|-------------------|-----------------|
| `auto-docs-rule-violated-changelog-unreleased-missing-7-features` | 🔴 **NÃO FEITO** | `## [Unreleased]` segue sem telemetria, PRIVACY.md, `helpers/`, skills iOS/Android, stack-detection wiring, workflow-detection nem archive-index.sh |
| `ref-helpers-archive-index-script-shipped-but-not-hooked` | 🔴 **NÃO FEITO** | `grep -rln archive-index` → só o próprio arquivo; nenhum hook/CI/`update.sh` o invoca |
| `ref-claude-md-file-structure-omits-helpers-and-privacy-and-claude-md-folder` | 🔴 **NÃO FEITO** | bloco "File Structure" ainda lista `scripts/` sem `helpers/`, `scripts/helpers/`, `PRIVACY.md` ou `CLAUDE-md/` |
| `ref-templates-backlog-template-md-orphan` | 🔴 **NÃO FEITO** | `helpers/orphan-template-scan.sh` ainda reporta `templates/backlog-template.md` órfão |
| `flow-size-limits-sh-ci-only-warn-only-not-in-stop-dispatcher-...` | 🔴 **NÃO FEITO** | `ci.yml:28` segue `--warn-only`; sem `03b-size-limits.sh` no Stop; `bash helpers/size-limits.sh` reporta **9/17 agentes** > 200 linhas |
| `flow-stop-dispatcher-globs-all-sh-no-allowlist-...` | 🔴 **NÃO FEITO** | `scripts/hooks/stop.sh:32` ainda `for script in "$HOOKS_DIR"/*.sh`. **Nota Guardian:** `scripts/hooks/pre-tool-use.sh:11` tem o **mesmo** glob não guardado — o problema é dos dois dispatchers, não só do Stop |

Amostra de 6 fingerprints: **0 endereçados**. Coerente com throughput 0% (sem commits).

---

## 3. Saída das ferramentas de verificação (helpers)

```
bash helpers/agent-lint.sh                    → clean ✓
bash helpers/size-limits.sh                   → 9 agentes > 200 linhas (idêntico a 2026-05-19)
bash helpers/orphan-skill-scan.sh             → 2 duplicate loads (ui-ux-designer, commands/update.md) — persistem
bash helpers/orphan-template-scan.sh          → backlog-template.md órfão (pendente)
bash helpers/check-fingerprint-uniqueness.sh  → slugs únicos ✓
wc -l docs/reports/_index.md                  → 676 (working tree, não commitado)
```

`size-limits` (9 agentes > cap): backend-developer 261, frontend-test-specialist 262, setup-assistant
239, devops-specialist 237, security-specialist 234, frontend-developer 232, code-reviewer 228,
qa-specialist 208, backend-reviewer 204. **Confirma** o status ⚠️ Partial recomendado em 2026-05-19
para `ref-size-limits-warn-only-permanent-tech-debt-11-agents-violating` (ferramenta existe e roda,
mas a regra "Max ~200 lines" segue **sem enforcement bloqueante**).

---

## 4. Nova discrepância Guardian encontrada nesta passada

**`docs/agents.md` (a "canonical agent reference" do CLAUDE.md) tem a coluna `Model` errada em 2 dos 17 agentes:**

| Agente | `docs/agents.md` diz | Frontmatter real | Status |
|--------|----------------------|------------------|--------|
| `technical-writer` | **Haiku** (`docs/agents.md:26`) | `claude-sonnet-4-6` | ❌ ERRADO |
| `setup-assistant` | **Sonnet** (`docs/agents.md:27`) | `claude-opus-4-7` | ❌ ERRADO |

Além de errado, o caso `technical-writer` **contradiz a própria CLAUDE.md**, que afirma na seção
Authoring Standards: *"Haiku is available for **future** micro-agents… add it back when a concrete
candidate emerges."* Hoje **nenhum** agente usa Haiku (`grep '^model:' agents/*.md` → 4 Opus + 13
Sonnet, 0 Haiku), mas a referência canônica anuncia um agente Haiku que não existe. Detalhado e
proposto como sugestão nova em [01-referencias-e-consistencia.md](01-referencias-e-consistencia.md) (R1).

---

## 5. Falso positivo descartado (disciplina Guardian)

Durante a coleta, `adr-template.md` apareceu como "referenciado em 0 arquivos `.md`" — candidato a
órfão. **Verificado e descartado:** o template é lido pelo script `scripts/new-adr.sh` (um `.sh`, não
um `.md`), por isso não aparece em grep restrito a markdown e por isso `orphan-template-scan.sh` **não**
o reporta (o scanner cobre `.sh` também). `adr-template.md` **não é órfão**. Registrado aqui para que
passadas futuras não o re-levantem.

---

## 6. Ângulos novos desta passada (detalhados nos relatórios temáticos)

Como não há drift por commit, os ângulos vêm de leitura estrutural mais profunda:

1. **`docs/agents.md` coluna Model errada** em `technical-writer` (Haiku→Sonnet) e `setup-assistant` (Sonnet→Opus). → [01](01-referencias-e-consistencia.md)
2. **Diretiva de carga do `comments-policy`** (com o parêntese condicional verbatim) **copiada em 8 agentes** — sem fonte única. → [01](01-referencias-e-consistencia.md)
3. **File Structure do CLAUDE.md** enumera `scripts/` omitindo 3 scripts de runtime enviados (`check-updates.sh`, `rollback.sh`, `validate-commit-msg.sh`). → [01](01-referencias-e-consistencia.md)
4. **CI `orphan-skill-scan` com `continue-on-error: true`** — nunca bloqueia; 2 warnings de peso parados há dias. → [02](02-fluxos-e-workflows.md)
5. **Gate de sync de README com 3 pares hardcoded** — novos pares `*.pt-BR.md` não são descobertos. → [02](02-fluxos-e-workflows.md)
6. **CI dispara em `push` E `pull_request`** ambos `["**"]** — toda branch de PR roda CI duas vezes. → [02](02-fluxos-e-workflows.md)
7. **`backend-developer` "Integration Awareness"** duplica "Critical rules" inline para 7 integrações (Supabase/GoTrue/JWT/Kong/Realtime/SonarQube/Async) — viola stack-agnostic de forma sistêmica. → [03](03-agentes-e-skills.md)
8. **`frontend-developer` "Security"** hardcoda APIs de framework no corpo (`dangerouslySetInnerHTML`/`v-html`, `VITE_*`/`NEXT_PUBLIC_*`). → [03](03-agentes-e-skills.md)
9. **`database-specialist` description** enumera ~12 engines + DBs gerenciados de 3 nuvens — superfície de identidade stack-prescriptive. → [03](03-agentes-e-skills.md)
10. **Regras inline do "Integration Awareness"** são **eager** (~70-80 linhas/spawn) e anulam o desenho lazy de detecção. → [04](04-economia-tokens.md)
11. **Dedup lê o `_index.md` inteiro (676 linhas)** quando só precisa da lista de slugs. → [04](04-economia-tokens.md)
12. **Diretiva `comments-policy` duplicada em 8 agentes** vira multiplicador de tokens em fluxos multi-agente. → [04](04-economia-tokens.md)

---

## Apêndice — comandos de verificação executados

```
git log -1 --pretty=...                         # 9f1826d, 2026-05-18 21:41 (último commit)
git log --since="2026-05-19 00:00" --oneline    # 0 commits na janela
git status --short                              # _index.md M; 2026-05-18/, 2026-05-19/ untracked
bash helpers/agent-lint.sh                       # clean
bash helpers/size-limits.sh                      # 9 agentes > 200 linhas
bash helpers/orphan-skill-scan.sh                # 2 duplicate loads
bash helpers/orphan-template-scan.sh             # backlog-template.md órfão
bash helpers/check-fingerprint-uniqueness.sh     # slugs únicos
grep '^model:' agents/*.md | sort | uniq -c      # 4 opus + 13 sonnet, 0 haiku
sed -n '26,27p' docs/agents.md                   # technical-writer=Haiku, setup-assistant=Sonnet (errados)
```
