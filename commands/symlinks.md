Load `skills/shared/interaction-patterns/SKILL.md` before asking the user any question with a finite set of answers.

---

You are running the **`/devteam:symlinks`** command.

Its job: detect the operating system, analyze every dev-team-agents symlink, repair anything materialized as a plain file, and — when the OS blocks native symlinks — walk the user through the fix. It wraps `scripts/fix-symlinks.sh`, which does the detection, auto-repair, and re-validation.

**Interaction rule:** All yes/no and multiple-choice prompts in this command use the `AskUserQuestion` tool as defined in `skills/shared/interaction-patterns/SKILL.md`.

**IMPORTANT — Output rules:**
- Be direct and terse. No analysis, no side notes, no commentary beyond what is specified below.
- Do NOT explain what you are about to do before doing it.
- Only output exactly what each step below says to output.

> This command operates on the local installation, not a git branch — it does **not** load `current-context` and has no Plan Gate.

---

## Step 1 — Detect the OS

```bash
if grep -qiE '(microsoft|wsl)' /proc/version 2>/dev/null; then echo "WSL";
elif [ "$(uname -s 2>/dev/null)" = "Darwin" ]; then echo "macOS";
elif uname -s 2>/dev/null | grep -qiE 'mingw|msys|cygwin'; then echo "Windows (git-bash)";
elif [ "$(uname -s 2>/dev/null)" = "Linux" ]; then echo "Linux";
else echo "Unknown"; fi
```

Output exactly one line: `OS: <detected>`

---

## Step 2 — Analyze and repair

```bash
bash .claude/dev-team-agents/scripts/fix-symlinks.sh; echo "EXIT:$?"
```

Read the final `EXIT:` line and branch on it in Step 3.

---

## Step 3 — Report the outcome

**`EXIT:0` and the output contains `Nothing to fix`** → output exactly:

```
All dev-team-agents symlinks are healthy. Nothing to fix.
```

Then stop.

**`EXIT:0` and the output contains `repaired`** → output exactly:

```
Repaired all broken symlinks as native links.
Restart Claude Code so it re-indexes commands, agents, and skills.
```

Then stop.

**`EXIT:1`** → the script hit an error. Output exactly:

```
Repair failed. Script output:
```

Followed by the raw script output. Then stop.

**`EXIT:3`** → the OS is blocking native symlink creation. Continue to Step 4.

---

## Step 4 — OS blocks native symlinks (only on `EXIT:3`)

The environment cannot create native symlinks yet (Windows without Developer Mode / elevation / `core.symlinks=true`). Use the **`AskUserQuestion`** tool:

```json
{
  "questions": [
    {
      "question": "Native symlinks are blocked on this machine. How do you want to fix it?",
      "header": "Symlink fix",
      "multiSelect": false,
      "options": [
        { "label": "Developer Mode", "description": "Recommended, no admin. Settings → System → For developers → enable Developer Mode. Fixes this and future clones." },
        { "label": "Elevated terminal", "description": "Fastest, one-off. Open PowerShell as Administrator in the project root." },
        { "label": "Run Claude as admin", "description": "Fully close Claude Code (including tray/Task Manager), then relaunch as administrator." }
      ]
    }
  ]
}
```

Wait for the answer, then:

- **Developer Mode** → instruct the user to enable it now, then confirm with `AskUserQuestion` ("Developer Mode enabled?" → Yes / Not yet). On **Yes**, run Step 5. On **Not yet**, output `Enable Developer Mode, then run /devteam:symlinks again.` and stop.
- **Elevated terminal** → tell the user to run, in the project root of an Administrator PowerShell:
  ```
  git config core.symlinks true
  git checkout -- .claude
  ```
  Then `Restart Claude Code afterward.` and stop (the elevated session does the checkout, not this one).
- **Run Claude as admin** → output `Close Claude Code completely, reopen it as administrator, then run /devteam:symlinks again.` and stop.

---

## Step 5 — Finish the safe git repair (only after Developer Mode is enabled)

```bash
git config core.symlinks true && git checkout -- .claude && bash .claude/dev-team-agents/scripts/fix-symlinks.sh; echo "EXIT:$?"
```

- **`EXIT:0`** → output exactly:
  ```
  Symlinks repaired. Restart Claude Code so it re-indexes commands, agents, and skills.
  ```
- **`EXIT:3`** → output exactly:
  ```
  Still blocked. Use the elevated-terminal or run-as-administrator option instead.
  ```

Then stop.
