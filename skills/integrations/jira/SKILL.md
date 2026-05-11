---
name: jira
description: Jira via Atlassian MCP — issue ops, JQL, branch naming, PR comment.
---

# Jira

## MCP Detection

Before any Jira operation, verify the Atlassian MCP is available using this three-step check. **Do not show setup instructions until all three steps fail.**

**Step 1 — Check `~/.claude.json` for existing configuration.** Before anything else, read the user-level Claude settings file:

```bash
cat ~/.claude.json
```

Look for an entry under `mcpServers` (or `projects[*].mcpServers`) with a key containing `atlassian` and a URL pointing to `mcp.atlassian.com`. If found, the MCP is already configured — do **not** show setup instructions. Instead, proceed to Step 2. If the MCP is configured but not loaded in the current session, tell the user:

> "The Atlassian MCP is already configured in `~/.claude.json`. It may not have been loaded in this session — please restart Claude Code and try again."

**Step 2 — Check for deferred tools.** Atlassian MCP tools may start in a deferred state in new sessions. Always run ToolSearch:

```
ToolSearch: query="atlassian", max_results=5
```

If ToolSearch returns Atlassian tools (e.g., `mcp__atlassian__atlassianUserInfo`), the MCP is installed — load the schema and proceed to Step 3. Do **not** show setup instructions just because the tool wasn't immediately callable.

**Step 3 — Verify connectivity.** After loading the schema, attempt a lightweight call:

```
mcp__atlassian__atlassianUserInfo
```

If this call succeeds, the MCP is fully operational. If it returns a connection or authentication error (not a "tool not found" error), stop and guide the user through re-authentication (see **MCP Setup** below).

Only show setup instructions when **all three steps fail** — i.e., no `atlassian` entry in `~/.claude.json`, ToolSearch returns no Atlassian tools, AND the direct call fails.

All MCP calls rely on the credentials registered via `claude mcp add --scope local`. These are stored in the user's local Claude Code settings (typically `~/.claude.json`) and are resolved automatically — never hardcode tokens, override headers, or attempt direct HTTP calls to the Atlassian API. If authentication fails, direct the user to re-run the setup command with a valid token rather than working around it.

---

## Project Pattern Detection

After confirming the MCP is available, scan the target project for Jira-specific usage patterns before acting. This ensures behavior adapts to how the team actually uses Jira rather than assuming defaults.

### What to detect

Run a small JQL sample of recent issues to inspect:

```
mcp__atlassian__searchJiraIssuesUsingJql
  jql: "project = PROJ ORDER BY created DESC"
  fields: ["summary", "issuetype", "status", "labels", "components", "priority", "assignee", "reporter", "customfield_*"]
  maxResults: 10
```

Look for:

| Signal | What it tells you |
|--------|-------------------|
| Custom issue types (beyond Story/Bug/Task) | Use those types when creating issues |
| Consistent label patterns | Mirror label conventions on new issues |
| Workflow statuses beyond the standard set | Refer to actual status names; don't assume `In Progress` exists |
| Custom fields present on all issues | Fill them when creating or updating issues |
| Assignee vs. unassigned distribution | Gauge whether auto-assigning is normal for the team |
| Linked issue patterns | Understand how the team structures epics and dependencies |

Store detected patterns in working memory for the session. Do not re-query on every operation.

### Pre-operation assignment confirmation

**Before executing any MCP write operation** (create, update, transition, comment, assign), ask the user once per session:

> "Should I assign this task to you as well?"

If the user answers **yes**: call `mcp__atlassian__lookupJiraAccountId` with the user's email, then set `assignee` on the issue via `mcp__atlassian__editJiraIssue`. If **no**: leave the assignee unchanged. Remember the answer for the rest of the session — do not ask again.

---

## MCP Setup

If the Atlassian MCP is unavailable, guide the user through project-level setup. This approach registers the MCP server in the user's local Claude Code settings for that project only — no files are added to the repository and no global configuration is touched.

**Authentication method: email + API token only.** OAuth is never used. Do not offer or suggest OAuth as an alternative. Before proceeding with any setup step, you must have both the user's Atlassian **email** and **API token** — if either is missing, stop and ask for it explicitly before continuing.

### Step 1 — Generate an API token

Ask the user to visit the following URL and create a new API token:

```
https://id.atlassian.com/manage-profile/security/api-tokens
```

Instructions to pass to the user:
1. Click **Create API token**
2. Give it a label (e.g., `claude-code`)
3. Copy the generated token immediately — it will not be shown again
4. Paste the token here, along with the email address associated with the Atlassian account

### Step 2 — Register the MCP server locally

