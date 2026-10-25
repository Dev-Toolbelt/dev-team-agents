"""Repair ledger (ADR-0050, spec docs/specs/repair-ledger.md).

A shell command fails (non-zero) and, within the next 10 shell calls, the same command signature
succeeds *with a delta*: an env var set, a flag added, a wrapper from a fixed list prepended, or
another program's step run first. That pair is a repair; it is stored in the machine-local
``repair-ledger.json`` and replayed as a context hint the next time the signature fails.

Hook-only entry, no CLI surface::

    python3 -I -c '...; from devteam import repairs; repairs.main(argv)' \\
        --state-dir <dir> --session <id>            (PostToolUse payload JSON on stdin)

It prints the hint lines to deliver (plain text, no prefix), one per line. The shell side enqueues
them on the context-hints channel, or emits them as PostToolUse context. Any error prints nothing
and exits 0: a hook never disturbs the provider.

Two records live in the machine-local state directory:

* ``repair-ledger.json``            -- ``{"schema": 1, "repairs": [{sig, delta, kinds, count, ...}]}``
* ``.repair-window-<session>.json`` -- the rolling window of recent shell calls; it exists only while
  an eligible failure is waiting for its retry, so a session that never fails never has one.

Both are written under a lock and atomically. Only option *names* are kept for flags (``-p``, never
``-pSECRET``; ``--name`` without ``=value``), env values are dropped when the name or value could be a
secret, and everything stored or printed also passes through the task-board secret patterns
(``tasks.redact``).
"""

import json
import os
import re
import shlex
import sys
import time
from pathlib import Path

from . import jsonio, lock
from .tasks import _INVISIBLE, redact

LEDGER_FILE = "repair-ledger.json"
WINDOW_PREFIX = ".repair-window-"
SCHEMA = 1
WINDOW_CALLS = 10
MAX_LEDGER = 200
LOCK_TIMEOUT = 2.0
LOCK_STALE = 30.0
WINDOW_MAX_AGE = 24 * 3600
MAX_COMMAND = 20000
MAX_HINT = 280

_SESSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_SECRET_NAME = re.compile(r"(?i)(key|token|secret|pass|pwd|auth|cred|cookie|session|private|dsn|signature|salt)")
_SAFE_VALUE = re.compile(r"^[\w./:@+,=%-]{0,60}$")
_REDIRECT = {">", ">>", "<", "<<", "<<<", ">&", "<&", "&>", "&>>", ">|"}
_SEPARATORS = {"&&", "||", ";", "&", ";;", "(", ")"}

#: Wrappers that change how a command runs without changing which command it is (fixed list).
_WRAPPERS = (
    ("sudo",), ("rtk",), ("npx",), ("bunx",), ("time",), ("nice",), ("nohup",), ("command",), ("exec",),
    ("env",), ("bundle", "exec"), ("poetry", "run"), ("uv", "run"), ("pipenv", "run"),
    ("pnpm", "exec"), ("pnpm", "dlx"), ("yarn", "exec"), ("dotenv", "--"), ("mise", "exec", "--"),
    ("asdf", "exec"), ("direnv", "exec", "."),
)

#: Programs that only look; they never fail in a way worth teaching, nor repair anything.
_LOOK_PROGRAMS = frozenset(
    "ls ll la cat head tail less more grep egrep fgrep rg ag find fd echo printf pwd which whereis type "
    "wc stat file tree du df ps whoami id date uname hostname printenv true false test [ diff cmp jq "
    "sort uniq cut basename dirname realpath readlink sleep tput man help history zcat".split()
)
_LOOK_SUBCOMMANDS = {
    "git": frozenset(
        "status log diff show branch remote rev-parse ls-files blame describe tag shortlog reflog".split()
    ),
    "docker": frozenset("ps logs images inspect info version".split()),
    "kubectl": frozenset("get describe logs".split()),
    "npm": frozenset("ls list view outdated root bin".split()),
    "pip": frozenset("list show freeze".split()),
    "pip3": frozenset("list show freeze".split()),
    "brew": frozenset("list info".split()),
}
_GH_LOOK_VERBS = frozenset("view list status checks diff".split())
#: Not a command of its own: bookkeeping around the real one.
_SKIP_PROGRAMS = frozenset({"cd", "export", "set", "unset", "pushd", "popd", "alias", "umask", ":"})
#: Housekeeping steps that run between almost any failure and its retry; never "the fix".
_NOT_A_STEP = frozenset({"git"})

