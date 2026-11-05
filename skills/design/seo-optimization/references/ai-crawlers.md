# AI Crawlers and robots.txt

Load when `robots.txt` is edited or the user states a policy on AI crawling or training. Sources: RFC 9309 (Robots Exclusion Protocol), [Google's robots.txt spec](https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt), [Google's user-triggered fetchers](https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers), and the crawler pages of [OpenAI](https://developers.openai.com/api/docs/bots), [Anthropic](https://support.claude.com/en/articles/8896518), [Apple](https://support.apple.com/en-us/119829) and [Perplexity](https://docs.perplexity.ai/guides/bots) (as last verified 2026-11-04). Operators add tokens often — check their docs before claiming a token's purpose.

## Tokens by purpose

Report every claim against the bot it actually concerns. Blocking a training crawler does not remove a site from AI answers; blocking a search crawler does.

| Operator | Training | Search / citation index | User-triggered fetch |
|---|---|---|---|
| OpenAI | `GPTBot` | `OAI-SearchBot` | `ChatGPT-User` |
| Anthropic | `ClaudeBot` | `Claude-SearchBot` | `Claude-User` |
| Google | `Google-Extended` (a control token, not a crawler) | `Googlebot` | `Google-Agent` (agents acting on a user's request) |
| Apple | `Applebot-Extended` (control token) | `Applebot` | — |
| Perplexity | — | `PerplexityBot` | `Perplexity-User` |
| Common Crawl | `CCBot` (dataset used by many trainers) | — | — |
| ByteDance | `Bytespider` | — | — |

- `Google-Extended` governs use of content for Gemini training and grounding only. It has **no effect** on Google Search ranking or on AI Overviews, which follow `Googlebot` and snippet controls
- User-triggered fetchers act on a person's request. Google (`Google-Agent`) and Perplexity (`Perplexity-User`) say theirs generally ignore `robots.txt`; OpenAI says `ChatGPT-User` rules may not apply; Anthropic says its bots, `Claude-User` included, honour it. Document the limit per operator instead of promising control, and put private paths behind authentication
- `OAI-AdsBot` checks landing pages submitted as ChatGPT ads; OpenAI's page does not say how it treats `robots.txt` — blocking it is an ads decision, not a search or training one

## robots.txt mechanics (RFC 9309)

| Rule | Consequence |
|---|---|
| A crawler obeys only the **most specific group** that names it | Rules under `User-agent: *` do not reach a bot that has its own group — repeat the needed lines inside every named group |
| Longest matching path wins; `Allow` wins a tie | Order of lines does not matter |
| `robots.txt` answers `4xx` | Treated as no restrictions |
| `robots.txt` answers `5xx` or `429`, or times out | Treated as full disallow while it persists; Google falls back to its cached copy, and after about 30 days of errors behaves as if there were no file |
| File size | Google reads the first 500 KiB |

Never IP-block crawlers as a policy tool: it breaks verification and cannot distinguish purposes.

## Verifying a bot

A User-Agent string is trivially spoofed. Before allowlisting a bot or reporting how it is treated, match the source IP against the operator's published ranges (or, for Google, reverse + forward DNS — `crawl-index-control.md` § CDN, WAF and bot protection):

| Operator | Published IP ranges |
|---|---|
| Google | `common-crawlers.json`, `special-crawlers.json`, `user-triggered-fetchers.json`, `user-triggered-fetchers-google.json`, `user-triggered-agents.json` (`Google-Agent`) — listed on [verifying Google requests](https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests) |
| OpenAI | `openai.com/gptbot.json`, `/searchbot.json`, `/chatgpt-user.json`, `/adsbot.json` |
| Anthropic | `claude.com/crawling/bots.json` |
| Perplexity | `perplexity.ai/perplexitybot.json`, `/perplexity-user.json` |

Read the files live — ranges change, and operators name them the current source of truth for WAF rules.

## Usage-preference signals

None is a standard — track them, never raise their absence as a finding, and add one only when the user asks.

| Signal | Status (as last verified 2026-11-04) |
|---|---|
| `Content-Signal: search=yes, ai-input=yes, ai-train=no` | Cloudflare convention. Its IETF individual draft (`draft-romm-aipref-contentsignals`) has expired; no crawler operator's docs were found saying it is honoured. If used, repeat it inside each named group and describe it as a stated preference, not a control |
| IETF AIPREF working group (`draft-ietf-aipref-vocab`, `draft-ietf-aipref-attach`) | Working-group Internet-Drafts, no RFC yet |
| `User-Agent: __usage_ai-training` group (`draft-kelley-aipref-training-preference-signal`) | Individual draft; Anthropic states it honours this "no AI training" signal from 2026-10-30, and a `ClaudeBot` group takes priority over it. Not a crawl control — crawlers still follow their own token's group |

Sources: [IETF AIPREF documents](https://datatracker.ietf.org/wg/aipref/documents/), [Content-Signal draft](https://datatracker.ietf.org/doc/draft-romm-aipref-contentsignals/), [training-preference draft](https://datatracker.ietf.org/doc/draft-kelley-aipref-training-preference-signal/), Anthropic's crawler page above.

## Policy procedure

1. Ask the user (via `AskUserQuestion`) whether they want to allow training, allow AI search/citation, both, or neither — never pick a default
2. Write one group per token that needs a rule different from `*`
3. Verify the live file answers `200` and parses (no HTML error page at `/robots.txt`)
