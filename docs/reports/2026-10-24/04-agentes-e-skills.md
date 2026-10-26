# Eixo D — Agentes e Skills — 2026-10-24

**Baseline:** `HEAD` = `b64428b`. 18 agentes, 156 `SKILL.md`, 1 skill nova no delta
(`skills/devops/local-environment`).

## Nenhum achado original neste eixo.

### Tamanhos no `HEAD`

Nenhum agente ou comando acima do teto (`helpers/size-limits.sh` limpo; agentes 211, comandos 200,
skills 500). As cinco maiores `SKILL.md`:

| Linhas | Skill | `references/`? | Estado |
|---|---|---|---|
| 414 | `skills/shared/migration-v1-to-v2` | não | Porta 5 — já no conjunto aberto |
| 402 | `skills/architecture/orchestration` | não | Porta 5 — `token-orchestration-skill-377-lines-…-no-references-dir`, **mediu pior**: 377 → 402 |
| 334 | `skills/shared/project-context` | sim | — |
| 319 | `skills/shared/backlog-template` | não | 242 no `HEAD` (as 319 são do working tree sujo); abaixo de qualquer limiar |
| 318 | `skills/shared/interaction-patterns` | não | Porta 5 — `token-interaction-patterns-209-lines-…`, **mediu pior**: 209 → 318 |

### A skill nova passa

`skills/devops/local-environment/SKILL.md` — 105 linhas, carregada condicionalmente por
`/devteam:up`, `/devteam:down` e pelo Visual Check Gate, e referenciada na tabela de detecção de
`agents/devops-specialist.md:73`. Dentro do orçamento, com um único dono, sem regra duplicada em
corpo de agente. `orphan-skill-scan.sh` a encontra alcançável.

### Candidato levantado e descartado

- **`skills/shared/docs-templates/SKILL.md` com 301 linhas de esqueletos de documento sem
  `references/`.** Medido no disco e **falso**: no `HEAD` o arquivo tem **153 linhas / 4.014
  bytes**. As 301 linhas, os nove esqueletos e as chamadas a `scripts/doc-path.sh` pertencem a
  trabalho não commitado. Descartado na Porta 0 — a evidência não existe no `HEAD`. Registrado
  aqui porque é exatamente o tipo de achado que uma auditoria sobre o disco teria publicado como
  HIGH.
- **Regra de sonda de compose duplicada entre `product-analyst` e `stack-detection`.** Real, mas o
  defeito dominante é o acoplamento a produto numa seção de comportamento, não a duplicação.
  Publicado no Eixo A como `agent-product-analyst-step6-gates-isolated-infra-on-docker-and-inlines-compose-probe`
  para não contar o mesmo achado duas vezes.
