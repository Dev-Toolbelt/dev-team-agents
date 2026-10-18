---
description: Catalog a mandatory reuse or standardization rule
argument-hint: <rule description>
model: haiku
---

Load `skills/shared/reuse-guidelines/SKILL.md` before doing anything — it owns the registry format, the three `type`s, and the classify → propose → confirm → append routine this command runs.

Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

---

## Step 1 — Read the description

`$ARGUMENTS` is a free-text description of the rule to catalog, e.g. `coloque o componente XPTO para uso padrão em todo projeto` or `arquivos de upload sempre em xpto/pasta`.

If `$ARGUMENTS` is empty, ask the user for the rule description with `AskUserQuestion` (free-form — this is strict free-form input, not a finite choice) and stop until answered.

---

## Step 2 — Classify `type`

Follow the classification already loaded above:

- Names a component, class, or helper to reuse → `code-pattern`
- About where a kind of file must live → `path-convention`
- Anything else (layout, positioning, structural convention not expressible as a regex) → `design-rule`

If the description could plausibly fit more than one `type`, use `AskUserQuestion` (single-select, options = the plausible types with a one-line example of what each would enforce) rather than guessing.

---

## Step 3 — Resolve `canonical_ref`

Grep the repository for the named component/file/pattern to find its actual path. If more than one candidate matches, or nothing matches, use `AskUserQuestion` to confirm the correct path with the user — never invent a path that doesn't exist in the repo.

---

## Step 4 — Draft the row

- `name`: short kebab/snake identifier derived from the description
- `rule`: one sentence, restating the user's intent in the registry's voice
- `detection`:
  - `code-pattern` → a regex built from the canonical file's actual markup/API (read the file; do not guess a pattern that would never match real violations)
  - `path-convention` → `path:<name-glob>=><required-dir>`
  - `design-rule` → literal `(review-only — no regex; verify against canonical_ref)`
- `canonical_ref`: the path resolved in Step 3

---

## Step 5 — Confirm before writing

Show the full proposed row to the user in the registry's table format. Use `AskUserQuestion` (single-select): **Add this rule** (recommended) / **Edit the description and retry** / **Cancel**.

Never append to `docs/development/reuse-guidelines.md` without this confirmation, even when `$ARGUMENTS` reads as unambiguous.

---

## Step 6 — Append

If confirmed:
1. If `docs/development/reuse-guidelines.md` does not exist yet, create it from `.dev-team-agents/templates/reuse-guidelines-template.md`'s header (`| name | type | rule | detection | canonical_ref |` + separator row) before appending — copy the header shape, not the example row.
2. Append the new row as the last line of the table (Edit tool, smallest possible diff — do not rewrite the file).
3. Confirm to the user: `Catalogado em docs/development/reuse-guidelines.md — regra <name> (<type>).`

---

## $ARGUMENTS

Free text — the rule description. No flags.
