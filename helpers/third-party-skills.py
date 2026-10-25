#!/usr/bin/env python3
"""Vendor and verify the third-party skills listed in skills/third-party/sources.json.

Usage:
  python3 helpers/third-party-skills.py verify            # every vendored tree matches its recorded hash
  python3 helpers/third-party-skills.py sync [name ...]   # fetch at the pinned commit, record the hash
  python3 helpers/third-party-skills.py sync --force NAME # overwrite a tree that no longer matches

`sync` streams the pinned commit's tarball from codeload.github.com, extracts only
the skill's own path (minus its `exclude` globs) plus the declared license files,
and refuses links, absolute paths, `..` members and oversized archives. Nothing
downloaded is executed. `verify` is offline and is what the test suite runs.
"""

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parent.parent
THIRD_PARTY_DIR = REPO_ROOT / "skills" / "third-party"
MANIFEST = THIRD_PARTY_DIR / "sources.json"
TARBALL_URL = "https://codeload.github.com/{repo}/tar.gz/{commit}"
#: Caps on the whole decompressed archive, not only on the skill's own subset, so a
#: decompression bomb is stopped while it is being read.
MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 50000
MAX_SKILL_BYTES = 20 * 1024 * 1024
MAX_SKILL_ENTRIES = 2000
#: Files in skills/third-party/ itself that are not vendored skills.
ROOT_FILES = {"README.md", "sources.json"}

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def tree_hash(root):
    """sha256 over every entry, sorted by relative POSIX path.

    Each file contributes its path, NUL, an exec flag, NUL and its content sha256, so
    a mode change is caught too. A symlink anywhere — file or directory — is an
    error, never followed.
    """
    entries = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames + filenames:
            path = Path(dirpath) / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                raise ValueError(f"{root.name}: {rel} is a symlink")
            if name in filenames:
                if not path.is_file():
                    raise ValueError(f"{root.name}: {rel} is not a regular file")
                entries.append((rel, path))
    digest = hashlib.sha256()
    for rel, path in sorted(entries, key=lambda item: item[0]):
        executable = b"x" if path.stat().st_mode & stat.S_IXUSR else b"-"
        digest.update(rel.encode() + b"\0" + executable + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _safe_relative(value, what):
    rel = PurePosixPath(value)
    if not value or rel.is_absolute() or ".." in rel.parts or str(rel) in (".", ""):
        raise ValueError(f"{what} must be a relative path inside the repository, got {value!r}")
    return rel


def validate_entry(name, entry):
    if not NAME_RE.match(name):
        raise ValueError(f"skill name {name!r} must match {NAME_RE.pattern}")
    if not REPO_RE.match(entry.get("repo", "")):
        raise ValueError(f"{name}: repo must be owner/name")
    if not COMMIT_RE.match(entry.get("commit", "")):
        raise ValueError(f"{name}: commit must be a full 40-character sha, never a branch or tag")
    _safe_relative(entry.get("path", ""), f"{name}: path")
    for license_file in entry.get("license_files", []):
        if PurePosixPath(license_file).name in ("SKILL.md", ""):
            raise ValueError(f"{name}: license file {license_file!r} is not allowed")
        _safe_relative(license_file, f"{name}: license file")
    for pattern in entry.get("exclude", []):
        _safe_relative(pattern, f"{name}: exclude pattern")


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def save_manifest(manifest):
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, MANIFEST)


def _excluded(target, patterns):
    text = target.as_posix()
    return any(fnmatch.fnmatchcase(text, pattern) for pattern in patterns)


