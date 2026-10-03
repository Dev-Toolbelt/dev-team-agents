"""Account-level integrations with external REST APIs (GitHub, Jira, Cloudflare).

An integration is not a plugin. A plugin is per-project with committed settings; an
integration has a secret token (account-level, through `creds`, so ADR-0010's keychain
and audit trail apply), non-secret account config in the portable store, and an optional
per-project binding that is committed and shared like `plugin-settings/`.

| What | Where |
|---|---|
| token | secret store, `creds` key ``integration.<name>.token`` (global layer) |
| account config | ``data/integrations/<name>.json`` (portable) |
| project binding | ``<project>/.dev-team-agents/integration-settings/<name>.json`` (committed) |
| last test result | ``data/machines/<id>/integrations-status.json`` (machine-local) |

All network I/O goes through :mod:`.http`. The token never appears in a payload, an
exception message or a log line: the only functions that hold it are the adapters' own
``test``/``resources`` calls, which build the Authorization header and nothing else.

The token is bound to the origin it was stored for (``token_origin`` in the account
config). Change ``api_url``/``site_url`` and the token is *stale*: it is sent nowhere until
the user reconnects with a new token. The keychain value is kept (No-Destruction).

Storing a new token is three steps under the integrations lock: drop ``token_origin`` from
the account file, write the token, then write the new origin and a fresh
``token_generation``. A failure between any two leaves the token stale, never bound to the
previous host. A reader that uses the token without the lock (``test``, ``resources``)
re-reads the account file after reading the token and refuses when it changed: whatever
it read may belong to a connect that was in flight. The keychain read itself stays outside
the lock, because an OS prompt there must not block every other command.

Lock order: the integrations lock is the outer one. ``connect`` and ``disconnect`` take it
and then the ``credentials`` lock inside ``creds``; nothing in ``creds`` takes the
integrations lock, so the order cannot invert. No lock is held across a network call.

Agents reach an API through :func:`call` (ADR-0031), and only on an adapter that sets
``callable = True``: the CLI resolves the endpoint, reads the token and makes the request,
so the token never reaches the agent's context. Reads run freely; a write method needs
``allow_write``, which an agent passes only after the user confirmed that write.

Schemas: ``SCHEMA`` versions the account file and ``SETTINGS_SCHEMA`` the committed project
binding — separate numbers, because a client must declare each before writing it and the
two can change independently. The machine-local status file is a cache the CLI alone
writes; it carries its own ``STATUS_SCHEMA`` and is not part of the client declaration.
"""

from __future__ import annotations

import datetime
import re
import urllib.parse
import uuid
from pathlib import Path

from .. import creds, jsonio, paths, project, quarantine
from ..errors import EnvError, UsageError
from ..lock import store_lock
from . import http
from .base import check_token, is_blank
from .cloudflare import Cloudflare
from .github import GitHub
from .jira import Jira

SCHEMA = 1
SETTINGS_SCHEMA = 1
STATUS_SCHEMA = 1
#: Reserved, non-field key in the account config: the normalised origin the stored token
#: was issued for. The token is only ever sent to that origin.
TOKEN_ORIGIN = "token_origin"
#: Reserved, non-field key: changes on every token write, so a test result for a replaced
#: token is recognised as stale even when the origin is unchanged.
TOKEN_GENERATION = "token_generation"
RESERVED_KEYS = (TOKEN_ORIGIN, TOKEN_GENERATION)
SETTINGS_DIR = "integration-settings"
STATUS_FILE = "integrations-status.json"
LOCK = "integrations"
STATES = ("not_connected", "connected", "invalid_token", "rate_limited", "unreachable", "unknown")

_ADAPTERS = {adapter.name: adapter for adapter in (Cloudflare(), GitHub(), Jira())}
CALL_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")
# An absolute API path: RFC 3986 path characters plus `{field}` placeholders. No query,
# fragment, backslash or whitespace can get through; percent-escapes are checked apart.
_ENDPOINT_RE = re.compile(r"^/[A-Za-z0-9._~%!$&'()*+,;=:@/{}-]+$")
_PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")
_ESCAPE_RE = re.compile(r"%([0-9A-Fa-f]{2})")
# What a percent-escape may never stand for: a separator, a dot, a second escape
# (`%252e` decodes to `%2e`), or a control character.
_FORBIDDEN_ESCAPES = frozenset(b"/\\.%") | frozenset(range(0x20)) | {0x7F}


