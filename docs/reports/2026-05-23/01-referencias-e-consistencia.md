# Referências e Consistência — 2026-05-23

> 3 sugestões originais. Cada item traz **trecho/evidência**, **motivo** e **impactos positivos e negativos** da correção proposta. Todas foram cruzadas contra o banco de 481 fingerprints (`_index.md`) e são inéditas.

---

## R1 — `frontend-developer` enumera 4 frameworks SPA + 4 template engines **na `description`** (a diretriz principal do agente) — violação stack-agnostic na superfície de identidade

**Severidade:** MEDIUM-HIGH
**Fingerprint:** `ref-frontend-developer-description-frontmatter-enumerates-react-vue-svelte-angular-and-blade-twig-erb-jinja-on-identity-surface`

**Evidência** — `agents/frontend-developer.md:3` (campo `description` do frontmatter):

```yaml
description: Implements frontend features following the project's design system and
  architecture. Works in both decoupled SPAs (React, Vue, Svelte, Angular) and
  server-rendered templates (Blade, Twig, ERB, Jinja). Collaborates with ui-ux-designer …
```

**Motivo:** a `description` é o **primeiro contato** do orquestrador com o papel do agente (a "diretriz principal", exatamente o alvo que a tarefa pede para auditar). A regra core da CLAUDE.md manda que agentes sejam **stack-agnostic** e que listas concretas vivam apenas em tabelas de detecção→skill no corpo. Aqui a identidade do agente já fixa uma lista fechada de **8 tecnologias** (React/Vue/Svelte/Angular + Blade/Twig/ERB/Jinja). Um projeto em **Solid**, **Qwik**, **Alpine**, **Razor (.cshtml)** ou **Slim/Handlebars** não aparece, e a identidade do agente sugere que ele "trabalha com" só esse conjunto. Este é exatamente o mesmo padrão já flagrado e parcialmente corrigido em outros agentes — `devops-specialist` (description, ✅ 2026-05-13/18), `database-specialist` (description, 2026-05-20) e `mobile-developer` (description, 2026-05-22) — mas **o `frontend-developer` nunca foi auditado na sua description**, apesar de ser o agente com a lista mais longa. Note o contraste interno: o **corpo** já tem a tabela de detecção correta (linhas 79-92, "Chakra UI", "TanStack Query" → skills), provando que o autor sabe o padrão — ele só não foi aplicado à description.

**Impacto positivo da correção:** reescrever para algo agnóstico ("Works in both decoupled SPA architectures and server-rendered template architectures; detects the project's framework and loads the matching skill") completa a família de descrições e remove o viés de identidade; mantém a tabela de detecção do corpo como fonte única das tecnologias concretas.

**Impacto negativo / risco:** contra-argumento legítimo — nomear stacks populares ajuda o roteador a escolher o agente certo. Mitigação: manter os exemplos **apenas** na tabela de detecção (corpo), nunca na description. Risco de regressão: como `database`/`mobile`, é uma classe que **reaparece** a cada feature nova; vale ligar o validador que cruza description × regra agnóstica (sugerido em passadas anteriores).

---

## R2 — A CLAUDE.md (Hook Files Map + File Structure) **omite `scripts/hooks/lib/session-summary-detect.sh`**, dependência compartilhada por 2 hooks

**Severidade:** MEDIUM
**Fingerprint:** `ref-claude-md-hook-files-map-and-file-structure-omit-scripts-hooks-lib-session-summary-detect-shared-dep-of-two-hooks`

**Evidência** — o `lib/` existe e é `source`-ado por **dois** hooks:

```
scripts/hooks/pre-compact.sh:14          . "$(dirname …)/lib/session-summary-detect.sh"
scripts/hooks/stop/01-session-summary.sh:13  . "$(dirname …)/../lib/session-summary-detect.sh"
```

E a "Hook Files Map" da CLAUDE.md lista só os 4 entry-points:

```
| SessionStart | scripts/hooks/session-start.sh | — | … |
| PreToolUse   | scripts/hooks/pre-tool-use.sh  | Dispatcher | … |
| PreCompact   | scripts/hooks/pre-compact.sh   | — | … |
| Stop         | scripts/hooks/stop.sh          | Dispatcher | … |
```

