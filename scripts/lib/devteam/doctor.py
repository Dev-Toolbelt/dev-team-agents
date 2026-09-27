"""Diagnose the store and a project's bind, and reconcile identity.

Findings are reported; only two repairs happen, and both are additive: pointing
an existing registry entry at a directory that moved, and re-binding artifacts
that are missing or point at the wrong version. Nothing here deletes.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import bind as bind_module
from . import paths, project, registry, versions

OK = "ok"
WARN = "warn"
FAIL = "fail"


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
    if registered.resolve() != root.resolve():
        other = project.load(registered) if registered.is_dir() else None
        if other is not None and other.get("project_id") == project_id:
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
    expected_version = versions.resolve(entry.get("pin"))
    missing = []
    wrong_version = []
    for item in manifest.get("artifacts", []):
        candidate = root / item.get("path", "")
        if not (candidate.exists() or candidate.is_symlink()):
            missing.append(item["path"])
            continue
        if item.get("kind") == "link" and candidate.is_symlink():
            target = os.readlink(str(candidate))
            if expected_version not in target:
                wrong_version.append(item["path"])
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
