# ADR-0031: Agents call integration APIs through a CLI proxy that holds the token

**Date:** 2026-10-02
**Status:** Accepted
**Deciders:** dev-team-agents maintainers
**Relates to:** [ADR-0023](0023-integrations-are-account-level-connections-whose-network-calls-live-in-the-cli.md) (resolves its follow-up "agents should consume `devteam integration`"), [ADR-0010](0010-credential-values-in-the-os-keychain-with-non-secret-reference-files.md)

## Context

ADR-0023 gave GitHub and Jira account-level connections: the token lives in the secret store, is bound
to the origin it was issued for, and every read is audited. It gave **agents** no way to use the
connection. The only API calls the CLI makes are its own `test` and `resources`.

The trigger for this ADR was a Cloudflare integration "so that agents can execute functions via the
API": change DNS records, purge cache, list Workers, read R2 and KV. The existing
`skills/devops/cloudflare` skill answered that by asking the user to export `CLOUDFLARE_API_TOKEN`.
That puts a long-lived, write-capable token in the environment of every process the agent starts, in
the model's context whenever it is echoed, and in any log that captures the environment.

| Option | Token printed into the agent's context | Origin-bound | Request recorded | Write guard |
|---|---|---|---|---|
| Env var the user exports | Whenever echoed | No | No | None |
| `devteam cred get` piped into `curl` | Yes, in the transcript | No | One read line | None |
| **The CLI makes the request** | **No** | **Yes (ADR-0023 policy)** | **Every call** | **`--allow-write`** |

## Decision

### 1. `devteam integration call` is the agent's API entry point

```
devteam integration call <name> <METHOD> <endpoint> [--query k=v]… [--data JSON | --data-file FILE|-] [--allow-write] [--path P] [--json]
```

The CLI checks the endpoint and reads the token through `creds.get_value`, which writes the ADR-0010
audit line. It then sends the request under the ADR-0023 HTTP policy: https only, the configured
origin only, **no redirect followed**, 10 s / 20 s timeouts and a 2 MB response cap. It prints the
API's JSON response. The command line accepts no abbreviated options (`allow_abbrev=False`), so
`--allow` is not `--allow-write`. Request bodies are strict JSON (no `NaN` / `Infinity`), at most 1 MB.

### 2. Opt-in per adapter

Only an adapter that sets `supports_call = True` accepts `call`. Cloudflare is the first. GitHub and
Jira stay out: agents already reach them through `gh` and the Atlassian MCP, and widening their
surface is a separate decision. An adapter that opts in also declares `forbidden_endpoints` (§5) and
may declare `describe_error(body)`, which turns the API's error body into one line for the
human-mode message.

### 3. The endpoint is a path, never a URL

- **Shape.** The endpoint must be an absolute path of RFC 3986 path characters.
  - Refused: a query string, a fragment, an empty segment, a `.` or `..` segment.
  - Refused: a percent-escape that decodes to `/`, `\`, `.`, `%` or a control character. That rules
    out `..%2f`, `%2e%2e` and the double-encoded `%252e`.
  - Query parameters go through `--query`.
- **Checked before the token is read.** These checks run first, so a malformed call never touches the
  keychain.
- **Placeholders.**
  - `{field}` placeholders such as `{zone_id}` and `{account_id}` take the configured account and
    project values. The origin field cannot be a placeholder.
  - Each value is re-validated by the adapter, because the account file is hand-editable, then
    percent-encoded. The filled path is checked again.
- **Unreadable project binding.** A binding that cannot be read is an error. It is not treated as an
  unset field.
- **`api_url`.** The Cloudflare adapter accepts only `https://api.cloudflare.com/client/v4` and its
  FedRAMP twin, so a mistyped or hostile URL never receives a token.

### 4. Reads are free; writes need `--allow-write` and the user's confirmation

`GET` runs without a flag. `POST`, `PUT`, `PATCH` and `DELETE` are refused, and nothing is sent, unless
`--allow-write` is passed.

The skill (`skills/integrations/cloudflare-api`) sets the rule for that flag. An agent passes
`--allow-write` only after both steps below:

1. It has shown the user the exact request with `AskUserQuestion`.
2. The user answered yes.

Afterwards the agent reads the record back to verify the change. The flag is passed by the agent
itself, so this is a **policy gate, not a technical one** (see Threat model).

### 5. Endpoints whose response is a credential are never called

`forbidden_endpoints` is matched on the decoded, filled-in path. Such a call is refused even with
`--allow-write`. For Cloudflare the list covers:

- creating, reading or rolling API tokens (user and account; `…/tokens/verify` stays callable)
- the Global API Key
- tunnel and WARP-connector tokens
- Access service tokens
- R2 temporary credentials

