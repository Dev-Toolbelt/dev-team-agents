# Auditoria Guardian — 2026-05-19 (décima quarta passada)

> Modo Guardian: cruzamento de marcações ✅ Executed e reaberturas pendentes contra o
> estado real do repositório (`git log` + leitura de arquivos), antes de gerar qualquer
> sugestão nova. Objetivo: confirmar que o que está marcado como feito **realmente foi
> feito**, e marcar cada item como **feito / parcialmente feito / não feito**.

---

## Resumo Executivo

| Métrica | Valor |
|---------|-------|
| Janela auditada | 2026-05-18 (geração do último relatório) → 2026-05-19 |
| Commits na janela | **0** (último commit: `9f1826d`, 2026-05-18 21:41) |
| Throughput da janela | **0%** — nenhum fingerprint pendente foi endereçado |
| Reaberturas de 2026-05-18 reverificadas | 3 → **3 ainda não feitas** |
| Fingerprints HIGH de 2026-05-18 reverificados | 6 amostrados → **6 ainda pendentes** |
| Nova discrepância Guardian encontrada | 1 (`size-limits` marcado ✅ mas problema persiste) |
| Falsos positivos descartados nesta passada | 1 (sync README.pt-BR de telemetria) |

**Veredito:** repositório **congelado** desde a última geração de relatório. Como não houve
nenhum commit na janela, o estado dos arquivos é idêntico ao que a auditoria de 2026-05-18
observou. Consequentemente, **todas as reaberturas e pendências HIGH continuam válidas** e o
foco do dia 2026-05-19 é (a) confirmar a estagnação e (b) levantar **ângulos novos** ainda
não fingerprintados — já que a superfície de "drift por commit" não existe hoje.

---

## 1. Verificação das 3 reaberturas recomendadas em 2026-05-18

A auditoria de 2026-05-18 recomendou reabrir 3 itens como ⚠️ Partial. Reverificados arquivo a arquivo:

| # | Item | Status verificado | Evidência |
|---|------|-------------------|-----------|
| 1 | devops-specialist body ainda stack-prescriptive | 🔴 **NÃO FEITO** | `agents/devops-specialist.md:140` (`Single EC2/VPS + Docker Compose`), `:143` (`não necessariamente Kubernetes`), `:151` (`Don't use Kubernetes when Docker Compose works`), `:154` (`service mesh when Nginx`), `:156` (`Datadog, Grafana Cloud … CloudWatch … Prometheus`) — seções "Decision Framework" e "Anti-Overengineering Rules" intactas |
| 2 | iOS/Android skills rasas demais | 🔴 **NÃO FEITO** | `skills/mobile/ios/SKILL.md` = **33 linhas**, `skills/mobile/android/SKILL.md` = **35 linhas** (vs `ios-hig` 218, `material-design` 221) — inalteradas |
| 3 | design-patterns lazy-load gate ausente | 🟡 **PARCIAL (inalterado)** | `references/` extraído (✅), mas `backend-developer.md:212` e `software-architect.md:29-30` ainda carregam o `SKILL.md` inteiro (152 linhas) em vez de `references/composition-root.md`; gate condicional continua ausente |

**Conclusão:** as 3 reaberturas permanecem com o **mesmo status** registrado em 2026-05-18. Devem
continuar marcadas como ⚠️ Partial / 🔴 no índice.

---

## 2. Reverificação de pendências HIGH de 2026-05-18 (amostra)

| Fingerprint (2026-05-18) | Status verificado | Evidência atual |
|--------------------------|-------------------|-----------------|
| `auto-docs-rule-violated-changelog-unreleased-missing-7-features` | 🔴 **NÃO FEITO** | `CHANGELOG.md` `## [Unreleased]` não cita telemetria, PRIVACY.md, `helpers/`, skills iOS/Android, stack-detection wiring, workflow-detection nem archive-index.sh |
| `ref-helpers-archive-index-script-shipped-but-not-hooked` | 🔴 **NÃO FEITO** | `grep -rln archive-index` retorna apenas o próprio arquivo; nenhum hook/CI/`update.sh` o invoca |
| `token-telemetry-helper-289-lines … duplicação _telemetry_enabled em 3 scripts` | 🔴 **NÃO FEITO** | `_telemetry_enabled` ainda presente em `scripts/hooks/pre-tool-use/02-telemetry.sh`, `scripts/hooks/stop/05-telemetry.sh` e `scripts/helpers/telemetry-send.sh` |
| `flow-workflow-detection-skill-only-loaded-by-software-architect` | 🔴 **NÃO FEITO** | skill segue carregada por 1 agente apenas |
| `ref-claude-md-file-structure-omits-helpers-and-privacy-and-claude-md-folder` | 🔴 **NÃO FEITO** | bloco "File Structure" (CLAUDE.md) ainda lista `scripts/` sem `helpers/`, `scripts/helpers/`, `PRIVACY.md` ou `CLAUDE-md/` |
| `ref-templates-backlog-template-md-orphan` | 🔴 **NÃO FEITO** | `helpers/orphan-template-scan.sh` ainda reporta `templates/backlog-template.md` órfão |

