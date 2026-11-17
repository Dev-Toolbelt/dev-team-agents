# ADR-0066: AEO and GEO are covered by the existing SEO skill extended with references for non-Google engines, AI commerce feeds and AI-visibility measurement

**Date:** 2026-11-16  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers; `software-architect`  
**Applies to:** `skills/design/seo-optimization/**`, `agents/seo-specialist.md`, `agents/product-analyst.md`, `skills/shared/frontend-done-checklist/SKILL.md`, `helpers/canonical-facts.json`  
**Relates to:** research notes in `docs/development/aeo-geo/` (pt-BR, marked language exception)

## Context

Sites and online stores built with the framework need to appear in AI answers: Google AI Overviews and AI Mode, ChatGPT search and shopping, Claude, Perplexity and Copilot. `skills/design/seo-optimization` already carried an AEO/GEO section aligned with Google's AI optimization guide, which treats AEO and GEO as ordinary SEO, and `seo-specialist` already ran the gate. Missing were: how non-Google engines discover and cite pages, product feeds for AI shopping surfaces (Merchant Center and UCP, the OpenAI product feed, the Perplexity Merchant Program), AI-referral measurement (the GA4 AI Assistant channel, `utm_source=chatgpt.com`, the Search Console generative AI report, Bing AI Performance, verified-bot logs), page-type guidance, a feed and page parity check, and a discovery-time prompt for these decisions. `CLAUDE.md` requires one canonical home per rule.

## Decision

1. AEO and GEO stay inside `seo-optimization`, owned by `seo-specialist`. There is no separate AEO/GEO skill or agent.
2. Three references are loaded on demand from § Conditional References: `answer-engines.md`, `ai-commerce-feeds.md` and `page-type-playbook.md`. `ai-crawlers.md` and `monitoring.md` are updated in place.
3. Only official, verifiable facts may raise a `BLOCKER`. Academic and industry studies (the KDD 2024 GEO paper, later work, Ahrefs) are context: at most an `ISSUE`, never a target or a score. The one new `BLOCKER` is JSON-LD price or availability that differs from the visible page, or from a feed built in the same codebase, when the cause is in that code.
4. One catalog generator feeds the product page's JSON-LD and every product feed. Parity between them is part of audit step 8.
5. Off-site signals (third-party mentions and reviews) are advisory and routed to marketing, never executed by an agent.
6. `product-analyst` records the AI-crawler policy by purpose, the feed destinations and AI-visibility measurement as open scope decisions when a project matches the SEO Detection Signals. `frontend-done-checklist` requires main content and price in the initial server HTML on public surfaces, with JSON-LD preferred there.
7. `helpers/canonical-facts.json` gains tripwires for recurring wrong claims about `llms.txt`, `Google-Extended` and `GPTBot`.

## Rationale

- Google states that its AI features have no additional requirements, so a separate GEO rule set would hold a second copy of the same facts (`llms.txt`, schema, crawler tokens) and drift.
- Existing routing (the spawn classifier keywords "AEO", "GEO", "AI search", the Detection Signals, `/devteam:seo`) already reaches the right agent.
- On-demand references keep the always-loaded context flat.

## Alternatives Considered

### Option A: a new `skills/design/aeo-geo/` skill
- **Pros**: an explicit name; other agents could load it on its own.
- **Cons**: duplicates § AI Search and the crawler policy, and this repository has seen duplicated rules drift before.
- **Why rejected**: it breaks the one-home-per-rule principle for no functional gain.

### Option B: a new `geo-specialist` agent
- **Pros**: explicit ownership.
- **Cons**: near-total overlap with `seo-specialist`, one more gate per command, and off-site work is not development work.
- **Why rejected**: overengineering.

## Consequences

### Positive
- One gate covers SEO, AEO and GEO. Stores get a feed parity check, and AI-visibility measurement is set up during the build.

### Negative
- `seo-optimization` grows by three references, and "GEO" has no folder of its own (keyword routing covers discovery).

### Risks
- Operator facts change quickly (feed fields, preview reports, crawler tokens). Every line carries an "as last verified" date, and claims that could not be confirmed on a primary page were left out.
