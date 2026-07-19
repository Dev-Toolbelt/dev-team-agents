# Relatório — Referências e Consistência

**Data:** 2026-05-26
**Janela auditada:** 2026-05-24 → 2026-05-26
**Foco:** discrepâncias estruturais inéditas detectadas por releitura de skills/agentes (8ª janela consecutiva sem commits — sem drift por commit, achados vêm de leitura sistemática).

---

## R1 — `skills/ui-libraries/shadcn` tem `name: shadcn-ui` no frontmatter divergente do diretório

**Fingerprint:** `ref-skill-ui-libraries-shadcn-frontmatter-name-shadcn-ui-with-hyphen-while-directory-basename-is-shadcn-no-validator-enforces-name-equals-dir-convention`

**Severidade:** **MEDIUM**

**Evidência:**

```yaml
# skills/ui-libraries/shadcn/SKILL.md  (linhas 1-3)
---
name: shadcn-ui
description: shadcn/ui — Radix UI + Tailwind copy-paste; MCP for component install.
---
```

O diretório é `skills/ui-libraries/shadcn/`, mas o `name:` do frontmatter é `shadcn-ui`.
Todas as outras 5 skills de `ui-libraries/` conformam:

| Diretório | `name:` no frontmatter | Bate? |
|---|---|---|
| `antd` | `antd` | ✅ |
| `bootstrap` | `bootstrap` | ✅ |
| `chakra-ui` | `chakra-ui` | ✅ |
| `jquery` | `jquery` | ✅ |
| `mui` | `mui` | ✅ |
| **`shadcn`** | **`shadcn-ui`** | **❌** |

**Impacto:**

1. **Lookup ambíguo:** `frontend-developer.md:75` carrega pelo path (`skills/ui-libraries/shadcn/SKILL.md`), mas qualquer skill loader que use o nome como chave (ex. registry, slash-command de skill) procura por `shadcn-ui` e falha ao mapear de volta para o diretório `shadcn`.
2. **Identificação interna inconsistente:** o conteúdo da skill em `:23` registra `"shadcn-ui": {...}` como nome do MCP — ou seja, há **duas grafias** para o mesmo identificador no mesmo arquivo.
3. **Sem validador:** `helpers/agent-lint.sh` valida frontmatter de agentes; nenhum equivalente cobre `skills/**/*/SKILL.md` para a regra "name == basename(dir)".

**Recomendação:**

- **Opção A (mínima):** renomear `name: shadcn-ui` → `name: shadcn` (preserva path, alinha com as outras 5).
- **Opção B (acomodação):** renomear diretório `shadcn/` → `shadcn-ui/` e atualizar a única referência em `agents/frontend-developer.md:75`.

**Por que original:** banco menciona `ref-no-codeowners-file` e `ref-orphan-template-scan-consumers-list` mas **nenhum fingerprint anterior tratou inconsistência name×directory** em skills. Distinto também de `auto-no-frontmatter-tools-validator` (era ordem de tools em agentes).

---

## R2 — `CLAUDE.md:130` aponta `agent-creator` para path externo `.claude/skills/agent-creator/SKILL.md` sem nenhuma validação de existência

**Fingerprint:** `ref-claude-md-130-agent-creator-points-to-external-claude-skills-path-shipped-by-host-not-by-repo-no-validator-checks-the-path-exists-at-runtime-and-orphan-scan-cannot-cover-it`

**Severidade:** **LOW-MEDIUM**

**Evidência:**

```markdown
# CLAUDE.md:128-131
| Skill | Path | Trigger |
|-------|------|---------|
| `skill-creator` | `skills/skill-creator/SKILL.md` | `/skill-creator` ... |
| `agent-creator` | `.claude/skills/agent-creator/SKILL.md` (global Claude skill — not in this repo) | `/agent-creator` ... |
```

A varredura `grep -rohE 'skills/.../SKILL\.md'` encontra a única referência a `skills/agent-creator/SKILL.md` exatamente nesta linha — o tooling de orphan scan tenta resolvê-la contra o repo e falha silenciosamente porque a regra exclui user-invocable skills:

```text
MISSING: skills/agent-creator/SKILL.md   (encontrado por grep, ignorado por helpers/orphan-skill-scan.sh)
```

