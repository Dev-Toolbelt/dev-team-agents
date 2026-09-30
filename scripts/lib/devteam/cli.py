"""Argument parsing and the subcommand table.

Every handler returns ``(payload, human)``: the JSON body and a terminal
rendering of the same facts. Nothing prints directly, so the ``--json`` contract
cannot be broken by a stray ``print``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import bind as bind_module
from . import catalog, compat, creds, doctor, global_skills, migrate, notifications, paths, prefs, project, providers, registry, store, tasks, update, upgrade, versions
from . import secrets as secrets_module
from .errors import ConflictError, DevteamError, EnvError, UsageError
from .output import Emitter

PROGRAM = "devteam"


class _Parser(argparse.ArgumentParser):
    """An ``ArgumentParser`` that routes its own errors through the CLI contract.

    argparse calls ``sys.exit(2)`` itself, so a bad flag printed usage text on
    stderr and **nothing** on stdout — breaking the documented promise that
    ``--json`` always emits exactly one document, on the paths a client is most
    likely to hit (`--mode bogus`, `--provider bogus`, a missing `--from`).
    """

    def error(self, message):
        raise UsageError(message, hint="Run `devteam --help` or `devteam <command> --help`.")

    def exit(self, status=0, message=None):
        if status:
            raise UsageError((message or "").strip() or "invalid arguments")
        raise _HelpRequested()


class _HelpRequested(Exception):
    """``--help`` printed its text; exit cleanly without an error payload."""


def _short(project_id):
    return project_id.split("-")[0]


def _table(rows, headers):
    widths = [len(h) for h in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(str(cell)))
    out = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)).rstrip()]
    out.append("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        out.append("  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
    return "\n".join(out)


def cmd_path(args, emitter):
    payload = paths.describe()
    human = "\n".join(
        "{:<20} {}".format(key, value) for key, value in payload.items() if value is not None
    )
    return payload, human


def cmd_version(args, emitter):
    # The `compat` block is what ADR-0011's "compatibility is declared, not assumed"
    # costs: a client — the desktop app is the first — reads the shape numbers before
    # it writes, and degrades to read-only when the store carries one it does not
    # understand. It lives on `version` because that is the call a client makes first.
    payload = {
        "current": versions.current(),
        "installed": versions.installed(),
        "core": str(paths.core_dir()),
        "compat": compat.describe(),
    }
    schemas = payload["compat"]["store_schemas"]
    human = "\n".join(
        [
            "current: {}".format(payload["current"] or "(none)"),
            "installed: {}".format(", ".join(payload["installed"]) or "(none)"),
            "json contract: {}".format(payload["compat"]["json_contract"]),
            "store shapes: {}".format(
                ", ".join("{}={}".format(k, schemas[k]) for k in sorted(schemas))
            ),
        ]
    )
    return payload, human


def cmd_compat(args, emitter):
    # ADR-0011 named this the missing enforcement point: `compat.unsupported_by()`
    # implemented the comparison but had no caller outside its tests, so "the app
    # degrades to read-only" had nothing that actually asked the question. This is
    # that caller — a client states what it understands and gets back a boolean it
    # can branch on, computed by the framework rather than re-derived per client.
    description = compat.describe()
    payload = {
        "json_contract": description["json_contract"],
        "min_app_version": description["min_app_version"],
        "store_schemas": description["store_schemas"],
        "client_schemas": None,
        "may_write": None,
        "unsupported": {},
    }

    unsupported = {}
    parsed = None
    if args.client is not None:
        parsed = compat.parse_client_schemas(args.client, "--client")
    elif args.client_file is not None:
        # The label names the flag, not just the path: `--client-file /nope/x.json could
        # not be read`. That attribution was lost when this call site stopped carrying its
        # own reader, and it is the exact property `compat`'s docstring argues for.
        parsed = compat.load_client_schemas(
            args.client_file, source="--client-file {}".format(args.client_file)
        )
    else:
        # Neither flag: fall back to the global declaration seam, so a client that
        # exported `DEVTEAM_CLIENT_SCHEMAS` once gets `may_write` from a bare
        # `devteam compat` instead of having to restate the same file in a second flag
        # form. An explicit `--client`/`--client-file` outranks it — more specific wins,
        # the same precedence the seam itself uses between flag and variable.
        declaration = compat.client_declaration(
            getattr(args, "client_schemas", None), os.environ
        )
        if declaration is not None:
            parsed = declaration.schemas

    if parsed is not None:
        unsupported = compat.unsupported_by(parsed)
        payload["client_schemas"] = parsed
        payload["unsupported"] = unsupported
        # A boolean the client can branch on directly, rather than inferring the
        # verdict from whether `unsupported` happens to be empty — inference is how
        # a client gets exactly this backwards.
        payload["may_write"] = not unsupported

    lines = [
        "json contract: {}".format(payload["json_contract"]),
        "min app version: {}".format(payload["min_app_version"] or "(none asserted)"),
        "store shapes: {}".format(
            ", ".join(
                "{}={}".format(k, payload["store_schemas"][k])
                for k in sorted(payload["store_schemas"])
            )
        ),
    ]
    if payload["client_schemas"] is not None:
        if payload["may_write"]:
            lines.append("may_write: yes — this client understands every shape the store uses")
        else:
            lines.append("may_write: no — upgrade the client before it writes to this store")
            for name in sorted(unsupported):
                info = unsupported[name]
                lines.append(
                    "  {:<16} store={} client={}".format(name, info["store"], info["client"])
                )
    return payload, "\n".join(lines)


def cmd_store_list(args, emitter):
    installed = versions.installed()
    active = versions.current()
    pinned = versions.pinned_versions()
    rows = [
        (v, "current" if v == active else "", "pinned" if v in pinned else "") for v in installed
    ]
    payload = {"installed": installed, "current": active, "pinned": sorted(pinned)}
    human = _table(rows, ["VERSION", "ACTIVE", "PINNED"]) if rows else "no version installed"
    return payload, human


def cmd_store_install(args, emitter):
    version = versions.install_from_tree(
        args.source, version=args.version, force=args.force, make_current=args.activate
    )
    payload = {"version": version, "current": versions.current(), "source": str(Path(args.source).resolve())}
    return payload, "installed {} into the core (current: {})".format(version, payload["current"])


def cmd_store_use(args, emitter):
    versions.set_current(args.version)
    return {"current": args.version}, "current = {}".format(args.version)


def cmd_store_gc(args, emitter):
    result = versions.gc(dry_run=not args.apply)
    if args.apply:
        human = "removed: {}".format(", ".join(result["removed"]) or "(nothing)")
    else:
        human = "would remove: {}\nkept: {}\n(pass --apply to remove)".format(
            ", ".join(result["would_remove"]) or "(nothing)", ", ".join(result["kept"])
        )
    return result, human


def cmd_bind(args, emitter):
    # Here, not in `bind_module.bind()`: `sync`, `sync --all` and `migrate` all call
    # that function, and a refusal there would stop a project that was already bound
    # over a v2 install from ever syncing again. Only a bind the user asked for is
    # refused. Binding over a v2 install used to succeed — it adopted the old relative
    # links and left the vendored tree tracked in git, where `doctor` could no longer
    # see it. `--mode vendored` is let through: that path already quarantines any
    # existing tree before re-vendoring.
    if args.mode != "vendored":
        root = project.resolve_root(args.path)
        leftover = migrate.leftover_trees(root) if root.is_dir() else []
        if leftover:
            raise ConflictError(
                "{} is a v2 vendored install ({} under {}/) — bind would leave that tree "
                "behind".format(root, ", ".join(leftover), project.PROJECT_DIR),
                hint="Run `devteam migrate` — it shows a plan first, binds, and moves the "
                "old tree into a dated quarantine rather than deleting it.",
            )
    if args.pin is not None:
        paths.validate_version(args.pin)
    result = bind_module.bind(
        args.path,
        provider_names=args.provider,
        mode=args.mode,
        pin=args.pin,
        emitter=emitter,
    )
    human = "\n".join(
        [
            "bound {}".format(result["path"]),
            "  identity  {}{}".format(
                result["project_id"], " (created)" if result["identity_created"] else ""
            ),
            "  version   {}".format(result["version"]),
            "  mode      {}".format(result["mode"]),
            "  providers {}".format(", ".join(result["providers"])),
            "  artifacts {}".format(result["artifacts"]),
        ]
        + (
            ["  pin       {}".format(result["pin"])] if result.get("pin") else []
        )
        + (
            [
                "  retired   {} path(s) moved to quarantine".format(len(result["retired"])),
            ]
            if result.get("retired")
            else []
        )
        + (
            [
                "  merged    {} — project config, commit these yourself".format(
                    ", ".join(result["merged_project_files"])
                ),
            ]
            if result.get("merged_project_files")
            else []
        )
        + _preferences_import_lines(result.get("preferences_import"))
    )
    return result, human


def _preferences_import_lines(report):
    """The human summary of `prefs.import_legacy`, or nothing when there was no file."""
    if not report:
        return []
    if report.get("problem"):
        return ["  prefs     {} not imported: {}".format(report["source"], report["problem"])]
    return [
        "  prefs     {} imported from {}, file moved to quarantine".format(
            len(report["imported"]), report["source"]
        )
    ]


def cmd_unbind(args, emitter):
    result = bind_module.unbind(
        args.path, project_id=args.project_id, keep_artifacts=args.keep_artifacts
    )
    lines = [
        "unbound {}".format(result["path"]),
        "  unlinked    {}".format(len(result["unlinked"])),
        "  quarantined {}".format(len(result["quarantined"])),
        "  kept        {}".format(", ".join(result["kept"])),
    ]
    if result["removed_dirs"]:
        lines.append("  removed     {} empty dir(s)".format(len(result["removed_dirs"])))
    if result["quarantined"]:
        lines.append("  quarantine  {}".format(result["quarantined"][0]["to"]))
    if result["problems"]:
        lines.append("  problems    {}".format(len(result["problems"])))
    return result, "\n".join(lines)


def cmd_list(args, emitter):
    entries = registry.entries()
    active = versions.current()
    rows = []
    payload_projects = []
    for project_id, entry in sorted(entries.items(), key=lambda kv: kv[1].get("path", "")):
        pin = entry.get("pin")
        resolved = pin or active
        drift = "pinned" if pin and pin != active else ""
        exists = Path(entry.get("path", "")).is_dir()
        if not exists:
            drift = "MISSING"
        rows.append(
            (
                _short(project_id),
                entry.get("path", ""),
                ",".join(entry.get("providers", [])),
                entry.get("mode", ""),
                resolved or "?",
                drift,
            )
        )
        payload_projects.append(
            {
                "project_id": project_id,
                "path": entry.get("path"),
                "providers": entry.get("providers", []),
                "mode": entry.get("mode"),
                "pin": pin,
                "resolves_to": resolved,
                "path_exists": exists,
            }
        )
    payload = {"current": active, "projects": payload_projects}
    human = (
        _table(rows, ["ID", "PATH", "PROVIDERS", "MODE", "VERSION", "NOTE"])
        if rows
        else "no project bound yet — run `devteam bind` inside one"
    )
    return payload, human


def cmd_sync(args, emitter):
    if args.all:
        result = bind_module.sync_all(emitter=emitter)
        human = "synced {} project(s){}".format(
            len(result["synced"]),
            "" if not result["problems"] else "; {} problem(s)".format(len(result["problems"])),
        )
        return result, human
    if args.project_id:
        result = bind_module.sync_project(args.project_id, emitter=emitter)
    else:
        root = project.resolve_root(args.path)
        data = project.load(root)
        if data is None:
            raise UsageError(
                "{} is not a bound project".format(root), hint="Run `devteam bind` first."
            )
        result = bind_module.sync_project(data["project_id"], emitter=emitter)
    return result, "synced {} to {}".format(result["path"], result["version"])


def cmd_pin(args, emitter):
    root = project.resolve_root(args.path)
    data = project.load(root)
    if data is None:
        raise UsageError("{} is not a bound project".format(root))
    if args.release:
        entry = registry.set_pin(data["project_id"], None)
        human = "pin released — {} now follows current".format(root)
    else:
        if not args.version:
            raise UsageError("pass a version to pin, or --release to clear the pin")
        paths.validate_version(args.version)
        versions.require(args.version)
        entry = registry.set_pin(data["project_id"], args.version)
        human = "pinned {} to {}".format(root, args.version)
    return {"project_id": data["project_id"], "pin": entry.get("pin"), "path": str(root)}, human


def cmd_update(args, emitter):
    if args.check:
        result = update.check()
        human = "latest {} | installed: {} | current: {}".format(
            result["latest_ref"], ", ".join(result["installed"]) or "(none)", result["current"] or "(none)"
        )
        return result, human
    result = update.run(
        ref=args.ref,
        activate=not args.no_activate,
        sync=not args.no_sync,
        force=args.force,
        sha256=args.sha256,
        emitter=emitter,
    )
    lines = [
        "{} {} | current: {} | synced {} project(s)".format(
            "installed" if result["installed_now"] else "already present:",
            result["version"],
            result["activated"] or versions.current(),
            result["synced"],
        )
    ]
    integrity = result.get("integrity")
    if integrity and not integrity.get("verified"):
        lines.append(
            "  integrity NOT verified (no digest pinned) — sha256 {}".format(integrity["sha256"])
        )
    if result["problems"]:
        lines.append("  {} project(s) failed to sync:".format(len(result["problems"])))
        for problem in result["problems"]:
            lines.append("    {}: {}".format(problem["project_id"], problem["error"]))
    return result, "\n".join(lines)


def cmd_migrate(args, emitter):
    if getattr(args, "pin", None) is not None:
        paths.validate_version(args.pin)
    if args.apply:
        result = migrate.apply(
            args.path, provider_names=args.provider, mode=args.mode, pin=args.pin, emitter=emitter
        )
        lines = [
            "migrated {}".format(result["path"]),
            "  identity   {}".format(result["project_id"]),
            "  version    {}".format(result["version"]),
            "  quarantine {}".format(result["quarantine_dir"] or "(nothing moved)"),
            "  preserved  {}".format(", ".join(result["preserved"])),
        ]
        untrack = result["git_tracked"] + result["git_tracked_artifacts"]
        if untrack:
            lines.append(
                "  git        {} path(s) still tracked — commit their removal:".format(len(untrack))
            )
            lines.append("               git rm -r --cached {}".format(" ".join(untrack)))
        if result["unrecognised"]:
            lines.append("  left alone {}".format(", ".join(result["unrecognised"])))
        return result, "\n".join(lines)

    result = migrate.plan(args.path, provider_names=args.provider, mode=args.mode)
    lines = ["migration plan for {} (nothing changed)".format(result["path"])]
    lines.extend("  - {}".format(action) for action in result["actions"])
    untrack = result["git_tracked"] + result["git_tracked_artifacts"]
    if untrack:
        lines.append("  after --apply, untrack them (the files stay on disk):")
        lines.append("    git rm -r --cached {}".format(" ".join(untrack)))
    lines.append("  run again with --apply to execute")
    return result, "\n".join(lines)


def cmd_doctor(args, emitter):
    target = None if args.no_project else (args.path or ".")
    result = doctor.run(project_root=target, reassign_identity=args.reassign_identity)
    lines = []
    for item in result["findings"]:
        marker = {"ok": "ok  ", "warn": "WARN", "fail": "FAIL"}[item["level"]]
        lines.append("{} [{}] {}".format(marker, item["category"], item["message"]))
        if item.get("hint"):
            lines.append("        hint: {}".format(item["hint"]))
    lines.append("status: {}".format(result["status"]))
    return result, "\n".join(lines)



def _bound_project(path=None, required=True):
    """``(root, project_id)`` for a path, or ``(root, None)`` when unbound."""
    root = project.resolve_root(path)
    data = project.load(root)
    if data is None:
        if required:
            raise UsageError(
                "{} is not a bound project".format(root), hint="Run `devteam bind` first."
            )
        return root, None
    return root, data["project_id"]


def _catalog_version(args):
    """This project's pin, else the active version — same resolution as ``prefs``."""
    _root, project_id = _bound_project(getattr(args, "path", None), required=False)
    pin = (registry.get(project_id) or {}).get("pin") if project_id else None
    return versions.resolve(pin), project_id


