# Wiki Knowledge Base

Every project gets a wiki at `docs/wiki/`. Agents write entries after completing tasks that reveal non-obvious domain knowledge — gotchas, multi-layer flows, behavioral quirks that aren't derivable from reading code.

The `setup-assistant` creates `wiki/README.md` on FIRST_RUN.

**The canonical specification lives in `skills/shared/docs-sync/references/wiki-format.md`** — entry format, `Tags` retrieval key, never-delete rule, dynamic domain folders, index format, and the update protocol. Load it before writing an entry. Do not restate any part of it here; this file existed as a second copy and had already drifted into a conflicting entry format and a contradictory (predefined) folder list before it was reduced to this pointer.

For **reading** the wiki at the start of a task — keyword lookup against the index rather than loading the directory — see `skills/shared/project-context/SKILL.md` § Context Loading Order.
