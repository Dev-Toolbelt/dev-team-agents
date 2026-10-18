---
name: diataxis-framework
description: Diataxis — tutorials, how-to, reference, explanation types.
---

# Diataxis Documentation Framework

## Four Document Types

| Type | Answers | Oriented to | Example |
|------|---------|-------------|---------|
| **Tutorial** | "Help me learn by doing" | Learning | "Build your first API in 10 minutes" |
| **How-to guide** | "Help me accomplish X" | Goals | "How to configure CORS" |
| **Reference** | "What is X? What does it do?" | Information | "API endpoint reference" |
| **Explanation** | "Why does it work this way?" | Understanding | "How the auth token lifecycle works" |

The most common mistake is mixing types in one document. Each document should belong to exactly one type.

## Tutorials

- Reader is a learner; guide them step by step
- Every step must work; never skip to an end state
- Use concrete, specific examples (not abstract placeholders)
- Goal: reader succeeds and understands what they just did
- Do not explain why (that is Explanation); just show what to do

## How-to Guides

- Reader has a specific goal; they know what they want but not how
- Start from a working system; do not re-explain prerequisites
- Use numbered steps for actions; use bullet lists only for options
- Title format: "How to X" or "X-ing with Y"
- Do not teach concepts (that is Tutorial); just solve the problem

## Reference

- Complete, accurate, consistent, non-opinionated
- Describe what it is, not how to use it
- Structure: input → output; parameters; types; constraints; examples
- Should be auto-generated where possible (JSDoc, docstrings, OpenAPI)
- Do not explain decisions (that is Explanation)

## Explanation

- Reader wants to understand, not to do
- Discuss trade-offs, history, alternatives, constraints
- Use the word "because" frequently
- Title format: "About X", "Understanding X", "Why X works this way"
- Do not give step-by-step instructions (that is Tutorial/How-to)

## Anti-patterns

| Anti-pattern | What it mixes | Fix |
|-------------|---------------|-----|
| "Getting started" that also explains internals | Tutorial + Explanation | Separate intro tutorial from architecture doc |
| README with installation, config reference, and rationale | How-to + Reference + Explanation | Split into three documents |
| API reference with opinionated usage advice | Reference + How-to | Move advice to a separate how-to guide |
| Tutorial that skips steps to reach a complex state | Tutorial + Reference | Show every step or link to a simpler prerequisite |

## Applying Diataxis

When reviewing or authoring docs:
1. Identify what the reader needs (learning, goal, information, or understanding)
2. Choose the corresponding document type
3. Verify the title matches the type (imperative verb → how-to; noun phrase → reference)
4. Check for anti-patterns: if it answers two different questions, split it

When a document is hard to write, it is usually because it is mixing types.
