<!--
Reuse Guidelines registry — see skills/shared/reuse-guidelines/SKILL.md for the
full format spec and the three enforcement behaviors (code-pattern,
path-convention, design-rule). Copy this file to
docs/development/reuse-guidelines.md and replace the example row(s) below.
-->

| name | type | rule | detection | canonical_ref |
|------|------|------|-----------|---------------|
| example_modal | code-pattern | Always use the shared Modal component, never a new modal implementation | `<div[^>]*className=["'][^"']*\bmodal\b` | src/components/Modal.tsx |
