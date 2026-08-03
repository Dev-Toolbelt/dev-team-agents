# Session Summary — Write Rules

## Multi-Agent Sessions

When multiple agents work in the same session, each agent **appends** its contribution to today's entry — never overwrites. Use the agent name as a sub-heading:

```markdown
## YYYY-MM-DD | [task title]
### backend-developer
**Done**: ...
**Decisions**: ...
**Next**: ...
### frontend-developer
**Done**: ...
```

If no entry exists for today, create one with the agent name as the first sub-heading.

## Rotation Policy

After writing a new entry, trim entries according to `.dev-team-agents/user-data/preferences.json`:
- `session_summary_max_days` (default: 30) — remove entries older than this many days
- `session_summary_max_entries` (default: 30) — keep at most this many entries total

To trim: identify the cutoff date (`date -v-${MAX_DAYS}d +%Y-%m-%d` on macOS, `date -d "${MAX_DAYS} days ago" +%Y-%m-%d` on Linux), then remove all `## YYYY-MM-DD` blocks with a date before the cutoff. If the remaining count still exceeds `session_summary_max_entries`, remove the oldest entries until within the limit.

### Promotion Guard — check before trimming

Trimming is the one place in the memory layer where knowledge is destroyed by design, and it is the correct design: episodic memory is supposed to decay. What must not decay is the durable knowledge that was only ever recorded there.

Before removing any block, scan the blocks about to go for a non-empty `**Decisions**:` line. For each one, check whether that decision already exists in a durable artifact:

```bash
grep -ril "<distinctive term from the decision>" docs/development/adrs/ docs/wiki/ 2>/dev/null
```

If nothing matches, the decision was never promoted. Report it once, in the user's language, before trimming:

> ⚠️ Expiring session entries contain decisions not found in any ADR or wiki entry:
> - YYYY-MM-DD — [decision, one line]
>
> Run `/devteam:learn` to promote them, or confirm they can be dropped.

Then proceed with the trim. **The guard reports; it does not block, and it does not promote on its own** — an automatic promotion would fill the wiki with entries nobody chose to keep, which is the failure mode the "not derivable from code" test exists to prevent.

Entries whose `**Decisions**:` line is empty or absent are trimmed silently — there is nothing to lose.