def names():
    return sorted(_ADAPTERS)


def get_adapter(name):
    adapter = _ADAPTERS.get(name)
    if adapter is None:
        raise UsageError(
            "unknown integration {!r}".format(name), hint="Available: {}".format(", ".join(names()))
        )
    return adapter


def token_key(name):
    return "integration.{}.token".format(name)


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── storage ───────────────────────────────────────────────────────────────────


def account_path(name):
    return paths.data_dir() / "integrations" / "{}.json".format(name)


def project_path(project_root, name):
    return Path(project_root) / project.PROJECT_DIR / SETTINGS_DIR / "{}.json".format(name)


def status_path():
    return paths.machine_dir() / STATUS_FILE


def _read_config(path, max_schema=SCHEMA):
    data = jsonio.read_json(path)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise EnvError("{} must hold a JSON object".format(path), hint="Fix the file by hand.")
    schema = data.get("schema", max_schema)
    if not isinstance(schema, int) or isinstance(schema, bool) or schema < 1:
        raise EnvError("{}: 'schema' must be a positive integer".format(path))
    if schema > max_schema:
        raise EnvError(
            "{}: schema {} is newer than this CLI understands (max {})".format(
                path, schema, max_schema
            )
        )
    config = data.get("config", {})
    if not isinstance(config, dict):
        raise EnvError("{}: 'config' must be an object".format(path), hint="Fix the file by hand.")
    return config


def _read_account_raw(name):
    """The account file's config including the reserved ``token_origin`` key."""
    return _read_config(account_path(name))


def read_account(name):
    return {k: v for k, v in _read_account_raw(name).items() if k not in RESERVED_KEYS}


def read_project(project_root, name):
    return _read_config(project_path(project_root, name), SETTINGS_SCHEMA)


def _write_account(name, config):
    """Caller holds the integrations lock."""
    jsonio.write_json_atomic(account_path(name), {"schema": SCHEMA, "config": config})


def _checked_project_path(project_root, name):
    """The binding file path, or ``UsageError`` when it could land outside the project."""
    root = Path(project_root)
    target = project_path(root, name)
    for candidate in (root / project.PROJECT_DIR, target.parent, target):
        if candidate.is_symlink():
            raise UsageError(
                "{} is a symbolic link".format(candidate),
                hint="Integration bindings are only written to real files inside the project.",
            )
    try:
        target.parent.resolve().relative_to(root.resolve())
    except ValueError:
        raise UsageError(
            "{} resolves outside the project".format(target.parent),
            hint="Integration bindings are only written to real files inside the project.",
        ) from None
    return target


def _write_project(project_root, name, config):
    """Caller holds the integrations lock."""
    target = _checked_project_path(project_root, name)
    jsonio.write_json_atomic(
        target,
        {"schema": SETTINGS_SCHEMA, "config": config},
        mode=jsonio.PROJECT_FILE_MODE,
        dir_mode=None,
    )


def _load_status():
    """``(status, usable)``. A missing file is usable and empty; a malformed or newer one
    is unusable and reads as empty: an unreadable cache must never break ``list``/``show``."""
    if paths.machine_id(create=False) is None:
        return {}, True
    try:
        data = jsonio.read_json(status_path())
    except EnvError:
        return {}, False
    if data is None:
        return {}, True
    if not isinstance(data, dict) or not isinstance(data.get("status", {}), dict):
        return {}, False
    schema = data.get("schema", STATUS_SCHEMA)
    if not isinstance(schema, int) or isinstance(schema, bool) or schema < 1 or schema > STATUS_SCHEMA:
        return {}, False
    return data.get("status", {}), True


def _read_status_file():
    return _load_status()[0]


