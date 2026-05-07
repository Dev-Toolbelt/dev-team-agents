# 5. Automação e Governança

← [Voltar ao índice](index.md)

---

## 5.1 Validador de frontmatter de agente

Embora `agent-creator` carregue checklist manual, **não há script** que verifique:
- Frontmatter contém `name`, `description`, `model`, `tools`
- `model` está entre os 3 permitidos
- Existe seção "Foundational Rule"
- Para coding agents, existe seção "Worktree Isolation"

> **Fingerprint:** `auto-skill-frontmatter-validator`

**Sugestão:** Criar `scripts/agent-lint.sh` chamado pelo `Stop` hook quando o
`git status --porcelain` mostrar mudança em `agents/*.md`.

## 5.2 Detecção de skills carregadas em duplicidade no mesmo agente

`orphan-skill-scan.sh` detecta órfãos e refs quebradas, mas não detecta uma skill
carregada **duas vezes** no mesmo agente (caso real do `database-multitenancy` no
`database-specialist`).

> **Fingerprint:** `auto-redundant-skill-load-scan`

**Sugestão:** Adicionar uma terceira fase ao scan:
```bash
for agent in agents/*.md; do
  awk '/skills\/.*\/SKILL\.md/' "$agent" | sort | uniq -c | awk '$1>1'
done
```

## 5.3 Validador de sincronia README.md ↔ README.pt-BR.md

A regra "README Sync Rule" do `CLAUDE.md` é uma política, mas não há `pre-commit` que
a valide. Resultado: as listas de skills divergiram (visto em [§1.2.B](01-referencias.md#b-readme-desatualizado-em-relação-à-árvore-real-de-skills)).

> **Fingerprint:** `gov-readme-pt-br-sync-check`

**Sugestão simples:** comparar contagem de linhas + headings nas duas versões; alertar
se diferença > 5%.

```bash
diff <(grep -c '^#' README.md) <(grep -c '^#' README.pt-BR.md)
```

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Pega regressão no commit, não em produção |
| **Negativo** | Pode dar falso positivo quando uma versão tem mais conteúdo legítimo (ajustar tolerância) |
