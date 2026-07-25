# Fluxos e Workflows — 2026-05-15

> Pontos de melhoria em fluxos `/devteam:*`, hooks, scripts de install/update, e workflows.

---

## 1. `flow-refactor-command-duplicates-workflows-refactor-md-content-with-full-prompts-inline`

**Arquivo:** `commands/refactor.md` (152 linhas) vs. `workflows/refactor.md` (278 linhas)

**Observação:** o command inline um pipeline de 4 fases (Analysis → Joint Planning → Implementation → Quality Gate) com **prompts completos para software-architect, test-specialists, database, security**, variante Fast-Track e Plan Gate boilerplate. **`workflows/refactor.md` existe** e cobre o mesmo conteúdo de forma canônica.

Padrão repo: command é orquestrador curto → workflow é guia detalhado.

**Por que importa:**
- Duplicação: alterar fluxo de refactoring exige editar **dois arquivos** ou divergem silenciosamente.
- Outros commands (`/devteam:fullstack`, `/devteam:bugfix`) já usam padrão curto delegando ao workflow.

**Impacto positivo:** reduzir `commands/refactor.md` de 152 → ~30 linhas (delega para `workflows/refactor.md`); single-source-of-truth; economia ~2.000 tokens/spawn.

**Impacto negativo:** usuários que invocam `/devteam:refactor` precisam de 1 ida-volta extra à doc; mitigável com link `[full workflow](../workflows/refactor.md)` no header.

---

## 2. `flow-commit-command-160-lines-pre-commit-gates-extractable-skill`

**Arquivo:** `commands/commit.md` (160 linhas — **maior command do repo**)

**Observação:** Steps 4.5a/b/c/d (Lint / Type-check / Tests / commit-msg validation) somam ~60 linhas de lógica reutilizável. Step 3 (layer-mapping table de 9 rows) duplica a mesma classificação que `conventional-commits/SKILL.md` faz.

Candidatos de extração:
- `skills/shared/pre-commit-gates/SKILL.md` — lint/type-check/test runner detection
- `skills/shared/commit-layer-mapping/SKILL.md` — classificação por path/extensão

**Por que importa:**
- Outros commands (potencialmente `/devteam:pr`) duplicarão a mesma lógica.
- Edge cases (ESLint vs Biome, `tsc --noEmit` vs `pyright`) requerem fixes em N lugares.

**Impacto positivo:** commit.md cai para ~80 linhas; pre-commit-gates reutilizável por `/devteam:pr` e CI sub-tasks; economia ~1.300 tokens × spawns onde commit é invocado.

**Impacto negativo:** mais um skill no repo (++1 file); aumento marginal do orphan-scan scope.

---

## 3. `flow-install-script-strip-list-stale-misses-new-dev-only-scripts-fingerprint-orphan-template-rollback`

**Arquivo:** `scripts/install.sh:158-162`

**Observação:** o `install.sh` strippa explicitamente:

```bash
rm -f "$INSTALL_DIR/scripts/install.sh"
rm -f "$INSTALL_DIR/scripts/orphan-skill-scan.sh"
rm -f "$INSTALL_DIR/scripts/agent-lint.sh"
rm -f "$INSTALL_DIR/scripts/size-limits.sh"
```

