# Content Quality

Load for editorial pages — blog posts, guides, comparisons, location pages, and any page generated from a template at scale. Sources: Google Search Central — [creating helpful, reliable, people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content) and the [spam policies](https://developers.google.com/search/docs/essentials/spam-policies).

This reference describes checks; severity is decided only by SKILL.md § Quality Gate Output Format.

Google publishes **no minimum word count, readability score or keyword density**, and states there is no ideal page length for its AI features. Never raise a finding on those numbers alone.

The test Google gives: *would this content leave my users satisfied?*

When `seo-specialist` drafts or rewrites copy itself, it follows `skills/shared/ai-writing-signs/SKILL.md`; promotional adjectives, inflated importance and vague attribution are also what Google's helpful-content guidance calls low value.

## Non-commodity content

Value comes from what only this site can say — first-hand experience, expert opinion, original data. A page that recycles what already ranks, or that a generative model could produce from existing pages, is commodity content — a finding on an editorial page. AI-assisted content is allowed when it meets the same bar and the spam policies. Google's [generative AI content guide](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content), updated 2026-10-01 (as last verified 2026-11-04), says to fact-check and review all AI output for accuracy before publishing, and to consider saying how the content was created.

## E-E-A-T — Who, How, Why

| Question | What the page should show |
|---|---|
| **Who** created it? | A byline, where readers would expect one, linking to an author page with real credentials or experience; a clear owner of the site. Fabricated profiles — made-up names, AI-generated headshots, false credentials — are deception |
| **How** was it created? | First-hand evidence (photos, tests, data, methodology); disclosure of automation or AI use where readers would reasonably expect it |
| **Why** does it exist? | To help a reader, not primarily to attract search traffic |

- **Trust** weighs most: accurate claims, sources for facts, contact details, clear corrections
- **YMYL** topics (health, finance, legal, safety) need named, qualified authors and cited sources — a missing author there is a finding with high impact

Warning signs Google names: writing to a target word count, changing dates without changing content (faked freshness), summarising other pages without adding value, and producing many pages on topics outside the site's expertise.

- Update `dateModified` and the visible "Last updated" date only on a substantive edit — a date bump on a typo fix or a re-save is faked freshness. Byline dates describe when the page was published or significantly updated ([byline dates](https://developers.google.com/search/docs/appearance/publication-dates))

## Search intent and page type

Before judging a page, check what the query's top results are. If most are product pages and the page is a blog post (or the reverse), the page type is the problem, not the copy.

| Mismatch | What to report |
|---|---|
| Informational article targeting a transactional query, or the reverse | A finding, high impact — the page type is wrong |
| Format mismatch (results favour lists/tools, page is prose) | A finding |
| Mixed results | Note only — either type can rank |

This needs a live search; when none is available, state the intent you assumed.

## Cannibalization and site structure

- No two indexable pages target the same primary query. When they do, merge into the stronger page and `301` the other, or differentiate their intent
- A topic hub links to every page in its cluster and each page links back. Click depth: SKILL.md § Technical SEO Checklist › Site architecture

## Scaled and programmatic pages

Google's [spam policies](https://developers.google.com/search/docs/essentials/spam-policies) target scaled content abuse and site reputation abuse, however the pages were produced — both added on 2024-03-05 ([announcement](https://developers.google.com/search/blog/2024/03/core-update-spam-policies)) (as last verified 2026-11-04). Generating a page for each query variation or *fan-out* query to win AI answers is scaled content abuse too ([AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)).

| Check | Rule |
|---|---|
| Standalone value | Each generated page must be useful to someone who lands on it directly — data, answers or options specific to that page |
| Doorway pages | Many pages funnelling to one destination, differing only by a keyword or city, are doorways |
| Overlap with a hand-written page | The generated page canonicals to the hand-written one, or is not generated |
| Data source | Pages built on first-party or proprietary data (own inventory, measurements, reviews) can carry standalone value; pages built only from scraped feeds or search results are a listed scaled-content-abuse example. Public data alone needs added analysis to pass the swap test |
| Varying sections | Sections change with the data (different facts, comparisons, options), not just the inserted variable |
| Thin entries | A page whose record lacks enough data to be useful gets a per-page `noindex` (meta or `X-Robots-Tag`; why it must not also be disallowed: `crawl-index-control.md` § noindex) or is not generated — [block indexing](https://developers.google.com/search/docs/crawling-indexing/block-indexing). The cut-off is *heuristic* |
| Rendering | Main content is in the rendered HTML; server-rendered output also serves crawlers that do not run JS — § JavaScript rendering in the skill, `agent-readiness.md` |
| Rollout | Launch a small batch and check indexing and impressions in Search Console, and engagement in analytics (`monitoring.md` § Testing tools, § Analytics), before scaling (*heuristic*) |
| Keyword-driven generation | Generating one page per keyword variation from search-volume data is scaled content abuse, not a strategy — never recommend it |
| Third-party content on a strong domain | Hosting unrelated content to borrow the domain's ranking is site reputation abuse — flag it. Since 2026-08-28 (as last verified 2026-11-04), inside the EEA such pages are ranked separately from the main domain instead of getting a manual action; outside the EEA a manual action still applies ([spam policies](https://developers.google.com/search/docs/essentials/spam-policies)). The finding is the same either way |

**Swap test:** replace the page's variable (city, product, keyword) with another — if the page still reads true, it has no standalone value. Report a failing page, and separately a generator about to publish pages that fail it. Severity: SKILL.md § Quality Gate Output Format.

## Comparison and "best of" pages

- Claims about competitors are verifiable and dated ("price as of 2026-10")
- Disclose the site's own product or affiliate relationship near the top
- Use `ItemList` for roundups; never mark up competitors' products with ratings
