# A Personal Preference Goes to a Git-Ignored File

**Origin:** `orchestrator_default` design review, ADR-0062 | 2026-11-02
**Tags:** orchestrator_default, settings.local.json, settings.json, personal preference, git-ignored, committed settings, default agent, bind, gitignore, team flip-flop

> Write a personal default only to `.claude/settings.local.json`, never to the committed `settings.json`: a value in the committed file is set for every teammate, and each one who disagrees reverts it, so the file flips back and forth.

---

## What it is

`orchestrator_default` makes the orchestrator the default agent for one user. It is personal. The Claude target is `.claude/settings.local.json`, which the bind-managed `.gitignore` block ignores. opencode and Codex have no default at all. The decision came from a software-architect review that flagged committed-file flip-flops across a team.

## How it works

| Provider | Where the default goes | Git status |
|----------|------------------------|-----------|
| claude | `.claude/settings.local.json`, key `agent` | git-ignored |
| opencode | none | n/a |
| codex | none | n/a |

- The writer (`scripts/lib/devteam/default_agent.py`, called from `bind.py`) writes `"agent"` only into `settings.local.json`.
- With the preference off, the key is removed only while it holds `"orchestrator"`. A value the user set by hand is left alone.
- `settings.json` is never touched by this preference.

## Gotchas

- **A committed write looks harmless once.** It reaches every clone on the next pull. One teammate who wants a different default reverts it, and the next sync flips it back.
- **Do not add the key to the committed file to share a default.** A team default is a project decision and needs its own record, not this key.
- **The ignore rule is load-bearing.** `settings.local.json` is safe only while the bind-managed `.gitignore` block lists it. A `devteam sync` that rewrites that block must keep the entry (see `docs/wiki/git/gitignore-managed-block-is-rewritten.md`).
- **Other providers have no file to write.** opencode and Codex get no default, so a parity check must not expect one.

## References

- ADR-0062 (orchestrator persona and supervision gate)
- `scripts/lib/devteam/default_agent.py` (provider map and the removal rule)
- `scripts/lib/devteam/bind.py` (`.claude/settings.local.json` in the ignored set)
- `docs/wiki/git/gitignore-managed-block-is-rewritten.md`
