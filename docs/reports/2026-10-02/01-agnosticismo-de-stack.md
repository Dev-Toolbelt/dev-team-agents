# Eixo A — Agnosticismo de stack — 2026-10-02

**Varredura integral** de `agents/` e `commands/` (o eixo não entra em amostragem).

Varredura semente obrigatória:

```bash
rg -in 'laravel|symfony|django|rails|spring|express|nest|next\.js|react|vue|angular|svelte|\
tailwind|bootstrap|eloquent|prisma|hibernate|sequelize|typeorm|phpunit|jest|vitest|pytest|\
rspec|composer|npm|yarn|pnpm|pip|maven|gradle|docker|kubernetes|terraform|aws|gcp|azure|\
mysql|postgres|mongodb|redis|php|python|ruby|golang|typescript|javascript' agents/ commands/
```

**124 linhas de hit → 23 candidatos agrupados por alvo+causa → 0 violações originais.**

## nenhum achado original neste eixo

Queda dos 23 candidatos:

| Porta / motivo | Candidatos |
|---|---|
| **Porta 5** (já registrado no banco como item aberto) | **17** |
| **Porta 3** (semântica — 2 de 3 atributos coincidem com linha registrada) | 3 |
| Exceção de seção (tabela de detecção, "Example", lista de skills condicionais) | 1 agrupado (mais ~12 descartes dentro dos grupos acima) |
| Falso positivo do regex (`nest` em "interest", `express` em "expression", `rails` em "trails") | 2 |

Este é o resultado esperado e é uma boa notícia: o Eixo A roda integral desde 2026-07-30 e o
estoque de acoplamento em `agents/` e `commands/` já está **inteiramente catalogado**. Dezessete dos
23 candidatos são itens do banco que seguem abertos — ou seja, o eixo não tem mais o que descobrir,
tem o que executar. O trabalho útil neste eixo hoje é fechar os 17, não achar o 18º.

Uma observação metodológica para o próximo pass: o regex semente produz 124 linhas para 23 grupos
reais, uma relação de 5:1 em ruído. Boa parte vem de três fontes — tabelas de detecção (que são
exceção por design), substrings de palavras comuns (`nest`, `express`, `rails`, `spring`) e
`python`/`docker` em contextos que são pré-requisito do próprio harness, não do projeto-alvo
(`commands/health-check.md:52` — "Python Prerequisite"). Ancorar os termos curtos com `\b` cortaria o
ruído sem perder cobertura.

---

## Descartados por duplicação

- `commands/commit.md:125-133` (tabela de lint: npm, eslint, phpcs, ruff, tsc) — porta 5 — já citado no banco pelas mesmas linhas, e é tabela de detecção.
- `agents/setup-assistant.md:146-147` (jest, pytest, phpunit na lista de sinais) — porta 5 — registrado, e lista de sinais.
- `agents/setup-assistant.md:26,66,74` (Docker Compose, "Docker, IaC") — porta 3 — coincide com `agent-setup-assistant-lines-60-70-docker-compose-version-detection-inline-bash-block-stack-prescriptive`.
- `agents/frontend-developer.md:3` (oito frameworks na `description`) — porta 5 — registrado e aberto.
- `agents/frontend-developer.md:83-96` (TanStack/SWR, `useState`) — porta 3 — alvo e causa iguais a `agent-frontend-developer-body-92-102-data-fetching-section-hardcodes-usestate-useeffect-tanstack-query-swr-stack-prescriptive`.
- `agents/frontend-developer.md:69-70` (Bootstrap, Chakra) — exceção — tabela de detecção de `ui-libraries`.
- `agents/frontend-developer.md:90,146` — porta 3 — cobertos por `agent-frontend-developer-testability-presumes-reactive-component-model`.
- `agents/frontend-reviewer.md:112,114` (PropTypes, `React.ChangeEvent`) — porta 1 — slug já no banco.
- `agents/frontend-test-specialist.md:141-153` (LCOV, Jest, Vitest, chave Sonar) — porta 5 — registrado.
- `agents/frontend-test-specialist.md:27,103` — exceção — sinais de detecção e roteamento para skill.
- `agents/mobile-developer.md:55-75,138-150,160` (matriz de runners, React Native) — porta 5 — registrado; `:55-75` são tabelas de detecção.
- `agents/devops-specialist.md:46-56,137-148` (Docker como "Primary", checklist Docker/Terraform) — porta 5 — registrado.
- `agents/devops-specialist.md:70-79` — exceção — tabelas de roteamento para skills de devops.
- `agents/database-specialist.md:27,55-72,132` (docker-compose, engines, env vars de Mongo/Redis/Supabase) — portas 3 e 5 — registrado; `:132` tem a mesma causa e remédio da linha já citada.
- `agents/security-specialist.md:28-29,80-85` (Dockerfile, expressões do GitHub Actions) — porta 1 — `agent-security-specialist-cicd-checklist-github-actions-only-vocabulary`.
- `agents/backend-reviewer.md:30` (phpcs, pyproject, rubocop, golangci) — porta 1 — `agent-reviewer-linter-config-three-divergent-ecosystem-incomplete-copies`.
- `agents/backend-reviewer.md:165-170` (placeholders `file.go`/`file.php`) — porta 3 — mesma causa e remédio de `agent-code-reviewer-output-template-pins-file-js-six-placeholders`; aqui os placeholders são deliberadamente mistos, logo não pinam uma linguagem.
- `agents/code-reviewer.md:79` (`npm run lint`, `composer phpcs`) — exceção — está sob comentário "Examples".
- `commands/mobile.md:19,26` (React Native, Expo, Flutter) — porta 5 — registrado.
- `commands/devops.md:2,14` (Docker na description e na linha de spawn) — porta 5 — registrado.
- `commands/audit.md:54,126,128` (Docker, Redis, CDN) — porta 5 — registrado.
- `commands/relayout.md:32,43` (Storybook, Tailwind, Docker) — porta 5 — registrado.
- `agents/backend-developer.md:78-83` (jsonwebtoken, laravel/horizon, sidekiq, wp-config) — exceção — tabela de detecção de skills.
- `agents/backend-developer.md:100` ("service provider registration") — porta 3 — exemplo entre parênteses; tema já em `agent-backend-developer-composition-root-rule-1-line-vs-frontend-developer-12-lines`.
- `agents/product-analyst.md:132-153` (gate de Docker, nomes de compose) — porta 3 — o gate é condicional ("only when the project uses Docker"), agnóstico por construção; a redundância com a cascata de worktree já está registrada.
- `agents/ui-ux-designer.md:57-59` (Xcode, Swift, React Native, Flutter) — exceção — tabela de detecção.
- `commands/commit.md:36-45`, `commands/merge.md:47-52` (stack Docker isolada) — exceção — delegam a `skills/shared/worktree/SKILL.md`, com Docker como "if used".
- `commands/adr.md:12` ("Adopt PostgreSQL") — exceção — exemplo de uso do comando.
- `commands/explain.md:28,48,63` — exceção — `:48` é cláusula anti-acoplamento ("never defaulting to JavaScript"); as demais são vocabulário.
- `commands/health-check.md:52` ("Python Prerequisite") — exceção — pré-requisito do CLI do harness, não do projeto-alvo.
- `agents/qa-specialist.md:3,9`, `agents/software-architect.md:89`, `commands/rule.md:27` — falso positivo do regex (substrings `nest`, `express`, `rails`).
