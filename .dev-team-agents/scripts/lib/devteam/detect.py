"""What a folder is, read from the folder and the machine: ``devteam detect`` (ADR-0030).

First-run onboarding used to ask the user things a program can read. This module reports
the providers on the machine and in the project, the primary stack, a suggested project
type and a read-only first task. It never writes: no file is created, no command that
could change the project is run, and every subprocess is timeout-guarded.

The stack table (``stack-signals.json``) and the per-provider launch map
(``first-task.json``) are data next to this package, not code, so a row is one edit.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from . import providers

LIB_DIR = Path(__file__).resolve().parent.parent
STACK_SIGNALS_FILE = LIB_DIR / "stack-signals.json"
FIRST_TASK_FILE = LIB_DIR / "first-task.json"

#: Directories that never count as the project's own code or history.
IGNORED_DIRS = frozenset(
    {
        "node_modules", "vendor", "dist", "build", "docs", "target", "out", "coverage",
        "venv", "env", "__pycache__", "bin", "obj", "pods", "site-packages",
    }
)
#: Directory names that hold tests, not the code under test.
TEST_DIRS = frozenset({"tests", "test", "__tests__", "spec", "specs", "e2e"})
CI_MARKERS = (
    ".github/workflows", ".gitlab-ci.yml", "Jenkinsfile", ".circleci", "bitbucket-pipelines.yml",
    "azure-pipelines.yml", ".travis.yml",
)
_MAX_FILES = 20000
_MAX_DEPTH = 6
_PROBE_TIMEOUT = 5
_BASE_CANDIDATES = ("main", "master", "trunk", "develop")


def _load(path):
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


# ── subprocess helpers ────────────────────────────────────────────────────────

def _run(argv, cwd=None):
    """Stdout of a short command, or None when it is missing, slow or failed."""
    try:
        result = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=_PROBE_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", "replace")


def binary_version(binary):
    """First line of ``<binary> --version``, or None when it does not answer."""
    out = _run([binary, "--version"])
    if out is None:
        return None
    lines = out.strip().splitlines()
    return lines[0].strip() if lines and lines[0].strip() else None


def _git(root, *args):
    out = _run(["git", *args], cwd=root)
    return out.strip() if out is not None else None


# ── providers ─────────────────────────────────────────────────────────────────

def installed_providers():
    """Provider CLIs on ``PATH``, in ``ALL_PROVIDERS`` order. The binary name is the provider's."""
    found = []
    for name in providers.ALL_PROVIDERS:
        if shutil.which(name):
            found.append({"name": name, "binary": name, "version": binary_version(name)})
    return found


def detect_providers(root):
    installed = installed_providers()
    names = [item["name"] for item in installed]
    in_project = providers.detect_in_project(root)
    both = [name for name in in_project if name in names]
    suggested = both[0] if both else (names[0] if names else None)
    return {"installed": installed, "in_project": in_project, "suggested": suggested}


# ── project scan ──────────────────────────────────────────────────────────────

def _source_extensions(table):
    return {ext for stack in table["stacks"] for ext in stack["extensions"]}


def _is_test_file(name):
    low = name.lower()
    stem = low.rsplit(".", 1)[0]
    return low.startswith("test_") or stem.endswith(("_test", ".test", ".spec"))


def scan_tree(root, extensions):
    """Source-file counts by extension and by top-level directory, plus test/CI presence."""
    root = Path(root)
    by_ext = {}
    by_top = {}
    has_tests = False
    total = 0
    for current, dirs, files in os.walk(str(root)):
        rel = Path(current).relative_to(root)
        depth = len(rel.parts)
        top = rel.parts[0] if rel.parts else "."
        kept = []
        for name in dirs:
            if name.startswith(".") or name.lower() in IGNORED_DIRS:
                continue
            if name.lower() in TEST_DIRS:
                has_tests = True
            kept.append(name)
        dirs[:] = kept if depth < _MAX_DEPTH else []
        in_tests = any(part.lower() in TEST_DIRS for part in rel.parts)
        for name in files:
            total += 1
            if total > _MAX_FILES:
                return by_ext, by_top, has_tests
            if _is_test_file(name):
                has_tests = True
            ext = os.path.splitext(name)[1].lower()
            if ext in extensions and not in_tests:
                by_ext[ext] = by_ext.get(ext, 0) + 1
                by_top[top] = by_top.get(top, 0) + 1
    return by_ext, by_top, has_tests