def _catalog_row(kind, entry):
    if entry.get("malformed"):
        note = "MALFORMED: {}".format(entry["error"])
        if kind == "agents":
            return (entry["name"], "-", "-", entry["path"], note)
        if kind == "skills":
            return (entry["name"], entry.get("category") or "-", entry["path"], note)
        return (entry["name"], entry["path"], note)
    if kind == "agents":
        return (
            entry["name"],
            entry.get("tier") or "-",
            entry.get("model") or "-",
            entry["path"],
            entry.get("description") or "-",
        )
    if kind == "skills":
        return (entry["name"], entry.get("category") or "-", entry["path"], entry.get("description") or "-")
    return (entry["name"], entry["path"], entry.get("description") or "-")


_CATALOG_HEADERS = {
    "agents": ["NAME", "TIER", "MODEL", "PATH", "DESCRIPTION"],
    "skills": ["NAME", "CATEGORY", "PATH", "DESCRIPTION"],
    "commands": ["NAME", "PATH", "DESCRIPTION"],
}


def cmd_catalog(args, emitter):
    version, project_id = _catalog_version(args)
    result = catalog.summary(version)
    payload = {
        "version": version,
        "project_id": project_id,
        "counts": result["counts"],
        "malformed": result["malformed"],
    }
    lines = ["version: {}".format(version)]
    if project_id:
        lines.append("project: {}".format(_short(project_id)))
    for kind in catalog.KINDS:
        note = (
            "  ({} malformed)".format(result["malformed"][kind]) if result["malformed"][kind] else ""
        )
        lines.append("{:<10} {}{}".format(kind, result["counts"][kind], note))
    return payload, "\n".join(lines)


