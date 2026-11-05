# Search Appearance

Load when the title, meta description, robots meta or snippet controls, favicon, or `<head>`/layout templates are edited or reviewed, or the site gets Discover traffic. Sources: Google Search Central — [title links](https://developers.google.com/search/docs/appearance/title-link), [snippets](https://developers.google.com/search/docs/appearance/snippet), [robots meta tag](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag), [favicon](https://developers.google.com/search/docs/appearance/favicon-in-search), [Discover](https://developers.google.com/search/docs/appearance/google-discover) (as last verified 2026-11-04).

This reference describes checks; severity is decided only by SKILL.md § Quality Gate Output Format.

Title and description length heuristics are in SKILL.md § On-Page SEO Checklist; site names in `schema-status.md` § Authoring rules; `og:*` tags in `share-preview-check.md`. Google sets no fixed length for either element — results are truncated to the device width.

## Title links

Google builds the title link from, among others: the `<title>`, the main visible title, headings such as `<h1>`, `og:title`, other large or styled text, anchor text on the page and in links pointing to it, and `WebSite` structured data. A `<title>` that fails the checks below is the usual reason Google rewrites it.

| Check | What to report |
|---|---|
| Every page has a `<title>`, distinct from other pages | Missing titles; vague ones ("Home", "Profile") |
| Not micro-boilerplate | Template titles that differ only by a small token (e.g. many pages sharing all but an episode number) |
| No stale dates | A year or date in the title that the visible content has moved past |
| Matches the content | Title that disagrees with the page, often from dynamic data |
| Clear main title | Several equally prominent headings — Google may pick the first one |
| Same language and script as the main content | Mismatch between title and body language |
| No keyword repetition | Stuffed variants of the same term |
| Site name | Optional, once, at the start or end with a delimiter; for domain-level site names Google may drop a duplicate |

## Snippets and controls

Snippets come mainly from page content; the meta description is used when it describes the page better. Write a unique description per page (site-level only for the home and aggregation pages) that summarizes the page and carries specifics (author, date, price, maker) — not a keyword list.

| Control | Effect |
|---|---|
| `nosnippet` | No text snippet or video preview in Search, Images and Discover, and the content is not used as direct input for AI Overviews and AI Mode; a static thumbnail may still show |
| `max-snippet:[n]` | Cap in characters; `0` = `nosnippet`, `-1` = no limit |
| `max-image-preview:none\|standard\|large` | Image preview size; `large` allows up to viewport width; unset = default size |
| `max-video-preview:[n]` | Seconds; `0` = static image only, `-1` = no limit |
| `data-nosnippet` | Boolean attribute, only on `span`, `div` or `section` (any value excludes, even `"false"`); needs valid, closed HTML — an unclosed `div` excludes everything after it. Set at element creation, never toggled by JS on an existing node |

A sitewide `nosnippet` or `max-snippet:0` left in a layout template is a finding: it removes snippets and AI-feature eligibility for every page (SKILL.md § AI Search).

## Favicon

| Requirement | Detail |
|---|---|
| Declared on the home page | `<link rel="icon">` (also `shortcut icon`, `apple-touch-icon`, `apple-touch-icon-precomposed`) on the domain or subdomain home; subdirectory homes are not supported |
| Crawlable | Googlebot can fetch the home page, Googlebot-Image the icon file — neither blocked by `robots.txt` |
| Shape and size | Square (1:1), at least 8×8 px; Google recommends more than 48×48 |
| Format | BMP, GIF, ICO, PNG, JPEG, PPM or TIFF; a stable URL |
| Scope | One per hostname; subdirectories share it |

Updates can take days to weeks; display is never guaranteed.

## Discover

- No special markup is required: indexed pages that meet Discover's content policies are eligible
- Large, high-quality images at least **1200 px wide**, and `max-image-preview:large` (or AMP); name the image with `og:image` or schema.org markup. Avoid the site logo or text-heavy images as the representative image
- Titles that capture the content, not clickbait or withheld information
- Traffic is in Search Console's Discover performance report; Discover manual actions appear under Manual actions
