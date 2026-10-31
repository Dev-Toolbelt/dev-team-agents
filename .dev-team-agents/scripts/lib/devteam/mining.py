"""`devteam mine sessions|reviews` -- candidate rules from history, never written anywhere (ADR-0050).

* **sessions** reads the messages the user typed in this project's local transcripts, one reader
  per provider in ``providers.ALL_PROVIDERS``, and lists a correction or preference that was
  expressed on at least ``MIN_DAYS`` distinct local days. No model call and no network.
* **reviews** lists inline review threads of the last ``MERGED_PRS`` merged pull requests that were
  resolved or outdated (the author acted on them), each with its file. The GitHub integration
  adapter serves the request (ADR-0023); ``gh`` is the fallback when the adapter cannot.

Both only read. Every text that leaves this module went through ``tasks.redact``.

Transcript formats are provider internals, so a reader that cannot make sense of a file skips it:
a missing or malformed transcript yields no candidates, never an error. Formats read:

* claude -- ``~/.claude/projects/<slug>/*.jsonl`` (``<slug>`` is the project path with every
  non-alphanumeric character replaced by ``-``; worktrees under ``.worktrees/`` have their own
  slug starting ``<slug>--worktrees-``).
* codex -- ``${CODEX_HOME:-~/.codex}/sessions/**/rollout-*.jsonl``; the first line carries the
  session's ``cwd`` and ``originator``.
* opencode -- ``opencode.db`` (SQLite) under ``${XDG_DATA_HOME:-~/.local/share}/opencode/``, tables
  ``session`` / ``message`` / ``part`` (verified against a live install). Older opencode versions
  stored JSON files under ``storage/message/<session>/msg_*.json`` and ``storage/part/<message>/
  prt_*.json``; that layout is read too but is UNVERIFIED (no install on hand to confirm it).
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sqlite3
import subprocess
import urllib.parse
from pathlib import Path

from . import integrations, providers
from .errors import DevteamError
from .tasks import redact

MIN_DAYS = 2
MERGED_PRS = 50
MAX_FILES = 200          # transcripts read per provider, newest first
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_LINE_BYTES = 1024 * 1024
MAX_MESSAGES = 3000      # typed messages kept for clustering, per provider
MAX_TEXT = 400           # a longer message is a task description or pasted text, not a correction
MAX_LINES = 4
MAX_CANDIDATES = 50
MAX_THREADS = 100
EXCERPT = 200
NEAR_DUPLICATE = 0.75    # word-set Jaccard above which two messages are the same correction

_CORRECTION = re.compile(
    r"(?i)\b(?:don'?t|do not|never|stop (?:doing|using|adding|creating|writing|making)|"
    r"not like (?:that|this)|i (?:said|told you|asked)|instead of|rather than|wrong|"
    r"must not|should not|shouldn'?t|no need to|without (?:asking|creating|adding)|"
    r"n[aã]o (?:use|crie|fa[cç]a|quero|precisa|deve|pode|coloque|adicione)|nunca|"
    r"pare de|em vez de|ao inv[eé]s de|j[aá] (?:falei|te disse)|errado)\b"
)
_PREFERENCE = re.compile(
    r"(?i)\b(?:always|prefer|from now on|going forward|by default|every time|whenever|"
    r"sempre|prefiro|de agora em diante|daqui pra frente|por padr[aã]o|toda vez)\b"
)
_NOISE_PREFIX = ("<", "[Pasted", "[Request interrupted", "Caveat:", "# AGENTS.md", "# CLAUDE.md")
_WORD = re.compile(r"[^\W_]+", re.UNICODE)


# -- shared helpers ----------------------------------------------------------------------------


def _local_day(value):
    """``YYYY-MM-DD`` in the machine's local zone for an ISO string or an epoch (s or ms)."""
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            seconds = value / 1000.0 if value > 1e11 else float(value)
            moment = datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc)
        elif isinstance(value, str) and value:
            moment = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=datetime.timezone.utc)
        else:
            return None
        return moment.astimezone().strftime("%Y-%m-%d")
    except (ValueError, OverflowError, OSError):
        return None


