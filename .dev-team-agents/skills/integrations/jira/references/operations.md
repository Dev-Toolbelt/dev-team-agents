# Jira Core Operations Reference

Full MCP tool call details. Load when executing Jira operations that require exact parameter names or when building composite workflows.

## Get accessible resources

```
mcp__atlassian__getAccessibleAtlassianResources
```

Run once to discover available Jira sites and confirm the `cloudId` for Cloud instances.

## Get a single issue

```
mcp__atlassian__getJiraIssue
  issueIdOrKey: "PROJ-123"
```

Returns: summary, description, status, assignee, reporter, priority, labels, components, fix versions, linked issues.

## Search issues (JQL)

```
mcp__atlassian__searchJiraIssuesUsingJql
  jql: "project = PROJ AND sprint in openSprints() AND assignee = currentUser()"
  fields: ["summary", "status", "priority", "assignee"]
  maxResults: 20
```

### Common JQL patterns

| Goal | JQL |
|------|-----|
| Current sprint | `project = PROJ AND sprint in openSprints()` |
| My open issues | `assignee = currentUser() AND statusCategory != Done` |
| Unresolved bugs | `project = PROJ AND issuetype = Bug AND resolution = Unresolved` |
| Recently updated | `project = PROJ AND updated >= -7d ORDER BY updated DESC` |
| By epic | `"Epic Link" = PROJ-10 ORDER BY priority DESC` |

## Create an issue

```
mcp__atlassian__createJiraIssue
  projectKey: "PROJ"
  summary: "Short, imperative description"
  issueType: "Story"        # Story | Bug | Task | Sub-task | Epic
  description: "..."        # ADF or plain text
  priority: "Medium"        # Highest | High | Medium | Low | Lowest
  assignee: "account-id"    # optional
  labels: ["backend"]       # optional
```

## Update an issue

```
mcp__atlassian__editJiraIssue
  issueIdOrKey: "PROJ-123"
  summary: "Updated summary"
  description: "..."
  priority: "High"
  assignee: "account-id"
```

## Transition (move status)

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

## Add a comment

Always fetch the issue first to get the `reporter` field:

```
mcp__atlassian__addCommentToJiraIssue
  issueIdOrKey: "PROJ-123"
  comment: "Created by: @{reporter.displayName}\n\n<body>"
```

## Log work

```
mcp__atlassian__addWorklogToJiraIssue
  issueIdOrKey: "PROJ-123"
  timeSpent: "2h 30m"
  comment: "Implemented the service layer and unit tests"
  started: "2026-05-07T09:00:00.000+0000"    # ISO-8601
```

## Link issues

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

## Comment style

All comments must follow the QA comment format:

```
@{reporter.displayName}

**PR:** {PR link}

**What was done**
- <concise list — one line per logical change>

**Side effects / risks**
- <anything that may behave differently — write "None" explicitly if none>

**How to test**
1. <step-by-step instructions>
2. <include preconditions, test data, environment details if relevant>
3. <expected outcome for each step>
```

Rules: imperative voice ("Navigate to…", "Click…", "Verify that…"); specific — mention exact UI labels, endpoints, config values; "Side effects" must always be present; keep "What was done" to ≤5 bullets.
