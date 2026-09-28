"""Argument parsing and the subcommand table.

Every handler returns ``(payload, human)``: the JSON body and a terminal
rendering of the same facts. Nothing prints directly, so the ``--json`` contract
cannot be broken by a stray ``print``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import bind as bind_module
from . import doctor, migrate, paths, prefs, project, providers, registry, store, update, upgrade, versions
from .errors import DevteamError, EnvError, UsageError
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
    payload = {
        "current": versions.current(),
        "installed": versions.installed(),
        "core": str(paths.core_dir()),
    }
    human = "current: {}\ninstalled: {}".format(
        payload["current"] or "(none)", ", ".join(payload["installed"]) or "(none)"
    )
    return payload, human


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
    )
    return result, human


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
        if result["git_tracked"]:
            lines.append(
                "  git        {} path(s) still tracked — commit their removal:".format(
                    len(result["git_tracked"])
                )
            )
            lines.append("               git rm -r --cached {}".format(" ".join(result["git_tracked"])))
        if result["unrecognised"]:
            lines.append("  left alone {}".format(", ".join(result["unrecognised"])))
        return result, "\n".join(lines)

    result = migrate.plan(args.path, provider_names=args.provider, mode=args.mode)
    lines = ["migration plan for {} (nothing changed)".format(result["path"])]
    lines.extend("  - {}".format(action) for action in result["actions"])
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


def cmd_upgrade(args, emitter):
    if args.apply:
        result = upgrade.apply(args.path, emitter=emitter)
        lines = [
            "upgraded {}".format(result["path"]),
            "  layout      {} -> {}".format(result["from_layout"], result["to_layout"]),
            "  copied      {} file(s) to {}".format(result["copied"], result["destination"]),
            "  quarantine  {}".format(result["quarantined"] or "(nothing to move)"),
            "  pointer     {}".format(result["state_pointer"]),
        ]
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

    return parser


def main(argv=None, stdout=None, stderr=None):
    # The emitter is built before parsing so a parse error can still honour
    # `--json`; argv is scanned directly because argparse has not run yet.
    argv_list = list(argv) if argv is not None else None
    raw = argv_list if argv_list is not None else __import__("sys").argv[1:]
    emitter = Emitter(as_json="--json" in raw, stdout=stdout, stderr=stderr)

    try:
        parser = build_parser()
        args = parser.parse_args(argv_list)
    except _HelpRequested:
        return 0
    except DevteamError as exc:
        return emitter.fail(exc)

    emitter.as_json = getattr(args, "json", emitter.as_json)

    # The store's own shape is brought up to date before any command reads it: a
    # command that found registry.json at the pre-split path would report every
    # bound project as unbound. Idempotent, and a no-op for an already-split store.
    try:
        adopted = store.adopt_machine_layout()
    except (OSError, DevteamError) as exc:
        return emitter.fail(
            EnvError(
                "cannot bring the data store up to the current layout: {}".format(exc),
                hint="Check permissions on the data store, then retry.",
            )
        )
    if adopted["moved"] or adopted["quarantined"]:
        emitter.warn(
            "moved {} machine-local record(s) into {}".format(
                len(adopted["moved"]), paths.machine_dir()
            )
        )

    if not getattr(args, "command", None) or not hasattr(args, "func"):
        if getattr(args, "command", None) == "store":
            return emitter.fail(UsageError("store needs a subcommand: list, install, use, gc"))
        if getattr(args, "command", None) == "prefs":
            return emitter.fail(UsageError("prefs needs a subcommand: list, get, set, unset"))
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
    elif payload.get("problems"):
        # Applies to sync AND update: an update that activates a version but fails
        # to sync N projects is not a success.
        ok = False
        exit_code = 1

    payload = dict(payload)
    payload["ok"] = ok
    emitter.emit(payload, human)
    return exit_code
