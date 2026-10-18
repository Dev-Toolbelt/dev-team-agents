# Docs Sync — Wiki Format & Protocol

**This is the canonical wiki specification.** Agents and skills reference it; they do not restate it. `skills/shared/project-context/references/wiki.md` points here.

The wiki captures **domain knowledge that isn't derivable from reading the code** — non-obvious behaviors, multi-component flows, platform-specific gotchas, and concepts that work differently in this project than their name implies.

---

## When to Write a Wiki Entry

Write a new page (or update an existing one) when a task reveals:
- A flow that spans multiple layers or services in a non-obvious way
- A concept whose behavior in this codebase differs from what the name implies
- A gotcha, invariant, or constraint that would surprise a new agent
- A sync/dispatch behavior, state machine edge case, or offline-first deviation
- A business rule that lives nowhere obvious in the code
- A decision made without an ADR — below the threshold for a full record, but worth keeping

**Do NOT write** for: things clear from reading the code, standard library patterns, or anything already in `CLAUDE.md`.

---

## Wiki Entry Format

```markdown
# [Concept or Flow Title]

**Origin:** [task or feature context] | YYYY-MM-DD
**Tags:** [comma-separated keywords — the retrieval key; see Index below]

> [One-sentence "read this first" callout — the most important gotcha for a new agent]

---

## What it is
[1–3 sentences of context]

## How it works
[Diagram, code block, or numbered flow — the mechanics]

## Gotchas
[Bullets — only surprises, not documentation of the obvious]

## References
[Related ADR, code path, or external doc — omit when there are none]
```

Omit sections that add no value. Keep entries under 80 lines.

**`Tags` is load-bearing, not decoration.** It is what an agent greps to decide whether to read the entry at all. Use the words someone would actually search — domain nouns, component names, error strings — not categories.

---

## Never Delete an Entry

A wiki entry is superseded, never removed. When knowledge goes stale, add to the top of the entry:

```markdown
> ⚠️ Outdated as of YYYY-MM-DD — [what changed, and where the current behavior is documented]
```

Then update the body. Deleting the entry destroys the only record that the old behavior ever existed, which is exactly what the next agent needs when it hits a system still running it. The same rule governs every memory artifact — see the No-Destruction Rule in `skills/shared/setup-health-check/SKILL.md`.

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
4. **Update** `wiki/README.md`: add one index row for the entry — path, its `Tags`, and its callout. Editing an existing entry means updating that row, not adding a second one
5. **Never** include session dates, author names, or task history in the body

A wiki entry that is not in the index is invisible: step 3 without step 4 writes knowledge nothing will ever retrieve.

---

## wiki/README.md Format — Retrieval Index

One row per **entry**, not per domain. This file is the only part of the wiki an agent loads unconditionally, so it must stay greppable and small: the row carries just enough to decide whether opening the entry is worth it.

```markdown
# Wiki

## Index

| Entry | Keywords | Read it when |
|-------|----------|--------------|
| `auth/jwt-refresh.md` | jwt, refresh token, 401, session expiry | A session dies before its stated TTL |
| `orders/state-machine.md` | order status, transition, cancel, refund | Changing anything that moves an order between states |
```

| Column | Content |
|--------|---------|
| **Entry** | Path relative to `docs/wiki/`, in backticks |
| **Keywords** | Copied verbatim from the entry's `Tags` line — the two must not drift |
| **Read it when** | The entry's callout, compressed to one clause. A trigger condition, not a summary |

**Entry counts are not tracked.** A count is a number to keep in sync that answers no question an agent has; `ls` produces it on demand.

**A project whose `README.md` still carries the older `## Domains` count table keeps it.** Add the `## Index` section above it and leave the domain rows in place — their `Covers` text is knowledge someone wrote. Never regenerate this file over an existing one.
