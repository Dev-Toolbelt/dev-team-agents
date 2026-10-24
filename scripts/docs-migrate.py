#!/usr/bin/env python3
"""Move a bound project's docs from the `development` layout to `gated` (ADR-0045).

Run from the project root:

    python3 -I .dev-team-agents/scripts/docs-migrate.py [plan]      dry run, read-only
    python3 -I .dev-team-agents/scripts/docs-migrate.py apply        re-plans, then executes
    python3 -I .dev-team-agents/scripts/docs-migrate.py set-layout <development|gated>

The procedure around it is skills/shared/doc-flow/references/migration.md. `apply`
never trusts an earlier plan: it recomputes every check on the tree as it is now.

Output lines: MOVE, MERGE, CONFLICT, LINKS, UNTRACKED, SKIP, LAYOUT, SUMMARY,
REFUSE (exit 1), APPLIED. A cloned repository is untrusted input, so no symlink is
followed, nothing outside the project root is read or written, and only files git
tracks are rewritten — git holds their previous content, which keeps the run
reversible until it is committed.
"""

import argparse
import datetime
import os
import posixpath
import re
import stat
import subprocess
import sys

# -I leaves the script's directory off sys.path. Appended, never inserted, so nothing
# in the lib dir can shadow the standard library.
_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
if _LIB not in sys.path:
    sys.path.append(_LIB)

import docs_root  # noqa: E402
from devteam import jsonio, project  # noqa: E402

MAX_FILE_BYTES = 1024 * 1024  # the cap backlog._read applies
SYMLINK_MODE = "120000"
MERGED = ("dod", "backlog-index", "backlog-readme")  # merged into the gated backlog-index doc
MERGE_TITLES = {"dod": "Definition of Done", "backlog-index": "Sprints", "backlog-readme": "Backlog Notes"}
AGENT_FILES = ("CLAUDE.md", "AGENTS.md")
_GIT_ENV_OVERRIDES = ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
LINK = re.compile(r"(\]\()([^)\s#<>]+)([^)]*\))")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
J = posixpath.join


class Refuse(Exception):
    """A precondition failed; nothing was changed."""


class Root:
    """The project root and the guarded file operations under it."""

    def __init__(self, path):
        self.path = os.path.realpath(path)

    def abs(self, rel):
        return os.path.join(self.path, *rel.split("/"))

    def check(self, rel):
        """Refuse ``rel`` when a component is a symlink or it resolves outside the root."""
        if not rel or rel.startswith("/") or "\\" in rel or "\0" in rel:
            raise Refuse("unsafe path {!r}".format(rel[:120]))
        current = self.path
        for part in rel.rstrip("/").split("/"):
            if part in ("", ".", ".."):
                raise Refuse("unsafe path {!r}".format(rel[:120]))
            current = os.path.join(current, part)
            if os.path.islink(current):
                raise Refuse("{} is a symlink — a migration never follows one".format(
                    os.path.relpath(current, self.path)))
            if not os.path.lexists(current):
                break
        real = os.path.realpath(self.abs(rel.rstrip("/")))
        if real != self.path and not real.startswith(self.path + os.sep):
            raise Refuse("{} resolves outside the project root".format(rel))

    def exists(self, rel):
        return os.path.lexists(self.abs(rel.rstrip("/")))

    def isdir(self, rel):
        target = self.abs(rel.rstrip("/"))
        return not os.path.islink(target) and os.path.isdir(target)

    def read(self, rel):
        """The file's text, or a reason string prefixed with ``!`` when it is not read."""
        self.check(rel)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        try:
            fd = os.open(self.abs(rel), flags)
        except OSError as exc:
            return "!cannot open ({})".format(exc.strerror)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                return "!not a regular file"
            if info.st_size > MAX_FILE_BYTES:
                return "!larger than 1 MiB"
            data = b""
            while len(data) <= MAX_FILE_BYTES:
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                data += chunk
        finally:
            os.close(fd)
        if len(data) > MAX_FILE_BYTES:
            return "!larger than 1 MiB"
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return "!not UTF-8"

    def write(self, rel, text, create=False):
        """Overwrite an existing regular file in place, or create a new one (never over anything)."""
        self.check(rel)
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        if create:
            fd = os.open(self.abs(rel), os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow, 0o644)
        else:
            fd = os.open(self.abs(rel), os.O_WRONLY | nofollow)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise Refuse("{} is not a regular file".format(rel))
            os.ftruncate(fd, 0)
            payload = text.encode("utf-8")
            while payload:
                payload = payload[os.write(fd, payload):]
            os.fsync(fd)
        finally:
            os.close(fd)

    def makedirs(self, rel_dir):
        if rel_dir:
            self.check(rel_dir)
            os.makedirs(self.abs(rel_dir), exist_ok=True)


