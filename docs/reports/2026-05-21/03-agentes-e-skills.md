# Agentes e Skills — 2026-05-21

> 3 sugestões originais. Foco do dia: **violações stack-agnostic em agentes ainda não auditados** (security-specialist, frontend-reviewer) e padrão de extração não aplicado a uma skill grande. Cada item traz **trecho**, **motivo** e **impactos positivos e negativos**. Deduplicadas contra os 437 fingerprints.

---

## A1 — `security-specialist` codifica no corpo comandos de SAST e auditoria de dependências por linguagem/ferramenta (stack-prescritivo)

**Severidade:** HIGH
**Fingerprint:** `agent-security-specialist-body-130-153-hardcodes-per-language-sast-and-dep-audit-commands-bandit-composer-npm-trivy-stack-prescriptive`

**Evidência** — `agents/security-specialist.md:130-153`:

```bash
# SAST
semgrep --config=auto .
bandit -r . -ll          # Python
# Node.js
npm audit --audit-level=high
# PHP (Composer)
composer audit
# Python
pip-audit
# Docker image
trivy image myapp:latest
# General
snyk test
```

**Motivo:** o corpo do agente fixa um conjunto fechado de ferramentas atreladas a linguagens/ecossistemas concretos (`bandit`→Python, `npm audit`→Node, `composer audit`→PHP, `pip-audit`→Python, `trivy`→Docker). É a **mesma classe** da reabertura aberta do `devops-specialist` (corpo stack-prescritivo), mas em um agente ainda não flagrado para isso — o banco só tinha `ref-security-specialist-tools-lack-write-edit` (sobre permissões de tool, não relacionado). O princípio ("rode SAST e auditoria de dependências, trate HIGH/CRITICAL") é stack-agnostic e correto; a **lista concreta de comandos** deveria viver numa skill (ex.: `skills/security/dependency-scanning/`) carregada por gate de detecção do ecossistema, deixando no corpo apenas o princípio.

**Impacto positivo da correção:** conforma o agente ao mandato stack-agnostic; centraliza a matriz "ecossistema → ferramenta" numa skill versionável (mais fácil manter e estender com novas ferramentas); reduz o corpo do agente (que está em 234 linhas, acima do cap).

**Impacto negativo / risco:** uma camada de indireção (agente → skill) significa que, para o caso comum, o LLM precisa carregar a skill; mitigável mantendo no corpo um resumo de 2-3 linhas do princípio e o gate. Risco de, na migração, perder algum comando — recomenda-se mover verbatim para a skill.

---

## A2 — `frontend-reviewer` usa identificadores React/TypeScript no corpo (Type Safety + Code Quality)

**Severidade:** MEDIUM
**Fingerprint:** `agent-frontend-reviewer-body-type-safety-and-code-quality-hardcodes-react-ts-identifiers-proptypes-react-changeevent-hocs`

**Evidência** — `agents/frontend-reviewer.md:107-117`:

```
### 10. Type Safety
- Component props without declared types (PropTypes, TypeScript interfaces)
- Forced type assertions (`as Type`) without a guard
- Event handler types missing (`React.ChangeEvent<HTMLInputElement>` vs generic `Event`)

### 11. Code Quality & Conventions
- KISS violations: ... HOCs wrapping HOCs, context for a single value
```

**Motivo:** `PropTypes`, `React.ChangeEvent<HTMLInputElement>`, `as Type` e `HOCs` são identificadores específicos de React/TypeScript embutidos no corpo de um agente que deveria ser stack-agnostic. É a mesma classe já flagrada em `frontend-developer` (composition root / security) e `frontend-test-specialist` (receitas React/Vue), mas o `frontend-reviewer` é um arquivo distinto ainda não coberto pelo banco. Os critérios de revisão (props tipadas, evitar asserções forçadas, evitar abstração desnecessária) são válidos de forma genérica; só a **redação** está presa a uma stack.

**Impacto positivo da correção:** consistência com os outros agentes de frontend já saneados; o checklist de revisão fica aplicável a qualquer framework (Angular, Svelte, Vue, etc.) sem reescrita; reduz o tamanho do maior cluster de agentes de revisão.

**Impacto negativo / risco:** revisores humanos acostumados aos exemplos React podem achar a versão genérica menos "concreta"; mitigável citando exemplos entre parênteses como ilustração ("ex.: em React, `React.ChangeEvent`") em vez de como regra. Cuidado para não perder a especificidade útil ao generalizar.

---

## A3 — Skill `architecture/graphql` (235 linhas, 3ª maior) nunca recebeu a extração para `references/` e é carregada por gate narrativo, não por sinal de detecção

**Severidade:** LOW-MEDIUM
**Fingerprint:** `skill-architecture-graphql-235-lines-third-largest-no-references-extraction-loaded-by-narrative-gate-not-detection-signal`

**Evidência** — tamanho e estrutura:

```
235 skills/architecture/graphql/SKILL.md
$ ls skills/architecture/graphql/
SKILL.md            # nenhum subdiretório references/
```

Carregamento — `agents/backend-developer.md:47`:

```
Load `skills/architecture/graphql/SKILL.md` when implementing a GraphQL API — covers schema design, resolver patterns, N+1 prevention via DataLoader, and subscription conventions.
```

**Motivo:** em 2026-05-13 o padrão de extração `references/` foi aplicado a 7 skills grandes para permitir lazy-load por seção. A `graphql` (3ª maior skill do repo, atrás só de `graphify-setup` e `project-context`) **nunca recebeu esse tratamento** — segue monolítica. Além disso, o gate de carga é uma frase narrativa ("when implementing a GraphQL API"), não um sinal de detecção estruturado como os que `mobile-developer`/`ui-ux-designer` usam (tabela de Detection Signals). Inédito no banco (`graphql` não aparece em nenhum fingerprint). Distinto da reabertura do design-patterns (R3): lá a extração foi feita mas o gate não foi ligado; aqui a extração nunca foi sequer feita.

**Impacto positivo da correção:** aplicar `references/` (ex.: `schema-design.md`, `dataloader-n+1.md`, `subscriptions.md`) permite carregar só a seção relevante; converter o gate narrativo em sinal de detecção (presença de `*.graphql`/`schema.graphql`, dependência `graphql`/`apollo` no manifesto) torna o carregamento determinístico e econômico.

**Impacto negativo / risco:** GraphQL é, por natureza, um tópico específico — há quem argumente que a skill inteira já é "a referência" e não precisa fragmentar. O ganho de lazy-load só se materializa se os consumidores realmente carregarem por seção (vide a lição da reabertura design-patterns: extrair sem ligar o gate não economiza nada). Recomenda-se fazer as duas coisas juntas (extrair **e** ligar o gate) ou nenhuma.
