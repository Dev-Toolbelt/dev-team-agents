"""Argument parsing and the subcommand table.

Every handler returns ``(payload, human)``: the JSON body and a terminal
rendering of the same facts. Nothing prints directly, so the ``--json`` contract
cannot be broken by a stray ``print``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import bind as bind_module
from . import doctor, migrate, paths, project, providers, registry, update, versions
from .errors import DevteamError, UsageError
from .output import Emitter

PROGRAM = "devteam"


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
    )
    return result, human


def cmd_unbind(args, emitter):
    result = bind_module.unbind(
        args.path, project_id=args.project_id, keep_artifacts=args.keep_artifacts
    )
    human = "unbound {}\n  removed {} artifact(s)\n  kept    {}".format(
        result["path"], len(result["removed"]), ", ".join(result["kept"])
    )
    return result, human


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
        emitter=emitter,
    )
    human = "{} {} | current: {} | synced {} project(s)".format(
        "installed" if result["installed_now"] else "already present:",
        result["version"],
        result["activated"] or versions.current(),
        result["synced"],
    )
    return result, human


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

    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        parents=[common],
        description="dev-team-agents — one install, many bound projects",
    )
    sub = parser.add_subparsers(dest="command")

    def leaf(action, name, **kwargs):
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
    parser = build_parser()
    args = parser.parse_args(argv)
    emitter = Emitter(as_json=getattr(args, "json", False), stdout=stdout, stderr=stderr)

    if not getattr(args, "command", None) or not hasattr(args, "func"):
        if getattr(args, "command", None) == "store":
            emitter.fail(UsageError("store needs a subcommand: list, install, use, gc"))
            return 2
        emitter.fail(UsageError("no command given — run `devteam --help`"))
        return 2

    try:
        payload, human = args.func(args, emitter)
    except DevteamError as exc:
        return emitter.fail(exc)
    except KeyboardInterrupt:
        emitter.warn("interrupted")
        return 130

    emitter.emit(payload, human)
    if args.command == "doctor" and payload.get("status") == "fail":
        return 1
    if args.command == "sync" and payload.get("problems"):
        return 1
    return 0
