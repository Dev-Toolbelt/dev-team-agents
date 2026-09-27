"""Fetch a release into the core and re-point every project that follows it.

This is the command the whole v3 design exists for: one download, one pointer
move, then every bound project that is not pinned resolves to the new version.
"""

from __future__ import annotations

import json
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from . import bind as bind_module
from . import versions
from .errors import EnvError

GITHUB_OWNER = "Dev-Toolbelt"
GITHUB_REPO = "dev-team-agents"
API_LATEST = "https://api.github.com/repos/{}/{}/releases/latest"
TARBALL = "https://github.com/{}/{}/archive/refs/tags/{}.tar.gz"
USER_AGENT = "dev-team-agents-cli"
TIMEOUT = 30


def _get(url, as_json=False):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        raise EnvError("GitHub returned HTTP {} for {}".format(exc.code, url)) from exc
    except (urllib.error.URLError, OSError) as exc:
        raise EnvError(
            "cannot reach {}: {}".format(url, exc),
            hint="Check connectivity, or install from a local tree with "
            "`devteam store install --from <path>`.",
        ) from exc
    if as_json:
        try:
            return json.loads(payload.decode("utf-8"))
        except ValueError as exc:
            raise EnvError("GitHub returned a malformed response for {}".format(url)) from exc
    return payload


def latest_ref():
    """The newest published release tag, e.g. ``v3.0.0``."""
    data = _get(API_LATEST.format(GITHUB_OWNER, GITHUB_REPO), as_json=True)
    tag = data.get("tag_name")
    if not tag:
        raise EnvError("the latest release has no tag_name")
    return tag


def ref_to_version(ref):
    return ref[1:] if ref.startswith("v") else ref


def check():
    """Compare the newest release with what the core already holds."""
    ref = latest_ref()
    version = ref_to_version(ref)
    installed = versions.installed()
    return {
        "latest_ref": ref,
        "latest_version": version,
        "installed": installed,
        "current": versions.current(),
        "already_installed": version in installed,
    }


def _download_tree(ref, workdir):
    """Download and extract a tag, returning the extracted repository root."""
    url = TARBALL.format(GITHUB_OWNER, GITHUB_REPO, ref)
    archive = Path(workdir) / "source.tar.gz"
    archive.write_bytes(_get(url))
    extract_to = Path(workdir) / "extracted"
    extract_to.mkdir()
    with tarfile.open(str(archive), "r:gz") as tar:
        members = []
        for member in tar.getmembers():
            # Refuse absolute paths and traversal before writing anything.
            target = Path(member.name)
            if target.is_absolute() or ".." in target.parts:
                raise EnvError("refusing to extract unsafe path from archive: {}".format(member.name))
            members.append(member)
        tar.extractall(str(extract_to), members=members)
    roots = [child for child in extract_to.iterdir() if child.is_dir()]
    if len(roots) != 1:
        raise EnvError("unexpected archive layout: {} top-level entries".format(len(roots)))
    return roots[0]


def run(ref=None, activate=True, sync=True, force=False, emitter=None):
    resolved_ref = ref or latest_ref()
    version = ref_to_version(resolved_ref)

    if version in versions.installed() and not force:
        installed_now = False
    else:
        workdir = tempfile.mkdtemp(prefix="devteam-update-")
        try:
            tree = _download_tree(resolved_ref, workdir)
            versions.install_from_tree(tree, version=version, force=force, make_current=False)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        installed_now = True

    activated = None
    if activate:
        versions.set_current(version)
        activated = version

    synced = None
    if sync:
        synced = bind_module.sync_all(emitter=emitter)

    return {
        "ref": resolved_ref,
        "version": version,
        "installed_now": installed_now,
        "activated": activated,
        "synced": len(synced["synced"]) if synced else 0,
        "problems": synced["problems"] if synced else [],
    }