def _typed(text):
    """The text when it looks typed by a person, else ``None``: short, prose, not a tag or a paste."""
    if not isinstance(text, str):
        return None
    text = text.strip()
    if not text or len(text) > MAX_TEXT or text.startswith(_NOISE_PREFIX):
        return None
    if text.count("\n") >= MAX_LINES or "```" in text:
        return None
    return text


def _roots(root):
    """The project root plus the main checkout when ``root`` is a linked worktree."""
    found = {str(Path(root).resolve())}
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=str(root),
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5, check=False,
        )
        if out.returncode == 0:
            common = Path(out.stdout.decode("utf-8", "replace").strip())
            if common.name == ".git":
                found.add(str(common.parent.resolve()))
    except (OSError, subprocess.SubprocessError):
        pass
    return sorted(found)


def _under(path, roots):
    if not isinstance(path, str) or not path:
        return False
    path = os.path.normpath(path)
    return any(path == r or path.startswith(r + os.sep) for r in roots)


def _newest(paths):
    """At most ``MAX_FILES`` readable paths, newest modification first."""
    stamped = []
    for path in paths:
        try:
            stamped.append((os.stat(path).st_mtime, str(path)))
        except OSError:
            continue
    stamped.sort(reverse=True)
    return [p for _t, p in stamped[:MAX_FILES]]


def _lines(path, stats=None):
    """Decoded JSON objects of a JSONL file, streamed; unreadable or oversized input is skipped.

    A file over ``MAX_FILE_BYTES`` is counted in ``stats["skipped_oversize"]`` when given.
    """
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            if stats is not None:
                stats["skipped_oversize"] = stats.get("skipped_oversize", 0) + 1
            return
        with open(path, "rb") as stream:
            for raw in stream:
                if len(raw) > MAX_LINE_BYTES:
                    continue
                try:
                    obj = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(obj, dict):
                    yield obj
    except OSError:
        return


# -- readers: each yields (day, text) for messages the user typed -------------------------------


def _claude_text(obj):
    if obj.get("type") != "user" or obj.get("isSidechain") or obj.get("isMeta"):
        return None
    if str(obj.get("entrypoint", "")).startswith("sdk"):  # headless / automated run
        return None
    origin = obj.get("origin")
    if isinstance(origin, dict) and origin.get("kind") not in (None, "human"):
        return None
    content = (obj.get("message") or {}).get("content")
    if isinstance(content, list):
        # A tool result or an attachment makes the whole message non-typed.
        if any(not isinstance(b, dict) or b.get("type") != "text" for b in content):
            return None
        content = "\n".join(b.get("text", "") for b in content)
    return content if isinstance(content, str) else None


def read_claude(roots, home=None, stats=None):
    base = Path(home or Path.home()) / ".claude" / "projects"
    slugs = {re.sub(r"[^A-Za-z0-9]", "-", r) for r in roots}
    try:
        names = sorted(os.listdir(base))
    except OSError:
        return
    files = []
    for name in names:
        if name in slugs or any(name.startswith(s + "--worktrees-") for s in slugs):
            try:
                files += [base / name / f for f in os.listdir(base / name) if f.endswith(".jsonl")]
            except OSError:
                continue
    for path in _newest(files):
        # The slug is lossy (every non-alphanumeric becomes "-"), so two projects can share one:
        # the session's recorded cwd decides whether the file belongs to this project.
        cwd = None
        found = []
        for obj in _lines(path, stats):
            if cwd is None and isinstance(obj.get("cwd"), str):
                cwd = obj["cwd"]
            text = _typed(_claude_text(obj))
            day = _local_day(obj.get("timestamp")) if text else None
            if day:
                found.append((day, text))
        if _under(cwd, roots):
            yield from found


