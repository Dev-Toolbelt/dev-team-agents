#!/usr/bin/env python3
"""Render a winget manifest set from the tracked scaffold to a real release.

Input is the scaffold under packaging/winget/manifests/ (PackageVersion 0.0.0, the
literal tag vX.Y.Z, 64-zero digests). Output is the same three files at the real
version, in the directory layout winget-pkgs uses, ready for `winget validate` and
`wingetcreate submit`.

The four edits a hand bump needs — the version directory, PackageVersion in all three
files, InstallerUrl, InstallerSha256 — are exactly what
.github/scripts/ci/04-packaging.sh enforces agree, so the rendered tree is meant to be
run through that gate (WINGET_ROOT=<out>). Digests are read from a SHA256SUMS.txt
published beside the installers; this script never hashes anything itself, so a digest
can only come from the release's own checksum file.

Usage:
  render-winget-manifests.py --package Devteam|DevteamApp --tag <tag> --sums <file> --out <dir>
                             [--templates packaging/winget/manifests]

--tag is the release tag the installers live under: vX.Y.Z for the CLI, app-vX.Y.Z for
the app. The version is the tag without that prefix.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCAFFOLD_VERSION = "0.0.0"
SCAFFOLD_TAG = "vX.Y.Z"
SCAFFOLD_TOKEN = "X.Y.Z"
ZERO_DIGEST = "0" * 64
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
SUMS_LINE_RE = re.compile(r"^([0-9a-fA-F]{64}) [ *](.+)$")
TAG_RE = {
    "Devteam": re.compile(r"^v(\d+\.\d+\.\d+)$"),
    "DevteamApp": re.compile(r"^app-v(\d+\.\d+\.\d+)$"),
}
SCHEMA_HEADER = "# yaml-language-server:"


def die(message: str) -> "None":
    sys.stderr.write("render-winget-manifests: error: %s\n" % message)
    sys.exit(1)


def read_sums(path: Path) -> dict[str, str]:
    sums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        match = SUMS_LINE_RE.match(line)
        if not match:
            die("%s: not a sha256sum line: %r" % (path, line))
        sums[match.group(2).strip()] = match.group(1).lower()
    if not sums:
        die("%s holds no digests" % path)
    return sums


def render_file(text: str, version: str, tag: str, sums: dict[str, str], name: str) -> str:
    out: list[str] = []
    pending_asset: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        # Comments describe the scaffold ("UNRELEASED ... 64 zeros ..."); on a released
        # manifest they would be false. Only the schema pointer is kept.
        if stripped.startswith("#"):
            if stripped.startswith(SCHEMA_HEADER):
                out.append(line)
            continue
        if re.match(r"^PackageVersion:\s", line):
            line = "PackageVersion: %s" % version
        elif re.match(r"^\s*-?\s*InstallerUrl:\s", line):
            url = line.split("InstallerUrl:", 1)[1].strip()
            if "/download/%s/" % SCAFFOLD_TAG not in url or SCAFFOLD_TOKEN not in url.rsplit("/", 1)[1]:
                die("%s: InstallerUrl is not the scaffold shape: %s" % (name, url))
            url = url.replace("/download/%s/" % SCAFFOLD_TAG, "/download/%s/" % tag)
            head, asset = url.rsplit("/", 1)
            asset = asset.replace(SCAFFOLD_TOKEN, version)
            url = head + "/" + asset
            pending_asset = asset
            line = line.split("InstallerUrl:", 1)[0] + "InstallerUrl: " + url
        elif re.match(r"^\s*InstallerSha256:\s", line):
            if pending_asset is None:
                die("%s: InstallerSha256 with no preceding InstallerUrl" % name)
            digest = sums.get(pending_asset)
            if digest is None:
                die("%s: %s is not listed in the SHA256SUMS.txt (has: %s)"
                    % (name, pending_asset, ", ".join(sorted(sums))))
            if not SHA_RE.match(digest) or digest == ZERO_DIGEST:
                die("%s: digest for %s is not a real sha256: %s" % (name, pending_asset, digest))
            line = line.split("InstallerSha256:", 1)[0] + 'InstallerSha256: "%s"' % digest
            pending_asset = None
        out.append(line)
    if pending_asset is not None:
        die("%s: InstallerUrl for %s has no InstallerSha256 after it" % (name, pending_asset))
    return "\n".join(out).rstrip("\n") + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--package", required=True, choices=sorted(TAG_RE))
    parser.add_argument("--tag", required=True)
    parser.add_argument("--sums", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--templates", type=Path, default=Path("packaging/winget/manifests"))
    args = parser.parse_args()

    match = TAG_RE[args.package].match(args.tag)
    if not match:
        die("tag %r does not match %s for package %s" % (args.tag, TAG_RE[args.package].pattern, args.package))
    version = match.group(1)

    template_dir = args.templates / "d" / "DevToolbelt" / args.package / SCAFFOLD_VERSION
    files = sorted(template_dir.glob("*.yaml"))
    if len(files) != 3:
        die("expected 3 scaffold manifests in %s, found %d" % (template_dir, len(files)))

    sums = read_sums(args.sums)
    target = args.out / "d" / "DevToolbelt" / args.package / version
    target.mkdir(parents=True, exist_ok=True)
    for source in files:
        text = source.read_text(encoding="utf-8")
        if not re.search(r"^PackageVersion:\s*%s\s*$" % re.escape(SCAFFOLD_VERSION), text, re.M):
            die("%s is not on the scaffold version %s — refusing to re-render a released manifest"
                % (source, SCAFFOLD_VERSION))
        (target / source.name).write_text(
            render_file(text, version, args.tag, sums, source.name), encoding="utf-8")
    sys.stdout.write("rendered %d manifests to %s\n" % (len(files), target))


if __name__ == "__main__":
    main()