def read_status(name):
    record = _read_status_file().get(name)
    return record if isinstance(record, dict) else None


def _update_status_locked(name, record):
    """Set (or, with ``None``, drop) one record. True when it changed. Caller holds the lock.

    A status file this CLI cannot read is moved to quarantine first, never overwritten.
    """
    status, usable = _load_status()
    if not usable:
        try:
            quarantine.move(status_path(), None, group="integrations-status")
        except OSError as exc:
            raise EnvError("cannot set aside the unreadable {}: {}".format(status_path(), exc)) from None
    status = dict(status)
    if status.get(name) == record or (record is None and name not in status):
        return False
    if record is None:
        del status[name]
    else:
        status[name] = record
    jsonio.write_json_atomic(status_path(), {"schema": STATUS_SCHEMA, "status": status})
    return True


# ── config semantics ──────────────────────────────────────────────────────────


def _fields(adapter, scope):
    return [f for f in adapter.fields if f["scope"] == scope]


def _field(adapter, key):
    for candidate in adapter.fields:
        if candidate["key"] == key:
            return candidate
    raise UsageError(
        "{} has no field {!r}".format(adapter.name, key),
        hint="Fields: {}".format(", ".join(f["key"] for f in adapter.fields)),
    )


def effective_account(adapter, stored=None):
    """Declared account fields: stored value, else the default, blanks dropped."""
    stored = _read_account_raw(adapter.name) if stored is None else stored
    out = {}
    for f in _fields(adapter, "account"):
        value = stored.get(f["key"], f["default"])
        if not is_blank(value):
            out[f["key"]] = value
    return out


def valid_project_values(adapter, raw):
    """Declared project fields that still pass the adapter's validation, normalised.

    The binding file is committed and hand-editable, so a value is re-checked on every read
    and an invalid one is treated as unset.
    """
    out = {}
    for f in _fields(adapter, "project"):
        value = raw.get(f["key"])
        if not isinstance(value, str) or is_blank(value):
            continue
        try:
            out[f["key"]] = adapter.normalize(f["key"], value)
        except UsageError:
            continue
    return out


def _visible(f, account):
    rule = f["visible_when"]
    return rule is None or account.get(rule["key"]) == rule["equals"]


def missing_fields(adapter, account):
    return [
        f["key"]
        for f in _fields(adapter, "account")
        if f["required"] and _visible(f, account) and is_blank(account.get(f["key"]))
    ]


def token_reference(name):
    entry, _layer = creds.resolve(token_key(name), None)
    return entry


def link_config(project_root, name):
    """``{"account", "project"}`` for a connected integration, else ``None``; the token is never read.

    The non-secret facts a link builder needs (the site or API URL, the project's key or
    repository). "Connected" is the same test the settings view uses: a token reference exists, it
    was issued for the configured origin, and no required account field is blank. No network, no
    keychain value, no audit line: only references and config files are read.
    """
    adapter = get_adapter(name)
    try:
        raw = _read_account_raw(name)
        account = effective_account(adapter, raw)
        if token_reference(name) is None or is_stale(adapter, raw, account) or missing_fields(adapter, account):
            return None
        project = valid_project_values(adapter, read_project(project_root, name))
    except (EnvError, UsageError, OSError):
        return None
    return {"account": account, "project": project}


class TokenMissing(Exception):
    """The reference exists but this machine holds no value for it (ADR-0010: references
    are portable, values are not)."""


def read_token(name):
    """The token, through `creds.get_value` so ADR-0010's audit line is written.

    Raises :class:`TokenMissing` when only the reference reached this machine.
    """
    try:
        return creds.get_value(token_key(name), None, agent=None)
    except EnvError:
        # `get_value` raises EnvError for a missing value; the reference was checked by
        # the caller, so that is the case here. Its message names no secret.
        raise TokenMissing() from None


class TokenNotOnMachine(UsageError):
    """`UsageError` for a reference whose value is not on this machine."""


def _missing_message(adapter):
    return "The {} token is not stored on this machine; reconnect with the token".format(
        adapter.title
    )


