"""Fetch a release into the core and re-point every project that follows it.

This is the command the whole v3 design exists for: one download, one pointer
move, then every bound project that is not pinned resolves to the new version.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import ssl
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import bind as bind_module
from . import paths, versions
from .errors import EnvError, UsageError

GITHUB_OWNER = "Dev-Toolbelt"
GITHUB_REPO = "dev-team-agents"
API_LATEST = "https://api.github.com/repos/{}/{}/releases/latest"
TARBALL = "https://github.com/{}/{}/archive/refs/tags/{}.tar.gz"
USER_AGENT = "dev-team-agents-cli"
TIMEOUT = 30
#: A release tarball of this project is ~3 MB. The cap exists so a compromised or
#: misbehaving endpoint cannot drive the process out of memory.
MAX_DOWNLOAD_BYTES = 128 * 1024 * 1024
#: Only these hosts may serve a release, including after a redirect.
ALLOWED_HOSTS = frozenset(
    {"github.com", "api.github.com", "codeload.github.com", "objects.githubusercontent.com"}
)
#: `vX.Y.Z` with an optional pre-release/build suffix. Validated BEFORE the first
#: network call: an unvalidated ref was interpolated straight into the URL path,
#: where `../` segments retargeted the download at an arbitrary repository — and
#: the semver check only happened after the archive had already been extracted.
REF_RE = re.compile(r"v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?\Z")
SHA256_ENV = "DEVTEAM_TARBALL_SHA256"


def validate_ref(ref):
    if not isinstance(ref, str) or not REF_RE.match(ref):
        raise UsageError(
            "invalid ref {!r} — expected vX.Y.Z".format(ref),
            hint="Refs are version tags; nothing else is fetched.",
        )
    return ref


def _check_url(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise EnvError(
            "refusing to fetch from {}".format(url),
            hint="Releases are only fetched over https from GitHub.",
        )
    return url


class _RestrictedRedirects(urllib.request.HTTPRedirectHandler):
    """Follow redirects only to an allowed https host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _check_url(newurl)
        return urllib.request.HTTPRedirectHandler.redirect_request(
            self, req, fp, code, msg, headers, newurl
        )


def _opener():
    context = ssl.create_default_context()
    return urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context), _RestrictedRedirects()
    )


def _get(url, as_json=False):
    _check_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with _opener().open(request, timeout=TIMEOUT) as response:
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > MAX_DOWNLOAD_BYTES:
                raise EnvError(
                    "refusing a {} byte response from {}".format(declared, url),
                    hint="The release archive is far smaller than this.",
                )
            payload = response.read(MAX_DOWNLOAD_BYTES + 1)
            if len(payload) > MAX_DOWNLOAD_BYTES:
                raise EnvError("response from {} exceeds the size cap".format(url))
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
    return validate_ref(tag)


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


def safe_members(tar):
    """Yield only members that cannot write outside the extraction directory.

    The previous filter checked ``member.name`` and stopped there. Three classes
    slipped through, and the first is a full escape: a symlink or hardlink member
    whose **linkname** is absolute or climbs out, after which any later member
    whose own clean ``name`` descends through that link is written outside the
    tree. Device and FIFO members were also unfiltered.

    This runs in addition to ``filter="data"`` below, not instead of it: the
    keyword only exists on Python 3.12+, and on older interpreters
    ``extractall``'s default is ``fully_trusted``.
    """
    for member in tar.getmembers():
        name = Path(member.name)
        # An archive is untrusted input that may have been built on, or for, a
        # different platform than the one extracting it — so both a member name
        # and a link target are checked against POSIX *and* Windows absoluteness
        # regardless of which platform this process is running on. A bare
        # `name.is_absolute()` only answers for the host's own flavour:
        # `WindowsPath("/etc").is_absolute()` is False, which let a
        # POSIX-absolute member name through unrejected when extracting on
        # Windows.
        if name.is_absolute() or ".." in name.parts or paths.is_absolute_on_any_platform(member.name):
            raise EnvError("refusing unsafe archive member name: {}".format(member.name))
        if member.isdev() or member.isfifo():
            raise EnvError("refusing device/fifo archive member: {}".format(member.name))
        if member.issym() or member.islnk():
            link = Path(member.linkname)
            if link.is_absolute() or paths.is_absolute_on_any_platform(member.linkname):
                raise EnvError(
                    "refusing archive link with an absolute target: {} -> {}".format(
                        member.name, member.linkname
                    )
                )
            resolved = os.path.normpath(os.path.join(str(name.parent), member.linkname))
            if os.path.isabs(resolved) or resolved == ".." or resolved.startswith(".." + os.sep):
                raise EnvError(
                    "refusing archive link escaping the tree: {} -> {}".format(
                        member.name, member.linkname
                    )
                )
        yield member


def verify_digest(payload, expected=None):
    """Verify the archive against a pinned digest, or say plainly that it cannot.

    v2's `scripts/lib/installer-fetch.sh` verifies `install.sh` against a
    published `.sha256`; the v3 fetch had no equivalent, which was a regression in
    a path that then executes shell scripts from the downloaded tree. Until a
    digest is published per release, `DEVTEAM_TARBALL_SHA256` provides
    out-of-band pinning and the absence of any digest is reported, not hidden.
    """
    actual = hashlib.sha256(payload).hexdigest()
    pinned = expected or os.environ.get(SHA256_ENV)
    if not pinned:
        return {"sha256": actual, "verified": False}
    if actual.lower() != pinned.strip().lower():
        raise EnvError(
            "archive digest mismatch: expected {}, got {}".format(pinned.strip(), actual),
            hint="The download does not match the pinned digest. Nothing was installed.",
        )
    return {"sha256": actual, "verified": True}


def _download_tree(ref, workdir, expected_sha256=None, emitter=None):
    """Download and extract a tag, returning the extracted repository root."""
    url = TARBALL.format(GITHUB_OWNER, GITHUB_REPO, urllib.parse.quote(ref, safe=""))
    payload = _get(url)
    digest = verify_digest(payload, expected_sha256)
    if not digest["verified"] and emitter is not None:
        emitter.warn(
            "archive integrity NOT verified (no digest pinned); sha256={}".format(
                digest["sha256"]
            )
        )
    archive = Path(workdir) / "source.tar.gz"
    archive.write_bytes(payload)
    extract_to = Path(workdir) / "extracted"
    extract_to.mkdir()
    with tarfile.open(str(archive), "r:gz") as tar:
        members = list(safe_members(tar))
        try:
            tar.extractall(str(extract_to), members=members, filter="data")
        except TypeError:
            # Python < 3.12 has no `filter=`; safe_members is the floor there.
            tar.extractall(str(extract_to), members=members)
    roots = [child for child in extract_to.iterdir() if child.is_dir()]
    if len(roots) != 1:
        raise EnvError("unexpected archive layout: {} top-level entries".format(len(roots)))
    return roots[0], digest


def run(ref=None, activate=True, sync=True, force=False, sha256=None, emitter=None):
    resolved_ref = validate_ref(ref) if ref else latest_ref()
    version = ref_to_version(resolved_ref)
    if versions.parse_semver(version) is None:
        raise UsageError("ref {} does not carry a semantic version".format(resolved_ref))

    digest = None
    if version in versions.installed() and not force:
        installed_now = False
    else:
        workdir = tempfile.mkdtemp(prefix="devteam-update-")
        try:
            tree, digest = _download_tree(
                resolved_ref, workdir, expected_sha256=sha256, emitter=emitter
            )
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
        "integrity": digest,
        "synced": len(synced["synced"]) if synced else 0,
        "problems": synced["problems"] if synced else [],
    }
