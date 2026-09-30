"""The user-level skills each provider reads — list, show, install, remove (ADR-0020).

Claude Code, Codex and opencode each read skills from a directory in the user's home,
outside any project and outside the store. This module is the one place that knows
those directories (through ``scripts/lib/global-skill-roots.json``) and the only writer
to them, so the desktop app can manage them as a client of this CLI (ADR-0011) instead
of touching the filesystem itself.

The unit is a **root**: one physical directory, read by one or more providers. opencode
also reads ``~/.claude/skills`` and ``~/.agents/skills``, so reporting per provider
would list one directory's skills two or three times; every entry therefore carries
the root it lives in and the providers that read that root.

Two rules shape every write:

- **Nothing is deleted.** Removing — or replacing — a real directory moves it into the
  store's quarantine (the No-Destruction Rule, canonical in
  ``skills/shared/setup-health-check/SKILL.md``). A symlink is unlinked, because what
  it points at is not touched.
- **A skill this framework manages is refused.** A symlink resolving into the core
  store belongs to a bind; ``devteam sync`` would put it back, so removing it here only
  hides a problem.

Third-party skills use more YAML than this repository's flat frontmatter — folded
``description: >`` blocks, nested ``metadata:`` maps — so :func:`read_frontmatter`
reads leniently: it needs ``name`` and ``description`` and ignores what it does not
understand, instead of reporting a working skill as malformed.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from . import lock, paths, quarantine
from .errors import ConflictError, UsageError

ROOTS_FILE = Path(__file__).resolve().parent.parent / "global-skill-roots.json"

#: Overrides the home directory ``~`` expands to in the roots file. The test seam: the
#: suite must never read or write the developer's real ``~/.claude/skills``.
USER_HOME_ENV = "DEVTEAM_USER_HOME"

PROVIDERS = ("claude", "codex", "opencode")

#: agentskills.io: lowercase letters, digits and hyphens, at most 64 characters.
NAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")

#: Limits on an archive, checked before a single byte is extracted.
MAX_ARCHIVE_MEMBERS = 2000
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024

#: How many files ``show`` lists before truncating.
MAX_LISTED_FILES = 200

ARCHIVE_SUFFIXES = (".zip", ".skill")


# ── roots ─────────────────────────────────────────────────────────────────────


def user_home():
    raw = os.environ.get(USER_HOME_ENV)
    return Path(raw).expanduser() if raw else Path(os.path.expanduser("~"))


def _expand(raw):
    if raw == "~":
        return user_home()
    if raw.startswith("~/"):
        return user_home() / raw[2:]
    return Path(raw)


def load_roots():
    """``(roots, install_target)`` from the canonical JSON file."""
    with open(ROOTS_FILE, encoding="utf-8") as handle:
        data = json.load(handle)
    roots = []
    for entry in data["roots"]:
        roots.append(
            {
                "id": entry["id"],
                "path": _expand(entry["path"]),
                "read_by": list(entry["read_by"]),
            }
        )
    return roots, dict(data["install_target"])


def _roots_for(provider):
    roots, _target = load_roots()
    if provider in (None, "all"):
        return roots
    return [root for root in roots if provider in root["read_by"]]


def _root_by_id(root_id):
    roots, _target = load_roots()
    for root in roots:
        if root["id"] == root_id:
            return root
    raise UsageError(
        "unknown skill root {!r}".format(root_id),
        hint="One of: {}.".format(", ".join(root["id"] for root in roots)),
    )


def _describe_root(root, install_target):
    return {
        "id": root["id"],
        "path": str(root["path"]),
        "exists": root["path"].is_dir(),
        "providers": root["read_by"],
        "install_target_for": sorted(p for p, rid in install_target.items() if rid == root["id"]),
    }


# ── frontmatter ───────────────────────────────────────────────────────────────


def _unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    # An unquoted YAML scalar ends at ` #`: `name: foo # note` is `foo`.
    return re.split(r"\s+#", value, maxsplit=1)[0].rstrip()


def read_frontmatter(text):
    """``(fields, body)`` — top-level scalar keys only, block scalars folded.

    Nested maps and lists are skipped rather than rejected: a skill carrying
    ``metadata:`` or ``allowed-tools:`` is still a working skill. The closing
    ``---`` must start at column 0, so an indented ``---`` inside a block scalar
    does not end the block. Raises ``ValueError`` only when there is no
    frontmatter block at all.
    """
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        raise ValueError("SKILL.md does not start with a '---' frontmatter block")
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip() == "---"), None)
    if end is None:
        raise ValueError("SKILL.md has no closing '---' for its frontmatter block")

    fields = {}
    index = 1
    while index < end:
        line = lines[index].rstrip("\r")
        index += 1
        if not line.strip() or line.lstrip().startswith("#") or line[0] in " \t":
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key, value = key.strip(), value.strip()
        indicator = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
        if indicator in ("", ">", "|", ">-", "|-", ">+", "|+"):
            block = []
            while index < end and (not lines[index].strip() or lines[index][0] in " \t"):
                block.append(lines[index].strip())
                index += 1
            if indicator == "":
                continue  # a nested map or list, not a scalar
            joiner = "\n" if indicator.startswith("|") else " "
            fields[key] = joiner.join(part for part in block if part).strip()
        else:
            fields[key] = _unquote(value)
    return fields, "\n".join(lines[end + 1 :])


def validate_skill_dir(skill_dir, expected_name=None):
    """``(name, description, body)`` for a directory, or ``ValueError`` saying why not."""
    skill_md = Path(skill_dir) / "SKILL.md"
    if not skill_md.is_file():
        raise ValueError("no SKILL.md")
    fields, body = read_frontmatter(skill_md.read_text(encoding="utf-8"))
    name = fields.get("name")
    if not name:
        raise ValueError("frontmatter has no 'name'")
    if not fields.get("description"):
        raise ValueError("frontmatter has no 'description'")
    if not NAME_PATTERN.match(name):
        raise ValueError(
            "name {!r} is not lowercase letters, digits and hyphens (max 64)".format(name)
        )
    if expected_name is not None and name != expected_name:
        raise ValueError("frontmatter name {!r} does not match its directory {!r}".format(name, expected_name))
    return name, fields["description"], body


# ── listing ───────────────────────────────────────────────────────────────────


def _core_real():
    try:
        return Path(os.path.realpath(str(paths.core_dir())))
    except OSError:
        return None


def _inside(path, container):
    try:
        real = Path(os.path.realpath(str(path)))
    except OSError:
        return False
    return real == container or container in real.parents


def _is_managed(path):
    """Resolves into the core store — the framework owns it, not the user.

    Checked on the **resolved** path, not only on a symlink leaf: a root that is
    itself a symlink into the core makes every child a plain directory that still
    lives inside the versioned store, and moving one would damage it.
    """
    core = _core_real()
    return core is not None and _inside(path, core)


def _entry(root, child):
    is_link = child.is_symlink()
    record = {
        "name": child.name,
        "description": None,
        "root": root["id"],
        "root_path": str(root["path"]),
        "path": str(child),
        "providers": root["read_by"],
        "is_symlink": is_link,
        "link_target": os.readlink(str(child)) if is_link else None,
        "managed": _is_managed(child),
        "status": "ok",
        "error": None,
    }
    try:
        _name, description, _body = validate_skill_dir(child, expected_name=child.name)
        record["description"] = description
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        record["status"] = "malformed"
        record["error"] = str(exc)
        try:
            fields, _ = read_frontmatter((child / "SKILL.md").read_text(encoding="utf-8"))
            record["description"] = fields.get("description") or None
        except (OSError, UnicodeDecodeError, ValueError):
            pass
    return record


def _children(root):
    """Skill directories in a root: dot-entries (provider internals such as Codex's
    ``.system``, and this module's own staging directories) and plain files are not
    skills and are never reported."""
    base = root["path"]
    if not base.is_dir():
        return []
    found = []
    for child in sorted(base.iterdir(), key=lambda p: p.name):
        if child.name.startswith("."):
            continue
        if child.is_dir() or child.is_symlink():
            found.append(child)
    return found


def list_skills(provider=None):
    roots, install_target = load_roots()
    selected = _roots_for(provider)
    skills = [_entry(root, child) for root in selected for child in _children(root)]
    return {
        "provider": provider or "all",
        "roots": [_describe_root(root, install_target) for root in selected],
        "skills": skills,
        "count": len(skills),
    }


def _check_name(name):
    """Reject anything that is not a plain directory name before it meets a path.

    Deliberately looser than ``NAME_PATTERN``: an existing third-party skill with an
    uppercase letter or an underscore must stay removable. What is refused is what
    could reach outside the root — ``.``, ``..``, separators, NUL — and dot-names,
    which are never skills here.
    """
    if (
        not name
        or name.startswith(".")
        or any(ch in name for ch in ("/", "\\", "\0"))
        or re.match(r"^[A-Za-z]:", name)
    ):
        raise UsageError(
            "{!r} is not a skill name".format(name),
            hint="Pass the bare directory name `devteam skills list` shows.",
        )


def _locate(name, root_id=None):
    """``(root, child)`` — matched among a root's real children, never by joining paths."""
    _check_name(name)
    if root_id is not None:
        roots = [_root_by_id(root_id)]
    else:
        roots, _target = load_roots()
    matches = [
        (root, child) for root in roots for child in _children(root) if child.name == name
    ]
    if not matches:
        where = "root {!r}".format(root_id) if root_id else "any global skill root"
        raise UsageError(
            "no skill named {!r} in {}".format(name, where),
            hint="Run `devteam skills list` to see what is installed.",
        )
    if len(matches) > 1:
        raise UsageError(
            "{!r} exists in more than one root: {}".format(name, ", ".join(r["id"] for r, _ in matches)),
            hint="Pass --root to say which one.",
        )
    return matches[0]


def show(name, root_id=None):
    root, child = _locate(name, root_id)
    record = _entry(root, child)
    try:
        record["body"] = read_frontmatter((child / "SKILL.md").read_text(encoding="utf-8"))[1]
    except (OSError, UnicodeDecodeError, ValueError):
        record["body"] = None
    files = []
    truncated = False
    if child.is_dir():
        for current, dirs, names in os.walk(str(child)):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for file_name in sorted(names):
                if len(files) >= MAX_LISTED_FILES:
                    truncated = True
                    break
                files.append(Path(current, file_name).relative_to(child).as_posix())
            if truncated:
                break
    record["files"] = files
    record["files_truncated"] = truncated
    return record


# ── install ───────────────────────────────────────────────────────────────────

#: Prefix of the hidden directory a copy is staged in before it is renamed into place.
#: Distinctive on purpose: only directories carrying it are ever swept as stale.
STAGING_PREFIX = ".devteam-staging-"

#: Archive members that are packaging debris, not skill content.
ARCHIVE_DEBRIS = ("__MACOSX/",)


def _reject_links(tree):
    for current, dirs, names in os.walk(str(tree)):
        for item in dirs + names:
            if Path(current, item).is_symlink():
                raise UsageError(
                    "the source contains a symlink: {}".format(Path(current, item).relative_to(tree)),
                    hint="Copy the files it points at, or install the directory with --link.",
                )


def _safe_member(info):
    name = info.filename
    posix = PurePosixPath(name.replace("\\", "/"))
    if posix.is_absolute() or ".." in posix.parts or re.match(r"^[A-Za-z]:", name):
        raise UsageError("the archive has an unsafe path: {!r}".format(name))
    mode = (info.external_attr >> 16) & 0o170000
    if mode == stat.S_IFLNK:
        raise UsageError("the archive contains a symlink: {!r}".format(name))
    if info.flag_bits & 0x1:
        raise UsageError("the archive is encrypted: {!r}".format(name))


def _extract(archive, into):
    """Validate every member, then extract — keeping permission bits, never setuid."""
    try:
        with zipfile.ZipFile(str(archive)) as bundle:
            members = [
                info
                for info in bundle.infolist()
                if not info.filename.replace("\\", "/").startswith(ARCHIVE_DEBRIS)
            ]
            if len(members) > MAX_ARCHIVE_MEMBERS:
                raise UsageError("the archive has more than {} entries".format(MAX_ARCHIVE_MEMBERS))
            if sum(info.file_size for info in members) > MAX_ARCHIVE_BYTES:
                raise UsageError("the archive expands to more than {} MB".format(MAX_ARCHIVE_BYTES // (1024 * 1024)))
            for info in members:
                _safe_member(info)
            for info in members:
                target = bundle.extract(info, str(into))
                mode = (info.external_attr >> 16) & 0o777
                if mode and not info.is_dir() and os.name == "posix":
                    os.chmod(target, mode | stat.S_IRUSR | stat.S_IWUSR)
    except zipfile.BadZipFile as exc:
        raise UsageError("{} is not a valid zip archive: {}".format(archive, exc))
    except RuntimeError as exc:  # an encrypted member the flag check did not catch
        raise UsageError("{} cannot be extracted: {}".format(archive, exc))


def _skill_root_in(tree):
    """The directory holding SKILL.md: the tree itself, or its single subdirectory."""
    if (tree / "SKILL.md").is_file():
        return tree
    entries = [p for p in tree.iterdir() if not p.name.startswith(".") and p.name != "__MACOSX"]
    if len(entries) == 1 and entries[0].is_dir() and (entries[0] / "SKILL.md").is_file():
        return entries[0]
    raise UsageError("no SKILL.md at the top of the source, nor in its single top-level folder")


def _targets(providers, root_ids):
    """The roots to write, covering every chosen provider with as few roots as possible.

    opencode also reads the Claude and ``.agents`` roots, so installing for
    ``claude`` + ``opencode`` into both ``~/.claude/skills`` and opencode's own root
    would make opencode see the skill twice. A provider already covered by a chosen
    root adds nothing. ``--root`` accepts only roots that are an install target —
    a listed-only root (``codex``) is never written.
    """
    roots, install_target = load_roots()
    by_id = {root["id"]: root for root in roots}
    writable = set(install_target.values())
    selected = []
    for root_id in root_ids or []:
        root = _root_by_id(root_id)
        if root["id"] not in writable:
            raise UsageError(
                "root {!r} is listed but never written".format(root_id),
                hint="Install into one of: {}.".format(", ".join(sorted(writable))),
            )
        if root["id"] not in selected:
            selected.append(root["id"])
    chosen = list(providers or [])
    if "all" in chosen or (not chosen and not selected):
        chosen = list(PROVIDERS)
    for provider in chosen:
        if any(provider in by_id[root_id]["read_by"] for root_id in selected):
            continue
        selected.append(install_target[provider])
    return [by_id[root_id] for root_id in selected]


def _move_aside(path, root):
    """Unlink a symlink, quarantine a real directory. Returns the quarantine path or None."""
    if path.is_symlink():
        path.unlink()
        return None
    return quarantine.move(path, None, group="global-skills/{}".format(root["id"]))


def _sweep_stale_staging(root):
    """Staging directories an interrupted install left behind go to quarantine."""
    base = root["path"]
    if not base.is_dir():
        return
    for child in base.iterdir():
        if child.name.startswith(STAGING_PREFIX) and child.is_dir() and not child.is_symlink():
            quarantine.move(child, None, group="global-skills/{}/stale-staging".format(root["id"]))


def _discard_own_copy(path):
    """Remove a copy this call created. The source still holds the same content, so
    this is not user data — the one removal the No-Destruction Rule does not cover."""
    if path.is_symlink():
        path.unlink()
    elif path.exists():
        shutil.rmtree(str(path))


def _conflict(message, reason, hint):
    return ConflictError(message, hint=hint, details={"reason": reason})


def _check_link_source(skill_dir, targets):
    real = Path(os.path.realpath(str(skill_dir)))
    core = _core_real()
    if core is not None and _inside(real, core):
        raise UsageError(
            "{} is inside the dev-team-agents core store".format(skill_dir),
            hint="Link a skill you own; the store's skills reach projects through `devteam bind`.",
        )
    for root in targets:
        if _inside(real, Path(os.path.realpath(str(root["path"])))):
            raise UsageError(
                "{} already lives in the {} root; linking it there would link it to itself".format(
                    skill_dir, root["id"]
                ),
                hint="Link a directory from outside the global skill roots.",
            )


def _also_present(name, targets, chosen_roots):
    """Other roots a target's providers read that already hold a skill of this name."""
    readers = {p for root in targets for p in root["read_by"]}
    roots, _target = load_roots()
    found = []
    for root in roots:
        if root["id"] in chosen_roots or not readers.intersection(root["read_by"]):
            continue
        if any(child.name == name for child in _children(root)):
            found.append({"root": root["id"], "path": str(root["path"] / name)})
    return found


def install(source, providers=None, root_ids=None, replace=False, link=False):
    source = Path(source).expanduser()
    if not source.exists():
        raise UsageError("{} does not exist".format(source))
    source = Path(os.path.abspath(str(source)))
    is_archive = source.is_file()
    if is_archive and source.suffix.lower() not in ARCHIVE_SUFFIXES:
        raise UsageError(
            "{} is neither a directory nor a .zip/.skill archive".format(source)
        )
    if is_archive and link:
        raise UsageError("--link needs a directory source, not an archive")

    targets = _targets(providers, root_ids)

    with tempfile.TemporaryDirectory(prefix="devteam-skill-") as scratch:
        if is_archive:
            _extract(source, Path(scratch))
            skill_dir = _skill_root_in(Path(scratch))
        else:
            skill_dir = _skill_root_in(source)
            if link:
                _check_link_source(skill_dir, targets)
            else:
                _reject_links(skill_dir)
        try:
            name, description, _body = validate_skill_dir(skill_dir)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise UsageError("not an installable skill: {}".format(exc))

        with lock.store_lock("global-skills"):
            # Every target is checked before any is written: a conflict in the
            # third root must not leave the skill installed in the first two.
            for root in targets:
                destination = root["path"] / name
                present = destination.exists() or destination.is_symlink()
                if present and _is_managed(destination):
                    raise _conflict(
                        "{} is managed by dev-team-agents and cannot be replaced".format(destination),
                        "managed",
                        "It is a bind artifact; `devteam sync` owns it.",
                    )
                if present and not replace:
                    raise _conflict(
                        "a skill named {!r} already exists in {}".format(name, root["path"]),
                        "exists",
                        "Pass --replace to move the current one to quarantine first.",
                    )

            # Phase 1 — stage a copy in every root. Nothing visible changes yet, and a
            # failure here removes only the stages this call made.
            staged = {}
            try:
                for root in targets:
                    root["path"].mkdir(parents=True, exist_ok=True)
                    _sweep_stale_staging(root)
                    if link:
                        continue
                    stage = Path(
                        tempfile.mkdtemp(prefix="{}{}-".format(STAGING_PREFIX, name), dir=str(root["path"]))
                    )
                    staged[root["id"]] = stage
                    shutil.rmtree(str(stage))
                    shutil.copytree(str(skill_dir), str(stage), symlinks=False)
            except BaseException:
                for stage in staged.values():
                    _discard_own_copy(stage)
                raise

            # Phase 2 — swap each stage into place. A failure part-way rolls back the
            # roots already swapped: the new copy goes, and what was there comes back
            # from quarantine (or its symlink is recreated).
            installed = []
            applied = []
            try:
                for root in targets:
                    destination = root["path"] / name
                    previous_link = os.readlink(str(destination)) if destination.is_symlink() else None
                    replaced = destination.exists() or destination.is_symlink()
                    quarantined = _move_aside(destination, root) if replaced else None
                    applied.append((destination, quarantined, previous_link))
                    if link:
                        os.symlink(str(skill_dir), str(destination), target_is_directory=True)
                    else:
                        os.replace(str(staged[root["id"]]), str(destination))
                        del staged[root["id"]]
                    installed.append(
                        {
                            "root": root["id"],
                            "path": str(destination),
                            "providers": root["read_by"],
                            "replaced": replaced,
                            "quarantined_to": str(quarantined) if quarantined else None,
                        }
                    )
            except BaseException:
                for destination, quarantined, previous_link in reversed(applied):
                    if destination.exists() or destination.is_symlink():
                        _discard_own_copy(destination)
                    if quarantined is not None:
                        shutil.move(str(quarantined), str(destination))
                    elif previous_link is not None:
                        os.symlink(previous_link, str(destination), target_is_directory=True)
                raise
            finally:
                for stage in staged.values():
                    _discard_own_copy(stage)

            also_present = _also_present(name, targets, {root["id"] for root in targets})

    return {
        "name": name,
        "description": description,
        "source": str(source),
        "linked": bool(link),
        "installed": installed,
        "also_present": also_present,
    }


# ── remove ────────────────────────────────────────────────────────────────────


def remove(name, root_id=None):
    with lock.store_lock("global-skills"):
        root, child = _locate(name, root_id)
        if _is_managed(child):
            raise _conflict(
                "{} is managed by dev-team-agents and is not removed here".format(child),
                "managed",
                "It is a bind artifact; unbind the project instead.",
            )
        link_target = os.readlink(str(child)) if child.is_symlink() else None
        quarantined = _move_aside(child, root)
    return {
        "name": name,
        "root": root["id"],
        "path": str(child),
        "providers": root["read_by"],
        "action": "unlinked" if link_target is not None else "quarantined",
        "quarantined_to": str(quarantined) if quarantined else None,
        "link_target": link_target,
    }