def _origin_string(url):
    """``scheme://host:port`` (lower-cased, default port made explicit), or ``None``."""
    if not isinstance(url, str):
        return None
    try:
        scheme, host, port = http.origin(url)
    except ValueError:
        return None
    if not host or port is None:
        return None
    return "{}://{}:{}".format(scheme, host, port)


def current_origin(adapter, account):
    return _origin_string(account.get(adapter.origin_key))


def is_stale(adapter, raw_account, account):
    """True when a token is stored but was not stored for the origin configured now."""
    if token_reference(adapter.name) is None:
        return False
    stored = raw_account.get(TOKEN_ORIGIN)
    return stored is None or stored != current_origin(adapter, account)


def _stale_message(adapter):
    return "The {} changed since the token was stored; reconnect with a new token".format(
        adapter.origin_key
    )


def _changed_while_reading(adapter):
    return UsageError(
        "{} was reconfigured while its token was being read".format(adapter.name),
        hint="Run the command again.",
    )


def _require_ready(adapter):
    """``(account, token, snapshot)`` or ``UsageError`` naming what is missing.

    ``snapshot`` is the raw account config the token is about to be used with, so a caller
    can tell afterwards whether it changed while the request was in flight. The account
    file is read again after the token: if a connect ran in between, the token may belong
    to a different origin than ``account`` says, so nothing is sent.
    """
    raw = _read_account_raw(adapter.name)
    account = effective_account(adapter, raw)
    missing = missing_fields(adapter, account)
    if missing:
        raise UsageError(
            "{} is missing: {}".format(adapter.name, ", ".join(missing)),
            hint="Run `devteam integration connect {}`.".format(adapter.name),
        )
    if token_reference(adapter.name) is None:
        raise UsageError(
            "{} has no token".format(adapter.name),
            hint="Run `devteam integration connect {}` and pipe the token in.".format(adapter.name),
        )
    if is_stale(adapter, raw, account):
        raise UsageError(
            _stale_message(adapter),
            hint="Run `devteam integration connect {}` and pipe the new token in.".format(adapter.name),
        )
    try:
        token = read_token(adapter.name)
    except TokenMissing:
        raise TokenNotOnMachine(
            _missing_message(adapter),
            hint="Run `devteam integration connect {}` and pipe the token in.".format(adapter.name),
        ) from None
    if _read_account_raw(adapter.name) != raw:
        raise _changed_while_reading(adapter)
    return account, token, raw


# ── view ──────────────────────────────────────────────────────────────────────


def build_view(adapter, project_root=None, project_id=None):
    name = adapter.name
    raw = _read_account_raw(name)
    account = effective_account(adapter, raw)
    entry = token_reference(name)
    has_token = entry is not None
    stale = has_token and is_stale(adapter, raw, account)
    connected = has_token and not stale and not missing_fields(adapter, account)

    bound = project_root is not None and project_id is not None
    project_values = None
    project_problem = None
    detected = {}
    if bound:
        try:
            raw_project = read_project(project_root, name)
        except EnvError as exc:
            # The binding is committed and hand-editable: one bad file must not take the
            # whole list down with it. It reads as unset, and the problem is reported.
            raw_project, project_problem = {}, str(exc)
        project_values = valid_project_values(adapter, raw_project)
        # Detection shells out; only worth it while there is a project field left to fill.
        unfilled = [f for f in _fields(adapter, "project") if f["key"] not in project_values]
        if account and unfilled:
            detected = {k: v for k, v in adapter.detect(project_root, account).items()
                        if k not in project_values}

    record = read_status(name) if connected else None
    if stale:
        status = {
            "state": "not_connected",
            "checked_at": None,
            "summary": "{}.".format(_stale_message(adapter)),
            "facts": [],
        }
    elif not connected:
        status = {"state": "not_connected", "checked_at": None, "summary": "Not connected", "facts": []}
    elif record and record.get("state") in STATES:
        status = {
            "state": record["state"],
            "checked_at": record.get("checked_at"),
            "summary": record.get("summary", ""),
            "facts": record.get("facts") or [],
        }
    else:
        status = {"state": "unknown", "checked_at": None, "summary": "Not tested yet", "facts": []}

    return {
        "name": name,
        "title": adapter.title,
        "description": adapter.description,
        "homepage": adapter.homepage,
        "auth": dict(
            adapter.auth, has_token=has_token, stale=stale, backend=entry.get("source") if entry else None
        ),
        "fields": [dict(f, binds_token=f["key"] == adapter.origin_key) for f in adapter.fields],
        "account": account,
        "project": project_values,
        "project_problem": project_problem,
        "detected": detected,
        "connected": connected,
        "project_configured": bool(project_values),
        "status": status,
    }


