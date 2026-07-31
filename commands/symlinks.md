Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

---

You are running the **`/devteam:symlinks`** command.

Its job: detect the operating system and the active provider, analyze every dev-team-agents symlink, repair anything materialized as a plain file, and — when the OS blocks native symlinks — walk the user through the fix in that provider's terms. It wraps `scripts/fix-symlinks.sh`, which does the detection, auto-repair, and re-validation.

**IMPORTANT — Output rules:**
- Be direct and terse. No analysis, no side notes, no commentary beyond what is specified below.
- Do NOT explain what you are about to do before doing it.
- Only output exactly what each step below says to output.

> This command operates on the local installation, not a git branch — it does **not** load `current-context` and has no Plan Gate.

---

## Step 1 — Detect the OS and the active provider

```bash
if grep -qiE '(microsoft|wsl)' /proc/version 2>/dev/null; then echo "OS: WSL";
elif [ "$(uname -s 2>/dev/null)" = "Darwin" ]; then echo "OS: macOS";
elif uname -s 2>/dev/null | grep -qiE 'mingw|msys|cygwin'; then echo "OS: Windows (git-bash)";
elif [ "$(uname -s 2>/dev/null)" = "Linux" ]; then echo "OS: Linux";
else echo "OS: Unknown"; fi

if   [ -f .claude/settings.json ]; then echo "Provider: claude"
elif [ -f .opencode/opencode.json ] || [ -f .opencode/opencode.jsonc ]; then echo "Provider: opencode"
elif [ -f .codex/hooks.json ]; then echo "Provider: codex"
else echo "Provider: unknown"; fi
```

Output exactly the two lines produced: `OS: <detected>` and `Provider: <provider>`.

Bind these two labels for every later step — never hardcode a CLI name:

| Provider | `<CLI>` | `<config-dir>` |
|----------|---------|----------------|
| `claude` | Claude Code | `.claude` |
| `opencode` | opencode | `.opencode` |
| `codex` | Codex CLI | `.codex` |
| `unknown` | your CLI | `.claude` |

> `fix-symlinks.sh` repairs the **`.claude/` tree only**. The opencode and Codex installs also symlink `skills/` (into `.opencode/skills/` and `.codex/skills/`), and those links break under the same Windows condition — but the helper does not touch them, so on those providers it can report "nothing to fix" while `skills/` is still materialized. Handle that in Step 6.

---

## Step 2 — Analyze and repair

```bash
bash .dev-team-agents/scripts/fix-symlinks.sh; echo "EXIT:$?"
```

Read the final `EXIT:` line and branch on it in Step 3.

---

## Step 3 — Report the outcome

**`EXIT:0` and the output contains `Nothing to fix`** → output exactly:

```
All dev-team-agents symlinks are healthy. Nothing to fix.
```

Then go to Step 6.

**`EXIT:0` and the output contains `repaired`** → output exactly:

```
Repaired all broken symlinks as native links.
Restart <CLI> so it re-indexes commands, agents, and skills.
```

(substituting the `<CLI>` bound in Step 1 — do not print the literal placeholder)

Then go to Step 6.

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
        { "label": "Run CLI as admin", "description": "Fully close <CLI> (including tray/Task Manager), then relaunch as administrator." }
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
  git checkout -- <config-dir>
  ```
  Then `Restart <CLI> afterward.` and stop (the elevated session does the checkout, not this one).
- **Run CLI as admin** → output `Close <CLI> completely, reopen it as administrator, then run /devteam:symlinks again.` and stop.

---

## Step 5 — Finish the safe git repair (only after Developer Mode is enabled)

Substitute `<config-dir>` from Step 1:

```bash
git config core.symlinks true && git checkout -- <config-dir> && bash .dev-team-agents/scripts/fix-symlinks.sh; echo "EXIT:$?"
```

- **`EXIT:0`** → output exactly (with `<CLI>` substituted):
  ```
  Symlinks repaired. Restart <CLI> so it re-indexes commands, agents, and skills.
  ```
- **`EXIT:3`** → output exactly:
  ```
  Still blocked. Use the elevated-terminal or run-as-administrator option instead.
  ```

Then continue to Step 6.

---

## Step 6 — Skills link check for non-Claude providers

Skip entirely and stop when `Provider:` is `claude` or `unknown` — Step 2 already covered that tree.

When `Provider:` is `opencode` or `codex`: `fix-symlinks.sh` does not inspect `<config-dir>/skills`, so verify it directly:

```bash
test -L <config-dir>/skills/dev-team-agents && echo "SKILLS:link" || echo "SKILLS:broken"
```

On `SKILLS:broken`, output exactly one line, then stop:

```
Re-run bash .dev-team-agents/scripts/install-<provider>.sh to restore the skills symlink.
```

On `SKILLS:link`, output nothing extra and stop.
