# Agent Readiness

Load when the site expects AI agents or agentic browsers to read or act on it, or when content may only exist after JavaScript runs. Many agentic browsers read pages through the accessibility tree and the DOM, so most of these checks are accessibility checks — for WCAG rules load `skills/architecture/accessibility-patterns/SKILL.md`. Google points site owners to web.dev's [best practices for agent-compatible sites](https://web.dev/articles/ai-agent-site-ux).

## Content without JavaScript

Some AI crawlers do not execute JavaScript. Fetch the page as raw HTML (no rendering) and compare it with the rendered page.

| Result | What to report |
|---|---|
| Main content, title, canonical and JSON-LD present in raw HTML | Pass, tagged `raw` |
| Raw HTML carries only an app shell (empty root element, "enable JavaScript") on an indexable page | A finding for non-rendering crawlers, tagged `raw`. Run a rendering test and report separately, tagged `rendered`, whether the rendered output also lacks it — the gate treats that case as its own condition |
| Some content (reviews, prices, tabs) only after JS | A finding naming the JS-only content, tagged `raw` |

A raw HTML page with fewer than about 150 visible words on a content page is a signal worth checking, not a verdict (*heuristic*).

## Acting on the page

| Check | Why it matters to an agent |
|---|---|
| Native `<button>` and `<a href>`, not clickable `<div>`s | Agents find actions by role |
| Every input and icon-only button has an accessible name | Unnamed controls cannot be chosen reliably |
| Targets large enough to hit reliably (WCAG 2.2 target size) | Coordinate-based agents miss small targets |
| No transparent overlay above controls; cookie banners dismissable | Overlays intercept clicks |
| Menus open on click or focus, not only on hover | Many agents do not hover |
| Primary actions in the same place and wording across templates | Agents generalise from one page to the next |
| Landmarks (`<header>`, `<nav>`, `<main>`, `<footer>`) | Lets an agent skip to the content |
| No CAPTCHA in front of public content | Blocks every agent, including legitimate ones |

## Lighthouse Agentic Browsing category

A Lighthouse category added in 13.2 and labelled experimental / "still under development" ([Chrome docs](https://developer.chrome.com/docs/lighthouse/agentic-browsing), [`default-config.js`](https://github.com/GoogleChrome/lighthouse/blob/main/core/config/default-config.js); Lighthouse 13.6) (as last verified 2026-11-04). Needs Chrome 150+; WebMCP audits need the WebMCP origin trial. Not in the PageSpeed Insights API's documented `category` values.

| Audit | Checks |
|---|---|
| `agent-accessibility-tree` | Fails if any of a fixed set of 33 axe rules fails (names and labels, ARIA validity, `tabindex`, `duplicate-id-aria`…). Colour contrast, heading order and landmarks are not in the set |
| `webmcp-form-coverage`, `webmcp-registered-tools`, `webmcp-schema-validity` | WebMCP tool registration and schema; N/A without WebMCP |
| `cumulative-layout-shift` | Lab CLS |
| `llms-txt` | Fetches `llms.txt`: other `4xx` is N/A; `5xx`, `429` or fetch error fails; otherwise needs a `# ` H1, one Markdown link and 50+ characters |
| `ard-schema` | Validates an Agentic Resource Discovery manifest (`/.well-known/ard.json`, or `rel="ard"`; `ai-catalog.json` is flagged as a legacy location). N/A when nothing signals one and the file answers `4xx` |

The result is a pass fraction, not a 0–100 score — report it as "X/N".

- It is a **lab diagnostic for agents, never a Google Search ranking signal**, and never the source of a CLS verdict (field data decides — SKILL.md § Core Web Vitals)
- Its `llms-txt` audit does not change § AI Search › Not needed for Google: a missing `llms.txt` is never a finding, and Lighthouse marks it N/A anyway
- Report failing audits as findings tagged `lab`, with the X/N result; adding files or WebMCP tools only to raise N is not a recommendation. Running Lighthouse: `monitoring.md` § Testing tools

## Optional machine-readable delivery

- A Markdown version of a page is optional, for agents — not a Google signal; no major consumer is documented. Advertise a `.md` alternate with `<link rel="alternate" type="text/markdown" href="/page.md">` (HTML: an alternate with a `type` is "a reformulation of the current document in the specified format"), or negotiate on `Accept: text/markdown`. Keep it content-equivalent to the HTML. If content is negotiated on `Accept`, the response must send `Vary: Accept` so caches do not serve Markdown to browsers
- `llms.txt` rules live in the skill's § AI Search › Not needed for Google

Emerging agent protocols (agent cards, commerce manifests, browser-exposed tool APIs) are drafts with no confirmed consumer: mention them only when the user asks, as "track, don't implement yet". The [Universal Commerce Protocol](https://ucp.dev/) is the one Google names as letting its Search agents take more actions — on a store, flag it as worth tracking, not as a gap.
