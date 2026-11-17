<!-- Exceção de idioma: documento em pt-BR a pedido do usuário. Ver § 8, Open Decision 4. -->

# Plano de Implementação — AEO/GEO em projetos de site e e-commerce

**Status:** Aprovado e implementado em 2026-11-16 (Abordagem 1) — evidência: ADR-0066, novas referências em `skills/design/seo-optimization/references/`; alterações não commitadas aguardando revisão
**Data:** 2026-11-16
**Base de evidências:** [`knowledge-base.md`](knowledge-base.md)
**ADR:** [ADR-0066](../adrs/0066-aeo-and-geo-are-covered-by-the-existing-seo-skill-extended-with-references-for-non-google-engines-ai-commerce-feeds-and-ai-visibility-measurement.md) (rascunho original em [`adr-draft.md`](adr-draft.md))

Este documento tem duas partes:

- **Parte A (§ 1–4)** — o que o time aplica em cada projeto de cliente (checklist técnico, por tipo de página, medição).
- **Parte B (§ 5–7)** — como embutir isso no `dev-team-agents` (abordagens, recomendação, passos).

---

## Achado de partida

O repositório **já cobre a maior parte do AEO/GEO "lado Google"**: `skills/design/seo-optimization/SKILL.md` tem uma seção § AI Search — AEO / GEO, tabela de bots por finalidade (`references/ai-crawlers.md`), agent readiness, schema de e-commerce, monitoramento; `agents/seo-specialist.md` roda o gate; `skills/shared/spawn-classifier/SKILL.md` já dispara o agente com "GEO", "AEO", "AI search". Portanto **o plano é estender, não criar uma segunda fonte de verdade**.

Lacunas encontradas (o que falta hoje):

| # | Lacuna | Evidência |
|---|---|---|
| G1 | Mecanismos fora do Google (ChatGPT search, Claude, Perplexity, Copilot) só aparecem como tokens de `robots.txt`; nada sobre como cada um encontra e cita conteúdo | `grep` sem ocorrências de IndexNow como sinal de frescor para Copilot, Bing AI Performance, etc. |
| G2 | Feeds para superfícies de IA além do Merchant Center: OpenAI Product Feed, UCP (`native_commerce`), Perplexity Merchant Program | `references/schema-ecommerce-local.md` só cita Merchant Center/GBP |
| G3 | Medição de tráfego de IA: canal GA4 **AI Assistant**, `utm_source=chatgpt.com`, Bing AI Performance, logs por bot verificado | `references/monitoring.md` § Analytics só fala de Landing page/Default channel |
| G4 | Guia por tipo de página (home, PLP, PDP, blog, FAQ) | Inexistente; hoje só há a tabela página → schema |
| G5 | Paridade feed ↔ página ↔ JSON-LD (preço/estoque) como verificação | Inexistente |
| G6 | Sinais fora do site (menções, reviews de terceiros) — achado de pesquisa mais forte, mas fora do escopo de dev | `SKILL.md` § Off-Page Signals só fala de backlinks |
| G7 | Fatos novos a atualizar: Google suportará AIPREF `__usage_ai-training` em 2027; Search Console Generative AI report liberado a todos em 2026-08-31 | `references/ai-crawlers.md` (verificado em 2026-11-04) não traz o item do Google |
| G8 | Nenhum ponto na fase de produto/descoberta pergunta a política de bots de IA, feeds e medição antes do build | `product-analyst` / NFR não mencionam |

---

# Parte A — Aplicação em projetos de cliente

## 1. Checklist técnico

Severidade segue o gate existente: só fatos [OFICIAL] podem ser `BLOCKER`; [INDÚSTRIA]/[ACADÊMICO] viram, no máximo, `ISSUE` ou recomendação.

### 1.1 Rastreio e política de bots de IA