**Não strippa** (e portanto ship para usuários):
- `scripts/check-fingerprint-uniqueness.sh` (criado hoje, 26 linhas)
- `scripts/orphan-template-scan.sh` (criado hoje, 36 linhas)
- `scripts/rollback.sh` (created earlier, 89 linhas — útil ao usuário, **manter**)
- `scripts/validate-commit-msg.sh` (49 linhas — útil, mas vide #5 abaixo)

**Por que importa:**
- Scripts dev-only (fingerprint-uniqueness, orphan-template-scan) vão para `.dev-team-agents/scripts/` em todas as instalações = **bloat desnecessário**.
- Critério "dev tool only" não está documentado em comentário inline na strip list → fica obscuro qual script deve ser adicionado a cada release.

**Impacto positivo:** +2 linhas `rm -f` no install.sh; reduzir footprint do pacote instalado em ~62 linhas.

**Impacto negativo:** zero. Strip de dev-tools é convenção consolidada.

---

## 4. `flow-notifier-hardcodes-45-tip-strings-in-bash-array-no-externalized-data`

**Arquivo:** `scripts/hooks/stop/04-notifier.sh:184-235` (240 linhas total — **maior hook script**)

**Observação:** 15 tips × 3 idiomas (pt-BR / en / es) = **45 strings hardcoded** em array Bash inline (~9 KB). Adicionar 16ª tip ou corrigir typo exige editar o hook em si.

```bash
TIPS_PT=(
  "Use /devteam:plan antes de mudanças grandes"
  "..."  # × 14 mais
)
TIPS_EN=( ... )
TIPS_ES=( ... )
```

**Por que importa:**
- Single-responsibility violation: hook deveria emitir, dados deveriam ser externalizados.
- Não é localizado por outros idiomas (fr, it, de) sem rebuild do script.
- Cada invocação do `Stop` hook carrega **todas as 45 strings** mesmo emitindo só 1 por dia.

**Impacto positivo:**
- Mover para `skills/shared/notifier/tips/{pt-BR,en,es}.json`.
- Hook lê arquivo correspondente ao locale do usuário → carrega apenas 15 strings em vez de 45 (−67% memória do hook).
- Adicionar idioma vira drop-in `tips/it.json` sem mudar hook.

**Impacto negativo:** +1 dependência de leitura de filesystem por execução (~5ms overhead, desprezível); +1 skill criado.

---

## 5. `flow-commit-references-nonexistent-validate-commit-msg-script-dead-conditional`

**Arquivo:** `commands/commit.md:99-112` (Step 4.5d)

**Observação:** o command verifica:

```bash
if [ -f ".dev-team-agents/scripts/validate-commit-msg.sh" ]; then
  bash .dev-team-agents/scripts/validate-commit-msg.sh "$MSG"
fi
```

Porém o script `scripts/validate-commit-msg.sh` **existe** no repo (49 linhas) mas NÃO está sendo distribuído pelo `install.sh` (não está na allowlist `KEEP_ROOT` explícita para scripts/, nem é tratado como dev-only).

Verificação: `bash scripts/install.sh --dry-run` (se existir) mostra que `scripts/` é copiado integralmente — então o script ESTÁ sendo distribuído. A condicional não é dead, mas o **fingerprint `ref-validate-commit-msg-script-now-distributed-but-still-orphan-from-ci-and-commit-command` (2026-05-14)** marcou Executed sem validar invocação em commit.md.

**Por que importa:**
- Marca Executed de 2026-05-14 é **falso positivo parcial**: script distribuído sim, mas invocação `commands/commit.md:99-112` usa path absoluto que **não funciona em todos os ambientes** (assume install em `.dev-team-agents/`; ignora override `DEVTEAM_INSTALL_DIR`).

**Impacto positivo:** usar `$INSTALL_DIR` exportado pelo session-start hook; ou fallback inline com regex Conventional Commits direto no command.

**Impacto negativo:** mais 5-10 linhas no commit.md (que já é maior do repo). Contradiz #2 acima — preferir extração para skill `pre-commit-gates`.

---

## 6. `flow-ci-fingerprint-check-strict-while-orphan-scan-tolerant-asymmetric-gates`

**Arquivo:** `.github/workflows/ci.yml:23-25`

**Observação:** asimetria entre dois gates novos:

```yaml
- name: Orphan skill scan
  run: bash scripts/orphan-skill-scan.sh --quiet
  continue-on-error: true        # ← tolerante

- name: Fingerprint uniqueness check
  run: bash scripts/check-fingerprint-uniqueness.sh
  # SEM continue-on-error          ← strict
```

Combinado com o bug do regex (vide [01-referencias-e-consistencia](01-referencias-e-consistencia.md#1)), o gate strict **vai falhar CI por falso positivo** em algum PR futuro (ex.: dois SHAs `b8ece69` mencionados em PR description).

**Por que importa:**
- Inversão de risco: orphan-scan é mais maduro (validado) mas tem `continue-on-error`; fingerprint-check é novo, com bug conhecido, e é strict.
- Resultado provável: primeiro PR falhar irá disparar revert ou hot-fix; pior caso bloqueia merges.

**Impacto positivo:** ou (a) adicionar `continue-on-error: true` até regex ser corrigido (defensivo), ou (b) corrigir regex primeiro e manter strict (preferível).

**Impacto negativo:** zero — ambas opções melhoram robustez.

---

## 7. `flow-workflows-plan-template-reference-density-1x-vs-8x-inconsistent-enforcement`

**Arquivos:** `workflows/*.md` (10 arquivos)

**Observação:** densidade de referência ao `templates/plan-template.md` varia 8× entre workflows:

```bash
$ grep -c "plan-template" workflows/*.md
workflows/bug-fix.md:1
workflows/design.md:1
workflows/mobile.md:1
workflows/fullstack.md:2
workflows/maintenance.md:2
workflows/new-project.md:3
workflows/inherited-project.md:3
workflows/security-patch.md:4
workflows/review.md:5
workflows/refactor.md:8
```

**Por que importa:**
- workflows mais simples (bug-fix, design, mobile) **mencionam plan-template apenas 1×** — Plan Gate enforcement é frágil.
- workflows complexos (refactor) reforçam 8×, ofuscando o objetivo do step.
- Inconsistência sugere falta de checklist canônico de "como escrever um workflow".

**Impacto positivo:** padronizar densidade (idealmente 2-3 refs por workflow: 1 no header, 1 no step principal, 1 no closing).

**Impacto negativo:** edição em massa de 10 arquivos; risco de regredir conteúdo único de cada workflow.
