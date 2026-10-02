"""Diagnose the store and a project's bind, and reconcile identity.

Findings are reported; only two repairs happen, and both are additive: pointing
an existing registry entry at a directory that moved, and re-binding artifacts
that are missing or point at the wrong version. Nothing here deletes.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import bind as bind_module
from .errors import ConflictError, EnvError
from . import creds, credentials_local, hooks, migrate, paths, prefs, project, registry, versions
from . import providers as providers_module

OK = "ok"
WARN = "warn"
FAIL = "fail"


def _points_into(target, version):
    r"""True when a link target lives inside ``versions/<version>/``.

    A substring test (`version not in target`) false-negatives whenever the store
    path itself contains the version string, so compare by path components.

    ``paths.realpath_normalized`` rather than a bare ``os.path.realpath`` matters
    on Windows: ``target`` is read back with ``os.readlink``, which always carries
    the ``\\?\`` extended prefix, while ``expected_root`` is a plain path that
    does not reliably pick the same prefix up from ``realpath`` — comparing the
    two unnormalized reports a perfectly healthy bind as pointing at the wrong
    version.
    """
    expected_root = paths.version_dir(version)
    try:
        resolved = paths.realpath_normalized(target)
        root = paths.realpath_normalized(expected_root)
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


def check_machine():
    """Report the machine identity and where its records live (ADR-0013)."""
    # `create=False`: doctor reports, it does not mint an identity as a side effect
    # of being run — otherwise a second `doctor` sees a different world than the first.
    current = paths.machine_id(create=False)
    if current is None:
        findings = [
            _finding(
                OK,
                "machine",
                "no machine identity recorded yet — the first command that writes to "
                "the store will create one",
            )
        ]
    else:
        findings = [
            _finding(
                OK,
                "machine",
                "machine {} on host {} — machine-local records in {}".format(
                    current, paths.machine_host(), paths.machine_dir(current)
                ),
            )
        ]
    other = [
        entry.name
        for entry in sorted(paths.machines_dir().glob("*"))
        if entry.is_dir() and entry.name != current
    ]
    if other:
        # Inert is not the same as expected. A second record set means the store was
        # restored from elsewhere, or is reachable from more than one machine — a
        # shared $DEVTEAM_HOME, a roaming profile, a restored image, a VM clone. None
        # of it is read, and none of it is touched, but it is worth looking at.
        findings.append(
            _finding(
                WARN,
                "machine",
                "{} other machine record set(s) in {}: {}".format(
                    len(other), paths.machines_dir(), ", ".join(other)
                ),
                "Nothing reads them. If this store is shared between machines or was "
                "restored from another one, expect each machine to keep its own set.",
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
                    "Run `devteam bind` there (or `devteam migrate` over a v2 tree) — it restores "
                    "project.json with this registered project_id.",
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


#: `creds.check` returns a stable issue code; the sentence and the severity belong to
#: whoever presents it. A missing value is a FAIL because the credential cannot be used
#: at all; an insecure backend is a WARN because it works and the user may have no
#: alternative on their platform — ADR-0010 asks for it to be loud, not fatal.
_CREDENTIAL_ISSUES = {
    "missing-value": (
        FAIL,
        "the reference resolves to no value in the {source} store",
        "Re-store it with `devteam cred set {key}`, or drop the reference with "
        "`devteam cred unset {key}`.",
    ),
    "insecure-backend": (
        WARN,
        "the value is in the last-resort plaintext store, not encrypted",
        "Run `devteam cred backends` to see what this machine offers.",
    ),
    "unknown-source": (
        FAIL,
        "declares a source this build does not know: {detail}",
        "Update dev-team-agents, or fix the entry by hand.",
    ),
    "backend-error": (
        FAIL,
        "the secret store could not be read: {detail}",
        None,
    ),
}


def _credential_finding(finding):
    level, template, hint = _CREDENTIAL_ISSUES.get(
        finding["issue"], (WARN, "unrecognised issue: {issue}", None)
    )
    fields = {
        "key": finding.get("key", "-"),
        "layer": finding.get("layer", "-"),
        "detail": finding.get("detail", ""),
        "issue": finding["issue"],
        "source": finding.get("detail") or "configured",
    }
    return _finding(
        level,
        "credentials",
        "{} ({} layer): {}".format(fields["key"], fields["layer"], template.format(**fields)),
        hint.format(**fields) if hint else None,
    )


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
        # `devteam bind` is the right advice for a directory that never had the
        # framework on it — but not for one carrying a shape from before this
        # command existed. Both older shapes are adapted by a dedicated command,
        # never by `bind`, which does not know how to fold either one in.
        legacy = migrate.detect(root)
        if legacy["is_v2"]:
            findings.append(
                _finding(
                    WARN,
                    "project",
                    "{} is a v2 vendored install ({} under {}/), not a v3 bind".format(
                        root, ", ".join(legacy["vendored_trees"]), project.PROJECT_DIR
                    ),
                    "Run `devteam migrate` — it shows a plan first and moves the old "
                    "tree into a dated quarantine rather than deleting it.",
                )
            )
        elif migrate.pre_root_install(root):
            # The same words `bind` and `migrate` refuse with, so the three never
            # disagree about what to run.
            refusal = migrate.pre_root_error(root)
            findings.append(_finding(WARN, "project", refusal.message, refusal.hint))
        else:
            findings.append(
                _finding(
                    WARN, "project", "{} is not a bound project".format(root), "Run `devteam bind`."
                )
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

    if project.upgrade_available(root):
        findings.append(
            _finding(
                WARN,
                "layout",
                "project is on layout {} (current is {}) — memory still lives in {}/{}".format(
                    project.layout(root),
                    project.CURRENT_LAYOUT,
                    project.PROJECT_DIR,
                    project.LEGACY_MEMORY_DIR,
                ),
                "Run `devteam upgrade` to move it into the store. Nothing moves until you do.",
            )
        )
    else:
        findings.append(_finding(OK, "layout", "layout {}".format(project.layout(root))))

    # Both pointers, and repaired rather than only reported: a pointer is a
    # regenerated projection that every bind and sync rewrites, so rewriting it here is
    # the same additive repair doctor already performs on a moved registry entry. The
    # alternative — reporting and waiting — is what made a stale `state-dir` hand every
    # hook an empty `state.json` until someone happened to run `devteam sync`.
    expected = (
        (project.STATE_DIR_POINTER, str(project.state_dir(root, project_id))),
        (project.MEMORY_DIR_POINTER, str(project.memory_dir(root, project_id))),
    )
    stale = []
    for name, want in expected:
        pointer = root / project.PROJECT_DIR / name
        if not pointer.is_file():
            stale.append((name, "missing"))
        elif pointer.read_text(encoding="utf-8").strip() != want:
            stale.append((name, "naming a directory this layout does not resolve to"))
    if stale:
        try:
            project.write_pointers(root, project_id)
        except (EnvError, OSError) as exc:
            findings.append(
                _finding(
                    FAIL,
                    "layout",
                    "cannot rewrite the directory pointers: {}".format(exc),
                    "Check permissions on {}/.".format(project.PROJECT_DIR),
                )
            )
        else:
            for name, why in stale:
                actions.append({"action": "repointed", "pointer": name})
                findings.append(
                    _finding(
                        OK,
                        "layout",
                        "pointer {} was {}; rewritten".format(name, why),
                    )
                )
    else:
        findings.append(_finding(OK, "layout", "both directory pointers resolve correctly"))

    # Credential findings belong in the same report: a reference whose value is gone,
    # or a value sitting in the last-resort plaintext backend, is exactly the kind of
    # drift `doctor` exists to surface, and ADR-0010 asks for it to be reported loudly.
    for finding in creds.check(project_id):
        findings.append(_credential_finding(finding))

    resolved_prefs = root / prefs.RESOLVED_FILE
    if not resolved_prefs.is_file():
        findings.append(
            _finding(
                WARN,
                "preferences",
                "{} is missing — agents have no resolved preferences to read".format(
                    prefs.RESOLVED_FILE
                ),
                "Run `devteam sync`.",
            )
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
    bound = manifest.get("providers") or ["claude"]
    settings = root / hooks.SETTINGS_FILE
    if "claude" in bound and manifest.get("mode") != "vendored":
        registered = hooks.registered_events(root)
        expected_events = [event for event, _ in hooks.EVENTS]
        absent = [event for event in expected_events if event not in registered]
        if absent:
            findings.append(
                _finding(
                    WARN,
                    "hooks",
                    "{} not registered in {}".format(", ".join(absent), hooks.SETTINGS_FILE),
                    "Run `devteam sync` — without them the {} enforcement and "
                    "task board capture do not run in this project.".format(", ".join(expected_events)),
                )
            )
        elif settings.is_file():
            findings.append(
                _finding(OK, "hooks", "{} dispatchers registered in {}".format(len(expected_events), hooks.SETTINGS_FILE))
            )
    if "codex" in bound:
        present = providers_module.codex_hook_events(root)
        absent = [e for e in providers_module.CODEX_MANAGED_EVENTS if e not in present]
        if absent:
            findings.append(
                _finding(
                    WARN,
                    "hooks",
                    "{} not wired in {}".format(", ".join(absent), providers_module.CODEX_HOOKS_FILE),
                    "Run `devteam sync` — it re-runs the Codex installer, which rewrites the managed hooks.",
                )
            )
        else:
            findings.append(
                _finding(
                    OK,
                    "hooks",
                    "{} Codex hook events wired in {}".format(len(present), providers_module.CODEX_HOOKS_FILE),
                )
            )
    if "opencode" in bound:
        plugin = root / providers_module.OPENCODE_PLUGIN_FILE
        if plugin.exists():
            findings.append(_finding(OK, "hooks", "opencode plugin present at {}".format(providers_module.OPENCODE_PLUGIN_FILE)))
        else:
            findings.append(
                _finding(
                    WARN,
                    "hooks",
                    "opencode plugin missing at {}".format(providers_module.OPENCODE_PLUGIN_FILE),
                    "Run `devteam sync` — it re-runs the opencode installer, which copies the plugin.",
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

    # The unbound-v2 branch above never runs once a bind has written `project.json`,
    # so a bind over a v2 install left the vendored tree behind with nothing to say
    # so: this project reported `status: ok` with 324 framework files still in git.
    leftover = migrate.leftover_trees(root)
    if leftover:
        findings.append(
            _finding(
                WARN,
                "project",
                "a v2 vendored install is still here ({} under {}/) — nothing reads it "
                "since the bind".format(", ".join(leftover), project.PROJECT_DIR),
                "Run `devteam migrate` — it shows a plan first and moves the old tree into "
                "a dated quarantine rather than deleting it.",
            )
        )

    tracked = bind_module.tracked_artifacts(root, manifest)
    if tracked:
        findings.append(
            _finding(
                WARN,
                "bind",
                "{} bind artifact(s) are tracked by git — ignoring them has no effect "
                "while they are, and a commit would hand teammates links into this "
                "machine's store".format(len(tracked)),
                "Untrack them (the files stay on disk) and commit the removal: "
                "git rm -r --cached {}".format(" ".join(tracked)),
            )
        )
    return findings, actions


def check_credentials_local(root):
    """ADR-0024 relocation as a doctor check. A conflict is a finding, never a failure."""
    if project.load(root) is None:
        return [], [], None
    findings, actions = [], []
    try:
        report = credentials_local.relocate(root)
    except (EnvError, ConflictError, OSError) as exc:
        findings.append(
            _finding(WARN, "credentials", "cannot relocate credentials.local.json: {}".format(exc))
        )
        return findings, actions, None
    for item in report["moved"]:
        actions.append({"action": "credentials_relocated", "from": item["from"], "to": item["to"]})
        findings.append(
            _finding(OK, "credentials", "credentials.local.json moved to {}".format(item["to"]))
        )
    for item in report["quarantined"]:
        actions.append(
            {"action": "credentials_quarantined", "path": item["path"], "to": item["to"], "reason": item["reason"]}
        )
        findings.append(
            _finding(
                OK,
                "credentials",
                "{} copy of credentials.local.json quarantined: {}".format(item["reason"], item["path"]),
            )
        )
    for item in report["conflicts"]:
        if item.get("reason") == "symlink":
            message = "a credentials.local.json symlink is involved ({} / {})".format(
                item["legacy"], item["root"]
            )
            hint = "dev-team-agents never reads or moves credentials through a link; replace it with a regular file. Nothing was changed."
        else:
            message = "{} and {} hold different credentials.local.json content".format(
                item["legacy"], item["root"]
            )
            hint = "Merge them by hand into {} and delete the legacy copy; nothing was changed.".format(
                item["root"]
            )
        findings.append(_finding(WARN, "credentials", message, hint))
    target = Path(report["path"])
    # Permission bits mean nothing on Windows (every file reads 0666), and `chmod 600` cannot
    # clear the warning there: the check is POSIX-only, as secrets.py documents.
    try:
        mode = target.stat().st_mode & 0o777 if os.name == "posix" and target.is_file() else None
    except OSError:
        mode = None
    if mode is not None and mode & 0o077:
        findings.append(
            _finding(
                WARN,
                "credentials",
                "{} is readable by other users (mode {:04o})".format(target, mode),
                "chmod 600 {}".format(target),
            )
        )
    return findings, actions, report


def run(project_root=None, reassign_identity=False):
    findings = list(check_store())
    findings.extend(check_machine())
    registry_findings, _ = check_registry()
    findings.extend(registry_findings)

    actions = []
    credentials_report = None
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
        cred_findings, cred_actions, credentials_report = check_credentials_local(root)
        findings.extend(cred_findings)
        actions.extend(cred_actions)

    worst = OK
    for item in findings:
        if item["level"] == FAIL:
            worst = FAIL
            break
        if item["level"] == WARN:
            worst = WARN
    return {
        "status": worst,
        "findings": findings,
        "actions": actions,
        "credentials_local": credentials_report,
    }