_HOST_DENY = re.compile(
    r"(?i)(blocked by .{0,40}hook|hook .{0,30}(denied|blocked|rejected)|PreToolUse.{0,40}(denied|blocked)"
    r"|permission (to use|for) .{0,30}(has been )?denied|user (doesn't|does not) want to"
    r"|(denied|rejected) by the user|\[devteam|credential-guard|tool use was rejected|requires approval"
    r"|not allowed to (run|use)|sandbox.{0,30}(denied|blocked))"
)
_SQL_GRAPHQL = re.compile(
    r"(?i)(SQLSTATE|syntax error at or near|ERROR:\s+(relation|column|syntax)|\bORA-\d{5}"
    r"|\bERROR \d{4} \(\w{5}\)|sqlite3?\.\w*Error|near \"[^\"]+\": syntax error|Unknown column|no such table"
    r"|GraphQL error|Cannot query field|\"errors\"\s*:\s*\[\s*\{[^}]*\"(message|extensions)\")"
)
_EXIT_TEXT = (
    re.compile(r"(?im)^\s*Exit code:?\s*(-?\d+)"),
    re.compile(r"(?i)process exited with code\s+(-?\d+)"),
    re.compile(r"(?i)exited with (?:code|status)\s+(-?\d+)"),
    re.compile(r"\"(?:exit_code|exitCode|returncode)\"\s*:\s*(-?\d+)"),
)
_EXIT_KEYS = ("exit_code", "exitCode", "returncode", "exit")


# ── parsing a shell command into a comparable shape ─────────────────────────


