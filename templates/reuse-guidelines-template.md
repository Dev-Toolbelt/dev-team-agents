<!--
Reuse Guidelines registry — see skills/shared/reuse-guidelines/SKILL.md for the
full format spec and the enforcement behaviors (code-pattern, path-convention,
design-rule, review-rule). Copy this file to docs/development/reuse-guidelines.md
and replace the example row(s) below. scope, severity and added are optional;
write a literal pipe inside a cell as \|.
-->

| name | type | rule | detection | canonical_ref | scope | severity | added |
|------|------|------|-----------|---------------|-------|----------|-------|
| example_modal | code-pattern | Always use the shared Modal component, never a new modal implementation | `<div[^>]*className=["'][^"']*\bmodal\b` | src/components/Modal.tsx | src/* | blocking | YYYY-MM-DD |