def list_views(project_root=None, project_id=None):
    return [build_view(_ADAPTERS[n], project_root, project_id) for n in names()]


# ── operations ────────────────────────────────────────────────────────────────


def run_test(adapter, account, token):
    """One live check, as a TestResult. A failing API is a result, not an error."""
    try:
        result = adapter.test(account, token)
    except http.FetchError as exc:
        result = {"ok": False, "state": exc.state, "summary": exc.summary, "facts": []}
    result["checked_at"] = _now()
    return result


def _persist_if_unchanged(name, snapshot, result):
    """Record ``result`` only when the account config is still what was tested."""
    with store_lock(LOCK):
        if _read_account_raw(name) != snapshot:
            return False
        _update_status_locked(
            name, {k: result[k] for k in ("state", "checked_at", "summary", "facts")}
        )
    return True


def _not_connected(summary):
    return {"ok": False, "state": "not_connected", "summary": summary, "facts": [], "checked_at": _now()}


def test(name):
    adapter = get_adapter(name)
    try:
        account, token, snapshot = _require_ready(adapter)
    except TokenNotOnMachine:
        # A result, not an error: the account is configured, this machine just lacks the
        # value. The card says so instead of showing a raw problem.
        return _not_connected("{}.".format(_missing_message(adapter)))
    result = run_test(adapter, account, token)
    _persist_if_unchanged(name, snapshot, result)
    return result


def parse_field_args(adapter, pairs):
    out = {}
    for pair in pairs or []:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            raise UsageError("--field expects key=value, got {!r}".format(key or pair))
        declared = _field(adapter, key)
        if declared["scope"] != "account":
            raise UsageError(
                "{} is a project field".format(key),
                hint="Set it with `devteam integration config set {} {} <value>`.".format(
                    adapter.name, key
                ),
            )
        out[key] = adapter.normalize(key, value)
    return out


def check_connect_fields(name, field_values):
    """``UsageError`` when required account fields would still be missing — checked
    before the CLI prompts for a token, so nobody types a secret into a doomed command."""
    adapter = get_adapter(name)
    merged = dict(_read_account_raw(name))
    merged.update(field_values)
    missing = missing_fields(adapter, effective_account(adapter, merged))
    if missing:
        raise UsageError(
            "{} needs: {}".format(name, ", ".join(missing)),
            hint="Pass them with --field key=value.",
        )


