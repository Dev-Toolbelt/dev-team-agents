<!-- Exceção de idioma: documento em pt-BR a pedido do usuário. Ver Open Decision 4 em implementation-plan.md § 8 sobre a versão canônica em inglês. -->

# Base de Conhecimento — AEO e GEO para sites e e-commerce

**Status:** Implementado — ver ADR-0066 (2026-11-16)
**Data de acesso de todas as fontes:** 2026-11-16 (salvo indicação em contrário)
**Autor:** `software-architect` (modo planejamento)
**Uso:** referência para o time ao planejar, construir e revisar sites institucionais, landing pages, blogs e lojas virtuais. Complementa — não substitui — `skills/design/seo-optimization/SKILL.md`, que já é a fonte normativa do gate de SEO.

---

## 1. Definições e modelo mental

| Sigla | Ideia (segundo o briefing do usuário) | Superfícies | O que de fato decide |
|---|---|---|---|
| **SEO** | "Você na lista" | Links azuis do Google/Bing | Rastreio, indexação, ranqueamento |
| **AEO** — Answer Engine Optimization | "Você na resposta" | AI Overviews e AI Mode do Google, respostas do Bing/Copilot, featured snippets | As mesmas etapas do SEO + elegibilidade a snippet + o sistema escolher sua página como fonte de apoio |
| **GEO** — Generative Engine Optimization | "A IA recomenda você" | ChatGPT (search e shopping), Claude, Gemini, Perplexity, Copilot | Índice próprio de cada operador (ou índice de terceiros), feeds de produto, menções de terceiros sobre a marca, e o que o modelo já aprendeu no treino |