def _cmd_catalog_kind(kind):
    def handler(args, emitter):
        version, project_id = _catalog_version(args)
        entries = catalog.list_kind(kind, version)
        rows = [_catalog_row(kind, entry) for entry in entries]
        payload = {
            "version": version,
            "project_id": project_id,
            kind: entries,
            "count": len(entries),
        }
        human = (
            _table(rows, _CATALOG_HEADERS[kind])
            if rows
            else "no {} found in version {}".format(kind, version)
        )
        return payload, human

    return handler


cmd_catalog_agents = _cmd_catalog_kind("agents")
cmd_catalog_skills = _cmd_catalog_kind("skills")
cmd_catalog_commands = _cmd_catalog_kind("commands")


def cmd_catalog_show(args, emitter):
    version, project_id = _catalog_version(args)
    result = catalog.show(args.name, version)
    payload = dict(result)
    payload["project_id"] = project_id
    lines = ["{} ({})".format(result["name"], result["kind"])]
    lines.append("  path      {}".format(result["path"]))
    lines.append("  version   {}".format(result["version"]))
    if result.get("tier"):
        lines.append("  tier      {}".format(result["tier"]))
    if result.get("model"):
        lines.append("  model     {}".format(result["model"]))
    if result.get("category"):
        lines.append("  category  {}".format(result["category"]))
    if result.get("description"):
        lines.append("  {}".format(result["description"]))
    lines.append("")
    lines.append(result["body"])
    return payload, "\n".join(lines)


def _notification_line(record):
    return "{:<8} {}  {}".format(record["level"], _short(record["project_id"]), record["message"])


def cmd_notifications_list(args, emitter):
    records = notifications.collect(args.project or None, unseen_only=args.unseen)
    payload = {"notifications": records, "count": len(records)}
    human = "\n".join(_notification_line(r) for r in records) or "no notifications"
    return payload, human


def cmd_notifications_ack(args, emitter):
    marked = notifications.ack(args.ids, all_=args.all, project_ids=args.project or None)
    return {"acknowledged": marked, "count": len(marked)}, "acknowledged {}".format(len(marked))


def _watch_interval(text):
    # Zero or a negative value would make `watch` a busy loop of `stat` calls.
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError("not a number: {!r}".format(text))
    if not value >= 0.01:
        raise argparse.ArgumentTypeError("must be at least 0.01 seconds")
    return value


def cmd_notifications_watch(args, emitter):
    def emit(event):
        human = None
        if event["event"] == "notification":
            human = _notification_line(event["notification"])
        emitter.stream(event, human)

    reason = notifications.watch(emit, interval=args.interval)
    return {"reason": reason}, None


def _hook_payload():
    """The hook JSON on stdin, or ``{}`` — a hook must never fail on what it was fed."""
    try:
        if sys.stdin is None or sys.stdin.isatty():
            return {}
        data = json.loads(sys.stdin.read() or "null")
    except (OSError, ValueError, RecursionError):
        return {}
    return data if isinstance(data, dict) else {}


def _hook_root(args):
    try:
        return project.resolve_root(args.project_root)
    except DevteamError:
        return Path(args.project_root) if args.project_root else Path.cwd()


def cmd_tasks_record(args, emitter):
    result = tasks.record(_hook_root(args), _hook_payload(), provider=args.provider)
    return result, "recorded" if result["recorded"] else "nothing recorded"


def cmd_tasks_mark(args, emitter):
    result = tasks.mark(_hook_root(args), _hook_payload(), args.state)
    return result, "marked ({} open)".format(result["open"]) if result["marked"] else "nothing marked"


def _tasks_filters(args):
    return dict(
        project_ids=args.project or None,
        since=args.since,
        stale_after=args.stale_after,
        ended_after=args.ended_after,
    )