| Item | Regra | Nível |
|---|---|---|
| Separar bots por finalidade | Busca/citação (`Googlebot`, `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`, `Bingbot`) ≠ treino (`GPTBot`, `ClaudeBot`, `Google-Extended`, `Applebot-Extended`, `CCBot`) ≠ fetch do usuário (`ChatGPT-User`, `Claude-User`, `Perplexity-User`, `Google-Agent`) | OFICIAL |
| Bloquear bot de **busca** em página indexável | Tira o site das respostas daquele mecanismo; `ISSUE` alto, a menos que seja decisão registrada do cliente | OFICIAL |
| Treino | Decisão de negócio do cliente; nunca padrão silencioso (regra já existente: perguntar) | OFICIAL |
| `robots.txt` responde `200`, nunca `5xx`/`429` | `5xx` persistente = disallow total | OFICIAL (RFC 9309) |
| WAF/CDN | Permitir pelos IPs publicados (`openai.com/searchbot.json`, `claude.com/crawling/bots.json`, `perplexity.ai/perplexitybot.json`); não bloquear por IP como política; "Bot Fight"/desafios não podem pegar bots de busca verificados | OFICIAL |
| Rotas privadas | Atrás de autenticação — fetchers de usuário podem ignorar `robots.txt` | OFICIAL |

Template de política a oferecer ao cliente (perguntado, nunca imposto): **"Busca sim, treino a decidir"** — grupos explícitos permitindo os bots de busca, grupo por token de treino conforme a resposta.

### 1.2 Renderização

- Conteúdo principal, título, canonical, preço, disponibilidade e JSON-LD **no HTML inicial** (SSR/SSG/ISR). Vários crawlers de IA não executam JS (`references/agent-readiness.md`).
- Reviews, preço e variações carregados só no cliente = achado `raw`.
- Links como `<a href>`; paginação com URLs reais.

### 1.3 Dados estruturados (JSON-LD)

| Tipo | Onde | Observação |
|---|---|---|
| `Organization` (+ `logo`, `sameAs`, `@id` estável) | Home / layout global | Consistência de entidade; um único `@id` reutilizado |
| `WebSite` | Home | |
| `BreadcrumbList` | PLP, PDP, blog | Igual ao breadcrumb visível |
| `Product` + `Offer` (`price`, `priceCurrency`, `availability`, `shippingDetails`, `hasMerchantReturnPolicy`) | PDP | Um `Offer` por variante comprável |
| `AggregateRating` / `Review` | PDP com reviews reais | Nunca reviews inventados ou incentivados |
| `Article`/`BlogPosting` (+ `author` → `ProfilePage`/`Person`) | Blog | `datePublished`, `dateModified` |
| `FAQPage` | Só Q&A visível de verdade | Sem rich result no Google; manter só se o conteúdo existir para o usuário |

Regra de comunicação: schema é justificado por **rich results, Merchant Center e consistência de entidade**. Não prometer "citação por IA" (CONTESTADO).

### 1.4 Feeds de produto (e-commerce)

| Destino | O que exige | Status |
|---|---|---|
| Google Merchant Center | Feed de produtos; UCP checkout via atributo `native_commerce` (EUA, comerciantes selecionados) | OFICIAL |
| OpenAI (ChatGPT) | Product Feed JSONL/CSV/TSV, snapshot completo, URL HTTPS/SFTP; `is_eligible_search`; checkout exige integração à parte | OFICIAL |
| Perplexity | Merchant Program | INDÚSTRIA — confirmar |

Regra de arquitetura: **um único gerador de catálogo** (mesma fonte de dados) produz JSON-LD da PDP, feed Google e feed OpenAI. Teste automatizado de **paridade** preço/estoque/URL/GTIN entre os três. Atualizar feed quando preço/estoque mudam (as duas especificações pedem dados atuais).

### 1.5 Frescor e descoberta

- `sitemap.xml` com `lastmod` real; enviado ao Search Console e ao Bing Webmaster Tools.
- **IndexNow** no publish/update/delete de PDP e artigos (Bing e participantes; Google não participa). Baixo custo, recomendado para e-commerce com estoque/preço voláteis.

### 1.6 Performance

Core Web Vitals em campo (p75) — limites e correções ficam em `skills/architecture/performance-budgets/SKILL.md`. Sem regra nova.

### 1.7 Conteúdo estruturado para extração de resposta

