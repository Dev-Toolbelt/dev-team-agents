#!/usr/bin/env python3
"""Render packaging/homebrew/devteam-app.rb at a real version and digest.

Only the two placeholder directives change: `version "0.0.0-unreleased"` and
`sha256 "NO_RELEASE_SHA256_DOES_NOT_EXIST_YET"`. The url already builds the asset name
and the `app-v<version>` tag from `#{version}`, so it is left alone. Full-line comments
are dropped from the output: they document the unreleased scaffold and would be false
on a released cask.

The digest must be the dmg's own, taken from the release's SHA256SUMS.txt — this script
only reads it.

Usage:
  render-app-cask.py --tag app-vX.Y.Z --sums SHA256SUMS.txt --out devteam-app.rb
                     [--cask packaging/homebrew/devteam-app.rb]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PLACEHOLDER_VERSION = "0.0.0-unreleased"
PLACEHOLDER_SHA = "NO_RELEASE_SHA256_DOES_NOT_EXIST_YET"
TAG_RE = re.compile(r"^app-v(\d+\.\d+\.\d+)$")


def die(message: str) -> None:
    sys.stderr.write("render-app-cask: error: %s\n" % message)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--sums", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cask", type=Path, default=Path("packaging/homebrew/devteam-app.rb"))
    args = parser.parse_args()

    match = TAG_RE.match(args.tag)
    if not match:
        die("tag %r is not app-vMAJOR.MINOR.PATCH" % args.tag)
    version = match.group(1)
    dmg = "dev-team-agents-%s.dmg" % version

    digest = None
    for line in args.sums.read_text(encoding="utf-8").splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[1].strip().lstrip("*") == dmg:
            digest = parts[0].lower()
    if digest is None or not re.match(r"^[0-9a-f]{64}$", digest):
        die("%s has no valid sha256 line for %s" % (args.sums, dmg))

    lines_out: list[str] = []
    seen_version = seen_sha = False
    for line in args.cask.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("#"):
            continue
        if re.match(r'^\s*version "%s"\s*$' % re.escape(PLACEHOLDER_VERSION), line):
            line = '  version "%s"' % version
            seen_version = True
        elif re.match(r'^\s*sha256 "%s"\s*$' % re.escape(PLACEHOLDER_SHA), line):
            line = '  sha256 "%s"' % digest
            seen_sha = True
        if line.strip() == "" and lines_out and lines_out[-1].strip() == "":
            continue
        lines_out.append(line)
    if not (seen_version and seen_sha):
        die("%s is not on the placeholder version/sha256 (version found: %s, sha256 found: %s)"
            % (args.cask, seen_version, seen_sha))

    args.out.write_text("\n".join(lines_out).strip("\n") + "\n", encoding="utf-8")
    sys.stdout.write("rendered %s (version %s)\n" % (args.out, version))


if __name__ == "__main__":
    main()
