# Answer Engines

Load when a non-Google AI engine is named (ChatGPT search, Claude, Perplexity, Bing/Copilot), or the user asks how AI answers find and cite a site. Sources: [Google's AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), [AI features and your website](https://developers.google.com/search/docs/appearance/ai-features), the Bing Webmaster blog ([sitemaps in AI-powered search](https://blogs.bing.com/webmaster/July-2025/Keeping-Content-Discoverable-with-Sitemaps-in-AI-Powered-Search), [AI Performance](https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview)), [IndexNow](https://www.indexnow.org/documentation), and the crawler pages of [OpenAI](https://developers.openai.com/api/docs/bots), [Anthropic](https://support.claude.com/en/articles/8896518) and [Perplexity](https://docs.perplexity.ai/docs/resources/perplexity-crawlers) (as last verified 2026-11-16).

Crawler tokens, their purposes and `robots.txt` mechanics live in `ai-crawlers.md` — this file names which bot each engine needs, never the full table.

## How each engine finds and cites content

| Engine | Where cited pages come from | Bot that must be allowed | What the operator documents |
|---|---|---|---|
| Google — AI Overviews, AI Mode | The Search index, through the core ranking and quality systems | `Googlebot` | A page is eligible when it is indexed and eligible to show with a snippet; no additional technical requirement. Optimizing for generative AI search "is ... still SEO" |
| Bing — Copilot, AI summaries in Bing | Bing's index | `Bingbot` | Sitemaps with accurate `lastmod` and IndexNow are its freshness signals for search and AI-generated answers; no tool guarantees when content appears there |
| OpenAI — ChatGPT search | OpenAI's search index | `OAI-SearchBot` | Search and training bots are separate settings — behavior in `ai-crawlers.md` |
| Anthropic — Claude | Claude's search index, plus fetches on a user's request | `Claude-SearchBot`, `Claude-User` | Effect of blocking: `ai-crawlers.md` |
| Perplexity | Perplexity's search index | `PerplexityBot` | Effect of blocking: `ai-crawlers.md` |

- Blocking a search bot reduces or removes the site's visibility in that engine's answers (operators word it differently — `ai-crawlers.md`); blocking a training bot does not. Report each `robots.txt` rule against the engine it actually affects
- No engine publishes a ranking formula for its AI answers. Report a page as *eligible*, never as *will be cited*
- Product data reaches AI shopping surfaces through feeds, not crawling alone — `ai-commerce-feeds.md`

## Freshness: IndexNow

[IndexNow](https://www.indexnow.org/documentation) pushes added, updated and deleted URLs to participating engines (as last verified 2026-11-16).

| Point | Rule |
|---|---|
| Who receives it | Engines in the [participant registry](https://www.indexnow.org/searchengines.json) — Bing, Yandex, Seznam, Naver, Yep, Internet Archive, Amazonbot. Participants share submitted URLs with each other. **Google is not a participant** |
| Ownership proof | A UTF-8 key file on the same host — at the root, or elsewhere with `keyLocation` (a key file in a subdirectory covers only that path) |
| Batch size | Up to 10,000 URLs per JSON POST |
| When to call it | On publish, update and delete of indexable pages — product pages first on a store whose prices or stock change often |

IndexNow is a recommendation, never a gate condition: its absence is an `ISSUE` at most, and only where Bing or Copilot visibility is a stated goal. It does not replace the sitemap (`sitemap-rules.md`).

## What to tell the user

- One set of practices serves every engine: crawlable, indexable pages with content in the raw HTML (`agent-readiness.md`), the bots above allowed, accurate sitemaps
- Site owners cannot buy or request a citation in any of these engines' organic answers. Ads products exist (`OAI-AdsBot` in `ai-crawlers.md`) and are a separate decision
- Measuring AI visibility per engine: `monitoring.md`

## Evidence: official documentation vs studies

Only rows marked **official** can support a gate condition. Studies explain *why* a recommendation matters; they never set a target.

| Source | Kind | What it shows | How to use it |
|---|---|---|---|
| [Google's AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide) | Official | AI features rest on core Search ranking; AEO/GEO is SEO; no AI-specific markup or files needed | Basis for SKILL.md § AI Search |
| Operator crawler pages (OpenAI, Anthropic, Perplexity) | Official | Which bot feeds search, which feeds training, what blocking each does | Basis for bot findings (`ai-crawlers.md`) |
| Bing Webmaster blog, IndexNow docs | Official | Sitemaps, `lastmod` and IndexNow as freshness signals for Bing and Copilot | Recommendation, `ISSUE` at most |
| Aggarwal et al., "GEO: Generative Engine Optimization", KDD 2024 — [arXiv 2311.09735](https://arxiv.org/abs/2311.09735) | Study (lab) | On a synthetic engine and its own benchmark (GEO-bench), adding citations, quotations and statistics raised the authors' visibility metric by up to 40%; effects varied by domain | Context for "cite sources, give verifiable numbers". Never a target or an uplift promise — SKILL.md § Rejected third-party claims |
| Chen, Wang, Chen, Koudas, "Generative Engine Optimization: How to Dominate AI Search", 2025 — [arXiv 2509.08919](https://arxiv.org/abs/2509.08919) | Study (preprint) | AI search services favour third-party, authoritative sources over brand-owned content, more than Google's results do | Advisory for marketing: earned media and third-party reviews (SKILL.md § Off-Page Signals). Not code work |
| Kumar & Lakkaraju, "Manipulating Large Language Models to Increase Product Visibility", 2024 — [arXiv 2404.07981](https://arxiv.org/abs/2404.07981) | Study (vulnerability) | A crafted "strategic text sequence" on a product page can push an LLM to rank that product first | A spam finding, never a technique. Hidden or machine-targeted text on a page is reported under `spam-security.md` |
