# UAPI Recipes — Common Tasks End to End

Every function and parameter name below was checked against the cPanel UAPI OpenAPI spec (11.138). For the full parameter list of any function, open it from [function-index.md](function-index.md).

Conventions used here:

```bash
export CPANEL_HOST=server.example.com CPANEL_USER=myuser CPANEL_TOKEN=…   # from a secret store, never committed
uapi_http() {  # uapi_http Module function key=value …   (POST, form-encoded)
  local mod=$1 fn=$2; shift 2
  local args=(); for kv in "$@"; do args+=(--data-urlencode "$kv"); done
  curl -sS -H "Authorization: cpanel $CPANEL_USER:$CPANEL_TOKEN" "${args[@]}" \
    "https://$CPANEL_HOST:2083/execute/$mod/$fn"
}
```

On the server itself, replace `uapi_http` with `uapi --user=$CPANEL_USER --output=jsonpretty`.

Every recipe ends with a **verify** step. Never report success from `status: 1` of a write alone when a `list_*` read-back is cheap.

---

## 0. Bootstrap an Integration

| Step | Call | Notes |
|---|---|---|
| 1 | `Tokens::create_full_access name=<app> [expires_at=<unix>] [readonly=1]` | Once, from the UI or CLI; store `data.token` in a secret manager |
| 2 | `ServerInformation::get_information` | Connectivity + auth smoke test |
| 3 | `Features::list_features` / `Features::has_feature name=<feature>` | Confirm that the account can use what you need |
| 4 | `Quota::get_quota_info`, `ResourceUsage::get_usages` | Baseline limits before you create things |

---

## 1. Email Account Lifecycle

| Goal | Call |
|---|---|
| Create (recommended) | `UserManager::create_user username=info domain=example.com password=… services.email.enabled=1 services.email.quota=1024` |
| Create (classic) | `Email::add_pop email=info domain=example.com password=… quota=1024` |
| List | `Email::list_pops` (light) / `Email::list_pops_with_disk domain=example.com` (usage: `diskused`, `diskquota`, `suspended_login`) |
| Change password | `Email::passwd_pop email=info domain=example.com password=…` |
| Change quota | `Email::edit_pop_quota email=info domain=example.com quota=2048` |
| Suspend / resume login | `Email::suspend_login email=info@example.com` / `Email::unsuspend_login …` |
| Delete | `Email::delete_pop email=info domain=example.com` |

- cPanel recommends `UserManager::create_user` over `Email::add_pop`, because `add_pop` is incompatible with the *Reset Password* feature.
- `cpanel` is not a valid mailbox name. `quota=0`/`unlimited` works only when no maximum quota is set.
- Disabling the *Receive Mail* server role disables these functions.

```bash
uapi_http Email add_pop email=info domain=example.com "password=$MAILBOX_PW" quota=1024
uapi_http Email list_pops_with_disk domain=example.com api.filter=1 api.filter_column=user api.filter_term=info api.filter_type=eq   # verify
```

## 2. Forwarders and Autoresponders

| Goal | Call |
|---|---|
| Forward to an address | `Email::add_forwarder domain=example.com email=sales@example.com fwdopt=fwd fwdemail=alice@example.org` |
| Bounce with a message | `… fwdopt=fail failmsgs="No such person"` |
| Pipe to a script | `… fwdopt=pipe pipefwd=path/script.php` (requires the *File Storage* role) |
| Other `fwdopt` values | `blackhole` (discard), `system` + `fwdsystem=<user>` |
| List / delete | `Email::list_forwarders domain=example.com` / `Email::delete_forwarder` |
| Autoresponder | `Email::add_auto_responder email=info domain=example.com from="Info" subject="Out of office" body="…" is_html=0 interval=24 start=<unix> stop=<unix>` |

## 3. Email Deliverability (SPF, DKIM, DMARC)

1. Inspect: `EmailAuth::validate_current_spfs domain=example.com`, `EmailAuth::validate_current_dkims domain=example.com`, `EmailAuth::validate_current_dmarcs domain=example.com`, `EmailAuth::validate_current_ptrs`.
2. DKIM: `EmailAuth::ensure_dkim_keys_exist domain=example.com`, then `EmailAuth::enable_dkim domain=example.com`.
3. SPF: `EmailAuth::install_spf_records domain=example.com record="v=spf1 +a +mx +ip4:203.0.113.10 -all"`. URI-encode `+` as `%2B` on the query string; for several domains, repeat each `domain`/`record` pair.
4. DMARC: `EmailAuth::apply_dmarc domain=example.com policy="v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com"`.
5. Verify: re-run step 1.

These functions write DNS records. They work only when the zone is hosted on the cPanel server (DNS role enabled). Otherwise, give the user the record values to publish at their DNS provider.

## 4. MySQL Database, User and Privileges

