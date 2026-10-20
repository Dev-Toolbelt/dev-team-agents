"""The sprint backlog read as a graph: ready frontier, computed waves, lint, claims and prime (ADR-0044).

The sprint files under ``docs/backlog/sprints/`` stay the **only** source of truth for a task's
status — ``[ ]`` / ``[~]`` / ``[x]``, committed in git (``skills/shared/backlog-template``). This
module never writes them. It reads ``Depends on`` / ``Wave`` / ``Status`` and derives what the
agent used to work out by eye: which tasks are ready, the waves the dependency graph implies, and
the defects (a cycle, an unknown dependency, a dependency in the same or a later wave).

The one piece of state it owns is the **claim** record, ``backlog-claims.json`` in the project's
machine-local state directory (ADR-0013): which orchestrator is working a task on this machine
right now. A claim is advisory and expires (``DEFAULT_TTL``); an expired claim is free. Claims are
keyed to the main checkout, never to a worktree, so a sprint run from its integration worktree and
a hook in the main checkout read the same record. A released claim is kept, marked, and only the
oldest released ones are dropped past ``MAX_CLAIMS`` — an open claim is never dropped.
"""

from __future__ import annotations

import os
import re
import secrets
import stat
import subprocess
import time
import unicodedata
from pathlib import Path

from . import jsonio, lock, project
from .errors import ConflictError, DevteamError, EnvError, UsageError

SCHEMA = 1
CLAIMS_FILE = "backlog-claims.json"
SPRINTS_DIR = Path("docs") / "backlog" / "sprints"
INDEX_FILE = "sprints.md"
#: A claim lives this long unless it is renewed; a wave renews it when it starts.
DEFAULT_TTL = 4 * 3600
MAX_TTL = 7 * 24 * 3600
MAX_CLAIMS = 200
#: Entries this release cannot read that a rewrite carries over, newest kept.
MAX_FOREIGN_ENTRIES = 50
#: A sprint file larger than this is not a sprint file; it is read no further.
MAX_FILE_BYTES = 1024 * 1024
#: Lines and bytes `prime` prints at most: it lands in every compacted context, so it must stay small.
PRIME_MAX_LINES = 24
PRIME_MAX_BYTES = 4096
LOCK_TIMEOUT = 5.0

STATUSES = ("pending", "in_progress", "done", "unknown")
_TASK_ID = re.compile(r"\bTASK-\d+\b")
_TASK_HEAD = re.compile(r"^### (?=TASK-\d+)", re.M)
_FIELD = re.compile(r"^\*\*(?P<key>[A-Za-z ]+)\*\*:[ \t]*(?P<value>.*)$", re.M)
# One character class and a literal, so a row is matched in linear time; whether its cells name a
# task is checked afterwards. `[^|]*TASK-\d+[^|]*` backtracked quadratically on a crafted line.
_PLAN_ROW = re.compile(r"^\|[ \t]*(?P<wave>[A-Za-z0-9]{1,16})[ \t]*\|(?P<tasks>[^|\n]*)\|", re.M)
_SPEC_REF = re.compile(r"docs/specs/[A-Za-z0-9._/-]+\.md")
_PLAN_HEAD = re.compile(r"^#{1,3}[ \t]+Parallel Execution Plan\b.*$", re.M | re.I)
_ANY_HEAD = re.compile(r"^#{1,3}[ \t]", re.M)
_SPRINT_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_OWNER = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_SPRINT_SCOPE = re.compile(r"^(?P<scope>.+)-sprint-\d+$")


# ── reading ─────────────────────────────────────────────────────────────────


def _safe(value, limit=80):
    """``value`` as one line of plain text: no control, format, line or paragraph separators.

    Sprint text reaches the agent's context through `prime`, so a character that renders as a
    line break (U+2028, NEL) or hides text (bidi, zero-width) could fake a line of its own.
    """
    text = "".join(
        " " if unicodedata.category(ch) in ("Cc", "Cf", "Zl", "Zp") else ch for ch in str(value)
    )
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def sprints_dir(root):
    return Path(root) / SPRINTS_DIR


def _contained_sprints_dir(root):
    """``sprints_dir(root)`` resolved, or ``None`` when a symlinked parent leads out of the checkout."""
    directory = sprints_dir(root)
    try:
        resolved = directory.resolve()
        resolved.relative_to(Path(root).resolve())
    except (OSError, ValueError):
        return None
    return resolved