def _duration(seconds):
    minutes = int(seconds) // 60
    return "{}h{:02d}m".format(minutes // 60, minutes % 60) if minutes >= 60 else "{}m".format(minutes)


def cmd_tasks_list(args, emitter):
    board = tasks.collect(**_tasks_filters(args))
    lines = []
    for item in board["projects"]:
        counts = item["counts"]
        lines.append(
            "{}  todo {} · in progress {} · done {}  ({} session(s), {} stale, {} abandoned)".format(
                _short(item["project_id"]),
                counts["todo"],
                counts["in_progress"],
                counts["done"],
                item["sessions_total"],
                item["stale"],
                item["abandoned"],
            )
        )
        for session in item["sessions"]:
            lines.append("  {} {} [{}] {}".format(session["provider"], session["session_id"], session["status"], session["branch"] or ""))
            for task in session["tasks"]:
                lines.append("    {:<11} {}  ({})".format(task["column"], task["content"], _duration(task["durations"].get(task["status"], 0))))
    return board, "\n".join(lines) or "no tasks"


def cmd_tasks_watch(args, emitter):
    def emit(event):
        human = None
        if event["event"] == "snapshot" and not event["project"].get("removed"):
            human = "{} {}".format(_short(event["project"]["project_id"]), event["project"]["counts"])
        emitter.stream(event, human)

    kwargs = _tasks_filters(args)
    reason = tasks.watch(emit, interval=args.interval, **kwargs)
    return {"reason": reason}, None


def _skill_row(entry):
    flags = []
    if entry["is_symlink"]:
        flags.append("link")
    if entry["managed"]:
        flags.append("managed")
    if entry["status"] != "ok":
        flags.append("MALFORMED: {}".format(entry["error"]))
    return (
        entry["name"],
        entry["root"],
        ",".join(entry["providers"]),
        " ".join(flags) or "-",
        entry["description"] or "-",
    )


def cmd_skills_list(args, emitter):
    payload = global_skills.list_skills(args.provider)
    rows = [_skill_row(entry) for entry in payload["skills"]]
    lines = [
        "{:<9} {}{}".format(root["id"], root["path"], "" if root["exists"] else "  (absent)")
        for root in payload["roots"]
    ]
    lines.append("")
    lines.append(
        _table(rows, ["NAME", "ROOT", "PROVIDERS", "FLAGS", "DESCRIPTION"])
        if rows
        else "no global skills installed"
    )
    return payload, "\n".join(lines)


def cmd_skills_show(args, emitter):
    payload = global_skills.show(args.name, args.root)
    lines = ["{} ({})".format(payload["name"], payload["root"])]
    lines.append("  path       {}".format(payload["path"]))
    lines.append("  providers  {}".format(", ".join(payload["providers"])))
    if payload["is_symlink"]:
        lines.append("  link to    {}".format(payload["link_target"]))
    if payload["status"] != "ok":
        lines.append("  MALFORMED  {}".format(payload["error"]))
    if payload["description"]:
        lines.append("  {}".format(payload["description"]))
    lines.append("  files      {}{}".format(len(payload["files"]), "+" if payload["files_truncated"] else ""))
    if payload["body"]:
        lines.append("")
        lines.append(payload["body"])
    return payload, "\n".join(lines)


def cmd_skills_install(args, emitter):
    payload = global_skills.install(
        args.source,
        providers=args.provider,
        root_ids=args.root,
        replace=args.replace,
        link=args.link,
    )
    lines = []
    for item in payload["installed"]:
        note = ""
        if item["quarantined_to"]:
            note = "  (previous copy quarantined to {})".format(item["quarantined_to"])
        elif item["replaced"]:
            note = "  (previous link replaced)"
        lines.append("installed {} -> {}{}".format(payload["name"], item["path"], note))
    for other in payload["also_present"]:
        lines.append(
            "note: {} also exists in the {} root ({}); a provider reading both sees two copies".format(
                payload["name"], other["root"], other["path"]
            )
        )
    return payload, "\n".join(lines)


def cmd_skills_remove(args, emitter):
    payload = global_skills.remove(args.name, args.root)
    if payload["action"] == "unlinked":
        human = "unlinked {} (it pointed at {})".format(payload["path"], payload["link_target"])
    else:
        human = "moved {} to quarantine: {}".format(payload["path"], payload["quarantined_to"])
    return payload, human


def cmd_prefs_list(args, emitter):
    root, project_id = _bound_project(args.path, required=False)
    version = versions.resolve((registry.get(project_id) or {}).get("pin") if project_id else None)
    resolved = prefs.resolve(project_id, version)
    rows = [
        (key, str(resolved["values"][key]), resolved["origin"].get(key, "?"))
        for key in sorted(resolved["values"])
    ]
    payload = {
        "project_id": project_id,
        "version": version,
        "values": resolved["values"],
        "origin": resolved["origin"],
        "unknown": resolved["unknown"],
    }
    human = _table(rows, ["KEY", "VALUE", "FROM"])
    if resolved["unknown"]:
        human += "\n\nunknown key(s) carried through: {}".format(", ".join(resolved["unknown"]))
    return payload, human


def cmd_prefs_get(args, emitter):
    root, project_id = _bound_project(args.path, required=False)
    version = versions.resolve((registry.get(project_id) or {}).get("pin") if project_id else None)
    result = prefs.get(project_id, version, key=args.key)
    return result, "{} = {}  (from {})".format(result["key"], result["value"], result["origin"])


def cmd_prefs_set(args, emitter):
    root, project_id = _bound_project(args.path, required=args.scope == "project")
    version = versions.resolve((registry.get(project_id) or {}).get("pin") if project_id else None)
    result = prefs.set_value(
        args.key, args.value, version, scope=args.scope, project_id=project_id
    )
    if project_id:
        prefs.materialize(root, project_id, version)
    return result, "{} = {} in the {} layer".format(result["key"], result["value"], result["scope"])


def cmd_prefs_unset(args, emitter):
    root, project_id = _bound_project(args.path, required=args.scope == "project")
    result = prefs.unset(args.key, scope=args.scope, project_id=project_id)
    if project_id:
        version = versions.resolve((registry.get(project_id) or {}).get("pin"))
        prefs.materialize(root, project_id, version)
    human = "{} {} from the {} layer".format(
        "removed" if result["removed"] else "was not set in", result["key"], result["scope"]
    )
    return result, human


def _cred_project_id(args):
    """``None`` for the global layer, this project's id otherwise."""
    if getattr(args, "global_layer", False):
        return None
    _, project_id = _bound_project(getattr(args, "path", None))
    return project_id


def cmd_cred_list(args, emitter):
    project_id = _cred_project_id(args)
    entries = creds.list_entries(project_id)
    rows = [
        (e["key"], e["layer"], e["source"], ",".join(e["scope"]) or "-", e["purpose"])
        for e in entries
    ]
    payload = {"project_id": project_id, "credentials": entries, "count": len(entries)}
    human = (
        _table(rows, ["KEY", "LAYER", "SOURCE", "SCOPE", "PURPOSE"])
        if rows
        else "no credentials declared — add one with `devteam cred set`"
    )
    return payload, human


def cmd_cred_get(args, emitter):
    # The one command whose stdout IS the payload. ADR-0010: it "prints the value on
    # stdout and nothing else". Wrapping a secret in a `--json` document would put it
    # into a structure a client is likely to log, so `--json` is refused here rather
    # than silently honoured — a documented exception to the --json contract, because
    # the alternative is a contract that leaks.
    if emitter.as_json:
        raise UsageError(
            "`devteam cred get` does not support --json",
            hint=(
                "It writes the value to stdout and nothing else, so it cannot be wrapped "
                "in a document without putting a secret somewhere a client would log. Use "
                "`devteam cred list --json` for the references."
            ),
        )
    project_id = _cred_project_id(args)
    value = creds.get_value(args.key, project_id, agent=args.agent)
    emitter.raw(value)
    return {"key": args.key, "delivered": True}, None


def cmd_cred_set(args, emitter):
    project_id = _cred_project_id(args)
    # Never from argv: a value in a command line is in the process table for every
    # other user on the machine, and in the shell history of this one.
    value = _read_secret_from_stdin(args.key)
    scope = [s.strip() for s in (args.scope or "").split(",") if s.strip()]
    result = creds.set_entry(
        args.key,
        args.purpose,
        ref_scope=scope,
        project_id=project_id,
        value=value,
        backend=args.backend,
    )
    lines = [
        "stored {}".format(result["key"]),
        "  layer    {}".format(result["layer"]),
        "  source   {}".format(result["source"]),
        "  ref      {}".format(result["ref"]),
        "  scope    {}".format(", ".join(result["scope"]) or "(any agent)"),
    ]
    # Derived from `source`, not read from the result: `creds._public_view` builds its
    # dicts by naming non-secret fields explicitly so a future field cannot leak by
    # default, and that is worth more than saving this line.
    if result.get("source") == "insecure":
        emitter.warn(
            "this machine has no secret store, so the value is in a mode-600 file: {}. "
            "It is not encrypted — treat the machine as the boundary.".format(
                paths.secrets_dir()
            )
        )
    return result, "\n".join(lines)


def _read_secret_from_stdin(key):
    import getpass
    import sys as _sys

    if _sys.stdin is not None and _sys.stdin.isatty():
        value = getpass.getpass("value for {} (not echoed): ".format(key))
    else:
        value = _sys.stdin.read()
    # A trailing newline from a pipe or a heredoc is the shell's, not the secret's.
    value = value.rstrip("\r\n")
    if not value:
        raise UsageError(
            "no value was given for {}".format(key),
            hint="Pipe it in (`printf %s \"$TOKEN\" | devteam cred set ...`) or run interactively.",
        )
    return value


def cmd_cred_unset(args, emitter):
    project_id = _cred_project_id(args)
    result = creds.unset(args.key, project_id=project_id, forget_value=args.forget_value)
    if not result["removed"]:
        return result, "no reference named {} in this layer".format(result["key"])
    lines = ["removed the reference {}".format(result["key"])]
    if result["value_removed"]:
        lines.append("  value    deleted from the secret store")
    else:
        lines.append("  value    kept — pass --forget-value to delete it too")
    return result, "\n".join(lines)


def cmd_cred_import(args, emitter):
    project_id = _cred_project_id(args)
    result = creds.import_file(args.file, project_id)
    lines = [
        "imported {}".format(args.file),
        "  stored     {} value(s): {}".format(
            len(result["imported"]), ", ".join(result["imported"]) or "(none)"
        ),
        "  references {}".format(paths.credentials_file(project_id)),
        "  quarantine {}".format(result["quarantined_to"] or "(nothing to move)"),
    ]
    if result["non_secret"]:
        lines.append(
            "  kept as plain values (not secrets): {}".format(", ".join(result["non_secret"]))
        )
    if result["insecure"]:
        emitter.warn(
            "{} value(s) went to the last-resort plaintext backend at {} — it is not "
            "encrypted. `devteam cred backends` says what this machine offers.".format(
                len(result["insecure"]), paths.secrets_dir()
            )
        )
    return result, "\n".join(lines)


def cmd_cred_backends(args, emitter):
    payload = secrets_module.describe()
    rows = [
        (name, "yes" if name in payload["available"] else "no", payload["probed"].get(name) or "")
        for name in secrets_module.BACKENDS
    ]
    human = "\n".join(
        [_table(rows, ["BACKEND", "AVAILABLE", "WHY NOT"]), "", "default: {}".format(payload["default"])]
    )
    return payload, human


def cmd_cred_check(args, emitter):
    project_id = _cred_project_id(args)
    findings = creds.check(project_id)
    # `problems` is always present, empty list included. It used to appear only on the
    # findings branch — it exists to trigger `main()`'s exit-1 path, and that check is
    # truthiness-based so `[]` still means success — but a key that comes and goes with
    # the data makes the payload's shape depend on state, and ADR-0011 makes this shape
    # public API. A client doing `payload.problems.length` would have worked until the
    # day everything was fine. Found by the app-facing key-set tests.
    payload = {"project_id": project_id, "findings": findings, "problems": findings}
    if not findings:
        return payload, "every declared credential resolves"
    rows = [
        (f["issue"], f["key"], f["layer"], str(f.get("detail") or ""))
        for f in findings
    ]
    return payload, _table(rows, ["ISSUE", "KEY", "LAYER", "DETAIL"])


def cmd_upgrade(args, emitter):
    if args.apply:
        result = upgrade.apply(args.path, emitter=emitter)
        lines = [
            "upgraded {}".format(result["path"]),
            "  layout      {} -> {}".format(result["from_layout"], result["to_layout"]),
            "  copied      {} file(s) to {}".format(result["copied"], result["destination"]),
            "  quarantine  {}".format(result["quarantined"] or "(nothing to move)"),
            "  pointers    {}, {}".format(result["state_pointer"], result["memory_pointer"]),
            "  exclude     {}".format(result["git_exclude"]),
        ]
        if result["retained"]:
            lines.append(
                "  kept        {} (project-owned, stays committed)".format(
                    ", ".join(result["retained"])
                )
            )
        # `layout` lives in the committed project.json, so an uncommitted upgrade is
        # invisible to a fresh clone — it comes back on layout 1 and asks to upgrade
        # again. Observed in an end-to-end run; nothing else says this.
        lines.append(
            "  commit      {}/project.json — the new layout is committed state; a clone "
            "without it returns to layout {}".format(
                project.PROJECT_DIR, result["from_layout"]
            )
        )
        if result["git_tracked"]:
            lines.append(
                "  git         commit the removal: git rm -r --cached {}".format(
                    " ".join(result["git_tracked"])
                )
            )
        return result, "\n".join(lines)

    result = upgrade.plan(args.path)
    lines = [
        "upgrade plan for {} (nothing changed)".format(result["path"]),
        "  layout {} -> {}".format(result["from_layout"], result["to_layout"]),
    ]
    lines.extend("  - {}".format(action) for action in result["actions"])
    lines.append("  run again with --apply to execute")
    return result, "\n".join(lines)



def cmd_export(args, emitter):
    result = store.export(args.to, include_machine=args.all)
    lines = [
        "exported {} file(s) to {} ({:.1f} MB)".format(
            result["files"], result["archive"], result["bytes"] / (1024 * 1024)
        )
    ]
    if result["portable_only"]:
        lines.append("  portable only — left behind: {}".format(", ".join(result["excluded"])))
        lines.append("  on the other machine: run `devteam bind` in each project")
    else:
        lines.append("  includes this machine's registry and manifests (absolute paths)")
    return result, "\n".join(lines)


def cmd_import(args, emitter):
    result = store.import_archive(args.archive, force=args.force)
    lines = ["imported {} into {}".format(result["archive"], result["data_dir"])]
    if result["previous_kept_at"]:
        lines.append("  previous store kept at {}".format(result["previous_kept_at"]))
    if result["machine_records_kept"]:
        lines.append(
            "  kept this machine's own records: {}".format(
                ", ".join(result["machine_records_kept"])
            )
        )
    lines.append("  next: {}".format(result["next"]))
    return result, "\n".join(lines)


def cmd_uninstall(args, emitter):
    if args.purge and not args.yes:
        raise UsageError(
            "--purge deletes your data store: every project's memory, preferences and "
            "credential references",
            hint="Run `devteam export` first, then repeat with --purge --yes.",
        )
    result = store.uninstall(purge=args.purge)
    lines = ["removed {} path(s)".format(len(result["removed"]))]
    for path in result["removed"]:
        lines.append("  {}".format(path))
    if result["data_kept"]:
        lines.append("  kept your data store at {} (pass --purge to remove it too)".format(result["data_kept"]))
    elif result["purged"]:
        lines.append("  data store purged")
    return result, "\n".join(lines)


def build_parser():
    # `--json` is declared on a parent parser and attached to every subcommand as
    # well as the root, so both `devteam --json path` and `devteam path --json`
    # work. SUPPRESS is what makes that safe: without it the subparser's own
    # default would overwrite a flag passed before the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="emit a single JSON document on stdout",
    )
    # The declaration seam, on every command for the same reason `--json` is: a client
    # should not have to know whether this particular command takes it. SUPPRESS keeps a
    # value passed before the subcommand from being overwritten by the subparser's
    # default, exactly as for `--json`.
    common.add_argument(
        "--client-schemas",
        dest="client_schemas",
        metavar="PATH",
        default=argparse.SUPPRESS,
        help=(
            "path to a JSON file naming the store shapes this caller understands; a "
            "mutating command is refused when any shape is missing or behind "
            "(env: {})".format(compat.CLIENT_SCHEMAS_ENV)
        ),
    )

    parser = _Parser(
        prog=PROGRAM,
        parents=[common],
        description="dev-team-agents — one install, many bound projects",
    )
    sub = parser.add_subparsers(dest="command")

    def leaf(action, name, **kwargs):
        # `add_subparsers` sets parser_class from the parser it is called on, so
        # every subcommand is a _Parser and its errors honour the contract too.
        kwargs.setdefault("parents", [common])
        return action.add_parser(name, **kwargs)

    leaf(sub, "path", help="show resolved store locations").set_defaults(func=cmd_path)
    leaf(sub, "version", help="show core versions").set_defaults(func=cmd_version)

    # No `--path`/`--global`: this describes the *store*, not a project — same
    # discipline as `path`/`catalog`. Creates nothing, including no machine identity.
    compat_parser = leaf(
        sub, "compat", help="what this store requires, or whether a client's shapes can write to it"
    )
    compat_group = compat_parser.add_mutually_exclusive_group()
    compat_group.add_argument("--client", help="JSON object: shape name -> integer schema version")
    compat_group.add_argument("--client-file", help="path to a file containing the same JSON object")
    compat_parser.set_defaults(func=cmd_compat)

    store = leaf(sub, "store", help="manage the versioned core").add_subparsers(dest="store_cmd")
    leaf(store, "list", help="list installed versions").set_defaults(func=cmd_store_list)
    install = leaf(store, "install", help="install a version from a local tree")
    install.add_argument("--from", dest="source", required=True, help="path to a dev-team-agents tree")
    install.add_argument("--version", help="X.Y.Z (default: newest entry in the tree's CHANGELOG)")
    install.add_argument("--force", action="store_true", help="replace the version if present")
    install.add_argument(
        "--activate", action="store_true", default=None, help="make it current after installing"
    )
    install.set_defaults(func=cmd_store_install)
    use = leaf(store, "use", help="set the current version")
    use.add_argument("version")
    use.set_defaults(func=cmd_store_use)
    gc = leaf(store, "gc", help="remove versions nothing references")
    gc.add_argument("--apply", action="store_true", help="actually remove (default: preview)")
    gc.set_defaults(func=cmd_store_gc)

    bind_parser = leaf(sub, "bind", help="bind a project to the store")
    bind_parser.add_argument("path", nargs="?", help="project root (default: current directory)")
    bind_parser.add_argument(
        "--provider",
        action="append",
        choices=providers.ALL_PROVIDERS,
        help="repeatable; default: detect from the project",
    )
    bind_parser.add_argument("--mode", default="auto", choices=bind_module.MODES)
    bind_parser.add_argument("--pin", help="pin this project to a version")
    bind_parser.set_defaults(func=cmd_bind)

    unbind = leaf(sub, "unbind", help="remove bind artifacts, keeping identity and memory")
    unbind.add_argument("path", nargs="?")
    unbind.add_argument("--project-id")
    unbind.add_argument("--keep-artifacts", action="store_true")
    unbind.set_defaults(func=cmd_unbind)

    leaf(sub, "list", help="list bound projects").set_defaults(func=cmd_list)

    sync = leaf(sub, "sync", help="rebuild bind artifacts from the store")
    sync.add_argument("path", nargs="?")
    sync.add_argument("--all", action="store_true", help="every bound project")
    sync.add_argument("--project-id")
    sync.set_defaults(func=cmd_sync)

    pin = leaf(sub, "pin", help="pin this project to a version, or release the pin")
    pin.add_argument("version", nargs="?")
    pin.add_argument("--path")
    pin.add_argument("--release", action="store_true")
    pin.set_defaults(func=cmd_pin)

    update_parser = leaf(sub, "update", help="fetch a release, activate it and sync")
    update_parser.add_argument("--ref", help="tag to install (default: latest release)")
    update_parser.add_argument("--check", action="store_true", help="report only")
    update_parser.add_argument("--no-activate", action="store_true")
    update_parser.add_argument("--no-sync", action="store_true")
    update_parser.add_argument("--force", action="store_true")
    update_parser.add_argument(
        "--sha256", help="expected sha256 of the release archive (out-of-band pinning)"
    )
    update_parser.set_defaults(func=cmd_update)

    migrate_parser = leaf(sub, "migrate", help="convert a v2 vendored install into a bind")
    migrate_parser.add_argument("path", nargs="?")
    migrate_parser.add_argument("--apply", action="store_true", help="execute (default: preview)")
    migrate_parser.add_argument(
        "--provider", action="append", choices=providers.ALL_PROVIDERS
    )
    migrate_parser.add_argument("--mode", default="auto", choices=bind_module.MODES)
    migrate_parser.add_argument("--pin")
    migrate_parser.set_defaults(func=cmd_migrate)

    notif_parser = leaf(
        sub, "notifications", help="the notification queue the hooks write and the app shows"
    ).add_subparsers(dest="notifications_cmd")
    notif_list = leaf(notif_parser, "list", help="live notifications across bound projects")
    notif_list.add_argument("--project", action="append", metavar="PROJECT_ID")
    notif_list.add_argument("--unseen", action="store_true", help="only those not yet acknowledged")
    notif_list.set_defaults(func=cmd_notifications_list)
    notif_ack = leaf(notif_parser, "ack", help="mark notifications seen")
    notif_ack.add_argument("ids", nargs="*", metavar="ID")
    notif_ack.add_argument("--all", action="store_true", help="every live notification")
    notif_ack.add_argument("--project", action="append", metavar="PROJECT_ID")
    notif_ack.set_defaults(func=cmd_notifications_ack)
    notif_watch = leaf(
        notif_parser,
        "watch",
        help="stream new notifications until stdin closes or SIGTERM (JSON Lines with --json)",
    )
    notif_watch.add_argument(
        "--interval", type=_watch_interval, default=1.0, help="seconds between checks (>= 0.01)"
    )
    notif_watch.set_defaults(func=cmd_notifications_watch)

    tasks_parser = leaf(
        sub, "tasks", help="the cross-project task board the hooks feed and the app shows"
    ).add_subparsers(dest="tasks_cmd")

    def tasks_filters(action):
        action.add_argument("--project", action="append", metavar="PROJECT_ID")
        action.add_argument("--since", type=float, metavar="EPOCH", help="drop sessions idle since before this")
        action.add_argument(
            "--stale-after", type=int, default=tasks.DEFAULT_STALE_AFTER, metavar="SECONDS",
            help="an in-progress task older than this is stale (default 3600)",
        )
        action.add_argument(
            "--ended-after", type=int, default=tasks.DEFAULT_ENDED_AFTER, metavar="SECONDS",
            help="a session unseen for this long counts as ended (default 21600)",
        )

    tasks_record = leaf(tasks_parser, "record", help="hook-only: fold a todo-tool payload from stdin into its session")
    tasks_record.add_argument("--project-root", metavar="DIR")
    tasks_record.add_argument("--provider", default="auto", choices=("auto",) + tasks.PROVIDERS)
    tasks_record.set_defaults(func=cmd_tasks_record)
    tasks_mark = leaf(tasks_parser, "mark", help="hook-only: mark the payload's session idle or ended")
    tasks_mark.add_argument("--project-root", metavar="DIR")
    tasks_mark.add_argument("--state", required=True, choices=("idle", "ended"))
    tasks_mark.set_defaults(func=cmd_tasks_mark)
    tasks_list = leaf(tasks_parser, "list", help="every bound project with tasks, with derived state")
    tasks_filters(tasks_list)
    tasks_list.set_defaults(func=cmd_tasks_list)
    tasks_watch = leaf(
        tasks_parser,
        "watch",
        help="stream project snapshots until stdin closes or SIGTERM (JSON Lines with --json)",
    )
    tasks_filters(tasks_watch)
    tasks_watch.add_argument(
        "--interval", type=_watch_interval, default=1.0, help="seconds between checks (>= 0.01)"
    )
    tasks_watch.set_defaults(func=cmd_tasks_watch)

    prefs_parser = leaf(sub, "prefs", help="read and write the preference layers").add_subparsers(
        dest="prefs_cmd"
    )
    prefs_list = leaf(prefs_parser, "list", help="every key, its value and which layer set it")
    prefs_list.add_argument("--path")
    prefs_list.set_defaults(func=cmd_prefs_list)
    prefs_get = leaf(prefs_parser, "get", help="one key")
    prefs_get.add_argument("key")
    prefs_get.add_argument("--path")
    prefs_get.set_defaults(func=cmd_prefs_get)
    prefs_set = leaf(prefs_parser, "set", help="write a key into a layer")
    prefs_set.add_argument("key")
    prefs_set.add_argument("value")
    prefs_set.add_argument("--scope", default="global", choices=prefs.SCOPES)
    prefs_set.add_argument("--path")
    prefs_set.set_defaults(func=cmd_prefs_set)
    prefs_unset = leaf(prefs_parser, "unset", help="drop a key so the layer below applies")
    prefs_unset.add_argument("key")
    prefs_unset.add_argument("--scope", default="global", choices=prefs.SCOPES)
    prefs_unset.add_argument("--path")
    prefs_unset.set_defaults(func=cmd_prefs_unset)

    cred_parser = leaf(
        sub, "cred", help="declare credentials as references; values go to the OS secret store"
    ).add_subparsers(dest="cred_cmd")

    def cred_leaf(name, **kwargs):
        leafp = leaf(cred_parser, name, **kwargs)
        leafp.add_argument("--path", help="project directory (default: the current one)")
        leafp.add_argument(
            "--global",
            dest="global_layer",
            action="store_true",
            help="act on the global layer instead of this project's",
        )
        return leafp

    cred_list = cred_leaf("list", help="every declared credential — references only, never a value")
    cred_list.set_defaults(func=cmd_cred_list)

    cred_get = cred_leaf("get", help="print one value on stdout and nothing else")
    cred_get.add_argument("key")
    cred_get.add_argument("--agent", help="the agent asking, checked against the entry's scope")
    cred_get.set_defaults(func=cmd_cred_get)

    cred_set = cred_leaf("set", help="declare a credential; the value is read from stdin")
    cred_set.add_argument("key")
    cred_set.add_argument("--purpose", required=True, help="why this project needs it")
    cred_set.add_argument("--scope", help="comma-separated agent names allowed to read it")
    cred_set.add_argument(
        "--backend", choices=secrets_module.BACKENDS, help="override the probed default"
    )
    cred_set.set_defaults(func=cmd_cred_set)

    cred_unset = cred_leaf("unset", help="remove a reference; the value stays unless told otherwise")
    cred_unset.add_argument("key")
    cred_unset.add_argument(
        "--forget-value",
        dest="forget_value",
        action="store_true",
        help="also delete the value from the secret store",
    )
    cred_unset.set_defaults(func=cmd_cred_unset)

    cred_import = cred_leaf("import", help="migrate a v2 credentials.local.json into references")
    cred_import.add_argument("file", help="the file to import — never scanned for, always named")
    cred_import.set_defaults(func=cmd_cred_import)

    cred_check = cred_leaf("check", help="report references with no value, or an insecure backend")
    cred_check.set_defaults(func=cmd_cred_check)

    cred_backends = leaf(cred_parser, "backends", help="which secret stores this machine has")
    cred_backends.set_defaults(func=cmd_cred_backends)

    upgrade_parser = leaf(
        sub, "upgrade", help="move this project's memory into the store (asks first)"
    )
    upgrade_parser.add_argument("path", nargs="?")
    upgrade_parser.add_argument("--apply", action="store_true", help="execute (default: preview)")
    upgrade_parser.set_defaults(func=cmd_upgrade)

    export_parser = leaf(sub, "export", help="archive the data store for another machine")
    export_parser.add_argument("--to", help="destination file or directory")
    export_parser.add_argument(
        "--all",
        action="store_true",
        help="also archive this machine's registry and bind manifests (absolute paths)",
    )
    export_parser.set_defaults(func=cmd_export)

    import_parser = leaf(sub, "import", help="restore a data store from an archive")
    import_parser.add_argument("archive")
    import_parser.add_argument("--force", action="store_true", help="replace a populated store")
    import_parser.set_defaults(func=cmd_import)

    uninstall_parser = leaf(sub, "uninstall", help="remove the core; keeps your data store")
    uninstall_parser.add_argument(
        "--purge", action="store_true", help="ALSO delete the data store — memory included"
    )
    uninstall_parser.add_argument(
        "--yes", action="store_true", help="required alongside --purge; there is no undo"
    )
    uninstall_parser.set_defaults(func=cmd_uninstall)

    doctor_parser = leaf(sub, "doctor", help="diagnose the store and this project's bind")
    doctor_parser.add_argument("path", nargs="?")
    doctor_parser.add_argument(
        "--no-project", action="store_true", help="check the store only, ignoring the cwd"
    )
    doctor_parser.add_argument(
        "--reassign-identity",
        action="store_true",
        help="give this project a new project_id (fork case)",
    )
    doctor_parser.set_defaults(func=cmd_doctor)

    # Unlike `store`/`prefs`/`cred`, `catalog` alone is a valid, meaningful call
    # (the summary) — so `func` is set on the parent parser itself, not only on
    # its subcommands. A subparsers action only overwrites `func` on the shared
    # namespace when a subcommand is actually chosen, so this default survives a
    # bare `devteam catalog`.
    catalog_parser = leaf(
        sub, "catalog", help="browse the resolved version's agents, skills and commands (read-only)"
    )
    catalog_parser.add_argument("--path", help="project directory (default: the current one)")
    catalog_parser.set_defaults(func=cmd_catalog)
    catalog_sub = catalog_parser.add_subparsers(dest="catalog_cmd")

    catalog_agents = leaf(catalog_sub, "agents", help="every agent in the resolved version")
    catalog_agents.add_argument("--path", help="project directory (default: the current one)")
    catalog_agents.set_defaults(func=cmd_catalog_agents)

    catalog_skills = leaf(catalog_sub, "skills", help="every skill in the resolved version")
    catalog_skills.add_argument("--path", help="project directory (default: the current one)")
    catalog_skills.set_defaults(func=cmd_catalog_skills)

    catalog_commands = leaf(catalog_sub, "commands", help="every command in the resolved version")
    catalog_commands.add_argument("--path", help="project directory (default: the current one)")
    catalog_commands.set_defaults(func=cmd_catalog_commands)

    catalog_show = leaf(catalog_sub, "show", help="one entry's metadata and its body")
    catalog_show.add_argument("name", help="a bare agent, skill or command name")
    catalog_show.add_argument("--path", help="project directory (default: the current one)")
    catalog_show.set_defaults(func=cmd_catalog_show)

    # The user-level skill directories each provider reads (ADR-0017) — outside every
    # project and outside the store. No `--path`: nothing here depends on a project.
    skills_parser = leaf(
        sub, "skills", help="list, show, install and remove the providers' global skills"
    ).add_subparsers(dest="skills_cmd")
    provider_choices = global_skills.PROVIDERS + ("all",)

    skills_list = leaf(skills_parser, "list", help="every skill in the global skill directories")
    skills_list.add_argument("--provider", default="all", choices=provider_choices)
    skills_list.set_defaults(func=cmd_skills_list)

    skills_show = leaf(skills_parser, "show", help="one global skill's metadata, body and files")
    skills_show.add_argument("name")
    skills_show.add_argument("--root", help="the root id, when the name exists in more than one")
    skills_show.set_defaults(func=cmd_skills_show)

    skills_install = leaf(skills_parser, "install", help="install a skill from a directory or a .zip")
    skills_install.add_argument(
        "--source", required=True, help="a directory holding SKILL.md, or a .zip/.skill archive"
    )
    skills_install.add_argument(
        "--provider",
        action="append",
        choices=provider_choices,
        help="repeatable; each provider installs into its own target root (default: all)",
    )
    skills_install.add_argument("--root", action="append", help="repeatable; install into this root id")
    skills_install.add_argument(
        "--replace", action="store_true", help="move an existing skill of the same name to quarantine"
    )
    skills_install.add_argument(
        "--link", action="store_true", help="symlink a directory source instead of copying it"
    )
    skills_install.set_defaults(func=cmd_skills_install)

    skills_remove = leaf(
        skills_parser, "remove", help="remove a global skill (a directory goes to quarantine)"
    )
    skills_remove.add_argument("name")
    skills_remove.add_argument("--root", help="the root id, when the name exists in more than one")
    skills_remove.set_defaults(func=cmd_skills_remove)

    return parser


