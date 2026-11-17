<!-- Rascunho em pt-BR. Ao aprovar, criar a versão em inglês com `bash scripts/new-adr.sh "..."` e adicionar a linha em docs/development/adrs/README.md (índice verificado mecanicamente, ADR-0038). Mantido fora de adrs/ para não quebrar o índice nem a regra de idioma enquanto é proposta. -->

> **Histórico:** rascunho substituído por [ADR-0066](../adrs/0066-aeo-and-geo-are-covered-by-the-existing-seo-skill-extended-with-references-for-non-google-engines-ai-commerce-feeds-and-ai-visibility-measurement.md) (Accepted, 2026-11-16). Mantido como registro.

# AEO e GEO são cobertos pela skill de SEO existente, estendida com referências para mecanismos fora do Google, feeds de IA e medição

**Status**: Superseded by ADR-0066
**Date**: 2026-11-16
**Deciders**: maintainers do dev-team-agents; `software-architect`
**Applies to**: `skills/design/seo-optimization/**`, `agents/seo-specialist.md`, `skills/shared/frontend-done-checklist/SKILL.md`

## Context

Projetos de site e e-commerce feitos com o time precisam aparecer em respostas de IA (AI Overviews/AI Mode do Google, ChatGPT, Claude, Perplexity, Copilot). O repositório já tem `skills/design/seo-optimization` com uma seção AEO/GEO alinhada ao guia oficial do Google, que trata AEO/GEO como SEO comum. Faltam: mecanismos fora do Google, feeds de produto para superfícies de IA (Merchant Center/UCP, Product Feed da OpenAI), medição de tráfego de IA (canal GA4 AI Assistant, `utm_source=chatgpt.com`, Search Console Generative AI report, Bing AI Performance), guia por tipo de página e paridade feed ↔ página. O `CLAUDE.md` exige uma fonte única por regra. Evidências em `docs/development/aeo-geo/knowledge-base.md`.

## Decision

Vamos estender `seo-optimization` com novas referências carregadas por sinal (`answer-engines.md`, `ai-commerce-feeds.md`, `page-type-playbook.md`) e atualizar `ai-crawlers.md`, `monitoring.md` e `SKILL.md`. `seo-specialist` continua dono do gate. Não haverá skill nem agente separados para AEO/GEO. Só fatos de documentação oficial podem gerar `BLOCKER`; estudos acadêmicos e de mercado orientam prioridade e no máximo geram `ISSUE`. Sinais fora do site (menções, reviews de terceiros) ficam como recomendação para marketing.

## Rationale

- O Google declara que não há requisitos adicionais para recursos de IA; separar "GEO" de "SEO" criaria duas fontes para os mesmos fatos (`llms.txt`, schema, bots).
- O roteamento existente (`spawn-classifier`, Detection Signals, `/devteam:seo`) já dispara o agente certo para "AEO/GEO".
- Referências sob demanda mantêm o custo de contexto baixo.

## Alternatives Considered

### Option A — Nova skill `skills/design/aeo-geo/`
- **Pros**: nome explícito; carregável por outros agentes isoladamente.
- **Cons**: duplica § AI Search e a política de bots; risco de divergência já observado no repositório.
- **Why rejected**: viola a regra de fonte única sem ganho funcional.

### Option B — Novo agente `geo-specialist`
- **Pros**: responsabilidade explícita.
- **Cons**: sobreposição com `seo-specialist`; mais um gate; trabalho fora do site não é de dev.
- **Why rejected**: overengineering.

## Consequences

**Positive**: um gate único cobre SEO, AEO e GEO; projetos de e-commerce ganham checagem de feed e paridade; medição de IA passa a ser configurada no build.
**Negative**: `seo-optimization` cresce em referências; o termo "GEO" não tem pasta própria (mitigado pelo roteamento por palavra-chave existente).
**Risks**: fatos de operadores mudam rápido — cada linha carrega data de verificação e itens não confirmados na fonte primária ficam fora.