def _status(value):
    match = re.match(r"\s*\[(.)\]", value or "")
    if not match:
        return "unknown"
    return {" ": "pending", "~": "in_progress", "x": "done", "X": "done"}.get(match.group(1), "unknown")


def _scope(path):
    match = _SPRINT_SCOPE.match(Path(path).stem)
    return match.group("scope") if match else None


def _read(path):
    """The file's text, or ``None`` when it is not a regular file we are willing to read."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        if Path(path).is_symlink():
            return None
        fd = os.open(str(path), flags)
    except OSError:
        return None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
            return None
        with os.fdopen(fd, "rb") as handle:
            fd = None
            data = handle.read(MAX_FILE_BYTES + 1)
    except OSError:
        return None
    finally:
        if fd is not None:
            os.close(fd)
    if len(data) > MAX_FILE_BYTES:
        return None
    return data.decode("utf-8", errors="replace")


def read_text(path):
    """The guarded read other modules use: no symlink, a regular file, at most ``MAX_FILE_BYTES``."""
    return _read(path)


def parse(text):
    """``{"waves": [...], "tasks": [...]}`` from one sprint file's text. Never raises.

    The one reader of the sprint task block: `scripts/lib/spec_lint.py` reads `Spec` / `Covers`
    through it too, so the two checks can never disagree on where a task's fields end.
    """
    waves = []
    # Only the Parallel Execution Plan's rows name waves; another table that mentions a task
    # (a summary, an agent assignment) is not one. A file without the heading is read whole.
    plan = text
    head_match = _PLAN_HEAD.search(text)
    if head_match:
        rest = text[head_match.end():]
        nxt = _ANY_HEAD.search(rest)
        plan = rest[: nxt.start()] if nxt else rest
    for row in _PLAN_ROW.finditer(plan):
        if not _TASK_ID.search(row.group("tasks")):
            continue
        if row.group("wave") not in waves and row.group("wave").lower() != "wave":
            waves.append(row.group("wave"))
    tasks = []
    for block in _TASK_HEAD.split(text)[1:]:
        head, _, body = block.partition("\n")
        # A task's fields end at the next heading: a later `## Sprint Summary` must not lend it a Wave.
        nxt = _ANY_HEAD.search(body)
        if nxt:
            body = body[: nxt.start()]
        ident = _TASK_ID.match(head)
        if not ident:
            continue
        name = re.sub(r"^\s*[—–-]\s*", "", head[ident.end():]).strip()
        fields = {}
        for field in _FIELD.finditer(body):
            fields.setdefault(field.group("key").strip().lower(), field.group("value").strip())
        depends_raw = fields.get("depends on", "")
        depends = []
        for dep in _TASK_ID.findall(depends_raw):
            if dep not in depends:
                depends.append(dep)
        note = None
        if not depends and depends_raw and not re.match(r"^\W*none\b", depends_raw, re.I):
            note = _safe(depends_raw, 120)
        tasks.append(
            {
                "id": ident.group(0),
                "name": _safe(name, 120),
                "wave": _safe(fields["wave"], 16) if fields.get("wave") else None,
                "agent": _safe(fields["agent"], 64) if fields.get("agent") else None,
                "branch": _safe(fields["worktree branch"].strip("` "), 120) if fields.get("worktree branch") else None,
                "covers": re.findall(r"\bS\d+\b", fields.get("covers", "")),
                # Read from the raw field, before any truncation: spec-lint checks each one exists.
                "spec_refs": _SPEC_REF.findall(fields.get("spec", "")),
                "depends_on": depends,
                "external_note": note,
                "status": _status(fields.get("status")),
            }
        )
    return {"waves": waves, "tasks": tasks}


def sprint_files(root):
    """Every sprint file in the project, sorted; the status index is not one."""
    directory = _contained_sprints_dir(root)
    if directory is None:
        return []
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return []
    return [directory / n for n in names if n.endswith(".md") and n != INDEX_FILE]


def resolve_sprint(root, ref):
    """The sprint file ``ref`` names: a path inside ``docs/backlog/sprints/`` or a bare stem."""
    if not isinstance(ref, str) or not ref.strip():
        raise UsageError("a sprint is required")
    directory = _contained_sprints_dir(root)
    if directory is None:
        raise UsageError("{} leads outside the checkout".format(SPRINTS_DIR.as_posix()))
    ref = ref.strip()
    if _SPRINT_NAME.match(ref):
        candidate = directory / "{}.md".format(ref)
    else:
        given = Path(ref)
        if given.is_absolute():
            candidate = given.resolve()
        else:
            # Relative to where the user ran the command, else to the project root.
            candidate = (Path.cwd() / given).resolve()
            try:
                candidate.relative_to(directory)
            except ValueError:
                candidate = (Path(root) / given).resolve()
    try:
        candidate.relative_to(directory)
    except ValueError:
        raise UsageError(
            "{} is not inside {}".format(_safe(ref), SPRINTS_DIR.as_posix()),
            hint="Name the sprint by its file stem (e.g. auth-sprint-1) or its path under docs/backlog/sprints/.",
        )
    if candidate.name == INDEX_FILE or candidate.suffix != ".md" or _read(candidate) is None:
        raise UsageError("no sprint file {}".format(_safe(ref)))
    return candidate


def load_all(root):
    """``{path: parsed}`` for every readable sprint file in the project."""
    out = {}
    for path in sprint_files(root):
        text = _read(path)
        if text is not None:
            out[path] = parse(text)
    return out


def _rel(root, path):
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return Path(path).name


# ── the graph ───────────────────────────────────────────────────────────────


def _lookup(dep, path, everything):
    """Status of ``dep`` outside ``path``: same-scope sprints first, then any. ``None`` if unknown."""
    scope = _scope(path)
    same, other = [], []
    for other_path, parsed in everything.items():
        if other_path == path:
            continue
        for task in parsed["tasks"]:
            if task["id"] == dep:
                (same if _scope(other_path) == scope else other).append(task["status"])
    found = same or other
    if not found:
        return None
    return "done" if all(s == "done" for s in found) else "open"


def _cycles(tasks):
    """Each dependency cycle once, as ``[a, b, …, a]``. Iterative: a long chain is not a recursion limit."""
    graph = {t["id"]: [d for d in t["depends_on"] if d != t["id"]] for t in tasks}
    done, found, keys = set(), [], set()
    for start in graph:
        if start in done:
            continue
        path, on_path, iters = [start], {start}, [iter(graph[start])]
        while iters:
            nxt = next(iters[-1], None)
            if nxt is None:
                node = path.pop()
                on_path.discard(node)
                done.add(node)
                iters.pop()
                continue
            if nxt in on_path:
                cycle = path[path.index(nxt):]
                key = frozenset(cycle)
                if key not in keys:
                    keys.add(key)
                    found.append(cycle + [nxt])
            elif nxt in graph and nxt not in done:
                path.append(nxt)
                on_path.add(nxt)
                iters.append(iter(graph[nxt]))
    return found


def analyze(root, path, everything=None, claims=None, now=None):
    """The ready frontier, the computed waves and the per-task state of one sprint file."""
    everything = everything if everything is not None else load_all(root)
    parsed = everything.get(path)
    if parsed is None:
        text = _read(path)
        parsed = parse(text) if text is not None else {"waves": [], "tasks": []}
    now = time.time() if now is None else now
    local = {t["id"]: t for t in parsed["tasks"]}
    live = {c["task"]: c for c in (claims or []) if c["sprint"] == Path(path).name and _live(c, now)}

    def dep_state(dep):
        if dep in local:
            return "done" if local[dep]["status"] == "done" else "open"
        return _lookup(dep, path, everything) or "unknown"

    rows = []
    for task in parsed["tasks"]:
        open_deps = [d for d in task["depends_on"] if d != task["id"] and dep_state(d) != "done"]
        claim = live.get(task["id"])
        # An open blocker outranks a claim: the claimer can only start the task once it clears.
        if task["status"] == "done":
            state = "done"
        elif open_deps:
            state = "blocked"
        elif claim is not None:
            state = "claimed"
        elif task["status"] == "in_progress":
            state = "in_progress"
        else:
            state = "ready"
        row = dict(task, state=state, blocked_by=open_deps)
        row["claim"] = _public_claim(claim, now) if claim else None
        rows.append(row)

    # Kahn layering over the tasks still to do; a dependency already done, or outside the
    # file, does not hold a layer back (an open external one keeps its task `blocked`).
    # A task held by an open dependency outside the file is not placeable in any layer.
    # So is anything that depends on such a task, however indirectly.
    open_rows = {r["id"]: r for r in rows if r["state"] != "done"}
    held = {i for i, r in open_rows.items() if any(d not in local for d in r["blocked_by"])}
    grew = True
    while grew:
        grew = False
        for i, r in open_rows.items():
            if i not in held and any(d in held for d in r["depends_on"]):
                held.add(i)
                grew = True
    todo = {i: r for i, r in open_rows.items() if i not in held}
    pending = {i: {d for d in r["depends_on"] if d in todo and d != i} for i, r in todo.items()}
    layers = []
    while pending:
        layer = sorted(i for i, deps in pending.items() if not deps)
        if not layer:
            break
        layers.append(layer)
        for i in layer:
            pending.pop(i)
        for deps in pending.values():
            deps.difference_update(layer)
    return {
        "sprint": _rel(root, path),
        "declared_waves": parsed["waves"],
        "tasks": rows,
        "ready": [r["id"] for r in rows if r["state"] == "ready"],
        "in_progress": [r["id"] for r in rows if r["state"] in ("in_progress", "claimed")],
        "blocked": [r["id"] for r in rows if r["state"] == "blocked"],
        "done": [r["id"] for r in rows if r["state"] == "done"],
        "computed_waves": layers,
        "unlayered": sorted(set(pending) | set(held)),
        "in_cycle": sorted({i for cycle in _cycles([r for r in rows if r["state"] != "done"]) for i in cycle}),
    }


def lint_file(root, path, everything=None):
    """Findings for one sprint file: ``{"level", "sprint", "task", "message"}``."""
    everything = everything if everything is not None else load_all(root)
    parsed = everything.get(path) or parse(_read(path) or "")
    sprint = _rel(root, path)
    findings = []

    def add(level, task, message):
        findings.append({"level": level, "sprint": sprint, "task": task, "message": message})

    ids = [t["id"] for t in parsed["tasks"]]
    for ident in sorted({i for i in ids if ids.count(i) > 1}):
        add("ERROR", ident, "{} is defined more than once".format(ident))
    local = {t["id"]: t for t in parsed["tasks"]}
    order = {w: n for n, w in enumerate(parsed["waves"])}
    branches = {}
    for task in parsed["tasks"]:
        if task["status"] == "unknown":
            add("WARN", task["id"], "Status is not one of [ ], [~], [x]")
        if not task["wave"]:
            add("WARN", task["id"], "no Wave field")
        elif not order:
            add("ERROR", task["id"], "Wave {} but the file has no Parallel Execution Plan rows".format(task["wave"]))
        elif task["wave"] not in order:
            add("ERROR", task["id"], "Wave {} is not a row of the Parallel Execution Plan".format(_safe(task["wave"], 16)))
        if task["branch"]:
            branches.setdefault(task["branch"], []).append(task["id"])
        for dep in task["depends_on"]:
            if dep == task["id"]:
                add("ERROR", task["id"], "depends on itself")
                continue
            if dep not in local:
                if _lookup(dep, path, everything) is None:
                    add("ERROR", task["id"], "depends on {}, which no sprint file defines".format(dep))
                continue
            mine, theirs = order.get(task["wave"]), order.get(local[dep]["wave"])
            if mine is not None and theirs is not None and theirs >= mine:
                add("ERROR", task["id"], "depends on {} in wave {}, which is not an earlier wave".format(dep, local[dep]["wave"]))
    for branch, owners in sorted(branches.items()):
        if len(owners) > 1:
            add("ERROR", owners[1], "Worktree branch {} is shared by {}".format(_safe(branch, 60), ", ".join(owners)))
    for cycle in _cycles(parsed["tasks"]):
        add("ERROR", cycle[0], "dependency cycle: {}".format(" → ".join(cycle)))
    return findings


# ── claims ──────────────────────────────────────────────────────────────────

#: Inherited git overrides would point these lookups at another repository's state (ADR-0043).
_GIT_OVERRIDES = ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY")


def _git(args, cwd):
    env = {k: v for k, v in os.environ.items() if k not in _GIT_OVERRIDES}
    try:
        out = subprocess.run(
            ["git"] + args, cwd=str(cwd), env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=False, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.decode("utf-8", "replace") if out.returncode == 0 else None


def main_root(root):
    """The main checkout of ``root``'s repository: claims are keyed there, never to a worktree."""
    common = (_git(["rev-parse", "--git-common-dir"], root) or "").strip()
    if not common:
        return Path(root)
    common_path = Path(common) if Path(common).is_absolute() else Path(root) / common
    main = common_path.resolve().parent
    return main if project.project_file(main).exists() else Path(root)