**Conclusão principal (oficial):** para o Google, AEO/GEO **é SEO**. Os recursos de IA da Busca usam os mesmos sistemas de ranqueamento e qualidade, e "não há requisitos adicionais para aparecer em AI Overviews ou AI Mode" ([Google — AI features and your website](https://developers.google.com/search/docs/appearance/ai-features); [Google — AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)). Fora do Google, cada operador tem seu crawler de busca, e para produtos existe um canal adicional — **feeds de produto** — que não passa por HTML.

O que o termo "GEO" acrescenta na prática, além de SEO:

1. **Acesso dos crawlers de busca de IA** (OAI-SearchBot, Claude-SearchBot, PerplexityBot) — um `robots.txt` que bloqueia "bots de IA" no atacado tira o site das respostas.
2. **Feeds de produto para superfícies de IA** (Merchant Center/UCP, Product Feed da OpenAI, Perplexity Merchant Program).
3. **Sinais fora do site** (menções de terceiros, reviews, imprensa) — evidência correlacional forte, mas é trabalho de marketing/PR, não do time de desenvolvimento.
4. **Medição separada** — relatórios próprios por mecanismo, sem uma métrica unificada.

---

## 2. Níveis de evidência usados neste documento

| Nível | Significado | Pode virar regra de gate? |
|---|---|---|
| **[OFICIAL]** | Documentação do operador do mecanismo ou de um padrão (Google, Microsoft/Bing, OpenAI, Anthropic, Perplexity, schema.org, IndexNow, RFC) | Sim |
| **[ACADÊMICO]** | Artigo revisado por pares ou preprint de pesquisa | Não diretamente — resultados de laboratório em mecanismos sintéticos ou de um momento específico |
| **[INDÚSTRIA]** | Estudo de dados de empresa reconhecida (Ahrefs, Pew, Seer, Semrush, Search Engine Land) | Não — orienta prioridade, nunca vira `BLOCKER` |
| **[OPINIÃO]** | Declaração de palco, post de praticante, ferramenta vendendo métrica | Não — registrar só como contexto |
| **[CONTESTADO]** | Fontes de nível alto discordam ou a evidência é fraca | Não — documentar os dois lados |

Essa escala é compatível com a regra já existente na skill de SEO: um número *heurístico* pode gerar `ISSUE`, nunca `BLOCKER`, e alegações de terceiros sem fonte primária são rejeitadas (`skills/design/seo-optimization/SKILL.md` § AI Search › Rejected third-party claims).

---

## 3. O que é oficial (por operador)

### 3.1 Google (Busca, AI Overviews, AI Mode, Gemini)

| Fato | Fonte |
|---|---|
| [OFICIAL] Recursos de IA da Busca usam os sistemas centrais de ranqueamento e qualidade; manter o básico de SEO | [AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide) |
| [OFICIAL] Elegibilidade: página indexada e elegível a aparecer **com snippet**; "There are no additional requirements" | [AI features and your website](https://developers.google.com/search/docs/appearance/ai-features) |
| [OFICIAL] Controles: `noindex`, `nosnippet`, `data-nosnippet`, `max-snippet` limitam o uso; `robots.txt` para Googlebot controla o rastreio | Mesma página |
| [OFICIAL] `llms.txt`, arquivos "de IA" e Markdown não são usados pela Busca — nem ajudam nem atrapalham | AI optimization guide |
| [OFICIAL] Não é preciso "chunking" de conteúdo; "There's no ideal page length" | AI optimization guide |
| [OFICIAL] "Structured data isn't required for generative AI search"; não existe schema especial para IA. Continuar usando para rich results | AI optimization guide |
| [OFICIAL] *Query fan-out*: o modelo gera consultas relacionadas concorrentes. Criar páginas para cada consulta de fan-out é abuso de conteúdo em escala | AI optimization guide |
| [OFICIAL] Buscar "menções" inautênticas é contraproducente | AI optimization guide |
| [OFICIAL] Conteúdo útil, confiável e feito para pessoas; E-E-A-T (experiência, especialidade, autoridade, confiança) | [Creating helpful content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content); [Search Quality Rater Guidelines](https://guidelines.raterhub.com/searchqualityevaluatorguidelines.pdf) |
| [OFICIAL] Dados estruturados devem corresponder ao conteúdo visível | [Structured data general guidelines](https://developers.google.com/search/docs/appearance/structured-data/sd-policies) |
| [OFICIAL] `Google-Extended` controla treino e *grounding* do Gemini/Vertex; **não** afeta inclusão nem ranqueamento na Busca nem AI Overviews | [Google's common crawlers](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers) |
| [OFICIAL] Google declara intenção de suportar o sinal AIPREF `User-Agent: __usage_ai-training` no início de 2027 | Resultado de busca em developers.google.com (página de crawlers); **reverificar antes de codificar** |
| [OFICIAL] Relatório "Generative AI performance" no Search Console: impressões em AI Overviews e AI Mode, por página/país/data/dispositivo; liberado a todos os sites em 2026-08-31 | [Search Console Help 16984139](https://support.google.com/webmasters/answer/16984139) |
| [OFICIAL] Tráfego de AI Overviews/AI Mode também entra no relatório de Performance, tipo "Web" | AI features and your website |
| [OFICIAL] Produtos entram nas respostas de IA via **Merchant Center**; negócio local via **Google Business Profile** | AI optimization guide |
| [OFICIAL] **Universal Commerce Protocol (UCP)**: botão de checkout em listagens elegíveis no AI Mode e no Gemini, com atributo `native_commerce`; disponível para comerciantes selecionados nos EUA | [Merchant Center Help 16837055](https://support.google.com/merchants/answer/16837055); [UCP onboarding 16992327](https://support.google.com/merchants/answer/16992327); [developers.google.com/merchant/ucp](https://developers.google.com/merchant/ucp) |
| [OFICIAL] Ferramentas de terceiros não têm acesso aos sistemas internos do Google | [Third-party SEO tools](https://developers.google.com/search/docs/fundamentals/third-party-seo) |

### 3.2 Microsoft (Bing, Copilot)

| Fato | Fonte |
|---|---|
| [OFICIAL] IndexNow: protocolo de push de URLs alteradas/novas/removidas; arquivo-chave no host; até 10.000 URLs por POST; mecanismos participantes compartilham as URLs entre si. Google não é participante | [IndexNow documentation](https://www.indexnow.org/documentation) |
| [OFICIAL] Bing Webmaster Tools "AI Performance" (preview público desde fev/2026): citações em Copilot e resumos de IA do Bing por *grounding query* e por página; **sem dados de clique**; não cobre ChatGPT, Perplexity nem Google | [Search Engine Land](https://searchengineland.com/bing-webmaster-tools-testing-new-ai-performance-report-468039) [INDÚSTRIA, reportando o produto]; confirmar em [bing.com/webmasters](https://www.bing.com/webmasters/) |
| [OPINIÃO de porta-voz] Fabrice Canel (Bing) afirmou na SMX Munich 2025 que schema ajuda os LLMs da Microsoft a entender o conteúdo e recomendou IndexNow para frescor | [Search Engine Land](https://searchengineland.com/microsoft-bing-copilot-use-schema-for-its-llms-453455) |

### 3.3 OpenAI (ChatGPT search, shopping)

| Fato | Fonte |
|---|---|
| [OFICIAL] `OAI-SearchBot` — aparece no ChatGPT search; "we recommend allowing OAI-SearchBot"; mudanças levam ~24 h | [OpenAI bots](https://developers.openai.com/api/docs/bots) |
| [OFICIAL] `GPTBot` — treino; bloquear não remove da busca | Mesma página |
| [OFICIAL] `ChatGPT-User` — ações iniciadas pelo usuário; regras do `robots.txt` podem não se aplicar | Mesma página |
| [OFICIAL] `OAI-AdsBot` — verifica landing pages de anúncios | Mesma página |
| [OFICIAL] ChatGPT adiciona `utm_source=chatgpt.com` nos links de referência | [Publishers and developers FAQ](https://help.openai.com/en/articles/12627856-publishers-and-developers-faq) |
| [OFICIAL] Product Feed: JSONL/CSV/TSV, snapshot completo, via upload, URL HTTPS ou SFTP; campos obrigatórios `item_id`, `title`, `description`, `url`, `brand`, `seller_name`, `image_url`, `availability`, `price`, `target_countries`, `store_country`; flag `is_eligible_search` (padrão `true`) e `is_eligible_checkout` (padrão desabilitado, exige integração própria) | [Submit product feeds](https://developers.openai.com/commerce/guides/submit-product-feeds); [Product feed schema](https://developers.openai.com/commerce/specs/file-upload/products) |
| [OFICIAL] Cadastro via Business Hub / "Businesses in ChatGPT" | [openai.com/business/businesses-in-chatgpt](https://openai.com/business/businesses-in-chatgpt/) |
| [CONTESTADO] Taxas sobre vendas e se checkout influencia ranqueamento — relatos de terceiros conflitam; nada oficial encontrado sobre ranqueamento | Cobertura de imprensa; não usar como regra |

### 3.4 Anthropic (Claude)

| Fato | Fonte |
|---|---|
| [OFICIAL] `ClaudeBot` (treino), `Claude-SearchBot` (indexação para busca), `Claude-User` (busca disparada pelo usuário). Todos respeitam `robots.txt` e `Crawl-delay`. Bloquear `Claude-SearchBot`/`Claude-User` pode reduzir visibilidade nas respostas | [Anthropic — crawler policy](https://support.claude.com/en/articles/8896518) |
| [OFICIAL] Desde 2026-10-30 reconhece sinal de opt-out de treino baseado em draft IETF; um grupo `ClaudeBot` explícito tem prioridade | Mesma página |
| [OFICIAL] Lista de IPs: `claude.com/crawling/bots.json`; não bloquear por IP | Mesma página |

### 3.5 Perplexity

| Fato | Fonte |
|---|---|
| [OFICIAL] `PerplexityBot` indexa para resultados de busca, não para treino; recomendação: permitir no `robots.txt` e nos IPs publicados | [Perplexity crawlers](https://docs.perplexity.ai/docs/resources/perplexity-crawlers) |
| [OFICIAL] `Perplexity-User` — buscas do usuário; geralmente ignora `robots.txt` | Mesma página |
| [INDÚSTRIA] Perplexity Merchant Program (nov/2024) para dados de produto; critério de ranqueamento não publicado | [Shopify — Perplexity shopping](https://www.shopify.com/blog/perplexity-shopping); confirmar no site da Perplexity antes de usar |

### 3.6 Padrões e propostas

| Item | Status | Fonte |
|---|---|---|
| [OFICIAL] RFC 9309 (Robots Exclusion Protocol) | Padrão | [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309) |
| [OFICIAL] schema.org — `Organization`, `Product`, `Offer`, `AggregateRating`, `Review`, `BreadcrumbList`, `Article`, `FAQPage` | Vocabulário | [schema.org](https://schema.org/) |
| [CONTESTADO] `llms.txt` | Proposta comunitária; Google declara que não usa; Ahrefs (jun/2026, 137 mil domínios) achou 97% dos arquivos sem nenhuma requisição em maio/2026, mas alguns agentes (ex.: ferramentas de código) leem | [llmstxt.org](https://llmstxt.org/); [Ahrefs llms.txt study](https://ahrefs.com/blog/llmstxt-study/) |
| [CONTESTADO] IETF AIPREF (`draft-ietf-aipref-vocab`, `-attach`) | Drafts de working group, sem RFC | [IETF AIPREF](https://datatracker.ietf.org/wg/aipref/documents/) |
| [OFICIAL, experimental] Lighthouse "Agentic Browsing" | Diagnóstico de laboratório, não sinal de ranqueamento | Já documentado em `skills/design/seo-optimization/references/agent-readiness.md` |

---

## 4. Evidência acadêmica

| Trabalho | O que mostra | Limites |
|---|---|---|
| [ACADÊMICO] Aggarwal et al., **"GEO: Generative Engine Optimization"**, KDD 2024 — [arXiv 2311.09735](https://arxiv.org/abs/2311.09735) | Benchmark GEO-bench. Adicionar citações (*Quotation Addition*) e estatísticas aumentou a visibilidade medida até ~40% (Position-Adjusted Word Count +41%); *Cite Sources* e fluência também ajudaram; *keyword stuffing* piorou (−8,7%). Ganho maior para sites mal posicionados (rank 5: +115% com *Cite Sources*; rank 1 chegou a perder visibilidade). Efeito varia por domínio. No Perplexity.ai real: +22% com citações | Mecanismo de geração sintético e de 2023–2024; métricas de "visibilidade" definidas pelos autores; não mede nenhum mecanismo atual. A skill de SEO já rejeita importar esses percentuais como meta |
| [ACADÊMICO] Chen, Wang, Chen, Koudas, **"Generative Engine Optimization: How to Dominate AI Search"** (U. Toronto, set/2025) — [arXiv 2509.08919](https://arxiv.org/abs/2509.08919) | Mecanismos de IA mostram viés forte e consistente para **mídia conquistada** (fontes terceiras, autoritativas) sobre conteúdo da própria marca, mais que o Google tradicional | Preprint; razões numéricas citadas em resumos de terceiros não foram confirmadas no texto |
| [ACADÊMICO] Kumar e Lakkaraju, **"Manipulating Large Language Models to Increase Product Visibility"** (2024) — [arXiv 2404.07981](https://arxiv.org/abs/2404.07981) | Sequências de texto estratégicas na página de produto podem colocar o produto no topo da recomendação de um LLM | Mostra **vulnerabilidade**, não prática recomendada — é manipulação e se enquadra em spam; usar só como alerta (texto oculto/injeção é proibido) |

**Leitura do arquiteto:** a pesquisa acadêmica sustenta que *conteúdo verificável* (citações, números com fonte, linguagem clara) e *reputação em terceiros* aumentam a chance de ser usado como fonte. Ela não sustenta metas numéricas, contagem de palavras ou "pontuação GEO".

---

## 5. Estudos da indústria (orientam prioridade, não são regra)

| Estudo | Achado | Ressalva |
|---|---|---|
| [INDÚSTRIA] Pew Research Center, jul/2025 — [link](https://www.pewresearch.org/short-reads/2025/07/22/google-users-are-less-likely-to-click-on-links-when-an-ai-summary-appears-in-the-results/) | Com resumo de IA, cliques em resultado tradicional caem de 15% para 8% das visitas; clique no link dentro do resumo ~1%; 18% das buscas tinham resumo | 900 adultos dos EUA, março/2025; Google contestou a metodologia |
| [INDÚSTRIA] Ahrefs, fev/2026 — [AI Overviews reduce clicks (update)](https://ahrefs.com/blog/ai-overviews-reduce-clicks-update/) | AI Overview associado a CTR 58% menor para a posição 1 (dez/2025); estudo anterior (abr/2025) dava 34,5%; Seer Interactive e Authoritas na mesma direção | Correlacional |
| [INDÚSTRIA] Ahrefs, mai/2025 — [AI Overview brand correlation](https://ahrefs.com/blog/ai-overview-brand-correlation/) | Menções da marca na web têm a maior correlação com visibilidade em AI Overviews (Spearman 0,664 vs 0,218 de backlinks) | Correlação ≠ causa; casa com o artigo de Toronto (mídia conquistada) |
| [INDÚSTRIA] Ahrefs, jun/2026 — [llms.txt study](https://ahrefs.com/blog/llmstxt-study/) | 97% dos `llms.txt` sem requisição | Amostra enviesada para sites técnicos |
| [INDÚSTRIA] Google Analytics — canal padrão **AI Assistant** (ChatGPT, Gemini, Deepseek, Copilot, Grok; exclui AI Overviews/AI Mode); regra: `medium` = `ai-assistant` | [GA4 default channel group](https://support.google.com/analytics/answer/9756891) [OFICIAL] | Tráfego sem referrer cai em Direct; Perplexity/Claude podem precisar de canal customizado — verificar no relatório do projeto |

---

## 6. Pontos contestados — posição recomendada

| Tema | Lado A | Lado B | Posição para o time |
|---|---|---|---|
| Schema afeta citação por LLM? | Microsoft (Canel) diz que ajuda seus LLMs [OPINIÃO de porta-voz] | Google: não é necessário para IA [OFICIAL]; testes controlados de terceiros não acharam ganho de citação [INDÚSTRIA] | Implementar schema **pelos rich results, pelo Merchant Center e pela consistência de entidade** — nunca vender como "otimização para IA" |
| `llms.txt` | Proposta llmstxt.org; alguns agentes de código leem | Google não usa; logs mostram quase zero leitura | Opcional, barato, nunca gate. Só quando o cliente pedir ou o site for de documentação/API |
| Bloquear bots de IA | Proteção de conteúdo/treino | Bloquear bots de busca tira o site das respostas | Separar por finalidade: **busca/citação** vs **treino** vs **fetch do usuário**. Decisão é do cliente, nunca padrão silencioso (regra já existente em `references/ai-crawlers.md`) |
| "Escrever para IA" (blocos curtos, FAQ em toda página) | Popular em blogs de GEO | Google: não é preciso; abuso de escala é spam | Estruturar para leitura humana: resposta cedo, headings descritivos, dados com fonte |
| Pontuação "GEO/AI visibility" de ferramentas | Ferramentas vendem | Nenhum operador publica tal métrica | Usar ferramentas de painel de prompts só como amostragem direcional, nunca como KPI de aceite |

---

## 7. Implicações para o time de desenvolvimento

1. **Nada de "camada GEO" separada.** O trabalho técnico é o SEO correto + política de bots por finalidade + feeds + medição.
2. **E-commerce tem um canal extra de alto valor:** feeds (Merchant Center/UCP, OpenAI Product Feed, Perplexity). O feed precisa sair do mesmo modelo de dados que alimenta o JSON-LD da PDP — preço/estoque divergentes entre feed, página e schema é o erro mais caro.
3. **Conteúdo verificável** (especificações reais, fotos próprias, reviews verdadeiros, autor identificado, números com fonte) é o que a pesquisa e o Google apontam juntos.
4. **Sinais fora do site** (imprensa, reviews em terceiros, presença em comparativos) têm a maior correlação com recomendação, mas pertencem a marketing/PR — o time de dev deve sinalizar, não executar.
5. **Medição em quatro fontes**, sem número único: Search Console (Generative AI performance), Bing AI Performance, GA4 canal AI Assistant + `utm_source=chatgpt.com`, logs de servidor por bot verificado.

---

## 8. Validade e manutenção

- Operadores mudam tokens, flags de feed e relatórios com frequência; cada fato com fonte deve ser **reverificado** quando for codificado em skill (padrão "as last verified AAAA-MM-DD" já usado em `skills/design/seo-optimization/`).
- Itens marcados "confirmar" (Bing AI Performance, Perplexity Merchant Program, AIPREF no Google em 2027) não foram lidos na página primária nesta pesquisa e **não podem** virar regra sem essa leitura.