#: Commands whose `--json` stdout is JSON Lines rather than one document. Every line,
#: a failure included, is then one compact object (`Emitter.lines`).
STREAMING_COMMANDS = frozenset({("notifications", "watch"), ("tasks", "watch")})


def _looks_streaming(raw):
    """Whether argv names a streaming command, for failures raised before parsing ends."""
    words = [word for word in raw if not word.startswith("-")]
    return any(tuple(words[i : i + 2]) in STREAMING_COMMANDS for i in range(len(words)))


def resolved_command_path(parser, args):
    """The leaf path the parse resolved to, e.g. ``("cred", "get")``.

    Walked from the real parser rather than read off a hardcoded set of dest names
    (`command`, `store_cmd`, `cred_cmd`, …): a new command group would otherwise resolve
    to its parent path and be gated as the wrong thing, silently. Same discipline as
    `tests/test_json_contract.py`'s discovery walk, and the same path tuples, so the
    classification in `compat.py` is keyed by what both produce.

    Returns a group path (``("store",)``) when no subcommand was chosen; `main` only
    gates a path that actually resolved to a handler.
    """
    path = []
    node = parser
    while True:
        action = next(
            (a for a in node._actions if isinstance(a, argparse._SubParsersAction)), None
        )
        if action is None:
            break
        chosen = getattr(args, action.dest, None)
        if not chosen or chosen not in action.choices:
            break
        path.append(chosen)
        node = action.choices[chosen]
    return tuple(path)


