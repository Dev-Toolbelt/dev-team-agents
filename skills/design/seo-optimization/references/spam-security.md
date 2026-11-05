# Spam Policies and Site Security

Load when a site has affiliate or sponsored links, user-generated content (comments, forums, reviews), serves bots or user agents different content, has a hacked-site warning or a Security issues report, or sits on an expired or acquired domain. Sources: Google Search Central — [spam policies](https://developers.google.com/search/docs/essentials/spam-policies), [qualify outbound links](https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links), [prevent user-generated spam](https://developers.google.com/search/docs/monitor-debug/prevent-abuse), [security and abuse](https://developers.google.com/search/docs/monitor-debug/security); Search Console Help — [Security issues report](https://support.google.com/webmasters/answer/9044101) (as last verified 2026-11-04).

This reference describes checks; severity is decided only by SKILL.md § Quality Gate Output Format.

Scaled content abuse, doorways and site reputation abuse are checked in `content-quality.md` § Scaled and programmatic pages — not repeated here.

## Policies a code or template review can catch

| Policy | Finding | Allowed |
|---|---|---|
| **Cloaking** | Server or edge logic that branches on a search-engine user agent or IP to change content, keywords or links | Paywalled content shown in full to Google under Flexible Sampling. A pre-rendered copy for bots is acceptable only when it carries the same content users get; dynamic rendering is a workaround Google no longer recommends (SKILL.md § JavaScript rendering) |
| **Sneaky redirects** | Redirects that differ by user agent, device or referrer — crawlers get one page, users (often mobile) another | Site moves, consolidation, logged-in users sent to an internal page. Redirect mechanics: `crawl-index-control.md` |
| **Hidden text and links** | White-on-white or zero-size/zero-opacity text, off-screen positioning, text behind images, a link on a single character | Accordions, tabs, sliders, tooltips, screen-reader-only text |
| **Keyword stuffing** | Lists of cities, phone numbers or repeated phrases with no reader value | — |
| **Link spam** | Paid or exchanged links without qualification, sitewide footer/widget/template links, automated link creation, optimized anchors in forum signatures | Paid links qualified `rel="sponsored"` or `rel="nofollow"` |
| **Expired domain abuse** | An expired domain bought and repurposed mainly to rank low-value content unrelated to its history | — |
| **Thin affiliation** | Affiliate pages that copy merchant descriptions without original reviews, testing, comparison or price context | Affiliate pages that add that value |
| **Misleading functionality** | A "tool" or service page that only leads to ads | — |

## Link qualification

| `rel` value | Use for |
|---|---|
| `sponsored` | Ads and paid placements (affiliate links included). `nofollow` remains acceptable, `sponsored` is preferred |
| `ugc` | Links in comments, forum posts and other user content; may be dropped for consistently trusted contributors |
| `nofollow` | Any other link you do not want associated with the site, when the values above don't fit |

- Values combine: `rel="ugc nofollow"` or comma-separated
- Links carrying these values are generally not followed, but the target can still be crawled from sitemaps or other sites
- Never `nofollow` internal links to control crawling — use `robots.txt` for fetching and `noindex` for indexing (`crawl-index-control.md` § noindex)

## User-generated content

Public comment, forum, profile and upload areas need abuse controls, or UGC spam lands on the site:

- `rel="ugc"` or `nofollow` on user-posted links
- `noindex` on content from accounts with no reputation until trusted
- CAPTCHA (or equivalent) on sign-up and post forms; moderation queues for suspicious activity; blocklists for repeat offenders

## Hacked content, malware and the Security issues report

Hacked-content types in the policy: **code injection** (malicious scripts, crypto-mining), **page injection** (new spam or phishing pages), **content injection** (hidden links or text, cloaking), and redirects keyed on referrer, user agent or device. A hack often uses cloaking, so the owner's browser shows a clean page — check the page as Googlebot sees it (URL Inspection) and in logs.

The Search Console Security issues report lists hacked malware, code/content/URL injection, deceptive pages and embedded resources, harmful downloads, and unclear mobile billing (errors); possible login phishing, suspected deceptive pages and uncommon downloads (warnings). Affected pages can carry a warning label in results and a browser interstitial.

What to report and recommend:

- Any open Security issues entry or Safe Browsing warning on the property — name each issue type and an example URL
- Fix every listed issue sitewide, then **Request Review** describing the issue, the fix and the result; do not resubmit while one is pending (it can lengthen review or mark the site a repeat offender). Reviews take several days to a few weeks
- Spam manual actions appear in the separate Manual actions report — read both
