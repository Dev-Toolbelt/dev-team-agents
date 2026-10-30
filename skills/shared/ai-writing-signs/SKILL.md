---
name: ai-writing-signs
description: Never-produce rules for signs of AI-generated text, for any prose a person reads.
---

# AI Writing Signs

Rules for any prose a person reads, in any language: documentation, README, release notes, PR descriptions and review comments, blog and landing-page copy, UX microcopy, requirements documents, emails and messages drafted for the user. Source: Portuguese Wikipedia, [Sinais de texto gerado por inteligência artificial](https://pt.wikipedia.org/wiki/Wikip%C3%A9dia:Sinais_de_texto_gerado_por_intelig%C3%AAncia_artificial), which adapts the English [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing).

The signs are statistical: no single one proves a text came from a model, and the page says so. They are listed here because each one also makes text worse — vaguer, longer, less verifiable. The goal is accurate, specific text, not text that "passes" a detector.

`technical-writer` and the PR review comment also apply the vendored `stop-slop` (English phrase checks) through `skills/shared/third-party-writing-skills/SKILL.md`; this skill does not load it.

## Exempt

This table is the one list of exemptions for both this skill and the vendored writing skills.

| Text | Why |
|---|---|
| Agent, skill, command and template bodies; `CLAUDE.md`, `AGENTS.md` | Rule documents: `always` / `never` and terse imperatives carry the requirement |
| Commit messages | `conventional-commits` owns the format |
| ADRs, specs (their Given/When/Then scenarios), wiki entries, plans | Fixed templates with their own wording rules |
| Code, code comments, CLI output, `--json` payloads | Not prose |

Requirements documents and PRDs are prose and are covered; only their template's fixed headings and fields are not. Never change quoted text, command output, identifiers, or a format a framework skill or template fixes.

## 1. Content

| Never | Write instead |
|---|---|
| **Inflated importance or legacy** — "serves as a testament", "plays a crucial role", "marks a turning point", "leaves an indelible mark", "contributing to" (PT: "serve como", "é um testemunho", "papel crucial", "marca indelével", "ponto de virada") | The fact itself, with its source: what happened, when, measured how |
| **Notability padding** — "independent coverage", "active social-media presence", lists of outlets that mentioned the subject | Cite the coverage that supports a claim; drop the rest |
| **Superficial analysis** — a trailing participle that adds a judgement: "…, highlighting its importance", "…, reflecting…", "…, ensuring…", "valuable insights" (PT: "destacando", "refletindo", "garantindo", "percepções valiosas") | End the sentence at the fact, or state the consequence with its evidence |
| **Promotional language** — "vibrant", "rich", "renowned", "innovative", "nestled in the heart of", "a diverse range of" (PT: "vibrante", "renomado", "inovador", "no coração de", "gama diversificada") | Concrete attributes: numbers, names, what it does. Marketing copy may persuade, but with specific claims, never stock adjectives |
| **Vague connection** — "in connection with", "associated with", "linked to" when the relation is known | Name the relation: founded, owns, caused, wrote |
| **Vague attribution** — "experts argue", "observers note", "industry reports", "some critics", or "such as" before a list that is in fact complete | Name the source. If none exists, drop the claim. Say "such as" only for a partial list |
| **Formulaic closing** — "Despite its challenges…", "Future outlook", "Challenges and prospects" sections | End when the content ends. A section on challenges exists only when sources describe specific ones |
| **Boilerplate sections** — "Awards and recognition", "Legacy", "Impact" added by default | A section only when there is sourced content for it |

## 2. Language and grammar

| Never | Write instead |
|---|---|
| **AI vocabulary** — clusters of the words in `references/vocabulary.md` ("delve", "tapestry", "pivotal", "underscore", "foster", "showcase", "landscape", "realm", "intricate", "meticulous") | The plain word. One occurrence is not a problem; several in one paragraph are |
| **Copula avoidance** — "serves as", "functions as", "stands as", "represents", "boasts", "features", "offers" in place of *is*/*has* (PT: "serve como", "funciona como", "representa", "ostenta", "apresenta") | "is", "are", "has" (PT: "é", "são", "tem", "há") |
| **Negative parallelism** — "not just X, but also Y", "not X, but Y", "it's not X — it's Y", "Y rather than X" used for rhythm (PT: "não apenas… mas também", "não é… é…") | State Y. Keep a contrast only when the reader actually believes X |
| **List or title as a proper noun** — "Releases of X is a chronological list of…" | Describe the subject, not the document: "X has shipped four major versions since 2021" |
| **Rule of three** — triads of adjectives, three parallel short sentences, three-item lists padded to reach three | The number of items the content has. Two is fine; one is fine |
| **Elegant variation** — swapping synonyms for the same entity to avoid repetition ("the company… the firm… the organisation… the tech giant") | Repeat the name or use a pronoun |
| **False range** — "from X to Y" where X and Y are not ends of one scale ("from startups to sustainability") | List the items |
| **Hedged significance** (added from practice, not on the source page) — "arguably", "it is worth noting that", "it's important to remember" | State the point. Keep a hedge only for real uncertainty |

## 3. Style and formatting

| Never | Write instead |
|---|---|
| Title Case In Every Heading Word | Sentence case, unless the project's style guide says otherwise |
| Bold on every key term, or bold mid-sentence for emphasis | Bold for a term being defined or a warning; nothing else |
| Vertical lists where every item opens with a **Bold title:** and an explanation | Prose, or a table when items share attributes |
| Emoji as heading or bullet decoration | No emoji unless the project's own voice uses them |
| Small tables holding what one sentence says | A sentence |
| A section that holds only subsections; skipped heading levels; the document title repeated as a heading | One `#` title, levels in order, intro text under each section that has children |
| A "Summary", "In conclusion", "Overall" paragraph restating the section above | Stop after the last new point |
| Curly quotes or `↩` in source files (Markdown, code, wikitext) | Straight quotes; curly quotes only where the project's typography uses them |
| Em dashes as the default connector | Commas, periods, parentheses. Keep the dashes a fixed format places (see the shared exceptions) |

## 4. Text addressed to the user, left in the deliverable

Never let chat scaffolding reach a document, commit, PR, page or message:

- Openers and closers: "Certainly!", "Great question", "Here is…", "I hope this helps", "Let me know if…", "Feel free to…" (PT: "Claro!", "Aqui está", "Espero que isso ajude", "Há mais alguma coisa")
- Knowledge-cutoff or refusal lines: "as of my last update", "as an AI language model"
- Source-availability disclaimers that speculate: "while specific details are not widely documented, it is likely…" — say what is unknown, or leave the gap out
- Reflexive caveats, frequent from mid-2026: "should not be confused with…", "does not by itself establish…" (PT: "não deve ser confundido com", "não estabelece, por si só") when nobody would confuse them
- Unfilled template slots: `[Article title]`, `[Your name]`, `INSERT_URL`, `2025-XX-XX`, `TODO` — fill them or ask the user (Sub-agent Question Relay in `skills/shared/interaction-patterns/SKILL.md`)

A PR description, review comment or change summary is the equivalent of Wikipedia's edit summary. In it, never: claim compliance in general terms ("in line with best practices", "ensuring consistency"), list what was "preserved" or "avoided", or praise the change ("improved", "refined", "enhanced"). State what changed and why, with paths.

## 5. Markup

- Use the target format's syntax: Markdown in Markdown files, wikitext in wikitext, HTML in HTML. Never literal `**bold**` or `## heading` in a format that does not render them
- Never leak chatbot tokens: `contentReference[oaicite:N]`, `citeturn0search0`, `【N†source】`, `{"attributableIndex": …}`. `helpers/canonical-facts.py` fails on them in shipped Markdown
- No `---` rule between every section; no link written as `[text]([url](url))`

## 6. Citations and references

Fabricated sources are the most harmful sign: they are false, not just badly written.

- Cite only a source you have read in this session, or one the user supplied, and only for a claim it supports. Never write a reference from memory
- A URL, DOI or ISBN you cite resolves and points to the work named. If you could not check it, say "unverified" instead of presenting it as fact
- A book reference carries a page or section
- Strip tracking parameters from URLs: `utm_source=chatgpt.com`, `utm_source=openai`, `utm_source=copilot.com`, `referrer=grok.com`
- Never invent statistics, quotes, dates or names. A missing number is better than an invented one
- Every reference defined in a document is cited in its text

## 7. Signs that do not work — do not over-correct

The page lists these as unreliable. Never rewrite text only to avoid them:

- Correct grammar and spelling; a formal or academic register; a mix of formal and informal
- Single transition words: "moreover", "consequently", "notably" (PT: "além disso", "consequentemente")
- Plain, unadorned prose that reads as "dull"
- Literal-translation slips, or a regional variety of a language (pt-BR, pt-PT)
- Accurate markup

Plain human patterns are the target: "is", "has", "there is"; plain verbs ("used", "died"); a qualifier when it is true ("often", "tends to", "may").

## Self-check

Before delivering prose, read it once against §§ 1–6 and fix what you find. The check is silent: never print a score or a list of patterns avoided, and never mention this skill in the deliverable.