def claims_path(root):
    base = main_root(root)
    return Path(project.state_dir(base)) / CLAIMS_FILE


def _live(claim, now):
    return claim.get("released_at") is None and isinstance(claim.get("expires_at"), (int, float)) and claim["expires_at"] > now


def owner_hint(owner):
    """Enough of an owner token to recognise it, not enough to reuse it from another session."""
    return owner if len(owner) <= 8 else owner[:8] + "…"


def _public_claim(claim, now):
    return {
        "task": claim["task"],
        "sprint": claim["sprint"],
        "owner_hint": owner_hint(claim["owner"]),
        "claimed_at": claim["claimed_at"],
        "expires_at": claim["expires_at"],
        "expires_in": max(0, int(claim["expires_at"] - now)),
    }


def _valid(claim):
    return (
        isinstance(claim, dict)
        and all(isinstance(claim.get(k), str) for k in ("task", "sprint", "owner"))
        and bool(_TASK_ID.fullmatch(claim["task"]))
        and bool(_OWNER.match(claim["owner"]))
        and isinstance(claim.get("claimed_at"), (int, float))
        and isinstance(claim.get("expires_at"), (int, float))
    )


def _load_claims(path):
    """The valid claims for a read; anything unreadable reads as no claims."""
    try:
        data = jsonio.read_json(path)
    except (DevteamError, OSError, ValueError):
        return []
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or not isinstance(data.get("claims"), list):
        return []
    return [c for c in data["claims"] if _valid(c)]


