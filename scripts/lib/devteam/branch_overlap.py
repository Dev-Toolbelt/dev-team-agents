"""Branch-overlap cache: teammates' unmerged remote branches, matched against local edits (ADR-0051).

Two entry points, both reached through the hook scripts and neither raising to them:

``refresh``  runs detached from session start. At most every ``REFRESH_INTERVAL`` seconds it
             fetches quietly, lists the remote branches not merged into the base and not authored
             by the current git user, and records each one's changed files and hunk ranges in a
             dot-prefixed cache in the machine-local state directory (ADR-0013). Offline or any
             error: exit 0 and the previous cache stays.
``match``    reads the cache only — never git network — and prints the cached branches whose hunks
             overlap the working-tree hunks of one file against HEAD, as ``branch<TAB>author``.

Ranges are old-side line numbers (the base for a branch, HEAD for the working tree), so a branch
and a local edit are comparable without rebasing either. A pure insertion at line N counts as
the single line N.

Files, in the state directory (dot-prefixed, so ``paths.is_machine_local_record`` already
classifies them as machine-local):
  .branch-overlap.json   the cache
  .branch-overlap.stamp  mtime = last refresh attempt, successful or not (the 10-minute gate)
  .branch-overlap.lock/  mkdir lock held while refreshing
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import time

from . import jsonio
from .errors import DevteamError
from .lock import Lock

CACHE_NAME = ".branch-overlap.json"
STAMP_NAME = ".branch-overlap.stamp"
LOCK_NAME = ".branch-overlap.lock"

REFRESH_INTERVAL = 600
FETCH_TIMEOUT = 60
GIT_TIMEOUT = 30
MAX_BRANCHES = 50
MAX_FILES = 200
MAX_HUNKS = 100
MAX_MATCHES = 3
#: A branch whose tip is older than this is abandoned work, not a teammate in flight.
MAX_AGE_SECONDS = 60 * 24 * 3600
MAX_AUTHOR_LEN = 40
MAX_BRANCH_LEN = 80
FALLBACK_AUTHOR = "a teammate"
#: A range end for "the whole file" (an untracked file in the working tree).
WHOLE_FILE = 2 ** 31

_AUTHOR_UNSAFE = re.compile(r"[^\w .@-]")
_BRANCH_UNSAFE = re.compile(r"[^A-Za-z0-9._/+@-]")
_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@")


def clean_author(text):
    """A teammate-controlled author name made safe to embed in a hint; the fallback when nothing is left."""
    text = " ".join(_AUTHOR_UNSAFE.sub("", str(text)).split())[:MAX_AUTHOR_LEN].strip()
    return text or FALLBACK_AUTHOR


def clean_branch(text):
    """A teammate-controlled branch name reduced to git-ref-safe characters; '' when nothing is left."""
    return _BRANCH_UNSAFE.sub("", str(text))[:MAX_BRANCH_LEN]


def _ssh_default(root):
    """Non-interactive ssh options, unless the user already chose an ssh command (env or git config)."""
    if os.environ.get("GIT_SSH_COMMAND"):
        return None
    try:
        configured = subprocess.run(
            ["git", "-C", root, "config", "core.sshCommand"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=GIT_TIMEOUT,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        configured = b""
    return None if configured else "ssh -o BatchMode=yes -o ConnectTimeout=10"


def _git(root, *args, timeout=GIT_TIMEOUT, ssh=None):
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    if ssh:
        env["GIT_SSH_COMMAND"] = ssh
    env["LC_ALL"] = "C"
    result = subprocess.run(
        ["git", "-C", root] + list(args),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=timeout,
        env=env,
    )
    if result.returncode != 0:
        raise OSError("git {} failed".format(args[0]))
    return result.stdout.decode("utf-8", "replace")


def parse_hunks(diff_text):
    """``{path: [[start, end], ...]}`` from ``git diff -U0`` output, old-side coordinates."""
    files = {}
    current = None
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            current = None
        elif line.startswith("+++ "):
            target = line[4:]
            if target == "/dev/null":
                current = None
            else:
                current = target[2:] if target.startswith("b/") else target
                files.setdefault(current, [])
        elif line.startswith("--- ") and current is None:
            continue
        elif current is not None:
            m = _HUNK_RE.match(line)
            if m:
                start = int(m.group(1))
                count = 1 if m.group(2) is None else int(m.group(2))
                hunks = files[current]
                if len(hunks) < MAX_HUNKS:
                    hunks.append([start, start + max(count, 1) - 1])
    return files


def _base_ref(root):
    """The origin default branch as ``refs/remotes/origin/<name>``, or None.

    ``refs/remotes/origin/HEAD`` is absent in a clone made with ``--no-checkout``-style tooling, a
    ``git init`` plus ``remote add``, or a worktree-only setup. The refresher runs detached, so the
    remote itself may be asked: ``git ls-remote --symref origin HEAD`` names the default branch, and
    Nothing is assumed about the name, and the result stays in memory: the user's git state (the
    remote's recorded HEAD, its refs) is never changed from here.
    """
    try:
        ref = _git(root, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD").strip()
        if ref:
            return ref
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        out = _git(root, "ls-remote", "--symref", "origin", "HEAD", timeout=FETCH_TIMEOUT, ssh=_ssh_default(root))
    except (OSError, subprocess.SubprocessError):
        return None
    name = None
    for line in out.splitlines():
        m = re.match(r"^ref:\s+refs/heads/(\S+)\s+HEAD$", line)
        if m:
            name = m.group(1)
            break
    if not name:
        return None
    ref = "refs/remotes/origin/" + name
    try:
        _git(root, "rev-parse", "--verify", "--quiet", ref)
    except (OSError, subprocess.SubprocessError):
        return None
    return ref


def _collect(root):
    base = _base_ref(root)
    if not base:
        return None
    me = ""
    try:
        me = _git(root, "config", "user.email").strip().lower()
    except OSError:
        pass
    sep = "\x1f"
    now = time.time()
    out = _git(
        root,
        "for-each-ref",
        "--sort=-committerdate",
        "--no-merged=" + base,
        "--format=%(refname)" + sep + "%(refname:short)" + sep + "%(authoremail)" + sep + "%(authorname)" + sep
        + "%(committerdate:unix)",
        "refs/remotes/origin",
    )
    branches = []
    for row in out.splitlines():
        parts = row.split(sep)
        if len(parts) != 5:
            continue
        refname, short, email, author, committed = parts
        try:
            if now - int(committed) > MAX_AGE_SECONDS:
                continue
        except ValueError:
            continue
        if refname in (base, "refs/remotes/origin/HEAD"):
            continue
        email = email.strip("<>").lower()
        if me and email == me:
            continue
        if len(branches) >= MAX_BRANCHES:
            break
        try:
            merge_base = _git(root, "merge-base", base, refname).strip()
            diff = _git(root, "diff", "-U0", "--no-color", "--no-renames", "--no-ext-diff", merge_base, refname)
        except (OSError, subprocess.SubprocessError):
            continue
        files = parse_hunks(diff)
        if not files:
            continue
        kept = dict(sorted(files.items())[:MAX_FILES])
        name = clean_branch(short[len("origin/"):] if short.startswith("origin/") else short)
        if not name:
            continue
        branches.append({"name": name, "author": clean_author(author), "files": kept})
    return {"base": base, "branches": branches}


def sentinel_dir():
    """Where ``04-branch-overlap.sh`` looks, with a shell glob and no fork, for "some cache has a branch"."""
    base = (os.environ.get("TMPDIR") or "/tmp").rstrip("/") or "/tmp"
    return os.path.join(base, "devteam-branch-overlap")


def _set_sentinel(state_dir, present):
    """One file per state directory in ``sentinel_dir``: present while its cache holds a branch.

    The hook runs after every edit, and resolving git and the state directory costs tens of
    milliseconds, so it leaves in bash unless the directory holds a file. A missing or stale
    sentinel is harmless: missing forgoes one warning, stale costs the slow path.
    """
    try:
        key = hashlib.sha1(os.path.realpath(state_dir).encode("utf-8", "replace")).hexdigest()[:20]
        directory = sentinel_dir()
        path = os.path.join(directory, key)
        if present:
            os.makedirs(directory, mode=0o700, exist_ok=True)
            st = os.lstat(directory)
            # A directory another account planted in a shared $TMPDIR is not ours to write in.
            if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.geteuid() or st.st_mode & 0o022:
                return
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
            try:
                # A re-assert refreshes the age the 24 h sweep reads, so a live sentinel is kept.
                os.utime(fd)
            except (NotImplementedError, OSError):
                pass
            finally:
                os.close(fd)
        else:
            os.unlink(path)
    except OSError:
        pass


def _reassert_sentinel(state_dir):
    """Re-create the sentinel from the existing cache: $TMPDIR is cleared on reboot, the cache is not."""
    try:
        cache = jsonio.read_json(os.path.join(state_dir, CACHE_NAME), default=None)
        if isinstance(cache, dict) and cache.get("branches"):
            _set_sentinel(state_dir, True)
    except (DevteamError, OSError, ValueError):
        pass


def refresh(root, state_dir, force=False):
    """Refresh the cache when due. Never raises; returns True when a new cache was written."""
    try:
        if not os.path.isdir(state_dir):
            return False
        stamp = os.path.join(state_dir, STAMP_NAME)
        if not force:
            try:
                if time.time() - os.path.getmtime(stamp) < REFRESH_INTERVAL:
                    _reassert_sentinel(state_dir)
                    return False
            except OSError:
                pass
        lock = Lock(os.path.join(state_dir, LOCK_NAME), timeout=0.5, stale_after=300)
        with lock:
            # Re-check under the lock: a concurrent refresher may have just finished.
            if not force:
                try:
                    if time.time() - os.path.getmtime(stamp) < REFRESH_INTERVAL:
                        _reassert_sentinel(state_dir)
                        return False
                except OSError:
                    pass
            with open(stamp, "w", encoding="utf-8") as handle:
                handle.write(str(int(time.time())) + "\n")
            try:
                _git(root, "fetch", "--quiet", "origin", timeout=FETCH_TIMEOUT, ssh=_ssh_default(root))
                data = _collect(root)
            except (OSError, subprocess.SubprocessError):
                return False
            if data is None:
                return False
            data["refreshed_at"] = int(time.time())
            jsonio.write_json_atomic(os.path.join(state_dir, CACHE_NAME), data)
            _set_sentinel(state_dir, bool(data.get("branches")))
            return True
    except (DevteamError, OSError, ValueError, subprocess.SubprocessError):
        return False


def _overlaps(a, b):
    return a[0] <= b[1] and b[0] <= a[1]


def _working_hunks(root, path):
    """Working-tree hunks of ``path`` against HEAD; the whole file when HEAD does not track it."""
    tracked = True
    try:
        _git(root, "cat-file", "-e", "HEAD:" + path)
    except (OSError, subprocess.SubprocessError):
        tracked = False
    if not tracked:
        return [[1, WHOLE_FILE]]
    diff = _git(root, "diff", "-U0", "--no-color", "--no-renames", "--no-ext-diff", "HEAD", "--", path)
    return parse_hunks(diff).get(path, [])


def match(root, state_dir, path):
    """``[(branch, author)]`` whose cached hunks overlap the working-tree hunks of ``path``."""
    try:
        cache = jsonio.read_json(os.path.join(state_dir, CACHE_NAME), default=None)
        if not isinstance(cache, dict):
            return []
        candidates = [b for b in cache.get("branches", []) if isinstance(b, dict) and path in (b.get("files") or {})]
        if not candidates:
            return []
        local = _working_hunks(root, path)
        if not local:
            return []
        found = []
        for branch in candidates:
            ranges = branch["files"][path]
            if any(_overlaps(h, r) for h in local for r in ranges if len(r) == 2):
                found.append((clean_branch(branch.get("name", "")), clean_author(branch.get("author", ""))))
            if len(found) >= MAX_MATCHES:
                break
        return found
    except (DevteamError, OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        return []


def main(argv):
    """``refresh <root> <state-dir>`` or ``match <root> <state-dir> <repo-relative-path>``; always 0."""
    try:
        if len(argv) >= 3 and argv[0] == "refresh":
            refresh(argv[1], argv[2], force="--force" in argv[3:])
        elif len(argv) >= 4 and argv[0] == "match":
            for name, author in match(argv[1], argv[2], argv[3]):
                sys.stdout.write("{}\t{}\n".format(name, author))
    except Exception:  # noqa: BLE001 - a hook helper never disturbs the provider
        pass
    return 0