**Impacto:**

- Documentação prometida ("Global Claude skill") **não tem nenhum mecanismo para verificar se o cliente Claude do usuário realmente entregou o arquivo**.
- Se o ambiente do desenvolvedor mudar (perda do plugin `.claude/skills/`, instalação parcial, host alternativo), o trigger `/agent-creator` simplesmente quebra sem aviso.
- Diferença para R1: aqui o problema **não é grafia**, é **declaração de dependência externa sem health-check**.

**Recomendação:**

Adicionar verificação em `scripts/hooks/session-start.sh` (ou em um novo `helpers/external-skills-check.sh`) que, para cada entrada da tabela de `CLAUDE.md` cuja `Path` começa com `.claude/skills/`, faça `[ -f "$HOME/.claude/skills/.../SKILL.md" ] || warn`. ~12 linhas de bash; promove a tabela de prosa documental para contrato verificável.

**Por que original:** este path é citado em `docs/reports/2026-05-06/01-referencias.md:23` (fora do banco), mas nunca virou fingerprint próprio. Distinto de `ref-claude-md-mentions-agents-creator-as-claude-skills-path` (2026-05-12) — aquele era ambiguidade `path repo×path pós-install`; este é **ausência de gate de existência runtime**.

---

## R3 — Bullet `TODO/FIXME que deveria ser issue tracker tickets` duplicado verbatim em 3 agentes revisores sem skill compartilhada

**Fingerprint:** `ref-three-reviewers-todo-fixme-issue-tracker-tickets-bullet-duplicated-verbatim-no-shared-source-distinct-from-reviewer-base-and-reviewer-mindset-already-extracted`

**Severidade:** **LOW-MEDIUM**

**Evidência:**

```text
agents/code-reviewer.md:124   - TODO/FIXME comments (should be issue tracker tickets)
agents/backend-reviewer.md:133 - TODO/FIXME that should be issue tracker tickets
agents/frontend-reviewer.md:122 - TODO/FIXME that should be issue tracker tickets
```

Os 3 reviewers já carregam `skills/shared/reviewer-base/SKILL.md` (19 linhas) **E** `skills/shared/reviewer-mindset/SKILL.md` (18 linhas) — ou seja, **o padrão de extração já existe e foi aplicado** para conceitos correlatos, mas este bullet específico (e outros do mesmo bloco "Smells comuns") foi deixado inline.

A redação não é idêntica (uma usa "comments", outras "that") — sinal clássico de copy-paste e divergência semântica latente. Se a política mudar (ex. "TODOs com data de vencimento são OK"), o autor precisa lembrar de tocar 3 arquivos.

**Impacto:**

- ~3 bullets × 3 arquivos = ~9 linhas de duplicação. Token-wise marginal (~120 tokens/spawn), mas representa **regressão do princípio de single-source-of-truth** que motivou a extração de `reviewer-mindset` no v1.4.

**Recomendação:**

Acrescentar 1 seção `Common Smells` à `skills/shared/reviewer-base/SKILL.md` com 3-5 bullets de smells comuns (TODO/FIXME, magic numbers, dead code, commented-out code, console.log/print). Substituir o bullet inline pelos 3 reviewers por uma referência à seção.

**Por que original:** existe `skill-shared-reviewer-base-and-reviewer-mindset-two-overlapping-checklist-skills-loaded-by-4-review-agents-no-documented-boundary` (2026-05-19) sobre **fronteira**, mas nenhum fingerprint tratou de **conteúdo concreto duplicado nos consumidores das duas skills**.

---

## Sumário das 3 recomendações

| # | Fingerprint | Severidade | Esforço |
|---|---|---|---|
| R1 | shadcn-ui name×dir mismatch | MEDIUM | 1 linha (rename) + adicionar regra ao `agent-lint.sh` (~10 linhas) |
| R2 | `agent-creator` external path sem health-check | LOW-MEDIUM | ~12 linhas de bash em `session-start.sh` |
| R3 | TODO/FIXME bullet duplicado em 3 reviewers | LOW-MEDIUM | mover para `reviewer-base/SKILL.md`, substituir nos 3 arquivos |

Nenhum dos 3 conflita com fingerprint marcado ✅ Executed ou ↩️ Reverted no banco.