def _load_for_write(path):
    """``(valid, other)`` entries for a rewrite. A file this release cannot read is refused, never
    overwritten: it may hold another owner's live claims or come from a newer CLI."""
    if not path.is_file():
        return [], []
    try:
        data = jsonio.read_json(path)
    except (DevteamError, OSError, ValueError):
        data = None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or not isinstance(data.get("claims"), list):
        raise EnvError(
            "{} is unreadable or from a newer release; it was left untouched".format(path),
            hint="Upgrade the devteam CLI, or move the file aside if it is corrupt.",
        )
    valid = [c for c in data["claims"] if _valid(c)]
    # Kept as written, but bounded: entries nothing here can read cannot grow the file forever.
    return valid, [c for c in data["claims"] if not _valid(c)][-MAX_FOREIGN_ENTRIES:]


def read_claims(root):
    path = claims_path(root)
    return _load_claims(path) if path.is_file() else []


def _cap(claims):
    if len(claims) <= MAX_CLAIMS:
        return claims
    released = sorted((c for c in claims if c.get("released_at") is not None), key=lambda c: c["released_at"])
    drop = {id(c) for c in released[: len(claims) - MAX_CLAIMS]}
    return [c for c in claims if id(c) not in drop]


def _locked(root):
    path = claims_path(root)
    return path, lock.Lock(str(path)[: -len(".json")] + ".lock", timeout=LOCK_TIMEOUT, stale_after=30.0)


