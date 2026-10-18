# First-Time Setup Guard

**When you see `[DEVTEAM:FIRST_TIME_SETUP]` at the start of a session**, stop immediately and ask the user the following quiz before doing anything else — including loading context or answering their original prompt:

```
AskUserQuestion:
  question: "It looks like this is your first time using dev-team-agents on this machine.
             Would you like to run the onboarding wizard to configure your preferences?"
  header: "First-time setup"
  options:
    - label: "Yes, run onboarding"
      description: "Run the health check and set up your preferences (language, notifications, etc.)"
    - label: "No, skip for now"
      description: "Create a default preferences.json and continue — you can change it anytime"
```

**If the user chooses "Yes, run onboarding":**
- Invoke the `setup-assistant` agent in `FIRST_RUN` mode.

**If the user chooses "No, skip for now":**
1. Create `.dev-team-agents/user-data/preferences.json` by copying the canonical default schema verbatim:
   ```bash
   cp .dev-team-agents/scripts/lib/preferences-defaults.json \
      .dev-team-agents/user-data/preferences.json
   ```
   Copy the file — do not retype the JSON. The schema in `scripts/lib/preferences-defaults.json` is the single source of truth, and a hand-written copy here drifted from it before. Read it if you need to report the values back; `skills/shared/user-preferences/SKILL.md` documents what each field means.

   **Only when the file does not already exist.** An existing `preferences.json` is never overwritten, and neither is `credentials.local.json`.
2. Notify the user, in their configured language: "Default preferences created. You can change them anytime by editing `.dev-team-agents/user-data/preferences.json`." — state the `language` value the file actually got.
3. Continue with their original request.