- Responder a pergunta principal cedo, em linguagem clara; headings descritivos; listas/tabelas reais para especificações e comparações.
- Afirmações verificáveis: números com fonte, especificações exatas, citações atribuídas (alinhado com o artigo KDD 2024 e com "non-commodity content" do Google).
- **Proibido:** páginas por variação de consulta/fan-out (abuso de escala), texto oculto ou "sequências estratégicas" para LLM (spam/manipulação), FAQ inventado.

### 1.8 Entidade, marca e E-E-A-T

- Página "Sobre", políticas (troca, frete, privacidade), contato real, autores com página própria.
- `Organization.sameAs` apontando perfis oficiais; nome da marca idêntico em site, feeds, GBP e marketplaces.
- **Fora do escopo de dev, mas sinalizar ao cliente:** reviews em plataformas de terceiros, imprensa, presença em comparativos — maior correlação com recomendação por IA (Ahrefs 2025; Chen et al. 2025).

### 1.9 Medição (ver § 3)

## 2. Guia por tipo de página

| Página | Objetivo AEO/GEO | Obrigatório | Evitar |
|---|---|---|---|
| **Home** | Definir a entidade | `Organization` + `WebSite` com `@id`; proposta de valor em texto (não só imagem); links rastreáveis para categorias; contato/políticas no rodapé | Conteúdo principal só em carrossel JS |
| **PLP / categoria** | Ser fonte para "melhor X para Y" | Texto introdutório curto e útil (critérios de escolha); `BreadcrumbList`; paginação com URL; facetas sem gerar URLs indexáveis infinitas (canonical/`noindex` conforme `references/crawl-index-control.md`) | Texto genérico gerado em massa; cada combinação de filtro indexável |
| **PDP** | Ser recomendado e citado com preço certo | `Product`/`Offer` completo no HTML inicial; especificações em tabela; fotos próprias; reviews reais (com `AggregateRating` só se visíveis); frete/troca visíveis; paridade com feeds; `OutOfStock` mantendo `200` | Descrição copiada do fabricante sem acréscimo; preço só via JS |
| **Blog / guia** | Ser citado em respostas informacionais | Autor identificado (`Person`/`ProfilePage`), datas, experiência de primeira mão, dados com fonte, links internos para PLP/PDP | Artigos em escala por palavra-chave; conteúdo "para IA" |
| **FAQ / central de ajuda** | Responder dúvidas de pré-venda e pós-venda | Perguntas reais (do SAC/busca interna), respostas diretas, uma pergunta por heading; `FAQPage` opcional | FAQ inventado em toda página só pelo markup |

## 3. Como medir

| Fonte | Mede | Quem roda | Nível |
|---|---|---|---|
| Search Console — Generative AI performance | Impressões em AI Overviews/AI Mode por página/país/dispositivo | Usuário (login) | OFICIAL |
| Search Console — Performance "Web" | Cliques/impressões, inclui IA | Usuário | OFICIAL |
| Bing Webmaster Tools — AI Performance | Citações em Copilot/Bing AI por *grounding query* e página (sem cliques) | Usuário | INDÚSTRIA (confirmar no produto) |
| GA4 — canal padrão **AI Assistant** | Sessões vindas de ChatGPT, Gemini, Copilot etc. (exclui AI Overviews/AI Mode) | Dev configura, usuário lê | OFICIAL |
| GA4 — canal customizado | `source` com regex para `perplexity|claude|chatgpt|copilot|gemini` acima de Referral, se o padrão não cobrir | Dev | Prática |
| `utm_source=chatgpt.com` | Atribuição de cliques do ChatGPT | Automático | OFICIAL |
| Logs de servidor / CDN | Hits por bot **verificado por IP** (busca vs treino vs user) e status code | Dev/DevOps | OFICIAL (listas de IP) |
| Merchant Center / Business Hub da OpenAI | Status de aprovação do feed, erros de item | Usuário | OFICIAL |
| Painel de prompts (ferramenta de terceiros ou amostragem manual) | Presença da marca em respostas para um conjunto fixo de perguntas | Marketing | OPINIÃO — direcional, nunca KPI de aceite |

