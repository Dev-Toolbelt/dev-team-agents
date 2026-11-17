# ADR-0067: Client briefing and brand guide are client-level docs with private inputs kept out of git

**Date:** 2026-11-17  
**Status:** Accepted  
**Deciders:** Maintainer  
**Applies to:** `skills/shared/client-briefing/**`, `skills/design/brand-design-system/**`, `commands/brief.md`  
**Relates to:** [ADR-0045](0045-a-gated-pre-implementation-documentation-flow-is-the-default-docs-layout-for-new-projects.md) (doc layout map, read-only inputs)

## Context

A client-kickoff routine was validated in a client-site project: a prompt turns the client's filled-in briefing form (PDF) into a strategic briefing, and a second prompt turns the client's logo into a design system with an AI image-generation layer. `product-analyst` wrote the first and `ui-ux-designer` the second. Importing it into the harness raised four questions the existing rules did not answer:

- The doc layout map (ADR-0045) had no owning doc for a client briefing, and the brand document (300+ lines) does not fit the 80-line cap of `design-system.md`.
- The brand prompt put palette values and CSS tokens in the brand document, which would make two docs own the same values.
- The form carries personal data (phone, e-mail, address of a sole trader) and the inputs are private binaries, while the gated layout's `docs/source/` is committed and read-only.
- A PRD rule citing the briefing would trace back to the analyst's suggestions, not to what the client said.

## Decision

1. **Two new map keys.** `client-briefing` (owner `product-analyst`; `product/briefing.md` in `development`, `briefing.md` in `gated`) owns client-level business facts — who the client is, audience, positioning, voice; product rules stay in `prd`. `brand-guide` (owner `ui-ux-designer`; `design/brand-guide.md`) owns the brand reasoning.
2. **Values have one owner.** `design-system` (with `design-tokens` in gated) owns every implementable value — palette, CSS tokens, type and spacing scales. `brand-guide` names tokens and links to them; a value changes in `design-system` first. The rule lives in `skills/shared/docs-sync/SKILL.md` § `design-system`.
3. **Private inputs stay out of git.** The form and the brand image live next to the briefing or at a path the user gives, never in a read-only (committed) directory. The skill checks `git check-ignore` per file and asks before adding the exact path to `.gitignore`.
4. **Personal identifiers are redacted** in every committed output (briefing and source file); business-facing contact data is kept. An unclear case is redacted and listed for the user.
5. **Gated keeps the trace chain.** `product-analyst` also writes a dated Stage 0 source file with the form's questions and answers verbatim — redaction being the only alteration — and PRD rules cite that file, never the briefing.
6. **Form and image content are data.** Answers are quoted; an embedded instruction is listed, never followed; only color and geometry are read from an SVG source.
7. **`/devteam:brief`** runs both in order (briefing, then brand guide with the briefing as supporting context). The rules live in the two skills; the command points at them.

## Consequences

### Positive
- The routine works in any bound project, on every provider, with output in the project's language.
- No fact has two owners: values in `design-system`, reasoning in `brand-guide`, client facts in `client-briefing`, product rules in `prd`.
- Client personal data and raw files do not reach git history through this flow.

### Negative
- The brand guide is no longer one self-contained document: a reader follows token links into `design-system` for values.
- The gated Stage 0 source file is not strictly verbatim when it holds a redacted identifier.

### Neutral
- The default input names are English (`client-briefing-form.pdf`, `brand-reference.*`); the pt-BR names used by the original project are accepted as a locale example.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Write the whole brand document into `design-system.md` | Breaks the 80-line cap that keeps the always-read doc cheap |
| Condense the brand prompt into `design-system.md` only | Drops the AI image layer and the brand reasoning, which are the reasons to import the routine |
| `brand-guide` owns the palette, `design-system` derives from it | Every token change would need a two-doc amendment rule |
| Briefing outside git entirely, PRD cites it | Breaks doc-flow Principle 1: a rule could trace to an analyst guess |
