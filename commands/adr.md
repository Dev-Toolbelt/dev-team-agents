Load `skills/shared/current-context/SKILL.md` to identify the active branch and project state before acting.

Load `skills/shared/interaction-patterns/SKILL.md` before asking the user any question with a finite set of answers.

---

## Step 1 — Validate title

`$ARGUMENTS` must contain the ADR title. If empty, stop and ask the user: "Please provide the ADR title, e.g.: `/devteam:adr Adopt PostgreSQL as primary database`"

---

## Step 2 — Create the ADR file

Run the ADR creation script to auto-number the file and place it in `docs/development/adrs/`:

```bash
bash .dev-team-agents/scripts/new-adr.sh "$ARGUMENTS"
```

Show the user the created file path.

---

## Step 3 — Fill the ADR template

**MANDATORY:** Use the Task tool to spawn the agent below. Do NOT fill the template in the main context — always delegate.

- `software-architect` at `.claude/agents/dev-team/software-architect.md` — reads the generated ADR file, fills in Context, Decision, Consequences, and Alternatives using the current project context and the decision described in `$ARGUMENTS`. Changes status from `Proposed` to `Accepted` when the content is complete and the user approves.

---

**PLAN GATE — mandatory for the spawned agent:**
1. Read `.dev-team-agents/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before writing to the ADR file.
3. Do not execute and then explain — plan first, execute second.

Task: Fill ADR for decision: $ARGUMENTS
