# Page-Type Playbook

Load when reviewing or building a page template — home, category/listing (PLP), product detail (PDP), blog or guide, FAQ or help centre — or when asked what a page type needs for search and AI answers. Each row condenses rules owned by other references; follow the pointer for the rule itself. Sources are those of the references named.

Every page type first passes SKILL.md § Technical SEO Checklist and § JavaScript rendering: main content, title and canonical in the initial server HTML; JSON-LD preferred there (crawlers that do not run JavaScript: `agent-readiness.md`).

## By page type

| Page | Goal | Required | Avoid |
|---|---|---|---|
| **Home** | Define the entity: who the business is and what it sells | `Organization` + `WebSite` with a stable `@id` reused site-wide (`schema-status.md` § Authoring rules); value proposition in text, not only in an image; crawlable `<a href>` links to the main categories; contact and policy pages linked from the footer | Main content only inside a JS carousel or slider |
| **PLP / category** | Be the source for "best X for Y" questions | A short, useful introduction (how to choose); `BreadcrumbList` matching the visible trail; one URL per paginated page (SKILL.md › Pagination); links to every product meant to be indexed (`schema-ecommerce-local.md` § Category pages); facets handled per `crawl-index-control.md` § URL parameters and faceted navigation | Generic intro text generated in bulk across categories; every filter combination indexable |
| **PDP** | Be recommended and cited with the right price | Complete `Product`/`Offer`, preferably in the initial HTML (`schema-ecommerce-local.md` § Product and Offer); specifications in a real table; own product photos (`media.md`); reviews only when real and visible; shipping and returns visible; parity with feeds (`ai-commerce-feeds.md` § Parity check); out of stock stays `200` (`schema-ecommerce-local.md` § Availability and removed products) | Manufacturer description copied with nothing added (`content-quality.md` § Non-commodity content); price or stock rendered only by JS |
| **Blog / guide** | Be cited in informational answers | Named author with a profile page, publish and update dates, first-hand experience, figures with their source (`content-quality.md` § E-E-A-T); `Article`/`BlogPosting`; internal links to the relevant PLP and PDP | Articles generated per keyword or fan-out query (`content-quality.md` § Scaled and programmatic pages); rewriting for an "AI style" (SKILL.md › Not needed for Google) |
| **FAQ / help centre** | Answer real pre-sale and post-sale questions | Questions taken from support tickets or site search, answered directly, one question per heading; `FAQPage` optional and only for visible Q&A — no Google rich result (`schema-status.md` § Restricted or retired) | A FAQ block added to every page only for the markup |

## What to report

- A template missing a **Required** item is an `ISSUE`, unless the item is itself a gate condition in SKILL.md § Quality Gate Output Format (for example main content only after JavaScript, confirmed in a rendering test)
- An **Avoid** item present is an `ISSUE`; scaled generation that fails the swap test is the `BLOCKER` that § Quality Gate Output Format defines
- Report against the template file, then list the sampled URLs that show it
