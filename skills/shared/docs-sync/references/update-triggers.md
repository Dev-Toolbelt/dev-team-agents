# Docs Sync — Update Triggers

When work is delivered, patch the corresponding doc section immediately. Use the smallest possible Edit — one table row, one bullet, one field.

## Trigger Table

| Work delivered | Doc to patch | Section |
|---------------|-------------|---------|
| New dep installed (language, framework, lib) | `tech-stack.md` | Tech Stack table |
| New service or module created | `architecture.md` | Module Map |
| New API endpoint or contract defined | `architecture.md` | API Contracts |
| New code pattern established | `code-standards.md` | Patterns in Use |
| New linter/formatter rule added | `code-standards.md` | Detected Config |
| Sprint file created | `backlog/README.md` | Sprint Files |
| New UI component added | `design/design-system.md` | Component Inventory |
| New color or typography token | `design/design-system.md` | relevant section |
| Task completed touching a directory | `project.md` | Active Areas |
| Schema migration applied | `architecture.md` | Module Map or API Contracts |
| Architectural layer added or renamed | `architecture.md` | Layers |
| Non-obvious domain behavior discovered | `wiki/<domain>/<topic>.md` | New or updated wiki entry |
| User explicitly asks to standardize, note, or remember something | `wiki/<domain>/<topic>.md` or `code-standards.md` | User-triggered wiki write |

---

## Update Protocol

1. **Read** the target file completely before writing anything
2. **Identify** only the section that changed — one table row, one bullet, one field
3. **Edit** using the smallest possible `old_string` → `new_string` diff (Edit tool, not Write)
4. **Update** `<!-- last-updated: YYYY-MM-DD -->` on line 1 in the same edit
5. **Check line count** — if the file now exceeds its budget, remove the oldest or least-relevant entries in the same patch

**Never:**
- Write the entire file when only one section changed
- Add a "Changelog" or "History" section to any doc
- Copy content verbatim from one doc to another (link instead)
- Create sections not defined in the schema without explicit user approval
- Leave a section with only a heading and no content — omit the heading instead

---

## User-Intent Triggers — Write Immediately

When the user's message matches any of these patterns, **treat it as an explicit wiki write request** — do not wait for the task to finish.

### Convention / Standardization Signals

| Pattern (PT) | Pattern (EN) | What to capture |
|---|---|---|
| "convencione …" | "establish as convention …" | The convention name, rule, and why |
| "coloque como padrão …" | "set as project standard …" | The pattern, its scope, and any exceptions |
| "torne padrão …" | "make the standard …" | The decision, rationale, and affected files/layers |
| "adote como padrão …" | "adopt as standard …" | Same as above |
| "defina como padrão …" | "define as the standard …" | The rule and where it applies |
| "a partir de agora … sempre" | "from now on … always" | The behavioral rule being established |
| "sempre que … faça …" | "whenever … do …" | The trigger → action pair as a project rule |
| "nunca mais …" / "não faça mais …" | "never again …" / "stop doing …" | The anti-pattern and why it was banned |
| "use somente …" / "apenas …" | "only use …" | The enforced choice and what it replaces |

### Memory / Note-Taking Signals

| Pattern (PT) | Pattern (EN) | What to capture |
|---|---|---|
| "anote isso …" | "note this …" | The fact or rule verbatim |
| "não esqueça …" | "don't forget …" | The constraint or reminder |
| "guarde essa informação …" | "save this information …" | The piece of knowledge |
| "registre que …" | "record that …" | The statement being registered |
| "lembre(-se) que …" | "remember that …" | The rule or fact |
| "isso é importante …" | "this is important …" | The highlighted rule or fact |
| "para referência futura …" | "for future reference …" | The reference material |

### Approval / Confirmation Signals

| Pattern | What to capture |
|---|---|
| "sim, siga esse padrão" / "yes, follow that pattern" | The pattern as an established convention |
| "exato, sempre assim" / "exactly, always like that" | The confirmed approach as a project rule |
| "pode adotar isso" / "you can adopt that" | The decision, now official |
| "fica assim então" / "let's go with that" | The finalized decision |

### Where to write user-triggered entries

1. Use `code-standards.md` (`## Patterns in Use` or `## Anti-Patterns`) for code conventions
2. Use a wiki entry (`wiki/<domain>/<topic>.md`) for domain rules, behavioral constraints, or multi-layer decisions
3. If unsure which document fits, prefer the wiki — it is the more flexible format
4. Confirm with: _"Noted — recorded in `wiki/<domain>/<topic>.md`."_