Once the user provides their **email** and **API token**, compute the Base64-encoded credential yourself:

```bash
echo -n "{email}:{api_token}" | base64
```

Then show the user the ready-to-run command with the computed Base64 value already filled in — do not ask the user to compute anything:

```bash
cd path/to/target/project

claude mcp add atlassian https://mcp.atlassian.com/v1/sse \
  --transport http \
  --header "Authorization: Basic <computed-base64-string>" \
  --scope local
```

The `--scope local` flag stores the configuration in the user's local Claude Code settings for that project only — nothing is written to the repository and nothing is committed.

### Step 3 — Restart Claude Code and verify

Ask the user to restart Claude Code so it picks up the new MCP configuration. Then verify the connection:

```
mcp__atlassian__atlassianUserInfo
```

Expected: returns account name, email, and accessible Atlassian sites. If it fails:
- Confirm the email and token are correct (no trailing spaces)
- Confirm the Base64 string was generated with `email:token` (colon separator, no extra characters)
- Re-run `claude mcp add` with the corrected values — it will overwrite the previous entry
- Confirm Claude Code was restarted after running the command

---

## Core Operations

### Get accessible resources (sites/projects)

```
mcp__atlassian__getAccessibleAtlassianResources
```

Run once to discover available Jira sites and confirm the `cloudId` for Cloud instances.

### Get a single issue

```
mcp__atlassian__getJiraIssue
  issueIdOrKey: "PROJ-123"
```

Returns: summary, description, status, assignee, reporter, priority, labels, components, fix versions, linked issues.

### Search issues (JQL)

```
mcp__atlassian__searchJiraIssuesUsingJql
  jql: "project = PROJ AND sprint in openSprints() AND assignee = currentUser()"
  fields: ["summary", "status", "priority", "assignee"]
  maxResults: 20
```

Common JQL patterns:

| Goal | JQL |
|------|-----|
| Current sprint | `project = PROJ AND sprint in openSprints()` |
| My open issues | `assignee = currentUser() AND statusCategory != Done` |
| Unresolved bugs | `project = PROJ AND issuetype = Bug AND resolution = Unresolved` |
| Recently updated | `project = PROJ AND updated >= -7d ORDER BY updated DESC` |
| By epic | `"Epic Link" = PROJ-10 ORDER BY priority DESC` |

### Create an issue

```
mcp__atlassian__createJiraIssue
  projectKey: "PROJ"
  summary: "Short, imperative description"
  issueType: "Story"        # Story | Bug | Task | Sub-task | Epic
  description: "..."        # Atlassian Document Format (ADF) or plain text
  priority: "Medium"        # Highest | High | Medium | Low | Lowest
  assignee: "account-id"    # optional
  labels: ["backend"]       # optional
```

### Update an issue

```
mcp__atlassian__editJiraIssue
  issueIdOrKey: "PROJ-123"
  summary: "Updated summary"
  description: "..."
  priority: "High"
  assignee: "account-id"
```

### Transition (move status)

Always fetch valid transitions first:

```
mcp__atlassian__getTransitionsForJiraIssue
  issueIdOrKey: "PROJ-123"
```

Then transition:

```
mcp__atlassian__transitionJiraIssue
  issueIdOrKey: "PROJ-123"
  transitionId: "31"        # from getTransitions output
```

Common transition names: `To Do` → `In Progress` → `In Review` → `Done`

### Add a comment

Always fetch the issue first to get the `reporter` field, then prefix the comment body with an attribution line:

```
mcp__atlassian__addCommentToJiraIssue
  issueIdOrKey: "PROJ-123"
  comment: "Created by: @{reporter.displayName}\n\nQA validated on staging. All acceptance criteria met."
```

The `reporter` value comes from `getJiraIssue` → `fields.reporter.displayName`. Always include it as the first line of every comment so there is an auditable record of who triggered the action.

### Log work (worklog)

```
mcp__atlassian__addWorklogToJiraIssue
  issueIdOrKey: "PROJ-123"
  timeSpent: "2h 30m"
  comment: "Implemented the service layer and unit tests"
  started: "2026-05-07T09:00:00.000+0000"    # ISO-8601
```

### Link issues

Get valid link types first:

```
mcp__atlassian__getIssueLinkTypes
```

Then link:

```
mcp__atlassian__createIssueLink
  linkType: "blocks"        # blocks | is blocked by | relates to | duplicates | clones
  inwardIssueKey: "PROJ-100"
  outwardIssueKey: "PROJ-101"
```

---

## Branch / Worktree Naming

When starting work on a Jira issue, create the branch (or worktree) following this pattern:

