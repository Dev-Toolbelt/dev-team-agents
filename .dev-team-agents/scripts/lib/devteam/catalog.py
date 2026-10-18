"""Read-only catalog of what a resolved version actually contains (ADR-0011).

ADR-0011 makes the desktop app a client of this CLI: every screen invokes
``devteam <command> --json`` and renders the result, nothing is reimplemented in
TypeScript. One of the app's screens browses the installed agents and skills
read-only and shows the version they came from — there was no command behind
that screen until this module. It is also useful on its own: "which agents does
my bound project actually have, and from which version" is a question asked in a
terminal, and answering it used to mean reading the store by hand.

Every fact reported here comes straight from a file's own YAML frontmatter —
``helpers/agent-lint.sh`` already enforces ``name``/``description``/``tier``/
``model`` on agents and ``name``/``description`` on skills, so this module reads
that same flat, ``---``-delimited shape rather than guessing a schema. Parsing is
a small, honest reader (see :func:`parse_frontmatter`): the repository is
standard library only, and a 20-line reader that says plainly what it does not
handle is better than a YAML dependency. A file whose frontmatter does not fit
that shape is reported as a malformed entry, with its path, rather than raising —
a catalog that dies on one bad file is useless for finding the bad file.

Nothing here resolves *which* version to read, and nothing here touches a
project, the registry, or the machine identity — that resolution (a project's
pin, falling back to the active version) is identical to what ``prefs`` already
does, and lives in ``cli.py`` next to it rather than being re-invented here. See
``cmd_prefs_list`` and ``doctor.check_machine`` for the precedent this follows.
Every function below is a pure read against ``versions.require(<version>)``: it
creates nothing, on any path.
"""

from __future__ import annotations

from pathlib import Path

from . import command_usage, versions
from .errors import UsageError

#: The three trees this catalog reads, and the order they are reported in.
KINDS = ("agents", "skills", "commands")


def parse_frontmatter(text):
    """``(frontmatter, body)`` for the flat, ``---``-delimited YAML this repo uses.

    Handles exactly what ``helpers/agent-lint.sh`` enforces: one ``key: value``
    scalar pair per line, values optionally wrapped in matching quotes, blank
    lines and ``#`` comments ignored. Anything else this repository does not
    actually use — a nested map, a list, a multi-line scalar — raises
    ``ValueError`` naming the offending line rather than silently guessing at it.
    Deliberately no YAML dependency: standard library only.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("does not start with a '---' frontmatter delimiter")
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        raise ValueError("no closing '---' for the frontmatter block")

    data = {}
    for raw in lines[1:end]:
        line = raw.rstrip("\r")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError("not a 'key: value' line: {!r}".format(line))
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError("empty key in line: {!r}".format(line))
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        data[key] = value

    body = "\n".join(lines[end + 1 :])
    return data, body


def _read_text(path):
    return Path(path).read_text(encoding="utf-8")


def _malformed(name_fallback, rel, version, exc, extra=None):
    entry = {"name": name_fallback, "path": rel, "version": version, "malformed": True, "error": str(exc)}
    if extra:
        entry.update(extra)
    return entry


def _agent_entry(path, version_dir, version):
    # `.as_posix()`: `path` is part of the `--json` contract the desktop app
    # consumes (ADR-0011), and a shape change includes the separator — a Windows
    # CLI answering `agents\backend-developer.md` where every other platform
    # answers `agents/backend-developer.md` is exactly the breaking change that
    # ADR forbids, just silent because nothing failed loudly.
    rel = Path(path).relative_to(version_dir).as_posix()
    name_fallback = Path(path).stem
    try:
        frontmatter, _body = parse_frontmatter(_read_text(path))
    except (OSError, ValueError) as exc:
        return _malformed(name_fallback, rel, version, exc)
    return {
        "name": frontmatter.get("name", name_fallback),
        "tier": frontmatter.get("tier"),
        "model": frontmatter.get("model"),
        "description": frontmatter.get("description"),
        "path": rel,
        "version": version,
    }


def _skill_entry(path, version_dir, version):
    rel_path = Path(path).relative_to(version_dir)
    # `.as_posix()`: see `_agent_entry` — same `--json` contract.
    rel = rel_path.as_posix()
    # `skills/<category>/.../SKILL.md` — the parts after `skills/` itself, so the
    # first one is the top-level grouping CLAUDE.md's file-structure list names
    # (shared, architecture, testing, ...). A skill directly under `skills/`
    # (e.g. `skill-creator`) has no separate category, so it names itself.
    parts = rel_path.parts[1:]
    category = parts[0] if len(parts) > 1 else None
    name_fallback = Path(path).parent.name
    try:
        frontmatter, _body = parse_frontmatter(_read_text(path))
    except (OSError, ValueError) as exc:
        return _malformed(name_fallback, rel, version, exc, extra={"category": category})
    return {
        "name": frontmatter.get("name", name_fallback),
        "description": frontmatter.get("description"),
        "category": category,
        "path": rel,
        "version": version,
    }


def _command_meta(version_dir):
    """The resolved version's own commands.json (`featured`, `related`); ``{}`` when it has none."""
    return command_usage.load_commands(Path(version_dir) / "scripts" / "lib")


