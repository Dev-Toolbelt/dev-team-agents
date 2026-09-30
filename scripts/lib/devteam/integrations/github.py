"""GitHub (github.com and GitHub Enterprise Server) over the REST API."""

from __future__ import annotations

import re
import subprocess
import urllib.parse

from ..errors import UsageError
from . import http
from .base import check_token, fact, field

DEFAULT_API_URL = "https://api.github.com"
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class GitHub:
    name = "github"
    origin_key = "api_url"
    title = "GitHub"
    description = "Read repositories and sign in with a personal access token."
    homepage = "https://github.com"
    auth = {
        "kind": "token",
        "label": "Personal access token",
        "help": "A fine-grained or classic personal access token. It is stored in the OS "
        "secret store, never in a file the project shares.",
    }
    fields = [
        field(
            "api_url", "account", "API URL", required=True, default=DEFAULT_API_URL,
            placeholder="https://api.github.com",
            help="https://api.github.com, or https://<host>/api/v3 for GitHub Enterprise Server.",
        ),
        field(
            "repository", "project", "Repository", placeholder="owner/name", resource="repos",
            help="The repository this project works against.",
        ),
    ]

    def normalize(self, key, value):
        value = value.strip()
        if key == "api_url":
            return http.validate_base_url(value, "api_url")
        if key == "repository":
            if not _REPO_RE.match(value):
                raise UsageError("repository must look like owner/name")
            return value
        raise UsageError("unknown field {!r}".format(key))

    def _headers(self, token):
        return {
            "Authorization": "Bearer {}".format(check_token(token)),
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def test(self, account, token):
        data, headers = http.get_json(account["api_url"], "/user", self._headers(token))
        if not isinstance(data, dict) or not data.get("login"):
            raise http.FetchError("unreachable", "The server did not answer like the GitHub API")
        scopes = headers.get("X-OAuth-Scopes")
        if scopes is None:
            scope_text = "fine-grained"
        else:
            scope_text = scopes.strip() or "none"
        facts = [fact("Account", data["login"], "positive")]
        if data.get("name"):
            facts.append(fact("Name", data["name"]))
        facts.append(fact("Token scopes", scope_text))
        remaining, limit = headers.get("X-RateLimit-Remaining"), headers.get("X-RateLimit-Limit")
        if remaining is not None and limit is not None:
            low = remaining.strip().isdigit() and int(remaining) < 50
            facts.append(fact("Rate limit", "{} / {} remaining".format(remaining, limit),
                              "warning" if low else "neutral"))
        return {"ok": True, "state": "connected",
                "summary": "Signed in as {}".format(data["login"]), "facts": facts}

    def resources(self, kind, account, token):
        if kind != "repos":
            raise UsageError("unknown resource kind {!r} for github".format(kind),
                             hint="Available: repos")
        data, headers = http.get_json(
            account["api_url"], "/user/repos", self._headers(token),
            query={"per_page": "100", "sort": "updated"},
        )
        if not isinstance(data, list):
            raise http.FetchError("unreachable", "The server did not answer like the GitHub API")
        items = [
            {"value": repo["full_name"], "label": repo["full_name"]}
            for repo in data
            if isinstance(repo, dict) and isinstance(repo.get("full_name"), str)
        ]
        truncated = 'rel="next"' in (headers.get("Link") or "")
        return {"items": items, "truncated": truncated}

    def detect(self, project_root, account):
        api_host = (urllib.parse.urlsplit(account["api_url"]).hostname or "").lower()
        web_host = "github.com" if api_host == "api.github.com" else api_host
        try:
            out = subprocess.run(
                ["git", "remote", "get-url", "origin"], cwd=str(project_root),
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return {}
        if out.returncode != 0:
            return {}
        repo = parse_remote(out.stdout.decode("utf-8", "replace").strip(), web_host)
        return {"repository": repo} if repo else {}


_SCP_RE = re.compile(r"^(?:[^@/]+@)?(?P<host>[^:/]+):(?P<path>[^/].*)$")


def parse_remote(url, web_host):
    """``owner/name`` when ``url`` points at ``web_host``, else ``None``."""
    host = path = None
    if "://" in url:
        try:
            parsed = urllib.parse.urlsplit(url)
            host, path = parsed.hostname, parsed.path
        except ValueError:
            return None
    else:
        match = _SCP_RE.match(url)
        if match:
            host, path = match.group("host"), match.group("path")
    if not host or host.lower() != web_host:
        return None
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return path if _REPO_RE.match(path) else None