def read_codex(roots, home=None, stats=None):
    base = Path(os.environ.get("CODEX_HOME") or Path(home or Path.home()) / ".codex") / "sessions"
    files = []
    for dirpath, _dirs, names in os.walk(base):
        files += [os.path.join(dirpath, n) for n in names if n.startswith("rollout-") and n.endswith(".jsonl")]
    for path in _newest(files):
        belongs = False
        for number, obj in enumerate(_lines(path, stats)):
            payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
            if number == 0:
                if obj.get("type") != "session_meta":
                    break
                headless = payload.get("originator") == "codex_exec" or payload.get("source") == "exec"
                belongs = _under(payload.get("cwd"), roots) and not headless
                if not belongs:
                    break
                continue
            if obj.get("type") != "response_item" or payload.get("type") != "message" or payload.get("role") != "user":
                continue
            blocks = payload.get("content")
            if not isinstance(blocks, list) or any(not isinstance(b, dict) or b.get("type") != "input_text" for b in blocks):
                continue
            text = _typed("\n".join(b.get("text", "") for b in blocks))
            day = _local_day(obj.get("timestamp")) if text else None
            if day:
                yield day, text


def _opencode_base(home=None):
    data = os.environ.get("XDG_DATA_HOME") or str(Path(home or Path.home()) / ".local" / "share")
    return Path(data) / "opencode"


def _opencode_db(db, roots):
    try:
        conn = sqlite3.connect("file:{}?mode=ro".format(db), uri=True, timeout=2)
    except sqlite3.Error:
        return
    try:
        marks = ",".join("?" * len(roots))
        rows = conn.execute(
            "SELECT m.time_created, p.data FROM session s "
            "JOIN message m ON m.session_id = s.id JOIN part p ON p.message_id = m.id "
            "WHERE s.parent_id IS NULL AND (s.directory IN ({0}) OR {1}) "
            "AND json_extract(m.data, '$.role') = 'user' "
            "ORDER BY s.time_updated DESC, m.time_created, p.time_created LIMIT ?".format(
                marks, " OR ".join(["s.directory LIKE ? ESCAPE '\\'"] * len(roots))
            ),
            list(roots) + [_like_prefix(r) for r in roots] + [MAX_MESSAGES * 4],
        )
        for created, data in rows:
            try:
                part = json.loads(data)
            except (TypeError, ValueError):
                continue
            if not isinstance(part, dict) or part.get("type") != "text" or part.get("synthetic"):
                continue
            text = _typed(part.get("text"))
            day = _local_day(created) if text else None
            if day:
                yield day, text
    except sqlite3.Error:
        return
    finally:
        conn.close()


def _like_prefix(root):
    return root.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + os.sep + "%"


def _opencode_json(storage, roots):
    """The pre-SQLite layout. UNVERIFIED: written from opencode's documented storage tree."""
    sessions = {}
    for path in _newest(str(p) for p in (storage / "session").glob("*/ses_*.json")):
        try:
            with open(path, "r", encoding="utf-8") as stream:
                info = json.load(stream)
        except (OSError, ValueError):
            continue
        if isinstance(info, dict) and not info.get("parentID") and _under(info.get("directory"), roots):
            sessions[info.get("id")] = True
    for session_id in sessions:
        for msg_path in sorted((storage / "message" / str(session_id)).glob("msg_*.json")):
            try:
                with open(msg_path, "r", encoding="utf-8") as stream:
                    msg = json.load(stream)
            except (OSError, ValueError):
                continue
            if not isinstance(msg, dict) or msg.get("role") != "user":
                continue
            for part_path in sorted((storage / "part" / str(msg.get("id"))).glob("prt_*.json")):
                try:
                    with open(part_path, "r", encoding="utf-8") as stream:
                        part = json.load(stream)
                except (OSError, ValueError):
                    continue
                if isinstance(part, dict) and part.get("type") == "text" and not part.get("synthetic"):
                    text = _typed(part.get("text"))
                    day = _local_day((msg.get("time") or {}).get("created")) if text else None
                    if day:
                        yield day, text