```
{type}/{taskId}_short-description
```

### Rules

- `{type}` — one of the Conventional Commits types below; choose based on the **issue type and intent**
- `{taskId}` — the Jira issue key exactly as-is (e.g., `VHI-450`, `PROJ-123`)
- `short-description` — lowercase, hyphen-separated, ≤5 words, imperative — derived from the issue summary
- Separator between `taskId` and description: **underscore** (`_`)
- No uppercase in the description part

### Type mapping

| Conventional Commits type | When to use for a Jira issue |
|--------------------------|------------------------------|
| `feat` | New feature (Story, New Feature issue type) |
| `fix` | Bug fix (Bug issue type) |
| `docs` | Documentation task |
| `style` | Visual / formatting only, no logic change |
| `refactor` | Code change that is neither fix nor feature |
| `perf` | Performance improvement task |
| `test` | Adding or correcting tests only |
| `build` | Build system or dependency changes |
| `ci` | CI/CD configuration changes |
| `chore` | Maintenance, config, tooling (Task / Chore issue type) |
| `revert` | Reverting a previous change |

### Examples

```
feat/VHI-450_add-user-authentication
fix/PROJ-123_prevent-double-charge-on-retry
chore/API-88_upgrade-laravel-11
refactor/BACK-210_extract-order-service
test/FE-77_cover-checkout-flow
docs/INFRA-5_update-deployment-runbook
```

### Creating the branch

```bash
# Standard branch
git checkout -b feat/VHI-450_add-user-authentication

# Worktree (if project uses worktree isolation)
# Load skills/shared/worktree/SKILL.md and use its pattern,
# then name the branch following this convention
```

After creating the branch, confirm the assignment preference (see **Project Pattern Detection → Pre-operation assignment confirmation**) and act accordingly. Do not change the issue status — the user manages transitions manually unless they explicitly ask or the project's CLAUDE.md instructs otherwise.

---

## Workflow Pattern

When a user asks to start work on a Jira issue:

1. Fetch the issue → `mcp__atlassian__getJiraIssue`
2. Read summary and issue type to determine the branch `type`
3. Propose the branch name: `{type}/{issueKey}_short-description`
4. On approval: create the branch (or worktree)
5. Ask the assignment question (see **Pre-operation assignment confirmation**); do not change the issue status
6. **PR trigger**: immediately after a PR is created for a Jira-tracked task, ask: "Should I add a comment on {issueKey}?" If the user confirms, post a comment that includes the PR link by default and follows the **QA comment format** (see **Comment Style**).

When a user asks to create a bug report in Jira:

1. Create issue with type `Bug`, priority matching severity, description with steps to reproduce + expected + actual
2. Link to the PR or commit if available
3. Confirm the assignment preference; leave unassigned if the user declines

---

## Comment Style

All comments posted to Jira issues must be written for a **QA audience**: direct, structured, and immediately actionable. No filler, no internal developer notes.

### Required structure

```
@{reporter.displayName}

**PR:** {PR link}

**What was done**
- <concise list of changes — one line per logical change>

**Side effects / risks**
- <list anything that may behave differently after this change — even if low risk>
- None — if no side effects exist

**How to test**
1. <step-by-step instructions the QA should follow to validate the change>
2. <include preconditions, test data, or environment details if relevant>
3. <state the expected outcome for each step>
```

### Rules

- Write in the imperative: "Navigate to…", "Click…", "Verify that…"
- Be specific — mention exact UI labels, endpoints, or config values when relevant
- If the change is backend-only, describe how to verify the observable effect (API response, log entry, DB state)
- Keep "What was done" to ≤5 bullets; longer changes should reference the PR diff
- "Side effects" must always be present — write "None" explicitly rather than omitting the section

---

## Conventions

- Always read the issue before creating a branch — the summary informs both `type` and the short description
- Never hard-code `cloudId` — fetch it via `getAccessibleAtlassianResources` on first use
- Prefer `searchJiraIssuesUsingJql` over navigating the UI for bulk lookups
- **Do not transition issue status automatically.** The user manages workflow transitions manually. Only call `transitionJiraIssue` when the user explicitly requests it or when the target project's CLAUDE.md instructs it. When a transition is requested, always call `getTransitionsForJiraIssue` first — transition IDs vary per project workflow
- Every comment must begin with `Created by: @{reporter.displayName}` — always fetch the reporter from the issue before posting
- All comments must follow the **QA comment format** defined in **Comment Style** — structured, direct, and immediately actionable for a QA engineer
- Always ask the assignment question once per session before any write operation; do not ask again if already answered