def connect(name, field_values, token):
    """Write account config and token, then test. ``token=None`` keeps the stored one.

    Returns ``(TestResult, backend)``; ``backend`` is where a *new* token went, else ``None``.
    Keeping the stored token while the origin changed (or was never recorded) sends nothing:
    the result is a ``not_connected`` TestResult saying a new token is needed.
    """
    adapter = get_adapter(name)
    backend = None
    with store_lock(LOCK):
        if token is None and token_reference(name) is None:
            raise UsageError(
                "no token was given for {}".format(name),
                hint="Pipe it in: printf %s \"$TOKEN\" | devteam integration connect {}".format(name),
            )
        raw = _read_account_raw(name)
        merged = dict(raw)
        merged.update(field_values)
        account = effective_account(adapter, merged)
        missing = missing_fields(adapter, account)
        if missing:
            raise UsageError(
                "{} needs: {}".format(name, ", ".join(missing)),
                hint="Pass them with --field key=value.",
            )
        if token is not None:
            origin = current_origin(adapter, account)
            if origin is None:
                raise UsageError("{} is not a valid URL".format(adapter.origin_key))
            try:
                check_token(token)
            except http.FetchError as exc:
                # Refused before it reaches the secret store: it could never be sent.
                raise UsageError(exc.summary, hint="Paste the token without spaces or line breaks.") from None
            # Unbind first: should the token write or the final config write fail, the
            # file names no origin and the token reads as stale, never as bound to the
            # previous host.
            unbound = {k: v for k, v in raw.items() if k not in RESERVED_KEYS}
            if unbound != raw:
                _write_account(name, unbound)
            entry = creds.set_entry(
                token_key(name),
                "{} API access for `devteam integration`".format(adapter.title),
                project_id=None,
                value=token,
            )
            backend = entry.get("source")
            merged[TOKEN_ORIGIN] = origin
            merged[TOKEN_GENERATION] = uuid.uuid4().hex
            raw = unbound
        if merged != raw:
            _write_account(name, merged)
        stale = token is None and is_stale(adapter, merged, account)
    if stale:
        return _not_connected("{}.".format(_stale_message(adapter))), backend
    if token is None:
        try:
            token = read_token(name)
        except TokenMissing:
            return _not_connected("{}.".format(_missing_message(adapter))), backend
        if _read_account_raw(name) != merged:
            raise _changed_while_reading(adapter)
    result = run_test(adapter, account, token)
    _persist_if_unchanged(name, merged, result)
    return result, backend


def disconnect(name, keep_token=False):
    adapter = get_adapter(name)
    changed = False
    with store_lock(LOCK):
        if not keep_token:
            changed = creds.unset(token_key(name), None, forget_value=True)["removed"]
        changed = _update_status_locked(name, None) or changed
    return adapter, changed


def _normalized(adapter, key, value):
    declared = _field(adapter, key)
    if is_blank(value):
        raise UsageError(
            "{} must not be empty".format(key),
            hint="Use `devteam integration config unset {} {}` to clear it.".format(adapter.name, key),
        )
    return declared, adapter.normalize(key, value)


def config_get(name, key, project_root=None, project_id=None):
    adapter = get_adapter(name)
    account = effective_account(adapter)
    bound = project_root is not None and project_id is not None
    project_values = None
    if bound:
        project_values = valid_project_values(adapter, read_project(project_root, name))
    if key is None:
        return {"integration": name, "account": account, "project": project_values}
    declared = _field(adapter, key)
    scope = declared["scope"]
    if scope == "account":
        value = account.get(key)
    else:
        value = (project_values or {}).get(key)
    return {"key": key, "value": value, "scope": scope}


def _require_project(adapter, key, project_root, project_id):
    if project_root is None or project_id is None:
        raise UsageError(
            "{} is a project field and this directory is not a bound project".format(key),
            hint="Run `devteam bind` first, or pass --path to a bound project.",
        )


def config_set(name, key, value, project_root=None, project_id=None):
    adapter = get_adapter(name)
    declared, normalized = _normalized(adapter, key, value)
    if declared["scope"] != "account":
        _require_project(adapter, key, project_root, project_id)
    with store_lock(LOCK):
        if declared["scope"] == "account":
            stored = dict(_read_account_raw(name))
            stored[key] = normalized
            _write_account(name, stored)
            _update_status_locked(name, None)
        else:
            stored = dict(read_project(project_root, name))
            stored[key] = normalized
            _write_project(project_root, name, stored)
    return adapter


def config_unset(name, key, project_root=None, project_id=None):
    adapter = get_adapter(name)
    declared = _field(adapter, key)
    if declared["scope"] != "account":
        _require_project(adapter, key, project_root, project_id)
    with store_lock(LOCK):
        if declared["scope"] == "account":
            stored = dict(_read_account_raw(name))
            removed = stored.pop(key, None) is not None
            if removed:
                _write_account(name, stored)
                _update_status_locked(name, None)
        else:
            stored = dict(read_project(project_root, name))
            removed = stored.pop(key, None) is not None
            if removed:
                _write_project(project_root, name, stored)
    return adapter, removed