def read_opencode(roots, home=None, stats=None):
    base = _opencode_base(home)
    db = base / "opencode.db"
    if db.is_file():
        yield from _opencode_db(db, roots)
    if (base / "storage" / "session").is_dir():
        yield from _opencode_json(base / "storage", roots)


#: One reader per provider. ``tests/test_provider_ownership.py`` style: a provider in
#: ``ALL_PROVIDERS`` without a reader here is a gap.
READERS = {"claude": read_claude, "codex": read_codex, "opencode": read_opencode}


# -- clustering -----------------------------------------------------------------------------------


def _words(text):
    return frozenset(w.lower() for w in _WORD.findall(text))


def _kind(text):
    if _CORRECTION.search(text):
        return "correction"
    if _PREFERENCE.search(text):
        return "preference"
    return None


def _jaccard(a, b):
    return len(a & b) / float(len(a | b)) if a and b else 0.0


def cluster(items):
    """Group ``(provider, day, text)`` items that state the same correction.

    Messages with identical word sets merge exactly; the rest merge when their word sets overlap
    by at least ``NEAR_DUPLICATE``. A group becomes a candidate with at least ``MIN_DAYS`` days.
    """
    groups = []  # {"words", "texts": {text: n}, "days", "providers", "kind"}
    taken = {}
    for provider, day, text in items:
        taken[provider] = taken.get(provider, 0) + 1
        if taken[provider] > MAX_MESSAGES:
            continue
        kind = _kind(text)
        words = _words(text)
        if not kind or len(words) < 3:
            continue
        for group in groups:
            if group["words"] == words or _jaccard(group["words"], words) >= NEAR_DUPLICATE:
                break
        else:
            group = {"words": words, "texts": {}, "days": set(), "providers": set(), "kind": kind, "n": 0}
            groups.append(group)
        group["texts"][text] = group["texts"].get(text, 0) + 1
        group["days"].add(day)
        group["providers"].add(provider)
        group["n"] += 1
    found = []
    for group in groups:
        if len(group["days"]) < MIN_DAYS:
            continue
        wording = max(group["texts"].items(), key=lambda kv: (kv[1], -len(kv[0])))[0]
        found.append({
            "text": " ".join(redact(wording).split())[:EXCERPT],
            "kind": group["kind"],
            "days": sorted(group["days"]),
            "occurrences": group["n"],
            "providers": sorted(group["providers"]),
        })
    found.sort(key=lambda c: (-len(c["days"]), -c["occurrences"], c["text"]))
    return found[:MAX_CANDIDATES]


# -- sessions -------------------------------------------------------------------------------------


def sessions(root, home=None):
    roots = _roots(root)
    items = []
    scanned = {}
    skipped = {}
    for provider in providers.ALL_PROVIDERS:
        reader = READERS.get(provider)
        count = 0
        stats = {}
        if reader is not None:
            try:
                for day, text in reader(roots, home, stats):
                    items.append((provider, day, text))
                    count += 1
                    if count >= MAX_MESSAGES:
                        break
            except Exception:  # noqa: BLE001 -- a provider's internal format must never fail the command
                pass
        scanned[provider] = count
        skipped[provider] = stats.get("skipped_oversize", 0)
    return {
        "min_days": MIN_DAYS,
        "messages_by_provider": scanned,
        "skipped_oversize_by_provider": skipped,
        "candidates": cluster(items),
    }


