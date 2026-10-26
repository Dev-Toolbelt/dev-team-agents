# AI Crawlers and robots.txt

Load when `robots.txt` is edited or the user states a policy on AI crawling or training. Sources: RFC 9309 (Robots Exclusion Protocol), [Google's robots.txt spec](https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt), and the crawler pages of [OpenAI](https://platform.openai.com/docs/bots), [Anthropic](https://support.anthropic.com/en/articles/8896518), [Apple](https://support.apple.com/en-us/119829) and [Perplexity](https://docs.perplexity.ai/guides/bots). Operators add tokens often — check their docs before claiming a token's purpose.

## Tokens by purpose

Report every claim against the bot it actually concerns. Blocking a training crawler does not remove a site from AI answers; blocking a search crawler does.

| Operator | Training | Search / citation index | User-triggered fetch |
|---|---|---|---|
| OpenAI | `GPTBot` | `OAI-SearchBot` | `ChatGPT-User` |
| Anthropic | `ClaudeBot` | `Claude-SearchBot` | `Claude-User` |
| Google | `Google-Extended` (a control token, not a crawler) | `Googlebot` | — |
| Apple | `Applebot-Extended` (control token) | `Applebot` | — |
| Perplexity | — | `PerplexityBot` | `Perplexity-User` |
| Common Crawl | `CCBot` (dataset used by many trainers) | — | — |
| ByteDance | `Bytespider` | — | — |

- `Google-Extended` governs use of content for Gemini training and grounding only. It has **no effect** on Google Search ranking or on AI Overviews, which follow `Googlebot` and snippet controls
- User-triggered fetchers act on a person's request and may not honour `robots.txt` the way crawlers do — document that limit instead of promising control

## robots.txt mechanics (RFC 9309)

| Rule | Consequence |
|---|---|
| A crawler obeys only the **most specific group** that names it | Rules under `User-agent: *` do not reach a bot that has its own group — repeat the needed lines inside every named group |
| Longest matching path wins; `Allow` wins a tie | Order of lines does not matter |
| `robots.txt` answers `4xx` | Treated as no restrictions |
| `robots.txt` answers `5xx` or `429`, or times out | Treated as full disallow while it persists; Google falls back to its cached copy, and after about 30 days of errors behaves as if there were no file |
| File size | Google reads the first 500 KiB |

Never IP-block crawlers as a policy tool: it breaks verification and cannot distinguish purposes.

## Content signals

`Content-Signal: search=yes, ai-input=yes, ai-train=no` is a convention published by Cloudflare. It states a preference; as of 2026-10 no crawler operator's documentation was found saying it is honoured. Add it only when the user asks, inside each named group, and describe it as a stated preference, not a control.

## Policy procedure

1. Ask the user (via `AskUserQuestion`) whether they want to allow training, allow AI search/citation, both, or neither — never pick a default
2. Write one group per token that needs a rule different from `*`
3. Verify the live file answers `200` and parses (no HTML error page at `/robots.txt`)
