# A spawned agent runs the body loaded at session start

**Origin:** trial run of setup-assistant after its agent file changed mid-session | 2026-10-25
**Tags:** sub-agent, system prompt, agent body, session start, stale prompt, spawn, setup-assistant, trial run, agents md

> A sub-agent spawned by type runs the agent body the harness loaded at session start. Edits to `agents/<name>.md` made later do not reach it, so tell it to read the file on disk.

---

## What it is

Spawning an agent by `subagent_type` gives it the body that existed when the session started, as its system prompt. Editing the file afterwards changes the source, not the running prompt.

## How it works

Observed in a trial: `setup-assistant` reported that its prompt carried an older Step 5 and Step 6 than the file on disk.

When trial-running an agent you just edited:

1. Put the instruction in the spawn prompt: read and follow `.dev-team-agents/agents/<name>.md` in the bound project (or `agents/<name>.md` in this repository).
2. Tell the agent to treat its own system-prompt copy as stale where the two disagree.
3. Alternatively, start a new session so the harness reloads the body.

## Gotchas

- The stale copy still looks authoritative to the agent. It will not flag the difference unless told to check.
- This affects only subagents spawned in the same session. A new session loads the current file.
- Verify the spawned run's behavior against the file on disk, not against its own summary of the prompt.
