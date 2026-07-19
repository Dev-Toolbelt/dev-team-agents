# Relatório — Fluxos e Workflows

**Data:** 2026-05-26
**Janela auditada:** 2026-05-24 → 2026-05-26
**Foco:** sub-escopos refinados de fingerprints que estavam corretos só pela metade, ou contradições novas entre o que workflows prometem e o que executam.

---

## F1 — `workflows/refactor.md` ainda não tem o passo `session summary` no Workflow Closure — fingerprint de 2026-05-23 estava errado sobre `fullstack.md`

**Fingerprint:** `flow-workflow-refactor-md-closure-still-missing-session-summary-step-while-fingerprint-of-2026-05-23-was-misclassified-fullstack-md-actually-has-it-refactor-is-the-only-outlier`

**Severidade:** **MEDIUM**

**Evidência:**

```bash
$ grep -ciE "session.summary|session summary" workflows/*.md
3 workflows/bug-fix.md
2 workflows/design.md
1 workflows/fullstack.md       ← TEM (linha "Session summary written")
4 workflows/inherited-project.md
2 workflows/maintenance.md
2 workflows/mobile.md
2 workflows/new-project.md
1 workflows/refactor.md        ← linha solta dentro de seção "Recovery", NÃO no Closure
2 workflows/review.md
2 workflows/security-patch.md
```

Releitura de `workflows/refactor.md` (linhas 250-278): a única menção a "session summary" está em **prosa narrativa**, não na lista checkable de Workflow Closure. Comparado com `fullstack.md` linha 268 (`☐ Session summary written` — item explícito no checklist).

O fingerprint anterior `flow-session-summary-closure-step-present-in-eight-of-ten-workflows-but-absent-from-fullstack-and-refactor-highest-fanout` (2026-05-23) supôs incorretamente que **ambos** estavam fora. Auditoria de hoje confirma:

| Workflow | Tem checkbox `☐ Session summary written` no Workflow Closure? |
|---|---|
| `bug-fix.md` | ✅ |
| `design.md` | ✅ |
| `fullstack.md` | ✅ |
| `inherited-project.md` | ✅ |
| `maintenance.md` | ✅ |
| `mobile.md` | ✅ |
| `new-project.md` | ✅ |
| `refactor.md` | ❌ — só prosa, não checkbox |
| `review.md` | ✅ |
| `security-patch.md` | ✅ |

**9/10 conformes; refactor é o único outlier.**

**Impacto:**

- O workflow `refactor.md` é um dos 2 com mais sub-passos (278 linhas, 1ª no ranking de workflows). Justamente onde **mais decisões precisam ficar registradas** no `session-summary`, o passo não é cobrado no closure.
- Fluxo de `/devteam:refactor` termina sem prompt de session-summary; próxima sessão começa sem o registro do que foi decidido (race condition de memória entre agentes).

**Recomendação:**

Adicionar a linha `☐ Session summary written (Memory System rule)` à seção "## Workflow Closure" de `workflows/refactor.md` (uma única linha). Refinar o fingerprint anterior para 🟢 Resolved no que tange a `fullstack.md` e manter aberto apenas para `refactor.md`.

**Por que original:** **corrige** uma classificação errada do banco — sub-escopo mais específico, e o anterior está parcial não por implementação parcial mas por **diagnóstico parcial**.

---

## F2 — `helpers/archive-index.sh` permanece órfão de hook após 8 dias — a "promessa de rotação a cada 90 dias" do próprio `_index.md` não tem mecanismo de disparo

**Fingerprint:** `flow-helpers-archive-index-sh-orphan-of-hook-eight-days-after-flagged-rotation-90-day-promise-in-index-md-line-19-20-has-no-trigger-cron-ci-stop-hook-or-update-sh`

**Severidade:** **MEDIUM-HIGH**

**Evidência:**

```bash
$ grep -rln "archive-index" scripts/ helpers/ commands/ workflows/ .github/ skills/ CLAUDE.md 2>/dev/null
helpers/archive-index.sh                  # o próprio script
                                          # (NADA além dele — 0 consumidores)
```

E em `docs/reports/_index.md:19-20`:

> Estratégia de evolução: o índice cresce indefinidamente, mas pode ser **rotacionado** a cada 90 dias movendo entradas antigas para `_index-archive-YYYY-Q.md`.

O `archive-index.sh` (66 linhas, commit `eb3168e` de 2026-05-18) implementa exatamente essa rotação, mas:

- Nenhum sub-script de Stop o chama (`scripts/hooks/stop/01-*.sh`…`05-*.sh`)
- Nenhum sub-script de PreToolUse o chama
- Nenhum workflow do CI (`.github/workflows/ci.yml`)
- `scripts/update.sh` não o chama
- `scripts/install.sh` não o chama
- Não há cron/launchd documentado

Status no banco:

```text
ref-helpers-archive-index-script-shipped-but-not-hooked-no-cronjob-no-pre-tool-use-no-stop-trigger — flagged 2026-05-18 (HIGH)
```

Marcado em 2026-05-18, sem fix em 8 dias. Não promovido a ↩️ Reverted. Não foi marcado ✅. Simplesmente parado.

