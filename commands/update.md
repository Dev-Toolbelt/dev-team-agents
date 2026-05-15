Load `skills/shared/interaction-patterns/SKILL.md` before asking the user any question with a finite set of answers.

---

You are running the **`/devteam:update`** command.

**Interaction rule:** All yes/no and multiple-choice prompts in this command use the `AskUserQuestion` tool as defined in `skills/shared/interaction-patterns/SKILL.md`.

**IMPORTANT — Output rules:**
- Be direct and terse. No analysis, no side notes, no observations, no commentary beyond what is specified below.
- Do NOT add any personal remarks, flag issues you noticed, or mention things "worth flagging".
- Do NOT explain what you are about to do before doing it.
- Only output exactly what each step below says to output.

---

## Arguments

| Argument | Effect |
|----------|--------|
| _(none)_ | Check for updates and install if available |
| `--enable-auto` | Enable automatic updates |
| `--disable-auto` | Disable automatic updates |
| `vX.Y.Z` | Pin to a specific version |

---

## Step 1 — Read current version

```bash
cat .claude/user-data/.installed-version 2>/dev/null || echo "unknown"
```

---

## Step 2 — Check for updates

Force a fresh check (bypass the 24h TTL):

```bash
rm -f .claude/user-data/.last-update-check
bash .claude/dev-team-agents/scripts/check-updates.sh
```

**If the script produces no output** → already up to date. Output exactly:

```
Installed: <current-version>
Latest:    <current-version>

Up to date.
```

Then stop. Do not add anything else.

**If the script outputs a banner with a new version** → parse current and latest from the output, then continue to Step 3.

---

## Step 3 — Offer to update

Output exactly:

```
Update available: <current-version> → <latest-version>
```

Then immediately use the **`AskUserQuestion`** tool with a single question:

```json
{
  "questions": [
    {
      "question": "Apply update?",
      "header": "Update",
      "multiSelect": false,
      "options": [
        { "label": "Yes", "description": "Download and apply the update now." },
        { "label": "No",  "description": "Skip this update and keep the current version." }
      ]
    }
  ]
}
```

Wait for the user's answer before proceeding.

---

## Step 4 — Apply the update (only if user said yes)

```bash
bash .claude/dev-team-agents/scripts/update.sh latest
```

After the script exits successfully, output exactly:

```
Updated to <latest-version>. Start a new session to pick up the changes.
```

Then immediately use the **`AskUserQuestion`** tool to offer a health check:

```json
{
  "questions": [
    {
      "question": "Run a health check to verify the installation?",
      "header": "Health check",
      "multiSelect": false,
      "options": [
        { "label": "Yes", "description": "Run a health check on this project now." },
        { "label": "No",  "description": "Skip the health check." }
      ]
    }
  ]
}
```

- If the user answers **Yes**: output exactly `"Run a health check on this project"` as a prompt to trigger the health check flow.
- If the user answers **No**: stop. Do not add anything else.

---

## Auto-update toggle (only if $ARGUMENTS contains a flag)

| Argument | Command | Output |
|----------|---------|--------|
| `--enable-auto` | `bash .claude/dev-team-agents/scripts/update.sh --enable-auto` | `Auto-update enabled.` |
| `--disable-auto` | `bash .claude/dev-team-agents/scripts/update.sh --disable-auto` | `Auto-update disabled.` |

If either flag is present, skip Steps 1–4 and handle only the toggle.

---

## Pin to a specific version (only if $ARGUMENTS is a version tag like `v1.2.3`)

Skip Steps 1–3. Run:

```bash
bash .claude/dev-team-agents/scripts/update.sh $ARGUMENTS
```

Output exactly: `Installed <version>.`