**Motivo:** o arquivo `lib/session-summary-detect.sh` (599 B) centraliza a lógica de detecção (`TODAY`, `NOW`, `HAS_CHANGES`, `TODAY_COMMITS`) usada por `pre-compact.sh` **e** por `stop/01-session-summary.sh` — um bom padrão de DRY em runtime. O problema é puramente documental: nenhuma das duas estruturas de referência da CLAUDE.md (Hook Files Map **nem** o ASCII tree de File Structure) menciona o subdiretório `lib/` ou esse arquivo. Quem for alterar a lógica de detecção de sessão lendo a CLAUDE.md **não descobre** que ela é compartilhada por dois hooks — risco de editar um caminho e regredir o outro. Distinto dos achados de File Structure anteriores: `ref-claude-md-file-structure-omits-helpers-and-privacy` (2026-05-18, diretórios de topo), `…-scripts-enumeration-omits-…` (2026-05-20, scripts de topo) e `…-skills-subtree-omits-…` (2026-05-21, domínios de skill). Aqui o gap é a **subárvore de hooks** e, especialmente, uma **dependência compartilhada invisível**.

**Impacto positivo da correção:** acrescentar uma linha à Hook Files Map ("Shared: `scripts/hooks/lib/session-summary-detect.sh` — detecção comum a PreCompact e Stop/01") e ao ASCII tree torna o acoplamento explícito; protege a lógica compartilhada de edições parciais.

**Impacto negativo / risco:** nenhum funcional (doc). Único risco é a própria CLAUDE.md crescer — mitigável com uma única linha, sem nova seção.

---

## R3 — A skill `release-prep` existe em **duas árvores com conteúdo divergente** (88 linhas enviadas vs 181 linhas dev), mesmo nome, sem regra de sync

**Severidade:** MEDIUM
**Fingerprint:** `ref-release-prep-skill-exists-twice-shared-88-lines-shipped-vs-claude-skills-181-lines-dev-divergent-content-no-sync-rule`

**Evidência** — dois `SKILL.md` chamados `release-prep`:

```
 88  skills/shared/release-prep/SKILL.md    ← árvore enviável; carregada por agents/technical-writer.md
181  .claude/skills/release-prep/SKILL.md   ← .claude/ (dev-only, removido do pacote por install.sh)
```

**Motivo:** existem **duas** skills homônimas em árvores diferentes, com **conteúdos divergentes** (88 vs 181 linhas, ~2× de diferença). A de `skills/shared/release-prep/` é parte do pacote instalado e é a única referenciada por um agente real (`technical-writer`). A de `.claude/skills/release-prep/` é uma skill de nível-repo (dev/release tooling), `rm -rf`-ada do tarball pelo `install.sh` (junto com todo o `.claude/`). O risco é duplo: (1) **confusão de manutenção** — um colaborador editando "a skill release-prep" pode tocar a errada; (2) **deriva silenciosa** — não há regra de sync entre as duas (como existe para o par README), então elas vão divergindo sem detecção (já estão em 88 vs 181). É a mesma classe da divergência `templates/backlog-template.md` físico × skill homônima notada em 2026-05-22, mas um **par diferente** (`release-prep` × `release-prep`) e com a agravante de estarem em **árvores de empacotamento opostas**.

**Impacto positivo da correção:** decidir conscientemente — ou (a) renomear uma delas para deixar claro o escopo (`release-prep` enviável vs `repo-release-prep` interno), ou (b) registrar no CLAUDE.md/Package-exclusions que são duas coisas distintas com propósitos distintos, removendo a ambiguidade do nome.

**Impacto negativo / risco:** baixo. Renomear a versão dev exige atualizar suas referências em `CONTRIBUTING.md`/`.claude/` (poucas). Se nada for feito, o custo é a deriva continuar — um dia o `technical-writer` herdará um comportamento desatualizado sem que ninguém perceba que havia uma "outra" release-prep mais nova.
