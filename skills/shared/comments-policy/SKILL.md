---
name: comments-policy
description: Code commenting standards — no comments by default; type annotations and AAA markers.
---

# Comments Policy

The guiding principle: **code should be self-documenting through clear naming**. Comments are the exception, not the rule.

---

## Core Principle — Default: No Comments

Code communicates intent through clear naming, small focused functions, and proper structure. Comments become outdated, double the maintenance burden, and often signal unclear code.

**Before adding a comment, ask:**
- Can I make the code clearer with a better name or extracted method?
- Is this explaining WHAT (fix the code) or WHY (only valid reason)?
- Is this a required type/exception annotation?
- Will this comment become outdated?

---

## When NOT to Comment

| Anti-pattern | Rule |
|---|---|
| Explaining what code does | Improve the code instead |
| Commenting bad code | Fix the code instead |
| Noise / obvious annotations | Remove them |
| Commented-out dead code | Delete it — Git history exists |
| Version-control comments | Use Git commits |
| TODO / FIXME | Create an issue tracker ticket |
| Dividers (`// === Section ===`) | Use proper class/method structure |
| Journal / attribution | Use Git blame |
| Closing brace markers (`} // end if`) | Refactor to smaller functions |

See `references/anti-patterns.md` for full before/after code examples.

---

## When to Comment

| Case | Required? | Format |
|---|---|---|
| Business rule or regulatory constraint | Yes — explains WHY | Inline comment citing the rule |
| Non-obvious algorithm with external reference | Yes — explains WHY | Inline comment with URL |
| Workaround for a known external bug | Yes — explains WHY | Inline comment with ticket reference |
| Typed collections / generics | Yes — type annotation | Native language syntax |
| Exceptions / errors thrown | Yes — type annotation | Native language syntax |
| ORM/dynamic property types | Yes — type annotation | Native language syntax |
| Complex return shapes | Yes — type annotation | Native language syntax |
| Test structure | Yes — AAA markers | `// Arrange`, `// Act`, `// Assert` |

See `references/type-annotations.md` and `references/aaa-pattern.md` for full examples.

---

## Quick Reference

```
Need to add a comment?
├─ Explaining WHAT code does?           → ❌ Improve the code instead
├─ Explaining WHY (rule/workaround)?    → ✅ Add it with context
├─ Type info the language can't express? → ✅ Required — use native syntax
├─ Exceptions / error conditions?       → ✅ Required — use native syntax
└─ Test structure?                      → ✅ Required — use AAA markers
```

---

## Reference Material (load on demand)

- `references/aaa-pattern.md` — AAA test pattern with examples
- `references/type-annotations.md` — type annotation rules by language
- `references/anti-patterns.md` — anti-pattern examples (what NOT to do)
