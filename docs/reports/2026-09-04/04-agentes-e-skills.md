# Eixo D — Agentes e skills (2026-09-04)

**Data:** 2026-09-04 · **Baseline:** `HEAD` = `a67cac9`

---

## Nenhum achado original neste eixo

A varredura rodou e não rendeu achado original com evidência. Registro o que foi verificado, para que
o próximo pass não refaça o mesmo caminho.

### O que foi checado

| Checagem | Comando / evidência | Resultado |
|---|---|---|
| Limites de tamanho de agentes | `bash helpers/size-limits.sh` | 18/18 agentes dentro de `AGENT_LIMIT=211`; nenhuma violação de agente |
| Limites de skills | idem | 152/152 skills dentro de 500 linhas |
| Limites de comandos | idem | 35/35 comandos dentro de 200 linhas |
| Frontmatter de agentes (`name`/`description`/`tier`/`model`/`effort`) | `bash helpers/agent-lint.sh` | `clean ✓` |
| Espelho `tiers.json` ↔ `model:` ↔ run-banner | idem (`agent-lint` falha em qualquer divergência) | íntegro |
| Identidade de skills (`name` == basename do diretório, unicidade entre categorias) | idem | íntegro |
| Roster de orquestração ↔ `agents/` (nome e tier, nos dois sentidos) | idem | íntegro |
| Orçamento de 95 caracteres nas descrições de skill | script Python sobre os 152 `SKILL.md` | **0 acima do orçamento** |
| Cargas duplicadas de skill | `bash helpers/orphan-skill-scan.sh` | 3 reportadas, **todas falsos positivos já registrados** (ver Eixo B) |
| Skills órfãs (sem agente/comando que carregue) | idem | nenhuma |

### Candidatos levantados e por que caíram

**`agents/setup-assistant.md` — três papéis em um agente.** Levantado, mas verificado na Fase 1 deste
pass como **✅ Feito**: `b4e219f` cortou 106 linhas e `:169-172` hoje delega explicitamente ("Do not
restate either procedure here; load it and follow it"). Não é achado.

**`agents/devops-specialist.md:81` — restatement parcial da tabela de detecção do SonarQube.** É o
sub-escopo pendente de `token-sonarqube-detection-block-redundant`, reconfirmado 🟡 na Fase 1. Porta
5: já registrado, não implementado.

**`skills/architecture/orchestration/SKILL.md` — 391 linhas sem `references/`.** Porta 5, já no
conjunto aberto. Mesmo para `skills/shared/interaction-patterns/SKILL.md` (209 linhas × 34
consumidores), `skills/shared/token-efficiency/SKILL.md` (160 × 18) e
`skills/shared/migration-v1-to-v2/SKILL.md` (438 linhas).

**Três agentes exatamente no teto de 211 linhas.** Registrado como
`agent-three-at-exactly-211-line-ceiling-zero-headroom-for-additions` (LOW, aberto). Porta 5.

**Teto documentado (205) divergente do enforçado (211).** `CLAUDE.md:92` e `:313` afirmam que
`helpers/size-limits.sh` "enforces 205"; `helpers/size-limits.sh:44` tem `AGENT_LIMIT=211`. É um
achado real e HIGH — e está registrado desde 2026-08-14 como
`agent-line-cap-205-documented-in-claude-md-vs-211-enforced-by-size-limits`, ainda aberto. Porta 5.

---

## Leitura do eixo

Zero achados aqui é o resultado esperado, não uma anomalia. Este eixo depende de **mudança** para
render: regras que derivam entre agentes, skills que crescem além do ponto de extração, agentes que
estouram o teto. Nada disso pode ter acontecido — `git diff --stat a67cac9..HEAD` é vazio, e os
passes de 2026-08-21 e 2026-08-28 já varreram esta mesma árvore.

O que o eixo devolve, em vez de achados, é a confirmação de que **todos os gates de autoria passam**
com uma única exceção (`size-limits.sh` saindo 1 por causa do `CLAUDE.md`, que é um bug do próprio
gate já registrado como HIGH). A disciplina de autoria está mecanicamente sustentada; o passivo do
eixo é backlog não executado, não deriva nova.