def new_owner():
    return "own-{}".format(secrets.token_hex(6))


def claim(root, sprint_ref, task_ids, owner=None, ttl=DEFAULT_TTL, take_over=False, now=None):
    """Claim every task in ``task_ids`` for ``owner``, all or none. Renews the owner's own claims."""
    now = time.time() if now is None else now
    if owner is not None and not _OWNER.match(owner):
        raise UsageError("--owner must match {}".format(_OWNER.pattern))
    if not isinstance(ttl, int) or not 60 <= ttl <= MAX_TTL:
        raise UsageError("--ttl must be between 60 and {} seconds".format(MAX_TTL))
    path = resolve_sprint(root, sprint_ref)
    known = {t["id"]: t for t in parse(_read(path) or "")["tasks"]}
    wanted = []
    for ident in task_ids:
        if not _TASK_ID.fullmatch(ident or ""):
            raise UsageError("{} is not a task id".format(_safe(ident, 20)))
        if ident not in known:
            raise UsageError("{} is not a task of {}".format(ident, path.name))
        if known[ident]["status"] == "done":
            raise UsageError("{} is already done".format(ident))
        if ident not in wanted:
            wanted.append(ident)
    if not wanted:
        raise UsageError("at least one task id is required")
    if not project.load(main_root(root)):
        raise EnvError(
            "claims need a bound project",
            hint="Run `devteam bind` in this repository first; `devteam backlog ready` works without one.",
        )
    owner = owner or new_owner()
    file_path, guard = _locked(root)
    with guard:
        claims, other = _load_for_write(file_path)
        foreign = [
            c for c in claims
            if c["sprint"] == path.name and c["task"] in wanted and _live(c, now) and c["owner"] != owner
        ]
        if foreign and not take_over:
            raise ConflictError(
                "{} already claimed by another orchestrator".format(", ".join(sorted(c["task"] for c in foreign))),
                hint="Another session may be running this sprint. Pass --take-over only after the user chose to take it over.",
                details={"claims": [_public_claim(c, now) for c in foreign]},
            )
        for c in claims:
            if c["sprint"] == path.name and c["task"] in wanted and c.get("released_at") is None:
                c["released_at"] = now
                if c["owner"] == owner:
                    c["released_reason"] = "renewed"
                else:
                    c["released_reason"] = "taken_over" if _live(c, now) else "expired"
        fresh = [
            {"task": t, "sprint": path.name, "owner": owner, "claimed_at": now, "expires_at": now + ttl, "released_at": None}
            for t in wanted
        ]
        claims = _cap(claims + fresh)
        jsonio.write_json_atomic(file_path, {"schema": SCHEMA, "claims": claims + other})
    return {
        "sprint": _rel(root, path),
        "owner": owner,
        "claimed": [_public_claim(c, now) for c in fresh],
        "taken_over": [_public_claim(c, now) for c in foreign],
    }