def resources(name, kind):
    adapter = get_adapter(name)
    account, token, _snapshot = _require_ready(adapter)
    try:
        return adapter.resources(kind, account, token)
    except http.FetchError as exc:
        raise EnvError(
            "cannot list {} for {}: {}".format(kind, name, exc.summary),
            hint="Run `devteam integration test {}` to check the connection.".format(name),
        ) from None


# ── call ──────────────────────────────────────────────────────────────────────


def callable_names():
    return [n for n in names() if getattr(_ADAPTERS[n], "supports_call", False)]


def _call_adapter(name):
    adapter = get_adapter(name)
    if not getattr(adapter, "supports_call", False):
        raise UsageError(
            "{} does not support `integration call`".format(name),
            hint="Integrations that do: {}".format(", ".join(callable_names()) or "none"),
        )
    return adapter


def _check_method(method, allow_write):
    method = (method or "").upper()
    if method not in CALL_METHODS:
        raise UsageError("method must be one of {}".format(", ".join(CALL_METHODS)))
    if method in WRITE_METHODS and not allow_write:
        raise UsageError(
            "{} changes data and needs --allow-write".format(method),
            hint="Confirm the change with the user first, then repeat the call with --allow-write.",
        )
    return method


def _check_path(path):
    """``UsageError`` unless every segment of ``path`` is a plain, non-dot name."""
    if not isinstance(path, str) or not _ENDPOINT_RE.match(path):
        raise UsageError(
            "endpoint must be an absolute API path such as /zones",
            hint="Pass query parameters with --query key=value, never in the endpoint.",
        )
    for escape in _ESCAPE_RE.findall(path):
        if int(escape, 16) in _FORBIDDEN_ESCAPES:
            raise UsageError(
                "endpoint must not percent-encode '/', '\\', '.', '%' or a control character"
            )
    if _ESCAPE_RE.sub("", path).count("%"):
        raise UsageError("endpoint has a malformed percent-escape")
    for segment in path.split("/")[1:]:
        if segment in ("", ".", ".."):
            raise UsageError("endpoint must not contain empty, '.' or '..' segments")


def check_endpoint(adapter, endpoint):
    """The endpoint's shape and placeholder names, checked before any token is read."""
    _check_path(endpoint)
    allowed = _placeholder_keys(adapter)
    for key in _PLACEHOLDER_RE.findall(endpoint):
        if key not in allowed:
            raise UsageError(
                "unknown placeholder {{{}}}".format(key),
                hint="Placeholders: {}".format(", ".join("{" + k + "}" for k in sorted(allowed))),
            )
    if "{" in _PLACEHOLDER_RE.sub("", endpoint) or "}" in _PLACEHOLDER_RE.sub("", endpoint):
        raise UsageError("endpoint has a malformed placeholder; use {field_name}")


def _placeholder_keys(adapter):
    return {f["key"] for f in adapter.fields if f["key"] != adapter.origin_key}


def _forbidden(adapter, path):
    """The reason ``path`` is never called, or ``None``. Matched on the decoded path, so
    an escape cannot dodge a pattern."""
    decoded = urllib.parse.unquote(path)
    for pattern, reason in getattr(adapter, "forbidden_endpoints", ()):
        if pattern.search(decoded):
            return reason
    return None


def resolve_endpoint(adapter, endpoint, values, project_bound=True):
    """The request path with ``{field}`` placeholders filled, or ``UsageError``.

    Only declared fields other than the origin can be placeholders. Each value is
    re-validated by the adapter (the account file is hand-editable) and percent-encoded,
    and the filled path is checked again, so a substitution cannot add a segment.
    """
    check_endpoint(adapter, endpoint)
    scopes = {f["key"]: f["scope"] for f in adapter.fields}

    def fill(match):
        key = match.group(1)
        value = values.get(key)
        if is_blank(value):
            if scopes[key] == "project" and not project_bound:
                raise UsageError(
                    "{{{}}} is a project field and this directory is not a bound project".format(key),
                    hint="Run the call from the project, or pass --path to it.",
                )
            raise UsageError(
                "{{{}}} is not set".format(key),
                hint="Run `devteam integration config set {} {} <value>`.".format(adapter.name, key),
            )
        try:
            value = adapter.normalize(key, str(value))
        except UsageError as exc:
            raise UsageError(
                "the configured {} is invalid: {}".format(key, exc.message),
                hint="Fix it with `devteam integration config set {} {} <value>`.".format(adapter.name, key),
            ) from None
        return urllib.parse.quote(value, safe="")

    path = _PLACEHOLDER_RE.sub(fill, endpoint)
    _check_path(path)
    reason = _forbidden(adapter, path)
    if reason:
        raise UsageError(
            "{} is never called through `integration call`: {}".format(path, reason),
            hint="Its response is a credential. Ask the user to do this in the dashboard.",
        )
    return path


