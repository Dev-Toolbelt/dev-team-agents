---
model: haiku
---

Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

---

You are running the **`/devteam:update`** command.

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
v=$(cat .dev-team-agents/user-data/.installed-version 2>/dev/null); echo "${v:-unknown}"
```

Store the output as `<current-version>`. A missing **or empty** version file both resolve to `unknown`.

---

## Step 2 — Repair path (only when `<current-version>` is exactly `unknown`)

An `unknown` version means `.dev-team-agents/user-data/.installed-version` is missing or unreadable — the installation metadata is broken. Do **NOT** report "up to date" and do **NOT** run the version check (it cannot compare an unknown version). Force a fresh reinstall of the latest version to repair the metadata:

```bash
bash .dev-team-agents/scripts/update.sh latest
rm -f .dev-team-agents/user-data/.last-update-check .dev-team-agents/user-data/.last-releases-etag
```

Then read the repaired version:

```bash
cat .dev-team-agents/user-data/.installed-version 2>/dev/null || echo "unknown"
```

Output exactly (substituting the repaired version):

```
Installed version was missing — reinstalled latest.
Now on <repaired-version>. Start a new session to pick up the changes.
```

Then skip Steps 3–5 and stop. Do not add anything else.

---

## Step 3 — Check for updates (only when `<current-version>` is a known version)

Force a fresh check (bypass the 24h TTL **and** the cached ETag, so a `304 Not Modified` cannot mask a version mismatch):

```bash
rm -f .dev-team-agents/user-data/.last-update-check .dev-team-agents/user-data/.last-releases-etag
bash .dev-team-agents/scripts/check-updates.sh
```

**If the script produces no output** → already up to date. Output exactly:

```
Installed: <current-version>
Latest:    <current-version>

Up to date.
```

Then stop. Do not add anything else.

**If the script outputs a banner with a new version** → parse current and latest from the output, then continue to Step 4.

---

## Step 4 — Offer to update

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

## Step 5 — Apply the update (only if user said yes)

```bash
bash .dev-team-agents/scripts/update.sh latest
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
| `--enable-auto` | `bash .dev-team-agents/scripts/update.sh --enable-auto` | `Auto-update enabled.` |
| `--disable-auto` | `bash .dev-team-agents/scripts/update.sh --disable-auto` | `Auto-update disabled.` |

If either flag is present, skip Steps 1–5 and handle only the toggle.

---

## Pin to a specific version (only if $ARGUMENTS is a version tag like `v1.2.3`)

Skip Steps 1–4. Run:

```bash
bash .dev-team-agents/scripts/update.sh $ARGUMENTS
```

Output exactly: `Installed <version>.`
