# Jira REST API Fallback

Use this reference when all three MCP detection steps fail — the MCP is configured but not loaded, or the user is in a new session where the MCP cannot be reached.

## Step 1 — Credentials

The token never enters the conversation and is never read from an MCP config (`skills/shared/credentials/SKILL.md` § 3b). The REST fallback uses a `jira` group in `credentials.local.json`:

```json
"jira": { "site": "https://mycompany.atlassian.net", "email": "you@example.com", "token": { "$ref": "..." }, "$secrets": ["token"] }
```

If the group or its `token` is missing, follow the last row of credentials § 3b: the user stores it in the app's Credentials tab (or by hand, then `devteam cred local secure --apply`). The site URL may be asked for directly — it is not a secret.

## Step 2 — Make REST API calls

Run every call through `devteam cred local exec`. The credentials reach `curl` on stdin (`--config -`), never on a command line:

```bash
jira() {  # usage: jira <path> [curl args…]
  devteam cred local exec /jira -- sh -c '
    p="$1"; shift
    printf "user = \"%s:%s\"\n" "$DEVTEAM_EMAIL" "$DEVTEAM_TOKEN" |
      curl -s --config - -H "Accept: application/json" "$@" "$DEVTEAM_SITE$p"
  ' sh "$@"
}

# Get an issue
jira /rest/api/3/issue/PROJ-123

# Search with JQL
jira "/rest/api/3/issue/search?jql=project%3DPROJ%20AND%20sprint%20in%20openSprints()&fields=summary,status,priority,assignee&maxResults=20"

# Create an issue
jira /rest/api/3/issue -X POST -H "Content-Type: application/json" \
     -d '{"fields":{"project":{"key":"PROJ"},"summary":"Short description","issuetype":{"name":"Story"}}}'

# Add a comment (ADF body)
jira /rest/api/3/issue/PROJ-123/comment -X POST -H "Content-Type: application/json" \
     -d '{"body":{"type":"doc","version":1,"content":[{"type":"paragraph","content":[{"type":"text","text":"Comment text here"}]}]}}'

# Transition an issue
jira /rest/api/3/issue/PROJ-123/transitions -X POST -H "Content-Type: application/json" \
     -d '{"transition":{"id":"31"}}'

# Get available transitions
jira /rest/api/3/issue/PROJ-123/transitions
```

A write (`POST`, `PUT`) follows the same consent rules as through the MCP.

## REST API parity with MCP operations

| MCP tool | REST API equivalent |
|----------|---------------------|
| `getJiraIssue` | `GET /rest/api/3/issue/{key}` |
| `searchJiraIssuesUsingJql` | `GET /rest/api/3/issue/search?jql=...` |
| `createJiraIssue` | `POST /rest/api/3/issue` |
| `editJiraIssue` | `PUT /rest/api/3/issue/{key}` |
| `getTransitionsForJiraIssue` | `GET /rest/api/3/issue/{key}/transitions` |
| `transitionJiraIssue` | `POST /rest/api/3/issue/{key}/transitions` |
| `addCommentToJiraIssue` | `POST /rest/api/3/issue/{key}/comment` (ADF body) |
| `addWorklogToJiraIssue` | `POST /rest/api/3/issue/{key}/worklog` |
| `lookupJiraAccountId` | `GET /rest/api/3/user/search?query={email}` |
| `getIssueLinkTypes` | `GET /rest/api/3/issueLinkType` |
| `createIssueLink` | `POST /rest/api/3/issueLink` |

## ADF (Atlassian Document Format)

Used for comments and descriptions:

```json
{
  "type": "doc",
  "version": 1,
  "content": [
    {
      "type": "paragraph",
      "content": [{ "type": "text", "text": "Your text here" }]
    }
  ]
}
```

## Fallback behavior rules

- Use only when all three MCP detection steps fail
- Apply the same Core Operations, Comment Style, Branch Naming, and Conventions rules — behavior must be identical regardless of transport
- Never print, echo or store the email:token pair or the `DEVTEAM_*` variables
- If the `jira` group is missing and the user prefers the MCP, guide through MCP Setup before continuing
