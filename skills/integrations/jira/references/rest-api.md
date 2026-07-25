# Jira REST API Fallback

Use this reference when all three MCP detection steps fail — the MCP is configured but not loaded, or the user is in a new session where the MCP cannot be reached.

## Step 1 — Extract credentials

```bash
cat ~/.claude.json 2>/dev/null
cat .mcp.json 2>/dev/null
```

Look for the `atlassian` entry under `mcpServers`:

```json
{
  "mcpServers": {
    "atlassian": {
      "type": "sse",
      "url": "https://mcp.atlassian.com/v1/sse",
      "headers": {
        "Authorization": "Basic <base64-encoded-email:token>"
      }
    }
  }
}
```

If neither file has an `atlassian` entry, ask the user for email + API token, then compute:

```bash
echo -n "{email}:{api_token}" | base64
```

## Step 2 — Determine Jira cloud URL

1. Check conversation for a domain mention (e.g., `mycompany.atlassian.net`)
2. Check `docs/project.md` or `CLAUDE.md`
3. Ask the user: *"What is your Jira cloud URL?"*

Store as `JIRA_BASE` for the session.

## Step 3 — Make REST API calls

```bash
AUTH="Basic <extracted-base64-value>"
JIRA_BASE="https://mycompany.atlassian.net"

# Get an issue
curl -s -H "Authorization: $AUTH" -H "Accept: application/json" \
     "$JIRA_BASE/rest/api/3/issue/PROJ-123"

# Search with JQL
curl -s -H "Authorization: $AUTH" -H "Accept: application/json" \
     "$JIRA_BASE/rest/api/3/issue/search?jql=project%3DPROJ%20AND%20sprint%20in%20openSprints()&fields=summary,status,priority,assignee&maxResults=20"

# Create an issue
curl -s -X POST \
     -H "Authorization: $AUTH" -H "Content-Type: application/json" -H "Accept: application/json" \
     -d '{"fields":{"project":{"key":"PROJ"},"summary":"Short description","issuetype":{"name":"Story"}}}' \
     "$JIRA_BASE/rest/api/3/issue"

# Add a comment (ADF body)
curl -s -X POST \
     -H "Authorization: $AUTH" -H "Content-Type: application/json" -H "Accept: application/json" \
     -d '{"body":{"type":"doc","version":1,"content":[{"type":"paragraph","content":[{"type":"text","text":"Comment text here"}]}]}}' \
     "$JIRA_BASE/rest/api/3/issue/PROJ-123/comment"

# Transition an issue
curl -s -X POST \
     -H "Authorization: $AUTH" -H "Content-Type: application/json" -H "Accept: application/json" \
     -d '{"transition":{"id":"31"}}' \
     "$JIRA_BASE/rest/api/3/issue/PROJ-123/transitions"

# Get available transitions
curl -s -H "Authorization: $AUTH" -H "Accept: application/json" \
     "$JIRA_BASE/rest/api/3/issue/PROJ-123/transitions"
```

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
- Never store extracted credentials in any file; use them only for the session duration
- If credentials not found and user cannot provide them, guide through MCP Setup before continuing
