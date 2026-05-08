You are running the **`/devteam:update`** command. Your job is to check for updates and, when available, apply them in a friendly, transparent way.

---

## Step 1 — Read current version

```bash
cat .claude/user-data/.installed-version 2>/dev/null || echo "unknown"
```

Display the current installed version to the user.

---

## Step 2 — Check for updates

Run the check script (bypasses the 24h TTL by deleting the timestamp first, so the check is always fresh):

```bash
rm -f .claude/user-data/.last-update-check
bash .claude/dev-team-agents/scripts/check-updates.sh
```

Capture the output:
- **No output** → already on the latest version. Tell the user: "You are already up to date." Stop here.
- **Output with a new version** → parse current and latest version from the banner and continue to Step 3.

---

## Step 3 — Offer to update

Present the update clearly:

```
A new version of dev-team-agents is available.

  Current : vX.Y.Z
  Latest  : vA.B.C

Would you like to update now? (yes / no)
```

Wait for the user's confirmation before proceeding.

---

## Step 4 — Apply the update (only if the user confirmed)

Run:

```bash
bash .claude/dev-team-agents/scripts/update.sh latest
```

Stream the output to the user as it runs so they can follow progress.

After the script exits successfully, tell the user:
- The update is complete.
- Any agents or skills loaded in the current session are now outdated — start a fresh Claude Code session to pick up the new versions.

---

## Step 5 — Auto-update toggle (only if $ARGUMENTS contains a flag)

| Argument | Action |
|----------|--------|
| `--enable-auto` | Run `bash .claude/dev-team-agents/scripts/update.sh --enable-auto` and confirm to the user |
| `--disable-auto` | Run `bash .claude/dev-team-agents/scripts/update.sh --disable-auto` and confirm to the user |

If either flag is present, skip Steps 1–4 and handle only the toggle.

---

## Pin to a specific version (only if $ARGUMENTS is a version tag like `v1.2.3`)

Skip Steps 1–3. Run:

```bash
bash .claude/dev-team-agents/scripts/update.sh $ARGUMENTS
```

Tell the user which version was installed when the script completes.