def fetch(entry, dest):
    """Stream the pinned tarball and write the skill's subset and license files into dest."""
    skill_prefix = PurePosixPath(entry["path"])
    licenses = {PurePosixPath(name).as_posix() for name in entry["license_files"]}
    excludes = entry.get("exclude", [])
    url = TARBALL_URL.format(repo=entry["repo"], commit=entry["commit"])
    archive_bytes = archive_entries = skill_bytes = skill_entries = 0
    written = set()
    with urllib.request.urlopen(url, timeout=60) as resp, tarfile.open(fileobj=resp, mode="r|gz") as tar:
        for member in tar:
            archive_entries += 1
            archive_bytes += max(member.size, 0)
            if archive_entries > MAX_ARCHIVE_ENTRIES or archive_bytes > MAX_ARCHIVE_BYTES:
                raise ValueError(f"{entry['repo']}: archive exceeds the size limits")
            parts = PurePosixPath(member.name).parts
            if len(parts) < 2:
                continue
            rel = PurePosixPath(*parts[1:])
            if rel.is_absolute() or ".." in rel.parts:
                raise ValueError(f"unsafe member {member.name}")
            if rel.as_posix() in licenses:
                target = PurePosixPath(rel.name)
            elif rel.is_relative_to(skill_prefix) and rel != skill_prefix:
                target = rel.relative_to(skill_prefix)
                if _excluded(target, excludes):
                    continue
            else:
                continue
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError(f"{entry['repo']}: {rel} is a link or special file")
            # Case-folded: on a case-insensitive filesystem `license` and `LICENSE` are one file.
            if target.as_posix().lower() in written:
                raise ValueError(f"{entry['repo']}: {target} is written twice (license file collision)")
            skill_entries += 1
            skill_bytes += member.size
            if skill_entries > MAX_SKILL_ENTRIES or skill_bytes > MAX_SKILL_BYTES:
                raise ValueError(f"{entry['repo']}: skill exceeds the size limits")
            out = dest / target
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(tar.extractfile(member).read())
            os.chmod(out, 0o755 if member.mode & 0o111 else 0o644)
            written.add(target.as_posix().lower())
    if not (dest / "SKILL.md").is_file():
        raise ValueError(f"{entry['repo']}: no SKILL.md under {skill_prefix}")
    missing = [name for name in licenses if PurePosixPath(name).name.lower() not in written]
    if missing:
        raise ValueError(f"{entry['repo']}: license files not found: {', '.join(missing)}")


def frontmatter_name(skill_md):
    lines = skill_md.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return None


def sync_one(manifest, name, force):
    entry = manifest["skills"][name]
    validate_entry(name, entry)
    current = THIRD_PARTY_DIR / name
    if current.exists() and entry.get("sha256") and not force:
        if tree_hash(current) != entry["sha256"]:
            sys.exit(f"{name}: vendored tree was modified; re-run with --force to overwrite")
    # Staged next to the destination so the swap is a rename on the same filesystem.
    staging = Path(tempfile.mkdtemp(prefix=f".{name}-", dir=THIRD_PARTY_DIR))
    try:
        staged = staging / name
        staged.mkdir()
        fetch(entry, staged)
        if frontmatter_name(staged / "SKILL.md") != name:
            sys.exit(f"{name}: SKILL.md frontmatter name does not match the manifest key")
        previous = staging / f"{name}.previous"
        if current.exists():
            os.replace(current, previous)
        try:
            os.replace(staged, current)
        except OSError:
            if previous.exists():
                os.replace(previous, current)
            raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    entry["sha256"] = tree_hash(current)
    # Saved per skill: a failure on the next one leaves this one recorded, not "modified".
    save_manifest(manifest)
    print(f"synced {name} @ {entry['commit'][:12]}")


def sync(names, force):
    manifest = load_manifest()
    unknown = [n for n in names if n not in manifest["skills"]]
    if unknown:
        sys.exit(f"unknown skill(s): {', '.join(unknown)}")
    for name in names or sorted(manifest["skills"]):
        sync_one(manifest, name, force)


def verify():
    manifest = load_manifest()
    failures = []
    for name, entry in sorted(manifest["skills"].items()):
        tree = THIRD_PARTY_DIR / name
        try:
            validate_entry(name, entry)
            if not (tree / "SKILL.md").is_file():
                failures.append(f"{name}: not vendored (run sync)")
            elif not entry.get("sha256"):
                failures.append(f"{name}: no recorded hash (run sync)")
            elif tree_hash(tree) != entry["sha256"]:
                failures.append(f"{name}: content differs from the recorded hash")
        except ValueError as exc:
            failures.append(str(exc))
    listed = set(manifest["skills"])
    for child in sorted(THIRD_PARTY_DIR.iterdir()):
        if child.is_dir() and not child.is_symlink():
            if child.name not in listed:
                failures.append(f"{child.name}: directory not listed in sources.json")
        elif child.name not in ROOT_FILES:
            failures.append(f"{child.name}: unexpected entry in skills/third-party/")
    if failures:
        print("third-party skills: FAIL")
        for line in failures:
            print(f"  · {line}")
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sync_p = sub.add_parser("sync")
    sync_p.add_argument("names", nargs="*")
    sync_p.add_argument("--force", action="store_true")
    sub.add_parser("verify")
    args = parser.parse_args()
    if args.cmd == "sync":
        sync(args.names, args.force)
        return 0
    return verify()


if __name__ == "__main__":
    sys.exit(main())
