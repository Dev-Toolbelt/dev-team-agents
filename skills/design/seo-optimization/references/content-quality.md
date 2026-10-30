# Content Quality

Load for editorial pages — blog posts, guides, comparisons, location pages, and any page generated from a template at scale. Source: Google Search Central "Creating helpful, reliable, people-first content" and the spam policies.

Google publishes **no minimum word count, readability score or keyword density**, and states there is no ideal page length for its AI features. Never raise a finding on those numbers alone.

The test Google gives: *would this content leave my users satisfied?*

When `seo-specialist` drafts or rewrites copy itself, it follows `skills/shared/ai-writing-signs/SKILL.md`; promotional adjectives, inflated importance and vague attribution are also what Google's helpful-content guidance calls low value.

## Non-commodity content

Value comes from what only this site can say — first-hand experience, expert opinion, original data. A page that recycles what already ranks, or that a generative model could produce from existing pages, is commodity content: an `ISSUE` on an editorial page. AI-assisted content is allowed when it meets the same bar and the spam policies.

## E-E-A-T — Who, How, Why

| Question | What the page should show |
|---|---|
| **Who** created it? | A byline that links to an author page with real credentials or experience; a clear owner of the site |
| **How** was it created? | First-hand evidence (photos, tests, data, methodology); disclosure when automation or AI was used substantially |
| **Why** does it exist? | To help a reader, not primarily to attract search traffic |

- **Trust** weighs most: accurate claims, sources for facts, contact details, clear corrections
- **YMYL** topics (health, finance, legal, safety) need named, qualified authors and cited sources — a missing author there is an `ISSUE` with higher priority

Warning signs Google names: writing to a target word count, changing dates without changing content (faked freshness), summarising other pages without adding value, and producing many pages on topics outside the site's expertise.

## Search intent and page type

Before judging a page, check what the query's top results are. If most are product pages and the page is a blog post (or the reverse), the page type is the problem, not the copy.

| Mismatch | Severity |
|---|---|
| Informational article targeting a transactional query, or the reverse | `ISSUE`, top priority |
| Format mismatch (results favour lists/tools, page is prose) | `ISSUE` |
| Mixed results | Note only — either type can rank |

This needs a live search; when none is available, state the intent you assumed.

## Cannibalization and site structure

- No two indexable pages target the same primary query. When they do, merge into the stronger page and `301` the other, or differentiate their intent
- A topic hub links to every page in its cluster and each page links back; important pages are reachable within about 3 clicks of the homepage (*heuristic*)

## Scaled and programmatic pages

Google's spam policies (2024) target scaled content abuse and site reputation abuse, however the pages were produced. Generating a page for each query variation or *fan-out* query to win AI answers is scaled content abuse too ([AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)).

| Check | Rule |
|---|---|
| Standalone value | Each generated page must be useful to someone who lands on it directly — data, answers or options specific to that page |
| Doorway pages | Many pages funnelling to one destination, differing only by a keyword or city, are doorways |
| Overlap with a hand-written page | The generated page canonicals to the hand-written one, or is not generated |
| Rollout | Publish in batches and watch indexing before generating the next batch |
| Third-party content on a strong domain | Hosting unrelated content to borrow the domain's ranking is site reputation abuse — flag it |

**Swap test:** replace the page's variable (city, product, keyword) with another — if the page still reads true, it has no standalone value. Severity is set by the skill's § Quality Gate Output Format: a failing page is an `ISSUE`; a generator about to publish pages that fail it is listed there as a `BLOCKER`.

## Comparison and "best of" pages

- Claims about competitors are verifiable and dated ("price as of 2026-10")
- Disclose the site's own product or affiliate relationship near the top
- Use `ItemList` for roundups; never mark up competitors' products with ratings
