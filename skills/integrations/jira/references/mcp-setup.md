# Jira MCP Setup

Guide the user through project-level setup when the Atlassian MCP is unavailable. Registers the MCP server in the CLI's local, project-scoped MCP settings — no files added to the repository, no global configuration touched.

> The commands below use the **Claude Code** CLI (`claude mcp add`). On opencode, add the same server to the `mcp` block of the project's `opencode.json`; on Codex CLI, add it to that CLI's MCP config. The credential computation in Step 2 is identical for all three.

**Authentication method: email + API token only.** OAuth is never used. Before any setup step, you must have both the user's Atlassian **email** and **API token** — if either is missing, stop and ask explicitly.

## Step 1 — Generate an API token

Ask the user to visit:

```
https://id.atlassian.com/manage-profile/security/api-tokens
```

Instructions:
1. Click **Create API token**
2. Give it a label (e.g., `claude-code`)
3. Copy the token immediately — it will not be shown again
4. Paste the token here, along with the associated Atlassian account email

## Step 2 — Register the MCP server locally (Claude Code)

Compute the Base64-encoded credential yourself:

```bash
echo -n "{email}:{api_token}" | base64
```

Show the user the ready-to-run command with the computed Base64 value already filled in:

```bash
cd path/to/target/project

claude mcp add atlassian https://mcp.atlassian.com/v1/sse \
  --transport http \
  --header "Authorization: Basic <computed-base64-string>" \
  --scope local
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