**Impacto:**

- `_index.md` cresce a ~12 linhas/dia mesmo sem commits (cada passada do scheduled task adiciona uma linha à tabela Statistics + 4-5 linhas por sub-relatório). Está em **821 linhas** hoje, +174 linhas em 7 dias (taxa de **+25 linhas/dia**, acelerou de +12 medido em 2026-05-19).
- O recurso necessário para frear o crescimento **existe** e **funciona** — só não foi conectado.
- Em ~25 dias o `_index.md` ultrapassa 1.500 linhas e o passo de dedup já lerá ~20k tokens só do índice.

**Recomendação:**

Adicionar 1 chamada simples em `scripts/hooks/stop/99-archive-index.sh` (novo subscript no tier `99-` = cleanup, alinhado à CLAUDE.md:368): verifica se hoje é dia-1 do trimestre, e em caso afirmativo executa `bash helpers/archive-index.sh --quiet`. ~10 linhas de bash. Reforça a regra trimestral sem cron externo.

**Por que original:** o fingerprint anterior só apontava "orphan of hook". Este sub-escopo **conecta** a orfandade à **regra documentada no próprio `_index.md`** que o script atende — explicita que a omissão **viola uma promessa pública do projeto**.

---

## F3 — Nenhum hook/CI valida `name == basename(dir)` em `skills/**/*/SKILL.md`; convenção implícita conformada por 124/125 skills, violada apenas por `shadcn`

**Fingerprint:** `auto-no-validator-enforces-skill-frontmatter-name-equals-directory-basename-convention-shadcn-is-the-only-violator-out-of-125-skills-bug-passed-silently`

**Severidade:** **MEDIUM**

**Evidência:**

```bash
$ for f in $(find skills/ -name "SKILL.md"); do
    name=$(grep -m1 "^name:" "$f" | sed 's/^name: //')
    dir=$(basename $(dirname "$f"))
    [ "$name" != "$dir" ] && echo "$f  name=$name  dir=$dir"
  done

skills/ui-libraries/shadcn/SKILL.md  name=shadcn-ui  dir=shadcn
```

Único violador entre **125 skills** (`find skills/ -name "SKILL.md" | wc -l` = 129; excluindo `skill-creator` user-invocable + 3 índices = 125 produtos auditáveis). Sem o gate, **o bug sobreviveu desde a criação da skill** (não datado, pré-banco de auditoria).

Comparação com gates equivalentes que existem:

- `helpers/agent-lint.sh`: valida frontmatter de agentes (`name`, `description`, `model`, `tools`) — **MAS NÃO valida frontmatter de skills**.
- `helpers/orphan-skill-scan.sh`: caça referências, **NÃO** valida frontmatter.
- `helpers/orphan-template-scan.sh`: idem.
- `helpers/size-limits.sh`: linhas, **NÃO** frontmatter.

→ Existe um **gap arquitetural**: nenhum dos 6 helpers cobre `skills/**/SKILL.md` no nível frontmatter.

**Impacto:**

- Hoje: 1 violador (shadcn). Sem gate, o número só pode crescer.
- Skill name aparece em logs do skill-tool, em barras de progresso de carregamento, em mensagens de erro — divergência entre `name` (logado) e `dir` (path no `Read`) quebra debugging.

**Recomendação:**

Estender `helpers/agent-lint.sh` (~10 linhas) para também varrer skills:

```bash
# Skill name == basename(dir) check
for f in $(find skills/ -name "SKILL.md"); do
  name=$(awk '/^name:/{print $2; exit}' "$f")
  dir=$(basename $(dirname "$f"))
  if [ "$name" != "$dir" ]; then
    echo "ERROR: $f → frontmatter name='$name' diverges from directory '$dir'"
    EXIT_CODE=1
  fi
done
```

Wireável em `.github/workflows/ci.yml` (mesma seção `agent-lint`) e em `scripts/hooks/stop/03-agent-lint.sh` (atualmente só valida agentes). Renomear o script para `03-frontmatter-lint.sh` ou criar `03b-skill-lint.sh`.

**Por que original:** distinto de `auto-no-validator-cross-checks-docs-agents-md-model-column-against-agent-frontmatter-discrepancy-survived-four-days-unseen` (2026-05-22, era agentes×docs) e de `auto-agent-lint-quiz-first-regex-only-matches-yes-no-variants` (2026-05-22, regex parcial). Aqui é **frontmatter de skills inteiramente sem validador**, gap classe diferente.

---

## Sumário das 3 recomendações

| # | Fingerprint | Severidade | Esforço |
|---|---|---|---|
| F1 | `refactor.md` Closure sem session-summary checkbox | MEDIUM | 1 linha |
| F2 | `archive-index.sh` órfão; promessa de rotação 90d sem trigger | MEDIUM-HIGH | ~10 linhas (novo `99-archive-index.sh`) |
| F3 | Sem validador de `name == dir` em skills | MEDIUM | ~10 linhas no `agent-lint.sh` |

Os 3 são wireamentos simples; total ≈ 20 linhas de código novas + 1 linha de markdown. Throughput esperado de implementação se o repo destravar: **mesmo dia**.
