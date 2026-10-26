# Sitemap Rules

Source: sitemaps.org protocol and Google Search Central sitemap documentation.

## Limits

| Rule | Value |
|---|---|
| URLs per sitemap file | 50,000 maximum |
| File size | 50 MB uncompressed maximum (gzip allowed for transfer) |
| Above either limit | Split, and list the files in a sitemap index (an index may list 50,000 sitemaps) |
| Encoding | UTF-8, entity-escaped URLs (`&` → `&amp;`) |
| URL form | Absolute, same protocol and host as the canonical URLs |

## What goes in

- Only canonical, indexable URLs answering `200`
- Exclude: `noindex` pages, URLs that redirect, non-canonical duplicates, parameter variants, `4xx`/`5xx`, pages disallowed in `robots.txt`, login and cart pages
- A URL in the sitemap whose canonical points elsewhere is a contradiction — report it as `ISSUE`

## Fields

| Field | Rule |
|---|---|
| `<loc>` | Required |
| `<lastmod>` | W3C Datetime (`2026-10-23` or full timestamp), changed only when the main content changes meaningfully. Google ignores it on sites where it is consistently wrong — never set it to the build time on every deploy |
| `<priority>`, `<changefreq>` | Ignored by Google; harmless, do not spend effort on them |

## Extensions

| Extension | Rule |
|---|---|
| Image | `<image:image>` with `<image:loc>`; Google deprecated the caption/title/licence sub-tags |
| Video | `<video:video>` with thumbnail, title, description, and content or player location |
| News | Articles published in the last 2 days only, at most 1,000 URLs per news sitemap |
| `hreflang` | `xhtml:link` alternates — see `hreflang.md` |

## Discovery

Reference the sitemap from `robots.txt` (`Sitemap: https://example.com/sitemap.xml`) and submit it in Search Console / Bing Webmaster Tools. IndexNow is an optional push protocol used by Bing and Yandex, not by Google — advisory only.
