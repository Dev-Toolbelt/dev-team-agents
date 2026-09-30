"""The three-layer preference cascade (ADR-0008).

    shipped defaults  ->  global user  ->  this project

All three layers are **personal**: nothing about a preference is committed. The
cascade is resolved **on write** and materialised to one file per project, so the
18 agent bodies keep doing a single file read and no merge logic enters any of
them.

``context_paths`` is deliberately absent from this module: it is topology, not a
preference, and lives in the committed ``project.json``.
"""

from __future__ import annotations

from pathlib import Path

from . import jsonio, paths, project, quarantine, versions
from .errors import EnvError, UsageError

#: Where the projection lands, relative to the project root. Stable across the
#: memory-layout change, unlike the v2 `user-data/preferences.json` path.
RESOLVED_FILE = Path(project.PROJECT_DIR) / "resolved" / "preferences.json"

#: Opt-in fields. An absent value means "never opted in", so these resolve to
#: `false` rather than to their schema default — carrying over the v2 rule that a
#: user who never saw the prompt has not consented. Writing one explicitly is the
#: only way to turn it on.
CONSENT_KEYS = ("telemetry", "auto_update")

SCOPES = ("global", "project")


def defaults_file(version):
    return versions.require(version) / "scripts" / "lib" / "preferences-defaults.json"


def defaults(version):
    data = jsonio.read_json(defaults_file(version))
    if not isinstance(data, dict):
        raise EnvError(
            "missing or malformed preference defaults in version {}".format(version),
            hint="Re-install the version with `devteam store install --force`.",
        )
    return data


def global_file():
    return paths.global_preferences_file()


def project_file(project_id):
    return paths.project_data_dir(project_id) / "preferences.json"


def _layer(path):
    data = jsonio.read_json(path, default=None)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise EnvError(
            "{} is not a JSON object".format(path),
            hint="Fix the file by hand; dev-team-agents will not overwrite it.",
        )
    return data


def resolve(project_id, version):
    """The merged view, plus where each value came from."""
    base = defaults(version)
    layers = (
        ("defaults", base),
        ("global", _layer(global_file())),
        ("project", _layer(project_file(project_id)) if project_id else {}),
    )

    merged = {}
    origin = {}
    for name, layer in layers:
        for key, value in layer.items():
            if name != "defaults" and key not in base:
                # An unknown key is kept, not dropped — a newer CLI may own it —
                # but it is reported so a typo does not masquerade as a setting.
                origin.setdefault(key, name)
                merged[key] = value
                continue
            merged[key] = value
            origin[key] = name

    for key in CONSENT_KEYS:
        if origin.get(key) == "defaults":
            merged[key] = False
            origin[key] = "consent-withheld"

    unknown = sorted(k for k in merged if k not in base)
    return {"values": merged, "origin": origin, "unknown": unknown}


def materialize(project_root, project_id, version):
    """Write the projection the agents read. Returns a manifest record."""
    resolved = resolve(project_id, version)
    payload = dict(resolved["values"])
    # A generated file that looks hand-editable invites edits that the next sync
    # silently discards. The marker is inside the data because JSON has no
    # comments, and it names the command that does persist a change.
    payload["_generated_by"] = "devteam sync — edit with `devteam prefs set`, not by hand"
    target = Path(project_root) / RESOLVED_FILE
    jsonio.write_json_atomic(target, payload, mode=jsonio.PROJECT_FILE_MODE, dir_mode=None)
    return {
        # `.as_posix()`: see the comment in `project._write_pointer` — this
        # manifest key must match the forward-slash form everything else in the
        # manifest, the exclude block and `.gitignore` uses.
        "path": RESOLVED_FILE.as_posix(),
        "kind": "resolved",
        "keys": len(resolved["values"]),
        "unknown": resolved["unknown"],
    }


def get(project_id, version, key=None):
    resolved = resolve(project_id, version)
    if key is None:
        return resolved
    if key not in resolved["values"]:
        raise UsageError(
            "unknown preference {!r}".format(key),
            hint="Run `devteam prefs list` to see every key.",
        )
    return {
        "key": key,
        "value": resolved["values"][key],
        "origin": resolved["origin"].get(key),
    }


def _coerce(key, raw, base):
    """Parse a command-line string against the type the default declares."""
    if key not in base:
        raise UsageError(
            "unknown preference {!r}".format(key),
            hint="Run `devteam prefs list` to see every key.",
        )
    expected = base[key]
    text = raw.strip()
    if text.lower() in ("null", "none", ""):
        return None
    if isinstance(expected, bool) or text.lower() in ("true", "false"):
        if text.lower() not in ("true", "false"):
            raise UsageError("{} expects true or false, got {!r}".format(key, raw))
        return text.lower() == "true"
    if isinstance(expected, int) and not isinstance(expected, bool):
        try:
            return int(text)
        except ValueError:
            raise UsageError("{} expects an integer, got {!r}".format(key, raw)) from None
    if isinstance(expected, float):
        try:
            return float(text)
        except ValueError:
            raise UsageError("{} expects a number, got {!r}".format(key, raw)) from None
    if isinstance(expected, list):
        return [item.strip() for item in text.split(",") if item.strip()]
    return text