KPIs sugeridos por projeto (linha de base no lançamento, revisão mensal): impressões em IA (GSC), sessões e conversão do canal AI Assistant, citações Bing, % de PDPs com paridade feed/página = 100%, % de templates com conteúdo principal no HTML bruto = 100%, erros de feed = 0.

## 4. Fora do escopo do time de dev

PR, campanhas de review, presença em marketplaces/comparativos, Wikipedia/Wikidata. O agente registra a recomendação para marketing/growth; não executa.

---

# Parte B — Embutir no dev-team-agents

## 5. Abordagens

### Abordagem 1 (recomendada) — Estender `seo-optimization` + `seo-specialist`

Novas referências dentro da skill existente, roteadas pela tabela § Conditional References; ajustes pequenos em `SKILL.md`; um gancho de descoberta no fluxo de produto.

- **Prós:** uma única fonte de verdade (regra "Canonical Rule Homes"); reaproveita o gate, a escala de severidade, a lista de alegações rejeitadas e o roteamento já existente no `spawn-classifier`; carregamento sob demanda mantém custo de token baixo; nenhum agente novo.
- **Contras:** a skill cresce (o `SKILL.md` tem 268 linhas, limite ~500 — as novidades vão para `references/`, que é isento); "GEO" continua sem uma pasta com o nome.

### Abordagem 2 — Nova skill `skills/design/aeo-geo/` com `references/`

- **Prós:** nome explícito e fácil de encontrar; pode ser carregada também por `product-analyst` e `frontend-developer` sem puxar todo o SEO.
- **Contras:** duplica a § AI Search, a tabela de bots e a política de schema; duas skills dizendo coisas sobre `llms.txt` e schema-para-IA vão divergir (o próprio `CLAUDE.md` registra que regras duplicadas já derivaram antes); conflita com a posição oficial de que AEO/GEO é SEO.
- **Por que não:** custo de manutenção e risco de contradição maiores que o ganho de nome.

### Abordagem 3 — Novo agente `geo-specialist`

- **Prós:** responsabilidade explícita; poderia cobrir também sinais fora do site.
- **Contras:** sobreposição quase total com `seo-specialist`; um gate a mais nos comandos; o trabalho fora do site não é de dev; aumenta roster, prompts e banners.
- **Por que não:** overengineering — o problema não pede um papel novo.

**Recomendação: Abordagem 1.** Coerente com a orientação oficial do Google (AEO/GEO é SEO), com a regra de fonte única do repositório e com YAGNI.

## 6. Plano — Estender a skill de SEO com AEO/GEO multi-mecanismo

### Context
O usuário quer aplicar AEO/GEO em sites e e-commerce feitos com o time. A skill de SEO já cobre o lado Google; faltam mecanismos fora do Google, feeds de IA, medição de tráfego de IA, guia por tipo de página e um gancho na descoberta (lacunas G1–G8).

### Scope
**In scope:**
- Novas referências em `skills/design/seo-optimization/references/`
- Ajustes em `skills/design/seo-optimization/SKILL.md` (Conditional References, § AI Search, Audit step 8, Off-Page)
- Atualização factual de `references/ai-crawlers.md`, `references/monitoring.md`, `references/schema-ecommerce-local.md`
- Uma linha de descoberta no fluxo do `product-analyst` (NFR/escopo) e uma linha no checklist de pronto do frontend
- ADR em inglês via `new-adr.sh` + linha no índice
- Entradas em `helpers/canonical-facts.json` para alegações erradas recorrentes

**Out of scope:**
- Novo agente ou nova skill de topo
- Ferramentas que chamem APIs externas (Search Console, Bing, OpenAI) — o gate continua sem rede
- Execução de PR/marketing
- Mudanças em instaladores, render engine ou hooks (nada provider-facing além do conteúdo de skill, que já chega igual aos três providers)