Calling any of these would put a new secret in the transcript.

### 6. Failure is an environment error that carries the API's own answer

A non-2xx answer exits `3`. Its `details` carry:

| Key | Content |
|---|---|
| `state` | The ADR-0023 state (`invalid_token`, `rate_limited`, `unreachable`) |
| `http_status` | The HTTP status code |
| `retry_after` | Seconds to wait, only when the server sent `Retry-After` |
| `response` | The API's JSON error body |

In human mode the message carries the adapter's one-line summary of that body. For Cloudflare that is
`[code] message`, so the error is not lost without `--json`. A successful answer that is not JSON (a
raw KV value, a zone file) gets a hint that points at the provider's own CLI. Neither the token nor
the request headers can appear in any of this, because `http.py` builds every message itself.

### 7. Every call is recorded

Each call appends an `integration-call` line to the global credential audit log. The line holds the
method, the resolved path, `allow_write`, the project id, the HTTP status on failure, and an outcome:
`ok`, `failed`, or `refused` for a call stopped before sending. It never holds the body, the query
values or the response. Calls that send a request also leave the ADR-0010 token-read line.

### 8. Store-neutral, and not an app operation

- **Compat class.** `call` writes none of the shapes `store_schemas()` declares, but it can write to
  the remote account, so `compat` classifies it **store-neutral** (never refused to a declared
  client). The remote write is governed by §4, not by the client schema gate.
- **Desktop app.** The app does not get `call`: `ALLOWED_COMMANDS` in `app/src/cli/operations.ts`
  leaves it out, and a test pins that. Running arbitrary API requests is an agent capability, not a
  settings screen.

### 9. The integration token is not readable by an agent

`03-credential-guard.sh` refuses `devteam cred get integration.*` in a PreToolUse hook, on every
provider through the shared dispatcher. No agent task needs the value. A user who does can run the
command in their own terminal, which no hook sees.

## Threat model

The proxy removes the **need** to expose the token, and gives agents one path that is easy to audit.
It is **not an isolation boundary**. An agent with a shell runs as the user, and ADR-0010 already
says so: "an agent with Bash can read anything the user can read". The credential-guard rule in §9
matches command text and can be bypassed like every rule in that hook. `--allow-write` is passed by
the same agent it guards.

**API responses are third-party content.** Firewall events, DNS comments and rule descriptions carry
text written by people outside the conversation, and a prompt injection there can try to steer the
agent into a write. Three things stand against it:

- the skill's rule that a response is data, never an instruction
- the confirmation step in §4
- the forbidden endpoints in §5, which hold even when the agent is fooled

A provider-native confirmation for write calls, one the agent cannot answer itself, was the remaining
gap. [ADR-0032](0032-bind-writes-provider-native-ask-rules-for-integration-writes.md) closes it: `bind`
and the installers write each provider's own "ask" rule for a write call (Claude Code
`permissions.ask`, opencode `permission.bash`, a Codex `prefix_rule`), and `call` refuses a write that
is not in the form those rules match.

## Provider parity

| Provider | How it gets this |
|---|---|
| claude | The `call` command (a shell command), the skill through the `skills/` symlink, the guard through `.claude/settings.json` → `pre-tool-use.sh` |
| opencode | The same command and skill. The guard runs through the plugin's `tool.execute.before` → `pre-tool-use.sh`, where exit 2 blocks |
| codex | The same command and skill. The guard runs through the Codex PreToolUse hook → `pre-tool-use.sh`. `AskUserQuestion` maps to the Codex equivalent through `scripts/lib/tool-map.json`, and `check-codex-compat.sh` passes on the rendered agents |

## Consequences

- **Setup.** An agent can use Cloudflare through a connection the user set up once with
  `devteam integration connect cloudflare`. It never needs a token in its environment.
- **Audit.** The audit log shows which requests agents made: method and path, never content.
- **Bodies.** Only JSON bodies are supported. Multipart endpoints (a Worker script upload, KV values
  with metadata) stay with `wrangler`, which the skill says.
- **Size.** Responses above 2 MB fail, and the skill tells agents to paginate.
- **Stored status.** A `call` failing with 401 does not update the stored integration status. The
  next `integration test` does.
- **Contract.** The success payload `{integration, method, endpoint, response}` is pinned in
  `tests/test_json_contract.py` (`AGENT_FACING_KEYS`). `response` is whatever the remote API returned
  and is not part of the contract.
- **Future adapters.** An adapter that wants `call` sets `supports_call = True` and declares its
  `forbidden_endpoints`. It does not need a new ADR unless it changes the endpoint or write rules.
