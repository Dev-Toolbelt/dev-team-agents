# Jira MCP Setup

Guide the user through project-level setup when the Atlassian MCP is unavailable. Registers the MCP server in the CLI's local, project-scoped MCP settings — no files added to the repository, no global configuration touched.

> The commands below use the **Claude Code** CLI (`claude mcp add`). On opencode, add the same server to the `mcp` block of the project's `opencode.json`; on Codex CLI, add it to that CLI's MCP config. For those, the user builds the header value in their own terminal with the first and last lines of Step 2 and `printf '%s:%s' "$E" "$T" | base64 | tr -d '\n'`, and writes it into that config themselves.

**Authentication method: email + API token only.** OAuth is never used. The token never enters the conversation (`skills/shared/credentials/SKILL.md` § 3b): the user creates it and registers the server **in their own terminal**, with the command below.

## Step 1 — Generate an API token

Ask the user to visit:

```
https://id.atlassian.com/manage-profile/security/api-tokens
```

Instructions:
1. Click **Create API token**
2. Give it a label (e.g., `claude-code`)
3. Copy the token immediately — it will not be shown again
4. Keep it for Step 2 — never paste it into the chat

## Step 2 — Register the MCP server locally (Claude Code)

Show the user this command to run **in their own terminal**, from the target project. It asks for the email and the token (hidden), builds the header, and keeps both out of the chat and the shell history:

```bash
printf 'Atlassian email: '; read -r E
printf 'API token: '; stty -echo; read -r T; stty echo; echo
claude mcp add atlassian https://mcp.atlassian.com/v1/sse \
  --transport http \
  --header "Authorization: Basic $(printf '%s:%s' "$E" "$T" | base64 | tr -d '\n')" \
  --scope local
unset E T
```

The `--scope local` flag stores the configuration in the user's local Claude Code settings for that project only — nothing is written to the repository. Other CLIs: use their project-scoped MCP config so the credential stays out of the repo.

## Step 3 — Restart and verify

Ask the user to restart their CLI, then verify:

```
mcp__atlassian__atlassianUserInfo
```

Expected: returns account name, email, and accessible Atlassian sites.

If it fails:
- Confirm email and token are correct (no trailing spaces)
- Confirm Base64 was generated with `email:token` (colon separator, no extra characters)
- Re-run `claude mcp add` with corrected values — overwrites the previous entry
- Confirm the CLI was restarted
