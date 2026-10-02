# UAPI Calling Conventions

Source: *Introduction to UAPI* (api.docs.cpanel.net/cpanel/introduction) and the cPanel UAPI OpenAPI spec.

## Anatomy of a Call

```
https://<host>:2083/execute/<Module>/<function>?<param>=<value>&<param>=<value>
```

| Part | Rule |
|---|---|
| `Module` | CamelCase, case-sensitive (`Email`, `Mysql`, `SubDomain`, `VersionControlDeployment`) |
| `function` | lowercase snake_case (`add_pop`, `list_databases`); some legacy names have no underscore (`addsubdomain`, `addaddondomain`) |
| Parameters | `key=value`, URI-encoded, joined with `&` |
| Notation in docs/this skill | `Module::function` |

## Value Encoding

| Kind | How to send |
|---|---|
| **Boolean** | `1` / `0` — the APIs do **not** accept `true` / `false` |
| String with special chars | URI-encode (`%2C` for `,`, `%20` for space, `%40` for `@`) |
| **Repeated value / list** | Repeat the key (`remove=3&remove=7`) or index it (`command-0=…&command-1=…`) — check the function's parameter notes |
| JSON value | Serialize to a string, then URI-encode (`add={"dname":"www","ttl":300,"record_type":"A","data":["203.0.113.10"]}`) |
| Dotted names | Literal (`services.email.enabled=1` in `UserManager::create_user`) |
| Prefixed DB names | When DB prefixing is on, `user_dbname` — get the prefix from `Mysql::get_restrictions` |

## HTTP Method

- The spec documents most functions as `GET`. 33 operations are `POST` — mainly file uploads (`Fileman::upload_files` needs `multipart/form-data`) and large payloads.
- For calls that carry **secrets** (`password`, `key`, `cert`) or long payloads (`Batch::strict`, `Fileman::save_file_content`), send `POST` with `application/x-www-form-urlencoded` so values do not land in access logs or proxies. The `Batch::strict` docs explicitly recommend POST for long calls. Validate POST on the target server version once before relying on it.

## Call Methods

### HTTP (remote integrations)

```bash
curl -sS -H "Authorization: cpanel $CPANEL_USER:$CPANEL_TOKEN" \
  --data-urlencode "email=info" \
  --data-urlencode "password=$MAILBOX_PASSWORD" \
  --data-urlencode "domain=example.com" \
  "https://$CPANEL_HOST:2083/execute/Email/add_pop"
```

### CLI on the server

```bash
uapi --user=username --output=jsonpretty Email add_pop email='info' password='s3cret' domain='example.com'
```

| Flag | Values |
|---|---|
| `--output` | `json`, `jsonpretty`, `yaml` (default `yaml`) |
| `--user` | Target cPanel account (required when running as root) |
| `uapi --help` | Built-in help |

- Space-separate `key=value` pairs; quote or escape special characters: `key='{"a":1}'` or `key=[\"a\",\"b\"]`.
- CLI calls that fail **before** the function runs do not return the usual metadata.
- On CloudLinux: `/usr/local/cpanel/bin/uapi`.
- A few functions have `CLI support: False` (for example, `Fileman::upload_files`). The module references flag them.

### LiveAPI PHP (inside cPanel)

```php
require_once "/usr/local/cpanel/php/cpanel.php";
$cpanel = new CPANEL();                       // connect once
$res = $cpanel->uapi('Email', 'list_pops', ['regex' => 'info']);
if ($res['cpanelresult']['result']['status']) {
    $data = $res['cpanelresult']['result']['data'];
} else {
    $errors = $res['cpanelresult']['result']['errors'];
}
$cpanel->end();                               // disconnect once
```

### LiveAPI Perl (inside cPanel)

```perl
use Cpanel::LiveAPI ();
my $cpanel = Cpanel::LiveAPI->new();
my $res = $cpanel->uapi('Email', 'list_pops', { regex => 'info' });
my $ok  = $res->{cpanelresult}{result}{status};
$cpanel->end();
```

If a LiveAPI call misbehaves, retry the same call from a browser session to isolate the problem.

## Client Snippets

### Python

```python
import os, requests

BASE = f"https://{os.environ['CPANEL_HOST']}:2083/execute"
HEADERS = {"Authorization": f"cpanel {os.environ['CPANEL_USER']}:{os.environ['CPANEL_TOKEN']}"}

def uapi(module: str, function: str, **params):
    r = requests.post(f"{BASE}/{module}/{function}", headers=HEADERS, data=params, timeout=60)
    r.raise_for_status()                      # transport/auth errors (401, 5xx)
    body = r.json()
    if not body.get("status"):                # API-level failure arrives as HTTP 200
        raise RuntimeError("; ".join(body.get("errors") or ["unknown UAPI error"]))
    for w in body.get("warnings") or []:
        print("UAPI warning:", w)
    return body.get("data")

print(uapi("DomainInfo", "list_domains"))
```

### Node.js (fetch)

```js
const base = `https://${process.env.CPANEL_HOST}:2083/execute`;
const auth = `cpanel ${process.env.CPANEL_USER}:${process.env.CPANEL_TOKEN}`;

export async function uapi(module, fn, params = {}) {
  const res = await fetch(`${base}/${module}/${fn}`, {
    method: 'POST',
    headers: { Authorization: auth, 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(params),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const body = await res.json();
  if (!body.status) throw new Error((body.errors ?? ['unknown UAPI error']).join('; '));
  return body.data;
}
```

### PHP (Guzzle)

```php
$client = new GuzzleHttp\Client([
    'base_uri' => "https://{$host}:2083/execute/",
    'headers'  => ['Authorization' => "cpanel {$user}:{$token}"],
    'timeout'  => 60,
]);
$body = json_decode((string) $client->post('Mysql/create_database', [
    'form_params' => ['name' => "{$prefix}app"],
])->getBody(), true);
if (!$body['status']) { throw new RuntimeException(implode('; ', $body['errors'] ?? [])); }
```

## Batch Calls

`Batch::strict` runs several UAPI calls **in order** and stops at the first failure. It does **not** roll back the calls that already succeeded.

```bash
uapi --user=username Batch strict \
  command-0='["Mysql","create_database",{"name":"user_app"}]' \
  command-1='["Mysql","create_user",{"name":"user_app","password":"…"}]' \
  command-2='["Mysql","set_privileges_on_database",{"user":"user_app","database":"user_app","privileges":"ALL PRIVILEGES"}]'
```

- Each `command` is a JSON array `[Module, function, {params}]`; the params object is optional.
- HTTP query string: repeat `command=` (no index needed). LiveAPI PHP/Perl: you **must** index (`command-0`, `command-1`, …).
- Result `data` is an array of per-call results, each with its own `status`/`errors`/`data`.

## Calling UAPI as Root or Reseller

Use WHM API 1 `uapi_cpanel` on port `2087` with a WHM token. It proxies a UAPI call for a named cPanel user (`cpanel.user`, `cpanel.module`, `cpanel.function`, plus the function's parameters). Some functions refuse the proxy, for example `Fileman::upload_files`; the module references note this. WHM API 1 itself is out of scope for this skill.

## Do Not

- Do **not** drive cPanel by posting to interface URLs (`/frontend/jupiter/.../index.html`). It is unsupported and breaks between versions. Always call the API function.
- Do **not** call a UAPI function through another API's call method (cPanel API 1/API 2 call styles).
- Do **not** assume a function exists: server profiles (roles) disable groups of functions. For example, disabling *Receive Mail* disables the `Email::*` mailbox functions. Check `Features::has_feature` or `Features::list_features`, and handle the error.