def _command_entry(path, version_dir, version, meta=None):
    # `.as_posix()`: see `_agent_entry` — same `--json` contract.
    rel = Path(path).relative_to(version_dir).as_posix()
    # Commands carry no `name:` key (only `description` and, optionally,
    # `argument-hint` are Claude-only frontmatter here) — the filename is the name.
    name = Path(path).stem
    try:
        frontmatter, _body = parse_frontmatter(_read_text(path))
    except (OSError, ValueError) as exc:
        return _malformed(name, rel, version, exc)
    entry_meta = (meta or {}).get(name)
    entry_meta = entry_meta if isinstance(entry_meta, dict) else {}
    related = entry_meta.get("related")
    return {
        "name": name,
        "description": frontmatter.get("description"),
        "path": rel,
        "version": version,
        # ADR-0030 section 5: additive, so a version that predates them answers false / [].
        "featured": entry_meta.get("featured") is True,
        "related": [item for item in related if isinstance(item, str)] if isinstance(related, list) else [],
    }


def list_agents(version):
    version_dir = versions.require(version)
    found = sorted((version_dir / "agents").glob("*.md"))
    return [_agent_entry(path, version_dir, version) for path in found]


def list_skills(version):
    version_dir = versions.require(version)
    found = sorted((version_dir / "skills").glob("**/SKILL.md"))
    return [_skill_entry(path, version_dir, version) for path in found]


def list_commands(version, featured_only=False):
    version_dir = versions.require(version)
    found = sorted((version_dir / "commands").glob("*.md"))
    meta = _command_meta(version_dir)
    entries = [_command_entry(path, version_dir, version, meta) for path in found]
    if featured_only:
        entries = [entry for entry in entries if entry.get("featured")]
    return entries


_LISTERS = {"agents": list_agents, "skills": list_skills, "commands": list_commands}


def list_kind(kind, version, featured_only=False):
    if featured_only and kind == "commands":
        return list_commands(version, featured_only=True)
    lister = _LISTERS.get(kind)
    if lister is None:
        raise UsageError(
            "unknown catalog kind: {!r}".format(kind),
            hint="Use one of: {}".format(", ".join(KINDS)),
        )
    return lister(version)


def summary(version):
    """Counts per kind, and how many of each were malformed."""
    counts = {}
    malformed = {}
    for kind in KINDS:
        entries = list_kind(kind, version)
        counts[kind] = len(entries)
        malformed[kind] = sum(1 for entry in entries if entry.get("malformed"))
    return {"version": version, "counts": counts, "malformed": malformed}


def show(name, version):
    """One entry's metadata and body, resolved by bare name across all kinds.

    A malformed entry's reported name is only a best-effort fallback (the file's
    own frontmatter could not be trusted to begin with), so it is excluded from
    this lookup — it is only reachable through the kind listing it showed up in.
    """
    candidates = []
    for kind in KINDS:
        for entry in list_kind(kind, version):
            if entry.get("malformed"):
                continue
            if entry.get("name") == name:
                candidates.append((kind, entry))

    if not candidates:
        raise UsageError(
            "no agent, skill or command named {!r} in version {}".format(name, version),
            hint="Run `devteam catalog agents|skills|commands` to see what exists.",
        )
    if len(candidates) > 1:
        raise UsageError(
            "{!r} is ambiguous in version {}: {}".format(
                name,
                version,
                ", ".join("{} ({})".format(kind, entry["path"]) for kind, entry in candidates),
            ),
            hint="Ask for the kind directly, e.g. `devteam catalog agents`, and read its path.",
        )

    kind, entry = candidates[0]
    version_dir = versions.require(version)
    text = _read_text(version_dir / entry["path"])
    _frontmatter, body = parse_frontmatter(text)
    result = dict(entry)
    result["kind"] = kind
    result["body"] = body.strip("\n")
    return result