def parse_query_args(pairs):
    out = []
    for pair in pairs or []:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            raise UsageError("--query expects key=value, got {!r}".format(pair))
        out.append((key, value))
    return out


def _audit_call(name, method, endpoint, allow_write, outcome, project_id, http_status=None):
    """One line per call in the global audit log: what was asked for and how it ended.

    Never the body, the query values or the response; the path alone says which resource.
    """
    detail = {"method": method, "endpoint": endpoint, "allow_write": bool(allow_write)}
    if project_id is not None:
        detail["project_id"] = project_id
    if http_status is not None:
        detail["http_status"] = http_status
    try:
        creds.audit(None, "integration-call", token_key(name), outcome=outcome, detail=detail)
    except OSError:
        # The trail is best effort, like every other audit line: a full disk must not
        # turn a finished request into a reported failure.
        pass


def _error_message(adapter, method, path, exc):
    message = "{} {} failed: {}".format(method, path, exc.summary)
    describe = getattr(adapter, "describe_error", None)
    detail = describe(exc.body) if describe and exc.body else None
    return "{} ({})".format(message, detail) if detail else message


def call(name, method, endpoint, query=None, body=None, allow_write=False,
         project_root=None, project_id=None):
    """One API request on the user's behalf; the token never leaves this function's callees.

    Returns ``{"integration", "method", "endpoint", "response"}``. An HTTP failure is an
    ``EnvError`` whose ``details`` carry the status and the API's own error body. Every
    call, refused or sent, leaves an ``integration-call`` audit line.
    """
    adapter = _call_adapter(name)
    raw_method = (method or "").upper()
    try:
        method = _check_method(method, allow_write)
        if body is not None and method == "GET":
            raise UsageError("a GET request takes no body")
        check_endpoint(adapter, endpoint)
    except UsageError:
        _audit_call(name, raw_method, endpoint, allow_write, "refused", project_id)
        raise
    bound = project_root is not None and project_id is not None
    # A binding that cannot be read is reported, not treated as unset: "{zone_id} is not
    # set" would send the user to `config set` for a file that is actually broken.
    project_values = valid_project_values(adapter, read_project(project_root, name)) if bound else {}
    account, token, _snapshot = _require_ready(adapter)
    values = dict(account)
    values.update(project_values)
    try:
        path = resolve_endpoint(adapter, endpoint, values, project_bound=bound)
    except UsageError:
        _audit_call(name, method, endpoint, allow_write, "refused", project_id)
        raise
    try:
        data, _headers = http.request_json(
            method, account[adapter.origin_key], path, adapter.headers(token),
            body=body, query=query or None,
        )
    except http.FetchError as exc:
        _audit_call(name, method, path, allow_write, "failed", project_id, exc.http_status)
        details = {"state": exc.state, "http_status": exc.http_status, "response": exc.body}
        if exc.retry_after is not None:
            details["retry_after"] = exc.retry_after
        if exc.reason == "not_json":
            hint = "This endpoint answers with raw content, not JSON; use the provider's own CLI for it."
        else:
            hint = "Run with --json to read the API's full answer in details.response."
        raise EnvError(_error_message(adapter, method, path, exc), hint=hint, details=details) from None
    _audit_call(name, method, path, allow_write, "ok", project_id)
    return {"integration": name, "method": method, "endpoint": path, "response": data}
