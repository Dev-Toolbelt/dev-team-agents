---
name: jira
description: Working with Jira via the official Atlassian MCP. Covers MCP detection and setup, issue operations (create, read, update, transition, comment, worklog, link), JQL search, and the branch/worktree naming standard for Jira-tracked tasks.
---

# Jira

## MCP Detection

Before any Jira operation, verify the Atlassian MCP is available by attempting a lightweight call:

```
mcp__atlassian__atlassianUserInfo
```

If the tool is unavailable or returns a connection error, stop and guide the user through installation (see **MCP Setup** below).

---

## MCP Setup

If the Atlassian MCP is not installed, walk the user through these steps:

### Step 1 — Add the MCP server

Run in the project root (or globally with `--global`):

```bash
claude mcp add --transport http atlassian https://mcp.atlassian.com/v1/sse
```

> If using a self-hosted Jira instance, replace the URL with your instance's MCP endpoint, e.g.:
> `https://your-domain.atlassian.net/gateway/api/mcp/v1/sse`

### Step 2 — Authenticate

After adding the server, Claude Code will prompt for Atlassian credentials on first use. The MCP uses OAuth 2.0 — the user must authorize access in the browser popup that appears.

Alternatively, set credentials via environment:

```bash
# API token (recommended for Jira Cloud)
export ATLASSIAN_API_TOKEN=<your-token>
export ATLASSIAN_EMAIL=<your-email>
export ATLASSIAN_URL=https://your-domain.atlassian.net
```

To generate an API token: https://id.atlassian.com/manage-profile/security/api-tokens

### Step 3 — Verify

```
mcp__atlassian__atlassianUserInfo
```

Expected: returns your Atlassian account info. If it fails, re-check the token and URL.

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

```
mcp__atlassian__addCommentToJiraIssue
  issueIdOrKey: "PROJ-123"
  comment: "QA validated on staging. All acceptance criteria met."
```

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

After creating the branch, transition the Jira issue to **In Progress** and optionally assign it to the current user.

---

## Workflow Pattern

When a user asks to start work on a Jira issue:

1. Fetch the issue → `mcp__atlassian__getJiraIssue`
2. Read summary and issue type to determine the branch `type`
3. Propose the branch name: `{type}/{issueKey}_short-description`
4. On approval: create the branch (or worktree)
5. Transition issue to **In Progress**
6. When work is done: transition to **In Review** and add a comment summarizing what was done

When a user asks to create a bug report in Jira:

1. Create issue with type `Bug`, priority matching severity, description with steps to reproduce + expected + actual
2. Link to the PR or commit if available
3. Assign to the responsible developer or leave unassigned per team convention

---

## Conventions

- Always read the issue before creating a branch — the summary informs both `type` and the short description
- Never hard-code `cloudId` — fetch it via `getAccessibleAtlassianResources` on first use
- Prefer `searchJiraIssuesUsingJql` over navigating the UI for bulk lookups
- When moving a status, always call `getTransitionsForJiraIssue` first — transition IDs vary per project workflow
- Comments should be concise and action-oriented — state what was done or what is blocked, not internal notes