def set_value(key, raw_value, version, scope="global", project_id=None):
    """Write into a source layer — never into the projection."""
    if scope not in SCOPES:
        raise UsageError("scope must be one of: {}".format(", ".join(SCOPES)))
    if scope == "project" and not project_id:
        raise UsageError("a project scope needs a bound project")

    base = defaults(version)
    value = _coerce(key, raw_value, base)
    target = global_file() if scope == "global" else project_file(project_id)
    layer = _layer(target)
    layer[key] = value
    jsonio.write_json_atomic(target, layer)
    return {"key": key, "value": value, "scope": scope, "file": str(target)}


def unset(key, scope="global", project_id=None):
    """Remove a key from one layer so the layer below it takes over again."""
    if scope not in SCOPES:
        raise UsageError("scope must be one of: {}".format(", ".join(SCOPES)))
    target = global_file() if scope == "global" else project_file(project_id)
    layer = _layer(target)
    if key not in layer:
        return {"key": key, "scope": scope, "removed": False, "file": str(target)}
    layer.pop(key)
    jsonio.write_json_atomic(target, layer)
    return {"key": key, "scope": scope, "removed": True, "file": str(target)}


# ── the v2 in-project preferences file ─────────────────────────────────────────

#: Where a v2 install, and a layout-1 project, kept its preferences. The cascade never
#: reads it: `project_file()` is the project layer on every layout.
LEGACY_FILE_NAME = "preferences.json"

#: The one key the v2 schema documented as "bool or array" (suppress by notification type).
#: Its default is a boolean, so the type check would otherwise throw the list away.
BOOL_OR_LIST_KEYS = ("suppress_notifications",)

#: The quarantine group an imported file is moved into — findable by name, never deleted.
IMPORTED_GROUP = "imported-preferences"


def legacy_file(project_root):
    return project.legacy_memory_dir(project_root) / LEGACY_FILE_NAME


def _fits_default(key, value, default):
    """Whether ``value`` could have been stored for a key with this ``default``."""
    if key in BOOL_OR_LIST_KEYS and isinstance(value, list):
        return all(isinstance(item, str) for item in value)
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, int):
        return isinstance(value, int) and not isinstance(value, bool)
    if isinstance(default, float):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if isinstance(default, str):
        return isinstance(value, str)
    if isinstance(default, list):
        return isinstance(value, list)
    if default is None:
        return value is None or isinstance(value, (bool, int, float, str))
    return False


def import_legacy(project_root, project_id, version, emitter=None):
    """Adopt a v2 ``user-data/preferences.json`` as this project's preference layer.

    Before this, a project bound over a v2 install kept its preferences in a file the
    cascade never reads, so they silently stopped applying, and a later ``devteam
    upgrade`` refused because the same name already existed at its destination.

    Copy → verify → retire, the order ``upgrade`` uses: declared keys whose value fits
    the default's type are written into the project layer, read back and compared, and
    only then is the file moved to quarantine — never deleted (No-Destruction Rule).

    - **The project layer wins a conflict.** A value already there was set through the
      CLI or the app after the v2 file was last written, so it is the newer decision.
    - **Unknown and ill-typed keys do not hold the import back.** They are reported, and
      the quarantined file keeps them recoverable.

    Returns ``None`` when there is no legacy file, else a report. The file is left in
    place, with ``problem`` set, when it cannot be read or the write did not verify.
    """
    source = legacy_file(project_root)
    if not source.is_file():
        return None
    report = {
        "source": "{}/{}/{}".format(project.PROJECT_DIR, project.LEGACY_MEMORY_DIR, LEGACY_FILE_NAME),
        "imported": [],
        "unchanged": [],
        "conflicts": [],
        "ignored": [],
        "quarantined": None,
        "problem": None,
    }

    try:
        legacy = jsonio.read_json(source)
    except EnvError as exc:
        legacy = exc
    if not isinstance(legacy, dict):
        report["problem"] = "not a JSON object; left in place" if not isinstance(legacy, EnvError) else str(legacy)
        if emitter is not None:
            emitter.warn("{} was not imported: {}".format(report["source"], report["problem"]))
        return report

    base = defaults(version)
    target = project_file(project_id)
    layer = _layer(target)
    for key in sorted(legacy):
        value = legacy[key]
        if key not in base:
            report["ignored"].append({"key": key, "reason": "unknown"})
        elif not _fits_default(key, value, base[key]):
            report["ignored"].append({"key": key, "reason": "invalid"})
        elif key in layer:
            report["unchanged" if layer[key] == value else "conflicts"].append(key)
        else:
            layer[key] = value
            report["imported"].append(key)

    if report["imported"]:
        jsonio.write_json_atomic(target, layer)
        written = _layer(target)
        unverified = [key for key in report["imported"] if written.get(key) != legacy[key]]
        if unverified:
            report["problem"] = "the project layer did not read back {}; left in place".format(
                ", ".join(unverified)
            )
            if emitter is not None:
                emitter.warn("{} was not retired: {}".format(report["source"], report["problem"]))
            return report

    report["quarantined"] = str(quarantine.move(source, project_id, group=IMPORTED_GROUP))
    if emitter is not None:
        if report["conflicts"]:
            emitter.warn(
                "kept this project's stored value over {} for: {}".format(
                    report["source"], ", ".join(report["conflicts"])
                )
            )
        if report["ignored"]:
            emitter.warn(
                "not imported from {} (see the quarantined copy): {}".format(
                    report["source"],
                    ", ".join("{} ({})".format(item["key"], item["reason"]) for item in report["ignored"]),
                )
            )
    return report

