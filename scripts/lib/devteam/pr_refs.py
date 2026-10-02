"""What the task board reads out of a PR/MR creation, a merge and an issue reference (ADR-0018).

Everything the hooks need to decide "did a pull/merge request just get created or merged?" and
"does this text reference an issue?" lives here, in one tested place, next to
:mod:`review_triggers`. The bash gates in front of the CLI are deliberately looser (a substring
test); this module is the authority.

Trust model (ADR-0018 § SECURITY AMENDMENTS, ADR-0025). A command line, a tool result
and a prompt are all untrusted text. Nothing here ever keeps a URL taken from them: a link is
parsed into validated *parts* (kind, host, repository path, number) and the URL is **rebuilt** from
the parts, then re-validated on every read against the project's current git remotes and
integration configuration. The check that a command really invokes ``gh pr create`` is a
false-positive filter, not a security control: the security comes from the response parser, the
shape checks and the remote match.

Pure except for two clearly marked readers, :func:`git_remotes` and :func:`load_context`, which
never touch the network, the keychain or the integration token.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import urllib.parse

#: A command longer than this is not analysed; a response/prompt longer than the text caps is cut.
MAX_COMMAND = 20000
MAX_TEXT = 200000
MAX_PROMPT = 65536
#: Most references one prompt or task text can add: a pasted list must not flood the record.
MAX_REFS_PER_TEXT = 10

KIND_PR = "pr"
KIND_MR = "mr"
LINK_KIND = {KIND_PR: "github_pr", KIND_MR: "gitlab_mr"}

HOST_RE = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
GITHUB_PATH_RE = re.compile(
    r"^/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/([A-Za-z0-9._-]{1,100})/(pull|issues)/([1-9][0-9]{0,9})$"
)
GITLAB_PATH_RE = re.compile(
    r"^/((?:[A-Za-z0-9_.-]{1,255}/){1,20}[A-Za-z0-9_.-]{1,255})/-/merge_requests/([1-9][0-9]{0,9})$"
)
OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
REPO_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
JIRA_PROJECT_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,9}$")
JIRA_BASE_PATH_RE = re.compile(r"^(/[A-Za-z0-9._~-]+)*$")
JIRA_KEY_RE = re.compile(r"^([A-Z][A-Z0-9_]{1,9})-([1-9][0-9]{0,9})$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/+@-]{0,199}$")

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_URL_LINE_RE = re.compile(r"^\s*(https://\S+)\s*$")
_URL_IN_TEXT_RE = re.compile(r"https://[^\s<>\"'`)\]]{1,2048}")
_ENV_ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=")
_FORBIDDEN_ENV = re.compile(r"^(PATH|GH_HOST|GH_REPO|GITLAB_HOST|GLAB_[A-Z0-9_]*)$")
#: Builtins whose arguments are assignments that persist for the rest of the command line.
_EXPORTERS = frozenset({"export", "declare", "typeset", "readonly", "local"})
_SHADOW_RE = re.compile(r"(?:^|[\s;&|(])(?:function\s+(?:gh|glab)\b|(?:gh|glab)\s*\(\s*\)|alias\s+(?:gh|glab)=)")
_REDIR_OP_RE = re.compile(r"&>>?|>>|>&|>\||>|<<<|<&|<>|<")
_PREFIX_KEYWORDS = frozenset({"if", "then", "do", "else", "elif", "while", "until", "!", "{", "("})
_ENV_VALUE_OPTS = frozenset({"-u", "--unset", "-C", "--chdir"})
_ENV_REFUSED_OPTS = frozenset({"-S", "--split-string"})
_HEREDOC_RE = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
_GH_MERGED_RE = re.compile(r"(?i)\bmerged pull request\s+(?:[A-Za-z0-9._-]+/[A-Za-z0-9._-]+)?#([1-9][0-9]{0,9})\b")
_GLAB_MERGED_RE = re.compile(r"(?im)^\W*merged!?\W*$")
_GIT_FF_RE = re.compile(r"(?m)^(?:Fast-forward\b|Merge made by\b)")
_GIT_FAIL_RE = re.compile(r"(?m)^(?:CONFLICT\b|fatal:|error:|Automatic merge failed)")

#: Flags that take a value, per tool, for the commands whose positional argument matters.
_VALUE_FLAGS = {
    "gh": frozenset({"-b", "--body", "-F", "--body-file", "-t", "--subject", "--match-head-commit",
                     "-R", "--repo", "-A", "--author-email", "-H", "--head", "-B", "--base", "--title",
                     "-a", "--assignee", "-l", "--label", "-m", "--milestone", "-p", "--project",
                     "-r", "--reviewer"}),
    "glab": frozenset({"-m", "--message", "--sha", "--squash-message", "-R", "--repo", "-s",
                       "--source-branch", "-b", "--target-branch", "-t", "--title", "-d",
                       "--description", "-a", "--assignee", "-l", "--label"}),
}
#: Short flags that are values on one verb and booleans on another: `gh pr merge -m/-r` are
#: `--merge`/`--rebase` (on `create` they are a milestone and a reviewer); `glab mr merge -s/-d` are
#: `--squash`/`--remove-source-branch` (on `create` they are a source branch and a description).
_BOOLEAN_OVERRIDES = {
    ("gh", "merge"): frozenset({"-m", "-r"}),
    ("glab", "merge"): frozenset({"-s", "-b", "-t", "-d", "-a", "-l"}),
}
_GIT_VALUE_FLAGS = frozenset({"-m", "-F", "-s", "-X", "--strategy", "--strategy-option", "--file", "--into-name"})
_GIT_GLOBAL_VALUE_FLAGS = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"})
_GIT_ABORTS = frozenset({"--abort", "--continue", "--quit", "--squash"})


# ── links ────────────────────────────────────────────────────────────────────


def _repo_segments_ok(path):
    for segment in path.split("/"):
        if segment in (".", "..") or segment.startswith("-") or segment.endswith(".git"):
            return False
    return True


def parse_link(url):
    """``{"kind", "host", "repo", "number"}`` for a canonical PR/MR/issue URL, else ``None``.

    ``kind`` is ``github_pr``, ``github_issue`` or ``gitlab_mr``. Strict: https, a plain
    lowercase host with no userinfo or port, no query or fragment, no percent-escape, and the
    URL must equal the one rebuilt from its parts.
    """
    if not isinstance(url, str) or not 12 <= len(url) <= 2048 or not url.startswith("https://"):
        return None
    if "\\" in url or "%" in url or "?" in url or "#" in url or any(c.isspace() for c in url):
        return None
    try:
        parts = urllib.parse.urlsplit(url)
        host = parts.hostname
        parts.port  # noqa: B018 - raises ValueError on a malformed port
    except ValueError:
        return None
    if not host or parts.netloc != host or not HOST_RE.match(host) or url != "https://" + host + parts.path:
        return None
    match = GITHUB_PATH_RE.match(parts.path)
    if match:
        owner, name, which, number = match.groups()
        repo = "{}/{}".format(owner, name)
        if not _repo_segments_ok(name):
            return None
        return {"kind": "github_pr" if which == "pull" else "github_issue", "host": host, "repo": repo, "number": int(number)}
    match = GITLAB_PATH_RE.match(parts.path)
    if match and _repo_segments_ok(match.group(1)):
        return {"kind": "gitlab_mr", "host": host, "repo": match.group(1), "number": int(match.group(2))}
    return None


def build_link(kind, host, repo, number):
    """The URL for validated parts, or ``None`` when the parts do not round-trip through :func:`parse_link`."""
    if not (isinstance(host, str) and isinstance(repo, str) and isinstance(number, int) and not isinstance(number, bool)):
        return None
    if kind == "github_pr":
        url = "https://{}/{}/pull/{}".format(host, repo, number)
    elif kind == "github_issue":
        url = "https://{}/{}/issues/{}".format(host, repo, number)
    elif kind == "gitlab_mr":
        url = "https://{}/{}/-/merge_requests/{}".format(host, repo, number)
    else:
        return None
    parsed = parse_link(url)
    if parsed is None or parsed["kind"] != kind or parsed["host"] != host or parsed["repo"] != repo or parsed["number"] != number:
        return None
    return url


def mark_parts(entry):
    """The validated ``{"kind": "pr"|"mr", "host", "repo", "number"}`` of a stored mark, else ``None``."""
    if not isinstance(entry, dict) or entry.get("kind") not in LINK_KIND:
        return None
    url = build_link(LINK_KIND[entry["kind"]], entry.get("host"), entry.get("repo"), entry.get("number"))
    if url is None:
        return None
    return {"kind": entry["kind"], "host": entry["host"], "repo": entry["repo"], "number": entry["number"]}


def clean_branch(value):
    """``value`` when it is a plain branch name, else ``None``. An ``owner:`` prefix is dropped."""
    if not isinstance(value, str):
        return None
    name = value.strip()
    if ":" in name:
        name = name.split(":", 1)[1]
    if not BRANCH_RE.match(name) or ".." in name or name.endswith((".lock", "/")):
        return None
    return name


# ── remotes and project context ──────────────────────────────────────────────

_SCP_RE = re.compile(r"^(?:[^@/\s]+@)?([^:/\s]+):(?!//)(.+)$")


def parse_remote_url(url):
    """``(host, repo)`` of a git remote URL (https, ssh://, git://, scp form), lowercased, else ``None``."""
    if not isinstance(url, str):
        return None
    text = url.strip()
    host = path = None
    if "://" in text:
        try:
            parts = urllib.parse.urlsplit(text)
            host, path = parts.hostname, parts.path
        except ValueError:
            return None
        if parts.scheme not in ("https", "http", "ssh", "git"):
            return None
    else:
        match = _SCP_RE.match(text)
        if match:
            host, path = match.group(1), match.group(2)
    if not host or not path:
        return None
    host = host.lower().rstrip(".")
    repo = path.strip("/")
    if repo.endswith(".git"):
        repo = repo[:-4]
    repo = repo.rstrip("/").lower()
    if not HOST_RE.match(host) or not repo or not _repo_segments_ok(repo):
        return None
    return host, repo


def git_remotes(root):
    """``[{"name", "host", "repo"}]`` for every remote of the project at ``root``; ``[]`` on any failure.

    One ``git remote -v`` run against the project root (never a payload's directory), with the
    fsmonitor hook off: a repository's own config must not get to run a program here.
    """
    try:
        result = subprocess.run(
            ["git", "-c", "core.fsmonitor=false", "-C", str(root), "remote", "-v"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=3, check=False,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return []
    if result.returncode != 0:
        return []
    found, seen = [], set()
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        pieces = line.split()
        if len(pieces) < 2:
            continue
        parsed = parse_remote_url(pieces[1])
        if parsed is None or (pieces[0], parsed) in seen:
            continue
        seen.add((pieces[0], parsed))
        found.append({"name": pieces[0], "host": parsed[0], "repo": parsed[1]})
    return found


def _web_host(api_url):
    """The web host a GitHub API URL belongs to: ``api.github.com`` is ``github.com``, a GHE host is itself."""
    try:
        host = urllib.parse.urlsplit(api_url).hostname
    except ValueError:
        return None
    if not host:
        return None
    host = host.lower()
    host = "github.com" if host == "api.github.com" else host
    return host if HOST_RE.match(host) else None


def _valid_repository(value):
    if not isinstance(value, str) or value.count("/") != 1:
        return None
    owner, name = value.split("/")
    if not OWNER_RE.match(owner) or not REPO_NAME_RE.match(name) or not _repo_segments_ok(name):
        return None
    return "{}/{}".format(owner, name)


def _valid_base_path(path):
    """True for ``""`` or a context path such as ``/jira``: no trailing slash, no ``.``/``..`` segment."""
    return bool(JIRA_BASE_PATH_RE.match(path)) and not any(seg in (".", "..") for seg in path.split("/"))


def load_context(root, with_remotes=True):
    """``{"remotes", "github", "jira"}``: what links may be built from, read without the token.

    ``github`` is ``{"web_host", "repository"|None}`` when the GitHub integration is connected,
    ``jira`` is ``{"site_url", "host", "path", "project_key"}`` when Jira is connected AND the
    project binds a valid key. An integration that is not connected contributes nothing: there is
    no fallback to the git origin. ``repository`` is ``None`` unless a current git remote on the
    web host names it, so ``with_remotes=False`` never yields one. Never raises.
    """
    ctx = {"remotes": git_remotes(root) if with_remotes else [], "github": None, "jira": None}
    try:
        from . import integrations

        config = integrations.link_config(root, "github")
        if config is not None:
            web = _web_host(config["account"].get("api_url", ""))
            if web:
                # The binding file is committed: it names the repository `fixes #N` links to only
                # when a current git remote on the web host names the same repository.
                repository = _valid_repository(config["project"].get("repository"))
                if repository and not any(r["host"] == web and r["repo"] == repository.lower() for r in ctx["remotes"]):
                    repository = None
                ctx["github"] = {"web_host": web, "repository": repository}
        config = integrations.link_config(root, "jira")
        if config is not None:
            key = config["project"].get("project_key")
            site = config["account"].get("site_url")
            parts = urllib.parse.urlsplit(site) if isinstance(site, str) else None
            host = (parts.hostname or "").lower() if parts else ""
            base = parts.path.rstrip("/") if parts else ""
            if (isinstance(key, str) and JIRA_PROJECT_RE.match(key) and parts and parts.scheme == "https"
                    and HOST_RE.match(host) and parts.netloc.lower() == host and _valid_base_path(base)):
                ctx["jira"] = {
                    "site_url": "https://{}{}".format(parts.netloc.lower(), base),
                    "host": host, "path": base, "project_key": key,
                }
    except Exception:  # noqa: BLE001 - a hook must never fail on a damaged integration file
        return {"remotes": ctx["remotes"], "github": None, "jira": None}
    return ctx


def link_hosts(ctx):
    """``[{"host", "kinds"}]``: the hosts this project's links may point at, per link kind.

    A consistency check inside the CLI's trust boundary, not a second trust anchor: a mark never
    adds a host. GitHub: ``github.com`` plus the connected account's web host. GitLab:
    ``gitlab.com`` plus a self-hosted host only when a git remote currently names it. Jira: the
    connected site's host, with ``base_path`` (``""`` for Cloud / a root site, else the context
    path such as ``/jira``) on the entry that carries the ``jira`` kind; GitHub/GitLab entries never have it.
    """
    hosts = {}

    def add(host, kind):
        hosts.setdefault(host, set()).add(kind)

    github = ctx.get("github")
    add("github.com", "github_pr")
    github_hosts = {"github.com"}
    if github:
        github_hosts.add(github["web_host"])
        add(github["web_host"], "github_pr")
        if github.get("repository"):
            add(github["web_host"], "github_issue")
    add("gitlab.com", "gitlab_mr")
    for remote in ctx.get("remotes") or []:
        if remote["host"] not in github_hosts and _self_hosted_gitlab_candidate(remote["host"]):
            add(remote["host"], "gitlab_mr")
    if ctx.get("jira"):
        add(ctx["jira"]["host"], "jira")
    entries = []
    for host, kinds in sorted(hosts.items()):
        entry = {"host": host, "kinds": sorted(kinds)}
        if "jira" in kinds:
            entry["base_path"] = ctx["jira"].get("path", "")
        entries.append(entry)
    return entries


#: Remote hosts that are known forges other than GitLab: never a self-hosted GitLab MR host.
_OTHER_FORGES = frozenset({"bitbucket.org", "codeberg.org", "dev.azure.com", "ssh.dev.azure.com", "sourceforge.net"})


def _self_hosted_gitlab_candidate(host):
    """True when a non-GitHub remote host may carry GitLab MR links: no punycode label, no other forge."""
    return host not in _OTHER_FORGES and not any(label.startswith("xn--") for label in host.split("."))


def mark_valid(parts, ctx):
    """True when ``parts`` (a PR/MR mark) matches a current remote and an allowed host for its kind."""
    if not parts:
        return False
    kind = LINK_KIND[parts["kind"]]
    allowed = any(h["host"] == parts["host"] and kind in h["kinds"] for h in link_hosts(ctx))
    return allowed and remote_matches(parts, ctx.get("remotes") or [])


def remote_matches(parts, remotes):
    repo = parts["repo"].lower()
    return any(r["host"] == parts["host"] and r["repo"] == repo for r in remotes)


def unique_repo(remotes, host=None):
    """The one ``(host, repo)`` the remotes name (optionally restricted to ``host``), else ``None``."""
    found = {(r["host"], r["repo"]) for r in remotes if host is None or r["host"] == host}
    return next(iter(found)) if len(found) == 1 else None


# ── commands ─────────────────────────────────────────────────────────────────


def _segments(command):
    """The pipeline segments of ``command``: split on unquoted ``; | & && ||``, newlines and ``( )``.

    Redirections (``2>&1``, ``>&2``, ``&>f``, ``> f``, ``<f``) are removed, not split on; a
    backslash-newline continuation is joined; heredoc bodies and ``#`` comments are dropped;
    quoted text stays inside its segment.
    """
    segments, current = [], []
    heredocs = []
    i, n, quote = 0, len(command), None
    while i < n:
        c = command[i]
        if quote:
            current.append(c)
            if c == "\\" and quote == '"' and i + 1 < n:
                if command[i + 1] == "\n":
                    current.pop()
                else:
                    current.append(command[i + 1])
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            if command[i + 1] != "\n":
                current.append(c)
                current.append(command[i + 1])
            i += 2
            continue
        if c in "'\"":
            quote = c
            current.append(c)
            i += 1
            continue
        if command.startswith("<<", i) and not command.startswith("<<<", i):
            match = _HEREDOC_RE.match(command, i)
            if match:
                heredocs.append(match.group(2))
                i = match.end()
                continue
        if (c in "<>" or (c == "&" and command.startswith("&>", i))) and not command.startswith("<(", i) \
                and not command.startswith(">(", i):
            _drop_fd_digits(current)
            i = _skip_redirect(command, i)
            continue
        if c in "()" and not (c == "(" and current and current[-1] == "$"):
            segments.append("".join(current))
            current = []
            i += 1
            continue
        if c == "#" and (not current or current[-1] in " \t"):
            while i < n and command[i] != "\n":
                i += 1
            continue
        if c == "\n":
            segments.append("".join(current))
            current = []
            i += 1
            for delimiter in heredocs:
                while i < n:
                    end = command.find("\n", i)
                    end = n if end == -1 else end
                    line = command[i:end].strip()
                    i = min(n, end + 1)
                    if line == delimiter:
                        break
            heredocs = []
            continue
        if c in ";|&":
            segments.append("".join(current))
            current = []
            i += 2 if c in "|&" and i + 1 < n and command[i + 1] == c else 1
            continue
        current.append(c)
        i += 1
    segments.append("".join(current))
    return segments


def _drop_fd_digits(current):
    """Remove the file-descriptor number (the ``2`` of ``2>&1``) that sits right before a redirection."""
    j = len(current)
    while j > 0 and current[j - 1].isdigit():
        j -= 1
    if j < len(current) and (j == 0 or current[j - 1] in " \t"):
        del current[j:]


def _skip_redirect(command, i):
    """The index after the redirection operator at ``i`` and its target word."""
    n = len(command)
    match = _REDIR_OP_RE.match(command, i)
    j = match.end() if match else i + 1
    while j < n and command[j] in " \t":
        j += 1
    quote = None
    while j < n:
        ch = command[j]
        if quote:
            if ch == "\\" and quote == '"' and j + 1 < n:
                j += 2
                continue
            if ch == quote:
                quote = None
            j += 1
            continue
        if ch in "'\"":
            quote = ch
        elif ch == "\\" and j + 1 < n:
            j += 1
        elif ch in " \t\n;|&<>()":
            break
        j += 1
    return j


def _split(segment):
    """The shell words of a segment, else ``None`` when it does not parse."""
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return None


def _sets_tool_env(words):
    """True when a segment assigns ``PATH``/``GH_HOST``/``GH_REPO``/``GITLAB_HOST``/``GLAB_*``.

    Only an assignment in command position counts — a ``NAME=value`` prefix, or an argument of
    ``export``/``declare``/``env`` and friends — so ``gh pr create --body "set PATH=/a"`` is not one.
    Such an assignment can aim the tool somewhere the project's remotes do not say.
    """
    for i, word in enumerate(words):
        match = _ENV_ASSIGN_RE.match(word)
        if not match or not _FORBIDDEN_ENV.match(match.group(1)):
            continue
        if all(
            _ENV_ASSIGN_RE.match(w) or w in _PREFIX_KEYWORDS or w in _EXPORTERS or w in ("env", "time", "command")
            or w.startswith("-")
            for w in words[:i]
        ):
            return True
    return False


def _strip_prefixes(tokens):
    """``tokens`` without what runs before the real command, else ``None`` when it must be refused.

    Dropped: ``NAME=value`` words, shell keywords and group openers (``if then do ! { (``), ``time``,
    ``command`` and ``env`` with their options. Any ``PATH``/``GH_HOST``/``GH_REPO``/``GITLAB_HOST``/
    ``GLAB_*`` assignment, wherever it appears, refuses the segment; so does ``env -S`` and
    ``command -v``/``-V`` (which run nothing).
    """
    while tokens:
        head = tokens[0]
        match = _ENV_ASSIGN_RE.match(head)
        if match:
            if _FORBIDDEN_ENV.match(match.group(1)):
                return None
            tokens = tokens[1:]
        elif head in _PREFIX_KEYWORDS:
            tokens = tokens[1:]
        elif head in ("time", "command"):
            tokens = tokens[1:]
            while tokens and tokens[0].startswith("-") and tokens[0] != "-":
                option = tokens[0]
                tokens = tokens[1:]
                if option == "--":
                    break
                if head == "command" and ("v" in option[1:] or "V" in option[1:]):
                    return None
        elif head == "env":
            tokens = tokens[1:]
            while tokens:
                option = tokens[0]
                if option in _ENV_REFUSED_OPTS or option.startswith("--split-string="):
                    return None
                if option in _ENV_VALUE_OPTS:
                    tokens = tokens[2:]
                elif option.startswith("-"):
                    tokens = tokens[1:]
                    if option == "--":
                        break
                else:
                    break
        else:
            break
    return tokens or None


def _flags(tokens, tool, verb):
    """``(values, positionals)`` of the arguments after the verb: ``{flag: value}`` and the bare words."""
    values, positionals = {}, []
    takes_value = _VALUE_FLAGS[tool] - _BOOLEAN_OVERRIDES.get((tool, verb), frozenset())
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.startswith("--") and "=" in token:
            name, _, value = token.partition("=")
            values[name] = value
        elif token.startswith("-") and token != "-":
            if token in takes_value and i + 1 < len(tokens):
                values[token] = tokens[i + 1]
                i += 1
            else:
                values.setdefault(token, True)
        else:
            positionals.append(token)
        i += 1
    return values, positionals


def _pick(values, *names):
    for name in names:
        if isinstance(values.get(name), str):
            return values[name]
    return None


def _repo_arg(value):
    """``owner/repo`` (or ``host/owner/repo``) from a ``--repo`` argument, lowercased, else ``None``."""
    if not isinstance(value, str) or not 3 <= len(value) <= 400:
        return None
    parts = value.strip("/").split("/")
    if len(parts) >= 3 and "." in parts[0]:
        return "/".join(parts[1:]).lower()
    return value.strip("/").lower() if len(parts) >= 2 else None


def _merge_target(positionals):
    """What ``gh pr merge`` / ``glab mr merge`` was told to merge: number, link parts, branch or nothing."""
    if not positionals:
        return None
    arg = positionals[0]
    plain = arg.lstrip("!#")
    if plain.isdigit() and 1 <= len(plain) <= 10 and int(plain) > 0:
        return {"number": int(plain)}
    link = parse_link(arg)
    if link and link["kind"] in ("github_pr", "gitlab_mr"):
        return {"link": link}
    branch = clean_branch(arg)
    return {"branch": branch} if branch else None


def analyze_command(command):
    """The PR/MR/merge actions a shell command line invokes, in order; ``[]`` for anything else.

    Actions: ``{"op": "create", "tool", "kind", "head", "repo"}``, ``{"op": "merge", "tool",
    "kind", "target", "repo"}`` and ``{"op": "git_merge", "branch"}``. A false-positive filter
    only (a command inside ``echo``, quotes or a heredoc is not an action); what makes a mark is
    the tool's own result, parsed by :func:`created_link` / :func:`merge_confirmed`.
    """
    if not isinstance(command, str) or not command.strip() or len(command) > MAX_COMMAND:
        return []
    if _SHADOW_RE.search(command):
        return []
    actions = []
    for segment in _segments(command):
        if not segment.strip():
            continue
        words = _split(segment)
        if words and _sets_tool_env(words):
            return []
        tokens = _strip_prefixes(words) if words else None
        if not tokens:
            continue
        head = tokens[0]
        if head == "gh" and len(tokens) >= 3 and tokens[1] == "pr" and tokens[2] in ("create", "merge"):
            tool, kind, verb = "gh", KIND_PR, tokens[2]
        elif head == "glab" and len(tokens) >= 3 and tokens[1] == "mr" and tokens[2] in ("create", "merge"):
            tool, kind, verb = "glab", KIND_MR, tokens[2]
        elif head == "git":
            action = _git_merge_action(tokens[1:])
            if action:
                actions.append(action)
            continue
        else:
            continue
        values, positionals = _flags(tokens[3:], tool, verb)
        repo = _repo_arg(_pick(values, "-R", "--repo"))
        if verb == "create":
            branch = _pick(values, "-H", "--head") if tool == "gh" else _pick(values, "-s", "--source-branch")
            actions.append({"op": "create", "tool": tool, "kind": kind, "head": clean_branch(branch), "repo": repo})
        else:
            actions.append({"op": "merge", "tool": tool, "kind": kind, "target": _merge_target(positionals), "repo": repo})
    return actions


def _git_merge_action(tokens):
    i = 0
    while i < len(tokens) and tokens[i].startswith("-"):
        i += 2 if tokens[i] in _GIT_GLOBAL_VALUE_FLAGS else 1
    if i >= len(tokens) or tokens[i] != "merge":
        return None
    refs = []
    j = i + 1
    while j < len(tokens):
        token = tokens[j]
        if token in _GIT_ABORTS:
            return None
        if token in _GIT_VALUE_FLAGS:
            j += 2
            continue
        if token.startswith("-"):
            j += 1
            continue
        refs.append(token)
        j += 1
    if len(refs) != 1:
        return None
    return {"op": "git_merge", "branch": clean_branch(refs[0])} if clean_branch(refs[0]) else None


# ── results ──────────────────────────────────────────────────────────────────


def created_link(output):
    """The parts of the one PR/MR URL a ``gh pr create`` / ``glab mr create`` result prints, else ``None``.

    Only a URL that is a whole line counts, it must pass :func:`parse_link`, and exactly one
    distinct PR/MR URL may be present: more than one is ambiguous and ignored.
    """
    if not isinstance(output, str):
        return None
    found = {}
    for line in _ANSI_RE.sub("", output[:MAX_TEXT]).splitlines():
        match = _URL_LINE_RE.match(line)
        if not match:
            continue
        parts = parse_link(match.group(1))
        if parts and parts["kind"] in ("github_pr", "gitlab_mr"):
            found[(parts["kind"], parts["host"], parts["repo"], parts["number"])] = parts
    return next(iter(found.values())) if len(found) == 1 else None


def merge_confirmed(action, output):
    """The merged number (or ``True`` when none is printed) for a successful merge result, else ``None``.

    ``gh pr merge`` prints "Merged pull request #N" (also after squash/rebase); ``glab mr merge``
    prints "Merged!". ``--auto`` ("will be automatically merged") is not a merge. For ``git merge``
    only a positive marker counts: ``Fast-forward`` or ``Merge made by``; "Already up to date"
    and a conflict do not.
    """
    if not isinstance(output, str):
        return None
    text = _ANSI_RE.sub("", output[:MAX_TEXT])
    if action["op"] == "git_merge":
        return True if _GIT_FF_RE.search(text) and not _GIT_FAIL_RE.search(text) else None
    if action["tool"] == "gh":
        match = _GH_MERGED_RE.search(text)
        return int(match.group(1)) if match else None
    if _GLAB_MERGED_RE.search(text):
        link = created_link(text)
        return link["number"] if link and link["kind"] == "gitlab_mr" else True
    return None


# ── payloads ─────────────────────────────────────────────────────────────────


def _strings(value, depth=0):
    if depth > 6:
        return
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item, depth + 1)
    elif isinstance(value, list):
        for item in value[:200]:
            yield from _strings(item, depth + 1)


def _response_text(value):
    """The text a tool result carries, whatever shape the provider gave it (string, object, JSON string)."""
    if isinstance(value, str):
        text = value
        try:
            decoded = json.loads(value)
        except ValueError:
            return text
        return _response_text(decoded) if isinstance(decoded, (str, dict, list)) else text
    if isinstance(value, dict):
        named = [value[k] for k in ("stdout", "stderr", "output") if isinstance(value.get(k), str)]
        if named:
            return "\n".join(named)
    return "\n".join(_strings(value))


def _mcp_objects(value, depth=0):
    """Every JSON object a tool result holds: itself, ``structuredContent`` and any ``content[].text`` JSON."""
    if depth > 4:
        return
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except ValueError:
            return
        if isinstance(decoded, (dict, list)):
            yield from _mcp_objects(decoded, depth + 1)
    elif isinstance(value, dict):
        yield value
        if "structuredContent" in value:
            yield from _mcp_objects(value["structuredContent"], depth + 1)
        content = value.get("content")
        for item in content[:50] if isinstance(content, list) else ():
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                yield from _mcp_objects(item["text"], depth + 1)
    elif isinstance(value, list):
        for item in value[:50]:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                yield from _mcp_objects(item["text"], depth + 1)
            else:
                yield from _mcp_objects(item, depth + 1)


def _is_error(objects):
    return any(o.get("isError") is True or o.get("is_error") is True for o in objects)


def _int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def mcp_created(response):
    """``(parts, head)`` for a ``create_pull_request`` result, else ``None``.

    Only ``html_url`` and ``number`` are read, from a JSON object (never free text); the number
    in the URL path must equal ``number``; an ``isError`` result is ignored.
    """
    objects = list(_mcp_objects(response))
    if _is_error(objects):
        return None
    for obj in objects:
        url, number = obj.get("html_url"), _int(obj.get("number"))
        if not isinstance(url, str) or number is None:
            continue
        parts = parse_link(url)
        if not parts or parts["kind"] != "github_pr" or parts["number"] != number:
            continue
        head = obj.get("head")
        return parts, clean_branch(head.get("ref") if isinstance(head, dict) else None)
    return None


def mcp_merged(tool_input, response):
    """``{"number", "repo"}`` for a successful ``merge_pull_request`` result, else ``None``."""
    objects = list(_mcp_objects(response))
    if _is_error(objects) or not any(o.get("merged") is True for o in objects):
        return None
    inp = tool_input if isinstance(tool_input, dict) else {}
    number = _int(inp.get("pullNumber") or inp.get("pull_number") or inp.get("number"))
    if number is None:
        return None
    owner, name = inp.get("owner"), inp.get("repo")
    repo = _valid_repository("{}/{}".format(owner, name)) if isinstance(owner, str) and isinstance(name, str) else None
    return {"number": number, "repo": repo.lower() if repo else None}


def _tool(payload):
    """``(name, kind)``: the tool a hook payload names, from any provider's spelling."""
    for key in ("tool_name", "tool"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value, key
    return "", ""


def classify(payload):
    """What a hook payload is, as far as this module is concerned, else ``None``.

    ``{"event": "command", "actions", "output", "cwd", "failed"}`` for a shell call (Claude Code and Codex
    ``Bash``, opencode ``bash``; ``failed`` when the output came from Claude Code's
    ``PostToolUseFailure`` ``error`` field, where only a creation's "already exists" URL is read) that invokes ``gh``/``glab``/``git merge``;
    ``{"event": "mcp_create"|"mcp_merge", ...}`` for the pull-request MCP tools;
    ``{"event": "prompt", "text"}`` for a user prompt.
    """
    if not isinstance(payload, dict):
        return None
    name, _ = _tool(payload)
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else ""
    if not name:
        prompt = payload.get("prompt")
        if isinstance(prompt, str) and prompt.strip():
            return {"event": "prompt", "text": prompt[:MAX_PROMPT]}
        return None
    inp = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else payload.get("args")
    inp = inp if isinstance(inp, dict) else {}
    response, failed = None, False
    for key in ("tool_response", "tool_output", "output", "error"):
        if payload.get(key) is not None:
            response, failed = payload[key], key == "error"
            break
    bare = name.lower().split(".")[-1]
    if bare == "bash":
        actions = analyze_command(inp.get("command"))
        if not actions or response is None:
            return None
        return {
            "event": "command", "actions": actions, "output": _response_text(response)[:MAX_TEXT],
            "cwd": cwd, "failed": failed,
        }
    if bare.endswith("create_pull_request"):
        created = mcp_created(response)
        return {"event": "mcp_create", "created": created, "cwd": cwd, "head": clean_branch(inp.get("head"))} if created else None
    if bare.endswith("merge_pull_request"):
        merged = mcp_merged(inp, response)
        return {"event": "mcp_merge", "merged": merged, "cwd": cwd} if merged else None
    return None


# ── issue references ─────────────────────────────────────────────────────────

_OWNER_REPO_ISSUE_RE = re.compile(
    r"(?<![\w./-])([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/([A-Za-z0-9._-]{1,100})#([1-9][0-9]{0,9})\b"
)
_CLOSING_RE = re.compile(r"\b(?i:fix(?:e[sd])?|close[sd]?|resolve[sd]?)\s+#([1-9][0-9]{0,9})\b")
#: A cheap pre-test the callers use before loading any configuration: nothing here can match without one of these.
_MAYBE_REF_RE = re.compile(r"-[0-9]|#[0-9]|/issues/|/browse/")


def maybe_ref(text):
    """False when ``text`` cannot hold a reference, so a caller need not load the integration config."""
    return isinstance(text, str) and bool(_MAYBE_REF_RE.search(text))


def _jira_key_re(project_key, source):
    tail = r"(?![A-Za-z0-9_])" if source == "branch" else r"(?![A-Za-z0-9_-])"
    return re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(project_key) + r"-([1-9][0-9]{0,9})" + tail)


def _github_repos(ctx):
    """Lowercased repositories a GitHub issue reference may name: the bound one and any a remote on the web host names."""
    github = ctx["github"]
    return {github["repository"].lower()} | {r["repo"] for r in ctx.get("remotes") or [] if r["host"] == github["web_host"]}


def extract_refs(text, ctx, source="prompt"):
    """Issue references in ``text`` as parts, per the strict rules; ``[]`` with no integration configured.

    ``source`` is ``prompt``, ``branch`` (Jira keys only, which may be followed by ``-slug``) or
    ``task``. A GitHub ``owner/repo#N`` or issue URL must name the bound repository or one a remote
    on the web host names, whatever the source.
    Returns ``{"system": "jira", "key"}`` / ``{"system": "github", "repo", "number"}`` entries;
    nothing but the key is kept from the text.
    """
    if not isinstance(text, str) or not text or not maybe_ref(text):
        return []
    text = text[:MAX_PROMPT]
    found, seen = [], set()

    def add(entry, marker):
        if marker not in seen and len(found) < MAX_REFS_PER_TEXT:
            seen.add(marker)
            found.append(entry)

    jira = ctx.get("jira")
    if jira:
        for match in _jira_key_re(jira["project_key"], source).finditer(text):
            add({"system": "jira", "key": "{}-{}".format(jira["project_key"], match.group(1))}, ("j", match.group(1)))
        if source != "branch":
            for url in _URL_IN_TEXT_RE.findall(text):
                try:
                    parts = urllib.parse.urlsplit(url)
                    host = parts.hostname
                except ValueError:
                    continue
                match = re.match(r"^" + re.escape(jira["path"]) + r"/browse/([A-Z][A-Z0-9_]{1,9})-([1-9][0-9]{0,9})$", parts.path)
                if parts.scheme == "https" and host == jira["host"] and match and match.group(1) == jira["project_key"]:
                    add({"system": "jira", "key": "{}-{}".format(match.group(1), match.group(2))}, ("j", match.group(2)))
    github = ctx.get("github")
    if github and github.get("repository") and source != "branch":
        bound = github["repository"].lower()
        allowed = _github_repos(ctx)

        def accept(repo):
            # Prompt text is often pasted from elsewhere: no source may link an arbitrary repository.
            return repo.lower() in allowed

        for match in _OWNER_REPO_ISSUE_RE.finditer(text):
            repo = "{}/{}".format(match.group(1), match.group(2))
            if _valid_repository(repo) and accept(repo):
                add({"system": "github", "repo": repo, "number": int(match.group(3))}, ("g", repo.lower(), match.group(3)))
        for match in _CLOSING_RE.finditer(text):
            add({"system": "github", "repo": github["repository"], "number": int(match.group(1))}, ("g", bound, match.group(1)))
        for url in _URL_IN_TEXT_RE.findall(text):
            parts = parse_link(url)
            if parts and parts["kind"] == "github_issue" and parts["host"] == github["web_host"] and accept(parts["repo"]):
                add({"system": "github", "repo": parts["repo"], "number": parts["number"]}, ("g", parts["repo"].lower(), str(parts["number"])))
    return found


def ref_view(entry, ctx):
    """``{"system", "key", "url"}`` for a stored reference that still validates, else ``None``.

    The URL is rebuilt from the current integration config on every call; a reference whose
    integration is gone, or whose key or repository no longer belongs to the bound project or its
    remotes, is omitted.
    """
    if not isinstance(entry, dict):
        return None
    if entry.get("system") == "jira":
        jira = ctx.get("jira")
        match = JIRA_KEY_RE.match(entry.get("key") if isinstance(entry.get("key"), str) else "")
        if not jira or not match or match.group(1) != jira["project_key"]:
            return None
        key = "{}-{}".format(match.group(1), match.group(2))
        url = "{}/browse/{}".format(jira["site_url"], key)
        shape = re.match(r"^https://" + re.escape(jira["host"]) + re.escape(jira["path"]) + r"/browse/[A-Z][A-Z0-9_]{1,9}-[1-9][0-9]{0,9}$", url)
        return {"system": "jira", "key": key, "url": url} if shape else None
    if entry.get("system") == "github":
        github = ctx.get("github")
        repo, number = entry.get("repo"), entry.get("number")
        if not github or not github.get("repository") or not _valid_repository(repo):
            return None
        # Re-validated on every read, as when it was taken: a repository no remote vouches for any more is dropped.
        if repo.lower() not in _github_repos(ctx):
            return None
        url = build_link("github_issue", github["web_host"], repo, number)
        return {"system": "github", "key": "{}#{}".format(repo, number), "url": url} if url else None
    return None


def ref_identity(entry):
    """A hashable identity for a stored reference (for de-duplication), or ``None`` when malformed."""
    if not isinstance(entry, dict):
        return None
    if entry.get("system") == "jira" and isinstance(entry.get("key"), str):
        return ("jira", entry["key"])
    if entry.get("system") == "github" and isinstance(entry.get("repo"), str) and isinstance(entry.get("number"), int):
        return ("github", entry["repo"].lower(), entry["number"])
    return None