def render_sessions(result):
    lines = ["mine sessions: {} candidate(s) from {} typed message(s)".format(
        len(result["candidates"]), sum(result["messages_by_provider"].values()))]
    for item in result["candidates"]:
        lines.append("  [{}] {} ({} days: {})".format(
            item["kind"], item["text"], len(item["days"]), ", ".join(item["days"][-3:])))
    for provider, n in sorted(result.get("skipped_oversize_by_provider", {}).items()):
        if n:
            lines.append("  note: {} {} transcript(s) skipped (over {} MB)".format(n, provider, MAX_FILE_BYTES // (1024 * 1024)))
    return "\n".join(lines)


# -- reviews --------------------------------------------------------------------------------------


def _web_host(values):
    """The web host the integration is configured for (GitHub Enterprise), else ``github.com``."""
    api_url = values.get("api_url") if values else None
    if isinstance(api_url, str) and api_url:
        api_host = (urllib.parse.urlsplit(api_url).hostname or "").lower()
        if api_host and api_host != "api.github.com":
            return api_host
    return "github.com"


def _repository(root, values):
    """``owner/name``: the integration's bound repository, else the git origin on github.com."""
    bound = values.get("repository") if values else None
    if isinstance(bound, str) and bound:
        return bound
    try:
        out = subprocess.run(
            ["git", "remote", "get-url", "origin"], cwd=str(root), stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    from .integrations.github import parse_remote
    return parse_remote(out.stdout.decode("utf-8", "replace").strip(), _web_host(values))


def _nodes_via_adapter(root):
    adapter, values, token = integrations.ready("github", root)
    repository = _repository(root, values)
    if not repository:
        raise DevteamError("no repository")
    return repository, adapter.review_threads(values, token, repository, MERGED_PRS)


def _nodes_via_gh(root):
    from .integrations.github import REVIEW_THREADS_QUERY
    repository = _repository(root, None)
    if not repository:
        raise DevteamError("no repository")
    owner, _, name = repository.partition("/")
    out = subprocess.run(
        ["gh", "api", "graphql", "-f", "query=" + REVIEW_THREADS_QUERY, "-f", "owner=" + owner,
         "-f", "name=" + name, "-F", "prs={}".format(MERGED_PRS)],
        cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=60, check=False,
    )
    if out.returncode != 0:
        raise DevteamError("gh failed")
    return repository, json.loads(out.stdout)["data"]["repository"]["pullRequests"]["nodes"]


def _threads(nodes):
    found = []
    for pr in nodes or []:
        if not isinstance(pr, dict):
            continue
        for thread in ((pr.get("reviewThreads") or {}).get("nodes") or []):
            if not isinstance(thread, dict) or not (thread.get("isResolved") or thread.get("isOutdated")):
                continue
            comments = ((thread.get("comments") or {}).get("nodes")) or []
            body = comments[0].get("body") if comments and isinstance(comments[0], dict) else None
            if not isinstance(body, str) or not thread.get("path"):
                continue
            state = [s for s, on in (("resolved", thread.get("isResolved")), ("outdated", thread.get("isOutdated"))) if on]
            found.append({
                "pr": pr.get("number"),
                "url": pr.get("url"),
                "path": redact(str(thread["path"])),
                "state": "+".join(state),
                "excerpt": " ".join(redact(body).split())[:EXCERPT],
            })
    return found[:MAX_THREADS]


def reviews(root):
    """Candidates from merged-PR review threads; an empty list with a ``reason`` when unreachable."""
    attempts = (("github-adapter", _nodes_via_adapter), ("gh", _nodes_via_gh))
    for source, fetch in attempts:
        try:
            repository, nodes = fetch(root)
        except Exception:  # noqa: BLE001 -- unreachable, not connected, no gh: try the next path
            continue
        return {"available": True, "reason": None, "source": source, "repository": repository,
                "prs_scanned": len(nodes or []), "candidates": _threads(nodes)}
    return {"available": False, "reason": "reviews could not be read: neither the GitHub integration "
            "nor `gh` could reach the repository", "source": None, "repository": None,
            "prs_scanned": 0, "candidates": []}


def render_reviews(result):
    if not result["available"]:
        return "mine reviews: {}".format(result["reason"])
    lines = ["mine reviews: {} candidate(s) from {} merged PR(s) via {}".format(
        len(result["candidates"]), result["prs_scanned"], result["source"])]
    for item in result["candidates"]:
        lines.append("  PR #{} {} [{}] {}".format(item["pr"], item["path"], item["state"], item["excerpt"]))
    return "\n".join(lines)