### Approach
Cada lacuna vira uma referência carregada sob demanda por um sinal na tabela § Conditional References, mantendo `SKILL.md` como índice e gate. Fatos entram em inglês, com URL e "as last verified 2026-MM-DD", reverificados na página primária no momento da escrita (itens marcados "confirmar" na base de conhecimento só entram se a leitura primária os confirmar). A escala de evidência da base de conhecimento já é a da skill (*heuristic* → `ISSUE`), então nada novo vira `BLOCKER` exceto o que é oficial e verificável no código: conteúdo/preço só em JS na PDP, e divergência de preço entre feed e JSON-LD gerada pelo mesmo código. Abordagens 2 e 3 rejeitadas (§ 5).

### Steps
| # | Action | Files / Areas Affected | Complexity | Par. |
|---|---|---|---|---|
| 1 | Criar `references/answer-engines.md`: como Google, Bing/Copilot, ChatGPT, Claude e Perplexity descobrem e citam conteúdo; IndexNow; o que cada um documenta; tabela de evidência (oficial vs estudo) incluindo GEO KDD 2024, Toronto 2025 e Kumar & Lakkaraju como alerta de manipulação | `skills/design/seo-optimization/references/answer-engines.md` | Medium | A |
| 2 | Criar `references/ai-commerce-feeds.md`: Merchant Center + UCP `native_commerce`, OpenAI Product Feed (campos obrigatórios, flags), Perplexity (só se confirmado), regra do gerador único e checagem de paridade feed ↔ JSON-LD ↔ página | `.../references/ai-commerce-feeds.md` | Medium | A |
| 3 | Criar `references/page-type-playbook.md`: home, PLP, PDP, blog, FAQ (tabela da § 2) | `.../references/page-type-playbook.md` | Low | A |
| 4 | Atualizar `references/monitoring.md` § Analytics: canal GA4 AI Assistant, canal customizado, `utm_source=chatgpt.com`, Search Console Generative AI report, Bing AI Performance, logs por bot verificado; painéis de prompt como direcionais | `.../references/monitoring.md` | Low | A |
| 5 | Atualizar `references/ai-crawlers.md`: intenção do Google de suportar AIPREF em 2027; recomendação explícita da OpenAI/Perplexity de permitir bots de busca; reverificar todas as linhas | `.../references/ai-crawlers.md` | Low | A |
| 6 | Atualizar `SKILL.md`: linhas novas em § Conditional References (sinais: "e-commerce feed/catalog export", "page template review", "non-Google AI engine named", "analytics setup"); § AI Search › What works ganha "Non-Google answer engines" (1–2 linhas apontando para step 1); Audit step 8 inclui paridade de feed e política de bot por finalidade; § Off-Page Signals cita menções de terceiros como advisory para marketing | `skills/design/seo-optimization/SKILL.md` | Medium | — |
| 7 | Gancho de descoberta: no fluxo do `product-analyst`, quando a Detection Signal de SEO bate, registrar como NFR/decisão aberta (a) política de bots de IA por finalidade, (b) destinos de feed, (c) medição de IA — sem restar regras, só apontando para a skill | `agents/product-analyst.md` (1–3 linhas) ou o template de NFR — decidir pelo menor ponto que já é carregado | Low | B |
| 8 | Checklist de pronto do frontend: uma linha "superfície pública → conteúdo principal, preço e JSON-LD no HTML inicial; rodar o gate de SEO" apontando para a skill | `skills/shared/frontend-done-checklist/SKILL.md` | Low | B |
| 9 | `helpers/canonical-facts.json`: adicionar formas erradas recorrentes (ex.: "llms.txt melhora ranking no Google", "Google-Extended remove de AI Overviews", "FAQPage gera rich result") se ainda não existirem | `helpers/canonical-facts.json` | Low | B |
| 10 | ADR em inglês via `bash scripts/new-adr.sh` a partir de `adr-draft.md`, com `**Applies to:**` e linha no `docs/development/adrs/README.md` | `docs/development/adrs/` | Low | — |
| 11 | Traduzir `knowledge-base.md` e este plano para inglês (ou registrar a exceção) conforme Open Decision 4 | `docs/development/aeo-geo/` | Low | — |
| 12 | Scoped review (regra do repositório): `code-reviewer` + `software-architect`; lints `agent-lint.sh`, `size-limits.sh`, `orphan-skill-scan.sh`, `canonical-facts.py`; testes escopados | — | Low | — |