def release(root, sprint_ref, task_ids, owner, now=None):
    """Release ``owner``'s live claims on ``task_ids`` (every task of the sprint when empty)."""
    now = time.time() if now is None else now
    if not owner or not _OWNER.match(owner):
        raise UsageError("--owner is required and must match {}".format(_OWNER.pattern))
    path = resolve_sprint(root, sprint_ref)
    file_path, guard = _locked(root)
    released = []
    with guard:
        claims, other = _load_for_write(file_path)
        for c in claims:
            if c["sprint"] != path.name or c["owner"] != owner or c.get("released_at") is not None:
                continue
            if task_ids and c["task"] not in task_ids:
                continue
            c["released_at"] = now
            c["released_reason"] = "released"
            released.append(c["task"])
        if released:
            jsonio.write_json_atomic(file_path, {"schema": SCHEMA, "claims": claims + other})
    return {"sprint": _rel(root, path), "owner": owner, "released": sorted(released)}


# ── prime ───────────────────────────────────────────────────────────────────


def _index_in_progress(root):
    """Sprint stems the status index marks ``In progress``."""
    directory = _contained_sprints_dir(root)
    text = _read(directory / INDEX_FILE) if directory is not None else None
    text = text or ""
    stems = set()
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[-1].lower() != "in progress":
            continue
        linked = [Path(t).stem for t in re.findall(r"\]\(([^()\s]+\.md)\)", line)]
        if linked:
            stems.update(linked)
            continue
        number = re.search(r"\bsprint-(\d+)\b", cells[1])
        if number:
            scope = cells[0]
            stems.add("sprint-{}".format(number.group(1)) if scope in ("", "legacy") else "{}-sprint-{}".format(scope, number.group(1)))
    return stems


def _worktrees(root):
    """``(path, branch)`` of each checkout of this repository."""
    out = []
    path = None
    for line in (_git(["worktree", "list", "--porcelain"], root) or "").splitlines():
        if line.startswith("worktree "):
            path = Path(line[len("worktree "):])
            out.append((path, ""))
        elif line.startswith("branch ") and path is not None:
            out[-1] = (path, line[len("branch "):])
    return out


