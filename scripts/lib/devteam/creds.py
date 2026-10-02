"""Credential **references** — non-secret, reviewable, diffable (ADR-0010).

This module holds the record of *which* credentials a project needs: purpose,
which backend holds the value, the opaque ``ref`` that names it there, and who
is expected to read it. It never holds a value itself — ``secrets.py`` does
that, keyed by ``ref`` — and every payload this module returns is built by
naming fields explicitly, never by copying an entry, so a value-shaped field
added to the schema later cannot leak through a code path that forgot to pop it.

Layered like preferences (ADR-0008): a project's own
``data/credentials/<project_id>.json`` overrides the shared
``data/credentials/global.json``. Both are portable (ADR-0013) — they hold no
value, only the fact that one exists and where.

The audit trail (``data/machines/<machine-id>/projects/<project_id>/audit.log``)
is machine-local and append-only JSONL: two machines appending to one portable
log would need merge semantics nothing here has, and a trail that silently
interleaves two hosts is worse than two separate ones.

**Stated limitation, not sold as a boundary:** the ``scope`` check below is
hygiene and auditability, exactly as ADR-0010 frames it — an agent with shell
access can read anything the user can read, scope or no scope. Presenting it as
a sandbox would be a lie a future reader could build on.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from . import jsonio, paths, quarantine
from . import secrets as secrets_module  # NB: 'secrets' also shadows the stdlib
# module of the same name. This relative import is scoped to the package and is
# fine here, but a future `import secrets` written elsewhere in this file would
# silently reach the stdlib one instead — hence the comment, not just the alias.
from .errors import EnvError, UsageError
from .lock import store_lock

SCHEMA = 1

#: Not secrets. ADR-0010 keeps them in this file's schema for back-compat and
#: they are read without touching a backend — carried over verbatim by
#: `import_file` rather than pushed through `secrets.put`.
NON_SECRET_KEYS = ("work_feedback_active", "work_feedback_interval_minutes")

#: A credential key reaches a backend ref (`devteam/<scope>/<key>`) and a CLI
#: argument. Letters/digits/`.`/`_`/`-` only, starting alphanumeric — the same
#: shape the ADR's own example (`posthog.api_key`) uses.
_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

#: The only fields a reference entry may carry. Anything else is rejected outright
#: — see `_check_entry_fields` — because the whole design rests on this file never
#: holding a value, and a field named just plausibly enough to look like metadata
#: is exactly how a hand-edit would smuggle one in.
_ALLOWED_ENTRY_FIELDS = {"purpose", "source", "ref", "scope"}

#: Field names that specifically look like they carry a secret, called out on their
#: own so the error can say what's wrong instead of just "unexpected field".
_VALUE_LOOKING_FIELDS = {
    "value",
    "secret",
    "secret_value",
    "password",
    "passwd",
    "pass",
    "token",
    "api_key",
    "apikey",
    "access_token",
    "credential",
    "cred",
}

#: Sentinel used only to pick an audit-log path when there is no project — a
#: project_id is always a UUID4, so this string can never collide with a real one.
_GLOBAL_AUDIT_SCOPE = "global"


# ── validation ──────────────────────────────────────────────────────────────


def _require_valid_key(key):
    if not isinstance(key, str) or not _KEY_RE.match(key):
        raise UsageError(
            "credential key {!r} must start with a letter or digit and contain only "
            "letters, digits, '.', '_' or '-'".format(key)
        )


def _check_entry_fields(key, entry, source):
    extra = set(entry) - _ALLOWED_ENTRY_FIELDS
    if not extra:
        return
    suspicious = {f for f in extra if f.lower() in _VALUE_LOOKING_FIELDS}
    if suspicious:
        raise EnvError(
            "{}: credential {!r} has a field that looks like it holds a value: {}".format(
                source, key, ", ".join(sorted(suspicious))
            ),
            hint=(
                "This file holds references only, never secret values (ADR-0010). "
                "Remove the field and store the actual value with `devteam cred set`."
            ),
        )
    raise EnvError(
        "{}: credential {!r} has unexpected field(s): {}".format(
            source, key, ", ".join(sorted(extra))
        )
    )


def _empty():
    return {"schema": SCHEMA, "credentials": {}}


def _validate(data, source):
    """Raise on anything a caller would otherwise have to defend against.

    Mirrors `project.py`'s and `registry.py`'s pattern: refuse a schema newer
    than this CLI understands rather than guessing at it, and never rewrite a
    malformed file — name it and tell the user to fix it by hand.
    """
    if not isinstance(data, dict):
        raise EnvError("{}: expected a JSON object".format(source))

    schema = data.get("schema", SCHEMA)
    if not isinstance(schema, int) or isinstance(schema, bool) or schema < 1:
        raise EnvError("{}: 'schema' must be a positive integer".format(source))
    if schema > SCHEMA:
        raise EnvError(
            "{}: schema {} is newer than this CLI understands (max {})".format(
                source, schema, SCHEMA
            ),
            hint="Update dev-team-agents — an older CLI must not rewrite a newer file.",
        )

    credentials = data.get("credentials", {})
    if not isinstance(credentials, dict):
        raise EnvError("{}: 'credentials' must be a JSON object".format(source))

    for key, entry in credentials.items():
        if not isinstance(key, str) or not _KEY_RE.match(key):
            raise EnvError("{}: {!r} is not a valid credential key".format(source, key))
        if not isinstance(entry, dict):
            raise EnvError("{}: credential {!r} must be a JSON object".format(source, key))
        _check_entry_fields(key, entry, source)

        purpose = entry.get("purpose")
        if not isinstance(purpose, str) or not purpose.strip():
            raise EnvError("{}: credential {!r} needs a non-empty 'purpose'".format(source, key))

        src = entry.get("source")
        # Structure is validated here; the **set** of known backends is not. A `source`
        # this build does not recognise is data, and it has an honest cause: a file
        # written by a newer CLI, or restored from a machine with a backend this one
        # lacks. Refusing it here made `devteam cred list` and `devteam doctor` fail
        # hard on a file they should have been able to describe — and it made
        # `check()`'s own `unknown-source` finding unreachable, which is how the dead
        # branch was noticed. `check()` reports it, and a read of it fails at use time
        # with the backend's own error.
        if not isinstance(src, str) or not src.strip():
            raise EnvError(
                "{}: credential {!r} needs a non-empty 'source'".format(source, key),
                hint="Known sources in this build: {}.".format(
                    ", ".join(secrets_module.BACKENDS)
                ),
            )

        ref = entry.get("ref")
        if not isinstance(ref, str) or not ref.strip():
            raise EnvError("{}: credential {!r} needs a non-empty 'ref'".format(source, key))

        scope = entry.get("scope", [])
        if not isinstance(scope, list) or not all(
            isinstance(item, str) and item.strip() for item in scope
        ):
            raise EnvError(
                "{}: credential {!r} 'scope' must be a list of non-empty strings".format(
                    source, key
                )
            )

    if "work_feedback_active" in data and not isinstance(data["work_feedback_active"], bool):
        raise EnvError("{}: 'work_feedback_active' must be a boolean".format(source))
    if "work_feedback_interval_minutes" in data:
        value = data["work_feedback_interval_minutes"]
        if isinstance(value, bool) or not isinstance(value, int):
            raise EnvError("{}: 'work_feedback_interval_minutes' must be an integer".format(source))

    return data


# ── layer I/O ────────────────────────────────────────────────────────────────


def load(project_id=None):
    """One layer, validated. ``project_id=None`` reads the shared global layer."""
    path = paths.credentials_file(project_id)
    data = jsonio.read_json(path, default=None)
    if data is None:
        return _empty()
    return _validate(data, source=str(path))


def _write(data, project_id):
    _validate(data, source=str(paths.credentials_file(project_id)))
    jsonio.write_json_atomic(paths.credentials_file(project_id), data)


def _ref_for(key, project_id):
    _require_valid_key(key)
    scope_id = project_id if project_id else "global"
    return "devteam/{}/{}".format(scope_id, key)


def _public_view(key, entry, layer):
    """Build the payload field-by-field — never by copying `entry` and popping
    keys — so a value-shaped field that slips past `_validate` (or a future
    field nobody thought to strip) cannot leak through this path by default.
    """
    return {
        "key": key,
        "purpose": entry.get("purpose"),
        "source": entry.get("source"),
        "ref": entry.get("ref"),
        "scope": list(entry.get("scope", [])),
        "layer": layer,
    }


# ── resolution ───────────────────────────────────────────────────────────────


def resolve(key, project_id):
    """The winning entry for ``key`` and which layer it came from.

    Project layer overrides global, same cascade direction as `prefs.py`.
    Returns ``(None, None)`` when neither layer has it — a missing credential
    is a normal question to ask, never an error by itself.
    """
    _require_valid_key(key)
    if project_id:
        entry = load(project_id).get("credentials", {}).get(key)
        if entry is not None:
            return dict(entry), "project"
    entry = load(None).get("credentials", {}).get(key)
    if entry is not None:
        return dict(entry), "global"
    return None, None


def list_entries(project_id):
    """Every reference visible to ``project_id``, project overriding global.

    References only, on every code path — see `_public_view`. Never a value.
    """
    merged = {}
    for key, entry in load(None).get("credentials", {}).items():
        merged[key] = _public_view(key, entry, "global")
    if project_id:
        for key, entry in load(project_id).get("credentials", {}).items():
            merged[key] = _public_view(key, entry, "project")
    return sorted(merged.values(), key=lambda item: item["key"])


# ── mutation ─────────────────────────────────────────────────────────────────


def set_entry(key, purpose, ref_scope=None, project_id=None, value=None, backend=None):
    """Register or update a reference in the layer ``project_id`` selects.

    When ``value`` is given, it is pushed into a backend first (`default_backend()`
    unless ``backend`` is given) and ``source`` records whichever backend actually
    took it. When ``value`` is omitted, the entry is written with no value change —
    useful for updating ``purpose``/``scope`` on an existing reference, or for
    pointing at a ref whose value was set out of band.
    """
    if not isinstance(purpose, str) or not purpose.strip():
        raise UsageError("credential purpose must be a non-empty string")
    scope = list(ref_scope) if ref_scope else []
    for item in scope:
        if not isinstance(item, str) or not item.strip():
            raise UsageError("credential scope entries must be non-empty strings")

    ref = _ref_for(key, project_id)
    with store_lock("credentials"):
        data = load(project_id)
        existing = data.get("credentials", {}).get(key)
        if value is not None:
            stored = secrets_module.put(ref, value, backend=backend)
            source = stored["backend"]
        elif backend is not None:
            source = backend
        elif existing is not None:
            source = existing.get("source")
        else:
            source = secrets_module.default_backend()

        entry = {"purpose": purpose, "source": source, "ref": ref, "scope": scope}
        data.setdefault("credentials", {})[key] = entry
        _write(data, project_id)

    return _public_view(key, entry, "project" if project_id else "global")


def get_value(key, project_id, agent=None):
    """Resolve -> scope check -> backend get -> audit. Returns the value.

    The scope check is **hygiene and auditability, not a sandbox** (ADR-0010):
    an agent running with Bash can read anything the user can read regardless of
    what ``scope`` says. When ``scope`` is non-empty and ``agent`` is given and
    not in it, the read is refused and audited. When ``agent`` is ``None`` the
    read is allowed — the audit line simply records a null agent, which is what
    "the caller was unidentified" looks like in the trail.

    A failed read is audited too: a scope refusal and a missing value are
    exactly what an audit trail exists to surface, not just successful reads.
    """
    entry, layer = resolve(key, project_id)
    if entry is None:
        audit(project_id, "get", key, agent=agent, outcome="not-registered")
        raise EnvError(
            "no credential registered for {!r}".format(key),
            hint="Run `devteam cred set {} ...` to register it.".format(key),
        )

    scope = entry.get("scope") or []
    if scope and agent is not None and agent not in scope:
        audit(project_id, "get", key, agent=agent, outcome="scope-refused", detail={"layer": layer})
        raise EnvError(
            "{!r} is not in the declared scope for credential {!r}".format(agent, key),
            hint=(
                "Scope is hygiene and auditability, not a sandbox (ADR-0010) — anything "
                "with shell access can read what the user can read. Add the agent to "
                "'scope' if it should be a recorded, intended reader."
            ),
        )

    value = secrets_module.get(entry["ref"], entry["source"])
    if value is None:
        audit(
            project_id, "get", key, agent=agent, outcome="value-missing", detail={"layer": layer}
        )
        raise EnvError(
            "credential {!r} is registered but has no value stored".format(key),
            hint="Run `devteam cred set {} --value ...` to store one.".format(key),
        )

    audit(project_id, "get", key, agent=agent, outcome="ok", detail={"layer": layer})
    return value


def read_system_secret(ref, backend, label):
    """Read a secret the CLI itself owns (no registered credential entry) and audit the read.

    The account session's refresh token (ADR-0029 SR-16) has no ``credentials.json`` row, so
    :func:`get_value` cannot resolve it, but its read still belongs in the same trail as every
    other secret read. The audit line carries ``label`` as the key and never the value or the
    ref. Returns ``None`` when nothing is stored.
    """
    value = secrets_module.get(ref, backend)
    audit(
        None, "get", label, agent=None,
        outcome="ok" if value is not None else "value-missing",
        detail={"layer": "system"},
    )
    return value


def unset(key, project_id=None, forget_value=False):
    """Remove the reference from the layer ``project_id`` selects.

    Deletes the backend value only when ``forget_value=True`` — a reference
    removed by mistake must not take a value that another reference (or a
    reused ref) might still point at.
    """
    _require_valid_key(key)
    with store_lock("credentials"):
        data = load(project_id)
        entry = data.get("credentials", {}).pop(key, None)
        if entry is None:
            return {"key": key, "removed": False, "value_removed": False}
        _write(data, project_id)

    value_removed = False
    if forget_value:
        value_removed = secrets_module.delete(entry["ref"], entry["source"])

    audit(
        project_id,
        "unset",
        key,
        outcome="ok",
        detail={
            "layer": "project" if project_id else "global",
            "value_removed": value_removed,
        },
    )
    return {"key": key, "removed": True, "value_removed": value_removed}


# ── v2 migration ─────────────────────────────────────────────────────────────


def import_file(path, project_id):
    """Migrate a v2 ``credentials.local.json`` into references (ADR-0010).

    Opt-in per file, on an explicit path — this **never scans the tree for
    candidates**. This repository's own root-level `credentials.local.json`,
    read on purpose by `docs/prompts/posthog-metrics-report.md`, is the proof
    case a scanning importer would have broken.

    Ordering is copy -> verify -> retire, the same one `upgrade.py` uses: every
    value is pushed into a backend and read back before the reference file is
    touched or the original is moved, and a failure partway through rolls back
    what was already stored and leaves the original file untouched.
    """
    source_path = Path(path)
    raw = jsonio.read_json(source_path, default=None)
    if raw is None:
        raise EnvError("{} does not exist or is empty".format(source_path))
    if not isinstance(raw, dict):
        raise EnvError("{}: expected a JSON object".format(source_path))

    non_secret = {}
    secret_items = {}
    for key, item_value in raw.items():
        if key in NON_SECRET_KEYS:
            non_secret[key] = item_value
            continue
        if not isinstance(item_value, str):
            raise EnvError(
                "{}: {!r} must be a string to import as a credential value".format(
                    source_path, key
                )
            )
        _require_valid_key(key)
        secret_items[key] = item_value

    # Copy phase: nothing here touches the reference file or the original yet.
    stored = {}
    try:
        for key, item_value in secret_items.items():
            ref = _ref_for(key, project_id)
            result = secrets_module.put(ref, item_value)
            verified = secrets_module.get(ref, result["backend"])
            if verified != item_value:
                raise EnvError(
                    "verification failed writing credential {!r} to {}".format(
                        key, result["backend"]
                    )
                )
            stored[key] = result
    except Exception:
        # Leave nothing half-written: roll back whatever this import already
        # pushed into a backend before propagating the failure.
        for key, result in stored.items():
            try:
                secrets_module.delete(_ref_for(key, project_id), result["backend"])
            except Exception:
                pass
        raise

    with store_lock("credentials"):
        data = load(project_id)
        credentials = data.setdefault("credentials", {})
        for key, result in stored.items():
            credentials[key] = {
                "purpose": "Imported from {}".format(source_path.name),
                "source": result["backend"],
                "ref": _ref_for(key, project_id),
                "scope": [],
            }
        for key, item_value in non_secret.items():
            data[key] = item_value
        _write(data, project_id)

    # Retire, never delete (No-Destruction Rule).
    quarantined = quarantine.move(source_path, project_id, group="credentials-import")

    audit(
        project_id,
        "import",
        "*",
        outcome="ok",
        detail={
            "layer": "project" if project_id else "global",
            "count": len(stored),
            "source": str(source_path),
        },
    )

    return {
        "imported": sorted(stored.keys()),
        "non_secret": sorted(non_secret.keys()),
        "insecure": sorted(key for key, result in stored.items() if result.get("insecure")),
        "quarantined_to": str(quarantined) if quarantined else None,
    }


# ── audit trail ──────────────────────────────────────────────────────────────


def _audit_scope(project_id):
    return project_id if project_id else _GLOBAL_AUDIT_SCOPE


def audit(project_id, action, key, agent=None, outcome="ok", detail=None):
    """Append one JSONL line: timestamp, action, key, layer, agent, outcome.

    Append-only on purpose (ADR-0013): opened with ``"a"`` and written in one
    call, so a crash mid-write can corrupt at most the last line, never an
    earlier one, and two machines' logs could one day be merged rather than
    needing to be reconciled. Never writes the value or anything derived from
    it — no length, no hash, no prefix — because the whole point of an audit
    trail is that reading it back teaches you nothing about the secret itself.
    """
    detail = dict(detail or {})
    layer = detail.pop("layer", None)
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "action": action,
        "key": key,
        "layer": layer,
        "agent": agent,
        "outcome": outcome,
    }
    if detail:
        record["detail"] = detail

    path = paths.audit_log(_audit_scope(project_id))
    jsonio.ensure_dir(path.parent)
    line = json.dumps(record, sort_keys=True).encode("utf-8") + b"\n"
    fd = os.open(str(path), os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)


# ── doctor integration ───────────────────────────────────────────────────────


def check(project_id):
    """Findings for ``devteam doctor``: never raises for what it finds wrong.

    Flags a reference with no value stored, any credential on the ``insecure``
    backend (loud by design — ADR-0010 never wants that mode to look equivalent
    to the other two), and a ``source`` this build of the CLI does not know.
    """
    findings = []
    layers = [("global", None)]
    if project_id:
        layers.append(("project", project_id))

    for layer_name, layer_project_id in layers:
        for key, entry in load(layer_project_id).get("credentials", {}).items():
            source = entry.get("source")
            if source not in secrets_module.BACKENDS:
                findings.append(
                    {"key": key, "layer": layer_name, "issue": "unknown-source", "detail": source}
                )
                continue
            if source == "insecure":
                findings.append({"key": key, "layer": layer_name, "issue": "insecure-backend"})
            try:
                value = secrets_module.get(entry.get("ref"), source)
            except secrets_module.SecretError as exc:
                findings.append(
                    {"key": key, "layer": layer_name, "issue": "backend-error", "detail": str(exc)}
                )
                continue
            if value is None:
                findings.append({"key": key, "layer": layer_name, "issue": "missing-value"})

    return findings
