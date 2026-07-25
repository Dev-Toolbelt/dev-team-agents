# Wiki Knowledge Base

Every project gets a wiki at `docs/wiki/`. Agents write entries after completing tasks that reveal non-obvious domain knowledge — gotchas, multi-layer flows, behavioral quirks that aren't derivable from reading code.

The `setup-assistant` creates `wiki/README.md` on FIRST_RUN.

See `skills/shared/docs-sync/SKILL.md` for the wiki entry format, domain folder rules, and update protocol.

## When to Write a Wiki Entry

Write a wiki entry when a task reveals:
- Non-obvious behavior that future agents would need to know
- Gotchas or edge cases that caused confusion
- Multi-layer flows that aren't obvious from code alone
- Integration quirks between components or external services
- Decisions made without an ADR (below the threshold for a full ADR but worth recording)

## Directory Structure

```
docs/wiki/
├── README.md          ← index of all entries; created by setup-assistant on FIRST_RUN
├── backend/           ← backend domain entries
├── frontend/          ← frontend domain entries
├── database/          ← schema, migrations, query patterns
├── devops/            ← CI/CD, infra, deployment quirks
└── integrations/      ← external service integration notes
```

Use the domain folder that best matches the topic. When a topic spans domains, place it in the primary domain and cross-reference from the README index.

## Entry Format

```markdown
# [Short descriptive title]

**Date**: YYYY-MM-DD
**Agent**: [agent-name]
**Tags**: [comma-separated keywords]

## Context

[Why this is worth knowing — the situation that surfaced this knowledge]

## Finding

[The actual knowledge: what was discovered, how it behaves, what the gotcha is]

## Impact

[What breaks or degrades if this isn't known / followed]

## References

- [Link to related ADR, code file, or external doc if applicable]
```

## Update Protocol

1. After completing a task, assess whether new non-obvious domain knowledge was surfaced
2. If yes, create or update an entry in the appropriate domain folder
3. Add a one-line summary to `wiki/README.md` under the correct domain heading
4. Never delete wiki entries — mark outdated ones with `> ⚠️ Outdated as of YYYY-MM-DD` and explain what changed
