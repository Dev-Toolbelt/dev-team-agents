"""Diagnose the store and a project's bind, and reconcile identity.

Findings are reported; only two repairs happen, and both are additive: pointing
an existing registry entry at a directory that moved, and re-binding artifacts
that are missing or point at the wrong version. Nothing here deletes.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import bind as bind_module
from .errors import EnvError
from . import hooks, paths, project, registry, versions

OK = "ok"
WARN = "warn"
FAIL = "fail"


def _points_into(target, version):
    """True when a link target lives inside ``versions/<version>/``.

    A substring test (`version not in target`) false-negatives whenever the store
    path itself contains the version string, so compare by path components.
    """
    expected_root = paths.version_dir(version)
    try:
        resolved = Path(os.path.realpath(str(target)))
        root = Path(os.path.realpath(str(expected_root)))
        resolved.relative_to(root)
        return True
    except (ValueError, OSError):
        return False


def _finding(level, category, message, hint=None):
    item = {"level": level, "category": category, "message": message}
    if hint:
        item["hint"] = hint
    return item


def check_store():
    findings = []
    core = paths.core_dir()
    if not core.is_dir():
        findings.append(
            _finding(
                FAIL,
                "store",
                "core directory does not exist: {}".format(core),
                "Run `devteam store install --from <tree>`.",
            )
        )
        return findings

    installed = versions.installed()
    if not installed:
        findings.append(
            _finding(FAIL, "store", "no version is installed in {}".format(paths.versions_dir()))
        )
    active = versions.current()
    if not active:
        findings.append(
            _finding(
                FAIL,
                "store",
                "no active version: {} is missing".format(paths.current_file()),
                "Run `devteam store use <version>`.",
            )
        )
    elif active not in installed:
        findings.append(
            _finding(
                FAIL,
                "store",
                "current points at {}, which is not installed".format(active),
                "Run `devteam store use <version>` with one of: {}".format(", ".join(installed)),
            )
        )
    else:
        findings.append(_finding(OK, "store", "current = {}".format(active)))

    incomplete = [v for v in installed if not (paths.version_dir(v) / "VERSION").is_file()]
    for version in incomplete:
        findings.append(
            _finding(
                WARN,
                "store",
                "version {} has no VERSION marker — it may be a partial copy".format(version),
            )
        )
    return findings


def check_registry():
    findings = []
    entries = registry.entries()
    if not entries:
        findings.append(_finding(OK, "registry", "no projects bound yet"))
        return findings, entries
    for project_id, entry in sorted(entries.items()):
        root = Path(entry.get("path", ""))
        if not root.is_dir():
            findings.append(
                _finding(
                    WARN,
                    "registry",
                    "bound path is gone: {} ({})".format(root, project_id),
                    "Run `devteam doctor` from the project's new location to reconcile it.",
                )
            )
            continue
        data = project.load(root)
        if data is None:
            findings.append(
                _finding(
                    WARN,
                    "registry",
                    "{} has no project.json but is registered".format(root),
                    "Run `devteam bind` there to recreate it.",
                )
            )
        elif data["project_id"] != project_id:
            findings.append(
                _finding(
                    FAIL,
                    "registry",
                    "{} carries identity {} but is registered as {}".format(
                        root, data["project_id"], project_id
                    ),
                    "Run `devteam bind` there, then `devteam unbind --project-id {}`.".format(
                        project_id
                    ),
                )
            )
    return findings, entries


def check_project(project_root):
    """Bind health for one project, plus the reconciliation decision."""
    findings = []
    actions = []
    root = Path(project_root)
    if not root.is_dir():
        raise EnvError(
            "no such directory: {}".format(root),
            hint="Pass a path that exists, or run doctor with --no-project.",
        )
    data = project.load(root)
    if data is None:
        findings.append(
            _finding(WARN, "project", "{} is not a bound project".format(root), "Run `devteam bind`.")
        )
        return findings, actions

    project_id = data["project_id"]
    entry = registry.get(project_id)
    if entry is None:
        findings.append(
            _finding(
                WARN,
                "project",
                "identity {} is not in the registry".format(project_id),
                "Run `devteam bind` here.",
            )
        )
        return findings, actions

    registered = Path(entry.get("path", ""))
    known_paths = {registered.resolve()} | {
        Path(w).resolve() for w in entry.get("worktrees", [])
    }
    if root.resolve() not in known_paths:
        other = project.load(registered) if registered.is_dir() else None
        if (
            other is not None
            and other.get("project_id") == project_id
            and bind_module._same_git_repository(registered, root)
        ):
            findings.append(
                _finding(
                    OK,
                    "identity",
                    "{} is a linked worktree of the bound checkout at {}".format(root, registered),
                )
            )
        elif other is not None and other.get("project_id") == project_id:
            findings.append(
                _finding(
                    FAIL,
                    "identity",
                    "identity {} exists at two paths: {} and {}".format(
                        project_id, registered, root
                    ),
                    "A fork inherited the identity. Run `devteam doctor --reassign-identity` "
                    "in the copy that should get a new one. Nothing was merged.",
                )
            )
        else:
            previous, now = registry.relocate(project_id, root)
            actions.append({"action": "relocated", "from": previous, "to": now})
            findings.append(
                _finding(OK, "identity", "registry re-pointed from {} to {}".format(previous, now))
            )

    manifest = bind_module.read_manifest(project_id)
    try:
        expected_version = versions.resolve(entry.get("pin"))
    except EnvError as exc:
        # The store being broken is the case doctor exists for. Aborting here with
        # exit 3 threw away every finding already collected, including the store
        # FAIL that explains the problem.
        findings.append(
            _finding(
                FAIL,
                "bind",
                "cannot resolve this project's version: {}".format(exc.message),
                exc.hint,
            )
        )
        return findings, actions

    missing = []
    broken = []
    wrong_version = []
    for item in manifest.get("artifacts", []):
        rel = item.get("path")
        if not rel:
            findings.append(
                _finding(FAIL, "bind", "manifest has an artifact entry with no path")
            )
            continue
        candidate = root / rel
        if candidate.is_symlink() and not candidate.exists():
            broken.append(rel)
            continue
        if not candidate.exists():
            missing.append(rel)
            continue
        if item.get("kind") == "link" and candidate.is_symlink():
            target = Path(os.readlink(str(candidate)))
            if not _points_into(target, expected_version):
                wrong_version.append(rel)

    # A copy-mode artifact carries no target to inspect, so the manifest's own
    # version is the only record — and `copy` is the mode Windows uses, where
    # drift went completely undetected before.
    if manifest.get("version") and manifest["version"] != expected_version:
        findings.append(
            _finding(
                WARN,
                "bind",
                "artifacts were built from {} but this project resolves to {}".format(
                    manifest["version"], expected_version
                ),
                "Run `devteam sync`.",
            )
        )
    if broken:
        findings.append(
            _finding(
                WARN,
                "bind",
                "{} artifact(s) are broken symlinks".format(len(broken)),
                "Run `devteam sync`.",
            )
        )
    if missing:
        findings.append(
            _finding(
                WARN,
                "bind",
                "{} artifact(s) missing".format(len(missing)),
                "Run `devteam sync`.",
            )
        )
    if wrong_version:
        findings.append(
            _finding(
                WARN,
                "bind",
                "{} artifact(s) point at a version other than {}".format(
                    len(wrong_version), expected_version
                ),
                "Run `devteam sync`.",
            )
        )
    if not missing and not wrong_version and manifest.get("artifacts"):
        findings.append(
            _finding(
                OK,
                "bind",
                "{} artifact(s) resolve to {}".format(len(manifest["artifacts"]), expected_version),
            )
        )
    settings = root / hooks.SETTINGS_FILE
    if manifest.get("mode") != "vendored":
        registered = hooks.registered_events(root)
        expected_events = [event for event, _ in hooks.EVENTS]
        absent = [event for event in expected_events if event not in registered]
        if absent:
            findings.append(
                _finding(
                    WARN,
                    "hooks",
                    "{} not registered in {}".format(", ".join(absent), hooks.SETTINGS_FILE),
                    "Run `devteam sync` — without them the Stop, SessionStart and "
                    "PreCompact enforcement does not run in this project.",
                )
            )
        elif settings.is_file():
            findings.append(
                _finding(OK, "hooks", "4 dispatchers registered in {}".format(hooks.SETTINGS_FILE))
            )

    if manifest.get("mode") and entry.get("mode") and manifest["mode"] != entry["mode"]:
        findings.append(
            _finding(
                WARN,
                "bind",
                "registry says mode={} but the last bind used {}".format(
                    entry["mode"], manifest["mode"]
                ),
                "Run `devteam sync`.",
            )
        )
    return findings, actions


def run(project_root=None, reassign_identity=False):
    findings = list(check_store())
    registry_findings, _ = check_registry()
    findings.extend(registry_findings)

    actions = []
    if project_root is not None:
        root = project.resolve_root(project_root)
        if reassign_identity:
            previous, new = project.reassign_identity(root)
            actions.append({"action": "reassigned_identity", "from": previous, "to": new})
            findings.append(
                _finding(
                    OK,
                    "identity",
                    "identity reassigned {} -> {} (memory for the old id was left untouched)".format(
                        previous, new
                    ),
                )
            )
        project_findings, project_actions = check_project(root)
        findings.extend(project_findings)
        actions.extend(project_actions)

    worst = OK
    for item in findings:
        if item["level"] == FAIL:
            worst = FAIL
            break
        if item["level"] == WARN:
            worst = WARN
    return {"status": worst, "findings": findings, "actions": actions}