Amostra de 6/32 fingerprints de 2026-05-18: **0 endereçados**. Coerente com throughput 0% (sem commits).

---

## 3. Nova discrepância Guardian encontrada nesta passada

**`ref-size-limits-warn-only-permanent-tech-debt-11-agents-violating`** está marcado **✅ Executed: 2026-05-15**, porém o problema de fundo **persiste e piorou em granularidade**:

- `helpers/size-limits.sh` continua sendo invocado em CI apenas como `--warn-only` (`.github/workflows/ci.yml:28`) — nunca bloqueia.
- `bash helpers/size-limits.sh` reporta hoje **9 agentes** acima do cap de 200 linhas (53% dos 17): backend-developer 261, backend-reviewer 204, code-reviewer 228, devops-specialist 237, frontend-developer 232, frontend-test-specialist 262, qa-specialist 208, security-specialist 234, setup-assistant 239.
- O "Executed" de 2026-05-15 refletiu apenas a **adição da flag `--warn-only`**, não a resolução da dívida (sem cronograma de enforce, sem gate bloqueante).

**Recomendação Guardian:** corrigir a marcação de `ref-size-limits-warn-only-permanent-tech-debt-11-agents-violating` para **⚠️ Partial** — a ferramenta existe e roda, mas a regra "Max ~200 lines" (CLAUDE.md) segue **sem enforcement**. O sub-escopo pendente (enforcement bloqueante + paridade no Stop hook) é reproposto hoje como `flow-size-limits-sh-ci-only-warn-only-not-in-stop-dispatcher-...` em [02-fluxos-e-workflows.md](02-fluxos-e-workflows.md).

---

## 4. Falso positivo descartado (disciplina Guardian)

Durante a coleta, um candidato a achado novo — "README.pt-BR fora de sincronia na seção de
telemetria" (EN tem 2 menções a *telemetry/PostHog*, PT-BR tem 1) — foi **verificado e
descartado**: o cabeçalho PT-BR está corretamente traduzido para `## Telemetria Anônima`
(`README.pt-BR.md:217`) e a seção tem corpo completo e equivalente, incluindo o bloco
`{ "telemetry": false }` e o link para `PRIVACY.md`. Ambos os arquivos têm **14 seções `##`**.
A diferença de contagem era apenas artefato do grep case-insensitive não casar "Telemetria".
Registrado aqui para evitar que passadas futuras o re-levantem como problema.

---

## 5. Achados estruturais novos desta passada (detalhados nos relatórios temáticos)

Como não há drift por commit, os ângulos novos vêm de leitura estrutural mais profunda:

1. **Contradição factual em CLAUDE.md:183** — o parágrafo "Code Reviewer roles" diz que o `code-reviewer` delega a `backend-test-specialist`/`frontend-test-specialist`, mas o agente real (`code-reviewer.md:21-22`) roteia para `backend-reviewer`/`frontend-reviewer` via `review-router`. → [01](01-referencias-e-consistencia.md)
2. **Colisão de nomes "helpers"** — `helpers/` (raiz, dev-only, removido no install) vs `scripts/helpers/` (runtime, enviado ao usuário). → [01](01-referencias-e-consistencia.md)
3. **Prefixo `02b-` não documentado** na tabela de convenção de sub-scripts do Stop. → [01](01-referencias-e-consistencia.md)
4. **`size-limits.sh` sem gate bloqueante nem paridade no Stop.** → [02](02-fluxos-e-workflows.md)
5. **Gate de sync README só compara contagem de seções e 50% de linhas, não conteúdo.** → [02](02-fluxos-e-workflows.md)
6. **Stop dispatcher faz glob `*.sh` sem allowlist** — qualquer arquivo solto executa. → [02](02-fluxos-e-workflows.md)
7. **frontend-test-specialist embute receitas React/Vue no corpo** (violação stack-agnostic). → [03](03-agentes-e-skills.md)
8. **backend-developer embute regras realtime Supabase/Postgres no corpo** apesar de carregar a skill `realtime`. → [03](03-agentes-e-skills.md)
9. **_index.md em 647 linhas** (8ª passada de crescimento; archive-index.sh existe mas não dispara). → [04](04-economia-tokens.md)

---

## Apêndice — comandos de verificação executados

```
git log --since="2026-05-17 00:00" --pretty=...        # 0 commits após 2026-05-18 21:41
bash helpers/orphan-skill-scan.sh                       # 2 duplicate loads (já fingerprintados)
bash helpers/orphan-template-scan.sh                    # backlog-template.md órfão (pendente)
bash helpers/agent-lint.sh                              # clean ✓
bash helpers/check-fingerprint-uniqueness.sh           # slugs únicos ✓
bash helpers/size-limits.sh                            # 9 agentes > 200 linhas
wc -l docs/reports/_index.md                           # 647
```
