# Docs Sync — Wiki Format & Protocol

The wiki captures **domain knowledge that isn't derivable from reading the code** — non-obvious behaviors, multi-component flows, platform-specific gotchas, and concepts that work differently in this project than their name implies.

---

## When to Write a Wiki Entry

Write a new page (or update an existing one) when a task reveals:
- A flow that spans multiple layers or services in a non-obvious way
- A concept whose behavior in this codebase differs from what the name implies
- A gotcha, invariant, or constraint that would surprise a new agent
- A sync/dispatch behavior, state machine edge case, or offline-first deviation
- A business rule that lives nowhere obvious in the code

**Do NOT write** for: things clear from reading the code, standard library patterns, or anything already in `CLAUDE.md`.

---

## Wiki Entry Format

```markdown
# [Concept or Flow Title]

**Origin:** [task or feature context] | YYYY-MM-DD

> [One-sentence "read this first" callout — the most important gotcha for a new agent]

---

## What it is
[1–3 sentences of context]

## How it works
[Diagram, code block, or numbered flow — the mechanics]

## Gotchas
[Bullets — only surprises, not documentation of the obvious]
```

Omit sections that add no value. Keep entries under 80 lines.

---

## Domain Folders — Dynamic, Project-Driven

Domains are **not predefined**. Agents create folders based on the project's actual domain concepts.

| Domain example | Use for |
|----------------|---------|
| `auth/` | Authentication flows, JWT behavior, RBAC quirks |
| `payments/` | Payment states, webhook handling, idempotency |
| `orders/` | Order state machine, transition guards, edge cases |
| `sync/` | Outbox/inbox pattern, dispatch rules, ordering constraints |
| `uploads/` | Multipart flow, chunk handling, retry behavior |
| *(any domain)* | Create the folder the first time an entry belongs there |

When a topic spans two domains, place the file in the more specific one and link from the other.

---

## Wiki Update Protocol

1. **Read** `docs/wiki/README.md` and the target domain folder before writing
2. **Decide**: new file or patch an existing one?
   - New concept → new file (`kebab-case.md`, e.g., `order-state-machine.md`)
   - Additional detail to existing concept → Edit the existing file
3. **Write / Edit** the entry
4. **Update** `wiki/README.md`: add a new domain row if the folder is new; update the entry count
5. **Never** include session dates, author names, or task history in the body

---

## wiki/README.md Format

```markdown
# Wiki

## Domains

| Folder | Covers | Entries |
|--------|--------|---------|
| `auth/` | Authentication, JWT, RBAC | 2 |
| `orders/` | Order state machine, transitions | 1 |
```
