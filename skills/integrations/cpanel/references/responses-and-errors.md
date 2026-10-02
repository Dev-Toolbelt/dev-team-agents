# UAPI Responses and Errors

## Response Envelope

Every UAPI function returns the same `result` shape:

| Field | Type | Meaning |
|---|---|---|
| `status` | `1` / `0` | **The only success signal.** `1` = success, `0` = failure |
| `data` | object / array / string / null | Function output (shape per function, see module references) |
| `errors` | array of string / null | Why the call failed |
| `warnings` | array of string / null | Non-fatal problems — the call succeeded but something is off |
| `messages` | array of string / null | Informational messages |
| `metadata` | object | Extra info: `transformed`, `paginate`, record counts |

Where the envelope sits depends on the call method:

| Call method | Path to `status` |
|---|---|
| HTTP `/execute/...` | top level: `body.status`, `body.data` |
| CLI `uapi --output=json` | `.result.status` (wrapped with `apiversion`, `module`, `func`) |
| LiveAPI PHP | `$res['cpanelresult']['result']['status']` |
| LiveAPI Perl | `$res->{cpanelresult}{result}{status}` |
| `Batch::strict` | outer `status` plus each item in `data[]` has its own envelope |

```json
{
  "status": 1,
  "data": "info+example.com",
  "errors": null,
  "warnings": null,
  "messages": null,
  "metadata": {}
}
```

## Handling Rules

1. **Check `status`, never the HTTP code alone.** A function-level failure still comes back as HTTP `200` with `status: 0`.
2. HTTP non-2xx means transport or authentication trouble: `401`/`403` = bad, expired or insufficient token; `5xx` = server issue. Treat these separately from API errors.
3. Surface `errors[]` to the user verbatim; they are localized, human-readable strings.
4. Log `warnings[]`. A successful call can still carry, for example, a "permissions not applied" warning from `Fileman::upload_files`.
5. CLI calls that fail before the function runs (bad module or function name, bad user) do **not** return the metadata block. Parse defensively.
6. Write calls with `rollback: none` (most of them) leave partial state on failure. Read the state back before retrying. Calls marked `rollback: clean` are reverted by the server.

## Common Failure Causes

| Symptom | Likely cause | Fix |
|---|---|---|
| `401` / login page HTML instead of JSON | Wrong header format, revoked/expired token, wrong user | `Authorization: cpanel <user>:<token>` — note the literal word `cpanel`, then `user:token` |
| HTML returned on `2087` | Called UAPI on a WHM port | Use `2083`, or WHM API 1 `uapi_cpanel` |
| `status 0` with "feature" / "not permitted" error | The account's feature list lacks the feature | `Features::has_feature` → ask the host to enable it |
| Function "disabled" / unknown | Server profile disabled the role (Mail, DNS, MySQL, Web Server…) | Check roles; pick a different function or ask the host |
| `status 0` on DB functions with "invalid name" | Missing DB prefix or name too long | `Mysql::get_restrictions` → `prefix`, `max_database_name_length` |
| `DNS::mass_edit_zone` rejected | Stale `serial` | Re-read with `DNS::parse_zone`, take the current SOA serial, retry once |
| Read-only token rejected on write | Token created with `readonly=1` | Use a full token for mutating calls |
| `true`/`false` ignored | Booleans must be `1`/`0` | Send `1`/`0` |
| Function exists in docs but not on the server | Older cPanel version | Compare the function's `since` value in the module reference with `ServerInformation::get_information` / the cPanel version |

## Idempotency and Retries

- Most `add_*` / `create_*` functions are **not** idempotent: a retry after a timeout may fail with "already exists". Before retrying, check the current state with the matching `list_*` function.
- Retry only on transport errors (timeouts, `5xx`). Never auto-retry a `status: 0` response; it is a decision, not a glitch.
- Long-running operations return a task or operation ID instead of blocking: `VersionControlDeployment::create` (`deploy_id`, `task_id`, `sse_url`), `WebsiteBackup::*` (`operation_status`), `Backup::fullbackup_*`, `ExtractInfo::progress`. Poll the matching status function.