def _tokens(command):
    text = command.replace("\r", "\n").replace("\n", " ; ")
    try:
        lex = shlex.shlex(text, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        lex.commenters = ""
        return list(lex)
    except ValueError:
        return text.split()


def _segments(tokens):
    """First pipe stage of each ``&&``/``||``/``;`` segment, redirections dropped."""
    segments, current, tail, i = [], [], False, 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in _SEPARATORS:
            if current:
                segments.append(current)
            current, tail = [], False
        elif tok in ("|", "|&"):
            tail = True
        elif tok in _REDIRECT or re.fullmatch(r"\d*[<>]+&?\d*", tok):
            if tok in _REDIRECT and current and current[-1].isdigit():
                current.pop()
            i += 1
        elif not tail:
            current.append(tok)
        i += 1
    if current:
        segments.append(current)
    return segments


def _wrapper_at(tokens, i):
    for wrapper in _WRAPPERS:
        if tuple(tokens[i : i + len(wrapper)]) == wrapper:
            return wrapper
    return None


def _segment(tokens):
    env, wrappers, i = {}, [], 0

    def take_env():
        nonlocal i
        while i < len(tokens) and _ENV_ASSIGN.match(tokens[i]):
            name, _, value = tokens[i].partition("=")
            env[name] = value
            i += 1

    take_env()
    while i < len(tokens):
        wrapper = _wrapper_at(tokens, i)
        if wrapper is None:
            break
        wrappers.append(" ".join(wrapper))
        i += len(wrapper)
        if "--" not in wrapper:
            while i < len(tokens) and tokens[i].startswith("-"):
                i += 1
        take_env()
    rest = tokens[i:]
    if not rest:
        return {"env": env, "wrappers": wrappers, "program": "", "pos": [], "flags": [], "kind": "skip"}
    program = os.path.basename(rest[0])
    pos, flags, seen_flag = [], [], False
    for tok in rest[1:]:
        if tok.startswith("-") and len(tok) > 1:
            seen_flag = True
            flags.append(_flag_name(tok))
        elif not seen_flag and len(pos) < 3:
            pos.append(tok[:60])
    kind = "command"
    if program in _SKIP_PROGRAMS:
        kind = "skip"
    elif program in _LOOK_PROGRAMS or (program in _LOOK_SUBCOMMANDS and pos and pos[0] in _LOOK_SUBCOMMANDS[program]):
        kind = "look"
    elif program == "gh" and pos and (pos[0] == "run" or (len(pos) > 1 and pos[1] in _GH_LOOK_VERBS)):
        kind = "look"
    return {"env": env, "wrappers": wrappers, "program": program, "pos": pos, "flags": flags,
            "kind": kind, "rest": rest}


def _flag_name(tok):
    """The option name only: ``--name`` without ``=value``, ``-p`` for ``-pSECRET``/``-uuser:pw``.

    A single-dash flag longer than two characters may carry an attached value (a password, a token), so
    it is cut to its first letter; bundled booleans (``-rf``) lose their tail, which only makes the
    comparison coarser. The result still goes through ``redact`` before it is stored.
    """
    name = tok.split("=", 1)[0] if tok.startswith("--") else tok[:2]
    return redact(name)[:40]


def _env_entry(name, value):
    """``NAME=value`` for the ledger, the value dropped when it could be a secret."""
    if _SECRET_NAME.search(name) or not _SAFE_VALUE.match(value):
        return "{}=[redacted]".format(name)
    return redact("{}={}".format(name, value))


def parse_command(command):
    """The comparable shape of one shell call, or ``None`` when there is nothing to compare."""
    if not isinstance(command, str) or not command.strip() or len(command) > MAX_COMMAND:
        return None
    segments = [_segment(s) for s in _segments(_tokens(command))]
    global_env = {}
    commands = []
    for seg in segments:
        if seg["program"] == "export":
            for tok in seg.get("rest", [])[1:]:
                if _ENV_ASSIGN.match(tok):
                    name, _, value = tok.partition("=")
                    global_env[name] = value
        elif seg["kind"] != "skip":
            commands.append(seg)
    if not commands:
        return None
    real = [seg for seg in commands if seg["kind"] != "look"]
    primary = (real or commands)[-1]
    commands = commands[: commands.index(primary)]
    commands = commands + []
    env = dict(global_env)
    env.update(primary["env"])
    steps = []
    for seg in commands:
        if seg["kind"] == "look":
            continue
        steps.append(redact(" ".join([seg["program"]] + seg["pos"][:2]))[:80])
    sig = redact(" ".join([primary["program"]] + primary["pos"]))[:120]
    return {
        "sig": sig,
        "program": redact(primary["program"]),
        "env": {name: _env_entry(name, value) for name, value in env.items()},
        "wrappers": primary["wrappers"],
        "flags": sorted(set(primary["flags"])),
        "steps": steps,
        "look": primary["kind"] == "look",
    }


def delta_between(failed, retry, between=()):
    """What the retry has that the failed call lacked: ``(kinds, human-readable items)``."""
    kinds, items = [], []
    for name, entry in sorted(retry["env"].items()):
        if failed["env"].get(name) != entry:
            kinds.append("env")
            items.append("set {}".format(entry))
    added = [f for f in retry["flags"] if f not in failed["flags"]]
    if added:
        kinds.append("flag")
        items.append("added {}".format(" ".join(added[:4])))
    wrapped = [w for w in retry["wrappers"] if w not in failed["wrappers"]]
    if wrapped:
        kinds.append("wrapper")
        items.append("prefixed with {}".format(" ".join(wrapped)))
    steps = [s for s in retry["steps"] if s not in failed["steps"]]
    if steps:
        kinds.append("step")
        items.append("ran `{}` first".format(steps[-1]))
    elif between:
        kinds.append("step")
        items.append("ran `{}` in between".format(between[-1]))
    return list(dict.fromkeys(kinds)), items


# ── reading a hook payload ──────────────────────────────────────────────────


def _first(payload, keys):
    for container in (payload, payload.get("tool_input"), payload.get("args"), payload.get("input")):
        if isinstance(container, dict):
            for key in keys:
                if key in container:
                    return container[key]
    return None


def extract_command(payload):
    value = _first(payload, ("command", "cmd"))
    if isinstance(value, list):
        try:
            return shlex.join(str(v) for v in value)
        except (TypeError, ValueError):
            return None
    return value if isinstance(value, str) else None


def _response_parts(payload):
    """``(text, exit_code, failed_flag)`` from whichever result key the provider used."""
    failed = payload.get("hook_event_name") == "PostToolUseFailure"
    parts, code = [], None
    for key in ("tool_response", "tool_output", "output", "error", "result"):
        value = payload.get(key)
        if isinstance(value, dict):
            for ek in _EXIT_KEYS:
                if isinstance(value.get(ek), int) and not isinstance(value.get(ek), bool):
                    code = value[ek]
            if value.get("is_error") is True or value.get("isError") is True:
                failed = True
            for sub in ("stdout", "stderr", "output", "error", "text", "message"):
                if isinstance(value.get(sub), str):
                    parts.append(value[sub])
        elif isinstance(value, str):
            parts.append(value)
        if key == "error" and value:
            failed = True
    meta = payload.get("metadata")
    if isinstance(meta, dict):
        for ek in _EXIT_KEYS:
            if isinstance(meta.get(ek), int) and not isinstance(meta.get(ek), bool):
                code = meta[ek]
    for ek in _EXIT_KEYS:
        if code is None and isinstance(payload.get(ek), int) and not isinstance(payload.get(ek), bool):
            code = payload[ek]
    text = "\n".join(parts)[:8000]
    if code is None:
        for pattern in _EXIT_TEXT:
            match = pattern.search(text)
            if match:
                code = int(match.group(1))
                break
    return text, code, failed


def classify(payload):
    """``(ok, ignored)``: whether the call succeeded, and whether a failure is of an ignored kind."""
    text, code, flagged = _response_parts(payload)
    if payload.get("interrupted") is True:
        return False, True
    failed = flagged or (code is not None and code != 0)
    if code == 0 and not flagged:
        failed = False
    if not failed:
        return True, False
    return False, bool(_HOST_DENY.search(text) or _SQL_GRAPHQL.search(text))


# ── stores ──────────────────────────────────────────────────────────────────


def _window_path(state_dir, session):
    return Path(state_dir) / "{}{}.json".format(WINDOW_PREFIX, session)


def _sentinel_path(session):
    """Marks "this session has an open repair window" where bash can test it without resolving the state dir.

    ``03-repair-detect.sh`` runs on every shell call; resolving the machine-local state directory costs
    tens of milliseconds, so it first looks for this file (session ids are unique per session). A missing
    or stale sentinel is harmless: stale only costs the slow path once, missing only forgoes recording
    one repair.
    """
    base = (os.environ.get("TMPDIR") or "/tmp").rstrip("/") or "/tmp"
    return os.path.join(base, "devteam-repair-open-{}".format(session))


def _set_sentinel(session, present):
    path = _sentinel_path(session)
    try:
        if present:
            os.close(os.open(path, os.O_WRONLY | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600))
        else:
            os.unlink(path)
    except OSError:
        pass


def _locked(path):
    return lock.Lock(str(path)[: -len(".json")] + ".lock", timeout=LOCK_TIMEOUT, stale_after=LOCK_STALE)


def _read_window(path):
    try:
        data = jsonio.read_json(path, default=None)
    except Exception:
        data = None
    if isinstance(data, dict) and isinstance(data.get("calls"), list) and isinstance(data.get("seq"), int):
        return data
    return {"seq": 0, "calls": []}


def read_ledger(state_dir):
    try:
        data = jsonio.read_json(Path(state_dir) / LEDGER_FILE, default=None)
    except Exception:
        return []
    if isinstance(data, dict) and data.get("schema") == SCHEMA and isinstance(data.get("repairs"), list):
        return [r for r in data["repairs"] if isinstance(r, dict) and isinstance(r.get("sig"), str)]
    return []


def _record_repair(state_dir, sig, kinds, items, now):
    """Add or refresh one entry. A ledger this release cannot read is left untouched."""
    path = Path(state_dir) / LEDGER_FILE
    with lock.Lock(Path(state_dir) / ".repair-ledger.lock", timeout=LOCK_TIMEOUT, stale_after=LOCK_STALE):
        data = jsonio.read_json(path, default=None)
        if data is None:
            data = {"schema": SCHEMA, "repairs": []}
        if not (isinstance(data, dict) and data.get("schema") == SCHEMA and isinstance(data.get("repairs"), list)):
            return False
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        for entry in data["repairs"]:
            if isinstance(entry, dict) and entry.get("sig") == sig:
                entry.update(delta=items, kinds=kinds, last_seen=stamp, count=int(entry.get("count") or 0) + 1)
                break
        else:
            data["repairs"].append(
                {"sig": sig, "delta": items, "kinds": kinds, "count": 1, "first_seen": stamp, "last_seen": stamp}
            )
        if len(data["repairs"]) > MAX_LEDGER:
            data["repairs"].sort(key=lambda r: str(r.get("last_seen") or ""), reverse=True)
            del data["repairs"][MAX_LEDGER:]
        jsonio.write_json_atomic(path, data)
    return True


def _sweep_windows(state_dir, now):
    try:
        names = os.listdir(state_dir)
    except OSError:
        return
    for name in names:
        if name.startswith(WINDOW_PREFIX) and name.endswith(".json"):
            full = os.path.join(state_dir, name)
            try:
                if now - os.stat(full).st_mtime > WINDOW_MAX_AGE:
                    os.unlink(full)
            except OSError:
                pass


def hint_line(entry):
    text = "`{}` failed before; what fixed it: {} (may not apply here)".format(
        entry["sig"], "; ".join(str(d) for d in entry.get("delta") or []) or "unknown"
    )
    return redact(_INVISIBLE.sub(" ", text))[:MAX_HINT]


# ── the detector ────────────────────────────────────────────────────────────


def process(state_dir, session, payload, now=None):
    """Fold one shell call into the window; return the hint lines to deliver (possibly none)."""
    now = time.time() if now is None else now
    if not _SESSION.fullmatch(session or "") or not isinstance(payload, dict):
        return []
    info = parse_command(extract_command(payload))
    if info is None:
        return []
    ok, ignored = classify(payload)
    path = _window_path(state_dir, session)
    eligible = (not ok) and (not ignored) and not info["look"]
    if not eligible and not path.exists():
        _set_sentinel(session, False)
        return []
    hints = []
    with _locked(path):
        window = _read_window(path)
        seq = window["seq"] + 1
        calls = [c for c in window["calls"] if seq - int(c.get("seq", 0)) <= WINDOW_CALLS]
        if eligible:
            for entry in read_ledger(state_dir):
                if entry["sig"] == info["sig"]:
                    hints.append(hint_line(entry))
                    break
        elif ok and not info["look"]:
            pending = [c for c in calls if c.get("eligible") and not c.get("resolved") and c["sig"] == info["sig"]]
            if pending:
                failed = pending[-1]
                failed["resolved"] = True
                between = [
                    c["sig"] for c in calls
                    if failed["seq"] < c["seq"] and c.get("ok") and not c.get("look")
                    and c.get("program") not in _NOT_A_STEP and c.get("program") != info["program"]
                ]
                kinds, items = delta_between(failed, info, between)
                if items:
                    try:
                        _record_repair(state_dir, info["sig"], kinds, items, now)
                    except Exception:
                        pass
        call = dict(info, seq=seq, ok=ok, eligible=eligible, resolved=False)
        calls.append(call)
        if any(c.get("eligible") and not c.get("resolved") for c in calls):
            _sweep_windows(state_dir, now)
            jsonio.write_json_atomic(path, {"seq": seq, "calls": calls})
            _set_sentinel(session, True)
        else:
            try:
                os.unlink(path)
            except OSError:
                pass
            _set_sentinel(session, False)
    return hints


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        state_dir = args[args.index("--state-dir") + 1]
        session = args[args.index("--session") + 1]
        payload = json.loads(sys.stdin.read(1048577))
        for line in process(state_dir, session, payload):
            print(line)
    except Exception:
        pass
    return 0