def _has_ci(root):
    return any((Path(root) / marker).exists() for marker in CI_MARKERS)


def _signal_matches(root, signal):
    """The label of the file evidence behind a matching signal, or None."""
    root = Path(root)
    if "all_files" in signal:
        files = signal["all_files"]
        if all((root / name).is_file() for name in files) and not any(
            (root / name).exists() for name in signal.get("none_files", ())
        ):
            return " + ".join(files)
        return None
    if "glob" in signal:
        pattern = signal["glob"]
        try:
            hit = next(root.glob(pattern), None)
        except (OSError, ValueError):
            hit = None
        return pattern if hit is not None else None
    if "file_contains" in signal:
        spec = signal["file_contains"]
        target = root / spec["file"]
        try:
            if target.is_file() and spec["text"] in target.read_text(encoding="utf-8", errors="replace"):
                return "{} ({})".format(spec["file"], spec["text"])
        except OSError:
            return None
    return None


def detect_stack(root, table=None, by_ext=None):
    table = table or _load(STACK_SIGNALS_FILE)
    matched = []
    signals = []
    for stack in table["stacks"]:
        labels = [label for label in (_signal_matches(root, s) for s in stack["signals"]) if label]
        if labels:
            matched.append(stack)
            signals.extend(labels)
    if not matched:
        return {"primary": None, "all": [], "signals": []}
    counts = by_ext or {}

    def weight(stack):
        return sum(counts.get(ext, 0) for ext in stack["extensions"])

    # `max` keeps the first of equal weights, which is the table's own order.
    primary = max(matched, key=weight)
    seen = []
    for label in signals:
        if label not in seen:
            seen.append(label)
    return {"primary": primary["name"], "all": [s["name"] for s in matched], "signals": seen}


# ── git ───────────────────────────────────────────────────────────────────────

def default_branch(root):
    """The base branch, auto-detected; never assumed.

    Order: the remote's HEAD, ``init.defaultBranch``, then the first of the conventional
    names that exists locally. ``None`` when nothing resolves.
    """
    head = _git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if head:
        return head.split("/", 1)[1] if "/" in head else head
    configured = _git(root, "config", "--get", "init.defaultBranch")
    candidates = ([configured] if configured else []) + list(_BASE_CANDIDATES)
    for name in candidates:
        if _git(root, "rev-parse", "--verify", "--quiet", "refs/heads/" + name):
            return name
    return None


def git_facts(root):
    inside = _git(root, "rev-parse", "--is-inside-work-tree")
    if inside != "true":
        return {"repo": False, "commits": 0, "tags": 0, "branch": None, "base": None, "ahead": 0}
    commits = _git(root, "rev-list", "--count", "HEAD")
    tags = _git(root, "tag", "--list")
    branch = _git(root, "symbolic-ref", "--short", "-q", "HEAD")
    base = default_branch(root)
    ahead = 0
    if branch and base and branch != base:
        count = _git(root, "rev-list", "--count", "{}..HEAD".format(base))
        ahead = int(count) if count and count.isdigit() else 0
    return {
        "repo": True,
        "commits": int(commits) if commits and commits.isdigit() else 0,
        "tags": len(tags.splitlines()) if tags else 0,
        "branch": branch,
        "base": base,
        "ahead": ahead,
    }


# ── project type ──────────────────────────────────────────────────────────────