def _ensure_utf8_stdio():
    """Force ``sys.stdout``/``sys.stderr`` to UTF-8, if the interpreter allows it.

    Every human-facing message in this package is an ordinary Python string that
    may contain non-ASCII punctuation — an em dash, mainly (`grep -rn "—"` finds
    dozens, in hints and human output, not just comments). On Linux and macOS
    that is never a problem: the stream is UTF-8 by default. On Windows it is
    only UTF-8 when talking to a real console; the moment stdout/stderr are
    redirected to a pipe or a file — exactly what every subprocess-driven test,
    and every caller piping this CLI's output, does — Python falls back to
    ``locale.getpreferredencoding()``, commonly ``cp1252``, and a bare em dash
    raises ``UnicodeEncodeError`` or round-trips as a different byte than a
    UTF-8-decoding caller expects. ``reconfigure`` exists on every stream this
    matters for (Python 3.7+'s ``TextIOWrapper``) and is a no-op cost-wise; a
    stream that lacks it (already replaced by a test double) is left alone.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass


def main(argv=None, stdout=None, stderr=None):
    # The emitter is built before parsing so a parse error can still honour
    # `--json`; argv is scanned directly because argparse has not run yet.
    if stdout is None and stderr is None:
        # Only when both are about to default to the real `sys.stdout`/`sys.stderr`
        # — a caller that supplied its own streams (every in-process test) gets
        # exactly what it passed in, untouched.
        _ensure_utf8_stdio()
    argv_list = list(argv) if argv is not None else None
    raw = argv_list if argv_list is not None else sys.argv[1:]
    emitter = Emitter(as_json="--json" in raw, stdout=stdout, stderr=stderr)
    # Before parsing, too: a bad `--interval` is a failure of the streaming command.
    emitter.lines = _looks_streaming(raw)

    try:
        parser = build_parser()
        args = parser.parse_args(argv_list)
    except _HelpRequested:
        return 0
    except DevteamError as exc:
        return emitter.fail(exc)

    emitter.as_json = getattr(args, "json", emitter.as_json)

    # The write gate, and it runs HERE — before `adopt_machine_layout()`, which is
    # itself a store mutation, and before any handler. A refusal must leave the store
    # byte-identical, so nothing that writes may run ahead of it.
    #
    # The declaration is resolved (and therefore validated) whenever one is present,
    # even for a read-only command: a client whose declaration file is corrupt has a
    # broken installation, and reporting that on its first call rather than on its first
    # *write* removes the window where the gate silently is not there. The refusal
    # itself applies only to a command that writes.
    command_path = resolved_command_path(parser, args)
    emitter.lines = command_path in STREAMING_COMMANDS
    try:
        declaration = compat.client_declaration(
            getattr(args, "client_schemas", None), os.environ
        )
        # Computed here as well as inside `compat.gate` because the relocation decision
        # below needs the comparison for a *read-only* command, where the gate
        # deliberately does not raise. Both call `compat.unsupported_by` — the rule still
        # has one definition; only the pure function runs twice.
        unsupported = compat.unsupported_by(declaration.schemas) if declaration else {}
        # `hasattr(args, "func")` keeps a group invoked with no subcommand — `devteam
        # store`, `prefs`, `cred` — out of the gate. Its path resolves to the group, which
        # is in neither classification table, so `is_mutating` would fail closed and turn
        # a "needs a subcommand" usage error (exit 2) into a conflict (exit 4) about a
        # command the caller never asked for.
        if declaration is not None and hasattr(args, "func"):
            compat.gate(command_path, declaration)
    except DevteamError as exc:
        return emitter.fail(exc)
    except Exception as exc:  # noqa: BLE001 - the contract outranks a clean traceback
        # The same net the handler call below carries, for the same reason and because
        # this block parses caller-supplied text: `Path.read_text` raises
        # `UnicodeDecodeError` and `json.loads` raises `RecursionError`, neither of which
        # is an `OSError` or a `JSONDecodeError`. Both are converted to `UsageError` in
        # `compat` now; this is what keeps the *next* one from reaching the shell as a
        # traceback with an empty stdout under `--json`.
        return emitter.fail(
            EnvError(
                "unexpected {} while reading the client declaration: {}".format(
                    type(exc).__name__, exc
                ),
                hint="This is a bug in dev-team-agents; please report it.",
            )
        )

    # The store's own shape is brought up to date before any command reads it: a
    # command that found registry.json at the pre-split path would report every
    # bound project as unbound. Idempotent, and a no-op for an already-split store.
    #
    # **Not on behalf of an incompatible client.** The relocation writes `registry` and
    # `bind_manifest`; a client that declared it cannot read those shapes must not have
    # them rewritten because it asked a read-only question. A read-only command then
    # answers against the layout actually on disk — which every one of them does
    # correctly except those in `compat.NEEDS_MACHINE_LAYOUT`, which are refused rather
    # than allowed to answer wrong.
    adopted = None
    if unsupported and store.machine_layout_pending():
        if command_path in compat.NEEDS_MACHINE_LAYOUT:
            return emitter.fail(
                compat.migration_required(command_path, declaration, unsupported)
            )
    else:
        try:
            adopted = store.adopt_machine_layout()
        except (OSError, DevteamError) as exc:
            return emitter.fail(
                EnvError(
                    "cannot bring the data store up to the current layout: {}".format(exc),
                    hint="Check permissions on the data store, then retry.",
                )
            )
    if adopted and (adopted["moved"] or adopted["quarantined"]):
        emitter.warn(
            "moved {} machine-local record(s) into {}; repointed {} project(s)".format(
                len(adopted["moved"]), paths.machine_dir(), len(adopted["repointed"])
            )
        )

    if not getattr(args, "command", None) or not hasattr(args, "func"):
        if getattr(args, "command", None) == "store":
            return emitter.fail(UsageError("store needs a subcommand: list, install, use, gc"))
        if getattr(args, "command", None) == "prefs":
            return emitter.fail(UsageError("prefs needs a subcommand: list, get, set, unset"))
        if getattr(args, "command", None) == "cred":
            return emitter.fail(
                UsageError("cred needs a subcommand: list, get, set, unset, import, check, backends")
            )
        if getattr(args, "command", None) == "notifications":
            return emitter.fail(UsageError("notifications needs a subcommand: list, ack, watch"))
        if getattr(args, "command", None) == "tasks":
            return emitter.fail(UsageError("tasks needs a subcommand: record, mark, list, watch"))
        if getattr(args, "command", None) == "skills":
            return emitter.fail(UsageError("skills needs a subcommand: list, show, install, remove"))
        return emitter.fail(UsageError("no command given — run `devteam --help`"))

    try:
        payload, human = args.func(args, emitter)
    except DevteamError as exc:
        return emitter.fail(exc)
    except KeyboardInterrupt:
        emitter.warn("interrupted")
        return 130
    except OSError as exc:
        return emitter.fail(
            EnvError(
                "{}: {}".format(type(exc).__name__, exc),
                hint="Check permissions and that every path involved is reachable.",
            )
        )
    except Exception as exc:  # noqa: BLE001 - the contract outranks a clean traceback
        # An unexpected exception used to reach the shell as a traceback with an
        # empty stdout under --json, which a client cannot tell from a findings
        # result. One document always goes out.
        return emitter.fail(
            EnvError(
                "unexpected {}: {}".format(type(exc).__name__, exc),
                hint="This is a bug in dev-team-agents; please report it.",
            )
        )

    ok = True
    exit_code = 0
    if args.command == "doctor":
        # `1` is "ran and reported a problem it did not fix" — a WARN finding is
        # exactly that, and returning 0 made every recoverable problem look like
        # success to a client reading only the exit code.
        if payload.get("status") in ("warn", "fail"):
            ok = False
            exit_code = 1
    elif args.command == "compat":
        # `1`, not `2` and not `3`: an incompatible client is a real, well-formed
        # answer to a well-formed question — the store and the client both parsed
        # fine, there is just a shape neither side can paper over. That is exactly
        # what exit 1 means elsewhere in this CLI ("ran and reported a problem it
        # did not fix"), so a caller already branching on `$?` for `cred check` or
        # `sync` gets the same signal here instead of a third meaning to learn. `2`
        # is reserved for a malformed question (bad JSON, wrong type) — those raise
        # `UsageError` above and never reach this branch. A bare `devteam compat`
        # with no `--client` has `may_write is None` and stays a clean `0`: nothing
        # was asked, so nothing can be incompatible.
        if payload.get("may_write") is False:
            ok = False
            exit_code = 1
    elif payload.get("problems"):
        # Applies to sync AND update: an update that activates a version but fails
        # to sync N projects is not a success.
        ok = False
        exit_code = 1

    if emitter.streamed:
        # A streaming command's stdout is JSON Lines and already carried its last
        # event (`end`); a trailing indented document would be unparseable there.
        return exit_code

    payload = dict(payload)
    # `warn` only reaches stderr, and ADR-0011 makes the desktop app a client of this
    # CLI: a store mutation it cannot observe in the document is a contract gap.
    # `adopted` is None when the relocation was skipped because an incompatible client
    # asked a read-only question — nothing moved, so there is nothing to report.
    if adopted and (adopted["moved"] or adopted["quarantined"]):
        payload["store_relocation"] = adopted
    payload["ok"] = ok
    emitter.emit(payload, human)
    return exit_code
