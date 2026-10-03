#!/usr/bin/env python3
"""Fail when a Supabase service-role credential appears in a tree (ADR-0029 SR-36).

The service-role key bypasses every row-level policy, so it must never reach the repository
or a package. Two shapes are recognised:

* a legacy JWT whose payload decodes to ``"role": "service_role"``;
* a new-style secret key, ``sb_secret_`` followed by its body.

Usage: ``secret_scan.py <dir> [<dir> ...]``. Exit 0 clean, 1 findings, 2 cannot run.
Findings name the file and line, never the value. ``tests/test_secret_scan.py`` seeds a
positive case at runtime, so no real-looking key is ever committed to prove this works.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys

JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.(eyJ[A-Za-z0-9_-]{8,})\.[A-Za-z0-9_-]{16,}")
SECRET_KEY_RE = re.compile(r"\bsb_secret_[A-Za-z0-9_-]{16,}")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".worktrees", "dist", "out"}
MAX_BYTES = 2 * 1024 * 1024


def _b64url_json(segment):
    padded = segment + "=" * (-len(segment) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, UnicodeDecodeError):
        return None


def scan_text(text):
    """``[(line_number, kind)]`` for every service-role credential in ``text``."""
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        for match in JWT_RE.finditer(line):
            payload = _b64url_json(match.group(1))
            if isinstance(payload, dict) and payload.get("role") == "service_role":
                found.append((number, "service_role JWT"))
        if SECRET_KEY_RE.search(line):
            found.append((number, "sb_secret_ key"))
    return found


def scan_tree(root):
    findings = []
    for directory, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            path = os.path.join(directory, name)
            try:
                if os.path.getsize(path) > MAX_BYTES:
                    continue
                with open(path, "rb") as handle:
                    raw = handle.read()
            except OSError:
                continue
            if b"\0" in raw[:4096]:
                continue
            for number, kind in scan_text(raw.decode("utf-8", errors="replace")):
                findings.append("{}:{}: {}".format(os.path.relpath(path, root), number, kind))
    return findings


def main(argv):
    roots = argv[1:]
    if not roots or not all(os.path.isdir(r) for r in roots):
        print("usage: secret_scan.py <dir> [<dir> ...]", file=sys.stderr)
        return 2
    findings = [f for root in roots for f in scan_tree(root)]
    for line in findings:
        print("  " + line)
    if findings:
        print("  service-role credential found: remove it and rotate the key (ADR-0029 SR-36)")
        return 1
    print("  no service-role credential found")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