Steps 1–5 (grupo A) podem ser enviados em paralelo; 7–9 (grupo B) em paralelo depois do step 6.

### Risks & Dependencies
- **Risk:** fatos de operadores mudam rápido (flags de feed, relatórios em preview) — **Mitigation:** cada linha com data de verificação; itens não confirmados na fonte primária ficam fora.
- **Risk:** inflar a skill e o custo de contexto — **Mitigation:** tudo novo em `references/`, carregado por sinal; `SKILL.md` ganha só linhas de roteamento.
- **Risk:** agente prometer "aparecer no ChatGPT" — **Mitigation:** a § Eligibility já proíbe prometer aparição; a nova referência repete o princípio por remissão, não por cópia.
- **Risk:** conflito com a regra de idioma do repositório — **Mitigation:** Open Decision 4.
- **Depends on:** aprovação deste plano e da Abordagem 1.
- **Assumption:** `seo-specialist` continua sendo o único dono do gate; nenhum provider exige tratamento especial para novos arquivos em `references/` (a árvore `skills/` já é entregue inteira a opencode e Codex e por pasta ao Claude Code).

### Definition of Done
- [ ] G1–G8 cobertos, cada fato com URL e data de verificação
- [ ] Nenhuma regra duplicada entre `SKILL.md` e as novas referências
- [ ] `SKILL.md` ≤ 500 linhas; descrições ≤ 95 caracteres
- [ ] `agent-lint.sh`, `size-limits.sh`, `orphan-skill-scan.sh`, `canonical-facts.py` passam
- [ ] ADR aceito e indexado
- [ ] Scoped review concluído

---
Awaiting your approval before proceeding.
Reply "approved" to execute or provide feedback to adjust.

After approving: steps that share the same Par. group letter can be sent as simultaneous agent prompts in a single message to run them in parallel and reduce total execution time.

## 7. Quem carrega o quê e quando

| Agente | Quando | O que carrega |
|---|---|---|
| `seo-specialist` | Gate obrigatório em superfície pública; `/devteam:seo` | `seo-optimization` + referências por sinal (novas: answer-engines, ai-commerce-feeds, page-type-playbook) |
| `product-analyst` | Descoberta de site/e-commerce | Só o gancho do step 7 (perguntas abertas sobre bots, feeds, medição) |
| `software-architect` | Decisão de stack de renderização e de pipeline de catálogo/feed | Base de conhecimento § 7 + `ai-commerce-feeds.md` (gerador único) |
| `frontend-developer` | Implementação de templates públicos | `frontend-done-checklist` (linha do step 8); correções vindas do gate |
| `backend-developer` | Geração de feeds, IndexNow, endpoints de catálogo | Recebe as linhas de achado do gate; sem skill nova |
| `devops-specialist` | WAF/CDN e logs por bot | `references/ai-crawlers.md` § Verifying a bot (já existe) |

## 8. Open Decisions

1. **Abordagem de integração** — (a) Estender `seo-optimization` + `seo-specialist` (**recomendada**); (b) nova skill `aeo-geo`; (c) novo agente `geo-specialist`.
2. **Aprovação do plano § 6** — Aprovar / Ajustar.
3. **Estratégia de execução** (gate obrigatório do arquiteto) — (a) worktree isolado (**recomendado**, mexe em skill compartilhada); (b) nova branch na árvore atual; (c) branch atual.
4. **Idioma dos documentos em `docs/development/aeo-geo/`** — `CLAUDE.md` § Language exige inglês salvo exceção marcada. (a) Manter pt-BR como exceção marcada e escrever as referências da skill em inglês (**recomendado** — a skill é o que é entregue; estes documentos são material de pesquisa); (b) traduzir para inglês e manter cópia `.pt-BR.md`, como em `docs/installation.md`; (c) só inglês.
5. **Gancho de descoberta (step 7)** — (a) uma linha no `product-analyst` (**recomendado**); (b) linha no template de NFR; (c) não incluir.
6. **Perplexity Merchant Program** — (a) incluir só após confirmar na página oficial (**recomendado**); (b) omitir.