def prime(root, now=None):
    """A short block of the active sprint work for a compacted or resumed context; ``None`` if idle."""
    now = time.time() if now is None else now
    base = main_root(root)
    claims = read_claims(base)
    live = [c for c in claims if _live(c, now)]
    claimed_sprints = {c["sprint"] for c in live}
    # A running sprint keeps its status in its integration worktree, so the newest copy of a
    # claimed sprint file is read from whichever checkout of this repository has it.
    candidates = {}
    checkouts, branches = [], {}
    for checkout, branch in [(base, "")] + _worktrees(base):
        if checkout.resolve() not in [c.resolve() for c in checkouts]:
            checkouts.append(checkout)
            branches[checkout] = branch
    # /devteam:sprint flips a sprint to In progress in its integration worktree's index, so every
    # checkout's index counts — a claim that expired mid-wave must not hide a running sprint.
    active = set()
    for checkout in checkouts:
        active |= _index_in_progress(checkout)
    for checkout in checkouts:
        for path in sprint_files(checkout):
            if path.stem in active or path.name in claimed_sprints:
                candidates.setdefault(path.name, []).append((checkout, path))
    parsed_by_checkout = {}
    sprints = []
    for name, copies in sorted(candidates.items()):
        # The copy furthest along by its own statuses wins; on a tie a claimed sprint is read
        # from a worktree, because /devteam:sprint edits status in its integration worktree.
        best = None
        for checkout, path in copies:
            if checkout not in parsed_by_checkout:
                parsed_by_checkout[checkout] = load_all(checkout)
            view = analyze(checkout, path, parsed_by_checkout[checkout], live, now)
            statuses = [t["status"] for t in view["tasks"]]
            in_worktree = name in claimed_sprints and checkout.resolve() != base.resolve()
            # On a tie the integration worktree (`sprint/<scope>-<n>`) beats a per-task one.
            score = (
                statuses.count("done") + statuses.count("in_progress"),
                in_worktree,
                in_worktree and branches.get(checkout, "").startswith("refs/heads/sprint/"),
            )
            if best is None or score > best[0]:
                best = (score, checkout, view)
        _, checkout, view = best
        if not view["in_progress"] and not view["ready"] and not view["blocked"]:
            continue
        view["checkout"] = str(checkout)
        sprints.append(view)
    if not sprints:
        return None
    return {"sprints": sprints, "claims": [_public_claim(c, now) for c in live]}


def prime_text(result):
    """The ``[DEVTEAM:ACTIVE_WORK]`` block, capped in lines and bytes. Task names are quoted:
    they are text from a sprint file, data for the agent, never an instruction."""
    lines = ["[DEVTEAM:ACTIVE_WORK]"]
    for view in result["sprints"]:
        by_id = {t["id"]: t for t in view["tasks"]}
        lines.append("Sprint {} ({} done, {} in progress, {} ready, {} blocked) — checkout {}".format(
            _safe(view["sprint"], 120), len(view["done"]), len(view["in_progress"]), len(view["ready"]),
            len(view["blocked"]), _safe(view["checkout"], 200)))
        for ident in view["in_progress"]:
            task = by_id[ident]
            claim_note = ""
            if task["claim"]:
                claim_note = " · claimed by {} ({}m left)".format(task["claim"]["owner_hint"], task["claim"]["expires_in"] // 60)
            lines.append('  in progress {} name="{}" [{} · wave {} · covers {}]{}'.format(
                ident, task["name"].replace('"', "'"), task["agent"] or "?", task["wave"] or "?",
                ",".join(task["covers"]) or "—", claim_note))
        if view["ready"]:
            lines.append("  ready next: {}".format(", ".join(view["ready"][:8])))
        for ident in view["blocked"][:4]:
            lines.append("  blocked {} by {}".format(ident, ", ".join(by_id[ident]["blocked_by"])))
    tail = "Resume with the devteam sprint command; status lives in the sprint file, claims in `devteam backlog ready`."
    more = "  … (`devteam backlog ready` for the rest)"
    # The tail line always follows, and a truncated block also gets `more`: both count.
    body = lines[: PRIME_MAX_LINES - 2] if len(lines) > PRIME_MAX_LINES - 1 else lines
    truncated = len(lines) > PRIME_MAX_LINES - 1
    while len("\n".join(body + [more, tail]).encode("utf-8")) > PRIME_MAX_BYTES and len(body) > 1:
        body.pop()
        truncated = True
    return "\n".join(body + ([more] if truncated else []) + [tail])
