# Eixo D — Agentes e Skills

**Data:** 2026-07-31 · **Baseline:** `f54569a`

---

## Contexto medido

`helpers/size-limits.sh` passa limpo: 17/17 agentes ≤ 200, 25/25 comandos ≤ 200, 142/142 skills
≤ 500. Os limites que o repo declara estão todos respeitados — este eixo é sobre o que os limites
não capturam.

Dez skills passam de 200 linhas **sem** um diretório `references/` (20 skills no repo já têm um):

| Linhas | Skill | Loaders |
|---|---|---|
| 437 | `skills/shared/migration-v1-to-v2/SKILL.md` | **1** |
| 244 | `skills/devops/graphify-setup/SKILL.md` | — |
| 237 | `skills/shared/backlog-template/SKILL.md` | 1 (condicional, corrigido nesta janela) |
| 222 | `skills/integrations/database-production/SKILL.md` | — |
| 221 | `skills/mobile/material-design/SKILL.md` | — |
| 220 | `skills/architecture/llm-integration/SKILL.md` | — |
| 218 | `skills/mobile/ios-hig/SKILL.md` | — |
| 216 | `skills/integrations/supabase/SKILL.md` | — |
| 209 | `skills/shared/interaction-patterns/SKILL.md` | **26** → ver Eixo E |
| 206 | `skills/integrations/jwt/SKILL.md` | — |

Sete das dez são skills de referência específicas de plataforma (`integrations/*`, `mobile/*`,
`devops/*`) — exatamente a categoria que o `CLAUDE.md` isenta por design, carregada só quando a
detecção dispara. Não são achado. As duas anômalas são a primeira e a penúltima da lista, e ambas
estão em `skills/shared/`.

---

## MEDIUM

### A maior skill do repositório é um manual de migração de 437 linhas com um único carregador

- **Fingerprint:** `skill-shared-migration-v1-to-v2-437-lines-largest-in-repo-single-conditional-loader-in-setup-assistant-no-references-extraction-and-no-retirement-criterion`
- **Alvo:** `skills/shared/migration-v1-to-v2/SKILL.md`
- **Evidência:**
  `wc -l skills/shared/migration-v1-to-v2/SKILL.md` → **437** — a maior skill do repo, 43% acima da
  segunda (`project-context`, 309) e 87% acima do limite típico de referência.
  Carregadores: **um**. `grep -rn 'migration-v1-to-v2' agents/ commands/ skills/ CLAUDE.md` retorna
  apenas `agents/setup-assistant.md:172` — uma linha de tabela condicional: "The project shows v1
  layout signals — agents as files in `.claude/agents/` rather than symlinks … | Load
  `skills/shared/migration-v1-to-v2/SKILL.md` and follow it."
  Sem `references/`: `find skills/shared/migration-v1-to-v2 -type d -name references` → vazio.
- **Problema:** é um procedimento pontual — migrar um projeto de v1 para v2 — mantido como skill de
  primeira classe em `skills/shared/`, o diretório reservado a "foundational rules used by all
  agents" (`CLAUDE.md:242`). Ela não é fundacional e não é usada por todos os agentes: é usada por
  um, uma vez por projeto, e apenas em projetos que ainda estão em v1.
- **Por que importa:** o custo não é de contexto — a carga é condicional e raramente dispara. O
  custo é de **manutenção sem critério de saída**. Toda mudança estrutural no v2 (caminhos de
  símbolo, hooks, layout de `user-data/`) invalida partes destas 437 linhas, e nada sinaliza isso:
  `helpers/orphan-skill-scan.sh` a vê referenciada e passa limpo, `size-limits.sh` a vê sob 500 e
  passa limpo. Ela envelhece em silêncio, e o único momento em que alguém descobre que envelheceu é
  durante uma migração real — o pior momento possível. O repo não registra em lugar nenhum quando
  esta skill deve ser aposentada.
- **Proposta:** duas mudanças independentes. (a) Extrair para `references/` os blocos
  procedimentais longos (passos de repointar símbolos, tabela de equivalência de caminhos v1→v2),
  deixando no `SKILL.md` o gate de detecção e o roteiro de alto nível — o padrão que
  `skills/integrations/gotrue/` já adotou nesta janela (225 → 73 linhas). (b) Registrar no topo da
  skill um **critério de aposentadoria** explícito, no formato "remover quando `<condição>`" — por
  exemplo, uma versão-alvo do `CHANGELOG.md` a partir da qual instalações v1 deixam de ser
  suportadas.
- **Impacto positivo:** o `SKILL.md` cai para a faixa dos ~80-120 linhas dos demais roteiros
  condicionais; o critério de saída transforma um item de manutenção perpétua em um item com data.
- **Impacto negativo / risco:** real. Durante uma migração, um procedimento fragmentado em
  `SKILL.md` + `references/` custa uma leitura a mais em um momento em que o agente está mexendo em
  símbolos e hooks de um projeto do usuário — o caminho onde um passo perdido quebra a instalação.
  O ganho de manutenção é para o mantenedor; o custo é para o usuário migrando. Se a extração for
  feita, o `SKILL.md` precisa manter a **sequência completa** dos passos e delegar só o detalhe de
  cada um.
- **Esforço:** Médio

---

## Nenhum achado original nos demais sub-eixos

- **Regra duplicada sem casa canônica:** a tabela *Canonical Rule Homes* do `CLAUDE.md:151-161`
  cobre as sete regras que estavam duplicadas, e a Fase 1 verificou ✅ a consolidação de duas delas
  (Foundational Rule em 17 agentes, "project rules override" em 14). Uma varredura por outras
  regras repetidas em ≥3 agentes não produziu candidato que sobrevivesse à Porta 3 — os
  reincidentes (`comments-policy`, SonarQube, `docs-sync`) já estão registrados no banco.
- **Agente acima do limite de linhas:** zero. Maior é `agents/security-specialist.md` com 198.
- **Sobreposição de responsabilidades:** o par que motivava a suspeita —
  `security-specialist` × `qa-specialist` sobre `security-checklist` — foi particionado nesta
  janela (verificado ✅ na Fase 1: `agents/security-specialist.md:32` "security-audit column only";
  `agents/qa-specialist.md:39` com gate de detecção). Nenhum outro par apresenta carga eager da
  mesma skill sem fronteira declarada.
- **Cobertura faltante:** `skills/testing/` ganhou três skills nesta janela (`load-testing`,
  `decoupled-frontend`, `frontend-hook-tests`) e `skills/security/` ganhou `dependency-audit`. As
  lacunas que o banco registrava nesses domínios foram fechadas.