def git(root, *args):
    env = {k: v for k, v in os.environ.items() if k not in _GIT_ENV_OVERRIDES}
    try:
        done = subprocess.run(["git", "-C", root.path] + list(args), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=env, timeout=60, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise Refuse("git failed to run: {}".format(exc))
    if done.returncode != 0:
        raise Refuse("git {} failed: {}".format(args[0], done.stderr.decode("utf-8", "replace").strip()[:300]))
    return done.stdout.decode("utf-8", "replace")


def git_z(root, *args):
    return [item for item in git(root, *args).split("\0") if item]


class Plan:
    def __init__(self):
        self.moves, self.merges, self.conflicts = [], [], []  # (key, src, dst)
        self.dir_moves = []  # (src_dir, dst_dir)
        self.links = []  # (old, new, text)
        self.untracked, self.skipped = [], []  # paths; (path, reason)
        self.merge_target = None
        self.merge_sources = {}  # key -> text
        self.retarget = {}
        self.quarantine = {}


def _project(root):
    pj = ".dev-team-agents/project.json"
    if not root.exists(pj):
        raise Refuse("not a bound project — {} is missing; run `devteam bind` first".format(pj))
    root.check(pj)
    try:
        return project.load(root.path)
    except Exception as exc:  # noqa: BLE001 — any unreadable identity is a refusal
        raise Refuse("{} is not valid: {}".format(pj, exc))


def _preconditions(root):
    try:
        top = git(root, "rev-parse", "--show-toplevel").strip()
    except Refuse:
        raise Refuse("not a git work tree — the migration moves files with `git mv`")
    if os.path.realpath(top) != root.path:
        raise Refuse("run from the repository top level ({})".format(top))
    data = _project(root)
    current = (data or {}).get("docs_layout", project.DEFAULT_DOCS_LAYOUT)
    if current != "development":
        raise Refuse("the docs layout is already {!r} — nothing to migrate".format(current))
    if git(root, "status", "--porcelain", "-z").strip("\0"):
        raise Refuse("the working tree is dirty — commit or stash first (/devteam:commit)")
    wr = docs_root.write_root(root.path)
    root.check(wr)
    scope = [wr, "CLAUDE.md", "AGENTS.md", ".dev-team-agents/project.json"]
    links = []
    for entry in git_z(root, "ls-files", "-s", "-z", "--", *scope):
        meta, _, path = entry.partition("\t")
        if meta.split(" ")[0] == SYMLINK_MODE:
            links.append(path)
    if links:
        raise Refuse("tracked symlinks in the migration scope: " + ", ".join(sorted(links)))
    return wr


def build_plan(root):
    wr = _preconditions(root)
    today = datetime.date.today().isoformat()
    quar = J(wr, "legacy", "migration-" + today)
    docs = docs_root.layouts_map()["docs"]
    tracked = set(git_z(root, "ls-files", "-z", "--", wr, *AGENT_FILES))
    untracked = set(git_z(root, "ls-files", "-z", "--others", "--", wr, *AGENT_FILES))
    plan = Plan()
    plan.merge_target = J(wr, docs["backlog-index"]["gated"])
    root.check(plan.merge_target)

    def quarantine_of(src):
        return J(quar, posixpath.relpath(src, wr))

    for key, entry in docs.items():
        dev, gated = entry.get("development"), entry.get("gated")
        if key in MERGED:
            src = dev and J(wr, dev)
            if src and root.exists(src):
                root.check(src)
                if src in tracked:
                    plan.merges.append((key, src, plan.merge_target))
                else:
                    plan.untracked.append(src)
            continue
        if not dev or not gated or dev == gated:
            continue
        src, dst = J(wr, dev).rstrip("/"), J(wr, gated).rstrip("/")
        if not root.exists(src):
            continue
        root.check(src)
        root.check(dst)
        if root.isdir(src):
            plan.dir_moves.append((src, dst))
            for path in sorted(p for p in tracked if p.startswith(src + "/")):
                target = J(dst, posixpath.relpath(path, src))
                root.check(path)
                root.check(target)
                (plan.conflicts if root.exists(target) else plan.moves).append((key, path, target))
        elif src in tracked:
            (plan.conflicts if root.exists(dst) else plan.moves).append((key, src, dst))
        else:
            plan.untracked.append(src)

    if plan.merges and root.exists(plan.merge_target):
        plan.conflicts += plan.merges
        plan.merges = []
    for _, src, _ in plan.conflicts:
        q = quarantine_of(src)
        root.check(q)
        if root.exists(q):
            raise Refuse("quarantine path {} already exists".format(q))
        plan.quarantine[src] = q
    for key, src, _ in plan.merges:
        text = root.read(src)
        if text.startswith("!"):
            raise Refuse("cannot merge {}: {} — no content is dropped".format(src, text[1:]))
        plan.merge_sources[key] = text

    plan.retarget = {src: dst for _, src, dst in plan.moves}
    plan.retarget.update({src: dst for _, src, dst in plan.merges})
    plan.retarget.update(plan.quarantine)
    plan.retarget.update(dict(plan.dir_moves))
    historical = {src for _, src, _ in plan.merges}

    plan.untracked += sorted(p for p in untracked if p not in plan.untracked)
    scan = sorted(p for p in tracked if p.endswith(".md") and (p.startswith(wr + "/") or p in AGENT_FILES))
    for path in scan:
        if path in historical:
            continue
        text = root.read(path)
        if text.startswith("!"):
            plan.skipped.append((path, text[1:]))
            continue
        new_path = plan.retarget.get(path, path)
        after = rewrite(text, path, new_path, plan)
        if after != text:
            plan.links.append((path, new_path, after))
    return plan


def rewrite(text, old_file, new_file, plan):
    """Relative links re-resolved for the file's new location; root-anchored paths retargeted."""
    old_dir, new_dir = posixpath.dirname(old_file), posixpath.dirname(new_file)
    moved = old_dir != new_dir

    def fix(match):
        target = match.group(2)
        if SCHEME.match(target) or target.startswith("/"):
            return match.group(0)
        resolved = posixpath.normpath(J(old_dir, target) if old_dir else target)
        new_target = plan.retarget.get(resolved)
        if new_target is None:
            if not moved:
                return match.group(0)
            new_target = resolved
        rel = posixpath.relpath(new_target, new_dir or ".")
        if target.endswith("/") and not rel.endswith("/"):
            rel += "/"
        return match.group(1) + rel + match.group(3) if rel != target else match.group(0)

    text = LINK.sub(fix, text)
    for src, dst in sorted(plan.retarget.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(r"(?<![\w./-])" + re.escape(src) + r"(?![\w-])", lambda _m, d=dst: d, text)
    return text


def _section_body(text, src, plan):
    """Every line of ``text`` except its first H1; headings outside fences demoted one level."""
    body, h1_dropped, fence = [], False, False
    for line in text.splitlines():
        if line.startswith("```") or line.startswith("~~~"):
            fence = not fence
        if not fence and not h1_dropped and line.startswith("# "):
            h1_dropped = True
            continue
        if not fence and re.match(r"^#{1,5} ", line):
            line = "#" + line
        body.append(line)
    return rewrite("\n".join(body), src, plan.merge_target, plan).strip("\n")


def merged_index(plan, today):
    """The gated backlog index: skills/shared/backlog-template/SKILL.md § Gated Layout."""
    sources = ", ".join("`{}`".format(src) for _, src, _ in plan.merges)
    out = ["<!-- last-updated: {} -->".format(today), "# Backlog", "",
           "> Merged on {} by the docs layout migration from {}. The originals are kept as historical.".format(
               today, sources), ""]
    out += ["## Definition of Done", ""]
    if "dod" in plan.merge_sources:
        out += [_section_body(plan.merge_sources["dod"], _src(plan, "dod"), plan), ""]
    else:
        out += ["<!-- TODO: product-analyst to complete — the shared DoD of the backlog-template skill "
                "plus the doc-flow Definition of Done Additions -->", ""]
    out += ["## Definition of Ready",
            "A task enters a wave only when every item of `.dev-team-agents/skills/shared/doc-flow/SKILL.md` "
            "§ Definition of Ready holds — the list lives there, never copied here.", "",
            "### Project additions", "- none", ""]
    out += ["## Sprints", ""]
    if "backlog-index" in plan.merge_sources:
        out += [_section_body(plan.merge_sources["backlog-index"], _src(plan, "backlog-index"), plan), ""]
    else:
        out += ["| Scope | Sprint | Theme | Goal (one line) | Status |",
                "|-------|--------|-------|-----------------|--------|",
                "| — | No sprints created yet | — | — | — |", ""]
    if "backlog-readme" in plan.merge_sources:
        out += ["## " + MERGE_TITLES["backlog-readme"], "",
                _section_body(plan.merge_sources["backlog-readme"], _src(plan, "backlog-readme"), plan), ""]
    return "\n".join(out).rstrip("\n") + "\n"


def _src(plan, key):
    return next(src for k, src, _ in plan.merges if k == key)


def with_banner(text, src, target):
    lines = text.splitlines()
    rel = posixpath.relpath(target, posixpath.dirname(src) or ".")
    banner = "> ⚠️ Historical — superseded by [{}]({}). Current behavior is documented there.".format(
        posixpath.basename(target), rel)
    at = next((i + 1 for i, line in enumerate(lines) if line.startswith("# ")), 0)
    lines[at:at] = ["", banner]
    return "\n".join(lines) + "\n"


def print_plan(plan):
    for key, src, dst in plan.moves:
        print("MOVE", key, src, "->", dst)
    for key, src, dst in plan.merges:
        print("MERGE", key, src, "->", dst)
    for key, src, dst in plan.conflicts:
        print("CONFLICT", key, src, "->", dst, "(source quarantined to {})".format(plan.quarantine[src]))
    for old, new, _ in plan.links:
        print("LINKS", old if old == new else "{} -> {}".format(old, new))
    for path in plan.untracked:
        print("UNTRACKED", path, "(not tracked by git: left in place, not rewritten)")
    for path, reason in plan.skipped:
        print("SKIP", path, "({}: not rewritten)".format(reason))
    print("LAYOUT development -> gated")
    print("SUMMARY moves={} merges={} conflicts={} links={} untracked={} skipped={}".format(
        len(plan.moves), len(plan.merges), len(plan.conflicts), len(plan.links),
        len(plan.untracked), len(plan.skipped)))


def apply(root, plan):
    today = datetime.date.today().isoformat()
    for _, src, dst in plan.moves:
        root.makedirs(posixpath.dirname(dst))
        git(root, "mv", "--", src, dst)
    for _, src, _ in plan.conflicts:
        q = plan.quarantine[src]
        root.makedirs(posixpath.dirname(q))
        git(root, "mv", "--", src, q)
    for _, new, text in plan.links:
        root.write(new, text)
    if plan.merges:
        root.makedirs(posixpath.dirname(plan.merge_target))
        root.write(plan.merge_target, merged_index(plan, today), create=True)
        for key, src, _ in plan.merges:
            root.write(src, with_banner(plan.merge_sources[key], src, plan.merge_target))
    set_layout(root, "gated")


def set_layout(root, value):
    data = _project(root)
    if data is None:
        raise Refuse("not a bound project — run `devteam bind` first")
    data["docs_layout"] = value
    project.validate(data, source=str(project.project_file(root.path)))
    jsonio.write_json_atomic(
        project.project_file(root.path), data, mode=jsonio.PROJECT_FILE_MODE, dir_mode=None
    )
    print("LAYOUT", value)


def main(argv):
    parser = argparse.ArgumentParser(prog="docs-migrate.py", description=__doc__.split("\n")[0])
    parser.add_argument("--root", default=".", help="project root (default: the current directory)")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("plan", help="dry run: print the plan, change nothing (default)")
    sub.add_parser("apply", help="recompute the plan and execute it")
    layout = sub.add_parser("set-layout", help="record docs_layout in project.json")
    layout.add_argument("value", choices=list(project.docs_layouts()))
    args = parser.parse_args(argv)
    root = Root(args.root)
    try:
        if args.command == "set-layout":
            set_layout(root, args.value)
            return 0
        plan = build_plan(root)
        print_plan(plan)
        if args.command == "apply":
            apply(root, plan)
            print("APPLIED")
    except Refuse as exc:
        print("REFUSE", exc)
        return 1
    except Exception as exc:  # noqa: BLE001 — EnvError from the store layer, an OSError mid-apply
        print("REFUSE", "{}: {}".format(type(exc).__name__, exc))
        if args.command == "apply":
            print("REFUSE", "apply stopped part-way — `git status` shows what changed; nothing is committed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