def classify_project(git, code_files, has_tests, has_ci):
    """``(type, confidence, reasons)``. Unsure means ``maintenance``, the least presumptuous answer."""
    commits, tags = git["commits"], git["tags"]
    reasons = []
    if commits == 0:
        reasons.append("no commits yet")
        if code_files:
            reasons.append("{} source file(s) not committed".format(code_files))
        return "new", "high", reasons
    if commits <= 3 and code_files <= 15:
        return "new", "high", ["{} commit(s) and {} source file(s)".format(commits, code_files)]
    if commits <= 3:
        return (
            "maintenance",
            "low",
            ["{} commit(s) but {} source files — probably an imported project".format(commits, code_files)],
        )
    if tags or (has_tests and commits >= 10):
        if tags:
            reasons.append("{} release tag(s)".format(tags))
        if has_tests:
            reasons.append("tests present")
        if has_ci:
            reasons.append("CI configured")
        reasons.append("{} commits".format(commits))
        return "maintenance", ("high" if (has_tests or has_ci) else "low"), reasons
    if not has_tests and not has_ci:
        reasons = ["{} commits".format(commits), "no tests, CI or release tags"]
        conflict = code_files > 200 or commits > 200
        if conflict:
            reasons.append("but a large codebase or history")
        return "unfinished", ("low" if conflict else "high"), reasons
    reasons = ["{} commits".format(commits)]
    reasons.append("tests present" if has_tests else "CI configured, no tests found")
    return "maintenance", "low", reasons


# ── first task ────────────────────────────────────────────────────────────────

def launch_for(provider, kind, target, table=None):
    """``{"provider", "argv"}`` for a provider, or None when it has no read-only mode."""
    table = table or _load(FIRST_TASK_FILE)
    entry = (table.get("providers") or {}).get(provider)
    if not entry:
        return None
    extra = (table.get("kinds") or {}).get(kind, {}).get("args", "")
    prompt = entry["prompt"].format(
        kind=kind, target=target, args=(" " + extra) if extra else ""
    )
    return {"provider": provider, "argv": [part.replace("{prompt}", prompt) for part in entry["argv"]]}


def _audit_target(by_top):
    candidates = {
        name: count for name, count in by_top.items() if name.lower() not in TEST_DIRS
    }
    if not candidates:
        return None
    dirs = {n: c for n, c in candidates.items() if n != "."}
    if dirs:
        return max(sorted(dirs), key=lambda n: dirs[n])
    return "."


def first_task(git, by_top, provider):
    if git["repo"] and git["ahead"] > 0 and git["branch"]:
        kind, target = "review", git["branch"]
        label = "Review your last changes on {}".format(target)
    else:
        top = _audit_target(by_top)
        if top is None:
            return None
        kind, target = "audit", top
        label = "Audit this project" if top == "." else "Audit {}/".format(top)
    launch = launch_for(provider, kind, target) if provider else None
    return {"kind": kind, "target": target, "label": label, "read_only": True, "launch": launch}


# ── entry point ───────────────────────────────────────────────────────────────

def run(path=None, provider=None, project_type=None):
    """The ``devteam detect`` document body. ``provider``/``project_type`` are the user's overrides."""
    root = Path(path or ".").resolve()
    table = _load(STACK_SIGNALS_FILE)
    by_ext, by_top, has_tests = scan_tree(root, _source_extensions(table))
    git = git_facts(root)
    code_files = sum(by_top.values())

    provider_info = detect_providers(root)
    if provider:
        provider_info["suggested"] = provider
    stack = detect_stack(root, table, by_ext)
    suggested, confidence, reasons = classify_project(git, code_files, has_tests, _has_ci(root))
    if project_type:
        suggested, confidence, reasons = project_type, "high", ["chosen by you"]
    return {
        "path": str(root),
        "providers": provider_info,
        "stack": stack,
        "project_type": {"suggested": suggested, "confidence": confidence, "reasons": reasons},
        "first_task": first_task(git, by_top, provider_info["suggested"]),
    }