```bash
uapi_http Mysql get_restrictions            # → data.prefix (e.g. "myuser_"), max name lengths
uapi_http Mysql create_database name=myuser_app
uapi_http Mysql create_user name=myuser_app "password=$DB_PW"
uapi_http Mysql set_privileges_on_database user=myuser_app database=myuser_app "privileges=ALL PRIVILEGES"
uapi_http Mysql list_databases              # verify (also: Mysql::get_privileges_on_database)
```

- With DB prefixing enabled, **every** database and user name must carry the prefix.
- `privileges` replaces the existing list; it does not add to it. Pass a comma-separated subset (`SELECT,INSERT,UPDATE,DELETE`) for least privilege.
- One-shot alternative: `Mysql::setup_db_and_user [prefix=…]` creates a randomly named DB and user pair.
- Remote access: `Mysql::add_host host=203.0.113.0/24` (+ `Mysql::add_host_note`).
- Atomic-ish chain: wrap the three calls in `Batch::strict` (stops at the first failure, no rollback). See [calling-conventions.md](calling-conventions.md#batch-calls).
- PostgreSQL has the same shape under `Postgresql::*` (`create_database`, `create_user`, `grant_all_privileges`).

## 5. Domains

| Goal | Call |
|---|---|
| List everything | `DomainInfo::list_domains` (names) / `DomainInfo::domains_data` (docroots, types) / `DomainInfo::single_domain_data domain=…` |
| Subdomain | `SubDomain::addsubdomain domain=blog rootdomain=example.com dir=public_html/blog` |
| Addon domain | `AddonDomain::addaddondomain newdomain=other.com subdomain=other dir=public_html/other.com` |
| Alias (parked) | `Park::park domain=alias.com` |
| Remove | `SubDomain::delsubdomain`, `AddonDomain::deladdondomain`, `Park::unpark` |

- Disabling the *Web Server* role disables these functions.
- The target domain's DNS must point at the server for it to serve traffic. Check with `DNS::parse_zone`, or use the external lookups in `DomainLookup`.

## 6. DNS Zone Editing

```bash
uapi_http DNS parse_zone zone=example.com
#   → data[]: {line_index, type: record|control|comment, record_type, ttl, dname_b64, data_b64[]}
#   → the SOA record's data contains the current serial
uapi_http DNS mass_edit_zone zone=example.com serial=2026100101 \
  'add={"dname":"www","ttl":300,"record_type":"A","data":["203.0.113.10"]}' \
  'add={"dname":"@","ttl":300,"record_type":"TXT","data":["google-site-verification=…"]}' \
  remove=23
#   → data.new_serial
```

- `parse_zone` returns names and values **base64-encoded**. Decode them, and be prepared for byte sequences that are not valid UTF-8.
- `serial` must equal the zone's current SOA serial; a mismatch fails the call. Retry: re-parse, take the new serial, apply again.
- `edit` items need `line_index` (0-based) plus the full new record; `remove` takes line indexes. Indexes come from the **same** `parse_zone` read.
- Temporary domains cannot be edited. Reset a zone with `ZoneEdit::resetzone` (destructive; ask first).
- DNSSEC: `DNSSEC::*`. Dynamic DNS: `DynamicDNS::*`.

## 7. SSL / TLS

### AutoSSL (preferred)

```bash
uapi_http SSL start_autossl_check
uapi_http SSL is_autossl_check_in_progress   # poll
uapi_http SSL get_autossl_problems           # per-domain failures (usually DNS/DCV)
uapi_http SSL installed_hosts                # verify
```

### Custom certificate

| Step | Call |
|---|---|
| Key | `SSL::generate_key keytype=rsa-2048 friendly_name=example` → key id |
| CSR | `SSL::generate_csr key_id=… domains=example.com,www.example.com countryName=BR stateOrProvinceName=SP localityName="Sao Paulo" organizationName="Example Ltd"` |
| Install | `SSL::install_ssl domain=example.com cert=<PEM> key=<PEM> cabundle=<PEM>` (POST: PEMs are long and the key is a secret) |
| Inspect | `SSL::list_certs`, `SSL::fetch_best_for_domain domain=…`, `SSL::installed_hosts` |
| Remove | `SSL::delete_ssl domain=…` |

DCV pre-checks: `DCV::check_domains_via_http`, `DCV::check_domains_via_dns`.

## 8. Redirects

```bash
uapi_http Mime add_redirect domain=example.com src=/old redirect=https://example.com/new type=permanent redirect_www=0
uapi_http Mime list_redirects               # verify; remove with Mime::delete_redirect
```

`redirect_www`: `0` = with and without www, `1` = only without, `2` = only with.

## 9. PHP Version per Site (EasyApache 4)

```bash
uapi_http LangPHP php_get_installed_versions        # → ea-php81, ea-php82, …
uapi_http LangPHP php_get_vhost_versions            # current version per vhost
uapi_http LangPHP php_set_vhost_versions vhost=example.com version=ea-php82
```

php.ini directives: `LangPHP::php_ini_get_user_content` / `php_ini_set_user_content`, or the `LangPHP::php_ini_*_directives` functions.

## 10. Git Deployment

1. Create or clone: `VersionControl::create type=git name=site repository_root=/home/myuser/repositories/site source_repository='{"remote_name":"origin","url":"https://github.com/org/site.git"}'`
2. Commit a `.cpanel.yml` at the repo root:

   ```yaml
   ---
   deployment:
     tasks:
       - export DEPLOYPATH=/home/myuser/public_html/
       - /bin/cp -R public/* $DEPLOYPATH
   ```

3. Pull: `VersionControl::update repository_root=… branch=main` (fast-forward only).
4. Deploy: `VersionControlDeployment::create repository_root=…` → `deploy_id`, `task_id`, `log_path`, `sse_url`.
5. Verify: `VersionControlDeployment::retrieve`, or read the log at `~/.cpanel/logs/vc_<ts>_git_deploy.log`.

Deployment requires a checked-in `.cpanel.yml`, at least one branch, and a **clean** working tree. Otherwise the deploy functions are disabled for that repository.

## 11. Files

| Goal | Call |
|---|---|
| List | `Fileman::list_files dir=public_html include_permissions=1` |
| Read | `Fileman::get_file_content dir=public_html file=.htaccess` |
| Write | `Fileman::save_file_content dir=public_html file=.htaccess content=…` (POST) |
| Upload | `Fileman::upload_files dir=public_html overwrite=1` — **POST `multipart/form-data`**, parts `file-0`, `file-1`…; not available on the CLI, in LiveAPI or through `uapi_cpanel` |
| Empty the trash | `Trash::remove` (plugin), `Trash::usage` |

```bash
curl -sS -H "Authorization: cpanel $CPANEL_USER:$CPANEL_TOKEN" \
  -F "dir=public_html" -F "overwrite=1" -F "file-0=@dist/index.html" \
  "https://$CPANEL_HOST:2083/execute/Fileman/upload_files"
```

Uploaded files are virus-scanned; infected files are rejected and counted in `data.failed`.

## 12. FTP Accounts

`Ftp::add_ftp user=deploy domain=example.com pass=… homedir=public_html quota=0` · list `Ftp::list_ftp_with_disk` · password `Ftp::passwd` · delete `Ftp::delete_ftp` · sessions `Ftp::list_sessions` / `Ftp::kill_session`.

## 13. Backups

| Goal | Call |
|---|---|
| Full account backup to the home directory | `Backup::fullbackup_to_homedir [email=notify@example.com]` |
| Off-site (SCP with key) | `Backup::fullbackup_to_scp_with_key host=… key_name=… key_passphrase=… directory=…` (also `_to_ftp`, `_to_scp_with_password`) |
| List | `Backup::list_backups` |
| Restore files / DBs / email | `Restore::*` (query first with `Restore::query_file_info`) |
| Website snapshots (plugin `WebsiteBackup`, cPanel 138+) | `WebsiteBackup::create_backup` → `list_operations` / `operation_status operationId=…` → `restore_backup` |
| WordPress | `WordPressBackup::*`, `WordPressRestore::*` |

Backups run asynchronously. Report "started", poll the status, and report "done" only when the status says so.

## 14. Monitoring and Usage

| Metric | Call |
|---|---|
| Disk quota | `Quota::get_quota_info` |
| All limits (disk, inodes, DBs, mailboxes…) | `ResourceUsage::get_usages` |
| Sidebar stats | `StatsBar::get_stats display=diskusage\|bandwidthusage\|…` |
| Bandwidth | `Bandwidth::query grouping=domain\|year_month start=<unix> end=<unix>` |
| Mailbox sizes | `Email::list_pops_with_disk api.sort=1 api.sort_column=diskused api.sort_method=numeric api.sort_reverse=1` |
| Error log / logins | `Stats::get_site_errors`, `LastLogin::get_last_or_current_logged_in_ip` |

## 15. Security Operations

| Goal | Call |
|---|---|
| Block an IP / range | `BlockIP::add_ip ip=198.51.100.7` (remove: `BlockIP::remove_ip`) |
| ModSecurity per domain | `ModSecurity::list_domains`, `ModSecurity::enable_domains` / `disable_domains` |
| Password-protect a directory | `DirectoryPrivacy::configure_directory_protection` + `DirectoryProtection::*` |
| Active sessions | `ActiveSessions::list_active_sessions` |
| Rotate API tokens | `Tokens::create_full_access` (new) → switch the integration → `Tokens::revoke name=<old>` |
| SSH | `SSH::get_port`, `KnownHosts::*` |
